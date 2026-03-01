"""Resource-checked agent spawning with prompt composition.
Spec reference: Section 4.4 (spawn_agent), Section 18 (resource checks).

Phase 1.5: Budget and rate-limit checks before spawning (Section 18.4).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from ..models.agent import AgentRegistryEntry, AgentStatus
from ..models.base import generate_id
from ..models.capability import CapabilityAtom, ModelPreference
from ..models.domain import DomainConfig
from ..models.resource import BudgetPressureLevel
from ..models.role import RoleComposition
from ..models.task import Task
from ..models.team import SubTask
from ..models.voice import VoiceAtom
from ..state.yaml_store import YamlStore
from .prompt_composer import ComposedPrompt, PromptComposer
from .resource_tracker import ResourceTracker

if TYPE_CHECKING:
    from .budget_tracker import BudgetTracker
    from .rate_limiter import BackpressureLevel, RateLimiter

logger = logging.getLogger("uagents.agent_spawner")


class ResourceConstrainedError(RuntimeError):
    """Raised when spawn is blocked by resource constraints."""


class AgentSpawner:
    """Resource-checked agent spawning with prompt composition.

    Spawn pipeline (Section 4.4):
    1. Check compute (CPU/memory/disk)
    2. Check agent cap
    3. Load role composition
    4. Compose prompt via PromptComposer
    5. Register in agent registry
    6. Return spawn descriptor for Claude Code Task tool
    """

    def __init__(
        self,
        prompt_composer: PromptComposer,
        resource_tracker: ResourceTracker,
        yaml_store: YamlStore,
        domain: str = "meta",
        budget_tracker: BudgetTracker | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        self.prompt_composer = prompt_composer
        self.resource_tracker = resource_tracker
        self.yaml_store = yaml_store
        self.domain = domain
        self.budget_tracker = budget_tracker
        self.rate_limiter = rate_limiter
        self._agents_base = f"instances/{domain}/state/agents"

    def spawn(
        self,
        role: RoleComposition,
        task: Task,
        domain_config: DomainConfig,
        capabilities: dict[str, CapabilityAtom],
        voice_atoms: dict[str, VoiceAtom],
    ) -> tuple[AgentRegistryEntry, ComposedPrompt]:
        """Full spawn pipeline. Raises ResourceConstrainedError if blocked.

        Phase 1.5 spawn policy (Section 18.4):
        - FULL_STOP backpressure: no agents spawn
        - SINGLE_AGENT backpressure: only if no other agents are active
        - RED budget: no spawn
        """
        # 1-2. Resource check with 20% headroom (G1)
        can_spawn, reason = self.resource_tracker.can_spawn_agent()
        if not can_spawn:
            raise ResourceConstrainedError(f"Cannot spawn agent: {reason}")

        # Phase 1.5: Rate limit check
        if self.rate_limiter is not None:
            from .rate_limiter import BackpressureLevel
            bp = self.rate_limiter.get_backpressure_level()
            if bp == BackpressureLevel.FULL_STOP:
                raise ResourceConstrainedError(
                    f"Cannot spawn: rate limit backpressure at {bp.value}"
                )
            if bp == BackpressureLevel.SINGLE_AGENT:
                active = self.list_active()
                if len(active) > 0:
                    raise ResourceConstrainedError(
                        f"Cannot spawn: rate limit at SINGLE_AGENT and "
                        f"{len(active)} agent(s) already active"
                    )

        # Phase 1.5: Budget check
        if self.budget_tracker is not None:
            pressure = self.budget_tracker.get_pressure()
            if pressure == BudgetPressureLevel.RED:
                raise ResourceConstrainedError(
                    f"Cannot spawn: budget pressure RED "
                    f"({self.budget_tracker.get_window().remaining_tokens} tokens remaining)"
                )

        # 3. Validate role references (G2)
        for cap_name in role.capabilities:
            if cap_name not in capabilities:
                raise FileNotFoundError(
                    f"Capability '{cap_name}' referenced by role '{role.name}' "
                    f"not found. Available: {list(capabilities.keys())}"
                )

        # 4. Compose prompt
        composed = self.prompt_composer.compose(
            role=role,
            task=task,
            domain=domain_config,
            capabilities=capabilities,
            voice_atoms=voice_atoms,
        )

        # 5. Register agent
        agent_id = generate_id("agent")
        entry = AgentRegistryEntry(
            id=agent_id,
            created_at=datetime.now(timezone.utc),
            role=role.name,
            model=ModelPreference(role.model),
            voice_profile_hash="",  # Computed from voice atoms
            status=AgentStatus.ACTIVE,
            current_task=task.id,
            spawned_by="orchestrator",
            estimated_cost=composed.total_tokens,
        )

        # Write to agent-scoped directory (G5: no write contention)
        agent_dir = f"{self._agents_base}/{agent_id}"
        self.yaml_store.write(f"{agent_dir}/status.yaml", entry)

        return entry, composed

    def despawn(self, agent_id: str, reason: str) -> None:
        """Update agent status to despawned."""
        path = f"{self._agents_base}/{agent_id}/status.yaml"
        entry = self.yaml_store.read(path, AgentRegistryEntry)
        entry.status = AgentStatus.DESPAWNED
        entry.updated_at = datetime.now(timezone.utc)
        self.yaml_store.write(path, entry)

    def list_active(self) -> list[AgentRegistryEntry]:
        """List all active agents."""
        agents: list[AgentRegistryEntry] = []
        try:
            for name in self.yaml_store.list_dir(self._agents_base):
                path = f"{self._agents_base}/{name}/status.yaml"
                if self.yaml_store.exists(path):
                    entry = self.yaml_store.read(path, AgentRegistryEntry)
                    if entry.status == AgentStatus.ACTIVE:
                        agents.append(entry)
        except (FileNotFoundError, NotADirectoryError):
            pass
        return agents

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
        entry.heartbeat_at = datetime.now(timezone.utc)
        if subtask:
            entry.subtask_id = subtask.id
            entry.current_task = f"{task.id}:{subtask.id}"

        # Update persisted entry
        agent_dir = f"{self._agents_base}/{entry.id}"
        self.yaml_store.write(f"{agent_dir}/status.yaml", entry)
        return entry, composed

    def update_heartbeat(self, agent_id: str) -> None:
        """Update agent's heartbeat timestamp."""
        agent_dir = f"{self._agents_base}/{agent_id}"
        try:
            data = self.yaml_store.read_raw(f"{agent_dir}/status.yaml")
            data["heartbeat_at"] = datetime.now(timezone.utc).isoformat()
            self.yaml_store.write_raw(f"{agent_dir}/status.yaml", data)
        except FileNotFoundError:
            logger.warning(
                f"Cannot update heartbeat for {agent_id} — agent file not found (already despawned?)"
            )

    @staticmethod
    def _parse_aware_datetime(iso_str: str) -> datetime:
        """FM-112: Parse ISO datetime string, ensuring timezone-aware result.

        Phase 1 code may have written naive UTC timestamps (datetime.utcnow()).
        Phase 2 uses aware timestamps (datetime.now(timezone.utc)). This method
        normalizes both formats so datetime subtraction never raises TypeError.
        """
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            # Assume naive timestamps are UTC (Phase 1 convention)
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def check_agent_health(self, agent_id: str, timeout_minutes: int = 10) -> bool:
        """Check if agent is responsive (heartbeat within timeout).

        FM-63: Agents without heartbeat are treated as unhealthy if
        their creation time exceeds timeout. No more permanent "healthy"
        for legacy agents.
        FM-112: Uses _parse_aware_datetime() to handle mixed naive/aware timestamps.
        """
        agent_dir = f"{self._agents_base}/{agent_id}"
        try:
            data = self.yaml_store.read_raw(f"{agent_dir}/status.yaml")
            if data.get("status") == AgentStatus.DESPAWNED:
                return False
            heartbeat = data.get("heartbeat_at")
            if heartbeat:
                last_beat = self._parse_aware_datetime(heartbeat)
                elapsed = (datetime.now(timezone.utc) - last_beat).total_seconds() / 60
                return elapsed < timeout_minutes

            # FM-63: No heartbeat — check creation time instead
            created_at = data.get("created_at")
            if created_at:
                created = self._parse_aware_datetime(created_at)
                elapsed = (datetime.now(timezone.utc) - created).total_seconds() / 60
                if elapsed > timeout_minutes:
                    logger.info(
                        f"Agent {agent_id} has no heartbeat and was created "
                        f"{elapsed:.1f} min ago (> {timeout_minutes} min timeout). "
                        f"Treating as unhealthy."
                    )
                    return False
            return True  # Newly created, within timeout
        except FileNotFoundError:
            return False

    def despawn_idle_agents(self, timeout_minutes: int = 5) -> list[str]:
        """Despawn agents that have been idle beyond timeout.

        Phase 1.5: Resource reclamation for idle agents (Section 18.4).
        """
        despawned = []
        for entry in self.list_active():
            if not self.check_agent_health(entry.id, timeout_minutes):
                self.despawn(entry.id, f"Idle timeout ({timeout_minutes}min)")
                despawned.append(entry.id)
                logger.info(f"Despawned idle agent: {entry.id}")
        return despawned
