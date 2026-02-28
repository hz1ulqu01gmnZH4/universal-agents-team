# Universal Agents Framework — v0.2 Design Addendum

**Date:** 2026-02-27
**Status:** Addendum to v0.1 design — addressing 13 improvement items
**Companion research (pending):** creativity, skills crystallization, self-aware AI/bootstrapping

---

## Improvement Items Index

| # | Item | Type | Status |
|---|------|------|--------|
| 1 | Domain/task-specific constitutions (motto/rules) | Design | Addressed below |
| 2 | Creativity for agent teams/swarms | Research | Agent running |
| 3 | Skills as capability crystallization + LLM skills issues | Research | Agent running |
| 4 | Long-running autonomous capability | Design | Addressed below |
| 5 | Meta-analysis methodology for full self-audit | Design | Addressed below |
| 6 | Tree-like GUI viewer for audit | Design | Addressed below |
| 7 | Self-capability-aware improvement methodology | Research | Agent running |
| 8 | Taking over tasks from ai-lab-agents / ai-game-studio | Design | Addressed below |
| 9 | Domain switching via working subdirectory | Design | Addressed below |
| 10 | Role creation / adaptation via evolution | Design | Addressed below |
| 12 | Bootstrapping paradox resolution (dual-copy) | Research | Agent running |
| 13 | Self-risk awareness / self-governance | Research | Agent running |

---

## Item 1: Layered Constitution — Domain & Task-Level Rules

### Problem
The v0.1 design has a single global CONSTITUTION.md. But different domains need different mottos, principles, and rules. A research lab cares about reproducibility; a game studio cares about player experience; a meta domain cares about safe self-improvement.

### Design: Three-Layer Constitution

```
LAYER 0: GLOBAL CONSTITUTION (CONSTITUTION.md)
  │  Immutable axioms that apply everywhere.
  │  A1-A8 from v0.1 design.
  │  Human-only edits.
  │
  ├── LAYER 1: DOMAIN CHARTER (domain/{name}/CHARTER.md)
  │     Domain-specific principles, motto, values, quality standards.
  │     Applies to all tasks within this domain instance.
  │     Human-approved edits (Tier 1 evolution).
  │     Examples:
  │       - Research Lab: "Reproducibility above all. No result without p-value."
  │       - Game Studio: "Player experience is the final arbiter. Sakurai principles."
  │       - Meta: "Every change must make the framework more capable AND more auditable."
  │
  └── LAYER 2: TASK MANDATE (per-task, in task record)
        Task-specific constraints, success criteria, guiding principles.
        Set by orchestrator or human at task creation.
        Examples:
          - "This task is exploratory — breadth over depth"
          - "This task is safety-critical — double review required"
          - "Motto: Move fast but measure everything"
```

### Constitution Hierarchy

```yaml
# domain/research_lab/CHARTER.md
charter:
  name: "AI Research Lab"
  motto: "Reproducibility above all"

  principles:
    P1: "No experimental result without statistical significance test"
    P2: "Every hypothesis must be falsifiable"
    P3: "Literature review before experimentation"
    P4: "Negative results are results — publish them"

  quality_gates:
    - "Experiment must have documented protocol before execution"
    - "All code must be version-controlled and reproducible"
    - "Results must be reviewed by at least one agent not involved in execution"

  forbidden:
    - "Never p-hack or cherry-pick results"
    - "Never skip the literature review step"

  inherited_from: "../../CONSTITUTION.md"  # Global axioms always apply
```

```yaml
# Task-level mandate example
task:
  id: task-001
  mandate:
    motto: "Speed matters — this is a time-boxed exploration"
    constraints:
      - "Max 30 minutes total"
      - "Breadth over depth — survey 10 options, don't deep-dive on any"
    relaxed_rules:
      - "Single review sufficient (normally double for this complexity)"
    reason_for_relaxation: "Exploratory task — findings will be validated in follow-up"
```

### Enforcement

```
On every task:
  1. Load CONSTITUTION.md → global axioms
  2. Load domain CHARTER.md → domain principles
  3. Load task mandate → task-specific rules
  4. Merge: global > domain > task (global always wins conflicts)
  5. Pass merged rule set to all agents working on the task
  6. Reviewer checks against merged rule set
```

---

## Item 4: Long-Running Autonomous Capability

### Problem
Current design assumes task-by-task operation. The user wants the framework to keep running — processing tasks, scouting for problems, evolving — until it runs out of things to do or needs human input.

### Design: Autonomous Run Loop

