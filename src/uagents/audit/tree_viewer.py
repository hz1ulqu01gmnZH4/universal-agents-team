"""Terminal tree viewer using rich library.
Spec reference: Section 17.3 (Audit Viewer Formats)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.tree import Tree

from .logger import AuditLogger
from ..models.audit import LogStream


class AuditTreeViewer:
    """Renders audit logs as a collapsible terminal tree.

    User preference: tree-like GUI for audit viewing.
    """

    def __init__(self, audit_logger: AuditLogger):
        self.logger = audit_logger
        self.console = Console()

    def render_session(
        self,
        since: datetime,
        until: datetime | None = None,
        streams: list[LogStream] | None = None,
    ) -> None:
        """Render session audit tree to terminal."""
        if streams is None:
            streams = [LogStream.TASKS, LogStream.DECISIONS]

        tree = Tree(f"[bold]Session audit: {since.isoformat()}[/bold]")

        for stream in streams:
            entries = self.logger.query(stream, since=since, until=until, limit=200)
            if not entries:
                continue
            branch = tree.add(f"[cyan]{stream.value}[/cyan] ({len(entries)} entries)")
            for entry in entries:
                ts = entry.get("timestamp", "?")[:19]
                event = entry.get("event", entry.get("decision_type", "?"))
                actor = entry.get("actor", "?")
                branch.add(f"[dim]{ts}[/dim] {event} — {actor}")

        self.console.print(tree)

    def render_task_detail(self, task_id: str) -> None:
        """Render a single task's full timeline."""
        entries = self.logger.query(LogStream.TASKS, limit=500)
        task_entries = [e for e in entries if e.get("task_id") == task_id]

        tree = Tree(f"[bold]Task: {task_id}[/bold]")
        for entry in task_entries:
            ts = entry.get("timestamp", "?")[:19]
            event = entry.get("event", "?")
            actor = entry.get("actor", "?")
            detail = entry.get("detail", {})
            node = tree.add(f"[dim]{ts}[/dim] [green]{event}[/green] — {actor}")
            if detail:
                for k, v in detail.items():
                    node.add(f"{k}: {v}")

        self.console.print(tree)
