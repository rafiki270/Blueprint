# Blueprint

Developer-focused LLM orchestration toolkit with both interactive (TUI) and static automation modes. The aim: make "vibe coding" cost-efficient by routing work across multiple models—e.g., replace an expensive £200/mo GPT Pro with a stack of cheaper specialists (Claude for architecture/planning, GPT for organizing/verification, local DeepSeek for bulk coding, Gemini as a fallback when DeepSeek is too small or low-quality). You get a repeatable path from brief → spec → tasks → execution with routing, logging, and packaging baked in.

## What we're building
- CLI-first workflow with a full-screen TUI and a headless/static runner.
- Pluggable LLM wrappers (Claude, Gemini, DeepSeek, Codex) behind a router.
- Persistent feature state (briefs, specs, tasks) stored on disk.
- Usage tracking and logging designed for auditable runs.

## Current status
- Phase 1 (Foundation) is complete. Subsequent phases (LLM wrappers, orchestration, TUI, static mode, utilities, docs, packaging) are outlined and in progress.
- All phase-by-phase requirements and specs live in `Internal/`. Start with `Internal/AGENTS_GUIDE.md` for a quick orientation.

## Getting started (developers)
1. Clone this repo and create a Python 3.9+ virtual environment.
2. Install tooling dependencies you prefer for linting/formatting (none are enforced yet).
3. Follow the phased guides in `Internal/` to implement remaining components. Each phase file lists deliverables, test commands, and success criteria.

## Installation & CLI (planned)
Once the package is wired up (Phase 8), installation will look like:
```bash
pip install blueprint
blueprint --version
```
During development you can install locally:
```bash
pip install -e .
blueprint --version
```

## Usage (planned)
- Interactive mode: `blueprint` launches a plain console chat; run `blueprint tui` for the full-screen Textual UI.
- Static mode: `blueprint run <feature>` executes tasks headlessly for CI/CD or automation.

## Project layout
- `Internal/` – Implementation guides and specs (`AGENTS_GUIDE.md` + phased docs).
- `AGENTS.md` – Quick pointers to the internal agent docs.
- `src/` (to be populated per phases) – Core package code.

## Contributing workflow
- Read the relevant `Internal/PHASE_*.md` before coding.
- Implement in order; each phase has tests/checks you should run.
- Keep changes incremental and validated before moving to the next phase.

## Roadmap
- Phase 1: Foundation ✅
- Phase 2: LLM wrappers and router ✅
- Phase 3: Orchestration pipeline ✅
- Phase 4: Interactive TUI ⏳
- Phase 5: Static mode runner
- Phase 6: Logging and usage tracking
- Phase 7: Documentation pass
- Phase 8: Packaging and distribution
