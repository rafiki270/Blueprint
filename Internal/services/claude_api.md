✅ Claude API (Anthropic) — Integration Notes for Blueprint

Server host
- Anthropic platform API base: https://api.anthropic.com (Messages/Models APIs; requires API key and anthropic-version header).
- If using a cloud wrapper (e.g., AWS Bedrock, Google Vertex), use the provider’s endpoint with Claude model IDs.
- Preferred model for Blueprint architecture: use the latest Opus (e.g., claude-opus-*-latest) for top-tier reasoning/architecture tasks.

Models & discovery
- List models via Models API (e.g., GET /v1/models on Claude platform or provider wrappers) to discover available IDs (e.g., claude-sonnet-4.5, opus, haiku).
- Use dynamic discovery instead of hard-coding; choose lighter vs heavy models per task.

Core endpoints (chat/messages)
- Chat-style/messages API (e.g., POST /v1/messages): send messages array (role + content), get reply.
- Legacy prompt→completion may exist on some providers.

Key request params (messages API)
- model (required): e.g., claude-sonnet-4.5-YYYYMMDD.
- messages: [{role: "user"/"assistant"/"system", content: "..."}].
- max_tokens_to_sample (or similar): cap output tokens.
- temperature/top_p: sampling controls.
- tools/tool-use: declare tools/functions with JSON schemas to enable tool calls.
- Headers/versioning: include API key and required version headers (e.g., anthropic-version).
- Fine-grained tool streaming header (e.g., fine-grained-tool-streaming-2025-05-14) for tool-call streams.

Streaming & tool-use
- Streaming supported (SSE/chunked) for chat; use provider stream variants (e.g., InvokeModelWithResponseStream on Bedrock/Vertex).
- Tool-use supported; fine-grained tool streaming streams tool-call args mid-stream.
- Be prepared to reassemble/validate JSON across chunks; handle truncation.

Context, limits, usage
- Large context (up to ~1M tokens on newer models like Sonnet 4.x). Budget tokens; trim/summarize before sending huge contexts.
- Rate/throughput limits enforced; implement backoff/fallback.
- Usage/cost reporting endpoints (org-level) exist for aggregated stats; per-call usage may depend on provider.

Practical cautions
- Model list may not include capability matrix; maintain a known-good set for chat/tool use.
- Streaming + tool calls + large payloads can produce big token usage; watch cost/performance.
- Ensure SDK/provider supports streaming/tool-streaming; otherwise use raw HTTP.
- Sandbox external tool execution in your agent.

Why use Claude in Blueprint
- Agent-friendly: tool calls, streaming, large context; good for code agents (patch/apply/test).
- Choose model by task criticality: lighter for quick steps, heavy for deep context/reasoning.
- Use usage/cost reporting to keep budgets in check.
