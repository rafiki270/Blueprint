"""Persona definitions and management for the orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Sequence

from ..config import ConfigLoader


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

    def __init__(self, config: Optional[ConfigLoader] = None) -> None:
        self.config = config or ConfigLoader()
        self.personas: Dict[str, Persona] = {p.name: p for p in self._load_personas()}
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

    def _load_personas(self) -> Iterable[Persona]:
        """Load personas from config, falling back to defaults."""
        raw = self.config.personas.get("personas") if hasattr(self.config, "personas") else None
        if not raw:
            raw = self.config._get_default_personas().get("personas", {})  # type: ignore[attr-defined]

        personas: list[Persona] = []
        for name, data in raw.items():
            personas.append(
                Persona(
                    name=name,
                    description=data.get("description", ""),
                    system_prompt=data.get("system_prompt", ""),
                    temperature=float(data.get("temperature", 0.7)),
                    max_tokens=int(data.get("max_tokens", 4000)),
                    preferred_backends=tuple(data.get("preferred_backends", ())),
                )
            )
        return personas
