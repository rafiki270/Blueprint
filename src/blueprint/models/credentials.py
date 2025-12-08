"""Credential loading for provider adapters."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .base import Provider


class CredentialsManager:
    """Loads provider credentials from env or ~/.config/blueprint/credentials.json."""

    def __init__(self) -> None:
        self.credentials_path = self._resolve_path()
        self._cache = self._load_file()

    def get_api_key(self, provider: Provider) -> Optional[str]:
        """Return API key for provider, preferring env var overrides."""
        env_var = {
            Provider.OPENAI: "OPENAI_API_KEY",
            Provider.CLAUDE: "ANTHROPIC_API_KEY",
            Provider.GEMINI: "GEMINI_API_KEY",
        }.get(provider)

        # Gemini also respects GOOGLE_GENERATIVE_AI_API_KEY
        if provider == Provider.GEMINI:
            env_var = "GEMINI_API_KEY" if os.getenv("GEMINI_API_KEY") else "GOOGLE_GENERATIVE_AI_API_KEY"

        if env_var and os.getenv(env_var):
            return os.getenv(env_var)

        provider_key = provider.value
        provider_config = self._cache.get("providers", {}).get(provider_key, {})
        key_fields = ["api_key", "token", "key"]
        for field in key_fields:
            value = provider_config.get(field)
            if value:
                return value
        return None

    def get_base_url(self, provider: Provider, default: Optional[str] = None) -> Optional[str]:
        """Return base URL for provider if configured."""
        if provider == Provider.OLLAMA and os.getenv("OLLAMA_HOST"):
            return os.getenv("OLLAMA_HOST")

        provider_config = self._cache.get("providers", {}).get(provider.value, {})
        return provider_config.get("base_url", default)

    def set_provider(self, provider: Provider, data: Dict[str, Any]) -> None:
        """Persist credentials for a provider."""
        providers = self._cache.setdefault("providers", {})
        providers[provider.value] = data
        self._write_file()

    def _resolve_path(self) -> Path:
        if os.name == "nt":
            root = Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming")
            config_dir = root / "blueprint"
        else:
            config_dir = Path.home() / ".config" / "blueprint"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "credentials.json"

    def _load_file(self) -> Dict[str, Any]:
        if not self.credentials_path.exists():
            return {"version": "1.0", "providers": {}}

        try:
            raw = self.credentials_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            return {"version": "1.0", "providers": {}}
        return {"version": "1.0", "providers": {}}

    def _write_file(self) -> None:
        payload = json.dumps(self._cache, indent=2)
        self.credentials_path.write_text(payload, encoding="utf-8")
        try:
            # Restrict permissions on POSIX systems.
            self.credentials_path.chmod(0o600)
        except (OSError, NotImplementedError):
            pass
