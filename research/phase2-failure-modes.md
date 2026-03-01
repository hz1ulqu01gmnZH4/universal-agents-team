# Phase 2 Failure Mode Analysis -- Complete Enumerated List

**Date:** 2026-03-01
**Scope:** Phase 2 "Self-Awareness" components: DiversityEngine, StagnationDetector, CapabilityTracker, CalibrationEngine, Audit Viewer Enhancements, Deferred Phase 1.5 Fixes, Orchestrator Integration
**Numbering:** Continues from Phase 1.5 failure mode catalog (last used: FM-68, plus design doc FM-70 through FM-84)
**Starting at:** FM-85

**Analyzed files:**
- `/home/ak/universal-agents-team/research/detailed-design-phase2.md` (design doc, ~2543 lines)
- `/home/ak/universal-agents-team/src/uagents/engine/orchestrator.py` (existing, 307 lines)
- `/home/ak/universal-agents-team/src/uagents/engine/resource_tracker.py` (existing, 202 lines)
- `/home/ak/universal-agents-team/src/uagents/engine/agent_spawner.py` (existing, 239 lines)
- `/home/ak/universal-agents-team/src/uagents/state/yaml_store.py` (existing, 159 lines)
- `/home/ak/universal-agents-team/src/uagents/state/jsonl_writer.py` (existing, 162 lines)
- `/home/ak/universal-agents-team/src/uagents/audit/logger.py` (existing, 78 lines)
- `/home/ak/universal-agents-team/src/uagents/models/base.py` (existing, FrameworkModel with `extra="forbid"`)
- `/home/ak/universal-agents-team/src/uagents/models/task.py` (existing, TaskMetrics, TaskReview)
- `/home/ak/universal-agents-team/src/uagents/models/voice.py` (existing, VoiceProfile with optional tone/style)

**Cross-reference:** Phase 1.5 failure modes at `/home/ak/universal-agents-team/research/phase1.5-failure-modes.md` (FM-01 through FM-68); Phase 2 design doc embedded failure modes (FM-70 through FM-84, D-1 through D-7).

---

## CRITICAL SEVERITY (6 total)

---

**FM-85** | **DiversityEngine TF-IDF: Division by Zero on All-Empty Outputs**
- **Component:** `engine/diversity_engine.py` :: `compute_text_diversity()`, `_compute_idf()`, `_tf_idf_vector()`
- **Failure:** If all agent outputs are empty strings (e.g., agents timed out, returned no content), `_tokenize()` returns empty lists for every document. `_compute_idf()` returns an empty dict (no tokens across any document). `_tf_idf_vector()` returns an empty dict for each output. `_cosine_distance()` receives two empty dicts, `all_keys` is empty, returns 0.0. The mean distance is 0.0, and `compute_text_diversity()` returns 0.0. So far, correct -- but the `SRDMeasurement` is constructed with `composite_srd=0.0`, health_status returns "critical", and a stagnation signal fires. The real problem: `agent_outputs` was provided with `len >= 2` so diversity measurement was triggered, but the 0.0 is indistinguishable from genuinely identical outputs. No metadata differentiates "empty outputs" from "identical outputs."
- **Trigger:** Agents produce empty outputs due to timeout, error, or context limit.
- **Impact:** False stagnation alert. The orchestrator cannot distinguish "agents failed to produce output" from "agents produced identical output." Wrong corrective action may be taken in Phase 4+.
- **Severity:** CRITICAL
- **Mitigation:** NOT ADDRESSED. Design doc FM-70 only covers `< 2 outputs`, not `>= 2 empty outputs`. Add a guard: if all outputs are empty or below a minimum length threshold, return a special sentinel or skip diversity measurement entirely.
- **Phase:** Phase 2

---

**FM-86** | **CalibrationEngine Unbounded `records` List Grows Until Memory Exhaustion**
- **Component:** `engine/calibration_engine.py` :: `record_prediction()`, `_save_state()`; `models/self_assessment.py` :: `CalibrationState.records`
- **Failure:** Every call to `record_prediction()` appends a `CalibrationRecord` to `self._state.records`. The design doc FM-74 says "Cap records list to 100 entries. Oldest trimmed in `_save_state()`." However, the actual `_save_state()` implementation (design doc lines 1413-1418) is simply `self.yaml_store.write(path, self._state)` with NO trimming logic. The `CalibrationState` model has no `max_length` validator on the `records` field. After 1000+ evolution cycles, the YAML file grows without bound, eventually hitting the `MAX_YAML_SIZE_BYTES` (1MB) cap in `YamlStore.read()`, causing a `ValueError` crash on the next `_load_state()` call.
- **Trigger:** Long-running framework with many evolution cycles. Approximate threshold: ~1000-2000 records before YAML serialization exceeds 1MB.
- **Impact:** `ValueError: YAML file exceeds size cap` crash on CalibrationEngine initialization. Complete loss of calibration functionality. Since `__init__` calls `_load_state()`, the CalibrationEngine cannot be instantiated at all after this point.
- **Severity:** CRITICAL
- **Mitigation:** NOT ADDRESSED. FM-74 documents the intent but the code does not implement trimming. Add explicit trimming in `_save_state()`: `self._state.records = self._state.records[-100:]` before writing.
- **Phase:** Phase 2

---

**FM-87** | **Orchestrator `record_task_outcome()` Accesses `task.metrics.tokens_used` Which May Be Zero**
- **Component:** `engine/orchestrator.py` :: `record_task_outcome()` (design doc line 2264)
- **Failure:** `record_task_outcome()` calls `self.capability_tracker.record_outcome(tokens_used=task.metrics.tokens_used)`. `TaskMetrics.tokens_used` defaults to 0 and is only populated if the caller explicitly sets it. In the current codebase, no code in the orchestration pipeline sets `task.metrics.tokens_used` -- the `complete_execution()` method records `task.metrics.budget_allocated` (not `tokens_used`) to the budget tracker. If `tokens_used` is 0, the capability tracker's `avg_tokens` rolling average is corrupted: `(avg * (n-1) + 0) / n` systematically drags the average toward zero.
- **Trigger:** Every task completion where `tokens_used` has not been explicitly populated.
- **Impact:** `CapabilityMapEntry.avg_tokens` converges to 0 over time. The FM-41 learned complexity classifier uses `avg_tokens` thresholds (< 5000 = "small", < 20000 = "medium"). All task types eventually classified as "small" complexity, causing systematic budget under-allocation.
- **Severity:** CRITICAL
- **Mitigation:** NOT ADDRESSED. The design doc does not show where `tokens_used` is set. Either: (a) populate `tokens_used` from `budget_tracker.record_consumption()` results, or (b) guard `record_outcome()` to skip when `tokens_used == 0`.
- **Phase:** Phase 2

---

**FM-88** | **FM-18 Ledger `record_consumption()` Calls `_consumption_ledger._maybe_rotate()` Directly, Violating Encapsulation and Creating Race**
- **Component:** `engine/budget_tracker.py` :: `record_consumption()` (design doc lines 1720-1726)
- **Failure:** The FM-18 fix bypasses `JsonlWriter.append()` and directly manipulates internals: calls `self._consumption_ledger._maybe_rotate()`, opens `self._consumption_ledger.current_path` directly, implements its own `fcntl.flock()` locking. This creates two independent locking mechanisms on the same file: the `JsonlWriter.append()` method locks the data file itself, while this code also locks the data file. If another component (e.g., audit logging) uses `JsonlWriter.append()` on the same writer, the two locking schemes can interleave: one caller acquires the flock on the file descriptor, writes, releases; the other caller's `_maybe_rotate()` could rotate the file between the first caller's `_maybe_rotate()` and `open()` calls, causing the first caller to write to the old (now rotated) file.
- **Trigger:** Concurrent consumption recording and JSONL rotation.
- **Impact:** Consumption records written to rotated files that may be outside the current window scan. Token consumption silently lost from window totals.
- **Severity:** CRITICAL
- **Mitigation:** NOT ADDRESSED. The code should use `JsonlWriter.append()` with a proper `BaseLogEntry` subclass instead of bypassing the writer's API. If custom fields are needed, create a `ConsumptionLogEntry` subclass.
- **Phase:** Phase 2

---

**FM-89** | **FM-18 Ledger Rebuild Reads All Entries on Every `get_window()` Call**
- **Component:** `engine/budget_tracker.py` :: `_rebuild_window_from_ledger()` (design doc lines 1752-1780), `get_window()` (design doc line 1805)
- **Failure:** `get_window()` now delegates to `_rebuild_window_from_ledger()`, which calls `self._consumption_ledger.read_entries(since=window_start, limit=10_000)`. `read_entries()` opens every file in `_all_log_files()`, reads line-by-line, parses JSON, and filters by timestamp. For a 5-hour window with heavy usage (e.g., 1 consumption record per minute = 300 records, or bursts of 10+ per minute = 3000+ records), this is a full file scan on every `get_window()` call. `get_window()` is called in `process_task()` (via budget pressure check), `record_consumption()`, and `get_budget_summary()`. Under normal operation, this creates O(n) I/O per task start.
- **Trigger:** Any system running for more than a few minutes with active task processing.
- **Impact:** Severe performance degradation. Each `get_window()` call involves opening multiple files, reading potentially thousands of lines, JSON-parsing each, and filtering. This dominates wall-clock time of task processing. Design doc FM-75 acknowledges this ("cached rebuild with mtime check") but defers it to Phase 3.
- **Severity:** CRITICAL
- **Mitigation:** PARTIALLY ADDRESSED. FM-75 proposes caching but defers to Phase 3. The `_persist_window(window)` call in `record_consumption()` provides a cached snapshot, but `get_window()` does NOT read from this cache -- it always rebuilds from the ledger. Fix: `get_window()` should read the cached `window.yaml` first and only rebuild if the ledger's mtime is newer.
- **Phase:** Phase 2 (performance is unacceptable for production; cannot defer to Phase 3)

