"""Evolution engine models.
Spec reference: Section 7 (Evolution Engine), Section 8 (Dual-Copy).

Phase 4 additions: EvolutionLifecycleState, EvaluationDimension,
EvaluationResult, ArchiveCell, ArchiveEntry, ObservationTrigger,
EvolutionOutcome.

Literature basis:
- Darwin Godel Machine: 20%→50% SWE-bench (population + dual-copy)
- Song et al. 2024: Generation-verification gap (independent evaluator)
- AlphaEvolve (DeepMind): Evolutionary search in code space
- ADAS (ICLR 2025): Meta-agent archive of agentic designs
"""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field

from .base import FrameworkModel, IdentifiableModel


class EvolutionTier(IntEnum):
    """Evolution tiers matching protection rings."""

    CONSTITUTIONAL = 0  # Human only — CONSTITUTION.md
    FRAMEWORK = 1       # Human approval required
    ORGANIZATIONAL = 2  # Quorum approval
    OPERATIONAL = 3     # Auto-approved


class EvolutionLifecycleState(StrEnum):
    """8-step evolution lifecycle states (Section 7.2)."""

    OBSERVE = "observe"       # 1. Detect problem or improvement opportunity
    ATTRIBUTE = "attribute"   # 2. Root-cause analysis with evidence
    PROPOSE = "propose"       # 3. Generate candidate fix with diffs
    EVALUATE = "evaluate"     # 4. Constitutional check, multi-dimensional eval
    APPROVE = "approve"       # 5. Tier-based approval
    COMMIT = "commit"         # 6. Git commit with structured message
    VERIFY = "verify"         # 7. Post-commit verification
    LOG = "log"               # 8. Full record to logs/evolution/

    # Terminal states
    REJECTED = "rejected"     # Proposal rejected at any stage
    ROLLED_BACK = "rolled_back"  # Promoted but verification failed


class ObservationTrigger(StrEnum):
    """What triggered the evolution observation (Section 7.2 step 1)."""

    TASK_FAILURE = "task_failure"           # Task completed with review fail
    STAGNATION = "stagnation"              # StagnationDetector signal
    DIVERSITY_DROP = "diversity_drop"       # SRD below floor
    CAPABILITY_GAP = "capability_gap"       # CapabilityTracker blind spot
    PERFORMANCE_DECLINE = "performance_decline"  # Declining success rate
    CONTEXT_PRESSURE = "context_pressure"   # Chronic high context utilization
    MANUAL = "manual"                       # Human-initiated


class EvaluationDimension(StrEnum):
    """6 evaluation dimensions for dual-copy assessment (Section 8.2)."""

    CAPABILITY = "capability"       # Does it perform tasks better?
    CONSISTENCY = "consistency"     # Reproducible results across runs?
    ROBUSTNESS = "robustness"       # Handles edge cases?
    PREDICTABILITY = "predictability"  # Can we anticipate when it will fail?
    SAFETY = "safety"               # Stays within constitutional bounds?
    DIVERSITY = "diversity"         # Maintains SRD above floor?


class EvolutionOutcome(StrEnum):
    """Final outcome of an evolution attempt."""

    PROMOTED = "promoted"       # Fork replaced active config
    ROLLED_BACK = "rolled_back"  # Fork discarded after failed verification
    REJECTED = "rejected"       # Proposal rejected before fork
    HELD = "held"               # Marginal improvement — held for human review


class EvolutionProposal(IdentifiableModel):
    """An agent's proposal to modify a component (Section 7.2 step 3).

    Every proposal includes the tier, component path, unified diff,
    rationale, evidence, and estimated risk. The constitutional check
    validates against Ring 0/1 protection before evaluation.

    Persisted to: instances/{domain}/state/evolution/proposals/{id}.yaml
    """

    tier: EvolutionTier
    component: str  # File path being modified (relative to instance root)
    diff: str       # Unified diff — what changes
    rationale: str  # Required: why this change is needed
    # FM-P4-47-FIX: Keep evidence as untyped dict for backward compatibility
    # with existing callers (e.g., SkillLibrary._log_ring_transition)
    evidence: dict = Field(default_factory=dict)  # triggering_tasks, metrics, etc.
    estimated_risk: float = Field(ge=0.0, le=1.0)
    trigger: ObservationTrigger = ObservationTrigger.MANUAL
    trigger_detail: str = ""  # e.g., task_id that failed, stagnation signal type
    lifecycle_state: EvolutionLifecycleState = EvolutionLifecycleState.OBSERVE


