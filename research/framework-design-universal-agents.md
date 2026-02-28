# Universal Agents Framework — Design Document

**Version:** 0.1 (Design Draft)
**Date:** 2026-02-27
**Status:** Design — pending implementation
**First Domain:** Meta (self-improvement)

---

## 1. Design Philosophy

### 1.1 Core Thesis

A domain-agnostic, self-evolving multi-agent framework where:
- **Roles are composable atoms**, not hardcoded personas
- **Topology adapts per task**, not per framework instance
- **Evolution is a first-class operation**, not an afterthought
- **Everything is auditable** — no action happens without a trace
- **The framework's first job is to make itself better**

### 1.2 What This Replaces

| Aspect | ai-lab-agents / ai-game-studio | Universal Agents |
|--------|-------------------------------|-----------------|
| Roles | Hardcoded (PI, Director, etc.) | Composable from capability atoms |
| Domain | Locked (research / game dev) | Loaded from domain config |
| Topology | Fixed hierarchy | Dynamic per-task (parallel / sequential / hierarchical / hybrid) |
| Evolution | Manual (IDOE, human edits) | Tiered (auto → quorum → human) |
| Task mgmt | Session-scoped | Persistent with park/resume |
| Audit | Partial (process rules changelog) | Complete (every action logged) |
| Diversity | Not measured | Built-in SRD metric |
| Coordination | Explicit messaging only | Stigmergic + quorum + messaging |

### 1.3 Guiding Principles

