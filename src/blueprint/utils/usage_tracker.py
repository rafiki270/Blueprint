"""Usage tracking utilities for LLM calls."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, MutableMapping, Optional


@dataclass
class UsageRecord:
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class UsageTracker:
    """Tracks usage metrics across sessions and tasks."""

    def __init__(self, feature_dir: Path | None = None, pricing: Optional[MutableMapping[str, MutableMapping[str, float]]] = None) -> None:
        self.feature_dir = feature_dir
        self.records: List[UsageRecord] = []
        # pricing map: provider -> model -> {"input": rate_per_1k, "output": rate_per_1k}
        self.pricing: MutableMapping[str, MutableMapping[str, float]] = pricing or {}

    def record_usage(self, provider: str, model: str, usage: Optional[MutableMapping[str, float] | object]) -> None:
        """Store a usage record; cost is estimated if pricing is available."""
        prompt_tokens = self._read_field(usage, "prompt_tokens")
        completion_tokens = self._read_field(usage, "completion_tokens")
        total_tokens = self._read_field(usage, "total_tokens") or prompt_tokens + completion_tokens
        estimated_cost = self._estimate_cost(provider, model, prompt_tokens, completion_tokens)

        record = UsageRecord(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=estimated_cost,
            success=usage is not None,
        )
        self.records.append(record)

    def get_stats(self, provider: Optional[str] = None, model: Optional[str] = None) -> Dict[str, float]:
        """Return aggregated stats filtered by provider/model."""
        filtered = [
            r
            for r in self.records
            if (provider is None or r.provider == provider) and (model is None or r.model == model)
        ]
        stats = defaultdict(float)
        for r in filtered:
            stats["requests"] += 1
            stats["prompt_tokens"] += r.prompt_tokens
            stats["completion_tokens"] += r.completion_tokens
            stats["total_tokens"] += r.total_tokens
            stats["cost"] += r.cost
            if not r.success:
                stats["errors"] += 1
        return dict(stats)

    def reset(self) -> None:
        """Clear recorded usage."""
        self.records.clear()

    def set_pricing(self, provider: str, model: str, input_per_1k: float, output_per_1k: Optional[float] = None) -> None:
        """Configure pricing for cost estimation."""
        if provider not in self.pricing:
            self.pricing[provider] = {}
        # store blended rate; if output not provided, use input rate
        self.pricing[provider][model] = (input_per_1k, output_per_1k if output_per_1k is not None else input_per_1k)

    # --- Legacy helpers used by UI ---
    def get_today_usage(self) -> Dict:
        stats = self.get_stats()
        return {
            "claude": int(stats.get("requests", 0)),
            "claude_tokens": int(stats.get("total_tokens", 0)),
            "gemini_input_tokens": int(stats.get("prompt_tokens", 0)),
            "gemini_output_tokens": int(stats.get("completion_tokens", 0)),
            "deepseek": int(stats.get("requests", 0)),
            "codex": int(stats.get("requests", 0)),
        }

    def get_7day_trend(self) -> Dict[str, Dict]:
        # This implementation is lightweight: it uses aggregate counts without bucketing by day.
        stats = self.get_stats()
        total_calls = int(stats.get("requests", 0))
        return {
            "claude": {"total_calls": total_calls, "trend": "—"},
            "gemini": {"total_calls": total_calls, "trend": "—"},
            "deepseek": {"total_calls": total_calls, "trend": "—"},
            "codex": {"total_calls": total_calls, "trend": "—"},
        }

    def get_routing_suggestions(self) -> List[str]:
        suggestions: List[str] = []
        stats = self.get_stats()
        if stats.get("errors", 0) > 3:
            suggestions.append("High error rate detected; consider switching to a fallback provider.")
        return suggestions

    # --- Internals ---
    def _estimate_cost(self, provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = self.pricing.get(provider, {}).get(model)
        if not pricing:
            return 0.0
        input_rate, output_rate = pricing
        return (prompt_tokens * input_rate + completion_tokens * output_rate) / 1000.0

    def _read_field(self, usage: Optional[object], field: str) -> int:
        if usage is None:
            return 0
        if isinstance(usage, dict):
            return int(usage.get(field) or 0)
        return int(getattr(usage, field, 0) or 0)
