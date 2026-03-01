"""Governance models for Phase 5.
Spec reference: Section 7.3 (Quorum Sensing), Section 14 (Self-Governance).

Phase 5 additions: QuorumEligibility, QuorumSession, ObjectiveAlignmentResult,
RiskDimension, RiskScore, RiskAssessment, AlignmentCheckResult, HumanDecision.

Literature basis:
- Anthropic 2024: 78% alignment faking under RL pressure
- COCOA (EMNLP 2025): co-evolving constitutions
- arXiv:2506.23844: recursive objective shift from auto-summarized reflections
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from .base import FrameworkModel, IdentifiableModel


class QuorumSessionStatus(StrEnum):
    """Quorum session lifecycle states (FM-P5-N02-FIX)."""

    COLLECTING = "collecting"
    TALLIED = "tallied"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"


class RiskDimension(StrEnum):
    """10 risk dimensions from Section 14.4."""

    OPERATIONAL = "operational"
    EVOLUTIONARY = "evolutionary"
    DIVERSITY = "diversity"
    KNOWLEDGE = "knowledge"
    RESOURCE = "resource"
    GOVERNANCE = "governance"
    ALIGNMENT = "alignment"
    CALIBRATION = "calibration"
    ENVIRONMENT = "environment"
    COMPLEXITY = "complexity"


class RiskLevel(StrEnum):
    """Risk threshold levels from Section 14.4."""

    HEALTHY = "healthy"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"


class AlignmentCheckType(StrEnum):
    """Types of alignment verification checks from Section 14.3."""

    BEHAVIORAL_CONSISTENCY = "behavioral_consistency"
    CAPABILITY_ELICITATION = "capability_elicitation"
    CROSS_AGENT_MONITORING = "cross_agent_monitoring"
    RED_TEAM = "red_team"


class QuorumEligibility(FrameworkModel):
    """Determines whether a role composition is eligible to vote.

    Anti-gaming rules from Section 7.3:
    - Role must be >= min_tasks_for_voter old
    - Role must not share lineage with another voter
    - Role must not have been created by the same evolution as another voter
    """

    role_name: str
    task_count: int = Field(ge=0)
    lineage_id: str = ""
    created_by_evolution: str = ""
    is_scout: bool = False
    eligible: bool = False
    rejection_reason: str = ""


class QuorumSession(IdentifiableModel):
    """A quorum voting session for a Tier 2 proposal.

    Lifecycle: COLLECTING -> TALLIED -> (APPROVED | REJECTED)

    Anti-gaming enforced:
    - Voters from different role compositions
    - Scout always gets a vote
    - Sealed votes (collected independently, revealed together)
    - Role maturity >= min_tasks_for_voter
    - Max 1 voter per role lineage
    - Roles from same evolution proposal can't both vote
    """

    proposal_id: str
    required_voters: int = Field(ge=3, default=3)
    threshold: float = Field(ge=0.0, le=1.0, default=0.67)
    eligible_voters: list[QuorumEligibility] = Field(default_factory=list)
    sealed_votes: list[str] = Field(default_factory=list)
    status: QuorumSessionStatus = QuorumSessionStatus.COLLECTING
    tally_approve: int = 0
    tally_reject: int = 0
    scout_voted: bool = False
    completed_at: datetime | None = None


class ObjectiveAlignmentResult(IdentifiableModel):
    """Result of an objective alignment check (Section 14.1).

    Produced by ObjectiveAnchor.check_alignment().
    """

    evolution_count_at_check: int
    recent_outcomes: list[str] = Field(default_factory=list)
    success_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    alignment_score: float = Field(ge=0.0, le=1.0, default=0.0)
    passed: bool = True
    detail: str = ""


class RiskScore(FrameworkModel):
    """Score for a single risk dimension."""

    dimension: RiskDimension
    score: float = Field(ge=0.0, le=1.0)
    level: RiskLevel = RiskLevel.HEALTHY
    detail: str = ""
    indicators: list[str] = Field(default_factory=list)


class RiskAssessment(IdentifiableModel):
    """Complete risk scorecard assessment (Section 14.4).

    Produced by RiskScorecard.compute().
    """

    dimension_scores: list[RiskScore] = Field(default_factory=list)
    aggregate_score: float = Field(ge=0.0, le=1.0, default=0.0)
    aggregate_level: RiskLevel = RiskLevel.HEALTHY
    governance_weight: float = 2.0
    alignment_weight: float = 2.0
    actions_required: list[str] = Field(default_factory=list)
    halted_operations: list[str] = Field(default_factory=list)


class AlignmentCheckResult(IdentifiableModel):
    """Result of an alignment verification check (Section 14.3).

    Produced by AlignmentVerifier.run_checks().
    """

    check_type: AlignmentCheckType
    passed: bool = True
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    detail: str = ""
    flagged_agents: list[str] = Field(default_factory=list)


class AlignmentReport(IdentifiableModel):
    """Complete alignment verification report.

    Aggregates individual check results.
    """

    trigger: str = ""
    task_count_at_check: int = 0
    checks: list[AlignmentCheckResult] = Field(default_factory=list)
    overall_passed: bool = True
    flagged_agents: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class HumanDecision(IdentifiableModel):
    """A pending human decision (Section 16.3).

    Stored in state/governance/pending_human_decisions.yaml.
    Phase 5 creates the queue; Phase 6+ integrates with the run loop.
    """

    decision_type: str
    summary: str
    proposed_by: str
    urgency: str = "normal"
    quorum_result: str = ""
    blocking: bool = False
    blocking_tasks: list[str] = Field(default_factory=list)
    resolved: bool = False
    resolution: str = ""
    resolved_at: datetime | None = None
