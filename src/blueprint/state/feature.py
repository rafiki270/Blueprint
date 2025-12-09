"""Feature state management."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .persistence import Persistence


class Feature:
    """Manages feature state and files."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.base_dir = self._base_root() / name
        self.tasks_dir = self.base_dir / "tasks"
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
        for directory in (self.logs_dir, self.partial_dir, self.summaries_dir, self.tasks_dir):
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

    def task_dir(self, task_id: str) -> Path:
        """Directory for a specific task."""
        return self.tasks_dir / task_id

    def task_spec_path(self, task_id: str) -> Path:
        """Spec path for a specific task."""
        return self.task_dir(task_id) / "spec.md"

    def save_task_spec(self, task_id: str, content: str) -> None:
        """Save per-task specification markdown."""
        dir_path = self.task_dir(task_id)
        Persistence.ensure_dir(dir_path)
        (dir_path / "spec.md").write_text(content, encoding="utf-8")

    def load_task_spec(self, task_id: str) -> Optional[str]:
        """Load per-task specification if present."""
        path = self.task_spec_path(task_id)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def task_conversation_path(self, task_id: str) -> Path:
        """Conversation history path for a specific task."""
        return self.task_dir(task_id) / "session-context.json"

    def append_task_conversation(self, task_id: str, role: str, message: str) -> None:
        """Append a message to the task's conversation history (JSONL)."""
        dir_path = self.task_dir(task_id)
        Persistence.ensure_dir(dir_path)
        conv_path = self.task_conversation_path(task_id)

        # Maintain compatibility if existing file is newline-delimited JSON
        entries = self.load_task_conversation_entries(task_id)
        entries.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "role": role,
                "content": message,
            }
        )
        Persistence.save_json(conv_path, {"entries": entries})

    def clear_task_conversation(self, task_id: str) -> None:
        """Clear persisted conversation for a task."""
        dir_path = self.task_dir(task_id)
        Persistence.ensure_dir(dir_path)
        conv_path = self.task_conversation_path(task_id)
        Persistence.save_json(conv_path, {"entries": []})

    def load_task_conversation_entries(self, task_id: str) -> List[Dict[str, str]]:
        """Load conversation as structured entries."""
        conv_path = self.task_conversation_path(task_id)
        if not conv_path.exists():
            return []

        entries: List[Dict[str, str]] = []
        data = Persistence.load_json(conv_path)
        if data and "entries" in data and isinstance(data["entries"], list):
            for item in data["entries"]:
                if isinstance(item, dict) and "role" in item and "content" in item:
                    entries.append(
                        {
                            "timestamp": str(item.get("timestamp", "")),
                            "role": str(item.get("role")),
                            "content": str(item.get("content")),
                        }
                        )
            return entries

        # Legacy fallback: newline-delimited JSON
        if conv_path.exists():
            try:
                raw = conv_path.read_text(encoding="utf-8")
                for line in raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if isinstance(data, dict) and "role" in data and "content" in data:
                            entries.append(
                                {
                                    "timestamp": data.get("timestamp", ""),
                                    "role": str(data.get("role")),
                                    "content": str(data.get("content")),
                                }
                            )
                            continue
                    except json.JSONDecodeError:
                        # Legacy format: [timestamp] role: content
                        if line.startswith("[") and "]" in line and ":" in line:
                            ts_part = line[1 : line.find("]")]
                            remainder = line[line.find("]") + 1 :].strip()
                            if ":" in remainder:
                                role_part, content_part = remainder.split(":", 1)
                                entries.append(
                                    {
                                        "timestamp": ts_part.strip(),
                                        "role": role_part.strip(),
                                        "content": content_part.strip(),
                                    }
                                )
            except Exception:
                return []
        return entries

    def load_task_conversation(self, task_id: str) -> Optional[str]:
        """Load the full conversation history as formatted text."""
        entries = self.load_task_conversation_entries(task_id)
        if not entries:
            return None
        lines = [f"[{e.get('timestamp')}] {e.get('role')}: {e.get('content')}" for e in entries]
        return "\n".join(lines)

    @staticmethod
    def list_features() -> List[str]:
        """List all available features."""
        base_dir = Feature._base_root()
        if not base_dir.exists():
            return []
        return sorted([p.name for p in base_dir.iterdir() if p.is_dir()])

    @staticmethod
    def find_active_features() -> List[str]:
        """Find features with incomplete tasks."""
        active: List[str] = []
        for name in Feature.list_features():
            base_dir = Feature._base_root() / name
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

    @staticmethod
    def _base_root() -> Path:
        """Root folder for per-project state (relative to launch directory)."""
        return Path.cwd() / ".blueprint"
