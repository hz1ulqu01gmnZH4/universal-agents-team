# Multi-Agent Orchestration Patterns for LLM-Based Systems: Literature Review (2024-2026)

**Date**: 2026-02-28
**Papers Reviewed**: ~65 papers across 8 topic areas
**Sources**: arXiv (primary), Google Scholar (unavailable during search)
**Focus**: Practical implementations and concrete architectural patterns

---

## Table of Contents

1. [Field Overview](#1-field-overview)
2. [Agent-to-Agent Communication Patterns](#2-agent-to-agent-communication-patterns)
3. [Topology Routing: Hierarchical vs Flat vs Dynamic](#3-topology-routing)
4. [Agent Spawning and Lifecycle Management](#4-agent-spawning-and-lifecycle-management)
5. [Task Decomposition and Delegation](#5-task-decomposition-and-delegation)
6. [Review and Verification Patterns](#6-review-and-verification-patterns)
7. [Backpressure, Flow Control, and Token Efficiency](#7-backpressure-flow-control-and-token-efficiency)
8. [State Sharing vs Message Passing](#8-state-sharing-vs-message-passing)
9. [Prompt Engineering for Orchestrator Agents](#9-prompt-engineering-for-orchestrator-agents)
10. [Framework Comparison: CrewAI, AutoGen, LangGraph](#10-framework-comparison)
11. [Why Multi-Agent Systems Fail](#11-why-multi-agent-systems-fail)
12. [Key Findings and Design Principles](#12-key-findings-and-design-principles)
13. [Gaps and Opportunities](#13-gaps-and-opportunities)
14. [Citation Recommendations](#14-citation-recommendations)

---

## 1. Field Overview

The period 2024-2026 has seen an explosion of research on multi-agent LLM systems, driven by the convergence of frontier model capabilities across providers. A fundamental insight from this period is that **orchestration topology now dominates system-level performance over individual model capability** (AdaptOrch, Yu 2026). As LLMs from OpenAI, Anthropic, Google, and xAI converge toward comparable benchmark performance, the marginal return from switching models diminishes while the return from better orchestration design increases dramatically (12-23% improvement from topology alone).

The field has matured through several phases:
- **2024**: Framework proliferation (AutoGen, CrewAI, LangGraph establishing themselves), initial multi-agent debate papers
- **2025 H1**: Dynamic topology research, failure taxonomy development, resource-aware systems
- **2025 H2**: Information-flow orchestration, formal verification of agent systems, hierarchical memory management
- **2026 Q1**: Convergence on hybrid topologies, RL-optimized agent coordination, formal agent lifecycle standards

**Critical finding**: A large-scale empirical study of 1600+ annotated failure traces across 7 MAS frameworks (MAST, Cemri et al. 2025) found that multi-agent systems fail in three fundamental ways: (i) system design issues, (ii) inter-agent misalignment, and (iii) task verification failures. These categories encompass 14 unique failure modes and directly inform the architectural patterns below.

---

## 2. Agent-to-Agent Communication Patterns

### 2.1 Workflow-Based (Rule-Driven) Communication

Traditional approach used by most frameworks where human engineers enumerate task states and specify routing rules in advance. Essentially rule-based decision trees.

**Limitations** (CORAL, Ren et al. 2026):
- Requires substantial manual effort to anticipate and encode possible task states
- Cannot exhaustively cover the state space of complex real-world tasks
- Fragile to edge cases

**Example Frameworks**: OWL, most CrewAI/LangGraph deployments

### 2.2 Information-Flow Orchestrated Communication (CORAL)

**Paper**: "Beyond Rule-Based Workflows: An Information-Flow-Orchestrated Multi-Agents Paradigm via A2A Communication" (Ren et al., 2026) [2601.09883]

**Architecture**: A dedicated information flow orchestrator continuously monitors task progress and dynamically coordinates agents through an Agent-to-Agent (A2A) toolkit using natural language, without relying on predefined workflows.

**Key Pattern**:
```
[Information Flow Orchestrator]
    |--- monitors task progress continuously
    |--- coordinates agents via A2A toolkit
    |--- uses natural language for coordination
    |--- no predefined workflow required

Agents communicate through:
    A2A Toolkit --> natural language messages
    Orchestrator --> dynamic routing decisions
```

**Results**: GAIA benchmark pass@1: 63.64% vs OWL's 55.15% (+8.49pp) with comparable token consumption.

**Key Insight**: Dynamic coordination through A2A communication outperforms static routing, especially for edge cases.

### 2.3 Semi-Centralized A2A Communication (Anemoi)

**Paper**: "Anemoi: A Semi-Centralized Multi-Agent System Based on A2A Communication MCP server" (Ren et al., 2025) [2508.17068]

**Architecture**: Unlike traditional centralized designs where a planner coordinates workers through unidirectional prompt passing, Anemoi enables structured and direct inter-agent collaboration. All agents can:
- Monitor progress
- Assess results
- Identify bottlenecks
- Propose refinements in real time

**Results**: 52.73% accuracy with GPT-4.1-mini as planner, surpassing OWL (43.63%) by +9.09% under identical settings.

**Key Insight**: Reducing reliance on a single planner through A2A communication makes systems more robust when using smaller/cheaper planner models.

### 2.4 Typed Protocol Communication (Gradientsys)

**Paper**: "Gradientsys: A Multi-Agent LLM Scheduler with ReAct Orchestration" (Song et al., 2025) [2507.06520]

**Architecture**: Uses a typed Model-Context Protocol (MCP) for agent coordination with:
- LLM-powered scheduler for one-to-many task dispatch
- Hybrid synchronous/asynchronous execution
- Agent capacity constraints respected
- Retry-and-replan mechanism for failures
- Observability layer with Server-Sent Events (SSE)

### 2.5 Layered Protocol Architecture (Internet of Agents)

**Paper**: "A Layered Protocol Architecture for the Internet of Agents" (Fleming et al., 2025) [2511.19699]

**Proposes two new protocol layers**:
- **Agent Communication Layer (L8)**: Formalizes message structure -- envelopes, speech-act performatives (REQUEST, INFORM), interaction patterns (request-reply, publish-subscribe)
- **Agent Semantic Layer (L9)**: Handles semantic context discovery, semantic grounding, semantic validation, and introduces primitives for coordination and consensus

**Key Insight**: Current network stacks (OSI/TCP/IP) were designed for data delivery, not agent collaboration. Agent systems need semantic-aware communication layers.

---

## 3. Topology Routing

### 3.1 Four Canonical Topologies (AdaptOrch)

**Paper**: "AdaptOrch: Task-Adaptive Multi-Agent Orchestration in the Era of LLM Performance Convergence" (Yu, 2026) [2602.16873]

**The four topologies**:

| Topology | When to Use | Pros | Cons |
|----------|------------|------|------|
| **Parallel** | Independent subtasks, embarrassingly parallel work | Maximum throughput, low latency | No inter-agent information sharing |
| **Sequential** | Dependent tasks, pipeline processing | Clear information flow, easy debugging | Latency proportional to chain length |
| **Hierarchical** | Complex tasks needing strategic decomposition | Good for mixed-complexity tasks, scalable | Single point of failure at supervisor |
| **Hybrid** | Complex real-world tasks with mixed dependencies | Best of all worlds | Most complex to implement |

**Three Key Contributions**:

1. **Performance Convergence Scaling Law**: Formalizes when orchestration selection outweighs model selection. As model capabilities converge, topology choice becomes the dominant factor.

2. **Topology Routing Algorithm**: Maps task decomposition DAGs to optimal orchestration patterns in O(|V| + |E|) time.

3. **Adaptive Synthesis Protocol**: Provable termination guarantees and heuristic consistency scoring for merging parallel agent outputs.

**Results**: 12-23% improvement over static single-topology baselines on SWE-bench, GPQA, and RAG tasks, even with identical underlying models.

### 3.2 Intra-Node Mixtures + Inter-Node Topology (HieraMAS)

**Paper**: "HieraMAS: Optimizing Intra-Node LLM Mixtures and Inter-Node Topology for Multi-Agent Systems" (Yao et al., 2026) [2602.20229]

**Architecture**: Introduces "supernodes" where each functional role is implemented by multiple heterogeneous LLMs using a propose-synthesis structure.

```
Supernode (Role: Code Reviewer)
    |--- LLM-A (proposes review)
    |--- LLM-B (proposes review)
    |--- LLM-C (proposes review)
    |--- Synthesizer (merges proposals)
```

**Two-Stage Optimization**:
1. **Multi-level Reward Attribution**: Fine-grained feedback at both node level and system level (solves the credit assignment problem)
2. **Graph Classification for Topology Selection**: Treats choosing the communication structure as a holistic decision rather than optimizing edges individually

### 3.3 Dynamic Per-Round Topology (DyTopo)

**Paper**: "DyTopo: Dynamic Topology Routing for Multi-Agent Reasoning via Semantic Matching" (Lu et al., 2026) [2602.06039]

**Architecture**: A manager-guided framework that reconstructs a sparse directed communication graph at each reasoning round.

**Need/Offer Mechanism**:
- Each agent outputs lightweight natural-language descriptors:
  - **Need** (query): What information the agent requires
  - **Offer** (key): What information the agent can provide
- DyTopo embeds these descriptors and performs semantic matching
- Messages routed only along induced edges (sparse graph)

**Results**: +6.2% over strongest baseline across code generation and mathematical reasoning benchmarks with 4 LLM backbones.

**Key Insight**: Communication pathways should reconfigure across reasoning rounds, not remain static.

### 3.4 RL-Optimized Topology Evolution (AgentConductor)

**Paper**: "AgentConductor: Topology Evolution for Multi-Agent Competition-Level Code Generation" (Wang et al., 2026) [2602.17100]

**Architecture**: RL-optimized MAS with an LLM-based orchestrator that enables end-to-end feedback-driven dynamic generation of interaction topologies.

**Two Key Innovations**:
1. **Topological Density Function**: Captures communication-aware mathematical characterizations of multi-agent interactions
2. **Difficulty Interval Partitioning**: Avoids excessive pruning for precise density upper bound measurement per difficulty level

**Results**: +14.6% pass@1 accuracy, 13% density reduction, 68% token cost reduction over strongest baseline on competition-level code datasets.

### 3.5 GNN-Designed Topologies (G-Designer)

**Paper**: "G-Designer: Architecting Multi-agent Communication Topologies via Graph Neural Networks" (Zhang et al., 2024) [2410.11782]

**Architecture**: Uses a variational graph auto-encoder to encode agents and a task-specific virtual node, then decodes a task-adaptive communication topology.

**Results**: MMLU 84.50%, HumanEval pass@1 89.90%. Reduces token consumption by up to 95.33% on HumanEval. Adversarially robust with merely 0.3% accuracy drop.

### 3.6 Topology Safety Findings (NetSafe)

**Paper**: "NetSafe: Exploring the Topological Safety of Multi-agent Networks" (Yu et al., 2024) [2410.15686]

**Critical Finding**: Highly connected networks are more susceptible to adversarial attack spread. Star Graph Topology showed 29.7% performance decrease under attack. Networks with greater average distances from attackers exhibit enhanced safety.

**Practical Guidance**: Favor sparse or hierarchical connectivity, maximize attacker-target separation, restrict hub/shortcut pathways via topology-aware access control.

### 3.7 Communication Graph Pruning (M3Prune)

**Paper**: "M3Prune: Hierarchical Communication Graph Pruning for Efficient Multi-Modal Multi-Agent RAG" (Shao et al., 2025) [2511.19969]

**Three-stage pruning**:
1. Intra-modal graph sparsification (text and visual separately)
2. Dynamic communication topology from key edges for inter-modal sparsification
3. Progressive redundant edge pruning for efficient hierarchical topology

**Result**: Outperforms both single-agent and multi-agent baselines while significantly reducing token consumption.

### 3.8 Conformity Dynamics and Topology Effects

**Paper**: "Conformity Dynamics in LLM Multi-Agent Systems: The Roles of Topology and Self-Social Weighting" (Han et al., 2026) [2601.05606]

**Key Findings**:
- Centralized structures enable immediate decisions but are sensitive to hub competence and exhibit same-model alignment biases
- Distributed structures promote more robust consensus
- Increased network connectivity speeds convergence but heightens risk of "wrong-but-sure cascades" (agents converge on incorrect decisions with high confidence)
- Network topology critically governs both efficiency and robustness of collective judgments

---

## 4. Agent Spawning and Lifecycle Management

### 4.1 CEO-Employee Model with Economic Constraints (HASHIRU)

**Paper**: "HASHIRU: Hierarchical Agent System for Hybrid Intelligent Resource Utilization" (Pai et al., 2025) [2506.04255]

**Architecture**:
```
CEO Agent
    |--- Hiring Decision (based on task + resource constraints)
    |       |--- Cost constraint
    |       |--- Memory constraint
    |--- Employee Agents (dynamically instantiated)
    |       |--- Local LLMs prioritized (via Ollama)
    |       |--- API LLMs for overflow
    |--- Firing Decision (with economic firing costs)
    |       |--- Hiring/firing costs promote team stability
```

**Resource-Aware Spawning**:
- Prioritizes smaller local LLMs, escalates to API/larger models only when necessary
- Economic model with hiring/firing costs promotes team stability
- Autonomous tool creation capability
- Memory function for persistent knowledge

**Results**: GSM8K 96% (vs Gemini 2.0 Flash 61%), JEEBench 80% (vs 68.3%), SVAMP 92% (vs 84%)

### 4.2 OS-Inspired Hierarchical Agent Isolation (AgentSys)

**Paper**: "AgentSys: Secure and Dynamic LLM Agents Through Explicit Hierarchical Memory Management" (Wen et al., 2026) [2602.07398]

**Architecture** (inspired by OS process memory isolation):
```
Main Agent
    |--- spawns Worker Agent 1 (isolated context)
    |       |--- spawns Nested Worker (isolated context)
    |       |--- returns schema-validated JSON
    |--- spawns Worker Agent 2 (isolated context)
    |       |--- returns schema-validated JSON
    |--- Only schema-validated return values cross boundaries
    |--- External data NEVER enters main agent's memory
```

**Key Pattern**: External data and subtask traces never enter the main agent's memory; only schema-validated return values cross boundaries through deterministic JSON parsing.

**Security Results**: Isolation alone cuts attack success to 2.19%. With validator/sanitizer: 0.78% (AgentDojo), 4.25% (ASB).

### 4.3 Unified Agent Lifecycle Management (UALM)

**Paper**: "Agentic AI Governance and Lifecycle Management in Healthcare" (Prakash et al., 2026) [2601.15630]

**Five Control-Plane Layers**:
1. **Identity and Persona Registry**: Agent registration, identity management
2. **Orchestration and Cross-Domain Mediation**: Coordination across boundaries
3. **Bounded Context and Memory**: PHI-bounded context management
4. **Runtime Policy Enforcement**: Kill-switch triggers, real-time enforcement
5. **Lifecycle Management and Decommissioning**: Credential revocation, audit logging

### 4.4 Agent-as-a-Service (AaaS-AN)

**Paper**: "Agent-as-a-Service based on Agent Network" (Zhu et al., 2025) [2505.08446]

**Architecture**: Service-oriented paradigm with:
- Dynamic Agent Network where agents self-organize based on task/role dependencies
- Service discovery, registration, and interoperability protocols
- Service Scheduler with Execution Graph for distributed coordination
- Context tracking and runtime task management
- Validated on MAS with 100+ agent services

### 4.5 Trace-Driven Lifecycle Verification (TriCEGAR)

**Paper**: "TriCEGAR: A Trace-Driven Abstraction Mechanism for Agentic AI" (Koohestani et al., 2026) [2601.22997]

**Architecture**: Automates state construction from execution logs, builds abstractions from traces using predicate trees, constructs behavioral MDPs, performs probabilistic model checking for bounds like Pmax(success) and Pmin(failure). Enables anomaly detection as a guardrailing signal.

---

## 5. Task Decomposition and Delegation

### 5.1 Hierarchical Decomposition with Specialized Workers (Project Synapse)

**Paper**: "Project Synapse: A Hierarchical Multi-Agent Framework with Hybrid Memory" (Yadav et al., 2026) [2601.08156]

**Pattern**: Central Resolution Supervisor performs strategic task decomposition and delegates subtasks to specialized worker agents for tactical execution. Orchestrated via LangGraph for cyclical workflows.

### 5.2 Plan-then-Execute (P-t-E) Pattern

**Paper**: "Architecting Resilient LLM Agents: A Guide to Secure Plan-then-Execute Implementations" (Del Rosario et al., 2025) [2509.08646]

**Architecture**:
```
Phase 1: PLANNING
    Planner Agent
        |--- Analyzes task requirements
        |--- Decomposes into subtask DAG
        |--- Assigns resources and tools
        |--- Produces execution plan

Phase 2: EXECUTION
    Executor Agent(s)
        |--- Follows plan
        |--- Uses scoped tool access
        |--- Reports results back

Phase 3: (Optional) RE-PLANNING
    |--- Dynamic re-planning loop if execution fails
    |--- DAG parallel execution for independent subtasks
    |--- Human-in-the-Loop verification checkpoints
```

**Framework Implementations**:
- **LangGraph**: Stateful graphs enabling dynamic re-planning
- **CrewAI**: Declarative tool scoping for security boundaries
- **AutoGen**: Built-in Docker sandboxing for safe code execution

**Security Property**: P-t-E provides inherent resilience to indirect prompt injection by establishing control-flow integrity.

### 5.3 HALO: Hierarchical Three-Level Decomposition

**Paper**: "HALO: Hierarchical Autonomous Logic-Oriented Orchestration for Multi-Agent LLM Systems" (Hou et al., 2025) [2505.13516]

**Architecture**:
```
Level 1: High-level Planning Agent --> Task decomposition
Level 2: Mid-level Role-Design Agents --> Subtask-specific agent instantiation
Level 3: Low-level Inference Agents --> Subtask execution via MCTS

Subtask execution reformulated as structured workflow search:
    Monte Carlo Tree Search explores agentic action space
    Constructs optimal reasoning trajectories
    Adaptive Prompt Refinement transforms raw queries
```

**Results**: 14.4% average improvement over SOTA, up to 19.6% on MATH Algebra.

### 5.4 Expertise Delegation Study

**Paper**: "Towards Multi-Agent Reasoning Systems for Collaborative Expertise Delegation" (Xu et al., 2025) [2505.07313]

**Three Design Dimensions Investigated**:
1. **Expertise-Domain Alignment**: Benefits are highly domain-contingent, most effective for contextual reasoning
2. **Collaboration Paradigm**: Diversity-driven integration consistently outperforms rigid task decomposition
3. **System Scale**: Scaling with specialization has computational tradeoffs; need efficient communication protocols

**Key Finding**: "Collaboration focused on integrating diverse knowledge consistently outperforms rigid task decomposition."

---

## 6. Review and Verification Patterns

### 6.1 Non-Circular Validation (ALAS)

**Paper**: "ALAS: Transactional and Dynamic Multi-Agent LLM Planning" (Geng & Chang, 2025) [2511.03094]

**Architecture**:
```
Planning LLM --> generates plans
    |
Independent Validator --> operates with fresh, bounded context
    |--- NOT the same LLM that planned
    |--- Avoids self-check loops
    |--- Avoids mid-context attrition
    |
Versioned Execution Log --> grounded checks + restore points
    |
Localized Repair Protocol:
    |--- retry, catch, timeout, backoff
    |--- idempotency keys, compensation, loop guards
    |--- Maps to Amazon States Language / Argo Workflows
    |--- Edit only minimal affected region
```

**Results**: 83.7% success, 60% token reduction, 1.82x faster. Validator detects injected structural faults with low overhead.

**Key Insight**: Validator isolation + versioned execution logs + localized repair = measurable efficiency, feasibility, and scalability gains.

### 6.2 Multi-Agent Debate for Verification

Multiple papers establish the multi-agent debate pattern:

**TS-Debate** (Trirat et al., 2026) [2601.19151]:
- Modality-specialized agents (text, visual, numeric) debate claims
- Reviewer agents use verification-conflict-calibration mechanism
- Lightweight code execution for programmatic verification

**Tool-MAD** (Jeong et al., 2026) [2601.04742]:
- Each agent has a distinct external tool (search API, RAG module)
- Adaptive query formulation refines evidence during debate
- Faithfulness and Answer Relevance scores for Judge agent
- +5.5% accuracy over SOTA debate frameworks

**Diversity of Thought** (Hegazy, 2024) [2410.12853]:
- Diverse trained models debate better than homogeneous ones
- 3 diverse medium-capacity models (Gemini-Pro, Mixtral, PaLM 2-M) at 91% beat GPT-4 on GSM-8K after 4 rounds
- 3 identical Gemini-Pro only reach 82%

### 6.3 Coder-Executor-Critic Pattern

**Paper**: "Collaboration Dynamics and Reliability Challenges of Multi-Agent LLM Systems in FEA" (Tian & Zhang, 2024) [2408.13406]

**Critical Findings**:
- **Three-agent Coder-Executor-Critic** uniquely produced correct solutions
- Adding redundant reviewers REDUCED success rates
- **Affirmation bias**: Rebuttal agent endorsed rather than challenged outputs (85-92% agreement, including errors)
- **Premature consensus**: Redundant reviewers triggered early agreement
- **Verification-validation gap**: Executable but physically incorrect code passed undetected

**Design Principles**:
1. Assign complementary agent roles (functional diversity > team size)
2. Enforce multi-level validation (execution + specification + domain physics)
3. Prevent early consensus through adversarial or trigger-based interaction control

### 6.4 D3: Cost-Aware Adversarial Evaluation

**Paper**: "Debate, Deliberate, Decide (D3)" (Harrasse et al., 2024) [2410.04663]

**Two Protocols**:
1. **MORE** (Multi-Advocate One-Round): k parallel defenses per answer for signal amplification
2. **SAMRE** (Single-Advocate Multi-Round): Iterative argument refinement under explicit token budget with convergence checks

**Mathematical Properties**: Posterior distribution of score gaps concentrates around true difference; probability of mis-ranking vanishes with rounds.

### 6.5 Intervention-Driven Debugging (DoVer)

**Paper**: "DoVer: Intervention-Driven Auto Debugging for LLM Multi-Agent Systems" (Ma et al., 2025) [2512.06749]

**Architecture**: Augments hypothesis generation with active verification through targeted interventions (editing messages, altering plans). Flips 18-28% of failed trials into successes on GAIA/AssistantBench. 49% recovery on AG2 framework.

**Key Insight**: Multiple distinct interventions can independently repair a failed task -- single-step attribution is often ill-posed.

---

## 7. Backpressure, Flow Control, and Token Efficiency

### 7.1 Hierarchical Autoscaling with Backpressure (Chiron)

**Paper**: "Hierarchical Autoscaling for Large Language Model Serving with Chiron" (Patke et al., 2025) [2501.08090]

**Architecture**: Uses hierarchical backpressure estimated from queue size, utilization, and SLOs. Divides requests into interactive (tight SLO) vs batch (relaxed SLO).

**Results**: Up to 90% higher SLO attainment, 70% improved GPU efficiency over existing solutions.

### 7.2 Resource-Aware Shortcuts (Co-Saving)

**Paper**: "Co-Saving: Resource Aware Multi-Agent Collaboration for Software Development" (Qiu et al., 2025) [2505.21898]

**Architecture**: Introduces "shortcuts" -- instructional transitions learned from historically successful trajectories -- that bypass redundant reasoning agents.

**Results**: 50.85% reduction in token usage over ChatDev, 10.06% code quality improvement.

**Key Pattern**: Learn which agent interactions are typically redundant from past traces, then skip them.

### 7.3 Dynamic Agent Elimination (AgentDropout)

**Paper**: "AgentDropout: Dynamic Agent Elimination for Token-Efficient and High-Performance LLM-Based Multi-Agent Collaboration" (Wang et al., 2025) [2503.18891]

**Architecture**: Optimizes adjacency matrices of communication graphs to identify and eliminate redundant agents and communication edges across rounds.

**Results**: 21.6% reduction in prompt tokens, 18.4% reduction in completion tokens, +1.14 performance improvement.

### 7.4 Token-Efficient Codified Reasoning (CodeAgents)

**Paper**: "CodeAgents: A Token-Efficient Framework for Codified Multi-Agent Reasoning in LLMs" (Yang et al., 2025) [2507.03254]

**Architecture**: Codifies all agent interaction (Task, Plan, Feedback, roles, tools) into modular pseudocode with control structures, boolean logic, and typed variables.

**Results**: 3-36pp performance gain over NL prompting, 55-87% input token reduction, 41-70% output token reduction.

### 7.5 Selective Debate Triggering (iMAD)

**Paper**: "iMAD: Intelligent Multi-Agent Debate for Efficient and Accurate LLM Inference" (Fan et al., 2025) [2511.11306]

**Architecture**: Selectively triggers multi-agent debate only when likely to be beneficial. Extracts 41 interpretable linguistic/semantic features capturing hesitation cues from single-agent self-critique. Lightweight classifier decides whether to engage debate.

**Results**: Up to 92% token reduction, up to 13.5% accuracy improvement by avoiding unnecessary debate.

### 7.6 Role-Aware Context Routing (RCR-Router)

**Paper**: "RCR-Router: Efficient Role-Aware Context Routing for Multi-Agent LLM Systems with Structured Memory" (Liu et al., 2025) [2508.04903]

**Architecture**: First routing approach that dynamically selects semantically relevant memory subsets for each agent based on role and task stage, adhering to strict token budget.

**Results**: Up to 30% token reduction while maintaining answer quality on HotPotQA, MuSiQue, 2WikiMultihop.

### 7.7 Multi-Objective Team Composition (MALBO)

**Paper**: "MALBO: Optimizing LLM-Based Multi-Agent Teams via Multi-Objective Bayesian Optimization" (Sabbatella, 2025) [2511.11788]

**Architecture**: Formalizes team composition as multi-objective optimization (task accuracy vs inference cost). Uses Bayesian Optimization with Gaussian Process surrogates.

**Results**: 45% average cost reduction, up to 65.8% cost reduction for heterogeneous teams vs homogeneous baselines at maximum performance.

### 7.8 Heterogeneous Collaboration (SC-MAS)

**Paper**: "SC-MAS: Constructing Cost-Efficient Multi-Agent Systems with Edge-Level Heterogeneous Collaboration" (Zhao et al., 2026) [2601.09434]

**Architecture**: Models MAS as directed graphs where edges represent pairwise collaboration strategies. A unified controller progressively constructs executable MAS by selecting roles, assigning edge-level strategies, and allocating LLM backbones.

**Results**: +3.35% accuracy on MMLU with 15.38% cost reduction; +3.53% on MBPP with 12.13% cost reduction.

---

## 8. State Sharing vs Message Passing

### 8.1 Blackboard Architecture for LLM MAS

**Paper**: "Exploring Advanced LLM Multi-Agent Systems Based on Blackboard Architecture" (Han & Zhang, 2025) [2507.01701]

**Architecture**:
```
Shared Blackboard (global state)
    |--- All agents can read/write
    |--- Agents see each other's messages during entire process
    |--- Agent selection based on current blackboard content
    |--- Selection/execution rounds repeat until consensus

Properties:
    + Full information sharing
    + Dynamic agent activation
    + Fewer tokens than alternatives
    - Potential for information overload
    - Security/privacy concerns
```

**Results**: Competitive with SOTA static/dynamic MAS, achieves best average performance while spending fewer tokens.

### 8.2 Blackboard for Data Discovery at Scale

**Paper**: "LLM-Based Multi-Agent Blackboard System for Information Discovery" (Salemi et al., 2025) [2510.01285]

**Architecture**: Central agent posts requests to shared blackboard. Autonomous subordinate agents (data lake partitions or web retrievers) volunteer to respond based on capabilities.

**Key Advantage**: Removes need for central coordinator to know each agent's expertise. Improves scalability and flexibility.

**Results**: 13-57% relative improvement in end-to-end success, up to 9% data discovery F1 gain.

### 8.3 Shared Blackboard for Multi-Robot Coordination

**Paper**: "H-AIM: Orchestrating LLMs, PDDL, and Behavior Trees for Hierarchical Multi-Robot Planning" (Zeng & Li, 2026) [2601.11063]

**Pattern**: Shared blackboard mechanism for communication and state synchronization across dynamically-sized heterogeneous robot teams. Supports behavior tree compilation for reactive control.

### 8.4 Centralized Versioned Learner State

**Paper**: "IntelliCode: A Multi-Agent LLM Tutoring System with Centralized Learner Modeling" (David & Ghosh, 2025) [2512.18669]

**Architecture**: StateGraph Orchestrator coordinates six specialized agents, all operating as pure transformations over a shared versioned state under a single-writer policy. Enables auditable updates and state tracking.

### 8.5 Modular Procedural Memory (LEGOMem)

**Paper**: "LEGOMem: Modular Procedural Memory for Multi-Agent LLM Systems for Workflow Automation" (Han et al., 2025) [2510.04851]

**Key Findings**:
- **Orchestrator memory is critical** for effective task decomposition and delegation
- **Fine-grained agent memory** improves execution accuracy
- Even smaller models benefit substantially from procedural memory, narrowing the gap with stronger agents

**Architecture**: Decomposes past task trajectories into reusable memory units, flexibly allocates across orchestrators and task agents.

### 8.6 Latent Memory with Policy Optimization (LatentMem)

**Paper**: "LatentMem: Customizing Latent Memory for Multi-Agent Systems" (Fu et al., 2026) [2602.03036]

**Architecture**: Addresses memory homogenization and information overload with:
- Experience bank storing raw trajectories in lightweight form
- Memory composer synthesizing compact latent memories conditioned on agent-specific contexts
- Latent Memory Policy Optimization (LMPO) propagating task-level signals through latent memories

**Results**: Up to 19.36% performance gain over vanilla settings.

### 8.7 State Sharing Pattern Comparison

| Pattern | Information Sharing | Token Efficiency | Security | Scalability |
|---------|-------------------|-----------------|----------|-------------|
| **Blackboard** (shared state) | Full visibility | Moderate (all read all) | Low (no isolation) | Moderate |
| **Message passing** (A2A) | Selective | High (targeted messages) | High (boundaries) | High |
| **Shared memory + single writer** | Controlled writes | Moderate | Medium | Medium |
| **Schema-validated returns** (AgentSys) | Minimal necessary | Very high | Very high | High |
| **Latent memory** (LatentMem) | Role-customized | Very high | High | High |

---

## 9. Prompt Engineering for Orchestrator Agents

### 9.1 Dynamic Prompt Engineering

**Paper**: "Dynamic Multi-Agent Orchestration and Retrieval" (Seabra et al., 2024) [2412.17964]

**Pattern**: Adapts prompts in real time to query-specific contexts. Router agents dynamically select retrieval strategy (SQL agent, RAG agent) based on query nature.

### 9.2 Adaptive Prompt Refinement (HALO)

**Paper**: HALO (Hou et al., 2025) [2505.13516]

**Pattern**: Since most users lack expertise in prompt engineering, HALO transforms raw queries into task-specific prompts automatically before routing to agents.

### 9.3 Codified Multi-Agent Prompting (CodeAgents)

**Paper**: CodeAgents (Yang et al., 2025) [2507.03254]

**Pattern**: All agent interactions codified into modular pseudocode:
```python
# Instead of natural language:
TASK(agent_role="researcher", tools=["arxiv_search", "web_fetch"])
PLAN {
    STEP_1: search_papers(query=task.keywords, max=20)
    IF results.count < 5:
        STEP_2: broaden_search(relax_constraints=True)
    STEP_3: FOR paper IN results:
        extract_findings(paper)
    STEP_4: synthesize(findings, format="structured_review")
}
FEEDBACK(validator_role="reviewer", check=["completeness", "accuracy"])
```

**Key Benefit**: 55-87% input token reduction vs natural language prompts.

### 9.4 Orchestrator-Specialist Architecture

**Paper**: "Orchestrator Multi-Agent Clinical Decision Support System" (Wu et al., 2025) [2512.04207]

**Pattern**: Central orchestrator performs task decomposition and coordinates agent routing to domain-specialized agents. Each specialist produces structured, evidence-grounded rationale.

**Finding**: Orchestrated multi-agent with guideline-based prompting consistently achieved highest F1, with larger gains in smaller models. "Structured multi-agent reasoning improves accuracy beyond prompt engineering alone."

### 9.5 ReAct-Style Orchestration

**Paper**: "Agentic AI Empowered Intent-Based Networking for 6G" (Jiang et al., 2026) [2601.06640]

**Pattern**: Orchestrator agent uses ReAct-style reasoning (Reason-Action cycles) to coordinate specialist agents. Grounded in structured state representations.

**Finding**: Careful prompt engineering required to encode context-dependent decision thresholds for network automation.

---

## 10. Framework Comparison

### 10.1 Comprehensive Framework Analysis

**Paper**: "Agentic AI Frameworks: Architectures, Protocols, and Design Challenges" (Derouiche et al., 2025) [2508.10146]

| Framework | Architecture | Communication | Memory | Key Feature |
|-----------|-------------|---------------|--------|-------------|
| **CrewAI** | Role-based crews | Declarative tool scoping | Task-scoped | Simple role assignment, security-focused |
| **LangGraph** | Stateful graph | Graph-based state transitions | Checkpoint/persist | Dynamic re-planning, state management |
| **AutoGen** | Conversational agents | Group chat / nested chat | Conversation history | Docker sandboxing, flexible chat patterns |
| **Semantic Kernel** | Plugin-based | Function calling | Kernel memory | Microsoft ecosystem integration |
| **Agno** | Lightweight agents | Function-first | Configurable | Minimal overhead |
| **Google ADK** | Agent Development Kit | Tool-first | Cloud-integrated | Google Cloud native |
| **MetaGPT** | SOP-driven roles | Standardized outputs | Shared environment | Software engineering focus |

**Communication Protocols**:
- **Contract Net Protocol (CNP)**: Manager announces task, contractors bid, manager awards
- **Agent-to-Agent (A2A)**: Google's protocol for inter-agent communication
- **Agent Network Protocol (ANP)**: Decentralized agent discovery and messaging
- **Agora**: Open marketplace for agent services

### 10.2 Bug Patterns in Frameworks

**Paper**: "An Empirical Study of Bugs in Modern LLM Agent Frameworks" (Zhu et al., 2026) [2602.21806]

**998 bug reports analyzed from CrewAI and LangChain**:
- 15 root causes, 7 observable symptoms, 5 lifecycle stages
- Top root causes: API misuse, API incompatibility, Documentation Desync
- Bugs concentrated in "Self-Action" stage
- Top symptoms: Functional Error, Crash, Build Failure

### 10.3 Framework-Agnostic Specification (Agent Spec)

**Paper**: "Open Agent Specification: A Unified Representation for AI Agents" (Amini et al., 2025) [2510.04173]

**Architecture**: Declarative language defining agents compatible across LangGraph, CrewAI, AutoGen, and WayFlow. Standardized evaluation harness (like HELM for LLMs but for agents).

### 10.4 Benchmark Comparison (REALM-Bench)

**Paper**: "REALM-Bench: A Benchmark for Evaluating Multi-Agent Systems" (Geng & Chang, 2025) [2502.18836]

**Tests**: 14 planning/scheduling problems with LangGraph, AutoGen, CrewAI, and Swarm using GPT-4o, Claude-3.7, DeepSeek-R1.

### 10.5 Large-Scale Development Study

**Paper**: "A Large-Scale Study on the Development and Issues of Multi-Agent AI Systems" (Liu et al., 2026) [2601.07136]

**42K+ commits, 4.7K+ resolved issues across 8 leading systems**:
- Three development profiles: sustained, steady, burst-driven
- 40.8% perfective commits (feature enhancement prioritized)
- 27.4% corrective, 24.3% adaptive
- Most frequent issues: bugs (22%), infrastructure (14%), agent coordination (10%)
- Median resolution: <1 day to ~2 weeks

---

## 11. Why Multi-Agent Systems Fail

### 11.1 MAST Failure Taxonomy

**Paper**: "Why Do Multi-Agent LLM Systems Fail?" (Cemri et al., 2025) [2503.13657]

**3 Categories, 14 Failure Modes** (from 1600+ annotated traces across 7 frameworks):

**Category 1: System Design Issues**
- Poor role specification
- Inadequate tool access
- Missing error recovery
- Suboptimal communication structure

**Category 2: Inter-Agent Misalignment**
- Conflicting interpretations
- Information loss in handoffs
- Affirmation bias (agents agree with errors)
- Redundant/circular communication

**Category 3: Task Verification**
- Missing verification steps
- Incorrect success criteria
- Self-verification loops (circular checking)
- Premature task completion claims

**Key Finding**: "Identified failures require more sophisticated solutions" -- simple scaling of agents does not resolve fundamental design issues.

### 11.2 Affirmation Bias and Premature Consensus

**Paper**: Tian & Zhang (2024) [2408.13406]

- Rebuttal agents endorse rather than challenge (85-92% agreement rate including on errors)
- Adding reviewers paradoxically reduces success
- Functional complementarity matters more than team size

### 11.3 Memory Leakage by Topology

**Paper**: "Topology Matters: Measuring Memory Leakage in Multi-Agent LLMs" (Liu et al., 2025) [2512.04668]

**MAMA Framework** findings:
- Denser connectivity = more information leakage
- Shorter attacker-target distance = more leakage
- Higher target centrality = more leakage
- Most leakage occurs in early rounds then plateaus
- Model choice shifts absolute rates but preserves topology ordering

---

## 12. Key Findings and Design Principles

### Principle 1: Topology is the First-Class Optimization Target
Orchestration topology achieves 12-23% gains independent of model choice (AdaptOrch). As models converge in capability, topology becomes the dominant performance factor.

### Principle 2: Dynamic Topology > Static Topology
Systems that reconfigure communication per round (DyTopo +6.2%, AgentConductor +14.6%) consistently outperform fixed topologies. Use semantic matching of need/offer descriptors to route communication.

### Principle 3: Functional Complementarity > Team Size
The Coder-Executor-Critic triplet outperforms larger teams. Adding redundant reviewers causes premature consensus and affirmation bias. Each agent should have a unique, complementary role.

### Principle 4: Separate Planning from Validation
Never let the planning LLM validate its own work (self-check loops). Use independent validators with fresh context (ALAS pattern). Maintain versioned execution logs for grounded verification.

### Principle 5: OS-Style Memory Isolation
Agent spawning should follow OS process isolation: isolated contexts, schema-validated return values only, external data never enters parent agent memory (AgentSys). This provides both security and clarity.

### Principle 6: Resource-Aware Agent Management
Use economic models (hiring/firing costs) for agent lifecycle (HASHIRU). Learn "shortcuts" to bypass redundant agents (Co-Saving, 50% token reduction). Apply selective debate triggering (iMAD, 92% token savings).

### Principle 7: Memory Architecture Matters
Orchestrator memory is critical for task decomposition; agent memory improves execution (LEGOMem). Use role-customized latent memory to avoid homogenization (LatentMem). Blackboard patterns work for full-visibility scenarios but have security tradeoffs.

### Principle 8: Diverse Models > Identical Models in Debate
Heterogeneous model teams in debate settings outperform homogeneous ones (3 diverse medium-capacity models at 91% beat GPT-4 at 82% on GSM-8K). Use model diversity as a design parameter.

### Principle 9: Sparse Communication is Safer and More Efficient
Highly connected networks are more vulnerable to attack propagation (NetSafe). Prune communication graphs hierarchically (M3Prune). Favor sparse topologies with maximum attacker-target separation.

### Principle 10: Codify Agent Interactions
Convert natural language agent interactions to pseudocode with control structures (CodeAgents). This yields 55-87% input token reduction while improving performance by 3-36pp.

---

## 13. Gaps and Opportunities

### Gap 1: No Standard for Agent Lifecycle Events
While UALM and TriCEGAR propose lifecycle models, there is no widely adopted standard for agent birth, health monitoring, graceful degradation, and decommissioning. Agent Spec (2510.04173) is an early attempt.

### Gap 2: Backpressure Mechanisms for Agent Swarms are Underdeveloped
Chiron addresses LLM serving autoscaling, but no paper proposes a comprehensive backpressure mechanism specifically for multi-agent swarms where agents can dynamically adjust their output rate based on downstream capacity.

### Gap 3: Self-Evolving Topology Selection
While SEMAS (2602.16738) demonstrates self-evolving agents for IoT, no paper yet shows fully autonomous topology evolution based on performance feedback in a general-purpose setting. AgentConductor uses RL but requires pre-training.

### Gap 4: Cross-Framework Agent Migration
Agent Spec proposes portability, but live migration of agents between frameworks (with state preservation) during execution remains unaddressed.

### Gap 5: Formal Verification of Multi-Agent Safety Properties
While TriCEGAR and MAMA provide initial tools, formal verification of safety properties (no agent can cause unbounded resource consumption, no circular delegation, guaranteed termination) remains immature.

### Gap 6: Context Compression Across Agent Boundaries
How to efficiently compress context when passing information between agents, especially in deep hierarchies, is understudied. RCR-Router addresses this partially with role-aware context routing.

---

## 14. Citation Recommendations

### Must Cite (Foundational)

1. **AdaptOrch** (Yu, 2026) [2602.16873] -- Defines topology as first-class optimization target, 12-23% gains
2. **MAST** (Cemri et al., 2025) [2503.13657] -- 14 failure modes across 7 frameworks, 1600+ traces
3. **CORAL** (Ren et al., 2026) [2601.09883] -- Information-flow orchestration replacing workflow-based MAS
4. **G-Designer** (Zhang et al., 2024) [2410.11782] -- GNN-based topology design, 95% token reduction
5. **AutoGen Studio** (Dibia et al., 2024) [2408.15247] -- Foundational multi-agent framework paper

### Should Cite (Directly Relevant)

6. **HieraMAS** (Yao et al., 2026) [2602.20229] -- Intra-node LLM mixtures + inter-node topology
7. **DyTopo** (Lu et al., 2026) [2602.06039] -- Per-round dynamic topology via semantic matching
8. **AgentConductor** (Wang et al., 2026) [2602.17100] -- RL-optimized topology evolution, +14.6%
9. **ALAS** (Geng & Chang, 2025) [2511.03094] -- Non-circular validation, versioned execution
10. **Co-Saving** (Qiu et al., 2025) [2505.21898] -- Resource-aware shortcuts, 50% token reduction
11. **AgentSys** (Wen et al., 2026) [2602.07398] -- OS-inspired hierarchical memory isolation
12. **HASHIRU** (Pai et al., 2025) [2506.04255] -- CEO-employee resource-aware spawning
13. **LEGOMem** (Han et al., 2025) [2510.04851] -- Modular procedural memory placement
14. **AgentDropout** (Wang et al., 2025) [2503.18891] -- Dynamic agent elimination for efficiency
15. **CodeAgents** (Yang et al., 2025) [2507.03254] -- Token-efficient codified reasoning
16. **Tian & Zhang** (2024) [2408.13406] -- Affirmation bias, premature consensus findings
17. **Agentic AI Frameworks** (Derouiche et al., 2025) [2508.10146] -- Framework comparison survey

### Consider Citing (Context)

18. **NetSafe** (Yu et al., 2024) [2410.15686] -- Topological safety
19. **TodyComm** (Fan et al., 2026) [2602.03688] -- Task-oriented dynamic communication
20. **Blackboard MAS** (Han & Zhang, 2025) [2507.01701] -- Blackboard pattern for LLM MAS
21. **LatentMem** (Fu et al., 2026) [2602.03036] -- Latent memory customization
22. **P-t-E Guide** (Del Rosario et al., 2025) [2509.08646] -- Plan-then-Execute implementation guide
23. **HALO** (Hou et al., 2025) [2505.13516] -- Hierarchical orchestration with MCTS
24. **Agent Spec** (Amini et al., 2025) [2510.04173] -- Cross-framework agent specification
25. **SC-MAS** (Zhao et al., 2026) [2601.09434] -- Cost-efficient heterogeneous collaboration
26. **Bugs in Frameworks** (Zhu et al., 2026) [2602.21806] -- 998 bugs in CrewAI/LangChain
27. **Development Study** (Liu et al., 2026) [2601.07136] -- 42K commits across 8 MAS frameworks
28. **MALBO** (Sabbatella, 2025) [2511.11788] -- Bayesian optimization for team composition
29. **iMAD** (Fan et al., 2025) [2511.11306] -- Selective debate triggering
30. **Diversity of Thought** (Hegazy, 2024) [2410.12853] -- Model diversity in debate

---

## Appendix: Concrete Architectural Patterns for Implementation

### Pattern A: Topology-Adaptive Orchestrator

```
class TopologyRouter:
    topologies = [PARALLEL, SEQUENTIAL, HIERARCHICAL, HYBRID]

    def route(task: TaskDAG) -> Topology:
        # AdaptOrch algorithm: O(|V|+|E|)
        dependencies = analyze_dependencies(task)
        parallelizable = find_independent_subtasks(task)

        if all_independent(dependencies):
            return PARALLEL
        elif is_linear_chain(dependencies):
            return SEQUENTIAL
        elif has_supervisor_workers(dependencies):
            return HIERARCHICAL
        else:
            return HYBRID  # mix of above
```

### Pattern B: Agent Lifecycle Manager

```
class AgentLifecycleManager:
    # HASHIRU-inspired CEO-Employee model
    def spawn_agent(task, budget):
        cost = estimate_cost(task)
        if cost > budget.remaining:
            return hire_local_llm(task)  # cheaper
        else:
            return hire_api_agent(task)

    def should_fire(agent):
        # Economic model: firing cost vs keeping cost
        return (agent.idle_time * keep_cost) > firing_cost

    # AgentSys-inspired isolation
    def execute_subtask(parent, subtask):
        worker = spawn_isolated_worker(subtask)
        result = worker.execute()  # isolated context
        validated = schema_validate(result)  # JSON only
        return validated  # never raw external data
```

### Pattern C: Non-Circular Validation

```
class ValidationPipeline:
    # ALAS-inspired
    def validate(plan, execution_log):
        validator = create_fresh_validator()  # independent LLM
        validator.context = bounded_context(execution_log.latest_version)
        # NOT the planning LLM's context

        result = validator.check(plan)
        if result.failed:
            repair = localized_repair(
                execution_log,
                failure_point=result.failure_location,
                policies=[RETRY, BACKOFF, IDEMPOTENCY, COMPENSATE]
            )
            return repair
        return result
```

### Pattern D: Dynamic Communication Graph

```
class DynamicTopology:
    # DyTopo-inspired need/offer matching
    def build_round_graph(agents, round_goal):
        needs = {a: a.describe_needs(round_goal) for a in agents}
        offers = {a: a.describe_offers(round_goal) for a in agents}

        need_embeddings = embed(needs)
        offer_embeddings = embed(offers)

        graph = SparseDirectedGraph()
        for sender in agents:
            for receiver in agents:
                if sender != receiver:
                    score = cosine_sim(
                        offer_embeddings[sender],
                        need_embeddings[receiver]
                    )
                    if score > threshold:
                        graph.add_edge(sender, receiver)
        return graph
```

### Pattern E: Resource-Aware Communication Pruning

```
class CommunicationPruner:
    # AgentDropout + M3Prune inspired
    def prune(graph, token_budget):
        # Score each edge by importance
        for edge in graph.edges:
            edge.score = compute_importance(
                sender=edge.source,
                receiver=edge.target,
                task_state=current_state
            )

        # Remove lowest-scoring edges until within budget
        sorted_edges = sort_by_score(graph.edges)
        while estimated_tokens(graph) > token_budget:
            graph.remove_edge(sorted_edges.pop_lowest())

        return graph
```

---

*End of Literature Review*
