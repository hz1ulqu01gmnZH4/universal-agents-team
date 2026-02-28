# The Organizational Self-Evolution Gap

**Date:** 2026-02-25
**Context:** Gap analysis from self-evolving agents literature review

---

## The Gap

No published system evolves **shared organizational knowledge** — the layer of process rules, role definitions, escalation policies, coordination norms, and institutional memory that governs how a multi-agent team operates.

All existing self-evolving agent work targets one of two levels:

| Level | What Evolves | Examples |
|-------|-------------|----------|
| **Task-level** | Agent prompts, tool choices, output quality | Reflexion, Self-Refine, TextGrad |
| **Architecture-level** | Agent code, workflow topology, model selection | ADAS, Darwin Godel Machine, EvoMAC, AFlow |

The **organizational level** — sitting between architecture and task — is unstudied:

| Level | What Evolves | Examples |
|-------|-------------|----------|
| **Organizational** | SOPs, role charters, quality gates, approval workflows, conflict resolution rules, escalation policies, communication norms | **None published** |

---

## What Organizational Knowledge Is

In a hierarchical multi-agent system, organizational knowledge includes:

### 1. Process Rules (SOPs)
Explicit rules governing how work flows through the system. Examples from our implementations:

- "Hardware assessment MUST be the first task before protocol design" (Lab Rule 1 — born from H6 protocol requiring 3x rewrites)
- "ALL code task completions MUST include runtime verification results" (Studio CR-02 — born from unit tests passing while game was broken)
- "After 2 REJECT→REVISE cycles on the same task, auto-escalate to Director" (Studio QR-04 — born from observed stuck review cycles)

These are not prompts. They are **shared constraints** that every agent in the organization must follow, enforced by the Manager role.

### 2. Role Definitions
What each role is responsible for, what it is forbidden from doing, and how it communicates. Examples:

- "PI CANNOT execute experiments, write code, or contact specialists directly" (Lab F001-F004)
- "Manager can ONLY write to dashboard.md and queue/ files" (Both orgs, F001)
- "Reviewer checks animation screenshots for pose distinctness — if all poses look like idle, the capture method is broken" (Studio CR-07)

### 3. Quality Gates
Checkpoints that work must pass through before advancing. Examples:

- 4-stage approval gate: PROPOSE → REVIEW → ESCALATE → APPROVE (both orgs)
- Mandatory peer review before reporting to PI/Director (both orgs)
- Visual evidence requirement for 3D model deployment (Studio CR-05)

### 4. Escalation Policies
Rules for when and how to escalate decisions up the hierarchy. Examples:

- "Workers propose follow-up tasks. Within-directive scope = Manager auto-approves. New-direction scope = escalate to Director" (Studio WF-05)
- "Severity S/A observations MUST include a PROPOSE_TASK block or justify inaction" (Studio QR-05)

### 5. Institutional Memory
The accumulated record of what went wrong, why, and what was changed — the changelog that prevents regression. Example from our Lab Process Rules v2.3:

```
| v2.3 | 2026-02-22 | Rule 28 (Parameter Fidelity Verification) |
| v2.2 | 2026-02-21 | Rule 25 (Contract-First Dispatch), Rule 26 (Timeout) |
| v2.1 | 2026-02-21 | Rule 23 (Hardness Estimation), Rule 24 (PI Report Format) |
| v2.0 | 2026-02-04 | 12-decision reform |
| v1.0 | 2026-02-01 | Initial rules |
```

---

## Why This Gap Exists

### 1. Evaluation is hard
Task-level self-improvement has a clear signal: did the code pass the test? Did the answer match? Organizational improvement has no such automated metric. "Did the process rule prevent the failure it was designed to prevent?" requires observing the absence of a failure over time — a counterfactual.

### 2. Timescale mismatch
Task-level evolution operates within a single episode (seconds to minutes). Organizational evolution operates across sprints/sessions (hours to weeks). Most research focuses on the faster loop.

### 3. The knowledge is not in any one agent
Organizational knowledge is **shared state**. It lives in documents that all agents reference. No single agent "owns" it in the way an agent owns its prompt. Existing frameworks (Reflexion, TextGrad) update a single agent's behavior — they don't update shared cross-agent constraints.

