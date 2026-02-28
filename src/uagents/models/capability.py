"""Capability atom models.
Spec reference: Section 4.1 (Capability Atoms)."""
from __future__ import annotations

from enum import StrEnum
from typing import Literal

from .base import FrameworkModel


class ModelPreference(StrEnum):
    """Claude model tier preference."""

    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"


class ThinkingSetting(FrameworkModel):
    """Thinking mode configuration — can be bool or 'extended'."""

    value: bool | Literal["extended"]


class CapabilityAtom(FrameworkModel):
    """A single composable capability fragment.
    Roles are composed from multiple atoms."""

    name: str
    description: str
    instruction_fragment: str
    model_preference: ModelPreference | None = None
    thinking: ThinkingSetting | None = None
    authority: bool = False