```
┌─────────────────────────────────────────────────────┐
│              AUTONOMOUS RUN LOOP                     │
│                                                      │
│  ┌─────────┐    ┌──────────┐    ┌────────────────┐  │
│  │  SCOUT   │───▶│ TASK     │───▶│ EXECUTE &      │  │
│  │  CYCLE   │    │ QUEUE    │    │ REVIEW         │  │
│  └─────────┘    └──────────┘    └───────┬────────┘  │
│       │              ▲                   │           │
│       │              │                   ▼           │
│  ┌─────────┐    ┌──────────┐    ┌────────────────┐  │
│  │ EVOLVE  │◀───│ REFLECT  │◀───│ AUDIT &        │  │
│  │ CYCLE   │    │ CYCLE    │    │ METRICS        │  │
│  └─────────┘    └──────────┘    └────────────────┘  │
│                                                      │
│  STOPS WHEN:                                         │
│  - Task queue empty AND no scout findings            │
│  - Human approval needed (Tier 1 evolution)          │
│  - Resource limit reached                            │
│  - Human sends halt signal                           │
│  - Critical safety issue detected                    │
│                                                      │
│  HUMAN DECISIONS:                                    │
│  - Queued as "pending_human" items                   │
│  - Framework continues with other work               │
│  - When human returns, decisions are presented        │
│  - Framework picks up where it left off              │
└─────────────────────────────────────────────────────┘
```

### Run Loop Detail

```yaml
autonomous_loop:
  phases:
    1_scout:
      description: "Scout agents proactively search for problems and opportunities"
      frequency: "Continuous — scouts run in background"
      outputs: "New task proposals added to queue"
      includes:
        - framework_weakness_scan
        - stagnation_check
        - diversity_measurement
        - pending_task_review
        - domain_specific_discovery

    2_prioritize:
      description: "Rank task queue by priority, dependencies, and expected impact"
      method: "Orchestrator scores tasks, selects next batch"
      factors:
        - priority_level
        - blocked_by_resolution
        - expected_improvement_magnitude
        - resource_cost_estimate
        - staleness (parked tasks get priority boost over time)

    3_execute:
      description: "Process tasks through full lifecycle"
      parallel: "Multiple tasks can execute if resources allow"
      mandatory: "Every task goes through REVIEW before COMPLETE"

    4_reflect:
      description: "After each task batch, reflect on what was learned"
      outputs:
        - "Did task performance match expectations?"
        - "Were the right roles assigned?"
        - "Was the right topology selected?"
        - "What would we do differently?"
      frequency: "After every 3-5 completed tasks"

    5_evolve:
      description: "Apply discovered improvements"
      auto: "Tier 3 changes applied immediately"
      queued: "Tier 2 changes queued for quorum"
      human: "Tier 1 changes queued for human approval"

  human_decision_queue:
    storage: "state/pending_human_decisions.yaml"
    format:
      - id: "hd-001"
        type: "tier1_evolution_approval"
        summary: "Proposed change to topology routing algorithm"
        detail: "..."
        proposed_by: "agent-003"
        quorum_result: "3/3 approve"
        blocking: false  # framework can continue with other work
        blocking_tasks: ["task-020"]  # which tasks wait for this
    presentation: |
      When human returns, show:
      1. Summary of what was accomplished while away
      2. Pending decisions ranked by impact
      3. Current task queue state
      4. Any parked tasks that could be resumed
```

### Proactive Scout Behavior

```yaml
scout_proactive:
  always_running: true
  scout_types:

    weakness_scanner:
      description: "Continuously looks for framework weaknesses"
      checks:
        - "Are there untested assumptions in the framework?"
        - "Are there roles that have never been used?"
        - "Are there topology patterns that haven't been tried?"
        - "Are there configuration archive cells that are empty?"
        - "Are process rules contradictory?"

    performance_monitor:
      description: "Tracks task performance trends"
      checks:
        - "Are tasks taking longer than expected?"
        - "Are review rounds increasing?"
        - "Are certain role compositions performing poorly?"
        - "Token usage trending up without quality improvement?"

    opportunity_detector:
      description: "Looks for improvement opportunities"
      checks:
        - "Could a new capability help with common task patterns?"
        - "Is there a recurring manual step that could be automated?"
        - "Are agents frequently blocked on the same issue?"

    risk_sentinel:
      description: "Monitors for emerging risks (links to Item 13)"
      checks:
        - "Is diversity declining?"
        - "Are evolutions becoming too frequent / too aggressive?"
        - "Are constitutional checks being skipped?"
        - "Is resource usage approaching limits?"
```

---

## Item 5: Meta-Analysis Methodology for Full Self-Audit

### Problem
Task logs alone aren't enough for full self-audit. The framework needs comprehensive meta-analysis of its own behavior patterns.

