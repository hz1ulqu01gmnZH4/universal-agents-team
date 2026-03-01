"""4-stage skill validation pipeline.
Spec reference: Section 12.2 (Skill Validation).

Validates extracted skill candidates through:
  Stage 1 (Syntax): Parse as CapabilityAtom, check required fields
  Stage 2 (Execution): Apply skill to 2+ archived tasks, check outputs
  Stage 3 (Comparison): A/B test vs baseline, must show >= +5pp improvement
  Stage 4 (Review): Human or senior agent approval

Key constraints:
- Total budget: 15000 tokens (configurable)
- Early termination: if any stage fails, stop immediately
- Stage 2 requires at least 2 archived test tasks of similar type
- Stage 3 improvement threshold: +5pp (matches ring_3_to_2)
- Stage 4 review is blocking -- skill stays in STAGE_3_PASSED until approved

Literature basis:
- CASCADE (arXiv:2512.23880): Execution-based validation, not self-eval
- SAGE (arXiv:2512.17102): +8.9% via validation pipeline
- SkillsBench (arXiv:2602.12670): Self-eval fails, execution tests work
- SoK Agent Skills (arXiv:2602.20867): 26.1% vulnerability rate
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from ..models.audit import DecisionLogEntry
from ..models.base import generate_id
from ..models.capability import CapabilityAtom
from ..models.environment import ModelExecuteFn
from ..models.protection import ProtectionRing
from ..models.skill import (
    ExtractionCandidate,
    SkillRecord,
    SkillStatus,
    ValidationResult,
    ValidationStage,
)
from ..models.task import Task
from ..state.yaml_store import YamlStore

logger = logging.getLogger("uagents.skill_validator")

# Stage 2 execution test prompt template
EXECUTION_TEST_PROMPT = """You are testing whether a skill instruction helps solve a task.

## Skill being tested
Name: {skill_name}
Instruction: {skill_instruction}

## Task to solve (from archive)
Title: {task_title}
Description: {task_description}

## Your job
Apply the skill instruction above to solve this task. Provide your solution.
At the end of your response, on a new line, write:
QUALITY: <1-10> (how well the skill helped with this task, 10=perfectly relevant)
"""

# Stage 3 baseline prompt (without skill)
BASELINE_PROMPT = """You are solving a task.

## Task to solve
Title: {task_title}
Description: {task_description}

