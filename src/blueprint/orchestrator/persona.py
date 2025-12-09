"""Persona definitions and management for the orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Sequence


@dataclass
class Persona:
    """Represents a reusable system prompt and routing preferences."""

    name: str
    description: str
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 4000
    preferred_backends: Sequence[str] = ()


class PersonaManager:
    """Stores available personas and tracks the active one."""

    def __init__(self) -> None:
        self.personas: Dict[str, Persona] = {p.name: p for p in self._default_personas()}
        self._active: str = "general-assistant"

    def set_active(self, name: str) -> Persona:
        """Select the active persona."""
        if name not in self.personas:
            raise KeyError(f"Unknown persona: {name}")
        self._active = name
        return self.personas[name]

    def get_active(self) -> Persona:
        """Return the current persona."""
        return self.personas[self._active]

    def get(self, name: str | None) -> Persona:
        """Return a persona by name, falling back to the active one."""
        if name is None:
            return self.get_active()
        if name not in self.personas:
            raise KeyError(f"Unknown persona: {name}")
        return self.personas[name]

    def list_names(self) -> Iterable[str]:
        """List available persona names."""
        return self.personas.keys()

    def _default_personas(self) -> Iterable[Persona]:
        """Built-in personas mirroring the orchestrator spec."""
        return [
            Persona(
                name="general-assistant",
                description="Balanced general-purpose assistant.",
                system_prompt=(
                    "You are a helpful AI assistant. Provide clear, accurate, and concise answers. "
                    "Think step-by-step and explain reasoning briefly when helpful."
                ),
                temperature=0.7,
                max_tokens=4000,
                preferred_backends=("claude", "openai"),
            ),
            Persona(
                name="code-specialist",
                description="Expert at writing, reviewing, and debugging code.",
                system_prompt=(
                    "You are an expert software engineer. You write clean, idiomatic, well-tested code. "
                    "You follow best practices and explain design decisions briefly."
                ),
                temperature=0.3,
                max_tokens=8000,
                preferred_backends=("openai", "claude"),
            ),
            Persona(
                name="fast-parser",
                description="Focused on quick parsing and structured output.",
                system_prompt=(
                    "You are a fast, efficient parser. Extract structured information accurately and return "
                    "well-formatted JSON responses when possible."
                ),
                temperature=0.2,
                max_tokens=2000,
                preferred_backends=("gemini", "openai"),
            ),
            Persona(
                name="context-distiller",
                description="Distills large contexts into task-relevant summaries.",
                system_prompt=(
                    "You are a context distillation specialist. Read large amounts of context and extract only "
                    "the most relevant information for the current task. Focus on key decisions, unresolved issues, "
                    "critical facts, and recent changes."
                ),
                temperature=0.3,
                max_tokens=4000,
                preferred_backends=("gemini",),
            ),
            Persona(
                name="local-coder",
                description="Local model for quick coding tasks.",
                system_prompt=(
                    "You are a concise coding assistant running locally. Provide practical code solutions without fluff."
                ),
                temperature=0.3,
                max_tokens=2000,
                preferred_backends=("ollama",),
            ),
            Persona(
                name="architect",
                description="Deep reasoning and system design.",
                system_prompt=(
                    "You are a senior software architect. Think thoroughly about trade-offs, scalability, "
                    "and maintainability. Provide detailed technical plans."
                ),
                temperature=0.2,
                max_tokens=16000,
                preferred_backends=("claude", "openai"),
            ),
        ]
