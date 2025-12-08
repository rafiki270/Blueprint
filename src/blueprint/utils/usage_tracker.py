"""Placeholder usage tracker for interactive UI."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List


class UsageTracker:
    """Tracks usage metrics (stub for now)."""

    def __init__(self, feature_dir: Path) -> None:
        self.feature_dir = feature_dir

    def get_today_usage(self) -> Dict:
        return {
            "claude": 0,
            "claude_tokens": 0,
            "gemini_input_tokens": 0,
            "gemini_output_tokens": 0,
            "deepseek": 0,
            "codex": 0,
        }

    def get_7day_trend(self) -> Dict[str, Dict]:
        return {
            "claude": {"total_calls": 0, "trend": "—"},
            "gemini": {"total_calls": 0, "trend": "—"},
            "deepseek": {"total_calls": 0, "trend": "—"},
            "codex": {"total_calls": 0, "trend": "—"},
        }

    def get_routing_suggestions(self) -> List[str]:
        return []
