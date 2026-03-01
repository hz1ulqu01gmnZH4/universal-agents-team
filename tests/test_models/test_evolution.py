"""Tests for evolution engine models."""
from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError


def test_evolution_tiers():
    """Evolution tiers match protection rings."""
    from uagents.models.evolution import EvolutionTier

    assert EvolutionTier.CONSTITUTIONAL == 0
    assert EvolutionTier.FRAMEWORK == 1
    assert EvolutionTier.ORGANIZATIONAL == 2
    assert EvolutionTier.OPERATIONAL == 3


def test_evolution_proposal_creation():
    """EvolutionProposal can be created with required fields."""
    from uagents.models.evolution import EvolutionProposal, EvolutionTier

    proposal = EvolutionProposal(
        id="evo-20260228-001",
        created_at=datetime.utcnow(),
        tier=EvolutionTier.OPERATIONAL,
        component="roles/compositions/orchestrator.yaml",
        diff="--- a/old\n+++ b/new\n",
        rationale="Improve orchestrator config",
        evidence={"triggering_task": "task-001"},
        estimated_risk=0.2,
    )
    assert proposal.tier == EvolutionTier.OPERATIONAL
    assert proposal.estimated_risk == 0.2


def test_evolution_proposal_risk_range():
    """estimated_risk must be 0.0 to 1.0."""
    from uagents.models.evolution import EvolutionProposal, EvolutionTier

    with pytest.raises(ValidationError):
        EvolutionProposal(
            id="evo-001",
            created_at=datetime.utcnow(),
            tier=EvolutionTier.OPERATIONAL,
            component="test.yaml",
            diff="diff",
            rationale="test",
            evidence={},
            estimated_risk=1.5,
        )


def test_quorum_vote_creation():
    """QuorumVote can be created."""
    from uagents.models.evolution import QuorumVote

    vote = QuorumVote(
        voter_id="agent-001",
        voter_role="reviewer",
        vote="approve",
        rationale="Looks safe",
        timestamp=datetime.utcnow(),
    )
    assert vote.vote == "approve"


def test_dual_copy_candidate():
    """DualCopyCandidate tracks evaluation state."""
    from uagents.models.evolution import DualCopyCandidate

    candidate = DualCopyCandidate(
        evo_id="evo-001",
        fork_path="state/evolution/candidates/evo-001",
        modified_files=["roles/compositions/orchestrator.yaml"],
    )
    assert not candidate.promoted
    assert len(candidate.modified_files) == 1
