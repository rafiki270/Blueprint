# Phase 7: Documentation

## Overview
This phase creates comprehensive documentation for Blueprint users and contributors.

## Dependencies
- All previous phases should be mostly complete

## Documentation Structure
```
Docs/
├── GETTING_STARTED.md
├── INSTALLATION.md
├── USAGE.md
├── INTERACTIVE_MODE.md
├── TASKS.md
├── MODELS.md
├── ROUTING.md
├── STATE.md
├── TROUBLESHOOTING.md
├── EXTENDING.md
└── ARCHITECTURE.md

README.md (updated)
```

## File: `Docs/GETTING_STARTED.md`
**Purpose**: Quick introduction for new users

**Content outline**:
```markdown
# Getting Started with Blueprint

## What is Blueprint?

Blueprint is a CLI-only multi-LLM development orchestrator that coordinates Claude, Gemini, DeepSeek (via Ollama), and GPT (via Codex CLI) to automate software development workflows.

## Quick Start

1. Install Blueprint
2. Ensure LLM CLIs are installed (claude, gemini, ollama, codex)
3. Create your first feature:
   ```bash
   blueprint
   ```
4. Provide a feature brief when prompted
5. Blueprint will generate a spec and tasks automatically
6. Start interactive mode to execute tasks

## First Feature Example

Create a simple authentication feature:

```bash
$ blueprint
Creating new feature...
Feature name: user-auth
Paste your brief (Ctrl+D when done):
Add user authentication with login, logout, and session management.
^D
```

Blueprint will:
1. Generate technical specification using Claude
2. Convert spec to structured tasks
3. Launch interactive mode for task execution

## Next Steps

- Read [Interactive Mode](INTERACTIVE_MODE.md) to learn all commands
- See [Models](MODELS.md) to understand model roles
- Check [Tasks](TASKS.md) for task management
```

## File: `Docs/INSTALLATION.md`
**Purpose**: Installation instructions for all platforms

**Content outline**:
```markdown
# Installation

## Requirements

- Python 3.10 or higher
- One or more of the following LLM CLIs:
  - Claude CLI
  - Gemini CLI
  - Ollama (for DeepSeek)
  - Codex CLI

## Installation Methods

### Via pip (Recommended)

```bash
pip install blueprint-cli
```

### From Source

```bash
git clone https://github.com/your-org/blueprint.git
cd blueprint
pip install -e .
```

## Installing LLM CLIs

### Claude CLI
```bash
# Installation instructions for Claude CLI
npm install -g @anthropic-ai/claude-cli
```

### Gemini CLI
```bash
# Installation instructions for Gemini CLI
pip install google-generativeai-cli
```

### Ollama (DeepSeek)
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Pull DeepSeek model
ollama pull deepseek-coder:14b
```

### Codex CLI
```bash
# Installation instructions for Codex CLI
pip install codex-cli
```

## Verification

Verify Blueprint is installed:

```bash
blueprint --version
```

Check which LLM CLIs are available:

```bash
which claude
which gemini
which ollama
which codex
```

## Configuration

Blueprint stores configuration in `~/.blueprint/settings.json`.

Edit settings:

```bash
# Open in editor
$EDITOR ~/.blueprint/settings.json
```

Default settings:
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

## Platform-Specific Notes

### macOS
No additional configuration needed.

### Linux
Ensure Python bin directory is in PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Windows (WSL)
Blueprint works in WSL2. Install all CLIs in WSL environment.

## Troubleshooting

See [Troubleshooting](TROUBLESHOOTING.md) for common issues.
```

## File: `Docs/USAGE.md`
**Purpose**: Complete command reference

**Content outline**:
```markdown
# Usage Guide

## Commands

### Interactive Mode (Default)

```bash
blueprint
```

Starts interactive mode. If features exist, offers to resume.

### Static Mode

```bash
blueprint run <feature>
```

Executes all incomplete tasks automatically.

```bash
blueprint run <feature> --task <task-id>
```

Executes a specific task.

### Feature Management

List all features:
```bash
blueprint list
```

Delete a feature:
```bash
blueprint delete <feature>
```

Show feature status:
```bash
blueprint status <feature>
```

## Interactive Commands

Once in interactive mode, use these commands:

### Task Management
- `/tasks` - List all tasks
- `/done <id>` - Mark task completed
- `/delete <id>` - Delete task
- `/redo <id>` - Mark task incomplete
- `/missing` - Show incomplete tasks
- `/next` - Move to next task
- `/task <id>` - Jump to task

### Execution Control
- `/start` - Start next task
- `/stop` - Stop current task (Ctrl+S)
- `/correct` - Enter correction mode
- `/resume` - Resume current task

### Configuration
- `/switch-model` - Change local coder
- `/usage` - Show usage dashboard (Ctrl+U)
- `/spec` - View specification
- `/logs` - View logs

