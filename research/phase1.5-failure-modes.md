I now have complete verification of all details. Here is the full structured failure mode catalog.

---

# Phase 1.5 Failure Mode Analysis -- Complete Enumerated List (67 Failure Modes)

**Analyzed files:**
- `/home/ak/universal-agents-team/research/detailed-design-phase1.5.md` (design doc, 1949 lines)
- `/home/ak/universal-agents-team/src/uagents/engine/resource_tracker.py` (existing)
- `/home/ak/universal-agents-team/src/uagents/engine/orchestrator.py` (existing)
- `/home/ak/universal-agents-team/src/uagents/engine/agent_spawner.py` (existing)
- `/home/ak/universal-agents-team/src/uagents/engine/prompt_composer.py` (existing)
- `/home/ak/universal-agents-team/src/uagents/models/resource.py` (existing)
- `/home/ak/universal-agents-team/src/uagents/models/task.py` (existing)
- `/home/ak/universal-agents-team/src/uagents/state/yaml_store.py` (existing)
- `/home/ak/universal-agents-team/src/uagents/engine/task_lifecycle.py` (existing)
- `/home/ak/universal-agents-team/src/uagents/models/base.py` (existing)
- `/home/ak/universal-agents-team/src/uagents/models/agent.py` (existing)
- `/home/ak/universal-agents-team/src/uagents/engine/team_manager.py` (existing)
- `/home/ak/universal-agents-team/src/uagents/audit/logger.py` (existing)
- `/home/ak/universal-agents-team/src/uagents/engine/topology_router.py` (existing, lines 60-99)

---

## CRITICAL SEVERITY (8 total: 4 documented + 4 new)

---

**FM-01** | **R1 -- Already Documented**
- **Category:** Data Integrity
- **Location:** `engine/budget_tracker.py` :: `_persist_window()`, `_persist_weekly()`
- **Description:** Window budget file corrupted mid-write. If the process crashes between temp-file creation and `os.replace()`, the budget file is left in an inconsistent state.
- **Impact:** Lost budget tracking. Agents become budget-unaware, reverting to unbounded behavior. On corrupt read, `YamlStore.read()` raises `ValueError` and the `get_window()` `except FileNotFoundError` handler does not catch it, so the caller crashes.
- **Already Documented?** Yes (R1). Mitigated by YamlStore atomic writes (temp + replace). Mitigation text says "create new window (conservative)" but the code's `get_window()` only catches `FileNotFoundError`, not `ValueError` from corrupt YAML.

---

**FM-02** | **R2 -- Already Documented**
- **Category:** Silent Degradation
- **Location:** `engine/rate_limiter.py` :: `record_request()`, `can_send()`, `get_backpressure()`
- **Description:** Rate limiter local mirror drifts out of sync with server-side state. Since the framework does not receive API responses directly (Claude Code is the intermediary), the mirror relies on estimates and manual `update_from_headers()` calls.
- **Impact:** Either sends requests that trigger 429 errors (mirror under-estimates) or blocks work unnecessarily (mirror over-estimates). Over time, drift accumulates.
- **Already Documented?** Yes (R2). Mitigated by pessimistic estimation and `handle_429()` mirror update.

---

**FM-03** | **R3 -- Already Documented**
- **Category:** Data Integrity
- **Location:** `engine/orchestrator.py` :: `process_task()` (design doc Part 7.2 line 1509-1513), `engine/task_lifecycle.py` :: `transition()`
- **Description:** Budget annotation written to task YAML (`task.budget = task_budget`) can be lost on the next `transition()` call because `transition()` re-reads the task from disk (via `_load_task()`). If the budget write and the transition read happen in quick succession and a different process modifies the file in between, the budget annotation disappears.
- **Impact:** Task proceeds without budget tracking. Rolling average never updated for that task. Agent has no budget visibility.
- **Already Documented?** Yes (R3). Mitigated by "task budget persisted before transition."

---

**FM-04** | **R4 -- Already Documented**
- **Category:** Concurrency
- **Location:** `engine/cost_gate.py` :: `request_approval()`, `_check_caps()`, `_record_cost()`
- **Description:** TOCTOU race on daily cost cap. Two concurrent agents call `_check_caps()` which reads `daily.total_spent`. Both see under-cap. Both proceed. Both write incremented `total_spent`. The second write overwrites the first via `YamlStore.write()`, but the YamlStore lock only covers each individual write, not the read-check-write span.
- **Impact:** Actual daily spending exceeds configured cap by up to one concurrent request's amount.
- **Already Documented?** Yes (R4). Acknowledged: "Race window is small (seconds)."

---

**FM-05** | **NEW -- Timezone Mismatch Between Existing Code and Phase 1.5**
- **Category:** Data Integrity
- **Location:** All datetime comparisons: `engine/budget_tracker.py` :: `get_window()` (line 465), `get_weekly()` (line 521); `engine/rate_limiter.py` :: `__init__()`, `record_request()`, `handle_429()`; versus `engine/task_lifecycle.py` :: lines 60, 69, 99, 102; `engine/agent_spawner.py` :: lines 88, 109, 145, 160, 178; `engine/team_manager.py` :: lines 93, 174, 197.
- **Description:** The existing codebase uses `datetime.utcnow()` throughout (naive UTC, no timezone info). Phase 1.5 code uses `datetime.now(timezone.utc)` (timezone-aware UTC). When `BudgetTracker.get_window()` executes `now = datetime.now(timezone.utc)` and compares against `window.window_start` (deserialized from YAML), the comparison `now >= window_end` can raise `TypeError: can't compare offset-naive and offset-aware datetimes`. Whether the error manifests depends on Pydantic's datetime serialization behavior: `model_dump(mode="json")` converts datetimes to ISO strings, and `yaml.safe_load()` may or may not restore timezone info depending on the format.
- **Impact:** `TypeError` crash on window expiry check. Budget tracking completely broken. If the error path varies by Pydantic version, it could be an intermittent failure.
- **Already Documented?** No.

---

**FM-06** | **NEW -- `ensure_dir()` Does Not Exist in YamlStore**
- **Category:** API Contract Mismatch
- **Location:** `state/yaml_store.py` (missing method); called from `engine/budget_tracker.py` :: `__init__()` (design doc line 455), `engine/rate_limiter.py` :: `_persist()` (design doc line 990), `engine/cost_gate.py` :: `_save_record()` (design doc line 1432-1433).
- **Description:** The design doc calls `self.yaml_store.ensure_dir(...)` in at least three Phase 1.5 components. This method does not exist in the current `YamlStore` class at `/home/ak/universal-agents-team/src/uagents/state/yaml_store.py` (confirmed: 153 lines, methods are `__init__`, `_resolve`, `read`, `_check_disk_space`, `write`, `read_raw`, `write_raw`, `exists`, `list_dir` -- no `ensure_dir`). The design doc describes adding it (Part 1.5, lines 106-118) as a modification in Step 6 of the implementation sequence. But Step 2 (BudgetTracker) and Step 3 (RateLimiter) depend on it. The dependency graph in Part 9.1 shows `ensure_dir` in Step 6, AFTER Steps 2-4.
- **Impact:** `AttributeError: 'YamlStore' object has no attribute 'ensure_dir'` on first instantiation of `BudgetTracker`, `RateLimiter`, or `CostGate`. Complete failure of the entire resource awareness stack.
- **Already Documented?** No. The design doc mentions it as a modification but misordered the dependency: Step 6 depends on Steps 2-4, but Steps 2-4 depend on `ensure_dir` from Step 6.

