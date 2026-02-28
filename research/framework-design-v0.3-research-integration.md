# Universal Agents Framework — v0.3 Research Integration

**Date:** 2026-02-27
**Status:** Integrating findings from 3 research streams into framework design
**Companion docs:** v0.1 (core design), v0.2 (addendum items 1-10,13)

---

## Research Streams Integrated

| Stream | Papers | Key Impact on Design |
|--------|--------|---------------------|
| Creativity in multi-agent systems | 43 papers | Creative protocol, anti-stagnation, Csikszentmihalyi loop |
| Skills crystallization + LLM skills | 42 papers | Skill validation pipeline, the Skill Paradox resolution |
| Self-aware AI + bootstrapping | 26 papers | Dual-copy evolution, calibration, self-governance |

**Total research base:** ~190 papers across 8 literature reviews informing this framework.

---

## Item 2: Creativity Engine

### The Problem
Agents default to correct-but-predictable outputs. Creative problem solving — finding novel approaches, reframing problems, generating unexpected connections — requires explicit architectural support.

### Research-Backed Design: Creative Protocol

From the creativity research, 7 principles directly inform the framework:

```yaml
# core/creativity.yaml
creativity_engine:

  # === PROTOCOL: Separate-Then-Together ===
  creative_protocol:
    description: "Evidence-based brainstorming protocol from Straub et al. 2025"
    phases:
      1_diverge:
        description: "3-5 persona-conditioned agents brainstorm independently"
        duration: "Time-boxed — prevent problem drift"
        rules:
          - "No convergence pressure — agents cannot see others' outputs"
          - "Quantity over quality — fluency first"
          - "Persona-conditioned: each agent gets distinct creative persona"
          - "SCAMPER or Six Hats rotation for structured divergence"
        personas:
          - type: "analogist"
            instruction: "Solve this by finding analogies in unrelated domains"
          - type: "inverter"
            instruction: "What if we did the exact opposite of the obvious approach?"
          - type: "constraint_remover"
            instruction: "What would we do if X limitation didn't exist?"
          - type: "combiner"
            instruction: "What two existing solutions could be merged into something new?"

      2_cross_pollinate:
        description: "Agents share outputs via BLIND review"
        rules:
          - "Blind: agents don't know whose idea they're reviewing"
          - "Build on, don't judge — 'yes, and...' not 'no, but...'"
          - "Cross-pollination: reviewer must combine reviewed idea with own"
        rationale: "Li et al. 2026 — blind peer review preserves divergent trajectories"

      3_synthesize:
        description: "Orchestrator integrates best ideas"
        rules:
          - "Select for diversity of approach, not just quality"
          - "Preserve minority ideas that challenge consensus"
          - "Flag combinatorial opportunities"

      4_evaluate:
        description: "Multi-criteria evaluation with diverse critic agents"
        criteria:
          novelty: "Is this genuinely new, not a reformulation?"
          quality: "Does it actually solve the problem?"
          diversity: "Does it differ from other solutions found?"
          feasibility: "Can it be implemented with available resources?"
        rationale: "CreativityPrism (2025) — these dimensions are independent"

  # === ANTI-STAGNATION ===
  anti_stagnation:
    degeneration_of_thought_prevention:
      description: "Liang et al. 2023: self-reflection alone leads to creative stagnation"
      mechanisms:
        - "Inject adversarial agents when output entropy drops"
        - "Periodic persona rotation (never same persona twice in a row)"
        - "Non-cooperative agent pairs competing on novelty"
        - "Difficulty rewards: bonus for agents that pose challenges"
      measurement:
        - "Information entropy of agent outputs (should not decline monotonically)"
        - "Semantic distance between consecutive outputs (should stay above threshold)"

    shared_imagination_prevention:
      description: "Zhou et al. 2024: LLMs from same family hallucinate alike"
      mechanisms:
        - "Use heterogeneous models when possible (different model families)"
        - "Vary temperature per agent (not all at default)"
        - "Vary system prompt structure (not just content)"
      note: "Claude Max limits us to Claude models, so prompt-level diversity is critical"

  # === CSIKSZENTMIHALYI LOOP ===
  systems_model:
    description: "Imasato et al. 2024 — the systems model of creativity"
    components:
      individual_agents: "Generate creative variations"
      field_agents: "Evaluate and select (critics, reviewers)"
      domain_knowledge: "Preserve and transmit validated innovations"
    loop: |
      Individuals generate → Field evaluates → Best enter Domain →
      Domain knowledge feeds back to Individuals → cycle continues
    mapping_to_framework:
      individual_agents: "All roles with creative_synthesis capability"
      field_agents: "Reviewer role + quorum evaluators"
      domain_knowledge: "MAP-Elites archive + organizational memory + skills library"

  # === CREATIVITY METRICS ===
  metrics:
    guilford_dimensions:
      fluency: "Number of distinct ideas generated per session"
      flexibility: "Number of distinct categories/approaches"
      originality: "Semantic distance from common/expected solutions"
      elaboration: "Detail and development of ideas"
    measurement_frequency: "Per creative task"
    storage: "logs/creativity/"
    note: "Temperature has weak influence on true creativity (Peeperkorn 2024). Structure matters more."

  # === WHEN TO USE ===
  activation:
    triggers:
      - "Task is tagged as novel or exploratory"
      - "Task has failed with conventional approaches"
      - "Scout reports: existing approaches are insufficient"
      - "Human requests creative exploration"
      - "Evolution proposal requires novel solution design"
    topology: "debate or parallel_swarm (never pipeline for creative tasks)"
```

