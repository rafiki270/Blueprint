"""Session, distillation, and persistent context management for the orchestrator."""

from __future__ import annotations

import asyncio
import pickle
import sqlite3
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, Iterable, List, MutableMapping, Sequence

from ..config import ConfigLoader
from ..models.base import ChatMessage, ChatRequest, Provider
from ..state.persistence import Persistence


class PersistentMemory:
    """SQLite-backed persistent memory store with lightweight embeddings."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT,
                value TEXT,
                embedding BLOB,
                tags TEXT,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def add(self, key: str, value: str, tags: list[str] | None = None) -> None:
        embedding = self._generate_embedding(value)
        self.conn.execute(
            """
            INSERT INTO memories (key, value, embedding, tags)
            VALUES (?, ?, ?, ?)
            """,
            (key, value, self._serialize_embedding(embedding), json_dumps(tags or [])),
        )
        self.conn.commit()

    def retrieve(self, query: str, limit: int = 5) -> list[str]:
        """Retrieve relevant memories using embedding similarity."""
        query_embedding = self._generate_embedding(query)
        cursor = self.conn.execute("SELECT value, embedding FROM memories")

        results: list[tuple[float, str]] = []
        for value, embedding_blob in cursor:
            embedding = self._deserialize_embedding(embedding_blob)
            similarity = self._cosine_similarity(query_embedding, embedding)
            results.append((similarity, value))

        results.sort(reverse=True, key=lambda x: x[0])
        return [value for _, value in results[:limit]]

    def _generate_embedding(self, text: str) -> list[float]:
        # Placeholder embedding; replace with model-backed embeddings if available.
        return [float(len(text) % 10)] * 64

    def _serialize_embedding(self, embedding: list[float]) -> bytes:
        return pickle.dumps(embedding)

    def _deserialize_embedding(self, blob: bytes) -> list[float]:
        return pickle.loads(blob)

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        import math

        dot_product = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        return dot_product / (mag_a * mag_b) if mag_a and mag_b else 0.0


def json_dumps(obj: object) -> str:
    import json

    return json.dumps(obj)


class ContextManager:
    """Manages multi-tier context system (session + persistent + distillation)."""

    def __init__(self, config: ConfigLoader, orchestrator: "LLMOrchestrator" | None = None) -> None:
        self.config = config
        self.orchestrator = orchestrator
        ctx = config.get
        self.max_session_messages = int(ctx("context.session_max_messages", 50))
        self.max_session_tokens = int(ctx("context.session_max_tokens", 100000))
        self.summarize_threshold = int(ctx("context.auto_summarize_threshold", 40))
        self.enable_distillation = bool(ctx("context.enable_distillation", True))
        self.distillation_trigger_tokens = int(ctx("context.distillation_trigger_tokens", 50000))
        self.distillation_target_tokens = int(ctx("context.distillation_target_tokens", 8000))
        self.distillation_backend = ctx("context.distillation_backend", "gemini")
        self.distillation_persona = ctx("context.distillation_persona", "context-distiller")

        self._session: Dict[str, Deque[ChatMessage]] = {}

        memory_enabled = bool(ctx("context.persistent_memory_enabled", True))
        memory_path = Path(ctx("context.memory_db_path", "~/.config/blueprint/memory.db")).expanduser()
        self.memory = PersistentMemory(memory_path) if memory_enabled else None

    # --- Session context -------------------------------------------------
    def add_message(self, message: ChatMessage, backend: str | None = None) -> None:
        """Add message to session context."""
        key = backend or "global"
        if key not in self._session:
            self._session[key] = deque(maxlen=self.max_session_messages)
        self._session[key].append(message)
        if len(self._session[key]) >= self.summarize_threshold:
            self._summarize_context(key)

    def get_context(
        self,
        backend: str | None = None,
        max_tokens: int | None = None,
        current_task: str | None = None,
    ) -> list[ChatMessage]:
        """Get context for backend, optionally distilling and trimming."""
        key = backend or "global"
        context = list(self._session.get(key, []))
        if key != "global":
            context = list(self._session.get("global", [])) + context

        if max_tokens:
            context = self._trim_to_tokens(context, max_tokens)
        return context

    def get_relevant_context(
        self,
        query: str,
        backend: str | None = None,
        max_items: int = 5,
    ) -> list[ChatMessage]:
        """Combine persistent memory retrieval with recent session context."""
        recent = self.get_context(backend)[-10:]
        memories = self.memory.retrieve(query, limit=max_items) if self.memory else []
        memory_messages = [ChatMessage(role="system", content=f"[Memory] {mem}") for mem in memories]
        return memory_messages + recent

    def clear_backend_context(self, backend: str) -> None:
        """Clear session context for specific backend."""
        self._session.pop(backend, None)

    def clear_all(self) -> None:
        """Clear all session contexts."""
        self._session.clear()

    # --- Persistent memory ----------------------------------------------
    def remember(self, text: str, tags: Sequence[str] | None = None) -> None:
        if not self.memory:
            return
        self.memory.add(key="note", value=text, tags=list(tags) if tags else [])

    def retrieve(self, query: str, limit: int = 5) -> List[str]:
        if not self.memory:
            return []
        return self.memory.retrieve(query, limit=limit)

    async def distill_async(self, backend: str, hint: str | None = None) -> List[ChatMessage]:
        """Async distillation that leverages the orchestrator's client when available."""
        history = list(self._session.get(backend, ()))
        if not history:
            return []

        if self._estimate_tokens(history) <= self.distillation_trigger_tokens:
            return history

        summary_msg = await self._distill_context_async(history, hint, backend)
        keep_tail = history[-8:]
        distilled = [summary_msg] + keep_tail
        self._session[backend] = deque(distilled, maxlen=self.max_session_messages)
        return distilled

    # --- Internal helpers -----------------------------------------------
    def _summarize_context(self, key: str) -> None:
        """Summarize old context to save tokens."""
        context = list(self._session[key])
        keep_recent = 10
        to_summarize = context[:-keep_recent]
        recent = context[-keep_recent:]
        if not to_summarize:
            return

        summary_text = "\n".join(f"{msg.role}: {msg.content}" for msg in to_summarize)
        summary_msg = ChatMessage(
            role="system",
            content=f"[Previous conversation summary]: {summary_text}",
        )
        self._session[key] = deque([summary_msg] + recent, maxlen=self.max_session_messages)

    def _trim_to_tokens(self, messages: list[ChatMessage], max_tokens: int) -> list[ChatMessage]:
        """Trim message list to fit token budget, keeping most recent messages."""
        total_tokens = 0
        result: list[ChatMessage] = []
        for msg in reversed(messages):
            msg_tokens = len(msg.content) // 4
            if total_tokens + msg_tokens > max_tokens:
                break
            result.insert(0, msg)
            total_tokens += msg_tokens
        return result

    def _estimate_tokens(self, messages: Sequence[ChatMessage]) -> int:
        return max(1, sum(len(m.content) for m in messages) // 4)

    async def _distill_context_async(
        self,
        context: list[ChatMessage],
        current_task: str | None,
        backend: str | None = None,
    ) -> ChatMessage:
        """Run distillation via LLM backend, fallback to lightweight summary."""
        context_text = self._format_context_for_distillation(context)
        distillation_prompt = (
            "You are analyzing a large conversation history to extract only the information relevant to the current task.\n\n"
            f"**Current Task:**\n{current_task or ''}\n\n"
            f"**Full Context:**\n{context_text}\n\n"
            "Instructions:\n"
            "Extract and summarize only the information from the context that is relevant to completing the current task. "
            "Focus on key decisions, important code patterns, unresolved issues, critical facts, and recent changes. "
            "Ignore tangential or redundant information."
        )

        distilled_summary: str | None = None
        if self.orchestrator is not None:
            try:
                provider = self._provider_for_backend(self.distillation_backend)
                messages = [ChatMessage(role="user", content=distillation_prompt)]
                request = self.orchestrator._build_direct_request(  # noqa: SLF001
                    messages=messages,
                    provider=provider,
                    persona_name=self.distillation_persona,
                )
                response = await self.orchestrator.client.chat(request)  # type: ignore[arg-type]
                distilled_summary = response.content
            except Exception:
                distilled_summary = None

        if not distilled_summary:
            distilled_summary = f"[Context distilled] Task: {current_task or ''}\n{context_text[:2000]}"

        target_backend = backend or "global"
        return ChatMessage(role="system", content=distilled_summary)

    def _provider_for_backend(self, backend: str) -> Provider:
        mapping = {
            "claude": Provider.CLAUDE,
            "openai": Provider.OPENAI,
            "gemini": Provider.GEMINI,
            "ollama": Provider.OLLAMA,
        }
        return mapping.get(backend, Provider.GEMINI)

    def _format_context_for_distillation(self, context: list[ChatMessage]) -> str:
        return "\n".join(f"{msg.role}: {msg.content}" for msg in context)

    def stats(self, backend: str) -> dict[str, int]:
        msgs = list(self._session.get(backend, ()))
        return {"messages": len(msgs), "estimated_tokens": self._estimate_tokens(msgs)}
