"""Configuration loader for Blueprint (global + project with TOML-based defaults)."""

from __future__ import annotations

import json
import os
import platform
import stat
from pathlib import Path
from typing import Any, Dict, Optional

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback for Python <3.11
    import tomli as tomllib  # type: ignore


class ConfigLoader:
    """
    Handles configuration loading from multiple sources with priority resolution.

    Priority (highest → lowest):
    1. Command-line arguments (not handled here)
    2. Environment variables (BLUEPRINT_*)
    3. Project config (.blueprint/config.toml)
    4. Global config (~/.config/blueprint/config.toml)
    5. Built-in defaults
    """

    def __init__(self) -> None:
        self.global_dir = self.get_global_config_dir()
        self.project_dir = self.get_project_config_dir()

        self.config: Dict[str, Any] = {}
        self.credentials: Dict[str, Any] = {}
        self.personas: Dict[str, Any] = {}

        self._load_all()

    # ------------------------------------------------------------------ #
    # Public getters
    # ------------------------------------------------------------------ #
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-separated key."""
        keys = key.split(".")
        value: Any = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def get_credential(self, provider: str, key: str) -> Optional[str]:
        """Get credential for a provider."""
        return self.credentials.get(provider, {}).get(key)

    def get_persona(self, name: str) -> Dict[str, Any] | None:
        """Get persona configuration by name."""
        return self.personas.get(name)

    # ------------------------------------------------------------------ #
    # Load/merge helpers
    # ------------------------------------------------------------------ #
    def _load_all(self) -> None:
        """Load all configuration files with proper priority."""
        self._load_global_config()
        self._load_credentials()
        self._load_personas()

        if self.project_dir:
            self._load_project_config()
            self._load_project_personas()

        self._apply_env_overrides()

    def _load_global_config(self) -> None:
        """Load global configuration."""
        config_file = self.global_dir / "config.toml"
        if config_file.exists():
            with open(config_file, "rb") as f:
                self.config = tomllib.load(f)
        else:
            self.config = self._get_default_config()
            self._create_default_config()

    def _load_credentials(self) -> None:
        """Load credentials with security checks."""
        creds_file = self.global_dir / "credentials.toml"

        if not creds_file.exists():
            self._create_default_credentials()
            return

        if platform.system() != "Windows":
            st = creds_file.stat()
            # world/group readable bits disallowed
            if st.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                raise PermissionError(
                    f"Insecure permissions on {creds_file}. Run: chmod 600 {creds_file}"
                )

        with open(creds_file, "rb") as f:
            self.credentials = tomllib.load(f)

    def _load_personas(self) -> None:
        """Load global personas."""
        personas_file = self.global_dir / "personas.toml"
        if personas_file.exists():
            with open(personas_file, "rb") as f:
                self.personas = tomllib.load(f).get("personas", {})
        else:
            self.personas = self._get_default_personas()
            self._create_default_personas()

    def _load_project_config(self) -> None:
        """Load project-specific config and merge with global."""
        config_file = self.project_dir / "config.toml"
        if config_file.exists():
            with open(config_file, "rb") as f:
                project_config = tomllib.load(f)
                self._deep_merge(self.config, project_config)

    def _load_project_personas(self) -> None:
        """Load project-specific personas."""
        personas_file = self.project_dir / "personas.toml"
        if personas_file.exists():
            with open(personas_file, "rb") as f:
                project_personas = tomllib.load(f).get("personas", {})
                self.personas.update(project_personas)

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides (BLUEPRINT_*)."""
        env_prefix = "BLUEPRINT_"
        for key, value in os.environ.items():
            if not key.startswith(env_prefix):
                continue
            config_key = key[len(env_prefix) :].lower().replace("_", ".")
            self._set_nested(self.config, config_key, value)

    # ------------------------------------------------------------------ #
    # Static paths/helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_global_config_dir() -> Path:
        """Get platform-specific global config directory following XDG spec."""
        system = platform.system()
        if system == "Windows":
            base = Path(os.environ.get("APPDATA", "~\\AppData\\Roaming")).expanduser()
        elif system == "Darwin":
            xdg = os.environ.get("XDG_CONFIG_HOME")
            base = Path(xdg) if xdg else Path.home() / ".config"
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
        return base / "blueprint"

    @staticmethod
    def get_project_config_dir() -> Path | None:
        """Find .blueprint directory in current or parent directories."""
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            config_dir = parent / ".blueprint"
            if config_dir.is_dir():
                return config_dir
        return None

    # ------------------------------------------------------------------ #
    # Persistence helpers
    # ------------------------------------------------------------------ #
    def _create_default_config(self) -> None:
        self.global_dir.mkdir(parents=True, exist_ok=True)
        config_file = self.global_dir / "config.toml"
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(self._get_default_config_toml())

    def _create_default_credentials(self) -> None:
        self.global_dir.mkdir(parents=True, exist_ok=True)
        creds_file = self.global_dir / "credentials.toml"
        with open(creds_file, "w", encoding="utf-8") as f:
            f.write("# Add your API credentials here\n\n")
        if platform.system() != "Windows":
            os.chmod(creds_file, 0o600)

    def _create_default_personas(self) -> None:
        self.global_dir.mkdir(parents=True, exist_ok=True)
        personas_file = self.global_dir / "personas.toml"
        with open(personas_file, "w", encoding="utf-8") as f:
            f.write(self._get_default_personas_toml())

    # ------------------------------------------------------------------ #
    # Default content
    # ------------------------------------------------------------------ #
    def _get_default_config(self) -> Dict[str, Any]:
        """Built-in defaults mirroring the design doc."""
        return {
            "general": {
                "version": "1.0.0",
                "log_level": "info",
                "log_file": "~/.config/blueprint/blueprint.log",
            },
            "orchestrator": {
                "default_backend": "claude",
                "fallback_chain": ["claude", "openai", "gemini", "ollama"],
                "auto_switch_on_context_limit": True,
                "streaming_preferred": True,
            },
            "backends": {
                "claude": {
                    "provider": "claude",
                    "model": "claude-sonnet-4.5-20250929",
                    "persona": "general-assistant",
                    "max_context_tokens": 200000,
                    "temperature": 0.7,
                },
                "openai": {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "persona": "code-specialist",
                    "max_context_tokens": 128000,
                    "temperature": 0.7,
                },
                "gemini": {
                    "provider": "gemini",
                    "model": "gemini-2-flash",
                    "persona": "fast-parser",
                    "max_context_tokens": 1000000,
                    "temperature": 0.5,
                },
                "ollama": {
                    "provider": "ollama",
                    "model": "deepseek-coder:latest",
                    "persona": "local-coder",
                    "max_context_tokens": 8192,
                    "temperature": 0.3,
                },
                "opus": {
                    "provider": "opus_self",
                    "model": "claude-opus-4-5-20251101",
                    "persona": "architect",
                    "max_context_tokens": 200000,
                    "temperature": 0.2,
                },
            },
            "context": {
                "session_max_messages": 50,
                "session_max_tokens": 100000,
                "persistent_memory_enabled": True,
                "memory_db_path": "~/.config/blueprint/memory.db",
                "auto_summarize_threshold": 40,
                "summarization_backend": "gemini",
                "enable_distillation": True,
                "distillation_backend": "gemini",
                "distillation_persona": "context-distiller",
                "distillation_trigger_tokens": 50000,
                "distillation_target_tokens": 8000,
            },
            "tools": {
                "permission_mode": "manual",
                "sandbox_enabled": True,
                "timeout_seconds": 300,
                "auto_approve": [
                    "read_file:src/**",
                    "list_directory:**",
                    "search_code:**",
                ],
            },
            "quotas": {
                "max_cost_per_hour": 10.0,
                "max_cost_per_day": 100.0,
                "max_tokens_per_request": 100000,
                "warn_on_expensive_model": True,
                "expensive_threshold": 0.05,
            },
            "cache": {
                "enabled": True,
                "ttl_seconds": 3600,
                "max_entries": 1000,
            },
        }

    def _get_default_config_toml(self) -> str:
        """Default config TOML text for first-run creation."""
        default = self._get_default_config()
        # Keep TOML literal close to design sample for readability.
        return "\n".join(
            [
                "[general]",
                f'version = "{default["general"]["version"]}"',
                f'log_level = "{default["general"]["log_level"]}"',
                f'log_file = "{default["general"]["log_file"]}"',
                "",
                "[orchestrator]",
                f'default_backend = "{default["orchestrator"]["default_backend"]}"',
                "fallback_chain = [\"claude\", \"openai\", \"gemini\", \"ollama\"]",
                "auto_switch_on_context_limit = true",
                "streaming_preferred = true",
                "",
                "[backends.claude]",
                'provider = "claude"',
                'model = "claude-sonnet-4.5-20250929"',
                'persona = "general-assistant"',
                "max_context_tokens = 200000",
                "temperature = 0.7",
                "",
                "[backends.openai]",
                'provider = "openai"',
                'model = "gpt-4o"',
                'persona = "code-specialist"',
                "max_context_tokens = 128000",
                "temperature = 0.7",
                "",
                "[backends.gemini]",
                'provider = "gemini"',
                'model = "gemini-2-flash"',
                'persona = "fast-parser"',
                "max_context_tokens = 1000000",
                "temperature = 0.5",
                "",
                "[backends.ollama]",
                'provider = "ollama"',
                'model = "deepseek-coder:latest"',
                'persona = "local-coder"',
                "max_context_tokens = 8192",
                "temperature = 0.3",
                "",
                "[backends.opus]",
                'provider = "opus_self"',
                'model = "claude-opus-4-5-20251101"',
                'persona = "architect"',
                "max_context_tokens = 200000",
                "temperature = 0.2",
                "",
                "[context]",
                "session_max_messages = 50",
                "session_max_tokens = 100000",
                "persistent_memory_enabled = true",
                'memory_db_path = "~/.config/blueprint/memory.db"',
                "auto_summarize_threshold = 40",
                'summarization_backend = "gemini"',
                "enable_distillation = true",
                'distillation_backend = "gemini"',
                'distillation_persona = "context-distiller"',
                "distillation_trigger_tokens = 50000",
                "distillation_target_tokens = 8000",
                "",
                "[tools]",
                'permission_mode = "manual"',
                "sandbox_enabled = true",
                "timeout_seconds = 300",
                'auto_approve = ["read_file:src/**", "list_directory:**", "search_code:**"]',
                "",
                "[quotas]",
                "max_cost_per_hour = 10.0",
                "max_cost_per_day = 100.0",
                "max_tokens_per_request = 100000",
                "warn_on_expensive_model = true",
                "expensive_threshold = 0.05",
                "",
                "[cache]",
                "enabled = true",
                "ttl_seconds = 3600",
                "max_entries = 1000",
                "",
            ]
        )

    def _get_default_personas(self) -> Dict[str, Any]:
        """Default personas matching the design doc."""
        return {
            "personas": {
                "general-assistant": {
                    "name": "General Assistant",
                    "description": "Balanced general-purpose assistant",
                    "system_prompt": (
                        "You are a helpful AI assistant. You provide clear, accurate, "
                        "and concise answers. You think step-by-step and explain your reasoning."
                    ),
                    "preferred_backends": ["claude", "openai"],
                    "temperature": 0.7,
                    "max_tokens": 4000,
                },
                "code-specialist": {
                    "name": "Code Specialist",
                    "description": "Expert at writing, reviewing, and debugging code",
                    "system_prompt": (
                        "You are an expert software engineer. You write clean, idiomatic, "
                        "well-tested code. You follow best practices and explain your design decisions."
                    ),
                    "preferred_backends": ["openai", "claude"],
                    "temperature": 0.3,
                    "max_tokens": 8000,
                },
                "fast-parser": {
                    "name": "Fast Parser",
                    "description": "Quick parsing and structured output",
                    "system_prompt": (
                        "You are a fast, efficient parser. You extract structured "
                        "information accurately and return well-formatted JSON responses."
                    ),
                    "preferred_backends": ["gemini", "openai"],
                    "temperature": 0.2,
                    "max_tokens": 2000,
                },
                "context-distiller": {
                    "name": "Context Distiller",
                    "description": "Distills large contexts into focused, task-relevant summaries",
                    "system_prompt": (
                        "You are a context distillation specialist. Your job is to read "
                        "large amounts of context (conversation history, code, documentation) and extract "
                        "only the most relevant information for the current task.\n\n"
                        "Focus on:\n"
                        "- Key decisions and their rationale\n"
                        "- Important code patterns and structures\n"
                        "- Unresolved issues or blockers\n"
                        "- Critical facts and constraints\n"
                        "- Recent changes and their impact\n\n"
                        "Produce a concise summary that preserves all task-relevant information while "
                        "removing redundancy and tangential details."
                    ),
                    "preferred_backends": ["gemini"],
                    "temperature": 0.3,
                    "max_tokens": 4000,
                },
                "local-coder": {
                    "name": "Local Coder",
                    "description": "Local model for simple coding tasks",
                    "system_prompt": (
                        "You are a coding assistant running locally. You provide "
                        "concise, practical code solutions."
                    ),
                    "preferred_backends": ["ollama"],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                    "context_window": 8192,
                },
                "architect": {
                    "name": "Software Architect",
                    "description": "Deep reasoning and system design",
                    "system_prompt": (
                        "You are a senior software architect with deep expertise in "
                        "system design, architecture patterns, and best practices. You think thoroughly "
                        "about trade-offs, scalability, maintainability, and provide detailed technical plans."
                    ),
                    "preferred_backends": ["opus"],
                    "temperature": 0.2,
                    "max_tokens": 16000,
                },
            }
        }

    def _get_default_personas_toml(self) -> str:
        """Default personas TOML text (kept readable for users)."""
        data = self._get_default_personas()["personas"]
        lines: list[str] = []
        for key, persona in data.items():
            lines.append(f"[personas.{key}]")
            lines.append(f'name = "{persona["name"]}"')
            lines.append(f'description = "{persona["description"]}"')
            lines.append('system_prompt = """' + persona["system_prompt"] + '"""')
            preferred = ", ".join(f'"{p}"' for p in persona.get("preferred_backends", []))
            lines.append(f"preferred_backends = [{preferred}]")
            lines.append(f'temperature = {persona.get("temperature", 0.7)}')
            lines.append(f"max_tokens = {persona.get('max_tokens', 4000)}")
            if "context_window" in persona:
                lines.append(f"context_window = {persona['context_window']}")
            lines.append("")  # blank line between personas
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Utility helpers
    # ------------------------------------------------------------------ #
    def _deep_merge(self, base: dict, override: dict) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _set_nested(self, d: dict, path: str, value: Any) -> None:
        keys = path.split(".")
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value


# Backwards compatibility: existing code imports Config
Config = ConfigLoader

__all__ = ["ConfigLoader", "Config"]
