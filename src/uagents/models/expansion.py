"""Self-expansion models for Phase 7.
Spec reference: Section 9.2 (Pressure Fields), Section 22 (Domain), Section 25 (Phase 7).

Review fixes applied:
- FM-P7-016: ScoutTarget/ScoutReport/PressureField/DomainSwitchRecord inherit from
  IdentifiableModel for consistency with codebase conventions (id, created_at, updated_at).
- FM-P7-017: Note on StrEnum + use_enum_values=True behavior documented.
- FM-P7-023: ScoutReport.performance_estimate bounded to [0.0, 1.0].
- FM-P7-045: DomainConfig.name validated with max length.
- DR-Issue-1: Archive path clarified (archive is at core level, cross-domain reads only).
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import Field

from .base import FrameworkModel, IdentifiableModel, generate_id


class ScoutTargetType(StrEnum):
    """What the scout should explore."""
    ARCHIVE_GAP = "archive_gap"           # Unexplored MAP-Elites cell
    STAGNATION_RESPONSE = "stagnation_response"  # Response to stagnation signal
    DIVERSITY_FLOOR = "diversity_floor"    # SRD/VDI below floor
    MANUAL = "manual"                      # Human-requested exploration


class ScoutStatus(StrEnum):
    """Scout lifecycle states.

    Note: FrameworkModel has use_enum_values=True. After validation,
    status is stored as the raw string (e.g. "completed"). StrEnum.__eq__
    allows comparison with ScoutStatus.COMPLETED. Do NOT use isinstance()
    checks on enum fields after model construction.
    """
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ScoutTarget(IdentifiableModel):
    """What a scout agent should explore.

    Produced by ScoutSpawner based on stagnation signals, archive gaps,
    or manual requests. Consumed by the orchestrator to create scout tasks.

    FM-P7-016-FIX: Inherits from IdentifiableModel (provides id, created_at,
    updated_at) for consistency with codebase conventions.
    """
    id: str = Field(default_factory=lambda: generate_id("stgt"))
    target_type: ScoutTargetType
    description: str
    # For ARCHIVE_GAP: the cell coordinates to explore.
    # FM-P7-DR-Issue-9: Validation of coords for ARCHIVE_GAP targets is done
    # at the ScoutSpawner level, not here — model allows empty strings for
    # non-ARCHIVE_GAP targets.
    task_type: str = ""
    complexity: str = ""
    # Priority: higher = more urgent
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # FM-P7-016-FIX: IdentifiableModel requires created_at at construction;
    # default_factory satisfies this. updated_at from TimestampedModel defaults to None.


class ScoutReport(IdentifiableModel):
    """Result from a scout exploration.

    Filed by the orchestrator after a scout task completes. Contains
    findings that may trigger evolution proposals or archive updates.

    FM-P7-016-FIX: Inherits from IdentifiableModel.
    FM-P7-023-FIX: performance_estimate bounded to [0.0, 1.0].
    """
    id: str = Field(default_factory=lambda: generate_id("srpt"))
    target_id: str  # References ScoutTarget.id
    scout_agent_id: str = ""
    status: ScoutStatus = ScoutStatus.COMPLETED
    findings: str = ""  # Free-text description of what was found
    recommendation: str = ""  # Suggested action
    # Behavioral coordinates for archive update
    task_type: str = ""
    complexity: str = ""
    # FM-P7-023-FIX: Bounded to prevent archive corruption from unbounded values
    performance_estimate: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PressureRegion(FrameworkModel):
    """A single region in a pressure field.

    Tracks which agents have explored this region and how saturated it is.
    Saturation decays exponentially over time.
    """
    name: str
    explored_by: list[str] = Field(default_factory=list)  # Agent IDs
    saturation: float = Field(default=0.0, ge=0.0, le=1.0)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PressureField(IdentifiableModel):
    """A stigmergic pressure field for indirect coordination.

    Spec reference: Section 9.2.
    Agents leave traces that influence other agents' behavior.
    Low-saturation regions attract exploration.

    FM-P7-016-FIX: Inherits from IdentifiableModel for id/timestamp consistency.
    """
    id: str = Field(default_factory=lambda: generate_id("pf"))
    name: str  # e.g., "exploration_pressure", "evolution_pressure"
    regions: list[PressureRegion] = Field(default_factory=list)
    # FM-P7-IMP-012-FIX: gt=0.0 prevents ZeroDivisionError in decay calculation
    decay_half_life_hours: float = Field(default=24.0, gt=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # updated_at inherited from TimestampedModel, defaults to None


class VoiceDefaults(FrameworkModel):
    """Domain-level voice atom defaults.

    Spec reference: Section 22.2 (voice_defaults in domain.yaml).
    DR-Issue-17-FIX: Strongly typed instead of bare dict[str, str | float].
    """
    description: str = ""
    language: str = ""       # e.g., "language_japanese"
    tone: str = ""           # e.g., "tone_precise"
    style: str = ""          # e.g., "style_technical"
    formality: float = Field(default=0.7, ge=0.0, le=1.0)
    verbosity: float = Field(default=0.5, ge=0.0, le=1.0)


class DomainConfig(FrameworkModel):
    """Configuration for a domain workspace.

    Spec reference: Section 22.2.
    Each domain has capabilities, review criteria, task types, and voice defaults.
    """
    name: str = Field(min_length=1, max_length=64)  # FM-P7-045-FIX: length limit
    description: str = ""
    capabilities: dict[str, dict] = Field(default_factory=dict)
    review_criteria: list[str] = Field(default_factory=list)
    task_types: list[str] = Field(default_factory=list)
    voice_defaults: VoiceDefaults = Field(default_factory=VoiceDefaults)  # DR-Issue-17-FIX


class DomainSwitchRecord(IdentifiableModel):
    """Record of a domain switch event.

    Logged to shared/domain-switches/ for audit trail.
    FM-P7-016-FIX: Inherits from IdentifiableModel.
    """
    id: str = Field(default_factory=lambda: generate_id("dsw"))
    from_domain: str
    to_domain: str
    parked_task_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""
