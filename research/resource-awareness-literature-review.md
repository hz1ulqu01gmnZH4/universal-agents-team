# Resource Awareness in LLM-Based Multi-Agent Systems: A Literature Review

## Token Budget Management, Computational Resource Awareness, Cost-Aware Decision Making, and Rate Limit Handling

**Date:** 2026-02-28
**Scope:** ~65 papers, systems, and frameworks surveyed
**Relevance:** Universal Agents Framework -- resource-constrained self-evolving multi-agent system on Claude Code / Claude Max

---

## 1. Introduction

Large language model (LLM)-based multi-agent systems (MAS) have demonstrated remarkable
capabilities in collaborative problem-solving, from software development (ChatDev, MetaGPT)
to scientific discovery (Agent Laboratory, Kosmos) and general reasoning (CAMEL, AutoGen).
However, a critical and often overlooked dimension of these systems is *resource awareness*:
the ability of agents to perceive, plan around, and optimize their consumption of computational
resources, API tokens, wall-clock time, and monetary costs.

This gap matters especially for autonomous, long-running frameworks. A system like the
Universal Agents Framework, designed for continuous self-evolution on a Claude Max subscription,
must operate within hard constraints: per-minute rate limits, rolling hourly token windows,
weekly allocation caps, and finite CPU/memory on the host machine. Without resource awareness,
agents waste tokens on redundant reasoning, spawn processes that exceed available memory, or
hit rate limits that stall the entire pipeline.

This review synthesizes literature across four tightly coupled topics:

1. **Token Budget Management** -- tracking, estimating, and optimizing token consumption
2. **Computational Resource Awareness** -- monitoring CPU, GPU, memory, and disk; adaptive scaling
3. **Cost-Aware Agent Decision Making** -- monetary cost modeling, human approval workflows, spending limits
4. **Rate Limit Handling** -- detection, backoff, fair allocation, priority scheduling

We cover key papers (with arXiv IDs where available), quantitative findings, design patterns,
and gaps in current research, concluding with design implications for our framework.

---

## 2. Token Budget Management for LLM Agents

### 2.1 The Token Cost Problem

Token consumption is the primary operational cost in LLM-based MAS. The "Tokenomics" study
(Salim et al., 2026; arXiv:2601.14470) provides the first empirical analysis of where tokens
are consumed in agentic software engineering. Analyzing 30 software development tasks in the
ChatDev framework, they found:

- The iterative **Code Review stage accounts for 59.4% of all tokens** consumed
- **Input tokens constitute 53.9%** of total consumption (more than output + reasoning combined)
- The primary cost lies not in initial generation but in **automated refinement and verification**

These findings suggest that naive multi-agent collaboration is inherently token-wasteful, with
most tokens spent re-ingesting context rather than producing novel output.

### 2.2 Token-Budget-Aware Reasoning

The TALE framework (Han et al., 2024; arXiv:2412.18547) introduced token-budget-aware
reasoning for individual LLM calls. TALE operates in two modes:

- **TALE-EP (Estimation and Prompting):** A budget estimator predicts task complexity, then
  crafts a prompt that includes the estimated token budget, guiding the LLM to reason concisely.
- **TALE-PT (Post Training):** Fine-tunes models to inherently respect budget constraints.

Key result: TALE-EP achieves **80.22% average accuracy** with only **138.53 average output
tokens**, representing a **67% reduction in output token costs** and **59% reduction in expenses**
while maintaining competitive performance versus vanilla Chain-of-Thought.

### 2.3 Budget-Aware Agent Scaling

BATS (Budget-Aware Test-time Scaling; Liu et al., 2025; arXiv:2511.17006) is the first
systematic study of budget-constrained agents. Key contributions:

- **Budget Tracker:** A lightweight plug-in that provides agents with continuous budget
  awareness, enabling them to dynamically adapt planning and verification strategies.
- **Unified cost metric:** Jointly accounts for token consumption and tool-call costs.
- Agents with budget awareness "dig deeper" on promising leads or "pivot" to new paths
  based on remaining resources.
- Finding: Simply granting agents a larger tool-call budget **fails to improve performance**
  without budget awareness -- agents lack intrinsic ability to manage resources.

### 2.4 Budget-Constrained Tool Learning

Zheng et al. (2024; arXiv:2402.15960) formalized budget-constrained tool learning. Their method:

1. Estimates tool usefulness based on past experience
2. Uses **dynamic programming** to formulate a plan specifying which tools to use and how many
   times, before execution begins
3. Integrates with various tool-learning methods as a planning layer

The INTENT framework (Liu et al., 2026; arXiv:2602.11541) extends this to sequential
decision-making with stochastic tool executions and strict monetary budgets, using an
intention-aware hierarchical world model to anticipate future tool usage and risk-calibrated costs.

### 2.5 Token-Efficient Multi-Agent Communication

Multiple recent works tackle token efficiency at the communication level:

**AgentDropout** (Wang et al., 2025; arXiv:2503.18891) dynamically eliminates redundant agents
and communication links by optimizing adjacency matrices of communication graphs:
- **21.6% reduction** in prompt tokens, **18.4% reduction** in completion tokens
- Simultaneous **performance improvement of 1.14** on benchmark tasks

