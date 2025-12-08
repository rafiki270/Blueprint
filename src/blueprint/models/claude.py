"""Anthropic Claude API adapter."""

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
    ToolCall,
    Usage,
)
from .credentials import CredentialsManager


class ClaudeAdapter(BaseAdapter):
    """Adapter for Claude Messages API."""

    provider = Provider.CLAUDE

    def __init__(
        self,
        credentials: CredentialsManager | None = None,
        default_model: str = "claude-3-5-sonnet-20241022",
        base_url: str | None = None,
        api_version: str = "2023-06-01",
        timeout: float = 30.0,
    ) -> None:
        self.credentials = credentials or CredentialsManager()
        self.default_model = default_model
        self.base_url = (base_url or self.credentials.get_base_url(Provider.CLAUDE) or "https://api.anthropic.com").rstrip(
            "/"
        )
        self.api_version = api_version
        self.timeout = timeout

    async def chat(self, request: ChatRequest) -> ChatResponse:
        api_key = self.credentials.get_api_key(Provider.CLAUDE)
        if not api_key:
            raise LLMUnavailableException("ANTHROPIC_API_KEY not configured.")

        payload = self._build_payload(request, stream=False)
        url = f"{self.base_url}/v1/messages"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(url, headers=self._headers(api_key), json=payload)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMExecutionException(f"Claude request failed: {exc}") from exc

        data = resp.json()
        content_text = self._extract_text_blocks(data.get("content") or [])
        usage = self._parse_usage(data.get("usage"))
        tool_calls = self._parse_tool_calls(data.get("content") or [])

        return ChatResponse(
            content=content_text,
            provider=self.provider,
            model=data.get("model") or request.model or self.default_model,
            usage=usage,
            finish_reason=data.get("stop_reason"),
            tool_calls=tool_calls,
            metadata={"id": data.get("id")},
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[StreamChunk, None]:
        api_key = self.credentials.get_api_key(Provider.CLAUDE)
        if not api_key:
            raise LLMUnavailableException("ANTHROPIC_API_KEY not configured.")

        payload = self._build_payload(request, stream=True)
        url = f"{self.base_url}/v1/messages"

        async with httpx.AsyncClient(timeout=None) as client:
            try:
                async with client.stream("POST", url, headers=self._headers(api_key), json=payload) as resp:
                    resp.raise_for_status()
                    async for raw_line in resp.aiter_lines():
                        line = raw_line.strip()
                        if not line:
                            continue
                        if line.startswith("data:"):
                            line = line[len("data:") :].strip()
                        if line == "[DONE]":
                            yield StreamChunk(delta="", is_done=True, provider=self.provider, model=payload["model"])
                            break

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

                        chunk_type = data.get("type")
                        delta_text = ""
                        tool_call = None
                        if chunk_type == "content_block_delta":
                            delta_text = (data.get("delta") or {}).get("text", "") or ""
                        elif chunk_type == "message_delta":
                            if data.get("delta", {}).get("stop_reason"):
                                yield StreamChunk(
                                    delta="",
                                    is_done=True,
                                    provider=self.provider,
                                    model=data.get("model") or payload["model"],
                                    usage=self._parse_usage(data.get("usage")),
                                )
                                continue
                        elif chunk_type == "content_block_start":
                            block = data.get("content_block") or {}
                            if block.get("type") == "tool_use":
                                tool_call = ToolCall(
                                    id=str(block.get("id") or ""),
                                    name=block.get("name") or "",
                                    arguments=block.get("input") or {},
                                )

                        yield StreamChunk(
                            delta=delta_text,
                            is_done=False,
                            provider=self.provider,
                            model=data.get("model") or payload["model"],
                            usage=None,
                            tool_call=tool_call,
                        )
            except httpx.HTTPError as exc:
                yield StreamChunk(
                    delta="",
                    is_done=True,
                    provider=self.provider,
                    model=request.model or self.default_model,
                    error=LLMExecutionException(f"Claude stream failed: {exc}"),
                )

    async def list_models(self) -> List[ModelInfo]:
        api_key = self.credentials.get_api_key(Provider.CLAUDE)
        if not api_key:
            raise LLMUnavailableException("ANTHROPIC_API_KEY not configured.")

        url = f"{self.base_url}/v1/models"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, headers=self._headers(api_key))
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMExecutionException(f"Failed to list Claude models: {exc}") from exc

        data = resp.json()
        results = []
        for model in data.get("data", []):
            model_id = model.get("id")
            if model_id:
                results.append(ModelInfo(id=model_id, provider=self.provider))
        return results

    async def check_health(self) -> ProviderHealth:
        try:
            await self.list_models()
            return ProviderHealth(provider=self.provider, status="healthy")
        except LLMException:
            return ProviderHealth(provider=self.provider, status="down")

    def _headers(self, api_key: str) -> Dict[str, str]:
        return {
            "x-api-key": api_key,
            "anthropic-version": self.api_version,
            "Content-Type": "application/json",
        }

    def _build_payload(self, request: ChatRequest, stream: bool) -> Dict[str, object]:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        payload: Dict[str, object] = {
            "model": request.model or self.default_model,
            "messages": messages,
            "stream": stream,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        else:
            payload["max_tokens"] = 1024
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop:
            payload["stop_sequences"] = list(request.stop)
        if request.tools:
            payload["tools"] = list(request.tools)
        return payload

    def _extract_text_blocks(self, blocks: List[Dict[str, object]]) -> str:
        texts: List[str] = []
        for block in blocks:
            if block.get("type") == "text":
                value = block.get("text")
                if isinstance(value, str):
                    texts.append(value)
        return "".join(texts)

    def _parse_tool_calls(self, blocks: List[Dict[str, object]]) -> List[ToolCall]:
        calls: List[ToolCall] = []
        for block in blocks:
            if block.get("type") != "tool_use":
                continue
            calls.append(
                ToolCall(
                    id=str(block.get("id") or ""),
                    name=block.get("name") or "",
                    arguments=block.get("input") or {},
                )
            )
        return calls

    def _parse_usage(self, payload: Optional[Dict[str, object]]) -> Optional[Usage]:
        if not payload:
            return None
        input_tokens = int(payload.get("input_tokens") or 0)
        output_tokens = int(payload.get("output_tokens") or 0)
        return Usage(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )

    # --- Compatibility helpers for existing pipeline flows ---

    async def generate_spec(self, brief: str, model: Optional[str] = None) -> str:
        """Generate a technical specification from a brief."""
        prompt = f"""You are a system architect. Convert this brief into a detailed technical specification including overview, architecture, API definitions, data models, test plan, and implementation steps.

Brief:
{brief}"""
        response = await self.chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content=prompt)],
                model=model or self.default_model,
                temperature=0.2,
                max_tokens=2048,
            )
        )
        return response.content
