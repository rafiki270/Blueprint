# Phase 6: Utilities & Logging

## Overview
This phase implements logging, usage tracking, and utility functions used throughout Blueprint.

## Dependencies
- Phase 1 must be complete

## Directory Structure
```
src/blueprint/utils/
├── __init__.py
├── logger.py
└── usage_tracker.py
```

## File: `src/blueprint/utils/logger.py`
**Purpose**: Structured logging to feature log files

**Requirements**:
1. Log to `~/.blueprint/<feature>/logs/`
2. Separate logs by type (errors, tasks, general)
3. Timestamp all entries
4. Support different log levels
5. Rotate logs by date
6. Provide helper methods for common log operations

**Implementation outline**:
```python
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from ..state.tasks import Task

class Logger:
    """Structured logger for Blueprint operations"""

    def __init__(self, feature_dir: Path):
        self.feature_dir = feature_dir
        self.logs_dir = feature_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Setup loggers
        self.general_logger = self._setup_logger("general", "blueprint.log")
        self.task_logger = self._setup_logger("tasks", "tasks.log")
        self.error_logger = self._setup_logger("errors", "errors.log")

    def _setup_logger(self, name: str, filename: str) -> logging.Logger:
        """Setup a logger with file handler"""
        logger = logging.getLogger(f"blueprint.{name}")
        logger.setLevel(logging.DEBUG)

        # Create file handler
        log_file = self.logs_dir / filename
        handler = logging.FileHandler(log_file, mode='a')
        handler.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def log(self, message: str, level: str = "info"):
        """Log general message"""
        log_func = getattr(self.general_logger, level.lower(), self.general_logger.info)
        log_func(message)

    def log_task_start(self, task: Task):
        """Log task start"""
        self.task_logger.info(f"Starting task: {task.id} - {task.title}")
        self.task_logger.info(f"  Type: {task.type.value}")
        self.task_logger.info(f"  Status: {task.status.value}")

    def log_task_complete(self, task: Task):
        """Log task completion"""
        self.task_logger.info(f"Completed task: {task.id} - {task.title}")

    def log_task_failed(self, task: Task, error: str):
        """Log task failure"""
        self.task_logger.error(f"Failed task: {task.id} - {task.title}")
        self.task_logger.error(f"  Error: {error}")
        self.error_logger.error(f"Task {task.id} failed: {error}")

    def log_error(self, message: str, exception: Optional[Exception] = None):
        """Log error"""
        self.error_logger.error(message)
        if exception:
            self.error_logger.exception(exception)

    def log_model_call(self, model: str, prompt_length: int):
        """Log LLM model call"""
        self.general_logger.info(f"Model call: {model} (prompt: {prompt_length} chars)")

    def log_pipeline_start(self, feature_name: str):
        """Log pipeline start"""
        self.general_logger.info("="*60)
        self.general_logger.info(f"Pipeline started for feature: {feature_name}")
        self.general_logger.info("="*60)

    def log_pipeline_complete(self, feature_name: str, tasks_created: int):
        """Log pipeline completion"""
        self.general_logger.info("="*60)
        self.general_logger.info(f"Pipeline completed for feature: {feature_name}")
        self.general_logger.info(f"Tasks created: {tasks_created}")
        self.general_logger.info("="*60)

    def get_recent_logs(self, log_type: str = "general", lines: int = 50) -> str:
        """Get recent log entries"""
        log_files = {
            "general": "blueprint.log",
            "tasks": "tasks.log",
            "errors": "errors.log"
        }

        log_file = self.logs_dir / log_files.get(log_type, "blueprint.log")
        if not log_file.exists():
            return ""

        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])

    def clear_logs(self, log_type: Optional[str] = None):
        """Clear log files"""
        if log_type:
            log_files = {
                "general": "blueprint.log",
                "tasks": "tasks.log",
                "errors": "errors.log"
            }
            log_file = self.logs_dir / log_files.get(log_type)
            if log_file.exists():
                log_file.write_text("")
        else:
            # Clear all logs
            for log_file in self.logs_dir.glob("*.log"):
                log_file.write_text("")
```

