# Agent Teams vs Agent Swarms: A Comprehensive Literature Review

**Date:** 2026-02-27
**Scope:** Multi-agent LLM systems (2024-2026)
**Focus:** Structured agent teams (hierarchical, role-based) vs agent swarms (decentralized, emergent)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Definitions and Conceptual Distinction](#definitions-and-conceptual-distinction)
3. [Academic Papers](#academic-papers)
4. [Industry Blog Posts and Engineering Reports](#industry-blog-posts)
5. [Framework Documentation and Architecture Guides](#framework-docs)
6. [Taxonomies and Classification Frameworks](#taxonomies)
7. [Empirical Comparisons](#empirical-comparisons)
8. [Practical Guidelines for Choosing](#practical-guidelines)
9. [Hybrid Approaches](#hybrid-approaches)
10. [Key Tradeoffs Summary](#tradeoffs)
11. [Full Citation List](#citations)

---

## 1. Executive Summary

The literature reveals a spectrum of multi-agent coordination patterns rather than a simple binary choice. The field is converging on several key insights:

1. **Agent teams** (structured, role-based, hierarchical) excel at tasks requiring accountability, quality control, and predictable workflows, but create bottlenecks at the coordinator and scale poorly when the orchestrator is overloaded.

2. **Agent swarms** (decentralized, emergent, self-organizing) excel at exploration-heavy tasks, parallel search, and situations requiring resilience, but struggle with tight coordination, shared state, and cost control.

3. **The emerging consensus favors hybrid approaches** that combine hierarchical strategic planning with decentralized tactical execution, mirroring the "centralized training, decentralized execution" paradigm from multi-agent reinforcement learning.

4. **Orchestration topology matters more than model selection** when underlying models converge in capability (AdaptOrch, 2026).

5. **The practical recommendation** from Anthropic, the Swarms framework, and multiple surveys: start with the simplest approach (single agent or prompt chaining), add structure only when demonstrably needed, and choose architecture based on task decomposability, inter-agent dependency, and parallelizability.

---

## 2. Definitions and Conceptual Distinction

### Agent Teams (Structured/Hierarchical)
- **Definition:** Multiple agents organized with explicit roles, responsibilities, and communication protocols. A coordinator/manager/orchestrator assigns tasks and synthesizes results.
- **Communication:** Typically top-down task assignment with bottom-up reporting. May include lateral communication within defined channels.
- **Coordination:** Centralized or semi-centralized. An orchestrator maintains global state and makes delegation decisions.
- **Analogy:** A software development team with a tech lead, frontend developer, backend developer, and QA engineer.
- **Example frameworks:** CrewAI (crews with roles), LangGraph (DAG-based), Anthropic orchestrator-workers pattern.

### Agent Swarms (Decentralized/Emergent)
- **Definition:** Multiple agents operating with local-only information and interaction rules, where global behavior emerges from local interactions without central control.
- **Communication:** Peer-to-peer, local neighborhood, or stigmergic (via shared environment/artifacts).
- **Coordination:** Decentralized. No single agent has a global view; coordination emerges from interaction dynamics.
- **Analogy:** An ant colony where individual ants follow simple pheromone rules but collectively find optimal food paths.
- **Example frameworks:** OpenAI Swarm (handoff-based), Swarms library, SwarmSys, Society of HiveMind.

### The Blurring Boundary
The term "swarm" has been co-opted in the LLM community to mean different things:
- **Classical swarm intelligence** (Boids, ACO, PSO): Simple agents, local rules, emergent behavior. Truly decentralized.
- **OpenAI Swarm / "agent swarms" in LLM context:** Often refers to handoff-based routing between specialized agents. Not truly decentralized -- more like sequential delegation.
- **Claude Code Agent Teams / "swarm mode":** Parallel agents with shared task lists and direct messaging. A hybrid between teams and swarms.

Rahman et al. (2025) argue in "LLM-Powered Swarms: A New Frontier or a Conceptual Stretch?" that LLM-based swarms fundamentally break classical swarm principles: they trade decentralization for centralized API calls, invert the simplicity-to-complexity relationship, and replace genuine emergence with predetermined prompts.

---

## 3. Academic Papers

### 3.1 Surveys and Overviews

**[S1] "Large Language Model based Multi-Agents: A Survey of Progress and Challenges"**
- Authors: Guo et al. (2024)
- Venue: IJCAI 2024
- URL: https://arxiv.org/abs/2402.01680
- Key contribution: Comprehensive survey covering agent profiling, communication mechanisms, and capability growth. Classifies MAS by domain (problem-solving, simulation, evaluation) and communication structure.

**[S2] "Multi-Agent Collaboration Mechanisms: A Survey of LLMs"**
- Authors: Tran et al. (2025)
- URL: https://arxiv.org/abs/2501.06322
- Key contribution: Extensible framework characterizing collaboration along five dimensions: actors, types (cooperation/competition/coopetition), structures (peer-to-peer/centralized/distributed), strategies (role-based/model-based), and coordination protocols. Identifies the shift from isolated models to collaboration-centric approaches.

**[S3] "Beyond Self-Talk: A Communication-Centric Survey of LLM-Based Multi-Agent Systems"**
- Authors: Yan et al. (2025)
- URL: https://arxiv.org/abs/2502.14321
- Key contribution: Framework integrating system-level communication (architecture, goals, protocols) with internal communication (strategies, paradigms, content). Identifies communication efficiency, security, and scalability as key challenges.

**[S4] "Multi-Agent Coordination across Diverse Applications: A Survey"**
- Authors: Sun et al. (2025)
- URL: https://arxiv.org/abs/2502.14743
- Key contribution: Answers four fundamental coordination questions (what/why/who/how). Identifies **hybridization of hierarchical and decentralized coordination** as a promising future direction. Covers applications from warehouse automation to LLM-based systems.

**[S5] "A Survey on LLM-based Multi-Agent System: Recent Advances and New Frontiers"**
- Authors: Chen et al. (2024)
- URL: https://arxiv.org/abs/2412.17481
- Key contribution: Framework encompassing solving complex tasks, simulating scenarios, and evaluating generative agents.

**[S6] "LLMs Working in Harmony: A Survey on Building Effective LLM-Based Multi Agent Systems"**
- Authors: Aratchige & Ilmini (2025)
- URL: https://arxiv.org/abs/2504.01963
- Key contribution: Focus on four critical areas: Architecture, Memory, Planning, and Technologies/Frameworks. Reviews Mixture of Agents architecture and ReAct planning model.

**[S7] "Agentic AI Frameworks: Architectures, Protocols, and Design Challenges"**
- Authors: Derouiche et al. (2025)
- URL: https://arxiv.org/abs/2508.10146
- Key contribution: Systematic comparison of CrewAI, LangGraph, AutoGen, Semantic Kernel, Agno, Google ADK, and MetaGPT. Establishes a foundational taxonomy and analyzes communication protocols (Contract Net Protocol, A2A, ANP, Agora).

### 3.2 Hierarchical / Team-Based Approaches

**[H1] "Can Lessons From Human Teams Be Applied to Multi-Agent Systems?"**
- Authors: Muralidharan et al. (2025)
- URL: https://arxiv.org/abs/2510.07488
- Key finding: **Flat teams tend to perform better than hierarchical ones** on commonsense and social reasoning tasks (CommonsenseQA, StrategyQA, Social IQa, Latent Implicit Hate). Diversity has a nuanced impact. Agents are overconfident about their team performance.
- Significance: One of the few empirical comparisons of flat vs. hierarchical structures.

**[H2] "AdaptOrch: Task-Adaptive Multi-Agent Orchestration"**
- Authors: Yu (2026)
- URL: https://arxiv.org/abs/2602.16873
- Key finding: When LLMs converge in capability, **orchestration topology dominates system-level performance over individual model capability**. Proposes four canonical topologies: parallel, sequential, hierarchical, and hybrid. Topology-aware orchestration achieves 12-23% improvement over static single-topology baselines.
- Contributions: Performance Convergence Scaling Law; Topology Routing Algorithm mapping task DAGs to optimal patterns in O(|V| + |E|) time.

**[H3] "How to Train a Leader: Hierarchical Reasoning in Multi-Agent LLMs"**
- Authors: Estornell et al. (2025)
- URL: https://arxiv.org/abs/2507.08960
- Key finding: Training only a single leader LLM to coordinate untrained peers improves performance on BBH, MATH, and MMLU. Leaders trained with MLPO perform better even in single-agent settings.

**[H4] "HALO: Hierarchical Autonomous Logic-Oriented Orchestration"**
- Authors: Hou et al. (2025)
- URL: https://arxiv.org/abs/2505.13516
- Key finding: Three-level hierarchy (high-level planning agent, mid-level role-design agents, low-level inference agents) with MCTS-based workflow search yields 14.4% average improvement over baselines.

**[H5] "Agyn: A Multi-Agent System for Team-Based Autonomous Software Engineering"**
- Authors: Benkovich & Valkov (2026)
- URL: https://arxiv.org/abs/2602.01465
- Key finding: Explicitly modeling software engineering as an organizational process with specialized agent roles (coordination, research, implementation, review) resolves 72.2% of SWE-bench 500 tasks. Team structure and methodology matter as much as model improvements.

**[H6] "CTHA: Constrained Temporal Hierarchical Architecture"**
- Authors: Jardine (2026)
- URL: https://arxiv.org/abs/2601.10738
- Key finding: Temporal hierarchies with constrained inter-layer communication yield 47% reduction in failure cascades and 2.3x improvement in sample efficiency over unconstrained hierarchical baselines.

**[H7] "Lemon Agent Technical Report"**
- Authors: Jiang et al. (2026)
- URL: https://arxiv.org/abs/2602.07092
- Key finding: Orchestrator-worker architecture with hierarchical self-adaptive scheduling achieves 91.36% on GAIA benchmark. Two-tier architecture balances global coordination with local execution.

### 3.3 Swarm / Decentralized Approaches

**[D1] "Multi-Agent Systems Powered by Large Language Models: Applications in Swarm Intelligence"**
- Authors: Jimenez-Romero et al. (2025)
- URL: https://arxiv.org/abs/2503.03800
- Key finding: LLMs can replace hard-coded agent programs in swarm simulations (ant colony foraging, bird flocking). Both structured/rule-based and autonomous/knowledge-driven prompts can induce emergent behaviors.

**[D2] "The Society of HiveMind: Multi-Agent Optimization of Foundation Model Swarms"**
- Authors: Mamie & Rao (2025)
- URL: https://arxiv.org/abs/2503.05473
- Key finding: Swarm-based orchestration provides **negligible benefit on knowledge tasks but significant improvement on logical reasoning tasks**. Diverse model ensembles outperform homogeneous ones.

**[D3] "LLM-Powered Swarms: A New Frontier or a Conceptual Stretch?"**
- Authors: Rahman et al. (2025)
- URL: https://arxiv.org/abs/2506.14496
- Key finding: LLM-based swarms do NOT capture fundamental principles of classical swarm intelligence. LLM Boids required ~300x more computation time than classical Boids. However, LLM-based ACO produced more optimized path distributions in fewer iterations. **LLM swarms trade execution speed for intuitive abstraction and flexible reasoning.**

**[D4] "SwarmSys: Decentralized Swarm-Inspired Agents for Scalable and Adaptive Reasoning"**
- Authors: Li et al. (2025)
- URL: https://arxiv.org/abs/2510.10047
- Key finding: Closed-loop framework with Explorers, Workers, and Validators using pheromone-inspired reinforcement. Outperforms baselines on symbolic reasoning, research synthesis, and scientific programming. **"Coordination scaling may rival model scaling in advancing LLM intelligence."**

**[D5] "SwarmAgentic: Towards Fully Automated Agentic System Generation via Swarm Intelligence"**
- Authors: Zhang et al. (2025)
- URL: https://arxiv.org/abs/2506.15672
- Key finding: PSO-inspired population-based optimization of agent system structures achieves +261.8% relative improvement over ADAS on TravelPlanner. Demonstrates that swarm optimization can effectively search the space of possible multi-agent architectures.

**[D6] "Swarm Intelligence Enhanced Reasoning (SIER)"**
- Authors: Zhu et al. (2025)
- URL: https://arxiv.org/abs/2505.17115
- Key finding: Formulating LLM reasoning as optimization with density-driven swarm intelligence enhances both solution quality and diversity.

**[D7] "Benchmarking LLMs' Swarm Intelligence (SwarmBench)"**
- Authors: Ruan et al. (2025)
- URL: https://arxiv.org/abs/2505.04364
- Key finding: Current LLMs **significantly struggle with robust long-range planning and adaptive strategy formation** under decentralized swarm constraints. Performance varies dramatically across task types (pursuit, synchronization, foraging, flocking, transport).

**[D8] "Emergent Coordination via Pressure Fields and Temporal Decay"**
- Authors: Rodriguez (2026)
- URL: https://arxiv.org/abs/2601.08129
- Key finding: **Implicit coordination through shared pressure gradients (48.5% solve rate) dramatically outperforms conversation-based coordination (12.6%), hierarchical control (1.5%), and sequential baselines (0.4%)** on meeting room scheduling. Constraint-driven emergence offers a simpler and more effective foundation for multi-agent AI.

**[D9] "Swarms of LLM Agents for Protein Sequence Design"**
- Authors: Wang et al. (2025)
- URL: https://arxiv.org/abs/2511.22311
- Key finding: Decentralized per-residue agents with local neighborhood interactions achieve effective protein design without motif scaffolds or MSA. Demonstrates emergent behaviors and effective fitness landscape navigation.

### 3.4 Incident Response: Direct Comparison of Centralized vs Decentralized

**[C1] "Multi-Agent Collaboration in Incident Response with Large Language Models"**
- Authors: Liu (2024)
- URL: https://arxiv.org/abs/2412.00652
- Key finding: Directly compares centralized, decentralized, and hybrid multi-agent configurations for cybersecurity incident response. One of the few papers to systematically evaluate all three structures on the same task.

### 3.5 Taxonomy Paper

**[T1] "A Taxonomy of Hierarchical Multi-Agent Systems: Design Patterns, Coordination Mechanisms, and Industrial Applications"**
- URL: https://arxiv.org/abs/2508.12683
- Key contribution: Five-dimensional taxonomy:
  1. **Control hierarchy:** Centralized to decentralized to hybrid
  2. **Information flow:** Top-down, bottom-up, peer-to-peer
  3. **Role/task delegation:** Static vs. dynamic/emergent
  4. **Temporal hierarchy:** Single timescale vs. multi-timescale layered
  5. **Communication structure:** Static vs. dynamic networks
- Maps six coordination mechanisms (Contract Net, Auctions, Consensus, Feudal MARL, Organizational, Platform-based) to these dimensions.
- Identifies **hybrid approaches** as increasingly favored.

---

## 4. Industry Blog Posts and Engineering Reports

### 4.1 Anthropic: "Building Effective Agents" (2024)
- URL: https://www.anthropic.com/research/building-effective-agents
- Key framework: Distinguishes **workflows** (predefined code paths) from **agents** (LLM-directed processes).
- Five composable patterns:
  1. **Prompt Chaining:** Sequential steps with gates. Trades latency for accuracy.
  2. **Routing:** Input classification to specialized handlers.
  3. **Parallelization:** Simultaneous execution (sectioning or voting).
  4. **Orchestrator-Workers:** Dynamic task decomposition and delegation.
  5. **Evaluator-Optimizer:** Generate-then-critique feedback loop.
- **Core principle:** "Complexity increases only when demonstrably improving outcomes." Start simple, add multi-agent structure only when needed.

### 4.2 Anthropic: "How We Built Our Multi-Agent Research System" (2025)
- URL: https://www.anthropic.com/engineering/multi-agent-research-system
- Architecture: Orchestrator-worker pattern with lead agent + 3-5 parallel subagents.
- Results: 90.2% better than single-agent Claude Opus 4. 90% reduction in research time.
- Key finding: Token usage alone accounts for 80% of performance differences.
- Eight prompt engineering principles, including "parallelize aggressively" and "scale effort dynamically."
- **Tradeoffs:** Agents use ~4x more tokens than chat; multi-agent uses ~15x more. Poor fit for tightly coupled tasks (e.g., coding with shared state).

### 4.3 Claude Code Agent Teams / Swarm Mode (2025-2026)
- URL: https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/
- URL: https://www.atcyrus.com/stories/what-is-claude-code-swarm-feature
- Three levels: **Subagents** (fire-and-forget), **Agent Teams** (shared task list + direct messaging), **Solo sessions** (full control).
- Key insight: "Subagents are fire-and-forget workers. Agent teams are collaborators. Subagents report back to main only. Agent teams share findings and coordinate directly."
- Cost: Agent teams use ~4x more tokens than subagents for the same number of agents.
- Best for: Large features (parallel tracks), QA swarms (multiple testing perspectives), competing hypotheses (debate and converge).

### 4.4 Framework Comparison Blog Posts

**Langfuse Blog: "Comparing Open-Source AI Agent Frameworks" (2025)**
- URL: https://langfuse.com/blog/2025-03-19-ai-agent-comparison
- Identifies five orchestration patterns: Graph-based (LangGraph), Conversation-driven (AutoGen), Role-based collaboration (CrewAI), Code-centric (Smolagents), Skill-based (Semantic Kernel).

**Softmax Data: "Agent Swarm vs Anthropic Workflows vs LangGraph" (2025)**
- URL: https://blog.softmaxdata.com/agent-architectures-compared/
- Key insight: "Agents trade latency and cost for better task performance." Verify whether a single well-prompted model solves your problem before adopting multi-agent complexity.

**DEV Community: "The Great AI Agent Showdown of 2026"**
- URL: https://dev.to/topuzas/the-great-ai-agent-showdown-of-2026-openai-autogen-crewai-or-langgraph-1ea8

**Devels.ai: "OpenAI Swarm vs LangGraph vs AutoGen vs CrewAI"**
- URL: https://www.devels.ai/en/blog/openai-swarm-vs-langgraph-vs-autogen-vs-crewai-which-ai-agent-framework-wins

---

## 5. Framework Documentation and Architecture Guides

### 5.1 Swarms Framework (swarms.world)
- URL: https://docs.swarms.world/en/latest/swarms/concept/swarm_architectures/
- URL: https://docs.swarms.world/en/latest/swarms/concept/how_to_choose_swarms/
- Provides 25+ architecture types organized into categories:
  - **Hierarchical:** Tree, HierarchicalSwarm
  - **Consensus-Based:** Majority Voting, Council as Judge, Debate with Judge, Election
  - **Workflow-Based:** Sequential, Concurrent, Graph, Batched Grid
  - **Communication-Centric:** GroupChat, Interactive GroupChat, Round Robin, Dynamic Conversational
  - **Ensemble Methods:** Mixture of Agents, LLM Council, Self MoA Seq
  - **Meta/Hybrid:** Auto-Builder, Swarm Rearrange, Hybrid Hierarchical Cluster, SwarmRouter

### 5.2 CrewAI
- Production-grade framework for role-based AI agent teams
- "Crews" with agents assigned specific roles, tools, and goals
- Claims 60% of Fortune 500 companies as users
- Strength: Built-in memory (short and long-term), production readiness

### 5.3 OpenAI Agents SDK (formerly Swarm)
- OpenAI Swarm (2024): Experimental, lightweight, handoff-based routing. Not production-ready.
- OpenAI Agents SDK (March 2025): Production-ready replacement with handoff patterns.
- Mental model: "A customer service call where you get transferred between departments"
- Sequential, stateless, linear flow

### 5.4 Microsoft AutoGen / Agent Framework
- Conversation-driven architecture: Agents as asynchronous conversation participants
- AutoGen merged with Semantic Kernel (October 2025) into unified Microsoft Agent Framework
- Cloud-agnostic, supports all major LLM providers
- Strength: Flexibility, distributed runtimes, custom collaboration patterns
- Weakness: "Free-form" chat can be unpredictable for business logic

### 5.5 LangGraph
- Graph-based approach: Nodes as agents, edges as communication paths
- Two patterns: Collaboration (shared history) or Hierarchical/Supervisor (delegated with private workspaces)
- Best for: Production systems requiring full orchestration control and state management

### 5.6 Google ADK
- Python framework launched at Google Cloud NEXT 2025
- Hierarchical agents with tight Google Cloud integration
- Software-engineering-first approach with testing harness and CLI tooling

---

## 6. Taxonomies and Classification Frameworks

### 6.1 The Five-Dimensional Taxonomy (arxiv 2508.12683)
Most comprehensive taxonomy identified:

| Dimension | Spectrum |
|-----------|----------|
| Control | Fully centralized <-> Hybrid <-> Fully decentralized |
| Information Flow | Top-down <-> Bidirectional <-> Peer-to-peer |
| Role Assignment | Static/predetermined <-> Dynamic/emergent |
| Temporal Layering | Single timescale <-> Multi-timescale (strategic + tactical) |
| Communication | Static network <-> Dynamic/adaptive network |

### 6.2 Anthropic's Pattern Hierarchy
From simplest to most complex:
1. Single LLM call (optimized prompt)
2. Prompt Chaining (sequential workflow)
3. Routing (classification + dispatch)
4. Parallelization (simultaneous independent tasks)
5. Orchestrator-Workers (dynamic decomposition)
6. Evaluator-Optimizer (iterative refinement)
7. Full Autonomous Agent (LLM controls tool use)

### 6.3 AdaptOrch's Four Canonical Topologies
1. **Parallel:** Independent agents, results aggregated
2. **Sequential:** Pipeline of agents, each processing prior output
3. **Hierarchical:** Manager decomposes and delegates to workers
4. **Hybrid:** Dynamic combination of the above based on task DAG

### 6.4 Tran et al.'s Collaboration Framework
Five dimensions of multi-agent collaboration:
1. **Actors:** Which agents participate
2. **Types:** Cooperation, competition, or coopetition
3. **Structures:** Peer-to-peer, centralized, or distributed
4. **Strategies:** Role-based or model-based
5. **Coordination Protocols:** Communication rules and patterns

### 6.5 Communication Topology Options (from multiple sources)
- **Star/Centralized:** All agents communicate through a hub
- **Hierarchical/Tree:** Manager-worker with multiple levels
- **Fully Connected/Mesh:** Every agent can talk to every other
- **Sequential/Pipeline:** Linear chain of processing
- **Small-World:** Clustered with cross-cluster shortcuts
- **Scale-Free:** Hub-dominated network
- **DAG:** Directed acyclic graph of dependencies

---

## 7. Empirical Comparisons

### 7.1 Flat vs. Hierarchical Teams (Muralidharan et al., 2025)
- **Task:** CommonsenseQA, StrategyQA, Social IQa, Latent Implicit Hate
- **Finding:** Flat teams outperform hierarchical ones on commonsense/social reasoning
- **Caveat:** Agents are overconfident about team performance

### 7.2 Topology Selection Impact (AdaptOrch, 2026)
- **Tasks:** SWE-bench (coding), GPQA (reasoning), RAG tasks
- **Finding:** Topology-aware orchestration: 12-23% improvement over static topologies
- **Key insight:** Orchestration topology matters more than model selection

### 7.3 Pressure Fields vs. Hierarchical Control (Rodriguez, 2026)
- **Task:** Meeting room scheduling (1,350 trials)
- **Finding:** Implicit coordination (48.5%) dramatically outperforms hierarchical control (1.5%) and conversation-based coordination (12.6%)
- **Implication:** Constraint-driven emergence can be simpler and more effective than explicit hierarchies

### 7.4 LLM Swarms vs. Classical Swarms (Rahman et al., 2025)
- **Tasks:** Boids flocking, Ant Colony Optimization
- **Finding:** LLM Boids: ~300x slower than classical. LLM ACO: better path optimization in fewer iterations.
- **Conclusion:** LLM swarms excel at reasoning-heavy optimization but fail at real-time coordination

### 7.5 Swarm Intelligence for Reasoning (HiveMind, 2025)
- **Finding:** Negligible benefit on knowledge tasks, significant benefit on logical reasoning
- **Implication:** Swarm approaches add value specifically for reasoning-intensive problems

### 7.6 SwarmBench: LLM Swarm Intelligence Benchmark (Ruan et al., 2025)
- **Tasks:** Pursuit, Synchronization, Foraging, Flocking, Transport
- **Finding:** Current LLMs significantly struggle with robust long-range planning under decentralized constraints. Performance varies dramatically by task type.

### 7.7 Team Structure in Software Engineering (Agyn, 2026)
- **Task:** SWE-bench 500
- **Finding:** Explicitly modeled team structure (72.2% resolution) outperforms single-agent baselines
- **Insight:** "Future progress may depend as much on organizational design and agent infrastructure as on model improvements"

### 7.8 Multi-Agent vs. Single-Agent Token Economics (Anthropic, 2025)
- **Finding:** Single agent: 1x tokens. Agentic: ~4x tokens. Multi-agent: ~15x tokens.
- **But:** Token usage accounts for 80% of performance variance -- more tokens generally means better results.

---

## 8. Practical Guidelines for Choosing

### 8.1 When to Use Structured Agent Teams

**Choose teams when:**
- Tasks have clear role separation and division of labor
- Quality control and accountability are important
- Workflows are well-defined or semi-structured
- Human oversight is needed at specific checkpoints
- The problem maps to a known organizational structure (e.g., dev team, clinical team, trading desk)
- You need predictable, auditable behavior
- Tasks have moderate parallelism with some interdependence

**Real-world examples:**
- Software engineering (Agyn): coordinator, researcher, implementer, reviewer
- Clinical diagnosis (ColaCare, MedChat): specialist agents + meta-agent orchestrator
- Financial trading (TradingAgents): analysts, risk managers, traders
- Incident response (Liu, 2024): centralized coordinator with specialist responders

### 8.2 When to Use Agent Swarms

**Choose swarms when:**
- Tasks are massively parallelizable with minimal interdependence
- Exploration breadth matters more than coordination depth
- Resilience to individual agent failures is important
- The search space is large and benefits from diverse approaches
- You want emergent solutions that might not come from predetermined structure
- Optimization across a large solution space is needed
- Real-time adaptation without central bottlenecks is required

**Real-world examples:**
- Research and information gathering (Anthropic research system)
- Protein design (Wang et al., 2025): per-residue agents with local interactions
- Drug discovery (PharmaSwarm): parallel hypothesis generation and validation
- Reasoning enhancement (SIER, ASI): diverse solution exploration

### 8.3 Decision Matrix

| Factor | Favors Teams | Favors Swarms |
|--------|-------------|---------------|
| Task structure | Well-defined, decomposable | Open-ended, exploratory |
| Inter-agent dependency | High (shared state needed) | Low (independent subtasks) |
| Quality requirements | High (needs oversight) | Moderate (diversity valued) |
| Cost sensitivity | Moderate (structured overhead) | Variable (can explode) |
| Latency tolerance | Low (needs fast coordination) | High (parallel exploration OK) |
| Fault tolerance needs | Low (coordinator manages) | High (no single point of failure) |
| Scale | Moderate (10s of agents) | Large (100s+ agents) |
| Predictability needs | High | Low |
| Domain knowledge | Deep, specialized roles | Broad, diverse perspectives |

### 8.4 The Anthropic Escalation Ladder
From their "Building Effective Agents" guide:
1. Start with a single well-prompted LLM
2. Add prompt chaining if steps are clear
3. Add routing if inputs vary in type
4. Add parallelization if subtasks are independent
5. Add orchestrator-workers if decomposition is dynamic
6. Add evaluator-optimizer if iterative improvement is needed
7. Use full autonomous agents only for genuinely open-ended problems

---

## 9. Hybrid Approaches

The most promising direction identified across the literature is hybrid architectures that combine hierarchical strategic oversight with decentralized tactical execution.

### 9.1 Key Hybrid Patterns

**Centralized Training, Decentralized Execution (CTDE)**
- From MARL literature (Li et al., "Learn as Individuals, Evolve as a Team," 2025)
- Individual agents learn local utility functions; team maintains shared cooperation knowledge
- Combines individual learning with team evolution

**Hierarchical with Local Autonomy**
- Strategic decisions centralized, tactical decisions decentralized
- Examples: Smart grid management, warehouse automation
- The taxonomy paper (2508.12683) identifies this as increasingly favored

**Temporal Hierarchy**
- Different layers operate at different timescales
- High-level: Long-horizon planning (strategic)
- Low-level: Short-horizon execution (tactical)
- CTHA (Jardine, 2026): Constrained inter-layer communication for stability

**Dynamic Leader Election**
- No permanent hierarchy; leaders emerge situationally
- SwarmSys (Li et al., 2025): Explorers, Workers, Validators cycle through roles
- RALLY (Wang et al., 2025): Role-adaptive switching in UAV swarms

**Hybrid Hierarchical Cluster**
- From Swarms framework: Combines hierarchical and peer-to-peer communication
- Central coordination for cross-department tasks; peer coordination within departments

**Orchestrator with Swarm Workers**
- A structured orchestrator delegates to a swarm of workers that self-organize
- Anthropic's research system: Lead agent coordinates, but subagents execute independently in parallel
- Lemon Agent (2026): Orchestrator-worker with two-tier self-adaptive scheduling

### 9.2 The Convergence Thesis
Multiple sources converge on the same insight:
- Sun et al. (2025): "hybridization of hierarchical and decentralized mechanism" is a crucial strategy
- AdaptOrch (2026): Dynamic topology selection based on task structure
- The taxonomy paper (2508.12683): "well-designed hierarchies can greatly enhance coordination" while acknowledging the need to "marry hierarchical and decentralized coordination"
- Rodriguez (2026): Even "implicit coordination" (neither purely hierarchical nor purely swarm) can dramatically outperform explicit structures

---

## 10. Key Tradeoffs Summary

### 10.1 Control vs. Autonomy
- **Teams:** High control, predictable behavior, human-auditable decisions
- **Swarms:** High autonomy, emergent solutions, harder to debug/explain
- **Hybrid:** Strategic control with tactical autonomy

### 10.2 Efficiency vs. Resilience
- **Teams:** Efficient coordination but single point of failure at orchestrator
- **Swarms:** Resilient to individual failures but coordination overhead grows
- **Hybrid:** Hierarchical efficiency with decentralized fallbacks

### 10.3 Cost vs. Performance
- **Single agent:** 1x tokens, baseline performance
- **Structured team:** ~4-5x tokens, moderate improvement
- **Multi-agent swarm:** ~15x+ tokens, significant improvement on complex tasks
- **Key finding:** Token usage accounts for 80% of performance variance (Anthropic, 2025)

### 10.4 Scalability vs. Coherence
- **Teams:** Coherent outputs but bottleneck at coordinator as team grows
- **Swarms:** Scale well (no central bottleneck) but coherence degrades
- **HierarchicalSwarm:** Creates bottlenecks if the director is overloaded

### 10.5 Generality vs. Specialization
- **Teams:** Deep specialization through role assignment
- **Swarms:** Broad exploration through diversity
- **Mixture of Agents:** Combines specialized agents with aggregation

### 10.6 Speed vs. Quality
- **Parallel swarms:** Fast (all agents work simultaneously) but may miss coordination
- **Sequential teams:** Slower but each step builds on validated prior work
- **Orchestrator-workers:** Dynamic balance based on task needs

---

## 11. Full Citation List

### Academic Papers (arXiv)

1. Guo et al. "Large Language Model based Multi-Agents: A Survey." IJCAI 2024. https://arxiv.org/abs/2402.01680
2. Tran et al. "Multi-Agent Collaboration Mechanisms: A Survey of LLMs." 2025. https://arxiv.org/abs/2501.06322
3. Yan et al. "Beyond Self-Talk: A Communication-Centric Survey of LLM-Based MAS." 2025. https://arxiv.org/abs/2502.14321
4. Sun et al. "Multi-Agent Coordination across Diverse Applications: A Survey." 2025. https://arxiv.org/abs/2502.14743
5. Chen et al. "A Survey on LLM-based Multi-Agent System." 2024. https://arxiv.org/abs/2412.17481
6. Aratchige & Ilmini. "LLMs Working in Harmony." 2025. https://arxiv.org/abs/2504.01963
7. Derouiche et al. "Agentic AI Frameworks: Architectures, Protocols, and Design Challenges." 2025. https://arxiv.org/abs/2508.10146
8. Muralidharan et al. "Can Lessons From Human Teams Be Applied to MAS?" 2025. https://arxiv.org/abs/2510.07488
9. Yu. "AdaptOrch: Task-Adaptive Multi-Agent Orchestration." 2026. https://arxiv.org/abs/2602.16873
10. Estornell et al. "How to Train a Leader: Hierarchical Reasoning in Multi-Agent LLMs." 2025. https://arxiv.org/abs/2507.08960
11. Hou et al. "HALO: Hierarchical Autonomous Logic-Oriented Orchestration." 2025. https://arxiv.org/abs/2505.13516
12. Benkovich & Valkov. "Agyn: Team-Based Autonomous Software Engineering." 2026. https://arxiv.org/abs/2602.01465
13. Jardine. "CTHA: Constrained Temporal Hierarchical Architecture." 2026. https://arxiv.org/abs/2601.10738
14. Jiang et al. "Lemon Agent Technical Report." 2026. https://arxiv.org/abs/2602.07092
15. Jimenez-Romero et al. "Multi-Agent Systems Powered by LLMs: Applications in Swarm Intelligence." 2025. https://arxiv.org/abs/2503.03800
16. Mamie & Rao. "The Society of HiveMind." 2025. https://arxiv.org/abs/2503.05473
17. Rahman et al. "LLM-Powered Swarms: A New Frontier or a Conceptual Stretch?" 2025. https://arxiv.org/abs/2506.14496
18. Li et al. "SwarmSys: Decentralized Swarm-Inspired Agents." 2025. https://arxiv.org/abs/2510.10047
19. Zhang et al. "SwarmAgentic: Fully Automated Agentic System Generation via Swarm Intelligence." 2025. https://arxiv.org/abs/2506.15672
20. Zhu et al. "Swarm Intelligence Enhanced Reasoning (SIER)." 2025. https://arxiv.org/abs/2505.17115
21. Ruan et al. "Benchmarking LLMs' Swarm Intelligence (SwarmBench)." 2025. https://arxiv.org/abs/2505.04364
22. Rodriguez. "Emergent Coordination via Pressure Fields and Temporal Decay." 2026. https://arxiv.org/abs/2601.08129
23. Wang et al. "Swarms of LLM Agents for Protein Sequence Design." 2025. https://arxiv.org/abs/2511.22311
24. Liu. "Multi-Agent Collaboration in Incident Response with LLMs." 2024. https://arxiv.org/abs/2412.00652
25. "A Taxonomy of Hierarchical Multi-Agent Systems." 2025. https://arxiv.org/abs/2508.12683
26. Li et al. "Learn as Individuals, Evolve as a Team." 2025. https://arxiv.org/abs/2506.07232
27. Sabbatella. "MALBO: Optimizing LLM-Based Multi-Agent Teams via Bayesian Optimization." 2025. https://arxiv.org/abs/2511.11788
28. Furuya & Kitagawa. "The Geometry of Dialogue: Graphing Language Models for Multi-Agent Teams." 2025. https://arxiv.org/abs/2510.26352
29. Wan et al. "ReMA: Learning to Meta-think for LLMs with Multi-Agent RL." 2025. https://arxiv.org/abs/2503.09501
30. Bilal et al. "Meta-Thinking in LLMs via Multi-Agent RL: A Survey." 2025. https://arxiv.org/abs/2504.14520
31. Song et al. "LLM Agent Swarm for Hypothesis-Driven Drug Discovery." 2025. https://arxiv.org/abs/2504.17967
32. Jin et al. "A Comprehensive Survey on Multi-Agent Cooperative Decision-Making." 2025. https://arxiv.org/abs/2503.13415

### Industry Blog Posts and Documentation

33. Anthropic. "Building Effective Agents." 2024. https://www.anthropic.com/research/building-effective-agents
34. Anthropic. "How We Built Our Multi-Agent Research System." 2025. https://www.anthropic.com/engineering/multi-agent-research-system
35. alexop.dev. "From Tasks to Swarms: Agent Teams in Claude Code." 2025. https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/
36. Softmax Data. "Agent Swarm vs Anthropic Workflows vs LangGraph." 2025. https://blog.softmaxdata.com/agent-architectures-compared/
37. Langfuse. "Comparing Open-Source AI Agent Frameworks." 2025. https://langfuse.com/blog/2025-03-19-ai-agent-comparison
38. Swarms Documentation. "Multi-Agent Architectures." https://docs.swarms.world/en/latest/swarms/concept/swarm_architectures/
39. Swarms Documentation. "How to Choose Swarms." https://docs.swarms.world/en/latest/swarms/concept/how_to_choose_swarms/
40. Arize AI. "Comparing OpenAI Swarm with other Multi-Agent Frameworks." https://arize.com/blog/comparing-openai-swarm
41. Devels.ai. "OpenAI Swarm vs LangGraph vs AutoGen vs CrewAI." https://www.devels.ai/en/blog/openai-swarm-vs-langgraph-vs-autogen-vs-crewai-which-ai-agent-framework-wins
42. DEV Community. "The Great AI Agent Showdown of 2026." https://dev.to/topuzas/the-great-ai-agent-showdown-of-2026-openai-autogen-crewai-or-langgraph-1ea8
43. AI21. "What is Agent Swarm?" https://www.ai21.com/glossary/foundational-llm/agent-swarm/
44. Augment Code. "What Is Agentic Swarm Coding?" https://www.augmentcode.com/guides/what-is-agentic-swarm-coding-definition-architecture-and-use-cases
45. ODSC. "Agent Swarms vs. Agent Hierarchies: When to Use Which." https://odsc.ai/speakers-portfolio/agent-swarms-vs-agent-hierarchies-when-to-use-which-multi-agent-architecture/

---

## Appendix: Key Figures and Frameworks at a Glance

### The Spectrum of Multi-Agent Coordination

```
CENTRALIZED                                              DECENTRALIZED
     |                                                        |
Single    Prompt    Routing  Orchestrator-  Agent    Swarm    Emergent
Agent     Chain              Workers        Teams             Coordination
     |        |        |         |            |        |         |
  Simple   Sequential  Fan-out  Dynamic    Role-based  Self-    Pressure
  prompt   pipeline    dispatch  decomp     parallel   organizing  fields

  Control: HIGH  =================================>  Control: LOW
  Emergence: LOW =================================>  Emergence: HIGH
  Cost: LOW      =================================>  Cost: HIGH
  Predictability: HIGH ===========================>  Predictability: LOW
```

### Architecture Selection Flowchart

```
START: Do you need multi-agent at all?
  |
  +-- Can a single well-prompted agent solve it? --> YES --> Use single agent
  |
  +-- NO: Is the task decomposable?
       |
       +-- Into sequential steps? --> Prompt Chaining
       |
       +-- Into parallel independent subtasks? --> Parallelization / Concurrent Workers
       |
       +-- Into dynamic subtasks (unknown until runtime)? --> Orchestrator-Workers
       |
       +-- Requires iterative refinement? --> Evaluator-Optimizer
       |
       +-- Requires diverse perspectives converging? --> Debate / Voting / MoA
       |
       +-- Massive search space, exploration-heavy?
            |
            +-- Need resilience, no central bottleneck? --> Swarm / Decentralized
            |
            +-- Need quality control + exploration? --> Hybrid (hierarchical + swarm)
```