**Optima** (Chen et al., 2024; arXiv:2410.08115) uses RL to train MAS for communication
efficiency, achieving **2.8x performance gain with less than 10% of tokens** on heavy
information-exchange tasks, using a reward function that balances task performance, token
efficiency, and readability.

**CodeAgents** (Yang et al., 2025; arXiv:2507.03254) codifies multi-agent reasoning into
modular pseudocode, reducing input tokens by **55-87%** and output tokens by **41-70%** while
improving planning accuracy by 3-36 percentage points.

**Agent-GSPO** (Fan et al., 2025; arXiv:2510.22477) uses Group Sequence Policy Optimization
with communication-aware rewards that penalize verbosity, fostering "strategic silence" where
agents learn when *not* to communicate.

**TopoDIM** (Sun et al., 2026; arXiv:2601.10120) generates one-shot communication topologies
with diverse interaction modes, reducing token consumption by **46.41%** while improving
performance by **1.50%**.

**SupervisorAgent** (Lin et al., 2025; arXiv:2510.26585) provides runtime adaptive supervision
without altering base architectures, reducing token consumption by **29.45%** on GAIA benchmark
without compromising success rate.

### 2.6 Context Compression for Long-Running Agents

For long-running agents, context growth is a major cost driver:

**AgentOCR** (Feng et al., 2026; arXiv:2601.04786) represents accumulated observation-action
history as rendered images, achieving **>50% token reduction** while preserving 95% of
text-based agent performance, with agents trained to emit adaptive compression rates.

**Dynamic System Instructions (ITR)** (Franko, 2025; arXiv:2602.17046) retrieves per-step
only the minimal system-prompt fragments and tool subset needed, reducing per-step context
tokens by **95%**, improving tool routing by **32%**, and cutting episode cost by **70%**.

**Co-Saving** (Qiu et al., 2025; arXiv:2505.21898) introduces "shortcuts" -- instructional
transitions learned from historically successful trajectories -- that bypass redundant
reasoning agents. Compared to ChatDev, Co-Saving achieves **50.85% reduction in token usage**
and **10.06% improvement** in code quality.

### 2.7 Summary of Token Efficiency Results

| Method | Token Reduction | Performance Impact | Mechanism |
|--------|----------------|-------------------|-----------|
| TALE-EP | 67% output tokens | -0.5% accuracy | Budget-aware prompting |
| AgentDropout | 21.6% prompt, 18.4% completion | +1.14 score | Graph optimization |
| Optima | 90%+ tokens | +2.8x perf | RL-trained communication |
| CodeAgents | 55-87% input, 41-70% output | +3-36pp accuracy | Codified reasoning |
| Co-Saving | 50.85% total | +10.06% quality | Experience shortcuts |
| TopoDIM | 46.41% total | +1.50% perf | One-shot topology |
| SupervisorAgent | 29.45% total | No degradation | Runtime supervision |
| ITR | 95% per-step context | +32% tool routing | Dynamic prompt retrieval |
| AgentOCR | >50% total | -5% perf | Visual history compression |

---

## 3. Computational Resource Awareness

### 3.1 Resource-Aware Agent Architectures

**HASHIRU** (Pai et al., 2025; arXiv:2506.04255) is the most directly relevant framework for
resource-aware multi-agent systems. It features:

- A "CEO" agent that dynamically manages "employee" agents based on task needs and **resource
  constraints** (cost, memory)
- **Hybrid intelligence** that prioritizes smaller, local LLMs (via Ollama) while flexibly
  using external APIs when necessary
- An **economic model** with hiring/firing costs that promotes team stability
- **Autonomous budget management** including cost model generation
- Results: 96% on GSM8K (vs. 61% for Gemini 2.0 Flash), 80% on JEEBench (vs. 68.3%)

**SEMAS** (Saleh et al., 2026; arXiv:2602.16738) distributes specialized agents across
Edge/Fog/Cloud tiers for IoT predictive maintenance:

- Edge agents: lightweight feature extraction and pre-filtering
- Fog agents: ensemble detection with dynamic consensus voting
- Cloud agents: PPO-based policy optimization with non-blocking inference
- Demonstrates **resource-aware specialization** without sacrificing real-time performance

### 3.2 LLM Inference on Heterogeneous Hardware

**Agent.xpu** (2025; arXiv:2506.24045) addresses efficient scheduling of agentic LLM
workloads on heterogeneous SoC devices, using CPU, integrated GPU, and NPU with two-tier
asynchronous scheduling via Boost.Asio for request processing and coroutine mechanisms for
kernel parallelism.

**NEO** (2025) offloads decoding attention and KV cache of selected inference requests to CPU,
adaptively deciding offloading policy for dynamic workloads -- achieving efficient resource
utilization when GPU memory is constrained.

**LeMix** (Li et al., 2025; arXiv:2507.21276) co-locates concurrent LLM serving and training
workloads with dynamic resource allocation based on workload characteristics, achieving
**3.53x throughput improvement** and **2.12x higher SLO attainment**.

### 3.3 Adaptive Scaling and Resource Allocation

The **Self-Organized Agents (SoA)** framework (Ishibashi & Nishimura, 2024; arXiv:2404.02183)
demonstrates automatic agent multiplication based on problem complexity, allowing dynamic
scalability while keeping per-agent context load constant -- a key pattern for resource-aware
spawning.

