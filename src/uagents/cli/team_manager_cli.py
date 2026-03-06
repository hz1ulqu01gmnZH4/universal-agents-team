"""Team management CLI — list, status, dissolve teams.
Spec reference: Section 4.4 (Team Lifecycle)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage teams")
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="List active teams")
    list_p.add_argument("--root", default=".", help="Framework root")
    list_p.add_argument("--domain", default="meta")

    status_p = sub.add_parser("status", help="Show team status")
    status_p.add_argument("--root", default=".", help="Framework root")
    status_p.add_argument("--domain", default="meta")
    status_p.add_argument("--team-id", required=True)

    dissolve_p = sub.add_parser("dissolve", help="Dissolve a team")
    dissolve_p.add_argument("--root", default=".", help="Framework root")
    dissolve_p.add_argument("--domain", default="meta")
    dissolve_p.add_argument("--team-id", required=True)
    dissolve_p.add_argument("--reason", default="CLI-initiated dissolution")

    args = parser.parse_args()
    root = Path(args.root).resolve()

    from ..engine.framework_factory import FrameworkFactory

    factory = FrameworkFactory(root, args.domain)
    orchestrator = factory.build()
    tm = orchestrator.team_manager

    if args.command == "list":
        teams_dir = f"instances/{args.domain}/state/teams"
        try:
            names = orchestrator.yaml_store.list_dir(teams_dir)
        except (FileNotFoundError, NotADirectoryError):
            names = []
        for name in names:
            if name.endswith(".yaml"):
                data = orchestrator.yaml_store.read_raw(f"{teams_dir}/{name}")
                print(json.dumps({
                    "team_id": data.get("id", name),
                    "status": data.get("status", "unknown"),
                    "task_id": data.get("task_id", ""),
                    "member_count": len(data.get("members", [])),
                }))

    elif args.command == "status":
        team_path = f"instances/{args.domain}/state/teams/{args.team_id}.yaml"
        try:
            data = orchestrator.yaml_store.read_raw(team_path)
        except FileNotFoundError:
            print(f"Team {args.team_id} not found", file=sys.stderr)
            raise SystemExit(1)
        print(json.dumps(data, indent=2, default=str))

    elif args.command == "dissolve":
        tm.dissolve_team(args.team_id, args.reason)
        print(f"Team {args.team_id} dissolved.")


if __name__ == "__main__":
    main()
