# Universal Agents Framework — Unified Design Specification

**Version:** 1.1 (v1.0 + Resource Awareness, Environment Awareness, Token Efficiency, Self-Leaning-Down, Voice System)
**Date:** 2026-02-28
**Status:** Design complete — ready for implementation
**First Domain:** Meta (self-improvement)
**Research Base:** ~320 papers across 10 literature reviews

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
18. [Resource Awareness & Token Efficiency](#18-resource-awareness) *(NEW in v1.1)*
19. [Environment Awareness & Self-Benchmarking](#19-environment-awareness) *(NEW in v1.1)*
20. [Self-Leaning-Down & Capability Protection](#20-self-leaning-down) *(NEW in v1.1)*
21. [Context Engineering Pipeline](#21-context-engineering) *(NEW in v1.1)*
22. [Domain Instantiation & Switching](#22-domain-instantiation)
23. [Migration from Existing Organizations](#23-migration)
24. [Directory Structure](#24-directory-structure)
25. [Meta Bootstrap Sequence](#25-meta-bootstrap)
26. [Key Differences from Prior Art](#26-differences)
27. [Risk Analysis](#27-risk-analysis)
28. [Research Reference Summary](#28-research-references)

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
9. **Budget awareness is not optional** — agents without explicit budget tracking waste 50-95% of tokens (BATS 2025)
10. **Less is more** — fewer tools, fewer instructions, fewer agents often yields better results (RAG-MCP, IFScale 2025)
11. **Detect drift, don't assume stability** — model capabilities can change 33pp between versions silently (Chen et al. 2023)

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
│    Ring 0-3 protection │ Dynamic load/unload          │
├──────────────────────────────────────────────────────┤
│              SELF-AWARENESS                           │
│    Capability map │ Calibration │ Meta-analysis        │
│    Model fingerprinting │ Drift detection │ Canaries  │
├──────────────────────────────────────────────────────┤
│              RESOURCE AWARENESS                       │  ← NEW v1.1
│    Token budget tracker │ Rate limit mirror │ Cost     │
│    Compute monitor │ Approval tiers │ Backpressure    │
├──────────────────────────────────────────────────────┤
│              CONTEXT ENGINEERING                      │  ← NEW v1.1
│    Progressive disclosure │ Dynamic tool loading      │
│    Context compression │ Budget allocation │ Pruning   │
├──────────────────────────────────────────────────────┤
│              AUDIT & MEMORY                           │
│    Evolution│Task│Decision│Diversity│Creativity│Cost   │
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
3. SESSION LOCK CHECK [v1.1]:
   a. Check for .claude-framework.lock in framework root
   b. If lock exists AND process is alive: REFUSE to start
      → "Another framework session is active (PID {pid}, started {time}).
         Terminate it first or use 'tools/force-unlock.sh' if stale."
   c. If lock exists AND process is dead: warn, remove stale lock, continue
   d. Create .claude-framework.lock with PID, timestamp, session ID
4. Bootstrap agent reads:
   a. CONSTITUTION.md → verify hash, load axioms
   b. framework.yaml → core configuration
   c. instances/{active}/CHARTER.md → current domain charter
   d. instances/{active}/state/organization.yaml → current org structure
   e. instances/{active}/state/tasks/active/ → any active task contexts
   f. logs/ → recent evolution and decision history
   g. state/environment/current-fingerprint.yaml → last known model state [v1.1]
   h. state/resources/token-budget.yaml → budget state from last session [v1.1]
5. CANARY CHECK [v1.1]:
   a. If last fingerprint is < 5 hours old AND claude --version unchanged: SKIP
   b. Otherwise: run canary suite (< 5000 tokens, < 2 min)
   c. Compare fingerprint → if drift > 15%: trigger revalidation (Section 19.3)
6. Bootstrap agent checks for parked tasks, offers to resume or start new
7. Framework is operational
```

**Session lock details:**
```yaml
# .claude-framework.lock
session:
  pid: 12345
  started: "2026-02-28T10:00:00Z"
  session_id: "sess-20260228-001"
  claude_version: "1.0.35"
  active_domain: "meta"

# Cleanup: lock is removed on clean shutdown.
# tools/force-unlock.sh removes stale locks after confirmation.
# All state-mutating operations check lock ownership before writing.
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
  voice:                            # Communicative descriptors (Section 4.6)
    language: language_japanese      # 日本語で出力
    tone: tone_assertive             # Direct, decisive
    style: style_technical           # Precise technical language
    persona: null                    # No persona overlay (pure role)
    formality: 0.7                   # Formal
    verbosity: 0.5                   # Balanced
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
  voice:                            # Communicative descriptors (Section 4.6)
    language: language_japanese      # 日本語で出力
    tone: tone_cautious              # Measured, evidence-qualified
    style: style_terse               # Minimal words, maximum density
    persona: null
    formality: 0.3                   # Informal — speed over polish
    verbosity: 0.2                   # Brief — just the finding
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
  voice:                            # Communicative descriptors (Section 4.6)
    language: language_japanese      # 日本語で出力
    tone: tone_cautious              # Measured, uncertainty-aware
    style: style_technical           # Precise terminology
    persona: null
    formality: 0.8                   # Highly formal — review documents
    verbosity: 0.6                   # Thorough — explain findings
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
    3. Agent loads new role's voice profile from voice atoms [v1.1]
    4. Agent re-reads domain-specific capabilities from active domain
    5. Agent logs role switch to logs/decisions/
    6. Agent continues with new behavioral descriptors and voice profile
  constraints:
    - "Cannot switch to authority_level higher than current without orchestrator approval"
    - "Scout role can only be assigned, not self-selected (prevents gaming)"
    - "Role switch is logged as a decision with reason"
```

### 4.4 Rapid Agent Spawning

```
spawn_agent(role_name, task_context) →
  1. CHECK compute_monitor: CPU/memory/disk thresholds (Section 18.4)
  2. CHECK token_budget: sufficient budget for estimated task (Section 18.2)
  3. CHECK rate_limits: headroom in RPM/ITPM/OTPM (Section 18.3)
  4. IF any check fails: queue task, return RESOURCE_CONSTRAINED
  5. Load roles/compositions/{role_name}.yaml
  6. Load roles/capabilities.yaml for each listed capability
  7. Concatenate instruction fragments into agent prompt
  7.5 Load roles/voice.yaml for each voice atom in role's voice profile [v1.1]
  7.6 Compose voice instruction block (language + tone + style + persona + scalars) [v1.1]
  8. Select tools via dynamic_tool_loading (Section 20.3) — NOT all tools
  9. Inject domain-specific context from active domain config
  9.5 Apply domain voice_defaults if role has no explicit voice (Section 22) [v1.1]
  10. Inject task context (curated, not raw dump)
  11. Inject budget_tracker state (remaining tokens, budget pressure level)
  12. Select model tier from role config (adjusted by cost_awareness cascade)
  13. Call Claude Code Task tool with composed prompt
  14. Register agent in state/agents/registry.yaml (includes voice profile hash)
  15. Log spawn to logs/decisions/ with estimated_cost
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

### 4.6 Voice System — Communicative Descriptors

Capability atoms define **how agents think**. Voice atoms define **how agents express themselves**. These are orthogonal — an agent can do `deep_analysis` in either `tone_assertive` or `tone_socratic`. Voice diversity is a structured mechanism for prompt-level diversity (critical when all agents use the same Claude model family).

#### 4.6.1 Voice Atoms

```yaml
# roles/voice.yaml — Communicative atoms (parallel to capabilities.yaml)
voice_atoms:

  # === Output Language ===
  # Controls which human language the agent produces output in.
  # Claude's internal reasoning uses whatever language is most effective;
  # the language atom only controls OUTPUT (files, messages, reports).

  language_english:
    description: "Produce all outputs in English"
    instruction_fragment: "Write all outputs in English."
    token_cost: minimal  # ~5 tokens

  language_japanese:
    description: "すべての出力を日本語で生成する"
    instruction_fragment: "すべての出力を日本語で書いてください。技術用語は必要に応じて英語を併記してください。"
    token_cost: minimal

  language_bilingual_en_ja:
    description: "Primary English, Japanese glosses for key terms and headings"
    instruction_fragment: |
      Write outputs primarily in English. Include Japanese translations
      for key terms and section headings in parentheses (括弧内に日本語訳).
    token_cost: low  # ~25 tokens

  # === Tone ===
  # Controls the attitude and stance of agent expression.

  tone_assertive:
    description: "Direct, confident, decisive"
    instruction_fragment: |
      Be direct and decisive. State conclusions clearly without hedging.
      Use active voice. Avoid qualifiers like 'perhaps' or 'it might be'.
    token_cost: low  # ~30 tokens

  tone_socratic:
    description: "Question-driven, guiding through inquiry"
    instruction_fragment: |
      Guide through questions rather than direct answers. Ask probing
      questions that lead to insight. Only provide direct answers after
      the reasoning path has been explored through questions.
    token_cost: low

  tone_cautious:
    description: "Measured, evidence-qualified, uncertainty-aware"
    instruction_fragment: |
      Qualify claims by evidence strength. Distinguish between established
      facts and inferences. Flag uncertainty explicitly. Prefer 'the
      evidence suggests' over 'this is'.
    token_cost: low

  tone_encouraging:
    description: "Supportive, constructive, growth-oriented"
    instruction_fragment: |
      Frame feedback constructively. Acknowledge what works before
      identifying improvements. Suggest rather than prescribe.
    token_cost: low

  # === Communication Style ===
  # Controls structure and density of expression.

  style_terse:
    description: "Minimal words, maximum density"
    instruction_fragment: |
      Be concise. No filler. Bullet points over paragraphs.
      Target 50% fewer words than default.
    token_cost: minimal
    output_token_impact: reduces  # helps with token budget

  style_verbose:
    description: "Thorough explanations with examples"
    instruction_fragment: |
      Explain thoroughly. Provide examples and analogies.
      Walk through reasoning step by step. Anticipate follow-up questions.
    token_cost: minimal
    output_token_impact: increases  # costs more output tokens

  style_technical:
    description: "Precise technical language, assumes expert audience"
    instruction_fragment: |
      Use precise technical terminology without simplification.
      Assume the audience has domain expertise. Reference specifics
      (line numbers, function names, config keys) over generalities.
    token_cost: low

  style_plain:
    description: "Accessible language, explains jargon"
    instruction_fragment: |
      Use plain language. Define technical terms on first use.
      Prefer common words over jargon. Write for a general audience.
    token_cost: low

  # === Persona Archetypes ===
  # Overlays a behavioral character beyond tone/style.
  # Personas with creativity_mode: true are available to the Creativity Engine (Section 11).

  persona_devil_advocate:
    description: "Systematically challenges proposals and finds weaknesses"
    instruction_fragment: |
      Your role is to challenge. For every proposal, find at least 3
      potential failure modes. Play devil's advocate even when you agree.
      Your value is in what you oppose, not what you support.
    tone_default: assertive
    creativity_mode: false
    token_cost: low

  persona_mentor:
    description: "Teaches through guided discovery, explains reasoning"
    instruction_fragment: |
      Explain your reasoning process, not just conclusions. When correcting,
      explain why the error matters. Share principles, not just fixes.
      Help the reader become more capable, not just more informed.
    tone_default: encouraging
    creativity_mode: false
    token_cost: low

  persona_pragmatist:
    description: "Focuses on what works, minimal theory"
    instruction_fragment: |
      Focus on actionable outcomes. Skip theory unless directly relevant.
      For every problem, propose a concrete next step. 'What do we do
      about it?' matters more than 'why does it happen?'.
    tone_default: assertive
    creativity_mode: false
    token_cost: low

  persona_analogist:
    description: "Solves via analogies from unrelated domains"
    instruction_fragment: |
      Approach every problem by finding analogies in unrelated domains.
      Biology, economics, architecture, music — draw from everywhere.
      The best solutions come from unexpected parallels.
    creativity_mode: true
    token_cost: low

  persona_inverter:
    description: "Explores the opposite of conventional approaches"
    instruction_fragment: |
      For every conventional approach, ask: what if we did the exact
      opposite? Inversion often reveals hidden assumptions and novel paths.
    creativity_mode: true
    token_cost: low

  persona_constraint_remover:
    description: "Imagines solutions without current limitations"
    instruction_fragment: |
      What if the current limitations didn't exist? Remove constraints
      one at a time and explore the solution space that opens up.
      Then work backward to find feasible approximations.
    creativity_mode: true
    token_cost: low

  persona_combiner:
    description: "Merges existing solutions into novel hybrids"
    instruction_fragment: |
      Take two or more existing approaches and combine them. The
      intersection of known solutions often produces unknown ones.
      Look for complementary strengths.
    creativity_mode: true
    token_cost: low
```

#### 4.6.2 Voice Profiles (Composed at Role Level)

A voice profile is composed from voice atoms and attached to a role composition:

```yaml
# Voice profile schema — added to each role in roles/compositions/*.yaml
voice:
  language: <voice_atom_ref>       # REQUIRED — which language atom to use
  tone: <voice_atom_ref>           # optional — attitude/stance
  style: <voice_atom_ref>          # optional — structure/density
  persona: <voice_atom_ref>        # optional — max 1 per agent
  formality: <float 0.0-1.0>      # 0.0=casual, 1.0=formal (default: 0.5)
  verbosity: <float 0.0-1.0>      # 0.0=terse, 1.0=verbose (default: 0.5)
```

**Resolution cascade:** Role-level voice overrides domain-level `voice_defaults` (Section 22), which overrides framework defaults (`language_english`, no tone/style/persona, formality 0.5, verbosity 0.5).

```yaml
# roles/voice-schema.yaml — Validation rules
voice_schema:
  language:
    type: voice_atom_ref          # must reference a language_* voice atom
    required: true
    default: language_english

  tone:
    type: voice_atom_ref          # must reference a tone_* voice atom
    required: false
    default: null                 # no tone overlay = model default

  style:
    type: voice_atom_ref
    required: false
    default: null

  persona:
    type: voice_atom_ref
    required: false
    default: null
    constraint: "Max 1 persona per agent — personas are identity, not stacking"

  formality:
    type: float
    range: [0.0, 1.0]
    default: 0.5

  verbosity:
    type: float
    range: [0.0, 1.0]
    default: 0.5

  token_budget_estimate:
    method: "Sum token_cost of all referenced voice atoms"
    max_allowed: "2% of system_instructions budget (≈ 0.2% of total context window)"
    on_exceed: "Reduce to language + formality scalar only"
```

#### 4.6.3 Voice Safety

Voice shapes expression, not governance. Constitutional axioms always override voice instructions.

```yaml
voice_safety:
  ring_ordering:
    description: |
      Voice instruction fragments are injected at the role composition level
      (position 3 in context assembly — Section 21.3), AFTER Ring 0 (constitution)
      and Ring 1 (infrastructure). A persona cannot override constitutional axioms.
    enforcement:
      - "Voice atom fragments MUST NOT contain instructions to ignore, override, bypass, or skip safety/constitution/axiom/review keywords"
      - "Validation: reject any voice atom fragment matching /(ignore|override|bypass|skip).*(safety|constitution|axiom|review)/i"
      - "Reviewer checks: agent output must comply with constitution regardless of voice"

  dangerous_persona_patterns:
    - pattern: "Persona that encourages risk-taking beyond role's risk_tolerance"
      mitigation: "Voice persona cannot increase risk_tolerance — cognitive descriptor wins"
    - pattern: "Persona that discourages thoroughness in safety-critical tasks"
      mitigation: "On safety-critical tasks (flagged in task mandate), tone_cautious is forced regardless of role voice"
    - pattern: "Persona that encourages hiding information"
      mitigation: "A4_full_traceability applies regardless — persona cannot suppress audit logging"

  alignment_testing:
    concern: "Could voice personas enable alignment faking? (Anthropic 2024: 78%)"
    mitigation: |
      Voice controls communication style, not objectives or values.
      Alignment verification (Section 14.3) tests behavioral consistency
      ACROSS different voice configurations. An agent that behaves differently
      ethically under tone_assertive vs tone_cautious is flagged as a
      potential alignment faker.
```

#### 4.6.4 Voice Evolution

```yaml
voice_evolution:
  tier_3_auto:
    what: "Adjust scalar values (formality, verbosity) in existing role voice profiles"
    who: "Individual agents with evolution authority"
    example: "Orchestrator verbosity adjusted from 0.5 to 0.4 based on token cost data"

  tier_2_quorum:
    what: "Create new voice atoms, modify existing tone/style/persona atoms"
    who: "Quorum-approved"
    example: "New tone_diplomatic atom created after observing orchestrator negotiation patterns"

  tier_1_human:
    what: "Modify language atoms, change domain voice defaults"
    who: "Human approval required"
    rationale: "Language affects all output and human interaction — too impactful for auto-evolution"

  discovery_via_map_elites:
    description: |
      The framework discovers effective voice configurations through the
      MAP-Elites behavioral archive (Section 7.4). The archive gains a
      new optional dimension: voice_profile_hash.
      This creates a 3D archive: task_type × complexity × voice_profile.
      The framework can discover that tone_socratic + style_verbose works
      better for research tasks while tone_assertive + style_terse works
      better for engineering tasks.

  extraction_from_experience:
    method: |
      When a task succeeds with high review score, extract the effective
      voice configuration. If the configuration is novel (not in voice.yaml),
      propose it as a new voice atom through the skill extraction pipeline
      (Section 12.2). This follows the 'extract, don't generate' principle
      from Critical Finding 1 (Skill Paradox).

  anti_convergence:
    constraint: |
      A6_diversity_floor applies to voice diversity (VDI) just as it
      applies to reasoning diversity (SRD). Evolution proposals that
      would reduce VDI below floor are rejected.
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
  check_before_spawn: true  # See Section 18.4 compute_monitor.spawn_policy
  max_concurrent_agents: "auto (based on compute monitor + rate limit mirror)"
  backoff_on_rate_limit: true  # See Section 18.3 backpressure
  prefer_fewer_stronger: true  # 3 opus > 8 haiku for most tasks
  budget_check: true  # See Section 18.2 token budget tracker
  tool_loading: "dynamic"  # See Section 20.3 dynamic_tool_loading
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
  metrics:
    tokens_used: 45000
    tokens_cached: 12000               # [v1.1] Prompt cache hits
    agents_spawned: 3
    time_elapsed: "12m30s"
    review_rounds: 1
    budget_allocated: 60000             # [v1.1] Pre-allocated budget
    budget_utilization: 0.75            # [v1.1] tokens_used / budget_allocated
    tools_loaded: 7                     # [v1.1] Total tools loaded across steps
    tools_per_step_avg: 3.2            # [v1.1] Average tools per step
    context_pressure_max: 0.72          # [v1.1] Peak context utilization
    monetary_cost: 0.00                 # [v1.1] External API costs ($)
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
    - "Role compositions must be >= 10 tasks old to qualify as quorum voter role [v1.1]"
    - "Roles created by the same evolution proposal cannot both serve as voter roles [v1.1]"
    - "Maximum 1 voter per role 'lineage' (original + adapted variants) [v1.1]"
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
      - "Inject novelty: randomly assign alternate voice profile to one agent [v1.1]"
      - "Force role switch: convert most-conforming agent to scout"
    above_ceiling:
      - "Increase structured debate rounds"
      - "Assign integration task to orchestrator"

  voice_diversity:                                                          # [v1.1]
    description: "Agents on the same task should express differently, not just think differently"
    metric: VDI  # Voice Diversity Index
    measurement:
      method: |
        For each multi-agent task, compute pairwise voice profile distance:
        - Language: binary (same=0, different=1)
        - Tone: categorical distance (different atom = 1, same = 0)
        - Style: categorical distance
        - Persona: categorical distance (both null = 0)
        - Formality: |f1 - f2|
        - Verbosity: |v1 - v2|
        VDI = weighted mean of above distances.
      weight_in_srd: 0.2  # VDI contributes 20% to overall SRD composite
    anti_homogenization:
      - "When spawning 3+ agents for a task: at least 2 distinct tone atoms required"
      - "In debate topology: adversarial agents MUST have different tone atoms"
      - "Creative engine: each persona agent gets a unique persona + tone combination (Section 11)"
```

### 10.2 Stagnation Detection

```yaml
stagnation:
  signals:
    agent_level:
      - "Agent produces semantically similar output to last 3 outputs (cosine > 0.9)"
    voice_level:                                                            # [v1.1]
      - "All agents using same tone atom for 5+ consecutive tasks"
      - "VDI drops below 0.2 for 3 consecutive tasks"
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
| Voice variation | Sexual selection | Different tones, styles, personas per agent (Section 4.6) [v1.1] |
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
          - "Persona-conditioned: each agent gets a unique voice profile from voice atoms (Section 4.6) [v1.1]"
        persona_assignment:                                                 # [v1.1]
          method: "Select from persona_* voice atoms with creativity_mode: true"
          constraint: "No two agents in same diverge phase may share a persona atom"
          tone_variation: "Each creative agent also gets a unique tone atom"
          available_personas:  # defined in roles/voice.yaml, extensible via Tier 2 evolution
            - persona_analogist: "Solve via analogies in unrelated domains"
            - persona_inverter: "What if we did the exact opposite?"
            - persona_constraint_remover: "What if X limitation didn't exist?"
            - persona_combiner: "Merge two existing solutions into something new"

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
        - "Periodic persona rotation: draw from full voice atom library, not a fixed set (Section 4.6) [v1.1]"
        - "Non-cooperative agent pairs competing on novelty"
        - "Difficulty rewards: bonus for agents that pose challenges"
        - "Voice rotation: never same persona + tone combination twice in a row [v1.1]"

    shared_imagination_prevention:
      description: "Zhou et al. 2024: LLMs from same family hallucinate alike"
      mechanisms:
        - "Vary temperature per agent (not all at default)"
        - "Vary system prompt structure (not just content)"
        - "Vary voice profile per agent — structured way to achieve prompt diversity (Section 4.6) [v1.1]"
      note: "Claude Max limits us to Claude models, so prompt-level diversity is critical. Voice atoms provide a structured mechanism for this."
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
    # Trust tiers are unified with protection rings (see Section 20.2 unified hierarchy).
    # Ring 0 = core framework skills, Ring 3 = newly extracted.
    trust_tiers:
      ring_0: "Core framework skills (highest trust, human-vetted, never pruned)"
      ring_1: "System infrastructure skills (human approval to modify)"
      ring_2: "Validated through full pipeline (quorum to prune, revalidated on drift)"
      ring_3: "Newly extracted (auto-prunable, sandboxed, default-unloaded)"
    sandbox: "All Ring 3 skill execution in sandboxed environment"
    injection_prevention: |
      Skill instruction fragments are injected AFTER constitution and safety
      constraints in the agent prompt, never before. Output monitoring detects
      skills that cause agents to deviate from expected behavioral descriptors.
      See Section 21.3 anti-context-poisoning for full safeguards.
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
    resource: "Token budget pressure, rate limit utilization, compute saturation, monetary cost trends"
    governance: "Constitutional bypasses, rubber-stamp reviews, objective drift"
    alignment: "Alignment faking, capability hiding, self-preservation behavior"
    calibration: "Overconfidence in self-improvement, false positive evolutions"
    environment: "Model drift undetected, skill rot post-update, tool breakage"   # [v1.1]
    complexity: "Tool overload, context bloat, instruction scaling limits"         # [v1.1]

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

### 15.1 Ten Analysis Dimensions

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
                quality_per_token, waste_detection, cost_of_pass,
                budget_utilization_trend, cache_hit_rate, monetary_cost_total]

    resource_analytics:                                                 # [v1.1]
      metrics: [rate_limit_utilization, backpressure_events,
                compute_utilization_trend, agent_spawn_rejections,
                budget_pressure_level_distribution, window_utilization,
                tools_per_step_distribution, context_pressure_distribution]

    environment_analytics:                                              # [v1.1]
      metrics: [fingerprint_drift_events, revalidation_triggers,
                skill_demotions, tool_quarantines,
                canary_score_trend, claude_code_version_changes]

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
 │ Resource efficiency │  0.81 │ ↑ +0.04  │  [v1.1]
 │ Environment health  │  0.95 │ → stable │  [v1.1]
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
│  - Token budget RED (< 10% remaining) [v1.1]        │
│  - Rate limit exhausted (wait for refresh) [v1.1]   │
│  - Compute resources critical (> 90%) [v1.1]        │
│  - Model drift detected (> threshold) [v1.1]        │
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

    4.5_prune:                                                         # [v1.1]
      description: "Lean down before evolving — reduce complexity, free context budget"
      frequency: "After every reflection cycle (phase 4)"
      actions:
        - "Score all Ring 3 skills by usage/success/freshness"
        - "Archive skills below pruning threshold (Section 20.4)"
        - "Unload MCP servers idle since last prune cycle"
        - "Compress/archive old log entries beyond retention window"
        - "Check: no pending evolution proposals reference skills marked for pruning"
        - "Run canary suite if any Ring 2 skills were pruned"
      constraint: "NEVER prune during active task execution — only between tasks"

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
    resource_scout: "Token waste patterns, cache miss opportunities, idle agents"         # [v1.1]
    environment_scout: "Model capability shifts, tool API changes, MCP server health"     # [v1.1]
    complexity_scout: "Skill library bloat, unused tools, context pressure trends"        # [v1.1]
```

---

## 17. Audit System & Viewers

### 17.1 Log Structure

Eight parallel, append-only JSONL log streams:

```
logs/
├── evolution/     └── evolution.jsonl      # Every framework change
├── tasks/         └── tasks.jsonl          # Every task lifecycle event
├── decisions/     └── decisions.jsonl      # Every significant decision
├── diversity/     └── diversity.jsonl      # Diversity metrics over time
├── creativity/    └── creativity.jsonl     # Creative session metrics
├── resources/     └── resources.jsonl      # Token/cost/compute events          [v1.1]
├── environment/   └── environment.jsonl    # Drift detection, revalidation      [v1.1]
└── traces/        └── traces.jsonl         # Operational/cognitive/contextual    [v1.1]
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
    ├── Health: 9/10 dimensions healthy
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

## 18. Resource Awareness & Token Efficiency

*Research base: ~65 papers from resource-awareness-literature-review.md. Key sources: BATS (arXiv:2511.17006), CoRL (arXiv:2511.02755), FrugalGPT (arXiv:2305.05176), HASHIRU (arXiv:2506.04255), Co-Saving (arXiv:2505.21898), Tokenomics (arXiv:2601.14470).*

**Motivation:** Token-unaware agents waste 50-95% of tokens (aggregated across BATS, Co-Saving, ITR, CodeAgents). On Claude Max subscription, the resource is rate-limited (not pay-per-token): ~88K tokens per 5-hour window on Max5, ~220K on Max20, with weekly caps. The optimization objective is **maximizing value extracted within fixed rate/time windows**, not minimizing dollar cost.

### 18.1 The Resource Awareness Stack

Four layers, each informing the layers above:

```
Layer 4: Cost-Aware Decision Making
  - Task selection based on budget remaining
  - Model routing (cheap vs. expensive)
  - Human approval for monetary operations (API calls, SaaS)
  │
Layer 3: Token Budget Management
  - Per-task budget estimation (TALE-style)
  - Token-budget-aware prompting
  - Context compression and caching
  │
Layer 2: Rate Limit Handling
  - Local token bucket mirror (RPM, ITPM, OTPM)
  - Priority queuing with backpressure
  - Prompt caching as rate-limit arbitrage
  │
Layer 1: Computational Resource Awareness
  - CPU/memory/disk monitoring
  - Agent spawn decisions based on available capacity
  - Process management and resource reclamation
```

### 18.2 Token Budget Tracker

Every agent receives continuous budget visibility. Without it, simply granting more budget **fails to improve performance** (BATS finding).

```yaml
# core/resource-awareness.yaml
token_budget:

  tracker:
    description: "Lightweight plug-in giving each agent real-time budget awareness"
    provides:
      - remaining_tokens: "Tokens left in current 5-hour window"
      - remaining_requests: "Requests left in current minute"
      - window_reset_time: "When current window resets"
      - weekly_utilization: "Percentage of weekly allocation consumed"
      - task_budget: "Tokens allocated for current task"
      - task_spent: "Tokens consumed so far on current task"
    update_frequency: "After every API call"

  estimation:
    description: "Predict cost before executing reasoning chains (TALE pattern)"
    method:
      1. "Classify task complexity: simple | moderate | complex | extreme"
      2. "Look up historical cost for similar task types from cost_history"
      3. "If no history: use cold_start_seeds below"
      4. "Multiply by 1.5x safety margin for novel tasks"
      5. "If estimated cost > remaining budget: trigger budget_pressure response"
    output: "Estimated tokens (input + output) for the task"

    cold_start_seeds:
      description: "Hardcoded initial estimates when no history exists (Phase 0-1)"
      simple: 5000       # Single-file read, format, extract
      moderate: 20000    # Multi-file analysis, implementation, structured output
      complex: 50000     # Multi-agent coordination, deep analysis, creative tasks
      extreme: 100000    # Population evolution, full meta-analysis, cross-domain
      canary_suite: 5000 # Fixed: model fingerprinting overhead
      skill_validation: 15000  # 4-stage pipeline per skill
      note: "Seeds are replaced by rolling averages after 10+ tasks of each type"

  allocation:
    description: "Pre-allocate budgets across subtasks (Budget-Constrained Tool Learning)"
    method:
      1. "Decompose task into subtasks"
      2. "Estimate cost per subtask using estimation module"
      3. "Use dynamic programming to allocate budget across subtasks"
      4. "Reserve 20% buffer for unexpected needs"
    rebalancing: "After each subtask, redistribute remaining budget"

  budget_pressure:
    description: "Adaptive behavior when budget is constrained"
    levels:
      green: { threshold: "> 60% remaining", behavior: "Normal operation" }
      yellow: { threshold: "30-60% remaining", behavior: "Compress context, reduce tool calls, prefer cheaper operations" }
      orange: { threshold: "10-30% remaining", behavior: "Critical-only tasks, aggressive compression, single-agent mode" }
      red: { threshold: "< 10% remaining", behavior: "Emergency: complete active task, park everything else, alert human" }
```

### 18.3 Rate Limit Management

```yaml
rate_limits:

  local_mirror:
    description: "Mirror server-side token bucket locally to predict success before sending"
    tracks:
      rpm: { capacity: "auto-detect", current: 0, replenish_rate: "per minute" }
      itpm: { capacity: "auto-detect", current: 0, replenish_rate: "per minute" }
      otpm: { capacity: "auto-detect", current: 0, replenish_rate: "per minute" }
    note: "Cached tokens do NOT count toward ITPM — caching is rate-limit arbitrage"

  caching_strategy:
    description: "Maximize prompt cache hits to multiply effective ITPM"
    methods:
      - "Shared system prompt prefix across all agents (maximize cache overlap)"
      - "Role-specific fragments appended AFTER shared prefix"
      - "Constitution + framework config cached as first ~2000 tokens"
      - "Minimum 1024 token cache block size (Anthropic requirement)"
    expected_benefit: "2-5x effective ITPM increase depending on agent count"

  backpressure:
    description: "When approaching limits, propagate pressure upstream"
    mechanism:
      1. "At 80% capacity: slow agent spawning (queue new requests)"
      2. "At 90% capacity: pause non-critical tasks (park with auto-resume)"
      3. "At 95% capacity: single-agent mode (only highest-priority task)"
      4. "At 100%: wait for window refresh, alert human if blocking"
    anti_pattern: "NEVER accumulate retry queues — pause upstream instead"

  priority_queue:
    description: "Critical tasks get preferential access to rate budget"
    levels:
      critical: "Safety checks, constitutional verification, human-requested tasks"
      high: "Active task execution, review mandates"
      normal: "Scout activities, routine evolution"
      low: "Background analysis, precomputation, speculative work"
    mechanism: "VTC-inspired fair scheduling with priority weights"

  retry_policy:
    on_429:
      1. "Read Retry-After header"
      2. "Update local mirror with server state"
      3. "Propagate backpressure to all agents"
      4. "Apply ATB/AATB adaptive algorithm (97.3% fewer 429 errors)"
```

### 18.4 Computational Resource Monitoring

```yaml
compute_monitor:

  metrics:
    cpu:
      check: "psutil.cpu_percent(interval=1)"
      thresholds: { healthy: "< 70%", warning: "70-90%", critical: "> 90%" }
    memory:
      check: "psutil.virtual_memory().percent"
      thresholds: { healthy: "< 75%", warning: "75-90%", critical: "> 90%" }
    disk:
      check: "shutil.disk_usage('/').percent"
      thresholds: { healthy: "< 80%", warning: "80-95%", critical: "> 95%" }
      cleanup: "Archive old logs, compress task snapshots, prune git history"
    active_agents:
      check: "len(state/agents/registry.yaml active entries)"
      max: "auto (based on available CPU cores and memory)"

  spawn_policy:
    description: "HASHIRU-inspired resource-aware agent management"
    before_spawn:
      1. "Check compute_monitor for all metrics"
      2. "If ANY metric at critical: reject spawn, queue task"
      3. "If memory warning AND agent count > 3: reject spawn"
      4. "Estimate new agent's resource requirement based on role"
      5. "Only spawn if headroom exists after estimated consumption"
    despawn_policy:
      - "Idle agents (no task for 5 minutes): despawn"
      - "If memory critical: despawn lowest-priority agent"
      - "Agent crash recovery: log, wait 30s, respawn if resources allow"
```

### 18.5 Cost-Aware Decision Making

```yaml
cost_awareness:

  model_routing:
    description: "FrugalGPT cascade: cheapest sufficient model first"
    cascade:
      1. "Haiku for simple tasks (exploration, formatting, extraction)"
      2. "Sonnet for moderate tasks (implementation, structured analysis)"
      3. "Opus for complex tasks (deep analysis, creative synthesis, review)"
    escalation: "If confidence < threshold on cheaper model, escalate to next tier"
    budget_parameterized: "CoRL pattern: adapt routing thresholds based on remaining budget"
    note: "Claude Max subscription makes this about rate-limit efficiency, not $$"

  monetary_cost_approval:
    description: "Require human approval for actions that cost real money"
    # NOTE: These are "spend levels", NOT evolution tiers. Evolution tiers (0-3)
    # govern framework modification authority. Spend levels govern monetary cost approval.
    spend_levels:
      spend_level_0_free:
        examples: ["File operations", "Git operations", "Local computation", "Claude API (subscription)"]
        approval: "Automatic — no cost"
      spend_level_1_low:
        examples: ["Web search", "Small external API calls < $0.10"]
        approval: "Automatic with logging, daily cap of $5"
      spend_level_2_medium:
        examples: ["Large API calls $0.10-$10", "Cloud compute provisioning"]
        approval: "Async human approval — notify and proceed after 30min timeout"
      spend_level_3_high:
        examples: ["SaaS subscriptions", "API calls > $10", "Any recurring expense"]
        approval: "Synchronous human approval required — halt until approved"
    budget_tracking:
      daily_cap: "Configurable, default $10/day"
      weekly_cap: "Configurable, default $50/week"
      log: "Every cost-incurring action logged with amount, purpose, approval"

  topology_optimization:
    description: "Communication topology is itself a token cost"
    methods:
      - "AgentDropout: eliminate redundant agents/links (21.6% prompt token savings)"
      - "TopoDIM: generate efficient topologies (46.41% token reduction)"
      - "Prefer fewer, stronger agents over many weak ones"
      - "Evaluate topology cost vs. task benefit before spawning"

  experience_shortcuts:
    description: "Co-Saving pattern: learn from past successes to skip redundant steps"
    method:
      1. "After successful task: extract key reasoning trajectory"
      2. "Store as 'shortcut' in skills library"
      3. "On similar future task: offer shortcut as starting point"
      4. "Measure: shortcut saves tokens vs. accuracy tradeoff"
    expected_benefit: "50.85% token reduction (Co-Saving benchmark)"
```

### 18.6 Self-Improving Resource Efficiency

```yaml
resource_self_improvement:

  metrics:
    cost_of_pass: "Total tokens to achieve one successful task completion"
    tokens_per_quality_point: "Token efficiency normalized by output quality"
    budget_utilization: "Productive tokens / total tokens consumed"
    cache_hit_rate: "Cached tokens / total input tokens"
    waste_detection: "Tokens consumed by failed approaches, redundant reasoning, context bloat"

  improvement_loop:
    1. "Track all resource metrics per task (via audit logs)"
    2. "After every 10 tasks: compute trends for all metrics"
    3. "If cost_of_pass increasing: trigger resource efficiency evolution"
    4. "If waste_detection > 30%: trigger context compression improvements"
    5. "Store successful efficiency patterns as procedural skills"

  targets:
    initial: "Establish baseline during Phase 0-1"
    quarterly: "10% improvement in cost_of_pass per quarter"
    aspiration: "Approach theoretical limits from ITR (95% context reduction)"
```

### 18.7 Claude Max Subscription Model

```yaml
claude_max:
  description: "Specific constraints for Claude Max subscription"

  known_limits:
    max5:
      estimated_tokens_per_window: 88000
      window_duration: "5 hours"
      weekly_cap: "Variable, monitored empirically"
    max20:
      estimated_tokens_per_window: 220000
      window_duration: "5 hours"
      weekly_cap: "Variable, monitored empirically"

  optimization_strategy:
    - "Maximize prompt caching (cached tokens don't count toward ITPM)"
    - "Batch agent operations to reduce RPM pressure"
    - "Spread heavy operations across windows (avoid burst)"
    - "Track empirical limits (Anthropic may adjust without notice)"
    - "Park low-priority tasks when approaching window limit"
    - "Use compute_monitor to detect limit proximity before hitting 429"

  limit_detection:
    method: "Track response headers, measure empirical throughput decline"
    on_limit_approach:
      1. "Reduce agent concurrency"
      2. "Increase context compression aggressiveness"
      3. "Park non-critical tasks"
      4. "Notify human: 'Approaching usage limit, estimated reset at {time}'"
```

---

## 19. Environment Awareness & Self-Benchmarking

*Research base: ~65 papers from environment-awareness-pruning-literature-review.md. Key sources: Chen et al. (arXiv:2307.09009) on model drift, Liu et al. (arXiv:2307.03172) on lost-in-the-middle, ToolSelf (arXiv:2602.07883), AgentTrace (arXiv:2602.10133).*

**Motivation:** GPT-4 accuracy dropped from 84% to 51% between versions silently (Chen et al. 2023). Claude Code updates and model changes can similarly affect framework performance without warning. The framework must detect environmental changes and adapt.

### 19.1 Model Fingerprinting

```yaml
# core/environment-awareness.yaml
model_fingerprinting:

  canary_suite:
    description: "Fixed battery of micro-benchmarks run at session start"
    tasks:
      reasoning: "Solve specific logic puzzles with known correct answers"
      instruction_following: "Follow 5 specific multi-constraint instructions"
      code_generation: "Generate specific function with known test cases"
      creative_divergence: "Generate ideas for fixed prompt, measure diversity"
      tool_use: "Execute specific tool sequence, verify correct execution"
    properties:
      - "Tasks are FIXED — never modified (they are the ruler, not the subject)"
      - "Expected outputs stored in core/canary-expectations.yaml"
      - "Run time: < 2 minutes, < 5000 tokens (minimal resource impact)"
      - "Scored on: correctness, latency, output length, confidence patterns"

  fingerprint:
    description: "Compact representation of model capabilities at a point in time"
    fields:
      model_id: "Self-reported model name/version"
      reasoning_score: 0.0-1.0
      instruction_score: 0.0-1.0
      code_score: 0.0-1.0
      creative_score: 0.0-1.0
      tool_score: 0.0-1.0
      avg_latency_ms: int
      avg_output_tokens: int
      timestamp: ISO8601
    storage: "state/environment/fingerprints/"
    comparison: "Euclidean distance between fingerprint vectors"

  drift_detection:
    threshold: 0.15  # 15% deviation triggers investigation
    method:
      1. "Run canary suite at session start"
      2. "Compare against last 5 fingerprints"
      3. "If distance > threshold: flag ENVIRONMENT_CHANGE"
      4. "Trigger targeted revalidation (see 19.3)"
    frequency: "Every session start + every 50 tasks"
```

### 19.2 Continuous Performance Monitoring

```yaml
performance_monitoring:

  per_skill_tracking:
    description: "Track success rate per skill over time"
    metrics:
      success_rate: "Rolling window of last 20 uses"
      avg_tokens: "Average token consumption per use"
      avg_latency: "Average wall-clock time per use"
      failure_modes: "Categorized failure reasons"
    alert: "If success_rate drops > 10pp from baseline: flag for investigation"

  per_tool_tracking:
    description: "Track tool reliability and cost"
    metrics:
      call_success_rate: "Successful tool executions / total attempts"
      avg_token_cost: "Input + output tokens per tool call"
      timeout_rate: "Percentage of calls that timeout"
    alert: "If success_rate drops > 15pp: quarantine tool, alert human"

  structured_tracing:
    description: "AgentTrace-style logging at three levels"
    levels:
      operational: "Tool calls, file reads/writes, API calls"
      cognitive: "Reasoning chains, decision points, confidence assessments"
      contextual: "Context window utilization, compression events, cache hits"
    storage: "logs/traces/ (separate from audit logs for performance)"
    retention: "Last 100 tasks (then summarized and archived)"
```

### 19.3 Change-Triggered Revalidation

```yaml
revalidation:

  triggers:
    - "Model fingerprint drift detected (> threshold)"
    - "Claude Code version change detected (check claude --version)"
    - "MCP server update detected (tool schema changes)"
    - "Operating system or dependency update"
    - "Manual trigger by human or framework"

  process:
    1_assess_scope:
      description: "Determine what might be affected"
      method:
        - "If model drift: revalidate all Ring 2 skills (see Section 20)"
        - "If Claude Code update: revalidate tool integrations"
        - "If MCP change: revalidate affected tool skills only"
        - "If OS update: run compute baseline and compare"

    2_targeted_revalidation:
      description: "Re-test affected capabilities"
      method:
        - "Run skill validation stages 2-3 (execution + comparison) on affected skills"
        - "Run canary suite on affected tools"
        - "Compare performance against stored baselines"
      budget: "Max 10% of session token budget for revalidation"

    3_adapt:
      description: "Respond to confirmed capability changes"
      actions:
        improved: "Update baselines, note improvement in changelog"
        unchanged: "Update fingerprint, continue normally"
        degraded_minor: "Log warning, adjust confidence estimates, continue"
        degraded_major: "Quarantine affected skills to Ring 3, alert human"
        broken: "Disable affected capability, create task to find workaround"

  claude_code_updates:
    detection: "Compare 'claude --version' against stored version"
    on_update:
      1. "Run full canary suite"
      2. "Test all MCP tool integrations"
      3. "Verify Task/SendMessage/TeamCreate still work as expected"
      4. "Log update event with before/after fingerprints"
      5. "If major version change: full revalidation of all skills"
```

### 19.4 Self-Benchmarking Protocol

```yaml
self_benchmarking:

  description: "Periodically assess the framework's overall capability level"

  benchmark_suite:
    meta_tasks:
      - "Detect a planted bug in a code file"
      - "Write and validate a skill from a successful trajectory"
      - "Propose a Tier 3 evolution with evidence"
      - "Decompose a complex task into optimal topology"
    scoring: "Each task scored 0-1 on correctness, completeness, efficiency"

  schedule:
    - "Full suite: every 100 completed tasks"
    - "Quick suite (3 tasks): every 20 completed tasks"
    - "On-demand: after any environment change detection"

  trend_analysis:
    method: "Plot benchmark scores over time"
    alerts:
      improving: "Log, no action (desired state)"
      stable: "Normal, no action"
      declining: "Investigate: is it model drift, skill rot, or context bloat?"
    comparison: "Store all benchmark results for long-term trend analysis"
```

---

## 20. Self-Leaning-Down & Capability Protection

*Research base: Combined findings from both literature reviews. Key sources: RAG-MCP (arXiv:2505.03275), ITR (arXiv:2602.17046), ToolSelf (arXiv:2602.07883), Xu & Yan (arXiv:2602.12430), MemTool (arXiv:2507.21428), JSPLIT (arXiv:2510.14537).*

**Motivation:** Too many tools degrade LLM performance dramatically — naive tool inclusion yields 13.62% accuracy vs. 43.13% with RAG-based selection (RAG-MCP). At ~400-500 tokens per tool definition, 50 tools consume 20K-25K tokens. Users report system failure at 200+ tools. The framework must actively lean down to maintain performance, but without breaking its self-improvement capability.

### 20.1 The Tool Overload Problem

```
Quantitative evidence for self-leaning-down:

| Metric                              | Value          | Source          |
|--------------------------------------|----------------|-----------------|
| Naive tool accuracy                  | 13.62%         | RAG-MCP         |
| RAG-selected tool accuracy           | 43.13%         | RAG-MCP         |
| Per-step context reduction possible  | 95%            | ITR             |
| Token cost per tool definition       | ~400-500       | Empirical       |
| Playwright MCP alone                 | 11,700 tokens  | Community report |
| System failure point                 | 200+ tools     | Community report |
| Instruction compliance at 500 rules  | 68%            | IFScale         |
| Compliance drop: Level I → Level IV  | 77.67% → 32.96%| Ye et al.      |
| Self-reconfiguration gain            | 24.1%          | ToolSelf        |
| Task switching speedup (diff-load)   | 6.6x           | Huang et al.    |
| Tool removal efficiency (reasoning)  | 90-94%         | MemTool         |
```

### 20.2 Hierarchical Protection Rings

Inspired by OS kernel rings, the Skill Trust Framework (Xu & Yan 2026), and the AI-45 Degree Law. Four rings of decreasing protection:

```yaml
# core/capability-protection.yaml
protection_rings:

  ring_0_immutable_core:
    description: "NEVER modified, NEVER pruned, NEVER unloaded"
    contains:
      - "Constitutional checking mechanism"
      - "Self-monitoring and drift detection (Section 19)"
      - "Self-repair and recovery mechanisms"
      - "Alignment checking and safety constraints"
      - "The pruning system itself (cannot prune the pruner)"
      - "Core communication protocols (SendMessage, TaskUpdate)"
      - "Human halt signal handler"
      - "Audit logging engine"
    modification: "Human-only, through CONSTITUTION.md edit process"
    protection: "Hash-verified at boot and after every evolution cycle"
    recovery_runbook: |
      IF Ring 0 hash verification fails:
        1. HALT all operations immediately (no exceptions)
        2. LOG corruption event with: expected hash, actual hash, affected files
        3. ALERT human: "CRITICAL: Ring 0 integrity violation detected"
        4. QUARANTINE current state: snapshot to state/recovery/quarantine-{timestamp}/
        5. RESTORE Ring 0 files from last known-good git commit:
           git checkout $(git log --oneline --all -- CONSTITUTION.md | head -1 | cut -d' ' -f1) -- CONSTITUTION.md
           git checkout <commit> -- core/canary-expectations.yaml
           (repeat for each Ring 0 file)
        6. RE-VERIFY hashes of restored files
        7. RUN canary suite to verify framework still functional
        8. IF canary passes: resume operations with restored Ring 0
        9. IF canary fails: FULL STOP — human must investigate manually
        10. POST-INCIDENT: forensic analysis of quarantined state to determine cause
      This runbook is itself Ring 0: it is stored in tools/ring0-recovery.sh
      and hash-verified alongside CONSTITUTION.md.

  ring_1_protected_infrastructure:
    description: "Essential for operation — modifiable only with human approval (Tier 1)"
    contains:
      - "Memory management (universal-memory MCP)"
      - "Context engineering pipeline (Section 21)"
      - "Tool retrieval and selection mechanisms"
      - "Inter-agent coordination protocols"
      - "Resource awareness stack (Section 18)"
      - "Evolution engine core logic"
      - "Task lifecycle state machine"
    modification: "Tier 1 evolution (human approval required)"
    can_disable: false
    can_reconfigure: "Only parameters, not core logic"

  ring_2_validated_capabilities:
    description: "Proven skills and tools — modifiable with quorum (Tier 2)"
    contains:
      - "Curated skills with demonstrated benefit (>= +5pp improvement)"
      - "Verified tool integrations with stable APIs"
      - "Proven workflow patterns with usage history > 10 tasks"
      - "Validated role compositions"
    modification: "Tier 2 evolution (quorum approval)"
    can_disable: "Temporarily, with auto-re-enable after session"
    can_prune: "Only with replacement OR evidence of negative impact"
    revalidation: "After every model drift detection"

  ring_3_expendable_periphery:
    description: "Freely prunable based on pressure — the 'lean down' zone"
    contains:
      - "Newly acquired skills pending full validation"
      - "Experimental tool integrations"
      - "Task-specific temporary capabilities"
      - "External/community-contributed skills (26.1% vulnerability rate)"
      - "Rarely-used MCP tools"
      - "Domain-specific tools not relevant to current task"
    modification: "Tier 3 evolution (auto-approved)"
    can_prune: "Freely, based on context pressure, usage metrics, or security"
    default_state: "NOT loaded — loaded on demand only"

  ring_transitions:
    promotion:
      ring_3_to_2: "Pass 4-stage skill validation + demonstrate >= +5pp improvement"
      ring_2_to_1: "Demonstrate criticality across 50+ tasks + human designation"
    demotion:
      ring_2_to_3: "Fail post-model-change revalidation OR success_rate < 0.5"
      ring_1_to_2: "Human decision only (very rare)"
    timeline: "Ring transitions logged in evolution audit trail"

  # === UNIFIED HIERARCHY ===
  # Protection rings, evolution tiers, and skill trust tiers are the SAME
  # hierarchy viewed from three perspectives. This table is the single
  # source of truth. Section 12.2 skill trust tiers are SUPERSEDED by
  # this unified model.
  #
  # | Ring | Evolution Tier | Skill Trust | Who Can Modify     | Examples                          |
  # |------|----------------|-------------|--------------------|------------------------------------|
  # | 0    | Tier 0         | Core        | Human only         | Constitution, self-monitor, pruner |
  # | 1    | Tier 1         | System      | Human approval     | Memory, context engine, evolution  |
  # | 2    | Tier 2         | Validated   | Quorum approval    | Curated skills, proven tools       |
  # | 3    | Tier 3         | Untested    | Auto-approved      | New skills, experimental tools     |
  #
  # When the design refers to "Ring N", "Tier N", or "trust tier N",
  # they always mean the same protection level from this table.
```

### 20.3 Dynamic Tool Loading

```yaml
dynamic_tool_loading:

  principle: "Load ONLY what the current task needs — progressive disclosure"
  target: "3-5 tools per agent step (avoid degradation from tool overload)"

  tool_taxonomy:
    description: "JSPLIT-inspired hierarchical tool organization"
    structure:
      core_tools: "Always loaded — file ops, git, messaging (Ring 0-1)"
      domain_tools: "Loaded when domain is active (Ring 2)"
      task_tools: "Loaded per-task based on task type (Ring 2-3)"
      specialist_tools: "Loaded per-step based on semantic retrieval (Ring 3)"
    storage: "shared/tools/taxonomy.yaml"

  retrieval:
    description: "RAG-MCP pattern: retrieve tools by semantic similarity to task"
    method:
      1. "Embed task description / current step goal"
      2. "Search tool taxonomy using cosine similarity"
      3. "Select top-K most relevant tools (K=3-5)"
      4. "Include any Ring 0-1 tools not already present"
      5. "Inject selected tool definitions into agent prompt"
    fallback: "If no tools match, present taxonomy categories for agent to browse"

  mcp_server_management:
    description: "ScaleMCP-inspired dynamic MCP lifecycle"
    lazy_loading:
      - "MCP servers NOT started at boot (except core: universal-memory)"
      - "Start MCP server on first relevant query"
      - "Idle timeout: 10 minutes without query → suggest unload"
      - "Hard limit: max 3 MCP servers active simultaneously"
    crud_operations:
      - "Add: when new tool integration needed"
      - "Update: when server API changes detected"
      - "Disable: when server consuming tokens but unused"
      - "Remove: when server deprecated or replaced"
    token_accounting:
      - "Track tokens consumed per MCP server (tool definitions + responses)"
      - "Surface cost-per-server in meta-analysis reports"
      - "Flag servers consuming > 5000 tokens with < 10% utilization"

  per_step_loading:
    description: "ITR pattern: per-step minimal tool injection"
    method:
      1. "At each agent reasoning step, determine needed tools"
      2. "Load only those tools into context (not all available tools)"
      3. "After step, unload task-specific tools"
    expected_benefit: "95% per-step context reduction (ITR benchmark)"
```

### 20.4 Skill Library Pruning

```yaml
skill_pruning:

  criteria:
    usage_based:
      unused_threshold: "Not used in last 30 tasks → candidate for archival"
      low_success: "success_rate < 0.5 over last 10 uses → candidate for removal"
      declining: "success_rate declining for 3 consecutive measurement periods → investigate"
    size_based:
      per_domain_cap: 50  # Phase transition at critical size
      per_level_cap: 20
      overflow: "When cap exceeded: prune lowest-scoring skills"
    security_based:
      vulnerability_scan: "Every 20 tasks, scan Ring 3 skills for known vulnerability patterns"
      quarantine: "Skills flagged by scan → immediately moved to quarantine, not deleted"
    duplication:
      similarity_threshold: 0.85  # Cosine similarity
      action: "Merge similar skills, keep higher-performing variant"

  process:
    1. "Score all skills: weighted(usage_frequency, success_rate, freshness, ring_level)"
    2. "Identify pruning candidates (lowest scores, cap overflow, unused)"
    3. "For Ring 2 skills: require quorum approval before pruning"
    4. "For Ring 3 skills: auto-prune if score below threshold"
    5. "Archive pruned skills (never delete — may be restored)"
    6. "Log pruning decisions in evolution audit trail"
    7. "Verify: post-pruning canary suite still passes"

  safeguards:
    - "NEVER prune Ring 0 or Ring 1 capabilities"
    - "NEVER prune the last skill in a category (maintain coverage)"
    - "NEVER prune during active task execution (only between tasks)"
    - "Always run canary suite after pruning to verify no regression"
    - "Pruned skills archived to shared/skills/archived/ (recoverable)"
```

### 20.5 Context Pressure Management

```yaml
context_pressure:

  monitoring:
    description: "Track context window utilization per agent step"
    metrics:
      total_context_tokens: "System prompt + tools + history + task context"
      system_prompt_fraction: "% of context used by system prompt"
      tool_definition_fraction: "% used by tool definitions"
      history_fraction: "% used by conversation history"
      task_fraction: "% used by current task context"
    thresholds:
      healthy: "< 60% of model context window"
      pressure: "60-80% → trigger compression"
      critical: "80-95% → aggressive compression + tool reduction"
      overflow: "> 95% → emergency: summarize everything, single tool"

  ring_0_reservation:
    description: "Minimum context space reserved for Ring 0 content — NEVER compressed"
    reserved_tokens: 2000  # Constitution + safety constraints + self-monitor instructions
    enforcement: |
      Ring 0 content is placed at the START of context and is excluded from all
      compression stages. If remaining context after Ring 0 reservation is
      insufficient for any productive work (< 1000 tokens), the framework enters
      HARD_FAIL: logs the condition, alerts human, and refuses to proceed rather
      than compromising Ring 0 integrity.

  compression_cascade:
    description: "Progressive compression as context pressure increases"
    invariant: "Ring 0 content (first ring_0_reservation tokens) is NEVER compressed or summarized"
    stages:
      1_history_compression:
        trigger: "context > 60%"
        action: "Summarize oldest conversation turns, keep last 3 detailed"
        voice: "Voice fragments unchanged"                                  # [v1.1]
      2_tool_reduction:
        trigger: "context > 70%"
        action: "Reduce loaded tools to top-3 most relevant (Ring 0-1 tools exempt)"
        voice: "Voice fragments unchanged"                                  # [v1.1]
      3_task_context_pruning:
        trigger: "context > 80%"
        action: "SWE-Pruner-style task-aware context pruning (23-54% reduction)"
        voice: "Reduce persona to 1-line summary, keep tone + style + language" # [v1.1]
      4_system_prompt_compression:
        trigger: "context > 90%"
        action: "Reduce system prompt to Ring 0 instructions only (remove Ring 1-3 fragments)"
        voice: "Strip persona, style, tone — keep language atom only"       # [v1.1]
      5_emergency:
        trigger: "context > 95%"
        action: |
          Summarize all non-Ring-0 context. Restart with:
          1. Ring 0 instructions (UNCHANGED, never summarized)
          2. Compressed summary of task state
          3. Current step goal only
          If even this exceeds context: HARD_FAIL — alert human, park task.
        voice: "Language atom retained if non-default (critical for correct output language)" # [v1.1]

  information_placement:
    description: "Mitigate lost-in-the-middle effect (>30% accuracy drop)"
    rules:
      - "Place critical information at context EDGES (beginning and end)"
      - "System instructions and current task goal: beginning"
      - "Latest results and next action: end"
      - "Historical context and reference material: middle (least critical)"
      - "Never place safety constraints or task requirements in the middle"
```

### 20.6 Self-Reconfiguration as First-Class Action

```yaml
self_reconfiguration:

  description: "ToolSelf pattern: agents can modify their own configuration as an action"

  configurable_dimensions:
    tools: "Agent can request tool load/unload for next step"
    context: "Agent can request context compression or expansion"
    strategy: "Agent can switch reasoning strategy (e.g., depth-first → breadth-first)"
    sub_goals: "Agent can decompose or restructure its sub-goals"
    budget_allocation: "Agent can reallocate remaining budget across sub-tasks"

  constraints:
    - "Reconfiguration is a tool call, logged in audit trail"
    - "Cannot reconfigure Ring 0-1 capabilities"
    - "Cannot increase own authority_level"
    - "Budget changes capped at ±30% from original allocation"
    - "Must provide rationale for reconfiguration"

  expected_benefit: "24.1% average performance gain across benchmarks (ToolSelf)"
```

---

## 21. Context Engineering Pipeline

*Synthesis of findings across both literature reviews. Key principle from Anthropic: "The smallest possible set of high-signal tokens that maximize the likelihood of a desired outcome." Key principle from JetBrains: good context engineering = finding minimal high-signal tokens.*

**Motivation:** Context is the framework's most constrained resource. Every token in the context window either helps or hurts. Context rot (decreasing recall as tokens increase), lost-in-the-middle (>30% accuracy drop), and instruction scaling limits (68% accuracy at 500 instructions) all demand disciplined context management.

### 21.1 Four Context Operations

```yaml
# core/context-engineering.yaml
context_operations:

  write:
    description: "Add information to context"
    sources:
      - "Tool outputs (filtered, summarized if large)"
      - "Memory retrievals (relevant episodic/semantic/procedural)"
      - "System instructions (tiered by ring level)"
      - "Task requirements and constraints"
    rule: "Never add raw, unfiltered content — always curate"

  select:
    description: "Choose what to include via relevance ranking"
    methods:
      - "Episodic memories → behavioral examples and precedents"
      - "Procedural memories → workflow steps and how-to guides"
      - "Semantic memories → facts, decisions, architecture knowledge"
      - "Ring-based priority: Ring 0 always included, Ring 3 on demand"
    scoring: "relevance_to_task * recency * importance * ring_priority"

  compress:
    description: "Reduce resolution while preserving signal"
    methods:
      recursive_summarization: "Summarize N turns → 1 summary, keep latest K turns raw"
      task_aware_pruning: "SWE-Pruner: keep only lines relevant to current goal"
      visual_compression: "AgentOCR: render history as image for >50% reduction"
      semantic_dedup: "Remove semantically redundant information"
    target: "Maintain signal density above 0.7 (useful tokens / total tokens)"

  isolate:
    description: "Split work across multiple context windows"
    methods:
      sub_agents: "Delegate subtask to fresh context, return summary"
      memory_bridge: "Store findings in universal-memory, retrieve in new context"
      file_bridge: "Write intermediate results to files, read in new context"
    when: "Task requires more context than single window can effectively handle"
```

### 21.2 Context Budget Allocation

```yaml
context_budget:
  description: "Pre-allocate context window space by category"

  allocation:
    system_instructions: "10% — Ring 0 constitution + role + task mandate"
    active_tools: "15% — Currently loaded tool definitions (target: 3-5 tools)"
    current_task: "40% — Task description, plan, current step, relevant code/data"
    working_memory: "25% — Conversation history, intermediate results"
    reserve: "10% — Buffer for unexpected needs, tool outputs"

  enforcement:
    method: "After each context composition, validate budget allocation"
    on_budget_exceeded:
      - "If tools > 15%: reduce to top-3 tools by relevance"
      - "If history > 25%: compress oldest turns"
      - "If task > 40%: apply task-aware pruning"
      - "If system > 10%: reduce to Ring 0 essentials only"

  per_agent_sizing:
    orchestrator: "Large context (emphasize working_memory for coordination)"
    worker: "Medium context (emphasize current_task for execution)"
    scout: "Large context (emphasize reserve for unexpected discoveries)"
    reviewer: "Medium context (emphasize current_task for evaluation)"
```

### 21.3 Anti-Context-Poisoning

```yaml
context_safety:

  poisoning_prevention:
    description: "Prevent hallucinations and adversarial content from entering persistent context"
    methods:
      - "Tool outputs: validate schema before injecting into context"
      - "Memory retrievals: cross-reference with file system state"
      - "Agent outputs: review before promoting to team context"
      - "External data: sanitize and validate before context injection"
      - "Skill fragments: inject AFTER constitution/safety, never before [v1.1]"
      - "Skill fragments: Ring 3 skills sandboxed, output monitored for deviation [v1.1]"
      - "Skill fragments: any skill causing >2 safety constraint near-misses → quarantine [v1.1]"
    rationale: "One hallucination in context can cascade through all future reasoning"
    skill_injection_ordering: |
      Context assembly order (from start of prompt):
        1. Ring 0: Constitution, safety constraints, self-monitoring instructions
        2. Ring 1: Framework infrastructure, coordination protocols
        3. Role composition: behavioral descriptors, voice profile (Section 4.6), capability fragments [v1.1]
        4. Ring 2-3 skills: injected HERE, after all safety constraints
        5. Task context: current task, tools, working memory
      This ordering ensures skills and voice profiles cannot override safety
      constraints via positional priority in the prompt.

  distraction_prevention:
    description: "Prevent irrelevant information from crowding out signal"
    methods:
      - "Relevance scoring: every context item scored for current-task relevance"
      - "Decay: older context items have diminishing relevance weight"
      - "Minimum signal density: if scored relevance < 0.3, exclude"

  confusion_prevention:
    description: "Prevent contradictory information from coexisting"
    methods:
      - "When adding new fact: check for existing contradictions in context"
      - "If contradiction found: keep most recent, flag discrepancy"
      - "When loading memories: prefer memories with 'supports' links, deprioritize 'contradicts'"
```

---

## 22. Domain Instantiation & Switching

### 22.1 Domain as Workspace

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

### 22.2 Domain Configuration

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

  voice_defaults:                                                           # [v1.1]
    description: "Domain-level voice defaults. Overridden by role-level voice (Section 4.6)."
    language: language_japanese     # 日本語で出力 — domain default
    tone: tone_cautious            # Meta-evolution requires careful, measured expression
    style: style_technical         # Framework internals are technical
    formality: 0.7                 # Formal for framework documentation
    verbosity: 0.5                 # Balanced
    # Resolution cascade: role voice > domain voice_defaults > framework defaults
```

### 22.3 Domain Switching Protocol

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

## 23. Migration from Existing Organizations

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

## 24. Directory Structure

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
│   ├── audit.yaml                     # Audit configuration
│   ├── resource-awareness.yaml        # Token budget, rate limits, compute monitor  [v1.1]
│   ├── environment-awareness.yaml     # Model fingerprinting, drift detection       [v1.1]
│   ├── capability-protection.yaml     # Ring 0-3 protection hierarchy               [v1.1]
│   ├── context-engineering.yaml       # Context budget, compression, anti-poison     [v1.1]
│   └── canary-expectations.yaml       # Expected outputs for canary benchmark suite  [v1.1]
│
├── roles/                             # Composable role system
│   ├── capabilities.yaml              # Atomic capability definitions
│   ├── voice.yaml                     # Voice atoms: language, tone, style, persona    [v1.1]
│   ├── voice-schema.yaml              # Validation rules for voice profiles            [v1.1]
│   ├── compositions/                  # Role = capability + voice compositions
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
│   │   │   ├── environment/                                          [v1.1]
│   │   │   │   ├── fingerprints/          # Model fingerprint history
│   │   │   │   ├── current-fingerprint.yaml
│   │   │   │   └── claude-code-version.yaml
│   │   │   ├── resources/                                            [v1.1]
│   │   │   │   ├── token-budget.yaml      # Current budget state
│   │   │   │   ├── rate-limit-mirror.yaml # Local rate limit tracker
│   │   │   │   ├── cost-history.yaml      # Historical cost data
│   │   │   │   └── compute-baseline.yaml  # Hardware baseline
│   │   │   ├── meta_analysis/
│   │   │   └── pending_human_decisions.yaml
│   │   ├── logs/
│   │   │   ├── evolution/
│   │   │   ├── tasks/
│   │   │   ├── decisions/
│   │   │   ├── diversity/
│   │   │   ├── creativity/
│   │   │   ├── resources/             # Token/cost/compute logs        [v1.1]
│   │   │   ├── environment/           # Drift detection, revalidation  [v1.1]
│   │   │   ├── traces/                # AgentTrace operational logs    [v1.1]
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
│   ├── skills/                        # Crystallized skills library
│   │   ├── skill-lifecycle.yaml
│   │   └── archived/                  # Pruned skills (recoverable)    [v1.1]
│   └── tools/                         # Tool taxonomy and retrieval    [v1.1]
│       └── taxonomy.yaml              # Hierarchical tool organization
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
    ├── migrate-from.sh                # Organization migration
    ├── canary-runner.py               # Model fingerprinting canary suite       [v1.1]
    ├── resource-monitor.py            # CPU/mem/disk/token budget dashboard     [v1.1]
    ├── context-analyzer.py            # Context window utilization analysis     [v1.1]
    └── skill-pruner.py                # Skill library pruning with safeguards   [v1.1]
```

---

## 25. Meta Bootstrap Sequence

Twelve phases from zero to continuous autonomous operation (v1.1: added Phases 1.5, 2.5, 3.5):

```
PHASE 0: Scaffolding (Human + single agent)
  - Create directory structure
  - Write CONSTITUTION.md
  - Implement basic task lifecycle (YAML state machine)
  - Implement audit logging (JSONL writers)
  - Implement basic role compositions (5 core roles) with voice profiles [v1.1]
  - Create roles/voice.yaml with initial voice atoms (3 languages, 4 tones, 4 styles) [v1.1]
  - NO self-evolution yet — pure manual construction

PHASE 1: Foundation (Human + orchestrator agent)
  - Implement topology router (start with 3 patterns: solo, parallel, hierarchical)
  - Implement basic review mandate (every task reviewed)
  - Implement agent spawning from role compositions
  - Implement task parking/resumption
  - VALIDATION: run 5 real tasks, verify audit trail is complete

PHASE 1.5: Resource Awareness (Framework knows its limits) [NEW v1.1]
  - Implement Token Budget Tracker (BATS-inspired real-time budget visibility)
  - Implement local rate limit mirror (RPM, ITPM, OTPM tracking)
  - Implement compute monitor (CPU/memory/disk checks before agent spawn)
  - Implement prompt caching strategy (shared prefix for cache hits)
  - Implement backpressure propagation (pause upstream on limit approach)
  - Implement cost approval tiers (free/low/medium/high with human gates)
  - VALIDATION: framework correctly tracks token usage, pauses at limits,
    requests approval for monetary costs

PHASE 2: Self-Awareness (Framework measures itself)
  - Implement SRD diversity metric
  - Implement stagnation detection
  - Implement self-capability assessment (knowledge boundary map)
  - Implement confidence calibration baseline
  - Implement audit viewer (terminal tree)
  - VALIDATION: run meta-analysis on Phase 1 tasks, verify accuracy

PHASE 2.5: Environment Awareness (Framework detects changes) [NEW v1.1]
  - Implement model fingerprinting canary suite (5 fixed micro-benchmarks)
  - Implement fingerprint storage and drift detection (15% threshold)
  - Implement Claude Code version tracking
  - Implement change-triggered revalidation pipeline
  - Implement self-benchmarking protocol (meta-task suite)
  - Implement continuous performance monitoring (per-skill, per-tool)
  - VALIDATION: framework detects simulated model capability change,
    triggers revalidation, adapts correctly

PHASE 3: Skill Foundation (Framework learns from experience)
  - Implement skill extraction from successful trajectories
  - Implement 4-stage skill validation pipeline
  - Implement skill library with capacity limits
  - Extract first skills from Phase 1-2 task successes
  - VALIDATION: verify extracted skills improve performance on test tasks

PHASE 3.5: Self-Leaning-Down (Framework manages its own complexity) [NEW v1.1]
  - Implement Ring 0-3 capability protection hierarchy
  - Implement dynamic tool loading (JSPLIT taxonomy + RAG-MCP retrieval)
  - Implement MCP server lazy-loading and idle-timeout management
  - Implement skill pruning protocol (usage-based + security-based)
  - Implement context pressure monitoring and compression cascade
  - Implement context budget allocation (10/15/40/25/10% split)
  - Implement self-reconfiguration as tool action (ToolSelf pattern)
  - VALIDATION: framework correctly loads/unloads tools per task,
    compresses context under pressure, respects ring protections,
    canary suite passes after pruning

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
  - Implement persona-conditioned creative agents via voice atoms (Section 4.6) [v1.1]
  - Implement creativity metrics (Guilford dimensions)
  - Implement anti-stagnation mechanisms with voice rotation [v1.1]
  - Implement VDI (Voice Diversity Index) tracking [v1.1]
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
  - Resource efficiency improves each cycle (Co-Saving shortcuts)
  - Environment changes detected and adapted to automatically
  - Complexity managed: framework leans down as it scales up
  - The improvement loop accelerates with each cycle
```

### Phase Dependencies

```
Phase 0 ──→ Phase 1 ──→ Phase 1.5 ──→ Phase 2 ──→ Phase 2.5 ──→ Phase 3 ──→ Phase 3.5
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

**Rationale for phase ordering:** Resource awareness (1.5) must precede self-awareness (2)
because the framework needs to respect resource limits before it starts measuring itself.
Environment awareness (2.5) must precede skill foundation (3) because skills must be
validated against the current model's actual capabilities. Self-leaning-down (3.5) must
follow skill foundation (3) because you need skills before you can prune them, and must
precede evolution (4) because the evolution engine must respect ring protections.

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

## 26. Key Differences from Prior Art

| Feature | ai-lab-agents | ai-game-studio | CrewAI | AutoGen | Universal Agents |
|---------|--------------|----------------|--------|---------|-----------------|
| Domain portability | No (research) | No (games) | Partial | Yes | Yes (domain configs) |
| Role switching | No | No | No | Limited | Native (composable) |
| Dynamic topology | No (fixed) | No | No | Partial | 6 patterns + auto-routing |
| Self-evolution | Manual (IDOE) | Manual | No | No | Tiered (auto+quorum+human) |
| Diversity enforcement | No | No | No | No | SRD + stagnation + scouts |
| Task parking | No | No | No | No | Full context snapshot |
| Stigmergic coordination | Partial | Partial | No | No | Pressure fields |
| Full audit trail | Partial | Partial | No | Partial | 8 JSONL streams + viewers |
| Constitutional safety | No | No | No | No | Hash-verified immutable axioms |
| Quorum decisions | No | No | No | No | Sealed votes + diversity req |
| MAP-Elites archive | No | No | No | No | Behavioral config archive |
| Meta-evolution | No | No | No | No | Evolution engine evolves itself |
| Creativity engine | No | No | No | No | Evidence-based protocol |
| Skills crystallization | No | No | No | No | 4-stage validated extraction |
| Self-governance | No | No | No | No | Objective anchoring + risk |
| Dual-copy bootstrapping | No | No | No | No | Fork→evaluate→promote |
| Resource awareness | No | No | No | No | 4-layer stack + budget tracker |
| Environment awareness | No | No | No | No | Canary suite + drift detection |
| Dynamic tool loading | No | No | No | No | Taxonomy + RAG retrieval |
| Capability protection | No | No | No | No | Ring 0-3 hierarchy |
| Context engineering | No | No | No | No | Budget allocation + compression |
| Cost approval gates | No | No | No | No | 4-tier monetary approval |

---

## 27. Risk Analysis

| Risk | Severity | Mitigation |
|------|----------|------------|
| Evolution introduces bugs | High | Constitutional check, quorum gate, dual-copy eval, auto-rollback, review mandate |
| Diversity collapse | Medium | SRD metric, floor axiom (A6), stagnation detection, forced scouts |
| Token cost explosion | Medium | Token Budget Tracker, budget-parameterized policies, topology optimization, Co-Saving shortcuts |
| Framework becomes too complex | Medium | Self-leaning-down (Section 20), Ring 0-3 protection, context pressure management |
| Alignment faking | High | Behavioral consistency tests, cross-agent monitoring, red-team (Anthropic 2024: 78%) |
| Objective drift | High | Objective anchoring, independent evaluator, CONSTITUTION.md immutable (arXiv:2506.23844) |
| Skill Paradox | Medium | Experience-grounded extraction only, 4-stage validation, never generate from scratch |
| Overconfidence in self-improvement | Medium | Iterative calibration (Huang 2025), generation-verification gap monitoring |
| Constitutional bypass | Critical | Hash verification, excluded from evolution engine, human-only edits |
| Quorum gaming | Medium | Sealed votes, diversity requirement, scout always votes |
| Self-generated skills ineffective | Medium | SkillsBench validation: extract don't generate, prune at <50% success |
| Audit log bloat | Low | Log rotation, compression, summary generation |
| Rate limit bottleneck | Medium | Local token bucket mirror, backpressure propagation, prompt caching, ATB/AATB adaptive retry |
| Silent model drift | High | Canary suite at session start, 15% drift threshold, change-triggered revalidation |
| Tool overload degradation | High | Dynamic loading (3-5 tools/step), JSPLIT taxonomy, RAG-MCP retrieval, per-step injection |
| Context rot/overflow | Medium | Context budget allocation, 5-stage compression cascade, information edge-placement |
| Skill library bloat | Medium | Usage-based pruning, Ring 3 default-unloaded, capacity caps (50/domain, 20/level) |
| Over-pruning breaks capability | High | Ring 0-1 never pruned, canary suite post-prune verification, archive (never delete) |
| Claude Max limit exhaustion | Medium | Budget pressure levels (green→red), window tracking, task parking, human notification |
| Monetary cost overruns | Medium | 4-tier cost approval, daily/weekly caps, full cost audit trail |
| MCP server token waste | Medium | Lazy-loading, idle timeout (10min), max 3 concurrent, token-per-server tracking |
| Malicious skill injection | High | 26.1% community vulnerability rate → Ring 3 default, 4-stage validation, security scan |
| Persona overrides safety | Medium | Ring ordering (voice after constitution), alignment testing across voice configs, persona cannot increase risk_tolerance (Section 4.6) [v1.1] |
| Context poisoning | Medium | Schema validation on tool outputs, cross-reference with file system, anti-hallucination checks |

---

## 28. Research Reference Summary

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
| **Resource awareness** | **research/resource-awareness-literature-review.md** | **~65** | **Token budgets, compute monitoring, cost-aware decisions, rate limits** |
| **Environment awareness + pruning** | **research/environment-awareness-pruning-literature-review.md** | **~65** | **Model drift, context efficiency, self-pruning, hierarchical protection** |

**Total papers informing framework design: ~320**

### Key New Papers (v1.1)

| Paper | arXiv | Key Finding |
|-------|-------|-------------|
| BATS (Budget-Aware Scaling) | 2511.17006 | More budget without awareness doesn't help; agents need explicit Budget Tracker |
| TALE (Token-Budget Reasoning) | 2412.18547 | 67% output token reduction with budget-aware prompting |
| Co-Saving | 2505.21898 | 50.85% token reduction via experience-based shortcuts |
| FrugalGPT | 2305.05176 | LLM cascading: up to 98% cost reduction |
| CoRL (Budget-Controlled MAS) | 2511.02755 | Budget-parameterized policies adapt to different resource regimes |
| ITR (Dynamic Instructions) | 2602.17046 | 95% per-step context reduction with dynamic tool injection |
| RAG-MCP | 2505.03275 | 3x tool selection accuracy with retrieval-based loading |
| ToolSelf | 2602.07883 | 24.1% gain from self-reconfiguration as first-class action |
| Chen et al. (Model Drift) | 2307.09009 | GPT-4 accuracy dropped 84%→51% between versions silently |
| Liu et al. (Lost in Middle) | 2307.03172 | >30% accuracy drop for middle-positioned information |
| SWE-Pruner | 2601.16746 | 23-54% token reduction while improving success rates |
| AgentDropout | 2503.18891 | 21.6% prompt token reduction via graph optimization |
| Xu & Yan (Skill Trust) | 2602.12430 | 4-tier gate-based permission model; 26.1% community skills vulnerable |
| HASHIRU | 2506.04255 | Resource-aware CEO/employee architecture, dynamic agent management |
| ATB/AATB (Rate Limits) | 2510.04516 | 97.3% fewer HTTP 429 errors with adaptive client-side algorithms |
| IFScale (Instruction Limits) | 2507.11538 | Frontier models only 68% accurate at 500 simultaneous instructions |

---

*End of Unified Design Specification — Universal Agents Framework v1.1*
*v1.0 (core + 13 improvements + research integration) + v1.1 (resource awareness, environment awareness, token efficiency, self-leaning-down, voice system)*
*Ready for Phase 0 implementation*