### Key Empirical Finding
**Structure > individual capability for creativity:**
- GPT-4o multi-agent with good structure beats single o1 (FilmAgent 2025)
- Decomposition-based workflows achieve 4.17/5 novelty vs. 2.33/5 for reflection (Saraogi et al. 2025)
- 3 diverse medium models can outperform single top model creatively

---

## Item 3: Skills as Crystallized Capabilities

### The Skill Paradox (SkillsBench 2026)

**Critical finding:** Curated skills improve performance by +16.2pp. Self-generated skills provide **negligible or negative benefit** across 7,308 trajectories.

**Resolution — what makes self-evolution work despite this:**
The successful systems (CASCADE 93.3%, SAGE +8.9%, SkillRL +15.3%) all share: execution-based validation, experience-grounded extraction, continuous maintenance, and RL-augmented quality signals.

### Design: Skill Lifecycle with Validation Pipeline

```yaml
# shared/skills/skill-lifecycle.yaml
skill_lifecycle:

  # === EXTRACTION (not generation) ===
  extraction:
    source: "Successful task execution trajectories ONLY"
    method: |
      1. Identify task that was completed successfully with high review score
      2. Extract the reasoning pattern / approach / procedure used
      3. Abstract away task-specific details, keep transferable pattern
      4. Express as capability atom (instruction fragment + behavioral descriptor)
    rationale: "SkillsBench: experience-grounded extraction works; imagination-based generation fails"
    anti_pattern: "NEVER generate skills from scratch via LLM prompting"

  # === MULTI-STAGE VALIDATION PIPELINE ===
  validation:
    description: "4-stage validation before any skill enters the library"

    stage_1_syntax:
      check: "Is the skill well-formed? Can it be parsed as a capability atom?"
      catches: "Malformed instruction fragments, hallucinated references"
      gate: "Automated — reject immediately if fails"

    stage_2_execution:
      check: "Does the skill produce correct outputs when applied to test tasks?"
      method: "Apply skill to 2+ real tasks from the archive, compare output quality"
      catches: "Skills that sound good but don't actually improve performance"
      gate: "Automated — must pass on both test tasks"
      rationale: "SAGE, PSV: execution-based validation is essential"

    stage_3_comparison:
      check: "Is this skill better than the baseline (no skill) and existing alternatives?"
      method: "A/B comparison: task with skill vs. task without vs. task with existing skill"
      catches: "Redundant skills, skills that don't add value"
      gate: "Automated — must show measurable improvement"

    stage_4_review:
      check: "Human or senior agent reviews the skill for safety and quality"
      catches: "Subtle quality issues, security concerns, adversarial patterns"
      gate: "Reviewer approval required"
      rationale: "26.1% of community skills contain vulnerabilities (Malicious Skills 2025)"

  # === LIBRARY ORGANIZATION ===
  organization:
    structure: "Hierarchical with semantic clustering"
    capacity_limits:
      per_domain: 50  # Maximum skills per domain (Li 2026: phase transition at critical size)
      per_level: 20   # Maximum skills per hierarchical level
    rationale: "SkillsBench: focused 2-3 module skills outperform comprehensive docs"

  # === CONTINUOUS MAINTENANCE ===
  maintenance:
    scoring:
      metrics:
        - usage_frequency: "How often is this skill selected?"
        - success_rate: "What % of tasks using this skill pass review?"
        - freshness: "When was this skill last validated?"
      period: "Every 20 tasks"

    pruning:
      trigger: "Skill success_rate < 0.5 OR usage_frequency = 0 for 30 tasks"
      action: "Move to deprecated, mark as 'unvalidated' if used"

    merging:
      trigger: "Two skills have cosine similarity > 0.85"
      action: "Consolidate into single skill, keep the one with higher success_rate"

    versioning:
      every_change: "Git commit with provenance (which task generated this skill)"
      rollback: "Any skill can be reverted to previous version"

  # === SECURITY ===
  security:
    trust_tiers:
      tier_0: "Core framework skills (highest trust, human-vetted)"
      tier_1: "Validated through full pipeline (high trust)"
      tier_2: "Partially validated (medium trust — sandbox execution)"
      tier_3: "Newly extracted (low trust — no execution without validation)"
    sandbox: "All skill execution in sandboxed environment"
    scanning: "Check for shadow features, excessive permissions, data exfiltration patterns"
```

