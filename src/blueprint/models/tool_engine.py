"""Tool execution registry for LLM tool-calling."""

from __future__ import annotations

from typing import Any, Callable, Dict, MutableMapping, Optional


ToolHandler = Callable[[MutableMapping[str, Any]], Any]


class ToolEngine:
    """Registers and executes tools with optional approval gating."""

    def __init__(self) -> None:
        self._registry: Dict[str, ToolHandler] = {}
        self._approval_mode = "manual"  # "manual" or "trust"
        self._whitelist: set[str] = set()

    def register_tool(self, name: str, handler: ToolHandler) -> None:
        self._registry[name] = handler

    def execute_tool(self, name: str, args: MutableMapping[str, Any]) -> Any:
        if name not in self._registry:
            raise ValueError(f"Unknown tool: {name}")
        if self._approval_mode == "manual" and name not in self._whitelist:
            raise PermissionError(f"Tool {name} requires approval in manual mode.")
        return self._registry[name](args)

    def set_mode(self, mode: str) -> None:
        if mode not in {"manual", "trust"}:
            raise ValueError("Mode must be 'manual' or 'trust'")
        self._approval_mode = mode

    def whitelist(self, tool_names: list[str]) -> None:
        self._whitelist.update(tool_names)
