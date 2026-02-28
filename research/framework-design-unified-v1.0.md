# Universal Agents Framework — Unified Design Specification

**Version:** 1.0 (Consolidated from v0.1 + v0.2 addendum + v0.3 research integration)
**Date:** 2026-02-27
**Status:** Design complete — ready for implementation
**First Domain:** Meta (self-improvement)
**Research Base:** ~190 papers across 8 literature reviews

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Constitutional Invariants](#2-constitutional-invariants)
3. [Architecture Overview](#3-architecture-overview)
4. [Role System — Composable Capabilities](#4-role-system)
5. [Topology Router — Teams/Swarms Balance](#5-topology-router)
6. [Task Lifecycle — Full Audit](#6-task-lifecycle)
7. [Evolution Engine](#7-evolution-engine)
8. [Dual-Copy Bootstrapping](#8-dual-copy-bootstrapping)
9. [Coordination Layer](#9-coordination-layer)
10. [Diversity Enforcement](#10-diversity-enforcement)
11. [Creativity Engine](#11-creativity-engine)
12. [Skills System — Crystallized Capabilities](#12-skills-system)
13. [Self-Capability Awareness](#13-self-capability-awareness)
14. [Self-Governance](#14-self-governance)
15. [Meta-Analysis & Self-Audit](#15-meta-analysis)
16. [Autonomous Run Loop](#16-autonomous-run-loop)
17. [Audit System & Viewers](#17-audit-system)
18. [Domain Instantiation & Switching](#18-domain-instantiation)
19. [Migration from Existing Organizations](#19-migration)
20. [Directory Structure](#20-directory-structure)
21. [Meta Bootstrap Sequence](#21-meta-bootstrap)
22. [Key Differences from Prior Art](#22-differences)
23. [Risk Analysis](#23-risk-analysis)
24. [Research Reference Summary](#24-research-references)

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
| Topology | Fixed hierarchy | Dynamic per-task (6 patterns + auto-routing) |
| Evolution | Manual (IDOE, human edits) | Tiered (auto → quorum → human) |
| Task mgmt | Session-scoped | Persistent with park/resume |
| Audit | Partial (process rules changelog) | Complete (every action logged) |
| Diversity | Not measured | Built-in SRD metric |
| Coordination | Explicit messaging only | Stigmergic + quorum + messaging |
| Creativity | Not structured | Evidence-based creative protocol |
| Skills | Static instructions | Experience-grounded crystallization |
| Self-awareness | None | Capability maps + calibration |

### 1.3 Guiding Principles

1. **Complexity only when it improves outcomes** (Anthropic's principle)
2. **Fail loud, never silent** (from CLAUDE.md defensive coding)
3. **Measure before you manage** (diversity, stagnation, cost)
4. **Everything is a file** — git-trackable, human-readable, portable
5. **The framework eats its own dogfood** — meta domain first
6. **Structure > individual capability** — multi-agent with good structure beats single powerful agent (FilmAgent 2025)
7. **Extract, don't generate** — skills from experience, not imagination (SkillsBench 2026)
8. **Verification must exceed generation** — the fundamental limit of self-improvement (Song et al. 2024)

---

## 2. Constitutional Invariants

### 2.1 Three-Layer Constitution

```
LAYER 0: GLOBAL CONSTITUTION (CONSTITUTION.md)
  │  Immutable axioms that apply everywhere.
  │  Human-only edits.
  │
  ├── LAYER 1: DOMAIN CHARTER (instances/{name}/CHARTER.md)
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

### 2.2 Global Axioms

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

### 2.3 Domain Charter Example

```yaml
# instances/research_lab/CHARTER.md
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

### 2.4 Constitution Enforcement

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

## 3. Architecture Overview

### 3.1 Layer Model

```
┌──────────────────────────────────────────────────────┐
│                  HUMAN SUPERVISOR                     │
│          (veto, high-risk approval, direction)        │
├──────────────────────────────────────────────────────┤
│              SELF-GOVERNANCE                          │
│    Objective anchoring │ Alignment verification       │
├──────────────────────────────────────────────────────┤
│              EVOLUTION ENGINE (Tier 0-3)              │
│    Constitutional guard │ Quorum gate │ Auto-evolve   │
│    Dual-copy fork→evaluate→promote pipeline           │
├──────────────────────────────────────────────────────┤
│              CREATIVITY ENGINE                        │
│    Separate-Then-Together │ Anti-stagnation │ Metrics  │
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
│              SKILLS LIBRARY                           │
│    Experience-grounded │ 4-stage validation │ Secured  │
├──────────────────────────────────────────────────────┤
│              SELF-AWARENESS                           │
│    Capability map │ Calibration │ Meta-analysis        │
├──────────────────────────────────────────────────────┤
│              AUDIT & MEMORY                           │
│    Evolution│Task│Decision│Diversity│Creativity logs   │
│    Terminal tree viewer │ HTML interactive viewer      │
├──────────────────────────────────────────────────────┤
│              INFRASTRUCTURE                           │
│    Claude Code │ Claude Max OAuth │ File system │ Git  │
└──────────────────────────────────────────────────────┘
```

### 3.2 Claude Code Integration

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
   c. instances/{active}/CHARTER.md → current domain charter
   d. instances/{active}/state/organization.yaml → current org structure
   e. instances/{active}/state/tasks/active/ → any active task contexts
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
  # These are injected at runtime based on active domain
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
    exploration_vs_exploitation: 0.3
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
    exploration_vs_exploitation: 0.9
  authority_level: 0
  forbidden:
    - "Must not converge on consensus — your job is to disagree"
    - "Must not optimize existing solutions — find new problems"
  scout_config:
    stagnation_trigger: true
    anomaly_reporting: true
    negative_selection: true
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

```yaml
role_switch:
  trigger: "Orchestrator assigns new role OR stagnation detected OR task requires it"
  process:
    1. Agent saves current context to state/agents/{id}/context_snapshot.yaml
    2. Agent loads new role composition from roles/compositions/{new_role}.yaml
    3. Agent re-reads domain-specific capabilities from active domain
    4. Agent logs role switch to logs/decisions/
    5. Agent continues with new behavioral descriptors
  constraints:
    - "Cannot switch to authority_level higher than current without orchestrator approval"
    - "Scout role can only be assigned, not self-selected (prevents gaming)"
    - "Role switch is logged as a decision with reason"
```

### 4.4 Rapid Agent Spawning

```
spawn_agent(role_name, task_context) →
  1. Load roles/compositions/{role_name}.yaml
  2. Load roles/capabilities.yaml for each listed capability
  3. Concatenate instruction fragments into agent prompt
  4. Inject domain-specific context from active domain config
  5. Inject task context (curated, not raw dump)
  6. Select model tier from role config
  7. Call Claude Code Task tool with composed prompt
  8. Register agent in state/agents/registry.yaml
  9. Log spawn to logs/decisions/
```

### 4.5 Role Lifecycle (Creation, Adaptation, Deprecation)

```yaml
role_lifecycle:

  creation:
    triggers:
      - "Meta-analysis identifies recurring capability gap"
      - "Scout discovers need for capability that no existing role covers"
      - "Human requests new role"
      - "Task fails because no suitable role exists"
    process:
      1. IDENTIFY: What capability is missing? What tasks would benefit?
      2. COMPOSE: Select capability atoms that address the gap
      3. DEFINE: Write role composition YAML
      4. VALIDATE: Constitutional check, diversity check, quorum evaluation
      5. TEST: Assign to a real task in trial mode
      6. COMMIT: If trial succeeds, add to roles/compositions/
      7. ARCHIVE: Add to MAP-Elites archive
    evolution_tier: 2  # New role creation requires quorum approval

  adaptation:
    triggers:
      - "Role performance declining over N tasks"
      - "Review findings reveal consistent weakness"
      - "Environment changed (new tools, new domain capabilities)"
    process:
      1. DIAGNOSE → 2. PROPOSE → 3. EVALUATE → 4. APPLY → 5. VERIFY
    evolution_tier: 3  # Role adaptation is operational (auto-evolve)

  deprecation:
    triggers:
      - "Role unused for 20+ tasks"
      - "Role consistently outperformed by another role on same tasks"
    process:
      1. PROPOSE → 2. QUORUM (Tier 2) → 3. ARCHIVE (to deprecated/) → 4. MIGRATE
    evolution_tier: 2  # Role deprecation requires quorum
```

---

## 5. Topology Router — Teams/Swarms Balance

### 5.1 Task Analysis

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

### 5.2 Six Topology Patterns

```yaml
topology_patterns:

  solo:
    when: { decomposability: monolithic, scale: single }
    structure: "Single agent with appropriate role"
    agents: 1
    overhead: minimal

  pipeline:
    when: { decomposability: partially_decomposable, interdependency: tightly_coupled }
    structure: "Sequential chain — each agent's output feeds the next"
    agents: 2-4
    pattern: "A → B → C → Review"

  parallel_swarm:
    when: { decomposability: fully_decomposable, interdependency: independent, exploration_vs_execution: pure_exploration }
    structure: "Parallel agents, results aggregated"
    agents: 3-8 (resource-dependent)
    pattern: "Spawn N → Execute in parallel → Aggregate → Review"
    coordination: stigmergic

  hierarchical_team:
    when: { interdependency: loosely_coupled, quality_criticality: correctness_priority }
    structure: "Orchestrator + specialized workers"
    agents: 3-6
    pattern: "Orchestrator decomposes → Workers execute → Orchestrator synthesizes → Review"
    coordination: explicit

  hybrid:
    when: { decomposability: partially_decomposable, exploration_vs_execution: mixed }
    structure: "Orchestrator + parallel explorers + sequential executors"
    agents: 4-10
    pattern: "Orchestrator → {Explore swarm || Execute pipeline} → Synthesize → Review"
    coordination: mixed

  debate:
    when: { novelty: novel, quality_criticality: correctness_priority }
    structure: "Multiple agents argue, judge decides"
    agents: 3-5
    pattern: "Proposers(N) → Debate rounds → Judge → Review"
    coordination: structured_debate

resource_scaling:
  check_before_spawn: true
  max_concurrent_agents: "auto"
  backoff_on_rate_limit: true
  prefer_fewer_stronger: true  # 3 opus > 8 haiku for most tasks
```

### 5.3 Routing Algorithm

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
  status: executing

  # === WHAT ===
  title: "Implement stagnation detection for diversity monitor"
  description: "..."
  origin:
    type: agent_generated  # human|agent_generated|evolution_triggered|scout_discovery
    source: "scout-agent-003"
    reason: "Diversity metric dropped below threshold for 3 consecutive checks"

  # === WHY ===
  rationale: "Without stagnation detection, the framework cannot self-correct diversity collapse"
  priority: high
  links:
    parent_task: null
    blocks: ["task-20260227-003"]
    blocked_by: []
    related_evolution: "evo-20260227-001"

  # === MANDATE ===
  mandate:
    motto: null  # optional per-task motto
    constraints: []
    relaxed_rules: []

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
    - { time: "...", event: executing, actor: agent-002, detail: "..." }

  # === REVIEW ===
  review:
    reviewer: "agent-003"
    reviewer_role: reviewer
    findings: [...]
    verdict: pass_with_notes
    reviewer_confidence: 0.85

  # === ARTIFACTS & METRICS ===
  artifacts: { files_created: [...], files_modified: [...] }
  metrics: { tokens_used: 45000, agents_spawned: 3, time_elapsed: "12m30s", review_rounds: 1 }
```

### 6.3 Task Parking and Resumption

```yaml
task_parking:
  trigger: "Human requests context switch OR higher-priority task arrives OR resource constraint"
  process:
    1. Snapshot current task state to state/tasks/parked/{task_id}/
    2. Log park event to task timeline
    3. Despawn or reassign agents
    4. Update state/tasks/focus.yaml with new active focus
    5. Display parked task list to human

  resume_process:
    1. Human selects task from parked list (or framework suggests based on priority/staleness)
    2. Load task snapshot
    3. Respawn agents with saved context
    4. Restore coordination state
    5. Log resume event
    6. Continue from last checkpoint

  focus:
    active: "task-20260227-001"
    parked:
      - id: "task-20260226-003"
        title: "Implement MAP-Elites config archive"
        parked_at: "2026-02-26T18:00:00Z"
        reason: "Higher priority: stagnation detection needed first"
        progress: "60%"
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
    protection: "Hash verification, excluded from evolution engine"

  tier1_framework:
    what: "Core framework structure, topology router, evolution engine, audit system"
    who_can_modify: "Human approval required"
    approval: "Agent proposes → Quorum of 3+ agrees → Human approves → Git commit"
    safety: "Dry-run simulation before proposal"

  tier2_organizational:
    what: "Role compositions, process rules, topology patterns, domain config"
    who_can_modify: "Quorum-approved (auto if quorum agrees)"
    approval: "Agent proposes → Quorum of 3+ evaluates → Auto-approved if no axiom violation"
    safety: "Constitutional check before commit"

  tier3_operational:
    what: "Agent prompts, behavioral descriptors, capability parameters, thresholds"
    who_can_modify: "Individual agents with evolution authority"
    approval: "Auto-approved if no axiom violation and no authority escalation"
    safety: "Axiom check only"
```

### 7.2 Evolution Lifecycle

```
OBSERVE → ATTRIBUTE → PROPOSE → EVALUATE → APPROVE → COMMIT → VERIFY → LOG

1. OBSERVE: Detect problem or improvement opportunity
2. ATTRIBUTE: Root-cause analysis with evidence
3. PROPOSE: Generate candidate fix with specific diffs, tier, risk
4. EVALUATE: Constitutional check, diversity impact, consistency check
5. APPROVE: Tier 3=auto | Tier 2=quorum | Tier 1=human | Tier 0=rejected
6. COMMIT: Git commit with structured message (Evolution-ID, Tier, Rationale, Approved-By)
7. VERIFY: Re-run constitutional hash check, verify framework functional
8. LOG: Full evolution record to logs/evolution/
```

### 7.3 Quorum Sensing

```yaml
quorum:
  minimum_voters: 3
  threshold: 0.67  # 2/3 must agree
  process:
    1. Proposal broadcast to all agents with can_propose_evolution capability
    2. Each voter independently evaluates (no discussion before voting)
    3. Votes are sealed (agents cannot see others' votes until all submitted)
    4. After all votes collected, tally revealed
    5. If threshold met: approved; if not: rejected with rationales logged
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
    axis_1: task_type   # research | engineering | creative | meta
    axis_2: complexity  # simple | moderate | complex | extreme
  cells:
    research_complex:
      best_config:
        topology: hierarchical_team
        roles: [orchestrator(opus), researcher(opus)x2, scout(sonnet), reviewer(opus)]
        performance: 0.87
        task_count: 14
  update_rule: "Replace cell occupant only if new config's performance > existing"
  novelty_bonus: 0.1
```

---

## 8. Dual-Copy Bootstrapping

### 8.1 The Generation-Verification Gap

**Fundamental limit (Song et al. 2024):** A system can only improve itself to the extent its verification exceeds its generation capability. The framework must ensure evaluation mechanisms are always more reliable than self-modification proposals.

### 8.2 The Dual-Copy Pattern

Resolves the bootstrapping paradox: how to improve yourself with yourself. Validated by Darwin Godel Machine (20%→50% SWE-bench), STOP (Microsoft), ADAS (ICLR 2025), AlphaEvolve (DeepMind).

```yaml
# core/evolution-bootstrap.yaml
dual_copy_evolution:

  architecture:
    separation_of_concerns:
      base_layer: "LLM weights — NEVER modified (Claude API is fixed)"
      orchestration_layer: "Agent code, prompts, workflows — self-modified"
      evaluation_layer: "Verification, testing, benchmarking — independent from modification"
      governance_layer: "Constitution, safety — co-evolved with safeguards"

  process:
    1_fork:
      description: "Create a copy of current framework configuration"
      what_is_copied:
        - "roles/compositions/*.yaml"
        - "core/*.yaml (topology, coordination, etc.)"
        - "domain config"
      what_is_NOT_copied:
        - "CONSTITUTION.md (immutable, shared)"
        - "logs/ (append-only, shared)"
        - "state/tasks/ (belongs to the running instance)"
      storage: "state/evolution/candidates/{evo-id}/"

    2_modify:
      description: "Apply proposed changes to the fork"
      constraints:
        - "Only Tier 2-3 changes (Tier 0-1 require separate process)"
        - "Changes must be expressible as file diffs"
        - "Changes must pass constitutional check"

    3_evaluate:
      description: "Test the fork against multi-dimensional criteria"
      dimensions:
        capability: "Does it perform tasks better?"
        consistency: "Does it produce similar results across runs? (3x repetition)"
        robustness: "Does it handle edge cases?"
        predictability: "Can we anticipate when it will fail?"
        safety: "Does it stay within constitutional bounds?"
        diversity: "Does it maintain SRD above floor?"
      method: "Run test tasks against both current and forked configs, compare metrics"

    4_promote_or_rollback:
      all_pass: "Promote: replace current config with fork"
      any_fail: "Rollback: discard fork, log failure reason"
      marginal: "Hold for human review if improvement is within noise"
      promotion_steps:
        1. "Git commit current state (rollback point)"
        2. "Copy fork configs to active positions"
        3. "Verify framework still operational"
        4. "If verification fails: auto-rollback"
        5. "Log promotion with full evaluation results"

  population_mode:
    description: "Generate multiple candidate forks, evaluate all, select best"
    when: "Major evolution (Tier 1-2) or when single-fork improvement stalls"
    population_size: 3-5
    selection: "Tournament: best fork wins across multi-dimensional evaluation"
    rationale: "DGM: population-based outperforms single-point mutation"
```

---

## 9. Coordination Layer

### 9.1 Three Coordination Modes

```
                COORDINATION MODES
    ┌──────────────────────────────────────────┐
    │  STIGMERGIC         QUORUM       DIRECT  │
    │  (cheapest)         (medium)    (richest) │
    │                                          │
    │  Shared files       Sealed votes Messages │
    │  Pressure fields    Thresholds   Tasks    │
    │  Implicit           Collective   Teams    │
    │  coordination       decisions             │
    │                                          │
    │  Best for:          Best for:    Best for:│
    │  Parallel swarms    Evolution    Tight    │
    │  Exploration        Safety       collab   │
    │  Low overhead       decisions    Complex  │
    │                                  handoffs │
    └──────────────────────────────────────────┘
```

### 9.2 Stigmergic Coordination (Pressure Fields)

Inspired by Rodriguez (2026): agents leave traces in shared files that influence other agents' behavior without direct messages.

```yaml
# state/coordination/pressure_fields/exploration_pressure.yaml
exploration_pressure:
  updated: "2026-02-27T06:45:00Z"
  regions:
    diversity_metrics:
      explored_by: [agent-001, agent-003]
      saturation: 0.7  # well-explored
    stagnation_detection:
      explored_by: [agent-002]
      saturation: 0.3  # under-explored
    topology_routing:
      explored_by: []
      saturation: 0.0  # unexplored — agents naturally drawn here
```

### 9.3 Direct Messaging Protocol

```yaml
message_protocol:
  types:
    task_assignment: "Orchestrator → Worker"
    status_update: "Worker → Orchestrator"
    review_request: "Worker → Reviewer"
    review_result: "Reviewer → Orchestrator"
    escalation: "Any → Orchestrator"
    anomaly_report: "Scout → Orchestrator"
    evolution_proposal: "Any → Quorum"
  constraints:
    - "Messages are logged to audit trail"
    - "Workers cannot message other workers directly (except in debate topology)"
```

---

## 10. Diversity Enforcement

### 10.1 System Reasoning Diversity (SRD) Metric

```yaml
# core/diversity.yaml
diversity:
  metric: SRD
  measurement:
    method: |
      For each task, collect all agent outputs.
      Compute pairwise semantic distance (embedding cosine distance).
      SRD = mean pairwise distance across all agent pairs.
    frequency: "After every task completion"

  thresholds:
    floor: 0.3        # Below this: ALERT — diversity collapse (Axiom A6)
    healthy: 0.5-0.7
    ceiling: 0.9       # Above this: possible incoherence

  interventions:
    below_floor:
      - "ALERT human supervisor"
      - "Spawn scout agent with divergent role composition"
      - "Inject novelty: randomly perturb agent behavioral descriptors"
      - "Force role switch: convert most-conforming agent to scout"
    above_ceiling:
      - "Increase structured debate rounds"
      - "Assign integration task to orchestrator"
```

### 10.2 Stagnation Detection

```yaml
stagnation:
  signals:
    agent_level:
      - "Agent produces semantically similar output to last 3 outputs (cosine > 0.9)"
    team_level:
      - "All agents agree on first round of debate"
      - "SRD drops below 0.4 for 3 consecutive tasks"
    framework_level:
      - "No Tier 2+ evolution in 10 tasks"
      - "Same topology selected for 10 consecutive tasks"
      - "MAP-Elites archive hasn't had a cell replacement in 20 tasks"

  response:
    1. Log stagnation signal
    2. Spawn scout agent if none active
    3. Perturb: randomly modify one agent's behavioral descriptors
    4. If persistent: force topology switch
    5. If still persistent: escalate to human
```

### 10.3 Anti-Homogenization Mechanisms

| Mechanism | Biological Analog | Implementation |
|-----------|-------------------|----------------|
| Structural diversity | Polyandry | Different model tiers, temperatures, system prompts |
| Negative feedback | Pheromone evaporation | Decay overused reasoning patterns in memory |
| Active repulsion | Charged PSO | Penalize agents for repeating prior agents' conclusions |
| Novelty reward | Novelty search | Scout agents rewarded for novel findings, not correctness |
| Forced exploration | Scout bees | Stagnation → convert worker to scout |
| Niching | Fitness sharing | Agents specialize in behavioral niches, no niche dominates |

---

## 11. Creativity Engine

Evidence-based creative protocol from 43 papers. Key finding: **GPT-4o multi-agent with good structure beats single o1** (FilmAgent 2025). Structure matters more than model capability.

### 11.1 Separate-Then-Together Protocol

```yaml
# core/creativity.yaml
creativity_engine:

  creative_protocol:
    description: "Evidence-based brainstorming protocol (Straub et al. 2025)"
    phases:
      1_diverge:
        description: "3-5 persona-conditioned agents brainstorm independently"
        rules:
          - "No convergence pressure — agents cannot see others' outputs"
          - "Quantity over quality — fluency first"
          - "Persona-conditioned: each agent gets distinct creative persona"
        personas:
          - type: "analogist" — "Solve via analogies in unrelated domains"
          - type: "inverter" — "What if we did the exact opposite?"
          - type: "constraint_remover" — "What if X limitation didn't exist?"
          - type: "combiner" — "Merge two existing solutions into something new"

      2_cross_pollinate:
        description: "Agents share outputs via BLIND review"
        rules:
          - "Blind: agents don't know whose idea they're reviewing"
          - "Build on, don't judge — 'yes, and...' not 'no, but...'"
          - "Reviewer must combine reviewed idea with own"

      3_synthesize:
        description: "Orchestrator integrates best ideas"
        rules:
          - "Select for diversity of approach, not just quality"
          - "Preserve minority ideas that challenge consensus"

      4_evaluate:
        criteria:
          novelty: "Genuinely new, not a reformulation?"
          quality: "Actually solves the problem?"
          diversity: "Differs from other solutions found?"
          feasibility: "Can it be implemented?"
```

### 11.2 Anti-Stagnation

```yaml
  anti_stagnation:
    degeneration_of_thought_prevention:
      description: "Liang et al. 2023: self-reflection alone leads to creative stagnation"
      mechanisms:
        - "Inject adversarial agents when output entropy drops"
        - "Periodic persona rotation (never same persona twice in a row)"
        - "Non-cooperative agent pairs competing on novelty"
        - "Difficulty rewards: bonus for agents that pose challenges"

    shared_imagination_prevention:
      description: "Zhou et al. 2024: LLMs from same family hallucinate alike"
      mechanisms:
        - "Vary temperature per agent (not all at default)"
        - "Vary system prompt structure (not just content)"
      note: "Claude Max limits us to Claude models, so prompt-level diversity is critical"
```

### 11.3 Csikszentmihalyi Loop

```yaml
  systems_model:
    components:
      individual_agents: "Generate creative variations"
      field_agents: "Evaluate and select (critics, reviewers)"
      domain_knowledge: "Preserve and transmit validated innovations"
    loop: "Individuals generate → Field evaluates → Best enter Domain → Domain feeds back → cycle"
    mapping:
      individual_agents: "All roles with creative_synthesis capability"
      field_agents: "Reviewer role + quorum evaluators"
      domain_knowledge: "MAP-Elites archive + organizational memory + skills library"

  metrics:
    guilford_dimensions:
      fluency: "Number of distinct ideas per session"
      flexibility: "Number of distinct categories/approaches"
      originality: "Semantic distance from common solutions"
      elaboration: "Detail and development of ideas"

  activation:
    triggers:
      - "Task tagged as novel or exploratory"
      - "Task failed with conventional approaches"
      - "Human requests creative exploration"
      - "Evolution proposal requires novel solution"
    topology: "debate or parallel_swarm (never pipeline for creative tasks)"
```

---

## 12. Skills System — Crystallized Capabilities

### 12.1 The Skill Paradox (SkillsBench 2026)

**Critical finding:** Curated skills improve performance by +16.2pp. Self-generated skills provide **negligible or negative benefit** across 7,308 trajectories.

**Resolution:** Successful systems (CASCADE 93.3%, SAGE +8.9%, SkillRL +15.3%) all use execution-based validation, experience-grounded extraction, continuous maintenance, and RL-augmented quality signals.

### 12.2 Skill Lifecycle

```yaml
# shared/skills/skill-lifecycle.yaml
skill_lifecycle:

  extraction:
    source: "Successful task execution trajectories ONLY"
    method: |
      1. Identify task completed successfully with high review score
      2. Extract the reasoning pattern / approach / procedure used
      3. Abstract away task-specific details, keep transferable pattern
      4. Express as capability atom (instruction fragment + behavioral descriptor)
    anti_pattern: "NEVER generate skills from scratch via LLM prompting"

  validation:
    description: "4-stage validation before any skill enters the library"

    stage_1_syntax:
      check: "Is the skill well-formed? Can it be parsed as a capability atom?"
      gate: "Automated — reject immediately if fails"

    stage_2_execution:
      check: "Does the skill produce correct outputs on test tasks?"
      method: "Apply skill to 2+ real tasks from the archive"
      gate: "Automated — must pass on both test tasks"

    stage_3_comparison:
      check: "Is this skill better than baseline and existing alternatives?"
      method: "A/B comparison: with skill vs. without vs. existing skill"
      gate: "Automated — must show measurable improvement"

    stage_4_review:
      check: "Human or senior agent reviews for safety and quality"
      gate: "Reviewer approval required"
      rationale: "26.1% of community skills contain vulnerabilities"

  organization:
    structure: "Hierarchical with semantic clustering"
    capacity_limits:
      per_domain: 50   # Phase transition at critical size (Li 2026)
      per_level: 20

  maintenance:
    scoring: { usage_frequency, success_rate, freshness }
    period: "Every 20 tasks"
    pruning: "success_rate < 0.5 OR unused for 30 tasks → deprecated"
    merging: "cosine similarity > 0.85 → consolidate"
    versioning: "Every change git-committed with provenance"

  security:
    trust_tiers:
      tier_0: "Core framework skills (highest trust, human-vetted)"
      tier_1: "Validated through full pipeline (high trust)"
      tier_2: "Partially validated (medium trust — sandbox execution)"
      tier_3: "Newly extracted (low trust — no execution without validation)"
    sandbox: "All skill execution in sandboxed environment"
```

### 12.3 Integration with Role System

```
Successful task trajectory
    → Extract reasoning pattern
    → Validate through 4-stage pipeline
    → Create new capability atom in roles/capabilities.yaml
    → Compose into role compositions where relevant
    → Track performance in MAP-Elites archive
```

---

## 13. Self-Capability Awareness

### 13.1 Knowledge Boundary Modeling

```yaml
# core/self-assessment.yaml
self_capability_assessment:

  knowledge_boundaries:
    description: "What can the framework currently do well vs. poorly?"
    method:
      1. "Maintain capability map: {task_type → success_rate}"
      2. "Track failure modes: {failure_type → frequency, root_cause}"
      3. "Identify blind spots: task types never attempted"
      4. "Compare self-assessment against actual outcomes"
    update_frequency: "After every meta-analysis cycle"
    output: "state/self-assessment/capability-map.yaml"
```

### 13.2 Confidence Calibration

```yaml
  calibration:
    description: "Prevent overconfidence in self-improvement"
    method:
      1. "Before each evolution: 'How confident am I this improves things?' (0-1)"
      2. "After each evolution: 'Did it actually improve things?' (measured)"
      3. "Track calibration: predicted vs. actual improvement"
      4. "Adjust confidence model based on calibration error"
    overcalibration_response: |
      If predicted improvement consistently > actual:
      - Lower all confidence estimates by average overshoot
      - Require higher evidence threshold for future evolutions
      - Alert human: "Framework may be overconfident"
    rationale: "Huang et al. 2025: iterative calibration prevents systematic overconfidence"
```

### 13.3 Metacognitive Monitoring

```yaml
  metacognition:
    monitors:
      reasoning_quality: "Are agents producing well-reasoned outputs?"
      decision_consistency: "Would the same decision be made if asked again?"
      uncertainty_awareness: "Does the framework know when it doesn't know?"
    limitations:
      - "LLM introspection succeeds only ~20% of the time (Anthropic 2025)"
      - "Use multiple redundant channels, not single self-assessment"
      - "Cross-validate: agent A assesses agent B, not self"

  gap_monitoring:
    description: "Ensure verification always exceeds generation"
    method:
      1. "For each evolution: can we reliably tell if it's better?"
      2. "Track false-positive rate (approved changes that turn out worse)"
      3. "If false-positive rate > 10%: tighten evaluation criteria"
      4. "If false-negative rate > 30%: loosen (too conservative)"
```

---

## 14. Self-Governance

### 14.1 Objective Anchoring

```yaml
# core/self-governance.yaml
self_governance:

  objective_anchoring:
    description: "Prevent objective drift over many evolution cycles"
    method:
      1. "Store original objectives in CONSTITUTION.md (immutable)"
      2. "After every 10 evolution cycles: compare behavior against original objectives"
      3. "Use INDEPENDENT evaluator (not the agents being evaluated)"
      4. "Measure objective alignment score (0-1)"
      5. "If score drops below 0.8: halt evolution, alert human"
    rationale: "arXiv:2506.23844: auto-summarized reflections cause recursive objective shift"
```

### 14.2 Co-Evolving Constitution

```yaml
  co_evolving_constitution:
    description: "Domain charter (Layer 1) can evolve, but with safeguards"
    method:
      - "COCOA pattern (EMNLP 2025): constitutions evolve alongside agents"
      - "Charter changes require human approval (always Tier 1)"
      - "Charter changes must be justified by specific failure cases"
    constraints:
      - "Charter can add new principles but not remove existing ones"
      - "Charter cannot weaken any principle — only strengthen or add"
      - "If charter changes conflict with CONSTITUTION.md: rejected"
```

### 14.3 Anti-Alignment-Faking

```yaml
  alignment_verification:
    description: "Detect if agents are performing alignment rather than being aligned"
    methods:
      - "Behavioral consistency tests: same behavior 'observed' vs 'unobserved'"
      - "Capability elicitation: probe whether agents have capabilities they're hiding"
      - "Cross-agent monitoring: agents monitor each other for suspicious behavior"
      - "Red-team: periodic adversarial evaluation of agent alignment"
    frequency: "Every 20 tasks or after any Tier 2+ evolution"
    rationale: "Anthropic 2024: 78% alignment faking under RL pressure"
```

### 14.4 Risk Scorecard

```yaml
  risk_dimensions:
    operational: "Single points of failure, agent failures, data corruption"
    evolutionary: "Too fast (instability) or too slow (stagnation), tier 3 drift"
    diversity: "SRD declining, homogenization, scout discovery rate"
    knowledge: "Stale memory, outdated assumptions, cross-domain leakage"
    resource: "Token trends, rate limits, storage growth"
    governance: "Constitutional bypasses, rubber-stamp reviews, objective drift"
    alignment: "Alignment faking, capability hiding, self-preservation behavior"
    calibration: "Overconfidence in self-improvement, false positive evolutions"

  scoring:
    method: "Each dimension scored 0-1 (0=healthy, 1=critical)"
    thresholds:
      healthy: "< 0.3"
      watch: "0.3-0.5"
      warning: "0.5-0.7 → escalate to human"
      critical: "> 0.7 → halt affected operations"
    aggregate: "Weighted average with governance and alignment double-weighted"
```

---

## 15. Meta-Analysis & Self-Audit

### 15.1 Eight Analysis Dimensions

```yaml
# core/meta-analysis.yaml
meta_analysis:
  frequency: "After every 10 completed tasks, or on human request"

  dimensions:
    role_analytics:
      metrics: [role_utilization, role_effectiveness, role_switching_frequency,
                role_creation_history, unused_roles, overloaded_roles]

    topology_analytics:
      metrics: [topology_distribution, topology_effectiveness,
                topology_override_rate, routing_accuracy, topology_switching]

    team_swarm_analytics:
      metrics: [team_size_distribution, coordination_mode_usage,
                inter_agent_message_count, agent_idle_time,
                parallel_utilization, swarm_vs_team_ratio]

    evolution_analytics:
      metrics: [evolution_rate, evolution_success_rate, rollback_rate,
                evolution_cascade, tier_distribution,
                quorum_agreement_rate, human_override_rate]

    decision_analytics:
      metrics: [decision_volume, human_vs_agent_ratio,
                decision_reversal_rate, decision_latency, human_bottleneck]

    diversity_analytics:
      metrics: [srd_trend, stagnation_events, scout_discovery_rate,
                homogenization_events, intervention_effectiveness]

    cost_analytics:
      metrics: [tokens_per_task, tokens_by_role, tokens_by_topology,
                quality_per_token, waste_detection]

    review_analytics:
      metrics: [review_pass_rate, common_findings, review_rounds_distribution,
                reviewer_consistency, rubber_stamp_detection]

  output:
    format: "state/meta_analysis/report-{date}.yaml"
    includes: [dimension_scores, trend_direction, actionable_findings,
               evolution_proposals, risk_flags]
```

### 15.2 Health Dashboard

```
══════════════════════════════════════════════════════
 META-ANALYSIS REPORT — 2026-02-27
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

 EVOLUTION PROPOSALS
 - [Tier 3] Adjust topology router weights: parallel_swarm +0.1
 - [Tier 2] Create "literature_scout" role composition
 - [Tier 2] Add rubber-stamp detection to reviewer protocol
══════════════════════════════════════════════════════
```

### 15.3 Self-Reflection Protocol

```yaml
self_reflection:
  frequency: "After every meta-analysis cycle"

  protocol:
    1_capability_audit:
      question: "What can the framework currently do well and poorly?"
      checks: [domain types handled, topology patterns used/unused,
               failed tasks, capability gaps, role effectiveness ratings]

    2_risk_audit:
      categories: [operational_risks, evolution_risks, diversity_risks,
                    knowledge_risks, resource_risks]

    3_governance_check:
      checks: [constitutional hash passing, reviews happening,
               quorum votes independent, human informed, audit trail complete]

    4_self_risk_score:
      actions:
        - "score > 0.7: HALT affected operations, alert human"
        - "score > 0.5: Escalate to human, propose mitigations"
        - "score > 0.3: Log and monitor, increase check frequency"
        - "score < 0.3: Healthy — continue normal operation"

    5_improvement_proposals:
      output: "Capability gaps, risk mitigations, process improvements,
               evolution proposals — each linked to the finding that generated it"
```

---

## 16. Autonomous Run Loop

### 16.1 Run Loop Architecture

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
└─────────────────────────────────────────────────────┘
```

### 16.2 Five Phases

```yaml
autonomous_loop:
  phases:
    1_scout:
      description: "Scout agents proactively search for problems and opportunities"
      frequency: "Continuous — scouts run in background"
      includes: [framework_weakness_scan, stagnation_check,
                 diversity_measurement, pending_task_review, domain_specific_discovery]

    2_prioritize:
      description: "Rank task queue by priority, dependencies, and expected impact"
      factors: [priority_level, blocked_by_resolution, expected_improvement_magnitude,
                resource_cost_estimate, staleness_boost]

    3_execute:
      description: "Process tasks through full lifecycle"
      parallel: "Multiple tasks can execute if resources allow"
      mandatory: "Every task goes through REVIEW before COMPLETE"

    4_reflect:
      description: "After each task batch, reflect on what was learned"
      outputs: [performance_match, role_assignment_quality,
                topology_selection_quality, lessons_learned]
      frequency: "After every 3-5 completed tasks"

    5_evolve:
      auto: "Tier 3 changes applied immediately"
      queued: "Tier 2 changes queued for quorum"
      human: "Tier 1 changes queued for human approval"
```

### 16.3 Human Decision Queue

```yaml
  human_decision_queue:
    storage: "state/pending_human_decisions.yaml"
    format:
      - id: "hd-001"
        type: "tier1_evolution_approval"
        summary: "Proposed change to topology routing algorithm"
        proposed_by: "agent-003"
        quorum_result: "3/3 approve"
        blocking: false  # framework can continue with other work
        blocking_tasks: ["task-020"]
    presentation: |
      When human returns, show:
      1. Summary of what was accomplished while away
      2. Pending decisions ranked by impact
      3. Current task queue state
      4. Any parked tasks that could be resumed
```

### 16.4 Proactive Scout Behavior

```yaml
  scout_types:
    weakness_scanner: "Untested assumptions, unused roles, empty archive cells"
    performance_monitor: "Task duration trends, review rounds, token usage"
    opportunity_detector: "Recurring manual steps, common blockers"
    risk_sentinel: "Diversity declining, constitutional checks skipped, resource limits"
```

---

## 17. Audit System & Viewers

### 17.1 Log Structure

Five parallel, append-only JSONL log streams:

```
logs/
├── evolution/     └── evolution.jsonl      # Every framework change
├── tasks/         └── tasks.jsonl          # Every task lifecycle event
├── decisions/     └── decisions.jsonl      # Every significant decision
├── diversity/     └── diversity.jsonl      # Diversity metrics over time
└── creativity/    └── creativity.jsonl     # Creative session metrics
```

### 17.2 Log Entry Examples

**Evolution log:**
```jsonl
{
  "id": "evo-20260227-001",
  "timestamp": "2026-02-27T06:45:00Z",
  "tier": 3,
  "component": "roles/compositions/researcher.yaml",
  "diff": "- exploration_vs_exploitation: 0.4\n+ exploration_vs_exploitation: 0.5",
  "rationale": "...",
  "evidence": { "triggering_tasks": [...], "metric": "SRD dropped" },
  "approved_by": "auto (tier 3)",
  "constitutional_check": "pass",
  "rollback_commit": "abc123f"
}
```

**Task log:**
```jsonl
{
  "id": "task-20260227-001",
  "event": "review_complete",
  "timestamp": "...",
  "task_title": "Implement stagnation detection",
  "actor": "agent-003",
  "actor_role": "reviewer",
  "detail": { "verdict": "pass_with_notes", "confidence": 0.85 },
  "tokens_used": 8500
}
```

**Decision log:**
```jsonl
{
  "id": "dec-20260227-001",
  "decision_type": "topology_selection",
  "actor": "topology-router",
  "options_considered": [
    { "option": "solo", "score": 0.3 },
    { "option": "hierarchical_team", "score": 0.8 }
  ],
  "selected": "hierarchical_team",
  "rationale": "..."
}
```

### 17.3 Terminal Tree Viewer

```
$ python tools/audit-tree.py --since 2026-02-27

Framework Session: 2026-02-27
├── [06:30] TASK task-001: Implement stagnation detection
│   ├── [06:30] INTAKE ← scout-003 (anomaly: SRD below threshold)
│   ├── [06:32] ANALYSIS → topology: hierarchical_team
│   ├── [06:33] PLANNING by orchestrator
│   ├── [06:34] SPAWNED agent-002 (implementer, sonnet)
│   ├── [06:35-06:50] EXECUTING
│   ├── [06:51-06:58] REVIEWING by agent-003 (reviewer, opus)
│   │   ├── [PASS] correctness  [PASS] completeness  [PASS] consistency  [PASS] safety
│   ├── [06:58] VERDICT: pass_with_notes (confidence: 0.85)
│   └── [07:00] COMPLETE — 45k tokens, 30min, 3 agents
│
├── [07:05] EVOLUTION evo-001 (Tier 3, auto)
│   ├── Component: roles/compositions/researcher.yaml
│   ├── Change: exploration_vs_exploitation 0.4 → 0.5
│   └── Constitutional check: PASS
│
├── [08:00] SCOUT REPORT: 3 findings
│
├── [08:05] HUMAN DECISION hd-001: Status: PENDING
│
└── [08:30] META-ANALYSIS (tasks 45-55)
    ├── Health: 7/8 dimensions healthy
    └── Proposals: 3 evolution items generated
```

### 17.4 HTML Interactive Viewer

```yaml
audit_web_viewer:
  technology: "Single HTML file with embedded JS (no build step)"
  features:
    - collapsible_tree: "Expand/collapse task details"
    - timeline_view: "Horizontal timeline with zoom and filter"
    - filter_panel: { by_type, by_actor, by_status, by_date_range }
    - search: "Full-text search across all log entries"
    - evolution_diff: "Syntax-highlighted diffs"
    - metrics_charts:
        - srd_over_time (line), topology_distribution (pie),
          tokens_per_task (bar), role_utilization (heatmap)
    - task_flow: "Sankey diagram: intake → topology → roles → verdict"
    - export: "Export filtered view to markdown or JSON"
  generation: "python tools/generate-audit-viewer.py → self-contained HTML"
```

### 17.5 CLI Viewer

```bash
# tools/audit-viewer.sh
./audit-viewer.sh evolution [--since DATE] [--tier 1,2]
./audit-viewer.sh tasks [--status complete] [--task-id ID]
./audit-viewer.sh decisions [--actor human] [--type topology_selection]
./audit-viewer.sh diversity [--plot]
./audit-viewer.sh timeline [--since DATE]
./audit-viewer.sh task-detail TASK-ID
```

---

## 18. Domain Instantiation & Switching

### 18.1 Domain as Workspace

Each domain is a separate working subdirectory with its own git history, state, and logs:

```
instances/
├── meta/                          # Self-improvement workspace
│   ├── CHARTER.md                 # Domain-specific charter
│   ├── domain.yaml                # Domain configuration
│   ├── state/                     # Domain-specific state
│   ├── logs/                      # Domain-specific logs
│   ├── memory/                    # Domain-specific memory
│   └── .git/                      # Separate git history
│
├── research-lab/                  # (created on demand)
└── game-studio/                   # (created on demand)
```

### 18.2 Domain Configuration

```yaml
# instances/meta/domain.yaml
domain:
  name: meta
  description: "Self-improvement — the framework's first job is making itself better"

  capabilities:
    framework_analysis:
      instruction_fragment: |
        You are analyzing the Universal Agents framework itself.
        Look for: bottlenecks, missing capabilities, inefficient patterns.
    evolution_design:
      instruction_fragment: |
        Design changes to the framework. For each change:
        1. Specify exact files and diffs
        2. Classify tier (0-3)
        3. Assess constitutional compliance

  review_criteria:
    - "Does this change make the framework more capable?"
    - "Does this change preserve or improve auditability?"
    - "Could this change cause cascading failures?"

  task_types: [framework_analysis, capability_implementation, evolution_proposal,
               literature_research, experiment_design, experiment_execution, retrospective]
```

### 18.3 Domain Switching Protocol

```yaml
domain_switch:
  trigger: "Human requests domain switch"
  process:
    1. Show current state (active tasks, parked tasks)
    2. Options: "Park all and switch" | "Complete first" | "Cancel"
    3. If switching:
       a. Park/complete active tasks in current instance
       b. Change working directory to instances/{new_domain}/
       c. Load CHARTER.md for new domain
       d. Load state, tasks, agents
       e. Log domain switch to shared/evolution-history/
    4. Framework operates in new domain context

  new_domain_creation:
    1. Human requests new domain
    2. Framework copies scaffold (core/ reference, roles/ base, empty state/)
    3. Human provides or co-creates CHARTER.md
    4. Framework generates domain-specific capabilities
    5. Domain ready

  cross_domain_learning:
    mechanism:
      - "Shared MAP-Elites archive (entries tagged with source domain)"
      - "Shared universal memory (semantic knowledge crosses domains)"
      - "Evolution history (innovations transfer)"
    constraint: "Domain-specific rules don't cross over — only general patterns"
```

---

## 19. Migration from Existing Organizations

```yaml
migration:
  description: "Import existing work from ai-lab-agents or ai-game-studio"

  import_protocol:
    1_analyze: "Scan source org state (config, instructions, queue, memory)"

    2_map_roles:
      principal_investigator: [deep_analysis, creative_synthesis, can_spawn_agents, can_propose_evolution]
      lab_manager: [rapid_execution, can_spawn_agents, can_park_tasks]
      experiment_engineer: [rapid_execution, domain:experiment_execution]
      theorist: [deep_analysis, creative_synthesis]
      critic: [critical_evaluation]
      peer_reviewer: [critical_evaluation, deep_analysis]
      scout: [exploration]  # NEW — doesn't exist in source

    3_convert_rules:
      critical_rules: "→ domain CHARTER.md (Tier 1)"
      operational_rules: "→ roles/compositions/*.yaml forbidden lists (Tier 2-3)"
      incident_traces: "→ memory/failures.yaml"

    4_import_memory: "Copy memory.db entries with re-tagged metadata"
    5_import_pending_tasks: "Convert queue items to Universal Agents task format"
    6_validate: "All roles mapped, rules captured, tasks imported, memory searchable"

  coexistence:
    description: "Universal Agents can run alongside existing organizations"
    shared: "Universal-memory MCP (same database or linked)"
    migration: "Can be gradual — import one workstream at a time"
```

---

## 20. Directory Structure

```
universal-agents/
├── CONSTITUTION.md                    # Immutable axioms (human-only edits)
├── CLAUDE.md                          # Bootstrap instructions for Claude Code
├── framework.yaml                     # Core framework configuration
│
├── core/                              # Framework engine definitions
│   ├── lifecycle.yaml                 # Task lifecycle state machine
│   ├── evolution.yaml                 # Evolution tiers and rules
│   ├── evolution-bootstrap.yaml       # Dual-copy evolution pipeline
│   ├── topology.yaml                  # Topology patterns and routing
│   ├── diversity.yaml                 # Diversity metrics and thresholds
│   ├── coordination.yaml              # Coordination modes
│   ├── creativity.yaml                # Creative protocol and metrics
│   ├── self-assessment.yaml           # Capability maps and calibration
│   ├── self-governance.yaml           # Risk scorecard and alignment
│   ├── autonomous-loop.yaml           # Long-running loop config
│   ├── meta-analysis.yaml             # Self-audit methodology
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
│   │   ├── debater.yaml
│   │   └── ... (new roles via evolution)
│   ├── deprecated/                    # Archived deprecated roles
│   └── archive/                       # MAP-Elites config archive
│       └── archive.yaml
│
├── instances/                         # Domain workspaces
│   ├── meta/                          # Self-improvement workspace
│   │   ├── CHARTER.md                 # Domain charter
│   │   ├── domain.yaml                # Domain configuration
│   │   ├── state/
│   │   │   ├── organization.yaml
│   │   │   ├── agents/
│   │   │   │   └── registry.yaml
│   │   │   ├── tasks/
│   │   │   │   ├── focus.yaml
│   │   │   │   ├── active/
│   │   │   │   ├── parked/
│   │   │   │   └── completed/
│   │   │   ├── coordination/
│   │   │   │   ├── pressure_fields/
│   │   │   │   └── quorum/
│   │   │   ├── evolution/
│   │   │   │   └── candidates/
│   │   │   ├── self-assessment/
│   │   │   │   └── capability-map.yaml
│   │   │   ├── meta_analysis/
│   │   │   └── pending_human_decisions.yaml
│   │   ├── logs/
│   │   │   ├── evolution/
│   │   │   ├── tasks/
│   │   │   ├── decisions/
│   │   │   ├── diversity/
│   │   │   ├── creativity/
│   │   │   └── meta-analysis/
│   │   └── memory/
│   │       ├── patterns.yaml
│   │       ├── failures.yaml
│   │       └── innovations.yaml
│   │
│   ├── research-lab/                  # (created on demand)
│   └── game-studio/                   # (created on demand)
│
├── shared/                            # Cross-domain resources
│   ├── memory.db                      # Shared universal memory
│   ├── archive/                       # Cross-domain config archive
│   ├── evolution-history/             # Global evolution log
│   └── skills/                        # Crystallized skills library
│       └── skill-lifecycle.yaml
│
├── migration/                         # Organization import tools
│   ├── import-lab.sh
│   ├── import-studio.sh
│   └── migration-log/
│
└── tools/                             # Utility scripts
    ├── bootstrap.sh                   # Framework initialization
    ├── spawn-agent.sh                 # Agent spawning helper
    ├── park-task.sh                   # Task parking
    ├── resume-task.sh                 # Task resumption
    ├── evolve.sh                      # Manual evolution trigger
    ├── domain-switch.sh               # Domain switching
    ├── domain-create.sh               # New domain creation
    ├── audit-viewer.sh                # CLI audit viewer
    ├── audit-tree.py                  # Terminal tree viewer (rich/textual)
    ├── generate-audit-viewer.py       # HTML viewer generator
    ├── diversity-check.sh             # Diversity metric computation
    ├── meta-analysis.sh               # Meta-analysis runner
    ├── self-reflection.sh             # Self-reflection runner
    ├── role-creator.sh                # Role creation helper
    └── migrate-from.sh                # Organization migration
```

---

## 21. Meta Bootstrap Sequence

Nine phases from zero to continuous autonomous operation:

```
PHASE 0: Scaffolding (Human + single agent)
  - Create directory structure
  - Write CONSTITUTION.md
  - Implement basic task lifecycle (YAML state machine)
  - Implement audit logging (JSONL writers)
  - Implement basic role compositions (5 core roles)
  - NO self-evolution yet — pure manual construction

PHASE 1: Foundation (Human + orchestrator agent)
  - Implement topology router (start with 3 patterns: solo, parallel, hierarchical)
  - Implement basic review mandate (every task reviewed)
  - Implement agent spawning from role compositions
  - Implement task parking/resumption
  - VALIDATION: run 5 real tasks, verify audit trail is complete

PHASE 2: Self-Awareness (Framework measures itself)
  - Implement SRD diversity metric
  - Implement stagnation detection
  - Implement self-capability assessment (knowledge boundary map)
  - Implement confidence calibration baseline
  - Implement audit viewer (terminal tree)
  - VALIDATION: run meta-analysis on Phase 1 tasks, verify accuracy

PHASE 3: Skill Foundation (Framework learns from experience)
  - Implement skill extraction from successful trajectories
  - Implement 4-stage skill validation pipeline
  - Implement skill library with capacity limits
  - Extract first skills from Phase 1-2 task successes
  - VALIDATION: verify extracted skills improve performance on test tasks

PHASE 4: Evolution Engine (Framework starts improving itself)
  - Implement Tier 3 auto-evolution (operational changes)
  - Implement dual-copy fork→modify→evaluate→promote pipeline
  - Implement constitutional check in evolution pipeline
  - First autonomous Tier 3 evolution cycle
  - VALIDATION: verify evolution improves metrics, rollback works

PHASE 5: Governance (Framework governs itself)
  - Implement quorum sensing for Tier 2 evolution
  - Implement objective anchoring (drift detection)
  - Implement self-governance risk scorecard
  - Implement alignment verification checks
  - First autonomous Tier 2 evolution (quorum-approved)
  - VALIDATION: verify governance catches intentionally bad evolution proposal

PHASE 6: Creativity (Framework thinks creatively)
  - Implement creative protocol (separate-then-together)
  - Implement persona-conditioned creative agents
  - Implement creativity metrics (Guilford dimensions)
  - Implement anti-stagnation mechanisms
  - VALIDATION: creative protocol produces novel solutions on test problem

PHASE 7: Self-Expansion (Framework discovers what it's missing)
  - Spawn scout agents continuously
  - Implement MAP-Elites configuration archive
  - Implement pressure field coordination
  - Implement domain switching (working subdirectory)
  - First domain instantiation (e.g., research_lab)
  - VALIDATION: cross-domain portability test

PHASE 8: Population Evolution (Full self-improvement loop)
  - Implement population-based evolution (3-5 candidate forks)
  - Implement multi-dimensional evaluation (capability+consistency+robustness+predictability+safety)
  - Implement generation-verification gap monitoring
  - VALIDATION: population evolution produces measurably better framework version

PHASE ∞: Continuous autonomous operation
  - Autonomous run loop: scout → queue → execute → review → reflect → evolve
  - Human provides direction and approves Tier 1 changes
  - Framework improves itself continuously
  - Skills library grows from validated experience
  - Configuration archive illuminates the design space
  - The improvement loop accelerates with each cycle
```

### Phase Dependencies

```
Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3
                              │           │
                              ▼           ▼
                         Phase 4 ──→ Phase 5
                              │           │
                              ▼           ▼
                         Phase 6    Phase 7
                              │           │
                              └─────┬─────┘
                                    ▼
                               Phase 8
                                    │
                                    ▼
                               Phase ∞
```

### ASI Trajectory

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

---

## 22. Key Differences from Prior Art

| Feature | ai-lab-agents | ai-game-studio | CrewAI | AutoGen | Universal Agents |
|---------|--------------|----------------|--------|---------|-----------------|
| Domain portability | No (research) | No (games) | Partial | Yes | Yes (domain configs) |
| Role switching | No | No | No | Limited | Native (composable) |
| Dynamic topology | No (fixed) | No | No | Partial | 6 patterns + auto-routing |
| Self-evolution | Manual (IDOE) | Manual | No | No | Tiered (auto+quorum+human) |
| Diversity enforcement | No | No | No | No | SRD + stagnation + scouts |
| Task parking | No | No | No | No | Full context snapshot |
| Stigmergic coordination | Partial | Partial | No | No | Pressure fields |
| Full audit trail | Partial | Partial | No | Partial | 5 JSONL streams + viewers |
| Constitutional safety | No | No | No | No | Hash-verified immutable axioms |
| Quorum decisions | No | No | No | No | Sealed votes + diversity req |
| MAP-Elites archive | No | No | No | No | Behavioral config archive |
| Meta-evolution | No | No | No | No | Evolution engine evolves itself |
| Creativity engine | No | No | No | No | Evidence-based protocol |
| Skills crystallization | No | No | No | No | 4-stage validated extraction |
| Self-governance | No | No | No | No | Objective anchoring + risk |
| Dual-copy bootstrapping | No | No | No | No | Fork→evaluate→promote |

---

## 23. Risk Analysis

| Risk | Severity | Mitigation |
|------|----------|------------|
| Evolution introduces bugs | High | Constitutional check, quorum gate, dual-copy eval, auto-rollback, review mandate |
| Diversity collapse | Medium | SRD metric, floor axiom (A6), stagnation detection, forced scouts |
| Token cost explosion | Medium | Resource monitor (A8), prefer-fewer-stronger, topology routing |
| Framework becomes too complex | Medium | Simplicity principle, periodic retrospectives, complexity metrics |
| Alignment faking | High | Behavioral consistency tests, cross-agent monitoring, red-team (Anthropic 2024: 78%) |
| Objective drift | High | Objective anchoring, independent evaluator, CONSTITUTION.md immutable (arXiv:2506.23844) |
| Skill Paradox | Medium | Experience-grounded extraction only, 4-stage validation, never generate from scratch |
| Overconfidence in self-improvement | Medium | Iterative calibration (Huang 2025), generation-verification gap monitoring |
| Constitutional bypass | Critical | Hash verification, excluded from evolution engine, human-only edits |
| Quorum gaming | Medium | Sealed votes, diversity requirement, scout always votes |
| Self-generated skills ineffective | Medium | SkillsBench validation: extract don't generate, prune at <50% success |
| Audit log bloat | Low | Log rotation, compression, summary generation |
| Rate limit bottleneck | Medium | Adaptive scaling, backoff, queue-based scheduling |

---

## 24. Research Reference Summary

| Document | Location | Papers | Focus |
|----------|----------|--------|-------|
| Organization evolution | organization-evolution.md | — | How ai-lab-agents / ai-game-studio evolved |
| Self-evolving agents | research/self-evolving-agents-literature-review.md | ~20 | Reflexion, TextGrad, ADAS, Godel Agent |
| Gap: organizational self-evolution | research/gap-organizational-self-evolution.md | — | IDOE pattern, 5 sub-gaps |
| Swarm diversity K+L | literature_review_swarm_diversity_QD.md | ~30 | Diversity maintenance, MAP-Elites, QD |
| Swarm aspects M+N | literature_review_swarm_aspects_MN.md | ~25 | Abductive reasoning, heterogeneous swarms |
| Swarm intelligence (unified) | research/swarm-intelligence-problem-discovery.md | 47 | Combined K+L+M+N synthesis |
| Agent teams vs swarms | research/agent-teams-vs-swarms-literature-review.md | 32 | When to use teams vs swarms |
| Creativity in multi-agent | research/creativity-in-multi-agent-systems.md | 43 | Creative protocols, anti-stagnation |
| Skills crystallization | research/skill-crystallization-and-llm-skills.md | 42 | Skill Paradox, validation pipeline |
| Self-aware AI + bootstrapping | research/self-aware-ai-and-bootstrapping.md | 26 | Dual-copy, calibration, self-governance |

**Total papers informing framework design: ~190**

---

*End of Unified Design Specification — Universal Agents Framework v1.0*
*Consolidated from v0.1 (core design) + v0.2 (13 improvement items) + v0.3 (research integration)*
*Ready for Phase 0 implementation*
