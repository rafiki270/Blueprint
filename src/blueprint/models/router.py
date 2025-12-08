"""Model routing utilities."""

from __future__ import annotations

from enum import Enum

from .claude import ClaudeCLI
from .codex import CodexCLI
from .deepseek import DeepSeekCLI
from .gemini import GeminiCLI
from .base import BaseLLM
from ..config import Config


class ModelRole(Enum):
    ARCHITECT = "architecture"
    CODER = "code"
    BOILERPLATE = "boilerplate"
    REVIEWER = "review"
    PARSER = "parser"


class ModelRouter:
    """Routes tasks to appropriate LLM models."""

    def __init__(self, config: Config) -> None:
        self.config = config
        cli_commands = config.get("cli_commands", {})
        self.claude = ClaudeCLI(cli_commands.get("claude", "claude"))
        self.gemini = GeminiCLI(cli_commands.get("gemini", "gemini"))
        self.deepseek = DeepSeekCLI(
            model=config.get("local_model", "deepseek-coder:14b"),
            cli_command=cli_commands.get("ollama", "ollama"),
        )
        self.codex = CodexCLI(cli_commands.get("codex", "codex"))

        self.ollama_available: bool | None = None
        self.max_chars_local = config.get("max_chars_local_model", 20000)

    async def check_availability(self) -> None:
        """Check which models are available."""
        self.ollama_available = await self.deepseek.check_availability()

        if not self.ollama_available and self.config.get("ollama_unavailable_warning", True):
            print("WARNING: Ollama is not available. Local coding disabled.")
            print("Blueprint will use Gemini for code generation.")

    async def route(self, role: ModelRole, content_size: int = 0) -> BaseLLM:
        """
        Route to appropriate model based on role and content size.

        Args:
            role: The model role needed.
            content_size: Size of content in characters.
        """
        if self.ollama_available is None:
            await self.check_availability()

        if role == ModelRole.ARCHITECT:
            return self.claude
        if role == ModelRole.REVIEWER:
            return self.codex
        if role == ModelRole.BOILERPLATE or content_size > self.max_chars_local:
            return self.gemini
        if role == ModelRole.CODER:
            if self.ollama_available and content_size <= self.max_chars_local:
                return self.deepseek
            return self.gemini
        if role == ModelRole.PARSER:
            if content_size > self.max_chars_local:
                return self.gemini
            if self.ollama_available:
                return self.deepseek
            return self.gemini

        # Default fallback
        return self.gemini

    def get_routing_stats(self) -> dict:
        """Get statistics for routing suggestions."""
        return {
            "ollama_available": self.ollama_available,
            "max_chars_local": self.max_chars_local,
            "models": {
                "claude": "available",
                "gemini": "available",
                "deepseek": "available" if self.ollama_available else "unavailable",
                "codex": "available",
            },
        }