### Other
- `/help` - Show help (F1)
- `/exit` - Exit Blueprint (Ctrl+C)

## Workflow Examples

### Creating a New Feature

```bash
$ blueprint
Feature name: api-endpoints
Paste brief:
Add REST API endpoints for CRUD operations on users
^D

Generating specification...
[Claude output...]

Converting to tasks...
[Tasks created...]

Interactive mode started.
blueprint> /tasks
```

### Resuming Existing Feature

```bash
$ blueprint
Found active features:
1. api-endpoints (5 tasks remaining)
2. ui-redesign (12 tasks remaining)

Select feature [1]: 1

Resuming: api-endpoints
blueprint> /missing
```

### Running Static Mode

```bash
$ blueprint run api-endpoints
[Execution output...]
Summary:
  Total: 10
  Completed: 8
  Failed: 2
```

## Tips

1. **Use static mode for automation**: Perfect for CI/CD
2. **Review specs before execution**: Use `/spec` command
3. **Monitor usage**: Check `/usage` regularly
4. **Save output**: Logs are in `~/.blueprint/<feature>/logs/`
```

## File: `Docs/INTERACTIVE_MODE.md`
**Purpose**: Deep dive into interactive mode features

(Include detailed explanation of TUI, keybindings, panels, streaming, etc.)

## File: `Docs/TASKS.md`
**Purpose**: Task management in depth

**Content outline**:
```markdown
# Task Management

## Task Structure

Each task has:
- **ID**: Unique identifier (e.g., `task-1`)
- **Title**: Brief description
- **Description**: Detailed requirements
- **Type**: code, boilerplate, review, architecture
- **Status**: pending, in-progress, blocked, completed, skipped

## Task Lifecycle

```
pending → in-progress → completed
                ↓
              blocked
```

## Task Types

### Architecture
- Handled by Claude
- Design decisions
- Technical planning
- No code generation

### Boilerplate
- Handled by Gemini
- Large code scaffolds
- DTOs, models, configs
- Template generation

### Code
- Handled by DeepSeek or Gemini
- Core implementation
- Business logic
- Refactoring

### Review
- Handled by Codex
- Code review
- Test analysis
- Quality checks

## Managing Tasks

### Creating Tasks
Tasks are created automatically from spec, but you can add manually:
```bash
blueprint> /add "Implement user login" --type code
```

### Marking Complete
```bash
blueprint> /done task-3
```

### Deleting Tasks
```bash
blueprint> /delete task-5
```

### Redo Tasks
```bash
blueprint> /redo task-2
```

## Task Persistence

Tasks are stored in:
```
~/.blueprint/<feature>/
  ├── tasks.json          # Task definitions
  └── tasks_status.json   # Current status
```

Format:
```json
{
  "id": "task-1",
  "title": "Implement authentication",
  "description": "Add JWT-based authentication...",
  "type": "code",
  "status": "pending",
  "created_at": "2025-12-08T10:00:00Z",
  "updated_at": "2025-12-08T10:00:00Z"
}
```
```

## File: `Docs/MODELS.md`
**Purpose**: Explain model roles and capabilities

(Include model routing logic, roles, when each is used, etc.)

## File: `Docs/ROUTING.md`
**Purpose**: Deep dive into routing logic

(Explain size-based routing, role-based routing, fallbacks, etc.)

## File: `Docs/STATE.md`
**Purpose**: Explain state management and file structure

**Content outline**:
```markdown
# State Management

## State Directory

All Blueprint state lives in:
```
~/.blueprint/
  └── <feature>/
      ├── spec.md
      ├── tasks.json
      ├── tasks_status.json
      ├── progress.json
      ├── usage.json
      ├── current_task.txt
      ├── settings.json
      ├── logs/
      │   ├── blueprint.log
      │   ├── tasks.log
      │   └── errors.log
      ├── partial/
      │   ├── task-1_code.py
      │   ├── task-2_boilerplate.py
      │   └── ...
      └── summaries/
```

## File Purposes

### spec.md
Technical specification in Markdown format.

### tasks.json
Complete task definitions with descriptions.

### tasks_status.json
Current status of each task (pending/completed/etc.).

### progress.json
Overall progress metrics.

### usage.json
LLM usage tracking data.

### current_task.txt
ID of currently executing task (for resume).

### logs/
All execution logs organized by type.

### partial/
Generated code and outputs from tasks.

### summaries/
Summaries and reviews from supervision.

## Persistence Strategy

- **Atomic writes**: All JSON writes use temp files + rename
- **Lock files**: Prevent concurrent modifications
- **Auto-recovery**: Corrupted files fallback to defaults

## Manual Inspection

All files are human-readable:
```bash
# View spec
cat ~/.blueprint/my-feature/spec.md

# View tasks
cat ~/.blueprint/my-feature/tasks.json

# View logs
tail -f ~/.blueprint/my-feature/logs/blueprint.log
```

