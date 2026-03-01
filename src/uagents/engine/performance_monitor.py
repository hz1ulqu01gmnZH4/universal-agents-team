"""Continuous performance monitoring for skills, tools, and structured traces.
Spec reference: Section 19.2 (Continuous Performance Monitoring).

Tracks per-skill success rates (rolling window of 20), per-tool reliability,
and structured traces at 3 levels (operational, cognitive, contextual).

Key constraints:
- Rolling window size is configurable (default 20)
- Alert on > 10pp drop from established baseline
- Tool quarantine at < 50% success rate
- Trace retention: last 100 tasks
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime, timezone

from ..audit.logger import AuditLogger
from ..models.audit import LogStream, TraceLogEntry
from ..models.base import generate_id
from ..models.environment import (
    PerformanceAlert,
    PerformanceTrack,
    SkillPerformance,
    ToolPerformance,
    TraceEntry,
    TraceLevel,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.performance_monitor")

# SF-2/IFM-22: PerformanceAlert is now a FrameworkModel defined in
# models/environment.py. No longer a plain class in this module.


class PerformanceMonitor:
    """Tracks per-skill and per-tool performance with alerts.

    Design invariants:
    - Rolling window for skills (configurable, default 20)
    - Baseline established after first `window_size` attempts
    - Alerts surfaced but not acted upon (Phase 2.5 detects, Phase 4+ acts)
    - Tool quarantine flag set but not enforced (Phase 3.5 enforces)
    - State persisted to YAML for crash recovery
    - Traces logged via AuditLogger for structured debugging
    - SF-4/IFM-25: All _track mutations guarded by threading.Lock
    - MF-7/IFM-15: Dirty flag + batch writes (persist every 5 updates)
    - IFM-08: Uses injected AuditLogger instead of separate JsonlWriter
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        audit_logger: AuditLogger | None = None,  # IFM-08: Injected
    ):
        self.yaml_store = yaml_store
        self._domain = domain
        self._state_base = f"instances/{domain}/state/environment"
        self.yaml_store.ensure_dir(self._state_base)

        # Load config
        config_raw = yaml_store.read_raw("core/environment-awareness.yaml")
        ea = config_raw.get("environment_awareness", {})
        pm = ea.get("performance_monitoring", {})
        self._skill_window_size = int(pm.get("skill_window_size", 20))
        self._skill_alert_drop = float(pm.get("skill_alert_drop_pp", 10)) / 100.0
        self._tool_alert_drop = float(pm.get("tool_alert_drop_pp", 15)) / 100.0
        self._tool_quarantine_threshold = float(
            pm.get("tool_quarantine_threshold", 0.5)
        )
        self._trace_retention = int(pm.get("trace_retention_tasks", 100))

        # SF-4/IFM-25: Thread safety for _track mutations
        self._lock = threading.Lock()

        # Load persisted state
        self._track = self._load_track()

        # MF-7/IFM-15: Dirty flag + batch writes
        self._dirty_count = 0
        self._BATCH_WRITE_THRESHOLD = 5  # Persist every 5 updates

        # Pending alerts (consumed by EnvironmentMonitor on each check)
        self._pending_alerts: list[PerformanceAlert] = []

        # IFM-08: Use injected AuditLogger for traces (no separate JsonlWriter)
        self._audit_logger = audit_logger

        # In-memory trace task IDs for retention management
        self._traced_task_ids: deque[str] = deque(maxlen=self._trace_retention)

    def record_skill_outcome(
        self,
        skill_name: str,
        success: bool,
        tokens_used: int = 0,
        latency_ms: int = 0,
    ) -> SkillPerformance:
        """Record a skill execution outcome.

        SF-4/IFM-25: All _track mutations guarded by self._lock.
        MF-7/IFM-15: Uses dirty flag + batch writes.
        IFM-17: Deduplicates alerts by target_name + alert_type.

        Args:
            skill_name: Name/type of the skill (matches task_type).
            success: Whether the execution succeeded.
            tokens_used: Tokens consumed by this execution.
            latency_ms: Wall-clock time in milliseconds.

        Returns:
            Updated SkillPerformance record.
        """
        with self._lock:
            if skill_name not in self._track.skills:
                self._track.skills[skill_name] = SkillPerformance(
                    skill_name=skill_name
                )
            skill = self._track.skills[skill_name]

            # Update rolling window
            skill.recent_outcomes.append(success)
            if len(skill.recent_outcomes) > self._skill_window_size:
                skill.recent_outcomes = skill.recent_outcomes[
                    -self._skill_window_size:
                ]

            # Update totals
            skill.total_attempts += 1
            if success:
                skill.total_successes += 1
            skill.total_tokens += tokens_used
            skill.total_latency_ms += latency_ms
            skill.last_updated = datetime.now(timezone.utc)

            # Establish baseline after first full window
            if (
                skill.baseline_success_rate is None
                and len(skill.recent_outcomes) >= self._skill_window_size
            ):
                skill.baseline_success_rate = skill.success_rate
                logger.info(
                    f"Skill baseline established: {skill_name} = "
                    f"{skill.baseline_success_rate:.2%}"
                )

            # Check for alerts
            drop = skill.success_rate_drop
            if drop is not None and drop > self._skill_alert_drop:
                alert = PerformanceAlert(
                    alert_type="skill_degradation",
                    target_name=skill_name,
                    message=(
                        f"Skill '{skill_name}' success rate dropped "
                        f"{drop:.1%} from baseline "
                        f"({skill.baseline_success_rate:.2%} -> "
                        f"{skill.success_rate:.2%})"
                    ),
                    current_rate=skill.success_rate,
                    baseline_rate=skill.baseline_success_rate,
                    timestamp=datetime.now(timezone.utc),
                )
                # IFM-17: Deduplicate by target_name + alert_type
                existing_keys = {
                    (a.target_name, a.alert_type) for a in self._pending_alerts
                }
                if (skill_name, "skill_degradation") not in existing_keys:
                    self._pending_alerts.append(alert)
                logger.warning(alert.message)

            self._maybe_save_track()
            return skill

    def record_tool_outcome(
        self,
        tool_name: str,
        success: bool,
        timed_out: bool = False,
        tokens_used: int = 0,
    ) -> ToolPerformance:
        """Record a tool execution outcome.

        SF-4/IFM-25: Guarded by self._lock.
        IFM-17: Deduplicates alerts.

        Args:
            tool_name: Name of the tool.
            success: Whether the tool call succeeded.
            timed_out: Whether the call timed out.
            tokens_used: Tokens consumed by this tool call.

        Returns:
            Updated ToolPerformance record.
        """
        with self._lock:
            if tool_name not in self._track.tools:
                self._track.tools[tool_name] = ToolPerformance(tool_name=tool_name)
            tool = self._track.tools[tool_name]

            tool.total_calls += 1
            if success:
                tool.successful_calls += 1
            else:
                tool.failed_calls += 1
            if timed_out:
                tool.timeout_calls += 1
            tool.total_tokens += tokens_used
            tool.last_updated = datetime.now(timezone.utc)

            # Check for quarantine threshold
            if (
                tool.total_calls >= 10
                and tool.success_rate < self._tool_quarantine_threshold
            ):
                alert = PerformanceAlert(
                    alert_type="tool_quarantine",
                    target_name=tool_name,
                    message=(
                        f"Tool '{tool_name}' success rate "
                        f"{tool.success_rate:.2%} < quarantine threshold "
                        f"{self._tool_quarantine_threshold:.2%} "
                        f"({tool.total_calls} calls)"
                    ),
                    current_rate=tool.success_rate,
                    baseline_rate=None,
                    timestamp=datetime.now(timezone.utc),
                )
                # IFM-17: Deduplicate by target_name + alert_type
                existing_keys = {
                    (a.target_name, a.alert_type) for a in self._pending_alerts
                }
                if (tool_name, "tool_quarantine") not in existing_keys:
                    self._pending_alerts.append(alert)
                logger.warning(alert.message)

            self._maybe_save_track()
            return tool

    def record_trace(
        self,
        level: TraceLevel,
        task_id: str,
        category: str,
        detail: dict,
        tokens_used: int = 0,
        latency_ms: int = 0,
    ) -> None:
        """Record a structured trace entry.

        IFM-08: Uses injected AuditLogger instead of separate JsonlWriter
        to avoid duplicate trace writers and inconsistent log files.

        Args:
            level: Trace level (operational, cognitive, contextual).
            task_id: ID of the task being traced.
            category: Category of the trace (e.g., "tool_call", "reasoning_step").
            detail: Structured detail data.
            tokens_used: Tokens consumed.
            latency_ms: Time taken.
        """
        if self._audit_logger is None:
            return  # No audit logger available — traces not recorded

        now = datetime.now(timezone.utc)

        # Write to JSONL trace log via AuditLogger
        log_entry = TraceLogEntry(
            id=generate_id("trace"),
            timestamp=now,
            level=level.value,
            detail={
                "task_id": task_id,
                "category": category,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                **detail,
            },
        )
        self._audit_logger.log_trace(log_entry)

        # Track task for retention
        if task_id not in self._traced_task_ids:
            self._traced_task_ids.append(task_id)

    def get_pending_alerts(self) -> list[PerformanceAlert]:
        """Consume and return pending alerts. Clears the alert queue.

        IFM-N01: Guarded by self._lock to prevent race conditions.
        """
        with self._lock:
            alerts = list(self._pending_alerts)
            self._pending_alerts.clear()
            return alerts

    def get_skill_performance(self, skill_name: str) -> SkillPerformance | None:
        """Get performance record for a specific skill.

        IFM-N02: Guarded by self._lock to prevent race conditions.
        """
        with self._lock:
            return self._track.skills.get(skill_name)

    def get_tool_performance(self, tool_name: str) -> ToolPerformance | None:
        """Get performance record for a specific tool.

        IFM-N02: Guarded by self._lock to prevent race conditions.
        """
        with self._lock:
            return self._track.tools.get(tool_name)

    def get_all_skill_performances(self) -> dict[str, SkillPerformance]:
        """Get all skill performance records.

        IFM-N03: Guarded by self._lock to prevent race conditions.
        """
        with self._lock:
            return dict(self._track.skills)

    def get_all_tool_performances(self) -> dict[str, ToolPerformance]:
        """Get all tool performance records.

        IFM-N03: Guarded by self._lock to prevent race conditions.
        """
        with self._lock:
            return dict(self._track.tools)

    def get_degraded_skills(self) -> list[SkillPerformance]:
        """Get skills whose success rate dropped > alert threshold from baseline.

        IFM-N01: Guarded by self._lock to prevent race conditions.
        """
        with self._lock:
            degraded: list[SkillPerformance] = []
            for skill in self._track.skills.values():
                drop = skill.success_rate_drop
                if drop is not None and drop > self._skill_alert_drop:
                    degraded.append(skill)
            return sorted(degraded, key=lambda s: s.success_rate)

    def get_quarantined_tools(self) -> list[ToolPerformance]:
        """Get tools below quarantine threshold with sufficient data.

        IFM-N01: Guarded by self._lock to prevent race conditions.
        """
        with self._lock:
            quarantined: list[ToolPerformance] = []
            for tool in self._track.tools.values():
                if (
                    tool.total_calls >= 10
                    and tool.success_rate < self._tool_quarantine_threshold
                ):
                    quarantined.append(tool)
            return quarantined

    def get_task_count(self) -> int:
        """SF-8: Public getter for tasks-since-last-check counter.
        Replaces direct access to self._track.tasks_since_last_check.

        IFM-N03: Guarded by self._lock to prevent race conditions.
        """
        with self._lock:
            return self._track.tasks_since_last_check

    def increment_task_counter(self) -> int:
        """Increment and return the tasks-since-last-check counter."""
        with self._lock:
            self._track.tasks_since_last_check += 1
            self._maybe_save_track()
            return self._track.tasks_since_last_check

    def reset_task_counter(self) -> None:
        """Reset the tasks-since-last-check counter (after periodic check).

        IFM-N28: Catches exceptions from _flush_track_unlocked() to prevent
        persistence failures from blocking the counter reset.
        """
        with self._lock:
            self._track.tasks_since_last_check = 0
            try:
                self._flush_track_unlocked()
            except Exception as e:
                logger.warning(f"Failed to persist task counter reset: {e}")

    def _load_track(self) -> PerformanceTrack:
        """Load performance track from YAML or create new.

        IFM-03: YamlStore.read() uses strict=False in model_validate(),
        which overrides the class-level strict=True. This is intentional
        for YAML roundtrip compatibility with nested models.
        Test requirement: verify PerformanceTrack roundtrip (write then read)
        produces identical data.

        IFM-04: Trims recent_outcomes to skill_window_size after load,
        in case the config changed between sessions.
        """
        path = f"{self._state_base}/performance-track.yaml"
        try:
            track = self.yaml_store.read(path, PerformanceTrack)
            # IFM-04: Trim recent_outcomes if config changed
            for skill in track.skills.values():
                if len(skill.recent_outcomes) > self._skill_window_size:
                    skill.recent_outcomes = skill.recent_outcomes[
                        -self._skill_window_size:
                    ]
            return track
        except Exception as e:
            if not isinstance(e, FileNotFoundError):
                logger.warning(
                    f"Corrupt performance track, resetting: {e}"
                )
            return PerformanceTrack(created_at=datetime.now(timezone.utc))

    def _maybe_save_track(self) -> None:
        """MF-7/IFM-15: Batch writes — only persist every N updates.

        Reduces YAML write frequency to prevent excessive I/O.
        Caller must hold self._lock.
        """
        self._dirty_count += 1
        if self._dirty_count >= self._BATCH_WRITE_THRESHOLD:
            self._flush_track_unlocked()

    def _flush_track(self) -> None:
        """Force-persist performance track to YAML (acquires lock)."""
        with self._lock:
            self._flush_track_unlocked()

    def _flush_track_unlocked(self) -> None:
        """Force-persist performance track to YAML (caller holds lock)."""
        self._track.updated_at = datetime.now(timezone.utc)
        self.yaml_store.write(
            f"{self._state_base}/performance-track.yaml",
            self._track,
        )
        self._dirty_count = 0

    def flush(self) -> None:
        """Public flush — persist any dirty state immediately.

        MF-7/IFM-15: Called by EnvironmentMonitor at session end or
        before periodic checks to ensure no data is lost.
        """
        self._flush_track()
