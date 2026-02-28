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
