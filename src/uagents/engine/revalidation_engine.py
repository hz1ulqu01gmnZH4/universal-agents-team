"""Change-triggered revalidation pipeline.
Spec reference: Section 19.3 (Change-Triggered Revalidation).

When drift or version change is detected, assesses scope, runs targeted
revalidation capped at 10% of session budget, classifies adaptation.

Key design decisions:
- Budget-capped: max 10% of session token budget
- Trigger classification determines scope (what to revalidate)
- Adaptation response is classified, not acted upon (Phase 2.5 detects, Phase 4+ acts)
- Exception: degraded_major and broken trigger quarantine to Ring 3

IFM-28: Migration note — Constructor signature changed in Phase 2.5:
  - Added `capability_tracker` parameter (optional, None if Phase 2 not active)
  - All callers (EnvironmentMonitor.__init__) must update their instantiation.
  Callers to update:
    - engine/environment_monitor.py: EnvironmentMonitor.__init__()
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..engine.budget_tracker import BudgetTracker
from ..engine.canary_runner import CanaryRunner
from ..engine.capability_tracker import CapabilityTracker
from ..models.base import generate_id
from ..models.environment import (
    AdaptationResponse,
    DriftDetection,
    ModelExecuteFn,
    ModelFingerprint,
    RevalidationResult,
    RevalidationTrigger,
    VersionInfo,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.revalidation_engine")

# IFM-07: Mapping from assess_scope() output to _classify_task_type() names.
# assess_scope() uses capability-oriented names; the Orchestrator uses
# task_type names. This mapping bridges the two vocabularies.
SCOPE_TO_TASK_TYPE: dict[str, str] = {
    "decomposition": "decomposition",
    "evolution_proposal": "evolution",
    "skill_validation": "validation",
    "review": "review",
    "simple_fix": "bugfix",
    "feature": "feature",
    "research": "research",
    "code_generation": "code_generation",
    "canary_suite": "canary",
    "tool_integrations": "tool_integration",
    "mcp_tools": "mcp_tool",
}


class RevalidationEngine:
    """Runs targeted revalidation after detected environment changes.

    Design invariants:
    - Revalidation budget capped at `budget_cap_pct` of session window remaining
    - Scope is determined by trigger type (model drift -> skills, version change -> tools)
    - Results persisted to state/environment/revalidation-history/
    - Does NOT autonomously modify skills (Phase 4+) except quarantine
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        budget_tracker: BudgetTracker,
        capability_tracker: CapabilityTracker | None = None,
        domain: str = "meta",
    ):
        self.yaml_store = yaml_store
        self.budget_tracker = budget_tracker
        self.capability_tracker = capability_tracker
        self._domain = domain
        self._state_base = f"instances/{domain}/state/environment"
        self.yaml_store.ensure_dir(f"{self._state_base}/revalidation-history")

        # Load config
        config_raw = yaml_store.read_raw("core/environment-awareness.yaml")
        ea = config_raw.get("environment_awareness", {})
        rv = ea.get("revalidation", {})
        self._budget_cap_pct = float(rv.get("budget_cap_pct", 0.10))
        self._min_budget = int(rv.get("min_budget_tokens", 2000))
        # MF-4: Threshold names now match AdaptationResponse levels clearly
        self._improved_threshold = float(rv.get("improved_threshold", 0.05))
        self._degraded_minor_threshold = float(rv.get("degraded_minor_threshold", 0.05))
        self._degraded_major_threshold = float(rv.get("degraded_major_threshold", 0.15))
        self._broken_threshold = float(rv.get("broken_threshold", 0.30))

    def compute_budget_cap(self) -> int:
        """Compute the token budget cap for revalidation.

        Returns max tokens allowed, based on current window remaining.
        """
        window = self.budget_tracker.get_window()
        cap = int(window.remaining_tokens * self._budget_cap_pct)
        return max(cap, 0)

    def should_revalidate(self, budget_cap: int) -> bool:
        """Check if revalidation is feasible given budget constraints."""
        if budget_cap < self._min_budget:
            logger.info(
                f"Skipping revalidation: budget cap {budget_cap} "
                f"< minimum {self._min_budget}"
            )
            return False
        return True

    def assess_scope(
        self,
        trigger: RevalidationTrigger,
        drift: DriftDetection | None = None,
        version_changes: list[str] | None = None,
    ) -> list[str]:
        """Determine what needs revalidation based on trigger type.

        Args:
            trigger: What caused the revalidation.
            drift: DriftDetection result (for model_drift triggers).
            version_changes: List of changed version fields.

        Returns:
            List of scope items (skill names, tool names, or categories).
        """
        scope: list[str] = []

        if trigger == RevalidationTrigger.MODEL_DRIFT:
            if drift is not None and drift.affected_dimensions:
                # Map affected dimensions to skills that depend on them
                dim_to_skills = {
                    "reasoning": ["decomposition", "evolution_proposal", "research"],
                    "instruction": ["skill_validation", "review"],
                    "code": ["simple_fix", "feature", "code_generation"],
                    "creative": ["evolution_proposal", "research"],
                    "tool": ["canary_suite", "feature"],
                }
                for dim in drift.affected_dimensions:
                    skills = dim_to_skills.get(dim, [])
                    for skill in skills:
                        if skill not in scope:
                            scope.append(skill)
            else:
                # Generic drift — revalidate all Ring 2 skills
                scope = [
                    "decomposition",
                    "evolution_proposal",
                    "skill_validation",
                    "review",
                    "simple_fix",
                    "feature",
                    "research",
                ]

        elif trigger == RevalidationTrigger.VERSION_CHANGE:
            if version_changes and "claude_code_version" in version_changes:
                # Claude Code update — revalidate tool integrations
                scope = ["tool_integrations", "mcp_tools", "canary_suite"]
            else:
                # Python or OS update — lighter revalidation
                scope = ["canary_suite"]

        elif trigger == RevalidationTrigger.MCP_CHANGE:
            scope = ["tool_integrations", "mcp_tools"]

        elif trigger == RevalidationTrigger.PERFORMANCE_DROP:
            # Scope should be determined by caller based on which skills dropped
            scope = ["affected_skills"]  # Placeholder — caller overrides

        elif trigger == RevalidationTrigger.MANUAL:
            # Full revalidation
            scope = [
                "decomposition",
                "evolution_proposal",
                "skill_validation",
                "review",
                "simple_fix",
                "feature",
                "research",
                "canary_suite",
                "tool_integrations",
            ]

        logger.info(f"Revalidation scope for {str(trigger)}: {scope}")
        return scope

    def classify_adaptation(
        self,
        pre_fingerprint: ModelFingerprint | None,
        post_fingerprint: ModelFingerprint | None,
        drift: DriftDetection | None = None,
    ) -> AdaptationResponse:
        """Classify the adaptation response based on fingerprint comparison.

        Compares pre and post revalidation fingerprints to determine
        whether the environment change was positive, neutral, or negative.

        MF-4: Uses separate broken_threshold. Threshold names match
        AdaptationResponse levels: improved > +5%, degraded_minor > -5%,
        degraded_major > -15%, broken > -30%.

        IFM-20: Also checks per-dimension extremes. If any single dimension
        drops more than degraded_minor_threshold, the classification is
        at least DEGRADED_MINOR, even if the mean is above threshold.
        """
        if pre_fingerprint is None or post_fingerprint is None:
            # Cannot classify without both fingerprints
            return AdaptationResponse.UNCHANGED

        distance = post_fingerprint.distance_to(pre_fingerprint)
        deltas = post_fingerprint.per_dimension_delta(pre_fingerprint)

        # Compute mean delta (positive = improvement)
        mean_delta = sum(deltas.values()) / len(deltas) if deltas else 0.0

        # MF-4: Classify based on mean delta with distinct thresholds
        if mean_delta > self._improved_threshold:
            classification = AdaptationResponse.IMPROVED
        elif mean_delta < -self._broken_threshold:
            classification = AdaptationResponse.BROKEN
        elif mean_delta < -self._degraded_major_threshold:
            classification = AdaptationResponse.DEGRADED_MAJOR
        elif mean_delta < -self._degraded_minor_threshold:
            classification = AdaptationResponse.DEGRADED_MINOR
        else:
            classification = AdaptationResponse.UNCHANGED

        # IFM-20: Per-dimension extreme check. If any single dimension
        # drops more than degraded_minor_threshold, escalate to at least
        # DEGRADED_MINOR to prevent mean masking per-dimension degradation.
        if classification in (
            AdaptationResponse.UNCHANGED,
            AdaptationResponse.IMPROVED,
        ):
            worst_drop = min(deltas.values()) if deltas else 0.0
            if worst_drop < -self._degraded_minor_threshold:
                logger.warning(
                    f"Per-dimension extreme detected: worst_drop={worst_drop:.4f} "
                    f"< -{self._degraded_minor_threshold}. "
                    f"Escalating from {str(classification)} to DEGRADED_MINOR."
                )
                classification = AdaptationResponse.DEGRADED_MINOR

        return classification

    def run_revalidation(
        self,
        trigger: RevalidationTrigger,
        trigger_detail: str,
        drift: DriftDetection | None = None,
        version_changes: list[str] | None = None,
        pre_fingerprint: ModelFingerprint | None = None,
        execute_fn: ModelExecuteFn | None = None,
        canary_runner: CanaryRunner | None = None,
    ) -> RevalidationResult:
        """Execute a full revalidation cycle.

        MF-5/IFM-06: Now actually calls execute_fn via canary_runner to produce
        a post_fingerprint for meaningful adaptation classification. Also tracks
        tokens_used from the canary re-run.

        Args:
            trigger: What caused the revalidation.
            trigger_detail: Human-readable description of the trigger.
            drift: DriftDetection result (if applicable).
            version_changes: Changed version fields (if applicable).
            pre_fingerprint: Fingerprint before the change.
            execute_fn: Model execution function for re-running canaries.
            canary_runner: CanaryRunner instance for re-running canary suite.

        Returns:
            RevalidationResult with classification and actions taken.
        """
        budget_cap = self.compute_budget_cap()
        now = datetime.now(timezone.utc)

        if not self.should_revalidate(budget_cap):
            result = RevalidationResult(
                created_at=now,
                trigger=trigger,
                trigger_detail=f"{trigger_detail} [SKIPPED: insufficient budget]",
                scope=[],
                tokens_used=0,
                budget_cap=budget_cap,
                adaptation=AdaptationResponse.UNCHANGED,
                actions_taken=["revalidation_skipped_budget"],
            )
            self._store_result(result)
            return result

        # Assess scope
        scope = self.assess_scope(trigger, drift, version_changes)

        # Track tokens used during revalidation
        tokens_used = 0
        actions_taken: list[str] = []
        affected_skills: list[str] = []
        post_fingerprint: ModelFingerprint | None = None

        # MF-5/IFM-06: Re-run canary suite to get post_fingerprint.
        # Without this, classify_adaptation() always returns UNCHANGED
        # because post_fingerprint would be None.
        if execute_fn is not None and canary_runner is not None:
            try:
                suite_result = canary_runner.run_suite(execute_fn)
                post_fingerprint = suite_result.fingerprint
                tokens_used = suite_result.total_tokens
                actions_taken.append(
                    f"canary_rerun:tokens={tokens_used}"
                )
            except Exception as e:
                logger.warning(
                    f"Canary re-run during revalidation failed: {e}"
                )
                actions_taken.append(f"canary_rerun_failed:{e}")
        else:
            if execute_fn is None:
                logger.warning(
                    "Revalidation: no execute_fn provided, "
                    "cannot produce post_fingerprint"
                )
            if canary_runner is None:
                logger.warning(
                    "Revalidation: no canary_runner provided, "
                    "cannot produce post_fingerprint"
                )

        # If capability tracker is available, check skill performance
        if self.capability_tracker is not None:
            for skill_name in scope:
                if skill_name in (
                    "tool_integrations", "mcp_tools", "affected_skills"
                ):
                    continue  # These are categories, not individual skills
                entry = self.capability_tracker.get_capability(skill_name)
                if entry.attempts > 0 and entry.success_rate < 0.5:
                    affected_skills.append(skill_name)
                    actions_taken.append(
                        f"flagged_weak_skill:{skill_name} "
                        f"(success_rate={entry.success_rate:.2f})"
                    )

        # Classify adaptation
        adaptation = self.classify_adaptation(
            pre_fingerprint, post_fingerprint, drift
        )

        # Take actions based on adaptation classification
        if adaptation == AdaptationResponse.IMPROVED:
            actions_taken.append("updated_baselines")
            actions_taken.append("logged_improvement")
        elif adaptation == AdaptationResponse.UNCHANGED:
            actions_taken.append("updated_fingerprint")
        elif adaptation == AdaptationResponse.DEGRADED_MINOR:
            actions_taken.append("logged_warning")
            actions_taken.append("adjusted_confidence_estimates")
        elif adaptation == AdaptationResponse.DEGRADED_MAJOR:
            for skill in affected_skills:
                actions_taken.append(f"quarantine_to_ring3:{skill}")
            actions_taken.append("alert_human")
        elif adaptation == AdaptationResponse.BROKEN:
            for skill in affected_skills:
                actions_taken.append(f"disabled_capability:{skill}")
            actions_taken.append("create_workaround_task")
            actions_taken.append("alert_human_urgent")

        result = RevalidationResult(
            created_at=now,
            trigger=trigger,
            trigger_detail=trigger_detail,
            scope=scope,
            tokens_used=tokens_used,
            budget_cap=budget_cap,
            pre_fingerprint=pre_fingerprint,
            post_fingerprint=post_fingerprint,
            adaptation=adaptation,
            affected_skills=affected_skills,
            actions_taken=actions_taken,
        )

        self._store_result(result)

        logger.info(
            f"Revalidation complete: trigger={str(trigger)}, "
            f"adaptation={str(adaptation)}, "
            f"actions={len(actions_taken)}, tokens={tokens_used}"
        )

        return result

    def get_revalidation_history(self, limit: int = 10) -> list[RevalidationResult]:
        """Load recent revalidation results."""
        history_dir = f"{self._state_base}/revalidation-history"
        try:
            files = self.yaml_store.list_dir(history_dir)
        except (NotADirectoryError, FileNotFoundError):
            return []
        yaml_files = sorted(
            (f for f in files if f.endswith(".yaml") and not f.endswith(".lock")),
            reverse=True,
        )
        results: list[RevalidationResult] = []
        for fname in yaml_files[:limit]:
            try:
                r = self.yaml_store.read(
                    f"{history_dir}/{fname}", RevalidationResult
                )
                results.append(r)
            except Exception as e:
                logger.warning(f"Skipping corrupt revalidation result {fname}: {e}")
        return results

    def _store_result(self, result: RevalidationResult) -> None:
        """Persist revalidation result to YAML.

        IFM-01: Appends generate_id() suffix to prevent timestamp collisions.
        SF-6: Trims history to last 50 entries after storing.
        """
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_suffix = generate_id("rv").split("-")[-1]  # 8-char hex
        path = (
            f"{self._state_base}/revalidation-history/"
            f"{timestamp_str}_{unique_suffix}.yaml"
        )
        self.yaml_store.write(path, result)
        self._trim_history()

    def _trim_history(self, max_entries: int = 50) -> None:
        """SF-6: Trim revalidation history to last max_entries results."""
        history_dir = f"{self._state_base}/revalidation-history"
        try:
            files = self.yaml_store.list_dir(history_dir)
        except (NotADirectoryError, FileNotFoundError):
            return
        yaml_files = sorted(
            f for f in files if f.endswith(".yaml") and not f.endswith(".lock")
        )
        while len(yaml_files) > max_entries:
            oldest = yaml_files.pop(0)
            try:
                self.yaml_store.delete(f"{history_dir}/{oldest}")
            except FileNotFoundError:
                pass  # Already deleted (race condition)
