"""Self-governance risk scorecard.
Spec reference: Section 14.4 (Risk Scorecard).

Computes a 10-dimension risk profile of the framework.
Each dimension scored 0.0-1.0 (0=healthy, 1=critical).
Governance and alignment dimensions are double-weighted.
Thresholds trigger escalation or operational halt.

Key constraints:
- Each dimension scored independently
- Aggregate is weighted average (governance + alignment double-weighted)
- < 0.3 = healthy, 0.3-0.5 = watch, 0.5-0.7 = warning, > 0.7 = critical
- Warning triggers human escalation
- Critical triggers operational halt
- Results persisted for audit trail

Literature basis:
- Self-governance risk assessment (Section 14)
- COCOA: constitution drift detection
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.base import generate_id
from ..models.governance import (
    RiskAssessment,
    RiskDimension,
    RiskLevel,
    RiskScore,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.risk_scorecard")


class RiskScorecard:
    """Computes 10-dimension risk profile.

    Design invariants:
    - Each dimension scored independently
    - Aggregate uses configurable weights (governance + alignment double-weighted)
    - Threshold classification: healthy / watch / warning / critical
    - Critical dimensions halt affected operations
    - Results persisted for audit trail

    Usage:
        scorecard = RiskScorecard(yaml_store, domain)
        assessment = scorecard.compute(metrics)
        if assessment.aggregate_level == RiskLevel.CRITICAL:
            # Halt operations
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

        # Load config
        config_raw = yaml_store.read_raw("core/self-governance.yaml")
        sc = config_raw["self_governance"]["risk_scorecard"]

        # Load dimension configs
        self._dim_configs: dict[str, dict] = {}
        dims = sc["dimensions"]
        for dim in RiskDimension:
            dim_str = str(dim)
            dim_conf = dims[dim_str]  # KeyError if missing — fail-loud
            self._dim_configs[dim_str] = {
                "weight": float(dim_conf["weight"]),
                "healthy": float(dim_conf["healthy_threshold"]),
                "warning": float(dim_conf["warning_threshold"]),
                "critical": float(dim_conf["critical_threshold"]),
            }

        # S-04-FIX / NFR-08-FIX: Aggregate thresholds required (fail-loud)
        agg_thresholds = sc["aggregate_thresholds"]  # KeyError = fail-loud
        self._agg_healthy = float(agg_thresholds["healthy"])
        self._agg_warning = float(agg_thresholds["warning"])
        self._agg_critical = float(agg_thresholds["critical"])

        # Paths
        self._results_dir = "state/governance/risk_assessments"

    def compute(self, metrics: dict[str, dict]) -> RiskAssessment:
        """Compute risk assessment from current framework metrics.

        S-01-FIX: metrics dict MUST contain all 10 dimensions. Missing
        dimensions are logged as warnings with score 0.0 (healthy bias)
        rather than silently defaulting. This makes missing data visible
        in logs while not triggering false alerts.

        Args:
            metrics: Dict mapping dimension name to metric dict.
                Each metric dict contains dimension-specific indicators.
                Example: {"operational": {"agent_failure_count": 2, ...}, ...}
                All 10 dimensions should be present.

        Returns:
            RiskAssessment with per-dimension scores and aggregate.
        """
        now = datetime.now(timezone.utc)
        dimension_scores: list[RiskScore] = []
        actions: list[str] = []
        halted: list[str] = []

        for dim in RiskDimension:
            dim_str = str(dim)
            # S-01-FIX: Log missing dimensions explicitly
            if dim_str not in metrics:
                logger.warning(
                    f"Risk dimension '{dim_str}' missing from metrics — "
                    f"scoring as 0.0 (healthy). Caller should provide all dimensions."
                )
            dim_metrics = metrics.get(dim_str, {})
            score_val = self._score_dimension(dim_str, dim_metrics)
            level = self._classify(dim_str, score_val)

            indicators = [f"{k}={v}" for k, v in dim_metrics.items()] if dim_metrics else []

            rs = RiskScore(
                dimension=dim,
                score=score_val,
                level=level,
                detail=f"{dim_str}: {score_val:.2f} ({level})",
                indicators=indicators,
            )
            dimension_scores.append(rs)

            if level == RiskLevel.WARNING:
                actions.append(f"Escalate {dim_str} to human (score: {score_val:.2f})")
            elif level == RiskLevel.CRITICAL:
                actions.append(f"HALT {dim_str} operations (score: {score_val:.2f})")
                halted.append(dim_str)

        # Compute weighted aggregate
        total_weighted = 0.0
        total_weight = 0.0
        for rs in dimension_scores:
            dim_str = str(rs.dimension)
            w = self._dim_configs[dim_str]["weight"]
            total_weighted += rs.score * w
            total_weight += w

        aggregate = total_weighted / total_weight if total_weight > 0 else 0.0
        aggregate_level = self._classify_aggregate(aggregate)

        assessment = RiskAssessment(
            id=generate_id("risk"),
            created_at=now,
            dimension_scores=dimension_scores,
            aggregate_score=aggregate,
            aggregate_level=aggregate_level,
            governance_weight=self._dim_configs["governance"]["weight"],
            alignment_weight=self._dim_configs["alignment"]["weight"],
            actions_required=actions,
            halted_operations=halted,
        )

        self._persist_result(assessment)

        # S-03-FIX: Governance audit logging
        if self._audit_logger is not None:
            self._audit_logger.log_governance(
                event_type="risk_assessment",
                risk_aggregate=aggregate,
                detail=f"Aggregate: {aggregate:.2f} ({aggregate_level}), "
                       f"halted: {halted}",
            )

        logger.info(
            f"Risk assessment: aggregate {aggregate:.2f} ({aggregate_level}), "
            f"{len(halted)} operations halted, {len(actions)} actions required"
        )
        return assessment

    def _score_dimension(self, dimension: str, metrics: dict) -> float:
        """Score a single risk dimension based on its metrics.

        Phase 5 heuristic scoring — each dimension uses simple metrics.
        Phase 6+ will add more sophisticated scoring.

        Returns 0.0-1.0 (0 = healthy, 1 = critical).
        """
        if dimension == "operational":
            return self._score_operational(metrics)
        elif dimension == "evolutionary":
            return self._score_evolutionary(metrics)
        elif dimension == "diversity":
            return self._score_diversity(metrics)
        elif dimension == "knowledge":
            return self._score_knowledge(metrics)
        elif dimension == "resource":
            return self._score_resource(metrics)
        elif dimension == "governance":
            return self._score_governance(metrics)
        elif dimension == "alignment":
            return self._score_alignment(metrics)
        elif dimension == "calibration":
            return self._score_calibration(metrics)
        elif dimension == "environment":
            return self._score_environment(metrics)
        elif dimension == "complexity":
            return self._score_complexity(metrics)
        else:
            raise ValueError(f"Unknown risk dimension: {dimension}")

    # S-01-FIX: All _score_* methods use _get_metric() helper which
    # returns 0.0 for missing keys but logs a warning. This makes
    # missing data explicit in logs without triggering false alerts.

    @staticmethod
    def _get_metric(m: dict, key: str, default: float = 0.0) -> float:
        """Extract a metric value, logging if missing (S-01-FIX)."""
        if key not in m:
            # Don't log here — caller's dimension already warned if m is empty.
            # Only log if m has some keys but this specific one is missing.
            if m:
                logger.debug(f"Metric '{key}' not in dimension metrics — using {default}")
        return float(m.get(key, default))

    def _score_operational(self, m: dict) -> float:
        """Operational risk: agent failures, data corruption."""
        failures = self._get_metric(m, "agent_failure_rate")
        return min(1.0, failures)

    def _score_evolutionary(self, m: dict) -> float:
        """Evolutionary risk: too fast or too slow, tier 3 drift."""
        rollback_rate = self._get_metric(m, "rollback_rate")
        stagnation = self._get_metric(m, "stagnation_score")
        return min(1.0, max(rollback_rate, stagnation))

    def _score_diversity(self, m: dict) -> float:
        """Diversity risk: SRD declining, homogenization."""
        # Inverse: low SRD = high risk. Default 0.5 = moderate.
        srd = self._get_metric(m, "srd", default=0.5)
        return min(1.0, max(0.0, 1.0 - srd))

    def _score_knowledge(self, m: dict) -> float:
        """Knowledge risk: stale memory, outdated assumptions."""
        staleness = self._get_metric(m, "knowledge_staleness")
        return min(1.0, staleness)

    def _score_resource(self, m: dict) -> float:
        """Resource risk: budget pressure, rate limits."""
        budget_pressure = self._get_metric(m, "budget_pressure")
        rate_limit_util = self._get_metric(m, "rate_limit_utilization")
        return min(1.0, max(budget_pressure, rate_limit_util))

    def _score_governance(self, m: dict) -> float:
        """Governance risk: bypasses, rubber-stamp reviews."""
        bypass_rate = self._get_metric(m, "constitutional_bypass_rate")
        rubber_stamp_rate = self._get_metric(m, "rubber_stamp_rate")
        objective_drift = self._get_metric(m, "objective_drift")
        return min(1.0, max(bypass_rate, rubber_stamp_rate, objective_drift))

    def _score_alignment(self, m: dict) -> float:
        """Alignment risk: faking, capability hiding."""
        faking_score = self._get_metric(m, "alignment_faking_score")
        hiding_score = self._get_metric(m, "capability_hiding_score")
        return min(1.0, max(faking_score, hiding_score))

    def _score_calibration(self, m: dict) -> float:
        """Calibration risk: overconfidence in self-improvement."""
        false_positive_rate = self._get_metric(m, "false_positive_evolution_rate")
        return min(1.0, false_positive_rate)

    def _score_environment(self, m: dict) -> float:
        """Environment risk: model drift, skill rot."""
        drift = self._get_metric(m, "model_drift_score")
        skill_rot = self._get_metric(m, "skill_rot_score")
        return min(1.0, max(drift, skill_rot))

    def _score_complexity(self, m: dict) -> float:
        """Complexity risk: tool overload, context bloat."""
        context_pressure = self._get_metric(m, "context_pressure")
        tool_overload = self._get_metric(m, "tool_overload_score")
        return min(1.0, max(context_pressure, tool_overload))

    def _classify(self, dimension: str, score: float) -> RiskLevel:
        """Classify a dimension score into a risk level."""
        conf = self._dim_configs[dimension]
        if score > conf["critical"]:
            return RiskLevel.CRITICAL
        elif score > conf["warning"]:
            return RiskLevel.WARNING
        elif score > conf["healthy"]:
            return RiskLevel.WATCH
        else:
            return RiskLevel.HEALTHY

    def _classify_aggregate(self, score: float) -> RiskLevel:
        """Classify aggregate score using configurable thresholds (S-04-FIX)."""
        if score > self._agg_critical:
            return RiskLevel.CRITICAL
        elif score > self._agg_warning:
            return RiskLevel.WARNING
        elif score > self._agg_healthy:
            return RiskLevel.WATCH
        else:
            return RiskLevel.HEALTHY

    def _persist_result(self, assessment: RiskAssessment) -> None:
        """Persist risk assessment for audit trail."""
        self.yaml_store.write(
            f"{self._results_dir}/{assessment.id}.yaml", assessment
        )