### Design: Meta-Analysis Dimensions

```yaml
meta_analysis:
  description: "Periodic deep analysis of framework behavior for self-improvement"
  frequency: "After every 10 completed tasks, or on human request"

  dimensions:

    # === ROLE ANALYTICS ===
    role_analytics:
      metrics:
        - role_utilization: "How often is each role composition used?"
        - role_effectiveness: "Task success rate by role composition"
        - role_switching_frequency: "How often do agents switch roles?"
        - role_creation_history: "Timeline of new roles created"
        - unused_roles: "Roles defined but never assigned"
        - overloaded_roles: "Roles assigned to >50% of tasks"
      analysis: |
        Are we using too few roles? Too many?
        Which roles drive success? Which are overhead?
        Should any roles be merged? Split? Deprecated?

    # === TOPOLOGY ANALYTICS ===
    topology_analytics:
      metrics:
        - topology_distribution: "How often each pattern is selected"
        - topology_effectiveness: "Task success rate by topology"
        - topology_override_rate: "How often does human override routing?"
        - routing_accuracy: "Did selected topology match actual task needs?"
        - topology_switching: "Did any tasks switch topology mid-execution?"
      analysis: |
        Is the topology router making good decisions?
        Are we over-relying on one pattern?
        Should routing rules be updated?

    # === TEAM/SWARM ANALYTICS ===
    team_swarm_analytics:
      metrics:
        - team_size_distribution: "How many agents per task?"
        - coordination_mode_usage: "Stigmergy vs quorum vs messaging"
        - inter_agent_message_count: "Communication volume per task"
        - agent_idle_time: "Time agents spend waiting vs working"
        - parallel_utilization: "How well are parallel agents utilized?"
        - swarm_vs_team_ratio: "Ratio of swarm to team topologies"
      analysis: |
        Are teams too large? Too small?
        Is coordination overhead justified by outcomes?
        Are we using the right coordination mode?

    # === EVOLUTION ANALYTICS ===
    evolution_analytics:
      metrics:
        - evolution_rate: "Changes per time period by tier"
        - evolution_success_rate: "Did changes improve outcomes?"
        - rollback_rate: "How often are evolutions rolled back?"
        - evolution_cascade: "Do changes cause unexpected downstream effects?"
        - tier_distribution: "Distribution of changes across tiers"
        - quorum_agreement_rate: "How often does quorum agree?"
        - human_override_rate: "How often does human override quorum?"
      analysis: |
        Is evolution rate healthy? Too fast (unstable) or too slow (stagnant)?
        Are Tier 3 auto-evolutions actually helping?
        Should tier boundaries be adjusted?

    # === DECISION ANALYTICS ===
    decision_analytics:
      metrics:
        - decision_volume: "Total decisions per time period"
        - human_vs_agent_ratio: "Ratio of human to agent decisions"
        - decision_reversal_rate: "How often are decisions reversed?"
        - decision_latency: "Time from need to decision"
        - human_bottleneck: "Decisions queued waiting for human"
      analysis: |
        Is the human a bottleneck?
        Are agents making good autonomous decisions?
        Should more decisions be delegated?

    # === DIVERSITY ANALYTICS ===
    diversity_analytics:
      metrics:
        - srd_trend: "SRD over time"
        - stagnation_events: "Count and frequency of stagnation detections"
        - scout_discovery_rate: "Novel findings per scout-hour"
        - homogenization_events: "Times diversity dropped below floor"
        - intervention_effectiveness: "Did diversity interventions work?"
      analysis: |
        Is diversity healthy?
        Are anti-homogenization mechanisms effective?
        Should thresholds be adjusted?

    # === COST ANALYTICS ===
    cost_analytics:
      metrics:
        - tokens_per_task: "Average and distribution"
        - tokens_by_role: "Which roles consume most tokens?"
        - tokens_by_topology: "Which patterns are most expensive?"
        - quality_per_token: "Task quality normalized by cost"
        - waste_detection: "Tasks that consumed many tokens but failed"
      analysis: |
        Are we spending tokens efficiently?
        Which patterns give best quality-per-token?

    # === REVIEW ANALYTICS ===
    review_analytics:
      metrics:
        - review_pass_rate: "First-pass approval rate"
        - common_findings: "Most frequent review issues"
        - review_rounds_distribution: "How many rounds to pass?"
        - reviewer_consistency: "Do different reviewers agree?"
        - rubber_stamp_detection: "Reviews that found zero issues (suspicious)"
      analysis: |
        Are reviews catching real issues?
        Are there patterns in failures that could be prevented earlier?

  output:
    format: "state/meta_analysis/report-{date}.yaml"
    includes:
      - dimension_scores  # 0-1 health score per dimension
      - trend_direction   # improving / stable / declining per dimension
      - actionable_findings  # specific improvement proposals
      - evolution_proposals  # proposed changes with tier classification
      - risk_flags  # items requiring human attention
```

