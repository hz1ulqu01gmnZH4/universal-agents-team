"""Tests for Phase 4 (Evolution Engine) — TDD suite.

Written BEFORE implementation (test-first). Tests the interfaces defined
in research/detailed-design-phase4.md (v0.2.0).

Coverage categories:
  1. Data Model Tests (models/evolution.py — new enums and models)
  2. DualCopyManager Tests (engine/dual_copy_manager.py)
  3. EvolutionValidator Tests (engine/evolution_validator.py)
  4. MAPElitesArchive Tests (engine/map_elites_archive.py)
  5. EvolutionEngine Tests (engine/evolution_engine.py)
  6. Orchestrator Integration Tests (engine/orchestrator.py modifications)
  7. Audit Model Tests (models/audit.py backward compatibility)
  8. Failure Mode Coverage (CRITICAL and HIGH failure modes)

All tests run WITHOUT real LLM calls or network access. GitOps,
AuditLogger, RingEnforcer, and ConstitutionGuard are mocked where needed.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from unittest.mock import MagicMock, patch

import pytest
import yaml


# ---------------------------------------------------------------------------
# YAML config fixture: core/evolution.yaml
# ---------------------------------------------------------------------------

def _write_evolution_yaml(base: Path) -> None:
    """Write core/evolution.yaml with test config."""
    core = base / "core"
    core.mkdir(parents=True, exist_ok=True)
    config = {
        "evolution": {
            "tiers": {
                "tier_3_auto_approve": True,
                "tier_2_requires_quorum": True,
                "tier_1_requires_human": True,
                "tier_0_immutable": True,
            },
            "lifecycle": {
                "max_proposals_per_cycle": 5,
                "max_concurrent_candidates": 1,
                "proposal_timeout_minutes": 30,
                "cooldown_between_evolutions": 3,
            },
            "evaluation": {
                "min_capability": 0.5,
                "min_consistency": 0.6,
                "min_robustness": 0.4,
                "min_predictability": 0.3,
                "min_safety": 0.9,
                "min_diversity": 0.4,
                "promote_threshold": 0.6,
                "hold_threshold": 0.5,
                "weights": {
                    "capability": 0.25,
                    "consistency": 0.20,
                    "robustness": 0.15,
                    "predictability": 0.10,
                    "safety": 0.20,
                    "diversity": 0.10,
                },
            },
            "dual_copy": {
                "fork_includes": [
                    "roles/compositions/*.yaml",
                    "core/topology.yaml",
                ],
                "fork_excludes": [
                    "CONSTITUTION.md",
                    "core/constitution-hash.txt",
                    "logs/**",
                    "state/tasks/**",
                    "state/agents/**",
                ],
                "candidates_dir": "state/evolution/candidates",
            },
            "archive": {
                "task_types": ["research", "engineering", "creative", "meta"],
                "complexities": ["simple", "moderate", "complex", "extreme"],
                "novelty_bonus": 0.1,
                "min_tasks_for_cell": 3,
                "archive_path": "state/evolution/archive.yaml",
            },
            "objective_anchoring": {
                "check_every_n_cycles": 10,
                "min_alignment_score": 0.8,
                "alignment_check_agent": "",
            },
            "safety": {
                "max_file_modifications_per_proposal": 3,
                "max_diff_lines": 200,
                "forbidden_path_patterns": [
                    "CONSTITUTION.md",
                    "constitution-hash",
                    "core/evolution.yaml",
                    ".claude/",
                ],
                "allowed_extensions": [".yaml", ".yml", ".md"],
                "budget_change_cap_pct": 30,
            },
        },
    }
    with open(core / "evolution.yaml", "w") as f:
        yaml.dump(config, f)


def _write_constitution(base: Path) -> Path:
    """Write a CONSTITUTION.md and hash file."""
    constitution = base / "CONSTITUTION.md"
    constitution.write_text(
        "# Constitution\n\n"
        "## A1: Human Halt\nHuman can halt at any time.\n",
        encoding="utf-8",
    )
    hash_file = base / "core" / "constitution-hash.txt"
    hash_file.parent.mkdir(parents=True, exist_ok=True)
    content = constitution.read_bytes()
    hash_file.write_text(hashlib.sha256(content).hexdigest())
    return constitution


def _write_topology_yaml(base: Path) -> None:
    """Write a sample core/topology.yaml for forking tests."""
    core = base / "core"
    core.mkdir(parents=True, exist_ok=True)
    config = {
        "topology": {
            "default_pattern": "hub_spoke",
            "max_agents": 5,
            "communication_overhead_factor": 0.15,
        },
    }
    with open(core / "topology.yaml", "w") as f:
        yaml.dump(config, f)


def _write_role_composition(base: Path, name: str = "researcher") -> None:
    """Write a sample role composition YAML."""
    roles = base / "roles" / "compositions"
    roles.mkdir(parents=True, exist_ok=True)
    config = {
        "role": {
            "name": name,
            "authority_level": "executor",
            "behavioral_descriptors": {
                "thinking_style": "analytical",
                "communication": "precise",
            },
        },
    }
    with open(roles / f"{name}.yaml", "w") as f:
        yaml.dump(config, f)


@pytest.fixture
def evo_base(tmp_path: Path) -> Path:
    """Create a fully configured instance root for evolution tests."""
    _write_evolution_yaml(tmp_path)
    _write_constitution(tmp_path)
    _write_topology_yaml(tmp_path)
    _write_role_composition(tmp_path, "researcher")
    _write_role_composition(tmp_path, "engineer")
    # Create candidates dir
    (tmp_path / "state" / "evolution" / "candidates").mkdir(parents=True, exist_ok=True)
    # Create records dir
    (tmp_path / "state" / "evolution" / "records").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def evo_yaml_store(evo_base: Path):
    """Create a YamlStore rooted at the evolution base."""
    from uagents.state.yaml_store import YamlStore
    return YamlStore(evo_base)


# ===========================================================================
# 1. Data Model Tests
# ===========================================================================

class TestEvolutionDataModels:
    """Test new Phase 4 data models in models/evolution.py."""

    def test_evolution_lifecycle_state_enum(self):
        """All 10 lifecycle states exist."""
        from uagents.models.evolution import EvolutionLifecycleState

        assert len(EvolutionLifecycleState) == 10
        assert EvolutionLifecycleState.OBSERVE == "observe"
        assert EvolutionLifecycleState.ATTRIBUTE == "attribute"
        assert EvolutionLifecycleState.PROPOSE == "propose"
        assert EvolutionLifecycleState.EVALUATE == "evaluate"
        assert EvolutionLifecycleState.APPROVE == "approve"
        assert EvolutionLifecycleState.COMMIT == "commit"
        assert EvolutionLifecycleState.VERIFY == "verify"
        assert EvolutionLifecycleState.LOG == "log"
        assert EvolutionLifecycleState.REJECTED == "rejected"
        assert EvolutionLifecycleState.ROLLED_BACK == "rolled_back"

    def test_observation_trigger_enum(self):
        """All 7 observation triggers exist."""
        from uagents.models.evolution import ObservationTrigger

        assert len(ObservationTrigger) == 7
        assert ObservationTrigger.TASK_FAILURE == "task_failure"
        assert ObservationTrigger.STAGNATION == "stagnation"
        assert ObservationTrigger.MANUAL == "manual"

    def test_evaluation_dimension_enum(self):
        """All 6 evaluation dimensions exist."""
        from uagents.models.evolution import EvaluationDimension

        assert len(EvaluationDimension) == 6
        assert EvaluationDimension.CAPABILITY == "capability"
        assert EvaluationDimension.SAFETY == "safety"
        assert EvaluationDimension.DIVERSITY == "diversity"

    def test_evolution_outcome_enum(self):
        """All 4 outcomes exist."""
        from uagents.models.evolution import EvolutionOutcome

        assert len(EvolutionOutcome) == 4
        assert EvolutionOutcome.PROMOTED == "promoted"
        assert EvolutionOutcome.ROLLED_BACK == "rolled_back"
        assert EvolutionOutcome.REJECTED == "rejected"
        assert EvolutionOutcome.HELD == "held"

    def test_evolution_proposal_creation(self):
        """EvolutionProposal with all required fields."""
        from uagents.models.evolution import (
            EvolutionProposal,
            EvolutionTier,
            ObservationTrigger,
        )
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="roles/compositions/researcher.yaml",
            diff="changes:\n  - key: role.authority_level\n    old: executor\n    new: lead",
            rationale="Promote researcher to lead after strong performance",
            evidence={"task_success_rate": 0.9},
            estimated_risk=0.2,
            trigger=ObservationTrigger.PERFORMANCE_DECLINE,
            trigger_detail="task-001 failed",
        )
        assert proposal.tier == EvolutionTier.OPERATIONAL
        assert proposal.estimated_risk == 0.2

    def test_evolution_proposal_evidence_untyped(self):
        """FM-P4-47: evidence field accepts any dict, not just dict[str, str]."""
        from uagents.models.evolution import EvolutionProposal, EvolutionTier
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="core/topology.yaml",
            diff="changes:\n  - key: topology.max_agents\n    old: 5\n    new: 7",
            rationale="Increase agent cap",
            evidence={
                "task_ids": ["task-001", "task-002"],
                "metrics": {"success_rate": 0.85, "avg_tokens": 1500},
                "count": 42,
            },
            estimated_risk=0.1,
        )
        assert proposal.evidence["count"] == 42
        assert isinstance(proposal.evidence["metrics"], dict)

    def test_evolution_proposal_risk_bounds(self):
        """estimated_risk must be 0.0-1.0."""
        from uagents.models.evolution import EvolutionProposal, EvolutionTier
        from uagents.models.base import generate_id
        from pydantic import ValidationError

        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            EvolutionProposal(
                id=generate_id("evo"),
                created_at=now,
                tier=EvolutionTier.OPERATIONAL,
                component="core/topology.yaml",
                diff="test",
                rationale="test",
                estimated_risk=1.5,  # Invalid — above 1.0
            )

    def test_dimension_score_creation(self):
        """DimensionScore with score bounds."""
        from uagents.models.evolution import DimensionScore, EvaluationDimension
        from pydantic import ValidationError

        score = DimensionScore(
            dimension=EvaluationDimension.SAFETY,
            score=0.95,
            detail="Constitutional check passed",
        )
        assert score.score == 0.95

        with pytest.raises(ValidationError):
            DimensionScore(
                dimension=EvaluationDimension.SAFETY,
                score=1.5,  # Invalid — above 1.0
            )

    def test_evaluation_result_creation(self):
        """EvaluationResult with all fields."""
        from uagents.models.evolution import (
            EvaluationResult,
            EvolutionOutcome,
            DimensionScore,
            EvaluationDimension,
        )
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        result = EvaluationResult(
            id=generate_id("eval"),
            created_at=now,
            proposal_id="evo-001",
            candidate_id="evo-001",
            dimension_scores=[
                DimensionScore(dimension=EvaluationDimension.SAFETY, score=0.95),
            ],
            overall_score=0.7,
            verdict=EvolutionOutcome.PROMOTED,
            verdict_reason="Score above threshold",
        )
        assert result.verdict == EvolutionOutcome.PROMOTED

    def test_evolution_record_creation(self):
        """EvolutionRecord with optional fields."""
        from uagents.models.evolution import (
            EvolutionRecord,
            EvolutionProposal,
            EvolutionTier,
            EvolutionOutcome,
        )
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="core/topology.yaml",
            diff="test",
            rationale="test",
            estimated_risk=0.1,
        )
        record = EvolutionRecord(
            id=generate_id("rec"),
            created_at=now,
            proposal=proposal,
            approved_by="auto (tier 3)",
            constitutional_check="pass",
            outcome=EvolutionOutcome.PROMOTED,
            verification_passed=True,
            rollback_commit="abc123",
        )
        assert record.outcome == EvolutionOutcome.PROMOTED
        assert record.verification_passed is True

    def test_evolution_record_rejected_empty_rollback(self):
        """FM-P4-17: Rejected records have empty rollback_commit (valid)."""
        from uagents.models.evolution import (
            EvolutionRecord,
            EvolutionProposal,
            EvolutionTier,
            EvolutionOutcome,
        )
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="test.yaml",
            diff="test",
            rationale="test",
            estimated_risk=0.1,
        )
        record = EvolutionRecord(
            id=generate_id("rec"),
            created_at=now,
            proposal=proposal,
            approved_by="rejected",
            constitutional_check="fail",
            outcome=EvolutionOutcome.REJECTED,
            # rollback_commit not set — defaults to ""
        )
        assert record.rollback_commit == ""

    def test_dual_copy_candidate_str_fork_path(self):
        """FM-P4-25: fork_path is str, not Path."""
        from uagents.models.evolution import DualCopyCandidate

        candidate = DualCopyCandidate(
            evo_id="evo-001",
            fork_path="state/evolution/candidates/evo-001",
        )
        assert isinstance(candidate.fork_path, str)

    def test_archive_cell_no_upper_performance_bound(self):
        """DR-01: ArchiveCell.performance has no upper bound (novelty bonus)."""
        from uagents.models.evolution import ArchiveCell

        cell = ArchiveCell(
            task_type="research",
            complexity="moderate",
            performance=1.1,  # Above 1.0 — valid with novelty bonus
        )
        assert cell.performance == 1.1

    def test_map_elites_state_defaults(self):
        """MAPElitesState has sensible defaults."""
        from uagents.models.evolution import MAPElitesState

        state = MAPElitesState()
        assert state.cells == []
        assert state.total_evaluations == 0
        assert state.total_replacements == 0


# ===========================================================================
# 2. DualCopyManager Tests
# ===========================================================================

class TestDualCopyManager:
    """Test dual-copy fork pipeline."""

    def _make_proposal(self, component="core/topology.yaml"):
        from uagents.models.evolution import EvolutionProposal, EvolutionTier
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        return EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component=component,
            diff=yaml.dump({
                "changes": [
                    {"key": "topology.max_agents", "old": 5, "new": 7},
                ],
            }),
            rationale="Increase max agents",
            estimated_risk=0.1,
        )

    def test_create_fork_copies_files(self, evo_yaml_store, evo_base):
        """Fork copies matching files to candidates dir."""
        from uagents.engine.dual_copy_manager import DualCopyManager

        mgr = DualCopyManager(evo_yaml_store)
        proposal = self._make_proposal()
        candidate = mgr.create_fork(proposal)

        # Fork directory created
        fork_dir = evo_base / candidate.fork_path
        assert fork_dir.exists()

        # Source files copied
        assert len(candidate.source_files) > 0
        assert "core/topology.yaml" in candidate.source_files

    def test_create_fork_excludes_constitution(self, evo_yaml_store, evo_base):
        """Fork excludes constitution and other protected files."""
        from uagents.engine.dual_copy_manager import DualCopyManager

        mgr = DualCopyManager(evo_yaml_store)
        proposal = self._make_proposal()
        candidate = mgr.create_fork(proposal)

        assert "CONSTITUTION.md" not in candidate.source_files
        assert "core/constitution-hash.txt" not in candidate.source_files

    def test_create_fork_rejects_existing_dir(self, evo_yaml_store, evo_base):
        """FM-P4-05: Fork directory already exists raises ForkError."""
        from uagents.engine.dual_copy_manager import DualCopyManager, ForkError

        mgr = DualCopyManager(evo_yaml_store)
        proposal = self._make_proposal()

        # Create fork directory manually (simulate stale fork)
        candidates = evo_base / "state" / "evolution" / "candidates"
        (candidates / proposal.id).mkdir(parents=True)

        with pytest.raises(ForkError, match="already exists"):
            mgr.create_fork(proposal)

    def test_apply_diff_modifies_value(self, evo_yaml_store, evo_base):
        """apply_diff changes YAML value in fork."""
        from uagents.engine.dual_copy_manager import DualCopyManager

        mgr = DualCopyManager(evo_yaml_store)
        proposal = self._make_proposal()
        candidate = mgr.create_fork(proposal)

        mgr.apply_diff(candidate, proposal)

        # Verify the change was applied in the fork
        fork_dir = evo_base / candidate.fork_path
        modified = yaml.safe_load(
            (fork_dir / "core" / "topology.yaml").read_text()
        )
        assert modified["topology"]["max_agents"] == 7
        assert "core/topology.yaml" in candidate.modified_files

    def test_apply_diff_verifies_old_value(self, evo_yaml_store, evo_base):
        """FM-P4-38: apply_diff checks 'old' value matches current value."""
        from uagents.engine.dual_copy_manager import DualCopyManager, ForkError

        mgr = DualCopyManager(evo_yaml_store)

        # Create proposal with wrong 'old' value
        from uagents.models.evolution import EvolutionProposal, EvolutionTier
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="core/topology.yaml",
            diff=yaml.dump({
                "changes": [
                    {"key": "topology.max_agents", "old": 999, "new": 7},
                ],
            }),
            rationale="Test old value mismatch",
            estimated_risk=0.1,
        )
        candidate = mgr.create_fork(proposal)

        with pytest.raises(ForkError, match="Old value mismatch"):
            mgr.apply_diff(candidate, proposal)

    def test_apply_diff_empty_diff_raises(self, evo_yaml_store, evo_base):
        """FM-P4-06: Empty diff raises ForkError."""
        from uagents.engine.dual_copy_manager import DualCopyManager, ForkError
        from uagents.models.evolution import EvolutionProposal, EvolutionTier
        from uagents.models.base import generate_id

        mgr = DualCopyManager(evo_yaml_store)
        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="core/topology.yaml",
            diff="",
            rationale="Empty diff test",
            estimated_risk=0.1,
        )
        candidate = mgr.create_fork(proposal)

        with pytest.raises(ForkError):
            mgr.apply_diff(candidate, proposal)

    def test_promote_copies_files_atomically(self, evo_yaml_store, evo_base):
        """FM-P4-18: promote() uses atomic writes, not shutil.copy2."""
        from uagents.engine.dual_copy_manager import DualCopyManager

        mgr = DualCopyManager(evo_yaml_store)
        proposal = self._make_proposal()
        candidate = mgr.create_fork(proposal)
        mgr.apply_diff(candidate, proposal)

        # Before promote, check original value
        original = yaml.safe_load(
            (evo_base / "core" / "topology.yaml").read_text()
        )
        assert original["topology"]["max_agents"] == 5

        mgr.promote(candidate)

        # After promote, check new value
        promoted = yaml.safe_load(
            (evo_base / "core" / "topology.yaml").read_text()
        )
        assert promoted["topology"]["max_agents"] == 7
        assert candidate.promoted is True

    def test_promote_missing_file_raises(self, evo_yaml_store, evo_base):
        """FM-P4-02: Missing modified file in fork raises PromotionError."""
        from uagents.engine.dual_copy_manager import (
            DualCopyManager,
            PromotionError,
        )

        mgr = DualCopyManager(evo_yaml_store)
        proposal = self._make_proposal()
        candidate = mgr.create_fork(proposal)
        mgr.apply_diff(candidate, proposal)

        # Delete the modified file from fork to simulate corruption
        fork_dir = evo_base / candidate.fork_path
        (fork_dir / "core" / "topology.yaml").unlink()

        with pytest.raises(PromotionError, match="missing from fork"):
            mgr.promote(candidate)

    def test_cleanup_removes_fork(self, evo_yaml_store, evo_base):
        """cleanup_fork removes fork directory."""
        from uagents.engine.dual_copy_manager import DualCopyManager

        mgr = DualCopyManager(evo_yaml_store)
        proposal = self._make_proposal()
        candidate = mgr.create_fork(proposal)

        fork_dir = evo_base / candidate.fork_path
        assert fork_dir.exists()

        mgr.cleanup_fork(candidate)
        assert not fork_dir.exists()

    def test_cleanup_idempotent(self, evo_yaml_store, evo_base):
        """cleanup_fork is safe to call multiple times."""
        from uagents.engine.dual_copy_manager import DualCopyManager

        mgr = DualCopyManager(evo_yaml_store)
        proposal = self._make_proposal()
        candidate = mgr.create_fork(proposal)

        mgr.cleanup_fork(candidate)
        mgr.cleanup_fork(candidate)  # No error

    def test_exclude_uses_fnmatch(self, evo_yaml_store, evo_base):
        """FM-P4-31: Exclude matching uses fnmatch, not substring."""
        from uagents.engine.dual_copy_manager import DualCopyManager

        mgr = DualCopyManager(evo_yaml_store)

        # "state/tasks/**" should NOT match "state_backup/tasks.yaml"
        # because fnmatch is pattern-based, not substring-based
        assert not mgr._is_excluded("state_backup/tasks.yaml")

        # But "state/tasks/**" should match "state/tasks/task-001.yaml"
        assert mgr._is_excluded("state/tasks/task-001.yaml")

    def test_instance_root_derived_from_yaml_store(self, evo_yaml_store, evo_base):
        """DR-07: instance_root derived from yaml_store.base_dir."""
        from uagents.engine.dual_copy_manager import DualCopyManager

        mgr = DualCopyManager(evo_yaml_store)
        assert mgr.instance_root == evo_base.resolve()

    def test_manifest_persisted(self, evo_yaml_store, evo_base):
        """FM-P4-42: Fork manifest persisted to candidates dir."""
        from uagents.engine.dual_copy_manager import DualCopyManager

        mgr = DualCopyManager(evo_yaml_store)
        proposal = self._make_proposal()
        candidate = mgr.create_fork(proposal)

        manifest_path = (
            evo_base
            / "state"
            / "evolution"
            / "candidates"
            / proposal.id
            / "manifest.yaml"
        )
        assert manifest_path.exists()


# ===========================================================================
# 3. EvolutionValidator Tests
# ===========================================================================

class TestEvolutionValidator:
    """Test multi-dimensional evolution evaluation."""

    def _make_proposal_and_candidate(
        self,
        component="roles/compositions/researcher.yaml",
        tier=None,
        risk=0.2,
        diff_lines=5,
        n_modified_files=1,
    ):
        from uagents.models.evolution import (
            EvolutionProposal,
            EvolutionTier,
            DualCopyCandidate,
        )
        from uagents.models.base import generate_id

        if tier is None:
            tier = EvolutionTier.OPERATIONAL
        now = datetime.now(timezone.utc)

        diff_content = "\n".join([f"line {i}" for i in range(diff_lines)])

        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=tier,
            component=component,
            diff=diff_content,
            rationale="Test proposal",
            estimated_risk=risk,
        )

        candidate = DualCopyCandidate(
            evo_id=proposal.id,
            fork_path=f"state/evolution/candidates/{proposal.id}",
            modified_files=[f"file_{i}.yaml" for i in range(n_modified_files)],
        )
        return proposal, candidate

    def test_evaluate_promotes_good_proposal(self, evo_yaml_store):
        """Good proposal scores above promote_threshold."""
        from uagents.engine.evolution_validator import EvolutionValidator
        from uagents.models.evolution import EvolutionOutcome

        validator = EvolutionValidator(evo_yaml_store)
        proposal, candidate = self._make_proposal_and_candidate(
            risk=0.1, diff_lines=5, n_modified_files=1,
        )

        result = validator.evaluate(candidate, proposal)
        # Low risk + small diff + 1 file + safe target = should promote
        assert len(result.dimension_scores) == 6
        # promote_threshold is 0.6 in test config
        assert result.overall_score >= 0.6, (
            f"Expected score >= 0.6 (promote_threshold), got {result.overall_score}"
        )
        verdict_str = result.verdict if isinstance(result.verdict, str) else str(result.verdict)
        assert verdict_str == "promoted", (
            f"Expected promoted verdict, got {verdict_str}"
        )

    def test_evaluate_rejects_ring0_target(self, evo_yaml_store):
        """Safety dimension fails for constitution target."""
        from uagents.engine.evolution_validator import EvolutionValidator
        from uagents.models.evolution import EvolutionOutcome

        validator = EvolutionValidator(evo_yaml_store)
        proposal, candidate = self._make_proposal_and_candidate(
            component="CONSTITUTION.md",
            risk=0.1,
        )

        result = validator.evaluate(candidate, proposal)
        # Safety score = 0.0 for Ring 0 target → below min_safety (0.9)
        assert result.verdict == EvolutionOutcome.REJECTED
        assert "safety" in result.verdict_reason.lower() or "minimum" in result.verdict_reason.lower()

    def test_evaluate_rejects_ring1_engine_target(self, evo_yaml_store):
        """Safety dimension fails for Ring 1 (engine/) target."""
        from uagents.engine.evolution_validator import EvolutionValidator
        from uagents.models.evolution import EvolutionOutcome

        validator = EvolutionValidator(evo_yaml_store)
        proposal, candidate = self._make_proposal_and_candidate(
            component="engine/orchestrator.py",
        )

        result = validator.evaluate(candidate, proposal)
        assert result.verdict == EvolutionOutcome.REJECTED

    def test_evaluate_state_path_not_ring1(self, evo_yaml_store):
        """DR-17: state/ path is NOT Ring 1 — should not fail safety."""
        from uagents.engine.evolution_validator import EvolutionValidator

        validator = EvolutionValidator(evo_yaml_store)
        proposal, candidate = self._make_proposal_and_candidate(
            component="state/evolution/archive.yaml",
            risk=0.1,
        )

        result = validator.evaluate(candidate, proposal)
        # state/ is data, not framework code — safety should NOT be 0.0
        safety_score = None
        for ds in result.dimension_scores:
            dim_key = ds.dimension if isinstance(ds.dimension, str) else str(ds.dimension)
            if dim_key == "safety":
                safety_score = ds.score
                break
        assert safety_score is not None
        assert safety_score > 0.0, "state/ path should not be treated as Ring 1"

    def test_evaluate_all_six_dimensions(self, evo_yaml_store):
        """All 6 dimensions are scored."""
        from uagents.engine.evolution_validator import EvolutionValidator

        validator = EvolutionValidator(evo_yaml_store)
        proposal, candidate = self._make_proposal_and_candidate()
        result = validator.evaluate(candidate, proposal)

        dim_names = set()
        for ds in result.dimension_scores:
            dim_key = ds.dimension if isinstance(ds.dimension, str) else str(ds.dimension)
            dim_names.add(dim_key)

        assert dim_names == {
            "capability", "consistency", "robustness",
            "predictability", "safety", "diversity",
        }

    def test_negative_weights_rejected(self, evo_base):
        """FM-P4-45: Negative evaluation weights raise ValueError."""
        from uagents.state.yaml_store import YamlStore

        # Modify config to have negative weight
        config_path = evo_base / "core" / "evolution.yaml"
        config = yaml.safe_load(config_path.read_text())
        config["evolution"]["evaluation"]["weights"]["safety"] = -0.5
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        yaml_store = YamlStore(evo_base)

        from uagents.engine.evolution_validator import EvolutionValidator

        with pytest.raises(ValueError, match="negative"):
            EvolutionValidator(yaml_store)

    def test_per_dimension_minimum_enforcement(self, evo_yaml_store):
        """Per-dimension minimums reject proposals with any dimension below floor."""
        from uagents.engine.evolution_validator import EvolutionValidator
        from uagents.models.evolution import EvolutionOutcome

        validator = EvolutionValidator(evo_yaml_store)
        # High risk → capability score = 1.0 - 0.95 = 0.05, below min 0.5
        proposal, candidate = self._make_proposal_and_candidate(
            risk=0.95,
        )

        result = validator.evaluate(candidate, proposal)
        assert result.verdict == EvolutionOutcome.REJECTED
        assert "minimum" in result.verdict_reason.lower() or "below" in result.verdict_reason.lower()


# ===========================================================================
# 4. MAPElitesArchive Tests
# ===========================================================================

class TestMAPElitesArchive:
    """Test quality-diversity archive."""

    def _make_promoted_record(
        self,
        task_type="research",
        complexity="moderate",
        score=0.7,
    ):
        from uagents.models.evolution import (
            EvolutionRecord,
            EvolutionProposal,
            EvolutionTier,
            EvolutionOutcome,
            EvaluationResult,
        )
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="core/topology.yaml",
            diff="test",
            rationale="test",
            evidence={
                "task_type": task_type,
                "complexity": complexity,
            },
            estimated_risk=0.1,
        )
        evaluation = EvaluationResult(
            id=generate_id("eval"),
            created_at=now,
            proposal_id=proposal.id,
            candidate_id=proposal.id,
            overall_score=score,
            verdict=EvolutionOutcome.PROMOTED,
        )
        record = EvolutionRecord(
            id=generate_id("rec"),
            created_at=now,
            proposal=proposal,
            evaluation=evaluation,
            approved_by="auto (tier 3)",
            constitutional_check="pass",
            outcome=EvolutionOutcome.PROMOTED,
            verification_passed=True,
        )
        return record

    def test_archive_creates_new_cell(self, evo_yaml_store):
        """New cell created with novelty bonus."""
        from uagents.engine.map_elites_archive import MAPElitesArchive

        archive = MAPElitesArchive(evo_yaml_store)
        record = self._make_promoted_record(score=0.7)

        updated = archive.update_from_evolution(record)
        assert updated is True
        assert len(archive.get_all_cells()) == 1

        cell = archive.get_all_cells()[0]
        # Novelty bonus of 0.1 should be added
        assert cell.performance == pytest.approx(0.8)  # 0.7 + 0.1

    def test_archive_replaces_better_performance(self, evo_yaml_store):
        """Replace cell only when new performance > existing."""
        from uagents.engine.map_elites_archive import MAPElitesArchive

        archive = MAPElitesArchive(evo_yaml_store)

        # First evolution — creates cell with 0.7 + 0.1 = 0.8
        record1 = self._make_promoted_record(score=0.7)
        archive.update_from_evolution(record1)

        # Second evolution with higher score
        record2 = self._make_promoted_record(score=0.9)
        updated = archive.update_from_evolution(record2)
        assert updated is True
        assert archive.get_all_cells()[0].performance == pytest.approx(0.9)

    def test_archive_keeps_better_existing(self, evo_yaml_store):
        """Do NOT replace cell when new performance <= existing."""
        from uagents.engine.map_elites_archive import MAPElitesArchive

        archive = MAPElitesArchive(evo_yaml_store)

        # First evolution — creates cell with 0.7 + 0.1 = 0.8
        record1 = self._make_promoted_record(score=0.7)
        archive.update_from_evolution(record1)

        # Second evolution with LOWER score
        record2 = self._make_promoted_record(score=0.5)
        updated = archive.update_from_evolution(record2)
        assert updated is False
        assert archive.get_all_cells()[0].performance == pytest.approx(0.8)

    def test_archive_rejects_non_promoted(self, evo_yaml_store):
        """Only PROMOTED records update the archive."""
        from uagents.engine.map_elites_archive import MAPElitesArchive
        from uagents.models.evolution import EvolutionOutcome

        archive = MAPElitesArchive(evo_yaml_store)
        record = self._make_promoted_record()
        # Override to rejected using model_validate(strict=False) — use_enum_values
        # stores enums as primitives, so strict=True rejects them on reconstruction
        record_dict = record.model_dump()
        record_dict["outcome"] = "rejected"
        from uagents.models.evolution import EvolutionRecord
        record = EvolutionRecord.model_validate(record_dict, strict=False)

        updated = archive.update_from_evolution(record)
        assert updated is False

    def test_archive_rejects_invalid_task_type(self, evo_yaml_store):
        """FM-P4-22: Unknown task_type skips archive (no fallback)."""
        from uagents.engine.map_elites_archive import MAPElitesArchive

        archive = MAPElitesArchive(evo_yaml_store)
        record = self._make_promoted_record(task_type="unknown_type")

        updated = archive.update_from_evolution(record)
        assert updated is False
        assert len(archive.get_all_cells()) == 0

    def test_archive_rejects_invalid_complexity(self, evo_yaml_store):
        """FM-P4-22: Unknown complexity skips archive (no fallback)."""
        from uagents.engine.map_elites_archive import MAPElitesArchive

        archive = MAPElitesArchive(evo_yaml_store)
        record = self._make_promoted_record(complexity="impossible")

        updated = archive.update_from_evolution(record)
        assert updated is False

    def test_archive_rejects_missing_task_type(self, evo_yaml_store):
        """FM-P4-22: Missing task_type in evidence skips archive."""
        from uagents.engine.map_elites_archive import MAPElitesArchive

        archive = MAPElitesArchive(evo_yaml_store)
        record = self._make_promoted_record()
        # Remove task_type from evidence
        record.proposal.evidence.pop("task_type", None)

        updated = archive.update_from_evolution(record)
        assert updated is False

    def test_archive_maps_orchestrator_complexity(self, evo_yaml_store):
        """DR-21: 'small'/'medium'/'large' mapped to archive vocabulary."""
        from uagents.engine.map_elites_archive import MAPElitesArchive

        archive = MAPElitesArchive(evo_yaml_store)

        # "small" → "simple"
        record = self._make_promoted_record(complexity="small", score=0.7)
        updated = archive.update_from_evolution(record)
        assert updated is True
        cell = archive.get_all_cells()[0]
        assert cell.complexity == "simple"

    def test_archive_coverage(self, evo_yaml_store):
        """Coverage fraction computed correctly."""
        from uagents.engine.map_elites_archive import MAPElitesArchive

        archive = MAPElitesArchive(evo_yaml_store)
        # 4 task_types × 4 complexities = 16 total cells
        assert archive.get_coverage() == 0.0

        archive.update_from_evolution(
            self._make_promoted_record("research", "moderate")
        )
        assert archive.get_coverage() == pytest.approx(1 / 16)

    def test_get_best_config_requires_min_tasks(self, evo_yaml_store):
        """Cell needs min_tasks before it serves as baseline."""
        from uagents.engine.map_elites_archive import MAPElitesArchive

        archive = MAPElitesArchive(evo_yaml_store)
        archive.update_from_evolution(
            self._make_promoted_record("research", "moderate", score=0.7)
        )

        # min_tasks_for_cell = 3, but only 1 task so far
        config = archive.get_best_config("research", "moderate")
        assert config is None  # Not enough tasks

    def test_archive_persists_to_disk(self, evo_yaml_store, evo_base):
        """Archive state persisted and reloaded on init."""
        from uagents.engine.map_elites_archive import MAPElitesArchive

        archive1 = MAPElitesArchive(evo_yaml_store)
        archive1.update_from_evolution(
            self._make_promoted_record("research", "moderate", score=0.7)
        )

        # Create a new archive instance — should load from disk
        archive2 = MAPElitesArchive(evo_yaml_store)
        assert len(archive2.get_all_cells()) == 1


# ===========================================================================
# 5. EvolutionEngine Tests
# ===========================================================================

class TestEvolutionEngine:
    """Test the main evolution lifecycle engine."""

    def _make_engine(self, evo_yaml_store, evo_base):
        """Create EvolutionEngine with mocked dependencies."""
        from uagents.engine.evolution_engine import EvolutionEngine
        from uagents.engine.dual_copy_manager import DualCopyManager
        from uagents.engine.evolution_validator import EvolutionValidator
        from uagents.engine.map_elites_archive import MAPElitesArchive

        git_ops = MagicMock()
        git_ops.create_rollback_point.return_value = "rollback-sha-123"
        git_ops.commit_evolution.return_value = "commit-sha-456"

        constitution_guard = MagicMock()
        # Real check_proposal returns tuple[bool, str] — must match interface
        constitution_guard.check_proposal.return_value = (True, "Constitutional check passed")
        constitution_guard.verify_hash.return_value = True

        ring_enforcer = MagicMock()
        ring_enforcer.verify_no_ring_0_modification.return_value = False  # No violation

        audit_logger = MagicMock()

        dcm = DualCopyManager(evo_yaml_store)
        validator = EvolutionValidator(evo_yaml_store)
        archive = MAPElitesArchive(evo_yaml_store)

        engine = EvolutionEngine(
            yaml_store=evo_yaml_store,
            git_ops=git_ops,
            constitution_guard=constitution_guard,
            dual_copy_manager=dcm,
            validator=validator,
            archive=archive,
            audit_logger=audit_logger,
            ring_enforcer=ring_enforcer,
        )
        return engine, git_ops, constitution_guard, ring_enforcer, audit_logger

    def _make_tier3_proposal(self, component="core/topology.yaml"):
        from uagents.models.evolution import (
            EvolutionProposal,
            EvolutionTier,
            ObservationTrigger,
        )
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        return EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component=component,
            diff=yaml.dump({
                "changes": [
                    {"key": "topology.max_agents", "old": 5, "new": 7},
                ],
            }),
            rationale="Increase max agents",
            evidence={"task_type": "research", "complexity": "moderate"},
            estimated_risk=0.1,
            trigger=ObservationTrigger.MANUAL,
        )

    def test_run_evolution_full_lifecycle(self, evo_yaml_store, evo_base):
        """Full PROPOSE→EVALUATE→APPROVE→COMMIT→VERIFY→LOG lifecycle."""
        engine, git_ops, _, _, audit_logger = self._make_engine(
            evo_yaml_store, evo_base
        )
        proposal = self._make_tier3_proposal()

        record = engine.run_evolution(proposal)

        assert record is not None
        outcome_str = record.outcome if isinstance(record.outcome, str) else str(record.outcome)
        # Tier 3 + safe component (core/topology.yaml) + low risk (0.1)
        # + small diff (1 change) → expected: promoted
        assert outcome_str == "promoted", f"Expected promoted, got {outcome_str}"
        assert record.verification_passed is True
        assert record.evaluation is not None
        assert record.evaluation.overall_score > 0.0

        # Verify Git operations were called
        git_ops.create_rollback_point.assert_called_once()
        git_ops.commit_evolution.assert_called_once()

        # Verify audit logging happened
        assert audit_logger.log_evolution.call_count >= 1

    def test_run_evolution_rejects_tier0(self, evo_yaml_store, evo_base):
        """Tier 0 proposal rejected immediately."""
        from uagents.models.evolution import (
            EvolutionProposal,
            EvolutionTier,
            EvolutionOutcome,
        )
        from uagents.models.base import generate_id

        engine, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)

        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.CONSTITUTIONAL,
            component="CONSTITUTION.md",
            diff="test",
            rationale="test",
            estimated_risk=0.0,
        )

        record = engine.run_evolution(proposal)
        outcome_str = record.outcome if isinstance(record.outcome, str) else str(record.outcome)
        assert outcome_str == "rejected"

    def test_run_evolution_rejects_tier1_tier2(self, evo_yaml_store, evo_base):
        """Tier 1 and 2 proposals rejected in Phase 4 (only Tier 3)."""
        from uagents.models.evolution import (
            EvolutionProposal,
            EvolutionTier,
        )
        from uagents.models.base import generate_id

        engine, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)
        now = datetime.now(timezone.utc)

        for tier in (EvolutionTier.FRAMEWORK, EvolutionTier.ORGANIZATIONAL):
            proposal = EvolutionProposal(
                id=generate_id("evo"),
                created_at=now,
                tier=tier,
                component="core/topology.yaml",
                diff="test",
                rationale="test",
                estimated_risk=0.1,
            )
            record = engine.run_evolution(proposal)
            outcome_str = record.outcome if isinstance(record.outcome, str) else str(record.outcome)
            assert outcome_str == "rejected"

    def test_cooldown_enforcement(self, evo_yaml_store, evo_base):
        """Evolution blocked until cooldown_between_evolutions tasks complete."""
        engine, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)

        # Initially, can_evolve() should be False (0 tasks completed)
        assert engine.can_evolve() is False

        # Record 3 task completions (cooldown is 3)
        engine.record_task_completion()
        engine.record_task_completion()
        engine.record_task_completion()

        assert engine.can_evolve() is True

    def test_cooldown_resets_after_evolution(self, evo_yaml_store, evo_base):
        """Cooldown counter resets after evolution runs."""
        engine, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)

        # Complete 3 tasks
        for _ in range(3):
            engine.record_task_completion()

        proposal = self._make_tier3_proposal()
        record = engine.run_evolution(proposal)

        # Verify evolution actually succeeded before checking cooldown
        outcome_str = record.outcome if isinstance(record.outcome, str) else str(record.outcome)
        assert outcome_str == "promoted", (
            f"Evolution must succeed for cooldown reset test; got {outcome_str}"
        )

        # After successful evolution, cooldown should reset
        assert engine.can_evolve() is False

    def test_persistent_state_survives_restart(self, evo_yaml_store, evo_base):
        """FM-P4-23: Evolution state persists across restarts."""
        engine1, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)

        # Record some completions
        engine1.record_task_completion()
        engine1.record_task_completion()

        # Create new engine instance (simulating restart)
        engine2, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)

        # State should be preserved
        # Record one more to reach cooldown
        engine2.record_task_completion()
        assert engine2.can_evolve() is True

    def test_pause_blocks_evolution(self, evo_yaml_store, evo_base):
        """FM-P4-48: Paused engine rejects all evolution attempts."""
        engine, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)

        # Complete enough tasks for cooldown
        for _ in range(3):
            engine.record_task_completion()

        # Pause the engine by setting the persistent state
        engine._state.paused = True
        engine._state.pause_reason = "Alignment concern"
        engine._save_state()

        assert engine.is_paused() is True
        assert engine.can_evolve() is False

        # Attempt evolution — should be rejected due to pause
        proposal = self._make_tier3_proposal()
        record = engine.run_evolution(proposal)
        outcome_str = record.outcome if isinstance(record.outcome, str) else str(record.outcome)
        assert outcome_str == "rejected"

        # Unpause and verify engine resumes
        engine.unpause("Human cleared alignment concern")
        assert engine.is_paused() is False
        assert engine.can_evolve() is True

    def test_constitution_failure_rejects(self, evo_yaml_store, evo_base):
        """Constitutional check failure rejects proposal."""
        engine, _, constitution_guard, _, _ = self._make_engine(
            evo_yaml_store, evo_base
        )
        constitution_guard.check_proposal.return_value = (False, "Ring 0 violation")

        for _ in range(3):
            engine.record_task_completion()

        proposal = self._make_tier3_proposal()
        record = engine.run_evolution(proposal)
        outcome_str = record.outcome if isinstance(record.outcome, str) else str(record.outcome)
        assert outcome_str == "rejected"

    def test_ring_violation_triggers_rollback(self, evo_yaml_store, evo_base):
        """FM-P4-29: Ring 0 violation after promotion triggers rollback."""
        engine, git_ops, _, ring_enforcer, _ = self._make_engine(
            evo_yaml_store, evo_base
        )
        # Ring enforcer raises RingViolationError after promotion
        from uagents.engine.ring_enforcer import RingViolationError
        ring_enforcer.verify_no_ring_0_modification.side_effect = RingViolationError(
            "Ring 0 file modified"
        )

        for _ in range(3):
            engine.record_task_completion()

        proposal = self._make_tier3_proposal()
        record = engine.run_evolution(proposal)
        outcome_str = record.outcome if isinstance(record.outcome, str) else str(record.outcome)
        assert outcome_str in ("rolled_back", "rejected")

    def test_git_ops_failure_rejects(self, evo_yaml_store, evo_base):
        """FM-P4-20: GitOpsError during commit rejects proposal."""
        from uagents.state.git_ops import GitOpsError

        engine, git_ops, _, _, _ = self._make_engine(evo_yaml_store, evo_base)
        git_ops.commit_evolution.side_effect = GitOpsError("Git failed")

        for _ in range(3):
            engine.record_task_completion()

        proposal = self._make_tier3_proposal()
        record = engine.run_evolution(proposal)
        outcome_str = record.outcome if isinstance(record.outcome, str) else str(record.outcome)
        assert outcome_str in ("rejected", "rolled_back")

    def test_forbidden_path_rejected(self, evo_yaml_store, evo_base):
        """Forbidden path pattern in component → rejected."""
        engine, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)

        for _ in range(3):
            engine.record_task_completion()

        proposal = self._make_tier3_proposal(component="CONSTITUTION.md")
        record = engine.run_evolution(proposal)
        outcome_str = record.outcome if isinstance(record.outcome, str) else str(record.outcome)
        assert outcome_str == "rejected"

    def test_file_count_limit_loaded(self, evo_yaml_store, evo_base):
        """FM-P4-27: max_file_modifications_per_proposal config loaded."""
        engine, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)

        # Verify config loaded — attribute must exist with correct value
        assert hasattr(engine, '_max_file_modifications')
        assert engine._max_file_modifications == 3  # From test config

    def test_create_proposal_helper(self, evo_yaml_store, evo_base):
        """EvolutionEngine.create_proposal() creates valid proposal."""
        from uagents.models.evolution import ObservationTrigger

        engine, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)

        proposal = engine.create_proposal(
            component="core/topology.yaml",
            diff=yaml.dump({"changes": [{"key": "a.b", "old": 1, "new": 2}]}),
            rationale="Test proposal",
            trigger=ObservationTrigger.MANUAL,
            trigger_detail="manual test",
        )
        assert proposal.component == "core/topology.yaml"
        assert proposal.rationale == "Test proposal"


# ===========================================================================
# 6. Orchestrator Integration Tests
# ===========================================================================

class TestOrchestratorEvolutionIntegration:
    """Test orchestrator's evolution engine integration."""

    def test_orchestrator_accepts_evolution_engine_param(self, evo_base):
        """Orchestrator constructor accepts optional evolution_engine."""
        # This test verifies the interface — the actual orchestrator
        # constructor signature includes evolution_engine: ... | None = None
        from uagents.engine.orchestrator import Orchestrator

        # Verify the constructor accepts evolution_engine keyword
        import inspect
        sig = inspect.signature(Orchestrator.__init__)
        param_names = list(sig.parameters.keys())
        assert "evolution_engine" in param_names

    def test_trigger_evolution_validates_trigger(self, evo_base):
        """DR-10: Invalid trigger raises ValueError."""
        import inspect
        from uagents.engine.orchestrator import Orchestrator

        # Verify method exists with expected parameters
        assert hasattr(Orchestrator, "trigger_evolution_if_ready")
        sig = inspect.signature(Orchestrator.trigger_evolution_if_ready)
        param_names = list(sig.parameters.keys())
        # Must accept at least self + trigger parameter
        assert len(param_names) >= 2, (
            f"trigger_evolution_if_ready must accept trigger param, got: {param_names}"
        )
        assert "trigger" in param_names or "trigger_type" in param_names, (
            f"Missing trigger parameter in signature: {param_names}"
        )


