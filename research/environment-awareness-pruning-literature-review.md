# Literature Review: Environment Awareness, Context Management, Self-Pruning, and Hierarchical Protection for Self-Evolving Agent Frameworks

**Date:** 2026-02-28
**Scope:** ~65 papers and systems across four interconnected research topics
**Purpose:** Ground the Universal Agents Framework in prior work on environment change detection, context window management, capability pruning, and safe self-modification hierarchies.

---

## 1. Introduction

Self-evolving multi-agent frameworks face a fundamental paradox: they must be capable enough to handle diverse tasks, yet lean enough to operate within fixed resource constraints (context windows, token budgets, latency limits). As these systems grow---accumulating skills, tools, and knowledge---they risk becoming bloated, slow, and fragile. Worse, when the underlying model or environment changes silently, accumulated capabilities may degrade without warning.

This literature review examines four critical dimensions of this challenge:

1. **Environment Change Detection and Adaptation** -- How agents detect when their underlying model, tools, or environment have changed, and how they adapt.
2. **Context Window Efficiency and Management** -- How to compose and compress context for maximum agent effectiveness.
3. **Self-Pruning and Lean-Down Strategies** -- How to determine what capabilities to shed when the system becomes overloaded.
4. **Hierarchical Importance for Safe Self-Modification** -- How to create protection rings ensuring core capabilities survive pruning cycles.

These topics are deeply interconnected: effective pruning requires understanding context window dynamics, safe self-modification requires environment awareness, and context management is the mechanism through which pruning decisions manifest.

---

## 2. Environment Change Detection and Adaptation

### 2.1 The Silent Model Drift Problem

The foundational work on LLM behavioral drift is Chen, Zaharia & Zou (2023), "How is ChatGPT's behavior changing over time?" [arXiv:2307.09009]. This study evaluated GPT-3.5 and GPT-4 across seven diverse tasks between March and June 2023, revealing dramatic performance shifts:

- GPT-4's accuracy on prime number identification dropped from **84% to 51%** in just three months.
- Directly executable code generation plummeted from **52% to 10%** for GPT-4.
- GPT-4's willingness to follow chain-of-thought prompting declined significantly.
- Multi-hop question performance fluctuated in opposite directions for GPT-3.5 vs GPT-4.

The key finding was that **the behavior of the "same" LLM service can change substantially in a relatively short amount of time**, and these changes are opaque to users. The authors provide evidence that a common factor behind many behavior drifts is declining instruction-following capability. This has direct implications for any framework that depends on stable model behavior across sessions.

**Quantitative finding:** Performance can vary by **30+ percentage points** between model versions on the same task, with no external signal that the model has changed.

### 2.2 Concept Drift Detection Methods

While direct LLM behavioral drift detection remains nascent, the broader concept drift literature provides established detection methodologies:

**Loss-based drift detection** is the most applicable to LLM agents. Aguiar & Cano (2023) present a comprehensive analysis of concept drift locality [arXiv:2311.06396], introducing categorization by locality and scale with 2,760 benchmark problems. They compare 9 state-of-the-art drift detectors across various difficulty levels, finding that drift locality significantly influences detector performance.

**Clustering-based detection** was validated by Mishra & Stamp (2025) [arXiv:2502.14135], who used MiniBatch K-Means clustering with silhouette coefficients to identify temporal concept drift. Their **drift-aware retraining** achieved classification accuracy within 1% of periodic retraining while being far more computationally efficient---a pattern directly applicable to agent self-monitoring.

**Feature relevance analysis** for explaining drift was proposed by Siirtola & Roning (2023) [arXiv:2301.08453], who showed that monitoring how feature relevance changes over time can not only detect drift but also **explain the reason** for it, when a limited number of typical reasons are predefined. This "explain the drift" approach is particularly valuable for agent systems that need to understand why performance degraded, not just that it did.

### 2.3 Self-Monitoring and Self-Evaluation

Chiu, Zhang & van der Schaar (2025) introduce a framework for **strategic self-improvement** for competitive agents [arXiv:2512.04988] that identifies three core capabilities: **metacognition** (accurate self-assessment of skills), **competitive awareness** (modeling rivals and market dynamics), and **long-horizon strategic planning**. Their simulations show that agents prompted with reasoning capabilities learn to strategically self-improve and adapt to changing conditions.

The **AgentTrace** framework (AlSayyad, Huang & Pal, 2026) [arXiv:2602.10133] provides structured runtime observability across three surfaces: operational, cognitive, and contextual. Unlike traditional logging, AgentTrace captures continuous introspectable traces designed for agent security, accountability, and real-time monitoring---precisely the infrastructure needed for drift detection.

For production monitoring, emerging evaluation platforms (DeepEval, InspectAI, Phoenix, GALILEO) increasingly incorporate regression detection through continuous evaluation during development and after deployment. Agent simulation tools like LangWatch enable testing of multi-step agents with realistic goal-driven behavior, catching failures that ordinary evaluation datasets miss, such as **multi-turn reasoning errors, memory drift, or tool misuse**.

### 2.4 Implications for Self-Benchmarking

