"""Evolution engine models.
Spec reference: Section 7 (Evolution Engine), Section 8 (Dual-Copy)."""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum
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


class EvolutionProposal(IdentifiableModel):
    tier: EvolutionTier
    component: str  # File path being modified
    diff: str       # Unified diff
    rationale: str
    evidence: dict  # triggering_tasks, metrics, etc.
    estimated_risk: float = Field(ge=0.0, le=1.0)


class QuorumVote(FrameworkModel):
    """A single sealed vote in a quorum process."""

    voter_id: str
    voter_role: str
    vote: Literal["approve", "reject"]
    rationale: str
    timestamp: datetime


class QuorumResult(FrameworkModel):
    votes: list[QuorumVote]
    threshold: float
    approved: bool


class EvolutionRecord(IdentifiableModel):
    """Post-approval evolution record."""

    proposal: EvolutionProposal
    approved_by: str  # "auto (tier 3)", "quorum", "human"
    constitutional_check: Literal["pass", "fail"]
    rollback_commit: str  # Git SHA for rollback
    quorum: QuorumResult | None = None


class DualCopyCandidate(FrameworkModel):
    """A fork being evaluated in dual-copy bootstrapping."""

    evo_id: str
    fork_path: Path  # state/evolution/candidates/{evo-id}/
    modified_files: list[str]
    evaluation: dict  # capability, consistency, robustness scores
    promoted: bool = False
