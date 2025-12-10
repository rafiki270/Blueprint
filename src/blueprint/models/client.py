"""Unified LLM client with routing, caching, streaming, and fallback."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict, Iterable, List, MutableMapping, Optional, Sequence

from .base import (
    BaseAdapter,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    LLMException,
    LLMExecutionException,
    Provider,
    StreamChunk,
    ToolCall,
)
from .cache import CacheManager
from ..config import ConfigLoader
from .codex import OpenAIAdapter
from .claude import ClaudeAdapter
from .credentials import CredentialsManager
from .deepseek import OllamaAdapter
from .gemini import GeminiAdapter
from .streaming import StreamHandler
from .tool_engine import ToolEngine
from ..utils.usage_tracker import UsageTracker


class AdapterFactory:
    """Creates provider adapters with shared credential/config objects."""

    def __init__(self, credentials: Optional[CredentialsManager] = None) -> None:
        self.credentials = credentials or CredentialsManager()
        self._cache: Dict[Provider, BaseAdapter] = {}

    def create(self, provider: Provider) -> BaseAdapter:
        if provider in self._cache:
            return self._cache[provider]
        adapter: BaseAdapter
        if provider == Provider.OPENAI:
            adapter = OpenAIAdapter(credentials=self.credentials)
        elif provider == Provider.CLAUDE:
            adapter = ClaudeAdapter(credentials=self.credentials)
        elif provider == Provider.GEMINI:
            adapter = GeminiAdapter(credentials=self.credentials)
        elif provider == Provider.OLLAMA:
            adapter = OllamaAdapter(credentials=self.credentials)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        self._cache[provider] = adapter
        return adapter


class LLMClient:
    """Facade over multiple LLM providers with fallback, caching, and usage tracking."""

    def __init__(
        self,
        fallback_chain: Optional[Sequence[Provider]] = None,
        cache_ttl_seconds: int = 3600,
        cache_max_entries: int = 512,
        config: Optional[ConfigLoader] = None,
    ) -> None:
        self.config = config or ConfigLoader()
        self.credentials = CredentialsManager(self.config)
        self.adapter_factory = AdapterFactory(self.credentials)
        self.stream_handler = StreamHandler()
        self.cache = CacheManager(ttl_seconds=cache_ttl_seconds, max_entries=cache_max_entries)
        self.tool_engine = ToolEngine(config=self.config)
        self.tool_engine.set_auto_approve_patterns(self.config.get("tools.auto_approve", []) or [])
        self.usage_tracker = UsageTracker(feature_dir=None)
        self.fallback_chain = list(fallback_chain) if fallback_chain else [
            Provider.OLLAMA,
            Provider.CLAUDE,
            Provider.OPENAI,
            Provider.GEMINI,
        ]

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a non-streaming request, respecting fallback chain and cache."""
        cache_key = self.cache.get_cache_key(
            {"messages": [m.__dict__ for m in request.messages], "model": request.model, "provider": str(request.metadata)}
        )
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        providers = [request.provider] if request.provider else self.fallback_chain
        last_error: Optional[Exception] = None
        for provider in providers:
            adapter = self.adapter_factory.create(provider)
            try:
                response = await adapter.chat(request)
                self._record_usage(response.provider.value, response.model, response.usage)
                self.cache.set(cache_key, response)
                return response
            except Exception as exc:  # noqa: PERF203
                last_error = exc
                continue
        raise LLMExecutionException(f"All providers failed. Last error: {last_error}")

    async def stream(self, request: ChatRequest) -> AsyncGenerator[StreamChunk, None]:
        """Stream responses with retry/fallback."""
        providers = [request.provider] if request.provider else self.fallback_chain
        adapters = [self.adapter_factory.create(p) for p in providers]
        if not adapters:
            raise LLMExecutionException("No providers configured for streaming.")

        async for chunk in self.stream_handler.handle_stream(
            request=request,
            adapter=adapters[0],
            fallback_adapters=adapters[1:],
        ):
            # Track usage on final chunk if provided
            if chunk.is_done and chunk.usage:
                self._record_usage(chunk.provider.value, chunk.model or request.model or "", chunk.usage)
            yield chunk

    async def list_models(self, provider: Optional[Provider] = None) -> List[Dict[str, str]]:
        """List available models across providers."""
        providers = [provider] if provider else self.fallback_chain
        results: List[Dict[str, str]] = []
        for p in providers:
            try:
                adapter = self.adapter_factory.create(p)
                models = await adapter.list_models()
                for model in models:
                    results.append({"id": model.id, "provider": model.provider.value})
            except LLMException:
                continue
        return results

    async def planning_mode(self, context: MutableMapping[str, object]) -> ChatResponse:
        """Use a heavy model (default: Claude) to generate a structured plan."""
        provider = Provider.CLAUDE if Provider.CLAUDE in self.fallback_chain else self.fallback_chain[0]
        adapter = self.adapter_factory.create(provider)
        prompt = self._build_planning_prompt(context)
        request = ChatRequest(
            messages=[ChatMessage(role="system", content="You are a senior software planner."), ChatMessage(role="user", content=prompt)],
            temperature=0.2,
            max_tokens=1500,
            model=context.get("model"),
        )
        response = await adapter.chat(request)
        self._record_usage(response.provider.value, response.model, response.usage)
        return response

    def set_fallback_chain(self, chain: Sequence[Provider]) -> None:
        self.fallback_chain = list(chain)

    def register_tool(self, name: str, handler) -> None:
        self.tool_engine.register_tool(name, handler)

    async def execute_tool(self, tool_call: ToolCall) -> MutableMapping[str, object]:
        try:
            result = self.tool_engine.execute_tool(tool_call.name, tool_call.arguments)
            return {"toolCallId": tool_call.id, "result": result, "approved": True}
        except Exception as exc:  # noqa: PERF203 - explicit propagation
            return {"toolCallId": tool_call.id, "result": None, "error": str(exc), "approved": False}

    def _record_usage(self, provider: str, model: str, usage: Optional[MutableMapping[str, object]]) -> None:
        try:
            self.usage_tracker.record_usage(provider, model, usage)  # type: ignore[arg-type]
        except Exception:
            # usage tracking should not break client flow
            pass

    def _build_planning_prompt(self, context: MutableMapping[str, object]) -> str:
        goal = context.get("goal", "")
        requirements = context.get("requirements", [])
        constraints = context.get("constraints", [])
        previous = context.get("previousPlans")
        return "\n".join(
            [
                "Generate a structured implementation plan.",
                f"Goal:\n{goal}",
                "Requirements:",
                "\n".join(f"- {req}" for req in requirements) if requirements else "- None provided",
                "Constraints:",
                "\n".join(f"- {c}" for c in constraints) if constraints else "- None provided",
                f"Previous plans: {previous}" if previous else "",
            ]
        )
