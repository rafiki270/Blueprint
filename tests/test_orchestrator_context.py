import asyncio
import pytest

from blueprint.orchestrator.orchestrator import LLMOrchestrator
from blueprint.models.base import ChatMessage, ChatResponse, Provider, Usage
from blueprint.models.router import ModelRole


class DummyAdapter:
    """Minimal adapter stand-in with a provider and default model."""

    def __init__(self, provider: Provider = Provider.OPENAI, model: str = "gpt-test") -> None:
        self.provider = provider
        self.default_model = model


def test_chat_includes_context_and_persona(monkeypatch):
    orchestrator = LLMOrchestrator()

    # Force routing to our dummy adapter
    dummy_adapter = DummyAdapter()
    async def fake_route(role, content_size=0):
        return dummy_adapter

    monkeypatch.setattr(orchestrator.router, "route", fake_route)

    captured = {}

    async def fake_chat(request):
        captured["request"] = request
        return ChatResponse(
            content="ok",
            provider=request.provider or Provider.OPENAI,
            model=request.model or "gpt-test",
            usage=Usage(),
        )

    monkeypatch.setattr(orchestrator.client, "chat", fake_chat)

    # Seed prior context
    orchestrator.context_manager.add_message(ChatMessage(role="user", content="previous turn"), "openai")

    response = asyncio.run(
        orchestrator.chat("current turn", backend="openai", include_context=True)
    )

    # Assert response passes through
    assert response.content == "ok"

    # Verify the composed messages include persona prompt + previous context + current input
    req = captured["request"]
    roles = [m.role for m in req.messages]
    assert roles[0] == "system"  # persona prompt
    assert any(m.content == "previous turn" for m in req.messages)
    assert any(m.content == "current turn" for m in req.messages)

    # Global context is merged when backend-specific key used
    orchestrator.context_manager.add_message(ChatMessage(role="user", content="global note"), "global")
    ctx = orchestrator.context_manager.get_context("openai")
    assert any(m.content == "global note" for m in ctx)


def test_chat_without_context(monkeypatch):
    orchestrator = LLMOrchestrator()
    dummy_adapter = DummyAdapter()

    async def fake_route(role, content_size=0):
        return dummy_adapter

    monkeypatch.setattr(orchestrator.router, "route", fake_route)

    captured = {}

    async def fake_chat(request):
        captured["request"] = request
        return ChatResponse(
            content="ok",
            provider=request.provider or Provider.OPENAI,
            model=request.model or "gpt-test",
            usage=Usage(),
        )

    monkeypatch.setattr(orchestrator.client, "chat", fake_chat)

    orchestrator.context_manager.add_message(ChatMessage(role="user", content="old"), "openai")

    asyncio.run(
        orchestrator.chat("fresh", backend="openai", include_context=False)
    )

    contents = [m.content for m in captured["request"].messages]
    assert "old" not in contents
    assert "fresh" in contents
