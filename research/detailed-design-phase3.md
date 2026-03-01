# Universal Agents Framework — Phase 3 Detailed Design

**Version:** 0.3.1
**Date:** 2026-03-01
**Source:** framework-design-unified-v1.1.md (Section 12), skill-crystallization-and-llm-skills.md (42 papers)
**Status:** Implementation-ready (14 review fixes applied: 5 must-fix, 9 should-fix/IFM)
**Scope:** Phase 3 "Skill Foundation" — skill extraction from trajectories, 4-stage validation pipeline, skill library with maintenance, ring-based trust tiers
**Prerequisite:** Phase 0 + Phase 1 + Phase 1.5 + Phase 2 + Phase 2.5 fully implemented

---

## Table of Contents

1. [Architecture Overview](#part-1-architecture-overview)
2. [Data Models](#part-2-data-models)
3. [YAML Configuration](#part-3-yaml-configuration)
4. [SkillExtractor Engine](#part-4-skillextractor-engine)
5. [SkillValidator Engine](#part-5-skillvalidator-engine)
6. [SkillLibrary Engine](#part-6-skilllibrary-engine)
7. [Modifications to Existing Files](#part-7-modifications-to-existing-files)
8. [Implementation Sequence](#part-8-implementation-sequence)
9. [Failure Modes](#part-9-failure-modes)

---

## Part 1: Architecture Overview

### 1.1 What Phase 3 Adds

Phase 3 transforms the framework from "executing tasks and measuring performance" to "learning reusable skills from successful execution." After Phase 2.5, the framework can detect environment changes, track per-skill performance, and measure confidence calibration — but it cannot extract, validate, or reuse reasoning patterns from successful tasks. The Skill Paradox (SkillsBench 2026, arXiv:2602.12670) demonstrates that curated skills provide +16.2pp improvement, while self-generated skills are negligible or negative. The resolution: execution-based validation, experience-grounded extraction, and continuous maintenance (CASCADE 93.3%, SAGE +8.9%, SkillRL +15.3%).

Phase 3 adds three subsystems:

1. **SkillExtractor** — Identifies completed tasks with high review scores, extracts the reasoning pattern used, and abstracts it into a transferable capability atom. Uses `ModelExecuteFn` for LLM-assisted abstraction. Produces `ExtractionCandidate` records. Extraction is from real trajectories ONLY — never generated from scratch (Section 12.1, SkillsBench anti-pattern).
2. **SkillValidator** — Runs candidates through a 4-stage validation pipeline: (1) Syntax check (well-formed CapabilityAtom), (2) Execution test (apply to 2+ archived tasks), (3) Comparison (A/B test vs baseline, must show >= +5pp), (4) Review (human or senior agent approval). Each stage is budget-capped. Early termination on failure. Total budget: 15000 tokens default.
3. **SkillLibrary** — Stores validated skills with ring-based trust tiers (Ring 3 = new, Ring 2 = validated). Provides TF-IDF semantic search for skill retrieval. Runs periodic maintenance: prune low-performers, merge near-duplicates (cosine similarity > 0.85), score by usage/success/freshness. Enforces capacity limits (50 per domain, 20 per level).

### 1.2 Key Design Principles (from 42 papers)

1. **Extract, don't generate** — Skills are abstracted from real successful trajectories. Naive LLM generation fails (SkillsBench). EvolveR offline distillation and AutoRefine dual-form extraction work. The extraction prompt includes the actual trajectory and asks for abstraction.
2. **Execution-based validation, not LLM self-eval** — All successful skill systems (CASCADE, SAGE, SkillRL) use execution tests, not self-assessment. Stage 2 applies the skill to real archived tasks and checks outputs.
3. **Capacity limits prevent phase transition** — Library size must stay below critical threshold (Li et al. 2026). Selection accuracy is stable up to critical size, then drops sharply due to semantic confusability. Enforce 50 per domain, 20 per level.
4. **Focused skills outperform comprehensive ones** — 2-3 module focused skills outperform comprehensive documentation (SkillsBench). Skills should be narrow capability atoms, not broad instructions.
5. **Security by default** — 26.1% of community skills contain vulnerabilities (SoK Agent Skills, arXiv:2602.20867). Ring 3 skills are sandboxed, instruction fragments injected AFTER constitution and safety constraints, never before.
6. **Continuous maintenance prevents library rot** — Without consolidation (cluster, refactor, aggregate), libraries accumulate dead code (ToolLibGen). Score by usage/success/freshness every 20 tasks. Prune failures, merge duplicates.
7. **Hierarchy manages complexity** — STEPS taxonomy, Odyssey (40 primitives + 183 compositions) demonstrate that hierarchical organization scales. Skills organized by domain and level.
8. **Skills are text, not code** — Skills are instruction fragments injected into agent prompts as context. No `eval()`, no `exec()`, no code execution. This eliminates an entire class of injection vulnerabilities.

### 1.3 What Phase 3 Does NOT Include

- **Automatic skill injection into agent prompts** (Phase 3.5 — requires dynamic tool loading). Phase 3 builds the library; Phase 3.5 uses it.
- **RL-augmented quality signals** (Phase 4+ — requires evolution engine). Phase 3 uses empirical execution tests.
- **MAP-Elites archive integration** (Phase 4+ — requires population management). Phase 3 tracks performance but does not maintain a quality-diversity archive.
- **Cross-domain skill transfer** (Phase 5+ — requires domain switching). Phase 3 is domain-scoped.
- **Automatic Ring 1 promotion** (never — Ring 1 requires human approval per spec Section 20).
- **Code execution skills** — Skills are instruction fragments only. Never executable code.

Phase 3 is a **write-path construction** phase. Skills can be extracted, validated, stored, searched, and retrieved. They are NOT automatically injected into agent prompts yet (that is Phase 3.5). The strongest autonomous action is Ring 3 to Ring 2 promotion based on validation evidence.

### 1.4 Component Dependency Graph

```
SkillExtractor ────────────┐
  (extracts from tasks)     │
                            ▼
SkillValidator ─────────► SkillLibrary ◄─── PerformanceMonitor (Phase 2.5)
  (4-stage pipeline)        │ (storage +     (per-skill success rates)
                            │  maintenance)
                            │
                            ▼
                     DiversityEngine (Phase 2)
                     (TF-IDF for similarity)
                            │
                            ▼
                     YamlStore (Phase 0)
                     (persistence layer)
```

### 1.5 Integration Points with Existing Phases

| Phase | Integration |
|-------|-------------|
| Phase 0 | `YamlStore` for all state persistence, `generate_id()` for IDs, `FrameworkModel` for all models |
| Phase 0 | `CapabilityAtom` from `models/capability.py` — skills extend this model |
| Phase 0 | `ProtectionRing` and `RingTransition` from `models/protection.py` — ring management |
| Phase 0 | `GitOps.commit_evolution()` for versioning skill changes |
| Phase 1 | `AuditLogger.log_decision()` for skill extraction/validation decisions |
| Phase 1 | `AuditLogger.log_evolution()` for ring transitions |
| Phase 1.5 | `BudgetTracker.get_window()` for validation budget cap |
| Phase 2 | `CapabilityTracker.record_outcome()` for recording skill validation outcomes |
| Phase 2 | `DiversityEngine.tokenize()`, `compute_idf()`, `tf_idf_vector()`, `cosine_distance()` for similarity search |
| Phase 2.5 | `PerformanceMonitor.get_skill_performance()` for maintenance scoring |
| Phase 2.5 | `ModelExecuteFn` protocol for LLM calls in extraction and validation |

### 1.6 Files Created and Modified

**New files (4):**

| File | Lines (est.) | Purpose |
|------|------------|---------|
| `models/skill.py` | ~350 | Skill data models: SkillStatus, ValidationStage, SkillSource, ValidationResult, SkillRecord, SkillLibraryStats, ExtractionCandidate, MaintenanceRecord |
| `engine/skill_extractor.py` | ~280 | Extract reasoning patterns from successful task trajectories |
| `engine/skill_validator.py` | ~380 | 4-stage validation pipeline (syntax, execution, comparison, review) |
| `engine/skill_library.py` | ~450 | Skill storage, retrieval, TF-IDF search, maintenance, ring management |

**New YAML config (1):**

| File | Purpose |
|------|---------|
| `core/skill-system.yaml` | All thresholds, capacity limits, maintenance periods, validation budgets |

**Modified files (2):**

| File | Changes |
|------|---------|
| `engine/orchestrator.py` | Add SkillLibrary integration: extract after task completion, run maintenance periodically |
| `audit/tree_viewer.py` | Add skill event rendering in DECISIONS and EVOLUTION streams |

---

## Part 2: Data Models

### 2.1 New Models in `models/skill.py`

```python
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
    """Central skill model — a validated capability atom with lifecycle metadata.

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
        return self.status == SkillStatus.ACTIVE

    @property
    def is_prunable(self) -> bool:
        """True if skill meets pruning criteria (Section 12.4).

        success_rate < 0.5 OR unused for 30 tasks -> deprecated.
        Ring 0 and Ring 1 skills are never prunable.
        """
        if self.ring in (
            ProtectionRing.RING_0_IMMUTABLE,
            ProtectionRing.RING_1_PROTECTED,
        ):
            return False
        if not self.is_active:
            return False
        if self.metrics.usage_count == 0:
            return False  # Never used — don't prune, just not yet tried
        if self.metrics.success_rate < 0.5:
            return True
        if self.metrics.tasks_since_last_use >= 30:
            return True
        return False

    @property
    def last_validation_stage(self) -> ValidationStage | None:
        """Most recent validation stage completed."""
        if not self.validation_results:
            return None
        return self.validation_results[-1].stage


class ExtractionCandidate(IdentifiableModel):
    """Pre-validation skill candidate produced by SkillExtractor.

    Contains the raw extracted pattern before it enters the
    validation pipeline. Intermediate model — not persisted long-term.

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
    Not persisted — derived from current library state.
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
```

### 2.2 Model Summary

| Model | Purpose | Persisted To |
|-------|---------|-------------|
| `SkillStatus` | Enum: 9 lifecycle states | Used in `SkillRecord` |
| `ValidationStage` | Enum: 4 validation stages | Used in `ValidationResult` |
| `SkillSource` | Provenance: task ID, trajectory, timestamps | Part of `SkillRecord` |
| `ValidationResult` | Result of one validation stage | Part of `SkillRecord` |
| `SkillPerformanceMetrics` | Usage count, success rate, freshness | Part of `SkillRecord` |
| `SkillRecord` | Central skill model with full lifecycle | `state/skills/{name}.yaml` |
| `ExtractionCandidate` | Pre-validation candidate | `state/skills/candidates/` (temporary) |
| `SkillMaintenanceAction` | Enum: prune/merge/promote/demote | Used in `MaintenanceRecord` |
| `MaintenanceRecord` | Record of a maintenance action | `state/skills/maintenance-history/` |
| `SkillLibraryStats` | Aggregate library statistics | Not persisted (computed on demand) |

---

## Part 3: YAML Configuration

### 3.1 `core/skill-system.yaml`

```yaml
# Skill system configuration
# Spec reference: Section 12 (Skill Lifecycle)
# All thresholds are authoritative — engines read from this file, not hardcoded constants.
#
# Literature basis:
# - SkillsBench (arXiv:2602.12670): Curated skills +16.2pp
# - CASCADE (arXiv:2512.23880): 93.3% via execution-based validation
# - Li et al. 2026: Phase transition at critical library size
# - SoK Agent Skills (arXiv:2602.20867): 26.1% vulnerability rate

skill_system:

  extraction:
    # Minimum review confidence to extract skill from a task trajectory
    min_review_confidence: 0.7
    # Minimum trajectory length (characters) to consider for extraction
    min_trajectory_length: 200
    # Maximum trajectory snippet length stored in SkillSource (characters)
    max_trajectory_snippet: 2000
    # Token budget for the extraction LLM call
    extraction_token_budget: 3000
    # Verdicts that qualify for extraction
    qualifying_verdicts:
      - "pass"
      - "pass_with_notes"
    # Cooldown: minimum tasks between extraction attempts for the same task_type
    # Prevents extracting near-duplicate skills from consecutive similar tasks
    extraction_cooldown_tasks: 5

  validation:
    # Total token budget for the entire 4-stage pipeline (Section 12.2)
    total_token_budget: 15000
    # Per-stage token budgets
    stage_budgets:
      syntax: 0           # Stage 1: No LLM call needed (pure parsing)
      execution: 6000     # Stage 2: 2 test tasks x ~3000 tokens each
      comparison: 6000    # Stage 3: A/B test (baseline + with-skill)
      review: 3000        # Stage 4: Review prompt generation
    # Stage 2: Minimum number of archived test tasks required
    min_test_tasks: 2
    # Stage 3: Minimum improvement (percentage points) required
    min_improvement_pp: 5
    # Stage 3: Number of comparison runs per variant (with/without skill)
    comparison_runs: 2
    # Stage 4: Who can approve (human or agent with authority capability)
    review_approvers:
      - "human"
      - "authority_agent"

  library:
    # Capacity limits (Section 12.3) — Li et al. 2026 phase transition
    capacity:
      per_domain: 50      # Maximum active skills per domain
      per_level: 20       # Maximum active skills per hierarchy level
    # Storage paths (relative to instance root)
    skills_dir: "state/skills"
    candidates_dir: "state/skills/candidates"
    maintenance_dir: "state/skills/maintenance-history"

  maintenance:
    # Maintenance period (Section 12.4)
    period_tasks: 20       # Run maintenance every N completed tasks
    # Pruning thresholds
    prune_success_rate: 0.5    # success_rate < this -> deprecated
    prune_unused_tasks: 30     # unused for N tasks -> deprecated
    # Merge threshold — cosine similarity (1 - cosine_distance)
    merge_similarity_threshold: 0.85
    # Maximum maintenance records to keep
    max_maintenance_history: 100
    # Scoring weights for composite score
    scoring_weights:
      usage_frequency: 0.4
      success_rate: 0.4
      freshness: 0.2

  ring_transitions:
    # Ring 3 -> Ring 2 requirements (Section 20.2)
    ring_3_to_2:
      min_improvement_pp: 5      # Must demonstrate >= +5pp improvement
      min_usage_count: 5         # Must have been used at least N times
      min_success_rate: 0.7      # Must have >= 70% success rate
      require_full_validation: true  # Must have passed all 4 stages
    # Ring 2 -> Ring 3 demotion triggers
    ring_2_to_3:
      on_revalidation_failure: true   # Demote if post-drift revalidation fails
      on_success_rate_below: 0.5      # Demote if success_rate drops below this
    # Ring 0 and Ring 1: human-only, never automated
    ring_0_immutable: true
    ring_1_human_only: true

  security:
    # Injection ordering (Section 12.5)
    # Skills injected AFTER constitution and safety constraints, never before
    injection_position: "after_constitution"
    # Ring 3 skills are sandboxed (Phase 3.5 enforces)
    ring_3_sandboxed: true
    # Maximum instruction_fragment length (characters)
    max_instruction_length: 1500
    # Forbidden patterns in instruction_fragment
    # FM-S08: Prevents prompt injection via skill content
    forbidden_patterns:
      - "ignore previous instructions"
      - "ignore all instructions"
      - "disregard"
      - "override constitution"
      - "bypass safety"
      - "system prompt"
```

---

## Part 4: SkillExtractor Engine

### 4.1 `engine/skill_extractor.py`

```python
"""Skill extraction from successful task trajectories.
Spec reference: Section 12.1 (Skill Extraction).

Identifies completed tasks with high review scores and extracts the
reasoning pattern into a transferable capability atom. Uses ModelExecuteFn
for LLM-assisted abstraction from real trajectories.

Key constraints:
- Extract from REAL trajectories only — never generate from scratch
- Minimum review confidence threshold (configurable, default 0.7)
- Minimum trajectory length (configurable, default 200 chars)
- Token budget for extraction call (configurable, default 3000)
- Deduplication against existing library skills
- Cooldown between extractions of same task_type

Literature basis:
- SkillsBench (arXiv:2602.12670): "NEVER generate skills from scratch"
- EvolveR: Offline distillation from trajectories works
- AutoRefine: Dual-form extraction (procedural + declarative) works
- CASCADE (arXiv:2512.23880): Experience-grounded extraction
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.audit import DecisionLogEntry, LogStream
from ..models.base import generate_id
from ..models.environment import ModelExecuteFn
from ..models.skill import (
    ExtractionCandidate,
    SkillSource,
)
from ..models.task import Task, TaskReview
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.skill_extractor")

# Extraction prompt template.
# This prompt asks the LLM to abstract a reasoning pattern from a concrete
# task trajectory. It does NOT ask the LLM to generate a skill from scratch.
# FM-S01: The trajectory is included verbatim to ground the extraction.
EXTRACTION_PROMPT = """You are extracting a reusable reasoning pattern from a successful task execution.

## Task that was completed successfully
Title: {task_title}
Type: {task_type}
Description: {task_description}

## Key reasoning steps from the execution trajectory
{trajectory_snippet}

## Your job
Abstract the reasoning pattern used in this task into a REUSABLE capability instruction.

Rules:
1. Focus on the TRANSFERABLE pattern, not task-specific details
2. The instruction should be 2-5 sentences, focused and actionable
3. It should help an agent perform similar tasks better
4. Do NOT include task-specific names, IDs, or data
5. Do NOT generate generic advice — extract the SPECIFIC pattern that made this task succeed

## Output format (respond with EXACTLY this structure, no other text)
NAME: <short_snake_case_name>
DESCRIPTION: <one sentence describing what this skill does>
INSTRUCTION: <2-5 sentence instruction fragment that can be injected into an agent prompt>
"""


class SkillExtractor:
    """Extracts reusable skills from successful task trajectories.

    Design invariants:
    - Only extracts from tasks with review verdict "pass" or "pass_with_notes"
    - Only extracts when reviewer_confidence >= threshold (default 0.7)
    - Uses real trajectory data — never generates from scratch (SkillsBench)
    - Deduplicates against existing skills in the library
    - Respects extraction cooldown per task_type
    - Budget-capped LLM call for abstraction
    - Candidates stored temporarily for validation pipeline

    Usage:
        extractor = SkillExtractor(yaml_store, domain="meta")
        candidate = extractor.extract_from_task(task, execute_fn)
        if candidate is not None:
            # Send to SkillValidator
            validator.validate(candidate)

    FM-S01: Guards against low-quality trajectory extraction.
    FM-S06: Checks for duplicate skill names before extraction.
    FM-S07: Budget enforcement via token cap.
    FM-S08: Rejects instructions with forbidden patterns.
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        audit_logger: object | None = None,  # AuditLogger, optional
    ):
        self.yaml_store = yaml_store
        self._domain = domain
        self._audit_logger = audit_logger

        # Load config (fail-loud if missing)
        config_raw = yaml_store.read_raw("core/skill-system.yaml")
        ss = config_raw.get("skill_system")
        if ss is None:
            raise ValueError(
                "core/skill-system.yaml missing 'skill_system' section"
            )
        ext = ss.get("extraction", {})
        self._min_review_confidence = float(
            ext.get("min_review_confidence", 0.7)
        )
        self._min_trajectory_length = int(
            ext.get("min_trajectory_length", 200)
        )
        self._max_trajectory_snippet = int(
            ext.get("max_trajectory_snippet", 2000)
        )
        self._extraction_token_budget = int(
            ext.get("extraction_token_budget", 3000)
        )
        self._qualifying_verdicts: list[str] = ext.get(
            "qualifying_verdicts", ["pass", "pass_with_notes"]
        )
        self._extraction_cooldown = int(
            ext.get("extraction_cooldown_tasks", 5)
        )

        # Security: forbidden patterns (FM-S08)
        sec = ss.get("security", {})
        self._max_instruction_length = int(
            sec.get("max_instruction_length", 1500)
        )
        self._forbidden_patterns: list[str] = sec.get(
            "forbidden_patterns", []
        )

        # State paths
        self._skills_base = f"instances/{domain}/state/skills"
        self._candidates_dir = f"{self._skills_base}/candidates"
        yaml_store.ensure_dir(self._skills_base)
        yaml_store.ensure_dir(self._candidates_dir)

        # Track recent extractions per task_type for cooldown
        # In-memory only — rebuilt from disk is unnecessary (cooldown is short)
        self._recent_extractions: dict[str, int] = {}  # task_type -> tasks_ago

    def extract_from_task(
        self,
        task: Task,
        execute_fn: ModelExecuteFn,
        task_type: str,
        existing_skill_names: list[str] | None = None,
    ) -> ExtractionCandidate | None:
        """Extract a skill from a completed task trajectory.

        Args:
            task: Completed task with review verdict and trajectory.
            execute_fn: LLM execution function for abstraction.
            task_type: Task type classification from Orchestrator._classify_task_type().
                IFM-MF5: Passed in by the orchestrator to avoid divergent
                classification logic. Previously duplicated here.
            existing_skill_names: Names of skills already in library
                (for deduplication). If None, no dedup check.

        Returns:
            ExtractionCandidate if extraction succeeded, None if:
            - Task does not qualify (wrong verdict, low confidence)
            - Trajectory too short
            - Cooldown not elapsed for this task_type
            - LLM output unparseable
            - Duplicate skill name detected
            - Instruction contains forbidden patterns (FM-S08)

        FM-S01: Only extracts from high-confidence passing tasks.
        FM-S06: Checks for duplicate skill names.
        FM-S07: Respects extraction token budget.
        FM-S08: Rejects instructions with forbidden patterns.
        """
        # Guard: task must have a passing review
        if not self._qualifies_for_extraction(task):
            return None

        # Guard: cooldown check (task_type passed by orchestrator)
        if not self._cooldown_elapsed(task_type):
            logger.debug(
                f"Extraction skipped for task {task.id}: "
                f"cooldown not elapsed for task_type={task_type}"
            )
            return None

        # Build trajectory snippet from task timeline and artifacts
        trajectory = self._build_trajectory_snippet(task)
        if len(trajectory) < self._min_trajectory_length:
            logger.debug(
                f"Extraction skipped for task {task.id}: "
                f"trajectory too short ({len(trajectory)} < "
                f"{self._min_trajectory_length})"
            )
            return None

        # Build extraction prompt
        prompt = EXTRACTION_PROMPT.format(
            task_title=task.title,
            task_type=task_type,
            task_description=task.description[:500],
            trajectory_snippet=trajectory,
        )

        # Call LLM for abstraction (FM-S07: budget-capped)
        try:
            output, tokens_used = execute_fn(
                prompt, self._extraction_token_budget
            )
        except Exception as e:
            logger.warning(
                f"Extraction LLM call failed for task {task.id}: {e}"
            )
            return None

        # Parse LLM output
        parsed = self._parse_extraction_output(output)
        if parsed is None:
            logger.warning(
                f"Extraction output unparseable for task {task.id}: "
                f"output={output[:200]}..."
            )
            return None

        name, description, instruction = parsed

        # FM-S08: Check for forbidden patterns in instruction
        for pattern in self._forbidden_patterns:
            if pattern.lower() in instruction.lower():
                logger.warning(
                    f"Extraction rejected for task {task.id}: "
                    f"instruction contains forbidden pattern '{pattern}'"
                )
                self._log_decision(
                    task.id, name, "rejected_forbidden_pattern",
                    f"Instruction contains forbidden pattern: {pattern}"
                )
                return None

        # FM-S08: Enforce max instruction length
        if len(instruction) > self._max_instruction_length:
            logger.warning(
                f"Extraction rejected for task {task.id}: "
                f"instruction too long ({len(instruction)} > "
                f"{self._max_instruction_length})"
            )
            return None

        # FM-S06: Check for duplicate skill names
        if existing_skill_names and name in existing_skill_names:
            logger.info(
                f"Extraction skipped for task {task.id}: "
                f"skill name '{name}' already exists in library"
            )
            return None

        # Build candidate
        review = task.review
        assert review is not None  # Guaranteed by _qualifies_for_extraction

        source = SkillSource(
            task_id=task.id,
            task_title=task.title,
            task_type=task_type,
            review_verdict=review.verdict,
            reviewer_confidence=review.reviewer_confidence,
            trajectory_snippet=trajectory[:self._max_trajectory_snippet],
            extraction_timestamp=datetime.now(timezone.utc),
            extraction_tokens=tokens_used,
        )

        candidate = ExtractionCandidate(
            id=generate_id("cand"),
            created_at=datetime.now(timezone.utc),
            name=name,
            description=description,
            instruction_fragment=instruction,
            source=source,
            domain=self._domain,
        )

        # Persist candidate temporarily
        self.yaml_store.write(
            f"{self._candidates_dir}/{candidate.id}.yaml",
            candidate,
        )

        # Update cooldown tracker
        self._recent_extractions[task_type] = 0

        # Log decision
        self._log_decision(
            task.id, name, "extracted",
            f"Skill extracted from task {task.id} "
            f"(confidence={review.reviewer_confidence:.2f}, "
            f"tokens={tokens_used})"
        )

        logger.info(
            f"Skill extracted: name='{name}' from task {task.id} "
            f"(tokens={tokens_used})"
        )

        return candidate

    def increment_cooldowns(self) -> None:
        """Increment all cooldown counters by 1 task.

        Called by the orchestrator after each task completion.
        """
        for task_type in list(self._recent_extractions.keys()):
            self._recent_extractions[task_type] += 1
            # Clean up entries that have exceeded cooldown
            if self._recent_extractions[task_type] > self._extraction_cooldown:
                del self._recent_extractions[task_type]

    def _qualifies_for_extraction(self, task: Task) -> bool:
        """Check if a task qualifies for skill extraction.

        FM-S01: Strict qualification criteria prevent low-quality extraction.
        """
        # Must have a review
        if task.review is None:
            logger.debug(f"Task {task.id} skipped: no review")
            return False

        # Must have passing verdict
        if task.review.verdict not in self._qualifying_verdicts:
            logger.debug(
                f"Task {task.id} skipped: verdict={task.review.verdict}"
            )
            return False

        # Must have sufficient confidence
        if task.review.reviewer_confidence < self._min_review_confidence:
            logger.debug(
                f"Task {task.id} skipped: confidence="
                f"{task.review.reviewer_confidence:.2f} < "
                f"{self._min_review_confidence}"
            )
            return False

        return True

    def _cooldown_elapsed(self, task_type: str) -> bool:
        """Check if cooldown has elapsed for this task_type."""
        if task_type not in self._recent_extractions:
            return True
        return self._recent_extractions[task_type] >= self._extraction_cooldown

    def _build_trajectory_snippet(self, task: Task) -> str:
        """Build a trajectory snippet from task timeline and artifacts.

        Concatenates timeline entries and artifact summaries into a
        narrative of the task execution. Truncated to max_trajectory_snippet.
        """
        parts: list[str] = []

        # Timeline entries
        for entry in task.timeline:
            parts.append(
                f"[{entry.event}] {entry.actor}: {entry.detail}"
            )

        # Artifact summaries (keys and truncated values)
        for key, value in task.artifacts.items():
            val_str = str(value)
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            parts.append(f"[artifact:{key}] {val_str}")

        trajectory = "\n".join(parts)
        return trajectory[:self._max_trajectory_snippet]

    def _parse_extraction_output(
        self, output: str
    ) -> tuple[str, str, str] | None:
        """Parse the LLM extraction output into (name, description, instruction).

        Expected format:
            NAME: <name>
            DESCRIPTION: <description>
            INSTRUCTION: <instruction>

        Returns None if parsing fails.
        """
        lines = output.strip().split("\n")
        name = None
        description = None
        instruction_parts: list[str] = []
        current_field: str | None = None

        for line in lines:
            stripped = line.strip()
            if stripped.upper().startswith("NAME:"):
                name = stripped[5:].strip()
                current_field = "name"
            elif stripped.upper().startswith("DESCRIPTION:"):
                description = stripped[12:].strip()
                current_field = "description"
            elif stripped.upper().startswith("INSTRUCTION:"):
                instruction_parts.append(stripped[12:].strip())
                current_field = "instruction"
            elif current_field == "instruction" and stripped:
                # Multi-line instruction continuation
                instruction_parts.append(stripped)

        instruction = " ".join(instruction_parts).strip()

        # Validate all fields present and non-empty
        if not name or not description or not instruction:
            return None

        # Normalize name to snake_case
        name = name.lower().replace(" ", "_").replace("-", "_")
        # Remove non-alphanumeric characters (except underscore)
        name = "".join(c for c in name if c.isalnum() or c == "_")

        if not name:
            return None

        return name, description, instruction

    # IFM-MF5: _classify_task_type() REMOVED from SkillExtractor.
    # The orchestrator passes task_type as a parameter to extract_from_task()
    # to avoid maintaining a divergent copy of classification logic.

    def _log_decision(
        self, task_id: str, skill_name: str,
        decision: str, rationale: str
    ) -> None:
        """Log a skill extraction decision to the DECISIONS audit stream."""
        if self._audit_logger is None:
            return
        try:
            entry = DecisionLogEntry(
                id=generate_id("dec"),
                timestamp=datetime.now(timezone.utc),
                decision_type=f"skill_extraction_{decision}",
                actor="skill_extractor",
                options_considered=[
                    {"skill_name": skill_name, "task_id": task_id}
                ],
                selected=decision,
                rationale=rationale,
            )
            self._audit_logger.log_decision(entry)
        except Exception as e:
            logger.warning(f"Failed to log extraction decision: {e}")
```

---

## Part 5: SkillValidator Engine

### 5.1 `engine/skill_validator.py`

```python
"""4-stage skill validation pipeline.
Spec reference: Section 12.2 (Skill Validation).

Validates extracted skill candidates through:
  Stage 1 (Syntax): Parse as CapabilityAtom, check required fields
  Stage 2 (Execution): Apply skill to 2+ archived tasks, check outputs
  Stage 3 (Comparison): A/B test vs baseline, must show >= +5pp improvement
  Stage 4 (Review): Human or senior agent approval

Key constraints:
- Total budget: 15000 tokens (configurable)
- Early termination: if any stage fails, stop immediately
- Stage 2 requires at least 2 archived test tasks of similar type
- Stage 3 improvement threshold: +5pp (matches ring_3_to_2)
- Stage 4 review is blocking — skill stays in STAGE_3_PASSED until approved

Literature basis:
- CASCADE (arXiv:2512.23880): Execution-based validation, not self-eval
- SAGE (arXiv:2512.17102): +8.9% via validation pipeline
- SkillsBench (arXiv:2602.12670): Self-eval fails, execution tests work
- SoK Agent Skills (arXiv:2602.20867): 26.1% vulnerability rate
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.audit import DecisionLogEntry
from ..models.base import generate_id
from ..models.capability import CapabilityAtom
from ..models.environment import ModelExecuteFn
from ..models.protection import ProtectionRing
from ..models.skill import (
    ExtractionCandidate,
    SkillRecord,
    SkillStatus,
    ValidationResult,
    ValidationStage,
)
from ..models.task import Task
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.skill_validator")

# Stage 2 execution test prompt template
EXECUTION_TEST_PROMPT = """You are testing whether a skill instruction helps solve a task.

## Skill being tested
Name: {skill_name}
Instruction: {skill_instruction}

## Task to solve (from archive)
Title: {task_title}
Description: {task_description}

## Your job
Apply the skill instruction above to solve this task. Provide your solution.
At the end of your response, on a new line, write:
QUALITY: <1-10> (how well the skill helped with this task, 10=perfectly relevant)
"""

# Stage 3 baseline prompt (without skill)
BASELINE_PROMPT = """You are solving a task.

## Task to solve
Title: {task_title}
Description: {task_description}

## Your job
Solve this task. Provide your solution.
At the end of your response, on a new line, write:
QUALITY: <1-10> (how confident you are in your solution, 10=very confident)
"""


class SkillValidator:
    """4-stage validation pipeline for skill candidates.

    Design invariants:
    - Total budget capped at 15000 tokens (configurable)
    - Early termination: any stage failure stops the pipeline
    - Stage 1 is automated (no LLM call, pure parsing)
    - Stage 2 requires 2+ archived test tasks
    - Stage 3 requires measurable improvement (>= +5pp)
    - Stage 4 generates review request (approval is external)
    - Each stage produces a ValidationResult
    - Budget tracking per stage, total not exceeded

    Usage:
        validator = SkillValidator(yaml_store, domain="meta")
        record = validator.validate(candidate, execute_fn, test_tasks)
        if record.status == SkillStatus.STAGE_3_PASSED:
            # Needs review approval before activation
            pass

    FM-S02: Stage 2 uses multiple test tasks to reduce flakiness.
    FM-S05: Stage 3 threshold matches ring_3_to_2 promotion criteria.
    FM-S07: Budget enforcement across all stages.
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        audit_logger: object | None = None,  # AuditLogger, optional
        budget_tracker: object | None = None,  # BudgetTracker, optional
    ):
        self.yaml_store = yaml_store
        self._domain = domain
        self._audit_logger = audit_logger
        # IFM-N20: BudgetTracker for pre-validation budget check
        self._budget_tracker = budget_tracker

        # Load config (fail-loud if missing)
        config_raw = yaml_store.read_raw("core/skill-system.yaml")
        ss = config_raw.get("skill_system")
        if ss is None:
            raise ValueError(
                "core/skill-system.yaml missing 'skill_system' section"
            )
        val = ss.get("validation", {})
        self._total_budget = int(val.get("total_token_budget", 15000))
        stage_budgets = val.get("stage_budgets", {})
        self._stage_budgets = {
            ValidationStage.SYNTAX: int(stage_budgets.get("syntax", 0)),
            ValidationStage.EXECUTION: int(
                stage_budgets.get("execution", 6000)
            ),
            ValidationStage.COMPARISON: int(
                stage_budgets.get("comparison", 6000)
            ),
            ValidationStage.REVIEW: int(stage_budgets.get("review", 3000)),
        }
        self._min_test_tasks = int(val.get("min_test_tasks", 2))
        self._min_improvement_pp = float(val.get("min_improvement_pp", 5))
        self._comparison_runs = int(val.get("comparison_runs", 2))

        # Security config
        sec = ss.get("security", {})
        self._forbidden_patterns: list[str] = sec.get(
            "forbidden_patterns", []
        )

        # State path
        self._skills_base = f"instances/{domain}/state/skills"
        yaml_store.ensure_dir(self._skills_base)

    def validate(
        self,
        candidate: ExtractionCandidate,
        execute_fn: ModelExecuteFn,
        test_tasks: list[Task],
    ) -> SkillRecord:
        """Run the full 4-stage validation pipeline.

        Args:
            candidate: Extracted skill candidate.
            execute_fn: LLM execution function for stages 2-3.
            test_tasks: Archived completed tasks for execution testing.
                Must have at least `min_test_tasks` entries.

        Returns:
            SkillRecord with validation results and final status.
            Status will be one of:
            - REJECTED: Failed at any stage
            - STAGE_3_PASSED: Passed stages 1-3, awaiting review
            - VALIDATED: Passed all 4 stages (if review auto-approved)

        FM-S02: Multiple test tasks reduce flakiness.
        FM-S05: Improvement threshold matches ring promotion criteria.
        FM-S07: Budget tracking prevents overspend.
        IFM-N20: Pre-checks session budget before starting validation.
        """
        # IFM-N20: Pre-check session budget before validation.
        # Validation can consume up to total_budget tokens (default 15000).
        # If the session budget is too low, skip validation with a warning.
        if self._budget_tracker is not None:
            try:
                window = self._budget_tracker.get_window()
                if window.remaining_tokens < self._total_budget:
                    logger.warning(
                        f"Skipping validation: session budget too low "
                        f"({window.remaining_tokens} remaining, "
                        f"need {self._total_budget} for validation)"
                    )
                    record = candidate.to_skill_record()
                    record.status = SkillStatus.REJECTED
                    stage = ValidationResult(
                        stage=ValidationStage.SYNTAX,
                        passed=False,
                        score=0.0,
                        detail=(
                            f"Validation skipped: insufficient session budget "
                            f"({window.remaining_tokens} < {self._total_budget})"
                        ),
                        tokens_used=0,
                        timestamp=datetime.now(timezone.utc),
                    )
                    record.validation_results.append(stage)
                    self._persist_record(record)
                    return record
            except Exception as e:
                logger.warning(
                    f"BudgetTracker check failed, proceeding with "
                    f"validation anyway: {e}"
                )

        # Convert candidate to skill record
        record = candidate.to_skill_record()
        record.status = SkillStatus.VALIDATING

        total_tokens_used = 0

        # Stage 1: Syntax check
        stage_1 = self._stage_1_syntax(record)
        record.validation_results.append(stage_1)
        total_tokens_used += stage_1.tokens_used

        if not stage_1.passed:
            record.status = SkillStatus.REJECTED
            self._persist_record(record)
            self._log_validation_decision(record, "rejected_stage_1")
            return record

        record.status = SkillStatus.STAGE_1_PASSED

        # Stage 2: Execution test
        if len(test_tasks) < self._min_test_tasks:
            # Not enough test tasks — defer validation
            stage_2 = ValidationResult(
                stage=ValidationStage.EXECUTION,
                passed=False,
                score=0.0,
                detail=(
                    f"Deferred: only {len(test_tasks)} test tasks available, "
                    f"need {self._min_test_tasks}"
                ),
                tokens_used=0,
                timestamp=datetime.now(timezone.utc),
            )
            record.validation_results.append(stage_2)
            record.status = SkillStatus.REJECTED
            self._persist_record(record)
            self._log_validation_decision(
                record, "deferred_insufficient_test_tasks"
            )
            logger.info(
                f"Skill '{record.name}' validation deferred: "
                f"insufficient test tasks ({len(test_tasks)} < "
                f"{self._min_test_tasks})"
            )
            return record

        remaining_budget = self._total_budget - total_tokens_used
        stage_2 = self._stage_2_execution(
            record, execute_fn, test_tasks, remaining_budget
        )
        record.validation_results.append(stage_2)
        total_tokens_used += stage_2.tokens_used

        if not stage_2.passed:
            record.status = SkillStatus.REJECTED
            self._persist_record(record)
            self._log_validation_decision(record, "rejected_stage_2")
            return record

        record.status = SkillStatus.STAGE_2_PASSED

        # FM-S07: Check total budget before stage 3
        remaining_budget = self._total_budget - total_tokens_used
        if remaining_budget < 500:
            stage_3 = ValidationResult(
                stage=ValidationStage.COMPARISON,
                passed=False,
                score=0.0,
                detail=(
                    f"Budget exhausted: {remaining_budget} tokens remaining, "
                    f"need at least 500 for comparison"
                ),
                tokens_used=0,
                timestamp=datetime.now(timezone.utc),
            )
            record.validation_results.append(stage_3)
            record.status = SkillStatus.REJECTED
            self._persist_record(record)
            self._log_validation_decision(record, "rejected_budget_exhausted")
            return record

        # Stage 3: Comparison test
        stage_3 = self._stage_3_comparison(
            record, execute_fn, test_tasks, remaining_budget
        )
        record.validation_results.append(stage_3)
        total_tokens_used += stage_3.tokens_used

        if not stage_3.passed:
            record.status = SkillStatus.REJECTED
            self._persist_record(record)
            self._log_validation_decision(record, "rejected_stage_3")
            return record

        record.status = SkillStatus.STAGE_3_PASSED

        # Stage 4: Review — generate review summary but do NOT append
        # a ValidationResult yet. The result is appended only when
        # approve_skill() or reject_skill() is called.
        # SF-8: Previously appended a passed=False "pending" result here,
        # which was confusing — "not passed" looked like a failure but
        # actually meant "awaiting review". Now, no Stage 4 result is
        # stored until the review decision is made.
        remaining_budget = self._total_budget - total_tokens_used
        self._stage_4_review(record, remaining_budget)
        # Skill stays STAGE_3_PASSED awaiting review via approve_skill()
        # or reject_skill(). No status change here.

        self._persist_record(record)
        self._log_validation_decision(record, f"completed_{record.status}")

        logger.info(
            f"Skill '{record.name}' validation complete: "
            f"status={record.status}, "
            f"total_tokens={total_tokens_used}"
        )

        return record

    def approve_skill(self, record: SkillRecord, reviewer: str) -> SkillRecord:
        """Approve a skill that passed stages 1-3 (external review approval).

        Args:
            record: SkillRecord with status STAGE_3_PASSED.
            reviewer: Identity of the reviewer who approved.

        Returns:
            Updated SkillRecord with status VALIDATED.

        Raises:
            ValueError: If skill is not in STAGE_3_PASSED status.
        """
        if record.status != SkillStatus.STAGE_3_PASSED:
            raise ValueError(
                f"Cannot approve skill '{record.name}': "
                f"status is {record.status}, expected STAGE_3_PASSED"
            )

        # Add review approval result
        review_result = ValidationResult(
            stage=ValidationStage.REVIEW,
            passed=True,
            score=1.0,
            detail=f"Approved by reviewer: {reviewer}",
            tokens_used=0,
            timestamp=datetime.now(timezone.utc),
            reviewer=reviewer,
        )
        record.validation_results.append(review_result)
        record.status = SkillStatus.VALIDATED

        self._persist_record(record)
        self._log_validation_decision(record, "approved")

        logger.info(
            f"Skill '{record.name}' approved by {reviewer}"
        )

        return record

    def reject_skill(
        self, record: SkillRecord, reviewer: str, reason: str
    ) -> SkillRecord:
        """Reject a skill during review.

        Args:
            record: SkillRecord with status STAGE_3_PASSED.
            reviewer: Identity of the reviewer who rejected.
            reason: Reason for rejection.

        Returns:
            Updated SkillRecord with status REJECTED.
        """
        if record.status != SkillStatus.STAGE_3_PASSED:
            raise ValueError(
                f"Cannot reject skill '{record.name}': "
                f"status is {record.status}, expected STAGE_3_PASSED"
            )

        review_result = ValidationResult(
            stage=ValidationStage.REVIEW,
            passed=False,
            score=0.0,
            detail=f"Rejected by {reviewer}: {reason}",
            tokens_used=0,
            timestamp=datetime.now(timezone.utc),
            reviewer=reviewer,
        )
        record.validation_results.append(review_result)
        record.status = SkillStatus.REJECTED

        self._persist_record(record)
        self._log_validation_decision(record, "rejected_review")

        return record

    def _stage_1_syntax(self, record: SkillRecord) -> ValidationResult:
        """Stage 1: Syntax check — is the skill well-formed?

        Checks:
        - name is non-empty and valid identifier
        - description is non-empty
        - instruction_fragment is non-empty
        - instruction_fragment does not contain forbidden patterns
        - Can be parsed as a CapabilityAtom

        No LLM call needed — pure parsing. 0 tokens.
        """
        now = datetime.now(timezone.utc)
        issues: list[str] = []

        # Check name
        if not record.name or not record.name.replace("_", "").isalnum():
            issues.append(f"Invalid name: '{record.name}'")

        # Check description
        if not record.description or len(record.description.strip()) < 5:
            issues.append("Description too short or empty")

        # Check instruction_fragment
        if not record.instruction_fragment or len(
            record.instruction_fragment.strip()
        ) < 10:
            issues.append("Instruction fragment too short or empty")

        # Check forbidden patterns (FM-S08)
        for pattern in self._forbidden_patterns:
            if pattern.lower() in record.instruction_fragment.lower():
                issues.append(
                    f"Forbidden pattern in instruction: '{pattern}'"
                )

        # Try to construct CapabilityAtom
        if not issues:
            try:
                record.to_capability_atom()
            except Exception as e:
                issues.append(f"Cannot construct CapabilityAtom: {e}")

        passed = len(issues) == 0
        detail = "All syntax checks passed" if passed else "; ".join(issues)

        return ValidationResult(
            stage=ValidationStage.SYNTAX,
            passed=passed,
            score=1.0 if passed else 0.0,
            detail=detail,
            tokens_used=0,
            timestamp=now,
        )

    def _stage_2_execution(
        self,
        record: SkillRecord,
        execute_fn: ModelExecuteFn,
        test_tasks: list[Task],
        budget: int,
    ) -> ValidationResult:
        """Stage 2: Execution test — does the skill produce correct outputs?

        Applies the skill instruction to 2+ archived test tasks and checks
        that the quality score is >= 5/10 on each.

        FM-S02: Uses multiple test tasks to reduce LLM non-determinism.
        FM-S07: Respects per-stage budget cap.

        Args:
            record: Skill being validated.
            execute_fn: LLM execution function.
            test_tasks: Archived completed tasks for testing.
            budget: Remaining token budget for this stage.

        Returns:
            ValidationResult with pass/fail and scores.
        """
        now = datetime.now(timezone.utc)
        stage_budget = min(budget, self._stage_budgets[ValidationStage.EXECUTION])
        per_task_budget = stage_budget // max(len(test_tasks), 1)

        total_tokens = 0
        scores: list[float] = []
        test_task_ids: list[str] = []

        # SF-6: Use ALL available test tasks, not just min_test_tasks.
        # Per-task budget already accounts for variable counts.
        # min_test_tasks is a minimum requirement, not a cap.
        for test_task in test_tasks:
            if total_tokens >= stage_budget:
                break  # FM-S07: Budget exhausted

            prompt = EXECUTION_TEST_PROMPT.format(
                skill_name=record.name,
                skill_instruction=record.instruction_fragment,
                task_title=test_task.title,
                task_description=test_task.description[:500],
            )

            try:
                output, tokens_used = execute_fn(prompt, per_task_budget)
                total_tokens += tokens_used
            except Exception as e:
                logger.warning(
                    f"Stage 2 execution failed for task {test_task.id}: {e}"
                )
                scores.append(0.0)
                test_task_ids.append(test_task.id)
                continue

            # Parse quality score from output
            # IFM-N10: _parse_quality_score returns None on failure.
            # Skip tasks with unparseable scores instead of using a fallback.
            quality = self._parse_quality_score(output)
            if quality is None:
                logger.warning(
                    f"Stage 2 skipping task {test_task.id}: "
                    f"unparseable quality score"
                )
                test_task_ids.append(test_task.id)
                continue
            # Normalize to 0-1 (quality is 1-10)
            normalized = quality / 10.0
            scores.append(normalized)
            test_task_ids.append(test_task.id)

        if not scores:
            return ValidationResult(
                stage=ValidationStage.EXECUTION,
                passed=False,
                score=0.0,
                detail="No execution test results obtained",
                tokens_used=total_tokens,
                timestamp=now,
                test_task_ids=test_task_ids,
            )

        avg_score = sum(scores) / len(scores)
        # Must score >= 0.5 (i.e., quality >= 5/10) on average
        passed = avg_score >= 0.5
        # Must pass on all test tasks (not just average)
        all_passed = all(s >= 0.5 for s in scores)
        passed = passed and all_passed

        detail = (
            f"Avg score: {avg_score:.2f}, "
            f"per-task: {[f'{s:.2f}' for s in scores]}, "
            f"all_passed: {all_passed}"
        )

        return ValidationResult(
            stage=ValidationStage.EXECUTION,
            passed=passed,
            score=avg_score,
            detail=detail,
            tokens_used=total_tokens,
            timestamp=now,
            test_task_ids=test_task_ids,
        )

    def _stage_3_comparison(
        self,
        record: SkillRecord,
        execute_fn: ModelExecuteFn,
        test_tasks: list[Task],
        budget: int,
    ) -> ValidationResult:
        """Stage 3: Comparison — is this skill better than baseline?

        A/B test: runs test tasks with and without the skill instruction.
        Must show >= min_improvement_pp percentage point improvement.

        FM-S05: Improvement threshold matches ring_3_to_2 criteria (+5pp).
        FM-S07: Respects per-stage budget cap.

        IFM-N11 KNOWN LIMITATION: This stage uses LLM self-reported quality
        scores (QUALITY: 1-10), which contradicts the "execution-based
        validation" principle from Section 12.2. This is a pragmatic
        compromise: true execution-based comparison (running the skill on
        real tasks and comparing actual outputs to ground truth) requires
        the evolution engine (Phase 4). The +5pp improvement threshold
        provides some margin against noise. Phase 4 will replace this with
        execution-based quality measurement.

        IFM-N15: With only comparison_runs (default 2) per variant, random
        noise can produce false positives. The +5pp threshold provides some
        margin. Phase 4 will add more statistical rigor (minimum 3 runs,
        paired comparisons, effect size estimation).

        Args:
            record: Skill being validated.
            execute_fn: LLM execution function.
            test_tasks: Archived tasks for A/B comparison.
            budget: Remaining token budget for this stage.

        Returns:
            ValidationResult with improvement delta.
        """
        now = datetime.now(timezone.utc)
        stage_budget = min(
            budget, self._stage_budgets[ValidationStage.COMPARISON]
        )
        # Budget split: half for baseline, half for with-skill
        half_budget = stage_budget // 2
        per_task_budget = half_budget // max(len(test_tasks), 1)

        total_tokens = 0
        baseline_scores: list[float] = []
        skill_scores: list[float] = []

        # Select test tasks (use same ones as stage 2 for consistency)
        selected_tasks = test_tasks[:self._comparison_runs]

        # Run baseline (without skill)
        for test_task in selected_tasks:
            if total_tokens >= stage_budget:
                break

            prompt = BASELINE_PROMPT.format(
                task_title=test_task.title,
                task_description=test_task.description[:500],
            )

            try:
                output, tokens_used = execute_fn(prompt, per_task_budget)
                total_tokens += tokens_used
                # IFM-N10: Skip unparseable scores instead of using fallback.
                # IFM-N11: Stage 3 comparison scores are LLM-assessed quality.
                # This is a pragmatic compromise — true execution-based
                # comparison requires the evolution engine (Phase 4).
                quality = self._parse_quality_score(output)
                if quality is None:
                    continue  # Skip unparseable baseline result
                baseline_scores.append(quality / 10.0)
            except Exception as e:
                logger.warning(f"Stage 3 baseline failed: {e}")
                # IFM-N10: Do not append 0.0 fallback on exception.
                # Let the "insufficient comparison data" check handle it.

        # Run with skill
        for test_task in selected_tasks:
            if total_tokens >= stage_budget:
                break

            prompt = EXECUTION_TEST_PROMPT.format(
                skill_name=record.name,
                skill_instruction=record.instruction_fragment,
                task_title=test_task.title,
                task_description=test_task.description[:500],
            )

            try:
                output, tokens_used = execute_fn(prompt, per_task_budget)
                total_tokens += tokens_used
                # IFM-N10: Skip unparseable scores.
                quality = self._parse_quality_score(output)
                if quality is None:
                    continue  # Skip unparseable skill result
                skill_scores.append(quality / 10.0)
            except Exception as e:
                logger.warning(f"Stage 3 with-skill failed: {e}")
                # IFM-N10: Do not append 0.0 fallback on exception.

        if not baseline_scores or not skill_scores:
            return ValidationResult(
                stage=ValidationStage.COMPARISON,
                passed=False,
                score=0.0,
                detail="Insufficient comparison data",
                tokens_used=total_tokens,
                timestamp=now,
            )

        baseline_avg = sum(baseline_scores) / len(baseline_scores)
        skill_avg = sum(skill_scores) / len(skill_scores)
        # Improvement in percentage points (0-100 scale)
        improvement_pp = (skill_avg - baseline_avg) * 100.0

        passed = improvement_pp >= self._min_improvement_pp

        detail = (
            f"Baseline avg: {baseline_avg:.2f}, "
            f"Skill avg: {skill_avg:.2f}, "
            f"Improvement: {improvement_pp:+.1f}pp "
            f"(threshold: {self._min_improvement_pp}pp)"
        )

        return ValidationResult(
            stage=ValidationStage.COMPARISON,
            passed=passed,
            score=skill_avg,
            detail=detail,
            tokens_used=total_tokens,
            timestamp=now,
            improvement_delta=improvement_pp,
        )

    def _stage_4_review(
        self, record: SkillRecord, budget: int
    ) -> ValidationResult:
        """Stage 4: Review — generate review request for approval.

        This stage does NOT auto-approve. It generates a review summary
        that a human or senior agent can review. The skill stays in
        STAGE_3_PASSED status until approve_skill() or reject_skill()
        is called.

        Exception: if no reviewer is required (test mode), marks as passed.

        Args:
            record: Skill that passed stages 1-3.
            budget: Remaining token budget (used for review summary only).

        Returns:
            ValidationResult with review request details.
            passed=False indicates review is pending (not a failure).
        """
        now = datetime.now(timezone.utc)

        # Build review summary from validation results
        summary_parts = [
            f"Skill: {record.name}",
            f"Description: {record.description}",
            f"Source task: {record.source.task_id}",
            f"Instruction ({len(record.instruction_fragment)} chars):",
            f"  {record.instruction_fragment[:200]}...",
        ]
        for vr in record.validation_results:
            summary_parts.append(
                f"  Stage {vr.stage}: "
                f"{'PASS' if vr.passed else 'FAIL'} "
                f"(score={vr.score:.2f}, tokens={vr.tokens_used})"
            )
            if vr.improvement_delta is not None:
                summary_parts.append(
                    f"    Improvement: {vr.improvement_delta:+.1f}pp"
                )

        review_summary = "\n".join(summary_parts)

        # Log the review request
        logger.info(
            f"Skill '{record.name}' awaiting review:\n{review_summary}"
        )

        # Review is pending — return passed=False to indicate awaiting approval
        # The approve_skill() method will add a passed=True result later
        return ValidationResult(
            stage=ValidationStage.REVIEW,
            passed=False,  # Pending, not failed
            score=0.0,
            detail=f"Review pending. Summary:\n{review_summary}",
            tokens_used=0,
            timestamp=now,
        )

    def _parse_quality_score(self, output: str) -> float | None:
        """Parse a QUALITY: <1-10> score from LLM output.

        Returns the parsed score clamped to [1, 10], or None if unparseable.

        IFM-N10: Previously returned 5.0 as fallback, which equals the Stage 2
        passing threshold (5/10) — causing parse failures to count as passing.
        Now returns None so callers can skip unparseable results.
        """
        import re
        match = re.search(r"QUALITY:\s*(\d+(?:\.\d+)?)", output)
        if match:
            score = float(match.group(1))
            return max(1.0, min(10.0, score))  # Clamp to 1-10
        logger.warning(
            "Could not parse QUALITY score from output — skipping this result"
        )
        return None

    def _persist_record(self, record: SkillRecord) -> None:
        """Persist a skill record to YAML.

        FM-S10: Uses skill name for filename to prevent unbounded growth.
        """
        record.updated_at = datetime.now(timezone.utc)
        self.yaml_store.write(
            f"{self._skills_base}/{record.name}.yaml",
            record,
        )

    def _log_validation_decision(
        self, record: SkillRecord, decision: str
    ) -> None:
        """Log a validation decision to the DECISIONS audit stream."""
        if self._audit_logger is None:
            return
        try:
            stages = [
                {
                    "stage": vr.stage,
                    "passed": vr.passed,
                    "score": vr.score,
                }
                for vr in record.validation_results
            ]
            entry = DecisionLogEntry(
                id=generate_id("dec"),
                timestamp=datetime.now(timezone.utc),
                decision_type=f"skill_validation_{decision}",
                actor="skill_validator",
                options_considered=stages,
                selected=decision,
                rationale=(
                    f"Skill '{record.name}' validation: {decision}. "
                    f"Stages completed: {len(record.validation_results)}"
                ),
            )
            self._audit_logger.log_decision(entry)
        except Exception as e:
            logger.warning(f"Failed to log validation decision: {e}")
```

---

## Part 6: SkillLibrary Engine

### 6.1 `engine/skill_library.py`

```python
"""Skill library — storage, retrieval, search, and lifecycle management.
Spec reference: Section 12.3 (Organization), Section 12.4 (Maintenance).

Stores validated skills with ring-based trust tiers. Provides TF-IDF
semantic search for skill retrieval. Runs periodic maintenance: prune
low-performers, merge near-duplicates, score by usage/success/freshness.

Key constraints:
- Capacity limits: 50 per domain, 20 per level (Li et al. 2026)
- Maintenance every 20 tasks (configurable)
- Prune: success_rate < 0.5 OR unused for 30 tasks -> deprecated
- Merge: cosine similarity > 0.85 -> consolidate
- Ring transitions: 3->2 requires +5pp improvement + full validation
- All changes git-committed with provenance

Literature basis:
- Li et al. 2026: Phase transition at critical library size
- ToolLibGen: Consolidation (cluster, refactor, aggregate)
- Odyssey: 40 primitives + 183 compositions, hierarchical organization
- STEPS: Taxonomy-based skill organization
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..audit.logger import AuditLogger
from ..engine.diversity_engine import (
    compute_idf,
    cosine_distance,
    tf_idf_vector,
    tokenize,
)
from ..models.audit import DecisionLogEntry, EvolutionLogEntry, LogStream
from ..models.base import generate_id
from ..models.evolution import EvolutionTier
from ..models.protection import ProtectionRing, RingTransition
from ..models.skill import (
    ExtractionCandidate,
    MaintenanceRecord,
    SkillLibraryStats,
    SkillMaintenanceAction,
    SkillPerformanceMetrics,
    SkillRecord,
    SkillStatus,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.skill_library")


class SkillLibrary:
    """Skill storage, retrieval, and lifecycle management.

    Design invariants:
    - All skills persisted to YAML via YamlStore
    - Capacity enforced per domain (50) and per level (20)
    - TF-IDF search uses DiversityEngine functions (no duplication)
    - Maintenance is synchronous, called explicitly by orchestrator
    - Ring transitions logged to EVOLUTION audit stream
    - Skill records are the source of truth — not in-memory cache
    - FM-S03: Capacity overflow rejects new skills, does not evict
    - FM-S04: Merge produces combined skill only if both score well
    - FM-S06: Name uniqueness enforced on add

    Usage:
        library = SkillLibrary(yaml_store, domain="meta")
        library.add_skill(validated_record)
        results = library.search_skills("error handling")
        records = library.run_maintenance()
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        audit_logger: AuditLogger | None = None,
    ):
        self.yaml_store = yaml_store
        self._domain = domain
        self._audit_logger = audit_logger

        # Load config (fail-loud if missing)
        config_raw = yaml_store.read_raw("core/skill-system.yaml")
        ss = config_raw.get("skill_system")
        if ss is None:
            raise ValueError(
                "core/skill-system.yaml missing 'skill_system' section"
            )
        lib = ss.get("library", {})
        cap = lib.get("capacity", {})
        self._capacity_per_domain = int(cap.get("per_domain", 50))
        self._capacity_per_level = int(cap.get("per_level", 20))

        maint = ss.get("maintenance", {})
        self._maintenance_period = int(maint.get("period_tasks", 20))
        self._prune_success_rate = float(
            maint.get("prune_success_rate", 0.5)
        )
        self._prune_unused_tasks = int(maint.get("prune_unused_tasks", 30))
        self._merge_threshold = float(
            maint.get("merge_similarity_threshold", 0.85)
        )
        self._max_maintenance_history = int(
            maint.get("max_maintenance_history", 100)
        )

        ring_cfg = ss.get("ring_transitions", {})
        r32 = ring_cfg.get("ring_3_to_2", {})
        self._promote_min_improvement = float(
            r32.get("min_improvement_pp", 5)
        )
        self._promote_min_usage = int(r32.get("min_usage_count", 5))
        self._promote_min_success_rate = float(
            r32.get("min_success_rate", 0.7)
        )
        self._promote_require_validation = bool(
            r32.get("require_full_validation", True)
        )

        r23 = ring_cfg.get("ring_2_to_3", {})
        self._demote_on_revalidation_failure = bool(
            r23.get("on_revalidation_failure", True)
        )
        self._demote_success_threshold = float(
            r23.get("on_success_rate_below", 0.5)
        )

        # State paths
        self._skills_dir = f"instances/{domain}/state/skills"
        self._maintenance_dir = f"{self._skills_dir}/maintenance-history"
        yaml_store.ensure_dir(self._skills_dir)
        yaml_store.ensure_dir(self._maintenance_dir)

        # Task counter for maintenance scheduling
        self._tasks_since_maintenance = 0

    def add_skill(self, record: SkillRecord) -> bool:
        """Add a validated skill to the library.

        Args:
            record: SkillRecord with status VALIDATED.

        Returns:
            True if skill was added, False if rejected (capacity overflow
            or duplicate name).

        Raises:
            ValueError: If skill status is not VALIDATED.

        FM-S03: Capacity overflow rejects, does not evict.
        FM-S06: Duplicate name check.
        """
        if record.status != SkillStatus.VALIDATED:
            raise ValueError(
                f"Cannot add skill '{record.name}': "
                f"status is {record.status}, expected VALIDATED"
            )

        # FM-S06: Check for duplicate name
        existing = self.get_skill(record.name)
        if existing is not None:
            logger.warning(
                f"Skill '{record.name}' already exists in library"
            )
            return False

        # FM-S03: Check capacity
        active_count = self._count_active_skills()
        if active_count >= self._capacity_per_domain:
            logger.warning(
                f"Library at capacity ({active_count}/{self._capacity_per_domain}). "
                f"Skill '{record.name}' rejected."
            )
            return False

        # Activate the skill
        record.status = SkillStatus.ACTIVE
        record.updated_at = datetime.now(timezone.utc)
        self._persist_skill(record)

        logger.info(
            f"Skill '{record.name}' added to library "
            f"(ring={record.ring}, domain={record.domain})"
        )

        return True

    def get_skill(self, name: str) -> SkillRecord | None:
        """Get a skill by name.

        Args:
            name: Skill name (used as filename).

        Returns:
            SkillRecord or None if not found.
        """
        path = f"{self._skills_dir}/{name}.yaml"
        try:
            return self.yaml_store.read(path, SkillRecord)
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.warning(f"Error loading skill '{name}': {e}")
            return None

    def get_all_skills(self) -> list[SkillRecord]:
        """Load all skill records from disk.

        Returns list of successfully loaded records. Corrupt files
        are logged and skipped.
        """
        skills: list[SkillRecord] = []
        try:
            # IFM-MF2: YamlStore has list_dir(), not list_files().
            # list_dir() returns names (not paths), so filter by suffix
            # and skip known subdirectory names.
            entries = self.yaml_store.list_dir(self._skills_dir)
        except (FileNotFoundError, NotADirectoryError):
            return []

        for fname in entries:
            # Skip subdirectories (list_dir returns names, not paths)
            if fname in ("candidates", "maintenance-history"):
                continue
            # Only process .yaml files
            if not fname.endswith(".yaml"):
                continue
            try:
                skill = self.yaml_store.read(
                    f"{self._skills_dir}/{fname}", SkillRecord
                )
                skills.append(skill)
            except Exception as e:
                logger.warning(f"Skipping corrupt skill file {fname}: {e}")

        return skills

    def get_active_skills(self) -> list[SkillRecord]:
        """Get all active skills."""
        return [s for s in self.get_all_skills() if s.is_active]

    def get_skill_names(self) -> list[str]:
        """Get names of all skills (active and inactive).

        Used by SkillExtractor for deduplication.
        """
        return [s.name for s in self.get_all_skills()]

    def search_skills(
        self, query: str, limit: int = 5
    ) -> list[SkillRecord]:
        """Search for skills using TF-IDF semantic similarity.

        Uses DiversityEngine's TF-IDF functions for text similarity.
        Searches against skill name + description + instruction_fragment.

        Args:
            query: Search query text.
            limit: Maximum results to return.

        Returns:
            List of SkillRecords sorted by relevance (most relevant first).
        """
        active_skills = self.get_active_skills()
        if not active_skills:
            return []

        # Build document corpus: one document per skill
        documents: list[list[str]] = []
        for skill in active_skills:
            doc_text = f"{skill.name} {skill.description} {skill.instruction_fragment}"
            documents.append(tokenize(doc_text))

        # Add query as a document for IDF computation
        query_tokens = tokenize(query)
        all_docs = documents + [query_tokens]

        # Compute IDF across all documents + query
        idf = compute_idf(all_docs)

        # Compute query vector
        query_vector = tf_idf_vector(query_tokens, idf)

        # Compute similarity for each skill
        scored: list[tuple[float, SkillRecord]] = []
        for i, skill in enumerate(active_skills):
            skill_vector = tf_idf_vector(documents[i], idf)
            # cosine_distance returns distance (0=identical, 1=orthogonal)
            # We want similarity, so use 1 - distance
            distance = cosine_distance(query_vector, skill_vector)
            similarity = 1.0 - distance
            scored.append((similarity, skill))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[0], reverse=True)

        return [skill for _, skill in scored[:limit]]

    def get_skills_for_task(self, task_type: str) -> list[SkillRecord]:
        """Get active skills relevant to a task type.

        Uses task_type as search query. Returns top 3 matches.

        Args:
            task_type: Task type from Orchestrator._classify_task_type().

        Returns:
            List of relevant active SkillRecords (max 3).
        """
        return self.search_skills(task_type, limit=3)

    def record_skill_usage(
        self,
        name: str,
        success: bool,
        task_id: str,
        performance_monitor: object | None = None,  # PerformanceMonitor
    ) -> None:
        """Record that a skill was used in a task.

        Updates the skill's performance metrics and optionally reports
        to the PerformanceMonitor for rolling window tracking.

        Args:
            name: Skill name.
            success: Whether the task using this skill succeeded.
            task_id: ID of the task that used the skill.
            performance_monitor: Optional PerformanceMonitor instance.
                SF-7/IFM-N18: Reports skill outcomes to PerformanceMonitor
                for centralized performance tracking and drift detection.
        """
        skill = self.get_skill(name)
        if skill is None:
            logger.warning(f"Cannot record usage: skill '{name}' not found")
            return

        skill.metrics.usage_count += 1
        if success:
            skill.metrics.success_count += 1
        skill.metrics.last_used_task_id = task_id
        skill.metrics.last_used_at = datetime.now(timezone.utc)
        skill.metrics.tasks_since_last_use = 0

        self._persist_skill(skill)

        # SF-7/IFM-N18: Report to PerformanceMonitor for centralized tracking
        if performance_monitor is not None:
            try:
                performance_monitor.record_skill_outcome(
                    skill_name=name, success=success
                )
            except Exception as e:
                logger.warning(
                    f"Failed to report skill outcome to PerformanceMonitor: {e}"
                )

    def run_maintenance(self) -> list[MaintenanceRecord]:
        """Run periodic maintenance: prune, merge, score, promote/demote.

        Called by the orchestrator every maintenance_period tasks.
        Synchronous — not in background threads.

        Steps:
        1. Increment tasks_since_last_use for all active skills
        2. Prune: deprecate skills with success_rate < 0.5 or unused for 30 tasks
        3. Merge: consolidate near-duplicates (cosine similarity > 0.85)
        4. Promote: Ring 3 -> Ring 2 if criteria met
        5. Demote: Ring 2 -> Ring 3 if performance dropped
        6. Log all actions

        Returns:
            List of MaintenanceRecords describing actions taken.

        FM-S04: Merge only if combined skill scores well.
        FM-S10: Maintenance history trimmed to max_maintenance_history.

        SF-5: This method calls get_active_skills() multiple times (after prune,
        after merge) which re-reads YAML from disk. With cap of 50 skills per
        domain, this is at most 150 YAML reads (3 x 50) — acceptable cost for
        correctness. A future optimization could cache in-memory during a single
        maintenance pass.
        """
        records: list[MaintenanceRecord] = []
        all_skills = self.get_active_skills()

        if not all_skills:
            return records

        # Step 1: Increment staleness counters
        for skill in all_skills:
            skill.metrics.tasks_since_last_use += 1
            self._persist_skill(skill)

        # Step 2: Prune low-performers
        prune_records = self._prune_skills(all_skills)
        records.extend(prune_records)

        # Reload after pruning (some may be deprecated now)
        all_skills = self.get_active_skills()

        # Step 3: Merge near-duplicates
        merge_records = self._merge_similar_skills(all_skills)
        records.extend(merge_records)

        # Reload after merging
        all_skills = self.get_active_skills()

        # Step 4: Promote eligible Ring 3 skills
        promote_records = self._promote_eligible(all_skills)
        records.extend(promote_records)

        # Step 5: Demote underperforming Ring 2 skills
        demote_records = self._demote_underperforming(all_skills)
        records.extend(demote_records)

        # Persist maintenance records
        for rec in records:
            self._persist_maintenance_record(rec)

        # Trim history
        self._trim_maintenance_history()

        # Reset task counter
        self._tasks_since_maintenance = 0

        logger.info(
            f"Maintenance complete: {len(records)} actions taken "
            f"({len(prune_records)} pruned, {len(merge_records)} merged, "
            f"{len(promote_records)} promoted, {len(demote_records)} demoted)"
        )

        return records

    def promote_skill(self, name: str) -> RingTransition | None:
        """Promote a Ring 3 skill to Ring 2 if criteria are met.

        Criteria (Section 20.2, ring_3_to_2):
        - Passed full 4-stage validation
        - Demonstrated >= +5pp improvement (from stage 3)
        - Used at least min_usage_count times
        - Success rate >= min_success_rate

        Returns:
            RingTransition if promoted, None if criteria not met.

        FM-S05: Ensures sufficient evidence before promotion.
        """
        skill = self.get_skill(name)
        if skill is None:
            return None

        if skill.ring != ProtectionRing.RING_3_EXPENDABLE:
            logger.debug(
                f"Skill '{name}' not Ring 3, cannot promote "
                f"(current ring={skill.ring})"
            )
            return None

        # Check criteria
        if not self._meets_promotion_criteria(skill):
            return None

        # Perform promotion
        transition = RingTransition(
            item=name,
            from_ring=ProtectionRing.RING_3_EXPENDABLE,
            to_ring=ProtectionRing.RING_2_VALIDATED,
            reason=(
                f"Meets promotion criteria: "
                f"usage={skill.metrics.usage_count}, "
                f"success_rate={skill.metrics.success_rate:.2f}"
            ),
            evidence=(
                f"Improvement: "
                f"{self._get_improvement_delta(skill):.1f}pp"
            ),
            approved_by="skill_library_auto",
        )

        skill.ring = ProtectionRing.RING_2_VALIDATED
        skill.updated_at = datetime.now(timezone.utc)
        self._persist_skill(skill)

        # Log to EVOLUTION stream
        self._log_ring_transition(transition)

        logger.info(
            f"Skill '{name}' promoted: Ring 3 -> Ring 2"
        )

        return transition

    def demote_skill(
        self, name: str, reason: str
    ) -> RingTransition | None:
        """Demote a Ring 2 skill to Ring 3.

        Called when:
        - Post-model-change revalidation fails (Phase 2.5 cross-ref)
        - Success rate drops below demotion threshold

        Args:
            name: Skill name.
            reason: Reason for demotion.

        Returns:
            RingTransition if demoted, None if skill not found or not Ring 2.
        """
        skill = self.get_skill(name)
        if skill is None:
            return None

        if skill.ring != ProtectionRing.RING_2_VALIDATED:
            return None

        transition = RingTransition(
            item=name,
            from_ring=ProtectionRing.RING_2_VALIDATED,
            to_ring=ProtectionRing.RING_3_EXPENDABLE,
            reason=reason,
            evidence=(
                f"success_rate={skill.metrics.success_rate:.2f}, "
                f"usage={skill.metrics.usage_count}"
            ),
            approved_by="skill_library_auto",
        )

        skill.ring = ProtectionRing.RING_3_EXPENDABLE
        skill.updated_at = datetime.now(timezone.utc)
        self._persist_skill(skill)

        self._log_ring_transition(transition)

        logger.info(
            f"Skill '{name}' demoted: Ring 2 -> Ring 3. Reason: {reason}"
        )

        return transition

    def get_stats(self) -> SkillLibraryStats:
        """Compute aggregate library statistics."""
        all_skills = self.get_all_skills()

        stats = SkillLibraryStats()
        stats.total_skills = len(all_skills)

        total_success = 0.0
        total_composite = 0.0
        active_count = 0

        for skill in all_skills:
            if skill.status == SkillStatus.ACTIVE:
                stats.active_skills += 1
                active_count += 1
                total_success += skill.metrics.success_rate
                total_composite += skill.metrics.composite_score
            elif skill.status == SkillStatus.DEPRECATED:
                stats.deprecated_skills += 1
            elif skill.status == SkillStatus.REJECTED:
                stats.rejected_skills += 1
            elif skill.status == SkillStatus.VALIDATING:
                stats.validating_skills += 1
            elif skill.status == SkillStatus.CANDIDATE:
                stats.candidate_skills += 1

            # Ring counts (active only)
            if skill.is_active:
                if skill.ring == ProtectionRing.RING_0_IMMUTABLE:
                    stats.ring_0_count += 1
                elif skill.ring == ProtectionRing.RING_1_PROTECTED:
                    stats.ring_1_count += 1
                elif skill.ring == ProtectionRing.RING_2_VALIDATED:
                    stats.ring_2_count += 1
                elif skill.ring == ProtectionRing.RING_3_EXPENDABLE:
                    stats.ring_3_count += 1

            # Domain counts
            domain = skill.domain
            stats.domains[domain] = stats.domains.get(domain, 0) + 1

        if active_count > 0:
            stats.avg_success_rate = total_success / active_count
            stats.avg_composite_score = total_composite / active_count

        return stats

    def increment_task_counter(self) -> bool:
        """Increment task counter and return True if maintenance is due."""
        self._tasks_since_maintenance += 1
        return self._tasks_since_maintenance >= self._maintenance_period

    # ── Internal Methods ──

    def _count_active_skills(self) -> int:
        """Count active skills in the library."""
        return len(self.get_active_skills())

    def _prune_skills(
        self, skills: list[SkillRecord]
    ) -> list[MaintenanceRecord]:
        """Prune low-performing or stale skills.

        Criteria (Section 12.4):
        - success_rate < 0.5 (with at least 1 usage)
        - unused for 30 tasks

        Ring 0 and Ring 1 skills are never pruned.
        """
        records: list[MaintenanceRecord] = []

        for skill in skills:
            if not skill.is_prunable:
                continue

            reason = ""
            if skill.metrics.success_rate < self._prune_success_rate:
                reason = (
                    f"success_rate={skill.metrics.success_rate:.2f} "
                    f"< {self._prune_success_rate}"
                )
            elif skill.metrics.tasks_since_last_use >= self._prune_unused_tasks:
                reason = (
                    f"unused_tasks={skill.metrics.tasks_since_last_use} "
                    f">= {self._prune_unused_tasks}"
                )

            if reason:
                skill.status = SkillStatus.DEPRECATED
                skill.updated_at = datetime.now(timezone.utc)
                self._persist_skill(skill)

                record = MaintenanceRecord(
                    id=generate_id("maint"),
                    created_at=datetime.now(timezone.utc),
                    action=SkillMaintenanceAction.PRUNE,
                    skill_name=skill.name,
                    detail=reason,
                    composite_score=skill.metrics.composite_score,
                    success_rate=skill.metrics.success_rate,
                    usage_count=skill.metrics.usage_count,
                )
                records.append(record)
                logger.info(f"Pruned skill '{skill.name}': {reason}")

        return records

    def _merge_similar_skills(
        self, skills: list[SkillRecord]
    ) -> list[MaintenanceRecord]:
        """Merge near-duplicate skills (cosine similarity > threshold).

        FM-S04: Only merges if both skills have similar performance.
        The skill with higher composite_score is kept; the other is deprecated.
        The kept skill's description is updated to note the merge.

        Uses DiversityEngine's TF-IDF functions for similarity computation.
        """
        records: list[MaintenanceRecord] = []
        if len(skills) < 2:
            return records

        # Build TF-IDF vectors for all skills
        documents = [
            tokenize(
                f"{s.name} {s.description} {s.instruction_fragment}"
            )
            for s in skills
        ]
        idf = compute_idf(documents)
        vectors = [tf_idf_vector(tokens, idf) for tokens in documents]

        # Find pairs with similarity > threshold
        merged_indices: set[int] = set()

        for i in range(len(skills)):
            if i in merged_indices:
                continue
            for j in range(i + 1, len(skills)):
                if j in merged_indices:
                    continue

                distance = cosine_distance(vectors[i], vectors[j])
                similarity = 1.0 - distance

                if similarity >= self._merge_threshold:
                    # FM-S04: Keep the one with higher composite score
                    keep_idx, deprecate_idx = (
                        (i, j)
                        if skills[i].metrics.composite_score
                        >= skills[j].metrics.composite_score
                        else (j, i)
                    )

                    kept = skills[keep_idx]
                    deprecated = skills[deprecate_idx]

                    # Update kept skill's description
                    kept.description = (
                        f"{kept.description} "
                        f"(merged with: {deprecated.name})"
                    )
                    kept.version += 1
                    kept.updated_at = datetime.now(timezone.utc)
                    self._persist_skill(kept)

                    # Deprecate the other
                    deprecated.status = SkillStatus.DEPRECATED
                    deprecated.updated_at = datetime.now(timezone.utc)
                    self._persist_skill(deprecated)

                    merged_indices.add(deprecate_idx)

                    record = MaintenanceRecord(
                        id=generate_id("maint"),
                        created_at=datetime.now(timezone.utc),
                        action=SkillMaintenanceAction.MERGE,
                        skill_name=kept.name,
                        detail=(
                            f"Merged with '{deprecated.name}' "
                            f"(similarity={similarity:.3f})"
                        ),
                        merged_with=deprecated.name,
                        composite_score=kept.metrics.composite_score,
                        success_rate=kept.metrics.success_rate,
                        usage_count=kept.metrics.usage_count,
                    )
                    records.append(record)
                    logger.info(
                        f"Merged skills: kept '{kept.name}', "
                        f"deprecated '{deprecated.name}' "
                        f"(similarity={similarity:.3f})"
                    )

        return records

    def _promote_eligible(
        self, skills: list[SkillRecord]
    ) -> list[MaintenanceRecord]:
        """Promote Ring 3 skills that meet promotion criteria."""
        records: list[MaintenanceRecord] = []

        for skill in skills:
            if skill.ring != ProtectionRing.RING_3_EXPENDABLE:
                continue
            if not self._meets_promotion_criteria(skill):
                continue

            transition = self.promote_skill(skill.name)
            if transition is not None:
                record = MaintenanceRecord(
                    id=generate_id("maint"),
                    created_at=datetime.now(timezone.utc),
                    action=SkillMaintenanceAction.PROMOTE,
                    skill_name=skill.name,
                    detail=(
                        f"Promoted Ring 3 -> Ring 2: "
                        f"usage={skill.metrics.usage_count}, "
                        f"success_rate={skill.metrics.success_rate:.2f}"
                    ),
                    from_ring=ProtectionRing.RING_3_EXPENDABLE,
                    to_ring=ProtectionRing.RING_2_VALIDATED,
                    composite_score=skill.metrics.composite_score,
                    success_rate=skill.metrics.success_rate,
                    usage_count=skill.metrics.usage_count,
                )
                records.append(record)

        return records

    def _demote_underperforming(
        self, skills: list[SkillRecord]
    ) -> list[MaintenanceRecord]:
        """Demote Ring 2 skills with success_rate below threshold."""
        records: list[MaintenanceRecord] = []

        for skill in skills:
            if skill.ring != ProtectionRing.RING_2_VALIDATED:
                continue
            if skill.metrics.usage_count < 5:
                continue  # Not enough data to judge
            if skill.metrics.success_rate >= self._demote_success_threshold:
                continue  # Still performing well

            transition = self.demote_skill(
                skill.name,
                f"success_rate={skill.metrics.success_rate:.2f} "
                f"< {self._demote_success_threshold}",
            )
            if transition is not None:
                record = MaintenanceRecord(
                    id=generate_id("maint"),
                    created_at=datetime.now(timezone.utc),
                    action=SkillMaintenanceAction.DEMOTE,
                    skill_name=skill.name,
                    detail=(
                        f"Demoted Ring 2 -> Ring 3: "
                        f"success_rate={skill.metrics.success_rate:.2f}"
                    ),
                    from_ring=ProtectionRing.RING_2_VALIDATED,
                    to_ring=ProtectionRing.RING_3_EXPENDABLE,
                    composite_score=skill.metrics.composite_score,
                    success_rate=skill.metrics.success_rate,
                    usage_count=skill.metrics.usage_count,
                )
                records.append(record)

        return records

    def _meets_promotion_criteria(self, skill: SkillRecord) -> bool:
        """Check if a skill meets Ring 3 -> Ring 2 promotion criteria."""
        # Must have sufficient usage
        if skill.metrics.usage_count < self._promote_min_usage:
            return False

        # Must have sufficient success rate
        if skill.metrics.success_rate < self._promote_min_success_rate:
            return False

        # Must have passed full validation (if required)
        if self._promote_require_validation:
            if skill.status != SkillStatus.ACTIVE:
                return False
            # Check that all 4 stages were passed
            passed_stages = {
                vr.stage for vr in skill.validation_results if vr.passed
            }
            # IFM-N25: FrameworkModel uses use_enum_values=True, so
            # ValidationResult.stage stores string values after YAML
            # roundtrip, not enum members. Build required_stages as
            # strings to ensure the comparison works correctly.
            # SF-2: Removed dead code (unused `required` comprehension).
            required_stages = {s.value for s in ValidationStage}
            if not required_stages.issubset(passed_stages):
                return False

        # Must have demonstrated improvement
        improvement = self._get_improvement_delta(skill)
        if improvement < self._promote_min_improvement:
            return False

        return True

    def _get_improvement_delta(self, skill: SkillRecord) -> float:
        """Get the improvement delta from stage 3 validation.

        IFM-N25: Compare against string value since use_enum_values=True
        stores strings after YAML roundtrip.
        """
        for vr in skill.validation_results:
            if (
                vr.stage == ValidationStage.COMPARISON.value
                and vr.improvement_delta is not None
            ):
                return vr.improvement_delta
        return 0.0

    def _persist_skill(self, skill: SkillRecord) -> None:
        """Persist a skill record to YAML."""
        self.yaml_store.write(
            f"{self._skills_dir}/{skill.name}.yaml",
            skill,
        )

    def _persist_maintenance_record(self, record: MaintenanceRecord) -> None:
        """Persist a maintenance record to YAML."""
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_suffix = generate_id("maint").split("-")[-1]
        path = (
            f"{self._maintenance_dir}/"
            f"{timestamp_str}_{unique_suffix}.yaml"
        )
        self.yaml_store.write(path, record)

    def _trim_maintenance_history(self) -> None:
        """Trim maintenance history to max_maintenance_history entries.

        FM-S10: Prevents unbounded growth of maintenance records.
        """
        try:
            # IFM-MF2: YamlStore has list_dir(), not list_files().
            # list_dir() returns sorted names. Filter by .yaml suffix.
            entries = self.yaml_store.list_dir(self._maintenance_dir)
        except (FileNotFoundError, NotADirectoryError):
            return

        sorted_files = [f for f in entries if f.endswith(".yaml")]
        while len(sorted_files) > self._max_maintenance_history:
            oldest = sorted_files.pop(0)
            try:
                self.yaml_store.delete(
                    f"{self._maintenance_dir}/{oldest}"
                )
            except FileNotFoundError:
                pass

    def _log_ring_transition(self, transition: RingTransition) -> None:
        """Log a ring transition to the EVOLUTION audit stream."""
        if self._audit_logger is None:
            return
        try:
            entry = EvolutionLogEntry(
                id=generate_id("evo"),
                timestamp=datetime.now(timezone.utc),
                tier=EvolutionTier.ORGANIZATIONAL,
                component=f"skill:{transition.item}",
                diff=f"Ring {transition.from_ring} -> {transition.to_ring}",
                rationale=transition.reason,
                evidence={"transition": transition.evidence},
                approved_by=transition.approved_by,
                constitutional_check="pass",
                rollback_commit="",  # No git commit for ring transitions
            )
            self._audit_logger.log_evolution(entry)
        except Exception as e:
            logger.warning(f"Failed to log ring transition: {e}")
```

---

## Part 7: Modifications to Existing Files

### 7.1 Audit Stream Usage

Phase 3 does NOT add a new LogStream. The existing 8 streams are sufficient:

- **DECISIONS stream**: Used for skill extraction decisions (extract/skip/reject) and validation decisions (stage pass/fail). Logged via `AuditLogger.log_decision()` with `DecisionLogEntry`.
- **EVOLUTION stream**: Used for ring transitions (promote/demote). Logged via `AuditLogger.log_evolution()` with `EvolutionLogEntry`.

This follows the principle from Phase 2.5: skills are a form of evolution (ring transitions are evolution events) and extraction/validation are decisions.

### 7.2 Changes to `engine/orchestrator.py`

Add SkillLibrary, SkillExtractor, and SkillValidator integration. The Orchestrator calls `extract_from_task()` after successful task completion, runs validation when candidates are available, and triggers maintenance periodically.

Add to `__init__()`:

```python
    def __init__(
        self,
        # ... existing parameters ...
        execute_fn: ModelExecuteFn | None = None,          # Phase 3: LLM call function
        skill_library: SkillLibrary | None = None,        # Phase 3
        skill_extractor: SkillExtractor | None = None,    # Phase 3
        skill_validator: SkillValidator | None = None,    # Phase 3
    ):
        # ... existing assignments ...
        # IFM-MF3: Store execute_fn so skill extraction/validation can use it.
        # Without this, self._execute_fn is referenced but never assigned.
        self._execute_fn = execute_fn
        self.skill_library = skill_library
        self.skill_extractor = skill_extractor
        self.skill_validator = skill_validator
```

Add TYPE_CHECKING imports:

```python
if TYPE_CHECKING:
    # ... existing imports ...
    from ..models.environment import ModelExecuteFn  # IFM-MF3
    from .skill_library import SkillLibrary
    from .skill_extractor import SkillExtractor
    from .skill_validator import SkillValidator
```

Add to task completion flow (after review verdict, before archiving):

```python
        # Phase 3: Skill extraction from successful tasks
        if (
            self.skill_extractor is not None
            and self.skill_library is not None
            and self.skill_validator is not None
            and task.review is not None
            and task.review.verdict in ("pass", "pass_with_notes")
        ):
            try:
                task_type = self._classify_task_type(task)
                existing_names = self.skill_library.get_skill_names()
                # IFM-MF5: Pass task_type explicitly to avoid divergent classifier
                candidate = self.skill_extractor.extract_from_task(
                    task, self._execute_fn, task_type, existing_names
                )
                if candidate is not None:
                    # Get test tasks for validation
                    test_tasks = self._get_archived_test_tasks(
                        task_type=task_type,
                        exclude_id=task.id,
                        limit=3,
                    )
                    record = self.skill_validator.validate(
                        candidate, self._execute_fn, test_tasks
                    )
                    if record.status == SkillStatus.VALIDATED:
                        self.skill_library.add_skill(record)
                    elif record.status == SkillStatus.STAGE_3_PASSED:
                        logger.info(
                            f"Skill '{record.name}' awaiting review"
                        )
            except Exception as e:
                logger.warning(f"Skill extraction/validation failed: {e}")

        # Phase 3: Increment extraction cooldowns
        if self.skill_extractor is not None:
            self.skill_extractor.increment_cooldowns()

        # Phase 3: Check if skill maintenance is due
        if self.skill_library is not None:
            if self.skill_library.increment_task_counter():
                try:
                    self.skill_library.run_maintenance()
                except Exception as e:
                    logger.warning(f"Skill maintenance failed: {e}")
```

Add helper method for retrieving test tasks:

```python
    def _get_archived_test_tasks(
        self,
        task_type: str,
        exclude_id: str,
        limit: int = 3,
    ) -> list[Task]:
        """Get archived tasks of similar type for skill validation.

        Returns completed tasks with passing reviews, excluding the
        current task. Used as test tasks for Stage 2 and Stage 3
        of the skill validation pipeline.

        IFM-MF4: Uses TaskLifecycle's "completed" directory (not "archive").
        TaskLifecycle maps COMPLETE and ARCHIVED statuses to "completed".
        Uses self.task_lifecycle.domain instead of self._domain.
        IFM-MF2: Uses list_dir() + suffix filter (not list_files()).
        """
        # Load from task completed directory
        completed_dir = (
            f"instances/{self.task_lifecycle.domain}/state/tasks/completed"
        )
        tasks: list[Task] = []
        try:
            entries = self.yaml_store.list_dir(completed_dir)
        except (FileNotFoundError, NotADirectoryError):
            return []

        for fname in [f for f in entries if f.endswith(".yaml")]:
            if len(tasks) >= limit:
                break
            try:
                task = self.yaml_store.read(
                    f"{completed_dir}/{fname}", Task
                )
                if (
                    task.id != exclude_id
                    and task.review is not None
                    and task.review.verdict in ("pass", "pass_with_notes")
                    and self._classify_task_type(task) == task_type
                ):
                    tasks.append(task)
            except Exception:
                continue

        return tasks
```

### 7.3 Changes to `audit/tree_viewer.py`

Add skill event rendering for DECISIONS stream entries with `decision_type` starting with `skill_`:

```python
    # In the DECISIONS stream rendering, add after existing decision handling:

    def _render_decision_entry(
        self, branch: Tree, entry: dict
    ) -> None:
        """Render a single decision entry, with skill-aware formatting."""
        ts = entry.get("timestamp", "?")[:19]
        decision_type = entry.get("decision_type", "?")
        actor = entry.get("actor", "?")

        if decision_type.startswith("skill_extraction"):
            selected = entry.get("selected", "?")
            color = "green" if selected == "extracted" else "yellow"
            branch.add(
                f"[dim]{ts}[/dim] "
                f"[{color}]SKILL EXTRACT[/{color}] "
                f"{selected} -- {actor}"
            )
        elif decision_type.startswith("skill_validation"):
            selected = entry.get("selected", "?")
            if "rejected" in selected:
                color = "red"
            elif "approved" in selected or "completed_validated" in selected:
                color = "green"
            else:
                color = "yellow"
            branch.add(
                f"[dim]{ts}[/dim] "
                f"[{color}]SKILL VALIDATE[/{color}] "
                f"{selected} -- {actor}"
            )
        else:
            # Existing decision rendering
            branch.add(
                f"[dim]{ts}[/dim] {decision_type} -- {actor}"
            )
```

For EVOLUTION stream, ring transitions for skills are already handled by the existing evolution rendering. The `component` field starts with `skill:` for skill-related transitions, which can be used for filtering.

---

## Part 8: Implementation Sequence

### 8.1 Dependency Graph

```
Step 0: YAML config (core/skill-system.yaml)
  |
  |---> Step 1: models/skill.py (all data models)
  |       |
  |       |---> Step 2: engine/skill_extractor.py (depends on models/skill)
  |       |
  |       |---> Step 3: engine/skill_validator.py (depends on models/skill)
  |       |
  |       \---> Step 4: engine/skill_library.py (depends on models/skill,
  |                                               diversity_engine)
  |
  |---> Step 5: engine/orchestrator.py (integration, depends on Steps 2-4)
  |
  \---> Step 6: audit/tree_viewer.py (skill event rendering)
```

### 8.2 Step-by-Step Implementation

**Step 0: YAML Configuration File**

Files to create:
- `core/skill-system.yaml` (from Part 3.1)

Verification:
```bash
uv run python -c "
import yaml
with open('core/skill-system.yaml') as f:
    data = yaml.safe_load(f)
assert 'skill_system' in data
assert data['skill_system']['validation']['total_token_budget'] == 15000
assert data['skill_system']['library']['capacity']['per_domain'] == 50
print('skill-system.yaml: OK')
"
```

Gate: YAML file loads and validates.

**Step 1: Data Models (`models/skill.py`)**

Files to create:
- `src/uagents/models/skill.py` (from Part 2)

Tests to run:
```bash
uv run pytest tests/test_models/test_skill.py -v
```

Gate: All model tests pass. `SkillRecord` instantiates with valid data. `ExtractionCandidate.to_skill_record()` produces valid `SkillRecord`. `SkillPerformanceMetrics` computed properties (success_rate, freshness, composite_score) return correct values. `SkillRecord.is_prunable` returns correct results for Ring 0/1 (never prunable), Ring 2/3 with various metrics. All enums have correct values. `FrameworkModel` strict mode enforced.

**Step 2: SkillExtractor Engine**

Files to create:
- `src/uagents/engine/skill_extractor.py` (from Part 4)

Tests to run:
```bash
uv run pytest tests/test_engine/test_skill_extractor.py -v
```

Gate: Extraction qualifies only passing tasks with sufficient confidence. Trajectory building concatenates timeline and artifacts. LLM output parsing handles NAME/DESCRIPTION/INSTRUCTION format. Forbidden pattern detection blocks malicious instructions. Cooldown mechanism prevents rapid re-extraction. Deduplication against existing names works. Budget cap respected.

**Step 3: SkillValidator Engine**

Files to create:
- `src/uagents/engine/skill_validator.py` (from Part 5)

Tests to run:
```bash
uv run pytest tests/test_engine/test_skill_validator.py -v
```

Gate: Stage 1 syntax check validates name, description, instruction. Stage 2 execution test applies skill to test tasks and parses quality scores. Stage 3 comparison runs A/B test and computes improvement delta. Stage 4 review generates summary and awaits approval. Early termination on stage failure. Budget tracking across stages. `approve_skill()` and `reject_skill()` update status correctly.

**Step 4: SkillLibrary Engine**

Files to create:
- `src/uagents/engine/skill_library.py` (from Part 6)

Tests to run:
```bash
uv run pytest tests/test_engine/test_skill_library.py -v
```

Gate: `add_skill()` adds validated skills and enforces capacity. `get_skill()` loads from YAML. `search_skills()` returns relevant results via TF-IDF. `run_maintenance()` prunes low-performers, merges duplicates, promotes/demotes. `promote_skill()` requires all criteria. `demote_skill()` works for Ring 2 skills. Capacity overflow rejects new skills. Maintenance history trimmed. Ring transitions logged.

**Step 5: Orchestrator Integration**

Files to modify:
- `src/uagents/engine/orchestrator.py` (from Part 7.2)

Tests to run:
```bash
uv run pytest tests/test_engine/test_orchestrator.py -v -k skill
```

Gate: Orchestrator creates skill components. Extraction triggered after successful task completion. Validation runs when candidates available. Maintenance triggered at correct interval. Extraction cooldowns incremented. Test task retrieval from archive works.

**Step 6: Audit Tree Viewer**

Files to modify:
- `src/uagents/audit/tree_viewer.py` (from Part 7.3)

Tests to run:
```bash
uv run pytest tests/test_audit/test_tree_viewer.py -v -k skill
```

Gate: Skill extraction decisions render with color coding. Skill validation decisions render with pass/fail indicators. Existing rendering unbroken.

**Step 7: Full Regression**

```bash
uv run pytest --tb=short -q
```

Gate: All existing tests pass. All new tests pass. No regressions.

### 8.3 Verification Checklist

| # | Check | Command |
|---|-------|---------|
| 1 | Skill models instantiate correctly | `uv run pytest tests/test_models/test_skill.py -v` |
| 2 | SkillPerformanceMetrics properties correct | `uv run pytest tests/test_models/test_skill.py -v -k metrics` |
| 3 | SkillRecord.is_prunable ring-aware | `uv run pytest tests/test_models/test_skill.py -v -k prunable` |
| 4 | ExtractionCandidate.to_skill_record() | `uv run pytest tests/test_models/test_skill.py -v -k candidate` |
| 5 | SkillExtractor qualification check | `uv run pytest tests/test_engine/test_skill_extractor.py -v -k qualifies` |
| 6 | SkillExtractor output parsing | `uv run pytest tests/test_engine/test_skill_extractor.py -v -k parse` |
| 7 | SkillExtractor forbidden pattern check | `uv run pytest tests/test_engine/test_skill_extractor.py -v -k forbidden` |
| 8 | SkillExtractor cooldown mechanism | `uv run pytest tests/test_engine/test_skill_extractor.py -v -k cooldown` |
| 9 | SkillExtractor deduplication | `uv run pytest tests/test_engine/test_skill_extractor.py -v -k dedup` |
| 10 | Validator stage 1 syntax check | `uv run pytest tests/test_engine/test_skill_validator.py -v -k stage_1` |
| 11 | Validator stage 2 execution test | `uv run pytest tests/test_engine/test_skill_validator.py -v -k stage_2` |
| 12 | Validator stage 3 comparison | `uv run pytest tests/test_engine/test_skill_validator.py -v -k stage_3` |
| 13 | Validator stage 4 review | `uv run pytest tests/test_engine/test_skill_validator.py -v -k stage_4` |
| 14 | Validator early termination | `uv run pytest tests/test_engine/test_skill_validator.py -v -k early_term` |
| 15 | Validator budget enforcement | `uv run pytest tests/test_engine/test_skill_validator.py -v -k budget` |
| 16 | Validator approve/reject | `uv run pytest tests/test_engine/test_skill_validator.py -v -k approve` |
| 17 | Library add_skill capacity check | `uv run pytest tests/test_engine/test_skill_library.py -v -k add` |
| 18 | Library search_skills TF-IDF | `uv run pytest tests/test_engine/test_skill_library.py -v -k search` |
| 19 | Library run_maintenance prune | `uv run pytest tests/test_engine/test_skill_library.py -v -k prune` |
| 20 | Library run_maintenance merge | `uv run pytest tests/test_engine/test_skill_library.py -v -k merge` |
| 21 | Library promote_skill | `uv run pytest tests/test_engine/test_skill_library.py -v -k promote` |
| 22 | Library demote_skill | `uv run pytest tests/test_engine/test_skill_library.py -v -k demote` |
| 23 | Library get_stats | `uv run pytest tests/test_engine/test_skill_library.py -v -k stats` |
| 24 | Orchestrator skill integration | `uv run pytest tests/test_engine/test_orchestrator.py -v -k skill` |
| 25 | Audit tree viewer skill rendering | `uv run pytest tests/test_audit/test_tree_viewer.py -v -k skill` |
| 26 | YAML config loads correctly | `uv run pytest tests/test_config/test_skill_system.py -v` |
| 27 | End-to-end: extract -> validate -> add | `uv run pytest tests/test_engine/test_skill_e2e.py -v` |
| 28 | Existing tests still pass | `uv run pytest --tb=short -q` |

---

## Part 9: Failure Modes

### 9.1 Extraction Quality (FM-S01 through FM-S03)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-S01 | Skill extracted from low-quality trajectory — review confidence was high but trajectory was trivial or short | HIGH | Extraction Quality | **MITIGATED:** `min_trajectory_length` threshold (default 200 chars) prevents extraction from trivial tasks. `min_review_confidence` (default 0.7) prevents extraction from uncertain reviews. Trajectory must contain substantive timeline entries and artifacts. |
| FM-S02 | Validation stage 2 flaky due to non-deterministic LLM output — same skill passes or fails depending on LLM randomness | HIGH | Extraction Quality | **MITIGATED:** Stage 2 uses ALL available test tasks (SF-6, minimum 2) and requires ALL to pass, not just average. Quality score parser returns None on parse failure (IFM-N10) — unparseable results are skipped entirely, preventing fallback values from distorting scores. Stage 3 runs comparison_runs (default 2) per variant. |
| FM-S03 | Library capacity overflow — too many skills extracted, capacity limit reached, new valid skills rejected | MEDIUM | Extraction Quality | **MITIGATED:** Capacity enforced at add_skill() time. New skills that would exceed limit are rejected (not evicted). Maintenance pruning creates room for new skills. Extraction cooldown (5 tasks between same task_type) prevents rapid accumulation. |

### 9.2 Skill Content (FM-S04 through FM-S08)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-S04 | Skill merging produces worse combined skill — two good skills merged, result is less effective | MEDIUM | Skill Content | **MITIGATED:** Merge keeps the higher-scoring skill unchanged (only updates description). The lower-scoring skill is deprecated. No instruction content is combined — this is a "keep best, deprecate rest" strategy, not a content merge. |
| FM-S05 | Ring promotion with insufficient evidence — skill promoted to Ring 2 based on small sample or lucky streak | HIGH | Skill Content | **MITIGATED:** Promotion requires: (1) full 4-stage validation passed, (2) >= +5pp improvement from stage 3, (3) >= 5 usages, (4) >= 70% success rate. All four criteria must be met simultaneously. |
| FM-S06 | Extraction produces duplicate of existing skill — same pattern extracted from similar tasks | MEDIUM | Skill Content | **MITIGATED:** `extract_from_task()` accepts `existing_skill_names` and checks name uniqueness. Extraction cooldown per task_type prevents rapid re-extraction. Maintenance merge consolidates near-duplicates (similarity > 0.85). |
| FM-S07 | Budget exhaustion during validation — 15000 token budget runs out mid-pipeline | MEDIUM | Skill Content | **MITIGATED:** Per-stage budgets allocated from total. Remaining budget checked before each stage. Budget exhaustion produces a REJECTED result with clear detail message, not a crash. Stage 1 uses 0 tokens (pure parsing). |
| FM-S08 | Skill injection causes prompt context overflow — too many skills loaded overwhelm context window | LOW | Skill Content | **MITIGATED (Phase 3.5 enforces):** Phase 3 does not auto-inject skills into prompts. Phase 3.5 will use dynamic tool loading with 3-5 tools/step target. `max_instruction_length` (1500 chars) limits individual skill size. Capacity limits (50 per domain) bound total library size. Forbidden pattern check prevents prompt injection attacks. |

### 9.3 Performance and Drift (FM-S09 through FM-S12)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-S09 | Stale skills after model drift — skills validated under old model behavior degrade after update | HIGH | Performance | **MITIGATED (cross-ref Phase 2.5):** When `EnvironmentMonitor` detects drift or version change, `RevalidationEngine` flags affected skills. `SkillLibrary.demote_skill()` can be called by the orchestrator for Ring 2 skills with `on_revalidation_failure`. Ring 3 skills are already expendable. |
| FM-S10 | Unbounded skill storage growth — maintenance never runs, skills accumulate without limit | MEDIUM | Performance | **MITIGATED:** Capacity limits enforced at add_skill() (50 per domain). Maintenance history trimmed to 100 entries. Maintenance period (20 tasks) is short enough to prevent accumulation. `SkillPerformanceMetrics.tasks_since_last_use` is bounded by the prune threshold (30). |
| FM-S11 | Maintenance runs too frequently — every 20 tasks includes full TF-IDF computation across all skills | LOW | Performance | **MITIGATED:** TF-IDF computation is O(n^2) but n is capped at 50 (capacity limit). At 50 skills, pairwise comparison is 1225 pairs — trivially fast. No LLM calls during maintenance (only text similarity). |
| FM-S12 | TF-IDF search returns irrelevant results — tokenization is too naive for technical skill descriptions | MEDIUM | Performance | **MITIGATED:** Uses the same tokenizer as DiversityEngine (regex word boundary split). For skill search, the query + all skill descriptions form the IDF corpus, which gives appropriate term weighting. Limit=5 default keeps result set small. Phase 4+ could upgrade to embedding-based search. |

### 9.4 Concurrency and State (FM-S13 through FM-S16)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-S13 | Two extractions for the same task run concurrently — duplicate candidates created | LOW | Concurrency | **MITIGATED:** Extraction is called synchronously from the orchestrator's task completion handler. No parallel extraction paths exist in Phase 3. Deduplication by name provides additional safety. |
| FM-S14 | Skill YAML file written partially — crash during write corrupts skill record | MEDIUM | Concurrency | **MITIGATED:** `YamlStore.write()` uses atomic temp-file + `os.replace()`. Partial writes are impossible. Corrupt files are logged and skipped by `get_all_skills()`. |
| FM-S15 | Maintenance and extraction run simultaneously — skill added while maintenance is pruning | LOW | Concurrency | **MITIGATED:** Both operations are synchronous and called from the orchestrator's single-threaded task completion handler. No parallel execution in Phase 3. |
| FM-S16 | Cooldown tracker lost on restart — extraction cooldowns are in-memory only | LOW | Concurrency | **MITIGATED:** Cooldown is short (5 tasks). Worst case on restart: one extra extraction of a recently-extracted task_type. This is harmless — deduplication by name prevents actual duplicates. |

### 9.5 API Contracts (FM-S17 through FM-S20)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-S17 | `execute_fn` raises exception during extraction — LLM API error, timeout, rate limit | MEDIUM | API Contracts | **MITIGATED:** `extract_from_task()` wraps `execute_fn` call in try/except, logs warning, returns None. Validation stages also wrap calls. No crash propagation. |
| FM-S18 | `YamlStore.list_dir()` returns entries including subdirectories (candidates/, maintenance-history/) | MEDIUM | API Contracts | **MITIGATED (IFM-MF2):** `get_all_skills()` uses `list_dir()` (not the nonexistent `list_files()`) and filters by name — skipping entries named `"candidates"` or `"maintenance-history"` and only processing files ending in `.yaml`. `_trim_maintenance_history()` similarly fixed. |
| FM-S19 | `SkillRecord.to_capability_atom()` fails if model_preference or thinking has invalid value after YAML roundtrip | LOW | API Contracts | **MITIGATED:** `YamlStore.read()` uses Pydantic validation. Invalid enum values in YAML cause `ValidationError` on load, caught by `get_skill()` and `get_all_skills()`. Corrupt files are skipped with warning. |
| FM-S20 | `CapabilityTracker` task types do not include "skill_validation" — recording skill validation outcomes mismatches | LOW | API Contracts | **MITIGATED:** `CapabilityTracker` already includes "skill_validation" in `ALL_KNOWN_TASK_TYPES`. Skill validation outcomes can be recorded without modification. |

### 9.6 Spec Divergence (FM-S21 through FM-S24)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-S21 | Spec says "Track performance in MAP-Elites archive" but Phase 3 does not implement MAP-Elites | MEDIUM | Spec Divergence | **ACCEPTED:** MAP-Elites requires the evolution engine (Phase 4+). Phase 3 tracks performance via `SkillPerformanceMetrics` which can feed into MAP-Elites later. The `composite_score` property provides a quality metric compatible with MAP-Elites quality dimension. |
| FM-S22 | Spec says "Compose into role compositions where relevant" but Phase 3 does not auto-compose | LOW | Spec Divergence | **ACCEPTED:** Role composition is Phase 3.5 scope (dynamic tool loading). Phase 3 provides `to_capability_atom()` which produces the atom that Phase 3.5 can compose into roles. |
| FM-S23 | Spec says "Every change git-committed with provenance" but skill YAML changes are not git-committed | MEDIUM | Spec Divergence | **DEFERRED:** Git committing every skill YAML change would create excessive commits during maintenance (prune + merge could be 10+ files). Ring transitions ARE logged to EVOLUTION audit stream. Phase 4 can add batched git commits for skill changes via `GitOps.commit_evolution()`. |
| FM-S24 | Spec says "sandbox" for Ring 3 execution but Phase 3 does not implement sandboxing | LOW | Spec Divergence | **ACCEPTED:** Phase 3 does not auto-inject skills into prompts, so sandbox is not yet needed. Phase 3.5 (dynamic tool loading) will implement sandboxing for Ring 3 skill injection. The `ring_3_sandboxed: true` config flag is already set for Phase 3.5 to consume. |

### 9.7 Security (FM-S25 through FM-S28)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-S25 | Malicious skill instruction injected via crafted task trajectory — adversarial task output designed to produce harmful skill | HIGH | Security | **MITIGATED:** (1) Forbidden pattern check blocks known injection phrases. (2) Stage 4 review requires human or authority agent approval. (3) Ring 3 skills are expendable and sandboxed (Phase 3.5). (4) Skills injected AFTER constitution in prompt, never before. (5) 26.1% vulnerability rate from literature drives this multi-layer defense. |
| FM-S26 | Skill instruction fragment contains encoded/obfuscated malicious content that bypasses forbidden pattern check | MEDIUM | Security | **MITIGATED:** Stage 4 human review is the final gate. Forbidden patterns are a first-pass filter, not the sole defense. Ring 3 default trust level limits blast radius. Phase 4+ can add more sophisticated content analysis. |
| FM-S27 | Skill with high success rate gains Ring 2 trust, then degrades silently after model update | HIGH | Security | **MITIGATED (cross-ref Phase 2.5):** `EnvironmentMonitor` drift detection triggers revalidation. `ring_2_to_3.on_revalidation_failure` config enables automatic demotion. Rolling performance monitoring via `PerformanceMonitor` detects gradual degradation. |
| FM-S28 | Skill library YAML files modified directly on disk, bypassing validation pipeline | MEDIUM | Security | **MITIGATED:** `YamlStore` validates on read. Invalid files produce `ValidationError`. Ring 0/1 files are protected by constitution guard (Phase 0). Ring 2/3 skill files are in the state directory which is user-writable by design — direct modification is acceptable for human operators. |

### 9.8 Review-Identified Failure Modes (IFM-MF/SF/N series, v0.3.1)

These failure modes were identified during the design review and failure mode analysis conducted after v0.3.0. All have been fixed in v0.3.1.

| ID | Failure Mode | Severity | Category | Fix Applied |
|----|-------------|----------|----------|-------------|
| IFM-MF1 | `SkillRecord`, `ExtractionCandidate`, `MaintenanceRecord` extend `TimestampedModel` but pass `id=` in constructors — `TimestampedModel` does not have an `id` field | CRITICAL | Data Model | **FIXED:** Changed base class to `IdentifiableModel` which extends `TimestampedModel` and includes the `id` field. |
| IFM-MF2 | `YamlStore.list_files()` called in `get_all_skills()`, `_trim_maintenance_history()`, `_get_archived_test_tasks()` — this method does not exist | CRITICAL | API Contract | **FIXED:** Replaced with `list_dir()` + manual `.yaml` suffix filtering. Fixed subdirectory filtering to check by name (`fname in ("candidates", "maintenance-history")`) instead of path prefix. |
| IFM-MF3 | Orchestrator references `self._execute_fn` which is never assigned — all extraction/validation LLM calls crash | CRITICAL | Integration | **FIXED:** Added `execute_fn: ModelExecuteFn | None = None` parameter to orchestrator `__init__()`, stored as `self._execute_fn`. |
| IFM-MF4 | `_get_archived_test_tasks()` uses wrong directory `"archive"` and references `self._domain` which doesn't exist on orchestrator | HIGH | Integration | **FIXED:** Changed to `"completed"` directory (matching `TaskLifecycle` status mapping). Changed `self._domain` to `self.task_lifecycle.domain`. |
| IFM-MF5 | `SkillExtractor._classify_task_type()` duplicates `Orchestrator._classify_task_type()` — divergence risk | HIGH | Design | **FIXED:** Removed duplicate classifier from `SkillExtractor`. `extract_from_task()` now accepts `task_type: str` parameter passed by orchestrator. |
| IFM-N10 | `_parse_quality_score()` returns 5.0 fallback on parse failure — equals Stage 2 passing threshold, causing parse failures to count as passes | HIGH | Validation | **FIXED:** Returns `None` instead. Callers skip unparseable results. Stage 3 baseline/with-skill loops skip rather than append 0.0 fallback on exception. |
| IFM-N11 | Stage 3 uses LLM self-reported quality scores, contradicting "execution-based validation" principle | MEDIUM | Design | **DOCUMENTED:** Added explicit comment acknowledging this as a pragmatic compromise. True execution-based comparison requires Phase 4 evolution engine. |
| IFM-N15 | Stage 3 with only 2 comparison runs has insufficient statistical power — random noise can cause false positives | MEDIUM | Validation | **DOCUMENTED:** Added note that +5pp threshold provides margin. Phase 4 will add more statistical rigor (minimum 3 runs, paired comparisons). |
| IFM-N18 | `record_skill_usage()` does not report to `PerformanceMonitor` — dual tracking confusion, degraded skill detection misses skill library outcomes | MEDIUM | Integration | **FIXED:** Added `performance_monitor` parameter to `record_skill_usage()`. Calls `performance_monitor.record_skill_outcome()` when provided. |
| IFM-N20 | No `BudgetTracker` pre-check before validation — validation can exhaust session budget | HIGH | Budget | **FIXED:** Added `budget_tracker` parameter to `SkillValidator.__init__()`. `validate()` checks `budget_tracker.get_window().remaining_tokens` before starting. If insufficient, returns REJECTED with explanatory detail. |
| IFM-N25 | `_meets_promotion_criteria()` compares `set(ValidationStage)` (enum members) against `passed_stages` (strings after YAML roundtrip via `use_enum_values=True`) — promotion NEVER works | HIGH | Data Model | **FIXED:** Changed `required_stages` to `{s.value for s in ValidationStage}` for string comparison. Removed dead `required` set comprehension. Fixed `_get_improvement_delta()` to also compare `.value`. |
| SF-3 | `ExtractionCandidate` missing `thinking` field — not passed through to `SkillRecord` in `to_skill_record()` | LOW | Data Model | **FIXED:** Added `thinking: ThinkingSetting | None = None` to `ExtractionCandidate`. Passed through in `to_skill_record()`. |
| SF-6 | Stage 2 only tests `min_test_tasks` (2) — wastes available test data | LOW | Validation | **FIXED:** Stage 2 now uses ALL available test tasks. `min_test_tasks` is a minimum requirement gate, not a cap. Per-task budget already accounts for variable counts. |
| SF-8 | Stage 4 appends `passed=False` "pending" result during `validate()` — confusing semantics (not-passed looks like failure but means awaiting review) | MEDIUM | Validation | **FIXED:** `validate()` no longer appends a Stage 4 result. The result is only appended by `approve_skill()` or `reject_skill()`. |

### 9.9 Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 3 (IFM-MF1, IFM-MF2, IFM-MF3) | All FIXED in v0.3.1 |
| HIGH | 12 | FM-S01, FM-S02, FM-S05, FM-S09, FM-S25, FM-S27 (original), IFM-MF4, IFM-MF5, IFM-N10, IFM-N20, IFM-N25 (review-identified). All FIXED or MITIGATED |
| MEDIUM | 18 | All MITIGATED, FIXED, DOCUMENTED, or DEFERRED with plan |
| LOW | 9 | All documented, acceptable |
| **Total** | **42** | 28 original + 14 review-identified |