## File: `src/blueprint/utils/usage_tracker.py`
**Purpose**: Track and analyze LLM usage statistics

**Requirements**:
1. Track per-model call counts
2. Estimate token usage
3. Store timestamps
4. Calculate 7-day trends
5. Provide routing suggestions
6. Persist to `usage.json`

**Implementation outline**:
```python
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

class UsageTracker:
    """Tracks LLM usage and provides analytics"""

    def __init__(self, feature_dir: Path):
        self.feature_dir = feature_dir
        self.usage_file = feature_dir / "usage.json"
        self.usage_data = self._load()

    def _load(self) -> Dict:
        """Load usage data from file"""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self._init_usage_data()
        return self._init_usage_data()

    def _init_usage_data(self) -> Dict:
        """Initialize empty usage data structure"""
        return {
            "calls": [],  # List of {model, timestamp, prompt_chars, estimated_tokens}
            "daily_summary": {},  # {date: {model: count}}
            "models": {
                "claude": {"calls": 0, "estimated_tokens": 0},
                "gemini": {"calls": 0, "input_tokens": 0, "output_tokens": 0},
                "deepseek": {"calls": 0},
                "codex": {"calls": 0}
            }
        }

    def _save(self):
        """Save usage data to file"""
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage_file, 'w') as f:
            json.dump(self.usage_data, f, indent=2)

    def record_call(self, model: str, prompt_chars: int = 0,
                   input_tokens: int = 0, output_tokens: int = 0):
        """
        Record an LLM call

        Args:
            model: Model name (claude, gemini, deepseek, codex)
            prompt_chars: Number of characters in prompt
            input_tokens: Actual input tokens (if available)
            output_tokens: Actual output tokens (if available)
        """
        timestamp = datetime.utcnow().isoformat()
        date = timestamp.split('T')[0]

        # Estimate tokens if not provided (rough: 4 chars = 1 token)
        estimated_tokens = input_tokens or (prompt_chars // 4)

        # Record call
        call_record = {
            "model": model,
            "timestamp": timestamp,
            "prompt_chars": prompt_chars,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_tokens": estimated_tokens
        }
        self.usage_data["calls"].append(call_record)

        # Update model stats
        if model in self.usage_data["models"]:
            self.usage_data["models"][model]["calls"] += 1

            if model == "claude":
                self.usage_data["models"][model]["estimated_tokens"] += estimated_tokens
            elif model == "gemini":
                self.usage_data["models"][model]["input_tokens"] += input_tokens
                self.usage_data["models"][model]["output_tokens"] += output_tokens

        # Update daily summary
        if date not in self.usage_data["daily_summary"]:
            self.usage_data["daily_summary"][date] = {}

        if model not in self.usage_data["daily_summary"][date]:
            self.usage_data["daily_summary"][date][model] = 0

        self.usage_data["daily_summary"][date][model] += 1

        self._save()

    def get_today_usage(self) -> Dict:
        """Get today's usage statistics"""
        today = datetime.utcnow().date().isoformat()
        daily = self.usage_data["daily_summary"].get(today, {})

        # Get detailed stats for today
        today_calls = [
            c for c in self.usage_data["calls"]
            if c["timestamp"].startswith(today)
        ]

        result = {
            "claude": daily.get("claude", 0),
            "claude_tokens": sum(c.get("estimated_tokens", 0)
                                for c in today_calls if c["model"] == "claude"),
            "gemini": daily.get("gemini", 0),
            "gemini_input_tokens": sum(c.get("input_tokens", 0)
                                      for c in today_calls if c["model"] == "gemini"),
            "gemini_output_tokens": sum(c.get("output_tokens", 0)
                                       for c in today_calls if c["model"] == "gemini"),
            "deepseek": daily.get("deepseek", 0),
            "codex": daily.get("codex", 0)
        }

        return result

    def get_7day_trend(self) -> Dict:
        """Get 7-day usage trends"""
        today = datetime.utcnow().date()
        dates = [(today - timedelta(days=i)).isoformat() for i in range(7)]

        trends = {}
        for model in ["claude", "gemini", "deepseek", "codex"]:
            calls = []
            for date in reversed(dates):
                count = self.usage_data["daily_summary"].get(date, {}).get(model, 0)
                calls.append(count)

            total = sum(calls)
            # Calculate trend (comparing first half vs second half)
            first_half = sum(calls[:3])
            second_half = sum(calls[4:])

            if first_half > 0:
                trend_pct = ((second_half - first_half) / first_half) * 100
                trend_symbol = "↑" if trend_pct > 0 else "↓" if trend_pct < 0 else "→"
                trend = f"{trend_symbol} {abs(trend_pct):.0f}%"
            else:
                trend = "→"

            trends[model] = {
                "total_calls": total,
                "daily_calls": calls,
                "trend": trend
            }

        return trends

    def get_routing_suggestions(self) -> List[str]:
        """Get suggestions based on usage patterns"""
        suggestions = []
        today_usage = self.get_today_usage()

        # Heavy Gemini usage
        if today_usage["gemini"] > 20:
            suggestions.append(
                "High Gemini usage today - consider using DeepSeek for smaller tasks"
            )

        # Heavy Claude usage
        if today_usage["claude"] > 10:
            suggestions.append(
                "High Claude usage - ensure you're only using it for architecture tasks"
            )

        # No DeepSeek usage but it should be available
        if today_usage["deepseek"] == 0 and today_usage["gemini"] > 5:
            suggestions.append(
                "No local model usage - check if Ollama is running for faster code generation"
            )

        # Token estimates
        if today_usage["claude_tokens"] > 50000:
            suggestions.append(
                f"High token usage today (~{today_usage['claude_tokens']:,} tokens) - consider breaking specs into smaller features"
            )

        return suggestions

    def get_total_stats(self) -> Dict:
        """Get total all-time statistics"""
        return {
            "total_calls": len(self.usage_data["calls"]),
            "models": self.usage_data["models"],
            "days_active": len(self.usage_data["daily_summary"])
        }

    def export_csv(self, output_path: Path):
        """Export usage data to CSV"""
        import csv

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["timestamp", "model", "prompt_chars", "estimated_tokens"]
            )
            writer.writeheader()

            for call in self.usage_data["calls"]:
                writer.writerow({
                    "timestamp": call["timestamp"],
                    "model": call["model"],
                    "prompt_chars": call.get("prompt_chars", 0),
                    "estimated_tokens": call.get("estimated_tokens", 0)
                })
```

