"""Tool loading and taxonomy models.
Spec reference: Section 20.3 (Dynamic Tool Loading).

Phase 3.5: ToolDefinition, ToolCategory, ToolTaxonomy, ToolLoadRequest,
           ToolLoadResult, McpServerState, McpServerRecord.

Literature basis:
- RAG-MCP (arXiv:2505.03275): RAG-based tool selection 43.13% vs. naive 13.62%
- JSPLIT (arXiv:2510.14537): Hierarchical tool taxonomy
- ITR (arXiv:2602.17046): 95% per-step context reduction
- ScaleMCP: Dynamic MCP server lifecycle management
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from .base import FrameworkModel
from .protection import ProtectionRing


class ToolCategory(StrEnum):
    """JSPLIT-inspired tool categories (Section 20.3)."""

    CORE = "core"              # Always loaded — file ops, git, messaging (Ring 0-1)
    DOMAIN = "domain"          # Loaded when domain is active (Ring 2)
    TASK = "task"              # Loaded per-task based on task type (Ring 2-3)
    SPECIALIST = "specialist"  # Loaded per-step via semantic retrieval (Ring 3)


class ToolDefinition(FrameworkModel):
    """A single tool available for agent use.

    Represents a tool's metadata and injection text. The instruction_fragment
    is what gets injected into the agent prompt when the tool is loaded.
    Token cost is estimated at creation time and tracked for budget accounting.
    """

    name: str
    description: str
    instruction_fragment: str
    category: ToolCategory
    ring: ProtectionRing
    token_cost: int = Field(ge=0)  # Estimated tokens for this tool definition
    mcp_server: str | None = None  # MCP server name if tool requires one
    tags: list[str] = Field(default_factory=list)  # Semantic tags for retrieval


class McpServerState(StrEnum):
    """MCP server lifecycle states."""

    STOPPED = "stopped"    # Not running
    STARTING = "starting"  # In process of starting
    RUNNING = "running"    # Active and available
    IDLE = "idle"          # Running but no recent queries
    ERROR = "error"        # Failed to start or crashed


class McpServerRecord(FrameworkModel):
    """Tracks an MCP server's lifecycle and resource consumption.

    Used by ToolLoader to manage lazy loading, idle timeout, and
    token accounting per MCP server.
    """

    name: str
    state: McpServerState = McpServerState.STOPPED
    tools_provided: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    last_query_at: datetime | None = None
    total_tokens_consumed: int = 0
    total_queries: int = 0
    ring: ProtectionRing = ProtectionRing.RING_3_EXPENDABLE

    @property
    def is_active(self) -> bool:
        """True if server is running or idle (can serve queries)."""
        return self.state in (McpServerState.RUNNING.value, McpServerState.IDLE.value)

    @property
    def utilization(self) -> float:
        """Query-to-token ratio. Low utilization = candidate for unload."""
        if self.total_tokens_consumed == 0:
            return 0.0
        return self.total_queries / (self.total_tokens_consumed / 1000.0)


class ToolLoadRequest(FrameworkModel):
    """Request to load tools for a specific agent step.

    Created by ToolLoader based on task type and step goal.
    Contains both the tools to load and the rationale for selection.
    """

    task_type: str
    step_goal: str
    requested_tools: list[str]  # Tool names to load
    always_loaded: list[str] = Field(default_factory=list)  # Ring 0-1 tools
    rationale: str = ""


class ToolLoadResult(FrameworkModel):
    """Result of a tool loading operation.

    Contains the actual tools loaded, total token cost,
    and any tools that were requested but not loaded (with reasons).
    """

    loaded_tools: list[ToolDefinition]
    total_token_cost: int = Field(ge=0)
    rejected_tools: list[str] = Field(default_factory=list)  # Names of tools not loaded
    rejection_reasons: dict[str, str] = Field(default_factory=dict)
    mcp_servers_started: list[str] = Field(default_factory=list)


class ToolTaxonomy(FrameworkModel):
    """Complete tool taxonomy loaded from YAML.

    Hierarchical organization of all available tools.
    Used by ToolLoader for category-based and semantic retrieval.
    """

    tools: list[ToolDefinition] = Field(default_factory=list)
    max_tools_per_step: int = 5
    max_mcp_servers: int = 3
    mcp_idle_timeout_minutes: int = 10
    tool_token_budget_pct: float = 0.15  # From ContextBudgetAllocation
