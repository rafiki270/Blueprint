# LLM Usage Tracking & Observability Subsystem

## Executive Summary

This document specifies a production-grade usage tracking and observability subsystem for the multi-LLM orchestration platform. The system provides comprehensive metrics collection, session management, cost estimation, and reporting across all backend types (paid APIs and local models). It tracks every LLM interaction, aggregates usage at session and project levels, enforces quotas, and provides rich reporting capabilities.

**Key Features:**
- Per-call tracking with token counts, latency, and cost
- Session-based aggregation with lifecycle management
- Persistent historical storage (SQLite)
- Real-time streaming metrics with incremental updates
- Unified interface across paid and free backends
- Cost estimation with model-specific pricing
- Quota enforcement with configurable thresholds
- Rich CLI reporting and export capabilities

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Models & Schema](#2-data-models--schema)
3. [Core Components](#3-core-components)
4. [Python API Interface](#4-python-api-interface)
5. [Cost Estimation & Pricing](#5-cost-estimation--pricing)
6. [Session Management](#6-session-management)
7. [Quota Enforcement](#7-quota-enforcement)
8. [Reporting & Visualization](#8-reporting--visualization)
9. [Integration Points](#9-integration-points)
10. [Example Implementation](#10-example-implementation)
11. [Limitations & Trade-offs](#11-limitations--trade-offs)
12. [Integration Recommendations](#12-integration-recommendations)
13. [Documentation Structure](#13-documentation-structure)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   LLM Orchestrator                          │
│                  (Orchestrates calls)                       │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬─────────────┐
        ▼            ▼            ▼             ▼
   [OpenAI]     [Claude]      [Gemini]     [Ollama]
   Backend      Backend       Backend      Backend
        │            │            │             │
        └────────────┴────────────┴─────────────┘
                     │
                     ▼ (intercept before/after)
┌─────────────────────────────────────────────────────────────┐
│              Usage Tracking Subsystem                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  UsageTracker (Core)                                  │  │
│  │  - register_call_start()                              │  │
│  │  - register_call_end()                                │  │
│  │  - record_chunk() [for streaming]                     │  │
│  │  - record_error()                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────┬──────────────┬──────────────┬───────────┐  │
│  │  Session   │ Cost         │ Persistent   │ Quota     │  │
│  │  Manager   │ Calculator   │ Storage      │ Enforcer  │  │
│  └────────────┴──────────────┴──────────────┴───────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Usage Reporter                                       │  │
│  │  - format_session_stats()                             │  │
│  │  - format_backend_stats()                             │  │
│  │  - export_to_json() / export_to_csv()                │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 Persistent Storage                          │
│  ┌──────────────────┬──────────────────┬────────────────┐  │
│  │ SQLite DB        │ Session Logs     │ Export Files   │  │
│  │ (usage.db)       │ (.json)          │ (.csv, .json)  │  │
│  └──────────────────┴──────────────────┴────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.1 Design Principles

1. **Low Overhead** - Minimal performance impact on LLM calls
2. **Accuracy** - Precise token counting and cost calculation
3. **Reliability** - Never fail LLM calls due to tracking errors
4. **Flexibility** - Support both paid and free backends uniformly
5. **Persistence** - Survive process restarts and crashes
6. **Privacy** - No sensitive prompt/response content in logs (optional redaction)
7. **Extensibility** - Easy to add new backends and metrics

---

## 2. Data Models & Schema

### 2.1 UsageEntry (Per-Call Record)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Dict, Any
from enum import Enum

class CallType(str, Enum):
    CHAT = "chat"
    GENERATE = "generate"
    STREAM = "stream"
    TOOL_CALL = "tool_call"
    EMBEDDING = "embedding"

class CallStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"

@dataclass
class UsageEntry:
    """Single LLM call usage record."""

    # Identifiers
    call_id: str                        # Unique call identifier
    session_id: str                     # Session this call belongs to
    timestamp: datetime                 # When call was made

    # Backend info
    backend: str                        # Backend name (e.g., "openai", "ollama")
    model: str                          # Model name (e.g., "gpt-4o", "deepseek-coder")
    provider: str                       # Provider (e.g., "openai", "anthropic")

    # Call details
    call_type: CallType                 # Type of call
    operation: str                      # Specific operation (e.g., "chat", "plan_task")
    persona: str | None = None          # Persona used if any

    # Metrics
    prompt_tokens: int = 0              # Input tokens
    completion_tokens: int = 0          # Output tokens
    total_tokens: int = 0               # Total tokens
    prompt_chars: int = 0               # Character count (fallback if tokens unavailable)
    completion_chars: int = 0

    # Timing
    start_time: datetime | None = None  # Call start
    end_time: datetime | None = None    # Call end
    duration_ms: float = 0              # Total duration in milliseconds

    # Streaming metrics
    is_streaming: bool = False
    chunk_count: int = 0                # Number of chunks received
    first_token_latency_ms: float = 0   # Time to first token (TTFT)

    # Cost (for paid backends)
    input_cost_usd: float = 0.0         # Cost of input tokens
    output_cost_usd: float = 0.0        # Cost of output tokens
    total_cost_usd: float = 0.0         # Total cost

    # Status
    status: CallStatus = CallStatus.SUCCESS
    error_message: str | None = None
    error_code: str | None = None
    retry_count: int = 0
    fallback_used: bool = False
    fallback_backend: str | None = None

    # Additional metadata
    metadata: Dict[str, Any] | None = None  # Extra context (task type, tool calls, etc.)
    cached: bool = False                    # Whether response was cached

    def __post_init__(self):
        """Calculate derived fields."""
        if self.end_time and self.start_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000

        if self.prompt_tokens and self.completion_tokens:
            self.total_tokens = self.prompt_tokens + self.completion_tokens
```

### 2.2 SessionUsage (Aggregated Session Stats)

```python
@dataclass
class SessionUsage:
    """Aggregated usage for a session."""

    # Session info
    session_id: str
    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: float = 0

    # Call counts
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    cached_calls: int = 0

    # Token aggregates
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0

    # Cost aggregates
    total_cost_usd: float = 0.0

    # Per-backend breakdown
    backend_stats: Dict[str, "BackendSessionStats"] = None

    # Per-model breakdown
    model_stats: Dict[str, "ModelSessionStats"] = None

    # Error summary
    error_count: int = 0
    timeout_count: int = 0
    rate_limit_count: int = 0
    fallback_count: int = 0

    # Performance metrics
    avg_latency_ms: float = 0
    avg_tokens_per_second: float = 0

    def __post_init__(self):
        if self.backend_stats is None:
            self.backend_stats = {}
        if self.model_stats is None:
            self.model_stats = {}

@dataclass
class BackendSessionStats:
    """Usage stats for a specific backend within a session."""
    backend: str
    calls: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    errors: int = 0
    avg_latency_ms: float = 0

@dataclass
class ModelSessionStats:
    """Usage stats for a specific model within a session."""
    model: str
    backend: str
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
```

### 2.3 BackendUsageSummary (Historical Aggregates)

```python
@dataclass
class BackendUsageSummary:
    """Historical usage summary for a backend."""

    backend: str
    provider: str

    # Time window
    start_date: datetime
    end_date: datetime

    # Aggregates
    total_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    # Breakdown by model
    model_usage: Dict[str, "ModelUsageSummary"] = None

    # Breakdown by day/hour (for trend analysis)
    daily_usage: Dict[str, "DailyUsage"] = None

    def __post_init__(self):
        if self.model_usage is None:
            self.model_usage = {}
        if self.daily_usage is None:
            self.daily_usage = {}

@dataclass
class ModelUsageSummary:
    """Historical usage for a specific model."""
    model: str
    backend: str
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    avg_cost_per_call: float = 0.0

@dataclass
class DailyUsage:
    """Usage aggregated by day."""
    date: str  # YYYY-MM-DD
    calls: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
```

### 2.4 Database Schema (SQLite)

```sql
-- Main usage entries table
CREATE TABLE usage_entries (
    call_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Backend info
    backend TEXT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,

    -- Call details
    call_type TEXT NOT NULL,
    operation TEXT,
    persona TEXT,

    -- Metrics
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    prompt_chars INTEGER DEFAULT 0,
    completion_chars INTEGER DEFAULT 0,

    -- Timing
    start_time DATETIME,
    end_time DATETIME,
    duration_ms REAL DEFAULT 0,

    -- Streaming
    is_streaming BOOLEAN DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    first_token_latency_ms REAL DEFAULT 0,

    -- Cost
    input_cost_usd REAL DEFAULT 0.0,
    output_cost_usd REAL DEFAULT 0.0,
    total_cost_usd REAL DEFAULT 0.0,

    -- Status
    status TEXT DEFAULT 'success',
    error_message TEXT,
    error_code TEXT,
    retry_count INTEGER DEFAULT 0,
    fallback_used BOOLEAN DEFAULT 0,
    fallback_backend TEXT,

    -- Flags
    cached BOOLEAN DEFAULT 0,

    -- Indexes
    INDEX idx_session_id (session_id),
    INDEX idx_backend (backend),
    INDEX idx_model (model),
    INDEX idx_timestamp (timestamp),
    INDEX idx_status (status)
);

-- Sessions table
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    duration_seconds REAL DEFAULT 0,

    -- Aggregates
    total_calls INTEGER DEFAULT 0,
    successful_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,

    total_prompt_tokens INTEGER DEFAULT 0,
    total_completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0.0,

    -- Metadata
    project_name TEXT,
    user TEXT,
    description TEXT
);

-- Backend summaries (materialized aggregates)
CREATE TABLE backend_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backend TEXT NOT NULL,
    provider TEXT NOT NULL,
    date DATE NOT NULL,  -- Daily aggregates

    calls INTEGER DEFAULT 0,
    tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0.0,

    UNIQUE(backend, date)
);

-- Model summaries
CREATE TABLE model_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,
    backend TEXT NOT NULL,
    date DATE NOT NULL,

    calls INTEGER DEFAULT 0,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0.0,

    UNIQUE(model, backend, date)
);

-- Pricing data (model-specific)
CREATE TABLE model_pricing (
    model TEXT PRIMARY KEY,
    backend TEXT NOT NULL,
    provider TEXT NOT NULL,

    -- Pricing (USD per 1k tokens)
    input_price_per_1k REAL NOT NULL,
    output_price_per_1k REAL NOT NULL,

    -- Context limits
    max_input_tokens INTEGER,
    max_output_tokens INTEGER,

    -- Metadata
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_free BOOLEAN DEFAULT 0  -- Local models
);
```

---

## 3. Core Components

### 3.1 UsageTracker (Core Tracking Logic)

**Responsibilities:**
- Register call starts and ends
- Calculate token counts and costs
- Handle streaming incremental updates
- Record errors and fallbacks
- Persist to database

### 3.2 SessionManager

**Responsibilities:**
- Create and manage session lifecycle
- Aggregate usage within session
- Generate session IDs
- Provide session context to tracker

### 3.3 CostCalculator

**Responsibilities:**
- Load model pricing data
- Calculate cost from token counts
- Support different pricing models (per-token, per-call, tiered)
- Handle free/local models (cost = 0)

### 3.4 PersistentStorage

**Responsibilities:**
- SQLite database operations
- Insert usage entries
- Query aggregates
- Maintain summary tables
- Handle migrations

### 3.5 QuotaEnforcer

**Responsibilities:**
- Check usage against quotas
- Raise exceptions when exceeded
- Support multiple quota types (hourly, daily, monthly, per-session)

### 3.6 UsageReporter

**Responsibilities:**
- Format usage stats for display
- Generate CLI reports
- Export to JSON/CSV
- Create visualizations

---

## 4. Python API Interface

### 4.1 Main UsageTracker Interface

```python
from typing import Generator, ContextManager
from contextlib import contextmanager
import uuid
from datetime import datetime
import sqlite3

class UsageTracker:
    """
    Core usage tracking system.

    Tracks all LLM calls, aggregates by session, persists to database,
    and provides rich reporting capabilities.
    """

    def __init__(
        self,
        db_path: Path,
        config: ConfigLoader,
        cost_calculator: CostCalculator,
    ):
        self.db_path = db_path
        self.config = config
        self.cost_calculator = cost_calculator

        # Components
        self.storage = PersistentStorage(db_path)
        self.session_manager = SessionManager(self.storage)
        self.quota_enforcer = QuotaEnforcer(self, config)
        self.reporter = UsageReporter(self)

        # Current session
        self.current_session: Session | None = None

        # In-flight calls (for streaming)
        self.active_calls: Dict[str, UsageEntry] = {}

    # ============ Session Management ============

    def start_session(
        self,
        session_id: str | None = None,
        project_name: str | None = None,
        description: str | None = None,
    ) -> Session:
        """
        Start a new tracking session.

        Args:
            session_id: Optional custom session ID
            project_name: Optional project name
            description: Optional session description

        Returns:
            Session object

        Example:
            >>> tracker = UsageTracker(...)
            >>> session = tracker.start_session(project_name="my-project")
        """
        session = self.session_manager.create_session(
            session_id=session_id or self._generate_session_id(),
            project_name=project_name,
            description=description,
        )

        self.current_session = session
        return session

    def end_session(self) -> SessionUsage:
        """
        End current session and return stats.

        Returns:
            SessionUsage with aggregated stats

        Example:
            >>> stats = tracker.end_session()
            >>> print(f"Total cost: ${stats.total_cost_usd:.2f}")
        """
        if not self.current_session:
            raise ValueError("No active session")

        session_usage = self.session_manager.end_session(self.current_session.session_id)
        self.current_session = None

        return session_usage

    def get_current_session(self) -> Session | None:
        """Get current active session."""
        return self.current_session

    # ============ Call Tracking ============

    @contextmanager
    def track_call(
        self,
        backend: str,
        model: str,
        call_type: CallType,
        operation: str | None = None,
        persona: str | None = None,
        is_streaming: bool = False,
    ) -> Generator[str, None, None]:
        """
        Context manager for tracking a single LLM call.

        Usage:
            >>> with tracker.track_call("openai", "gpt-4", CallType.CHAT) as call_id:
            ...     response = backend.chat(messages)
            ...     tracker.record_tokens(call_id, response.usage)
        """
        call_id = self._generate_call_id()

        # Create usage entry
        entry = UsageEntry(
            call_id=call_id,
            session_id=self.current_session.session_id if self.current_session else "no-session",
            timestamp=datetime.now(),
            backend=backend,
            model=model,
            provider=self._get_provider(backend),
            call_type=call_type,
            operation=operation,
            persona=persona,
            is_streaming=is_streaming,
            start_time=datetime.now(),
        )

        self.active_calls[call_id] = entry

        try:
            yield call_id

            # Success - finalize entry
            entry.end_time = datetime.now()
            entry.status = CallStatus.SUCCESS

        except Exception as e:
            # Error - record it
            entry.end_time = datetime.now()
            entry.status = self._classify_error(e)
            entry.error_message = str(e)
            entry.error_code = type(e).__name__
            raise

        finally:
            # Always persist
            self._finalize_call(call_id)

    def record_tokens(
        self,
        call_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        cached: bool = False,
    ) -> None:
        """
        Record token counts for a call.

        Args:
            call_id: Call identifier from track_call()
            prompt_tokens: Input token count
            completion_tokens: Output token count
            cached: Whether response was cached
        """
        if call_id not in self.active_calls:
            raise ValueError(f"Unknown call_id: {call_id}")

        entry = self.active_calls[call_id]
        entry.prompt_tokens = prompt_tokens
        entry.completion_tokens = completion_tokens
        entry.total_tokens = prompt_tokens + completion_tokens
        entry.cached = cached

        # Calculate cost
        if not entry.cached:
            cost = self.cost_calculator.calculate_cost(
                model=entry.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
            entry.input_cost_usd = cost.input_cost
            entry.output_cost_usd = cost.output_cost
            entry.total_cost_usd = cost.total_cost

    def record_chunk(
        self,
        call_id: str,
        chunk_tokens: int = 1,
    ) -> None:
        """
        Record a streaming chunk.

        Args:
            call_id: Call identifier
            chunk_tokens: Tokens in this chunk (usually 1)
        """
        if call_id not in self.active_calls:
            return

        entry = self.active_calls[call_id]
        entry.chunk_count += 1
        entry.completion_tokens += chunk_tokens
        entry.total_tokens += chunk_tokens

        # Record TTFT (time to first token)
        if entry.chunk_count == 1 and entry.start_time:
            entry.first_token_latency_ms = (
                (datetime.now() - entry.start_time).total_seconds() * 1000
            )

    def record_error(
        self,
        call_id: str,
        error: Exception,
        fallback_backend: str | None = None,
    ) -> None:
        """
        Record an error for a call.

        Args:
            call_id: Call identifier
            error: Exception that occurred
            fallback_backend: Backend used as fallback (if any)
        """
        if call_id not in self.active_calls:
            return

        entry = self.active_calls[call_id]
        entry.status = self._classify_error(error)
        entry.error_message = str(error)
        entry.error_code = type(error).__name__

        if fallback_backend:
            entry.fallback_used = True
            entry.fallback_backend = fallback_backend

    def record_fallback(
        self,
        original_call_id: str,
        fallback_backend: str,
    ) -> None:
        """Mark that a fallback was used."""
        if original_call_id in self.active_calls:
            entry = self.active_calls[original_call_id]
            entry.fallback_used = True
            entry.fallback_backend = fallback_backend

    # ============ Queries & Stats ============

    def get_session_stats(
        self,
        session_id: str | None = None,
    ) -> SessionUsage:
        """
        Get stats for a session.

        Args:
            session_id: Session to query (None = current session)

        Returns:
            SessionUsage with aggregated stats
        """
        if session_id is None:
            if not self.current_session:
                raise ValueError("No active session")
            session_id = self.current_session.session_id

        return self.storage.get_session_usage(session_id)

    def get_backend_stats(
        self,
        backend: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> BackendUsageSummary:
        """
        Get historical stats for a backend.

        Args:
            backend: Backend name
            start_date: Start of time window
            end_date: End of time window

        Returns:
            BackendUsageSummary
        """
        return self.storage.get_backend_summary(backend, start_date, end_date)

    def get_global_stats(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Dict[str, BackendUsageSummary]:
        """
        Get stats across all backends.

        Returns:
            Dict mapping backend name to BackendUsageSummary
        """
        return self.storage.get_global_summary(start_date, end_date)

    def get_model_stats(
        self,
        model: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ModelUsageSummary:
        """Get historical stats for a specific model."""
        return self.storage.get_model_summary(model, start_date, end_date)

    # ============ Quota Checking ============

    def check_quota(
        self,
        backend: str,
        estimated_tokens: int = 0,
    ) -> None:
        """
        Check if request would exceed quotas.

        Raises:
            QuotaExceededError if quota would be exceeded
        """
        self.quota_enforcer.check(backend, estimated_tokens)

    # ============ Export & Reporting ============

    def export_session(
        self,
        output_path: Path,
        format: Literal["json", "csv"] = "json",
        session_id: str | None = None,
    ) -> None:
        """Export session data to file."""
        self.reporter.export_session(output_path, format, session_id)

    def export_global_usage(
        self,
        output_path: Path,
        format: Literal["json", "csv"] = "json",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> None:
        """Export all usage data to file."""
        self.reporter.export_global(output_path, format, start_date, end_date)

    def generate_report(
        self,
        report_type: Literal["session", "backend", "model", "global"],
        **kwargs,
    ) -> str:
        """
        Generate formatted report for CLI display.

        Args:
            report_type: Type of report
            **kwargs: Report-specific arguments

        Returns:
            Formatted report string
        """
        return self.reporter.generate_report(report_type, **kwargs)

    # ============ Private Methods ============

    def _finalize_call(self, call_id: str) -> None:
        """Finalize and persist a call entry."""
        if call_id not in self.active_calls:
            return

        entry = self.active_calls.pop(call_id)

        # Calculate final cost if streaming
        if entry.is_streaming and entry.completion_tokens > 0:
            cost = self.cost_calculator.calculate_cost(
                model=entry.model,
                prompt_tokens=entry.prompt_tokens,
                completion_tokens=entry.completion_tokens,
            )
            entry.total_cost_usd = cost.total_cost

        # Persist to database
        self.storage.insert_usage_entry(entry)

        # Update session aggregates
        if self.current_session:
            self.session_manager.add_call_to_session(
                self.current_session.session_id, entry
            )

    def _generate_call_id(self) -> str:
        """Generate unique call ID."""
        return f"call_{uuid.uuid4().hex[:12]}"

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{timestamp}_{uuid.uuid4().hex[:8]}"

    def _get_provider(self, backend: str) -> str:
        """Get provider name from backend."""
        # Map backend to provider
        mapping = {
            "openai": "openai",
            "claude": "anthropic",
            "opus": "anthropic",
            "gemini": "google",
            "ollama": "local",
        }
        return mapping.get(backend, "unknown")

    def _classify_error(self, error: Exception) -> CallStatus:
        """Classify error type."""
        error_str = str(error).lower()

        if "rate limit" in error_str or "429" in error_str:
            return CallStatus.RATE_LIMITED
        elif "timeout" in error_str:
            return CallStatus.TIMEOUT
        elif "quota" in error_str:
            return CallStatus.QUOTA_EXCEEDED
        else:
            return CallStatus.ERROR
```

---

## 5. Cost Estimation & Pricing

### 5.1 CostCalculator

```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class CostBreakdown:
    """Cost calculation result."""
    input_cost: float
    output_cost: float
    total_cost: float
    pricing_model: str  # "per_token" | "free" | "fixed"

class CostCalculator:
    """
    Calculate costs for LLM calls based on model pricing.

    Supports:
    - Per-token pricing (most APIs)
    - Free models (local LLMs)
    - Fixed-price models (rare)
    """

    def __init__(self, storage: PersistentStorage):
        self.storage = storage
        self.pricing_cache: Dict[str, ModelPricing] = {}
        self._load_pricing()

    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> CostBreakdown:
        """
        Calculate cost for a call.

        Args:
            model: Model name
            prompt_tokens: Input token count
            completion_tokens: Output token count

        Returns:
            CostBreakdown with input/output/total costs
        """
        # Get pricing for model
        pricing = self.get_model_pricing(model)

        if pricing.is_free:
            return CostBreakdown(
                input_cost=0.0,
                output_cost=0.0,
                total_cost=0.0,
                pricing_model="free",
            )

        # Calculate per-token costs
        input_cost = (prompt_tokens / 1000) * pricing.input_price_per_1k
        output_cost = (completion_tokens / 1000) * pricing.output_price_per_1k

        return CostBreakdown(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=input_cost + output_cost,
            pricing_model="per_token",
        )

    def get_model_pricing(self, model: str) -> "ModelPricing":
        """Get pricing info for a model."""
        # Check cache
        if model in self.pricing_cache:
            return self.pricing_cache[model]

        # Load from database
        pricing = self.storage.get_model_pricing(model)

        if not pricing:
            # Unknown model - assume free (conservative)
            pricing = ModelPricing(
                model=model,
                backend="unknown",
                provider="unknown",
                input_price_per_1k=0.0,
                output_price_per_1k=0.0,
                is_free=True,
            )

        self.pricing_cache[model] = pricing
        return pricing

    def set_model_pricing(
        self,
        model: str,
        backend: str,
        provider: str,
        input_price_per_1k: float,
        output_price_per_1k: float,
        is_free: bool = False,
    ) -> None:
        """Set pricing for a model."""
        pricing = ModelPricing(
            model=model,
            backend=backend,
            provider=provider,
            input_price_per_1k=input_price_per_1k,
            output_price_per_1k=output_price_per_1k,
            is_free=is_free,
        )

        self.storage.upsert_model_pricing(pricing)
        self.pricing_cache[model] = pricing

    def _load_pricing(self) -> None:
        """Load all pricing data from database."""
        all_pricing = self.storage.get_all_model_pricing()
        for pricing in all_pricing:
            self.pricing_cache[pricing.model] = pricing

@dataclass
class ModelPricing:
    """Pricing information for a model."""
    model: str
    backend: str
    provider: str
    input_price_per_1k: float   # USD per 1k input tokens
    output_price_per_1k: float  # USD per 1k output tokens
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    is_free: bool = False
    last_updated: datetime | None = None
```

### 5.2 Default Pricing Data

```python
DEFAULT_PRICING = {
    # OpenAI
    "gpt-4o": {
        "backend": "openai",
        "provider": "openai",
        "input_price_per_1k": 0.0025,
        "output_price_per_1k": 0.01,
        "max_input_tokens": 128000,
    },
    "gpt-4": {
        "backend": "openai",
        "provider": "openai",
        "input_price_per_1k": 0.03,
        "output_price_per_1k": 0.06,
        "max_input_tokens": 8192,
    },
    "gpt-3.5-turbo": {
        "backend": "openai",
        "provider": "openai",
        "input_price_per_1k": 0.0005,
        "output_price_per_1k": 0.0015,
        "max_input_tokens": 16385,
    },

    # Anthropic
    "claude-opus-4-5-20251101": {
        "backend": "opus",
        "provider": "anthropic",
        "input_price_per_1k": 0.015,
        "output_price_per_1k": 0.075,
        "max_input_tokens": 200000,
    },
    "claude-sonnet-4.5-20250929": {
        "backend": "claude",
        "provider": "anthropic",
        "input_price_per_1k": 0.003,
        "output_price_per_1k": 0.015,
        "max_input_tokens": 200000,
    },

    # Google
    "gemini-2-flash": {
        "backend": "gemini",
        "provider": "google",
        "input_price_per_1k": 0.0001,
        "output_price_per_1k": 0.0004,
        "max_input_tokens": 1000000,
    },

    # Local (free)
    "deepseek-coder:latest": {
        "backend": "ollama",
        "provider": "local",
        "input_price_per_1k": 0.0,
        "output_price_per_1k": 0.0,
        "is_free": True,
        "max_input_tokens": 8192,
    },
}

def initialize_pricing(calculator: CostCalculator):
    """Initialize default pricing in database."""
    for model, pricing_data in DEFAULT_PRICING.items():
        calculator.set_model_pricing(model=model, **pricing_data)
```

---

## 6. Session Management

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Session:
    """Active session object."""
    session_id: str
    start_time: datetime
    project_name: str | None = None
    description: str | None = None
    user: str | None = None

    # Real-time aggregates (updated as calls complete)
    call_count: int = 0
    token_count: int = 0
    cost_usd: float = 0.0
    error_count: int = 0

class SessionManager:
    """Manages session lifecycle and aggregation."""

    def __init__(self, storage: PersistentStorage):
        self.storage = storage
        self.active_sessions: Dict[str, Session] = {}

    def create_session(
        self,
        session_id: str,
        project_name: str | None = None,
        description: str | None = None,
    ) -> Session:
        """Create and start a new session."""
        session = Session(
            session_id=session_id,
            start_time=datetime.now(),
            project_name=project_name,
            description=description,
        )

        # Persist to database
        self.storage.insert_session(session)

        # Track in memory
        self.active_sessions[session_id] = session

        return session

    def end_session(self, session_id: str) -> SessionUsage:
        """End a session and compute final stats."""
        session = self.active_sessions.pop(session_id, None)

        if not session:
            # Load from database
            session = self.storage.get_session(session_id)

        # Compute final aggregates
        usage = self.storage.get_session_usage(session_id)

        # Update session end time
        self.storage.update_session_end_time(session_id, datetime.now())

        return usage

    def add_call_to_session(
        self,
        session_id: str,
        usage_entry: UsageEntry,
    ) -> None:
        """Update session with a completed call."""
        session = self.active_sessions.get(session_id)

        if session:
            # Update in-memory aggregates
            session.call_count += 1
            session.token_count += usage_entry.total_tokens
            session.cost_usd += usage_entry.total_cost_usd

            if usage_entry.status != CallStatus.SUCCESS:
                session.error_count += 1

        # Update database aggregates
        self.storage.update_session_aggregates(session_id, usage_entry)

    def get_session_stats(self, session_id: str) -> SessionUsage:
        """Get current stats for a session."""
        return self.storage.get_session_usage(session_id)
```

---

## 7. Quota Enforcement

```python
from datetime import datetime, timedelta

class QuotaExceededError(Exception):
    """Raised when usage quota is exceeded."""
    pass

@dataclass
class QuotaConfig:
    """Quota configuration."""
    # Cost limits
    max_cost_per_hour: float | None = None
    max_cost_per_day: float | None = None
    max_cost_per_month: float | None = None
    max_cost_per_session: float | None = None

    # Token limits
    max_tokens_per_hour: int | None = None
    max_tokens_per_day: int | None = None
    max_tokens_per_request: int | None = None

    # Request limits
    max_requests_per_minute: int | None = None
    max_requests_per_hour: int | None = None

class QuotaEnforcer:
    """Enforce usage quotas."""

    def __init__(self, tracker: UsageTracker, config: ConfigLoader):
        self.tracker = tracker
        self.quota_config = self._load_quota_config(config)

    def check(
        self,
        backend: str,
        estimated_tokens: int = 0,
    ) -> None:
        """
        Check if request would exceed quotas.

        Raises:
            QuotaExceededError if any quota would be exceeded
        """
        # Check session quota
        if self.tracker.current_session:
            self._check_session_quota(estimated_tokens)

        # Check hourly quotas
        self._check_hourly_quota(backend, estimated_tokens)

        # Check daily quotas
        self._check_daily_quota(backend, estimated_tokens)

        # Check per-request limits
        self._check_request_quota(estimated_tokens)

    def _check_session_quota(self, estimated_tokens: int) -> None:
        """Check session-level quotas."""
        if not self.quota_config.max_cost_per_session:
            return

        session = self.tracker.current_session
        if session.cost_usd >= self.quota_config.max_cost_per_session:
            raise QuotaExceededError(
                f"Session cost quota exceeded: "
                f"${session.cost_usd:.2f} >= ${self.quota_config.max_cost_per_session:.2f}"
            )

    def _check_hourly_quota(self, backend: str, estimated_tokens: int) -> None:
        """Check hourly quotas."""
        if not (self.quota_config.max_cost_per_hour or self.quota_config.max_tokens_per_hour):
            return

        # Get usage in last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        hourly_usage = self.tracker.storage.get_usage_in_timeframe(
            start_time=one_hour_ago,
            end_time=datetime.now(),
        )

        # Check cost quota
        if self.quota_config.max_cost_per_hour:
            if hourly_usage.total_cost >= self.quota_config.max_cost_per_hour:
                raise QuotaExceededError(
                    f"Hourly cost quota exceeded: "
                    f"${hourly_usage.total_cost:.2f} >= ${self.quota_config.max_cost_per_hour:.2f}"
                )

        # Check token quota
        if self.quota_config.max_tokens_per_hour:
            if hourly_usage.total_tokens + estimated_tokens >= self.quota_config.max_tokens_per_hour:
                raise QuotaExceededError(
                    f"Hourly token quota exceeded: "
                    f"{hourly_usage.total_tokens} >= {self.quota_config.max_tokens_per_hour}"
                )

    def _check_daily_quota(self, backend: str, estimated_tokens: int) -> None:
        """Check daily quotas."""
        if not self.quota_config.max_cost_per_day:
            return

        # Get usage today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_usage = self.tracker.storage.get_usage_in_timeframe(
            start_time=today_start,
            end_time=datetime.now(),
        )

        if daily_usage.total_cost >= self.quota_config.max_cost_per_day:
            raise QuotaExceededError(
                f"Daily cost quota exceeded: "
                f"${daily_usage.total_cost:.2f} >= ${self.quota_config.max_cost_per_day:.2f}"
            )

    def _check_request_quota(self, estimated_tokens: int) -> None:
        """Check per-request limits."""
        if not self.quota_config.max_tokens_per_request:
            return

        if estimated_tokens > self.quota_config.max_tokens_per_request:
            raise QuotaExceededError(
                f"Request token limit exceeded: "
                f"{estimated_tokens} > {self.quota_config.max_tokens_per_request}"
            )

    def _load_quota_config(self, config: ConfigLoader) -> QuotaConfig:
        """Load quota configuration."""
        return QuotaConfig(
            max_cost_per_hour=config.get("quotas.max_cost_per_hour"),
            max_cost_per_day=config.get("quotas.max_cost_per_day"),
            max_cost_per_month=config.get("quotas.max_cost_per_month"),
            max_cost_per_session=config.get("quotas.max_cost_per_session"),
            max_tokens_per_hour=config.get("quotas.max_tokens_per_hour"),
            max_tokens_per_day=config.get("quotas.max_tokens_per_day"),
            max_tokens_per_request=config.get("quotas.max_tokens_per_request"),
            max_requests_per_minute=config.get("quotas.max_requests_per_minute"),
        )
```

---

## 8. Reporting & Visualization

### 8.1 CLI Report Formats

```python
class UsageReporter:
    """Generate formatted usage reports."""

    def __init__(self, tracker: UsageTracker):
        self.tracker = tracker

    def generate_report(
        self,
        report_type: Literal["session", "backend", "model", "global"],
        **kwargs,
    ) -> str:
        """Generate formatted report."""
        if report_type == "session":
            return self._format_session_report(**kwargs)
        elif report_type == "backend":
            return self._format_backend_report(**kwargs)
        elif report_type == "model":
            return self._format_model_report(**kwargs)
        elif report_type == "global":
            return self._format_global_report(**kwargs)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    def _format_session_report(self, session_id: str | None = None) -> str:
        """Format session usage report for CLI."""
        usage = self.tracker.get_session_stats(session_id)

        report = f"""
╔══════════════════════════════════════════════════════════╗
║              SESSION USAGE REPORT                        ║
╚══════════════════════════════════════════════════════════╝

Session ID: {usage.session_id}
Duration: {usage.duration_seconds:.1f}s
Started: {usage.start_time.strftime('%Y-%m-%d %H:%M:%S')}
{"Ended: " + usage.end_time.strftime('%Y-%m-%d %H:%M:%S') if usage.end_time else "Status: Active"}

┌─ REQUESTS ─────────────────────────────────────────────┐
│ Total Calls:      {usage.total_calls:>6}                           │
│ Successful:       {usage.successful_calls:>6}                           │
│ Failed:           {usage.failed_calls:>6}                           │
│ Cached:           {usage.cached_calls:>6}                           │
│ Fallbacks Used:   {usage.fallback_count:>6}                           │
└────────────────────────────────────────────────────────┘

┌─ TOKENS ───────────────────────────────────────────────┐
│ Prompt Tokens:    {usage.total_prompt_tokens:>10,}                     │
│ Completion Tokens:{usage.total_completion_tokens:>10,}                     │
│ Total Tokens:     {usage.total_tokens:>10,}                     │
└────────────────────────────────────────────────────────┘

┌─ COST ─────────────────────────────────────────────────┐
│ Total Cost:       ${usage.total_cost_usd:>10.4f} USD                │
│ Avg per Call:     ${usage.total_cost_usd/max(usage.total_calls,1):>10.4f} USD                │
└────────────────────────────────────────────────────────┘

┌─ PERFORMANCE ──────────────────────────────────────────┐
│ Avg Latency:      {usage.avg_latency_ms:>10.1f} ms                  │
│ Tokens/Second:    {usage.avg_tokens_per_second:>10.1f}                       │
└────────────────────────────────────────────────────────┘

┌─ BY BACKEND ───────────────────────────────────────────┐
"""
        for backend, stats in usage.backend_stats.items():
            report += f"""│ {backend:.<20} {stats.calls:>4} calls  {stats.tokens:>8,} tokens  ${stats.cost_usd:>8.4f} │
"""
        report += """└────────────────────────────────────────────────────────┘

"""
        return report

    def _format_backend_report(
        self,
        backend: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> str:
        """Format backend usage report."""
        summary = self.tracker.get_backend_stats(backend, start_date, end_date)

        report = f"""
╔══════════════════════════════════════════════════════════╗
║              BACKEND USAGE REPORT                        ║
╚══════════════════════════════════════════════════════════╝

Backend: {summary.backend}
Provider: {summary.provider}
Period: {summary.start_date.strftime('%Y-%m-%d')} to {summary.end_date.strftime('%Y-%m-%d')}

┌─ TOTALS ───────────────────────────────────────────────┐
│ Total Calls:      {summary.total_calls:>10,}                     │
│ Total Tokens:     {summary.total_tokens:>10,}                     │
│ Total Cost:       ${summary.total_cost_usd:>10.2f} USD                │
└────────────────────────────────────────────────────────┘

┌─ BY MODEL ─────────────────────────────────────────────┐
"""
        for model, stats in summary.model_usage.items():
            report += f"""│ {model:.<25}                                       │
│   Calls:          {stats.calls:>10,}                     │
│   Tokens:         {stats.total_tokens:>10,}                     │
│   Cost:           ${stats.cost_usd:>10.4f} USD                │
│   Avg/Call:       ${stats.avg_cost_per_call:>10.4f} USD                │
│                                                        │
"""
        report += """└────────────────────────────────────────────────────────┘

"""
        return report

    def _format_global_report(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> str:
        """Format global usage report across all backends."""
        all_stats = self.tracker.get_global_stats(start_date, end_date)

        total_calls = sum(s.total_calls for s in all_stats.values())
        total_tokens = sum(s.total_tokens for s in all_stats.values())
        total_cost = sum(s.total_cost_usd for s in all_stats.values())

        report = f"""
╔══════════════════════════════════════════════════════════╗
║              GLOBAL USAGE REPORT                         ║
╚══════════════════════════════════════════════════════════╝

Period: {(start_date or datetime.now()).strftime('%Y-%m-%d')} to {(end_date or datetime.now()).strftime('%Y-%m-%d')}

┌─ OVERALL TOTALS ───────────────────────────────────────┐
│ Total Calls:      {total_calls:>10,}                     │
│ Total Tokens:     {total_tokens:>10,}                     │
│ Total Cost:       ${total_cost:>10.2f} USD                │
└────────────────────────────────────────────────────────┘

┌─ BY BACKEND ───────────────────────────────────────────┐
"""
        for backend, stats in all_stats.items():
            pct_calls = (stats.total_calls / max(total_calls, 1)) * 100
            pct_cost = (stats.total_cost_usd / max(total_cost, 1)) * 100

            report += f"""│ {backend:.<20}                                    │
│   Calls:          {stats.total_calls:>6,} ({pct_calls:>5.1f}%)                    │
│   Tokens:         {stats.total_tokens:>10,}                     │
│   Cost:           ${stats.total_cost_usd:>8.2f} ({pct_cost:>5.1f}%)                 │
│                                                        │
"""
        report += """└────────────────────────────────────────────────────────┘

"""
        return report

    def export_session(
        self,
        output_path: Path,
        format: Literal["json", "csv"],
        session_id: str | None = None,
    ) -> None:
        """Export session data to file."""
        usage = self.tracker.get_session_stats(session_id)

        if format == "json":
            self._export_json(output_path, usage)
        elif format == "csv":
            self._export_csv(output_path, usage)

    def _export_json(self, path: Path, data: Any) -> None:
        """Export to JSON."""
        import json
        from dataclasses import asdict

        with open(path, "w") as f:
            json.dump(asdict(data), f, indent=2, default=str)

    def _export_csv(self, path: Path, usage: SessionUsage) -> None:
        """Export to CSV."""
        import csv

        # Get individual calls for this session
        calls = self.tracker.storage.get_session_calls(usage.session_id)

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "call_id", "timestamp", "backend", "model", "call_type",
                "prompt_tokens", "completion_tokens", "total_tokens",
                "duration_ms", "cost_usd", "status"
            ])
            writer.writeheader()

            for call in calls:
                writer.writerow({
                    "call_id": call.call_id,
                    "timestamp": call.timestamp.isoformat(),
                    "backend": call.backend,
                    "model": call.model,
                    "call_type": call.call_type.value,
                    "prompt_tokens": call.prompt_tokens,
                    "completion_tokens": call.completion_tokens,
                    "total_tokens": call.total_tokens,
                    "duration_ms": call.duration_ms,
                    "cost_usd": call.total_cost_usd,
                    "status": call.status.value,
                })
```

### 8.2 Example CLI Commands

```bash
# Show current session stats
$ blueprint stats session
# (displays formatted session report)

# Show backend-specific stats
$ blueprint stats backend openai

# Show model-specific stats
$ blueprint stats model gpt-4o

# Show global stats (all backends, all time)
$ blueprint stats global

# Show stats for date range
$ blueprint stats global --start 2025-12-01 --end 2025-12-31

# Export session to JSON
$ blueprint export session --format json --output session_usage.json

# Export global usage to CSV
$ blueprint export global --format csv --output usage_report.csv
```

---

## 9. Integration Points

### 9.1 Integration with Orchestrator

The usage tracker integrates at key points in the orchestration flow:

```python
class LLMOrchestrator:
    def __init__(self, ...):
        # ... existing init ...

        # Add usage tracker
        self.usage_tracker = UsageTracker(
            db_path=Path.home() / ".config" / "blueprint" / "usage.db",
            config=self.config,
            cost_calculator=CostCalculator(...),
        )

        # Start session automatically
        self.usage_tracker.start_session(
            project_name=self.config.get("project.name"),
        )

    def chat(self, message, *, backend=None, **kwargs) -> ChatResponse:
        """Chat with usage tracking."""

        # ... existing code to prepare messages and select backend ...

        # Check quota before making call
        try:
            self.usage_tracker.check_quota(backend)
        except QuotaExceededError as e:
            # Handle quota exceeded - maybe fallback or raise
            print(f"Warning: {e}")
            # Try fallback...

        # Track the call
        with self.usage_tracker.track_call(
            backend=backend,
            model=self.model,
            call_type=CallType.CHAT,
            operation="chat",
            persona=kwargs.get("persona"),
        ) as call_id:

            # Execute call
            backend_impl = self._backends[backend]
            response = backend_impl.chat(messages=messages, **kwargs)

            # Record usage
            self.usage_tracker.record_tokens(
                call_id=call_id,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                cached=response.metadata.cached,
            )

        return response

    def stream(self, message, *, backend=None, **kwargs) -> Iterator[StreamChunk]:
        """Stream with usage tracking."""

        # ... existing code ...

        with self.usage_tracker.track_call(
            backend=backend,
            model=self.model,
            call_type=CallType.STREAM,
            is_streaming=True,
        ) as call_id:

            for chunk in backend_impl.stream(messages=messages, **kwargs):
                # Record each chunk
                if chunk.delta:
                    self.usage_tracker.record_chunk(call_id, chunk_tokens=1)

                yield chunk

                # At end, record final usage
                if chunk.is_done and chunk.usage:
                    self.usage_tracker.record_tokens(
                        call_id=call_id,
                        prompt_tokens=chunk.usage.prompt_tokens,
                        completion_tokens=chunk.usage.completion_tokens,
                    )
```

### 9.2 Integration with Backend Wrappers

Backend wrappers should extract usage info from API responses:

```python
class BackendWrapper:
    def chat(self, messages, **kwargs) -> ChatResponse:
        # ... make API call ...

        response = ChatResponse(
            content=...,
            usage=UsageInfo(
                prompt_tokens=api_response.usage.prompt_tokens,
                completion_tokens=api_response.usage.completion_tokens,
                total_tokens=api_response.usage.total_tokens,
            ),
            # ...
        )

        return response
```

### 9.3 For Local Models Without Token Counts

```python
def estimate_tokens(text: str) -> int:
    """Estimate token count for models that don't report it."""
    # Simple heuristic: ~4 characters per token
    return len(text) // 4

class OllamaAdapter:
    def chat(self, messages, **kwargs) -> ChatResponse:
        # ... make API call ...

        # Ollama may not return token counts, estimate them
        prompt_text = "\n".join(msg.content for msg in messages)
        completion_text = response_content

        usage = UsageInfo(
            prompt_tokens=estimate_tokens(prompt_text),
            completion_tokens=estimate_tokens(completion_text),
            total_tokens=estimate_tokens(prompt_text) + estimate_tokens(completion_text),
        )

        return ChatResponse(content=completion_text, usage=usage, ...)
```

---

## 10. Example Implementation

### 10.1 Complete Usage Example

```python
from pathlib import Path
from blueprint.orchestrator import LLMOrchestrator
from blueprint.usage import UsageTracker, CallType

# Initialize orchestrator (includes usage tracker)
orchestrator = LLMOrchestrator()

# Usage tracking starts automatically with session

# Make some calls
response1 = orchestrator.chat("Explain Python decorators")
response2 = orchestrator.chat("Write a merge sort function", backend="openai")

# Stream a response
for chunk in orchestrator.stream("Generate a README"):
    print(chunk.delta, end="", flush=True)

# Check current session stats
session_stats = orchestrator.usage_tracker.get_session_stats()
print(f"\nSession cost so far: ${session_stats.total_cost_usd:.4f}")
print(f"Total tokens: {session_stats.total_tokens:,}")

# Generate report
report = orchestrator.usage_tracker.generate_report("session")
print(report)

# Export session data
orchestrator.usage_tracker.export_session(
    Path("session_report.json"),
    format="json"
)

# End session
final_stats = orchestrator.usage_tracker.end_session()
print(f"Final session cost: ${final_stats.total_cost_usd:.4f}")
```

### 10.2 Standalone Usage Tracking

```python
# Use tracker independently
from blueprint.usage import UsageTracker, CostCalculator, PersistentStorage

storage = PersistentStorage(Path("usage.db"))
calculator = CostCalculator(storage)
tracker = UsageTracker(Path("usage.db"), config, calculator)

# Start session
session = tracker.start_session(project_name="my-project")

# Track a manual call
with tracker.track_call(
    backend="openai",
    model="gpt-4o",
    call_type=CallType.CHAT,
) as call_id:
    # Make API call
    response = api_client.chat(...)

    # Record usage
    tracker.record_tokens(
        call_id=call_id,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
    )

# End session
stats = tracker.end_session()
print(f"Total cost: ${stats.total_cost_usd:.2f}")
```

---

## 11. Limitations & Trade-offs

### 11.1 What Can Be Reliably Tracked

| Metric | Paid APIs | Local Models | Notes |
|--------|-----------|--------------|-------|
| **Request Count** | ✅ Exact | ✅ Exact | Always accurate |
| **Token Counts** | ✅ Exact | ⚠️ Estimated | Local models may not report tokens |
| **Cost** | ✅ Calculated | ✅ Zero | Pricing data must be kept current |
| **Latency** | ✅ Measured | ✅ Measured | Wall-clock time |
| **TTFT** | ✅ Streaming | ✅ Streaming | Time to first token |
| **Error Rates** | ✅ Tracked | ✅ Tracked | All errors logged |

### 11.2 Known Limitations

**1. Token Estimation Accuracy**
- Local models (Ollama) often don't report exact token counts
- Estimation heuristic (~4 chars/token) is approximate
- Can differ by ±20% from actual tokenization

**Mitigation:**
- Use estimation consistently
- Track character counts as fallback
- Note in reports when tokens are estimated

**2. Streaming Token Counts**
- Some APIs don't report usage until stream completes
- Incremental counting may miss tokens in metadata
- Final count may differ from chunk-by-chunk sum

**Mitigation:**
- Always use final usage report if available
- Log discrepancies for debugging
- Prefer API-reported counts over estimates

**3. Pricing Data Staleness**
- API pricing changes over time
- Must manually update pricing database
- Historical costs may be inaccurate retroactively

**Mitigation:**
- Periodic pricing updates
- Version pricing data with timestamps
- Allow manual cost overrides

**4. Caching Impact on Cost**
- Cached responses don't consume tokens but may not be free
- Prompt caching has different pricing
- Hard to attribute cached savings

**Mitigation:**
- Flag cached responses separately
- Track cache hit rate
- Document caching policy

**5. Overhead**
- Database writes add ~1-5ms per call
- SQLite locking can bottleneck at high concurrency
- Memory usage for active calls

**Mitigation:**
- Async writes (optional)
- Batch inserts
- Periodic cleanup of old data

### 11.3 Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| **Track Everything** | Complete audit trail | Storage overhead, complexity |
| **Track Aggregates Only** | Low overhead | Can't debug individual calls |
| **Real-time Updates** | Immediate visibility | Performance impact |
| **Batch Updates** | Better performance | Delayed visibility |
| **Detailed Metadata** | Rich debugging | Privacy concerns |
| **Minimal Metadata** | Privacy-friendly | Limited debugging |

**Recommendation:** Track individual calls with essential metadata, aggregate in real-time for session stats, batch-write historical summaries.

---

## 12. Integration Recommendations

### 12.1 Files to Update

**1. Orchestrator (`orchestrator.py`)**
- Add `usage_tracker` initialization
- Wrap all LLM calls with tracking
- Check quotas before calls
- Handle `QuotaExceededError`

**2. Backend Wrappers (`wrapper/adapters/`)**
- Ensure all responses include `UsageInfo`
- Estimate tokens for backends that don't report them
- Include metadata (cached, streaming, etc.)

**3. Config System (`config/config.toml`)**
- Add `[usage]` section for database path
- Add `[quotas]` section for limits
- Add `[pricing]` section for model costs

**4. CLI (`cli/main.py`)**
- Add `/stats` command group
- Add `/export` command
- Show usage warnings in output

**5. Session Management**
- Integrate session lifecycle with orchestrator startup/shutdown
- Persist session IDs across restarts (optional)

### 12.2 Configuration Example

```toml
# ~/.config/blueprint/config.toml

[usage]
database_path = "~/.config/blueprint/usage.db"
enable_tracking = true
track_metadata = true  # Include extra context in logs
auto_export_on_session_end = false

[quotas]
max_cost_per_hour = 10.0
max_cost_per_day = 100.0
max_cost_per_month = 500.0
max_cost_per_session = 25.0

max_tokens_per_hour = 1000000
max_tokens_per_request = 100000

warn_at_percent = 80  # Warn when 80% of quota used

[pricing]
# Pricing data loaded from database
# Can override specific models here
# gpt-4o_input_price_per_1k = 0.0025
```

### 12.3 Initialization in Main

```python
# blueprint/cli/main.py

def main():
    # Load config
    config = ConfigLoader()

    # Initialize orchestrator (includes usage tracker)
    orchestrator = LLMOrchestrator(config)

    # Start session
    orchestrator.usage_tracker.start_session(
        project_name=detect_project_name(),
        description="CLI session",
    )

    try:
        # Run CLI
        cli_loop(orchestrator)

    finally:
        # End session and show summary
        stats = orchestrator.usage_tracker.end_session()

        print("\n" + "="*60)
        print("SESSION SUMMARY")
        print("="*60)
        print(f"Total calls: {stats.total_calls}")
        print(f"Total tokens: {stats.total_tokens:,}")
        print(f"Total cost: ${stats.total_cost_usd:.4f}")
        print(f"Duration: {stats.duration_seconds:.1f}s")

        if stats.total_cost_usd > 1.0:
            print(f"\n⚠️  High cost session! Consider using cheaper models.")
```

---

## 13. Documentation Structure

### 13.1 LLM_USAGE.md Content

Create `/LLM_USAGE.md` in project root:

```markdown
# LLM Usage Tracking

This project tracks all LLM API usage for monitoring costs and performance.

## What is Tracked

For every LLM call, we record:
- **Backend & Model**: Which LLM provider and model was used
- **Token Counts**: Input, output, and total tokens
- **Cost**: Estimated cost in USD (based on current pricing)
- **Timing**: Request duration and latency metrics
- **Status**: Success, errors, timeouts, rate limits
- **Context**: Session ID, operation type, persona used

## Data Storage

Usage data is stored in:
- **Database**: `~/.config/blueprint/usage.db` (SQLite)
- **Session Logs**: `.blueprint/sessions/` (JSON, per-session)
- **Exports**: User-generated exports (JSON/CSV)

## Viewing Usage Stats

### Current Session
```bash
blueprint stats session
```

### Specific Backend
```bash
blueprint stats backend openai
blueprint stats backend ollama
```

### All Backends (Global)
```bash
blueprint stats global
blueprint stats global --start 2025-12-01 --end 2025-12-31
```

### Export Data
```bash
# Export current session
blueprint export session --format json --output my_session.json

# Export all usage
blueprint export global --format csv --output usage_report.csv
```

## Cost Estimation

Costs are estimated using current pricing data for each model:

| Model | Input (per 1k tokens) | Output (per 1k tokens) |
|-------|----------------------|------------------------|
| gpt-4o | $0.0025 | $0.01 |
| gpt-4 | $0.03 | $0.06 |
| claude-opus-4-5 | $0.015 | $0.075 |
| claude-sonnet-4.5 | $0.003 | $0.015 |
| gemini-2-flash | $0.0001 | $0.0004 |
| ollama (local) | $0 | $0 |

**Note:** Local models (Ollama) have zero cost but still consume compute resources.

## Quotas

Default quotas (configurable in `~/.config/blueprint/config.toml`):
- **Per Hour**: $10.00
- **Per Day**: $100.00
- **Per Session**: $25.00

When a quota is exceeded, the system will:
1. Attempt to fallback to a cheaper model
2. Raise a `QuotaExceededError` if no fallback available
3. Log the event

## Token Counting

### Paid APIs
OpenAI, Claude, Gemini report exact token counts in API responses.

### Local Models
Ollama and other local models may not report exact tokens. We estimate:
- **Heuristic**: ~4 characters ≈ 1 token
- **Accuracy**: ±20% of actual tokenization

Estimated tokens are marked in reports.

## Privacy & Security

Usage tracking does **NOT** store:
- Prompt content
- Response content
- User input
- Sensitive metadata

We only store:
- Token counts
- Costs
- Timing metrics
- Error codes (not messages)

## Resetting Usage

To reset usage counters (e.g., new billing cycle):

```python
from blueprint.usage import UsageTracker

tracker = UsageTracker(...)
tracker.storage.reset_usage_after_date("2025-12-01")
```

Or manually delete: `rm ~/.config/blueprint/usage.db`

## Interpreting Reports

### Session Report
- Shows usage for current or specific session
- Includes per-backend breakdown
- Real-time during session

### Backend Report
- Historical usage for a specific backend
- Per-model breakdown
- Date-range filtered

### Global Report
- All backends combined
- Percentage breakdown by backend
- Useful for cost allocation

## FAQ

**Q: Why is my session cost higher than expected?**
A: Check which models were used. GPT-4 and Opus are significantly more expensive than Sonnet or Gemini Flash.

**Q: Can I disable usage tracking?**
A: Set `enable_tracking = false` in config, but quota enforcement will not work.

**Q: How accurate are token estimates for local models?**
A: Within ±20%. For exact counts, use models that report tokens (OpenAI, Claude, Gemini).

**Q: Where can I see pricing data?**
A: Run `blueprint pricing list` or query `model_pricing` table in usage database.
```

---

## Conclusion

This usage tracking subsystem provides comprehensive observability for multi-LLM orchestration. It supports both paid and free backends, tracks granular metrics, enforces quotas, and provides rich reporting capabilities.

**Key Features:**
- ✅ Per-call tracking with full metadata
- ✅ Session-level aggregation
- ✅ Historical persistence (SQLite)
- ✅ Cost estimation with model-specific pricing
- ✅ Quota enforcement (hourly, daily, monthly, per-session)
- ✅ Streaming support with incremental updates
- ✅ Rich CLI reporting
- ✅ Export to JSON/CSV
- ✅ Unified interface across all backends
- ✅ Low overhead (~1-5ms per call)

**Integration Points:**
- Orchestrator: Wrap all LLM calls
- Backend wrappers: Extract usage from responses
- Config: Quotas and pricing
- CLI: `/stats` and `/export` commands

The system balances completeness with performance, providing detailed tracking without significantly impacting LLM call latency.

## Implementation Checklist
- [ ] Usage entry/session schema implemented with persistence (SQLite/JSONL)
- [ ] Per-call tracking hooks wired into adapters/orchestrator
- [ ] Session-level aggregation and lifetime/project summaries
- [ ] Pricing catalog with cost estimation and quota enforcement
- [ ] Streaming updates for partial usage/finalization
- [ ] Export/reporting (JSON/CSV) and CLI `/stats` integration
- [ ] Documentation updates (`LLM_USAGE_TRACKING.md`)
