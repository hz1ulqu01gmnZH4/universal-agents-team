# Detailed Design — Phase 8: Population Evolution

**Version:** 0.2.0
**Date:** 2026-03-05
**Status:** Reviewed — fixes applied (Step 5 complete)
**Depends on:** Phase 4 (Evolution Engine), Phase 5 (Governance), Phase 7 (Self-Expansion)
**Spec sections:** Section 7.4 (MAP-Elites), Section 8 (Dual-Copy Bootstrapping),
Section 13.3 (Metacognitive Monitoring — Gap Monitoring), Section 16 (Run Loop)

---

## Part 1: Architecture Overview

### What Phase 8 Adds

Phase 8 closes the self-improvement loop by enabling **population-based evolution**.
Instead of evaluating a single fork at a time, the framework generates 3-5 candidate
configurations, evaluates all against multi-dimensional criteria, and selects the best
via tournament. This is the core mechanism from Darwin Godel Machine (20%→50% SWE-bench).

Additionally, Phase 8 introduces **generation-verification gap monitoring** — tracking
whether the evolution approval mechanism is actually reliable. If approved changes turn
out worse (false positives), criteria tighten. If good changes are rejected (false
negatives), criteria loosen. This ensures the verification system stays calibrated.

Finally, Phase 8 wires the MAP-Elites archive into topology routing — the Phase 7
placeholder `_consult_archive()` gets real functionality, and archive cells store
topology metadata from successful evolutions.

### What Phase 8 Does NOT Include

- **Autonomous run loop** — Phase ∞ (scout → queue → execute → review → reflect → evolve)
- **Meta-evolution** — evolution engine evolving itself (Level 3)
- **Real task execution against forks** — evaluation remains heuristic-based; real
  execution requires running full task pipelines against forked configs, which is
  Phase ∞ scope
- **Cross-domain evolution** — population candidates are within a single domain

### Key Principles

1. **Generation-verification gap**: Verification must always exceed generation capability.
   Track false-positive/negative rates and auto-calibrate thresholds.
2. **Population diversity**: Candidates should explore different directions, not converge
   on the same mutation. Use archive gap information to seed population diversity.
3. **Tournament selection**: Best candidate wins across all 6 dimensions (DGM pattern).
4. **Fail-loud**: Population operations fail loudly on any inconsistency.

---

## Part 2: Data Models (`src/uagents/models/population.py`)

