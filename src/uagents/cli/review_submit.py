"""Submit a review for a task in REVIEWING status.
Spec reference: Section 5.5 (Review Process), Axiom A7."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Submit a review for a task"
    )
    parser.add_argument("--root", default=".", help="Framework root directory")
    parser.add_argument("--domain", default="meta", help="Domain name")
    parser.add_argument("--task-id", required=True, help="Task ID to review")
    parser.add_argument("--reviewer-id", required=True, help="Reviewer agent ID")
    parser.add_argument("--reviewer-role", default="reviewer", help="Reviewer role")
    parser.add_argument("--verdict", required=True,
                        choices=["pass", "fail", "pass_with_notes"],
                        help="Review verdict")
    parser.add_argument("--confidence", type=float, default=0.8,
                        help="Confidence score (0.0-1.0)")
    parser.add_argument("--findings", required=True, nargs="+",
                        help="Review findings (one or more strings)")
    args = parser.parse_args()

    root = Path(args.root).resolve()

    from ..engine.framework_factory import FrameworkFactory

    factory = FrameworkFactory(root, args.domain)
    orchestrator = factory.build()

    task = orchestrator.review_engine.submit_review(
        task_id=args.task_id,
        reviewer_id=args.reviewer_id,
        reviewer_role=args.reviewer_role,
        findings=args.findings,
        verdict=args.verdict,
        confidence=args.confidence,
    )

    # submit_review leaves pass/pass_with_notes at VERDICT; advance to COMPLETE
    from ..models.task import TaskStatus
    if args.verdict in ("pass", "pass_with_notes"):
        task = orchestrator.task_lifecycle.transition(
            task.id, TaskStatus.COMPLETE, args.reviewer_id,
            f"Review passed ({args.verdict})",
        )

    print(json.dumps({
        "task_id": task.id,
        "status": str(task.status),
        "verdict": args.verdict,
    }, indent=2))


if __name__ == "__main__":
    main()
