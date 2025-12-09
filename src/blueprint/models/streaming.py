"""Streaming helpers for LLM adapters."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Iterable, List, Optional, Sequence

from .base import BaseAdapter, ChatRequest, StreamChunk
from .base import LLMExecutionException


class StreamHandler:
    """Normalize streaming responses and handle retries/fallbacks."""

    def __init__(self, max_retries: int = 2, backoff_seconds: float = 1.0) -> None:
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    async def handle_stream(
        self,
        request: ChatRequest,
        adapter: BaseAdapter,
        fallback_adapters: Sequence[BaseAdapter] | None = None,
        expect_json: bool = False,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Yield normalized chunks; retry or fallback on failure."""
        attempts = 0
        adapters: List[BaseAdapter] = [adapter]
        if fallback_adapters:
            adapters.extend(fallback_adapters)

        for current_adapter in adapters:
            while attempts <= self.max_retries:
                try:
                    collected: List[str] = []
                    async for chunk in current_adapter.stream_chat(request):
                        # Basic structural validation
                        if chunk.error:
                            raise chunk.error
                        if chunk.delta:
                            collected.append(chunk.delta)
                        yield chunk
                    # Post-stream validation
                    if not collected:
                        raise LLMExecutionException("Stream produced no content")
                    if expect_json:
                        self._validate_json("".join(collected))
                    return
                except Exception as exc:
                    attempts += 1
                    if attempts > self.max_retries:
                        yield StreamChunk(
                            delta="",
                            is_done=True,
                            provider=current_adapter.provider,
                            model=request.model,
                            error=LLMExecutionException(str(exc)),
                        )
                        break
                    await asyncio.sleep(self.backoff_seconds * attempts)
            # Move to next adapter if available
        # If we exhausted adapters and retries without success, emit terminal chunk
        yield StreamChunk(
            delta="",
            is_done=True,
            provider=adapter.provider,
            model=request.model,
            error=LLMExecutionException("Streaming failed after retries/fallbacks"),
        )

    def _validate_json(self, payload: str) -> None:
        """Basic JSON validation for streams expected to return structured output."""
        import json

        try:
            json.loads(payload)
        except json.JSONDecodeError as exc:  # pragma: no cover - lightweight guard
            raise LLMExecutionException(f"Invalid JSON output: {exc}") from exc
