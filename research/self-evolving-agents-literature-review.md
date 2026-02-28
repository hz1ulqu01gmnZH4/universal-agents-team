# Self-Evolving AI Agents: Comprehensive Literature Review

**Date:** 2026-02-25
**Scope:** Academic papers (2023-2026), open-source implementations, industry practice
**Focus:** Systems where agents autonomously improve their own instructions, processes, roles, or architectures

---

## Executive Summary

The field of self-evolving agents has undergone a Cambrian explosion between 2024 and 2026. Three distinct clusters of work have emerged: (1) single-agent iterative refinement methods (Reflexion, Self-Refine, TextGrad, Godel Agent), (2) multi-agent structural self-modification (EvoMAC, CoMAS, ADAS/Meta Agent Search, EvoAgentX), and (3) full open-ended evolutionary systems (Darwin Godel Machine, Group-Evolving Agents). Two comprehensive surveys (Fang et al. 2025 with 64 citations; Gao et al. 2025) now provide taxonomies for the entire space.

The most critical gap for our use case -- a hierarchical multi-agent organization (PI/Director + specialists) that evolves its own process rules, role definitions, and coordination norms incident-by-incident -- is only partially addressed. Most work focuses on task-level performance, not organizational knowledge (SOPs, role charters, escalation policies). This is the design space we occupy.

---

## Category 1: Foundational Single-Agent Self-Improvement Patterns

These form the building blocks that later multi-agent systems extend.

### 1.1 Reflexion (Shinn et al., NeurIPS 2023)

- **Title:** Reflexion: Language Agents with Verbal Reinforcement Learning
- **Authors:** Noah Shinn, Federico Cassano, Ashwin Gopinath, Karthik Narasimhan, Shunyu Yao
- **Source:** arXiv 2303.11366; NeurIPS 2023; **3,599 citations**
- **Core idea:** Reinforce language agents not by updating weights but through linguistic feedback. After each episode, the agent reflects in natural language on what went wrong and stores the reflection in an episodic memory buffer. Future rollouts are conditioned on that buffer.
- **Methodology:** Three-agent loop: Actor (executes), Evaluator (scores), Self-Reflection (generates verbal gradient). The self-reflection text is prepended to future prompts.
- **Key results:** 91% pass@1 on HumanEval (vs. GPT-4 baseline 80%); significant gains on AlfWorld (sequential decision-making) and HotPotQA.
- **Relevance:** Direct ancestor of all "learn from failure via self-critique" approaches. Closest analog to our incident-postmortem loop: the agent reviews its own failure and writes a new process note. The limitation is it operates within a single task episode, not accumulating org-level policy.

### 1.2 Self-Refine (Madaan et al., NeurIPS 2023)

- **Title:** Self-Refine: Iterative Refinement with Self-Feedback
- **Authors:** Aman Madaan, Niket Tandon, Prakhar Gupta et al.
- **Source:** NeurIPS 2023; **3,328 citations**
- **Core idea:** A single model iteratively generates output, critiques it, and revises it in a multi-turn loop using the same LLM for all three steps.
- **Methodology:** Generate -> Feedback -> Refine loop; no gradient updates; no additional model training.
- **Key results:** 20% average improvement over one-shot baselines across 7 diverse generation tasks.
- **Relevance:** Shows that LLMs can usefully self-critique. Our Director/PI role effectively does a "self-refine" on process rules after each sprint/incident.

### 1.3 TextGrad / ProTeGi (Yuksekgonul et al., 2024; Published in Nature)

- **Title:** TextGrad: Automatic "Differentiation" via Text
- **Authors:** Mert Yuksekgonul et al. (Stanford HAI / Zou Group)
- **Source:** arXiv 2406.07496; published in Nature
- **Core idea:** Backpropagation through text: LLMs supply textual "gradients" (natural language feedback on what is wrong and why) that are then used to update upstream prompts or code in a compound AI pipeline. Direct analog of numerical gradient descent, but operating entirely in language space.
- **Methodology:** Forward pass evaluates a pipeline component; backward pass asks an LLM to critique the current prompt/code relative to the objective; the critique ("gradient") is used to rewrite the upstream component.
- **Key results:** GPT-4o on GPQA: 51% -> 55%; LeetCode-Hard solutions: 20% relative gain; drug molecule design improvements.
- **Relevance:** High. This is essentially what happens when our PI agent reads a failing sprint report and rewrites the process rule. TextGrad provides a principled framework for this that could be formalized. EvoAgentX uses TextGrad as one of its optimizer backends.

---

## Category 2: Automated Agent Design (Architecture-Level Self-Modification)

### 2.1 ADAS: Automated Design of Agentic Systems (Hu, Lu, Clune 2024 / ICLR 2025)

