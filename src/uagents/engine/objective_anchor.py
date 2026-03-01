"""Objective anchoring — drift detection over evolution cycles.
Spec reference: Section 14.1 (Objective Anchoring).

Monitors for objective drift by comparing recent evolution outcomes
against the original objectives in CONSTITUTION.md. Uses evolution
success rate as a proxy for alignment (Phase 5 heuristic).

Key constraints:
- Runs every N evolution cycles (configurable)
- Independent from the evolution engine (structurally separate)
- If alignment drops below threshold: pause evolution, alert human
- Results persisted for audit trail
- CONSTITUTION.md is the ground truth (immutable)

Literature basis:
- arXiv:2506.23844: auto-summarized reflections cause recursive objective shift
- Anthropic 2024: alignment faking under RL pressure
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.base import generate_id
from ..models.governance import ObjectiveAlignmentResult
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.objective_anchor")


class ObjectiveAlignmentError(RuntimeError):
    """Raised when objective alignment drops below threshold."""


class ObjectiveAnchor:
    """Monitors objective drift across evolution cycles.

    Design invariants:
    - Structurally independent from EvolutionEngine
    - Reads evolution records from disk (no shared state)
    - Compares against CONSTITUTION.md objectives (immutable)
    - Pauses evolution on alignment failure
    - Results persisted for audit trail

    Usage:
        anchor = ObjectiveAnchor(yaml_store, domain)
        result = anchor.check_alignment(evolution_count)
        if not result.passed:
            # Evolution should be paused
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        audit_logger: object | None = None,
    ):
        self.yaml_store = yaml_store
        self.domain = domain
        self._audit_logger = audit_logger

        config_raw = yaml_store.read_raw("core/self-governance.yaml")
        oa = config_raw["self_governance"]["objective_anchoring"]

        self._check_interval = int(oa["check_every_n_cycles"])
        self._min_score = float(oa["min_alignment_score"])
        self._recent_window = int(oa["recent_window"])
        self._halt_on_failure = bool(oa["halt_on_failure"])

        self._records_dir = "state/evolution/records"
        self._results_dir = "state/governance/alignment_results"

    def should_check(self, evolution_count: int) -> bool:
        """Whether an alignment check is due based on evolution count."""
        if evolution_count == 0:
            return False
        return evolution_count % self._check_interval == 0

    def check_alignment(
        self, evolution_count: int
    ) -> ObjectiveAlignmentResult:
        """Check if recent evolutions align with constitutional objectives.

        Phase 5 heuristic: alignment is measured by evolution success rate.

        Args:
            evolution_count: Current total evolution count.

        Returns:
            ObjectiveAlignmentResult with score and pass/fail.

        Raises:
            ObjectiveAlignmentError: If alignment score below threshold
                                     and halt_on_failure is enabled.
        """
        now = datetime.now(timezone.utc)

        records_dir = self.yaml_store.base_dir / self._records_dir
        if not records_dir.exists() or not records_dir.is_dir():
            # S-NFR-19-FIX: If evolution_count > 0 but records dir missing,
            # that indicates data loss — raise alignment error.
            if evolution_count > 0:
                raise ObjectiveAlignmentError(
                    f"Evolution count is {evolution_count} but records "
                    f"directory '{self._records_dir}' does not exist. "
                    f"Evolution records may have been lost."
                )
            result = ObjectiveAlignmentResult(
                id=generate_id("align"),
                created_at=now,
                evolution_count_at_check=evolution_count,
                alignment_score=1.0,
                success_rate=1.0,
                passed=True,
                detail="No evolutions have occurred yet — no alignment concern",
            )
            self._persist_result(result)
            return result

        record_files = sorted(
            f
            for f in records_dir.iterdir()
            if f.suffix in (".yaml", ".yml")
        )
        recent = (
            record_files[-self._recent_window :]
            if len(record_files) >= self._recent_window
            else record_files
        )

        if not recent:
            result = ObjectiveAlignmentResult(
                id=generate_id("align"),
                created_at=now,
                evolution_count_at_check=evolution_count,
                alignment_score=1.0,
                success_rate=1.0,
                passed=True,
                detail="No recent evolution records — no alignment concern",
            )
            self._persist_result(result)
            return result

        outcomes: list[str] = []
        promoted_count = 0
        total = 0
        for rf in recent:
            rel_path = str(rf.relative_to(self.yaml_store.base_dir))
            data = self.yaml_store.read_raw(rel_path)
            outcome = data["outcome"]  # KeyError = fail-loud
            outcomes.append(outcome)
            total += 1
            if outcome == "promoted":
                promoted_count += 1

        success_rate = promoted_count / total if total > 0 else 0.0
        alignment_score = success_rate
        passed = alignment_score >= self._min_score

        result = ObjectiveAlignmentResult(
            id=generate_id("align"),
            created_at=now,
            evolution_count_at_check=evolution_count,
            recent_outcomes=outcomes,
            success_rate=success_rate,
            alignment_score=alignment_score,
            passed=passed,
            detail=(
                f"Evolution success rate: {promoted_count}/{total} "
                f"({success_rate:.0%}). Alignment score: "
                f"{alignment_score:.2f}. Threshold: {self._min_score:.2f}."
            ),
        )
        self._persist_result(result)

        # S-03-FIX: Governance audit logging
        if self._audit_logger is not None:
            self._audit_logger.log_governance(
                event_type="alignment_check",
                detail=result.detail,
                alignment_passed=result.passed,
            )

        if not passed:
            logger.warning(
                f"Objective alignment check FAILED at evolution "
                f"#{evolution_count}: score {alignment_score:.2f} < "
                f"threshold {self._min_score:.2f}"
            )
            if self._halt_on_failure:
                raise ObjectiveAlignmentError(
                    f"Objective alignment score {alignment_score:.2f} below "
                    f"threshold {self._min_score:.2f} at evolution "
                    f"#{evolution_count}. Success rate: {success_rate:.0%}. "
                    f"Evolution should be paused."
                )
        else:
            logger.info(
                f"Objective alignment check passed at evolution "
                f"#{evolution_count}: score {alignment_score:.2f} >= "
                f"threshold {self._min_score:.2f}"
            )

        return result

    def _persist_result(self, result: ObjectiveAlignmentResult) -> None:
        """Persist alignment check result for audit trail."""
        self.yaml_store.write(
            f"{self._results_dir}/{result.id}.yaml", result
        )