### 4. Safety concerns
Allowing agents to modify their own organizational rules introduces risks that task-level self-modification does not:
- A rule change could cascade to all downstream agents
- A bad rule could persist across sessions (unlike a bad task attempt that gets reset)
- Without human oversight, the system could evolve rules that optimize for measurable proxies while degrading unmeasured qualities

---

## What Exists That Partially Addresses It

### MetaGPT (Hong et al., ICLR 2024)
Defines roles via Standardized Operating Procedures (SOPs). Agents communicate through structured documents. **But SOPs are static** — defined at setup time by humans, never modified by agents. No incident-driven evolution.

### SeaAgent (Sun et al., 2025)
Auto-generates and updates a "usage manual" from experience. Future agents consult it. **But it's single-agent** — one agent evolves its own manual, not a shared organizational document governing multiple agents.

### EvoMAC (Xue et al., ICLR 2025)
Co-evolves agent prompts AND inter-agent connections via textual backpropagation. **But it evolves architecture, not organizational rules.** The topology changes are about who-talks-to-whom, not about shared process constraints like "all code changes require runtime verification."

### ADAS / Darwin Godel Machine
Maintain an archive of discovered agent designs that grows over time. **But the archive contains agent implementations (code), not organizational policies.** The meta-agent proposes new agent designs, not new coordination rules.

### EvolveR (Wu et al., 2025)
Closed-loop experience lifecycle: execute → extract → distill → store → retrieve. **Closest to our pattern** in terms of the lifecycle, but operates at the individual agent skill level, not at the organizational policy level.

---

## Our Architecture as a Reference Implementation

Our `ai-lab-agents` and `ai-game-studio` systems implement organizational self-evolution through what we term **Incident-Driven Organizational Evolution (IDOE)**:

### The IDOE Loop

```
1. EXECUTE  — Agents run a sprint (tasks dispatched, executed, reviewed)
2. OBSERVE  — PI/Director reads sprint results, identifies friction/failure
3. ATTRIBUTE — Root cause analysis: which specific process rule was absent,
               unclear, or violated?
4. PROPOSE  — PI/Director drafts a new rule or rule modification
5. VALIDATE — Human supervisor reviews the proposed rule change
6. COMMIT   — Rule is written to the process rules document with:
               - Incident trace (what happened)
               - Rule text (imperative)
               - Enforcement mechanism (how violations are caught)
               - Rationale (why this rule exists)
7. PROPAGATE — Manager enforces the new rule on all future task dispatches
8. ACCUMULATE — Changelog records the rule, creating institutional memory
```

### Properties That Distinguish IDOE from Prior Work

| Property | Prior Work | IDOE |
|----------|-----------|------|
| **What evolves** | Agent prompts or code | Shared organizational rules |
| **Evolution trigger** | Task failure signal | Incident postmortem with root cause attribution |
| **Scope of change** | Single agent | All agents (rules are shared) |
| **Persistence** | Within episode or session | Permanent (written to versioned document) |
| **Safety gate** | Automated test | Human approval for rule-level changes |
| **Traceability** | Archive of designs | Each rule traces to its originating incident |
| **Enforcement** | Implicit (prompt conditioning) | Explicit (Manager rejects non-compliant work) |
| **Regression prevention** | None or implicit | Changelog + institutional memory prevents re-introducing fixed problems |

### Evidence of Effectiveness

Over 25 days of operation (Feb 01-25, 2026):

**AI Lab Agents:**
- Process rules grew from 8 (v1.0) to 28 (v2.3)
- Major reform at v2.0 (12 simultaneous decisions) triggered by accumulated observations
- Created 3 new specialist roles (Critic, Peer Reviewer, Debater) in response to observed quality gaps
- The Critic role alone was created because a parameter counting error propagated through 3 tasks before being caught

**AI Game Studio:**
- Process rules grew from 0 to 11 Critical Rules + 17 supporting rules (v1.4)
- Ported 7 rule patterns from the lab after proving effective
- Each CR traces to a specific incident with date, description, and enforcement mechanism
- CR-10 (Dual-Repo Sync) was created after two consecutive REJECTs for the same root cause — the rule prevented all future occurrences

---

## Five Sub-Gaps for Future Research