**AgentInfer** (Lin et al., 2025; arXiv:2512.18337) co-designs inference optimization and
architectural design with four components:

- **AgentCollab:** Hierarchical dual-model reasoning balancing large and small model usage
- **AgentSched:** Cache-aware hybrid scheduler minimizing latency
- **AgentSAM:** Suffix-automaton speculative decoding reusing multi-session memory
- **AgentCompress:** Semantic compression of agent memory
- Results: **50%+ reduction in ineffective tokens**, **1.8-2.5x overall speedup**

### 3.4 Memory and KV-Cache Management

**VL-Cache** (Tu et al., 2024; arXiv:2410.23317) demonstrates modality-aware KV cache
compression, retaining only 10% of KV cache while maintaining accuracy, with **2.33x
end-to-end latency acceleration** and **7.08x decoding speedup** -- directly applicable to
reducing memory pressure in multi-agent inference.

**ShardMemo** (Zhao et al., 2026; arXiv:2601.21545) provides a budgeted tiered memory service
for agentic LLMs with scope-before-routing, cost-aware gating over shard families, and fixed
probe budgets that reduce retrieval work by **20.5%** and p95 latency by **20%**.

### 3.5 Emerging Pattern: Energetic and Survival-Oriented Agents

**Energentic Intelligence** (Karagoz, 2025; arXiv:2506.04916) introduces a class of autonomous
systems defined by their capacity to sustain themselves through internal energy regulation.
While focused on physical energy, the formalization of energy-based utility functions and
viability-constrained survival horizons is directly transferable to computational resource
management in software agents.

---

## 4. Cost-Aware Agent Decision Making

### 4.1 LLM Cascades and Model Routing

**FrugalGPT** (Chen et al., 2023; arXiv:2305.05176) introduced three strategies for cost
reduction:

1. **Prompt adaptation:** Reducing input token count
2. **LLM approximation:** Using cheaper models with cached completions
3. **LLM cascade:** Sequentially querying models from cheapest to most expensive, stopping
   when confidence is sufficient

Key result: FrugalGPT matches GPT-4 performance with **up to 98% cost reduction** or improves
accuracy by 4% at the same cost.

**TensorOpera Router** (Stripelis et al., 2024; arXiv:2408.12320) dynamically routes queries
to the most appropriate expert model, achieving **40% improvement in efficiency** and **30%
cost reduction** while maintaining or improving performance by 10%.

**RouterBench** (Hu et al., 2024; arXiv:2403.12031) provides a standardized benchmark for
evaluating LLM routing systems with 405K+ inference outcomes, establishing the theoretical
framework for routing optimization.

**PILOT** (Panda et al., 2025; arXiv:2508.21141) frames LLM routing as a contextual bandit
problem with an online cost policy modeled as a multi-choice knapsack problem for
resource-efficient routing under diverse user budgets.

**BELLA** (Okamoto et al., 2026; arXiv:2602.02386) decomposes model capabilities into
interpretable skill profiles and uses multi-objective optimization to select models that
maximize performance while respecting budget constraints.

**MESS+** (Woisetschlager et al., 2025; arXiv:2505.19947) achieves **2x cost savings** over
existing routing techniques through stochastic optimization with rigorous SLA compliance
guarantees, learning request satisfaction probabilities in real-time.

### 4.2 Cost-Controlled Multi-Agent Coordination

**CoRL** (Jin et al., 2025; arXiv:2511.02755) is the most complete framework for
budget-controlled multi-agent LLM coordination. Key design:

- A **centralized controller LLM** selectively coordinates a pool of expert models
- Formulated as **RL with dual objectives**: maximize task performance, minimize inference cost
- A **controllable multi-budget setting**: a single trained system adapts behavior at inference
  time to different budget levels (high, medium, low)
- Under high budgets, CoRL **surpasses the best single expert LLM**
- Under low budgets, it maintains strong performance via selective expert invocation

This pattern of budget-parameterized policies is directly relevant to our framework, where
the daily/weekly token budget varies based on subscription utilization patterns.

### 4.3 Budget-Aware ML Agent Systems

**BudgetMLAgent** (Gandhi et al., 2024; arXiv:2411.07464) demonstrates cost-effective
multi-agent ML automation:

- Uses a **Planner** (cheap model) + **Workers** (task executors) architecture
- Employs **LLM cascades**: try cheap model first, escalate to GPT-4 only when needed
- **Ask-the-expert** calls: occasional GPT-4 consultations for planning only
- **Efficient retrieval** of past observations to avoid redundant computation
- Result: **94.2% cost reduction** ($0.931 to $0.054 per run) with **better success rate**
  (32.95% vs. 22.72% for GPT-4 single agent)

### 4.4 Cost Benchmarks and Evaluation

**CostBench** (Liu et al., 2025; arXiv:2511.02734) is the first cost-centric benchmark for
evaluating agents' economic reasoning. Key findings:

- Agents frequently **fail to identify cost-optimal solutions** even in static settings
- GPT-5 achieves **less than 75% exact match** on hardest cost-optimization tasks
- Performance drops by **~40% under dynamic conditions** (tool failures, cost changes)
- Demonstrates fundamental gaps in agents' ability to reason about costs

