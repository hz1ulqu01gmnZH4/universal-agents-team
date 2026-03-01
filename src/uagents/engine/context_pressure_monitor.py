"""Context pressure monitoring and compression cascade.
Spec reference: Section 20.5 (Context Pressure Management),
Section 21.2 (Context Budget Allocation).

Tracks context window utilization per agent step. Determines
ContextPressureLevel and CompressionStage. Monitors Ring 0
reservation. Triggers HARD_FAIL when insufficient context for Ring 0.

Key constraints:
- Ring 0 content (first ring_0_reserved_tokens) is NEVER compressed
- Compression cascade is progressive (5 stages)
- HARD_FAIL if remaining context < min_productive_tokens after Ring 0
- Information placement: critical info at edges (lost-in-the-middle mitigation)
- All thresholds configurable via core/context-pressure.yaml

Literature basis:
- Liu 2023: >30% accuracy drop for middle-positioned information
- IFScale: 68% compliance at 500 instructions
- SWE-Pruner: 23-54% task-aware context pruning
"""
from __future__ import annotations

import logging

from ..models.context import (
    CompressionStage,
    ContextBudgetAllocation,
    ContextSnapshot,
)
from ..models.protection import ContextPressureLevel
from ..models.reconfiguration import ContextPressureConfig
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.context_pressure_monitor")


class ContextHardFailError(RuntimeError):
    """Raised when context is insufficient for Ring 0 + minimal productive work.

    This is a non-recoverable error that requires human intervention.
    The framework must HALT immediately — no silent fallback.
    """


