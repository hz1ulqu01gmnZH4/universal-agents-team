"""Team coordination models for multi-agent orchestration.
Spec reference: Section 5.2 (Topology Patterns), Section 9 (Coordination Layer)."""
from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .agent import AgentStatus
from .base import FrameworkModel, IdentifiableModel


class TopologyPattern(StrEnum):
    """Available topology patterns. Phase 1 implements first 3."""

    SOLO = "solo"
    PARALLEL_SWARM = "parallel_swarm"
    HIERARCHICAL_TEAM = "hierarchical_team"
    # Phase 2+:
    # PIPELINE = "pipeline"
    # HYBRID = "hybrid"
    # DEBATE = "debate"


class CoordinationMode(StrEnum):
    """How agents coordinate within a topology."""

    NONE = "none"  # Solo agent, no coordination
    STIGMERGIC = "stigmergic"  # Shared files, pressure fields (parallel swarm)
    EXPLICIT = "explicit"  # Direct messaging (hierarchical team)


class TeamStatus(StrEnum):
    """Team lifecycle states."""

    FORMING = "forming"  # Agents being spawned
    ACTIVE = "active"  # All agents working
    REVIEWING = "reviewing"  # Workers done, reviewer active
    COMPLETING = "completing"  # Synthesizing results
    DISSOLVED = "dissolved"  # Team work complete


class SubTaskStatus(StrEnum):
    """SubTask lifecycle states."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    UNASSIGNED = "unassigned"


class TeamMember(FrameworkModel):
    """A member of an agent team."""

    agent_id: str
    role: str
    status: AgentStatus  # Validated enum, not bare str
    assigned_subtask: str | None = None


class Team(IdentifiableModel):
    """An active agent team working on a task."""

    task_id: str
    pattern: TopologyPattern
    coordination: CoordinationMode
    status: TeamStatus
    orchestrator_id: str | None = None  # Agent ID of orchestrator (hierarchical)
    reviewer_id: str | None = None  # Agent ID assigned reviewer
    members: list[TeamMember] = []
    max_agents: int = Field(ge=1, le=10)
    subtask_assignments: dict[str, str] = {}  # subtask_id -> agent_id


class SubTask(IdentifiableModel):
    """A decomposed subtask within a team."""

    parent_task_id: str
    title: str
    description: str
    assigned_to: str | None = None  # agent_id
    status: SubTaskStatus = SubTaskStatus.PENDING
    result: str | None = None
    token_usage: int = 0
    output_text: str | None = None  # FM-116: Captured agent output for diversity measurement
