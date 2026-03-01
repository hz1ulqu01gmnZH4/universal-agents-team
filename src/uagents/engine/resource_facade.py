"""Single entry point for resource consumption recording (FM-64).
Spec reference: Section 18 (Resource Awareness & Self-Budgeting).

Wraps BudgetTracker, RateLimiter, and ResourceTracker to ensure
consistent recording across all resource dimensions. Also constructs
ResourceSnapshot (FM-56) and logs to audit (FM-65).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ..models.audit import LogStream, ResourceLogEntry
from ..models.base import generate_id
from ..models.resource import BudgetPressureLevel, ResourceSnapshot

if TYPE_CHECKING:
    from ..audit.logger import AuditLogger
    from .budget_tracker import BudgetTracker
    from .rate_limiter import RateLimiter
    from .resource_tracker import ResourceTracker

logger = logging.getLogger("uagents.resource_facade")


class ResourceFacade:
    """Single entry point for recording resource consumption (FM-64).

    Wraps BudgetTracker and RateLimiter to ensure consistent recording.
    Also constructs ResourceSnapshot (FM-56) and logs to audit (FM-65).
    """

    def __init__(
        self,
        budget_tracker: BudgetTracker,
        rate_limiter: RateLimiter,
        resource_tracker: ResourceTracker,
        audit_logger: AuditLogger | None = None,
    ):
        self.budget = budget_tracker
        self.rate = rate_limiter
        self.compute = resource_tracker
        self.audit = audit_logger
        # S-7: Delta tracking for cumulative /usage output
        self._last_synced_input: int = 0
        self._last_synced_output: int = 0
        self._last_synced_cache: int = 0

    def record_consumption(
        self,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
    ) -> None:
        """Record token consumption in both budget and rate tracking."""
        total = input_tokens + output_tokens
        self.budget.record_consumption(total, is_cached=(cached_tokens > 0))
        self.rate.record_request(input_tokens, output_tokens, cached_tokens)

    def take_snapshot(self, reason: str) -> ResourceSnapshot:
        """Create a point-in-time snapshot (FM-56).

        Called before every resource-consuming decision (spawn, task start).
        Persisted to audit log for post-hoc analysis (FM-65).
        """
        window = self.budget.get_window()
        weekly = self.budget.get_weekly()
        metrics = self.compute.check_compute()

        can_spawn = (
            metrics.cpu_percent < 85.0
            and window.pressure_level != BudgetPressureLevel.RED
        )
        rejection = None
        if not can_spawn:
            if metrics.cpu_percent >= 85.0:
                rejection = f"CPU too high: {metrics.cpu_percent}%"
            else:
                rejection = f"Budget pressure: {window.pressure_level}"

        snapshot = ResourceSnapshot(
            timestamp=datetime.now(timezone.utc),
            compute=metrics,
            window_budget=window,
            weekly_budget=weekly,
            rate_pressure=self.rate.get_backpressure(),
            budget_pressure=window.pressure_level,
            can_spawn=can_spawn,
            spawn_rejection_reason=rejection,
        )

        # FM-65: Log to RESOURCES audit stream
        if self.audit is not None:
            self.audit.log_resource(ResourceLogEntry(
                id=generate_id("rlog"),
                timestamp=snapshot.timestamp,
                event_type=reason,
                detail=snapshot.model_dump(),
            ))

        return snapshot

    def sync_from_usage(self) -> dict | None:
        """FM-57/FM-113/S-7: Sync budget tracker from /usage command output.

        Calls ResourceTracker.parse_usage_output() and feeds DELTA
        into BudgetTracker.record_consumption(). Returns parsed data
        or None if parsing failed.

        FM-113: Uses self.record_consumption() which is defined on
        ResourceFacade (line 46), not on budget_tracker. This routes
        through both budget and rate tracking.

        S-7: Tracks last-seen totals to compute deltas. The /usage
        command returns cumulative totals, not per-call increments.
        Without delta tracking, every sync would re-count all usage.
        """
        usage_data = self.compute.parse_usage_output()
        if usage_data is None:
            return None

        input_tokens = usage_data.get("input_tokens", 0)
        output_tokens = usage_data.get("output_tokens", 0)
        cache_read = usage_data.get("cache_read", 0)

        # S-7: Compute delta from last sync (cumulative → incremental)
        delta_input = input_tokens - self._last_synced_input
        delta_output = output_tokens - self._last_synced_output
        delta_cache = cache_read - self._last_synced_cache

        # IFM-07: Guard against negative deltas (session restart or /usage reset)
        if delta_input < 0 or delta_output < 0:
            logger.warning(
                f"Cumulative /usage decreased (reset detected). "
                f"delta_input={delta_input}, delta_output={delta_output}. "
                f"Treating current values as new baseline."
            )
            delta_input = max(0, delta_input)
            delta_output = max(0, delta_output)
            delta_cache = max(0, delta_cache)

        if delta_input > 0 or delta_output > 0:
            self.record_consumption(
                input_tokens=delta_input,
                output_tokens=delta_output,
                cached_tokens=max(0, delta_cache),
            )

        # Always update baseline (even on reset, to prevent perpetual negative deltas)
        self._last_synced_input = input_tokens
        self._last_synced_output = output_tokens
        self._last_synced_cache = cache_read

        usage_data["delta_input"] = delta_input
        usage_data["delta_output"] = delta_output
        return usage_data
