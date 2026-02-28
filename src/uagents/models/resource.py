"""Resource awareness models.
Spec reference: Section 18 (Resource Awareness & Token Efficiency)."""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum, StrEnum

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