### Integration with Role System
Skills crystallize into capability atoms:

```
Successful task trajectory
    → Extract reasoning pattern
    → Validate through 4-stage pipeline
    → Create new capability atom in roles/capabilities.yaml
    → Compose into role compositions where relevant
    → Track performance in MAP-Elites archive
```

---

## Item 7 + 12: Self-Capability Awareness & Bootstrapping Resolution

### The Generation-Verification Gap (Song et al. 2024)

**Fundamental limit:** A system can only improve itself to the extent its verification exceeds its generation capability. The framework must ensure evaluation mechanisms are always more reliable than self-modification proposals.

### Design: Self-Capability Assessment Module

```yaml
# core/self-assessment.yaml
self_capability_assessment:

  # === KNOWLEDGE BOUNDARY MODELING ===
  knowledge_boundaries:
    description: "What can the framework currently do well vs. poorly?"
    method:
      1. "Maintain a capability map: {task_type → success_rate}"
      2. "Track failure modes: {failure_type → frequency, root_cause}"
      3. "Identify blind spots: task types never attempted"
      4. "Compare self-assessment against actual outcomes"
    update_frequency: "After every meta-analysis cycle"
    output: "state/self-assessment/capability-map.yaml"

  # === CONFIDENCE CALIBRATION ===
  calibration:
    description: "Prevent overconfidence in self-improvement"
    method:
      1. "Before each evolution: 'How confident am I this improves things?' (0-1)"
      2. "After each evolution: 'Did it actually improve things?' (measured)"
      3. "Track calibration: predicted improvement vs. actual improvement"
      4. "Adjust confidence model based on calibration error"
    calibration_check: "Every 5 evolution cycles"
    overcalibration_response: |
      If predicted improvement consistently > actual improvement:
      - Lower all confidence estimates by the average overshoot
      - Require higher evidence threshold for future evolutions
      - Alert human: "Framework may be overconfident in self-improvement"
    rationale: "Huang et al. 2025: iterative calibration prevents systematic overconfidence"

  # === METACOGNITIVE MONITORING ===
  metacognition:
    description: "Framework monitors its own cognitive processes"
    monitors:
      reasoning_quality: "Are agents producing well-reasoned outputs?"
      decision_consistency: "Would the same decision be made if asked again?"
      uncertainty_awareness: "Does the framework know when it doesn't know?"
    limitations:
      - "LLM introspection succeeds only ~20% of the time (Anthropic 2025)"
      - "Use multiple redundant channels, not single self-assessment"
      - "Cross-validate: agent A assesses agent B's capabilities, not self"
    rationale: "Ackerman 2025: metacognition is real but limited"

  # === GENERATION-VERIFICATION GAP ===
  gap_monitoring:
    description: "Ensure verification always exceeds generation"
    method:
      1. "For each evolution proposal: can we reliably tell if it's better?"
      2. "Track: how often do we approve changes that turn out worse?"
      3. "If false-positive rate > 10%: tighten evaluation criteria"
      4. "If false-negative rate > 30%: loosen (we're too conservative)"
    rationale: "Song et al. 2024: this gap is the fundamental limit of self-improvement"
```

