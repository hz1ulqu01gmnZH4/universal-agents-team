"""Analyze a task and recommend topology.
Spec reference: Section 5 (Topology Selection)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze task and recommend topology"
    )
    parser.add_argument("--root", default=".", help="Framework root directory")
    parser.add_argument("--domain", default="meta", help="Domain name")
    parser.add_argument("--task-id", required=True, help="Task ID to analyze")
    args = parser.parse_args()

    root = Path(args.root).resolve()

    from ..engine.framework_factory import FrameworkFactory

    factory = FrameworkFactory(root, args.domain)
    orchestrator = factory.build()

    try:
        task = orchestrator.task_lifecycle._load_task(args.task_id)
    except FileNotFoundError:
        print(f"Error: Task {args.task_id} not found", file=sys.stderr)
        raise SystemExit(1)

    analysis = orchestrator.topology_router.analyze(task)
    routing = orchestrator.topology_router.route(analysis, task)

    print(json.dumps({
        "task_id": task.id,
        "recommended_topology": routing.pattern,
        "agent_count": routing.agent_count,
        "role_assignments": routing.role_assignments,
        "rationale": routing.rationale,
        "analysis": {
            "decomposability": str(analysis.decomposability),
            "interdependency": str(analysis.interdependency),
            "exploration_vs_execution": str(analysis.exploration_vs_execution),
            "quality_criticality": str(analysis.quality_criticality),
            "scale": str(analysis.scale),
            "novelty": str(analysis.novelty),
        },
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
