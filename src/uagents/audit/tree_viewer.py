"""Terminal tree viewer using rich library.
Spec reference: Section 17.3 (Audit Viewer Formats).

Phase 2: Enhanced with diversity snapshot rendering and stagnation alerts.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from ..models.audit import LogStream
from .logger import AuditLogger


class AuditTreeViewer:
    """Renders audit logs as a collapsible terminal tree.

    Phase 2 enhancements:
    - Diversity stream rendering with SRD health color coding
    - Stagnation signal display
    - Cross-stream timeline view
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
            streams = [LogStream.TASKS, LogStream.DECISIONS, LogStream.DIVERSITY]

        tree = Tree(f"[bold]Session audit: {since.isoformat()}[/bold]")

        for stream in streams:
            entries = self.logger.query(stream, since=since, until=until, limit=200)
            if not entries:
                continue

            if stream == LogStream.DIVERSITY:
                self._render_diversity_branch(tree, entries)
            else:
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

    def render_diversity_summary(
        self,
        since: datetime,
        until: datetime | None = None,
    ) -> None:
        """Render diversity metrics summary as a table."""
        entries = self.logger.query(
            LogStream.DIVERSITY, since=since, until=until, limit=100
        )

        table = Table(title="Diversity Metrics")
        table.add_column("Task", style="cyan")
        table.add_column("SRD", justify="right")
        table.add_column("Text Div", justify="right")
        table.add_column("VDI", justify="right")
        table.add_column("Agents", justify="right")
        table.add_column("Health", justify="center")
        table.add_column("Stagnation", style="yellow")

        for entry in entries:
            srd = entry.get("srd_composite", 0.0)
            health = entry.get("health_status", "?")
            health_style = self._health_color(health)
            stag_signals = entry.get("stagnation_signals", [])
            stag_text = ", ".join(
                s.get("level", "?") for s in stag_signals
            ) if stag_signals else "-"

            table.add_row(
                entry.get("task_id", "?")[-12:],
                f"{srd:.3f}",
                f"{entry.get('text_diversity', 0.0):.3f}",
                f"{entry.get('vdi_score', 0.0):.3f}" if entry.get("vdi_score") else "-",
                str(entry.get("agent_count", "?")),
                f"[{health_style}]{health}[/{health_style}]",
                stag_text,
            )

        self.console.print(table)

    def render_timeline(
        self,
        since: datetime,
        until: datetime | None = None,
        limit: int = 50,
    ) -> None:
        """Render cross-stream timeline (all events merged chronologically)."""
        entries = self.logger.query_all(since=since, until=until, limit=limit)

        tree = Tree(f"[bold]Timeline: {since.isoformat()}[/bold]")
        for entry in entries:
            ts = entry.get("timestamp", "?")[:19]
            stream = entry.get("stream", "?")
            stream_color = self._stream_color(stream)

            if stream == "tasks":
                label = f"{entry.get('event', '?')} — {entry.get('actor', '?')}"
            elif stream == "decisions":
                label = f"{entry.get('decision_type', '?')} → {entry.get('selected', '?')}"
            elif stream == "diversity":
                srd = entry.get("srd_composite", 0.0)
                health = entry.get("health_status", "?")
                label = f"SRD={srd:.3f} ({health})"
            elif stream == "resources":
                label = entry.get("event_type", "?")
            else:
                label = entry.get("event_type", str(entry.get("detail", "?")))

            tree.add(
                f"[dim]{ts}[/dim] [{stream_color}]{stream}[/{stream_color}] {label}"
            )

        self.console.print(tree)

    def _render_diversity_branch(
        self, tree: Tree, entries: list[dict]
    ) -> None:
        """Render diversity entries with health color coding."""
        branch = tree.add(
            f"[cyan]diversity[/cyan] ({len(entries)} measurements)"
        )
        for entry in entries:
            srd = entry.get("srd_composite", 0.0)
            health = entry.get("health_status", "?")
            color = self._health_color(health)
            task = entry.get("task_id", "?")[-12:]
            agents = entry.get("agent_count", "?")

            node = branch.add(
                f"[dim]{entry.get('timestamp', '?')[:19]}[/dim] "
                f"Task {task}: SRD=[{color}]{srd:.3f}[/{color}] "
                f"({agents} agents, {health})"
            )

            # Show stagnation signals as sub-nodes
            for signal in entry.get("stagnation_signals", []):
                level = signal.get("level", "?")
                desc = signal.get("description", "?")
                node.add(f"[yellow]⚠ {level}:[/yellow] {desc}")

    @staticmethod
    def _health_color(health: str) -> str:
        """Map health status to rich color."""
        return {
            "critical": "red bold",
            "warning": "yellow",
            "healthy": "green",
            "high": "cyan",
            "incoherent": "magenta",
        }.get(health, "white")

    @staticmethod
    def _stream_color(stream: str) -> str:
        """Map stream name to rich color."""
        return {
            "tasks": "green",
            "decisions": "blue",
            "diversity": "magenta",
            "resources": "yellow",
            "evolution": "red",
            "environment": "cyan",
            "creativity": "bright_magenta",
            "traces": "dim",
        }.get(stream, "white")
