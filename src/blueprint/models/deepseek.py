"""Ollama (local) API adapter."""

from __future__ import annotations

import json
from typing import AsyncGenerator, Dict, List, Optional

import httpx

from .base import (
    BaseAdapter,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    LLMExecutionException,
    LLMUnavailableException,
    ModelInfo,
    Provider,
    ProviderHealth,
    StreamChunk,
    Usage,
)
from .credentials import CredentialsManager


class OllamaAdapter(BaseAdapter):
    """Adapter for local Ollama chat API."""

    provider = Provider.OLLAMA

    def __init__(
        self,
        credentials: CredentialsManager | None = None,
        default_model: str = "deepseek-coder:latest",
        base_url: str = "http://localhost:11434",
        timeout: float = 30.0,
    ) -> None:
        self.credentials = credentials or CredentialsManager()
        self.default_model = default_model
        self.base_url = (self.credentials.get_base_url(Provider.OLLAMA, base_url) or base_url).rstrip("/")
        self.timeout = timeout

    async def chat(self, request: ChatRequest) -> ChatResponse:
        url = f"{self.base_url}/api/chat"
        payload = self._build_payload(request, stream=False)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMExecutionException(f"Ollama request failed: {exc}") from exc

        data = resp.json()
        message = data.get("message") or {}
        content = message.get("content") or data.get("response") or ""

        return ChatResponse(
            content=content,
            provider=self.provider,
            model=payload["model"],
            usage=None,
            finish_reason="stop" if data.get("done", True) else None,
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[StreamChunk, None]:
        url = f"{self.base_url}/api/chat"
        payload = self._build_payload(request, stream=True)

        async with httpx.AsyncClient(timeout=None) as client:
            try:
                async with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    async for raw_line in resp.aiter_lines():
                        line = raw_line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError as exc:
                            yield StreamChunk(
                                delta="",
                                is_done=False,
                                provider=self.provider,
                                model=payload["model"],
                                error=LLMExecutionException(f"Malformed stream chunk: {exc}"),
                            )
                            continue

                        delta_text = ""
                        if "message" in data and data["message"].get("content"):
                            delta_text = data["message"]["content"]
                        elif "response" in data and isinstance(data["response"], str):
                            delta_text = data["response"]

                        is_done = bool(data.get("done"))
                        yield StreamChunk(
                            delta=delta_text,
                            is_done=is_done,
                            provider=self.provider,
                            model=payload["model"],
                            usage=None,
                        )
                        if is_done:
                            break
            except httpx.HTTPError as exc:
                yield StreamChunk(
                    delta="",
                    is_done=True,
                    provider=self.provider,
                    model=payload["model"],
                    error=LLMExecutionException(f"Ollama stream failed: {exc}"),
                )

    async def list_models(self) -> List[ModelInfo]:
        url = f"{self.base_url}/api/tags"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMExecutionException(f"Failed to list Ollama models: {exc}") from exc

        data = resp.json()
        results: List[ModelInfo] = []
        for model in data.get("models", []):
            name = model.get("name")
            if name:
                results.append(ModelInfo(id=name, provider=self.provider))
        return results

    async def check_health(self) -> ProviderHealth:
        try:
            await self.list_models()
            return ProviderHealth(provider=self.provider, status="healthy")
        except LLMException:
            return ProviderHealth(provider=self.provider, status="down")

    def _build_payload(self, request: ChatRequest, stream: bool) -> Dict[str, object]:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        payload: Dict[str, object] = {
            "model": request.model or self.default_model,
            "messages": messages,
            "stream": stream,
        }
        if request.temperature is not None:
            payload["options"] = {"temperature": request.temperature}
        return payload

    # --- Compatibility helpers for existing pipeline flows ---

    async def generate_code(self, task_description: str, context: str = "") -> str:
        """Generate code for a task description."""
        prompt = f"""Generate production-ready code for this task.

Task: {task_description}

Context:
{context}"""
        response = await self.chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content=prompt)],
                model=self.default_model,
                temperature=0.4,
            )
        )
        return response.content

    async def refactor_code(self, code: str, instructions: str) -> str:
        """Refactor existing code according to instructions."""
        prompt = f"""Refactor this code according to the instructions.

Instructions: {instructions}

Code:
{code}"""
        response = await self.chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content=prompt)],
                model=self.default_model,
                temperature=0.2,
            )
        )
        return response.content

    async def get_context_limit(self) -> Optional[int]:
        """Return context length if reported by Ollama."""
        url = f"{self.base_url}/api/show"
        payload = {"name": self.default_model}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                params = data.get("model_info") or data.get("parameters") or data
                for key in ("context_length", "context", "ctx"):
                    value = params.get(key) if isinstance(params, dict) else None
                    if isinstance(value, int):
                        return value
            except httpx.HTTPError:
                return None
        return None


# Backwards compatibility alias for previous DeepSeek naming.
DeepSeekAdapter = OllamaAdapter
