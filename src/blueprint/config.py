"""Settings management for Blueprint."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict


class Config:
    """Manages Blueprint settings."""

    DEFAULT_SETTINGS: Dict[str, Any] = {
        "local_model": "deepseek-coder:14b",
        "max_chars_local_model": 20000,
        "ollama_unavailable_warning": True,
        "cli_commands": {
            "claude": "claude",
            "gemini": "gemini",
            "ollama": "ollama",
            "codex": "codex",
        },
    }

    def __init__(self) -> None:
        self.config_dir = Path.home() / ".blueprint"
        self.config_file = self.config_dir / "settings.json"
        self.settings: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load settings from file or create defaults."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        settings = copy.deepcopy(self.DEFAULT_SETTINGS)

        if not self.config_file.exists():
            return settings

        try:
            with self.config_file.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            if isinstance(data, dict):
                # Merge saved values over defaults.
                settings.update(data)
        except (OSError, json.JSONDecodeError):
            # Corrupted or unreadable file; fall back to defaults.
            return settings

        return settings

    def save(self) -> None:
        """Save current settings to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with self.config_file.open("w", encoding="utf-8") as fp:
            json.dump(self.settings, fp, indent=2)

    def get(self, key: str, default: Any | None = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value and persist."""
        self.settings[key] = value
        self.save()