### Gap 1: Automated Organizational Evaluation Metrics
How do you measure whether a process rule is working? Task-level has pass/fail. Organizational level needs metrics like: rule violation rate, time-to-completion trend, escalation frequency, rework rate. No framework exists for this.

### Gap 2: Hierarchical Responsibility Attribution
TextGrad propagates a generic "blame signal" backward. No system performs structured root cause analysis asking "which role's process rule was the proximate cause of this failure?" before deciding what to update. Our structured postmortem approach is more principled but entirely manual.

### Gap 3: Rule Conflict Detection
As the rule set grows, new rules may conflict with existing ones. No system detects or resolves conflicts between organizational rules. Our architecture relies on the PI/Director noticing conflicts during review — an approach that scales poorly.

### Gap 4: Cross-Domain Rule Transfer
Our lab and studio share a common architecture and actively port rules between them. But the porting is manual and requires human judgment about applicability. No work studies whether evolved organizational rules (as opposed to agent code or weights) transfer across domains.

### Gap 5: Organizational Rule Pruning
Rules accumulate but are rarely removed. Over time, the process rules document grows monotonically. No system implements principled pruning of organizational rules — detecting rules that are no longer needed, that have been superseded, or that create more friction than they prevent.

---

## Mapping to Existing Frameworks

For researchers wanting to situate IDOE within existing taxonomies:

| Taxonomy (Fang et al. 2025) | IDOE Mapping |
|------------------------------|-------------|
| **What evolves?** | "Environment interface" — shared rules that all agents interact with |
| **Evolution signal** | "Explicit feedback" — incident postmortem, not reward signal |
| **Evolution mechanism** | "Experience accumulation" — closest, but at org level not skill level |
| **Optimization method** | "Textual gradient" (PI critique → rule rewrite) + "Archive" (versioned rules) |

| Taxonomy (Gao et al. 2025) | IDOE Mapping |
|-----------------------------|-------------|
| **Self-evolution stage** | "Post-deployment continuous improvement" |
| **Data source** | "Self-generated experience" — sprint outcomes as training data |
| **Feedback type** | "Scalar + natural language" — binary (did the rule prevent failure?) + postmortem text |

---

## References

- Reflexion: Shinn et al., NeurIPS 2023 ([arXiv 2303.11366](https://arxiv.org/abs/2303.11366))
- Self-Refine: Madaan et al., NeurIPS 2023
- TextGrad: Yuksekgonul et al., Nature 2024 ([arXiv 2406.07496](https://arxiv.org/abs/2406.07496))
- ADAS: Hu, Lu, Clune, ICLR 2025 ([arXiv 2408.08435](https://arxiv.org/abs/2408.08435))
- Godel Agent: Yin et al., ACL 2025 ([arXiv 2410.04444](https://arxiv.org/abs/2410.04444))
- Darwin Godel Machine: Zhang et al., Sakana AI, May 2025 ([arXiv 2505.22954](https://arxiv.org/abs/2505.22954))
- EvoMAC: Xue et al., ICLR 2025 ([arXiv 2410.16946](https://arxiv.org/abs/2410.16946))
- AFlow: Zhang et al., ICLR 2025 Oral ([arXiv 2410.10762](https://arxiv.org/abs/2410.10762))
- EvoAgentX: Wang et al., July 2025 ([arXiv 2507.03616](https://arxiv.org/abs/2507.03616))
- EvolveR: Wu et al., 2025 ([arXiv 2510.16079](https://arxiv.org/abs/2510.16079))
- SeaAgent: Sun et al., 2025 ([arXiv 2508.04700](https://arxiv.org/abs/2508.04700))
- CoMAS: Xue et al., 2025 ([arXiv 2510.08529](https://arxiv.org/abs/2510.08529))
- MetaGPT: Hong et al., ICLR 2024 ([arXiv 2308.00352](https://arxiv.org/abs/2308.00352))
- Agentic Neural Networks: 2025 ([arXiv 2506.09046](https://arxiv.org/abs/2506.09046))
- Fang et al. Survey: 2025 ([arXiv 2508.07407](https://arxiv.org/abs/2508.07407))
- Gao et al. Survey: 2025 ([arXiv 2507.21046](https://arxiv.org/abs/2507.21046))
