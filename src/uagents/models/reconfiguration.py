"""Self-reconfiguration models.
Spec reference: Section 20.6 (Self-Reconfiguration as First-Class Action).

Phase 3.5: ReconfigurationAction, ReconfigurationRequest,
           ReconfigurationResult, SecurityScanResult,
           RingEnforcementEvent, ContextPressureConfig.

Literature basis:
- ToolSelf (arXiv:2602.07883): 24.1% performance gain from self-reconfiguration
- Xu & Yan (arXiv:2602.12430): Skill Trust Framework, ring-based protection
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .base import FrameworkModel, IdentifiableModel
from .protection import ProtectionRing


class ReconfigurationAction(StrEnum):
    """Actions an agent can take to reconfigure itself (Section 20.6)."""

    TOOL_LOAD = "tool_load"            # Load a specific tool for next step
    TOOL_UNLOAD = "tool_unload"        # Unload a tool no longer needed
    CONTEXT_COMPRESS = "context_compress"  # Trigger context compression
    CONTEXT_EXPAND = "context_expand"    # Request more context space
    STRATEGY_SWITCH = "strategy_switch"  # Change reasoning strategy
    BUDGET_REALLOCATE = "budget_reallocate"  # Reallocate remaining budget


class ReconfigurationRequest(IdentifiableModel):
    """An agent's request to reconfigure itself.

    Every reconfiguration is logged with a rationale.
    Constraints are validated before execution.

    Persisted to: instances/{domain}/state/reconfigurations/
    """

    agent_id: str
    action: ReconfigurationAction
    target: str  # What to reconfigure (tool name, strategy name, budget category)
    parameters: dict[str, str] = Field(default_factory=dict)  # Action-specific params
    rationale: str  # Required: why this reconfiguration is needed
    budget_delta_pct: float = 0.0  # For BUDGET_REALLOCATE: change percentage (-30 to +30)


class ReconfigurationResult(FrameworkModel):
    """Result of a reconfiguration attempt.

    Includes whether the request was approved, what was changed,
    and any constraint violations that prevented the change.
    """

    request_id: str
    approved: bool
    action_taken: str = ""
    constraint_violated: str = ""  # Non-empty if rejected
    tokens_before: int = 0
    tokens_after: int = 0


class SecurityScanResult(IdentifiableModel):
    """Result of a security vulnerability scan on Ring 3 skills.

    Persisted to: instances/{domain}/state/skills/security-scans/

    Scans check for known vulnerability patterns in skill
    instruction fragments (SoK Agent Skills: 26.1% vulnerability rate).
    """

    skills_scanned: int = 0
    vulnerabilities_found: int = 0
    quarantined_skills: list[str] = Field(default_factory=list)
    scan_details: list[dict[str, str]] = Field(default_factory=list)
    tokens_used: int = Field(ge=0, default=0)


class RingEnforcementEvent(IdentifiableModel):
    """Record of a ring enforcement action.

    Logged whenever the RingEnforcer detects or prevents a ring
    violation. CRITICAL events trigger HARD_FAIL.

    Persisted to: instances/{domain}/state/ring-enforcement/
    """

    event_type: str  # "hash_check", "access_denied", "violation_detected", "recovery"
    ring: ProtectionRing
    target: str  # File path or capability name
    detail: str
    severity: str  # "info", "warning", "critical"
    recovery_action: str = ""  # What was done to recover (if anything)


class ContextPressureConfig(FrameworkModel):
    """Configuration for context pressure management.

    Loaded from core/context-pressure.yaml. All thresholds
    for pressure levels, compression cascade, and Ring 0 reservation.
    """

    # Context pressure thresholds (fraction of context window)
    # IFM-N68: healthy_threshold removed — HEALTHY is implicit (below pressure_threshold)
    pressure_threshold: float = 0.60
    critical_threshold: float = 0.80
    overflow_threshold: float = 0.95

    # Compression cascade triggers (fraction of context window)
    history_compression_trigger: float = 0.60
    tool_reduction_trigger: float = 0.70
    task_pruning_trigger: float = 0.80
    system_compress_trigger: float = 0.90
    emergency_trigger: float = 0.95

    # Ring 0 reservation
    ring_0_reserved_tokens: int = 2000
    min_productive_tokens: int = 1000  # Below this: HARD_FAIL

    # Compression parameters
    history_keep_recent: int = 3  # Keep last N turns detailed
    tool_reduction_target: int = 3  # Reduce to top-N tools

    # Information placement
    edge_placement_enabled: bool = True
