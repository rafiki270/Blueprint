# Agent Resources

All agent-facing documentation lives in the `Internal/` folder.

- Start with `Internal/AGENTS_GUIDE.md` for orientation, workflows, and expectations.
- Additional specs and phase guides are in `Internal/` alongside the agent guide.

Keep this file pinned so you can quickly jump into the Internal docs when needed. Documentation and progress tracking must stay current—update the relevant Internal files as you implement changes. The project must remain cross-platform (macOS, Linux, WSL); avoid OS-specific assumptions in tooling and code.

Note: `make install` (or `make dev`) should install any required Python dependencies for the current phase; if you add a new dependency, wire it into those targets so a single command brings the environment up to date.

Current phase progress (see README.md for status; keep this in sync after any phase moves):
- Phase 1: ✅ Foundation
- Phase 2: ✅ LLM wrappers and router
- Phase 3: ✅ Orchestration pipeline
- Phase 4: ⏳ Interactive TUI
- Remaining: Phases 5–8

Textual layout/styling reference: see `Internal/TEXTUAL_LAYOUT_STYLING.md` for supported Textual 6.8.0 layout/styling properties (grid, spans, styling basics, widgets) and a minimal layout example. Use only supported props (no grid-row-start/column-start).
