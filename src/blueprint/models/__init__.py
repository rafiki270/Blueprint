"""LLM adapters and routing."""

from .base import (
    BaseAdapter,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    LLMExecutionException,
    LLMException,
    LLMUnavailableException,
    ModelInfo,
    Provider,
    ProviderHealth,
    StreamChunk,
    ToolCall,
    Usage,
)
from .claude import ClaudeAdapter
from .codex import CodexAdapter, OpenAIAdapter
from .credentials import CredentialsManager
from .deepseek import DeepSeekAdapter, OllamaAdapter
from .gemini import GeminiAdapter
from .router import ModelRole, ModelRouter

# Backwards-compatible aliases for previous naming.
ClaudeCLI = ClaudeAdapter
GeminiCLI = GeminiAdapter
DeepSeekCLI = OllamaAdapter
CodexCLI = OpenAIAdapter
BaseLLM = BaseAdapter

__all__ = [
    "BaseAdapter",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "LLMException",
    "LLMUnavailableException",
    "LLMExecutionException",
    "ModelInfo",
    "Provider",
    "ProviderHealth",
    "StreamChunk",
    "ToolCall",
    "Usage",
    "ClaudeAdapter",
    "OpenAIAdapter",
    "CodexAdapter",
    "OllamaAdapter",
    "DeepSeekAdapter",
    "GeminiAdapter",
    "ModelRouter",
    "ModelRole",
    "CredentialsManager",
    # Legacy exports
    "ClaudeCLI",
    "GeminiCLI",
    "DeepSeekCLI",
    "CodexCLI",
    "BaseLLM",
]
