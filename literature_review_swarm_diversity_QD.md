# Literature Review: Swarm Diversity Maintenance & Quality-Diversity Algorithms
## Aspects K and L — Comprehensive Survey

**Date:** 2026-02-25
**Scope:** Biological swarm diversity, PSO/ACO diversity mechanisms, Novelty Search, MAP-Elites/QD algorithms, LLM/agent applications

---

## PART I: ASPECT K — Swarm Diversity Maintenance Mechanisms

---

### K1. Biological Foundations: Polyandry and Behavioral Castes

**K1.1 — Ant Colony and Honeybee Polyandry**

**Key Reference:**
- Ratnieks, F.L.W., Helantera, H. (2009). *Extreme polyandry in social Hymenoptera: evolutionary causes and consequences for colony organisation.* Philosophical Transactions of the Royal Society B.
- Supporting: Palmer, K.A., Oldroyd, B.P. "Evolution of extreme polyandry in the honeybee Apis mellifera L." (2000). Multiple publications via PubMed, Springer.

**Core Idea:**
Queen honeybees and army ant queens mate with 10–20+ males (hyperpolyandry), producing genetically diverse worker cohorts. The genetic diversity among half-sisters confers colony-level benefits: improved disease resistance, better task allocation, and more stable homeostasis under environmental fluctuation. Multiple-patriline colonies outperform single-patriline colonies in brood survival, foraging efficiency, and resilience to pathogens.

**Mechanism:**
- Genetically diverse castes are predisposed to different behavioral thresholds (foraging vs. nursing vs. guarding)
- Genetic diversity provides a buffer against pathogen adaptation ("moving target" hypothesis)
- Task specialization emerges bottom-up from genotype-linked behavioral thresholds, not from top-down assignment

**Relevance to Multi-Agent LLM:**
Polyandry is the biological implementation of *forced diversity* in a collective system. The insight is that a swarm cannot voluntarily diversify itself; diversity must be *structurally embedded* at initialization. For LLM agent systems, this argues for diverse model initialization strategies (different fine-tuning, different temperature, different system prompts) rather than letting homogeneous agents self-diversify through prompting alone.

---

**K1.2 — Genetic Diversity Promotes Colony Homeostasis**

**Reference:**
- Mattila, H.R., Seeley, T.D. (2007). "Genetic Diversity in Honey Bee Colonies Enhances Productivity and Fitness." *Science*, 317(5836):362–365.
- Also: "Genetic diversity promotes homeostasis in insect colonies." *Trends in Ecology & Evolution*, 22(8):408–416.

**Core Idea:**
Colonies with high genetic diversity showed superior performance in temperature regulation, foraging, reproduction, and disease resistance. The 2007 Science paper is a landmark empirical demonstration that swarm diversity directly causes fitness improvements, not merely correlates with them.

**Relevance:**
Provides empirical evidence that diversity in a swarm *causes* better collective problem-solving, directly analogous to heterogeneous multi-agent reasoning ensembles.

---

### K2. Pheromone Evaporation as Negative Feedback (ACO)

**Key Reference:**
- Dorigo, M., Stutzle, T. (2004). *Ant Colony Optimization.* MIT Press. ISBN: 0-262-04219-3.

**Core Idea:**
In biological ant colonies and Ant Colony Optimization (ACO) algorithms, pheromone evaporation is the canonical negative feedback mechanism that prevents path lock-in. Without evaporation, the first discovered solution (often suboptimal) becomes permanently reinforced and the colony cannot adapt. Evaporation implements "useful forgetting," biasing exploration toward novelty by decaying reward on previously-exploited paths.

**Methodology:**
- Pheromone level τ(t+1) = (1-ρ)·τ(t) + Δτ, where ρ is the evaporation rate
- High ρ → fast forgetting, more exploration, less convergence
- Low ρ → strong memory, exploitation of known paths, risk of lock-in

**Key Results:**
- Algorithms without evaporation converge on suboptimal paths and stagnate
- Tuning ρ controls the exploration-exploitation balance
- Stagnation detection and restart mechanisms are needed when diversity collapses

**Relevance:**
Pheromone evaporation = LLM agent "memory decay" or "archive pruning." Systems that continuously reward the same reasoning path risk convergence collapse. Implementing negative feedback in agent scoring (discounting overused reasoning patterns) prevents stagnation.

---

### K3. Premature Convergence as a Failure Mode in Particle Swarm Optimization

**Key Reference:**
- Blackwell, T.M. (2005). "Particle swarms and population diversity." *Soft Computing*, 9(11):793–802.
- Google Scholar: 161 citations.

**Core Idea:**
Blackwell proposed formal diversity metrics for PSO and demonstrated that the "social" update rule causes rapid diversity collapse: all particles rush toward the global best, eliminating useful exploration. Charged particle swarms introduce electrostatic inter-particle repulsion to maintain diversity.

**Mechanism — Charged PSO:**
- Neutral particles: standard PSO behavior (converge toward gbest)
- Charged particles: inter-particle repulsion prevents clustering
- Hybrid charged-neutral swarms balance exploration and exploitation

**Related Work:**
- Cheng, S. (2013). "Population Diversity in Particle Swarm Optimization: Definition, Observation, Control, and Application." University of Liverpool dissertation. (34 citations)
- Cheng, S., Shi, Y., Qin, Q., Zhang, Q., Bai, R. (2014). "Population diversity maintenance in brain storm optimization algorithm." *Journal of Artificial Intelligence and Soft Computing Research*. (156 citations)

**Key Failure Mode:**
Standard PSO diversity collapses rapidly in later iterations, leaving the algorithm stuck near the global best but unable to escape local optima.

**Relevance:**
The "particle rushing to gbest" failure mode is directly analogous to LLM agents converging on the consensus answer after a few rounds of debate, eliminating productive disagreement. Introducing "repulsion" (explicit penalties for agents that repeat prior agent answers) is a direct computational analog.

---

### K4. Niching and Speciation for Multi-Modal Diversity Maintenance

**Key References:**
- Petrowski, A. (1996). "A clearing procedure as a niching method for genetic algorithms." ICEC.
- Li, X. (2010). "Niching Without Niching Parameters: Particle Swarm Optimization Using a Ring Topology." *IEEE Trans. Evolutionary Computation*, 14(1):150–169.
- Dynamic niching PSO with external archive: *Information Sciences*, 2023 (ScienceDirect).

**Core Idea:**
Niching algorithms maintain multiple sub-populations ("niches" or "species") simultaneously, each exploring a different region of the search space. Clearing, crowding, and fitness sharing are classic mechanisms. Speciation-based PSO divides particles into species based on similarity, preventing inter-species social influence.

**Mechanisms:**
1. **Fitness Sharing:** Reduces fitness of solutions in crowded regions, rewarding exploration of sparse areas
2. **Crowding:** New solutions replace similar (not random) population members
3. **Clearing:** Only the best individual in each niche retains full fitness
4. **Speciation:** Particles only interact within their species (neighborhood)

**Key Results:**
- Niching methods reliably find multiple optima simultaneously
- Prevents "winner-take-all" collapse to single solution
- Adaptive niching (no fixed radius parameter) improves robustness

**Relevance:**
Niching = maintaining multiple active hypothesis clusters in a multi-agent LLM system. Rather than converging on one "best" answer, the system maintains K distinct reasoning lineages.

---

### K5. Population Diversity Metrics

**Key Reference:**
- Li, Y., et al. (2021). "A Diversity Model Based on Dimension Entropy and Its Application to Swarm Intelligence Algorithm." *Entropy*, 23(4):397. PMC8065515.

**Core Idea:**
Formally defines diversity metrics for swarm populations. Dimension entropy measures the distribution of particles across each dimension of the search space. Other metrics include:
- **Position diversity:** Mean pairwise Euclidean distance between all particles
- **Velocity diversity:** Spread of particle velocities
- **Fitness diversity:** Variance in objective function values
- **Entropy-based metrics:** Treat the population distribution as a probability distribution

**Key Insight:**
Different diversity metrics capture different aspects of population collapse. Position diversity can remain high while fitness diversity collapses (particles spread out but all evaluating similarly). Monitoring multiple metrics is necessary.

**Relevance:**
For LLM agent systems, diversity metrics could include:
- Semantic embedding distance between agent outputs
- Divergence in reasoning chain lengths/structures
- Disagreement rate on factual claims
- Entropy of probability distributions over answer choices

---

### K6. Stochastic Resonance and Noise Injection

**Key Reference:**
- Novel randomized PSO (RPSO): "A novel randomised particle swarm optimizer," *International Journal of Machine Learning and Cybernetics*, Springer, 2020.

**Core Idea:**
Introducing Gaussian white noise with adjustable intensity into particle update rules maintains diversity and prevents premature convergence. This is a form of controlled stochastic resonance: a moderate level of noise improves performance by enabling particles to escape local optima, while too much noise prevents convergence.

