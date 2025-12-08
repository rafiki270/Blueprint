"""Model routing utilities for provider adapters."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional

from ..config import Config
from .base import BaseAdapter, Provider
from .claude import ClaudeAdapter
from .codex import OpenAIAdapter
from .credentials import CredentialsManager
from .deepseek import OllamaAdapter
from .gemini import GeminiAdapter


class ModelRole(Enum):
    ARCHITECT = "architecture"
    CODER = "code"
    BOILERPLATE = "boilerplate"
    REVIEWER = "review"
    PARSER = "parser"


class ModelRouter:
    """Route tasks to the most suitable provider."""

    def __init__(self, config: Config) -> None:
        self.config = config
        creds = CredentialsManager()

        self.claude = ClaudeAdapter(credentials=creds, default_model=config.get("claude_model", "claude-3-5-sonnet-20241022"))
        self.gemini = GeminiAdapter(credentials=creds, default_model=config.get("gemini_model", "gemini-2.0-flash"))
        self.ollama = OllamaAdapter(credentials=creds, default_model=config.get("local_model", "deepseek-coder:latest"))
        self.openai = OpenAIAdapter(credentials=creds, default_model=config.get("openai_model", "gpt-4o"))

        self.max_chars_local = config.get("max_chars_local_model", 20000)
        self._health_cache: Dict[Provider, str] = {}

    async def check_availability(self) -> None:
        """Run lightweight health checks."""
        for adapter in (self.ollama, self.claude, self.gemini, self.openai):
            try:
                health = await adapter.check_health()
                self._health_cache[adapter.provider] = health.status
            except Exception:
                self._health_cache[adapter.provider] = "down"

    async def route(self, role: ModelRole, content_size: int = 0) -> BaseAdapter:
        """Route to an adapter based on role and context size."""
        if role == ModelRole.ARCHITECT:
            return self.claude
        if role == ModelRole.REVIEWER:
            return self.openai
        if role == ModelRole.BOILERPLATE:
            return self.gemini
        if role == ModelRole.PARSER:
            if content_size > self.max_chars_local:
                return self.gemini
            if await self._is_ollama_available():
                return self.ollama
            return self.gemini

        # Default coder flow
        if await self._is_ollama_available() and content_size <= self.max_chars_local:
            return self.ollama
        return self.gemini

    def get_routing_stats(self) -> dict:
        """Return recent availability for display."""
        return {
            "ollama_available": self._health_cache.get(Provider.OLLAMA) == "healthy",
            "max_chars_local": self.max_chars_local,
            "models": {
                "claude": self._health_cache.get(Provider.CLAUDE, "unknown"),
                "gemini": self._health_cache.get(Provider.GEMINI, "unknown"),
                "ollama": self._health_cache.get(Provider.OLLAMA, "unknown"),
                "openai": self._health_cache.get(Provider.OPENAI, "unknown"),
            },
        }

    async def _is_ollama_available(self) -> bool:
        if self._health_cache.get(Provider.OLLAMA) == "healthy":
            return True
        try:
            health = await self.ollama.check_health()
            self._health_cache[Provider.OLLAMA] = health.status
            return health.status == "healthy"
        except Exception:
            self._health_cache[Provider.OLLAMA] = "down"
            return False