- **Title:** Automated Design of Agentic Systems
- **Authors:** Shengran Hu, Cong Lu, Jeff Clune
- **Source:** arXiv 2408.08435; **ICLR 2025**; **302 citations**; open source: github.com/ShengranHu/ADAS
- **Core idea:** A meta-agent searches the space of all possible agentic system designs by iteratively programming new agents in code, maintaining an ever-growing archive of discovered designs (the "archive"). Each new agent is built on top of high-performing previous discoveries.
- **Methodology:**
  1. Agents are expressed as Python code (Turing Complete, so all possible designs are reachable in principle)
  2. A meta-agent (LLM) proposes a new agent design based on the archive
  3. The new agent is evaluated on benchmarks
  4. If it improves, it is added to the archive
  5. Repeat indefinitely
- **Key results:** Meta Agent Search significantly outperforms hand-designed agents across coding, science, and math domains. Discovered agents transfer well across models and domains.
- **Relevance:** Very high as a conceptual model. The "archive of past agent designs" is analogous to our accumulated process rules and role definitions. The meta-agent that proposes new designs is analogous to our PI/Director. Key insight: expressing agent behavior in code (not just prompts) makes the design space Turing Complete. Limitation: requires running many evaluations (expensive).

### 2.2 Godel Agent: Self-Referential Recursive Self-Improvement (Yin et al., 2024 / ACL 2025)

- **Title:** Godel Agent: A Self-Referential Agent Framework for Recursive Self-Improvement
- **Authors:** Xunjian Yin, Xinyi Wang, Liangming Pan, Xiaojun Wan, William Yang Wang
- **Source:** arXiv 2410.04444; **ACL 2025**; **25 citations**; open source: github.com/Arvid-pku/Godel_Agent
- **Core idea:** Inspired by Godel's incompleteness theorems and the theoretical Godel Machine: an agent that can freely decide its own routine, modules, and -- crucially -- the way to update them. It is self-referential: the optimization procedure itself is subject to self-modification.
- **Methodology:** Unlike ADAS (meta-agent outside the loop), Godel Agent has a single self-modifying agent that both executes tasks and autonomously modifies its own code and reasoning procedures via LLM prompting. No fixed optimization algorithm; the agent chooses how to improve itself.
- **Key results:** Matches or exceeds Meta Agent Search (ADAS) across benchmarks; outperforms ADAS on MGSM math by 11%.
- **Relevance:** High. This is a cleaner model of what we want: a PI/Director agent that not only updates the team's process rules, but also updates the way it decides to update them (meta-meta-learning). Limitation: less interpretable than ADAS since no explicit archive.

### 2.3 Darwin Godel Machine (Zhang, Hu, Lu, Lange, Clune; Sakana AI, May 2025)

- **Title:** Darwin Godel Machine: Open-Ended Evolution of Self-Improving Agents
- **Authors:** Jenny Zhang, Shengran Hu, Cong Lu, Robert Lange, Jeff Clune
- **Source:** arXiv 2505.22954; open source: github.com/jennyzzt/dgm
- **Core idea:** Combines Darwinian evolution (population of agents, selection, mutation) with the Godel Machine concept (provably beneficial self-improvement) -- but replaces the impractical proof requirement with empirical validation. The DGM maintains an archive of agent variants (lineage), and agents improve their performance on tasks by rewriting their own code.
- **Methodology:**
  1. Maintain an archive of agent variants (the "evolutionary lineage")
  2. Sample a parent agent from the archive
  3. Use the parent agent to propose and implement code modifications to itself
  4. Run tests to empirically validate whether the modified agent is better
  5. If better, add to archive; continue
- **Key results:** On SWE-bench: 20.0% -> 50.0% (auto-improved). On Polyglot: 14.2% -> 30.7%, surpassing all hand-designed agents. Discovered improvements include: patch validation step, better file viewing, enhanced editing tools, solution ranking, history tracking.
- **Relevance:** The highest-profile demonstration of code-level self-modification to date. Directly relevant: the "testing team validates changes before promoting them to archive" maps to our pattern of running a sprint and evaluating whether the process change improved outcomes.

---

## Category 3: Multi-Agent Structural Self-Modification

### 3.1 EvoMAC: Self-Evolving Multi-Agent Collaboration Networks (Xue et al., ICLR 2025)

- **Title:** Self-Evolving Multi-Agent Collaboration Networks for Software Development
- **Authors:** Xue et al.
- **Source:** arXiv 2410.16946; **ICLR 2025**; open source available
- **Core idea:** A textual backpropagation algorithm that updates both agent prompts AND agent connections (the topology of who talks to whom) within a multi-agent system for software development.
- **Methodology:**
  1. Forward pass: coding team (MAC network) generates code
  2. Testing team generates unit tests as "proxy target" and runs them -- producing objective binary feedback
  3. Backward pass: textual backpropagation propagates the failure signal upstream through the agent network, identifying which agent's behavior most contributed to failure and rewriting their prompts
  4. Both agent instructions and inter-agent connections are updated