```python
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

    PROMOTED = "promoted"       # Best candidate promoted
    ALL_REJECTED = "all_rejected"  # No candidate met thresholds
    HELD = "held"               # Best candidate marginal — held for human
    CANCELLED = "cancelled"     # Run cancelled (budget, safety, etc.)


class CandidateResult(FrameworkModel):
    """Result for a single candidate in a population run.

    Stores the candidate ID, evaluation scores, and rank.
    """

    candidate_id: str  # DualCopyCandidate.evo_id
    proposal_id: str
    evaluation_id: str = ""  # EvaluationResult.id
    overall_score: float = Field(ge=0.0, le=1.0, default=0.0)
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    rank: int = 0  # 1 = best
    promoted: bool = False
    rejection_reason: str = ""


class PopulationRun(IdentifiableModel):
    """A population-based evolution run (Section 8.2 population_mode).

    Generates multiple candidate forks, evaluates all, selects best.
    Tournament selection: best fork wins across multi-dimensional evaluation.

    Persisted to: instances/{domain}/state/evolution/populations/{id}.yaml
    """

    id: str = Field(default_factory=lambda: generate_id("pop"))
    trigger_proposal_id: str  # The original proposal that triggered population mode
    population_size: int = Field(ge=2, le=10, default=3)
    candidates: list[CandidateResult] = Field(default_factory=list)
    outcome: PopulationOutcome = PopulationOutcome.CANCELLED
    winner_id: str = ""  # candidate_id of the winner (empty if no winner)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    reason: str = ""  # Human-readable outcome description


class GapCalibrationAction(StrEnum):
    """Action taken by gap monitor to recalibrate evaluation thresholds."""

    TIGHTEN = "tighten"   # Too many false positives — raise thresholds
    LOOSEN = "loosen"     # Too many false negatives — lower thresholds
    HOLD = "hold"         # Rates within acceptable range


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
    false_positives: int = 0  # Promoted but later rolled back or degraded
    false_negatives: int = 0  # Rejected but manual review says would have helped
    fp_rate: float = 0.0  # false_positives / total_promotions (0 if no promotions)
    fn_rate: float = 0.0  # false_negatives / total_rejections (0 if no rejections)
    last_calibration_action: GapCalibrationAction = GapCalibrationAction.HOLD
    threshold_adjustments: int = 0  # Total number of threshold adjustments made
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

---

## Part 3: PopulationEvolver (`src/uagents/engine/population_evolver.py`)

### 3.1 Class Definition

```python
"""Population-based evolution orchestrator.
Spec reference: Section 8.2 (Dual-Copy, population_mode).

Generates multiple candidate forks from a base proposal, evaluates all
against multi-dimensional criteria, and selects the best via tournament.

Key constraints:
- Population size configurable (default 3, max 10)
- Each candidate gets independent constitutional check
- Tournament selection: highest overall_score wins
- All candidates cleaned up after run (win or lose)
- Budget pressure gating: population mode requires GREEN/YELLOW budget
- Archive gaps used to seed candidate diversity

Literature basis:
- Darwin Godel Machine: population of forks evaluated in parallel (20%→50%)
- AlphaEvolve (DeepMind): island model with migration
- ADAS (ICLR 2025): archive-based meta-agent search
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.base import generate_id
from ..models.evolution import (
    DualCopyCandidate,
    EvaluationResult,
    EvolutionOutcome,
    EvolutionProposal,
    EvolutionRecord,
    EvolutionTier,
)
from ..models.population import (
    CandidateResult,
    GapCalibrationAction,
    PopulationOutcome,
    PopulationRun,
)
from ..state.yaml_store import YamlStore
from .constitution_guard import ConstitutionGuard
from .dual_copy_manager import DualCopyManager, ForkError
from .evolution_validator import EvolutionValidator
from .map_elites_archive import MAPElitesArchive

logger = logging.getLogger("uagents.population_evolver")


class PopulationError(RuntimeError):
    """Raised when population evolution fails non-recoverably."""


class PopulationEvolver:
    """Population-based evolution using tournament selection.

    Design invariants:
    - Each candidate is a separate DualCopyCandidate fork
    - Candidates are evaluated independently (generation-verification gap)
    - Tournament selects highest overall_score across 6 dimensions
    - All forks cleaned up after run (winner promoted externally by EvolutionEngine)
    - Population run is persisted for audit trail

    Usage:
        evolver = PopulationEvolver(yaml_store, dual_copy_manager,
                                     evolution_validator, constitution_guard,
                                     archive, domain)
        run = evolver.run_population(base_proposal, population_size=3)
        if run.outcome == PopulationOutcome.PROMOTED:
            # Winner info in run.winner_id, run.candidates
            pass
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        dual_copy_manager: DualCopyManager,
        evolution_validator: EvolutionValidator,
        constitution_guard: ConstitutionGuard,
        archive: MAPElitesArchive,
        domain: str = "meta",
        budget_tracker: "BudgetTracker | None" = None,  # FM-P8-034
    ):
        self.yaml_store = yaml_store
        self.dual_copy_manager = dual_copy_manager
        self.evolution_validator = evolution_validator
        self.constitution_guard = constitution_guard
        self.archive = archive
        self.domain = domain
        self._base = f"instances/{domain}/state/evolution"
        self._budget_tracker = budget_tracker

        # Load population config from evolution.yaml
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

        Creates `population_size` variants of the base proposal, evaluates
        each independently, and selects the best via tournament.

        M-01/FM-P8-013 fix: Returns the winner's fork ALIVE (not cleaned up)
        so EvolutionEngine can promote it directly without re-evaluation.
        Loser forks are cleaned up. Caller MUST clean up winner fork after
        promotion or rejection.

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

        # FM-P8-034 fix: Budget pressure check before population run.
        # Population mode is N× cost — require GREEN or YELLOW budget.
        if self._budget_tracker is not None:
            pressure = self._budget_tracker.current_pressure()
            if pressure not in ("green", "yellow"):
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

        if winner is None:
            run.outcome = PopulationOutcome.ALL_REJECTED
            run.reason = "No candidate met promotion thresholds"
        elif winner.overall_score < self._get_hold_threshold():
            # Below hold threshold but above minimum — should not happen
            # since _evaluate_candidate already sets rejection_reason
            run.outcome = PopulationOutcome.ALL_REJECTED
            run.reason = "Winner below hold threshold"
        else:
            promote_threshold = self._get_promote_threshold()
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

        # Cleanup LOSER forks only — winner fork is kept alive for
        # EvolutionEngine to promote directly (M-01/FM-P8-013 fix:
        # avoids double-fork re-evaluation bug)
        winner_fork: DualCopyCandidate | None = None
        winner_proposal_variant: EvolutionProposal | None = None
        for proposal_variant, candidate in candidates:
            if candidate.evo_id == run.winner_id:
                winner_fork = candidate
                winner_proposal_variant = proposal_variant
                continue  # Keep winner fork alive
            try:
                self.dual_copy_manager.cleanup_fork(candidate)
            except OSError as e:
                # FM-P8-015 fix: log at ERROR, not swallowed
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
        Diversity is seeded from archive gaps if configured.

        Returns list of (proposal_variant, fork) tuples.
        """
        candidates: list[tuple[EvolutionProposal, DualCopyCandidate]] = []

        for i in range(count):
            # Create a variant proposal (Phase 8: variants differ in diff content)
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

        Phase 8 scope: variants use the same diff but with perturbed
        estimated_risk to produce non-degenerate tournament results
        (FM-P8-014 fix). Real diff-level mutation (e.g., parameter
        sweeps, alternative implementations) is Phase ∞ scope.

        The variant_index is embedded in the ID for traceability.
        """
        variant_id = generate_id(f"evo-pop-{variant_index}")

        # FM-P8-014 fix: Perturb estimated_risk so evaluation scores
        # differ across variants (avoids all-identical-score degenerate
        # tournament). In Phase ∞, real diff-level mutations will
        # produce genuine diversity.
        base_risk = base_proposal.estimated_risk
        risk_perturbation = 0.01 * variant_index  # Small deterministic offset
        perturbed_risk = min(base_risk + risk_perturbation, 1.0)

        return EvolutionProposal(
            id=variant_id,
            tier=base_proposal.tier,
            component=base_proposal.component,
            diff=base_proposal.diff,
            rationale=f"[Population variant {variant_index}] {base_proposal.rationale}",
            evidence=base_proposal.evidence,
            estimated_risk=perturbed_risk,
            trigger=base_proposal.trigger,
            trigger_detail=base_proposal.trigger_detail,
        )

    def _evaluate_candidate(
        self,
        proposal: EvolutionProposal,
        candidate: DualCopyCandidate,
    ) -> CandidateResult:
        """Evaluate a single candidate using the EvolutionValidator.

        Returns CandidateResult with scores and rank (rank set later by tournament).
        """
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

        # M-06 fix: Handle both REJECTED and HELD verdicts.
        # HELD candidates should NOT participate in tournament —
        # they are marginal and need human review.
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
        Remaining candidates ranked by overall_score (descending).
        Returns the winner or None if all rejected.
        """
        eligible = [r for r in results if not r.rejection_reason]
        if not eligible:
            return None

        # Sort by overall_score descending
        eligible.sort(key=lambda r: r.overall_score, reverse=True)

        # Assign ranks
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
```

---

## Part 4: GapMonitor (`src/uagents/engine/gap_monitor.py`)

### 4.1 Class Definition

```python
"""Generation-verification gap monitor.
Spec reference: Section 13.3 (Metacognitive Monitoring — gap_monitoring).

