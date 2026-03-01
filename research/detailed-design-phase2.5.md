# Universal Agents Framework — Phase 2.5 Detailed Design

**Version:** 0.2.0
**Date:** 2026-03-01
**Source:** framework-design-unified-v1.1.md (Section 19), environment-awareness-pruning-literature-review.md (~65 papers)
**Status:** Implementation-ready — reviewed and fixed (7 must-fix, 9 should-fix, 19 failure mode items applied)
**Scope:** Phase 2.5 "Environment Awareness" — model fingerprinting, drift detection, revalidation pipeline, continuous performance monitoring, self-benchmarking
**Prerequisite:** Phase 0 + Phase 1 + Phase 1.5 + Phase 2 fully implemented

---

## Table of Contents

1. [Architecture Overview](#part-1-architecture-overview)
2. [Data Models](#part-2-data-models)
3. [YAML Configuration](#part-3-yaml-configuration)
4. [CanaryRunner Engine](#part-4-canaryrunner-engine)
5. [DriftDetector Engine](#part-5-driftdetector-engine)
6. [RevalidationEngine](#part-6-revalidationengine)
7. [PerformanceMonitor](#part-7-performancemonitor)
8. [EnvironmentMonitor Upgrade](#part-8-environmentmonitor-upgrade)
9. [Modifications to Existing Files](#part-9-modifications-to-existing-files)
10. [Implementation Sequence](#part-10-implementation-sequence)
11. [Failure Modes](#part-11-failure-modes)

---

## Part 1: Architecture Overview

### 1.1 What Phase 2.5 Adds

Phase 2.5 transforms the framework from "self-measuring but environment-oblivious" to "environment-aware." After Phase 2, the framework can measure its own diversity, stagnation, capability, and confidence — but it cannot detect when the environment beneath it changes. GPT-4 accuracy dropped from 84% to 51% between versions silently (Chen et al. 2023, arXiv:2307.09009). Claude Code updates and underlying model changes can similarly affect framework performance without warning.

Phase 2.5 adds five subsystems:

1. **CanaryRunner** — Executes 5 fixed micro-benchmark tasks at session start to produce a ModelFingerprint. Tasks are FIXED and never change (they are the ruler, not the subject). Budget: < 5000 tokens, < 2 minutes.
2. **DriftDetector** — Stores fingerprint history, computes Euclidean distance between current and baseline fingerprints, flags drift when distance > 15% threshold. Tracks Claude Code version changes.
3. **RevalidationEngine** — When drift or version change is detected, assesses scope, runs targeted revalidation capped at 10% of session budget, and classifies adaptation response (improved/unchanged/degraded_minor/degraded_major/broken).
4. **PerformanceMonitor** — Continuously tracks per-skill success rates (rolling window of 20), per-tool reliability, and structured traces at 3 levels (operational, cognitive, contextual). Alerts on > 10pp success rate drops.
5. **EnvironmentMonitor (upgraded)** — Orchestrates all Phase 2.5 components. Replaces Phase 0 stub. Runs session_start() checks and periodic_check() every N tasks.

### 1.2 Key Design Principles (from ~65 papers)

1. **Canary tasks are FIXED** — They never change. They are the ruler, not the subject. Modifying canaries would invalidate all historical comparisons (Chen et al. 2023).
2. **Euclidean distance in 5D score space** — Simple, interpretable, deterministic. No learned embeddings or statistical tests needed for drift detection.
3. **Budget-capped revalidation** — Max 10% of session token budget. Revalidation is valuable but must not consume the session (BATS, arXiv:2511.17006).
4. **Per-dimension drift analysis** — When drift is detected, report WHICH capabilities changed, not just that something changed. Enables targeted revalidation.
5. **Version tracking is cheap insurance** — `claude --version` comparison catches most updates with zero token cost.
6. **Rolling windows prevent noise** — Per-skill tracking uses rolling window of 20 to smooth out individual task variance.
7. **Structured tracing enables debugging** — Three levels (operational, cognitive, contextual) from AgentTrace (arXiv:2602.10133) provide actionable diagnostics.

### 1.3 What Phase 2.5 Does NOT Include

- Automatic skill modification based on drift (Phase 3 — requires skill extraction).
- Model cascading / routing based on fingerprint (Phase 4+ — requires evolution engine).
- Dynamic tool loading changes based on tool performance (Phase 3.5).
- Population-based adaptation to environment changes (Phase 8).
- Automatic MCP server schema diffing (future — requires MCP introspection API).
- OS-level change detection beyond version strings (future).

Phase 2.5 is a **detection and measurement** phase for environment changes. It detects and classifies changes, runs revalidation, and records adaptation responses. It does NOT autonomously modify the framework in response (that is Phase 4+). The strongest autonomous action is quarantining a broken skill to Ring 3.

### 1.4 Component Dependency Graph

```
CanaryRunner ──────────┐
  (runs canaries)      │
                       ▼
DriftDetector ─────► EnvironmentMonitor ◄─── PerformanceMonitor
  (compares FPs)       │ (orchestrator)        (per-skill/tool)
                       │
                       ▼
              RevalidationEngine
              (targeted re-test)
                       │
                       ▼
              CapabilityTracker (Phase 2)
              (updates skill records)
```

### 1.5 Integration Points with Existing Phases

| Phase | Integration |
|-------|-------------|
| Phase 0 | `YamlStore` for all state persistence, `generate_id()` for IDs |
| Phase 1 | `AuditLogger.log_environment()` for ENVIRONMENT stream events |
| Phase 1.5 | `BudgetTracker.get_window()` for revalidation budget cap |
| Phase 2 | `CapabilityTracker.record_outcome()` for skill-level performance updates |
| Phase 2 | `AuditTreeViewer` for environment stream rendering |

### 1.6 Files Created & Modified

**New files (5):**
| File | Lines (est.) | Purpose |
|------|------------|---------|
| `engine/canary_runner.py` | ~320 | Fixed micro-benchmark execution and scoring (with hash verification, named checkers, ProcessPoolExecutor) |
| `engine/drift_detector.py` | ~230 | Fingerprint storage, comparison, drift classification (with history guard, broad exception handling) |
| `engine/revalidation_engine.py` | ~300 | Triggered revalidation with budget cap (with canary re-run, per-dim check, history trim) |
| `engine/performance_monitor.py` | ~330 | Per-skill/tool tracking, structured tracing (with threading.Lock, batch writes, dedup alerts) |
| `core/canary-expectations.yaml` | ~80 | Fixed expected outputs for 5 canary probes |

**Modified files (5):**
| File | Changes |
|------|---------|
| `models/environment.py` | Add CanarySuiteResult, PerformanceTrack, SkillPerformance, ToolPerformance, RevalidationResult, BenchmarkSuiteResult, VersionInfo, ModelExecuteFn, PerformanceAlert, EnvironmentCheckResult |
| `engine/environment_monitor.py` | Full rewrite as Phase 2.5 orchestrator |
| `core/environment-awareness.yaml` | Complete configuration file |
| `audit/tree_viewer.py` | Environment stream rendering |
| `audit/logger.py` | Already has `log_environment()` — no changes needed |

---

## Part 2: Data Models

### 2.1 New Models in `models/environment.py`

The existing `models/environment.py` already defines `ModelFingerprint`, `CanaryResult`, and `DriftDetection`. Phase 2.5 adds the following models to the same file.

```python
"""Environment awareness models.
Spec reference: Section 19 (Environment Awareness & Self-Benchmarking).

Phase 0: ModelFingerprint, CanaryResult, DriftDetection.
Phase 2.5: CanarySuiteResult, VersionInfo, PerformanceTrack,
           SkillPerformance, ToolPerformance, RevalidationResult,
           BenchmarkSuiteResult, TraceEntry, ModelExecuteFn.
"""
from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from pydantic import Field

from .base import FrameworkModel, TimestampedModel


# SF-1: Typed protocol for model execution function (replaces bare `callable`)
class ModelExecuteFn(Protocol):
    """Protocol for model execution functions used by CanaryRunner and
    RevalidationEngine.

    Signature: (prompt: str, max_tokens: int) -> tuple[str, int]
    Returns: (output_text, tokens_used)
    """

    def __call__(self, prompt: str, max_tokens: int) -> tuple[str, int]: ...


# ── Existing Phase 0 models ──
# Migration note (MF-3): Phase 2.5 adds Field(ge=0.0, le=1.0) validators
# to CanaryResult.score and Field(ge=0) to CanaryResult.tokens_used and
# CanaryResult.latency_ms. Existing stored CanaryResult YAML files must
# contain valid values (non-negative, score in [0,1]) or they will fail
# Pydantic validation on load. Phase 0 data should already conform since
# scores are always 0.0-1.0 and counts are non-negative.

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

    def per_dimension_delta(self, other: ModelFingerprint) -> dict[str, float]:
        """Per-dimension signed delta (self - other). Positive = improvement."""
        return {
            "reasoning": self.reasoning_score - other.reasoning_score,
            "instruction": self.instruction_score - other.instruction_score,
            "code": self.code_score - other.code_score,
            "creative": self.creative_score - other.creative_score,
            "tool": self.tool_score - other.tool_score,
        }

    def score_vector(self) -> list[float]:
        """Return the 5 capability scores as a list."""
        return [
            self.reasoning_score,
            self.instruction_score,
            self.code_score,
            self.creative_score,
            self.tool_score,
        ]


class CanaryResult(FrameworkModel):
    """Result of a single canary micro-benchmark."""

    task_name: str
    expected: str
    actual: str
    score: float = Field(ge=0.0, le=1.0)
    tokens_used: int = Field(ge=0)
    latency_ms: int = Field(ge=0)


class DriftDetection(FrameworkModel):
    """Result of drift analysis comparing current vs baseline fingerprints."""

    current: ModelFingerprint
    baseline: ModelFingerprint
    distance: float
    threshold: float = 0.15
    drift_detected: bool
    affected_dimensions: list[str]


# ── Phase 2.5 new models ──

class CanarySuiteResult(TimestampedModel):
    """Complete result of running the 5-task canary suite."""

    results: list[CanaryResult]
    fingerprint: ModelFingerprint
    total_tokens: int = Field(ge=0)
    total_latency_ms: int = Field(ge=0)
    all_passed: bool

    @property
    def task_scores(self) -> dict[str, float]:
        """Map of task_name -> score for quick lookup."""
        return {r.task_name: r.score for r in self.results}


class VersionInfo(FrameworkModel):
    """Tracked version information for environment change detection."""

    claude_code_version: str
    python_version: str
    os_info: str
    timestamp: datetime

    def differs_from(self, other: VersionInfo) -> list[str]:
        """Return list of fields that differ between two VersionInfo instances."""
        changes: list[str] = []
        if self.claude_code_version != other.claude_code_version:
            changes.append("claude_code_version")
        if self.python_version != other.python_version:
            changes.append("python_version")
        if self.os_info != other.os_info:
            changes.append("os_info")
        return changes


class SkillPerformance(FrameworkModel):
    """Rolling performance record for a single skill/task_type."""

    skill_name: str
    recent_outcomes: list[bool] = Field(default_factory=list)  # Last 20 outcomes
    total_attempts: int = 0
    total_successes: int = 0
    total_tokens: int = 0
    total_latency_ms: int = 0
    baseline_success_rate: float | None = None  # Set after first 20 attempts
    last_updated: datetime | None = None

    @property
    def success_rate(self) -> float:
        """Current success rate from rolling window."""
        if not self.recent_outcomes:
            return 0.0
        return sum(1 for o in self.recent_outcomes if o) / len(self.recent_outcomes)

    @property
    def avg_tokens(self) -> float:
        """Average tokens per attempt."""
        if self.total_attempts == 0:
            return 0.0
        return self.total_tokens / self.total_attempts

    @property
    def avg_latency_ms(self) -> float:
        """Average latency per attempt."""
        if self.total_attempts == 0:
            return 0.0
        return self.total_latency_ms / self.total_attempts

    @property
    def success_rate_drop(self) -> float | None:
        """Drop in success rate vs baseline (positive = degradation).
        Returns None if no baseline established yet."""
        if self.baseline_success_rate is None:
            return None
        return self.baseline_success_rate - self.success_rate


class ToolPerformance(FrameworkModel):
    """Rolling performance record for a single tool."""

    tool_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeout_calls: int = 0
    total_tokens: int = 0
    last_updated: datetime | None = None

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    @property
    def timeout_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.timeout_calls / self.total_calls

    @property
    def avg_token_cost(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_tokens / self.total_calls


class PerformanceTrack(TimestampedModel):
    """Complete performance tracking state. Persisted to YAML."""

    skills: dict[str, SkillPerformance] = Field(default_factory=dict)
    tools: dict[str, ToolPerformance] = Field(default_factory=dict)
    tasks_since_last_check: int = 0


class RevalidationTrigger(StrEnum):
    """What caused a revalidation."""

    MODEL_DRIFT = "model_drift"
    VERSION_CHANGE = "version_change"
    MCP_CHANGE = "mcp_change"
    PERFORMANCE_DROP = "performance_drop"
    MANUAL = "manual"


class AdaptationResponse(StrEnum):
    """Classification of how the environment changed."""

    IMPROVED = "improved"
    UNCHANGED = "unchanged"
    DEGRADED_MINOR = "degraded_minor"
    DEGRADED_MAJOR = "degraded_major"
    BROKEN = "broken"


class RevalidationResult(TimestampedModel):
    """Result of a triggered revalidation."""

    trigger: RevalidationTrigger
    trigger_detail: str
    scope: list[str]  # What was revalidated (skill names, tool names)
    tokens_used: int = Field(ge=0)
    budget_cap: int  # Max tokens allowed for this revalidation
    pre_fingerprint: ModelFingerprint | None = None
    post_fingerprint: ModelFingerprint | None = None
    adaptation: AdaptationResponse
    affected_skills: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)


class BenchmarkTask(FrameworkModel):
    """A single self-benchmarking meta-task."""

    name: str
    description: str
    expected_behavior: str
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    tokens_used: int = Field(ge=0, default=0)
    latency_ms: int = Field(ge=0, default=0)


class BenchmarkSuiteResult(TimestampedModel):
    """Result of self-benchmarking protocol."""

    tasks: list[BenchmarkTask]
    composite_score: float = Field(ge=0.0, le=1.0)
    suite_type: str  # "full" or "quick"
    total_tokens: int = Field(ge=0)

    @property
    def task_scores(self) -> dict[str, float]:
        return {t.name: t.score for t in self.tasks}


class TraceLevel(StrEnum):
    """Structured trace levels from AgentTrace (arXiv:2602.10133)."""

    OPERATIONAL = "operational"
    COGNITIVE = "cognitive"
    CONTEXTUAL = "contextual"


class TraceEntry(FrameworkModel):
    """A single structured trace entry."""

    level: TraceLevel
    task_id: str
    timestamp: datetime
    category: str  # e.g., "tool_call", "reasoning_step", "context_usage"
    detail: dict
    tokens_used: int = 0
    latency_ms: int = 0


# SF-2/IFM-22/IFM-23: Converted from plain classes to FrameworkModel
class PerformanceAlert(FrameworkModel):
    """A performance alert to be surfaced to the orchestrator."""

    alert_type: str  # "skill_degradation", "tool_degradation", "tool_quarantine"
    target_name: str
    message: str
    current_rate: float
    baseline_rate: float | None = None
    timestamp: datetime


class EnvironmentCheckResult(FrameworkModel):
    """Result of an environment check (session start or periodic)."""

    drift_detected: bool = False
    drift: DriftDetection | None = None
    version_changes: list[str] = Field(default_factory=list)
    version_info: VersionInfo | None = None
    fingerprint: ModelFingerprint | None = None
    revalidation_triggered: bool = False
    adaptation: AdaptationResponse | None = None
    alerts: list[PerformanceAlert] = Field(default_factory=list)
    canary_all_passed: bool = True
    skipped: bool = False
    skip_reason: str = ""
```

### 2.2 Model Summary

| Model | Purpose | Persisted To |
|-------|---------|-------------|
| `CanarySuiteResult` | Complete canary run results with fingerprint | `state/environment/canary-results/` |
| `VersionInfo` | Claude Code + Python + OS version snapshot | `state/environment/version-info.yaml` |
| `SkillPerformance` | Per-skill rolling success rate (window=20) | Part of `PerformanceTrack` |
| `ToolPerformance` | Per-tool success/timeout rates | Part of `PerformanceTrack` |
| `PerformanceTrack` | Aggregate performance state | `state/environment/performance-track.yaml` |
| `RevalidationResult` | Outcome of triggered revalidation | `state/environment/revalidation-history/` |
| `BenchmarkSuiteResult` | Self-benchmarking scores | `state/environment/benchmark-results/` |
| `TraceEntry` | Structured trace for debugging | `logs/traces/` via JSONL |
| `RevalidationTrigger` | Enum: what caused revalidation | Used in `RevalidationResult` |
| `AdaptationResponse` | Enum: how environment changed | Used in `RevalidationResult` |
| `TraceLevel` | Enum: operational/cognitive/contextual | Used in `TraceEntry` |
| `ModelExecuteFn` | Protocol: model execution function signature | Used in CanaryRunner, RevalidationEngine, EnvironmentMonitor |
| `PerformanceAlert` | Performance degradation alert (FrameworkModel) | In-memory, consumed by EnvironmentMonitor |
| `EnvironmentCheckResult` | Result of session start / periodic check (FrameworkModel) | Returned to Orchestrator |

---

## Part 3: YAML Configuration

### 3.1 `core/environment-awareness.yaml`

```yaml
# Environment awareness configuration
# Spec reference: Section 19 (Environment Awareness & Self-Benchmarking)
# All thresholds are authoritative — engines read from this file, not hardcoded constants.

environment_awareness:

  canary_suite:
    # Budget constraints for canary execution
    max_total_tokens: 5000        # Hard cap: entire suite must use < 5000 tokens
    max_runtime_seconds: 120      # Hard cap: entire suite must complete in < 2 min
    per_task_token_cap: 1200      # Soft cap per individual canary task
    # Scoring thresholds
    pass_score: 0.7               # Score >= this counts as "passed"
    # Recency skip: don't re-run if last fingerprint is recent AND version unchanged
    skip_if_recent_hours: 5       # Hours before canary re-run is needed

  drift_detection:
    threshold: 0.15               # Euclidean distance > this triggers ENVIRONMENT_CHANGE
    history_size: 10              # Number of recent fingerprints to store
    baseline_window: 5            # Use median of last N fingerprints as baseline
    per_dimension_alert: 0.10     # Per-dimension delta > this flags that dimension
    periodic_check_interval: 50   # Re-run canaries every N completed tasks

  revalidation:
    budget_cap_pct: 0.10          # Max fraction of session token budget for revalidation
    min_budget_tokens: 2000       # Don't revalidate if budget < this (too few to be useful)
    # Adaptation classification thresholds (MF-4: named to match AdaptationResponse levels)
    improved_threshold: 0.05      # Mean delta > +5% → IMPROVED
    degraded_minor_threshold: 0.05  # Mean delta < -5% → DEGRADED_MINOR
    degraded_major_threshold: 0.15  # Mean delta < -15% → DEGRADED_MAJOR
    broken_threshold: 0.30          # Mean delta < -30% → BROKEN

  performance_monitoring:
    skill_window_size: 20         # Rolling window for per-skill success rate
    skill_alert_drop_pp: 10       # Alert if success_rate drops > 10 percentage points
    tool_alert_drop_pp: 15        # Alert if tool success_rate drops > 15pp
    tool_quarantine_threshold: 0.5  # Quarantine tool if success_rate < 50%
    trace_retention_tasks: 100    # Keep traces for last N tasks

  self_benchmarking:
    full_suite_interval: 100      # Run full benchmark every N completed tasks
    quick_suite_interval: 20      # Run quick benchmark every N completed tasks
    quick_suite_tasks: 3          # Number of tasks in quick suite (first 3 of full)

  version_tracking:
    check_on_session_start: true  # Always check claude --version at session start
    version_command: "claude --version"
    version_timeout_seconds: 5
```

### 3.2 `core/canary-expectations.yaml`

```yaml
# Fixed canary suite expected outputs
# WARNING: These values must NEVER be changed. They are the ruler, not the subject.
# Changing canary expectations invalidates all historical fingerprint comparisons.
# Spec reference: Section 19.1 (Model Fingerprinting)

canary_expectations:

  reasoning:
    prompt: |
      Solve this logic puzzle step by step:
      There are 3 boxes. Box A contains only apples. Box B contains only bananas.
      Box C contains a mix of apples and bananas. All labels are WRONG.
      You pick one fruit from Box C and it is an apple.
      What does each box actually contain?
    expected_answer: "Box C has apples, Box A has bananas, Box B has the mix"
    scoring:
      method: "keyword_match"
      required_keywords:
        - "C"
        - "apples"
        - "A"
        - "bananas"
        - "B"
        - "mix"
      min_keywords: 5  # Must match at least 5 of 6 keywords

  instruction_following:
    prompt: |
      Follow these instructions exactly:
      1. Start your response with the word "RESPONSE"
      2. List exactly 3 colors, one per line, numbered 1-3
      3. Each color must be a single word
      4. End your response with the word "DONE"
      5. Do not include any other text
    expected_answer: "RESPONSE\n1. <color>\n2. <color>\n3. <color>\nDONE"
    scoring:
      method: "constraint_check"
      # MF-1: Named constraint checkers replace eval() expressions.
      # Each constraint specifies a `checker` (key in CONSTRAINT_CHECKERS)
      # and an `arg` (value passed to the checker function).
      constraints:
        - name: "starts_with_response"
          checker: "starts_with"
          arg: "RESPONSE"
        - name: "ends_with_done"
          checker: "ends_with"
          arg: "DONE"
        - name: "has_three_numbered"
          checker: "regex_count_eq"
          arg:
            pattern: "^\\d+\\."
            count: 3
        - name: "no_extra_text"
          checker: "line_count_le"
          arg: 6

  code_generation:
    prompt: |
      Write a Python function called `fibonacci` that takes an integer n
      and returns the nth Fibonacci number (0-indexed, so fibonacci(0)=0,
      fibonacci(1)=1, fibonacci(6)=8). Use iteration, not recursion.
      Return ONLY the function, no explanation.
    expected_answer: "def fibonacci(n):"
    scoring:
      method: "code_validation"
      test_cases:
        - input: 0
          expected: 0
        - input: 1
          expected: 1
        - input: 6
          expected: 8
        - input: 10
          expected: 55

  creative_divergence:
    prompt: |
      List exactly 5 unusual uses for a paperclip. Each use must be
      a single sentence. Number them 1-5.
    expected_answer: "5 distinct creative uses"
    scoring:
      method: "diversity_score"
      min_items: 5
      uniqueness_threshold: 0.3  # Pairwise TF-IDF distance must be > 0.3

  tool_use:
    prompt: |
      I need you to perform these steps in order:
      1. Calculate 17 * 23
      2. Report the result as: "RESULT: <number>"
      3. State whether the result is prime or composite as: "TYPE: <prime|composite>"
    expected_answer: "RESULT: 391\nTYPE: composite"
    scoring:
      method: "exact_fields"
      fields:
        - name: "result"
          pattern: "RESULT:\\s*(\\d+)"
          expected: "391"
        - name: "type"
          pattern: "TYPE:\\s*(\\w+)"
          expected: "composite"
```

---

## Part 4: CanaryRunner Engine

### 4.1 `engine/canary_runner.py`

```python
"""Fixed micro-benchmark runner for model fingerprinting.
Spec reference: Section 19.1 (Model Fingerprinting).

Executes 5 fixed canary tasks at session start to produce a ModelFingerprint.
Tasks are FIXED and never change — they are the ruler, not the subject.

Key constraints:
- Total budget: < 5000 tokens
- Total runtime: < 2 minutes
- Canary expectations loaded from core/canary-expectations.yaml
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import logging
import re
import time
from datetime import datetime, timezone

import yaml

from ..models.base import generate_id
from ..models.environment import (
    CanaryResult,
    CanarySuiteResult,
    ModelExecuteFn,
    ModelFingerprint,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.canary_runner")

# Scoring method constants
SCORE_KEYWORD_MATCH = "keyword_match"
SCORE_CONSTRAINT_CHECK = "constraint_check"
SCORE_CODE_VALIDATION = "code_validation"
SCORE_DIVERSITY = "diversity_score"
SCORE_EXACT_FIELDS = "exact_fields"

# Canary task names — fixed, never changed
CANARY_TASKS = [
    "reasoning",
    "instruction_following",
    "code_generation",
    "creative_divergence",
    "tool_use",
]

# Mapping from canary task name to fingerprint dimension
TASK_TO_DIMENSION = {
    "reasoning": "reasoning_score",
    "instruction_following": "instruction_score",
    "code_generation": "code_score",
    "creative_divergence": "creative_score",
    "tool_use": "tool_score",
}

# MF-1: Named constraint checkers replace eval().
# Each checker takes (output: str, arg: Any) -> bool.
CONSTRAINT_CHECKERS: dict[str, object] = {
    "starts_with": lambda output, arg: output.strip().startswith(arg),
    "ends_with": lambda output, arg: output.strip().endswith(arg),
    "regex_count_eq": lambda output, arg: (
        len(re.findall(arg["pattern"], output, re.MULTILINE)) == arg["count"]
    ),
    "line_count_le": lambda output, arg: len(output.strip().split("\n")) <= arg,
}


class CanaryRunner:
    """Executes fixed micro-benchmark tasks and produces ModelFingerprints.

    Design invariants:
    - Canary tasks are FIXED — loaded from core/canary-expectations.yaml
    - Budget-capped: entire suite < 5000 tokens, < 2 minutes
    - Scoring is deterministic: no LLM-as-judge, only pattern matching
    - Results stored to state/environment/canary-results/
    - SF-10: Expectations file hash verified at startup
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        model_id: str = "unknown",  # SF-9: Accept model_id as parameter
    ):
        self.yaml_store = yaml_store
        self._domain = domain
        self._model_id = model_id
        self._state_base = f"instances/{domain}/state/environment"
        self.yaml_store.ensure_dir(self._state_base)
        self.yaml_store.ensure_dir(f"{self._state_base}/canary-results")

        # Load canary expectations (fail-loud if missing)
        raw = yaml_store.read_raw("core/canary-expectations.yaml")
        expectations = raw.get("canary_expectations")
        if expectations is None:
            raise ValueError(
                "core/canary-expectations.yaml missing 'canary_expectations' section"
            )
        self._expectations: dict = expectations

        # SF-10: Verify expectations hash to detect accidental modifications
        self._verify_expectations_hash(raw)

        # Load config (SF-5: config loading consolidated — see EnvironmentMonitor)
        config_raw = yaml_store.read_raw("core/environment-awareness.yaml")
        ea = config_raw.get("environment_awareness", {})
        cs = ea.get("canary_suite", {})
        self._max_total_tokens = int(cs.get("max_total_tokens", 5000))
        self._max_runtime_seconds = int(cs.get("max_runtime_seconds", 120))
        self._per_task_token_cap = int(cs.get("per_task_token_cap", 1200))
        self._pass_score = float(cs.get("pass_score", 0.7))
        # SF-7/IFM-16: Use drift_detection.history_size for canary result trimming
        dd = ea.get("drift_detection", {})
        self._history_size = int(dd.get("history_size", 10))

    def _verify_expectations_hash(self, raw: dict) -> None:
        """SF-10: Verify SHA-256 of canary expectations against stored hash.

        On first run, stores the hash. On subsequent runs, compares and
        logs CRITICAL if the expectations have been modified.
        """
        canonical = yaml.dump(
            raw.get("canary_expectations", {}),
            default_flow_style=False,
            sort_keys=True,
        )
        current_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        hash_path = f"{self._state_base}/canary-expectations-hash.yaml"
        try:
            stored = self.yaml_store.read_raw(hash_path)
            stored_hash = stored.get("sha256", "")
            if stored_hash != current_hash:
                logger.critical(
                    "CANARY EXPECTATIONS MODIFIED! "
                    f"Stored hash: {stored_hash[:16]}..., "
                    f"Current hash: {current_hash[:16]}... "
                    "This invalidates all historical fingerprint comparisons. "
                    "If this change is intentional, delete "
                    f"{hash_path} and restart."
                )
                raise ValueError(
                    "Canary expectations hash mismatch — "
                    "historical fingerprint comparisons invalidated. "
                    "See log for details."
                )
        except FileNotFoundError:
            # First run — store hash
            self.yaml_store.write_raw(hash_path, {"sha256": current_hash})
            logger.info(
                f"Canary expectations hash stored: {current_hash[:16]}..."
            )

    def run_suite(self, execute_fn: ModelExecuteFn) -> CanarySuiteResult:
        """Execute all 5 canary tasks and return suite result.

        Args:
            execute_fn: Callable that takes (prompt: str, max_tokens: int)
                and returns (output: str, tokens_used: int).
                This is the model execution interface — injected to allow
                testing without actual model calls.

        Returns:
            CanarySuiteResult with all 5 results and computed fingerprint.

        Raises:
            RuntimeError: If suite exceeds budget or timeout.
        """
        results: list[CanaryResult] = []
        total_tokens = 0
        suite_start = time.monotonic()

        for task_name in CANARY_TASKS:
            # Check budget before each task
            if total_tokens >= self._max_total_tokens:
                logger.warning(
                    f"Canary suite budget exhausted at {total_tokens} tokens "
                    f"after {len(results)} tasks"
                )
                # Score remaining tasks as 0
                result = CanaryResult(
                    task_name=task_name,
                    expected=self._get_expected(task_name),
                    actual="[BUDGET_EXHAUSTED]",
                    score=0.0,
                    tokens_used=0,
                    latency_ms=0,
                )
                results.append(result)
                continue

            # Check timeout
            elapsed = time.monotonic() - suite_start
            if elapsed > self._max_runtime_seconds:
                logger.warning(
                    f"Canary suite timeout at {elapsed:.1f}s "
                    f"after {len(results)} tasks"
                )
                result = CanaryResult(
                    task_name=task_name,
                    expected=self._get_expected(task_name),
                    actual="[TIMEOUT]",
                    score=0.0,
                    tokens_used=0,
                    latency_ms=0,
                )
                results.append(result)
                continue

            # Execute canary task
            prompt = self._get_prompt(task_name)
            task_start = time.monotonic()
            try:
                output, tokens_used = execute_fn(prompt, self._per_task_token_cap)
            except Exception as e:
                logger.error(f"Canary task '{task_name}' execution failed: {e}")
                output = f"[ERROR: {e}]"
                tokens_used = 0
            task_elapsed_ms = int((time.monotonic() - task_start) * 1000)

            # Score the output
            score = self._score_task(task_name, output)
            total_tokens += tokens_used

            result = CanaryResult(
                task_name=task_name,
                expected=self._get_expected(task_name),
                actual=output[:500],  # Truncate for storage
                score=score,
                tokens_used=tokens_used,
                latency_ms=task_elapsed_ms,
            )
            results.append(result)

            logger.info(
                f"Canary '{task_name}': score={score:.2f}, "
                f"tokens={tokens_used}, latency={task_elapsed_ms}ms"
            )

        # Compute fingerprint from results
        fingerprint = self._compute_fingerprint(results)
        total_latency_ms = int((time.monotonic() - suite_start) * 1000)
        all_passed = all(r.score >= self._pass_score for r in results)

        now = datetime.now(timezone.utc)
        suite_result = CanarySuiteResult(
            created_at=now,
            results=results,
            fingerprint=fingerprint,
            total_tokens=total_tokens,
            total_latency_ms=total_latency_ms,
            all_passed=all_passed,
        )

        # Persist result
        self._store_result(suite_result)

        logger.info(
            f"Canary suite complete: all_passed={all_passed}, "
            f"total_tokens={total_tokens}, latency={total_latency_ms}ms"
        )

        return suite_result

    def _get_prompt(self, task_name: str) -> str:
        """Get the prompt for a canary task."""
        task = self._expectations.get(task_name)
        if task is None:
            raise ValueError(f"Unknown canary task: {task_name}")
        prompt = task.get("prompt")
        if prompt is None:
            raise ValueError(f"Canary task '{task_name}' missing 'prompt' field")
        return prompt.strip()

    def _get_expected(self, task_name: str) -> str:
        """Get the expected answer string for a canary task."""
        task = self._expectations.get(task_name)
        if task is None:
            return ""
        return task.get("expected_answer", "")

    def _score_task(self, task_name: str, output: str) -> float:
        """Score a canary task output against expectations.

        Scoring is deterministic — no LLM-as-judge. Uses pattern matching,
        keyword matching, constraint checking, or code validation.
        """
        task = self._expectations.get(task_name)
        if task is None:
            return 0.0
        scoring = task.get("scoring", {})
        method = scoring.get("method", "keyword_match")

        if method == SCORE_KEYWORD_MATCH:
            return self._score_keyword_match(output, scoring)
        elif method == SCORE_CONSTRAINT_CHECK:
            return self._score_constraint_check(output, scoring)
        elif method == SCORE_CODE_VALIDATION:
            return self._score_code_validation(output, scoring)
        elif method == SCORE_DIVERSITY:
            return self._score_diversity(output, scoring)
        elif method == SCORE_EXACT_FIELDS:
            return self._score_exact_fields(output, scoring)
        else:
            logger.warning(f"Unknown scoring method '{method}' for task '{task_name}'")
            return 0.0

    @staticmethod
    def _score_keyword_match(output: str, scoring: dict) -> float:
        """Score by counting required keywords present in output."""
        keywords = scoring.get("required_keywords", [])
        min_keywords = scoring.get("min_keywords", len(keywords))
        if not keywords:
            return 0.0
        output_lower = output.lower()
        matched = sum(1 for kw in keywords if kw.lower() in output_lower)
        if matched >= min_keywords:
            return 1.0
        return matched / len(keywords)

    @staticmethod
    def _score_constraint_check(output: str, scoring: dict) -> float:
        """Score by checking named constraints on output.

        MF-1: Uses CONSTRAINT_CHECKERS dict instead of eval().
        Each constraint specifies a `checker` name and `arg` value.
        IFM-18: Logs warning on individual constraint failures.
        """
        constraints = scoring.get("constraints", [])
        if not constraints:
            return 0.0
        passed = 0
        for constraint in constraints:
            checker_name = constraint.get("checker", "")
            arg = constraint.get("arg")
            name = constraint.get("name", checker_name)
            checker_fn = CONSTRAINT_CHECKERS.get(checker_name)
            if checker_fn is None:
                logger.warning(
                    f"Unknown constraint checker '{checker_name}' "
                    f"in constraint '{name}' — scoring 0"
                )
                continue
            try:
                result = checker_fn(output, arg)
                if result:
                    passed += 1
            except Exception as e:
                logger.warning(
                    f"Constraint checker '{name}' raised {type(e).__name__}: "
                    f"{e} — scoring 0 for this constraint"
                )
        return passed / len(constraints)

    @staticmethod
    def _score_code_validation(output: str, scoring: dict) -> float:
        """Score by extracting code and running test cases.

        MF-2: Uses concurrent.futures.ProcessPoolExecutor with 2-second
        timeout instead of bare exec(). Namespace restricted to builtins only.
        """
        test_cases = scoring.get("test_cases", [])
        if not test_cases:
            return 0.0

        # Extract the function from output
        # Look for def fibonacci(...): block
        code_match = re.search(
            r"(def\s+fibonacci\s*\([^)]*\)\s*:.*?)(?=\n\S|\Z)",
            output,
            re.DOTALL,
        )
        if not code_match:
            # Try extracting from code block
            block_match = re.search(r"```(?:python)?\s*\n(.*?)```", output, re.DOTALL)
            if block_match:
                code = block_match.group(1).strip()
            else:
                code = output.strip()
        else:
            code = code_match.group(1).strip()

        # MF-2: Run in subprocess with timeout to prevent infinite loops
        # and restrict namespace (no imports available)
        def _run_tests(code: str, test_cases: list[dict]) -> float:
            """Execute code and test cases in restricted namespace."""
            namespace: dict = {"__builtins__": {"range": range, "int": int}}
            try:
                exec(code, namespace)  # noqa: S102 — sandboxed canary eval
            except Exception:
                return 0.0
            func = namespace.get("fibonacci")
            if func is None or not callable(func):
                return 0.0
            passed = 0
            for tc in test_cases:
                try:
                    result = func(tc["input"])
                    if result == tc["expected"]:
                        passed += 1
                except Exception:
                    pass
            return passed / len(test_cases)

        try:
            with concurrent.futures.ProcessPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_run_tests, code, test_cases)
                return future.result(timeout=2.0)
        except concurrent.futures.TimeoutError:
            logger.warning("Code validation timed out after 2 seconds")
            return 0.0
        except Exception as e:
            logger.warning(f"Code validation failed: {e}")
            return 0.0

    @staticmethod
    def _score_diversity(output: str, scoring: dict) -> float:
        """Score creative output by counting distinct items and uniqueness."""
        min_items = scoring.get("min_items", 5)

        # Extract numbered items
        items = re.findall(r"^\d+[.)]\s*(.+)$", output, re.MULTILINE)
        if len(items) < min_items:
            # Partial credit for having some items
            return len(items) / min_items * 0.5

        # Check uniqueness: simple word-set Jaccard distance
        scores: list[float] = []
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                words_i = set(items[i].lower().split())
                words_j = set(items[j].lower().split())
                if not words_i or not words_j:
                    continue
                intersection = len(words_i & words_j)
                union = len(words_i | words_j)
                jaccard_sim = intersection / union if union > 0 else 0.0
                distance = 1.0 - jaccard_sim
                scores.append(distance)

        if not scores:
            return 0.5  # Can't assess diversity with no pairs

        avg_distance = sum(scores) / len(scores)
        uniqueness_threshold = scoring.get("uniqueness_threshold", 0.3)

        if avg_distance >= uniqueness_threshold:
            return 1.0
        return avg_distance / uniqueness_threshold

    @staticmethod
    def _score_exact_fields(output: str, scoring: dict) -> float:
        """Score by extracting specific fields and comparing to expected values."""
        fields = scoring.get("fields", [])
        if not fields:
            return 0.0
        matched = 0
        for field in fields:
            pattern = field.get("pattern", "")
            expected = field.get("expected", "")
            match = re.search(pattern, output)
            if match and match.group(1).strip() == expected:
                matched += 1
        return matched / len(fields)

    def _compute_fingerprint(self, results: list[CanaryResult]) -> ModelFingerprint:
        """Build ModelFingerprint from canary results.

        SF-9: Uses self._model_id (injected via constructor) instead of
        hardcoded model ID.
        """
        scores: dict[str, float] = {}
        for r in results:
            dim = TASK_TO_DIMENSION.get(r.task_name)
            if dim:
                scores[dim] = r.score

        latencies = [r.latency_ms for r in results if r.latency_ms > 0]
        token_counts = [r.tokens_used for r in results if r.tokens_used > 0]

        return ModelFingerprint(
            created_at=datetime.now(timezone.utc),
            model_id=self._model_id,
            reasoning_score=scores.get("reasoning_score", 0.0),
            instruction_score=scores.get("instruction_score", 0.0),
            code_score=scores.get("code_score", 0.0),
            creative_score=scores.get("creative_score", 0.0),
            tool_score=scores.get("tool_score", 0.0),
            avg_latency_ms=int(sum(latencies) / len(latencies)) if latencies else 0,
            avg_output_tokens=int(sum(token_counts) / len(token_counts)) if token_counts else 0,
        )

    def _store_result(self, suite_result: CanarySuiteResult) -> None:
        """Persist canary suite result to YAML.

        IFM-01: Appends generate_id() suffix to prevent timestamp collisions.
        SF-7/IFM-16: Trims old results to history_size.
        """
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_suffix = generate_id("cr").split("-")[-1]  # 8-char hex
        path = (
            f"{self._state_base}/canary-results/"
            f"{timestamp_str}_{unique_suffix}.yaml"
        )
        self.yaml_store.write(path, suite_result)
        self._trim_canary_results()

    def _trim_canary_results(self) -> None:
        """SF-7/IFM-16: Remove oldest canary results exceeding history_size."""
        results_dir = f"{self._state_base}/canary-results"
        try:
            files = self.yaml_store.list_dir(results_dir)
        except (NotADirectoryError, FileNotFoundError):
            return
        yaml_files = sorted(
            f for f in files if f.endswith(".yaml") and not f.endswith(".lock")
        )
        while len(yaml_files) > self._history_size:
            oldest = yaml_files.pop(0)
            try:
                self.yaml_store.delete(f"{results_dir}/{oldest}")
            except FileNotFoundError:
                pass  # Already deleted (race condition)

    def get_latest_result(self) -> CanarySuiteResult | None:
        """Load the most recent canary suite result, or None if none exist."""
        results_dir = f"{self._state_base}/canary-results"
        try:
            files = self.yaml_store.list_dir(results_dir)
        except (NotADirectoryError, FileNotFoundError):
            return None
        yaml_files = [f for f in files if f.endswith(".yaml") and not f.endswith(".lock")]
        if not yaml_files:
            return None
        latest = sorted(yaml_files)[-1]
        return self.yaml_store.read(
            f"{results_dir}/{latest}", CanarySuiteResult
        )
```

---

## Part 5: DriftDetector Engine

### 5.1 `engine/drift_detector.py`

```python
"""Fingerprint storage, comparison, and drift detection.
Spec reference: Section 19.1 (Model Fingerprinting — drift_detection).

Stores fingerprint history, computes Euclidean distance between current
and baseline (median of last N), flags drift when distance > threshold.
Also tracks Claude Code version changes.

Key design decisions:
- Baseline is median of last N fingerprints (not just last one) — smooths noise
- Per-dimension delta reported for targeted revalidation
- Version comparison is zero-cost (subprocess, no tokens)
"""
from __future__ import annotations

import logging
import platform
import subprocess
import sys
from datetime import datetime, timezone

from ..models.base import generate_id
from ..models.environment import (
    DriftDetection,
    ModelFingerprint,
    VersionInfo,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.drift_detector")


class DriftDetector:
    """Detects model capability drift and version changes.

    Design invariants:
    - Fingerprint history limited to `history_size` entries (bounded storage)
    - Baseline computed as per-dimension median of last `baseline_window` fingerprints
    - Version info persisted and compared at every session start
    - All state persisted to YAML via YamlStore
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta"):
        self.yaml_store = yaml_store
        self._domain = domain
        self._state_base = f"instances/{domain}/state/environment"
        self.yaml_store.ensure_dir(self._state_base)
        self.yaml_store.ensure_dir(f"{self._state_base}/fingerprints")

        # Load config
        config_raw = yaml_store.read_raw("core/environment-awareness.yaml")
        ea = config_raw.get("environment_awareness", {})
        dd = ea.get("drift_detection", {})
        self._threshold = float(dd.get("threshold", 0.15))
        self._history_size = int(dd.get("history_size", 10))
        self._baseline_window = int(dd.get("baseline_window", 5))
        self._per_dim_alert = float(dd.get("per_dimension_alert", 0.10))

        vt = ea.get("version_tracking", {})
        self._version_command = str(vt.get("version_command", "claude --version"))
        self._version_timeout = int(vt.get("version_timeout_seconds", 5))

    def store_fingerprint(self, fingerprint: ModelFingerprint) -> None:
        """Store a fingerprint to history. Trims to history_size.

        IFM-01: Appends generate_id() suffix for collision avoidance.
        MF-6/IFM-02: last-fingerprint.yaml stored in state dir, not core/.
        """
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_suffix = generate_id("fp").split("-")[-1]  # 8-char hex
        path = (
            f"{self._state_base}/fingerprints/"
            f"{timestamp_str}_{unique_suffix}.yaml"
        )
        self.yaml_store.write(path, fingerprint)

        # Trim old fingerprints if exceeding history_size
        self._trim_history()

        # MF-6/IFM-02: Write to state dir, not core/ (which is read-only config)
        self.yaml_store.write_raw(
            f"{self._state_base}/last-fingerprint.yaml",
            {
                "timestamp": fingerprint.created_at.isoformat(),
                "claude_version": self.check_claude_version(),
                "path": path,
            },
        )

    def load_fingerprint_history(self) -> list[ModelFingerprint]:
        """Load all stored fingerprints, sorted chronologically (oldest first)."""
        fp_dir = f"{self._state_base}/fingerprints"
        try:
            files = self.yaml_store.list_dir(fp_dir)
        except (NotADirectoryError, FileNotFoundError):
            return []
        yaml_files = sorted(
            f for f in files if f.endswith(".yaml") and not f.endswith(".lock")
        )
        fingerprints: list[ModelFingerprint] = []
        for fname in yaml_files:
            try:
                fp = self.yaml_store.read(f"{fp_dir}/{fname}", ModelFingerprint)
                fingerprints.append(fp)
            except Exception as e:
                logger.warning(f"Skipping corrupt fingerprint {fname}: {e}")
        return fingerprints

    def compute_baseline(self, history: list[ModelFingerprint]) -> ModelFingerprint | None:
        """Compute baseline fingerprint as per-dimension median of last N.

        Returns None if history is empty.
        """
        if not history:
            return None

        window = history[-self._baseline_window:]
        if not window:
            return None

        # Compute median for each dimension
        def median(values: list[float]) -> float:
            s = sorted(values)
            n = len(s)
            if n % 2 == 1:
                return s[n // 2]
            return (s[n // 2 - 1] + s[n // 2]) / 2

        reasoning_scores = [fp.reasoning_score for fp in window]
        instruction_scores = [fp.instruction_score for fp in window]
        code_scores = [fp.code_score for fp in window]
        creative_scores = [fp.creative_score for fp in window]
        tool_scores = [fp.tool_score for fp in window]
        latencies = [fp.avg_latency_ms for fp in window]
        output_tokens = [fp.avg_output_tokens for fp in window]

        return ModelFingerprint(
            created_at=datetime.now(timezone.utc),
            model_id=window[-1].model_id,  # Use most recent model_id
            reasoning_score=median(reasoning_scores),
            instruction_score=median(instruction_scores),
            code_score=median(code_scores),
            creative_score=median(creative_scores),
            tool_score=median(tool_scores),
            avg_latency_ms=int(median([float(x) for x in latencies])),
            avg_output_tokens=int(median([float(x) for x in output_tokens])),
        )

    def detect_drift(self, current: ModelFingerprint) -> DriftDetection:
        """Compare current fingerprint against stored baseline.

        If no history exists, baseline is the current fingerprint itself
        (distance = 0, no drift detected).

        IFM-10: Suppresses drift detection when history has fewer entries
        than baseline_window to prevent false alarms on early sessions.
        """
        history = self.load_fingerprint_history()
        baseline = self.compute_baseline(history)

        if baseline is None:
            # First run — no baseline, no drift
            return DriftDetection(
                current=current,
                baseline=current,
                distance=0.0,
                threshold=self._threshold,
                drift_detected=False,
                affected_dimensions=[],
            )

        distance = current.distance_to(baseline)
        deltas = current.per_dimension_delta(baseline)

        # Identify affected dimensions
        affected: list[str] = []
        for dim_name, delta in deltas.items():
            if abs(delta) > self._per_dim_alert:
                affected.append(dim_name)

        drift_detected = distance > self._threshold

        # IFM-10: Suppress false drift alarms when insufficient history.
        # With fewer than baseline_window fingerprints, the baseline is
        # statistically unreliable and would cause false alarms on the
        # second session.
        if len(history) < self._baseline_window:
            drift_detected = False

        if drift_detected:
            logger.warning(
                f"Model drift detected: distance={distance:.4f} "
                f"(threshold={self._threshold}), "
                f"affected_dimensions={affected}"
            )
        else:
            logger.info(
                f"No drift: distance={distance:.4f} "
                f"(threshold={self._threshold})"
            )

        return DriftDetection(
            current=current,
            baseline=baseline,
            distance=distance,
            threshold=self._threshold,
            drift_detected=drift_detected,
            affected_dimensions=affected,
        )

    def check_version(self) -> tuple[VersionInfo, list[str]]:
        """Check current environment version and compare to stored version.

        Returns:
            Tuple of (current VersionInfo, list of changed fields).
            Changed fields is empty if no previous version stored.
        """
        current = VersionInfo(
            claude_code_version=self.check_claude_version(),
            python_version=platform.python_version(),
            os_info=f"{platform.system()} {platform.release()}",
            timestamp=datetime.now(timezone.utc),
        )

        # Load previous version
        # IFM-19: Catch all exceptions (FileNotFoundError on first run,
        # ValidationError on schema change, yaml.ScannerError on corruption).
        version_path = f"{self._state_base}/version-info.yaml"
        changes: list[str] = []
        try:
            previous = self.yaml_store.read(version_path, VersionInfo)
            changes = current.differs_from(previous)
            if changes:
                logger.warning(
                    f"Version changes detected: {changes}. "
                    f"Previous: {previous.claude_code_version}, "
                    f"Current: {current.claude_code_version}"
                )
        except FileNotFoundError:
            logger.info("No previous version info — first run")
        except Exception as e:
            logger.warning(
                f"Could not load previous version info, treating as first run: "
                f"{type(e).__name__}: {e}"
            )

        # Store current version
        self.yaml_store.write(version_path, current)

        return current, changes

    def check_claude_version(self) -> str:
        """Get Claude Code version string via subprocess."""
        parts = self._version_command.split()
        try:
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=self._version_timeout,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def _trim_history(self) -> None:
        """Remove oldest fingerprints exceeding history_size."""
        fp_dir = f"{self._state_base}/fingerprints"
        try:
            files = self.yaml_store.list_dir(fp_dir)
        except (NotADirectoryError, FileNotFoundError):
            return
        yaml_files = sorted(
            f for f in files if f.endswith(".yaml") and not f.endswith(".lock")
        )
        while len(yaml_files) > self._history_size:
            oldest = yaml_files.pop(0)
            try:
                self.yaml_store.delete(f"{fp_dir}/{oldest}")
            except FileNotFoundError:
                pass  # Already deleted (race condition)
```

---

## Part 6: RevalidationEngine

### 6.1 `engine/revalidation_engine.py`

```python
"""Change-triggered revalidation pipeline.
Spec reference: Section 19.3 (Change-Triggered Revalidation).

When drift or version change is detected, assesses scope, runs targeted
revalidation capped at 10% of session budget, classifies adaptation.

Key design decisions:
- Budget-capped: max 10% of session token budget
- Trigger classification determines scope (what to revalidate)
- Adaptation response is classified, not acted upon (Phase 2.5 detects, Phase 4+ acts)
- Exception: degraded_major and broken trigger quarantine to Ring 3

IFM-28: Migration note — Constructor signature changed in Phase 2.5:
  - Added `capability_tracker` parameter (optional, None if Phase 2 not active)
  - All callers (EnvironmentMonitor.__init__) must update their instantiation.
  Callers to update:
    - engine/environment_monitor.py: EnvironmentMonitor.__init__()
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..engine.budget_tracker import BudgetTracker
from ..engine.canary_runner import CanaryRunner
from ..engine.capability_tracker import CapabilityTracker
from ..models.base import generate_id
from ..models.environment import (
    AdaptationResponse,
    DriftDetection,
    ModelExecuteFn,
    ModelFingerprint,
    RevalidationResult,
    RevalidationTrigger,
    VersionInfo,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.revalidation_engine")

# IFM-07: Mapping from assess_scope() output to _classify_task_type() names.
# assess_scope() uses capability-oriented names; the Orchestrator uses
# task_type names. This mapping bridges the two vocabularies.
SCOPE_TO_TASK_TYPE: dict[str, str] = {
    "decomposition": "decomposition",
    "evolution_proposal": "evolution",
    "skill_validation": "validation",
    "review": "review",
    "simple_fix": "bugfix",
    "feature": "feature",
    "research": "research",
    "code_generation": "code_generation",
    "canary_suite": "canary",
    "tool_integrations": "tool_integration",
    "mcp_tools": "mcp_tool",
}


class RevalidationEngine:
    """Runs targeted revalidation after detected environment changes.

    Design invariants:
    - Revalidation budget capped at `budget_cap_pct` of session window remaining
    - Scope is determined by trigger type (model drift -> skills, version change -> tools)
    - Results persisted to state/environment/revalidation-history/
    - Does NOT autonomously modify skills (Phase 4+) except quarantine
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        budget_tracker: BudgetTracker,
        capability_tracker: CapabilityTracker | None = None,
        domain: str = "meta",
    ):
        self.yaml_store = yaml_store
        self.budget_tracker = budget_tracker
        self.capability_tracker = capability_tracker
        self._domain = domain
        self._state_base = f"instances/{domain}/state/environment"
        self.yaml_store.ensure_dir(f"{self._state_base}/revalidation-history")

        # Load config
        config_raw = yaml_store.read_raw("core/environment-awareness.yaml")
        ea = config_raw.get("environment_awareness", {})
        rv = ea.get("revalidation", {})
        self._budget_cap_pct = float(rv.get("budget_cap_pct", 0.10))
        self._min_budget = int(rv.get("min_budget_tokens", 2000))
        # MF-4: Threshold names now match AdaptationResponse levels clearly
        self._improved_threshold = float(rv.get("improved_threshold", 0.05))
        self._degraded_minor_threshold = float(rv.get("degraded_minor_threshold", 0.05))
        self._degraded_major_threshold = float(rv.get("degraded_major_threshold", 0.15))
        self._broken_threshold = float(rv.get("broken_threshold", 0.30))

    def compute_budget_cap(self) -> int:
        """Compute the token budget cap for revalidation.

        Returns max tokens allowed, based on current window remaining.
        """
        window = self.budget_tracker.get_window()
        cap = int(window.remaining_tokens * self._budget_cap_pct)
        return max(cap, 0)

    def should_revalidate(self, budget_cap: int) -> bool:
        """Check if revalidation is feasible given budget constraints."""
        if budget_cap < self._min_budget:
            logger.info(
                f"Skipping revalidation: budget cap {budget_cap} "
                f"< minimum {self._min_budget}"
            )
            return False
        return True

    def assess_scope(
        self,
        trigger: RevalidationTrigger,
        drift: DriftDetection | None = None,
        version_changes: list[str] | None = None,
    ) -> list[str]:
        """Determine what needs revalidation based on trigger type.

        Args:
            trigger: What caused the revalidation.
            drift: DriftDetection result (for model_drift triggers).
            version_changes: List of changed version fields.

        Returns:
            List of scope items (skill names, tool names, or categories).
        """
        scope: list[str] = []

        if trigger == RevalidationTrigger.MODEL_DRIFT:
            if drift is not None and drift.affected_dimensions:
                # Map affected dimensions to skills that depend on them
                dim_to_skills = {
                    "reasoning": ["decomposition", "evolution_proposal", "research"],
                    "instruction": ["skill_validation", "review"],
                    "code": ["simple_fix", "feature", "code_generation"],
                    "creative": ["evolution_proposal", "research"],
                    "tool": ["canary_suite", "feature"],
                }
                for dim in drift.affected_dimensions:
                    skills = dim_to_skills.get(dim, [])
                    for skill in skills:
                        if skill not in scope:
                            scope.append(skill)
            else:
                # Generic drift — revalidate all Ring 2 skills
                scope = [
                    "decomposition",
                    "evolution_proposal",
                    "skill_validation",
                    "review",
                    "simple_fix",
                    "feature",
                    "research",
                ]

        elif trigger == RevalidationTrigger.VERSION_CHANGE:
            if version_changes and "claude_code_version" in version_changes:
                # Claude Code update — revalidate tool integrations
                scope = ["tool_integrations", "mcp_tools", "canary_suite"]
            else:
                # Python or OS update — lighter revalidation
                scope = ["canary_suite"]

        elif trigger == RevalidationTrigger.MCP_CHANGE:
            scope = ["tool_integrations", "mcp_tools"]

        elif trigger == RevalidationTrigger.PERFORMANCE_DROP:
            # Scope should be determined by caller based on which skills dropped
            scope = ["affected_skills"]  # Placeholder — caller overrides

        elif trigger == RevalidationTrigger.MANUAL:
            # Full revalidation
            scope = [
                "decomposition",
                "evolution_proposal",
                "skill_validation",
                "review",
                "simple_fix",
                "feature",
                "research",
                "canary_suite",
                "tool_integrations",
            ]

        logger.info(f"Revalidation scope for {trigger.value}: {scope}")
        return scope

    def classify_adaptation(
        self,
        pre_fingerprint: ModelFingerprint | None,
        post_fingerprint: ModelFingerprint | None,
        drift: DriftDetection | None = None,
    ) -> AdaptationResponse:
        """Classify the adaptation response based on fingerprint comparison.

        Compares pre and post revalidation fingerprints to determine
        whether the environment change was positive, neutral, or negative.

        MF-4: Uses separate broken_threshold. Threshold names match
        AdaptationResponse levels: improved > +5%, degraded_minor > -5%,
        degraded_major > -15%, broken > -30%.

        IFM-20: Also checks per-dimension extremes. If any single dimension
        drops more than degraded_minor_threshold, the classification is
        at least DEGRADED_MINOR, even if the mean is above threshold.
        """
        if pre_fingerprint is None or post_fingerprint is None:
            # Cannot classify without both fingerprints
            return AdaptationResponse.UNCHANGED

        distance = post_fingerprint.distance_to(pre_fingerprint)
        deltas = post_fingerprint.per_dimension_delta(pre_fingerprint)

        # Compute mean delta (positive = improvement)
        mean_delta = sum(deltas.values()) / len(deltas) if deltas else 0.0

        # MF-4: Classify based on mean delta with distinct thresholds
        if mean_delta > self._improved_threshold:
            classification = AdaptationResponse.IMPROVED
        elif mean_delta < -self._broken_threshold:
            classification = AdaptationResponse.BROKEN
        elif mean_delta < -self._degraded_major_threshold:
            classification = AdaptationResponse.DEGRADED_MAJOR
        elif mean_delta < -self._degraded_minor_threshold:
            classification = AdaptationResponse.DEGRADED_MINOR
        else:
            classification = AdaptationResponse.UNCHANGED

        # IFM-20: Per-dimension extreme check. If any single dimension
        # drops more than degraded_minor_threshold, escalate to at least
        # DEGRADED_MINOR to prevent mean masking per-dimension degradation.
        if classification in (
            AdaptationResponse.UNCHANGED,
            AdaptationResponse.IMPROVED,
        ):
            worst_drop = min(deltas.values()) if deltas else 0.0
            if worst_drop < -self._degraded_minor_threshold:
                logger.warning(
                    f"Per-dimension extreme detected: worst_drop={worst_drop:.4f} "
                    f"< -{self._degraded_minor_threshold}. "
                    f"Escalating from {classification.value} to DEGRADED_MINOR."
                )
                classification = AdaptationResponse.DEGRADED_MINOR

        return classification

    def run_revalidation(
        self,
        trigger: RevalidationTrigger,
        trigger_detail: str,
        drift: DriftDetection | None = None,
        version_changes: list[str] | None = None,
        pre_fingerprint: ModelFingerprint | None = None,
        execute_fn: ModelExecuteFn | None = None,
        canary_runner: CanaryRunner | None = None,
    ) -> RevalidationResult:
        """Execute a full revalidation cycle.

        MF-5/IFM-06: Now actually calls execute_fn via canary_runner to produce
        a post_fingerprint for meaningful adaptation classification. Also tracks
        tokens_used from the canary re-run.

        Args:
            trigger: What caused the revalidation.
            trigger_detail: Human-readable description of the trigger.
            drift: DriftDetection result (if applicable).
            version_changes: Changed version fields (if applicable).
            pre_fingerprint: Fingerprint before the change.
            execute_fn: Model execution function for re-running canaries.
            canary_runner: CanaryRunner instance for re-running canary suite.

        Returns:
            RevalidationResult with classification and actions taken.
        """
        budget_cap = self.compute_budget_cap()
        now = datetime.now(timezone.utc)

        if not self.should_revalidate(budget_cap):
            result = RevalidationResult(
                created_at=now,
                trigger=trigger,
                trigger_detail=f"{trigger_detail} [SKIPPED: insufficient budget]",
                scope=[],
                tokens_used=0,
                budget_cap=budget_cap,
                adaptation=AdaptationResponse.UNCHANGED,
                actions_taken=["revalidation_skipped_budget"],
            )
            self._store_result(result)
            return result

        # Assess scope
        scope = self.assess_scope(trigger, drift, version_changes)

        # Track tokens used during revalidation
        tokens_used = 0
        actions_taken: list[str] = []
        affected_skills: list[str] = []
        post_fingerprint: ModelFingerprint | None = None

        # MF-5/IFM-06: Re-run canary suite to get post_fingerprint.
        # Without this, classify_adaptation() always returns UNCHANGED
        # because post_fingerprint would be None.
        if execute_fn is not None and canary_runner is not None:
            try:
                suite_result = canary_runner.run_suite(execute_fn)
                post_fingerprint = suite_result.fingerprint
                tokens_used = suite_result.total_tokens
                actions_taken.append(
                    f"canary_rerun:tokens={tokens_used}"
                )
            except Exception as e:
                logger.warning(
                    f"Canary re-run during revalidation failed: {e}"
                )
                actions_taken.append(f"canary_rerun_failed:{e}")
        else:
            if execute_fn is None:
                logger.warning(
                    "Revalidation: no execute_fn provided, "
                    "cannot produce post_fingerprint"
                )
            if canary_runner is None:
                logger.warning(
                    "Revalidation: no canary_runner provided, "
                    "cannot produce post_fingerprint"
                )

        # If capability tracker is available, check skill performance
        if self.capability_tracker is not None:
            for skill_name in scope:
                if skill_name in (
                    "tool_integrations", "mcp_tools", "affected_skills"
                ):
                    continue  # These are categories, not individual skills
                entry = self.capability_tracker.get_capability(skill_name)
                if entry.attempts > 0 and entry.success_rate < 0.5:
                    affected_skills.append(skill_name)
                    actions_taken.append(
                        f"flagged_weak_skill:{skill_name} "
                        f"(success_rate={entry.success_rate:.2f})"
                    )

        # Classify adaptation
        adaptation = self.classify_adaptation(
            pre_fingerprint, post_fingerprint, drift
        )

        # Take actions based on adaptation classification
        if adaptation == AdaptationResponse.IMPROVED:
            actions_taken.append("updated_baselines")
            actions_taken.append("logged_improvement")
        elif adaptation == AdaptationResponse.UNCHANGED:
            actions_taken.append("updated_fingerprint")
        elif adaptation == AdaptationResponse.DEGRADED_MINOR:
            actions_taken.append("logged_warning")
            actions_taken.append("adjusted_confidence_estimates")
        elif adaptation == AdaptationResponse.DEGRADED_MAJOR:
            for skill in affected_skills:
                actions_taken.append(f"quarantine_to_ring3:{skill}")
            actions_taken.append("alert_human")
        elif adaptation == AdaptationResponse.BROKEN:
            for skill in affected_skills:
                actions_taken.append(f"disabled_capability:{skill}")
            actions_taken.append("create_workaround_task")
            actions_taken.append("alert_human_urgent")

        result = RevalidationResult(
            created_at=now,
            trigger=trigger,
            trigger_detail=trigger_detail,
            scope=scope,
            tokens_used=tokens_used,
            budget_cap=budget_cap,
            pre_fingerprint=pre_fingerprint,
            post_fingerprint=post_fingerprint,
            adaptation=adaptation,
            affected_skills=affected_skills,
            actions_taken=actions_taken,
        )

        self._store_result(result)

        logger.info(
            f"Revalidation complete: trigger={trigger.value}, "
            f"adaptation={adaptation.value}, "
            f"actions={len(actions_taken)}, tokens={tokens_used}"
        )

        return result

    def get_revalidation_history(self, limit: int = 10) -> list[RevalidationResult]:
        """Load recent revalidation results."""
        history_dir = f"{self._state_base}/revalidation-history"
        try:
            files = self.yaml_store.list_dir(history_dir)
        except (NotADirectoryError, FileNotFoundError):
            return []
        yaml_files = sorted(
            (f for f in files if f.endswith(".yaml") and not f.endswith(".lock")),
            reverse=True,
        )
        results: list[RevalidationResult] = []
        for fname in yaml_files[:limit]:
            try:
                r = self.yaml_store.read(
                    f"{history_dir}/{fname}", RevalidationResult
                )
                results.append(r)
            except Exception as e:
                logger.warning(f"Skipping corrupt revalidation result {fname}: {e}")
        return results

    def _store_result(self, result: RevalidationResult) -> None:
        """Persist revalidation result to YAML.

        IFM-01: Appends generate_id() suffix to prevent timestamp collisions.
        SF-6: Trims history to last 50 entries after storing.
        """
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_suffix = generate_id("rv").split("-")[-1]  # 8-char hex
        path = (
            f"{self._state_base}/revalidation-history/"
            f"{timestamp_str}_{unique_suffix}.yaml"
        )
        self.yaml_store.write(path, result)
        self._trim_history()

    def _trim_history(self, max_entries: int = 50) -> None:
        """SF-6: Trim revalidation history to last max_entries results."""
        history_dir = f"{self._state_base}/revalidation-history"
        try:
            files = self.yaml_store.list_dir(history_dir)
        except (NotADirectoryError, FileNotFoundError):
            return
        yaml_files = sorted(
            f for f in files if f.endswith(".yaml") and not f.endswith(".lock")
        )
        while len(yaml_files) > max_entries:
            oldest = yaml_files.pop(0)
            try:
                self.yaml_store.delete(f"{history_dir}/{oldest}")
            except FileNotFoundError:
                pass  # Already deleted (race condition)
```

---

## Part 7: PerformanceMonitor

### 7.1 `engine/performance_monitor.py`

```python
"""Continuous performance monitoring for skills, tools, and structured traces.
Spec reference: Section 19.2 (Continuous Performance Monitoring).

Tracks per-skill success rates (rolling window of 20), per-tool reliability,
and structured traces at 3 levels (operational, cognitive, contextual).

Key constraints:
- Rolling window size is configurable (default 20)
- Alert on > 10pp drop from established baseline
- Tool quarantine at < 50% success rate
- Trace retention: last 100 tasks
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime, timezone

from ..audit.logger import AuditLogger
from ..models.audit import LogStream, TraceLogEntry
from ..models.base import generate_id
from ..models.environment import (
    PerformanceAlert,
    PerformanceTrack,
    SkillPerformance,
    ToolPerformance,
    TraceEntry,
    TraceLevel,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.performance_monitor")

# SF-2/IFM-22: PerformanceAlert is now a FrameworkModel defined in
# models/environment.py. No longer a plain class in this module.


class PerformanceMonitor:
    """Tracks per-skill and per-tool performance with alerts.

    Design invariants:
    - Rolling window for skills (configurable, default 20)
    - Baseline established after first `window_size` attempts
    - Alerts surfaced but not acted upon (Phase 2.5 detects, Phase 4+ acts)
    - Tool quarantine flag set but not enforced (Phase 3.5 enforces)
    - State persisted to YAML for crash recovery
    - Traces logged via AuditLogger for structured debugging
    - SF-4/IFM-25: All _track mutations guarded by threading.Lock
    - MF-7/IFM-15: Dirty flag + batch writes (persist every 5 updates)
    - IFM-08: Uses injected AuditLogger instead of separate JsonlWriter
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        audit_logger: AuditLogger | None = None,  # IFM-08: Injected
    ):
        self.yaml_store = yaml_store
        self._domain = domain
        self._state_base = f"instances/{domain}/state/environment"
        self.yaml_store.ensure_dir(self._state_base)

        # Load config
        config_raw = yaml_store.read_raw("core/environment-awareness.yaml")
        ea = config_raw.get("environment_awareness", {})
        pm = ea.get("performance_monitoring", {})
        self._skill_window_size = int(pm.get("skill_window_size", 20))
        self._skill_alert_drop = float(pm.get("skill_alert_drop_pp", 10)) / 100.0
        self._tool_alert_drop = float(pm.get("tool_alert_drop_pp", 15)) / 100.0
        self._tool_quarantine_threshold = float(
            pm.get("tool_quarantine_threshold", 0.5)
        )
        self._trace_retention = int(pm.get("trace_retention_tasks", 100))

        # SF-4/IFM-25: Thread safety for _track mutations
        self._lock = threading.Lock()

        # Load persisted state
        self._track = self._load_track()

        # MF-7/IFM-15: Dirty flag + batch writes
        self._dirty_count = 0
        self._BATCH_WRITE_THRESHOLD = 5  # Persist every 5 updates

        # Pending alerts (consumed by EnvironmentMonitor on each check)
        self._pending_alerts: list[PerformanceAlert] = []

        # IFM-08: Use injected AuditLogger for traces (no separate JsonlWriter)
        self._audit_logger = audit_logger

        # In-memory trace task IDs for retention management
        self._traced_task_ids: deque[str] = deque(maxlen=self._trace_retention)

    def record_skill_outcome(
        self,
        skill_name: str,
        success: bool,
        tokens_used: int = 0,
        latency_ms: int = 0,
    ) -> SkillPerformance:
        """Record a skill execution outcome.

        SF-4/IFM-25: All _track mutations guarded by self._lock.
        MF-7/IFM-15: Uses dirty flag + batch writes.
        IFM-17: Deduplicates alerts by target_name + alert_type.

        Args:
            skill_name: Name/type of the skill (matches task_type).
            success: Whether the execution succeeded.
            tokens_used: Tokens consumed by this execution.
            latency_ms: Wall-clock time in milliseconds.

        Returns:
            Updated SkillPerformance record.
        """
        with self._lock:
            if skill_name not in self._track.skills:
                self._track.skills[skill_name] = SkillPerformance(
                    skill_name=skill_name
                )
            skill = self._track.skills[skill_name]

            # Update rolling window
            skill.recent_outcomes.append(success)
            if len(skill.recent_outcomes) > self._skill_window_size:
                skill.recent_outcomes = skill.recent_outcomes[
                    -self._skill_window_size:
                ]

            # Update totals
            skill.total_attempts += 1
            if success:
                skill.total_successes += 1
            skill.total_tokens += tokens_used
            skill.total_latency_ms += latency_ms
            skill.last_updated = datetime.now(timezone.utc)

            # Establish baseline after first full window
            if (
                skill.baseline_success_rate is None
                and len(skill.recent_outcomes) >= self._skill_window_size
            ):
                skill.baseline_success_rate = skill.success_rate
                logger.info(
                    f"Skill baseline established: {skill_name} = "
                    f"{skill.baseline_success_rate:.2%}"
                )

            # Check for alerts
            drop = skill.success_rate_drop
            if drop is not None and drop > self._skill_alert_drop:
                alert = PerformanceAlert(
                    alert_type="skill_degradation",
                    target_name=skill_name,
                    message=(
                        f"Skill '{skill_name}' success rate dropped "
                        f"{drop:.1%} from baseline "
                        f"({skill.baseline_success_rate:.2%} -> "
                        f"{skill.success_rate:.2%})"
                    ),
                    current_rate=skill.success_rate,
                    baseline_rate=skill.baseline_success_rate,
                    timestamp=datetime.now(timezone.utc),
                )
                # IFM-17: Deduplicate by target_name + alert_type
                existing_keys = {
                    (a.target_name, a.alert_type) for a in self._pending_alerts
                }
                if (skill_name, "skill_degradation") not in existing_keys:
                    self._pending_alerts.append(alert)
                logger.warning(alert.message)

            self._maybe_save_track()
            return skill

    def record_tool_outcome(
        self,
        tool_name: str,
        success: bool,
        timed_out: bool = False,
        tokens_used: int = 0,
    ) -> ToolPerformance:
        """Record a tool execution outcome.

        SF-4/IFM-25: Guarded by self._lock.
        IFM-17: Deduplicates alerts.

        Args:
            tool_name: Name of the tool.
            success: Whether the tool call succeeded.
            timed_out: Whether the call timed out.
            tokens_used: Tokens consumed by this tool call.

        Returns:
            Updated ToolPerformance record.
        """
        with self._lock:
            if tool_name not in self._track.tools:
                self._track.tools[tool_name] = ToolPerformance(tool_name=tool_name)
            tool = self._track.tools[tool_name]

            tool.total_calls += 1
            if success:
                tool.successful_calls += 1
            else:
                tool.failed_calls += 1
            if timed_out:
                tool.timeout_calls += 1
            tool.total_tokens += tokens_used
            tool.last_updated = datetime.now(timezone.utc)

            # Check for quarantine threshold
            if (
                tool.total_calls >= 10
                and tool.success_rate < self._tool_quarantine_threshold
            ):
                alert = PerformanceAlert(
                    alert_type="tool_quarantine",
                    target_name=tool_name,
                    message=(
                        f"Tool '{tool_name}' success rate "
                        f"{tool.success_rate:.2%} < quarantine threshold "
                        f"{self._tool_quarantine_threshold:.2%} "
                        f"({tool.total_calls} calls)"
                    ),
                    current_rate=tool.success_rate,
                    baseline_rate=None,
                    timestamp=datetime.now(timezone.utc),
                )
                # IFM-17: Deduplicate by target_name + alert_type
                existing_keys = {
                    (a.target_name, a.alert_type) for a in self._pending_alerts
                }
                if (tool_name, "tool_quarantine") not in existing_keys:
                    self._pending_alerts.append(alert)
                logger.warning(alert.message)

            self._maybe_save_track()
            return tool

    def record_trace(
        self,
        level: TraceLevel,
        task_id: str,
        category: str,
        detail: dict,
        tokens_used: int = 0,
        latency_ms: int = 0,
    ) -> None:
        """Record a structured trace entry.

        IFM-08: Uses injected AuditLogger instead of separate JsonlWriter
        to avoid duplicate trace writers and inconsistent log files.

        Args:
            level: Trace level (operational, cognitive, contextual).
            task_id: ID of the task being traced.
            category: Category of the trace (e.g., "tool_call", "reasoning_step").
            detail: Structured detail data.
            tokens_used: Tokens consumed.
            latency_ms: Time taken.
        """
        if self._audit_logger is None:
            return  # No audit logger available — traces not recorded

        now = datetime.now(timezone.utc)

        # Write to JSONL trace log via AuditLogger
        log_entry = TraceLogEntry(
            id=generate_id("trace"),
            timestamp=now,
            level=level.value,
            detail={
                "task_id": task_id,
                "category": category,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                **detail,
            },
        )
        self._audit_logger.log_trace(log_entry)

        # Track task for retention
        if task_id not in self._traced_task_ids:
            self._traced_task_ids.append(task_id)

    def get_pending_alerts(self) -> list[PerformanceAlert]:
        """Consume and return pending alerts. Clears the alert queue."""
        alerts = list(self._pending_alerts)
        self._pending_alerts.clear()
        return alerts

    def get_skill_performance(self, skill_name: str) -> SkillPerformance | None:
        """Get performance record for a specific skill."""
        return self._track.skills.get(skill_name)

    def get_tool_performance(self, tool_name: str) -> ToolPerformance | None:
        """Get performance record for a specific tool."""
        return self._track.tools.get(tool_name)

    def get_all_skill_performances(self) -> dict[str, SkillPerformance]:
        """Get all skill performance records."""
        return dict(self._track.skills)

    def get_all_tool_performances(self) -> dict[str, ToolPerformance]:
        """Get all tool performance records."""
        return dict(self._track.tools)

    def get_degraded_skills(self) -> list[SkillPerformance]:
        """Get skills whose success rate dropped > alert threshold from baseline."""
        degraded: list[SkillPerformance] = []
        for skill in self._track.skills.values():
            drop = skill.success_rate_drop
            if drop is not None and drop > self._skill_alert_drop:
                degraded.append(skill)
        return sorted(degraded, key=lambda s: s.success_rate)

    def get_quarantined_tools(self) -> list[ToolPerformance]:
        """Get tools below quarantine threshold with sufficient data."""
        quarantined: list[ToolPerformance] = []
        for tool in self._track.tools.values():
            if (
                tool.total_calls >= 10
                and tool.success_rate < self._tool_quarantine_threshold
            ):
                quarantined.append(tool)
        return quarantined

    def get_task_count(self) -> int:
        """SF-8: Public getter for tasks-since-last-check counter.
        Replaces direct access to self._track.tasks_since_last_check."""
        return self._track.tasks_since_last_check

    def increment_task_counter(self) -> int:
        """Increment and return the tasks-since-last-check counter."""
        with self._lock:
            self._track.tasks_since_last_check += 1
            self._maybe_save_track()
            return self._track.tasks_since_last_check

    def reset_task_counter(self) -> None:
        """Reset the tasks-since-last-check counter (after periodic check)."""
        with self._lock:
            self._track.tasks_since_last_check = 0
            self._flush_track()

    def _load_track(self) -> PerformanceTrack:
        """Load performance track from YAML or create new.

        IFM-03: YamlStore.read() uses strict=False in model_validate(),
        which overrides the class-level strict=True. This is intentional
        for YAML roundtrip compatibility with nested models.
        Test requirement: verify PerformanceTrack roundtrip (write then read)
        produces identical data.

        IFM-04: Trims recent_outcomes to skill_window_size after load,
        in case the config changed between sessions.
        """
        path = f"{self._state_base}/performance-track.yaml"
        try:
            track = self.yaml_store.read(path, PerformanceTrack)
            # IFM-04: Trim recent_outcomes if config changed
            for skill in track.skills.values():
                if len(skill.recent_outcomes) > self._skill_window_size:
                    skill.recent_outcomes = skill.recent_outcomes[
                        -self._skill_window_size:
                    ]
            return track
        except Exception as e:
            if not isinstance(e, FileNotFoundError):
                logger.warning(
                    f"Corrupt performance track, resetting: {e}"
                )
            return PerformanceTrack(created_at=datetime.now(timezone.utc))

    def _maybe_save_track(self) -> None:
        """MF-7/IFM-15: Batch writes — only persist every N updates.

        Reduces YAML write frequency to prevent excessive I/O.
        Caller must hold self._lock.
        """
        self._dirty_count += 1
        if self._dirty_count >= self._BATCH_WRITE_THRESHOLD:
            self._flush_track_unlocked()

    def _flush_track(self) -> None:
        """Force-persist performance track to YAML (acquires lock)."""
        with self._lock:
            self._flush_track_unlocked()

    def _flush_track_unlocked(self) -> None:
        """Force-persist performance track to YAML (caller holds lock)."""
        self._track.updated_at = datetime.now(timezone.utc)
        self.yaml_store.write(
            f"{self._state_base}/performance-track.yaml",
            self._track,
        )
        self._dirty_count = 0

    def flush(self) -> None:
        """Public flush — persist any dirty state immediately.

        MF-7/IFM-15: Called by EnvironmentMonitor at session end or
        before periodic checks to ensure no data is lost.
        """
        self._flush_track()
```

---

## Part 8: EnvironmentMonitor Upgrade

### 8.1 `engine/environment_monitor.py` (Full Rewrite)

This replaces the Phase 0 stub entirely. The EnvironmentMonitor becomes the orchestrator for all Phase 2.5 components.

```python
"""Environment awareness orchestrator.
Spec reference: Section 19 (Environment Awareness & Self-Benchmarking).

Phase 2.5: Full rewrite replacing Phase 0 stub.
Orchestrates CanaryRunner, DriftDetector, RevalidationEngine,
and PerformanceMonitor. Provides session_start() and periodic_check()
entry points for the Orchestrator.

Key responsibilities:
- Session start: run canaries, check drift, check version
- Periodic check: every N tasks, re-run canaries and check performance
- Audit logging: all events to ENVIRONMENT stream
- Alert aggregation: surface performance alerts to orchestrator
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from ..audit.logger import AuditLogger
from ..engine.budget_tracker import BudgetTracker
from ..engine.canary_runner import CanaryRunner
from ..engine.capability_tracker import CapabilityTracker
from ..engine.drift_detector import DriftDetector
from ..engine.performance_monitor import PerformanceMonitor
from ..engine.revalidation_engine import RevalidationEngine
from ..models.audit import EnvironmentLogEntry
from ..models.base import generate_id
from ..models.environment import (
    AdaptationResponse,
    DriftDetection,
    EnvironmentCheckResult,
    ModelExecuteFn,
    ModelFingerprint,
    RevalidationTrigger,
    VersionInfo,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.environment_monitor")

# SF-2/IFM-23: EnvironmentCheckResult is now a FrameworkModel defined in
# models/environment.py. No longer a plain class in this module.


class EnvironmentMonitor:
    """Orchestrates all Phase 2.5 environment awareness components.

    Design invariants:
    - session_start() runs at every session start (unless canary recency skip)
    - periodic_check() runs every `periodic_check_interval` completed tasks
    - All events logged to ENVIRONMENT audit stream
    - Alerts aggregated from PerformanceMonitor and surfaced to Orchestrator
    - Budget awareness: canary suite and revalidation respect budget caps
    - IFM-09: Stores execute_fn for use by periodic_check()
    - SF-5/IFM-05: Config loaded once and sections injected to sub-components
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        budget_tracker: BudgetTracker,
        audit_logger: AuditLogger | None = None,
        capability_tracker: CapabilityTracker | None = None,
        domain: str = "meta",
        model_id: str = "unknown",  # SF-9: Passed to CanaryRunner
    ):
        self.yaml_store = yaml_store
        self.budget_tracker = budget_tracker
        self.audit_logger = audit_logger
        self._domain = domain

        # IFM-09: Store execute_fn for periodic_check(). Set by session_start().
        self._execute_fn: ModelExecuteFn | None = None

        # SF-5/IFM-05: Load config ONCE and inject parsed sections to sub-components
        config_raw = yaml_store.read_raw("core/environment-awareness.yaml")
        ea = config_raw.get("environment_awareness", {})
        cs = ea.get("canary_suite", {})
        dd = ea.get("drift_detection", {})
        self._skip_if_recent_hours = float(cs.get("skip_if_recent_hours", 5))
        self._periodic_interval = int(dd.get("periodic_check_interval", 50))

        # Initialize sub-components (config sections already loaded above)
        self.canary_runner = CanaryRunner(yaml_store, domain, model_id=model_id)
        self.drift_detector = DriftDetector(yaml_store, domain)
        self.revalidation_engine = RevalidationEngine(
            yaml_store, budget_tracker, capability_tracker, domain
        )
        # IFM-08: Pass audit_logger to PerformanceMonitor (no separate JsonlWriter)
        self.performance_monitor = PerformanceMonitor(
            yaml_store, domain, audit_logger=audit_logger
        )

    def session_start(self, execute_fn: ModelExecuteFn) -> EnvironmentCheckResult:
        """Run environment checks at session start.

        Steps:
        1. Check Claude Code version
        2. Determine if canary run needed (recency check)
        3. Run canary suite if needed
        4. Detect drift against stored baseline
        5. Trigger revalidation if drift or version change detected
        6. Log all events to ENVIRONMENT audit stream

        Args:
            execute_fn: Model execution function for canary tasks.
                Signature: (prompt: str, max_tokens: int) -> (output: str, tokens_used: int)

        Returns:
            EnvironmentCheckResult with all findings.
        """
        # IFM-09: Store execute_fn for periodic_check() to use later
        self._execute_fn = execute_fn

        result = EnvironmentCheckResult()

        # Step 1: Version check (zero cost)
        version_info, version_changes = self.drift_detector.check_version()
        result.version_info = version_info
        result.version_changes = version_changes

        if version_changes:
            self._log_event(
                "version_change",
                {
                    "changes": version_changes,
                    "current": version_info.claude_code_version,
                },
            )

        # Step 2: Recency check
        if not version_changes and not self._should_run_canary():
            result.skipped = True
            result.skip_reason = "recent_fingerprint_valid"
            logger.info(
                "Canary suite skipped: recent fingerprint still valid"
            )
            self._log_event("canary_skipped", {"reason": result.skip_reason})
            return result

        # Step 3: Run canary suite
        logger.info("Running canary suite at session start...")
        suite_result = self.canary_runner.run_suite(execute_fn)
        result.fingerprint = suite_result.fingerprint
        result.canary_all_passed = suite_result.all_passed

        self._log_event(
            "fingerprint",
            {
                "scores": suite_result.task_scores,
                "total_tokens": suite_result.total_tokens,
                "all_passed": suite_result.all_passed,
            },
        )

        # Step 4: Detect drift
        drift = self.drift_detector.detect_drift(suite_result.fingerprint)
        result.drift = drift
        result.drift_detected = drift.drift_detected

        # Store the new fingerprint
        self.drift_detector.store_fingerprint(suite_result.fingerprint)

        if drift.drift_detected:
            self._log_event(
                "drift",
                {
                    "distance": drift.distance,
                    "threshold": drift.threshold,
                    "affected_dimensions": drift.affected_dimensions,
                },
            )

        # Step 5: Trigger revalidation if needed
        trigger: RevalidationTrigger | None = None
        trigger_detail = ""

        if drift.drift_detected:
            trigger = RevalidationTrigger.MODEL_DRIFT
            trigger_detail = (
                f"Drift distance {drift.distance:.4f} > "
                f"threshold {drift.threshold}. "
                f"Affected: {drift.affected_dimensions}"
            )
        elif version_changes:
            trigger = RevalidationTrigger.VERSION_CHANGE
            trigger_detail = f"Version changes: {version_changes}"

        if trigger is not None:
            reval_result = self.revalidation_engine.run_revalidation(
                trigger=trigger,
                trigger_detail=trigger_detail,
                drift=drift if drift.drift_detected else None,
                version_changes=version_changes if version_changes else None,
                pre_fingerprint=drift.baseline if drift.drift_detected else None,
                execute_fn=execute_fn,
                canary_runner=self.canary_runner,  # MF-5: pass for post_fingerprint
            )
            result.revalidation_triggered = True
            result.adaptation = reval_result.adaptation

            self._log_event(
                "revalidation",
                {
                    "trigger": trigger.value,
                    "adaptation": reval_result.adaptation.value,
                    "scope": reval_result.scope,
                    "tokens_used": reval_result.tokens_used,
                    "actions": reval_result.actions_taken,
                },
            )

        logger.info(
            f"Session start check complete: "
            f"drift={result.drift_detected}, "
            f"version_changes={result.version_changes}, "
            f"revalidation={result.revalidation_triggered}"
        )

        return result

    def periodic_check(
        self, execute_fn: ModelExecuteFn | None = None
    ) -> EnvironmentCheckResult:
        """Run periodic environment check (every N tasks).

        Lighter than session_start: focuses on canary re-run and
        performance alerts. Called by Orchestrator after task completion.

        IFM-09: Falls back to stored self._execute_fn if execute_fn not
        provided. Checks execute_fn is not None before proceeding.
        IFM-21: Degraded skills now trigger revalidation (not just logging).

        Args:
            execute_fn: Model execution function. If None, uses stored
                execute_fn from session_start().

        Returns:
            EnvironmentCheckResult with findings.
        """
        # IFM-09: Use stored execute_fn if not provided
        fn = execute_fn or self._execute_fn
        if fn is None:
            logger.warning(
                "periodic_check: no execute_fn available — "
                "skipping canary re-run"
            )
            result = EnvironmentCheckResult(
                skipped=True,
                skip_reason="no_execute_fn",
            )
            return result

        result = EnvironmentCheckResult()

        # Flush pending performance data before check
        self.performance_monitor.flush()

        # Run canary suite
        logger.info(
            f"Running periodic environment check "
            f"(interval: {self._periodic_interval} tasks)"
        )
        suite_result = self.canary_runner.run_suite(fn)
        result.fingerprint = suite_result.fingerprint
        result.canary_all_passed = suite_result.all_passed

        # Detect drift
        drift = self.drift_detector.detect_drift(suite_result.fingerprint)
        result.drift = drift
        result.drift_detected = drift.drift_detected

        # Store fingerprint
        self.drift_detector.store_fingerprint(suite_result.fingerprint)

        # Collect performance alerts
        result.alerts = self.performance_monitor.get_pending_alerts()

        # Trigger revalidation on drift
        if drift.drift_detected:
            reval_result = self.revalidation_engine.run_revalidation(
                trigger=RevalidationTrigger.MODEL_DRIFT,
                trigger_detail=(
                    f"Periodic check drift: {drift.distance:.4f} > "
                    f"{drift.threshold}"
                ),
                drift=drift,
                pre_fingerprint=drift.baseline,
                execute_fn=fn,
                canary_runner=self.canary_runner,  # MF-5
            )
            result.revalidation_triggered = True
            result.adaptation = reval_result.adaptation

            self._log_event(
                "periodic_revalidation",
                {
                    "drift_distance": drift.distance,
                    "adaptation": reval_result.adaptation.value,
                },
            )

        # IFM-21: Degraded skills trigger PERFORMANCE_DROP revalidation
        degraded = self.performance_monitor.get_degraded_skills()
        if degraded:
            skill_names = [s.skill_name for s in degraded]
            self._log_event(
                "performance_alert",
                {
                    "degraded_skills": skill_names,
                    "rates": {
                        s.skill_name: s.success_rate for s in degraded
                    },
                },
            )

            # IFM-21: Trigger revalidation for degraded skills
            if not result.revalidation_triggered:
                reval_result = self.revalidation_engine.run_revalidation(
                    trigger=RevalidationTrigger.PERFORMANCE_DROP,
                    trigger_detail=(
                        f"Degraded skills: {skill_names}"
                    ),
                    execute_fn=fn,
                    canary_runner=self.canary_runner,
                )
                result.revalidation_triggered = True
                result.adaptation = reval_result.adaptation

                self._log_event(
                    "performance_revalidation",
                    {
                        "degraded_skills": skill_names,
                        "adaptation": reval_result.adaptation.value,
                    },
                )

        # Reset task counter
        self.performance_monitor.reset_task_counter()

        return result

    def should_run_periodic_check(self) -> bool:
        """Check if periodic check is due based on task count.

        SF-8: Uses get_task_count() getter instead of accessing
        private _track attribute directly.
        """
        count = self.performance_monitor.get_task_count()
        return count >= self._periodic_interval

    def on_task_complete(
        self,
        task_type: str,
        success: bool,
        tokens_used: int = 0,
        latency_ms: int = 0,
    ) -> None:
        """Called after each task completion to update performance tracking.

        This is the primary integration point with the Orchestrator.
        """
        self.performance_monitor.record_skill_outcome(
            skill_name=task_type,
            success=success,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )
        self.performance_monitor.increment_task_counter()

    def on_tool_call(
        self,
        tool_name: str,
        success: bool,
        timed_out: bool = False,
        tokens_used: int = 0,
    ) -> None:
        """Called after each tool call to update tool performance tracking."""
        self.performance_monitor.record_tool_outcome(
            tool_name=tool_name,
            success=success,
            timed_out=timed_out,
            tokens_used=tokens_used,
        )

    def _should_run_canary(self) -> bool:
        """Check if canary suite needs to run (recency check).

        MF-6/IFM-02: Reads from state dir, not core/.
        IFM-14: Catches TypeError for timezone-naive datetime comparison.
        """
        try:
            # MF-6: Read from state dir (not core/)
            state_base = f"instances/{self._domain}/state/environment"
            data = self.yaml_store.read_raw(
                f"{state_base}/last-fingerprint.yaml"
            )
            last_run = datetime.fromisoformat(data.get("timestamp", ""))
            elapsed_hours = (
                datetime.now(timezone.utc) - last_run
            ).total_seconds() / 3600
            if elapsed_hours < self._skip_if_recent_hours:
                stored_version = data.get("claude_version", "")
                current_version = self.drift_detector.check_claude_version()
                if stored_version == current_version:
                    return False
        except (FileNotFoundError, ValueError, KeyError, TypeError):
            # IFM-14: TypeError catches timezone-naive vs timezone-aware
            # datetime comparison failures
            pass
        return True

    def _log_event(self, event_type: str, detail: dict) -> None:
        """Log an environment event to the ENVIRONMENT audit stream."""
        if self.audit_logger is None:
            return
        entry = EnvironmentLogEntry(
            id=generate_id("env"),
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            detail=detail,
        )
        self.audit_logger.log_environment(entry)
```

---

## Part 9: Modifications to Existing Files

### 9.1 Changes to `models/environment.py`

**Action:** Replace the entire file contents with the model definitions from Part 2.

The file currently contains `ModelFingerprint`, `CanaryResult`, and `DriftDetection`. The Phase 2.5 version adds the `per_dimension_delta()` and `score_vector()` methods to `ModelFingerprint`, and adds all new models: `CanarySuiteResult`, `VersionInfo`, `SkillPerformance`, `ToolPerformance`, `PerformanceTrack`, `RevalidationTrigger`, `AdaptationResponse`, `RevalidationResult`, `BenchmarkTask`, `BenchmarkSuiteResult`, `TraceLevel`, `TraceEntry`.

**Backward compatibility:** The existing `ModelFingerprint`, `CanaryResult`, and `DriftDetection` classes retain their existing fields and behavior. New methods (`per_dimension_delta`, `score_vector`) are additive. Existing YAML files will load correctly.

### 9.2 Changes to `audit/tree_viewer.py`

Add environment stream rendering to the `AuditTreeViewer`. The following methods are added:

```python
    # Add to render_session() — in the stream loop, add environment handling:
    # After the existing `if stream == LogStream.DIVERSITY:` block:

    def render_session(
        self,
        since: datetime,
        until: datetime | None = None,
        streams: list[LogStream] | None = None,
    ) -> None:
        """Render session audit tree to terminal."""
        if streams is None:
            streams = [
                LogStream.TASKS,
                LogStream.DECISIONS,
                LogStream.DIVERSITY,
                LogStream.ENVIRONMENT,  # Phase 2.5 addition
            ]

        tree = Tree(f"[bold]Session audit: {since.isoformat()}[/bold]")

        for stream in streams:
            entries = self.logger.query(
                stream, since=since, until=until, limit=200
            )
            if not entries:
                continue

            if stream == LogStream.DIVERSITY:
                self._render_diversity_branch(tree, entries)
            elif stream == LogStream.ENVIRONMENT:
                self._render_environment_branch(tree, entries)
            else:
                branch = tree.add(
                    f"[cyan]{stream.value}[/cyan] ({len(entries)} entries)"
                )
                for entry in entries:
                    ts = entry.get("timestamp", "?")[:19]
                    event = entry.get(
                        "event", entry.get("decision_type", "?")
                    )
                    actor = entry.get("actor", "?")
                    branch.add(f"[dim]{ts}[/dim] {event} -- {actor}")

        self.console.print(tree)
```

Add the new `_render_environment_branch` method:

```python
    def _render_environment_branch(
        self, tree: Tree, entries: list[dict]
    ) -> None:
        """Render environment entries with drift/version color coding."""
        branch = tree.add(
            f"[cyan]environment[/cyan] ({len(entries)} events)"
        )
        for entry in entries:
            ts = entry.get("timestamp", "?")[:19]
            event_type = entry.get("event_type", "?")
            detail = entry.get("detail", {})

            if event_type == "drift":
                distance = detail.get("distance", 0)
                dims = detail.get("affected_dimensions", [])
                color = "red bold" if distance > 0.2 else "yellow"
                node = branch.add(
                    f"[dim]{ts}[/dim] "
                    f"[{color}]DRIFT[/{color}] "
                    f"distance={distance:.4f}, "
                    f"affected={dims}"
                )
            elif event_type == "version_change":
                changes = detail.get("changes", [])
                node = branch.add(
                    f"[dim]{ts}[/dim] "
                    f"[yellow]VERSION CHANGE[/yellow] {changes}"
                )
            elif event_type == "fingerprint":
                scores = detail.get("scores", {})
                passed = detail.get("all_passed", False)
                color = "green" if passed else "yellow"
                node = branch.add(
                    f"[dim]{ts}[/dim] "
                    f"[{color}]FINGERPRINT[/{color}] "
                    f"passed={passed}"
                )
                for task_name, score in scores.items():
                    score_color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"
                    node.add(f"{task_name}: [{score_color}]{score:.2f}[/{score_color}]")
            elif event_type == "revalidation":
                adaptation = detail.get("adaptation", "?")
                adapt_color = {
                    "improved": "green",
                    "unchanged": "white",
                    "degraded_minor": "yellow",
                    "degraded_major": "red",
                    "broken": "red bold",
                }.get(adaptation, "white")
                node = branch.add(
                    f"[dim]{ts}[/dim] "
                    f"REVALIDATION "
                    f"[{adapt_color}]{adaptation}[/{adapt_color}]"
                )
                for action in detail.get("actions", []):
                    node.add(f"  {action}")
            elif event_type == "performance_alert":
                skills = detail.get("degraded_skills", [])
                node = branch.add(
                    f"[dim]{ts}[/dim] "
                    f"[yellow]PERF ALERT[/yellow] "
                    f"degraded: {skills}"
                )
            else:
                branch.add(
                    f"[dim]{ts}[/dim] {event_type}: "
                    f"{str(detail)[:80]}"
                )
```

Add environment summary table method:

```python
    def render_environment_summary(
        self,
        since: datetime,
        until: datetime | None = None,
    ) -> None:
        """Render environment metrics summary as a table."""
        entries = self.logger.query(
            LogStream.ENVIRONMENT, since=since, until=until, limit=100
        )

        table = Table(title="Environment Events")
        table.add_column("Time", style="dim", width=19)
        table.add_column("Event", style="cyan")
        table.add_column("Detail", style="white")
        table.add_column("Status", justify="center")

        for entry in entries:
            ts = entry.get("timestamp", "?")[:19]
            event_type = entry.get("event_type", "?")
            detail = entry.get("detail", {})

            if event_type == "drift":
                detail_str = f"distance={detail.get('distance', 0):.4f}"
                status = "[red]DRIFT[/red]"
            elif event_type == "version_change":
                detail_str = str(detail.get("changes", []))
                status = "[yellow]CHANGED[/yellow]"
            elif event_type == "fingerprint":
                detail_str = f"tokens={detail.get('total_tokens', 0)}"
                passed = detail.get("all_passed", False)
                status = "[green]PASS[/green]" if passed else "[yellow]PARTIAL[/yellow]"
            elif event_type == "revalidation":
                detail_str = detail.get("trigger", "?")
                adapt = detail.get("adaptation", "?")
                color = "green" if adapt == "improved" else "red" if "degraded" in adapt else "white"
                status = f"[{color}]{adapt}[/{color}]"
            else:
                detail_str = str(detail)[:40]
                status = "-"

            table.add_row(ts, event_type, detail_str, status)

        self.console.print(table)
```

Also update the `render_timeline()` method to handle environment events:

```python
    # In render_timeline(), add to the stream dispatch after the existing
    # "elif stream == 'resources':" block:

            elif stream == "environment":
                event_type = entry.get("event_type", "?")
                detail = entry.get("detail", {})
                if event_type == "drift":
                    label = f"DRIFT distance={detail.get('distance', 0):.4f}"
                elif event_type == "version_change":
                    label = f"VERSION {detail.get('changes', [])}"
                elif event_type == "revalidation":
                    label = f"REVAL {detail.get('adaptation', '?')}"
                else:
                    label = f"{event_type}"
```

### 9.3 Changes to `audit/logger.py`

**No changes needed.** The `AuditLogger` already has `log_environment(entry: EnvironmentLogEntry)` and `log_trace(entry: TraceLogEntry)` methods with `JsonlWriter` instances for both streams. Phase 2.5 uses these existing interfaces. IFM-08: `PerformanceMonitor` now uses the injected `AuditLogger.log_trace()` instead of creating a separate `JsonlWriter`.

### 9.4 Changes to `engine/orchestrator.py`

Add `EnvironmentMonitor` integration. The Orchestrator should call `EnvironmentMonitor.session_start()` during initialization and `on_task_complete()` after each task.

Add to `__init__()`:

```python
    def __init__(
        self,
        # ... existing parameters ...
        environment_monitor: EnvironmentMonitor | None = None,  # Phase 2.5
    ):
        # ... existing assignments ...
        self.environment_monitor = environment_monitor
```

Add TYPE_CHECKING import (SF-1: ModelExecuteFn Protocol):

```python
if TYPE_CHECKING:
    # ... existing imports ...
    from .environment_monitor import EnvironmentMonitor
    from ..models.environment import ModelExecuteFn
```

Add session start call (called once when Orchestrator starts):

```python
    def start_session(self, execute_fn: ModelExecuteFn) -> dict:
        """Initialize session. Phase 2.5: includes environment checks.

        IFM-09: Stores execute_fn as self._execute_fn for use by
        periodic_check(). Checks it is not None before calling.
        """
        # IFM-09: Store execute_fn for periodic checks
        self._execute_fn = execute_fn

        results: dict = {}

        # Phase 2.5: Environment awareness check
        if self.environment_monitor is not None:
            env_result = self.environment_monitor.session_start(execute_fn)
            results["environment"] = {
                "drift_detected": env_result.drift_detected,
                "version_changes": env_result.version_changes,
                "revalidation_triggered": env_result.revalidation_triggered,
                "canary_all_passed": env_result.canary_all_passed,
                "skipped": env_result.skipped,
            }
            if env_result.adaptation is not None:
                results["environment"]["adaptation"] = env_result.adaptation.value

        return results
```

Add to task completion flow (in `handle_verdict()` or `record_task_outcome()`):

```python
        # Phase 2.5: Update environment monitoring
        if self.environment_monitor is not None:
            task_type = self._classify_task_type(task)
            self.environment_monitor.on_task_complete(
                task_type=task_type,
                success=success,
                tokens_used=tokens_used,
            )

            # Check if periodic environment check is due
            if self.environment_monitor.should_run_periodic_check():
                # IFM-09: periodic_check() uses stored execute_fn if not
                # provided, so we can call without arguments. Check that
                # self._execute_fn is not None for safety.
                if self._execute_fn is not None:
                    try:
                        self.environment_monitor.periodic_check()
                    except Exception as e:
                        logger.warning(
                            f"Periodic environment check failed: {e}"
                        )
                else:
                    logger.warning(
                        "Periodic check due but no execute_fn available"
                    )
```

---

## Part 10: Implementation Sequence

### 10.1 Dependency Graph

```
Step 0: YAML configs (environment-awareness.yaml, canary-expectations.yaml)
  |
  |---> Step 1: models/environment.py (new models, extends existing)
  |       |
  |       |---> Step 3: engine/canary_runner.py (depends on models/environment)
  |       |
  |       |---> Step 4: engine/drift_detector.py (depends on models/environment)
  |       |
  |       |---> Step 5: engine/performance_monitor.py (depends on models/environment)
  |       |
  |       |---> Step 6: engine/revalidation_engine.py (depends on models/environment,
  |       |                                             budget_tracker, capability_tracker)
  |       |
  |       \---> Step 7: engine/environment_monitor.py (depends on Steps 3-6)
  |
  |---> Step 2: audit/tree_viewer.py (environment stream rendering)
  |
  \---> Step 8: engine/orchestrator.py (integration, depends on Step 7)
```

### 10.2 Step-by-Step Implementation

**Step 0: YAML Configuration Files**

Files to create:
- `core/environment-awareness.yaml` (from Part 3.1)
- `core/canary-expectations.yaml` (from Part 3.2)

Verification:
```bash
uv run python -c "
import yaml
with open('core/environment-awareness.yaml') as f:
    data = yaml.safe_load(f)
assert 'environment_awareness' in data
assert data['environment_awareness']['drift_detection']['threshold'] == 0.15
print('environment-awareness.yaml: OK')

with open('core/canary-expectations.yaml') as f:
    data = yaml.safe_load(f)
assert 'canary_expectations' in data
assert len(data['canary_expectations']) == 5
print('canary-expectations.yaml: OK')
"
```

Gate: Both YAML files load and validate.

---

**Step 1: Data Models (`models/environment.py`)**

Files to modify:
- `src/uagents/models/environment.py` — Replace with full Phase 2.5 models (Part 2)

Tests to run:
```bash
uv run pytest tests/test_models/test_environment.py -v
```

Gate: All model tests pass. `ModelFingerprint.per_dimension_delta()` and `score_vector()` work. All new models instantiate with valid data. All enums have correct values. `FrameworkModel` strict mode enforced (extra fields rejected).

---

**Step 2: Audit Tree Viewer (`audit/tree_viewer.py`)**

Files to modify:
- `src/uagents/audit/tree_viewer.py` — Add environment rendering (Part 9.2)

Tests to run:
```bash
uv run pytest tests/test_audit/test_tree_viewer.py -v
```

Gate: Environment stream rendering works. `render_environment_summary()` produces table. Existing diversity/task rendering unbroken.

---

**Step 3: CanaryRunner Engine**

Files to create:
- `src/uagents/engine/canary_runner.py` (Part 4)

Tests to run:
```bash
uv run pytest tests/test_engine/test_canary_runner.py -v
```

Gate: All 5 scoring methods produce correct scores for known inputs. Budget cap respected. Timeout handling works. Results stored to YAML. `get_latest_result()` retrieves most recent.

---

**Step 4: DriftDetector Engine**

Files to create:
- `src/uagents/engine/drift_detector.py` (Part 5)

Tests to run:
```bash
uv run pytest tests/test_engine/test_drift_detector.py -v
```

Gate: Fingerprint storage and retrieval works. Baseline computation produces correct median. Drift detection triggers at threshold. Per-dimension analysis identifies affected dimensions. Version comparison detects changes. History trimming respects `history_size`.

---

**Step 5: PerformanceMonitor Engine**

Files to create:
- `src/uagents/engine/performance_monitor.py` (Part 7)

Tests to run:
```bash
uv run pytest tests/test_engine/test_performance_monitor.py -v
```

Gate: Skill outcome recording updates rolling window. Baseline established after `window_size` attempts. Alert fires on > 10pp drop. Tool outcome recording tracks success/timeout rates. Tool quarantine alert at < 50%. Trace entries written to JSONL. State persisted to YAML.

---

**Step 6: RevalidationEngine**

Files to create:
- `src/uagents/engine/revalidation_engine.py` (Part 6)

Tests to run:
```bash
uv run pytest tests/test_engine/test_revalidation_engine.py -v
```

Gate: Budget cap computation correct. Scope assessment maps triggers to correct skills. Adaptation classification correct for all 5 response types. Results stored to YAML. History retrieval works.

---

**Step 7: EnvironmentMonitor (Full Rewrite)**

Files to modify:
- `src/uagents/engine/environment_monitor.py` — Replace with Part 8

Tests to run:
```bash
uv run pytest tests/test_engine/test_environment_monitor.py -v
```

Gate: `session_start()` runs canaries, detects drift, checks version, triggers revalidation. `periodic_check()` runs on schedule. `on_task_complete()` updates performance tracking. Recency skip works. Audit events logged to ENVIRONMENT stream.

---

**Step 8: Orchestrator Integration**

Files to modify:
- `src/uagents/engine/orchestrator.py` — Add EnvironmentMonitor (Part 9.4)

Tests to run:
```bash
uv run pytest tests/test_engine/test_orchestrator.py -v -k environment
```

Gate: Orchestrator creates EnvironmentMonitor. `start_session()` runs environment checks. Task completion updates environment monitoring. Periodic checks triggered at correct interval.

---

**Step 9: Full Regression**

```bash
uv run pytest --tb=short -q
```

Gate: All existing tests pass. All new tests pass. No regressions.

### 10.3 Verification Checklist

| # | Check | Command |
|---|-------|---------|
| 1 | New models instantiate correctly | `uv run pytest tests/test_models/test_environment.py -v` |
| 2 | ModelFingerprint.per_dimension_delta() works | Same as #1 |
| 3 | CanarySuiteResult aggregates correctly | Same as #1 |
| 4 | VersionInfo.differs_from() detects changes | Same as #1 |
| 5 | CanaryRunner scores keyword_match correctly | `uv run pytest tests/test_engine/test_canary_runner.py -v -k keyword` |
| 6 | CanaryRunner scores constraint_check correctly | `uv run pytest tests/test_engine/test_canary_runner.py -v -k constraint` |
| 7 | CanaryRunner scores code_validation correctly | `uv run pytest tests/test_engine/test_canary_runner.py -v -k code` |
| 8 | CanaryRunner scores diversity correctly | `uv run pytest tests/test_engine/test_canary_runner.py -v -k diversity` |
| 9 | CanaryRunner scores exact_fields correctly | `uv run pytest tests/test_engine/test_canary_runner.py -v -k exact` |
| 10 | CanaryRunner respects budget cap | `uv run pytest tests/test_engine/test_canary_runner.py -v -k budget` |
| 11 | DriftDetector stores and retrieves fingerprints | `uv run pytest tests/test_engine/test_drift_detector.py -v -k store` |
| 12 | DriftDetector computes median baseline | `uv run pytest tests/test_engine/test_drift_detector.py -v -k baseline` |
| 13 | DriftDetector detects drift at threshold | `uv run pytest tests/test_engine/test_drift_detector.py -v -k drift` |
| 14 | DriftDetector identifies affected dimensions | `uv run pytest tests/test_engine/test_drift_detector.py -v -k dimension` |
| 15 | DriftDetector version check works | `uv run pytest tests/test_engine/test_drift_detector.py -v -k version` |
| 16 | RevalidationEngine budget cap correct | `uv run pytest tests/test_engine/test_revalidation_engine.py -v -k budget` |
| 17 | RevalidationEngine scope assessment correct | `uv run pytest tests/test_engine/test_revalidation_engine.py -v -k scope` |
| 18 | RevalidationEngine adaptation classification | `uv run pytest tests/test_engine/test_revalidation_engine.py -v -k adapt` |
| 19 | PerformanceMonitor skill tracking | `uv run pytest tests/test_engine/test_performance_monitor.py -v -k skill` |
| 20 | PerformanceMonitor tool tracking | `uv run pytest tests/test_engine/test_performance_monitor.py -v -k tool` |
| 21 | PerformanceMonitor alert logic | `uv run pytest tests/test_engine/test_performance_monitor.py -v -k alert` |
| 22 | PerformanceMonitor trace logging | `uv run pytest tests/test_engine/test_performance_monitor.py -v -k trace` |
| 23 | EnvironmentMonitor session_start() full flow | `uv run pytest tests/test_engine/test_environment_monitor.py -v -k session` |
| 24 | EnvironmentMonitor periodic_check() | `uv run pytest tests/test_engine/test_environment_monitor.py -v -k periodic` |
| 25 | EnvironmentMonitor recency skip | `uv run pytest tests/test_engine/test_environment_monitor.py -v -k skip` |
| 26 | Audit tree viewer environment rendering | `uv run pytest tests/test_audit/test_tree_viewer.py -v -k environment` |
| 27 | Orchestrator environment integration | `uv run pytest tests/test_engine/test_orchestrator.py -v -k environment` |
| 28 | VALIDATION: simulated drift triggers revalidation | `uv run pytest tests/test_engine/test_environment_monitor.py -v -k simulated_drift` |
| 29 | Existing tests still pass (backward compat) | `uv run pytest --tb=short -q` |
| 30 | Full test suite passes | `uv run pytest --tb=long -v` |

---

## Part 11: Failure Modes

### 11.1 Data Integrity (FM-139 through FM-145)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-139 | Canary expectations YAML modified accidentally, invalidating all historical fingerprint comparisons | CRITICAL | Data Integrity | **FIXED (SF-10):** `CanaryRunner.__init__()` computes SHA-256 of expectations and compares to stored hash. On mismatch, logs CRITICAL and raises `ValueError`. On first run, stores the hash. `canary-expectations.yaml` has WARNING comment at top. |
| FM-140 | Fingerprint YAML files corrupted (partial write, disk full) | HIGH | Data Integrity | `YamlStore.write()` uses atomic temp-file + `os.replace()`. `_check_disk_space()` prevents writes below 100MB free. Corrupt fingerprints are skipped with warning in `load_fingerprint_history()`. |
| FM-141 | Performance track YAML grows unbounded as new skills/tools are added | MEDIUM | Data Integrity | PerformanceTrack is bounded by the number of known task types (8) and tools (typically < 50). `SkillPerformance.recent_outcomes` is trimmed to `window_size`. Total size stays well under 1MB YAML cap. |
| FM-142 | Revalidation history directory accumulates unlimited files | MEDIUM | Data Integrity | **FIXED (SF-6):** `RevalidationEngine._trim_history()` added. Keeps last 50 results. Called after each store. |
| FM-143 | `CanarySuiteResult` stored with truncated `actual` field (500 char limit) loses scoring-relevant data | LOW | Data Integrity | Scoring is computed before truncation. The `actual` field in storage is for debugging/audit only. Score is the authoritative result. |
| FM-144 | `last-fingerprint.yaml` written to `core/` directory which is typically read-only config | MEDIUM | Data Integrity | **FIXED (MF-6/IFM-02):** Moved to `{state_base}/last-fingerprint.yaml` in the domain state directory. `_should_run_canary()` and `store_fingerprint()` paths updated. |
| FM-145 | ModelFingerprint `per_dimension_delta()` signs confusing (positive = current better or baseline better?) | LOW | Data Integrity | Docstring clarifies: "Positive = improvement (current > baseline)". Convention: `self - other`, where `self` is current and `other` is baseline. |

### 11.2 Concurrency (FM-146 through FM-149)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-146 | Two sessions start simultaneously, both run canary suite, both write fingerprints | MEDIUM | Concurrency | `YamlStore.write()` uses advisory file locks. Two fingerprints written is acceptable — they provide two data points. `_trim_history()` prevents unbounded growth. |
| FM-147 | `PerformanceMonitor._save_track()` called from multiple threads (tool callbacks) | HIGH | Concurrency | **FIXED (SF-4/IFM-25):** `self._lock = threading.Lock()` added. All `_track` mutations guarded by `with self._lock:`. `YamlStore.write()` also acquires advisory file lock for on-disk safety. |
| FM-148 | `periodic_check()` runs while `session_start()` is still executing | LOW | Concurrency | `periodic_check()` is only triggered from task completion, which cannot happen during `session_start()`. No actual race. |
| FM-149 | Fingerprint trimming deletes file while `load_fingerprint_history()` is reading it | LOW | Concurrency | `_trim_history()` catches `FileNotFoundError`. `load_fingerprint_history()` catches all exceptions per file. Worst case: one fingerprint missing from history — acceptable. |

### 11.3 API Contracts (FM-150 through FM-154)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-150 | `execute_fn` signature mismatch — caller passes wrong function signature | HIGH | API Contracts | **FIXED (SF-1):** `ModelExecuteFn` Protocol defined in `models/environment.py`. All `execute_fn` parameters now typed as `ModelExecuteFn` instead of bare `callable`. Signature: `(prompt: str, max_tokens: int) -> tuple[str, int]`. Static type checkers enforce compliance. |
| FM-151 | `execute_fn` returns negative `tokens_used` | MEDIUM | API Contracts | `CanaryResult.tokens_used` has `Field(ge=0)` validator. Pydantic will raise `ValidationError`. CanaryRunner should catch and log, defaulting to 0. |
| FM-152 | `CapabilityTracker` not available (Phase 2 not implemented or disabled) | MEDIUM | API Contracts | All references to `capability_tracker` check `is not None`. RevalidationEngine and EnvironmentMonitor work without it (degraded: no skill-level analysis). |
| FM-153 | `BudgetTracker.get_window()` returns stale data (cached from before revalidation consumed tokens) | MEDIUM | API Contracts | `BudgetTracker._rebuild_window_from_ledger()` checks mtime. After revalidation tokens are consumed via `record_consumption()`, the cache is invalidated. |
| FM-154 | `AuditLogger` is None — all `_log_event()` calls silently skipped | LOW | API Contracts | Intentional design. `_log_event()` checks `self.audit_logger is None` and returns. Environment awareness works without audit logging (degraded observability). |

### 11.4 Silent Degradation (FM-155 through FM-161)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-155 | Canary suite always scores 1.0 because model is too capable — drift never detected | MEDIUM | Silent Degradation | Canary tasks are designed with varied difficulty. `creative_divergence` task uses diversity scoring which is unlikely to be 1.0. If all tasks consistently score 1.0, the fingerprint vector is [1,1,1,1,1] and any degradation will be detected as drift from perfect baseline. |
| FM-156 | `_score_code_validation()` uses `exec()` — security risk if model output contains malicious code | HIGH | Silent Degradation | **FIXED (MF-2):** Now runs in `concurrent.futures.ProcessPoolExecutor` with 2-second timeout and restricted namespace (`__builtins__` limited to `range`, `int`). Exceptions logged. |
| FM-157 | `_score_constraint_check()` uses `eval()` — security risk | HIGH | Silent Degradation | **FIXED (MF-1):** Replaced `eval()` with `CONSTRAINT_CHECKERS` dictionary of named checker functions. YAML constraints now specify `checker` name and `arg` value instead of raw Python expressions. IFM-18: Failures logged with warning. |
| FM-158 | Drift threshold 0.15 is too sensitive — false positives on natural variance | MEDIUM | Silent Degradation | Threshold is configurable via `environment-awareness.yaml`. Baseline uses median of last 5 fingerprints (smooths noise). Monitor false positive rate and adjust. |
| FM-159 | Drift threshold 0.15 is too insensitive — real drift below 0.15 goes undetected | MEDIUM | Silent Degradation | Per-dimension alert at 0.10 catches single-dimension drift even if overall distance < 0.15. If a single dimension drops > 0.10, it is flagged even without overall drift. |
| FM-160 | `check_claude_version()` returns "unknown" on WSL or restricted environments — version tracking disabled | LOW | Silent Degradation | "unknown" is treated as a valid version string. If both previous and current are "unknown", no version change is detected. Acceptable — version tracking is best-effort. |
| FM-161 | Rolling window of 20 for skill performance is too small for rarely-used skills | MEDIUM | Silent Degradation | Window size is configurable. For skills with < 20 uses, baseline is not established (`baseline_success_rate = None`), so no false alerts fire. Alerts only trigger after full window. |

### 11.5 Resource Leaks (FM-162 through FM-164)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-162 | Trace JSONL files grow without bound if tasks are small (< retention limit but high volume) | MEDIUM | Resource Leaks | `JsonlWriter` has rotation at 5MB and max 5 rotated files. Total trace storage bounded to ~30MB. |
| FM-163 | `PerformanceMonitor._pending_alerts` grows if `get_pending_alerts()` never called | LOW | Resource Leaks | Alerts accumulate until consumed. In practice, `periodic_check()` or `session_start()` consumes them. Worst case: a few hundred alert objects in memory — negligible. |
| FM-164 | Canary results directory accumulates files if `_trim_history()` only trims fingerprints, not canary results | MEDIUM | Resource Leaks | **FIXED (SF-7/IFM-16):** `CanaryRunner._trim_canary_results()` added. Keeps last `history_size` results. Called after each store. |

### 11.6 Spec Divergence (FM-165 through FM-168)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-165 | Spec says "Run canary suite at session start + every 50 tasks" but implementation uses configurable interval | LOW | Spec Divergence | Config default is 50, matching spec. Configurability is intentional enhancement. |
| FM-166 | Spec says "If MCP change: revalidate affected tool skills only" but Phase 2.5 has no MCP schema diff mechanism | MEDIUM | Spec Divergence | Phase 2.5 supports `MCP_CHANGE` trigger type with scope `["tool_integrations", "mcp_tools"]`. Actual MCP schema comparison is deferred — manual trigger by human for now. |
| FM-167 | Spec says "If OS update: run compute baseline and compare" but implementation only tracks version string | LOW | Spec Divergence | OS version string change triggers `VERSION_CHANGE` revalidation. Full compute baseline (CPU benchmarking) is Phase 3.5 scope (compute monitoring). |
| FM-168 | Self-benchmarking protocol (Section 19.4) meta-tasks not implemented | MEDIUM | Spec Divergence | `BenchmarkSuiteResult` and `BenchmarkTask` models are defined. Implementation of actual meta-task execution (bug detection, skill writing, evolution proposal, decomposition) requires Phase 3+ capabilities. Phase 2.5 provides the data models and storage; Phase 3 provides the meta-task execution. |

### 11.7 Review-Identified Failure Modes (FM-169 through FM-186)

These failure modes were identified during design and failure mode reviews.
All HIGH and CRITICAL items have been fixed in the design; MEDIUM items have
documented mitigations.

| ID | Failure Mode | Severity | Category | Status |
|----|-------------|----------|----------|--------|
| FM-169 | Timestamp-based filenames can collide when two operations run within the same second (e.g., concurrent sessions) | MEDIUM | Data Integrity | **FIXED (IFM-01):** `generate_id()` suffix appended to all timestamp-based filenames in `CanaryRunner._store_result()`, `DriftDetector.store_fingerprint()`, `RevalidationEngine._store_result()`. |
| FM-170 | Pydantic `strict=True` on `FrameworkModel` vs `strict=False` in `YamlStore.read()` — nested model YAML roundtrip may fail | HIGH | Data Integrity | **FIXED (IFM-03):** Note added to `_load_track()` explaining that `YamlStore.read()` uses `strict=False` which overrides class-level `strict=True`. Test requirement added for `PerformanceTrack` roundtrip verification. |
| FM-171 | `recent_outcomes` list not trimmed when `skill_window_size` config changes between sessions | MEDIUM | Data Integrity | **FIXED (IFM-04):** `_load_track()` trims `recent_outcomes` to `skill_window_size` after loading. |
| FM-172 | `run_revalidation()` never calls `execute_fn` — `post_fingerprint` always None, `classify_adaptation()` always returns UNCHANGED | CRITICAL | Logic | **FIXED (MF-5/IFM-06):** `run_revalidation()` now accepts `canary_runner` parameter and re-runs canary suite to produce `post_fingerprint`. `tokens_used` tracked from canary re-run. |
| FM-173 | Scope names from `assess_scope()` don't match `_classify_task_type()` names in Orchestrator | MEDIUM | API Contracts | **FIXED (IFM-07):** Added `SCOPE_TO_TASK_TYPE` mapping dictionary bridging the two naming vocabularies. |
| FM-174 | `PerformanceMonitor` creates its own `JsonlWriter` for traces, duplicating the `AuditLogger`'s TRACES writer | MEDIUM | Resource Leaks | **FIXED (IFM-08):** `PerformanceMonitor` now accepts injected `AuditLogger` and uses `log_trace()` instead of creating a separate `JsonlWriter`. |
| FM-175 | `Orchestrator._execute_fn` never assigned — `periodic_check()` calls fail | HIGH | Logic | **FIXED (IFM-09):** `start_session()` stores `execute_fn` as `self._execute_fn`. `periodic_check()` checks it is not None. `EnvironmentMonitor` also stores it internally. |
| FM-176 | False drift alarm on second session when history has fewer entries than `baseline_window` | HIGH | Logic | **FIXED (IFM-10):** Added `if len(history) < baseline_window: drift_detected = False` guard in `detect_drift()`. |
| FM-177 | Timezone-naive `datetime.fromisoformat()` comparison with timezone-aware `datetime.now(timezone.utc)` raises `TypeError` | MEDIUM | Data Integrity | **FIXED (IFM-14):** Added `TypeError` to the except clause in `_should_run_canary()`. |
| FM-178 | Excessive YAML writes from `PerformanceMonitor` — every skill outcome triggers a full YAML write | HIGH | Performance | **FIXED (MF-7/IFM-15):** Added dirty flag + batch write mechanism. Only persists every 5 updates or on explicit `flush()`. |
| FM-179 | Canary results directory accumulates files without trimming | MEDIUM | Resource Leaks | **FIXED (SF-7/IFM-16):** Added `_trim_canary_results()` to `CanaryRunner`, keeps last `history_size` entries. |
| FM-180 | Duplicate pending alerts when the same skill/tool triggers multiple times before consumption | MEDIUM | Logic | **FIXED (IFM-17):** Alerts deduplicated by `target_name + alert_type` before appending to `_pending_alerts`. |
| FM-181 | Silent exception swallowing in constraint evaluation (originally `eval()`, now named checkers) | MEDIUM | Observability | **FIXED (IFM-18):** Named checker failures now logged with `logger.warning()` including checker name, exception type, and message. |
| FM-182 | `check_version()` catches only `FileNotFoundError` — `ValidationError` from schema changes crashes startup | HIGH | API Contracts | **FIXED (IFM-19):** Except clause now catches `Exception` with warning for non-`FileNotFoundError` cases. |
| FM-183 | Mean delta in `classify_adaptation()` masks per-dimension degradation (e.g., +0.3 reasoning, -0.2 code = +0.02 mean = UNCHANGED) | HIGH | Logic | **FIXED (IFM-20):** Added per-dimension extreme check. If any single dimension drops more than `degraded_minor_threshold`, classification is at least `DEGRADED_MINOR`. |
| FM-184 | Performance alerts (degraded skills) never trigger revalidation — only drift triggers it | HIGH | Logic | **FIXED (IFM-21):** `periodic_check()` now triggers `PERFORMANCE_DROP` revalidation when `get_degraded_skills()` returns non-empty list. |
| FM-185 | `PerformanceAlert` and `EnvironmentCheckResult` are plain classes, not `FrameworkModel` — lose validation and serialization | MEDIUM | Data Integrity | **FIXED (SF-2/IFM-22/IFM-23):** Both converted to `FrameworkModel` subclasses in `models/environment.py`. |
| FM-186 | Constructor signatures changed in Phase 2.5 — callers not updated | HIGH | API Contracts | **FIXED (IFM-28):** Migration notes added to `RevalidationEngine` and `EnvironmentMonitor` docstrings listing all callers to update. `CanaryRunner` now accepts `model_id` parameter. `PerformanceMonitor` accepts `audit_logger`. |

### 11.8 Summary

| Severity | Count | All Fixed? |
|----------|-------|------------|
| CRITICAL | 2 | FM-139: Hash verification added (SF-10). FM-172: run_revalidation now calls execute_fn (MF-5). |
| HIGH | 13 | All FIXED: FM-140 (YamlStore), FM-147 (Lock), FM-150 (type check), FM-156 (ProcessPoolExecutor), FM-157 (named checkers), FM-170 (strict=False note), FM-175 (execute_fn stored), FM-176 (history guard), FM-178 (batch writes), FM-182 (broad except), FM-183 (per-dim check), FM-184 (perf revalidation), FM-186 (migration notes). |
| MEDIUM | 22 | All documented with mitigations or FIXED |
| LOW | 11 | Documented, acceptable |
| **Total** | **48** | |
