"""Tool execution engine with permission management and audit logging."""

from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, MutableMapping, Optional, Sequence

from ..config import ConfigLoader

ToolHandler = Callable[[MutableMapping[str, Any]], Any]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON schema
    handler: ToolHandler
    requires_approval: bool = True
    category: str = "general"
    timeout_seconds: int = 300

    def to_llm_schema(self) -> dict:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


@dataclass
class ToolResult:
    tool_call_id: str
    result: Any
    error: str | None = None
    approved: bool = True


class PermissionManager:
    """Manages tool execution permissions."""

    def __init__(self, config: Optional[ConfigLoader] = None) -> None:
        self.config = config or ConfigLoader()
        self.approval_callback: Callable[[str, Tool, MutableMapping[str, Any]], bool] | None = None
        self.auto_approve_patterns: Sequence[str] = self.config.get("tools.auto_approve", []) or []

    def set_approval_callback(self, callback: Callable[[str, Tool, MutableMapping[str, Any]], bool]) -> None:
        self.approval_callback = callback

    def request_approval(self, tool_name: str, tool: Tool, args: MutableMapping[str, Any]) -> bool:
        if self.approval_callback:
            return self.approval_callback(tool_name, tool, args)
        # CLI fallback
        print(f"\n🔧 Tool execution request: {tool_name}\nArgs: {args}")
        response = input("Approve? (y/n): ")
        return response.strip().lower() == "y"

    def is_whitelisted(self, tool_name: str, args: MutableMapping[str, Any]) -> bool:
        from fnmatch import fnmatch

        for pattern in self.auto_approve_patterns:
            parts = pattern.split(":", 1)
            tool_pattern = parts[0]
            if tool_pattern not in (tool_name, "**"):
                continue
            if len(parts) == 1:
                return True
            arg_pattern = parts[1]
            path_arg = args.get("path")
            if path_arg and fnmatch(str(path_arg), arg_pattern):
                return True
        return False


class ToolEngine:
    """Registers and executes tools with optional approval gating."""

    def __init__(self, config: Optional[ConfigLoader] = None) -> None:
        self.config = config or ConfigLoader()
        self.permission_mode = self.config.get("tools.permission_mode", "manual")
        self.permission_manager = PermissionManager(self.config)
        self._registry: Dict[str, Tool] = {}
        self._whitelist: set[str] = set()
        self._audit_log: Optional[Path] = None
        self._register_builtin_tools()

    def set_mode(self, mode: str) -> None:
        if mode not in {"manual", "auto", "deny", "trust"}:
            raise ValueError("Mode must be 'manual', 'auto', 'deny', or 'trust'")
        self.permission_mode = mode

    def get_mode(self) -> str:
        return self.permission_mode

    def whitelist(self, tool_names: list[str]) -> None:
        self._whitelist.update(tool_names)

    def set_auto_approve_patterns(self, patterns: Sequence[str]) -> None:
        self.permission_manager.auto_approve_patterns = patterns

    def register_tool(self, name: str, handler: ToolHandler, *, description: str = "", parameters: dict | None = None, requires_approval: bool = True, timeout_seconds: int = 300) -> None:
        tool = Tool(
            name=name,
            description=description or name,
            parameters=parameters or {"type": "object", "properties": {}},
            handler=handler,
            requires_approval=requires_approval,
            timeout_seconds=timeout_seconds,
        )
        self._registry[name] = tool

    def execute_tool(self, name: str, args: MutableMapping[str, Any]) -> Any:
        if name not in self._registry:
            raise ValueError(f"Unknown tool: {name}")
        tool = self._registry[name]
        self._enforce_permissions(tool, args)
        result = self._execute_sandboxed(tool, args)
        self._audit(name, args, success=True)
        return result

    def enable_audit(self, log_path: Path) -> None:
        self._audit_log = log_path
        self._audit_log.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _enforce_permissions(self, tool: Tool, args: MutableMapping[str, Any]) -> None:
        if self.permission_mode == "deny":
            raise PermissionError("Tool execution denied by policy.")

        if self.permission_mode == "trust":
            return

        if self.permission_mode == "auto":
            if tool.requires_approval and tool.name not in self._whitelist:
                if not self.permission_manager.is_whitelisted(tool.name, args):
                    raise PermissionError(f"Tool {tool.name} not whitelisted for auto execution.")
            return

        # manual mode
        if tool.requires_approval and tool.name not in self._whitelist:
            approved = self.permission_manager.request_approval(tool.name, tool, args)
            if not approved:
                raise PermissionError(f"Tool {tool.name} execution denied by user.")

    def _execute_sandboxed(self, tool: Tool, args: MutableMapping[str, Any]) -> Any:
        try:
            if asyncio.iscoroutinefunction(tool.handler):
                return asyncio.run(asyncio.wait_for(tool.handler(args), timeout=tool.timeout_seconds))
            # sync handler: run in thread with timeout
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(tool.handler, args)
                return future.result(timeout=tool.timeout_seconds)
        except Exception as exc:
            self._audit(tool.name, args, success=False)
            raise exc

    def _audit(self, name: str, args: MutableMapping[str, Any], success: bool) -> None:
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
            pass

    def _register_builtin_tools(self) -> None:
        """Register built-in tools from the design spec."""
        self.register_tool(
            name="read_file",
            description="Read contents of a file",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path to read"}},
                "required": ["path"],
            },
            handler=self._read_file_handler,
            requires_approval=False,
        )

        self.register_tool(
            name="write_file",
            description="Write content to a file",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
            handler=self._write_file_handler,
            requires_approval=True,
        )

        self.register_tool(
            name="list_directory",
            description="List files in a directory",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=self._list_directory_handler,
            requires_approval=False,
        )

        self.register_tool(
            name="run_shell_command",
            description="Execute a shell command",
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string"}, "cwd": {"type": "string"}},
                "required": ["command"],
            },
            handler=self._shell_handler,
            requires_approval=True,
            timeout_seconds=600,
        )

    # Built-in handlers --------------------------------------------------
    def _read_file_handler(self, args: dict) -> str:
        path = Path(args["path"])
        return path.read_text(encoding="utf-8")

    def _write_file_handler(self, args: dict) -> str:
        path = Path(args["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"], encoding="utf-8")
        return f"Wrote {len(args['content'])} characters to {path}"

    def _list_directory_handler(self, args: dict) -> list[str]:
        path = Path(args["path"])
        return [str(p) for p in path.iterdir()]

    def _shell_handler(self, args: dict) -> str:
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
