"""Task lifecycle CRUD CLI.
Spec reference: Part 8 (Step 9), Part 4.5 (TaskLifecycle)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..models.task import TaskOrigin, TaskOriginType, TaskStatus
from ..state.yaml_store import YamlStore
from ..engine.task_lifecycle import TaskLifecycle


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Task lifecycle management"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    create_parser = subparsers.add_parser("create", help="Create a new task")
    create_parser.add_argument("--title", required=True, help="Task title")
    create_parser.add_argument("--description", required=True, help="Task description")
    create_parser.add_argument(
        "--origin", default="human",
        choices=["human", "agent_generated", "evolution_triggered", "scout_discovery"],
        help="Task origin type (default: human)"
    )
    create_parser.add_argument(
        "--priority", default="medium",
        choices=["low", "medium", "high", "critical"],
        help="Task priority (default: medium)"
    )
    create_parser.add_argument(
        "--rationale", default="",
        help="Why this task exists"
    )
    create_parser.add_argument(
        "--domain", default="meta",
        help="Domain name (default: meta)"
    )
    create_parser.add_argument(
        "--root", default=".",
        help="Framework root directory (default: current dir)"
    )

    # transition
    trans_parser = subparsers.add_parser("transition", help="Transition task state")
    trans_parser.add_argument("--task-id", required=True, help="Task ID")
    trans_parser.add_argument(
        "--status", required=True,
        choices=[s.value for s in TaskStatus],
        help="Target status"
    )
    trans_parser.add_argument(
        "--actor", default="human",
        help="Who is performing this transition"
    )
    trans_parser.add_argument(
        "--detail", default="",
        help="Transition detail message"
    )
    trans_parser.add_argument("--domain", default="meta")
    trans_parser.add_argument("--root", default=".")

    # list
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument(
        "--filter", default="active",
        choices=["active", "parked", "all"],
        help="Filter tasks (default: active)"
    )
    list_parser.add_argument("--domain", default="meta")
    list_parser.add_argument("--root", default=".")

    # show
    show_parser = subparsers.add_parser("show", help="Show task details")
    show_parser.add_argument("--task-id", required=True, help="Task ID")
    show_parser.add_argument("--domain", default="meta")
    show_parser.add_argument("--root", default=".")

    # park
    park_parser = subparsers.add_parser("park", help="Park a task")
    park_parser.add_argument("--task-id", required=True, help="Task ID")
    park_parser.add_argument("--reason", required=True, help="Reason for parking")
    park_parser.add_argument("--actor", default="human")
    park_parser.add_argument("--domain", default="meta")
    park_parser.add_argument("--root", default=".")

    # resume
    resume_parser = subparsers.add_parser("resume", help="Resume a parked task")
    resume_parser.add_argument("--task-id", required=True, help="Task ID")
    resume_parser.add_argument("--actor", default="human")
    resume_parser.add_argument("--domain", default="meta")
    resume_parser.add_argument("--root", default=".")

    args = parser.parse_args()
    root = Path(args.root).resolve()
    yaml_store = YamlStore(root)
    lifecycle = TaskLifecycle(yaml_store, args.domain)

    if args.command == "create":
        origin = TaskOrigin(
            type=TaskOriginType(args.origin),
            source="cli",
            reason=args.rationale or args.title,
        )
        task = lifecycle.create(
            title=args.title,
            description=args.description,
            origin=origin,
            priority=args.priority,
            rationale=args.rationale,
        )
        print(f"Task created: {task.id}")
        print(f"  Title:    {task.title}")
        print(f"  Status:   {task.status}")
        print(f"  Priority: {task.priority}")

    elif args.command == "transition":
        new_status = TaskStatus(args.status)
        task = lifecycle.transition(
            task_id=args.task_id,
            new_status=new_status,
            actor=args.actor,
            detail=args.detail or f"Transitioned to {args.status}",
        )
        print(f"Task {task.id} transitioned to {task.status}")

    elif args.command == "list":
        if args.filter == "active":
            tasks = lifecycle.get_active()
        elif args.filter == "parked":
            tasks = lifecycle.get_parked()
        else:
            tasks = lifecycle.get_active() + lifecycle.get_parked()

        if not tasks:
            print("No tasks found.")
        else:
            for task in tasks:
                print(f"  [{task.status}] {task.id}: {task.title}")

    elif args.command == "show":
        # Load task from any directory
        task = lifecycle._load_task(args.task_id)
        print(f"Task: {task.id}")
        print(f"  Title:       {task.title}")
        print(f"  Status:      {task.status}")
        print(f"  Priority:    {task.priority}")
        print(f"  Description: {task.description}")
        print(f"  Origin:      {task.origin.type} ({task.origin.source})")
        print(f"  Created:     {task.created_at}")
        if task.timeline:
            print("  Timeline:")
            for entry in task.timeline:
                print(f"    {entry.time} | {entry.event} | {entry.actor}")

    elif args.command == "park":
        task = lifecycle.park(args.task_id, args.reason, args.actor)
        print(f"Task {task.id} parked: {args.reason}")

    elif args.command == "resume":
        task = lifecycle.resume(args.task_id, args.actor)
        print(f"Task {task.id} resumed to {task.status}")


if __name__ == "__main__":
    main()
