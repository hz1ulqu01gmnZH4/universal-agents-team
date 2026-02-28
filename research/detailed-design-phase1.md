# Universal Agents Framework — Phase 1 Detailed Design

**Version:** 0.1.0
**Date:** 2026-02-28
**Source:** framework-design-unified-v1.1.md, detailed-design-phase0.md, multi-agent-orchestration-literature-review.md (~65 papers)
**Status:** Implementation-ready — concrete enough to code from directly
**Scope:** Phase 1 "Multi-Agent Orchestration Foundation" — topology routing, agent spawning, review mandate, task parking/resumption
**Prerequisite:** Phase 0 fully implemented (46 source files, 146 tests passing)

---

## Table of Contents

1. [Phase 1 Architecture Overview](#part-1-phase-1-architecture-overview)
2. [New & Modified Data Models](#part-2-new--modified-data-models)
3. [Topology Router Upgrade](#part-3-topology-router-upgrade)
4. [Agent Spawning & Team Management](#part-4-agent-spawning--team-management)
5. [Review Mandate Engine](#part-5-review-mandate-engine)
6. [Task Parking & Resumption](#part-6-task-parking--resumption)
7. [Orchestrator Agent](#part-7-orchestrator-agent)
8. [Claude Code Integration Patterns](#part-8-claude-code-integration-patterns)
9. [CLAUDE.md Phase 1 Updates](#part-9-claudemd-phase-1-updates)
10. [Implementation Sequence](#part-10-implementation-sequence)
11. [Verification Checklist](#part-11-verification-checklist)
12. [Edge Cases, Failure Modes & Mitigations](#part-12-edge-cases-failure-modes--mitigations)

---

## Part 1: Phase 1 Architecture Overview

### 1.1 What Phase 1 Adds

Phase 0 built the **scaffolding**: data models, state management, basic CLI tools, audit logging, prompt composition.

Phase 1 builds the **multi-agent orchestration foundation**: the ability for the framework to analyze tasks, select topologies, spawn agent teams, enforce reviews, and manage concurrent work.

```
Phase 0 (solo agent, manual)     Phase 1 (orchestrated teams)
───────────────────────────      ──────────────────────────────
Human → Task → Solo Agent       Human → Task → Orchestrator
         ↓                                   ↓
      Execute                         Analyze (6 dimensions)
         ↓                                   ↓
      Complete                      Route (select topology)
                                            ↓
                                     Spawn team (resource-checked)
                                            ↓
                                     Workers execute (parallel/sequential)
                                            ↓
                                     Reviewer validates (mandatory)
                                            ↓
                                     Verdict → Complete/Re-plan
```

### 1.2 Key Design Principles from Literature

1. **Topology is a first-class optimization target** — AdaptOrch (2026) proves 12-23% improvement from topology alone
2. **Separate planning from validation** — ALAS (2025) shows non-circular validation + localized repair = 83.7% success, 60% token reduction
3. **Functional complementarity beats team size** — 3-agent Coder-Executor-Critic > larger teams (Tian & Zhang, 2024)
4. **Information-flow orchestration** — CORAL (2026) replaces predefined workflows with dynamic coordination
5. **Memory isolation prevents contamination** — AgentSys (2026) isolates worker contexts from external data

### 1.3 Phase 1 Scope (4 Capabilities)

From the 12-phase meta bootstrap sequence (Section 25, unified spec):

```
PHASE 1: Foundation (Human + orchestrator agent)
  1. Implement topology router (start with 3 patterns: solo, parallel, hierarchical)
  2. Implement basic review mandate (every task reviewed)
  3. Implement agent spawning from role compositions
  4. Implement task parking/resumption
  VALIDATION: run 5 real tasks, verify audit trail is complete
```

### 1.4 What Phase 1 Does NOT Include

- Evolution engine (Phase 2.5+)
- Diversity metrics / SRD (Phase 2)
- Creativity engine (Phase 3)
- Self-awareness / meta-analysis (Phase 2)
- Dynamic tool loading (Phase 1.5)
- Cost router / FrugalGPT cascade (Phase 2+)
- Pipeline, hybrid, or debate topologies (Phase 2+)
- Rate limit mirror implementation (Phase 1.5)
- Chars-per-token recalibration (Phase 1.5)

### 1.5 Files Modified (Phase 0 → Phase 1)

```
MODIFIED (upgrade existing Phase 0 code):
  src/uagents/engine/topology_router.py      — LLM-judgment analysis, 3-pattern routing
  src/uagents/engine/agent_spawner.py        — full spawn pipeline, team management
  src/uagents/engine/task_lifecycle.py       — review integration, enhanced parking
  src/uagents/engine/prompt_composer.py      — orchestrator prompt generation
  src/uagents/claude_md/generator.py         — Phase 1 CLAUDE.md content
  src/uagents/cli/bootstrap.py               — Phase 1 scaffold additions
  src/uagents/cli/task_manager.py            — review commands
  src/uagents/cli/spawn_agent.py             — team-aware spawning
  src/uagents/models/task.py                 — review fields enforcement
  src/uagents/models/agent.py                — team tracking fields

NEW FILES:
  src/uagents/engine/review_engine.py        — review mandate enforcement
  src/uagents/engine/team_manager.py         — team lifecycle, messaging
  src/uagents/engine/orchestrator.py         — orchestrator decision logic
  src/uagents/models/team.py                 — team data models
  src/uagents/models/message.py              — inter-agent message models
  src/uagents/cli/team_manager.py            — team CLI commands
  tools/team-manager.sh                      — team shell wrapper

  tests/test_engine/test_topology_router_phase1.py
  tests/test_engine/test_review_engine.py
  tests/test_engine/test_team_manager.py
  tests/test_engine/test_orchestrator.py
  tests/test_engine/test_agent_spawner_phase1.py
  tests/test_models/test_team.py
  tests/test_models/test_message.py
  tests/test_integration/test_full_lifecycle.py
```

Estimated: ~15 new/modified source files, ~8 new test files, ~120+ new tests

---

## Part 2: New & Modified Data Models

### 2.1 Team Models (`models/team.py`) — NEW

```python
"""Team coordination models for multi-agent orchestration.
Spec reference: Section 5.2 (Topology Patterns), Section 9 (Coordination Layer)."""
from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .base import FrameworkModel, IdentifiableModel, TimestampedModel


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
    NONE = "none"                # Solo agent, no coordination
    STIGMERGIC = "stigmergic"   # Shared files, pressure fields (parallel swarm)
    EXPLICIT = "explicit"        # Direct messaging (hierarchical team)


class TeamStatus(StrEnum):
    """Team lifecycle states."""
    FORMING = "forming"          # Agents being spawned
    ACTIVE = "active"            # All agents working
    REVIEWING = "reviewing"      # Workers done, reviewer active
    COMPLETING = "completing"    # Synthesizing results
    DISSOLVED = "dissolved"      # Team work complete


class TeamMember(FrameworkModel):
    """A member of an agent team."""
    agent_id: str
    role: str
    status: str  # References AgentStatus value
    assigned_subtask: str | None = None


class Team(IdentifiableModel):
    """An active agent team working on a task."""
    task_id: str
    pattern: TopologyPattern
    coordination: CoordinationMode
    status: TeamStatus
    orchestrator_id: str | None = None   # Agent ID of orchestrator (hierarchical)
    reviewer_id: str | None = None       # Agent ID assigned reviewer
    members: list[TeamMember] = []
    max_agents: int = Field(ge=1, le=10)
    subtask_assignments: dict[str, str] = {}  # subtask_id -> agent_id


class SubTask(IdentifiableModel):
    """A decomposed subtask within a team."""
    parent_task_id: str
    title: str
    description: str
    assigned_to: str | None = None  # agent_id
    status: str = "pending"  # pending, executing, completed, failed
    result: str | None = None
    token_usage: int = 0
```

### 2.2 Message Models (`models/message.py`) — NEW

```python
"""Inter-agent message models.
Spec reference: Section 9 (Coordination Layer)."""
from __future__ import annotations

from enum import StrEnum

from .base import FrameworkModel, TimestampedModel


class MessageType(StrEnum):
    """Types of inter-agent messages (Section 9)."""
    TASK_ASSIGNMENT = "task_assignment"        # Orchestrator -> Worker
    STATUS_UPDATE = "status_update"            # Worker -> Orchestrator
    REVIEW_REQUEST = "review_request"          # Worker -> Reviewer
    REVIEW_RESULT = "review_result"            # Reviewer -> Orchestrator
    ESCALATION = "escalation"                  # Any -> Orchestrator
    SUBTASK_RESULT = "subtask_result"          # Worker -> Orchestrator
    PARK_REQUEST = "park_request"              # Any -> Orchestrator
    COORDINATION_ACK = "coordination_ack"      # Any -> Any


class AgentMessage(TimestampedModel):
    """A message between agents, logged for audit."""
    message_type: MessageType
    sender_id: str
    recipient_id: str
    content: str
    task_id: str | None = None
    requires_ack: bool = False
    ack_received: bool = False
```

### 2.3 Modified Task Model (`models/task.py`)

Add review enforcement fields:

```python
# Add to existing Task class:
class Task(IdentifiableModel):
    # ... existing fields ...
    team_id: str | None = None           # NEW: Team managing this task
    review_required: bool = True          # NEW: Axiom A7 enforcement (always True)
    subtasks: list[str] = []             # NEW: SubTask IDs for decomposed work
```

### 2.4 Modified Agent Model (`models/agent.py`)

Add team-awareness:

```python
class AgentRegistryEntry(IdentifiableModel):
    # ... existing fields ...
    team_name: str | None = None    # EXISTING but unused → now populated
    heartbeat_at: datetime | None = None  # NEW: last activity timestamp
    subtask_id: str | None = None         # NEW: assigned subtask within team
```

### 2.5 Topology Analysis Enhancement

The existing `TaskAnalysis` and `RoutingResult` models in `topology_router.py` are sufficient.
Add one new model for LLM analysis context:

```python
class AnalysisContext(FrameworkModel):
    """Context provided to LLM for task analysis."""
    task_title: str
    task_description: str
    available_roles: list[str]
    active_agent_count: int
    resource_headroom: float  # 0.0-1.0
    similar_past_tasks: list[dict] = []  # From task history
```

---

## Part 3: Topology Router Upgrade

### 3.1 Current State (Phase 0)

The Phase 0 `TopologyRouter` returns hardcoded defaults:
- `analyze()` → always PARTIALLY_DECOMPOSABLE / LOOSELY_COUPLED / MIXED / MEDIUM / MEDIUM / MODERATE
- `route()` → only selects solo or hierarchical_team based on simple if/else

### 3.2 Phase 1 Upgrade: Heuristic-Enhanced Analysis

Phase 1 replaces the hardcoded analysis with **structured heuristic analysis** (not full LLM judgment — that comes in Phase 2 with MAP-Elites). The analysis uses task description keywords, size estimation, and available resource state.

```python
class TopologyRouter:
    """Task analysis and topology routing.

    Phase 0: Hardcoded defaults.
    Phase 1: Heuristic-enhanced analysis with keyword extraction, resource awareness.
    Phase 2+: LLM judgment + MAP-Elites archive lookup.
    """

    def __init__(self, yaml_store: YamlStore, resource_tracker: ResourceTracker):
        self.yaml_store = yaml_store
        self.resource_tracker = resource_tracker

    def analyze(self, task: Task) -> TaskAnalysis:
        """Analyze task along 6 dimensions using structured heuristics.

        Phase 1 heuristic strategy:
        - Decomposability: keyword-based (list/multiple/each → decomposable)
        - Interdependency: keyword-based (depends/after/then → coupled)
        - Exploration vs Execution: keyword-based (research/explore vs implement/fix)
        - Quality Criticality: keyword-based (critical/safety/production vs quick/draft)
        - Scale: description length + keyword count heuristic
        - Novelty: check task history for similar titles (Jaccard similarity)
        """
        text = f"{task.title} {task.description}".lower()

        # Decomposability
        decomp_keywords = {"parallel", "independent", "each", "multiple", "all", "every", "batch"}
        mono_keywords = {"single", "one", "specific", "this", "the"}
        decomp_score = sum(1 for k in decomp_keywords if k in text)
        mono_score = sum(1 for k in mono_keywords if k in text)
        if decomp_score >= 2:
            decomposability = Decomposability.FULLY_DECOMPOSABLE
        elif decomp_score >= 1:
            decomposability = Decomposability.PARTIALLY_DECOMPOSABLE
        else:
            decomposability = Decomposability.MONOLITHIC

        # Interdependency
        coupled_keywords = {"depends", "after", "then", "requires", "blocking", "sequential"}
        independent_keywords = {"independent", "parallel", "concurrent", "separate"}
        coupled_score = sum(1 for k in coupled_keywords if k in text)
        indep_score = sum(1 for k in independent_keywords if k in text)
        if coupled_score >= 2:
            interdependency = Interdependency.TIGHTLY_COUPLED
        elif indep_score >= 1:
            interdependency = Interdependency.INDEPENDENT
        else:
            interdependency = Interdependency.LOOSELY_COUPLED

        # Exploration vs Execution
        explore_keywords = {"research", "explore", "investigate", "analyze", "discover", "design", "plan"}
        execute_keywords = {"implement", "fix", "build", "deploy", "create", "write", "code"}
        explore_score = sum(1 for k in explore_keywords if k in text)
        execute_score = sum(1 for k in execute_keywords if k in text)
        if explore_score > execute_score + 1:
            expl_exec = ExplorationExecution.PURE_EXPLORATION
        elif execute_score > explore_score + 1:
            expl_exec = ExplorationExecution.PURE_EXECUTION
        else:
            expl_exec = ExplorationExecution.MIXED

        # Quality Criticality
        critical_keywords = {"critical", "safety", "production", "security", "must not fail", "correctness"}
        speed_keywords = {"quick", "draft", "prototype", "rough", "fast", "hack"}
        crit_score = sum(1 for k in critical_keywords if k in text)
        speed_score = sum(1 for k in speed_keywords if k in text)
        if crit_score >= 2:
            quality = QualityCriticality.CRITICAL
        elif crit_score >= 1:
            quality = QualityCriticality.HIGH
        elif speed_score >= 1:
            quality = QualityCriticality.LOW
        else:
            quality = QualityCriticality.MEDIUM

        # Scale (based on description length and complexity indicators)
        word_count = len(text.split())
        if word_count > 200 or "large" in text or "major" in text or "comprehensive" in text:
            scale = Scale.LARGE
        elif word_count > 50 or decomp_score >= 1:
            scale = Scale.MEDIUM
        else:
            scale = Scale.SMALL

        # Novelty (check recent task history)
        novelty = self._assess_novelty(task.title)

        return TaskAnalysis(
            decomposability=decomposability,
            interdependency=interdependency,
            exploration_vs_execution=expl_exec,
            quality_criticality=quality,
            scale=scale,
            novelty=novelty,
        )

    def _assess_novelty(self, title: str) -> Novelty:
        """Check task history for similar tasks using word overlap."""
        title_words = set(title.lower().split())
        try:
            completed_dir = "state/tasks/completed"
            completed_tasks = self.yaml_store.list_dir(completed_dir)
        except (NotADirectoryError, FileNotFoundError):
            return Novelty.NOVEL  # No history → novel

        max_similarity = 0.0
        for task_file in completed_tasks[:50]:  # Check last 50 completed
            try:
                data = self.yaml_store.read_raw(f"{completed_dir}/{task_file}")
                past_title = data.get("title", "")
                past_words = set(past_title.lower().split())
                if title_words and past_words:
                    intersection = title_words & past_words
                    union = title_words | past_words
                    similarity = len(intersection) / len(union)  # Jaccard
                    max_similarity = max(max_similarity, similarity)
            except Exception:
                continue

        if max_similarity > 0.7:
            return Novelty.ROUTINE
        elif max_similarity > 0.4:
            return Novelty.MODERATE
        else:
            return Novelty.NOVEL

    def route(self, analysis: TaskAnalysis) -> RoutingResult:
        """Select topology pattern based on 6-dimension analysis.

        Phase 1 implements 3 patterns:
        - solo: monolithic + small + routine
        - parallel_swarm: fully_decomposable + independent
        - hierarchical_team: everything else (default)

        All topologies include a mandatory reviewer agent.
        """
        # Check available resources
        can_spawn, _ = self.resource_tracker.can_spawn_agent()
        metrics = self.resource_tracker.check_compute()

        # Solo: simple, small, monolithic tasks
        if (analysis.decomposability == Decomposability.MONOLITHIC
                and analysis.scale == Scale.SMALL
                and analysis.novelty in (Novelty.ROUTINE, Novelty.MODERATE)):
            return RoutingResult(
                pattern="solo",
                agent_count=2,  # worker + reviewer (A7: review always mandatory)
                role_assignments=[
                    {"role": "implementer", "purpose": "execute task"},
                    {"role": "reviewer", "purpose": "mandatory review"},
                ],
                inject_scout=False,
                rationale=f"Monolithic + small + {analysis.novelty.value} → solo with mandatory review",
            )

        # Parallel swarm: decomposable + independent subtasks
        if (analysis.decomposability == Decomposability.FULLY_DECOMPOSABLE
                and analysis.interdependency == Interdependency.INDEPENDENT):
            # Scale agent count based on resources
            base_count = 3 if analysis.scale == Scale.SMALL else 4
            if analysis.scale == Scale.LARGE:
                base_count = 5
            # Cap by resources: at most (max_agents - active_agents - 1 for reviewer)
            agent_cap = max(2, metrics.active_agents + base_count + 1)
            actual_count = min(base_count, 6)  # Hard cap at 6 workers

            roles = [{"role": "orchestrator", "purpose": "decompose and aggregate"}]
            for i in range(actual_count):
                roles.append({"role": "implementer", "purpose": f"parallel worker {i+1}"})
            roles.append({"role": "reviewer", "purpose": "mandatory review"})

            return RoutingResult(
                pattern="parallel_swarm",
                agent_count=len(roles),
                role_assignments=roles,
                inject_scout=analysis.novelty == Novelty.NOVEL,
                rationale=f"Fully decomposable + independent → parallel swarm ({actual_count} workers)",
            )

        # Hierarchical team: default for complex/coupled tasks
        team_size = 3  # orchestrator + worker + reviewer
        if analysis.scale == Scale.LARGE or analysis.quality_criticality in (
            QualityCriticality.HIGH, QualityCriticality.CRITICAL
        ):
            team_size = 4  # orchestrator + 2 workers + reviewer
        if analysis.scale == Scale.LARGE and analysis.quality_criticality == QualityCriticality.CRITICAL:
            team_size = 5  # orchestrator + 3 workers + reviewer

        roles = [{"role": "orchestrator", "purpose": "strategic coordination"}]
        worker_count = team_size - 2  # minus orchestrator and reviewer
        for i in range(worker_count):
            role_name = self._select_worker_role(analysis, i)
            roles.append({"role": role_name, "purpose": f"worker {i+1}"})
        roles.append({"role": "reviewer", "purpose": "mandatory review"})

        return RoutingResult(
            pattern="hierarchical_team",
            agent_count=len(roles),
            role_assignments=roles,
            inject_scout=analysis.novelty == Novelty.NOVEL,
            rationale=f"Complex/coupled task → hierarchical team ({team_size} agents)",
        )

    def _select_worker_role(self, analysis: TaskAnalysis, index: int) -> str:
        """Select appropriate worker role based on task analysis."""
        if analysis.exploration_vs_execution == ExplorationExecution.PURE_EXPLORATION:
            return "researcher" if index == 0 else "scout"
        elif analysis.exploration_vs_execution == ExplorationExecution.PURE_EXECUTION:
            return "implementer"
        else:
            # Mixed: first worker implements, second researches
            return "implementer" if index == 0 else "researcher"
```

### 3.3 Pattern Selection Rules Summary

| Analysis | Pattern | Agents | Rationale |
|----------|---------|--------|-----------|
| monolithic + small + routine/moderate | solo | 2 (worker + reviewer) | Simple tasks don't need decomposition |
| fully_decomposable + independent | parallel_swarm | 4-7 (orchestrator + N workers + reviewer) | Independent subtasks benefit from parallelism |
| everything else | hierarchical_team | 3-5 (orchestrator + N workers + reviewer) | Default: structured delegation with oversight |

### 3.4 Routing Decision Logging

Every routing decision is logged to `logs/decisions/`:

```python
from ..audit.logger import AuditLogger
from ..models.audit import DecisionLogEntry

def _log_routing_decision(
    self, task: Task, analysis: TaskAnalysis, result: RoutingResult
) -> None:
    """Log topology routing decision for audit trail."""
    entry = DecisionLogEntry(
        id=generate_id("dec"),
        timestamp=datetime.utcnow(),
        stream=LogStream.DECISIONS,
        decision_type="topology_routing",
        inputs={"task_id": task.id, "analysis": analysis.model_dump()},
        output=result.model_dump(),
        rationale=result.rationale,
        actor="topology_router",
    )
    self.audit_logger.log_decision(entry)
```

---

## Part 4: Agent Spawning & Team Management

### 4.1 Team Manager (`engine/team_manager.py`) — NEW

The team manager handles the full lifecycle of agent teams:

```python
"""Team lifecycle management for multi-agent orchestration.
Spec reference: Section 5.2 (Topology Patterns), Section 9 (Coordination Layer)."""
from __future__ import annotations

from datetime import datetime

from ..models.agent import AgentRegistryEntry, AgentStatus
from ..models.base import generate_id
from ..models.capability import CapabilityAtom, ModelPreference
from ..models.team import (
    CoordinationMode, SubTask, Team, TeamMember, TeamStatus, TopologyPattern,
)
from ..models.task import Task
from ..models.voice import VoiceAtom
from ..state.yaml_store import YamlStore
from .agent_spawner import AgentSpawner


class TeamCreationError(RuntimeError):
    """Raised when team cannot be formed."""


class TeamManager:
    """Manages agent team lifecycle: creation, monitoring, dissolution.

    Team lifecycle:
    1. FORMING  — spawning agents, assigning roles
    2. ACTIVE   — agents working on subtasks
    3. REVIEWING — workers complete, reviewer validates
    4. COMPLETING — synthesizing results
    5. DISSOLVED — team work finished, agents despawned

    Invariants:
    - Every team has exactly one reviewer (Axiom A7)
    - Agent count never exceeds resource limits
    - All team state persisted to YAML for crash recovery
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        agent_spawner: AgentSpawner,
        capabilities: dict[str, CapabilityAtom],
        voice_atoms: dict[str, VoiceAtom],
    ):
        self.yaml_store = yaml_store
        self.agent_spawner = agent_spawner
        self.capabilities = capabilities
        self.voice_atoms = voice_atoms

    def create_team(
        self,
        task: Task,
        routing_result: RoutingResult,
        domain_config: DomainConfig,
    ) -> Team:
        """Create a team from a routing result.

        Steps:
        1. Create team record with FORMING status
        2. Spawn each agent in role_assignments
        3. Register agents as team members
        4. Transition team to ACTIVE
        5. Log team creation to audit trail

        Raises TeamCreationError if any spawn fails.
        """
        team_id = generate_id("team")

        # Determine coordination mode from topology pattern
        pattern = TopologyPattern(routing_result.pattern)
        coordination = self._pattern_to_coordination(pattern)

        team = Team(
            id=team_id,
            created_at=datetime.utcnow(),
            task_id=task.id,
            pattern=pattern,
            coordination=coordination,
            status=TeamStatus.FORMING,
            max_agents=routing_result.agent_count,
        )

        # Persist team record
        team_dir = f"state/teams/{team_id}"
        self.yaml_store.write(f"{team_dir}/team.yaml", team)

        # Spawn each agent
        spawned_members: list[TeamMember] = []
        for assignment in routing_result.role_assignments:
            role_name = assignment["role"]
            try:
                role = self._load_role(role_name)
                agent_entry, composed = self.agent_spawner.spawn(
                    role=role,
                    task=task,
                    domain_config=domain_config,
                    capabilities=self.capabilities,
                    voice_atoms=self.voice_atoms,
                )
                agent_entry.team_name = team_id
                member = TeamMember(
                    agent_id=agent_entry.id,
                    role=role_name,
                    status=AgentStatus.ACTIVE,
                )
                spawned_members.append(member)

                # Track orchestrator and reviewer
                if role_name == "orchestrator":
                    team.orchestrator_id = agent_entry.id
                elif role_name == "reviewer":
                    team.reviewer_id = agent_entry.id

            except Exception as e:
                # If any spawn fails, despawn already-spawned agents
                for m in spawned_members:
                    self.agent_spawner.despawn(m.agent_id, f"Team creation failed: {e}")
                raise TeamCreationError(
                    f"Failed to spawn {role_name} for team {team_id}: {e}"
                ) from e

        team.members = spawned_members
        team.status = TeamStatus.ACTIVE

        # Persist updated team state
        self.yaml_store.write(f"{team_dir}/team.yaml", team)
        return team

    def decompose_task(
        self, team: Team, task: Task, subtask_descriptions: list[dict]
    ) -> list[SubTask]:
        """Create subtasks and assign to team members.

        Args:
            team: The active team
            task: The parent task
            subtask_descriptions: List of {"title": str, "description": str} dicts

        Returns:
            List of created SubTask objects
        """
        subtasks: list[SubTask] = []
        # Get available workers (not orchestrator, not reviewer)
        workers = [
            m for m in team.members
            if m.role not in ("orchestrator", "reviewer")
        ]

        for i, desc in enumerate(subtask_descriptions):
            subtask_id = generate_id("subtask")
            # Round-robin assignment to workers
            worker = workers[i % len(workers)] if workers else None

            subtask = SubTask(
                id=subtask_id,
                created_at=datetime.utcnow(),
                parent_task_id=task.id,
                title=desc["title"],
                description=desc["description"],
                assigned_to=worker.agent_id if worker else None,
                status="pending" if worker else "unassigned",
            )
            subtasks.append(subtask)

            if worker:
                team.subtask_assignments[subtask_id] = worker.agent_id

        # Persist subtasks
        team_dir = f"state/teams/{team.id}"
        for st in subtasks:
            self.yaml_store.write(f"{team_dir}/subtasks/{st.id}.yaml", st)

        return subtasks

    def transition_team(self, team_id: str, new_status: TeamStatus) -> Team:
        """Transition team to a new status."""
        team = self._load_team(team_id)
        team.status = new_status
        team.updated_at = datetime.utcnow()
        self.yaml_store.write(f"state/teams/{team_id}/team.yaml", team)
        return team

    def dissolve_team(self, team_id: str, reason: str) -> None:
        """Dissolve a team, despawning all agents.

        Steps:
        1. Despawn all active agents
        2. Set team status to DISSOLVED
        3. Log dissolution
        """
        team = self._load_team(team_id)
        for member in team.members:
            if member.status != AgentStatus.DESPAWNED:
                self.agent_spawner.despawn(member.agent_id, reason)
                member.status = AgentStatus.DESPAWNED

        team.status = TeamStatus.DISSOLVED
        self.yaml_store.write(f"state/teams/{team_id}/team.yaml", team)

    def get_active_teams(self) -> list[Team]:
        """List all non-dissolved teams."""
        teams = []
        try:
            team_dirs = self.yaml_store.list_dir("state/teams")
        except (NotADirectoryError, FileNotFoundError):
            return teams
        for team_dir in team_dirs:
            try:
                data = self.yaml_store.read_raw(f"state/teams/{team_dir}/team.yaml")
                if data.get("status") != TeamStatus.DISSOLVED:
                    teams.append(Team(**data))
            except Exception:
                continue
        return teams

    def _load_team(self, team_id: str) -> Team:
        """Load team from YAML store."""
        data = self.yaml_store.read_raw(f"state/teams/{team_id}/team.yaml")
        return Team(**data)

    def _load_role(self, role_name: str) -> RoleComposition:
        """Load a role composition from YAML."""
        from ..models.role import RoleComposition
        data = self.yaml_store.read_raw(f"roles/compositions/{role_name}.yaml")
        role_data = data.get("role", data)
        return RoleComposition(**role_data)

    def _pattern_to_coordination(self, pattern: TopologyPattern) -> CoordinationMode:
        """Map topology pattern to coordination mode."""
        mapping = {
            TopologyPattern.SOLO: CoordinationMode.NONE,
            TopologyPattern.PARALLEL_SWARM: CoordinationMode.STIGMERGIC,
            TopologyPattern.HIERARCHICAL_TEAM: CoordinationMode.EXPLICIT,
        }
        return mapping.get(pattern, CoordinationMode.EXPLICIT)
```

### 4.2 Agent Spawner Upgrades

Modifications to existing `agent_spawner.py`:

```python
# Add to AgentSpawner class:

def spawn_for_team(
    self,
    role: RoleComposition,
    task: Task,
    domain_config: DomainConfig,
    capabilities: dict[str, CapabilityAtom],
    voice_atoms: dict[str, VoiceAtom],
    team_id: str,
    subtask: SubTask | None = None,
) -> tuple[AgentRegistryEntry, ComposedPrompt]:
    """Spawn an agent as part of a team.

    Extends base spawn() with:
    - team_name populated on agent entry
    - subtask assignment if provided
    - heartbeat timestamp initialized
    """
    entry, composed = self.spawn(role, task, domain_config, capabilities, voice_atoms)
    entry.team_name = team_id
    entry.heartbeat_at = datetime.utcnow()
    if subtask:
        entry.subtask_id = subtask.id
        entry.current_task = f"{task.id}:{subtask.id}"

    # Update persisted entry
    agent_dir = f"state/agents/{entry.id}"
    self.yaml_store.write(f"{agent_dir}/status.yaml", entry)
    return entry, composed

def update_heartbeat(self, agent_id: str) -> None:
    """Update agent's heartbeat timestamp."""
    agent_dir = f"state/agents/{agent_id}"
    try:
        data = self.yaml_store.read_raw(f"{agent_dir}/status.yaml")
        data["heartbeat_at"] = datetime.utcnow().isoformat()
        self.yaml_store.write_raw(f"{agent_dir}/status.yaml", data)
    except FileNotFoundError:
        pass  # Agent already despawned

def check_agent_health(self, agent_id: str, timeout_minutes: int = 10) -> bool:
    """Check if agent is responsive (heartbeat within timeout)."""
    agent_dir = f"state/agents/{agent_id}"
    try:
        data = self.yaml_store.read_raw(f"{agent_dir}/status.yaml")
        if data.get("status") == AgentStatus.DESPAWNED:
            return False
        heartbeat = data.get("heartbeat_at")
        if not heartbeat:
            return True  # No heartbeat tracking yet
        last_beat = datetime.fromisoformat(heartbeat)
        elapsed = (datetime.utcnow() - last_beat).total_seconds() / 60
        return elapsed < timeout_minutes
    except FileNotFoundError:
        return False
```

### 4.3 Spawn Pipeline (Full 15-Step)

The complete spawn pipeline for Phase 1:

```
spawn_agent(role_name, task, team_id) ->
  1. CHECK compute_monitor: CPU < 80%, memory < 80%, disk < 90%
  2. CHECK agent_cap: active_agents < max_concurrent (Phase 0: 10)
  3. IF any check fails: raise ResourceConstrainedError
  4. Load roles/compositions/{role_name}.yaml
  5. Load roles/capabilities.yaml for each listed capability
  6. Validate all capability references exist (G2)
  7. Load roles/voice.yaml for each voice atom in role's voice profile
  8. Compose prompt via PromptComposer.compose():
     - Ring 0: Constitution axioms (immutable, never compressed)
     - Ring 1: Domain context (domain.yaml, charter, mandate)
     - Ring 2: Role instructions (capabilities + voice + behavioral + forbidden)
     - Ring 3: Task context (title, description, subtask, artifacts)
  9. Apply voice compression cascade based on context pressure
  10. Apply edge placement (Ring 0 first, Ring 3 last, middle sorted by priority)
  11. Estimate token cost from composed prompt
  12. Generate agent ID via generate_id("agent")
  13. Create AgentRegistryEntry with team_name, subtask_id
  14. Persist to state/agents/{agent_id}/status.yaml
  15. Return (AgentRegistryEntry, ComposedPrompt) — caller invokes Claude Code Task tool
```

### 4.4 Directory Structure Additions

Phase 1 adds these directories to the scaffold:

```
state/
├── teams/                        # NEW: Team state
│   └── {team_id}/
│       ├── team.yaml             # Team record
│       └── subtasks/             # Decomposed subtasks
│           └── {subtask_id}.yaml
├── coordination/                 # NEW: Stigmergic coordination
│   └── pressure_fields/          # Shared state for parallel swarms
│       └── {field_name}.yaml
```

---

## Part 5: Review Mandate Engine

### 5.1 Design Rationale

Axiom A7 (from CONSTITUTION.md): "Mandatory peer review — no self-approval."

Literature support:
- ALAS (2025): Separate planning from non-circular validation
- Tian & Zhang (2024): Coder-Executor-Critic is the minimal effective team
- MAST (2025): Task verification failures are the most common multi-agent failure mode

### 5.2 Review Engine (`engine/review_engine.py`) — NEW

```python
"""Review mandate enforcement engine.
Spec reference: Section 6.2 (Task Lifecycle), Axiom A7."""
from __future__ import annotations

from datetime import datetime

from ..models.audit import DecisionLogEntry, LogStream
from ..models.base import generate_id
from ..models.task import Task, TaskReview, TaskStatus
from ..state.yaml_store import YamlStore
from .task_lifecycle import TaskLifecycle


class ReviewViolationError(RuntimeError):
    """Raised when review mandate is violated."""


class ReviewEngine:
    """Enforces mandatory review for all tasks.

    Invariants (Axiom A7):
    - Every task MUST pass through REVIEWING before COMPLETE
    - Reviewer MUST NOT be the same agent that executed the task
    - Review MUST contain specific findings (no rubber-stamping)
    - Failed reviews send task back to PLANNING with feedback

    Review flow:
    1. Task reaches EXECUTING → REVIEWING transition
    2. ReviewEngine validates reviewer is different from executor
    3. Reviewer agent examines work artifacts
    4. Reviewer submits structured review (findings, verdict, confidence)
    5. If verdict == "fail": task → PLANNING with review feedback
    6. If verdict == "pass"/"pass_with_notes": task → VERDICT → COMPLETE
    """

    # Minimum findings required to prevent rubber-stamping
    MIN_FINDINGS = 1
    # Minimum reviewer confidence to accept
    MIN_CONFIDENCE = 0.3

    def __init__(self, yaml_store: YamlStore, task_lifecycle: TaskLifecycle):
        self.yaml_store = yaml_store
        self.task_lifecycle = task_lifecycle

    def validate_review_eligible(self, task: Task) -> None:
        """Check that task is ready for review."""
        if task.status != TaskStatus.REVIEWING.value:
            raise ReviewViolationError(
                f"Task {task.id} is in {task.status}, not REVIEWING"
            )

    def submit_review(
        self,
        task_id: str,
        reviewer_id: str,
        reviewer_role: str,
        findings: list[str],
        verdict: str,  # "pass", "pass_with_notes", "fail"
        confidence: float,
    ) -> Task:
        """Submit a review for a task.

        Validates review quality:
        - Must have at least MIN_FINDINGS findings
        - Confidence must be at least MIN_CONFIDENCE
        - Verdict must be one of: pass, pass_with_notes, fail

        Returns updated task after applying review.
        """
        # Validate verdict
        valid_verdicts = {"pass", "pass_with_notes", "fail"}
        if verdict not in valid_verdicts:
            raise ReviewViolationError(
                f"Invalid verdict '{verdict}'. Must be one of: {valid_verdicts}"
            )

        # Validate findings (prevent rubber-stamping)
        if len(findings) < self.MIN_FINDINGS:
            raise ReviewViolationError(
                f"Review must contain at least {self.MIN_FINDINGS} finding(s). "
                f"Got {len(findings)}. Rubber-stamp reviews are not allowed (A7)."
            )

        # Validate confidence
        if confidence < self.MIN_CONFIDENCE:
            raise ReviewViolationError(
                f"Reviewer confidence {confidence} below minimum {self.MIN_CONFIDENCE}. "
                f"If unsure, request more context rather than low-confidence approval."
            )

        # Validate reviewer is not the executor
        task = self.task_lifecycle._load_task(task_id)
        self.validate_review_eligible(task)
        self._validate_not_self_review(task, reviewer_id)

        # Record review
        review = TaskReview(
            reviewer=reviewer_id,
            reviewer_role=reviewer_role,
            findings=findings,
            verdict=verdict,
            reviewer_confidence=confidence,
        )
        task.review = review

        # Persist review to task
        self._persist_review(task)

        # Apply verdict
        if verdict == "fail":
            # Failed review: back to PLANNING with feedback
            feedback = "; ".join(findings)
            task = self.task_lifecycle.transition(
                task_id, TaskStatus.PLANNING, reviewer_id,
                f"Review FAILED: {feedback}"
            )
        else:
            # Passed: REVIEWING → VERDICT → COMPLETE
            task = self.task_lifecycle.transition(
                task_id, TaskStatus.VERDICT, reviewer_id,
                f"Review {verdict}: {'; '.join(findings[:3])}"
            )

        return task

    def get_review(self, task_id: str) -> TaskReview | None:
        """Get the review for a task, if any."""
        task = self.task_lifecycle._load_task(task_id)
        return task.review

    def _validate_not_self_review(self, task: Task, reviewer_id: str) -> None:
        """Ensure reviewer didn't also execute the task."""
        # Check timeline for who executed the task
        for entry in task.timeline:
            if (entry.to_status == TaskStatus.EXECUTING.value
                    and entry.actor == reviewer_id):
                raise ReviewViolationError(
                    f"Agent {reviewer_id} cannot review task {task.id} — "
                    f"they were the executor. Self-review violates Axiom A7."
                )

    def _persist_review(self, task: Task) -> None:
        """Persist review to task YAML file."""
        # Find task in active/parked/completed directory
        for subdir in ("active", "parked", "completed"):
            path = f"state/tasks/{subdir}/{task.id}.yaml"
            try:
                self.yaml_store.read_raw(path)
                # Found it — write updated task
                self.yaml_store.write(path, task)
                return
            except FileNotFoundError:
                continue
        raise FileNotFoundError(f"Task {task.id} not found in any task directory")
```

### 5.3 Review Prompt Template

The reviewer agent receives a structured prompt:

```python
REVIEWER_PROMPT_TEMPLATE = """## Review Mandate (Axiom A7)

You are reviewing task: {task_id} — "{task_title}"

### Requirements
{task_description}

### Artifacts to Review
{artifacts_summary}

### Review Checklist (mandatory)
1. **Correctness**: Does the output match the task requirements?
2. **Completeness**: Is anything missing from the deliverable?
3. **Consistency**: Does it align with existing framework state?
4. **Safety**: Does it violate any constitutional axiom?

### Instructions
- You MUST provide at least 1 specific finding
- You MUST NOT rubber-stamp — examine each artifact carefully
- You MUST NOT modify the artifacts — only report findings
- Report your verdict as: pass, pass_with_notes, or fail
- Report your confidence as a float 0.0-1.0

### Output Format
Submit your review using the framework review tool:
  uv run python -m uagents.cli.task_manager review {task_id} \\
    --reviewer {reviewer_id} \\
    --verdict <pass|pass_with_notes|fail> \\
    --confidence <0.0-1.0> \\
    --finding "Finding 1" \\
    --finding "Finding 2"
"""
```

### 5.4 Review Flow Diagram

```
Task EXECUTING
     │
     ▼
Task REVIEWING ←─────────────────────┐
     │                                │
     ▼                                │
ReviewEngine.submit_review()          │
     │                                │
     ├─── verdict == "fail" ──────────┤
     │    (back to PLANNING           │
     │     with feedback)             │
     │                                │
     ├─── verdict == "pass" ──────────┤
     │    or "pass_with_notes"        │
     ▼                                │
Task VERDICT                          │
     │                                │
     ▼                                │
Task COMPLETE ─── or ─── PLANNING ────┘
                  (if additional rounds needed)
```

---

## Part 6: Task Parking & Resumption

### 6.1 Current State (Phase 0)

Phase 0 has basic park/resume in TaskLifecycle:
- `park()` transitions to PARKED status, moves YAML to `state/tasks/parked/`
- `resume()` transitions back to PLANNING
- Focus tracking via `state/tasks/focus.yaml`

### 6.2 Phase 1 Enhancements

Phase 1 adds team-aware parking:

```python
# Add to TaskLifecycle class:

def park_with_team(
    self, task_id: str, reason: str, actor: str,
    team_manager: TeamManager,
) -> Task:
    """Park a task and manage its team.

    Steps:
    1. Park the task (PARKED status)
    2. If task has a team: dissolve the team (despawn agents)
    3. Snapshot team state for resume
    4. Update focus tracking
    """
    task = self._load_task(task_id)

    # Snapshot team state before dissolving
    if task.team_id:
        team = team_manager._load_team(task.team_id)
        team_snapshot = team.model_dump()
        self.yaml_store.write_raw(
            f"state/tasks/parked/{task_id}/team_snapshot.yaml",
            team_snapshot,
        )
        team_manager.dissolve_team(task.team_id, f"Task parked: {reason}")

    # Park the task
    task = self.park(task_id, reason, actor)

    # Update focus if this was the focused task
    focus = self.get_focus()
    if focus == task_id:
        self._clear_focus()

    return task

def resume_with_team(
    self, task_id: str, actor: str,
    team_manager: TeamManager,
    topology_router: TopologyRouter,
    domain_config: DomainConfig,
) -> tuple[Task, Team | None]:
    """Resume a parked task, potentially recreating its team.

    Steps:
    1. Resume the task (back to PLANNING)
    2. If task had a team: re-analyze and create new team
    3. Set as focused task

    Returns (resumed_task, new_team_or_None)
    """
    task = self.resume(task_id, actor)
    self.set_focus(task_id)

    # Check if task had a team
    new_team = None
    snapshot_path = f"state/tasks/parked/{task_id}/team_snapshot.yaml"
    try:
        self.yaml_store.read_raw(snapshot_path)
        # Re-analyze and create new team
        analysis = topology_router.analyze(task)
        routing = topology_router.route(analysis)
        new_team = team_manager.create_team(task, routing, domain_config)
        task.team_id = new_team.id
    except FileNotFoundError:
        pass  # No team to restore — solo task

    return task, new_team

def list_parked_with_details(self) -> list[dict]:
    """List parked tasks with staleness information."""
    parked = self.get_parked()
    details = []
    now = datetime.utcnow()
    for task in parked:
        # Find when it was parked (last timeline entry)
        parked_at = None
        for entry in reversed(task.timeline):
            if entry.to_status == TaskStatus.PARKED.value:
                parked_at = entry.time
                break

        staleness_hours = 0.0
        if parked_at:
            staleness_hours = (now - parked_at).total_seconds() / 3600

        details.append({
            "task": task,
            "parked_at": parked_at,
            "staleness_hours": round(staleness_hours, 1),
            "had_team": task.team_id is not None,
        })
    return details
```

### 6.3 Focus Management

```python
def _clear_focus(self) -> None:
    """Clear the focus file when task is parked."""
    focus_path = "state/tasks/focus.yaml"
    try:
        self.yaml_store.write_raw(focus_path, {"active": None, "parked": []})
    except Exception:
        pass

def suggest_resume(self) -> str | None:
    """Suggest which parked task to resume based on priority and staleness.

    Priority order:
    1. Highest priority parked task
    2. Among equal priority: stalest task
    """
    parked = self.list_parked_with_details()
    if not parked:
        return None

    # Sort by priority (desc), then staleness (desc)
    parked.sort(
        key=lambda d: (d["task"].priority, d["staleness_hours"]),
        reverse=True,
    )
    return parked[0]["task"].id
```

---

## Part 7: Orchestrator Agent

### 7.1 Orchestrator Decision Logic (`engine/orchestrator.py`) — NEW

The orchestrator is the central coordination agent for hierarchical teams and parallel swarms.

```python
"""Orchestrator decision logic for multi-agent coordination.
Spec reference: Section 4.3 (Orchestrator Role), Section 5 (Topology)."""
from __future__ import annotations

from datetime import datetime

from ..models.base import generate_id
from ..models.task import Task, TaskStatus
from ..models.team import SubTask, Team, TeamStatus
from ..state.yaml_store import YamlStore
from .review_engine import ReviewEngine
from .task_lifecycle import TaskLifecycle
from .team_manager import TeamManager
from .topology_router import TopologyRouter


class Orchestrator:
    """Central orchestration logic for task processing.

    The orchestrator is NOT an agent itself — it's the decision engine
    that the orchestrator agent (or the framework in solo mode) invokes.

    Orchestration pipeline:
    1. Receive task
    2. Analyze via TopologyRouter
    3. Select topology and create team
    4. Decompose task into subtasks
    5. Assign subtasks to team members
    6. Monitor progress
    7. Trigger review when workers complete
    8. Handle review verdict (complete or re-plan)
    9. Dissolve team on completion
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        topology_router: TopologyRouter,
        team_manager: TeamManager,
        task_lifecycle: TaskLifecycle,
        review_engine: ReviewEngine,
    ):
        self.yaml_store = yaml_store
        self.topology_router = topology_router
        self.team_manager = team_manager
        self.task_lifecycle = task_lifecycle
        self.review_engine = review_engine

    def process_task(
        self, task_id: str, domain_config, actor: str = "orchestrator"
    ) -> dict:
        """Full orchestration pipeline for a task.

        Returns dict with:
        - task: Final task state
        - team: Team record (or None for solo)
        - analysis: TaskAnalysis
        - routing: RoutingResult
        - review: TaskReview (or None if pending)
        """
        # 1. Load task
        task = self.task_lifecycle._load_task(task_id)

        # 2. Transition to ANALYSIS
        task = self.task_lifecycle.transition(
            task_id, TaskStatus.ANALYSIS, actor, "Starting orchestration"
        )

        # 3. Analyze task
        analysis = self.topology_router.analyze(task)

        # 4. Route to topology
        routing = self.topology_router.route(analysis)

        # 5. Transition to PLANNING
        task = self.task_lifecycle.transition(
            task_id, TaskStatus.PLANNING, actor,
            f"Topology: {routing.pattern} ({routing.agent_count} agents)"
        )

        # 6. Store topology assignment on task
        from ..models.task import TaskTopology, TopologyAssignment
        task.topology = TaskTopology(
            selected=TopologyAssignment(
                pattern=routing.pattern,
                agent_count=routing.agent_count,
                rationale=routing.rationale,
            ),
        )

        # 7. Create team (if not solo pattern — even solo has reviewer)
        team = self.team_manager.create_team(task, routing, domain_config)
        task.team_id = team.id

        # 8. Transition to EXECUTING
        task = self.task_lifecycle.transition(
            task_id, TaskStatus.EXECUTING, actor,
            f"Team {team.id} executing with {len(team.members)} agents"
        )

        return {
            "task": task,
            "team": team,
            "analysis": analysis,
            "routing": routing,
        }

    def complete_execution(self, task_id: str, actor: str = "orchestrator") -> Task:
        """Transition task from EXECUTING to REVIEWING.

        Called when all workers have completed their subtasks.
        """
        return self.task_lifecycle.transition(
            task_id, TaskStatus.REVIEWING, actor,
            "All workers complete — entering mandatory review"
        )

    def handle_verdict(
        self, task_id: str, actor: str = "orchestrator"
    ) -> Task:
        """Handle review verdict and transition appropriately.

        If review verdict is "pass" or "pass_with_notes":
          VERDICT → COMPLETE
        If review verdict is "fail":
          Already handled by ReviewEngine (back to PLANNING)
        """
        task = self.task_lifecycle._load_task(task_id)
        if task.review and task.review.verdict in ("pass", "pass_with_notes"):
            task = self.task_lifecycle.transition(
                task_id, TaskStatus.COMPLETE, actor,
                f"Review passed: {task.review.verdict}"
            )
            # Dissolve team
            if task.team_id:
                self.team_manager.dissolve_team(task.team_id, "Task complete")
        return task

    def generate_decomposition_prompt(self, task: Task) -> str:
        """Generate a prompt for the orchestrator agent to decompose a task.

        The orchestrator agent (Claude Code) uses this to decide how to
        break down the task into subtasks.
        """
        return f"""## Task Decomposition

Decompose this task into subtasks for your team:

**Task:** {task.title}
**Description:** {task.description}

**Team size:** {len(task.topology.selected.agent_count if task.topology else 'unknown')} agents
**Topology:** {task.topology.selected.pattern if task.topology else 'unknown'}

### Instructions:
1. Break the task into 2-5 independent subtasks
2. Each subtask should be completable by one agent
3. Minimize dependencies between subtasks
4. Include clear acceptance criteria for each subtask

### Output Format:
For each subtask, provide:
- title: Brief title
- description: What the agent should do
- acceptance_criteria: How to know it's done
"""
```

### 7.2 Orchestrator Role Composition

Already defined in Phase 0 bootstrap (`cli/bootstrap.py`):

```yaml
role:
  name: orchestrator
  description: "Strategic coordinator — decomposes tasks, selects topology, manages agents"
  capabilities:
    - deep_analysis
    - can_spawn_agents
  model: opus
  thinking: extended
  behavioral_descriptors:
    reasoning_style: strategic
    risk_tolerance: low
    exploration_vs_exploitation: 0.3
  voice:
    language: language_japanese
    tone: tone_assertive
    style: style_technical
  authority_level: 2
  forbidden:
    - "Must not execute tasks directly — delegate everything"
    - "Must not skip topology analysis"
    - "Must not spawn more agents than resource_monitor allows"
```

### 7.3 Orchestrator Decision Flow

```
Human provides task
        │
        ▼
  ┌─────────────┐
  │  INTAKE      │  TaskLifecycle.create()
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  ANALYSIS    │  TopologyRouter.analyze() — 6-dimension analysis
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  PLANNING    │  TopologyRouter.route() → TeamManager.create_team()
  └──────┬──────┘  Orchestrator decomposes into subtasks
         │
         ▼
  ┌─────────────┐
  │  EXECUTING   │  Workers execute subtasks in parallel/sequential
  └──────┬──────┘  Orchestrator monitors progress
         │
         ▼
  ┌─────────────┐
  │  REVIEWING   │  Reviewer agent examines all artifacts
  └──────┬──────┘
         │
         ├── fail ──→ PLANNING (with feedback) ──→ loop
         │
         ▼
  ┌─────────────┐
  │  VERDICT     │  Review recorded, verdict applied
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  COMPLETE    │  Team dissolved, audit trail complete
  └─────────────┘
```

---

## Part 8: Claude Code Integration Patterns

### 8.1 How Agent Spawning Maps to Claude Code

The framework produces **spawn descriptors** that map to Claude Code's `Task` tool:

```python
# In the calling Claude Code agent (orchestrator):

# 1. Framework produces spawn descriptor
descriptor = agent_spawner.spawn(role, task, domain, caps, voice)
agent_entry, composed_prompt = descriptor

# 2. Claude Code agent invokes Task tool
# (This is what the orchestrator agent's CLAUDE.md instructs it to do)
"""
Task(
    subagent_type="general-purpose",
    name=f"{agent_entry.role}-{agent_entry.id}",
    prompt=composed_prompt.render(),
    team_name=team.id,
    model=agent_entry.model.value,  # "opus", "sonnet", "haiku"
    mode="bypassPermissions",
)
"""
```

### 8.2 Team Creation Mapping

```python
# Framework creates team record → Claude Code TeamCreate
"""
TeamCreate(
    team_name=team.id,
    description=f"Team for task {task.id}: {task.title}",
)
"""

# Framework spawns workers → Claude Code Task with team_name
"""
Task(
    subagent_type="general-purpose",
    name="implementer-001",
    prompt=composed_prompt,
    team_name=team.id,
)
"""

# Inter-agent messaging → Claude Code SendMessage
"""
SendMessage(
    type="message",
    recipient="implementer-001",
    content="Your subtask: ...",
    summary="Subtask assignment",
)
"""
```

### 8.3 Review Submission Mapping

The reviewer agent calls the framework's review CLI:

```bash
# Reviewer agent runs this via Bash tool:
uv run python -m uagents.cli.task_manager review task-20260228-001 \
    --reviewer agent-20260228-003 \
    --verdict pass_with_notes \
    --confidence 0.85 \
    --finding "Implementation matches requirements" \
    --finding "Minor: variable naming could be more descriptive"
```

### 8.4 Communication Pattern by Topology

| Topology | Claude Code Mechanism | Framework State |
|----------|----------------------|-----------------|
| Solo | Single Task tool call | 1 agent in registry |
| Parallel Swarm | Multiple Task tool calls (parallel) | N agents, stigmergic via files |
| Hierarchical | TeamCreate + Task + SendMessage | Team record + message log |

---

## Part 9: CLAUDE.md Phase 1 Updates

### 9.1 New Sections to Add

The CLAUDE.md generator needs to produce Phase 1 content:

```markdown
## Multi-Agent Orchestration (Phase 1)

### Task Processing Protocol
When you receive a task:
1. Create task: `uv run python -m uagents.cli.task_manager create "title" "description"`
2. Analyze: `uv run python -m uagents.engine.topology_router analyze <task_id>`
3. Route: Framework selects topology (solo, parallel_swarm, or hierarchical_team)
4. If solo: Execute directly, then request review
5. If team: Framework creates team, spawns agents, assigns subtasks
6. After execution: Mandatory review before completion (Axiom A7)

### Team Operations
- List teams: `uv run python -m uagents.cli.team_manager list`
- Team status: `uv run python -m uagents.cli.team_manager status <team_id>`
- Dissolve team: `uv run python -m uagents.cli.team_manager dissolve <team_id>`

### Review Protocol (Axiom A7 — MANDATORY)
- Every task must be reviewed before completion
- Reviewer must NOT be the executor
- Review must contain specific findings (no rubber-stamping)
- Submit review: `uv run python -m uagents.cli.task_manager review <task_id> ...`
- Failed reviews return task to PLANNING with feedback

### Task Parking
- Park current task: `uv run python -m uagents.cli.task_manager park <task_id> "reason"`
- List parked: `uv run python -m uagents.cli.task_manager list --parked`
- Resume: `uv run python -m uagents.cli.task_manager resume <task_id>`
- Framework suggests resume based on priority and staleness

### Phase 1 Limitations
- 3 topology patterns only (solo, parallel_swarm, hierarchical_team)
- No pipeline, hybrid, or debate topologies
- No evolution engine or self-improvement
- No MAP-Elites archive (pure heuristic routing)
- No rate limit tracking or token budget enforcement
- Max 10 concurrent agents
```

### 9.2 Generator Changes

Add to `claude_md/generator.py`:

```python
def _section_orchestration(self) -> str:
    """Generate multi-agent orchestration section."""
    return """## Multi-Agent Orchestration

### Task Processing
1. Create task → analyze (6 dimensions) → route (select topology)
2. Solo: single worker + reviewer
3. Parallel: orchestrator + N workers + reviewer
4. Hierarchical: orchestrator + specialized workers + reviewer

### Review Mandate (Axiom A7)
Every task requires mandatory peer review before completion.
- Reviewer ≠ executor
- Must provide specific findings
- Failed review → back to PLANNING

### Topology Patterns (Phase 1)
| Pattern | When | Agents |
|---------|------|--------|
| solo | simple + small + routine | 2 |
| parallel_swarm | decomposable + independent | 4-7 |
| hierarchical_team | complex + coupled | 3-5 |
"""

def _section_phase1_limitations(self) -> str:
    """Generate Phase 1 limitations section."""
    return """## Current Limitations (Phase 1)
- 3 topology patterns (solo, parallel_swarm, hierarchical_team)
- Heuristic-based routing (no LLM judgment, no MAP-Elites)
- No evolution engine or self-improvement
- No rate limit tracking
- No dynamic tool loading
- Max 10 concurrent agents
"""
```

---

## Part 10: Implementation Sequence

### 10.1 Wave 1: Data Models & Directory Structure

**Prerequisites:** Phase 0 complete (146 tests passing)
**Estimated files:** ~5

1. Create `src/uagents/models/team.py` — Team, SubTask, TeamMember, TopologyPattern, etc.
2. Create `src/uagents/models/message.py` — MessageType, AgentMessage
3. Modify `src/uagents/models/task.py` — add team_id, review_required, subtasks fields
4. Modify `src/uagents/models/agent.py` — add heartbeat_at, subtask_id fields
5. Update `src/uagents/state/directory.py` — add state/teams/ and state/coordination/ dirs
6. Write tests for new models

**Verification:** `uv run pytest tests/test_models/ -v` — all pass, including new model tests

### 10.2 Wave 2: Topology Router Upgrade

**Prerequisites:** Wave 1 complete
**Estimated files:** ~2

1. Upgrade `src/uagents/engine/topology_router.py` — heuristic analysis, 3-pattern routing
2. Write comprehensive routing tests

**Verification:** `uv run pytest tests/test_engine/test_topology_router*.py -v` — all pass

### 10.3 Wave 3: Team Manager & Agent Spawner Upgrades

**Prerequisites:** Wave 1, Wave 2 complete
**Estimated files:** ~3

1. Create `src/uagents/engine/team_manager.py` — full team lifecycle
2. Upgrade `src/uagents/engine/agent_spawner.py` — team-aware spawning, heartbeat
3. Write team management tests

**Verification:** `uv run pytest tests/test_engine/test_team_manager.py tests/test_engine/test_agent_spawner*.py -v`

### 10.4 Wave 4: Review Engine

**Prerequisites:** Wave 1 complete
**Estimated files:** ~2

1. Create `src/uagents/engine/review_engine.py` — review mandate enforcement
2. Write review engine tests (submit_review, self-review prevention, rubber-stamp detection)

**Verification:** `uv run pytest tests/test_engine/test_review_engine.py -v`

### 10.5 Wave 5: Orchestrator & Task Lifecycle Enhancements

**Prerequisites:** Waves 2-4 complete
**Estimated files:** ~3

1. Create `src/uagents/engine/orchestrator.py` — orchestration pipeline
2. Upgrade `src/uagents/engine/task_lifecycle.py` — team-aware parking, resume suggestions
3. Write orchestrator and enhanced lifecycle tests

**Verification:** `uv run pytest tests/test_engine/test_orchestrator.py tests/test_engine/test_task_lifecycle*.py -v`

### 10.6 Wave 6: CLI & CLAUDE.md Updates

**Prerequisites:** Waves 1-5 complete
**Estimated files:** ~5

1. Create `src/uagents/cli/team_manager.py` — team CLI commands
2. Create `tools/team-manager.sh` — shell wrapper
3. Upgrade `src/uagents/cli/task_manager.py` — review commands
4. Upgrade `src/uagents/cli/spawn_agent.py` — team-aware spawning
5. Upgrade `src/uagents/claude_md/generator.py` — Phase 1 content
6. Upgrade `src/uagents/cli/bootstrap.py` — Phase 1 directory scaffold

**Verification:** `uv run pytest --tb=long -v` — ALL tests pass

### 10.7 Wave 7: Integration Tests

**Prerequisites:** All waves complete
**Estimated files:** ~2

1. Create `tests/test_integration/test_full_lifecycle.py` — end-to-end task processing
2. Create `tests/test_integration/test_parking_resumption.py` — park/resume with team

**Verification:** Full test suite passes, integration tests verify end-to-end flow

### 10.8 Implementation Dependency Graph

```
Wave 1 (Models + Dirs)
  │
  ├──→ Wave 2 (Topology Router)
  │         │
  │         ├──→ Wave 3 (Team Manager + Spawner) ──┐
  │         │                                       │
  │         └──────────────────────────────────────→ Wave 5 (Orchestrator)
  │                                                    │
  ├──→ Wave 4 (Review Engine) ─────────────────────────┘
  │                                                    │
  └────────────────────────────────────────────────→ Wave 6 (CLI + CLAUDE.md)
                                                       │
                                                       └──→ Wave 7 (Integration)
```

Waves 2, 3, 4 can be partially parallelized since they depend on Wave 1 but are mostly independent of each other.

---

## Part 11: Verification Checklist

### 11.1 Unit Tests (per module)

- [ ] `test_team.py` — Team creation, status transitions, member management (8+ tests)
- [ ] `test_message.py` — Message model creation, type validation (4+ tests)
- [ ] `test_topology_router_phase1.py` — Heuristic analysis for all 6 dimensions, 3-pattern routing, novelty assessment (15+ tests)
- [ ] `test_team_manager.py` — Create team, decompose, dissolve, list active (10+ tests)
- [ ] `test_agent_spawner_phase1.py` — Team-aware spawn, heartbeat, health check (8+ tests)
- [ ] `test_review_engine.py` — Submit review, self-review prevention, rubber-stamp detection, verdict handling (12+ tests)
- [ ] `test_orchestrator.py` — Full pipeline, completion, verdict handling (8+ tests)
- [ ] `test_task_lifecycle_phase1.py` — Team-aware parking, resume with team, resume suggestions (8+ tests)

### 11.2 Integration Tests

- [ ] End-to-end: INTAKE → ANALYSIS → PLANNING → EXECUTING → REVIEWING → VERDICT → COMPLETE
- [ ] Park and resume with team recreation
- [ ] Failed review → re-plan → re-execute → pass
- [ ] Solo topology: worker + reviewer
- [ ] Parallel swarm: orchestrator + 3 workers + reviewer
- [ ] Hierarchical team: orchestrator + 2 workers + reviewer
- [ ] Resource-constrained spawn rejection

### 11.3 Manual Validation

- [ ] Run 5 real tasks through the framework and verify complete audit trail
- [ ] Verify all tasks have reviews in their YAML records
- [ ] Verify team records in `state/teams/` match expected topology
- [ ] Verify CLAUDE.md contains Phase 1 orchestration instructions
- [ ] Verify parked tasks can be resumed and complete successfully

### 11.4 Regression

- [ ] All 146 existing Phase 0 tests still pass
- [ ] Phase 0 bootstrap still creates correct directory scaffold
- [ ] Constitution hash verification still works
- [ ] Solo task processing (no team) still works end-to-end

---

## Part 12: Edge Cases, Failure Modes & Mitigations

### 12.1 Topology Routing Failures

| ID | Failure Mode | Severity | Mitigation |
|----|-------------|----------|------------|
| T1 | Heuristic misclassifies task | Medium | Default to hierarchical_team (safest). Log analysis for human review. Phase 2+ adds LLM judgment. |
| T2 | No resources for selected topology | High | Downgrade: hierarchical→solo, parallel→solo. Log resource constraint. |
| T3 | Novelty check has no history | Low | Default to NOVEL (conservative). Results in optional scout injection. |

### 12.2 Team Management Failures

| ID | Failure Mode | Severity | Mitigation |
|----|-------------|----------|------------|
| M1 | Agent spawn fails mid-team-creation | High | Rollback: despawn all already-spawned agents. Raise TeamCreationError. |
| M2 | Agent becomes unresponsive (no heartbeat) | Medium | 10-minute timeout. Despawn hung agent, reassign subtask. |
| M3 | Team creation exceeds resource limits | High | Pre-check via can_spawn_agent() for each team member. Reduce team size if needed. |
| M4 | Subtask assignment fails (no workers available) | Medium | Leave subtask unassigned, log warning. Orchestrator can retry. |

### 12.3 Review Failures

| ID | Failure Mode | Severity | Mitigation |
|----|-------------|----------|------------|
| R1 | Rubber-stamp review (no findings) | High | Enforce MIN_FINDINGS=1. Reject reviews with zero findings. |
| R2 | Self-review attempt | Critical | Check timeline: reviewer ≠ executor. Raise ReviewViolationError. |
| R3 | Review loop (fail → re-plan → fail → ...) | Medium | Track review_rounds in TaskMetrics. After 3 rounds: escalate to human. |
| R4 | Reviewer agent crashes before submitting | Medium | Task stays in REVIEWING. Timeout + respawn reviewer. |
| R5 | Low confidence review | Low | Enforce MIN_CONFIDENCE=0.3. Below threshold: reject review, request more analysis. |

### 12.4 Task Parking Failures

| ID | Failure Mode | Severity | Mitigation |
|----|-------------|----------|------------|
| P1 | Park with unsaved team state | Medium | Always snapshot team before dissolving. Atomic YAML write. |
| P2 | Resume with stale context | Low | Re-analyze task on resume. Create fresh team, don't restore old agent states. |
| P3 | Park during mid-execution | Medium | Workers may have partial results. Snapshot subtask progress. |
| P4 | Multiple tasks competing for focus | Low | Priority-based focus selection. Human can override via CLI. |

### 12.5 Communication Failures

| ID | Failure Mode | Severity | Mitigation |
|----|-------------|----------|------------|
| C1 | SendMessage not delivered (Claude Code limitation) | Medium | Require ACK for critical messages. Retry once after 2 min. Escalate on failure. |
| C2 | Message ordering not guaranteed | Low | Include sequence numbers in messages. Orchestrator can request status updates. |
| C3 | Stigmergic coordination stale (parallel swarm) | Low | Pressure fields include timestamps. Ignore entries > 5 min old. |

### 12.6 Cascading Failures

| ID | Failure Mode | Severity | Mitigation |
|----|-------------|----------|------------|
| X1 | Orchestrator agent crashes | Critical | Task remains in current state. Human can resume or reassign. YAML state is always consistent. |
| X2 | All workers fail simultaneously | High | Team dissolves. Task parks automatically. Human notification. |
| X3 | Disk full during team creation | Critical | Pre-check disk space before each YAML write (existing Phase 0 protection in yaml_store). |

---

## Appendix A: Complete File Inventory

### New Files (Phase 1)

```
src/uagents/models/team.py              # ~80 lines
src/uagents/models/message.py           # ~45 lines
src/uagents/engine/team_manager.py      # ~250 lines
src/uagents/engine/review_engine.py     # ~180 lines
src/uagents/engine/orchestrator.py      # ~200 lines
src/uagents/cli/team_manager.py         # ~120 lines
tools/team-manager.sh                   # ~3 lines

tests/test_models/test_team.py          # ~100 lines
tests/test_models/test_message.py       # ~50 lines
tests/test_engine/test_topology_router_phase1.py  # ~200 lines
tests/test_engine/test_team_manager.py  # ~150 lines
tests/test_engine/test_review_engine.py # ~180 lines
tests/test_engine/test_orchestrator.py  # ~120 lines
tests/test_engine/test_agent_spawner_phase1.py  # ~100 lines
tests/test_engine/test_task_lifecycle_phase1.py # ~100 lines
tests/test_integration/test_full_lifecycle.py   # ~150 lines
tests/test_integration/test_parking_resumption.py # ~100 lines
```

### Modified Files (Phase 0 → Phase 1)

```
src/uagents/models/task.py              # +3 fields
src/uagents/models/agent.py             # +2 fields
src/uagents/engine/topology_router.py   # ~300 lines (rewrite analyze + route)
src/uagents/engine/agent_spawner.py     # +60 lines (team-aware spawn, heartbeat)
src/uagents/engine/task_lifecycle.py    # +80 lines (team parking, resume suggestions)
src/uagents/engine/prompt_composer.py   # +30 lines (orchestrator prompt)
src/uagents/claude_md/generator.py      # +40 lines (Phase 1 sections)
src/uagents/cli/bootstrap.py            # +20 lines (Phase 1 dirs)
src/uagents/cli/task_manager.py         # +40 lines (review commands)
src/uagents/cli/spawn_agent.py          # +20 lines (team-aware)
src/uagents/state/directory.py          # +5 lines (new dirs)
```

### Estimated Totals

- New source code: ~875 lines across 7 files
- Modified source code: ~295 lines across 11 files
- New test code: ~1,250 lines across 10 files
- Total new/modified: ~2,420 lines
- Expected test count: 146 (existing) + ~120 (new) = ~266 tests

---

## Appendix B: Literature References

Key papers informing Phase 1 design:

1. **AdaptOrch** (Yu, 2026) — Topology routing algorithm, 12-23% improvement from topology alone
2. **CORAL** (Ren et al., 2026) — Information-flow orchestration replacing predefined workflows
3. **ALAS** (Geng & Chang, 2025) — Non-circular validation, localized repair, 83.7% success
4. **AgentSys** (Wen et al., 2026) — OS-inspired memory isolation for agent spawning
5. **Tian & Zhang** (2024) — Functional complementarity: 3-agent Coder-Executor-Critic is optimal
6. **MAST** (Cemri et al., 2025) — 14 failure modes in multi-agent systems
7. **DyTopo** (Lu et al., 2026) — Dynamic per-round communication graphs, +6.2%
8. **AgentConductor** (Wang et al., 2026) — RL-optimized topologies, +14.6% pass@1
9. **Co-Saving** (Qiu et al., 2025) — Resource-aware shortcuts, 50% token reduction
10. **LEGOMem** (Han et al., 2025) — Orchestrator memory critical for decomposition/delegation

Full literature review: `research/multi-agent-orchestration-literature-review.md`
