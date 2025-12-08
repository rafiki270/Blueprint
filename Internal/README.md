# Blueprint Implementation Guide

This directory contains phased implementation guides for Blueprint, designed to be used by Codex (GPT CLI) for automated implementation.

## Phase Overview

Each phase is a standalone markdown file with:
- Complete implementation requirements
- Code outlines and examples
- Testing checklist
- Success criteria

## Implementation Order

Follow these phases in order:

### 1. [PHASE_1_FOUNDATION.md](PHASE_1_FOUNDATION.md)
**Duration: 1-2 sessions**

Foundation layer: settings, state management, task lifecycle.

**Key deliverables:**
- Config management (`config.py`)
- State persistence (`state/persistence.py`)
- Feature management (`state/feature.py`)
- Task lifecycle (`state/tasks.py`)
- Basic CLI entry point

**Dependencies:** None

**Test before moving on:**
```bash
python -m blueprint --version
# Should output version

python -c "from blueprint.config import Config; c = Config(); print(c.settings)"
# Should load default settings
```

---

### 2. [PHASE_2_LLM_WRAPPERS.md](PHASE_2_LLM_WRAPPERS.md)
**Duration: 2-3 sessions**

LLM CLI wrappers and routing logic.

**Key deliverables:**
- Base LLM interface (`models/base.py`)
- Claude, Gemini, DeepSeek, Codex wrappers
- Model router with intelligent routing

**Dependencies:** Phase 1

**Test before moving on:**
```bash
python -c "
import asyncio
from blueprint.models import ClaudeCLI
async def test():
    claude = ClaudeCLI()
    available = await claude.check_availability()
    print(f'Claude available: {available}')
asyncio.run(test())
"
```

---

### 3. [PHASE_3_ORCHESTRATION.md](PHASE_3_ORCHESTRATION.md)
**Duration: 2-3 sessions**

Pipeline orchestration: brief → spec → tasks → execution.

**Key deliverables:**
- Pipeline (`orchestrator/pipeline.py`)
- Task executor (`orchestrator/executor.py`)
- Supervisor (`orchestrator/supervisor.py`)

**Dependencies:** Phases 1 and 2

**Test before moving on:**
```bash
# Test pipeline
python -c "
import asyncio
from blueprint.config import Config
from blueprint.state.feature import Feature
from blueprint.models.router import ModelRouter
from blueprint.orchestrator import Pipeline

async def test():
    config = Config()
    feature = Feature('test-feature')
    feature.initialize()
    router = ModelRouter(config)
    pipeline = Pipeline(feature, router)
    print('Pipeline initialized')

asyncio.run(test())
"
```

---

### 4. [PHASE_4_INTERACTIVE_MODE.md](PHASE_4_INTERACTIVE_MODE.md)
**Duration: 3-4 sessions**

Full Textual TUI with widgets and commands.

**Key deliverables:**
- All widgets (task list, output panel, context, usage modal, command bar)
- Command handlers
- Main TUI app

**Dependencies:** Phases 1, 2, and 3

**Test before moving on:**
```bash
# Test interactive mode (will require manual testing)
blueprint

# Should launch TUI without errors
```

---

### 5. [PHASE_5_STATIC_MODE.md](PHASE_5_STATIC_MODE.md)
**Duration: 1-2 sessions**

Non-interactive static mode for automation.

**Key deliverables:**
- Static runner (`static/runner.py`)
- Updated CLI commands

**Dependencies:** Phases 1, 2, and 3

**Test before moving on:**
```bash
# Create test feature first, then:
blueprint run test-feature

# Should execute tasks without errors
```

---

### 6. [PHASE_6_UTILITIES.md](PHASE_6_UTILITIES.md)
**Duration: 1 session**

Logging and usage tracking.

**Key deliverables:**
- Logger (`utils/logger.py`)
- Usage tracker (`utils/usage_tracker.py`)

**Dependencies:** Phase 1

**Test before moving on:**
```bash
python -c "
from pathlib import Path
from blueprint.utils import Logger, UsageTracker

feature_dir = Path.home() / '.blueprint' / 'test'
feature_dir.mkdir(parents=True, exist_ok=True)

logger = Logger(feature_dir)
logger.log('Test log entry')

tracker = UsageTracker(feature_dir)
tracker.record_call('claude', prompt_chars=1000)
print('Logger and tracker working')
"
```

---

### 7. [PHASE_7_DOCUMENTATION.md](PHASE_7_DOCUMENTATION.md)
**Duration: 2-3 sessions**

Comprehensive documentation.

