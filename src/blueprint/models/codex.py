"""OpenAI (ChatGPT/Codex) API adapter."""

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


class OpenAIAdapter(BaseAdapter):
    """Adapter for OpenAI Chat Completions."""

    provider = Provider.OPENAI

    def __init__(
        self,
        credentials: CredentialsManager | None = None,
        default_model: str = "gpt-4o",
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.credentials = credentials or CredentialsManager()
        self.default_model = default_model
        self.base_url = (base_url or self.credentials.get_base_url(Provider.OPENAI) or "https://api.openai.com/v1").rstrip(
            "/"
        )
        self.timeout = timeout

    async def chat(self, request: ChatRequest) -> ChatResponse:
        api_key = self.credentials.get_api_key(Provider.OPENAI)
        if not api_key:
            raise LLMUnavailableException("OPENAI_API_KEY not configured.")

        payload = self._build_payload(request, stream=False)
        url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, headers=self._headers(api_key), json=payload)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMExecutionException(f"OpenAI request failed: {exc}") from exc

        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content", "")
        tool_calls = self._parse_tool_calls(message)
        usage = self._parse_usage(data.get("usage"))

        return ChatResponse(
            content=content,
            provider=self.provider,
            model=data.get("model") or request.model or self.default_model,
            usage=usage,
            finish_reason=choice.get("finish_reason"),
            tool_calls=tool_calls,
            metadata={"id": data.get("id")},
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[StreamChunk, None]:
        api_key = self.credentials.get_api_key(Provider.OPENAI)
        if not api_key:
            raise LLMUnavailableException("OPENAI_API_KEY not configured.")

        payload = self._build_payload(request, stream=True)
        url = f"{self.base_url}/chat/completions"

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
                            parsed = json.loads(line)
                        except json.JSONDecodeError as exc:
                            yield StreamChunk(
                                delta="",
                                is_done=False,
                                provider=self.provider,
                                model=payload["model"],
                                error=LLMExecutionException(f"Malformed stream chunk: {exc}"),
                            )
                            continue

                        choice = (parsed.get("choices") or [{}])[0]
                        delta = (choice.get("delta") or {}).get("content", "") or ""
                        finish_reason = choice.get("finish_reason")
                        usage = self._parse_usage(parsed.get("usage"))
                        tool_calls = self._parse_tool_calls(choice.get("delta") or {})

                        yield StreamChunk(
                            delta=delta,
                            is_done=finish_reason is not None,
                            provider=self.provider,
                            model=parsed.get("model") or payload["model"],
                            usage=usage,
                            tool_call=tool_calls[0] if tool_calls else None,
                        )
            except httpx.HTTPError as exc:
                yield StreamChunk(
                    delta="",
                    is_done=True,
                    provider=self.provider,
                    model=request.model or self.default_model,
                    error=LLMExecutionException(f"OpenAI stream failed: {exc}"),
                )

    async def list_models(self) -> List[ModelInfo]:
        api_key = self.credentials.get_api_key(Provider.OPENAI)
        if not api_key:
            raise LLMUnavailableException("OPENAI_API_KEY not configured.")

        url = f"{self.base_url}/models"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, headers=self._headers(api_key))
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMExecutionException(f"Failed to list OpenAI models: {exc}") from exc

        data = resp.json()
        models = []
        for model in data.get("data", []):
            model_id = model.get("id")
            if model_id:
                models.append(ModelInfo(id=model_id, provider=self.provider))
        return models

    async def check_health(self) -> ProviderHealth:
        try:
            await self.list_models()
            return ProviderHealth(provider=self.provider, status="healthy")
        except LLMException:
            return ProviderHealth(provider=self.provider, status="down")

    def _build_payload(self, request: ChatRequest, stream: bool) -> Dict[str, object]:
        messages = [self._message_to_dict(m) for m in request.messages]
        payload: Dict[str, object] = {
            "model": request.model or self.default_model,
            "messages": messages,
            "stream": stream,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop:
            payload["stop"] = list(request.stop)
        if request.tools:
            payload["tools"] = list(request.tools)
        if stream:
            payload["stream_options"] = {"include_usage": True}
        return payload

    def _headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _message_to_dict(self, message: ChatMessage) -> Dict[str, object]:
        data: Dict[str, object] = {"role": message.role, "content": message.content}
        if message.name:
            data["name"] = message.name
        if message.tool_call_id:
            data["tool_call_id"] = message.tool_call_id
        return data

    def _parse_usage(self, payload: Optional[Dict[str, object]]) -> Optional[Usage]:
        if not payload:
            return None
        prompt = int(payload.get("prompt_tokens") or 0)
        completion = int(payload.get("completion_tokens") or 0)
        total = int(payload.get("total_tokens") or prompt + completion)
        return Usage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)

    def _parse_tool_calls(self, message: Dict[str, object]) -> List[ToolCall]:
        tool_calls: List[ToolCall] = []
        for call in message.get("tool_calls") or []:
            try:
                arguments = call.get("function", {}).get("arguments") or "{}"
                parsed_args = json.loads(arguments) if isinstance(arguments, str) else arguments
                tool_calls.append(
                    ToolCall(
                        id=call.get("id") or "",
                        name=call.get("function", {}).get("name") or "",
                        arguments=parsed_args or {},
                    )
                )
            except Exception:
                continue
        return tool_calls

    # --- Compatibility helpers for existing pipeline flows ---

    async def review_tasks(self, tasks_json: str, model: Optional[str] = None, extra_args: Optional[List[str]] = None) -> str:
        """Review and refine generated tasks."""
        prompt = f"""Review these tasks and suggest improvements:

Tasks:
{tasks_json}

Return refined tasks JSON with clearer descriptions and dependencies."""
        response = await self.chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content=prompt)],
                model=model or self.default_model,
                temperature=0.2,
            )
        )
        return response.content

    async def review_code(
        self, code: str, requirements: str, model: Optional[str] = None, extra_args: Optional[List[str]] = None
    ) -> Dict:
        """Review code and return approval/feedback JSON."""
        prompt = f"""Review this code against requirements.

Requirements:
{requirements}

Code:
{code}

Respond in JSON format:
{{
  "approved": true/false,
  "feedback": "Detailed feedback",
  "corrections": ["List of required corrections"]
}}"""
        response = await self.chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content=prompt)],
                model=model or self.default_model,
                temperature=0.1,
            )
        )
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"approved": False, "feedback": response.content, "corrections": []}

    async def generate_correction(
        self, code: str, issue: str, model: Optional[str] = None, extra_args: Optional[List[str]] = None
    ) -> str:
        """Generate corrected code for a specified issue."""
        prompt = f"""Fix this issue in the code.

Issue: {issue}

Code:
{code}

Return only the corrected code."""
        response = await self.chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content=prompt)],
                model=model or self.default_model,
                temperature=0.2,
            )
        )
        return response.content


# Backwards compatibility alias for previous naming.
CodexAdapter = OpenAIAdapter
