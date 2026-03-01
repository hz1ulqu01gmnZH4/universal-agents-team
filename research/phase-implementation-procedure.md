# Phase Implementation Procedure

**Version:** 1.0
**Date:** 2026-03-01
**Status:** Active — applies to all phases from Phase 1.5 onward
**Derived from:** Phase 0 and Phase 1 experience, refined through Phase 1.5 review cycles

---

## Overview

Each phase of the Universal Agents Framework follows a **12-step procedure** with
multiple review gates. No step is skipped. Every gate requires explicit pass before
proceeding. The procedure is designed to catch failures at the cheapest point —
design time is 10x cheaper than implementation time, which is 10x cheaper than
production debugging.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Phase N Implementation Pipeline                     │
│                                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │  DESIGN  │──▶│  REVIEW  │──▶│  HARDEN  │──▶│IMPLEMENT │            │
│  │  (1-2)   │   │  (3-5)   │   │  (6-7)   │   │  (8-12)  │            │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘            │
│                                                                         │
│  Steps 1-2: Write detailed design from phase spec                      │
│  Steps 3-5: Design review → failure mode enumeration → fix design      │
│  Steps 6-7: Write tests → review tests                                 │
│  Steps 8-12: Implement → review → failure modes → fix → final review   │
│                                                                         │
│  Gate rule: ALL tests must pass before any step is marked complete.     │
│  Gate rule: ALL review findings must be addressed (fixed or documented).│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Procedure

### Phase: DESIGN

#### Step 1: Read Phase N Specification

**Input:** Unified design spec section(s) for Phase N + relevant literature reviews
**Output:** Understanding of scope, constraints, dependencies
**Actor:** Lead (human or orchestrator)

1. Read the relevant sections of `research/framework-design-unified-v1.1.md`
2. Read associated literature review(s) for the phase
3. Read the previous phase's detailed design (for interface contracts)
4. Identify:
   - New files to create
   - Existing files to modify
   - Interface boundaries with adjacent phases
   - External dependencies (APIs, libraries, services)
5. Note any ambiguities or contradictions in the spec for resolution during design

**Gate:** Proceed when scope is understood and no blocking ambiguities remain.

---

#### Step 2: Write Detailed Design Document

**Input:** Phase spec + literature + previous phase interfaces
**Output:** `research/detailed-design-phaseN.md` (implementation-ready)
**Actor:** Lead

The detailed design document must be **concrete enough to code from directly**:

1. **Architecture overview** — what the phase adds, key principles, what it does NOT include
2. **Data models** — full Pydantic class definitions with all fields, types, validators
3. **New component implementations** — complete class definitions with:
   - Constructor signatures (all parameters typed)
   - Public method signatures with docstrings
   - Full method bodies (not pseudocode — real Python)
   - Private helper methods
   - Error handling paths
4. **Modified component changes** — exact diffs to existing files:
   - New parameters added to constructors
   - New method implementations
   - Modified method logic (showing before/after)
5. **YAML config schemas** — complete config file contents
6. **Implementation sequence** — dependency graph with step ordering
7. **Verification checklist** — test commands for each component
8. **Edge cases & failure modes** — initial set from design-time analysis

**Quality bar:**
- An implementer should be able to copy-paste code blocks directly
- No "..." or "TODO" in code blocks
- All import paths explicit
- All function signatures complete (no `*args, **kwargs` handwaving)

**Gate:** Document complete. All code blocks syntactically valid.

---

### Phase: REVIEW

#### Step 3: Design Review by Subagent

**Input:** `research/detailed-design-phaseN.md`
**Output:** Review findings with severity ratings
**Actor:** Subagent (code-reviewer or general-purpose, opus model)

Launch a review subagent with the following mandate:

```
Review the Phase N detailed design document for:

1. CORRECTNESS: Do code blocks match the spec? Are interfaces consistent?
2. COMPLETENESS: Are all spec requirements addressed? Any gaps?
3. CONSISTENCY: Do Part X and Part Y agree on signatures, types, behavior?
4. FEASIBILITY: Can this actually be implemented as written?
5. INTEGRATION: Does it fit with existing Phase 0/1/... code?

Rate each finding as:
- MUST-FIX (M): Blocks implementation. Will cause runtime errors or spec violations.
- SHOULD-FIX (S): Quality/maintainability issue. Won't crash but will cause problems.
- NICE-TO-HAVE (N): Polish. Optional improvement.

Score the design 1-5:
- 5: Implementation-ready, no changes needed
- 4: Minor fixes needed, fundamentally sound
- 3: Significant issues but approach is correct
- 2: Major rework needed
- 1: Wrong approach, redesign required
```

