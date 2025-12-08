## Ollama API quick reference

### Core endpoints
- Generate (streaming text): `POST /api/generate`  
  Example:  
  ```bash
  curl http://localhost:11434/api/generate -d '{
    "model": "deepseek-coder:latest",
    "prompt": "Write a function to reverse a string in Python."
  }'
  ```  
  Streaming responses resemble:  
  ```
  {"response":"def reverse_string(s):","done":false}
  {"response":"\n    return s[::-1]","done":false}
  {"done":true}
  ```

- Chat (messages): `POST /api/chat`  
  Example:  
  ```bash
  curl http://localhost:11434/api/chat -d '{
    "model": "deepseek-coder:latest",
    "messages": [
      {"role": "user", "content": "Explain decorators in Python."}
    ]
  }'
  ```

- Pull model: `POST /api/pull`  
  ```bash
  curl http://localhost:11434/api/pull -d '{
    "name": "deepseek-coder:latest"
  }'
  ```
- List models: `GET /api/tags`
- Delete model: `DELETE /api/delete`

### Tool-calling / structured output (prompt-enforced)
- No built-in tool schema; enforce via prompting. Example schema prompt:  
  ```json
  {
    "response_format": {
      "type": "json",
      "schema": {
        "tool": "string",
        "arguments": "object"
      }
    }
  }
  ```
- Example tool-call prompt:  
  ```
  You are a coding agent. Respond only with a JSON object:
  {
    "tool": "apply_patch",
    "arguments": { ... }
  }
  ```
- DeepSeek models follow structured JSON reliably when instructed.

### Minimal Blueprint-style call (non-streaming)
```javascript
async function callOllama(prompt) {
  const res = await fetch("http://localhost:11434/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "deepseek-coder:latest",
      prompt,
      stream: false
    })
  });
  return await res.json();
}
```

### Streaming
- Supported by default on `/api/generate` and `/api/chat`; set `"stream": true` (default) or `"stream": false` for full responses.
- Tool-calling can stream; handle mid-stream tool signals and resume after execution.
- Thinking traces may appear in a `thinking` field on capable models.
- SDK note: REST defaults to streaming; some SDKs require `stream=True`.
- Ensure your transport forwards chunked responses; avoid buffering when proxying.

Chat streaming (curl):
```bash
curl http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
        "model": "llama3.1",
        "messages": [
          { "role": "user", "content": "Write a Python function to reverse a string." }
        ],
        "stream": true
      }'
```

Chat streaming (Python, official lib):
```python
import ollama

stream = ollama.chat(
    model="llama3.1",
    messages=[{"role": "user", "content": "Write a reverse_string function in Python"}],
    stream=True
)

for chunk in stream:
    print(chunk["message"]["content"], end="", flush=True)
```