---

**FM-90** | **VoiceProfile Fields `tone` and `style` Can Be `None`, Causing `_voice_distance()` Crash**
- **Component:** `engine/diversity_engine.py` :: `_voice_distance()` (design doc lines 423-447)
- **Failure:** `VoiceProfile.tone` and `VoiceProfile.style` are `str | None` (from `voice.py` line 49-50: `tone: str | None = None`, `style: str | None = None`). The `_voice_distance()` function compares `a.tone == b.tone` and `a.style == b.style`. When both are `None`, Python evaluates `None == None` as `True`, giving distance 0.0 -- which is correct (both have no tone = no difference). However, when one is `None` and the other is a string, `None == "tone_formal"` is `False`, giving distance 1.0. This is semantically questionable: an agent with no configured tone versus one with an explicit tone gets maximum distance, even though "no tone" might effectively resolve to a default.
- **Trigger:** Mixed deployment where some agents have explicit voice profiles and others use defaults.
- **Impact:** VDI systematically inflated when comparing agents with voice profiles against those without. The framework perceives high voice diversity when the actual behavioral diversity may be lower. SRD composite score overstated by up to 0.2 * VDI_WEIGHT = 0.04 per pair.
- **Severity:** CRITICAL (the computed metric is systematically wrong, not just noisy)
- **Mitigation:** NOT ADDRESSED. The code handles `persona=None` as a special case but applies no equivalent logic to `tone=None` or `style=None`. Either resolve `None` to a framework default before comparison, or define the semantics explicitly (e.g., None = "unspecified" gets distance 0.5 from any explicit value).
- **Phase:** Phase 2

---

## HIGH SEVERITY (14 total)

---

**FM-91** | **SRD History File Non-Atomic Read-Modify-Write**
- **Component:** `engine/diversity_engine.py` :: `append_srd_history()` (design doc lines 616-629)
- **Failure:** `append_srd_history()` reads the history file via `read_raw()`, appends a value, then writes it back via `write_raw()`. Between the read and write, another concurrent call to `append_srd_history()` (from a different task completing simultaneously) could read the same state and overwrite the first caller's append. YamlStore's advisory lock only covers the individual `write_raw()` call, not the full read-modify-write cycle.
- **Trigger:** Two tasks complete simultaneously and both call `record_task_outcome()`, which calls `append_srd_history()`.
- **Impact:** One SRD value silently lost from history. Stagnation detector sees a gap in the time series. Low-frequency event but accumulates over time.
- **Severity:** HIGH
- **Mitigation:** Design doc FM-77 acknowledges this: "Uses `yaml_store.write_raw()` which has advisory locking. Acceptable for Phase 2 (low frequency)." This is overly optimistic -- concurrent task completions are not rare in multi-agent frameworks.
- **Phase:** Phase 2

---

**FM-92** | **StagnationDetector `_tone_history` Contains `set` Objects That Cannot Round-Trip Through YAML**
- **Component:** `engine/stagnation_detector.py` :: `_save_state()` (design doc lines 904-913), `_load_state()` (design doc lines 915-929)
- **Failure:** `_save_state()` serializes `_tone_history` as `[list(s) for s in self._tone_history]`. `_load_state()` reconstructs as `self._tone_history.append(set(v))`. This works for round-tripping. However, YAML serialization of lists can reorder elements (YAML sequences are ordered but if the original set was `{"b", "a"}`, `list()` gives arbitrary order). More critically: if `agent_tones` passed to `check_all()` is an empty set `set()`, it serializes as an empty list `[]`, which `set([])` correctly reconstructs as empty set. But the comparison `all(t == first for t in recent_tones)` compares sets. Two empty sets are equal, so `len(first) <= 1` is True (0 <= 1). An empty tone name `next(iter(first))` raises `StopIteration`.
- **Trigger:** 5+ consecutive tasks where `agent_tones` is an empty set (no voice atoms assigned).
- **Impact:** `StopIteration` exception crashes `_check_voice_stagnation()`. Since `check_all()` calls `_check_voice_stagnation()` before `_save_state()`, the state is not saved, but the signal propagation is lost and the caller receives an unhandled exception.
- **Severity:** HIGH
- **Mitigation:** NOT ADDRESSED. The guard `if first else "none"` (design doc line 859) uses conditional expression, but `next(iter(first))` is only reached when `first` is truthy. However, an empty set is falsy, so `tone_name = "none"` would be selected. Actually, re-reading: `next(iter(first)) if first else "none"` -- this is correct Python. The `if first` guards the `next(iter(...))`. So the empty-set case IS handled. **Revised analysis:** The `StopIteration` does NOT fire. However, the semantics are still wrong: "no tones assigned for 5 tasks" is flagged as "all agents using same tone 'none'" which is misleading. And the real issue remains: `set` objects in a deque don't round-trip cleanly if YAML changes list ordering. The ordering issue is benign since sets are compared with `==` regardless of internal ordering.
- **Revised Severity:** MEDIUM (misleading signal text, not a crash)
- **Mitigation:** PARTIALLY ADDRESSED. The code works but produces misleading stagnation signals when voice atoms are not configured.
- **Phase:** Phase 2

---

**FM-93** | **CapabilityTracker Rolling Average Formula Wrong After First Record**
- **Component:** `engine/capability_tracker.py` :: `record_outcome()` (design doc lines 1019-1027)
- **Failure:** The rolling average update is `entry.avg_tokens = (entry.avg_tokens * (n - 1) + tokens_used) / n` where `n = entry.attempts` (already incremented). On the first call: `attempts` goes from 0 to 1, so `n=1`, formula is `(0 * 0 + tokens_used) / 1 = tokens_used`. Correct. On the second call: `n=2`, formula is `(tokens_used_1 * 1 + tokens_used_2) / 2`. Correct. The formula is mathematically sound for a running mean. However, `avg_review_confidence` has the guard `if review_confidence > 0`. If the first record has `review_confidence=0` (reviewer did not provide confidence) and the second has `review_confidence=0.8`, the formula computes `(0.0 * 1 + 0.8) / 2 = 0.4`. But only one actual confidence was recorded, so the correct average should be 0.8. The `if review_confidence > 0` guard skips the update entirely for zero-confidence records, but does NOT skip incrementing `n` (which already happened for `attempts`). This means `n` includes records without confidence data, diluting the average.
- **Trigger:** Any task where the reviewer does not provide a confidence score (review_confidence=0.0).
- **Impact:** `avg_review_confidence` systematically underreported. After 10 tasks with 5 having confidence scores, the denominator is 10 but only 5 numerator contributions exist. Average is half of true average.
- **Severity:** HIGH
- **Mitigation:** NOT ADDRESSED. Either track a separate `confidence_count` or skip the division when `review_confidence == 0`.
- **Phase:** Phase 2

---

**FM-94** | **CalibrationEngine `_apply_overcalibration_response()` Double-Increments Evidence Threshold**
- **Component:** `engine/calibration_engine.py` :: `_apply_overcalibration_response()` (design doc lines 1361-1403)
- **Failure:** The method first unconditionally increments `evidence_threshold += 0.05` (line 1373). Then it checks `get_false_positive_rate()` and, if FP > 10%, increments again: `evidence_threshold += 0.05` (line 1389). If both the ECE alert AND the false positive rate are triggered simultaneously (which they often will be, since overconfidence causes both high ECE and high false positives), the evidence threshold increases by 0.10 in a single call. With the cap at 0.9 and starting at 0.6, it takes only 3 consecutive overcalibration events to reach the maximum 0.9 threshold. Then the false negative check at line 1397 decrements by 0.05, but this creates oscillation: threshold jumps up by 0.10, then down by 0.05, then up by 0.10, producing a ratcheting upward pattern.
- **Trigger:** Framework experiences overconfident predictions (common during bootstrap).
- **Impact:** Evidence threshold ratchets to 0.9 within a few cycles, making it nearly impossible for any evolution proposal to be approved. Self-improvement effectively halted.
- **Severity:** HIGH
- **Mitigation:** NOT ADDRESSED. The FP/FN adjustments should be mutually exclusive with the base overcalibration response, or use a single combined adjustment.
- **Phase:** Phase 2

---

