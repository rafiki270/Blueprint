"""LLM adapters and routing."""

from .base import (
    BaseAdapter,
    BaseLLM,
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
from .cache import CacheManager
from .client import LLMClient, AdapterFactory
from .claude import ClaudeAdapter
from .codex import CodexAdapter, OpenAIAdapter
from .credentials import CredentialsManager
from .deepseek import DeepSeekAdapter, OllamaAdapter
from .gemini import GeminiAdapter
from .streaming import StreamHandler
from .tool_engine import ToolEngine
from .router import ModelRole, ModelRouter

# Backwards-compatible aliases for previous naming.
ClaudeCLI = ClaudeAdapter
GeminiCLI = GeminiAdapter
DeepSeekCLI = OllamaAdapter
CodexCLI = OpenAIAdapter
BaseLLM = BaseAdapter

__all__ = [
    "BaseAdapter",
    "BaseLLM",
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
    "CacheManager",
    "LLMClient",
    "AdapterFactory",
    "ClaudeAdapter",
    "OpenAIAdapter",
    "CodexAdapter",
    "OllamaAdapter",
    "DeepSeekAdapter",
    "GeminiAdapter",
    "StreamHandler",
    "ToolEngine",
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
