✅ Gemini API (Google AI / Vertex AI) — Overview for Blueprint

What exists (late 2025)
- Public REST API + official SDKs (text, chat, multimodal).
- Requires API key (Google AI Studio / Google Cloud / Vertex AI) with billing/permissions.
- Supports streaming, function/tool-calling, structured JSON output, multimodal inputs (text, image, audio, video), and a Live API for low-latency/voice/video.

Core endpoints
- Non-streaming: POST https://generativelanguage.googleapis.com/v1beta/models/<model-id>:generateContent
- Streaming: POST https://generativelanguage.googleapis.com/v1beta/models/<model-id>:streamGenerateContent?alt=sse&key=<KEY> (SSE chunks)
- Live API: real-time/bidirectional (WebSocket/stream) for voice/video agents.

Request shape (text-only example)
```json
{
  "contents": [
    { "parts": [ { "text": "Write a Python function to reverse a string." } ] }
  ],
  "model": "gemini-2-flash",
  "temperature": 0.2
  // add tools/functions, JSON mode, multimodal parts, etc.
}
```

Streaming example (curl)
```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2-flash:streamGenerateContent?alt=sse&key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [
      { "parts": [ { "text": "Write a Python function to reverse a string." } ] }
    ],
    "model": "gemini-2-flash"
  }'
```

SDK streaming example (pseudo-Python)
```python
from google.genai import Client
client = Client(api_key=GEMINI_API_KEY)

stream = client.stream_generate_content(
    model="gemini-2-flash",
    contents=[{"parts":[{"text":"Generate a JSON patch to update foo()"}]}]
)

for chunk in stream:
    print(chunk.get("text", ""), end="")
```

Features to leverage
- Function/tool-calling: declare functions/tools and parse returned calls (name + JSON args).
- Structured/JSON mode: constrain outputs to JSON for automation.
- Multimodal: send text + images/audio/video if needed.
- Streaming: incremental output for CLI responsiveness.
- Thinking/reasoning traces: models may emit intermediate reasoning depending on settings/model.

Caveats / considerations
- Quotas/costs vary by model and account; large multimodal inputs incur latency/cost.
- SDK defaults differ (streaming may be off by default).
- Tool-calling + streaming + multimodal increases orchestration complexity; ensure you handle partial/tool-call chunks correctly.

Use in Blueprint
- Treat Gemini as a backend for parsing/spec-normalization, fallback coding, and structured outputs.
- Use streaming for interactive console UX; use JSON/tool-calls for patch/test orchestration.
- Maintain your own rate/usage tracking; handle retries/backoff on quota errors.

✅ List models & streaming/generation notes
- List models: GET https://generativelanguage.googleapis.com/v1beta/models (params: pageSize, pageToken). Response: list of model objects (ids like models/gemini-2.5-flash, baseModelId, version).
- Streaming: use streamGenerateContent for chunked output; generateContent for one-shot.
- SDKs expose list/generate/stream methods (e.g., generateContentStream/streamGenerateContent).
- Quotas: enforced per project/key; see Cloud console/AI Studio for limits (requests, token usage). Billing is per token (input + output + cached).
- Context windows can be very large (e.g., Flash ~1M tokens); output caps vary by model. Token-counting APIs exist to preflight prompts.
- Monitoring: use Cloud console dashboards/logging for requests, token usage, cost, errors; compute/track in-app for per-task budgeting.

Practical guidance
- Discover models dynamically via the list endpoint; filter for chat/coding-capable models.
- Use streaming for UX; use token-counting to stay within limits; implement backoff for quota/rate limits.
- Prefer cheaper models for frequent/light tasks; reserve heavy models for long reasoning/multimodal.
