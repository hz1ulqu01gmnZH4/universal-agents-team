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

from ..models.resource import (
    BudgetPressureLevel,
    ResourceEfficiencyMetrics,
    TaskBudgetAnnotation,
    WeeklyBudget,
    WindowBudget,
)
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.budget_tracker")


class ResourceConstrainedError(RuntimeError):
    """Raised when there are insufficient resources to proceed."""


class BudgetTracker:
    """Provides continuous budget visibility to agents and orchestrator.

    Responsibilities:
    1. Track token consumption per window, per week, per task
    2. Estimate task costs (cold seeds -> rolling average)
    3. Compute budget pressure levels
    4. Allocate budgets to subtasks with reserve
    5. Persist budget state to YAML for crash recovery

    Design invariants:
    - Budget state persisted after every update (crash recovery)
    - Pressure levels computed from remaining tokens, not spent
    - Rolling average replaces cold seeds after ROLLING_AVERAGE_THRESHOLD samples
    - 20% budget reserved for unexpected needs
    """

    # Minimum tokens for a task to be worth starting (FM-37)
    MIN_TASK_BUDGET = 500

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
        # FM-58: ValueError for structure issues, FileNotFoundError propagates if missing
        config = yaml_store.read_raw("core/resource-awareness.yaml")
        raw_seeds = config.get("resource_awareness", {}).get("cold_seeds")
        if raw_seeds is None:
            raise ValueError(
                "core/resource-awareness.yaml has unexpected structure: "
                "missing 'resource_awareness.cold_seeds' section. "
                "Expected YAML structure: resource_awareness: { cold_seeds: { ... } }"
            )
        self._cold_seeds: dict[str, int] = {str(k): int(v) for k, v in raw_seeds.items()}

        # Load config thresholds
        ra = config.get("resource_awareness", {})
        self._rolling_threshold = int(ra.get("rolling_average_threshold", 10))
        self._safety_margin = float(ra.get("safety_margin_novel", 1.5))
        self._budget_reserve_pct = float(ra.get("budget_reserve_pct", 0.20))

        # Token history for rolling averages (in-memory; rebuilt from audit logs on restart)
        self._token_history: dict[str, deque[int]] = {}

        # Cache hit tracking (consumed by compute_efficiency)
        self._cache_hit_tokens: int = 0
        self._total_input_tokens: int = 0

        # Ensure resource state directory exists
        self.yaml_store.ensure_dir(self._budget_base)

        # FM-18: Append-only consumption ledger
        # S-6: Use absolute path from yaml_store base_dir
        from ..state.jsonl_writer import JsonlWriter
        from ..models.audit import LogStream
        ledger_dir = self.yaml_store.base_dir / f"instances/{domain}/state/resources/consumption"
        self._consumption_ledger = JsonlWriter(
            log_dir=ledger_dir,
            stream=LogStream.RESOURCES,
            max_size_mb=5,
            max_rotated_files=5,
        )
        # FM-89: Cached window totals for fast reads
        self._cached_window: WindowBudget | None = None
        self._cached_window_mtime: float = 0.0

        # R11: Load persisted token history
        self._load_token_history()

    # ── Window Management ──

    def get_window(self) -> WindowBudget:
        """Get current window budget (FM-18: rebuilt from consumption ledger)."""
        return self._rebuild_window_from_ledger()

    def record_consumption(self, tokens: int, is_cached: bool = False) -> WindowBudget:
        """Record token consumption via append-only ledger (FM-18).

        M-2: Uses JsonlWriter.append() with a proper ConsumptionLogEntry
        instead of bypassing the writer's API. This ensures consistent
        locking, secret scrubbing, and rotation.
        """
        # Ensure window metadata exists BEFORE appending, so window_start <= entry timestamp
        self._get_or_create_window_metadata()

        now = datetime.now(timezone.utc)

        # M-2: Append via JsonlWriter API with proper typed entry
        from ..models.audit import ConsumptionLogEntry
        from ..models.base import generate_id
        entry = ConsumptionLogEntry(
            id=generate_id("cons"),
            timestamp=now,
            tokens=tokens,
            is_cached=is_cached,
        )
        self._consumption_ledger.append(entry)

        # Invalidate cache since we just wrote (mtime may not change within same second)
        self._cached_window = None
        self._cached_window_mtime = 0.0

        # Rebuild window from ledger (FM-89: with caching)
        window = self._rebuild_window_from_ledger()
        self._persist_window(window)  # Also update cache

        # Track cache hits for efficiency metrics
        if is_cached:
            self._cache_hit_tokens += tokens
        self._total_input_tokens += tokens

        # FM-97: Weekly budget also uses ledger approach (not read-modify-write)
        self._increment_weekly_ledger(tokens)

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

        R6 fix: IQR filtering on rolling average to remove outlier contamination.
        """
        key = f"{task_type}_{complexity}"

        # Check rolling average with IQR filtering
        history = self._token_history.get(key, deque())
        if len(history) >= self._rolling_threshold:
            filtered = self._iqr_filter(list(history))
            if filtered:
                avg = int(sum(filtered) / len(filtered))
                logger.debug(
                    f"estimate_task_cost({key}): IQR-filtered average = {avg} "
                    f"from {len(filtered)}/{len(history)} samples"
                )
                return avg

        # Fall back to cold seeds
        seed = self._cold_seeds.get(key, self._cold_seeds.get(task_type))
        if seed is not None:
            logger.debug(f"estimate_task_cost({key}): cold seed = {seed}")
            return seed

        # Unknown type — apply safety margin
        default = 10_000
        novel_estimate = int(default * self._safety_margin)
        logger.debug(f"estimate_task_cost({key}): unknown type, novel estimate = {novel_estimate}")
        return novel_estimate

    @staticmethod
    def _iqr_filter(values: list[int]) -> list[int]:
        """Remove outliers using IQR method. Returns filtered list."""
        if len(values) < 4:
            return values
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[3 * n // 4]
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        return [v for v in values if lower <= v <= upper]

    def record_actual_usage(self, task_type: str, complexity: str, tokens_used: int) -> None:
        """Record actual token usage for a completed task."""
        key = f"{task_type}_{complexity}"
        if key not in self._token_history:
            self._token_history[key] = deque(maxlen=50)
        self._token_history[key].append(tokens_used)
        self._persist_token_history()  # R11: persist immediately
        logger.info(f"Recorded usage: {key} = {tokens_used} tokens (now {len(self._token_history[key])} samples)")

    def allocate_task_budget(self, task_type: str, complexity: str = "medium") -> TaskBudgetAnnotation:
        """Allocate a budget for a task before execution starts.

        FM-37: Minimum allocation enforced (MIN_TASK_BUDGET).
        """
        estimated = self.estimate_task_cost(task_type, complexity)
        allocated = int(estimated * (1 + self._budget_reserve_pct))

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
        method = "rolling_average" if len(history) >= self._rolling_threshold else "cold_seed"

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

        FM-54: Takes separate input_tokens and output_tokens.
        """
        total_tokens = input_tokens + output_tokens
        return ResourceEfficiencyMetrics(
            task_id=task_id,
            cost_of_pass=total_tokens,
            budget_utilization=1.0 - (waste_tokens / total_tokens) if total_tokens > 0 else 0.0,
            cache_hit_tokens=cache_hits,
            total_input_tokens=input_tokens,
            waste_tokens=waste_tokens,
            review_rounds=review_rounds,
        )

    def compute_trends(self, metrics: list[ResourceEfficiencyMetrics]) -> dict:
        """Compute efficiency trends from a list of metrics.

        R15: Returns trend data including a degrading flag that the
        StagnationDetector can consume.
        """
        if len(metrics) < 2:
            return {"status": "insufficient_data", "degrading": False}

        mid = len(metrics) // 2
        first_half = metrics[:mid]
        second_half = metrics[mid:]

        first_avg = sum(m.cost_of_pass for m in first_half) / len(first_half)
        second_avg = sum(m.cost_of_pass for m in second_half) / len(second_half)

        if second_avg < first_avg * 0.9:
            trend = "improving"
        elif second_avg > first_avg * 1.1:
            trend = "degrading"
        else:
            trend = "stable"

        return {
            "status": "computed",
            "cost_trend": trend,
            "degrading": trend == "degrading",
            "task_count": len(metrics),
            "first_half_avg": round(first_avg),
            "second_half_avg": round(second_avg),
        }

    # ── Internal ──

    def _increment_weekly_ledger(self, tokens: int) -> None:
        """FM-97: Atomic weekly budget increment via file lock.

        Uses a separate fcntl lock spanning the full read-modify-write
        cycle for the weekly budget, preventing the race condition.
        """
        import fcntl
        lock_path = self.yaml_store.base_dir / f"{self._budget_base}/weekly.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "w") as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
            try:
                weekly = self.get_weekly()
                weekly.tokens_consumed += tokens
                self._persist_weekly(weekly)
            finally:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)

    def _rebuild_window_from_ledger(self) -> WindowBudget:
        """Rebuild window budget by summing consumption records within window.

        FM-18: This is the authoritative source of truth for token consumption.
        FM-89/S-3: Caches window totals. Only re-scans ledger if file mtime changed.
        """
        # FM-89: Check if cached window is still fresh
        try:
            current_mtime = self._consumption_ledger.current_path.stat().st_mtime
        except FileNotFoundError:
            current_mtime = 0.0

        if (
            self._cached_window is not None
            and current_mtime == self._cached_window_mtime
        ):
            return self._cached_window

        window = self._get_or_create_window_metadata()
        window_start = window.window_start

        # Sum consumption from ledger
        total_tokens = 0
        total_requests = 0
        last_request = None

        entries = self._consumption_ledger.read_entries(
            since=window_start, limit=10_000
        )
        for entry in entries:
            total_tokens += entry.get("tokens", 0)
            total_requests += 1
            ts = entry.get("timestamp")
            if ts:
                last_request = ts

        window.tokens_consumed = total_tokens
        window.requests_made = total_requests
        if last_request:
            window.last_request_at = datetime.fromisoformat(last_request)

        # FM-89: Update cache
        self._cached_window = window
        self._cached_window_mtime = current_mtime

        return window

    def _get_or_create_window_metadata(self) -> WindowBudget:
        """Get window metadata (start time, capacity) or create new."""
        path = f"{self._budget_base}/window.yaml"
        try:
            window = self.yaml_store.read(path, WindowBudget)
            now = datetime.now(timezone.utc)
            window_end = window.window_start + timedelta(hours=window.window_duration_hours)
            if now >= window_end:
                logger.info(f"Window expired. Starting new window.")
                window = self._new_window()
                self._persist_window(window)
                # FM-89: Invalidate cache on window change
                self._cached_window = None
                self._cached_window_mtime = 0.0
            return window
        except FileNotFoundError:
            window = self._new_window()
            self._persist_window(window)
            return window

    def _persist_token_history(self) -> None:
        """R11: Persist token history to YAML for crash recovery."""
        data = {
            "history": {k: list(v) for k, v in self._token_history.items()},
            "cache_hit_tokens": self._cache_hit_tokens,
            "total_input_tokens": self._total_input_tokens,
        }
        self.yaml_store.write_raw(
            f"{self._budget_base}/token-history.yaml", data
        )

    def _load_token_history(self) -> None:
        """R11: Load persisted token history on startup."""
        try:
            data = self.yaml_store.read_raw(
                f"{self._budget_base}/token-history.yaml"
            )
            for key, values in data.get("history", {}).items():
                self._token_history[key] = deque(values, maxlen=50)
            self._cache_hit_tokens = int(data.get("cache_hit_tokens", 0))
            self._total_input_tokens = int(data.get("total_input_tokens", 0))
            logger.info(
                f"Loaded token history: {len(self._token_history)} types, "
                f"{sum(len(v) for v in self._token_history.values())} samples"
            )
        except FileNotFoundError:
            pass  # First run — empty history is correct

    def _new_window(self) -> WindowBudget:
        return WindowBudget(
            window_start=datetime.now(timezone.utc),
            estimated_capacity=self._window_capacity,
        )

    def _new_weekly(self) -> WeeklyBudget:
        """Create a new weekly budget.

        FM-67: Aligns week_start to the most recent Monday 00:00 UTC.
        """
        now = datetime.now(timezone.utc)
        days_since_monday = now.weekday()
        monday = now.replace(hour=0, minute=0, second=0, microsecond=0)
        monday -= timedelta(days=days_since_monday)
        return WeeklyBudget(week_start=monday)

    def _persist_window(self, window: WindowBudget) -> None:
        self.yaml_store.write(f"{self._budget_base}/window.yaml", window)

    def _persist_weekly(self, weekly: WeeklyBudget) -> None:
        self.yaml_store.write(f"{self._budget_base}/weekly.yaml", weekly)
