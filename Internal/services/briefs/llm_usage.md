# LLM Usage / Session / Status Tracking Subsystem — Design Spec

## 1. Architecture & Components
- **UsageTracker (core)**: In-process service that records per-call metrics and feeds aggregations. Exposes methods for call lifecycle events (start, chunk, end, error/fallback).
- **SessionManager**: Creates session contexts (per CLI run, per task run, per TUI session) and assigns session IDs; aggregates session-level stats; flushes on close.
- **PricingCatalog**: Holds per-backend/model pricing (tokens → cost). Supports dynamic refresh from config.
- **Storage layer**: Pluggable persistence (JSONL append + SQLite recommended). Stores UsageEntry rows and rollups (session summary, backend/model summary, lifetime totals).
- **Report API**: Read-only interface to query per-session, per-backend, per-model, per-window stats; export to JSON/CSV.
- **Integration points**:
  - Before call: `register_call_start`
  - On stream chunk: `record_chunk`
  - After call completion: `finalize_call`
  - On error: `record_error`
  - On fallback: `record_fallback` (annotate previous call + new backend)

## 2. Data Definitions & Schema
- **UsageEntry (per call)**:
  - `id`, `timestamp_start`, `timestamp_end`
  - `backend_id` (e.g., `openai`), `model` (e.g., `gpt-4o-2024-xx`)
  - `request_type` (`chat|generate|tool|stream`)
  - `session_id`, `project_id` (optional)
  - `prompt_tokens`, `completion_tokens`, `total_tokens`
  - `estimated_cost` (USD), `currency`
  - `latency_ms`
  - `success` (bool), `error_code`, `error_message`
  - `retry_count`, `fallback_from` (if applicable)
  - `metadata` (json: tool calls, route info)
- **SessionUsage**:
  - `session_id`, `started_at`, `ended_at`
  - `totals`: requests, prompt_tokens, completion_tokens, cost, latency_ms, errors, fallbacks
  - `by_backend`: map backend → aggregated counters
  - `by_model`: map model → aggregated counters
- **BackendUsageSummary** (per backend/model over time window):
  - `backend_id`, `model`
  - `window_start`, `window_end`
  - `requests`, `prompt_tokens`, `completion_tokens`, `cost`, `errors`
  - `p95_latency_ms`, `p50_latency_ms` (optional if computed)
- **Storage schema** (SQLite suggestion):
  - `usage_entries(id PK, session_id, project_id, backend_id, model, request_type, ts_start, ts_end, prompt_tokens, completion_tokens, total_tokens, cost, currency, latency_ms, success, error_code, error_message, retry_count, fallback_from, metadata_json)`
  - `sessions(session_id PK, project_id, started_at, ended_at, requests, prompt_tokens, completion_tokens, cost, errors, fallbacks, latency_ms_total)`
  - `pricing(backend_id, model, input_per_million, output_per_million, currency, PRIMARY KEY(backend_id, model))`

## 3. Public Interface (Python-style)
```python
tracker = UsageTracker(storage=SQLiteStorage(path), pricing=PricingCatalog(...))

session = tracker.start_session(project_id="feature-x")  # returns session_id

call_id = tracker.register_call_start(
    backend="openai",
    model="gpt-4o",
    request_type="chat",
    session_id=session,
    prompt_tokens=est_prompt_tokens,
)

# streaming path
for chunk in stream:
    tracker.record_chunk(call_id, delta_tokens=chunk_tokens, delta_bytes=len(chunk.text))

tracker.finalize_call(
    call_id,
    completion_tokens=total_completion_tokens,
    success=True,
    error=None,
)

tracker.end_session(session)

session_stats = tracker.get_session_stats(session)
backend_stats = tracker.get_backend_stats(window="30d")
tracker.export_usage("reports/usage.json")
```
Key methods:
- `start_session(project_id: str | None) -> str`
- `end_session(session_id: str) -> SessionUsage`
- `register_call_start(...) -> str`
- `record_chunk(call_id: str, delta_tokens: int | None, elapsed_ms: float | None = None)`
- `record_error(call_id: str, error_code: str, message: str)`
- `record_fallback(call_id: str, to_backend: str, to_model: str)`
- `finalize_call(call_id: str, completion_tokens: int | None, success: bool, error: str | None = None)`
- `get_session_stats(session_id: str) -> SessionUsage`
- `get_backend_stats(window: str | tuple[datetime, datetime]) -> list[BackendUsageSummary]`
- `get_global_stats() -> BackendUsageSummary`
- `export_usage(path: str, format: "json" | "csv")`

