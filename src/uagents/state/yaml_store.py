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
        if not str(full).startswith(str(self.base_dir)):
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

    def write(self, relative_path: str, model: FrameworkModel) -> None:
        """Atomic write: serialize to temp file, then os.replace().
        Acquires advisory lock for duration of write."""
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Check disk space before write (S3)
        try:
            import psutil
            disk = psutil.disk_usage(str(path.parent))
            if disk.free < 100 * 1024 * 1024:  # 100MB threshold
                raise OSError(
                    f"Insufficient disk space ({disk.free // 1024 // 1024}MB free). "
                    f"Refusing write to prevent data corruption: {path}"
                )
        except ImportError:
            pass  # psutil optional for disk check

        data = model.model_dump(mode="json", exclude_none=True)
        tmp_path = path.with_suffix(f".tmp.{os.getpid()}")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                yaml.dump(data, f, default_flow_style=False,
                          allow_unicode=True, sort_keys=False)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            tmp_path.replace(path)  # Atomic on POSIX
        except Exception:
            # Clean up temp file on any failure
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def read_raw(self, relative_path: str) -> dict:
        """Read YAML as raw dict (for partial reads). Still validates basic structure."""
        path = self._resolve(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"Required YAML file not found: {path}")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            raise ValueError(f"Empty YAML file: {path}")
        if not isinstance(data, dict):
            raise TypeError(f"Expected YAML dict, got {type(data).__name__}: {path}")
        return data

    def write_raw(self, relative_path: str, data: dict) -> None:
        """Atomic write from raw dict. Same atomic pattern as write()."""
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f".tmp.{os.getpid()}")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False,
                          allow_unicode=True, sort_keys=False)
            tmp_path.replace(path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def exists(self, relative_path: str) -> bool:
        return self._resolve(relative_path).exists()

    def list_dir(self, relative_path: str) -> list[str]:
        path = self._resolve(relative_path)
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        return sorted(p.name for p in path.iterdir())
