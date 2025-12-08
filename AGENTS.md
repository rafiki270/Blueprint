# Agent Resources

All agent-facing documentation lives in the `Internal/` folder.

- Start with `Internal/AGENTS_GUIDE.md` for orientation, workflows, and expectations.
- Additional specs and phase guides are in `Internal/` alongside the agent guide.

Keep this file pinned so you can quickly jump into the Internal docs when needed. Documentation and progress tracking must stay current—update the relevant Internal files as you implement changes. The project must remain cross-platform (macOS, Linux, WSL); avoid OS-specific assumptions in tooling and code.

Note: `make install` (or `make dev`) should install any required Python dependencies for the current phase; if you add a new dependency, wire it into those targets so a single command brings the environment up to date.
