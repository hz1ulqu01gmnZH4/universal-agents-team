"""Terminal tree viewer for audit logs.
Spec reference: Part 4.9 (AuditTreeViewer)."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..audit.logger import AuditLogger
from ..audit.tree_viewer import AuditTreeViewer
from ..models.audit import LogStream


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit log tree viewer"
    )
    parser.add_argument(
        "--since", default="today",
        help="Start time: 'today', ISO datetime, or relative like '1h', '30m' (default: today)"
    )
    parser.add_argument(
        "--until", default=None,
        help="End time: ISO datetime (default: now)"
    )
    parser.add_argument(
        "--stream", nargs="*", default=None,
        help="Log streams to display (default: tasks decisions)"
    )
    parser.add_argument(
        "--task-id", default=None,
        help="Show detailed timeline for a specific task"
    )
    parser.add_argument(
        "--domain", default="meta",
        help="Domain name (default: meta)"
    )
    parser.add_argument(
        "--root", default=".",
        help="Framework root directory (default: current dir)"
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    log_root = root / "instances" / args.domain / "logs"
    logger = AuditLogger(log_root)
    viewer = AuditTreeViewer(logger)

    # Parse --since
    since = _parse_time(args.since)

    # Parse --until
    until = _parse_time(args.until) if args.until else None

    # Parse streams
    streams = None
    if args.stream:
        streams = [LogStream(s) for s in args.stream]

    if args.task_id:
        viewer.render_task_detail(args.task_id)
    else:
        viewer.render_session(since=since, until=until, streams=streams)


def _parse_time(value: str) -> datetime:
    """Parse time specification: 'today', ISO datetime, or relative."""
    if value == "today":
        now = datetime.now(timezone.utc)
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if value == "now":
        return datetime.now(timezone.utc)

    # Relative time: e.g. '1h', '30m', '2d'
    if value and value[-1] in ("h", "m", "d") and value[:-1].isdigit():
        amount = int(value[:-1])
        unit = value[-1]
        delta_map = {"h": "hours", "m": "minutes", "d": "days"}
        return datetime.now(timezone.utc) - timedelta(**{delta_map[unit]: amount})

    # ISO format
    return datetime.fromisoformat(value)


if __name__ == "__main__":
    main()