**AutoMaAS** (Ma et al., 2025; arXiv:2510.02669) introduces self-evolving multi-agent
architecture search with **performance-cost analysis** for automatic operator lifecycle
management, achieving 1.0-7.1% performance improvement while reducing inference costs by 3-5%.

### 4.5 Economic Models for Agent Task Outsourcing

**COALESCE** (Bhatt et al., 2025; arXiv:2506.01900) introduces a framework for agents to
dynamically outsource subtasks to specialized third-party agents:

- **Unified cost model** comparing internal execution costs against external prices
- **Market-based decision-making** via epsilon-greedy exploration
- Theoretical simulations show **41.8% cost reduction** potential
- Empirical validation confirms **20.3% cost reduction** across 240 real LLM tasks

### 4.6 Human-in-the-Loop Cost Governance

While no single paper formalizes human approval workflows for cost-incurring agent actions,
several patterns emerge from practice:

- **Tiered approval thresholds:** Low-cost actions proceed automatically; medium-cost actions
  require async approval; high-cost actions require synchronous human confirmation
- **Per-run spend caps:** Hard limits on total API cost per agent run
- **Token budget allocation:** Pre-allocating token budgets to agent subtasks before execution
- **Cost-of-pass metric** (Wang et al., 2025; arXiv:2508.02694): Measures the total cost
  required to achieve one successful task completion, enabling principled cost-performance
  trade-off analysis

The **Efficient Agents** framework (Wang et al., 2025; arXiv:2508.02694) formalizes this
through empirical analysis of when additional agent modules yield diminishing returns,
achieving **96.7% of leading performance** while reducing cost-of-pass by **28.4%**
($0.398 to $0.228).

---

## 5. Rate Limit Handling in Multi-Agent Systems

### 5.1 Rate Limiting Mechanisms

Modern LLM APIs employ the **token bucket algorithm** for rate limiting, where capacity is
continuously replenished up to a maximum limit rather than being reset at fixed intervals.
The Claude API measures rate limits along three dimensions:

- **RPM** (Requests Per Minute)
- **ITPM** (Input Tokens Per Minute) -- only uncached tokens count for most Claude models
- **OTPM** (Output Tokens Per Minute)

A critical insight: **prompt caching** effectively increases ITPM limits because cached tokens
do not count toward the ITPM quota, making caching not just a latency optimization but a
rate-limit mitigation strategy.

### 5.2 Client-Side Rate Limit Management

**ATB/AATB** (Farkiani et al., 2025; arXiv:2510.04516) presents adaptive client-side
algorithms for HTTP API rate limit handling:

- **ATB** (offline): Infers system congestion from response patterns and schedules retries
  using service workers
- **AATB** (online): Enhances retry behavior using aggregated telemetry data
- Reduces HTTP 429 errors by **up to 97.3%** compared to exponential backoff
- Requires no central coordination, relying only on minimal server feedback

This directly applies to multi-agent systems hitting Claude API rate limits, where each agent
acts as an independent client.

### 5.3 Fair Scheduling for LLM Serving

**Virtual Token Counter (VTC)** (Sheng et al., 2023; arXiv:2401.00588) defines LLM serving
fairness based on a cost function accounting for input and output tokens:

- Achieves a **tight 2x upper bound** on service difference between backlogged clients
- Work-conserving: never wastes capacity when there are waiting requests
- Directly applicable to fair token allocation across concurrent agents sharing a single
  API endpoint

### 5.4 Reliability Under Rate Limits

**ReliabilityBench** (Gupta, 2026; arXiv:2601.06112) evaluates LLM agent reliability under
production stress conditions including rate limiting:

- Tests consistency (pass^k), robustness (semantic perturbations), and **fault tolerance**
  (rate limits, timeouts, partial responses, schema drift)
- Finding: **Rate limiting is the most damaging fault** in ablations
- Perturbations reduce success from 96.9% at epsilon=0 to 88.1% at epsilon=0.2
- ReAct architecture is more robust than Reflexion under combined stress

### 5.5 Token Pooling and Priority Allocation

No single paper fully addresses token pooling across concurrent agents, but several patterns
emerge:

**Priority-based allocation:** CoRL (arXiv:2511.02755) implicitly implements this by having
the controller decide which expert to invoke based on expected value vs. cost -- critical
tasks get access to expensive models, routine tasks use cheap ones.

**Sliding window management:** By mid-2025, Anthropic redesigned Claude's usage into rolling
hourly windows and weekly caps across all interfaces. Multi-agent systems must therefore track
cumulative usage across all agent threads within these windows.

**Prompt caching as rate-limit arbitrage:** Since cached tokens do not count toward ITPM
limits for Claude models, agents sharing a common system prompt effectively multiply their
available input bandwidth. This creates a natural incentive for agent architectures that
maximize cache hit rates through shared prefixes.

### 5.6 Backpressure and Adaptive Scheduling Patterns

Practical multi-agent rate limit management combines several strategies:

1. **Token bucket tracking:** Mirror the server-side token bucket algorithm locally to predict
   when requests will succeed before sending them
2. **Priority queues:** Assign priority scores to agent tasks; higher-priority tasks get
   preferential access to the token budget
