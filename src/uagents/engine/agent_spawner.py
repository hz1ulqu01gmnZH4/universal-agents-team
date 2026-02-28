"""Resource-checked agent spawning with prompt composition.
Spec reference: Section 4.4 (spawn_agent), Section 18 (resource checks)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..models.agent import AgentRegistryEntry, AgentStatus
from ..models.base import generate_id
from ..models.capability import CapabilityAtom, ModelPreference
from ..models.domain import DomainConfig
from ..models.role import RoleComposition
from ..models.task import Task
from ..models.voice import VoiceAtom
from ..state.yaml_store import YamlStore
from .prompt_composer import ComposedPrompt, PromptComposer
from .resource_tracker import ResourceTracker


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
    ):
        self.prompt_composer = prompt_composer
        self.resource_tracker = resource_tracker
        self.yaml_store = yaml_store
        self.domain = domain
        self._agents_base = f"instances/{domain}/state/agents"

    def spawn(
        self,
        role: RoleComposition,
        task: Task,
        domain_config: DomainConfig,
        capabilities: dict[str, CapabilityAtom],
        voice_atoms: dict[str, VoiceAtom],
    ) -> tuple[AgentRegistryEntry, ComposedPrompt]:
        """Full spawn pipeline. Raises ResourceConstrainedError if blocked."""
        # 1-2. Resource check with 20% headroom (G1)
        can_spawn, reason = self.resource_tracker.can_spawn_agent()
        if not can_spawn:
            raise ResourceConstrainedError(f"Cannot spawn agent: {reason}")

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
            created_at=datetime.utcnow(),
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
        entry.updated_at = datetime.utcnow()
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
