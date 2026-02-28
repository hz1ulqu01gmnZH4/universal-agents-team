"""YAML serialization helpers — used throughout the framework.
NOT a model file, but critical infrastructure."""
from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def model_to_yaml(model: BaseModel, path: Path) -> None:
    """Serialize a Pydantic model to YAML file.
    Uses atomic write pattern for safety."""
    data = model.model_dump(mode="json", exclude_none=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f".tmp.{__import__('os').getpid()}")
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_path.replace(path)  # Atomic on POSIX


def model_from_yaml(model_class: type[T], path: Path) -> T:
    """Deserialize a Pydantic model from YAML file.
    NEVER returns defaults — raises on missing or invalid files."""
    if not path.exists():
        raise FileNotFoundError(f"Required YAML file not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"Empty YAML file: {path}")
    return model_class.model_validate(data, strict=False)
