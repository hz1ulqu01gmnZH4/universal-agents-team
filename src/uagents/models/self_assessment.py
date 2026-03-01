"""Self-capability assessment models.
Spec reference: Section 13 (Self-Capability Awareness).

Phase 2: Knowledge boundary map, confidence calibration, gap monitoring.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .base import FrameworkModel


class CapabilityMapEntry(FrameworkModel):
    """Performance record for a single task type.

    Tracked per task_type (from Orchestrator._classify_task_type).
    """

    task_type: str
    attempts: int = 0
    successes: int = 0  # review verdict == "pass" or "pass_with_notes"
    failures: int = 0   # review verdict == "fail"
    avg_tokens: float = 0.0
    token_count: int = 0           # FM-87: count of records with non-zero tokens
    avg_review_confidence: float = 0.0
    confidence_count: int = 0      # FM-93: count of records with non-zero confidence
    last_updated: datetime | None = None

    @property
    def success_rate(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.successes / self.attempts


class CapabilityMap(FrameworkModel):
    """Complete knowledge boundary map (Section 13.1).

    Persisted to state/self-assessment/capability-map.yaml.
    """

    entries: dict[str, CapabilityMapEntry] = {}  # task_type → entry
    blind_spots: list[str] = []  # Task types never attempted
    last_analysis: datetime | None = None

    def get_entry(self, task_type: str) -> CapabilityMapEntry:
        """Get or create entry for a task type."""
        if task_type not in self.entries:
            self.entries[task_type] = CapabilityMapEntry(task_type=task_type)
        return self.entries[task_type]


class CalibrationRecord(FrameworkModel):
    """Single calibration data point (Section 13.2).

    Recorded before each evolution: predicted confidence.
    Recorded after evaluation: actual improvement measured.
    """

    evolution_id: str
    predicted_confidence: float = Field(ge=0.0, le=1.0)
    actual_improvement: float | None = None  # None until evaluation completes
    calibration_error: float | None = None   # predicted - actual
    timestamp: datetime


class CalibrationState(FrameworkModel):
    """Persistent calibration state (Section 13.2).

    Persisted to state/self-assessment/calibration.yaml.
    """

    records: list[CalibrationRecord] = []
    running_ece: float = 0.0              # Rolling ECE over last 10 cycles
    confidence_deflation: float = 0.0     # Applied to all future confidence estimates
    evidence_threshold: float = 0.6       # Minimum evidence to approve evolutions
    overcalibrated: bool = False          # True if systematic overconfidence detected
    overcalibration_streak: int = 0       # Consecutive cycles where predicted > actual
    undercalibration_streak: int = 0     # FM-108: Consecutive cycles where predicted < actual

    @property
    def ece_alert(self) -> bool:
        """True if ECE exceeds 0.15 threshold (Huang et al. 2025)."""
        return self.running_ece > 0.15


class GapAssessment(FrameworkModel):
    """Generation-verification gap assessment (Section 13.3).

    Song et al. 2024: self-improvement is bounded by gap.
    If verifier_accuracy - generator_accuracy < 0.05, self-improvement unreliable.
    """

    verifier_accuracy: float = Field(ge=0.0, le=1.0)
    generator_accuracy: float = Field(ge=0.0, le=1.0)
    assessment_date: datetime
    benchmark_task_count: int  # How many tasks were used to compute this

    @property
    def gap_score(self) -> float:
        return self.verifier_accuracy - self.generator_accuracy

    @property
    def self_improvement_reliable(self) -> bool:
        """Gap must exceed minimum threshold (0.05) with sufficient data.

        FM-100: Requires at least 10 benchmark tasks to avoid unreliable
        gap estimates from small samples.
        """
        if self.benchmark_task_count < 10:
            return False  # Insufficient data for reliable assessment
        return self.gap_score >= 0.05