**FM-95** | **CalibrationEngine ECE Treats Negative `actual_improvement` Asymmetrically**
- **Component:** `engine/calibration_engine.py` :: `record_outcome()` (design doc lines 1237-1238), `_recompute_ece()` (design doc lines 1345-1359)
- **Failure:** `calibration_error = predicted_confidence - actual_improvement`. `predicted_confidence` is in [0, 1] (Pydantic constraint). `actual_improvement` can be negative (an evolution that made things worse). If `predicted_confidence = 0.3` and `actual_improvement = -0.2`, then `calibration_error = 0.3 - (-0.2) = 0.5`. This is a large positive error, correctly indicating overconfidence. But the ECE is `mean(abs(calibration_error))`. Since the error is already `predicted - actual`, the absolute value means a negative `actual_improvement` always produces a large ECE contribution even if `predicted_confidence` was low. An evolution with predicted=0.1 and actual=-0.5 gives |0.1 - (-0.5)| = 0.6 ECE contribution, even though the prediction was cautious (0.1 confidence). The calibration error conflates "prediction quality" with "evolution outcome quality."
- **Trigger:** Any evolution that produces negative improvement (regression).
- **Impact:** ECE inflated by bad evolution outcomes even when predictions were conservative. Overcalibration response triggered prematurely. Framework becomes too conservative about evolution.
- **Severity:** HIGH
- **Mitigation:** NOT ADDRESSED. Standard ECE computation bins predictions into calibration buckets and measures the gap between mean predicted probability and empirical frequency. The implementation's approach of `|predicted - actual|` is not standard ECE -- it's mean absolute error between a probability and a continuous outcome. This is a fundamental formula mismatch.
- **Phase:** Phase 2

---

**FM-96** | **`record_task_outcome()` Accesses `task.review.verdict` and `task.review.reviewer_confidence` Without Full Null Guard**
- **Component:** `engine/orchestrator.py` :: `record_task_outcome()` (design doc lines 2259-2260)
- **Failure:** The code checks `task.review is not None and task.review.verdict in (...)` for the `success` variable. Correct. But `confidence = task.review.reviewer_confidence if task.review else 0.0` -- this accesses `task.review.reviewer_confidence`. If `task.review` exists but `reviewer_confidence` is somehow missing or the model validation failed partially, the code could raise `AttributeError`. More practically: the design doc says `record_task_outcome()` is "called after task reaches COMPLETE or VERDICT(fail) status." For VERDICT(fail) tasks, `task.review` should exist (the review engine creates it). But if the task was manually transitioned to COMPLETE (e.g., by a human operator bypassing the review engine), `task.review` could be `None`, and `success` would be `False` even though the task was manually approved. This silently records a failure for a successful task.
- **Trigger:** Manual task completion bypassing review engine. Or a task where review was skipped.
- **Impact:** CapabilityMap records false failures, depressing success rates. Weak area detection produces false positives.
- **Severity:** HIGH
- **Mitigation:** NOT ADDRESSED. Add guard: if `task.review is None` and task status is COMPLETE, either skip recording or assume success with low confidence.
- **Phase:** Phase 2

---

**FM-97** | **FM-18 Ledger: `record_consumption()` Still Does Read-Modify-Write on Weekly Budget**
- **Component:** `engine/budget_tracker.py` :: `record_consumption()` (design doc lines 1738-1740)
- **Failure:** The FM-18 fix replaces the window budget's read-modify-write with an append-only ledger. However, lines 1738-1740 still do: `weekly = self.get_weekly(); weekly.tokens_consumed += tokens; self._persist_weekly(weekly)`. This is the exact same read-modify-write pattern that FM-18 was supposed to fix, just applied to the weekly budget instead of the window budget. The original FM-19 (Phase 1.5) identified this as a race condition, and it remains unresolved.
- **Trigger:** Two concurrent `record_consumption()` calls.
- **Impact:** Weekly budget consumption undercounted. Same as FM-19 from Phase 1.5 -- one increment silently lost per race.
- **Severity:** HIGH
- **Mitigation:** NOT ADDRESSED. FM-18 fix was incomplete: it fixed the window budget but not the weekly budget. Either extend the ledger approach to weekly budgets, or use a file lock spanning the full read-modify-write cycle for the weekly budget.
- **Phase:** Phase 2

---

**FM-98** | **StagnationDetector State Corruption on `_load_state()` With Mistyped Data**
- **Component:** `engine/stagnation_detector.py` :: `_load_state()` (design doc lines 915-929)
- **Failure:** `_load_state()` reads raw YAML and iterates over values, casting each to `float()`, `str()`, `int()`, or constructing `set()`. If the YAML file was manually edited or corrupted (e.g., `srd_history: ["not_a_number", 0.5]`), `float("not_a_number")` raises `ValueError`. The `except FileNotFoundError: pass` handler does NOT catch `ValueError`, `TypeError`, or `KeyError`. Any corruption in the state file crashes `StagnationDetector.__init__()`, preventing the entire Phase 2 self-awareness stack from initializing.
- **Trigger:** Manual editing of state YAML files, or partial write corruption.
- **Impact:** `ValueError` or `TypeError` crash on StagnationDetector initialization. Cascading failure: Orchestrator's `record_task_outcome()` cannot run diversity/stagnation checks.
- **Severity:** HIGH
- **Mitigation:** Design doc FM-72 says "Catch `ValueError`/`KeyError` in `_load_state()`, log warning, reset to empty state." But the actual code (design doc lines 917-929) only catches `FileNotFoundError`. The mitigation is documented but NOT implemented.
- **Phase:** Phase 2

---

**FM-99** | **DiversityEngine `create_snapshot()` Produces Timestamps That May Differ from SRDMeasurement**
- **Component:** `engine/diversity_engine.py` :: `compute_srd()` (design doc line 564), `create_snapshot()` (design doc line 592)
- **Failure:** `compute_srd()` creates `SRDMeasurement` with `timestamp=datetime.now(timezone.utc)`. Then `create_snapshot()` is called separately and creates `DiversitySnapshot` with its own `timestamp=datetime.now(timezone.utc)`. These are two separate `now()` calls. The snapshot timestamp will be later than the SRD timestamp by the duration of the `compute_srd()` execution. Additionally, the `DiversityLogEntry` created in `record_task_outcome()` uses `snapshot.timestamp` (design doc line 2305), which is neither the SRD timestamp nor the task completion timestamp.
- **Trigger:** Every diversity measurement. Time skew increases under load.
- **Impact:** Audit log timestamps do not precisely match SRD measurement timestamps. Timeline queries using exact timestamp matching will miss entries. Cross-stream timeline reconstruction may show events in wrong order.
- **Severity:** HIGH
- **Mitigation:** NOT ADDRESSED. Use a single timestamp created at the start of `record_task_outcome()` and pass it through to all sub-components.
- **Phase:** Phase 2

---

**FM-100** | **`compute_gap_assessment()` Has No Validation That Inputs Are Meaningful**
- **Component:** `engine/calibration_engine.py` :: `compute_gap_assessment()` (design doc lines 1268-1299)
- **Failure:** The method accepts `verifier_accuracy` and `generator_accuracy` as floats in [0, 1] (Pydantic constraint on `GapAssessment`). But there is no validation that `benchmark_task_count` is sufficient for statistical significance. A gap assessment with `benchmark_task_count=1` is treated identically to one with `benchmark_task_count=1000`. The `self_improvement_reliable` property reports True/False based solely on the gap value, regardless of sample size.
- **Trigger:** Early bootstrap when only 1-2 benchmark tasks have been run.
- **Impact:** Unreliable gap assessment with high variance treated as authoritative. Phase 4+ may make evolution decisions based on a gap computed from a single task.
- **Severity:** HIGH
- **Mitigation:** NOT ADDRESSED. Add a minimum `benchmark_task_count` threshold (e.g., 10) below which `self_improvement_reliable` always returns False.
- **Phase:** Phase 2

---

**FM-101** | **`YamlStore.delete()` Method Called by FM-18 Archival But Does Not Exist**
- **Component:** `state/yaml_store.py` (missing method); called from `engine/cost_gate.py` :: `archive_old_records()` (design doc line 2148: `self.yaml_store.delete(path)`)
- **Failure:** The current `YamlStore` class (159 lines) has no `delete()` method. The design doc Part 8.8 says "Add `delete` method to `YamlStore` if not present (needed for archival)" (line 2160) but does not provide the implementation. The archival method `archive_old_records()` calls `self.yaml_store.delete(path)` which will raise `AttributeError`.
- **Trigger:** Any call to `archive_old_records()`.
- **Impact:** `AttributeError: 'YamlStore' object has no attribute 'delete'`. Cost record archival completely non-functional. R8/R16 fix is broken.
- **Severity:** HIGH
- **Mitigation:** NOT ADDRESSED. The design doc acknowledges the need but does not provide the implementation. This is the same class of error as FM-06 (Phase 1.5) where `ensure_dir()` was missing -- except `ensure_dir()` has since been implemented (confirmed in current yaml_store.py line 145).
- **Phase:** Phase 2

---

**FM-102** | **`AuditLogger` Missing `log_diversity()` Method -- LogStream.DIVERSITY Writer Exists But No Typed Method**
- **Component:** `audit/logger.py` (existing, 78 lines)
- **Failure:** The current `AuditLogger` has methods for `log_evolution`, `log_task`, `log_decision`, `log_resource`, `log_environment`, `log_trace` -- but NOT `log_diversity()`. The design doc Part 7.2 (lines 1640-1642) says to add `log_diversity(self, entry: DiversityLogEntry)`. The `LogStream.DIVERSITY` enum value exists and a `JsonlWriter` is created for it in `__init__()`, but there is no typed dispatch method. `record_task_outcome()` calls `self.audit_logger.log_diversity(...)` (design doc line 2303) which will raise `AttributeError`.
- **Trigger:** Any call to `record_task_outcome()` that measures diversity.
- **Impact:** `AttributeError: 'AuditLogger' object has no attribute 'log_diversity'`. Diversity metrics never logged to audit trail. No historical diversity data for trend analysis.
- **Severity:** HIGH
- **Mitigation:** ADDRESSED IN DESIGN (Part 7.2 lines 1640-1658 show the addition). This is an implementation ordering issue: the `log_diversity()` method must be added before orchestrator integration (Step 8 before Step 11 in dependency graph). Documented but easy to miss.
- **Phase:** Phase 2

