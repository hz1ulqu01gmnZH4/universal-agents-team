"""Team lifecycle management for multi-agent orchestration.
Spec reference: Section 5.2 (Topology Patterns), Section 9 (Coordination Layer)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..audit.logger import AuditLogger
from ..models.agent import AgentRegistryEntry, AgentStatus
from ..models.base import generate_id
from ..models.capability import CapabilityAtom, ModelPreference
from ..models.domain import DomainConfig
from ..models.role import RoleComposition
from ..models.task import Task
from ..models.team import (
    CoordinationMode,
    SubTask,
    SubTaskStatus,
    Team,
    TeamMember,
    TeamStatus,
    TopologyPattern,
)
from ..models.voice import VoiceAtom
from ..state.yaml_store import YamlStore
from .agent_spawner import AgentSpawner
from .topology_router import RoutingResult

logger = logging.getLogger("uagents.team_manager")


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
        domain: str = "meta",
        audit_logger: AuditLogger | None = None,
    ):
        self.yaml_store = yaml_store
        self.agent_spawner = agent_spawner
        self.capabilities = capabilities
        self.voice_atoms = voice_atoms
        self._teams_base = f"instances/{domain}/state/teams"
        self.audit_logger = audit_logger

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
            created_at=datetime.now(timezone.utc),
            task_id=task.id,
            pattern=pattern,
            coordination=coordination,
            status=TeamStatus.FORMING,
            max_agents=routing_result.agent_count,
        )

        # Persist team record
        team_dir = f"{self._teams_base}/{team_id}"
        self.yaml_store.write(f"{team_dir}/team.yaml", team)

        # Spawn each agent
        spawned_members: list[TeamMember] = []
        for assignment in routing_result.role_assignments:
            role_name = assignment["role"]
            try:
                role = self._load_role(role_name)
                agent_entry, composed = self.agent_spawner.spawn_for_team(
                    role=role,
                    task=task,
                    domain_config=domain_config,
                    capabilities=self.capabilities,
                    voice_atoms=self.voice_atoms,
                    team_id=team_id,
                )
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
                created_at=datetime.now(timezone.utc),
                parent_task_id=task.id,
                title=desc["title"],
                description=desc["description"],
                assigned_to=worker.agent_id if worker else None,
                status=SubTaskStatus.PENDING if worker else SubTaskStatus.UNASSIGNED,
            )
            subtasks.append(subtask)

            if worker:
                team.subtask_assignments[subtask_id] = worker.agent_id

        # Persist subtasks
        team_dir = f"{self._teams_base}/{team.id}"
        for st in subtasks:
            self.yaml_store.write(f"{team_dir}/subtasks/{st.id}.yaml", st)

        return subtasks

    def transition_team(self, team_id: str, new_status: TeamStatus) -> Team:
        """Transition team to a new status."""
        team = self._load_team(team_id)
        team.status = new_status
        team.updated_at = datetime.now(timezone.utc)
        self.yaml_store.write(f"{self._teams_base}/{team_id}/team.yaml", team)
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
        self.yaml_store.write(f"{self._teams_base}/{team_id}/team.yaml", team)

    def get_active_teams(self) -> list[Team]:
        """List all non-dissolved teams."""
        teams = []
        try:
            team_dirs = self.yaml_store.list_dir(self._teams_base)
        except (NotADirectoryError, FileNotFoundError):
            return teams
        for team_dir in team_dirs:
            try:
                data = self.yaml_store.read_raw(f"{self._teams_base}/{team_dir}/team.yaml")
                if data.get("status") != TeamStatus.DISSOLVED:
                    teams.append(Team.model_validate(data, strict=False))
            except Exception as e:
                logger.warning(
                    f"Failed to load team from {team_dir}: {e}"
                )
                continue
        return teams

    def _load_team(self, team_id: str) -> Team:
        """Load team from YAML store.

        Uses model_validate() instead of Team(**data) to properly validate
        through Pydantic (handles nested models, type coercion, etc.).
        strict=False allows YAML string values to be coerced to enums/datetimes.
        """
        data = self.yaml_store.read_raw(f"{self._teams_base}/{team_id}/team.yaml")
        return Team.model_validate(data, strict=False)

    def _load_role(self, role_name: str) -> RoleComposition:
        """Load a role composition from YAML."""
        data = self.yaml_store.read_raw(f"roles/compositions/{role_name}.yaml")
        role_data = data.get("role", data)
        return RoleComposition.model_validate(role_data, strict=False)

    def _pattern_to_coordination(self, pattern: TopologyPattern) -> CoordinationMode:
        """Map topology pattern to coordination mode."""
        mapping = {
            TopologyPattern.SOLO: CoordinationMode.NONE,
            TopologyPattern.PARALLEL_SWARM: CoordinationMode.STIGMERGIC,
            TopologyPattern.HIERARCHICAL_TEAM: CoordinationMode.EXPLICIT,
        }
        return mapping.get(pattern, CoordinationMode.EXPLICIT)
