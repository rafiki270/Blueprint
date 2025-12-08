# LLM Orchestrator Architecture - Python Implementation

## Executive Summary

This document specifies a production-grade multi-LLM orchestration platform in Python. The orchestrator sits above the LLM wrapper layer and provides intelligent routing, context management, tool execution, streaming coordination, and persona-based model selection. It follows Python best practices and integrates with the unified LLM wrapper designed in `LLM_API_WRAPPER.md`.

---

## Table of Contents

1. [Configuration Management Strategy](#1-configuration-management-strategy)
2. [Architecture Overview](#2-architecture-overview)
3. [Module Breakdown](#3-module-breakdown)
4. [Python API Interfaces](#4-python-api-interfaces)
5. [Persona System](#5-persona-system)
6. [Context Management](#6-context-management)
7. [Tool Execution & Permissions](#7-tool-execution--permissions)
8. [Orchestration & Routing Logic](#8-orchestration--routing-logic)
9. [Streaming Coordination](#9-streaming-coordination)
10. [Usage Tracking & Quotas](#10-usage-tracking--quotas)
11. [Task & Workflow Management](#11-task--workflow-management)
12. [Implementation Roadmap](#12-implementation-roadmap)
13. [Example Usage](#13-example-usage)

---

## 1. Configuration Management Strategy

### 1.1 Industry Best Practices Analysis

Following patterns from major CLI tools:

| Tool | Global Config | Local Config | Credentials |
|------|--------------|--------------|-------------|
| Git | `~/.gitconfig` | `.git/config` | Credential helper |
| AWS CLI | `~/.aws/config` | - | `~/.aws/credentials` |
| Docker | `~/.docker/config.json` | - | In config file |
| VS Code | `~/.config/Code/User/settings.json` | `.vscode/settings.json` | Keychain |
| npm | `~/.npmrc` | `.npmrc` | In npmrc |
| Terraform | - | `.terraform/` | Various providers |

**Common Patterns:**
- Global config in XDG-compliant directory (`~/.config/<app>/`)
- Local config in project directory (`.app/` or `.apprc`)
- Credentials separated from config (when sensitive)
- Platform-specific paths (XDG on Linux, Application Support on macOS)

### 1.2 Blueprint Configuration Strategy

```
Global Configuration Hierarchy:
┌─────────────────────────────────────────────────────────┐
│ Platform-Specific Global Config Directory              │
│                                                          │
│ Linux:   ~/.config/blueprint/                           │
│ macOS:   ~/.config/blueprint/  (or ~/Library/...)       │
│ Windows: %APPDATA%\blueprint\                           │
└─────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┬──────────────┐
        ▼                ▼                ▼              ▼
   config.toml    credentials.toml   personas.toml   usage.db
   (settings)      (API keys)         (model roles)   (metrics)

Project-Local Configuration:
┌─────────────────────────────────────────────────────────┐
│ Project Root: .blueprint/                               │
└─────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┬──────────────┐
        ▼                ▼                ▼              ▼
   config.toml     personas.toml    memory.db      tools.toml
   (overrides)     (project roles)  (context)      (permissions)
```

### 1.3 Configuration File Formats

**Why TOML?**
- Human-readable and editable (better than JSON)
- Strong typing (better than YAML)
- Python standard library support (`tomllib` in 3.11+, `toml` package)
- Used by major Python tools (Poetry, Black, mypy)

#### Global Config (~/.config/blueprint/config.toml)

```toml
[general]
version = "1.0.0"
log_level = "info"
log_file = "~/.config/blueprint/blueprint.log"

[orchestrator]
default_backend = "claude"
fallback_chain = ["claude", "openai", "gemini", "ollama"]
auto_switch_on_context_limit = true
streaming_preferred = true

[backends.claude]
provider = "claude"
model = "claude-sonnet-4.5-20250929"
persona = "general-assistant"
max_context_tokens = 200000
temperature = 0.7

[backends.openai]
provider = "openai"
model = "gpt-4o"
persona = "code-specialist"
max_context_tokens = 128000
temperature = 0.7

[backends.gemini]
provider = "gemini"
model = "gemini-2-flash"
persona = "fast-parser"
max_context_tokens = 1000000
temperature = 0.5

[backends.ollama]
provider = "ollama"
model = "deepseek-coder:latest"
persona = "local-coder"
max_context_tokens = 8192
temperature = 0.3

[backends.opus]
provider = "opus_self"
model = "claude-opus-4-5-20251101"
persona = "architect"
max_context_tokens = 200000
temperature = 0.2

[context]
# Short-term session context
session_max_messages = 50
session_max_tokens = 100000

# Persistent memory
persistent_memory_enabled = true
memory_db_path = "~/.config/blueprint/memory.db"

# Context compression
auto_summarize_threshold = 40  # messages
summarization_backend = "gemini"  # fast model for summarization

# Context distillation (for large contexts)
enable_distillation = true
distillation_backend = "gemini"  # Use Gemini's large context window
distillation_persona = "context-distiller"
distillation_trigger_tokens = 50000  # Distill when context exceeds this
distillation_target_tokens = 8000    # Target size after distillation

[tools]
# Permission modes: "manual" (ask every time), "auto" (whitelist), "deny"
permission_mode = "manual"
sandbox_enabled = true
timeout_seconds = 300

# Auto-approved tool patterns (when permission_mode = "auto")
auto_approve = [
    "read_file:src/**",
    "list_directory:**",
    "search_code:**",
]

[quotas]
max_cost_per_hour = 10.0
max_cost_per_day = 100.0
max_tokens_per_request = 100000
warn_on_expensive_model = true
expensive_threshold = 0.05  # per request

[cache]
enabled = true
ttl_seconds = 3600
max_entries = 1000
```

#### Credentials (~/.config/blueprint/credentials.toml)

```toml
# IMPORTANT: This file should have 0600 permissions (user read/write only)

[openai]
api_key = "sk-..."
organization_id = "org-..."
base_url = "https://api.openai.com/v1"

[claude]
api_key = "sk-ant-..."
base_url = "https://api.anthropic.com"
version = "2023-06-01"

[gemini]
api_key = "AIza..."
project_id = "my-project-123"

[ollama]
base_url = "http://localhost:11434"
# No API key needed for local

[opus_self]
api_key = "sk-ant-..."  # Same as claude or separate
model = "claude-opus-4-5-20251101"
```

#### Personas (~/.config/blueprint/personas.toml)

```toml
# Persona definitions: role-specific system prompts and behavior

[personas.general-assistant]
name = "General Assistant"
description = "Balanced general-purpose assistant"
system_prompt = """You are a helpful AI assistant. You provide clear, accurate,
and concise answers. You think step-by-step and explain your reasoning."""
preferred_backends = ["claude", "openai"]
temperature = 0.7
max_tokens = 4000

[personas.code-specialist]
name = "Code Specialist"
description = "Expert at writing, reviewing, and debugging code"
system_prompt = """You are an expert software engineer. You write clean, idiomatic,
well-tested code. You follow best practices and explain your design decisions."""
preferred_backends = ["openai", "claude"]
temperature = 0.3
max_tokens = 8000

[personas.fast-parser]
name = "Fast Parser"
description = "Quick parsing and structured output"
system_prompt = """You are a fast, efficient parser. You extract structured
information accurately and return well-formatted JSON responses."""
preferred_backends = ["gemini", "openai"]
temperature = 0.2
max_tokens = 2000

[personas.context-distiller]
name = "Context Distiller"
description = "Distills large contexts into focused, task-relevant summaries"
system_prompt = """You are a context distillation specialist. Your job is to read
large amounts of context (conversation history, code, documentation) and extract
only the most relevant information for the current task.

Focus on:
- Key decisions and their rationale
- Important code patterns and structures
- Unresolved issues or blockers
- Critical facts and constraints
- Recent changes and their impact

Produce a concise summary that preserves all task-relevant information while
removing redundancy and tangential details."""
preferred_backends = ["gemini"]  # Gemini has 1M+ context window
temperature = 0.3
max_tokens = 4000

[personas.local-coder]
name = "Local Coder"
description = "Local model for simple coding tasks"
system_prompt = """You are a coding assistant running locally. You provide
concise, practical code solutions."""
preferred_backends = ["ollama"]
temperature = 0.3
max_tokens = 2000
context_window = 8192  # Strict limit for local model

[personas.architect]
name = "Software Architect"
description = "Deep reasoning and system design"
system_prompt = """You are a senior software architect with deep expertise in
system design, architecture patterns, and best practices. You think thoroughly
about trade-offs, scalability, maintainability, and provide detailed technical plans."""
preferred_backends = ["opus"]
temperature = 0.2
max_tokens = 16000
```

#### Project Config (.blueprint/config.toml)

```toml
# Project-specific overrides
[project]
name = "my-awesome-project"
version = "0.1.0"

[orchestrator]
default_backend = "ollama"  # Override global: prefer local for this project
fallback_chain = ["ollama", "claude", "openai"]

[tools]
permission_mode = "auto"  # Trust this project
auto_approve = [
    "read_file:**",
    "write_file:src/**",
    "run_tests:**",
    "git_diff:**",
]

[context]
# Project-specific context settings
include_files = [
    "README.md",
    "docs/architecture.md",
    "src/core/**/*.py",
]
```

### 1.4 Configuration Resolution Order

```
Priority (highest to lowest):
1. Command-line arguments
2. Environment variables (BLUEPRINT_*)
3. Project config (.blueprint/config.toml)
4. Global config (~/.config/blueprint/config.toml)
5. Built-in defaults
```

### 1.5 Configuration Loader Implementation

```python
from pathlib import Path
from typing import Any, Dict
import tomllib  # Python 3.11+ (or use `toml` package for older versions)
import os
import platform

class ConfigLoader:
    """Handles configuration loading from multiple sources with priority resolution."""

    @staticmethod
    def get_global_config_dir() -> Path:
        """Get platform-specific global config directory following XDG spec."""
        if platform.system() == "Windows":
            base = Path(os.environ.get("APPDATA", "~\\AppData\\Roaming")).expanduser()
        elif platform.system() == "Darwin":  # macOS
            # Support both XDG and macOS-native paths
            xdg = os.environ.get("XDG_CONFIG_HOME")
            if xdg:
                base = Path(xdg)
            else:
                # Use ~/.config for consistency, but could use ~/Library/Application Support
                base = Path.home() / ".config"
        else:  # Linux and others
            base = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()

        return base / "blueprint"

    @staticmethod
    def get_project_config_dir() -> Path | None:
        """Find .blueprint directory in current or parent directories."""
        current = Path.cwd()

        # Walk up directory tree looking for .blueprint/
        for parent in [current] + list(current.parents):
            config_dir = parent / ".blueprint"
            if config_dir.is_dir():
                return config_dir

        return None

    def __init__(self):
        self.global_dir = self.get_global_config_dir()
        self.project_dir = self.get_project_config_dir()

        self.config: Dict[str, Any] = {}
        self.credentials: Dict[str, Any] = {}
        self.personas: Dict[str, Any] = {}

        self._load_all()

    def _load_all(self):
        """Load all configuration files with proper priority."""
        # Load global configs
        self._load_global_config()
        self._load_credentials()
        self._load_personas()

        # Load project configs (overrides global)
        if self.project_dir:
            self._load_project_config()
            self._load_project_personas()

        # Apply environment variable overrides
        self._apply_env_overrides()

    def _load_global_config(self):
        """Load global configuration."""
        config_file = self.global_dir / "config.toml"
        if config_file.exists():
            with open(config_file, "rb") as f:
                self.config = tomllib.load(f)
        else:
            self.config = self._get_default_config()
            self._create_default_config()

    def _load_credentials(self):
        """Load credentials with security checks."""
        creds_file = self.global_dir / "credentials.toml"

        if not creds_file.exists():
            self._create_default_credentials()
            return

        # Check file permissions (Unix-like systems)
        if platform.system() != "Windows":
            stat_info = os.stat(creds_file)
            if stat_info.st_mode & 0o077:  # Check if group/world readable
                raise PermissionError(
                    f"Insecure permissions on {creds_file}. "
                    f"Run: chmod 600 {creds_file}"
                )

        with open(creds_file, "rb") as f:
            self.credentials = tomllib.load(f)

    def _load_personas(self):
        """Load global personas."""
        personas_file = self.global_dir / "personas.toml"
        if personas_file.exists():
            with open(personas_file, "rb") as f:
                self.personas = tomllib.load(f).get("personas", {})
        else:
            self.personas = self._get_default_personas()
            self._create_default_personas()

    def _load_project_config(self):
        """Load project-specific config and merge with global."""
        config_file = self.project_dir / "config.toml"
        if config_file.exists():
            with open(config_file, "rb") as f:
                project_config = tomllib.load(f)
                self._deep_merge(self.config, project_config)

    def _load_project_personas(self):
        """Load project-specific personas."""
        personas_file = self.project_dir / "personas.toml"
        if personas_file.exists():
            with open(personas_file, "rb") as f:
                project_personas = tomllib.load(f).get("personas", {})
                # Project personas override global
                self.personas.update(project_personas)

    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        # Support BLUEPRINT_* environment variables
        env_prefix = "BLUEPRINT_"
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                # Convert BLUEPRINT_ORCHESTRATOR_DEFAULT_BACKEND -> orchestrator.default_backend
                config_key = key[len(env_prefix):].lower().replace("_", ".")
                self._set_nested(self.config, config_key, value)

    def _deep_merge(self, base: dict, override: dict):
        """Deep merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _set_nested(self, d: dict, path: str, value: Any):
        """Set nested dictionary value from dot-separated path."""
        keys = path.split(".")
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value

    def _create_default_config(self):
        """Create default global config file."""
        self.global_dir.mkdir(parents=True, exist_ok=True)
        config_file = self.global_dir / "config.toml"

        with open(config_file, "w") as f:
            f.write(self._get_default_config_toml())

    def _create_default_credentials(self):
        """Create empty credentials file with secure permissions."""
        self.global_dir.mkdir(parents=True, exist_ok=True)
        creds_file = self.global_dir / "credentials.toml"

        with open(creds_file, "w") as f:
            f.write("# Add your API credentials here\n\n")

        # Set secure permissions (Unix-like)
        if platform.system() != "Windows":
            os.chmod(creds_file, 0o600)

    def _create_default_personas(self):
        """Create default personas file."""
        self.global_dir.mkdir(parents=True, exist_ok=True)
        personas_file = self.global_dir / "personas.toml"

        with open(personas_file, "w") as f:
            f.write(self._get_default_personas_toml())

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-separated key."""
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def get_credential(self, provider: str, key: str) -> str | None:
        """Get credential for a provider."""
        return self.credentials.get(provider, {}).get(key)

    def get_persona(self, name: str) -> Dict[str, Any] | None:
        """Get persona configuration by name."""
        return self.personas.get(name)

    # ... default config generation methods omitted for brevity
```

---

## 2. Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                        CLI / Application                       │
└───────────────────────────┬────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                      LLM Orchestrator                          │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Public API                                               │ │
│  │  • chat() / stream()                                      │ │
│  │  • execute_task() / plan_task()                           │ │
│  │  • switch_persona() / reset_context()                     │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────┬──────────────┬────────────┬─────────────┐   │
│  │ Router &    │ Context      │ Tool       │ Streaming   │   │
│  │ Backend     │ Manager      │ Executor   │ Coordinator │   │
│  │ Selector    │              │            │             │   │
│  └─────────────┴──────────────┴────────────┴─────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Cross-Cutting Services                                   │ │
│  │  • Usage Tracker  • Permission Manager                    │ │
│  │  • Config Loader  • Metrics Logger                        │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────┬────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                    LLM Wrapper (Backend Layer)                 │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐    │
│  │ OpenAI   │ Claude   │ Gemini   │ Ollama   │ Opus     │    │
│  │ Adapter  │ Adapter  │ Adapter  │ Adapter  │ Adapter  │    │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘    │
└────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┬──────────┐
        ▼                   ▼                   ▼          ▼
   [OpenAI API]        [Claude API]        [Gemini]   [Ollama]
```

### 2.1 Layer Responsibilities

**Orchestrator Layer (this design):**
- Intelligent routing to appropriate backend
- Context management (session + persistent)
- Tool execution with permissions
- Persona management
- Task workflow coordination

**Wrapper Layer (from LLM_API_WRAPPER.md):**
- Unified API across providers
- Streaming with error recovery
- Fallback chains
- Usage tracking
- Request/response normalization

---

## 3. Module Breakdown

### 3.1 Module Structure

```
blueprint/
├── orchestrator/
│   ├── __init__.py
│   ├── orchestrator.py         # Main Orchestrator class
│   ├── router.py                # Backend selection & routing
│   ├── persona.py               # Persona management
│   └── task.py                  # Task workflow coordination
├── context/
│   ├── __init__.py
│   ├── manager.py               # Context manager
│   ├── session.py               # Short-term session context
│   ├── memory.py                # Persistent memory store
│   └── retriever.py             # Context retrieval & summarization
├── tools/
│   ├── __init__.py
│   ├── executor.py              # Tool execution engine
│   ├── permissions.py           # Permission management
│   ├── registry.py              # Tool registry
│   └── builtin/                 # Built-in tools
│       ├── file_ops.py
│       ├── code_ops.py
│       ├── shell.py
│       └── git.py
├── streaming/
│   ├── __init__.py
│   ├── coordinator.py           # Streaming coordination
│   └── validator.py             # Output validation
├── config/
│   ├── __init__.py
│   ├── loader.py                # Config loader (see 1.5)
│   └── models.py                # Pydantic models for config
├── usage/
│   ├── __init__.py
│   ├── tracker.py               # Usage tracking
│   └── quotas.py                # Quota enforcement
├── wrapper/                      # LLM Wrapper layer
│   ├── __init__.py
│   ├── client.py                # Main LLMClient
│   ├── adapters/                # Provider adapters
│   └── ...
└── cli/
    ├── __init__.py
    └── main.py                  # CLI entry point
```

---

## 4. Python API Interfaces

### 4.1 Core Protocols & Types

```python
from typing import Protocol, Iterator, AsyncIterator, Literal, TypedDict
from dataclasses import dataclass
from enum import Enum

# ============ Message Types ============

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass
class Message:
    role: MessageRole
    content: str
    name: str | None = None          # For tool messages
    tool_call_id: str | None = None  # For tool responses
    metadata: dict[str, Any] | None = None

# ============ Response Types ============

@dataclass
class ChatResponse:
    content: str
    finish_reason: Literal["stop", "length", "tool_call", "error"]
    usage: UsageInfo
    tool_calls: list[ToolCall] | None = None
    backend: str
    model: str
    metadata: ResponseMetadata

@dataclass
class UsageInfo:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float | None = None

@dataclass
class ResponseMetadata:
    request_id: str
    latency_ms: float
    cached: bool = False
    retries_attempted: int = 0

@dataclass
class StreamChunk:
    delta: str
    is_done: bool
    usage: UsageInfo | None = None
    tool_call: ToolCall | None = None
    error: Exception | None = None

# ============ Tool Types ============

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON schema
    handler: Callable[[dict], Any]
    requires_approval: bool = True

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

@dataclass
class ToolResult:
    tool_call_id: str
    result: Any
    error: str | None = None
    approved: bool = True

# ============ Persona Types ============

@dataclass
class Persona:
    name: str
    description: str
    system_prompt: str
    preferred_backends: list[str]
    temperature: float = 0.7
    max_tokens: int = 4000
    context_window: int | None = None  # Override for this persona

# ============ Backend Protocol ============

class LLMBackend(Protocol):
    """Protocol for LLM backend implementations."""

    name: str
    persona: Persona

    def chat(
        self,
        messages: list[Message],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[Tool] | None = None,
    ) -> ChatResponse:
        """Synchronous chat completion."""
        ...

    def stream(
        self,
        messages: list[Message],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[Tool] | None = None,
    ) -> Iterator[StreamChunk]:
        """Streaming chat completion."""
        ...

    async def achat(
        self,
        messages: list[Message],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[Tool] | None = None,
    ) -> ChatResponse:
        """Async chat completion."""
        ...

    async def astream(
        self,
        messages: list[Message],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[Tool] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Async streaming chat completion."""
        ...

    def reset_context(self) -> None:
        """Clear this backend's conversation context."""
        ...

    def get_usage(self) -> UsageStats:
        """Get usage statistics for this backend."""
        ...

    @property
    def max_context_tokens(self) -> int:
        """Maximum context window size in tokens."""
        ...

    @property
    def supports_streaming(self) -> bool:
        """Whether this backend supports streaming."""
        ...

    @property
    def supports_tools(self) -> bool:
        """Whether this backend supports tool calling."""
        ...
```

### 4.2 Main Orchestrator Interface

```python
from pathlib import Path

class LLMOrchestrator:
    """
    Main orchestrator for multi-LLM platform.

    Responsibilities:
    - Route requests to appropriate backends
    - Manage context across backends
    - Coordinate tool execution with permissions
    - Handle streaming with validation
    - Track usage and enforce quotas
    """

    def __init__(
        self,
        config_dir: Path | None = None,
        project_dir: Path | None = None,
    ):
        """
        Initialize orchestrator.

        Args:
            config_dir: Override global config directory
            project_dir: Override project directory detection
        """
        self.config = ConfigLoader()
        self.wrapper = LLMClient()  # From wrapper layer

        # Core components
        self.router = BackendRouter(self.config, self.wrapper)
        self.context_manager = ContextManager(self.config)
        self.tool_executor = ToolExecutor(self.config)
        self.stream_coordinator = StreamCoordinator()
        self.usage_tracker = UsageTracker(self.config)
        self.persona_manager = PersonaManager(self.config)

        # Initialize backends
        self._backends: dict[str, LLMBackend] = {}
        self._initialize_backends()

    # ============ Core Chat Methods ============

    def chat(
        self,
        message: str | list[Message],
        *,
        backend: str | None = None,
        persona: str | None = None,
        include_context: bool = True,
        tools: list[Tool] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ChatResponse:
        """
        Send a chat message with automatic routing and context management.

        Args:
            message: User message or full message history
            backend: Override backend selection (default: auto-route)
            persona: Use specific persona (default: current persona)
            include_context: Include session context in request
            tools: Available tools for this request
            max_tokens: Override max tokens
            temperature: Override temperature

        Returns:
            ChatResponse with result

        Example:
            >>> orchestrator = LLMOrchestrator()
            >>> response = orchestrator.chat("Explain async/await in Python")
            >>> print(response.content)
        """
        # Prepare messages
        messages = self._prepare_messages(message, include_context)

        # Determine task category for fallback routing
        task_category = self.router._categorize_task(messages, persona)

        # Track attempted backends for fallback
        attempted_backends = []

        # Retry loop for quota-exceeded handling
        while True:
            # Select backend
            if backend is None:
                backend = self.router.select_backend(
                    messages=messages,
                    persona=persona,
                    task_type="chat",
                    exclude_backends=attempted_backends,
                )

            # Apply persona
            if persona:
                self.switch_persona(persona, backend=backend)

            # Add system prompt from persona
            messages = self._apply_persona_prompt(messages, backend)

            try:
                # Check quotas
                self.usage_tracker.check_quotas(backend)

                # Execute
                backend_impl = self._backends[backend]
                response = backend_impl.chat(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    tools=tools or self.tool_executor.get_enabled_tools(),
                )

                # Handle tool calls
                if response.finish_reason == "tool_call":
                    response = self._handle_tool_calls(response, backend_impl, messages)

                # Update context
                if include_context:
                    self.context_manager.add_message(Message(MessageRole.USER, str(message)))
                    self.context_manager.add_message(Message(MessageRole.ASSISTANT, response.content))

                # Track usage
                self.usage_tracker.record(backend, response.usage)

                return response

            except QuotaExceededError as e:
                # Quota exceeded - try fallback backend
                attempted_backends.append(backend)
                fallback_backend = self.router.get_fallback_for_quota_exceeded(backend, task_category)

                if fallback_backend and fallback_backend not in attempted_backends:
                    print(f"Quota exceeded for {backend}. Falling back to {fallback_backend}...")
                    backend = fallback_backend
                    # Retry with fallback backend
                    continue
                else:
                    # No more fallbacks available
                    raise Exception(
                        f"All backends exhausted. Quota exceeded for: {', '.join(attempted_backends)}"
                    ) from e

            except Exception as e:
                # Other errors - don't retry
                raise

    def stream(
        self,
        message: str | list[Message],
        *,
        backend: str | None = None,
        persona: str | None = None,
        include_context: bool = True,
        tools: list[Tool] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Iterator[StreamChunk]:
        """
        Stream chat response with automatic routing and validation.

        Yields:
            StreamChunk objects with incremental content

        Example:
            >>> for chunk in orchestrator.stream("Write a sorting algorithm"):
            ...     print(chunk.delta, end="", flush=True)
        """
        # Similar to chat() but yields chunks
        messages = self._prepare_messages(message, include_context)

        if backend is None:
            backend = self.router.select_backend(
                messages=messages,
                persona=persona,
                task_type="stream",
            )

        backend_impl = self._backends[backend]

        # Stream with validation and error recovery
        yield from self.stream_coordinator.stream_with_validation(
            backend=backend_impl,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
        )

    async def achat(self, *args, **kwargs) -> ChatResponse:
        """Async version of chat()."""
        ...

    async def astream(self, *args, **kwargs) -> AsyncIterator[StreamChunk]:
        """Async version of stream()."""
        ...

    # ============ Task Management ============

    def execute_task(
        self,
        task: Task,
        *,
        backend: str | None = None,
        streaming: bool = True,
    ) -> TaskResult:
        """
        Execute a complex multi-step task.

        Args:
            task: Task definition with steps and requirements
            backend: Override backend selection
            streaming: Stream intermediate results

        Returns:
            TaskResult with outputs from each step

        Example:
            >>> task = Task(
            ...     name="refactor-auth",
            ...     steps=[
            ...         TaskStep("analyze", "Review current auth implementation"),
            ...         TaskStep("design", "Design new auth system"),
            ...         TaskStep("implement", "Implement changes"),
            ...     ]
            ... )
            >>> result = orchestrator.execute_task(task)
        """
        return self.task_coordinator.execute(task, backend, streaming)

    def plan_task(
        self,
        goal: str,
        requirements: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Task:
        """
        Use planning backend (Opus) to create a detailed task plan.

        Args:
            goal: High-level goal description
            requirements: List of requirements
            context: Additional context (files, docs, etc.)

        Returns:
            Task with generated steps and dependencies

        Example:
            >>> task = orchestrator.plan_task(
            ...     goal="Add user authentication",
            ...     requirements=["JWT tokens", "Password hashing", "RBAC"],
            ... )
            >>> print(task.steps)
        """
        planning_backend = self.config.get("backends.opus.name", "opus")
        planner = self._backends[planning_backend]

        # Use planning persona
        planning_prompt = self._build_planning_prompt(goal, requirements, context)
        response = planner.chat(messages=[Message(MessageRole.USER, planning_prompt)])

        # Parse response into Task
        return self._parse_task_plan(response.content)

    # ============ Context Management ============

    def reset_context(self, backend: str | None = None) -> None:
        """
        Reset conversation context.

        Args:
            backend: Reset specific backend, or all if None

        Example:
            >>> orchestrator.reset_context("ollama")
        """
        if backend:
            self._backends[backend].reset_context()
            self.context_manager.clear_backend_context(backend)
        else:
            for b in self._backends.values():
                b.reset_context()
            self.context_manager.clear_all()

    def get_context(self, backend: str | None = None) -> list[Message]:
        """Get current conversation context."""
        return self.context_manager.get_context(backend)

    def add_persistent_memory(self, key: str, value: Any, tags: list[str] | None = None):
        """Add to persistent memory store."""
        self.context_manager.memory.store(key, value, tags)

    def retrieve_memory(self, query: str, limit: int = 5) -> list[Any]:
        """Retrieve relevant items from persistent memory."""
        return self.context_manager.memory.retrieve(query, limit)

    # ============ Persona Management ============

    def switch_persona(self, persona_name: str, backend: str | None = None) -> None:
        """
        Switch to a different persona.

        Args:
            persona_name: Name of persona (from config)
            backend: Apply to specific backend, or current default

        Example:
            >>> orchestrator.switch_persona("code-specialist")
        """
        persona = self.persona_manager.get(persona_name)
        if not persona:
            raise ValueError(f"Unknown persona: {persona_name}")

        target_backend = backend or self.router.current_backend
        self._backends[target_backend].persona = persona

    def get_current_persona(self, backend: str | None = None) -> Persona:
        """Get active persona for backend."""
        target_backend = backend or self.router.current_backend
        return self._backends[target_backend].persona

    def list_personas(self) -> list[str]:
        """List available persona names."""
        return self.persona_manager.list_personas()

    # ============ Tool Management ============

    def register_tool(self, tool: Tool) -> None:
        """Register a tool for LLM use."""
        self.tool_executor.register(tool)

    def unregister_tool(self, name: str) -> None:
        """Unregister a tool."""
        self.tool_executor.unregister(name)

    def set_tool_permission_mode(self, mode: Literal["manual", "auto", "deny"]) -> None:
        """Set tool permission mode."""
        self.tool_executor.set_permission_mode(mode)

    def approve_tool(self, tool_call_id: str) -> None:
        """Manually approve a pending tool call."""
        self.tool_executor.approve(tool_call_id)

    def deny_tool(self, tool_call_id: str) -> None:
        """Deny a pending tool call."""
        self.tool_executor.deny(tool_call_id)

    # ============ Usage & Metrics ============

    def get_usage(self, backend: str | None = None) -> UsageStats:
        """Get usage statistics."""
        if backend:
            return self._backends[backend].get_usage()
        else:
            return self.usage_tracker.get_aggregate_usage()

    def reset_usage(self) -> None:
        """Reset usage counters."""
        self.usage_tracker.reset()

    def get_health(self) -> dict[str, HealthStatus]:
        """Check health of all backends."""
        return {
            name: backend.check_health()
            for name, backend in self._backends.items()
        }

    # ============ Private Methods ============

    def _initialize_backends(self):
        """Initialize all configured backends."""
        backend_configs = self.config.get("backends", {})

        for name, config in backend_configs.items():
            persona = self.persona_manager.get(config.get("persona"))
            backend = BackendWrapper(
                name=name,
                provider=config["provider"],
                model=config["model"],
                persona=persona,
                wrapper_client=self.wrapper,
                config=config,
            )
            self._backends[name] = backend

    def _prepare_messages(
        self,
        message: str | list[Message],
        include_context: bool,
    ) -> list[Message]:
        """Prepare message list with context."""
        if isinstance(message, str):
            user_message = Message(MessageRole.USER, message)
            messages = [user_message]
        else:
            messages = message

        if include_context:
            context = self.context_manager.get_context()
            messages = context + messages

        return messages

    def _apply_persona_prompt(
        self,
        messages: list[Message],
        backend: str,
    ) -> list[Message]:
        """Prepend system prompt from persona."""
        persona = self._backends[backend].persona

        # Check if there's already a system message
        has_system = any(msg.role == MessageRole.SYSTEM for msg in messages)

        if not has_system and persona.system_prompt:
            system_msg = Message(MessageRole.SYSTEM, persona.system_prompt)
            return [system_msg] + messages

        return messages

    def _handle_tool_calls(
        self,
        response: ChatResponse,
        backend: LLMBackend,
        messages: list[Message],
    ) -> ChatResponse:
        """Execute tool calls and continue conversation."""
        if not response.tool_calls:
            return response

        # Execute each tool call
        tool_results = []
        for tool_call in response.tool_calls:
            result = self.tool_executor.execute(tool_call)
            tool_results.append(result)

        # Add assistant message with tool calls
        messages.append(Message(
            MessageRole.ASSISTANT,
            response.content,
            metadata={"tool_calls": response.tool_calls}
        ))

        # Add tool results
        for result in tool_results:
            messages.append(Message(
                MessageRole.TOOL,
                str(result.result),
                tool_call_id=result.tool_call_id,
            ))

        # Continue conversation
        return backend.chat(messages)
```

---

## 5. Persona System

### 5.1 Persona Manager

```python
from dataclasses import dataclass, field

@dataclass
class Persona:
    name: str
    description: str
    system_prompt: str
    preferred_backends: list[str] = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4000
    context_window: int | None = None

    # Behavioral settings
    verbosity: Literal["concise", "normal", "verbose"] = "normal"
    thinking_style: Literal["direct", "step_by_step", "deep_reasoning"] = "step_by_step"

    # Task preferences
    prefers_streaming: bool = True
    requires_tools: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "preferred_backends": self.preferred_backends,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "context_window": self.context_window,
            "verbosity": self.verbosity,
            "thinking_style": self.thinking_style,
            "prefers_streaming": self.prefers_streaming,
            "requires_tools": self.requires_tools,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Persona":
        """Create from dictionary."""
        return cls(**data)

class PersonaManager:
    """Manages persona definitions and switching."""

    def __init__(self, config: ConfigLoader):
        self.config = config
        self.personas: dict[str, Persona] = {}
        self._load_personas()

    def _load_personas(self):
        """Load personas from config."""
        persona_configs = self.config.personas

        for name, config in persona_configs.items():
            self.personas[name] = Persona.from_dict(config)

        # Ensure default persona exists
        if "default" not in self.personas:
            self.personas["default"] = self._get_default_persona()

    def get(self, name: str) -> Persona | None:
        """Get persona by name."""
        return self.personas.get(name)

    def list_personas(self) -> list[str]:
        """List all persona names."""
        return list(self.personas.keys())

    def add_persona(self, persona: Persona, save: bool = True):
        """Add or update a persona."""
        self.personas[persona.name] = persona

        if save:
            self._save_persona(persona)

    def remove_persona(self, name: str):
        """Remove a persona."""
        if name == "default":
            raise ValueError("Cannot remove default persona")

        self.personas.pop(name, None)
        self._delete_persona(name)

    def reset_to_defaults(self):
        """Reset all personas to defaults."""
        self.personas = self._get_default_personas()
        # Save to config

    @staticmethod
    def _get_default_persona() -> Persona:
        """Get default persona."""
        return Persona(
            name="default",
            description="Balanced general-purpose assistant",
            system_prompt="You are a helpful AI assistant. Provide clear and accurate responses.",
            preferred_backends=["claude", "openai"],
        )

    @staticmethod
    def _get_default_personas() -> dict[str, Persona]:
        """Get all default personas."""
        return {
            "default": PersonaManager._get_default_persona(),
            "code-specialist": Persona(
                name="code-specialist",
                description="Expert software engineer",
                system_prompt="""You are an expert software engineer. You write clean,
                idiomatic, well-tested code. You follow best practices and explain
                your design decisions. You think step-by-step through problems.""",
                preferred_backends=["openai", "claude"],
                temperature=0.3,
                max_tokens=8000,
            ),
            "local-coder": Persona(
                name="local-coder",
                description="Fast local coding assistant",
                system_prompt="""You are a concise coding assistant. Provide direct,
                practical solutions without verbose explanations.""",
                preferred_backends=["ollama"],
                temperature=0.3,
                max_tokens=2000,
                context_window=8192,
                verbosity="concise",
            ),
            "architect": Persona(
                name="architect",
                description="Senior software architect for design and planning",
                system_prompt="""You are a senior software architect with deep expertise
                in system design, architecture patterns, and best practices. You think
                thoroughly about trade-offs, scalability, maintainability, and provide
                detailed technical plans with reasoning.""",
                preferred_backends=["opus"],
                temperature=0.2,
                max_tokens=16000,
                thinking_style="deep_reasoning",
            ),
            "reviewer": Persona(
                name="reviewer",
                description="Code reviewer focused on quality and best practices",
                system_prompt="""You are an experienced code reviewer. You identify bugs,
                security issues, performance problems, and suggest improvements. You are
                constructive and specific in your feedback.""",
                preferred_backends=["claude", "openai"],
                temperature=0.2,
                requires_tools=True,
            ),
            "context-distiller": Persona(
                name="context-distiller",
                description="Distills large contexts into focused, task-relevant summaries",
                system_prompt="""You are a context distillation specialist. Your job is to read
                large amounts of context (conversation history, code, documentation) and extract
                only the most relevant information for the current task.

                Focus on:
                - Key decisions and their rationale
                - Important code patterns and structures
                - Unresolved issues or blockers
                - Critical facts and constraints
                - Recent changes and their impact

                Produce a concise summary that preserves all task-relevant information while
                removing redundancy and tangential details.""",
                preferred_backends=["gemini"],  # Gemini has 1M+ context window
                temperature=0.3,
                max_tokens=4000,
            ),
        }
```

### 5.2 Persona-Based Routing

```python
class BackendRouter:
    """Routes requests to appropriate backends based on context."""

    def __init__(self, config: ConfigLoader, wrapper: LLMClient):
        self.config = config
        self.wrapper = wrapper
        self.current_backend: str = config.get("orchestrator.default_backend", "claude")

        # Define capability-based fallback chains
        self.architecture_chain = ["opus", "claude", "openai", "gemini"]  # Never local
        self.coding_chain = ["openai", "claude", "ollama"]  # Local OK for coding
        self.parsing_chain = ["gemini", "openai", "claude"]  # Fast models first

    def select_backend(
        self,
        messages: list[Message],
        persona: str | None = None,
        task_type: str = "chat",
        exclude_backends: list[str] | None = None,
    ) -> str:
        """
        Select appropriate backend based on request characteristics.

        Routing logic:
        1. Detect task type (architecture/planning, coding, parsing)
        2. Select appropriate capability chain
        3. If persona specified, prioritize its preferences within chain
        4. Check quota/availability of each backend in chain
        5. Return first available backend
        6. Never use local LLM for architecture/planning

        Args:
            messages: Conversation messages
            persona: Optional persona to use
            task_type: Type of task
            exclude_backends: Backends to exclude (e.g., quota exceeded)

        Returns:
            Backend name to use
        """
        exclude_backends = exclude_backends or []

        # Determine task category
        task_category = self._categorize_task(messages, persona)

        # Select appropriate chain based on task
        if task_category == "architecture":
            chain = self.architecture_chain
        elif task_category == "coding":
            chain = self.coding_chain
        elif task_category == "parsing":
            chain = self.parsing_chain
        else:
            chain = self.config.get("orchestrator.fallback_chain", ["claude", "openai", "gemini"])

        # If persona specified, reorder chain to prioritize persona preferences
        if persona:
            persona_obj = self.config.personas.get(persona)
            if persona_obj and persona_obj.preferred_backends:
                # Prioritize persona backends but keep others as fallback
                preferred = [b for b in persona_obj.preferred_backends if b not in exclude_backends]
                fallback = [b for b in chain if b not in preferred and b not in exclude_backends]
                chain = preferred + fallback

        # Check each backend in chain
        for backend_name in chain:
            if backend_name in exclude_backends:
                continue

            # Check if backend is available and under quota
            if self._is_backend_available(backend_name, messages):
                return backend_name

        # Last resort: return first non-excluded backend
        for backend_name in chain:
            if backend_name not in exclude_backends:
                return backend_name

        # Absolute fallback
        return self.current_backend

    def get_fallback_for_quota_exceeded(self, current_backend: str, task_category: str) -> str | None:
        """
        Get fallback backend when current backend exceeds quota.

        Args:
            current_backend: Backend that exceeded quota
            task_category: Type of task (architecture, coding, parsing)

        Returns:
            Next best backend, or None if no fallback available
        """
        # Select chain based on task
        if task_category == "architecture":
            chain = self.architecture_chain
        elif task_category == "coding":
            chain = self.coding_chain
        elif task_category == "parsing":
            chain = self.parsing_chain
        else:
            chain = self.config.get("orchestrator.fallback_chain", [])

        # Find current backend in chain
        try:
            current_idx = chain.index(current_backend)
            # Return next backend in chain
            if current_idx + 1 < len(chain):
                return chain[current_idx + 1]
        except ValueError:
            # Current backend not in chain, return first in chain
            return chain[0] if chain else None

        return None

    def _categorize_task(self, messages: list[Message], persona: str | None = None) -> str:
        """
        Categorize task type from messages and persona.

        Returns:
            "architecture" | "coding" | "parsing" | "general"
        """
        # Check persona first
        if persona:
            if persona in ["architect", "reviewer", "planner"]:
                return "architecture"
            elif persona in ["code-specialist", "local-coder"]:
                return "coding"
            elif persona in ["fast-parser", "context-distiller"]:
                return "parsing"

        # Check message content
        if self._is_planning_task(messages):
            return "architecture"

        if self._is_coding_task(messages):
            return "coding"

        if self._is_parsing_task(messages):
            return "parsing"

        return "general"

    def _is_backend_available(self, backend_name: str, messages: list[Message]) -> bool:
        """Check if backend is available and can handle the request."""
        backend_config = self.config.get(f"backends.{backend_name}", {})

        if not backend_config:
            return False

        # Check context size
        total_tokens = self._estimate_tokens(messages)
        max_context = backend_config.get("max_context_tokens", 8192)

        if total_tokens > max_context * 0.8:  # 80% safety margin
            return False

        # Could add quota checks here via usage tracker

        return True

    def _estimate_tokens(self, messages: list[Message]) -> int:
        """Rough token estimation (4 chars ≈ 1 token)."""
        total_chars = sum(len(msg.content) for msg in messages)
        return total_chars // 4

    def _is_planning_task(self, messages: list[Message]) -> bool:
        """Detect if this is a planning/architecture task."""
        keywords = [
            "plan", "design", "architecture", "architect",
            "strategy", "approach", "structure", "organize",
            "roadmap", "blueprint", "system design"
        ]

        last_user_msg = next(
            (msg.content.lower() for msg in reversed(messages) if msg.role == MessageRole.USER),
            ""
        )

        return any(keyword in last_user_msg for keyword in keywords)

    def _is_coding_task(self, messages: list[Message]) -> bool:
        """Detect if this is a coding task."""
        keywords = [
            "write code", "implement", "function", "class",
            "refactor", "fix bug", "debug", "code review",
            "add feature", "modify", "update code"
        ]

        last_user_msg = next(
            (msg.content.lower() for msg in reversed(messages) if msg.role == MessageRole.USER),
            ""
        )

        return any(keyword in last_user_msg for keyword in keywords)

    def _is_parsing_task(self, messages: list[Message]) -> bool:
        """Detect if this is a parsing/extraction task."""
        keywords = [
            "parse", "extract", "analyze", "summarize",
            "convert to json", "format", "normalize"
        ]

        last_user_msg = next(
            (msg.content.lower() for msg in reversed(messages) if msg.role == MessageRole.USER),
            ""
        )

        return any(keyword in last_user_msg for keyword in keywords)
```

---

## 6. Context Management

The context management system is a critical component of the orchestrator, handling the challenge of working with multiple backends that have vastly different context window sizes (from 8K tokens for local models to 1M+ for Gemini).

**Key Feature: Intelligent Context Distillation**

When context grows beyond a backend's limits, the system automatically leverages Gemini's massive context window to distill the conversation into a focused, task-relevant summary. This allows small/local models to maintain awareness of large projects without losing critical information.

### 6.1 Multi-Tier Context Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Ephemeral Context                     │
│              (Current conversation only)                │
│  • Cleared on reset_context()                           │
│  • Max 50 messages / 100k tokens (configurable)         │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   Session Context                       │
│            (Active session, backend-specific)           │
│  • Per-backend message history                          │
│  • Auto-distilled when exceeding thresholds             │
│  • Cleared on explicit reset or session end             │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│             Context Distillation Layer                  │
│      (Uses Gemini to compress large contexts)           │
│  • Triggered at 50k tokens (configurable)               │
│  • Gemini reads full context (up to 1M+ tokens)         │
│  • Extracts task-relevant info → ~8k token summary      │
│  • Preserves recent messages for continuity             │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Persistent Memory                      │
│      (Long-term facts, project knowledge, history)      │
│  • SQLite database                                      │
│  • Vector embeddings for retrieval                      │
│  • Never cleared (unless explicit purge)                │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Context Manager Implementation

```python
import sqlite3
from collections import deque
from typing import Any

class ContextManager:
    """Manages multi-tier context system."""

    def __init__(self, config: ConfigLoader, orchestrator: "LLMOrchestrator" = None):
        self.config = config
        self.orchestrator = orchestrator  # Reference for calling distillation backend

        # Session context (per-backend)
        self.session_contexts: dict[str, deque[Message]] = {}

        # Persistent memory
        self.memory = PersistentMemory(
            db_path=config.get("context.memory_db_path", "~/.config/blueprint/memory.db")
        )

        # Context limits
        self.max_session_messages = config.get("context.session_max_messages", 50)
        self.max_session_tokens = config.get("context.session_max_tokens", 100000)
        self.summarize_threshold = config.get("context.auto_summarize_threshold", 40)

        # Distillation settings
        self.enable_distillation = config.get("context.enable_distillation", True)
        self.distillation_trigger_tokens = config.get("context.distillation_trigger_tokens", 50000)
        self.distillation_target_tokens = config.get("context.distillation_target_tokens", 8000)
        self.distillation_backend = config.get("context.distillation_backend", "gemini")
        self.distillation_persona = config.get("context.distillation_persona", "context-distiller")

    def add_message(self, message: Message, backend: str | None = None):
        """Add message to session context."""
        key = backend or "global"

        if key not in self.session_contexts:
            self.session_contexts[key] = deque(maxlen=self.max_session_messages)

        self.session_contexts[key].append(message)

        # Check if summarization needed
        if len(self.session_contexts[key]) >= self.summarize_threshold:
            self._summarize_context(key)

    def get_context(
        self,
        backend: str | None = None,
        max_tokens: int | None = None,
        current_task: str | None = None,
    ) -> list[Message]:
        """Get context for backend, respecting token limits."""
        key = backend or "global"
        context = list(self.session_contexts.get(key, []))

        # Estimate total tokens in context
        total_tokens = self._estimate_tokens(context)

        # If context is too large and distillation is enabled, distill it
        if (self.enable_distillation and
            total_tokens > self.distillation_trigger_tokens and
            self.orchestrator is not None and
            current_task is not None):

            context = self._distill_context(context, current_task, backend)

        if max_tokens:
            # Trim context to fit token limit
            context = self._trim_to_tokens(context, max_tokens)

        return context

    def get_relevant_context(
        self,
        query: str,
        backend: str | None = None,
        max_items: int = 5,
    ) -> list[Message]:
        """
        Get relevant context using retrieval.

        Combines:
        1. Recent session context
        2. Retrieved persistent memories
        """
        # Get recent context
        recent = self.get_context(backend)[-10:]  # Last 10 messages

        # Retrieve from persistent memory
        memories = self.memory.retrieve(query, limit=max_items)

        # Convert memories to messages
        memory_messages = [
            Message(MessageRole.SYSTEM, f"[Memory] {mem}")
            for mem in memories
        ]

        return memory_messages + recent

    def clear_backend_context(self, backend: str):
        """Clear session context for specific backend."""
        self.session_contexts.pop(backend, None)

    def clear_all(self):
        """Clear all session contexts."""
        self.session_contexts.clear()

    def _summarize_context(self, key: str):
        """Summarize old context to save tokens."""
        context = list(self.session_contexts[key])

        # Keep recent messages, summarize older ones
        keep_recent = 10
        to_summarize = context[:-keep_recent]
        recent = context[-keep_recent:]

        if not to_summarize:
            return

        # Use fast model to generate summary
        summarization_backend = self.config.get("context.summarization_backend", "gemini")
        # ... call LLM to summarize to_summarize ...

        # Replace old messages with summary
        summary_msg = Message(
            MessageRole.SYSTEM,
            f"[Previous conversation summary]: {summary_content}"
        )

        self.session_contexts[key] = deque([summary_msg] + recent, maxlen=self.max_session_messages)

    def _trim_to_tokens(self, messages: list[Message], max_tokens: int) -> list[Message]:
        """Trim message list to fit token budget."""
        # Simple implementation: estimate tokens and trim from start
        total_tokens = 0
        result = []

        for msg in reversed(messages):
            msg_tokens = len(msg.content) // 4  # Rough estimate
            if total_tokens + msg_tokens > max_tokens:
                break
            result.insert(0, msg)
            total_tokens += msg_tokens

        return result

    def _estimate_tokens(self, messages: list[Message]) -> int:
        """Estimate total tokens in message list."""
        total_chars = sum(len(msg.content) for msg in messages)
        return total_chars // 4  # Rough estimate: 4 chars ≈ 1 token

    def _distill_context(
        self,
        context: list[Message],
        current_task: str,
        backend: str | None = None,
    ) -> list[Message]:
        """
        Distill large context using Gemini's large context window.

        This method sends the entire context to Gemini (which can handle 1M+ tokens)
        along with the current task, and asks it to extract only the relevant
        information needed for the task.

        Args:
            context: Full conversation context
            current_task: Description of the current task
            backend: Target backend (to understand its constraints)

        Returns:
            Distilled context as a smaller list of messages
        """
        # Build distillation prompt
        context_text = self._format_context_for_distillation(context)

        distillation_prompt = f"""You are analyzing a large conversation history to extract only the information relevant to the current task.

**Current Task:**
{current_task}

**Full Context:**
{context_text}

**Instructions:**
Extract and summarize only the information from the context that is relevant to completing the current task. Focus on:
1. Key decisions and rationale that affect the current task
2. Important code patterns, structures, or constraints
3. Unresolved issues or blockers related to the task
4. Critical facts, requirements, or user preferences
5. Recent changes that impact the current work

Ignore:
- Tangential discussions not related to the task
- Resolved issues
- Redundant information
- Verbose explanations that can be condensed

Provide a concise summary (target: ~{self.distillation_target_tokens} tokens) that preserves all task-relevant context."""

        try:
            # Call distillation backend (Gemini) with special persona
            original_persona = None
            if self.distillation_backend in self.orchestrator._backends:
                distill_backend = self.orchestrator._backends[self.distillation_backend]
                original_persona = distill_backend.persona

                # Temporarily switch to distillation persona
                distill_persona = self.orchestrator.persona_manager.get(self.distillation_persona)
                if distill_persona:
                    distill_backend.persona = distill_persona

            # Make the distillation call
            response = self.orchestrator.chat(
                message=distillation_prompt,
                backend=self.distillation_backend,
                include_context=False,  # Don't include context in distillation request!
            )

            # Restore original persona
            if original_persona:
                distill_backend.persona = original_persona

            # Convert distilled summary into a system message
            distilled_msg = Message(
                MessageRole.SYSTEM,
                f"[Distilled Context - {len(context)} messages compressed]\n\n{response.content}"
            )

            # Keep very recent messages (last 3-5) for continuity
            recent_messages = context[-3:]

            return [distilled_msg] + recent_messages

        except Exception as e:
            # If distillation fails, fall back to simple trimming
            print(f"Warning: Context distillation failed: {e}")
            return self._trim_to_tokens(context, self.distillation_target_tokens)

    def _format_context_for_distillation(self, messages: list[Message]) -> str:
        """Format message history as text for distillation."""
        formatted = []

        for i, msg in enumerate(messages, 1):
            role = msg.role.value.upper()
            content = msg.content[:10000]  # Cap individual messages at 10k chars

            formatted.append(f"[Message {i} - {role}]\n{content}\n")

        return "\n".join(formatted)

class PersistentMemory:
    """
    Long-term persistent memory using SQLite + embeddings.

    Stores:
    - Project facts
    - Historical context
    - Learned patterns
    - User preferences
    """

    def __init__(self, db_path: str):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self._initialize_schema()

    def _initialize_schema(self):
        """Create tables if not exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                embedding BLOB,  -- Serialized numpy array
                tags TEXT,       -- JSON array of tags
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories(tags)
        """)
        self.conn.commit()

    def store(self, key: str, value: Any, tags: list[str] | None = None):
        """Store a memory."""
        import json

        # Generate embedding (using a lightweight model or API)
        embedding = self._generate_embedding(str(value))

        self.conn.execute("""
            INSERT INTO memories (key, value, embedding, tags)
            VALUES (?, ?, ?, ?)
        """, (
            key,
            str(value),
            self._serialize_embedding(embedding),
            json.dumps(tags or [])
        ))
        self.conn.commit()

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        """Retrieve relevant memories using embedding similarity."""
        query_embedding = self._generate_embedding(query)

        # Get all memories (in production, use approximate NN search)
        cursor = self.conn.execute("SELECT value, embedding FROM memories")

        results = []
        for value, embedding_blob in cursor:
            embedding = self._deserialize_embedding(embedding_blob)
            similarity = self._cosine_similarity(query_embedding, embedding)
            results.append((similarity, value))

        # Sort by similarity and return top k
        results.sort(reverse=True, key=lambda x: x[0])

        # Update access stats
        # ...

        return [value for _, value in results[:limit]]

    def _generate_embedding(self, text: str) -> Any:
        """Generate embedding vector for text."""
        # Option 1: Use OpenAI embeddings API
        # Option 2: Use sentence-transformers locally
        # Option 3: Simple TF-IDF (placeholder)
        # For now, placeholder
        return [0.0] * 384  # Typical embedding dimension

    def _serialize_embedding(self, embedding: Any) -> bytes:
        """Serialize embedding to bytes."""
        import pickle
        return pickle.dumps(embedding)

    def _deserialize_embedding(self, blob: bytes) -> Any:
        """Deserialize embedding from bytes."""
        import pickle
        return pickle.loads(blob)

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between vectors."""
        import math
        dot_product = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        return dot_product / (mag_a * mag_b) if mag_a and mag_b else 0.0
```

---

## 7. Tool Execution & Permissions

### 7.1 Tool Registry & Execution

```python
from typing import Callable, Awaitable
from dataclasses import dataclass, field
import asyncio
import subprocess
from pathlib import Path

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON schema
    handler: Callable[[dict], Any]
    requires_approval: bool = True
    category: str = "general"
    timeout_seconds: int = 300

    def to_llm_schema(self) -> dict:
        """Convert to LLM function schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

class ToolExecutor:
    """Safe tool execution with permission management."""

    def __init__(self, config: ConfigLoader):
        self.config = config
        self.registry: dict[str, Tool] = {}
        self.permission_manager = PermissionManager(config)

        # Pending approvals
        self.pending_approvals: dict[str, ToolCall] = {}

        # Register built-in tools
        self._register_builtin_tools()

    def register(self, tool: Tool):
        """Register a tool."""
        self.registry[tool.name] = tool

    def unregister(self, name: str):
        """Unregister a tool."""
        self.registry.pop(name, None)

    def get_enabled_tools(self) -> list[Tool]:
        """Get list of enabled tools."""
        return list(self.registry.values())

    def execute(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a tool call with permission checking.

        Flow:
        1. Check if tool exists
        2. Check permissions
        3. If manual approval needed, queue and wait
        4. Execute in sandbox
        5. Return result
        """
        tool = self.registry.get(tool_call.name)
        if not tool:
            return ToolResult(
                tool_call_id=tool_call.id,
                result=None,
                error=f"Unknown tool: {tool_call.name}",
                approved=False,
            )

        # Check permissions
        permission_mode = self.config.get("tools.permission_mode", "manual")

        if permission_mode == "deny":
            return ToolResult(
                tool_call_id=tool_call.id,
                result=None,
                error="Tool execution denied by policy",
                approved=False,
            )

        if permission_mode == "manual" and tool.requires_approval:
            # Queue for approval
            self.pending_approvals[tool_call.id] = tool_call

            # Request approval from user (via callback/UI)
            approved = self.permission_manager.request_approval(tool_call, tool)

            if not approved:
                return ToolResult(
                    tool_call_id=tool_call.id,
                    result=None,
                    error="Tool execution denied by user",
                    approved=False,
                )

        elif permission_mode == "auto":
            # Check whitelist
            if not self.permission_manager.is_whitelisted(tool_call, tool):
                return ToolResult(
                    tool_call_id=tool_call.id,
                    result=None,
                    error="Tool not whitelisted for auto-execution",
                    approved=False,
                )

        # Execute
        try:
            result = self._execute_sandboxed(tool, tool_call.arguments)
            return ToolResult(
                tool_call_id=tool_call.id,
                result=result,
                approved=True,
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                result=None,
                error=str(e),
                approved=True,
            )

    def _execute_sandboxed(self, tool: Tool, arguments: dict) -> Any:
        """Execute tool with sandboxing and timeout."""
        # Validate arguments against schema
        # ... JSON schema validation ...

        # Execute with timeout
        try:
            if asyncio.iscoroutinefunction(tool.handler):
                return asyncio.run(
                    asyncio.wait_for(
                        tool.handler(arguments),
                        timeout=tool.timeout_seconds
                    )
                )
            else:
                # Run in thread pool with timeout
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(tool.handler, arguments)
                    return future.result(timeout=tool.timeout_seconds)
        except TimeoutError:
            raise TimeoutError(f"Tool {tool.name} exceeded timeout of {tool.timeout_seconds}s")

    def _register_builtin_tools(self):
        """Register built-in tools."""
        # File operations
        self.register(Tool(
            name="read_file",
            description="Read contents of a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"}
                },
                "required": ["path"]
            },
            handler=self._read_file_handler,
            requires_approval=False,  # Reading is safe
        ))

        self.register(Tool(
            name="write_file",
            description="Write content to a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            },
            handler=self._write_file_handler,
            requires_approval=True,  # Writing requires approval
        ))

        self.register(Tool(
            name="list_directory",
            description="List files in a directory",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            },
            handler=self._list_directory_handler,
            requires_approval=False,
        ))

        # Shell execution
        self.register(Tool(
            name="run_shell_command",
            description="Execute a shell command",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "cwd": {"type": "string"}
                },
                "required": ["command"]
            },
            handler=self._shell_handler,
            requires_approval=True,  # Shell commands always need approval
            timeout_seconds=600,
        ))

        # ... more tools ...

    def _read_file_handler(self, args: dict) -> str:
        """Read file handler."""
        path = Path(args["path"])
        return path.read_text()

    def _write_file_handler(self, args: dict) -> str:
        """Write file handler."""
        path = Path(args["path"])
        path.write_text(args["content"])
        return f"Wrote {len(args['content'])} characters to {path}"

    def _list_directory_handler(self, args: dict) -> list[str]:
        """List directory handler."""
        path = Path(args["path"])
        return [str(p) for p in path.iterdir()]

    def _shell_handler(self, args: dict) -> str:
        """Shell command handler."""
        result = subprocess.run(
            args["command"],
            shell=True,
            capture_output=True,
            text=True,
            cwd=args.get("cwd"),
            timeout=600,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {result.stderr}")

        return result.stdout

class PermissionManager:
    """Manages tool execution permissions."""

    def __init__(self, config: ConfigLoader):
        self.config = config
        self.approval_callback: Callable[[ToolCall, Tool], bool] | None = None

    def set_approval_callback(self, callback: Callable[[ToolCall, Tool], bool]):
        """Set callback for manual approval requests."""
        self.approval_callback = callback

    def request_approval(self, tool_call: ToolCall, tool: Tool) -> bool:
        """Request approval for tool execution."""
        if self.approval_callback:
            return self.approval_callback(tool_call, tool)

        # Fallback: CLI prompt
        print(f"\n🔧 Tool execution request:")
        print(f"   Tool: {tool.name}")
        print(f"   Description: {tool.description}")
        print(f"   Arguments: {tool_call.arguments}")
        response = input("   Approve? (y/n): ")
        return response.lower() == "y"

    def is_whitelisted(self, tool_call: ToolCall, tool: Tool) -> bool:
        """Check if tool call matches whitelist patterns."""
        auto_approve_patterns = self.config.get("tools.auto_approve", [])

        for pattern in auto_approve_patterns:
            if self._matches_pattern(tool_call, tool, pattern):
                return True

        return False

    def _matches_pattern(self, tool_call: ToolCall, tool: Tool, pattern: str) -> bool:
        """Check if tool call matches permission pattern."""
        # Pattern format: "tool_name:arg_pattern"
        # Example: "read_file:src/**"

        parts = pattern.split(":", 1)
        tool_pattern = parts[0]

        if tool_pattern != tool.name and tool_pattern != "**":
            return False

        if len(parts) == 1:
            return True  # No argument restriction

        # Check argument pattern (e.g., path glob)
        arg_pattern = parts[1]

        # For file operations, check path
        if "path" in tool_call.arguments:
            from fnmatch import fnmatch
            return fnmatch(tool_call.arguments["path"], arg_pattern)

        return False
```

---

## 8. Orchestration & Routing Logic

### 8.1 Backend Wrapper

```python
class BackendWrapper:
    """
    Wraps a provider adapter from the wrapper layer with orchestrator-specific logic.
    """

    def __init__(
        self,
        name: str,
        provider: str,
        model: str,
        persona: Persona,
        wrapper_client: LLMClient,
        config: dict,
    ):
        self.name = name
        self.provider = provider
        self.model = model
        self.persona = persona
        self.wrapper = wrapper_client
        self.config = config

        # Context-specific to this backend
        self.local_context: deque[Message] = deque(maxlen=100)

    @property
    def max_context_tokens(self) -> int:
        return self.config.get("max_context_tokens", 8192)

    @property
    def supports_streaming(self) -> bool:
        # Query wrapper layer
        models = self.wrapper.listModels(provider=self.provider)
        model_info = next((m for m in models if m.id == self.model), None)
        return model_info.capabilities.get("streaming", False) if model_info else False

    @property
    def supports_tools(self) -> bool:
        models = self.wrapper.listModels(provider=self.provider)
        model_info = next((m for m in models if m.id == self.model), None)
        return model_info.capabilities.get("tool_calling", False) if model_info else False

    def chat(
        self,
        messages: list[Message],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[Tool] | None = None,
    ) -> ChatResponse:
        """Execute chat via wrapper layer."""
        # Convert to wrapper format
        wrapper_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]

        response = self.wrapper.chat(
            messages=wrapper_messages,
            model=self.model,
            provider=self.provider,
            max_tokens=max_tokens or self.persona.max_tokens,
            temperature=temperature or self.persona.temperature,
            tools=[t.to_llm_schema() for t in tools] if tools else None,
        )

        # Convert back to orchestrator format
        return ChatResponse(
            content=response["content"],
            finish_reason=response["finish_reason"],
            usage=UsageInfo(**response["usage"]),
            tool_calls=[ToolCall(**tc) for tc in response.get("tool_calls", [])],
            backend=self.name,
            model=response["model"],
            metadata=ResponseMetadata(**response["metadata"]),
        )

    def stream(
        self,
        messages: list[Message],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[Tool] | None = None,
    ) -> Iterator[StreamChunk]:
        """Execute streaming via wrapper layer."""
        wrapper_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]

        for chunk in self.wrapper.stream(
            messages=wrapper_messages,
            model=self.model,
            provider=self.provider,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            yield StreamChunk(
                delta=chunk["delta"],
                is_done=chunk["is_done"],
                usage=UsageInfo(**chunk["usage"]) if chunk.get("usage") else None,
                tool_call=ToolCall(**chunk["tool_call"]) if chunk.get("tool_call") else None,
                error=chunk.get("error"),
            )

    def reset_context(self):
        """Reset backend-specific context."""
        self.local_context.clear()

    def get_usage(self) -> UsageStats:
        """Get usage stats from wrapper."""
        return self.wrapper.getUsage(provider=self.provider)
```

---

## 9. Streaming Coordination

```python
class StreamCoordinator:
    """Coordinates streaming with validation and error recovery."""

    def stream_with_validation(
        self,
        backend: BackendWrapper,
        messages: list[Message],
        max_tokens: int | None = None,
        temperature: float | None = None,
        tools: list[Tool] | None = None,
    ) -> Iterator[StreamChunk]:
        """
        Stream with automatic validation and retry.

        Features:
        - Accumulates chunks for validation
        - Detects incomplete/malformed output
        - Retries on stream errors
        - Validates final output
        """
        accumulated = []

        try:
            for chunk in backend.stream(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                tools=tools,
            ):
                if chunk.error:
                    yield chunk
                    return

                accumulated.append(chunk.delta)
                yield chunk

                if chunk.is_done:
                    # Validate complete response
                    full_response = "".join(accumulated)
                    if not self._validate_response(full_response, tools):
                        # Invalid - yield error
                        yield StreamChunk(
                            delta="",
                            is_done=True,
                            error=Exception("Invalid or incomplete response"),
                        )

        except Exception as e:
            yield StreamChunk(delta="", is_done=True, error=e)

    def _validate_response(self, response: str, tools: list[Tool] | None) -> bool:
        """Validate complete response."""
        # If expecting JSON/tool call, validate structure
        if tools:
            try:
                import json
                parsed = json.loads(response)
                # Validate tool call structure
                return "tool" in parsed and "arguments" in parsed
            except:
                return False

        # Basic validation
        return len(response.strip()) > 0
```

---

## 10. Usage Tracking & Quotas

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict

@dataclass
class UsageStats:
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    by_backend: Dict[str, dict] = field(default_factory=dict)

    def add(self, backend: str, usage: UsageInfo):
        """Add usage record."""
        self.total_requests += 1
        self.total_tokens += usage.total_tokens
        self.total_cost += usage.estimated_cost or 0.0

        if backend not in self.by_backend:
            self.by_backend[backend] = {
                "requests": 0,
                "tokens": 0,
                "cost": 0.0,
            }

        self.by_backend[backend]["requests"] += 1
        self.by_backend[backend]["tokens"] += usage.total_tokens
        self.by_backend[backend]["cost"] += usage.estimated_cost or 0.0

class UsageTracker:
    """Track usage and enforce quotas."""

    def __init__(self, config: ConfigLoader):
        self.config = config
        self.stats = UsageStats()

        # Time-windowed stats
        self.hourly_stats: deque[tuple[datetime, UsageStats]] = deque()
        self.daily_stats: deque[tuple[datetime, UsageStats]] = deque()

    def record(self, backend: str, usage: UsageInfo):
        """Record usage."""
        self.stats.add(backend, usage)

        # Add to time windows
        now = datetime.now()
        self.hourly_stats.append((now, usage))
        self.daily_stats.append((now, usage))

        # Clean old entries
        self._cleanup_windows()

    def check_quotas(self, backend: str):
        """Check if quotas allow this request."""
        max_hourly = self.config.get("quotas.max_cost_per_hour")
        max_daily = self.config.get("quotas.max_cost_per_day")

        if max_hourly:
            hourly_cost = self._get_cost_in_window(self.hourly_stats)
            if hourly_cost >= max_hourly:
                raise QuotaExceededError(
                    f"Hourly quota exceeded: ${hourly_cost:.2f} / ${max_hourly:.2f}"
                )

        if max_daily:
            daily_cost = self._get_cost_in_window(self.daily_stats)
            if daily_cost >= max_daily:
                raise QuotaExceededError(
                    f"Daily quota exceeded: ${daily_cost:.2f} / ${max_daily:.2f}"
                )

    def get_aggregate_usage(self) -> UsageStats:
        """Get aggregate usage stats."""
        return self.stats

    def reset(self):
        """Reset usage counters."""
        self.stats = UsageStats()
        self.hourly_stats.clear()
        self.daily_stats.clear()

    def _cleanup_windows(self):
        """Remove old entries from time windows."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Remove old hourly entries
        while self.hourly_stats and self.hourly_stats[0][0] < hour_ago:
            self.hourly_stats.popleft()

        # Remove old daily entries
        while self.daily_stats and self.daily_stats[0][0] < day_ago:
            self.daily_stats.popleft()

    def _get_cost_in_window(self, window: deque) -> float:
        """Calculate total cost in time window."""
        return sum(
            usage.estimated_cost or 0.0
            for _, usage in window
        )

class QuotaExceededError(Exception):
    """Raised when quota is exceeded."""
    pass
```

---

## 11. Task & Workflow Management

```python
from enum import Enum
from dataclasses import dataclass
from typing import List

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class TaskStep:
    id: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    suggested_approach: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None

@dataclass
class Task:
    name: str
    description: str
    steps: list[TaskStep]
    context: dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskResult:
    task: Task
    success: bool
    outputs: dict[str, Any]
    errors: list[str]

class TaskCoordinator:
    """Coordinates multi-step task execution."""

    def __init__(self, orchestrator: "LLMOrchestrator"):
        self.orchestrator = orchestrator

    def execute(
        self,
        task: Task,
        backend: str | None = None,
        streaming: bool = True,
    ) -> TaskResult:
        """Execute a multi-step task."""
        outputs = {}
        errors = []

        completed_steps = set()

        while len(completed_steps) < len(task.steps):
            # Find next executable step
            next_step = self._find_next_step(task.steps, completed_steps)

            if not next_step:
                errors.append("Circular dependencies or blocked steps")
                break

            # Execute step
            try:
                next_step.status = TaskStatus.IN_PROGRESS

                result = self.orchestrator.chat(
                    message=self._build_step_prompt(next_step, task.context),
                    backend=backend,
                    include_context=True,
                )

                next_step.result = result.content
                next_step.status = TaskStatus.COMPLETED
                outputs[next_step.id] = result.content
                completed_steps.add(next_step.id)

            except Exception as e:
                next_step.status = TaskStatus.FAILED
                next_step.error = str(e)
                errors.append(f"Step {next_step.id} failed: {e}")
                break

        success = len(completed_steps) == len(task.steps)

        return TaskResult(
            task=task,
            success=success,
            outputs=outputs,
            errors=errors,
        )

    def _find_next_step(
        self,
        steps: list[TaskStep],
        completed: set[str],
    ) -> TaskStep | None:
        """Find next executable step."""
        for step in steps:
            if step.id in completed:
                continue

            # Check if all dependencies are completed
            if all(dep in completed for dep in step.dependencies):
                return step

        return None

    def _build_step_prompt(self, step: TaskStep, context: dict) -> str:
        """Build prompt for executing a step."""
        prompt = f"""
Execute the following task step:

**Step**: {step.description}

**Suggested Approach**: {step.suggested_approach}

**Context**:
{self._format_context(context)}

Provide a detailed implementation.
""".strip()

        return prompt

    def _format_context(self, context: dict) -> str:
        """Format context for prompt."""
        return "\n".join(f"- {k}: {v}" for k, v in context.items())
```

---

## 12. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
- Configuration system (TOML loader, multi-tier)
- Persona system (manager, default personas)
- Backend wrapper integration with LLM wrapper layer
- Basic orchestrator shell

### Phase 2: Context Management (Week 2-3)
- Session context manager
- Persistent memory (SQLite + basic retrieval)
- Context trimming and summarization
- Multi-backend context isolation
- Context distillation using Gemini for large contexts

### Phase 3: Tool System (Week 3-4)
- Tool registry and executor
- Permission manager (manual/auto modes)
- Built-in tools (file ops, shell, git)
- Sandboxing and timeout enforcement

### Phase 4: Routing & Streaming (Week 4-5)
- Backend router with intelligent selection
- Stream coordinator with validation
- Persona-based routing
- Fallback logic

### Phase 5: Usage & Quotas (Week 5)
- Usage tracker with time windows
- Quota enforcement
- Cost estimation
- Metrics export

### Phase 6: Task Workflows (Week 6)
- Task coordinator
- Multi-step execution
- Dependency resolution
- Planning mode integration

### Phase 7: Testing & Polish (Week 7-8)
- Unit tests for all modules
- Integration tests
- CLI interface
- Documentation
- Example scripts

---

## 13. Example Usage

### 13.1 Basic Chat with Auto-Routing

```python
from blueprint.orchestrator import LLMOrchestrator

# Initialize
orchestrator = LLMOrchestrator()

# Simple chat - auto-routes to appropriate backend
response = orchestrator.chat("Explain Python decorators")
print(response.content)

# Streaming
for chunk in orchestrator.stream("Write a binary search implementation"):
    print(chunk.delta, end="", flush=True)
```

### 13.2 Persona Switching

```python
# Switch to code specialist persona
orchestrator.switch_persona("code-specialist")

response = orchestrator.chat("Review this code for bugs: ...")
print(response.content)

# Switch to architect for planning
orchestrator.switch_persona("architect")
plan = orchestrator.plan_task(
    goal="Add authentication system",
    requirements=["JWT", "RBAC", "Password hashing"],
)
```

### 13.3 Tool Execution

```python
# Register custom tool
orchestrator.register_tool(Tool(
    name="run_tests",
    description="Run project tests",
    parameters={
        "type": "object",
        "properties": {
            "test_path": {"type": "string"}
        }
    },
    handler=lambda args: subprocess.run(["pytest", args["test_path"]]),
    requires_approval=True,
))

# Enable auto-approval mode
orchestrator.set_tool_permission_mode("auto")

# Chat with tools
response = orchestrator.chat(
    "Run the tests in tests/unit",
    tools=orchestrator.tool_executor.get_enabled_tools(),
)
```

### 13.4 Multi-Step Task Execution

```python
# Plan a task
task = orchestrator.plan_task(
    goal="Refactor authentication module",
    requirements=[
        "Improve code organization",
        "Add unit tests",
        "Update documentation",
    ],
)

# Execute the plan
result = orchestrator.execute_task(task, streaming=True)

if result.success:
    print("Task completed successfully!")
    for step_id, output in result.outputs.items():
        print(f"\n--- {step_id} ---\n{output}")
else:
    print("Task failed:", result.errors)
```

### 13.5 Context Management

```python
# Add to persistent memory
orchestrator.add_persistent_memory(
    key="project_architecture",
    value="This project uses Clean Architecture with FastAPI",
    tags=["architecture", "project"]
)

# Retrieve relevant memory
memories = orchestrator.retrieve_memory("What architecture do we use?")

# Reset context for local backend
orchestrator.reset_context(backend="ollama")
```

### 13.6 Usage Monitoring

```python
# Get usage stats
stats = orchestrator.get_usage()
print(f"Total cost: ${stats.total_cost:.2f}")
print(f"Total tokens: {stats.total_tokens}")

for backend, usage in stats.by_backend.items():
    print(f"{backend}: {usage['requests']} requests, ${usage['cost']:.2f}")

# Check health
health = orchestrator.get_health()
for backend, status in health.items():
    print(f"{backend}: {status}")
```

### 13.7 Context Distillation (Large Context Handling)

```python
# When working with large contexts that exceed backend limits,
# the orchestrator automatically uses Gemini to distill context

# Example: Long conversation with local model (limited context)
orchestrator.switch_persona("local-coder")

# After many messages, context grows beyond ollama's 8k limit
for i in range(100):
    orchestrator.chat(f"Step {i}: Implement feature X")

# Next request will automatically trigger distillation
# Gemini reads the full 100-message context and extracts only
# what's relevant to the current task
response = orchestrator.chat(
    "Now refactor the authentication module",
    backend="ollama",  # Small context window
)

# Behind the scenes:
# 1. Orchestrator detects context > 50k tokens (configured threshold)
# 2. Sends full context to Gemini with "context-distiller" persona
# 3. Gemini analyzes and summarizes to ~8k tokens
# 4. Distilled context + recent messages sent to ollama
# 5. Response returned with full context awareness

# Manual distillation for specific use cases
orchestrator.context_manager.enable_distillation = True
distilled = orchestrator.context_manager.get_context(
    backend="ollama",
    current_task="Refactor the authentication module to use JWT tokens"
)

# Configuration options (in config.toml):
# [context]
# enable_distillation = true
# distillation_backend = "gemini"
# distillation_persona = "context-distiller"
# distillation_trigger_tokens = 50000
# distillation_target_tokens = 8000

# Benefits:
# - Use local/small models with large context awareness
# - Reduce costs by not sending full context to expensive models
# - Maintain conversation continuity across context limit boundaries
# - Leverage Gemini's 1M+ token context window for analysis
```

---

## Conclusion

This orchestrator architecture provides:

1. **Unified Multi-LLM Access** - Single Python API across all backends
2. **Intelligent Routing** - Persona and context-aware backend selection
3. **Robust Context Management** - Multi-tier (session + persistent) with limits
4. **Context Distillation** - Automatic use of Gemini's 1M+ context window to distill large conversations into task-relevant summaries for backends with smaller context limits
5. **Safe Tool Execution** - Permission-based with approval workflows
6. **Streaming Support** - With validation and error recovery
7. **Usage Tracking** - Cost monitoring and quota enforcement
8. **Task Workflows** - Multi-step execution with dependencies
9. **Industry-Standard Config** - TOML-based, XDG-compliant, global + local
10. **Persona System** - Specialized roles (code-specialist, architect, context-distiller, etc.) for optimal model selection

### Key Innovation: Context Distillation

The context distillation system solves a critical problem in multi-LLM orchestration: how to use fast, cheap, or local models (with limited context windows) while maintaining awareness of large, complex conversations.

**How it works:**
1. When context exceeds a configured threshold (default: 50k tokens)
2. The full context is sent to Gemini (1M+ token capacity)
3. Gemini, using the "context-distiller" persona, extracts only task-relevant information
4. The distilled summary (~8k tokens) + recent messages are sent to the target backend
5. The smaller model can now work effectively with full context awareness

**Benefits:**
- Use local models (Ollama) for long projects without losing context
- Reduce API costs by sending less data to expensive models
- Maintain continuity across context limit boundaries
- Leverage each model's strengths (Gemini for analysis, others for execution)

The design follows Python best practices, uses type hints throughout, and integrates seamlessly with the LLM wrapper layer designed in `LLM_API_WRAPPER.md`.

## Implementation Checklist
- [ ] Backend interfaces and adapters wired into orchestrator/router
- [ ] Session + persistent context stores with persona injection and distillation
- [ ] Routing/fallback logic with budget awareness and task-type mapping
- [ ] Tool runner with permission modes and audit logging
- [ ] Usage tracking and quota enforcement hooks
- [ ] Task queue with dependency handling and history
- [ ] Streaming validation/recovery paths
- [ ] Documentation and CLI commands (`/stats`, `/mode`, personas)