**Key deliverables:**
- All Docs/*.md files
- Updated README.md

**Dependencies:** All previous phases

**Test before moving on:**
- Read through all documentation
- Verify code examples work
- Check all links

---

### 8. [PHASE_8_PACKAGING.md](PHASE_8_PACKAGING.md)
**Duration: 1 session**

Package for distribution.

**Key deliverables:**
- `pyproject.toml`
- `setup.py`
- Distribution files

**Dependencies:** All previous phases

**Test before moving on:**
```bash
# Build package
python -m build

# Install locally
pip install dist/*.whl

# Test
blueprint --version
```

---

## Implementation Strategy

### For Codex Implementation

Each phase file contains:
1. **Overview** - What this phase accomplishes
2. **Directory structure** - Files to create
3. **File-by-file breakdown** - Detailed implementation requirements
4. **Testing checklist** - How to verify it works
5. **Success criteria** - Definition of done

### Recommended Workflow

For each phase:

1. **Read the phase file completely**
2. **Create directory structure**
3. **Implement files in order**
4. **Test each component**
5. **Run phase checklist**
6. **Verify success criteria**
7. **Move to next phase**

### Testing Strategy

- **Unit tests**: Test individual components (optional but recommended)
- **Integration tests**: Test component interactions
- **Manual tests**: Run provided test commands
- **E2E tests**: Test full workflows after Phase 5

### Common Issues

#### Async/Await
Most model operations are async. Remember to:
```python
async def my_function():
    result = await some_async_call()
    return result

# Run with
asyncio.run(my_function())
```

#### Subprocess Management
LLM CLI wrappers use `asyncio.create_subprocess_exec`:
```python
process = await asyncio.create_subprocess_exec(
    "claude", "prompt here",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
```

#### State Persistence
Always use atomic writes:
```python
# Bad
with open(file, 'w') as f:
    json.dump(data, f)

# Good
Persistence.save_json(file, data)  # Uses temp file + rename
```

## Quick Reference

### Key Directories
```
src/blueprint/
├── __init__.py
├── __main__.py
├── cli.py                  # Entry point
├── config.py               # Settings
├── state/                  # State management
├── models/                 # LLM wrappers
├── orchestrator/           # Pipeline logic
├── interactive/            # TUI
├── static/                 # Static mode
└── utils/                  # Logger, tracker
```

### Key Classes

- `Config` - Settings management
- `Feature` - Feature state
- `TaskManager` - Task lifecycle
- `BaseLLM` - LLM interface
- `ModelRouter` - Route to models
- `Pipeline` - Brief → Spec → Tasks
- `TaskExecutor` - Execute tasks
- `Supervisor` - Review/correct
- `BlueprintApp` - TUI app
- `StaticRunner` - Static mode
- `Logger` - Logging
- `UsageTracker` - Usage stats

### Entry Points

```bash
blueprint                    # Interactive mode
blueprint run <feature>      # Static mode
python -m blueprint          # Alternative entry
```

## Progress Tracking

Mark phases as complete:

- [x] Phase 1: Foundation ✓
- [ ] Phase 2: LLM Wrappers
- [ ] Phase 3: Orchestration
- [ ] Phase 4: Interactive Mode
- [ ] Phase 5: Static Mode
- [ ] Phase 6: Utilities
- [ ] Phase 7: Documentation
- [ ] Phase 8: Packaging

## Getting Help

If you encounter issues during implementation:

1. Check the specific phase file for details
2. Review the test commands
3. Check dependencies are installed
4. Verify previous phases are complete

## Final Integration Test

After completing all phases:

```bash
# Full workflow test
blueprint                    # Create new feature
# Enter brief, let it generate spec and tasks
# Execute some tasks in interactive mode
/tasks                       # Verify tasks listed
/start                       # Execute a task
/usage                       # Check usage stats
/exit                        # Exit cleanly

# Test static mode
blueprint run <feature>      # Run all tasks

# Verify state
ls ~/.blueprint/<feature>/   # Check files created
cat ~/.blueprint/<feature>/spec.md
cat ~/.blueprint/<feature>/tasks.json
```

## Success Definition

Blueprint is complete when:

✅ All 8 phases implemented
✅ All test checklists pass
✅ Interactive mode works smoothly
✅ Static mode executes tasks
✅ Documentation is complete
✅ Package builds and installs
✅ Works on macOS, Linux, WSL
✅ No API keys required
✅ All LLM CLIs integrate correctly

---

**Remember:** These guides are designed for sequential implementation. Don't skip phases or you'll miss critical dependencies.

Good luck! 🚀