## File: `src/blueprint/utils/__init__.py`
```python
"""Utility modules"""

from .logger import Logger
from .usage_tracker import UsageTracker

__all__ = ["Logger", "UsageTracker"]
```

## Integration Example
**How to use Logger and UsageTracker:**

```python
from blueprint.utils import Logger, UsageTracker

# Setup
feature_dir = Path.home() / ".blueprint" / "my-feature"
logger = Logger(feature_dir)
usage_tracker = UsageTracker(feature_dir)

# Logging
logger.log_pipeline_start("my-feature")
logger.log_task_start(task)
logger.log_error("Something went wrong", exception)

# Usage tracking
usage_tracker.record_call("claude", prompt_chars=5000)
usage_tracker.record_call("gemini", input_tokens=1000, output_tokens=500)

today_stats = usage_tracker.get_today_usage()
trends = usage_tracker.get_7day_trend()
suggestions = usage_tracker.get_routing_suggestions()
```

## Testing Checklist
- [ ] Logger creates log files in correct directory
- [ ] Different log levels work correctly
- [ ] Task logging captures all events
- [ ] Error logging includes exception details
- [ ] Usage tracker persists data correctly
- [ ] Token estimation is reasonable
- [ ] 7-day trends calculate correctly
- [ ] Routing suggestions are helpful
- [ ] CSV export works
- [ ] Log rotation doesn't lose data

## Success Criteria
- All operations are logged appropriately
- Usage tracking provides accurate statistics
- Trends help identify patterns
- Suggestions are actionable
- Log files are organized and searchable
- Performance impact is minimal
- Data persists across sessions