## 4. Cost Estimation / Pricing Overlay
- Store pricing per backend/model in `PricingCatalog` (input/output cost per 1M tokens, currency).
- During `finalize_call`, compute:
  - `cost = (prompt_tokens * in_price + completion_tokens * out_price) / 1_000_000`
  - For local/free backends, prices default to zero.
- Pricing overrides loaded from config file (`~/.config/blueprint/pricing.json`) or embedded defaults; allow runtime updates.
- If token counts are unknown, allow estimation via prompt length heuristics and mark `estimated=True` in metadata.

## 5. CLI / UI Reporting Layout
- `/stats session` (current):
  - `Session ID`, duration, total requests
  - Tokens in/out, cost, errors, fallbacks
  - Per-backend table: requests | tokens_in | tokens_out | cost | errors | p95 latency
- `/stats model`:
  - Per-model aggregates (requests, tokens, cost, avg latency, errors)
- `/stats all` or `/stats lifetime`:
  - Cumulative totals (requests, tokens, cost) and top 3 backends by spend/usage.
- `/stats recent 24h`:
  - Time-windowed rollup (hourly buckets optional).
- Include a “budget” line if limits configured: e.g., `Monthly budget: $50, used $18.40 (36.8%)`.

## 6. Example Python Skeleton
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class UsageEntry:
    id: str
    session_id: str
    backend: str
    model: str
    request_type: str
    ts_start: datetime
    ts_end: Optional[datetime] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    fallback_from: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class UsageTracker:
    def __init__(self, storage, pricing):
        self.storage = storage
        self.pricing = pricing

    def register_call_start(self, backend, model, request_type, session_id, prompt_tokens=0, metadata=None) -> str:
        entry = UsageEntry(
            id=self._new_id(),
            session_id=session_id,
            backend=backend,
            model=model,
            request_type=request_type,
            ts_start=datetime.utcnow(),
            prompt_tokens=prompt_tokens,
            metadata=metadata or {},
        )
        self.storage.insert_entry(entry)
        return entry.id

    def record_chunk(self, call_id: str, delta_tokens: Optional[int], elapsed_ms: Optional[float] = None):
        self.storage.bump_tokens(call_id, delta_tokens or 0)
        if elapsed_ms:
            self.storage.bump_latency(call_id, elapsed_ms)

    def finalize_call(self, call_id: str, completion_tokens: Optional[int], success: bool, error: Optional[str] = None):
        entry = self.storage.get_entry(call_id)
        entry.completion_tokens = completion_tokens or entry.completion_tokens
        entry.ts_end = datetime.utcnow()
        entry.success = success
        if error:
            entry.error_message = error
            entry.success = False
        entry.cost = self.pricing.estimate(entry.backend, entry.model, entry.prompt_tokens, entry.completion_tokens)
        self.storage.update_entry(entry)
```

## 7. Limitations & Trade-offs
- Local backends may not report token counts; fallback to character-based estimates (imprecise).
- Streaming token counts may be unknown until final chunk; interim estimates may differ from final usage.
- Latency metrics depend on clock sync; per-chunk latency requires careful measurement to avoid overhead.
- Pricing changes over time; historical entries should store the applied price at call time to avoid recomputation drift.
- Aggregations over large JSONL logs can be slow; SQLite or incremental rollups recommended for scale.

## 8. Integration Guidance
- **Adapters**: Emit call lifecycle events (`register_call_start`, `record_chunk`, `finalize_call`, `record_error`).
- **Orchestrator/pipeline**: Wrap each provider call with tracker hooks; pass session_id from SessionManager.
- **UI/TUI**: Add `/stats` commands and a usage panel that queries tracker APIs.
- **Config**: Add pricing and budget fields; allow overrides via config file/env.
- **Logging**: Ensure sensitive prompt data is not persisted; store only counts/metadata.

## 9. LLM_USAGE.md (recommended content)
- What metrics are captured (requests, tokens, cost, errors, latency).
- Where data is stored (path to SQLite/JSONL), retention policy, how to reset/rotate.
- How to interpret stats for paid vs free backends; how costs are estimated.
- How to configure pricing and budgets; how to start a new billing cycle.
- Privacy/security notes (avoid storing raw prompts/responses unless user opts in).

---

Prompt (for traceability):
“You are a senior system architect specializing in multi-LLM orchestration and observability...” (full brief in request above).
