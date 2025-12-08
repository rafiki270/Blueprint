"""Base abstractions for LLM CLI wrappers."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional


class LLMException(Exception):
    """Base exception for LLM errors."""


class LLMUnavailableException(LLMException):
    """Raised when an LLM CLI is not available."""


class LLMExecutionException(LLMException):
    """Raised when execution of an LLM command fails."""


class BaseLLM(ABC):
    """Base class for all LLM CLI wrappers."""

    def __init__(self, cli_command: str) -> None:
        self.cli_command = cli_command
        self.process: Optional[asyncio.subprocess.Process] = None

    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if LLM CLI is available."""

    async def execute(
        self, prompt: str, stream: bool = True, extra_args: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Execute LLM command with prompt.

        Args:
            prompt: The prompt to send to the LLM.
            stream: Whether to stream output line by line.
            extra_args: Additional CLI arguments to prepend before the prompt.
        """
        if not await self.check_availability():
            raise LLMUnavailableException(f"{self.cli_command} is not available")

        try:
            args = [self.cli_command]
            if extra_args:
                args.extend(extra_args)
            args.append(prompt)

            self.process = await asyncio.create_subprocess_exec(
                *args,
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

    async def _stream_output(self) -> AsyncGenerator[str, None]:
        """Stream stdout line by line."""
        if not self.process or not self.process.stdout:
            return

        while True:
            line = await self.process.stdout.readline()
            if not line:
                break
            yield line.decode(errors="replace").rstrip()

    async def _ensure_success(self) -> None:
        """Ensure process completed successfully after streaming."""
        if not self.process:
            return

        await self.process.wait()
        if self.process.returncode and self.process.returncode != 0:
            stderr_content = ""
            if self.process.stderr:
                stderr_content = (await self.process.stderr.read()).decode(errors="replace")
            raise LLMExecutionException(f"Command failed: {stderr_content}")

    async def stop(self) -> None:
        """Stop the running process gracefully."""
        if not self.process:
            return

        try:
            self.process.terminate()
            await asyncio.wait_for(self.process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            self.process.kill()
            await self.process.wait()
        finally:
            self.process = None

    def is_running(self) -> bool:
        """Check if process is currently running."""
        return self.process is not None and self.process.returncode is None
