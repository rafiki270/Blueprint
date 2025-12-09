"""Tool execution registry for LLM tool-calling."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, MutableMapping, Optional


ToolHandler = Callable[[MutableMapping[str, Any]], Any]


class ToolEngine:
    """Registers and executes tools with optional approval gating."""

    def __init__(self) -> None:
        self._registry: Dict[str, ToolHandler] = {}
        self._approval_mode = "manual"  # "manual" or "trust"
        self._whitelist: set[str] = set()
        self._audit_log: Optional[Path] = None

    def register_tool(self, name: str, handler: ToolHandler) -> None:
        self._registry[name] = handler

    def execute_tool(self, name: str, args: MutableMapping[str, Any]) -> Any:
        if name not in self._registry:
            raise ValueError(f"Unknown tool: {name}")
        if self._approval_mode == "manual" and name not in self._whitelist:
            raise PermissionError(f"Tool {name} requires approval in manual mode.")
        result = self._registry[name](args)
        self._audit(name, args, success=True)
        return result

    def set_mode(self, mode: str) -> None:
        if mode not in {"manual", "trust"}:
            raise ValueError("Mode must be 'manual' or 'trust'")
        self._approval_mode = mode

    def get_mode(self) -> str:
        """Return current approval mode."""
        return self._approval_mode

    def whitelist(self, tool_names: list[str]) -> None:
        self._whitelist.update(tool_names)

    def enable_audit(self, log_path: Path) -> None:
        """Enable audit logging to the given file."""
        self._audit_log = log_path
        self._audit_log.parent.mkdir(parents=True, exist_ok=True)

    def _audit(self, name: str, args: MutableMapping[str, Any], success: bool) -> None:
        """Write an audit line if enabled; keep payload small to avoid leaking secrets."""
        if not self._audit_log:
            return
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool": name,
            "success": success,
            "arg_keys": list(args.keys()),
        }
        try:
            with self._audit_log.open("a", encoding="utf-8") as fp:
                fp.write(f"{entry}\n")
        except OSError:
            # Audit failures should not block tool execution.
            pass
