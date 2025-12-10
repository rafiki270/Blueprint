"""Credential loading for provider adapters using ConfigLoader TOML credentials."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from ..config import ConfigLoader
from .base import Provider


class CredentialsManager:
    """Loads provider credentials from env or ~/.config/blueprint/credentials.toml."""

    def __init__(self, config: Optional[ConfigLoader] = None) -> None:
        self.config = config or ConfigLoader()

    def get_api_key(self, provider: Provider) -> Optional[str]:
        """Return API key for provider, preferring env var overrides."""
        env_var = {
            Provider.OPENAI: "OPENAI_API_KEY",
            Provider.CLAUDE: "ANTHROPIC_API_KEY",
            Provider.GEMINI: "GEMINI_API_KEY",
            Provider.OLLAMA: "OLLAMA_API_KEY",
        }.get(provider)

        # Gemini also respects GOOGLE_GENERATIVE_AI_API_KEY
        if provider == Provider.GEMINI:
            env_var = "GEMINI_API_KEY" if os.getenv("GEMINI_API_KEY") else "GOOGLE_GENERATIVE_AI_API_KEY"

        if env_var and os.getenv(env_var):
            return os.getenv(env_var)

        provider_key = provider.value
        return self.config.get_credential(provider_key, "api_key")

    def get_base_url(self, provider: Provider, default: Optional[str] = None) -> Optional[str]:
        """Return base URL for provider if configured."""
        if provider == Provider.OLLAMA and os.getenv("OLLAMA_HOST"):
            return os.getenv("OLLAMA_HOST")
        provider_key = provider.value
        return self.config.get_credential(provider_key, "base_url") or default

    def set_provider(self, provider: Provider, data: Dict[str, Any]) -> None:
        """Persist credentials for a provider (best-effort)."""
        # ConfigLoader handles credential files; for now, we update in-memory.
        if hasattr(self.config, "credentials"):
            providers = self.config.credentials.setdefault(provider.value, {})
            providers.update(data)