**Related:**
- Adaptive learning strategy PSO (2020): classifies particles into ordinary and locally-best, with noise injected into ordinary particle updates to increase diversity.
- Entropy-based parameter adjustment in PE-PSO (2025, arXiv:2507.13647): dynamically adjusts exploration based on current population entropy.

**Relevance:**
Temperature in LLM sampling is the direct analog of noise injection. Non-zero temperature maintains reasoning diversity. Adaptive temperature (reducing toward convergence, increasing when diversity collapses) is an understudied mechanism for multi-agent LLM systems.

---

### K7. Swarm Stagnation Detection and Remedies

**Key Reference:**
- Rivera, M.M., et al. (2023). "Dynamical sphere regrouping particle swarm optimization: A proposed algorithm for dealing with PSO premature convergence." *Mathematics*, 11(20):4339. (10 citations)
- ADPSO: "An adaptive dynamic multi-swarm particle swarm optimization with stagnation detection and spatial exclusion." *Engineering Applications of Artificial Intelligence*, 2023.

**Core Idea:**
Stagnation detection monitors convergence indicators (diversity metrics, improvement rate, position variance) and triggers diversity restoration when thresholds are crossed. Remedies include:
1. Random restart (some particles re-initialized randomly)
2. Repulsion operator activation
3. Topology change (switch from fully-connected to ring topology)
4. Chaotic perturbation

**Relevance:**
The equivalent in LLM agent systems is "diversity monitoring and intervention." If all agents converge on the same answer after 2 rounds of debate, inject a devil's advocate prompt, re-seed with a novel hypothesis, or explicitly instruct agents to argue against the current consensus.

---

## PART II: ASPECT L — Novelty Search & Quality-Diversity Algorithms

---

### L1. Foundational Novelty Search

**L1.1 — Original Novelty Search Paper**

**Title:** Abandoning Objectives: Evolution Through the Search for Novelty Alone
**Authors:** Lehman, J., Stanley, K.O.
**Year:** 2011
**Source:** *Evolutionary Computation*, 19(2):189–223. Also: GECCO 2008 (original workshop version). DOI: 10.1162/evco_a_00025
**arXiv:** Not on arXiv (pre-arXiv era for this community); PDF at: https://www.cs.swarthmore.edu/~meeden/DevelopmentalRobotics/lehman_ecj11.pdf
**Citations:** 1,800+ (Google Scholar)

**Core Idea:**
Rewarding novelty alone (rather than proximity to objective) often reaches objectives faster than objective-based search in deceptive fitness landscapes. Instead of asking "how close is this solution to the goal?", novelty search asks "how different is this behavior from everything seen before?"

**Methodology:**
- Behavioral characterization (BC): a low-dimensional descriptor of what a solution *does*, not how well it performs
- Novelty metric: sparseness = average distance to k-nearest neighbors in behavior space
- Permanent archive: stores all previously-visited behaviors; prevents cycling; counterbalances exploration biases
- No fitness signal: population evolves purely to maximize behavioral novelty

**Key Results:**
- On maze navigation with deceptive fitness gradients, novelty search finds the exit in 100% of runs vs. ~40% for objective-based approaches
- Solutions found by novelty search have lower genomic complexity
- Novelty search naturally promotes evolvability (diverse populations have more evolvable offspring)

**Relevance:**
The core insight — that directly optimizing for the goal can be *less effective* than optimizing for diversity of explored behaviors — applies directly to LLM hypothesis generation. An LLM agent system that only generates hypothesis variants near the current "best" hypothesis may miss entire solution classes that require distant behavioral stepping stones.

---

**L1.2 — Novelty Search and the Problem with Objectives**

**Title:** Novelty Search and the Problem with Objectives
**Authors:** Lehman, J., Stanley, K.O.
**Year:** 2011
**Source:** *Genetic Programming Theory and Practice IX.* Springer. Chapter 3.
**URL:** https://link.springer.com/chapter/10.1007/978-1-4614-1770-5_3

**Core Idea:**
Extends the argument beyond mazes to a general theory of why objectives fail: ambitious objectives don't illuminate a gradient toward themselves; intermediate stepping stones often look nothing like the final goal. This is the "deceptive landscape" problem.

---

**L1.3 — Novelty Search Applied to Swarm Robotics**

**Title:** Evolution of Swarm Robotics Systems with Novelty Search
**Authors:** Gomes, J., Urbano, P., Christensen, A.L.
**Year:** 2013
**Source:** arXiv:1304.3362
**arXiv ID:** 1304.3362

**Core Idea:**
First application of novelty search to swarm controller evolution. Demonstrates that novelty search prevents premature convergence caused by deceptive fitness landscapes in swarm coordination tasks (aggregation, energy-sharing station).

**Key Results:**
- Novelty search + NEAT finds solutions that fitness-based evolution cannot
- Discovers broader diversity of solutions for the same task
- Hybrid novelty+fitness variants combine exploratory and exploitary advantages

**Relevance:**
Direct bridge from novelty search to multi-agent systems. The agents are a swarm; novelty is applied to the swarm's collective behavioral descriptor.

---

### L2. MAP-Elites: The Core Illumination Algorithm

**L2.1 — Original MAP-Elites**

**Title:** Illuminating search spaces by mapping elites
**Authors:** Mouret, J.-B., Clune, J.
**Year:** 2015
**Source:** arXiv:1504.04909
**URL:** https://arxiv.org/abs/1504.04909
**Citations:** 2,500+ (Google Scholar)

**Core Idea:**
MAP-Elites (Multi-dimensional Archive of Phenotypic Elites) divides a user-defined behavioral descriptor space into a grid of cells. Each cell stores only the highest-performing solution with those behavioral characteristics. The algorithm simultaneously optimizes *performance* within every behavioral niche, producing a map of high-performing diverse solutions.

**Methodology:**
- Define K behavioral dimensions (e.g., limb usage fraction in robot locomotion)
- Maintain archive grid: cells indexed by discretized behavioral coordinates
- Each cell contains the elite (highest-fitness) solution with those coordinates
- Generate new solutions by mutating/crossing archive members; if new solution outcompetes existing cell occupant, replace it
- Return: entire archive = diverse repertoire of high-quality solutions

**Key Results:**
- Produces a repertoire of ~1000–100,000 behavioral variants, all near-optimal within their niche
- Enables rapid adaptation: when environment changes, switch to a pre-computed solution from a different archive cell
- Illuminates the full search space rather than converging on one solution

**Relevance:**
MAP-Elites can be applied to agent behavior spaces: define behavioral dimensions as "reasoning style," "formality," "domain focus"; maintain a population of agents that are diverse across these dimensions while each being high-performing.

---

**L2.2 — Robots that can adapt like animals (MAP-Elites in practice)**

**Title:** Robots that can adapt like animals
**Authors:** Cully, A., Clune, J., Tarapore, D., Mouret, J.-B.
**Year:** 2015
**Source:** *Nature*, 521:503–507.
**URL:** https://www.nature.com/articles/nature14422
**Citations:** 1,800+

**Core Idea:**
Uses MAP-Elites to pre-compute a behavioral repertoire of 13,000 walking gaits. When the robot is damaged, it uses Bayesian optimization over the repertoire (Intelligent Trial & Error) to find a working gait within ~1 minute, testing fewer than 10 options.

**Key Results:**
- Behavioral repertoire enables damage recovery 6x faster than existing methods
- Robot tests <10 behaviors yet succeeds because repertoire is maximally diverse and high-quality

**Relevance:**
The "pre-compute diverse repertoire, then select at deployment time" pattern is directly applicable to multi-agent LLM systems: pre-compute a diverse set of agent configurations/prompts/reasoning styles, then select the most appropriate subset for each task.

---

**L2.3 — Scaling MAP-Elites to Deep Neuroevolution**

**Title:** Scaling MAP-Elites to Deep Neuroevolution
**Authors:** Colas, C., Huizinga, J., Madhavan, V., Clune, J.
**Year:** 2020
**Source:** arXiv:2003.01825
**arXiv ID:** 2003.01825

**Core Idea:**
Standard MAP-Elites cannot handle high-dimensional neural network parameter spaces. ME-ES combines MAP-Elites with Evolution Strategies (CMA-ES) to scale to deep neural networks. Shows MAP-Elites is competitive with state-of-the-art RL exploration methods on deceptive reward tasks.

---

**L2.4 — CMA-ME: Covariance Matrix Adaptation MAP-Elites**

**Title:** Covariance Matrix Adaptation for the Rapid Illumination of Behavior Space
**Authors:** Fontaine, M.C., Togelius, J., Nikolaidis, S., Hoover, A.K.
**Year:** 2020
**Source:** GECCO 2020. arXiv:1912.02400
**URL:** https://arxiv.org/abs/1912.02400