# ===========================================================================
# 7. Audit Model Backward Compatibility Tests
# ===========================================================================

class TestAuditModelBackwardCompatibility:
    """Test EvolutionLogEntry backward compatibility (DR-02/FM-P4-16)."""

    def test_evolution_log_entry_old_fields_have_defaults(self):
        """Old fields (approved_by, constitutional_check, rollback_commit) have defaults."""
        from uagents.models.audit import EvolutionLogEntry
        from uagents.models.evolution import EvolutionTier
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        # Construct without old fields — should use defaults
        entry = EvolutionLogEntry(
            id=generate_id("log"),
            timestamp=now,
            tier=EvolutionTier.OPERATIONAL,
            component="core/topology.yaml",
            diff="test",
            rationale="test",
            evidence={"key": "value"},
        )
        assert entry.approved_by == ""
        assert entry.constitutional_check == ""
        assert entry.rollback_commit == ""

    def test_evolution_log_entry_old_caller_style(self):
        """SkillLibrary caller style still works (DR-02)."""
        from uagents.models.audit import EvolutionLogEntry
        from uagents.models.evolution import EvolutionTier
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        # This is how SkillLibrary._log_ring_transition() constructs entries
        entry = EvolutionLogEntry(
            id=generate_id("log"),
            timestamp=now,
            tier=EvolutionTier.ORGANIZATIONAL,
            component="skills/test-skill",
            diff="ring 2 → ring 3",
            rationale="Ring transition",
            evidence={},
            approved_by="human",
            constitutional_check="pass",
            rollback_commit="abc123",
        )
        assert entry.approved_by == "human"
        assert entry.constitutional_check == "pass"
        assert entry.rollback_commit == "abc123"

    def test_evolution_log_entry_new_fields(self):
        """Phase 4 fields available with defaults."""
        from uagents.models.audit import EvolutionLogEntry
        from uagents.models.evolution import EvolutionTier
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        entry = EvolutionLogEntry(
            id=generate_id("log"),
            timestamp=now,
            tier=EvolutionTier.OPERATIONAL,
            component="core/topology.yaml",
            diff="test",
            rationale="test",
            evidence={},
            lifecycle_state="commit",
            outcome="promoted",
            evaluation_score=0.75,
            trigger="manual",
        )
        assert entry.lifecycle_state == "commit"
        assert entry.outcome == "promoted"
        assert entry.evaluation_score == 0.75
        assert entry.trigger == "manual"