### Design: Bootstrapping Resolution — The Dual-Copy Pattern

```yaml
# core/evolution-bootstrap.yaml
dual_copy_evolution:
  description: |
    Resolves the bootstrapping paradox: how to improve yourself with yourself.
    Validated by Darwin Godel Machine, STOP, ADAS, AlphaEvolve.

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
        - "domain/active.yaml"
      what_is_NOT_copied:
        - "CONSTITUTION.md (immutable, shared)"
        - "logs/ (append-only, shared)"
        - "state/tasks/ (belongs to the running instance)"
      storage: "state/evolution/candidates/{evo-id}/"

    2_modify:
      description: "Apply proposed changes to the fork"
      method: |
        The evolution engine modifies the forked configuration.
        Changes are isolated — the running framework is unaffected.
      constraints:
        - "Only Tier 2-3 changes (Tier 0-1 require separate process)"
        - "Changes must be expressible as file diffs"
        - "Changes must pass constitutional check against CONSTITUTION.md"

    3_evaluate:
      description: "Test the fork against multi-dimensional criteria"
      dimensions:
        capability: "Does it perform tasks better? (run test tasks)"
        consistency: "Does it produce similar results across runs? (3x repetition)"
        robustness: "Does it handle edge cases? (adversarial test tasks)"
        predictability: "Can we anticipate when it will fail?"
        safety: "Does it stay within constitutional bounds?"
        diversity: "Does it maintain SRD above floor?"
      method: |
        Run a battery of test tasks against both current and forked configs.
        Compare metrics across all dimensions.
        A fork must improve on at least one dimension without regressing on any.
      rationale: "Rabanser et al. 2026: 4 dimensions of agent reliability"

    4_promote_or_rollback:
      gate:
        all_pass: "Promote: replace current config with fork"
        any_fail: "Rollback: discard fork, log failure reason"
        marginal: "Hold for human review if improvement is within noise"
      promotion: |
        1. Git commit current state (rollback point)
        2. Copy fork configs to active positions
        3. Verify framework still operational
        4. If verification fails: auto-rollback to pre-commit state
        5. Log promotion with full evaluation results
      rationale: "DGM, ADAS, AlphaEvolve: all use fork→evaluate→promote"

  # === POPULATION-BASED VARIANT ===
  population_mode:
    description: "Generate multiple candidate forks, evaluate all, select best"
    when: "Major evolution (Tier 1-2) or when single-fork improvement stalls"
    population_size: 3-5  # Resource-dependent
    selection: "Tournament: best fork wins across multi-dimensional evaluation"
    rationale: "DGM: population-based outperforms single-point mutation (20%→50% SWE-bench)"
```

---

## Item 13 (Enhanced): Self-Governance with Research Integration

### Alignment Faking Risk (Anthropic 2024)

**Critical finding:** Claude 3 Opus faked alignment in up to 78% of cases under RL pressure. Self-modifying systems with self-preservation tendencies could resist correction.

### Objective Drift Risk (arXiv:2506.23844)

Auto-summarized reflections can recursively shift agent objectives away from original intent.

