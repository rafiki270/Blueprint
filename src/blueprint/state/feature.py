"""Feature state management."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .persistence import Persistence


class Feature:
    """Manages feature state and files."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.base_dir = Path.home() / ".blueprint" / name
        self.spec_file = self.base_dir / "spec.md"
        self.tasks_file = self.base_dir / "tasks.json"
        self.tasks_status_file = self.base_dir / "tasks_status.json"
        self.progress_file = self.base_dir / "progress.json"
        self.usage_file = self.base_dir / "usage.json"
        self.current_task_file = self.base_dir / "current_task.txt"
        self.logs_dir = self.base_dir / "logs"
        self.partial_dir = self.base_dir / "partial"
        self.summaries_dir = self.base_dir / "summaries"

    def initialize(self) -> None:
        """Create feature directory structure and default files."""
        Persistence.ensure_dir(self.base_dir)
        for directory in (self.logs_dir, self.partial_dir, self.summaries_dir):
            Persistence.ensure_dir(directory)

        # Initialize common JSON files if missing.
        if not self.tasks_file.exists():
            Persistence.save_json(self.tasks_file, {"tasks": []})
        if not self.tasks_status_file.exists():
            Persistence.save_json(self.tasks_status_file, {})
        if not self.progress_file.exists():
            Persistence.save_json(self.progress_file, {})
        if not self.usage_file.exists():
            Persistence.save_json(self.usage_file, {})
        if not self.current_task_file.exists():
            self.current_task_file.touch()

    def exists(self) -> bool:
        """Check if feature exists."""
        return self.base_dir.exists()

    def save_spec(self, content: str) -> None:
        """Save specification markdown."""
        Persistence.ensure_dir(self.base_dir)
        self.spec_file.write_text(content, encoding="utf-8")

    def load_spec(self) -> Optional[str]:
        """Load specification markdown."""
        if not self.spec_file.exists():
            return None
        return self.spec_file.read_text(encoding="utf-8")

    def save_tasks(self, tasks: List[Dict]) -> None:
        """Save tasks.json and derived task statuses."""
        Persistence.save_json(self.tasks_file, {"tasks": tasks})
        status_map = {task.get("id"): task.get("status") for task in tasks if task.get("id")}
        Persistence.save_json(self.tasks_status_file, status_map)

    def load_tasks(self) -> List[Dict]:
        """Load tasks.json."""
        data = Persistence.load_json(self.tasks_file)
        tasks = data.get("tasks") if isinstance(data, dict) else None
        return tasks or []

    @staticmethod
    def list_features() -> List[str]:
        """List all available features."""
        base_dir = Path.home() / ".blueprint"
        if not base_dir.exists():
            return []
        return sorted([p.name for p in base_dir.iterdir() if p.is_dir()])

    @staticmethod
    def find_active_features() -> List[str]:
        """Find features with incomplete tasks."""
        active: List[str] = []
        for name in Feature.list_features():
            base_dir = Path.home() / ".blueprint" / name
            tasks_status_file = base_dir / "tasks_status.json"
            tasks_file = base_dir / "tasks.json"
            statuses: Dict[str, str] = {}
            if tasks_status_file.exists():
                raw_status = Persistence.load_json(tasks_status_file)
                if isinstance(raw_status, dict):
                    statuses = raw_status
            if not statuses and tasks_file.exists():
                data = Persistence.load_json(tasks_file)
                if isinstance(data, dict):
                    tasks = data.get("tasks", [])
                    if isinstance(tasks, list):
                        statuses = {t.get("id"): t.get("status") for t in tasks if isinstance(t, dict)}

            if any(status not in ("completed", "skipped") for status in statuses.values()):
                active.append(name)
        return active
