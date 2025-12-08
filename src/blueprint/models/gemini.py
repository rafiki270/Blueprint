"""Gemini CLI wrapper."""

from __future__ import annotations

import asyncio
from typing import Dict, List

from .base import BaseLLM


class GeminiCLI(BaseLLM):
    """Wrapper for Gemini CLI."""

    def __init__(self, cli_command: str = "gemini") -> None:
        super().__init__(cli_command)

    async def check_availability(self) -> bool:
        """Check if gemini CLI is available."""
        try:
            process = await asyncio.create_subprocess_exec(
                "which",
                self.cli_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.wait()
            return process.returncode == 0
        except Exception:
            return False

    async def parse_spec_to_tasks(
        self,
        spec: str,
        model: str | None = None,
        sandbox: bool = False,
        output_format: str | None = None,
        extra_args: list[str] | None = None,
    ) -> str:
        """Parse specification into structured tasks JSON (as string)."""
        prompt = f"""Convert this specification into structured tasks JSON.

Specification:
{spec}

Return ONLY valid JSON array with tasks in this format:
[
  {{
    \"id\": \"task-1\",
    \"title\": \"Task title\",
    \"description\": \"Detailed description\",
    \"type\": \"code|boilerplate|review|architecture\"
  }}
]"""

        args: list[str] = []
        if model:
            args.extend(["-m", model])
        if sandbox:
            args.append("--sandbox")
        if output_format:
            args.extend(["-o", output_format])
        if extra_args:
            args.extend(extra_args)
        # Prefer positional prompt; fall back to -p for compatibility.
        args.append("-p")

        result: List[str] = []
        async for line in self.execute(prompt, stream=False, extra_args=args):
            result.append(line)

        return "\n".join(result)

    async def generate_boilerplate(
        self,
        task_description: str,
        model: str | None = None,
        sandbox: bool = False,
        output_format: str | None = None,
        extra_args: list[str] | None = None,
    ) -> str:
        """Generate boilerplate code for a task."""
        prompt = f"""Generate boilerplate code for this task:

{task_description}

Provide complete, production-ready code."""

        args: list[str] = []
        if model:
            args.extend(["-m", model])
        if sandbox:
            args.append("--sandbox")
        if output_format:
            args.extend(["-o", output_format])
        if extra_args:
            args.extend(extra_args)

        result: List[str] = []
        async for line in self.execute(prompt, stream=True, extra_args=args or None):
            result.append(line)

        return "\n".join(result)
