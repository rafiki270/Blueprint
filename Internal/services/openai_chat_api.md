✅ OpenAI Chat Completions API (ChatGPT-style) — Reference

Base endpoint
- POST https://api.openai.com/v1/chat/completions
- Headers: Authorization: Bearer <YOUR_API_KEY>, Content-Type: application/json

Core request body
```json
{
  "model": "gpt-4o", // e.g. gpt-4o, gpt-4, gpt-3.5-turbo
  "messages": [
    { "role": "system", "content": "You are a helpful coding assistant." },
    { "role": "user",   "content": "Write a function to reverse a string in Python." }
  ]
}
```

Common optional params
- temperature (float) — randomness; lower = more deterministic.
- top_p (float) — nucleus sampling alternative to temperature.
- n (int) — number of completions to generate (cost scales).
- stop (string|string[]) — stop sequences (max 4).
- max_tokens — cap output tokens (mind context limit).
- stream (bool) — stream tokens incrementally.
- stream_options.include_usage (bool) — include usage in final stream chunk.
- logit_bias (object) — bias specific tokens.
- presence_penalty / frequency_penalty — adjust repetition.
- Function/tool-calling — declare functions/tools and let model emit a call (name + arguments) instead of free text.
- Response/JSON mode — some SDKs support a “JSON mode” / structured output flag to enforce valid JSON; otherwise, prompt for structured output explicitly.

Response (non-stream)
- choices[0].message.content — primary reply.
- usage — token usage (prompt, completion, total).

Streaming
- Set "stream": true.
- Response is SSE chunks with incremental deltas: chunk.choices[0].delta.content.
- Optionally include usage in the final chunk: "stream_options": { "include_usage": true }.

Example request (streaming + usage)
```json
{
  "model": "gpt-4o",
  "messages": [
    { "role": "system", "content": "You are a helpful coding assistant." },
    { "role": "user", "content": "Generate a hello-world in Rust." }
  ],
  "temperature": 0.2,
  "stream": true,
  "stream_options": { "include_usage": true }
}
```

Function/tool-calling pattern
- Declare functions/tools schema in the request.
- Let the model return a function call with name + JSON arguments.
- Your orchestrator parses the call, executes the tool, then (optionally) feeds the result back in the next message.

Rate limits / billing (important)
- RPM (requests/min) and TPM (tokens/min) limits vary by account/tier; no “remaining quota” endpoint.
- Each call returns usage; track it. With streaming, request include_usage.
- Implement retry/backoff on HTTP 429 (rate limits).
- Token budgeting: trim/summarize history; don’t exceed context window or TPM budgets.

Practical guidance for agents
- Track per-call usage; maintain in-process RPM/TPM/cost guards.
- Enforce max prompt/output tokens; summarize or drop older context.
- Use cheaper models for parsing/formatting; reserve higher models for critical steps.
- Add backoff/fallbacks for 429s or timeouts.

Minimal curl example
```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "model": "gpt-4o",
        "messages": [
          { "role": "system", "content": "You are a helpful coding assistant." },
          { "role": "user", "content": "Write a function to reverse a string in Python." }
        ],
        "temperature": 0.2
      }'
```

Minimal streaming pseudo-code (Python-like)
```python
resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    stream=True,
    stream_options={"include_usage": True},
)
for chunk in resp:
    delta = chunk.choices[0].delta
    if delta and delta.content:
        print(delta.content, end="")
# Final chunk includes usage if include_usage was set.
```

✅ List available models
- GET https://api.openai.com/v1/models
- Headers: Authorization: Bearer <YOUR_API_KEY>

Example (curl):
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

Example (Python):
```python
from openai import OpenAI
client = OpenAI(api_key="YOUR_KEY")
models = client.models.list()
for m in models.data:
    print(m.id)
```

Caveats:
- Returned list may include models not compatible with all endpoints; you may need to filter (e.g., chat-compatible).
- Capabilities/availability depend on account tier/verification.
- Model metadata doesn’t always spell out supported endpoints; expect to try/catch or maintain a known-good list.
