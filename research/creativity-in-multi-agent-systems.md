# Creativity in Multi-Agent AI/LLM Systems: A Comprehensive Literature Review

**Date:** 2026-02-27
**Scope:** Academic papers and implementations (2023-2026) on creative problem-solving, divergent thinking, collaboration patterns, brainstorming protocols, adversarial dynamics, computational creativity theory, and creativity metrics in multi-agent LLM systems.

---

## Table of Contents

1. [Survey and Overview Papers](#1-survey-and-overview-papers)
2. [Theoretical Foundations: Computational Creativity](#2-theoretical-foundations-computational-creativity)
3. [Divergent Thinking in LLM Agents](#3-divergent-thinking-in-llm-agents)
4. [Creative Collaboration Patterns in Multi-Agent Systems](#4-creative-collaboration-patterns-in-multi-agent-systems)
5. [Brainstorming and Ideation Protocols](#5-brainstorming-and-ideation-protocols)
6. [Adversarial Dynamics and Productive Disagreement](#6-adversarial-dynamics-and-productive-disagreement)
7. [Self-Evolving and Co-Evolutionary Agent Systems](#7-self-evolving-and-co-evolutionary-agent-systems)
8. [Creativity Metrics and Evaluation](#8-creativity-metrics-and-evaluation)
9. [Creative Applications of Multi-Agent Systems](#9-creative-applications-of-multi-agent-systems)
10. [Key Implementations and Repositories](#10-key-implementations-and-repositories)
11. [Synthesis: Design Principles for Creative Multi-Agent Systems](#11-synthesis-design-principles-for-creative-multi-agent-systems)
12. [Application to a Self-Evolving Multi-Agent Framework](#12-application-to-a-self-evolving-multi-agent-framework)

---

## 1. Survey and Overview Papers

### 1.1 Creativity in LLM-based Multi-Agent Systems: A Survey
- **Authors:** Yi-Cheng Lin, Kang-Chieh Chen, Zhe-Yan Li, Tzu-Heng Wu, Tzu-Hsuan Wu, Kuan-Yu Chen, Hung-yi Lee, Yun-Nung Chen
- **Year:** 2025 (EMNLP 2025)
- **Paper:** https://arxiv.org/abs/2505.21116
- **Key Findings:** This is the first survey dedicated to creativity in multi-agent systems. It presents: (1) a taxonomy of agent proactivity and persona design, (2) an overview of generation techniques including divergent exploration, iterative refinement, and collaborative synthesis, (3) relevant datasets and evaluation metrics, and (4) a discussion of challenges including inconsistent evaluation standards, insufficient bias mitigation, coordination conflicts, and lack of unified benchmarks.
- **Application to Self-Evolving Framework:** Provides the taxonomic backbone for classifying creative behaviors in agents. The taxonomy of agent proactivity (reactive, proactive, autonomous) can directly inform how agents in a self-evolving framework choose when and how to contribute creative ideas. The identification of coordination conflicts as a key challenge suggests that creative agent orchestration needs explicit conflict-resolution mechanisms.

### 1.2 Large Language Models for Scientific Idea Generation: A Creativity-Centered Survey
- **Authors:** Fatemeh Shahhosseini, Arash Marioriyad, Ali Momen, et al.
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2511.07448
- **Key Findings:** Organizes methods for LLM-driven scientific ideation into five families: (1) External knowledge augmentation, (2) Prompt-based distributional steering, (3) Inference-time scaling, (4) Multi-agent collaboration, and (5) Parameter-level adaptation. Adopts Boden's taxonomy to characterize creative novelty types and Rhodes' 4Ps framework (Person, Process, Press, Product) to analyze creativity sources.
- **Application to Self-Evolving Framework:** The five method families provide a menu of techniques that different agents could specialize in. A self-evolving system could dynamically allocate agents across these families based on what stage of creative generation the system is in.

### 1.3 Multi-Agent Large Language Models for Conversational Task-Solving
- **Authors:** Jonas Becker
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2410.22932
- **Key Findings:** Systematic evaluation across discussion paradigms reveals three critical challenges: (1) longer discussions enhance reasoning but cause "problem drift" where agents lose focus on task requirements, (2) prolonged discussions risk "alignment collapse" raising safety concerns, (3) "discussion monopolization" through long generations creates fairness issues. Multi-agent systems excel in complex reasoning but fail on basic tasks.
- **Application to Self-Evolving Framework:** Directly informs conversation length management. A self-evolving framework needs adaptive discussion termination -- knowing when to stop discussing and start executing. The problem drift finding suggests implementing checkpoints that re-anchor agents to the original creative objective.

---

## 2. Theoretical Foundations: Computational Creativity

### 2.1 Boden's Three Types of Creativity Applied to LLMs

**Source:** Margaret Boden's foundational work on computational creativity, extensively referenced in recent LLM literature.

Three types of creativity form the theoretical bedrock for understanding what LLMs can and cannot do creatively:

1. **Combinatorial Creativity:** Connecting familiar ideas in novel ways. LLMs are strongest here due to their ability to identify and recombine patterns across vast knowledge spaces. Most current multi-agent creative systems operate at this level.

2. **Exploratory Creativity:** Discovering new possibilities within an established conceptual space by testing rule implications. Multi-agent debate and iterative refinement approaches achieve this level.

3. **Transformational Creativity:** Fundamentally altering the rules of a conceptual space to reach previously inaccessible points. This remains largely elusive for current LLMs due to their autoregressive nature -- generating text one token at a time inherently constrains them to existing probability distributions.

**Application to Self-Evolving Framework:** A self-evolving framework should explicitly target all three levels. Combinatorial creativity can be achieved through cross-domain agent collaboration. Exploratory creativity through structured search with diverse agent perspectives. Transformational creativity is the hardest challenge -- it may require agents that can modify their own prompts, tools, and interaction patterns in ways that fundamentally change the system's creative search space.

### 2.2 Creative Agents: Simulating the Systems Model of Creativity with Generative Agents
- **Authors:** Naomi Imasato, Kazuki Miyazawa, Takayuki Nagai, Takato Horii
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2411.17065
- **Key Findings:** Implements Csikszentmihalyi's systems model of creativity using LLM agents. In Csikszentmihalyi's model, creativity emerges from the interaction of three forces: (1) the Individual who produces variations, (2) the Field (social institutions/gatekeepers) that selects promising variations, (3) the Domain (cultural knowledge) that preserves and transmits selected innovations. Experiments compared isolated virtual artists versus multi-agent systems. Results show that agents receiving feedback from the "field" (other agents serving as gatekeepers) generate artifacts that are more novel and more valuable.
- **Application to Self-Evolving Framework:** This is directly applicable. A self-evolving framework should implement all three components: generator agents (Individual), evaluator/critic agents (Field), and a shared knowledge base that accumulates validated creative outputs (Domain). The key insight is that creativity is not a property of individual agents but an emergent property of the system's social architecture.

### 2.3 LLMs Can Realize Combinatorial Creativity
- **Authors:** Tianyang Gu, Jingjin Wang, Zhihao Zhang, HaoHong Li
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2412.14141
- **Key Findings:** Explicitly implements combinatorial creativity theory using LLMs. Features a generalization-level retrieval system for cross-domain knowledge discovery and a structured combinatorial process for idea generation. The retrieval system maps concepts across different abstraction levels to enable meaningful connections between disparate domains. Improves similarity scores to real research developments by 7-10% across multiple metrics.
- **Application to Self-Evolving Framework:** The generalization-level retrieval system is a powerful mechanism for a self-evolving framework. Agents could maintain an abstraction hierarchy of concepts, enabling them to find non-obvious connections between domains at different levels of generality. This is how truly creative combinations emerge -- not by matching surface-level keywords but by recognizing structural similarities at higher abstraction levels.

---

## 3. Divergent Thinking in LLM Agents

### 3.1 Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate
- **Authors:** Tian Liang, Zhiwei He, Wenxiang Jiao, Xing Wang, et al.
- **Year:** 2023
- **Paper:** https://arxiv.org/abs/2305.19118
- **Key Findings:** Identifies the critical "Degeneration-of-Thought" (DoT) problem: once an LLM has established confidence in its solutions, it cannot generate novel thoughts through self-reflection even if its initial stance is incorrect. Proposes Multi-Agent Debate (MAD) where multiple agents argue in a "tit for tat" state managed by a judge. Key design insights: (1) adaptive break of debate is required, (2) a "modest" level of tit-for-tat is optimal -- too aggressive debate reduces quality, (3) LLMs may not be fair judges if different models are used.
- **Application to Self-Evolving Framework:** The Degeneration-of-Thought problem is a critical threat to any self-evolving system. If agents converge too quickly on a solution, the system loses creative potential. The MAD framework provides a direct countermeasure: when the system detects convergence (DoT), it should inject adversarial agents or switch to debate mode. The finding about "modest" tit-for-tat suggests a creativity thermostat -- the system needs to calibrate the intensity of disagreement.

### 3.2 Divergent Creativity in Humans and Large Language Models
- **Authors:** Antoine Bellemare-Pepin, Francois Lespinasse, Philipp Tholke, Yann Harel, Kory Mathewson, Jay A. Olson, Yoshua Bengio, Karim Jerbi
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2405.13012
- **Key Findings:** Compared LLM semantic divergence against 100,000 humans. LLMs can surpass average human performance on the Divergent Association Task and approach human creative writing abilities, but fall short of highly creative humans. Even top-performing LLMs are largely surpassed by highly creative individuals, underscoring a ceiling. Proposes techniques to improve semantic diversity: prompt design, hyper-parameter tuning, and ensemble methods.
- **Application to Self-Evolving Framework:** The "creativity ceiling" finding is important. A self-evolving framework should not rely on individual agent creativity alone but use multi-agent interaction to push past the ceiling that single agents cannot breach. The benchmark against 100K humans provides a concrete target: the system should aim to match or exceed the 90th percentile of human creative performance, not just the average.

### 3.3 Evaluating LLMs' Divergent Thinking Capabilities for Scientific Idea Generation with Minimal Context (LiveIdeaBench)
- **Authors:** Kai Ruan, Xuan Wang, Jixiang Hong, Peng Wang, Yang Liu, Hao Sun
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2412.17596
- **Key Findings:** Uses single-keyword prompts to evaluate divergent thinking across five dimensions from Guilford's theory: originality, feasibility, fluency, flexibility, and clarity. Tested 40+ models across 1,180 keywords in 22 scientific domains. Critical finding: scientific idea generation capabilities are poorly predicted by standard metrics of general intelligence. Models like QwQ-32B-preview achieve creative performance comparable to top-tier models despite significant gaps in general intelligence scores.
- **Application to Self-Evolving Framework:** The decoupling of creativity from general intelligence has profound implications. A self-evolving framework should not assume that its "smartest" agent is also its most creative. It may be more effective to assign creative ideation tasks to agents specifically selected or fine-tuned for divergent thinking, even if they are smaller or less capable at other tasks.

### 3.4 Does Less Hallucination Mean Less Creativity?
- **Authors:** Mohor Banerjee, Nadya Yuki Wangsajaya, et al.
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2512.11509
- **Key Findings:** Investigates how hallucination-reduction techniques affect creativity. Chain of Verification (CoVe) enhances divergent thinking, DoLa (Decoding by Contrasting Layers) suppresses it, and RAG shows minimal impact. This reveals a fundamental tension: some hallucination-reduction methods kill creativity while others preserve or enhance it.
- **Application to Self-Evolving Framework:** This is an actionable design principle. In creative phases, agents should use CoVe rather than DoLa for verification. The framework could implement a "creativity mode" switch that changes verification strategies depending on whether the current objective is creative exploration versus factual accuracy. RAG's neutral impact suggests it can be safely used for grounding without sacrificing creativity.

### 3.5 Shared Imagination: LLMs Hallucinate Alike
- **Authors:** Yilun Zhou, Caiming Xiong, Silvio Savarese, Chien-Sheng Wu
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2407.16604
- **Key Findings:** Despite total fictionality of imaginary questions, all models can answer each other's questions with remarkable success, suggesting a "shared imagination space." This implies model homogeneity -- LLMs trained on similar data develop similar creative biases.
- **Application to Self-Evolving Framework:** This is a warning about diversity. If all agents in a multi-agent system use similar LLMs, they will share the same creative blindspots. A self-evolving framework should deliberately use heterogeneous models (different architectures, training data, sizes) to maximize the creative search space and avoid the "shared imagination" trap.

---

## 4. Creative Collaboration Patterns in Multi-Agent Systems

### 4.1 The Spark Effect: On Engineering Creative Diversity in Multi-Agent AI Systems
- **Authors:** Alexander Doudkin, Anton Voelker, Friedrich von Borries
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2510.15568
- **Key Findings:** Persona-conditioned LLM agents ("Sparks") intentionally diversify agent behavior within multi-agent workflows. Using an LLM-as-a-judge protocol calibrated against human gold standards, they observe a mean diversity gain of +4.1 points (on a 1-10 scale) when persona-conditioned agents replace a uniform system prompt, narrowing the gap to human experts to just 1.0 point.
- **Application to Self-Evolving Framework:** Persona conditioning is a low-cost, high-impact technique. A self-evolving framework should maintain a library of persona prompts that can be dynamically assigned to agents. The +4.1 diversity gain from simply changing system prompts is remarkable -- this is the single most cost-effective intervention identified in this review.

### 4.2 Exploring Design of Multi-Agent LLM Dialogues for Research Ideation
- **Authors:** Keisuke Ueda, Wataru Hirota, Takuto Asakura, et al.
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2507.08350
- **Code:** https://github.com/g6000/MultiAgent-Research-Ideator
- **Key Findings:** Comprehensive analysis of multi-agent dialogue configurations for scientific ideation. Compared different agent roles, number of agents, and dialogue depth. Results show that: (1) enlarging the agent cohort enriches idea diversity, (2) deepening interaction depth increases diversity, (3) broadening agent persona heterogeneity enriches diversity, and (4) increasing critic-side diversity within ideation-critique-revision loops boosts feasibility.
- **Application to Self-Evolving Framework:** Provides concrete design parameters. The finding that critic diversity matters more than generator diversity for feasibility is counter-intuitive and actionable. A self-evolving framework should invest more in diversifying its evaluation/critic agents than its generator agents when the goal is producing feasible creative ideas.

### 4.3 Beyond Brainstorming: What Drives High-Quality Scientific Ideas?
- **Authors:** Nuo Chen, Yicheng Tong, Jiaying Wu, et al.
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2508.04575
- **Key Findings:** Investigates whether structured multi-agent discussions surpass solitary ideation. Key results: (1) Multi-agent discussions substantially outperform solitary baselines. (2) A designated leader acts as a catalyst, transforming discussion into more integrated and visionary proposals. (3) Cognitive diversity is a primary driver of quality. (4) Expertise is a non-negotiable prerequisite -- teams lacking senior knowledge fail to surpass even a single competent agent.
- **Application to Self-Evolving Framework:** The "leader as catalyst" finding suggests that creative multi-agent sessions should not be purely democratic. A self-evolving framework should designate a "creative director" agent that synthesizes diverse inputs rather than just aggregating votes. The expertise prerequisite means that agents need deep domain knowledge before they can be effectively creative -- random persona assignment without knowledge backing produces inferior results.

### 4.4 On the Dynamics of Multi-Agent LLM Communities Driven by Value Diversity
- **Authors:** Muhua Huang, Qinlin Zhao, Xiaoyuan Yi, Xing Xie
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2512.10665
- **Key Findings:** Using Schwartz's Theory of Basic Human Values, constructed multi-agent simulations of communities with varying value diversity. Value diversity enhances value stability, fosters emergent behaviors, and produces more creative principles. However, effects show diminishing returns: extreme heterogeneity induces instability.
- **Application to Self-Evolving Framework:** Value diversity as a creativity lever is novel and powerful. Beyond just different personas or roles, agents could be given different "value systems" (e.g., prioritizing novelty vs. safety vs. efficiency). The diminishing returns finding provides a practical constraint: there is an optimal level of diversity beyond which the system becomes chaotic rather than creative.

### 4.5 AgentVerse: Facilitating Multi-Agent Collaboration and Exploring Emergent Behaviors
- **Authors:** Weize Chen, Yusheng Su, et al.
- **Year:** 2024 (ICLR 2024)
- **Paper:** https://arxiv.org/abs/2308.10848
- **Code:** https://github.com/OpenBMB/AgentVerse
- **Key Findings:** Multi-agent groups outperform single agents across text understanding, reasoning, coding, and embodied AI tasks. Discovers three emergent behaviors: (1) Volunteer behaviors -- agents spontaneously offer assistance, improving team efficiency, (2) Conformity behaviors -- agents adjust deviated behaviors under criticism from others, (3) Destructive behaviors -- occasionally leading to undesired outcomes.
- **Application to Self-Evolving Framework:** The emergence of volunteer, conformity, and destructive behaviors is directly relevant. A self-evolving framework should monitor for these emergent patterns and selectively reinforce volunteer behaviors (which increase creative output), manage conformity (which can suppress creative outliers), and detect and mitigate destructive behaviors. This requires a meta-level observation mechanism.

### 4.6 Exploring Collaboration Mechanisms for LLM Agents: A Social Psychology View
- **Authors:** (ACL 2024)
- **Paper:** https://github.com/zjunlp/MachineSoM
- **Key Findings:** Simulated societies of LLM agents with individual traits (easy-going, overconfident) engaging in debate and reflection. Found that individual traits have minimal influence on performance, but collaborative strategies have significant impact. Multi-agent discussion outperformed single-agent chain-of-thought, demonstrating emergent problem-solving where mediocre reasoners collectively produce superior outcomes.
- **Application to Self-Evolving Framework:** The finding that individual traits matter less than collaboration structure is crucial. A self-evolving framework should optimize its interaction topology and communication protocols rather than focusing on making individual agents "smarter." The structure of collaboration is more important than the capability of any single agent.

### 4.7 SMoA: Sparse Mixture-of-Agents
- **Authors:** Dawei Li, Zhen Tan, Peijia Qian, et al.
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2411.03284
- **Key Findings:** Draws inspiration from Sparse Mixture-of-Experts to sparsify information flows among LLM agents. Introduces Response Selection and Early Stopping mechanisms. Assigns distinct role descriptions to each agent, fostering diverse and divergent thinking. Achieves performance comparable to dense mixture-of-agents with significantly lower computational costs.
- **Application to Self-Evolving Framework:** Sparse communication is essential for scalable creative systems. Not every agent needs to talk to every other agent. A self-evolving framework should use selective routing -- directing creative inputs only to agents whose perspectives are most likely to produce novel combinations, rather than broadcasting to all agents.

---

## 5. Brainstorming and Ideation Protocols

### 5.1 Persona-based Multi-Agent Collaboration for Brainstorming
- **Authors:** Nate Straub, Saara Khan, Katharina Jay, Brian Cabral, Oskar Linde
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2512.04488
- **Key Findings:** Demonstrates the importance of persona-based brainstorming. Evaluates different persona pairings (e.g., Doctor vs VR Engineer) and agent-to-agent dynamics across three modes: (1) separate brainstorming, (2) together brainstorming, (3) separate-then-together brainstorming. Results: persona choice shapes idea domains, collaboration mode shifts diversity of idea generation, and multi-agent persona-driven brainstorming produces greater idea depth and cross-domain coverage.
- **Application to Self-Evolving Framework:** The "separate-then-together" pattern is particularly promising. A self-evolving framework could implement a two-phase creative process: Phase 1 has diverse specialist agents brainstorming independently (maximizing divergence), Phase 2 brings them together for synthesis and cross-pollination (enabling combinatorial creativity). This mirrors the classic "diverge then converge" pattern in design thinking.

### 5.2 IBIS-based Brainstorming Support System with Multiple AI Agents
- **Source:** ACM DIS 2024, https://dl.acm.org/doi/fullHtml/10.1145/3643562.3672609
- **Key Findings:** Implements an extended Issue-Based Information System (IBIS) for multi-agent brainstorming. Agents post messages in IBIS structure (Issues, Positions, Arguments) and determine which messages require replies. Enables flexible, tree-like idea development rather than sequential brainstorming. Features dynamic role-playing where agents adopt diverse personas and provide evidence-based information via web search.
- **Application to Self-Evolving Framework:** The IBIS structure provides a formal framework for organizing creative discourse. Instead of unstructured agent chat, a self-evolving framework could require agents to tag their contributions as Issues (problems to solve), Positions (proposed solutions), or Arguments (evidence for/against). This makes the creative process more tractable and enables the system to track which ideas have been adequately explored versus which remain open.

### 5.3 The Wisdom of Agent Crowds: A Human-AI Interaction Innovation Ignition Framework
- **Authors:** Senhao Yang, Qiwen Cheng, Ruiqi Ma, et al.
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2505.06947
- **Key Findings:** Constructs a multi-agent brainstorming framework based on BDI (Belief-Desire-Intention) theory. Integrates general and reasoning LLMs to handle complex problems. Designs a quantitative analysis algorithm for brainstorming diversity based on k-means clustering and information entropy. Uses real-time updated structured text summaries and an interactive "Cothinker" module.
- **Application to Self-Evolving Framework:** The BDI theoretical grounding is valuable. Agents with explicit beliefs, desires, and intentions can reason about their own creative processes and adapt them. The information entropy metric for measuring brainstorming diversity is directly implementable as a runtime signal: if entropy drops below a threshold, the system knows creativity is declining and can intervene.

### 5.4 Brainstormers (GitHub Implementation)
- **Repository:** https://github.com/Azzedde/brainstormers
- **Key Features:** Suite of specialized brainstorming agents implementing: Reverse Brainstorming, Role Storming, SCAMPER (Substitute, Combine, Adapt, Modify, Put to other uses, Eliminate, Reverse), Six Thinking Hats, and Starbursting.
- **Application to Self-Evolving Framework:** Provides ready-to-use brainstorming method implementations. A self-evolving framework could rotate through these structured creativity techniques based on the nature of the problem. SCAMPER is particularly useful for improving existing solutions, while Six Thinking Hats ensures systematic coverage of different perspectives.

### 5.5 ResearchTown: Simulator of Human Research Community
- **Authors:** Haofei Yu, Zhaochen Hong, Zirui Cheng, et al.
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2412.17767
- **Key Findings:** Multi-agent framework simulating research communities. Represents researchers as agent nodes and papers as data nodes in a graph, connected by collaboration relationships. Introduces TextGNN that models research activities (reading, writing, reviewing) as message-passing on the agent-data graph. Can generate interdisciplinary research ideas.
- **Application to Self-Evolving Framework:** The graph-based representation of agent-knowledge relationships is powerful. A self-evolving framework could maintain a dynamic knowledge graph where agent expertise, past contributions, and idea connections are all represented. This enables intelligent routing of creative tasks to the most relevant agent combinations.

---

## 6. Adversarial Dynamics and Productive Disagreement

### 6.1 Improving Factuality and Reasoning in Language Models through Multiagent Debate
- **Authors:** Yilun Du, Shuang Li, Antonio Torralba, Joshua B. Tenenbaum, Igor Mordatch
- **Year:** 2023 (ICML 2024)
- **Paper:** https://arxiv.org/abs/2305.14325
- **Code:** https://github.com/composable-models/llm_multiagent_debate
- **Key Findings:** The foundational "society of minds" paper. Multiple LLM instances propose and debate their individual responses over multiple rounds. Significantly enhances mathematical and strategic reasoning, reduces hallucinations. The approach treats different instances of the same LLM as a "multiagent society" where members generate and critique each other's outputs.
- **Application to Self-Evolving Framework:** This is the baseline architecture for productive disagreement. A self-evolving framework should implement multi-round debate as a standard creative refinement mechanism. The key innovation is that debate is not about finding consensus but about surfacing the strongest ideas through adversarial pressure.

### 6.2 LLM Review: Enhancing Creative Writing via Blind Peer Review Feedback
- **Authors:** Weiyue Li, Mingxiao Song, Zhenda Shen, et al.
- **Year:** 2026
- **Paper:** https://arxiv.org/abs/2601.08003
- **Key Findings:** Addresses a critical problem: multi-agent frameworks that improve reasoning through interaction can paradoxically hinder creativity by inducing content homogenization. Proposes "Blind Peer Review" -- agents exchange targeted feedback while revising independently, preserving divergent creative trajectories. On the SciFi-100 benchmark, LLM Review consistently outperforms multi-agent baselines. Smaller models with this framework can surpass larger single-agent models, suggesting interaction structure may substitute for model scale.
- **Application to Self-Evolving Framework:** The content homogenization warning is critical. If agents directly see and respond to each other's outputs, they tend to converge. The "blind peer review" pattern -- agents receive feedback but revise independently -- preserves diversity while still enabling improvement. This should be the default creative refinement protocol in a self-evolving framework.

### 6.3 LLM-based Multi-Agent Poetry Generation in Non-Cooperative Environments
- **Authors:** Ran Zhang, Steffen Eger
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2409.03659
- **Key Findings:** Introduces non-cooperative interactions alongside cooperative ones to encourage diversity in poetry generation. Evaluated on 96K generated poems. For training-based agents: 3.0-3.7 percentage point increase in diversity, 5.6-11.3 pp increase in novelty. Non-homogeneous agent ensembles further enhance diversity by 7.0-17.5 pp. However, prompting-based agents show decreased lexical diversity over time and do not maintain group-based divergence.
- **Application to Self-Evolving Framework:** Non-cooperative (competitive) dynamics actively boost novelty and diversity. A self-evolving framework should not only have agents cooperate but also compete. The decrease in diversity over time for prompting-based agents is a warning about long-running creative sessions -- the framework needs periodic "reset" mechanisms or fresh agent injection to prevent creative stagnation.

### 6.4 OPTAGENT: Optimizing Multi-Agent LLM Interactions Through Verbal Reinforcement Learning
- **Authors:** Zhenyu Bi, Meng Lu, Yang Li, et al.
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2510.18032
- **Key Findings:** Proposes verbal reinforcement learning that dynamically constructs and refines multi-agent collaboration structures. Defines action spaces and a feedback mechanism evaluating communication robustness and coherence throughout debate. Addresses the problem that existing collaboration structures suppress correct but less dominant agent contributions. Outperforms single-agent prompting and state-of-the-art multi-agent frameworks on reasoning, creative writing, scientific reasoning, and numerical sorting.
- **Application to Self-Evolving Framework:** The suppression of minority contributions is a direct threat to creativity. A self-evolving framework should implement mechanisms that protect and amplify minority viewpoints, even (especially) when they contradict the majority. OPTAGENT's verbal RL approach for optimizing collaboration structure could be used to dynamically adjust how agents interact based on whether the current task requires convergent or divergent thinking.

### 6.5 MultiAgent Collaboration Attack: Investigating Adversarial Attacks in LLM Collaborations via Debate
- **Authors:** Alfonso Amayuelas, Xianjun Yang, et al.
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2406.14711
- **Key Findings:** Evaluates multi-agent debate networks under adversarial influence. Highlights the importance of a model's persuasive ability in influencing others. Explores inference-time methods to generate more compelling arguments and prompt-based mitigation as a defensive strategy.
- **Application to Self-Evolving Framework:** Understanding adversarial dynamics is relevant not just for security but for creativity. A "controlled adversary" agent that deliberately challenges the majority could serve as a creativity catalyst. The finding about persuasive ability suggests that creative leadership in multi-agent systems may depend on an agent's ability to make novel ideas compelling, not just generate them.

---

## 7. Self-Evolving and Co-Evolutionary Agent Systems

### 7.1 Google AI Co-Scientist
- **Source:** Google Research, 2025
- **URL:** https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/
- **Architecture:** Six specialized agents: Generation (creates hypotheses via self-play scientific debate), Reflection (evaluates and critiques), Ranking (tournament-style evaluation using Elo ratings), Evolution (iterative refinement), Proximity (relevance assessment), Meta-review (oversight). A Supervisor agent manages resource allocation.
- **Key Findings:** Self-play debates among agents generate diverse perspectives. Test-time compute scaling improves quality -- more reasoning time yields better results. Elo ratings correlate positively with correctness. Successfully produced novel drug repurposing candidates for acute myeloid leukemia validated in wet lab experiments.
- **Application to Self-Evolving Framework:** The Google Co-Scientist architecture is the closest existing system to what a self-evolving creative framework needs. The key innovations to adopt: (1) Elo-based tournament ranking for comparing creative outputs, (2) self-play debate for generating diverse perspectives, (3) the Evolution agent that explicitly refines ideas across generations, (4) Supervisor-level resource allocation that determines which creative directions to invest more compute in.

### 7.2 Self-Evolving Multi-Agent Collaboration Networks for Software Development (EvoMAC)
- **Authors:** (ICLR 2025)
- **Paper:** https://arxiv.org/abs/2410.16946
- **Key Findings:** Introduces textual backpropagation -- using text-based environmental feedback to update agent behavior analogous to gradient descent in neural networks. The system iteratively adapts both agents and their connections during test time. Features a coding team (feed-forward), testing team (target proxy for feedback), and updating team (textual backpropagation). Outperforms previous state-of-the-art by 26-35% on software benchmarks.
- **Application to Self-Evolving Framework:** Textual backpropagation is a breakthrough concept for self-evolving systems. Instead of updating model weights, the system updates agent prompts and interaction patterns based on textual feedback about creative output quality. A self-evolving creative framework could implement "creative backpropagation" -- when a creative output fails evaluation, the system traces back through the agent interactions that produced it and adjusts those interaction patterns.

### 7.3 Multi-Agent Evolve: LLM Self-Improve through Co-evolution
- **Authors:** Yixing Chen, Yiding Wang, Siqi Zhu, et al.
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2510.23595
- **Key Findings:** Three cooperative yet competing roles from a single LLM: Proposer (generates questions), Solver (produces answers), Judge (evaluates both). Creates a self-rewarding loop enabling improvement without external supervision. The Proposer receives a "difficulty reward" inversely proportional to solver success, creating an adversarial dynamic. Achieves 4.54% average improvement across 20 benchmarks without any human-annotated data.
- **Application to Self-Evolving Framework:** The adversarial co-evolution pattern is directly applicable to creativity. A "Creative Proposer" that is rewarded for generating challenges that the "Creative Solver" struggles with would naturally push toward increasingly creative problem formulations. The self-rewarding loop eliminates the need for external creativity judges, making the system fully autonomous.

### 7.4 IDVSCI: Internal Discussion and Vote Scientists
- **Authors:** Weilun Yu, Shixiang Tang, et al.
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2506.18348
- **Key Findings:** Dynamic Knowledge Exchange mechanism enabling iterative feedback among agents, and a Dual-Diversity Review paradigm simulating heterogeneous expert evaluation. These components jointly promote deeper reasoning and generation of more creative and impactful scientific ideas. Outperforms AI Scientist and VIRSCI across multiple benchmarks.
- **Application to Self-Evolving Framework:** The Dual-Diversity Review -- evaluating ideas from multiple diverse perspectives simultaneously -- prevents premature convergence. A self-evolving framework should implement multi-criteria creative evaluation where the same idea is assessed on novelty, feasibility, surprise, usefulness, and aesthetic value by different evaluator agents.

### 7.5 Evaluating Novelty in AI-Generated Research Plans Using Multi-Workflow LLM Pipelines
- **Authors:** Devesh Saraogi, Rohit Singhee, Dhruv Kumar
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2601.09714
- **Key Findings:** Benchmarks five reasoning architectures for generating novel research plans. Decomposition-based and long-context workflows achieve mean novelty of 4.17/5, while reflection-based approaches score only 2.33/5. High-performing workflows maintain feasibility without sacrificing creativity. Results vary across research domains.
- **Application to Self-Evolving Framework:** Reflection alone is not sufficient for novelty -- this confirms the DoT problem. Decomposition (breaking problems into sub-problems) and long-context processing (maintaining broad awareness) are more effective for creative generation than iterative self-reflection. A self-evolving framework should prefer decomposition-based creative strategies over reflection-based ones.

---

## 8. Creativity Metrics and Evaluation

### 8.1 CreativityPrism: A Holistic Evaluation Framework for Large Language Model Creativity
- **Authors:** Zhaoyi Joey Hou, Bowei Alvin Zhang, et al.
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2510.20091
- **Key Findings:** Consolidates eight tasks across divergent thinking, creative writing, and logical reasoning into a three-dimensional taxonomy: Quality, Novelty, and Diversity. Evaluated 17 state-of-the-art LLMs. Key finding: high performance in one creative dimension or domain rarely generalizes to others. Novelty metrics often show weak or negative correlations with other metrics. Proprietary LLMs dominate creative writing and reasoning by 15% over open-source, but offer no advantage in divergent thinking.
- **Application to Self-Evolving Framework:** The finding that creativity dimensions are largely independent means a self-evolving framework needs separate evaluation mechanisms for quality, novelty, and diversity. Optimizing for one will not automatically improve the others. The framework should track all three dimensions and explicitly balance them based on the current creative objective.

### 8.2 Is Temperature the Creativity Parameter of Large Language Models?
- **Authors:** Max Peeperkorn, Tom Kouwenhoven, Dan Brown, Anna Jordanous
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2405.00492
- **Key Findings:** Tests the common claim using four creativity conditions: novelty, typicality, cohesion, and coherence. Temperature is only weakly correlated with novelty and moderately correlated with incoherence. No relationship with cohesion or typicality. The influence of temperature on creativity is far more nuanced than the "creativity parameter" claim suggests.
- **Application to Self-Evolving Framework:** Simply turning up temperature is not a viable creativity strategy. A self-evolving framework should not rely on sampling temperature as its primary creativity lever. Instead, structural interventions (diverse agents, adversarial debate, persona conditioning) are far more effective. Temperature may serve as a fine-tuning knob within a broader creative architecture.

### 8.3 Large Language Models Show Both Individual and Collective Creativity Comparable to Humans
- **Authors:** Luning Sun, Yuzhuo Yuan, Yuan Yao, et al.
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2412.03151
- **Key Findings:** Benchmarks LLMs against both individual humans and groups of humans across 13 creative tasks in three domains. Best LLMs (Claude, GPT-4) rank in the 52nd percentile against individual humans. LLMs excel in divergent thinking and problem solving but lag in creative writing. When queried 10 times, an LLM's collective creativity equals 8-10 humans. Each additional two LLM responses equal one extra human.
- **Application to Self-Evolving Framework:** The "collective creativity" finding is actionable: generating multiple diverse outputs and selecting the best is a valid strategy. A self-evolving framework should implement ensemble creativity -- have multiple agents generate solutions, then use evaluation agents to select the most creative ones. The 10-query = 8-10 humans equivalence provides a concrete scaling law for creative output.

### 8.4 Humanlike Cognitive Patterns as Emergent Phenomena in Large Language Models
- **Authors:** Zhisheng Tang, Mayank Kejriwal
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2412.15501
- **Key Findings:** Systematic review across decision-making, reasoning, and creativity. LLMs exhibit some human-like biases but not all. A distinct dichotomy in creativity: LLMs excel in language-based creative tasks (storytelling) but struggle with divergent thinking tasks requiring real-world context. LLMs hold considerable potential as collaborators augmenting human creativity in human-machine problem-solving settings.
- **Application to Self-Evolving Framework:** The finding that LLMs struggle with creativity requiring real-world context suggests that creative agents need grounding mechanisms -- access to real-world data, tool use, and environmental feedback. Purely text-based creative generation has limits. A self-evolving framework should integrate external information sources into its creative process.

### 8.5 Rethinking Creativity Evaluation: A Critical Analysis
- **Source:** https://arxiv.org/pdf/2508.05470
- **Key Findings:** Challenges existing creativity evaluation approaches. LLMs may encourage mid-level novelty but rarely produce radically original ideas, reinforcing combinatorial rather than conceptual creativity.

### 8.6 Guilford's Divergent Thinking Dimensions (Applied in Multiple Papers)

The standard framework for measuring divergent thinking, used across multiple papers reviewed:

| Dimension | Definition | How to Measure in Multi-Agent Systems |
|-----------|-----------|--------------------------------------|
| **Fluency** | Number of ideas generated | Count of unique proposals per session |
| **Flexibility** | Number of different categories of ideas | Cluster analysis of semantic embeddings |
| **Originality** | Statistical rarity of ideas | Inverse frequency in training data / prior outputs |
| **Elaboration** | Level of detail in ideas | Depth of specification in proposals |

---

## 9. Creative Applications of Multi-Agent Systems

### 9.1 ComposerX: Multi-Agent Symbolic Music Composition with LLMs
- **Authors:** Qixin Deng, Qikai Yang, et al.
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2404.18081
- **Key Findings:** Multi-agent approach significantly improves music composition quality over single-agent LLMs. Agents decompose the complex creative task into manageable sub-tasks (melody, harmony, rhythm).
- **Application to Self-Evolving Framework:** Creative task decomposition -- breaking a complex creative task into specialized sub-tasks handled by different agents -- is a general pattern applicable beyond music.

### 9.2 BookWorld: From Novels to Interactive Agent Societies for Creative Story Generation
- **Authors:** Yiting Ran, Xintao Wang, et al.
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2504.14538
- **Key Findings:** Constructs multi-agent societies from book characters for creative story generation. Achieves 75.36% win rate over previous methods while maintaining fidelity to source material.
- **Application to Self-Evolving Framework:** Character-based personas grounded in rich narrative contexts produce better creative output than generic role descriptions. A self-evolving framework could derive agent personas from historical examples of creative thinkers or problem solvers.

### 9.3 FilmAgent: A Multi-Agent Framework for End-to-End Film Automation
- **Authors:** Zhenran Xu, Longyue Wang, et al.
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2501.12909
- **Key Findings:** Simulates directors, screenwriters, actors, and cinematographers collaborating through iterative feedback and revision. Despite using the less advanced GPT-4o, the multi-agent system surpasses the single-agent o1 model, demonstrating the advantage of well-coordinated collaboration.
- **Application to Self-Evolving Framework:** Multi-agent coordination with role specialization can outperform more powerful single agents. This supports investing in agent orchestration quality over raw model capability.

### 9.4 Evaluating Creativity and Deception in LLMs: A Simulation Framework for Multi-Agent Balderdash
- **Authors:** Parsa Hejabi, Elnaz Rahmati, et al.
- **Year:** 2024
- **Paper:** https://arxiv.org/abs/2411.10422
- **Code:** https://github.com/ParsaHejabi/Simulation-Framework-for-Multi-Agent-Balderdash
- **Key Findings:** Uses the game Balderdash to evaluate creative and deceptive capabilities. Assesses ability to produce plausible but fictitious definitions (creativity) and to identify correct definitions (reasoning). Novel game-based evaluation framework.
- **Application to Self-Evolving Framework:** Game-based evaluation of creativity is an underexplored approach. A self-evolving framework could use creative games as training environments where agents develop creative skills through play rather than through direct optimization.

### 9.5 Igniting Creative Writing in Small Language Models
- **Authors:** Xiaolong Wei, Bo Lu, et al.
- **Year:** 2025
- **Paper:** https://arxiv.org/abs/2508.21476
- **Code:** https://github.com/weixiaolong94-hub/Igniting-Creative-Writing-in-Small-Language-Models
- **Key Findings:** Multi-agent rejection sampling framework for creative tasks. A principle-guided LLM-as-a-Judge with adversarial training and reflection yields superior creative generation quality with better training efficiency and less dependence on human-annotated data.
- **Application to Self-Evolving Framework:** The adversarial training of the judge agent is directly relevant. In a self-evolving framework, the creativity evaluator should itself evolve through adversarial pressure -- it should become harder to impress over time, pushing the creative agents to produce increasingly novel outputs.

---

## 10. Key Implementations and Repositories

| Repository | Description | URL |
|-----------|-------------|-----|
| **Multi-Agents-Debate** | MAD framework for divergent thinking | https://github.com/Skytliang/Multi-Agents-Debate |
| **AgentVerse** | Multi-agent deployment for task-solving and simulation | https://github.com/OpenBMB/AgentVerse |
| **MultiAgent-Research-Ideator** | Multi-agent dialogues for scientific ideation | https://github.com/g6000/MultiAgent-Research-Ideator |
| **LLM Multiagent Debate** | ICML 2024 multiagent debate framework | https://github.com/composable-models/llm_multiagent_debate |
| **Brainstormers** | Suite of brainstorming agents (SCAMPER, Six Hats, etc.) | https://github.com/Azzedde/brainstormers |
| **CoQuest** | LLM agent system for research co-creation | https://github.com/yiren-liu/coquest |
| **MachineSoM** | Exploring collaboration mechanisms (ACL 2024) | https://github.com/zjunlp/MachineSoM |
| **SMoA** | Sparse mixture-of-agents for diverse thinking | https://github.com/David-Li0406/SMoA |
| **Balderdash Framework** | Game-based creativity evaluation | https://github.com/ParsaHejabi/Simulation-Framework-for-Multi-Agent-Balderdash |
| **Creative Writing SLMs** | Multi-agent rejection sampling for creativity | https://github.com/weixiaolong94-hub/Igniting-Creative-Writing-in-Small-Language-Models |
| **Awesome-Self-Evolving-Agents** | Curated survey of self-evolving agents | https://github.com/EvoAgentX/Awesome-Self-Evolving-Agents |

---

## 11. Synthesis: Design Principles for Creative Multi-Agent Systems

Based on the 40+ papers reviewed, the following design principles emerge for building creative multi-agent systems:

### Principle 1: Diversity is the Primary Driver of Creativity

Multiple papers converge on this finding. Diversity manifests in several forms:
- **Model diversity:** Use heterogeneous LLMs to avoid "shared imagination" bias (Zhou et al., 2024)
- **Persona diversity:** Persona-conditioned agents produce +4.1 diversity gain (Doudkin et al., 2025)
- **Value diversity:** Different value systems lead to more creative principles, with diminishing returns at extremes (Huang et al., 2025)
- **Critic diversity:** More important than generator diversity for feasibility (Ueda et al., 2025)

### Principle 2: Structure Matters More Than Individual Capability

The collaboration structure determines creative output more than individual agent capability:
- Collaboration strategies outweigh individual traits (ACL 2024 MachineSoM)
- GPT-4o multi-agent beats single o1 (FilmAgent, 2025)
- Smaller models with good structure surpass larger single models (LLM Review, 2026)
- Decomposition-based workflows achieve 4.17/5 novelty vs. 2.33/5 for reflection (Saraogi et al., 2025)

### Principle 3: Balance Convergence and Divergence

Creative systems need both divergent exploration and convergent synthesis:
- Too much convergence causes content homogenization (LLM Review, 2026)
- Too much divergence causes instability (Huang et al., 2025)
- "Modest" levels of adversarial debate are optimal (Liang et al., 2023)
- Separate-then-together brainstorming outperforms pure collaboration (Straub et al., 2025)

### Principle 4: Implement the Csikszentmihalyi Loop

Creativity requires three interacting components:
- **Individual agents** that generate variations
- **Field agents** that evaluate and select promising variations
- **Domain knowledge** that preserves and transmits validated innovations
- Agents receiving field feedback generate more creative artifacts (Imasato et al., 2024)

### Principle 5: Prevent Degeneration-of-Thought

Self-reflection alone leads to creative stagnation:
- The DoT problem means confident agents cannot self-generate novel thoughts (Liang et al., 2023)
- Reflection-based approaches score poorly on novelty (Saraogi et al., 2025)
- Non-cooperative dynamics boost novelty by 5.6-11.3 pp (Zhang & Eger, 2024)
- Blind peer review preserves divergent trajectories (Li et al., 2026)

### Principle 6: Creativity is Multi-Dimensional and Non-Transferable

High creativity in one dimension does not predict high creativity in another:
- Quality, novelty, and diversity are largely independent (CreativityPrism, 2025)
- LLMs excel at divergent thinking but lag in creative writing (Sun et al., 2024)
- Temperature has weak influence on true creativity (Peeperkorn et al., 2024)
- General intelligence poorly predicts creative capability (LiveIdeaBench, 2024)

### Principle 7: Adversarial Dynamics are Creativity Catalysts

Controlled conflict improves creative output:
- Debate forces agents to inspect rather than replicate peer reasoning
- Non-cooperative environments increase diversity by 7-17.5 pp (Zhang & Eger, 2024)
- "Difficulty rewards" create productive adversarial pressure (MAE, 2025)
- Adversarial training of judges pushes creative quality higher (Wei et al., 2025)

---

## 12. Application to a Self-Evolving Multi-Agent Framework

### Recommended Architecture

Based on this literature review, a self-evolving multi-agent creative framework should implement:

```
+------------------------------------------------------------------+
|                     CREATIVE SUPERVISOR                           |
|  - Allocates resources to creative vs. execution phases           |
|  - Monitors creativity metrics (novelty, diversity, quality)      |
|  - Triggers mode switches (diverge / converge / evaluate)         |
+------------------------------------------------------------------+
        |                    |                    |
        v                    v                    v
+----------------+  +----------------+  +------------------+
| GENERATION     |  | EVALUATION     |  | EVOLUTION        |
| AGENTS         |  | AGENTS (Field) |  | AGENTS           |
|                |  |                |  |                  |
| - Diverse      |  | - Diverse      |  | - Textual        |
|   personas     |  |   evaluators   |  |   backprop       |
| - Heterogeneous|  | - Multi-criteria|  | - Elo ranking   |
|   models       |  |   (novelty,    |  | - Adversarial    |
| - SCAMPER/     |  |    quality,    |  |   co-evolution   |
|   Six Hats     |  |    diversity)  |  | - Difficulty     |
|   rotation     |  | - Blind review |  |   rewards        |
+----------------+  +----------------+  +------------------+
        |                    |                    |
        v                    v                    v
+------------------------------------------------------------------+
|                   DOMAIN KNOWLEDGE BASE                           |
|  - Validated creative outputs (accumulated innovations)           |
|  - Abstraction hierarchy for cross-domain combination             |
|  - Agent-data graph (ResearchTown style)                          |
|  - IBIS-structured idea trees                                     |
+------------------------------------------------------------------+
```

### Key Implementation Strategies

1. **Separate-Then-Together Creative Protocol**
   - Phase 1 (Diverge): 3-5 persona-conditioned agents brainstorm independently
   - Phase 2 (Cross-pollinate): Agents share outputs via blind review
   - Phase 3 (Synthesize): Creative director agent integrates best ideas
   - Phase 4 (Evaluate): Multi-criteria evaluation with diverse critic agents

2. **Anti-Stagnation Mechanisms**
   - Monitor information entropy of agent outputs; inject adversarial agents when entropy drops
   - Periodic persona rotation to prevent creative ruts
   - Non-cooperative agent pairs that compete on novelty
   - "Difficulty reward" for agents that pose challenges others cannot solve

3. **Creativity-Preserving Verification**
   - Use Chain of Verification (CoVe) rather than DoLa during creative phases
   - Implement "creativity mode" that relaxes factual constraints during ideation
   - Use RAG for grounding without suppressing divergent thinking

4. **Self-Evolving Creative Capability**
   - Elo tournament ranking for comparing creative outputs across generations
   - Textual backpropagation to update agent prompts based on creative evaluation feedback
   - Adversarial judge training -- evaluators that become harder to impress over time
   - Track which agent combinations produce the most creative outputs and reinforce those patterns

5. **Measurable Creativity Targets**
   - Track Guilford dimensions: fluency, flexibility, originality, elaboration
   - Maintain separate metrics for quality, novelty, and diversity (they are independent)
   - Use k-means clustering + information entropy for diversity measurement
   - Benchmark against human creative performance (target: 75th+ percentile)
   - Use LLM-as-a-judge calibrated against human gold standards

### What Remains Unsolved

Based on this review, the following are open challenges:

1. **Transformational creativity** remains out of reach. Current systems achieve combinatorial and exploratory creativity but cannot fundamentally alter their conceptual frameworks.

2. **Creative persistence over time.** Prompting-based agents show decreased diversity over extended sessions. Long-running self-evolving systems will face this problem acutely.

3. **Creativity-accuracy tradeoff.** The tension between being creative (generating novel ideas) and being correct (generating feasible ideas) lacks a principled resolution.

4. **Unified evaluation.** No single benchmark captures the full spectrum of creativity. Different dimensions require different metrics and they often negatively correlate.

5. **Scaling laws for creativity.** While we know that 10 LLM queries approximate 8-10 humans in collective creativity, the scaling behavior for more agents and more interactions is unknown.

---

## References (Full List)

1. Lin, Y.C. et al. (2025). "Creativity in LLM-based Multi-Agent Systems: A Survey." EMNLP 2025. arXiv:2505.21116
2. Liang, T. et al. (2023). "Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate." arXiv:2305.19118
3. Bellemare-Pepin, A. et al. (2024). "Divergent Creativity in Humans and Large Language Models." arXiv:2405.13012
4. Imasato, N. et al. (2024). "Creative Agents: Simulating the Systems Model of Creativity with Generative Agents." arXiv:2411.17065
5. Doudkin, A. et al. (2025). "The Spark Effect: On Engineering Creative Diversity in Multi-Agent AI Systems." arXiv:2510.15568
6. Ueda, K. et al. (2025). "Exploring Design of Multi-Agent LLM Dialogues for Research Ideation." arXiv:2507.08350
7. Chen, N. et al. (2025). "Beyond Brainstorming: What Drives High-Quality Scientific Ideas?" arXiv:2508.04575
8. Du, Y. et al. (2023). "Improving Factuality and Reasoning in Language Models through Multiagent Debate." ICML 2024. arXiv:2305.14325
9. Li, W. et al. (2026). "LLM Review: Enhancing Creative Writing via Blind Peer Review Feedback." arXiv:2601.08003
10. Zhang, R. & Eger, S. (2024). "LLM-based Multi-Agent Poetry Generation in Non-Cooperative Environments." arXiv:2409.03659
11. Gu, T. et al. (2024). "LLMs Can Realize Combinatorial Creativity." arXiv:2412.14141
12. Hou, Z.J. et al. (2025). "CreativityPrism: A Holistic Evaluation Framework for LLM Creativity." arXiv:2510.20091
13. Ruan, K. et al. (2024). "LiveIdeaBench: Evaluating LLMs' Divergent Thinking Capabilities." arXiv:2412.17596
14. Peeperkorn, M. et al. (2024). "Is Temperature the Creativity Parameter of LLMs?" arXiv:2405.00492
15. Sun, L. et al. (2024). "LLMs Show Both Individual and Collective Creativity Comparable to Humans." arXiv:2412.03151
16. Huang, M. et al. (2025). "On the Dynamics of Multi-Agent LLM Communities Driven by Value Diversity." arXiv:2512.10665
17. Chen, W. et al. (2024). "AgentVerse: Facilitating Multi-Agent Collaboration and Exploring Emergent Behaviors." ICLR 2024. arXiv:2308.10848
18. Li, D. et al. (2024). "SMoA: Improving Multi-agent LLMs with Sparse Mixture-of-Agents." arXiv:2411.03284
19. Straub, N. et al. (2025). "Persona-based Multi-Agent Collaboration for Brainstorming." arXiv:2512.04488
20. Yu, H. et al. (2024). "ResearchTown: Simulator of Human Research Community." arXiv:2412.17767
21. Bi, Z. et al. (2025). "OPTAGENT: Optimizing Multi-Agent LLM Interactions Through Verbal Reinforcement Learning." arXiv:2510.18032
22. Hejabi, P. et al. (2024). "Evaluating Creativity and Deception in LLMs: Multi-Agent Balderdash." arXiv:2411.10422
23. Zhou, Y. et al. (2024). "Shared Imagination: LLMs Hallucinate Alike." arXiv:2407.16604
24. Franceschelli, G. & Musolesi, M. (2024). "Creative Beam Search: LLM-as-a-Judge For Improving Response Generation." arXiv:2405.00099
25. Tang, Z. & Kejriwal, M. (2024). "Humanlike Cognitive Patterns as Emergent Phenomena in LLMs." arXiv:2412.15501
26. Shahhosseini, F. et al. (2025). "LLMs for Scientific Idea Generation: A Creativity-Centered Survey." arXiv:2511.07448
27. Banerjee, M. et al. (2025). "Does Less Hallucination Mean Less Creativity?" arXiv:2512.11509
28. Wei, X. et al. (2025). "Igniting Creative Writing in Small Language Models." arXiv:2508.21476
29. Deng, Q. et al. (2024). "ComposerX: Multi-Agent Symbolic Music Composition with LLMs." arXiv:2404.18081
30. Ran, Y. et al. (2025). "BookWorld: From Novels to Interactive Agent Societies." arXiv:2504.14538
31. Xu, Z. et al. (2025). "FilmAgent: A Multi-Agent Framework for End-to-End Film Automation." arXiv:2501.12909
32. Becker, J. (2024). "Multi-Agent LLMs for Conversational Task-Solving." arXiv:2410.22932
33. Yu, W. et al. (2025). "IDVSCI: Dynamic Knowledge Exchange and Dual-diversity Review." arXiv:2506.18348
34. Saraogi, D. et al. (2025). "Evaluating Novelty in AI-Generated Research Plans Using Multi-Workflow LLM Pipelines." arXiv:2601.09714
35. Chen, Y. et al. (2025). "Multi-Agent Evolve: LLM Self-Improve through Co-evolution." arXiv:2510.23595
36. EvoMAC (2025). "Self-Evolving Multi-Agent Collaboration Networks for Software Development." ICLR 2025. arXiv:2410.16946
37. Google Research (2025). "Accelerating Scientific Breakthroughs with an AI Co-Scientist." https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/
38. Yang, S. et al. (2025). "The Wisdom of Agent Crowds." arXiv:2505.06947
39. Amayuelas, A. et al. (2024). "MultiAgent Collaboration Attack." arXiv:2406.14711
40. Shanahan, M. & Clarke, C. (2023). "Evaluating LLM Creativity from a Literary Perspective." arXiv:2312.03746
41. Haase, J. et al. (2025). "S-DAT: A Multilingual Framework for Automated Divergent Thinking Assessment." arXiv:2505.09068
42. Wan, Q. et al. (2023). "It Felt Like Having a Second Mind: Investigating Human-AI Co-creativity." arXiv:2307.10811
43. Zhou, S. et al. (2025). "NAMeGEn: Creative Name Generation via Agent-based Goal Enhancement." arXiv:2511.15408
