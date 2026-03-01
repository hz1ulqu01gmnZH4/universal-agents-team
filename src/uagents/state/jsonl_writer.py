"""Append-only JSONL log writer with rotation.
Spec reference: Section 17 (Audit System)."""
from __future__ import annotations

import fcntl
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from ..models.audit import BaseLogEntry, LogStream

# Secret patterns to scrub before writing (X7)
_SECRET_PATTERNS = [
    re.compile(r"(sk-[a-zA-Z0-9]{20,})"),                    # OpenAI/Anthropic API keys
    re.compile(r"(ghp_[a-zA-Z0-9]{36})"),                     # GitHub personal access tokens
    re.compile(r"(gho_[a-zA-Z0-9]{36})"),                     # GitHub OAuth tokens
    re.compile(r"(password\s*[=:]\s*\S+)", re.I),             # Password assignments
    re.compile(r"(ANTHROPIC_API_KEY\s*=\s*\S+)"),             # Anthropic keys
    re.compile(r"(OPENAI_API_KEY\s*=\s*\S+)"),                # OpenAI keys
    re.compile(r"(AWS_SECRET_ACCESS_KEY\s*=\s*\S+)"),         # AWS secret keys
    re.compile(r"(AKIA[0-9A-Z]{16})"),                        # AWS access key IDs
    re.compile(r"(xoxb-[a-zA-Z0-9-]+)"),                     # Slack bot tokens
    re.compile(r"(xoxp-[a-zA-Z0-9-]+)"),                     # Slack user tokens
    re.compile(r"(Bearer\s+[a-zA-Z0-9._~+/=-]{20,})", re.I), # Bearer tokens
    re.compile(r"(ssh-(?:rsa|ed25519)\s+\S{20,})"),           # SSH keys
    re.compile(r"(SECRET[_-]?KEY\s*[=:]\s*\S+)", re.I),      # Generic secret keys
    re.compile(r"(API[_-]?KEY\s*[=:]\s*\S+)", re.I),         # Generic API keys
    re.compile(r"(TOKEN\s*[=:]\s*\S{20,})", re.I),           # Generic long tokens
]


class JsonlWriter:
    """Append-only JSONL log writer with rotation support.

    Design invariants:
    - Append-only: entries are never modified after writing
    - Thread-safe: file lock on every append (A1)
    - Rotation at configurable max size (default 10MB)
    - Max rotated files to prevent unbounded disk usage (A3)
    - Corrupt lines skipped on read with warning logged (A2)
    - Secret scrubbing before write (X7)
    """

    def __init__(
        self,
        log_dir: Path,
        stream: LogStream,
        max_size_mb: int = 10,
        max_rotated_files: int = 10,
    ):
        self.log_dir = log_dir
        self.stream = stream
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_rotated_files = max_rotated_files
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @property
    def current_path(self) -> Path:
        return self.log_dir / f"{self.stream.value}.jsonl"

    def append(self, entry: BaseLogEntry) -> None:
        """Append a log entry. Thread-safe via file lock."""
        line = entry.model_dump_json(exclude_none=True)
        line = self._scrub_secrets(line)
        self._maybe_rotate()
        with open(self.current_path, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(line + "\n")
            f.flush()
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def read_entries(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Read entries with optional time-range filter.
        Searches current + rotated files for time-range queries (A4)."""
        entries: list[dict] = []
        for path in self._all_log_files():
            if not path.exists():
                continue
            with open(path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        # Corrupt line — skip with warning (A2)
                        import sys
                        print(
                            f"WARNING: Corrupt JSON at {path}:{line_num}, skipping",
                            file=sys.stderr,
                        )
                        continue
                    ts = entry.get("timestamp", "")
                    if since and ts < since.isoformat():
                        continue
                    if until and ts > until.isoformat():
                        continue
                    entries.append(entry)
                    if len(entries) >= limit:
                        return entries
        return entries

    def _maybe_rotate(self) -> None:
        """Rotate if current file exceeds max size."""
        if not self.current_path.exists():
            return
        if self.current_path.stat().st_size < self.max_size_bytes:
            return
        self.rotate()

    def rotate(self) -> None:
        """Rotate current log file under lock. Sequence (A6):
        1. Acquire lock to prevent concurrent rotation
        2. Atomic rename old → rotated
        3. Create new empty file
        4. Clean up excess rotated files
        """
        if not self.current_path.exists():
            return
        lock_path = self.current_path.with_suffix(".lock")
        with open(lock_path, "w", encoding="utf-8") as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
            # Re-check after acquiring lock (another process may have rotated)
            if not self.current_path.exists() or self.current_path.stat().st_size < self.max_size_bytes:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
                return
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            rotated = self.log_dir / f"{self.stream.value}.{timestamp}.jsonl"
            self.current_path.rename(rotated)
            self.current_path.touch()
            self._cleanup_old_rotated()
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)

    def _all_log_files(self) -> list[Path]:
        """Current + rotated files, sorted chronologically."""
        files = sorted(self.log_dir.glob(f"{self.stream.value}.*.jsonl"))
        if self.current_path.exists():
            files.append(self.current_path)
        return files

    def _cleanup_old_rotated(self) -> None:
        """Remove oldest rotated files exceeding max_rotated_files."""
        rotated = sorted(self.log_dir.glob(f"{self.stream.value}.*.jsonl"))
        while len(rotated) > self.max_rotated_files:
            oldest = rotated.pop(0)
            oldest.unlink()

    @staticmethod
    def _scrub_secrets(text: str) -> str:
        """Remove known secret patterns from log text (X7)."""
        for pattern in _SECRET_PATTERNS:
            text = pattern.sub("[REDACTED]", text)
        return text
