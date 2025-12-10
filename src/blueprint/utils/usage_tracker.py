"""Usage tracking utilities for LLM calls with quota enforcement."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, MutableMapping, Optional


class QuotaExceededError(Exception):
    """Raised when a quota threshold is exceeded."""


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


@dataclass
class UsageStats:
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    by_backend: Dict[str, dict] = field(default_factory=dict)

    def add(self, backend: str, usage: UsageRecord) -> None:
        self.total_requests += 1
        self.total_tokens += usage.total_tokens
        self.total_cost += usage.cost
        if backend not in self.by_backend:
            self.by_backend[backend] = {"requests": 0, "tokens": 0, "cost": 0.0}
        self.by_backend[backend]["requests"] += 1
        self.by_backend[backend]["tokens"] += usage.total_tokens
        self.by_backend[backend]["cost"] += usage.cost


class UsageTracker:
    """Tracks usage metrics across sessions and tasks."""

    def __init__(
        self,
        feature_dir: Path | None = None,
        pricing: Optional[MutableMapping[str, MutableMapping[str, float]]] = None,
        max_cost: Optional[float] = None,
        max_tokens_per_request: Optional[int] = None,
        max_cost_hourly: Optional[float] = None,
        max_cost_daily: Optional[float] = None,
    ) -> None:
        self.feature_dir = feature_dir
        self.records: List[UsageRecord] = []
        # pricing map: provider -> model -> (input_rate_per_1k, output_rate_per_1k)
        self.pricing: MutableMapping[str, MutableMapping[str, float]] = pricing or {}
        self.max_cost = max_cost
        self.max_tokens_per_request = max_tokens_per_request
        self.max_cost_hourly = max_cost_hourly
        self.max_cost_daily = max_cost_daily

        self.stats = UsageStats()
        self.hourly_stats: deque[tuple[datetime, UsageRecord]] = deque()
        self.daily_stats: deque[tuple[datetime, UsageRecord]] = deque()

    def record_usage(self, provider: str, model: str, usage: Optional[MutableMapping[str, float] | object]) -> None:
        """Store a usage record; cost is estimated if pricing is available."""
        prompt_tokens = self._read_field(usage, "prompt_tokens")
        completion_tokens = self._read_field(usage, "completion_tokens")
        total_tokens = self._read_field(usage, "total_tokens") or prompt_tokens + completion_tokens
        estimated_cost = self._estimate_cost(provider, model, prompt_tokens, completion_tokens)

        if self.max_tokens_per_request and total_tokens > self.max_tokens_per_request:
            raise QuotaExceededError(
                f"Request exceeded max tokens: {total_tokens} > {self.max_tokens_per_request}"
            )

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
        self.stats.add(provider, record)

        now = datetime.now()
        self.hourly_stats.append((now, record))
        self.daily_stats.append((now, record))
        self._cleanup_windows()

        if self.max_cost is not None and self.get_stats().get("cost", 0.0) > self.max_cost:
            raise QuotaExceededError(
                f"Total cost exceeded limit: ${self.get_stats()['cost']:.2f} / ${self.max_cost:.2f}"
            )

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

    def get_aggregate_usage(self) -> UsageStats:
        """Return aggregate usage snapshot."""
        return self.stats

    def check_quotas(self, backend: str) -> None:
        """Check hourly/daily quotas."""
        if self.max_cost_hourly is not None:
            hourly_cost = self._get_cost_in_window(self.hourly_stats)
            if hourly_cost >= self.max_cost_hourly:
                raise QuotaExceededError(
                    f"Hourly quota exceeded: ${hourly_cost:.2f} / ${self.max_cost_hourly:.2f}"
                )
        if self.max_cost_daily is not None:
            daily_cost = self._get_cost_in_window(self.daily_stats)
            if daily_cost >= self.max_cost_daily:
                raise QuotaExceededError(
                    f"Daily quota exceeded: ${daily_cost:.2f} / ${self.max_cost_daily:.2f}"
                )

    def reset(self) -> None:
        """Clear recorded usage."""
        self.records.clear()
        self.stats = UsageStats()
        self.hourly_stats.clear()
        self.daily_stats.clear()

    def set_limits(self, *, max_cost: Optional[float] = None, max_tokens_per_request: Optional[int] = None) -> None:
        """Configure quota limits."""
        self.max_cost = max_cost
        self.max_tokens_per_request = max_tokens_per_request

    def set_pricing(self, provider: str, model: str, input_per_1k: float, output_per_1k: Optional[float] = None) -> None:
        """Configure pricing for cost estimation."""
        if provider not in self.pricing:
            self.pricing[provider] = {}
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

    def check_request_budget(self, estimated_tokens: int, estimated_cost: Optional[float] = None) -> None:
        """Validate a request against configured quotas."""
        if self.max_tokens_per_request and estimated_tokens > self.max_tokens_per_request:
            raise QuotaExceededError(
                f"Estimated tokens {estimated_tokens} exceed limit {self.max_tokens_per_request}"
            )
        if self.max_cost is not None and estimated_cost is not None and estimated_cost > self.max_cost:
            raise QuotaExceededError(
                f"Estimated cost ${estimated_cost:.2f} would exceed limit ${self.max_cost:.2f}"
            )

    def _cleanup_windows(self) -> None:
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        while self.hourly_stats and self.hourly_stats[0][0] < hour_ago:
            self.hourly_stats.popleft()
        while self.daily_stats and self.daily_stats[0][0] < day_ago:
            self.daily_stats.popleft()

    def _get_cost_in_window(self, window: deque[tuple[datetime, UsageRecord]]) -> float:
        return sum(rec.cost for _, rec in window)