3. **Backpressure propagation:** When rate limits are hit, propagate backpressure upstream
   to pause task spawning rather than accumulating a retry queue
4. **Graceful degradation:** Switch to smaller/cheaper models when primary model rate limits
   are exhausted (model fallback cascading)
5. **Batch consolidation:** Aggregate multiple small agent requests into fewer, larger requests
   to reduce RPM pressure at the cost of slightly higher latency

---

## 6. Cross-Topic Synthesis

### 6.1 The Resource Awareness Stack

Across the four topics, a layered architecture for resource awareness emerges:

```
Layer 4: Cost-Aware Decision Making
  - Task selection based on budget remaining
  - Model routing (cheap vs. expensive)
  - Human approval for expensive operations

Layer 3: Token Budget Management
  - Per-task budget estimation
  - Token-budget-aware prompting
  - Context compression and caching

Layer 2: Rate Limit Handling
  - Token bucket tracking
  - Priority queuing
  - Backpressure and retry logic

Layer 1: Computational Resource Awareness
  - CPU/memory/disk monitoring
  - Agent spawn decisions
  - Hardware-tier placement (edge/fog/cloud)
```

Each layer informs the layers above it: computational constraints determine rate limit
capacity, rate limits constrain token budgets, and token budgets inform cost-aware decisions.

### 6.2 Converging Design Patterns

Several design patterns appear across multiple papers:

**Pattern 1: Budget-Parameterized Policies.** Rather than fixed behavior, train agents that
accept a budget parameter and adapt their strategy accordingly (CoRL, BATS, TALE). This
enables a single system to operate across different resource regimes.

**Pattern 2: Estimate-Then-Plan.** Before executing, estimate the resource cost of a task plan,
then optimize the plan to fit within constraints (Budget-Constrained Tool Learning, INTENT,
FrugalGPT cascades). This prevents budget overruns rather than detecting them post-hoc.

**Pattern 3: Topology Optimization.** The communication graph between agents is itself a
resource-consuming artifact. Optimizing it (AgentDropout, TopoDIM, HyperAgent, ARG-Designer)
simultaneously improves performance and reduces token consumption.