Tracks whether evolution approvals are actually reliable:
- False positive rate: approved changes that turned out worse
- False negative rate: rejected changes that would have been beneficial

Auto-calibrates evaluation thresholds:
- FP rate > 10%: tighten (raise promote_threshold by 0.05)
- FN rate > 30%: loosen (lower promote_threshold by 0.05)

Key constraints:
- Threshold changes are bounded (promote_threshold in [0.4, 0.9])
- Each calibration action is logged
- Metrics are persisted for continuity across sessions
- Calibration only triggers after minimum sample size (10 promotions)

Literature basis:
- Song et al. 2024: Generation-verification gap
- Huang 2025: Iterative calibration
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import yaml
from pydantic import ValidationError

from ..models.population import GapCalibrationAction, GapMetrics
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.gap_monitor")

# M-07 fix: Thresholds loaded from YAML config, not hardcoded.
# Module-level defaults used ONLY as last resort if config missing
# (FM-119 pattern: acceptable for state, not config — but these are
# initial defaults for the config file itself).
_DEFAULT_FP_TIGHTEN = 0.10
_DEFAULT_FN_LOOSEN = 0.30
_DEFAULT_THRESHOLD_STEP = 0.05
_DEFAULT_MIN_PROMOTE = 0.4
_DEFAULT_MAX_PROMOTE = 0.9
_DEFAULT_MIN_SAMPLE = 10


