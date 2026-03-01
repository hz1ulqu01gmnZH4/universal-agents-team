"""Agent registry models.
Spec reference: Section 4.4 (spawn_agent function)."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from .base import IdentifiableModel
from .capability import ModelPreference
from .voice import VoiceProfile


class AgentStatus(StrEnum):
    ACTIVE = "active"
    IDLE = "idle"
    PARKED = "parked"
    DESPAWNED = "despawned"


class AgentRegistryEntry(IdentifiableModel):
    """A registered agent in the framework."""

    role: str
    model: ModelPreference
    voice_profile_hash: str
    status: AgentStatus
    current_task: str | None = None
    spawned_by: str
    estimated_cost: int
    team_name: str | None = None
    heartbeat_at: datetime | None = None  # Last activity timestamp
    subtask_id: str | None = None  # Assigned subtask within team
    voice: VoiceProfile | None = None  # Phase 2: Full voice profile for VDI computation
