# Phase 1: Foundation & State Management

## Overview
This phase establishes the foundational infrastructure for Blueprint including settings management, state persistence, and task lifecycle management.

## Directory Structure to Create
```
src/
└── blueprint/
    ├── __init__.py
    ├── __main__.py
    ├── cli.py
    ├── config.py
    └── state/
        ├── __init__.py
        ├── feature.py
        ├── tasks.py
        └── persistence.py
```

## File: `src/blueprint/__init__.py`
**Purpose**: Package initialization, version info

```python
"""Blueprint - Multi-LLM Development Orchestrator"""

__version__ = "0.1.0"
__author__ = "Blueprint Contributors"

from .config import Config
from .state.feature import Feature
from .state.tasks import TaskManager

__all__ = ["Config", "Feature", "TaskManager"]
```

## File: `src/blueprint/__main__.py`
**Purpose**: Entry point when running `python -m blueprint`

```python
"""Entry point for Blueprint CLI"""

from .cli import main

if __name__ == "__main__":
    main()
```

## File: `src/blueprint/config.py`
**Purpose**: Settings management for ~/.blueprint/settings.json

**Requirements**:
1. Load/save settings from `~/.blueprint/settings.json`
2. Default settings if file doesn't exist
3. Settings schema:
   ```json
   {
     "local_model": "deepseek-coder:14b",
     "max_chars_local_model": 20000,
     "ollama_unavailable_warning": true,
     "cli_commands": {
       "claude": "claude",
       "gemini": "gemini",
       "ollama": "ollama",
       "codex": "codex"
     }
   }
   ```

**Implementation outline**:
```python
import json
import os
from pathlib import Path
from typing import Dict, Any

class Config:
    """Manages Blueprint settings"""

    DEFAULT_SETTINGS = {
        "local_model": "deepseek-coder:14b",
        "max_chars_local_model": 20000,
        "ollama_unavailable_warning": True,
        "cli_commands": {
            "claude": "claude",
            "gemini": "gemini",
            "ollama": "ollama",
            "codex": "codex"
        }
    }

    def __init__(self):
        self.config_dir = Path.home() / ".blueprint"
        self.config_file = self.config_dir / "settings.json"
        self.settings = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load settings from file or create defaults"""
        # Implementation here
        pass

    def save(self):
        """Save current settings to file"""
        # Implementation here
        pass

    def get(self, key: str, default=None):
        """Get a setting value"""
        # Implementation here
        pass

    def set(self, key: str, value: Any):
        """Set a setting value and save"""
        # Implementation here
        pass
```

## File: `src/blueprint/state/persistence.py`
**Purpose**: JSON file I/O with atomic writes

**Requirements**:
1. Atomic writes (write to .tmp, then rename)
2. JSON serialization/deserialization
3. Error handling for corrupted files
4. Directory creation if needed

**Implementation outline**:
```python
import json
import os
from pathlib import Path
from typing import Any, Dict
import tempfile
import shutil

class Persistence:
    """Handles atomic JSON file operations"""

    @staticmethod
    def load_json(file_path: Path) -> Dict[str, Any]:
        """Load JSON from file, return {} if not found"""
        # Implementation here
        pass

    @staticmethod
    def save_json(file_path: Path, data: Dict[str, Any]):
        """Atomically save JSON to file"""
        # Write to temp file first, then rename
        # Implementation here
        pass

    @staticmethod
    def ensure_dir(dir_path: Path):
        """Create directory if it doesn't exist"""
        # Implementation here
        pass
```

## File: `src/blueprint/state/feature.py`
**Purpose**: Feature state management

**Requirements**:
1. Create/load feature state from `~/.blueprint/<feature>/`
2. Manage feature files:
   - `spec.md`
   - `tasks.json`
   - `tasks_status.json`
   - `progress.json`
   - `usage.json`
   - `current_task.txt`
   - `logs/` directory
3. Support multiple features
4. Resume detection

**Implementation outline**:
```python
from pathlib import Path
from typing import Optional, List
from .persistence import Persistence

class Feature:
    """Manages feature state and files"""

    def __init__(self, name: str):
        self.name = name
        self.base_dir = Path.home() / ".blueprint" / name
        self.spec_file = self.base_dir / "spec.md"
        self.tasks_file = self.base_dir / "tasks.json"
        self.tasks_status_file = self.base_dir / "tasks_status.json"
        self.progress_file = self.base_dir / "progress.json"
        self.usage_file = self.base_dir / "usage.json"
        self.current_task_file = self.base_dir / "current_task.txt"
        self.logs_dir = self.base_dir / "logs"
        self.partial_dir = self.base_dir / "partial"
        self.summaries_dir = self.base_dir / "summaries"

    def initialize(self):
        """Create feature directory structure"""
        # Implementation here
        pass

    def exists(self) -> bool:
        """Check if feature exists"""
        # Implementation here
        pass

    def save_spec(self, content: str):
        """Save specification markdown"""
        # Implementation here
        pass

    def load_spec(self) -> Optional[str]:
        """Load specification markdown"""
        # Implementation here
        pass

    def save_tasks(self, tasks: List[Dict]):
        """Save tasks.json"""
        # Implementation here
        pass

    def load_tasks(self) -> List[Dict]:
        """Load tasks.json"""
        # Implementation here
        pass

    @staticmethod
    def list_features() -> List[str]:
        """List all available features"""
        # Implementation here
        pass

    @staticmethod
    def find_active_features() -> List[str]:
        """Find features with incomplete tasks"""
        # Implementation here
        pass
```