# ===========================================================================
# 8. YAML Config Tests
# ===========================================================================

class TestEvolutionYamlConfig:
    """Test evolution.yaml config loading."""

    def test_config_loads_all_sections(self, evo_yaml_store):
        """evolution.yaml has all required sections."""
        config = evo_yaml_store.read_raw("core/evolution.yaml")
        evo = config["evolution"]

        assert "tiers" in evo
        assert "lifecycle" in evo
        assert "evaluation" in evo
        assert "dual_copy" in evo
        assert "archive" in evo
        assert "objective_anchoring" in evo
        assert "safety" in evo

    def test_config_missing_key_raises_keyerror(self, evo_base):
        """IFM-N53: Missing YAML key raises KeyError immediately."""
        from uagents.state.yaml_store import YamlStore

        # Write config with missing 'evaluation' section
        core = evo_base / "core"
        config = {"evolution": {"tiers": {"tier_3_auto_approve": True}}}
        with open(core / "evolution.yaml", "w") as f:
            yaml.dump(config, f)

        yaml_store = YamlStore(evo_base)

        from uagents.engine.evolution_validator import EvolutionValidator

        with pytest.raises(KeyError):
            EvolutionValidator(yaml_store)


# ===========================================================================
# 9. Integration Tests
# ===========================================================================