### Self-Audit Report Template

```
══════════════════════════════════════════════════════
 META-ANALYSIS REPORT — 2026-02-27
 Tasks analyzed: 45-55 (tasks #45 through #55)
══════════════════════════════════════════════════════

 HEALTH DASHBOARD
 ┌─────────────────────┬───────┬──────────┐
 │ Dimension           │ Score │ Trend    │
 ├─────────────────────┼───────┼──────────┤
 │ Role utilization    │  0.72 │ ↑ +0.05  │
 │ Topology routing    │  0.85 │ → stable │
 │ Team efficiency     │  0.68 │ ↓ -0.03  │
 │ Evolution health    │  0.90 │ ↑ +0.08  │
 │ Decision quality    │  0.78 │ → stable │
 │ Diversity (SRD)     │  0.55 │ ↓ -0.07  │  ← WARNING
 │ Cost efficiency     │  0.73 │ ↑ +0.02  │
 │ Review quality      │  0.82 │ → stable │
 └─────────────────────┴───────┴──────────┘

 ALERTS
 [!] Diversity declining — SRD dropped from 0.62 to 0.55
     Recommendation: Spawn additional scout, inject novelty

 ACTIONABLE FINDINGS
 1. Reviewer role finding zero issues on 30% of tasks
    → May indicate rubber-stamping OR tasks are well-executed
    → Recommend: spot-check 3 "zero-issue" tasks for missed problems

 2. Hierarchical team topology selected 80% of the time
    → Over-reliance; parallel swarm untested on 3 suitable tasks
    → Recommend: Force parallel swarm on next suitable task

 3. New recurring pattern: agents often need "literature search" step
    → Recommend: Create dedicated "literature_scout" role composition

 EVOLUTION PROPOSALS
 - [Tier 3] Adjust topology router weights: parallel_swarm +0.1
 - [Tier 2] Create "literature_scout" role composition
 - [Tier 2] Add rubber-stamp detection to reviewer protocol
══════════════════════════════════════════════════════
```

---

## Item 6: Tree-Like GUI Viewer for Audit

### Design: Interactive Audit Tree

Two components: (a) a terminal-based tree viewer for daily use, (b) an HTML viewer for deep inspection.

### 6a. Terminal Tree Viewer (rich/textual based)

```
$ python tools/audit-tree.py --since 2026-02-27

Framework Session: 2026-02-27
├── [06:30] TASK task-001: Implement stagnation detection
│   ├── [06:30] INTAKE ← scout-003 (anomaly: SRD below threshold)
│   ├── [06:32] ANALYSIS → topology: hierarchical_team
│   │   └── Decision dec-001: scored hierarchical(0.8) > pipeline(0.5) > solo(0.3)
│   ├── [06:33] PLANNING by orchestrator (agent-001, opus)
│   │   ├── Subtask 1: Implement SRD metric calculation
│   │   ├── Subtask 2: Implement threshold monitoring
│   │   └── Subtask 3: Implement intervention triggers
│   ├── [06:34] SPAWNED agent-002 (implementer, sonnet)
│   ├── [06:35-06:50] EXECUTING
│   │   ├── [06:35] agent-002: Reading core/diversity.yaml
│   │   ├── [06:40] agent-002: Drafted SRD calculation
│   │   ├── [06:45] agent-002: Implemented threshold monitoring
│   │   └── [06:50] agent-002: Complete, requesting review
│   ├── [06:51-06:58] REVIEWING by agent-003 (reviewer, opus)
│   │   ├── [PASS] correctness
│   │   ├── [PASS] completeness (note: edge case missing)
│   │   ├── [PASS] consistency
│   │   └── [PASS] safety
│   ├── [06:58] VERDICT: pass_with_notes (confidence: 0.85)
│   ├── [07:00] COMPLETE — 45k tokens, 30min, 3 agents
│   └── ARTIFACTS: core/diversity.yaml, tools/diversity-check.sh
│
├── [07:05] EVOLUTION evo-001 (Tier 3, auto)
│   ├── Component: roles/compositions/researcher.yaml
│   ├── Change: exploration_vs_exploitation 0.4 → 0.5
│   ├── Trigger: SRD decline over tasks 46-50
│   ├── Constitutional check: PASS
│   └── Committed: abc123f
│
├── [07:10] TASK task-002: Validate topology routing accuracy
│   ├── ...
│   └── ...
│
├── [08:00] SCOUT REPORT: 3 findings
│   ├── Finding 1: Empty MAP-Elites cell (research_simple)
│   ├── Finding 2: Unused role composition (debater)
│   └── Finding 3: Potential optimization in coordination overhead
│
├── [08:05] HUMAN DECISION hd-001
│   ├── Type: Tier 1 evolution approval
│   ├── Proposal: Modify topology routing algorithm
│   └── Status: PENDING ← awaiting human
│
└── [08:30] META-ANALYSIS (tasks 45-55)
    ├── Health: 7/8 dimensions healthy
    ├── Alert: SRD declining
    └── Proposals: 3 evolution items generated
```

