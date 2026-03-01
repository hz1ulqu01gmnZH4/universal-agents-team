"""Environment awareness orchestrator.
Spec reference: Section 19 (Environment Awareness & Self-Benchmarking).

Phase 2.5: Full rewrite replacing Phase 0 stub.
Orchestrates CanaryRunner, DriftDetector, RevalidationEngine,
and PerformanceMonitor. Provides session_start() and periodic_check()
entry points for the Orchestrator.

Key responsibilities:
- Session start: run canaries, check drift, check version
- Periodic check: every N tasks, re-run canaries and check performance
- Audit logging: all events to ENVIRONMENT stream
- Alert aggregation: surface performance alerts to orchestrator
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from ..audit.logger import AuditLogger
from ..engine.budget_tracker import BudgetTracker
from ..engine.canary_runner import CanaryRunner
from ..engine.capability_tracker import CapabilityTracker
from ..engine.drift_detector import DriftDetector
from ..engine.performance_monitor import PerformanceMonitor
from ..engine.revalidation_engine import RevalidationEngine
from ..models.audit import EnvironmentLogEntry
from ..models.base import generate_id
from ..models.environment import (
    AdaptationResponse,
    DriftDetection,
    EnvironmentCheckResult,
    ModelExecuteFn,
    ModelFingerprint,
    RevalidationTrigger,
    VersionInfo,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.environment_monitor")

# SF-2/IFM-23: EnvironmentCheckResult is now a FrameworkModel defined in
# models/environment.py. No longer a plain class in this module.


class EnvironmentMonitor:
    """Orchestrates all Phase 2.5 environment awareness components.

    Design invariants:
    - session_start() runs at every session start (unless canary recency skip)
    - periodic_check() runs every `periodic_check_interval` completed tasks
    - All events logged to ENVIRONMENT audit stream
    - Alerts aggregated from PerformanceMonitor and surfaced to Orchestrator
    - Budget awareness: canary suite and revalidation respect budget caps
    - IFM-09: Stores execute_fn for use by periodic_check()
    - SF-5/IFM-05: Config loaded once and sections injected to sub-components
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        budget_tracker: BudgetTracker,
        audit_logger: AuditLogger | None = None,
        capability_tracker: CapabilityTracker | None = None,
        domain: str = "meta",
        model_id: str = "unknown",  # SF-9: Passed to CanaryRunner
    ):
        self.yaml_store = yaml_store
        self.budget_tracker = budget_tracker
        self.audit_logger = audit_logger
        self._domain = domain

        # IFM-09: Store execute_fn for periodic_check(). Set by session_start().
        self._execute_fn: ModelExecuteFn | None = None

        # SF-5/IFM-05: Load config ONCE and inject parsed sections to sub-components
        config_raw = yaml_store.read_raw("core/environment-awareness.yaml")
        ea = config_raw.get("environment_awareness", {})
        cs = ea.get("canary_suite", {})
        dd = ea.get("drift_detection", {})
        self._skip_if_recent_hours = float(cs.get("skip_if_recent_hours", 5))
        self._periodic_interval = int(dd.get("periodic_check_interval", 50))

        # Initialize sub-components (config sections already loaded above)
        self.canary_runner = CanaryRunner(yaml_store, domain, model_id=model_id)
        self.drift_detector = DriftDetector(yaml_store, domain)
        self.revalidation_engine = RevalidationEngine(
            yaml_store, budget_tracker, capability_tracker, domain
        )
        # IFM-08: Pass audit_logger to PerformanceMonitor (no separate JsonlWriter)
        self.performance_monitor = PerformanceMonitor(
            yaml_store, domain, audit_logger=audit_logger
        )

    def session_start(self, execute_fn: ModelExecuteFn) -> EnvironmentCheckResult:
        """Run environment checks at session start.

        Steps:
        1. Check Claude Code version
        2. Determine if canary run needed (recency check)
        3. Run canary suite if needed
        4. Detect drift against stored baseline
        5. Trigger revalidation if drift or version change detected
        6. Log all events to ENVIRONMENT audit stream

        Args:
            execute_fn: Model execution function for canary tasks.
                Signature: (prompt: str, max_tokens: int) -> (output: str, tokens_used: int)

        Returns:
            EnvironmentCheckResult with all findings.
        """
        # IFM-09: Store execute_fn for periodic_check() to use later
        self._execute_fn = execute_fn

        result = EnvironmentCheckResult()

        # Step 1: Version check (zero cost)
        version_info, version_changes = self.drift_detector.check_version()
        result.version_info = version_info
        result.version_changes = version_changes

        if version_changes:
            self._log_event(
                "version_change",
                {
                    "changes": version_changes,
                    "current": version_info.claude_code_version,
                },
            )

        # Step 2: Recency check
        if not version_changes and not self._should_run_canary():
            result.skipped = True
            result.skip_reason = "recent_fingerprint_valid"
            logger.info(
                "Canary suite skipped: recent fingerprint still valid"
            )
            self._log_event("canary_skipped", {"reason": result.skip_reason})
            return result

        # Step 3: Run canary suite
        logger.info("Running canary suite at session start...")
        suite_result = self.canary_runner.run_suite(execute_fn)
        result.fingerprint = suite_result.fingerprint
        result.canary_all_passed = suite_result.all_passed

        self._log_event(
            "fingerprint",
            {
                "scores": suite_result.task_scores,
                "total_tokens": suite_result.total_tokens,
                "all_passed": suite_result.all_passed,
            },
        )

        # Step 4: Detect drift
        drift = self.drift_detector.detect_drift(suite_result.fingerprint)
        result.drift = drift
        result.drift_detected = drift.drift_detected

        # Store the new fingerprint
        self.drift_detector.store_fingerprint(suite_result.fingerprint)

        if drift.drift_detected:
            self._log_event(
                "drift",
                {
                    "distance": drift.distance,
                    "threshold": drift.threshold,
                    "affected_dimensions": drift.affected_dimensions,
                },
            )

        # Step 5: Trigger revalidation if needed
        trigger: RevalidationTrigger | None = None
        trigger_detail = ""

        if drift.drift_detected:
            trigger = RevalidationTrigger.MODEL_DRIFT
            trigger_detail = (
                f"Drift distance {drift.distance:.4f} > "
                f"threshold {drift.threshold}. "
                f"Affected: {drift.affected_dimensions}"
            )
        elif version_changes:
            trigger = RevalidationTrigger.VERSION_CHANGE
            trigger_detail = f"Version changes: {version_changes}"

        if trigger is not None:
            reval_result = self.revalidation_engine.run_revalidation(
                trigger=trigger,
                trigger_detail=trigger_detail,
                drift=drift if drift.drift_detected else None,
                version_changes=version_changes if version_changes else None,
                pre_fingerprint=drift.baseline if drift.drift_detected else None,
                execute_fn=execute_fn,
                canary_runner=self.canary_runner,  # MF-5: pass for post_fingerprint
            )
            result.revalidation_triggered = True
            result.adaptation = reval_result.adaptation

            self._log_event(
                "revalidation",
                {
                    "trigger": str(trigger),
                    "adaptation": str(reval_result.adaptation),
                    "scope": reval_result.scope,
                    "tokens_used": reval_result.tokens_used,
                    "actions": reval_result.actions_taken,
                },
            )

        logger.info(
            f"Session start check complete: "
            f"drift={result.drift_detected}, "
            f"version_changes={result.version_changes}, "
            f"revalidation={result.revalidation_triggered}"
        )

        return result

    def periodic_check(
        self, execute_fn: ModelExecuteFn | None = None
    ) -> EnvironmentCheckResult:
        """Run periodic environment check (every N tasks).

        Lighter than session_start: focuses on canary re-run and
        performance alerts. Called by Orchestrator after task completion.

        IFM-09: Falls back to stored self._execute_fn if execute_fn not
        provided. Checks execute_fn is not None before proceeding.
        IFM-21: Degraded skills now trigger revalidation (not just logging).

        Args:
            execute_fn: Model execution function. If None, uses stored
                execute_fn from session_start().

        Returns:
            EnvironmentCheckResult with findings.
        """
        # IFM-09: Use stored execute_fn if not provided
        fn = execute_fn or self._execute_fn
        if fn is None:
            logger.warning(
                "periodic_check: no execute_fn available — "
                "skipping canary re-run"
            )
            result = EnvironmentCheckResult(
                skipped=True,
                skip_reason="no_execute_fn",
            )
            return result

        result = EnvironmentCheckResult()

        # Flush pending performance data before check
        self.performance_monitor.flush()

        # Run canary suite
        logger.info(
            f"Running periodic environment check "
            f"(interval: {self._periodic_interval} tasks)"
        )
        suite_result = self.canary_runner.run_suite(fn)
        result.fingerprint = suite_result.fingerprint
        result.canary_all_passed = suite_result.all_passed

        # Detect drift
        drift = self.drift_detector.detect_drift(suite_result.fingerprint)
        result.drift = drift
        result.drift_detected = drift.drift_detected

        # Store fingerprint
        self.drift_detector.store_fingerprint(suite_result.fingerprint)

        # Collect performance alerts
        result.alerts = self.performance_monitor.get_pending_alerts()

        # Trigger revalidation on drift
        if drift.drift_detected:
            reval_result = self.revalidation_engine.run_revalidation(
                trigger=RevalidationTrigger.MODEL_DRIFT,
                trigger_detail=(
                    f"Periodic check drift: {drift.distance:.4f} > "
                    f"{drift.threshold}"
                ),
                drift=drift,
                pre_fingerprint=drift.baseline,
                execute_fn=fn,
                canary_runner=self.canary_runner,  # MF-5
            )
            result.revalidation_triggered = True
            result.adaptation = reval_result.adaptation

            self._log_event(
                "periodic_revalidation",
                {
                    "drift_distance": drift.distance,
                    "adaptation": str(reval_result.adaptation),
                },
            )

        # IFM-21: Degraded skills trigger PERFORMANCE_DROP revalidation
        degraded = self.performance_monitor.get_degraded_skills()
        if degraded:
            skill_names = [s.skill_name for s in degraded]
            self._log_event(
                "performance_alert",
                {
                    "degraded_skills": skill_names,
                    "rates": {
                        s.skill_name: s.success_rate for s in degraded
                    },
                },
            )

            # IFM-21: Trigger revalidation for degraded skills
            if not result.revalidation_triggered:
                reval_result = self.revalidation_engine.run_revalidation(
                    trigger=RevalidationTrigger.PERFORMANCE_DROP,
                    trigger_detail=(
                        f"Degraded skills: {skill_names}"
                    ),
                    execute_fn=fn,
                    canary_runner=self.canary_runner,
                )
                result.revalidation_triggered = True
                result.adaptation = reval_result.adaptation

                self._log_event(
                    "performance_revalidation",
                    {
                        "degraded_skills": skill_names,
                        "adaptation": str(reval_result.adaptation),
                    },
                )

        # Reset task counter
        self.performance_monitor.reset_task_counter()

        return result

    def should_run_periodic_check(self) -> bool:
        """Check if periodic check is due based on task count.

        SF-8: Uses get_task_count() getter instead of accessing
        private _track attribute directly.
        """
        count = self.performance_monitor.get_task_count()
        return count >= self._periodic_interval

    def on_task_complete(
        self,
        task_type: str,
        success: bool,
        tokens_used: int = 0,
        latency_ms: int = 0,
    ) -> None:
        """Called after each task completion to update performance tracking.

        This is the primary integration point with the Orchestrator.
        """
        self.performance_monitor.record_skill_outcome(
            skill_name=task_type,
            success=success,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )
        self.performance_monitor.increment_task_counter()

    def on_tool_call(
        self,
        tool_name: str,
        success: bool,
        timed_out: bool = False,
        tokens_used: int = 0,
    ) -> None:
        """Called after each tool call to update tool performance tracking."""
        self.performance_monitor.record_tool_outcome(
            tool_name=tool_name,
            success=success,
            timed_out=timed_out,
            tokens_used=tokens_used,
        )

    def _should_run_canary(self) -> bool:
        """Check if canary suite needs to run (recency check).

        MF-6/IFM-02: Reads from state dir, not core/.
        IFM-14: Catches TypeError for timezone-naive datetime comparison.
        """
        try:
            # MF-6: Read from state dir (not core/)
            state_base = f"instances/{self._domain}/state/environment"
            data = self.yaml_store.read_raw(
                f"{state_base}/last-fingerprint.yaml"
            )
            last_run = datetime.fromisoformat(data.get("timestamp", ""))
            elapsed_hours = (
                datetime.now(timezone.utc) - last_run
            ).total_seconds() / 3600
            if elapsed_hours < self._skip_if_recent_hours:
                stored_version = data.get("claude_version", "")
                current_version = self.drift_detector.check_claude_version()
                if stored_version == current_version:
                    return False
        except (FileNotFoundError, ValueError, KeyError, TypeError):
            # IFM-14: TypeError catches timezone-naive vs timezone-aware
            # datetime comparison failures
            pass
        return True

    def _log_event(self, event_type: str, detail: dict) -> None:
        """Log an environment event to the ENVIRONMENT audit stream."""
        if self.audit_logger is None:
            return
        entry = EnvironmentLogEntry(
            id=generate_id("env"),
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            detail=detail,
        )
        self.audit_logger.log_environment(entry)
