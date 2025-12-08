# CLI Reference Notes for LLM Wrappers (2025)

Collected, actionable details for Blueprint LLM CLI wrappers (Claude, Gemini, DeepSeek/Ollama, Codex). Use these to align subprocess calls and flags.

## Claude Code CLI
- **Defaults**: Interactive REPL; use `-p/--print` for non-interactive output.
- **Models**: `--model <name>` (e.g., `claude-sonnet-4-5-20250929`); `--fallback-model` supported.
- **Output**: `--output-format text|json|stream-json` (with `--print`). `--include-partial-messages` works with `stream-json`.
- **Prompts**: Positional prompt or `-p "prompt"` (non-interactive). `--system-prompt`, `--append-system-prompt` available.
- **Sessions**: `--continue`, `--resume`, `--session-id`, `--fork-session`.
- **Tools / access**: `--tools/--allowed-tools/--disallowed-tools`, `--add-dir`, `--permission-mode`, `--dangerously-skip-permissions` (use carefully).
- **MCP/Plugins**: `claude mcp`, `--mcp-config`, `--strict-mcp-config`, `--plugin-dir`, `--disable-slash-commands`.
- **Auth/env**: `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL` (and other Anthropic/Bedrock vars).

## Gemini CLI
- **Defaults**: Interactive REPL; positional prompt preferred. `-p/--prompt` is deprecated but still works; `-i/--prompt-interactive` runs prompt then stays interactive.
- **Models**: `-m/--model <name>`; supports 3.x (e.g., `gemini-3-pro-preview`) when enabled.
- **Sandbox/tools**: `-s/--sandbox` to enable tool/shell actions; `--approval-mode default|auto_edit|yolo`; `-y/--yolo` auto-approves everything.
- **Output**: `-o/--output-format text|json|stream-json`.
- **Sessions**: `--resume`, `--list-sessions`, `--delete-session`.
- **Debug**: `-d/--debug` verbose; `--include-directories` to expand workspace; `--extensions`/`--list-extensions`; `allowed-tools`, `allowed-mcp-server-names`.
- **Auth**: Typically via `GOOGLE_GENERATIVE_AI_API_KEY` (per community); CLI handles login; preview features may be needed for 3.x models.
- **Example one-shot**: `gemini -m gemini-3-pro-preview -p "Explain X"`, or positional: `gemini -m gemini-3-pro-preview "Explain X"`.

## DeepSeek via Ollama
- **CLI**: `ollama run <model> "prompt"`. Other commands: `list`, `pull`, `ps`, `stop`, `show`, `create`, `rm`.
- **Wrapper strategy**: Only verify `ollama` binary exists; do not enforce model presence—use user’s configured models. Streaming via standard stdout lines.
- **Flags** (per `ollama run --help`): can pass `--keepalive`, `--verbose`, etc. if needed; current wrapper keeps args minimal unless extended.
- **Env**: N/A specific; relies on local Ollama setup.

## Codex CLI (openai/codex)
- **Defaults**: Interactive agent by default; subcommands: `exec`, `review`, `login/logout`, `mcp`, `sandbox`, `resume`, `features`, etc.
- **Config**: `~/.codex/config.toml`; overrides via `-c/--config key=value` (TOML-parsed), feature toggles `--enable/--disable`.
- **Models**: `-m/--model`; `--oss` + `--local-provider` to target LM Studio/Ollama.
- **Sandbox/approvals**: `-s/--sandbox read-only|workspace-write|danger-full-access`; `-a/--ask-for-approval untrusted|on-failure|on-request|never`; `--full-auto` convenience; `--dangerously-bypass-approvals-and-sandbox` (avoid unless sandboxed).
- **Workspace**: `-C/--cd`, `--add-dir`, `--search` (web search tool).
- **Images**: `-i/--image` attach images to prompt.
- **Modes**: `codex exec` for non-interactive; interactive supports slash commands (/status, /mcp, /logout, /quit).
- **Sampling/streaming**: Not publicly exposed; CLI is agentic, not a raw completion API.

## General wrapper guidance
- Prefer non-interactive flags (`-p/--print` or `-p/--prompt`) for one-shot calls; leave interactive/REPL to higher-level app modes.
- Allow user-provided CLI defaults; avoid hardcoding models—expose `extra_args` for caller to pass `--model`, sandbox, or approval flags.
- Streaming: Claude supports `--output-format=stream-json`; Gemini offers `stream-json`; Ollama streams stdout by default; Codex lacks explicit stream flag—treat as non-streaming.
- Availability checks: `which <cli>` only, except Ollama model presence is not enforced to respect user setup.