**Gate:** Score >= 3.0. All MUST-FIX items cataloged.

---

#### Step 4: Failure Mode Enumeration by Subagent

**Input:** `research/detailed-design-phaseN.md` + existing source code
**Output:** `research/phaseN-failure-modes.md`
**Actor:** Subagent (general-purpose, opus model)

Launch a failure mode subagent with the following mandate:

```
Exhaustively enumerate every possible failure mode in the Phase N design.

For EACH failure mode:
1. Assign an ID (FM-XX)
2. Classify severity: CRITICAL / HIGH / MEDIUM / LOW
3. Identify exact location (file, method, line range in design doc)
4. Describe the failure scenario step-by-step
5. Assess impact (what breaks, what data is lost, what behavior changes)
6. Check: Is this already documented in the design's failure modes section?
7. Propose a fix or mitigation

Categories to check:
- Data integrity (corruption, loss, inconsistency)
- Concurrency (races, TOCTOU, non-atomic operations)
- API contract mismatches (signature differences, missing methods, wrong types)
- State machine violations (invalid transitions, orphaned states)
- Silent degradation (errors caught and swallowed, fallback behavior hiding bugs)
- Resource leaks (unbounded growth, missing cleanup)
- Spec divergence (design says X, code does Y)
- Missing validation (unchecked inputs, unvalidated assumptions)
- Test gaps (untested critical paths)
- Integration risks (undefined wiring between components)

Cross-reference EVERY code block in the design doc against:
- The existing source files it modifies
- Other code blocks within the same design doc
- The spec sections it claims to implement
```

**Gate:** Failure mode document complete. All CRITICAL and HIGH items have proposed fixes.

---

#### Step 5: Fix Detailed Design Document

**Input:** Review findings (Step 3) + failure modes (Step 4)
**Output:** Updated `research/detailed-design-phaseN.md`
**Actor:** Lead

For each finding and failure mode:

1. **MUST-FIX / CRITICAL / HIGH**: Apply the fix directly to the design doc.
   - Update code blocks with corrected implementations
   - Add missing sections (datetime conventions, backward compat, concurrency strategy)
   - Fix dependency ordering in implementation sequence
   - Add new failure modes to Part 11 table
2. **SHOULD-FIX / MEDIUM**: Apply fix or document explicit acceptance with rationale.
3. **NICE-TO-HAVE / LOW**: Document as accepted/deferred with Phase N+1 target if appropriate.

Update Part 11 (failure modes table) to include ALL findings with status:
- **FIXED**: Design changed to eliminate the failure mode
- **DOCUMENTED**: Accepted with rationale (concurrency race accepted because low probability)
- **DEFERRED**: Will be addressed in Phase N+1 with specific plan

**Gate:** All CRITICAL/HIGH items addressed. Part 11 table updated. No MISSING items.

---

### Phase: HARDEN

#### Step 6: Write Tests

**Input:** Updated detailed design document
**Output:** Test files in `tests/`
**Actor:** Lead

Write tests BEFORE implementation (test-first for new components):

1. **Unit tests** for each new component:
   - Happy path (normal operation)
   - Edge cases (boundary values, empty inputs, max values)
   - Error paths (invalid inputs, missing dependencies, resource exhaustion)
   - State transitions (all valid transitions, rejection of invalid ones)
2. **Integration tests** for cross-component workflows:
   - Full lifecycle (create → process → execute → complete)
   - Backwards compatibility (new components with `None` dependencies)
   - Persistence round-trips (write to YAML → read back → verify equality)
3. **Regression tests**:
   - Existing tests still pass
   - Phase N-1 behavior unchanged when Phase N components are `None`

**Naming convention:** `tests/test_engine/test_{component}.py`
**Framework:** pytest with fixtures for YamlStore, temp dirs, mock configs

