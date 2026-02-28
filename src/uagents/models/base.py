"""Base models for the Universal Agents Framework.
Spec reference: used throughout all sections."""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound="FrameworkModel")


class FrameworkModel(BaseModel):
    """Base for all framework models.
    Enforces strict validation, forbids extra fields, uses enum by value."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        use_enum_values=True,
        validate_default=True,
    )


class TimestampedModel(FrameworkModel):
    """Adds created_at/updated_at with auto-population."""

    created_at: datetime
    updated_at: datetime | None = None


class IdentifiableModel(TimestampedModel):
    """Adds id field with prefix-based generation."""

    id: str  # e.g., "task-20260228-001", "evo-20260228-001"


_id_lock = threading.Lock()
_id_counters: dict[str, int] = {}


def generate_id(prefix: str) -> str:
    """Generate a timestamped unique ID.

    Format: {prefix}-{YYYYMMDD}-{NNN} where NNN is a zero-padded counter.
    Counter is per-prefix, per-process, monotonically increasing.
    Thread-safe via lock.
    """
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    key = f"{prefix}-{date_str}"
    with _id_lock:
        _id_counters[key] = _id_counters.get(key, 0) + 1
        counter = _id_counters[key]
    return f"{prefix}-{date_str}-{counter:03d}"


def validate_yaml_path(path: Path) -> Path:
    """Validate that a path points to a YAML file and exists."""
    if not path.exists():
        raise FileNotFoundError(f"Required YAML file not found: {path}")
    if path.suffix not in (".yaml", ".yml"):
        raise ValueError(f"Not a YAML file: {path}")
    return path