## Your job
Solve this task. Provide your solution.
At the end of your response, on a new line, write:
QUALITY: <1-10> (how confident you are in your solution, 10=very confident)
"""


class SkillValidator:
    """4-stage validation pipeline for skill candidates.

    Design invariants:
    - Total budget capped at 15000 tokens (configurable)
    - Early termination: any stage failure stops the pipeline
    - Stage 1 is automated (no LLM call, pure parsing)
    - Stage 2 requires 2+ archived test tasks
    - Stage 3 requires measurable improvement (>= +5pp)
    - Stage 4 generates review request (approval is external)
    - Each stage produces a ValidationResult
    - Budget tracking per stage, total not exceeded

    Usage:
        validator = SkillValidator(yaml_store, domain="meta")
        record = validator.validate(candidate, execute_fn, test_tasks)
        if record.status == SkillStatus.STAGE_3_PASSED:
            # Needs review approval before activation
            pass

    FM-S02: Stage 2 uses multiple test tasks to reduce flakiness.
    FM-S05: Stage 3 threshold matches ring_3_to_2 promotion criteria.
    FM-S07: Budget enforcement across all stages.
    """

    def __init__(
        self,
        yaml_store: YamlStore,
        domain: str = "meta",
        audit_logger: object | None = None,  # AuditLogger, optional
        budget_tracker: object | None = None,  # BudgetTracker, optional
    ):
        self.yaml_store = yaml_store
        self._domain = domain
        self._audit_logger = audit_logger
        # IFM-N20: BudgetTracker for pre-validation budget check
        self._budget_tracker = budget_tracker

        # Load config (fail-loud if missing)
        config_raw = yaml_store.read_raw("core/skill-system.yaml")
        ss = config_raw.get("skill_system")
        if ss is None:
            raise ValueError(
                "core/skill-system.yaml missing 'skill_system' section"
            )
        val = ss.get("validation", {})
        self._total_budget = int(val.get("total_token_budget", 15000))
        stage_budgets = val.get("stage_budgets", {})
        self._stage_budgets = {
            ValidationStage.SYNTAX: int(stage_budgets.get("syntax", 0)),
            ValidationStage.EXECUTION: int(
                stage_budgets.get("execution", 6000)
            ),
            ValidationStage.COMPARISON: int(
                stage_budgets.get("comparison", 6000)
            ),
            ValidationStage.REVIEW: int(stage_budgets.get("review", 3000)),
        }
        self._min_test_tasks = int(val.get("min_test_tasks", 2))
        self._min_improvement_pp = float(val.get("min_improvement_pp", 5))
        self._comparison_runs = int(val.get("comparison_runs", 2))

        # Security config
        sec = ss.get("security", {})
        self._forbidden_patterns: list[str] = sec.get(
            "forbidden_patterns", []
        )

        # State path
        self._skills_base = f"instances/{domain}/state/skills"
        yaml_store.ensure_dir(self._skills_base)

    def validate(
        self,
        candidate: ExtractionCandidate,
        execute_fn: ModelExecuteFn,
        test_tasks: list[Task],
    ) -> SkillRecord:
        """Run the full 4-stage validation pipeline.

        Args:
            candidate: Extracted skill candidate.
            execute_fn: LLM execution function for stages 2-3.
            test_tasks: Archived completed tasks for execution testing.
                Must have at least `min_test_tasks` entries.

        Returns:
            SkillRecord with validation results and final status.
            Status will be one of:
            - REJECTED: Failed at any stage
            - STAGE_3_PASSED: Passed stages 1-3, awaiting review
            - VALIDATED: Passed all 4 stages (if review auto-approved)

        FM-S02: Multiple test tasks reduce flakiness.
        FM-S05: Improvement threshold matches ring promotion criteria.
        FM-S07: Budget tracking prevents overspend.
        IFM-N20: Pre-checks session budget before starting validation.
        """
        # IFM-N20: Pre-check session budget before validation.
        # Validation can consume up to total_budget tokens (default 15000).
        # If the session budget is too low, skip validation with a warning.
        if self._budget_tracker is not None:
            try:
                window = self._budget_tracker.get_window()
                if window.remaining_tokens < self._total_budget:
                    logger.warning(
                        f"Skipping validation: session budget too low "
                        f"({window.remaining_tokens} remaining, "
                        f"need {self._total_budget} for validation)"
                    )
                    record = candidate.to_skill_record()
                    record.status = SkillStatus.REJECTED
                    stage = ValidationResult(
                        stage=ValidationStage.SYNTAX,
                        passed=False,
                        score=0.0,
                        detail=(
                            f"Validation skipped: insufficient session budget "
                            f"({window.remaining_tokens} < {self._total_budget})"
                        ),
                        tokens_used=0,
                        timestamp=datetime.now(timezone.utc),
                    )
                    record.validation_results.append(stage)
                    self._persist_record(record)
                    return record
            except Exception as e:
                # IFM-N38: BudgetTracker exception is a fail-safe rejection.
                # If we cannot verify budget, conservatively reject rather
                # than proceeding with potentially unbounded token spend.
                logger.error(
                    f"BudgetTracker check failed, rejecting validation "
                    f"(conservative fail-safe): {e}"
                )
                record = candidate.to_skill_record()
                record.status = SkillStatus.REJECTED
                stage = ValidationResult(
                    stage=ValidationStage.SYNTAX,
                    passed=False,
                    score=0.0,
                    detail=(
                        f"Validation rejected: BudgetTracker exception "
                        f"(conservative fail-safe): {e}"
                    ),
                    tokens_used=0,
                    timestamp=datetime.now(timezone.utc),
                )
                record.validation_results.append(stage)
                self._persist_record(record)
                return record

        # Convert candidate to skill record
        record = candidate.to_skill_record()
        record.status = SkillStatus.VALIDATING

        total_tokens_used = 0

        # Stage 1: Syntax check
        stage_1 = self._stage_1_syntax(record)
        record.validation_results.append(stage_1)
        total_tokens_used += stage_1.tokens_used

        if not stage_1.passed:
            record.status = SkillStatus.REJECTED
            self._persist_record(record)
            self._log_validation_decision(record, "rejected_stage_1")
            return record

        record.status = SkillStatus.STAGE_1_PASSED

        # Stage 2: Execution test
        if len(test_tasks) < self._min_test_tasks:
            # Not enough test tasks -- defer validation
            stage_2 = ValidationResult(
                stage=ValidationStage.EXECUTION,
                passed=False,
                score=0.0,
                detail=(
                    f"Deferred: only {len(test_tasks)} test tasks available, "
                    f"need {self._min_test_tasks}"
                ),
                tokens_used=0,
                timestamp=datetime.now(timezone.utc),
            )
            record.validation_results.append(stage_2)
            record.status = SkillStatus.REJECTED
            self._persist_record(record)
            self._log_validation_decision(
                record, "deferred_insufficient_test_tasks"
            )
            logger.info(
                f"Skill '{record.name}' validation deferred: "
                f"insufficient test tasks ({len(test_tasks)} < "
                f"{self._min_test_tasks})"
            )
            return record

        remaining_budget = self._total_budget - total_tokens_used
        stage_2 = self._stage_2_execution(
            record, execute_fn, test_tasks, remaining_budget
        )
        record.validation_results.append(stage_2)
        total_tokens_used += stage_2.tokens_used

        if not stage_2.passed:
            record.status = SkillStatus.REJECTED
            self._persist_record(record)
            self._log_validation_decision(record, "rejected_stage_2")
            return record

        record.status = SkillStatus.STAGE_2_PASSED

        # FM-S07: Check total budget before stage 3
        remaining_budget = self._total_budget - total_tokens_used
        if remaining_budget < 500:
            stage_3 = ValidationResult(
                stage=ValidationStage.COMPARISON,
                passed=False,
                score=0.0,
                detail=(
                    f"Budget exhausted: {remaining_budget} tokens remaining, "
                    f"need at least 500 for comparison"
                ),
                tokens_used=0,
                timestamp=datetime.now(timezone.utc),
            )
            record.validation_results.append(stage_3)
            record.status = SkillStatus.REJECTED
            self._persist_record(record)
            self._log_validation_decision(record, "rejected_budget_exhausted")
            return record

        # Stage 3: Comparison test
        stage_3 = self._stage_3_comparison(
            record, execute_fn, test_tasks, remaining_budget
        )
        record.validation_results.append(stage_3)
        total_tokens_used += stage_3.tokens_used

        if not stage_3.passed:
            record.status = SkillStatus.REJECTED
            self._persist_record(record)
            self._log_validation_decision(record, "rejected_stage_3")
            return record

        record.status = SkillStatus.STAGE_3_PASSED

        # Stage 4: Review -- generate review summary but do NOT append
        # a ValidationResult yet. The result is appended only when
        # approve_skill() or reject_skill() is called.
        # SF-8: Previously appended a passed=False "pending" result here,
        # which was confusing -- "not passed" looked like a failure but
        # actually meant "awaiting review". Now, no Stage 4 result is
        # stored until the review decision is made.
        remaining_budget = self._total_budget - total_tokens_used
        # SF-3: Return value intentionally discarded. Stage 4 generates
        # a review summary for logging but the ValidationResult is NOT
        # appended to validation_results here -- it is only appended
        # when approve_skill() or reject_skill() is called.
        _ = self._stage_4_review(record, remaining_budget)
        # Skill stays STAGE_3_PASSED awaiting review via approve_skill()
        # or reject_skill(). No status change here.

        self._persist_record(record)
        self._log_validation_decision(record, f"completed_{record.status}")

        logger.info(
            f"Skill '{record.name}' validation complete: "
            f"status={record.status}, "
            f"total_tokens={total_tokens_used}"
        )

        return record

    def approve_skill(self, record: SkillRecord, reviewer: str) -> SkillRecord:
        """Approve a skill that passed stages 1-3 (external review approval).

        Args:
            record: SkillRecord with status STAGE_3_PASSED.
            reviewer: Identity of the reviewer who approved.

        Returns:
            Updated SkillRecord with status VALIDATED.

        Raises:
            ValueError: If skill is not in STAGE_3_PASSED status.
        """
        if record.status != SkillStatus.STAGE_3_PASSED.value:
            raise ValueError(
                f"Cannot approve skill '{record.name}': "
                f"status is {record.status}, expected STAGE_3_PASSED"
            )

        # Add review approval result
        review_result = ValidationResult(
            stage=ValidationStage.REVIEW,
            passed=True,
            score=1.0,
            detail=f"Approved by reviewer: {reviewer}",
            tokens_used=0,
            timestamp=datetime.now(timezone.utc),
            reviewer=reviewer,
        )
        record.validation_results.append(review_result)
        record.status = SkillStatus.VALIDATED

        self._persist_record(record)
        self._log_validation_decision(record, "approved")

        logger.info(
            f"Skill '{record.name}' approved by {reviewer}"
        )

        return record

    def reject_skill(
        self, record: SkillRecord, reviewer: str, reason: str
    ) -> SkillRecord:
        """Reject a skill during review.

        Args:
            record: SkillRecord with status STAGE_3_PASSED.
            reviewer: Identity of the reviewer who rejected.
            reason: Reason for rejection.

        Returns:
            Updated SkillRecord with status REJECTED.
        """
        if record.status != SkillStatus.STAGE_3_PASSED.value:
            raise ValueError(
                f"Cannot reject skill '{record.name}': "
                f"status is {record.status}, expected STAGE_3_PASSED"
            )

        review_result = ValidationResult(
            stage=ValidationStage.REVIEW,
            passed=False,
            score=0.0,
            detail=f"Rejected by {reviewer}: {reason}",
            tokens_used=0,
            timestamp=datetime.now(timezone.utc),
            reviewer=reviewer,
        )
        record.validation_results.append(review_result)
        record.status = SkillStatus.REJECTED

        self._persist_record(record)
        self._log_validation_decision(record, "rejected_review")

        return record

    def _stage_1_syntax(self, record: SkillRecord) -> ValidationResult:
        """Stage 1: Syntax check -- is the skill well-formed?

        Checks:
        - name is non-empty and valid identifier
        - description is non-empty
        - instruction_fragment is non-empty
        - instruction_fragment does not contain forbidden patterns
        - Can be parsed as a CapabilityAtom

        No LLM call needed -- pure parsing. 0 tokens.
        """
        now = datetime.now(timezone.utc)
        issues: list[str] = []

        # Check name
        if not record.name or not record.name.replace("_", "").isalnum():
            issues.append(f"Invalid name: '{record.name}'")

        # Check description
        if not record.description or len(record.description.strip()) < 5:
            issues.append("Description too short or empty")

        # Check instruction_fragment
        if not record.instruction_fragment or len(
            record.instruction_fragment.strip()
        ) < 10:
            issues.append("Instruction fragment too short or empty")

        # Check forbidden patterns (FM-S08)
        for pattern in self._forbidden_patterns:
            if pattern.lower() in record.instruction_fragment.lower():
                issues.append(
                    f"Forbidden pattern in instruction: '{pattern}'"
                )

        # Try to construct CapabilityAtom
        if not issues:
            try:
                record.to_capability_atom()
            except Exception as e:
                issues.append(f"Cannot construct CapabilityAtom: {e}")

        passed = len(issues) == 0
        detail = "All syntax checks passed" if passed else "; ".join(issues)

        return ValidationResult(
            stage=ValidationStage.SYNTAX,
            passed=passed,
            score=1.0 if passed else 0.0,
            detail=detail,
            tokens_used=0,
            timestamp=now,
        )

    def _stage_2_execution(
        self,
        record: SkillRecord,
        execute_fn: ModelExecuteFn,
        test_tasks: list[Task],
        budget: int,
    ) -> ValidationResult:
        """Stage 2: Execution test -- does the skill produce correct outputs?

        Applies the skill instruction to 2+ archived test tasks and checks
        that the quality score is >= 5/10 on each.

        FM-S02: Uses multiple test tasks to reduce LLM non-determinism.
        FM-S07: Respects per-stage budget cap.

        Args:
            record: Skill being validated.
            execute_fn: LLM execution function.
            test_tasks: Archived completed tasks for testing.
            budget: Remaining token budget for this stage.

        Returns:
            ValidationResult with pass/fail and scores.
        """
        now = datetime.now(timezone.utc)
        stage_budget = min(budget, self._stage_budgets[ValidationStage.EXECUTION])
        per_task_budget = stage_budget // max(len(test_tasks), 1)

        total_tokens = 0
        scores: list[float] = []
        test_task_ids: list[str] = []

        # SF-6: Use ALL available test tasks, not just min_test_tasks.
        # Per-task budget already accounts for variable counts.
        # min_test_tasks is a minimum requirement, not a cap.
        for test_task in test_tasks:
            if total_tokens >= stage_budget:
                break  # FM-S07: Budget exhausted

            prompt = EXECUTION_TEST_PROMPT.format(
                skill_name=record.name,
                skill_instruction=record.instruction_fragment,
                task_title=test_task.title,
                task_description=test_task.description[:500],
            )

            try:
                output, tokens_used = execute_fn(prompt, per_task_budget)
                total_tokens += tokens_used
            except Exception as e:
                logger.warning(
                    f"Stage 2 execution failed for task {test_task.id}: {e}"
                )
                scores.append(0.0)
                test_task_ids.append(test_task.id)
                continue

            # Parse quality score from output
            # IFM-N10: _parse_quality_score returns None on failure.
            # Skip tasks with unparseable scores instead of using a fallback.
            quality = self._parse_quality_score(output)
            if quality is None:
                logger.warning(
                    f"Stage 2 skipping task {test_task.id}: "
                    f"unparseable quality score"
                )
                test_task_ids.append(test_task.id)
                continue
            # Normalize to 0-1 (quality is 1-10)
            normalized = quality / 10.0
            scores.append(normalized)
            test_task_ids.append(test_task.id)

        if not scores:
            return ValidationResult(
                stage=ValidationStage.EXECUTION,
                passed=False,
                score=0.0,
                detail="No execution test results obtained",
                tokens_used=total_tokens,
                timestamp=now,
                test_task_ids=test_task_ids,
            )

        avg_score = sum(scores) / len(scores)
        # Must score >= 0.5 (i.e., quality >= 5/10) on average
        passed = avg_score >= 0.5
        # Must pass on all test tasks (not just average)
        all_passed = all(s >= 0.5 for s in scores)
        passed = passed and all_passed

        detail = (
            f"Avg score: {avg_score:.2f}, "
            f"per-task: {[f'{s:.2f}' for s in scores]}, "
            f"all_passed: {all_passed}"
        )

        return ValidationResult(
            stage=ValidationStage.EXECUTION,
            passed=passed,
            score=avg_score,
            detail=detail,
            tokens_used=total_tokens,
            timestamp=now,
            test_task_ids=test_task_ids,
        )

    def _stage_3_comparison(
        self,
        record: SkillRecord,
        execute_fn: ModelExecuteFn,
        test_tasks: list[Task],
        budget: int,
    ) -> ValidationResult:
        """Stage 3: Comparison -- is this skill better than baseline?

        A/B test: runs test tasks with and without the skill instruction.
        Must show >= min_improvement_pp percentage point improvement.

        FM-S05: Improvement threshold matches ring_3_to_2 criteria (+5pp).
        FM-S07: Respects per-stage budget cap.

        Args:
            record: Skill being validated.
            execute_fn: LLM execution function.
            test_tasks: Archived tasks for A/B comparison.
            budget: Remaining token budget for this stage.

        Returns:
            ValidationResult with improvement delta.
        """
        now = datetime.now(timezone.utc)
        stage_budget = min(
            budget, self._stage_budgets[ValidationStage.COMPARISON]
        )
        # Budget split: half for baseline, half for with-skill
        half_budget = stage_budget // 2
        # SF-4: Divide by comparison_runs (not total test_tasks).
        # Stage 3 only uses comparison_runs tasks, so per-task budget
        # should reflect the actual number of tasks that will be run.
        per_task_budget = half_budget // max(self._comparison_runs, 1)

        total_tokens = 0
        baseline_scores: list[float] = []
        skill_scores: list[float] = []

        # Select test tasks (use same ones as stage 2 for consistency)
        selected_tasks = test_tasks[:self._comparison_runs]

        # IFM-N32: Paired comparison -- run baseline and skill on the SAME
        # task in sequence. Only compare scores when BOTH produce parseable
        # results for a given task. This prevents mismatched score lists.
        for test_task in selected_tasks:
            if total_tokens >= stage_budget:
                break

            # Run baseline (without skill)
            baseline_prompt = BASELINE_PROMPT.format(
                task_title=test_task.title,
                task_description=test_task.description[:500],
            )

            try:
                baseline_output, baseline_tokens = execute_fn(
                    baseline_prompt, per_task_budget
                )
                total_tokens += baseline_tokens
                baseline_quality = self._parse_quality_score(baseline_output)
            except Exception as e:
                logger.warning(
                    f"Stage 3 baseline failed for task {test_task.id}: {e}"
                )
                baseline_quality = None

            # Run with skill
            skill_prompt = EXECUTION_TEST_PROMPT.format(
                skill_name=record.name,
                skill_instruction=record.instruction_fragment,
                task_title=test_task.title,
                task_description=test_task.description[:500],
            )

            try:
                skill_output, skill_tokens = execute_fn(
                    skill_prompt, per_task_budget
                )
                total_tokens += skill_tokens
                skill_quality = self._parse_quality_score(skill_output)
            except Exception as e:
                logger.warning(
                    f"Stage 3 with-skill failed for task {test_task.id}: {e}"
                )
                skill_quality = None

            # IFM-N32: Only include this task if BOTH scores parsed successfully
            if baseline_quality is not None and skill_quality is not None:
                baseline_scores.append(baseline_quality / 10.0)
                skill_scores.append(skill_quality / 10.0)
            else:
                logger.warning(
                    f"Stage 3 skipping task {test_task.id}: "
                    f"unpaired scores (baseline={baseline_quality}, "
                    f"skill={skill_quality})"
                )

        if not baseline_scores or not skill_scores:
            return ValidationResult(
                stage=ValidationStage.COMPARISON,
                passed=False,
                score=0.0,
                detail="Insufficient comparison data",
                tokens_used=total_tokens,
                timestamp=now,
            )

        baseline_avg = sum(baseline_scores) / len(baseline_scores)
        skill_avg = sum(skill_scores) / len(skill_scores)
        # Improvement in percentage points (0-100 scale)
        improvement_pp = (skill_avg - baseline_avg) * 100.0

        passed = improvement_pp >= self._min_improvement_pp

        detail = (
            f"Baseline avg: {baseline_avg:.2f}, "
            f"Skill avg: {skill_avg:.2f}, "
            f"Improvement: {improvement_pp:+.1f}pp "
            f"(threshold: {self._min_improvement_pp}pp)"
        )

        return ValidationResult(
            stage=ValidationStage.COMPARISON,
            passed=passed,
            score=skill_avg,
            detail=detail,
            tokens_used=total_tokens,
            timestamp=now,
            improvement_delta=improvement_pp,
        )

    def _stage_4_review(
        self, record: SkillRecord, budget: int
    ) -> ValidationResult:
        """Stage 4: Review -- generate review request for approval.

        This stage does NOT auto-approve. It generates a review summary
        that a human or senior agent can review. The skill stays in
        STAGE_3_PASSED status until approve_skill() or reject_skill()
        is called.

        Args:
            record: Skill that passed stages 1-3.
            budget: Remaining token budget (used for review summary only).

        Returns:
            ValidationResult with review request details.
            passed=False indicates review is pending (not a failure).
        """
        now = datetime.now(timezone.utc)

        # Build review summary from validation results
        summary_parts = [
            f"Skill: {record.name}",
            f"Description: {record.description}",
            f"Source task: {record.source.task_id}",
            f"Instruction ({len(record.instruction_fragment)} chars):",
            f"  {record.instruction_fragment[:200]}...",
        ]
        for vr in record.validation_results:
            summary_parts.append(
                f"  Stage {vr.stage}: "
                f"{'PASS' if vr.passed else 'FAIL'} "
                f"(score={vr.score:.2f}, tokens={vr.tokens_used})"
            )
            if vr.improvement_delta is not None:
                summary_parts.append(
                    f"    Improvement: {vr.improvement_delta:+.1f}pp"
                )

        review_summary = "\n".join(summary_parts)

        # Log the review request
        logger.info(
            f"Skill '{record.name}' awaiting review:\n{review_summary}"
        )

        # Review is pending -- return passed=False to indicate awaiting approval
        # The approve_skill() method will add a passed=True result later
        return ValidationResult(
            stage=ValidationStage.REVIEW,
            passed=False,  # Pending, not failed
            score=0.0,
            detail=f"Review pending. Summary:\n{review_summary}",
            tokens_used=0,
            timestamp=now,
        )

    def _parse_quality_score(self, output: str) -> float | None:
        """Parse a QUALITY: <1-10> score from LLM output.

        Returns the parsed score clamped to [1, 10], or None if unparseable.

        IFM-N10: Previously returned 5.0 as fallback, which equals the Stage 2
        passing threshold (5/10) -- causing parse failures to count as passing.
        Now returns None so callers can skip unparseable results.
        """
        match = re.search(r"QUALITY:\s*(\d+(?:\.\d+)?)", output)
        if match:
            score = float(match.group(1))
            return max(1.0, min(10.0, score))  # Clamp to 1-10
        logger.warning(
            "Could not parse QUALITY score from output -- skipping this result"
        )
        return None

    def _persist_record(self, record: SkillRecord) -> None:
        """Persist a skill record to YAML.

        FM-S10: Uses skill name for filename to prevent unbounded growth.
        """
        record.updated_at = datetime.now(timezone.utc)
        self.yaml_store.write(
            f"{self._skills_base}/{record.name}.yaml",
            record,
        )

    def _log_validation_decision(
        self, record: SkillRecord, decision: str
    ) -> None:
        """Log a validation decision to the DECISIONS audit stream."""
        if self._audit_logger is None:
            return
        try:
            stages = [
                {
                    "stage": vr.stage,
                    "passed": vr.passed,
                    "score": vr.score,
                }
                for vr in record.validation_results
            ]
            entry = DecisionLogEntry(
                id=generate_id("dec"),
                timestamp=datetime.now(timezone.utc),
                decision_type=f"skill_validation_{decision}",
                actor="skill_validator",
                options_considered=stages,
                selected=decision,
                rationale=(
                    f"Skill '{record.name}' validation: {decision}. "
                    f"Stages completed: {len(record.validation_results)}"
                ),
            )
            self._audit_logger.log_decision(entry)
        except Exception as e:
            logger.warning(f"Failed to log validation decision: {e}")
