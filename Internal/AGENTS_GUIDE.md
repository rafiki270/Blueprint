# Blueprint Agents Implementation Guide

## Overview

This guide is for AI agents (Claude, Gemini, DeepSeek, Codex) implementing Blueprint. It describes the multi-agent approach, when to use each file, and how components fit together.

---

## 🎯 Implementation Philosophy

### The Meta-Irony
Blueprint is itself a multi-LLM orchestrator, and we're using multiple LLMs to build it. This guide explains how each LLM should approach their role in building Blueprint.

### Core Principles
1. **Check APIs Online**: Always verify latest CLI tool APIs before implementing
2. **Sequential Phases**: Implement in order - dependencies matter
3. **Test Before Proceeding**: Each phase must work before moving on
4. **Reference Design Specs**: TUI and architecture decisions are documented
5. **Follow Standards**: Use the patterns established in guides

---

## 🤖 Agent Roles in Building Blueprint

### Claude (You) - System Architect
**Role**: Planning, architecture, specification review

**Responsibilities**:
- Review phase implementations
- Ensure architectural consistency
- Validate design decisions
- Generate specifications
- Review complex async patterns

**When to engage**:
- Before starting each phase
- When design decisions arise
- After major milestones
- For troubleshooting architectural issues

**Files you reference**:
- All PHASE_*.md files
- TUI_DESIGN_SPEC.md
- ARCHITECTURE section in docs

---

### Codex (GPT) - Primary Implementation Agent
**Role**: Main coder, implements all Python code

**Responsibilities**:
- Implement each phase sequentially
- Write all Python modules
- Create tests
- Handle CLI integrations
- Write utility scripts

**Critical Requirements**:
⚠️ **ALWAYS CHECK ONLINE FOR LATEST APIs** ⚠️

Before implementing ANY integration with external CLIs:
1. Search for latest API documentation
2. Verify command syntax
3. Check for breaking changes
4. Validate subprocess patterns

**CLI Tools to Research**:
- Claude CLI: Latest command syntax and options
- Gemini CLI: Current API and streaming support
- Ollama: Model management, run commands
- Codex CLI: Your own CLI interface!
- Textual: Latest widget APIs and patterns

**Example Research Queries**:
```
"Ollama CLI commands 2025"
"Textual RichLog widget API latest"
"Claude CLI streaming output"
"Python asyncio subprocess best practices 2025"
```

**Files you implement**:
- PHASE_1_FOUNDATION.md → Phase 2
- PHASE_2_LLM_WRAPPERS.md → Phase 3
- PHASE_3_ORCHESTRATION.md → Phase 4
- PHASE_4_INTERACTIVE_MODE.md → Phase 5
- PHASE_5_STATIC_MODE.md → Done
- PHASE_6_UTILITIES.md → Support phases
- Scripts in CICD_AND_MAKEFILE.md

**When to reference design specs**:
- TUI_DESIGN_SPEC.md → During Phase 4
- CICD_AND_MAKEFILE.md → After Phase 5

---

### Gemini - Documentation and Boilerplate
**Role**: Documentation writer, boilerplate generator