## Backup and Recovery

Backup a feature:
```bash
tar -czf my-feature-backup.tar.gz ~/.blueprint/my-feature/
```

Restore:
```bash
tar -xzf my-feature-backup.tar.gz -C ~/
```
```

## File: `Docs/TROUBLESHOOTING.md`
**Purpose**: Common issues and solutions

(Include Ollama issues, CLI not found, permission errors, etc.)

## File: `Docs/EXTENDING.md`
**Purpose**: Guide for adding new models/features

(Explain how to add new LLM wrappers, extend routing, etc.)

## File: `Docs/ARCHITECTURE.md`
**Purpose**: Deep technical architecture for contributors

**Content outline**:
```markdown
# Architecture

## System Overview

Blueprint is organized into several layers:

```
┌─────────────────────────────────────────┐
│         CLI / Interactive TUI           │
├─────────────────────────────────────────┤
│      Orchestration Pipeline             │
│  (Pipeline, Executor, Supervisor)       │
├─────────────────────────────────────────┤
│         Model Router                    │
├─────────────────────────────────────────┤
│    LLM CLI Wrappers (Async)             │
│  (Claude, Gemini, DeepSeek, Codex)      │
├─────────────────────────────────────────┤
│    State Management & Persistence       │
└─────────────────────────────────────────┘
```

## Component Details

### State Layer
- Feature management
- Task lifecycle
- JSON persistence
- Atomic writes

### Models Layer
- Base LLM interface
- CLI wrappers for each model
- Async subprocess management
- Error handling and retries

### Orchestration Layer
- Pipeline: Brief → Spec → Tasks
- Executor: Task execution with routing
- Supervisor: Code review and correction

### Interface Layer
- CLI: Click-based commands
- TUI: Textual widgets and app
- Commands: Interactive command handlers

## Async Architecture

Blueprint uses asyncio throughout:
- Non-blocking LLM CLI calls
- Concurrent task execution
- Real-time streaming output

## Extension Points

To add a new LLM:
1. Create wrapper in `models/<name>.py`
2. Extend `BaseLLM`
3. Add to router
4. Update config

## Testing Strategy

- Unit tests: State, models, utils
- Integration tests: Pipeline, executor
- E2E tests: Full workflows
- Manual: TUI functionality
```

## File: `README.md` (Update)
**Purpose**: Project overview and quickstart

**Content outline**:
```markdown
# Blueprint

Multi-LLM Development Orchestrator

## What is Blueprint?

Blueprint is a CLI-only tool that orchestrates multiple AI models to automate software development workflows. It coordinates Claude, Gemini, DeepSeek (via Ollama), and GPT (via Codex CLI) to handle different aspects of feature development.

## Why Blueprint?

- **No API Keys Required**: Uses local CLI tools, not cloud APIs
- **Model Specialization**: Right model for each task
- **Interactive or Automated**: Choose your workflow
- **Full Control**: Stop, correct, resume anytime
- **Cost Conscious**: Uses local models when possible

## Quick Start

```bash
# Install
pip install blueprint-cli

# Create feature
blueprint

# Run static mode
blueprint run <feature>
```

## Supported Model CLIs

- **Claude CLI**: Architecture and specs
- **Gemini CLI**: Large docs, boilerplate
- **Ollama**: Local code generation (DeepSeek)
- **Codex CLI**: Code review, supervision

## Features

- ✅ Multi-LLM orchestration
- ✅ Interactive TUI with live streaming
- ✅ Task management (create, complete, delete)
- ✅ Intelligent model routing
- ✅ Usage tracking and analytics
- ✅ Resume from interruption
- ✅ Static mode for automation
- ✅ Comprehensive logging

## Documentation

- [Getting Started](Docs/GETTING_STARTED.md)
- [Installation](Docs/INSTALLATION.md)
- [Usage Guide](Docs/USAGE.md)
- [Interactive Mode](Docs/INTERACTIVE_MODE.md)
- [Task Management](Docs/TASKS.md)
- [Architecture](Docs/ARCHITECTURE.md)

## Requirements

- Python 3.10+
- At least one of: claude, gemini, ollama, codex CLIs

## License

MIT License - see [LICENSE](LICENSE)

## Contributing

See [EXTENDING.md](Docs/EXTENDING.md) for contribution guidelines.
```

## Testing Checklist
- [ ] All documentation files are complete
- [ ] Code examples are tested and accurate
- [ ] Links between docs work correctly
- [ ] README is concise and clear
- [ ] Installation instructions work on all platforms
- [ ] Troubleshooting covers common issues
- [ ] Architecture doc is technically accurate

## Success Criteria
- New users can get started in < 5 minutes
- All features are documented
- Examples are practical and working
- Technical details are accurate
- Documentation is well-organized
- Cross-references work correctly