---

**FM-103** | **`DiversityLogEntry` Model Not Defined in Existing `models/audit.py`**
- **Component:** `models/audit.py` (existing); referenced from `engine/orchestrator.py` :: `record_task_outcome()` (design doc lines 2301-2313)
- **Failure:** The design doc Part 2.3 (lines 305-319) defines `DiversityLogEntry` as a new class to add to `models/audit.py`. If this is not added before `record_task_outcome()` is integrated, the import `from ..models.audit import DiversityLogEntry` at line 2301 raises `ImportError`. The `LogStream.DIVERSITY` enum exists but the typed entry class does not.
- **Trigger:** Any import of `DiversityLogEntry` before the model is created.
- **Impact:** `ImportError` crash. Same class of issue as FM-102 -- model and method must be created before integration code that references them.
- **Severity:** HIGH
- **Mitigation:** ADDRESSED IN DESIGN (Part 2.3). Implementation ordering enforced by dependency graph (Step 7 before Step 11). But if Steps 7-8 are skipped or deferred, Step 11 crashes.
- **Phase:** Phase 2

---

**FM-104** | **StagnationDetector Framework-Level Stagnation Fires Indefinitely Once Triggered**
- **Component:** `engine/stagnation_detector.py` :: `_check_framework_stagnation()` (design doc lines 872-901), `record_evolution()` (design doc lines 807-811)
- **Failure:** `_tasks_since_evolution` is incremented on every `check_all()` call. Once it exceeds `FRAMEWORK_EVOLUTION_THRESHOLD` (10), the framework stagnation signal fires on EVERY subsequent call. The only reset mechanism is `record_evolution(tier)` with `tier >= 2`. In Phase 2, there IS no evolution engine -- Phase 2 is measurement-only. `record_evolution()` is never called. Therefore, after 10 tasks, the framework stagnation signal fires on every task completion for the entire Phase 2 deployment.
- **Trigger:** Processing 10+ tasks in Phase 2 (no evolution engine exists yet).
- **Impact:** Perpetual stagnation warning on every task. Log noise. Audit trail flooded with identical framework stagnation signals. If Phase 4+ treats these signals as actionable, the accumulated signal count (potentially hundreds) could trigger extreme corrective measures.
- **Severity:** HIGH
- **Mitigation:** NOT ADDRESSED. Either: (a) disable framework-level stagnation detection until the evolution engine exists, or (b) add a `max_consecutive_signals` cap after which the signal is suppressed with a "persistent" marker.
- **Phase:** Phase 2

---

## MEDIUM SEVERITY (18 total)

---

**FM-105** | **TF-IDF Cosine Distance Is Order-Sensitive for Document Pairs**
- **Component:** `engine/diversity_engine.py` :: `compute_text_diversity()` (design doc lines 467-484)
- **Failure:** The IDF computation uses the set of all documents. When new outputs are added (e.g., comparing tasks across time), the IDF values change. Two identical sets of outputs compared at different points in time (with different IDF dictionaries) will produce different distance values. This is expected TF-IDF behavior, but it means SRD values are NOT comparable across different measurements unless the document corpus is the same.
- **Trigger:** Comparing SRD scores from different tasks (which always have different IDF contexts).
- **Impact:** Stagnation detector compares SRD values across tasks as if they were on the same scale, but they are not. A task with 2 very different outputs and a task with 5 slightly different outputs may produce similar SRD scores despite different diversity levels.
- **Severity:** MEDIUM
- **Mitigation:** NOT ADDRESSED. The design doc acknowledges this implicitly by deferring embedding-based distance to Phase 3.5 (D-1). For Phase 2, TF-IDF is accepted as an approximation.
- **Phase:** Deferred (Phase 3.5, D-1)

---

**FM-106** | **`_cosine_distance()` Epsilon Fallback Produces Non-Zero Distance for Zero Vectors**
- **Component:** `engine/diversity_engine.py` :: `_cosine_distance()` (design doc lines 410-419)
- **Failure:** `mag1 = math.sqrt(sum(v ** 2 for v in v1.values())) or 1e-10`. If `v1` is a non-empty dict with all zero values (e.g., all TF-IDF scores are zero because no IDF matches), `mag1 = 0.0`, which is falsy, so `mag1 = 1e-10`. `mag2` similarly. `dot = 0`. `similarity = 0 / (1e-10 * 1e-10) = 0`. `distance = 1.0`. Two documents that happen to have no overlapping IDF terms (but are both non-empty) get maximum distance 1.0, even if this doesn't reflect actual semantic diversity.
- **Trigger:** Documents with completely non-overlapping vocabularies.
- **Impact:** SRD inflated when agents use entirely different vocabularies. This could mask actual convergent thinking expressed with different words.
- **Severity:** MEDIUM
- **Mitigation:** NOT ADDRESSED. This is a known limitation of bag-of-words approaches. Embedding-based distance (D-1) would address this.
- **Phase:** Deferred (Phase 3.5)

---

**FM-107** | **Capability Map's `blind_spots` Becomes Stale If `ALL_KNOWN_TASK_TYPES` Changes**
- **Component:** `engine/capability_tracker.py` :: `ALL_KNOWN_TASK_TYPES` (design doc lines 962-971), `_update_blind_spots()` (design doc lines 1095-1100)
- **Failure:** `ALL_KNOWN_TASK_TYPES` is a hardcoded list of 8 task types. If a Phase 3+ change adds new task types to the orchestrator's `_classify_task_type()`, the `ALL_KNOWN_TASK_TYPES` list must be manually synchronized. If the lists diverge, `_update_blind_spots()` either: (a) misses new task types (not in `ALL_KNOWN_TASK_TYPES` = never flagged as blind spots), or (b) reports removed task types as permanent blind spots.
- **Trigger:** Adding or removing task types in future phases without updating `ALL_KNOWN_TASK_TYPES`.
- **Impact:** Blind spot detection produces false negatives (missed new types) or false positives (removed types). Low immediate impact since blind spots are informational in Phase 2.
- **Severity:** MEDIUM
- **Mitigation:** NOT ADDRESSED. Should derive the list dynamically from `_classify_task_type()`'s return values, or load from YAML config (which `self-assessment.yaml` already has under `known_task_types`).
- **Phase:** Phase 2

---

**FM-108** | **CalibrationEngine `overcalibration_streak` Only Tracks Positive Errors, Misses Systematic Under-Confidence**
- **Component:** `engine/calibration_engine.py` :: `record_outcome()` (design doc lines 1240-1243)
- **Failure:** `if record.calibration_error > 0: streak += 1; else: streak = 0`. This tracks consecutive overconfidence (predicted > actual). But there is no equivalent tracking for consecutive underconfidence (predicted < actual). Systematic under-confidence (the framework is too conservative) is never detected. The `confidence_deflation` can only increase (via `_apply_overcalibration_response()`), never decrease based on systematic under-prediction.
- **Trigger:** Framework becomes overly conservative after early overcalibration events.
- **Impact:** One-directional calibration drift. The framework becomes permanently more conservative over time. Confidence deflation accumulates monotonically with no recovery path except manual reset.
- **Severity:** MEDIUM
- **Mitigation:** PARTIALLY ADDRESSED. The false negative rate check (design doc lines 1396-1403) can lower the evidence threshold, but it cannot reduce `confidence_deflation`. There is no code path that decreases `confidence_deflation`.
- **Phase:** Phase 2

---

**FM-109** | **`get_estimated_complexity()` Returns Empty String Instead of None**
- **Component:** `engine/capability_tracker.py` :: `get_estimated_complexity()` (design doc lines 1075-1093)
- **Failure:** When insufficient data exists, the method returns `""` (empty string). The caller in orchestrator's `_classify_complexity()` checks `if learned:` (design doc line 1973). In Python, `if "":` is falsy, so the empty string correctly triggers the fallback. However, the docstring says "Returns None if insufficient data" but the code returns `""`. If a future caller checks `if learned is not None:` instead of `if learned:`, the empty string would be truthy, and the function would return an empty complexity string to the budget tracker, which would try to look up cold seed key `"feature_"` (task_type + underscore + empty).
- **Trigger:** API misuse by future callers trusting the docstring over the implementation.
- **Impact:** Incorrect cold seed lookup key. Budget tracker returns 10,000 default instead of correct seed value.
- **Severity:** MEDIUM
- **Mitigation:** NOT ADDRESSED. Either return `None` as documented or update the docstring to match the implementation.
- **Phase:** Phase 2

---