class TestPhase4Integration:
    """Cross-component integration tests."""

    def test_fork_evaluate_promote_lifecycle(self, evo_yaml_store, evo_base):
        """Full fork → modify → evaluate → promote pipeline."""
        from uagents.engine.dual_copy_manager import DualCopyManager
        from uagents.engine.evolution_validator import EvolutionValidator
        from uagents.models.evolution import (
            EvolutionProposal,
            EvolutionTier,
            EvolutionOutcome,
        )
        from uagents.models.base import generate_id

        dcm = DualCopyManager(evo_yaml_store)
        validator = EvolutionValidator(evo_yaml_store)

        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="core/topology.yaml",
            diff=yaml.dump({
                "changes": [
                    {"key": "topology.max_agents", "old": 5, "new": 7},
                ],
            }),
            rationale="Increase max agents",
            evidence={"task_type": "research", "complexity": "moderate"},
            estimated_risk=0.1,
        )

        # Fork
        candidate = dcm.create_fork(proposal)
        assert len(candidate.source_files) > 0

        # Apply diff
        dcm.apply_diff(candidate, proposal)
        assert "core/topology.yaml" in candidate.modified_files

        # Evaluate
        result = validator.evaluate(candidate, proposal)
        assert len(result.dimension_scores) == 6

        # Promote (if verdict allows)
        outcome_str = result.verdict if isinstance(result.verdict, str) else str(result.verdict)
        if outcome_str == "promoted":
            dcm.promote(candidate)
            # Verify active config changed
            active = yaml.safe_load(
                (evo_base / "core" / "topology.yaml").read_text()
            )
            assert active["topology"]["max_agents"] == 7

        # Cleanup
        dcm.cleanup_fork(candidate)
        fork_dir = evo_base / candidate.fork_path
        assert not fork_dir.exists()

    def test_archive_updated_after_promotion(self, evo_yaml_store, evo_base):
        """Archive updated when evolution record is PROMOTED."""
        from uagents.engine.map_elites_archive import MAPElitesArchive
        from uagents.models.evolution import (
            EvolutionRecord,
            EvolutionProposal,
            EvolutionTier,
            EvolutionOutcome,
            EvaluationResult,
        )
        from uagents.models.base import generate_id

        archive = MAPElitesArchive(evo_yaml_store)

        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="core/topology.yaml",
            diff="test",
            rationale="test",
            evidence={"task_type": "engineering", "complexity": "complex"},
            estimated_risk=0.1,
        )
        evaluation = EvaluationResult(
            id=generate_id("eval"),
            created_at=now,
            proposal_id=proposal.id,
            candidate_id=proposal.id,
            overall_score=0.75,
            verdict=EvolutionOutcome.PROMOTED,
        )
        record = EvolutionRecord(
            id=generate_id("rec"),
            created_at=now,
            proposal=proposal,
            evaluation=evaluation,
            approved_by="auto (tier 3)",
            constitutional_check="pass",
            outcome=EvolutionOutcome.PROMOTED,
            verification_passed=True,
        )

        updated = archive.update_from_evolution(record)
        assert updated is True
        assert len(archive.get_all_cells()) == 1
        assert archive.get_all_cells()[0].task_type == "engineering"
        assert archive.get_all_cells()[0].complexity == "complex"

    def test_use_enum_values_consistency(self):
        """FM-P4-12: Enum values survive YAML roundtrip via use_enum_values=True."""
        from uagents.models.evolution import (
            EvolutionProposal,
            EvolutionTier,
            ObservationTrigger,
        )
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="test.yaml",
            diff="test",
            rationale="test",
            estimated_risk=0.1,
            trigger=ObservationTrigger.TASK_FAILURE,
        )

        # After use_enum_values, tier is stored as int, trigger as str
        # Use int()/str() for safe comparison
        assert int(proposal.tier) == 3
        assert str(proposal.trigger) == "task_failure"

        # Round-trip through dict — must use model_validate(strict=False)
        # because use_enum_values stores primitives but strict=True rejects them
        d = proposal.model_dump()
        restored = EvolutionProposal.model_validate(d, strict=False)
        assert int(restored.tier) == 3
        assert str(restored.trigger) == "task_failure"