A self-evolving agent framework needs:

1. **Canary tasks**: Small, fast benchmark tasks run regularly to detect capability shifts (inspired by Chen et al.'s diverse task battery).
2. **Silhouette-based drift detection**: Tracking clustering metrics on agent outputs to detect distributional shifts without labeled data.
3. **Feature relevance monitoring**: Tracking which capabilities are most relied upon and detecting when their relevance patterns shift.
4. **Structured trace capture**: Runtime observability at operational, cognitive, and contextual levels.

### 2.5 Gaps in Current Research

- No existing work directly addresses self-benchmarking by LLM agents to detect changes in their own underlying model.
- Concept drift literature focuses on data streams, not on the model-as-a-service drift scenario.
- No standard benchmark suite exists specifically designed for agents to test their own capabilities.
- The interaction between model updates and accumulated agent state (skills, memories) is unexplored.

---

## 3. Context Window Efficiency and Management

### 3.1 The Lost-in-the-Middle Problem

Liu et al. (2023), "Lost in the Middle: How Language Models Use Long Contexts" [arXiv:2307.03172], established the seminal finding that **performance is often highest when relevant information occurs at the beginning or end of the input context**, and significantly degrades when models must access information in the middle. Published in TACL 2024, this paper demonstrated:

- Performance drops of **>30%** when relevant information shifts from edges to middle positions.
- The effect persists even in models explicitly designed for long contexts.
- A U-shaped attention pattern where beginning and ending tokens receive disproportionate attention.

**Root cause**: Hsieh et al. (2024) [arXiv:2406.16008] connected this to intrinsic **attention bias** in transformer architectures. Their "Found in the Middle" calibration mechanism achieves up to **15 percentage point** improvement by scaling positional hidden states. Yu et al. (2024) [arXiv:2406.02536] further showed that modifying just **one dimension** of hidden states can improve performance by up to **15.2%**.

**Multi-hop implications**: Baker et al. (2024) [arXiv:2412.10079] demonstrated that in multi-hop QA settings, performance degrades not only with respect to distance from context edges but also **between** pieces of information---a critical finding for multi-agent systems where related information may be scattered across the context.

**Distance bias**: Tian et al. (2024) [arXiv:2410.14641] introduce LongPiBench showing that while most modern models are now robust against simple lost-in-the-middle issues, **significant biases related to spacing of relevant information** persist.

The **Tree of Agents** framework (Yu et al., 2025) [arXiv:2509.06436] addresses lost-in-the-middle by segmenting input into chunks processed by independent agents, each generating local cognition before dynamic collaborative reasoning along tree-structured paths, achieving comparable performance to models like Gemini 1.5 Pro using only LLaMA3.1-8B.

### 3.2 Context Compression Techniques

**Semantic compression**: Fei et al. (2023) [arXiv:2312.09571] propose semantic compression inspired by information theory source coding, enabling generalization to texts **6-8x longer** without fine-tuning.

**Recurrent Context Compression (RCC)**: Huang et al. (2024) [arXiv:2406.06110] achieve compression rates of up to **32x** on text reconstruction with BLEU4 scores near 0.95, and nearly **100% accuracy** on passkey retrieval at sequence length 1M. They also identify the problem of poor model responses when both instructions and context are compressed.

**Dynamic prompt compression**: Hu et al. (2025) [arXiv:2504.11004] model prompt compression as a Markov Decision Process, training a DCP-Agent to sequentially remove redundant tokens. Their hierarchical compression strategy outperforms state-of-the-art techniques especially at higher compression rates.

**Frequency-domain compression**: Kai et al. (2025) [arXiv:2505.00570] propose FreqKV, exploiting the observation that context information concentrates in low-frequency components, extending LLaMA-2-7B context to **256K tokens** with stable perplexity.

**SWE-Pruner** (Wang et al., 2026) [arXiv:2601.16746] is particularly relevant as a **self-adaptive context pruning framework** for coding agents. It achieves **23-54% token reduction** on agent tasks while even **improving success rates**, by training a lightweight 0.6B parameter neural "skimmer" to dynamically select relevant lines given an explicit goal.

### 3.3 Context Engineering for Agents

The emerging field of "context engineering" defines the problem as filling the context window with **just the right information at each step** of an agent's trajectory. Anthropic's engineering guidance identifies four core strategies:

1. **Write**: Adding information to the context (tool outputs, memories, instructions).
2. **Select**: Choosing what to include via relevance ranking---episodic memories for behavioral examples, procedural memories for steering, semantic memories for facts.
3. **Compress**: Reducing resolution through summarization, hierarchical or recursive.
4. **Isolate**: Splitting work across multiple context windows via sub-agents.

Key challenges identified in practice include **context poisoning** (hallucinations entering context), **context distraction** (overwhelming training signals), and **context confusion** (superfluous context influencing responses). The concept of **context rot**---decreasing recall accuracy as token count increases---further motivates aggressive context management.

JetBrains Research identifies that good context engineering means finding **the smallest possible set of high-signal tokens** that maximize the likelihood of a desired outcome.

### 3.4 Memory Management for Agents

**Agentic Memory (AgeMem)** (Yu et al., 2026) [arXiv:2601.01885] unifies long-term and short-term memory management directly into the agent's policy, exposing memory operations as tool-based actions. Agents autonomously decide **what and when to store, retrieve, update, summarize, or discard** information. Their three-stage progressive reinforcement learning strategy demonstrates improved task performance and more efficient context usage across five long-horizon benchmarks.

**AgentSys** (Wen et al., 2026) [arXiv:2602.07398] brings OS-inspired memory isolation to LLM agents, organizing agents hierarchically where external data and subtask traces **never enter the main agent's memory**. Only schema-validated return values cross boundaries. This alone cuts attack success to **2.19%** while slightly improving benign utility.

### 3.5 Instruction Scaling Limits

A critical finding for multi-agent frameworks: **performance consistently degrades as the number of simultaneous instructions increases**.

Harada et al. (2025) [arXiv:2509.21051] show that accuracy drops predictably with instruction count, proposing regression models that can estimate performance on unseen instruction combinations.

Jaroslawicz et al. (2025) [arXiv:2507.11538] introduce IFScale, finding that even frontier models achieve only **68% accuracy at 500 simultaneous instructions**, with distinct performance degradation patterns correlated to model size and reasoning capability. Crucially, they find **bias toward earlier instructions**---later instructions are more likely to be ignored.

Elder, Duesterwald & Muthusamy (2025) [arXiv:2510.14842] show instruction-following drops by up to **7 points for just 2 instructions** and further with 10, attributing degradation to **tension and conflict** between instructions.

Fu et al. (2025) [arXiv:2505.14810] identify a **fundamental tension between reasoning capacity and controllability**---models that reason more effectively often struggle more to comply with user directives.

**Quantitative finding for framework design:** At 77.67% compliance with a single level-I constraint, dropping to 32.96% at level IV (Ye et al., 2025) [arXiv:2505.07591]. This means frameworks should minimize simultaneous constraints on any single agent.

---

## 4. Self-Pruning and Lean-Down Strategies

### 4.1 The Tool Overload Problem

The most directly applicable finding for self-evolving frameworks: **too many tools degrade LLM performance dramatically**.

**RAG-MCP** (Gan & Sun, 2025) [arXiv:2505.03275] demonstrates that naive tool presentation causes severe selection accuracy problems. Their retrieval-augmented approach triples tool selection accuracy (**43.13% vs 13.62% baseline**) while cutting prompt tokens by **>50%**. This quantifies the penalty of bloated tool catalogs.

**JSPLIT** (Antonioni et al., 2025) [arXiv:2510.14537] introduces taxonomy-driven tool filtering for MCP, organizing tools hierarchically and including only the most relevant based on query and taxonomy structure. As tool count grows substantially, JSPLIT **improves** tool selection accuracy beyond even having all tools available.

**Dynamic ReAct** (Gaurav et al., 2025) [arXiv:2509.20386] proposes five progressive architectures for operating with extensive MCP tool sets, achieving up to **50% reduction in tool loading** while maintaining task completion accuracy through search-and-load mechanisms.

**Instruction-Tool Retrieval (ITR)** (Franko, 2025) [arXiv:2602.17046] is the most aggressive approach, reducing per-step context tokens by **95%**, improving correct tool routing by **32% relative**, and cutting end-to-end episode cost by **70%** versus monolithic baselines. This enables agents to run **2-20x more loops** within context limits.

**MemTool** (Lumer et al., 2025) [arXiv:2507.21428] enables dynamic tool/MCP management across multi-turn conversations. Reasoning LLMs achieve **90-94% tool removal efficiency** (correctly discarding no-longer-needed tools), while medium models manage only 0-60%, highlighting the capability-dependent nature of self-pruning.

**Scaling reality check**: At approximately 400-500 tokens per tool definition, 50 tools consume 20,000-25,000 tokens. Users report system failure at 200+ tools, making dynamic loading not optional but essential.

### 4.2 Skill Library Management

**Voyager** (Wang et al., 2023) [arXiv:2305.16291] established the paradigm of ever-growing skill libraries, where an LLM agent in Minecraft continuously discovers and stores skills as executable code. Voyager achieves **3.3x more unique items**, **2.3x longer distances**, and **15.3x faster** milestone completion. However, the Voyager skill library only grows---it has **no pruning mechanism**.

**PSEC** (Liu et al., 2025) [arXiv:2502.05932] proposes Parametric Skill Expansion and Composition, maintaining a **manageable** skill library by encoding skills as LoRA modules. A context-aware module dynamically activates different skills to handle new tasks, providing a mechanism for selective skill loading without wholesale inclusion.

**LEGO-Prover** (Wang et al., 2023) [arXiv:2310.00656] uses a growing skill library of verified lemmas for theorem proving, generating over **20,000 skills** with measured improvement from 47.1% to 50.4% success rate. This demonstrates that skill libraries can grow very large while remaining beneficial, but only with proper retrieval mechanisms.

**The Skill Paradox** (referenced from project's prior review): Curated skills improve performance by +16.2 percentage points, while self-generated skills provide negligible or negative benefit. This directly motivates quality-based pruning: skills should be validated and only retained if they demonstrably help.

### 4.3 Agent Skill Security and Lifecycle

**Xu & Yan (2026)** survey agent skills comprehensively [arXiv:2602.12430], proposing a **Skill Trust and Lifecycle Governance Framework** with a **four-tier, gate-based permission model** mapping skill provenance to graduated deployment capabilities. They identify that 26.1% of community-contributed skills contain vulnerabilities, and propose seven open challenges including cross-platform skill portability and capability-based permission models.

**Jiang et al. (2026)** [arXiv:2602.20867] map the full skill lifecycle: discovery, practice, distillation, storage, composition, evaluation, and **update**. They introduce seven design patterns including **self-evolving libraries** and **marketplace distribution**, and critically survey evidence that curated skills substantially improve agent success rates **while self-generated skills may degrade them**.

**Liu et al. (2026)** [arXiv:2602.06547] confirm that **malicious skills average 4.03 vulnerabilities** across a median of three kill chain phases, establishing that skill pruning is not just a performance concern but a **security imperative**.

### 4.4 Dynamic Loading/Unloading Patterns

**ScaleMCP** (Lumer et al., 2025) [arXiv:2505.06416] provides dynamic MCP tool management through CRUD operations with MCP servers as the single source of truth, plus auto-synchronizing tool storage. Their Tool Document Weighted Average embedding strategy emphasizes critical tool components during retrieval.

**AgentFlux** (Kadekodi et al., 2025) [arXiv:2510.00229] decomposes tool-calling into tool selection and argument generation with **dedicated LoRA adapters** dynamically loaded per step. Their decoupled fine-tuning improves tool calling accuracy by **46%** over base models.

**EIGHT architecture** (Wang & Zhang, 2025) [arXiv:2511.04548] demonstrates that with guaranteed module independence, even a monolithic application within a single process can **dynamically load, unload, or modify any part at runtime**---precisely the pattern needed for self-evolving frameworks.

**Anthropic's code execution with MCP** demonstrates that executing logic in a sandboxed environment can reduce token usage from **150,000 to 2,000 tokens** (98.7% savings), showing that offloading computation outside the context window is far more efficient than trying to fit everything inside it.

### 4.5 On-Demand Multi-Task Sparsity

Huang et al. (2025) [arXiv:2511.19986] introduce on-demand multi-task sparsity for edge deployment, decomposing model weights into reusable block-granular units and aligning sparse structures across tasks to maximize overlap. By dynamically loading only the **differential set** of blocks for each new task, they achieve **6.6x faster task switching**. This weight-level approach complements the context-level approaches above.

---

## 5. Hierarchical Importance for Safe Self-Modification

### 5.1 Graceful Degradation in Adaptive Systems

Chu et al. (2024) [arXiv:2401.09678] formalize graceful degradation and recovery as **requirement-driven adaptation tasks** for cyber-physical systems: degradation weakens ideal requirements when conditions are adverse, recovery strengthens them when conditions improve. They treat weakening and strengthening as **dual operations** under a single adaptation method using Signal Temporal Logic (STL). This mathematical framework for managing capability levels under uncertainty directly maps to agent self-modification.

**Adaptable TeaStore** (Bliudze et al., 2024) [arXiv:2412.16060] distinguishes between **mandatory and optional services**, supports multiple component versions with varying resource requirements, and considers **outsourcing functionalities** to external providers with local cache mechanisms. Their catalog of adaptation scenarios includes component unavailability, traffic surges, and user-triggered reconfigurations---directly analogous to agent capability management.

**RAPID** (Yin et al., 2026) [arXiv:2602.06653] introduces **Physical Mask** as runtime signal for modality presence, enabling auto-configuration and **graceful degradation under sensor hot-plug events**. Policies continue executing when sensors are physically added or removed. This hardware-level pattern of detecting capability changes and adapting in real-time is a direct analog for agent tool management.

### 5.2 Self-Reconfiguration Paradigm

**ToolSelf** (Zhou et al., 2026) [arXiv:2602.07883] proposes the most directly relevant paradigm: **tool-driven runtime self-reconfiguration**. By abstracting configuration updates as a callable tool, ToolSelf unifies task execution and self-adjustment into a single action space. Agents autonomously update sub-goals, context, strategy, and toolbox, transforming from passive executors into **dual managers of both task and self**. Their Configuration-Aware Two-stage Training achieves **24.1% average performance gain** across diverse benchmarks.

**MorphAgent** (Lu et al., 2024) [arXiv:2410.15048] enables agents to dynamically evolve roles and capabilities through self-evolving profiles optimized via three key metrics, implementing a two-phase process (Profile Update + Task Execution) where agents continuously adapt based on task feedback.

**Lemon Agent** (Jiang et al., 2026) [arXiv:2602.07092] implements **hierarchical self-adaptive scheduling** operating at both orchestrator and worker layers, dynamically adjusting computational intensity based on task complexity. Their **three-tier progressive context management** strategy reduces redundancy while increasing information density, and their **self-evolving memory system** extracts multi-dimensional valid information from historical experiences.

### 5.3 Layered Protection Models

Drawing from operating systems design and modern agent security frameworks, several patterns emerge for hierarchical capability protection:

**The MAPE-K Model for MAS**: Nascimento, Alencar & Cowan (2023) [arXiv:2307.06187] anchor LLM-based multi-agent adaptation on the Monitor-Analyze-Plan-Execute-Knowledge (MAPE-K) loop, providing a proven framework for structured self-adaptation with explicit separation between monitoring (detecting change), analysis (understanding impact), planning (deciding response), and execution (making changes).

**AdaptiFlow** (Zemtsop Ndadji et al., 2025) [arXiv:2512.23499] implements three levels of autonomy as a hierarchy: **self-healing** (lowest, automatic recovery), **self-protection** (middle, threat mitigation), and **self-optimization** (highest, performance tuning). Each level has different triggering conditions and scope of permissible modifications. This maps naturally to agent capability rings.

**AgentSys's hierarchical memory isolation** (Wen et al., 2026) [arXiv:2602.07398] borrows from OS process isolation: main agents spawn worker agents in isolated contexts, with deterministic JSON parsing as the only permitted boundary crossing. This achieves both security and performance benefits simultaneously.

**The Skill Trust and Lifecycle Governance Framework** (Xu & Yan, 2026) [arXiv:2602.12430] proposes a **four-tier, gate-based permission model**:
- Tier 1: System-verified core skills (highest trust, never pruned)
- Tier 2: Community-validated skills (high trust, prunable only with replacement)
- Tier 3: User-contributed skills (moderate trust, freely prunable)
- Tier 4: Untested/external skills (low trust, sandboxed, prunable by default)

### 5.4 Capability Ceilings and Scaling Limits

Marin (2025) [arXiv:2510.21866] documents **empirical capability ceilings** in autoregressive LLMs: knowledge retrieval tasks show negligible accuracy improvement despite smooth loss reduction across 240x parameter scaling. Attention interventions cause **catastrophic performance collapse** rather than graceful degradation. This finding has critical implications:

- **Core capabilities should be validated at the model's actual capability level**, not assumed to scale.
- **Safe self-modification must account for catastrophic failure modes**, not just gradual degradation.
- **Parameter scaling beyond certain thresholds offers minimal gains**, motivating efficient capability composition over brute-force scaling.

### 5.5 The AI-45 Degree Law

Shanghai AI Lab's "AI-45 Degree Law" proposes that safety and capability must coevolve along a 45-degree diagonal trajectory, with red lines denoting irreversible, catastrophic risks that must never be crossed. This philosophical framework directly supports the concept of protected capability cores: some capabilities (self-monitoring, self-repair, alignment checking) must be treated as **invariants** that no self-modification cycle can touch.

---

## 6. Cross-Topic Synthesis

### 6.1 The Pruning-Monitoring-Context Triangle

These four topics form an interlocking system:

```
Environment Detection <---> Context Management
         |                         |
         v                         v
   Self-Pruning <-------> Hierarchical Protection
```

- **Detection informs pruning**: If the model has changed, skills calibrated to the old model may need re-validation or removal.
- **Context management enables pruning**: Every pruning decision manifests as a context composition decision (what to load, what to omit).
- **Hierarchical protection constrains pruning**: Not everything can be pruned---core capabilities must be protected.
- **Detection requires context**: Self-benchmarking tasks consume context window space, creating a tension between monitoring and task execution.

### 6.2 Key Quantitative Thresholds

| Metric | Threshold | Source |
|--------|-----------|--------|
| Model drift magnitude | Up to 33 percentage points between versions | Chen et al. 2023 |
| Lost-in-the-middle degradation | >30% accuracy drop for middle-positioned info | Liu et al. 2023 |
| Tool overload baseline accuracy | 13.62% with naive tool inclusion | Gan & Sun 2025 |
| Tool retrieval improvement | 3x accuracy with RAG-based selection | Gan & Sun 2025 |
| Context reduction possible | 95% per-step with ITR | Franko 2025 |
| Instruction degradation | 77.67% at Level I to 32.96% at Level IV | Ye et al. 2025 |
| Frontier model instruction limit | 68% accuracy at 500 instructions | Jaroslawicz et al. 2025 |
| Skill curation benefit | +16.2 pp for curated vs. negligible for self-generated | Prior project review |
| Skill vulnerability rate | 26.1% of community skills have vulnerabilities | Liu et al. 2026 |
| Context compression ratio | Up to 32x with 0.95 BLEU4 | Huang et al. 2024 |
| Self-reconfiguration gain | 24.1% average across benchmarks | Zhou et al. 2026 |
| Task switching speedup | 6.6x with differential loading | Huang et al. 2025 |
| Tool removal efficiency (reasoning LLMs) | 90-94% correct removal rate | Lumer et al. 2025 |

### 6.3 Emerging Design Patterns

**Pattern 1: Progressive Disclosure**
Load capabilities on demand rather than all at once. Start with a minimal system prompt and expand only as needed. This is supported by RAG-MCP, ITR, JSPLIT, Dynamic ReAct, and the SKILL.md specification.

**Pattern 2: Dual Managers**
Agents simultaneously manage their task and their own configuration (ToolSelf pattern). Self-modification is not a separate phase but an integrated action within the normal action space.

**Pattern 3: Hierarchical Isolation**
Use OS-inspired memory isolation between agent layers (AgentSys pattern). Main agents never see raw external data; only validated, schema-conformant summaries cross boundaries.

**Pattern 4: Canary-Based Drift Detection**
Maintain a small suite of capability tests (inspired by Chen et al.) that are run periodically. Performance changes trigger re-validation of accumulated capabilities.

**Pattern 5: Trust-Tiered Governance**
Assign trust levels to capabilities based on provenance, validation status, and usage history. Higher-trust capabilities require more evidence to prune; lower-trust ones are prunable by default.

---

## 7. Design Implications for the Universal Agents Framework

### 7.1 Environment Awareness Layer

The framework should implement:

1. **Model Fingerprinting**: Run a fixed battery of micro-benchmarks at session start to fingerprint the underlying model's current capabilities. Compare against stored fingerprints to detect model changes.
2. **Continuous Performance Monitoring**: Track success rates, latency, and output quality metrics per skill/tool. Apply silhouette-based drift detection to detect distributional shifts.
3. **Structured Trace Capture**: Implement AgentTrace-style logging at operational, cognitive, and contextual levels. Use traces for both security auditing and drift detection.
4. **Change-Triggered Revalidation**: When drift is detected, trigger targeted revalidation of affected capabilities before wholesale pruning.

### 7.2 Context Budget Management

Based on the quantitative findings:

1. **Target 3-5 tools per agent step** to avoid the severe degradation seen with larger tool sets (13.62% baseline accuracy).
2. **Place critical information at context edges** (beginning and end) to mitigate lost-in-the-middle effects.
3. **Use retrieval-based tool selection** rather than loading all tools, following RAG-MCP's 3x accuracy improvement pattern.
4. **Implement progressive context compression** using recursive summarization for history and SWE-Pruner-style task-aware pruning for current context.
5. **Budget context allocation**: Reserve fixed portions for system instructions (~10%), active tools (~20%), current task (~40%), and working memory (~30%).

### 7.3 Self-Pruning Protocol

1. **Skill Validation Pipeline**: Every skill must pass 4-stage validation (as identified in prior project research). Skills that fail validation after a model change are quarantined, not deleted.
2. **Usage-Based Retention**: Track skill usage frequency and success rate. Skills unused for N sessions or with declining success rates are candidates for archival (not deletion).
3. **Dynamic Tool Loading**: Implement JSPLIT-style taxonomy for tool organization. Load only task-relevant tools per step using semantic retrieval.
4. **MCP Server Management**: Use gateway pattern for MCP server access. Lazy-load servers on first relevant query; unload after configurable idle period.
5. **Context Pressure Metrics**: Monitor context utilization per step. When utilization exceeds 80%, trigger automatic compression and tool reduction.

### 7.4 Hierarchical Protection Rings

Inspired by OS kernel rings, the Skill Trust Framework, and the AI-45 Degree Law:

**Ring 0 (Immutable Core)**:
- Self-monitoring and drift detection capabilities
- Self-repair and recovery mechanisms
- Alignment checking and safety constraints
- The pruning system itself (cannot prune the pruner)
- Core communication protocols between agents

**Ring 1 (Protected Infrastructure)**:
- Memory management (AgeMem-style unified LTM/STM)
- Context engineering pipeline
- Tool retrieval and selection mechanisms
- Inter-agent coordination protocols
- Logging and observability infrastructure

**Ring 2 (Validated Capabilities)**:
- Curated, tested skills with demonstrated benefit (+16.2pp threshold)
- Verified tool integrations with stable APIs
- Proven workflow patterns with usage history
- Can be temporarily disabled but not deleted without explicit approval

**Ring 3 (Expendable Periphery)**:
- Newly acquired skills pending full validation
- Experimental tool integrations
- Task-specific temporary capabilities
- External/community-contributed skills (26.1% vulnerability rate)
- Freely prunable based on context pressure, usage metrics, or security concerns

**Ring transitions**: Skills can be promoted from Ring 3 to Ring 2 after validation. Skills in Ring 2 can be demoted to Ring 3 if they fail post-model-change revalidation. Ring 0 and Ring 1 capabilities can only be modified through explicit human-approved processes.

---

## 8. Research Gaps and Open Problems

### 8.1 Direct Gaps

1. **No self-benchmarking standard**: No existing benchmark suite is designed for agents to test their own capabilities. Current evaluation assumes external evaluation.
2. **No skill pruning theory**: While skill acquisition is well-studied (Voyager, PSEC, LEGO-Prover), formal criteria for when to prune a skill do not exist.
3. **Model-skill interaction**: How model updates affect previously-validated skills is entirely unstudied. A skill validated on Claude 3.5 may behave differently on Claude 4.
4. **Context budget optimization**: No theoretical framework exists for optimal context allocation across system prompt, tools, task, and memory under a fixed token budget.
5. **Pruning safety proofs**: No formal verification exists for ensuring that capability pruning does not compromise core system properties.

### 8.2 Emerging Opportunities

1. **ToolSelf for self-evolution**: The ToolSelf paradigm of self-reconfiguration as a first-class action could be extended to full self-evolution, where the agent not only selects tools but modifies its own skill library.
2. **SWE-Pruner for agent contexts**: Task-aware adaptive pruning (23-54% reduction while improving success) could be applied beyond code contexts to general agent operation.
3. **AgentSys for security**: Memory isolation patterns could provide both security and performance benefits for self-evolving systems.
4. **Differential loading**: The on-demand sparsity approach (6.6x speedup) suggests that only loading the "diff" between the current and next capability set could dramatically reduce overhead.
5. **Skill Trust Governance**: The four-tier trust model could be integrated with ring-based protection to create a principled, security-aware pruning policy.

---

## 9. References

### Environment Change Detection and Adaptation

1. Chen, L., Zaharia, M., & Zou, J. (2023). How is ChatGPT's behavior changing over time? arXiv:2307.09009.
2. Aguiar, G.J. & Cano, A. (2023). A comprehensive analysis of concept drift locality in data streams. arXiv:2311.06396.
3. Mishra, A. & Stamp, M. (2025). Cluster analysis and concept drift detection in malware. arXiv:2502.14135.
4. Siirtola, P. & Roning, J. (2023). Feature relevance analysis to explain concept drift. arXiv:2301.08453.
5. Hinder, F. et al. (2023). Model based explanations of concept drift. arXiv:2303.09331.
6. Chiu, C., Zhang, S., & van der Schaar, M. (2025). Strategic self-improvement for competitive agents in AI labour markets. arXiv:2512.04988.
7. AlSayyad, A., Huang, K.Y., & Pal, R. (2026). AgentTrace: A structured logging framework for agent system observability. arXiv:2602.10133.
8. Alam, M.T. et al. (2024). MORPH: Towards automated concept drift adaptation for malware detection. arXiv:2401.12790.

### Context Window Efficiency and Management

9. Liu, N.F. et al. (2023). Lost in the Middle: How Language Models Use Long Contexts. arXiv:2307.03172. Published in TACL 2024.
10. Hsieh, C.-Y. et al. (2024). Found in the Middle: Calibrating positional attention bias improves long context utilization. arXiv:2406.16008.
11. Yu, Y. et al. (2024). Mitigate position bias in large language models via scaling a single dimension. arXiv:2406.02536.
12. Baker, G.A. et al. (2024). Lost in the Middle, and In-Between. arXiv:2412.10079.
13. Tian, R. et al. (2024). Distance between relevant information pieces causes bias in long-context LLMs. arXiv:2410.14641.
14. Yu, S. et al. (2025). Tree of Agents: Improving long-context capabilities via multi-perspective reasoning. arXiv:2509.06436.
15. Fei, W. et al. (2023). Extending context window of large language models via semantic compression. arXiv:2312.09571.
16. Huang, C. et al. (2024). Recurrent Context Compression. arXiv:2406.06110.
17. Hu, J. et al. (2025). Dynamic Compressing Prompts for efficient inference. arXiv:2504.11004.
18. Kai, J. et al. (2025). FreqKV: Key-value compression in frequency domain. arXiv:2505.00570.
19. Wang, Y. et al. (2026). SWE-Pruner: Self-adaptive context pruning for coding agents. arXiv:2601.16746.
20. Yu, Y. et al. (2026). Agentic Memory: Learning unified long-term and short-term memory management. arXiv:2601.01885.
21. Wen, R. et al. (2026). AgentSys: Secure and dynamic LLM agents through explicit hierarchical memory management. arXiv:2602.07398.
22. Peng, B. et al. (2023). YaRN: Efficient context window extension. arXiv:2309.00071.
23. Ding, Y. et al. (2024). LongRoPE: Extending LLM context window beyond 2 million tokens. arXiv:2402.13753.
24. He, J. et al. (2023). Never Lost in the Middle. arXiv:2311.09198.
25. Deng, J. et al. (2024). FltLM: Context filtering language model. arXiv:2410.06886.
26. Gupte, M. et al. (2025). What Works for Lost-in-the-Middle in LLMs? arXiv:2511.13900.
27. Ma, Y. & Liu, J. (2025). Quantifying laziness, decoding suboptimality, and context degradation. arXiv:2512.20662.

### Self-Pruning and Lean-Down Strategies

28. Gan, T. & Sun, Q. (2025). RAG-MCP: Mitigating prompt bloat in LLM tool selection. arXiv:2505.03275.
29. Antonioni, E. et al. (2025). JSPLIT: A taxonomy-based solution for prompt bloating in MCP. arXiv:2510.14537.
30. Gaurav, N. et al. (2025). Dynamic ReAct: Scalable tool selection for large-scale MCP environments. arXiv:2509.20386.
31. Franko, U. (2025). Dynamic system instructions and tool exposure for efficient agentic LLMs. arXiv:2602.17046.
32. Lumer, E. et al. (2025). MemTool: Optimizing short-term memory management for dynamic tool calling. arXiv:2507.21428.
33. Wang, G. et al. (2023). Voyager: An open-ended embodied agent with large language models. arXiv:2305.16291.
34. Liu, T. et al. (2025). Skill Expansion and Composition in Parameter Space (PSEC). arXiv:2502.05932.
35. Wang, H. et al. (2023). LEGO-Prover: Neural theorem proving with growing libraries. arXiv:2310.00656.
36. Lumer, E. et al. (2025). ScaleMCP: Dynamic and auto-synchronizing MCP tools. arXiv:2505.06416.
37. Kadekodi, R. et al. (2025). AgentFlux: Decoupled fine-tuning and inference for on-device agentic systems. arXiv:2510.00229.
38. Wang, Q. & Zhang, Y. (2025). Microservices are dying: Module division based on universal interfaces. arXiv:2511.04548.
39. Huang, L. et al. (2025). On-demand multi-task sparsity for efficient large-model deployment. arXiv:2511.19986.
40. Wu, Z. et al. (2025). GRETEL: Goal-driven retrieval and execution-based tool selection. arXiv:2510.17843.
41. Yeon, J. et al. (2025). Quantifying distributional robustness of agentic tool-selection (ToolCert). arXiv:2510.03992.
42. Xiao, Y. et al. (2025). ToolMem: Enhancing multimodal agents with learnable tool capability memory. arXiv:2510.06664.
43. Cui, S. et al. (2025). Self-guided function calling via stepwise experience recall (SEER). arXiv:2508.15214.
44. Shi, Z. et al. (2024). Learning to Use Tools via Cooperative and Interactive Agents (ConAgents). arXiv:2403.03031.
45. Zhou, K. et al. (2025). AINav: LLM-based adaptive interactive navigation with skill tree pruning. arXiv:2503.22942.

### Hierarchical Importance and Safe Self-Modification

46. Chu, S. et al. (2024). Integrating graceful degradation and recovery through requirement-driven adaptation. arXiv:2401.09678.
47. Bliudze, S. et al. (2024). Adaptable TeaStore: Mandatory vs. optional services. arXiv:2412.16060.
48. Yin, Z. et al. (2026). RAPID: Reconfigurable, adaptive platform with physical mask. arXiv:2602.06653.
49. Zhou, J. et al. (2026). ToolSelf: Unifying task execution and self-reconfiguration. arXiv:2602.07883.
50. Lu, S. et al. (2024). MorphAgent: Self-evolving profiles and decentralized collaboration. arXiv:2410.15048.
51. Jiang, H. et al. (2026). Lemon Agent: Hierarchical self-adaptive scheduling. arXiv:2602.07092.
52. Nascimento, N. et al. (2023). Self-adaptive LLM-based multiagent systems (MAPE-K). arXiv:2307.06187.
53. Zemtsop Ndadji, B.A. et al. (2025). AdaptiFlow: Event-driven autonomy in cloud microservices. arXiv:2512.23499.
54. Marin, J. (2025). Capability ceilings in autoregressive language models. arXiv:2510.21866.
55. Pope, M. & Sillito, J. (2021). Quartermaster: Modeling and simulating system degradation. arXiv:2103.03956.

### Agent Skills, Security, and Lifecycle

56. Xu, R. & Yan, Y. (2026). Agent Skills for LLMs: Architecture, acquisition, security. arXiv:2602.12430.
57. Jiang, Y. et al. (2026). SoK: Agentic Skills -- Beyond tool use in LLM agents. arXiv:2602.20867.
58. Liu, Y. et al. (2026). Malicious agent skills in the wild. arXiv:2602.06547.
59. Liu, Y. et al. (2026). Agent skills in the wild: Empirical security analysis at scale. arXiv:2601.10338.

### Instruction Following and Degradation

60. Harada, K. et al. (2025). When instructions multiply: Measuring LLM capabilities. arXiv:2509.21051.
61. Jaroslawicz, D. et al. (2025). How many instructions can LLMs follow at once? arXiv:2507.11538.
62. Elder, B. et al. (2025). Boosting instruction following at scale. arXiv:2510.14842.
63. Ye, J. et al. (2025). A multi-dimensional constraint framework for instruction following. arXiv:2505.07591.
64. Fu, T. et al. (2025). Scaling reasoning, losing control. arXiv:2505.14810.
65. Li, X. et al. (2025). When thinking fails: Pitfalls of reasoning for instruction-following. arXiv:2505.11423.

### Other Cited Works

66. Yuan, Z. et al. (2025). EfficientLLM: Efficiency in large language models. arXiv:2505.13840.
67. Hatalis, K. et al. (2025). Review of case-based reasoning for LLM agents. arXiv:2504.06943.
68. Su, H. et al. (2025). Learn-by-interact: Data-centric framework for self-adaptive agents. arXiv:2501.10893.
69. Lica, M. et al. (2024). MindForge: Embodied agents with theory of mind. arXiv:2411.12977.
70. Zhao, K. et al. (2025). SABER: Switchable and balanced training for efficient LLM reasoning. arXiv:2508.10026.
