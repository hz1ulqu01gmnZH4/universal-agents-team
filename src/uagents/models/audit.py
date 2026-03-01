"""Audit logging models.
Spec reference: Section 17 (Audit System & Viewers)."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from .base import FrameworkModel
from .evolution import EvolutionTier


class LogStream(StrEnum):
    """8 audit log streams."""

    EVOLUTION = "evolution"
    TASKS = "tasks"
    DECISIONS = "decisions"
    DIVERSITY = "diversity"
    CREATIVITY = "creativity"
    RESOURCES = "resources"
    ENVIRONMENT = "environment"
    TRACES = "traces"


class BaseLogEntry(FrameworkModel):
    """Base for all log entries."""

    id: str
    timestamp: datetime
    stream: LogStream


class EvolutionLogEntry(BaseLogEntry):
    """Evolution audit log entry — enhanced for Phase 4 lifecycle.

    DR-02-FIX: Backward-compatible with existing callers (SkillLibrary).
    Old required fields now have defaults. New Phase 4 fields added.
    """

    stream: Literal[LogStream.EVOLUTION] = LogStream.EVOLUTION
    tier: EvolutionTier
    component: str
    diff: str
    rationale: str
    evidence: dict
    # Original fields — KEEP with defaults for backward compatibility
    # (used by SkillLibrary._log_ring_transition and other Phase 3.5 callers)
    approved_by: str = ""
    constitutional_check: str = ""
    rollback_commit: str = ""
    # Phase 4 additions (all have defaults — backward compatible):
    lifecycle_state: str = ""  # EvolutionLifecycleState value
    outcome: str = ""          # EvolutionOutcome value
    evaluation_score: float = 0.0  # Overall evaluation score
    trigger: str = ""          # ObservationTrigger value


class TaskLogEntry(BaseLogEntry):
    stream: Literal[LogStream.TASKS] = LogStream.TASKS
    task_id: str
    event: str
    task_title: str
    actor: str
    actor_role: str
    detail: dict
    tokens_used: int = 0


class DecisionLogEntry(BaseLogEntry):
    stream: Literal[LogStream.DECISIONS] = LogStream.DECISIONS
    decision_type: str
    actor: str
    options_considered: list[dict]
    selected: str
    rationale: str


class ResourceLogEntry(BaseLogEntry):
    stream: Literal[LogStream.RESOURCES] = LogStream.RESOURCES
    event_type: str  # budget_check, rate_limit, spawn_decision, cost_approval
    detail: dict


class EnvironmentLogEntry(BaseLogEntry):
    stream: Literal[LogStream.ENVIRONMENT] = LogStream.ENVIRONMENT
    event_type: str  # fingerprint, drift, revalidation, version_change
    detail: dict


class DiversityLogEntry(BaseLogEntry):
    stream: Literal[LogStream.DIVERSITY] = LogStream.DIVERSITY
    task_id: str
    srd_composite: float
    text_diversity: float
    vdi_score: float | None = None
    agent_count: int
    stagnation_signals: list[dict]
    health_status: str


class ConsumptionLogEntry(BaseLogEntry):
    """FM-18: Typed consumption record for append-only ledger."""
    stream: Literal[LogStream.RESOURCES] = LogStream.RESOURCES
    tokens: int
    is_cached: bool = False


class TraceLogEntry(BaseLogEntry):
    stream: Literal[LogStream.TRACES] = LogStream.TRACES
    level: Literal["operational", "cognitive", "contextual"]
    detail: dict