### 6b. HTML Interactive Viewer

```yaml
# tools/audit-viewer-web/
audit_web_viewer:
  technology: "Single HTML file with embedded JS (no build step needed)"
  features:
    - collapsible_tree: "Expand/collapse task details, subtasks, agent actions"
    - timeline_view: "Horizontal timeline with zoom and filter"
    - filter_panel:
        by_type: [task, evolution, decision, scout, meta_analysis]
        by_actor: [human, agent-001, scout-003, ...]
        by_status: [complete, failed, parked, pending_human]
        by_date_range: true
    - search: "Full-text search across all log entries"
    - detail_panel: "Click any node to see full record"
    - evolution_diff: "Syntax-highlighted diffs for evolution changes"
    - metrics_charts:
        - srd_over_time: "Line chart"
        - topology_distribution: "Pie chart"
        - tokens_per_task: "Bar chart"
        - role_utilization: "Heatmap"
    - task_flow: "Sankey diagram: intake → topology → roles → verdict"
    - export: "Export filtered view to markdown or JSON"

  generation: |
    python tools/generate-audit-viewer.py
    → Opens audit-viewer.html with all logs loaded
    → Self-contained, no server needed
    → Can be shared as a single file
```

---

## Item 8: Taking Over Tasks from ai-lab-agents / ai-game-studio

### Design: Migration Protocol

```yaml
migration:
  description: "Import existing work from ai-lab-agents or ai-game-studio into Universal Agents"

  import_protocol:
    1_analyze:
      description: "Scan source organization's state"
      reads:
        - config/*.yaml  # hierarchy, models, tools
        - instructions/*.md  # role definitions
        - instructions/*_process_rules.md  # operational rules
        - queue/  # pending tasks
        - dashboard.md  # current state
        - memory.db  # universal memory database

    2_map_roles:
      description: "Map source roles to Universal Agents capability compositions"
      mapping_example:
        principal_investigator: [deep_analysis, creative_synthesis, can_spawn_agents, can_propose_evolution]
        lab_manager: [rapid_execution, can_spawn_agents, can_park_tasks]
        experiment_engineer: [rapid_execution, domain:experiment_execution]
        theorist: [deep_analysis, creative_synthesis]
        critic: [critical_evaluation]
        peer_reviewer: [critical_evaluation, deep_analysis]
        scout: [exploration]  # NEW — doesn't exist in source

    3_convert_rules:
      description: "Import process rules as domain charter + operational rules"
      mapping:
        critical_rules: "→ domain CHARTER.md (Tier 1)"
        operational_rules: "→ roles/compositions/*.yaml forbidden lists (Tier 2-3)"
        incident_traces: "→ memory/failures.yaml"

    4_import_memory:
      description: "Migrate universal memory database"
      method: "Copy memory.db entries with re-tagged metadata"

    5_import_pending_tasks:
      description: "Convert pending queue items to Universal Agents task format"
      mapping:
        queue/agent-specs/*.yaml: "→ state/tasks/active/task-*.yaml"
        dashboard.md: "→ state/organization.yaml + state/tasks/focus.yaml"

    6_validate:
      description: "Verify migration completeness"
      checks:
        - "All roles have corresponding compositions"
        - "All process rules are captured"
        - "All pending tasks are imported"
        - "Memory is accessible and searchable"
        - "Domain charter reflects source organization's values"

  coexistence:
    description: "Universal Agents can run alongside existing organizations"
    method: |
      Source orgs keep running in their directories.
      Universal Agents operates in its own directory.
      Shared: universal-memory MCP (same database or linked databases)
      Migration can be gradual: import one workstream at a time.
```

---

## Item 9: Domain Switching via Working Subdirectory

### Design: Domain as Workspace

