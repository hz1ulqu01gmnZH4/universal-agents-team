"""Resource awareness models.
Spec reference: Section 18 (Resource Awareness & Token Efficiency).

Phase 1.5 additions: WindowBudget, WeeklyBudget, ResourceSnapshot,
CostRecord, DailyCostSummary, TaskBudgetAnnotation, ResourceEfficiencyMetrics.
"""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum, StrEnum

from pydantic import field_validator

from .base import FrameworkModel


class BudgetPressureLevel(StrEnum):
    """Budget pressure levels from Section 18.2."""

    GREEN = "green"    # > 60% remaining — normal operation
    YELLOW = "yellow"  # 30-60% — compress, reduce tool calls
    ORANGE = "orange"  # 10-30% — critical-only, single-agent
    RED = "red"        # < 10% — emergency: park everything, alert human


class TokenBudget(FrameworkModel):
    remaining_tokens: int
    remaining_requests: int
    window_reset_time: datetime
    weekly_utilization: float
    task_budget: int
    task_spent: int
    pressure_level: BudgetPressureLevel


class RateLimitBucket(FrameworkModel):
    capacity: int
    current: int
    replenish_rate: str  # "per minute"


class RateLimitMirror(FrameworkModel):
    """Local mirror of server-side rate limits (Section 18.3)."""

    rpm: RateLimitBucket
    itpm: RateLimitBucket
    otpm: RateLimitBucket
    last_updated: datetime


class ComputeMetrics(FrameworkModel):
    """System resource metrics (Section 18.4)."""

    cpu_percent: float
    memory_percent: float
    disk_percent: float
    active_agents: int
    max_agents: int


class SpendLevel(IntEnum):
    """Monetary cost approval tiers (Section 18.5)."""

    FREE = 0    # File ops, git, Claude API (subscription)
    LOW = 1     # Web search, small API calls < $0.10
    MEDIUM = 2  # Large API calls $0.10-$10
    HIGH = 3    # SaaS subscriptions, > $10


class CostApproval(FrameworkModel):
    spend_level: SpendLevel
    amount: float
    purpose: str
    approved: bool
    approved_by: str | None = None


# ---------------------------------------------------------------------------
# Phase 1.5 additions
# ---------------------------------------------------------------------------


class WindowBudget(FrameworkModel):
    """Tracks token consumption within a rolling time window.

    Models the Claude Max subscription constraint: ~88K tokens per 5-hour
    window (Max5) or ~220K (Max20), with weekly caps.
    """
    window_start: datetime
    window_duration_hours: float = 5.0
    estimated_capacity: int = 88_000  # Max5 default; Max20 = 220_000
    tokens_consumed: int = 0
    requests_made: int = 0
    last_request_at: datetime | None = None

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.estimated_capacity - self.tokens_consumed)

    @property
    def utilization(self) -> float:
        if self.estimated_capacity <= 0:
            return 1.0
        return self.tokens_consumed / self.estimated_capacity

    @property
    def pressure_level(self) -> BudgetPressureLevel:
        remaining_pct = 1.0 - self.utilization
        if remaining_pct > 0.60:
            return BudgetPressureLevel.GREEN
        if remaining_pct > 0.30:
            return BudgetPressureLevel.YELLOW
        if remaining_pct > 0.10:
            return BudgetPressureLevel.ORANGE
        return BudgetPressureLevel.RED


class WeeklyBudget(FrameworkModel):
    """Tracks weekly token allocation.

    Weekly cap is empirically determined and may change without notice.
    Start conservative and adjust based on observed limits.
    """
    week_start: datetime
    estimated_weekly_cap: int = 1_000_000  # Conservative default
    tokens_consumed: int = 0
    windows_used: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.estimated_weekly_cap - self.tokens_consumed)

    @property
    def utilization(self) -> float:
        if self.estimated_weekly_cap <= 0:
            return 1.0
        return self.tokens_consumed / self.estimated_weekly_cap


class ResourceSnapshot(FrameworkModel):
    """Point-in-time snapshot of all resource dimensions.

    Created before every resource-consuming decision (spawn, task start).
    Persisted to audit log for post-hoc analysis.
    """
    timestamp: datetime
    compute: ComputeMetrics
    window_budget: WindowBudget
    weekly_budget: WeeklyBudget
    rate_pressure: float  # 0.0 = no pressure, 1.0 = at limit
    budget_pressure: BudgetPressureLevel
    can_spawn: bool
    spawn_rejection_reason: str | None = None


class CostRecord(FrameworkModel):
    """Audit record for a cost-incurring action."""
    id: str
    timestamp: datetime
    spend_level: SpendLevel
    amount: float
    currency: str = "USD"
    purpose: str
    approved: bool
    approved_by: str | None = None
    task_id: str | None = None
    agent_id: str | None = None


class DailyCostSummary(FrameworkModel):
    """Aggregated daily cost tracking for cap enforcement."""
    date: str  # YYYY-MM-DD — validated below
    total_spent: float = 0.0
    daily_cap: float = 10.0  # Default $10/day
    records: list[str] = []  # CostRecord IDs

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """FM-45: Enforce YYYY-MM-DD format (fail-loud)."""
        from datetime import datetime as dt
        try:
            dt.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"date must be YYYY-MM-DD format, got: {v!r}")
        return v

    @property
    def remaining(self) -> float:
        return max(0.0, self.daily_cap - self.total_spent)

    @property
    def at_cap(self) -> bool:
        return self.total_spent >= self.daily_cap


class TaskBudgetAnnotation(FrameworkModel):
    """Budget metadata attached to a task during execution.

    Provides BATS-style continuous budget visibility to executing agents.
    """
    estimated_tokens: int
    allocated_tokens: int
    spent_tokens: int = 0
    pressure_at_start: BudgetPressureLevel = BudgetPressureLevel.GREEN
    estimation_method: str = "cold_seed"  # cold_seed | rolling_average | manual

    @property
    def remaining(self) -> int:
        return max(0, self.allocated_tokens - self.spent_tokens)

    @property
    def utilization(self) -> float:
        if self.allocated_tokens <= 0:
            return 1.0
        return self.spent_tokens / self.allocated_tokens


class ResourceEfficiencyMetrics(FrameworkModel):
    """Self-improvement metrics tracked per task (Section 18.6).

    FM-54: cache_hit_rate uses total_input_tokens (not total) as denominator.
    """
    task_id: str
    cost_of_pass: int  # Total tokens to achieve successful completion
    tokens_per_quality_point: float | None = None
    budget_utilization: float  # productive / total
    cache_hit_tokens: int = 0
    total_input_tokens: int = 0
    waste_tokens: int = 0  # Failed approaches, redundant reasoning
    review_rounds: int = 1

    @property
    def cache_hit_rate(self) -> float:
        if self.total_input_tokens <= 0:
            return 0.0
        return self.cache_hit_tokens / self.total_input_tokens
