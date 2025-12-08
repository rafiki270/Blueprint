"""DeepSeek (via Ollama) CLI wrapper."""

from __future__ import annotations

import asyncio
from typing import List

from .base import BaseLLM, LLMExecutionException, LLMUnavailableException


class DeepSeekCLI(BaseLLM):
    """Wrapper for DeepSeek via Ollama."""

    def __init__(self, model: str = "deepseek-coder:14b", cli_command: str = "ollama") -> None:
        super().__init__(cli_command)
        self.model = model

    async def check_availability(self) -> bool:
        """Check if ollama CLI is available.

        We intentionally avoid enforcing model presence to allow users to rely on
        whatever models they've already configured in their local Ollama setup.
        """
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

    async def execute(self, prompt: str, stream: bool = True):
        """Execute with ollama run command."""
        if not await self.check_availability():
            raise LLMUnavailableException(f"Ollama CLI is not available")

        try:
            self.process = await asyncio.create_subprocess_exec(
                self.cli_command,
                "run",
                self.model,
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            if stream:
                async for line in self._stream_output():
                    yield line
                await self._ensure_success()
            else:
                stdout, stderr = await self.process.communicate()
                if self.process.returncode != 0:
                    raise LLMExecutionException(f"Command failed: {stderr.decode(errors='replace')}")
                yield stdout.decode(errors="replace")

        except Exception as exc:
            await self.stop()
            raise LLMExecutionException(f"Execution failed: {exc}") from exc

    async def generate_code(self, task_description: str, context: str = "") -> str:
        """Generate code for a task."""
        prompt = f"""Generate production-ready code for this task:

Task: {task_description}

Context:
{context}

Provide clean, well-documented code."""

        result: List[str] = []
        async for line in self.execute(prompt, stream=True):
            result.append(line)

        return "\n".join(result)

    async def refactor_code(self, code: str, instructions: str) -> str:
        """Refactor existing code."""
        prompt = f"""Refactor this code according to the instructions:

Code:
{code}

Instructions: {instructions}

Provide the refactored code."""

        result: List[str] = []
        async for line in self.execute(prompt, stream=False):
            result.append(line)

        return "\n".join(result)