---

**FM-07** | **NEW -- `FrameworkModel` `strict=True` / `extra="forbid"` Blocks New Fields on Existing Models**
- **Category:** API Contract Mismatch
- **Location:** `models/base.py` :: `FrameworkModel` (line 21-26: `ConfigDict(strict=True, extra="forbid")`); `models/task.py` :: `Task`; `models/agent.py` :: `AgentRegistryEntry`.
- **Description:** Phase 1.5 adds `budget: TaskBudgetAnnotation | None = None` to `Task` and `tokens_consumed: int = 0` / `cache_hits: int = 0` to `AgentRegistryEntry`. With `extra="forbid"`, any YAML file written by Phase 1.5 code that includes these new fields will be **rejected** when read by Phase 1 code (which lacks these fields in its model definitions). The converse direction works (Phase 1 YAML read by Phase 1.5 code gets defaults). This means: (a) rollback from Phase 1.5 to Phase 1 breaks all tasks/agents that had new fields written; (b) partial deployment where some processes run Phase 1 and others Phase 1.5 causes `ValidationError` crashes; (c) Appendix D's claim of "zero regression risk" is incorrect for any non-atomic deployment.
- **Impact:** `pydantic.ValidationError` with "Extra inputs are not permitted" on any YAML file that contains Phase 1.5 fields, when read by Phase 1 code. Forward compatibility broken.
- **Already Documented?** No. Appendix D discusses backwards compatibility but does not address the `extra="forbid"` constraint.

---

**FM-08** | **NEW -- Contradictory Null Guard Patterns Between Part 4.3 and Part 7.2**
- **Category:** API Contract Mismatch
- **Location:** `engine/orchestrator.py` :: `process_task()` -- Part 4.3 (design doc lines 1005-1006) vs. Part 7.2 (design doc lines 1485-1499).
- **Description:** Two separate code blocks in the design doc describe the same `process_task()` method with different null-checking patterns. Part 4.3 (lines 1005-1006) directly accesses `self.rate_limiter.get_backpressure_level()` and `self.budget_tracker.get_pressure()` WITHOUT `if self.rate_limiter:` guards. Part 7.2 (lines 1485-1499) DOES guard with `if self.budget_tracker:` and `if self.rate_limiter:`. If the implementer follows Part 4.3 literally, any call to `process_task()` without providing Phase 1.5 components will crash with `AttributeError: 'NoneType' object has no attribute 'get_backpressure_level'`. The design doc intends these to be the same function but presents contradictory versions.
- **Impact:** If Part 4.3 is implemented: `AttributeError` crash for all backwards-compatible callers. If Part 7.2 is implemented: correct behavior. The ambiguity risks the wrong version being coded.
- **Already Documented?** No. R10 addresses `budget_tracker=None` but does not mention the contradictory code blocks.

---

## HIGH SEVERITY (17 total: 5 documented + 12 new)

---

**FM-09** | **R5 -- Already Documented**
- **Category:** Silent Degradation
- **Location:** `engine/budget_tracker.py` :: `__init__()`, `_new_window()`
- **Description:** Window capacity estimate for Claude Max5 (88,000 tokens) or Max20 (220,000 tokens) may be wrong. These numbers come from community reports, not official documentation.
- **Impact:** Over-budgeting (agents think they have more capacity than exists, hit limits) or under-budgeting (agents park work unnecessarily).
- **Already Documented?** Yes (R5).

---

**FM-10** | **R6 -- Already Documented**
- **Category:** Data Integrity
- **Location:** `engine/budget_tracker.py` :: `record_actual_usage()`, `_token_history` deque
- **Description:** Rolling average contaminated by outlier tasks. A single extremely expensive or extremely cheap task skews the average for that task type.
- **Impact:** Future cost estimates wildly inaccurate until diluted by more samples.
- **Already Documented?** Yes (R6). Deque(maxlen=50) provides eventual dilution.

---

**FM-11** | **R7 -- Already Documented**
- **Category:** Silent Degradation
- **Location:** `engine/orchestrator.py` :: `process_task()` (design doc Part 4.3 lines 1008-1042)
- **Description:** Backpressure or budget pressure causes all tasks to be parked simultaneously. No work proceeds. System stalls until window refresh or human intervention.
- **Impact:** Complete framework stall. All queued tasks parked. No progress.
- **Already Documented?** Yes (R7). Mitigated by allowing CRITICAL priority tasks through.

---

**FM-12** | **R8 -- Already Documented**
- **Category:** Resource Leak
- **Location:** `engine/cost_gate.py` :: `_save_record()`
- **Description:** Individual `CostRecord` YAML files accumulate in the `costs/` directory without cleanup.
- **Impact:** Disk space consumed. Eventually `_check_disk_space()` in `YamlStore` blocks all writes.
- **Already Documented?** Yes (R8). Deferred to Phase 2 archival policy.

---

**FM-13** | **R9 -- Already Documented**
- **Category:** Silent Degradation
- **Location:** `engine/cache_manager.py` :: `get_shared_prefix()`
- **Description:** If the shared prefix content changes frequently (e.g., resource awareness section updated every window), the Anthropic cache TTL (5 minutes) may not be sufficient to keep the prefix cached.
- **Impact:** No cache hits. ITPM arbitrage benefit not realized. Rate pressure unrelieved.
- **Already Documented?** Yes (R9).

---

**FM-14** | **NEW -- Double-Counting Token Consumption Between ResourceTracker and BudgetTracker**
- **Category:** Data Integrity
- **Location:** `engine/resource_tracker.py` :: `record_actual_usage(task_type, tokens_used)` (line 100); `engine/budget_tracker.py` :: `record_actual_usage(task_type, complexity, tokens_used)` (design doc line 567).
- **Description:** The design doc says to deprecate `ResourceTracker._token_history` (Step 6) and delegate to `BudgetTracker`. But the existing `ResourceTracker.record_actual_usage()` still exists and appends to its own `_token_history` deque. If callers are not uniformly migrated, tokens get recorded in both places. `ResourceTracker.estimate_task_cost()` uses its own stale/partial history while `BudgetTracker.estimate_task_cost()` uses a different dataset. Two components produce divergent estimates for the same task type.
- **Impact:** Inconsistent cost estimates across framework components. Orchestrator gets one estimate, spawner gets another.
- **Already Documented?** No. Step 6 mentions deprecation but does not identify the double-counting risk.

---

**FM-15** | **NEW -- `record_actual_usage()` Signature Mismatch**
- **Category:** API Contract Mismatch
- **Location:** `engine/resource_tracker.py` :: `record_actual_usage(self, task_type: str, tokens_used: int)` (line 100); `engine/budget_tracker.py` :: `record_actual_usage(self, task_type: str, complexity: str, tokens_used: int)` (design doc line 567).
- **Description:** The existing method takes 2 positional parameters (task_type, tokens_used). The new method takes 3 (task_type, complexity, tokens_used). Any caller migrated from `ResourceTracker.record_actual_usage(type, tokens)` to `BudgetTracker.record_actual_usage(type, tokens)` will pass `tokens` as the `complexity` argument, causing a `TypeError` or silently wrong data.
- **Impact:** Runtime `TypeError` or incorrect string passed as `complexity`. Rolling average never updates correctly.
- **Already Documented?** No.

