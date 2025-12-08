# Multi-LLM Orchestration Architecture — Python Design Spec

## 1) Modules / Components
- **Backend Wrapper Module**
  - `LLMBackend` abstract class: unified `chat`, `stream`, `tool_call`, `reset_context`, `get_usage`.
  - Concrete adapters: `LocalBackend` (small context), `FastBackend` (parser/fallback), `ReviewBackend` (heavy reasoning), `PlannerBackend` (Opus/planning).
  - Persona store per backend (editable/resettable).
- **Context Manager / Memory Store**
  - Short-term session context (conversation buffers per backend).
  - Persistent project memory (facts/config/history/metadata) stored outside LLM context; retrieval provides scoped excerpts.
  - Summarization/indexing for long files/history; enforce context limits per backend.
  - Supports context reset per backend and shared/global context fetch on demand.
- **Tool-Runner Module**
  - Executes tool calls (files, commands, search, tests, patch apply) via safe wrappers.
  - Permission modes: manual approval vs trust/whitelist per project.
  - Sandboxing and auditing of tool executions; structured results.
- **Orchestrator / Router Module**
  - Decides backend per request based on role/persona, task type, cost/budget, context size.
  - Handles fallback chains and retries; selects streaming vs non-streaming.
  - Manages persona injection and per-backend context resets.
- **Streaming Interface / Adapter**
  - Normalizes streaming responses into `ChatChunk`.
  - Validates final output (JSON/tool-call) and can trigger retry/fallback on malformed output.
  - Supports incremental usage accounting during stream.
- **Config & Credentials Module**
  - Global credentials store (env/secure file) for providers.
  - Per-project config: default personas, backend selection rules, approval mode, budgets/quotas.
- **Usage & Metrics Module**
  - Tracks per-backend calls, tokens in/out, cost estimates, errors.
  - Exposes session/project/lifetime stats; quota enforcement hooks.
- **Tasks & Workflow Module**
  - Task model (id, title, type, status, history, context handle).
  - Task queue with task-scoped context and results.
  - Hooks to orchestrator for routing and to tool-runner for execution steps.

## 2) Public Python API (Pseudocode)
```python
from typing import Protocol, Iterator, AsyncIterator, TypedDict, Optional, List, Dict

class Message(TypedDict):
    role: str  # system|user|assistant|tool
    content: str
    name: str | None
    tool_call_id: str | None

class ChatResponse(TypedDict):
    content: str
    finish_reason: str | None
    tool_calls: list[ToolCall]
    usage: UsageStats
    raw: dict

class ChatChunk(TypedDict):
    delta: str
    tool_call: ToolCall | None
    is_done: bool
    usage: UsageStats | None
    error: str | None

class Persona(TypedDict):
    name: str
    description: str
    system_prompt: str

class UsageStats(TypedDict):
    requests: int
    prompt_tokens: int
    completion_tokens: int
    cost: float
    errors: int

class LLMBackend(Protocol):
    name: str
    persona: Persona
    context_window: int

    def chat(self, messages: List[Message], *, max_tokens: int | None = None,
             temperature: float = 0.0) -> ChatResponse: ...

    def stream(self, messages: List[Message], *, max_tokens: int | None = None,
               temperature: float = 0.0) -> Iterator[ChatChunk]: ...

    def reset_context(self) -> None: ...

    def get_usage(self) -> UsageStats: ...

class Orchestrator:
    def __init__(self, backends: Dict[str, LLMBackend], context_store, tool_runner, usage_tracker, config): ...
    def set_persona(self, backend: str, persona: Persona) -> None: ...
    def reset_persona(self, backend: str) -> None: ...
    def route(self, task_type: str, content_size: int | None = None) -> LLMBackend: ...
    def chat(self, messages: List[Message], *, task_type: str, stream: bool = False,
             max_tokens: int | None = None, temperature: float = 0.0) -> ChatResponse | Iterator[ChatChunk]: ...
    def reset_backend_context(self, backend: str) -> None: ...

class ContextStore:
    def get_session_context(self, session_id: str, backend: str) -> List[Message]: ...
    def append_session(self, session_id: str, backend: str, messages: List[Message]) -> None: ...
    def reset_backend(self, session_id: str, backend: str) -> None: ...
    def fetch_project_facts(self, keys: List[str], max_tokens: int) -> str: ...
    def summarize_file(self, path: str, max_tokens: int) -> str: ...

class ToolRunner:
    def run_tool(self, name: str, args: dict, session_id: str) -> dict: ...
    def set_mode(self, mode: Literal["manual", "trust"]) -> None: ...
    def whitelist(self, tools: List[str]) -> None: ...

class UsageTracker:
    def record_call(self, backend: str, stats: UsageStats) -> None: ...
    def get_backend_usage(self, backend: str) -> UsageStats: ...
    def get_totals(self) -> UsageStats: ...
    def enforce_quota(self, backend: str, delta_cost: float) -> None: ...

class Task(TypedDict):
    id: str
    title: str
    type: str  # parse|code|review|plan|chat
    status: str
    session_id: str
    context_keys: list[str]
    history: list[dict]
```

