"""Population evolution models.
Spec reference: Section 8.2 (Dual-Copy, population_mode),
Section 13.3 (Metacognitive Monitoring — gap_monitoring).

Phase 8 additions: PopulationRun, CandidateResult, GapMetrics,
GapCalibrationAction.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import Field

from .base import FrameworkModel, IdentifiableModel, generate_id


class PopulationOutcome(StrEnum):
    """Outcome of a population evolution run."""

    PROMOTED = "promoted"
    ALL_REJECTED = "all_rejected"
    HELD = "held"
    CANCELLED = "cancelled"


class CandidateResult(FrameworkModel):
    """Result for a single candidate in a population run.

    Stores the candidate ID, evaluation scores, and rank.
    """

    candidate_id: str
    proposal_id: str
    evaluation_id: str = ""
    overall_score: float = Field(ge=0.0, le=1.0, default=0.0)
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    rank: int = 0
    promoted: bool = False
    rejection_reason: str = ""


class PopulationRun(IdentifiableModel):
    """A population-based evolution run (Section 8.2 population_mode).

    Generates multiple candidate forks, evaluates all, selects best.
    Tournament selection: best fork wins across multi-dimensional evaluation.

    Persisted to: instances/{domain}/state/evolution/populations/{id}.yaml
    """

    id: str = Field(default_factory=lambda: generate_id("pop"))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trigger_proposal_id: str
    population_size: int = Field(ge=2, le=10, default=3)
    candidates: list[CandidateResult] = Field(default_factory=list)
    outcome: PopulationOutcome = PopulationOutcome.CANCELLED
    winner_id: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    reason: str = ""


class GapCalibrationAction(StrEnum):
    """Action taken by gap monitor to recalibrate evaluation thresholds."""

    TIGHTEN = "tighten"
    LOOSEN = "loosen"
    HOLD = "hold"


class GapMetrics(IdentifiableModel):
    """Generation-verification gap metrics (Section 13.3).

    Tracks whether evolution approvals are actually reliable:
    - False positives: approved changes that turned out worse
    - False negatives: rejected changes that would have been beneficial

    Persisted to: instances/{domain}/state/evolution/gap_metrics.yaml
    """

    id: str = Field(default_factory=lambda: generate_id("gap"))
    total_promotions: int = 0
    total_rejections: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    fp_rate: float = 0.0
    fn_rate: float = 0.0
    last_calibration_action: GapCalibrationAction = GapCalibrationAction.HOLD
    threshold_adjustments: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