**Core Idea:**
Introduces "emitters" — separate CMA-ES optimizers that each focus on improving a specific part of the archive. Each emitter is initialized from a different archive cell and optimizes in a different direction, enabling efficient directed exploration.

---

**L2.5 — Multi-Emitter MAP-Elites**

**Title:** Multi-Emitter MAP-Elites: Improving quality, diversity and convergence speed with heterogeneous sets of emitters
**Authors:** Cully, A.
**Year:** 2021
**Source:** arXiv:2007.05352
**arXiv ID:** 2007.05352

**Core Idea:**
Uses a *heterogeneous* set of emitter types (some exploitation-focused, some exploration-focused), with a bandit algorithm dynamically allocating compute budget to the most productive emitter at each stage. ME-MAP-Elites significantly outperforms both CMA-ME and basic MAP-Elites.

**Relevance:**
The bandit-over-emitters pattern is directly applicable to multi-agent LLM systems: maintain a portfolio of agent "styles" (exploitative/analytical vs. exploratory/creative vs. critical/skeptical), dynamically allocate compute to whichever style is most productive for the current task state.

---

**L2.6 — PGA-MAP-Elites (Policy Gradient Assisted)**

**Title:** Empirical analysis of PGA-MAP-Elites for Neuroevolution in Uncertain Domains
**Authors:** Flageat, M., Chalumeau, F., Cully, A.
**Year:** 2022
**Source:** arXiv:2210.13156
**arXiv ID:** 2210.13156

**Core Idea:**
Adds a gradient-based variation operator (inspired by deep RL policy gradients) alongside standard genetic operators in MAP-Elites. The gradient operator guides mutations toward archive-improving solutions, dramatically improving sample efficiency.

---

**L2.7 — DCG-MAP-Elites (Descriptor-Conditioned Gradients)**

**Title:** MAP-Elites with Descriptor-Conditioned Gradients and Archive Distillation into a Single Policy
**Authors:** Faldor, M., Chalumeau, F., Flageat, M., Cully, A.
**Year:** 2023
**Source:** arXiv:2303.03832
**arXiv ID:** 2303.03832

**Core Idea:**
Enhances policy gradient variation with a descriptor-conditioned critic that optimizes across the entire behavioral descriptor space simultaneously. Also distills the entire diverse archive into a single versatile policy. Improves QD score over PGA-MAP-Elites by 82% on locomotion tasks.

---

### L3. Quality-Diversity Theory and Variants

**L3.1 — QD Overview and the Novelty Search with Local Competition (NSLC)**

**Key Reference:**
- Lehman, J., Stanley, K.O. (2011). "Abandoning Objectives" (see L1.1)
- Pugh, J.K., Soros, L.B., Stanley, K.O. (2016). "Quality Diversity: A New Frontier for Evolutionary Computation." *Frontiers in Robotics and AI.*

**Core Idea:**
Quality-Diversity (QD) unifies novelty search (pure diversity) and objective-based search (pure quality) into algorithms that simultaneously optimize both. NSLC combines novelty fitness with local competition: solutions compete only against behavioral neighbors, allowing multiple high-quality solution clusters to co-exist.

---

**L3.2 — Quality Diversity Through Surprise**

**Title:** Quality Diversity Through Surprise
**Authors:** Gravina, D., Liapis, A., Yannakakis, G.N.
**Year:** 2018
**Source:** arXiv:1807.02397
**arXiv ID:** 1807.02397

