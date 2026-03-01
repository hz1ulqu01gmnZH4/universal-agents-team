"""Atomic YAML file operations with Pydantic validation.
Spec reference: Section 3.3 (state persistence), Section 24 (directory tree)."""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from ..models.base import FrameworkModel

T = TypeVar("T", bound=BaseModel)

# Hard size cap — refuse to load files over 1MB (failure mode S6)
MAX_YAML_SIZE_BYTES = 1_048_576


class YamlStore:
    """Atomic YAML file operations with advisory file locking.

    Design invariants:
    - Atomic writes via temp-file + os.replace() — prevents partial writes on crash (S2)
    - Advisory file locks via fcntl.flock() — prevents concurrent writes (S1)
    - Pydantic validation on every read — corrupt YAML caught immediately (S4)
    - Fail-loud: no defaults, no fallbacks. Missing/corrupt → raise immediately
    - Always yaml.safe_load(), NEVER yaml.load() (S5)
    - All file ops enforce encoding='utf-8' (S8)
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        if not self.base_dir.is_dir():
            raise FileNotFoundError(f"Base directory does not exist: {self.base_dir}")

    def _resolve(self, relative_path: str) -> Path:
        """Resolve relative path to absolute, validate it stays within base_dir."""
        full = (self.base_dir / relative_path).resolve()
        if not full.is_relative_to(self.base_dir):
            raise ValueError(f"Path escapes base directory: {relative_path}")
        return full

    def read(self, relative_path: str, model_class: type[T]) -> T:
        """Read YAML file, deserialize to Pydantic model.
        Raises FileNotFoundError or ValidationError (never returns defaults)."""
        path = self._resolve(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"Required YAML file not found: {path}")
        if not os.access(path, os.R_OK):
            raise PermissionError(f"Cannot read file (check permissions): {path}")
        file_size = path.stat().st_size
        if file_size > MAX_YAML_SIZE_BYTES:
            raise ValueError(
                f"YAML file exceeds size cap ({file_size} > {MAX_YAML_SIZE_BYTES}): {path}"
            )
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            raise ValueError(f"Empty YAML file: {path}")
        return model_class.model_validate(data, strict=False)

    def _check_disk_space(self, path: Path) -> None:
        """Check disk space before write. Uses psutil if available, os.statvfs otherwise."""
        threshold = 100 * 1024 * 1024  # 100MB
        try:
            import psutil
            disk = psutil.disk_usage(str(path.parent))
            free = disk.free
        except ImportError:
            stat = os.statvfs(str(path.parent))
            free = stat.f_bavail * stat.f_frsize
        if free < threshold:
            raise OSError(
                f"Insufficient disk space ({free // 1024 // 1024}MB free). "
                f"Refusing write to prevent data corruption: {path}"
            )

    def write(self, relative_path: str, model: FrameworkModel) -> None:
        """Atomic write: serialize to temp file, then os.replace().
        Acquires advisory lock on sidecar .lock file for mutual exclusion."""
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._check_disk_space(path)

        data = model.model_dump(mode="json", exclude_none=True)
        tmp_path = path.with_suffix(f".tmp.{os.getpid()}")
        lock_path = path.with_suffix(path.suffix + ".lock")
        try:
            with open(lock_path, "w", encoding="utf-8") as lock_f:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
                with open(tmp_path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, default_flow_style=False,
                              allow_unicode=True, sort_keys=False)
                    f.flush()
                    os.fsync(f.fileno())
                tmp_path.replace(path)  # Atomic on POSIX
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def read_raw(self, relative_path: str) -> dict:
        """Read YAML as raw dict (for partial reads). Still validates basic structure."""
        path = self._resolve(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"Required YAML file not found: {path}")
        file_size = path.stat().st_size
        if file_size > MAX_YAML_SIZE_BYTES:
            raise ValueError(
                f"YAML file exceeds size cap ({file_size} > {MAX_YAML_SIZE_BYTES}): {path}"
            )
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            raise ValueError(f"Empty YAML file: {path}")
        if not isinstance(data, dict):
            raise TypeError(f"Expected YAML dict, got {type(data).__name__}: {path}")
        return data

    def write_raw(self, relative_path: str, data: dict) -> None:
        """Atomic write from raw dict. Same atomic+locked pattern as write()."""
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._check_disk_space(path)
        tmp_path = path.with_suffix(f".tmp.{os.getpid()}")
        lock_path = path.with_suffix(path.suffix + ".lock")
        try:
            with open(lock_path, "w", encoding="utf-8") as lock_f:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
                with open(tmp_path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, default_flow_style=False,
                              allow_unicode=True, sort_keys=False)
                    f.flush()
                    os.fsync(f.fileno())
                tmp_path.replace(path)
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def delete(self, relative_path: str) -> None:
        """Delete a YAML file. FM-101: Required by cost record archival.

        Acquires advisory lock before deletion to prevent concurrent
        read-delete races. Raises FileNotFoundError if file does not exist.
        """
        path = self._resolve(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"Cannot delete non-existent file: {path}")
        lock_path = path.with_suffix(path.suffix + ".lock")
        with open(lock_path, "w", encoding="utf-8") as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
            path.unlink()
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
        # Clean up lock file (best-effort)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass

    def ensure_dir(self, relative_path: str) -> Path:
        """Create directory (and parents) if it doesn't exist. Returns the absolute path."""
        path = self._resolve(relative_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def exists(self, relative_path: str) -> bool:
        return self._resolve(relative_path).exists()

    def list_dir(self, relative_path: str) -> list[str]:
        path = self._resolve(relative_path)
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        return sorted(p.name for p in path.iterdir())
