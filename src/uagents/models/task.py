"""Task lifecycle models.
Spec reference: Section 6 (Task Lifecycle — Full Audit)."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field

from .base import FrameworkModel, IdentifiableModel, TimestampedModel
from .capability import ModelPreference
from .constitution import TaskMandate


class TaskStatus(StrEnum):
    """9 task states from Section 6.1."""

    INTAKE = "intake"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    EXECUTING = "executing"
    PARKED = "parked"
    REVIEWING = "reviewing"
    VERDICT = "verdict"
    COMPLETE = "complete"
    ARCHIVED = "archived"


class TaskOriginType(StrEnum):
    """How a task was created."""

    HUMAN = "human"
    AGENT_GENERATED = "agent_generated"
    EVOLUTION_TRIGGERED = "evolution_triggered"
    SCOUT_DISCOVERY = "scout_discovery"


class TaskOrigin(FrameworkModel):
    type: TaskOriginType
    source: str
    reason: str


class TaskLinks(FrameworkModel):
    parent_task: str | None = None
    blocks: list[str] = []
    blocked_by: list[str] = []
    related_evolution: str | None = None


class TaskReview(FrameworkModel):
    """Mandatory review record (Axiom A7)."""

    reviewer: str
    reviewer_role: str
    findings: list[str]
    verdict: Literal["pass", "pass_with_notes", "fail"]
    reviewer_confidence: float = Field(ge=0.0, le=1.0)


class TaskMetrics(FrameworkModel):
    """Resource consumption metrics for a task."""

    tokens_used: int = 0
    tokens_cached: int = 0
    agents_spawned: int = 0
    time_elapsed: str | None = None
    review_rounds: int = 0
    budget_allocated: int = 0
    budget_utilization: float = 0.0
    tools_loaded: int = 0
    tools_per_step_avg: float = 0.0
    context_pressure_max: float = 0.0
    monetary_cost: float = 0.0


class TaskTimelineEntry(FrameworkModel):
    """A single event in a task's timeline."""

    time: datetime
    event: str
    actor: str
    detail: str


class TopologyAssignment(FrameworkModel):
    role: str
    agent_id: str
    model: ModelPreference


class TaskTopology(FrameworkModel):
    """Selected topology for task execution."""

    pattern: str  # solo, pipeline, parallel_swarm, hierarchical_team, hybrid, debate
    analysis: dict
    agents: list[TopologyAssignment]


class Task(IdentifiableModel):
    """Complete task record — the central data structure."""

    status: TaskStatus
    title: str
    description: str
    origin: TaskOrigin
    rationale: str
    priority: Literal["low", "medium", "high", "critical"]
    links: TaskLinks = TaskLinks()
    mandate: TaskMandate = TaskMandate()
    topology: TaskTopology | None = None
    timeline: list[TaskTimelineEntry] = []
    review: TaskReview | None = None
    artifacts: dict = {}
    metrics: TaskMetrics = TaskMetrics()


# Valid state transitions — enforced by TaskLifecycle engine
VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.INTAKE: {TaskStatus.ANALYSIS},
    TaskStatus.ANALYSIS: {TaskStatus.PLANNING},
    TaskStatus.PLANNING: {TaskStatus.EXECUTING, TaskStatus.PARKED},
    TaskStatus.EXECUTING: {TaskStatus.REVIEWING, TaskStatus.PARKED},
    TaskStatus.PARKED: {TaskStatus.PLANNING, TaskStatus.EXECUTING},
    TaskStatus.REVIEWING: {TaskStatus.VERDICT},
    TaskStatus.VERDICT: {TaskStatus.COMPLETE, TaskStatus.PLANNING},  # fail → re-plan
    TaskStatus.COMPLETE: {TaskStatus.ARCHIVED},
    TaskStatus.ARCHIVED: set(),  # terminal state
}
