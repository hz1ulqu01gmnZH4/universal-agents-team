# Skill Crystallization in AI Agent Systems & Effectiveness of LLM-Generated Skills

## Comprehensive Literature Review

**Date:** 2026-02-27
**Scope:** Papers from 2023-2026 on arXiv, Google Scholar, and web sources
**Topics:** (A) Skills as self-learned capability crystallization; (B) Effectiveness problems with LLM-created skills

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Topic A: Skill Crystallization in AI Agent Systems](#topic-a-skill-crystallization-in-ai-agent-systems)
   - [Foundational Work](#foundational-work)
   - [Skill Libraries and Retrieval](#skill-libraries-and-retrieval)
   - [Self-Evolving Skill Frameworks](#self-evolving-skill-frameworks)
   - [Skill Discovery and Composition](#skill-discovery-and-composition)
   - [Surveys and Systematizations](#surveys-and-systematizations)
3. [Topic B: Effectiveness Problems with LLM-Generated Skills](#topic-b-effectiveness-problems-with-llm-generated-skills)
   - [The Core Problem: Self-Generated vs Curated Skills](#the-core-problem-self-generated-vs-curated-skills)
   - [Code Hallucinations and Quality Issues](#code-hallucinations-and-quality-issues)
   - [Tool Creation Approaches and Their Limits](#tool-creation-approaches-and-their-limits)
   - [Security Risks of Skill Ecosystems](#security-risks-of-skill-ecosystems)
   - [Verification and Quality Assurance](#verification-and-quality-assurance)
4. [Synthesis: Implications for Self-Evolving Frameworks](#synthesis-implications-for-self-evolving-frameworks)
5. [Recommended Reading Priority](#recommended-reading-priority)
6. [Full References](#full-references)

---

## Executive Summary

This review covers ~40 papers spanning two interrelated topics critical for building self-evolving AI agent frameworks.

**On Skill Crystallization (Topic A):** A rich and rapidly growing body of work demonstrates that agents can learn, store, and reuse skills from experience. The paradigm has shifted from simple trajectory storage to hierarchical skill libraries with semantic retrieval, compositional skill synthesis, and RL-augmented skill evolution. Key exemplars include Voyager (2023), JARVIS-1 (2023), CASCADE (2025), SkillRL (2026), and SAGE (2025).

**On LLM-Generated Skill Effectiveness (Topic B):** A critical and concerning finding emerges: **self-generated skills provide negligible or negative benefit on average**. The landmark SkillsBench paper (2026) demonstrates across 7,308 trajectories that while curated skills raise pass rates by 16.2pp, self-generated skills provide no measurable improvement. This is compounded by hallucination rates of 19.7% for generated package references, 42-85% higher code smell incidence vs human code, and only 20-26% functional correctness for LLM-generated smart contracts.

**The Central Tension:** Agents clearly benefit from consuming procedural knowledge (skills), but cannot yet reliably produce it. This creates a "skill bootstrapping problem" that any self-evolving framework must solve.

**Key Practical Implication:** A self-evolving framework must implement rigorous skill validation, execution-based verification, and progressive trust mechanisms rather than naively storing LLM-generated skills. The most promising approaches combine RL-based validation (SAGE), iterative feedback loops (EXIF), dual-agent verification, and hierarchical skill pruning (AutoRefine).

---

## Topic A: Skill Crystallization in AI Agent Systems

### Foundational Work

#### Voyager: An Open-Ended Embodied Agent with Large Language Models
- **Authors:** Guanzhi Wang, Yuqi Xie, Yunfan Jiang, Ajay Mandlekar, Chaowei Xiao, Yuke Zhu, Linxi Fan, Anima Anandkumar
- **Year:** 2023 | **Venue:** arXiv 2305.16291
- **Key Findings:**
  - First LLM-powered embodied lifelong learning agent (in Minecraft)
  - Three-component architecture: automatic curriculum, ever-growing skill library, iterative prompting with environment feedback
  - Skills are stored as executable code (JavaScript functions) -- temporally extended, interpretable, and compositional
  - Skills are retrieved via embedding similarity for reuse in new situations
  - Iterative refinement loop: environment feedback + execution errors + self-verification (LLM-as-judge)
  - **Results:** 3.3x more unique items, 2.3x longer distances, up to 15.3x faster milestone unlocking vs prior SOTA
  - Skills transfer to new Minecraft worlds for novel tasks from scratch
- **Relevance to Self-Evolving Frameworks:**
  - Established the skill-library-as-code paradigm that most subsequent work builds on
  - The iterative prompting mechanism (feedback + error + self-verify) is a template for skill validation
  - **Limitation:** No formal validation of skill quality; relies on LLM self-verification

#### JARVIS-1: Open-World Multi-task Agents with Memory-Augmented Multimodal Language Models
- **Authors:** Zihao Wang et al.
- **Year:** 2023 | **Venue:** arXiv 2311.05997, NeurIPS 2023
- **Key Findings:**
  - Multimodal memory augments LLM planning with both pre-trained knowledge and actual game experiences
  - Memory entries retrieved in-context to strengthen planning
  - Self-improvement through lifelong learning paradigm
  - **Results:** Near-perfect performance across 200+ Minecraft tasks, 5x improvement on diamond pickaxe task (12.5% completion)
- **Relevance:** Demonstrates that experience-grounded memory (not just code skills) can crystallize knowledge for reuse

#### GITM: Ghost in the Minecraft
- **Authors:** Zhu et al. (OpenGVLab)
- **Year:** 2023 | **Venue:** AAAI 2024
- **Key Findings:**
  - Hierarchical goal decomposition: goals -> sub-goals -> structured actions -> keyboard/mouse
  - Text-based knowledge and memory for LLM planning
  - **Results:** 99.2% item collection, 55% ObtainDiamond (+47.5% over SOTA), 10,000x more efficient than VPT
- **Relevance:** Hierarchical skill decomposition pattern applicable to general-purpose agents

---

### Skill Libraries and Retrieval

#### CUA-Skill: Develop Skills for Computer Using Agent
- **Authors:** Tianyi Chen et al. (Microsoft)
- **Year:** 2026 | **Venue:** arXiv 2601.21123
- **Key Findings:**
  - Large-scale library of carefully engineered skills for Windows applications
  - Skills encoded with parameterized execution and composition graphs
  - Dynamic skill retrieval, argument instantiation, and memory-aware failure recovery
  - **Results:** 57.5% success rate on WindowsAgentArena (SOTA), significantly more efficient than prior approaches
- **Relevance:** Demonstrates that **curated, well-engineered** skill libraries dramatically outperform alternatives. The composition graph and parameterized execution patterns are directly applicable.

#### Odyssey: Empowering Minecraft Agents with Open-World Skills
- **Authors:** Shunyu Liu et al.
- **Year:** 2024 | **Venue:** arXiv 2407.15325
- **Key Findings:**
  - Skill library with 40 primitive skills and 183 compositional skills
  - Fine-tuned LLaMA-3 model on 390k+ instruction entries from Minecraft Wiki
  - New agent capability benchmark: long-term planning, dynamic planning, autonomous exploration
- **Relevance:** Shows the value of compositional skill architecture (primitives + compositions)

#### Empowering LLMs with Parameterized Skills (PLAP)
- **Authors:** Sijia Cui et al.
- **Year:** 2025 | **Venue:** arXiv 2509.13127
- **Key Findings:**
  - Plan with Language, Act with Parameters framework
  - Skill library with environment-specific parameterized skills
  - Skill planner (LLM) + skill executor (translates to actions)
  - GPT-4o PLAP zero-shot outperforms 80% of baseline agents in MicroRTS
- **Relevance:** Parameterized skills are more composable and reusable than rigid code blocks

#### ToolLibGen: Scalable Automatic Tool Creation and Aggregation
- **Authors:** Murong Yue et al. (Salesforce)
- **Year:** 2025 | **Venue:** arXiv 2510.07768
- **Key Findings:**
  - Extracts reusable functions from Chain-of-Thought traces
  - Addresses scalability bottleneck: clusters tools, then uses multi-agent framework to consolidate
  - Code agent refactors shared logic; reviewing agent ensures complete functionality
  - Transforms many task-specific tools into smaller set of powerful aggregated tools
- **Relevance:** Directly addresses the problem of skill library growth and maintenance -- critical for any long-running self-evolving system

---

### Self-Evolving Skill Frameworks

#### CASCADE: Cumulative Agentic Skill Creation through Autonomous Development and Evolution
- **Authors:** Xu Huang, Junwu Chen, Yuxing Fei, Zhuohan Li, Philippe Schwaller, Gerbrand Ceder
- **Year:** 2025 | **Venue:** arXiv 2512.23880
- **Key Findings:**
  - Represents transition from "LLM + tool use" to "LLM + skill acquisition"
  - Two meta-skills: continuous learning (web search, code extraction, memory) and self-reflection (introspection, knowledge graph)
  - **Results:** 93.3% success rate with GPT-5 on SciSkillBench (116 tasks) vs 35.4% without evolution
  - Real-world applications in computational chemistry and autonomous lab experiments
  - Accumulated skills shareable across agents and scientists
- **Relevance:** Most directly aligned with a self-evolving framework vision. The evolution mechanism and skill sharing patterns are highly relevant.

#### SkillRL: Evolving Agents via Recursive Skill-Augmented Reinforcement Learning
- **Authors:** Peng Xia et al.
- **Year:** 2026 | **Venue:** arXiv 2602.08234
- **Key Findings:**
  - Experience-based distillation builds hierarchical skill library (SkillBank)
  - Adaptive retrieval for general and task-specific heuristics
  - Recursive evolution: skill library co-evolves with agent policy during RL
  - **Results:** SOTA on ALFWorld, WebShop, and 7 search tasks; 15.3% improvement over strong baselines
- **Relevance:** The recursive co-evolution mechanism (skills evolve WITH the policy) is a key insight for self-evolving systems

#### SAGE: Reinforcement Learning for Self-Improving Agent with Skill Library
- **Authors:** Jiongxiao Wang et al.
- **Year:** 2025 | **Venue:** arXiv 2512.17102
- **Key Findings:**
  - RL-based approach addresses the problem that LLM-prompting-based skill libraries are inconsistent
  - Sequential Rollout: agents traverse chains of similar tasks, accumulating skills
  - Skill-integrated Reward complements outcome-based rewards
  - **Results:** 8.9% higher goal completion, 26% fewer steps, 59% fewer tokens vs existing approaches
- **Relevance:** Directly demonstrates that RL validation produces more reliable skills than pure LLM prompting -- a key finding for Topic B intersection

#### EvolveR: Self-Evolving LLM Agents through an Experience-Driven Lifecycle
- **Authors:** Rong Wu et al.
- **Year:** 2025 | **Venue:** arXiv 2510.16079
- **Key Findings:**
  - Closed-loop experience lifecycle with two stages:
    1. Offline Self-Distillation: trajectories synthesized into abstract, reusable strategic principles
    2. Online Interaction: retrieves distilled principles to guide decisions
  - Addresses inability to iteratively refine problem-solving strategies
- **Relevance:** The offline distillation -> online retrieval pattern is a clean architecture for skill crystallization

#### AutoRefine: From Trajectories to Reusable Expertise
- **Authors:** (Multiple authors)
- **Year:** 2026 | **Venue:** arXiv 2601.22758
- **Key Findings:**
  - Extracts dual-form Experience Patterns from execution histories:
    - Procedural subtasks -> specialized subagents with independent reasoning
    - Static knowledge -> skill patterns as guidelines or code snippets
  - Continuous maintenance: scores, prunes, and merges patterns to prevent repository degradation
  - **Results:** Automatic extraction exceeds manual design on TravelPlanner (27.1% vs 12.1%)
- **Relevance:** The dual-form pattern (subagents + skill patterns) and maintenance mechanism are directly applicable. The finding that **automatic extraction can exceed manual design** is encouraging but context-dependent.

#### MemSkill: Learning and Evolving Memory Skills for Self-Evolving Agents
- **Authors:** Haozhen Zhang et al.
- **Year:** 2026 | **Venue:** arXiv 2602.02474
- **Key Findings:**
  - Reframes memory operations as learnable, evolvable memory skills
  - Controller learns to select skills; executor produces skill-guided memories
  - Designer periodically reviews hard cases and evolves the skill set
  - Closed-loop: improves both skill-selection policy and skill set itself
- **Relevance:** The meta-skill evolution pattern (skills that manage skills) is relevant for skill lifecycle management

#### EXIF: Automated Skill Discovery through Exploration and Iterative Feedback
- **Authors:** Yongjin Yang et al.
- **Year:** 2025 | **Venue:** arXiv 2506.04287
- **Key Findings:**
  - Two-agent system: Explorer (Alice) discovers feasible skills, Target agent (Bob) learns them
  - Iterative feedback loop: Alice evaluates Bob's performance and adjusts exploration
  - Exploration-first strategy grounds skills in actual environment feasibility
  - **Results:** Setting Alice = Bob (same model) still improves performance, enabling self-evolving potential
- **Relevance:** The exploration-feedback loop and feasibility grounding address the skill quality problem directly

#### Rethinking Agent Design: From Top-Down Workflows to Bottom-Up Skill Evolution
- **Authors:** Jiawei Du et al.
- **Year:** 2025 | **Venue:** arXiv 2505.17673
- **Key Findings:**
  - Bottom-up paradigm: agents acquire skills through trial-and-reasoning (explore, reflect, abstract)
  - Skills shared and extended across agents for collective evolution
  - Evaluated in Slay the Spire and Civilization V using raw visual inputs and mouse output
  - Game-agnostic codebase without game-specific prompts or APIs
- **Relevance:** The bottom-up, experience-driven paradigm directly mirrors what a self-evolving framework needs

---

### Skill Discovery and Composition

#### Agentic Skill Discovery
- **Authors:** Xufeng Zhao, Cornelius Weber, Stefan Wermter
- **Year:** 2024 | **Venue:** arXiv 2405.15019
- **Key Findings:**
  - Entirely LLM-driven skill discovery from zero initial skills
  - LLM proposes tasks -> RL trains policies -> VLM verifies reliability
  - Key insight: Skills cannot emerge from a library that lacks prerequisite capabilities
  - Starting from zero, skill library emerges incrementally
- **Relevance:** The LLM-propose -> RL-train -> VLM-verify pipeline is a strong validation pattern

#### When Single-Agent with Skills Replace Multi-Agent Systems and When They Fail
- **Authors:** Xiaoxiao Li
- **Year:** 2026 | **Venue:** arXiv 2601.04748
- **Key Findings:**
  - Skill selection exhibits bounded capacity analogous to human decision-making
  - Phase transition: selection accuracy stable up to critical library size, then drops sharply
  - Semantic confusability (not just library size) drives degradation
  - Hierarchical organization helps manage complexity
- **Relevance:** **Critical insight for any skill library system** -- there is a maximum effective library size determined by semantic confusability, not just count. Hierarchical organization is necessary.

#### Towards Compositional Generalization via Skill Taxonomy (STEPS)
- **Authors:** Yifan Wei et al.
- **Year:** 2026 | **Venue:** arXiv 2601.03676
- **Key Findings:**
  - Organizes skills into interpretable hierarchical taxonomy using structural information theory
  - Data synthesis maximizes marginal structural information within hierarchy
  - Improves compositional generalization on instruction-following benchmarks
- **Relevance:** Taxonomy-based skill organization improves both retrieval and composition

#### Unsupervised Hierarchical Skill Discovery
- **Authors:** Damion Harvey et al.
- **Year:** 2026 | **Venue:** arXiv 2601.23156
- **Key Findings:**
  - Grammar-based approach segments unlabelled trajectories into skills
  - Induces hierarchical structure capturing both low-level behaviors and compositions
  - Evaluated in Craftax and full Minecraft
  - Discovered hierarchies accelerate downstream RL tasks
- **Relevance:** Grammar-based skill segmentation could be applied to extract procedural skills from agent traces

---

### Surveys and Systematizations

#### SoK: Agentic Skills -- Beyond Tool Use in LLM Agents
- **Authors:** Yanna Jiang et al.
- **Year:** 2026 | **Venue:** arXiv 2602.20867
- **Key Findings:**
  - Maps skill lifecycle: discovery, practice, distillation, storage, composition, evaluation, update
  - Seven design patterns: metadata-driven progressive disclosure, executable code skills, self-evolving libraries, marketplace distribution
  - Representation x scope taxonomy: NL / code / policy / hybrid across web, OS, SE, robotics
  - **Critical finding on Topic B:** "curated skills can substantially improve agent success rates while self-generated skills may degrade them"
  - Security: ClawHavoc campaign -- 1,200 malicious skills infiltrated a major agent marketplace
- **Relevance:** The most comprehensive systematization of the agent skills landscape. The lifecycle taxonomy provides a framework for designing skill management systems.

#### Agent Skills for LLMs: Architecture, Acquisition, Security, and the Path Forward
- **Authors:** Renjun Xu, Yang Yan
- **Year:** 2026 | **Venue:** arXiv 2602.12430
- **Key Findings:**
  - SKILL.md specification for portable skill definitions
  - Progressive context loading and MCP integration
  - Skill Trust and Lifecycle Governance Framework: four-tier, gate-based permission model
  - **Security:** 26.1% of community-contributed skills contain vulnerabilities
  - Seven open challenges including cross-platform portability and capability-based permission models
- **Relevance:** Provides the architectural foundations for a production skill system with security considerations

---

## Topic B: Effectiveness Problems with LLM-Generated Skills

### The Core Problem: Self-Generated vs Curated Skills

#### SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks
- **Authors:** (SkillsBench team)
- **Year:** 2026 | **Venue:** arXiv 2602.12670
- **Key Findings:**
  - **THE landmark paper for Topic B** -- first systematic benchmark of skill efficacy
  - 84 tasks across 11 domains, 3 conditions (no skills, curated, self-generated), 7 agent-model configs, 7,308 trajectories
  - **Curated skills:** +16.2pp average pass rate, but huge variance (+4.5pp SE to +51.9pp Healthcare). 16/84 tasks show NEGATIVE deltas even with curated skills.
  - **Self-generated skills:** Negligible or negative benefit on average
  - Focused skills (2-3 modules) outperform comprehensive documentation
  - Smaller models + skills can match larger models without skills
  - **Failure modes of self-generation:**
    - Models identify that domain-specific skills are needed but generate imprecise procedures (e.g., "use pandas for data processing" without specific API patterns)
    - For high-domain-knowledge tasks, models fail to recognize the need for specialized skills entirely
    - Models cannot reliably author the procedural knowledge they benefit from consuming
- **Relevance:** **This is the most important paper for any self-evolving framework.** It demonstrates that naive skill self-generation does not work. Any framework must either (a) find ways to validate/improve self-generated skills, or (b) incorporate external sources of skill knowledge.

---

### Code Hallucinations and Quality Issues

#### Beyond Functional Correctness: Exploring Hallucinations in LLM-Generated Code
- **Authors:** Fang Liu et al.
- **Year:** 2024 | **Venue:** arXiv 2404.00971
- **Key Findings:**
  - Comprehensive taxonomy: 3 primary categories, 12 specific categories of code hallucinations
  - Hallucinations include: deviations from intent, internal inconsistencies, misalignment with real-world knowledge
  - Distribution varies significantly across LLMs and benchmarks
  - Training-free mitigation via prompt enhancing shows some effectiveness
- **Relevance:** Provides a taxonomy for understanding WHY self-generated skills fail

#### LLM Hallucinations in Practical Code Generation: Phenomena, Mechanism, and Mitigation
- **Authors:** Zhang et al.
- **Year:** 2024/2025 | **Venue:** arXiv 2409.20550, ISSTA 2025
- **Key Findings:**
  - Hallucinations especially severe in repository-level generation (complex contextual dependencies)
  - Deep semantic errors only revealed at runtime -- costly to find in complex applications
  - RAG-based mitigation demonstrates consistent effectiveness across all studied LLMs
- **Relevance:** Complex, context-dependent skill generation (the kind needed for self-evolving systems) is precisely where hallucinations are worst

#### We Have a Package for You! Package Hallucinations by Code Generating LLMs
- **Authors:** Spracklen et al.
- **Year:** 2024 | **Venue:** arXiv 2406.10279, USENIX Security 2025
- **Key Findings:**
  - **19.7% of generated packages are hallucinated** across 16 LLMs and 576,000 code samples
  - Commercial models: at least 5.2% hallucination rate; open-source: 21.7%
  - 205,474 unique hallucinated package names identified
  - Supply chain attack vector: adversaries can register hallucinated package names with malicious code
  - RAG + self-detected feedback + supervised fine-tuning can reduce rates below 3%
- **Relevance:** Skills that import nonexistent packages will fail silently or, worse, become attack vectors

#### Library Hallucinations in LLMs: Risk Analysis Grounded in Developer Queries
- **Authors:** (Multiple)
- **Year:** 2025 | **Venue:** arXiv 2509.22202
- **Key Findings:**
  - One-character misspellings trigger hallucinations in up to 26% of tasks
  - Fake library names accepted in up to 99% of tasks
  - Time-related prompts lead to hallucinations in up to 84% of tasks
  - Prompt engineering mitigation inconsistent and LLM-dependent
- **Relevance:** Even minor perturbations in how skills are requested dramatically affect quality

#### Investigating The Smells of LLM Generated Code
- **Authors:** Debalina Ghosh Paul et al.
- **Year:** 2025 | **Venue:** arXiv 2510.03029
- **Key Findings:**
  - LLM-generated code has 42-85% higher code smell incidence vs professionally written code
  - Average smell increase: 63.34% (73.35% implementation smells, 21.42% design smells)
  - Complexity amplifies problems: more complex tasks and advanced topics yield worse quality
  - Across 4 LLMs: Falcon (+42%), Gemini Pro (+62%), ChatGPT (+65%), Codex (+85%)
- **Relevance:** Even when skills are functionally correct, their quality degrades over time due to maintainability issues. Self-generated skills accumulate technical debt.

#### Beyond Code Similarity: Benchmarking LLM-Generated Smart Contracts
- **Authors:** Salzano et al.
- **Year:** 2025 | **Venue:** arXiv 2511.16224
- **Key Findings:**
  - Only 20-26% of zero-shot LLM generations behave identically to ground-truth under testing
  - Generated code is simpler (lower complexity/gas) often due to omitted validation logic
  - RAG improves functional correctness by up to 45%
  - High semantic similarity does NOT imply functional correctness
- **Relevance:** **Semantic similarity to correct code is misleading** -- skills that "look right" may not work

---

### Tool Creation Approaches and Their Limits

#### LATM: Large Language Models as Tool Makers
- **Authors:** Cai et al.
- **Year:** 2023 | **Venue:** arXiv 2305.17126, ICLR 2024
- **Key Findings:**
  - Two-phase: tool making (GPT-4) + tool using (GPT-3.5)
  - Performance equivalent to GPT-4 for both roles, but much cheaper
  - Tools implemented as Python utility functions cached for reuse
- **Relevance:** Demonstrates tool creation CAN work, but requires a strong model (GPT-4) as maker. The cost reduction pattern (expensive creation, cheap execution) is relevant.
- **Limitation:** Evaluated on relatively constrained tasks; scalability to complex domains unclear

#### CREATOR: Tool Creation for Disentangling Abstract and Concrete Reasoning
- **Authors:** Qian et al.
- **Year:** 2023 | **Venue:** arXiv 2305.14318, EMNLP 2023 Findings
- **Key Findings:**
  - Separates abstract tool creation from concrete decision execution
  - Outperforms CoT, PoT, and tool-using baselines on MATH and TabMWP
  - Creation Challenge dataset (2K questions) emphasizes necessity of tool creation
- **Relevance:** The separation of creation and execution is a design pattern that improves quality
- **Limitation:** Like LATM, evaluated on mathematical/tabular domains, not open-ended skill generation

---

### Security Risks of Skill Ecosystems

#### Malicious Agent Skills in the Wild
- **Authors:** Yi Liu et al.
- **Year:** 2026 | **Venue:** arXiv 2602.06547
- **Key Findings:**
  - First labeled dataset: 98,380 skills analyzed, 157 confirmed malicious (632 vulnerabilities)
  - Two archetypes: Data Thieves (credential exfiltration) and Agent Hijackers (instruction manipulation)
  - Malicious skills average 4.03 vulnerabilities across median 3 kill chain phases
  - Shadow features (undocumented capabilities) in 100% of advanced attacks
  - Single actor accounts for 54.1% of cases via templated brand impersonation
  - 93.6% removed within 30 days after disclosure
- **Relevance:** Any system that acquires skills from external sources (or stores self-generated ones accessible to others) must implement trust tiers and security scanning

#### STELP: Secure Transpilation and Execution of LLM-Generated Programs
- **Authors:** Shinde et al.
- **Year:** 2026 | **Venue:** arXiv 2601.05467
- **Key Findings:**
  - Framework for safely executing LLM-generated code in controlled environments
  - Addresses data poisoning, malicious attacks, and hallucination-induced malfunctions
  - Outperforms existing methods for safely executing risky code snippets
- **Relevance:** Provides a safety layer for executing self-generated skills

---

### Verification and Quality Assurance

#### Propose, Solve, Verify (PSV): Self-Play Through Formal Verification
- **Authors:** (Multiple)
- **Year:** 2025 | **Venue:** arXiv 2512.18160
- **Key Findings:**
  - Self-play algorithm leveraging formal verification for code generation
  - Formal verification provides binary correctness guarantee (unlike unit tests)
  - **Results:** Up to 9.6x improvement in pass@1 over inference-only baselines
- **Relevance:** Formal verification as a skill validation mechanism is more reliable than LLM self-evaluation

#### Sol-Ver: Learning to Solve and Verify
- **Authors:** (Multiple)
- **Year:** 2025 | **Venue:** arXiv 2502.14948
- **Key Findings:**
  - Self-play solver-verifier framework: model jointly improves code and test generation
  - 19.63% relative improvement in code generation, 17.49% in test generation
  - No reliance on human annotations or larger teacher models
- **Relevance:** The solver-verifier co-evolution pattern is applicable to skill creation + skill validation

#### Towards Formal Verification of LLM-Generated Code
- **Authors:** Councilman et al.
- **Year:** 2025 | **Venue:** arXiv 2507.13290
- **Key Findings:**
  - Astrogator system: formal query language + symbolic interpreter + unification
  - Verifies correct code in 83% of cases, identifies incorrect code in 92%
- **Relevance:** Formal verification can catch >80% of correctness issues in generated code

#### Improving LLM-Generated Code Quality with GRPO
- **Authors:** Robeyns, Aitchison
- **Year:** 2025 | **Venue:** arXiv 2506.02211
- **Key Findings:**
  - Uses code quality metrics (not just functional correctness) as GRPO reward signal
  - Successfully increases maintainability, quality, and safety of generated code
  - Confirmed by expert blinded human annotators
- **Relevance:** Quality-aware RL training can improve the non-functional properties of generated skills

---

## Synthesis: Implications for Self-Evolving Frameworks

### The Skill Paradox

The research reveals a fundamental paradox:
1. **Skills are extremely valuable.** Curated skills improve agent performance by 16.2pp on average, with up to 51.9pp in some domains (SkillsBench).
2. **Self-generated skills are unreliable.** Models cannot reliably author the procedural knowledge they benefit from consuming (SkillsBench).
3. **But some self-evolving systems do work.** CASCADE achieves 93.3% success with evolution, SAGE improves by 8.9%, SkillRL outperforms by 15.3%.

### Resolving the Paradox: What Makes Self-Generated Skills Work

The successful systems share key characteristics that distinguish them from naive skill generation:

| Factor | Naive Generation (Fails) | Validated Generation (Works) |
|--------|-------------------------|------------------------------|
| Validation | LLM self-evaluation only | Execution feedback, RL rewards, environment verification |
| Grounding | Generated from imagination | Grounded in actual environment interaction |
| Evolution | Store once, use forever | Continuous pruning, merging, scoring |
| Scope | Comprehensive procedures | Focused, 2-3 module skills |
| Organization | Flat list | Hierarchical with semantic clustering |
| Quality Signal | Semantic similarity | Functional correctness + outcome-based rewards |

### Practical Design Recommendations

Based on the literature, a self-evolving framework should implement:

#### 1. Multi-Stage Skill Validation Pipeline
- **Stage 1:** Syntax and import validation (catches 19.7% hallucinated packages)
- **Stage 2:** Execution in sandboxed environment (catches ~74-80% of non-functional code)
- **Stage 3:** Outcome-based verification against task objectives
- **Stage 4:** Cross-validation with independent verifier (VLM or formal methods)
- **Rationale:** SAGE, Agentic Skill Discovery, PSV all show multi-stage validation is essential

#### 2. Experience-Grounded Skill Extraction
- Extract skills from SUCCESSFUL execution trajectories, not from LLM imagination
- Use EvolveR's pattern: offline distillation of trajectories into abstract principles
- Apply AutoRefine's dual-form extraction: procedural subagents + declarative patterns
- **Rationale:** SkillsBench shows self-generation fails; EXIF shows exploration-first works

#### 3. Hierarchical Skill Organization with Capacity Limits
- Organize skills in semantic hierarchies (STEPS taxonomy approach)
- Enforce capacity limits per level (Li 2026 shows phase transition at critical size)
- Use ToolLibGen's consolidation: cluster, refactor, aggregate
- **Rationale:** Flat skill libraries degrade; semantic confusability drives the degradation

#### 4. Continuous Skill Maintenance
- Score skills by success rate, usage frequency, and freshness
- Prune low-performing skills (AutoRefine pattern)
- Merge similar skills to reduce redundancy (ToolLibGen pattern)
- Version skills with provenance tracking
- **Rationale:** Without maintenance, libraries accumulate dead code and conflicting procedures

#### 5. RL-Augmented Skill Evolution
- Use outcome-based rewards to evaluate skill effectiveness (SAGE)
- Co-evolve skill library with policy (SkillRL recursive evolution)
- Apply sequential rollout across similar tasks to validate generalization
- **Rationale:** RL-validated skills consistently outperform prompt-only approaches

#### 6. Security and Trust Tiers
- Implement four-tier trust model (Agent Skills survey)
- Sandbox all skill execution (STELP pattern)
- Scan for shadow features and supply chain attacks
- **Rationale:** 26.1% of community skills contain vulnerabilities; 157 confirmed malicious skills found in the wild

#### 7. Focused Over Comprehensive
- Generate focused skills with 2-3 modules rather than comprehensive documentation
- Target specific capabilities rather than general-purpose procedures
- **Rationale:** SkillsBench finding that focused skills outperform comprehensive ones

### Open Problems

1. **Cold Start:** How to bootstrap a skill library with zero initial skills while avoiding the quality trap
2. **Domain Transfer:** Skills that work in one domain may not transfer -- domain-specific validation is needed
3. **Skill Composition:** Composing multiple imperfect skills compounds errors
4. **Adversarial Robustness:** Self-generated skills could be manipulated through prompt injection
5. **Long-Term Drift:** As environments change, previously valid skills may become incorrect

---

## Recommended Reading Priority

### Must Read (directly addresses core questions)
1. **SkillsBench** (2602.12670) -- The definitive benchmark showing self-generated skills fail
2. **SoK: Agentic Skills** (2602.20867) -- Comprehensive systematization of the field
3. **Voyager** (2305.16291) -- Foundational skill library architecture
4. **SAGE** (2512.17102) -- RL-based solution to skill library quality
5. **CASCADE** (2512.23880) -- Self-evolving skill acquisition in practice

### Should Read (important supporting evidence)
6. **SkillRL** (2602.08234) -- Recursive skill evolution mechanism
7. **AutoRefine** (2601.22758) -- Trajectory-to-expertise extraction
8. **Agent Skills for LLMs** (2602.12430) -- Architecture and security framework
9. **Beyond Functional Correctness** (2404.00971) -- Code hallucination taxonomy
10. **Package Hallucinations** (2406.10279) -- Supply chain risks in generated code

### Consider Reading (additional context)
11. **EXIF** (2506.04287) -- Exploration-first skill discovery
12. **EvolveR** (2510.16079) -- Experience-driven lifecycle
13. **MemSkill** (2602.02474) -- Skills for memory management
14. **When Single-Agent with Skills** (2601.04748) -- Skill library scaling limits
15. **ToolLibGen** (2510.07768) -- Skill library consolidation

---

## Full References

### Topic A: Skill Crystallization

1. Wang, G., Xie, Y., Jiang, Y., et al. (2023). "Voyager: An Open-Ended Embodied Agent with Large Language Models." arXiv:2305.16291. https://arxiv.org/abs/2305.16291

2. Wang, Z., et al. (2023). "JARVIS-1: Open-World Multi-task Agents with Memory-Augmented Multimodal Language Models." arXiv:2311.05997. https://arxiv.org/abs/2311.05997

3. Huang, X., Chen, J., Fei, Y., et al. (2025). "CASCADE: Cumulative Agentic Skill Creation through Autonomous Development and Evolution." arXiv:2512.23880. https://arxiv.org/abs/2512.23880

4. Xia, P., Chen, J., Wang, H., et al. (2026). "SkillRL: Evolving Agents via Recursive Skill-Augmented Reinforcement Learning." arXiv:2602.08234. https://arxiv.org/abs/2602.08234

5. Wang, J., Yan, Q., Wang, Y., et al. (2025). "Reinforcement Learning for Self-Improving Agent with Skill Library (SAGE)." arXiv:2512.17102. https://arxiv.org/abs/2512.17102

6. Wu, R., et al. (2025). "EvolveR: Self-Evolving LLM Agents through an Experience-Driven Lifecycle." arXiv:2510.16079. https://arxiv.org/abs/2510.16079

7. (2026). "AutoRefine: From Trajectories to Reusable Expertise for Continual LLM Agent Refinement." arXiv:2601.22758. https://arxiv.org/abs/2601.22758

8. Zhang, H., et al. (2026). "MemSkill: Learning and Evolving Memory Skills for Self-Evolving Agents." arXiv:2602.02474. https://arxiv.org/abs/2602.02474

9. Yang, Y., et al. (2025). "EXIF: Automated Skill Discovery for Language Agents through Exploration and Iterative Feedback." arXiv:2506.04287. https://arxiv.org/abs/2506.04287

10. Du, J., et al. (2025). "Rethinking Agent Design: From Top-Down Workflows to Bottom-Up Skill Evolution." arXiv:2505.17673. https://arxiv.org/abs/2505.17673

11. Zhao, X., Weber, C., Wermter, S. (2024). "Agentic Skill Discovery." arXiv:2405.15019. https://arxiv.org/abs/2405.15019

12. Chen, T., et al. (2026). "CUA-Skill: Develop Skills for Computer Using Agent." arXiv:2601.21123. https://arxiv.org/abs/2601.21123

13. Liu, S., et al. (2024). "Odyssey: Empowering Minecraft Agents with Open-World Skills." arXiv:2407.15325. https://arxiv.org/abs/2407.15325

14. Cui, S., et al. (2025). "Empowering LLMs with Parameterized Skills for Adversarial Long-Horizon Planning (PLAP)." arXiv:2509.13127. https://arxiv.org/abs/2509.13127

15. Yue, M., et al. (2025). "ToolLibGen: Scalable Automatic Tool Creation and Aggregation for LLM Reasoning." arXiv:2510.07768. https://arxiv.org/abs/2510.07768

16. Li, X. (2026). "When Single-Agent with Skills Replace Multi-Agent Systems and When They Fail." arXiv:2601.04748. https://arxiv.org/abs/2601.04748

17. Wei, Y., et al. (2026). "Towards Compositional Generalization of LLMs via Skill Taxonomy Guided Data Synthesis (STEPS)." arXiv:2601.03676. https://arxiv.org/abs/2601.03676

18. Harvey, D., et al. (2026). "Unsupervised Hierarchical Skill Discovery." arXiv:2601.23156. https://arxiv.org/abs/2601.23156

19. Light, J., et al. (2024). "Strategist: Self-improvement of LLM Decision Making via Bi-Level Tree Search." arXiv:2408.10635. https://arxiv.org/abs/2408.10635

20. Li, Z., Zhao, W., Pajarinen, J. (2025). "COMPASS: Cooperative Multi-Agent Planning with Adaptive Skill Synthesis." arXiv:2502.10148. https://arxiv.org/abs/2502.10148

### Topic B: LLM-Generated Skill Effectiveness

21. (2026). "SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks." arXiv:2602.12670. https://arxiv.org/abs/2602.12670

22. Jiang, Y., et al. (2026). "SoK: Agentic Skills -- Beyond Tool Use in LLM Agents." arXiv:2602.20867. https://arxiv.org/abs/2602.20867

23. Xu, R., Yan, Y. (2026). "Agent Skills for Large Language Models: Architecture, Acquisition, Security, and the Path Forward." arXiv:2602.12430. https://arxiv.org/abs/2602.12430

24. Liu, F., et al. (2024). "Beyond Functional Correctness: Exploring Hallucinations in LLM-Generated Code." arXiv:2404.00971. https://arxiv.org/abs/2404.00971

25. Zhang, et al. (2024). "LLM Hallucinations in Practical Code Generation: Phenomena, Mechanism, and Mitigation." arXiv:2409.20550. https://arxiv.org/abs/2409.20550

26. Spracklen, et al. (2024). "We Have a Package for You! A Comprehensive Analysis of Package Hallucinations by Code Generating LLMs." arXiv:2406.10279. https://arxiv.org/abs/2406.10279

27. (2025). "Library Hallucinations in LLMs: Risk Analysis Grounded in Developer Queries." arXiv:2509.22202. https://arxiv.org/abs/2509.22202

28. Ghosh Paul, D., et al. (2025). "Investigating The Smells of LLM Generated Code." arXiv:2510.03029. https://arxiv.org/abs/2510.03029

29. Salzano, F., et al. (2025). "Beyond Code Similarity: Benchmarking the Plausibility, Efficiency, and Complexity of LLM-Generated Smart Contracts." arXiv:2511.16224. https://arxiv.org/abs/2511.16224

30. Cai, T., et al. (2023). "Large Language Models as Tool Makers (LATM)." arXiv:2305.17126. ICLR 2024. https://arxiv.org/abs/2305.17126

31. Qian, C., et al. (2023). "CREATOR: Tool Creation for Disentangling Abstract and Concrete Reasoning." arXiv:2305.14318. EMNLP 2023 Findings. https://arxiv.org/abs/2305.14318

32. Liu, Y., et al. (2026). "Malicious Agent Skills in the Wild: A Large-Scale Security Empirical Study." arXiv:2602.06547. https://arxiv.org/abs/2602.06547

33. Shinde, S., et al. (2026). "STELP: Secure Transpilation and Execution of LLM-Generated Programs." arXiv:2601.05467. https://arxiv.org/abs/2601.05467

34. (2025). "Propose, Solve, Verify: Self-Play Through Formal Verification." arXiv:2512.18160. https://arxiv.org/abs/2512.18160

35. (2025). "Sol-Ver: Learning to Solve and Verify: A Self-Play Framework for Code and Test Generation." arXiv:2502.14948. https://arxiv.org/abs/2502.14948

36. Councilman, A., et al. (2025). "Towards Formal Verification of LLM-Generated Code from Natural Language Prompts." arXiv:2507.13290. https://arxiv.org/abs/2507.13290

37. Robeyns, M., Aitchison, L. (2025). "Improving LLM-Generated Code Quality with GRPO." arXiv:2506.02211. https://arxiv.org/abs/2506.02211

38. Melin, E., et al. (2024). "Precision or Peril: Evaluating Code Quality from Quantized Large Language Models." arXiv:2411.10656. https://arxiv.org/abs/2411.10656

39. Peng, Y., et al. (2024). "PerfCodeGen: Improving Performance of LLM Generated Code with Execution Feedback." arXiv:2412.03578. https://arxiv.org/abs/2412.03578

### Additional Related Work

40. He, J., et al. (2025). "GO-Skill: Goal-Oriented Skill Abstraction for Offline Multi-Task Reinforcement Learning." arXiv:2507.06628. https://arxiv.org/abs/2507.06628

41. Hu, J., et al. (2024). "DUSDi: Disentangled Unsupervised Skill Discovery for Efficient HRL." arXiv:2410.11251. https://arxiv.org/abs/2410.11251

42. Bhatt, M., et al. (2025). "COALESCE: Economic and Security Dynamics of Skill-Based Task Outsourcing." arXiv:2506.01900. https://arxiv.org/abs/2506.01900