```
universal-agents/                      # Framework scaffold (template)
├── CONSTITUTION.md                    # Global (shared across all instances)
├── core/                              # Engine definitions (shared)
├── roles/                             # Base role compositions (shared)
├── tools/                             # Utility scripts (shared)
│
├── instances/                         # Each domain is a separate workspace
│   ├── meta/                          # Self-improvement instance
│   │   ├── CHARTER.md                 # Meta-specific charter
│   │   ├── domain.yaml                # Meta domain config
│   │   ├── state/                     # Meta-specific state
│   │   ├── logs/                      # Meta-specific logs
│   │   ├── memory/                    # Meta-specific memory
│   │   └── .git/                      # Separate git history
│   │
│   ├── research-lab/                  # Research lab instance
│   │   ├── CHARTER.md
│   │   ├── domain.yaml
│   │   ├── state/
│   │   ├── logs/
│   │   └── .git/
│   │
│   └── game-studio/                   # Game studio instance
│       ├── CHARTER.md
│       ├── domain.yaml
│       ├── state/
│       ├── logs/
│       └── .git/
│
└── shared/                            # Cross-domain resources
    ├── memory.db                      # Shared universal memory
    ├── archive/                       # MAP-Elites archive (all domains)
    └── evolution-history/             # Global evolution history
```

### Domain Switching Protocol

```yaml
domain_switch:
  trigger: "Human requests domain switch"

  process:
    1. Human: "Switch to research-lab"
    2. Framework: "Current domain: meta. Active tasks: 2. Parked tasks: 1."
    3. Framework: "Options:"
       a. "Park all active tasks and switch"
       b. "Complete active tasks first, then switch"
       c. "Cancel switch"
    4. Human selects option
    5. If switching:
       a. Park/complete active tasks in current instance
       b. Change working directory to instances/research-lab/
       c. Load CHARTER.md for research-lab
       d. Load state, tasks, agents from research-lab instance
       e. Log domain switch to shared/evolution-history/
    6. Framework operates in new domain context

  new_domain_creation:
    trigger: "Human requests a domain that doesn't exist"
    process:
      1. Human: "Create new domain: startup-advisor"
      2. Framework copies scaffold:
         - core/ reference (symlink or copy)
         - roles/ base compositions
         - Empty state/, logs/, memory/
      3. Human provides or co-creates CHARTER.md
      4. Framework generates domain-specific capabilities
      5. Domain ready for use

  cross_domain_learning:
    description: "Successful patterns from one domain can transfer to others"
    mechanism:
      - Shared MAP-Elites archive (archive entries tagged with source domain)
      - Shared universal memory (semantic knowledge crosses domains)
      - Evolution history (innovations in one domain inform others)
    constraint: "Domain-specific rules don't cross over — only general patterns"
```

---

## Item 10: Role Creation and Adaptation via Evolution

### Problem
v0.1 evolution can modify existing roles but doesn't explicitly cover creating entirely new roles or adapting role compositions based on experience.

### Design: Role Lifecycle

```yaml
role_lifecycle:

  # === CREATION ===
  creation:
    triggers:
      - "Meta-analysis identifies recurring capability gap"
      - "Scout discovers need for capability that no existing role covers"
      - "Human requests new role"
      - "Task fails because no suitable role exists"

    process:
      1. IDENTIFY: What capability is missing? What tasks would benefit?
      2. COMPOSE: Select capability atoms that address the gap
         - Can reuse existing atoms
         - Can propose new capability atoms (Tier 2 evolution)
      3. DEFINE: Write role composition YAML
         - Name, description, capabilities, model tier, behavioral descriptors
         - Forbidden actions, authority level
      4. VALIDATE:
         - Constitutional check (no axiom violations)
         - Diversity check (doesn't duplicate an existing role)
         - Quorum evaluation (Tier 2 — new role creation)
      5. TEST: Assign to a real task in trial mode
         - Task is reviewed with extra scrutiny
         - Role performance metrics collected
      6. COMMIT: If trial succeeds, add to roles/compositions/
      7. ARCHIVE: Add to MAP-Elites archive

    evolution_tier: 2  # New role creation requires quorum approval

  # === ADAPTATION ===
  adaptation:
    triggers:
      - "Role performance declining over N tasks"
      - "Review findings reveal consistent weakness"
      - "Environment changed (new tools, new domain capabilities)"

    process:
      1. DIAGNOSE: What's wrong with current role composition?
      2. PROPOSE: Specific changes to capabilities, descriptors, or forbidden rules
      3. EVALUATE: Will this improve the role? Impact on diversity?
      4. APPLY: Modify role composition
      5. VERIFY: Monitor next 3 tasks with adapted role

    evolution_tier: 3  # Role adaptation is operational (auto-evolve)

  # === DEPRECATION ===
  deprecation:
    triggers:
      - "Role unused for 20+ tasks"
      - "Role consistently outperformed by another role on same tasks"
      - "Meta-analysis flags as redundant"

    process:
      1. PROPOSE: Deprecation with rationale
      2. QUORUM: Tier 2 vote (roles are organizational assets)
      3. ARCHIVE: Move to roles/deprecated/ (not deleted — may be useful later)
      4. MIGRATE: Reassign any pending tasks that were using this role

    evolution_tier: 2  # Role deprecation requires quorum
```

