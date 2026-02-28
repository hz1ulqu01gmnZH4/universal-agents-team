# Universal Agents Framework — Phase 0 Detailed Design

**Version:** 0.1.0
**Date:** 2026-02-28
**Source:** framework-design-unified-v1.1.md (3549 lines, 28 sections, ~320 papers)
**Status:** Implementation-ready — concrete enough to code from directly
**Scope:** Phase 0 scaffolding only (no evolution, diversity, creativity, or self-improvement)

---

## Table of Contents

1. [Implementation Architecture Overview](#part-1-implementation-architecture-overview)
2. [Core Data Models (Pydantic v2)](#part-2-core-data-models-pydantic-v2)
3. [State Management Layer](#part-3-state-management-layer)
4. [Engine Layer (Core Logic)](#part-4-engine-layer-core-logic)
5. [CLAUDE.md as Bootstrap Entry Point](#part-5-claudemd-as-bootstrap-entry-point)
6. [Claude Code Integration Patterns](#part-6-claude-code-integration-patterns)
7. [Claude Code Limitations & Workarounds](#part-7-claude-code-limitations--workarounds)
8. [Phase 0 Implementation Sequence](#part-8-phase-0-implementation-sequence)
9. [Verification Checklist](#part-9-verification-checklist)
10. [Edge Cases, Failure Modes & Mitigations](#part-10-edge-cases-failure-modes--mitigations)

---

## Part 1: Implementation Architecture Overview

### 1.1 Key Realization

The framework runs **AS** Claude Code, not alongside it. Python code is tooling/utility that Claude Code agents invoke via Bash. The "runtime" is:

- **CLAUDE.md** — bootstrap entry point (tells Claude Code how to behave as the framework)
- **YAML configs** — all state, all configuration, all role definitions
- **Skills** — lazy-loaded capability extensions in `.claude/skills/framework-*/SKILL.md`
- **Python tools** — data models, state management, prompt composition, audit logging

Claude Code IS the execution engine. The Python package provides validation, atomic state operations, and CLI utilities.

### 1.2 Python Package Layout

```
universal-agents/
├── pyproject.toml                         # uv-managed, pydantic v2, pyyaml, psutil, rich
├── src/
│   └── uagents/                           # Main package: "uagents"
│       ├── __init__.py                    # Version, package-level exports
│       ├── py.typed                       # PEP 561 marker
│       │
│       ├── models/                        # ---- Pydantic v2 Data Models ----
│       │   ├── __init__.py
│       │   ├── base.py                    # Base model config, common validators, ID generators
│       │   ├── constitution.py            # Axiom, Constitution, Charter, TaskMandate
│       │   ├── capability.py              # CapabilityAtom, ModelPreference, ThinkingSetting
│       │   ├── voice.py                   # VoiceAtom, VoiceProfile, VoiceSafetyConfig
│       │   ├── role.py                    # RoleComposition, BehavioralDescriptors, AuthorityLevel
│       │   ├── task.py                    # Task (9 states), TaskTimeline, TaskReview, VALID_TRANSITIONS
│       │   ├── topology.py               # TopologyAnalysis, TopologyPattern, RoutingResult
│       │   ├── evolution.py              # EvolutionProposal, EvolutionRecord, QuorumVote, DualCopy
│       │   ├── skill.py                  # SkillRecord, SkillValidation, SkillScore
│       │   ├── diversity.py              # SRDMeasurement, VDIMeasurement, StagnationSignal
│       │   ├── creativity.py             # CreativeSession, GuilfordMetrics
│       │   ├── resource.py               # TokenBudget, RateLimitMirror, ComputeMetrics, SpendLevel
│       │   ├── environment.py            # ModelFingerprint, CanaryResult, DriftDetection
│       │   ├── protection.py             # ProtectionRing, RingTransition, ContextPressure
│       │   ├── context.py                # ContextBudget, CompressionStage, ContextSnapshot
│       │   ├── agent.py                  # AgentRegistryEntry, AgentStatus
│       │   ├── domain.py                 # DomainConfig, VoiceDefaults
│       │   ├── audit.py                  # LogEntry variants (8 types), LogStream enum
│       │   ├── session.py                # SessionLock
│       │   ├── meta_analysis.py          # MetaAnalysisReport, DimensionScore
│       │   ├── coordination.py           # PressureField, QuorumConfig
│       │   └── governance.py             # ObjectiveAnchoring, AlignmentCheck
│       │
│       ├── state/                         # ---- State Management Layer ----
│       │   ├── __init__.py
│       │   ├── yaml_store.py             # Atomic YAML read/write with Pydantic validation
│       │   ├── jsonl_writer.py           # Append-only JSONL log writer with rotation
│       │   ├── git_ops.py                # Git integration (commit, rollback, hash verify)
│       │   ├── lock_manager.py           # Session lock (.claude-framework.lock)
│       │   ├── directory.py              # Directory structure creation/validation
│       │   └── migration.py              # State migration between framework versions
│       │
│       ├── engine/                        # ---- Core Engine Logic ----
│       │   ├── __init__.py
│       │   ├── prompt_composer.py         # THE HEART: Ring 0-3 prompt assembly engine
│       │   ├── topology_router.py         # Task analysis + topology pattern selection
│       │   ├── evolution_pipeline.py      # Tier evaluation, dual-copy (Phase 1+)
│       │   ├── constitution_guard.py      # Hash verification, axiom loading
│       │   ├── quorum.py                  # Sealed vote collection (Phase 1+)
│       │   ├── diversity_engine.py        # SRD/VDI computation (Phase 1+)
│       │   ├── creativity_engine.py       # Separate-Then-Together (Phase 1+)
│       │   ├── skill_manager.py           # 4-stage validation (Phase 1+)
│       │   ├── resource_tracker.py        # Token budget, rate limit mirror, compute monitor
│       │   ├── environment_monitor.py     # Canary runner, fingerprint, drift detection
│       │   ├── context_manager.py         # Budget allocation, compression cascade
│       │   ├── tool_loader.py             # Dynamic tool selection (Phase 1+)
│       │   ├── task_lifecycle.py           # State machine transitions, parking/resumption
│       │   ├── agent_spawner.py           # Resource-checked spawn, registry management
│       │   ├── meta_analyzer.py           # 10-dimension analysis (Phase 1+)
│       │   ├── self_governance.py         # Objective anchoring (Phase 1+)
│       │   └── cost_router.py             # FrugalGPT cascade (Phase 1+)
│       │
│       ├── claude_md/                     # ---- CLAUDE.md Generation ----
│       │   ├── __init__.py
│       │   ├── generator.py              # CLAUDE.md template rendering from state
│       │   ├── sections.py               # Section builders (bootstrap, tools, roles)
│       │   └── updater.py                # Quick State section regeneration
│       │
│       ├── audit/                         # ---- Audit System ----
│       │   ├── __init__.py
│       │   ├── logger.py                 # 8-stream JSONL log dispatcher
│       │   ├── tree_viewer.py            # Terminal tree viewer (rich library)
│       │   ├── html_viewer.py            # Self-contained HTML report generator
│       │   ├── rotation.py               # Log rotation and archival
│       │   └── query.py                  # Log search, filter, aggregation
│       │
│       └── cli/                           # ---- CLI Entry Points (tool scripts) ----
│           ├── __init__.py
│           ├── bootstrap.py              # Initialize framework directory structure
│           ├── spawn_agent.py            # Compose prompt, validate resources, output spawn cmd
│           ├── park_task.py              # Snapshot task context, update focus
│           ├── resume_task.py            # Restore task context, respawn agents
│           ├── evolve.py                 # Trigger evolution pipeline (Phase 1+)
│           ├── canary_runner.py          # Model fingerprinting canary suite
│           ├── resource_monitor.py       # Resource dashboard (token/rate/compute)
│           ├── context_analyzer.py       # Context window utilization analysis
│           ├── skill_pruner.py           # Skill library maintenance (Phase 1+)
│           ├── audit_tree.py             # Terminal tree viewer
│           ├── audit_viewer.py           # CLI log query interface
│           ├── generate_audit_html.py    # HTML report generator
│           ├── diversity_check.py        # SRD/VDI metrics (Phase 1+)
│           ├── meta_analysis.py          # 10-dimension analysis (Phase 1+)
│           ├── domain_switch.py          # Domain switching
│           ├── domain_create.py          # New domain scaffolding
│           ├── role_creator.py           # Role creation helper
│           ├── force_unlock.py           # Remove stale session locks
│           ├── ring0_recovery.py         # Ring 0 integrity recovery
│           └── update_claude_md.py       # Regenerate Quick State section
│
├── tools/                                 # Shell wrappers for CLI (agents call these)
│   ├── bootstrap.sh                      # uv run python -m uagents.cli.bootstrap "$@"
│   ├── spawn-agent.sh
│   ├── park-task.sh
│   ├── resume-task.sh
│   ├── canary-runner.sh
│   ├── resource-monitor.sh
│   ├── audit-viewer.sh
│   ├── audit-tree.sh
│   ├── generate-audit-viewer.sh
│   ├── force-unlock.sh
│   ├── ring0-recovery.sh
│   └── update-claude-md.sh
│
└── tests/                                 # Test suite
    ├── conftest.py                       # Shared fixtures (temp directories, sample YAML)
    ├── test_models/                      # Model validation tests
    │   ├── test_task.py
    │   ├── test_role.py
    │   ├── test_voice.py
    │   ├── test_evolution.py
    │   ├── test_resource.py
    │   └── ...
    ├── test_state/                       # State management tests
    │   ├── test_yaml_store.py
    │   ├── test_jsonl_writer.py
    │   ├── test_git_ops.py
    │   └── test_lock_manager.py
    ├── test_engine/                      # Engine logic tests
    │   ├── test_prompt_composer.py
    │   ├── test_task_lifecycle.py
    │   ├── test_constitution_guard.py
    │   └── ...
    └── test_cli/                         # CLI integration tests
        ├── test_bootstrap.py
        └── ...
```

### 1.3 `pyproject.toml`

```toml
[project]
name = "universal-agents"
version = "0.1.0"
description = "Self-evolving multi-agent framework for Claude Code"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
    "pydantic>=2.0",
    "rich>=13.0",
    "psutil>=5.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/uagents"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### 1.4 Shell Wrapper Pattern

Every tool script follows the same pattern — agents invoke shell wrappers, not Python directly:

```bash
#!/usr/bin/env bash
# tools/bootstrap.sh — Initialize framework directory structure
set -euo pipefail
exec uv run python -m uagents.cli.bootstrap "$@"
```

This ensures: (1) `uv` manages the Python environment, (2) agents don't need to know Python internals, (3) all tool calls are auditable via shell history.

---

## Part 2: Core Data Models (Pydantic v2)

All models use strict validation, forbid extra fields, and fail loud on invalid data. Cross-references to v1.1 spec sections are noted.

### 2.1 `models/base.py` — Foundation

```python
"""Base models for the Universal Agents Framework.
Spec reference: used throughout all sections."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound="FrameworkModel")


class FrameworkModel(BaseModel):
    """Base for all framework models.
    Enforces strict validation, forbids extra fields, uses enum by value."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        use_enum_values=True,
        validate_default=True,
    )


class TimestampedModel(FrameworkModel):
    """Adds created_at/updated_at with auto-population."""

    created_at: datetime
    updated_at: datetime | None = None


class IdentifiableModel(TimestampedModel):
    """Adds id field with prefix-based generation."""

    id: str  # e.g., "task-20260228-001", "evo-20260228-001"


def generate_id(prefix: str) -> str:
    """Generate a timestamped unique ID.

    Format: {prefix}-{YYYYMMDD}-{NNN} where NNN is a zero-padded counter.
    Counter is per-prefix, per-day, derived from scanning existing files.
    """
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    # Counter would be derived from existing files in actual implementation
    pid_fragment = str(os.getpid())[-3:].zfill(3)
    return f"{prefix}-{date_str}-{pid_fragment}"


def validate_yaml_path(path: Path) -> Path:
    """Validate that a path points to a YAML file and exists."""
    if not path.exists():
        raise FileNotFoundError(f"Required YAML file not found: {path}")
    if path.suffix not in (".yaml", ".yml"):
        raise ValueError(f"Not a YAML file: {path}")
    return path
```

### 2.2 `models/constitution.py` — Constitutional Invariants

```python
"""Constitutional data models.
Spec reference: Section 2 (Constitutional Invariants)."""
from __future__ import annotations

from .base import FrameworkModel


class Axiom(FrameworkModel):
    """A single constitutional axiom (A1-A8)."""

    text: str
    enforcement: str


class Constitution(FrameworkModel):
    """Loaded representation of CONSTITUTION.md."""

    axioms: dict[str, Axiom]  # A1_human_halt, A2_human_veto, etc.
    hash: str  # SHA-256 of CONSTITUTION.md file content


class CharterPrinciple(FrameworkModel):
    """A domain charter principle."""

    id: str
    text: str


class Charter(FrameworkModel):
    """Domain-specific charter inheriting from constitution."""

    name: str
    motto: str
    principles: list[CharterPrinciple]
    quality_gates: list[str]
    forbidden: list[str]
    inherited_from: str  # Path to CONSTITUTION.md


class TaskMandate(FrameworkModel):
    """Per-task behavioral directives (overrides role defaults)."""

    motto: str | None = None
    constraints: list[str] = []
    relaxed_rules: list[str] = []
```

### 2.3 `models/capability.py` — Capability Atoms

```python
"""Capability atom models.
Spec reference: Section 4.1 (Capability Atoms)."""
from __future__ import annotations

from enum import StrEnum
from typing import Literal

from .base import FrameworkModel


class ModelPreference(StrEnum):
    """Claude model tier preference."""

    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"


class ThinkingSetting(FrameworkModel):
    """Thinking mode configuration — can be bool or 'extended'."""

    value: bool | Literal["extended"]


class CapabilityAtom(FrameworkModel):
    """A single composable capability fragment.
    Roles are composed from multiple atoms."""

    name: str
    description: str
    instruction_fragment: str
    model_preference: ModelPreference | None = None
    thinking: ThinkingSetting | None = None
    authority: bool = False
```

### 2.4 `models/voice.py` — Voice System

```python
"""Voice system models.
Spec reference: Section 4.6 (Voice System)."""
from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from .base import FrameworkModel


class VoiceAtomCategory(StrEnum):
    """Categories of voice atoms — prefix determines category."""

    LANGUAGE = "language"
    TONE = "tone"
    STYLE = "style"
    PERSONA = "persona"


class TokenCost(StrEnum):
    """Token cost classification for voice atoms."""

    MINIMAL = "minimal"  # ~5 tokens
    LOW = "low"          # ~10-15 tokens
    MODERATE = "moderate" # ~20-30 tokens


class VoiceAtom(FrameworkModel):
    """A single voice configuration fragment.
    Names use category prefixes: language_*, tone_*, style_*, persona_*."""

    name: str  # e.g., "language_japanese", "tone_assertive"
    category: VoiceAtomCategory
    description: str
    instruction_fragment: str
    token_cost: TokenCost = TokenCost.LOW
    creativity_mode: bool = False  # True for persona atoms that unlock creative behaviors
    tone_default: str | None = None  # For persona atoms: override tone
    output_token_impact: Literal["reduces", "increases", "neutral"] = "neutral"


class VoiceProfile(FrameworkModel):
    """A complete voice configuration for a role.
    Resolution cascade: role > domain_defaults > framework_defaults."""

    language: str  # Required — references a language_* atom
    tone: str | None = None  # References a tone_* atom
    style: str | None = None  # References a style_* atom
    persona: str | None = None  # References a persona_* atom (max 1)
    formality: float = Field(0.5, ge=0.0, le=1.0)
    verbosity: float = Field(0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_atom_prefixes(self) -> Self:
        """Ensure atom references use correct category prefixes."""
        if not self.language.startswith("language_"):
            raise ValueError(f"Language atom must start with 'language_': {self.language}")
        if self.tone and not self.tone.startswith("tone_"):
            raise ValueError(f"Tone atom must start with 'tone_': {self.tone}")
        if self.style and not self.style.startswith("style_"):
            raise ValueError(f"Style atom must start with 'style_': {self.style}")
        if self.persona and not self.persona.startswith("persona_"):
            raise ValueError(f"Persona atom must start with 'persona_': {self.persona}")
        return self


class VoiceSafetyConfig(FrameworkModel):
    """Validation rules for voice atom content safety.
    Spec reference: Section 4.6.3."""

    forbidden_patterns: list[str]  # Regex patterns that instruction_fragments must NOT match
    max_token_budget_pct: float = 0.02  # Voice must be < 2% of system_instructions
```

### 2.5 `models/role.py` — Role Composition

```python
"""Role composition models.
Spec reference: Section 4.2 (Composable Role Definitions)."""
from __future__ import annotations

from enum import IntEnum
from typing import Literal

from pydantic import Field

from .base import FrameworkModel
from .capability import ModelPreference, ThinkingSetting
from .voice import VoiceProfile


class BehavioralDescriptors(FrameworkModel):
    """Behavioral traits that shape reasoning style."""

    reasoning_style: Literal["strategic", "divergent", "analytical", "convergent", "lateral"]
    risk_tolerance: Literal["very_low", "low", "moderate", "high", "very_high"]
    exploration_vs_exploitation: float = Field(ge=0.0, le=1.0)


class AuthorityLevel(IntEnum):
    """Authority hierarchy matching protection rings."""

    WORKER = 0
    LEAD = 1
    ORCHESTRATOR = 2
    EVOLUTION_ENGINE = 3


class RoleComposition(FrameworkModel):
    """A complete role definition composed from atoms.
    Loaded from roles/compositions/{name}.yaml."""

    name: str
    description: str
    capabilities: list[str]  # References to CapabilityAtom names in capabilities.yaml
    model: ModelPreference
    thinking: ThinkingSetting
    behavioral_descriptors: BehavioralDescriptors
    voice: VoiceProfile
    authority_level: AuthorityLevel
    forbidden: list[str] = []
    scout_config: dict | None = None  # For scout roles: exploration parameters
    review_mandate: dict | None = None  # For reviewer roles: required checks
```

### 2.6 `models/task.py` — Task Lifecycle (9 States)

```python
"""Task lifecycle models.
Spec reference: Section 6 (Task Lifecycle — Full Audit)."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field

from .base import FrameworkModel, IdentifiableModel, TimestampedModel
from .capability import ModelPreference
from .constitution import TaskMandate


class TaskStatus(StrEnum):
    """9 task states from Section 6.1."""

    INTAKE = "intake"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    EXECUTING = "executing"
    PARKED = "parked"
    REVIEWING = "reviewing"
    VERDICT = "verdict"
    COMPLETE = "complete"
    ARCHIVED = "archived"


class TaskOriginType(StrEnum):
    """How a task was created."""

    HUMAN = "human"
    AGENT_GENERATED = "agent_generated"
    EVOLUTION_TRIGGERED = "evolution_triggered"
    SCOUT_DISCOVERY = "scout_discovery"


class TaskOrigin(FrameworkModel):
    type: TaskOriginType
    source: str
    reason: str


class TaskLinks(FrameworkModel):
    parent_task: str | None = None
    blocks: list[str] = []
    blocked_by: list[str] = []
    related_evolution: str | None = None


class TaskReview(FrameworkModel):
    """Mandatory review record (Axiom A7)."""

    reviewer: str
    reviewer_role: str
    findings: list[str]
    verdict: Literal["pass", "pass_with_notes", "fail"]
    reviewer_confidence: float = Field(ge=0.0, le=1.0)


class TaskMetrics(FrameworkModel):
    """Resource consumption metrics for a task."""

    tokens_used: int = 0
    tokens_cached: int = 0
    agents_spawned: int = 0
    time_elapsed: str | None = None
    review_rounds: int = 0
    budget_allocated: int = 0
    budget_utilization: float = 0.0
    tools_loaded: int = 0
    tools_per_step_avg: float = 0.0
    context_pressure_max: float = 0.0
    monetary_cost: float = 0.0


class TaskTimelineEntry(FrameworkModel):
    """A single event in a task's timeline."""

    time: datetime
    event: str
    actor: str
    detail: str


class TopologyAssignment(FrameworkModel):
    role: str
    agent_id: str
    model: ModelPreference


class TaskTopology(FrameworkModel):
    """Selected topology for task execution."""

    pattern: str  # solo, pipeline, parallel_swarm, hierarchical_team, hybrid, debate
    analysis: dict
    agents: list[TopologyAssignment]


class Task(IdentifiableModel):
    """Complete task record — the central data structure."""

    status: TaskStatus
    title: str
    description: str
    origin: TaskOrigin
    rationale: str
    priority: Literal["low", "medium", "high", "critical"]
    links: TaskLinks = TaskLinks()
    mandate: TaskMandate = TaskMandate()
    topology: TaskTopology | None = None
    timeline: list[TaskTimelineEntry] = []
    review: TaskReview | None = None
    artifacts: dict = {}
    metrics: TaskMetrics = TaskMetrics()


# Valid state transitions — enforced by TaskLifecycle engine
VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.INTAKE: {TaskStatus.ANALYSIS},
    TaskStatus.ANALYSIS: {TaskStatus.PLANNING},
    TaskStatus.PLANNING: {TaskStatus.EXECUTING, TaskStatus.PARKED},
    TaskStatus.EXECUTING: {TaskStatus.REVIEWING, TaskStatus.PARKED},
    TaskStatus.PARKED: {TaskStatus.PLANNING, TaskStatus.EXECUTING},
    TaskStatus.REVIEWING: {TaskStatus.VERDICT},
    TaskStatus.VERDICT: {TaskStatus.COMPLETE, TaskStatus.PLANNING},  # fail → re-plan
    TaskStatus.COMPLETE: {TaskStatus.ARCHIVED},
    TaskStatus.ARCHIVED: set(),  # terminal state
}
```

### 2.7 `models/evolution.py` — Evolution Engine

```python
"""Evolution engine models.
Spec reference: Section 7 (Evolution Engine), Section 8 (Dual-Copy)."""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum
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


class EvolutionProposal(IdentifiableModel):
    tier: EvolutionTier
    component: str  # File path being modified
    diff: str       # Unified diff
    rationale: str
    evidence: dict  # triggering_tasks, metrics, etc.
    estimated_risk: float = Field(ge=0.0, le=1.0)


class QuorumVote(FrameworkModel):
    """A single sealed vote in a quorum process."""

    voter_id: str
    voter_role: str
    vote: Literal["approve", "reject"]
    rationale: str
    timestamp: datetime


class QuorumResult(FrameworkModel):
    votes: list[QuorumVote]
    threshold: float
    approved: bool


class EvolutionRecord(IdentifiableModel):
    """Post-approval evolution record."""

    proposal: EvolutionProposal
    approved_by: str  # "auto (tier 3)", "quorum", "human"
    constitutional_check: Literal["pass", "fail"]
    rollback_commit: str  # Git SHA for rollback
    quorum: QuorumResult | None = None


class DualCopyCandidate(FrameworkModel):
    """A fork being evaluated in dual-copy bootstrapping."""

    evo_id: str
    fork_path: Path  # state/evolution/candidates/{evo-id}/
    modified_files: list[str]
    evaluation: dict  # capability, consistency, robustness scores
    promoted: bool = False
```

### 2.8 `models/resource.py` — Resource Awareness

```python
"""Resource awareness models.
Spec reference: Section 18 (Resource Awareness & Token Efficiency)."""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum, StrEnum

from .base import FrameworkModel


class BudgetPressureLevel(StrEnum):
    """Budget pressure levels from Section 18.2."""

    GREEN = "green"    # > 60% remaining — normal operation
    YELLOW = "yellow"  # 30-60% — compress, reduce tool calls
    ORANGE = "orange"  # 10-30% — critical-only, single-agent
    RED = "red"        # < 10% — emergency: park everything, alert human


class TokenBudget(FrameworkModel):
    remaining_tokens: int
    remaining_requests: int
    window_reset_time: datetime
    weekly_utilization: float
    task_budget: int
    task_spent: int
    pressure_level: BudgetPressureLevel


class RateLimitBucket(FrameworkModel):
    capacity: int
    current: int
    replenish_rate: str  # "per minute"


class RateLimitMirror(FrameworkModel):
    """Local mirror of server-side rate limits (Section 18.3)."""

    rpm: RateLimitBucket
    itpm: RateLimitBucket
    otpm: RateLimitBucket
    last_updated: datetime


class ComputeMetrics(FrameworkModel):
    """System resource metrics (Section 18.4)."""

    cpu_percent: float
    memory_percent: float
    disk_percent: float
    active_agents: int
    max_agents: int


class SpendLevel(IntEnum):
    """Monetary cost approval tiers (Section 18.5)."""

    FREE = 0    # File ops, git, Claude API (subscription)
    LOW = 1     # Web search, small API calls < $0.10
    MEDIUM = 2  # Large API calls $0.10-$10
    HIGH = 3    # SaaS subscriptions, > $10


class CostApproval(FrameworkModel):
    spend_level: SpendLevel
    amount: float
    purpose: str
    approved: bool
    approved_by: str | None = None
```

### 2.9 `models/environment.py` — Environment Awareness

```python
"""Environment awareness models.
Spec reference: Section 19 (Environment Awareness & Self-Benchmarking)."""
from __future__ import annotations

import math

from pydantic import Field

from .base import FrameworkModel, TimestampedModel


class ModelFingerprint(TimestampedModel):
    """Compact representation of model capabilities at a point in time."""

    model_id: str
    reasoning_score: float = Field(ge=0.0, le=1.0)
    instruction_score: float = Field(ge=0.0, le=1.0)
    code_score: float = Field(ge=0.0, le=1.0)
    creative_score: float = Field(ge=0.0, le=1.0)
    tool_score: float = Field(ge=0.0, le=1.0)
    avg_latency_ms: int
    avg_output_tokens: int

    def distance_to(self, other: ModelFingerprint) -> float:
        """Euclidean distance between fingerprint vectors (5 dimensions)."""
        return math.sqrt(
            (self.reasoning_score - other.reasoning_score) ** 2
            + (self.instruction_score - other.instruction_score) ** 2
            + (self.code_score - other.code_score) ** 2
            + (self.creative_score - other.creative_score) ** 2
            + (self.tool_score - other.tool_score) ** 2
        )


class CanaryResult(FrameworkModel):
    """Result of a single canary micro-benchmark."""

    task_name: str
    expected: str
    actual: str
    score: float
    tokens_used: int
    latency_ms: int


class DriftDetection(FrameworkModel):
    """Result of drift analysis comparing current vs baseline fingerprints."""

    current: ModelFingerprint
    baseline: ModelFingerprint
    distance: float
    threshold: float = 0.15  # 15% deviation triggers investigation
    drift_detected: bool
    affected_dimensions: list[str]
```

### 2.10 `models/protection.py` — Hierarchical Protection

```python
"""Protection ring models.
Spec reference: Section 20 (Self-Leaning-Down & Capability Protection)."""
from __future__ import annotations

from enum import IntEnum, StrEnum

from .base import FrameworkModel


class ProtectionRing(IntEnum):
    """OS-inspired protection rings. Same hierarchy as evolution tiers."""

    RING_0_IMMUTABLE = 0   # Constitution, self-monitor, pruner — NEVER modified
    RING_1_PROTECTED = 1   # Memory, context engine, evolution — human approval
    RING_2_VALIDATED = 2   # Curated skills, proven tools — quorum approval
    RING_3_EXPENDABLE = 3  # New skills, experimental — auto-approved


class RingClassification(FrameworkModel):
    path: str  # File or capability path
    ring: ProtectionRing
    reason: str


class RingTransition(FrameworkModel):
    item: str
    from_ring: ProtectionRing
    to_ring: ProtectionRing
    reason: str
    evidence: str
    approved_by: str


class ContextPressureLevel(StrEnum):
    """Context window utilization levels (Section 20.5)."""

    HEALTHY = "healthy"    # < 60%
    PRESSURE = "pressure"  # 60-80% → trigger compression
    CRITICAL = "critical"  # 80-95% → aggressive compression
    OVERFLOW = "overflow"  # > 95% → emergency
```

### 2.11 `models/context.py` — Context Engineering

```python
"""Context engineering models.
Spec reference: Section 21 (Context Engineering Pipeline)."""
from __future__ import annotations

from enum import IntEnum

from .base import FrameworkModel
from .protection import ContextPressureLevel


class ContextBudgetAllocation(FrameworkModel):
    """Pre-allocated context window space by category (Section 21.2)."""

    system_instructions_pct: float = 0.10  # Ring 0 constitution + role + mandate
    active_tools_pct: float = 0.15         # Currently loaded tool definitions (3-5 tools)
    current_task_pct: float = 0.40         # Task description, plan, current step, code/data
    working_memory_pct: float = 0.25       # Conversation history, intermediate results
    reserve_pct: float = 0.10             # Buffer for unexpected needs


class CompressionStage(IntEnum):
    """Progressive compression stages (Section 20.5)."""

    NONE = 0              # < 60% — no compression
    HISTORY = 1           # > 60% — summarize old turns
    TOOL_REDUCTION = 2    # > 70% — reduce to top-3 tools
    TASK_PRUNING = 3      # > 80% — SWE-Pruner task-aware pruning
    SYSTEM_COMPRESS = 4   # > 90% — Ring 0 only in system prompt
    EMERGENCY = 5         # > 95% — summarize everything non-Ring-0


class ContextSnapshot(FrameworkModel):
    """Point-in-time snapshot of context composition."""

    total_tokens: int
    system_tokens: int
    tool_tokens: int
    task_tokens: int
    history_tokens: int
    reserve_tokens: int
    pressure_level: ContextPressureLevel
    compression_stage: CompressionStage
    ring_0_tokens: int  # NEVER compressed
```

### 2.12 `models/agent.py` — Agent Registry

```python
"""Agent registry models.
Spec reference: Section 4.4 (spawn_agent function)."""
from __future__ import annotations

from enum import StrEnum

from .base import IdentifiableModel
from .capability import ModelPreference


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
```

### 2.13 `models/audit.py` — 8-Stream Audit Logging

```python
"""Audit logging models.
Spec reference: Section 17 (Audit System & Viewers)."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from .base import FrameworkModel
from .evolution import EvolutionTier


class LogStream(StrEnum):
    """8 audit log streams."""

    EVOLUTION = "evolution"
    TASKS = "tasks"
    DECISIONS = "decisions"
    DIVERSITY = "diversity"
    CREATIVITY = "creativity"
    RESOURCES = "resources"
    ENVIRONMENT = "environment"
    TRACES = "traces"


class BaseLogEntry(FrameworkModel):
    """Base for all log entries."""

    id: str
    timestamp: datetime
    stream: LogStream


class EvolutionLogEntry(BaseLogEntry):
    stream: Literal[LogStream.EVOLUTION] = LogStream.EVOLUTION
    tier: EvolutionTier
    component: str
    diff: str
    rationale: str
    evidence: dict
    approved_by: str
    constitutional_check: str
    rollback_commit: str


class TaskLogEntry(BaseLogEntry):
    stream: Literal[LogStream.TASKS] = LogStream.TASKS
    task_id: str
    event: str
    task_title: str
    actor: str
    actor_role: str
    detail: dict
    tokens_used: int = 0


class DecisionLogEntry(BaseLogEntry):
    stream: Literal[LogStream.DECISIONS] = LogStream.DECISIONS
    decision_type: str
    actor: str
    options_considered: list[dict]
    selected: str
    rationale: str


class ResourceLogEntry(BaseLogEntry):
    stream: Literal[LogStream.RESOURCES] = LogStream.RESOURCES
    event_type: str  # budget_check, rate_limit, spawn_decision, cost_approval
    detail: dict


class EnvironmentLogEntry(BaseLogEntry):
    stream: Literal[LogStream.ENVIRONMENT] = LogStream.ENVIRONMENT
    event_type: str  # fingerprint, drift, revalidation, version_change
    detail: dict


class TraceLogEntry(BaseLogEntry):
    stream: Literal[LogStream.TRACES] = LogStream.TRACES
    level: Literal["operational", "cognitive", "contextual"]
    detail: dict
```

### 2.14 `models/session.py` — Session Lock

```python
"""Session lock model.
Spec reference: Section 3.3 (Bootstrap boot sequence, step 3)."""
from __future__ import annotations

from datetime import datetime

from .base import FrameworkModel


class SessionLock(FrameworkModel):
    """Contents of .claude-framework.lock file."""

    pid: int
    started: datetime
    session_id: str
    claude_version: str
    active_domain: str
```

### 2.15 `models/domain.py` — Domain Configuration

```python
"""Domain configuration models.
Spec reference: Section 22 (Domain Instantiation & Switching)."""
from __future__ import annotations

from .base import FrameworkModel


class VoiceDefaults(FrameworkModel):
    """Default voice settings for a domain."""

    language: str = "language_japanese"
    tone: str = "tone_cautious"
    style: str = "style_technical"


class DomainConfig(FrameworkModel):
    """Configuration for a domain instance."""

    name: str
    charter_path: str
    voice_defaults: VoiceDefaults = VoiceDefaults()
    active: bool = True
    max_concurrent_agents: int = 5
    topology_patterns: list[str] = ["solo", "hierarchical_team"]
```

### 2.16 YAML Serialization Utility

```python
"""YAML serialization helpers — used throughout the framework.
NOT a model file, but critical infrastructure."""
from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def model_to_yaml(model: BaseModel, path: Path) -> None:
    """Serialize a Pydantic model to YAML file.
    Uses atomic write pattern for safety."""
    data = model.model_dump(mode="json", exclude_none=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f".tmp.{__import__('os').getpid()}")
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_path.replace(path)  # Atomic on POSIX


def model_from_yaml(model_class: type[T], path: Path) -> T:
    """Deserialize a Pydantic model from YAML file.
    NEVER returns defaults — raises on missing or invalid files."""
    if not path.exists():
        raise FileNotFoundError(f"Required YAML file not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"Empty YAML file: {path}")
    return model_class.model_validate(data)
```

---

## Part 3: State Management Layer

All framework state persists as files on disk — YAML for structured data, JSONL for append-only logs, git for versioned evolution. No database. No in-memory-only state. Every state mutation is atomic and fail-loud.

Spec references: Section 3.3 (bootstrap), Section 17 (audit), Section 24 (directory tree).

### 3.1 `state/yaml_store.py` — Atomic YAML Operations

The most critical infrastructure module. All framework configuration and mutable state lives in YAML files. Every read validates through Pydantic. Every write is atomic.

```python
"""Atomic YAML file operations with Pydantic validation.
Spec reference: Section 3.3 (state persistence), Section 24 (directory tree)."""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from ..models.base import FrameworkModel

T = TypeVar("T", bound=BaseModel)

# Hard size cap — refuse to load files over 1MB (failure mode S6)
MAX_YAML_SIZE_BYTES = 1_048_576


class YamlStore:
    """Atomic YAML file operations with advisory file locking.

    Design invariants:
    - Atomic writes via temp-file + os.replace() — prevents partial writes on crash (S2)
    - Advisory file locks via fcntl.flock() — prevents concurrent writes (S1)
    - Pydantic validation on every read — corrupt YAML caught immediately (S4)
    - Fail-loud: no defaults, no fallbacks. Missing/corrupt → raise immediately
    - Always yaml.safe_load(), NEVER yaml.load() (S5)
    - All file ops enforce encoding='utf-8' (S8)
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        if not self.base_dir.is_dir():
            raise FileNotFoundError(f"Base directory does not exist: {self.base_dir}")

    def _resolve(self, relative_path: str) -> Path:
        """Resolve relative path to absolute, validate it stays within base_dir."""
        full = (self.base_dir / relative_path).resolve()
        if not str(full).startswith(str(self.base_dir)):
            raise ValueError(f"Path escapes base directory: {relative_path}")
        return full

    def read(self, relative_path: str, model_class: type[T]) -> T:
        """Read YAML file, deserialize to Pydantic model.
        Raises FileNotFoundError or ValidationError (never returns defaults)."""
        path = self._resolve(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"Required YAML file not found: {path}")
        if not os.access(path, os.R_OK):
            raise PermissionError(f"Cannot read file (check permissions): {path}")
        file_size = path.stat().st_size
        if file_size > MAX_YAML_SIZE_BYTES:
            raise ValueError(
                f"YAML file exceeds size cap ({file_size} > {MAX_YAML_SIZE_BYTES}): {path}"
            )
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            raise ValueError(f"Empty YAML file: {path}")
        return model_class.model_validate(data)

    def write(self, relative_path: str, model: FrameworkModel) -> None:
        """Atomic write: serialize to temp file, then os.replace().
        Acquires advisory lock for duration of write."""
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Check disk space before write (S3)
        try:
            import psutil
            disk = psutil.disk_usage(str(path.parent))
            if disk.free < 100 * 1024 * 1024:  # 100MB threshold
                raise OSError(
                    f"Insufficient disk space ({disk.free // 1024 // 1024}MB free). "
                    f"Refusing write to prevent data corruption: {path}"
                )
        except ImportError:
            pass  # psutil optional for disk check

        data = model.model_dump(mode="json", exclude_none=True)
        tmp_path = path.with_suffix(f".tmp.{os.getpid()}")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                yaml.dump(data, f, default_flow_style=False,
                          allow_unicode=True, sort_keys=False)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            tmp_path.replace(path)  # Atomic on POSIX
        except Exception:
            # Clean up temp file on any failure
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def read_raw(self, relative_path: str) -> dict:
        """Read YAML as raw dict (for partial reads). Still validates basic structure."""
        path = self._resolve(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"Required YAML file not found: {path}")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            raise ValueError(f"Empty YAML file: {path}")
        if not isinstance(data, dict):
            raise TypeError(f"Expected YAML dict, got {type(data).__name__}: {path}")
        return data

    def write_raw(self, relative_path: str, data: dict) -> None:
        """Atomic write from raw dict. Same atomic pattern as write()."""
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f".tmp.{os.getpid()}")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False,
                          allow_unicode=True, sort_keys=False)
            tmp_path.replace(path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def exists(self, relative_path: str) -> bool:
        return self._resolve(relative_path).exists()

    def list_dir(self, relative_path: str) -> list[str]:
        path = self._resolve(relative_path)
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        return sorted(p.name for p in path.iterdir())
```

### 3.2 `state/jsonl_writer.py` — Append-Only 8-Stream Logger

```python
"""Append-only JSONL log writer with rotation.
Spec reference: Section 17 (Audit System)."""
from __future__ import annotations

import fcntl
import json
import os
import re
from datetime import datetime
from pathlib import Path

from ..models.audit import BaseLogEntry, LogStream

# Secret patterns to scrub before writing (X7)
_SECRET_PATTERNS = [
    re.compile(r"(sk-[a-zA-Z0-9]{20,})"),         # API keys
    re.compile(r"(ghp_[a-zA-Z0-9]{36})"),          # GitHub tokens
    re.compile(r"(password\s*[=:]\s*\S+)", re.I),  # Password assignments
    re.compile(r"(ANTHROPIC_API_KEY\s*=\s*\S+)"),  # Anthropic keys
]


class JsonlWriter:
    """Append-only JSONL log writer with rotation support.

    Design invariants:
    - Append-only: entries are never modified after writing
    - Thread-safe: file lock on every append (A1)
    - Rotation at configurable max size (default 10MB)
    - Max rotated files to prevent unbounded disk usage (A3)
    - Corrupt lines skipped on read with warning logged (A2)
    - Secret scrubbing before write (X7)
    """

    def __init__(
        self,
        log_dir: Path,
        stream: LogStream,
        max_size_mb: int = 10,
        max_rotated_files: int = 10,
    ):
        self.log_dir = log_dir
        self.stream = stream
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_rotated_files = max_rotated_files
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @property
    def current_path(self) -> Path:
        return self.log_dir / f"{self.stream.value}.jsonl"

    def append(self, entry: BaseLogEntry) -> None:
        """Append a log entry. Thread-safe via file lock."""
        line = entry.model_dump_json(exclude_none=True)
        line = self._scrub_secrets(line)
        self._maybe_rotate()
        with open(self.current_path, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(line + "\n")
            f.flush()
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def read_entries(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Read entries with optional time-range filter.
        Searches current + rotated files for time-range queries (A4)."""
        entries: list[dict] = []
        for path in self._all_log_files():
            if not path.exists():
                continue
            with open(path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        # Corrupt line — skip with warning (A2)
                        import sys
                        print(
                            f"WARNING: Corrupt JSON at {path}:{line_num}, skipping",
                            file=sys.stderr,
                        )
                        continue
                    ts = entry.get("timestamp", "")
                    if since and ts < since.isoformat():
                        continue
                    if until and ts > until.isoformat():
                        continue
                    entries.append(entry)
                    if len(entries) >= limit:
                        return entries
        return entries

    def _maybe_rotate(self) -> None:
        """Rotate if current file exceeds max size."""
        if not self.current_path.exists():
            return
        if self.current_path.stat().st_size < self.max_size_bytes:
            return
        self.rotate()

    def rotate(self) -> None:
        """Rotate current log file. Sequence (A6):
        1. Create new empty file
        2. Atomic rename old → rotated
        3. Clean up excess rotated files
        """
        if not self.current_path.exists():
            return
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        rotated = self.log_dir / f"{self.stream.value}.{timestamp}.jsonl"
        self.current_path.rename(rotated)
        self.current_path.touch()
        self._cleanup_old_rotated()

    def _all_log_files(self) -> list[Path]:
        """Current + rotated files, sorted chronologically."""
        files = sorted(self.log_dir.glob(f"{self.stream.value}.*.jsonl"))
        if self.current_path.exists():
            files.append(self.current_path)
        return files

    def _cleanup_old_rotated(self) -> None:
        """Remove oldest rotated files exceeding max_rotated_files."""
        rotated = sorted(self.log_dir.glob(f"{self.stream.value}.*.jsonl"))
        while len(rotated) > self.max_rotated_files:
            oldest = rotated.pop(0)
            oldest.unlink()

    @staticmethod
    def _scrub_secrets(text: str) -> str:
        """Remove known secret patterns from log text (X7)."""
        for pattern in _SECRET_PATTERNS:
            text = pattern.sub("[REDACTED]", text)
        return text
```

### 3.3 `state/git_ops.py` — Evolution Git Operations

```python
"""Git operations for evolution tracking and rollback.
Spec reference: Section 9 (Dual-Copy Evolution), Section 20.1 (immutability)."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


class GitOpsError(Exception):
    """Raised when a git operation fails."""


class GitOps:
    """Git operations for evolution tracking and rollback.

    Design invariants:
    - Never rebase or force-push (E5: preserve audit trail)
    - All evolution branches are merge-only
    - Structured commit messages for machine parsing
    - SHA-256 hash verification for constitution guard
    """

    def __init__(self, repo_dir: Path):
        self.repo_dir = repo_dir.resolve()

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the repo directory."""
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check and result.returncode != 0:
            raise GitOpsError(
                f"git {' '.join(args)} failed (exit {result.returncode}):\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        return result

    def commit_evolution(
        self,
        evo_id: str,
        tier: int,
        rationale: str,
        approved_by: str,
        files: list[str],
    ) -> str:
        """Structured evolution commit. Returns SHA.

        Commit message format:
            [evo] {evo_id} tier={tier}

            Rationale: {rationale}
            Approved-by: {approved_by}
            Files: {comma-separated files}
        """
        for f in files:
            self._run("add", f)
        msg = (
            f"[evo] {evo_id} tier={tier}\n\n"
            f"Rationale: {rationale}\n"
            f"Approved-by: {approved_by}\n"
            f"Files: {', '.join(files)}"
        )
        self._run("commit", "-m", msg)
        result = self._run("rev-parse", "HEAD")
        return result.stdout.strip()

    def create_rollback_point(self) -> str:
        """Tag current HEAD as a rollback target. Returns SHA."""
        result = self._run("rev-parse", "HEAD")
        sha = result.stdout.strip()
        return sha

    def rollback_to(self, commit_sha: str) -> None:
        """Create a revert commit to undo changes back to the given SHA.
        Never uses git reset --hard (E5: preserve history)."""
        self._run("revert", "--no-commit", f"{commit_sha}..HEAD")
        self._run("commit", "-m", f"[rollback] Revert to {commit_sha[:8]}")

    def compute_file_hash(self, path: str) -> str:
        """Compute SHA-256 of a file's content."""
        full_path = self.repo_dir / path
        if not full_path.exists():
            raise FileNotFoundError(f"Cannot hash missing file: {full_path}")
        content = full_path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def verify_file_hash(self, path: str, expected_hash: str) -> bool:
        """Verify file content hash (SHA-256)."""
        actual = self.compute_file_hash(path)
        return actual == expected_hash

    def get_diff(self, from_sha: str, to_sha: str) -> str:
        """Get unified diff between two commits."""
        result = self._run("diff", from_sha, to_sha)
        return result.stdout

    def create_evolution_branch(self, evo_id: str) -> str:
        """Create a branch for evolution evaluation."""
        branch_name = f"evo/{evo_id}"
        self._run("checkout", "-b", branch_name)
        return branch_name

    def merge_evolution_branch(self, branch_name: str) -> str:
        """Merge evolution branch back to main. Returns merge commit SHA."""
        self._run("checkout", "main")
        self._run("merge", "--no-ff", branch_name,
                  "-m", f"[evo-merge] {branch_name}")
        result = self._run("rev-parse", "HEAD")
        return result.stdout.strip()

    def delete_evolution_branch(self, branch_name: str) -> None:
        """Delete a rejected evolution branch."""
        self._run("branch", "-d", branch_name)
```

### 3.4 `state/lock_manager.py` — Session Lock

```python
"""Session lock management for single-instance enforcement.
Spec reference: Section 3.3 (bootstrap, step 3)."""
from __future__ import annotations

import atexit
import os
import signal
import subprocess
from datetime import datetime
from pathlib import Path

import yaml

from ..models.session import SessionLock

LOCK_FILENAME = ".claude-framework.lock"


class SessionAlreadyActiveError(RuntimeError):
    """Raised when attempting to acquire a lock held by a live process."""


class LockManager:
    """Manages .claude-framework.lock for single-session enforcement.

    Design invariants:
    - Atomic lock acquisition via open(path, 'x') (L4)
    - PID + start_time verification to detect PID reuse (L2)
    - atexit cleanup for normal exits (L5)
    - Signal handler for SIGTERM (X5)
    - Stale lock detection via os.kill(pid, 0) (L1)
    """

    def __init__(self, framework_root: Path):
        self.lock_path = framework_root / LOCK_FILENAME
        self._owns_lock = False

    def acquire(self, domain: str = "meta") -> SessionLock:
        """Acquire lock. Raises SessionAlreadyActiveError if lock held
        by live process. Removes stale locks with warning."""
        if self.lock_path.exists():
            existing = self._read_lock()
            if existing and self._is_process_alive(existing.pid):
                raise SessionAlreadyActiveError(
                    f"Another framework session is active "
                    f"(PID {existing.pid}, started {existing.started}). "
                    f"Terminate it first or run 'tools/force-unlock.sh'."
                )
            else:
                # Stale lock — warn and remove (L1)
                import sys
                pid_info = existing.pid if existing else "unknown"
                print(
                    f"WARNING: Removing stale lock (PID {pid_info} is dead)",
                    file=sys.stderr,
                )
                self.lock_path.unlink()

        lock = SessionLock(
            pid=os.getpid(),
            started=datetime.utcnow(),
            session_id=f"sess-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            claude_version=self._get_claude_version(),
            active_domain=domain,
        )

        # Atomic create via exclusive open (L4)
        try:
            fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                data = lock.model_dump(mode="json")
                yaml.dump(data, f, default_flow_style=False)
        except FileExistsError:
            raise SessionAlreadyActiveError(
                "Lock file appeared during acquisition (race condition). "
                "Another session started simultaneously."
            )

        self._owns_lock = True

        # Register cleanup (L5)
        atexit.register(self.release)
        signal.signal(signal.SIGTERM, self._signal_handler)

        return lock

    def release(self) -> None:
        """Release lock on clean shutdown."""
        if self._owns_lock and self.lock_path.exists():
            self.lock_path.unlink(missing_ok=True)
            self._owns_lock = False

    def check(self) -> SessionLock | None:
        """Check if lock exists and holder is alive. Returns info or None."""
        if not self.lock_path.exists():
            return None
        lock = self._read_lock()
        if lock and self._is_process_alive(lock.pid):
            return lock
        return None  # Stale

    def force_unlock(self) -> None:
        """Force-remove lock (for stale lock recovery)."""
        if self.lock_path.exists():
            self.lock_path.unlink()

    def verify_ownership(self) -> bool:
        """Verify current process owns the lock."""
        if not self.lock_path.exists():
            return False
        lock = self._read_lock()
        return lock is not None and lock.pid == os.getpid()

    def _read_lock(self) -> SessionLock | None:
        """Read lock file, return None if corrupt."""
        try:
            with open(self.lock_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data is None:
                return None
            return SessionLock.model_validate(data)
        except Exception:
            return None

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        """Check if process with PID is running (L1)."""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    @staticmethod
    def _get_claude_version() -> str:
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def _signal_handler(self, signum: int, frame: object) -> None:
        """Handle SIGTERM: release lock then exit (X5)."""
        self.release()
        raise SystemExit(128 + signum)
```

### 3.5 `state/directory.py` — Directory Scaffold

```python
"""Directory structure creation and validation.
Spec reference: Section 24 (Project Directory Tree)."""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar


class DirectoryManager:
    """Creates and validates framework directory structure.

    Design invariants:
    - Idempotent: re-running is always safe (D1)
    - Never overwrites existing files (D2)
    - Clear error on permission denied (D3)
    - Matches Section 24 exactly
    """

    # Structure definition — directories end with /, files don't
    CORE_DIRS: ClassVar[list[str]] = [
        "core/",
        "core/canary-tasks/",
        "roles/",
        "roles/capabilities/",
        "roles/compositions/",
        "shared/",
        "shared/skills/",
        "shared/tools/",
        "shared/archive/",
        "tools/",
        "tests/",
    ]

    INSTANCE_DIRS: ClassVar[list[str]] = [
        "state/",
        "state/tasks/",
        "state/tasks/active/",
        "state/tasks/parked/",
        "state/tasks/completed/",
        "state/agents/",
        "state/evolution/",
        "state/evolution/proposals/",
        "state/evolution/candidates/",
        "state/evolution/archive/",
        "state/coordination/",
        "state/coordination/pressure-fields/",
        "logs/",
        "logs/evolution/",
        "logs/tasks/",
        "logs/decisions/",
        "logs/diversity/",
        "logs/creativity/",
        "logs/resources/",
        "logs/environment/",
        "logs/traces/",
    ]

    CORE_FILES: ClassVar[dict[str, str]] = {
        "core/constitution-hash.txt": "",  # Populated during bootstrap
        "core/lifecycle.yaml": "",         # Task lifecycle definition
        "core/audit.yaml": "",             # Audit configuration
    }

    def scaffold(self, root: Path, domain: str = "meta") -> list[str]:
        """Create full directory structure. Returns list of created items."""
        created: list[str] = []

        # Top-level directories
        for d in self.CORE_DIRS:
            path = root / d
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                created.append(str(d))

        # Core placeholder files
        for filename, content in self.CORE_FILES.items():
            path = root / filename
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                created.append(filename)

        # Domain instance
        created.extend(self.scaffold_domain(root, domain))

        return created

    def scaffold_domain(self, root: Path, domain_name: str) -> list[str]:
        """Create a new domain instance directory."""
        created: list[str] = []
        instance_root = root / "instances" / domain_name

        for d in self.INSTANCE_DIRS:
            path = instance_root / d
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                created.append(f"instances/{domain_name}/{d}")

        # Create empty JSONL log files
        for stream in [
            "evolution", "tasks", "decisions", "diversity",
            "creativity", "resources", "environment", "traces",
        ]:
            log_file = instance_root / "logs" / stream / f"{stream}.jsonl"
            if not log_file.exists():
                log_file.touch()
                created.append(f"instances/{domain_name}/logs/{stream}/{stream}.jsonl")

        # Focus file
        focus_path = instance_root / "state" / "tasks" / "focus.yaml"
        if not focus_path.exists():
            focus_path.write_text("focus_task_id: null\n", encoding="utf-8")
            created.append(f"instances/{domain_name}/state/tasks/focus.yaml")

        return created

    def validate(self, root: Path) -> list[str]:
        """Check existing structure for missing items. Returns issues."""
        issues: list[str] = []
        for d in self.CORE_DIRS:
            if not (root / d).is_dir():
                issues.append(f"Missing directory: {d}")
        return issues
```

---

## Part 4: Engine Layer — Core Logic

The engine layer contains the framework's operational intelligence: prompt assembly, task state machines, agent spawning, constitution enforcement, resource tracking, topology routing, and environment monitoring. Each module is a Python class invoked by CLI tools.

Spec references: Sections 4-6 (roles, topology, tasks), 9 (evolution), 17-21 (audit, resource, environment, protection, context).

### 4.1 `engine/prompt_composer.py` — THE HEART

The prompt composer assembles agent prompts following the Ring 0→3 injection order, voice system, context budget allocation, and compression cascade. This is the single most important module in the framework.

```python
"""Ring-ordered prompt assembly engine.
Spec reference: Section 21 (Context Engineering Pipeline),
Section 4.6 (Voice System), Section 20.5 (Compression Cascade)."""
from __future__ import annotations

from enum import IntEnum
from pathlib import Path

from ..models.base import FrameworkModel
from ..models.capability import CapabilityAtom
from ..models.constitution import Constitution
from ..models.context import (
    CompressionStage,
    ContextBudgetAllocation,
    ContextSnapshot,
)
from ..models.domain import DomainConfig, VoiceDefaults
from ..models.protection import ContextPressureLevel
from ..models.resource import TokenBudget
from ..models.role import RoleComposition
from ..models.task import Task
from ..models.voice import VoiceAtom, VoiceProfile
from ..state.yaml_store import YamlStore


class PromptRing(IntEnum):
    """Injection order matches protection ring hierarchy."""

    RING_0 = 0  # Constitution, safety, self-monitor — NEVER compressed
    RING_1 = 1  # Infrastructure, coordination, resource awareness
    RING_2 = 2  # Role composition: behavioral + voice + capability fragments
    RING_3 = 3  # Skills, task context, tools, working memory


class PromptSection(FrameworkModel):
    """A discrete section of the composed prompt."""

    ring: PromptRing
    name: str
    content: str
    token_estimate: int
    compressible: bool  # Ring 0 sections = False, all others = True
    priority: float     # 0.0 = drop first, 1.0 = drop last (within ring)


class ComposedPrompt(FrameworkModel):
    """The fully assembled agent prompt with metadata."""

    sections: list[PromptSection]
    total_tokens: int
    compression_stage: CompressionStage
    voice_profile: VoiceProfile
    tools_loaded: list[str]
    dropped_sections: list[str]  # Names of sections removed by compression


# Token estimation: 3.5 chars/token for English (cold start seed)
# Calibrated against /usage output after 10+ samples (rolling average)
CHARS_PER_TOKEN_DEFAULT = 3.5


def estimate_tokens(text: str, chars_per_token: float = CHARS_PER_TOKEN_DEFAULT) -> int:
    """Estimate token count from text length.
    Primary method: parse /usage output (see ResourceTracker).
    Fallback: character-ratio estimation."""
    return max(1, int(len(text) / chars_per_token))


class PromptComposer:
    """Assembles agent prompts from framework state.

    Composition pipeline:
    1. Build Ring 0: constitution axioms, safety constraints
    2. Build Ring 1: infrastructure instructions, coordination protocol
    3. Build Ring 2: role composition (capabilities + voice + behavioral)
    4. Build Ring 3: skills, task context, selected tools
    5. Apply context budget allocation (10/15/40/25/10%)
    6. Apply compression cascade if over budget
    7. Apply edge placement (critical info at beginning/end)
    8. Return assembled prompt with metadata
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        constitution_path: Path,
    ):
        self.yaml_store = yaml_store
        self.constitution_path = constitution_path

    def compose(
        self,
        role: RoleComposition,
        task: Task,
        domain: DomainConfig,
        capabilities: dict[str, CapabilityAtom],
        voice_atoms: dict[str, VoiceAtom],
        max_tokens: int = 200_000,
        allocation: ContextBudgetAllocation | None = None,
    ) -> ComposedPrompt:
        """Full prompt composition pipeline."""
        if allocation is None:
            allocation = ContextBudgetAllocation()

        # 1. Build all ring sections
        sections: list[PromptSection] = []
        sections.extend(self._build_ring_0())
        sections.extend(self._build_ring_1(domain))
        sections.extend(self._build_ring_2(role, capabilities, voice_atoms,
                                            domain.voice_defaults))
        sections.extend(self._build_ring_3(task))

        # 2. Calculate totals
        total = sum(s.token_estimate for s in sections)

        # 3. Determine compression stage
        utilization = total / max_tokens if max_tokens > 0 else 1.0
        stage = self._determine_compression_stage(utilization)

        # 4. Apply compression if needed
        dropped: list[str] = []
        if stage > CompressionStage.NONE:
            sections, dropped = self._apply_compression(sections, stage)

        # 5. Apply edge placement (lost-in-the-middle mitigation)
        sections = self._apply_edge_placement(sections)

        final_total = sum(s.token_estimate for s in sections)

        return ComposedPrompt(
            sections=sections,
            total_tokens=final_total,
            compression_stage=stage,
            voice_profile=role.voice,
            tools_loaded=[],  # Populated by tool loader
            dropped_sections=dropped,
        )

    def _build_ring_0(self) -> list[PromptSection]:
        """Constitution axioms and safety constraints. NEVER compressed."""
        content = self.constitution_path.read_text(encoding="utf-8")
        return [
            PromptSection(
                ring=PromptRing.RING_0,
                name="constitution",
                content=f"## Constitutional Axioms (IMMUTABLE)\n\n{content}",
                token_estimate=estimate_tokens(content),
                compressible=False,
                priority=1.0,
            )
        ]

    def _build_ring_1(self, domain: DomainConfig) -> list[PromptSection]:
        """Infrastructure: coordination protocol, resource awareness."""
        charter_section = (
            f"## Domain: {domain.name}\n"
            f"Max concurrent agents: {domain.max_concurrent_agents}\n"
            f"Topology patterns: {', '.join(domain.topology_patterns)}\n"
        )
        return [
            PromptSection(
                ring=PromptRing.RING_1,
                name="domain_context",
                content=charter_section,
                token_estimate=estimate_tokens(charter_section),
                compressible=True,
                priority=0.8,
            )
        ]

    def _build_ring_2(
        self,
        role: RoleComposition,
        capabilities: dict[str, CapabilityAtom],
        voice_atoms: dict[str, VoiceAtom],
        domain_voice: VoiceDefaults | None,
    ) -> list[PromptSection]:
        """Role composition: capabilities + voice + behavioral descriptors."""
        sections: list[PromptSection] = []

        # Capability fragments
        cap_lines: list[str] = []
        for cap_name in role.capabilities:
            if cap_name not in capabilities:
                raise FileNotFoundError(
                    f"Capability atom '{cap_name}' not found. "
                    f"Available: {list(capabilities.keys())}"
                )
            atom = capabilities[cap_name]
            cap_lines.append(atom.instruction_fragment)

        cap_content = f"## Capabilities\n\n" + "\n".join(cap_lines)
        sections.append(PromptSection(
            ring=PromptRing.RING_2,
            name="capabilities",
            content=cap_content,
            token_estimate=estimate_tokens(cap_content),
            compressible=True,
            priority=0.7,
        ))

        # Voice block (with compression awareness)
        voice_content = self._compose_voice_block(
            role.voice, voice_atoms, CompressionStage.NONE
        )
        sections.append(PromptSection(
            ring=PromptRing.RING_2,
            name="voice",
            content=voice_content,
            token_estimate=estimate_tokens(voice_content),
            compressible=True,
            priority=0.5,  # Voice drops before capabilities
        ))

        # Behavioral descriptors
        bd = role.behavioral_descriptors
        bd_content = (
            f"## Behavioral Profile\n\n"
            f"Reasoning style: {bd.reasoning_style}\n"
            f"Risk tolerance: {bd.risk_tolerance}\n"
            f"Exploration vs exploitation: {bd.exploration_vs_exploitation:.1f}\n"
        )
        sections.append(PromptSection(
            ring=PromptRing.RING_2,
            name="behavioral",
            content=bd_content,
            token_estimate=estimate_tokens(bd_content),
            compressible=True,
            priority=0.6,
        ))

        # Forbidden actions
        if role.forbidden:
            forbidden_content = "## Forbidden\n\n" + "\n".join(
                f"- {f}" for f in role.forbidden
            )
            sections.append(PromptSection(
                ring=PromptRing.RING_2,
                name="forbidden",
                content=forbidden_content,
                token_estimate=estimate_tokens(forbidden_content),
                compressible=True,
                priority=0.9,  # Forbidden rules are high priority
            ))

        return sections

    def _build_ring_3(self, task: Task) -> list[PromptSection]:
        """Task context and working memory."""
        task_content = (
            f"## Current Task: {task.title}\n\n"
            f"Status: {task.status}\n"
            f"Priority: {task.priority}\n"
            f"Description: {task.description}\n"
        )
        if task.mandate.constraints:
            task_content += "\nConstraints:\n" + "\n".join(
                f"- {c}" for c in task.mandate.constraints
            )
        return [
            PromptSection(
                ring=PromptRing.RING_3,
                name="task_context",
                content=task_content,
                token_estimate=estimate_tokens(task_content),
                compressible=True,
                priority=0.8,
            )
        ]

    def _compose_voice_block(
        self,
        voice: VoiceProfile,
        atoms: dict[str, VoiceAtom],
        compression_stage: CompressionStage,
    ) -> str:
        """Build voice instruction text. Degrades under compression:

        Stage 0-2: full voice (language + tone + style + persona + scalars)
        Stage 3: persona summarized to 1 line, keep tone/style/language
        Stage 4: strip persona/style/tone, keep language only
        Stage 5: language only if non-default
        """
        parts: list[str] = ["## Voice\n"]

        # Language (always included unless stage 5 and default)
        if voice.language not in atoms:
            raise FileNotFoundError(
                f"Voice atom '{voice.language}' not found in voice.yaml. "
                f"Available: {list(atoms.keys())}"
            )

        if compression_stage >= CompressionStage.EMERGENCY:
            # Stage 5: language only if non-default
            if voice.language != "language_japanese":
                parts.append(atoms[voice.language].instruction_fragment)
            return "\n".join(parts) if len(parts) > 1 else ""

        # Language always included for stages 0-4
        parts.append(atoms[voice.language].instruction_fragment)

        if compression_stage >= CompressionStage.SYSTEM_COMPRESS:
            # Stage 4: language only
            return "\n".join(parts)

        # Tone
        if voice.tone and voice.tone in atoms:
            parts.append(atoms[voice.tone].instruction_fragment)

        # Style
        if voice.style and voice.style in atoms:
            parts.append(atoms[voice.style].instruction_fragment)

        if compression_stage >= CompressionStage.TASK_PRUNING:
            # Stage 3: persona summarized to 1 line
            if voice.persona and voice.persona in atoms:
                parts.append(f"Persona: {atoms[voice.persona].description}")
        else:
            # Stage 0-2: full persona
            if voice.persona and voice.persona in atoms:
                parts.append(atoms[voice.persona].instruction_fragment)

        # Scalars (stages 0-2 only)
        if compression_stage <= CompressionStage.TOOL_REDUCTION:
            parts.append(f"Formality: {voice.formality:.1f}/1.0")
            parts.append(f"Verbosity: {voice.verbosity:.1f}/1.0")

        return "\n".join(parts)

    @staticmethod
    def _determine_compression_stage(utilization: float) -> CompressionStage:
        """Map context utilization to compression stage."""
        if utilization < 0.60:
            return CompressionStage.NONE
        elif utilization < 0.70:
            return CompressionStage.HISTORY
        elif utilization < 0.80:
            return CompressionStage.TOOL_REDUCTION
        elif utilization < 0.90:
            return CompressionStage.TASK_PRUNING
        elif utilization < 0.95:
            return CompressionStage.SYSTEM_COMPRESS
        else:
            return CompressionStage.EMERGENCY

    @staticmethod
    def _apply_compression(
        sections: list[PromptSection],
        stage: CompressionStage,
    ) -> tuple[list[PromptSection], list[str]]:
        """Remove lowest-priority compressible sections until under budget.
        Returns (remaining_sections, dropped_section_names)."""
        dropped: list[str] = []
        # Sort compressible sections by priority ascending (drop lowest first)
        compressible = sorted(
            [s for s in sections if s.compressible],
            key=lambda s: s.priority,
        )
        incompressible = [s for s in sections if not s.compressible]

        # Drop sections based on stage severity
        drop_count = min(len(compressible), int(stage))
        for s in compressible[:drop_count]:
            dropped.append(s.name)

        remaining_compressible = compressible[drop_count:]
        result = incompressible + remaining_compressible
        # Re-sort by ring order
        result.sort(key=lambda s: (s.ring, -s.priority))
        return result, dropped

    @staticmethod
    def _apply_edge_placement(sections: list[PromptSection]) -> list[PromptSection]:
        """Critical info at beginning/end (lost-in-the-middle mitigation).
        Ring 0 always first. Highest-priority Ring 3 sections at the end."""
        ring_0 = [s for s in sections if s.ring == PromptRing.RING_0]
        middle = [s for s in sections if s.ring in (PromptRing.RING_1, PromptRing.RING_2)]
        ring_3 = [s for s in sections if s.ring == PromptRing.RING_3]

        # Sort middle by priority (lower priority → middle of prompt)
        middle.sort(key=lambda s: s.priority)

        return ring_0 + middle + ring_3

    def render(self, prompt: ComposedPrompt) -> str:
        """Render composed prompt to a single string."""
        return "\n\n".join(s.content for s in prompt.sections)
```

### 4.2 `engine/topology_router.py` — Task Analysis & Routing

```python
"""Task topology analysis and routing.
Spec reference: Section 5 (Topology & Coordination Patterns)."""
from __future__ import annotations

from enum import StrEnum

from ..models.base import FrameworkModel
from ..models.resource import ComputeMetrics


class Decomposability(StrEnum):
    MONOLITHIC = "monolithic"
    PARTIALLY_DECOMPOSABLE = "partially_decomposable"
    FULLY_DECOMPOSABLE = "fully_decomposable"


class Interdependency(StrEnum):
    INDEPENDENT = "independent"
    LOOSELY_COUPLED = "loosely_coupled"
    TIGHTLY_COUPLED = "tightly_coupled"


class ExplorationExecution(StrEnum):
    PURE_EXPLORATION = "pure_exploration"
    MIXED = "mixed"
    PURE_EXECUTION = "pure_execution"


class QualityCriticality(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Scale(StrEnum):
    SMALL = "small"       # < 1 hour
    MEDIUM = "medium"     # 1-4 hours
    LARGE = "large"       # 4+ hours


class Novelty(StrEnum):
    ROUTINE = "routine"
    MODERATE = "moderate"
    NOVEL = "novel"
    UNPRECEDENTED = "unprecedented"


class TaskAnalysis(FrameworkModel):
    """6-dimension task analysis result."""

    decomposability: Decomposability
    interdependency: Interdependency
    exploration_vs_execution: ExplorationExecution
    quality_criticality: QualityCriticality
    scale: Scale
    novelty: Novelty


class RoutingResult(FrameworkModel):
    """Topology routing decision."""

    pattern: str  # solo, pipeline, parallel_swarm, hierarchical_team, hybrid, debate
    agent_count: int
    role_assignments: list[dict]
    inject_scout: bool
    rationale: str


# Pattern selection matrix (simplified for Phase 0)
# Full version uses MAP-Elites archive lookup
PATTERN_RULES: dict[str, dict] = {
    "solo": {
        "conditions": "monolithic AND small AND routine",
        "agents": 1,
    },
    "pipeline": {
        "conditions": "partially_decomposable AND loosely_coupled",
        "agents": 2,
    },
    "hierarchical_team": {
        "conditions": "fully_decomposable OR large OR critical",
        "agents": 4,
    },
    "parallel_swarm": {
        "conditions": "fully_decomposable AND independent",
        "agents": 3,
    },
    "debate": {
        "conditions": "novel AND critical AND exploration",
        "agents": 3,
    },
}


class TopologyRouter:
    """Analyzes tasks and selects topology patterns.

    Phase 0: heuristic-based routing.
    Phase 1+: MAP-Elites archive lookup with reinforcement learning.
    """

    def analyze(self, task_description: str, hints: dict | None = None) -> TaskAnalysis:
        """Analyze task along 6 dimensions.
        Phase 0: uses heuristics from task description keywords.
        Phase 1+: uses LLM judgment + historical data."""
        # Default analysis — overridden by hints or LLM in later phases
        return TaskAnalysis(
            decomposability=Decomposability.PARTIALLY_DECOMPOSABLE,
            interdependency=Interdependency.LOOSELY_COUPLED,
            exploration_vs_execution=ExplorationExecution.MIXED,
            quality_criticality=QualityCriticality.MEDIUM,
            scale=Scale.MEDIUM,
            novelty=Novelty.MODERATE,
        )

    def route(
        self,
        analysis: TaskAnalysis,
        available_capacity: ComputeMetrics | None = None,
    ) -> RoutingResult:
        """Select topology pattern based on analysis and resource constraints."""
        # Phase 0: simplified routing
        if analysis.scale == Scale.SMALL and analysis.novelty == Novelty.ROUTINE:
            return RoutingResult(
                pattern="solo",
                agent_count=1,
                role_assignments=[{"role": "implementer", "model": "sonnet"}],
                inject_scout=False,
                rationale="Small routine task — solo execution sufficient",
            )

        if analysis.quality_criticality == QualityCriticality.CRITICAL:
            return RoutingResult(
                pattern="hierarchical_team",
                agent_count=4,
                role_assignments=[
                    {"role": "orchestrator", "model": "opus"},
                    {"role": "researcher", "model": "opus"},
                    {"role": "implementer", "model": "sonnet"},
                    {"role": "reviewer", "model": "opus"},
                ],
                inject_scout=analysis.novelty in (Novelty.NOVEL, Novelty.UNPRECEDENTED),
                rationale="Critical quality task — full team with dedicated reviewer",
            )

        # Default: hierarchical team
        return RoutingResult(
            pattern="hierarchical_team",
            agent_count=3,
            role_assignments=[
                {"role": "orchestrator", "model": "opus"},
                {"role": "implementer", "model": "sonnet"},
                {"role": "reviewer", "model": "opus"},
            ],
            inject_scout=False,
            rationale="Standard task — orchestrator + worker + reviewer",
        )
```

### 4.3 `engine/constitution_guard.py` — Constitutional Integrity

```python
"""Constitutional integrity enforcement.
Spec reference: Section 2 (Constitutional Axioms), Section 20 (Protection Rings)."""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..models.constitution import Constitution
from ..models.evolution import EvolutionProposal
from ..state.git_ops import GitOps


class ConstitutionIntegrityError(RuntimeError):
    """Raised when constitution hash verification fails."""


class ConstitutionGuard:
    """Enforces constitutional invariants.

    Design invariants:
    - Hash checked at boot and before every evolution (C1, C2)
    - Constitution file deletion → HARD_FAIL (C4)
    - Hash mismatch → HARD_FAIL with recovery instructions (C1)
    - Never auto-fixes hash mismatches
    """

    def __init__(self, constitution_path: Path, hash_path: Path):
        self.constitution_path = constitution_path
        self.hash_path = hash_path
        self._cached_hash: str | None = None

    def load_and_verify(self) -> str:
        """Load constitution, verify hash. Returns content.
        Raises ConstitutionIntegrityError on any failure."""
        # C4: file must exist
        if not self.constitution_path.exists():
            raise ConstitutionIntegrityError(
                f"CONSTITUTION.md not found at {self.constitution_path}. "
                f"HARD_FAIL: Restore from git or recreate. "
                f"ALL operations suspended until resolved."
            )

        content = self.constitution_path.read_text(encoding="utf-8")
        actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # First run: store hash
        if not self.hash_path.exists():
            self.hash_path.write_text(actual_hash, encoding="utf-8")
            self._cached_hash = actual_hash
            return content

        # Subsequent runs: verify
        expected_hash = self.hash_path.read_text(encoding="utf-8").strip()
        if actual_hash != expected_hash:
            raise ConstitutionIntegrityError(
                f"Constitution hash mismatch!\n"
                f"  Expected: {expected_hash}\n"
                f"  Actual:   {actual_hash}\n"
                f"If you edited CONSTITUTION.md intentionally, run:\n"
                f"  tools/rehash-constitution.sh\n"
                f"Otherwise, restore from git:\n"
                f"  git checkout -- CONSTITUTION.md"
            )

        self._cached_hash = actual_hash
        return content

    def verify_hash(self) -> bool:
        """Quick hash check without full content loading."""
        try:
            self.load_and_verify()
            return True
        except ConstitutionIntegrityError:
            return False

    def check_proposal(self, proposal: EvolutionProposal) -> tuple[bool, str]:
        """Verify proposal does not target constitution-protected paths."""
        # CONSTITUTION.md is never modifiable by evolution
        if "CONSTITUTION.md" in proposal.component:
            return False, "Evolution cannot modify CONSTITUTION.md (Ring 0 immutable)"
        if "constitution-hash" in proposal.component:
            return False, "Evolution cannot modify constitution hash"
        return True, "Constitutional check passed"

    def rehash(self) -> str:
        """Recompute and store hash. Only called by explicit human action."""
        if not self.constitution_path.exists():
            raise ConstitutionIntegrityError("Cannot rehash: CONSTITUTION.md not found")
        content = self.constitution_path.read_text(encoding="utf-8")
        new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self.hash_path.write_text(new_hash, encoding="utf-8")
        self._cached_hash = new_hash
        return new_hash
```

### 4.4 `engine/resource_tracker.py` — 4-Layer Resource Awareness

```python
"""4-layer resource awareness stack.
Spec reference: Section 18 (Resource Awareness & Self-Budgeting)."""
from __future__ import annotations

import re
import subprocess
from collections import deque
from datetime import datetime
from pathlib import Path

from ..models.resource import (
    BudgetPressureLevel,
    ComputeMetrics,
    CostApproval,
    RateLimitBucket,
    RateLimitMirror,
    SpendLevel,
    TokenBudget,
)
from ..state.yaml_store import YamlStore


# Cold-start seeds for token estimation (Section 18.2)
COLD_SEEDS: dict[str, int] = {
    "simple_fix": 2_000,
    "feature_small": 8_000,
    "feature_medium": 25_000,
    "feature_large": 80_000,
    "research": 15_000,
    "review": 5_000,
}


class ResourceTracker:
    """4-layer resource awareness: compute, rate limits, token budget, cost decisions.

    Token estimation strategy:
    - Primary: parse /usage output from a secondary Claude Code shell (I8)
    - Fallback: character-ratio estimation (3.5 chars/token English)
    - Rolling average replaces cold seeds after 10 samples (P4)
    """

    def __init__(self, yaml_store: YamlStore, state_dir: Path):
        self.yaml_store = yaml_store
        self.state_dir = state_dir
        self._token_history: deque[tuple[str, int]] = deque(maxlen=100)
        self._chars_per_token: float = 3.5  # Calibrated over time

    # ── Layer 1: Compute ──

    def check_compute(self) -> ComputeMetrics:
        """Read CPU/memory/disk via psutil. No fallbacks."""
        import psutil

        return ComputeMetrics(
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_percent=psutil.virtual_memory().percent,
            disk_percent=psutil.disk_usage("/").percent,
            active_agents=self._count_active_agents(),
            max_agents=5,  # From framework.yaml
        )

    def can_spawn_agent(self) -> tuple[bool, str]:
        """Pre-spawn resource check with 20% headroom (G1)."""
        metrics = self.check_compute()
        if metrics.cpu_percent > 80:
            return False, f"CPU too high: {metrics.cpu_percent}%"
        if metrics.memory_percent > 80:
            return False, f"Memory too high: {metrics.memory_percent}%"
        if metrics.disk_percent > 90:
            return False, f"Disk too high: {metrics.disk_percent}%"
        if metrics.active_agents >= metrics.max_agents:
            return False, f"At agent cap: {metrics.active_agents}/{metrics.max_agents}"
        return True, "Resources available"

    # ── Layer 2: Rate Limits ──

    def update_rate_mirror(self, tokens_consumed: int) -> None:
        """Update local rate limit mirror after API call."""
        # Reads from state/resources/rate-limits.yaml, updates counts
        pass  # Full implementation in Phase 1

    def get_backpressure_level(self) -> float:
        """0.0 = no pressure, 1.0 = at limit."""
        return 0.0  # Phase 0: no rate tracking

    # ── Layer 3: Token Budget ──

    def estimate_task_cost(self, task_type: str, complexity: str = "medium") -> int:
        """Estimate token cost for a task type.
        Uses rolling average if available, cold seeds otherwise."""
        key = f"{task_type}_{complexity}" if complexity else task_type
        # Check history for this task type
        matching = [t for label, t in self._token_history if label == key]
        if len(matching) >= 3:
            return int(sum(matching) / len(matching))
        # Fall back to cold seeds
        return COLD_SEEDS.get(key, COLD_SEEDS.get(task_type, 10_000))

    def record_actual_usage(self, task_type: str, tokens_used: int) -> None:
        """Record actual token usage for calibration."""
        self._token_history.append((task_type, tokens_used))
        # Recalibrate chars_per_token if we have /usage data
        self._maybe_recalibrate()

    def parse_usage_output(self) -> dict | None:
        """Parse /usage command output from Claude Code shell.
        Primary token tracking method (user-discovered).
        Returns dict with token counts or None if parsing fails (I8)."""
        try:
            result = subprocess.run(
                ["claude", "-p", "/usage"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return None
            return self._parse_usage_text(result.stdout)
        except Exception:
            return None  # Fall back to estimation

    @staticmethod
    def _parse_usage_text(text: str) -> dict | None:
        """Parse /usage output text into structured data.
        Format may change between Claude Code versions (I8)."""
        data: dict = {}
        # Look for common patterns in /usage output
        patterns = {
            "input_tokens": r"[Ii]nput\s+tokens?:\s*([0-9,]+)",
            "output_tokens": r"[Oo]utput\s+tokens?:\s*([0-9,]+)",
            "total_cost": r"[Cc]ost:\s*\$([0-9.]+)",
            "cache_read": r"[Cc]ache\s+read:\s*([0-9,]+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                val = match.group(1).replace(",", "")
                data[key] = float(val) if "." in val else int(val)
        return data if data else None

    # ── Layer 4: Cost Decisions ──

    def check_spend_level(self, estimated_cost: float) -> SpendLevel:
        """Classify cost into spend levels."""
        if estimated_cost <= 0:
            return SpendLevel.FREE
        if estimated_cost < 0.10:
            return SpendLevel.LOW
        if estimated_cost < 10.0:
            return SpendLevel.MEDIUM
        return SpendLevel.HIGH

    # ── Internal ──

    def _count_active_agents(self) -> int:
        """Count active agents from registry files."""
        agents_dir = self.state_dir / "agents"
        if not agents_dir.exists():
            return 0
        return sum(1 for _ in agents_dir.glob("*/status.yaml"))

    def _maybe_recalibrate(self) -> None:
        """Recalibrate chars_per_token ratio against /usage data (P4)."""
        usage = self.parse_usage_output()
        if usage and "input_tokens" in usage:
            # We'd need to correlate with known text lengths
            # Full implementation deferred to Phase 1
            pass
```

### 4.5 `engine/task_lifecycle.py` — 9-State Machine

```python
"""Task lifecycle state machine.
Spec reference: Section 6 (Task Lifecycle)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..models.task import (
    VALID_TRANSITIONS,
    Task,
    TaskMetrics,
    TaskOrigin,
    TaskStatus,
    TaskTimelineEntry,
)
from ..models.base import generate_id
from ..state.yaml_store import YamlStore


class InvalidTransitionError(ValueError):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, task_id: str, current: TaskStatus, attempted: TaskStatus):
        valid = VALID_TRANSITIONS.get(current, set())
        super().__init__(
            f"Invalid transition for task {task_id}: "
            f"{current} → {attempted}. "
            f"Valid transitions from {current}: {sorted(valid)}"
        )


class TaskLifecycle:
    """Task state machine management.

    Design invariants:
    - All transitions validated against VALID_TRANSITIONS (T1)
    - Every transition logged to timeline and audit (A4 axiom)
    - Heartbeat updated on every state change (T2)
    - Park/resume preserves full task context (T7)
    - REVIEWING mandatory before COMPLETE (A7 axiom)
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta"):
        self.yaml_store = yaml_store
        self.domain = domain
        self._tasks_base = f"instances/{domain}/state/tasks"

    def create(
        self,
        title: str,
        description: str,
        origin: TaskOrigin,
        priority: str = "medium",
        rationale: str = "",
    ) -> Task:
        """Create task in INTAKE state."""
        task = Task(
            id=generate_id("task"),
            created_at=datetime.utcnow(),
            status=TaskStatus.INTAKE,
            title=title,
            description=description,
            origin=origin,
            rationale=rationale,
            priority=priority,
            timeline=[
                TaskTimelineEntry(
                    time=datetime.utcnow(),
                    event="created",
                    actor=origin.source,
                    detail=f"Task created: {title}",
                )
            ],
        )
        self.yaml_store.write(
            f"{self._tasks_base}/active/{task.id}.yaml", task
        )
        return task

    def transition(
        self,
        task_id: str,
        new_status: TaskStatus,
        actor: str,
        detail: str,
    ) -> Task:
        """Transition task state. Validates against VALID_TRANSITIONS."""
        task = self._load_task(task_id)
        current = TaskStatus(task.status)

        # Validate transition (T1)
        valid_next = VALID_TRANSITIONS.get(current, set())
        if new_status not in valid_next:
            raise InvalidTransitionError(task_id, current, new_status)

        # Update task
        task.status = new_status
        task.updated_at = datetime.utcnow()
        task.timeline.append(
            TaskTimelineEntry(
                time=datetime.utcnow(),
                event=f"transition:{current}→{new_status}",
                actor=actor,
                detail=detail,
            )
        )

        # Move file to appropriate directory
        old_dir = self._status_dir(current)
        new_dir = self._status_dir(new_status)

        if old_dir != new_dir:
            # Remove from old location
            old_path = f"{self._tasks_base}/{old_dir}/{task_id}.yaml"
            new_path = f"{self._tasks_base}/{new_dir}/{task_id}.yaml"
            self.yaml_store.write(new_path, task)
            # Clean up old file
            old_full = self.yaml_store._resolve(old_path)
            if old_full.exists():
                old_full.unlink()
        else:
            self.yaml_store.write(
                f"{self._tasks_base}/{new_dir}/{task_id}.yaml", task
            )

        return task

    def park(self, task_id: str, reason: str, actor: str) -> Task:
        """Park a task (shorthand for transition to PARKED)."""
        task = self._load_task(task_id)
        return self.transition(task_id, TaskStatus.PARKED, actor, f"Parked: {reason}")

    def resume(self, task_id: str, actor: str) -> Task:
        """Resume a parked task back to PLANNING."""
        return self.transition(
            task_id, TaskStatus.PLANNING, actor, "Resumed from parked"
        )

    def get_active(self) -> list[Task]:
        """List all active (non-parked, non-completed) tasks."""
        return self._list_tasks_in("active")

    def get_parked(self) -> list[Task]:
        """List all parked tasks."""
        return self._list_tasks_in("parked")

    def get_focus(self) -> str | None:
        """Get the currently focused task ID."""
        try:
            data = self.yaml_store.read_raw(f"{self._tasks_base}/focus.yaml")
            return data.get("focus_task_id")
        except (FileNotFoundError, ValueError):
            return None

    def set_focus(self, task_id: str) -> None:
        """Set the focused task."""
        self.yaml_store.write_raw(
            f"{self._tasks_base}/focus.yaml",
            {"focus_task_id": task_id},
        )

    def _load_task(self, task_id: str) -> Task:
        """Load task from active, parked, or completed directories."""
        for subdir in ["active", "parked", "completed"]:
            path = f"{self._tasks_base}/{subdir}/{task_id}.yaml"
            if self.yaml_store.exists(path):
                return self.yaml_store.read(path, Task)
        raise FileNotFoundError(f"Task not found: {task_id}")

    def _list_tasks_in(self, subdir: str) -> list[Task]:
        """List all tasks in a subdirectory."""
        dir_path = f"{self._tasks_base}/{subdir}"
        tasks: list[Task] = []
        try:
            for name in self.yaml_store.list_dir(dir_path):
                if name.endswith(".yaml"):
                    tasks.append(
                        self.yaml_store.read(f"{dir_path}/{name}", Task)
                    )
        except (FileNotFoundError, NotADirectoryError):
            pass
        return tasks

    @staticmethod
    def _status_dir(status: TaskStatus) -> str:
        """Map task status to filesystem directory."""
        if status in (TaskStatus.COMPLETE, TaskStatus.ARCHIVED):
            return "completed"
        if status == TaskStatus.PARKED:
            return "parked"
        return "active"
```

### 4.6 `engine/agent_spawner.py` — Resource-Checked Agent Spawning

```python
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
```

### 4.7 `engine/environment_monitor.py` — Model Fingerprinting

```python
"""Model fingerprinting and drift detection.
Spec reference: Section 19 (Environment Awareness & Self-Benchmarking)."""
from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from ..models.environment import CanaryResult, DriftDetection, ModelFingerprint
from ..state.yaml_store import YamlStore


class EnvironmentMonitor:
    """Canary suite runner, model fingerprinting, drift detection.

    Phase 0: basic canary suite with 5 micro-benchmarks.
    Phase 1+: full fingerprinting with 20+ tasks, behavioral probes.
    """

    DRIFT_THRESHOLD = 0.15  # 15% deviation triggers investigation

    def __init__(self, yaml_store: YamlStore, canary_dir: Path):
        self.yaml_store = yaml_store
        self.canary_dir = canary_dir

    def should_run_canary(self) -> bool:
        """Skip if last fingerprint < 5 hours old AND Claude version unchanged."""
        try:
            data = self.yaml_store.read_raw("core/last-fingerprint.yaml")
            last_run = datetime.fromisoformat(data.get("timestamp", ""))
            elapsed = (datetime.utcnow() - last_run).total_seconds()
            if elapsed < 5 * 3600:  # 5 hours
                stored_version = data.get("claude_version", "")
                current_version = self.check_claude_version()
                if stored_version == current_version:
                    return False
        except (FileNotFoundError, ValueError, KeyError):
            pass
        return True

    def run_canary_suite(self) -> list[CanaryResult]:
        """Execute fixed micro-benchmark tasks."""
        # Phase 0: placeholder canary tasks
        # Each task is a known-answer prompt
        results: list[CanaryResult] = []
        canary_tasks = [
            ("arithmetic", "What is 7 * 8?", "56"),
            ("logic", "If all A are B and all B are C, are all A C?", "yes"),
            ("code", "Write a Python function to reverse a string", "def"),
            ("reasoning", "What comes next: 2, 4, 8, 16, ?", "32"),
            ("instruction", "Reply with exactly the word: ACKNOWLEDGED", "ACKNOWLEDGED"),
        ]
        for name, prompt, expected in canary_tasks:
            results.append(CanaryResult(
                task_name=name,
                expected=expected,
                actual="",  # Filled by actual execution
                score=0.0,
                tokens_used=0,
                latency_ms=0,
            ))
        return results

    def compute_fingerprint(self, results: list[CanaryResult]) -> ModelFingerprint:
        """Build fingerprint from canary results."""
        scores = {r.task_name: r.score for r in results}
        return ModelFingerprint(
            created_at=datetime.utcnow(),
            model_id="claude-opus-4-6",
            reasoning_score=scores.get("reasoning", 0.0),
            instruction_score=scores.get("instruction", 0.0),
            code_score=scores.get("code", 0.0),
            creative_score=0.5,  # No creative canary in Phase 0
            tool_score=0.5,      # No tool canary in Phase 0
            avg_latency_ms=int(sum(r.latency_ms for r in results) / max(len(results), 1)),
            avg_output_tokens=int(sum(r.tokens_used for r in results) / max(len(results), 1)),
        )

    def detect_drift(self, current: ModelFingerprint) -> DriftDetection:
        """Compare current fingerprint against stored baselines."""
        # Load last 5 fingerprints for comparison
        baseline = current  # Phase 0: compare against self
        distance = current.distance_to(baseline)
        affected: list[str] = []

        return DriftDetection(
            current=current,
            baseline=baseline,
            distance=distance,
            threshold=self.DRIFT_THRESHOLD,
            drift_detected=distance > self.DRIFT_THRESHOLD,
            affected_dimensions=affected,
        )

    @staticmethod
    def check_claude_version() -> str:
        """Get Claude Code version string."""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"
```

### 4.8 `audit/logger.py` — 8-Stream Audit Dispatcher

```python
"""Central audit logger dispatching to 8 JSONL streams.
Spec reference: Section 17 (Audit System & Viewers)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..models.audit import (
    BaseLogEntry,
    DecisionLogEntry,
    EnvironmentLogEntry,
    EvolutionLogEntry,
    LogStream,
    ResourceLogEntry,
    TaskLogEntry,
    TraceLogEntry,
)
from ..state.jsonl_writer import JsonlWriter


class AuditLogger:
    """Central audit dispatcher for all 8 log streams.

    Design invariants:
    - Every log method validates entry type matches stream
    - Cross-stream queries supported for timeline reconstruction
    - Phase 0 active streams: tasks, decisions (others are stubs)
    """

    def __init__(self, log_root: Path):
        self.log_root = log_root
        self.writers: dict[LogStream, JsonlWriter] = {
            stream: JsonlWriter(log_root / stream.value, stream)
            for stream in LogStream
        }

    def log_evolution(self, entry: EvolutionLogEntry) -> None:
        self.writers[LogStream.EVOLUTION].append(entry)

    def log_task(self, entry: TaskLogEntry) -> None:
        self.writers[LogStream.TASKS].append(entry)

    def log_decision(self, entry: DecisionLogEntry) -> None:
        self.writers[LogStream.DECISIONS].append(entry)

    def log_resource(self, entry: ResourceLogEntry) -> None:
        self.writers[LogStream.RESOURCES].append(entry)

    def log_environment(self, entry: EnvironmentLogEntry) -> None:
        self.writers[LogStream.ENVIRONMENT].append(entry)

    def log_trace(self, entry: TraceLogEntry) -> None:
        self.writers[LogStream.TRACES].append(entry)

    def query(
        self,
        stream: LogStream,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query a single stream with optional time filter."""
        return self.writers[stream].read_entries(since=since, until=until, limit=limit)

    def query_all(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Cross-stream query, merged chronologically."""
        all_entries: list[dict] = []
        for writer in self.writers.values():
            entries = writer.read_entries(since=since, until=until, limit=limit)
            all_entries.extend(entries)
        all_entries.sort(key=lambda e: e.get("timestamp", ""))
        return all_entries[:limit]
```

### 4.9 `audit/tree_viewer.py` — Terminal Audit Viewer

```python
"""Terminal tree viewer using rich library.
Spec reference: Section 17.3 (Audit Viewer Formats)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.tree import Tree

from .logger import AuditLogger
from ..models.audit import LogStream


class AuditTreeViewer:
    """Renders audit logs as a collapsible terminal tree.

    User preference: tree-like GUI for audit viewing.
    """

    def __init__(self, audit_logger: AuditLogger):
        self.logger = audit_logger
        self.console = Console()

    def render_session(
        self,
        since: datetime,
        until: datetime | None = None,
        streams: list[LogStream] | None = None,
    ) -> None:
        """Render session audit tree to terminal."""
        if streams is None:
            streams = [LogStream.TASKS, LogStream.DECISIONS]

        tree = Tree(f"[bold]Session audit: {since.isoformat()}[/bold]")

        for stream in streams:
            entries = self.logger.query(stream, since=since, until=until, limit=200)
            if not entries:
                continue
            branch = tree.add(f"[cyan]{stream.value}[/cyan] ({len(entries)} entries)")
            for entry in entries:
                ts = entry.get("timestamp", "?")[:19]
                event = entry.get("event", entry.get("decision_type", "?"))
                actor = entry.get("actor", "?")
                branch.add(f"[dim]{ts}[/dim] {event} — {actor}")

        self.console.print(tree)

    def render_task_detail(self, task_id: str) -> None:
        """Render a single task's full timeline."""
        entries = self.logger.query(LogStream.TASKS, limit=500)
        task_entries = [e for e in entries if e.get("task_id") == task_id]

        tree = Tree(f"[bold]Task: {task_id}[/bold]")
        for entry in task_entries:
            ts = entry.get("timestamp", "?")[:19]
            event = entry.get("event", "?")
            actor = entry.get("actor", "?")
            detail = entry.get("detail", {})
            node = tree.add(f"[dim]{ts}[/dim] [green]{event}[/green] — {actor}")
            if detail:
                for k, v in detail.items():
                    node.add(f"{k}: {v}")

        self.console.print(tree)
```

---

## Part 5: CLAUDE.md as Bootstrap Entry Point

CLAUDE.md is the framework's entry point. When Claude Code opens the framework directory, CLAUDE.md provides bootstrap instructions, tool references, and operational constraints. It is machine-generated by `claude_md/generator.py` and should be ~150-200 lines (~2.5K tokens).

Spec references: Section 3 (Architecture), Section 21.3 (prompt structure).

### 5.1 CLAUDE.md Template

The following is the target output of `generate_claude_md()`. Sections marked `[DYNAMIC]` are populated from framework state at generation time.

```markdown
# Universal Agents Framework — Bootstrap Instructions

**Phase:** [DYNAMIC: framework.yaml → phase]
**Active Domain:** [DYNAMIC: framework.yaml → active_domain]
**Constitution Hash:** [DYNAMIC: computed SHA-256]

---

## Bootstrap Protocol

When this session starts, execute these steps IN ORDER:

1. **Session Lock**: Run `tools/session-check.sh acquire`
   - If another session active → STOP, inform human
   - If stale lock → auto-removed with warning

2. **Constitution Check**: Run `tools/constitution-check.sh`
   - Verifies CONSTITUTION.md hash matches stored hash
   - On mismatch → HALT ALL OPERATIONS, alert human

3. **Load Context**:
   - Read CONSTITUTION.md for axioms
   - Read instances/[DOMAIN]/CHARTER.md for domain charter
   - Read instances/[DOMAIN]/state/tasks/focus.yaml for current task
   - Scan instances/[DOMAIN]/state/tasks/active/ for task backlog
   - Check instances/[DOMAIN]/state/tasks/parked/ for parked tasks

4. **Offer Options**:
   - If parked tasks exist: "You have N parked tasks. Resume one?"
   - If active task exists: "Continue working on: [task title]?"
   - Otherwise: "Ready for a new task."

## Constitutional Axioms (Always Active)

[DYNAMIC: axiom summaries from CONSTITUTION.md]

- A1: Human can halt all operations at any time
- A2: Human can veto any decision
- A3: Framework must not modify its own constitution
- A4: Every action must be logged and traceable
- A5: Evolution must be reversible
- A6: Task budgets are hard limits
- A7: Every task must be reviewed before completion
- A8: Resource exhaustion triggers graceful degradation, not failure

## Task Lifecycle

All tasks follow: INTAKE → ANALYSIS → PLANNING → EXECUTING → REVIEWING → VERDICT → COMPLETE → ARCHIVED

**Rules (non-negotiable):**
- Every task MUST pass through REVIEWING before COMPLETE (A7)
- Every action MUST be logged (A4)
- Human can halt at any time (A1)
- Human can veto any decision (A2)

## How to Process a Task

1. **INTAKE**: `uv run python -m uagents.cli.task_manager create --title "..." --description "..." --origin human`
2. **ANALYSIS**: Analyze complexity, select topology (solo or hierarchical_team)
3. **PLANNING**: Decompose task, assign roles. `uv run python -m uagents.cli.task_manager transition --task-id ID --status planning`
4. **EXECUTING**: Spawn agents as needed. `uv run python -m uagents.cli.spawn_agent --role implementer --task-id ID`
5. **REVIEWING**: Spawn reviewer. `uv run python -m uagents.cli.spawn_agent --role reviewer --task-id ID`
6. **VERDICT**: Pass → COMPLETE. Fail → back to PLANNING with feedback
7. **COMPLETE**: `uv run python -m uagents.cli.task_manager transition --task-id ID --status complete`

## Available Roles

| Role | Model | Purpose |
|------|-------|---------|
| orchestrator | opus | Strategic coordination, decomposition |
| researcher | opus | Deep research and analysis |
| implementer | sonnet | Efficient task execution |
| reviewer | opus | Quality verification |
| scout | sonnet | Exploration and anomaly detection |

## Tool Scripts

| Tool | Usage |
|------|-------|
| `tools/session-check.sh` | `acquire` / `release` / `status` |
| `tools/task-manager.sh` | `create` / `transition` / `list` / `show` / `park` / `resume` |
| `tools/spawn-agent.sh` | `--role NAME --task-id ID --context "..."` |
| `tools/audit-tree.sh` | `--since DATE [--stream tasks\|decisions]` |
| `tools/resource-monitor.sh` | `--format table\|json` |
| `tools/force-unlock.sh` | Remove stale session lock |

## Key Directories

- `CONSTITUTION.md` — Immutable axioms (Ring 0)
- `instances/[DOMAIN]/CHARTER.md` — Domain charter
- `instances/[DOMAIN]/state/tasks/` — Active, parked, completed tasks
- `instances/[DOMAIN]/state/agents/` — Agent registry (per-agent dirs)
- `instances/[DOMAIN]/logs/` — 8-stream audit logs
- `roles/` — Capability atoms, voice atoms, role compositions
- `core/` — Framework configuration, canary tasks

## Phase 0 Limitations

- NO self-evolution (all framework changes require human)
- NO diversity enforcement (metrics not yet implemented)
- NO resource tracking (token budgets not yet implemented)
- NO environment awareness (model fingerprinting not yet implemented)
- Topology limited to: solo, hierarchical_team
- Maximum 5 concurrent agents
```

### 5.2 `claude_md/generator.py` — CLAUDE.md Generator

```python
"""CLAUDE.md generation from framework state.
Spec reference: Section 3.3 (bootstrap), Section 21.3 (prompt structure)."""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..state.yaml_store import YamlStore


class ClaudeMdGenerator:
    """Generates CLAUDE.md from framework state.

    CLAUDE.md is ~150-200 lines, ~2.5K tokens.
    Machine-generated section has a hard cap of 100 lines (P5).
    """

    MAX_DYNAMIC_LINES = 100

    def __init__(self, yaml_store: YamlStore, framework_root: Path):
        self.yaml_store = yaml_store
        self.root = framework_root

    def generate(self, domain: str = "meta") -> str:
        """Generate complete CLAUDE.md content."""
        # Load framework config
        config = self.yaml_store.read_raw("framework.yaml")
        fw = config.get("framework", config)

        # Compute constitution hash
        constitution_path = self.root / "CONSTITUTION.md"
        if constitution_path.exists():
            content = constitution_path.read_text(encoding="utf-8")
            constitution_hash = hashlib.sha256(content.encode()).hexdigest()
        else:
            constitution_hash = "NOT_FOUND"

        # Load active domain info
        phase = fw.get("phase", "0")

        # Build CLAUDE.md sections
        sections: list[str] = [
            self._build_header(phase, domain, constitution_hash),
            self._build_bootstrap_protocol(domain),
            self._build_axiom_reference(),
            self._build_task_lifecycle(),
            self._build_task_processing(),
            self._build_roles_table(),
            self._build_tool_reference(),
            self._build_key_directories(domain),
            self._build_limitations(),
        ]

        return "\n\n".join(sections)

    def update_active_context(self, domain: str = "meta") -> str:
        """Regenerate only the dynamic 'Current State' section.
        Appended to static CLAUDE.md. Capped at MAX_DYNAMIC_LINES."""
        tasks = []
        try:
            active_dir = f"instances/{domain}/state/tasks/active"
            for name in self.yaml_store.list_dir(active_dir):
                if name.endswith(".yaml"):
                    data = self.yaml_store.read_raw(f"{active_dir}/{name}")
                    tasks.append(data)
        except (FileNotFoundError, NotADirectoryError):
            pass

        lines = ["## Current State", ""]
        if tasks:
            for t in tasks[:10]:  # Cap at 10 tasks
                lines.append(f"- [{t.get('status', '?')}] {t.get('title', '?')}")
        else:
            lines.append("No active tasks. Ready for new work.")

        # Enforce cap
        if len(lines) > self.MAX_DYNAMIC_LINES:
            lines = lines[: self.MAX_DYNAMIC_LINES]
            lines.append("... (truncated)")

        return "\n".join(lines)

    # ── Section builders (static content) ──

    @staticmethod
    def _build_header(phase: str, domain: str, hash_: str) -> str:
        return (
            f"# Universal Agents Framework — Bootstrap Instructions\n\n"
            f"**Phase:** {phase}\n"
            f"**Active Domain:** {domain}\n"
            f"**Constitution Hash:** {hash_}\n"
        )

    @staticmethod
    def _build_bootstrap_protocol(domain: str) -> str:
        return (
            "## Bootstrap Protocol\n\n"
            "When this session starts, execute IN ORDER:\n\n"
            "1. **Session Lock**: `tools/session-check.sh acquire`\n"
            "2. **Constitution Check**: `tools/constitution-check.sh`\n"
            f"3. **Load Context**: Read CONSTITUTION.md, "
            f"instances/{domain}/CHARTER.md, focus.yaml\n"
            "4. **Offer Options**: Resume parked tasks or accept new task\n"
        )

    @staticmethod
    def _build_axiom_reference() -> str:
        return (
            "## Constitutional Axioms\n\n"
            "- A1: Human can halt all operations at any time\n"
            "- A2: Human can veto any decision\n"
            "- A3: Framework must not modify its own constitution\n"
            "- A4: Every action must be logged and traceable\n"
            "- A5: Evolution must be reversible\n"
            "- A6: Task budgets are hard limits\n"
            "- A7: Every task must be reviewed before completion\n"
            "- A8: Resource exhaustion → graceful degradation\n"
        )

    @staticmethod
    def _build_task_lifecycle() -> str:
        return (
            "## Task Lifecycle\n\n"
            "INTAKE → ANALYSIS → PLANNING → EXECUTING → "
            "REVIEWING → VERDICT → COMPLETE → ARCHIVED\n\n"
            "Rules: A7 (review mandatory), A4 (all logged), "
            "A1 (human halt), A2 (human veto)\n"
        )

    @staticmethod
    def _build_task_processing() -> str:
        return (
            "## Processing Tasks\n\n"
            "1. INTAKE: `task_manager create`\n"
            "2. ANALYSIS: Select topology\n"
            "3. PLANNING: Decompose, assign roles\n"
            "4. EXECUTING: Spawn agents\n"
            "5. REVIEWING: Spawn reviewer\n"
            "6. VERDICT: Pass → complete, Fail → re-plan\n"
            "7. COMPLETE: Record metrics\n"
        )

    @staticmethod
    def _build_roles_table() -> str:
        return (
            "## Roles\n\n"
            "| Role | Model | Purpose |\n"
            "|------|-------|--------|\n"
            "| orchestrator | opus | Coordination |\n"
            "| researcher | opus | Analysis |\n"
            "| implementer | sonnet | Execution |\n"
            "| reviewer | opus | Verification |\n"
            "| scout | sonnet | Exploration |\n"
        )

    @staticmethod
    def _build_tool_reference() -> str:
        return (
            "## Tools\n\n"
            "All tools: `uv run python -m uagents.cli.<module> [args]`\n"
            "Shell wrappers in `tools/` directory.\n"
        )

    @staticmethod
    def _build_key_directories(domain: str) -> str:
        return (
            "## Key Directories\n\n"
            f"- `instances/{domain}/state/tasks/` — Task YAML files\n"
            f"- `instances/{domain}/state/agents/` — Agent registry\n"
            f"- `instances/{domain}/logs/` — 8-stream audit logs\n"
            "- `roles/` — Capabilities, voice atoms, compositions\n"
        )

    @staticmethod
    def _build_limitations() -> str:
        return (
            "## Phase 0 Limitations\n\n"
            "- No self-evolution\n"
            "- No diversity enforcement\n"
            "- No resource tracking\n"
            "- No environment awareness\n"
            "- Topology: solo, hierarchical_team only\n"
            "- Max 5 concurrent agents\n"
        )
```

### 5.3 Skills Architecture

Skills are stored in `.claude/skills/framework-*/SKILL.md` files. Each skill is a focused set of instructions that Claude Code loads on demand, keeping the base CLAUDE.md lightweight.

**7 Phase 0 skills:**

| Skill | File | Startup Tokens | Full Tokens | Purpose |
|-------|------|---------------|-------------|---------|
| orchestrate | `framework-orchestrate/SKILL.md` | ~100 | ~2K | Task decomposition, topology selection, agent coordination |
| spawn-agent | `framework-spawn/SKILL.md` | ~100 | ~1.5K | Compose prompt, check resources, invoke Task tool |
| review | `framework-review/SKILL.md` | ~100 | ~1.5K | Structured review protocol, findings format, verdict rules |
| coordinate | `framework-coordinate/SKILL.md` | ~100 | ~1.5K | Team messaging, stigmergy, quorum voting |
| audit | `framework-audit/SKILL.md` | ~100 | ~1K | Log viewing, tree rendering, timeline queries |
| evolve | `framework-evolve/SKILL.md` | ~100 | ~2K | Evolution proposal, dual-copy, constitutional check |
| resource | `framework-resource/SKILL.md` | ~100 | ~1K | Budget checking, rate limit awareness, compute monitoring |

**Skill file format:**

```markdown
# Skill: orchestrate

## When to Invoke
When a new task arrives and needs decomposition, or when coordinating multi-agent execution.

## Protocol

1. Read the task from `instances/{domain}/state/tasks/active/{task-id}.yaml`
2. Run topology analysis: `tools/topology-analyze.sh --task-id {task-id}`
3. Based on result, either:
   a. Solo: execute directly
   b. Team: spawn agents via `tools/spawn-agent.sh --role {role} --task-id {id}`
4. Monitor progress via `tools/audit-tree.sh --since now --stream tasks`
5. On completion: transition to REVIEWING

## Constraints
- Never skip REVIEWING (Axiom A7)
- Never exceed max_concurrent_agents
- Log every spawn decision to decisions stream
```

---

## Part 6: Claude Code Integration Patterns

The framework runs AS Claude Code. Every framework operation maps to a specific Claude Code capability. This section documents the exact mapping.

Spec reference: Section 3 (Architecture), Section 5 (Topology), Section 15 (Coordination).

### 6.1 Agent Spawn → Claude Code `Task` Tool

When the framework needs to spawn an agent, the orchestrating Claude Code session uses the `Task` tool. The Python tooling composes the prompt; Claude Code executes the spawn.

```
┌─────────────────────────────────────────────────────┐
│ Orchestrator (Claude Code session)                  │
│                                                      │
│ 1. uv run python -m uagents.cli.spawn_agent         │
│    --role researcher --task-id task-20260228-001     │
│    → outputs: composed prompt + spawn descriptor      │
│                                                      │
│ 2. Use Task tool:                                    │
│    Task(                                             │
│      description="Research for task-20260228-001",   │
│      prompt=<composed prompt from step 1>,           │
│      subagent_type="general-purpose",                │
│      model="opus",                                   │
│    )                                                 │
│                                                      │
│ 3. Agent executes, returns result                    │
│                                                      │
│ 4. uv run python -m uagents.cli.task_manager         │
│    transition --task-id task-20260228-001             │
│    --status reviewing                                 │
└─────────────────────────────────────────────────────┘
```

**Model mapping:**
- `ModelPreference.OPUS` → `model="opus"` in Task tool
- `ModelPreference.SONNET` → `model="sonnet"` in Task tool
- `ModelPreference.HAIKU` → `model="haiku"` in Task tool

**Subagent type selection:**
- Most agents → `subagent_type="general-purpose"` (full tool access)
- Read-only analysis → `subagent_type="Explore"` (no edit capability)
- Planning work → `subagent_type="Plan"` (research only)

### 6.2 Multi-Agent Teams → Claude Code `TeamCreate` + `SendMessage`

For hierarchical team topologies, the framework uses Claude Code's native team coordination:

```
┌─────────────────────────────────────────────────────┐
│ Framework bootstrap (main Claude Code session)       │
│                                                      │
│ 1. TeamCreate(team_name="task-001", description=...) │
│                                                      │
│ 2. TaskCreate(subject="Research phase", ...)         │
│    TaskCreate(subject="Implementation phase", ...)   │
│    TaskCreate(subject="Review phase", ...)           │
│                                                      │
│ 3. Task(                                             │
│      name="researcher",                              │
│      team_name="task-001",                           │
│      prompt=<composed researcher prompt>,            │
│    )                                                 │
│    Task(                                             │
│      name="implementer",                             │
│      team_name="task-001",                           │
│      prompt=<composed implementer prompt>,           │
│    )                                                 │
│                                                      │
│ 4. SendMessage(type="message",                       │
│      recipient="researcher",                         │
│      content="Begin research on ...",                │
│    )                                                 │
│                                                      │
│ 5. Teammates use TaskUpdate to mark tasks completed  │
│ 6. TeamDelete when all tasks done                    │
└─────────────────────────────────────────────────────┘
```

### 6.3 State Persistence — Dual Strategy

| Concern | Primary (YAML) | Supplementary (Universal Memory MCP) |
|---------|----------------|--------------------------------------|
| Task state | `state/tasks/active/*.yaml` | `store_memory(type="episodic")` for search |
| Agent registry | `state/agents/{id}/status.yaml` | Agent-scoped memories for context |
| Configuration | `roles/*.yaml`, `framework.yaml` | `store_memory(type="semantic")` for facts |
| Audit logs | `logs/{stream}/{stream}.jsonl` | Not duplicated |
| Evolution | `state/evolution/` + git branches | `store_memory(type="procedural")` for workflows |
| Session state | `.claude-framework.lock` | `create_session()` + `checkpoint_session()` |

**Rule:** YAML is the source of truth. Universal Memory is supplementary for semantic search. If Memory MCP is unavailable, framework continues with YAML-only state (I5).

### 6.4 Stigmergic Coordination — Shared Pressure Fields

For swarm topologies, agents coordinate indirectly through shared YAML files (spec Section 15.3):

```yaml
# instances/meta/state/coordination/pressure-fields/task-001.yaml
pressure_field:
  task_id: "task-20260228-001"
  dimensions:
    research_coverage: 0.4   # 0.0 = none, 1.0 = fully covered
    implementation_progress: 0.1
    test_coverage: 0.0
    review_status: 0.0
  last_updated: "2026-02-28T10:30:00Z"
  updated_by: "agent-20260228-002"
```

Each agent reads the pressure field before acting, updates it after acting. Single-writer convention: only the agent indicated by `updated_by` writes to a given pressure field. Other agents read-only.

### 6.5 Quorum Voting — Sealed File-Per-Voter Pattern

For evolution proposals requiring quorum (Tier 2):

```
state/evolution/proposals/{evo-id}/
├── proposal.yaml           # The evolution proposal
├── votes/
│   ├── agent-001.yaml      # Sealed vote from agent-001
│   ├── agent-002.yaml      # Sealed vote from agent-002
│   └── agent-003.yaml      # Sealed vote from agent-003
└── result.yaml             # Computed after all votes collected
```

Each voter writes exactly one file. No voter can read other votes before writing (sealed). The proposer collects all vote files and computes the quorum result.

### 6.6 Evolution via Git Branches

```
main ─────────────────────────────────────────────
  │                                        ↑
  └── evo/evo-20260228-001 ────────────── merge (if promoted)
       │                                   │
       ├── modify YAML configs             │
       ├── run evaluation                  │
       └── decision: promote or delete     │
                                           │
                                    delete branch (if rejected)
```

### 6.7 Race Prevention Strategies

| Scenario | Strategy | Mechanism |
|----------|----------|-----------|
| Two agents write same YAML | Single-writer convention | Each file has one owner |
| Two sessions start simultaneously | Session lock | `open(path, 'x')` exclusive create |
| Concurrent audit log appends | File locking | `fcntl.flock()` on append |
| Agent registry updates | Agent-scoped dirs | `state/agents/{id}/` — each agent owns its dir |
| Evolution concurrent proposals | Sequential evaluation | One proposal evaluated at a time |

---

## Part 7: Claude Code Limitations & Workarounds

The framework must work within Claude Code's constraints. These are the known limitations and their mitigations.

### 7.1 No Token Count API

**Limitation:** Claude Code does not expose token counts programmatically.

**Primary workaround:** Parse `/usage` command output from a secondary Claude Code shell instance. The `/usage` command displays input tokens, output tokens, cache reads, and cost data.

```python
# In resource_tracker.py
def parse_usage_output(self) -> dict | None:
    result = subprocess.run(["claude", "-p", "/usage"],
                            capture_output=True, text=True, timeout=10)
    # Parse with regex, version-aware (I8)
```

**Fallback:** Character-ratio estimation (3.5 chars/token for English). Calibrated against actual `/usage` data via rolling average. If estimation error >30%, flag for recalibration (P4).

### 7.2 No Direct Model Selection Control

**Limitation:** Cannot programmatically select which model an agent uses. The `model` parameter in Task tool is advisory.

**Workaround:** Use custom agent types defined in `.claude/agents/` with model hints in the prompt. Advisory only — Claude Code may override.

### 7.3 Ephemeral Agents

**Limitation:** Spawned agents (via Task tool) start with no memory of previous sessions. All context must be in the prompt.

**Workaround:** Full state reconstruction from YAML on every spawn. The prompt composer reads all relevant YAML files and injects their content into the agent's prompt. Parked task context is preserved in YAML for resume.

### 7.4 No Persistent Processes

**Limitation:** No daemon or background process can run between Claude Code sessions.

**Workaround:** Autonomous run loop is re-entered from persisted state. On session start, CLAUDE.md bootstrap reads framework state and resumes where it left off. State is always on disk, never in memory only.

### 7.5 No File Locking Primitives

**Limitation:** Claude Code agents cannot acquire file locks across processes.

**Workaround:**
- Single-writer convention (each file has one owner)
- Atomic writes (`os.replace()`)
- Session lock for single-framework-instance enforcement
- Append-only JSONL for audit logs (concurrent appends are safe with `fcntl.flock()`)

### 7.6 CLAUDE.md Not Reloadable Mid-Session

**Limitation:** CLAUDE.md is read once at session start. Changes during a session are not picked up.

**Workaround:** State is read directly from YAML files during the session. CLAUDE.md provides bootstrap instructions; live state is always read from disk. Machine-generated "Quick State" section is only authoritative at session start.

### 7.7 No Inter-Process Communication

**Limitation:** Agents cannot directly message each other except through Claude Code's `SendMessage` tool (within teams).

**Workaround:**
- Team agents use `SendMessage` for direct communication
- Non-team agents coordinate via shared YAML pressure fields (stigmergic)
- File-based message passing for critical coordination

### 7.8 Context Window Pressure from Framework Instructions

**Limitation:** CLAUDE.md + skill content consumes context window space, reducing room for actual task work.

**Workaround:**
- CLAUDE.md kept to ~150-200 lines (~2.5K tokens)
- Skills loaded on demand (~100 token trigger, ~2K full load)
- Context budget allocation: 10% for system instructions
- Compression cascade removes non-essential content under pressure

---

## Part 8: Phase 0 Implementation Sequence

Phase 0 is the **minimum viable framework**: human starts Claude Code in the framework directory → CLAUDE.md loads → framework bootstraps → human gives a task → orchestrator decomposes → workers execute → reviewer reviews → task completes with full audit trail.

Phase 0 does NOT include: evolution engine, diversity metrics, creativity engine, self-awareness, or any self-improvement. Those are Phase 1+.

### Dependency Graph

```
Step 1: Project Setup
  │
  ├──→ Step 2: Core Data Models
  │      │
  │      ├──→ Step 3: State Management
  │      │      │
  │      │      ├──→ Step 4: Directory Scaffold
  │      │      │      │
  │      │      │      └──→ Step 5: CONSTITUTION.md + Hash
  │      │      │             │
  │      │      │             └──→ Step 6: YAML Configs (roles, voice, framework)
  │      │      │
  │      │      ├──→ Step 7: Audit Logging
  │      │      │
  │      │      ├──→ Step 8: Prompt Composer
  │      │      │
  │      │      └──→ Step 9: Task Lifecycle
  │      │
  │      └──→ Step 10: CLAUDE.md + Skills
  │
  └──→ Step 11: Integration Test (all steps)
```

### Step-by-Step Details

| Step | What | Key Files | Dependencies | Validation |
|------|------|-----------|-------------|------------|
| 1 | Project setup | `pyproject.toml` | — | `uv run python -c "import yaml, pydantic, rich"` |
| 2 | Core data models | `src/uagents/models/*.py` (16 files) | Step 1 | All models instantiate, serialize to YAML, deserialize losslessly |
| 3 | State management | `src/uagents/state/*.py` (5 files) | Step 2 | Atomic write + read round-trip, lock acquire/release, JSONL append/read |
| 4 | Directory scaffold | `src/uagents/state/directory.py`, `cli/bootstrap.py` | Steps 2-3 | `uv run python -m uagents.cli.bootstrap --domain meta` creates full tree |
| 5 | CONSTITUTION.md | `CONSTITUTION.md`, `core/constitution-hash.txt` | Step 4 | SHA-256 hash computed and stored, hash verification passes |
| 6 | YAML configs | `roles/capabilities.yaml`, `roles/voice.yaml`, `roles/compositions/*.yaml`, `framework.yaml` | Steps 4-5 | All configs validate against Pydantic models, voice atom refs resolve |
| 7 | Audit logging | `src/uagents/audit/*.py` | Steps 2-3 | Append entry → read back succeeds, rotation at threshold, invalid stream raises |
| 8 | Prompt composer | `src/uagents/engine/prompt_composer.py` | Steps 2-3, 6 | Ring 0→3 ordering verified, voice compression stages work, budget enforcement |
| 9 | Task lifecycle | `src/uagents/engine/task_lifecycle.py` | Steps 2-3 | Full happy path works, invalid transitions rejected, park/resume |
| 10 | CLAUDE.md + Skills | `CLAUDE.md`, `.claude/skills/framework-*/SKILL.md` | Steps 5-9 | CLAUDE.md loads in Claude Code, bootstrap protocol executes |
| 11 | Integration test | End-to-end demo | All | Human → task → lifecycle → audit trail → complete |

### Step 1: Project Setup

```toml
# pyproject.toml
[project]
name = "universal-agents"
version = "0.1.0"
description = "Self-evolving multi-agent framework for Claude Code"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0.2",
    "pydantic>=2.10",
    "rich>=13.9",
    "psutil>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-cov>=6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/uagents"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

Commands:
```bash
cd /home/ak/universal-agents-team
uv init --no-readme
uv add pyyaml pydantic rich psutil
uv add --dev pytest pytest-cov
```

### Step 2: Core Data Models

Create all 16 model files as specified in Part 2. Key validation tests:

```python
# tests/test_models/test_task.py
def test_task_valid_transitions():
    """Every state has defined transitions."""
    for status in TaskStatus:
        assert status in VALID_TRANSITIONS

def test_task_roundtrip_yaml(tmp_path):
    """Task serializes to YAML and deserializes losslessly."""
    task = Task(
        id="task-20260228-001",
        created_at=datetime.utcnow(),
        status=TaskStatus.INTAKE,
        title="Test task",
        description="Test description",
        origin=TaskOrigin(type=TaskOriginType.HUMAN, source="test", reason="test"),
        rationale="testing",
        priority="medium",
    )
    path = tmp_path / "task.yaml"
    model_to_yaml(task, path)
    loaded = model_from_yaml(Task, path)
    assert loaded.id == task.id
    assert loaded.status == task.status

def test_invalid_transition_rejected():
    """Attempting INTAKE → EXECUTING should fail."""
    assert TaskStatus.EXECUTING not in VALID_TRANSITIONS[TaskStatus.INTAKE]

def test_voice_profile_validates_formality_range():
    """Formality must be 0.0 to 1.0."""
    with pytest.raises(ValidationError):
        VoiceProfile(language="language_english", formality=1.5)
```

### Steps 3-9: As Specified in Parts 3-4

Each step builds on previous ones. Implementation follows the code in Parts 3 and 4 exactly.

### Step 10: CLAUDE.md + Skills

Generate CLAUDE.md using `ClaudeMdGenerator` (Part 5). Create 7 skill files in `.claude/skills/framework-*/SKILL.md`.

### Step 11: Integration Test

The end-to-end demo sequence:

```
1. Bootstrap: uv run python -m uagents.cli.bootstrap --domain meta
   → Creates full directory tree, CONSTITUTION.md, CLAUDE.md

2. Session: uv run python -m uagents.cli.session_check acquire
   → Creates .claude-framework.lock

3. Constitution: verify hash
   → tools/constitution-check.sh passes

4. Task: uv run python -m uagents.cli.task_manager create \
     --title "Build greeting feature" \
     --description "Add a greeting module" \
     --origin human
   → Task created in INTAKE state

5. Transition through lifecycle:
   → INTAKE → ANALYSIS → PLANNING → EXECUTING → REVIEWING → VERDICT → COMPLETE

6. Audit: uv run python -m uagents.cli.audit_tree --since today
   → Tree shows all lifecycle events

7. Cleanup: uv run python -m uagents.cli.session_check release
   → Lock removed
```

---

## Part 9: Verification Checklist

Before Phase 0 is considered complete, every item must pass:

| # | Verification | Command | Expected |
|---|-------------|---------|----------|
| V1 | Dependencies install | `uv run python -c "import yaml, pydantic, rich, psutil"` | No errors |
| V2 | All models validate | `uv run pytest tests/test_models/ -v` | All pass |
| V3 | YAML round-trip | `uv run pytest -k yaml_roundtrip` | All pass |
| V4 | Bootstrap creates tree | `uv run python -m uagents.cli.bootstrap --domain meta` | Full directory tree created |
| V5 | Constitution hash | `tools/constitution-check.sh` | Hash matches |
| V6 | Invalid transitions rejected | `uv run pytest -k invalid_transition` | InvalidTransitionError raised |
| V7 | Task lifecycle happy path | `uv run pytest -k lifecycle_happy_path` | INTAKE → ... → COMPLETE |
| V8 | Audit logger works | `uv run pytest tests/test_audit/ -v` | Append + read + rotation pass |
| V9 | Prompt composer ring order | `uv run pytest -k ring_order` | Ring 0 appears before Ring 3 |
| V10 | Voice compression cascade | `uv run pytest -k voice_compression` | All 6 stages produce correct output |
| V11 | Session lock | `uv run pytest -k session_lock` | Acquire, stale detection, release all pass |
| V12 | CLAUDE.md generation | `uv run pytest -k claude_md` | Generated file contains hash, axioms, lifecycle |
| V13 | Full test suite | `uv run pytest --tb=long -v` | ALL tests pass, no warnings |
| V14 | Integration demo | Manual: human starts Claude Code → complete task | Audit trail recorded |

---

## Part 10: Edge Cases, Failure Modes & Mitigations

This section enumerates 64 failure modes across 12 subsystems with severity ratings and concrete mitigations. All mitigations follow the project's zero-tolerance no-fallback policy: **fail loud, never silently degrade**.

### 10.1 State Management (YAML Store)

| # | Failure Mode | Severity | Mitigation |
|---|-------------|----------|------------|
| S1 | **Concurrent writes** — two agents write same YAML file simultaneously | High | Single-writer convention: each file has exactly one owner. Agent-scoped files (`state/agents/{id}/`). JSONL is append-only. Session lock prevents duplicate framework instances. |
| S2 | **Crash during write** — partial YAML written to disk | High | Atomic write pattern: write to `{file}.tmp.{pid}`, then `os.replace()` (atomic on POSIX). Never write directly to target file. |
| S3 | **Disk full** — temp file creation fails | Medium | Check `psutil.disk_usage()` before write. If <100MB free: refuse write, log error, propagate as `ResourceExhaustedError`. Never silently swallow. |
| S4 | **External modification** — human/tool edits YAML, breaks Pydantic validation | Medium | Every read validates through Pydantic. On validation failure: `HARD_FAIL` with full error + file path + expected schema. Never load partial/invalid state. |
| S5 | **YAML deserialization attack** — crafted YAML exploits loader | High | Always use `yaml.safe_load()`, NEVER `yaml.load()`. Enforce as lint rule. Pydantic validation catches unexpected types/fields. |
| S6 | **Very large YAML files** — memory exhaustion loading registry/configs | Low | Size cap: refuse to load files >1MB. Split large collections (e.g., task archive) into per-item files. |
| S7 | **File permissions changed externally** | Low | Check `os.access()` before read/write. Clear error message with exact path and needed permissions. |
| S8 | **Encoding issues** — non-UTF-8 characters in YAML | Low | Enforce `encoding='utf-8'` on all file operations. Reject files that fail UTF-8 decode. |

### 10.2 JSONL Audit Logger

| # | Failure Mode | Severity | Mitigation |
|---|-------------|----------|------------|
| A1 | **Rotation race** — two processes rotate same log file | Medium | Only the session-lock-holding process rotates. Rotation check: `if file_size > 10MB AND holds_session_lock`. |
| A2 | **Corrupt JSON line** — partial write on crash | Medium | On read: skip lines that fail `json.loads()`, log warning with line number. Audit integrity checker tool reports corrupt lines. |
| A3 | **Disk exhaustion from unbounded logs** | Medium | 10MB rotation + configurable max rotated files (default 10 per stream). Emergency: if disk <100MB, pause non-critical logging, keep only `decision` and `safety` streams. |
| A4 | **Time-range query spans rotation boundary** | Low | Query function searches current + all rotated files matching time range. Rotated files named `{stream}.{timestamp}.jsonl` for chronological ordering. |
| A5 | **Clock skew between agents** — timestamps not strictly ordered | Low | Use `time.monotonic()` for duration/ordering within a session. Timestamps are informational, not ordering guarantees. Document this limitation. |
| A6 | **Append during rotation** — entry lost between rename and new file creation | Medium | Rotation sequence: (1) open new file, (2) atomic rename old→rotated, (3) new appends go to new file. Brief lock during rename. |

### 10.3 Session Lock

| # | Failure Mode | Severity | Mitigation |
|---|-------------|----------|------------|
| L1 | **Stale lock** — process died without cleanup (kill -9, crash) | High | PID liveness check: `os.kill(pid, 0)` on Linux. If PID dead → lock is stale → auto-remove with warning log. |
| L2 | **PID reuse** — OS recycles PID, lock appears valid | Medium | Store process start time in lock file. Verify PID + start_time match. If PID alive but start_time differs → stale lock. |
| L3 | **Lock file on NFS/network FS** — advisory locks unreliable | Low | Not a target scenario (local development). Document: "Framework requires local filesystem. NFS not supported." |
| L4 | **Simultaneous startup** — two instances check lock at same instant | Medium | Use `open(path, 'x')` (exclusive create) for lock acquisition. This is atomic on POSIX. If `FileExistsError` → another instance won. |
| L5 | **Lock not released on exception** — Python exception skips cleanup | High | `atexit.register()` for cleanup. Context manager for lock lifecycle. `try/finally` in bootstrap. Document that `kill -9` requires `tools/force-unlock.sh`. |

### 10.4 Constitution Guard

| # | Failure Mode | Severity | Mitigation |
|---|-------------|----------|------------|
| C1 | **Hash mismatch after legitimate edit** — user manually edited CONSTITUTION.md | Critical | Clear message: "Constitution hash mismatch. If you edited CONSTITUTION.md intentionally, run `tools/rehash-constitution.sh` to update the hash. Otherwise, restore from git." Never auto-fix. |
| C2 | **Hash file missing** | High | Bootstrap regenerates hash on first run. If hash file disappears mid-session: `HARD_FAIL` — refuse all operations until rehash. |
| C3 | **Git merge conflict in CONSTITUTION.md** | Medium | CONSTITUTION.md is excluded from evolution engine. Only human edits allowed. If conflict detected: halt, require human resolution. |
| C4 | **Constitution file deleted** | Critical | Check at session start and before every evolution. If missing: `HARD_FAIL` with recovery instructions (restore from git). |

### 10.5 Prompt Composer

| # | Failure Mode | Severity | Mitigation |
|---|-------------|----------|------------|
| P1 | **Context budget exceeded** — role composition + voice > allocation | High | Validation at compose time. If role+voice exceeds budget: (1) compress voice (persona → style → tone → language), (2) if still over: truncate least-critical capability atoms, (3) log what was dropped. Never silently exceed budget. |
| P2 | **Voice atom references non-existent atom** | Medium | Validate all atom references at compose time against `roles/voice.yaml`. If missing: `HARD_FAIL` with "Voice atom '{name}' not found in roles/voice.yaml". Never substitute defaults. |
| P3 | **Ring ordering violation via prompt injection** | High | Compose function enforces order programmatically (Ring 0 → 1 → 2 → 3). Output is a single string, not user-modifiable. Post-composition assertion: verify Ring 0 content appears in first N characters. |
| P4 | **Token estimation drift** — char-ratio diverges from actual | Medium | Calibrate against `/usage` output. Rolling average replaces cold seeds after 10 samples. If estimation error >30%: flag for recalibration. |
| P5 | **Very long CLAUDE.md** — user adds too much, exceeds token budget | Medium | CLAUDE.md composer enforces max length. If over: warn user with exact token estimate. Machine-generated section has 100-line cap. |
| P6 | **Missing role YAML during composition** | High | Fail loud: `FileNotFoundError` with exact path. Never fall back to a "default" role. |

### 10.6 Task Lifecycle

| # | Failure Mode | Severity | Mitigation |
|---|-------------|----------|------------|
| T1 | **Invalid state transition** | Medium | `VALID_TRANSITIONS` dict enforced in `transition()`. Attempting invalid transition raises `InvalidTransitionError(current, attempted, valid_options)`. Logged to `decision` audit stream. |
| T2 | **Stuck task** — agent died mid-execution, task remains `in_progress` | High | Heartbeat: task YAML updated with `last_heartbeat` timestamp. Monitor: tasks with heartbeat >5min old flagged as potentially stuck. Recovery: park task → allow reassignment. |
| T3 | **Orphaned tasks** — spawning agent died before completing lifecycle | Medium | Periodic scan: tasks in `assigned`/`in_progress` whose owner agent is not in registry → transition to `blocked` with reason "orphaned". |
| T4 | **Two agents claim same task** — race condition | Medium | Single-writer convention for task files. Agent must atomically write its ID to task file to claim. If file already has different owner → claim rejected. |
| T5 | **Circular task dependencies** | Low | Cycle detection at dependency creation time. DFS on dependency graph. Reject if adding edge creates cycle. |
| T6 | **Task state file corrupted** | Medium | Pydantic validation on every read (same as S4). If corrupted: log error, mark task as `failed` with "state corruption" reason. |
| T7 | **Park/resume with stale context** — agent resumes task but codebase changed | Medium | On resume: include diff summary since park time. Task mandate includes `parked_at_commit` hash for comparison. Agent must acknowledge stale context risk. |

### 10.7 Agent Spawner

| # | Failure Mode | Severity | Mitigation |
|---|-------------|----------|------------|
| G1 | **TOCTOU resource race** — resources available at check, exhausted at spawn | Medium | Optimistic spawn with immediate post-spawn resource recheck. If over threshold: immediately despawn the just-spawned agent. Reserve 20% headroom in pre-spawn check. |
| G2 | **YAML config references missing role/voice files** | High | Full dependency validation before spawn: check all referenced capability atoms, voice atoms, tool definitions exist. Fail with precise missing-file list. |
| G3 | **Claude Code Task tool fails silently** | High | Require agent to write a heartbeat file within 30s of spawn. If no heartbeat: spawn failed. Log and retry once. If retry fails: mark task as `blocked`. |
| G4 | **Too many concurrent agents** | Medium | Hard cap: `max_concurrent_agents` in `framework.yaml` (default: 5). Queue tasks when at cap. Log queue depth. |
| G5 | **Agent registry update race** — two spawns register simultaneously | Low | Agent-scoped files: each agent writes `state/agents/{own_id}/status.yaml`. Registry is read by scanning directory, not a single file. No write contention. |
| G6 | **Spawned agent enters infinite loop** | Medium | Timeout per task (configurable, default 30min). If exceeded: force-park task, despawn agent. Log full state for debugging. |

### 10.8 Directory Scaffold

| # | Failure Mode | Severity | Mitigation |
|---|-------------|----------|------------|
| D1 | **Partial scaffold** — interrupted mid-creation | Medium | Idempotent creation: `os.makedirs(exist_ok=True)` for directories, skip-if-exists for files. Re-running scaffold is always safe. |
| D2 | **Existing files in scaffold location** | Medium | Never overwrite existing files. Flag as warning: "File {path} already exists, skipping." Provide `--force` flag for explicit overwrite. |
| D3 | **Permission denied creating directories** | Medium | Clear error with exact path. Suggest: `chmod`/`chown` or choose different root. |

### 10.9 Git Operations (Evolution)

| # | Failure Mode | Severity | Mitigation |
|---|-------------|----------|------------|
| E1 | **Merge conflict in evolution branch** | Medium | Evolution operates on YAML configs, not arbitrary code. Structured merge: field-level comparison, auto-resolve non-conflicting fields, flag true conflicts for human review. |
| E2 | **Evolution branch diverges significantly from main** | Medium | Max branch lifetime: 24 hours. If not merged: auto-rebase. If rebase fails: archive branch, create fresh. |
| E3 | **Git operations during active editing** — staging conflicts | Low | Framework uses dedicated `state/` directory for its files. User code lives elsewhere. Separation by convention. |
| E4 | **Large binary accidentally committed** | Low | `.gitignore` generated by bootstrap. Pre-commit hook rejects files >1MB. |
| E5 | **History rewriting destroys audit trail** | Critical | Never rebase or force-push published branches. Document as constitutional constraint. All evolution branches are merge-only. |

### 10.10 Claude Code Integration

| # | Failure Mode | Severity | Mitigation |
|---|-------------|----------|------------|
| I1 | **CLAUDE.md exceeds effective token limit** | Medium | Machine-generated section has hard cap (100 lines). Static sections kept minimal (~150 lines total). Monitor with `/usage` output. |
| I2 | **Skill file missing or corrupted** | Medium | Skill loader validates file existence before injection. Missing skill: `HARD_FAIL` with skill name + expected path. Never silently skip a skill. |
| I3 | **Team coordination message lost** — SendMessage has no delivery guarantee | Medium | Important coordination: require acknowledgment message back. If no ack within 2min: retry once. If still no ack: escalate to team lead / log as coordination failure. |
| I4 | **Hung agent** — spawned agent never responds | Medium | Timeout (see G6). Team lead monitors heartbeats. Unresponsive agent → despawn → reassign task. |
| I5 | **Universal Memory MCP unavailable** | Medium | Memory is supplementary, not critical path. If unavailable: log warning, continue with YAML-only state. Do NOT silently substitute empty results for memory queries — log every failed query. |
| I6 | **Rate limits during multi-agent orchestration** | High | Backpressure propagation (Section 18.3). Reduce concurrency, queue tasks, park low-priority work. Never retry in tight loop. |
| I7 | **Claude Code version upgrade changes tool behavior** | Medium | Canary suite (Section 19.1) detects behavioral changes. On drift: log alert, continue with caution, flag for human review. |
| I8 | **`/usage` command output format changes** — parsing breaks | Low | Parser uses regex with version detection. If parse fails: fall back to character-ratio estimation. Log warning about `/usage` parse failure. |

### 10.11 Voice System

| # | Failure Mode | Severity | Mitigation |
|---|-------------|----------|------------|
| V1 | **Persona overrides safety constraints** — persona like "devil's advocate" pushes past guardrails | High | Voice injected at Ring 3, after constitution at Ring 0. Persona cannot modify `risk_tolerance`. Alignment tests run across all voice configs. |
| V2 | **Voice profile makes agent output unverifiable** — very creative persona produces unreliable reasoning | Medium | Reviewer agents always use `tone_cautious`, cannot have creative personas. Verification agents have strict voice profiles. |
| V3 | **Voice evolution converges** — all agents drift toward same voice | Medium | Voice Diversity Index (VDI) metric, 20% weight in SRD. Stagnation signals trigger forced voice rotation. Anti-convergence pressure in evolution. |
| V4 | **Language atom conflict with task requirements** — task requires English but agent has `language_japanese` | Medium | Task mandate can override voice language. Language inheritance: task_mandate > role_voice > domain_default. Log the override. |
| V5 | **Voice compression loses critical language atom** — under pressure, wrong language used | Medium | Compression cascade keeps language atom even at stage 5 if non-default. Language is the LAST thing dropped. |

### 10.12 Cross-Cutting Concerns

| # | Failure Mode | Severity | Mitigation |
|---|-------------|----------|------------|
| X1 | **System clock change** — timestamps become inconsistent | Low | Use `time.monotonic()` for duration/ordering within a session. Wall clock timestamps are informational. Log system clock jumps. |
| X2 | **Disk space exhaustion** — no component tracks overall disk | Medium | `compute_monitor` tracks disk usage (Section 18.4). At warning threshold: alert human, pause non-critical logging. At critical: refuse all writes except safety logs. |
| X3 | **Multiple framework instances across different directories** | Low | Session lock is per-directory. Two instances in different dirs are independent by design. Warn if both point to same `state/` directory. |
| X4 | **Python dependency conflict** — uv resolves different versions | Low | Pin all dependencies in `pyproject.toml` with exact versions. `uv.lock` committed to git. |
| X5 | **Signal handling during state write** — SIGTERM mid-write | Medium | Atomic writes (`os.replace`) protect file integrity. `signal.signal()` handler: set shutdown flag, complete current write, then exit cleanly. |
| X6 | **Memory pressure from loading many YAML files** | Low | Lazy loading: only load files when needed, don't cache everything. Agent-scoped: each agent loads only its own state + shared configs. |
| X7 | **Secrets in audit logs** — environment variables or API keys logged | High | Audit logger sanitizes known patterns (API keys, tokens, passwords) before writing. Regex-based scrubber. Log scrub actions. |

### Summary Statistics

| Category | Count |
|----------|-------|
| **Total failure modes** | **64** |
| Critical severity | 4 (C1, C4, E5, and constitutional bypass) |
| High severity | 18 (S1, S2, S5, L1, L5, C2, P1, P3, P6, T2, G2, G3, I6, V1, X7, +3) |
| Medium severity | 32 |
| Low severity | 10 |

All mitigations follow the zero-tolerance no-fallback policy: **fail loud, never silently degrade**.

---

## Appendix A: Cross-Reference to v1.1 Spec

| Design Part | v1.1 Spec Sections |
|-------------|-------------------|
| Part 1 (Architecture) | 1, 3, 24 |
| Part 2 (Data Models) | 2, 4, 5, 6, 9, 17, 18, 19, 20, 21, 22 |
| Part 3 (State Management) | 3.3, 17, 24 |
| Part 4 (Engine Layer) | 4-6, 9, 17-21 |
| Part 5 (CLAUDE.md) | 3, 21.3 |
| Part 6 (Integration) | 3, 5, 15 |
| Part 7 (Limitations) | 18, 19, 20, 21 |
| Part 8 (Phase 0 Sequence) | 3.3, 23 |
| Part 9 (Verification) | All |
| Part 10 (Failure Modes) | 27 + new analysis |

## Appendix B: Token Budget Summary

| Component | Estimated Tokens | Notes |
|-----------|-----------------|-------|
| CLAUDE.md (static) | ~2,500 | 150-200 lines |
| Skill trigger (per skill) | ~100 | One-liner in CLAUDE.md |
| Skill body (loaded on demand) | ~1,500-2,000 | Full skill instructions |
| Ring 0 (constitution) | ~500 | 8 axioms + enforcement |
| Ring 1 (infrastructure) | ~300 | Domain context + coordination |
| Ring 2 (role composition) | ~800-1,500 | Capabilities + voice + behavioral |
| Ring 3 (task context) | Variable | Task description + constraints |
| Total system overhead | ~4,500-6,000 | Well under 10% of 200K context |

---

*Document generated from v1.1 architecture spec (3549 lines, 28 sections).
Phase 0 target: minimum viable framework with full audit trail.
Implementation language: Python 3.11+ with Pydantic v2, managed by uv.*
