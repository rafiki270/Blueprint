"""Google Gemini API adapter."""

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


class GeminiAdapter(BaseAdapter):
    """Adapter for Gemini generateContent API."""

    provider = Provider.GEMINI

    def __init__(
        self,
        credentials: CredentialsManager | None = None,
        default_model: str = "gemini-2.0-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 30.0,
    ) -> None:
        self.credentials = credentials or CredentialsManager()
        self.default_model = default_model
        self.base_url = (self.credentials.get_base_url(Provider.GEMINI, base_url) or base_url).rstrip("/")
        self.timeout = timeout

    async def chat(self, request: ChatRequest) -> ChatResponse:
        api_key = self._api_key()
        payload = self._build_payload(request)
        model = request.model or self.default_model
        url = f"{self.base_url}/models/{model}:generateContent?key={api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMExecutionException(f"Gemini request failed: {exc}") from exc

        data = resp.json()
        text = self._extract_text(data)
        usage = self._parse_usage(data.get("usageMetadata"))

        return ChatResponse(
            content=text,
            provider=self.provider,
            model=model,
            usage=usage,
            finish_reason=data.get("candidates", [{}])[0].get("finishReason"),
            metadata={"candidates": len(data.get("candidates") or [])},
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[StreamChunk, None]:
        api_key = self._api_key()
        payload = self._build_payload(request)
        model = request.model or self.default_model
        url = f"{self.base_url}/models/{model}:streamGenerateContent?alt=sse&key={api_key}"

        async with httpx.AsyncClient(timeout=None) as client:
            try:
                async with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    async for raw_line in resp.aiter_lines():
                        line = raw_line.strip()
                        if not line:
                            continue
                        if line.startswith("data:"):
                            line = line[len("data:") :].strip()
                        if line == "[DONE]":
                            yield StreamChunk(delta="", is_done=True, provider=self.provider, model=model)
                            break
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError as exc:
                            yield StreamChunk(
                                delta="",
                                is_done=False,
                                provider=self.provider,
                                model=model,
                                error=LLMExecutionException(f"Malformed stream chunk: {exc}"),
                            )
                            continue

                        delta_text = self._extract_text(data)
                        usage = self._parse_usage(data.get("usageMetadata"))

                        yield StreamChunk(
                            delta=delta_text,
                            is_done=False,
                            provider=self.provider,
                            model=model,
                            usage=usage,
                        )
            except httpx.HTTPError as exc:
                yield StreamChunk(
                    delta="",
                    is_done=True,
                    provider=self.provider,
                    model=model,
                    error=LLMExecutionException(f"Gemini stream failed: {exc}"),
                )

    async def list_models(self) -> List[ModelInfo]:
        api_key = self._api_key()
        url = f"{self.base_url}/models?key={api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMExecutionException(f"Failed to list Gemini models: {exc}") from exc

        data = resp.json()
        results: List[ModelInfo] = []
        for model in data.get("models", []):
            model_id = model.get("name") or model.get("id")
            if model_id:
                # Trim prefix "models/" if present.
                cleaned = model_id.split("/")[-1]
                results.append(ModelInfo(id=cleaned, provider=self.provider))
        return results

    async def check_health(self) -> ProviderHealth:
        try:
            await self.list_models()
            return ProviderHealth(provider=self.provider, status="healthy")
        except LLMException:
            return ProviderHealth(provider=self.provider, status="down")

    def _build_payload(self, request: ChatRequest) -> Dict[str, object]:
        contents: List[Dict[str, object]] = []
        for message in request.messages:
            role = "user" if message.role == "user" else "model"
            if message.role == "system":
                role = "user"
            contents.append(
                {
                    "role": role,
                    "parts": [{"text": message.content}],
                }
            )

        payload: Dict[str, object] = {"contents": contents}
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["generationConfig"] = {"maxOutputTokens": request.max_tokens}
        if request.top_p is not None:
            payload.setdefault("generationConfig", {})
            payload["generationConfig"]["topP"] = request.top_p
        if request.stop:
            payload.setdefault("generationConfig", {})
            payload["generationConfig"]["stopSequences"] = list(request.stop)
        if request.tools:
            payload["tools"] = list(request.tools)
        return payload

    def _extract_text(self, data: Dict[str, object]) -> str:
        candidates = data.get("candidates") or []
        for candidate in candidates:
            parts = (candidate.get("content") or {}).get("parts") or []
            texts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
            if texts:
                return "".join(texts)
        # Some streaming events include top-level "content"
        content = data.get("content") or {}
        parts = content.get("parts") or []
        texts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
        return "".join(texts)

    def _parse_usage(self, payload: Optional[Dict[str, object]]) -> Optional[Usage]:
        if not payload:
            return None
        prompt = int(payload.get("promptTokenCount") or 0)
        completion = int(payload.get("candidatesTokenCount") or payload.get("totalTokenCount") or 0)
        total = int(payload.get("totalTokenCount") or prompt + completion)
        return Usage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)

    def _api_key(self) -> str:
        api_key = self.credentials.get_api_key(Provider.GEMINI)
        if not api_key:
            raise LLMUnavailableException("GEMINI_API_KEY or GOOGLE_GENERATIVE_AI_API_KEY not configured.")
        return api_key

    # --- Compatibility helpers for existing pipeline flows ---

    async def parse_spec_to_tasks(
        self, spec: str, model: Optional[str] = None, sandbox: bool = False, output_format: Optional[str] = None
    ) -> str:
        """Parse a specification into a tasks JSON array."""
        prompt = f"""Convert this specification into structured JSON tasks.

Specification:
{spec}

Return ONLY valid JSON array with tasks in this format:
[
  {{
    "id": "task-1",
    "title": "Task title",
    "description": "Detailed description",
    "type": "code|boilerplate|review|architecture"
  }}
]"""
        response = await self.chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content=prompt)],
                model=model or self.default_model,
                temperature=0.1,
            )
        )
        return response.content

    async def generate_boilerplate(
        self, task_description: str, model: Optional[str] = None, sandbox: bool = False, output_format: Optional[str] = None
    ) -> str:
        """Generate boilerplate code for a task description."""
        prompt = f"""Generate production-ready boilerplate code for this task:

{task_description}

Provide complete, idiomatic code with any necessary scaffolding."""
        response = await self.chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content=prompt)],
                model=model or self.default_model,
                temperature=0.4,
            )
        )
        return response.content
