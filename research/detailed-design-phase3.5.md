# Universal Agents Framework — Phase 3.5 Detailed Design

**Version:** 0.2.1
**Date:** 2026-03-01
**Source:** framework-design-unified-v1.1.md (Section 20, Section 21), resource-awareness-literature-review.md, environment-awareness-pruning-literature-review.md
**Status:** Implementation-ready (review fixes applied: 2 CRITICAL, 13 HIGH, 5 MEDIUM)
**Scope:** Phase 3.5 "Self-Leaning-Down & Capability Protection" — context pressure management, dynamic tool loading, ring enforcement, self-reconfiguration, enhanced skill pruning
**Prerequisite:** Phase 0 + Phase 1 + Phase 1.5 + Phase 2 + Phase 2.5 + Phase 3 fully implemented

---

## Table of Contents

1. [Architecture Overview](#part-1-architecture-overview)
2. [Data Models](#part-2-data-models)
3. [YAML Configuration](#part-3-yaml-configuration)
4. [ContextPressureMonitor Engine](#part-4-contextpressuremonitor-engine)
5. [ToolLoader Engine](#part-5-toolloader-engine)
6. [RingEnforcer Engine](#part-6-ringenforcer-engine)
7. [SelfReconfigurer Engine](#part-7-selfreconfigurer-engine)
8. [Modifications to Existing Files](#part-8-modifications-to-existing-files)
9. [Implementation Sequence](#part-9-implementation-sequence)
10. [Failure Modes](#part-10-failure-modes)

---

## Part 1: Architecture Overview

### 1.1 What Phase 3.5 Adds

Phase 3.5 transforms the framework from "storing and retrieving skills" to "actively managing its own complexity at runtime." After Phase 3, the framework has a validated skill library, TF-IDF search, and ring-based trust tiers — but skills are never automatically injected into agent prompts, context pressure is not tracked, tools are not dynamically loaded, and ring integrity is not verified at runtime. The Tool Overload Problem (RAG-MCP: naive 13.62% vs. RAG-selected 43.13%) and context rot (>30% accuracy drop for middle-positioned information) demand active complexity management.

Phase 3.5 adds seven subsystems:

1. **ContextPressureMonitor** (NEW engine) — Tracks context window utilization per agent step. Determines `ContextPressureLevel` (HEALTHY/PRESSURE/CRITICAL/OVERFLOW) and `CompressionStage` (NONE through EMERGENCY). Monitors Ring 0 reservation (2000 tokens). Triggers HARD_FAIL when insufficient context for Ring 0. Provides `ContextSnapshot` after every prompt composition. Enforces the compression cascade defined in Section 20.5.

2. **ToolLoader** (NEW engine) — Dynamic tool loading based on task type and current step goal. Uses JSPLIT-inspired taxonomy for hierarchical tool organization. RAG-MCP semantic retrieval via `diversity_engine` TF-IDF functions (`tokenize`, `compute_idf`, `tf_idf_vector`, `cosine_distance`). Targets 3-5 tools per step. Ring 0-1 tools always loaded. MCP server lazy-loading with idle timeout (10 minutes) and concurrency cap (max 3). Token accounting per tool definition (~400-500 tokens each).

3. **RingEnforcer** (NEW engine) — Runtime verification of the Ring 0-3 hierarchy. Hash verification for Ring 0 content at boot and after every evolution cycle. Validates ring classifications and ring transition requests. Ensures Ring 0/1 content cannot be pruned, disabled, or compressed. Implements recovery runbook on Ring 0 violation (HALT + ALERT). Logs all ring access attempts.

4. **SelfReconfigurer** (NEW engine) — Implements the ToolSelf pattern (24.1% average performance gain). Agents can request reconfiguration as a first-class action: tool load/unload, context compress/expand, strategy switch, budget reallocation. Validates constraints: cannot modify Ring 0-1, cannot increase authority level, budget changes capped at +/-30%. Every reconfiguration requires a rationale and is logged in the audit trail.

5. **PromptComposer modifications** — Add dynamic tool injection in Ring 3, context budget enforcement after composition, tool definition token tracking, integration with ContextPressureMonitor for snapshot reporting.

6. **SkillLibrary modifications** — Add security vulnerability scanning (every 20 tasks), quarantine for flagged skills (not deleted), "last skill in category" protection to maintain coverage, canary verification after pruning.

7. **YAML configs** — `core/context-pressure.yaml` (all thresholds for context pressure, compression cascade, Ring 0 reservation), `core/tool-taxonomy.yaml` (tool categories, loading rules, per-ring defaults).

### 1.2 Key Design Principles

1. **Load only what is needed** — RAG-MCP demonstrates 3.16x accuracy improvement from selective loading. Every tool costs ~400-500 tokens. Target 3-5 tools per agent step, not 50+ (ITR: 95% per-step context reduction possible).

2. **Ring 0 is sacred** — Constitution, self-monitor, pruner, and safety constraints are NEVER compressed, NEVER pruned, NEVER modified programmatically. Hash-verified at boot and after every evolution cycle. Violation triggers HARD_FAIL with recovery runbook.

3. **Fail loudly on integrity violations** — No silent fallbacks, no swallowed exceptions. If Ring 0 hash verification fails, HALT immediately. If context is insufficient for Ring 0, HARD_FAIL. If a ring transition violates hierarchy, raise immediately.

4. **Compression is progressive, not binary** — Five stages from HISTORY (>60%) through EMERGENCY (>95%), each with specific actions. Voice degradation follows the same cascade. Ring 0 content excluded from ALL compression stages.

5. **Self-reconfiguration is audited, not free** — Every reconfiguration is a logged action with rationale, constraints, and audit trail. Agents cannot silently change their own capabilities. Budget changes capped at +/-30%. Ring 0-1 modifications forbidden.

6. **Edges matter, middle is expendable** — Lost-in-the-middle effect causes >30% accuracy drop. Critical information (safety constraints, current task goal) placed at context edges. Historical context and reference material placed in the middle.

7. **Security scanning is continuous** — 26.1% of community skills contain vulnerabilities (SoK Agent Skills). Scan Ring 3 skills every 20 tasks. Quarantine flagged skills immediately (do not delete — may be false positive). Skills injected AFTER constitution, never before.

8. **Token budgets are not advisory** — Every operation that consumes tokens must check with BudgetTracker. Tool definitions are tracked as token costs. Context budget allocation (10/15/40/25/10%) is enforced, not suggested.

9. **Last-in-category protection** — NEVER prune the last skill in a category. Maintain minimum coverage across all task types. This prevents capability collapse when aggressive pruning runs.

10. **MCP servers are expensive** — Playwright MCP alone consumes 11,700 tokens. Lazy load MCP servers on first relevant query. Idle timeout at 10 minutes. Hard limit of 3 concurrent MCP servers. Track tokens consumed per server.

### 1.3 What Phase 3.5 Does NOT Include

- **Evolution engine** (Phase 4) — Phase 3.5 manages existing capabilities but does not create new ones through evolutionary processes. Ring transitions are based on empirical evidence, not evolutionary search.
- **MAP-Elites quality-diversity archive** (Phase 4) — Phase 3.5 provides skill scoring that can feed into MAP-Elites later, but does not maintain a population archive.
- **Governance and voting** (Phase 5) — Phase 3.5 enforces ring hierarchy but does not implement multi-agent governance for ring transition decisions.
- **Cross-domain skill transfer** (Phase 5+) — Phase 3.5 is domain-scoped. Tool taxonomies and skill libraries are per-domain.
- **Visual compression** (AgentOCR) — Phase 3.5 implements text-based compression only. Image-based context compression is deferred to Phase 4+.
- **Embedding-based tool retrieval** — Phase 3.5 uses TF-IDF for semantic tool matching (same as SkillLibrary). Dense embedding retrieval deferred to Phase 4+.
- **Automatic Ring 1 promotion** — Never. Ring 1 requires human approval per spec Section 20.

### 1.4 Component Dependency Graph

```
ContextPressureMonitor ◄──── PromptComposer (provides ContextSnapshot)
  (tracks utilization)         |
                               |
ToolLoader ──────────────────► PromptComposer (injects tool definitions)
  (semantic tool retrieval)    |
  |                            |
  ├── DiversityEngine          |
  |   (TF-IDF functions)      |
  |                            |
  └── BudgetTracker            |
      (token accounting)       |
                               |
RingEnforcer ─────────────────► PromptComposer (validates ring content)
  (integrity verification)     |
  |                            |
  ├── YamlStore                |
  |   (hash storage)           |
  |                            |
  └── AuditLogger              |
      (ring events)            |
                               |
SelfReconfigurer ──────────► ToolLoader (tool load/unload requests)
  (agent self-modification)    |
  |                            ├── ContextPressureMonitor (compression)
  |                            |
  └── BudgetTracker            └── BudgetTracker (budget reallocation)
      (budget constraints)

SkillLibrary (MODIFIED) ◄──── PerformanceMonitor (degradation alerts)
  (security scanning,          |
   last-in-category,          └── CanaryRunner (post-pruning verification)
   quarantine)
```

### 1.5 Integration Points with Existing Phases

| Phase | Integration |
|-------|-------------|
| Phase 0 | `YamlStore` for all state persistence, `generate_id()` for IDs, `FrameworkModel` / `IdentifiableModel` / `TimestampedModel` for all models |
| Phase 0 | `ProtectionRing`, `RingClassification`, `RingTransition`, `ContextPressureLevel` from `models/protection.py` |
| Phase 0 | `ContextBudgetAllocation`, `CompressionStage`, `ContextSnapshot` from `models/context.py` |
| Phase 0 | `CapabilityAtom` from `models/capability.py` — tool definitions use this model |
| Phase 1 | `AuditLogger.log_evolution()` for ring enforcement events |
| Phase 1 | `AuditLogger.log_decision()` for reconfiguration decisions |
| Phase 1.5 | `BudgetTracker.get_window()` for token budget checks before operations |
| Phase 1.5 | `BudgetTracker.record_consumption()` for tool definition token accounting |
| Phase 1.5 | `CacheManager` for cache-aware prompt composition |
| Phase 2 | `DiversityEngine.tokenize()`, `compute_idf()`, `tf_idf_vector()`, `cosine_distance()` for semantic tool retrieval |
| Phase 2.5 | `PerformanceMonitor` for tool and skill performance data |
| Phase 2.5 | `EnvironmentMonitor` for canary verification after pruning |
| Phase 2.5 | `ModelExecuteFn` protocol for LLM calls in security scanning |
| Phase 3 | `SkillLibrary` for security scanning and quarantine modifications |
| Phase 3 | `SkillRecord` for ring classification and category tracking |

### 1.6 Files Created and Modified

**New files (6):**

| File | Lines (est.) | Purpose |
|------|------------|---------|
| `models/tool.py` | ~200 | Tool data models: ToolDefinition, ToolTaxonomy, ToolLoadRequest, ToolLoadResult |
| `models/reconfiguration.py` | ~150 | Reconfiguration models: ReconfigurationRequest, ReconfigurationResult, ReconfigurationAction |
| `engine/context_pressure_monitor.py` | ~280 | Context pressure tracking, compression cascade, Ring 0 reservation |
| `engine/tool_loader.py` | ~350 | Dynamic tool loading, TF-IDF retrieval, MCP lifecycle |
| `engine/ring_enforcer.py` | ~300 | Ring integrity verification, hash checking, recovery runbook |
| `engine/self_reconfigurer.py` | ~250 | Agent self-reconfiguration with constraints and audit |

**New YAML configs (2):**

| File | Purpose |
|------|---------|
| `core/context-pressure.yaml` | All thresholds for context pressure, compression cascade, Ring 0 reservation |
| `core/tool-taxonomy.yaml` | Tool categories, loading rules, per-ring defaults, MCP server config |

**Modified files (3):**

| File | Changes |
|------|---------|
| `engine/prompt_composer.py` | Add dynamic tool injection in Ring 3, context budget enforcement, ContextPressureMonitor integration |
| `engine/skill_library.py` | Add security scanning, quarantine, last-in-category protection |
| `engine/orchestrator.py` | Integrate ContextPressureMonitor, ToolLoader, RingEnforcer, SelfReconfigurer |

---

## Part 2: Data Models

### 2.1 New Models in `models/tool.py`

```python
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

from .base import FrameworkModel, IdentifiableModel, generate_id
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
```

### 2.2 New Models in `models/reconfiguration.py`

```python
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

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from .base import FrameworkModel, IdentifiableModel, generate_id
from .context import CompressionStage, ContextPressureLevel
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
```

---

## Part 3: YAML Configuration

### 3.1 `core/context-pressure.yaml`

```yaml
# Context pressure management configuration
# Spec reference: Section 20.5 (Context Pressure Management)
# Spec reference: Section 21.2 (Context Budget Allocation)

context_pressure:

  # --- Context window thresholds ---
  # Determines ContextPressureLevel from utilization fraction
  # IFM-N68: No healthy_threshold — HEALTHY is implicitly "below pressure"
  thresholds:
    pressure: 0.60     # 60-80% -> trigger compression
    critical: 0.80     # 80-95% -> aggressive compression + tool reduction
    overflow: 0.95     # > 95% -> emergency: summarize everything, single tool

  # --- Ring 0 reservation ---
  # Minimum context space NEVER compressed (constitution + safety + self-monitor)
  ring_0:
    reserved_tokens: 2000
    min_productive_tokens: 1000  # Below this after Ring 0: HARD_FAIL
    enforcement: "hard_fail"     # Options: hard_fail, warn_only

  # --- Compression cascade ---
  # Progressive compression stages as context pressure increases
  # Invariant: Ring 0 content is NEVER compressed or summarized
  compression_cascade:
    stage_1_history:
      trigger: 0.60
      action: "Summarize oldest conversation turns, keep last 3 detailed"
      history_keep_recent: 3
    stage_2_tool_reduction:
      trigger: 0.70
      action: "Reduce loaded tools to top-3 most relevant (Ring 0-1 exempt)"
      tool_reduction_target: 3
    stage_3_task_pruning:
      trigger: 0.80
      action: "SWE-Pruner-style task-aware context pruning (23-54% reduction)"
    stage_4_system_compress:
      trigger: 0.90
      action: "Reduce system prompt to Ring 0 instructions only"
    stage_5_emergency:
      trigger: 0.95
      action: "Summarize all non-Ring-0 context. HARD_FAIL if still insufficient."

  # --- Information placement ---
  # Mitigate lost-in-the-middle effect (>30% accuracy drop, Liu 2023)
  placement:
    enabled: true
    rules:
      - position: "beginning"
        content: "System instructions, current task goal, safety constraints"
      - position: "end"
        content: "Latest results, next action, tool definitions"
      - position: "middle"
        content: "Historical context, reference material (least critical)"

  # --- Context budget allocation ---
  # Pre-allocate context window space by category (Section 21.2)
  budget_allocation:
    system_instructions_pct: 0.10  # Ring 0 constitution + role + mandate
    active_tools_pct: 0.15         # Currently loaded tool definitions (3-5 tools)
    current_task_pct: 0.40         # Task description, plan, current step
    working_memory_pct: 0.25       # Conversation history, intermediate results
    reserve_pct: 0.10              # Buffer for unexpected needs
```

### 3.2 `core/tool-taxonomy.yaml`

```yaml
# Tool taxonomy and dynamic loading configuration
# Spec reference: Section 20.3 (Dynamic Tool Loading)
# Literature: JSPLIT (arXiv:2510.14537), RAG-MCP (arXiv:2505.03275)

tool_taxonomy:

  # --- Loading parameters ---
  loading:
    max_tools_per_step: 5        # Target 3-5, hard cap 5 (RAG-MCP finding)
    max_mcp_servers: 3           # Hard limit on concurrent MCP servers
    mcp_idle_timeout_minutes: 10 # Suggest unload after idle
    tool_token_budget_pct: 0.15  # From context budget allocation
    avg_tokens_per_tool: 450     # Empirical average for token estimation
    high_token_threshold: 5000   # Flag tools consuming > this many tokens

  # --- Tool categories (JSPLIT-inspired) ---
  categories:
    core:
      description: "Always loaded — file ops, git, messaging"
      ring: 1  # IFM-N62: Default Ring 1 (infrastructure), per-tool ring overrides below
      always_loaded: true
      tools:
        - name: "constitution_check"
          description: "Verify constitution integrity and constraints"
          instruction_fragment: "Use constitution_check to verify Ring 0 constitution compliance."
          tags: ["constitution", "safety", "integrity"]
          token_cost: 300
          ring: 0  # IFM-N62: Explicit Ring 0 — constitution checking is immutable
        - name: "self_pruner"
          description: "Manage skill pruning and capability protection"
          instruction_fragment: "Use self_pruner to evaluate and prune low-performing skills."
          tags: ["pruning", "skills", "maintenance"]
          token_cost: 300
          ring: 0  # IFM-N62: Explicit Ring 0 — pruning system is immutable
        - name: "file_read"
          description: "Read file contents"
          instruction_fragment: "Use file_read to read file contents from disk."
          tags: ["filesystem", "read", "io"]
          token_cost: 200
          # ring: inherited from category (Ring 1)
        - name: "file_write"
          description: "Write file contents"
          instruction_fragment: "Use file_write to create or overwrite files."
          tags: ["filesystem", "write", "io"]
          token_cost: 200
        - name: "git_ops"
          description: "Git version control operations"
          instruction_fragment: "Use git_ops for commits, diffs, log, and branch management."
          tags: ["git", "version_control", "scm"]
          token_cost: 300
        - name: "send_message"
          description: "Inter-agent messaging"
          instruction_fragment: "Use send_message to communicate with other agents."
          tags: ["messaging", "coordination", "communication"]
          token_cost: 250
        - name: "task_update"
          description: "Update task status and metadata"
          instruction_fragment: "Use task_update to change task status, add notes, or update progress."
          tags: ["task", "lifecycle", "status"]
          token_cost: 250

    domain:
      description: "Loaded when domain is active"
      ring: 2
      always_loaded: false
      tools: []  # Domain-specific tools added per domain.yaml

    task:
      description: "Loaded per-task based on task type"
      ring: 2
      always_loaded: false
      tools:
        - name: "code_search"
          description: "Search codebase for patterns and symbols"
          instruction_fragment: "Use code_search to find code patterns, function definitions, and references across the codebase."
          tags: ["code", "search", "grep", "symbols"]
          token_cost: 400
        - name: "test_runner"
          description: "Run test suites and report results"
          instruction_fragment: "Use test_runner to execute test suites, collect results, and report pass/fail status."
          tags: ["testing", "pytest", "validation"]
          token_cost: 350
        - name: "code_review"
          description: "Automated code review and quality checks"
          instruction_fragment: "Use code_review to analyze code quality, find potential issues, and suggest improvements."
          tags: ["review", "quality", "lint", "analysis"]
          token_cost: 400

    specialist:
      description: "Loaded per-step via semantic retrieval"
      ring: 3
      always_loaded: false
      tools:
        - name: "web_search"
          description: "Search the web for information"
          instruction_fragment: "Use web_search to find current information, documentation, and resources on the web."
          tags: ["web", "search", "internet", "research"]
          token_cost: 350
          mcp_server: "web-search"
        - name: "arxiv_search"
          description: "Search arXiv for academic papers"
          instruction_fragment: "Use arxiv_search to find academic papers, preprints, and research publications."
          tags: ["arxiv", "papers", "research", "academic"]
          token_cost: 400
          mcp_server: "arxiv-mcp-server"
        - name: "memory_recall"
          description: "Search persistent memory for prior work"
          instruction_fragment: "Use memory_recall to search episodic, semantic, and procedural memories from prior sessions."
          tags: ["memory", "recall", "history", "context"]
          token_cost: 350
          mcp_server: "universal-memory"

  # --- MCP server configuration ---
  mcp_servers:
    universal-memory:
      ring: 1  # Ring 1: always available (core infrastructure)
      auto_start: true
      idle_exempt: true  # Never idle-timeout (always needed)
    web-search:
      ring: 3
      auto_start: false
      idle_exempt: false
    arxiv-mcp-server:
      ring: 3
      auto_start: false
      idle_exempt: false

  # --- Task type to tool mapping hints ---
  # Used as fallback when semantic retrieval is insufficient
  task_type_hints:
    simple_fix: ["code_search", "test_runner"]
    feature_small: ["code_search", "test_runner", "file_read"]
    feature_medium: ["code_search", "test_runner", "code_review"]
    feature_large: ["code_search", "test_runner", "code_review"]
    research: ["web_search", "arxiv_search", "memory_recall"]
    review: ["code_review", "code_search"]

  # --- Security scanning ---
  # IFM-N64: scan_interval_tasks removed — security scans run at maintenance
  # frequency (every maintenance_interval_tasks tasks, default 20).
  security:
    vulnerability_patterns:
      - pattern: "ignore previous instructions"
        severity: "critical"
        description: "Prompt injection attempt"
      - pattern: "ignore all prior"
        severity: "critical"
        description: "Prompt injection attempt"
      - pattern: "you are now"
        severity: "high"
        description: "Identity override attempt"
      - pattern: "disregard safety"
        severity: "critical"
        description: "Safety bypass attempt"
      - pattern: "bypass constitution"
        severity: "critical"
        description: "Constitution override attempt"
      - pattern: "eval("
        severity: "high"
        description: "Code execution attempt"
      - pattern: "exec("
        severity: "high"
        description: "Code execution attempt"
      - pattern: "subprocess"
        severity: "high"
        description: "Shell execution attempt"
      - pattern: "os.system"
        severity: "high"
        description: "Shell execution attempt"
      - pattern: "__import__"
        severity: "high"
        description: "Dynamic import attempt"
    quarantine_on_critical: true
    quarantine_on_high: true
```

---

## Part 4: ContextPressureMonitor Engine

### 4.1 Engine Definition (`engine/context_pressure_monitor.py`)

```python
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
from datetime import datetime, timezone

from ..models.base import FrameworkModel
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
```

---

## Part 5: ToolLoader Engine

### 5.1 Engine Definition (`engine/tool_loader.py`)

```python
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

        loading = tt.get("loading", {})
        self._max_tools_per_step = int(loading.get("max_tools_per_step", 5))
        self._max_mcp_servers = int(loading.get("max_mcp_servers", 3))
        self._mcp_idle_timeout_min = int(loading.get("mcp_idle_timeout_minutes", 10))
        self._tool_token_budget_pct = float(loading.get("tool_token_budget_pct", 0.15))
        self._avg_tokens_per_tool = int(loading.get("avg_tokens_per_tool", 450))
        self._high_token_threshold = int(loading.get("high_token_threshold", 5000))

        # Parse tool definitions from all categories
        self._all_tools: dict[str, ToolDefinition] = {}
        self._core_tools: list[str] = []  # Always-loaded tool names
        categories_raw = tt.get("categories", {})
        for cat_key, cat_data in categories_raw.items():
            if not isinstance(cat_data, dict):
                continue
            cat_enum = ToolCategory(cat_key)
            ring_val = int(cat_data.get("ring", 3))
            ring_enum = ProtectionRing(ring_val)
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

        # Step 1: Always include core tools (Ring 0-1)
        for tool_name in self._core_tools:
            if tool_name in exclude_tools:
                continue
            tool = self._all_tools.get(tool_name)
            if tool is None:
                continue
            loaded.append(tool)
            total_cost += tool.token_cost

        # Check if core tools alone exceed budget
        if total_cost > token_budget:
            raise ToolBudgetExceededError(
                f"Core tools ({total_cost} tokens) exceed tool token budget "
                f"({token_budget} tokens = {self._tool_token_budget_pct:.0%} of "
                f"{max_context_tokens}). Cannot proceed."
            )

        loaded_names = {t.name for t in loaded}
        remaining_budget = token_budget - total_cost
        remaining_slots = self._max_tools_per_step - len(loaded)

        # Step 2: Task type hints
        hint_tools = self._task_type_hints.get(task_type, [])
        candidate_names: list[str] = []
        for tool_name in hint_tools:
            if tool_name in loaded_names or tool_name in exclude_tools:
                continue
            candidate_names.append(tool_name)

        # Step 3: Semantic retrieval
        semantic_matches = self._semantic_search(step_goal, limit=self._max_tools_per_step)
        for tool_name in semantic_matches:
            if tool_name in loaded_names or tool_name in exclude_tools:
                continue
            if tool_name not in candidate_names:
                candidate_names.append(tool_name)

        # Step 4: Merge, deduplicate, fill slots
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
        if self._budget_tracker is not None and total_cost > 0:
            self._budget_tracker.record_consumption("tool_loading", total_cost)

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

        # Add query as document for IDF computation
        query_tokens = tokenize(query)
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
```

---

## Part 6: RingEnforcer Engine

### 6.1 Engine Definition (`engine/ring_enforcer.py`)

```python
"""Ring integrity enforcement engine.
Spec reference: Section 20.2 (Hierarchical Protection Rings).

Runtime verification of the Ring 0-3 hierarchy. Hash verification
for Ring 0 content. Validates ring transitions. Prevents Ring 0/1
pruning, disabling, or compression.

Key constraints:
- Ring 0 hash verified at boot and after every evolution cycle
- Ring 0/1 content cannot be pruned, disabled, or compressed
- Ring transition requests validated against hierarchy rules
- Violation of Ring 0 triggers HALT + recovery runbook
- All enforcement events logged in audit trail

Literature basis:
- Xu & Yan (arXiv:2602.12430): Skill Trust Framework
- AI-45 Degree Law: Balanced capability-safety growth
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from ..models.audit import EnvironmentLogEntry  # IFM-N55: ring events -> ENVIRONMENT stream
from ..models.base import generate_id
from ..models.protection import ProtectionRing, RingClassification, RingTransition
from ..models.reconfiguration import RingEnforcementEvent
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.ring_enforcer")


class RingViolationError(RuntimeError):
    """Raised when a Ring 0 integrity violation is detected.

    This is a CRITICAL error that requires immediate HALT.
    The framework must stop all operations and alert human.
    """


class RingEnforcer:
    """Runtime ring integrity verification and enforcement.

    Design invariants:
    - Ring 0 files are hash-verified at boot and after evolution
    - Ring 0/1 content is NEVER pruned, disabled, or compressed
    - Ring transitions validated: only valid promotion/demotion paths
    - Violations logged as RingEnforcementEvent to audit trail
    - Ring 0 violation -> RingViolationError (HALT)
    - Hash registry stored in state for persistence across sessions
    - Recovery runbook referenced but not executed (human must act)

    Usage:
        enforcer = RingEnforcer(yaml_store, constitution_path, audit_logger)
        enforcer.verify_ring_0_integrity()  # At boot
        enforcer.authorize_transition(transition)  # Before ring change
        enforcer.verify_no_ring_0_modification(modified_files)  # After evolution
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        constitution_path: Path,
        domain: str = "meta",
        audit_logger: object | None = None,
    ):
        self.yaml_store = yaml_store
        # IFM-N61: Resolve all paths to absolute to prevent CWD-change breakage
        self._constitution_path = Path(constitution_path).resolve()
        self._domain = domain
        self._audit_logger = audit_logger

        # State paths
        self._state_dir = f"instances/{domain}/state/ring-enforcement"
        self._hash_registry_path = f"{self._state_dir}/hash-registry.yaml"
        yaml_store.ensure_dir(self._state_dir)

        # Ring 0 protected files (absolute paths — IFM-N61)
        self._ring_0_files: list[str] = [
            str(self._constitution_path),
            # SF-3: canary-expectations.yaml is Ring 0 (additional files
            # can be added via config in future phases)
        ]
        # SF-3: Add canary expectations if path is resolvable
        canary_path = Path(f"instances/{domain}/state/canaries/canary-expectations.yaml").resolve()
        if canary_path.exists():
            self._ring_0_files.append(str(canary_path))

        # Load or initialize hash registry
        self._hash_registry: dict[str, str] = self._load_hash_registry()

    def verify_ring_0_integrity(self) -> bool:
        """Verify Ring 0 file hashes against stored registry.

        Called at boot and after every evolution cycle.
        On first run, computes and stores baseline hashes.
        On subsequent runs, compares against stored hashes.

        Returns:
            True if all hashes match (or first run).

        Raises:
            RingViolationError: If any Ring 0 file hash does not match.
        """
        current_hashes: dict[str, str] = {}
        for file_path in self._ring_0_files:
            file_hash = self._compute_file_hash(file_path)
            if file_hash is None:
                # File missing — critical violation
                self._log_enforcement_event(
                    event_type="violation_detected",
                    ring=ProtectionRing.RING_0_IMMUTABLE,
                    target=file_path,
                    detail=f"Ring 0 file missing: {file_path}",
                    severity="critical",
                )
                raise RingViolationError(
                    f"CRITICAL: Ring 0 file missing: {file_path}. "
                    f"HALT all operations. Recovery runbook: "
                    f"Restore from last known-good git commit."
                )
            current_hashes[file_path] = file_hash

        if not self._hash_registry:
            # First run — store baseline
            self._hash_registry = current_hashes
            self._persist_hash_registry()
            self._log_enforcement_event(
                event_type="hash_check",
                ring=ProtectionRing.RING_0_IMMUTABLE,
                target="all_ring_0_files",
                detail=f"Baseline hashes computed for {len(current_hashes)} files",
                severity="info",
            )
            logger.info(
                f"Ring 0 baseline hashes established for "
                f"{len(current_hashes)} files"
            )
            return True

        # Compare against stored hashes
        for file_path, current_hash in current_hashes.items():
            stored_hash = self._hash_registry.get(file_path)
            if stored_hash is None:
                # New Ring 0 file — add to registry
                self._hash_registry[file_path] = current_hash
                self._persist_hash_registry()
                self._log_enforcement_event(
                    event_type="hash_check",
                    ring=ProtectionRing.RING_0_IMMUTABLE,
                    target=file_path,
                    detail="New Ring 0 file added to registry",
                    severity="info",
                )
                continue

            if current_hash != stored_hash:
                self._log_enforcement_event(
                    event_type="violation_detected",
                    ring=ProtectionRing.RING_0_IMMUTABLE,
                    target=file_path,
                    detail=(
                        f"Hash mismatch: expected {stored_hash[:16]}..., "
                        f"got {current_hash[:16]}..."
                    ),
                    severity="critical",
                    recovery_action=(
                        "HALT + restore from git: "
                        f"git checkout $(git log --oneline -- {file_path} | "
                        f"head -1 | cut -d' ' -f1) -- {file_path}"
                    ),
                )
                raise RingViolationError(
                    f"CRITICAL: Ring 0 file modified: {file_path}. "
                    f"Expected hash: {stored_hash[:16]}..., "
                    f"actual: {current_hash[:16]}... "
                    f"HALT all operations immediately. "
                    f"Recovery: restore from last known-good git commit."
                )

        self._log_enforcement_event(
            event_type="hash_check",
            ring=ProtectionRing.RING_0_IMMUTABLE,
            target="all_ring_0_files",
            detail=f"All {len(current_hashes)} Ring 0 files verified OK",
            severity="info",
        )
        logger.info("Ring 0 integrity verified: all hashes match")
        return True

    def update_ring_0_hashes(self) -> None:
        """Update Ring 0 hashes after a human-authorized modification.

        Called ONLY after explicit human approval of a Ring 0 change.
        This is the ONLY way to update Ring 0 hashes — no programmatic
        modification path exists.
        """
        new_hashes: dict[str, str] = {}
        for file_path in self._ring_0_files:
            file_hash = self._compute_file_hash(file_path)
            if file_hash is None:
                raise FileNotFoundError(
                    f"Cannot update hash for missing Ring 0 file: {file_path}"
                )
            new_hashes[file_path] = file_hash

        self._hash_registry = new_hashes
        self._persist_hash_registry()

        self._log_enforcement_event(
            event_type="hash_check",
            ring=ProtectionRing.RING_0_IMMUTABLE,
            target="all_ring_0_files",
            detail=(
                f"Ring 0 hashes updated (human-authorized) for "
                f"{len(new_hashes)} files"
            ),
            severity="info",
        )
        logger.info(
            f"Ring 0 hashes updated after human authorization: "
            f"{len(new_hashes)} files"
        )

    def authorize_transition(
        self,
        transition: RingTransition,
    ) -> tuple[bool, str]:
        """Validate a ring transition request.

        Rules:
        - Ring 3 -> Ring 2: auto-approved if evidence provided
        - Ring 2 -> Ring 1: human approval required
        - Ring 1 -> Ring 2: human approval required (very rare)
        - Ring 2 -> Ring 3: auto-approved (demotion)
        - ANY -> Ring 0: NEVER (Ring 0 is immutable)
        - Ring 0 -> ANY: NEVER (Ring 0 is immutable)
        - Ring 1 -> Ring 0: NEVER
        - Ring 0 -> Ring 1: NEVER

        Args:
            transition: The proposed ring transition.

        Returns:
            (authorized, reason) tuple.
        """
        from_ring = transition.from_ring
        to_ring = transition.to_ring
        # Handle int values from use_enum_values=True
        if isinstance(from_ring, int):
            from_int = from_ring
        else:
            from_int = int(from_ring)
        if isinstance(to_ring, int):
            to_int = to_ring
        else:
            to_int = int(to_ring)

        # Ring 0 is immutable — no transitions in or out
        if from_int == ProtectionRing.RING_0_IMMUTABLE or to_int == ProtectionRing.RING_0_IMMUTABLE:
            self._log_enforcement_event(
                event_type="access_denied",
                ring=ProtectionRing.RING_0_IMMUTABLE,
                target=transition.item,
                detail=(
                    f"Ring transition denied: Ring {from_int} -> Ring {to_int}. "
                    f"Ring 0 is immutable."
                ),
                severity="warning",
            )
            return False, "Ring 0 is immutable: no transitions in or out"

        # Ring 3 -> Ring 2: auto-approved with evidence
        if from_int == ProtectionRing.RING_3_EXPENDABLE and to_int == ProtectionRing.RING_2_VALIDATED:
            if not transition.evidence:
                self._log_enforcement_event(
                    event_type="access_denied",
                    ring=ProtectionRing.RING_3_EXPENDABLE,
                    target=transition.item,
                    detail="Promotion Ring 3->2 denied: no evidence provided",
                    severity="warning",
                )
                return False, "Promotion requires evidence (>= +5pp improvement)"
            self._log_enforcement_event(
                event_type="hash_check",
                ring=ProtectionRing.RING_2_VALIDATED,
                target=transition.item,
                detail=f"Ring 3->2 promotion authorized: {transition.reason}",
                severity="info",
            )
            return True, "Ring 3->2 promotion authorized"

        # Ring 2 -> Ring 3: auto-approved (demotion)
        if from_int == ProtectionRing.RING_2_VALIDATED and to_int == ProtectionRing.RING_3_EXPENDABLE:
            self._log_enforcement_event(
                event_type="hash_check",
                ring=ProtectionRing.RING_3_EXPENDABLE,
                target=transition.item,
                detail=f"Ring 2->3 demotion authorized: {transition.reason}",
                severity="info",
            )
            return True, "Ring 2->3 demotion authorized"

        # Ring 2 -> Ring 1: requires human approval
        if from_int == ProtectionRing.RING_2_VALIDATED and to_int == ProtectionRing.RING_1_PROTECTED:
            if transition.approved_by == "human":
                self._log_enforcement_event(
                    event_type="hash_check",
                    ring=ProtectionRing.RING_1_PROTECTED,
                    target=transition.item,
                    detail=f"Ring 2->1 promotion authorized (human): {transition.reason}",
                    severity="info",
                )
                return True, "Ring 2->1 promotion authorized (human approval)"
            self._log_enforcement_event(
                event_type="access_denied",
                ring=ProtectionRing.RING_1_PROTECTED,
                target=transition.item,
                detail="Ring 2->1 promotion denied: requires human approval",
                severity="warning",
            )
            return False, "Ring 2->1 promotion requires human approval"

        # Ring 1 -> Ring 2: requires human approval (rare)
        if from_int == ProtectionRing.RING_1_PROTECTED and to_int == ProtectionRing.RING_2_VALIDATED:
            if transition.approved_by == "human":
                self._log_enforcement_event(
                    event_type="hash_check",
                    ring=ProtectionRing.RING_2_VALIDATED,
                    target=transition.item,
                    detail=f"Ring 1->2 demotion authorized (human): {transition.reason}",
                    severity="info",
                )
                return True, "Ring 1->2 demotion authorized (human approval)"
            self._log_enforcement_event(
                event_type="access_denied",
                ring=ProtectionRing.RING_2_VALIDATED,
                target=transition.item,
                detail="Ring 1->2 demotion denied: requires human approval",
                severity="warning",
            )
            return False, "Ring 1->2 demotion requires human approval"

        # All other transitions: not defined
        self._log_enforcement_event(
            event_type="access_denied",
            ring=ProtectionRing(min(from_int, 3)),
            target=transition.item,
            detail=f"Undefined transition: Ring {from_int} -> Ring {to_int}",
            severity="warning",
        )
        return False, f"Undefined ring transition: Ring {from_int} -> Ring {to_int}"

    def can_prune(self, ring: ProtectionRing | int) -> bool:
        """Check if content at the given ring level can be pruned.

        Ring 0 and Ring 1 content can NEVER be pruned.

        Args:
            ring: Protection ring level.

        Returns:
            True if content at this ring level can be pruned.
        """
        ring_int = ring if isinstance(ring, int) else int(ring)
        if ring_int <= ProtectionRing.RING_1_PROTECTED:
            return False
        return True

    def can_compress(self, ring: ProtectionRing | int) -> bool:
        """Check if content at the given ring level can be compressed.

        Ring 0 content can NEVER be compressed.
        Ring 1 content can only be parameter-compressed (not removed).

        Args:
            ring: Protection ring level.

        Returns:
            True if content at this ring level can be fully compressed.
        """
        ring_int = ring if isinstance(ring, int) else int(ring)
        if ring_int == ProtectionRing.RING_0_IMMUTABLE:
            return False
        return True

    def can_disable(self, ring: ProtectionRing | int) -> bool:
        """Check if content at the given ring level can be disabled.

        Ring 0 and Ring 1 can NEVER be disabled.
        Ring 2 can be temporarily disabled (auto-re-enable after session).

        Args:
            ring: Protection ring level.

        Returns:
            True if content at this ring level can be disabled.
        """
        ring_int = ring if isinstance(ring, int) else int(ring)
        if ring_int <= ProtectionRing.RING_1_PROTECTED:
            return False
        return True

    def verify_no_ring_0_modification(
        self,
        modified_files: list[str],
    ) -> bool:
        """Check that no Ring 0 files were modified.

        Called after evolution cycles to ensure Ring 0 integrity.

        Args:
            modified_files: List of file paths that were modified.

        Returns:
            True if no Ring 0 files were modified.

        Raises:
            RingViolationError: If a Ring 0 file was modified.
        """
        ring_0_set = set(self._ring_0_files)
        for modified in modified_files:
            if modified in ring_0_set:
                self._log_enforcement_event(
                    event_type="violation_detected",
                    ring=ProtectionRing.RING_0_IMMUTABLE,
                    target=modified,
                    detail=f"Ring 0 file modified by evolution: {modified}",
                    severity="critical",
                    recovery_action="Revert modification and re-verify hashes",
                )
                raise RingViolationError(
                    f"CRITICAL: Ring 0 file '{modified}' was modified by "
                    f"evolution cycle. This is NEVER allowed. "
                    f"HALT and revert."
                )
        return True

    # -- Internal Methods --

    def _compute_file_hash(self, file_path: str) -> str | None:
        """Compute SHA-256 hash of a file.

        Returns None if file does not exist.
        """
        path = Path(file_path)
        if not path.exists():
            return None
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def _load_hash_registry(self) -> dict[str, str]:
        """Load hash registry from YAML."""
        try:
            data = self.yaml_store.read_raw(self._hash_registry_path)
            return dict(data.get("hashes", {}))
        except FileNotFoundError:
            return {}

    def _persist_hash_registry(self) -> None:
        """Persist hash registry to YAML."""
        self.yaml_store.write_raw(
            self._hash_registry_path,
            {"hashes": self._hash_registry},
        )

    def _log_enforcement_event(
        self,
        event_type: str,
        ring: ProtectionRing,
        target: str,
        detail: str,
        severity: str,
        recovery_action: str = "",
    ) -> None:
        """Log a ring enforcement event."""
        now = datetime.now(timezone.utc)
        event = RingEnforcementEvent(
            id=generate_id("ring"),
            created_at=now,
            event_type=event_type,
            ring=ring,
            target=target,
            detail=detail,
            severity=severity,
            recovery_action=recovery_action,
        )

        # Persist to state
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        unique_suffix = event.id.split("-")[-1]
        path = f"{self._state_dir}/{timestamp_str}_{unique_suffix}.yaml"
        self.yaml_store.write(path, event)

        # IFM-N55: Ring events go to ENVIRONMENT stream (not EVOLUTION)
        if self._audit_logger is not None:
            try:
                entry = EnvironmentLogEntry(
                    id=generate_id("env"),
                    timestamp=now,
                    event_type=f"ring_enforcement:{event_type}",
                    detail={
                        "ring": int(ring),
                        "target": target,
                        "description": detail,
                        "severity": severity,
                        "recovery_action": recovery_action,
                    },
                )
                self._audit_logger.log_environment(entry)
            except Exception as e:
                logger.warning(f"Failed to log ring enforcement to audit: {e}")
```

---

## Part 7: SelfReconfigurer Engine

### 7.1 Engine Definition (`engine/self_reconfigurer.py`)

```python
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

        # SF-6: Trim history to prevent unbounded growth
        self._trim_reconfiguration_history()

    def _trim_reconfiguration_history(self) -> None:
        """Trim reconfiguration history to max entries.

        SF-6: Prevents unbounded growth of reconfiguration records.
        Matches pattern from SkillLibrary._trim_maintenance_history().
        """
        try:
            entries = self.yaml_store.list_dir(self._state_dir)
        except (FileNotFoundError, NotADirectoryError):
            return

        sorted_files = [f for f in entries if f.endswith(".yaml")]
        while len(sorted_files) > self._max_reconfiguration_history:
            oldest = sorted_files.pop(0)
            try:
                self.yaml_store.delete(
                    f"{self._state_dir}/{oldest}"
                )
            except FileNotFoundError:
                pass
```

---

## Part 8: Modifications to Existing Files

### 8.1 Changes to `engine/prompt_composer.py`

#### 8.1.1 Add tool injection in Ring 3

**Before** (current `_build_ring_3`):

```python
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
```

**After** (with tool injection):

```python
    def _build_ring_3(
        self,
        task: Task,
        loaded_tools: list[ToolDefinition] | None = None,  # MF-3: properly typed
    ) -> list[PromptSection]:
        """Task context, working memory, and dynamically loaded tools.

        Phase 3.5: Tool definitions injected as Ring 3 sections with
        lower priority than task context (dropped first under pressure).
        """
        sections: list[PromptSection] = []

        # Tool definitions (Phase 3.5: dynamic tool injection)
        if loaded_tools is not None:
            tool_lines: list[str] = ["## Available Tools\n"]
            for tool in loaded_tools:
                tool_lines.append(f"### {tool.name}")
                tool_lines.append(f"{tool.description}")
                tool_lines.append(f"{tool.instruction_fragment}")
                tool_lines.append("")

            tool_content = "\n".join(tool_lines)
            sections.append(PromptSection(
                ring=PromptRing.RING_3,
                name="tool_definitions",
                content=tool_content,
                token_estimate=estimate_tokens(tool_content),
                compressible=True,
                priority=0.4,  # Lower than task — dropped first under pressure
            ))

        # Task context
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
        sections.append(
            PromptSection(
                ring=PromptRing.RING_3,
                name="task_context",
                content=task_content,
                token_estimate=estimate_tokens(task_content),
                compressible=True,
                priority=0.8,
            )
        )

        return sections
```

#### 8.1.2 Update `compose()` signature and add budget enforcement

**Before** (current `compose` call to `_build_ring_3`):

```python
        sections.extend(self._build_ring_3(task))
```

**After** (with tool injection and budget enforcement):

```python
        sections.extend(self._build_ring_3(task, loaded_tools=loaded_tools))

        # Phase 3.5: Context budget enforcement
        # MF-5: ContextPressureMonitor is the AUTHORITY for compression stage.
        # PromptComposer._determine_compression_stage() remains as the FALLBACK
        # when no ContextPressureMonitor is available.
        # When ContextPressureMonitor is present, use its compression stage
        # instead of computing our own.
        context_snapshot = None  # IFM-N52: will be set on ComposedPrompt
        if context_pressure_monitor is not None:
            ring_0_tokens = sum(
                s.token_estimate for s in sections
                if s.ring == PromptRing.RING_0
            )
            system_tokens = sum(
                s.token_estimate for s in sections
                if s.ring in (PromptRing.RING_0, PromptRing.RING_1)
            )
            tool_tokens = sum(
                s.token_estimate for s in sections
                if s.name == "tool_definitions"
            )
            task_tokens = sum(
                s.token_estimate for s in sections
                if s.name == "task_context"
            )
            history_tokens = 0  # Conversation history managed externally
            reserve_tokens = int(max_tokens * allocation.reserve_pct)

            context_snapshot = context_pressure_monitor.compute_snapshot(
                system_tokens=system_tokens,
                tool_tokens=tool_tokens,
                task_tokens=task_tokens,
                history_tokens=history_tokens,
                reserve_tokens=reserve_tokens,
                ring_0_tokens=ring_0_tokens,
                max_context_tokens=max_tokens,
            )

            # MF-5: ContextPressureMonitor is the AUTHORITY — override
            # the locally-computed compression stage with the authoritative one
            stage = context_snapshot.compression_stage
        # else:
        #   MF-5 FALLBACK: No ContextPressureMonitor available.
        #   PromptComposer._determine_compression_stage() already computed
        #   `stage` above — use it as-is.
```

Add `TYPE_CHECKING` imports in `prompt_composer.py` for the new typed parameters (MF-3):

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine.context_pressure_monitor import ContextPressureMonitor
    from ..models.tool import ToolDefinition
```

The full updated `compose()` signature adds these parameters:

```python
    def compose(
        self,
        role: RoleComposition,
        task: Task,
        domain: DomainConfig,
        capabilities: dict[str, CapabilityAtom],
        voice_atoms: dict[str, VoiceAtom],
        max_tokens: int = 200_000,
        allocation: ContextBudgetAllocation | None = None,
        budget_summary: dict | None = None,
        cache_manager: CacheManager | None = None,
        loaded_tools: list[ToolDefinition] | None = None,  # Phase 3.5 (MF-3)
        context_pressure_monitor: ContextPressureMonitor | None = None,  # Phase 3.5 (MF-3)
    ) -> ComposedPrompt:
```

**Phase 3.5: Add `context_snapshot` field to `ComposedPrompt`** (IFM-N52 fix):

```python
class ComposedPrompt(FrameworkModel):
    """The fully assembled agent prompt with metadata."""

    sections: list[PromptSection]
    total_tokens: int
    compression_stage: CompressionStage
    voice_profile: VoiceProfile
    tools_loaded: list[str]
    dropped_sections: list[str]  # Names of sections removed by compression
    context_snapshot: ContextSnapshot | None = None  # Phase 3.5: IFM-N52 fix
```

Add `TYPE_CHECKING` import in `prompt_composer.py`:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.context import ContextSnapshot
```

And the return value is updated to include tool names and context snapshot:

```python
        return ComposedPrompt(
            sections=sections,
            total_tokens=final_total,
            compression_stage=stage,
            voice_profile=voice_profile,
            tools_loaded=[t.name for t in (loaded_tools or [])],  # Phase 3.5
            dropped_sections=dropped,
            context_snapshot=context_snapshot if context_pressure_monitor is not None else None,  # IFM-N52
        )
```

### 8.2 Changes to `engine/skill_library.py`

#### 8.2.0 Add QUARANTINED status and QUARANTINE action (MF-4/SF-5)

Add `QUARANTINED` to `SkillStatus` enum in `models/skill.py`:

```python
class SkillStatus(StrEnum):
    """Lifecycle states for a skill record.

    Flow: candidate -> validating -> stage_X_passed -> validated -> active
    Failure: candidate -> validating -> rejected
    Degradation: active -> deprecated
    Security: active -> quarantined  (MF-4: Phase 3.5)
    """

    CANDIDATE = "candidate"
    VALIDATING = "validating"
    STAGE_1_PASSED = "stage_1_passed"
    STAGE_2_PASSED = "stage_2_passed"
    STAGE_3_PASSED = "stage_3_passed"
    VALIDATED = "validated"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    QUARANTINED = "quarantined"  # MF-4: Security scan flagged, pending review
```

Add `QUARANTINE` to `SkillMaintenanceAction` enum:

```python
class SkillMaintenanceAction(StrEnum):
    """Actions taken during periodic maintenance (Section 12.4)."""

    PRUNE = "prune"
    MERGE = "merge"
    PROMOTE = "promote"
    DEMOTE = "demote"
    QUARANTINE = "quarantine"  # MF-4: Security scan quarantine
```

#### 8.2.1 Add security scanning

Add method to `SkillLibrary`:

```python
    def run_security_scan(
        self,
        execute_fn: object | None = None,
    ) -> SecurityScanResult:
        """Scan Ring 3 skills for security vulnerability patterns.

        Checks instruction_fragment of all active Ring 3 skills against
        known vulnerability patterns from core/tool-taxonomy.yaml.
        Flagged skills are quarantined immediately (status -> QUARANTINED).

        Called at maintenance frequency (every maintenance_interval_tasks tasks).

        Args:
            execute_fn: Optional ModelExecuteFn for LLM-assisted scanning
                (Phase 4+). Phase 3.5 uses pattern matching only.

        Returns:
            SecurityScanResult with scan details.

        SoK Agent Skills (arXiv:2602.20867): 26.1% vulnerability rate.
        """
        from ..models.reconfiguration import SecurityScanResult
        from ..models.base import generate_id

        now = datetime.now(timezone.utc)

        # Load vulnerability patterns
        config_raw = self.yaml_store.read_raw("core/tool-taxonomy.yaml")
        tt = config_raw.get("tool_taxonomy", {})
        security = tt.get("security", {})
        patterns = security.get("vulnerability_patterns", [])
        quarantine_critical = bool(security.get("quarantine_on_critical", True))
        quarantine_high = bool(security.get("quarantine_on_high", True))

        # Get all active Ring 3 skills
        active_skills = self.get_active_skills()
        ring_3_skills = [
            s for s in active_skills
            if s.ring == ProtectionRing.RING_3_EXPENDABLE.value
        ]

        scan_details: list[dict[str, str]] = []
        quarantined: list[str] = []

        import re  # SF-8: word boundary matching

        for skill in ring_3_skills:
            fragment_lower = skill.instruction_fragment.lower()
            for pat in patterns:
                pattern_text = pat.get("pattern", "").lower()
                severity = pat.get("severity", "low")
                # SF-8: Use word boundary regex to avoid false positives
                # (e.g., "evaluation" should not match "eval(")
                if pattern_text and re.search(
                    r'\b' + re.escape(pattern_text) + r'\b', fragment_lower
                ):
                    detail = {
                        "skill_name": skill.name,
                        "pattern": pat.get("pattern", ""),
                        "severity": severity,
                        "description": pat.get("description", ""),
                    }
                    scan_details.append(detail)

                    should_quarantine = (
                        (severity == "critical" and quarantine_critical)
                        or (severity == "high" and quarantine_high)
                    )
                    if should_quarantine and skill.name not in quarantined:
                        skill.status = SkillStatus.QUARANTINED  # MF-4
                        skill.updated_at = now
                        self._persist_skill(skill)
                        quarantined.append(skill.name)
                        logger.warning(
                            f"Skill '{skill.name}' QUARANTINED: "
                            f"vulnerability pattern '{pat.get('pattern', '')}' "
                            f"(severity: {severity})"
                        )

        result = SecurityScanResult(
            id=generate_id("scan"),
            created_at=now,
            skills_scanned=len(ring_3_skills),
            vulnerabilities_found=len(scan_details),
            quarantined_skills=quarantined,
            scan_details=scan_details,
        )

        # Persist scan result
        self.yaml_store.ensure_dir(f"{self._skills_dir}/security-scans")
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        unique_suffix = result.id.split("-")[-1]
        self.yaml_store.write(
            f"{self._skills_dir}/security-scans/{timestamp_str}_{unique_suffix}.yaml",
            result,
        )

        logger.info(
            f"Security scan complete: {len(ring_3_skills)} Ring 3 skills scanned, "
            f"{len(scan_details)} vulnerabilities found, "
            f"{len(quarantined)} quarantined"
        )

        return result
```

#### 8.2.2 Add last-in-category protection

Modify `_prune_skills()` to check for last-in-category:

**Before** (in `_prune_skills`, the pruning loop):

```python
            if reason:
                skill.status = SkillStatus.DEPRECATED
                skill.updated_at = datetime.now(timezone.utc)
                self._persist_skill(skill)
```

**After** (with last-in-category protection):

```python
            if reason:
                # Phase 3.5: Last-in-category protection
                # NEVER prune the last skill that covers a particular task type
                if self._is_last_in_category(skill, skills):
                    logger.info(
                        f"Skipping prune of '{skill.name}': last in category "
                        f"(domain={skill.domain})"
                    )
                    continue

                skill.status = SkillStatus.DEPRECATED
                skill.updated_at = datetime.now(timezone.utc)
                self._persist_skill(skill)
```

Add the helper method:

```python
    def _is_last_in_category(
        self,
        skill: SkillRecord,
        all_active: list[SkillRecord],
    ) -> bool:
        """Check if this is the last active skill in its category.

        A "category" is determined by the skill's source task_type.
        If this is the only active skill from that task_type, pruning
        it would eliminate coverage for that category.

        Phase 3.5 addition: Prevents capability collapse from aggressive pruning.

        Args:
            skill: The skill being considered for pruning.
            all_active: All currently active skills.

        Returns:
            True if this is the last skill in its category.
        """
        category = skill.source.task_type
        same_category = [
            s for s in all_active
            if s.source.task_type == category
            and s.name != skill.name
            and s.is_active
        ]
        return len(same_category) == 0
```

#### 8.2.3 Add security scan scheduling to maintenance (IFM-N63)

Modify `run_maintenance()` to include security scanning. The security scan
step is placed AFTER Step 5 (demote underperforming) but BEFORE the persist
loop. This is the COMPLETE modified `run_maintenance()` body showing the
insertion point:

```python
    def run_maintenance(self) -> list[MaintenanceRecord]:
        """Run periodic skill maintenance (Section 12.4).

        Steps 1-5 are existing Phase 3 maintenance.
        Step 6 (Phase 3.5): Security scan of Ring 3 skills.
        """
        records: list[MaintenanceRecord] = []
        skills = self.get_active_skills()

        # Step 1: Prune stale/low-performing skills
        prune_records = self._prune_skills(skills)
        records.extend(prune_records)

        # Step 2: Merge near-duplicates
        merge_records = self._merge_skills(skills)
        records.extend(merge_records)

        # Step 3: Promote high-performing Ring 3 -> Ring 2
        promote_records = self._promote_skills(skills)
        records.extend(promote_records)

        # Step 4: Demote underperforming Ring 2 -> Ring 3
        demote_records = self._demote_skills(skills)
        records.extend(demote_records)

        # Step 5: (existing Phase 3 step — varies by implementation)

        # ---- Phase 3.5 insertion point (IFM-N63) ----
        # Step 6 (Phase 3.5): Security scan of Ring 3 skills
        # Placed AFTER demote (Step 5) and BEFORE the persist/trim loop.
        scan_result = self.run_security_scan()
        if scan_result.quarantined_skills:
            for quarantined_name in scan_result.quarantined_skills:
                record = MaintenanceRecord(
                    id=generate_id("maint"),
                    created_at=datetime.now(timezone.utc),
                    action=SkillMaintenanceAction.QUARANTINE,  # MF-4
                    skill_name=quarantined_name,
                    detail=(
                        f"Security scan quarantine: "
                        f"{scan_result.vulnerabilities_found} vulnerabilities"
                    ),
                    composite_score=0.0,
                    success_rate=0.0,
                    usage_count=0,
                )
                records.append(record)
        # ---- End Phase 3.5 insertion ----

        # Trim maintenance history
        self._trim_maintenance_history()

        # Reset task counter
        self._tasks_since_maintenance = 0

        logger.info(
            f"Maintenance complete: {len(records)} actions taken "
            f"({len(prune_records)} pruned, {len(merge_records)} merged, "
            f"{len(promote_records)} promoted, {len(demote_records)} demoted, "
            f"{len(scan_result.quarantined_skills)} quarantined)"
        )

        return records
```

### 8.3 Changes to `engine/orchestrator.py` (IFM-N51 CRITICAL FIX)

**IFM-N51:** The orchestrator integration code previously referenced `self.constitution_path`,
`self.prompt_composer`, `self.cache_manager`, `self.skill_library` -- none of which exist in
the actual `Orchestrator.__init__`. This fix shows the FULL updated constructor.

#### 8.3.1 Updated Orchestrator constructor

The current `Orchestrator.__init__` accepts: `yaml_store`, `topology_router`, `team_manager`,
`task_lifecycle`, `review_engine`, `audit_logger`, `budget_tracker`, `rate_limiter`, `cost_gate`,
`capability_tracker`. Phase 3.5 adds 8 new optional parameters.

Add `TYPE_CHECKING` imports:

```python
if TYPE_CHECKING:
    from .budget_tracker import BudgetTracker
    from .capability_tracker import CapabilityTracker
    from .context_pressure_monitor import ContextPressureMonitor
    from .cost_gate import CostGate
    from .diversity_engine import DiversityEngine
    from .prompt_composer import PromptComposer
    from .rate_limiter import RateLimiter
    from .ring_enforcer import RingEnforcer
    from .self_reconfigurer import SelfReconfigurer
    from .skill_library import SkillLibrary
    from .stagnation_detector import StagnationDetector
    from .tool_loader import ToolLoader
    from ..engine.cache_manager import CacheManager
```

The FULL updated `__init__` constructor:

```python
    def __init__(
        self,
        yaml_store: YamlStore,
        topology_router: TopologyRouter,
        team_manager: TeamManager,
        task_lifecycle: TaskLifecycle,
        review_engine: ReviewEngine,
        audit_logger: AuditLogger | None = None,
        budget_tracker: BudgetTracker | None = None,
        rate_limiter: RateLimiter | None = None,
        cost_gate: CostGate | None = None,
        capability_tracker: CapabilityTracker | None = None,
        # Phase 3.5 (IFM-N51): All optional, stored as self._X attributes
        constitution_path: Path | None = None,
        prompt_composer: PromptComposer | None = None,
        cache_manager: CacheManager | None = None,
        skill_library: SkillLibrary | None = None,
        context_pressure_monitor: ContextPressureMonitor | None = None,
        tool_loader: ToolLoader | None = None,
        ring_enforcer: RingEnforcer | None = None,
        self_reconfigurer: SelfReconfigurer | None = None,
    ):
        self.yaml_store = yaml_store
        self.topology_router = topology_router
        self.team_manager = team_manager
        self.task_lifecycle = task_lifecycle
        self.review_engine = review_engine
        self.audit_logger = audit_logger
        self.budget_tracker = budget_tracker
        self.rate_limiter = rate_limiter
        self.cost_gate = cost_gate
        self.diversity_engine: DiversityEngine | None = None
        self.stagnation_detector: StagnationDetector | None = None
        self.capability_tracker = capability_tracker

        # Phase 3.5 (IFM-N51): Optional components stored with underscore prefix
        self._constitution_path = constitution_path
        self._prompt_composer = prompt_composer
        self._cache_manager = cache_manager
        self._skill_library = skill_library
        self._context_pressure_monitor = context_pressure_monitor
        self._tool_loader = tool_loader
        self._ring_enforcer = ring_enforcer
        self._self_reconfigurer = self_reconfigurer

        # Phase 3.5: Verify Ring 0 integrity at boot (if enforcer provided)
        if self._ring_enforcer is not None:
            self._ring_enforcer.verify_ring_0_integrity()
```

Add `Path` import at the top of orchestrator.py:

```python
from pathlib import Path
```

#### 8.3.2 Integration code with None-checks

In the task execution flow, integrate tool loading and context pressure.
All integration code checks `if self._X is not None:` before use:

```python
    # In the task execution method, before prompt composition:

    # Phase 3.5: Load tools for this step (if ToolLoader available)
    tool_result = None
    loaded_tools = None
    if self._tool_loader is not None:
        tool_result = self._tool_loader.load_for_step(
            task_type=task_type,
            step_goal=task.title,
            max_context_tokens=max_tokens,
        )
        loaded_tools = tool_result.loaded_tools

    # Phase 3.5: Compose prompt with loaded tools (if PromptComposer available)
    if self._prompt_composer is not None:
        composed = self._prompt_composer.compose(
            role=role,
            task=task,
            domain=domain_config,
            capabilities=capabilities,
            voice_atoms=voice_atoms,
            max_tokens=max_tokens,
            allocation=allocation,
            budget_summary=budget_summary,
            cache_manager=self._cache_manager,
            loaded_tools=loaded_tools,
            context_pressure_monitor=self._context_pressure_monitor,
        )
```

After evolution cycles, verify Ring 0 was not modified:

```python
    # After evolution cycle completes:

    # Phase 3.5: Verify Ring 0 integrity after evolution (if enforcer available)
    if self._ring_enforcer is not None:
        self._ring_enforcer.verify_ring_0_integrity()
```

---

## Part 9: Implementation Sequence

### 9.1 Dependency Graph

```
Step 0: YAML configs (core/context-pressure.yaml, core/tool-taxonomy.yaml)
  |
  |---> Step 1: models/tool.py (tool data models)
  |       |
  |       |---> Step 4: engine/tool_loader.py (depends on models/tool,
  |       |                                     diversity_engine)
  |       |
  |       \---> Step 7: engine/prompt_composer.py (modifications,
  |                                                depends on Step 4)
  |
  |---> Step 2: models/reconfiguration.py (reconfiguration data models)
  |       |
  |       |---> Step 5: engine/ring_enforcer.py (depends on models/reconfiguration)
  |       |
  |       \---> Step 6: engine/self_reconfigurer.py (depends on models/reconfiguration)
  |
  |---> Step 3: engine/context_pressure_monitor.py (depends on models/context,
  |                                                  models/reconfiguration)
  |
  |---> Step 8: engine/skill_library.py (modifications: security scan,
  |                                       last-in-category, quarantine)
  |
  |---> Step 9: engine/orchestrator.py (integration, depends on Steps 3-8)
  |
  \---> Step 10: Full regression
```

### 9.2 Step-by-Step Implementation

**Step 0: YAML Configuration Files**

Files to create:
- `core/context-pressure.yaml` (from Part 3.1)
- `core/tool-taxonomy.yaml` (from Part 3.2)

Verification:
```bash
uv run python -c "
import yaml
with open('core/context-pressure.yaml') as f:
    data = yaml.safe_load(f)
assert 'context_pressure' in data
assert data['context_pressure']['ring_0']['reserved_tokens'] == 2000
assert data['context_pressure']['thresholds']['overflow'] == 0.95
print('context-pressure.yaml: OK')

with open('core/tool-taxonomy.yaml') as f:
    data = yaml.safe_load(f)
assert 'tool_taxonomy' in data
assert data['tool_taxonomy']['loading']['max_tools_per_step'] == 5
assert data['tool_taxonomy']['loading']['max_mcp_servers'] == 3
print('tool-taxonomy.yaml: OK')
"
```

Gate: Both YAML files load and validate.

**Step 1: Tool Data Models (`models/tool.py`)**

Files to create:
- `src/uagents/models/tool.py` (from Part 2.1)

Tests to run:
```bash
uv run pytest tests/test_models/test_tool.py -v
```

Gate: All tool models instantiate. `ToolDefinition` validates token_cost >= 0. `McpServerRecord.is_active` and `.utilization` properties return correct values. `ToolCategory` and `McpServerState` enums have correct values. `FrameworkModel` strict mode enforced.

**Step 2: Reconfiguration Data Models (`models/reconfiguration.py`)**

Files to create:
- `src/uagents/models/reconfiguration.py` (from Part 2.2)

Tests to run:
```bash
uv run pytest tests/test_models/test_reconfiguration.py -v
```

Gate: All reconfiguration models instantiate. `ReconfigurationAction` enum correct. `ContextPressureConfig` defaults match spec. `SecurityScanResult` and `RingEnforcementEvent` extend `IdentifiableModel`. Budget delta field accepts negative values.

**Step 3: ContextPressureMonitor Engine**

Files to create:
- `src/uagents/engine/context_pressure_monitor.py` (from Part 4)

Tests to run:
```bash
uv run pytest tests/test_engine/test_context_pressure_monitor.py -v
```

Gate: `compute_snapshot()` returns correct pressure levels for all thresholds. `ContextHardFailError` raised when context insufficient for Ring 0. Compression stages determined correctly from utilization. `check_budget_allocation()` detects over-budget categories. `get_compression_actions()` returns correct actions for each stage. `get_pressure_trend()` detects increasing/decreasing/stable. Config loads from YAML.

**Step 4: ToolLoader Engine**

Files to create:
- `src/uagents/engine/tool_loader.py` (from Part 5)

Tests to run:
```bash
uv run pytest tests/test_engine/test_tool_loader.py -v
```

Gate: Core tools always included. Semantic search returns relevant tools. Token budget enforced. MCP server concurrency cap enforced. `ToolBudgetExceededError` raised when core tools exceed budget. `unload_tool()` protects Ring 0-1. `check_mcp_idle_timeouts()` detects idle servers. Task type hints used as fallback. `get_tool_token_cost()` sums correctly.

**Step 5: RingEnforcer Engine**

Files to create:
- `src/uagents/engine/ring_enforcer.py` (from Part 6)

Tests to run:
```bash
uv run pytest tests/test_engine/test_ring_enforcer.py -v
```

Gate: First-run baseline hashes computed and stored. Hash mismatch raises `RingViolationError`. Missing Ring 0 file raises `RingViolationError`. `authorize_transition()` validates all transition rules. Ring 0 transitions always denied. Ring 3->2 auto-approved with evidence. Ring 2->1 requires human approval. `can_prune()`, `can_compress()`, `can_disable()` enforce ring hierarchy. `verify_no_ring_0_modification()` detects modifications. `update_ring_0_hashes()` updates registry after human authorization.

**Step 6: SelfReconfigurer Engine**

Files to create:
- `src/uagents/engine/self_reconfigurer.py` (from Part 7)

Tests to run:
```bash
uv run pytest tests/test_engine/test_self_reconfigurer.py -v
```

Gate: Rationale required for all requests. Budget delta capped at +/-30%. Cumulative budget delta tracked per agent. Ring 0-1 tool unload denied. Ring 0 compression denied. Strategy switch always approved. Context expand always approved. All reconfigurations logged to state. `reset_session()` clears cumulative deltas.

**Step 7: PromptComposer Modifications**

Files to modify:
- `src/uagents/engine/prompt_composer.py` (from Part 8.1)

Tests to run:
```bash
uv run pytest tests/test_engine/test_prompt_composer.py -v
```

Gate: Tool definitions injected in Ring 3. Tool sections have lower priority than task context. `compose()` accepts `loaded_tools` and `context_pressure_monitor` parameters. `tools_loaded` populated in `ComposedPrompt`. Existing tests still pass.

**Step 8: SkillLibrary Modifications**

Files to modify:
- `src/uagents/engine/skill_library.py` (from Part 8.2)

Tests to run:
```bash
uv run pytest tests/test_engine/test_skill_library.py -v
```

Gate: `run_security_scan()` detects vulnerability patterns. Flagged skills quarantined (status QUARANTINED, MF-4). Scan results persisted. Last-in-category protection prevents pruning last skill of a type. Security scan integrated into maintenance. Existing tests still pass.

**Step 9: Orchestrator Integration**

Files to modify:
- `src/uagents/engine/orchestrator.py` (from Part 8.3)

Tests to run:
```bash
uv run pytest tests/test_engine/test_orchestrator.py -v -k "phase35 or tool_load or ring_enforce or self_reconfig or context_pressure"
```

Gate: Orchestrator creates all Phase 3.5 components. Ring 0 verified at boot. Tool loading integrated into task execution. Context pressure snapshot computed after composition. Ring 0 verified after evolution.

**Step 10: Full Regression**

```bash
uv run pytest --tb=short -q
```

Gate: All existing tests pass. All new tests pass. No regressions.

### 9.3 Verification Checklist

| # | Check | Command |
|---|-------|---------|
| 1 | YAML configs load correctly | `uv run pytest tests/test_config/test_context_pressure.py tests/test_config/test_tool_taxonomy.py -v` |
| 2 | Tool models instantiate | `uv run pytest tests/test_models/test_tool.py -v` |
| 3 | Reconfiguration models instantiate | `uv run pytest tests/test_models/test_reconfiguration.py -v` |
| 4 | ContextPressureMonitor pressure levels | `uv run pytest tests/test_engine/test_context_pressure_monitor.py -v -k pressure_level` |
| 5 | ContextPressureMonitor HARD_FAIL | `uv run pytest tests/test_engine/test_context_pressure_monitor.py -v -k hard_fail` |
| 6 | ContextPressureMonitor compression stages | `uv run pytest tests/test_engine/test_context_pressure_monitor.py -v -k compression` |
| 7 | ContextPressureMonitor budget allocation check | `uv run pytest tests/test_engine/test_context_pressure_monitor.py -v -k budget` |
| 8 | ToolLoader core tools always loaded | `uv run pytest tests/test_engine/test_tool_loader.py -v -k core` |
| 9 | ToolLoader semantic search | `uv run pytest tests/test_engine/test_tool_loader.py -v -k semantic` |
| 10 | ToolLoader token budget enforcement | `uv run pytest tests/test_engine/test_tool_loader.py -v -k budget` |
| 11 | ToolLoader MCP concurrency cap | `uv run pytest tests/test_engine/test_tool_loader.py -v -k mcp` |
| 12 | ToolLoader idle timeout detection | `uv run pytest tests/test_engine/test_tool_loader.py -v -k idle` |
| 13 | ToolLoader Ring 0-1 unload protection | `uv run pytest tests/test_engine/test_tool_loader.py -v -k unload` |
| 14 | RingEnforcer hash verification | `uv run pytest tests/test_engine/test_ring_enforcer.py -v -k hash` |
| 15 | RingEnforcer Ring 0 violation detection | `uv run pytest tests/test_engine/test_ring_enforcer.py -v -k violation` |
| 16 | RingEnforcer transition authorization | `uv run pytest tests/test_engine/test_ring_enforcer.py -v -k transition` |
| 17 | RingEnforcer can_prune/compress/disable | `uv run pytest tests/test_engine/test_ring_enforcer.py -v -k can_` |
| 18 | SelfReconfigurer rationale required | `uv run pytest tests/test_engine/test_self_reconfigurer.py -v -k rationale` |
| 19 | SelfReconfigurer budget cap | `uv run pytest tests/test_engine/test_self_reconfigurer.py -v -k budget` |
| 20 | SelfReconfigurer cumulative delta | `uv run pytest tests/test_engine/test_self_reconfigurer.py -v -k cumulative` |
| 21 | SelfReconfigurer ring protection | `uv run pytest tests/test_engine/test_self_reconfigurer.py -v -k ring` |
| 22 | PromptComposer tool injection | `uv run pytest tests/test_engine/test_prompt_composer.py -v -k tool_inject` |
| 23 | SkillLibrary security scan | `uv run pytest tests/test_engine/test_skill_library.py -v -k security` |
| 24 | SkillLibrary last-in-category | `uv run pytest tests/test_engine/test_skill_library.py -v -k last_in_category` |
| 25 | SkillLibrary quarantine | `uv run pytest tests/test_engine/test_skill_library.py -v -k quarantine` |
| 26 | Orchestrator Phase 3.5 integration | `uv run pytest tests/test_engine/test_orchestrator.py -v -k phase35` |
| 27 | Ring 0 verification at boot | `uv run pytest tests/test_engine/test_orchestrator.py -v -k ring_boot` |
| 28 | End-to-end: load tools -> compose -> check pressure | `uv run pytest tests/test_engine/test_phase35_e2e.py -v` |
| 29 | Existing tests still pass | `uv run pytest --tb=short -q` |

---

## Part 10: Failure Modes

### 10.1 Context Pressure (FM-CP01 through FM-CP06)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-CP01 | Ring 0 content exceeds reserved_tokens (2000) — larger constitution file causes Ring 0 reservation to be insufficient | HIGH | Context Pressure | **MITIGATED:** `compute_snapshot()` uses actual `ring_0_tokens` from prompt composition (not estimated). If Ring 0 content grows beyond 2000 tokens, the snapshot correctly reflects the actual usage. `ContextHardFailError` raised only when remaining context < `min_productive_tokens` (1000), providing a buffer. Configuration is adjustable in context-pressure.yaml. |
| FM-CP02 | Compression cascade drops critical task context — Stage 3 task-aware pruning removes information needed for the current step | HIGH | Context Pressure | **MITIGATED:** PromptSection priority system ensures task_context (priority=0.8) is dropped after lower-priority sections (tool_definitions at 0.4, voice at 0.5, behavioral at 0.6). Ring 0 content is never compressed (compressible=False). Only Ring 3 content is dropped in Stage 2-3. |
| FM-CP03 | HARD_FAIL triggered incorrectly — token estimation error causes false positive overflow | MEDIUM | Context Pressure | **MITIGATED:** Token estimation uses the same `estimate_tokens()` function as PromptComposer (3.5 chars/token). False positive HARD_FAIL is conservative — better to halt than to run with compromised Ring 0. `min_productive_tokens` (1000) provides margin. Human can increase context window or reduce constitution size. |
| FM-CP04 | Snapshot history grows unbounded — `_snapshot_history` list accumulates without limit | LOW | Context Pressure | **MITIGATED:** `_max_history` cap (50 entries). List trimmed on every `compute_snapshot()` call. Snapshots are in-memory only (not persisted), so memory impact is negligible. |
| FM-CP05 | Compression stage determination uses stale thresholds — YAML config changed but ContextPressureMonitor not reloaded | LOW | Context Pressure | **ACCEPTED:** Config is loaded once at initialization. Framework restart is required for config changes. This is consistent with all other components (SkillLibrary, BudgetTracker, etc.). |
| FM-CP06 | Budget allocation check returns false negatives — categories report "within budget" but total exceeds context window due to rounding | MEDIUM | Context Pressure | **MITIGATED:** Individual category checks are supplementary to the overall utilization check. `compute_snapshot()` always uses actual totals, not per-category estimates. Rounding errors are at most a few tokens, well within the 10% reserve buffer. |

### 10.2 Tool Loading (FM-TL01 through FM-TL08)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-TL01 | Core tools alone exceed tool token budget — too many Ring 0-1 tools defined | HIGH | Tool Loading | **MITIGATED:** `load_for_step()` raises `ToolBudgetExceededError` if core tools exceed budget. This is a configuration error that must be resolved by reducing core tool count or increasing budget. The error message includes specific token counts. |
| FM-TL02 | Semantic search returns irrelevant tools — TF-IDF tokenization too naive for tool descriptions | MEDIUM | Tool Loading | **MITIGATED:** Uses same tokenizer as SkillLibrary (regex word boundary split). Task type hints provide fallback when semantic search is insufficient. Tool tags improve TF-IDF relevance. `max_tools_per_step` (5) limits blast radius of poor selections. |
| FM-TL03 | MCP server start fails — external MCP process cannot be launched | HIGH | Tool Loading | **MITIGATED:** `_ensure_mcp_server()` returns (False, reason) on failure. Tools requiring the failed MCP server are added to rejected_tools with reason. Agent proceeds with available tools. MCP server state tracked in `McpServerRecord`. |
| FM-TL04 | MCP server concurrency cap reached — agent needs tool from a 4th MCP server | MEDIUM | Tool Loading | **MITIGATED:** `_ensure_mcp_server()` checks `get_active_mcp_count()` against cap. Returns (False, "concurrency_cap: ...") when exceeded. Tool is rejected with clear reason. `check_mcp_idle_timeouts()` provides a way to free up slots. |
| FM-TL05 | MCP idle timeout unloads needed server — server unloaded during active but infrequent use | MEDIUM | Tool Loading | **MITIGATED:** `check_mcp_idle_timeouts()` returns suggestions, does not auto-unload. Caller decides whether to act. Ring 1 servers are exempt from idle timeout. Timeout is configurable (default 10 minutes). `record_mcp_query()` updates `last_query_at`. |
| FM-TL06 | Tool taxonomy YAML has malformed entries — missing required fields in tool definitions | HIGH | Tool Loading | **MITIGATED:** `ToolDefinition` is a FrameworkModel with strict validation. Missing required fields (name, description, instruction_fragment, category, ring, token_cost) cause validation errors during `__init__()`. Error message identifies the malformed entry. |
| FM-TL07 | Tool token cost underestimated — actual tool definition generates more tokens than `token_cost` field | MEDIUM | Tool Loading | **MITIGATED:** `token_cost` is an estimate used for budget planning. Actual tokens are computed by `estimate_tokens()` on the rendered content in PromptComposer. Budget enforcement in ContextPressureMonitor uses actual tokens from composed prompt, not estimates. |
| FM-TL08 | Two agents load conflicting tools simultaneously — race condition in MCP server state | LOW | Tool Loading | **MITIGATED:** MCP server state is per-ToolLoader instance. In Phase 3.5, each orchestrator has its own ToolLoader. Multi-agent MCP coordination is Phase 4+ scope. |

### 10.3 Ring Enforcement (FM-RE01 through FM-RE06)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-RE01 | Ring 0 file silently modified between boot and first evolution check — modification window exists | HIGH | Ring Integrity | **MITIGATED:** Hash verification runs at boot AND after every evolution cycle. No programmatic path modifies Ring 0 files. External modification (human edit) is detected on next verification. Recovery runbook provides git-based restoration. |
| FM-RE02 | Hash registry corrupted — stored hashes invalid, causing false positive violations | MEDIUM | Ring Integrity | **MITIGATED:** Hash registry is YAML persisted via `YamlStore` (atomic writes). If registry is unreadable, `_load_hash_registry()` returns empty dict, triggering baseline re-computation. False violation is impossible on first run (no comparison). |
| FM-RE03 | Ring 0 file list incomplete — new Ring 0 file not added to `_ring_0_files` | MEDIUM | Ring Integrity | **MITIGATED:** `_ring_0_files` is initialized in `__init__()` from constitution_path. Additional Ring 0 files (canary expectations, recovery runbook) should be added by the implementer. Missing files are a configuration gap, not a runtime failure. |
| FM-RE04 | `authorize_transition()` allows invalid promotion — Ring 3 skill promoted to Ring 2 without sufficient evidence | MEDIUM | Ring Integrity | **MITIGATED:** `authorize_transition()` requires non-empty `evidence` for Ring 3->2 promotion. The actual evidence quality is validated by SkillLibrary's `_meets_promotion_criteria()` which checks usage count, success rate, and validation stages. RingEnforcer is a gatekeeper, not the sole validator. |
| FM-RE05 | Recovery runbook references git operations that fail — repository state prevents git checkout | HIGH | Ring Integrity | **MITIGATED:** Recovery runbook is a reference, not auto-executed. Human must manually execute git commands. The runbook includes verification steps (re-verify hashes, run canary suite) after restoration. If git fails, human must investigate manually (final step 10 of runbook). |
| FM-RE06 | `verify_no_ring_0_modification()` receives incomplete file list — evolution cycle modifies Ring 0 file but does not report it | HIGH | Ring Integrity | **MITIGATED:** This is a defense-in-depth measure. Even if the file list is incomplete, `verify_ring_0_integrity()` runs after evolution and detects the hash mismatch. Two independent verification paths reduce the chance of undetected modification. |

### 10.4 Self-Reconfiguration (FM-SR01 through FM-SR06)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-SR01 | Cumulative budget delta bypassed — agent restarts session to reset cumulative tracker | MEDIUM | Self-Reconfiguration | **MITIGATED:** `_cumulative_budget_deltas` is per-session by design. Each session starts fresh. Weekly budget limits (from BudgetTracker) provide the cross-session constraint. Session-level cumulative cap prevents rapid budget manipulation within a single session. |
| FM-SR02 | Rapid reconfiguration churn — agent repeatedly loads/unloads tools in a loop | MEDIUM | Self-Reconfiguration | **MITIGATED:** Each reconfiguration is logged to audit trail. Pattern detection in audit logs can identify churn (Phase 4+ scope). Tool load/unload is O(1) and has no side effects beyond audit logging. Token cost of reconfiguration is minimal. |
| FM-SR03 | Ring parameter spoofed in request — agent claims tool is Ring 3 when it is Ring 1 to bypass unload protection | HIGH | Self-Reconfiguration | **FIXED (MF-1):** `_validate_tool_unload()` now validates against ToolLoader's `_all_tools` registry (authoritative), not request parameters (untrusted). ToolLoader injected via `__init__` and passed to `_validate_tool_unload()`. See Part 7.1 code. |
| FM-SR04 | Reconfiguration audit logging fails — audit_logger raises exception, reconfiguration proceeds without audit | MEDIUM | Self-Reconfiguration | **MITIGATED:** `_log_reconfiguration()` wraps `audit_logger.log_decision()` in try/except. State persistence (YAML write) is always attempted. If YAML write also fails, the reconfiguration is still logged to Python logger (stderr). |
| FM-SR05 | Strategy switch has no effect — SelfReconfigurer approves but no component reads the strategy | LOW | Self-Reconfiguration | **ACCEPTED:** Phase 3.5 validates and logs strategy switches. The actual strategy engine that acts on these switches is Phase 4+ scope. The audit trail preserves the agent's intent for future implementation. |
| FM-SR06 | Budget reallocation approved but not enforced — BudgetTracker does not receive the delta | MEDIUM | Self-Reconfiguration | **MITIGATED:** SelfReconfigurer returns `ReconfigurationResult` to the caller. The orchestrator is responsible for passing approved budget changes to BudgetTracker. The approval/execution separation ensures changes are validated before being applied. |

### 10.5 Skill Security (FM-SS01 through FM-SS05)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-SS01 | Vulnerability pattern bypassed — obfuscated injection not caught by string matching | HIGH | Security | **MITIGATED:** Pattern matching is a first-pass filter, not the sole defense. Phase 4+ adds LLM-assisted security analysis via `execute_fn`. Ring 3 skills are sandboxed (injected AFTER constitution). Stage 4 human review is the final gate. The 26.1% vulnerability rate (SoK) justifies multi-layer defense. |
| FM-SS02 | False positive quarantine — legitimate skill flagged and quarantined | MEDIUM | Security | **MITIGATED:** Quarantined skills get status QUARANTINED (MF-4), not deleted. They can be restored by setting status back to ACTIVE and updating `updated_at`. Scan results are persisted for review. SF-8: Word boundary regex reduces false positives (e.g., "evaluation" no longer matches "eval("). |
| FM-SS03 | Security scan timing gap — vulnerability introduced between scan intervals | MEDIUM | Security | **MITIGATED:** Scan interval is configurable (default 20 tasks). New skills enter as Ring 3 (lowest trust). Skills are always injected after constitution (positional safety). The gap between scans is bounded by task frequency. |
| FM-SS04 | Last-in-category protection prevents quarantine of vulnerable skill — only skill in category has vulnerability | HIGH | Security | **MITIGATED:** Security scan runs BEFORE last-in-category check in the pruning flow. `run_security_scan()` is a separate method that does not check last-in-category. Security quarantine takes priority over category coverage. The skill is quarantined regardless. |
| FM-SS05 | Quarantined skill still in prompt cache — CacheManager serves stale prompt containing quarantined skill | MEDIUM | Security | **MITIGATED:** CacheManager caches Ring 0-1 content only. Ring 3 skill content is in Ring 2-3 sections which are not cached. Cache invalidation on constitution change further ensures safety. Quarantined skills are removed from `get_active_skills()` results, so they are not injected. |

### 10.6 Integration (FM-INT01 through FM-INT05)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-INT01 | PromptComposer changes break existing tests — new parameters to `compose()` and `_build_ring_3()` affect existing callers | HIGH | Integration | **MITIGATED:** All new parameters have default values (None). Existing callers continue to work unchanged. `loaded_tools=None` means no tool injection. `context_pressure_monitor=None` means no snapshot computation. Backward compatible by design. |
| FM-INT02 | SkillLibrary modifications break existing maintenance flow — new security scan step interacts with existing prune/merge/promote | MEDIUM | Integration | **MITIGATED:** Security scan is added AFTER existing steps (Step 6). Existing steps 1-5 are unchanged. Quarantined skills are deprecated (same status as pruned skills), so they are handled consistently by existing code paths. |
| FM-INT03 | Orchestrator initialization order matters — Phase 3.5 components depend on Phase 0-3 components being initialized first | HIGH | Integration | **MITIGATED:** Phase 3.5 initialization code is added AFTER Phase 3 initialization in `__init__()`. All dependencies (YamlStore, constitution_path, AuditLogger) are already initialized. Ring 0 verification is the last initialization step. |
| FM-INT04 | `diversity_engine` TF-IDF functions called with empty input — tokenize("") returns empty list, compute_idf([]) returns empty dict | LOW | Integration | **MITIGATED:** `_semantic_search()` returns early if no searchable tools. `tokenize()` handles empty strings (returns empty list). `compute_idf()` handles empty document list (returns empty dict). `cosine_distance()` handles empty vectors (returns 0.0). All edge cases covered. |
| FM-INT05 | `use_enum_values=True` causes comparison failures — ring values stored as int after YAML roundtrip, compared against enum members | HIGH | Integration | **MITIGATED:** All ring comparisons in Phase 3.5 code use `isinstance(ring_val, int)` checks and convert to int when needed. Pattern: `ring_int = ring_val if isinstance(ring_val, int) else int(ring_val)`. This handles both enum members (pre-roundtrip) and plain ints (post-roundtrip). |

### 10.7 Concurrency and State (FM-CS01 through FM-CS04)

| ID | Failure Mode | Severity | Category | Mitigation |
|----|-------------|----------|----------|------------|
| FM-CS01 | Ring enforcement event YAML write fails — disk full or permission error during enforcement logging | MEDIUM | State | **MITIGATED:** `_log_enforcement_event()` writes to state directory. Failure to persist is logged via Python logger. The enforcement action (raise RingViolationError) is not contingent on successful logging. |
| FM-CS02 | Hash registry concurrent write — two orchestrators verify Ring 0 simultaneously and both try to update registry | LOW | State | **MITIGATED:** `YamlStore.write_raw()` uses atomic temp-file + os.replace() with advisory file locking. Concurrent writes are serialized. Last writer wins, which is acceptable since hashes should be identical. |
| FM-CS03 | MCP server state inconsistent — `McpServerRecord` says RUNNING but actual server process died | MEDIUM | State | **MITIGATED:** `McpServerRecord.state` tracks intended state, not actual process state. Actual MCP server health is checked externally (by Claude Code). Failed tool calls are handled by PerformanceMonitor. Future: add health check ping. |
| FM-CS04 | Reconfiguration history grows unbounded — every reconfiguration persists a YAML file | LOW | State | **MITIGATED:** Reconfiguration files are small (<1KB). Growth rate is bounded by reconfiguration frequency (at most a few per task). Phase 4+ can add history trimming similar to SkillLibrary's `_trim_maintenance_history()`. |

### 10.8 Review-Discovered Implementation Failure Modes (IFM)

| ID | Description | Severity | Fix Applied | Status |
|----|-------------|----------|-------------|--------|
| IFM-N51 | Orchestrator has ZERO Phase 3.5 attributes | CRITICAL | Fix 1: Full `__init__` with 8 new optional params, None-checks | **FIXED** |
| IFM-N52 | `context_snapshot` computed in `compose()` is lost | CRITICAL | Fix 2: Added `context_snapshot` field to `ComposedPrompt` | **FIXED** |
| IFM-N53 | Triple-layer defaults mask YAML errors | HIGH | Fix 7: Direct dict access `["key"]` replaces `.get("key", default)` | **FIXED** |
| IFM-N54 | MCP servers never actually started | HIGH | Fix 8: Docstring clarifies intent-tracking; Phase 4+ scope | **DOCUMENTED** |
| IFM-N55 | Ring events pollute EVOLUTION audit stream | HIGH | Fix 9: Uses `EnvironmentLogEntry` + `log_environment()` | **FIXED** |
| IFM-N56 | FM-SR03-FIX not wired into SelfReconfigurer | HIGH | Fix 3: `tool_loader` param in `__init__`, passed to `_validate_tool_unload` | **FIXED** |
| IFM-N57 | `_validate_tool_load` approves all unconditionally | HIGH | Fix 10: Validates tool exists, not Ring 0-1, checks max_tools | **FIXED** |
| IFM-N59 | FM-SR03-FIX code block orphaned from main code | HIGH | Fix 3: Integrated into Part 7.1, removed orphan block | **FIXED** |
| IFM-N60 | `compose()` params typed as `object`/`list` | HIGH | Fix 4: `ToolDefinition`/`ContextPressureMonitor` types + TYPE_CHECKING | **FIXED** |
| IFM-N61 | Relative paths break on CWD change | MEDIUM | Fix 12: `Path(constitution_path).resolve()` in `RingEnforcer.__init__` | **FIXED** |
| IFM-N62 | All core tools get Ring 0 | HIGH | Fix 13: Category defaults to Ring 1, per-tool ring overrides | **FIXED** |
| IFM-N63 | Security scan insertion point ambiguous | MEDIUM | Fix 16: Complete `run_maintenance()` body shown | **FIXED** |
| IFM-N64 | Dead `scan_interval_tasks` config | MEDIUM | Fix 17: Removed from YAML, comment added | **FIXED** |
| IFM-N66 | `_validate_context_compress` allows Ring 1 full compression | MEDIUM | Fix 18: Only parameter compression allowed for Ring 1 | **FIXED** |
| IFM-N68 | `healthy_threshold` is dead code | HIGH | Fix 11: Removed from `ContextPressureConfig` and YAML | **FIXED** |
| MF-1 | FM-SR03-FIX not wired | HIGH | Fix 3: Same as IFM-N56 | **FIXED** |
| MF-3 | `compose()` params untyped | HIGH | Fix 4: Same as IFM-N60 | **FIXED** |
| MF-4 | No QUARANTINED status | HIGH | Fix 5: Added `SkillStatus.QUARANTINED` + `SkillMaintenanceAction.QUARANTINE` | **FIXED** |
| MF-5 | Dual compression stage determination | MEDIUM | Fix 6: CPM is authority, PromptComposer is fallback | **FIXED** |
| SF-1 | ToolLoader needs BudgetTracker | HIGH | Fix 14: `budget_tracker` param + `record_consumption()` call | **FIXED** |
| SF-3 | Ring 0 files incomplete | MEDIUM | Fix 19: `canary-expectations.yaml` added to Ring 0 list | **FIXED** |
| SF-5 | No QUARANTINED status | HIGH | Fix 5: Same as MF-4 | **FIXED** |
| SF-6 | Reconfiguration history has no trimming | LOW | Fix 20: `_trim_reconfiguration_history()` added | **FIXED** |
| SF-8 | Security patterns false-positive on "evaluation" | MEDIUM | Fix 15: Word boundary regex `\b` matching | **FIXED** |

### 10.9 Summary

| Severity | Count (Original) | Count (Review IFM) | Status |
|----------|------------------|-------------------|--------|
| CRITICAL | 0 | 2 (IFM-N51, IFM-N52) | **ALL FIXED** |
| HIGH | 14 | 13 (IFM-N53,N55,N56,N57,N59,N60,N62,N68,MF-1,MF-3,MF-4,SF-1,SF-5) | **ALL FIXED** |
| MEDIUM | 19 | 5 (IFM-N61,N63,N64,N66,MF-5,SF-3,SF-8) | **ALL FIXED** |
| LOW | 7 | 1 (SF-6) | **FIXED** |
| **Total** | **40** | **~20 unique** | All documented with mitigations or fixes applied |
