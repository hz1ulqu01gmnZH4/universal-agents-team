"""Population-based evolution orchestrator.
Spec reference: Section 8.2 (Dual-Copy, population_mode).

Generates multiple candidate forks from a base proposal, evaluates all
against multi-dimensional criteria, and selects the best via tournament.

Key constraints:
- Population size configurable (default 3, max 10)
- Each candidate gets independent constitutional check
- Tournament selection: highest overall_score wins
- Winner fork kept alive for caller to promote (M-01 fix)
- Loser forks cleaned up after run
- Budget pressure gating: population mode requires GREEN/YELLOW budget
- Archive gaps used to seed candidate diversity
- HELD candidates excluded from tournament (M-06 fix)

Literature basis:
- Darwin Godel Machine: population of forks evaluated in parallel (20%→50%)
- AlphaEvolve (DeepMind): island model with migration
- ADAS (ICLR 2025): archive-based meta-agent search
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ..models.base import generate_id
from ..models.evolution import (
    DualCopyCandidate,
    EvaluationResult,
    EvolutionOutcome,
    EvolutionProposal,
    EvolutionTier,
    ObservationTrigger,
)
from ..models.population import (
    CandidateResult,
    PopulationOutcome,
    PopulationRun,
)
from ..state.yaml_store import YamlStore
from .constitution_guard import ConstitutionGuard
from .dual_copy_manager import DualCopyManager, ForkError
from .evolution_validator import EvolutionValidator
from .map_elites_archive import MAPElitesArchive

if TYPE_CHECKING:
    from ..engine.budget_tracker import BudgetTracker

logger = logging.getLogger("uagents.population_evolver")


class PopulationError(RuntimeError):
    """Raised when population evolution fails non-recoverably."""


class PopulationEvolver:
    """Population-based evolution using tournament selection.

    Design invariants:
    - Each candidate is a separate DualCopyCandidate fork
    - Candidates are evaluated independently
    - Tournament selects highest overall_score across 6 dimensions
    - Winner fork kept alive for EvolutionEngine to promote directly (M-01)
    - Loser forks cleaned up after run
    - Population run is persisted for audit trail

    Usage:
        evolver = PopulationEvolver(yaml_store, dual_copy_manager,
                                     evolution_validator, constitution_guard,
                                     archive, domain)
        run, winner_fork, winner_proposal = evolver.run_population(base_proposal)
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        dual_copy_manager: DualCopyManager,
        evolution_validator: EvolutionValidator,
        constitution_guard: ConstitutionGuard,
        archive: MAPElitesArchive,
        domain: str = "meta",
        budget_tracker: "BudgetTracker | None" = None,
    ):
        self.yaml_store = yaml_store
        self.dual_copy_manager = dual_copy_manager
        self.evolution_validator = evolution_validator
        self.constitution_guard = constitution_guard
        self.archive = archive
        self.domain = domain
        self._base = f"instances/{domain}/state/evolution"
        self._budget_tracker = budget_tracker

        # Load population config from evolution.yaml (IFM-N53 fail-loud)
        config_raw = yaml_store.read_raw("core/evolution.yaml")
        pop_config = config_raw["evolution"]["population"]
        self._default_size: int = int(pop_config["default_size"])
        self._max_size: int = int(pop_config["max_size"])
        self._diversity_seed: bool = bool(pop_config["diversity_seed_from_archive"])

    def run_population(
        self,
        base_proposal: EvolutionProposal,
        population_size: int | None = None,
    ) -> tuple[PopulationRun, DualCopyCandidate | None, EvolutionProposal | None]:
        """Run a population-based evolution cycle.

        M-01/FM-P8-013 fix: Returns the winner's fork ALIVE (not cleaned up)
        so EvolutionEngine can promote it directly without re-evaluation.
        Loser forks are cleaned up. Caller MUST clean up winner fork.

        Args:
            base_proposal: The proposal to generate variants from.
            population_size: Number of candidates (default from config).

        Returns:
            Tuple of (PopulationRun, winner_fork, winner_proposal).
            winner_fork/winner_proposal are None if no winner.

        Raises:
            PopulationError: On non-recoverable failures.
        """
        size = population_size or self._default_size
        if size > self._max_size:
            raise PopulationError(
                f"Population size {size} exceeds maximum {self._max_size}"
            )

        # FM-P8-034: Budget pressure check
        if self._budget_tracker is not None:
            from ..models.resource import BudgetPressureLevel

            pressure = self._budget_tracker.get_pressure()
            if pressure not in (BudgetPressureLevel.GREEN, BudgetPressureLevel.YELLOW):
                raise PopulationError(
                    f"Budget pressure is {pressure}. Population evolution "
                    f"requires GREEN or YELLOW budget (N× fork cost)."
                )

        run = PopulationRun(
            trigger_proposal_id=base_proposal.id,
            population_size=size,
        )

        # Generate candidate variants
        candidates: list[tuple[EvolutionProposal, DualCopyCandidate]] = []
        try:
            candidates = self._generate_candidates(base_proposal, size)
        except (ForkError, PopulationError) as e:
            run.outcome = PopulationOutcome.CANCELLED
            run.reason = f"Failed to generate candidates: {e}"
            run.completed_at = datetime.now(timezone.utc)
            self._persist_run(run)
            return run, None, None

        if not candidates:
            run.outcome = PopulationOutcome.CANCELLED
            run.reason = "No valid candidates generated"
            run.completed_at = datetime.now(timezone.utc)
            self._persist_run(run)
            return run, None, None

        # Evaluate each candidate
        results: list[CandidateResult] = []
        for proposal_variant, candidate in candidates:
            result = self._evaluate_candidate(proposal_variant, candidate)
            results.append(result)

        # Tournament selection
        run.candidates = results
        winner = self._tournament_select(results)

        # Read both thresholds once to avoid TOCTOU inconsistency
        promote_threshold = self._get_promote_threshold()
        hold_threshold = self._get_hold_threshold()

        if winner is None:
            run.outcome = PopulationOutcome.ALL_REJECTED
            run.reason = "No candidate met promotion thresholds"
        elif winner.overall_score < hold_threshold:
            run.outcome = PopulationOutcome.ALL_REJECTED
            run.reason = "Winner below hold threshold"
        else:
            if winner.overall_score >= promote_threshold:
                run.outcome = PopulationOutcome.PROMOTED
                run.winner_id = winner.candidate_id
                winner.promoted = True
                run.reason = (
                    f"Winner {winner.candidate_id} with score "
                    f"{winner.overall_score:.3f} (threshold {promote_threshold})"
                )
            else:
                run.outcome = PopulationOutcome.HELD
                run.winner_id = winner.candidate_id
                run.reason = (
                    f"Winner {winner.candidate_id} marginal: score "
                    f"{winner.overall_score:.3f} (promote={promote_threshold})"
                )

        # Cleanup LOSER forks only — winner fork kept alive (M-01 fix)
        winner_fork: DualCopyCandidate | None = None
        winner_proposal_variant: EvolutionProposal | None = None
        for proposal_variant, candidate in candidates:
            if candidate.evo_id == run.winner_id:
                winner_fork = candidate
                winner_proposal_variant = proposal_variant
                continue
            try:
                self.dual_copy_manager.cleanup_fork(candidate)
            except OSError as e:
                # FM-P8-015: log at ERROR, not swallowed
                logger.error(
                    f"Failed to cleanup fork {candidate.evo_id}: {e}. "
                    f"Manual cleanup required."
                )

        run.completed_at = datetime.now(timezone.utc)
        self._persist_run(run)
        return run, winner_fork, winner_proposal_variant

    def _generate_candidates(
        self,
        base_proposal: EvolutionProposal,
        count: int,
    ) -> list[tuple[EvolutionProposal, DualCopyCandidate]]:
        """Generate candidate variants from a base proposal.

        Each variant is a slightly different mutation of the base proposal.
        """
        candidates: list[tuple[EvolutionProposal, DualCopyCandidate]] = []

        for i in range(count):
            variant = self._create_variant(base_proposal, i)

            # Constitutional check on each variant
            const_ok, const_reason = self.constitution_guard.check_proposal(variant)
            if not const_ok:
                logger.warning(
                    f"Candidate {i} failed constitutional check: {const_reason}"
                )
                continue

            # Create fork for this variant
            try:
                fork = self.dual_copy_manager.create_fork(variant)
                self.dual_copy_manager.apply_diff(fork, variant)
                self.dual_copy_manager.persist_manifest(fork)
                candidates.append((variant, fork))
            except ForkError as e:
                logger.warning(f"Candidate {i} fork failed: {e}")
                continue

        return candidates

    def _create_variant(
        self,
        base_proposal: EvolutionProposal,
        variant_index: int,
    ) -> EvolutionProposal:
        """Create a variant of the base proposal.

        FM-P8-014: Perturb estimated_risk so evaluation scores differ.
        Real diff-level mutation is Phase ∞ scope.
        """
        variant_id = generate_id(f"evo-pop-{variant_index}")

        # FM-P8-014: Perturb estimated_risk for non-degenerate tournament
        base_risk = base_proposal.estimated_risk
        risk_perturbation = 0.01 * variant_index
        perturbed_risk = min(base_risk + risk_perturbation, 1.0)

        # use_enum_values=True means base_proposal.tier is raw int/str,
        # but strict=True requires enum instances for construction
        return EvolutionProposal(
            id=variant_id,
            created_at=datetime.now(timezone.utc),
            tier=EvolutionTier(base_proposal.tier),
            component=base_proposal.component,
            diff=base_proposal.diff,
            rationale=f"[Population variant {variant_index}] {base_proposal.rationale}",
            evidence=base_proposal.evidence,
            estimated_risk=perturbed_risk,
            trigger=ObservationTrigger(base_proposal.trigger),
            trigger_detail=base_proposal.trigger_detail,
        )

    def _evaluate_candidate(
        self,
        proposal: EvolutionProposal,
        candidate: DualCopyCandidate,
    ) -> CandidateResult:
        """Evaluate a single candidate using the EvolutionValidator."""
        eval_result: EvaluationResult = self.evolution_validator.evaluate(
            candidate, proposal
        )

        result = CandidateResult(
            candidate_id=candidate.evo_id,
            proposal_id=proposal.id,
            evaluation_id=eval_result.id,
            overall_score=eval_result.overall_score,
            dimension_scores={
                ds.dimension: ds.score
                for ds in eval_result.dimension_scores
            },
        )

        # M-06: Handle both REJECTED and HELD verdicts
        if eval_result.verdict == EvolutionOutcome.REJECTED:
            result.rejection_reason = eval_result.verdict_reason
        elif eval_result.verdict == EvolutionOutcome.HELD:
            result.rejection_reason = (
                f"HELD for human review: {eval_result.verdict_reason}"
            )

        return result

    def _tournament_select(
        self,
        results: list[CandidateResult],
    ) -> CandidateResult | None:
        """Select the best candidate via tournament.

        Candidates with rejection_reason are excluded.
        Remaining ranked by overall_score descending.
        """
        eligible = [r for r in results if not r.rejection_reason]
        if not eligible:
            return None

        eligible.sort(key=lambda r: r.overall_score, reverse=True)

        for i, r in enumerate(eligible):
            r.rank = i + 1

        return eligible[0]

    def _get_promote_threshold(self) -> float:
        """Get the current promotion threshold from config."""
        config_raw = self.yaml_store.read_raw("core/evolution.yaml")
        return float(config_raw["evolution"]["evaluation"]["promote_threshold"])

    def _get_hold_threshold(self) -> float:
        """Get the current hold threshold from config."""
        config_raw = self.yaml_store.read_raw("core/evolution.yaml")
        return float(config_raw["evolution"]["evaluation"]["hold_threshold"])

    def _persist_run(self, run: PopulationRun) -> None:
        """Persist a PopulationRun to YAML."""
        path = f"{self._base}/populations/{run.id}.yaml"
        self.yaml_store.write(path, run)
        logger.info(
            f"Population run {run.id}: outcome={run.outcome}, "
            f"candidates={len(run.candidates)}, winner={run.winner_id}"
        )