### Capability Atom Creation

```yaml
capability_creation:
  description: "Creating new capability atoms (not just composing existing ones)"
  triggers:
    - "No existing capability atom matches the needed behavior"
    - "New tool or API becomes available"
    - "Domain-specific skill needed"

  process:
    1. Define capability:
       - Name, description
       - Instruction fragment (the prompt injection)
       - Model preference
       - Tool requirements
    2. Test: Use in a role composition on a real task
    3. Validate: Did the instruction fragment produce desired behavior?
    4. Commit: Add to roles/capabilities.yaml

  evolution_tier: 2  # New capability atoms are organizational

  # IMPORTANT: Relates to Item 3 (skills crystallization)
  # Capability atoms are the framework's "crystallized skills"
  # They must be validated — LLM-generated instruction fragments
  # are not automatically effective (see research on Item 3)
  quality_gates:
    - "Instruction fragment must be tested on at least 2 different tasks"
    - "Behavioral effect must be measurable (A/B comparison)"
    - "Must not duplicate existing capability (similarity check)"
```

---

## Item 5+13 (Combined): Self-Audit + Self-Risk Awareness

### Unified Self-Reflection Protocol

```yaml
self_reflection:
  description: "Periodic deep self-analysis combining meta-analysis, capability assessment, and risk detection"

  # Runs after every meta-analysis cycle
  protocol:

    1_capability_audit:
      question: "What can the framework currently do well and poorly?"
      checks:
        - "List all domain types successfully handled"
        - "List all topology patterns used vs unused"
        - "Identify tasks that failed or required multiple review rounds"
        - "Identify capability gaps (tasks we can't handle)"
        - "Rate each role composition's effectiveness (0-1)"

    2_risk_audit:
      question: "What risks does the framework currently face?"
      categories:

        operational_risks:
          - "Are there single points of failure?"
          - "What happens if the orchestrator agent fails mid-task?"
          - "What happens if universal memory becomes corrupted?"
          - "Are there tasks that have been parked too long?"

        evolution_risks:
          - "Is evolution rate too fast (instability)?"
          - "Is evolution rate too slow (stagnation)?"
          - "Are Tier 3 auto-evolutions drifting from original intent?"
          - "Is the evolution engine itself becoming a risk?"
          - "Are quorum votes becoming rubber-stamps?"

        diversity_risks:
          - "Is SRD trending down?"
          - "Are scouts finding fewer novel issues?"
          - "Are all agents using similar reasoning patterns?"
          - "Is the MAP-Elites archive becoming stale?"

        knowledge_risks:
          - "Is organizational memory growing stale?"
          - "Are we building on outdated assumptions?"
          - "Is cross-domain learning introducing domain-inappropriate patterns?"

        resource_risks:
          - "Token usage trending up without quality improvement?"
          - "Rate limit approaching? (Claude Max subscription)"
          - "Log storage growing unsustainably?"

    3_governance_check:
      question: "Is the framework governing itself properly?"
      checks:
        - "Are constitutional hash checks passing?"
        - "Are all required reviews actually happening?"
        - "Are quorum votes genuinely independent (sealed)?"
        - "Is the human informed of all Tier 1 changes?"
        - "Is the audit trail complete (no gaps)?"

    4_self_risk_score:
      output: |
        RISK SCORECARD
        ┌──────────────────────┬──────┬──────────┐
        │ Risk Category        │ Score│ Trend    │
        ├──────────────────────┼──────┼──────────┤
        │ Operational          │  0.2 │ → stable │ (low risk)
        │ Evolution            │  0.4 │ ↑ +0.1  │ (watch)
        │ Diversity            │  0.6 │ ↑ +0.15 │ (WARNING)
        │ Knowledge            │  0.3 │ → stable │ (ok)
        │ Resource             │  0.2 │ → stable │ (ok)
        │ Governance           │  0.1 │ → stable │ (good)
        └──────────────────────┴──────┴──────────┘

      actions:
        - score > 0.7: "HALT affected operations, alert human"
        - score > 0.5: "Escalate to human, propose mitigations"
        - score > 0.3: "Log and monitor, increase check frequency"
        - score < 0.3: "Healthy — continue normal operation"

    5_improvement_proposals:
      output: |
        Based on self-reflection, generate:
        1. Capability gaps to address (new roles, new capabilities)
        2. Risk mitigations to implement
        3. Process improvements
        4. Evolution proposals with tier classification
        Each proposal links to the specific finding that generated it.
```

