"""High-level orchestrator that wraps routing, context, personas, and tooling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import AsyncGenerator, Iterable, List, MutableMapping, Optional, Sequence

from ..config import Config
from ..models.base import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    Provider,
    StreamChunk,
)
from ..models.client import LLMClient
from ..models.router import ModelRole, ModelRouter
from ..models.tool_engine import ToolHandler
from ..utils.usage_tracker import QuotaExceededError, UsageTracker
from .context import ContextManager
from .persona import Persona, PersonaManager


BACKEND_ALIASES: MutableMapping[str, Provider] = {
    "claude": Provider.CLAUDE,
    "anthropic": Provider.CLAUDE,
    "openai": Provider.OPENAI,
    "codex": Provider.OPENAI,
    "gemini": Provider.GEMINI,
    "google": Provider.GEMINI,
    "ollama": Provider.OLLAMA,
    "deepseek": Provider.OLLAMA,
}


class LLMOrchestrator:
    """Core orchestrator API used by the CLI, TUI, and automation layers."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config()
        self.client = LLMClient()
        self.router = ModelRouter(self.config)
        self.context_manager = ContextManager(self.config)
        self.personas = PersonaManager()
        self.usage_tracker: UsageTracker = self.client.usage_tracker
        self.usage_tracker.set_limits(
            max_cost=self.config.get("quota_max_cost"),
            max_tokens_per_request=self.config.get("quota_max_tokens_per_request"),
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def chat(
        self,
        message: str | Sequence[ChatMessage],
        *,
        backend: str | None = None,
        persona: str | None = None,
        include_context: bool = True,
        tools: Sequence[MutableMapping[str, object]] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        task_type: str = "chat",
    ) -> ChatResponse:
        """Send a single-turn request with context, persona, and routing."""
        provider = await self._select_provider(backend, persona, message, task_type)
        persona_obj = self.personas.get(persona)
        messages = self._prepare_messages(message, provider, persona_obj, include_context)
        estimated_tokens = self._estimate_tokens(messages)
        self.usage_tracker.check_request_budget(estimated_tokens)

        response = await self._chat_with_fallback(
            messages=messages,
            preferred_provider=provider,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        if response.tool_calls:
            response = await self._handle_tool_calls(
                messages=messages,
                initial=response,
                provider=provider,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        self._record_context(provider, persona_obj, message, response)
        return response

    async def stream(
        self,
        message: str | Sequence[ChatMessage],
        *,
        backend: str | None = None,
        persona: str | None = None,
        include_context: bool = True,
        tools: Sequence[MutableMapping[str, object]] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        task_type: str = "chat",
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream a response while building context once the stream completes."""
        provider = await self._select_provider(backend, persona, message, task_type)
        persona_obj = self.personas.get(persona)
        messages = self._prepare_messages(message, provider, persona_obj, include_context)
        estimated_tokens = self._estimate_tokens(messages)
        self.usage_tracker.check_request_budget(estimated_tokens)

        full_delta: List[str] = []
        request = ChatRequest(
            messages=messages,
            provider=provider,
            model=self._default_model(provider),
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature or persona_obj.temperature,
        )

        async for chunk in self.client.stream(request):
            if chunk.delta:
                full_delta.append(chunk.delta)
            yield chunk

        if include_context and full_delta:
            synthetic_response = ChatResponse(
                content="".join(full_delta),
                provider=provider,
                model=request.model or "",
                usage=None,
            )
            self._record_context(provider, persona_obj, message, synthetic_response)

    def register_tool(self, name: str, handler: ToolHandler, *, auto_approve: bool = False) -> None:
        """Register a tool callable and optionally whitelist it."""
        self.client.register_tool(name, handler)
        if auto_approve:
            self.client.tool_engine.whitelist([name])
        self.client.tool_engine.enable_audit(self._audit_log_path())

    def set_tool_mode(self, mode: str) -> None:
        """Switch tool approval mode ('manual' or 'trust')."""
        self.client.tool_engine.set_mode(mode)

    def get_tool_mode(self) -> str:
        """Return current tool approval mode."""
        return self.client.tool_engine.get_mode()

    def remember(self, text: str, tags: Sequence[str] | None = None) -> None:
        """Persist a fact for later retrieval."""
        self.context_manager.remember(text, tags)

    def get_usage_stats(self) -> MutableMapping[str, float]:
        """Expose aggregate usage for UI/CLI commands like /stats."""
        return self.usage_tracker.get_stats()

    def set_persona(self, name: str) -> Persona:
        """Switch the active persona."""
        return self.personas.set_active(name)

    def get_active_persona(self) -> Persona:
        """Return the current persona."""
        return self.personas.get_active()

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    async def _select_provider(
        self,
        backend: str | None,
        persona: str | None,
        message: str | Sequence[ChatMessage],
        task_type: str,
    ) -> Provider:
        """Choose a provider using explicit choice, persona hints, or router heuristics."""
        if backend:
            if backend not in BACKEND_ALIASES:
                raise KeyError(f"Unknown backend: {backend}")
            return BACKEND_ALIASES[backend]

        role = self._role_for_task(task_type, persona)
        content_size = self._estimate_size(message)
        adapter = await self.router.route(role, content_size=content_size)
        return adapter.provider

    def _role_for_task(self, task_type: str, persona: str | None) -> ModelRole:
        """Map a task/persona into a routing role."""
        if persona == "architect":
            return ModelRole.ARCHITECT
        if persona == "code-specialist":
            return ModelRole.CODER
        if persona == "fast-parser":
            return ModelRole.PARSER
        if persona == "context-distiller":
            return ModelRole.PARSER
        if task_type == "review":
            return ModelRole.REVIEWER
        if task_type == "boilerplate":
            return ModelRole.BOILERPLATE
        return ModelRole.CODER

    def _prepare_messages(
        self,
        incoming: str | Sequence[ChatMessage],
        provider: Provider,
        persona: Persona,
        include_context: bool,
    ) -> List[ChatMessage]:
        """Build the message list with persona + context applied."""
        prepared: List[ChatMessage] = []
        if persona.system_prompt:
            prepared.append(ChatMessage(role="system", content=persona.system_prompt))

        backend_key = provider.value
        if include_context:
            context_messages = self._memory_blend(incoming, backend_key)
            if self._should_distill(context_messages):
                context_messages = self.context_manager.distill(
                    backend_key,
                    hint=incoming if isinstance(incoming, str) else None,
                )
            prepared.extend(context_messages)

        if isinstance(incoming, str):
            prepared.append(ChatMessage(role="user", content=incoming))
        else:
            prepared.extend(list(incoming))

        return prepared

    def _memory_blend(self, incoming: str | Sequence[ChatMessage], backend_key: str) -> List[ChatMessage]:
        """Blend session context with lightweight memory hits."""
        context = self.context_manager.get_context(backend_key)
        query = incoming if isinstance(incoming, str) else " ".join(msg.content for msg in incoming)
        memories = self.context_manager.retrieve(query, limit=3)
        memory_msgs = [ChatMessage(role="system", content=f"[Memory] {m}") for m in memories]
        return context + memory_msgs

    async def _chat_with_fallback(
        self,
        *,
        messages: Sequence[ChatMessage],
        preferred_provider: Provider,
        tools: Sequence[MutableMapping[str, object]] | None,
        max_tokens: int | None,
        temperature: float | None,
    ) -> ChatResponse:
        """Try the preferred provider first, then fall back through the chain."""
        providers = [preferred_provider] + [
            p for p in self.client.fallback_chain if p != preferred_provider
        ]
        last_error: Exception | None = None
        for provider in providers:
            request = ChatRequest(
                messages=messages,
                provider=provider,
                model=self._default_model(provider),
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            try:
                return await self.client.chat(request)
            except Exception as exc:  # noqa: PERF203
                last_error = exc
                continue

        raise last_error or RuntimeError("All providers failed to respond.")

    async def _handle_tool_calls(
        self,
        *,
        messages: Sequence[ChatMessage],
        initial: ChatResponse,
        provider: Provider,
        tools: Sequence[MutableMapping[str, object]] | None,
        max_tokens: int | None,
        temperature: float | None,
    ) -> ChatResponse:
        """Execute tool calls and send results back to the provider."""
        follow_up: List[ChatMessage] = list(messages)
        if initial.content:
            follow_up.append(ChatMessage(role="assistant", content=initial.content))

        for call in initial.tool_calls or []:
            tool_result = await self.client.execute_tool(call)
            follow_up.append(
                ChatMessage(
                    role="tool",
                    content=json.dumps(tool_result),
                    name=call.name,
                    tool_call_id=call.id,
                )
            )

        request = ChatRequest(
            messages=follow_up,
            provider=provider,
            model=self._default_model(provider),
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return await self.client.chat(request)

    def _record_context(
        self,
        provider: Provider,
        persona: Persona,
        original_message: str | Sequence[ChatMessage],
        response: ChatResponse,
    ) -> None:
        """Persist the conversational context for future turns."""
        backend_key = provider.value
        if isinstance(original_message, str):
            self.context_manager.add_message(backend_key, ChatMessage(role="user", content=original_message))
        else:
            for msg in original_message:
                self.context_manager.add_message(backend_key, msg)
        self.context_manager.add_message(backend_key, ChatMessage(role="assistant", content=response.content))

        if response.usage:
            try:
                self.usage_tracker.record_usage(provider.value, response.model, response.usage)  # type: ignore[arg-type]
            except Exception:
                # Usage tracking should not interrupt orchestration.
                pass

    def _default_model(self, provider: Provider) -> str | None:
        """Best-effort default model for a provider."""
        mapping = {
            Provider.CLAUDE: getattr(self.router.claude, "default_model", None),
            Provider.OPENAI: getattr(self.router.openai, "default_model", None),
            Provider.GEMINI: getattr(self.router.gemini, "default_model", None),
            Provider.OLLAMA: getattr(self.router.ollama, "default_model", None),
        }
        return mapping.get(provider)

    def _estimate_size(self, message: str | Sequence[ChatMessage]) -> int:
        """Rough size estimate for routing decisions."""
        if isinstance(message, str):
            return len(message)
        return sum(len(m.content) for m in message)

    def _estimate_tokens(self, messages: Sequence[ChatMessage]) -> int:
        """Rough token estimate (character based heuristic)."""
        chars = sum(len(m.content) for m in messages)
        return max(1, chars // 4)

    def _audit_log_path(self) -> Path:
        """Location for tool audit logs (per-feature if available)."""
        base = getattr(self, "feature_dir", None)
        if base is None:
            base = self.config.config_dir
        return Path(base) / "logs" / "tools.log"

    def _should_distill(self, messages: Sequence[ChatMessage]) -> bool:
        """Check if context distillation should run."""
        trigger = self.config.get("context_distill_trigger_tokens", 50000)
        return self._estimate_tokens(messages) > int(trigger)