1. **Complexity only when it improves outcomes** (Anthropic's principle)
2. **Fail loud, never silent** (from CLAUDE.md defensive coding)
3. **Measure before you manage** (diversity, stagnation, cost)
4. **Everything is a file** — git-trackable, human-readable, portable
5. **The framework eats its own dogfood** — meta domain first

---

## 2. Constitutional Invariants

These rules are **structurally protected** — they live in `CONSTITUTION.md` and the evolution engine is physically prevented from modifying this file. Only the human supervisor can edit it.

```yaml
# CONSTITUTION.md — Immutable Axioms
# This file CANNOT be modified by any agent. Only the human supervisor may edit it.
# The evolution engine MUST check this file's hash before and after any evolution cycle.
# If the hash changes unexpectedly, ALL evolution halts and the human is alerted.

axioms:
  A1_human_halt:
    text: "The human supervisor can halt all operations at any time"
    enforcement: "All agents check for halt signal before each action"

  A2_human_veto:
    text: "The human supervisor can veto any decision, evolution, or action"
    enforcement: "High-risk changes require human approval before commit"

  A3_no_self_modify_constitution:
    text: "No agent may modify CONSTITUTION.md or the constitutional check mechanism"
    enforcement: "constitution.md is in evolution engine's exclude list; hash-verified"

  A4_full_traceability:
    text: "Every action, decision, and evolution must be logged with provenance"
    enforcement: "Audit middleware wraps all state-changing operations"

  A5_reversibility:
    text: "Every evolution must be reversible — rollback must be possible"
    enforcement: "Git commit before every evolution; rollback script available"

  A6_diversity_floor:
    text: "The framework must maintain minimum reasoning diversity across agents"
    enforcement: "SRD metric checked; evolution that reduces diversity below floor is rejected"

  A7_review_mandate:
    text: "Every task output must be reviewed before being marked complete"
    enforcement: "Task lifecycle requires REVIEW state before COMPLETE"

  A8_resource_bounds:
    text: "The framework must respect resource limits (rate limits, tokens, cost)"
    enforcement: "Resource monitor tracks usage; agents throttled at limits"
```

---

## 3. Architecture Overview

### 3.1 Layer Model

```
┌──────────────────────────────────────────────────────┐
│                  HUMAN SUPERVISOR                     │
│          (veto, high-risk approval, direction)        │
├──────────────────────────────────────────────────────┤
│              EVOLUTION ENGINE (Tier 0-3)              │
│    Constitutional guard │ Quorum gate │ Auto-evolve   │
├──────────────────────────────────────────────────────┤
│              TOPOLOGY ROUTER                          │
│    Task analysis → Pattern selection → Agent scaling  │
├──────────────────────────────────────────────────────┤
│              COORDINATION LAYER                       │
│    Stigmergy │ Quorum Sensing │ Direct Messaging      │
├──────────────────────────────────────────────────────┤
│              AGENT POOL                               │
│    Composable roles │ Dynamic spawn/despawn │ Scouts   │
├──────────────────────────────────────────────────────┤
│              TASK LIFECYCLE                            │
│    Intake→Analysis→Plan→Execute→Review→Verdict→Archive│
├──────────────────────────────────────────────────────┤
│              AUDIT & MEMORY                           │
│    Evolution log │ Task log │ Decision log │ Viewer    │
├──────────────────────────────────────────────────────┤
│              INFRASTRUCTURE                           │
│    Claude Code │ Claude Max OAuth │ File system │ Git  │
└──────────────────────────────────────────────────────┘
```

### 3.2 Claude Code Integration

The framework runs entirely within Claude Code using Claude Max subscription OAuth. Key mappings:

| Framework Concept | Claude Code Primitive |
|---|---|
| Agent spawn | `Task` tool with `subagent_type` |
| Agent team | `TeamCreate` + `SendMessage` |
| Task management | `TaskCreate` / `TaskUpdate` / `TaskList` |
| Persistent state | File system (YAML/JSON) + git |
| Organizational memory | Universal Memory MCP (`store_memory` / `recall_memories`) |
| Inter-agent communication | `SendMessage` (explicit) + shared files (stigmergic) |
| Evolution tracking | Git commits + JSONL audit logs |
| Human interaction | `AskUserQuestion` + direct conversation |

### 3.3 Bootstrap Sequence

```
1. Human starts Claude Code in framework directory
2. CLAUDE.md loads framework bootstrap instructions
3. Bootstrap agent reads:
   a. CONSTITUTION.md → verify hash, load axioms
   b. framework.yaml → core configuration
   c. domain/active.yaml → current domain
   d. state/organization.yaml → current org structure
   e. state/tasks/active/ → any active task contexts
   f. logs/ → recent evolution and decision history
4. Bootstrap agent checks for parked tasks, offers to resume or start new
5. Framework is operational
```

---

## 4. Role System — Composable Capabilities

### 4.1 Capability Atoms

Instead of monolithic role definitions (500+ line instruction files), roles are composed from small, reusable capability atoms.

```yaml
# roles/capabilities.yaml
capabilities:

  # === Reasoning Styles ===
  deep_analysis:
    description: "Systematic, thorough analysis with evidence chains"
    instruction_fragment: |
      Analyze thoroughly. Every claim requires evidence. Show your reasoning chain.
      Never skip steps. Prefer depth over breadth.
    model_preference: opus
    thinking: extended

  creative_synthesis:
    description: "Connect disparate ideas, generate novel hypotheses"
    instruction_fragment: |
      Look for unexpected connections. Combine ideas from different domains.
      Propose bold hypotheses. Quantity of ideas first, then filter.
    model_preference: opus
    thinking: extended

  rapid_execution:
    description: "Fast, focused task completion"
    instruction_fragment: |
      Execute efficiently. Minimize deliberation. Follow the plan precisely.
      Ask only if blocked, not for confirmation.
    model_preference: sonnet
    thinking: false

  critical_evaluation:
    description: "Find flaws, challenge assumptions, verify claims"
    instruction_fragment: |
      Your job is to find what's wrong. Challenge every assumption.
      Check evidence quality. Look for logical gaps. Be adversarial.
    model_preference: opus
    thinking: extended

  exploration:
    description: "Broad search, scout for unknowns, find what others miss"
    instruction_fragment: |
      Search broadly. Look where others haven't. Your success metric is
      novelty — finding things the team doesn't know about yet.
      Report anomalies even if you can't explain them.
    model_preference: sonnet
    thinking: true

  # === Authorities ===
  can_spawn_agents:
    description: "Authority to spawn sub-agents"
    authority: true

  can_evolve_tier3:
    description: "Authority to auto-evolve operational rules"
    authority: true

  can_propose_evolution:
    description: "Authority to propose framework evolution (requires approval)"
    authority: true

  can_park_tasks:
    description: "Authority to park/resume task contexts"
    authority: true

  # === Domain-Specific (loaded from domain config) ===
  # These are injected at runtime based on domain/active.yaml
```

### 4.2 Role Compositions

A role is a named combination of capabilities + behavioral descriptors.

```yaml
# roles/compositions/orchestrator.yaml
role:
  name: orchestrator
  description: "Strategic coordinator — decomposes tasks, selects topology, manages agents"
  capabilities:
    - deep_analysis
    - can_spawn_agents
    - can_park_tasks
    - can_propose_evolution
  model: opus
  thinking: extended
  behavioral_descriptors:
    reasoning_style: strategic
    risk_tolerance: low
    exploration_vs_exploitation: 0.3  # mostly exploitation
  authority_level: 2  # 0=worker, 1=lead, 2=orchestrator, 3=evolution engine
  forbidden:
    - "Must not execute tasks directly — delegate everything"
    - "Must not skip topology analysis"
    - "Must not spawn more agents than resource_monitor allows"
```

```yaml
# roles/compositions/scout.yaml
role:
  name: scout
  description: "Exploration agent — finds problems, anomalies, and opportunities others miss"
  capabilities:
    - exploration
    - creative_synthesis
    - can_propose_evolution
  model: sonnet
  thinking: true
  behavioral_descriptors:
    reasoning_style: divergent
    risk_tolerance: high
    exploration_vs_exploitation: 0.9  # almost pure exploration
  authority_level: 0
  forbidden:
    - "Must not converge on consensus — your job is to disagree"
    - "Must not optimize existing solutions — find new problems"
  scout_config:
    stagnation_trigger: true  # activated when diversity drops
    anomaly_reporting: true   # report anything unexpected
    negative_selection: true  # flag what doesn't match known patterns
```

```yaml
# roles/compositions/reviewer.yaml
role:
  name: reviewer
  description: "Quality gate — verifies all outputs before completion"
  capabilities:
    - critical_evaluation
    - deep_analysis
  model: opus
  thinking: extended
  behavioral_descriptors:
    reasoning_style: analytical
    risk_tolerance: very_low
    exploration_vs_exploitation: 0.1
  authority_level: 1
  forbidden:
    - "Must not approve own work"
    - "Must not rubber-stamp — every review must contain specific findings"
    - "Must not modify the artifact under review — only report findings"
  review_mandate:
    required_checks:
      - correctness: "Does the output match the task requirements?"
      - completeness: "Is anything missing from the deliverable?"
      - consistency: "Does it align with existing framework state?"
      - safety: "Does it violate any constitutional axiom?"
```

### 4.3 Dynamic Role Switching

Agents can switch roles by loading a different composition. This is the key portability mechanism.

```yaml
# Role switching protocol
role_switch:
  trigger: "Orchestrator assigns new role OR stagnation detected OR task requires it"
  process:
    1. Agent saves current context to state/agents/{id}/context_snapshot.yaml
    2. Agent loads new role composition from roles/compositions/{new_role}.yaml
    3. Agent re-reads domain-specific capabilities from domain/active.yaml
    4. Agent logs role switch to logs/decisions/
    5. Agent continues with new behavioral descriptors
  constraints:
    - "Cannot switch to authority_level higher than current without orchestrator approval"
    - "Scout role can only be assigned, not self-selected (prevents gaming)"
    - "Role switch is logged as a decision with reason"
```

### 4.4 Rapid Agent Spawning

New agents are spawned via a standardized template that composes instructions from capabilities:

```
spawn_agent(role_name, task_context) →
  1. Load roles/compositions/{role_name}.yaml
  2. Load roles/capabilities.yaml for each listed capability
  3. Concatenate instruction fragments into agent prompt
  4. Inject domain-specific context from domain/active.yaml
  5. Inject task context (curated, not raw dump)
  6. Select model tier from role config
  7. Call Claude Code Task tool with composed prompt
  8. Register agent in state/agents/registry.yaml
  9. Log spawn to logs/decisions/
```

---

## 5. Topology Router — Teams/Swarms Balance

### 5.1 Task Analysis

When a task arrives, the topology router analyzes it before any agents are spawned:

```yaml
# core/topology.yaml
topology_router:
  analysis_dimensions:
    decomposability:
      question: "Can this task be broken into independent subtasks?"
      values: [monolithic, partially_decomposable, fully_decomposable]

    interdependency:
      question: "How much do subtasks depend on each other?"
      values: [independent, loosely_coupled, tightly_coupled]

    exploration_vs_execution:
      question: "Is this about finding the right approach or executing a known one?"
      values: [pure_exploration, mixed, pure_execution]

    quality_criticality:
      question: "How important is correctness vs. speed?"
      values: [speed_priority, balanced, correctness_priority]

    scale:
      question: "How many parallel workers could this benefit from?"
      values: [single, small_team(2-4), medium_team(5-8), swarm(9+)]

    novelty:
      question: "Has the framework solved similar tasks before?"
      values: [novel, partially_familiar, well_known]
```

### 5.2 Topology Selection Rules

```yaml
topology_patterns:

  solo:
    when:
      decomposability: monolithic
      scale: single
    structure: "Single agent with appropriate role"
    agents: 1
    overhead: minimal

  pipeline:
    when:
      decomposability: partially_decomposable
      interdependency: tightly_coupled
    structure: "Sequential chain — each agent's output feeds the next"
    agents: 2-4
    pattern: "A → B → C → Review"

  parallel_swarm:
    when:
      decomposability: fully_decomposable
      interdependency: independent
      exploration_vs_execution: pure_exploration
    structure: "Parallel agents, results aggregated"
    agents: 3-8 (resource-dependent)
    pattern: "Spawn N → Execute in parallel → Aggregate → Review"
    coordination: stigmergic  # shared pressure fields, not messages

  hierarchical_team:
    when:
      interdependency: loosely_coupled
      quality_criticality: correctness_priority
    structure: "Orchestrator + specialized workers"
    agents: 3-6
    pattern: "Orchestrator decomposes → Workers execute → Orchestrator synthesizes → Review"
    coordination: explicit  # direct messaging

  hybrid:
    when:
      decomposability: partially_decomposable
      exploration_vs_execution: mixed
    structure: "Orchestrator + parallel explorers + sequential executors"
    agents: 4-10
    pattern: "Orchestrator → {Explore swarm || Execute pipeline} → Synthesize → Review"
    coordination: mixed  # stigmergy for exploration, messaging for execution

  debate:
    when:
      novelty: novel
      quality_criticality: correctness_priority
    structure: "Multiple agents argue, judge decides"
    agents: 3-5
    pattern: "Proposers(N) → Debate rounds → Judge → Review"
    coordination: structured_debate

# Resource-aware scaling
resource_scaling:
  check_before_spawn: true
  max_concurrent_agents: "auto"  # determined by rate limit monitoring
  backoff_on_rate_limit: true
  prefer_fewer_stronger: true  # 3 opus > 8 haiku for most tasks
```

### 5.3 Topology Routing Algorithm

```
INPUT: Task description T
OUTPUT: Topology pattern P, agent count N, role assignments R

1. ANALYZE T along 6 dimensions (use LLM judgment + heuristics)
2. MATCH analysis to topology_patterns rules
3. CHECK resource_monitor for available capacity
4. ADJUST agent count based on available capacity
5. SELECT roles for each agent slot from roles/compositions/
6. IF task is novel AND diversity metric is low:
     INJECT scout agent into the team
7. LOG topology decision to logs/decisions/
8. RETURN (P, N, R)
```

---

## 6. Task Lifecycle — Full Audit

### 6.1 State Machine

```
                    ┌─────────┐
                    │  INTAKE  │ ← New task arrives (human or agent-generated)
                    └────┬────┘
                         │ Log: task origin, raw description
                         ▼
                    ┌─────────┐
                    │ ANALYSIS │ ← Topology router analyzes task
                    └────┬────┘
                         │ Log: analysis dimensions, topology selected
                         ▼
                    ┌─────────┐
                    │ PLANNING │ ← Orchestrator decomposes, assigns roles
                    └────┬────┘
                         │ Log: decomposition, role assignments, agent spawns
                    ┌────┴────┐
                    ▼         ▼
              ┌──────────┐ ┌─────────┐
              │ EXECUTING │ │ PARKED  │ ← Context-switched to another task
              └────┬─────┘ └────┬────┘
                   │            │ (resumed later)
                   │ Log: agent actions, intermediate results, decisions
                   ▼
              ┌──────────┐
              │ REVIEWING │ ← MANDATORY — every task is reviewed (Axiom A7)
              └────┬─────┘
                   │ Log: reviewer findings, pass/fail, specific issues
                   ▼
              ┌──────────┐
          ┌───│ VERDICT   │──── FAIL → back to PLANNING (with feedback)
          │   └──────────┘
          │        │ Log: final verdict, reviewer identity, rationale
          │        ▼
          │   ┌──────────┐
          │   │ COMPLETE  │ ← Fully verified output
          │   └────┬─────┘
          │        │ Log: completion summary, artifacts, metrics
          │        ▼
          │   ┌──────────┐
          └──▶│ ARCHIVED  │ ← Immutable record with full audit trail
              └──────────┘
```

### 6.2 Task Record Structure

```yaml
# state/tasks/active/task-{id}.yaml
task:
  id: "task-20260227-001"
  created: "2026-02-27T06:30:00Z"
  status: executing  # intake|analysis|planning|executing|parked|reviewing|verdict|complete|archived

  # === WHAT ===
  title: "Implement stagnation detection for diversity monitor"
  description: "..."
  origin:
    type: agent_generated  # human|agent_generated|evolution_triggered|scout_discovery
    source: "scout-agent-003"
    reason: "Diversity metric dropped below threshold for 3 consecutive checks"

  # === WHY ===
  rationale: "Without stagnation detection, the framework cannot self-correct diversity collapse"
  priority: high  # critical|high|medium|low
  links:
    parent_task: null
    blocks: ["task-20260227-003"]
    blocked_by: []
    related_evolution: "evo-20260227-001"

  # === HOW ===
  topology:
    pattern: hierarchical_team
    analysis: { decomposability: partially_decomposable, ... }
    agents:
      - { role: orchestrator, agent_id: "agent-001", model: opus }
      - { role: implementer, agent_id: "agent-002", model: sonnet }
      - { role: reviewer, agent_id: "agent-003", model: opus }

  # === EXECUTION ===
  timeline:
    - { time: "...", event: intake, actor: scout-agent-003, detail: "..." }
    - { time: "...", event: analysis, actor: topology-router, detail: "..." }
    - { time: "...", event: planning, actor: agent-001, detail: "..." }
    - { time: "...", event: agent_spawned, actor: agent-001, detail: "spawned agent-002 as implementer" }
    - { time: "...", event: executing, actor: agent-002, detail: "..." }

  # === REVIEW ===
  review:
    reviewer: "agent-003"
    reviewer_role: reviewer
    findings:
      - { type: pass, check: correctness, detail: "Implementation matches requirements" }
      - { type: issue, check: completeness, detail: "Missing edge case: empty agent pool", severity: minor }
    verdict: pass_with_notes
    reviewer_confidence: 0.85

  # === ARTIFACTS ===
  artifacts:
    files_created: [...]
    files_modified: [...]
    memory_stored: [...]
    decisions_made: [...]

  # === METRICS ===
  metrics:
    tokens_used: 45000
    agents_spawned: 3
    time_elapsed: "12m30s"
    topology_switches: 0
    review_rounds: 1
```

### 6.3 Task Parking and Resumption

```yaml
# Task parking protocol
task_parking:
  trigger: "Human requests context switch OR higher-priority task arrives OR resource constraint"
  process:
    1. Snapshot current task state to state/tasks/parked/{task_id}/
       - Active agent contexts
       - Intermediate results
       - Pending sub-tasks
       - Coordination state (pressure fields, quorum)
    2. Log park event to task timeline
    3. Despawn or reassign agents
    4. Update state/tasks/focus.yaml with new active focus
    5. Display parked task list to human

  resume_process:
    1. Human selects task from parked list (or framework suggests based on priority/staleness)
    2. Load task snapshot from state/tasks/parked/{task_id}/
    3. Respawn agents with saved context
    4. Restore coordination state
    5. Log resume event
    6. Continue from last checkpoint

  # Focus management
  focus:
    active: "task-20260227-001"  # Currently focused task
    parked:
      - id: "task-20260226-003"
        title: "Implement MAP-Elites config archive"
        parked_at: "2026-02-26T18:00:00Z"
        reason: "Higher priority: stagnation detection needed first"
        progress: "60% — archive structure implemented, search not done"
      - id: "task-20260225-001"
        title: "Research reinforcement learning for topology routing"
        parked_at: "2026-02-25T14:00:00Z"
        reason: "Blocked on experiment infrastructure"
        progress: "30% — literature survey complete, experiment design pending"
```

---

## 7. Evolution Engine

### 7.1 Evolution Tiers

```yaml
# core/evolution.yaml
evolution_tiers:

  tier0_constitutional:
    what: "Constitutional axioms (CONSTITUTION.md)"
    who_can_modify: "Human supervisor only — manual edit"
    approval: "N/A — agents cannot touch this"
    protection: "Hash verification, excluded from evolution engine"
    rollback: "Git history"

  tier1_framework:
    what: "Core framework structure, topology router, evolution engine, audit system"
    who_can_modify: "Human approval required"
    approval: |
      1. Agent proposes change with rationale and evidence
      2. Quorum of 3+ agents must independently agree
      3. Human reviews proposal, quorum result, and evidence
      4. Human approves or rejects
      5. If approved: git commit with evolution ID
    safety: "Dry-run simulation before proposal"
    rollback: "Git revert to pre-evolution commit"

  tier2_organizational:
    what: "Role compositions, process rules, topology patterns, domain config"
    who_can_modify: "Quorum-approved (auto if quorum agrees)"
    approval: |
      1. Agent proposes change with rationale and evidence
      2. Quorum of 3+ agents independently evaluate
      3. If quorum agrees AND no axiom violation detected: auto-approved
      4. If quorum disagrees OR axiom conflict: escalate to human
      5. Git commit with evolution ID
    safety: "Constitutional check before commit"
    rollback: "Git revert"

  tier3_operational:
    what: "Agent prompts, behavioral descriptors, capability parameters, thresholds"
    who_can_modify: "Individual agents with evolution authority"
    approval: |
      1. Agent identifies improvement opportunity
      2. Agent proposes change with A/B evidence
      3. Auto-approved if no axiom violation and no authority escalation
      4. Git commit with evolution ID
    safety: "Axiom check only"
    rollback: "Git revert"
```

### 7.2 Evolution Lifecycle

```
OBSERVE → ATTRIBUTE → PROPOSE → EVALUATE → APPROVE → COMMIT → VERIFY → LOG

1. OBSERVE: Agent detects a problem or improvement opportunity
   - Performance metric declined
   - Stagnation detected
   - Scout reports anomaly
   - Task review reveals pattern
   - Human provides feedback

2. ATTRIBUTE: Root-cause analysis
   - What caused the issue?
   - Is it a one-time incident or recurring pattern?
   - Which component is responsible?
   - What evidence supports the attribution?

3. PROPOSE: Generate candidate fix
   - Specific file changes (with diff)
   - Expected improvement
   - Risk assessment
   - Tier classification

4. EVALUATE: Validation
   - Constitutional check (no axiom violations)
   - Diversity impact (will this reduce SRD below floor?)
   - Consistency check (conflicts with existing rules?)
   - If Tier 1-2: quorum evaluation

5. APPROVE: Gate
   - Tier 3: auto-approved if checks pass
   - Tier 2: quorum consensus required
   - Tier 1: human approval required
   - Tier 0: rejected (agents cannot modify)

6. COMMIT: Apply
   - Git commit with structured message:
     Evolution-ID: evo-{date}-{seq}
     Tier: {0-3}
     Component: {what changed}
     Rationale: {why}
     Evidence: {what triggered this}
     Approved-By: {human|quorum|auto}
   - File modifications applied

7. VERIFY: Post-commit check
   - Re-run constitutional hash check
   - Verify framework still functional
   - If verification fails: auto-rollback

8. LOG: Audit
   - Full evolution record to logs/evolution/
   - Memory stored for future reference
   - Links to triggering task/decision
```

### 7.3 Quorum Sensing Implementation

```yaml
quorum:
  minimum_voters: 3
  threshold: 0.67  # 2/3 must agree
  process:
    1. Proposal is broadcast to all agents with can_propose_evolution capability
    2. Each voter independently evaluates (no discussion before voting)
    3. Votes are sealed (agents cannot see others' votes until all submitted)
    4. After all votes collected, tally revealed
    5. If threshold met: approved
    6. If not met: rejected with individual rationales logged
  anti_gaming:
    - "Voters must be from different role compositions (no homogeneous quorum)"
    - "Scout agents always get a vote (anti-homogenization check)"
    - "Voters cannot see each other's evaluations before submitting"
```

### 7.4 MAP-Elites Configuration Archive

```yaml
# roles/archive/ — Behavioral archive of successful configurations
archive:
  behavioral_dimensions:
    axis_1: task_type  # research | engineering | creative | meta
    axis_2: complexity  # simple | moderate | complex | extreme
  cells:
    research_complex:
      best_config:
        topology: hierarchical_team
        roles: [orchestrator(opus), researcher(opus)x2, scout(sonnet), reviewer(opus)]
        performance: 0.87
        task_count: 14
    engineering_moderate:
      best_config:
        topology: pipeline
        roles: [orchestrator(sonnet), implementer(sonnet), reviewer(opus)]
        performance: 0.92
        task_count: 23
  update_rule: "Replace cell occupant only if new config's performance > existing"
  novelty_bonus: 0.1  # Configs with novel role combinations get a performance boost
```

---

## 8. Coordination Layer

### 8.1 Three Coordination Modes

The framework uses three coordination modes, selected by the topology router:

```
                    COORDINATION MODES
    ┌──────────────────────────────────────────┐
    │                                          │
    │  STIGMERGIC         QUORUM       DIRECT  │
    │  (cheapest)         (medium)    (richest) │
    │                                          │
    │  Shared files       Sealed votes Messages │
    │  Pressure fields    Thresholds   Task     │
    │  Implicit           Collective   lists    │
    │  coordination       decisions    Teams    │
    │                                          │
    │  Best for:          Best for:    Best for:│
    │  Parallel swarms    Evolution    Tight    │
    │  Exploration        High-stakes  collab   │
    │  Low overhead       Safety       Complex  │
    │                     decisions    handoffs │
    └──────────────────────────────────────────┘
```

### 8.2 Stigmergic Coordination (Pressure Fields)

Inspired by Rodriguez (2026): agents leave traces in shared files that influence other agents' behavior without direct messages.

```yaml
# state/coordination/pressure_fields/
# Each file is a "pressure field" — a structured artifact agents read and write

# Example: exploration_pressure.yaml
exploration_pressure:
  updated: "2026-02-27T06:45:00Z"
  regions:
    diversity_metrics:
      explored_by: [agent-001, agent-003]
      saturation: 0.7  # well-explored
      last_novel_finding: "2026-02-27T06:30:00Z"
    stagnation_detection:
      explored_by: [agent-002]
      saturation: 0.3  # under-explored
      last_novel_finding: "2026-02-27T06:40:00Z"
    topology_routing:
      explored_by: []
      saturation: 0.0  # unexplored
      last_novel_finding: null

# Agents reading this file are naturally drawn toward low-saturation regions
# No explicit "go explore topology_routing" message needed
```

### 8.3 Direct Messaging Protocol

For tight coordination (hierarchical teams, complex handoffs):

```yaml
message_protocol:
  types:
    task_assignment: "Orchestrator → Worker: here's your task"
    status_update: "Worker → Orchestrator: progress report"
    review_request: "Worker → Reviewer: please review this output"
    review_result: "Reviewer → Orchestrator: findings"
    escalation: "Any → Orchestrator: I'm blocked / found an anomaly"
    anomaly_report: "Scout → Orchestrator: found something unexpected"
    evolution_proposal: "Any → Quorum: proposed change"
  constraints:
    - "Messages are logged to audit trail"
    - "Messages include sender role and authority level"
    - "Workers cannot message other workers directly (prevents unaudited side-channels)"
    - "Exception: debate topology allows structured peer-to-peer"
```

---

## 9. Diversity Enforcement

### 9.1 System Reasoning Diversity (SRD) Metric

Analog to Bettini et al.'s System Neural Diversity for LLM agents.

```yaml
# core/diversity.yaml
diversity:
  metric: SRD  # System Reasoning Diversity
  measurement:
    method: |
      For each task, collect all agent outputs.
      Compute pairwise semantic distance (embedding cosine distance).
      SRD = mean pairwise distance across all agent pairs.
      Higher SRD = more diverse reasoning.
    frequency: "After every task completion"
    storage: "logs/diversity/{date}.jsonl"

  thresholds:
    floor: 0.3        # Below this: ALERT — diversity collapse (Axiom A6)
    healthy: 0.5-0.7   # Normal operating range
    ceiling: 0.9       # Above this: possible incoherence (agents too divergent)

  interventions:
    below_floor:
      - "ALERT human supervisor"
      - "Spawn scout agent with divergent role composition"
      - "Inject novelty: randomly perturb agent behavioral descriptors"
      - "Force role switch: convert most-conforming agent to scout"
    above_ceiling:
      - "Increase structured debate rounds"
      - "Assign integration task to orchestrator"
      - "Reduce exploration_vs_exploitation ratio across agents"
```

### 9.2 Stagnation Detection

```yaml
stagnation:
  signals:
    agent_level:
      - "Agent produces output semantically similar to its last 3 outputs (cosine > 0.9)"
      - "Agent hasn't proposed a novel idea in N tasks"
    team_level:
      - "All agents agree on first round of debate (no productive disagreement)"
      - "SRD drops below 0.4 for 3 consecutive tasks"
    framework_level:
      - "No Tier 2+ evolution in 10 tasks"
      - "Same topology selected for 10 consecutive tasks"
      - "MAP-Elites archive hasn't had a cell replacement in 20 tasks"

  response:
    1. Log stagnation signal to logs/diversity/
    2. Spawn scout agent if none active
    3. Perturb: randomly modify one agent's behavioral descriptors
    4. If persistent: force topology switch (try a pattern not used recently)
    5. If still persistent: escalate to human
```

### 9.3 Anti-Homogenization Mechanisms

From our swarm diversity research (Aspects K, L, M, N):

| Mechanism | Biological Analog | Implementation |
|-----------|-------------------|----------------|
| Structural diversity | Polyandry | Different model tiers, temperatures, system prompts |
| Negative feedback | Pheromone evaporation | Decay overused reasoning patterns in memory |
| Active repulsion | Charged PSO | Penalize agents for repeating prior agents' conclusions |
| Novelty reward | Novelty search | Scout agents rewarded for novel findings, not correctness |
| Forced exploration | Scout bees | Stagnation → convert worker to scout |
| Niching | Fitness sharing | Agents specialize in behavioral niches, no niche dominates |

---

## 10. Audit System

### 10.1 Log Structure

Three parallel, append-only JSONL log streams:

```
logs/
├── evolution/
│   └── evolution.jsonl      # Every framework change
├── tasks/
│   └── tasks.jsonl          # Every task lifecycle event
├── decisions/
│   └── decisions.jsonl      # Every significant decision
└── diversity/
    └── diversity.jsonl      # Diversity metrics over time
```

### 10.2 Evolution Log Entry

```jsonl
{
  "id": "evo-20260227-001",
  "timestamp": "2026-02-27T06:45:00Z",
  "tier": 3,
  "component": "roles/compositions/researcher.yaml",
  "change_type": "modify",
  "diff": "- exploration_vs_exploitation: 0.4\n+ exploration_vs_exploitation: 0.5",
  "rationale": "Researcher agents have been too conservative; increasing exploration tendency based on 5 consecutive tasks where novel approaches were missed",
  "evidence": {
    "triggering_tasks": ["task-20260226-003", "task-20260226-005"],
    "metric": "SRD dropped from 0.55 to 0.38 over these tasks"
  },
  "approved_by": "auto (tier 3)",
  "constitutional_check": "pass",
  "diversity_impact": "SRD expected to increase by ~0.05",
  "rollback_commit": "abc123f"
}
```

### 10.3 Task Log Entry

```jsonl
{
  "id": "task-20260227-001",
  "event": "review_complete",
  "timestamp": "2026-02-27T07:00:00Z",
  "task_title": "Implement stagnation detection",
  "actor": "agent-003",
  "actor_role": "reviewer",
  "detail": {
    "verdict": "pass_with_notes",
    "findings_count": { "pass": 4, "issue_minor": 1, "issue_major": 0 },
    "specific_issues": ["Missing edge case: empty agent pool"],
    "confidence": 0.85
  },
  "artifacts_reviewed": ["core/diversity.yaml", "tools/diversity-check.sh"],
  "tokens_used": 8500
}
```

### 10.4 Decision Log Entry

```jsonl
{
  "id": "dec-20260227-001",
  "timestamp": "2026-02-27T06:35:00Z",
  "decision_type": "topology_selection",
  "actor": "topology-router",
  "actor_type": "system",  # human|agent|system
  "context": "Task: Implement stagnation detection",
  "options_considered": [
    { "option": "solo", "score": 0.3, "reason": "Task has subtasks" },
    { "option": "pipeline", "score": 0.5, "reason": "Sequential dependency" },
    { "option": "hierarchical_team", "score": 0.8, "reason": "Moderate complexity, needs review" }
  ],
  "selected": "hierarchical_team",
  "rationale": "Task has decomposable subtasks with review requirement; hierarchical team provides best quality/cost ratio",
  "overridden_by": null
}
```

### 10.5 Audit Viewer

A CLI tool that renders logs in human-readable format:

```bash
# tools/audit-viewer.sh
# Usage:
#   ./audit-viewer.sh evolution [--since 2026-02-27] [--tier 1,2]
#   ./audit-viewer.sh tasks [--status complete] [--task-id task-001]
#   ./audit-viewer.sh decisions [--actor human] [--type topology_selection]
#   ./audit-viewer.sh diversity [--plot]  # ASCII chart of SRD over time
#   ./audit-viewer.sh timeline [--since 2026-02-27]  # Unified chronological view
#   ./audit-viewer.sh task-detail task-001  # Full lifecycle view of one task
```

Example output for `task-detail`:

```
═══════════════════════════════════════════════════════════
 TASK: task-20260227-001 — Implement stagnation detection
═══════════════════════════════════════════════════════════

 Origin:  scout-agent-003 (agent_generated)
 Reason:  Diversity metric dropped below threshold
 Priority: HIGH

 ── LIFECYCLE ──────────────────────────────────────────
 06:30:00  INTAKE     scout-agent-003  → Anomaly reported
 06:32:00  ANALYSIS   topology-router  → hierarchical_team selected
 06:33:00  PLANNING   agent-001(orch)  → 3 subtasks created
 06:34:00  SPAWNED    agent-002(impl)  → implementer for core logic
 06:35:00  EXECUTING  agent-002(impl)  → Working on diversity.yaml...
 06:50:00  EXECUTING  agent-002(impl)  → Draft complete, requesting review
 06:51:00  REVIEWING  agent-003(rev)   → Review started
 06:58:00  VERDICT    agent-003(rev)   → PASS with notes (1 minor issue)
 07:00:00  COMPLETE   agent-001(orch)  → Task archived

 ── REVIEW ─────────────────────────────────────────────
 Reviewer: agent-003 (reviewer role, opus)
 Checks:  [PASS] correctness  [PASS] completeness*  [PASS] consistency  [PASS] safety
 Note:    Missing edge case — empty agent pool (minor)
 Confidence: 85%

 ── DECISIONS ──────────────────────────────────────────
 dec-001: topology → hierarchical_team (scored 0.8 vs solo 0.3, pipeline 0.5)
 dec-002: model selection → opus for reviewer (quality-critical review)

 ── ARTIFACTS ──────────────────────────────────────────
 Modified: core/diversity.yaml, tools/diversity-check.sh
 Memory:   mem-abc123 (procedural: stagnation detection implementation)

 ── COST ───────────────────────────────────────────────
 Tokens: 45,000 | Agents: 3 | Duration: 30m | Review rounds: 1
═══════════════════════════════════════════════════════════
```

---

## 11. Domain Instantiation

### 11.1 Domain Configuration

```yaml
# domain/active.yaml — loaded at bootstrap
domain:
  name: meta
  description: "Self-improvement — the framework's first job is making itself better"

  # Domain-specific capabilities injected into agents
  capabilities:
    framework_analysis:
      description: "Analyze framework components for improvement opportunities"
      instruction_fragment: |
        You are analyzing the Universal Agents framework itself.
        Look for: bottlenecks, missing capabilities, inefficient patterns,
        overly complex mechanisms, untested assumptions.
    evolution_design:
      description: "Design framework evolutions with safety analysis"
      instruction_fragment: |
        Design changes to the framework. For each change:
        1. Specify exact files and diffs
        2. Classify tier (0-3)
        3. Assess constitutional compliance
        4. Predict diversity impact
        5. Define rollback procedure

  # Domain-specific review criteria
  review_criteria:
    - "Does this change make the framework more capable?"
    - "Does this change preserve or improve auditability?"
    - "Does this change respect constitutional axioms?"
    - "Could this change cause cascading failures?"

  # Domain-specific task types
  task_types:
    - framework_analysis
    - capability_implementation
    - evolution_proposal
    - literature_research
    - experiment_design
    - experiment_execution
    - retrospective
```

### 11.2 Domain Templates

```yaml
# domain/templates/research_lab.yaml
domain:
  name: research_lab
  description: "AI/ML research laboratory"
  capabilities:
    literature_review: { ... }
    hypothesis_generation: { ... }
    experiment_design: { ... }
    statistical_analysis: { ... }
  review_criteria:
    - "Is the methodology sound?"
    - "Are results statistically significant?"
    - "Is the literature properly cited?"
  task_types:
    - literature_review
    - hypothesis_generation
    - experiment_design
    - experiment_execution
    - paper_writing
```

```yaml
# domain/templates/software_engineering.yaml
domain:
  name: software_engineering
  description: "Software product development"
  capabilities:
    code_implementation: { ... }
    code_review: { ... }
    testing: { ... }
    architecture_design: { ... }
  review_criteria:
    - "Do all tests pass?"
    - "Is the code secure (OWASP top 10)?"
    - "Does it follow existing patterns?"
  task_types:
    - feature_implementation
    - bug_fix
    - refactoring
    - testing
    - deployment
```

### 11.3 Domain Switching

```
1. Human: "Switch to software_engineering domain"
2. Framework saves current domain state
3. Load domain/templates/software_engineering.yaml → domain/active.yaml
4. Regenerate agent instructions with new domain capabilities
5. Update review criteria
6. Log domain switch to decisions log
7. Existing tasks tagged with previous domain
```

---

## 12. Directory Structure

```
universal-agents/
├── CONSTITUTION.md                    # Immutable axioms (human-only edits)
├── CLAUDE.md                          # Bootstrap instructions for Claude Code
├── framework.yaml                     # Core framework configuration
│
├── core/                              # Framework engine definitions
│   ├── lifecycle.yaml                 # Task lifecycle state machine
│   ├── evolution.yaml                 # Evolution tiers and rules
│   ├── topology.yaml                  # Topology patterns and routing
│   ├── diversity.yaml                 # Diversity metrics and thresholds
│   ├── coordination.yaml              # Coordination modes
│   └── audit.yaml                     # Audit configuration
│
├── roles/                             # Composable role system
│   ├── capabilities.yaml              # Atomic capability definitions
│   ├── compositions/                  # Role = capability compositions
│   │   ├── orchestrator.yaml
│   │   ├── researcher.yaml
│   │   ├── implementer.yaml
│   │   ├── reviewer.yaml
│   │   ├── scout.yaml
│   │   └── debater.yaml
│   └── archive/                       # MAP-Elites config archive
│       └── archive.yaml
│
├── domain/                            # Domain instantiation
│   ├── active.yaml                    # Current domain configuration
│   └── templates/                     # Domain templates
│       ├── meta.yaml                  # Self-improvement
│       ├── research_lab.yaml
│       ├── software_engineering.yaml
│       └── game_studio.yaml
│
├── state/                             # Persistent organizational state
│   ├── organization.yaml              # Current org structure and active agents
│   ├── agents/                        # Agent instances
│   │   └── registry.yaml              # Active agent registry
│   ├── tasks/                         # Task management
│   │   ├── focus.yaml                 # Current focus and parked task list
│   │   ├── active/                    # Currently executing tasks
│   │   ├── parked/                    # Parked (context-switched) tasks
│   │   └── completed/                 # Completed tasks (with full audit)
│   └── coordination/                  # Coordination state
│       ├── pressure_fields/           # Stigmergic artifacts
│       └── quorum/                    # Pending and completed quorum votes
│
├── logs/                              # Complete audit trail (append-only JSONL)
│   ├── evolution/
│   │   └── evolution.jsonl
│   ├── tasks/
│   │   └── tasks.jsonl
│   ├── decisions/
│   │   └── decisions.jsonl
│   └── diversity/
│       └── diversity.jsonl
│
├── memory/                            # Organizational memory supplements
│   ├── patterns.yaml                  # Discovered successful patterns
│   ├── failures.yaml                  # Known failure modes and fixes
│   └── innovations.yaml              # Successful innovations
│
└── tools/                             # Utility scripts
    ├── bootstrap.sh                   # Framework initialization
    ├── spawn-agent.sh                 # Agent spawning helper
    ├── park-task.sh                   # Task parking
    ├── resume-task.sh                 # Task resumption
    ├── evolve.sh                      # Manual evolution trigger
    ├── audit-viewer.sh                # Audit log viewer CLI
    ├── diversity-check.sh             # Diversity metric computation
    └── domain-switch.sh               # Domain switching
```

---

## 13. Meta Bootstrap — The Self-Improvement Loop

Since the first domain is `meta`, the framework's initial task list is:

```
PHASE 1: Foundation (Framework implements its own core)
  Task 1: Implement CONSTITUTION.md with hash verification
  Task 2: Implement task lifecycle state machine
  Task 3: Implement audit logging (JSONL writers)
  Task 4: Implement basic role composition and agent spawning
  Task 5: Implement basic topology routing (start with 2 patterns)

PHASE 2: Self-Awareness (Framework measures itself)
  Task 6: Implement SRD diversity metric
  Task 7: Implement stagnation detection
  Task 8: Implement audit viewer (CLI)
  Task 9: Implement task parking/resumption

PHASE 3: Self-Evolution (Framework improves itself)
  Task 10: Implement evolution engine (Tier 3 auto-evolution first)
  Task 11: Implement quorum sensing for Tier 2
  Task 12: Implement MAP-Elites configuration archive
  Task 13: Implement pressure field coordination

PHASE 4: Self-Expansion (Framework discovers what it's missing)
  Task 14: Spawn scout agents to find framework weaknesses
  Task 15: First autonomous Tier 2 evolution (quorum-approved)
  Task 16: Cross-domain validation (switch to research_lab, verify portability)
  Task 17: Performance benchmarking against ai-lab-agents on equivalent task

PHASE ∞: Continuous self-improvement loop
  - Scout agents find problems
  - Framework proposes and evaluates fixes
  - Successful fixes are committed and verified
  - Configuration archive grows
  - Topology routing improves with experience
  - The loop accelerates as the framework becomes more capable
```

### 13.1 The Bootstrapping Paradox

The framework cannot use its own evolution engine to build itself — it doesn't exist yet. Resolution:

```
Phase 1-2: Human + single Claude Code agent build the foundation manually
Phase 3:   The evolution engine is the first thing that evolves itself
Phase 4+:  Framework operates autonomously with human oversight
```

This mirrors biological abiogenesis: simple chemistry → self-replicating molecules → cells → complex organisms. The framework bootstraps from simple to complex.

### 13.2 ASI Trajectory

The path from framework to ASI bootstrapping:

```
Level 0: Framework runs tasks assigned by human
         (current ai-lab-agents level)

Level 1: Framework discovers its own improvement opportunities
         (scout agents, stagnation detection)

Level 2: Framework improves itself with human oversight
         (tiered evolution, quorum approval)

Level 3: Framework improves its own improvement mechanism
         (meta-evolution — evolution engine evolves itself)

Level 4: Framework discovers new domains and capabilities
         (domain switching, capability generation)

Level 5: Framework's rate of self-improvement accelerates
         (the improvement loop gets faster each cycle)

Level N: The framework can solve problems that no human
         could have anticipated or specified
```

Each level requires the previous level to be stable and verified. The audit trail ensures that every step is traceable and reversible.

---

## 14. Key Differences from Prior Art

| Feature | ai-lab-agents | ai-game-studio | CrewAI | AutoGen | This Framework |
|---------|--------------|----------------|--------|---------|---------------|
| Domain portability | No (research) | No (games) | Partial | Yes | Yes (domain configs) |
| Role switching | No | No | No | Limited | Native (composable) |
| Dynamic topology | No (fixed hierarchy) | No | No | Partial | Yes (6 patterns + auto-routing) |
| Self-evolution | Manual (IDOE) | Manual | No | No | Tiered (auto + quorum + human) |
| Diversity enforcement | No | No | No | No | Built-in (SRD + stagnation + scouts) |
| Task parking | No | No | No | No | Yes (full context snapshot) |
| Stigmergic coordination | Partial (dashboard.md) | Partial | No | No | Yes (pressure fields) |
| Full audit trail | Partial (changelog) | Partial | No | Partial | Yes (4 JSONL streams + viewer) |
| Constitutional safety | No | No | No | No | Yes (hash-verified immutable axioms) |
| Quorum decisions | No | No | No | No | Yes (sealed votes, diversity requirement) |
| MAP-Elites archive | No | No | No | No | Yes (behavioral config archive) |
| Meta-evolution | No | No | No | No | Yes (evolution engine evolves itself) |

---

## 15. Risk Analysis

| Risk | Severity | Mitigation |
|------|----------|------------|
| Evolution introduces bugs | High | Constitutional check, quorum gate, auto-rollback, review mandate |
| Diversity collapse | Medium | SRD metric, floor axiom (A6), stagnation detection, forced scouts |
| Token cost explosion | Medium | Resource monitor (A8), prefer-fewer-stronger, topology routing |
| Framework becomes too complex | Medium | Simplicity principle, periodic retrospectives, complexity metrics |
| Audit log bloat | Low | Log rotation, compression, summary generation |
| Constitutional bypass | Critical | Hash verification, excluded from evolution engine, human-only edits |
| Quorum gaming | Medium | Sealed votes, diversity requirement, scout always votes |
| Task parking context loss | Low | Full context snapshots, git-based state |
| Rate limit bottleneck | Medium | Adaptive scaling, backoff, queue-based scheduling |

---

*End of Design Document — Universal Agents Framework v0.1*
*Research basis: 5 prior literature reviews (self-evolving agents, gap analysis, swarm diversity K+L, abductive reasoning M+N, teams vs swarms)*
