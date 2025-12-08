# File Access & Context Management Subsystem — Design Spec

## 1) Architecture & Components
- **File Registry / Metadata Store**
  - Tracks file paths, sizes, hashes, last modified timestamps, version ids, tags (doc/config/code/test), and opt-in sensitivity flags.
  - Persists lightweight index (JSON/SQLite) for fast lookups; refreshed on startup and after writes.
- **Context Retrieval Module**
  - Serves backend requests for file content: full file, line ranges, or diff context.
  - Enforces content shaping rules per backend (local models get minimal snippets; cloud/review models can receive richer context).
  - Supports chunking for large files and token-aware truncation with summaries.
- **Session / Context Manager**
  - Maintains session-level stack: recent reads, open buffers, pending edits, uncommitted changes, active tasks.
  - Merges with project-level metadata to avoid stale reads; detects when requested content is outdated.
- **Tool-Call Interface (backend-agnostic)**
  - Standard tools: `list_files`, `read_file`, `read_lines`, `write_file`, `apply_patch`, `get_diff`, `file_history`, `summarize_file`.
  - All mediated by orchestrator with permission checks and audit logging.
- **Conflict Detection & Merge Module**
  - Compares incoming edits against current filesystem + last-known hash/line-range context.
  - Flags overlaps/stale patches; routes to heavy/review backend (e.g., Claude) or requests user approval for merge proposals.
- **Cache / Summarization / Indexing Module**
  - Stores token-efficient summaries for large files; caches recent snippets; optional semantic index for retrieval.
  - Provides “overview excerpts” for entrypoint docs (e.g., AGENTS.md, README.md) at startup.
- **Audit & Log Module**
  - Records all file-access tool calls with caller, timestamps, arguments, results, and before/after hashes or diffs.
  - Supports replay/rollback and traceability for compliance and debugging.

## 2) Unified API / Interface (Python-style)
```python
class FileAccessInterface:
    def list_files(self, globs: list[str] | None = None) -> list[str]: ...
    def read_file(self, filepath: str) -> str: ...
    def read_lines(self, filepath: str, start: int, end: int) -> str: ...
    def get_excerpt(self, filepath: str, max_lines: int = 80) -> str: ...
    def apply_patch(self, filepath: str, patch: str) -> PatchResult: ...
    def write_file(self, filepath: str, content: str, mode: str = "truncate") -> PatchResult: ...
    def get_diff(self, filepath: str, version1: str | None, version2: str | None) -> str: ...
    def get_file_history(self, filepath: str) -> list[FileVersionMeta]: ...
    def summarize_file(self, filepath: str, max_tokens: int) -> str: ...

class PatchResult(TypedDict):
    success: bool
    message: str
    conflict: bool
    diff: str
    version_id: str
```
All methods callable via tool-calling; orchestrator injects permission checks and audit logging before dispatch.

## 3) Workflow / Usage Patterns
- **Startup**
  - Build/refresh registry; identify entrypoint docs (AGENTS.md, README.md, config/manifest).
  - Produce truncated summaries/excerpts and paths; preload into session context presented to LLM.
- **Read flow**
  - Backend requests `read_lines(file, 50, 80)` → orchestrator verifies allowlist, reads, logs, returns snippet.
  - For local models, enforce minimal snippet and avoid large context unless explicitly approved.
- **Edit flow**
  - Backend proposes patch → orchestrator runs conflict detection (hash + range check). If clean, apply; else raise conflict and optionally route to review backend for merge proposal.
  - After apply: update registry, history, summaries; log audit.
- **Diff/history**
  - `get_diff` returns diff between versions or working tree vs last saved.
  - `file_history` lists version ids, timestamps, authors (caller), hashes.
- **Session context**
  - Maintain recent reads and writes; prioritize serving deltas/summaries to conserve tokens.

## 4) Documentation Spec (`LLM_FILE_ACCESS.md`)
- **Overview & Purpose**
- **Registry Schema** (fields: path, size, hash, mtime, tags, sensitivity)
- **Tool-Call Definitions** (arguments, return types, example tool JSON)
- **Permission & Approval Policy** (allowlist globs, manual approval rules, restricted paths)
- **Conflict Resolution Workflow** (detection, escalation to review model, user approval)
- **Logging/Audit Format** (per-call JSON fields: caller, tool, args, timestamp, success, hashes)
- **Usage Guidelines for LLMs** (be explicit with path + line range; do not assume whole repo is available)
- **Examples** (read lines, apply patch, diff request)
- **Safety Notes** (prompt-injection cautions, sensitive files, path normalization)
- **Reset/Rotation** (how to rotate logs/history, clear cache/summaries)

## 5) Security, Safety, Prompt-Design
- Enforce allowlist/denylist for file paths; normalize and reject path traversal.
- Require approvals for writes/patches outside workspace or sensitive globs.
- Never auto-send entire repo; prefer minimal snippets + summaries, especially to local/low-context models.
- Strip/escape user-provided paths in prompts; include explicit delimiters around injected file content.
- Avoid embedding secrets; redact known credential patterns in summaries.
- Log all tool invocations with caller identity and outcome.

## 6) Justification & Trade-offs
- **Pros**: Efficient token use, safer edits, reproducible history, backend-agnostic API, conflict-aware merges, auditable actions.
- **Cons**: Added complexity; potential stale summaries; conflict detection may need retries; maintaining indexes/summaries introduces overhead.

## 7) Phased Implementation / Roadmap
1. **MVP**: Registry builder + `list_files`, `read_file`, `read_lines`, basic audit logging.
2. **Tool Integration**: Expose unified tool schema; permission/approval checks; session context stack.
3. **Write Path**: `write_file`, `apply_patch`, conflict detection (hash/range), diff output.
4. **History/Audit**: Version metadata store, `file_history`, `get_diff`, rollback hooks.
5. **Summaries/Cache**: File summaries for large files; token-aware excerpts; optional semantic index.
6. **Conflict Resolution**: Automated merge suggestions via review backend; user-approved merges.
7. **Docs/UI**: Publish `LLM_FILE_ACCESS.md`; add `/files`, `/open`, `/patch`, `/stats files` commands in CLI/TUI; budget/limits for read/write operations.
