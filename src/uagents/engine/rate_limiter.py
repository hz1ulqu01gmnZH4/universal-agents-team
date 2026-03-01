"""Rate limit mirror with backpressure propagation.
Spec reference: Section 18.3 (Rate Limit Management).

Key literature:
- ATB/AATB (arXiv:2510.04516): 97.3% fewer 429 errors
- VTC (arXiv:2401.00588): Fair scheduling with priority weights
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from enum import StrEnum

from ..models.resource import RateLimitBucket, RateLimitMirror
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.rate_limiter")


class RequestPriority(StrEnum):
    """Priority levels for rate-limit queue (VTC-inspired)."""
    CRITICAL = "critical"  # Safety, constitution checks, human-requested
    HIGH = "high"          # Active execution, review mandates
    NORMAL = "normal"      # Scout, routine evolution
    LOW = "low"            # Background analysis, speculation


class BackpressureLevel(StrEnum):
    """System-wide backpressure levels."""
    NONE = "none"           # < 80% capacity
    SLOW = "slow"           # 80% — slow spawning, queue new
    PAUSE = "pause"         # 90% — pause non-critical tasks
    SINGLE_AGENT = "single" # 95% — only highest-priority task
    FULL_STOP = "stop"      # 100% — wait for refresh


class RateLimiter:
    """Local rate limit mirror with ATB-inspired backpressure.

    Design invariants:
    - Mirror is pessimistic: overestimates consumption (safe side)
    - Buckets replenish per minute (sliding window approximation)
    - Backpressure propagated as float 0.0-1.0 to orchestrator
    - Cached tokens excluded from ITPM accounting
    - State persisted to YAML for crash recovery
    """

    # Backpressure thresholds (from spec Section 18.3)
    SLOW_THRESHOLD = 0.80
    PAUSE_THRESHOLD = 0.90
    SINGLE_AGENT_THRESHOLD = 0.95
    STOP_THRESHOLD = 1.00

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        rpm_estimate: int = 50,
        itpm_estimate: int = 80_000,
        otpm_estimate: int = 16_000,
    ):
        self.yaml_store = yaml_store
        self.domain = domain
        self._state_path = f"instances/{domain}/state/resources/rate_limits.yaml"

        # Ensure directory exists
        yaml_store.ensure_dir(f"instances/{domain}/state/resources")

        # Initialize or load mirror
        try:
            self._mirror = yaml_store.read(self._state_path, RateLimitMirror)
        except FileNotFoundError:
            self._mirror = RateLimitMirror(
                rpm=RateLimitBucket(capacity=rpm_estimate, current=0, replenish_rate="per minute"),
                itpm=RateLimitBucket(capacity=itpm_estimate, current=0, replenish_rate="per minute"),
                otpm=RateLimitBucket(capacity=otpm_estimate, current=0, replenish_rate="per minute"),
                last_updated=datetime.now(timezone.utc),
            )
            self._persist()

        # FM-33: On restart, force an immediate replenishment to clear
        # stale accumulated values from the persisted mirror.
        self._last_replenish = time.monotonic() - 60.0

    def record_request(
        self,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
    ) -> None:
        """Record an API request's token consumption.

        Cached tokens do NOT count toward ITPM (rate-limit arbitrage).
        """
        self._maybe_replenish()

        self._mirror.rpm.current += 1
        # Only non-cached input tokens count toward ITPM
        effective_input = input_tokens - cached_tokens
        self._mirror.itpm.current += max(0, effective_input)
        self._mirror.otpm.current += output_tokens
        self._mirror.last_updated = datetime.now(timezone.utc)

        self._persist()

        bp = self.get_backpressure()
        if bp >= self.PAUSE_THRESHOLD:
            logger.warning(
                f"Rate pressure high: backpressure={bp:.2f} "
                f"RPM={self._mirror.rpm.current}/{self._mirror.rpm.capacity} "
                f"ITPM={self._mirror.itpm.current}/{self._mirror.itpm.capacity}"
            )

    def can_send(self, estimated_input: int, estimated_output: int,
                 priority: RequestPriority = RequestPriority.NORMAL) -> tuple[bool, str]:
        """Check if a request can be sent without exceeding limits.

        Critical requests always pass (safety).
        """
        if priority == RequestPriority.CRITICAL:
            return True, "Critical priority — always allowed"

        self._maybe_replenish()

        if self._mirror.rpm.current >= self._mirror.rpm.capacity:
            return False, f"RPM limit reached: {self._mirror.rpm.current}/{self._mirror.rpm.capacity}"

        if self._mirror.itpm.current + estimated_input > self._mirror.itpm.capacity:
            return False, (
                f"ITPM would exceed limit: {self._mirror.itpm.current} + {estimated_input} "
                f"> {self._mirror.itpm.capacity}"
            )

        if self._mirror.otpm.current + estimated_output > self._mirror.otpm.capacity:
            return False, (
                f"OTPM would exceed limit: {self._mirror.otpm.current} + {estimated_output} "
                f"> {self._mirror.otpm.capacity}"
            )

        return True, "Within rate limits"

    def get_backpressure(self) -> float:
        """Compute overall backpressure level (0.0-1.0).

        Takes the maximum utilization across all three buckets.
        """
        self._maybe_replenish()

        rpm_util = self._mirror.rpm.current / max(1, self._mirror.rpm.capacity)
        itpm_util = self._mirror.itpm.current / max(1, self._mirror.itpm.capacity)
        otpm_util = self._mirror.otpm.current / max(1, self._mirror.otpm.capacity)

        return max(rpm_util, itpm_util, otpm_util)

    def get_backpressure_level(self) -> BackpressureLevel:
        """Get the backpressure level as a named enum."""
        bp = self.get_backpressure()
        if bp >= self.STOP_THRESHOLD:
            return BackpressureLevel.FULL_STOP
        if bp >= self.SINGLE_AGENT_THRESHOLD:
            return BackpressureLevel.SINGLE_AGENT
        if bp >= self.PAUSE_THRESHOLD:
            return BackpressureLevel.PAUSE
        if bp >= self.SLOW_THRESHOLD:
            return BackpressureLevel.SLOW
        return BackpressureLevel.NONE

    def handle_429(self, retry_after: float | None = None) -> float:
        """Handle a 429 rate limit response.

        FM-23: Marks ALL THREE buckets at capacity (pessimistic).
        Returns recommended wait time in seconds.
        """
        self._mirror.rpm.current = self._mirror.rpm.capacity
        self._mirror.itpm.current = self._mirror.itpm.capacity
        self._mirror.otpm.current = self._mirror.otpm.capacity
        self._mirror.last_updated = datetime.now(timezone.utc)
        # Reset replenish timer — these are fresh server-derived values
        self._last_replenish = time.monotonic()
        self._persist()

        wait = retry_after if retry_after else 60.0
        logger.warning(f"429 received. Waiting {wait}s. Backpressure propagated.")
        return wait

    def update_from_headers(self, headers: dict) -> None:
        """Update mirror from API response headers.

        FM-60: Also parses OTPM headers if present.
        """
        if "x-ratelimit-limit-requests" in headers:
            self._mirror.rpm.capacity = int(headers["x-ratelimit-limit-requests"])
        if "x-ratelimit-remaining-requests" in headers:
            remaining = int(headers["x-ratelimit-remaining-requests"])
            self._mirror.rpm.current = self._mirror.rpm.capacity - remaining
        if "x-ratelimit-limit-tokens" in headers:
            self._mirror.itpm.capacity = int(headers["x-ratelimit-limit-tokens"])
        if "x-ratelimit-remaining-tokens" in headers:
            remaining = int(headers["x-ratelimit-remaining-tokens"])
            self._mirror.itpm.current = self._mirror.itpm.capacity - remaining
        # FM-60: Parse OTPM headers if available
        if "x-ratelimit-limit-output-tokens" in headers:
            self._mirror.otpm.capacity = int(headers["x-ratelimit-limit-output-tokens"])
        if "x-ratelimit-remaining-output-tokens" in headers:
            remaining = int(headers["x-ratelimit-remaining-output-tokens"])
            self._mirror.otpm.current = self._mirror.otpm.capacity - remaining

        self._mirror.last_updated = datetime.now(timezone.utc)
        # Reset replenish timer — these are fresh server-derived values
        self._last_replenish = time.monotonic()
        self._persist()

    # ── Internal ──

    def _maybe_replenish(self) -> None:
        """Replenish buckets based on elapsed time.

        FM-44: Advance _last_replenish by exactly `minutes * 60` seconds
        (not `now`) to preserve the fractional remainder.
        """
        now = time.monotonic()
        elapsed = now - self._last_replenish
        if elapsed >= 60.0:
            minutes = int(elapsed / 60.0)
            for _ in range(minutes):
                self._mirror.rpm.current = max(0, self._mirror.rpm.current - self._mirror.rpm.capacity)
                self._mirror.itpm.current = max(0, self._mirror.itpm.current - self._mirror.itpm.capacity)
                self._mirror.otpm.current = max(0, self._mirror.otpm.current - self._mirror.otpm.capacity)
            # FM-44: Advance by exact minutes, preserving fractional remainder
            self._last_replenish += minutes * 60.0

    def _persist(self) -> None:
        """Persist mirror state."""
        self.yaml_store.write(self._state_path, self._mirror)
