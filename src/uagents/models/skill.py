"""Skill system data models.
Spec reference: Section 12 (Skill Lifecycle).

Phase 3: SkillStatus, ValidationStage, SkillSource, ValidationResult,
          SkillRecord, SkillLibraryStats, ExtractionCandidate,
          SkillMaintenanceAction, MaintenanceRecord.

Literature basis:
- SkillsBench (arXiv:2602.12670): Curated skills +16.2pp, self-generated negligible
- CASCADE (arXiv:2512.23880): 93.3% via execution-based validation
- SoK Agent Skills (arXiv:2602.20867): 26.1% vulnerability rate in community skills
- Li et al. 2026: Phase transition at critical library size
- ToolLibGen: Library maintenance prevents dead code accumulation
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import IntEnum, StrEnum
from typing import Literal

from pydantic import Field

from .base import FrameworkModel, IdentifiableModel, TimestampedModel, generate_id
from .capability import CapabilityAtom, ModelPreference, ThinkingSetting
from .protection import ProtectionRing


class SkillStatus(StrEnum):
    """Lifecycle states for a skill record.

    Flow: candidate -> validating -> stage_X_passed -> validated -> active
    Failure: candidate -> validating -> rejected
    Degradation: active -> deprecated
    """

    CANDIDATE = "candidate"            # Extracted, awaiting validation
    VALIDATING = "validating"          # Currently in validation pipeline
    STAGE_1_PASSED = "stage_1_passed"  # Syntax check passed
    STAGE_2_PASSED = "stage_2_passed"  # Execution test passed
    STAGE_3_PASSED = "stage_3_passed"  # Comparison test passed
    VALIDATED = "validated"            # All 4 stages passed, awaiting activation
    ACTIVE = "active"                  # In the skill library, available for use
    DEPRECATED = "deprecated"          # Pruned due to low performance or staleness
    REJECTED = "rejected"              # Failed validation at any stage
    QUARANTINED = "quarantined"        # MF-4: Security scan flagged, pending review


class ValidationStage(StrEnum):
    """The 4 validation stages from Section 12.2."""

    SYNTAX = "syntax"          # Stage 1: Well-formed CapabilityAtom?
    EXECUTION = "execution"    # Stage 2: Produces correct outputs on test tasks?
    COMPARISON = "comparison"  # Stage 3: Better than baseline and alternatives?
    REVIEW = "review"          # Stage 4: Human or senior agent review


class SkillSource(FrameworkModel):
    """Provenance record for an extracted skill.

    Tracks which task trajectory the skill was extracted from,
    ensuring full auditability (Section 17).
    """

    task_id: str                  # ID of the task that produced this skill
    task_title: str               # Human-readable title for audit display
    task_type: str                # From Orchestrator._classify_task_type()
    review_verdict: Literal["pass", "pass_with_notes"]  # Only extract from passing tasks
    reviewer_confidence: float = Field(ge=0.0, le=1.0)
    trajectory_snippet: str       # Key reasoning steps (truncated for storage)
    extraction_timestamp: datetime
    extraction_tokens: int = Field(ge=0, default=0)  # Tokens used for extraction


class ValidationResult(FrameworkModel):
    """Result of a single validation stage.

    Each stage produces one ValidationResult. The SkillRecord
    accumulates these as the candidate progresses through the pipeline.
    """

    stage: ValidationStage
    passed: bool
    score: float = Field(ge=0.0, le=1.0)  # Stage-specific score
    detail: str                            # Human-readable explanation
    tokens_used: int = Field(ge=0, default=0)
    timestamp: datetime
    # Stage 2: test task IDs used
    test_task_ids: list[str] = Field(default_factory=list)
    # Stage 3: improvement delta (percentage points)
    improvement_delta: float | None = None
    # Stage 4: reviewer identity
    reviewer: str | None = None


class SkillPerformanceMetrics(FrameworkModel):
    """Performance tracking for an active skill.

    Scoring formula (Section 12.4):
    composite = 0.4 * usage_frequency + 0.4 * success_rate + 0.2 * freshness

    FM-S10: All counters are bounded. usage_count wraps to rolling window.
    """

    usage_count: int = 0              # Times this skill was applied
    success_count: int = 0            # Times application led to task success
    last_used_task_id: str | None = None
    last_used_at: datetime | None = None
    tasks_since_last_use: int = 0     # Incremented by maintenance, reset on use


    @property
    def success_rate(self) -> float:
        """Success rate from usage history."""
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count

    @property
    def freshness(self) -> float:
        """Freshness score: 1.0 if recently used, decays toward 0.0.

        Uses tasks_since_last_use as proxy. Decay: 1.0 - (tasks_since / 30).
        Clamped to [0.0, 1.0].
        """
        if self.usage_count == 0:
            return 0.0
        decay = 1.0 - (self.tasks_since_last_use / 30.0)
        return max(0.0, min(1.0, decay))

    @property
    def composite_score(self) -> float:
        """Weighted composite score for maintenance ranking.

        Weights: usage_frequency=0.4, success_rate=0.4, freshness=0.2
        usage_frequency normalized to [0,1] via min(usage_count/10, 1.0).
        """
        usage_freq = min(self.usage_count / 10.0, 1.0)
        return (
            0.4 * usage_freq
            + 0.4 * self.success_rate
            + 0.2 * self.freshness
        )


class SkillRecord(IdentifiableModel):
    """Central skill model -- a validated capability atom with lifecycle metadata.

    A SkillRecord wraps a CapabilityAtom with:
    - Source provenance (which task trajectory it was extracted from)
    - Validation history (results of each stage)
    - Ring classification (trust tier)
    - Performance metrics (usage, success rate, freshness)
    - Lifecycle status

    Persisted to: instances/{domain}/state/skills/{skill_name}.yaml
    Spec reference: Section 12, Section 20 (Protection Rings).

    FM-S01: Only extracted from high-confidence passing tasks.
    FM-S05: Ring promotion requires evidence (>= +5pp improvement).
    FM-S09: Stale skills demoted on model drift (cross-ref Phase 2.5).

    Base class: IdentifiableModel (not TimestampedModel) because constructors
    pass id= explicitly. IdentifiableModel extends TimestampedModel extends
    FrameworkModel, so created_at/updated_at are still available.
    IFM-MF1: Fixed from TimestampedModel to IdentifiableModel.
    """

    # Core capability atom fields (inlined, not nested, for flat YAML)
    name: str
    description: str
    instruction_fragment: str
    model_preference: ModelPreference | None = None
    thinking: ThinkingSetting | None = None

    # Provenance
    source: SkillSource
    domain: str = "meta"

    # Validation
    status: SkillStatus = SkillStatus.CANDIDATE
    validation_results: list[ValidationResult] = Field(default_factory=list)

    # Trust tier
    ring: ProtectionRing = ProtectionRing.RING_3_EXPENDABLE

    # Performance
    metrics: SkillPerformanceMetrics = Field(
        default_factory=SkillPerformanceMetrics
    )

    # Version tracking
    version: int = 1
    previous_version_id: str | None = None  # For merge/update lineage

    def to_capability_atom(self) -> CapabilityAtom:
        """Convert to a CapabilityAtom for prompt injection.

        Used by Phase 3.5 dynamic tool loading to compose skills
        into role definitions.
        """
        return CapabilityAtom(
            name=self.name,
            description=self.description,
            instruction_fragment=self.instruction_fragment,
            model_preference=self.model_preference,
            thinking=self.thinking,
        )

    @property
    def is_active(self) -> bool:
        """True if skill is available for use."""
        return self.status == SkillStatus.ACTIVE.value

    @property
    def is_prunable(self) -> bool:
        """True if skill meets pruning criteria (Section 12.4).

        success_rate < 0.5 OR unused for 30 tasks -> deprecated.
        Ring 0 and Ring 1 skills are never prunable.
        Ring 2 IS prunable (can be demoted or pruned directly).
        MF-1: Previously Ring 2 was incorrectly protected from pruning.
        """
        if self.ring in (
            ProtectionRing.RING_0_IMMUTABLE.value,
            ProtectionRing.RING_1_PROTECTED.value,
        ):
            return False
        if not self.is_active:
            return False
        if self.metrics.usage_count == 0:
            return False  # Never used -- don't prune, just not yet tried
        if self.metrics.success_rate < 0.5:
            return True
        if self.metrics.tasks_since_last_use >= 30:
            return True
        return False

    @property
    def last_validation_stage(self) -> str | None:
        """Most recent validation stage completed."""
        if not self.validation_results:
            return None
        return self.validation_results[-1].stage


class ExtractionCandidate(IdentifiableModel):
    """Pre-validation skill candidate produced by SkillExtractor.

    Contains the raw extracted pattern before it enters the
    validation pipeline. Intermediate model -- not persisted long-term.

    Persisted temporarily to: instances/{domain}/state/skills/candidates/

    Base class: IdentifiableModel (not TimestampedModel) because constructors
    pass id= explicitly via generate_id("cand").
    IFM-MF1: Fixed from TimestampedModel to IdentifiableModel.
    """

    name: str
    description: str
    instruction_fragment: str
    source: SkillSource
    domain: str = "meta"
    model_preference: ModelPreference | None = None
    # SF-3: thinking field added for parity with SkillRecord
    thinking: ThinkingSetting | None = None

    def to_skill_record(self) -> SkillRecord:
        """Convert to a SkillRecord for validation pipeline entry."""
        now = datetime.now(timezone.utc)
        return SkillRecord(
            id=generate_id("skill"),
            created_at=now,
            name=self.name,
            description=self.description,
            instruction_fragment=self.instruction_fragment,
            source=self.source,
            domain=self.domain,
            model_preference=self.model_preference,
            thinking=self.thinking,  # SF-3: Pass through thinking setting
            status=SkillStatus.CANDIDATE,
            ring=ProtectionRing.RING_3_EXPENDABLE,
        )


class SkillMaintenanceAction(StrEnum):
    """Actions taken during periodic maintenance (Section 12.4)."""

    PRUNE = "prune"        # Remove low-performing skill
    MERGE = "merge"        # Consolidate near-duplicate skills
    PROMOTE = "promote"    # Ring 3 -> Ring 2
    DEMOTE = "demote"      # Ring 2 -> Ring 3
    QUARANTINE = "quarantine"  # MF-4: Security scan quarantine


class MaintenanceRecord(IdentifiableModel):
    """Record of a single maintenance action.

    Persisted to: instances/{domain}/state/skills/maintenance-history/

    Base class: IdentifiableModel (not TimestampedModel) because constructors
    pass id= explicitly via generate_id("maint").
    IFM-MF1: Fixed from TimestampedModel to IdentifiableModel.
    """

    action: SkillMaintenanceAction
    skill_name: str
    detail: str
    # For merge: the other skill that was merged into this one
    merged_with: str | None = None
    # For promote/demote: the ring transition
    from_ring: ProtectionRing | None = None
    to_ring: ProtectionRing | None = None
    # Performance snapshot at time of action
    composite_score: float = 0.0
    success_rate: float = 0.0
    usage_count: int = 0


class SkillLibraryStats(FrameworkModel):
    """Aggregate statistics for the skill library.

    Computed on demand by SkillLibrary.get_stats().
    Not persisted -- derived from current library state.
    """

    total_skills: int = 0
    active_skills: int = 0
    deprecated_skills: int = 0
    rejected_skills: int = 0
    validating_skills: int = 0
    candidate_skills: int = 0
    ring_0_count: int = 0
    ring_1_count: int = 0
    ring_2_count: int = 0
    ring_3_count: int = 0
    avg_success_rate: float = 0.0
    avg_composite_score: float = 0.0
    domains: dict[str, int] = Field(default_factory=dict)  # domain -> count
    maintenance_actions_total: int = 0
    last_maintenance_at: datetime | None = None
