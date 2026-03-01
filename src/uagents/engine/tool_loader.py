"""Dynamic tool loading engine.
Spec reference: Section 20.3 (Dynamic Tool Loading).

Loads tools based on task type and step goal. Uses JSPLIT-inspired
taxonomy for hierarchical organization. RAG-MCP semantic retrieval
via DiversityEngine TF-IDF functions. Targets 3-5 tools per step.

Key constraints:
- Ring 0-1 tools always loaded (core category)
- Max tools per step: 5 (configurable)
- Max concurrent MCP servers: 3
- MCP idle timeout: 10 minutes
- Token accounting per tool definition (~400-500 tokens)
- Tool token budget: 15% of context window

Literature basis:
- RAG-MCP (arXiv:2505.03275): 43.13% accuracy with semantic tool selection
- ITR (arXiv:2602.17046): 95% per-step context reduction
- JSPLIT (arXiv:2510.14537): Hierarchical tool taxonomy
- ScaleMCP: Dynamic MCP server lifecycle
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ..engine.diversity_engine import (
    compute_idf,
    cosine_distance,
    tf_idf_vector,
    tokenize,
)
from ..models.base import FrameworkModel
from ..models.protection import ProtectionRing
from ..models.tool import (
    McpServerRecord,
    McpServerState,
    ToolCategory,
    ToolDefinition,
    ToolLoadRequest,
    ToolLoadResult,
    ToolTaxonomy,
)
from ..state.yaml_store import YamlStore

if TYPE_CHECKING:
    from ..engine.budget_tracker import BudgetTracker

logger = logging.getLogger("uagents.tool_loader")


class ToolBudgetExceededError(RuntimeError):
    """Raised when tool definitions would exceed the token budget."""


class McpServerLimitError(RuntimeError):
    """Raised when starting a new MCP server would exceed the concurrency cap."""


class ToolLoader:
    """Dynamic tool loading with semantic retrieval and MCP lifecycle.

    IFM-N54: Phase 3.5 ToolLoader tracks MCP server INTENT -- actual
    server lifecycle is managed by Claude Code. ToolLoader records that a
    server SHOULD be running. Verification of actual server status is
    Phase 4+ scope.

    Design invariants:
    - Ring 0-1 tools always included in every load result
    - Semantic retrieval uses TF-IDF from DiversityEngine (no duplication)
    - Tool token cost tracked and enforced against budget
    - MCP servers lazy-loaded, idle-timed-out, concurrency-capped
    - Task type hints used as fallback when semantic retrieval insufficient
    - All tools stored in taxonomy loaded from YAML

    Usage:
        loader = ToolLoader(yaml_store, budget_tracker=tracker)
        result = loader.load_for_step(task_type="research", step_goal="find papers on X")
        # result.loaded_tools contains the tools to inject
        # result.total_token_cost is the token budget consumed
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        budget_tracker: BudgetTracker | None = None,  # SF-1
    ):
        self.yaml_store = yaml_store
        self._domain = domain
        self._budget_tracker = budget_tracker  # SF-1: token accounting

        # Load taxonomy (fail-loud if missing)
        config_raw = yaml_store.read_raw("core/tool-taxonomy.yaml")
        tt = config_raw.get("tool_taxonomy")
        if tt is None:
            raise ValueError(
                "core/tool-taxonomy.yaml missing 'tool_taxonomy' section"
            )

        # IFM-N96-FIX: Direct dict access — missing keys raise KeyError
        # immediately instead of silently using defaults that mask config errors.
        loading = tt["loading"]
        self._max_tools_per_step = int(loading["max_tools_per_step"])
        self._max_mcp_servers = int(loading["max_mcp_servers"])
        self._mcp_idle_timeout_min = int(loading["mcp_idle_timeout_minutes"])
        self._tool_token_budget_pct = float(loading["tool_token_budget_pct"])
        self._avg_tokens_per_tool = int(loading["avg_tokens_per_tool"])
        self._high_token_threshold = int(loading["high_token_threshold"])

        # Parse tool definitions from all categories
        self._all_tools: dict[str, ToolDefinition] = {}
        self._core_tools: list[str] = []  # Always-loaded tool names
        categories_raw = tt.get("categories", {})
        for cat_key, cat_data in categories_raw.items():
            if not isinstance(cat_data, dict):
                continue
            # IFM-N91-FIX: Helpful error on invalid category/ring values
            try:
                cat_enum = ToolCategory(cat_key)
            except ValueError:
                valid = [e.value for e in ToolCategory]
                raise ValueError(
                    f"Invalid tool category '{cat_key}' in tool-taxonomy.yaml. "
                    f"Valid categories: {valid}"
                )
            ring_val = int(cat_data.get("ring", 3))
            try:
                ring_enum = ProtectionRing(ring_val)
            except ValueError:
                valid = [e.value for e in ProtectionRing]
                raise ValueError(
                    f"Invalid ring value {ring_val} for category '{cat_key}' "
                    f"in tool-taxonomy.yaml. Valid rings: {valid}"
                )
            always_loaded = bool(cat_data.get("always_loaded", False))

            for tool_raw in cat_data.get("tools", []):
                # IFM-N62: Per-tool ring override (falls back to category ring)
                tool_ring_val = int(tool_raw.get("ring", ring_val))
                tool_ring_enum = ProtectionRing(tool_ring_val)

                tool = ToolDefinition(
                    name=tool_raw["name"],
                    description=tool_raw.get("description", ""),
                    instruction_fragment=tool_raw.get("instruction_fragment", ""),
                    category=cat_enum,
                    ring=tool_ring_enum,
                    token_cost=int(tool_raw.get("token_cost", self._avg_tokens_per_tool)),
                    mcp_server=tool_raw.get("mcp_server"),
                    tags=tool_raw.get("tags", []),
                )
                self._all_tools[tool.name] = tool
                if always_loaded:
                    self._core_tools.append(tool.name)

        # Task type hints
        self._task_type_hints: dict[str, list[str]] = {}
        for task_type, tools in tt.get("task_type_hints", {}).items():
            self._task_type_hints[task_type] = list(tools)

        # MCP server records
        self._mcp_servers: dict[str, McpServerRecord] = {}
        for srv_name, srv_data in tt.get("mcp_servers", {}).items():
            if not isinstance(srv_data, dict):
                continue
            ring_val = int(srv_data.get("ring", 3))
            self._mcp_servers[srv_name] = McpServerRecord(
                name=srv_name,
                ring=ProtectionRing(ring_val),
                state=(
                    McpServerState.RUNNING
                    if srv_data.get("auto_start", False)
                    else McpServerState.STOPPED
                ),
            )

        # State dir for persistence
        self._state_dir = f"instances/{domain}/state/tools"
        yaml_store.ensure_dir(self._state_dir)

    def load_for_step(
        self,
        task_type: str,
        step_goal: str,
        max_context_tokens: int = 200_000,
        exclude_tools: list[str] | None = None,
    ) -> ToolLoadResult:
        """Load tools for a specific agent step.

        Pipeline:
        1. Always include Ring 0-1 core tools
        2. Check task type hints for relevant tools
        3. Semantic retrieval: TF-IDF match step_goal against tool descriptions
        4. Merge results, deduplicate, cap at max_tools_per_step
        5. Check token budget
        6. Check MCP server requirements
        7. Return loaded tools with metadata

        Args:
            task_type: Task type from orchestrator classification.
            step_goal: Natural language description of current step goal.
            max_context_tokens: Total context window for budget calculation.
            exclude_tools: Tool names to exclude (already loaded or explicitly removed).

        Returns:
            ToolLoadResult with loaded tools and token cost.

        Raises:
            ToolBudgetExceededError: If core tools alone exceed budget.
        """
        if exclude_tools is None:
            exclude_tools = []

        token_budget = int(max_context_tokens * self._tool_token_budget_pct)
        loaded: list[ToolDefinition] = []
        rejected: list[str] = []
        rejection_reasons: dict[str, str] = {}
        total_cost = 0

        # Step 1: Always include Ring 0 tools (immutable, unconditional)
        # Ring 1 tools are high-priority candidates but subject to the
        # max_tools_per_step cap alongside other dynamic tools.
        ring_0_names: list[str] = []
        ring_1_names: list[str] = []
        for tool_name in self._core_tools:
            if tool_name in exclude_tools:
                continue
            tool = self._all_tools.get(tool_name)
            if tool is None:
                continue
            ring_val = tool.ring
            ring_int = ring_val if isinstance(ring_val, int) else int(ring_val)
            if ring_int <= ProtectionRing.RING_0_IMMUTABLE:
                ring_0_names.append(tool_name)
                loaded.append(tool)
                total_cost += tool.token_cost
            else:
                ring_1_names.append(tool_name)

        # Check if Ring 0 tools alone exceed budget
        if total_cost > token_budget:
            raise ToolBudgetExceededError(
                f"Core tools ({total_cost} tokens) exceed tool token budget "
                f"({token_budget} tokens = {self._tool_token_budget_pct:.0%} of "
                f"{max_context_tokens}). Cannot proceed."
            )

        loaded_names = {t.name for t in loaded}
        remaining_budget = token_budget - total_cost
        # max_tools_per_step is the TOTAL cap on tools returned (Ring 0 + dynamic).
        remaining_slots = self._max_tools_per_step - len(loaded)

        # Step 2: Build ordered candidate list.
        # Priority: task type hints > Ring 1 core tools > semantic matches.
        # Ring 1 tools are core (always-loaded category) and get priority
        # over semantic matches to ensure essential capabilities are present.
        candidate_names: list[str] = []

        # 2a: Task type hints (highest priority for dynamic loading)
        hint_tools = self._task_type_hints.get(task_type, [])
        for tool_name in hint_tools:
            if tool_name in loaded_names or tool_name in exclude_tools:
                continue
            candidate_names.append(tool_name)

        # 2b: Ring 1 core tools (always-loaded category, high priority)
        for tool_name in ring_1_names:
            if tool_name not in candidate_names:
                candidate_names.append(tool_name)

        # 2c: Semantic retrieval (fill remaining slots with relevant tools)
        semantic_matches = self._semantic_search(step_goal, limit=self._max_tools_per_step)
        for tool_name in semantic_matches:
            if tool_name in loaded_names or tool_name in exclude_tools:
                continue
            if tool_name not in candidate_names:
                candidate_names.append(tool_name)

        # Step 3: Merge, deduplicate, fill slots
        mcp_started: list[str] = []
        for tool_name in candidate_names:
            if remaining_slots <= 0:
                break

            tool = self._all_tools.get(tool_name)
            if tool is None:
                rejected.append(tool_name)
                rejection_reasons[tool_name] = "tool_not_found"
                continue

            # Check token budget
            if tool.token_cost > remaining_budget:
                rejected.append(tool_name)
                rejection_reasons[tool_name] = (
                    f"token_budget_exceeded: cost={tool.token_cost}, "
                    f"remaining={remaining_budget}"
                )
                continue

            # Check MCP server requirement
            if tool.mcp_server is not None:
                mcp_ok, mcp_reason = self._ensure_mcp_server(tool.mcp_server)
                if not mcp_ok:
                    rejected.append(tool_name)
                    rejection_reasons[tool_name] = f"mcp_server_unavailable: {mcp_reason}"
                    continue
                if tool.mcp_server not in mcp_started:
                    mcp_started.append(tool.mcp_server)

            loaded.append(tool)
            loaded_names.add(tool.name)
            total_cost += tool.token_cost
            remaining_budget -= tool.token_cost
            remaining_slots -= 1

        # SF-1: Record tool loading token consumption in BudgetTracker
        # IFM-N87-FIX: record_consumption(tokens: int, is_cached: bool)
        if self._budget_tracker is not None and total_cost > 0:
            self._budget_tracker.record_consumption(total_cost)

        return ToolLoadResult(
            loaded_tools=loaded,
            total_token_cost=total_cost,
            rejected_tools=rejected,
            rejection_reasons=rejection_reasons,
            mcp_servers_started=mcp_started,
        )

    def unload_tool(self, tool_name: str) -> bool:
        """Unload a tool after a step completes.

        Ring 0-1 tools cannot be unloaded. Returns True if unloaded.

        Args:
            tool_name: Name of tool to unload.

        Returns:
            True if tool was unloaded, False if protected or not found.
        """
        tool = self._all_tools.get(tool_name)
        if tool is None:
            logger.warning(f"Cannot unload unknown tool: {tool_name}")
            return False

        # Ring 0-1 tools cannot be unloaded
        ring_val = tool.ring
        if isinstance(ring_val, int):
            ring_int = ring_val
        else:
            ring_int = int(ring_val)
        if ring_int <= ProtectionRing.RING_1_PROTECTED:
            logger.warning(
                f"Cannot unload Ring {ring_int} tool '{tool_name}': protected"
            )
            return False

        logger.debug(f"Unloaded tool '{tool_name}'")
        return True

    def check_mcp_idle_timeouts(self) -> list[str]:
        """Check for MCP servers that have been idle too long.

        Returns list of server names that should be unloaded.
        Does NOT actually stop the servers — caller must handle that.
        """
        now = datetime.now(timezone.utc)
        idle_servers: list[str] = []

        for name, record in self._mcp_servers.items():
            if not record.is_active:
                continue
            # Ring 1 servers with idle_exempt are never suggested for unload
            ring_val = record.ring
            if isinstance(ring_val, int):
                ring_int = ring_val
            else:
                ring_int = int(ring_val)
            if ring_int <= ProtectionRing.RING_1_PROTECTED:
                continue
            if record.last_query_at is None:
                continue

            idle_minutes = (now - record.last_query_at).total_seconds() / 60.0
            if idle_minutes >= self._mcp_idle_timeout_min:
                idle_servers.append(name)
                logger.info(
                    f"MCP server '{name}' idle for {idle_minutes:.0f} minutes "
                    f"(threshold: {self._mcp_idle_timeout_min})"
                )

        return idle_servers

    def get_tool(self, name: str) -> ToolDefinition | None:
        """Get a tool definition by name."""
        return self._all_tools.get(name)

    def get_all_tool_names(self) -> list[str]:
        """Get all registered tool names."""
        return list(self._all_tools.keys())

    def get_core_tool_names(self) -> list[str]:
        """Get names of always-loaded core tools."""
        return list(self._core_tools)

    def get_tool_token_cost(self, tool_names: list[str]) -> int:
        """Calculate total token cost for a set of tools."""
        total = 0
        for name in tool_names:
            tool = self._all_tools.get(name)
            if tool is not None:
                total += tool.token_cost
        return total

    def record_mcp_query(self, server_name: str, tokens_used: int) -> None:
        """Record an MCP server query for utilization tracking.

        Args:
            server_name: Name of the MCP server queried.
            tokens_used: Tokens consumed by the query.
        """
        record = self._mcp_servers.get(server_name)
        if record is None:
            logger.warning(f"Unknown MCP server: {server_name}")
            return
        record.last_query_at = datetime.now(timezone.utc)
        record.total_queries += 1
        record.total_tokens_consumed += tokens_used

        # Flag high-consumption servers
        if (
            record.total_tokens_consumed > self._high_token_threshold
            and record.utilization < 0.1
        ):
            logger.warning(
                f"MCP server '{server_name}' consuming "
                f"{record.total_tokens_consumed} tokens with only "
                f"{record.total_queries} queries "
                f"(utilization: {record.utilization:.2f})"
            )

    def get_mcp_status(self) -> dict[str, McpServerRecord]:
        """Get status of all MCP servers."""
        return dict(self._mcp_servers)

    def get_active_mcp_count(self) -> int:
        """Count currently active MCP servers."""
        return sum(1 for r in self._mcp_servers.values() if r.is_active)

    # -- Internal Methods --

    def _semantic_search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[str]:
        """Search tools by semantic similarity to query using TF-IDF.

        Uses DiversityEngine's TF-IDF functions for text similarity.
        Searches against tool name + description + tags.

        Args:
            query: Search query (step goal or task description).
            limit: Maximum results to return.

        Returns:
            List of tool names sorted by relevance (most relevant first).
        """
        # Exclude core tools from search (they are always loaded)
        searchable = [
            t for t in self._all_tools.values()
            if t.name not in self._core_tools
        ]
        if not searchable:
            return []

        # Build document corpus
        documents: list[list[str]] = []
        for tool in searchable:
            doc_text = f"{tool.name} {tool.description} {' '.join(tool.tags)}"
            documents.append(tokenize(doc_text))

        # IFM-N89-FIX: Return empty on empty query tokens
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Add query as document for IDF computation
        all_docs = documents + [query_tokens]

        # Compute IDF
        idf = compute_idf(all_docs)

        # Compute query vector
        query_vector = tf_idf_vector(query_tokens, idf)

        # Score each tool
        scored: list[tuple[float, str]] = []
        for i, tool in enumerate(searchable):
            tool_vector = tf_idf_vector(documents[i], idf)
            distance = cosine_distance(query_vector, tool_vector)
            similarity = 1.0 - distance
            scored.append((similarity, tool.name))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[0], reverse=True)

        return [name for _, name in scored[:limit]]

    def _ensure_mcp_server(self, server_name: str) -> tuple[bool, str]:
        """Ensure an MCP server is available, starting if needed.

        IFM-N54: Phase 3.5 ToolLoader tracks MCP server INTENT — actual
        server lifecycle is managed by Claude Code. ToolLoader records that a
        server SHOULD be running. Verification of actual server status is
        Phase 4+ scope.

        Args:
            server_name: MCP server to ensure is running.

        Returns:
            (success, reason) tuple.
        """
        record = self._mcp_servers.get(server_name)
        if record is None:
            return False, f"unknown_server: {server_name}"

        if record.is_active:
            return True, "already_running"

        # Check concurrency cap
        active_count = self.get_active_mcp_count()
        if active_count >= self._max_mcp_servers:
            return False, (
                f"concurrency_cap: {active_count}/{self._max_mcp_servers} "
                f"MCP servers already active"
            )

        # IFM-N54: Phase 3.5 ToolLoader tracks MCP server INTENT — actual
        # server lifecycle is managed by Claude Code. ToolLoader records that a
        # server SHOULD be running. Verification of actual server status is
        # Phase 4+ scope.
        record.state = McpServerState.RUNNING
        record.started_at = datetime.now(timezone.utc)
        logger.info(f"MCP server '{server_name}' marked as RUNNING (intent only)")
        return True, "started"
