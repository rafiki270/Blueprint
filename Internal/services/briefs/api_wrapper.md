# Unified LLM Wrapper & Orchestrator — Architecture & Implementation Plan

## 0. Goals
Provide a single, model-agnostic API over multiple backends (local, primary cloud, fallback alternative, and Opus for planning) with streaming, tool-calling, usage tracking, and global credential management.

## 1. High-Level Design (Modules)
1. **Core Client (`LLMClient`)**
   - Public façade exposing `chat`, `generate`, `stream`, `list_models`, `get_usage`, `planning_mode`, `execute_tool`.
2. **Provider Adapters**
   - `LocalAdapter` (e.g., Ollama/DeepSeek), `CloudAdapter` (e.g., OpenAI), `FallbackAdapter` (another LLM provider), `OpusAdapter` (heavy reasoning).
   - Each implements unified interface, handles auth, request/response normalization, streaming.
3. **Adapter Factory & Router**
   - Creates adapters from config; routes per request based on provider hint, task type, fallback chain, quotas.
4. **Streaming Handler**
   - Normalizes streams into `StreamChunk`; detects malformed/incomplete output; can trigger retry/fallback.
5. **Credentials Manager**
   - Global (per-user) credential storage and loading; env overrides; secure file (e.g., `~/.config/blueprint/credentials.json` or OS keychain).
6. **Usage Tracker**
   - Per-call and per-provider usage (tokens, cost, latency, errors); exposes aggregated stats; supports quotas/budgets.
7. **Tool Engine**
   - Registry of tools (file ops, patch, tests, commands); executes with permission/approval; integrates with tool-calling responses from models.
8. **Cache Manager (optional)**
   - Prompt/response cache with TTL and size cap; supports server-side cache hints where available.
9. **Planning Mode Coordinator**
   - Uses Opus (heavy model) to create structured plans for complex tasks; consumes large context and produces steps.

## 2. Interface Definition / API Surface
- **Types**
  - `ChatMessage { role: "system"|"user"|"assistant"|"tool", content: string, name?: string, tool_call_id?: string }`
  - `ChatRequest { messages: ChatMessage[], model?: string, provider?: string, temperature?: number, max_tokens?: number, top_p?: number, stop?: string[], tools?: Tool[], metadata?: Record<string, any> }`
  - `ChatResponse { content: string, finish_reason?: string, usage?: UsageInfo, tool_calls?: ToolCall[], provider: string, model: string, metadata: Record<string, any> }`
  - `StreamChunk { delta: string, is_done: boolean, usage?: UsageInfo, tool_call?: Partial<ToolCall>, error?: Error, provider: string, model?: string }`
  - `UsageInfo { prompt_tokens: number, completion_tokens: number, total_tokens: number, estimated_cost?: number }`
  - `Tool { name: string, description: string, parameters: JSONSchema }`
  - `ToolCall { id: string, name: string, arguments: Record<string, any> }`
- **Public Methods (LLMClient)**
  - `chat(request: ChatRequest) -> ChatResponse`
  - `generate(request: { prompt: string, ... }) -> ChatResponse`
  - `stream(request: ChatRequest) -> AsyncIterator<StreamChunk>`
  - `list_models(provider?: string) -> ModelInfo[]`
  - `get_usage(filter?: UsageFilter) -> UsageStats`
  - `reset_usage()`
  - `planning_mode(context: PlanningContext) -> Plan`
  - `execute_tool(tool_call: ToolCall) -> ToolResult`
  - `register_tool(tool: Tool, handler: ToolHandler)`
  - `set_fallback_chain(chain: string[])`

## 3. Streaming Handling Logic
- Stream lifecycle: initiate → subscribe → validate chunks → finalize → retry/fallback on error.
- Chunk validation: ensure structure; accumulate text; detect malformed JSON/tool-calls.
- On error or truncation: classify (retriable vs fatal vs provider failure) → retry with backoff or switch to fallback adapter.
- Include usage in final chunk when provider supports it; otherwise estimate from length.

## 4. Credentials Management
- Global file `~/.config/blueprint/credentials.json` (chmod 600) with per-provider keys/base URLs; env vars override.
- Optional OS keychain integration; never log secrets.
- Access via `CredentialsManager.get(provider)` returning `{ api_key, base_url, extra }`.

## 5. Usage / Cost Tracking
- Capture per-call: provider, model, tokens in/out (if available), estimated cost, latency, success/error.
- Aggregate per provider/model/session/project; expose via `get_usage`.
- Budget/quota enforcement hooks: warn/block when exceeding configured thresholds.
- Pricing metadata per provider/model stored in config; cost = tokens * price/1k.

## 6. Model-Backend Abstraction & Routing
- `AdapterFactory.create(provider)` returns a concrete adapter.
- `FallbackManager` maintains ordered providers; orchestrator iterates on failure.
- Routing inputs: explicit `provider`, implicit by task type, context size, budget, or planning mode.
- Context shaping: trim/summarize to fit backend context window; local backend never receives whole project context.

## 7. Tool-Calling Support
- Tool definitions passed in `ChatRequest.tools`; adapters surface tool calls in responses/stream chunks.
- `ToolEngine` executes registered tools with approval/safety checks; returns `ToolResult` to be fed back as a message.
- Permissions: manual approval or trust/whitelist mode; audit every invocation.

## 8. Error Handling & Fallback
- Error categories: retriable (timeouts, 429, transient network), provider failure (auth/403), fatal (bad request).
- Retry with exponential backoff up to max attempts; on provider failure, move to next fallback.
- Structured validation for JSON/tool-call responses; if invalid, re-ask with clarification or fallback.

## 9. Caching (Optional)
- Prompt/response cache with TTL and size cap; keyed by messages+model+params hash.
- Provider cache hints (e.g., Anthropic prompt caching) respected when available.

## 10. Planning Mode
- Dedicated coordinator using Opus/Review backend:
  - Input: goal, requirements, constraints, previous plans, codebase context.
  - Output: structured `Plan { overview, steps[], estimated_complexity, suggested_models, metadata }`.
  - Uses heavy model and may chain retrieval/summarization to fit context.

## 11. Sample Pseudocode (TypeScript-like)
```ts
const client = new LLMClient({
  credentialsManager,
  fallbackChain: ["local", "cloud", "fallback", "opus"],
});

// Simple chat
const resp = await client.chat({
  messages: [{ role: "user", content: "Explain streaming APIs." }],
  model: "gpt-4o",
  provider: "cloud",
});
console.log(resp.content);

// Streaming with fallback
for await (const chunk of client.stream({
  messages: [{ role: "user", content: "Write a quicksort in Python." }],
  provider: "local",
})) {
  if (chunk.error) {
    console.warn("Stream issue; switching to fallback...");
    client.setFallbackChain(["cloud"]);
  } else {
    process.stdout.write(chunk.delta);
  }
}

// Planning mode
const plan = await client.planning_mode({
  goal: "Add auth to the service",
  requirements: ["JWT", "RBAC", "tests"],
});
console.log(plan.steps);
```

## 12. Implementation Phases
1) Define core types and `LLMClient` interface; build `CredentialsManager` and `UsageTracker`.
2) Implement adapters (local, cloud, fallback, Opus) with chat/stream/list_models.
3) Add `AdapterFactory`, fallback routing, retry/backoff, streaming handler.
4) Integrate tool-calling (`ToolEngine`) and approval/permission hooks.
5) Add planning coordinator and cost/budget enforcement.
6) Add caching and optional prompt-caching hooks.
7) Harden validation, error reporting, and add unit/integration tests.
