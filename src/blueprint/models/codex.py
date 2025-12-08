"""Codex (GPT) CLI wrapper."""

from __future__ import annotations

import asyncio
import json
from typing import Dict, List

from .base import BaseLLM


class CodexCLI(BaseLLM):
    """Wrapper for GPT Codex CLI."""

    def __init__(self, cli_command: str = "codex") -> None:
        super().__init__(cli_command)

    async def check_availability(self) -> bool:
        """Check if codex CLI is available."""
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

    async def review_tasks(self, tasks_json: str, model: str | None = None, extra_args: list[str] | None = None) -> str:
        """Review and refine tasks generated from spec."""
        prompt = f"""Review these tasks and suggest improvements:

Tasks:
{tasks_json}

Provide refined tasks JSON with better organization, clearer descriptions, and proper dependencies."""

        result: List[str] = []
        args: list[str] = []
        if model:
            args.extend(["-m", model])
        if extra_args:
            args.extend(extra_args)

        async for line in self.execute(prompt, stream=False, extra_args=args or None):
            result.append(line)

        return "\n".join(result)

    async def review_code(
        self,
        code: str,
        requirements: str,
        model: str | None = None,
        extra_args: list[str] | None = None,
    ) -> Dict:
        """
        Review generated code.

        Returns:
            Dictionary with 'approved' bool and 'feedback' string.
        """
        prompt = f"""Review this code against requirements:

Requirements:
{requirements}

Code:
{code}

Respond in JSON format:
{{
  \"approved\": true/false,
  \"feedback\": \"Detailed feedback\",
  \"corrections\": [\"List of required corrections\"]
}}"""

        result: List[str] = []
        args: list[str] = []
        if model:
            args.extend(["-m", model])
        if extra_args:
            args.extend(extra_args)

        async for line in self.execute(prompt, stream=False, extra_args=args or None):
            result.append(line)

        return json.loads("\n".join(result))

    async def generate_correction(
        self,
        code: str,
        issue: str,
        model: str | None = None,
        extra_args: list[str] | None = None,
    ) -> str:
        """Generate corrected code."""
        prompt = f"""Fix this issue in the code:

Issue: {issue}

Code:
{code}

Provide the corrected code."""

        result: List[str] = []
        args: list[str] = []
        if model:
            args.extend(["-m", model])
        if extra_args:
            args.extend(extra_args)

        async for line in self.execute(prompt, stream=False, extra_args=args or None):
            result.append(line)

        return "\n".join(result)
