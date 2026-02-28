"""Domain configuration models.
Spec reference: Section 22 (Domain Instantiation & Switching)."""
from __future__ import annotations

from .base import FrameworkModel


class VoiceDefaults(FrameworkModel):
    """Default voice settings for a domain."""

    language: str = "language_japanese"
    tone: str = "tone_cautious"
    style: str = "style_technical"


class DomainConfig(FrameworkModel):
    """Configuration for a domain instance."""

    name: str
    charter_path: str
    voice_defaults: VoiceDefaults = VoiceDefaults()
    active: bool = True
    max_concurrent_agents: int = 5
    topology_patterns: list[str] = ["solo", "hierarchical_team"]