**Gate:** Tests written. Tests FAIL (because implementation doesn't exist yet).
Verify with `uv run pytest tests/test_engine/test_{component}.py -v` — expect failures.

---

#### Step 7: Test Review by Subagent

**Input:** Test files from Step 6
**Output:** Review findings on test quality
**Actor:** Subagent (test-qa or code-reviewer)

Launch a test review subagent:

```
Review the Phase N test files for:

1. COVERAGE: Are all public methods tested? All error paths? All state transitions?
2. ASSERTIONS: Does every test have meaningful assertions (not just "doesn't crash")?
3. ISOLATION: Do tests depend on each other? On external state? On timing?
4. MOCKING: Are mocks accurate to the real interfaces? Do they match API contracts?
5. EDGE CASES: Are boundary conditions tested? Empty collections? Zero values? None?
6. FAILURE MODES: Is every CRITICAL/HIGH failure mode from Step 4 covered by a test?
7. NO-OP TESTS: Are there tests that always pass regardless of implementation?

Flag any test that:
- Has no assertions
- Catches exceptions without re-raising (hiding failures)
- Uses mocks that don't match the actual interface signatures
- Tests implementation details rather than behavior
```

Apply fixes to tests based on review findings.

**Gate:** All review findings addressed. Tests still fail (no implementation yet).

---

### Phase: IMPLEMENT

#### Step 8: Implement Phase N

**Input:** Detailed design doc + tests
**Output:** Source code in `src/uagents/`
**Actor:** Lead (or team of subagents for parallel implementation)

Follow the implementation sequence from the design doc strictly:

1. Implement each step in dependency order
2. After each step, run that step's tests: `uv run pytest tests/test_engine/test_{component}.py -v`
3. After all steps, run the full test suite: `uv run pytest --tb=long -v`
4. All tests must pass before proceeding

**Rules:**
- Copy code from design doc code blocks (they are implementation-ready)
- Do NOT deviate from the design without documenting why
- If a design doc code block has a bug, fix it in BOTH the implementation AND the design doc
- Every new file must have module docstring with spec reference
- No `# TODO` in production code — either implement it or remove the requirement

**Gate:** ALL tests pass (new + existing). Zero failures. Zero warnings treated as errors.

---

#### Step 9: Implementation Review by Subagent

**Input:** `git diff` of all changes + source files
**Output:** Review findings
**Actor:** Subagent (code-reviewer, opus model)

Launch an implementation review subagent:

```
Review the Phase N implementation for:

1. DESIGN FIDELITY: Does the implementation match the detailed design doc?
2. CODE QUALITY: Clean code, proper error handling, no dead code
3. SECURITY: No injection, no unsafe deserialization, no path traversal
4. PERFORMANCE: No O(n²) where O(n) suffices, no unnecessary I/O
5. DEFENSIVE CODING: Loud failures, no silent fallbacks, no swallowed exceptions
6. INTEGRATION: Does it wire correctly with existing components?

Cross-reference every method against the design doc.
Flag any deviation (intentional or accidental).
```

**Gate:** All MUST-FIX findings addressed. Code matches design doc.

---

#### Step 10: Implementation Failure Mode Review by Subagent

**Input:** Implemented source code + design doc failure modes
**Output:** Implementation-specific failure mode findings
**Actor:** Subagent (general-purpose, opus model)

This is distinct from Step 4 (design-time). Implementation may introduce NEW failure
modes not present in the design:

```
Analyze the IMPLEMENTED code (not the design doc) for failure modes:

1. Are all design-doc failure mode mitigations actually implemented?
2. Did implementation introduce new failure modes not in the design?
3. Are there code paths where exceptions are caught but not handled?
4. Are there race conditions in the actual threading/async model?
5. Are there resource leaks (file handles, connections, memory)?
6. Do error messages include enough context for debugging?
7. Are all configuration values validated on load?

For each finding: ID, severity, file:line, description, proposed fix.
```

**Gate:** All CRITICAL/HIGH findings have proposed fixes.

---

#### Step 11: Apply Implementation Fixes

**Input:** Findings from Steps 9 and 10
**Output:** Updated source code + updated tests if needed
**Actor:** Lead

1. Apply all MUST-FIX and CRITICAL/HIGH fixes to source code
2. If fixes change behavior, update tests to match
3. If fixes reveal design gaps, update the design doc
4. Run full test suite: `uv run pytest --tb=long -v`
5. All tests must pass

**Gate:** ALL tests pass. All CRITICAL/HIGH findings fixed. Design doc updated if needed.

---

#### Step 12: Final Review for Phase N

**Input:** Complete implementation + tests + design doc
**Output:** Phase N sign-off
**Actor:** Subagent (code-reviewer, opus model) + Human approval

Final review checklist:

```
FINAL REVIEW — Phase N

[ ] All tests pass: `uv run pytest --tb=long -v` shows 0 failures
[ ] No regressions: existing test count unchanged or increased
[ ] Design doc matches implementation (no undocumented deviations)
[ ] Failure modes table (Part 11) reflects final state
[ ] All CRITICAL/HIGH failure modes have mitigations implemented
[ ] No TODO/FIXME/HACK in production code
[ ] All new files have module docstrings with spec references
[ ] git diff reviewed and approved
[ ] MEMORY.md updated with Phase N completion status
[ ] Commit message prepared (not committed until human approves)
```

**Gate:** Human approves. Commit created. Phase N complete.

---

## Summary: Gate Checklist per Phase

| Step | Name | Actor | Key Gate |
|------|------|-------|----------|
| 1 | Read phase spec | Lead | Scope understood, no blockers |
| 2 | Write detailed design | Lead | Doc complete, code blocks valid |
| 3 | Design review | Subagent (opus) | Score >= 3.0, MUST-FIX cataloged |
| 4 | Failure mode enumeration | Subagent (opus) | All CRITICAL/HIGH have fixes |
| 5 | Fix design doc | Lead | All findings addressed in doc |
| 6 | Write tests | Lead | Tests written, tests FAIL |
| 7 | Test review | Subagent | Test quality verified |
| 8 | Implement | Lead/Team | ALL tests pass |
| 9 | Implementation review | Subagent (opus) | Code matches design |
| 10 | Impl failure mode review | Subagent (opus) | No new CRITICAL gaps |
| 11 | Apply fixes | Lead | ALL tests pass post-fix |
| 12 | Final review | Subagent + Human | Sign-off, commit |

---

## Timing Estimates

Based on Phase 0 (46 files), Phase 1 (5 waves), and Phase 1.5 (in progress):

| Step | Typical Duration | Notes |
|------|-----------------|-------|
| 1-2 | 1-2 sessions | Depends on phase complexity |
| 3 | 1 subagent call | ~5 min |
| 4 | 1 subagent call | ~10 min (reads all source files) |
| 5 | 1 session | Proportional to finding count |
| 6 | 1 session | ~200 test lines per component |
| 7 | 1 subagent call | ~5 min |
| 8 | 1-3 sessions | Proportional to file count |
| 9 | 1 subagent call | ~10 min |
| 10 | 1 subagent call | ~10 min |
| 11 | 0.5-1 session | Proportional to finding count |
| 12 | 1 subagent call + human | ~10 min + human review |

**Total:** 4-8 sessions per phase (depending on complexity and finding count).

---

## Phase History

| Phase | Design Doc | Tests | Source Files | Status |
|-------|-----------|-------|-------------|--------|
| Phase 0 | `detailed-design-phase0.md` (4218 lines) | 254 tests | 46 files | Complete |
| Phase 1 | `detailed-design-phase1.md` | +42 tests | +8 files | Complete |
| Phase 1.5 | `detailed-design-phase1.5.md` (2445 lines) | TBD | TBD | Design complete, 67 FMs addressed |
| Phase 2 | TBD | TBD | TBD | Not started |

---

## Anti-Patterns (Lessons Learned)

1. **Never skip the failure mode step.** Phase 1.5 found 47 new failure modes not caught by design review. Several were CRITICAL (would crash on first use).

2. **Never reorder implementation steps without updating the dependency graph.** FM-06 (ensure_dir) was ordered AFTER the components that depend on it.

3. **Design review and failure mode review find DIFFERENT things.** Review catches quality/consistency issues. Failure mode enumeration catches runtime crash scenarios, race conditions, and integration gaps. Both are needed.

4. **Tests must be reviewed before implementation.** A test with no assertions is worse than no test — it gives false confidence. FM-55 (no CacheManager tests) was caught because the procedure requires test coverage for all components.

5. **Implementation can introduce failure modes not in the design.** Step 10 is not redundant with Step 4. Real code has real bugs that design docs don't.

6. **Update the design doc when implementation deviates.** The design doc is the source of truth for the NEXT phase. Stale design docs cause cascading errors.

7. **Subagent reviews must use opus model.** Lower-capability models miss subtle issues (cross-file consistency, state machine violations, concurrency races).
