"""Resource monitoring dashboard CLI.
Spec reference: Section 18 (Resource Awareness)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    """Display current resource status: compute, agents, token estimates."""
    parser = argparse.ArgumentParser(
        description="Resource monitoring dashboard"
    )
    parser.add_argument(
        "--domain", default="meta", help="Domain instance (default: meta)"
    )
    parser.add_argument(
        "--root", default=".", help="Framework root directory"
    )
    parser.add_argument(
        "--check-spawn",
        action="store_true",
        help="Check if an agent can be spawned",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: Framework root not found: {root}", file=sys.stderr)
        sys.exit(1)

    from uagents.engine.resource_tracker import ResourceTracker
    from uagents.state.yaml_store import YamlStore

    state_dir = root / "instances" / args.domain / "state"
    if not state_dir.is_dir():
        print(
            f"ERROR: Domain state directory not found: {state_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    store = YamlStore(root)
    tracker = ResourceTracker(store, state_dir)

    # Compute metrics
    metrics = tracker.check_compute()
    print("=== Resource Monitor ===")
    print(f"  CPU:           {metrics.cpu_percent:.1f}%")
    print(f"  Memory:        {metrics.memory_percent:.1f}%")
    print(f"  Disk:          {metrics.disk_percent:.1f}%")
    print(f"  Active agents: {metrics.active_agents}/{metrics.max_agents}")

    # Spend level
    backpressure = tracker.get_backpressure_level()
    print(f"  Backpressure:  {backpressure:.1f}")

    # Spawn check
    if args.check_spawn:
        can_spawn, reason = tracker.can_spawn_agent()
        status = "YES" if can_spawn else "NO"
        print(f"\n  Can spawn: {status} — {reason}")

    # Token usage (try /usage)
    usage = tracker.parse_usage_output()
    if usage:
        print("\n=== Token Usage ===")
        for key, val in usage.items():
            print(f"  {key}: {val}")
    else:
        print("\n  Token usage: unavailable (Claude /usage not accessible)")


if __name__ == "__main__":
    main()