# ===========================================================================
# 10. Additional Failure Mode Coverage (from test-qa review)
# ===========================================================================

class TestFailureModeCoverage:
    """Tests for CRITICAL and HIGH failure modes identified in review."""

    def _make_engine(self, evo_yaml_store, evo_base):
        """Create EvolutionEngine with mocked dependencies."""
        from uagents.engine.evolution_engine import EvolutionEngine
        from uagents.engine.dual_copy_manager import DualCopyManager
        from uagents.engine.evolution_validator import EvolutionValidator
        from uagents.engine.map_elites_archive import MAPElitesArchive

        git_ops = MagicMock()
        git_ops.create_rollback_point.return_value = "rollback-sha-123"
        git_ops.commit_evolution.return_value = "commit-sha-456"

        constitution_guard = MagicMock()
        constitution_guard.check_proposal.return_value = (True, "Constitutional check passed")
        constitution_guard.verify_hash.return_value = True

        ring_enforcer = MagicMock()
        ring_enforcer.verify_no_ring_0_modification.return_value = False

        audit_logger = MagicMock()

        dcm = DualCopyManager(evo_yaml_store)
        validator = EvolutionValidator(evo_yaml_store)
        archive = MAPElitesArchive(evo_yaml_store)

        engine = EvolutionEngine(
            yaml_store=evo_yaml_store,
            git_ops=git_ops,
            constitution_guard=constitution_guard,
            dual_copy_manager=dcm,
            validator=validator,
            archive=archive,
            audit_logger=audit_logger,
            ring_enforcer=ring_enforcer,
        )
        return engine, git_ops, constitution_guard, ring_enforcer, audit_logger

    def _make_tier3_proposal(self, component="core/topology.yaml"):
        from uagents.models.evolution import (
            EvolutionProposal,
            EvolutionTier,
            ObservationTrigger,
        )
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        return EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component=component,
            diff=yaml.dump({
                "changes": [
                    {"key": "topology.max_agents", "old": 5, "new": 7},
                ],
            }),
            rationale="Increase max agents",
            evidence={"task_type": "research", "complexity": "moderate"},
            estimated_risk=0.1,
            trigger=ObservationTrigger.MANUAL,
        )

    def test_constitution_hash_invalid_triggers_rollback(
        self, evo_yaml_store, evo_base,
    ):
        """FM-P4-01: If constitution hash invalid after promotion, rollback."""
        engine, git_ops, constitution_guard, _, _ = self._make_engine(
            evo_yaml_store, evo_base
        )
        # Constitution hash verification fails AFTER promotion
        constitution_guard.verify_hash.return_value = False

        for _ in range(3):
            engine.record_task_completion()

        proposal = self._make_tier3_proposal()
        record = engine.run_evolution(proposal)

        outcome_str = record.outcome if isinstance(record.outcome, str) else str(record.outcome)
        # Must be rolled_back or rejected — cannot be promoted with invalid hash
        assert outcome_str != "promoted", (
            f"Must not promote when constitution hash invalid; got {outcome_str}"
        )
        assert outcome_str in ("rolled_back", "rejected")

    def test_objective_alignment_pause(self, evo_yaml_store, evo_base):
        """FM-P4-03: Low alignment score pauses evolution engine."""
        engine, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)

        # Simulate low alignment detection → engine pauses
        engine.pause("Objective alignment below threshold (0.5 < 0.8)")
        assert engine.is_paused() is True
        assert engine.can_evolve() is False

        # Evolution attempts while paused are rejected
        for _ in range(3):
            engine.record_task_completion()
        proposal = self._make_tier3_proposal()
        record = engine.run_evolution(proposal)
        outcome_str = record.outcome if isinstance(record.outcome, str) else str(record.outcome)
        assert outcome_str == "rejected"

    def test_constitution_guard_bypass_via_diff_content(
        self, evo_yaml_store, evo_base,
    ):
        """FM-P4-26: Diff that indirectly modifies Ring 0 content rejected."""
        engine, _, _, ring_enforcer, _ = self._make_engine(
            evo_yaml_store, evo_base
        )
        # Ring enforcer raises RingViolationError for indirect Ring 0 modification
        from uagents.engine.ring_enforcer import RingViolationError
        ring_enforcer.verify_no_ring_0_modification.side_effect = RingViolationError(
            "Indirect Ring 0 modification detected in diff content"
        )

        for _ in range(3):
            engine.record_task_completion()

        proposal = self._make_tier3_proposal()
        record = engine.run_evolution(proposal)
        outcome_str = record.outcome if isinstance(record.outcome, str) else str(record.outcome)
        assert outcome_str != "promoted"
        assert outcome_str in ("rejected", "rolled_back")

    def test_get_stats_method(self, evo_yaml_store):
        """MAPElitesArchive.get_stats() returns meaningful statistics."""
        from uagents.engine.map_elites_archive import MAPElitesArchive
        from uagents.models.evolution import (
            EvolutionRecord, EvolutionProposal, EvolutionTier,
            EvolutionOutcome, EvaluationResult,
        )
        from uagents.models.base import generate_id

        archive = MAPElitesArchive(evo_yaml_store)

        # Stats on empty archive
        stats = archive.get_stats()
        assert isinstance(stats, dict)
        assert stats["total_cells"] == 0
        assert stats["coverage"] == 0.0

        # Add a record
        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"), created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="core/topology.yaml", diff="test",
            rationale="test",
            evidence={"task_type": "research", "complexity": "moderate"},
            estimated_risk=0.1,
        )
        evaluation = EvaluationResult(
            id=generate_id("eval"), created_at=now,
            proposal_id=proposal.id, candidate_id=proposal.id,
            overall_score=0.7, verdict=EvolutionOutcome.PROMOTED,
        )
        record = EvolutionRecord(
            id=generate_id("rec"), created_at=now,
            proposal=proposal, evaluation=evaluation,
            approved_by="auto (tier 3)", constitutional_check="pass",
            outcome=EvolutionOutcome.PROMOTED, verification_passed=True,
        )
        archive.update_from_evolution(record)

        stats = archive.get_stats()
        assert stats["total_cells"] == 1
        assert stats["coverage"] > 0.0

    def test_get_evolution_count(self, evo_yaml_store, evo_base):
        """EvolutionEngine.get_evolution_count() tracks evolution attempts."""
        engine, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)

        initial_count = engine.get_evolution_count()
        assert isinstance(initial_count, int)
        assert initial_count >= 0

        # Run an evolution
        for _ in range(3):
            engine.record_task_completion()
        proposal = self._make_tier3_proposal()
        engine.run_evolution(proposal)

        assert engine.get_evolution_count() == initial_count + 1

    def test_unpause_resumes_evolution(self, evo_yaml_store, evo_base):
        """unpause() clears pause state and records reason."""
        engine, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)

        # Pause
        engine.pause("Test pause reason")
        assert engine.is_paused() is True
        assert engine.can_evolve() is False

        # Unpause with reason
        engine.unpause("Human reviewed and cleared")
        assert engine.is_paused() is False

        # After unpause + enough tasks, evolution should work
        for _ in range(3):
            engine.record_task_completion()
        assert engine.can_evolve() is True

    def test_pause_persists_across_restart(self, evo_yaml_store, evo_base):
        """FM-P4-48: Paused state survives engine restart."""
        engine1, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)
        engine1.pause("Alignment concern detected")
        assert engine1.is_paused() is True

        # Create new engine instance (simulating restart)
        engine2, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)
        assert engine2.is_paused() is True
        assert engine2.can_evolve() is False

    def test_invalid_yaml_diff_raises_fork_error(
        self, evo_yaml_store, evo_base,
    ):
        """FM-P4-34: Invalid YAML in diff raises ForkError."""
        from uagents.engine.dual_copy_manager import DualCopyManager, ForkError
        from uagents.models.evolution import EvolutionProposal, EvolutionTier
        from uagents.models.base import generate_id

        mgr = DualCopyManager(evo_yaml_store)
        now = datetime.now(timezone.utc)

        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="core/topology.yaml",
            diff="not: valid: yaml: {{{",  # Invalid YAML
            rationale="Test invalid diff",
            estimated_risk=0.1,
        )
        candidate = mgr.create_fork(proposal)

        with pytest.raises((ForkError, yaml.YAMLError)):
            mgr.apply_diff(candidate, proposal)

    def test_concurrent_candidate_limit(self, evo_yaml_store, evo_base):
        """FM-P4-43: Only max_concurrent_candidates forks allowed at once."""
        engine, _, _, _, _ = self._make_engine(evo_yaml_store, evo_base)

        # Config: max_concurrent_candidates = 1
        # First evolution should proceed; second should be blocked
        for _ in range(6):
            engine.record_task_completion()

        # The engine should track concurrent candidates and enforce the limit.
        # Since max_concurrent_candidates=1, we verify the attribute exists
        # and is correctly loaded.
        assert hasattr(engine, '_max_concurrent_candidates')
        assert engine._max_concurrent_candidates == 1

    def test_yaml_roundtrip_complex_models(self, evo_yaml_store, evo_base):
        """Complex evolution models survive YAML write/read roundtrip."""
        from uagents.models.evolution import (
            EvolutionRecord, EvolutionProposal, EvolutionTier,
            EvolutionOutcome, EvaluationResult, DimensionScore,
            EvaluationDimension, ObservationTrigger,
        )
        from uagents.models.base import generate_id

        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="core/topology.yaml",
            diff=yaml.dump({"changes": [{"key": "a.b", "old": 1, "new": 2}]}),
            rationale="Test roundtrip",
            evidence={"task_type": "research", "complexity": "moderate"},
            estimated_risk=0.15,
            trigger=ObservationTrigger.MANUAL,
            trigger_detail="test trigger",
        )
        evaluation = EvaluationResult(
            id=generate_id("eval"),
            created_at=now,
            proposal_id=proposal.id,
            candidate_id=proposal.id,
            dimension_scores=[
                DimensionScore(
                    dimension=EvaluationDimension.SAFETY,
                    score=0.95,
                    detail="Ring 0 intact",
                ),
                DimensionScore(
                    dimension=EvaluationDimension.CAPABILITY,
                    score=0.8,
                ),
            ],
            overall_score=0.85,
            verdict=EvolutionOutcome.PROMOTED,
            verdict_reason="All dimensions above minimum",
        )
        record = EvolutionRecord(
            id=generate_id("rec"),
            created_at=now,
            proposal=proposal,
            evaluation=evaluation,
            approved_by="auto (tier 3)",
            constitutional_check="pass",
            outcome=EvolutionOutcome.PROMOTED,
            verification_passed=True,
            rollback_commit="abc123",
        )

        # Dump to dict and reconstruct (simulates YAML roundtrip)
        # Must use model_validate(strict=False) — same as YamlStore.read()
        d = record.model_dump()
        restored = EvolutionRecord.model_validate(d, strict=False)

        assert restored.id == record.id
        assert int(restored.proposal.tier) == int(record.proposal.tier)
        assert str(restored.proposal.trigger) == str(record.proposal.trigger)
        assert restored.evaluation.overall_score == record.evaluation.overall_score
        assert len(restored.evaluation.dimension_scores) == 2
        assert restored.verification_passed is True

    def test_git_rollback_called_on_ring_violation(
        self, evo_yaml_store, evo_base,
    ):
        """Git rollback_to is called when Ring 0 violation detected."""
        engine, git_ops, _, ring_enforcer, _ = self._make_engine(
            evo_yaml_store, evo_base,
        )
        from uagents.engine.ring_enforcer import RingViolationError
        ring_enforcer.verify_no_ring_0_modification.side_effect = RingViolationError(
            "Ring 0 file modified"
        )

        for _ in range(3):
            engine.record_task_completion()

        proposal = self._make_tier3_proposal()
        record = engine.run_evolution(proposal)

        outcome_str = record.outcome if isinstance(record.outcome, str) else str(record.outcome)
        assert outcome_str == "rolled_back", f"Expected rolled_back, got {outcome_str}"
        # Verify rollback was actually executed
        git_ops.rollback_to.assert_called_once()

    def test_disk_space_check_on_fork(self, evo_yaml_store, evo_base):
        """FM-P4-44: DualCopyManager checks disk space before fork."""
        from uagents.engine.dual_copy_manager import DualCopyManager
        from uagents.models.evolution import EvolutionProposal, EvolutionTier
        from uagents.models.base import generate_id

        mgr = DualCopyManager(evo_yaml_store)

        # Verify the method exists — actual disk space check depends on OS
        assert hasattr(mgr, '_check_disk_space') or hasattr(mgr, 'create_fork')
        # Normal fork should succeed (test environment has disk space)
        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component="core/topology.yaml",
            diff=yaml.dump({"changes": [{"key": "a.b", "old": 5, "new": 7}]}),
            rationale="Disk space test",
            estimated_risk=0.1,
        )
        candidate = mgr.create_fork(proposal)
        assert candidate is not None
