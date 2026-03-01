# Universal Agents Framework — Phase 1.5 Detailed Design

**Version:** 0.1.0
**Date:** 2026-02-28
**Source:** framework-design-unified-v1.1.md (Section 18), resource-awareness-literature-review.md (~65 papers)
**Status:** Implementation-ready — concrete enough to code from directly
**Scope:** Phase 1.5 "Resource Awareness" — token budgets, rate limit mirror, backpressure, cost approval, prompt caching, self-improving efficiency
**Prerequisite:** Phase 0 + Phase 1 fully implemented (46 source files, 254 tests passing)

---

## Table of Contents

1. [Phase 1.5 Architecture Overview](#part-1-phase-15-architecture-overview)
2. [New & Modified Data Models](#part-2-new--modified-data-models)
3. [Token Budget Tracker](#part-3-token-budget-tracker)
4. [Rate Limit Mirror & Backpressure](#part-4-rate-limit-mirror--backpressure)
5. [Prompt Caching Strategy](#part-5-prompt-caching-strategy)
6. [Cost Approval Workflow](#part-6-cost-approval-workflow)
7. [Budget-Aware Orchestration](#part-7-budget-aware-orchestration)
8. [Self-Improving Resource Efficiency](#part-8-self-improving-resource-efficiency)
9. [Implementation Sequence](#part-9-implementation-sequence)
10. [Verification Checklist](#part-10-verification-checklist)
11. [Edge Cases, Failure Modes & Mitigations](#part-11-edge-cases-failure-modes--mitigations)

---

## Part 1: Phase 1.5 Architecture Overview

### 1.1 What Phase 1.5 Adds

Phase 1.5 transforms the framework from "resource-oblivious" to "resource-aware." After Phase 1, agents spawn, execute, and review tasks without knowing how many tokens remain, whether rate limits are close, or whether spawning another agent will exhaust system resources. Phase 1.5 fills in the stubs left in `ResourceTracker` and integrates resource awareness into every decision point.

**Core insight from literature:** Token-unaware agents waste 50-95% of tokens (BATS, Co-Saving, ITR, CodeAgents). Simply granting larger budgets **fails** without budget awareness — agents lack intrinsic ability to manage resources (BATS finding, arXiv:2511.17006).

**Claude Max context:** The framework runs on Claude Max subscription. The optimization objective is **maximizing value extracted within fixed rate/time windows**, not minimizing dollar cost. Rate limits (RPM, ITPM, OTPM) and 5-hour rolling windows are the binding constraints. Prompt caching is rate-limit arbitrage: cached tokens don't count toward ITPM (2-5x effective throughput boost).

### 1.2 Architecture: 4-Layer Resource Stack

```
Layer 4: Cost-Aware Decision Making          ← NEW: approval workflow, daily/weekly caps
  - Human approval gates for monetary operations
  - Budget-parameterized model routing
  │
Layer 3: Token Budget Management              ← UPGRADE: full implementation
  - Per-task budget estimation (TALE-style)
  - Rolling window tracking (5-hour + weekly)
  - Budget pressure levels → behavioral adaptation
  │
Layer 2: Rate Limit Handling                  ← NEW: full implementation
  - Local token bucket mirror (RPM, ITPM, OTPM)
  - Backpressure propagation
  - Prompt caching for ITPM arbitrage
  │
Layer 1: Computational Resource Awareness     ← UPGRADE: threshold refinement
  - CPU/memory/disk monitoring (existing)
  - Enhanced spawn policy with headroom estimation
  - Idle agent despawn
```

### 1.3 Key Design Principles (from ~65 papers)

1. **Budget visibility is mandatory** — agents must see remaining budget at all times (BATS)
2. **Pause upstream, don't retry downstream** — backpressure > retry queues (ATB/AATB: 97.3% fewer 429s)
3. **Cache is rate-limit arbitrage** — shared prefix caching multiplies effective ITPM 2-5x
4. **59.4% of tokens go to review** — review is the #1 optimization target (Tokenomics)
5. **Cold seeds → rolling average** — 10 samples replaces hardcoded estimates (TALE)
6. **Ring 0 is never compressed** — constitution + safety sections survive all pressure levels

### 1.4 What Phase 1.5 Does NOT Include

- FrugalGPT model cascading Haiku→Sonnet→Opus (Phase 2+ — requires confidence-threshold calibration)
- Full topology optimization via AgentDropout/TopoDIM (Phase 2+ — requires diversity metrics)
- Experience-based shortcuts / Co-Saving pattern (Phase 3 — requires skill extraction)
- Dynamic tool loading / RAG-MCP retrieval (Phase 3.5)
- Population-based budget allocation with dynamic programming (Phase 4+)

### 1.5 Files Modified & Created

**New files (10):**
```
src/uagents/engine/rate_limiter.py          — Rate limit mirror + backpressure
src/uagents/engine/budget_tracker.py        — Token budget management (BATS-style)
src/uagents/engine/cost_gate.py             — Cost approval workflow
src/uagents/engine/cache_manager.py         — Prompt caching strategy
src/uagents/engine/resource_facade.py       — FM-64: Single entry point for consumption recording
core/resource-awareness.yaml                — FM-06: Resource config (created FIRST)
tests/test_engine/test_rate_limiter.py      — Rate limit mirror tests
tests/test_engine/test_budget_tracker.py    — Budget tracker tests
tests/test_engine/test_cost_gate.py         — Cost approval tests
tests/test_engine/test_cache_manager.py     — FM-55: Cache manager tests (NOT optional)
```

**Modified files (9):**
```
src/uagents/models/resource.py            — New models: WindowBudget, ResourceSnapshot, CostRecord
src/uagents/state/yaml_store.py          — Add public ensure_dir() method
src/uagents/engine/resource_tracker.py    — Deprecate _token_history, delegate to BudgetTracker
src/uagents/engine/orchestrator.py        — Budget-aware task selection, backpressure integration
src/uagents/engine/agent_spawner.py       — Budget check before spawn, idle despawn
src/uagents/engine/prompt_composer.py     — Cache-aware prefix assembly
src/uagents/engine/task_lifecycle.py      — Budget annotations on tasks
src/uagents/audit/logger.py              — Resource event logging
tests/test_engine/test_resource_tracker.py        — Extended tests
tests/test_engine/test_resource_tracker_extended.py — Extended tests
tests/test_engine/test_orchestrator.py    — Budget-aware orchestration tests
```

**YamlStore modification** — add `ensure_dir()` public method:
```python
# In state/yaml_store.py — add to YamlStore class:
def ensure_dir(self, relative_path: str) -> Path:
    """Ensure a directory exists under the base path. Returns the resolved Path.

    This is the PUBLIC API for directory creation. Components must NOT
    access _resolve() directly (private method).
    """
    resolved = self._resolve(relative_path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved
```

---

## Part 2: New & Modified Data Models

### 2.1 New Models in `models/resource.py`

```python
class WindowBudget(FrameworkModel):
    """Tracks token consumption within a rolling time window.

    Models the Claude Max subscription constraint: ~88K tokens per 5-hour
    window (Max5) or ~220K (Max20), with weekly caps.
    """
    window_start: datetime
    window_duration_hours: float = 5.0
    estimated_capacity: int = 88_000  # Max5 default; Max20 = 220_000
    tokens_consumed: int = 0
    requests_made: int = 0
    last_request_at: datetime | None = None

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.estimated_capacity - self.tokens_consumed)

    @property
    def utilization(self) -> float:
        if self.estimated_capacity <= 0:
            return 1.0
        return self.tokens_consumed / self.estimated_capacity

    @property
    def pressure_level(self) -> BudgetPressureLevel:
        remaining_pct = 1.0 - self.utilization
        if remaining_pct > 0.60:
            return BudgetPressureLevel.GREEN
        if remaining_pct > 0.30:
            return BudgetPressureLevel.YELLOW
        if remaining_pct > 0.10:
            return BudgetPressureLevel.ORANGE
        return BudgetPressureLevel.RED


class WeeklyBudget(FrameworkModel):
    """Tracks weekly token allocation.

    Weekly cap is empirically determined and may change without notice.
    Start conservative and adjust based on observed limits.
    """
    week_start: datetime
    estimated_weekly_cap: int = 1_000_000  # Conservative default
    tokens_consumed: int = 0
    windows_used: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.estimated_weekly_cap - self.tokens_consumed)

    @property
    def utilization(self) -> float:
        if self.estimated_weekly_cap <= 0:
            return 1.0
        return self.tokens_consumed / self.estimated_weekly_cap


class ResourceSnapshot(FrameworkModel):
    """Point-in-time snapshot of all resource dimensions.

    Created before every resource-consuming decision (spawn, task start).
    Persisted to audit log for post-hoc analysis.
    """
    timestamp: datetime
    compute: ComputeMetrics
    window_budget: WindowBudget
    weekly_budget: WeeklyBudget
    rate_pressure: float  # 0.0 = no pressure, 1.0 = at limit
    budget_pressure: BudgetPressureLevel
    can_spawn: bool
    spawn_rejection_reason: str | None = None


class CostRecord(FrameworkModel):
    """Audit record for a cost-incurring action."""
    id: str
    timestamp: datetime
    spend_level: SpendLevel
    amount: float
    currency: str = "USD"
    purpose: str
    approved: bool
    approved_by: str | None = None
    task_id: str | None = None
    agent_id: str | None = None


class DailyCostSummary(FrameworkModel):
    """Aggregated daily cost tracking for cap enforcement."""
    date: str  # YYYY-MM-DD
    total_spent: float = 0.0
    daily_cap: float = 10.0  # Default $10/day
    records: list[str] = []  # CostRecord IDs

    @property
    def remaining(self) -> float:
        return max(0.0, self.daily_cap - self.total_spent)

    @property
    def at_cap(self) -> bool:
        return self.total_spent >= self.daily_cap


class TaskBudgetAnnotation(FrameworkModel):
    """Budget metadata attached to a task during execution.

    Provides BATS-style continuous budget visibility to executing agents.
    """
    estimated_tokens: int
    allocated_tokens: int
    spent_tokens: int = 0
    pressure_at_start: BudgetPressureLevel = BudgetPressureLevel.GREEN
    estimation_method: str = "cold_seed"  # cold_seed | rolling_average | manual

    @property
    def remaining(self) -> int:
        return max(0, self.allocated_tokens - self.spent_tokens)

    @property
    def utilization(self) -> float:
        if self.allocated_tokens <= 0:
            return 1.0
        return self.spent_tokens / self.allocated_tokens


class ResourceEfficiencyMetrics(FrameworkModel):
    """Self-improvement metrics tracked per task (Section 18.6)."""
    task_id: str
    cost_of_pass: int  # Total tokens to achieve successful completion
    tokens_per_quality_point: float | None = None
    budget_utilization: float  # productive / total
    cache_hit_tokens: int = 0
    total_input_tokens: int = 0
    waste_tokens: int = 0  # Failed approaches, redundant reasoning
    review_rounds: int = 1

    @property
    def cache_hit_rate(self) -> float:
        if self.total_input_tokens <= 0:
            return 0.0
        return self.cache_hit_tokens / self.total_input_tokens
```

### 2.2 Datetime Convention (FM-05 CRITICAL)

**IMPORTANT:** The existing codebase uses `datetime.utcnow()` (naive UTC, no timezone info).
Phase 1.5 uses `datetime.now(timezone.utc)` (timezone-aware UTC). Comparing naive and
aware datetimes raises `TypeError`. Phase 1.5 implementation MUST:

1. **Step 0 (prerequisite):** Migrate all existing datetime usage to `datetime.now(timezone.utc)`:
   - `engine/task_lifecycle.py` — lines 60, 69, 99, 102
   - `engine/agent_spawner.py` — lines 88, 109, 145, 160, 178
   - `engine/team_manager.py` — lines 93, 174, 197
   - `engine/orchestrator.py` — line 88
   - All `datetime.utcnow()` → `datetime.now(timezone.utc)` globally
2. **Pydantic serialization:** Ensure `model_dump(mode="json")` produces ISO 8601 with timezone.
   Verify that `yaml.safe_load()` + Pydantic round-trips preserve timezone info.
3. **Test:** Add a test that round-trips a `WindowBudget` through YAML and verifies
   `window_start` is timezone-aware after deserialization.

### 2.3 Model Backward Compatibility (FM-07 CRITICAL)

**Problem:** `FrameworkModel` uses `extra="forbid"`. Adding `budget` to `Task` and
`tokens_consumed`/`cache_hits` to `AgentRegistryEntry` means Phase 1 code cannot read
YAML files written by Phase 1.5 (new fields rejected). Rollback is broken.

**Solution:** Phase 1.5 deployment MUST be atomic (all-or-nothing). Additionally:
- Add a comment in `models/base.py` near `extra="forbid"` documenting this constraint
- The `PromptSection.is_cached` field has the same constraint (FM-31)
- Phase 1.5 tests must verify that models WITHOUT the new fields still deserialize
  correctly (backwards compat for reading old data)
- Forward compat (Phase 1 reading Phase 1.5 data) is NOT supported; document in release notes

### 2.4 Modified Models

**`models/task.py`** — Add budget annotation field:

```python
# In class Task:
    budget: TaskBudgetAnnotation | None = None  # Phase 1.5: resource tracking
```

**`models/agent.py`** — Add token tracking fields:

```python
# In class AgentRegistryEntry:
    tokens_consumed: int = 0       # Phase 1.5: running total
    cache_hits: int = 0            # Phase 1.5: prompt cache hit count
```

### 2.5 DailyCostSummary Date Validation (FM-45)

```python
class DailyCostSummary(FrameworkModel):
    """Aggregated daily cost tracking for cap enforcement."""
    date: str  # YYYY-MM-DD — validated below
    # ... existing fields ...

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Enforce YYYY-MM-DD format (fail-loud)."""
        from datetime import datetime as dt
        try:
            dt.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"date must be YYYY-MM-DD format, got: {v!r}")
        return v
```

### 2.3 New YAML Config: `core/resource-awareness.yaml`

```yaml
# Resource awareness configuration (Section 18)
resource_awareness:

  claude_max_plan: "max5"  # max5 | max20

  window:
    duration_hours: 5
    estimated_capacity_max5: 88000
    estimated_capacity_max20: 220000

  weekly:
    estimated_cap: 1000000  # Conservative; adjusted empirically

  budget_pressure:
    green_threshold: 0.60   # > 60% remaining
    yellow_threshold: 0.30  # 30-60%
    orange_threshold: 0.10  # 10-30%
    # Below 10% = RED

  backpressure:
    slow_spawning_at: 0.80   # 80% rate capacity
    pause_noncritical_at: 0.90
    single_agent_at: 0.95
    full_stop_at: 1.00

  cold_seeds:
    # Task-type-based seeds (spec Section 18.2)
    # These are conservative starting estimates replaced by rolling averages
    # after rolling_average_threshold samples.
    simple_fix: 2000
    feature_small: 8000
    feature_medium: 25000
    feature_large: 80000
    research: 15000
    review: 5000
    canary_suite: 3000        # Environment monitoring canary tests
    skill_validation: 4000    # Skill crystallization validation
    evolution_proposal: 6000  # Self-evolution proposal evaluation
    decomposition: 5000       # Task decomposition by orchestrator
    # Note: YAML is the authority for cold seed values.
    # Python COLD_SEEDS dict must mirror this file exactly.
    # On startup, BudgetTracker loads seeds from YAML and raises
    # if the file is missing (fail-loud, no hardcoded fallback).

  rolling_average_threshold: 10  # Samples before using rolling average (spec Section 18.2)
  safety_margin_novel: 1.5       # 50% safety margin for novel tasks
  budget_reserve_pct: 0.20       # 20% buffer for unexpected needs

  idle_agent_timeout_minutes: 5

  cost_caps:
    daily: 10.0   # USD
    weekly: 50.0   # USD

  rate_limits:
    # Initial estimates; updated from response headers
    rpm_estimate: 50
    itpm_estimate: 80000
    otpm_estimate: 16000
```

---

## Part 3: Token Budget Tracker

### 3.1 Overview

The `BudgetTracker` is a BATS-inspired component that gives every agent continuous budget visibility. It tracks token consumption at three granularities:

1. **Per-task** — estimated vs. actual tokens for the current task
2. **Per-window** — tokens consumed in the current 5-hour rolling window
3. **Per-week** — aggregate weekly consumption against estimated cap

### 3.1.1 Concurrency Strategy (FM-18, FM-19)

**Problem:** `record_consumption()` performs a read-modify-write cycle on both
`window.yaml` and `weekly.yaml`. YamlStore's advisory lock covers only individual
`write()` calls, not the full read-modify-write span. Two concurrent
`record_consumption()` calls can lose one increment.

**Phase 1.5 approach:** Accept the race condition with documentation. In practice:
- Claude Code runs a single agent per session. Multi-agent scenarios go through
  the orchestrator (single-threaded). Concurrent writes are rare.
- The impact is systematic under-counting by at most one concurrent call's tokens
  per race. With typical agent concurrency (2-4), this is <5% drift.
- The window is 5 hours with ~88K tokens — a few hundred lost tokens are noise.

**Phase 2 fix (recommended):** Replace YAML read-modify-write with an append-only
ledger (`record_consumption` appends to a JSONL file, `get_window()` sums entries).
This eliminates the race entirely. See `jsonl_writer.py` pattern for implementation.

### 3.1.2 ResourceTracker Delegation Strategy (FM-14, FM-22, FM-24)

**Problem:** Both `ResourceTracker` and `BudgetTracker` have `estimate_task_cost()`
and `record_actual_usage()` methods with different signatures and different data
sources (hardcoded `COLD_SEEDS` dict vs. YAML-loaded seeds).

**Solution (Step 6):** `ResourceTracker` methods become delegating wrappers:

```python
# In resource_tracker.py (Step 6 modifications):

class ResourceTracker:
    def __init__(self, ..., budget_tracker: BudgetTracker | None = None):
        self.budget_tracker = budget_tracker
        # DEPRECATED: _token_history removed. All history in BudgetTracker.
        # DEPRECATED: COLD_SEEDS dict removed. Seeds loaded from YAML by BudgetTracker.

    def estimate_task_cost(self, task_type: str, complexity: str = "medium") -> int:
        """Delegate to BudgetTracker. Falls back to 10,000 if no BudgetTracker."""
        if self.budget_tracker:
            return self.budget_tracker.estimate_task_cost(task_type, complexity)
        return 10_000  # Phase 0 fallback (no budget tracking)

    def record_actual_usage(self, task_type: str, tokens_used: int) -> None:
        """Delegate to BudgetTracker with default complexity.

        FM-15 FIX: Signature maintained for backward compatibility.
        BudgetTracker's 3-param version called with complexity='medium' default.
        """
        if self.budget_tracker:
            self.budget_tracker.record_actual_usage(task_type, "medium", tokens_used)
```

**Callers:** All NEW Phase 1.5 code calls `BudgetTracker` directly.
Only legacy callers (Phase 0/1) go through `ResourceTracker` wrappers.

### 3.2 Implementation: `engine/budget_tracker.py`

```python
"""BATS-inspired token budget tracker.
Spec reference: Section 18.2 (Token Budget Tracker).

Key literature:
- BATS (arXiv:2511.17006): Budget awareness is mandatory
- TALE (arXiv:2412.18547): Estimation + prompting reduces 67% output tokens
- Tokenomics (arXiv:2601.14470): 59.4% of tokens in review stage
"""
from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..models.resource import (
    BudgetPressureLevel,
    DailyCostSummary,
    ResourceEfficiencyMetrics,
    TaskBudgetAnnotation,
    WeeklyBudget,
    WindowBudget,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.budget_tracker")

# Safety margin for novel tasks (no history)
NOVEL_SAFETY_MARGIN = 1.5

# Minimum samples before using rolling average over cold seed
# Must match core/resource-awareness.yaml:rolling_average_threshold
ROLLING_AVERAGE_THRESHOLD = 10

# Budget reserve for unexpected needs
BUDGET_RESERVE_PCT = 0.20


class BudgetTracker:
    """Provides continuous budget visibility to agents and orchestrator.

    Responsibilities:
    1. Track token consumption per window, per week, per task
    2. Estimate task costs (cold seeds → rolling average)
    3. Compute budget pressure levels
    4. Allocate budgets to subtasks with reserve
    5. Persist budget state to YAML for crash recovery

    Design invariants:
    - Budget state persisted after every update (crash recovery)
    - Pressure levels computed from remaining tokens, not spent
    - Rolling average replaces cold seeds after ROLLING_AVERAGE_THRESHOLD samples
    - 20% budget reserved for unexpected needs
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        plan: str = "max5",
    ):
        self.yaml_store = yaml_store
        self.domain = domain
        self._budget_base = f"instances/{domain}/state/resources"

        # Set capacity based on plan
        if plan == "max20":
            self._window_capacity = 220_000
        else:
            self._window_capacity = 88_000

        # Load cold seeds from YAML (fail-loud: no hardcoded fallback)
        # FM-58 FIX: Use ValueError (not FileNotFoundError) for structure issues.
        # Let FileNotFoundError from read_raw() propagate naturally if file is missing.
        config = yaml_store.read_raw("core/resource-awareness.yaml")
        raw_seeds = config.get("resource_awareness", {}).get("cold_seeds")
        if raw_seeds is None:
            raise ValueError(
                "core/resource-awareness.yaml has unexpected structure: "
                "missing 'resource_awareness.cold_seeds' section. "
                "Expected YAML structure: resource_awareness: { cold_seeds: { ... } }"
            )
        self._cold_seeds: dict[str, int] = {str(k): int(v) for k, v in raw_seeds.items()}

        # Token history for rolling averages (in-memory; rebuilt from audit logs on restart)
        self._token_history: dict[str, deque[int]] = {}

        # Cache hit tracking (consumed by compute_efficiency)
        self._cache_hit_tokens: int = 0
        self._total_input_tokens: int = 0

        # Ensure resource state directory exists
        self.yaml_store.ensure_dir(self._budget_base)

    # ── Window Management ──

    def get_window(self) -> WindowBudget:
        """Get or create the current window budget."""
        path = f"{self._budget_base}/window.yaml"
        try:
            window = self.yaml_store.read(path, WindowBudget)
            # Check if window has expired
            now = datetime.now(timezone.utc)
            window_end = window.window_start + timedelta(hours=window.window_duration_hours)
            if now >= window_end:
                # Window expired — start new one, carry nothing over
                logger.info(
                    f"Window expired (started {window.window_start}). "
                    f"Starting new window. Previous: {window.tokens_consumed}/{window.estimated_capacity}"
                )
                window = self._new_window()
                self._persist_window(window)
            return window
        except FileNotFoundError:
            window = self._new_window()
            self._persist_window(window)
            return window

    def record_consumption(self, tokens: int, is_cached: bool = False) -> WindowBudget:
        """Record token consumption. Returns updated window.

        Args:
            tokens: Number of tokens consumed
            is_cached: If True, tokens were from cache (don't count toward ITPM
                       rate limits but DO count toward budget window consumption)

        FM-38 FIX: Checks if window expired BEFORE recording. If expired,
        creates a new window and records tokens there. The tokens belong to
        whichever window was active when the API call was made, but since we
        cannot know that precisely, we record against the current (or new) window.
        The key fix is calling get_window() which handles expiry, and NOT
        attributing old-session tokens to a brand-new window.
        """
        window = self.get_window()
        # FM-38: get_window() already handles expiry and creates new window if needed.
        # Tokens are attributed to whichever window get_window() returns.
        window.tokens_consumed += tokens
        window.requests_made += 1
        window.last_request_at = datetime.now(timezone.utc)
        self._persist_window(window)

        # Track cache hits for efficiency metrics
        if is_cached:
            self._cache_hit_tokens += tokens
        self._total_input_tokens += tokens

        # Update weekly budget
        weekly = self.get_weekly()
        weekly.tokens_consumed += tokens
        self._persist_weekly(weekly)

        # Log pressure changes
        pressure = window.pressure_level
        if pressure in (BudgetPressureLevel.ORANGE, BudgetPressureLevel.RED):
            logger.warning(
                f"Budget pressure: {pressure.value} — "
                f"{window.remaining_tokens} tokens remaining in window"
            )

        return window

    def get_weekly(self) -> WeeklyBudget:
        """Get or create the weekly budget tracker."""
        path = f"{self._budget_base}/weekly.yaml"
        try:
            weekly = self.yaml_store.read(path, WeeklyBudget)
            # Check if week has rolled over (Monday boundary)
            now = datetime.now(timezone.utc)
            week_end = weekly.week_start + timedelta(days=7)
            if now >= week_end:
                weekly = self._new_weekly()
                self._persist_weekly(weekly)
            return weekly
        except FileNotFoundError:
            weekly = self._new_weekly()
            self._persist_weekly(weekly)
            return weekly

    # ── Task Budget Estimation ──

    def estimate_task_cost(self, task_type: str, complexity: str = "medium") -> int:
        """Estimate token cost for a task.

        Strategy (TALE-inspired):
        1. Build key from task_type + complexity
        2. If rolling average available (>= ROLLING_AVERAGE_THRESHOLD samples): use it
        3. Otherwise: use cold seed
        4. If neither: use 10,000 default
        5. For novel tasks (no key match): multiply by NOVEL_SAFETY_MARGIN

        Returns estimated total tokens (input + output).
        """
        key = f"{task_type}_{complexity}"

        # Check rolling average
        history = self._token_history.get(key, deque())
        if len(history) >= ROLLING_AVERAGE_THRESHOLD:
            avg = int(sum(history) / len(history))
            logger.debug(f"estimate_task_cost({key}): rolling average = {avg} from {len(history)} samples")
            return avg

        # Fall back to cold seeds (loaded from YAML in __init__)
        seed = self._cold_seeds.get(key, self._cold_seeds.get(task_type))
        if seed is not None:
            logger.debug(f"estimate_task_cost({key}): cold seed = {seed}")
            return seed

        # Unknown type — apply safety margin
        default = 10_000
        novel_estimate = int(default * NOVEL_SAFETY_MARGIN)
        logger.debug(f"estimate_task_cost({key}): unknown type, novel estimate = {novel_estimate}")
        return novel_estimate

    def record_actual_usage(self, task_type: str, complexity: str, tokens_used: int) -> None:
        """Record actual token usage for a completed task.

        Updates the rolling average for future estimates.
        """
        key = f"{task_type}_{complexity}"
        if key not in self._token_history:
            self._token_history[key] = deque(maxlen=50)  # Keep last 50 samples
        self._token_history[key].append(tokens_used)
        logger.info(f"Recorded usage: {key} = {tokens_used} tokens (now {len(self._token_history[key])} samples)")

    # Minimum tokens for a task to be worth starting
    MIN_TASK_BUDGET = 500

    def allocate_task_budget(self, task_type: str, complexity: str = "medium") -> TaskBudgetAnnotation:
        """Allocate a budget for a task before execution starts.

        Allocation = estimate + reserve:
        - estimated_tokens: raw estimate from rolling average or cold seed
        - allocated_tokens: estimated * (1 + BUDGET_RESERVE_PCT)
        - Capped to remaining window tokens
        - FM-37 FIX: Minimum allocation enforced (MIN_TASK_BUDGET).
          If remaining window tokens are below minimum, raises ResourceConstrainedError
          rather than allocating a zero/tiny budget.

        Raises:
            ResourceConstrainedError: If remaining window budget is below MIN_TASK_BUDGET.
        """
        estimated = self.estimate_task_cost(task_type, complexity)
        allocated = int(estimated * (1 + BUDGET_RESERVE_PCT))

        # Cap to remaining window budget
        window = self.get_window()
        if allocated > window.remaining_tokens:
            allocated = window.remaining_tokens
            logger.warning(
                f"Task budget capped to window remaining: {allocated} "
                f"(estimated {estimated}, window has {window.remaining_tokens})"
            )

        # FM-37: Enforce minimum allocation
        if allocated < self.MIN_TASK_BUDGET:
            raise ResourceConstrainedError(
                f"Insufficient window budget for task: {allocated} < {self.MIN_TASK_BUDGET} minimum. "
                f"Window has {window.remaining_tokens} tokens remaining."
            )

        # Determine estimation method
        key = f"{task_type}_{complexity}"
        history = self._token_history.get(key, deque())
        method = "rolling_average" if len(history) >= ROLLING_AVERAGE_THRESHOLD else "cold_seed"

        return TaskBudgetAnnotation(
            estimated_tokens=estimated,
            allocated_tokens=allocated,
            pressure_at_start=window.pressure_level,
            estimation_method=method,
        )

    def get_pressure(self) -> BudgetPressureLevel:
        """Get current budget pressure level."""
        window = self.get_window()
        return window.pressure_level

    def get_budget_summary(self) -> dict:
        """Get a summary of current budget state for agent prompts.

        This is injected into Ring 1 of the agent prompt to provide
        BATS-style continuous budget visibility.
        """
        window = self.get_window()
        weekly = self.get_weekly()
        return {
            "window_remaining_tokens": window.remaining_tokens,
            "window_utilization_pct": round(window.utilization * 100, 1),
            "window_pressure": window.pressure_level.value,
            "weekly_remaining_tokens": weekly.remaining,
            "weekly_utilization_pct": round(weekly.utilization * 100, 1),
        }

    # ── Efficiency Metrics ──

    def compute_efficiency(
        self, task_id: str, input_tokens: int, output_tokens: int,
        cache_hits: int, waste_tokens: int, review_rounds: int,
    ) -> ResourceEfficiencyMetrics:
        """Compute resource efficiency metrics for a completed task.

        FM-54 FIX: Takes separate input_tokens and output_tokens instead of
        combined total_tokens. This ensures cache_hit_rate is computed against
        input tokens only (cache applies only to input), not diluted by output.
        """
        total_tokens = input_tokens + output_tokens
        return ResourceEfficiencyMetrics(
            task_id=task_id,
            cost_of_pass=total_tokens,
            budget_utilization=1.0 - (waste_tokens / total_tokens) if total_tokens > 0 else 0.0,
            cache_hit_tokens=cache_hits,
            total_input_tokens=input_tokens,  # FM-54: input only, not total
            waste_tokens=waste_tokens,
            review_rounds=review_rounds,
        )

    # ── Internal ──

    def _new_window(self) -> WindowBudget:
        return WindowBudget(
            window_start=datetime.now(timezone.utc),
            estimated_capacity=self._window_capacity,
        )

    def _new_weekly(self) -> WeeklyBudget:
        """Create a new weekly budget.

        FM-67 FIX: Aligns week_start to the most recent Monday 00:00 UTC.
        This ensures weekly budget resets coincide with a consistent boundary,
        regardless of when the BudgetTracker was first initialized.
        """
        now = datetime.now(timezone.utc)
        # Align to Monday 00:00 UTC (weekday() returns 0 for Monday)
        days_since_monday = now.weekday()
        monday = now.replace(hour=0, minute=0, second=0, microsecond=0)
        monday -= timedelta(days=days_since_monday)
        return WeeklyBudget(
            week_start=monday,
        )

    def _persist_window(self, window: WindowBudget) -> None:
        self.yaml_store.write(f"{self._budget_base}/window.yaml", window)

    def _persist_weekly(self, weekly: WeeklyBudget) -> None:
        self.yaml_store.write(f"{self._budget_base}/weekly.yaml", weekly)
```

### 3.3 /usage Parsing Upgrade

The existing `ResourceTracker._parse_usage_text()` is retained and enhanced. The `BudgetTracker` delegates to it for primary token tracking (I8: parse Claude Code `/usage` command output).

```python
# In resource_tracker.py — enhanced _parse_usage_text:
@staticmethod
def _parse_usage_text(text: str) -> dict | None:
    """Parse /usage output. Format may change between Claude Code versions.

    Handles known formats:
    - "Input tokens: 10,000" / "Output tokens: 2,500"
    - "Cost: $0.15"
    - "Cache read: 5,000" / "Cache creation: 1,000"
    - "Total tokens: 12,500"
    """
    data: dict = {}
    patterns = {
        "input_tokens": r"[Ii]nput\s+tokens?:\s*([0-9,]+)",
        "output_tokens": r"[Oo]utput\s+tokens?:\s*([0-9,]+)",
        "total_tokens": r"[Tt]otal\s+tokens?:\s*([0-9,]+)",
        "total_cost": r"[Cc]ost:\s*\$([0-9.]+)",
        "cache_read": r"[Cc]ache\s+read:\s*([0-9,]+)",
        "cache_creation": r"[Cc]ache\s+creation:\s*([0-9,]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            val = match.group(1).replace(",", "")
            data[key] = float(val) if "." in val else int(val)
    return data if data else None
```

### 3.4 Budget Injection into Agent Prompts

The `PromptComposer` injects budget summary into Ring 1 (infrastructure ring). This provides BATS-style continuous visibility:

```python
# In prompt_composer.py — _build_ring_1():
def _build_ring_1_resource_awareness(self, budget_summary: dict) -> PromptSection:
    """Inject resource awareness into Ring 1."""
    content = (
        "## Resource Budget\n"
        f"Window: {budget_summary['window_remaining_tokens']:,} tokens remaining "
        f"({budget_summary['window_utilization_pct']}% used)\n"
        f"Pressure: {budget_summary['window_pressure']}\n"
        f"Weekly: {budget_summary['weekly_remaining_tokens']:,} tokens remaining "
        f"({budget_summary['weekly_utilization_pct']}% used)\n"
    )

    # Add behavioral guidance based on pressure
    pressure = budget_summary["window_pressure"]
    if pressure == "yellow":
        content += "\nBUDGET GUIDANCE: Compress context, reduce tool calls, prefer cheaper operations.\n"
    elif pressure == "orange":
        content += "\nBUDGET WARNING: Critical-only tasks. Aggressive compression. Single-agent mode.\n"
    elif pressure == "red":
        content += "\nBUDGET EMERGENCY: Complete active task only. Park everything else. Alert human.\n"

    return PromptSection(
        ring=PromptRing.RING_1,
        name="resource_awareness",
        content=content,
        token_estimate=estimate_tokens(content),  # Module-level function, not method
        compressible=True,
        priority=0.9,  # High priority within Ring 1
    )
```

---

## Part 4: Rate Limit Mirror & Backpressure

### 4.1 Overview

The `RateLimiter` maintains a local mirror of server-side rate limits. Rather than hitting 429 errors and retrying (expensive), the framework predicts when it will hit limits and pauses upstream.

**Key insight:** ATB/AATB algorithm achieves 97.3% fewer 429 errors (arXiv:2510.04516) via client-side prediction. Prompt caching doesn't count toward ITPM — this is rate-limit arbitrage.

### 4.2 Implementation: `engine/rate_limiter.py`

```python
"""Rate limit mirror with backpressure propagation.
Spec reference: Section 18.3 (Rate Limit Management).

Key literature:
- ATB/AATB (arXiv:2510.04516): 97.3% fewer 429 errors
- VTC (arXiv:2401.00588): Fair scheduling with priority weights
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from enum import StrEnum

from ..models.resource import RateLimitBucket, RateLimitMirror
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.rate_limiter")


class RequestPriority(StrEnum):
    """Priority levels for rate-limit queue (VTC-inspired)."""
    CRITICAL = "critical"  # Safety, constitution checks, human-requested
    HIGH = "high"          # Active execution, review mandates
    NORMAL = "normal"      # Scout, routine evolution
    LOW = "low"            # Background analysis, speculation


class BackpressureLevel(StrEnum):
    """System-wide backpressure levels."""
    NONE = "none"           # < 80% capacity
    SLOW = "slow"           # 80% — slow spawning, queue new
    PAUSE = "pause"         # 90% — pause non-critical tasks
    SINGLE_AGENT = "single" # 95% — only highest-priority task
    FULL_STOP = "stop"      # 100% — wait for refresh


class RateLimiter:
    """Local rate limit mirror with ATB-inspired backpressure.

    Responsibilities:
    1. Track RPM, ITPM, OTPM consumption locally
    2. Predict remaining capacity before each request
    3. Propagate backpressure when approaching limits
    4. Handle 429 responses (update mirror from server state)
    5. Priority queue: critical > high > normal > low

    Design invariants:
    - Mirror is pessimistic: overestimates consumption (safe side)
    - Buckets replenish per minute (sliding window approximation)
    - Backpressure propagated as float 0.0-1.0 to orchestrator
    - Cached tokens excluded from ITPM accounting
    - State persisted to YAML for crash recovery
    """

    # Backpressure thresholds (from spec Section 18.3)
    SLOW_THRESHOLD = 0.80
    PAUSE_THRESHOLD = 0.90
    SINGLE_AGENT_THRESHOLD = 0.95
    STOP_THRESHOLD = 1.00

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        rpm_estimate: int = 50,
        itpm_estimate: int = 80_000,
        otpm_estimate: int = 16_000,
    ):
        self.yaml_store = yaml_store
        self.domain = domain
        self._state_path = f"instances/{domain}/state/resources/rate_limits.yaml"

        # Initialize or load mirror
        try:
            self._mirror = yaml_store.read(self._state_path, RateLimitMirror)
        except FileNotFoundError:
            self._mirror = RateLimitMirror(
                rpm=RateLimitBucket(capacity=rpm_estimate, current=0, replenish_rate="per minute"),
                itpm=RateLimitBucket(capacity=itpm_estimate, current=0, replenish_rate="per minute"),
                otpm=RateLimitBucket(capacity=otpm_estimate, current=0, replenish_rate="per minute"),
                last_updated=datetime.now(timezone.utc),
            )
            self._persist()

        # FM-33 FIX: On restart, force an immediate replenishment to clear
        # stale accumulated values from the persisted mirror. Set _last_replenish
        # to 60+ seconds in the past so the first _maybe_replenish() call drains.
        self._last_replenish = time.monotonic() - 60.0

    def record_request(
        self,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
    ) -> None:
        """Record an API request's token consumption.

        Cached tokens do NOT count toward ITPM (rate-limit arbitrage).
        """
        self._maybe_replenish()

        self._mirror.rpm.current += 1
        # Only non-cached input tokens count toward ITPM
        effective_input = input_tokens - cached_tokens
        self._mirror.itpm.current += max(0, effective_input)
        self._mirror.otpm.current += output_tokens
        self._mirror.last_updated = datetime.now(timezone.utc)

        self._persist()

        bp = self.get_backpressure()
        if bp >= self.PAUSE_THRESHOLD:
            logger.warning(
                f"Rate pressure high: backpressure={bp:.2f} "
                f"RPM={self._mirror.rpm.current}/{self._mirror.rpm.capacity} "
                f"ITPM={self._mirror.itpm.current}/{self._mirror.itpm.capacity}"
            )

    def can_send(self, estimated_input: int, estimated_output: int,
                 priority: RequestPriority = RequestPriority.NORMAL) -> tuple[bool, str]:
        """Check if a request can be sent without exceeding limits.

        Critical requests always pass (safety).
        Other priorities checked against remaining capacity.
        """
        if priority == RequestPriority.CRITICAL:
            return True, "Critical priority — always allowed"

        self._maybe_replenish()

        # Check RPM
        if self._mirror.rpm.current >= self._mirror.rpm.capacity:
            return False, f"RPM limit reached: {self._mirror.rpm.current}/{self._mirror.rpm.capacity}"

        # Check ITPM (with headroom)
        if self._mirror.itpm.current + estimated_input > self._mirror.itpm.capacity:
            return False, (
                f"ITPM would exceed limit: {self._mirror.itpm.current} + {estimated_input} "
                f"> {self._mirror.itpm.capacity}"
            )

        # Check OTPM (with headroom)
        if self._mirror.otpm.current + estimated_output > self._mirror.otpm.capacity:
            return False, (
                f"OTPM would exceed limit: {self._mirror.otpm.current} + {estimated_output} "
                f"> {self._mirror.otpm.capacity}"
            )

        return True, "Within rate limits"

    def get_backpressure(self) -> float:
        """Compute overall backpressure level (0.0-1.0).

        Takes the maximum utilization across all three buckets.
        """
        self._maybe_replenish()

        rpm_util = self._mirror.rpm.current / max(1, self._mirror.rpm.capacity)
        itpm_util = self._mirror.itpm.current / max(1, self._mirror.itpm.capacity)
        otpm_util = self._mirror.otpm.current / max(1, self._mirror.otpm.capacity)

        return max(rpm_util, itpm_util, otpm_util)

    def get_backpressure_level(self) -> BackpressureLevel:
        """Get the backpressure level as a named enum."""
        bp = self.get_backpressure()
        if bp >= self.STOP_THRESHOLD:
            return BackpressureLevel.FULL_STOP
        if bp >= self.SINGLE_AGENT_THRESHOLD:
            return BackpressureLevel.SINGLE_AGENT
        if bp >= self.PAUSE_THRESHOLD:
            return BackpressureLevel.PAUSE
        if bp >= self.SLOW_THRESHOLD:
            return BackpressureLevel.SLOW
        return BackpressureLevel.NONE

    def handle_429(self, retry_after: float | None = None) -> float:
        """Handle a 429 rate limit response.

        Updates mirror to reflect server state (we're at limit).
        Returns recommended wait time in seconds.

        Anti-pattern: NEVER accumulate retry queues — pause upstream instead.

        FM-23 FIX: Marks ALL THREE buckets at capacity (not just RPM).
        A 429 could be triggered by any bucket. Pessimistically assume all are full.
        """
        # Mark ALL buckets as at capacity (pessimistic — FM-23)
        self._mirror.rpm.current = self._mirror.rpm.capacity
        self._mirror.itpm.current = self._mirror.itpm.capacity
        self._mirror.otpm.current = self._mirror.otpm.capacity
        self._mirror.last_updated = datetime.now(timezone.utc)
        self._persist()

        wait = retry_after if retry_after else 60.0
        logger.warning(f"429 received. Waiting {wait}s. Backpressure propagated.")
        return wait

    def update_from_headers(self, headers: dict) -> None:
        """Update mirror from API response headers.

        Claude API may return rate limit info in headers.
        This is the most accurate source of truth.

        FM-60 NOTE: OTPM headers are also parsed if present. As of Phase 1.5,
        the Claude API may not expose separate output token rate headers. If
        they become available, this method handles them automatically.
        """
        if "x-ratelimit-limit-requests" in headers:
            self._mirror.rpm.capacity = int(headers["x-ratelimit-limit-requests"])
        if "x-ratelimit-remaining-requests" in headers:
            remaining = int(headers["x-ratelimit-remaining-requests"])
            self._mirror.rpm.current = self._mirror.rpm.capacity - remaining
        if "x-ratelimit-limit-tokens" in headers:
            self._mirror.itpm.capacity = int(headers["x-ratelimit-limit-tokens"])
        if "x-ratelimit-remaining-tokens" in headers:
            remaining = int(headers["x-ratelimit-remaining-tokens"])
            self._mirror.itpm.current = self._mirror.itpm.capacity - remaining
        # FM-60: Parse OTPM headers if available
        if "x-ratelimit-limit-output-tokens" in headers:
            self._mirror.otpm.capacity = int(headers["x-ratelimit-limit-output-tokens"])
        if "x-ratelimit-remaining-output-tokens" in headers:
            remaining = int(headers["x-ratelimit-remaining-output-tokens"])
            self._mirror.otpm.current = self._mirror.otpm.capacity - remaining

        self._mirror.last_updated = datetime.now(timezone.utc)
        self._persist()

    # ── Internal ──

    def _maybe_replenish(self) -> None:
        """Replenish buckets based on elapsed time.

        Token bucket model: each bucket replenishes its full capacity every
        60 seconds (sliding window approximation). After N elapsed minutes,
        we subtract N * capacity from the current count, clamped to 0.

        Example with RPM capacity=50:
        - At t=0: current=45 (45 requests made)
        - After 1 minute: current = max(0, 45 - 50) = 0 (fully replenished)
        - After 2 minutes with current=120: current = max(0, 120 - 2*50) = 20

        This is pessimistic (safe): we assume the worst-case sliding window
        rather than tracking exact per-request timestamps.

        FM-44 FIX: Advance _last_replenish by exactly `minutes * 60` seconds
        (not `now`) to preserve the fractional remainder. This prevents
        cumulative under-replenishment that would cause increasingly aggressive
        backpressure over long sessions.
        """
        now = time.monotonic()
        elapsed = now - self._last_replenish
        if elapsed >= 60.0:
            minutes = int(elapsed / 60.0)
            for _ in range(minutes):
                self._mirror.rpm.current = max(0, self._mirror.rpm.current - self._mirror.rpm.capacity)
                self._mirror.itpm.current = max(0, self._mirror.itpm.current - self._mirror.itpm.capacity)
                self._mirror.otpm.current = max(0, self._mirror.otpm.current - self._mirror.otpm.capacity)
            # FM-44: Advance by exact minutes, preserving fractional remainder
            self._last_replenish += minutes * 60.0

    def _persist(self) -> None:
        """Persist mirror state."""
        self.yaml_store.ensure_dir(f"instances/{self.domain}/state/resources")
        self.yaml_store.write(self._state_path, self._mirror)
```

### 4.3 Backpressure Integration with Orchestrator

The orchestrator checks backpressure before every resource-consuming action.

**IMPORTANT (FM-08):** All accesses to `self.rate_limiter` and `self.budget_tracker` MUST
be guarded with null checks (`if self.rate_limiter:`). Part 7.2 is the canonical version.
This Part 4.3 block shows the detailed backpressure logic. The two MUST be consistent.

**IMPORTANT (FM-68):** Backpressure checks use `elif` (not `if`) to prevent cascading
evaluation. FULL_STOP > SINGLE_AGENT > PAUSE — only the highest-level block executes.

**IMPORTANT (FM-25):** Solo topology downgrade uses `pattern="pipeline"` with
`agent_count=2` (implementer + reviewer) rather than `pattern="solo"` with
`agent_count=2`, which contradicts the solo pattern definition (1 agent).
Using "pipeline" preserves the review step while reducing agent concurrency.

**IMPORTANT (FM-17):** INTAKE tasks that cannot be parked are added to a
`deferred_intake_tasks` list persisted to YAML. The orchestrator re-checks this list
on every `process_task()` call when pressure returns to GREEN.

```python
# In orchestrator.py — process_task():
def process_task(self, task_id: str, domain_config: DomainConfig, actor: str = "orchestrator") -> dict:
    """Full orchestration pipeline. Signature preserves existing `actor` parameter."""
    # ... existing analysis/routing (uses `actor` for transitions) ...

    # NEW: Re-check deferred INTAKE tasks when pressure is GREEN
    if self.budget_tracker and self.rate_limiter:
        if (self.budget_tracker.get_pressure() == BudgetPressureLevel.GREEN
                and self.rate_limiter.get_backpressure_level() == BackpressureLevel.NONE):
            self._retry_deferred_intake_tasks(domain_config, actor)

    # NEW: Check backpressure before team creation (FM-08: null-guarded)
    if self.rate_limiter:
        bp_level = self.rate_limiter.get_backpressure_level()

        # FM-68: Use elif chain — only highest-level block executes
        if bp_level == BackpressureLevel.FULL_STOP:
            # Only park if task is already in a parkable state (PLANNING or later).
            # INTAKE tasks cannot be parked (invalid transition) — defer instead.
            task = self.task_lifecycle._load_task(task_id)
            if task.status in (TaskStatus.PLANNING, TaskStatus.EXECUTING):
                self.task_lifecycle.park(task_id, "Rate limit — full stop", actor)
            elif task.status == TaskStatus.INTAKE:
                self._defer_intake_task(task_id, "Rate limit — full stop")
            raise ResourceConstrainedError("Rate limit at capacity. Task deferred. Wait for window refresh.")

        elif bp_level == BackpressureLevel.SINGLE_AGENT:
            # FM-25: Downgrade to pipeline (not "solo" which is defined as 1 agent)
            routing = RoutingResult(
                pattern="pipeline", agent_count=2,
                role_assignments=[
                    {"role": "implementer", "model": "sonnet", "purpose": "execute"},
                    {"role": "reviewer", "model": "sonnet", "purpose": "review"},
                ],
                inject_scout=False,
                rationale="Downgraded to pipeline: rate pressure at single-agent level",
            )

        elif bp_level == BackpressureLevel.PAUSE:
            # Only allow high/critical priority tasks
            task = self.task_lifecycle._load_task(task_id)
            if task.priority not in ("high", "critical"):
                if task.status in (TaskStatus.PLANNING, TaskStatus.EXECUTING):
                    self.task_lifecycle.park(task_id, "Rate limit — non-critical paused", actor)
                elif task.status == TaskStatus.INTAKE:
                    self._defer_intake_task(task_id, "Rate limit — non-critical paused")
                raise ResourceConstrainedError("Non-critical task deferred under rate pressure.")

    # Budget pressure: RED means complete active task only (FM-08: null-guarded)
    if self.budget_tracker:
        budget_pressure = self.budget_tracker.get_pressure()
        if budget_pressure == BudgetPressureLevel.RED:
            task = self.task_lifecycle._load_task(task_id)
            if task.priority not in ("high", "critical"):
                if task.status in (TaskStatus.PLANNING, TaskStatus.EXECUTING):
                    self.task_lifecycle.park(task_id, "Budget RED — non-critical deferred", actor)
                elif task.status == TaskStatus.INTAKE:
                    self._defer_intake_task(task_id, "Budget RED — non-critical deferred")
                raise ResourceConstrainedError("Budget at RED. Only critical tasks proceed.")

    # ... continue with team creation ...


# FM-17: Deferred INTAKE task tracking
def _defer_intake_task(self, task_id: str, reason: str) -> None:
    """Track INTAKE tasks that couldn't be parked for later retry."""
    path = f"instances/{self._domain}/state/tasks/deferred_intake.yaml"
    try:
        deferred = self.yaml_store.read_raw(path)
    except FileNotFoundError:
        deferred = {"tasks": []}
    if task_id not in [d["id"] for d in deferred["tasks"]]:
        deferred["tasks"].append({
            "id": task_id,
            "reason": reason,
            "deferred_at": datetime.now(timezone.utc).isoformat(),
        })
        self.yaml_store.write_raw(path, deferred)
    logger.info(f"Deferred INTAKE task {task_id}: {reason}")

def _retry_deferred_intake_tasks(self, domain_config: DomainConfig, actor: str) -> None:
    """Retry deferred INTAKE tasks when pressure returns to GREEN."""
    path = f"instances/{self._domain}/state/tasks/deferred_intake.yaml"
    try:
        deferred = self.yaml_store.read_raw(path)
    except FileNotFoundError:
        return
    if not deferred.get("tasks"):
        return
    # Process oldest first, clear the list
    tasks_to_retry = deferred["tasks"]
    deferred["tasks"] = []
    self.yaml_store.write_raw(path, deferred)
    for entry in tasks_to_retry:
        logger.info(f"Retrying deferred INTAKE task: {entry['id']}")
        # Re-submit will be picked up by normal task queue
```

---

## Part 5: Prompt Caching Strategy

### 5.1 Overview

Prompt caching is the highest-leverage optimization in Phase 1.5. Cached tokens don't count toward ITPM, so caching the shared system prefix (constitution + framework config) across all agents effectively multiplies ITPM throughput by 2-5x.

**Anthropic caching requirements:**
- Minimum cache block size: 1024 tokens
- Cache TTL: 5 minutes (refreshed on use)
- System prompt must be identical for cache hits

### 5.2 Implementation: `engine/cache_manager.py`

```python
"""Prompt caching strategy for rate-limit arbitrage.
Spec reference: Section 18.3 (Caching Strategy).

Key insight: Cached tokens don't count toward ITPM.
By caching the shared prefix (constitution + config), we get 2-5x effective ITPM.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from ..models.base import FrameworkModel

logger = logging.getLogger("uagents.cache_manager")


class CacheStats(FrameworkModel):
    """Cache hit/miss tracking."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    tokens_saved: int = 0  # Tokens that didn't count toward ITPM

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests


class CacheManager:
    """Manages prompt caching for rate-limit arbitrage.

    Strategy (Section 18.3):
    1. Shared system prompt prefix across all agents
       - Constitution (Ring 0): ~500 tokens, NEVER changes within session
       - Framework config (Ring 1): ~300 tokens, changes on evolution only
       - Resource awareness (Ring 1): ~100 tokens, changes per window
    2. Role-specific fragments appended AFTER shared prefix
    3. Task context appended last (most variable)

    Cache hierarchy (most → least stable):
    - Level 1: Constitution + axioms (~500 tokens) — session-stable
    - Level 2: Role composition (~200 tokens) — task-stable
    - Level 3: Resource awareness (~100 tokens) — window-stable
    - Level 4: Task context — changes per request (not cached)

    Design invariants:
    - Shared prefix must exceed 1024 tokens for Anthropic cache
    - Prefix must be IDENTICAL across agents for cache hits
    - Constitution hash checked on every cache refresh
    """

    # Minimum tokens for effective caching (Anthropic requirement)
    MIN_CACHE_BLOCK = 1024

    def __init__(self):
        self._prefix_cache: str | None = None
        self._prefix_hash: str | None = None
        self._prefix_tokens: int = 0
        self.stats = CacheStats()

    def get_shared_prefix(self, constitution_text: str, framework_config: str) -> str:
        """Get the cached shared prefix, rebuilding if changed.

        Returns the system prompt prefix that should be identical
        across all agents to maximize cache hits.
        """
        # Compute hash of inputs
        content = constitution_text + framework_config
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        if self._prefix_hash == content_hash and self._prefix_cache is not None:
            self.stats.cache_hits += 1
            self.stats.total_requests += 1
            return self._prefix_cache

        # Cache miss — rebuild prefix
        self._prefix_cache = self._build_prefix(constitution_text, framework_config)
        self._prefix_hash = content_hash
        # FM-35 FIX: Use same CHARS_PER_TOKEN as PromptComposer (3.5, not 4)
        self._prefix_tokens = int(len(self._prefix_cache) / 3.5)
        self.stats.cache_misses += 1
        self.stats.total_requests += 1

        if self._prefix_tokens < self.MIN_CACHE_BLOCK:
            logger.warning(
                f"Shared prefix is only ~{self._prefix_tokens} tokens, "
                f"below {self.MIN_CACHE_BLOCK} minimum for cache hits. "
                f"Consider adding more shared content."
            )

        return self._prefix_cache

    def estimate_cache_savings(self, total_input_tokens: int) -> int:
        """Estimate tokens saved from caching on a request.

        If the prefix is cached, those tokens don't count toward ITPM.

        FM-36 NOTE: This method is ESTIMATION ONLY — it does NOT update stats.
        Call `record_cache_savings()` after the request to update stats once.
        """
        if self._prefix_tokens > 0:
            return min(self._prefix_tokens, total_input_tokens)
        return 0

    def record_cache_savings(self, saved_tokens: int) -> None:
        """Record actual cache savings after a request completes.

        FM-36 FIX: Separated from estimate_cache_savings() to prevent
        double-counting when estimate is called multiple times per request.
        """
        self.stats.tokens_saved += saved_tokens

    def _build_prefix(self, constitution_text: str, framework_config: str) -> str:
        """Build the shared prefix from constitution + config.

        Order matters for cache hits — must be identical across all agents.
        """
        return (
            "# CONSTITUTION (Ring 0 — immutable)\n"
            f"{constitution_text}\n\n"
            "# FRAMEWORK CONFIGURATION\n"
            f"{framework_config}\n"
        )
```

### 5.3 PromptSection Model Modification

Add `is_cached` field to `PromptSection` (in `prompt_composer.py`):

```python
class PromptSection(FrameworkModel):
    """A discrete section of the composed prompt."""
    ring: PromptRing
    name: str            # Stable key — NEVER mutate after construction
    content: str
    token_estimate: int
    compressible: bool   # Ring 0 = False, all others = True
    priority: float      # 0.0 = drop first, 1.0 = drop last (within ring)
    is_cached: bool = False  # Phase 1.5: True if section is in shared cache prefix
```

### 5.4 Integration with PromptComposer

**FM-20 FIX:** The previous version used undefined `ring_0_section` and
`ring_1_infra_section` variables. The correct approach joins content from
the section lists returned by `_build_ring_0()` and `_build_ring_1()`.

**FM-21 FIX:** `_build_ring_1_resource_awareness()` is called inside `compose()`
when a `budget_summary` parameter is provided. It adds a section to the Ring 1
list. The `compose()` signature gains `budget_summary: dict | None = None` and
`cache_manager: CacheManager | None = None`.

```python
# In prompt_composer.py — compose():
def compose(
    self,
    domain: DomainConfig,
    role: RoleComposition,
    task: Task | None = None,
    budget_summary: dict | None = None,       # FM-21: budget injection
    cache_manager: CacheManager | None = None, # FM-20: cache integration
) -> ComposedPrompt:
    """Compose a prompt from ring sections.

    Phase 1.5 additions:
    - budget_summary: injected into Ring 1 via _build_ring_1_resource_awareness()
    - cache_manager: marks Ring 0/1 sections as cached for token accounting
    """
    sections: list[PromptSection] = []

    # Ring 0: Constitution + safety
    ring_0_sections = self._build_ring_0()
    sections.extend(ring_0_sections)

    # Ring 1: Infrastructure + config
    ring_1_sections = self._build_ring_1(domain)
    # FM-21: Add resource awareness to Ring 1 if budget_summary provided
    if budget_summary is not None:
        ring_1_sections.append(self._build_ring_1_resource_awareness(budget_summary))
    sections.extend(ring_1_sections)

    # ... existing Ring 2 (role) and Ring 3 (task) assembly ...

    # FM-20 FIX: Use joined content from ring section lists (not undefined variables)
    if cache_manager:
        ring_0_content = "\n".join(s.content for s in ring_0_sections)
        ring_1_content = "\n".join(s.content for s in ring_1_sections)
        shared_prefix = cache_manager.get_shared_prefix(ring_0_content, ring_1_content)

        # Mark prefix sections as cached for token accounting.
        # Uses a separate `is_cached` field — NEVER mutate section.name
        # (name is used as a stable key for compression and debugging).
        for section in sections:
            if section.ring in (PromptRing.RING_0, PromptRing.RING_1):
                section.is_cached = True

    # ... continue with assembly ...
```

---

## Part 6: Cost Approval Workflow

### 6.1 Overview

While Claude API calls are covered by subscription (SpendLevel.FREE), some agent actions incur real monetary costs: web API calls, cloud provisioning, SaaS subscriptions. The cost gate enforces approval workflows based on spend level.

### 6.2 Implementation: `engine/cost_gate.py`

```python
"""Monetary cost approval gateway.
Spec reference: Section 18.5 (Cost-Aware Decision Making).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..models.base import generate_id
from ..models.resource import CostApproval, CostRecord, DailyCostSummary, SpendLevel
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.cost_gate")


class CostCapExceededError(RuntimeError):
    """Raised when daily/weekly cost cap would be exceeded."""


class ApprovalRequiredError(RuntimeError):
    """Raised when human approval is needed for a cost."""
    def __init__(self, approval: CostApproval):
        self.approval = approval
        super().__init__(
            f"Human approval required: {approval.purpose} "
            f"(${approval.amount:.2f}, level={approval.spend_level.name})"
        )


class CostGate:
    """Enforces monetary cost approval tiers.

    Spend levels (Section 18.5):
    - FREE (0): File ops, git, Claude API — automatic
    - LOW (1): Web search, small API < $0.10 — auto with logging, daily cap
    - MEDIUM (2): Large API $0.10-$10 — async human approval (30min timeout)
    - HIGH (3): SaaS, > $10 — synchronous human approval required

    Design invariants:
    - Every cost-incurring action logged with amount, purpose, approval
    - Daily cap enforced regardless of spend level
    - Weekly cap enforced regardless of spend level
    - No action proceeds without explicit approval at correct level
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        daily_cap: float = 10.0,
        weekly_cap: float = 50.0,
    ):
        self.yaml_store = yaml_store
        self.domain = domain
        self.daily_cap = daily_cap
        self.weekly_cap = weekly_cap
        self._costs_base = f"instances/{domain}/state/resources/costs"

    def request_approval(
        self,
        amount: float,
        purpose: str,
        task_id: str | None = None,
        agent_id: str | None = None,
    ) -> CostApproval:
        """Request approval for a cost-incurring action.

        Returns CostApproval with approved=True for auto-approved levels.
        Raises ApprovalRequiredError for levels needing human input.
        Raises CostCapExceededError if daily/weekly cap would be exceeded.
        """
        level = self._classify_spend(amount)

        # Check caps first
        self._check_caps(amount)

        if level == SpendLevel.FREE:
            return CostApproval(spend_level=level, amount=amount, purpose=purpose, approved=True)

        if level == SpendLevel.LOW:
            # Auto-approve with logging
            approval = CostApproval(
                spend_level=level, amount=amount, purpose=purpose,
                approved=True, approved_by="auto_low"
            )
            self._record_cost(approval, task_id, agent_id)
            return approval

        if level == SpendLevel.MEDIUM:
            # Requires async human approval
            approval = CostApproval(
                spend_level=level, amount=amount, purpose=purpose, approved=False
            )
            self._record_cost(approval, task_id, agent_id)
            raise ApprovalRequiredError(approval)

        # HIGH
        approval = CostApproval(
            spend_level=level, amount=amount, purpose=purpose, approved=False
        )
        self._record_cost(approval, task_id, agent_id)
        raise ApprovalRequiredError(approval)

    def approve(self, record_id: str, approver: str) -> CostRecord:
        """Human approves a pending cost record.

        FM-43 FIX: After approving, update daily summary's total_spent.
        Without this, MEDIUM/HIGH approved costs would never be reflected
        in the daily cap, allowing unlimited spending.
        """
        record = self._load_record(record_id)
        record.approved = True
        record.approved_by = approver
        self._save_record(record)

        # FM-43: Update daily summary with the approved amount
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily = self.get_daily_summary()
        daily.total_spent += record.amount
        self.yaml_store.write(f"{self._costs_base}/daily/{today}.yaml", daily)

        logger.info(f"Cost approved: {record.purpose} (${record.amount:.2f}) by {approver}")
        return record

    def reject(self, record_id: str, reason: str) -> CostRecord:
        """Human rejects a pending cost record."""
        record = self._load_record(record_id)
        record.approved = False
        record.approved_by = f"REJECTED: {reason}"
        self._save_record(record)
        logger.info(f"Cost rejected: {record.purpose} — {reason}")
        return record

    def get_daily_summary(self) -> DailyCostSummary:
        """Get today's cost summary."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = f"{self._costs_base}/daily/{today}.yaml"
        try:
            return self.yaml_store.read(path, DailyCostSummary)
        except FileNotFoundError:
            return DailyCostSummary(date=today, daily_cap=self.daily_cap)

    def _classify_spend(self, amount: float) -> SpendLevel:
        """Classify monetary amount into spend level."""
        if amount <= 0:
            return SpendLevel.FREE
        if amount < 0.10:
            return SpendLevel.LOW
        if amount < 10.0:
            return SpendLevel.MEDIUM
        return SpendLevel.HIGH

    def _check_caps(self, amount: float) -> None:
        """Check daily and weekly caps. Raises CostCapExceededError if exceeded.

        Both caps are enforced. No silent pass-through (fail-loud policy).
        """
        daily = self.get_daily_summary()
        if daily.total_spent + amount > self.daily_cap:
            raise CostCapExceededError(
                f"Daily cap would be exceeded: ${daily.total_spent:.2f} + ${amount:.2f} "
                f"> ${self.daily_cap:.2f}"
            )

        # Weekly cap: aggregate last 7 daily summaries
        weekly_total = self._get_weekly_total()
        if weekly_total + amount > self.weekly_cap:
            raise CostCapExceededError(
                f"Weekly cap would be exceeded: ${weekly_total:.2f} + ${amount:.2f} "
                f"> ${self.weekly_cap:.2f}"
            )

    def _get_weekly_total(self) -> float:
        """Sum daily totals for the last 7 days."""
        from datetime import timedelta
        total = 0.0
        today = datetime.now(timezone.utc).date()
        for i in range(7):
            day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            path = f"{self._costs_base}/daily/{day}.yaml"
            try:
                summary = self.yaml_store.read(path, DailyCostSummary)
                total += summary.total_spent
            except FileNotFoundError:
                continue
        return total

    def _record_cost(self, approval: CostApproval, task_id: str | None, agent_id: str | None) -> CostRecord:
        """Create and persist a cost record."""
        record = CostRecord(
            id=generate_id("cost"),
            timestamp=datetime.now(timezone.utc),
            spend_level=approval.spend_level,
            amount=approval.amount,
            purpose=approval.purpose,
            approved=approval.approved,
            approved_by=approval.approved_by,
            task_id=task_id,
            agent_id=agent_id,
        )
        self._save_record(record)

        # Update daily summary
        # FM-42 FIX: Only add to daily records if approved. Unapproved records
        # are tracked only in their individual YAML files, not in the daily summary.
        # This prevents mixing approved/unapproved in the same list.
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily = self.get_daily_summary()
        if approval.approved:
            daily.total_spent += approval.amount
            daily.records.append(record.id)
            self.yaml_store.write(f"{self._costs_base}/daily/{today}.yaml", daily)

        return record

    def _save_record(self, record: CostRecord) -> None:
        self.yaml_store.ensure_dir(self._costs_base)
        self.yaml_store.ensure_dir(f"{self._costs_base}/daily")
        self.yaml_store.write(f"{self._costs_base}/{record.id}.yaml", record)

    def _load_record(self, record_id: str) -> CostRecord:
        return self.yaml_store.read(f"{self._costs_base}/{record_id}.yaml", CostRecord)
```

---

## Part 7: Budget-Aware Orchestration

### 7.1 Orchestrator Integration

The orchestrator becomes budget-aware at three decision points:

1. **Before task processing**: Check budget pressure, allocate task budget
2. **Before team creation**: Check backpressure, downgrade topology if needed
3. **After task completion**: Record efficiency metrics, update rolling averages

### 7.2 Modified `orchestrator.py`

```python
# FM-61: Required imports for Phase 1.5 additions:
from ..engine.budget_tracker import BudgetTracker
from ..engine.rate_limiter import BackpressureLevel, RateLimiter
from ..engine.cost_gate import CostGate
from ..models.resource import BudgetPressureLevel

class ResourceConstrainedError(RuntimeError):
    """Raised when resource constraints prevent task processing."""

# In Orchestrator.__init__():
def __init__(
    self,
    yaml_store: YamlStore,
    topology_router: TopologyRouter,
    team_manager: TeamManager,
    task_lifecycle: TaskLifecycle,
    review_engine: ReviewEngine,
    budget_tracker: BudgetTracker | None = None,     # NEW
    rate_limiter: RateLimiter | None = None,          # NEW
    cost_gate: CostGate | None = None,                # NEW
):
    # ... existing ...
    self.budget_tracker = budget_tracker
    self.rate_limiter = rate_limiter
    self.cost_gate = cost_gate

# In process_task() — budget-aware additions (preserves existing `actor` parameter):
def process_task(self, task_id: str, domain_config: DomainConfig, actor: str = "orchestrator") -> dict:
    """Full pipeline: INTAKE → ANALYSIS → PLANNING → EXECUTING.

    Phase 1.5 additions:
    - Budget pressure check before processing
    - Task budget allocation
    - Backpressure-aware topology downgrade (see Part 4.3 for full logic)
    - Budget injection into team's resource context
    """
    # 1. Budget pressure check (RED = critical-only)
    # Note: parking only valid from PLANNING/EXECUTING states, not INTAKE.
    # See Part 4.3 for full backpressure logic with state-aware parking.
    if self.budget_tracker:
        pressure = self.budget_tracker.get_pressure()
        if pressure == BudgetPressureLevel.RED:
            task = self.task_lifecycle._load_task(task_id)
            if task.priority not in ("high", "critical"):
                if task.status in (TaskStatus.PLANNING, TaskStatus.EXECUTING):
                    self.task_lifecycle.park(task_id, "Budget RED — non-critical deferred", actor)
                raise ResourceConstrainedError(
                    f"Budget pressure RED. Task {task_id} deferred. "
                    f"Window: {self.budget_tracker.get_window().remaining_tokens} tokens remaining."
                )

    # 2. Rate limit backpressure check
    if self.rate_limiter:
        bp_level = self.rate_limiter.get_backpressure_level()
        # ... backpressure handling as shown in Part 4.3 (state-aware parking) ...

    # 3. Allocate task budget
    task = self.task_lifecycle._load_task(task_id)
    if self.budget_tracker:
        task_budget = self.budget_tracker.allocate_task_budget(
            task_type=self._classify_task_type(task),
            complexity=self._classify_complexity(task),
        )
        task.budget = task_budget
        # Persist budget annotation
        self.yaml_store.write(
            f"instances/{domain_config.name}/state/tasks/active/{task_id}.yaml", task
        )

    # ... existing analysis, routing, team creation (using `actor`) ...

    return result


# In complete_execution() — preserves existing `actor` parameter:
def complete_execution(self, task_id: str, actor: str = "orchestrator") -> Task:
    """Transition EXECUTING → REVIEWING.

    Phase 1.5: Record token consumption for the task.
    """
    task = self.task_lifecycle.transition(
        task_id, TaskStatus.REVIEWING, actor, "Execution complete"
    )

    # Record efficiency metrics
    if self.budget_tracker and task.budget:
        self.budget_tracker.record_actual_usage(
            task_type=self._classify_task_type(task),
            complexity=self._classify_complexity(task),
            tokens_used=task.budget.spent_tokens,
        )

    return task


# Helper methods (FM-16: These MUST be implemented in orchestrator.py):
def _classify_task_type(self, task: Task) -> str:
    """Classify task into type for budget estimation.

    FM-40 FIX: Uses priority-ordered matching to avoid ambiguous classification.
    Most specific patterns checked first (canary, evolution, decomposition),
    then general patterns (fix, research, feature). Default is "feature_medium".

    Returns a key that matches cold_seeds in resource-awareness.yaml.
    """
    title_lower = task.title.lower()
    desc_lower = (task.description or "").lower()
    combined = title_lower + " " + desc_lower

    # Check specific Phase 1.5 task types first (most specific)
    if "canary" in combined:
        return "canary_suite"
    if "evolution" in combined or "evolve" in combined:
        return "evolution_proposal"
    if "decompos" in combined or "subtask" in combined:
        return "decomposition"
    if "skill" in combined and ("valid" in combined or "crystal" in combined):
        return "skill_validation"
    if "review" in combined:
        return "review"
    # General patterns (less specific)
    if any(w in combined for w in ("fix", "typo", "bug", "patch")):
        return "simple_fix"
    if any(w in combined for w in ("research", "analyze", "investigat", "survey")):
        return "research"
    if any(w in combined for w in ("implement", "add", "create", "build")):
        return "feature"
    return "feature"

def _classify_complexity(self, task: Task) -> str:
    """Classify task complexity for budget estimation.

    FM-41 NOTE: Description length is a poor proxy for complexity.
    This is a Phase 1.5 heuristic that will be replaced by a learned
    classifier in Phase 2+ (using actual token consumption data).

    Phase 1.5 improvement: Also considers number of subtasks and
    explicit complexity hints in the description.
    """
    desc = task.description or ""
    desc_lower = desc.lower()

    # Check for explicit complexity hints
    if any(w in desc_lower for w in ("trivial", "simple", "quick", "minor")):
        return "small"
    if any(w in desc_lower for w in ("complex", "large", "extensive", "major", "refactor")):
        return "large"

    # Fall back to description length (imperfect but usable)
    desc_len = len(desc)
    if desc_len < 100:
        return "small"
    if desc_len < 400:
        return "medium"
    return "large"
```

### 7.3 Agent Spawner Budget Check

```python
# AgentSpawner.__init__() — add optional new parameters:
def __init__(
    self,
    prompt_composer: PromptComposer,
    resource_tracker: ResourceTracker,
    yaml_store: YamlStore,
    domain: str = "meta",
    budget_tracker: BudgetTracker | None = None,     # NEW Phase 1.5
    rate_limiter: RateLimiter | None = None,          # NEW Phase 1.5
):
    # ... existing ...
    self.budget_tracker = budget_tracker
    self.rate_limiter = rate_limiter

# In agent_spawner.py — spawn():
def spawn(self, ...):
    """Resource-checked agent spawning.

    Phase 1.5: Check budget + rate limits in addition to compute.
    Spawn policy rules (spec Section 18.4):
    - FULL_STOP: no agents spawn
    - SINGLE_AGENT: only if no other agents are active
    - RED budget: no spawn
    - ORANGE budget: only high/critical priority tasks
    """
    # Existing: compute resource check
    can, reason = self.resource_tracker.can_spawn_agent()
    if not can:
        raise ResourceConstrainedError(f"Cannot spawn: {reason}")

    # NEW: Rate limit check
    if self.rate_limiter:
        bp = self.rate_limiter.get_backpressure_level()
        if bp in (BackpressureLevel.FULL_STOP, BackpressureLevel.SINGLE_AGENT):
            raise ResourceConstrainedError(
                f"Cannot spawn: rate limit backpressure at {bp.value}"
            )

    # NEW: Budget check
    if self.budget_tracker:
        pressure = self.budget_tracker.get_pressure()
        if pressure == BudgetPressureLevel.RED:
            raise ResourceConstrainedError(
                f"Cannot spawn: budget pressure RED "
                f"({self.budget_tracker.get_window().remaining_tokens} tokens remaining)"
            )

    # ... existing compose + register ...
```

### 7.4 Idle Agent Despawn

```python
# New method in agent_spawner.py:
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
```

---

## Part 8: Self-Improving Resource Efficiency

### 8.1 Overview

Every 10 completed tasks, the framework computes resource efficiency trends and stores them in the audit log. This establishes the baseline for Phase 2+ self-improvement.

### 8.2 Efficiency Metrics (Section 18.6)

| Metric | Definition | Target |
|--------|-----------|--------|
| `cost_of_pass` | Total tokens to achieve one successful task completion | Baseline, then 10% quarterly improvement |
| `tokens_per_quality_point` | Token efficiency normalized by output quality | Lower is better |
| `budget_utilization` | Productive tokens / total consumed | > 70% |
| `cache_hit_rate` | Cached tokens / total input tokens | > 50% after warmup |
| `waste_detection` | Tokens in failed approaches / total | < 30% |

### 8.3 Trend Computation

```python
# In budget_tracker.py:
def compute_trends(self, recent_metrics: list[ResourceEfficiencyMetrics]) -> dict:
    """Compute efficiency trends from recent task metrics.

    Called after every 10 completed tasks.
    Returns trend data for audit logging and evolution triggers.
    """
    if len(recent_metrics) < 2:
        return {"status": "insufficient_data", "count": len(recent_metrics)}

    costs = [m.cost_of_pass for m in recent_metrics]
    utils = [m.budget_utilization for m in recent_metrics]
    cache_rates = [m.cache_hit_rate for m in recent_metrics]
    wastes = [m.waste_tokens / max(1, m.cost_of_pass) for m in recent_metrics]

    # Simple trend: compare first half vs second half
    mid = len(recent_metrics) // 2
    first_half_cost = sum(costs[:mid]) / mid
    second_half_cost = sum(costs[mid:]) / (len(costs) - mid)

    avg_waste = sum(wastes) / len(wastes)
    avg_cache = sum(cache_rates) / len(cache_rates)
    avg_util = sum(utils) / len(utils)

    return {
        "status": "computed",
        "task_count": len(recent_metrics),
        "avg_cost_of_pass": int(sum(costs) / len(costs)),
        "cost_trend": "improving" if second_half_cost < first_half_cost else "degrading",
        "avg_budget_utilization": round(avg_util, 3),
        "avg_cache_hit_rate": round(avg_cache, 3),
        "avg_waste_ratio": round(avg_waste, 3),
        "needs_attention": avg_waste > 0.30 or avg_util < 0.50,
    }
```

---

## Part 9: Implementation Sequence

### 9.1 Dependency Graph

**FM-06 FIX:** `ensure_dir()` must be added to YamlStore BEFORE Steps 2-4
(BudgetTracker, RateLimiter, CostGate all call `yaml_store.ensure_dir()` in
their constructors). The YAML config (Step 14) must also precede Step 2
(BudgetTracker loads cold seeds from YAML on init). Reordered:

```
Step 0: YAML config: core/resource-awareness.yaml (FM-06: before Step 2)
  │
Step 0.5: YamlStore.ensure_dir() (FM-06: before Steps 2-4)
  │
Step 0.7: Datetime migration: datetime.utcnow() → datetime.now(timezone.utc) (FM-05)
  │
Step 1: New resource models (models/resource.py)
  │
  ├─→ Step 2: BudgetTracker (engine/budget_tracker.py)
  │     │     [depends on: Step 0 (YAML config), Step 0.5 (ensure_dir), Step 1 (models)]
  │     │
  ├─→ Step 3: RateLimiter (engine/rate_limiter.py)
  │     │     [depends on: Step 0.5 (ensure_dir), Step 1 (models)]
  │     │
  └─→ Step 4: CostGate (engine/cost_gate.py)
        │     [depends on: Step 0.5 (ensure_dir), Step 1 (models)]
        │
Step 5: CacheManager (engine/cache_manager.py)
  │
Step 6: ResourceTracker integration (delegate to BudgetTracker; remove COLD_SEEDS)
  │     [depends on: Step 2 (BudgetTracker)]
  │
Step 7: Orchestrator budget awareness + _classify_task_type()/_classify_complexity()
  │     [depends on: Steps 2, 3, 4, 6]
  │
Step 8: AgentSpawner budget/rate checks + idle despawn
  │     [depends on: Steps 2, 3]
  │
Step 9: PromptComposer cache-aware prefix + budget injection
  │     [depends on: Steps 2, 5]
  │
Step 10: Task model budget annotation
  │
Step 11: Audit logging for resource events
  │
Step 12: Tests for all new components (including CacheManager — FM-55)
  │
Step 13: Integration test: full lifecycle with budget tracking
```

### 9.2 Step Details

**Step 0: YAML config** (~50 lines, `core/resource-awareness.yaml`)
- FM-06: Must exist BEFORE BudgetTracker init (loads cold seeds from YAML)
- Contains all configurable thresholds, cold seeds, rate limit estimates
- Verify: `uv run python -c "import yaml; yaml.safe_load(open('core/resource-awareness.yaml'))"`

**Step 0.5: YamlStore.ensure_dir()** (~10 lines added to `state/yaml_store.py`)
- FM-06: Public method for directory creation, wrapping private `_resolve()`
- Must exist before Steps 2-4 (BudgetTracker, RateLimiter, CostGate all call it)
- Verify: `uv run pytest tests/test_state/ -v`

**Step 0.7: Datetime migration** (~20 lines changed across 4 files)
- FM-05: Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)`
- Files: task_lifecycle.py, agent_spawner.py, team_manager.py, orchestrator.py
- Verify: `grep -r "utcnow" src/` returns zero matches

**Step 1: New resource models** (~120 lines added to `models/resource.py`)
- Add `WindowBudget`, `WeeklyBudget`, `ResourceSnapshot`, `CostRecord`, `DailyCostSummary`, `TaskBudgetAnnotation`, `ResourceEfficiencyMetrics`
- Verify: `uv run pytest tests/test_models/ -v`

**Step 2: BudgetTracker** (~250 lines, new file)
- BATS-style budget visibility: window, weekly, per-task
- Cold seeds loaded from YAML (no hardcoded fallback)
- Cold seeds → rolling average transition at 10 samples
- Pressure level computation
- Budget summary for prompt injection
- Verify: `uv run pytest tests/test_engine/test_budget_tracker.py -v`

**Step 3: RateLimiter** (~250 lines, new file)
- Local token bucket mirror (RPM, ITPM, OTPM)
- Backpressure computation (0.0-1.0)
- 429 handling with mirror update
- Header-based mirror refresh
- Verify: `uv run pytest tests/test_engine/test_rate_limiter.py -v`

**Step 4: CostGate** (~200 lines, new file)
- Spend level classification
- Auto-approve FREE/LOW, raise for MEDIUM/HIGH
- Daily AND weekly cap enforcement (both fail-loud)
- Cost record persistence
- Verify: `uv run pytest tests/test_engine/test_cost_gate.py -v`

**Step 5: CacheManager** (~100 lines, new file)
- Shared prefix construction (constitution + config)
- Hash-based invalidation
- Cache statistics tracking
- FM-55: Tests ARE required (not optional). Add `tests/test_engine/test_cache_manager.py`
- Verify: `uv run pytest tests/test_engine/test_cache_manager.py -v`

**Step 6: ResourceTracker integration** (~40 lines modified)
- Wire `budget_tracker` and `rate_limiter` into existing `ResourceTracker`
- Delegate `get_backpressure_level()` to `rate_limiter`
- FM-14/FM-22/FM-24: Delegate `estimate_task_cost()` to `budget_tracker` (remove COLD_SEEDS dict)
- FM-15: Delegate `record_actual_usage()` with signature adapter (2-param → 3-param)
- **Deprecate** `ResourceTracker._token_history` — all token tracking now in `BudgetTracker`
- Note: `ensure_dir()` already added in Step 0.5 (FM-06)

**Step 7: Orchestrator budget awareness** (~60 lines modified)
- Budget pressure check before processing
- Backpressure-aware topology downgrade
- Task budget allocation
- Efficiency recording after completion

**Step 8: AgentSpawner upgrades** (~30 lines modified)
- Budget + rate limit checks in `spawn()` and `spawn_for_team()`
- `despawn_idle_agents()` method

**Step 9: PromptComposer caching** (~40 lines modified)
- Cache-aware prefix assembly
- Budget summary injection into Ring 1

**Step 10: Task model update** (~5 lines)
- Add `budget: TaskBudgetAnnotation | None = None` to Task

**Step 10.5: ResourceFacade** (~60 lines, new helper in `engine/resource_facade.py`)
- FM-64: Single entry point wrapping BudgetTracker + RateLimiter for consumption recording
- FM-56: Constructs `ResourceSnapshot` before every spawn/task-start decision
- FM-65: Calls `AuditLogger.log_resource()` with `ResourceLogEntry` for audit trail

```python
class ResourceFacade:
    """Single entry point for recording resource consumption (FM-64).

    Wraps BudgetTracker and RateLimiter to ensure consistent recording.
    Also constructs ResourceSnapshot (FM-56) and logs to audit (FM-65).
    """
    def __init__(self, budget_tracker: BudgetTracker, rate_limiter: RateLimiter,
                 resource_tracker: ResourceTracker, audit_logger: AuditLogger | None = None):
        self.budget = budget_tracker
        self.rate = rate_limiter
        self.compute = resource_tracker
        self.audit = audit_logger

    def record_consumption(self, input_tokens: int, output_tokens: int,
                           cached_tokens: int = 0) -> None:
        """Record token consumption in both budget and rate tracking."""
        total = input_tokens + output_tokens
        self.budget.record_consumption(total, is_cached=(cached_tokens > 0))
        self.rate.record_request(input_tokens, output_tokens, cached_tokens)

    def take_snapshot(self, reason: str) -> ResourceSnapshot:
        """Create a point-in-time snapshot (FM-56)."""
        window = self.budget.get_window()
        weekly = self.budget.get_weekly()
        compute = self.compute.check_resources()
        snapshot = ResourceSnapshot(
            timestamp=datetime.now(timezone.utc),
            compute=compute,
            window_budget=window,
            weekly_budget=weekly,
            rate_pressure=self.rate.get_backpressure(),
            budget_pressure=window.pressure_level,
            can_spawn=compute.cpu_pct < 85.0 and window.pressure_level != BudgetPressureLevel.RED,
            spawn_rejection_reason=None,
        )
        if self.audit:
            self.audit.log_resource(ResourceLogEntry(
                stream=LogStream.RESOURCES, event=reason, data=snapshot.model_dump()
            ))
        return snapshot
```

**Step 11: Audit logging** (~20 lines)
- FM-65: Resource events logged to RESOURCES stream via ResourceFacade

**Step 12: Unit tests** (~600 lines across 4 test files)
- BudgetTracker: window lifecycle, rolling average, pressure levels, allocation, min budget
- RateLimiter: bucket tracking, backpressure, 429 handling (all 3 buckets), replenishment
- CostGate: spend classification, cap enforcement, approval workflow, approve() updates daily
- FM-55: CacheManager: prefix construction, hash invalidation, token estimation, savings tracking

**Step 13: Integration test** (~100 lines)
- Full lifecycle with budget tracking: create → process → execute → complete
- Verify budget annotations persisted on task
- Verify efficiency metrics computed
- Verify datetime round-trip (FM-05): WindowBudget → YAML → WindowBudget preserves timezone

### 9.3 Estimated Sizes

| Component | New Lines | Modified Lines | Tests |
|-----------|-----------|----------------|-------|
| Models (resource.py) | ~120 | ~5 | ~20 |
| BudgetTracker | ~250 | — | ~40 |
| RateLimiter | ~250 | — | ~40 |
| CostGate | ~180 | — | ~30 |
| CacheManager | ~100 | — | ~15 |
| ResourceTracker mods | — | ~30 | ~10 |
| Orchestrator mods | — | ~60 | ~15 |
| AgentSpawner mods | — | ~30 | ~10 |
| PromptComposer mods | — | ~40 | ~10 |
| Task model | — | ~5 | — |
| Audit logging | — | ~20 | — |
| Integration test | ~100 | — | ~10 |
| YAML config | ~50 | — | — |
| **Total** | **~1050** | **~190** | **~200** |

---

## Part 10: Verification Checklist

### 10.1 Unit Tests

| # | What | Command | Expected |
|---|------|---------|----------|
| 1 | Budget tracker window lifecycle | `uv run pytest tests/test_engine/test_budget_tracker.py -v` | All pass |
| 2 | Budget tracker cold seed → rolling average | Same as above | Transitions at 10 samples (ROLLING_AVERAGE_THRESHOLD) |
| 3 | Budget tracker pressure levels | Same as above | GREEN/YELLOW/ORANGE/RED at correct thresholds |
| 4 | Rate limiter bucket tracking | `uv run pytest tests/test_engine/test_rate_limiter.py -v` | All pass |
| 5 | Rate limiter backpressure | Same as above | 0.0-1.0 range, named levels |
| 6 | Rate limiter 429 handling | Same as above | Mirror updated, wait time returned |
| 7 | Rate limiter replenishment | Same as above | Buckets replenish after 60s |
| 8 | Cost gate spend classification | `uv run pytest tests/test_engine/test_cost_gate.py -v` | All pass |
| 9 | Cost gate auto-approve LOW | Same as above | Approved without human |
| 10 | Cost gate reject MEDIUM/HIGH | Same as above | ApprovalRequiredError raised |
| 11 | Cost gate daily cap | Same as above | CostCapExceededError raised |
| 11b | Cost gate weekly cap | Same as above | CostCapExceededError raised when 7-day total exceeds weekly_cap |
| 12 | Cache manager prefix construction | Manual or test | Prefix > 1024 tokens |
| 13 | Cache manager hash invalidation | Manual or test | Rebuilds on content change |

### 10.2 Integration Tests

| # | What | Command | Expected |
|---|------|---------|----------|
| 14 | Full lifecycle with budget | `uv run pytest tests/test_integration/ -v` | Budget annotations on completed task |
| 15 | Orchestrator parks on RED pressure | Integration test | Task parked, ResourceConstrainedError |
| 16 | Topology downgrade on high backpressure | Integration test | Solo topology regardless of analysis |
| 17 | Idle agent despawn | Unit test | Agents despawned after timeout |

### 10.3 Regression

| # | What | Command | Expected |
|---|------|---------|----------|
| 18 | All existing tests still pass | `uv run pytest --tb=long -v` | 254+ passed, 0 failed |
| 19 | Phase 0 + Phase 1 lifecycle unchanged | Integration test | Same behavior when budget_tracker=None |

---

## Part 11: Edge Cases, Failure Modes & Mitigations

Total: **67 failure modes** (20 documented in original design + 47 discovered in review).
Full analysis: `research/phase1.5-failure-modes.md`.

### 11.1 Critical Severity (8 total)

| ID | Failure Mode | Impact | Mitigation | Status |
|----|-------------|--------|------------|--------|
| R1 | Window budget file corrupted mid-write | Lost budget tracking | Atomic write via YamlStore (temp + replace). On corrupt read: log warning, create new window. | Original |
| R2 | Rate limiter out of sync with server | 429 errors | Mirror is pessimistic. On 429: update ALL 3 buckets (FM-23 fix), propagate backpressure. | Original |
| R3 | Budget annotation lost on task transition | Task untracked | Task budget persisted before transition. If lost: log warning, treat as unbounded. | Original |
| R4 | Daily cost cap bypassed by concurrent agents | Spending exceeds cap | YamlStore locking for daily summary. Race window small (seconds). | Original |
| FM-05 | Timezone mismatch: utcnow() vs now(timezone.utc) | TypeError crash | Step 0.7: Migrate ALL datetime.utcnow() to datetime.now(timezone.utc). Add round-trip test. | **FIXED** |
| FM-06 | ensure_dir() missing; Steps 2-4 crash on init | AttributeError | Step 0.5: Add ensure_dir() to YamlStore BEFORE Steps 2-4. Reordered dependency graph. | **FIXED** |
| FM-07 | extra="forbid" breaks forward compat | ValidationError on rollback | Atomic deployment. Document in Appendix D. No partial deployment. | **FIXED** |
| FM-08 | Contradictory null guards Part 4.3 vs 7.2 | AttributeError or crash | Part 7.2 is canonical. All accesses guarded with `if self.rate_limiter:`. | **FIXED** |

### 11.2 High Severity (17 total)

| ID | Failure Mode | Impact | Mitigation | Status |
|----|-------------|--------|------------|--------|
| R5 | Window capacity estimate wrong | Over/under-budgeting | Empirical tracking: adjust from 429 frequency. | Original |
| R6 | Rolling average polluted by outlier | Inaccurate estimates | deque(maxlen=50). Phase 2: IQR filtering. | Original |
| R7 | All tasks park (system stalls) | No progress | CRITICAL priority always allowed. Single-agent mode runs one task. | Original |
| R8 | Cost records accumulate unboundedly | Disk fills | Phase 2: archive records older than 30 days. | Original |
| R9 | Cache prefix changes frequently | No cache hits | Constitution session-stable. Config changes only on evolution. | Original |
| FM-14 | Double-counting between ResourceTracker and BudgetTracker | Divergent estimates | Step 6: ResourceTracker delegates to BudgetTracker. See §3.1.2. | **FIXED** |
| FM-15 | record_actual_usage() signature mismatch (2 vs 3 params) | TypeError | Step 6: Adapter wrapper in ResourceTracker. See §3.1.2. | **FIXED** |
| FM-16 | _classify_task_type()/_classify_complexity() missing | AttributeError | Implemented in Part 7.2 with priority-ordered matching (FM-40 fix). | **FIXED** |
| FM-17 | INTAKE task orphaned after transient RED | Silent work loss | _defer_intake_task() + _retry_deferred_intake_tasks() on GREEN. See Part 4.3. | **FIXED** |
| FM-18 | Non-atomic read-modify-write on window budget | Under-counting | Accepted for Phase 1.5 (low concurrency). Phase 2: append-only ledger. See §3.1.1. | **DOCUMENTED** |
| FM-19 | Same race on weekly budget | Under-counting weekly | Same as FM-18. | **DOCUMENTED** |
| FM-20 | Cache integration uses undefined variables | NameError | Fixed: use joined content from ring_0_sections/ring_1_sections lists. See Part 5.4. | **FIXED** |
| FM-21 | _build_ring_1_resource_awareness() integration undefined | Ambiguous impl | compose() gains budget_summary param. Calls _build_ring_1_resource_awareness(). See Part 5.4. | **FIXED** |
| FM-22 | Duplicate estimate_task_cost() with different seeds | Divergent estimates | Step 6: Remove COLD_SEEDS from ResourceTracker, delegate to BudgetTracker. See §3.1.2. | **FIXED** |
| FM-23 | handle_429() only marks RPM at capacity | ITPM/OTPM still appears available | Fixed: All three buckets marked at capacity. See Part 4.2. | **FIXED** |
| FM-24 | Hardcoded COLD_SEEDS diverges from YAML | Inconsistent estimates | Step 6: Remove hardcoded dict. BudgetTracker is sole source. See §3.1.2. | **FIXED** |
| FM-25 | Solo downgrade has agent_count=2 (contradicts solo=1) | 2 agents under SINGLE_AGENT | Fixed: Use pattern="pipeline" with agent_count=2. See Part 4.3. | **FIXED** |

### 11.3 Medium Severity (19 total)

| ID | Failure Mode | Impact | Mitigation | Status |
|----|-------------|--------|------------|--------|
| R10 | budget_tracker=None (backwards compat) | No budget features | Guarded with `if self.budget_tracker:`. | Original |
| R11 | Token history lost on restart | Cold seeds used | Phase 2: persist to YAML. | Original |
| R12 | Cache below 1024 token minimum | No cache benefit | CacheManager logs warning. Pad if needed. | Original |
| R13 | OTPM estimate wrong | Bad backpressure | Conservative start (16K). Adjust from headers. FM-60: parse OTPM headers. | Original+**FIXED** |
| R14 | Weekly cap too conservative | Unnecessary parking | Start 1M. Adjust empirically. | Original |
| FM-31 | PromptSection.is_cached breaks rollback | ValidationError | Same atomic deployment constraint as FM-07. See §2.3. | **DOCUMENTED** |
| FM-32 | _maybe_replenish() 60s boundary | Conservative backpressure up to 59s | Acceptable: pessimistic=safe. Documented. | **DOCUMENTED** |
| FM-33 | Ghost backpressure on restart | False blocking 60s | Fixed: _last_replenish set 60s in past on init. | **FIXED** |
| FM-34 | Properties not in model_dump() | External tools miss derived values | Acceptable: properties are dynamic. External tools compute from raw fields. | **ACCEPTED** |
| FM-35 | CacheManager uses 4 c/t vs 3.5 c/t | 12.5% token underestimate | Fixed: Use 3.5 c/t consistently. | **FIXED** |
| FM-36 | estimate_cache_savings() accumulates | Double-counted savings | Fixed: Split into estimate (pure) + record (stateful). | **FIXED** |
| FM-37 | Zero-token budget allocation allowed | Task starts with no budget | Fixed: MIN_TASK_BUDGET=500. ResourceConstrainedError if below. | **FIXED** |
| FM-38 | Old-window tokens attributed to new window | Inflated new window | Documented: get_window() handles expiry. Tokens go to current window. | **DOCUMENTED** |
| FM-39 | Multiple task loads in process_task() | Budget annotation lost | Amplifies R3. Mitigated by persisting budget before transitions. | **DOCUMENTED** |
| FM-40 | _classify_task_type() order-dependent | Wrong budget estimates | Fixed: Priority-ordered matching (specific → general). | **FIXED** |
| FM-41 | _classify_complexity() based on desc length | Disconnected from reality | Improved: checks explicit keywords first, then length. Phase 2: learned classifier. | **FIXED** |
| FM-42 | Unapproved records in daily summary list | Mixed approved/unapproved | Fixed: Only approved records added to daily.records. | **FIXED** |
| FM-43 | approve() doesn't update daily.total_spent | Daily cap never triggered for MEDIUM/HIGH | Fixed: approve() reloads daily, adds amount, persists. | **FIXED** |
| FM-44 | _maybe_replenish() loses fractional minutes | Cumulative under-replenishment | Fixed: Advance _last_replenish by exact minutes*60, not now. | **FIXED** |
| FM-45 | DailyCostSummary.date no format validation | Misformatted dates silently skipped | Fixed: @field_validator enforces YYYY-MM-DD. See §2.5. | **FIXED** |

### 11.4 Low Severity (23 total)

| ID | Failure Mode | Impact | Mitigation | Status |
|----|-------------|--------|------------|--------|
| R15 | Efficiency trends show "degrading" | No auto-action | Phase 2 evolution engine. | Original |
| R16 | Cost records not cleaned up | Minor disk usage | Phase 2: archival policy. | Original |
| R17 | Budget pressure flickers | Log noise | Hysteresis: 2 consecutive checks. | Original |
| R18 | Idle despawn races with task assignment | Agent lost before task | Check current_task before despawn. | Original |
| R19 | Spawn policy rules incomplete | Spawns that should be blocked | Explicit checks for all levels. Test all paths. | Original |
| R20 | Parking INTAKE tasks (invalid) | State machine violation | Guard: check task.status. INTAKE → defer. | Original+**FIXED** |
| FM-52 | CacheManager no persistence | Stats lost on restart | Acceptable for Phase 1.5. Phase 2: persist to YAML. | **ACCEPTED** |
| FM-53 | check_agent_health() string vs StrEnum | Comparison may fail | StrEnum comparison works for lowercase. Document: YAML must store lowercase. | **DOCUMENTED** |
| FM-54 | compute_efficiency() total_tokens as input | Cache hit rate diluted | Fixed: Separate input_tokens and output_tokens params. | **FIXED** |
| FM-55 | No tests for CacheManager | Untested code deployed | Fixed: test_cache_manager.py added to Step 12. | **FIXED** |
| FM-56 | ResourceSnapshot never constructed | Dead code | Fixed: ResourceFacade.take_snapshot() creates snapshots. See Step 10.5. | **FIXED** |
| FM-57 | No integration parse_usage→BudgetTracker | Budget tracks explicit calls only | Phase 2: Wire parse_usage_output() into ResourceFacade.record_consumption(). | **DEFERRED** |
| FM-58 | BudgetTracker init misleading FileNotFoundError | Confusing debug | Fixed: Raises ValueError with structure details. | **FIXED** |
| FM-59 | _cache_hit_tokens not persisted | Session-scoped only | Same as R11. Phase 2: persist counters. | **ACCEPTED** |
| FM-60 | update_from_headers() ignores OTPM | OTPM never calibrated | Fixed: Parse x-ratelimit-*-output-tokens headers. | **FIXED** |
| FM-61 | Missing imports in orchestrator code | NameError | Fixed: Import block shown in Part 7.2. | **FIXED** |
| FM-62 | _get_weekly_total() midnight edge case | Missed cost at midnight | Narrow race. Acceptable for Phase 1.5. | **ACCEPTED** |
| FM-63 | despawn_idle_agents() skips agents without heartbeat | Legacy agents accumulate | Phase 2: Add heartbeat requirement. Phase 1.5: acceptable (few legacy agents). | **DEFERRED** |
| FM-64 | No single entry point for consumption | Budget/rate diverge | Fixed: ResourceFacade wraps both. See Step 10.5. | **FIXED** |
| FM-65 | Resource audit logging never called | No audit trail | Fixed: ResourceFacade.take_snapshot() logs to audit. See Step 10.5. | **FIXED** |
| FM-66 | get_budget_summary() non-atomic reads | Minor inconsistency | Acceptable: summary is advisory. Agents don't make hard decisions from it. | **ACCEPTED** |
| FM-67 | _new_weekly() doesn't align to Monday | Week boundary mismatch | Fixed: Aligns to most recent Monday 00:00 UTC. | **FIXED** |
| FM-68 | Backpressure if/elif cascade bug | Non-critical tasks parked at SINGLE_AGENT | Fixed: Use elif chain in Part 4.3. Only highest-level block executes. | **FIXED** |

---

## Appendix A: Literature References (Top 15 for Phase 1.5)

| Paper | Key Contribution | ArXiv |
|-------|-----------------|-------|
| BATS | Budget tracker concept, budget awareness mandatory | 2511.17006 |
| TALE | Estimation + prompting, 67% output reduction | 2412.18547 |
| Tokenomics | 59.4% of tokens in review, input > output | 2601.14470 |
| ATB/AATB | Client-side rate limiting, 97.3% fewer 429s | 2510.04516 |
| VTC | Fair token scheduling with priority weights | 2401.00588 |
| FrugalGPT | Model cascading, up to 98% cost reduction | 2305.05176 |
| CoRL | Budget-parameterized RL policies | 2511.02755 |
| HASHIRU | Resource-aware CEO/employee agents | 2506.04255 |
| Co-Saving | Experience shortcuts, 50.85% token reduction | 2505.21898 |
| ITR | Dynamic system instructions, 95% context reduction | 2602.17046 |
| CodeAgents | Communication efficiency, 55-87% input reduction | 2507.03254 |
| AgentDropout | Graph pruning, 21.6% prompt reduction | 2503.18891 |
| BudgetMLAgent | Planner+workers cascade, 94.2% cost reduction | 2411.07464 |
| ReliabilityBench | Rate limiting most damaging fault for agents | 2601.06112 |
| Efficient Agents | Cost-of-pass optimization, 28.4% improvement | 2508.02694 |

## Appendix B: YAML Config Reference

See `core/resource-awareness.yaml` in Part 2.3.

## Appendix C: Claude Max Token Estimates

| Plan | Window Duration | Est. Tokens/Window | Est. Weekly Cap | Source |
|------|----------------|-------------------|-----------------|--------|
| Max5 | 5 hours | 88,000 | ~1,000,000 | Empirical / community reports |
| Max20 | 5 hours | 220,000 | ~2,500,000 | Empirical / community reports |

These estimates are **not official** and may change. The framework detects actual limits empirically and adjusts.

## Appendix D: Backwards Compatibility

All Phase 1.5 components are **optional at the API level**. When `budget_tracker=None`,
`rate_limiter=None`, or `cost_gate=None`, the framework behaves exactly as Phase 1 — no
budget checks, no backpressure, no cost approval. All integration points are guarded:

```python
if self.budget_tracker:
    # Phase 1.5 behavior
# else: Phase 1 behavior (no change)
```

**FM-07 CONSTRAINT:** However, YAML-level compatibility is **one-directional** only:

| Direction | Supported? | Explanation |
|-----------|-----------|-------------|
| Phase 1.5 reading Phase 1 YAML | YES | New fields have defaults (`budget=None`, `tokens_consumed=0`) |
| Phase 1 reading Phase 1.5 YAML | **NO** | `extra="forbid"` rejects unknown fields (`budget`, `is_cached`) |
| Partial deployment (mixed) | **NO** | YAML written by 1.5 crashes 1.0 readers |

**Deployment constraint:** Phase 1.5 MUST be deployed atomically (all-or-nothing).
Rollback requires clearing YAML files that contain new fields, or running a migration
script that strips the new fields.

This means Phase 1.5 has **zero regression risk for behavior** but **non-zero rollback
risk for data**. Document this in release notes.
