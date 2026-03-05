"""Evolution engine — 8-step lifecycle driver.
Spec reference: Section 7 (Evolution Engine), Section 16.2 Phase 5 (Evolve).

Orchestrates the evolution lifecycle:
OBSERVE → ATTRIBUTE → PROPOSE → EVALUATE → APPROVE → COMMIT → VERIFY → LOG

Phase 4 scope: Tier 3 auto-approved evolutions only.
Tier 2 (quorum) and Tier 1 (human) deferred to Phase 5.

Key constraints:
- Constitutional check on EVERY proposal (before evaluation)
- Dual-copy isolation: changes NEVER applied in-place
- Atomic Git commits with structured messages
- Objective anchoring every 10 cycles
- All steps logged to evolution audit stream
- Ring 0/1 modifications FORBIDDEN
- RingEnforcer verifies modified files after promotion (FM-P4-29)
- Persistent state survives restarts (FM-P4-23)
- Persistent pause flag after alignment failure (FM-P4-48)

Literature basis:
- Darwin Godel Machine: dual-copy + population (20%→50% SWE-bench)
- Song et al. 2024: generation-verification gap
- ADAS (ICLR 2025): archive-based meta-agent search
- AlphaEvolve (DeepMind): evolutionary code improvement
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..audit.logger import AuditLogger
from ..models.audit import EvolutionLogEntry
from ..models.base import FrameworkModel, generate_id
from ..models.evolution import (
    DualCopyCandidate,
    EvaluationResult,
    EvolutionLifecycleState,
    EvolutionOutcome,
    EvolutionProposal,
    EvolutionRecord,
    EvolutionTier,
    ObservationTrigger,
)
from ..state.git_ops import GitOps, GitOpsError
from ..state.yaml_store import YamlStore
from .constitution_guard import ConstitutionGuard
from .dual_copy_manager import DualCopyManager, ForkError, PromotionError
from .evolution_validator import EvolutionValidator
from .map_elites_archive import MAPElitesArchive
from .gap_monitor import GapMonitor
from .population_evolver import PopulationEvolver, PopulationError
from .ring_enforcer import RingEnforcer, RingViolationError
from .stagnation_detector import StagnationDetector

from ..models.population import GapCalibrationAction, PopulationOutcome

# Phase 5: Governance imports (conditional — works even if not installed)
try:
    from .quorum_manager import QuorumManager, QuorumError, InsufficientVotersError
    from .objective_anchor import ObjectiveAnchor
    from .objective_anchor import ObjectiveAlignmentError as AnchorAlignmentError
    from .risk_scorecard import RiskScorecard
    from .alignment_verifier import AlignmentVerifier
except ImportError:  # pragma: no cover
    import warnings
    warnings.warn(
        "Phase 5 governance modules not importable. "
        "Tier 2 quorum, risk scorecard, and alignment verification "
        "will not be available.",
        ImportWarning,
        stacklevel=2,
    )
    QuorumManager = None  # type: ignore[assignment,misc]
    QuorumError = RuntimeError  # type: ignore[assignment,misc]
    InsufficientVotersError = RuntimeError  # type: ignore[assignment,misc]
    ObjectiveAnchor = None  # type: ignore[assignment,misc]
    AnchorAlignmentError = RuntimeError  # type: ignore[assignment,misc]
    RiskScorecard = None  # type: ignore[assignment,misc]
    AlignmentVerifier = None  # type: ignore[assignment,misc]

logger = logging.getLogger("uagents.evolution_engine")


class EvolutionError(RuntimeError):
    """Raised when an evolution operation fails non-recoverably."""


class EvolutionRejectedError(RuntimeError):
    """Raised when a proposal is rejected (constitutional, tier, or safety)."""


class ObjectiveAlignmentError(RuntimeError):
    """Raised when objective alignment drops below threshold.

    This is a non-recoverable error that requires human intervention.
    Evolution must be paused until the human investigates.
    The EvolutionEngine sets a persistent pause flag (FM-P4-48).
    """


class EvolutionEngineState(FrameworkModel):
    """Persistent state for the evolution engine (FM-P4-23-FIX).

    Persisted to: state/evolution/engine-state.yaml
    Survives process restarts.
    """

    evolution_count: int = 0
    tasks_since_last_evolution: int = 0
    paused: bool = False  # FM-P4-48-FIX: persistent pause flag
    pause_reason: str = ""


class EvolutionEngine:
    """Drives the 8-step evolution lifecycle.

    Design invariants:
    - Only Tier 3 proposals are auto-approved (Phase 4)
    - Constitutional check before every evaluation
    - Dual-copy isolation for all changes
    - RingEnforcer verifies modified files post-promotion (FM-P4-29)
    - Objective anchoring every N cycles
    - Every step logged to evolution audit stream
    - Ring 0/1 NEVER modified
    - Cooldown enforced between evolution cycles
    - Persistent state survives restarts (FM-P4-23)
    - Persistent pause flag on alignment failure (FM-P4-48)

    Usage:
        engine = EvolutionEngine(yaml_store, git_ops, constitution_guard,
                                 dual_copy_mgr, validator, archive,
                                 audit_logger, ring_enforcer)
        record = engine.run_evolution(proposal)
        # record.outcome is PROMOTED, ROLLED_BACK, REJECTED, or HELD
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        git_ops: GitOps,
        constitution_guard: ConstitutionGuard,
        dual_copy_manager: DualCopyManager,
        validator: EvolutionValidator,
        archive: MAPElitesArchive,
        audit_logger: AuditLogger,
        ring_enforcer: RingEnforcer,  # FM-P4-29-FIX: Required, not optional
        domain: str = "meta",
        # Phase 5: Optional governance components
        quorum_manager: QuorumManager | None = None,
        objective_anchor: ObjectiveAnchor | None = None,
        risk_scorecard: RiskScorecard | None = None,
        alignment_verifier: AlignmentVerifier | None = None,
        # Phase 8: Population evolution components
        population_evolver: PopulationEvolver | None = None,
        gap_monitor: GapMonitor | None = None,
        stagnation_detector: StagnationDetector | None = None,
    ):
        self.yaml_store = yaml_store
        self.git_ops = git_ops
        self.constitution_guard = constitution_guard
        self.dual_copy_manager = dual_copy_manager
        self.validator = validator
        self.archive = archive
        self.audit_logger = audit_logger
        self.ring_enforcer = ring_enforcer
        self.domain = domain
        # Phase 5: Governance components
        self._quorum_manager = quorum_manager
        self._objective_anchor = objective_anchor
        self._risk_scorecard = risk_scorecard
        self._alignment_verifier = alignment_verifier
        # Phase 8: Population evolution components
        self._population_evolver = population_evolver
        self._gap_monitor = gap_monitor
        self._stagnation_detector = stagnation_detector

        # Load config (fail-loud if missing)
        config_raw = yaml_store.read_raw("core/evolution.yaml")
        evo = config_raw["evolution"]

        # IFM-N53: Direct dict access — missing keys raise KeyError
        lifecycle = evo["lifecycle"]
        evaluation = evo["evaluation"]
        safety = evo["safety"]
        anchoring = evo["objective_anchoring"]

        self._max_proposals_per_cycle = int(lifecycle["max_proposals_per_cycle"])
        self._max_concurrent_candidates = int(lifecycle["max_concurrent_candidates"])  # FM-P4-43-FIX
        self._cooldown_between_evolutions = int(lifecycle["cooldown_between_evolutions"])
        self._proposal_timeout_min = int(lifecycle["proposal_timeout_minutes"])

        self._promote_threshold = float(evaluation["promote_threshold"])
        self._hold_threshold = float(evaluation["hold_threshold"])

        self._max_file_modifications = int(safety["max_file_modifications_per_proposal"])
        self._max_diff_lines = int(safety["max_diff_lines"])
        self._forbidden_patterns: list[str] = safety["forbidden_path_patterns"]
        self._allowed_extensions: list[str] = safety["allowed_extensions"]

        self._anchoring_interval = int(anchoring["check_every_n_cycles"])
        self._min_alignment_score = float(anchoring["min_alignment_score"])

        # FM-P4-19-FIX: Instance prefix for git paths
        self._instance_prefix = f"instances/{domain}/"

        # Persistence paths
        self._base = "state/evolution"
        self._proposals_dir = f"{self._base}/proposals"
        self._records_dir = f"{self._base}/records"
        self._evaluations_dir = f"{self._base}/evaluations"
        self._state_path = f"{self._base}/engine-state.yaml"

        # Audit failure counter (review fix #6: consecutive failures halt evolution)
        self._audit_failure_count = 0
        self._max_audit_failures = 3

        # FM-P4-23-FIX: Load persistent state (evolution count, cooldown, pause flag)
        self._state = self._load_state()

    @property
    def _evolution_count(self) -> int:
        return self._state.evolution_count

    @property
    def _tasks_since_last_evolution(self) -> int:
        return self._state.tasks_since_last_evolution

    def record_task_completion(self) -> None:
        """Called after each task verdict (pass or fail) to track cooldown.

        FM-P4-46-FIX: Called on ALL verdicts, not just pass.
        The cooldown prevents evolution from running too frequently.
        """
        self._state.tasks_since_last_evolution += 1
        self._save_state()

    def can_evolve(self) -> bool:
        """Check if evolution is allowed (cooldown elapsed and not paused)."""
        if self._state.paused:
            return False
        return self._state.tasks_since_last_evolution >= self._cooldown_between_evolutions

    def is_paused(self) -> bool:
        """Check if evolution is paused (FM-P4-48)."""
        return self._state.paused

    def pause(self, reason: str) -> None:
        """Pause evolution. Sets persistent pause flag (FM-P4-48)."""
        self._state.paused = True
        self._state.pause_reason = reason
        self._save_state()
        logger.info(f"Evolution paused: {reason}")

    def unpause(self, reason: str = "Human cleared pause") -> None:
        """Unpause evolution. Only called by explicit human action (FM-P4-48)."""
        self._state.paused = False
        self._state.pause_reason = reason
        self._save_state()
        logger.info(f"Evolution unpaused: {reason}")

    def get_evolution_count(self) -> int:
        """Return the total number of successful evolutions."""
        return self._state.evolution_count

    def run_evolution(self, proposal: EvolutionProposal) -> EvolutionRecord:
        """Execute the full 8-step evolution lifecycle for a proposal.

        Steps:
        1. OBSERVE — already done (trigger is in proposal)
        2. ATTRIBUTE — already done (evidence is in proposal)
        3. PROPOSE — validate proposal safety + diff format
        4. EVALUATE — constitutional check + dual-copy evaluation
        5. APPROVE — tier-based (Tier 3 auto in Phase 4)
        6. COMMIT — promote fork + Git commit (with error recovery)
        7. VERIFY — post-commit verification + Ring 0 check
        8. LOG — full record to audit stream

        Args:
            proposal: The evolution proposal to evaluate.

        Returns:
            EvolutionRecord with outcome (PROMOTED, REJECTED, HELD, ROLLED_BACK).

        Raises:
            EvolutionError: On non-recoverable failures (Git, IO).
            ObjectiveAlignmentError: When objective alignment is too low.
        """
        now = datetime.now(timezone.utc)

        # FM-P4-48-FIX: Check persistent pause flag
        if self._state.paused:
            return self._reject(
                proposal,
                f"Evolution paused: {self._state.pause_reason}",
                now,
            )

        # DR-09-FIX: Track lifecycle state as local variable, not mutating proposal
        current_state = EvolutionLifecycleState.PROPOSE

        # ── Step 3: PROPOSE — validate safety ──
        self._log_lifecycle(proposal, current_state)

        # 3a. Tier check (Phase 5: supports Tier 1-3)
        tier_int = int(proposal.tier)

        if tier_int == EvolutionTier.CONSTITUTIONAL:
            return self._reject(
                proposal,
                "Tier 0 (constitutional) evolution is NEVER allowed programmatically.",
                now,
            )
        if tier_int == EvolutionTier.FRAMEWORK:
            # Tier 1: queue for human approval (Phase 5 creates queue entry only)
            return self._queue_for_human(proposal, now)
        if tier_int == EvolutionTier.ORGANIZATIONAL:
            # Tier 2: requires quorum approval
            if self._quorum_manager is None:
                return self._reject(
                    proposal,
                    "Tier 2 (organizational) evolution requires QuorumManager "
                    "(Phase 5 governance). QuorumManager not configured.",
                    now,
                )
        # Tier 3 falls through to existing auto-approval path

        # 3b. Safety checks
        safety_ok, safety_reason = self._check_proposal_safety(proposal)
        if not safety_ok:
            return self._reject(proposal, safety_reason, now)

        # 3c. Constitutional check
        const_ok, const_reason = self.constitution_guard.check_proposal(proposal)
        if not const_ok:
            return self._reject(
                proposal, f"Constitutional: {const_reason}", now,
                constitutional_failure=True,
            )

        # FM-P4-34-FIX: Validate diff format (YAML) before creating fork
        try:
            yaml.safe_load(proposal.diff)
        except yaml.YAMLError as e:
            return self._reject(proposal, f"Diff is not valid YAML: {e}", now)

        # FM-P4-43-FIX: Check concurrent candidate limit
        candidates_dir = self.yaml_store.base_dir / self._base / "candidates"
        if candidates_dir.exists():
            existing = [d for d in candidates_dir.iterdir() if d.is_dir()]
            if len(existing) >= self._max_concurrent_candidates:
                return self._reject(
                    proposal,
                    f"Concurrent candidate limit ({self._max_concurrent_candidates}) reached. "
                    f"Wait for existing evolution to complete.",
                    now,
                )

        # ── Step 4: EVALUATE — dual-copy evaluation ──
        current_state = EvolutionLifecycleState.EVALUATE
        self._log_lifecycle(proposal, current_state)

        # FM-P4-34-FIX: Wrap fork+eval in try/except for cleanup
        candidate: DualCopyCandidate | None = None
        try:
            # 4a. Create fork
            candidate = self.dual_copy_manager.create_fork(proposal)

            # 4b. Apply diff to fork
            self.dual_copy_manager.apply_diff(candidate, proposal)

            # FM-P4-27-FIX: Check file count after apply_diff
            if len(candidate.modified_files) > self._max_file_modifications:
                self.dual_copy_manager.cleanup_fork(candidate)
                return self._reject(
                    proposal,
                    f"Modified {len(candidate.modified_files)} files, exceeds "
                    f"max of {self._max_file_modifications}",
                    now,
                )

            # FM-P4-42-FIX: Re-persist manifest after apply_diff
            self.dual_copy_manager.persist_manifest(candidate)

            # 4c. Evaluate fork
            evaluation = self.validator.evaluate(candidate, proposal)

        except ForkError as e:
            if candidate is not None:
                self.dual_copy_manager.cleanup_fork(candidate)
            return self._reject(proposal, f"Fork error: {e}", now)

        # Persist evaluation
        self.yaml_store.write(
            f"{self._evaluations_dir}/{evaluation.id}.yaml", evaluation
        )

        # ── Step 5: APPROVE — determine outcome ──
        current_state = EvolutionLifecycleState.APPROVE
        self._log_lifecycle(proposal, current_state)

        verdict_str = str(evaluation.verdict)
        if verdict_str == str(EvolutionOutcome.REJECTED):
            self.dual_copy_manager.cleanup_fork(candidate)
            return self._reject(
                proposal,
                f"Evaluation failed: {evaluation.verdict_reason}",
                now,
                evaluation=evaluation,
            )

        if verdict_str == str(EvolutionOutcome.HELD):
            self.dual_copy_manager.cleanup_fork(candidate)
            return self._hold(proposal, evaluation, now)

        # M-02-FIX: Two-phase quorum for Tier 2.
        # Phase 1: Create quorum session and return HELD record.
        # Phase 2: External code collects votes, then calls complete_tier2_evolution().
        if tier_int == EvolutionTier.ORGANIZATIONAL:
            try:
                quorum_session_id = self._initiate_tier2_quorum(proposal)
            except (InsufficientVotersError, QuorumError) as e:
                self.dual_copy_manager.cleanup_fork(candidate)
                return self._reject(
                    proposal,
                    f"Quorum process failed: {e}",
                    now,
                    evaluation=evaluation,
                )

            # Return HELD record — evolution paused pending quorum vote collection
            record = self._create_held_record(
                proposal, evaluation, candidate, now,
                f"Awaiting Tier 2 quorum: session {quorum_session_id}",
            )
            logger.info(
                f"Evolution {proposal.id} HELD pending quorum session {quorum_session_id}"
            )
            return record
        # Tier 3 continues with auto-approval
        approved_by = "auto (tier 3)"

        # ── Step 6: COMMIT — promote fork + git commit ──
        current_state = EvolutionLifecycleState.COMMIT
        self._log_lifecycle(proposal, current_state)

        rollback_sha = self.git_ops.create_rollback_point()

        # DR-05/FM-P4-20-FIX: Wrap promote + commit in try/except
        evolution_sha = ""
        try:
            # Promote: copy fork files to active positions
            self.dual_copy_manager.promote(candidate)

            # FM-P4-19-FIX: Prepend instance prefix to file paths for git
            git_files = self._git_paths(candidate)

            # Git commit
            evolution_sha = self.git_ops.commit_evolution(
                evo_id=proposal.id,
                tier=tier_int,
                rationale=proposal.rationale,
                approved_by="auto (tier 3)",
                files=git_files,
            )
        except (GitOpsError, PromotionError) as e:
            # Rollback promoted files if promotion happened
            logger.error(f"Commit failed for {proposal.id}: {e}")
            if candidate.promoted:
                try:
                    self.git_ops.rollback_to(rollback_sha)
                except GitOpsError as re:
                    # CATASTROPHIC: Commit failed AND rollback failed.
                    # Active config is inconsistent. Pause evolution immediately.
                    self._state.paused = True
                    self._state.pause_reason = (
                        f"CRITICAL: Commit failed AND rollback failed for "
                        f"{proposal.id}. Active config may be inconsistent. "
                        f"Commit error: {e}. Rollback error: {re}"
                    )
                    self._save_state()
                    raise EvolutionError(
                        f"Commit failed for {proposal.id} AND rollback to "
                        f"{rollback_sha} also failed. Active config is "
                        f"inconsistent. Evolution paused. Manual intervention "
                        f"required. Commit error: {e}. Rollback error: {re}"
                    ) from re
            self.dual_copy_manager.cleanup_fork(candidate)
            return self._reject(
                proposal, f"Commit failed: {e}", now, evaluation=evaluation
            )

        # ── Step 7: VERIFY — post-commit checks ──
        current_state = EvolutionLifecycleState.VERIFY
        self._log_lifecycle(proposal, current_state)

        # FM-P4-29-FIX: RingEnforcer verifies no Ring 0 files modified
        git_files = self._git_paths(candidate)
        try:
            self.ring_enforcer.verify_no_ring_0_modification(git_files)
            ring_check_passed = True
        except RingViolationError as e:
            logger.error(f"Ring 0 violation detected for {proposal.id}: {e}")
            ring_check_passed = False

        verification_ok = self._verify_post_commit() and ring_check_passed

        if not verification_ok:
            # FM-P4-37-FIX: Only rollback if evolution_sha != rollback_sha
            if evolution_sha and evolution_sha != rollback_sha:
                logger.error(
                    f"Post-commit verification failed for {proposal.id}. "
                    f"Rolling back to {rollback_sha[:8]}."
                )
                try:
                    self.git_ops.rollback_to(rollback_sha)
                except GitOpsError as e:
                    # CATASTROPHIC: Verification failed AND rollback failed
                    self._state.paused = True
                    self._state.pause_reason = (
                        f"CRITICAL: Verification failed AND rollback failed "
                        f"for {proposal.id}. Config inconsistent."
                    )
                    self._save_state()
                    raise EvolutionError(
                        f"Post-commit verification failed for {proposal.id} "
                        f"AND rollback to {rollback_sha} failed: {e}. "
                        f"Evolution paused. Manual intervention required."
                    ) from e
            self.dual_copy_manager.cleanup_fork(candidate)

            record = EvolutionRecord(
                id=generate_id("evo-rec"),
                created_at=now,
                proposal=proposal,
                evaluation=evaluation,
                approved_by="auto (tier 3)",
                constitutional_check="pass",
                rollback_commit=rollback_sha,
                evolution_commit=evolution_sha,
                outcome=EvolutionOutcome.ROLLED_BACK,
                verification_passed=False,
            )
            self._persist_record(record)
            self._log_outcome(record)
            return record

        # ── Step 8: LOG — success ──
        self.dual_copy_manager.cleanup_fork(candidate)

        record = EvolutionRecord(
            id=generate_id("evo-rec"),
            created_at=now,
            proposal=proposal,
            evaluation=evaluation,
            approved_by="auto (tier 3)",
            constitutional_check="pass",
            rollback_commit=rollback_sha,
            evolution_commit=evolution_sha,
            outcome=EvolutionOutcome.PROMOTED,
            verification_passed=True,
        )
        self._persist_record(record)
        self._log_outcome(record)

        # Track evolution count and reset cooldown (FM-P4-23: persisted)
        self._state.evolution_count += 1
        self._state.tasks_since_last_evolution = 0
        self._save_state()

        # DR-18-FIX: Archive update after counter update.
        # Narrowed to IO/data errors — programming bugs propagate.
        try:
            self.archive.update_from_evolution(record)
        except (OSError, ValueError, yaml.YAMLError) as e:
            logger.warning(f"Archive update failed for {record.id}: {e}")

        # Objective anchoring check
        if self._state.evolution_count % self._anchoring_interval == 0:
            self._check_objective_alignment()

        return record

    def create_proposal(
        self,
        component: str,
        diff: str,
        rationale: str,
        trigger: ObservationTrigger = ObservationTrigger.MANUAL,
        trigger_detail: str = "",
        evidence: dict | None = None,
        estimated_risk: float = 0.3,
    ) -> EvolutionProposal:
        """Create a new Tier 3 evolution proposal.

        Args:
            component: File path being modified (relative to instance root).
            diff: YAML-formatted diff of proposed changes.
            rationale: Why this change is needed (required).
            trigger: What triggered this proposal.
            trigger_detail: Additional trigger context (e.g., task_id).
            evidence: Supporting evidence dict.
            estimated_risk: Estimated risk (0.0-1.0).

        Returns:
            EvolutionProposal ready for run_evolution().
        """
        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component=component,
            diff=diff,
            rationale=rationale,
            evidence=evidence or {},
            estimated_risk=estimated_risk,
            trigger=trigger,
            trigger_detail=trigger_detail,
            lifecycle_state=EvolutionLifecycleState.OBSERVE,
        )

        # Persist proposal
        self.yaml_store.write(
            f"{self._proposals_dir}/{proposal.id}.yaml", proposal
        )

        return proposal

    # ── Private helpers ──

    def _check_proposal_safety(
        self, proposal: EvolutionProposal
    ) -> tuple[bool, str]:
        """Validate proposal against safety constraints.

        Checks:
        1. Component path not in forbidden patterns (path-aware matching)
        2. Component extension is allowed
        3. Diff size within limits
        """
        component = proposal.component
        component_path = Path(component)

        # 0. Path traversal check — prevent ../../../etc/passwd
        instance_root = Path(self.yaml_store.base_dir).resolve()
        resolved = (instance_root / component).resolve()
        if not resolved.is_relative_to(instance_root):
            return False, (
                f"Component path '{component}' escapes instance root "
                f"(path traversal detected)"
            )

        # 1. Forbidden path patterns — path-aware matching
        for pattern in self._forbidden_patterns:
            pattern_path = Path(pattern)
            try:
                if component_path.is_relative_to(pattern_path):
                    return False, f"Component '{component}' is under forbidden path '{pattern}'"
            except (TypeError, ValueError) as e:
                raise EvolutionError(
                    f"Forbidden path pattern '{pattern}' caused error "
                    f"when checking component '{component}': {e}. "
                    f"Fix the forbidden_path_patterns config."
                ) from e
            # Also check exact filename match (e.g., "CONSTITUTION.md")
            if component_path.name.lower() == pattern_path.name.lower():
                return False, f"Component filename '{component_path.name}' matches forbidden '{pattern}'"

        # 2. Allowed extensions
        extension = component_path.suffix
        if extension not in self._allowed_extensions:
            return False, (
                f"Component extension '{extension}' not in allowed list: "
                f"{self._allowed_extensions}"
            )

        # 3. Diff size
        diff_lines = len(proposal.diff.strip().split("\n")) if proposal.diff.strip() else 0
        if diff_lines > self._max_diff_lines:
            return False, (
                f"Diff has {diff_lines} lines, exceeds maximum of "
                f"{self._max_diff_lines}"
            )

        return True, "Safety checks passed"

    def _reject(
        self,
        proposal: EvolutionProposal,
        reason: str,
        now: datetime,
        evaluation: EvaluationResult | None = None,
        constitutional_failure: bool = False,
    ) -> EvolutionRecord:
        """Create a rejected evolution record."""
        logger.info(f"Evolution {proposal.id} rejected: {reason}")

        record = EvolutionRecord(
            id=generate_id("evo-rec"),
            created_at=now,
            proposal=proposal,
            evaluation=evaluation,
            approved_by="rejected",
            constitutional_check="fail" if constitutional_failure else "pass",
            # FM-P4-17: Empty string for rejected records (no rollback point)
            rollback_commit="",
            outcome=EvolutionOutcome.REJECTED,
            verification_passed=False,
        )
        self._persist_record(record)
        self._log_outcome(record)
        return record

    def _hold(
        self,
        proposal: EvolutionProposal,
        evaluation: EvaluationResult,
        now: datetime,
    ) -> EvolutionRecord:
        """Create a held-for-human evolution record."""
        logger.info(
            f"Evolution {proposal.id} held for human review: "
            f"score {evaluation.overall_score:.2f} is marginal"
        )

        record = EvolutionRecord(
            id=generate_id("evo-rec"),
            created_at=now,
            proposal=proposal,
            evaluation=evaluation,
            approved_by="held_for_human",
            constitutional_check="pass",
            rollback_commit="",
            outcome=EvolutionOutcome.HELD,
            verification_passed=False,
        )
        self._persist_record(record)
        self._log_outcome(record)
        return record

    def _verify_post_commit(self) -> bool:
        """Verify framework is still operational after commit.

        Checks:
        1. Constitution hash still valid
        2. evolution.yaml still parseable (FM-P4-39)
        """
        # 1. Constitution hash
        if not self.constitution_guard.verify_hash():
            logger.error("Post-commit verification: constitution hash INVALID")
            return False

        # 2. FM-P4-39-FIX: Verify evolution.yaml still loads correctly
        try:
            self.yaml_store.read_raw("core/evolution.yaml")
        except Exception as e:
            logger.error(f"Post-commit verification: evolution.yaml load failed: {e}")
            return False

        return True

    def _check_objective_alignment(self) -> None:
        """Check objective alignment using ObjectiveAnchor (Phase 5) or
        built-in heuristic (Phase 4 fallback).

        M-04-FIX: Uses canonical ObjectiveAlignmentError from evolution_engine.
        ObjectiveAnchor.check_alignment() raises AnchorAlignmentError which
        is caught and re-raised as the canonical type.

        FM-P4-48-FIX: Sets persistent pause flag on alignment failure.
        """
        if self._objective_anchor is not None:
            try:
                result = self._objective_anchor.check_alignment(
                    self._state.evolution_count
                )
            except AnchorAlignmentError as e:
                # Re-raise as canonical type for consistent handling
                self._state.paused = True
                self._state.pause_reason = str(e)
                self._save_state()
                raise ObjectiveAlignmentError(str(e)) from e

            if not result.passed:
                self._state.paused = True
                self._state.pause_reason = (
                    f"Objective alignment concern: {result.detail}"
                )
                self._save_state()
                raise ObjectiveAlignmentError(
                    f"ObjectiveAnchor check failed: {result.detail}. "
                    f"Evolution paused."
                )
            return

        # Phase 4 heuristic fallback (unchanged from Phase 4)
        # S-06-FIX: Phase 4 uses 50% threshold (hardcoded). ObjectiveAnchor
        # uses 80% (from config). When ObjectiveAnchor is None (Phase 4 mode),
        # the 50% heuristic remains active.
        records_dir = self.yaml_store.base_dir / self._records_dir
        if not records_dir.exists() or not records_dir.is_dir():
            raise EvolutionError(
                f"Objective alignment check triggered at evolution "
                f"#{self._state.evolution_count} but records directory "
                f"'{records_dir}' does not exist. Persistence is broken."
            )

        record_files = sorted(
            f for f in records_dir.iterdir() if f.suffix in (".yaml", ".yml")
        )
        recent = record_files[-10:] if len(record_files) >= 10 else record_files

        if not recent:
            raise EvolutionError(
                f"Objective alignment check triggered at evolution "
                f"#{self._state.evolution_count} but no record files found "
                f"in '{records_dir}'."
            )

        rejected_or_rolled_back = 0
        total = 0
        for rf in recent:
            try:
                data = self.yaml_store.read_raw(
                    str(rf.relative_to(self.yaml_store.base_dir))
                )
            except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
                raise EvolutionError(
                    f"Cannot read evolution record {rf} during "
                    f"objective alignment check: {e}"
                ) from e
            outcome = data["outcome"]  # KeyError if missing — fail-loud
            total += 1
            if outcome in ("rejected", "rolled_back"):
                rejected_or_rolled_back += 1

        if total == 0:
            return

        failure_rate = rejected_or_rolled_back / total
        logger.info(
            f"Objective alignment check at evolution #{self._state.evolution_count}: "
            f"{rejected_or_rolled_back}/{total} failed ({failure_rate:.0%})"
        )

        if failure_rate > 0.5:
            self._state.paused = True
            self._state.pause_reason = (
                f"Objective alignment concern: {failure_rate:.0%} of recent "
                f"evolutions failed. Human review required."
            )
            self._save_state()
            raise ObjectiveAlignmentError(
                f"Alignment check failed: {rejected_or_rolled_back}/{total} "
                f"recent evolutions rejected/rolled back ({failure_rate:.0%}). "
                f"Evolution paused. Human intervention required."
            )

    def _git_paths(self, candidate: DualCopyCandidate) -> list[str]:
        """Convert candidate's modified_files to git-relative paths."""
        return [f"{self._instance_prefix}{f}" for f in candidate.modified_files]

    def _persist_record(self, record: EvolutionRecord) -> None:
        """Persist evolution record to disk."""
        self.yaml_store.write(
            f"{self._records_dir}/{record.id}.yaml", record
        )

    def _load_state(self) -> EvolutionEngineState:
        """Load persistent state from disk. Create default if missing (FM-P4-23)."""
        try:
            return self.yaml_store.read(self._state_path, EvolutionEngineState)
        except FileNotFoundError:
            return EvolutionEngineState()

    def _save_state(self) -> None:
        """Persist state to disk (FM-P4-23)."""
        self.yaml_store.write(self._state_path, self._state)

    def _log_lifecycle(
        self,
        proposal: EvolutionProposal,
        state: EvolutionLifecycleState,
    ) -> None:
        """Log a lifecycle state transition to audit stream.

        DR-06-FIX: Narrow exception handling, re-raise critical errors.
        """
        now = datetime.now(timezone.utc)
        tier_int = int(proposal.tier)
        try:
            # strict=False: use_enum_values stores enums as primitives,
            # so model_validate with strict=False is needed for reconstruction
            # (same pattern as YamlStore.read)
            entry = EvolutionLogEntry.model_validate({
                "id": generate_id("evlog"),
                "timestamp": now,
                "tier": tier_int,
                "component": proposal.component,
                "diff": proposal.diff[:500],  # Truncate for log
                "rationale": proposal.rationale,
                "evidence": proposal.evidence,
                "lifecycle_state": str(state),
                "trigger": str(proposal.trigger),
            }, strict=False)
            self.audit_logger.log_evolution(entry)
            self._audit_failure_count = 0  # Reset on success
        except OSError as e:
            self._audit_failure_count += 1
            logger.error(f"Failed to log evolution lifecycle event: {e}")
            if self._audit_failure_count >= self._max_audit_failures:
                raise EvolutionError(
                    f"Audit logging failed {self._audit_failure_count} times "
                    f"consecutively. Halting evolution to preserve audit "
                    f"integrity. Last error: {e}"
                ) from e
        # ValueError/TypeError indicate bugs in entry construction — propagate

    def _log_outcome(self, record: EvolutionRecord) -> None:
        """Log the final evolution outcome to audit stream."""
        now = datetime.now(timezone.utc)
        tier_int = int(record.proposal.tier)

        # Validate evaluation presence for non-rejected outcomes
        eval_score = 0.0
        if record.evaluation is not None:
            eval_score = record.evaluation.overall_score
        elif str(record.outcome) != str(EvolutionOutcome.REJECTED):
            raise EvolutionError(
                f"Record {record.id} has outcome {record.outcome} but no "
                f"evaluation. Non-rejected records must have evaluations."
            )

        try:
            entry = EvolutionLogEntry.model_validate({
                "id": generate_id("evlog"),
                "timestamp": now,
                "tier": tier_int,
                "component": record.proposal.component,
                "diff": record.proposal.diff[:500],
                "rationale": record.proposal.rationale,
                "evidence": record.proposal.evidence,
                "lifecycle_state": "complete",
                "outcome": str(record.outcome),
                "evaluation_score": eval_score,
                "trigger": str(record.proposal.trigger),
            }, strict=False)
            self.audit_logger.log_evolution(entry)
            self._audit_failure_count = 0  # Reset on success
        except OSError as e:
            self._audit_failure_count += 1
            logger.error(f"Failed to log evolution outcome: {e}")
            if self._audit_failure_count >= self._max_audit_failures:
                raise EvolutionError(
                    f"Audit logging failed {self._audit_failure_count} times "
                    f"consecutively. Halting evolution. Last error: {e}"
                ) from e
        # ValueError/TypeError indicate bugs — propagate

    # ── Phase 5: Governance methods ──

    def _initiate_tier2_quorum(self, proposal: EvolutionProposal) -> str:
        """Phase 1: Create quorum session for a Tier 2 proposal.

        M-02-FIX: Two-phase design. This method creates the session and
        returns its ID. Votes are collected externally (by the orchestrator
        or run loop). complete_tier2_evolution() is called after votes arrive.

        Returns:
            Quorum session ID.

        Raises:
            InsufficientVotersError: If not enough eligible voters.
            QuorumError: If quorum creation fails.
        """
        if self._quorum_manager is None:
            raise QuorumError(
                "QuorumManager not configured — cannot run Tier 2 quorum"
            )

        role_registry = self._build_role_registry()
        session = self._quorum_manager.create_session(
            proposal, role_registry, proposer_role=""
        )
        return session.id

    def complete_tier2_evolution(
        self, proposal_id: str, quorum_session_id: str
    ) -> EvolutionRecord:
        """Phase 2: Complete a HELD Tier 2 evolution after quorum votes collected.

        M-02-FIX: Called by orchestrator/run loop after external vote collection.
        Tallies votes and either promotes or rejects the held evolution.

        Args:
            proposal_id: The evolution proposal ID.
            quorum_session_id: The quorum session to tally.

        Returns:
            Updated EvolutionRecord (PROMOTED or REJECTED).

        Raises:
            QuorumError: If tally fails.
            EvolutionError: If proposal or held record not found.
        """
        now = datetime.now(timezone.utc)

        # Load the held record
        held_record = self._load_held_record(proposal_id)
        if held_record is None:
            raise EvolutionError(
                f"No HELD record found for proposal {proposal_id}"
            )

        # Check for timeout first
        if self._quorum_manager.check_timeout(quorum_session_id):
            self.dual_copy_manager.cleanup_fork(
                self._load_candidate(held_record)
            )
            return self._transition_held_to_rejected(
                held_record,
                f"Quorum session {quorum_session_id} timed out",
                now,
            )

        # Tally votes
        quorum_result = self._quorum_manager.tally(quorum_session_id)

        if not quorum_result.approved:
            candidate = self._load_candidate(held_record)
            self.dual_copy_manager.cleanup_fork(candidate)
            reject_count = sum(1 for v in quorum_result.votes if v.vote == "reject")
            return self._transition_held_to_rejected(
                held_record,
                f"Quorum rejected: {reject_count}/{len(quorum_result.votes)} reject "
                f"(threshold: {quorum_result.threshold:.0%})",
                now,
            )

        # Quorum approved — promote
        approved_by = (
            f"quorum ({sum(1 for v in quorum_result.votes if v.vote == 'approve')}"
            f"/{len(quorum_result.votes)} approve)"
        )
        return self._promote_held_record(
            held_record, quorum_result, approved_by, now
        )

    def _build_role_registry(self) -> list[dict]:
        """Build role registry from compositions + role metadata.

        FM-P5-34-FIX: Role compositions don't contain runtime fields
        (task_count, lineage_id). These come from a separate role metadata
        file at state/roles/role_metadata.yaml, maintained by the
        orchestrator as agents complete tasks.

        Compositions provide: name, scout_config.
        Role metadata provides: task_count, lineage_id, created_by_evolution.

        Returns list of role info dicts for quorum eligibility computation.
        Sorted deterministically by name (FM-P5-63-FIX).
        """
        compositions_dir = self.yaml_store.base_dir / "roles" / "compositions"
        if not compositions_dir.exists():
            return []

        # Load role metadata (runtime stats)
        try:
            metadata = self.yaml_store.read_raw("state/roles/role_metadata.yaml")
        except FileNotFoundError:
            logger.warning(
                "state/roles/role_metadata.yaml not found — "
                "no roles will meet maturity requirement"
            )
            metadata = {}

        registry: list[dict] = []
        # FM-P5-63-FIX: Sort files for deterministic ordering
        for comp_file in sorted(compositions_dir.iterdir()):
            if comp_file.suffix not in (".yaml", ".yml"):
                continue
            try:
                rel_path = str(comp_file.relative_to(self.yaml_store.base_dir))
                data = self.yaml_store.read_raw(rel_path)

                role_name = data["name"]  # KeyError = fail-loud (FM-P5-34)
                role_meta = metadata.get(role_name, {})

                registry.append({
                    "name": role_name,
                    "task_count": int(role_meta.get("task_count", 0)),
                    "lineage_id": str(role_meta.get("lineage_id", "")),
                    "created_by_evolution": str(role_meta.get("created_by_evolution", "")),
                    "is_scout": data.get("scout_config") is not None,
                })
            except KeyError as e:
                raise EvolutionError(
                    f"Role composition {comp_file.name} missing required "
                    f"field {e}. Fix the composition file."
                )
            except (FileNotFoundError, ValueError) as e:
                logger.warning(f"Skipping role composition {comp_file}: {e}")

        return registry

    def _queue_for_human(
        self, proposal: EvolutionProposal, now: datetime
    ) -> EvolutionRecord:
        """Queue a Tier 1 proposal for human approval.

        Phase 5: Creates queue entry but does NOT process. The autonomous
        run loop (Phase 6+) will present these to the human.
        """
        from ..models.governance import HumanDecision

        decision = HumanDecision(
            id=generate_id("hd"),
            created_at=now,
            decision_type="tier1_evolution_approval",
            summary=f"Tier 1 evolution: {proposal.rationale}",
            proposed_by="evolution_engine",
            blocking=False,
            blocking_tasks=[],
        )

        # Persist to human decision queue
        queue_path = "state/governance/pending_human_decisions"
        self.yaml_store.write(f"{queue_path}/{decision.id}.yaml", decision)

        logger.info(
            f"Tier 1 proposal {proposal.id} queued for human approval: {decision.id}"
        )

        return self._reject(
            proposal,
            f"Tier 1 proposals require human approval. Queued as {decision.id}.",
            now,
        )

    def _create_held_record(
        self,
        proposal: EvolutionProposal,
        evaluation: EvaluationResult,
        candidate: DualCopyCandidate,
        now: datetime,
        reason: str,
    ) -> EvolutionRecord:
        """Create a HELD evolution record for Tier 2 pending quorum.

        FM-P5-58: Helper for the two-phase quorum API. Persists the
        candidate info so complete_tier2_evolution() can resume later.
        """
        record = EvolutionRecord(
            id=generate_id("evo"),
            created_at=now,
            proposal=proposal,
            evaluation=evaluation,
            outcome=EvolutionOutcome.HELD,
            approved_by=reason,
            constitutional_check="pass",
        )
        # Persist record and candidate reference
        self.yaml_store.write(
            f"state/evolution/records/{record.id}.yaml", record
        )
        self.yaml_store.write(
            f"state/evolution/candidates/{proposal.id}/held_candidate.yaml",
            candidate,
        )
        # S-CR-03-FIX: Do NOT increment evolution_count here.
        # Counter only increments on actual PROMOTED outcome
        # (in _promote_held_record or Tier 3 commit path).
        return record

    def _load_held_record(self, proposal_id: str) -> EvolutionRecord | None:
        """Load a HELD record by proposal ID (FM-P5-59)."""
        records_dir = self.yaml_store.base_dir / "state/evolution/records"
        if not records_dir.exists():
            return None
        for f in sorted(records_dir.iterdir()):
            if f.suffix not in (".yaml", ".yml"):
                continue
            data = self.yaml_store.read_raw(str(f.relative_to(self.yaml_store.base_dir)))
            if (data.get("proposal", {}).get("id") == proposal_id
                    and data.get("outcome") == "held"):
                return self.yaml_store.read(
                    str(f.relative_to(self.yaml_store.base_dir)),
                    EvolutionRecord,
                )
        return None

    def _load_candidate(self, held_record: EvolutionRecord) -> DualCopyCandidate:
        """Load DualCopyCandidate from a HELD record (FM-P5-60)."""
        proposal_id = held_record.proposal.id
        path = f"state/evolution/candidates/{proposal_id}/held_candidate.yaml"
        return self.yaml_store.read(path, DualCopyCandidate)

    def _transition_held_to_rejected(
        self,
        held_record: EvolutionRecord,
        reason: str,
        now: datetime,
    ) -> EvolutionRecord:
        """Transition a HELD record to REJECTED (FM-P5-61)."""
        held_record.outcome = EvolutionOutcome.REJECTED
        held_record.approved_by = reason
        self.yaml_store.write(
            f"state/evolution/records/{held_record.id}.yaml",
            held_record,
        )
        return held_record

    def _promote_held_record(
        self,
        held_record: EvolutionRecord,
        quorum_result,
        approved_by: str,
        now: datetime,
    ) -> EvolutionRecord:
        """Promote a HELD record after quorum approval (FM-P5-62).

        S-CR-04-FIX: Includes Git commit, ring enforcement, and
        post-commit verification — same safety as Tier 3 path.
        """
        candidate = self._load_candidate(held_record)

        # Create rollback point before promotion
        rollback_sha = self.git_ops.create_rollback_point()

        # Promote: copy fork files to active positions
        self.dual_copy_manager.promote(candidate)

        # Git commit
        git_files = self._git_paths(candidate)
        try:
            evolution_sha = self.git_ops.commit_evolution(
                evo_id=held_record.proposal.id,
                tier=int(held_record.proposal.tier),
                rationale=held_record.proposal.rationale,
                approved_by=approved_by,
                files=git_files,
            )
        except GitOpsError as e:
            logger.error(f"Git commit failed for {held_record.id}: {e}")
            if candidate.promoted:
                try:
                    self.git_ops.rollback_to(rollback_sha)
                except GitOpsError as re:
                    self._state.paused = True
                    self._state.pause_reason = (
                        f"CRITICAL: Tier 2 commit failed AND rollback failed "
                        f"for {held_record.id}. Error: {e}. Rollback: {re}"
                    )
                    self._save_state()
                    raise EvolutionError(
                        f"Tier 2 commit and rollback both failed for "
                        f"{held_record.id}. Manual intervention required."
                    ) from re
            self.dual_copy_manager.cleanup_fork(candidate)
            return self._transition_held_to_rejected(
                held_record, f"Git commit failed: {e}", now,
            )

        # Ring enforcement verification
        try:
            self.ring_enforcer.verify_no_ring_0_modification(git_files)
        except RingViolationError as e:
            logger.error(
                f"Ring 0 violation in Tier 2 promotion {held_record.id}: {e}"
            )
            self.git_ops.rollback_to(rollback_sha)
            self.dual_copy_manager.cleanup_fork(candidate)
            return self._transition_held_to_rejected(
                held_record, f"Ring 0 violation: {e}", now,
            )

        self.dual_copy_manager.cleanup_fork(candidate)

        held_record.outcome = EvolutionOutcome.PROMOTED
        held_record.approved_by = approved_by
        held_record.quorum = quorum_result
        held_record.evolution_commit = evolution_sha
        held_record.rollback_commit = rollback_sha
        held_record.verification_passed = True
        self.yaml_store.write(
            f"state/evolution/records/{held_record.id}.yaml",
            held_record,
        )

        # S-CR-03-FIX: Increment evolution count only on PROMOTED
        self._state.evolution_count += 1
        self._save_state()

        # Update archive
        self.archive.update_from_evolution(held_record)

        logger.info(
            f"Evolution {held_record.id} PROMOTED via quorum: {approved_by}"
        )
        return held_record

    # ------------------------------------------------------------------
    # Phase 8: Population-based evolution
    # ------------------------------------------------------------------

    def run_population_evolution(
        self,
        proposal: EvolutionProposal,
        population_size: int | None = None,
    ) -> EvolutionRecord:
        """Run population-based evolution for a proposal.

        Generates multiple candidates, evaluates all, selects best.
        If winner meets promote threshold, promotes it through the
        existing single-fork pipeline (Steps 5-8: approve→commit→verify→log).

        Args:
            proposal: Base proposal to generate variants from.
            population_size: Number of candidates (default from config).

        Returns:
            EvolutionRecord with outcome.

        Raises:
            EvolutionError: If population evolver not configured.
            PopulationError: On non-recoverable population failures.
        """
        if self._population_evolver is None:
            raise EvolutionError(
                "Population evolution requires PopulationEvolver. "
                "Configure it in EvolutionEngine constructor."
            )
        if self._gap_monitor is None:
            raise EvolutionError(
                "Population evolution requires GapMonitor. "
                "Configure it in EvolutionEngine constructor."
            )
        if self._stagnation_detector is None:
            raise EvolutionError(
                "Population evolution requires StagnationDetector. "
                "Configure it in EvolutionEngine constructor."
            )

        now = datetime.now(timezone.utc)

        # FM-P4-48-FIX: Check persistent pause flag
        if self._state.paused:
            return self._reject(
                proposal,
                f"Evolution paused: {self._state.pause_reason}",
                now,
            )

        # FM-P8-006: Tier/safety/constitutional checks before population run
        tier_int = int(proposal.tier)
        if tier_int == EvolutionTier.CONSTITUTIONAL:
            return self._reject(
                proposal,
                "Tier 0 (constitutional) evolution is NEVER allowed.",
                now,
            )
        if tier_int == EvolutionTier.FRAMEWORK:
            return self._reject(
                proposal,
                "Tier 1 (framework) proposals cannot use population mode.",
                now,
            )

        safety_ok, safety_reason = self._check_proposal_safety(proposal)
        if not safety_ok:
            return self._reject(proposal, safety_reason, now)

        const_ok, const_reason = self.constitution_guard.check_proposal(proposal)
        if not const_ok:
            return self._reject(
                proposal, f"Constitutional: {const_reason}", now,
                constitutional_failure=True,
            )

        try:
            yaml.safe_load(proposal.diff)
        except yaml.YAMLError as e:
            return self._reject(proposal, f"Diff is not valid YAML: {e}", now)

        # Run population — returns winner fork alive (M-01/FM-P8-013 fix)
        pop_run, winner_fork, winner_proposal = (
            self._population_evolver.run_population(
                base_proposal=proposal,
                population_size=population_size,
            )
        )

        try:
            if pop_run.outcome == PopulationOutcome.PROMOTED:
                # Winner fork is alive — promote with full safety pipeline
                winner_result = next(
                    c for c in pop_run.candidates
                    if c.candidate_id == pop_run.winner_id
                )

                # Step 6: COMMIT — rollback point, promote, git commit
                rollback_sha = self.git_ops.create_rollback_point()

                evolution_sha = ""
                try:
                    self.dual_copy_manager.promote(winner_fork)

                    git_files = self._git_paths(winner_fork)
                    tier_val = winner_proposal.tier
                    tier_int = tier_val if isinstance(tier_val, int) else int(tier_val)
                    evolution_sha = self.git_ops.commit_evolution(
                        evo_id=winner_proposal.id,
                        tier=tier_int,
                        rationale=winner_proposal.rationale,
                        approved_by="population_tournament",
                        files=git_files,
                    )
                except (GitOpsError, PromotionError) as e:
                    logger.error(
                        f"Population commit failed for {proposal.id}: {e}"
                    )
                    if winner_fork.promoted:
                        try:
                            self.git_ops.rollback_to(rollback_sha)
                        except GitOpsError as re:
                            self._state.paused = True
                            self._state.pause_reason = (
                                f"CRITICAL: Population commit failed AND rollback "
                                f"failed for {proposal.id}. Commit: {e}. "
                                f"Rollback: {re}"
                            )
                            self._save_state()
                            raise EvolutionError(
                                f"Population commit failed for {proposal.id} AND "
                                f"rollback to {rollback_sha} failed: {re}. "
                                f"Evolution paused."
                            ) from re
                    return self._reject(
                        proposal,
                        f"Population commit failed: {e}",
                        now,
                    )

                # Step 7: VERIFY — Ring 0 check + post-commit checks
                git_files = self._git_paths(winner_fork)
                try:
                    self.ring_enforcer.verify_no_ring_0_modification(git_files)
                    ring_check_passed = True
                except RingViolationError as e:
                    logger.error(
                        f"Ring 0 violation in population evolution "
                        f"{proposal.id}: {e}"
                    )
                    ring_check_passed = False

                verification_ok = self._verify_post_commit() and ring_check_passed

                if not verification_ok:
                    if evolution_sha and evolution_sha != rollback_sha:
                        logger.error(
                            f"Population post-commit verification failed for "
                            f"{proposal.id}. Rolling back to {rollback_sha[:8]}."
                        )
                        try:
                            self.git_ops.rollback_to(rollback_sha)
                        except GitOpsError as e:
                            self._state.paused = True
                            self._state.pause_reason = (
                                f"CRITICAL: Population verification failed AND "
                                f"rollback failed for {proposal.id}."
                            )
                            self._save_state()
                            raise EvolutionError(
                                f"Population verification failed for "
                                f"{proposal.id} AND rollback failed: {e}. "
                                f"Evolution paused."
                            ) from e
                    return self._reject(
                        proposal,
                        f"Population post-commit verification failed",
                        now,
                    )

                # Step 8: LOG — create record, update archive, track metrics
                # Create synthetic EvaluationResult from winner's scores
                # (_log_outcome requires evaluation on non-rejected records)
                winner_eval = EvaluationResult(
                    id=winner_result.evaluation_id or generate_id("eval"),
                    created_at=now,
                    proposal_id=winner_proposal.id,
                    candidate_id=winner_result.candidate_id,
                    overall_score=winner_result.overall_score,
                    verdict=EvolutionOutcome.PROMOTED,
                )
                record = EvolutionRecord(
                    id=generate_id("evo-rec"),
                    created_at=now,
                    proposal=winner_proposal,
                    evaluation=winner_eval,
                    outcome=EvolutionOutcome.PROMOTED,
                    approved_by="population_tournament",
                    constitutional_check="pass",
                    rollback_commit=rollback_sha,
                    evolution_commit=evolution_sha,
                    verification_passed=True,
                )
                self._persist_record(record)
                self._log_outcome(record)

                # Update archive (narrowed to IO/data errors)
                try:
                    self.archive.update_from_evolution(record)
                except (OSError, ValueError, yaml.YAMLError) as e:
                    logger.error(
                        f"Population archive update failed for {record.id}: {e}"
                    )

                # S-CR-03-FIX: Increment evolution count only on PROMOTED
                self._state.evolution_count += 1
                self._state.tasks_since_last_evolution = 0
                self._save_state()

                # Gap monitor + calibration check
                self._gap_monitor.record_promotion()
                action = self._gap_monitor.check_calibration()
                if action != GapCalibrationAction.HOLD:
                    self._gap_monitor.apply_calibration(action)

                # Wire stagnation detector (FM-P8-035 fix)
                self._stagnation_detector.record_evolution_outcome(
                    promoted=True
                )

                return record

            elif pop_run.outcome == PopulationOutcome.HELD:
                # FM-P8-028: HELD has dedicated handling
                # Create synthetic evaluation for audit log
                held_eval = EvaluationResult(
                    id=generate_id("eval"),
                    created_at=now,
                    proposal_id=proposal.id,
                    candidate_id=pop_run.winner_id or "",
                    overall_score=0.0,
                    verdict=EvolutionOutcome.HELD,
                    verdict_reason=pop_run.reason,
                )
                record = EvolutionRecord(
                    id=generate_id("evo-rec"),
                    created_at=now,
                    proposal=proposal,
                    evaluation=held_eval,
                    outcome=EvolutionOutcome.HELD,
                    approved_by="population_held",
                    constitutional_check="pass",
                    rollback_commit="",
                    verification_passed=False,
                )
                self._persist_record(record)
                self._log_outcome(record)
                # Persist to held queue for human review
                held_path = f"{self._base}/held/{record.id}.yaml"
                self.yaml_store.write(held_path, record)
                logger.info(
                    f"Population evolution held for review: {record.id}"
                )
                return record

            else:
                # ALL_REJECTED or CANCELLED
                self._gap_monitor.record_rejection()
                self._stagnation_detector.record_evolution_outcome(
                    promoted=False
                )
                return self._reject(
                    proposal,
                    f"Population evolution: {pop_run.reason}",
                    now,
                )

        finally:
            # Always cleanup winner fork (whether promoted or not)
            if winner_fork is not None:
                try:
                    self.dual_copy_manager.cleanup_fork(winner_fork)
                except OSError as e:
                    logger.error(
                        f"Failed to cleanup winner fork "
                        f"{winner_fork.evo_id}: {e}"
                    )
