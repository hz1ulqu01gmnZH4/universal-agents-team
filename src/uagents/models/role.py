"""Role composition models.
Spec reference: Section 4.2 (Composable Role Definitions)."""
from __future__ import annotations

from enum import IntEnum
from typing import Literal

from pydantic import Field

from .base import FrameworkModel
from .capability import ModelPreference, ThinkingSetting
from .voice import VoiceProfile


class BehavioralDescriptors(FrameworkModel):
    """Behavioral traits that shape reasoning style."""

    reasoning_style: Literal["strategic", "divergent", "analytical", "convergent", "lateral"]
    risk_tolerance: Literal["very_low", "low", "moderate", "high", "very_high"]
    exploration_vs_exploitation: float = Field(ge=0.0, le=1.0)


class AuthorityLevel(IntEnum):
    """Authority hierarchy matching protection rings."""

    WORKER = 0
    LEAD = 1
    ORCHESTRATOR = 2
    EVOLUTION_ENGINE = 3


class RoleComposition(FrameworkModel):
    """A complete role definition composed from atoms.
    Loaded from roles/compositions/{name}.yaml."""

    name: str
    description: str
    capabilities: list[str]  # References to CapabilityAtom names in capabilities.yaml
    model: ModelPreference
    thinking: ThinkingSetting
    behavioral_descriptors: BehavioralDescriptors
    voice: VoiceProfile
    authority_level: AuthorityLevel
    forbidden: list[str] = []
    scout_config: dict | None = None  # For scout roles: exploration parameters
    review_mandate: dict | None = None  # For reviewer roles: required checks
