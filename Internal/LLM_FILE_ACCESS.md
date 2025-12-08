# LLM File Access & Context Management Subsystem

## Executive Summary

This document specifies a production-ready file-access and context-management subsystem for a multi-LLM platform. The system provides intelligent, secure, and context-aware file operations while respecting each backend's memory constraints. It automatically loads project metadata at startup, supports granular file access (full/partial/diff), maintains edit history with conflict detection, and enforces permission-based security through a tool-call interface.

**Key Innovation:** The system never feeds full repository context to local/small models. Instead, it provides minimal, task-relevant file snippets on demand, with automatic context distillation for large files.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Components](#2-components)
3. [Python API Interface](#3-python-api-interface)
4. [Initialization & Metadata Loading](#4-initialization--metadata-loading)
5. [File Access Workflows](#5-file-access-workflows)
6. [Conflict Detection & Resolution](#6-conflict-detection--resolution)
7. [Permission & Security Model](#7-permission--security-model)
8. [Caching & Summarization](#8-caching--summarization)
9. [Audit & Logging](#9-audit--logging)
10. [Integration with Orchestrator](#10-integration-with-orchestrator)
11. [Implementation Roadmap](#11-implementation-roadmap)
12. [Security & Prompt Injection Defense](#12-security--prompt-injection-defense)
13. [Trade-offs & Justification](#13-trade-offs--justification)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   LLM Orchestrator                          │
│           (Routes requests, manages backends)               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              File Access Interface (Tool API)               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Tool Registry                                        │  │
│  │  - list_files()                                       │  │
│  │  - read_file() / read_lines()                         │  │
│  │  - write_file() / apply_patch()                       │  │
│  │  - get_file_diff() / get_file_history()              │  │
│  │  - get_file_metadata()                                │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬─────────────┬──────────────┐
        ▼            ▼            ▼             ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐
│File Registry │ │ Context  │ │ Conflict │ │  Cache  │ │  Audit   │
│   Manager    │ │ Retriever│ │ Detector │ │ Manager │ │  Logger  │
└──────────────┘ └──────────┘ └──────────┘ └─────────┘ └──────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    File System Storage                      │
│  ┌──────────────┬──────────────┬─────────────────────────┐ │
│  │ Project Files│ Metadata DB  │ Session State           │ │
│  │ (actual .py, │ (SQLite)     │ (.blueprint/session.db) │ │
│  │  .md, etc.)  │              │                         │ │
│  └──────────────┴──────────────┴─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.1 Design Principles

1. **Minimal Context** - Never send full repo to LLMs; provide only requested snippets
2. **Lazy Loading** - Load file content on demand, not at startup
3. **Granular Access** - Support full file, line ranges, or diff contexts
4. **Version Tracking** - Maintain edit history with timestamps and diffs
5. **Conflict Awareness** - Detect and resolve edit conflicts automatically
6. **Permission-Based** - All file operations require explicit approval or whitelisting
7. **Backend-Agnostic** - Same API for all LLM backends (local/remote)
8. **Audit Trail** - Log all file access and modifications

---

## 2. Components

### 2.1 File Registry Manager

**Responsibility:** Track all project files, their metadata, and version history.

**Data Storage:** SQLite database (`.blueprint/file_registry.db`)

**Schema:**
```sql
-- Main file registry
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT UNIQUE NOT NULL,
    relative_path TEXT NOT NULL,
    file_type TEXT,                    -- extension (.py, .md, etc.)
    size_bytes INTEGER,
    last_modified TIMESTAMP,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    is_entrypoint BOOLEAN DEFAULT 0,   -- AGENTS.md, README.md, etc.
    is_generated BOOLEAN DEFAULT 0,    -- Generated files
    checksum TEXT,                     -- SHA256 for change detection
    summary TEXT,                      -- Optional AI-generated summary
    indexed BOOLEAN DEFAULT 0          -- Whether indexed for search
);

-- Version history
CREATE TABLE file_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER REFERENCES files(id),
    version_number INTEGER,
    content_snapshot TEXT,            -- Full content or compressed
    diff_from_previous TEXT,          -- Unified diff format
    modified_by TEXT,                 -- "user" | "llm:<backend>" | "tool:<name>"
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    commit_message TEXT
);

-- File relationships (imports, references)
CREATE TABLE file_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id INTEGER REFERENCES files(id),
    target_file_id INTEGER REFERENCES files(id),
    relationship_type TEXT,           -- "imports", "references", "includes"
    last_updated TIMESTAMP
);

-- Session state (open buffers, pending edits)
CREATE TABLE session_buffers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER REFERENCES files(id),
    backend TEXT,                     -- Which LLM backend has this open
    content_snapshot TEXT,            -- Current buffer content
    unsaved_changes BOOLEAN DEFAULT 0,
    opened_at TIMESTAMP,
    last_modified_at TIMESTAMP
);
```

**Key Methods:**
```python
class FileRegistryManager:
    def scan_project(self, root_dir: Path) -> None:
        """Scan project directory and register all files."""

    def get_file_metadata(self, filepath: str) -> FileMetadata:
        """Get metadata for a file without loading content."""

    def update_file(self, filepath: str, content: str, modified_by: str) -> int:
        """Update file content and create new version."""

    def get_file_history(self, filepath: str, limit: int = 10) -> list[FileVersion]:
        """Get version history for a file."""

    def detect_changes(self, filepath: str) -> bool:
        """Check if file has changed on disk since last registry update."""

    def mark_as_entrypoint(self, filepath: str) -> None:
        """Mark file as project entrypoint (AGENTS.md, etc.)."""
```

### 2.2 Context Retriever

**Responsibility:** Extract minimal, task-relevant file content for LLM consumption.

**Features:**
- Line range extraction
- Function/class extraction (using AST for Python, regex for others)
- Diff context extraction
- Related files discovery
- Token-aware truncation

**Key Methods:**
```python
class ContextRetriever:
    def get_file_content(
        self,
        filepath: str,
        *,
        lines: tuple[int, int] | None = None,
        max_tokens: int | None = None,
        include_metadata: bool = True,
    ) -> FileContent:
        """Get file content with optional line range and token limits."""

    def get_function_definition(
        self,
        filepath: str,
        function_name: str,
    ) -> str:
        """Extract specific function/class definition from file."""

    def get_diff_context(
        self,
        filepath: str,
        version1: str,
        version2: str,
        context_lines: int = 3,
    ) -> str:
        """Get unified diff between two versions with context."""

    def get_related_files(
        self,
        filepath: str,
        depth: int = 1,
    ) -> list[str]:
        """Get files related to this file (imports, references)."""

    def truncate_to_tokens(
        self,
        content: str,
        max_tokens: int,
        strategy: str = "middle",  # "start" | "end" | "middle"
    ) -> str:
        """Truncate content to fit token budget."""
```

### 2.3 Conflict Detector

**Responsibility:** Detect and resolve conflicts between concurrent edits.

**Conflict Types:**
1. **Stale Buffer** - File changed on disk since LLM loaded it
2. **Overlapping Edits** - Two backends editing same lines
3. **Patch Context Mismatch** - Patch doesn't apply to current file state

**Key Methods:**
```python
class ConflictDetector:
    def check_for_conflicts(
        self,
        filepath: str,
        backend: str,
        intended_edit: Edit,
    ) -> ConflictReport:
        """Check if edit conflicts with current state."""

    def resolve_conflict(
        self,
        filepath: str,
        conflict: ConflictReport,
        strategy: str = "llm_review",  # "llm_review" | "user_approval" | "auto_merge"
    ) -> ResolvedEdit:
        """Resolve conflict using specified strategy."""

    def generate_three_way_merge(
        self,
        filepath: str,
        base_version: str,
        edit1: str,
        edit2: str,
    ) -> MergeResult:
        """Generate three-way merge with conflict markers."""
```

### 2.4 Cache Manager

**Responsibility:** Cache file summaries, embeddings, and metadata to reduce repeated reads.

**Caching Strategy:**
- **L1 (Memory)**: Recently accessed full file contents (LRU, max 50 files)
- **L2 (Disk)**: File summaries and metadata (`.blueprint/cache/`)
- **L3 (Embeddings)**: Vector embeddings for semantic search (optional)

**Key Methods:**
```python
class CacheManager:
    def get_cached_content(self, filepath: str) -> str | None:
        """Get cached file content if available and fresh."""

    def cache_content(self, filepath: str, content: str) -> None:
        """Cache file content in memory."""

    def get_summary(self, filepath: str) -> str | None:
        """Get cached summary of file."""

    def generate_summary(
        self,
        filepath: str,
        content: str,
        backend: str = "gemini",  # Use fast model for summarization
    ) -> str:
        """Generate and cache file summary using LLM."""

    def invalidate(self, filepath: str) -> None:
        """Invalidate cache for a file (on modification)."""
```

### 2.5 Audit Logger

**Responsibility:** Log all file access operations for debugging and compliance.

**Log Storage:** `.blueprint/audit.log` (rotating log file)

**Log Format:**
```json
{
  "timestamp": "2025-12-08T10:30:45Z",
  "operation": "read_lines",
  "filepath": "src/main.py",
  "backend": "ollama",
  "user": "developer",
  "parameters": {
    "start_line": 50,
    "end_line": 80
  },
  "result": "success",
  "tokens_returned": 342,
  "approved_by": "auto",
  "request_id": "req_abc123"
}
```

**Key Methods:**
```python
class AuditLogger:
    def log_access(
        self,
        operation: str,
        filepath: str,
        backend: str,
        parameters: dict,
        result: str,
        tokens_returned: int | None = None,
    ) -> None:
        """Log file access operation."""

    def log_modification(
        self,
        filepath: str,
        backend: str,
        diff: str,
        approved_by: str,
    ) -> None:
        """Log file modification."""

    def get_access_history(
        self,
        filepath: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[AuditEntry]:
        """Query audit log."""
```

---

## 3. Python API Interface

### 3.1 Main File Access Interface

```python
from typing import Literal, NamedTuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

# ============ Data Types ============

@dataclass
class FileMetadata:
    filepath: str
    relative_path: str
    file_type: str
    size_bytes: int
    last_modified: datetime
    last_accessed: datetime
    access_count: int
    is_entrypoint: bool
    checksum: str
    summary: str | None = None

@dataclass
class FileContent:
    filepath: str
    content: str
    metadata: FileMetadata
    lines_returned: tuple[int, int] | None = None  # (start, end) if partial
    tokens_estimated: int = 0
    cached: bool = False

@dataclass
class FileVersion:
    version_number: int
    timestamp: datetime
    modified_by: str
    commit_message: str | None
    diff_from_previous: str | None

@dataclass
class PatchResult:
    success: bool
    filepath: str
    lines_changed: int
    conflict_detected: bool
    conflict_report: "ConflictReport | None" = None
    new_version: int | None = None

@dataclass
class ConflictReport:
    filepath: str
    conflict_type: Literal["stale_buffer", "overlapping_edits", "patch_mismatch"]
    description: str
    base_version: int
    current_version: int
    conflicting_lines: list[tuple[int, int]]  # List of (start, end) line ranges

@dataclass
class Edit:
    filepath: str
    edit_type: Literal["full_replace", "patch", "line_replace"]
    content: str  # Full content or patch
    line_range: tuple[int, int] | None = None  # For line_replace
    base_version: int | None = None  # Version this edit is based on

# ============ Main Interface ============

class FileAccessInterface:
    """
    Unified file access interface for LLM backends.

    All file operations go through this interface via tool calls.
    """

    def __init__(
        self,
        project_root: Path,
        config: ConfigLoader,
        permission_manager: PermissionManager,
        orchestrator: LLMOrchestrator,
    ):
        self.project_root = project_root
        self.config = config
        self.permission_manager = permission_manager
        self.orchestrator = orchestrator

        # Components
        self.registry = FileRegistryManager(project_root)
        self.retriever = ContextRetriever(self.registry)
        self.conflict_detector = ConflictDetector(self.registry)
        self.cache = CacheManager(project_root / ".blueprint" / "cache")
        self.audit = AuditLogger(project_root / ".blueprint" / "audit.log")

    # ============ File Discovery ============

    def list_files(
        self,
        pattern: str = "**/*",
        exclude_patterns: list[str] | None = None,
        include_metadata: bool = False,
    ) -> list[str] | list[FileMetadata]:
        """
        List files in project matching pattern.

        Args:
            pattern: Glob pattern (e.g., "src/**/*.py")
            exclude_patterns: Patterns to exclude (e.g., ["*.pyc", "__pycache__"])
            include_metadata: Return full metadata instead of just paths

        Returns:
            List of file paths or FileMetadata objects

        Example:
            >>> files = interface.list_files("src/**/*.py")
            >>> print(files)
            ['src/main.py', 'src/utils.py', ...]
        """
        exclude_patterns = exclude_patterns or [
            "__pycache__", "*.pyc", ".git", "node_modules",
            ".venv", "venv", "*.egg-info", ".blueprint"
        ]

        # Audit log
        self.audit.log_access(
            operation="list_files",
            filepath=pattern,
            backend="system",
            parameters={"pattern": pattern},
            result="success",
        )

        return self.registry.list_files(pattern, exclude_patterns, include_metadata)

    # ============ File Reading ============

    def read_file(
        self,
        filepath: str,
        *,
        max_tokens: int | None = None,
        include_metadata: bool = True,
        use_cache: bool = True,
    ) -> FileContent:
        """
        Read full file content.

        Args:
            filepath: Path to file (relative to project root)
            max_tokens: Optional token limit for truncation
            include_metadata: Include file metadata in result
            use_cache: Use cached content if available

        Returns:
            FileContent with full file contents

        Example:
            >>> content = interface.read_file("src/main.py")
            >>> print(content.content)
        """
        # Permission check
        self.permission_manager.check_permission("read_file", filepath)

        # Try cache first
        if use_cache:
            cached = self.cache.get_cached_content(filepath)
            if cached:
                self.audit.log_access(
                    operation="read_file",
                    filepath=filepath,
                    backend="system",
                    parameters={},
                    result="success_cached",
                )
                # Return cached result...

        # Read from disk
        full_path = self.project_root / filepath
        content = full_path.read_text()

        # Update registry
        self.registry.update_access(filepath)

        # Truncate if needed
        if max_tokens:
            content = self.retriever.truncate_to_tokens(content, max_tokens)

        # Cache
        if use_cache:
            self.cache.cache_content(filepath, content)

        # Get metadata
        metadata = self.registry.get_file_metadata(filepath) if include_metadata else None

        # Audit log
        self.audit.log_access(
            operation="read_file",
            filepath=filepath,
            backend="system",
            parameters={"max_tokens": max_tokens},
            result="success",
            tokens_returned=len(content) // 4,
        )

        return FileContent(
            filepath=filepath,
            content=content,
            metadata=metadata,
            tokens_estimated=len(content) // 4,
        )

    def read_lines(
        self,
        filepath: str,
        start: int,
        end: int,
        *,
        include_context: bool = False,
        context_lines: int = 3,
    ) -> FileContent:
        """
        Read specific line range from file.

        Args:
            filepath: Path to file
            start: Starting line number (1-indexed)
            end: Ending line number (inclusive)
            include_context: Include surrounding context lines
            context_lines: Number of context lines before/after

        Returns:
            FileContent with requested line range

        Example:
            >>> content = interface.read_lines("src/main.py", 50, 80)
            >>> print(content.content)  # Lines 50-80
        """
        # Permission check
        self.permission_manager.check_permission("read_lines", filepath)

        # Get line range
        content = self.retriever.get_file_content(
            filepath,
            lines=(start, end),
            include_metadata=True,
        )

        # Audit log
        self.audit.log_access(
            operation="read_lines",
            filepath=filepath,
            backend="system",
            parameters={"start": start, "end": end},
            result="success",
            tokens_returned=content.tokens_estimated,
        )

        return content

    def get_function(
        self,
        filepath: str,
        function_name: str,
    ) -> str:
        """
        Extract specific function or class from file.

        Args:
            filepath: Path to file
            function_name: Name of function or class

        Returns:
            Function/class definition as string

        Example:
            >>> code = interface.get_function("src/utils.py", "parse_config")
            >>> print(code)  # Just the parse_config function
        """
        # Permission check
        self.permission_manager.check_permission("read_file", filepath)

        # Extract function
        code = self.retriever.get_function_definition(filepath, function_name)

        # Audit log
        self.audit.log_access(
            operation="get_function",
            filepath=filepath,
            backend="system",
            parameters={"function_name": function_name},
            result="success" if code else "not_found",
        )

        return code

    # ============ File Writing ============

    def write_file(
        self,
        filepath: str,
        content: str,
        *,
        backend: str,
        commit_message: str | None = None,
        create_backup: bool = True,
    ) -> PatchResult:
        """
        Write full content to file (replaces existing content).

        Args:
            filepath: Path to file
            content: New file content
            backend: Which LLM backend is making this change
            commit_message: Optional commit message
            create_backup: Create backup before overwriting

        Returns:
            PatchResult with operation status

        Example:
            >>> result = interface.write_file(
            ...     "src/new_file.py",
            ...     "def hello(): pass",
            ...     backend="openai"
            ... )
        """
        # Permission check
        approval = self.permission_manager.request_approval(
            operation="write_file",
            filepath=filepath,
            details={"content_size": len(content), "backend": backend}
        )

        if not approval.approved:
            return PatchResult(
                success=False,
                filepath=filepath,
                lines_changed=0,
                conflict_detected=False,
            )

        # Check for conflicts
        edit = Edit(
            filepath=filepath,
            edit_type="full_replace",
            content=content,
        )

        conflict_report = self.conflict_detector.check_for_conflicts(
            filepath, backend, edit
        )

        if conflict_report:
            # Route to review backend for conflict resolution
            resolved = self.conflict_detector.resolve_conflict(
                filepath, conflict_report, strategy="llm_review"
            )
            if not resolved.success:
                return PatchResult(
                    success=False,
                    filepath=filepath,
                    lines_changed=0,
                    conflict_detected=True,
                    conflict_report=conflict_report,
                )
            content = resolved.merged_content

        # Create backup if file exists
        full_path = self.project_root / filepath
        if create_backup and full_path.exists():
            backup_path = full_path.with_suffix(full_path.suffix + ".bak")
            backup_path.write_text(full_path.read_text())

        # Write file
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

        # Update registry
        new_version = self.registry.update_file(
            filepath, content, f"llm:{backend}", commit_message
        )

        # Invalidate cache
        self.cache.invalidate(filepath)

        # Audit log
        self.audit.log_modification(
            filepath=filepath,
            backend=backend,
            diff=f"Full file write ({len(content)} chars)",
            approved_by=approval.approved_by,
        )

        return PatchResult(
            success=True,
            filepath=filepath,
            lines_changed=len(content.splitlines()),
            conflict_detected=False,
            new_version=new_version,
        )

    def apply_patch(
        self,
        filepath: str,
        patch: str,
        *,
        backend: str,
        patch_format: Literal["unified", "context"] = "unified",
        commit_message: str | None = None,
    ) -> PatchResult:
        """
        Apply a patch (diff) to a file.

        Args:
            filepath: Path to file
            patch: Patch content in unified diff format
            backend: Which LLM backend is making this change
            patch_format: Format of patch ("unified" or "context")
            commit_message: Optional commit message

        Returns:
            PatchResult with operation status

        Example:
            >>> patch = '''
            ... --- a/src/main.py
            ... +++ b/src/main.py
            ... @@ -10,3 +10,4 @@
            ...  def main():
            ... +    print("Hello")
            ...      pass
            ... '''
            >>> result = interface.apply_patch("src/main.py", patch, backend="claude")
        """
        # Permission check
        approval = self.permission_manager.request_approval(
            operation="apply_patch",
            filepath=filepath,
            details={"patch_size": len(patch), "backend": backend}
        )

        if not approval.approved:
            return PatchResult(
                success=False,
                filepath=filepath,
                lines_changed=0,
                conflict_detected=False,
            )

        # Parse patch and apply
        try:
            import patch as patch_lib  # unidiff or similar library

            # Check for conflicts first
            edit = Edit(
                filepath=filepath,
                edit_type="patch",
                content=patch,
            )

            conflict_report = self.conflict_detector.check_for_conflicts(
                filepath, backend, edit
            )

            if conflict_report:
                # Attempt resolution
                resolved = self.conflict_detector.resolve_conflict(
                    filepath, conflict_report, strategy="llm_review"
                )
                if not resolved.success:
                    return PatchResult(
                        success=False,
                        filepath=filepath,
                        lines_changed=0,
                        conflict_detected=True,
                        conflict_report=conflict_report,
                    )

            # Apply patch
            full_path = self.project_root / filepath
            original_content = full_path.read_text()

            # Use patch library to apply
            patched_content = patch_lib.apply_patch(original_content, patch)

            # Write result
            full_path.write_text(patched_content)

            # Update registry
            new_version = self.registry.update_file(
                filepath, patched_content, f"llm:{backend}", commit_message
            )

            # Invalidate cache
            self.cache.invalidate(filepath)

            # Count changed lines
            lines_changed = len([line for line in patch.splitlines() if line.startswith("+") or line.startswith("-")])

            # Audit log
            self.audit.log_modification(
                filepath=filepath,
                backend=backend,
                diff=patch,
                approved_by=approval.approved_by,
            )

            return PatchResult(
                success=True,
                filepath=filepath,
                lines_changed=lines_changed,
                conflict_detected=False,
                new_version=new_version,
            )

        except Exception as e:
            return PatchResult(
                success=False,
                filepath=filepath,
                lines_changed=0,
                conflict_detected=False,
            )

    # ============ File History & Metadata ============

    def get_file_history(
        self,
        filepath: str,
        limit: int = 10,
    ) -> list[FileVersion]:
        """
        Get version history for a file.

        Args:
            filepath: Path to file
            limit: Maximum number of versions to return

        Returns:
            List of FileVersion objects, most recent first

        Example:
            >>> history = interface.get_file_history("src/main.py")
            >>> for version in history:
            ...     print(f"v{version.version_number}: {version.commit_message}")
        """
        return self.registry.get_file_history(filepath, limit)

    def get_file_diff(
        self,
        filepath: str,
        version1: int | str,
        version2: int | str,
        context_lines: int = 3,
    ) -> str:
        """
        Get diff between two versions of a file.

        Args:
            filepath: Path to file
            version1: Version number or "current"
            version2: Version number or "current"
            context_lines: Number of context lines in diff

        Returns:
            Unified diff as string

        Example:
            >>> diff = interface.get_file_diff("src/main.py", 1, 2)
            >>> print(diff)
        """
        return self.retriever.get_diff_context(
            filepath, str(version1), str(version2), context_lines
        )

    def get_file_metadata(
        self,
        filepath: str,
    ) -> FileMetadata:
        """
        Get metadata for a file without loading content.

        Args:
            filepath: Path to file

        Returns:
            FileMetadata object

        Example:
            >>> meta = interface.get_file_metadata("src/main.py")
            >>> print(f"Last modified: {meta.last_modified}")
        """
        return self.registry.get_file_metadata(filepath)

    def get_file_summary(
        self,
        filepath: str,
        regenerate: bool = False,
    ) -> str:
        """
        Get AI-generated summary of file.

        Args:
            filepath: Path to file
            regenerate: Force regeneration even if cached

        Returns:
            Summary text

        Example:
            >>> summary = interface.get_file_summary("src/main.py")
            >>> print(summary)
            "Main application entry point. Defines CLI interface..."
        """
        # Check cache
        if not regenerate:
            cached = self.cache.get_summary(filepath)
            if cached:
                return cached

        # Read file
        content = self.read_file(filepath, use_cache=True)

        # Generate summary
        summary = self.cache.generate_summary(
            filepath, content.content, backend="gemini"
        )

        return summary
```

---

## 4. Initialization & Metadata Loading

### 4.1 Startup Sequence

When the CLI/agent session starts, the file access subsystem:

1. **Scan Project Directory**
   - Discover all files
   - Register in file registry
   - Identify entrypoint files (`AGENTS.md`, `README.md`, config files)

2. **Load Entrypoint Metadata**
   - Read designated entrypoint docs
   - Generate summaries (if not cached)
   - Prepare truncated project overview

3. **Build Initial Context**
   - List all file paths (not contents)
   - Include truncated summaries of entrypoint files
   - Provide to LLM as initial project awareness

### 4.2 Entrypoint Configuration

Configure entrypoint files in `.blueprint/config.toml`:

```toml
[file_access]
# Files to load at startup
entrypoint_files = [
    "AGENTS.md",
    "README.md",
    "docs/ARCHITECTURE.md",
    "package.json",
    "pyproject.toml",
]

# Maximum tokens for entrypoint content
entrypoint_max_tokens = 500  # Truncate to summary

# Auto-generate summaries for large files
auto_summarize = true
summary_backend = "gemini"
```

### 4.3 Initial LLM Context

At startup, the LLM receives:

```
**Project Overview**

Project Root: /Users/dev/myproject

**Files Available (87 total):**
- src/
  - main.py (Entry point)
  - utils.py (Utilities)
  - models/ (5 files)
  - services/ (12 files)
- tests/ (23 files)
- docs/ (8 files)

**Key Documents:**

📄 AGENTS.md (truncated - use read_file() for full content)
"""
This project uses multiple LLM agents for code generation...
[Summary continues for ~500 tokens]
"""

📄 README.md (truncated)
"""
## MyProject
A multi-agent coding platform...
[Summary continues]
"""

**Available Tools:**
- list_files(pattern): List project files
- read_file(filepath): Read full file content
- read_lines(filepath, start, end): Read specific line range
- write_file(filepath, content): Write file (requires approval)
- apply_patch(filepath, patch): Apply diff (requires approval)
- get_file_history(filepath): Get version history
- get_file_diff(filepath, v1, v2): Get diff between versions
- get_function(filepath, name): Extract specific function/class

**Instructions:**
To access file content, use the appropriate tool. Do not assume entire repository
context is available. Request specific files or line ranges as needed for your task.
```

---

## 5. File Access Workflows

### 5.1 Workflow: LLM Requests File Content

```
User Request: "Fix the bug in src/main.py around line 50"
        ↓
Orchestrator → parse request → detect file reference
        ↓
LLM (OpenAI) generates tool call:
{
  "tool": "read_lines",
  "arguments": {
    "filepath": "src/main.py",
    "start": 45,
    "end": 60,
    "include_context": true
  }
}
        ↓
FileAccessInterface.read_lines()
  → Permission check (auto-approved for reads)
  → ContextRetriever.get_file_content(lines=(45, 60))
  → AuditLogger.log_access()
  → Return FileContent
        ↓
LLM receives:
"""
[Lines 45-60 from src/main.py]
45: def process_data(data):
46:     result = []
47:     for item in data:
48:         if item > 0:  # BUG: should be >= 0
49:             result.append(item)
50:     return result
...
"""
        ↓
LLM generates patch:
{
  "tool": "apply_patch",
  "arguments": {
    "filepath": "src/main.py",
    "patch": "--- a/src/main.py\n+++ b/src/main.py\n@@ -48 +48 @@\n-        if item > 0:\n+        if item >= 0:"
  }
}
        ↓
FileAccessInterface.apply_patch()
  → Permission check (requires approval)
  → User prompt: "Apply patch to src/main.py? [y/n]"
  → User approves
  → ConflictDetector.check_for_conflicts()
  → Apply patch
  → FileRegistry.update_file() (create new version)
  → AuditLogger.log_modification()
  → Return success
```

### 5.2 Workflow: Local LLM with Large File

```
User: "Refactor the authentication module" (large file: 2000 lines)
        ↓
Orchestrator selects backend: ollama (8k token limit)
        ↓
LLM requests: read_file("src/auth.py")
        ↓
FileAccessInterface detects:
  - File is 2000 lines
  - Backend is ollama (small context)
  - Need to provide minimal snippet
        ↓
Strategy:
  1. Get file summary from cache (generated by Gemini)
  2. Ask user/LLM which part to focus on
  3. Provide specific functions/line ranges only
        ↓
Return to LLM:
"""
File: src/auth.py (2000 lines total)

**Summary:**
Authentication module handling user login, JWT tokens, password hashing,
and session management. Main classes: AuthManager, JWTHandler, SessionStore.

**Available functions:**
- login(username, password)
- logout(session_id)
- verify_token(token)
- hash_password(password)
- create_session(user_id)

Which function would you like to see? Use get_function(filepath, name).
"""
        ↓
LLM: get_function("src/auth.py", "login")
        ↓
Return just the login function (50 lines instead of 2000)
```

### 5.3 Workflow: Conflict Detection & Resolution

```
Scenario: Two backends editing same file concurrently

Backend A (OpenAI): Opens src/utils.py v5, makes edits
Backend B (Claude): Opens src/utils.py v5, makes different edits
        ↓
Backend A writes first → success, creates v6
        ↓
Backend B tries to write:
  FileAccessInterface.write_file()
    → ConflictDetector.check_for_conflicts()
    → Detect: Backend B's edit based on v5, but current is v6
    → Conflict type: "stale_buffer"
        ↓
Conflict resolution:
  1. Get diff between v5 and v6 (Backend A's changes)
  2. Get Backend B's intended changes
  3. Route to review backend (Claude Opus):
     "Two sets of changes to src/utils.py. Merge them:
      Changes from Backend A: [diff]
      Changes from Backend B: [diff]
      Produce merged version."
  4. Apply merged result
  5. Create v7 with both changes
```

---

## 6. Conflict Detection & Resolution

### 6.1 Conflict Types

| Type | Description | Resolution Strategy |
|------|-------------|---------------------|
| **Stale Buffer** | File modified since LLM loaded it | 3-way merge or LLM review |
| **Overlapping Edits** | Two backends editing same lines | LLM review required |
| **Patch Mismatch** | Patch context doesn't match current file | Reject or LLM adaptation |

### 6.2 ConflictDetector Implementation

```python
class ConflictDetector:
    def check_for_conflicts(
        self,
        filepath: str,
        backend: str,
        intended_edit: Edit,
    ) -> ConflictReport | None:
        """Check if edit conflicts with current file state."""

        # Get current file version
        current_version = self.registry.get_current_version(filepath)

        # Check if edit specifies base version
        if intended_edit.base_version is not None:
            if intended_edit.base_version != current_version:
                # File changed since edit was prepared
                return ConflictReport(
                    filepath=filepath,
                    conflict_type="stale_buffer",
                    description=f"Edit based on v{intended_edit.base_version}, but current is v{current_version}",
                    base_version=intended_edit.base_version,
                    current_version=current_version,
                    conflicting_lines=[],
                )

        # Check for overlapping edits with session buffers
        open_buffers = self.registry.get_session_buffers(filepath)
        for buffer in open_buffers:
            if buffer.backend != backend and buffer.unsaved_changes:
                # Another backend has unsaved changes
                return ConflictReport(
                    filepath=filepath,
                    conflict_type="overlapping_edits",
                    description=f"Backend {buffer.backend} has unsaved changes",
                    base_version=current_version,
                    current_version=current_version,
                    conflicting_lines=[],  # Compute from diff
                )

        # For patches, validate context matches
        if intended_edit.edit_type == "patch":
            if not self._patch_applies_cleanly(filepath, intended_edit.content):
                return ConflictReport(
                    filepath=filepath,
                    conflict_type="patch_mismatch",
                    description="Patch context does not match current file",
                    base_version=current_version,
                    current_version=current_version,
                    conflicting_lines=[],
                )

        return None  # No conflicts

    def resolve_conflict(
        self,
        filepath: str,
        conflict: ConflictReport,
        strategy: str = "llm_review",
    ) -> ResolvedEdit:
        """Resolve conflict using specified strategy."""

        if strategy == "llm_review":
            # Use heavy model (Opus/Claude) to merge changes
            return self._llm_merge(filepath, conflict)
        elif strategy == "user_approval":
            # Ask user to choose
            return self._user_choose(filepath, conflict)
        elif strategy == "auto_merge":
            # Attempt automatic 3-way merge
            return self._three_way_merge(filepath, conflict)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _llm_merge(
        self,
        filepath: str,
        conflict: ConflictReport,
    ) -> ResolvedEdit:
        """Use LLM to intelligently merge conflicting changes."""

        # Get versions
        base_content = self.registry.get_version_content(
            filepath, conflict.base_version
        )
        current_content = self.registry.get_version_content(
            filepath, conflict.current_version
        )

        # Get diffs
        base_to_current_diff = self._diff(base_content, current_content)

        # Prompt heavy model
        prompt = f"""Two sets of changes were made to {filepath}. Please merge them intelligently.

**Base version (v{conflict.base_version}):**
```
{base_content[:1000]}  # Truncate for context
```

**Changes made by another process:**
```diff
{base_to_current_diff}
```

**Current version (v{conflict.current_version}):**
```
{current_content[:1000]}
```

**Conflict:** {conflict.description}

Please provide the merged version that incorporates both sets of changes without losing any functionality.
Output only the merged file content.
"""

        # Call review backend (Opus)
        response = self.orchestrator.chat(
            message=prompt,
            backend="opus",  # Use heavy model
            persona="reviewer",
            include_context=False,
        )

        merged_content = response.content.strip()

        return ResolvedEdit(
            success=True,
            merged_content=merged_content,
            strategy_used="llm_review",
        )
```

---

## 7. Permission & Security Model

### 7.1 Permission Modes

**Three modes (configured per-project):**

1. **Manual Approval** - User approves every file operation
2. **Auto (Whitelist)** - Certain operations/paths auto-approved
3. **Deny** - Block all file modifications

### 7.2 Permission Configuration

`.blueprint/config.toml`:
```toml
[file_access.permissions]
mode = "auto"  # "manual" | "auto" | "deny"

# Auto-approved operations (when mode = "auto")
auto_approve_read = true   # All reads allowed
auto_approve_write_patterns = [
    "src/**/*.py",         # Allow writes to Python files in src/
    "tests/**/*",          # Allow writes to tests/
]
auto_deny_patterns = [
    ".env",                # Never allow modification
    "secrets/**/*",
    "credentials.json",
]

# Require explicit approval for these operations
require_approval = [
    "delete_file",
    "rename_file",
]
```

### 7.3 Permission Manager

```python
class PermissionManager:
    def __init__(self, config: ConfigLoader):
        self.config = config
        self.mode = config.get("file_access.permissions.mode", "manual")

    def check_permission(
        self,
        operation: str,
        filepath: str,
    ) -> None:
        """
        Check if operation is allowed (raises PermissionError if not).

        For read operations: usually allowed (unless in deny mode).
        For write operations: depends on mode and configuration.
        """
        if self.mode == "deny":
            raise PermissionError(f"File access denied: {operation} on {filepath}")

        # Check deny patterns
        deny_patterns = self.config.get("file_access.permissions.auto_deny_patterns", [])
        for pattern in deny_patterns:
            if self._matches_pattern(filepath, pattern):
                raise PermissionError(f"File access denied by policy: {filepath}")

        # Reads usually allowed
        if operation in ["read_file", "read_lines", "list_files", "get_function"]:
            return  # Allowed

        # Writes require more checks
        if self.mode == "manual":
            # Will request approval in request_approval()
            return

        if self.mode == "auto":
            # Check whitelist
            write_patterns = self.config.get(
                "file_access.permissions.auto_approve_write_patterns", []
            )
            for pattern in write_patterns:
                if self._matches_pattern(filepath, pattern):
                    return  # Auto-approved

            # Not whitelisted - will require approval
            return

    def request_approval(
        self,
        operation: str,
        filepath: str,
        details: dict,
    ) -> ApprovalResult:
        """Request user approval for operation."""

        # In auto mode, check if auto-approved
        if self.mode == "auto":
            if operation == "read_file" or operation == "read_lines":
                return ApprovalResult(approved=True, approved_by="auto")

            write_patterns = self.config.get(
                "file_access.permissions.auto_approve_write_patterns", []
            )
            for pattern in write_patterns:
                if self._matches_pattern(filepath, pattern):
                    return ApprovalResult(approved=True, approved_by="auto")

        # Request user approval (CLI prompt or UI)
        print(f"\n📝 File operation request:")
        print(f"   Operation: {operation}")
        print(f"   File: {filepath}")
        print(f"   Details: {details}")
        response = input("   Approve? [y/n]: ")

        approved = response.lower() == "y"

        return ApprovalResult(
            approved=approved,
            approved_by="user" if approved else "denied_by_user",
        )

    def _matches_pattern(self, filepath: str, pattern: str) -> bool:
        """Check if filepath matches glob pattern."""
        from fnmatch import fnmatch
        return fnmatch(filepath, pattern)

@dataclass
class ApprovalResult:
    approved: bool
    approved_by: str  # "user" | "auto" | "denied_by_user" | "policy"
```

---

## 8. Caching & Summarization

### 8.1 Cache Strategy

**Three-tier caching:**

```
L1 (Memory) - Hot cache
  ├─ Recently accessed files (full content)
  ├─ LRU eviction, max 50 files
  └─ Invalidated on modification

L2 (Disk) - Summaries & metadata
  ├─ AI-generated file summaries
  ├─ File metadata (size, type, etc.)
  └─ Persisted in .blueprint/cache/

L3 (Embeddings) - Semantic search [Optional]
  ├─ Vector embeddings of file contents
  ├─ Enable semantic file search
  └─ Stored in .blueprint/embeddings.db
```

### 8.2 Summary Generation

When a large file is accessed by a small-context backend:

```python
class CacheManager:
    def generate_summary(
        self,
        filepath: str,
        content: str,
        backend: str = "gemini",
    ) -> str:
        """Generate AI summary of file using fast model."""

        # Check cache first
        cache_path = self.cache_dir / f"{filepath.replace('/', '_')}.summary"
        if cache_path.exists():
            # Check if still fresh (based on file mtime)
            cache_mtime = cache_path.stat().st_mtime
            file_mtime = (self.project_root / filepath).stat().st_mtime
            if cache_mtime > file_mtime:
                return cache_path.read_text()

        # Generate new summary
        prompt = f"""Summarize this code file concisely. Include:
1. Primary purpose and functionality
2. Main classes/functions (names only)
3. Key dependencies
4. Any notable patterns or complexity

File: {filepath}
```
{content[:10000]}  # Cap at 10k chars for prompt
```

Provide a 3-5 sentence summary."""

        response = self.orchestrator.chat(
            message=prompt,
            backend=backend,
            persona="context-distiller",
            include_context=False,
        )

        summary = response.content.strip()

        # Cache summary
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(summary)

        return summary
```

---

## 9. Audit & Logging

### 9.1 Audit Log Format

Every file operation is logged:

```json
{
  "id": "log_20251208_103045_abc123",
  "timestamp": "2025-12-08T10:30:45.123Z",
  "operation": "apply_patch",
  "filepath": "src/auth.py",
  "backend": "claude",
  "user": "developer",
  "session_id": "sess_xyz789",
  "parameters": {
    "patch_size_bytes": 342,
    "lines_affected": 5
  },
  "result": "success",
  "approval": {
    "required": true,
    "approved_by": "user",
    "approval_time": "2025-12-08T10:30:43Z"
  },
  "metadata": {
    "file_version_before": 12,
    "file_version_after": 13,
    "tokens_returned": null,
    "execution_time_ms": 234
  },
  "diff_summary": "@@ -45,3 +45,4 @@ ... (10 lines changed)"
}
```

### 9.2 Audit Queries

```python
# Get all modifications in last 24 hours
recent_mods = audit.get_access_history(
    operation="apply_patch",
    start_time=datetime.now() - timedelta(days=1)
)

# Get all access to specific file
file_history = audit.get_access_history(filepath="src/sensitive.py")

# Get all operations by specific backend
backend_ops = audit.get_access_history(backend="ollama")
```

---

## 10. Integration with Orchestrator

### 10.1 Tool Registration

Register file access tools with the orchestrator's tool executor:

```python
def register_file_tools(orchestrator: LLMOrchestrator):
    """Register all file access tools with orchestrator."""

    file_interface = FileAccessInterface(
        project_root=Path.cwd(),
        config=orchestrator.config,
        permission_manager=orchestrator.permission_manager,
        orchestrator=orchestrator,
    )

    # Read tools
    orchestrator.register_tool(Tool(
        name="list_files",
        description="List files in project matching a glob pattern",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g., 'src/**/*.py')",
                    "default": "**/*"
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "Include file metadata",
                    "default": False
                }
            }
        },
        handler=file_interface.list_files,
        requires_approval=False,
    ))

    orchestrator.register_tool(Tool(
        name="read_file",
        description="Read full content of a file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to file (relative to project root)"
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Optional max tokens for truncation"
                }
            },
            "required": ["filepath"]
        },
        handler=lambda args: file_interface.read_file(**args).content,
        requires_approval=False,
    ))

    orchestrator.register_tool(Tool(
        name="read_lines",
        description="Read specific line range from a file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string"},
                "start": {"type": "integer", "description": "Start line (1-indexed)"},
                "end": {"type": "integer", "description": "End line (inclusive)"}
            },
            "required": ["filepath", "start", "end"]
        },
        handler=lambda args: file_interface.read_lines(**args).content,
        requires_approval=False,
    ))

    # Write tools
    orchestrator.register_tool(Tool(
        name="write_file",
        description="Write content to a file (creates or overwrites)",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string"},
                "content": {"type": "string"},
                "backend": {"type": "string"},
                "commit_message": {"type": "string"}
            },
            "required": ["filepath", "content", "backend"]
        },
        handler=file_interface.write_file,
        requires_approval=True,
    ))

    orchestrator.register_tool(Tool(
        name="apply_patch",
        description="Apply a unified diff patch to a file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string"},
                "patch": {"type": "string", "description": "Unified diff format"},
                "backend": {"type": "string"}
            },
            "required": ["filepath", "patch", "backend"]
        },
        handler=file_interface.apply_patch,
        requires_approval=True,
    ))

    # Metadata tools
    orchestrator.register_tool(Tool(
        name="get_file_history",
        description="Get version history of a file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["filepath"]
        },
        handler=file_interface.get_file_history,
        requires_approval=False,
    ))

    orchestrator.register_tool(Tool(
        name="get_function",
        description="Extract specific function or class from a file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string"},
                "function_name": {"type": "string"}
            },
            "required": ["filepath", "function_name"]
        },
        handler=file_interface.get_function,
        requires_approval=False,
    ))
```

---

## 11. Implementation Roadmap

### Phase 1: Core Foundation (Week 1-2)
**Goal:** Basic file reading with registry

- [ ] File registry manager with SQLite schema
- [ ] Basic file scanning and metadata collection
- [ ] Simple read_file() and list_files() implementation
- [ ] Tool registration with orchestrator
- [ ] Basic audit logging

**Deliverables:**
- `FileRegistryManager` class
- `list_files()` and `read_file()` tools working
- SQLite database created
- Basic tests

### Phase 2: Context-Aware Access (Week 2-3)
**Goal:** Smart content retrieval for different backends

- [ ] Context retriever with line-range extraction
- [ ] Token-aware truncation
- [ ] Function/class extraction (Python AST)
- [ ] read_lines() and get_function() tools
- [ ] Cache manager (L1 memory cache)

**Deliverables:**
- `ContextRetriever` class
- Works with local LLMs (provides minimal context)
- Tests for line-range extraction

### Phase 3: File Modifications (Week 3-4)
**Goal:** Safe file writing with versioning

- [ ] write_file() implementation
- [ ] Version history tracking
- [ ] Backup creation before overwrite
- [ ] apply_patch() with patch library
- [ ] Permission manager integration

**Deliverables:**
- File modification tools working
- Version history in database
- Permission approval flow

### Phase 4: Conflict Detection (Week 4-5)
**Goal:** Detect and resolve edit conflicts

- [ ] Conflict detector implementation
- [ ] Session buffer tracking
- [ ] LLM-based conflict resolution
- [ ] Three-way merge capability
- [ ] Conflict resolution routing to review backend

**Deliverables:**
- `ConflictDetector` class
- Automatic conflict detection
- LLM merge resolution working

### Phase 5: Summarization & Caching (Week 5-6)
**Goal:** Optimize for large files

- [ ] File summary generation (using Gemini)
- [ ] L2 disk cache for summaries
- [ ] Automatic summarization for large files
- [ ] Smart context provision for small backends
- [ ] get_file_summary() tool

**Deliverables:**
- `CacheManager` with summary generation
- Large files handled gracefully for local LLMs

### Phase 6: Startup & Entrypoints (Week 6)
**Goal:** Intelligent initialization

- [ ] Entrypoint configuration
- [ ] Automatic AGENTS.md loading at startup
- [ ] Truncated project overview generation
- [ ] Initial context building for LLMs

**Deliverables:**
- Startup sequence implemented
- LLMs receive project overview at init

### Phase 7: Polish & Integration (Week 7-8)
**Goal:** Production-ready

- [ ] Comprehensive audit logging
- [ ] get_file_history() and get_file_diff() tools
- [ ] File relationship tracking
- [ ] Performance optimization
- [ ] Full integration with orchestrator
- [ ] Documentation and examples
- [ ] Security audit

**Deliverables:**
- All tools working end-to-end
- Tests passing
- Documentation complete
- Security review done

---

## 12. Security & Prompt Injection Defense

### 12.1 Path Validation

**Prevent directory traversal attacks:**

```python
def validate_filepath(filepath: str, project_root: Path) -> Path:
    """Validate and resolve filepath safely."""

    # Resolve to absolute path
    full_path = (project_root / filepath).resolve()

    # Ensure it's within project root
    if not full_path.is_relative_to(project_root):
        raise SecurityError(f"Path traversal attempt: {filepath}")

    # Block access to sensitive directories
    blocked_patterns = [".git", ".env", "node_modules/.env"]
    for pattern in blocked_patterns:
        if pattern in str(full_path):
            raise SecurityError(f"Access to blocked path: {filepath}")

    return full_path
```

### 12.2 Content Sanitization

**Strip sensitive information from file content before sending to LLM:**

```python
def sanitize_content(content: str) -> str:
    """Remove sensitive information from content."""

    # Patterns to redact
    patterns = [
        (r'api_key\s*=\s*["\']([^"\']+)["\']', 'api_key = "[REDACTED]"'),
        (r'password\s*=\s*["\']([^"\']+)["\']', 'password = "[REDACTED]"'),
        (r'secret\s*=\s*["\']([^"\']+)["\']', 'secret = "[REDACTED]"'),
        (r'token\s*=\s*["\']([^"\']+)["\']', 'token = "[REDACTED]"'),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

    return content
```

### 12.3 Prompt Injection Defense

**Use delimiters to separate code from instructions:**

```python
def format_file_content_for_llm(content: str, filepath: str) -> str:
    """Format file content with clear delimiters."""

    return f"""
**File: {filepath}**

```
{content}
```

**End of file content. Instructions continue below.**
""".strip()
```

**Validate tool call arguments:**

```python
def validate_tool_arguments(tool_name: str, arguments: dict) -> None:
    """Validate tool arguments to prevent injection."""

    # Ensure filepath doesn't contain shell metacharacters
    if tool_name in ["read_file", "write_file", "apply_patch"]:
        filepath = arguments.get("filepath", "")

        # Block shell metacharacters
        if any(char in filepath for char in [";", "|", "&", "$", "`"]):
            raise SecurityError(f"Invalid characters in filepath: {filepath}")

        # Block absolute paths (must be relative to project)
        if filepath.startswith("/"):
            raise SecurityError(f"Absolute paths not allowed: {filepath}")
```

### 12.4 Permissions Best Practices

1. **Default to deny** - Whitelist specific paths, not blacklist
2. **Require approval for writes** - Never auto-approve destructive operations
3. **Audit everything** - Log all file access with timestamps
4. **Sandbox execution** - Run tools in restricted environment
5. **Rate limiting** - Prevent excessive file operations
6. **User confirmation** - Show diffs before applying patches

---

## 13. Trade-offs & Justification

### 13.1 Advantages

| Advantage | Benefit |
|-----------|---------|
| **Minimal Context** | Local LLMs can work on large projects without running out of memory |
| **Granular Access** | Only load what's needed, reducing token costs |
| **Version Tracking** | Full edit history for debugging and rollback |
| **Conflict Detection** | Prevents data loss from concurrent edits |
| **Permission-Based** | Safety net against accidental destructive operations |
| **Audit Trail** | Compliance and debugging support |
| **Backend-Agnostic** | Same API for all LLMs (local/remote) |
| **Caching** | Reduced redundant file reads and API calls |

### 13.2 Trade-offs

| Trade-off | Impact | Mitigation |
|-----------|--------|------------|
| **Added Complexity** | More moving parts, more bugs | Phased implementation, comprehensive tests |
| **Storage Overhead** | SQLite DB, version history, cache files | Configurable retention, cleanup utilities |
| **Latency** | File ops add overhead | Aggressive caching, async I/O |
| **Stale Context** | LLM may work on outdated file state | Conflict detection, version tracking |
| **Permission Friction** | User approval slows workflow | Smart defaults, whitelisting |
| **Cache Invalidation** | Complex cache consistency | Simple mtime-based invalidation |

### 13.3 Why This Design?

**Problem:** Multi-LLM orchestration requires different backends to access project files, but:
- Local models have tiny context windows (can't hold whole repo)
- Sending full files wastes tokens and money
- Concurrent edits cause conflicts
- LLMs need safety guardrails for file modifications

**Solution:** This design provides:
1. **Smart context provision** - Give LLMs only what they need
2. **Safety** - Permission system prevents disasters
3. **Efficiency** - Caching and summarization reduce costs
4. **History** - Version tracking enables debugging and rollback
5. **Conflict resolution** - Use heavy models to merge changes intelligently

**Alternative Approaches Rejected:**
- **Send full repo to every LLM** - Wastes tokens, exceeds context limits
- **No version tracking** - Can't debug or rollback mistakes
- **Direct file system access** - Unsafe, no audit trail
- **Manual conflict resolution only** - Too slow, blocks workflow

---

## Conclusion

This file-access subsystem provides a production-ready foundation for multi-LLM platforms to safely and efficiently interact with project files. By combining intelligent context management, version tracking, conflict detection, and permission-based security, it enables local and remote LLMs to collaborate effectively on codebases of any size.

**Key Innovations:**
- Context distillation for local LLMs
- Automatic conflict resolution using heavy models
- Granular file access (lines, functions, diffs)
- Comprehensive audit trail

The phased implementation roadmap ensures incremental delivery of value, starting with basic file reading and building up to advanced conflict resolution and caching.
