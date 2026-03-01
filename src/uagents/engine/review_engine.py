"""Review mandate enforcement engine.
Spec reference: Section 6.2 (Task Lifecycle), Axiom A7."""
from __future__ import annotations

from datetime import datetime

from ..audit.logger import AuditLogger
from ..models.audit import DecisionLogEntry, LogStream
from ..models.base import generate_id
from ..models.task import Task, TaskReview, TaskStatus
from ..state.yaml_store import YamlStore
from .task_lifecycle import TaskLifecycle


class ReviewViolationError(RuntimeError):
    """Raised when review mandate is violated."""


class ReviewEngine:
    """Enforces mandatory review for all tasks.

    Invariants (Axiom A7):
    - Every task MUST pass through REVIEWING before COMPLETE
    - Reviewer MUST NOT be the same agent that executed the task
    - Review MUST contain specific findings (no rubber-stamping)
    - Failed reviews send task back to PLANNING with feedback

    Review flow:
    1. Task reaches EXECUTING -> REVIEWING transition
    2. ReviewEngine validates reviewer is different from executor
    3. Reviewer agent examines work artifacts
    4. Reviewer submits structured review (findings, verdict, confidence)
    5. If verdict == "fail": task -> PLANNING with review feedback
    6. If verdict == "pass"/"pass_with_notes": task -> VERDICT -> COMPLETE
    """

    # Minimum findings required to prevent rubber-stamping
    MIN_FINDINGS = 1
    # Minimum reviewer confidence to accept
    MIN_CONFIDENCE = 0.3

    def __init__(
        self,
        yaml_store: YamlStore,
        task_lifecycle: TaskLifecycle,
        audit_logger: AuditLogger | None = None,
    ):
        self.yaml_store = yaml_store
        self.task_lifecycle = task_lifecycle
        self.audit_logger = audit_logger

    def validate_review_eligible(self, task: Task) -> None:
        """Check that task is ready for review."""
        if task.status != TaskStatus.REVIEWING.value:
            raise ReviewViolationError(
                f"Task {task.id} is in {task.status}, not REVIEWING"
            )

    def submit_review(
        self,
        task_id: str,
        reviewer_id: str,
        reviewer_role: str,
        findings: list[str],
        verdict: str,  # "pass", "pass_with_notes", "fail"
        confidence: float,
    ) -> Task:
        """Submit a review for a task.

        Validates review quality:
        - Must have at least MIN_FINDINGS findings
        - Confidence must be at least MIN_CONFIDENCE
        - Verdict must be one of: pass, pass_with_notes, fail

        Returns updated task after applying review.
        """
        # Validate verdict
        valid_verdicts = {"pass", "pass_with_notes", "fail"}
        if verdict not in valid_verdicts:
            raise ReviewViolationError(
                f"Invalid verdict '{verdict}'. Must be one of: {valid_verdicts}"
            )

        # Validate findings (prevent rubber-stamping)
        if len(findings) < self.MIN_FINDINGS:
            raise ReviewViolationError(
                f"Review must contain at least {self.MIN_FINDINGS} finding(s). "
                f"Got {len(findings)}. Rubber-stamp reviews are not allowed (A7)."
            )

        # Validate confidence
        if confidence < self.MIN_CONFIDENCE:
            raise ReviewViolationError(
                f"Reviewer confidence {confidence} below minimum {self.MIN_CONFIDENCE}. "
                f"If unsure, request more context rather than low-confidence approval."
            )

        # Validate reviewer is not the executor
        task = self.task_lifecycle._load_task(task_id)
        self.validate_review_eligible(task)
        self._validate_not_self_review(task, reviewer_id)

        # Record review
        review = TaskReview(
            reviewer=reviewer_id,
            reviewer_role=reviewer_role,
            findings=findings,
            verdict=verdict,
            reviewer_confidence=confidence,
        )
        task.review = review

        # Increment review rounds in task metrics
        if task.metrics:
            review_rounds = getattr(task.metrics, "review_rounds", 0)
            task.metrics.review_rounds = review_rounds + 1

        # Escalate to human after 3 failed rounds (before transition)
        if task.metrics and task.metrics.review_rounds >= 3 and verdict == "fail":
            raise ReviewViolationError(
                f"Task {task_id} has failed review {task.metrics.review_rounds} times. "
                f"Escalating to human — automatic re-plan loop limit reached."
            )

        # Persist review and metrics to disk BEFORE transition.
        # This ensures transition() (which reloads from disk) picks up the review data.
        # If transition fails, the review-on-disk is recoverable state.
        self._persist_review(task)

        # Apply verdict — REVIEWING -> VERDICT first (mandatory intermediate state)
        task = self.task_lifecycle.transition(
            task_id, TaskStatus.VERDICT, reviewer_id,
            f"Review {verdict}: {'; '.join(findings[:3])}"
        )

        if verdict == "fail":
            # Failed review: VERDICT -> PLANNING with feedback
            feedback = "; ".join(findings)
            task = self.task_lifecycle.transition(
                task_id, TaskStatus.PLANNING, reviewer_id,
                f"Review FAILED (round {task.metrics.review_rounds if task.metrics else '?'}): {feedback}"
            )
        # If pass/pass_with_notes: stays at VERDICT, caller advances to COMPLETE

        return task

    def get_review(self, task_id: str) -> TaskReview | None:
        """Get the review for a task, if any."""
        task = self.task_lifecycle._load_task(task_id)
        return task.review

    def _validate_not_self_review(self, task: Task, reviewer_id: str) -> None:
        """Ensure reviewer didn't also execute the task.

        Two checks:
        1. Timeline: agents who triggered the EXECUTING transition
        2. Team membership: if task has a team, check the reviewer wasn't a worker
        """
        # Check 1: Timeline — agents who transitioned into EXECUTING
        for entry in task.timeline:
            if (f"\u2192{TaskStatus.EXECUTING.value}" in entry.event
                    and entry.actor == reviewer_id):
                raise ReviewViolationError(
                    f"Agent {reviewer_id} cannot review task {task.id} \u2014 "
                    f"they were the executor. Self-review violates Axiom A7."
                )

        # Check 2: Team membership — reviewer must not be a worker on the team
        if task.team_id:
            try:
                teams_base = self.task_lifecycle._tasks_base.replace(
                    "/state/tasks", "/state/teams"
                )
                team_data = self.yaml_store.read_raw(
                    f"{teams_base}/{task.team_id}/team.yaml"
                )
                for member in team_data.get("members", []):
                    if (member.get("agent_id") == reviewer_id
                            and member.get("role") not in ("reviewer", "orchestrator")):
                        raise ReviewViolationError(
                            f"Agent {reviewer_id} cannot review task {task.id} \u2014 "
                            f"they are a worker on team {task.team_id}. "
                            f"Self-review violates Axiom A7."
                        )
            except FileNotFoundError:
                pass  # Team file missing — skip team check

    def _persist_review(self, task: Task) -> None:
        """Persist review to task YAML file.

        Uses TaskLifecycle._tasks_base for domain-scoped paths.
        """
        tasks_base = self.task_lifecycle._tasks_base
        for subdir in ("active", "parked", "completed"):
            path = f"{tasks_base}/{subdir}/{task.id}.yaml"
            try:
                self.yaml_store.read_raw(path)
                # Found it -- write updated task
                self.yaml_store.write(path, task)
                return
            except FileNotFoundError:
                continue
        raise FileNotFoundError(f"Task {task.id} not found in any task directory")