class ContextPressureMonitor:
    """Tracks context window utilization and enforces compression cascade.

    Design invariants:
    - Ring 0 reservation is enforced on every snapshot
    - Compression stage is determined from utilization fraction
    - HARD_FAIL if available context < min_productive_tokens after Ring 0
    - All thresholds loaded from YAML config (no hardcoded defaults)
    - Snapshots are point-in-time: computed after each prompt composition
    - Edge placement rules applied by PromptComposer (this class provides data)

    Usage:
        monitor = ContextPressureMonitor(yaml_store)
        snapshot = monitor.compute_snapshot(composed_prompt, max_tokens)
        if snapshot.pressure_level == ContextPressureLevel.OVERFLOW:
            # Handle emergency compression
        stage = monitor.get_compression_stage(snapshot)
    """

    def __init__(self, yaml_store: YamlStore):
        self.yaml_store = yaml_store

        # Load config (fail-loud if missing)
        config_raw = yaml_store.read_raw("core/context-pressure.yaml")
        cp = config_raw.get("context_pressure")
        if cp is None:
            raise ValueError(
                "core/context-pressure.yaml missing 'context_pressure' section"
            )

        # IFM-N53: Direct dict access — missing YAML keys raise KeyError
        # immediately instead of silently using defaults that mask config errors.
        thresholds = cp["thresholds"]
        ring_0 = cp["ring_0"]
        cascade = cp["compression_cascade"]

        self._config = ContextPressureConfig(
            pressure_threshold=float(thresholds["pressure"]),
            critical_threshold=float(thresholds["critical"]),
            overflow_threshold=float(thresholds["overflow"]),
            history_compression_trigger=float(
                cascade["stage_1_history"]["trigger"]
            ),
            tool_reduction_trigger=float(
                cascade["stage_2_tool_reduction"]["trigger"]
            ),
            task_pruning_trigger=float(
                cascade["stage_3_task_pruning"]["trigger"]
            ),
            system_compress_trigger=float(
                cascade["stage_4_system_compress"]["trigger"]
            ),
            emergency_trigger=float(
                cascade["stage_5_emergency"]["trigger"]
            ),
            ring_0_reserved_tokens=int(ring_0["reserved_tokens"]),
            min_productive_tokens=int(ring_0["min_productive_tokens"]),
            history_keep_recent=int(
                cascade["stage_1_history"]["history_keep_recent"]
            ),
            tool_reduction_target=int(
                cascade["stage_2_tool_reduction"]["tool_reduction_target"]
            ),
            edge_placement_enabled=bool(
                cp["placement"]["enabled"]
            ),
        )

        # History of snapshots for trend analysis
        self._snapshot_history: list[ContextSnapshot] = []
        self._max_history = 50

    @property
    def config(self) -> ContextPressureConfig:
        """Expose config for PromptComposer integration."""
        return self._config

    def compute_snapshot(
        self,
        system_tokens: int,
        tool_tokens: int,
        task_tokens: int,
        history_tokens: int,
        reserve_tokens: int,
        ring_0_tokens: int,
        max_context_tokens: int,
    ) -> ContextSnapshot:
        """Compute a point-in-time context utilization snapshot.

        Called after every prompt composition to track utilization.
        Ring 0 tokens are tracked separately and NEVER compressed.

        Args:
            system_tokens: Tokens used by system instructions (Ring 0-1).
            tool_tokens: Tokens used by tool definitions.
            task_tokens: Tokens used by current task context.
            history_tokens: Tokens used by conversation history.
            reserve_tokens: Tokens reserved for unexpected needs.
            ring_0_tokens: Tokens used by Ring 0 content (subset of system_tokens).
            max_context_tokens: Total context window capacity.

        Returns:
            ContextSnapshot with pressure level and compression stage.

        Raises:
            ContextHardFailError: If context insufficient for Ring 0 +
                min_productive_tokens.
        """
        total = system_tokens + tool_tokens + task_tokens + history_tokens + reserve_tokens

        # Determine pressure level
        utilization = total / max_context_tokens if max_context_tokens > 0 else 1.0
        pressure_level = self._determine_pressure_level(utilization)

        # Determine compression stage
        compression_stage = self._determine_compression_stage(utilization)

        # Check Ring 0 reservation
        remaining_after_ring_0 = max_context_tokens - ring_0_tokens
        if remaining_after_ring_0 < self._config.min_productive_tokens:
            logger.critical(
                f"HARD_FAIL: Context insufficient for Ring 0 + productive work. "
                f"Ring 0 uses {ring_0_tokens} tokens, "
                f"remaining {remaining_after_ring_0} < "
                f"min_productive {self._config.min_productive_tokens}. "
                f"Context window: {max_context_tokens} tokens."
            )
            raise ContextHardFailError(
                f"Context insufficient: Ring 0 requires {ring_0_tokens} tokens, "
                f"only {remaining_after_ring_0} remaining for productive work "
                f"(minimum: {self._config.min_productive_tokens}). "
                f"Context window: {max_context_tokens} tokens. "
                f"HALT: Human intervention required."
            )

        snapshot = ContextSnapshot(
            total_tokens=total,
            system_tokens=system_tokens,
            tool_tokens=tool_tokens,
            task_tokens=task_tokens,
            history_tokens=history_tokens,
            reserve_tokens=reserve_tokens,
            pressure_level=pressure_level,
            compression_stage=compression_stage,
            ring_0_tokens=ring_0_tokens,
        )

        # Track history
        self._snapshot_history.append(snapshot)
        if len(self._snapshot_history) > self._max_history:
            self._snapshot_history = self._snapshot_history[-self._max_history:]

        return snapshot

    def check_budget_allocation(
        self,
        snapshot: ContextSnapshot,
        max_context_tokens: int,
        allocation: ContextBudgetAllocation | None = None,
    ) -> dict[str, bool]:
        """Check if context usage stays within budget allocation.

        Returns a dict mapping category names to whether they are
        within their allocated budget. Categories over budget need
        compression.

        Args:
            snapshot: Current context snapshot.
            max_context_tokens: Total context window capacity.
            allocation: Budget allocation (defaults to standard 10/15/40/25/10%).

        Returns:
            Dict of category -> within_budget (True = OK, False = over budget).
        """
        if allocation is None:
            allocation = ContextBudgetAllocation()

        system_budget = int(max_context_tokens * allocation.system_instructions_pct)
        tool_budget = int(max_context_tokens * allocation.active_tools_pct)
        task_budget = int(max_context_tokens * allocation.current_task_pct)
        history_budget = int(max_context_tokens * allocation.working_memory_pct)
        reserve_budget = int(max_context_tokens * allocation.reserve_pct)

        return {
            "system_instructions": snapshot.system_tokens <= system_budget,
            "active_tools": snapshot.tool_tokens <= tool_budget,
            "current_task": snapshot.task_tokens <= task_budget,
            "working_memory": snapshot.history_tokens <= history_budget,
            "reserve": snapshot.reserve_tokens <= reserve_budget,
        }

    def get_compression_actions(
        self,
        snapshot: ContextSnapshot,
    ) -> list[str]:
        """Get the list of compression actions needed for the current stage.

        Returns ordered list of actions from Stage 1 through the current
        compression stage. Earlier stages are prerequisite for later ones.

        Args:
            snapshot: Current context snapshot.

        Returns:
            List of action descriptions for the current compression stage.
        """
        actions: list[str] = []
        # CompressionStage is an IntEnum stored as int via use_enum_values
        stage_val = snapshot.compression_stage
        if isinstance(stage_val, int):
            stage_int = stage_val
        else:
            stage_int = int(stage_val)

        if stage_int >= CompressionStage.HISTORY:
            actions.append(
                f"Stage 1: Summarize oldest turns, keep last "
                f"{self._config.history_keep_recent} detailed"
            )
        if stage_int >= CompressionStage.TOOL_REDUCTION:
            actions.append(
                f"Stage 2: Reduce tools to top-{self._config.tool_reduction_target} "
                f"most relevant (Ring 0-1 exempt)"
            )
        if stage_int >= CompressionStage.TASK_PRUNING:
            actions.append(
                "Stage 3: Apply task-aware context pruning (23-54% reduction)"
            )
        if stage_int >= CompressionStage.SYSTEM_COMPRESS:
            actions.append(
                "Stage 4: Reduce system prompt to Ring 0 instructions only"
            )
        if stage_int >= CompressionStage.EMERGENCY:
            actions.append(
                "Stage 5: EMERGENCY — summarize all non-Ring-0 context"
            )

        return actions

    def get_pressure_trend(self) -> str:
        """Analyze pressure trend from snapshot history.

        Returns:
            "stable", "increasing", or "decreasing" based on recent snapshots.
        """
        if len(self._snapshot_history) < 3:
            return "stable"

        recent = self._snapshot_history[-5:]
        totals = [s.total_tokens for s in recent]

        # Simple linear trend
        diffs = [totals[i + 1] - totals[i] for i in range(len(totals) - 1)]
        avg_diff = sum(diffs) / len(diffs)

        if avg_diff > 500:
            return "increasing"
        elif avg_diff < -500:
            return "decreasing"
        return "stable"

    def _determine_pressure_level(self, utilization: float) -> ContextPressureLevel:
        """Map context utilization to pressure level."""
        if utilization >= self._config.overflow_threshold:
            return ContextPressureLevel.OVERFLOW
        elif utilization >= self._config.critical_threshold:
            return ContextPressureLevel.CRITICAL
        elif utilization >= self._config.pressure_threshold:
            return ContextPressureLevel.PRESSURE
        return ContextPressureLevel.HEALTHY

    def _determine_compression_stage(self, utilization: float) -> CompressionStage:
        """Map context utilization to compression stage."""
        if utilization >= self._config.emergency_trigger:
            return CompressionStage.EMERGENCY
        elif utilization >= self._config.system_compress_trigger:
            return CompressionStage.SYSTEM_COMPRESS
        elif utilization >= self._config.task_pruning_trigger:
            return CompressionStage.TASK_PRUNING
        elif utilization >= self._config.tool_reduction_trigger:
            return CompressionStage.TOOL_REDUCTION
        elif utilization >= self._config.history_compression_trigger:
            return CompressionStage.HISTORY
        return CompressionStage.NONE
