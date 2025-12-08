"""Task lifecycle management."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from .persistence import Persistence


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class TaskType(Enum):
    CODE = "code"
    BOILERPLATE = "boilerplate"
    REVIEW = "review"
    ARCHITECTURE = "architecture"


class Task:
    """Represents a single task."""

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        type: TaskType,
        status: TaskStatus = TaskStatus.PENDING,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> None:
        self.id = id
        self.title = title
        self.description = description
        self.type = type
        self.status = status
        timestamp = datetime.utcnow().isoformat()
        self.created_at = created_at or timestamp
        self.updated_at = updated_at or timestamp

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.type.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: Dict) -> "Task":
        """Create from dictionary."""
        return Task(
            id=data["id"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            type=TaskType(data.get("type", TaskType.CODE.value)),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


class TaskManager:
    """Manages task lifecycle."""

    def __init__(self, feature_dir: Path) -> None:
        self.feature_dir = feature_dir
        self.tasks_file = feature_dir / "tasks.json"
        self.tasks_status_file = feature_dir / "tasks_status.json"
        self.tasks: List[Task] = []
        self.load()

    def load(self) -> None:
        """Load tasks from disk."""
        data = Persistence.load_json(self.tasks_file)
        tasks_data = data.get("tasks") if isinstance(data, dict) else None
        tasks_status = Persistence.load_json(self.tasks_status_file)

        self.tasks = []
        if isinstance(tasks_data, list):
            for entry in tasks_data:
                if isinstance(entry, dict) and entry.get("id"):
                    task = Task.from_dict(entry)
                    # If statuses file overrides, prefer it.
                    status_override = tasks_status.get(task.id) if isinstance(tasks_status, dict) else None
                    if status_override:
                        task.status = TaskStatus(status_override)
                    self.tasks.append(task)

    def save(self) -> None:
        """Save tasks to disk."""
        data = {"tasks": [task.to_dict() for task in self.tasks]}
        Persistence.save_json(self.tasks_file, data)
        status_map = {task.id: task.status.value for task in self.tasks}
        Persistence.save_json(self.tasks_status_file, status_map)

    def _next_id(self) -> str:
        """Generate a new unique task id."""
        existing_numbers = []
        for task in self.tasks:
            if task.id.startswith("task-"):
                try:
                    existing_numbers.append(int(task.id.split("task-")[1]))
                except (IndexError, ValueError):
                    continue
        next_num = max(existing_numbers, default=0) + 1
        return f"task-{next_num}"

    def create(self, title: str, description: str, type: TaskType) -> Task:
        """Create a new task."""
        task_id = self._next_id()
        task = Task(id=task_id, title=title, description=description, type=type)
        self.tasks.append(task)
        self.save()
        return task

    def get(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return next((task for task in self.tasks if task.id == task_id), None)

    def delete(self, task_id: str) -> bool:
        """Delete a task."""
        task = self.get(task_id)
        if not task:
            return False
        self.tasks = [t for t in self.tasks if t.id != task_id]
        self.save()
        return True

    def _update_status(self, task_id: str, status: TaskStatus) -> bool:
        task = self.get(task_id)
        if not task:
            return False
        task.status = status
        task.updated_at = datetime.utcnow().isoformat()
        self.save()
        return True

    def mark_done(self, task_id: str) -> bool:
        """Mark task as completed."""
        return self._update_status(task_id, TaskStatus.COMPLETED)

    def mark_redo(self, task_id: str) -> bool:
        """Mark task as pending again."""
        return self._update_status(task_id, TaskStatus.PENDING)

    def mark_in_progress(self, task_id: str) -> bool:
        """Mark task as in progress."""
        return self._update_status(task_id, TaskStatus.IN_PROGRESS)

    def mark_blocked(self, task_id: str) -> bool:
        """Mark task as blocked."""
        return self._update_status(task_id, TaskStatus.BLOCKED)

    def mark_skipped(self, task_id: str) -> bool:
        """Mark task as skipped."""
        return self._update_status(task_id, TaskStatus.SKIPPED)

    def get_next(self) -> Optional[Task]:
        """Get next incomplete task."""
        for task in self.tasks:
            if task.status not in (TaskStatus.COMPLETED, TaskStatus.SKIPPED):
                return task
        return None

    def get_missing(self) -> List[Task]:
        """Get all incomplete tasks."""
        return [task for task in self.tasks if task.status not in (TaskStatus.COMPLETED, TaskStatus.SKIPPED)]

    def list_all(self) -> List[Task]:
        """List all tasks."""
        return list(self.tasks)
