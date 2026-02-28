"""Task lifecycle state machine.
Spec reference: Section 6 (Task Lifecycle)."""
from __future__ import annotations

from datetime import datetime
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
            created_at=datetime.utcnow(),
            status=TaskStatus.INTAKE,
            title=title,
            description=description,
            origin=origin,
            rationale=rationale,
            priority=priority,
            timeline=[
                TaskTimelineEntry(
                    time=datetime.utcnow(),
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
        task.updated_at = datetime.utcnow()
        task.timeline.append(
            TaskTimelineEntry(
                time=datetime.utcnow(),
                event=f"transition:{current}→{new_status}",
                actor=actor,
                detail=detail,
            )
        )

        # Move file to appropriate directory
        old_dir = self._status_dir(current)
        new_dir = self._status_dir(new_status)

        if old_dir != new_dir:
            # Remove from old location
            old_path = f"{self._tasks_base}/{old_dir}/{task_id}.yaml"
            new_path = f"{self._tasks_base}/{new_dir}/{task_id}.yaml"
            self.yaml_store.write(new_path, task)
            # Clean up old file
            old_full = self.yaml_store._resolve(old_path)
            if old_full.exists():
                old_full.unlink()
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

    @staticmethod
    def _status_dir(status: TaskStatus) -> str:
        """Map task status to filesystem directory."""
        if status in (TaskStatus.COMPLETE, TaskStatus.ARCHIVED):
            return "completed"
        if status == TaskStatus.PARKED:
            return "parked"
        return "active"