## File: `src/blueprint/state/tasks.py`
**Purpose**: Task lifecycle management (CRUD operations)

**Requirements**:
1. Task schema:
   ```json
   {
     "id": "task-1",
     "title": "Task title",
     "description": "Task description",
     "type": "code|boilerplate|review|architecture",
     "status": "pending|in-progress|blocked|completed|skipped",
     "created_at": "2025-12-08T10:00:00Z",
     "updated_at": "2025-12-08T10:00:00Z"
   }
   ```
2. CRUD operations: create, read, update, delete
3. Status transitions: mark done, redo, block
4. Filtering: get next, get missing, get by id
5. Task status persistence

**Implementation outline**:
```python
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum
from .persistence import Persistence
from pathlib import Path

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SKIPPED = "skipped"

class TaskType(Enum):
    CODE = "code"
    BOILERPLATE = "boilerplate"
    REVIEW = "review"
    ARCHITECTURE = "architecture"

class Task:
    """Represents a single task"""

    def __init__(self, id: str, title: str, description: str,
                 type: TaskType, status: TaskStatus = TaskStatus.PENDING):
        self.id = id
        self.title = title
        self.description = description
        self.type = type
        self.status = status
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        # Implementation here
        pass

    @staticmethod
    def from_dict(data: Dict) -> 'Task':
        """Create from dictionary"""
        # Implementation here
        pass

class TaskManager:
    """Manages task lifecycle"""

    def __init__(self, feature_dir: Path):
        self.feature_dir = feature_dir
        self.tasks_file = feature_dir / "tasks.json"
        self.tasks_status_file = feature_dir / "tasks_status.json"
        self.tasks: List[Task] = []
        self.load()

    def load(self):
        """Load tasks from disk"""
        # Implementation here
        pass

    def save(self):
        """Save tasks to disk"""
        # Implementation here
        pass

    def create(self, title: str, description: str, type: TaskType) -> Task:
        """Create a new task"""
        # Implementation here
        pass

    def get(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        # Implementation here
        pass

    def delete(self, task_id: str) -> bool:
        """Delete a task"""
        # Implementation here
        pass

    def mark_done(self, task_id: str) -> bool:
        """Mark task as completed"""
        # Implementation here
        pass

    def mark_redo(self, task_id: str) -> bool:
        """Mark task as pending again"""
        # Implementation here
        pass

    def mark_in_progress(self, task_id: str) -> bool:
        """Mark task as in progress"""
        # Implementation here
        pass

    def get_next(self) -> Optional[Task]:
        """Get next incomplete task"""
        # Implementation here
        pass

    def get_missing(self) -> List[Task]:
        """Get all incomplete tasks"""
        # Implementation here
        pass

    def list_all(self) -> List[Task]:
        """List all tasks"""
        # Implementation here
        pass
```

## File: `src/blueprint/state/__init__.py`
```python
"""State management modules"""

from .persistence import Persistence
from .feature import Feature
from .tasks import TaskManager, Task, TaskStatus, TaskType

__all__ = ["Persistence", "Feature", "TaskManager", "Task", "TaskStatus", "TaskType"]
```

## File: `src/blueprint/cli.py`
**Purpose**: CLI entry point (minimal for Phase 1)

**Requirements**:
1. Use Click or Typer
2. Basic commands: `blueprint`, `blueprint run <feature>`
3. Version info

**Implementation outline**:
```python
import click
from . import __version__

@click.group()
@click.version_option(version=__version__)
def main():
    """Blueprint - Multi-LLM Development Orchestrator"""
    pass

@main.command()
def interactive():
    """Start interactive mode (default)"""
    click.echo("Interactive mode - Coming in Phase 4")

@main.command()
@click.argument('feature')
def run(feature):
    """Run feature in static mode"""
    click.echo(f"Static mode for {feature} - Coming in Phase 5")

if __name__ == "__main__":
    main()
```

## Testing Checklist
- [ ] Config loads defaults on first run
- [ ] Config persists settings to ~/.blueprint/settings.json
- [ ] Persistence performs atomic writes
- [ ] Feature creates directory structure
- [ ] Feature can save/load spec.md
- [ ] TaskManager creates tasks with unique IDs
- [ ] TaskManager marks tasks as done/redo
- [ ] TaskManager filters tasks (next, missing)
- [ ] CLI entry point works (`python -m blueprint`)

## Dependencies
Add to `requirements.txt` or `pyproject.toml`:
- click >= 8.0
- python >= 3.10

## Success Criteria
- Blueprint can be imported as a Python module
- Config management works with settings.json
- Feature directories can be created and managed
- Tasks can be created, updated, and persisted
- Basic CLI responds to commands
