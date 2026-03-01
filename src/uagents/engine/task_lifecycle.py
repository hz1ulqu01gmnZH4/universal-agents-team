"""Task lifecycle state machine.
Spec reference: Section 6 (Task Lifecycle)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from ..models.task import (
    VALID_TRANSITIONS,
    Task,
    TaskMetrics,
    TaskOrigin,
    TaskStatus,
    TaskTimelineEntry,
)
from ..models.base import generate_id
from ..state.yaml_store import YamlStore


class InvalidTransitionError(ValueError):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, task_id: str, current: TaskStatus, attempted: TaskStatus):
        valid = VALID_TRANSITIONS.get(current, set())
        super().__init__(
            f"Invalid transition for task {task_id}: "
            f"{current} → {attempted}. "
            f"Valid transitions from {current}: {sorted(valid)}"
        )


class TaskLifecycle:
    """Task state machine management.

    Design invariants:
    - All transitions validated against VALID_TRANSITIONS (T1)
    - Every transition logged to timeline and audit (A4 axiom)
    - Heartbeat updated on every state change (T2)
    - Park/resume preserves full task context (T7)
    - REVIEWING mandatory before COMPLETE (A7 axiom)
    """

    def __init__(self, yaml_store: YamlStore, domain: str = "meta"):
        self.yaml_store = yaml_store
        self.domain = domain
        self._tasks_base = f"instances/{domain}/state/tasks"

    def create(
        self,
        title: str,
        description: str,
        origin: TaskOrigin,
        priority: str = "medium",
        rationale: str = "",
    ) -> Task:
        """Create task in INTAKE state."""
        task = Task(
            id=generate_id("task"),
            created_at=datetime.now(timezone.utc),
            status=TaskStatus.INTAKE,
            title=title,
            description=description,
            origin=origin,
            rationale=rationale,
            priority=priority,
            timeline=[
                TaskTimelineEntry(
                    time=datetime.now(timezone.utc),
                    event="created",
                    actor=origin.source,
                    detail=f"Task created: {title}",
                )
            ],
        )
        self.yaml_store.write(
            f"{self._tasks_base}/active/{task.id}.yaml", task
        )
        return task

    def transition(
        self,
        task_id: str,
        new_status: TaskStatus,
        actor: str,
        detail: str,
    ) -> Task:
        """Transition task state. Validates against VALID_TRANSITIONS."""
        task = self._load_task(task_id)
        current = TaskStatus(task.status)

        # Validate transition (T1)
        valid_next = VALID_TRANSITIONS.get(current, set())
        if new_status not in valid_next:
            raise InvalidTransitionError(task_id, current, new_status)

        # Update task
        task.status = new_status
        task.updated_at = datetime.now(timezone.utc)
        task.timeline.append(
            TaskTimelineEntry(
                time=datetime.now(timezone.utc),
                event=f"transition:{current}→{new_status}",
                actor=actor,
                detail=detail,
            )
        )

        # Move file to appropriate directory
        old_dir = self._status_dir(current)
        new_dir = self._status_dir(new_status)

        if old_dir != new_dir:
            # Write to new location first, then remove old (crash-safe order)
            old_path = f"{self._tasks_base}/{old_dir}/{task_id}.yaml"
            new_path = f"{self._tasks_base}/{new_dir}/{task_id}.yaml"
            self.yaml_store.write(new_path, task)
            # Clean up old file — tolerate missing (crash recovery: new was written but old wasn't deleted)
            try:
                old_full = self.yaml_store._resolve(old_path)
                if old_full.exists():
                    old_full.unlink()
            except OSError as e:
                logging.getLogger("uagents.task_lifecycle").warning(
                    f"Failed to clean up old task file {old_path}: {e} "
                    f"(task was successfully moved to {new_path})"
                )
        else:
            self.yaml_store.write(
                f"{self._tasks_base}/{new_dir}/{task_id}.yaml", task
            )

        return task

    def park(self, task_id: str, reason: str, actor: str) -> Task:
        """Park a task (shorthand for transition to PARKED)."""
        task = self._load_task(task_id)
        return self.transition(task_id, TaskStatus.PARKED, actor, f"Parked: {reason}")

    def resume(self, task_id: str, actor: str) -> Task:
        """Resume a parked task back to PLANNING."""
        return self.transition(
            task_id, TaskStatus.PLANNING, actor, "Resumed from parked"
        )

    def get_active(self) -> list[Task]:
        """List all active (non-parked, non-completed) tasks."""
        return self._list_tasks_in("active")

    def get_parked(self) -> list[Task]:
        """List all parked tasks."""
        return self._list_tasks_in("parked")

    def get_focus(self) -> str | None:
        """Get the currently focused task ID."""
        try:
            data = self.yaml_store.read_raw(f"{self._tasks_base}/focus.yaml")
            return data.get("focus_task_id")
        except (FileNotFoundError, ValueError):
            return None

    def set_focus(self, task_id: str) -> None:
        """Set the focused task."""
        self.yaml_store.write_raw(
            f"{self._tasks_base}/focus.yaml",
            {"focus_task_id": task_id},
        )

    def _load_task(self, task_id: str) -> Task:
        """Load task from active, parked, or completed directories."""
        for subdir in ["active", "parked", "completed"]:
            path = f"{self._tasks_base}/{subdir}/{task_id}.yaml"
            if self.yaml_store.exists(path):
                return self.yaml_store.read(path, Task)
        raise FileNotFoundError(f"Task not found: {task_id}")

    def _list_tasks_in(self, subdir: str) -> list[Task]:
        """List all tasks in a subdirectory."""
        dir_path = f"{self._tasks_base}/{subdir}"
        tasks: list[Task] = []
        try:
            for name in self.yaml_store.list_dir(dir_path):
                if name.endswith(".yaml"):
                    tasks.append(
                        self.yaml_store.read(f"{dir_path}/{name}", Task)
                    )
        except (FileNotFoundError, NotADirectoryError):
            pass
        return tasks

    # --- Phase 1 enhancements: team-aware parking & resume ---

    def park_with_team(
        self, task_id: str, reason: str, actor: str,
        team_manager: "TeamManager",
    ) -> Task:
        """Park a task and manage its team.

        Steps:
        1. Validate park transition is legal BEFORE any side effects
        2. Snapshot team state for resume
        3. Dissolve team (despawn agents)
        4. Park the task (PARKED status)
        5. Update focus tracking
        """
        task = self._load_task(task_id)

        # Validate transition is legal BEFORE dissolving team
        from ..models.task import VALID_TRANSITIONS, TaskStatus
        current = TaskStatus(task.status)
        if TaskStatus.PARKED not in VALID_TRANSITIONS.get(current, set()):
            from .task_lifecycle import InvalidTransitionError
            raise InvalidTransitionError(task_id, current, TaskStatus.PARKED)

        # Snapshot team state before dissolving
        if task.team_id:
            team = team_manager._load_team(task.team_id)
            team_snapshot = team.model_dump()
            self.yaml_store.write_raw(
                f"{team_manager._teams_base}/{task.team_id}/snapshot.yaml",
                team_snapshot,
            )
            team_manager.dissolve_team(task.team_id, f"Task parked: {reason}")

        # Park the task (transition already validated above)
        task = self.park(task_id, reason, actor)

        # Update focus if this was the focused task
        focus = self.get_focus()
        if focus == task_id:
            self._clear_focus()

        return task

    def resume_with_team(
        self, task_id: str, actor: str,
        team_manager: "TeamManager",
        topology_router: "TopologyRouter",
        domain_config: "DomainConfig",
    ) -> "tuple[Task, Team | None]":
        """Resume a parked task, potentially recreating its team.

        Steps:
        1. Resume the task (back to PLANNING)
        2. If task had a team: re-analyze and create new team
        3. Set as focused task

        Returns (resumed_task, new_team_or_None)
        """
        task = self.resume(task_id, actor)
        self.set_focus(task_id)

        # Check if task had a team (snapshot stored under teams dir)
        new_team = None
        old_team_id = task.team_id
        snapshot_path = f"{team_manager._teams_base}/{old_team_id}/snapshot.yaml" if old_team_id else None
        try:
            if not snapshot_path:
                raise FileNotFoundError("No team to restore")
            self.yaml_store.read_raw(snapshot_path)
            # Re-analyze and create new team
            analysis = topology_router.analyze(task)
            routing = topology_router.route(analysis)
            new_team = team_manager.create_team(task, routing, domain_config)
            task.team_id = new_team.id
        except FileNotFoundError:
            logging.getLogger("uagents.task_lifecycle").info(
                f"No team snapshot found for task {task_id} — resuming as solo task"
            )

        # Persist updated task (team_id change must reach disk)
        for subdir in ("active", "parked", "completed"):
            path = f"{self._tasks_base}/{subdir}/{task_id}.yaml"
            if self.yaml_store.exists(path):
                self.yaml_store.write(path, task)
                break

        return task, new_team

    def list_parked_with_details(self) -> list[dict]:
        """List parked tasks with staleness information."""
        parked = self.get_parked()
        details = []
        now = datetime.now(timezone.utc)
        for task in parked:
            # Find when it was parked (last timeline entry)
            # Timeline entries use event format "transition:X→Y"
            parked_at = None
            for entry in reversed(task.timeline):
                if f"\u2192{TaskStatus.PARKED.value}" in entry.event:
                    parked_at = entry.time
                    break

            staleness_hours = 0.0
            if parked_at:
                staleness_hours = (now - parked_at).total_seconds() / 3600

            details.append({
                "task": task,
                "parked_at": parked_at,
                "staleness_hours": round(staleness_hours, 1),
                "had_team": task.team_id is not None,
            })
        return details

    def _clear_focus(self) -> None:
        """Clear the focus file when task is parked.

        Phase 0 focus.yaml uses {"focus_task_id": ...} format.
        Must NOT silently swallow errors -- log warning instead (fail-loud policy).
        """
        focus_path = f"{self._tasks_base}/focus.yaml"
        try:
            self.yaml_store.write_raw(focus_path, {"focus_task_id": None})
        except Exception as e:
            logging.getLogger("uagents.task_lifecycle").warning(
                f"Failed to clear focus file at {focus_path}: {e}"
            )

    # Priority string to numeric value for sorting
    _PRIORITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    def suggest_resume(self) -> str | None:
        """Suggest which parked task to resume based on priority and staleness.

        Priority order:
        1. Highest priority parked task
        2. Among equal priority: stalest task
        """
        parked = self.list_parked_with_details()
        if not parked:
            return None

        # Sort by priority (desc), then staleness (desc)
        # Use numeric priority mapping since alphabetical order doesn't match semantic order
        parked.sort(
            key=lambda d: (
                self._PRIORITY_ORDER.get(d["task"].priority, 1),
                d["staleness_hours"],
            ),
            reverse=True,
        )
        return parked[0]["task"].id

    @staticmethod
    def _status_dir(status: TaskStatus) -> str:
        """Map task status to filesystem directory."""
        if status in (TaskStatus.COMPLETE, TaskStatus.ARCHIVED):
            return "completed"
        if status == TaskStatus.PARKED:
            return "parked"
        return "active"
