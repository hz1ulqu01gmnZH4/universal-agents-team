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

    reasoning_style: Literal["strategic", "divergent", "analytical", "convergent", "lateral"] = "analytical"
    risk_tolerance: Literal["very_low", "low", "moderate", "high", "very_high"] = "moderate"
    exploration_vs_exploitation: float = Field(default=0.5, ge=0.0, le=1.0)


class AuthorityLevel(IntEnum):
    """Authority hierarchy matching protection rings."""

    WORKER = 0
    LEAD = 1
    ORCHESTRATOR = 2
    EVOLUTION_ENGINE = 3


class RoleComposition(FrameworkModel):
    """A complete role definition composed from atoms.
    Loaded from roles/compositions/{name}.yaml.

    Phase 1: accepts simplified construction for testing and lightweight usage.
    Full construction with all fields remains supported."""

    name: str
    description: str
    capabilities: list[str]  # References to CapabilityAtom names in capabilities.yaml
    model: ModelPreference | str = ModelPreference.SONNET
    thinking: ThinkingSetting | str = "normal"
    behavioral_descriptors: BehavioralDescriptors = BehavioralDescriptors()
    voice: VoiceProfile | None = None  # None uses domain defaults
    authority_level: AuthorityLevel = AuthorityLevel.WORKER
    forbidden: list[str] = []
    scout_config: dict | None = None  # For scout roles: exploration parameters
    review_mandate: dict | None = None  # For reviewer roles: required checks