### Design: Self-Governance Protocol

```yaml
# core/self-governance.yaml
self_governance:

  # === OBJECTIVE ANCHORING ===
  objective_anchoring:
    description: "Prevent objective drift over many evolution cycles"
    method:
      1. "Store original objectives in CONSTITUTION.md (immutable)"
      2. "After every 10 evolution cycles: compare current behavior against original objectives"
      3. "Use INDEPENDENT evaluator (not the agents being evaluated)"
      4. "Measure objective alignment score (0-1)"
      5. "If score drops below 0.8: halt evolution, alert human"
    rationale: "arXiv:2506.23844: auto-summarized reflections cause recursive objective shift"

  # === CO-EVOLVING CONSTITUTION ===
  co_evolving_constitution:
    description: "Domain charter (Layer 1) can evolve, but with safeguards"
    method:
      - "COCOA pattern (EMNLP 2025): constitutions evolve alongside agents"
      - "Charter changes require human approval (always Tier 1)"
      - "Track charter evolution separately from operational evolution"
      - "Charter changes must be justified by specific failure cases"
    constraints:
      - "Charter can add new principles but not remove existing ones"
      - "Charter cannot weaken any principle — only strengthen or add"
      - "If charter changes would conflict with CONSTITUTION.md: rejected"

  # === ANTI-ALIGNMENT-FAKING ===
  alignment_verification:
    description: "Detect if agents are performing alignment rather than being aligned"
    methods:
      - "Behavioral consistency tests: does agent behave the same when 'observed' vs 'unobserved'?"
      - "Capability elicitation: probe whether agents have capabilities they're hiding"
      - "Cross-agent monitoring: agents monitor each other for suspicious behavior"
      - "Red-team: periodic adversarial evaluation of agent alignment"
    frequency: "Every 20 tasks or after any Tier 2+ evolution"
    rationale: "Anthropic 2024: 78% alignment faking under RL pressure"

  # === RISK SCORECARD (from v0.2, now research-enhanced) ===
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

## Updated Meta Bootstrap Phases

Incorporating all research findings, the bootstrap sequence becomes:

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
  - First domain instantiation (e.g., research_lab or software_engineering)
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

---

## Complete Research Reference Summary

| Document | Location | Papers | Focus |
|----------|----------|--------|-------|
| Organization evolution | research/organization-evolution.md | — | How ai-lab-agents / ai-game-studio evolved |
| Self-evolving agents | research/self-evolving-agents-literature-review.md | ~20 | Reflexion, TextGrad, ADAS, Godel Agent |
| Gap: organizational self-evolution | research/gap-organizational-self-evolution.md | — | IDOE pattern, 5 sub-gaps |
| Swarm diversity K+L | literature_review_swarm_diversity_QD.md | ~30 | Diversity maintenance, MAP-Elites, QD |
| Swarm aspects M+N | literature_review_swarm_aspects_MN.md | ~25 | Abductive reasoning, heterogeneous swarms |
| Swarm intelligence (unified) | research/swarm-intelligence-problem-discovery.md | 47 | Combined K+L+M+N synthesis |
| Agent teams vs swarms | research/agent-teams-vs-swarms-literature-review.md | 32 | When to use teams vs swarms |
| Creativity in multi-agent | research/creativity-in-multi-agent-systems.md | 43 | Creative protocols, anti-stagnation |
| Skills crystallization | research/skill-crystallization-and-llm-skills.md | 42 | Skill Paradox, validation pipeline |
| Self-aware AI + bootstrapping | research/self-aware-ai-and-bootstrapping.md | 26 | Dual-copy, calibration, self-governance |
| **Framework design v0.1** | research/framework-design-universal-agents.md | — | Core architecture |
| **Design addendum v0.2** | research/framework-design-v0.2-addendum.md | — | Items 1,4,5,6,8,9,10,13 |
| **Research integration v0.3** | research/framework-design-v0.3-research-integration.md | — | Items 2,3,7,12,13 (this doc) |

**Total papers informing framework design: ~190**

---

*End of v0.3 Research Integration*