---

## Updated Directory Structure (v0.2)

```
universal-agents/
├── CONSTITUTION.md                    # Global immutable axioms
├── CLAUDE.md                          # Bootstrap instructions
├── framework.yaml                     # Core config
│
├── core/                              # Engine definitions
│   ├── lifecycle.yaml                 # Task lifecycle
│   ├── evolution.yaml                 # Evolution tiers
│   ├── topology.yaml                  # Topology routing
│   ├── diversity.yaml                 # Diversity metrics
│   ├── coordination.yaml              # Coordination modes
│   ├── audit.yaml                     # Audit config
│   ├── autonomous-loop.yaml           # Long-running loop (NEW - Item 4)
│   ├── meta-analysis.yaml             # Self-audit methodology (NEW - Item 5)
│   └── self-reflection.yaml           # Risk awareness protocol (NEW - Item 13)
│
├── roles/
│   ├── capabilities.yaml              # Capability atoms
│   ├── compositions/
│   │   ├── orchestrator.yaml
│   │   ├── researcher.yaml
│   │   ├── implementer.yaml
│   │   ├── reviewer.yaml
│   │   ├── scout.yaml
│   │   ├── debater.yaml
│   │   └── ... (new roles via evolution)
│   ├── deprecated/                    # Deprecated roles (NEW - Item 10)
│   └── archive/                       # MAP-Elites archive
│
├── instances/                         # Domain workspaces (CHANGED - Item 9)
│   ├── meta/                          # Self-improvement workspace
│   │   ├── CHARTER.md                 # Domain charter (NEW - Item 1)
│   │   ├── domain.yaml
│   │   ├── state/
│   │   │   ├── organization.yaml
│   │   │   ├── agents/
│   │   │   ├── tasks/
│   │   │   │   ├── focus.yaml
│   │   │   │   ├── active/
│   │   │   │   ├── parked/
│   │   │   │   └── completed/
│   │   │   └── coordination/
│   │   ├── logs/
│   │   │   ├── evolution/
│   │   │   ├── tasks/
│   │   │   ├── decisions/
│   │   │   ├── diversity/
│   │   │   └── meta-analysis/         # (NEW - Item 5)
│   │   └── memory/
│   │
│   ├── research-lab/                  # (created on demand)
│   └── game-studio/                   # (created on demand)
│
├── shared/                            # Cross-domain (NEW - Item 9)
│   ├── memory.db                      # Shared universal memory
│   ├── archive/                       # Cross-domain config archive
│   ├── evolution-history/             # Global evolution log
│   └── skills/                        # Crystallized skills (NEW - Item 3)
│
├── migration/                         # (NEW - Item 8)
│   ├── import-lab.sh
│   ├── import-studio.sh
│   └── migration-log/
│
└── tools/
    ├── bootstrap.sh
    ├── spawn-agent.sh
    ├── park-task.sh
    ├── resume-task.sh
    ├── evolve.sh
    ├── domain-switch.sh               # (UPDATED - Item 9)
    ├── domain-create.sh               # (NEW - Item 9)
    ├── audit-viewer.sh                # CLI viewer
    ├── audit-tree.py                  # Terminal tree viewer (NEW - Item 6)
    ├── generate-audit-viewer.py       # HTML viewer generator (NEW - Item 6)
    ├── diversity-check.sh
    ├── meta-analysis.sh               # (NEW - Item 5)
    ├── self-reflection.sh             # (NEW - Item 13)
    ├── migrate-from.sh                # (NEW - Item 8)
    └── role-creator.sh                # (NEW - Item 10)
```

---

## Research Pending Integration

The following items will be integrated after background research completes:

| Item | Research Topic | Expected Output |
|------|---------------|-----------------|
| 2 | Creativity in multi-agent systems | Creative collaboration protocols, creativity metrics |
| 3 | Skills crystallization + LLM skills effectiveness | Skill validation pipeline, quality gates for auto-generated capabilities |
| 7 | Self-capability-aware improvement | Methodology for the framework to know its own strengths/weaknesses |
| 12 | Bootstrapping paradox resolution | Dual-copy or staged approach for safe self-evolution |
| 13 | Self-risk awareness / self-governance | Risk detection patterns, governance mechanisms |

---

*End of v0.2 Addendum*
*Companion to: framework-design-universal-agents.md (v0.1)*