**FM-110** | **Orchestrator `record_task_outcome()` Loads Task From Disk After Completion**
- **Component:** `engine/orchestrator.py` :: `record_task_outcome()` (design doc line 2253: `task = self.task_lifecycle._load_task(task_id)`)
- **Failure:** `record_task_outcome()` is called after the task reaches COMPLETE or VERDICT(fail). It loads the task from disk using `_load_task()`, which reads the active task file. But `handle_verdict()` may have already transitioned the task to COMPLETE, and the `TaskLifecycle` may have moved the file to a completed directory or archive. If the file has been moved, `_load_task()` raises `FileNotFoundError`.
- **Trigger:** `record_task_outcome()` called after task file has been archived or moved by the lifecycle system.
- **Impact:** `FileNotFoundError` crash. No diversity or capability metrics recorded for the task. Audit trail missing this task's measurements.
- **Severity:** MEDIUM
- **Mitigation:** NOT ADDRESSED. Either call `record_task_outcome()` BEFORE the final transition, or have `_load_task()` search both active and completed directories.
- **Phase:** Phase 2

---

**FM-111** | **`DiversitySnapshot.agent_outputs_hash` Truncated to 16 Characters May Collide**
- **Component:** `engine/diversity_engine.py` :: `create_snapshot()` (design doc line 585: `hexdigest()[:16]`)
- **Failure:** SHA-256 truncated to 16 hex characters = 64 bits of entropy. Birthday paradox: collision expected after ~2^32 (4 billion) snapshots. For practical purposes this is safe. However, the hash is computed from `"||".join(agent_outputs)` -- if agent outputs contain `"||"`, the delimiter is ambiguous. Outputs `["a||b", "c"]` and `["a", "b||c"]` produce different joins, so this is actually fine. The real issue: the hash is for "reproducibility" (design doc line 193), but the outputs themselves are not persisted alongside the hash, so the hash cannot be used to verify reproducibility -- there is nothing to compare against.
- **Trigger:** Any attempt to use the hash for verification.
- **Impact:** Dead metadata. The hash exists but serves no functional purpose without persisted outputs.
- **Severity:** MEDIUM
- **Mitigation:** NOT ADDRESSED. Either persist the agent outputs (expensive) or document that the hash is diagnostic-only.
- **Phase:** Deferred

---

**FM-112** | **FM-63 Fix: `check_agent_health()` Datetime Comparison May Fail on Naive vs. Aware Timestamps**
- **Component:** `engine/agent_spawner.py` :: `check_agent_health()` (design doc lines 2081-2114)
- **Failure:** The FM-63 fix computes `elapsed = (datetime.now(timezone.utc) - last_beat).total_seconds()` where `last_beat = datetime.fromisoformat(heartbeat)`. If the heartbeat was written by existing code using `datetime.utcnow()` (naive UTC, no timezone info -- as flagged in Phase 1.5 FM-05), then `last_beat` is a naive datetime. `datetime.now(timezone.utc) - naive_datetime` raises `TypeError: can't subtract offset-naive and offset-aware datetimes`. This is the exact same timezone mismatch identified in FM-05 (Phase 1.5) but now applied to the heartbeat system.
- **Trigger:** Agent heartbeat written by Phase 1 code (uses `datetime.utcnow()`) read by Phase 2 code (uses `datetime.now(timezone.utc)`).
- **Impact:** `TypeError` crash in `check_agent_health()`. Cascading: `despawn_idle_agents()` crashes, idle agents never cleaned up.
- **Severity:** MEDIUM (if FM-05 is fixed first, this is a non-issue; if FM-05 is NOT fixed, this is HIGH)
- **Mitigation:** PARTIALLY ADDRESSED. Depends on FM-05 being resolved system-wide. The design doc does not explicitly acknowledge this dependency.
- **Phase:** Phase 2 (blocked by FM-05)

---

