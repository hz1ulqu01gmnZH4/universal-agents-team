# Organization & Team Evolution

**Last updated:** 2026-02-25

## Origins: Multiple Shoguns Architecture (Jan 2026)

Both organizations descend from the **Multiple Shoguns** (マルチエージェント将軍) architecture, a Japanese multi-agent pattern documented at [zenn.dev](https://zenn.dev/shio_shoppaize/articles/8870bbf7c14c22). The core design philosophy:

- **Structure prevents errors, not deliberation** (仕組みで防ぐ)
- **Don't think. Delegate.** (考えるな。委譲しろ。)
- Strict hierarchy: human supervisor → strategic leader (Opus) → operational manager (Sonnet) → specialists

The `multi-agent-shogun` repo at `~/multi-agent-shogun` was the original reference implementation.

---

## Timeline

### 2026-01-30: Initial Commit — AI Game Studio

Both repos share the same initial commit history (first 7 commits are identical, `099f756` through `cc22d0b`). The scaffold was built as a **game development studio** first:

| Date | Commit | Event |
|------|--------|-------|
| Jan 30 | `099f756` | Initial commit: full plan (1720 lines) |
| Jan 30 | `a5fcbd3` | Trim plan to 502 lines |
| Jan 30 | `c7fb34e` | **v1 scaffold:** instructions, config, queue, launch script |
| Jan 30 | `076a1ae` | Add Qwen3-TTS voice tools |
| Jan 30 | `1b29ab9` | GPU VRAM reservation manager |
| Jan 31 | `8990f2f` | Refactor: tmux windows instead of sessions |
| Jan 31 | `528969c` | Fix tmux send-keys: 2-call protocol |
| Feb 01 | `cc22d0b` | Fix launch.sh unbound variable |
| Feb 01 | `33df598` | Add .gitignore for runtime state |

### 2026-02-01: Fork Point — AI Lab Agents Born

The `ai-lab-agents` repo diverged from the game studio scaffold. Evidence:

- The `_old/` directory inside `ai-lab-agents` contains the **original game studio files**: `director.md`, `manager.md`, `gameplay_programmer.md`, `asset_generator.md`, `qa_lead.md`, `audio_director.md`, `animation_director.md`, `art_director.md`, `balance_designer.md`, `debater.md`, `debater_playfeel.md`, `researcher.md`, `story_writer.md`, `ui_designer.md`, `studio.yaml`
- These were replaced with **research lab equivalents**: `principal_investigator.md`, `lab_manager.md`, `theorist.md`, `statistician.md`, `experiment_designer.md`, `experiment_engineer.md`, `hypothesis_generator.md`, `literature_researcher.md`, `science_writer.md`, `critic.md`, `peer_reviewer.md`, `debater.md`
- The `studio.yaml` became `lab.yaml`; `Director` became `Principal Investigator`; `Manager` became `Lab Manager`

### 2026-02-07: Game Studio Gets AORCHESTRA

| Date | Commit | Event |
|------|--------|-------|
| Feb 07 | `64a9959` | AORCHESTRA sub-agent delegation protocol added |
| Feb 07 | `0f7ed0f` | Strip persona names from tracked files |

### 2026-02-11: Lab Enters Phase 2

| Date | Commit | Event |
|------|--------|-------|
| Feb 11 | `50a7b4b` | A-EVOLVE Phase 1 Baseline complete (20/20 tasks) |
| Feb 11 | `7b91fc8` | PI approval for Phase 2 |
| Feb 15 | `d11768d` | Lock G1 predictions (latest lab commit) |

---

## Organizational Structure Comparison

### Shared Architecture Pattern

Both organizations follow the same 4-tier hierarchy:

```
┌──────────────────────────────────┐
│     総監督 (Supervisor/Human)     │  Ultimate authority
├──────────────────────────────────┤
│   Strategic Leader (Opus+ET)     │  Think → Decide → Delegate → STOP
│   Read-only on production files  │  Voice announcements in Japanese
│   Communicates ONLY with Manager │  Self-improvement duty
├──────────────────────────────────┤
│   Operational Manager (Sonnet)   │  "Don't think. Delegate."
│   Writes dashboard + queue only  │  Zero idle workers tolerance
│   Routes ALL communication       │  Chained dispatch (zero-gap)
├──────────────────────────────────┤
│   Specialist Pool                │  Pick up tasks from queue
│   Domain-specific execution      │  Notify via scripts/notify.sh
│   Can spawn sub-agents (AORCH)   │  Store findings in memory
└──────────────────────────────────┘
```

### AI Research Lab (`~/ai-lab-agents`)

**Purpose:** Autonomous scientific research (brain-AI efficiency gap investigation)

**Hierarchy:**
```
総監督 (Supervisor) = Human
    └── 主任研究員 (Principal Investigator) = Claude Opus + Extended Thinking
        └── ラボマネージャー (Lab Manager) = Claude Sonnet
            ├── Opus Specialists (novel reasoning, quality gates):
            │   ├── theorist          — Mathematical models, formal frameworks
            │   ├── peer_reviewer     — Scientific rigor quality gate
            │   ├── critic            — Arithmetic/factual verification gate
            │   ├── hypothesis_generator — Generate testable hypotheses
            │   ├── experiment_designer — Design experiments with controls
            │   ├── statistician      — Statistical analysis, power analysis
            │   └── debater           — Multi-persona structured debates (8 personas)
            │
            └── Sonnet Specialists (execution, synthesis):
                ├── experiment_engineer — Run experiments, collect data
                ├── literature_researcher — Search papers, synthesize findings
                └── science_writer     — Write reports, manuscripts
```

**Key Config:** `config/lab.yaml`
**Process Rules:** `instructions/lab_manager_process_rules.md` (v2.3, 28 rules)
**Research Principles:** Falsifiability first, reproducibility sacred, effect size over p-values, one variable at a time

### AI Game Studio (`~/ai-game-studio`)

**Purpose:** AI-powered game development (EFT-like extraction shooter)

**Hierarchy:**
```
総監督 (Executive Director) = Human
    └── 監督 (Director) = Claude Opus + Extended Thinking
        └── マネージャー (Manager) = Claude Sonnet (thinking OFF)
            ├── gameplay_programmer — Core mechanics, systems, integration
            ├── asset_generator    — 3D models, textures via AI tools
            ├── qa_lead            — Testing, verification, regression
            ├── audio_director     — Sound design, music, voice
            ├── animation_director — Animation pipeline, timing
            ├── art_director       — Visual consistency, lighting
            ├── balance_designer   — Game feel, tuning, difficulty
            ├── researcher         — Prior art, GDC talks, methodology
            ├── reviewer           — Zero-tolerance quality gate
            ├── story_writer       — Narrative, dialogue, lore
            ├── ui_designer        — UX/UI design, information hierarchy
            ├── debater            — Multi-persona design debates
            └── debater_playfeel   — Game feel-specific debates
```

**Key Config:** `config/studio.yaml`
**Process Rules:** `instructions/game_studio_process_rules.md` (v1.4, 11 CRs)
**Design Framework:** Sakurai's game design methods (Decisive Direction Method)
**Additional Tooling:** Gemini 3 Pro for vision/visual analysis escalation

---

## Role Evolution Over Time

### Roles Created After Initial Setup

#### AI Lab Agents — New Roles:

| Role | When | Why Created |
|------|------|-------------|
| `critic` | ~Feb 03-04 | H1 parameter counting error (task_044→048→caught at 053) revealed missing arithmetic quality gate. PI created the role to catch factual/arithmetic errors before they propagate. |
| `peer_reviewer` | ~Feb 04 | Part of the v2.0 12-decision reform. Formal scientific review gate for experiment designs and analysis. |
| `debater` | ~Feb 04 | Stress-test hypotheses via simulated multi-persona debates. 8 default personas (Skeptic, Domain Expert, Theorist, Empiricist, Pragmatist, Devil's Advocate, Minimalist, Visionary). |

#### AI Game Studio — New Roles:

| Role | When | Why Created |
|------|------|-------------|
| `debater_playfeel` | ~Feb 08 | Specialized debate format focused specifically on visceral game feel — distinct from the general `debater` role. |
| `balance_designer` | ~Feb 08 | Dedicated role for game tuning and difficulty balancing, separate from gameplay_programmer. |

### Roles That Migrated

The game studio's original specialist pool (visible in `_old/`) included game-specific roles. When the lab was created, these were replaced with research equivalents:

| Game Studio Role | Lab Equivalent | Transformation |
|------------------|---------------|----------------|
| Director (監督) | Principal Investigator (主任研究員) | Creative authority → Research authority |
| Manager (マネージャー) | Lab Manager (ラボマネージャー) | Task dispatch unchanged |
| Gameplay Programmer | Experiment Engineer | Code execution → Experiment execution |
| Researcher | Literature Researcher | Game research → Scientific literature |
| Reviewer | Peer Reviewer + Critic | Single gate → Dual gate (scientific rigor + factual accuracy) |
| Debater | Debater | Same pattern, different domain |
| — | Theorist | New: No game equivalent |
| — | Statistician | New: No game equivalent |
| — | Hypothesis Generator | New: No game equivalent |
| — | Experiment Designer | New: No game equivalent |
| — | Science Writer | New: No game equivalent |

---

## Process Rules Evolution

### Lab Process Rules Timeline

| Version | Date | Key Changes |
|---------|------|-------------|
| v1.0 | Feb 01 | Hardware First, Named Tmux, Resumability, Never Idle, Zero-Idle, Approval Gate, Fundamental Focus, Theoretical Grounding |
| v2.0 | Feb 04 | **12-decision reform:** tiered approval, deliberation buffers, statistical review gate, prior-art check, conflict resolution, null result protocol, minor correction authority, cross-agent consultation, template consolidation, version control |
| v2.1 | Feb 21 | Hardness Estimation & Team Sizing (Rule 23), PI Completion Report Format (Rule 24) |
| v2.2 | Feb 21 | Contract-First Dispatch (Rule 25), Timeout & Re-Delegation (Rule 26) |
| v2.3 | Feb 22 | Parameter Fidelity Verification (Rule 28) |

**Total: 28 rules** accumulated over ~3 weeks.

### Studio Process Rules Timeline

| Version | Date | Key Changes |
|---------|------|-------------|
| v1.0 | Feb 10 | Consolidated from manager/director/reviewer rules. Ported patterns from lab: CR-01 through CR-05, WF-01 through WF-05, QR-01 through QR-07, RR-01, OR-01 through OR-04 |
| v1.1 | Feb 21 | CR-07: Animation Screenshot Standard (seek/freeze method) — after D0-38 delay-based capture failure |
| v1.2 | Feb 21 | CR-08: Animation Capture Quality Gate (dual check) — after D0-53 exposed combat spiking |
| v1.3 | Feb 21 | CR-10: Dual-Repo Deliverable Sync — after 35-1 and 23-3 consecutive REJECTs |
| v1.4 | Feb 23 | CR-11: Scope-Cut Protocol (DDM Pillar 3) — formalized from Sakurai D43-6 research |

**Total: 11 Critical Rules + 5 Workflow Rules + 7 Quality Rules + 1 Risk Rule + 4 Organizational Rules.**

---

## Key Architectural Innovations

### 1. AORCHESTRA Protocol (Feb 07)

Based on arXiv 2602.03786. Every agent is a 4-tuple: `<Instruction, Context, Tools, Model>`. Workers can spawn sub-agents for parallel work while remaining responsible for output quality.

**Added to game studio Feb 07, then ported to lab.** Both versions include:
- Sub-agent delegation (fire-and-forget)
- Agent Teams (coordinated multi-agent work with TeamCreate/SendMessage)
- Model routing config (`config/model_routing.yaml`)
- Context curation guidelines (the "80/20 rule": 80% of sub-agent failures come from bad context)

### 2. Universal Memory MCP (Feb ~10-15)

Shared `memory.db` per organization. All agents store findings (semantic), events (episodic), and workflows (procedural). Enables cross-session knowledge persistence and cross-agent knowledge sharing.

- Lab: `~/ai-lab-agents/memory.db` (3.7 MB)
- Studio: `~/ai-game-studio/memory.db` (436 KB)

### 3. Voice Announcements (Jan 30 — from initial scaffold)

Both PI and Director use Qwen3-TTS `clone_voice` to announce major events to the supervisor **in Japanese**. Each has a reference voice WAV. Used for milestones, approvals needed, critical findings, and failures.

### 4. Shared Observation Protocol

Both organizations use the same inter-agent communication pattern:
- `scripts/notify.sh` for ALL communication (never "talk to your screen")
- Structured message types: QUESTION, BLOCKED, OBSERVATION, DECISION NEEDED, PROGRESS
- Observation→Proposal linkage for severity S/A issues

### 5. Incident-Driven Rule Creation

Every process rule traces to a specific incident. Format:
```
**Established:** {date} — {incident description}
**RULE:** {imperative statement}
**Enforcement:** {how violations are detected/prevented}
**Rationale:** {why this rule exists}
```

This pattern ensures rules are never speculative — they all exist because something went wrong.

---

## Cross-Pollination Between Organizations

The lab and studio actively learn from each other:

| Pattern | Origin | Ported To | When |
|---------|--------|-----------|------|
| Forbidden rules (F001-F005) | Game Studio plan | Lab (identical pattern) | Feb 01 |
| Process rules file format | Lab (v2.0 reform) | Studio (v1.0) | Feb 10 |
| Approval gate (4-stage) | Lab (Rule 11) | Studio (QR-02) | Feb 10 |
| Conflict resolution escalation | Lab (observed stuck reviews) | Studio (QR-04) | Feb 10 |
| Null result protocol | Lab | Studio (QR-06) | Feb 10 |
| Insertable approval stages | Lab (Stage 1.5, 1.7 additions) | Studio (QR-07) | Feb 10 |
| AORCHESTRA delegation | Studio (Feb 07 commit) | Lab (same protocol) | Feb ~11 |
| Dual quality gate (Critic + Peer Reviewer) | Lab | Studio (Reviewer alone fills both roles) | — |
| Sakurai DDM framework | Studio (D43 research series) | Studio-internal only | Feb 23 |

---

## Supporting Repositories

| Repository | Purpose | Relationship |
|------------|---------|-------------|
| `~/multi-agent-shogun` | Original reference architecture | Ancestor of both |
| `~/ai-game-studio` | Game development studio | Active — EFT-like demo |
| `~/ai-lab-agents` | Research lab | Active — brain-AI efficiency gap |
| `~/etf-like-demo` | Godot game project | Studio's runtime (separate from git repo) |
| `~/game-dev-research` | Game development framework research | Studio's methodology source |
| `~/universal-memory-mcp` | Universal Memory MCP server | Shared infrastructure |
| `~/universal-agents-team` | Meta-organization coordination | This repo (coordination layer) |

---

## Model Allocation Strategy

| Role Type | Lab Model | Studio Model | Rationale |
|-----------|-----------|-------------|-----------|
| Strategic Leader | Opus + ET | Opus + ET | Wrong decisions cascade everywhere |
| Operational Manager | Sonnet (was Opus in early config) | Sonnet (thinking OFF) | Fast delegation by rules |
| Quality Gates | Opus (critic, peer_reviewer) | Sonnet (reviewer) | Lab needs deeper scientific rigor |
| Execution Specialists | Sonnet | Sonnet | Clear specs, execution-focused |
| Mechanical Sub-agents | Haiku | Haiku | File reading, test running, formatting |

---

## Key Lessons Encoded in Process Rules

1. **"Unit tests pass but game is broken"** — Led to mandatory runtime verification gates (CR-02, CR-06)
2. **"File exists but it's the wrong model"** — Led to visual deployment verification (CR-05)
3. **"Delay-based screenshots show idle poses"** — Led to seek/freeze animation capture standard (CR-07)
4. **"Changes in repo A but not repo B"** — Led to dual-repo sync mandate (CR-10)
5. **"H1 parameter counting error propagated through 3 tasks"** — Led to the Critic role and arithmetic verification checklist
6. **"Hardware uncertainty caused 3× protocol rewrites"** — Led to "Hardware Assessment First" rule
7. **"PI restarted the lab, killing 7 active agents"** — Led to F006 (lab session restart prohibition)

---

## Current State (Feb 25, 2026)

**AI Lab Agents:**
- Phase 2 research (brain-AI efficiency gap)
- 12 specialist roles across Opus and Sonnet tiers
- 28 process rules (v2.3)
- A-EVOLVE methodology with autonomous experiment cycles

**AI Game Studio:**
- EFT-like extraction shooter demo
- 14 specialist roles (all Sonnet except Director on Opus)
- 11 Critical Rules + full process framework (v1.4)
- Sakurai game design methodology (39-item quality checklist, DDM framework)
- 866+ passing tests, config-driven animation pipeline (D42)

**Universal Agents Team:**
- Meta-coordination layer (this repo)
- Newly established, minimal structure so far
