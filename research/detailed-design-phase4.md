# Universal Agents Framework — Phase 4 Detailed Design

**Version:** 0.2.0
**Date:** 2026-03-01
**Source:** framework-design-unified-v1.1.md (Section 7, Section 8, Section 14, Section 16), self-evolving-agents-literature-review.md
**Status:** Implementation-ready (48 failure modes: 7 CRITICAL, 13 HIGH, 19 MEDIUM, 8 LOW — all mitigated)
**Scope:** Phase 4 "Evolution Engine" — evolution lifecycle (Tier 3 auto-approved), dual-copy fork-modify-evaluate-promote pipeline, MAP-Elites archive, evolution validation, constitutional guard integration
**Prerequisite:** Phase 0 + Phase 1 + Phase 1.5 + Phase 2 + Phase 2.5 + Phase 3 + Phase 3.5 fully implemented

---

## Table of Contents

1. [Architecture Overview](#part-1-architecture-overview)
2. [Data Models](#part-2-data-models)
3. [YAML Configuration](#part-3-yaml-configuration)
4. [EvolutionEngine](#part-4-evolutionengine)
5. [DualCopyManager](#part-5-dualcopymanager)
6. [EvolutionValidator](#part-6-evolutionvalidator)
7. [MAP-Elites Archive](#part-7-map-elites-archive)
8. [Modifications to Existing Files](#part-8-modifications-to-existing-files)
9. [Implementation Sequence](#part-9-implementation-sequence)
10. [Failure Modes](#part-10-failure-modes)

---

## Part 1: Architecture Overview

### 1.1 What Phase 4 Adds

Phase 4 transforms the framework from a *static execution engine* into a *self-improving system*. After Phase 3.5, the framework can execute tasks, manage agent teams, track diversity, detect stagnation, manage skill libraries, enforce ring hierarchy, and monitor context pressure — but it cannot *change itself*. All improvements require manual human edits to YAML configs, role compositions, and behavioral descriptors.

Phase 4 adds the evolution engine that enables agents to propose, evaluate, and apply improvements to their own operational parameters (Tier 3) through a rigorous 8-step lifecycle with constitutional safety checks.

Phase 4 adds four subsystems:

1. **EvolutionEngine** (NEW engine) — Orchestrates the 8-step evolution lifecycle: OBSERVE → ATTRIBUTE → PROPOSE → EVALUATE → APPROVE → COMMIT → VERIFY → LOG. Integrates with ConstitutionGuard for safety, GitOps for atomic commits, RingEnforcer for hierarchy enforcement, and AuditLogger for traceability. Phase 4 scope: Tier 3 auto-approved evolutions only.

2. **DualCopyManager** (NEW engine) — Implements the fork → modify → evaluate → promote/rollback pipeline from Section 8.2. Creates isolated copies of configuration files, applies proposed diffs, evaluates via multi-dimensional criteria, and either promotes successful changes or rolls back failures. All operations are Git-backed for auditability.

3. **EvolutionValidator** (NEW engine) — Multi-dimensional evaluation of evolution candidates. Scores on 6 dimensions: capability, consistency, robustness, predictability, safety, diversity. Each dimension produces a 0.0-1.0 score. Overall verdict: promote / rollback / hold-for-human. The validation layer is deliberately *independent* from the generation layer (Song et al. 2024: generation-verification gap).

4. **MAPElitesArchive** (NEW engine) — Behavioral archive of successful configurations using MAP-Elites quality-diversity algorithm. Two axes: task_type × complexity. Stores best-performing configuration per cell. Novelty bonus (0.1) encourages exploration. Update rule: replace cell occupant only if new config's performance exceeds existing.

### 1.2 Key Design Principles

1. **Generation-verification gap** — Verification must always exceed generation capability (Song et al. 2024). The EvolutionValidator is structurally independent from the EvolutionEngine that proposes changes. Validators cannot be modified by the same evolution cycle that created the proposals.

2. **Tier 3 only (Phase 4)** — Phase 4 implements only Tier 3 (operational) auto-approved evolutions: agent prompts, behavioral descriptors, capability parameters, thresholds. Tier 2 (organizational, quorum-approved) is Phase 5. Tier 1 (framework, human-approved) and Tier 0 (constitutional, human-only) are excluded from programmatic evolution.

3. **Constitutional check on every proposal** — Every EvolutionProposal passes through ConstitutionGuard.check_proposal() before evaluation. Proposals targeting Ring 0/1 content are rejected immediately. No exceptions.

4. **Dual-copy isolation** — Proposed changes are never applied in-place. A fork is created in `state/evolution/candidates/{evo-id}/`, changes applied to the fork, fork evaluated, and only promoted if all criteria pass. The active configuration is never modified until promotion.

5. **Atomic Git commits** — Every evolution is a structured Git commit via GitOps.commit_evolution(). Rollback points are created before promotion. Failed promotions trigger automatic rollback via GitOps.rollback_to().

6. **Audit everything** — Every step of the evolution lifecycle is logged to the evolution audit stream. Proposals, evaluations, approvals, commits, verifications, and failures all produce EvolutionLogEntry records.

7. **Fail loudly, never silently** — If a constitutional check fails, the evolution is rejected with a clear reason. If Git operations fail, the evolution is aborted. If validation dimensions are below threshold, the evolution is rolled back. No silent fallbacks, no swallowed exceptions.

8. **MAP-Elites for quality-diversity** — The archive maintains the best-performing configuration per behavioral cell (task_type × complexity). This prevents convergence to a single "optimal" configuration and maintains diverse strategies for different task types.

9. **Objective anchoring** — After every 10 evolution cycles, the system compares current behavior against the original objectives stored in CONSTITUTION.md. If alignment score drops below 0.8, evolution is paused and a human alert is triggered.

10. **Ring hierarchy immutable** — Ring 0 content is NEVER modified by evolution. Ring 1 modifications are forbidden in Phase 4 (require human approval). Only Ring 2-3 content can be evolved, and only through the dual-copy pipeline.

### 1.3 What Phase 4 Does NOT Include

- **Tier 2 quorum-approved evolution** (Phase 5) — Multi-agent voting with sealed ballots, anti-gaming rules, and role lineage restrictions.
- **Tier 1 human-approved evolution** (Phase 5) — Human decision queue integration for framework-level changes.
- **Population mode** (Phase 5) — Generating 3-5 candidate forks and tournament selection. Phase 4 uses single-fork evaluation only.
- **Proactive scout agents** (Phase 5+) — Scout agents that autonomously detect improvement opportunities. Phase 4 evolution is triggered by explicit observation events (task failure, stagnation signal, diversity drop).
- **Cross-domain evolution transfer** (Phase 6+) — Sharing successful evolutions across domains.
- **Self-governance risk scorecard** (Phase 5) — Comprehensive risk dimension scoring.
- **Anti-alignment-faking verification** (Phase 5) — Behavioral consistency tests and capability elicitation probes.

### 1.4 Architecture Diagram

```
                    ┌─────────────────────────────┐
                    │       EvolutionEngine        │
                    │  (8-step lifecycle driver)    │
                    └──────────┬──────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                     │
          ▼                    ▼                     ▼
┌─────────────────┐  ┌────────────────┐  ┌─────────────────────┐
│ ConstitutionGuard│  │ DualCopyManager│  │  EvolutionValidator  │
│ (safety gate)    │  │ (fork pipeline)│  │  (6-dimension eval)  │
└────────┬────────┘  └───────┬────────┘  └──────────┬──────────┘
         │                   │                       │
         │           ┌───────┴───────┐              │
         │           │   GitOps      │              │
         │           │ (atomic ops)  │              │
         │           └───────────────┘              │
         │                                          │
         ▼                                          ▼
┌─────────────────┐                     ┌─────────────────────┐
│  RingEnforcer    │                     │  MAPElitesArchive    │
│ (hierarchy check)│                     │ (quality-diversity)  │
└─────────────────┘                     └─────────────────────┘
                                                    │
                                                    ▼
                                          ┌─────────────────┐
                                          │   AuditLogger    │
                                          │ (evolution stream)│
                                          └─────────────────┘
```

### 1.5 Files to Create / Modify

**New files:**
- `src/uagents/engine/evolution_engine.py` — Main lifecycle driver
- `src/uagents/engine/dual_copy_manager.py` — Fork pipeline
- `src/uagents/engine/evolution_validator.py` — Multi-dimensional evaluation
- `src/uagents/engine/map_elites_archive.py` — Quality-diversity archive
- `instances/meta/core/evolution.yaml` — All evolution configuration
- `tests/test_engine/test_evolution_phase4.py` — Phase 4 test suite

**Modified files:**
- `src/uagents/models/evolution.py` — Full replacement: add EvolutionLifecycleState, EvaluationDimension, EvaluationResult, ArchiveCell, ObservationTrigger, EvolutionOutcome; update EvolutionProposal, EvolutionRecord, DualCopyCandidate
- `src/uagents/models/audit.py` — Add Phase 4 fields to EvolutionLogEntry (backward-compatible: new fields have defaults, old fields kept with defaults)
- `src/uagents/engine/orchestrator.py` — Integration point for evolution triggering
- `src/uagents/engine/skill_library.py` — No code changes needed (existing `_log_ring_transition()` uses fields preserved with defaults)

---

## Part 2: Data Models

### 2.1 New Models in `models/evolution.py`

```python
"""Evolution engine models.
Spec reference: Section 7 (Evolution Engine), Section 8 (Dual-Copy).

Phase 4 additions: EvolutionLifecycleState, EvaluationDimension,
EvaluationResult, ArchiveCell, ArchiveEntry, ObservationTrigger,
EvolutionOutcome.

Literature basis:
- Darwin Godel Machine: 20%→50% SWE-bench (population + dual-copy)
- Song et al. 2024: Generation-verification gap (independent evaluator)
- AlphaEvolve (DeepMind): Evolutionary search in code space
- ADAS (ICLR 2025): Meta-agent archive of agentic designs
"""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field

from .base import FrameworkModel, IdentifiableModel


class EvolutionTier(IntEnum):
    """Evolution tiers matching protection rings."""

    CONSTITUTIONAL = 0  # Human only — CONSTITUTION.md
    FRAMEWORK = 1       # Human approval required
    ORGANIZATIONAL = 2  # Quorum approval
    OPERATIONAL = 3     # Auto-approved


class EvolutionLifecycleState(StrEnum):
    """8-step evolution lifecycle states (Section 7.2)."""

    OBSERVE = "observe"       # 1. Detect problem or improvement opportunity
    ATTRIBUTE = "attribute"   # 2. Root-cause analysis with evidence
    PROPOSE = "propose"       # 3. Generate candidate fix with diffs
    EVALUATE = "evaluate"     # 4. Constitutional check, multi-dimensional eval
    APPROVE = "approve"       # 5. Tier-based approval
    COMMIT = "commit"         # 6. Git commit with structured message
    VERIFY = "verify"         # 7. Post-commit verification
    LOG = "log"               # 8. Full record to logs/evolution/

    # Terminal states
    REJECTED = "rejected"     # Proposal rejected at any stage
    ROLLED_BACK = "rolled_back"  # Promoted but verification failed


class ObservationTrigger(StrEnum):
    """What triggered the evolution observation (Section 7.2 step 1)."""

    TASK_FAILURE = "task_failure"           # Task completed with review fail
    STAGNATION = "stagnation"              # StagnationDetector signal
    DIVERSITY_DROP = "diversity_drop"       # SRD below floor
    CAPABILITY_GAP = "capability_gap"       # CapabilityTracker blind spot
    PERFORMANCE_DECLINE = "performance_decline"  # Declining success rate
    CONTEXT_PRESSURE = "context_pressure"   # Chronic high context utilization
    MANUAL = "manual"                       # Human-initiated


class EvaluationDimension(StrEnum):
    """6 evaluation dimensions for dual-copy assessment (Section 8.2)."""

    CAPABILITY = "capability"       # Does it perform tasks better?
    CONSISTENCY = "consistency"     # Reproducible results across runs?
    ROBUSTNESS = "robustness"       # Handles edge cases?
    PREDICTABILITY = "predictability"  # Can we anticipate when it will fail?
    SAFETY = "safety"               # Stays within constitutional bounds?
    DIVERSITY = "diversity"         # Maintains SRD above floor?


class EvolutionOutcome(StrEnum):
    """Final outcome of an evolution attempt."""

    PROMOTED = "promoted"       # Fork replaced active config
    ROLLED_BACK = "rolled_back"  # Fork discarded after failed verification
    REJECTED = "rejected"       # Proposal rejected before fork
    HELD = "held"               # Marginal improvement — held for human review


class EvolutionProposal(IdentifiableModel):
    """An agent's proposal to modify a component (Section 7.2 step 3).

    Every proposal includes the tier, component path, unified diff,
    rationale, evidence, and estimated risk. The constitutional check
    validates against Ring 0/1 protection before evaluation.

    Persisted to: instances/{domain}/state/evolution/proposals/{id}.yaml
    """

    tier: EvolutionTier
    component: str  # File path being modified (relative to instance root)
    diff: str       # Unified diff — what changes
    rationale: str  # Required: why this change is needed
    # FM-P4-47-FIX: Keep evidence as untyped dict for backward compatibility
    # with existing callers (e.g., SkillLibrary._log_ring_transition)
    evidence: dict = Field(default_factory=dict)  # triggering_tasks, metrics, etc.
    estimated_risk: float = Field(ge=0.0, le=1.0)
    trigger: ObservationTrigger = ObservationTrigger.MANUAL
    trigger_detail: str = ""  # e.g., task_id that failed, stagnation signal type
    lifecycle_state: EvolutionLifecycleState = EvolutionLifecycleState.OBSERVE


class DimensionScore(FrameworkModel):
    """Score for a single evaluation dimension."""

    dimension: EvaluationDimension
    score: float = Field(ge=0.0, le=1.0)
    detail: str = ""  # Explanation of score


class EvaluationResult(IdentifiableModel):
    """Result of multi-dimensional evaluation (Section 8.2 step 3).

    Contains per-dimension scores and an overall verdict.
    The verdict determines promote/rollback/hold.

    Persisted to: instances/{domain}/state/evolution/evaluations/{id}.yaml
    """

    proposal_id: str
    candidate_id: str  # DualCopyCandidate.evo_id
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    overall_score: float = Field(ge=0.0, le=1.0, default=0.0)
    verdict: EvolutionOutcome = EvolutionOutcome.REJECTED
    verdict_reason: str = ""
    evaluator_id: str = ""  # Agent that performed evaluation (independent!)


class QuorumVote(FrameworkModel):
    """A single sealed vote in a quorum process (Section 7.3).

    Phase 4: Stored but not used — quorum is Phase 5.
    """

    voter_id: str
    voter_role: str
    vote: Literal["approve", "reject"]
    rationale: str
    timestamp: datetime


class QuorumResult(FrameworkModel):
    """Result of a quorum vote (Section 7.3).

    Phase 4: Stored but not used — quorum is Phase 5.
    """

    votes: list[QuorumVote] = Field(default_factory=list)
    threshold: float = 0.67
    approved: bool = False


class EvolutionRecord(IdentifiableModel):
    """Post-approval evolution record (Section 7.2 step 8).

    The complete audit trail for a single evolution cycle.
    Includes the proposal, evaluation result, approval chain,
    commit reference, and verification result.

    Persisted to: instances/{domain}/state/evolution/records/{id}.yaml
    """

    proposal: EvolutionProposal
    evaluation: EvaluationResult | None = None
    approved_by: str  # "auto (tier 3)", "quorum", "human", "rejected", "held_for_human"
    constitutional_check: Literal["pass", "fail"]
    # FM-P4-17-FIX: Optional for rejected/held records that have no rollback point
    rollback_commit: str = ""  # Git SHA for rollback point (empty if rejected/held)
    evolution_commit: str = ""  # Git SHA of the evolution commit
    quorum: QuorumResult | None = None
    outcome: EvolutionOutcome = EvolutionOutcome.REJECTED
    verification_passed: bool = False


class DualCopyCandidate(FrameworkModel):
    """A fork being evaluated in dual-copy bootstrapping (Section 8.2).

    Created by DualCopyManager.create_fork(), populated during
    evaluation, and resolved by promote() or rollback().

    FM-P4-25-NOTE: fork_path changed from Path to str for YAML serialization
    compatibility with strict=True. No existing manifests need migration
    since Phase 4 is the first active use of DualCopyCandidate.

    Persisted to: instances/{domain}/state/evolution/candidates/{evo_id}/manifest.yaml
    """

    evo_id: str
    fork_path: str  # state/evolution/candidates/{evo-id}/ (string, not Path)
    source_files: list[str] = Field(default_factory=list)  # Files copied to fork
    modified_files: list[str] = Field(default_factory=list)  # Files modified in fork
    evaluation: dict[str, float] = Field(default_factory=dict)  # dimension -> score
    promoted: bool = False
    rolled_back: bool = False


class ArchiveCell(FrameworkModel):
    """A single cell in the MAP-Elites archive (Section 7.4).

    Indexed by (task_type, complexity). Stores the best-performing
    configuration found for this behavioral niche.
    """

    task_type: str  # "research", "engineering", "creative", "meta"
    complexity: str  # "simple", "moderate", "complex", "extreme"
    best_config: dict[str, str] = Field(default_factory=dict)  # topology, roles, etc.
    # DR-01-FIX: No upper bound — novelty bonus can push performance above 1.0
    performance: float = Field(ge=0.0, default=0.0)
    task_count: int = Field(ge=0, default=0)
    last_updated: datetime | None = None
    evolution_id: str = ""  # EvolutionRecord that set this cell


class MAPElitesState(FrameworkModel):
    """Full state of the MAP-Elites archive (Section 7.4).

    Persisted to: instances/{domain}/state/evolution/archive.yaml
    """

    cells: list[ArchiveCell] = Field(default_factory=list)
    novelty_bonus: float = 0.1
    total_evaluations: int = 0
    total_replacements: int = 0
```

### 2.2 Enhanced EvolutionLogEntry in `models/audit.py`

DR-02/FM-P4-16-FIX: The existing EvolutionLogEntry has required fields
`approved_by`, `constitutional_check`, `rollback_commit` used by SkillLibrary.
These MUST be kept (with defaults added) for backward compatibility.
New Phase 4 fields are added with defaults.

```python
class EvolutionLogEntry(BaseLogEntry):
    """Evolution audit log entry — enhanced for Phase 4 lifecycle.

    DR-02-FIX: Backward-compatible with existing callers (SkillLibrary).
    Old required fields now have defaults. New Phase 4 fields added.
    """

    stream: Literal[LogStream.EVOLUTION] = LogStream.EVOLUTION
    tier: EvolutionTier
    component: str
    diff: str
    rationale: str
    evidence: dict
    # Existing fields — kept with defaults for backward compatibility
    approved_by: str = ""
    constitutional_check: str = ""
    rollback_commit: str = ""
    # Phase 4 additions:
    lifecycle_state: str = ""  # EvolutionLifecycleState value
    outcome: str = ""          # EvolutionOutcome value
    evaluation_score: float = 0.0  # Overall evaluation score
    trigger: str = ""          # ObservationTrigger value
```

---

## Part 3: YAML Configuration

### 3.1 `instances/meta/core/evolution.yaml`

```yaml
# Evolution Engine Configuration
# Spec reference: Section 7 (Evolution Engine), Section 8 (Dual-Copy)
#
# All thresholds and limits for the evolution lifecycle.
# IFM-N53: Missing keys raise KeyError — no silent defaults.

evolution:
  # ── Tier constraints ──
  tiers:
    # Phase 4: Only tier 3 is auto-approved
    tier_3_auto_approve: true
    tier_2_requires_quorum: true  # Not implemented in Phase 4
    tier_1_requires_human: true   # Not implemented in Phase 4
    tier_0_immutable: true        # Always — CONSTITUTION.md never evolved

  # ── Lifecycle limits ──
  lifecycle:
    max_proposals_per_cycle: 5        # Maximum proposals evaluated per run-loop cycle
    max_concurrent_candidates: 1      # Phase 4: single-fork only (population mode is Phase 5)
    proposal_timeout_minutes: 30      # Abandon proposal if not resolved in this time
    cooldown_between_evolutions: 3    # Minimum completed tasks between evolution cycles

  # ── Evaluation thresholds ──
  evaluation:
    # Per-dimension minimum scores (0.0-1.0)
    min_capability: 0.5      # Must not degrade task performance
    min_consistency: 0.6     # Must be reproducible (3x repetition)
    min_robustness: 0.4      # Must handle edge cases
    min_predictability: 0.3  # Can we anticipate failures?
    min_safety: 0.9          # Constitutional compliance (high bar)
    min_diversity: 0.4       # Must maintain SRD above floor

    # Overall score thresholds
    promote_threshold: 0.6   # Overall score >= this → promote
    hold_threshold: 0.5      # Between hold and promote → hold for human review
    # Below hold_threshold → rollback

    # Dimension weights for overall score calculation
    weights:
      capability: 0.25
      consistency: 0.20
      robustness: 0.15
      predictability: 0.10
      safety: 0.20
      diversity: 0.10

  # ── Dual-copy pipeline ──
  dual_copy:
    # Files copied to fork (glob patterns relative to instance root)
    fork_includes:
      - "roles/compositions/*.yaml"
      - "core/topology.yaml"
      - "core/coordination.yaml"
      - "core/resource-awareness.yaml"
    # Files NEVER copied (shared, immutable, or append-only)
    fork_excludes:
      - "CONSTITUTION.md"
      - "core/constitution-hash.txt"
      - "logs/**"
      - "state/tasks/**"
      - "state/agents/**"
    # Candidate storage
    candidates_dir: "state/evolution/candidates"

  # ── MAP-Elites archive ──
  archive:
    # Behavioral dimensions
    task_types: ["research", "engineering", "creative", "meta"]
    complexities: ["simple", "moderate", "complex", "extreme"]
    # Update rules
    novelty_bonus: 0.1            # Added to score for novel configurations
    min_tasks_for_cell: 3         # Minimum tasks before a cell can be used as baseline
    archive_path: "state/evolution/archive.yaml"

  # ── Objective anchoring (Section 14.1) ──
  objective_anchoring:
    check_every_n_cycles: 10      # Compare behavior vs. constitution every N evolutions
    min_alignment_score: 0.8      # Below this: pause evolution, alert human
    alignment_check_agent: ""     # Must be DIFFERENT from proposing agents

  # ── Safety limits ──
  safety:
    max_file_modifications_per_proposal: 3  # Prevent sweeping changes
    max_diff_lines: 200                     # Prevent massive diffs
    forbidden_path_patterns:                # Patterns that can NEVER be evolved
      - "CONSTITUTION.md"
      - "constitution-hash"
      - "core/evolution.yaml"               # Evolution config itself is protected
      - ".claude/"                           # Claude Code config is protected
    allowed_extensions:                      # Only these file types can be evolved
      - ".yaml"
      - ".yml"
      - ".md"                               # Skill instructions, behavioral descriptors
    budget_change_cap_pct: 30               # Maximum budget reallocation percentage
```

---

## Part 4: EvolutionEngine

### 4.1 Class Definition

Review fixes applied: DR-04, DR-05, DR-06, DR-09, DR-10, FM-P4-19, FM-P4-20,
FM-P4-21, FM-P4-23, FM-P4-27, FM-P4-29, FM-P4-34, FM-P4-36, FM-P4-39,
FM-P4-43, FM-P4-46, FM-P4-48.

```python
"""Evolution engine — 8-step lifecycle driver.
Spec reference: Section 7 (Evolution Engine), Section 16.2 Phase 5 (Evolve).

Orchestrates the evolution lifecycle:
OBSERVE → ATTRIBUTE → PROPOSE → EVALUATE → APPROVE → COMMIT → VERIFY → LOG

Phase 4 scope: Tier 3 auto-approved evolutions only.
Tier 2 (quorum) and Tier 1 (human) deferred to Phase 5.

Key constraints:
- Constitutional check on EVERY proposal (before evaluation)
- Dual-copy isolation: changes NEVER applied in-place
- Atomic Git commits with structured messages
- Objective anchoring every 10 cycles
- All steps logged to evolution audit stream
- Ring 0/1 modifications FORBIDDEN
- RingEnforcer verifies modified files after promotion (FM-P4-29)
- Persistent state survives restarts (FM-P4-23)
- Persistent pause flag after alignment failure (FM-P4-48)

Literature basis:
- Darwin Godel Machine: dual-copy + population (20%→50% SWE-bench)
- Song et al. 2024: generation-verification gap
- ADAS (ICLR 2025): archive-based meta-agent search
- AlphaEvolve (DeepMind): evolutionary code improvement
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..audit.logger import AuditLogger
from ..models.audit import EvolutionLogEntry
from ..models.base import FrameworkModel, generate_id
from ..models.evolution import (
    DualCopyCandidate,
    EvaluationResult,
    EvolutionLifecycleState,
    EvolutionOutcome,
    EvolutionProposal,
    EvolutionRecord,
    EvolutionTier,
    ObservationTrigger,
)
from ..state.git_ops import GitOps, GitOpsError
from ..state.yaml_store import YamlStore
from .constitution_guard import ConstitutionGuard
from .dual_copy_manager import DualCopyManager, ForkError, PromotionError
from .evolution_validator import EvolutionValidator
from .map_elites_archive import MAPElitesArchive
from .ring_enforcer import RingEnforcer

logger = logging.getLogger("uagents.evolution_engine")


class EvolutionError(RuntimeError):
    """Raised when an evolution operation fails non-recoverably."""


class EvolutionRejectedError(RuntimeError):
    """Raised when a proposal is rejected (constitutional, tier, or safety)."""


class ObjectiveAlignmentError(RuntimeError):
    """Raised when objective alignment drops below threshold.

    This is a non-recoverable error that requires human intervention.
    Evolution must be paused until the human investigates.
    The EvolutionEngine sets a persistent pause flag (FM-P4-48).
    """


class EvolutionEngineState(FrameworkModel):
    """Persistent state for the evolution engine (FM-P4-23-FIX).

    Persisted to: state/evolution/engine-state.yaml
    Survives process restarts.
    """

    evolution_count: int = 0
    tasks_since_last_evolution: int = 0
    paused: bool = False  # FM-P4-48-FIX: persistent pause flag
    pause_reason: str = ""


class EvolutionEngine:
    """Drives the 8-step evolution lifecycle.

    Design invariants:
    - Only Tier 3 proposals are auto-approved (Phase 4)
    - Constitutional check before every evaluation
    - Dual-copy isolation for all changes
    - RingEnforcer verifies modified files post-promotion (FM-P4-29)
    - Objective anchoring every N cycles
    - Every step logged to evolution audit stream
    - Ring 0/1 NEVER modified
    - Cooldown enforced between evolution cycles
    - Persistent state survives restarts (FM-P4-23)
    - Persistent pause flag on alignment failure (FM-P4-48)

    Usage:
        engine = EvolutionEngine(yaml_store, git_ops, constitution_guard,
                                 dual_copy_mgr, validator, archive,
                                 audit_logger, ring_enforcer)
        record = engine.run_evolution(proposal)
        # record.outcome is PROMOTED, ROLLED_BACK, REJECTED, or HELD
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        git_ops: GitOps,
        constitution_guard: ConstitutionGuard,
        dual_copy_manager: DualCopyManager,
        validator: EvolutionValidator,
        archive: MAPElitesArchive,
        audit_logger: AuditLogger,
        ring_enforcer: RingEnforcer,  # FM-P4-29-FIX: Required, not optional
        domain: str = "meta",
    ):
        self.yaml_store = yaml_store
        self.git_ops = git_ops
        self.constitution_guard = constitution_guard
        self.dual_copy_manager = dual_copy_manager
        self.validator = validator
        self.archive = archive
        self.audit_logger = audit_logger
        self.ring_enforcer = ring_enforcer
        self.domain = domain

        # Load config (fail-loud if missing)
        config_raw = yaml_store.read_raw("core/evolution.yaml")
        evo = config_raw["evolution"]

        # IFM-N53: Direct dict access — missing keys raise KeyError
        lifecycle = evo["lifecycle"]
        evaluation = evo["evaluation"]
        safety = evo["safety"]
        anchoring = evo["objective_anchoring"]

        self._max_proposals_per_cycle = int(lifecycle["max_proposals_per_cycle"])
        self._max_concurrent_candidates = int(lifecycle["max_concurrent_candidates"])  # FM-P4-43-FIX
        self._cooldown_between_evolutions = int(lifecycle["cooldown_between_evolutions"])
        self._proposal_timeout_min = int(lifecycle["proposal_timeout_minutes"])

        self._promote_threshold = float(evaluation["promote_threshold"])
        self._hold_threshold = float(evaluation["hold_threshold"])

        self._max_file_modifications = int(safety["max_file_modifications_per_proposal"])
        self._max_diff_lines = int(safety["max_diff_lines"])
        self._forbidden_patterns: list[str] = safety["forbidden_path_patterns"]
        self._allowed_extensions: list[str] = safety["allowed_extensions"]

        self._anchoring_interval = int(anchoring["check_every_n_cycles"])
        self._min_alignment_score = float(anchoring["min_alignment_score"])

        # FM-P4-19-FIX: Instance prefix for git paths
        self._instance_prefix = f"instances/{domain}/"

        # Persistence paths
        self._base = f"state/evolution"
        self._proposals_dir = f"{self._base}/proposals"
        self._records_dir = f"{self._base}/records"
        self._evaluations_dir = f"{self._base}/evaluations"
        self._state_path = f"{self._base}/engine-state.yaml"

        # FM-P4-23-FIX: Load persistent state (evolution count, cooldown, pause flag)
        self._state = self._load_state()

    @property
    def _evolution_count(self) -> int:
        return self._state.evolution_count

    @property
    def _tasks_since_last_evolution(self) -> int:
        return self._state.tasks_since_last_evolution

    def record_task_completion(self) -> None:
        """Called after each task verdict (pass or fail) to track cooldown.

        FM-P4-46-FIX: Called on ALL verdicts, not just pass.
        The cooldown prevents evolution from running too frequently.
        """
        self._state.tasks_since_last_evolution += 1
        self._save_state()

    def can_evolve(self) -> bool:
        """Check if evolution is allowed (cooldown elapsed and not paused)."""
        if self._state.paused:
            return False
        return self._state.tasks_since_last_evolution >= self._cooldown_between_evolutions

    def is_paused(self) -> bool:
        """Check if evolution is paused (FM-P4-48)."""
        return self._state.paused

    def unpause(self, reason: str = "Human cleared pause") -> None:
        """Unpause evolution. Only called by explicit human action (FM-P4-48)."""
        self._state.paused = False
        self._state.pause_reason = reason
        self._save_state()
        logger.info(f"Evolution unpaused: {reason}")

    def run_evolution(self, proposal: EvolutionProposal) -> EvolutionRecord:
        """Execute the full 8-step evolution lifecycle for a proposal.

        Steps:
        1. OBSERVE — already done (trigger is in proposal)
        2. ATTRIBUTE — already done (evidence is in proposal)
        3. PROPOSE — validate proposal safety + diff format
        4. EVALUATE — constitutional check + dual-copy evaluation
        5. APPROVE — tier-based (Tier 3 auto in Phase 4)
        6. COMMIT — promote fork + Git commit (with error recovery)
        7. VERIFY — post-commit verification + Ring 0 check
        8. LOG — full record to audit stream

        Args:
            proposal: The evolution proposal to evaluate.

        Returns:
            EvolutionRecord with outcome (PROMOTED, REJECTED, HELD, ROLLED_BACK).

        Raises:
            EvolutionError: On non-recoverable failures (Git, IO).
            ObjectiveAlignmentError: When objective alignment is too low.
        """
        now = datetime.now(timezone.utc)

        # FM-P4-48-FIX: Check persistent pause flag
        if self._state.paused:
            return self._reject(
                proposal,
                f"Evolution paused: {self._state.pause_reason}",
                now,
            )

        # DR-09-FIX: Track lifecycle state as local variable, not mutating proposal
        current_state = EvolutionLifecycleState.PROPOSE

        # ── Step 3: PROPOSE — validate safety ──
        self._log_lifecycle(proposal, current_state)

        # 3a. Tier check: Phase 4 only allows Tier 3
        tier_int = int(proposal.tier)

        if tier_int != EvolutionTier.OPERATIONAL:
            reason = (
                f"Phase 4 only supports Tier 3 (operational) evolution. "
                f"Received Tier {tier_int}. Tier 0-2 evolutions require Phase 5."
            )
            return self._reject(proposal, reason, now)

        # 3b. Safety checks
        safety_ok, safety_reason = self._check_proposal_safety(proposal)
        if not safety_ok:
            return self._reject(proposal, safety_reason, now)

        # 3c. Constitutional check
        const_ok, const_reason = self.constitution_guard.check_proposal(proposal)
        if not const_ok:
            return self._reject(proposal, f"Constitutional: {const_reason}", now)

        # FM-P4-34-FIX: Validate diff format (YAML) before creating fork
        try:
            yaml.safe_load(proposal.diff)
        except yaml.YAMLError as e:
            return self._reject(proposal, f"Diff is not valid YAML: {e}", now)

        # FM-P4-43-FIX: Check concurrent candidate limit
        candidates_dir = self.yaml_store.base_dir / self._base / "candidates"
        if candidates_dir.exists():
            existing = [d for d in candidates_dir.iterdir() if d.is_dir()]
            if len(existing) >= self._max_concurrent_candidates:
                return self._reject(
                    proposal,
                    f"Concurrent candidate limit ({self._max_concurrent_candidates}) reached. "
                    f"Wait for existing evolution to complete.",
                    now,
                )

        # ── Step 4: EVALUATE — dual-copy evaluation ──
        current_state = EvolutionLifecycleState.EVALUATE
        self._log_lifecycle(proposal, current_state)

        # FM-P4-34-FIX: Wrap fork+eval in try/except for cleanup
        candidate: DualCopyCandidate | None = None
        try:
            # 4a. Create fork
            candidate = self.dual_copy_manager.create_fork(proposal)

            # 4b. Apply diff to fork
            self.dual_copy_manager.apply_diff(candidate, proposal)

            # FM-P4-27-FIX: Check file count after apply_diff
            if len(candidate.modified_files) > self._max_file_modifications:
                self.dual_copy_manager.cleanup_fork(candidate)
                return self._reject(
                    proposal,
                    f"Modified {len(candidate.modified_files)} files, exceeds "
                    f"max of {self._max_file_modifications}",
                    now,
                )

            # FM-P4-42-FIX: Re-persist manifest after apply_diff
            self.dual_copy_manager.persist_manifest(candidate)

            # 4c. Evaluate fork
            evaluation = self.validator.evaluate(candidate, proposal)

        except ForkError as e:
            if candidate is not None:
                self.dual_copy_manager.cleanup_fork(candidate)
            return self._reject(proposal, f"Fork error: {e}", now)

        # Persist evaluation
        self.yaml_store.write(
            f"{self._evaluations_dir}/{evaluation.id}.yaml", evaluation
        )

        # ── Step 5: APPROVE — determine outcome ──
        current_state = EvolutionLifecycleState.APPROVE
        self._log_lifecycle(proposal, current_state)

        verdict_str = str(evaluation.verdict)
        if verdict_str == str(EvolutionOutcome.REJECTED):
            self.dual_copy_manager.cleanup_fork(candidate)
            return self._reject(
                proposal,
                f"Evaluation failed: {evaluation.verdict_reason}",
                now,
                evaluation=evaluation,
            )

        if verdict_str == str(EvolutionOutcome.HELD):
            self.dual_copy_manager.cleanup_fork(candidate)
            return self._hold(proposal, evaluation, now)

        # ── Step 6: COMMIT — promote fork + git commit ──
        current_state = EvolutionLifecycleState.COMMIT
        self._log_lifecycle(proposal, current_state)

        rollback_sha = self.git_ops.create_rollback_point()

        # DR-05/FM-P4-20-FIX: Wrap promote + commit in try/except
        evolution_sha = ""
        try:
            # Promote: copy fork files to active positions
            self.dual_copy_manager.promote(candidate)

            # FM-P4-19-FIX: Prepend instance prefix to file paths for git
            git_files = [
                f"{self._instance_prefix}{f}" for f in candidate.modified_files
            ]

            # Git commit
            evolution_sha = self.git_ops.commit_evolution(
                evo_id=proposal.id,
                tier=tier_int,
                rationale=proposal.rationale,
                approved_by="auto (tier 3)",
                files=git_files,
            )
        except (GitOpsError, PromotionError) as e:
            # Rollback promoted files if promotion happened
            logger.error(f"Commit failed for {proposal.id}: {e}")
            if candidate.promoted:
                try:
                    self.git_ops.rollback_to(rollback_sha)
                except GitOpsError as re:
                    logger.error(f"Rollback also failed: {re}")
            self.dual_copy_manager.cleanup_fork(candidate)
            return self._reject(
                proposal, f"Commit failed: {e}", now, evaluation=evaluation
            )

        # ── Step 7: VERIFY — post-commit checks ──
        current_state = EvolutionLifecycleState.VERIFY
        self._log_lifecycle(proposal, current_state)

        # FM-P4-29-FIX: RingEnforcer verifies no Ring 0 files modified
        git_files = [
            f"{self._instance_prefix}{f}" for f in candidate.modified_files
        ]
        ring_violation = self.ring_enforcer.verify_no_ring_0_modification(git_files)
        verification_ok = self._verify_post_commit() and not ring_violation

        if not verification_ok:
            # FM-P4-37-FIX: Only rollback if evolution_sha != rollback_sha
            if evolution_sha and evolution_sha != rollback_sha:
                logger.error(
                    f"Post-commit verification failed for {proposal.id}. "
                    f"Rolling back to {rollback_sha[:8]}."
                )
                try:
                    self.git_ops.rollback_to(rollback_sha)
                except GitOpsError as e:
                    logger.error(f"Rollback failed: {e}")
            self.dual_copy_manager.cleanup_fork(candidate)

            record = EvolutionRecord(
                id=generate_id("evo-rec"),
                created_at=now,
                proposal=proposal,
                evaluation=evaluation,
                approved_by="auto (tier 3)",
                constitutional_check="pass",
                rollback_commit=rollback_sha,
                evolution_commit=evolution_sha,
                outcome=EvolutionOutcome.ROLLED_BACK,
                verification_passed=False,
            )
            self._persist_record(record)
            self._log_outcome(record)
            return record

        # ── Step 8: LOG — success ──
        self.dual_copy_manager.cleanup_fork(candidate)

        record = EvolutionRecord(
            id=generate_id("evo-rec"),
            created_at=now,
            proposal=proposal,
            evaluation=evaluation,
            approved_by="auto (tier 3)",
            constitutional_check="pass",
            rollback_commit=rollback_sha,
            evolution_commit=evolution_sha,
            outcome=EvolutionOutcome.PROMOTED,
            verification_passed=True,
        )
        self._persist_record(record)
        self._log_outcome(record)

        # Track evolution count and reset cooldown (FM-P4-23: persisted)
        self._state.evolution_count += 1
        self._state.tasks_since_last_evolution = 0
        self._save_state()

        # DR-18-FIX: Archive update after counter update (non-fatal)
        try:
            self.archive.update_from_evolution(record)
        except Exception as e:
            logger.warning(f"Archive update failed for {record.id}: {e}")

        # Objective anchoring check
        if self._state.evolution_count % self._anchoring_interval == 0:
            self._check_objective_alignment()

        return record

    def create_proposal(
        self,
        component: str,
        diff: str,
        rationale: str,
        trigger: ObservationTrigger = ObservationTrigger.MANUAL,
        trigger_detail: str = "",
        evidence: dict | None = None,
        estimated_risk: float = 0.3,
    ) -> EvolutionProposal:
        """Create a new Tier 3 evolution proposal.

        Args:
            component: File path being modified (relative to instance root).
            diff: YAML-formatted diff of proposed changes.
            rationale: Why this change is needed (required).
            trigger: What triggered this proposal.
            trigger_detail: Additional trigger context (e.g., task_id).
            evidence: Supporting evidence dict.
            estimated_risk: Estimated risk (0.0-1.0).

        Returns:
            EvolutionProposal ready for run_evolution().
        """
        now = datetime.now(timezone.utc)
        proposal = EvolutionProposal(
            id=generate_id("evo"),
            created_at=now,
            tier=EvolutionTier.OPERATIONAL,
            component=component,
            diff=diff,
            rationale=rationale,
            evidence=evidence or {},
            estimated_risk=estimated_risk,
            trigger=trigger,
            trigger_detail=trigger_detail,
            lifecycle_state=EvolutionLifecycleState.OBSERVE,
        )

        # Persist proposal
        self.yaml_store.write(
            f"{self._proposals_dir}/{proposal.id}.yaml", proposal
        )

        return proposal

    def get_evolution_count(self) -> int:
        """Return the total number of successful evolutions."""
        return self._state.evolution_count

    # ── Private helpers ──

    def _check_proposal_safety(
        self, proposal: EvolutionProposal
    ) -> tuple[bool, str]:
        """Validate proposal against safety constraints.

        Checks:
        1. Component path not in forbidden patterns (path-aware matching)
        2. Component extension is allowed
        3. Diff size within limits

        FM-P4-30-FIX: Use path-aware matching via Path comparison
        instead of simple substring matching.
        FM-P4-27: File count checked after apply_diff in run_evolution().
        """
        component = proposal.component
        component_path = Path(component)

        # 1. Forbidden path patterns — path-aware matching
        for pattern in self._forbidden_patterns:
            pattern_path = Path(pattern)
            # Check if component starts with the forbidden pattern
            # or if the forbidden pattern name is the component name
            try:
                if component_path.is_relative_to(pattern_path):
                    return False, f"Component '{component}' is under forbidden path '{pattern}'"
            except (TypeError, ValueError):
                pass
            # Also check exact filename match (e.g., "CONSTITUTION.md")
            if component_path.name.lower() == pattern_path.name.lower():
                return False, f"Component filename '{component_path.name}' matches forbidden '{pattern}'"

        # 2. Allowed extensions
        extension = component_path.suffix
        if extension not in self._allowed_extensions:
            return False, (
                f"Component extension '{extension}' not in allowed list: "
                f"{self._allowed_extensions}"
            )

        # 3. Diff size
        diff_lines = len(proposal.diff.strip().split("\n")) if proposal.diff.strip() else 0
        if diff_lines > self._max_diff_lines:
            return False, (
                f"Diff has {diff_lines} lines, exceeds maximum of "
                f"{self._max_diff_lines}"
            )

        return True, "Safety checks passed"

    def _reject(
        self,
        proposal: EvolutionProposal,
        reason: str,
        now: datetime,
        evaluation: EvaluationResult | None = None,
    ) -> EvolutionRecord:
        """Create a rejected evolution record."""
        logger.info(f"Evolution {proposal.id} rejected: {reason}")

        record = EvolutionRecord(
            id=generate_id("evo-rec"),
            created_at=now,
            proposal=proposal,
            evaluation=evaluation,
            approved_by="rejected",
            constitutional_check="fail" if "Constitutional" in reason else "pass",
            # FM-P4-17: Empty string for rejected records (no rollback point)
            rollback_commit="",
            outcome=EvolutionOutcome.REJECTED,
            verification_passed=False,
        )
        self._persist_record(record)
        self._log_outcome(record)
        return record

    def _hold(
        self,
        proposal: EvolutionProposal,
        evaluation: EvaluationResult,
        now: datetime,
    ) -> EvolutionRecord:
        """Create a held-for-human evolution record."""
        logger.info(
            f"Evolution {proposal.id} held for human review: "
            f"score {evaluation.overall_score:.2f} is marginal"
        )

        record = EvolutionRecord(
            id=generate_id("evo-rec"),
            created_at=now,
            proposal=proposal,
            evaluation=evaluation,
            approved_by="held_for_human",
            constitutional_check="pass",
            rollback_commit="",
            outcome=EvolutionOutcome.HELD,
            verification_passed=False,
        )
        self._persist_record(record)
        self._log_outcome(record)
        return record

    def _verify_post_commit(self) -> bool:
        """Verify framework is still operational after commit.

        Checks:
        1. Constitution hash still valid
        2. evolution.yaml still parseable (FM-P4-39: detect self-modification)
        """
        # 1. Constitution hash
        if not self.constitution_guard.verify_hash():
            logger.error("Post-commit verification: constitution hash INVALID")
            return False

        # 2. FM-P4-39-FIX: Verify evolution.yaml still loads correctly
        try:
            self.yaml_store.read_raw("core/evolution.yaml")
        except Exception as e:
            logger.error(f"Post-commit verification: evolution.yaml load failed: {e}")
            return False

        return True

    def _check_objective_alignment(self) -> None:
        """Check if current behavior aligns with constitutional objectives.

        Called every N evolution cycles (objective_anchoring.check_every_n_cycles).
        If alignment score drops below threshold, pauses evolution and raises
        ObjectiveAlignmentError.

        DR-04/FM-P4-21-FIX: Scans records directory instead of reading it as file.
        FM-P4-48-FIX: Sets persistent pause flag on alignment failure.

        Phase 4 heuristic: if >50% of recent evolutions were REJECTED or
        ROLLED_BACK, alignment may be drifting. Phase 5 adds independent evaluator.
        """
        # Scan evolution records directory
        records_dir = self.yaml_store.base_dir / self._records_dir
        if not records_dir.exists() or not records_dir.is_dir():
            # No records yet — alignment is trivially satisfied
            logger.info("Objective alignment check: no records found (OK)")
            return

        # Load last 10 records
        record_files = sorted(
            f for f in records_dir.iterdir() if f.suffix in (".yaml", ".yml")
        )
        recent = record_files[-10:] if len(record_files) >= 10 else record_files

        if not recent:
            return

        # Count outcomes
        rejected_or_rolled_back = 0
        total = 0
        for rf in recent:
            try:
                data = self.yaml_store.read_raw(
                    str(rf.relative_to(self.yaml_store.base_dir))
                )
                outcome = data.get("outcome", "")
                total += 1
                if outcome in ("rejected", "rolled_back"):
                    rejected_or_rolled_back += 1
            except Exception:
                continue

        if total == 0:
            return

        failure_rate = rejected_or_rolled_back / total
        logger.info(
            f"Objective alignment check at evolution #{self._state.evolution_count}: "
            f"{rejected_or_rolled_back}/{total} failed ({failure_rate:.0%})"
        )

        if failure_rate > 0.5:
            # FM-P4-48-FIX: Set persistent pause flag
            self._state.paused = True
            self._state.pause_reason = (
                f"Objective alignment concern: {failure_rate:.0%} of recent "
                f"evolutions failed. Human review required."
            )
            self._save_state()
            raise ObjectiveAlignmentError(
                f"Alignment check failed: {rejected_or_rolled_back}/{total} "
                f"recent evolutions rejected/rolled back ({failure_rate:.0%}). "
                f"Evolution paused. Human intervention required."
            )

    def _persist_record(self, record: EvolutionRecord) -> None:
        """Persist evolution record to disk."""
        self.yaml_store.write(
            f"{self._records_dir}/{record.id}.yaml", record
        )

    def _load_state(self) -> EvolutionEngineState:
        """Load persistent state from disk. Create default if missing (FM-P4-23)."""
        try:
            return self.yaml_store.read(self._state_path, EvolutionEngineState)
        except FileNotFoundError:
            return EvolutionEngineState()

    def _save_state(self) -> None:
        """Persist state to disk (FM-P4-23)."""
        self.yaml_store.write(self._state_path, self._state)

    def _log_lifecycle(
        self,
        proposal: EvolutionProposal,
        state: EvolutionLifecycleState,
    ) -> None:
        """Log a lifecycle state transition to audit stream.

        DR-06-FIX: Narrow exception handling, re-raise critical errors.
        """
        now = datetime.now(timezone.utc)
        tier_int = int(proposal.tier)
        try:
            self.audit_logger.log_evolution(EvolutionLogEntry(
                id=generate_id("evlog"),
                timestamp=now,
                tier=tier_int,
                component=proposal.component,
                diff=proposal.diff[:500],  # Truncate for log
                rationale=proposal.rationale,
                evidence=proposal.evidence,
                lifecycle_state=str(state),
                trigger=str(proposal.trigger),
            ))
        except (OSError, ValueError, TypeError) as e:
            logger.warning(f"Failed to log evolution lifecycle event: {e}")

    def _log_outcome(self, record: EvolutionRecord) -> None:
        """Log the final evolution outcome to audit stream."""
        now = datetime.now(timezone.utc)
        tier_int = int(record.proposal.tier)
        try:
            self.audit_logger.log_evolution(EvolutionLogEntry(
                id=generate_id("evlog"),
                timestamp=now,
                tier=tier_int,
                component=record.proposal.component,
                diff=record.proposal.diff[:500],
                rationale=record.proposal.rationale,
                evidence=record.proposal.evidence,
                lifecycle_state="complete",
                outcome=str(record.outcome),
                evaluation_score=(
                    record.evaluation.overall_score
                    if record.evaluation else 0.0
                ),
                trigger=str(record.proposal.trigger),
            ))
        except (OSError, ValueError, TypeError) as e:
            logger.warning(f"Failed to log evolution outcome: {e}")
```

---

## Part 5: DualCopyManager

### 5.1 Class Definition

```python
"""Dual-copy fork pipeline for evolution evaluation.
Spec reference: Section 8.2 (The Dual-Copy Pattern).

Manages the fork → modify → evaluate → promote/rollback pipeline.
Forks are isolated copies of configuration files stored in
state/evolution/candidates/{evo-id}/. Changes are NEVER applied
in-place until promotion.

Key constraints:
- Fork only Tier 2-3 eligible files (no CONSTITUTION.md, no logs)
- Changes must be expressible as file diffs
- Promotion uses YamlStore atomic writes (tmp + os.replace) — NOT shutil.copy2
- Rollback discards fork and reverts via GitOps
- Fork directory cleaned up after resolution (promote or rollback)
- "old" value verification: diff application checks current values before overwriting

Literature basis:
- Darwin Godel Machine: population of forks evaluated in parallel
- STOP (Microsoft): self-taught optimizer with copy mechanism
- AlphaEvolve: island model with migration between copies
"""
from __future__ import annotations

import fnmatch
import logging
import shutil
from pathlib import Path

import yaml

from ..models.evolution import DualCopyCandidate, EvolutionProposal
from ..models.base import generate_id
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.dual_copy_manager")


class ForkError(RuntimeError):
    """Raised when fork creation or manipulation fails."""


class PromotionError(RuntimeError):
    """Raised when promotion of a fork fails.

    This is a critical error — the active config may be inconsistent.
    GitOps rollback should be triggered immediately.
    """


class DualCopyManager:
    """Manages dual-copy fork pipeline for evolution evaluation.

    Design invariants:
    - Forks are created in candidates_dir/{evo-id}/
    - Source files copied according to fork_includes glob patterns
    - Fork excludes use fnmatch — no substring false positives (FM-P4-31)
    - Promotion uses YamlStore atomic writes — NOT shutil.copy2 (FM-P4-18)
    - Diff application verifies "old" values before overwriting (FM-P4-38)
    - Cleanup removes fork directory entirely
    - All operations are logged
    - instance_root derived from yaml_store.base_dir (DR-07)

    Usage:
        mgr = DualCopyManager(yaml_store, domain)
        candidate = mgr.create_fork(proposal)
        mgr.apply_diff(candidate, proposal)
        # ... evaluate candidate ...
        mgr.promote(candidate)  # or mgr.cleanup_fork(candidate)
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
    ):
        self.yaml_store = yaml_store
        # DR-07: Derive instance_root from yaml_store.base_dir
        # (yaml_store.base_dir IS the instance root, e.g., instances/meta/)
        # This eliminates the separate instance_root parameter that caused
        # path confusion in DR-07.
        self.instance_root = Path(yaml_store.base_dir).resolve()
        self.domain = domain

        # Load config (fail-loud if missing)
        config_raw = yaml_store.read_raw("core/evolution.yaml")
        dc = config_raw["evolution"]["dual_copy"]

        # IFM-N53: Direct dict access
        self._fork_includes: list[str] = dc["fork_includes"]
        self._fork_excludes: list[str] = dc["fork_excludes"]
        self._candidates_dir = str(dc["candidates_dir"])

    def create_fork(self, proposal: EvolutionProposal) -> DualCopyCandidate:
        """Create an isolated fork for evaluating a proposal.

        Copies relevant source files into candidates_dir/{evo-id}/.
        Only files matching fork_includes glob patterns are copied.
        Files matching fork_excludes (via fnmatch) are skipped.

        FM-P4-44: Checks available disk space before creating fork.

        Args:
            proposal: The evolution proposal to fork for.

        Returns:
            DualCopyCandidate with fork path and source file list.

        Raises:
            ForkError: If fork directory creation or file copy fails,
                       or if insufficient disk space.
        """
        fork_dir = self.instance_root / self._candidates_dir / proposal.id
        if fork_dir.exists():
            raise ForkError(
                f"Fork directory already exists: {fork_dir}. "
                f"A previous fork for {proposal.id} was not cleaned up."
            )

        # FM-P4-44: Check disk space before fork creation
        # Estimate: fork copies at most a few MB of YAML configs.
        # Require at least 50MB free to be safe.
        import shutil as shutil_mod
        disk_usage = shutil_mod.disk_usage(str(self.instance_root))
        min_free_bytes = 50 * 1024 * 1024  # 50 MB
        if disk_usage.free < min_free_bytes:
            raise ForkError(
                f"Insufficient disk space for fork: "
                f"{disk_usage.free / (1024*1024):.1f} MB free, "
                f"minimum {min_free_bytes / (1024*1024):.0f} MB required"
            )

        fork_dir.mkdir(parents=True, exist_ok=False)
        logger.info(f"Created fork directory: {fork_dir}")

        # Copy source files matching includes
        source_files: list[str] = []
        for pattern in self._fork_includes:
            matched = list(self.instance_root.glob(pattern))
            for src_file in matched:
                rel_path = str(src_file.relative_to(self.instance_root))
                # FM-P4-31: Use fnmatch for exclude checking
                if self._is_excluded(rel_path):
                    continue
                dest = fork_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                # FM-P4-24: Write fork files atomically (tmp + rename)
                self._atomic_copy(src_file, dest)
                source_files.append(rel_path)

        # Also copy the target file if not already included
        target_rel = proposal.component
        target_src = self.instance_root / target_rel
        if target_src.exists() and target_rel not in source_files:
            if not self._is_excluded(target_rel):
                dest = fork_dir / target_rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                self._atomic_copy(target_src, dest)
                source_files.append(target_rel)

        candidate = DualCopyCandidate(
            evo_id=proposal.id,
            fork_path=str(fork_dir.relative_to(self.instance_root)),
            source_files=source_files,
        )

        # Persist manifest via YamlStore (atomic write)
        self._persist_manifest(candidate, proposal.id)

        logger.info(
            f"Fork {proposal.id} created with {len(source_files)} source files"
        )
        return candidate

    def apply_diff(
        self, candidate: DualCopyCandidate, proposal: EvolutionProposal
    ) -> None:
        """Apply the proposal's diff to the forked copy.

        In Phase 4, diffs are YAML value changes represented as key-value
        pairs in the proposal.diff field. The diff format is:

            file: <relative_path>
            changes:
              - key: <dotted.yaml.path>
                old: <old_value>
                new: <new_value>

        FM-P4-38: Each change verifies the "old" value matches the current
        value before overwriting. This prevents applying diffs against stale
        data (e.g., if the file was modified between proposal and application).

        For Phase 4 (Tier 3 operational changes), this means modifying
        YAML config values like thresholds, behavioral descriptors,
        and capability parameters.

        Args:
            candidate: The fork to modify.
            proposal: The proposal containing the diff.

        Raises:
            ForkError: If diff application fails, or old value mismatch detected.
        """
        fork_dir = self.instance_root / candidate.fork_path
        target_file = fork_dir / proposal.component

        if not target_file.exists():
            raise ForkError(
                f"Target file does not exist in fork: {target_file}. "
                f"Ensure the component '{proposal.component}' was included in fork."
            )

        try:
            current_content = yaml.safe_load(
                target_file.read_text(encoding="utf-8")
            )
            if current_content is None:
                current_content = {}

            # Parse diff as YAML change spec
            diff_spec = yaml.safe_load(proposal.diff)
            if diff_spec is None:
                raise ForkError("Diff is empty — nothing to apply")

            changes = diff_spec.get("changes", [])
            if not changes:
                raise ForkError("Diff has no 'changes' key or it is empty")

            for change in changes:
                key_path = change["key"]
                new_value = change["new"]

                # FM-P4-38: Verify "old" value before overwriting
                if "old" in change:
                    expected_old = change["old"]
                    actual_old = self._get_nested_value(current_content, key_path)
                    if actual_old != expected_old:
                        raise ForkError(
                            f"Old value mismatch at '{key_path}': "
                            f"expected {expected_old!r}, found {actual_old!r}. "
                            f"File may have been modified since proposal creation."
                        )

                self._set_nested_value(current_content, key_path, new_value)

            # Write back atomically (tmp + rename within fork dir)
            tmp_file = target_file.with_suffix(".tmp")
            tmp_file.write_text(
                yaml.dump(
                    current_content,
                    default_flow_style=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )
            tmp_file.replace(target_file)

            candidate.modified_files.append(proposal.component)
            logger.info(
                f"Applied {len(changes)} changes to {proposal.component} "
                f"in fork {candidate.evo_id}"
            )

        except ForkError:
            raise  # Re-raise our own errors without wrapping
        except (yaml.YAMLError, KeyError, TypeError) as e:
            raise ForkError(
                f"Failed to apply diff to {proposal.component}: {e}"
            ) from e

    def promote(self, candidate: DualCopyCandidate) -> None:
        """Promote a fork by copying modified files to active positions.

        FM-P4-18: Uses YamlStore's atomic write mechanism (tmp + os.replace)
        instead of shutil.copy2. This ensures promotion is atomic per-file —
        if we crash mid-promotion, each file is either fully old or fully new,
        never a partial copy.

        This is the critical operation — it replaces active config files
        with the fork's versions. Must be followed by Git commit.

        Args:
            candidate: The evaluated and approved candidate.

        Raises:
            PromotionError: If any file copy fails.
        """
        fork_dir = self.instance_root / candidate.fork_path

        for rel_path in candidate.modified_files:
            src = fork_dir / rel_path
            dest = self.instance_root / rel_path

            if not src.exists():
                raise PromotionError(
                    f"Modified file missing from fork: {src}. "
                    f"Fork may be corrupted."
                )

            # FM-P4-18: Read the fork content and write via YamlStore
            # for atomic promotion. YamlStore.write_raw() uses tmp + os.replace.
            try:
                content = yaml.safe_load(src.read_text(encoding="utf-8"))
                self.yaml_store.write_raw(rel_path, content)
            except (OSError, yaml.YAMLError) as e:
                raise PromotionError(
                    f"Atomic promotion failed for {rel_path}: {e}"
                ) from e

            logger.info(f"Promoted {rel_path} from fork {candidate.evo_id}")

        candidate.promoted = True
        logger.info(
            f"Fork {candidate.evo_id} promoted: "
            f"{len(candidate.modified_files)} files updated"
        )

    def cleanup_fork(self, candidate: DualCopyCandidate) -> None:
        """Remove fork directory after resolution (promote or rollback).

        Safe to call multiple times — no-op if already cleaned up.

        Args:
            candidate: The resolved candidate to clean up.
        """
        fork_dir = self.instance_root / candidate.fork_path
        if fork_dir.exists():
            shutil.rmtree(str(fork_dir))
            logger.info(f"Cleaned up fork directory: {fork_dir}")

    def _persist_manifest(
        self, candidate: DualCopyCandidate, proposal_id: str
    ) -> None:
        """Persist fork manifest via YamlStore (atomic write).

        FM-P4-42: Separate method for manifest persistence, used by both
        create_fork() and EvolutionEngine after apply_diff().
        """
        manifest_path = f"{self._candidates_dir}/{proposal_id}/manifest.yaml"
        self.yaml_store.write(manifest_path, candidate)

    def _is_excluded(self, rel_path: str) -> bool:
        """Check if a relative path matches any exclude pattern.

        FM-P4-31: Uses fnmatch for glob-style pattern matching instead of
        substring matching, which caused false positives (e.g., "state/"
        substring matching "estate/" or files containing "state" anywhere).
        """
        for exclude in self._fork_excludes:
            # fnmatch supports *, ?, [seq] patterns
            if fnmatch.fnmatch(rel_path, exclude):
                return True
            # Also check if any path component matches (for patterns like "logs/*")
            # by checking if the exclude matches the path as a prefix
            if exclude.endswith("*"):
                prefix = exclude[:-1]  # Remove trailing *
                if rel_path.startswith(prefix):
                    return True
        return False

    @staticmethod
    def _atomic_copy(src: Path, dest: Path) -> None:
        """Copy a file atomically: write to tmp, then os.replace.

        FM-P4-24: Ensures fork files are never partially written.
        """
        import os
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        shutil.copy2(str(src), str(tmp))
        os.replace(str(tmp), str(dest))

    @staticmethod
    def _get_nested_value(data: dict, dotted_key: str):
        """Get a value from a nested dict using dotted key path.

        FM-P4-38: Used to verify "old" values before overwriting.
        Raises KeyError if any key in the path is missing.
        """
        keys = dotted_key.split(".")
        current = data
        for key in keys:
            current = current[key]  # KeyError if missing — fail-loud
        return current

    @staticmethod
    def _set_nested_value(data: dict, dotted_key: str, value) -> None:
        """Set a value in a nested dict using dotted key path.

        Example: _set_nested_value(d, "a.b.c", 42) sets d["a"]["b"]["c"] = 42.

        Raises KeyError if any intermediate key is missing.
        """
        keys = dotted_key.split(".")
        current = data
        for key in keys[:-1]:
            current = current[key]  # KeyError if missing — fail-loud
        current[keys[-1]] = value
```

---

## Part 6: EvolutionValidator

### 6.1 Class Definition

```python
"""Multi-dimensional evolution validator.
Spec reference: Section 8.2 (Dual-Copy, step 3_evaluate).

Evaluates fork candidates on 6 dimensions:
1. Capability — Does it perform tasks better?
2. Consistency — Reproducible results across runs?
3. Robustness — Handles edge cases?
4. Predictability — Can we anticipate failures?
5. Safety — Constitutional compliance?
6. Diversity — Maintains SRD above floor?

The validator is STRUCTURALLY INDEPENDENT from the evolution engine.
This enforces the generation-verification gap (Song et al. 2024):
the system that proposes changes cannot also evaluate them.

Key constraints:
- Each dimension produces a 0.0-1.0 score
- Overall score is weighted average of dimensions
- Verdict: promote if >= promote_threshold, hold if >= hold_threshold, else rollback
- Per-dimension minimums: any dimension below its minimum → rollback
- Safety dimension has the highest minimum (0.9)

Literature basis:
- Song et al. 2024: generation-verification gap
- SWE-Pruner: task-aware pruning (23-54% reduction)
- DGM: multi-dimensional fitness evaluation
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.base import generate_id
from ..models.evolution import (
    DimensionScore,
    DualCopyCandidate,
    EvaluationDimension,
    EvaluationResult,
    EvolutionOutcome,
    EvolutionProposal,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.evolution_validator")


class EvolutionValidator:
    """Multi-dimensional evaluation of evolution candidates.

    Design invariants:
    - Structurally independent from EvolutionEngine (generation-verification gap)
    - Each dimension scored independently (0.0-1.0)
    - Per-dimension minimums enforced (any below → rollback)
    - Overall score is weighted average
    - Verdict determined by thresholds: promote / hold / rollback
    - Safety dimension has highest bar (0.9 minimum)

    Usage:
        validator = EvolutionValidator(yaml_store)
        result = validator.evaluate(candidate, proposal)
        # result.verdict is PROMOTED, HELD, or REJECTED
    """

    def __init__(self, yaml_store: YamlStore):
        self.yaml_store = yaml_store

        # Load config (fail-loud if missing)
        config_raw = yaml_store.read_raw("core/evolution.yaml")
        ev = config_raw["evolution"]["evaluation"]

        # IFM-N53: Direct dict access
        self._min_scores = {
            EvaluationDimension.CAPABILITY: float(ev["min_capability"]),
            EvaluationDimension.CONSISTENCY: float(ev["min_consistency"]),
            EvaluationDimension.ROBUSTNESS: float(ev["min_robustness"]),
            EvaluationDimension.PREDICTABILITY: float(ev["min_predictability"]),
            EvaluationDimension.SAFETY: float(ev["min_safety"]),
            EvaluationDimension.DIVERSITY: float(ev["min_diversity"]),
        }

        weights = ev["weights"]
        self._weights = {
            EvaluationDimension.CAPABILITY: float(weights["capability"]),
            EvaluationDimension.CONSISTENCY: float(weights["consistency"]),
            EvaluationDimension.ROBUSTNESS: float(weights["robustness"]),
            EvaluationDimension.PREDICTABILITY: float(weights["predictability"]),
            EvaluationDimension.SAFETY: float(weights["safety"]),
            EvaluationDimension.DIVERSITY: float(weights["diversity"]),
        }

        # FM-P4-45: Validate all weights are non-negative
        for dim_name, w in self._weights.items():
            if w < 0.0:
                raise ValueError(
                    f"Evaluation weight for {dim_name} is negative ({w}). "
                    f"All weights must be >= 0.0."
                )

        self._promote_threshold = float(ev["promote_threshold"])
        self._hold_threshold = float(ev["hold_threshold"])

    def evaluate(
        self,
        candidate: DualCopyCandidate,
        proposal: EvolutionProposal,
    ) -> EvaluationResult:
        """Evaluate a fork candidate on all 6 dimensions.

        Phase 4 evaluation strategy:
        - Capability: Based on estimated risk (inverse — lower risk = higher score)
        - Consistency: Based on whether the change is a simple YAML value change
        - Robustness: Based on number of files modified (fewer = more robust)
        - Predictability: Based on diff size (smaller = more predictable)
        - Safety: Constitutional check + ring hierarchy check
        - Diversity: Based on whether the change affects diversity-relevant configs

        These are conservative heuristics for Phase 4. Phase 5 will add
        actual task-based evaluation (run tasks against both configs).

        Args:
            candidate: The fork to evaluate.
            proposal: The original proposal.

        Returns:
            EvaluationResult with per-dimension scores, overall score, and verdict.
        """
        now = datetime.now(timezone.utc)
        dimension_scores: list[DimensionScore] = []

        # Score each dimension
        for dim in EvaluationDimension:
            # use_enum_values means dim is a string after iteration
            dim_str = dim if isinstance(dim, str) else str(dim)
            score = self._score_dimension(dim_str, candidate, proposal)
            dimension_scores.append(score)

        # Check per-dimension minimums
        failed_dimensions: list[str] = []
        for ds in dimension_scores:
            dim_enum = ds.dimension
            dim_key = dim_enum if isinstance(dim_enum, str) else str(dim_enum)
            min_score = self._min_scores.get(dim_key, 0.0)
            if ds.score < min_score:
                failed_dimensions.append(
                    f"{dim_key}: {ds.score:.2f} < {min_score:.2f}"
                )

        # Compute overall score (weighted average)
        overall = 0.0
        total_weight = 0.0
        for ds in dimension_scores:
            dim_key = ds.dimension if isinstance(ds.dimension, str) else str(ds.dimension)
            w = self._weights.get(dim_key, 0.0)
            overall += ds.score * w
            total_weight += w

        if total_weight > 0:
            overall = overall / total_weight

        # Determine verdict
        if failed_dimensions:
            verdict = EvolutionOutcome.REJECTED
            verdict_reason = (
                f"Dimensions below minimum: {'; '.join(failed_dimensions)}"
            )
        elif overall >= self._promote_threshold:
            verdict = EvolutionOutcome.PROMOTED
            verdict_reason = f"Overall score {overall:.2f} >= promote threshold {self._promote_threshold}"
        elif overall >= self._hold_threshold:
            verdict = EvolutionOutcome.HELD
            verdict_reason = (
                f"Overall score {overall:.2f} between hold ({self._hold_threshold}) "
                f"and promote ({self._promote_threshold}) — marginal improvement"
            )
        else:
            verdict = EvolutionOutcome.REJECTED
            verdict_reason = (
                f"Overall score {overall:.2f} below hold threshold {self._hold_threshold}"
            )

        return EvaluationResult(
            id=generate_id("eval"),
            created_at=now,
            proposal_id=proposal.id,
            candidate_id=candidate.evo_id,
            dimension_scores=dimension_scores,
            overall_score=overall,
            verdict=verdict,
            verdict_reason=verdict_reason,
        )

    def _score_dimension(
        self,
        dimension: str,
        candidate: DualCopyCandidate,
        proposal: EvolutionProposal,
    ) -> DimensionScore:
        """Score a single evaluation dimension.

        Phase 4 heuristics — conservative scoring based on proposal
        characteristics. Phase 5 will add task-based evaluation.
        """
        if dimension == EvaluationDimension.CAPABILITY:
            return self._score_capability(proposal)
        elif dimension == EvaluationDimension.CONSISTENCY:
            return self._score_consistency(candidate, proposal)
        elif dimension == EvaluationDimension.ROBUSTNESS:
            return self._score_robustness(candidate)
        elif dimension == EvaluationDimension.PREDICTABILITY:
            return self._score_predictability(proposal)
        elif dimension == EvaluationDimension.SAFETY:
            return self._score_safety(proposal)
        elif dimension == EvaluationDimension.DIVERSITY:
            return self._score_diversity(proposal)
        else:
            # Unknown dimension — fail loud
            raise ValueError(f"Unknown evaluation dimension: {dimension}")

    def _score_capability(self, proposal: EvolutionProposal) -> DimensionScore:
        """Score capability: inverse of estimated risk.

        Lower risk proposals are more likely to maintain or improve capability.
        Risk 0.0 → score 1.0; Risk 1.0 → score 0.0.
        """
        risk = proposal.estimated_risk
        if isinstance(risk, (int, float)):
            risk_val = float(risk)
        else:
            risk_val = 0.5
        score = 1.0 - risk_val
        return DimensionScore(
            dimension=EvaluationDimension.CAPABILITY,
            score=score,
            detail=f"Inverse of estimated risk ({risk_val:.2f})",
        )

    def _score_consistency(
        self, candidate: DualCopyCandidate, proposal: EvolutionProposal
    ) -> DimensionScore:
        """Score consistency: based on change type.

        Simple YAML value changes (thresholds, parameters) are highly
        consistent. Structural changes (new keys, removed sections) less so.
        """
        # Phase 4 heuristic: YAML value changes are consistent
        diff_lower = proposal.diff.lower()
        if "new_key" in diff_lower or "remove" in diff_lower or "delete" in diff_lower:
            score = 0.5
            detail = "Structural YAML change — moderate consistency"
        else:
            score = 0.8
            detail = "YAML value change — high consistency"
        return DimensionScore(
            dimension=EvaluationDimension.CONSISTENCY,
            score=score,
            detail=detail,
        )

    def _score_robustness(self, candidate: DualCopyCandidate) -> DimensionScore:
        """Score robustness: fewer modified files = more robust.

        1 file: 0.9, 2 files: 0.7, 3 files: 0.5, 4+: 0.3
        """
        n_files = len(candidate.modified_files)
        if n_files <= 1:
            score = 0.9
        elif n_files <= 2:
            score = 0.7
        elif n_files <= 3:
            score = 0.5
        else:
            score = 0.3
        return DimensionScore(
            dimension=EvaluationDimension.ROBUSTNESS,
            score=score,
            detail=f"{n_files} files modified",
        )

    def _score_predictability(self, proposal: EvolutionProposal) -> DimensionScore:
        """Score predictability: smaller diffs are more predictable.

        <= 10 lines: 0.9, <= 50: 0.7, <= 100: 0.5, > 100: 0.3
        """
        diff_lines = len(proposal.diff.strip().split("\n")) if proposal.diff.strip() else 0
        if diff_lines <= 10:
            score = 0.9
        elif diff_lines <= 50:
            score = 0.7
        elif diff_lines <= 100:
            score = 0.5
        else:
            score = 0.3
        return DimensionScore(
            dimension=EvaluationDimension.PREDICTABILITY,
            score=score,
            detail=f"{diff_lines} lines in diff",
        )

    def _score_safety(self, proposal: EvolutionProposal) -> DimensionScore:
        """Score safety: constitutional compliance + ring hierarchy.

        Tier 3 proposals targeting Ring 2-3 content: 0.95 (high safety).
        Any hint of Ring 0-1 targeting: 0.0 (fail).
        """
        component_lower = proposal.component.lower()

        # Ring 0/1 targeting — immediate fail
        if "constitution" in component_lower:
            return DimensionScore(
                dimension=EvaluationDimension.SAFETY,
                score=0.0,
                detail="Targets constitution (Ring 0) — FORBIDDEN",
            )

        # Check for framework-level paths (Ring 1)
        # DR-17: "state/" removed — state/ is the instance data directory
        # (e.g., instances/meta/state/), NOT Ring 1 framework code.
        # Ring 1 = Python source under src/uagents/{engine,models,audit,cli}/.
        ring_1_indicators = ["engine/", "models/", "audit/", "cli/"]
        for indicator in ring_1_indicators:
            if indicator in component_lower:
                return DimensionScore(
                    dimension=EvaluationDimension.SAFETY,
                    score=0.0,
                    detail=f"Targets Ring 1 path ({indicator}) — FORBIDDEN in Phase 4",
                )

        # Tier 3 targeting operational configs — safe
        tier_val = proposal.tier
        tier_int = tier_val if isinstance(tier_val, int) else int(tier_val)
        if tier_int == 3:
            return DimensionScore(
                dimension=EvaluationDimension.SAFETY,
                score=0.95,
                detail="Tier 3 targeting operational config — safe",
            )

        return DimensionScore(
            dimension=EvaluationDimension.SAFETY,
            score=0.5,
            detail="Non-Tier 3 proposal — moderate safety",
        )

    def _score_diversity(self, proposal: EvolutionProposal) -> DimensionScore:
        """Score diversity: does the change affect diversity-relevant configs?

        Changes to role compositions may affect diversity (positive or negative).
        Changes to thresholds/parameters typically don't affect diversity.
        """
        component_lower = proposal.component.lower()

        if "composition" in component_lower or "role" in component_lower:
            # Role changes could affect diversity — neutral score
            score = 0.6
            detail = "Targets role composition — may affect diversity"
        elif "voice" in component_lower or "tone" in component_lower:
            score = 0.6
            detail = "Targets voice/tone config — may affect diversity"
        else:
            # Non-diversity-relevant change
            score = 0.8
            detail = "Non-diversity-relevant change — diversity maintained"

        return DimensionScore(
            dimension=EvaluationDimension.DIVERSITY,
            score=score,
            detail=detail,
        )
```

---

## Part 7: MAP-Elites Archive

### 7.1 Class Definition

```python
"""MAP-Elites quality-diversity archive for evolution.
Spec reference: Section 7.4 (MAP-Elites Configuration Archive).

Maintains a behavioral archive of successful configurations indexed
by (task_type, complexity). Stores the best-performing configuration
per cell. Novelty bonus encourages exploration of underexplored cells.

Key constraints:
- Update rule: replace cell occupant only if new > existing
- Novelty bonus (0.1) added for first-time cell occupation
- Minimum task count before a cell can serve as baseline
- Archive persisted as YAML to state/evolution/archive.yaml

Literature basis:
- MAP-Elites (Mouret & Clune, 2015): quality-diversity via behavioral grid
- ADAS (ICLR 2025): archive of agentic designs indexed by task type
- DGM: population-based evaluation with behavioral diversity
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.evolution import (
    ArchiveCell,
    EvolutionRecord,
    MAPElitesState,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.map_elites_archive")


class MAPElitesArchive:
    """Quality-diversity archive indexed by (task_type, complexity).

    Design invariants:
    - Each cell stores best-performing configuration
    - Replace only if new performance > existing
    - Novelty bonus for first-time cell occupants
    - Archive persisted to YAML after every update
    - Read from disk on init (crash recovery)

    Usage:
        archive = MAPElitesArchive(yaml_store, domain)
        archive.update_from_evolution(record)
        best = archive.get_best_config("research", "complex")
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta"):
        self.yaml_store = yaml_store
        self.domain = domain

        # Load config
        config_raw = yaml_store.read_raw("core/evolution.yaml")
        arc = config_raw["evolution"]["archive"]

        # IFM-N53: Direct dict access
        self._task_types: list[str] = arc["task_types"]
        self._complexities: list[str] = arc["complexities"]
        self._novelty_bonus = float(arc["novelty_bonus"])
        self._min_tasks = int(arc["min_tasks_for_cell"])
        self._archive_path = str(arc["archive_path"])

        # Load or initialize state
        self._state = self._load_state()

    def update_from_evolution(self, record: EvolutionRecord) -> bool:
        """Update archive with a successful evolution.

        Extracts task_type and complexity from the evolution evidence,
        and updates the corresponding cell if performance is better.

        Args:
            record: Completed evolution record (must be PROMOTED).

        Returns:
            True if the archive was updated, False otherwise.
        """
        outcome = record.outcome
        outcome_str = outcome if isinstance(outcome, str) else str(outcome)
        if outcome_str != "promoted":
            return False

        # Extract behavioral coordinates from evidence
        evidence = record.proposal.evidence
        task_type = evidence.get("task_type")
        complexity_raw = evidence.get("complexity")

        # FM-P4-22/DR-14: Reject invalid coordinates — NO fallback to defaults.
        # Silent fallback masks bugs in the proposal pipeline. If coordinates
        # are missing or invalid, the proposer must fix the evidence dict.
        if task_type is None:
            logger.warning(
                f"Evolution {record.id} missing 'task_type' in evidence — "
                f"skipping archive update"
            )
            return False
        if task_type not in self._task_types:
            logger.warning(
                f"Evolution {record.id} has unknown task_type '{task_type}' — "
                f"valid types: {self._task_types}. Skipping archive update."
            )
            return False

        # DR-21: Map orchestrator's complexity vocabulary to archive vocabulary.
        # Orchestrator uses: "small", "medium", "large"
        # Archive uses: "simple", "moderate", "complex", "extreme"
        # This mapping bridges the vocabulary gap between subsystems.
        _complexity_map: dict[str, str] = {
            "small": "simple",
            "medium": "moderate",
            "large": "complex",
            # Direct archive vocabulary also accepted (identity mapping)
            "simple": "simple",
            "moderate": "moderate",
            "complex": "complex",
            "extreme": "extreme",
        }
        if complexity_raw is None:
            logger.warning(
                f"Evolution {record.id} missing 'complexity' in evidence — "
                f"skipping archive update"
            )
            return False
        complexity = _complexity_map.get(str(complexity_raw))
        if complexity is None:
            logger.warning(
                f"Evolution {record.id} has unmappable complexity "
                f"'{complexity_raw}' — valid values: "
                f"{list(_complexity_map.keys())}. Skipping archive update."
            )
            return False

        # Get evaluation score as performance
        performance = 0.0
        if record.evaluation is not None:
            performance = record.evaluation.overall_score

        # Find or create cell
        cell = self._find_cell(task_type, complexity)
        now = datetime.now(timezone.utc)

        if cell is None:
            # New cell — novelty bonus applies
            effective_performance = performance + self._novelty_bonus
            new_cell = ArchiveCell(
                task_type=task_type,
                complexity=complexity,
                best_config=self._extract_config(record),
                performance=effective_performance,
                task_count=1,
                last_updated=now,
                evolution_id=record.id,
            )
            self._state.cells.append(new_cell)
            self._state.total_evaluations += 1
            self._state.total_replacements += 1
            self._save_state()
            logger.info(
                f"New archive cell ({task_type}, {complexity}) "
                f"with performance {effective_performance:.2f} (novelty bonus applied)"
            )
            return True

        # Existing cell — replace only if better
        self._state.total_evaluations += 1
        cell.task_count += 1

        if performance > cell.performance:
            old_perf = cell.performance
            cell.best_config = self._extract_config(record)
            cell.performance = performance
            cell.last_updated = now
            cell.evolution_id = record.id
            self._state.total_replacements += 1
            self._save_state()
            logger.info(
                f"Archive cell ({task_type}, {complexity}) updated: "
                f"{old_perf:.2f} → {performance:.2f}"
            )
            return True

        self._save_state()
        logger.info(
            f"Archive cell ({task_type}, {complexity}) not updated: "
            f"new {performance:.2f} <= existing {cell.performance:.2f}"
        )
        return False

    def get_best_config(
        self, task_type: str, complexity: str
    ) -> dict[str, str] | None:
        """Get the best configuration for a behavioral cell.

        Returns None if the cell doesn't exist or has insufficient tasks.
        """
        cell = self._find_cell(task_type, complexity)
        if cell is None:
            return None
        if cell.task_count < self._min_tasks:
            return None
        return cell.best_config

    def get_all_cells(self) -> list[ArchiveCell]:
        """Return all archive cells."""
        return list(self._state.cells)

    def get_coverage(self) -> float:
        """Return the fraction of cells that are occupied.

        Total possible cells = len(task_types) * len(complexities).
        """
        total_possible = len(self._task_types) * len(self._complexities)
        if total_possible == 0:
            return 0.0
        occupied = len(self._state.cells)
        return occupied / total_possible

    def get_stats(self) -> dict:
        """Return archive statistics."""
        return {
            "total_cells": len(self._state.cells),
            "total_possible": len(self._task_types) * len(self._complexities),
            "coverage": self.get_coverage(),
            "total_evaluations": self._state.total_evaluations,
            "total_replacements": self._state.total_replacements,
        }

    # ── Private helpers ──

    def _find_cell(
        self, task_type: str, complexity: str
    ) -> ArchiveCell | None:
        """Find a cell by its behavioral coordinates."""
        for cell in self._state.cells:
            if cell.task_type == task_type and cell.complexity == complexity:
                return cell
        return None

    def _extract_config(self, record: EvolutionRecord) -> dict[str, str]:
        """Extract configuration dict from an evolution record."""
        return {
            "component": record.proposal.component,
            "diff_summary": record.proposal.diff[:200],
            "rationale": record.proposal.rationale,
            "evolution_id": record.id,
        }

    def _load_state(self) -> MAPElitesState:
        """Load archive state from disk. Create empty if missing."""
        try:
            return self.yaml_store.read(self._archive_path, MAPElitesState)
        except FileNotFoundError:
            logger.info("No archive found — creating empty MAP-Elites state")
            return MAPElitesState()

    def _save_state(self) -> None:
        """Persist archive state to disk."""
        self.yaml_store.write(self._archive_path, self._state)
```

---

## Part 8: Modifications to Existing Files

### 8.1 `models/evolution.py` — Full Replacement

Replace the entire file with the models defined in Part 2. The new file adds:
- `EvolutionLifecycleState` (StrEnum, 10 states)
- `ObservationTrigger` (StrEnum, 7 triggers)
- `EvaluationDimension` (StrEnum, 6 dimensions)
- `EvolutionOutcome` (StrEnum, 4 outcomes)
- `DimensionScore` (FrameworkModel)
- `EvaluationResult` (IdentifiableModel)
- `ArchiveCell` (FrameworkModel)
- `MAPElitesState` (FrameworkModel)

Modified existing models:
- `EvolutionProposal` — adds `trigger`, `trigger_detail`, `lifecycle_state` fields
- `EvolutionRecord` — adds `evaluation`, `evolution_commit`, `outcome`, `verification_passed` fields
- `DualCopyCandidate` — changes `fork_path` from `Path` to `str` for YAML serialization, adds `source_files`, `rolled_back` fields

### 8.2 `models/audit.py` — Backward-Compatible EvolutionLogEntry

**CRITICAL (DR-02/FM-P4-16):** EvolutionLogEntry MUST keep the original fields
with defaults added. `SkillLibrary._log_ring_transition()` constructs entries with
`approved_by`, `constitutional_check`, `rollback_commit` — removing these breaks
existing callers.

Add defaults to old fields + add 4 new Phase 4 fields with defaults:
```python
class EvolutionLogEntry(BaseLogEntry):
    stream: Literal[LogStream.EVOLUTION] = LogStream.EVOLUTION
    tier: EvolutionTier
    component: str
    diff: str
    rationale: str
    evidence: dict
    # Original fields — KEEP with defaults for backward compatibility
    # (used by SkillLibrary._log_ring_transition and other Phase 3.5 callers)
    approved_by: str = ""             # Who approved (human, quorum, auto)
    constitutional_check: bool = True  # Did it pass constitution check?
    rollback_commit: str = ""         # Git commit SHA for rollback (empty if rejected/held)
    # Phase 4 additions (all have defaults — backward compatible):
    lifecycle_state: str = ""  # EvolutionLifecycleState value
    outcome: str = ""          # EvolutionOutcome value
    evaluation_score: float = 0.0  # Overall evaluation score
    trigger: str = ""          # ObservationTrigger value
```

### 8.3 `engine/orchestrator.py` — Evolution Trigger Integration

Add optional `evolution_engine` parameter to Orchestrator constructor and evolution triggering in `handle_verdict()`:

```python
# In __init__:
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .evolution_engine import EvolutionEngine

class Orchestrator:
    def __init__(
        self,
        # ... existing params ...
        evolution_engine: EvolutionEngine | None = None,
    ):
        # ... existing init ...
        self._evolution_engine = evolution_engine

    def handle_verdict(self, task_id: str, actor: str = "orchestrator") -> Task:
        # ... existing logic that transitions task to COMPLETE ...

        # FM-P4-46: Notify evolution engine on ALL verdicts (pass, fail, partial).
        # Evolution cooldown counts total completed tasks, not just successful ones.
        # This prevents starvation where failing tasks never advance the counter.
        if self._evolution_engine is not None:
            self._evolution_engine.record_task_completion()
        return task

    def trigger_evolution_if_ready(
        self,
        trigger: str,
        trigger_detail: str,
        component: str,
        diff: str,
        rationale: str,
    ) -> EvolutionRecord | None:
        """Check if evolution cooldown has elapsed and run if ready.

        Called by the autonomous run loop (Phase 5) or manually.
        Returns EvolutionRecord if evolution was run, None if cooldown active.

        DR-10: Validates trigger is a valid ObservationTrigger value before
        constructing the proposal. Invalid triggers raise ValueError.
        """
        if self._evolution_engine is None:
            return None
        if not self._evolution_engine.can_evolve():
            return None

        from ..models.evolution import ObservationTrigger
        # DR-10: Validate trigger value — fail loud on invalid trigger
        try:
            trigger_enum = ObservationTrigger(trigger)
        except ValueError:
            raise ValueError(
                f"Invalid evolution trigger '{trigger}'. "
                f"Valid triggers: {[t.value for t in ObservationTrigger]}"
            )

        proposal = self._evolution_engine.create_proposal(
            component=component,
            diff=diff,
            rationale=rationale,
            trigger=trigger_enum,
            trigger_detail=trigger_detail,
        )
        return self._evolution_engine.run_evolution(proposal)
```

### 8.4 `engine/skill_library.py` — No Changes Required

SkillLibrary's `_log_ring_transition()` constructs `EvolutionLogEntry` with
`approved_by`, `constitutional_check`, `rollback_commit`. These fields are
preserved with defaults in the updated audit model (Section 8.2). No code
changes needed in skill_library.py.

### 8.5 `engine/constitution_guard.py` — No Changes Required

**DR-16 (removed):** The evolution cycle counter was originally placed in
ConstitutionGuard, but this duplicates the EvolutionEngineState.evolution_count
field that the EvolutionEngine already maintains persistently (Part 4). The
EvolutionEngine checks `evolution_count % objective_anchoring_frequency` directly
from its own state. Adding a separate counter to ConstitutionGuard would create
two sources of truth that could drift. No changes to constitution_guard.py.

---

## Part 9: Implementation Sequence

### 9.1 Step-by-Step Order

1. **YAML config** — Create `instances/meta/core/evolution.yaml` with all thresholds
2. **Data models** — Update `models/evolution.py` with all new models (full replacement)
3. **Audit models** — Update `models/audit.py` with backward-compatible EvolutionLogEntry
4. **MAPElitesArchive** — Implement (no dependencies on other new engines)
5. **EvolutionValidator** — Implement (depends on models only)
6. **DualCopyManager** — Implement (depends on models + yaml_store)
7. **EvolutionEngine** — Implement (depends on all above + ConstitutionGuard + GitOps + RingEnforcer)
8. **Orchestrator integration** — Add evolution_engine parameter and trigger methods

**Note (DR-16):** ConstitutionGuard integration step removed — the evolution
cycle counter lives in EvolutionEngineState (persistent), not ConstitutionGuard.

### 9.2 Dependency Graph

```
evolution.yaml ──┐
                  │
models/evolution.py ──┬──────────────────────────────────┐
                      │                                   │
models/audit.py ──┐   │                                   │
                  │   │                                   │
                  ▼   ▼                                   ▼
           MAPElitesArchive    EvolutionValidator    DualCopyManager
                  │                    │                   │
                  └────────┬───────────┘───────────────────┘
                           │
                           ▼
                    EvolutionEngine
                    (uses ConstitutionGuard, GitOps,
                     RingEnforcer, AuditLogger)
                           │
                           ▼
                    Orchestrator
                    (integration)
```

---

## Part 10: Failure Modes

Total: 48 failure modes (15 original + 33 from review).

### 10.1 Critical Failure Modes (HARD_FAIL)

**FM-P4-01: Constitution hash invalid after evolution commit**
- Trigger: Post-commit verification finds hash mismatch
- Impact: Framework integrity compromised
- Mitigation: Automatic rollback via GitOps.rollback_to()
- Recovery: Human must verify and rehash

**FM-P4-02: Fork promotion corrupts active config**
- Trigger: File copy fails mid-promotion (disk full, permission)
- Impact: Active config in inconsistent state
- Mitigation: FM-P4-18 fix: atomic writes via YamlStore (tmp + os.replace). Git rollback to pre-promotion commit SHA as secondary safeguard.
- Recovery: Human checks file integrity

**FM-P4-03: Objective alignment drops below threshold**
- Trigger: alignment_score < min_alignment_score after N cycles
- Impact: System may be drifting from intended objectives
- Mitigation: Raise ObjectiveAlignmentError, set persistent paused=True flag (FM-P4-48), pause all evolution
- Recovery: Human reviews recent evolutions, calls unpause()

**FM-P4-16: EvolutionLogEntry backward-incompatible schema change** *(CRITICAL — from review)*
- Trigger: Removing `approved_by`, `constitutional_check`, `rollback_commit` breaks SkillLibrary callers
- Impact: Runtime AttributeError in existing Phase 3.5 code
- Mitigation: Keep old fields with defaults added; new Phase 4 fields also have defaults
- Recovery: N/A — prevented by design

**FM-P4-18: shutil.copy2 is not atomic during promotion** *(CRITICAL — from review)*
- Trigger: Crash or power loss during shutil.copy2 in promote()
- Impact: Active config file partially written — corrupted state
- Mitigation: promote() uses YamlStore.write_raw() which does tmp + os.replace (atomic)
- Recovery: Git rollback if atomic write mechanism somehow fails

**FM-P4-19: Git paths instance-relative, not repo-relative** *(CRITICAL — from review)*
- Trigger: GitOps.commit_evolution(files=[...]) expects repo-relative paths
- Impact: Git commit records wrong file paths, rollback targets wrong files
- Mitigation: EvolutionEngine prepends `instances/{domain}/` prefix to all file paths before calling GitOps
- Recovery: N/A — prevented by design

**FM-P4-26: ConstitutionGuard only checks component string** *(CRITICAL — from review)*
- Trigger: Proposal with diff targeting constitution content but component set to a config file
- Impact: Constitution modification bypasses guard check
- Mitigation: EvolutionEngine also checks diff content with path-aware forbidden pattern matching (FM-P4-30), plus RingEnforcer post-promotion verification
- Recovery: Ring violation detected post-commit → automatic rollback

### 10.2 High-Priority Failure Modes

**FM-P4-04: Git operations fail during evolution commit**
- Trigger: GitOps.commit_evolution() raises GitOpsError
- Impact: Evolution committed in YAML but not in Git
- Mitigation: EvolutionEngine catches GitOpsError in COMMIT step, marks as REJECTED, triggers rollback
- Recovery: Manual Git cleanup if partial commit exists

**FM-P4-05: Fork directory already exists (stale fork)**
- Trigger: Previous fork not cleaned up (crash during evaluation)
- Impact: create_fork() raises ForkError
- Mitigation: Check for stale forks on EvolutionEngine init, log warning
- Recovery: Manual cleanup of candidates/ directory

**FM-P4-06: Diff application fails (malformed diff spec)**
- Trigger: Invalid YAML in proposal.diff, missing keys
- Impact: apply_diff() raises ForkError
- Mitigation: Cleanup fork, reject proposal with clear error message. Pre-validation via yaml.safe_load(proposal.diff) before fork creation (FM-P4-34).
- Recovery: Fix diff format and re-submit proposal

**FM-P4-07: All evaluation dimensions below minimum**
- Trigger: Proposal is too risky or targets wrong scope
- Impact: Evolution rejected but resources consumed for fork + eval
- Mitigation: Pre-validate proposal scope before fork creation
- Recovery: Log rejection reason for proposing agent to learn from

**FM-P4-08: Evaluation dimension weights don't sum to 1.0**
- Trigger: Misconfigured evolution.yaml weights section
- Impact: Overall score calculation produces unexpected values
- Mitigation: Validator computes weighted average with actual total_weight (normalization). FM-P4-45: weights validated non-negative at init.
- Recovery: Fix config — weights are normalized at calculation time

**FM-P4-17: rollback_commit="" semantically invalid** *(HIGH — from review)*
- Trigger: EvolutionRecord created for rejected proposal has rollback_commit=""
- Impact: Misleading empty string suggests missing data
- Mitigation: Document that empty string is intentional for rejected/held records (no Git commit created). Field has default="".
- Recovery: N/A — documented behavior

**FM-P4-20: GitOpsError not caught during COMMIT step** *(HIGH — from review)*
- Trigger: promote() succeeds but commit_evolution() fails
- Impact: Active config changed but not committed — inconsistent state
- Mitigation: COMMIT step wrapped in try/except (GitOpsError, PromotionError) with rollback on failure
- Recovery: GitOps.rollback_to() reverts to pre-promotion state

**FM-P4-21: _check_objective_alignment reads directory as file** *(HIGH — from review)*
- Trigger: yaml_store.read_raw() called on records directory path
- Impact: Alignment check silently returns 1.0 (always passes)
- Mitigation: Fixed to scan directory for YAML files and analyze outcomes from evolution records
- Recovery: N/A — prevented by design

**FM-P4-23: Evolution count/cooldown lost on restart** *(HIGH — from review)*
- Trigger: Process restart clears in-memory evolution_count and tasks_since_last
- Impact: Cooldown resets, potentially triggering premature evolution
- Mitigation: EvolutionEngineState persisted to YAML via _save_state()/_load_state()
- Recovery: N/A — state survives restart

**FM-P4-29: RingEnforcer not integrated** *(HIGH — from review)*
- Trigger: Evolution promotes files that modify Ring 0 content
- Impact: Ring hierarchy violation undetected
- Mitigation: RingEnforcer added as required constructor parameter; verify_no_ring_0_modification() called after promotion
- Recovery: Ring violation → automatic rollback + REJECTED outcome

**FM-P4-30: Path matching uses simple substring (false positives)** *(HIGH — from review)*
- Trigger: Substring "constitution" matches "team-constitution-notes.yaml"
- Impact: Legitimate proposals rejected as Ring 0 violations
- Mitigation: Use Path.is_relative_to() and filename comparison for Ring 0 paths; fnmatch for exclude patterns (FM-P4-31)
- Recovery: N/A — prevented by design

**FM-P4-38: Old value not verified before diff application** *(HIGH — from review)*
- Trigger: File modified between proposal creation and diff application
- Impact: Diff overwrites unexpected values — silent corruption
- Mitigation: apply_diff() verifies each "old" value matches current value before overwriting
- Recovery: ForkError raised if mismatch detected; fork cleaned up

**FM-P4-48: No persistent pause after ObjectiveAlignmentError** *(HIGH — from review)*
- Trigger: Objective alignment fails, error raised but process restarts
- Impact: Evolution resumes on restart without human review
- Mitigation: paused=True flag in EvolutionEngineState; persisted to YAML; run_evolution() checks flag on entry
- Recovery: Human calls unpause() after reviewing recent evolutions

### 10.3 Medium-Priority Failure Modes

**FM-P4-09: MAP-Elites archive.yaml corrupted**
- Trigger: Crash during archive write
- Impact: Archive state lost
- Mitigation: YamlStore atomic writes (tmp + rename pattern)
- Recovery: Archive re-initialized from empty; populated by future evolutions

**FM-P4-10: Evolution cooldown never triggers**
- Trigger: No tasks completing (all blocked or parked)
- Impact: Evolution never runs
- Mitigation: Manual trigger via create_proposal() bypasses cooldown
- Recovery: Investigate why tasks are not completing

**FM-P4-11: Tier 0-2 proposal reaches run_evolution()**
- Trigger: Caller constructs proposal with wrong tier
- Impact: Proposal rejected at tier check (not harmful)
- Mitigation: run_evolution() validates tier at step 3
- Recovery: Caller gets EvolutionRecord with REJECTED outcome

**FM-P4-12: use_enum_values causes type mismatch in comparisons**
- Trigger: FrameworkModel's use_enum_values=True stores enum as int/str
- Impact: Direct enum comparison fails (e.g., tier == EvolutionTier.OPERATIONAL)
- Mitigation: Always use int()/str() for consistent conversion (no isinstance boilerplate)
- Recovery: Pattern: `int(proposal.tier)` and `str(record.outcome)`

**FM-P4-13: Audit logging failure during evolution lifecycle**
- Trigger: JsonlWriter fails (disk full, permission)
- Impact: Evolution audit trail incomplete
- Mitigation: Wrapped in try/except (OSError, ValueError, TypeError), logged to Python logger (DR-06: narrowed exception types)
- Recovery: Non-fatal for Phase 4; audit gaps noted in logs

**FM-P4-14: Concurrent evolution attempts**
- Trigger: Two evolution cycles start simultaneously
- Impact: Fork directory conflicts, Git merge conflicts
- Mitigation: max_concurrent_candidates=1 in config; create_fork() checks for existing dir (FM-P4-43)
- Recovery: Second attempt gets ForkError, retries after first completes

**FM-P4-15: DualCopyManager exclude pattern too broad**
- Trigger: Exclude pattern matches files that should be forked
- Impact: Fork is missing needed files, diff application fails
- Mitigation: Target file explicitly copied if not in fork_includes. FM-P4-31: fnmatch used instead of substring.
- Recovery: Adjust fork_excludes patterns in evolution.yaml

**FM-P4-22: Invalid archive coordinates fallback to defaults** *(MEDIUM — from review)*
- Trigger: Evidence dict has unknown task_type or complexity
- Impact: Unrelated data silently mapped to "meta"/"moderate" cell — corrupts archive
- Mitigation: Reject invalid coordinates; return False from update_from_evolution(). DR-21: complexity vocabulary mapping for known variants.
- Recovery: N/A — prevented by design

**FM-P4-24: Fork file creation not atomic** *(MEDIUM — from review)*
- Trigger: Crash during shutil.copy2 in create_fork()
- Impact: Fork has partially written files
- Mitigation: _atomic_copy() writes to .tmp then os.replace()
- Recovery: Stale fork detected and cleaned up on next EvolutionEngine init

**FM-P4-25: DualCopyCandidate.fork_path type confusion** *(MEDIUM — from review)*
- Trigger: fork_path is str (for YAML serialization) but used as Path in operations
- Impact: Potential str/Path type errors
- Mitigation: Document that fork_path is always str; wrap in Path() at use sites
- Recovery: N/A — documented behavior

**FM-P4-27: max_file_modifications loaded but never checked** *(MEDIUM — from review)*
- Trigger: Evolution modifies more files than configured maximum
- Impact: Overly broad changes slip through
- Mitigation: len(candidate.modified_files) checked after apply_diff(); ForkError if exceeded
- Recovery: Fork cleaned up, proposal rejected

**FM-P4-31: Exclude matching uses substring (false positives)** *(MEDIUM — from review)*
- Trigger: "state/" in path matches "estate/" or "persistence-state-backup.yaml"
- Impact: Legitimate files excluded from fork
- Mitigation: Use fnmatch.fnmatch() for glob-style pattern matching
- Recovery: N/A — prevented by design

**FM-P4-34: No diff format validation before fork creation** *(MEDIUM — from review)*
- Trigger: Malformed diff YAML discovered only after fork is created
- Impact: Wasted resources on fork creation for invalid proposal
- Mitigation: yaml.safe_load(proposal.diff) validated before create_fork()
- Recovery: N/A — prevented by design

**FM-P4-41: ArchiveCell.performance le=1.0 rejects novelty bonus** *(MEDIUM — from review)*
- Trigger: performance + novelty_bonus > 1.0 causes Pydantic validation error
- Impact: First-time archive updates always fail
- Mitigation: Removed le=1.0 constraint from ArchiveCell.performance
- Recovery: N/A — prevented by design

**FM-P4-42: Manifest not persisted after apply_diff()** *(MEDIUM — from review)*
- Trigger: Crash between apply_diff and manifest update
- Impact: Manifest doesn't reflect modified_files
- Mitigation: EvolutionEngine calls _persist_manifest() after apply_diff() returns
- Recovery: Manifest can be reconstructed from fork directory contents

**FM-P4-43: max_concurrent_candidates not checked** *(MEDIUM — from review)*
- Trigger: Multiple evolution cycles create forks simultaneously
- Impact: Resource contention, Git merge conflicts
- Mitigation: Count entries in candidates_dir before fork creation; reject if at limit
- Recovery: Second attempt rejected cleanly with ForkError

**FM-P4-44: Disk space not checked before fork creation** *(MEDIUM — from review)*
- Trigger: Disk nearly full when fork is attempted
- Impact: Partial fork creation, corrupted state
- Mitigation: shutil.disk_usage() check requires 50MB free before fork creation
- Recovery: ForkError raised with clear disk space message

**FM-P4-45: Negative evaluation weights** *(MEDIUM — from review)*
- Trigger: Misconfigured evolution.yaml has negative weight
- Impact: Dimension with negative weight inverts scoring — unsafe behavior rewarded
- Mitigation: __init__ validates all weights >= 0.0; raises ValueError if negative
- Recovery: N/A — prevented by design (fail at startup)

**FM-P4-46: Cooldown only advances on successful tasks** *(MEDIUM — from review)*
- Trigger: Tasks fail but evolution cooldown never advances
- Impact: Evolution never triggers in failure-heavy workloads
- Mitigation: record_task_completion() called on ALL verdicts (pass/fail/partial) in handle_verdict()
- Recovery: N/A — prevented by design

**FM-P4-47: EvolutionProposal.evidence type narrowed** *(MEDIUM — from review)*
- Trigger: evidence field changed from dict to dict[str, str]
- Impact: Existing callers with non-string values fail validation
- Mitigation: Keep evidence as untyped dict (no str constraint)
- Recovery: N/A — prevented by design

### 10.4 Low-Priority Failure Modes (from review)

**FM-P4-28: Filesystem ops not wrapped in try/except** *(LOW — from review)*
- Trigger: Permission errors on fork directory creation
- Impact: Unhandled OSError crashes evolution lifecycle
- Mitigation: DualCopyManager wraps mkdir/copy in try/except, converts to ForkError
- Recovery: Fork cleaned up, proposal rejected

**FM-P4-32: No timeout on diff application** *(LOW — from review)*
- Trigger: Extremely large YAML diff takes excessive time
- Impact: Evolution lifecycle blocks indefinitely
- Mitigation: Phase 4 diffs are small YAML value changes; risk is minimal. Phase 5 may add timeout.
- Recovery: Process can be killed; fork cleaned up on restart

**FM-P4-33: Archive disk usage grows unbounded** *(LOW — from review)*
- Trigger: Many cells accumulated over long operation
- Impact: archive.yaml grows large, slowing reads
- Mitigation: Total cells bounded by |task_types| × |complexities| (currently 7×4=28 max)
- Recovery: N/A — bounded by grid dimensions

**FM-P4-35: Race between two agents creating proposals** *(LOW — from review)*
- Trigger: Two agents call create_proposal() simultaneously
- Impact: Two proposals created for same component
- Mitigation: max_concurrent_candidates=1; second fork creation fails
- Recovery: Second agent's proposal rejected at fork creation

**FM-P4-36: YAML safe_load does not validate schema** *(LOW — from review)*
- Trigger: Diff YAML is syntactically valid but semantically wrong
- Impact: Nonsensical changes applied to config
- Mitigation: Key-path traversal raises KeyError for missing paths; old-value verification catches value mismatches
- Recovery: Fork evaluated; bad config scores poorly → rejected

**FM-P4-37: Cleanup not called on all error paths** *(LOW — from review)*
- Trigger: Exception between fork creation and cleanup
- Impact: Orphaned fork directories
- Mitigation: EvolutionEngine wraps entire lifecycle in try/finally with cleanup. Stale fork detection on init.
- Recovery: Manual cleanup or automatic on next init

**FM-P4-39: No evolution.yaml schema version** *(LOW — from review)*
- Trigger: Config format changes between phases
- Impact: Older config silently misinterpreted
- Mitigation: Phase 4 uses IFM-N53 direct access — missing keys raise KeyError immediately
- Recovery: Update config to match expected schema

**FM-P4-40: No smoke test after promotion** *(LOW — from review)*
- Trigger: Promoted config is syntactically valid but semantically wrong
- Impact: Bad config used for subsequent tasks
- Mitigation: Phase 4 VERIFY step checks constitution hash. Phase 5 will add task-based smoke testing.
- Recovery: Poor task performance triggers rollback in next evolution cycle

---

## Verification Checklist

1. `uv run pytest tests/test_engine/test_evolution_phase4.py -v` — all tests pass
2. `uv run pytest --tb=long -v` — zero regressions in existing tests
3. Evolution lifecycle: OBSERVE → ... → PROMOTED with audit trail
4. Constitutional rejection: Tier 0/1 proposals rejected with clear reason
5. Safety rejection: Forbidden paths, Ring 1 indicators, oversized diffs rejected
6. Dual-copy isolation: fork created, modified, promoted, cleaned up
7. Git integration: rollback point created, evolution committed, rollback works
8. MAP-Elites: archive updated on successful evolution, novelty bonus applied
9. Evaluation dimensions: all 6 scored, per-dimension minimums enforced
10. Cooldown: evolution blocked until N tasks complete
11. Objective anchoring: check triggered every N cycles, persistent pause on failure
12. Orchestrator integration: record_task_completion called on ALL verdicts
13. use_enum_values: all enum conversions use int()/str() pattern
14. Backward compatibility: EvolutionLogEntry works with SkillLibrary callers
15. Atomic operations: fork creation, diff application, and promotion all use tmp + os.replace
16. Old-value verification: apply_diff() checks "old" values before overwriting
17. Invalid archive coordinates rejected (no fallback to defaults)
18. Persistent state: evolution_count, paused flag survive restart
19. RingEnforcer: verify_no_ring_0_modification() called after every promotion
20. Negative weights rejected at EvolutionValidator init
14. Audit logging: EvolutionLogEntry includes lifecycle_state, outcome, trigger