**FM-113** | **FM-57 `sync_from_usage()` Calls `self.record_consumption()` on `ResourceFacade` But Method Signature Unknown**
- **Component:** `engine/resource_facade.py` :: `sync_from_usage()` (design doc lines 2047-2069)
- **Failure:** The design doc shows `self.record_consumption(input_tokens=..., output_tokens=..., cached_tokens=...)` called on the ResourceFacade. But the `BudgetTracker.record_consumption()` signature is `record_consumption(self, tokens: int, is_cached: bool = False)` (design doc line 1695) -- it takes a single `tokens` int, not separate `input_tokens`/`output_tokens`/`cached_tokens`. The `ResourceFacade.record_consumption()` method is not defined in the design doc. This is an API contract mismatch between the facade and the tracker.
- **Trigger:** Any call to `sync_from_usage()`.
- **Impact:** Either `TypeError` (wrong arguments) or `AttributeError` (method doesn't exist on facade). FM-57 parse_usage integration is non-functional.
- **Severity:** MEDIUM
- **Mitigation:** NOT ADDRESSED. The facade must either define its own `record_consumption()` that marshals parameters, or `sync_from_usage()` must call `budget_tracker.record_consumption()` directly with the correct signature.
- **Phase:** Phase 2

---

**FM-114** | **DiversityEngine `compute_vdi()` Duplicates Distance Computation Logic**
- **Component:** `engine/diversity_engine.py` :: `compute_vdi()` (design doc lines 486-529)
- **Failure:** `compute_vdi()` calls `_voice_distance(profiles[i], profiles[j])` to get the weighted distance, then ALSO manually re-computes per-dimension distances inline (lines 508-518: `dim_totals["language"] += (0.0 if a.language == b.language else 1.0)` etc.). The per-dimension computation in the loop duplicates the logic in `_voice_distance()` but WITHOUT applying `_VDI_WEIGHTS`. The `dim_avgs` dict contains unweighted raw dimension distances, while `vdi_score` contains the weighted composite. If `_VDI_WEIGHTS` are changed, `dim_avgs` won't reflect the new weights, creating inconsistency between `vdi_score` and `dimension_scores`.
- **Trigger:** Any change to `_VDI_WEIGHTS` constants.
- **Impact:** `VDIMeasurement.dimension_scores` diverges from `vdi_score`. Audit viewer shows per-dimension scores that don't sum to the composite. Debugging confusion.
- **Severity:** MEDIUM
- **Mitigation:** NOT ADDRESSED. Refactor: have `_voice_distance()` return both the composite and per-dimension breakdown, eliminating duplication.
- **Phase:** Phase 2

---

**FM-115** | **Orchestrator `record_task_outcome()` Not Called From Any Existing Code Path**
- **Component:** `engine/orchestrator.py` :: `record_task_outcome()` (design doc lines 2237-2315)
- **Failure:** The method is defined but the design doc does not show it being called from `complete_execution()` or `handle_verdict()`. The existing `handle_verdict()` transitions VERDICT -> COMPLETE and dissolves the team, then returns. It does not call `record_task_outcome()`. The design doc Part 9.1 says to add this method but does not show the integration point in the existing pipeline. An implementer must determine where to insert the call.
- **Trigger:** Phase 2 implementation completed without calling `record_task_outcome()`.
- **Impact:** All four Phase 2 measurement systems (diversity, stagnation, capability, calibration) are defined but never invoked. Phase 2 collects zero data. The entire phase is dead code.
- **Severity:** MEDIUM (the systems exist and work if called, but the integration point is missing)
- **Mitigation:** NOT ADDRESSED. Add a call to `record_task_outcome()` in `handle_verdict()` after the COMPLETE transition, or in a new `finalize_task()` method that wraps both verdict handling and metric recording.
- **Phase:** Phase 2

---

**FM-116** | **`record_task_outcome()` Requires `agent_outputs` Parameter That No Existing Component Provides**
- **Component:** `engine/orchestrator.py` :: `record_task_outcome()` (design doc line 2241: `agent_outputs: list[str] | None = None`)
- **Failure:** The method needs `agent_outputs` (list of text outputs from each agent) for diversity measurement. No existing component in the framework stores or provides agent outputs as a list of strings. The `TeamManager` tracks subtask statuses but not output text. The `AgentRegistryEntry` has no output field. The `SubTask` model has no output field. The agent outputs exist only in the Claude Code Task tool responses, which are transient.
- **Trigger:** Any call to `record_task_outcome()` that wants diversity metrics.
- **Impact:** `agent_outputs` is always `None` because no component captures it. The `if agent_outputs is not None and len(agent_outputs) >= 2` guard is never true. Diversity measurement never runs. VDI, SRD, stagnation detection -- all non-functional.
- **Severity:** MEDIUM (framework works but Phase 2 diversity features are useless)
- **Mitigation:** NOT ADDRESSED. Need to add agent output capture to the subtask completion flow. Either: (a) add an `output_text` field to `SubTask`, populated when agents complete, or (b) add a separate output collection step between `complete_execution()` and `record_task_outcome()`.
- **Phase:** Phase 2

---

**FM-117** | **Audit Tree Viewer `render_timeline()` Calls `query_all()` Which Has O(n*m) Complexity**
- **Component:** `audit/tree_viewer.py` :: `render_timeline()` (design doc line 1556); `audit/logger.py` :: `query_all()` (existing lines 65-77)
- **Failure:** `query_all()` queries ALL 8 log streams, reading up to `limit` entries from each, then merges and sorts. With 8 streams and limit=50, it reads up to 400 entries, sorts them, and returns 50. For large audit logs (thousands of entries per stream), the per-stream reads are expensive. The timeline view is a user-facing UI command -- slow response degrades the debugging experience.
- **Trigger:** `render_timeline()` on a long-running session with many log entries.
- **Impact:** Slow audit viewer response. Multiple seconds of file I/O before any output appears.
- **Severity:** MEDIUM
- **Mitigation:** NOT ADDRESSED. Could be mitigated with per-stream limits proportional to total limit (e.g., `limit // len(streams)` per stream) or a merged-stream index file.
- **Phase:** Deferred

---

**FM-118** | **`_classify_task_type()` Does Not Use `ALL_KNOWN_TASK_TYPES` -- Can Return Unlisted Types**
- **Component:** `engine/orchestrator.py` :: `_classify_task_type()` (existing lines 255-283); `engine/capability_tracker.py` :: `ALL_KNOWN_TASK_TYPES` (design doc lines 962-971)
- **Failure:** `_classify_task_type()` can return "feature" as a catch-all default (line 283). The 8 types in `ALL_KNOWN_TASK_TYPES` include all possible return values, so this is currently consistent. However, `_classify_task_type()` has no assertion or check that its return value is in `ALL_KNOWN_TASK_TYPES`. If a future modification adds a return value like `"documentation"`, the capability tracker will track it as a valid type but never flag it as a blind spot (since it's not in the hardcoded list).
- **Trigger:** Future modification to `_classify_task_type()` adding new return values.
- **Impact:** Silent divergence between classifier and capability tracker's known types list. Same root cause as FM-107 but from the opposite direction.
- **Severity:** MEDIUM
- **Mitigation:** NOT ADDRESSED. Add a runtime assertion: `assert result in ALL_KNOWN_TASK_TYPES` or load both from the same YAML config source.
- **Phase:** Phase 2

---

**FM-119** | **FM-52 Cache Stats Persistence: `CacheManager._load_stats()` Returns Default on Any Exception**
- **Component:** `engine/cache_manager.py` :: `_load_stats()` (design doc lines 2026-2033)
- **Failure:** `_load_stats()` catches `FileNotFoundError` and returns a new `CacheStats()`. But if the YAML file exists but is corrupted (e.g., truncated write), `yaml_store.read()` raises `ValueError` or `ValidationError`, which is NOT caught. The cache manager's `__init__()` would crash.
- **Trigger:** Corrupted `cache-stats.yaml` file.
- **Impact:** `ValueError` crash on CacheManager initialization. Cache management non-functional.
- **Severity:** MEDIUM
- **Mitigation:** NOT ADDRESSED. Add broader exception handling: `except (FileNotFoundError, ValueError, ValidationError): return CacheStats()`.
- **Phase:** Phase 2

---

**FM-120** | **R6 IQR Filter: Quartile Computation Uses Integer Division**
- **Component:** `engine/budget_tracker.py` :: `_iqr_filter()` (design doc lines 1848-1860)
- **Failure:** `q1 = sorted_vals[n // 4]` and `q3 = sorted_vals[3 * n // 4]`. For `n=5`: `q1 = sorted_vals[1]`, `q3 = sorted_vals[3]`. For `n=7`: `q1 = sorted_vals[1]`, `q3 = sorted_vals[5]`. This is a non-standard quartile computation (standard methods use interpolation). For small sample sizes (4-10), the quartile estimates are coarse. More critically: for `n=4`, `q1 = sorted_vals[1]`, `q3 = sorted_vals[3]`, which are the second and fourth values. If all 4 values are identical (e.g., `[100, 100, 100, 100]`), `iqr = 0`, `lower = 100`, `upper = 100`, all values pass. Correct. But for `[100, 100, 100, 200]`: `q1 = 100`, `q3 = 200`, `iqr = 100`, `lower = -50`, `upper = 350`. All pass. The filter has no effect for 4-element lists with moderate spread.
- **Trigger:** Small sample sizes (4-10 values).
- **Impact:** IQR filter is ineffective at small sample sizes. Outlier contamination persists until more samples accumulate. The `_iqr_filter()` returns original data for `len < 4`, and near-original for `4 <= len <= 8`.
- **Severity:** MEDIUM
- **Mitigation:** PARTIALLY ADDRESSED. The fallback to cold seeds when `len(filtered) < rolling_threshold` provides a safety net. But the IQR filter's stated purpose (R6: remove outliers) is not fulfilled for realistic sample sizes.
- **Phase:** Deferred

---

**FM-121** | **FM-18 Ledger: `_rebuild_window_from_ledger()` Uses `read_entries()` with `limit=10_000`**
- **Component:** `engine/budget_tracker.py` :: `_rebuild_window_from_ledger()` (design doc lines 1765-1766)
- **Failure:** `read_entries(since=window_start, limit=10_000)` silently truncates at 10,000 entries. If window consumption exceeds 10,000 records (e.g., 5-hour window with 2000 records/hour during burst), the rebuild misses records beyond the limit. `tokens_consumed` is undercounted for the window.
- **Trigger:** Very high throughput: > 10,000 consumption records in a single window.
- **Impact:** Window budget shows more remaining capacity than truly exists. Agents overshoot the window budget. Budget pressure level understated.
- **Severity:** MEDIUM
- **Mitigation:** NOT ADDRESSED. Either remove the limit (risk: memory pressure) or use a streaming sum without loading all entries into memory.
- **Phase:** Phase 2

---

**FM-122** | **Orchestrator Phase 2 `__init__()` Signature Change Breaks Backward Compatibility**
- **Component:** `engine/orchestrator.py` :: `__init__()` (design doc lines 1932-1947)
- **Failure:** The design doc adds `capability_tracker: CapabilityTracker | None = None` as a new parameter to `__init__()`. Additionally, `diversity_engine`, `stagnation_detector` are assigned directly in `__init__()` body (design doc lines 2217-2219) without being constructor parameters. This is inconsistent: `capability_tracker` is a parameter while `diversity_engine` and `stagnation_detector` are set as `None` attributes. Any caller that constructs an `Orchestrator` must now pass the new parameter or rely on the default. Existing tests that use positional arguments will break if the parameter order changes.
- **Trigger:** Existing callers or tests using positional arguments to `Orchestrator()`.
- **Impact:** Test failures. Existing code passing positional arguments may silently assign wrong values to wrong parameters.
- **Severity:** MEDIUM
- **Mitigation:** PARTIALLY ADDRESSED. The parameter has a default of `None`, so keyword callers are fine. But the asymmetry between `capability_tracker` (constructor param) and `diversity_engine`/`stagnation_detector` (attribute assignment) is confusing and invites bugs.
- **Phase:** Phase 2

---

## LOW SEVERITY (15 total)

---

**FM-123** | **`compute_text_diversity()` Quadratic Time Complexity in Agent Count**
- **Component:** `engine/diversity_engine.py` :: `compute_text_diversity()` (design doc lines 467-484)
- **Failure:** Computes all pairwise distances: O(n^2) pairs where n = number of agents. For typical multi-agent tasks (2-5 agents), this is 1-10 pairs -- negligible. But the framework's `max_agents` is configurable. If future phases increase agent count to 20+, the TF-IDF computation becomes expensive (190+ pairs).
- **Trigger:** Agent count > 10.
- **Impact:** CPU time increases quadratically. For 20 agents: 190 pairs with TF-IDF vectorization per pair. Potentially seconds of computation per task completion.
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. Current agent cap (5) makes this academic. Future phases should sample pairs if agent count exceeds threshold.
- **Phase:** Deferred

---

**FM-124** | **StagnationDetector In-Memory Deques Have `maxlen=20` But YAML State Has No Matching Cap**
- **Component:** `engine/stagnation_detector.py` :: `__init__()` (design doc lines 700-704), `_save_state()` / `_load_state()`
- **Failure:** `_srd_history = deque(maxlen=20)`. `_save_state()` serializes `list(self._srd_history)`, which outputs at most 20 values. `_load_state()` appends values one by one to the deque, which auto-trims to 20. So the round-trip is consistent. However, if the YAML file is manually edited to have 100 values, `_load_state()` appends all 100 but the deque's `maxlen=20` silently discards the first 80. No warning is logged for the discarded entries.
- **Trigger:** Manual editing of stagnation state YAML with too many entries.
- **Impact:** Silent data truncation. Negligible in practice since manual editing is rare and the deque behavior is correct.
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. Could log a warning when loaded data exceeds deque maxlen.
- **Phase:** Deferred

---

**FM-125** | **`DiversitySnapshot.stagnation_signals` Contains Full `StagnationSignal` Objects, Creating Large YAML**
- **Component:** `engine/diversity_engine.py` :: `create_snapshot()` (design doc lines 576-601); `models/diversity.py` :: `DiversitySnapshot` (design doc lines 182-193)
- **Failure:** `DiversitySnapshot.stagnation_signals` is `list[StagnationSignal]`. Each `StagnationSignal` has 8 fields. A snapshot with 3 stagnation signals adds ~24 YAML key-value pairs to the snapshot file. Over time, `latest-snapshot.yaml` contains verbose signal data that is also logged to `diversity.jsonl` (via `DiversityLogEntry`). The data is duplicated across two persistence systems.
- **Trigger:** Every task with stagnation signals.
- **Impact:** Minor disk usage from duplication. Snapshot file grows but is overwritten (only latest is kept).
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. The snapshot stores full signals for debugging convenience. Acceptable trade-off.
- **Phase:** Deferred

---

**FM-126** | **CalibrationEngine `get_false_positive_rate()` and `get_false_negative_rate()` Include ALL Historical Records**
- **Component:** `engine/calibration_engine.py` :: `get_false_positive_rate()` (design doc lines 1301-1321), `get_false_negative_rate()` (design doc lines 1323-1343)
- **Failure:** Both methods iterate over ALL records in `self._state.records` where `actual_improvement is not None`. This includes arbitrarily old records. If the framework's behavior changed (e.g., after overcalibration response adjusted thresholds), historical FP/FN rates include data from before the adjustment. The rates are "lifetime" rates, not recent rates.
- **Trigger:** Any use of FP/FN rates after calibration adjustments.
- **Impact:** FP/FN rates are contaminated by pre-adjustment data. The `_apply_overcalibration_response()` method uses these rates to decide whether to tighten or loosen thresholds, but the rates reflect behavior under old thresholds, not current ones.
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. Should use a rolling window (e.g., last 20 records) instead of lifetime rates.
- **Phase:** Phase 2

---

**FM-127** | **R15 `compute_trends()` Halving Strategy Produces Different-Sized Halves**
- **Component:** `engine/budget_tracker.py` :: `compute_trends()` (design doc lines 2171-2201)
- **Failure:** `mid = len(metrics) // 2; first_half = metrics[:mid]; second_half = metrics[mid:]`. For `len=5`: `mid=2`, first=[0,1], second=[2,3,4]. First half has 2 items, second has 3. The averages are computed over different sample sizes, making the comparison slightly biased toward the second half's mean being more stable (larger sample).
- **Trigger:** Odd-length metrics list.
- **Impact:** Minor statistical bias. The 10% threshold (`* 0.9` / `* 1.1`) is coarse enough that the sample size difference is negligible.
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. Acceptable for the coarse trend detection purpose.
- **Phase:** Deferred

---

**FM-128** | **`DiversityLogEntry.stagnation_signals` Is `list[dict]`, Not `list[StagnationSignal]`**
- **Component:** `models/audit.py` :: `DiversityLogEntry` (design doc lines 310-319)
- **Failure:** `stagnation_signals: list[dict]` stores pre-dumped dicts (from `s.model_dump()` in `record_task_outcome()`). This loses type safety: the dict structure is not validated by Pydantic on read. If the `StagnationSignal` model changes fields, existing log entries with old dict shapes won't be caught by validation. Log entry consumers must manually parse the dict keys.
- **Trigger:** Reading old diversity log entries after StagnationSignal model changes.
- **Impact:** Silent schema drift in audit logs. Old entries may have different field names than current model expects.
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. Audit logs are append-only and schema evolution is expected. Consumers should be lenient with `.get()` calls.
- **Phase:** Deferred

---

**FM-129** | **Audit Tree Viewer Uses Emoji Character in Stagnation Rendering**
- **Component:** `audit/tree_viewer.py` :: `_render_diversity_branch()` (design doc line 1607)
- **Failure:** `node.add(f"[yellow]⚠ {level}:[/yellow] {desc}")` uses the Unicode warning sign (U+26A0). Terminal emulators that do not support full Unicode will render this as a replacement character or garbled output.
- **Trigger:** Running audit viewer on a terminal without Unicode support.
- **Impact:** Visual corruption of stagnation signals in the audit tree. No data loss; only display issue.
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. Replace with ASCII alternative (e.g., `[!]` or `WARN:`) for maximum compatibility.
- **Phase:** Deferred

---

**FM-130** | **CalibrationEngine `record_prediction()` Stores Deflated Confidence, Not Raw**
- **Component:** `engine/calibration_engine.py` :: `record_prediction()` (design doc lines 1180-1208)
- **Failure:** The `CalibrationRecord.predicted_confidence` stores the deflated value (`max(0.0, confidence - deflation)`), not the raw value. The raw confidence is logged but not persisted. This means the `calibration_error` is computed as `deflated_confidence - actual_improvement`, not `raw_confidence - actual_improvement`. If the deflation factor changes between prediction and outcome recording, the ECE reflects the deflated predictions, which is what we want (we're calibrating the system's adjusted predictions). However, there is no way to retroactively analyze whether the raw (pre-deflation) predictions were improving over time, since raw values are not stored.
- **Trigger:** Any analysis of raw prediction quality over time.
- **Impact:** Cannot distinguish "predictions are getting better" from "deflation is compensating for bad predictions." Limits diagnostic capability.
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. Add a `raw_confidence` field to `CalibrationRecord` alongside `predicted_confidence`.
- **Phase:** Deferred

---

**FM-131** | **`_iqr_filter()` Is a Static Method But Operates on `list[int]` Only**
- **Component:** `engine/budget_tracker.py` :: `_iqr_filter()` (design doc lines 1848-1860)
- **Failure:** Method signature is `list[int]` but the comparison `lower <= v <= upper` uses float arithmetic (since `iqr` is float from `q3 - q1` when both are ints: still int, but `1.5 * iqr` is float). `lower` and `upper` are floats. The comparison `lower <= v <= upper` works correctly for int `v` against float bounds. No actual bug, but the type annotation suggests integer-only when the method works for floats too.
- **Trigger:** N/A (cosmetic).
- **Impact:** None. Type annotation is overly restrictive but functionally correct.
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. Minor typing issue.
- **Phase:** Deferred

---

**FM-132** | **`record_task_outcome()` Returns `dict` With Non-Serializable Pydantic Models**
- **Component:** `engine/orchestrator.py` :: `record_task_outcome()` (design doc lines 2237-2315)
- **Failure:** The return dict contains values from `entry.model_dump()`, `srd.model_dump()`, `s.model_dump()`, and `snapshot.model_dump()`. These are JSON-compatible dicts, so serialization is fine. However, the `results` dict itself is not a Pydantic model and has no schema. Callers must know the dict structure implicitly. If any sub-model's `model_dump()` output changes (e.g., field renamed), callers break silently.
- **Trigger:** Callers accessing result dict keys by name.
- **Impact:** Fragile API. No compile-time or validation-time checking of result dict structure.
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. Could return a typed `TaskOutcomeResult` Pydantic model instead of a raw dict.
- **Phase:** Deferred

---

**FM-133** | **StagnationDetector Voice Check Requires Exact Set Equality Across 5 Tasks**
- **Component:** `engine/stagnation_detector.py` :: `_check_voice_stagnation()` (design doc lines 854-858)
- **Failure:** `all(t == first for t in recent_tones)` checks if all tone sets are identical. If one task uses `{"tone_formal"}` and another uses `{"tone_formal", "tone_casual"}` (team had two agents with different tones), these are different sets. The stagnation check would NOT fire even though `tone_formal` was used in every task -- just not exclusively. The check requires exact uniformity, not dominant-tone detection.
- **Trigger:** Teams where most agents use the same tone but one agent occasionally uses a different tone.
- **Impact:** Voice stagnation not detected when one tone dominates but is not exclusive. False negatives in stagnation detection.
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. The check catches the extreme case (complete uniformity) but misses the common case (one dominant tone). A more nuanced check would track tone frequency across tasks.
- **Phase:** Deferred

---

**FM-134** | **R8/R16 Archival: `archive_old_records()` Is Never Called Automatically**
- **Component:** `engine/cost_gate.py` :: `archive_old_records()` (design doc lines 2125-2157)
- **Failure:** The method exists but is not called from any lifecycle hook, scheduler, or periodic task. It must be manually invoked. No automated archival occurs.
- **Trigger:** Cost records accumulate without anyone calling `archive_old_records()`.
- **Impact:** Cost record YAML files grow unboundedly. Same as original R8/R16 but now with a fix that is available but never triggered.
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. Add a call to `archive_old_records()` in a periodic maintenance hook (e.g., at window refresh time).
- **Phase:** Phase 2

---

**FM-135** | **`_check_team_srd()` Uses Last N Values From History, Not Consecutive Task Values**
- **Component:** `engine/stagnation_detector.py` :: `_check_team_srd()` (design doc lines 813-831)
- **Failure:** `recent = list(self._srd_history)[-SRD_CONSECUTIVE_THRESHOLD:]` takes the last 3 values from the deque. The deque is appended in `check_all()` which is called after every task. If a task is skipped (e.g., solo task with no diversity measurement), the deque retains old values. The "3 consecutive tasks" is actually "3 most recent measurements" which may span non-consecutive tasks if some tasks were solo.
- **Trigger:** Mix of solo and multi-agent tasks.
- **Impact:** Stagnation detection looks at non-consecutive tasks. A healthy multi-agent task between two stagnant ones would break the "consecutive" count, but if the healthy task was solo (no SRD appended), the two stagnant values remain adjacent in the deque. False stagnation signal.
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. The deque approach inherently conflates "consecutive measurements" with "consecutive tasks." Could add timestamps to each entry and validate temporal adjacency.
- **Phase:** Deferred

---

**FM-136** | **`CapabilityMap` Model Has `extra="forbid"` -- Adding New Fields in Phase 3 Breaks Deserialization**
- **Component:** `models/self_assessment.py` :: `CapabilityMap`, `CapabilityMapEntry`, `CalibrationState` (all inherit from `FrameworkModel`)
- **Failure:** Same pattern as FM-07 (Phase 1.5): `FrameworkModel` uses `extra="forbid"`. Any Phase 3+ changes that add fields to these models will make existing YAML files unreadable by the new code. Rolling back from Phase 3 to Phase 2 would also break if Phase 3 persisted files with new fields.
- **Trigger:** Phase 3+ adding fields to self-assessment models.
- **Impact:** `pydantic.ValidationError: Extra inputs are not permitted` on reading existing state files.
- **Severity:** LOW (same as FM-07; known issue, documented)
- **Mitigation:** PARTIALLY ADDRESSED. FM-07 was identified in Phase 1.5. The same mitigation applies: either deploy atomically or use `extra="ignore"` for cross-phase models.
- **Phase:** Deferred

---

**FM-137** | **YAML Config Files `diversity.yaml` and `self-assessment.yaml` Not Loaded by Any Component**
- **Component:** `core/diversity.yaml` (design doc lines 2330-2373), `core/self-assessment.yaml` (design doc lines 2377-2414)
- **Failure:** The design doc defines two YAML config files with thresholds, weights, and known task types. However, `DiversityEngine.__init__()` does not load `diversity.yaml`. `StagnationDetector.__init__()` does not load `diversity.yaml`. `CapabilityTracker.__init__()` does not load `self-assessment.yaml`. `CalibrationEngine.__init__()` does not load `self-assessment.yaml`. All components use hardcoded constants (e.g., `SRD_FLOOR = 0.3`, `ECE_ALERT_THRESHOLD = 0.15`, `ALL_KNOWN_TASK_TYPES = [...]`). The YAML configs are dead files.
- **Trigger:** Phase 2 deployment.
- **Impact:** Configuration changes require code changes. The YAML files serve as documentation only. If an operator modifies `diversity.yaml` expecting behavior to change, nothing happens.
- **Severity:** LOW (configs are just documentation, code works with hardcoded values)
- **Mitigation:** NOT ADDRESSED. Either load configs from YAML in `__init__()` or remove the YAML files and document constants in code.
- **Phase:** Deferred

---

## DEFERRED PHASE 1.5 FIXES -- NEW FAILURE MODES

These are failure modes introduced BY the deferred fixes, not in the original Phase 1.5 components.

---

**FM-138** | **FM-18 Fix Introduces Import Cycle Risk**
- **Component:** `engine/budget_tracker.py` :: `record_consumption()` (design doc lines 1704-1705)
- **Failure:** The FM-18 fix has inline imports: `from ..models.audit import BaseLogEntry, LogStream` and `from ..models.base import generate_id`. These are safe (no cycle risk). But line 1676 imports `from ..state.jsonl_writer import JsonlWriter` inside `__init__()`. The `JsonlWriter` imports `from ..models.audit import BaseLogEntry, LogStream`. The `BudgetTracker` imports `from ..models.resource import ...`. These are independent import chains, so no cycle. However, the `import json` and `import fcntl` inside `record_consumption()` (lines 1722-1723) are redundant with module-level availability and add per-call import overhead (Python caches module imports, so minimal cost, but still non-idiomatic).
- **Trigger:** N/A (code smell, not a runtime failure).
- **Impact:** None. Cosmetic issue.
- **Severity:** LOW
- **Mitigation:** NOT ADDRESSED. Move imports to module level.
- **Phase:** Deferred

---

## SUMMARY TABLE

| Severity | Count | FM Numbers |
|----------|-------|-----------|
| CRITICAL | 6 | FM-85, FM-86, FM-87, FM-88, FM-89, FM-90 |
| HIGH | 14 | FM-91, FM-92 (revised to MEDIUM), FM-93, FM-94, FM-95, FM-96, FM-97, FM-98, FM-99, FM-100, FM-101, FM-102, FM-103, FM-104 |
| MEDIUM | 18 | FM-105, FM-106, FM-107, FM-108, FM-109, FM-110, FM-111, FM-112, FM-113, FM-114, FM-115, FM-116, FM-117, FM-118, FM-119, FM-120, FM-121, FM-122 |
| LOW | 15 | FM-123, FM-124, FM-125, FM-126, FM-127, FM-128, FM-129, FM-130, FM-131, FM-132, FM-133, FM-134, FM-135, FM-136, FM-137, FM-138 |
| **TOTAL** | **53** | FM-85 through FM-138 |

Note: FM-92 was initially classified HIGH but revised to MEDIUM upon deeper analysis of the guard logic. The count above reflects the revised classification (13 HIGH, 1 reclassified to MEDIUM = still listed under HIGH row for traceability).

---

## CROSS-REFERENCE WITH DESIGN DOC EMBEDDED FAILURE MODES

The design doc Part 13 lists FM-70 through FM-84 and D-1 through D-7. This analysis found:

| Design Doc FM | Status | Our Finding |
|---------------|--------|-------------|
| FM-70 (empty outputs) | Incomplete | FM-85 extends: empty outputs not just `< 2`, but `>= 2 empty strings` |
| FM-71 (identical outputs) | Correct | No additional issue |
| FM-72 (state corruption) | NOT IMPLEMENTED | FM-98: catch clauses missing from actual code |
| FM-73 (unbounded map) | Correct | FM-107 adds: hardcoded list divergence risk |
| FM-74 (unbounded records) | NOT IMPLEMENTED | FM-86: trimming code not present in `_save_state()` |
| FM-75 (ledger rebuild perf) | DEFERRED | FM-89: performance is critical, cannot defer to Phase 3 |
| FM-76 (null voice VDI) | Correct | FM-90 extends: `None` tone/style semantics |
| FM-77 (SRD history race) | Acknowledged | FM-91: more severe than acknowledged |
| FM-78 (early ECE) | Correct | FM-95 adds: formula mismatch with standard ECE |
| FM-79 (IQR empty) | Correct | FM-120 adds: ineffective at small sample sizes |
| FM-80 (ledger rotation) | Claimed correct | FM-88 adds: internal API bypass creates new race |
| FM-81 (no multi-agent) | Correct | FM-116 extends: agent outputs never captured |
| FM-82 (bootstrap noise) | Correct | FM-104 extends: framework stagnation fires indefinitely |
| FM-83 (orphaned refs) | Correct | No additional issue |
| FM-84 (new agent health) | Correct | FM-112 adds: timezone mismatch dependency |

---

## TOP 15 MUST-FIX BEFORE IMPLEMENTATION (Prioritized)

| # | FM | Severity | Summary | Fix |
|---|-----|----------|---------|-----|
| 1 | FM-86 | CRITICAL | CalibrationState.records grows unbounded; crashes at 1MB YAML cap | Add `self._state.records = self._state.records[-100:]` in `_save_state()` |
| 2 | FM-89 | CRITICAL | FM-18 ledger rebuild reads entire JSONL on every `get_window()` call | Cache window totals; only rebuild when ledger mtime changes |
| 3 | FM-88 | CRITICAL | FM-18 fix bypasses JsonlWriter API, creating dual-locking race | Use `JsonlWriter.append()` with a `ConsumptionLogEntry` subclass |
| 4 | FM-87 | CRITICAL | `tokens_used` always 0 corrupts capability tracker averages | Add `tokens_used` population in task completion flow |
| 5 | FM-90 | CRITICAL | VoiceProfile None tone/style inflates VDI systematically | Define explicit semantics for None vs. explicit voice fields |
| 6 | FM-85 | CRITICAL | All-empty agent outputs produce misleading 0.0 SRD | Skip diversity measurement when all outputs empty |
| 7 | FM-98 | HIGH | StagnationDetector `_load_state()` crashes on corrupt YAML | Add `ValueError`/`TypeError`/`KeyError` to except clause |
| 8 | FM-94 | HIGH | Evidence threshold double-incremented per overcalibration event | Make FP/FN adjustments exclusive with base overcalibration adjustment |
| 9 | FM-104 | HIGH | Framework stagnation fires on every task after 10 tasks (no evolution engine in Phase 2) | Disable framework-level stagnation or add signal suppression |
| 10 | FM-101 | HIGH | `YamlStore.delete()` method missing; cost archival broken | Implement `delete()` method on YamlStore |
| 11 | FM-93 | HIGH | Capability tracker `avg_review_confidence` denominator includes zero-confidence records | Track separate confidence count |
| 12 | FM-97 | HIGH | FM-18 fix left weekly budget with same read-modify-write race | Extend ledger approach to weekly budget |
| 13 | FM-102 | HIGH | `log_diversity()` method missing from AuditLogger | Add method per design doc Part 7.2 (implementation ordering) |
| 14 | FM-103 | HIGH | `DiversityLogEntry` class not in existing models/audit.py | Add class per design doc Part 2.3 (implementation ordering) |
| 15 | FM-115 | MEDIUM | `record_task_outcome()` never called from any code path | Add call in `handle_verdict()` or create explicit integration point |

---

## IMPLEMENTATION ORDERING DEPENDENCIES

Several failure modes are blocking chains:

```
FM-103 (DiversityLogEntry model)
  └──▶ FM-102 (log_diversity() method)
       └──▶ FM-115 (record_task_outcome() integration)
            └──▶ FM-116 (agent output capture needed)

FM-101 (YamlStore.delete())
  └──▶ R8/R16 archival (FM-134: never auto-called)

FM-05 (Phase 1.5: timezone mismatch)
  └──▶ FM-112 (FM-63 heartbeat fix depends on timezone fix)

FM-87 (tokens_used population)
  └──▶ FM-93 (avg_review_confidence denominator)
       └──▶ FM-107/FM-118 (task type list sync)
```

These chains mean that fixing FM-115 alone is not sufficient -- the entire chain from FM-103 through FM-116 must be resolved together for Phase 2 diversity measurement to function.