---

**FM-16** | **NEW -- `_classify_task_type()` and `_classify_complexity()` Missing from Existing Orchestrator**
- **Category:** API Contract Mismatch
- **Location:** `engine/orchestrator.py` -- methods do not exist in current file (confirmed by grep); called at design doc lines 1506-1507 and 1533-1534.
- **Description:** The design doc introduces `_classify_task_type(self, task)` and `_classify_complexity(self, task)` as helper methods on `Orchestrator`. These are not in the current codebase. The modified `process_task()` and `complete_execution()` call them.
- **Impact:** `AttributeError: 'Orchestrator' object has no attribute '_classify_task_type'` on every budget allocation attempt. Budget tracking completely non-functional.
- **Already Documented?** No.

---

**FM-17** | **NEW -- Task Orphaned in INTAKE After Transient Budget RED**
- **Category:** State Machine Violation
- **Location:** `engine/orchestrator.py` :: `process_task()` (design doc Part 7.2 lines 1482-1495).
- **Description:** Budget pressure check runs before any state transitions. If pressure is RED, the code loads the task (which is in INTAKE state since `process_task()` hasn't transitioned it yet), checks `task.status in (TaskStatus.PLANNING, TaskStatus.EXECUTING)` -- this is False for INTAKE, so it does not park. It then raises `ResourceConstrainedError`. The task remains in INTAKE with no transition ever applied. When pressure returns to GREEN, nobody retries this specific task because no retry mechanism exists for tasks stuck in INTAKE. The task must be manually re-submitted.
- **Impact:** Tasks permanently orphaned in INTAKE after transient budget pressure. Silent work loss.
- **Already Documented?** R20 documents the INTAKE parking invalidity but not the orphaning consequence.

---

**FM-18** | **NEW -- Non-Atomic Read-Modify-Write on Window Budget**
- **Category:** Concurrency
- **Location:** `engine/budget_tracker.py` :: `record_consumption()` (design doc lines 481-513).
- **Description:** `record_consumption()` calls `get_window()` which reads `window.yaml`, increments `window.tokens_consumed`, then calls `_persist_window()` which writes it back. YamlStore's advisory lock only covers individual `write()` calls, not the read-modify-write cycle. Two concurrent `record_consumption()` calls: both read `tokens_consumed=1000`, both increment to `1500`, both write `1500`. Expected: `2000`. Actual: `1500`. 500 tokens of consumption silently lost.
- **Impact:** Systematic under-counting of token consumption. Budget pressure reported as lower than actual. Window budget appears to have more remaining capacity than truly exists, allowing agents to exceed real limits.
- **Already Documented?** No. R4 covers this pattern for cost caps but not for the window budget, which is the primary resource tracking mechanism.

---

**FM-19** | **NEW -- Same Read-Modify-Write Race on Weekly Budget**
- **Category:** Concurrency
- **Location:** `engine/budget_tracker.py` :: `record_consumption()` -> `get_weekly()` -> `_persist_weekly()` (design doc lines 501-503).
- **Description:** Same non-atomic read-modify-write pattern as FM-18 but for `WeeklyBudget.tokens_consumed`. Two concurrent calls lose one increment.
- **Impact:** Systematic under-counting of weekly consumption.
- **Already Documented?** No.

---

**FM-20** | **NEW -- `PromptComposer.compose()` Cache Integration Uses Undefined Variables**
- **Category:** API Contract Mismatch
- **Location:** `engine/prompt_composer.py` :: `compose()` (design doc Part 5.4 lines 1206-1207).
- **Description:** The design doc's cache integration code references `ring_0_section.content` and `ring_1_infra_section.content` as local variables. In the current `compose()` implementation, there are no such named variables. The method builds `sections` as a flat list via `self._build_ring_0()` (returns `list[PromptSection]`) and `self._build_ring_1(domain)` (returns `list[PromptSection]`). There is no `ring_0_section` or `ring_1_infra_section` binding. Copy-pasting the design doc code produces `NameError: name 'ring_0_section' is not defined`.
- **Impact:** Cache integration crashes if implemented literally from the design doc. Implementer must reverse-engineer the intent.
- **Already Documented?** No.

---

**FM-21** | **NEW -- `_build_ring_1_resource_awareness()` Integration Path Undefined**
- **Category:** API Contract Mismatch
- **Location:** `engine/prompt_composer.py` -- new method `_build_ring_1_resource_awareness(self, budget_summary: dict)` (design doc lines 707-734) vs. existing `_build_ring_1(self, domain: DomainConfig)`.
- **Description:** The existing `_build_ring_1()` returns `list[PromptSection]` and is called in `compose()` as `sections.extend(self._build_ring_1(domain))`. The new method returns a single `PromptSection`. The design doc does not specify how the two coexist: should `_build_ring_1()` be modified to call `_build_ring_1_resource_awareness()` internally? Should `compose()` call both separately? Should `compose()` receive a `budget_summary` parameter? The signature of `compose()` does not include `budget_summary`.
- **Impact:** Implementer must guess the integration approach. Budget summary either duplicated, missing, or placed at the wrong ring position depending on interpretation.
- **Already Documented?** No.

---

**FM-22** | **NEW -- Duplicate `estimate_task_cost()` Methods with Different Cold Seeds**
- **Category:** API Contract Mismatch
- **Location:** `engine/resource_tracker.py` :: `estimate_task_cost()` (line 89, uses hardcoded `COLD_SEEDS` with 6 entries); `engine/budget_tracker.py` :: `estimate_task_cost()` (design doc line 534, uses YAML-loaded seeds with 10 entries).
- **Description:** Both classes provide `estimate_task_cost(task_type, complexity)`. The `ResourceTracker` version uses a hardcoded dict with 6 entries (`simple_fix`, `feature_small`, `feature_medium`, `feature_large`, `research`, `review`). The `BudgetTracker` version uses YAML-loaded seeds with 4 additional entries (`canary_suite: 3000`, `skill_validation: 4000`, `evolution_proposal: 6000`, `decomposition: 5000`). If any code path still calls `ResourceTracker.estimate_task_cost()` for these 4 new task types, it returns the 10,000 default instead of the correct seed.
- **Impact:** 67-233% overestimation for canary, skill validation, evolution, and decomposition tasks if the wrong method is called.
- **Already Documented?** No.

---

**FM-23** | **NEW -- `handle_429()` Only Marks RPM at Capacity, Not ITPM or OTPM**
- **Category:** Missing Validation
- **Location:** `engine/rate_limiter.py` :: `handle_429()` (design doc lines 924-939).
- **Description:** The method's comment says "Mark all buckets as at capacity (pessimistic)" but the code only executes `self._mirror.rpm.current = self._mirror.rpm.capacity`. ITPM and OTPM `current` values are not set to their respective capacities. A 429 error could be triggered by exceeding any of the three buckets (RPM, ITPM, or OTPM). If the 429 was caused by ITPM exhaustion, the RPM bucket is incorrectly marked full while ITPM still appears to have capacity.
- **Impact:** After an ITPM-triggered 429, the mirror shows ITPM has remaining capacity. The framework continues sending requests that hit more 429s. The comment/code mismatch means the pessimistic safety claim is false.
- **Already Documented?** No.

---

**FM-24** | **NEW -- Hardcoded `COLD_SEEDS` in `resource_tracker.py` Diverges from YAML Config**
- **Category:** Spec Divergence
- **Location:** `engine/resource_tracker.py` :: `COLD_SEEDS` dict (lines 24-31); `core/resource-awareness.yaml` :: `cold_seeds` section (design doc lines 315-331).
- **Description:** The YAML config file has 10 cold seed entries. The hardcoded `COLD_SEEDS` dict in `resource_tracker.py` has 6 entries. The YAML config explicitly states: "Python COLD_SEEDS dict must mirror this file exactly." This invariant is already violated. The `BudgetTracker` loads from YAML (correct), but the `ResourceTracker` uses the hardcoded dict (stale).
- **Impact:** If Step 6 deprecation is incomplete, the two systems produce different estimates. If `ResourceTracker.estimate_task_cost()` is called for `canary_suite`, it returns 10,000 instead of 3,000.
- **Already Documented?** No.

---

**FM-25** | **NEW -- Solo Topology Downgrade Has `agent_count=2`, Contradicting Solo Pattern Definition**
- **Category:** Spec Divergence
- **Location:** `engine/orchestrator.py` :: `process_task()` (design doc Part 4.3 lines 1017-1026); `engine/topology_router.py` :: `PATTERN_RULES["solo"]` (line 77: `"agents": 1`).
- **Description:** Under `BackpressureLevel.SINGLE_AGENT`, the design doc creates `RoutingResult(pattern="solo", agent_count=2, role_assignments=[implementer, reviewer])`. The `PATTERN_RULES` dict defines "solo" as 1 agent. A "solo" routing with 2 agents contradicts the pattern definition. The `TeamManager.create_team()` will spawn both agents, defeating the purpose of single-agent backpressure.
- **Impact:** Under SINGLE_AGENT backpressure, 2 agents are spawned instead of 1. Rate pressure not actually reduced. The backpressure level's semantic meaning is violated.
- **Already Documented?** No.

---

## MEDIUM SEVERITY (19 total: 5 documented + 14 new)

---

**FM-26** | **R10 -- Already Documented**
- **Category:** Silent Degradation
- **Location:** `engine/orchestrator.py`, `engine/agent_spawner.py`
- **Description:** When `budget_tracker=None`, `rate_limiter=None`, or `cost_gate=None`, Phase 1.5 features are disabled. Framework reverts to Phase 0/1 behavior.
- **Impact:** No budget tracking, backpressure, or cost control. Acceptable for backwards compatibility.
- **Already Documented?** Yes (R10).

---

**FM-27** | **R11 -- Already Documented**
- **Category:** Data Integrity
- **Location:** `engine/budget_tracker.py` :: `_token_history`
- **Description:** In-memory token history deque is lost on process restart. Rolling averages revert to cold seeds until 10 new samples collected.
- **Impact:** Temporary accuracy loss of budget estimates after restart.
- **Already Documented?** Yes (R11). Persistence deferred to Phase 2.

---

**FM-28** | **R12 -- Already Documented**
- **Category:** Silent Degradation
- **Location:** `engine/cache_manager.py` :: `get_shared_prefix()`
- **Description:** Shared prefix below 1024 tokens. Constitution (~500 tokens) + config (~300 tokens) = ~800 tokens, which is below Anthropic's minimum cache block size.
- **Impact:** Cache never activates. No ITPM savings.
- **Already Documented?** Yes (R12).

---

**FM-29** | **R13 -- Already Documented**
- **Category:** Silent Degradation
- **Location:** `engine/rate_limiter.py` :: `__init__()` (default `otpm_estimate=16_000`)
- **Description:** OTPM capacity estimate of 16,000 may be wrong. OTPM is hardest to estimate empirically.
- **Impact:** Backpressure either too aggressive (blocks output-heavy tasks) or too lax (allows 429s on output).
- **Already Documented?** Yes (R13).

---

**FM-30** | **R14 -- Already Documented**
- **Category:** Silent Degradation
- **Location:** `engine/budget_tracker.py` :: `WeeklyBudget` (design doc line 169: `estimated_weekly_cap=1_000_000`)
- **Description:** Weekly cap of 1,000,000 tokens may be too conservative, causing unnecessary parking of tasks.
- **Impact:** Reduced throughput. Tasks parked when capacity actually exists.
- **Already Documented?** Yes (R14).

---

**FM-31** | **NEW -- `PromptSection.is_cached` Field Breaks Rollback Under `extra="forbid"`**
- **Category:** API Contract Mismatch
- **Location:** `engine/prompt_composer.py` :: `PromptSection` (design doc Part 5.3 line 1194).
- **Description:** Adding `is_cached: bool = False` to `PromptSection` (which inherits from `FrameworkModel` with `extra="forbid"`) means any serialized `PromptSection` that includes the `is_cached` key will be rejected by Phase 1 code. Same mechanism as FM-07 but at the prompt section level.
- **Impact:** Rollback from Phase 1.5 to Phase 1 breaks deserialization of any persisted prompt data containing `is_cached`.
- **Already Documented?** No.

---

**FM-32** | **NEW -- `_maybe_replenish()` Only Fires at 60-Second Boundaries**
- **Category:** Silent Degradation
- **Location:** `engine/rate_limiter.py` :: `_maybe_replenish()` (design doc lines 963-986).
- **Description:** Replenishment requires `elapsed >= 60.0`. If 59 seconds have passed, buckets remain at their accumulated values. For bursty workloads, the mirror shows near-full buckets for up to 59 seconds after they should have partially replenished.
- **Impact:** Overly conservative backpressure for up to 59 seconds in the worst case. Agents may be blocked from spawning or sending requests unnecessarily.
- **Already Documented?** No. The design doc describes this as "pessimistic (safe)" but does not quantify the delay.

---

**FM-33** | **NEW -- `time.monotonic()` State Lost on Restart Creates Ghost Backpressure**
- **Category:** Data Integrity
- **Location:** `engine/rate_limiter.py` :: `__init__()` (line 835: `self._last_replenish = time.monotonic()`), `_maybe_replenish()`
- **Description:** On restart, `_last_replenish` is set to the current `time.monotonic()`. Meanwhile, `_mirror.current` values are loaded from persisted YAML with accumulated consumption from the previous session. The replenishment logic will not clear stale values for up to 60 seconds because `elapsed` starts at 0 from the new monotonic clock.
- **Impact:** Transient false backpressure (up to 60 seconds) after process restart. May block spawning or park tasks unnecessarily.
- **Already Documented?** No.

---

**FM-34** | **NEW -- `WindowBudget` Properties Not Included in `model_dump()` Output**
- **Category:** Data Integrity
- **Location:** `models/resource.py` :: `WindowBudget` (design doc lines 127-159).
- **Description:** `remaining_tokens`, `utilization`, and `pressure_level` are Python `@property` decorators. Pydantic's `model_dump()` does not serialize properties by default. When `window.yaml` is read from disk, these values are recomputed dynamically.
- **Impact:** Minimal for normal operation (properties are computed). But any external tool reading `window.yaml` directly (audit viewer, debugging script) will not see remaining tokens or pressure level, only raw `tokens_consumed` and `estimated_capacity`.
- **Already Documented?** No.

---

**FM-35** | **NEW -- `CacheManager._prefix_tokens` Uses Different chars/token Ratio Than Rest of Codebase**
- **Category:** Silent Degradation
- **Location:** `engine/cache_manager.py` :: `get_shared_prefix()` (design doc line 1144: `len(...) // 4`); `engine/prompt_composer.py` :: `CHARS_PER_TOKEN_DEFAULT = 3.5` (line 59).
- **Description:** `CacheManager` estimates prefix tokens as `len(text) // 4` (4 chars/token). The rest of the codebase uses `3.5` chars/token. This means `CacheManager` underestimates prefix tokens by ~12.5%. A prefix that is actually 960 tokens (at 3.5 c/t) would be estimated at 840 tokens by the cache manager, incorrectly showing it below the 1024 minimum threshold.
- **Impact:** The 1024-token minimum check may falsely pass (reporting above threshold when actually below), or falsely fail (less likely direction).
- **Already Documented?** No.

---

**FM-36** | **NEW -- `estimate_cache_savings()` Accumulates on Every Call**
- **Category:** Data Integrity
- **Location:** `engine/cache_manager.py` :: `estimate_cache_savings()` (design doc lines 1157-1166).
- **Description:** Each call to `estimate_cache_savings()` adds to `self.stats.tokens_saved`. If called multiple times for the same logical request (e.g., once for pre-check estimation, once for post-request accounting), savings are double-counted.
- **Impact:** Inflated `tokens_saved` metric. Efficiency reports overstate cache benefit.
- **Already Documented?** No.

---

**FM-37** | **NEW -- Zero-Token Budget Allocation Allowed**
- **Category:** Missing Validation
- **Location:** `engine/budget_tracker.py` :: `allocate_task_budget()` (design doc lines 578-608).
- **Description:** `allocate_task_budget()` caps allocation to `window.remaining_tokens`. If the window is nearly exhausted, `allocated_tokens` could be 0. A `TaskBudgetAnnotation` with `allocated_tokens=0` is legal (no validation prevents it). The `utilization` property returns 1.0 (guarded division) and `remaining` returns 0. But no guard prevents the task from proceeding with a zero-token budget.
- **Impact:** Task starts execution with zero allocated budget. Agent sees 100% utilization immediately. If budget is advisory only, execution continues and consumes tokens that were not allocated.
- **Already Documented?** No.

---

**FM-38** | **NEW -- `record_consumption()` Attributes Old-Window Tokens to New Window**
- **Category:** State Machine Violation
- **Location:** `engine/budget_tracker.py` :: `record_consumption()` -> `get_window()` (design doc lines 481-513, 459-479).
- **Description:** `record_consumption(tokens)` calls `get_window()`. If the window has expired, `get_window()` creates a new window (tokens_consumed=0) and returns it. The tokens being recorded were consumed in the OLD window but are now added to the NEW window's count. The first `record_consumption()` call after window expiry incorrectly pollutes the new window.
- **Impact:** New window starts with a non-zero consumption count from the previous window. Pressure level artificially elevated at window start.
- **Already Documented?** No.

---

**FM-39** | **NEW -- Orchestrator Loads Task Multiple Times in Single `process_task()` Call**
- **Category:** Concurrency
- **Location:** `engine/orchestrator.py` :: `process_task()` (design doc Part 7.2 lines 1488, 1503 vs. existing code line 68).
- **Description:** The Phase 1.5 `process_task()` loads the task from YAML at least 3-4 times: once for budget pressure check (line 1488), once for budget allocation (line 1503), and the existing code loads it again at line 68 and via `transition()`. Each load is a separate disk read. Between loads, another process could modify the file. The budget annotation written at line 1511-1513 could be overwritten by a subsequent `transition()` that reloads the task from disk without the `budget` field (if the transition read precedes the budget write reaching disk).
- **Impact:** Budget annotations silently lost mid-pipeline. This amplifies FM-03 (R3).
- **Already Documented?** No (new amplification of R3).

---

**FM-40** | **NEW -- `_classify_task_type()` Heuristic Is Order-Dependent and Fragile**
- **Category:** Silent Degradation
- **Location:** `engine/orchestrator.py` :: `_classify_task_type()` (design doc lines 1542-1551).
- **Description:** Task type classification uses substring matching on `task.title.lower()` with `any()` short-circuiting. "Research the build fix" would match "research" first (returning "research") instead of "fix" (which would return "simple_fix"). "Review bug report" matches "review" (returns "research") instead of "bug" (returns "simple_fix"). The ordering of `if` chains creates implicit priority that may not match actual task resource profiles.
- **Impact:** Incorrect budget estimates for ambiguously-titled tasks. Under-allocation for expensive tasks classified as cheap; over-allocation for cheap tasks classified as expensive.
- **Already Documented?** No.

---

**FM-41** | **NEW -- `_classify_complexity()` Based Solely on Description Length**
- **Category:** Silent Degradation
- **Location:** `engine/orchestrator.py` :: `_classify_complexity()` (design doc lines 1553-1560).
- **Description:** Complexity classified by character count: <50 = "small", <200 = "medium", else "large". "Rewrite the entire codebase" (28 chars) is "small." A verbose description of a typo fix (250 chars) is "large." The heuristic has no correlation with actual resource consumption.
- **Impact:** Budget allocations disconnected from real complexity. Small-described expensive tasks get tiny budgets; verbose trivial tasks get oversized budgets.
- **Already Documented?** No.

---

**FM-42** | **NEW -- `CostGate._record_cost()` Adds Unapproved Records to Daily Summary Records List**
- **Category:** Data Integrity
- **Location:** `engine/cost_gate.py` :: `_record_cost()` (design doc lines 1406-1428).
- **Description:** When `_record_cost()` is called for MEDIUM/HIGH spend levels (approval.approved=False), `daily.records.append(record.id)` executes unconditionally. The `total_spent` check (`if approval.approved:`) correctly skips the amount, but the record ID is appended regardless. Rejected records appear in the daily records list alongside approved ones.
- **Impact:** Daily records list mixes approved and unapproved records. Audit analysis tools must cross-reference each record ID to determine approval status.
- **Already Documented?** No.

---

**FM-43** | **NEW -- `CostGate.approve()` Does Not Update Daily Summary `total_spent`**
- **Category:** Data Integrity
- **Location:** `engine/cost_gate.py` :: `approve()` (design doc lines 1334-1341) vs. `_record_cost()` (design doc lines 1406-1428).
- **Description:** When `request_approval()` is called for MEDIUM/HIGH, `_record_cost()` creates the cost record with `approved=False` and does NOT increment `daily.total_spent` (because the `if approval.approved:` guard is False). Later, `approve(record_id, approver)` sets `record.approved=True` and saves the record, but it does NOT re-open the daily summary and add the amount to `total_spent`. The approved cost is never reflected in the daily cap tracking.
- **Impact:** Daily cost cap is permanently undercounted for all MEDIUM/HIGH approved costs. A series of $5 approved costs would never trigger the $10 daily cap because `total_spent` stays at 0.
- **Already Documented?** No.

---

**FM-44** | **NEW -- `_maybe_replenish()` Integer Division Loses Fractional Minutes Permanently**
- **Category:** Silent Degradation
- **Location:** `engine/rate_limiter.py` :: `_maybe_replenish()` (design doc lines 981-986).
- **Description:** `minutes = int(elapsed / 60.0)` truncates fractional minutes. If 90 seconds elapsed: `minutes=1`, only 1 minute of replenishment applied, then `_last_replenish = now`. The next call after 30 more seconds: `elapsed=30 < 60`, no replenishment. The 30-second remainder is permanently lost. Over time, this systematic under-replenishment causes buckets to drift toward over-full.
- **Impact:** Cumulative conservative bias in rate limiting. Over a long session, increasingly aggressive backpressure from buckets that never fully drain.
- **Already Documented?** No.

---

**FM-45** | **NEW -- `DailyCostSummary.date` Has No Format Validation**
- **Category:** Missing Validation
- **Location:** `models/resource.py` :: `DailyCostSummary` (design doc line 216: `date: str`); `engine/cost_gate.py` :: `get_daily_summary()`, `_record_cost()`, `_get_weekly_total()`.
- **Description:** `date` is a bare `str` with no Pydantic validator enforcing YYYY-MM-DD format. All internal code uses `strftime("%Y-%m-%d")`, which is consistent. But a manually created or externally modified YAML file with `date: "02/28/2026"` would not be caught at validation time. The `_get_weekly_total()` loop iterates day strings in YYYY-MM-DD format and would silently skip misformatted entries.
- **Impact:** Minor: silently missed daily records in weekly aggregation if date formats diverge.
- **Already Documented?** No.

---

## LOW SEVERITY (23 total: 6 documented + 17 new)

---

**FM-46** | **R15 -- Already Documented**
- **Category:** Silent Degradation
- **Location:** `engine/budget_tracker.py` :: `compute_trends()` (design doc lines 1656-1688)
- **Description:** Efficiency trends may show "degrading" but no automated action taken in Phase 1.5.
- **Impact:** Degradation goes unaddressed until Phase 2 evolution engine.
- **Already Documented?** Yes (R15).

---

**FM-47** | **R16 -- Already Documented**
- **Category:** Resource Leak
- **Location:** `engine/cost_gate.py` :: `_save_record()`
- **Description:** Individual cost record YAML files not cleaned up.
- **Impact:** Minor disk usage growth over time.
- **Already Documented?** Yes (R16).

---

**FM-48** | **R17 -- Already Documented**
- **Category:** Silent Degradation
- **Location:** `engine/budget_tracker.py` :: `get_pressure()`
- **Description:** Budget pressure level flickers between GREEN/YELLOW or YELLOW/ORANGE at threshold boundaries, causing log noise.
- **Impact:** Noisy logs. Potential behavioral churn if agents react to frequent level changes.
- **Already Documented?** Yes (R17). Hysteresis proposed as mitigation.

---

**FM-49** | **R18 -- Already Documented**
- **Category:** Concurrency
- **Location:** `engine/agent_spawner.py` :: `despawn_idle_agents()`, `check_agent_health()` (lines 155-181)
- **Description:** Idle despawn races with task assignment. An agent could be marked idle and despawned while simultaneously being assigned a new subtask by the team manager.
- **Impact:** Agent despawned right before task assignment. Subtask left unassigned.
- **Already Documented?** Yes (R18).

---

**FM-50** | **R19 -- Already Documented**
- **Category:** Test Gap
- **Location:** `engine/agent_spawner.py` :: `spawn()` (design doc Part 7.3 lines 1580-1613)
- **Description:** Spawn policy rules for ORANGE budget and SINGLE_AGENT backpressure may be incompletely implemented. The design doc specifies: FULL_STOP = no spawn; SINGLE_AGENT = only if no other agents active; RED budget = no spawn; ORANGE budget = only high/critical priority tasks. The code only checks FULL_STOP, SINGLE_AGENT, and RED budget. ORANGE budget check is missing from the spawn code.
- **Impact:** Agents may spawn under ORANGE budget pressure when they should be restricted to high/critical priority tasks only.
- **Already Documented?** Yes (R19).

---

**FM-51** | **R20 -- Already Documented**
- **Category:** State Machine Violation
- **Location:** `engine/orchestrator.py` :: `process_task()` (design doc Part 4.3 lines 1008-1042)
- **Description:** INTAKE->PARKED is not in `VALID_TRANSITIONS`. Backpressure handlers guard against this with `task.status in (TaskStatus.PLANNING, TaskStatus.EXECUTING)`.
- **Impact:** Without the guard, `InvalidTransitionError` would be raised. With the guard, INTAKE tasks raise `ResourceConstrainedError` without parking (see FM-17 for the orphaning consequence).
- **Already Documented?** Yes (R20).

---

**FM-52** | **NEW -- `CacheManager` Has No State Persistence**
- **Category:** Data Integrity
- **Location:** `engine/cache_manager.py` :: all state (design doc lines 1120-1124)
- **Description:** `CacheManager` stores `_prefix_cache`, `_prefix_hash`, `_prefix_tokens`, and `stats` (CacheStats) entirely in memory. On process restart, all cache metadata and statistics are lost.
- **Impact:** Cache statistics reset to zero after every restart. No historical data for trend computation or efficiency analysis.
- **Already Documented?** No.

---

**FM-53** | **NEW -- `check_agent_health()` String vs. StrEnum Comparison**
- **Category:** Missing Validation
- **Location:** `engine/agent_spawner.py` :: `check_agent_health()` (line 172: `data.get("status") == AgentStatus.DESPAWNED`)
- **Description:** `data` is a raw dict from `read_raw()`. `data.get("status")` returns a string like `"despawned"`. `AgentStatus.DESPAWNED` is a `StrEnum`. Python `StrEnum` comparison with plain strings works correctly for matching cases. But if YAML serialization stores the value in a different case (e.g., "DESPAWNED" or "Despawned"), the comparison silently fails.
- **Impact:** If YAML stores status in non-lowercase format, health check returns True for despawned agents, treating them as healthy. Idle despawn would not clean them up.
- **Already Documented?** No.

---

**FM-54** | **NEW -- `compute_efficiency()` Uses `total_tokens` as Both `cost_of_pass` and `total_input_tokens`**
- **Category:** Data Integrity
- **Location:** `engine/budget_tracker.py` :: `compute_efficiency()` (design doc lines 633-646)
- **Description:** `compute_efficiency()` sets `cost_of_pass=total_tokens` and `total_input_tokens=total_tokens`. The `cache_hit_rate` property computes `cache_hit_tokens / total_input_tokens`. But `total_tokens` includes both input AND output tokens, so `cache_hit_rate` is diluted by output tokens in the denominator. Cache hit rate should be `cache_hits / input_tokens_only`.
- **Impact:** `cache_hit_rate` systematically underreported. A task with 50% input cache hits but equal input/output tokens would show ~25% cache hit rate.
- **Already Documented?** No.

---

**FM-55** | **NEW -- No Tests for CacheManager**
- **Category:** Test Gap
- **Location:** `tests/` (missing file)
- **Description:** The verification checklist (Part 10.1, items 12-13) lists CacheManager tests as "Manual or test." Step 5 uses "(if added)" hedging. The new files list (Part 1.5 lines 86-88) includes test files for rate_limiter, budget_tracker, and cost_gate but NOT for cache_manager. No test file is committed to being created.
- **Impact:** CacheManager code deployed without automated regression tests. Hash invalidation, minimum-threshold check, and statistics tracking untested.
- **Already Documented?** No.

---

**FM-56** | **NEW -- `ResourceSnapshot` Model Defined But Never Constructed**
- **Category:** Spec Divergence
- **Location:** `models/resource.py` :: `ResourceSnapshot` (design doc lines 184-198)
- **Description:** `ResourceSnapshot` is described as "Created before every resource-consuming decision (spawn, task start). Persisted to audit log for post-hoc analysis." No code in the design doc constructs a `ResourceSnapshot` instance. No method in `BudgetTracker`, `RateLimiter`, `Orchestrator`, or `AgentSpawner` creates one.
- **Impact:** Dead code. Audit log never receives pre-decision resource snapshots. Post-hoc analysis of resource decisions impossible. The model exists but serves no purpose.
- **Already Documented?** No.

---

**FM-57** | **NEW -- No Integration Between `parse_usage_output()` and `BudgetTracker`**
- **Category:** Spec Divergence
- **Location:** `engine/resource_tracker.py` :: `parse_usage_output()` (line 106); `engine/budget_tracker.py` (design doc)
- **Description:** The design doc states the `BudgetTracker` "delegates to [ResourceTracker._parse_usage_text()] for primary token tracking (I8)." No code in `BudgetTracker` calls `ResourceTracker.parse_usage_output()` or `_parse_usage_text()`. The two systems are completely disconnected.
- **Impact:** The primary token tracking method (parsing `/usage` CLI output) is not integrated with the budget system. Budget tracking relies entirely on explicit `record_consumption()` calls, which may drift from actual Claude API consumption.
- **Already Documented?** No.

---

**FM-58** | **NEW -- `BudgetTracker.__init__()` Raises Misleading Error on YAML Structure Change**
- **Category:** Missing Validation
- **Location:** `engine/budget_tracker.py` :: `__init__()` (design doc lines 438-444)
- **Description:** `__init__` reads `core/resource-awareness.yaml` and navigates `config.get("resource_awareness", {}).get("cold_seeds")`. If the YAML has a different nesting (e.g., `cold_seeds` at root level, or under a differently-named key), `raw_seeds` is `None` and a `FileNotFoundError` is raised with message "missing cold_seeds section." The file exists; only the structure differs. The error type is misleading (it is a structure/validation error, not a file-not-found error).
- **Impact:** Confusing error message during debugging. Developer looks for a missing file when the issue is YAML structure.
- **Already Documented?** No.

---

**FM-59** | **NEW -- `_cache_hit_tokens` and `_total_input_tokens` Not Persisted**
- **Category:** Data Integrity
- **Location:** `engine/budget_tracker.py` :: `__init__()` (design doc lines 451-452), `record_consumption()` (design doc lines 496-498)
- **Description:** `_cache_hit_tokens` and `_total_input_tokens` are in-memory counters initialized to 0. They are incremented by `record_consumption()` but never written to YAML. On restart, they reset to 0.
- **Impact:** Session-scoped cache tracking only. Cannot compute lifetime cache efficiency. This parallels R11 (token history) but for different counters.
- **Already Documented?** No.

---

**FM-60** | **NEW -- `update_from_headers()` Only Updates RPM and ITPM, Not OTPM**
- **Category:** Missing Validation
- **Location:** `engine/rate_limiter.py` :: `update_from_headers()` (design doc lines 941-959)
- **Description:** The method updates RPM from `x-ratelimit-limit-requests`/`x-ratelimit-remaining-requests` and ITPM from `x-ratelimit-limit-tokens`/`x-ratelimit-remaining-tokens`. No OTPM headers are parsed. If the API provides separate output token rate limit headers, they are ignored. The OTPM bucket remains at its initial estimate (16,000) permanently.
- **Impact:** OTPM never calibrated against actual server limits. Combined with FM-29 (R13: OTPM estimate wrong), the output token bucket is never corrected.
- **Already Documented?** Partially (R13 identifies wrong OTPM estimate). The specific gap in `update_from_headers()` is not mentioned.

---

**FM-61** | **NEW -- Missing Imports in Design Doc Orchestrator Code**
- **Category:** API Contract Mismatch
- **Location:** `engine/orchestrator.py` (design doc Part 4.3 lines 999-1045, Part 7.2 lines 1454-1561)
- **Description:** The design doc code uses `RoutingResult`, `BackpressureLevel`, `BudgetPressureLevel`, and `ResourceConstrainedError` without showing corresponding import statements. The existing `orchestrator.py` imports do not include these. `RoutingResult` is imported from `topology_router` already (line 17), but `BackpressureLevel` (from `rate_limiter`), `BudgetPressureLevel` (from `models/resource`), and `ResourceConstrainedError` (from `agent_spawner`) are not imported.
- **Impact:** `NameError` at runtime if imports are not added. An implementation detail, but the design doc is stated as "implementation-ready -- concrete enough to code from directly."
- **Already Documented?** No.

---

**FM-62** | **NEW -- `_get_weekly_total()` Midnight UTC Edge Case**
- **Category:** Missing Validation
- **Location:** `engine/cost_gate.py` :: `_get_weekly_total()` (design doc lines 1391-1404)
- **Description:** `_get_weekly_total()` uses `datetime.now(timezone.utc).date()` and looks back 7 days. At midnight UTC, `today` rolls over. If a cost was recorded just before midnight, it belongs to "yesterday." The loop correctly includes yesterday (i=1). However, `_record_cost()` writes the daily summary using `datetime.now(timezone.utc).strftime("%Y-%m-%d")`. If the `_record_cost()` and `_get_weekly_total()` calls straddle midnight, the cost could be recorded under today's date while `_get_weekly_total()` started its loop with yesterday as `today`.
- **Impact:** Narrow race window at midnight UTC. A cost recorded in the transition moment could be missed in the weekly total, allowing a one-time cap bypass.
- **Already Documented?** No.

---

**FM-63** | **NEW -- `despawn_idle_agents()` Never Despawns Agents Without Heartbeat**
- **Category:** Silent Degradation
- **Location:** `engine/agent_spawner.py` :: `check_agent_health()` (line 175-176: `if not heartbeat: return True`), `despawn_idle_agents()` (design doc lines 1619-1631)
- **Description:** `check_agent_health()` returns `True` (healthy) when `heartbeat` is `None`, meaning "No heartbeat tracking yet." `despawn_idle_agents()` only despawns agents where `check_agent_health()` returns `False`. Agents without heartbeat tracking (e.g., Phase 0/1 agents, or agents whose heartbeat was never initialized) are permanently considered "healthy" and never despawned by the idle timeout.
- **Impact:** Legacy agents without heartbeat tracking accumulate indefinitely. `_count_active_agents()` counts them, consuming agent capacity slots.
- **Already Documented?** No.

---

**FM-64** | **NEW -- No Single Entry Point Coordinating BudgetTracker and RateLimiter**
- **Category:** Integration Risk
- **Location:** `engine/budget_tracker.py` :: `record_consumption()` (design doc lines 481-513); `engine/rate_limiter.py` :: `record_request()` (design doc lines 837-864)
- **Description:** A caller recording token consumption must call both `budget_tracker.record_consumption(tokens, is_cached)` AND `rate_limiter.record_request(input_tokens, output_tokens, cached_tokens)` with consistent parameters. There is no single method that wraps both calls. If a caller calls one but not the other, or passes different values, the two systems diverge.
- **Impact:** Budget and rate limit tracking operate on inconsistent data. One shows tokens remaining that the other does not.
- **Already Documented?** No.

---

**FM-65** | **NEW -- Resource Audit Logging Never Implemented**
- **Category:** Test Gap
- **Location:** `audit/logger.py` :: `log_resource()` (line 48); design doc Step 11 (line 1785: "Resource events logged to RESOURCES stream ~20 lines")
- **Description:** Step 11 says resource events should be logged. The existing `AuditLogger.log_resource()` method exists and accepts `ResourceLogEntry`. But no Phase 1.5 code in the design doc calls `log_resource()`. No `ResourceLogEntry` instances are constructed anywhere in the BudgetTracker, RateLimiter, CostGate, or Orchestrator code.
- **Impact:** Resource events never reach the audit trail. Post-hoc analysis relies on Python `logging` module output only, which is not structured or queryable.
- **Already Documented?** No.

---

**FM-66** | **NEW -- `get_budget_summary()` Non-Atomic Window + Weekly Read**
- **Category:** Concurrency
- **Location:** `engine/budget_tracker.py` :: `get_budget_summary()` (design doc lines 615-629)
- **Description:** `get_budget_summary()` calls `get_window()` then `get_weekly()` sequentially. Between these two disk reads, a `record_consumption()` from another agent could update both. The summary could show a window utilization that does not correspond to the weekly utilization (e.g., window shows 50% used, weekly shows 45% used due to interleaving).
- **Impact:** Minor inconsistency in budget summary shown to agents. Could cause confusion during debugging.
- **Already Documented?** No.

---

**FM-67** | **NEW -- `_new_weekly()` Does Not Align to Monday**
- **Category:** Spec Divergence
- **Location:** `engine/budget_tracker.py` :: `_new_weekly()` (design doc lines 656-659), `get_weekly()` (design doc line 520: "Check if week has rolled over (Monday boundary)")
- **Description:** The comment says "Monday boundary" but `_new_weekly()` creates `WeeklyBudget(week_start=datetime.now(timezone.utc))` without aligning to Monday. The expiry check `week_end = weekly.week_start + timedelta(days=7)` creates a rolling 7-day window from creation time. If initialized on Wednesday, the "week" runs Wednesday-to-Wednesday. If Claude Max subscription resets on a specific day boundary, the framework's weekly tracking will not align.
- **Impact:** Weekly budget may reset mid-subscription-week or span two subscription weeks. Budget remaining could be overstated or understated near week boundaries.
- **Already Documented?** No.

---

**FM-68** | **NEW -- Backpressure Checks Use `if` Not `elif`, Causing Cascading Evaluation**
- **Category:** State Machine Violation
- **Location:** `engine/orchestrator.py` :: `process_task()` (design doc Part 4.3 lines 1008-1042)
- **Description:** The three backpressure checks use `if` (not `elif`). For `FULL_STOP`: the first block parks and raises. If the raise triggers, subsequent blocks are not reached. But if the task cannot be parked (INTAKE state) and it is a critical task, the `ResourceConstrainedError` still raises, so the subsequent blocks do not execute for FULL_STOP anyway. For `SINGLE_AGENT`: the second block creates a `RoutingResult` override but assigns it to a local `routing` variable. Then the `PAUSE` block also evaluates (because it is `if`, not `elif`), potentially parking the task AND creating a routing override, or raising a different error. For a non-critical task at `SINGLE_AGENT` level: block 2 sets `routing` to solo, then block 3 checks `task.priority` and parks/raises because PAUSE threshold (0.90) is below SINGLE_AGENT (0.95), so `bp_level >= PAUSE` is also true.
- **Impact:** At `SINGLE_AGENT` level, non-critical tasks are parked by the PAUSE block even though SINGLE_AGENT should still allow them to run (with reduced topology). The solo routing override from block 2 is wasted. Critical tasks at SINGLE_AGENT correctly get solo routing and proceed.
- **Already Documented?** No.

---

## SUMMARY TABLE

| Severity | Documented (R1-R20) | NEW | Total |
|----------|---------------------|-----|-------|
| Critical | 4 (FM-01 to FM-04) | 4 (FM-05 to FM-08) | **8** |
| High | 5 (FM-09 to FM-13) | 12 (FM-14 to FM-25) | **17** |
| Medium | 5 (FM-26 to FM-30) | 14 (FM-31 to FM-45) | **19** |
| Low | 6 (FM-46 to FM-51) | 17 (FM-52 to FM-68) | **23** |
| **TOTAL** | **20** | **47** | **67** |

---

## TOP 10 MUST-FIX BEFORE IMPLEMENTATION (Prioritized)

| Priority | FM | Severity | Summary | Fix |
|----------|-----|----------|---------|-----|
| 1 | FM-06 | Critical | `ensure_dir()` missing from YamlStore; BudgetTracker/RateLimiter/CostGate crash on init | Add `ensure_dir()` to YamlStore BEFORE implementing Steps 2-4. Fix dependency graph ordering. |
| 2 | FM-05 | Critical | Timezone mismatch: `datetime.utcnow()` (naive) vs `datetime.now(timezone.utc)` (aware) | Standardize entire codebase on `datetime.now(timezone.utc)`. Add migration for existing YAML datetimes. |
| 3 | FM-08 | Critical | Part 4.3 and Part 7.2 contradict on null guards for `rate_limiter`/`budget_tracker` | Use Part 7.2 pattern: always guard with `if self.rate_limiter:` / `if self.budget_tracker:`. |
| 4 | FM-07 | Critical | `extra="forbid"` breaks forward compatibility when new fields added to Task/Agent models | Either deploy atomically or use `extra="ignore"` for models that cross phase boundaries. |
| 5 | FM-23 | High | `handle_429()` only marks RPM at capacity; ITPM/OTPM left unchanged | Set all three buckets to capacity: `self._mirror.itpm.current = self._mirror.itpm.capacity; self._mirror.otpm.current = self._mirror.otpm.capacity`. |
| 6 | FM-18/19 | High | Read-modify-write race on window/weekly budget YAML | Hold YamlStore lock across the full read-modify-write cycle, or use an append-only ledger with periodic compaction. |
| 7 | FM-43 | Medium | `CostGate.approve()` never increments `daily.total_spent` | Add daily summary update in `approve()`: reload daily, add amount, persist. |
| 8 | FM-16 | High | `_classify_task_type()` and `_classify_complexity()` not in existing orchestrator | Implement these methods before budget-aware `process_task()` can function. |
| 9 | FM-25 | High | Solo topology downgrade uses `agent_count=2`, contradicts solo pattern (1 agent) | Use `pattern="pipeline"` with `agent_count=2`, or true solo with `agent_count=1` and separate review scheduling. |
| 10 | FM-14/22 | High | Duplicate `estimate_task_cost()` and `record_actual_usage()` between ResourceTracker and BudgetTracker | In Step 6, replace ResourceTracker methods with delegating wrappers that call BudgetTracker, or remove them entirely and update all callers. |