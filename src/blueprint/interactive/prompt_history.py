"""Per-task prompt history storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List


class PromptHistory:
    """Simple JSON-backed prompt history."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> List[str]:
        """Load prompts from disk."""
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [str(p) for p in data]
        except Exception:
            return []
        return []

    def append(self, prompt: str) -> List[str]:
        """Append a prompt and persist."""
        prompts = self.load()
        prompts.append(prompt)
        self._save(prompts)
        return prompts

    def clear(self) -> None:
        """Remove stored prompts."""
        if self.path.exists():
            self.path.unlink()

    def _save(self, prompts: List[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(prompts, indent=2), encoding="utf-8")
