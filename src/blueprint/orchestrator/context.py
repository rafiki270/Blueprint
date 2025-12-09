"""Session and persistent context management for the orchestrator."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, Iterable, List, MutableMapping, Sequence

from ..config import Config
from ..models.base import ChatMessage
from ..state.persistence import Persistence


class ContextManager:
    """Manages per-backend session history and lightweight persistent memory."""

    def __init__(self, config: Config, memory_path: Path | None = None) -> None:
        self.config = config
        self.max_messages = int(config.get("context_max_messages", 50))
        self.summarize_threshold = int(config.get("context_summarize_threshold", 40))
        self.distill_trigger_tokens = int(config.get("context_distill_trigger_tokens", 50000))
        self.distill_target_tokens = int(config.get("context_distill_target_tokens", 8000))

        self._session: Dict[str, Deque[ChatMessage]] = {}
        base_dir = memory_path or config.config_dir
        self.memory_file = Path(base_dir) / "memory.json"

    # --- Session context -------------------------------------------------
    def add_message(self, backend: str, message: ChatMessage) -> None:
        """Append a message to the session history for a backend."""
        history = self._session.setdefault(backend, deque())
        history.append(message)
        self._maybe_summarize(backend)

    def get_context(self, backend: str | None = None) -> List[ChatMessage]:
        """Return the session context for a backend, merged with global."""
        key = backend or "global"
        context = list(self._session.get(key, ()))
        if key != "global":
            context = list(self._session.get("global", ())) + context
        return context

    def clear_backend(self, backend: str) -> None:
        """Clear context for a specific backend."""
        self._session.pop(backend, None)

    def clear_all(self) -> None:
        """Clear context for all backends."""
        self._session.clear()

    def _maybe_summarize(self, backend: str) -> None:
        """Collapse older history to keep the session bounded."""
        history = self._session.get(backend)
        if not history:
            return

        threshold = max(self.summarize_threshold, self.max_messages)
        if len(history) <= threshold:
            return

        # Summarize older messages into a single system note.
        keep_tail = list(history)[-10:]
        prefix = list(history)[:-10]
        summary_text = "\n".join(f"{m.role}: {m.content}" for m in prefix)
        summarized = deque(keep_tail, maxlen=self.max_messages)
        summarized.appendleft(ChatMessage(role="system", content=f"[Earlier context summary]\n{summary_text}"))
        self._session[backend] = summarized

    def distill(self, backend: str, hint: str | None = None) -> List[ChatMessage]:
        """
        Reduce a long context to a smaller summary.

        This implementation is lightweight: we keep the last few turns and prepend a condensed note.
        """
        history = list(self._session.get(backend, ()))
        if not history:
            return []

        # If already below target, return as-is
        est_tokens = self._estimate_tokens(history)
        if est_tokens <= self.distill_target_tokens:
            return history

        keep_tail = history[-8:]
        earlier = history[:-8]
        summary_lines = [f"{msg.role}: {msg.content}" for msg in earlier]
        note_header = "[Context distilled]"
        if hint:
            note_header += f" Task: {hint}"
        summary = ChatMessage(
            role="system",
            content=f"{note_header}\nKey points:\n" + "\n".join(summary_lines[:20]),
        )
        distilled = [summary] + keep_tail
        self._session[backend] = deque(distilled, maxlen=self.max_messages)
        return distilled

    # --- Persistent memory ----------------------------------------------
    def remember(self, text: str, tags: Sequence[str] | None = None) -> None:
        """Store a fact in persistent memory."""
        payload: MutableMapping[str, object] = {
            "text": text,
            "tags": list(tags) if tags else [],
            "added_at": datetime.utcnow().isoformat(),
        }
        data = self._load_memories()
        items = data.get("items", [])
        items.append(payload)
        data["items"] = items
        Persistence.save_json(self.memory_file, data)

    def retrieve(self, query: str, limit: int = 5) -> List[str]:
        """Fetch memories matching a query string or tag."""
        data = self._load_memories()
        items: Iterable[MutableMapping[str, object]] = data.get("items", [])
        query_lower = query.lower()
        matches: List[str] = []
        for item in items:
            text = str(item.get("text", ""))
            tags = [str(t).lower() for t in item.get("tags", [])]
            if query_lower in text.lower() or query_lower in tags:
                matches.append(text)
            if len(matches) >= limit:
                break
        return matches

    def _load_memories(self) -> MutableMapping[str, object]:
        """Load persisted memory from disk."""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        return Persistence.load_json(self.memory_file)

    def _estimate_tokens(self, messages: Sequence[ChatMessage]) -> int:
        """Very rough token estimate."""
        return max(1, sum(len(m.content) for m in messages) // 4)

    def stats(self, backend: str) -> dict[str, int]:
        """Return lightweight stats for a backend context."""
        msgs = list(self._session.get(backend, ()))
        return {
            "messages": len(msgs),
            "estimated_tokens": self._estimate_tokens(msgs),
        }
