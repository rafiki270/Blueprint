"""Streaming coordination with validation and error recovery."""

from __future__ import annotations

from typing import AsyncGenerator, Iterator, List, Sequence

from ..models.base import StreamChunk


class StreamCoordinator:
    """Coordinates streaming with validation and error recovery."""

    async def stream_with_validation(
        self,
        stream: AsyncGenerator[StreamChunk, None],
        tools: Sequence[object] | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream with automatic validation and retry hooks.

        Features:
        - Accumulates chunks for validation
        - Detects incomplete/malformed output
        - Yields terminal error chunk on failure
        """
        accumulated: List[str] = []
        try:
            async for chunk in stream:
                if chunk.error:
                    yield chunk
                    return
                if chunk.delta:
                    accumulated.append(chunk.delta)
                yield chunk
                if chunk.is_done:
                    full_response = "".join(accumulated)
                    if not self._validate_response(full_response, tools):
                        yield StreamChunk(
                            delta="",
                            is_done=True,
                            provider=chunk.provider,
                            model=chunk.model,
                            error=Exception("Invalid or incomplete response"),
                        )
                        return
        except Exception as exc:  # pragma: no cover - defensive
            fallback_provider = getattr(chunk, "provider", None) if "chunk" in locals() else None
            yield StreamChunk(
                delta="",
                is_done=True,
                provider=fallback_provider,  # type: ignore[arg-type]
                model=getattr(chunk, "model", None) if "chunk" in locals() else None,  # type: ignore[arg-type]
                error=exc,
            )

    def _validate_response(self, response: str, tools: Sequence[object] | None) -> bool:
        """Validate complete response; basic JSON/tool call validation if tools provided."""
        if tools:
            try:
                import json

                parsed = json.loads(response)
                return isinstance(parsed, dict) or isinstance(parsed, list)
            except Exception:
                return False
        return len(response.strip()) > 0
