"""Lightweight prompt/response cache."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Optional, Tuple


class CacheManager:
    """In-memory TTL cache for LLM responses."""

    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 512) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._store: Dict[str, Tuple[float, Any]] = {}

    def get_cache_key(self, payload: Dict[str, Any]) -> str:
        """Hash a request payload to derive a cache key."""
        data = repr(payload).encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached entry if valid."""
        entry = self._store.get(key)
        if not entry:
            return None
        ts, value = entry
        if (time.time() - ts) > self.ttl_seconds:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        """Store a cache entry, evicting oldest if at capacity."""
        if len(self._store) >= self.max_entries:
            # Evict oldest
            oldest_key = next(iter(self._store.keys()))
            self._store.pop(oldest_key, None)
        self._store[key] = (time.time(), value)

    def clear(self) -> None:
        """Clear cache entries."""
        self._store.clear()
