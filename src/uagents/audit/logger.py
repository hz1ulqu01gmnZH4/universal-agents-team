"""Central audit logger dispatching to 8 JSONL streams.
Spec reference: Section 17 (Audit System & Viewers)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..models.audit import (
    BaseLogEntry,
    DecisionLogEntry,
    EnvironmentLogEntry,
    EvolutionLogEntry,
    LogStream,
    ResourceLogEntry,
    TaskLogEntry,
    TraceLogEntry,
)
from ..state.jsonl_writer import JsonlWriter


class AuditLogger:
    """Central audit dispatcher for all 8 log streams.

    Design invariants:
    - Every log method validates entry type matches stream
    - Cross-stream queries supported for timeline reconstruction
    - Phase 0 active streams: tasks, decisions (others are stubs)
    """

    def __init__(self, log_root: Path):
        self.log_root = log_root
        self.writers: dict[LogStream, JsonlWriter] = {
            stream: JsonlWriter(log_root / stream.value, stream)
            for stream in LogStream
        }

    def log_evolution(self, entry: EvolutionLogEntry) -> None:
        self.writers[LogStream.EVOLUTION].append(entry)

    def log_task(self, entry: TaskLogEntry) -> None:
        self.writers[LogStream.TASKS].append(entry)

    def log_decision(self, entry: DecisionLogEntry) -> None:
        self.writers[LogStream.DECISIONS].append(entry)

    def log_resource(self, entry: ResourceLogEntry) -> None:
        self.writers[LogStream.RESOURCES].append(entry)

    def log_environment(self, entry: EnvironmentLogEntry) -> None:
        self.writers[LogStream.ENVIRONMENT].append(entry)

    def log_trace(self, entry: TraceLogEntry) -> None:
        self.writers[LogStream.TRACES].append(entry)

    def query(
        self,
        stream: LogStream,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query a single stream with optional time filter."""
        return self.writers[stream].read_entries(since=since, until=until, limit=limit)

    def query_all(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Cross-stream query, merged chronologically."""
        all_entries: list[dict] = []
        for writer in self.writers.values():
            entries = writer.read_entries(since=since, until=until, limit=limit)
            all_entries.extend(entries)
        all_entries.sort(key=lambda e: e.get("timestamp", ""))
        return all_entries[:limit]