**Core Idea:**
Introduces "surprise" (violation of model-based expectations) as a complementary diversity measure to novelty. Surprise is orthogonal to novelty: a solution can be novel (unprecedented behavior) or surprising (behavior that violates the agent's predictions) or both. Synergistic combination of novelty + surprise leads to significantly higher QD performance.

**Key Results:**
- On 60 deceptive mazes: surprise+novelty+local competition outperforms all single-component variants
- Surprise alone is less effective than novelty alone; combination is most effective

---

**L3.3 — Differentiable Quality Diversity (DQD)**

**Title:** Differentiable Quality Diversity
**Authors:** Fontaine, M.C., Nikolaidis, S.
**Year:** 2021
**Source:** NeurIPS 2021. arXiv:2106.03894
**URL:** https://arxiv.org/abs/2106.03894

**Core Idea:**
Defines a new problem class (DQD) where both objective and behavioral descriptor functions are first-order differentiable, enabling gradient-based QD optimization. Proposes MAP-Elites via Gradient Arborescence (MEGA), which uses gradient information to efficiently explore the joint objective-behavior space.

---

**L3.4 — Dominated Novelty Search (DNS)**

**Title:** Dominated Novelty Search: Rethinking Local Competition in Quality-Diversity
**Authors:** Bahlous-Boldi, R., Faldor, M., Grillotti, L., et al. (Cully group)
**Year:** 2025
**Source:** arXiv:2502.00593
**arXiv ID:** 2502.00593

**Core Idea:**
Reformulates QD as a genetic algorithm where local competition occurs through dynamic fitness transformations rather than explicit archive grids. Eliminates need for predefined archive bounds or hard-to-tune parameters. Significantly outperforms existing QD approaches on standard benchmarks and in high-dimensional/unsupervised spaces.

---

**L3.5 — QD for Problem-Solving (Multi-Objective Comparison)**

**Title:** Can the Problem-Solving Benefits of Quality Diversity Be Obtained Without Explicit Diversity Maintenance?
**Authors:** Boldi, R., Spector, L.
**Year:** 2023
**Source:** arXiv:2305.07767
**arXiv ID:** 2305.07767

**Core Idea:**
Argues that QD's advantages come from implicit multi-objective structure, not explicit diversity. Proposes that QD should be compared to multi-objective optimization, not single-objective optimization. The correct question is: does explicit diversity maintenance add value beyond what multi-objective formulation provides?

---

### L4. QDax: Open-Source Hardware-Accelerated Implementation

**Title:** QDax: A Library for Quality-Diversity and Population-based Algorithms with Hardware Acceleration
**Authors:** Chalumeau, F., Lim, B., Boige, R., Allard, M., et al. (Cully group)
**Year:** 2023
**Source:** arXiv:2308.03665; JMLR 25, 2024.
**URL:** https://arxiv.org/abs/2308.03665
**GitHub:** https://github.com/adaptive-intelligent-robotics/QDax
**Citations:** Growing rapidly (JMLR publication)

**Core Idea:**
Open-source, JAX-based library implementing MAP-Elites, CMA-ME, PGA-MAP-Elites, DCG-MAP-Elites, QDPG, and other QD algorithms with hardware acceleration (GPU/TPU). Achieves 10x speedup over CPU implementations.

**Implementation:**
```python
# Example QDax usage
import qdax
from qdax.core.map_elites import MAPElites
from qdax.core.containers.mapelites_repertoire import compute_cvt_centroids

# Define behavioral descriptor space
centroids = compute_cvt_centroids(num_descriptors=2, num_init_cvt_samples=50000, num_centroids=1024)

# Initialize MAP-Elites
map_elites = MAPElites(scoring_function=scoring_fn, emitter=emitter, metrics_function=metrics_fn)
```

**Relevance:**
QDax is the go-to open-source implementation for running QD experiments at scale.

---

### L5. Quality-Diversity for AI/LLM Systems (2023–2026)

**L5.1 — Quality-Diversity through AI Feedback (QDAIF)**

**Title:** Quality-Diversity through AI Feedback
**Authors:** Bradley, H., Dai, A., Teufel, H., Zhang, J., Oostermeijer, K., Bellagente, M., Clune, J., Stanley, K., Schott, G., Lehman, J.
**Year:** 2023 (ICLR 2024)
**Source:** arXiv:2310.13032
**URL:** https://arxiv.org/abs/2310.13032 / https://qdaif.github.io/
**Citations:** Growing rapidly

**Core Idea:**
Applies MAP-Elites to text generation using LLMs as both *variation operators* (generating new text variants) and *evaluators* (rating quality and behavioral diversity via natural language prompts). LMs are prompted to assess qualitative aspects like "sentiment," "writing style," or "topic."

**Methodology:**
- Archive grid: axes defined by natural language behavioral dimensions (e.g., writing style x topic)
- Variation: LLM generates new text variants from archive occupants
- Evaluation: LLM rates quality (numeric score) and classifies behavioral descriptor (which cell)
- Tested on: opinion writing, short stories, poetry

**Key Results:**
- QDAIF covers more of the behavioral space with high-quality samples than non-QD baselines
- Human evaluation confirms AI feedback reasonably approximates human judgments on diversity and quality
- Works across multiple creative writing domains without domain-specific engineering

**Relevance:**
Direct application template for multi-agent LLM diversity: use one LLM to evaluate diversity of reasoning strategies generated by other LLMs, maintaining an archive of diverse-yet-high-quality agent configurations.

---

**L5.2 — Quality Diversity through Human Feedback (QDHF)**

**Title:** Quality Diversity through Human Feedback: Towards Open-Ended Diversity-Driven Optimization
**Authors:** Ding, L., Zhang, J., Clune, J., Spector, L., Lehman, J.
**Year:** 2024 (ICML 2024)
**Source:** arXiv:2310.12103
**URL:** https://arxiv.org/abs/2310.12103 / https://liding.info/qdhf/
**GitHub:** https://github.com/ld-ing/qdhf

**Core Idea:**
Addresses the challenge that QD requires manually crafted behavioral descriptors. QDHF learns behavioral descriptors from human similarity judgments (2AFC pairwise comparisons) using contrastive learning, eliminating need for domain expertise in descriptor design.

**Key Results:**
- Outperforms automatic diversity discovery methods
- Matches performance of manually crafted descriptors on robotics benchmarks
- Enhances diversity in diffusion model image generation (user study preferred QDHF outputs)

**Relevance:**
Enables QD for domains where behavioral space is not easily hand-designed — like agent reasoning styles or hypothesis quality, where "what makes two reasoning strategies different" is hard to formalize.

---

**L5.3 — LLMatic: NAS via LLMs and Quality Diversity**

**Title:** LLMatic: Neural Architecture Search via Large Language Models and Quality Diversity Optimization
**Authors:** Nasir, M.U., Earle, S., Cleghorn, C., James, S., Togelius, J.
**Year:** 2023
**Source:** arXiv:2306.01102
**URL:** https://arxiv.org/abs/2306.01102 / https://github.com/umair-nasir14/LLMatic

**Core Idea:**
LLMs generate code-defined neural network architectures; MAP-Elites maintains a diverse archive of these architectures by behavioral dimensions (parameter count, accuracy). The LLM serves as the variation operator; QD ensures diversity across both performance and behavioral axes.

**Key Results:**
- Competitive NAS performance evaluating only 2,000 candidates
- No prior knowledge of benchmark domain required
- LLM-based mutation operators more effective than random mutation for architecture generation

**Relevance:**
Shows LLM + QD is viable for generating diverse, high-quality candidate configurations — directly applicable to diverse agent design.

---

**L5.4 — In-context QD (LLMs as In-context AI Generators)**

**Title:** Large Language Models as In-context AI Generators for Quality-Diversity
**Authors:** Lim, B., Flageat, M., Cully, A.
**Year:** 2024 (Artificial Life Conference 2024)
**Source:** arXiv:2404.15794
**URL:** https://arxiv.org/abs/2404.15794
**Citations:** 12+

**Core Idea:**
Uses LLMs with few-shot prompting from the QD archive as context ("many-shot in-context generation") to generate new solutions. The LLM sees multiple high-quality, diverse examples from the archive and generates solutions that combine their properties. This exploits LLM in-context learning as a sophisticated recombination operator.

**Key Results:**
- Outperforms standard QD baselines across multiple domains (BBO functions, policy search)
- Works across multiple model sizes and archive population sizes
- Many-shot (large archive context) outperforms few-shot prompting

**Relevance:**
Shows that LLMs can serve as powerful recombination operators in QD, generating novel combinations of diverse solutions by "understanding" what properties make each solution valuable. Pattern directly applicable to multi-agent hypothesis recombination.

---

**L5.5 — Evolution through Large Models (ELM)**

**Title:** Evolution through Large Models
**Authors:** Lehman, J., Gordon, J., Jain, S., Ndousse, K., Yeh, C., et al. (OpenAI)
**Year:** 2023
**Source:** arXiv:2206.08896; *Evolutionary Machine Learning* (Springer, 2023), Chapter 11.
**URL:** https://arxiv.org/abs/2206.08896
**Citations:** 186+

**Core Idea:**
LLMs trained on code serve as powerful mutation operators in evolutionary algorithms, because LLM training data includes sequential code changes (diffs, PRs, commits) — the LLM has seen thousands of examples of "take this code and improve/modify it." ELM combined with MAP-Elites generates hundreds of thousands of functional programs and then bootstraps a conditional LLM from this diverse dataset.

**Key Results:**
- ELM+MAP-Elites generates a diverse behavioral repertoire of walking robot programs
- The LLM mutation operator discovers solutions impossible with random mutation
- Establishes LLM-as-mutation-operator as a new evolutionary computing paradigm

**Relevance:**
Foundational bridge paper between LLMs and evolutionary computation. The "LLM as mutation operator" pattern enables QD search over LLM-generated solutions without requiring hand-crafted operators.

---

**L5.6 — CycleQD: Agent Skill Acquisition via Quality-Diversity**

**Title:** Agent Skill Acquisition for Large Language Models via CycleQD
**Authors:** Kuroki, S., Nakamura, T., Akiba, T., Tang, Y. (Sakana AI)
**Year:** 2024 (ICLR 2025)
**Source:** arXiv:2410.14735
**URL:** https://arxiv.org/abs/2410.14735 / https://github.com/SakanaAI/CycleQD
**Citations:** 5+

**Core Idea:**
Applies QD to LLM model merging for multi-skill acquisition. In each cycle, one task's performance metric is the quality objective while others are behavioral descriptors. SVD-based mutation extrapolates model capabilities. Model merging serves as crossover between specialized expert models.

**Methodology:**
- Archive: grid over task performance dimensions (e.g., coding score x OS score x DB score)
- Quality objective: cycled through tasks one at a time
- Crossover: model merging (weighted parameter combination of archive members)
- Mutation: SVD-based perturbation of model weight matrices

**Key Results:**
- LLAMA3-8B-INSTRUCT with CycleQD surpasses traditional fine-tuning in coding/OS/DB tasks
- Achieves performance on par with GPT-3.5-Turbo
- Retains robust general language capabilities

**Relevance:**
Most direct application of QD to LLM capability diversification. Shows QD can prevent skill specialization collapse (where fine-tuning on one task degrades others) by explicitly maintaining diverse skill profiles in the archive.

---

**L5.7 — QDRT: Quality-Diversity Red-Teaming**

**Title:** Quality-Diversity Red-Teaming: Automated Generation of High-Quality and Diverse Attackers for Large Language Models
**Authors:** Wang, R.-J., Xue, K., Qin, Z., Li, Z., et al.
**Year:** 2025
**Source:** arXiv:2506.07121
**URL:** https://arxiv.org/abs/2506.07121

**Core Idea:**
Applies QD to LLM red-teaming: generates diverse adversarial prompts that are both effective (high attack success rate) and diverse (cover different attack styles and risk categories). Uses behavior-conditioned training and behavioral replay buffer. Trains multiple specialized attackers.

**Key Results:**
- Higher diversity and effectiveness than baseline red-teaming methods
- Works against GPT-2, Llama-3, Gemma-2, Qwen2.5

**Related:**
- **Rainbow Teaming** (NeurIPS 2024): Original QD-based red-teaming, casting adversarial prompt generation as MAP-Elites problem. Behavioral descriptors: risk category and attack style. Paper: https://proceedings.neurips.cc/paper_files/paper/2024/file/8147a43d030b43a01020774ae1d3e3bb-Paper-Conference.pdf
- **RainbowPlus** (arXiv:2504.15047, 2025): Extends Rainbow Teaming with multi-element archive and concurrent fitness evaluation. 100x more unique prompts; avg ASR 81.1%.

---

**L5.8 — DebateQD: QD-Evolved Debate Strategies for LLMs**

**Title:** Optimizing for Persuasion Improves LLM Generalization: Evidence from Quality-Diversity Evolution of Debate Strategies
**Authors:** Reedi, A.J., Leger, C., Pourcel, J., Gaven, L., Charriau, P., Pourcel, G.
**Year:** 2025
**Source:** arXiv:2510.05909
**URL:** https://arxiv.org/abs/2510.05909

**Core Idea:**
Uses QD (MAP-Elites-style) to evolve diverse debate strategies (rationality, authority, emotional appeal, etc.) through tournament competition among LLM agents. Maintains diversity of strategies via prompt-based behavioral dimensions within a single LLM architecture (no population of different models needed). Persuasion-optimized strategies generalize better than truth-optimized strategies.

**Key Results:**
- 13.94% smaller train-test generalization gap for persuasion-optimized strategies
- Works across 7B, 32B, 72B model scales
- First controlled evidence that competitive pressure improves reasoning generalization

**Relevance:**
Shows QD can diversify *reasoning strategies* (not just outputs) in LLM debate systems, and that diversity of argumentation styles improves generalization.

---

**L5.9 — DSDR: Diversity Regularization for LLM Reasoning**

**Title:** DSDR: Dual-Scale Diversity Regularization for Exploration in LLM Reasoning
**Authors:** (various)
**Year:** 2025
**Source:** arXiv:2602.19895
**URL:** https://arxiv.org/abs/2602.19895

**Core Idea:**
Applies diversity regularization at two scales during RLVR (reinforcement learning with verifiable rewards): globally, promotes diversity among correct reasoning trajectories (different solution modes); locally, prevents entropy collapse within each mode. Theoretically grounded: proves DSDR preserves optimal correctness under bounded regularization.

**Key Results:**
- Consistent improvements in accuracy and pass@k across reasoning benchmarks
- Prevents "reasoning mode collapse" (LLM converging to single solution path despite multiple valid approaches)

**Relevance:**
Directly addresses diversity maintenance in LLM training, not just inference. The dual-scale framing (global mode diversity + local within-mode entropy) maps cleanly onto the swarm diversity literature (species-level vs. within-species diversity).

---

**L5.10 — Diverse Prompts: MAP-Elites for Prompt Space Illumination**

**Title:** Diverse Prompts: Illuminating the Prompt Space of Large Language Models with MAP-Elites
**Authors:** Santos, G.M., Julia, R.M.D.S., Nascimento, M.Z.
**Year:** 2025
**Source:** arXiv:2504.14367
**URL:** https://arxiv.org/abs/2504.14367
**Citations:** 1

**Core Idea:**
Applies MAP-Elites to systematically explore the prompt design space. Uses context-free grammar (CFG) to define a structured prompt space; MAP-Elites dimensions = number of examples (shots) x reasoning depth. Evaluates on 7 BigBench Lite tasks across multiple LLMs.

**Key Results:**
- Reveals how structural prompt variations (shot count, reasoning depth) interact to affect LLM performance
- Shows quality-diversity tradeoffs in prompt design
- Actionable insights for task-specific prompt optimization

**Relevance:**
Shows MAP-Elites can explore the LLM *prompt* space (not just output space), directly applicable to designing diverse agent system prompts.

---

**L5.11 — EvoLattice: QD-Style LLM Program/Agent Evolution**

**Title:** EvoLattice: Persistent Internal-Population Evolution through Multi-Alternative Quality-Diversity Graph Representations for LLM-Guided Program Discovery
**Authors:** Yuksel, K.A.
**Year:** 2025
**Source:** arXiv:2512.13857
**URL:** https://arxiv.org/abs/2512.13857

**Core Idea:**
Represents an entire *population* of candidate programs or agent behaviors within a single directed acyclic graph (DAG). Multiple alternatives stored at each node; valid paths through the graph define distinct candidates. Avoids overwrite-based mutations that discard useful variants. QD dynamics emerge implicitly from the multi-alternative representation.

**Key Results:**
- More stable evolution and stronger improvement than prior LLM-guided methods
- Naturally prevents "destructive mutation" (overwriting good solutions with bad)

---

### L6. Multi-Agent LLM Diversity: Preventing Homogeneous Reasoning

**L6.1 — Multiagent Debate for Improved Reasoning (Foundational)**

**Title:** Improving Factuality and Reasoning in Language Models through Multiagent Debate
**Authors:** Du, Y., Li, S., Torralba, A., Tenenbaum, J.B., Mordatch, I.
**Year:** 2023 (ICML 2024)
**Source:** arXiv:2305.14325
**URL:** https://arxiv.org/abs/2305.14325
**Citations:** 400+

**Core Idea:**
Multiple LLM instances propose answers and critique each other's reasoning over multiple rounds. Inspired by the "Society of Minds" concept. Significantly improves mathematical reasoning and reduces factual hallucinations.

**Key Results:**
- Outperforms single-model self-reflection on GSM8K, MMLU, Chess, Biography
- Debate converges to better answers than any single agent achieves alone
- Works even with homogeneous agents (same model); heterogeneous agents perform better

**Relevance:**
Establishes multi-agent debate as a viable diversity mechanism. The paper explicitly notes that diversity of initial responses (even from the same model) improves debate quality.

---

**L6.2 — Diversity of Thought Elicits Stronger Reasoning**

**Title:** Diversity of Thought Elicits Stronger Reasoning Capabilities in Multi-Agent Debate Frameworks
**Authors:** (various)
**Year:** 2024
**Source:** arXiv:2410.12853; IJCSMA 2024.
**URL:** https://arxiv.org/abs/2410.12853

**Core Idea:**
Directly tests whether *model diversity* (different LLMs with different training) in multi-agent debate outperforms *model homogeneity* (many instances of the same LLM). Shows that diversity of thought (heterogeneous models) outperforms ability (homogeneous strong models).

**Key Results:**
- Heterogeneous ensemble (Gemini-Pro + Mixtral-8x7B + PaLM-2-M) achieves 91% on GSM8K after 4 debate rounds
- Homogeneous ensemble (3x Gemini-Pro) achieves only 82% on GSM8K
- Diverse ensemble *outperforms GPT-4*
- Validates Scott Page's "diversity trumps ability" theorem in LLM context

**Relevance:**
This is the most direct empirical evidence that reasoning diversity in multi-agent LLM systems produces better outcomes than raw capability. Key citation for any system that maintains diverse agent populations.

---

**L6.3 — Unleashing Diverse Thinking Modes (DiMo)**

**Title:** Unleashing Diverse Thinking Modes in LLMs through Multi-Agent Collaboration
**Authors:** He, Z., Feng, Y.
**Year:** 2025
**Source:** arXiv:2510.16645
**URL:** https://arxiv.org/abs/2510.16645

**Core Idea:**
Introduces DiMo: 4 specialized LLM agents each embodying a distinct reasoning paradigm (analytical, creative, critical, synthetic). Agents debate iteratively, challenging and refining initial responses. Produces explicit, auditable reasoning chains.

**Key Results:**
- Improves accuracy over single-model and debate baselines on 6 benchmarks
- Largest gains on mathematical reasoning

---

**L6.4 — Consensus-Diversity Tradeoff in Adaptive Multi-Agent Systems**

**Title:** Unraveling the Consensus-Diversity Tradeoff in Adaptive Multi-Agent LLM Systems
**Year:** 2025
**Source:** EMNLP 2025.
**URL:** https://aclanthology.org/2025.emnlp-main.772.pdf

**Core Idea:**
Formally studies the tradeoff between forcing consensus vs. preserving diversity in multi-agent LLM systems. Finds that implicit consensus (agents retain independent judgment) outperforms explicit consensus (agents must adopt collective action) on misinformation containment and public good provision tasks.

**Relevance:**
Theoretical framework for understanding when to push agents toward agreement vs. when to preserve disagreement. Key insight: forcing consensus too early degrades system performance.

---

**L6.5 — DSDR for LLM Reasoning Diversity** (see L5.9 above)

---

### L7. Additional Related Works

**L7.1 — Benchmarking QD for RL**

**Title:** Benchmarking Quality-Diversity Algorithms on Neuroevolution for Reinforcement Learning
**Authors:** Flageat, M., Lim, B., Grillotti, L., et al.
**Year:** 2022
**Source:** arXiv:2211.02193
**URL:** https://arxiv.org/abs/2211.02193 / https://github.com/adaptive-intelligent-robotics/QDax

**Core Idea:**
Defines standard QD metrics: coverage (fraction of archive filled), QD-score (sum of all elite fitnesses), maximum fitness, archive profile. Introduces corrected metrics for stochastic environments.

---

**L7.2 — BR-NS: Archive-less Novelty Search**

**Title:** BR-NS: an Archive-less Approach to Novelty Search
**Authors:** Salehi, A., Coninx, A., Doncieux, S.
**Year:** 2021
**Source:** arXiv:2104.03936
**arXiv ID:** 2104.03936

**Core Idea:**
Standard novelty search requires a Euclidean behavior space and k-NN archive lookup. BR-NS uses a learned behavior recognition model instead, enabling novelty search in non-Euclidean or high-dimensional behavior spaces.

**Relevance:**
Enables novelty search over semantic/embedding-based behavior spaces — directly applicable to LLM reasoning diversity where "behavior" is a high-dimensional embedding.

---

**L7.3 — BEACON: Bayesian Novelty Search**

**Title:** BEACON: A Bayesian Optimization Strategy for Novelty Search in Expensive Black-Box Systems
**Authors:** Tang, W.-T., Chakrabarty, A., Paulson, J.A.
**Year:** 2024
**Source:** arXiv:2406.03616
**arXiv ID:** 2406.03616

**Core Idea:**
Replaces evolutionary novelty search with Bayesian optimization (Gaussian process models) for sample-efficient novelty discovery in expensive black-box systems. 10 synthetic + 8 real-world benchmarks.

**Key Results:**
- Consistently outperforms evolutionary NS baselines under tight evaluation budgets
- Scalable to large input spaces via high-dimensional GP modeling

**Relevance:**
When LLM agent evaluations are expensive, Bayesian novelty search is more sample-efficient than evolutionary approaches.

---

**L7.4 — WANDER: LLM-Driven Novelty Search for Diverse Image Generation**

**Title:** Evolve to Inspire: Novelty Search for Diverse Image Generation
**Authors:** Inch, A., et al.
**Year:** 2025
**Source:** arXiv:2511.00686
**URL:** https://arxiv.org/abs/2511.00686

**Core Idea:**
WANDER applies novelty search directly to natural language prompt evolution for text-to-image diffusion models. LLM (GPT-4o-mini) serves as mutation operator; CLIP embeddings measure behavioral novelty; emitters guide search into distinct regions of prompt space.

**Key Results:**
- Significantly outperforms evolutionary prompt optimization baselines in diversity metrics
- 7x more token-efficient than competing method Lluminate
- Demonstrates LLM novelty search is viable for creative AI tasks

---

**L7.5 — QD for Hyperparameter Optimization (QD applied to ML)**

**Title:** A Collection of Quality Diversity Optimization Problems Derived from Hyperparameter Optimization of Machine Learning Models
**Authors:** Schneider, L., Pfisterer, F., Thomas, J., Bischl, B.
**Year:** 2022
**Source:** arXiv:2204.14061
**arXiv ID:** 2204.14061

**Core Idea:**
Applies QD to hyperparameter optimization of ML models, using novel behavioral dimensions like interpretability and resource usage. Reveals tradeoffs between accuracy, interpretability, and efficiency that single-objective HPO misses.

---

**L7.6 — Surveying Quality-Diversity in Synthetic LLM Data**

**Title:** Surveying the Effects of Quality, Diversity, and Complexity in Synthetic Data From Large Language Models
**Authors:** Havrilla, A., Dai, A., O'Mahony, L., et al.
**Year:** 2024
**Source:** arXiv:2412.02980
**URL:** https://arxiv.org/abs/2412.02980

**Core Idea:**
Reviews how quality, diversity, and complexity of LLM-generated synthetic training data affect downstream model performance. Finds that diversity is *essential* for out-of-distribution generalization; quality is essential for in-distribution generalization. Current LLM training over-optimizes for output quality at the expense of output diversity, limiting self-improvement.

**Key Results:**
- Quality-Diversity tradeoffs in training data have significant downstream effects
- Models evaluated/optimized only for quality have limited output diversity
- Balancing QDC is essential for future self-improvement algorithms

**Relevance:**
Provides strong empirical motivation for diversity-aware LLM training and agent systems. The "quality vs. diversity" tradeoff in LLM outputs is a direct analog of the convergence-diversity tradeoff in swarm intelligence.

---

## PART III: LITERATURE SYNTHESIS

---

### 3.1 Field Overview

**Aspect K (Swarm Diversity):**
Two decades of swarm intelligence research establish a clear empirical and theoretical foundation: diversity in swarm populations is not merely a nice-to-have but a functional necessity for robust collective problem-solving. The field identifies three fundamental mechanisms that maintain diversity:
1. Structural embedding (polyandry, caste systems — diversity at initialization)
2. Repulsion/niching (charged PSO, fitness sharing — active prevention of overcrowding)
3. Negative feedback (pheromone evaporation, memory decay — discouraging exploitation of known solutions)

Swarm stagnation (premature convergence) is the most-studied failure mode: it occurs when social learning pressure (agents copying the current best) overwhelms exploration pressure. Stagnation is self-reinforcing: once diversity collapses, recovery requires external intervention.

**Aspect L (Novelty Search and QD):**
The QD field originated with Lehman & Stanley's novelty search (2008/2011) and matured into the MAP-Elites framework (2015). The core insight — that maintaining diverse *behavioral repertoires* is more useful than optimizing a single objective — has been validated across evolutionary robotics, game design, neural architecture search, and increasingly, LLM systems.

The 2023–2025 period has seen an explosion of QD applications to LLMs: QDAIF uses LLMs as QD variation operators for creative text; CycleQD applies QD to LLM model merging; Rainbow Teaming applies QD to red-teaming; DebateQD applies QD to debate strategy evolution. This represents a rapid and significant paradigm shift.

---

### 3.2 Key Methodological Patterns

| Pattern | Biological Analog | Computational Implementation | LLM Agent Application |
|---------|-------------------|------------------------------|----------------------|
| Structural diversity embedding | Polyandry / multiple queens | Population initialization with diverse seeds | Initialize agents with diverse system prompts / fine-tuned variants |
| Negative feedback / evaporation | Pheromone evaporation | Memory decay, archive pruning | Discount overused reasoning patterns; rotate agent contexts |
| Repulsion / niching | Territorial behavior | Charged PSO, fitness sharing, crowding | Penalize agents for repeating prior agents' arguments |
| Novelty reward | No direct analog | Behavioral sparseness metric (k-NN) | Reward agents for proposing solutions distant from archive |
| Archive / repertoire | Memory, learned paths | MAP-Elites grid | Maintain diverse hypothesis archive; select by niche, not pure quality |
| Emitters / bandit | Caste specialization | Multi-emitter MAP-Elites with UCB | Bandit allocation across agent reasoning styles |
| Local competition | Within-niche selection | NSLC, MAP-Elites cell replacement | Agents compete only with agents of similar behavioral type |

---

### 3.3 Established Baselines for QD Performance

| Algorithm | Key Property | QD-Score | Coverage | Source |
|-----------|-------------|----------|----------|--------|
| MAP-Elites | Simple grid; random mutation | Baseline | Moderate | arXiv:1504.04909 |
| CMA-ME | Directed exploration via CMA emitters | +40-80% over ME | High | arXiv:1912.02400 |
| ME-MAP-Elites | Heterogeneous emitter portfolio | +100%+ over CMA-ME | Very high | arXiv:2007.05352 |
| PGA-MAP-Elites | Policy gradient variation operator | Top tier | High | arXiv:2210.13156 |
| DCG-MAP-Elites | Descriptor-conditioned gradients | +82% over PGA | Highest | arXiv:2303.03832 |
| QDAIF | LLM variation + LLM evaluation | N/A (text domain) | N/A | arXiv:2310.13032 |

---

### 3.4 Gaps in the Literature

1. **Gap: Diversity metrics for LLM reasoning.** PSO has formalized diversity metrics (position diversity, fitness diversity, entropy). LLM agent systems lack equivalent standardized metrics. Current proxies (semantic distance, disagreement rate) are ad hoc. *Opportunity:* Design a diversity metric suite specifically for LLM agent populations, analogous to QD-score and coverage in robot QD.

2. **Gap: Dynamic diversity management for LLM agents.** PSO literature has stagnation detection and diversity restoration mechanisms. LLM multi-agent literature focuses on static configurations. *Opportunity:* Implement adaptive diversity control: monitor agent agreement rate, trigger diversity injection when consensus forms too rapidly.

3. **Gap: Behavioral descriptors for agent hypothesis space.** MAP-Elites requires user-defined behavioral dimensions. For scientific hypothesis generation, these dimensions are unclear. *Opportunity:* Use QDHF (learned from human feedback) or automated descriptor learning to define meaningful behavioral axes for hypothesis diversity.

4. **Gap: Negative feedback in LLM agent memory.** No paper systematically studies pheromone-evaporation analogs in LLM multi-agent systems (discounting or decaying prior agent conclusions to prevent lock-in). *Opportunity:* Implement and evaluate "pheromone evaporation" as a mechanism to prevent reasoning stagnation over long multi-agent conversations.

5. **Gap: QD at inference time.** Most QD work focuses on training-time optimization. QDAIF and DebateQD apply QD at inference time, but this is underexplored. *Opportunity:* Run MAP-Elites-style search over agent configurations during a single inference session, maintaining a live archive of diverse high-quality reasoning approaches.

---

### 3.5 Theoretical Foundation: Why Diversity Matters

**Scott Page's Diversity Theorem (2007):**
*"The Difference: How the Power of Diversity Creates Better Groups, Firms, Schools, and Societies"* (Princeton University Press)
Proves mathematically that cognitively diverse groups solve problems better than homogeneous groups of high individual ability. The conditions: problems are complex, diversity of "tools" (cognitive strategies) is genuine, not nominal. Key theorem: diversity in problem-solving heuristics can compensate for lower average ability.

*Empirical LLM validation:* "Diversity of Thought Elicits Stronger Reasoning Capabilities in Multi-Agent Debate Frameworks" (arXiv:2410.12853, 2024) — diverse ensemble of medium-capacity models outperforms GPT-4.

---

## PART IV: CITATION RECOMMENDATIONS

---

### Must Cite (Foundational)

1. **Lehman & Stanley (2011).** "Abandoning Objectives." *Evolutionary Computation* 19(2). — Foundational novelty search; defines behavioral characterization and sparseness metric.

2. **Mouret & Clune (2015).** "Illuminating search spaces by mapping elites." arXiv:1504.04909. — Foundational MAP-Elites; defines illumination algorithm paradigm.

3. **Cully et al. (2015).** "Robots that can adapt like animals." *Nature* 521. — Landmark demonstration of behavioral repertoire for adaptive systems.

4. **Dorigo & Stutzle (2004).** *Ant Colony Optimization.* MIT Press. — ACO fundamentals including pheromone evaporation as diversity mechanism.

5. **Du et al. (2023).** "Improving Factuality and Reasoning in Language Models through Multiagent Debate." arXiv:2305.14325. — Foundational multi-agent LLM debate paper.

### Should Cite (Directly Relevant)

6. **Bradley et al. (2023).** "Quality-Diversity through AI Feedback." arXiv:2310.13032. — QD applied to LLM text generation; closest analog to our work.

7. **Kuroki et al. (2024).** "Agent Skill Acquisition for Large Language Models via CycleQD." arXiv:2410.14735. — QD applied to LLM model diversity; directly relevant.

8. **Anonymous (2024).** "Diversity of Thought Elicits Stronger Reasoning Capabilities in Multi-Agent Debate Frameworks." arXiv:2410.12853. — Empirical validation that diversity outperforms ability in LLM agents.

9. **Lim et al. (2024).** "Large Language Models as In-context AI Generators for Quality-Diversity." arXiv:2404.15794. — LLMs as QD variation operators; in-context generation from archive.

10. **Cully (2021).** "Multi-Emitter MAP-Elites." arXiv:2007.05352. — Heterogeneous emitter portfolio; bandit allocation pattern.

11. **Blackwell (2005).** "Particle swarms and population diversity." *Soft Computing* 9(11). — Diversity metrics for swarms; charged PSO as diversity mechanism.

12. **Havrilla et al. (2024).** "Surveying Quality, Diversity, and Complexity in Synthetic LLM Data." arXiv:2412.02980. — Quality-diversity tradeoffs in LLM training data.

### Consider Citing (Context)

13. **Ding et al. (2024).** "Quality Diversity through Human Feedback." arXiv:2310.12103 (ICML 2024). — When arguing that QD behavioral descriptors can be learned, not hand-crafted.

14. **Gomes et al. (2013).** "Evolution of Swarm Robotics Systems with Novelty Search." arXiv:1304.3362. — Novelty search applied to swarm controller evolution.

15. **Lehman et al. (2023).** "Evolution through Large Models." arXiv:2206.08896. — LLM as evolutionary mutation operator; foundational ELM paper.

16. **Chalumeau et al. (2023).** "QDax: A Library for QD and Population-based Algorithms with Hardware Acceleration." arXiv:2308.03665. — Open-source QD implementation.

17. **Santos et al. (2025).** "Diverse Prompts: Illuminating the Prompt Space of LLMs with MAP-Elites." arXiv:2504.14367. — MAP-Elites for LLM prompt diversity.

18. **Reedi et al. (2025).** "Optimizing for Persuasion Improves LLM Generalization: Evidence from QD Evolution of Debate Strategies." arXiv:2510.05909. — QD for reasoning strategy diversity.

19. **Scott Page (2007).** *The Difference.* Princeton University Press. — Theoretical foundation for "diversity trumps ability."

---

## PART V: RELATED WORK DRAFT

---

### Swarm Diversity Maintenance

Biological swarm intelligence systems have evolved sophisticated mechanisms to prevent premature convergence. Most prominently, queen polyandry in honeybees and army ants (Ratnieks & Helantera 2009; Mattila & Seeley 2007) embeds genetic diversity structurally at the colony level, producing worker cohorts with diverse behavioral thresholds that collectively perform better than genetically uniform colonies. This "structural diversity embedding" principle argues that diversity cannot be reliably achieved through behavioral adaptation alone — it must be present at initialization.

In computational swarm intelligence, the failure mode of premature convergence is thoroughly studied. Standard Particle Swarm Optimization (PSO) suffers rapid diversity collapse as all particles rush toward the current global best (Blackwell 2005; Cheng 2013). Remedies include charged particle swarms (inter-particle repulsion), niching (sub-population isolation), and fitness sharing (penalizing crowded solution regions). In Ant Colony Optimization, pheromone evaporation serves as a canonical negative feedback mechanism (Dorigo & Stutzle 2004): without it, the first discovered path receives permanent reinforcement regardless of quality.

Recent work on stagnation detection (Rivera et al. 2023) treats diversity collapse as a detectable system state requiring active intervention — a perspective directly applicable to multi-agent LLM systems where agent consensus emerging too rapidly may indicate premature convergence rather than correct solution discovery.

### Novelty Search and Quality-Diversity Algorithms

Novelty search (Lehman & Stanley 2011) demonstrated that objective-guided search is often inferior to diversity-guided search in deceptive fitness landscapes. By rewarding behavioral novelty (measured as k-nearest-neighbor sparseness in behavior space) rather than objective proximity, novelty search consistently finds solutions that objective-based evolution cannot. The core insight — that intermediate stepping stones toward complex solutions often look *unlike* the goal — applies directly to creative hypothesis generation in scientific discovery.

MAP-Elites (Mouret & Clune 2015) extended this insight into a practical algorithm that illuminates entire behavioral search spaces, producing repertoires of diverse high-performing solutions simultaneously. The landmark demonstration (Cully et al. 2015) showed that a robot with pre-computed behavioral repertoires of 13,000 gait variants could recover from damage within one minute by searching only ~10 candidates. Subsequent algorithmic improvements — CMA-ME (Fontaine et al. 2020), Multi-Emitter MAP-Elites (Cully 2021), PGA-MAP-Elites (Flageat et al. 2022), DCG-MAP-Elites (Faldor et al. 2023) — have consistently improved QD performance through better-directed exploration.

The open-source QDax library (Chalumeau et al. 2023) has democratized QD research with hardware-accelerated (JAX) implementations running 10x faster than CPU baselines, enabling large-scale experimentation.

### Quality-Diversity Applied to LLM Systems

The intersection of QD and LLM systems has emerged as a rapidly growing research area. Lehman et al.'s Evolution through Large Models (ELM, 2023) established LLMs as powerful mutation operators in evolutionary computation: LLMs trained on code have internalized structural patterns of valid code modification, dramatically outperforming random mutation. Quality-Diversity through AI Feedback (QDAIF, Bradley et al. 2023) applied MAP-Elites to creative text generation, using LLMs as both variation operators and behavioral evaluators, demonstrating coverage of diverse creative writing styles while maintaining quality.

CycleQD (Kuroki et al. 2024) applied QD to LLM model merging for multi-skill acquisition, showing that QD prevents skill specialization collapse (where fine-tuning on one task degrades others) and enables LLMs to achieve diverse capabilities simultaneously. In-context QD (Lim et al. 2024) exploited LLMs' few-shot learning abilities as sophisticated QD recombination operators, feeding diverse archive examples as context to generate novel combinations. DebateQD (Reedi et al. 2025) evolved diverse debate strategies (rationality, authority, emotional appeal) through QD, showing persuasion-optimized diversity improves reasoning generalization. Diverse Prompts (Santos et al. 2025) directly applied MAP-Elites to illuminate the prompt engineering search space across BigBench tasks.

### Diversity in Multi-Agent LLM Reasoning

Multi-agent debate systems (Du et al. 2023) demonstrated that having multiple LLM instances propose and critique answers improves factuality and reasoning, inspired by the "Society of Minds" concept. Critically, recent empirical work has confirmed that *model diversity* (using different LLMs) outperforms *model homogeneity* (using many instances of the same LLM): a diverse ensemble of medium-capacity models outperforms GPT-4 on GSM8K mathematical reasoning (arXiv:2410.12853, 2024). This validates Scott Page's (2007) theoretical diversity theorem in the LLM context.

The Consensus-Diversity Tradeoff (EMNLP 2025) provides a formal framework for understanding when to push agents toward agreement vs. preserve disagreement, finding that implicit consensus (agents retain independent judgment) consistently outperforms explicit consensus forcing. DSDR (arXiv:2602.19895, 2025) applies dual-scale diversity regularization during LLM training, preventing reasoning mode collapse at both the global (different solution strategies) and local (within-strategy entropy) levels.

### Positioning

Our work builds on this body of literature by applying principles from swarm diversity maintenance (negative feedback, niching, stagnation detection) and quality-diversity algorithms (MAP-Elites, behavioral repertoires, novelty metrics) to the design of multi-agent LLM systems for scientific discovery. We extend existing work by: (1) systematically applying biological swarm diversity principles to LLM agent architecture; (2) proposing diversity metrics specific to reasoning-space exploration; and (3) implementing QD-inspired mechanisms for maintaining diverse hypothesis populations over long multi-agent discovery sessions.

---

## PART VI: INSIGHTS FOR EXPERIMENT DESIGN

---

### Suggested Baselines

| Baseline | Description | Source |
|----------|-------------|--------|
| Homogeneous LLM ensemble | N instances of same model, same temperature | Du et al. (2023) |
| Self-consistency | Sample K responses, majority vote | Wang et al. (2023) |
| Vanilla multi-agent debate | Homogeneous agents, unconstrained convergence | Du et al. (2023) |
| MAP-Elites archive | Explicit behavioral grid, standard MAP-Elites | Mouret & Clune (2015) |
| QDAIF | LLM variation + LLM evaluation | Bradley et al. (2023) |

### Methodological Suggestions

1. **Define behavioral descriptors early.** MAP-Elites requires explicit behavioral dimensions. For hypothesis generation, candidate dimensions include: domain focus (narrow vs. broad), mechanism type (causal vs. correlational), falsifiability level, reasoning style (deductive vs. inductive). Consider QDHF (Ding et al. 2024) to learn descriptors from human feedback if manual definition is difficult.

2. **Implement stagnation detection.** Monitor agent agreement rate (fraction of agents proposing identical or near-identical hypotheses) and reasoning path entropy. Trigger diversity restoration (novel hypothesis seeding, devil's advocate injection, temperature increase) when these metrics cross thresholds.

3. **Use negative feedback on overused solutions.** Track which hypotheses have been extensively explored. Apply "evaporation" — reduce selection probability of heavily-explored hypotheses — to force exploration of novel areas.

4. **Consider emitter heterogeneity.** Rather than running a single agent type, maintain a portfolio of specialized agents (exploitative/refinement vs. exploratory/creative vs. critical/skeptical) and use a bandit algorithm to dynamically allocate compute based on recent archive improvement.

5. **Measure QD-score, not just quality.** Single best hypothesis quality is an incomplete metric. Measure: coverage (fraction of behavioral space explored), QD-score (sum of quality across all diverse solutions found), diversity metric (mean pairwise distance in reasoning embedding space).

### Potential Pitfalls

1. **Behavioral descriptor collapse.** If behavioral dimensions are too coarse or poorly chosen, the archive fills with solutions that are numerically diverse but semantically identical. Invest in careful descriptor design or use learned descriptors.

2. **Quality-diversity tradeoff.** Optimizing purely for novelty degrades quality (agents propose creative but poor hypotheses). Balance novelty reward with quality threshold — only add to archive if quality exceeds minimum bar (as in NSLC).

3. **Convergence disguised as diversity.** Agents may produce diverse-sounding outputs (different wordings, different examples) while converging on the same underlying reasoning. Surface-form diversity metrics (lexical diversity) can be misleading; semantic embedding distances are more reliable.

4. **Expensive evaluation bottleneck.** Running QD with LLM agents is expensive. Consider BEACON (Bayesian novelty search, arXiv:2406.03616) or surrogate-assisted MAP-Elites (Zhang et al. 2021, arXiv:2112.03534) to reduce evaluation cost.

5. **Archive bound explosion.** Unconstrained archive growth becomes computationally intractable. Use bounded archives (fixed cell count in MAP-Elites) or archived-less methods like BR-NS (arXiv:2104.03936) or Dominated Novelty Search (arXiv:2502.00593).

---

## References Index

| ID | Citation | ArXiv/Source |
|----|----------|--------------|
| K-ACO | Dorigo & Stutzle, *Ant Colony Optimization*, MIT Press 2004 | ISBN 0-262-04219-3 |
| K-PSO-DIV | Blackwell, "Particle swarms and population diversity," *Soft Computing* 2005 | Springer |
| K-POP-DIV | Cheng, S., "Population Diversity in PSO," University of Liverpool 2013 | ResearchGate |
| K-BRAIN | Cheng et al., "Population diversity maintenance in brain storm optimization," *JAISCR* 2014 | JAISCR |
| K-BIO1 | Mattila & Seeley, "Genetic Diversity in Honey Bee Colonies," *Science* 2007 | 317(5836):362 |
| K-BIO2 | Ratnieks & Helantera, "Extreme polyandry in social Hymenoptera," *Phil Trans B* 2009 | Springer |
| K-NICHING | Li, X. "Niching Without Niching Parameters," *IEEE Trans Evol Comp* 2010 | IEEE |
| K-STAG | Rivera et al., "Dynamical sphere regrouping PSO," *Mathematics* 2023 | MDPI |
| K-ENT | Li et al., "Diversity Model Based on Dimension Entropy," *Entropy* 2021 | PMC8065515 |
| L-NS1 | Lehman & Stanley, "Abandoning Objectives," *Evol Comput* 2011 | ECJ |
| L-NS2 | Lehman & Stanley, "Novelty Search and the Problem with Objectives," GPTP 2011 | Springer |
| L-ME1 | Mouret & Clune, "Illuminating search spaces by mapping elites," 2015 | arXiv:1504.04909 |
| L-ME2 | Cully et al., "Robots that can adapt like animals," *Nature* 2015 | 521:503-507 |
| L-ME-SCALE | Colas et al., "Scaling MAP-Elites to Deep Neuroevolution," 2020 | arXiv:2003.01825 |
| L-CMAME | Fontaine et al., "CMA for Rapid Illumination of Behavior Space," GECCO 2020 | arXiv:1912.02400 |
| L-MEMME | Cully, "Multi-Emitter MAP-Elites," 2021 | arXiv:2007.05352 |
| L-PGAME | Flageat et al., "PGA-MAP-Elites," 2022 | arXiv:2210.13156 |
| L-DCGME | Faldor et al., "DCG-MAP-Elites," GECCO 2023 | arXiv:2303.03832 |
| L-DNS | Bahlous-Boldi et al., "Dominated Novelty Search," 2025 | arXiv:2502.00593 |
| L-QDAX | Chalumeau et al., "QDax Library," JMLR 2024 | arXiv:2308.03665 |
| L-QDAIF | Bradley et al., "QDAIF," ICLR 2024 | arXiv:2310.13032 |
| L-QDHF | Ding et al., "QDHF," ICML 2024 | arXiv:2310.12103 |
| L-ELM | Lehman et al., "Evolution through Large Models," 2023 | arXiv:2206.08896 |
| L-LLMATIC | Nasir et al., "LLMatic," 2023 | arXiv:2306.01102 |
| L-ICQD | Lim et al., "LLMs as In-context AI Generators for QD," 2024 | arXiv:2404.15794 |
| L-CYCLEQD | Kuroki et al., "CycleQD," ICLR 2025 | arXiv:2410.14735 |
| L-QDRT | Wang et al., "QDRT," 2025 | arXiv:2506.07121 |
| L-RAINBOW | Samvelyan et al., "Rainbow Teaming," NeurIPS 2024 | NeurIPS 2024 |
| L-RBPLUS | Dang et al., "RainbowPlus," 2025 | arXiv:2504.15047 |
| L-DEBQD | Reedi et al., "DebateQD," 2025 | arXiv:2510.05909 |
| L-DSDR | (various), "DSDR," 2025 | arXiv:2602.19895 |
| L-DIVPROMPT | Santos et al., "Diverse Prompts," 2025 | arXiv:2504.14367 |
| L-EVOLATTICE | Yuksel, "EvoLattice," 2025 | arXiv:2512.13857 |
| L-WANDER | Inch et al., "WANDER," 2025 | arXiv:2511.00686 |
| L-DEBATE | Du et al., "Improving Factuality via Multiagent Debate," ICML 2024 | arXiv:2305.14325 |
| L-DIVTHOUGHT | (various), "Diversity of Thought," 2024 | arXiv:2410.12853 |
| L-DIMO | He & Feng, "DiMo," 2025 | arXiv:2510.16645 |
| L-CONSDIV | (various), "Consensus-Diversity Tradeoff," EMNLP 2025 | ACL Anthology |
| L-QDSYNTH | Havrilla et al., "Surveying QDC in Synthetic LLM Data," 2024 | arXiv:2412.02980 |
| L-BRNS | Salehi et al., "BR-NS," 2021 | arXiv:2104.03936 |
| L-BEACON | Tang et al., "BEACON," 2024 | arXiv:2406.03616 |
| L-PAGE | Scott Page, *The Difference*, Princeton UP 2007 | ISBN 978-0-691-13854-1 |
| L-SWARMEVO | Gomes et al., "Novelty Search for Swarm Robotics," 2013 | arXiv:1304.3362 |
| L-BENCH | Flageat et al., "Benchmarking QD for RL," 2022 | arXiv:2211.02193 |
| L-QDC | Schneider et al., "QD for HPO," 2022 | arXiv:2204.14061 |
