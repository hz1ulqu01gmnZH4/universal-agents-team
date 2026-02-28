# Swarm Intelligence for Problem Discovery & Evolution in Multi-Agent Systems

**Date:** 2026-02-25
**Context:** Literature review for universal-agents-team — swarm-inspired mechanisms to fight homogenization, maintain agent diversity, enable abductive reasoning, and support problem discovery in hierarchical multi-agent LLM systems.

---

## Executive Summary

This review surveys four interconnected research aspects at the intersection of swarm intelligence and multi-agent LLM systems, focusing on mechanisms that prevent homogenization and enable problem discovery:

| Aspect | Topic | Core Question |
|--------|-------|---------------|
| **K** | Swarm Diversity Maintenance | How do biological and computational swarms prevent premature convergence? |
| **L** | Novelty Search & Quality-Diversity | How can we optimize for diverse high-quality solutions rather than a single best? |
| **M** | Abductive Reasoning via Swarm Mechanisms | How can distributed agents discover problems they weren't programmed to find? |
| **N** | Heterogeneous Swarms & Cognitive Diversity | Why does agent heterogeneity improve collective performance, and how do we maintain it? |

### Key Findings

1. **Diversity is structurally necessary, not optional.** Biological evidence (honeybee polyandry, genetic diversity → colony fitness) and mathematical proof (Scott Page's Diversity Prediction Theorem) establish that diversity *causes* better collective problem-solving. Homogeneous agent swarms are fundamentally limited.

2. **Homogenization is an active threat.** LLM agents using identical models converge toward identical reasoning patterns (Sourati et al. 2025). Without architectural countermeasures, multi-agent systems degrade into expensive single-agent redundancy.

3. **Three biological mechanisms prevent convergence:** (a) structural diversity embedding at initialization (polyandry), (b) active repulsion between similar solutions (charged PSO, niching), and (c) negative feedback that decays overexploited paths (pheromone evaporation).

4. **Quality-Diversity (QD) algorithms provide the computational framework.** MAP-Elites and its variants maintain diverse behavioral repertoires rather than converging on a single optimum. QD is being rapidly applied to LLM systems (QDAIF, CycleQD, Rainbow Teaming, DebateQD) with strong results.

5. **No system combines swarm-scale anomaly detection with collective abductive reasoning.** The three-stage architecture — distributed anomaly detection (AIS) → collective signal amplification (quorum sensing) → abductive hypothesis formation — exists only as disconnected components.

6. **Empirical validation:** A diverse ensemble of 3 medium-capacity LLMs achieves 91% on GSM8K, outperforming GPT-4's 87% and homogeneous ensembles at 82% (Hegazy 2024). Diversity literally beats ability.

### Relevance to Our Architecture

Our AI Lab and Game Studio organizations already implement several swarm-inspired patterns:
- **Structural diversity**: Different model tiers (Opus/Sonnet/Haiku), specialized roles with distinct system prompts
- **Quality gates as negative selection**: Critic and Peer Reviewer roles flag anomalies
- **Incident-driven evolution (IDOE)**: A form of collective problem discovery and organizational learning
- **Stigmergic coordination**: Shared artifacts (dashboard.md, queue/) as indirect communication

**Missing mechanisms** that the literature suggests would be valuable:
- Explicit diversity metrics (no measurement of reasoning heterogeneity across agents)
- Stagnation detection (no automated monitoring of when agents converge on identical approaches)
- Scout roles (no agent with an explicit mandate to find new problem types)
- Pheromone evaporation (no systematic decay of overused reasoning patterns)
- Quorum-based anomaly escalation (anomaly detection is individual, not collective)

---

## Table of Contents

- [Part I: Aspect K — Swarm Diversity Maintenance Mechanisms](#part-i-aspect-k)
- [Part II: Aspect L — Novelty Search & Quality-Diversity Algorithms](#part-ii-aspect-l)
- [Part III: Aspect M — Abductive Reasoning & Problem Discovery](#part-iii-aspect-m)
- [Part IV: Aspect N — Heterogeneous Swarms & Cognitive Diversity](#part-iv-aspect-n)
- [Part V: Cross-Aspect Synthesis](#part-v-cross-aspect-synthesis)
- [Part VI: Gaps & Research Opportunities](#part-vi-gaps)
- [Part VII: Design Implications for Multi-Agent LLM Systems](#part-vii-design-implications)
- [Part VIII: Combined References](#part-viii-references)

---

## Part I: Aspect K — Swarm Diversity Maintenance Mechanisms

### K1. Biological Foundations

**Polyandry and Behavioral Castes:**
Queen honeybees and army ant queens mate with 10-20+ males, producing genetically diverse worker cohorts. Multiple-patriline colonies outperform single-patriline colonies in brood survival, foraging efficiency, and disease resistance (Ratnieks & Helantera 2009; Mattila & Seeley 2007 in *Science*).

Key insight: *A swarm cannot voluntarily diversify itself — diversity must be structurally embedded at initialization.* Genetically diverse castes are predisposed to different behavioral thresholds (foraging vs. nursing vs. guarding), so task specialization emerges bottom-up from diversity, not from top-down assignment.

**LLM Agent Analog:** Different model families, temperatures, system prompts, and fine-tuning create "genetic diversity" — relying on prompting alone to create diversity in homogeneous models is the equivalent of monandry.

### K2. Pheromone Evaporation (ACO)

In Ant Colony Optimization (Dorigo & Stutzle 2004), pheromone evaporation implements "useful forgetting":

```
τ(t+1) = (1-ρ)·τ(t) + Δτ
```

Without evaporation (ρ=0), the first discovered solution receives permanent reinforcement regardless of quality. High ρ → more exploration; low ρ → exploitation with risk of lock-in.

**LLM Agent Analog:** Systems that continuously reward the same reasoning path risk convergence collapse. Implementing memory decay or archive pruning — discounting overused reasoning patterns — prevents stagnation.

### K3. Premature Convergence in PSO

Blackwell (2005) demonstrated that PSO's social update rule causes rapid diversity collapse: all particles rush toward the global best, eliminating useful exploration. **Charged Particle Swarms** introduce inter-particle repulsion to maintain diversity:

- Neutral particles: standard PSO (converge toward gbest)
- Charged particles: repulsion prevents clustering
- Hybrid charged-neutral swarms balance exploration and exploitation

**LLM Agent Analog:** Agents converging on the consensus answer after a few debate rounds = "particles rushing to gbest." Explicit penalties for repeating prior agents' answers introduce computational "repulsion."

### K4. Niching and Speciation

Techniques that maintain multiple distinct subpopulations exploring different regions of the solution space:

| Technique | Mechanism | Reference |
|-----------|-----------|-----------|
| Fitness sharing | Divide fitness by niche count, penalizing crowding | Goldberg & Richardson 1987 |
| Clearing | Only best individual in each niche retains fitness | Petrowski 1996 |
| Speciation | Sub-populations evolve independently | Mahfoud 1995 |
| Parameter-free niching | Self-adaptive niche radius | Li 2010 |

**LLM Agent Analog:** Maintain agent "niches" — subgroups specializing in different hypothesis types or reasoning styles — and prevent any single niche from dominating the population.

### K5. Stagnation Detection

Rivera et al. (2023) proposed treating diversity collapse as a detectable system state requiring active intervention: dynamical sphere regrouping resets stagnating swarm subgroups.

**Three-level stagnation detection framework:**
1. **Individual level:** Agent hasn't proposed novel content in N rounds
2. **Niche level:** All agents in a subgroup converge on the same answer
3. **Population level:** Global diversity metric falls below threshold

**LLM Agent Analog:** Monitor agent agreement rate and reasoning path entropy. Trigger diversity restoration (novel hypothesis seeding, devil's advocate injection, temperature increase) when metrics cross thresholds.

### K6. Population Diversity Metrics

| Metric | Measures | Source |
|--------|----------|--------|
| Position diversity (PSO) | Mean pairwise distance between particles | Blackwell 2005 |
| Fitness diversity | Variance of fitness values | Cheng 2013 |
| Dimension-wise entropy | Information-theoretic diversity per dimension | Li et al. 2021 |
| Behavioral characterization | Position in behavior space (k-NN distance) | Lehman & Stanley 2011 |

---

## Part II: Aspect L — Novelty Search & Quality-Diversity Algorithms

### L1. Novelty Search

Lehman & Stanley (2011) demonstrated that **objective-guided search is often inferior to diversity-guided search** in deceptive fitness landscapes. By rewarding behavioral novelty (k-nearest-neighbor sparseness in behavior space) rather than objective proximity, novelty search finds solutions that objective-based evolution cannot.

Core insight: *Intermediate stepping stones toward complex solutions often look unlike the goal.* Optimizing directly for the objective can be a trap in deceptive landscapes.

The novelty metric:
```
ρ(x) = (1/k) Σ dist(x, μᵢ)    where μ₁..μₖ are k nearest neighbors in behavior space
```

### L2. MAP-Elites (Illumination Algorithms)

Mouret & Clune (2015) extended novelty search into MAP-Elites — an algorithm that **illuminates entire behavioral search spaces**, producing repertoires of diverse high-performing solutions simultaneously.

Landmark result: Cully et al. (2015, *Nature*) showed a hexapod robot with pre-computed repertoire of 13,000 gait variants could recover from damage within one minute by searching ~10 candidates from its behavioral archive.

**Algorithm:**
1. Define behavioral descriptor space (low-dimensional characterization of solutions)
2. Divide descriptor space into cells (the "map")
3. Generate random solutions, evaluate, place in corresponding cell
4. Mutate existing solutions, replace cell occupant only if quality improves
5. Result: a map of the highest-quality solution found for each behavioral niche

### L3. QD Algorithm Evolution

| Algorithm | Key Advance | QD-Score Improvement | Source |
|-----------|-------------|---------------------|--------|
| MAP-Elites | Grid-based illumination | Baseline | Mouret & Clune 2015 |
| CMA-ME | Directed exploration via CMA emitters | +40-80% over ME | Fontaine et al. 2020 |
| Multi-Emitter ME | Heterogeneous emitter portfolio + UCB | +100%+ over CMA-ME | Cully 2021 |
| PGA-MAP-Elites | Policy gradient variation operator | Top tier | Flageat et al. 2022 |
| DCG-MAP-Elites | Descriptor-conditioned gradients | +82% over PGA | Faldor et al. 2023 |

**QDax library** (Chalumeau et al. 2023): Open-source JAX-accelerated QD implementations, 10x faster than CPU baselines.

### L4. QD Applied to LLM Systems

The 2023-2025 period has seen an explosion of QD applications to LLMs:

| System | Application | Key Innovation |
|--------|------------|----------------|
| **ELM** (Lehman et al. 2023) | LLM as evolutionary mutation operator | LLMs internalize structural patterns of valid code modification |
| **QDAIF** (Bradley et al. 2023) | Creative text generation | LLM as both variation operator and behavioral evaluator |
| **CycleQD** (Kuroki et al. 2024) | LLM model merging | Prevents skill specialization collapse during multi-task fine-tuning |
| **Rainbow Teaming** (Samvelyan et al. 2024) | Red-teaming safety evaluation | MAP-Elites over adversarial attack strategies |
| **DebateQD** (Reedi et al. 2025) | Debate strategy evolution | Persuasion-optimized diversity improves reasoning generalization |
| **Diverse Prompts** (Santos et al. 2025) | Prompt engineering | MAP-Elites illuminates prompt space across BigBench tasks |
| **In-context QD** (Lim et al. 2024) | Few-shot generation | Archive examples as few-shot context for novel combinations |

### L5. Key QD Concepts for LLM Agent Design

**Behavioral Descriptors:** The dimensions that define "what kind" of solution this is (not how good). For hypothesis generation, candidate dimensions: domain focus, mechanism type, falsifiability level, reasoning style (deductive vs. inductive).

**QD-Score:** Sum of quality across all filled cells — measures both quality AND diversity simultaneously. Superior to "best solution found" as a metric.

**Coverage:** Fraction of behavioral space explored — measures how much of the solution landscape has been illuminated.

**Emitter Heterogeneity:** Rather than one agent type, maintain a portfolio (exploitative/refinement vs. exploratory/creative vs. critical/skeptical) with bandit-allocated compute.

---

## Part III: Aspect M — Abductive Reasoning & Problem Discovery

### M1. Artificial Immune Systems (AIS)

**Negative Selection (Aickelin & Dasgupta 2009):**
The immune system detects threats it has never seen by generating random detectors, maturing those that do NOT match self, and using mature detectors to flag non-self. This is anomaly detection without a prior definition of "anomaly."

**LLM Agent Analog:** Each agent maintains a representation of "normal" (its known problem categories) and flags anything that fails to match — passing flags up for collective evaluation.

**Danger Theory (Aickelin & Cayzer 2008):**
Matzinger's reformulation shifts from "is this foreign?" to "is this causing damage?" Not foreignness but *damage signals from injured cells* triggers immune response. A novel entity is not inherently dangerous — it becomes dangerous only when co-occurring with damage signals.

**LLM Agent Analog:** Rather than flagging all anomalies (overwhelming), agents should flag novelty that co-occurs with performance degradation, user frustration, or downstream failures. The "damage signal" concept maps to environmental feedback.

### M2. Quorum Sensing

Moreno-Gamez et al. (2023, *Nature Communications*) demonstrated that quorum sensing is not mere population counting — it is **collective environmental estimation**. Bacteria collectively estimate environmental conditions by pooling imperfect individual estimates, directly implementing "wisdom of the crowds" at the molecular level.

Mathematical result: The precision of collective estimates improves with √N (number of cells), independent of individual cell precision. This creates a clear optimality condition where organisms should "trust the crowd" over their own senses.

**LLM Agent Analog:** Individual agent anomaly signals are weak and noisy. A quorum threshold — only anomalies that multiple independent agents detect simultaneously are escalated — prevents false positives while amplifying genuine weak signals.

### M3. Scout/Forager Behavior

The Artificial Bee Colony algorithm (Karaboga & Basturk 2007) models three agent types:
- **Employed bees:** Exploit known food sources (known problem areas)
- **Onlooker bees:** Evaluate and select among employed bees' findings (peer review)
- **Scout bees:** Randomly search for new food sources when old ones are abandoned (problem discovery)

Key mechanism: After a food source has been exploited for a threshold number of cycles without improvement, the employed bee is converted to a scout — *forced exploration through stagnation detection.*

**LLM Agent Analog:** The scout role is explicitly missing from current multi-agent LLM architectures. No system designates agents with a mandate to find new problem types outside the known space.

### M4. Abductive Reasoning Frameworks

**Peirce's Framework:**
Abduction is the only form of reasoning that introduces new ideas. Deduction derives consequences; induction confirms patterns; abduction generates explanatory hypotheses for surprising observations.

**Garbuio & Lin (2021) — Innovative Abduction:**
In innovation contexts, abduction operates at two levels:
1. *Selective abduction:* Choosing among known hypotheses for an observed anomaly
2. *Innovative abduction:* Creating an entirely new hypothesis category — the problem frame itself is uncertain

**He & Chen (2025, TMLR) — LLM Hypothesis Discovery:**
Survey of LLM approaches to hypothesis generation and rule learning. Identifies a gap between rule learning (well-studied) and open-ended hypothesis discovery (understudied).

**Montes, Osman & Sierra (2022) — Theory of Mind + Abduction in MAS:**
Combines logical abduction with Theory of Mind (modeling what other agents believe) in multi-agent systems. Agents reason abductively about what other agents might know or have observed, enabling collaborative problem diagnosis.

### M5. The Three-Stage Architecture Gap

The literature converges on a three-stage architecture for collective problem discovery:

```
Stage 1: DISTRIBUTED ANOMALY DETECTION (AIS-inspired)
  Multiple agents independently monitor different aspects using
  negative-selection-style detectors. Gated by Danger Theory:
  only flag anomalies co-occurring with damage signals.
         │
         ▼
Stage 2: COLLECTIVE SIGNAL AMPLIFICATION (Quorum Sensing)
  Individual signals are weak and noisy. Pool them.
  Quorum threshold: only anomalies detected by multiple
  independent agents are escalated.
         │
         ▼
Stage 3: ABDUCTIVE HYPOTHESIS FORMATION (Garbuio & Lin)
  Generate candidate problem framings — not just "something
  is wrong" but "here is a hypothesis about what kind of
  problem this might be." Innovative abduction: generate
  the problem frame, not just detect the symptom.
```

**The Gap:** No existing system combines all three stages. The closest implementation (Ramkumar et al. 2024 — smart home attack diagnosis) uses Answer Set Programming rather than LLMs for the abductive step.

### M6. Stigmergic Problem Discovery

Khushiyant (2025) demonstrated that multi-LLM-agent swarms can develop **emergent collective memory** through stigmergic traces in shared environments, enabling the system to develop persistent knowledge structures analogous to ant colony pheromone trails.

Swarm Intelligence Enhanced Reasoning (Zhu et al. 2025) applies density-driven PSO to LLM reasoning, showing that treating reasoning steps as particle positions in search space enables collective exploration of the reasoning landscape.

---

## Part IV: Aspect N — Heterogeneous Swarms & Cognitive Diversity

### N1. Mathematical Foundation

**Scott Page's Diversity Prediction Theorem (2007):**
```
Collective Error = Average Individual Error − Predictive Diversity
```
This is not an empirical finding — it is a mathematical identity. Diversity in predictions is directly subtracted from collective error. The conditions: problems are complex, diversity of cognitive strategies is genuine (not nominal), and an appropriate aggregation mechanism exists.

**Empirical LLM Validation:**
Hegazy (2024) showed three diverse medium-capacity LLMs achieve 91% on GSM8K:
- vs. GPT-4 alone: 87%
- vs. homogeneous 3x medium: 82%
- **Diversity gap: +9 percentage points over homogeneous, +4 over single best**

### N2. Measuring Diversity

**System Neural Diversity (SND) — Bettini et al. (JMLR 2025):**
First rigorous metric for behavioral heterogeneity in multi-agent systems. Measures the diversity of behavioral policies across a team of agents, enabling quantitative claims about heterogeneity.

Follow-up work (2024) demonstrates that teams with higher SND find cooperative solutions more effectively in sparse-reward settings — diversity directly causes exploration success.

**The Measurement Gap:** SND exists for MARL. An analogous metric for LLM agent systems — measuring whether agents are actually reasoning differently or have converged to the same patterns — does not exist. Without measurement, diversity claims are unverifiable.

### N3. Enforcing vs. Emerging Heterogeneity

**Architectural Enforcement:**
- **Kaleidoscope** (Li et al., NeurIPS 2024): Learnable masks create structurally diverse agents from identical network parameters — each agent's mask determines what it "sees" and how it processes
- **Heterogeneous Swarms** (Feng et al., NeurIPS 2025): PSO optimizes DAG-structured multi-LLM systems where different models fill different nodes based on task requirements

**Emergent Heterogeneity:**
- **Van Diggelen et al. (2025):** Identical local Hebbian learning rules produce diverse behaviors at the collective level. Agents starting from the same initialization spontaneously specialize through interaction history — diversity emerges, not imposed.

**Model-Level Diversity:**
- **X-MAS** (Ye et al. 2025): Benchmarks 27 LLMs across 21 tasks, showing that no single model is best at everything — optimal teams are heterogeneous by construction
- **MARTI-MARS²** (Wang et al. 2026): Identifies a scaling law — homogeneous → heterogeneous training progressively increases performance ceilings

### N4. The Homogenization Threat

**Sourati et al. (2025):** Documented that widespread use of identical LLMs homogenizes reasoning outputs across users, reducing the cognitive diversity that makes collective intelligence work. This is an active convergence force, not a passive risk.

**Pekaric et al. (2025):** LLM-cybersecurity focus group found that human experts defer to AI suggestions even when wrong ("automation bias"), further concentrating reasoning toward the AI model's patterns.

**Hughes et al. (2024):** "Open-endedness is essential for ASI" — argue that artificial general intelligence requires systems that continuously generate novelty, and homogenization is the fundamental obstacle.

### N5. Design Principles for Maintained Heterogeneity

From the synthesis of N literature:

| Principle | Evidence | Implication |
|-----------|----------|-------------|
| **Diversity requires measurement** | SND (Bettini et al.) | Can't manage what you can't measure |
| **Diversity must be architectural** | Different models, roles, information access | Prompt-only diversity is shallow |
| **Expertise is a prerequisite** | Chen et al. 2025 | Diverse teams of weak agents fail; base competence required |
| **Homogenization is active** | Sourati et al. 2025 | Requires active countermeasures, not passive diversity |
| **Heterogeneity can emerge** | Van Diggelen et al. 2025 | Local learning + interaction → spontaneous specialization |
| **Disagreement needs structure** | Du et al. 2023, Hegazy 2024 | Unconstrained disagreement = noise; structured debate = synthesis |

### N6. Superorganism Theory

The SuperBrain architecture (Weigang et al. 2025) explicitly applies superorganism theory to LLM systems: individual user-LLM cognitive dyads (Subclass Brains) coordinate via swarm intelligence to form a Superclass Brain with emergent meta-intelligence.

Chen et al. (2025) provide empirical validation that cognitive diversity with leadership structure and base expertise substantially outperforms single-agent ideation for scientific proposal quality.

---

## Part V: Cross-Aspect Synthesis

### The Fundamental Connection

The four aspects are not independent — they form a coherent theory of collective intelligence:

```
ASPECT N (Heterogeneity)       ASPECT K (Diversity Maintenance)
  Why diversity matters   ←→     How to prevent diversity loss
        │                              │
        ▼                              ▼
ASPECT M (Problem Discovery)   ASPECT L (Quality-Diversity)
  What diversity enables   ←→     How to optimize for diversity
```

**The core argument:**
1. **N establishes the why:** Cognitive diversity mathematically and empirically improves collective performance
2. **K identifies the threat:** Swarms naturally converge (premature convergence, groupthink); diversity requires active maintenance
3. **L provides the framework:** Quality-Diversity algorithms optimize for diverse repertoires, not single optima
4. **M shows the payoff:** Only heterogeneous systems can perform distributed anomaly detection and collective abductive reasoning — the ultimate expression of collective intelligence

### The Biological Superorganism Parallel

Superorganisms solve exploration/exploitation and problem-discovery challenges *specifically because they are heterogeneous:*
- Scout bees are different from forager bees
- Dendritic cells are different from T-cells
- Quorum sensing in heterogeneous microbial communities produces qualitatively different dynamics than homogeneous populations

**The homogenization risk (N) directly undermines problem discovery capacity (M):** If all agents reason the same way, they detect only the same classes of problems, amplify only the same signals, and generate only the same hypotheses. A swarm of identical agents is not a superorganism — it is a single agent with redundancy.

### Key Methodological Patterns Across All Aspects

| Pattern | K Origin | L Origin | M Origin | N Origin |
|---------|----------|----------|----------|----------|
| Structural diversity at init | Polyandry | Population seeding | Negative selection repertoire | Model family diversity |
| Negative feedback / decay | Pheromone evaporation | Archive pruning | Self-space updating | Prevent echo chambers |
| Active repulsion | Charged PSO | Novelty reward | Danger signal gating | Disagreement structure |
| Stagnation detection | Diversity monitoring | Coverage tracking | Quorum thresholds | SND measurement |
| Behavioral characterization | Fitness landscape | Behavior descriptors | Anomaly classification | Reasoning style |
| Local competition | Niching | Cell replacement | Clonal selection | Niche specialization |

---

## Part VI: Gaps & Research Opportunities

### Gap 1: No Collective Abductive Architecture
No existing system combines swarm-distributed anomaly detection + quorum-threshold amplification + LLM abductive hypothesis generation. The components exist separately. **The integration is the research opportunity.**

### Gap 2: Diversity Metrics for LLM Reasoning
PSO has formalized diversity metrics. MARL has SND. LLM agent systems lack equivalent standardized metrics. Current proxies (semantic distance, disagreement rate) are ad hoc. **Need: a diversity metric suite for LLM agent populations, analogous to QD-score and coverage.**

### Gap 3: No Operational "Danger Signal" for LLM Agents
Danger Theory (Matzinger) has not been translated into LLM agent systems. What constitutes a "damage signal" (user frustration? downstream failure? task abandonment?) is undefined and unmeasured.

### Gap 4: Dynamic Diversity Management
PSO literature has stagnation detection and diversity restoration. LLM multi-agent literature focuses on static configurations. **Need: adaptive diversity control — monitor agreement rate, trigger diversity injection when consensus forms too rapidly.**

### Gap 5: The Scout Role
The ABC algorithm establishes scouts as critical for exploring unknown problem spaces. **No LLM multi-agent paper explicitly designates scout agents with a mandate to find problem types outside the known space.**

### Gap 6: Behavioral Descriptors for Hypothesis Space
MAP-Elites requires user-defined behavioral dimensions. For scientific hypothesis generation, these dimensions are unclear. **Need: automated descriptor learning (QDHF) for meaningful behavioral axes in hypothesis diversity.**

### Gap 7: Negative Feedback in LLM Agent Memory
No paper systematically studies pheromone-evaporation analogs in LLM multi-agent systems (discounting/decaying prior conclusions to prevent lock-in).

### Gap 8: QD at Inference Time
Most QD work focuses on training-time optimization. Running MAP-Elites-style search over agent configurations during a single inference session is underexplored.

### Gap 9: Abductive Reasoning at Swarm Scale
Current abductive reasoning in AI (He & Chen survey) treats it as single-agent. Multiple agents independently generating and cross-validating hypotheses about the same anomaly is unexplored.

### Gap 10: Productive Heterogeneous Disagreement vs. Echo Chambers
The echo chamber problem for LLM agent swarms is theoretically identified (Sourati et al.) but architecturally unsolved. Conditions under which diverse agents maintain diversity rather than converging through social pressure are unknown.

---

## Part VII: Design Implications for Multi-Agent LLM Systems

### Suggested Baselines

| Baseline | Description | Source |
|----------|-------------|--------|
| Homogeneous ensemble | N instances of same model, same temperature | Du et al. 2023 |
| Self-consistency | Sample K responses, majority vote | Wang et al. 2023 |
| Vanilla multi-agent debate | Homogeneous agents, unconstrained convergence | Du et al. 2023 |
| MAP-Elites archive | Explicit behavioral grid, standard MAP-Elites | Mouret & Clune 2015 |
| QDAIF | LLM variation + LLM evaluation | Bradley et al. 2023 |

### Concrete Design Recommendations

1. **Define behavioral descriptors early.** For hypothesis generation: domain focus, mechanism type, falsifiability, reasoning style. Use QDHF (Ding et al. 2024) if manual definition is difficult.

2. **Implement stagnation detection.** Monitor agreement rate and reasoning path entropy. Trigger diversity restoration when thresholds are crossed.

3. **Apply negative feedback on overused solutions.** Track heavily-explored hypotheses. Apply "evaporation" — reduce selection probability — to force novel exploration.

4. **Maintain emitter heterogeneity.** Portfolio of agent types (exploitative/refinement vs. exploratory/creative vs. critical/skeptical) with bandit-allocated compute.

5. **Measure QD-score, not just quality.** Coverage (fraction of space explored) + QD-score (sum of quality across diverse solutions) + diversity metric (mean pairwise distance in reasoning embedding space).

6. **Implement quorum-based escalation.** Individual anomaly signals → require N/3 independent confirmations before escalation to abductive reasoning phase.

7. **Designate scout agents.** At least one agent in every team should have an explicit mandate to explore outside the known problem space.

### Potential Pitfalls

1. **Behavioral descriptor collapse** — coarse dimensions produce semantically identical "diverse" solutions
2. **Quality-diversity tradeoff** — pure novelty optimization degrades quality
3. **Convergence disguised as diversity** — different words, same underlying reasoning; use semantic embeddings not lexical metrics
4. **Expensive evaluation bottleneck** — LLM QD is costly; consider BEACON (Bayesian) or surrogate-assisted methods
5. **Archive bound explosion** — use bounded archives or archive-less methods (BR-NS, Dominated Novelty Search)

---

## Part VIII: Combined References

### Must Cite (Foundational)

| # | Citation | Domain |
|---|----------|--------|
| 1 | Lehman & Stanley (2011). "Abandoning Objectives." *Evolutionary Computation* 19(2). | Novelty Search |
| 2 | Mouret & Clune (2015). "Illuminating search spaces by mapping elites." arXiv:1504.04909 | MAP-Elites |
| 3 | Cully et al. (2015). "Robots that can adapt like animals." *Nature* 521. | QD application |
| 4 | Dorigo & Stutzle (2004). *Ant Colony Optimization.* MIT Press. | ACO / diversity |
| 5 | Page (2007). *The Difference.* Princeton University Press. | Diversity theorem |
| 6 | Bonabeau, Dorigo, Theraulaz (1999). *Swarm Intelligence.* | Field foundation |
| 7 | Aickelin & Dasgupta (2009). AIS Tutorial. arXiv:0910.4899 | Immune systems |
| 8 | Aickelin & Cayzer (2008). Danger Theory. arXiv:0801.3549 | Problem discovery |
| 9 | Garbuio & Lin (2021). Abductive reasoning in innovation. | Abduction theory |
| 10 | Du et al. (2023). "Multiagent Debate." arXiv:2305.14325 | LLM debate |

### Should Cite (Directly Relevant)

| # | Citation | Domain |
|---|----------|--------|
| 11 | Bradley et al. (2023). QDAIF. arXiv:2310.13032 | QD + LLM |
| 12 | Kuroki et al. (2024). CycleQD. arXiv:2410.14735 | QD + LLM merging |
| 13 | Hegazy (2024). Diversity of Thought. arXiv:2410.12853 | Diversity > ability |
| 14 | Lim et al. (2024). In-context QD. arXiv:2404.15794 | QD + few-shot |
| 15 | Cully (2021). Multi-Emitter MAP-Elites. arXiv:2007.05352 | QD algorithm |
| 16 | Blackwell (2005). Particle swarms and diversity. *Soft Computing* 9(11). | PSO diversity |
| 17 | Feng et al. (2025). Heterogeneous Swarms. arXiv:2502.04510 | LLM-DAG optimization |
| 18 | Bettini et al. (2023). System Neural Diversity. arXiv:2305.02128 | Diversity metric |
| 19 | Moreno-Gamez et al. (2023). Quorum sensing. *Nature Communications*. | Collective estimation |
| 20 | Karaboga & Basturk (2007). ABC algorithm. | Scout/forager model |
| 21 | Sourati et al. (2025). Homogenizing effect of LLMs. arXiv:2508.01491 | Homogenization threat |
| 22 | He & Chen (2025). LLM hypothesis discovery. arXiv:2505.21935 | Abduction + LLM |
| 23 | Montes, Osman & Sierra (2022). ToM + Abduction. arXiv:2209.15279 | MAS abduction |
| 24 | Ye et al. (2025). X-MAS benchmark. arXiv:2505.16997 | Heterogeneous LLM |
| 25 | Wang et al. (2026). MARTI-MARS² scaling law. arXiv:2602.07848 | Het. scaling |

### Consider Citing (Context)

| # | Citation | Domain |
|---|----------|--------|
| 26 | Mattila & Seeley (2007). Genetic diversity in honeybees. *Science* 317(5836). | Bio foundation |
| 27 | Ratnieks & Helantera (2009). Extreme polyandry. *Phil Trans B*. | Bio foundation |
| 28 | Lehman et al. (2023). Evolution through Large Models. arXiv:2206.08896 | ELM |
| 29 | Samvelyan et al. (2024). Rainbow Teaming. NeurIPS 2024. | QD + safety |
| 30 | Reedi et al. (2025). DebateQD. arXiv:2510.05909 | QD + debate |
| 31 | Santos et al. (2025). Diverse Prompts. arXiv:2504.14367 | QD + prompts |
| 32 | Li et al. (2024). Kaleidoscope. arXiv:2410.08540 | MARL diversity |
| 33 | Van Diggelen et al. (2025). Emergent heterogeneity. arXiv:2507.11566 | Hebbian |
| 34 | Rivera et al. (2023). Dynamical sphere regrouping. *Mathematics*. | Stagnation |
| 35 | Cheng et al. (2014). Brain storm optimization diversity. *JAISCR*. | PSO diversity |
| 36 | Chen et al. (2025). Beyond Brainstorming. arXiv:2508.04575 | MAS + science |
| 37 | Weigang et al. (2025). SuperBrain. arXiv:2509.00510 | Superorganism |
| 38 | Ramkumar et al. (2024). Abductive attack diagnosis. arXiv:2412.10738 | Abduction app |
| 39 | Khushiyant (2025). Emergent collective memory. arXiv:2512.10166 | Stigmergy |
| 40 | Zhu et al. (2025). Swarm-enhanced reasoning. arXiv:2505.17115 | Swarm + LLM |
| 41 | Havrilla et al. (2024). QDC in synthetic data. arXiv:2412.02980 | QD + training |
| 42 | Ding et al. (2024). QDHF. arXiv:2310.12103 | Learned descriptors |
| 43 | Fontaine et al. (2020). CMA-ME. arXiv:1912.02400 | QD algorithm |
| 44 | Chalumeau et al. (2023). QDax. arXiv:2308.03665 | QD library |
| 45 | Hughes et al. (2024). Open-endedness for ASI. arXiv:2406.04268 | Open-ended AI |
| 46 | Mitchener et al. (2025). Kosmos AI Scientist. arXiv:2511.02824 | AI discovery |
| 47 | Cui & Yasseri (2024). AI-Enhanced Collective Intelligence. arXiv:2403.10433 | Human-AI CI |

### Key Author Clusters

| Cluster | Researchers | Affiliation |
|---------|-------------|-------------|
| Swarm Intelligence Foundations | Dorigo, Bonabeau, Theraulaz, Karaboga, Birattari | Various |
| Artificial Immune Systems | Aickelin, Dasgupta, Cayzer, De Castro, Timmis | Nottingham, Memphis |
| Diversity Theory (ML) | Scott Page, Gavin Brown, Kagan Tumer | Michigan, Manchester |
| MARL Diversity | Amanda Prorok, Matteo Bettini | Cambridge |
| QD Algorithms | Mouret, Cully, Lehman, Stanley | Various |
| Heterogeneous LLM Ensembles | Shangbin Feng, Tomas Pfister, Chen-Yu Lee | Google |
| Multi-Agent Debate | Yilun Du, Igor Mordatch, Mahmood Hegazy | MIT, DeepMind |
| Abductive Reasoning AI | Massimo Garbuio, Kaiyu He, Zhiyu Chen | Macquarie, Various |
| LLM Homogenization | Morteza Dehghani, Zhivar Sourati | USC |
| Open-Ended AI | Joel Lehman, Kenneth Stanley, Edward Hughes | DeepMind |

---

## Open-Source Implementations

| System | Function | Source |
|--------|----------|-------|
| QDax | Hardware-accelerated QD algorithms (JAX) | arXiv:2308.03665 |
| X-MAS | Heterogeneous LLM benchmark (27 models) | arXiv:2505.16997 |
| Kaleidoscope | Learnable masks for MARL diversity | github.com/LXXXXR/Kaleidoscope |
| Model Swarms | Collaborative LLM search in weight space | arXiv:2410.11163 |
| Heterogeneous Swarm | PSO-optimized multi-LLM DAG | arXiv:2502.04510 |
| swarm_gpt | LLM agents in NetLogo swarm simulations | github.com/crjimene/swarm_gpt |
| Kosmos AI Scientist | Literature search + hypothesis generation | arXiv:2511.02824 |
| Behavior Discovery | Novelty search for heterogeneous robot swarms | sites.google.com/view/heterogeneous-bd-methods |

---

*Compiled from parallel literature research on Aspects K, L, M, N.*
*Detailed per-paper catalogs available in:*
- `../literature_review_swarm_diversity_QD.md` (Aspects K+L, 1150 lines)
- `../literature_review_swarm_aspects_MN.md` (Aspects M+N, 744 lines)