- **Key results:** Outperforms all prior multi-agent coding systems on rSDE-Bench (software-level) and HumanEval (function-level).
- **Relevance:** Extremely high. This is the closest published work to our use case: a multi-agent team where both the individual roles (prompts) AND the organizational structure (connections) evolve based on task feedback. The "testing team as proxy evaluator" maps to our "PI reviews sprint output and identifies root failure agent." Limitation: requires an automated objective test proxy, which is natural for coding but must be designed for other domains.

### 3.2 AFlow: Automating Agentic Workflow Generation (Zhang et al., ICLR 2025 Oral)

- **Title:** AFlow: Automating Agentic Workflow Generation
- **Authors:** Zhang et al.
- **Source:** arXiv 2410.10762; **ICLR 2025 Oral (top 1.8%, #2 in LLM Agent category)**
- **Core idea:** Represents agentic workflows as graphs of operators. Uses Monte Carlo Tree Search (MCTS) to explore the workflow design space, with an LLM evaluator providing feedback on each candidate workflow.
- **Methodology:**
  1. Define operators: Ensemble, Review & Revise, Generate, Test, etc.
  2. MCTS searches the space of operator combinations
  3. LLM evaluates workflow performance on held-out examples
  4. MCTS backpropagates scores to guide future exploration
  5. Optimal workflow is returned
- **Key results:** 7.44% improvement on HotPotQA F1; significant gains across math, coding, reasoning benchmarks.
- **Relevance:** Useful if we want to formally search for the optimal workflow topology for a given task type. The MCTS-over-operators model could be applied to searching for optimal role definitions. But it operates at design time, not continuously at runtime.

### 3.3 CoMAS: Co-Evolving Multi-Agent Systems via Interaction Rewards (Xue et al., 2025)

- **Title:** CoMAS: Co-Evolving Multi-Agent Systems via Interaction Rewards
- **Authors:** Xinlei Xue, Yifan Zhou, Guanyu Zhang, Zhiyuan Zhang, Yilun Li
- **Source:** arXiv 2510.08529; **3 citations**
- **Core idea:** Agents co-evolve by generating intrinsic reward signals from inter-agent discussions, without requiring external reward signals or hand-designed reward functions. Optimized via reinforcement learning.
- **Methodology:** Agents engage in discussion; the quality/coherence/agreement of that discussion generates intrinsic rewards that drive RL-based parameter updates. Agents improve together through social interaction, mirroring human group learning.
- **Key results:** Self-evolution without any external supervision; consistent improvement over baselines.
- **Relevance:** Interesting for systems where ground-truth evaluation is hard. The "discussion quality as intrinsic reward" mechanism could inform how our PI agent decides which process changes to promote (based on whether agents agree the new rule is an improvement, not just whether a metric went up).

### 3.4 EvoAgentX: Automated Framework for Evolving Agentic Workflows (Wang et al., July 2025)

- **Title:** EvoAgentX: An Automated Framework for Evolving Agentic Workflows
- **Authors:** Yingxu Wang et al.
- **Source:** arXiv 2507.03616; open source: github.com/EvoAgentX/EvoAgentX
- **Core idea:** An open-source platform that automates construction, execution, and evolutionary optimization of multi-agent workflows. Integrates three optimizer backends: TextGrad (prompt gradient descent), AFlow (MCTS-based workflow topology search), and MIPRO (Bayesian prompt optimization).
- **Methodology:** Modular 5-layer architecture: basic components -> agent -> workflow -> evolving -> evaluation. The evolving layer wraps the three optimizers. Short-term and long-term memory modules enable cross-session learning.
- **Key results:** +7.44% HotPotQA F1, +10% MBPP pass@1, +10% MATH solve accuracy, +20% GAIA overall accuracy.
- **Relevance:** High practical relevance. This is the most complete open-source framework for what we need. We could potentially build on or be inspired by EvoAgentX rather than building from scratch. The three optimizer backends (gradient, search, Bayesian) represent the practical options for how to evolve agent instructions.

---

## Category 4: Experience-Driven and Memory-Based Self-Evolution

### 4.1 EvolveR: Self-Evolving LLM Agents Through an Experience-Driven Lifecycle (Wu et al., 2025)

- **Title:** EvolveR: Self-Evolving LLM Agents through an Experience-Driven Lifecycle
- **Authors:** Runze Wu, Xingtai Wang, Jingwei Mei, Pengfei Cai, Dahua Fu, Chao Yang
- **Source:** arXiv 2510.16079; **10 citations**
- **Core idea:** Agents maintain a complete "experience lifecycle": collect experience, distill it into reusable skills, and use those skills to improve future performance. Jointly updates policy and memory bank.
- **Methodology:** Closed-loop lifecycle: task execution -> experience extraction -> skill distillation -> memory storage -> retrieval at next task. The skill library grows over time.
- **Relevance:** Closely maps to our pattern: after each sprint, extract lessons-learned -> distill into updated process rules -> store in organizational memory -> apply in next sprint.

### 4.2 SeaAgent: Self-Evolving Computer Use Agent (Sun et al., 2025)

- **Title:** SeaAgent: Self-Evolving Computer Use Agent with Autonomous Learning from Experience
- **Authors:** Zhiqi Sun, Zhongde Liu, Yan Zang, Yating Cao, Xiaofeng Dong, Tao Wu
- **Source:** arXiv 2508.04700; **19 citations**
- **Core idea:** Agents operating computer interfaces (GUI automation) build an ever-growing "usage manual" from their own experiences. The manual is consulted during future interactions. Continuous evolution through task exposure.
- **Methodology:** Agent executes computer tasks -> successes and failures are recorded -> an auto-generated "usage manual" is updated with newly learned patterns -> future agents consult the manual.
- **Key results:** Consistent performance improvement as manual grows; self-improvement without human labeling.
- **Relevance:** Direct analog: our organization's "process rules" file is exactly this usage manual. SeaAgent validates the architectural pattern of externalizing learned behavior into a manually-maintained, auto-updated document.

### 4.3 MemEvolve: Meta-Evolution of Agent Memory Systems (Zhang et al., 2025)

- **Title:** MemEvolve: Meta-Evolution of Agent Memory Systems
- **Authors:** Guanyu Zhang, Hao Ren, Chenghao Zhan, Zirui Zhou, Jian Wang
- **Source:** arXiv 2512.18746; **14 citations**
- **Core idea:** Applies evolutionary algorithms to the memory system itself (not just to stored memories), co-evolving how memory is organized, indexed, and retrieved alongside what is stored.
- **Relevance:** Relevant if we want our PI agent to also evolve its retrieval strategy (which past incidents to look at when diagnosing a new failure), not just what gets stored.

---

## Category 5: Hierarchical / Organizational Multi-Agent Self-Improvement

### 5.1 Agentic Neural Networks (2025) -- Textual Backpropagation for Multi-Agent

- **Title:** Agentic Neural Networks: Self-Evolving Multi-Agent Systems via Textual Backpropagation
- **Source:** arXiv 2506.09046
- **Core idea:** Conceptualizes multi-agent collaboration as a neural network (agents = nodes, communication = edges, layers = agent teams). Uses forward pass (task execution) and backward pass (textual gradient propagation) to update agent prompts and coordination strategies.
- **Methodology:** Two-phase: forward (task decomposition and execution), backward (failure signal propagates backward through the agent layer stack, each upstream agent receiving a critique of how their output contributed to downstream failure).
- **Key results:** Effective on complex multi-step tasks.
- **Relevance:** Excellent conceptual model for our hierarchical org. Think of it as: PI at the top receives final output evaluation, propagates "blame" backward through Director -> Manager -> Specialist chain, with each level updating their behavior.

### 5.2 MetaGPT: Role-Based Multi-Agent SOPs (Hong et al., ICLR 2024)

- **Title:** MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework
- **Authors:** Sirui Hong et al.
- **Source:** arXiv 2308.00352; **ICLR 2024 Oral**
- **Core idea:** Models a multi-agent AI team as a software company, with roles (Product Manager, Architect, Engineer, QA) defined by Standardized Operating Procedures (SOPs). Agents communicate through structured documents (PRDs, designs, code reviews) rather than free-form chat.
- **Methodology:** Each role has a fixed SOP defining what inputs it accepts, what outputs it produces, and what quality checks it applies. The framework enforces the SOP contract at runtime.
- **Key results:** State-of-the-art on HumanEval and MBPP for multi-agent code generation at the time.
- **Relevance:** High historical relevance. MetaGPT was the first system to explicitly define multi-agent roles via SOPs -- which is precisely the "process rules" layer in our architecture. However, MetaGPT's SOPs are static (human-defined at setup time). Our architecture extends MetaGPT by making SOPs self-updating.

### 5.3 SEMAF: Methodological Framework for Self-Evolving Multi-Agent Systems (Jeong 2025)

- **Title:** A Methodological Framework for Self-Evolving Multi-Agent Systems: Toward Adaptive and Continuous Learning in LLM-Based Architectures
- **Authors:** Chanwoong Jeong
- **Source:** ResearchSquare preprint 2025
- **Core idea:** Proposes an integrated framework (SEMAF) for multi-agent systems to autonomously learn and adapt across interaction cycles, with feedback loops that update individual agent behavior and inter-agent coordination.
- **Relevance:** Closest to our use case in terms of framing, but appears to be a theoretical/framework paper without strong empirical evaluation.

---

## Category 6: Prompt Optimization and Instruction Evolution

### 6.1 Automatic Prompt Optimization Survey (Ramnath et al., EMNLP 2025)

- **Title:** A Systematic Survey of Automatic Prompt Optimization Techniques
- **Authors:** Kaveri Ramnath, Kexin Zhou, Shaokang Guan, Swaroop Mishra
- **Source:** EMNLP 2025 Main; **30 citations**
- **Core idea:** Comprehensive taxonomy of all techniques for automatically optimizing LLM prompts: gradient-based (ProTeGi, TextGrad), search-based (MCTS, beam search), RL-based, and evolutionary.
- **Relevance:** Essential reference for implementing our instruction evolution mechanism. Maps the design space of "how to update role instructions."

### 6.2 Bayesian Optimization in Language Space (Kang & Yoganarasimhan, 2025)

- **Title:** Bayesian Optimization in Language Space: An Eval-Efficient AI Self-Improvement Framework
- **Authors:** Eun Hye Kang, Harikesh Yoganarasimhan
- **Source:** arXiv 2511.12063; **1 citation**
- **Core idea:** Treats prompt optimization as Bayesian optimization over a semantic space. Proposes directions for improvement without expensive full rollouts; uses prior data and model-based search. Outperforms RL fine-tuning methods on several benchmarks while using fewer evaluations.
- **Relevance:** Useful if our PI agent needs to update process rules efficiently (few incidents = few evaluations available). Bayesian optimization is sample-efficient by design.

### 6.3 Adaptive Self-Improvement for LLM Agentic System (Zhang et al., 2025)

- **Title:** Adaptive Self-Improvement LLM Agentic System for ML Library Development
- **Authors:** Guanchu Zhang, Wei Liang, Olivia Hsu, Kunle Olukotun
- **Source:** arXiv 2502.02534; **19 citations**
- **Core idea:** An LLM agentic system that adaptively improves its own process for ML library development by reflecting on past attempts and generating improved strategies.
- **Methodology:** Iterative loops: attempt task -> log failure modes -> reflect -> generate improved strategy -> attempt again. Strategies (analogous to process rules) are stored and retrieved.
- **Relevance:** Another direct analog of our use case in a software development context.

---

## Category 7: Surveys and Taxonomies

### 7.1 Comprehensive Survey of Self-Evolving AI Agents (Fang et al., 2025)

- **Title:** A Comprehensive Survey of Self-Evolving AI Agents: A New Paradigm Bridging Foundation Models and Lifelong Agentic Systems
- **Authors:** Jitao Fang, Yuhao Peng, Xin Zhang, Yongqi Wang, Xingyu Yi
- **Source:** arXiv 2508.07407; **64 citations** (highest in category)
- **Taxonomy:** Three axes:
  - Single-agent optimization (prompt, memory, reasoning, tools)
  - Multi-agent optimization (topology, role definitions, communication protocols)
  - Domain-specific optimization (web agents, code agents, scientific agents)
- **Relevance:** Essential survey. The multi-agent axis directly covers our use case. Companion GitHub repo: github.com/EvoAgentX/Awesome-Self-Evolving-Agents

### 7.2 Survey of Self-Evolving Agents: What, When, How, Where (Gao et al., 2025)

- **Title:** A Survey of Self-Evolving Agents: What, When, How, and Where to Evolve on the Path to Artificial Super Intelligence
- **Authors:** H. Gao, J. Geng, W. Hua, M. Hu, X. Juan, H. Liu
- **Source:** arXiv 2507.21046; **1 citation** (newer)
- **Key framing:** Organizes self-evolution as a 4-dimension question (What? When? How? Where?) and discusses path from self-evolving agents toward ASI.
- **Relevance:** Useful as a framing tool for positioning our work.

### 7.3 Survey on Self-Evolution of Large Language Models (Tao et al., 2024)

- **Title:** A Survey on Self-Evolution of Large Language Models
- **Authors:** Zhengwei Tao, Ting-En Lin, Xiancai Chen et al.
- **Source:** arXiv 2404.14387; **109 citations**
- **Core idea:** Covers the LLM self-evolution landscape before the agent-specific focus: self-training, self-play, self-distillation, constitutional AI.
- **Relevance:** Background reading; covers weight-update self-improvement that is adjacent to but distinct from our focus (prompt/rule-level improvement without weight updates).

---

## Category 8: Constitutional AI and Self-Alignment Evolution

### 8.1 Constitutional AI (Bai et al., 2022 / Anthropic)

- **Title:** Constitutional AI: Harmlessness from AI Feedback
- **Authors:** Yuntao Bai et al. (Anthropic)
- **Source:** arXiv 2212.08073; Anthropic Research
- **Core idea:** Train a model to critique and revise its own responses according to a set of principles (a "constitution"), then use RLHF with AI-generated (rather than human) feedback.
- **Methodology:** Phase 1: model critiques and revises responses using constitutional principles. Phase 2: RL from AI feedback (RLAIF) using a preference model trained on those critiques.
- **Relevance:** Conceptually relevant: the "constitution" is a set of normative rules (like our process rules), and the model self-improves against those rules. However, this operates at the weight level, not the instruction level. Our architecture inverts this: the rules themselves evolve, not the weights.

---

## Category 9: Open-Source Implementations and Industry Practice

### 9.1 OpenAI Self-Evolving Agents Cookbook (OpenAI, 2025)

- **URL:** cookbook.openai.com/examples/partners/self_evolving_agents/autonomous_agent_retraining
- **Core idea:** A practical, production-oriented guide to building self-improving agent systems. Three strategies:
  1. Manual iteration (human reviews failures, updates prompts manually)
  2. LLM-as-judge loop (automated evaluation, automated prompt updates)
  3. GEPA: Genetic-Pareto algorithm (sample trajectories, reflect in natural language, propose revisions, evolve prompts through selection)
- **Key insight from cookbook:** "Agentic systems plateau because they depend on humans to diagnose edge cases and correct failures." The solution is a repeatable loop: capture issues -> learn from feedback -> promote improvements back to production.
- **Relevance:** Very high practical relevance. This is essentially our architecture described at a high level. Specifically: the incident-driven loop (failure -> reflection -> rule update -> re-deploy) is exactly what the cookbook advocates. The GEPA approach (evolutionary prompt search) is relevant if we want to automate the rule-update step.

### 9.2 EvoAgentX Framework (Open Source, May 2025)

- **URL:** github.com/EvoAgentX/EvoAgentX
- **Milestone:** 1,000 GitHub stars by July 2025
- **Core idea:** The most complete open-source implementation of self-evolving agent workflows. Integrates TextGrad, AFlow (MCTS), and MIPRO as optimizer backends.
- **Architecture:** 5-layer modular stack: basic components -> agent -> workflow -> evolving -> evaluation
- **Relevance:** High. Could serve as a reference implementation or starting point.

### 9.3 Darwin Godel Machine (Open Source, Sakana AI, May 2025)

- **URL:** github.com/jennyzzt/dgm
- **Alternative community implementation:** github.com/lemoz/darwin-godel-machine (with multi-LLM support, sandboxed execution, population-based evolution, comprehensive benchmarking)
- **Relevance:** Open-source implementation of the highest-performing self-modifying agent system published to date.

### 9.4 CrewAI / LangGraph / AutoGen (Major Framework Status, 2025)

- **CrewAI:** Role-based team orchestration; $18M Series A; 60% of Fortune 500 as customers; 100K+ agent executions/day. Does NOT include built-in self-evolution of roles.
- **LangGraph:** Graph-based workflow with stateful nodes; good for implementing our evolution loop explicitly as a graph.
- **AutoGen (Microsoft):** Merged with Semantic Kernel; conversation-first multi-agent collaboration. Has human-in-the-loop patterns that could support our PI approval gate.
- **Self-improvement gap:** None of these frameworks include built-in self-modification of agent roles or process rules. This is a gap in the tooling ecosystem our architecture addresses.

---

## Gaps in the Literature

### Gap 1: Org-Level Knowledge Evolution (Highest Priority for Our Use Case)

Most self-evolving agent research focuses on task-level performance (will the agent solve this problem better?). Almost none address organizational knowledge: how does the multi-agent team evolve its shared norms, escalation policies, role boundaries, and coordination protocols?

The closest work (MetaGPT + EvoMAC) treats SOPs as static setup or updates them only at the workflow topology level. No published system does what we do: have a PI/Director agent observe a full sprint/incident, diagnose which process rule failed, and rewrite that specific rule in the shared process rules document.

### Gap 2: Hierarchical Responsibility Attribution

When a multi-agent pipeline fails, current textual backpropagation approaches (EvoMAC, Agentic Neural Networks) propagate a generic blame signal backward. No system yet implements a structured root cause analysis ("Which role's process rule was the proximate cause?") before updating. Our incident-driven approach -- where the PI writes a structured postmortem identifying the specific failing rule and agent -- is more principled.

### Gap 3: Long-Horizon Organizational Memory

Most memory-based self-evolution systems (EvolveR, SeaAgent, MemEvolve) operate at the agent level. No system maintains an organizational memory (shared across all agents) that grows a history of what process changes were made, why, and what effect they had. This institutional memory is crucial for avoiding regressions (reverting a rule that was previously changed for a good reason).

### Gap 4: Human-in-the-Loop Safety Gate for Rule Changes

None of the fully automated self-evolution systems include a mandatory human approval gate specifically for process-level changes (as distinct from task-level outputs). The OpenAI Cookbook's human-review loop is the closest analog, but it focuses on output quality, not process rule changes. Our architecture's explicit "PI proposes, human approves" gate for rule changes is a safety mechanism not studied in the literature.

### Gap 5: Cross-Domain Rule Transfer

When a process rule is learned in one domain (e.g., game content generation), can it transfer to another (e.g., scientific research)? ADAS found that discovered agent designs transfer across domains. No work has studied whether evolved process rules (as opposed to agent code) transfer.

---

## Connections to Our Specific Use Case

Our ai-lab-agents and ai-game-studio systems implement a pattern we call **Incident-Driven Organizational Evolution (IDOE)**:

1. **Incident detection:** Sprint/task fails or produces substandard output
2. **Postmortem:** PI/Director conducts structured root cause analysis identifying the specific process rule or role definition that failed
3. **Rule update:** PI/Director proposes a targeted edit to the process rules document or a specific agent's role definition
4. **Human approval:** Proposed change surfaced for human review and approval
5. **Deployment:** Approved change is applied; agents pick up new rules on next initialization
6. **Retrospective:** After several sprints, evaluate whether change improved outcomes

Mapping to literature:
- Steps 1-3 directly implement Reflexion at the organizational level (not individual agent)
- Step 3 is a TextGrad-style "textual gradient" applied to process rules
- Step 4 is the human safety gate missing from most automated systems
- Step 5 is analogous to EvoMAC's prompt update step, but targeting role definitions rather than task-specific agent outputs
- The accumulating process rules document is analogous to ADAS's "archive of discoveries"
- The PI/Director role is analogous to ADAS's "meta-agent" but is embedded within the organizational hierarchy rather than sitting outside it

---

## Recommended Priority Reading

### Must Read (Directly Implement Our Pattern)
1. Shinn et al. 2023 -- Reflexion (arXiv 2303.11366) -- foundational failure-reflection pattern
2. Hu, Lu, Clune 2024 -- ADAS (arXiv 2408.08435) -- meta-agent archive architecture
3. Xue et al. 2024/2025 -- EvoMAC (arXiv 2410.16946) -- multi-agent role+topology co-evolution
4. Zhang et al. 2025 -- Darwin Godel Machine (arXiv 2505.22954) -- empirical self-improvement validation
5. OpenAI Cookbook 2025 -- Self-Evolving Agents -- practical production implementation guide

### Should Read (Strong Methodological Relevance)
6. Yuksekgonul et al. 2024 -- TextGrad (arXiv 2406.07496) -- textual gradient framework
7. Madaan et al. 2023 -- Self-Refine (NeurIPS 2023) -- self-critique loop
8. Yin et al. 2024 -- Godel Agent (arXiv 2410.04444) -- self-referential self-modification
9. Wang et al. 2025 -- EvoAgentX (arXiv 2507.03616) -- open-source integrated framework
10. Fang et al. 2025 -- Survey (arXiv 2508.07407) -- comprehensive taxonomy

### Consider Reading (Background and Context)
11. Hong et al. 2023 -- MetaGPT (arXiv 2308.00352) -- role-based SOPs for multi-agent teams
12. Xue et al. 2025 -- CoMAS (arXiv 2510.08529) -- co-evolution via interaction rewards
13. Wu et al. 2025 -- EvolveR (arXiv 2510.16079) -- experience lifecycle
14. Sun et al. 2025 -- SeaAgent (arXiv 2508.04700) -- usage manual auto-generation
15. Tao et al. 2024 -- LLM Self-Evolution Survey (arXiv 2404.14387) -- broader LLM context

---

## Related Work Narrative (Draft for Papers Section)

### Self-Improvement via Reflection

Early work on LLM self-improvement established the foundational pattern of critique-and-revise loops. **Self-Refine** (Madaan et al., 2023) showed a single LLM can iteratively improve outputs by generating its own feedback. **Reflexion** (Shinn et al., 2023) extended this to agent trajectories: after failing a task, an agent reflects in natural language and stores the reflection in an episodic buffer for future trials. These single-agent patterns established that verbal self-critique -- without weight updates -- can substantially improve LLM performance.

### Automated Agent Design (Architecture-Level)

A new research area, **Automated Design of Agentic Systems (ADAS)** (Hu et al., 2024), treats agent design itself as an optimization problem. A meta-agent maintains an archive of discovered agent designs, expressed in code, and iteratively proposes new designs for empirical validation. The **Godel Agent** (Yin et al., 2024) makes this self-referential: the optimization procedure itself is subject to self-modification. The **Darwin Godel Machine** (Zhang et al., 2025) demonstrates empirically that code-level self-modification can double coding agent performance on real benchmarks.

### Multi-Agent Structural Self-Modification

Several recent systems extend self-improvement from single agents to multi-agent organizational structures. **EvoMAC** (Xue et al., 2025) introduces textual backpropagation through an agent collaboration network, updating both individual agent prompts and inter-agent connections based on task feedback. **CoMAS** (Xue et al., 2025) generates intrinsic reward signals from inter-agent discussion quality, enabling co-evolution without external supervision. **EvoAgentX** (Wang et al., 2025) provides an open-source framework integrating multiple optimizer backends for evolving multi-agent workflows.

### Our Contribution

Existing work focuses primarily on task-level self-improvement: can agents solve problems better? We address a complementary and largely unexplored problem: **organizational-level self-improvement**, in which a hierarchical multi-agent system evolves its own shared process rules, role definitions, and coordination norms based on retrospective analysis of past sprints and incidents. Our Incident-Driven Organizational Evolution (IDOE) pattern introduces: (1) structured postmortem-driven root cause attribution at the rule level, (2) a human-in-the-loop safety gate specifically for process-level changes, and (3) an organizational memory that accumulates a history of rule changes with their rationale. To our knowledge, no prior published system implements all three components together.

---

## Sources

**arXiv / Academic Papers**
- [Reflexion (arXiv 2303.11366)](https://arxiv.org/abs/2303.11366)
- [Self-Refine (NeurIPS 2023)](https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html)
- [TextGrad (arXiv 2406.07496)](https://arxiv.org/abs/2406.07496)
- [ADAS (arXiv 2408.08435)](https://arxiv.org/abs/2408.08435)
- [Godel Agent (arXiv 2410.04444)](https://arxiv.org/abs/2410.04444)
- [EvoMAC (arXiv 2410.16946)](https://arxiv.org/abs/2410.16946)
- [AFlow (arXiv 2410.10762)](https://arxiv.org/pdf/2410.10762)
- [Darwin Godel Machine (arXiv 2505.22954)](https://arxiv.org/abs/2505.22954)
- [EvoAgentX (arXiv 2507.03616)](https://arxiv.org/abs/2507.03616)
- [EvolveR (arXiv 2510.16079)](https://arxiv.org/abs/2510.16079)
- [CoMAS (arXiv 2510.08529)](https://arxiv.org/abs/2510.08529)
- [Fang et al. Survey (arXiv 2508.07407)](https://arxiv.org/abs/2508.07407)
- [Gao et al. Survey (arXiv 2507.21046)](https://arxiv.org/abs/2507.21046)
- [Tao et al. LLM Self-Evolution Survey (arXiv 2404.14387)](https://arxiv.org/abs/2404.14387)
- [SeaAgent (arXiv 2508.04700)](https://arxiv.org/abs/2508.04700)
- [MetaGPT (arXiv 2308.00352)](https://arxiv.org/pdf/2308.00352)
- [Constitutional AI (arXiv 2212.08073)](https://arxiv.org/abs/2212.08073)
- [Agentic Neural Networks (arXiv 2506.09046)](https://arxiv.org/abs/2506.09046)

**Open Source Implementations**
- [EvoAgentX GitHub](https://github.com/EvoAgentX/EvoAgentX)
- [Awesome Self-Evolving Agents (survey companion repo)](https://github.com/EvoAgentX/Awesome-Self-Evolving-Agents)
- [Darwin Godel Machine GitHub (official)](https://github.com/jennyzzt/dgm)
- [Darwin Godel Machine GitHub (community)](https://github.com/lemoz/darwin-godel-machine)
- [ADAS GitHub](https://github.com/ShengranHu/ADAS)
- [Reflexion GitHub](https://github.com/noahshinn/reflexion)
- [Godel Agent GitHub](https://github.com/Arvid-pku/Godel_Agent)
- [TextGrad GitHub](https://github.com/zou-group/textgrad)

**Industry / Blog Posts**
- [OpenAI Self-Evolving Agents Cookbook](https://cookbook.openai.com/examples/partners/self_evolving_agents/autonomous_agent_retraining)
- [Sakana AI - Darwin Godel Machine Blog](https://sakana.ai/dgm/)
- [EvoAgentX Documentation](https://evoagentx.github.io/EvoAgentX/index.html)
- [Self-Evolving Multi-Agent Collaboration Network (ICLR PDF)](https://proceedings.iclr.cc/paper_files/paper/2025/file/39af4f2f9399122a14ccf95e2d2e7122-Paper-Conference.pdf)
