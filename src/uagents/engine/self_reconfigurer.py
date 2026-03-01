"""Agent self-reconfiguration engine.
Spec reference: Section 20.6 (Self-Reconfiguration as First-Class Action).

Implements the ToolSelf pattern: agents can modify their own
configuration as a first-class action. All reconfigurations are
logged, constrained, and auditable.

Key constraints:
- Cannot reconfigure Ring 0-1 capabilities
- Cannot increase own authority_level
- Budget changes capped at +/-30% from original allocation
- Must provide rationale for every reconfiguration
- All reconfigurations logged in audit trail

Literature basis:
- ToolSelf (arXiv:2602.07883): 24.1% average performance gain
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ..models.audit import DecisionLogEntry
from ..models.base import generate_id
from ..models.protection import ProtectionRing
from ..models.reconfiguration import (
    ReconfigurationAction,
    ReconfigurationRequest,
    ReconfigurationResult,
)
from ..state.yaml_store import YamlStore

if TYPE_CHECKING:
    from ..engine.tool_loader import ToolLoader

logger = logging.getLogger("uagents.self_reconfigurer")

# Maximum budget change percentage
MAX_BUDGET_DELTA_PCT = 30.0


class ReconfigurationDeniedError(RuntimeError):
    """Raised when a reconfiguration request violates constraints."""


class SelfReconfigurer:
    """Validates and executes agent self-reconfiguration requests.

    Design invariants:
    - Ring 0-1 capabilities are NEVER reconfigurable
    - Authority level cannot be increased via reconfiguration
    - Budget changes capped at +/-30%
    - Every reconfiguration requires a non-empty rationale
    - All reconfigurations logged as DECISIONS audit entries
    - Request IDs are unique and trackable
    - Rejected reconfigurations are logged with constraint violation details
    - Reconfiguration does NOT execute the change — it validates and records.
      The caller (orchestrator/agent) executes after approval.

    Usage:
        reconfigurer = SelfReconfigurer(yaml_store, tool_loader, audit_logger)
        result = reconfigurer.process_request(request)
        if result.approved:
            # Execute the reconfiguration
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        audit_logger: object | None = None,
        tool_loader: ToolLoader | None = None,  # MF-1/IFM-N56: FM-SR03-FIX wiring
    ):
        self.yaml_store = yaml_store
        self._domain = domain
        self._audit_logger = audit_logger
        self._tool_loader = tool_loader  # MF-1: for authoritative ring lookup

        # State dir for reconfiguration history
        self._state_dir = f"instances/{domain}/state/reconfigurations"
        yaml_store.ensure_dir(self._state_dir)

        # SF-6: History trimming
        self._max_reconfiguration_history = 100
        # IFM-N90-FIX: Trim every N logs, not on every log
        self._log_count_since_trim = 0
        self._TRIM_INTERVAL = 10

        # Track cumulative budget changes per agent (reset per session)
        self._cumulative_budget_deltas: dict[str, float] = {}

    def process_request(
        self,
        request: ReconfigurationRequest,
    ) -> ReconfigurationResult:
        """Validate and process a reconfiguration request.

        Checks all constraints before approving. Logs the request
        and result to audit trail regardless of outcome.

        Args:
            request: The reconfiguration request from an agent.

        Returns:
            ReconfigurationResult with approval status and details.
        """
        # Validate rationale is provided
        if not request.rationale.strip():
            result = ReconfigurationResult(
                request_id=request.id,
                approved=False,
                constraint_violated="rationale_required: empty rationale",
            )
            self._log_reconfiguration(request, result)
            return result

        # Route to action-specific validation
        action_val = request.action
        if isinstance(action_val, str):
            action_str = action_val
        else:
            action_str = str(action_val)

        if action_str == ReconfigurationAction.TOOL_LOAD.value:
            return self._validate_tool_load(request)
        elif action_str == ReconfigurationAction.TOOL_UNLOAD.value:
            return self._validate_tool_unload(request, tool_loader=self._tool_loader)  # MF-1
        elif action_str == ReconfigurationAction.CONTEXT_COMPRESS.value:
            return self._validate_context_compress(request)
        elif action_str == ReconfigurationAction.CONTEXT_EXPAND.value:
            return self._validate_context_expand(request)
        elif action_str == ReconfigurationAction.STRATEGY_SWITCH.value:
            return self._validate_strategy_switch(request)
        elif action_str == ReconfigurationAction.BUDGET_REALLOCATE.value:
            return self._validate_budget_reallocate(request)
        else:
            result = ReconfigurationResult(
                request_id=request.id,
                approved=False,
                constraint_violated=f"unknown_action: {action_str}",
            )
            self._log_reconfiguration(request, result)
            return result

    def get_cumulative_budget_delta(self, agent_id: str) -> float:
        """Get cumulative budget change for an agent in this session."""
        return self._cumulative_budget_deltas.get(agent_id, 0.0)

    def reset_session(self) -> None:
        """Reset session-scoped state (cumulative budget deltas)."""
        self._cumulative_budget_deltas.clear()

    # -- Action-Specific Validation --

    def _validate_tool_load(
        self,
        request: ReconfigurationRequest,
    ) -> ReconfigurationResult:
        """Validate a tool load request.

        IFM-N57: Validates against ToolLoader registry instead of
        unconditionally approving. Checks:
        1. Tool exists in registry
        2. Not Ring 0-1 (already loaded)
        3. Does not exceed max_tools_per_step
        """
        if self._tool_loader is not None:
            tool = self._tool_loader.get_tool(request.target)
            if tool is None:
                result = ReconfigurationResult(
                    request_id=request.id,
                    approved=False,
                    constraint_violated=(
                        f"tool_not_found: '{request.target}' not in ToolLoader registry"
                    ),
                )
                self._log_reconfiguration(request, result)
                return result

            ring_val = tool.ring
            ring_int = ring_val if isinstance(ring_val, int) else int(ring_val)
            if ring_int <= ProtectionRing.RING_1_PROTECTED:
                result = ReconfigurationResult(
                    request_id=request.id,
                    approved=False,
                    constraint_violated=(
                        f"already_loaded: Ring {ring_int} tool '{request.target}' "
                        f"is always loaded (core tool)"
                    ),
                )
                self._log_reconfiguration(request, result)
                return result

            # Check against max_tools_per_step if provided in parameters
            max_tools = request.parameters.get("max_tools_per_step")
            current_loaded = request.parameters.get("current_loaded_count")
            if max_tools is not None and current_loaded is not None:
                try:
                    if int(current_loaded) >= int(max_tools):
                        result = ReconfigurationResult(
                            request_id=request.id,
                            approved=False,
                            constraint_violated=(
                                f"max_tools_exceeded: {current_loaded}/{max_tools} "
                                f"tools already loaded"
                            ),
                        )
                        self._log_reconfiguration(request, result)
                        return result
                except (ValueError, TypeError):
                    pass  # Non-numeric values — skip check
        else:
            # SF-5-FIX: Log warning when no ToolLoader for validation
            logger.warning(
                f"No ToolLoader available for tool_load validation of "
                f"'{request.target}'. Approving without registry check."
            )

        result = ReconfigurationResult(
            request_id=request.id,
            approved=True,
            action_taken=f"tool_load approved: {request.target}",
        )
        self._log_reconfiguration(request, result)
        return result

    def _validate_tool_unload(
        self,
        request: ReconfigurationRequest,
        tool_loader: ToolLoader | None = None,
    ) -> ReconfigurationResult:
        """Validate a tool unload request.

        Constraint: Cannot unload Ring 0-1 tools.
        MF-1/FM-SR03-FIX: Validates against ToolLoader registry (authoritative),
        not request parameters (untrusted).
        """
        ring_int = 3  # Default if no ToolLoader available
        if tool_loader is not None:
            tool = tool_loader.get_tool(request.target)
            if tool is not None:
                ring_val = tool.ring
                ring_int = ring_val if isinstance(ring_val, int) else int(ring_val)
            else:
                # Tool not in registry — reject (unknown tool)
                result = ReconfigurationResult(
                    request_id=request.id,
                    approved=False,
                    constraint_violated=(
                        f"tool_not_found: '{request.target}' not in ToolLoader registry"
                    ),
                )
                self._log_reconfiguration(request, result)
                return result
        else:
            # Fallback to request parameters (less trusted) — log warning
            logger.warning(
                f"No ToolLoader available for ring validation of '{request.target}'. "
                f"Falling back to request parameters (untrusted)."
            )
            ring_str = request.parameters.get("ring", "3")
            try:
                ring_int = int(ring_str)
            except (ValueError, TypeError):
                ring_int = 3

        if ring_int <= ProtectionRing.RING_1_PROTECTED:
            result = ReconfigurationResult(
                request_id=request.id,
                approved=False,
                constraint_violated=(
                    f"ring_protected: cannot unload Ring {ring_int} tool "
                    f"'{request.target}'"
                ),
            )
            self._log_reconfiguration(request, result)
            return result

        result = ReconfigurationResult(
            request_id=request.id,
            approved=True,
            action_taken=f"tool_unload approved: {request.target}",
        )
        self._log_reconfiguration(request, result)
        return result

    def _validate_context_compress(
        self,
        request: ReconfigurationRequest,
    ) -> ReconfigurationResult:
        """Validate a context compression request.

        Constraints:
        - Cannot compress Ring 0 content at all
        - IFM-N66: Ring 1 content allows parameter compression only (not full removal)
        """
        target_ring_str = request.parameters.get("target_ring", "3")
        try:
            target_ring_int = int(target_ring_str)
        except (ValueError, TypeError):
            target_ring_int = 3

        if target_ring_int == ProtectionRing.RING_0_IMMUTABLE:
            result = ReconfigurationResult(
                request_id=request.id,
                approved=False,
                constraint_violated="ring_0_immutable: Ring 0 content cannot be compressed",
            )
            self._log_reconfiguration(request, result)
            return result

        # IFM-N66: Ring 1 allows parameter compression only, not full removal
        if target_ring_int == ProtectionRing.RING_1_PROTECTED:
            compression_type = request.parameters.get("compression_type", "full")
            if compression_type != "parameter":
                result = ReconfigurationResult(
                    request_id=request.id,
                    approved=False,
                    constraint_violated=(
                        "ring_1_protected: Ring 1 content allows parameter "
                        "compression only, not full removal. Set "
                        "compression_type='parameter' in request parameters."
                    ),
                )
                self._log_reconfiguration(request, result)
                return result

        result = ReconfigurationResult(
            request_id=request.id,
            approved=True,
            action_taken=f"context_compress approved: {request.target}",
        )
        self._log_reconfiguration(request, result)
        return result

    def _validate_context_expand(
        self,
        request: ReconfigurationRequest,
    ) -> ReconfigurationResult:
        """Validate a context expansion request.

        Always approved — expansion does not violate any constraints.
        The ContextPressureMonitor will determine if expansion is feasible.
        """
        result = ReconfigurationResult(
            request_id=request.id,
            approved=True,
            action_taken=f"context_expand approved: {request.target}",
        )
        self._log_reconfiguration(request, result)
        return result

    def _validate_strategy_switch(
        self,
        request: ReconfigurationRequest,
    ) -> ReconfigurationResult:
        """Validate a reasoning strategy switch.

        Always approved — strategy changes don't affect ring integrity.
        """
        result = ReconfigurationResult(
            request_id=request.id,
            approved=True,
            action_taken=(
                f"strategy_switch approved: {request.target} -> "
                f"{request.parameters.get('new_strategy', 'unknown')}"
            ),
        )
        self._log_reconfiguration(request, result)
        return result

    def _validate_budget_reallocate(
        self,
        request: ReconfigurationRequest,
    ) -> ReconfigurationResult:
        """Validate a budget reallocation request.

        Constraints:
        - Change capped at +/-30% from original allocation
        - Cumulative changes across session tracked per agent
        """
        delta_pct = request.budget_delta_pct

        # Check single-request cap
        if abs(delta_pct) > MAX_BUDGET_DELTA_PCT:
            result = ReconfigurationResult(
                request_id=request.id,
                approved=False,
                constraint_violated=(
                    f"budget_cap_exceeded: requested {delta_pct:+.1f}%, "
                    f"max is +/-{MAX_BUDGET_DELTA_PCT:.0f}%"
                ),
            )
            self._log_reconfiguration(request, result)
            return result

        # Check cumulative cap
        current_cumulative = self._cumulative_budget_deltas.get(
            request.agent_id, 0.0
        )
        new_cumulative = current_cumulative + delta_pct
        if abs(new_cumulative) > MAX_BUDGET_DELTA_PCT:
            result = ReconfigurationResult(
                request_id=request.id,
                approved=False,
                constraint_violated=(
                    f"cumulative_budget_cap: current cumulative "
                    f"{current_cumulative:+.1f}% + requested "
                    f"{delta_pct:+.1f}% = {new_cumulative:+.1f}% "
                    f"exceeds +/-{MAX_BUDGET_DELTA_PCT:.0f}% cap"
                ),
            )
            self._log_reconfiguration(request, result)
            return result

        # Approved — update cumulative tracker
        self._cumulative_budget_deltas[request.agent_id] = new_cumulative

        result = ReconfigurationResult(
            request_id=request.id,
            approved=True,
            action_taken=(
                f"budget_reallocate approved: {request.target} "
                f"{delta_pct:+.1f}% (cumulative: {new_cumulative:+.1f}%)"
            ),
        )
        self._log_reconfiguration(request, result)
        return result

    # -- Internal Methods --

    def _log_reconfiguration(
        self,
        request: ReconfigurationRequest,
        result: ReconfigurationResult,
    ) -> None:
        """Log a reconfiguration request and result.

        Persists to state and logs to DECISIONS audit stream.
        """
        now = datetime.now(timezone.utc)

        # Persist to state
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        unique_suffix = request.id.split("-")[-1]
        state_data = {
            "request_id": request.id,
            "agent_id": request.agent_id,
            "action": request.action if isinstance(request.action, str) else request.action.value,
            "target": request.target,
            "rationale": request.rationale,
            "approved": result.approved,
            "action_taken": result.action_taken,
            "constraint_violated": result.constraint_violated,
            "timestamp": now.isoformat(),
        }
        self.yaml_store.write_raw(
            f"{self._state_dir}/{timestamp_str}_{unique_suffix}.yaml",
            state_data,
        )

        # Log to DECISIONS audit stream
        if self._audit_logger is not None:
            try:
                entry = DecisionLogEntry(
                    id=generate_id("dec"),
                    timestamp=now,
                    decision_type=f"reconfiguration_{request.action}",
                    actor=request.agent_id,
                    options_considered=[
                        {
                            "action": request.action if isinstance(request.action, str) else request.action.value,
                            "target": request.target,
                            "rationale": request.rationale,
                        }
                    ],
                    selected="approved" if result.approved else "denied",
                    rationale=(
                        result.action_taken
                        if result.approved
                        else result.constraint_violated
                    ),
                )
                self._audit_logger.log_decision(entry)
            except Exception as e:
                # IFM-N98-FIX: Escalate for denied reconfigurations (security-relevant)
                if not result.approved:
                    logger.error(
                        f"Failed to log DENIED reconfiguration to audit: {e}"
                    )
                else:
                    logger.warning(
                        f"Failed to log reconfiguration to audit: {e}"
                    )

        if result.approved:
            logger.info(
                f"Reconfiguration approved: agent={request.agent_id} "
                f"action={request.action} target={request.target}"
            )
        else:
            logger.warning(
                f"Reconfiguration denied: agent={request.agent_id} "
                f"action={request.action} target={request.target} "
                f"violation={result.constraint_violated}"
            )

        # SF-6/IFM-N90-FIX: Trim periodically, not on every log
        self._log_count_since_trim += 1
        if self._log_count_since_trim >= self._TRIM_INTERVAL:
            self._trim_reconfiguration_history()
            self._log_count_since_trim = 0

    def _trim_reconfiguration_history(self) -> None:
        """Trim reconfiguration history to max entries.

        SF-6: Prevents unbounded growth of reconfiguration records.
        Matches pattern from SkillLibrary._trim_maintenance_history().
        """
        try:
            entries = self.yaml_store.list_dir(self._state_dir)
        except (FileNotFoundError, NotADirectoryError):
            return

        # SF-7-FIX: Explicit sorted() to guarantee oldest-first ordering
        sorted_files = sorted(f for f in entries if f.endswith(".yaml"))
        while len(sorted_files) > self._max_reconfiguration_history:
            oldest = sorted_files.pop(0)
            try:
                self.yaml_store.delete(
                    f"{self._state_dir}/{oldest}"
                )
            except FileNotFoundError:
                pass
