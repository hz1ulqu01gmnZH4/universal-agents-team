"""Multi-dimensional evolution validator.
Spec reference: Section 8.2 (Dual-Copy, step 3_evaluate).

Evaluates fork candidates on 6 dimensions:
1. Capability — Does it perform tasks better?
2. Consistency — Reproducible results across runs?
3. Robustness — Handles edge cases?
4. Predictability — Can we anticipate failures?
5. Safety — Constitutional compliance?
6. Diversity — Maintains SRD above floor?

The validator is STRUCTURALLY INDEPENDENT from the evolution engine.
This enforces the generation-verification gap (Song et al. 2024):
the system that proposes changes cannot also evaluate them.

Key constraints:
- Each dimension produces a 0.0-1.0 score
- Overall score is weighted average of dimensions
- Verdict: promote if >= promote_threshold, hold if >= hold_threshold, else rollback
- Per-dimension minimums: any dimension below its minimum → rollback
- Safety dimension has the highest minimum (0.9)

Literature basis:
- Song et al. 2024: generation-verification gap
- SWE-Pruner: task-aware pruning (23-54% reduction)
- DGM: multi-dimensional fitness evaluation
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.base import generate_id
from ..models.evolution import (
    DimensionScore,
    DualCopyCandidate,
    EvaluationDimension,
    EvaluationResult,
    EvolutionOutcome,
    EvolutionProposal,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.evolution_validator")


class EvolutionValidator:
    """Multi-dimensional evaluation of evolution candidates.

    Design invariants:
    - Structurally independent from EvolutionEngine (generation-verification gap)
    - Each dimension scored independently (0.0-1.0)
    - Per-dimension minimums enforced (any below → rollback)
    - Overall score is weighted average
    - Verdict determined by thresholds: promote / hold / rollback
    - Safety dimension has highest bar (0.9 minimum)

    Usage:
        validator = EvolutionValidator(yaml_store)
        result = validator.evaluate(candidate, proposal)
        # result.verdict is PROMOTED, HELD, or REJECTED
    """

    def __init__(self, yaml_store: YamlStore):
        self.yaml_store = yaml_store

        # Load config (fail-loud if missing)
        config_raw = yaml_store.read_raw("core/evolution.yaml")
        ev = config_raw["evolution"]["evaluation"]

        # IFM-N53: Direct dict access. Keys are str (StrEnum values)
        # for consistent lookup with use_enum_values iteration.
        self._min_scores: dict[str, float] = {
            str(EvaluationDimension.CAPABILITY): float(ev["min_capability"]),
            str(EvaluationDimension.CONSISTENCY): float(ev["min_consistency"]),
            str(EvaluationDimension.ROBUSTNESS): float(ev["min_robustness"]),
            str(EvaluationDimension.PREDICTABILITY): float(ev["min_predictability"]),
            str(EvaluationDimension.SAFETY): float(ev["min_safety"]),
            str(EvaluationDimension.DIVERSITY): float(ev["min_diversity"]),
        }

        weights = ev["weights"]
        self._weights: dict[str, float] = {
            str(EvaluationDimension.CAPABILITY): float(weights["capability"]),
            str(EvaluationDimension.CONSISTENCY): float(weights["consistency"]),
            str(EvaluationDimension.ROBUSTNESS): float(weights["robustness"]),
            str(EvaluationDimension.PREDICTABILITY): float(weights["predictability"]),
            str(EvaluationDimension.SAFETY): float(weights["safety"]),
            str(EvaluationDimension.DIVERSITY): float(weights["diversity"]),
        }

        # FM-P4-45: Validate all weights are non-negative
        for dim_name, w in self._weights.items():
            if w < 0.0:
                raise ValueError(
                    f"Evaluation weight for {dim_name} is negative ({w}). "
                    f"All weights must be >= 0.0."
                )

        self._promote_threshold = float(ev["promote_threshold"])
        self._hold_threshold = float(ev["hold_threshold"])

    def evaluate(
        self,
        candidate: DualCopyCandidate,
        proposal: EvolutionProposal,
    ) -> EvaluationResult:
        """Evaluate a fork candidate on all 6 dimensions.

        Phase 4 evaluation strategy:
        - Capability: Based on estimated risk (inverse — lower risk = higher score)
        - Consistency: Based on whether the change is a simple YAML value change
        - Robustness: Based on number of files modified (fewer = more robust)
        - Predictability: Based on diff size (smaller = more predictable)
        - Safety: Constitutional check + ring hierarchy check
        - Diversity: Based on whether the change affects diversity-relevant configs

        These are conservative heuristics for Phase 4. Phase 5 will add
        actual task-based evaluation (run tasks against both configs).

        Args:
            candidate: The fork to evaluate.
            proposal: The original proposal.

        Returns:
            EvaluationResult with per-dimension scores, overall score, and verdict.
        """
        now = datetime.now(timezone.utc)
        dimension_scores: list[DimensionScore] = []

        # Score each dimension
        for dim in EvaluationDimension:
            # use_enum_values means dim is a string after iteration
            dim_str = dim if isinstance(dim, str) else str(dim)
            score = self._score_dimension(dim_str, candidate, proposal)
            dimension_scores.append(score)

        # Check per-dimension minimums
        failed_dimensions: list[str] = []
        for ds in dimension_scores:
            dim_enum = ds.dimension
            dim_key = dim_enum if isinstance(dim_enum, str) else str(dim_enum)
            min_score = self._min_scores[dim_key]  # KeyError if missing — fail-loud
            if ds.score < min_score:
                failed_dimensions.append(
                    f"{dim_key}: {ds.score:.2f} < {min_score:.2f}"
                )

        # Compute overall score (weighted average)
        overall = 0.0
        total_weight = 0.0
        for ds in dimension_scores:
            dim_key = ds.dimension if isinstance(ds.dimension, str) else str(ds.dimension)
            w = self._weights[dim_key]  # KeyError if missing — fail-loud
            overall += ds.score * w
            total_weight += w

        if total_weight > 0:
            overall = overall / total_weight

        # Determine verdict
        if failed_dimensions:
            verdict = EvolutionOutcome.REJECTED
            verdict_reason = (
                f"Dimensions below minimum: {'; '.join(failed_dimensions)}"
            )
        elif overall >= self._promote_threshold:
            verdict = EvolutionOutcome.PROMOTED
            verdict_reason = f"Overall score {overall:.2f} >= promote threshold {self._promote_threshold}"
        elif overall >= self._hold_threshold:
            verdict = EvolutionOutcome.HELD
            verdict_reason = (
                f"Overall score {overall:.2f} between hold ({self._hold_threshold}) "
                f"and promote ({self._promote_threshold}) — marginal improvement"
            )
        else:
            verdict = EvolutionOutcome.REJECTED
            verdict_reason = (
                f"Overall score {overall:.2f} below hold threshold {self._hold_threshold}"
            )

        return EvaluationResult(
            id=generate_id("eval"),
            created_at=now,
            proposal_id=proposal.id,
            candidate_id=candidate.evo_id,
            dimension_scores=dimension_scores,
            overall_score=overall,
            verdict=verdict,
            verdict_reason=verdict_reason,
        )

    def _score_dimension(
        self,
        dimension: str,
        candidate: DualCopyCandidate,
        proposal: EvolutionProposal,
    ) -> DimensionScore:
        """Score a single evaluation dimension.

        Phase 4 heuristics — conservative scoring based on proposal
        characteristics. Phase 5 will add task-based evaluation.
        """
        if dimension == EvaluationDimension.CAPABILITY:
            return self._score_capability(proposal)
        elif dimension == EvaluationDimension.CONSISTENCY:
            return self._score_consistency(candidate, proposal)
        elif dimension == EvaluationDimension.ROBUSTNESS:
            return self._score_robustness(candidate)
        elif dimension == EvaluationDimension.PREDICTABILITY:
            return self._score_predictability(proposal)
        elif dimension == EvaluationDimension.SAFETY:
            return self._score_safety(proposal)
        elif dimension == EvaluationDimension.DIVERSITY:
            return self._score_diversity(proposal)
        else:
            # Unknown dimension — fail loud
            raise ValueError(f"Unknown evaluation dimension: {dimension}")

    def _score_capability(self, proposal: EvolutionProposal) -> DimensionScore:
        """Score capability: inverse of estimated risk.

        Lower risk proposals are more likely to maintain or improve capability.
        Risk 0.0 → score 1.0; Risk 1.0 → score 0.0.
        """
        # Pydantic validates estimated_risk as float in [0.0, 1.0] at construction
        risk_val = float(proposal.estimated_risk)
        score = 1.0 - risk_val
        return DimensionScore(
            dimension=EvaluationDimension.CAPABILITY,
            score=score,
            detail=f"Inverse of estimated risk ({risk_val:.2f})",
        )

    def _score_consistency(
        self, candidate: DualCopyCandidate, proposal: EvolutionProposal
    ) -> DimensionScore:
        """Score consistency: based on change type.

        Simple YAML value changes (thresholds, parameters) are highly
        consistent. Structural changes (new keys, removed sections) less so.
        """
        # Phase 4 heuristic: YAML value changes are consistent
        diff_lower = proposal.diff.lower()
        if "new_key" in diff_lower or "remove" in diff_lower or "delete" in diff_lower:
            score = 0.5
            detail = "Structural YAML change — moderate consistency"
        else:
            score = 0.8
            detail = "YAML value change — high consistency"
        return DimensionScore(
            dimension=EvaluationDimension.CONSISTENCY,
            score=score,
            detail=detail,
        )

    def _score_robustness(self, candidate: DualCopyCandidate) -> DimensionScore:
        """Score robustness: fewer modified files = more robust.

        1 file: 0.9, 2 files: 0.7, 3 files: 0.5, 4+: 0.3
        """
        n_files = len(candidate.modified_files)
        if n_files <= 1:
            score = 0.9
        elif n_files <= 2:
            score = 0.7
        elif n_files <= 3:
            score = 0.5
        else:
            score = 0.3
        return DimensionScore(
            dimension=EvaluationDimension.ROBUSTNESS,
            score=score,
            detail=f"{n_files} files modified",
        )

    def _score_predictability(self, proposal: EvolutionProposal) -> DimensionScore:
        """Score predictability: smaller diffs are more predictable.

        <= 10 lines: 0.9, <= 50: 0.7, <= 100: 0.5, > 100: 0.3
        """
        diff_lines = len(proposal.diff.strip().split("\n")) if proposal.diff.strip() else 0
        if diff_lines <= 10:
            score = 0.9
        elif diff_lines <= 50:
            score = 0.7
        elif diff_lines <= 100:
            score = 0.5
        else:
            score = 0.3
        return DimensionScore(
            dimension=EvaluationDimension.PREDICTABILITY,
            score=score,
            detail=f"{diff_lines} lines in diff",
        )

    def _score_safety(self, proposal: EvolutionProposal) -> DimensionScore:
        """Score safety: constitutional compliance + ring hierarchy.

        Tier 3 proposals targeting Ring 2-3 content: 0.95 (high safety).
        Any hint of Ring 0-1 targeting: 0.0 (fail).
        """
        component_lower = proposal.component.lower()

        # Ring 0/1 targeting — immediate fail
        if "constitution" in component_lower:
            return DimensionScore(
                dimension=EvaluationDimension.SAFETY,
                score=0.0,
                detail="Targets constitution (Ring 0) — FORBIDDEN",
            )

        # Check for framework-level paths (Ring 1)
        # DR-17: "state/" removed — state/ is the instance data directory
        # (e.g., instances/meta/state/), NOT Ring 1 framework code.
        # Ring 1 = Python source under src/uagents/{engine,models,audit,cli}/.
        ring_1_indicators = ["engine/", "models/", "audit/", "cli/"]
        for indicator in ring_1_indicators:
            if indicator in component_lower:
                return DimensionScore(
                    dimension=EvaluationDimension.SAFETY,
                    score=0.0,
                    detail=f"Targets Ring 1 path ({indicator}) — FORBIDDEN in Phase 4",
                )

        # Tier 3 targeting operational configs — safe
        tier_val = proposal.tier
        tier_int = tier_val if isinstance(tier_val, int) else int(tier_val)
        if tier_int == 3:
            return DimensionScore(
                dimension=EvaluationDimension.SAFETY,
                score=0.95,
                detail="Tier 3 targeting operational config — safe",
            )

        return DimensionScore(
            dimension=EvaluationDimension.SAFETY,
            score=0.5,
            detail="Non-Tier 3 proposal — moderate safety",
        )

    def _score_diversity(self, proposal: EvolutionProposal) -> DimensionScore:
        """Score diversity: does the change affect diversity-relevant configs?

        Changes to role compositions may affect diversity (positive or negative).
        Changes to thresholds/parameters typically don't affect diversity.
        """
        component_lower = proposal.component.lower()

        if "composition" in component_lower or "role" in component_lower:
            # Role changes could affect diversity — neutral score
            score = 0.6
            detail = "Targets role composition — may affect diversity"
        elif "voice" in component_lower or "tone" in component_lower:
            score = 0.6
            detail = "Targets voice/tone config — may affect diversity"
        else:
            # Non-diversity-relevant change
            score = 0.8
            detail = "Non-diversity-relevant change — diversity maintained"

        return DimensionScore(
            dimension=EvaluationDimension.DIVERSITY,
            score=score,
            detail=detail,
        )
