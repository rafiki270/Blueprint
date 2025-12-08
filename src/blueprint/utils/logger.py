"""Simple task logger placeholder."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..state.tasks import Task


class Logger:
    """Minimal logger that writes task events to feature logs."""

    def __init__(self, feature_dir: Path) -> None:
        self.feature_dir = feature_dir
        self.logs_dir = feature_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _write(self, filename: str, payload: dict) -> None:
        path = self.logs_dir / filename
        entry = {"timestamp": datetime.utcnow().isoformat(), **payload}
        with path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry) + "\n")

    def log_task_start(self, task: Task) -> None:
        self._write("tasks.log", {"event": "start", "task_id": task.id, "title": task.title})

    def log_task_complete(self, task: Task) -> None:
        self._write("tasks.log", {"event": "complete", "task_id": task.id, "title": task.title})

    def log_task_failed(self, task: Task, reason: str) -> None:
        self._write("tasks.log", {"event": "failed", "task_id": task.id, "title": task.title, "reason": reason})