class DimensionScore(FrameworkModel):
    """Score for a single evaluation dimension."""

    dimension: EvaluationDimension
    score: float = Field(ge=0.0, le=1.0)
    detail: str = ""  # Explanation of score


class EvaluationResult(IdentifiableModel):
    """Result of multi-dimensional evaluation (Section 8.2 step 3).

    Contains per-dimension scores and an overall verdict.
    The verdict determines promote/rollback/hold.

    Persisted to: instances/{domain}/state/evolution/evaluations/{id}.yaml
    """

    proposal_id: str
    candidate_id: str  # DualCopyCandidate.evo_id
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    overall_score: float = Field(ge=0.0, le=1.0, default=0.0)
    verdict: EvolutionOutcome = EvolutionOutcome.REJECTED
    verdict_reason: str = ""
    evaluator_id: str = ""  # Agent that performed evaluation (independent!)


class QuorumVote(FrameworkModel):
    """A single sealed vote in a quorum process (Section 7.3).

    Phase 4: Stored but not used — quorum is Phase 5.
    """

    voter_id: str
    voter_role: str
    vote: Literal["approve", "reject"]
    rationale: str
    timestamp: datetime


class QuorumResult(FrameworkModel):
    """Result of a quorum vote (Section 7.3).

    Phase 4: Stored but not used — quorum is Phase 5.
    """

    votes: list[QuorumVote] = Field(default_factory=list)
    threshold: float = 0.67
    approved: bool = False


class EvolutionRecord(IdentifiableModel):
    """Post-approval evolution record (Section 7.2 step 8).

    The complete audit trail for a single evolution cycle.
    Includes the proposal, evaluation result, approval chain,
    commit reference, and verification result.

    Persisted to: instances/{domain}/state/evolution/records/{id}.yaml
    """

    proposal: EvolutionProposal
    evaluation: EvaluationResult | None = None
    approved_by: str  # "auto (tier 3)", "quorum", "human", "rejected", "held_for_human"
    constitutional_check: Literal["pass", "fail"]
    # FM-P4-17-FIX: Optional for rejected/held records that have no rollback point
    rollback_commit: str = ""  # Git SHA for rollback point (empty if rejected/held)
    evolution_commit: str = ""  # Git SHA of the evolution commit
    quorum: QuorumResult | None = None
    outcome: EvolutionOutcome = EvolutionOutcome.REJECTED
    verification_passed: bool = False


class DualCopyCandidate(FrameworkModel):
    """A fork being evaluated in dual-copy bootstrapping (Section 8.2).

    Created by DualCopyManager.create_fork(), populated during
    evaluation, and resolved by promote() or rollback().

    FM-P4-25-NOTE: fork_path changed from Path to str for YAML serialization
    compatibility with strict=True. No existing manifests need migration
    since Phase 4 is the first active use of DualCopyCandidate.

    Persisted to: instances/{domain}/state/evolution/candidates/{evo_id}/manifest.yaml
    """

    evo_id: str
    fork_path: str  # state/evolution/candidates/{evo-id}/ (string, not Path)
    source_files: list[str] = Field(default_factory=list)  # Files copied to fork
    modified_files: list[str] = Field(default_factory=list)  # Files modified in fork
    evaluation: dict[str, float] = Field(default_factory=dict)  # dimension -> score
    promoted: bool = False
    rolled_back: bool = False


class ArchiveCell(FrameworkModel):
    """A single cell in the MAP-Elites archive (Section 7.4).

    Indexed by (task_type, complexity). Stores the best-performing
    configuration found for this behavioral niche.
    """

    task_type: str  # "research", "engineering", "creative", "meta"
    complexity: str  # "simple", "moderate", "complex", "extreme"
    best_config: dict[str, str] = Field(default_factory=dict)  # topology, roles, etc.
    # DR-01-FIX: No upper bound — novelty bonus can push performance above 1.0
    performance: float = Field(ge=0.0, default=0.0)
    task_count: int = Field(ge=0, default=0)
    last_updated: datetime | None = None
    evolution_id: str = ""  # EvolutionRecord that set this cell


class MAPElitesState(FrameworkModel):
    """Full state of the MAP-Elites archive (Section 7.4).

    Persisted to: instances/{domain}/state/evolution/archive.yaml
    """

    cells: list[ArchiveCell] = Field(default_factory=list)
    novelty_bonus: float = 0.1
    total_evaluations: int = 0
    total_replacements: int = 0
