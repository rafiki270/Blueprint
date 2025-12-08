"""Helpers for atomic JSON file operations."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict


class Persistence:
    """Handles atomic JSON file operations."""

    @staticmethod
    def load_json(file_path: Path) -> Dict[str, Any]:
        """Load JSON from file, return {} if not found or invalid."""
        if not file_path.exists():
            return {}

        try:
            with file_path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def save_json(file_path: Path, data: Dict[str, Any]) -> None:
        """Atomically save JSON to file."""
        Persistence.ensure_dir(file_path.parent)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=file_path.parent, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as fp:
                json.dump(data, fp, indent=2)
                fp.flush()
                os.fsync(fp.fileno())
            shutil.move(tmp_path, file_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @staticmethod
    def ensure_dir(dir_path: Path) -> None:
        """Create directory if it doesn't exist."""
        dir_path.mkdir(parents=True, exist_ok=True)