**Pattern 4: Experience-Based Shortcuts.** Learning from past successful trajectories to skip
redundant reasoning (Co-Saving, ShardMemo skill library, AgentInfer's SAM). This amortizes
the cost of exploration over time.

**Pattern 5: Tiered Model Usage.** Use cheap models by default, expensive models on demand
(BudgetMLAgent, HASHIRU, FrugalGPT, CoRL). The decision of when to escalate is the core
resource-awareness challenge.

### 6.3 Quantitative Landscape

Aggregating results across the literature, the achievable efficiency gains are substantial:

| Dimension | Best Reported Reduction | Source |
|-----------|----------------------|--------|
| API cost | 94-98% | BudgetMLAgent, FrugalGPT |
| Token consumption (MAS) | 50-95% | Co-Saving, ITR, CodeAgents |
| Rate limit errors | 97.3% | ATB/AATB |
| Inference latency | 1.8-2.5x speedup | AgentInfer |
| Memory footprint | 90% KV cache | VL-Cache |
| Per-step context | 95% reduction | ITR |

These numbers demonstrate that resource-unaware agents leave an enormous efficiency gap --
often an order of magnitude or more.

---

## 7. Design Implications for the Universal Agents Framework

Based on this review, we identify the following design requirements for resource awareness
in our framework:

### 7.1 Token Budget Subsystem

**Requirement:** Every agent must be budget-aware from the ground up.

- Implement a **Token Budget Tracker** (inspired by BATS) that gives each agent real-time
  visibility into its remaining token allocation
- Use **TALE-style budget estimation** to predict cost before executing reasoning chains
- Apply **dynamic programming-based planning** (from Budget-Constrained Tool Learning) to
  pre-allocate budgets across subtasks
- Implement **context compression** (Co-Saving shortcuts, AgentOCR visual compression) for
  long-running agents to prevent context growth from consuming the entire budget

### 7.2 Rate Limit Awareness

**Requirement:** The framework must treat rate limits as first-class constraints.

- Implement a **local token bucket mirror** that tracks Claude API consumption across all
  agent threads (RPM, ITPM, OTPM)
- Maximize **prompt caching** to exploit the fact that cached tokens do not count toward ITPM
  limits -- this is the single most impactful optimization for Claude Max
- Implement **backpressure propagation**: when approaching rate limits, pause agent spawning
  and queue tasks rather than hitting 429 errors
- Use **priority queuing** so critical tasks (e.g., safety checks) get preferential access

### 7.3 Cost-Aware Model/Agent Routing

**Requirement:** Not every task needs the most expensive model or the most agents.

- Implement **LLM cascading** (FrugalGPT pattern): attempt tasks with cheaper/smaller models
  first, escalate only when confidence is insufficient
- Use **CoRL-style budget-parameterized policies** so the system adapts its strategy based on
  remaining daily/weekly budget
- Apply **topology optimization** (AgentDropout, TopoDIM) to eliminate redundant agents and
  communication links in each collaboration round

### 7.4 Computational Resource Monitoring

**Requirement:** Agents must not spawn if the host machine lacks resources.

- Monitor **CPU, memory, and disk** before spawning new agent processes
- Implement **HASHIRU-style resource constraints** in the agent spawning policy
- Apply **tiered placement** (SEMAS pattern): lightweight tasks on local resources, heavy
  tasks deferred or distributed

### 7.5 Human Approval Workflows

**Requirement:** High-cost actions require human oversight.

- Define **spending tiers** with escalating approval requirements:
  - Tier 1 (< threshold_low): Automatic execution
  - Tier 2 (threshold_low -- threshold_high): Async notification + auto-proceed after timeout
  - Tier 3 (> threshold_high): Synchronous human approval required
- Log all costs for audit trail (per our existing audit trail requirement)
- Implement **per-run and per-day cost caps** as hard limits

### 7.6 Self-Improving Resource Efficiency

**Requirement:** The framework should improve its resource efficiency over time.

- Store successful trajectories and learn **Co-Saving shortcuts** to bypass redundant steps
- Use **Optima-style RL training** on communication efficiency if fine-tuning is available
- Track **cost-of-pass** (Efficient Agents metric) as a key performance indicator
- Apply **CostBench-style evaluation** to measure agents' economic reasoning capability

---

## 8. Gaps in Current Research

### 8.1 Subscription-Based Budget Models

Nearly all papers assume per-token API pricing. No work addresses the constraints of
**subscription-based access** (like Claude Max) where the resource is rate-limited rather
than pay-per-token. The optimization objective shifts from minimizing dollar cost to
maximizing value extracted within fixed rate/time windows.

### 8.2 Cross-Agent Budget Coordination

While individual agent budget awareness is studied, **coordinating budgets across a team of
concurrent agents** with shared rate limits remains unstudied. How should a team of 5 agents
sharing a single Claude Max subscription partition the hourly token window?

### 8.3 Long-Horizon Budget Planning

Existing work focuses on per-task or per-session budgets. **Multi-day or multi-week budget
planning** -- where today's usage affects tomorrow's capacity -- is unexplored. This is
critical for continuously running frameworks.

### 8.4 Resource-Aware Self-Evolution

No paper addresses how a **self-evolving** system should allocate resources between productive
work and self-improvement activities. How much of the token budget should be spent on
meta-learning vs. task execution?

### 8.5 Integrated Resource Monitoring

While separate works address token budgets, computational resources, and rate limits, no
framework provides **unified monitoring and optimization** across all resource dimensions
simultaneously. The interactions between these constraints (e.g., reducing token usage may
increase local compute for compression; caching reduces rate limit pressure but increases
memory usage) are unexplored.

### 8.6 Dynamic Cost Models for Tool Use

CostBench reveals that agents struggle with cost reasoning even in simple settings. Building
agents that can **learn and update cost models** for tools and APIs they have never used before
remains an open challenge.

### 8.7 Formal Guarantees on Budget Compliance

Most budget-aware methods are best-effort. **Formal guarantees** that an agent will never
exceed its budget -- analogous to real-time scheduling guarantees -- are lacking. The INTENT
framework (arXiv:2602.11541) begins to address this with hard budget feasibility constraints,
but more work is needed.

---

## 9. References

### Token Budget Management

1. Salim, M., Latendresse, J., Khatoonabadi, S.H., Shihab, E. (2026). "Tokenomics:
   Quantifying Where Tokens Are Used in Agentic Software Engineering." arXiv:2601.14470.

2. Han, T. et al. (2024). "Token-Budget-Aware LLM Reasoning." arXiv:2412.18547.
   ACL 2025 Findings.

3. Liu, T. et al. (2025). "Budget-Aware Tool-Use Enables Effective Agent Scaling."
   arXiv:2511.17006.

4. Zheng, Y. et al. (2024). "Budget-Constrained Tool Learning with Planning."
   arXiv:2402.15960.

5. Liu, H. et al. (2026). "Budget-Constrained Agentic Large Language Models:
   Intention-Based Planning for Costly Tool Use." arXiv:2602.11541.

6. Wang, Z. et al. (2025). "AgentDropout: Dynamic Agent Elimination for Token-Efficient
   and High-Performance LLM-Based Multi-Agent Collaboration." arXiv:2503.18891.

7. Chen, W. et al. (2024). "Optima: Optimizing Effectiveness and Efficiency for LLM-Based
   Multi-Agent System." arXiv:2410.08115.

8. Yang, B. et al. (2025). "CodeAgents: A Token-Efficient Framework for Codified
   Multi-Agent Reasoning in LLMs." arXiv:2507.03254.

9. Fan, Y. et al. (2025). "Agent-GSPO: Communication-Efficient Multi-Agent Systems via
   Group Sequence Policy Optimization." arXiv:2510.22477.

10. Sun, R. et al. (2026). "TopoDIM: One-shot Topology Generation of Diverse Interaction
    Modes for Multi-Agent Systems." arXiv:2601.10120.

11. Lin, F. et al. (2025). "Stop Wasting Your Tokens: Towards Efficient Runtime
    Multi-Agent Systems." arXiv:2510.26585.

12. Feng, L. et al. (2026). "AgentOCR: Reimagining Agent History via Optical
    Self-Compression." arXiv:2601.04786.

13. Franko, U. (2025). "Dynamic System Instructions and Tool Exposure for Efficient
    Agentic LLMs." arXiv:2602.17046.

14. Qiu, R. et al. (2025). "Co-Saving: Resource Aware Multi-Agent Collaboration for
    Software Development." arXiv:2505.21898.

15. Fan, W. et al. (2025). "iMAD: Intelligent Multi-Agent Debate for Efficient and
    Accurate LLM Inference." arXiv:2511.11306.

16. Li, S. et al. (2025). "Assemble Your Crew: Automatic Multi-agent Communication
    Topology Design via Autoregressive Graph Generation." arXiv:2507.18224.

### Computational Resource Awareness

17. Pai, K. et al. (2025). "HASHIRU: Hierarchical Agent System for Hybrid Intelligent
    Resource Utilization." arXiv:2506.04255.

18. Saleh, R. et al. (2026). "Self-Evolving Multi-Agent Network for Industrial IoT
    Predictive Maintenance (SEMAS)." arXiv:2602.16738.

19. Ishibashi, Y. & Nishimura, Y. (2024). "Self-Organized Agents: A LLM Multi-Agent
    Framework toward Ultra Large-Scale Code Generation." arXiv:2404.02183.

20. Lin, W. et al. (2025). "Towards Efficient Agents: A Co-Design of Inference
    Architecture and System (AgentInfer)." arXiv:2512.18337.

21. Tu, D. et al. (2024). "VL-Cache: Sparsity and Modality-Aware KV Cache Compression."
    arXiv:2410.23317.

22. Zhao, Y. et al. (2026). "ShardMemo: Masked MoE Routing for Sharded Agentic LLM
    Memory." arXiv:2601.21545.

23. Li, Y. et al. (2025). "LeMix: Unified Scheduling for LLM Training and Inference on
    Multi-GPU Systems." arXiv:2507.21276.

24. Karagoz, A. (2025). "Energentic Intelligence: From Self-Sustaining Systems to Enduring
    Artificial Life." arXiv:2506.04916.

25. Wen, B. (2025). "A Framework for Inherently Safer AGI through Language-Mediated Active
    Inference." arXiv:2508.05766.

26. Pan, J. & Li, G. (2025). "A Survey of LLM Inference Systems." arXiv:2506.21901.

### Cost-Aware Decision Making

27. Chen, L., Zaharia, M., Zou, J. (2023). "FrugalGPT: How to Use Large Language Models
    While Reducing Cost and Improving Performance." arXiv:2305.05176.

28. Stripelis, D. et al. (2024). "TensorOpera Router: A Multi-Model Router for Efficient
    LLM Inference." arXiv:2408.12320.

29. Hu, Q.J. et al. (2024). "RouterBench: A Benchmark for Multi-LLM Routing System."
    arXiv:2403.12031.

30. Panda, P. et al. (2025). "Adaptive LLM Routing under Budget Constraints (PILOT)."
    arXiv:2508.21141.

31. Okamoto, M. et al. (2026). "Trust by Design: Skill Profiles for Transparent,
    Cost-Aware LLM Routing (BELLA)." arXiv:2602.02386.

32. Woisetschlager, H. et al. (2025). "MESS+: Dynamically Learned Inference-Time LLM
    Routing with SLA Guarantees." arXiv:2505.19947.

33. Jin, B. et al. (2025). "Controlling Performance and Budget of a Centralized
    Multi-agent LLM System with Reinforcement Learning (CoRL)." arXiv:2511.02755.

34. Gandhi, S. et al. (2024). "BudgetMLAgent: A Cost-Effective LLM Multi-Agent system
    for Automating Machine Learning Tasks." arXiv:2411.07464. AIMLSystems 2024.

35. Liu, J. et al. (2025). "CostBench: Evaluating Multi-Turn Cost-Optimal Planning and
    Adaptation in Dynamic Environments." arXiv:2511.02734.

36. Ma, B. et al. (2025). "AutoMaAS: Self-Evolving Multi-Agent Architecture Search."
    arXiv:2510.02669.

37. Bhatt, M. et al. (2025). "COALESCE: Economic and Security Dynamics of Skill-Based
    Task Outsourcing Among Team of Autonomous LLM Agents." arXiv:2506.01900.

38. Wang, N. et al. (2025). "Efficient Agents: Building Effective Agents While Reducing
    Cost." arXiv:2508.02694.

39. Harrasse, A. et al. (2024). "D3: A Cost-Aware Adversarial Framework for Reliable and
    Interpretable LLM Evaluation." arXiv:2410.04663.

40. Briva Iglesias, V. & Dogru, G. (2025). "AI agents may be worth the hype but not the
    resources (yet)." arXiv:2505.01560.

41. Wang, S. (2025). "Maestro: Joint Graph & Config Optimization for Reliable AI Agents."
    arXiv:2509.04642.

### Rate Limit Handling

42. Farkiani, B. et al. (2025). "Rethinking HTTP API Rate Limiting: A Client-Side
    Approach." arXiv:2510.04516.

43. Sheng, Y. et al. (2023). "Fairness in Serving Large Language Models (VTC)."
    arXiv:2401.00588.

44. Gupta, A. (2026). "ReliabilityBench: Evaluating LLM Agent Reliability Under
    Production-Like Stress Conditions." arXiv:2601.06112.

45. Ding, Z. et al. (2025). "Network and Systems Performance Characterization of
    MCP-Enabled LLM Agents." arXiv:2511.07426.

### Additional Token Efficiency and Multi-Agent Communication

46. Fu, M. et al. (2026). "LatentMem: Customizing Latent Memory for Multi-Agent Systems."
    arXiv:2602.03036.

47. Fan, W. et al. (2026). "TodyComm: Task-Oriented Dynamic Communication for Multi-Round
    LLM-based Multi-Agent System." arXiv:2602.03688.

48. Ran, D. et al. (2025). "UIFormer: From User Interface to Agent Interface."
    arXiv:2512.13438.

49. Zhang, C. et al. (2025). "TeaRAG: A Token-Efficient Agentic RAG Framework."
    arXiv:2511.05385.

50. Ling, S. et al. (2025). "ELHPlan: Efficient Long-Horizon Task Planning for
    Multi-Agent Collaboration." arXiv:2509.24230.

51. Zhang, H. et al. (2025). "HyperAgent: Leveraging Hypergraphs for Topology Optimization
    in Multi-Agent Communication." arXiv:2510.10611.

52. Shao, W. et al. (2025). "M3Prune: Hierarchical Communication Graph Pruning."
    arXiv:2511.19969.

53. Su, H. et al. (2026). "ContextEvolve: Multi-Agent Context Compression."
    arXiv:2602.02597.

54. Liu, J. et al. (2025). "RCR-Router: Role-Aware Context Routing for Multi-Agent LLM
    Systems." arXiv:2508.04903.

55. Huan, C. et al. (2025). "GLM: Scaling Graph Chain-of-Thought Reasoning."
    arXiv:2511.01633.

56. Prateek, S. (2025). "Static-DRA: A Hierarchical Tree-based approach for Configurable
    Deep Research Agent." arXiv:2512.03887.

57. Hu, Z. et al. (2026). "Beyond RAG for Agent Memory: Retrieval by Decoupling and
    Aggregation." arXiv:2602.02007.

### LLM Routing and Model Selection

58. Yan, C. et al. (2026). "ZeroRouter: Breaking Model Lock-in via a Universal Latent
    Space." arXiv:2601.06220.

59. Li, H. et al. (2026). "LLMRouterBench: A Massive Benchmark for LLM Routing."
    arXiv:2601.07206.

60. Chiang, C.-K. et al. (2025). "LLM Routing with Dueling Feedback." arXiv:2510.00841.

61. Tran, C. et al. (2025). "Arch-Router: Aligning LLM Routing with Human Preferences."
    arXiv:2506.16655.

62. Piskala, D.B. et al. (2025). "OptiRoute: Dynamic LLM Routing Based on User
    Preferences." arXiv:2502.16696.

63. Guo, X. et al. (2025). "MoMA: Towards Generalized Routing -- Model and Agent
    Orchestration." arXiv:2509.07571.

### Semantic Caching and Serving Optimization

64. Gill, W. et al. (2024). "MeanCache: User-Centric Semantic Caching for LLM Web
    Services." arXiv:2403.02694.

65. Li, Y. et al. (2025). "EcoServe: Designing Carbon-Aware AI Inference Systems."
    arXiv:2502.05043.

---

## 10. Appendix: Key Frameworks and Systems Reference

| System | Key Feature | Cost Impact | Reference |
|--------|------------|-------------|-----------|
| FrugalGPT | LLM cascading | Up to 98% cost reduction | arXiv:2305.05176 |
| BudgetMLAgent | Planner + Workers + cascade | 94.2% cost reduction | arXiv:2411.07464 |
| CoRL | RL-based budget-controlled coordination | Surpasses best expert at high budget | arXiv:2511.02755 |
| BATS | Budget tracker + adaptive planning | First budget-aware scaling study | arXiv:2511.17006 |
| HASHIRU | Resource-aware CEO/employee agents | Outperforms Gemini 2.0 Flash | arXiv:2506.04255 |
| Co-Saving | Experience-based shortcuts | 50.85% token reduction | arXiv:2505.21898 |
| Optima | RL-trained communication | 2.8x perf at <10% tokens | arXiv:2410.08115 |
| AgentDropout | Graph-based agent elimination | 21.6% prompt token reduction | arXiv:2503.18891 |
| CostBench | Cost-centric evaluation | Reveals 40% perf drop under dynamics | arXiv:2511.02734 |
| ATB/AATB | Client-side rate limit handling | 97.3% fewer 429 errors | arXiv:2510.04516 |
| VTC | Fair LLM serving scheduler | 2x fairness bound | arXiv:2401.00588 |
| TALE | Token-budget-aware reasoning | 67% output token reduction | arXiv:2412.18547 |
| Efficient Agents | Cost-of-pass optimization | 28.4% cost-of-pass improvement | arXiv:2508.02694 |
| COALESCE | Agent task outsourcing market | 20.3-41.8% cost reduction | arXiv:2506.01900 |
| AgentInfer | Co-designed inference + architecture | 50%+ token reduction, 1.8-2.5x speedup | arXiv:2512.18337 |