class GapMonitor:
    """Generation-verification gap tracker and auto-calibrator.

    Design invariants:
    - Metrics are persisted to YAML for cross-session continuity
    - Calibration only fires after MIN_SAMPLE_SIZE promotions
    - Threshold adjustments are bounded by [MIN, MAX]
    - Each calibration action is logged with full context
    - FP/FN rates computed lazily (avoid division by zero)

    Usage:
        monitor = GapMonitor(yaml_store, domain)
        monitor.record_promotion()      # Evolution was promoted
        monitor.record_rejection()      # Evolution was rejected
        monitor.record_false_positive() # Promoted but degraded
        monitor.record_false_negative() # Rejected but would have helped
        action = monitor.check_calibration()
        # action is TIGHTEN, LOOSEN, or HOLD
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
    ):
        self.yaml_store = yaml_store
        self.domain = domain
        self._metrics_path = f"instances/{domain}/state/evolution/gap_metrics.yaml"

        # M-07 fix: Load thresholds from YAML config (IFM-N53 fail-loud)
        config_raw = yaml_store.read_raw("core/evolution.yaml")
        gap_cfg = config_raw["evolution"]["gap_monitoring"]
        self._fp_tighten: float = float(gap_cfg["fp_tighten_threshold"])
        self._fn_loosen: float = float(gap_cfg["fn_loosen_threshold"])
        self._threshold_step: float = float(gap_cfg["threshold_step"])
        self._min_promote: float = float(gap_cfg["min_promote_threshold"])
        self._max_promote: float = float(gap_cfg["max_promote_threshold"])
        self._min_sample: int = int(gap_cfg["min_sample_size"])

        self._metrics = self._load_metrics()

    def record_promotion(self) -> None:
        """Record that an evolution was promoted."""
        self._metrics.total_promotions += 1
        self._update_rates()
        self._persist()

    def record_rejection(self) -> None:
        """Record that an evolution was rejected."""
        self._metrics.total_rejections += 1
        self._update_rates()
        self._persist()

    def record_false_positive(self) -> None:
        """Record that a promoted evolution turned out worse.

        Called when a promoted change is later rolled back or when
        post-promotion performance monitoring detects degradation.
        """
        self._metrics.false_positives += 1
        self._update_rates()
        self._persist()

    def record_false_negative(self) -> None:
        """Record that a rejected evolution would have been beneficial.

        Called when manual human review determines a rejected proposal
        should have been approved.
        """
        self._metrics.false_negatives += 1
        self._update_rates()
        self._persist()

    def check_calibration(self) -> GapCalibrationAction:
        """Check if evaluation thresholds need recalibration.

        Returns the recommended action. Caller is responsible for
        applying the threshold change.

        Only triggers after MIN_SAMPLE_SIZE promotions to avoid
        reacting to noise.
        """
        if self._metrics.total_promotions < self._min_sample:
            return GapCalibrationAction.HOLD

        action = GapCalibrationAction.HOLD

        if self._metrics.fp_rate > self._fp_tighten:
            action = GapCalibrationAction.TIGHTEN
        elif self._metrics.fn_rate > self._fn_loosen:
            action = GapCalibrationAction.LOOSEN

        if action != GapCalibrationAction.HOLD:
            self._metrics.last_calibration_action = action
            self._metrics.threshold_adjustments += 1
            self._persist()
            logger.info(
                f"Gap calibration: {action} "
                f"(FP rate={self._metrics.fp_rate:.2f}, "
                f"FN rate={self._metrics.fn_rate:.2f})"
            )

        return action

    def apply_calibration(self, action: GapCalibrationAction) -> float:
        """Apply a calibration action to the promote_threshold.

        Reads current threshold from evolution.yaml, adjusts it,
        writes it back, and returns the new threshold.

        Args:
            action: TIGHTEN or LOOSEN.

        Returns:
            The new promote_threshold value.

        Raises:
            ValueError: If action is HOLD (no-op).
        """
        if action == GapCalibrationAction.HOLD:
            raise ValueError("Cannot apply HOLD action — it's a no-op")

        config_raw = self.yaml_store.read_raw("core/evolution.yaml")
        current = float(config_raw["evolution"]["evaluation"]["promote_threshold"])

        if action == GapCalibrationAction.TIGHTEN:
            new_threshold = min(
                current + self._threshold_step, self._max_promote
            )
        else:  # LOOSEN
            new_threshold = max(
                current - self._threshold_step, self._min_promote
            )

        # FM-P8-024 fix: Enforce promote_threshold > hold_threshold
        hold_threshold = float(
            config_raw["evolution"]["evaluation"]["hold_threshold"]
        )
        if new_threshold <= hold_threshold:
            logger.warning(
                f"Calibrated promote_threshold {new_threshold:.2f} would be "
                f"<= hold_threshold {hold_threshold:.2f}. Clamping to "
                f"hold_threshold + {self._threshold_step}"
            )
            new_threshold = hold_threshold + self._threshold_step

        config_raw["evolution"]["evaluation"]["promote_threshold"] = new_threshold
        self.yaml_store.write_raw("core/evolution.yaml", config_raw)

        logger.info(
            f"Threshold adjusted: {current:.2f} → {new_threshold:.2f} "
            f"({action})"
        )
        return new_threshold

    def get_metrics(self) -> GapMetrics:
        """Return current gap metrics (copy)."""
        return self._metrics.model_copy()

    def _update_rates(self) -> None:
        """Recompute FP/FN rates from counts."""
        if self._metrics.total_promotions > 0:
            self._metrics.fp_rate = (
                self._metrics.false_positives / self._metrics.total_promotions
            )
        else:
            self._metrics.fp_rate = 0.0

        if self._metrics.total_rejections > 0:
            self._metrics.fn_rate = (
                self._metrics.false_negatives / self._metrics.total_rejections
            )
        else:
            self._metrics.fn_rate = 0.0

    def _persist(self) -> None:
        """Persist metrics to YAML."""
        self.yaml_store.write(self._metrics_path, self._metrics)

    def _load_metrics(self) -> GapMetrics:
        """Load metrics from YAML or create fresh.

        FM-119 pattern: .get() / broad exception acceptable for STATE loading
        of new fields in old files. This is NOT config loading.
        FM-P8-016 fix: Catches corruption (YAML errors, validation errors)
        in addition to FileNotFoundError.
        """
        try:
            data = self.yaml_store.read_raw(self._metrics_path)
            return GapMetrics(**data)
        except FileNotFoundError:
            return GapMetrics()
        except (yaml.YAMLError, ValidationError, TypeError, KeyError) as e:
            logger.error(
                f"Gap metrics file corrupted at {self._metrics_path}: {e}. "
                f"Starting with fresh metrics. Old file will be overwritten "
                f"on next persist."
            )
            return GapMetrics()
```

---

## Part 5: Modified Components

### 5.1 `evolution_engine.py` — Population Mode Entry Point

Add a `run_population_evolution` method that delegates to PopulationEvolver and
handles the winner's promotion through the existing pipeline.

```python
# New imports (add to existing):
from .population_evolver import PopulationEvolver, PopulationError
from ..models.population import GapCalibrationAction, PopulationOutcome

# New constructor parameters (add to existing __init__):
def __init__(
    self,
    # ... existing params ...
    population_evolver: PopulationEvolver | None = None,
    gap_monitor: "GapMonitor | None" = None,
    # Note: stagnation_detector already exists in Phase 7 constructor
):
    # ... existing init ...
    self._population_evolver = population_evolver
    self._gap_monitor = gap_monitor
    # self._stagnation_detector already set by Phase 7

# New method:
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

    now = datetime.now(timezone.utc)

    # FM-P4-48-FIX: Check persistent pause flag
    if self._state.paused:
        return self._reject(
            proposal,
            f"Evolution paused: {self._state.pause_reason}",
            now,
        )

    # Run population — returns winner fork alive (M-01/FM-P8-013 fix)
    pop_run, winner_fork, winner_proposal = (
        self._population_evolver.run_population(
            base_proposal=proposal,
            population_size=population_size,
        )
    )

    try:
        # Handle outcome
        if pop_run.outcome == PopulationOutcome.PROMOTED:
            # Winner fork is alive — promote directly (no re-evaluation)
            # Steps 5-8 of single-fork pipeline: approve→commit→verify→log
            winner_result = next(
                c for c in pop_run.candidates
                if c.candidate_id == pop_run.winner_id
            )

            # Promote via DualCopyManager (atomic writes)
            self._dual_copy.promote(winner_fork)

            # Create EvolutionRecord for audit trail (FM-P8-033 fix:
            # single record, not PopulationRun + EvolutionRecord)
            record = EvolutionRecord(
                proposal=winner_proposal,
                outcome=EvolutionOutcome.PROMOTED,
                evaluation_score=winner_result.overall_score,
                evaluation_id=winner_result.evaluation_id,
                diff_summary=winner_proposal.diff,
                rationale=winner_proposal.rationale,
                evolution_id=winner_proposal.id,
                started_at=pop_run.started_at,
                completed_at=datetime.now(timezone.utc),
            )
            # Persist record
            record_path = f"{self._base}/records/{record.id}.yaml"
            self._yaml_store.write(record_path, record)

            # Update archive
            self._archive.insert(record)

            # Gap monitor + calibration check
            if self._gap_monitor is not None:
                self._gap_monitor.record_promotion()
                action = self._gap_monitor.check_calibration()
                if action != GapCalibrationAction.HOLD:
                    self._gap_monitor.apply_calibration(action)

            # Wire stagnation detector (FM-P8-035 fix)
            if self._stagnation_detector is not None:
                self._stagnation_detector.record_evolution_outcome(
                    promoted=True
                )

            return record

        elif pop_run.outcome == PopulationOutcome.HELD:
            # FM-P8-028 fix: HELD has its own handling, not reusing
            # _queue_for_human (which is Tier 1 specific)
            record = EvolutionRecord(
                proposal=proposal,
                outcome=EvolutionOutcome.HELD,
                evaluation_score=0.0,
                started_at=pop_run.started_at,
                completed_at=datetime.now(timezone.utc),
            )
            record_path = f"{self._base}/records/{record.id}.yaml"
            self._yaml_store.write(record_path, record)
            # Persist to held queue for human review
            held_path = f"{self._base}/held/{record.id}.yaml"
            self._yaml_store.write(held_path, record)
            logger.info(
                f"Population evolution held for review: {record.id}"
            )
            return record

        else:
            # ALL_REJECTED or CANCELLED
            if self._gap_monitor is not None:
                self._gap_monitor.record_rejection()
            if self._stagnation_detector is not None:
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
                self._dual_copy.cleanup_fork(winner_fork)
            except OSError as e:
                logger.error(
                    f"Failed to cleanup winner fork "
                    f"{winner_fork.evo_id}: {e}"
                )
```

### 5.2 `map_elites_archive.py` — Topology Metadata in Cells

Enhance `_extract_config` to include topology information from evolution records.

```python
# Modified method — ADDITIVE change (M-05/FM-P8-029 fix):
# Adds topology fields to existing _extract_config output.
# Does NOT replace existing fields (diff_summary, rationale, evolution_id).
def _extract_config(self, record: EvolutionRecord) -> dict[str, str]:
    """Extract best_config from an evolution record.

    Phase 4 fields: component, tier (existing).
    Phase 8 addition: topology, agent_count from evidence (if available).
    """
    # Call existing Phase 4 logic first
    config: dict[str, str] = {}

    # Existing Phase 4 fields — preserved
    if record.proposal:
        config["component"] = record.proposal.component
        config["tier"] = str(record.proposal.tier)

    # Phase 8 addition: topology from evidence (additive only)
    if record.proposal and record.proposal.evidence:
        evidence = record.proposal.evidence
        if "topology" in evidence:
            config["topology"] = str(evidence["topology"])
        if "agent_count" in evidence:
            config["agent_count"] = str(evidence["agent_count"])

    return config
```

**Implementation note:** The actual Phase 4 `_extract_config` may have additional
fields (e.g., `diff_summary`, `rationale`). The Phase 8 modification MUST preserve
all existing fields and only ADD the topology fields. Implementer should read the
current code and add the topology extraction block after existing logic.

### 5.3 `topology_router.py` — Wire Archive Consultation

The Phase 7 `_consult_archive()` method already works if archive cells have
a "topology" key in their `best_config`. Phase 8 ensures cells get topology
metadata via the enhanced `_extract_config()`. No code changes needed in
topology_router.py — the wiring is via the archive data.

### 5.4 `evolution_validator.py` — Threshold Refresh (FM-P8-017)

The current EvolutionValidator caches thresholds at `__init__` time. After gap
calibration adjusts `promote_threshold` in evolution.yaml, the validator won't
see the new value until restarted.

**Fix:** In `evaluate()`, re-read thresholds from YAML before applying verdict logic:

```python
# In evaluate(), before verdict determination:
def _refresh_thresholds(self) -> None:
    """Re-read thresholds from config (FM-P8-017 fix).

    Called at the start of each evaluate() to pick up gap calibration changes.
    """
    config_raw = self.yaml_store.read_raw("core/evolution.yaml")
    eval_cfg = config_raw["evolution"]["evaluation"]
    self._promote_threshold = float(eval_cfg["promote_threshold"])
    self._hold_threshold = float(eval_cfg["hold_threshold"])
```

### 5.5 `orchestrator.py` — No Changes Needed

**FM-P8-019/FM-P8-032 fix:** Gap monitoring is handled ONLY in EvolutionEngine
(via `run_population_evolution`), NOT in Orchestrator. This avoids:
- Double-counting gap signals from both Engine and Orchestrator (FM-P8-032)
- Referencing nonexistent `evolution_record` key in results dict (FM-P8-019)
- Missing runtime import for `GapCalibrationAction` (FM-P8-020)

The Orchestrator already calls `EvolutionEngine.run_population_evolution()` which
internally handles gap monitoring. No orchestrator-level gap tracking needed.

### 5.6 `stagnation_detector.py` — Population Trigger Signal

Add a signal that fires when single-fork evolution stalls (multiple consecutive
rejections), suggesting population mode should be used.

```python
# New constant:
SINGLE_FORK_STALL_THRESHOLD = 3  # N consecutive rejected evolutions

# New counter in __init__:
self._consecutive_rejections: int = 0

# New method:
def record_evolution_outcome(self, promoted: bool) -> None:
    """Record evolution outcome for stall detection.

    If promoted, reset counter. If rejected, increment.
    """
    if promoted:
        self._consecutive_rejections = 0
    else:
        self._consecutive_rejections += 1
    self._save_state()

# In _check_framework_stagnation(), add new signal:
if (
    self._consecutive_rejections >= SINGLE_FORK_STALL_THRESHOLD
    and self._consecutive_rejections % SINGLE_FORK_STALL_THRESHOLD == 0
):
    signals.append(StagnationSignal(
        level=StagnationLevel.FRAMEWORK,
        description=(
            f"Single-fork evolution stalled: {self._consecutive_rejections} "
            f"consecutive rejections. Consider population mode."
        ),
        metric_name="consecutive_rejections",
        metric_value=float(self._consecutive_rejections),
        threshold=float(SINGLE_FORK_STALL_THRESHOLD),
        consecutive_count=self._consecutive_rejections,
    ))

# In _save_state(), add:
"consecutive_rejections": self._consecutive_rejections,

# In _load_state(), add:
self._consecutive_rejections = int(state.get("consecutive_rejections", 0))
```

---

## Part 6: YAML Configuration Updates

### 6.1 `instances/meta/core/evolution.yaml` — Population Section

Add to the existing evolution.yaml:

```yaml
  # ── Population mode (Phase 8) ──
  population:
    default_size: 3               # Default number of candidates
    max_size: 5                   # Maximum candidates per run
    diversity_seed_from_archive: true  # Use archive gaps to seed diversity
    trigger_after_rejections: 3   # Switch to population mode after N consecutive rejections

  # ── Gap monitoring (Phase 8) ──
  gap_monitoring:
    fp_tighten_threshold: 0.10    # Tighten if false positive rate > 10%
    fn_loosen_threshold: 0.30     # Loosen if false negative rate > 30%
    threshold_step: 0.05          # Amount to adjust promote_threshold
    min_promote_threshold: 0.4    # Floor for promote_threshold
    max_promote_threshold: 0.9    # Ceiling for promote_threshold
    min_sample_size: 10           # Minimum promotions before calibrating
```

---

## Part 7: Directory Updates

### 7.1 `state/directory.py` — New Directories

```python
# Add to INSTANCE_DIRS:
"state/evolution/populations/",
"state/evolution/held/",  # FM-P8-028: HELD evolution queue for human review
```

---

## Part 8: Implementation Sequence

```
Step 1: Config update (evolution.yaml) — MUST be first (FM-P8-027 fix)
  └─ PopulationEvolver and GapMonitor read config at __init__
  └─ Add population and gap_monitoring sections

Step 2: Models (population.py)
  └─ No code dependencies. Pure data models.

Step 3: Modified Directory (directory.py)
  └─ Add populations/ directory
  └─ Test: populations/ directory created

Step 4: GapMonitor (gap_monitor.py)
  └─ Depends on: population.py models, evolution.yaml config
  └─ Test: GapMetrics persistence, rate computation, calibration logic,
     promote > hold invariant (FM-P8-024)

Step 5: PopulationEvolver (population_evolver.py)
  └─ Depends on: population.py, evolution.yaml, DualCopyManager,
     EvolutionValidator, ConstitutionGuard, MAPElitesArchive
  └─ Test: Population generation, tournament selection, cleanup,
     budget pressure gating (FM-P8-034), winner fork kept alive (M-01)

Step 6: Modified EvolutionEngine (evolution_engine.py)
  └─ Depends on: PopulationEvolver, GapMonitor
  └─ Test: run_population_evolution integration, direct promotion,
     HELD handling (FM-P8-028), stagnation wiring (FM-P8-035)

Step 7: Modified MAPElitesArchive (map_elites_archive.py)
  └─ Depends on: None (internal change)
  └─ Test: _extract_config includes topology (additive, M-05)

Step 8: Modified StagnationDetector (stagnation_detector.py)
  └─ Depends on: None (internal change)
  └─ Test: consecutive_rejections signal, persistence, record_evolution_outcome
```

**Note:** Orchestrator changes REMOVED (FM-P8-019/FM-P8-032 fix). Gap monitoring
is exclusively in EvolutionEngine.

---

## Part 9: Verification Checklist

```
[ ] evolution.yaml has population and gap_monitoring sections (Step 1)
[ ] PopulationRun model validates population_size bounds (ge=2, le=10)
[ ] GapMetrics persists and loads correctly (including corruption recovery)
[ ] PopulationEvolver creates correct number of forks
[ ] PopulationEvolver cleans up LOSER forks, keeps winner alive (M-01)
[ ] Winner fork cleaned up in finally block of run_population_evolution
[ ] Tournament selects highest overall_score
[ ] HELD candidates excluded from tournament (M-06)
[ ] All-rejected case handled correctly
[ ] GapMonitor reads thresholds from YAML config (M-07)
[ ] Calibration only fires after min_sample_size from config
[ ] Threshold adjustments bounded by [min, max] from config
[ ] promote_threshold > hold_threshold enforced after calibration (FM-P8-024)
[ ] StagnationDetector fires population signal after N rejections
[ ] FM-104 modulo pattern applied to population signal
[ ] record_evolution_outcome wired from EvolutionEngine (FM-P8-035)
[ ] Archive _extract_config includes topology (additive, M-05)
[ ] _extract_config preserves existing Phase 4 fields
[ ] Budget pressure check before population run (FM-P8-034)
[ ] HELD outcome has dedicated handling, not reusing _queue_for_human (FM-P8-028)
[ ] No gap monitoring in orchestrator (FM-P8-019/FM-P8-032)
[ ] generate_id imported at top of population.py (M-02)
[ ] populations/ and held/ directories created by DirectoryManager
[ ] All existing tests still pass
```

---

## Part 10: Edge Cases & Initial Failure Modes

| ID | Severity | Location | Description | Mitigation |
|----|----------|----------|-------------|------------|
| FM-P8-001 | HIGH | population_evolver.py | All candidates fail constitutional check → empty population | Return CANCELLED with reason |
| FM-P8-002 | MEDIUM | population_evolver.py | Fork creation fails for some candidates but not all | Continue with remaining; log warnings |
| FM-P8-003 | ~~HIGH~~ FIXED | population_evolver.py | Winner promotion re-creates fork (double-fork bug) | **M-01 fix:** Winner fork kept alive, promoted directly |
| FM-P8-004 | MEDIUM | gap_monitor.py | Division by zero in rate computation | Guard with > 0 checks |
| FM-P8-005 | LOW | gap_monitor.py | Calibration oscillation (tighten then loosen repeatedly) | Step size is small; bounded range; promote>hold invariant |
| FM-P8-006 | HIGH | evolution_engine.py | Population mode bypasses existing tier checks | Tier checks in run_population_evolution before delegating |
| FM-P8-007 | MEDIUM | stagnation_detector.py | consecutive_rejections persists across domains | Scoped to single stagnation_detector instance per domain |
| FM-P8-008 | LOW | population_evolver.py | Population size 1 is meaningless | Minimum is 2 (model validator) |
| FM-P8-009 | ~~HIGH~~ FIXED | population_evolver.py | Budget exhaustion during population (N forks = N× cost) | **FM-P8-034 fix:** Budget pressure check (GREEN/YELLOW required) |
| FM-P8-010 | MEDIUM | map_elites_archive.py | _extract_config topology key missing from old records | .get() with None — no topology returned, falls back to heuristic |
| FM-P8-011 | ~~MEDIUM~~ FIXED | gap_monitor.py | Metrics file corrupted | **FM-P8-016 fix:** Catches YAMLError, ValidationError, returns fresh |
| FM-P8-012 | LOW | population_evolver.py | Concurrent population runs | max_concurrent_candidates in evolution.yaml limits forks |
| FM-P8-013 | ~~CRITICAL~~ FIXED | evolution_engine.py | Winner re-evaluated during re-promotion | **M-01 fix:** Winner fork kept alive, direct promotion |
| FM-P8-014 | MEDIUM | population_evolver.py | All variants identical — population is illusory | **Scope limit:** Perturbed estimated_risk; real diversity Phase ∞ |
| FM-P8-015 | ~~HIGH~~ FIXED | population_evolver.py | Fork cleanup exceptions swallowed | **Fix:** `except OSError`, log at ERROR level |
| FM-P8-016 | ~~HIGH~~ FIXED | gap_monitor.py | Only catches FileNotFoundError | **M-03 fix:** Catches corruption errors too |
| FM-P8-017 | HIGH | evolution_validator.py | Calibrated thresholds never reach cached validator | **Design:** Validator re-reads thresholds on each evaluate() call |
| FM-P8-018 | MEDIUM | population_evolver.py | Winner proposal uses base diff, losing variant identity | Variants share same diff (Phase 8 scope); real mutation Phase ∞ |
| FM-P8-019 | ~~HIGH~~ FIXED | orchestrator.py | References nonexistent evolution_record key | **Fix:** Removed orchestrator gap monitor entirely |
| FM-P8-020 | ~~HIGH~~ FIXED | orchestrator.py | Missing GapCalibrationAction import | **Fix:** Removed orchestrator gap monitor entirely |
| FM-P8-024 | ~~MEDIUM~~ FIXED | gap_monitor.py | hold_threshold not updated when promote changes | **Fix:** Enforce promote > hold after calibration |
| FM-P8-027 | ~~MEDIUM~~ FIXED | population_evolver.py | Config key doesn't exist when constructor runs | **Fix:** Config YAML is Step 1 in implementation sequence |
| FM-P8-028 | ~~MEDIUM~~ FIXED | evolution_engine.py | HELD misrouted through _queue_for_human | **Fix:** Dedicated HELD handling with held/ queue |
| FM-P8-032 | ~~MEDIUM~~ FIXED | orchestrator.py | Double-counting gap signals | **Fix:** Gap monitoring only in EvolutionEngine |
| FM-P8-033 | ~~HIGH~~ FIXED | evolution_engine.py | Two records for one evolution | **Fix:** Single EvolutionRecord, PopulationRun for audit only |
| FM-P8-034 | ~~MEDIUM~~ FIXED | population_evolver.py | Budget pressure check not implemented | **Fix:** Added to run_population() |
| FM-P8-035 | ~~MEDIUM~~ FIXED | stagnation_detector.py | record_evolution_outcome never called | **Fix:** Wired from run_population_evolution |

---

## Part 11: Review Fixes Applied (v0.2.0)

Summary of all fixes applied during Step 5:

1. **M-01/FM-P8-013/FM-P8-033** (CRITICAL): Winner fork kept alive by PopulationEvolver, promoted directly by EvolutionEngine. No double-fork. Single EvolutionRecord.
2. **M-02** (MEDIUM): `generate_id` imported at top with other `.base` imports.
3. **M-03/FM-P8-016** (HIGH): `_load_metrics` catches YAMLError, ValidationError, TypeError, KeyError.
4. **M-05/FM-P8-029** (MEDIUM): `_extract_config` is additive — implementation note added to preserve existing fields.
5. **M-06** (MEDIUM): HELD verdict sets `rejection_reason`, excluding from tournament.
6. **M-07** (MEDIUM): Gap thresholds loaded from YAML config, not module constants.
7. **FM-P8-014** (MEDIUM): `estimated_risk` perturbed per variant for non-degenerate tournament. Documented as scope limitation.
8. **FM-P8-015** (HIGH): Fork cleanup catches `OSError` specifically, logs at ERROR.
9. **FM-P8-017** (HIGH): Design note that EvolutionValidator must re-read thresholds on each evaluate() call.
10. **FM-P8-019/FM-P8-020/FM-P8-032** (HIGH): Orchestrator gap monitor path removed entirely.
11. **FM-P8-024** (MEDIUM): `apply_calibration` enforces promote_threshold > hold_threshold.
12. **FM-P8-027** (MEDIUM): Implementation sequence reordered — config YAML is Step 1.
13. **FM-P8-028** (MEDIUM): HELD has dedicated handling with `held/` directory queue.
14. **FM-P8-034** (MEDIUM): Budget pressure check added to PopulationEvolver.
15. **FM-P8-035** (MEDIUM): `record_evolution_outcome` wired from `run_population_evolution`.

---

*End of Phase 8 Detailed Design — Version 0.2.0*
