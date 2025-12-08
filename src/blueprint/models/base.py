"""Shared types and base classes for API-backed LLM adapters."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Mapping, MutableMapping, Optional, Sequence


class LLMException(Exception):
    """Base exception for LLM failures."""


class LLMUnavailableException(LLMException):
    """Raised when an LLM provider cannot be reached or is not configured."""


class LLMExecutionException(LLMException):
    """Raised when a request to an LLM fails."""


class Provider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    OLLAMA = "ollama"


@dataclass
class ChatMessage:
    """Single chat message."""

    role: str
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


@dataclass
class ToolCall:
    """Tool invocation emitted by a model."""

    id: str
    name: str
    arguments: Mapping[str, Any]


@dataclass
class Usage:
    """Token usage details."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: Optional[float] = None


@dataclass
class ChatRequest:
    """Normalized request sent to providers."""

    messages: Sequence[ChatMessage]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    stop: Optional[Sequence[str]] = None
    tools: Optional[Sequence[Mapping[str, Any]]] = None
    metadata: MutableMapping[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    """Normalized chat response."""

    content: str
    provider: Provider
    model: str
    usage: Optional[Usage] = None
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    metadata: MutableMapping[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """Chunk of streamed output."""

    delta: str
    is_done: bool
    provider: Provider
    model: Optional[str] = None
    usage: Optional[Usage] = None
    tool_call: Optional[ToolCall] = None
    error: Optional[Exception] = None


@dataclass
class ModelInfo:
    """Information about an available model."""

    id: str
    provider: Provider
    context_window: Optional[int] = None
    capabilities: Optional[Sequence[str]] = None


@dataclass
class ProviderHealth:
    """Lightweight health check status."""

    provider: Provider
    status: str
    latency_ms: Optional[float] = None


class BaseAdapter(abc.ABC):
    """Abstract base for provider adapters."""

    provider: Provider

    @abc.abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a non-streaming chat request."""

    @abc.abstractmethod
    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[StreamChunk, None]:
        """Stream chat output incrementally."""

    @abc.abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """List models accessible to this provider."""

    @abc.abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Return provider reachability status."""

    async def execute(self, prompt: str, stream: bool = True, model: Optional[str] = None):
        """
        Compatibility helper: send a simple user prompt and yield text.

        Streamed execution yields incremental text deltas; non-streaming yields a single string.
        """
        request = ChatRequest(messages=[ChatMessage(role="user", content=prompt)], model=model)
        if stream:
            async for chunk in self.stream_chat(request):
                if chunk.delta:
                    yield chunk.delta
            return

        response = await self.chat(request)
        yield response.content

    async def get_context_limit(self) -> Optional[int]:
        """Return an optional context window if discoverable."""
        return None