**Responsibilities**:
- Write all Docs/*.md files (Phase 7)
- Generate boilerplate code structures
- Create examples and tutorials
- Write comments and docstrings

**Files you implement**:
- PHASE_7_DOCUMENTATION.md → All Docs/ files
- README.md updates
- Code comments and docstrings

**When to engage**:
- After Phase 5 completion (core features done)
- For generating example workflows
- Creating user guides

---

### DeepSeek - Testing and Refinement
**Role**: Test writer, code reviewer, refactorer

**Responsibilities**:
- Write unit tests
- Write integration tests
- Refactor code for clarity
- Optimize performance

**Files you reference**:
- All implemented Python code
- Testing checklists in each PHASE_*.md

**When to engage**:
- After each phase implementation
- For test coverage
- Code quality improvements

---

## 📁 File Reference Guide

### Implementation Files (Use in Order)

#### 1. README.md
**When**: First thing to read
**Purpose**: Implementation overview
**Use**: Understand workflow, track progress
**Next**: PHASE_1_FOUNDATION.md

#### 2. PHASE_1_FOUNDATION.md
**When**: First implementation phase
**Purpose**: Core infrastructure
**Creates**:
- `src/blueprint/config.py`
- `src/blueprint/state/*.py`
- `src/blueprint/cli.py`
**Next**: PHASE_2_LLM_WRAPPERS.md

#### 3. PHASE_2_LLM_WRAPPERS.md
**When**: After Phase 1 complete
**Purpose**: LLM CLI integrations
**Creates**:
- `src/blueprint/models/base.py`
- `src/blueprint/models/claude.py`
- `src/blueprint/models/gemini.py`
- `src/blueprint/models/deepseek.py`
- `src/blueprint/models/codex.py`
- `src/blueprint/models/router.py`

**⚠️ CRITICAL**: Research CLI APIs online before implementing!

**Online research required**:
```bash
# For Claude CLI
Search: "Claude CLI documentation 2025"
Verify: Command syntax, streaming, error handling

# For Gemini CLI
Search: "Google Gemini CLI API latest"
Verify: Authentication, rate limits, models

# For Ollama
Search: "Ollama CLI commands 2025"
Verify: Model management, run syntax, streaming

# For Codex
Search: "OpenAI Codex CLI 2025"
Verify: Available endpoints, pricing
```

**Next**: PHASE_3_ORCHESTRATION.md

#### 4. PHASE_3_ORCHESTRATION.md
**When**: After Phase 2 complete
**Purpose**: Pipeline logic
**Creates**:
- `src/blueprint/orchestrator/pipeline.py`
- `src/blueprint/orchestrator/executor.py`
- `src/blueprint/orchestrator/supervisor.py`
**Dependencies**: Uses models from Phase 2, state from Phase 1
**Next**: PHASE_4_INTERACTIVE_MODE.md

#### 5. PHASE_4_INTERACTIVE_MODE.md
**When**: After Phase 3 complete
**Purpose**: TUI implementation
**Creates**:
- `src/blueprint/interactive/app.py`
- `src/blueprint/interactive/widgets/*.py`
- `src/blueprint/interactive/commands.py`

**⚠️ MUST REFERENCE**: TUI_DESIGN_SPEC.md

**Design spec tells you**:
- Exact layout (3x3 grid)
- Panel dimensions and positions
- Colors and themes
- Status symbols (○ ◐ ● ⚠)
- Keyboard shortcuts
- Modal designs
- Animation timing

**Textual API research**:
```bash
Search: "Textual Python TUI latest API 2025"
Verify: Widget APIs, layout system, reactive properties
Check: RichLog, ListView, Markdown widgets
```

**Next**: PHASE_5_STATIC_MODE.md

#### 6. PHASE_5_STATIC_MODE.md
**When**: After Phase 4 complete
**Purpose**: Non-interactive runner
**Creates**: `src/blueprint/static/runner.py`
**Dependencies**: Uses executor from Phase 3
**Next**: PHASE_6_UTILITIES.md (can be parallel)

#### 7. PHASE_6_UTILITIES.md
**When**: Can implement anytime after Phase 1
**Purpose**: Logging and tracking
**Creates**:
- `src/blueprint/utils/logger.py`
- `src/blueprint/utils/usage_tracker.py`
**Used by**: All other phases
**Note**: Can implement in parallel with other phases

#### 8. PHASE_7_DOCUMENTATION.md
**When**: After Phase 5 complete (core done)
**Purpose**: User documentation
**Creates**: All `Docs/*.md` files, updates `README.md`
**Agent**: Primarily Gemini
**Next**: PHASE_8_PACKAGING.md

#### 9. PHASE_8_PACKAGING.md
**When**: After all phases complete
**Purpose**: Distribution setup
**Creates**:
- `pyproject.toml`
- `setup.py`
- `MANIFEST.in`
**Next**: CICD_AND_MAKEFILE.md

---

### Design & Reference Files (Consult During Implementation)

#### TUI_DESIGN_SPEC.md
**When to use**: During Phase 4 implementation
**Purpose**: Complete TUI design specification

**What it tells you**:
- **Layout**: Exact 3x3 grid structure
- **Panels**: Size, position, content of each panel
- **Colors**: Entire color palette
- **Symbols**: Status indicators (○ ◐ ● ⚠ ⊘)
- **Interactions**: Keyboard shortcuts, commands
- **Modals**: Usage dashboard, help, confirmations
- **Animations**: Spinner, progress, transitions
- **Edge cases**: Error states, empty states

**How to use it**:
1. Read "Layout Structure" section for overall design
2. Read each "Panel Details" section before implementing that widget
3. Copy color codes from "Color Palette" section
4. Reference "Keyboard Shortcuts" when implementing command handlers
5. Use "Modal Overlays" section for popup designs

**Example usage**:
```python
# When implementing TaskListWidget, reference:
# - Section: "2. Task List Panel"
# - Get status symbols: ○ ◐ ● ⚠ ⊘
# - Get colors: pending=gray, in-progress=yellow, etc.
# - Get format: [symbol] [task-id] Title

# When implementing OutputPanel, reference:
# - Section: "3. Output Stream Panel"
# - Get timestamp format: [HH:MM:SS]
# - Get status indicators: ✓ ✗ ⚠ ℹ
# - Get syntax highlighting theme: monokai
```

---

#### CICD_AND_MAKEFILE.md
**When to use**: After Phase 8 (packaging) complete
**Purpose**: CI/CD and automation setup

**What it tells you**:
- **Makefile**: All development commands
- **GitHub Actions**: CI and release workflows
- **Homebrew**: Tap setup and formula generation
- **Scripts**: Version bumping, formula generation

**What to implement**:
1. **Makefile** → Project root
2. **`.github/workflows/ci.yml`** → CI workflow
3. **`.github/workflows/release.yml`** → Release workflow
4. **`scripts/generate_formula.py`** → Homebrew formula generator
5. **`scripts/bump_version.py`** → Version management

**When each file is used**:
- **Makefile**: Every development session
- **CI workflow**: Every PR and push to main
- **Release workflow**: When GitHub release created
- **Scripts**: During release preparation

**Dependencies**:
- Requires Phase 8 (pyproject.toml) complete
- Needs working package build

---

## 🔄 Implementation Workflow

### Phase-by-Phase Approach

```
Start
  ↓
┌─────────────────────────────┐
│ 1. Read README.md           │
│    Understand overall flow  │
└─────────────────────────────┘
  ↓
┌─────────────────────────────┐
│ 2. Phase 1: Foundation      │
│    - Implement all files    │
│    - Test: config, state    │
│    - Verify persistence     │
└─────────────────────────────┘
  ↓
┌─────────────────────────────┐
│ 3. Phase 2: LLM Wrappers    │
│    ⚠️ RESEARCH APIs ONLINE  │
│    - Claude CLI             │
│    - Gemini CLI             │
│    - Ollama commands        │
│    - Codex CLI              │
│    - Test: subprocess calls │
└─────────────────────────────┘
  ↓
┌─────────────────────────────┐
│ 4. Phase 3: Orchestration   │
│    - Implement pipeline     │
│    - Test: brief→spec→tasks │
│    - Verify task execution  │
└─────────────────────────────┘
  ↓
┌─────────────────────────────┐
│ 5. Phase 4: Interactive TUI │
│    📋 REFERENCE:            │
│       TUI_DESIGN_SPEC.md    │
│    - Layout (3x3 grid)      │
│    - All widgets            │
│    - Commands               │
│    - Test: manual TUI       │
└─────────────────────────────┘
  ↓
┌─────────────────────────────┐
│ 6. Phase 5: Static Mode     │
│    - Implement runner       │
│    - Test: automated exec   │
└─────────────────────────────┘
  ↓
┌─────────────────────────────┐
│ 7. Phase 6: Utilities       │
│    (Can do earlier)         │
│    - Logger                 │
│    - Usage tracker          │
└─────────────────────────────┘
  ↓
┌─────────────────────────────┐
│ 8. Phase 7: Documentation   │
│    Agent: Gemini            │
│    - All Docs/*.md          │
│    - README.md              │
└─────────────────────────────┘
  ↓
┌─────────────────────────────┐
│ 9. Phase 8: Packaging       │
│    - pyproject.toml         │
│    - setup.py               │
│    - Test: build, install   │
└─────────────────────────────┘
  ↓
┌─────────────────────────────┐
│ 10. CI/CD Setup             │
│     📋 REFERENCE:           │
│        CICD_AND_MAKEFILE.md │
│     - Makefile              │
│     - GitHub Actions        │
│     - Scripts               │
└─────────────────────────────┘
  ↓
Done ✓
```

---

## 🔍 When to Research Online

### Critical Research Points

#### Phase 2 - LLM Wrappers (MOST IMPORTANT)

**Claude CLI**:
```bash
# Research before implementing:
1. Latest installation method
2. Command syntax: `claude "prompt"` or `claude --prompt "..."`?
3. Streaming support
4. Environment variables needed
5. Authentication flow
6. Error handling patterns

Search queries:
- "Claude CLI documentation 2025"
- "Anthropic Claude CLI streaming"
- "Claude CLI subprocess Python"
```

**Gemini CLI**:
```bash
# Research before implementing:
1. Official package name
2. Authentication setup
3. Command syntax
4. Model names (gemini-pro, gemini-ultra?)
5. Streaming API
6. Rate limits

Search queries:
- "Google Gemini CLI 2025"
- "Gemini Python CLI streaming"
- "Google AI CLI authentication"
```

**Ollama**:
```bash
# Research before implementing:
1. Command: `ollama run <model>` syntax
2. Model naming: deepseek-coder:14b, deepseek-coder:33b?
3. List models: `ollama list`
4. Pull models: `ollama pull <model>`
5. Streaming output format
6. Process management

Search queries:
- "Ollama CLI commands 2025"
- "Ollama Python subprocess streaming"
- "Ollama model management"
```

**Codex CLI**:
```bash
# Research before implementing:
1. Does official CLI exist? (May need to verify)
2. Alternative: OpenAI API with CLI wrapper
3. Command syntax
4. Authentication
5. Model access

Search queries:
- "OpenAI Codex CLI 2025"
- "GPT-4 CLI tool"
- "OpenAI Python CLI"
```

#### Phase 4 - Interactive Mode

**Textual Framework**:
```bash
# Research before implementing:
1. Latest version (0.47.x, 0.48.x?)
2. Widget API changes
3. Reactive system
4. Layout patterns
5. Async support

Search queries:
- "Textual Python TUI 2025 documentation"
- "Textual RichLog API"
- "Textual grid layout latest"
- "Textual reactive properties tutorial"
```

#### Phase 8 - Packaging

**Python Packaging**:
```bash
# Verify before implementing:
1. pyproject.toml standards (PEP 621)
2. setuptools vs poetry vs hatch
3. Entry points syntax
4. Dependencies specification

Search queries:
- "Python packaging best practices 2025"
- "pyproject.toml entry points"
```

---

## 📊 File Dependency Graph

```
AGENTS_GUIDE.md (this file)
        ↓
    README.md ← Start here
        ↓
┌───────────────────────────────────────────────┐
│                 PHASE 1                       │
│              Foundation                       │
│    config.py, state/*.py, cli.py              │
└───────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────┐
│                 PHASE 2                       │
│              LLM Wrappers                     │
│    models/*.py                                │
│    ⚠️ RESEARCH APIs ONLINE                    │
└───────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────┐
│                 PHASE 3                       │
│             Orchestration                     │
│    orchestrator/*.py                          │
│    Depends on: Phase 1 + Phase 2              │
└───────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────┐
│                 PHASE 4                       │
│            Interactive Mode                   │
│    interactive/*.py                           │
│    📋 Reference: TUI_DESIGN_SPEC.md           │
│    ⚠️ Research: Textual API                   │
│    Depends on: Phase 1 + Phase 2 + Phase 3   │
└───────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────┐
│                 PHASE 5                       │
│              Static Mode                      │
│    static/runner.py                           │
│    Depends on: Phase 1 + Phase 2 + Phase 3   │
└───────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────┐
│                 PHASE 6                       │
│               Utilities                       │
│    utils/*.py                                 │
│    Can implement anytime after Phase 1        │
└───────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────┐
│                 PHASE 7                       │
│             Documentation                     │
│    Docs/*.md, README.md                       │
│    Agent: Gemini                              │
│    Depends on: All phases 1-6 complete        │
└───────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────┐
│                 PHASE 8                       │
│               Packaging                       │
│    pyproject.toml, setup.py                   │
│    Depends on: All phases complete            │
└───────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────┐
│              CI/CD Setup                      │
│    📋 Reference: CICD_AND_MAKEFILE.md         │
│    Makefile, .github/workflows/*.yml          │
│    Depends on: Phase 8 complete               │
└───────────────────────────────────────────────┘
```

---

## 🎨 How Design Files Fit In

### TUI_DESIGN_SPEC.md

**Used during**: Phase 4 implementation

**What it provides**:
- Complete visual design
- Exact measurements
- Color values
- Symbol definitions
- Interaction patterns

**How to use it**:

```python
# Example: Implementing TaskListWidget

# Step 1: Read section "2. Task List Panel"
# Step 2: Note the status symbols
STATUS_SYMBOLS = {
    "pending": "○",      # From design spec
    "in-progress": "◐",  # From design spec
    "completed": "●",    # From design spec
    "blocked": "⚠",      # From design spec
    "skipped": "⊘"       # From design spec
}

# Step 3: Note the colors
STATUS_COLORS = {
    "pending": "gray",        # From design spec
    "in-progress": "yellow",  # From design spec
    "completed": "green",     # From design spec
    "blocked": "red",         # From design spec
    "skipped": "dim"          # From design spec
}

# Step 4: Implement according to design
class TaskListWidget(Widget):
    def render_task(self, task):
        symbol = STATUS_SYMBOLS[task.status]
        color = STATUS_COLORS[task.status]
        # ... implementation follows design spec
```

**Don't deviate from design spec without reason!**

---

### CICD_AND_MAKEFILE.md

**Used during**: Post-implementation (after Phase 8)

**What it provides**:
- Complete Makefile
- GitHub Actions workflows
- Homebrew formula generation
- Release automation

**Implementation order**:

1. **First: Makefile**
   ```bash
   # Copy from CICD_AND_MAKEFILE.md to project root
   # Test each target works
   make dev
   make test
   make build
   ```

2. **Second: Scripts**
   ```bash
   # Create scripts/ directory
   # Implement scripts/generate_formula.py
   # Implement scripts/bump_version.py
   # Make executable
   chmod +x scripts/*.py
   ```

3. **Third: GitHub Actions**
   ```bash
   # Create .github/workflows/
   # Implement ci.yml
   # Implement release.yml
   # Test with PR
   ```

4. **Fourth: Homebrew Tap**
   ```bash
   # Create separate repo: homebrew-blueprint
   # Generate initial formula
   make brew-formula
   # Test locally
   brew install --build-from-source Formula/blueprint.rb
   ```

**When workflows run**:
- **ci.yml**: Every push, every PR
- **release.yml**: Only when GitHub release created

---

## ⚠️ Critical Reminders

### For Codex (Primary Implementer)

1. **Always Research CLIs Online**
   - Don't assume API syntax
   - Check for latest versions
   - Verify command patterns
   - Test subprocess calls

2. **Follow Phase Order**
   - Don't skip ahead
   - Test before proceeding
   - Each phase builds on previous

3. **Reference Design Specs**
   - TUI_DESIGN_SPEC.md for Phase 4
   - Don't guess layouts or colors
   - Use exact specifications

4. **Check Testing Checklists**
   - Every phase has testing checklist
   - Run tests before next phase
   - Verify success criteria

5. **Use Async Properly**
   - All LLM calls are async
   - Use `asyncio.create_subprocess_exec`
   - Stream output properly
   - Handle process cleanup

### For All Agents

1. **This is Meta-Work**
   - You're building a multi-LLM orchestrator
   - The system you build will coordinate LLMs
   - Think about how YOU would want to be orchestrated

2. **Test Thoroughly**
   - Each component must work
   - Integration matters
   - User experience is critical

3. **Document as You Go**
   - Clear code comments
   - Helpful error messages
   - Actionable suggestions

---

## 📝 Quick Reference Checklist

### Before Starting Implementation

- [ ] Read this file (AGENTS_GUIDE.md)
- [ ] Read README.md
- [ ] Understand phase order
- [ ] Know when to research online
- [ ] Know which design specs to reference

### During Phase Implementation

- [ ] Read relevant PHASE_*.md completely
- [ ] Research CLI APIs online (Phase 2)
- [ ] Reference TUI_DESIGN_SPEC.md (Phase 4)
- [ ] Implement files in order
- [ ] Run tests from checklist
- [ ] Verify success criteria

### After Implementation Complete

- [ ] All phases 1-8 done
- [ ] Read CICD_AND_MAKEFILE.md
- [ ] Implement Makefile
- [ ] Implement GitHub Actions
- [ ] Setup Homebrew tap
- [ ] Test full release workflow

---

## 🚀 Success Criteria

You'll know Blueprint is complete when:

✅ Can install via: `pip install blueprint-cli`
✅ Can install via: `brew install blueprint`
✅ Interactive mode launches smoothly
✅ All LLM CLIs integrate correctly
✅ Tasks execute and stream output
✅ TUI looks exactly like design spec
✅ Static mode runs automatically
✅ Documentation is comprehensive
✅ CI/CD automates releases
✅ Makefile provides all commands

---

## 🆘 Troubleshooting

### "I don't know the CLI syntax for X"
→ **Research online first!** Don't guess.

### "The design spec conflicts with Phase file"
→ **Design spec wins for TUI.** It's more detailed.

### "Phase X depends on something not implemented"
→ **Check implementation order.** Phases build on each other.

### "Tests failing in Phase X"
→ **Don't proceed.** Fix current phase first.

### "Homebrew formula not working"
→ **Check CICD_AND_MAKEFILE.md.** Follow formula generation exactly.

---

## 🎯 Final Notes

### This is a Complex Project
- 8 phases + CI/CD setup
- Multiple external CLI integrations
- Rich TUI with real-time streaming
- Multi-agent coordination

### Take Your Time
- Each phase matters
- Test thoroughly
- Research when needed
- Reference design specs

### You're Building Something Cool
Blueprint will orchestrate multiple LLMs to automate software development. Make it robust, make it usable, make it awesome.

**Now go build it!** 🚀

Start with Phase 1, research APIs before Phase 2, reference TUI design in Phase 4, and you'll have a working multi-LLM orchestrator by the end.

Good luck! 🎉
