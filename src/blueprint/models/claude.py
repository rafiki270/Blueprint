"""Claude CLI wrapper."""

from __future__ import annotations

import asyncio

from .base import BaseLLM


class ClaudeCLI(BaseLLM):
    """Wrapper for Claude CLI."""

    def __init__(self, cli_command: str = "claude") -> None:
        super().__init__(cli_command)

    async def check_availability(self) -> bool:
        """Check if claude CLI is available."""
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

    async def generate_spec(
        self,
        brief: str,
        model: str | None = None,
        output_format: str | None = None,
        extra_args: list[str] | None = None,
    ) -> str:
        """Generate technical specification from brief."""
        prompt = f"""You are a system architect. Convert this brief into a detailed technical specification.

Brief:
{brief}

Generate a comprehensive specification including:
- Overview
- Architecture
- API definitions
- Data models
- Test plan
- Implementation steps

Format as markdown."""

        result = []
        args: list[str] = ["-p"]  # non-interactive
        if model:
            args.extend(["--model", model])
        if output_format:
            args.extend(["--output-format", output_format])
        if extra_args:
            args.extend(extra_args)

        async for line in self.execute(prompt, stream=False, extra_args=args):
            result.append(line)

        return "\n".join(result)