## 3) Routing & Fallback Logic
- Map task types to personas/backends:
  - `plan/review/deep`: heavy/reviewer backend.
  - `parse/fallback/cleanup`: fast backend.
  - `code/short`: local backend if context fits; otherwise fast backend.
  - `planner`: Opus-style planner backend for meta/orchestration.
- Fallback chain: on error/429/malformed output → retry same backend (with backoff) → fallback to next backend by cost/capability.
- Respect context_window: if projected prompt > backend limit, downscope via summarization/snippet extraction or route to larger backend.
- Allow manual override via config or per-call hints.

## 4) Context Management Strategy
- **Per-backend buffers**: Session-level message buffers; resettable via `reset_backend_context`.
- **Project memory**: Stored outside LLM context (files, facts, embeddings). Retrieval provides excerpts/summaries tailored to backend limits.
- **Role/persona injection**: prepend persona system prompt per backend; editable and resettable to defaults.
- **Context shaping**: estimate token budget per backend; include only necessary snippets (files, task description, recent history).
- **Reset controls**: API to wipe backend-specific conversation state without affecting project memory.

## 5) Tool-Calling & Permissions
- Tools exposed uniformly; orchestrator mediates execution.
- Modes:
  - **Manual**: require user approval for any tool that writes/modifies or executes commands.
  - **Trust**: allowlisted tools run automatically; others prompt for approval.
- Audit log per tool call: requester, tool, args, timestamp, result, approval status.
- Safety: path normalization, sandbox/working-directory enforcement, command timeouts, output size caps.

## 6) Streaming Handling
- Stream adapters yield `ChatChunk`.
- Track partial usage; aggregate usage at end (if provider returns usage) or estimate.
- Validate final output (JSON/tool-call schema). If malformed or truncated: request regeneration or fallback backend.
- Support mid-stream tool-call detection; orchestrator can pause stream, execute tool, and resume with new messages if supported.

## 7) Usage Tracking & Quotas
- Per-backend counters: requests, tokens in/out, cost, errors.
- Session/project totals; budgets per backend/project.
- Hooks in orchestrator: before call enforce remaining budget; after call update tracker; on stream, update incrementally if possible.
- Expose metrics to CLI/TUI (`/stats`, dashboards).

## 8) Tasks & Workflow
- Task abstraction: includes type, status, context keys, history of messages/tools/results.
- Task queue: sequential or prioritized; each task uses orchestrator to choose backend and tool-runner for actions.
- Result persistence: store outputs, applied patches, and usage per task.
- Integration with context store: task context keys pull relevant facts/files/summaries into prompts.

## 9) Config & Credentials
- Config file (per project + global) defining:
  - Backend endpoints/keys, default models, personas.
  - Routing rules (task→backend), budget/quotas, approval mode, tool whitelist.
  - Context limits per backend (max tokens, max snippets).
- Credentials manager: env + secure file; never logged; injectable into backends.

## 10) Implementation Roadmap (Phased)
1) **Backends & Interfaces**: Define `LLMBackend` base, implement adapters (local, fast, review, planner). Add personas and resettable contexts.
2) **Context Store**: Session buffers + project memory fetch; token budgeting and truncation helpers.
3) **Orchestrator/Router**: Routing rules, fallback, persona injection, context shaping; sync + streaming paths.
4) **Tool Runner + Permissions**: Tool registry, sandboxing, approval modes, audit logging.
5) **Usage Tracker**: Per-backend counters, budgets/quotas, CLI/TUI stats.
6) **Tasks & Workflow**: Task model, queue, history; integrate with orchestrator and tools.
7) **Validation & Recovery**: Streaming validation, malformed-output handling, retry/fallback strategies.
8) **Documentation & Examples**: Developer guide, config reference, persona defaults, `/stats` and `/mode` commands.

## Implementation Checklist
- [ ] Backend interfaces and adapters (local, fast, review, planner) wired into orchestrator
- [ ] Session/persistent context store with persona injection and context shaping
- [ ] Router/fallback logic with task-type routing and budget awareness
- [ ] Tool runner with permission modes and audit logging
- [ ] Usage tracking hooks in orchestrator calls
- [ ] Task queue with task-scoped context/history
- [ ] Streaming validation and recovery paths
- [ ] Developer docs and CLI commands for stats/mode/persona
