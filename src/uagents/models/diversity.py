"""Diversity measurement models.
Spec reference: Section 10 (Diversity Enforcement).

Phase 2: SRD metric, VDI metric, stagnation signals.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from .base import FrameworkModel


class StagnationLevel(StrEnum):
    """Stagnation detection levels from Section 10.2."""

    AGENT = "agent"          # Single agent repeating itself
    VOICE = "voice"          # All agents using same voice
    TEAM = "team"            # Team-level SRD collapse
    FRAMEWORK = "framework"  # No evolution, same topology


class StagnationSignal(FrameworkModel):
    """A detected stagnation event."""

    level: StagnationLevel
    description: str
    metric_name: str      # e.g., "srd", "vdi", "output_similarity"
    metric_value: float   # The value that triggered the signal
    threshold: float      # The threshold that was breached
    task_id: str | None = None
    agent_id: str | None = None
    consecutive_count: int = 1  # How many consecutive breaches


class VDIMeasurement(FrameworkModel):
    """Voice Diversity Index measurement for a task.

    Dimensions (Section 10.1):
    - Language: binary (same=0, different=1)
    - Tone: categorical distance
    - Style: categorical distance
    - Persona: categorical distance (both null = 0)
    - Formality: |f1 - f2|
    - Verbosity: |v1 - v2|
    """

    task_id: str
    agent_count: int
    vdi_score: float = Field(ge=0.0, le=1.0)
    dimension_scores: dict[str, float]  # Per-dimension averages
    timestamp: datetime


class SRDMeasurement(FrameworkModel):
    """System Reasoning Diversity measurement for a task.

    SRD = 0.8 * text_diversity + 0.2 * VDI (Section 10.1).
    """

    task_id: str
    agent_count: int
    text_diversity: float = Field(ge=0.0, le=1.0)  # Mean pairwise TF-IDF cosine distance
    vdi: VDIMeasurement | None = None
    composite_srd: float = Field(ge=0.0, le=1.0)  # Weighted composite
    timestamp: datetime

    @property
    def health_status(self) -> str:
        """Classify SRD health (Section 10.1 thresholds)."""
        if self.composite_srd < 0.3:
            return "critical"  # Below floor — diversity collapse
        if self.composite_srd < 0.4:
            return "warning"   # Approaching collapse
        if self.composite_srd <= 0.7:
            return "healthy"
        if self.composite_srd <= 0.9:
            return "high"
        return "incoherent"    # Above ceiling


class DiversitySnapshot(FrameworkModel):
    """Complete diversity state at a point in time.

    Logged to diversity.jsonl after every multi-agent task.
    """

    task_id: str
    srd: SRDMeasurement
    stagnation_signals: list[StagnationSignal]
    timestamp: datetime
    agent_outputs_hash: str  # SHA-256 of concatenated outputs for reproducibility
