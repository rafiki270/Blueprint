"""Textual application for interactive mode."""

from __future__ import annotations

import asyncio

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Input

from .commands import CommandHandler
from .widgets import (
    ContextPanel,
    ModelSelectorModal,
    NewTaskModal,
    OutputPanel,
    TaskListWidget,
    TopBar,
    UsageModal,
)
from ..config import Config
from ..models.router import ModelRole, ModelRouter
from ..orchestrator.executor import TaskExecutor
from ..state.feature import Feature
from ..state.tasks import TaskManager, TaskType
from ..utils.usage_tracker import UsageTracker


class BlueprintApp(App):
    """Blueprint interactive mode TUI."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 3;
        grid-rows: auto 1fr auto;
        grid-columns: 1fr 3fr;
        overflow: hidden;
    }

    #top-bar {
        column-span: 2;
    }

    #task-list-widget {
        border: tall $primary;
        padding: 0;
        overflow-y: auto;
    }

    #output-panel {
        border: tall $primary;
        padding: 0;
        overflow-y: auto;
    }

    #context-panel {
        display: none;
        column-span: 2;
        height: 0;
        border: tall $primary;
        padding: 0;
        overflow-y: auto;
    }

    Footer {
        column-span: 2;
        background: $primary;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+p", "command_palette", "Menu"),
        Binding("ctrl+m", "select_model", "Model"),
        Binding("ctrl+n", "new_task", "New Task"),
        Binding("ctrl+u", "show_usage", "Usage"),
        Binding("ctrl+s", "stop_task", "Stop Task"),
        Binding("ctrl+c", "exit_or_confirm", "Quit"),
        Binding("/", "focus_command", "Help", show=True, key_display="/help"),
    ]

    def __init__(self, feature_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = Config()
        self.feature = Feature(feature_name)
        self.feature.initialize()
        self.task_manager = TaskManager(self.feature.base_dir)
        self.router = ModelRouter(self.config)
        self.executor = TaskExecutor(self.task_manager, self.router, self.feature.base_dir)
        self.usage_tracker = UsageTracker(self.feature.base_dir)
        self.command_handler = CommandHandler(
            self.task_manager,
            self.executor,
            self.usage_tracker,
            self.feature,
            self,
        )
        self.context_visible = False
        self.default_input_placeholder = "Enter command (type /help for commands)"

        # Clarification mode state
        self.waiting_for_clarification = False
        self.clarification_questions = []
        self.clarification_answers = []
        self.clarification_task = None
        self.clarification_brief = ""

    def compose(self) -> ComposeResult:
        yield TopBar(feature_name=self.feature.name, id="top-bar")

        self.task_list = TaskListWidget(id="task-list-widget")
        self.output_panel = OutputPanel(id="output-panel")
        self.context_panel = ContextPanel(id="context-panel")

        yield self.task_list
        yield self.output_panel
        yield self.context_panel
        yield Footer(show_command_palette=False)

    async def on_mount(self) -> None:
        tasks = self.task_manager.list_all()
        self.task_list.update_tasks(tasks)

        spec = self.feature.load_spec()
        if spec:
            self.context_panel.set_spec(spec)

        await self.router.check_availability()

        self.output_panel.write_line(f"Blueprint Interactive Mode - Feature: {self.feature.name}")
        self.output_panel.write_line("Type /help for commands")

    async def on_ready(self) -> None:
        """Ensure command input is focused once the UI is ready."""
        if hasattr(self, "_focus_command_input"):
            self._focus_command_input("/help", placeholder=self.default_input_placeholder)

    async def on_top_bar_command_submitted(self, event: TopBar.CommandSubmitted) -> None:
        """Handle command submission from TopBar."""
        # Check if we're in clarification mode
        if self.waiting_for_clarification:
            await self._handle_clarification_answer(event.command)
        else:
            await self.command_handler.handle(event.command)

    async def on_top_bar_context_toggled(self, event: TopBar.ContextToggled) -> None:
        """Handle context pane toggle from TopBar."""
        self.context_visible = not self.context_visible

        context_pane = self.query_one("#context-panel", ContextPanel)
        task_pane = self.query_one("#task-list-widget", TaskListWidget)
        output_pane = self.query_one("#output-panel", OutputPanel)

        if self.context_visible:
            # Show context pane fullscreen, hide others
            context_pane.styles.display = "block"
            context_pane.styles.height = "1fr"
            context_pane.styles.min_height = 10
            task_pane.styles.display = "none"
            output_pane.styles.display = "none"
            self.screen.styles.grid_size = (1, 3)
            self.screen.styles.grid_rows = "auto 1fr auto"
        else:
            # Hide context pane - grid becomes 2x3 (TopBar, Panels, Footer)
            context_pane.styles.display = "none"
            context_pane.styles.height = "0"
            task_pane.styles.display = "block"
            output_pane.styles.display = "block"
            # Update grid to 3 rows
            self.screen.styles.grid_size = (2, 3)
            self.screen.styles.grid_rows = "auto 1fr auto"

        self.refresh(layout=True)

    async def on_top_bar_menu_toggled(self, event: TopBar.MenuToggled) -> None:
        """Handle menu toggle from TopBar - open command palette."""
        self.action_command_palette()

    def on_task_list_widget_new_task_requested(self, event: TaskListWidget.NewTaskRequested) -> None:
        """Handle new task button press from TaskListWidget."""
        self.run_worker(self._show_new_task_modal())

    def on_task_list_widget_task_selected(self, event: TaskListWidget.TaskSelected) -> None:
        """Handle task selection from TaskListWidget."""
        task = event.task
        self.output_panel.clear()

        # Show task header
        self.output_panel.write_line(f"[bold cyan]Task: {task.title}[/bold cyan]")
        self.output_panel.write_line(f"[dim]ID: {task.id} | Status: {task.status.value} | Type: {task.type.value}[/dim]")
        self.output_panel.write_line("")

        # Load and display conversation history
        entries = self.feature.load_task_conversation_entries(task.id)

        if entries:
            self.output_panel.write_line("[bold]Conversation History:[/bold]")
            self.output_panel.write_line("")
            for entry in entries:
                ts = entry.get("timestamp", "")
                role = entry.get("role", "")
                content = entry.get("content", "")
                self.output_panel.write_line(f"[dim]{ts}[/dim] {role}: {content}")
        else:
            self.output_panel.write_line("[dim]No conversation history yet for this task.[/dim]")
            self.output_panel.write_line("[dim]Start a task with /start to begin logging conversation.[/dim]")

        # Also update context panel with task details
        self.context_panel.set_task(task)

        # Load task spec if available
        task_spec = self.feature.load_task_spec(task.id)
        if task_spec:
            self.context_panel.set_spec(task_spec)

    async def _show_new_task_modal(self) -> None:
        """Show the new task modal and handle result."""
        result = await self.push_screen_wait(NewTaskModal())
        if result:
            brief = result.strip()
            if not brief:
                return

            self.output_panel.write_line(f"[bold cyan]New Task Brief:[/bold cyan]")
            self.output_panel.write_line(brief)
            self.output_panel.write_line("")

            digest = await self._generate_task_digest(brief)

            task = self.task_manager.create(
                title=digest,
                description=brief,
                type=TaskType.CODE,
            )

            self.task_list.update_tasks(self.task_manager.list_all(), current_id=task.id)
            self.context_panel.set_task(task)

            self.output_panel.write_success(f"Task created: [{task.id}] {task.title}")
            self.output_panel.write_line(f"[dim]Saved to {self.task_manager.tasks_file}[/dim]")

            await self._generate_task_spec(task, brief)

    def action_new_task(self) -> None:
        """Show new task modal."""
        self.run_worker(self._show_new_task_modal())

    async def _generate_task_digest(self, brief: str) -> str:
        """Use local LLM to create a 4-5 word digest for the task title."""
        fallback = self._fallback_digest(brief)

        await self.router.check_availability()
        if not self.router.ollama_available:
            self.output_panel.write_warning("Local model unavailable; using brief snippet for title.")
            return fallback

        model_name = getattr(self.router.deepseek, "model", "local-model")
        prompt = (
            "Summarize this task brief as a concise 4-5 word task title for a task list. "
            "Make it specific (include the domain or goal), and avoid generic phrases. "
            "Return only the title text, no quotes or punctuation.\n\n"
            f"Task brief:\n{brief}"
        )

        self.output_panel.write_line(f"[dim]Summarizing with local model ({model_name})...[/dim]")

        try:
            lines: list[str] = []
            async for line in self.router.deepseek.execute(prompt, stream=False):
                lines.append(line)

            raw = " ".join(lines)
            digest = self._normalize_digest(raw)
            return digest or fallback
        except Exception:
            self.output_panel.write_warning("Local summarization failed; using brief snippet for title.")
            return fallback

    @staticmethod
    def _fallback_digest(brief: str) -> str:
        """Fallback digest if local summarization is unavailable."""
        words = brief.split()
        if not words:
            return "New Task"
        return " ".join(words[:5])

    @staticmethod
    def _normalize_digest(text: str) -> str:
        """Normalize whitespace and trim to ~5 words."""
        cleaned = text.strip().strip("\"'“”‘’`")
        words = cleaned.split()
        if not words:
            return ""
        return " ".join(words[:5])

    async def _generate_task_spec(self, task, brief: str) -> None:
        """Generate and save a per-task spec with Claude."""
        self.output_panel.write_line("[dim]Generating task specification with Claude...[/dim]")
        try:
            claude = await self.router.route(ModelRole.ARCHITECT)
            repo_context = self._build_task_context(task)
            enriched_brief = f"""{brief}

Additional instructions for the architect:
- Act as the system architect and produce a concise, actionable technical spec.
- The spec text you return will be saved to: {self.feature.task_spec_path(task.id)}
- Tasks for this feature will live in: {self.feature.tasks_file}
- Include clear sections (overview, architecture, data/contracts, API/IO, risks, test plan, task checklist).
- Prefer architecture patterns appropriate to the brief (e.g., MVC, MVVM, or Clean Architecture). Explain the chosen pattern briefly.
- List external modules/libraries to use (and why), and note any OS/tooling assumptions.
- Provide task breakdown as a numbered list so a downstream LLM can execute them sequentially.
- Avoid suggesting concrete code unless absolutely necessary for a tricky interface or data shape; focus on structure and contracts.
- Keep it terminal-friendly (no excessive Markdown noise).
- If required information is missing, list the clarifying questions explicitly so we can follow up in the CLI.

Repository and task context:
{repo_context}"""

            spec = await claude.generate_spec(enriched_brief)
            self.feature.save_task_spec(task.id, spec)
            self.context_panel.set_spec(spec)
            self.output_panel.write_success(f"Task specification saved to {self.feature.task_spec_path(task.id)}")

            questions = self._extract_questions(spec)
            if questions:
                # Enter clarification mode instead of showing modal
                self.waiting_for_clarification = True
                self.clarification_questions = questions
                self.clarification_answers = []
                self.clarification_task = task
                self.clarification_brief = enriched_brief

                # Move focus to the command bar for answers
                self._focus_command_input(
                    "",
                    placeholder="Answer here (or type 'skip' to continue; press / to refocus)",
                )

                self.output_panel.write_line("")
                self.output_panel.write_line("[bold yellow]Claude needs clarifications:[/bold yellow]")
                for i, q in enumerate(questions, 1):
                    self.output_panel.write_line(f"{i}. {q}")
                self.output_panel.write_line("")
                self.output_panel.write_line(
                    "[bold cyan]Type your answer in the command bar at the top (Output is read-only).[/bold cyan]"
                )
                return  # Wait for user input
        except Exception as exc:
            self.output_panel.write_warning(f"Could not generate task specification: {exc}")

    def _build_task_context(self, task) -> str:
        """Assemble lightweight repo + task context for the architect."""
        repo_root = Path.cwd()
        files_to_include = self._find_case_insensitive(
            repo_root,
            [
                "README.md",
                "AGENTS.md",
                "CLAUDE.md",
                "gemini.md",
            ],
        )

        snippets: list[str] = []
        snippets.append(f"- Repo root: {repo_root}")
        snippets.append(f"- Feature dir: {self.feature.base_dir}")
        snippets.append(f"- Task dir: {self.feature.task_dir(task.id)}")

        # Task summaries for awareness of group context
        task_summaries = []
        for t in self.task_manager.list_all():
            task_summaries.append(f"[{t.id}] {t.title} (status: {t.status.value})")
        if task_summaries:
            snippets.append("Other tasks in this feature:")
            snippets.extend([f"  - {line}" for line in task_summaries])

        # Key docs snippets
        for path in files_to_include:
            if path.exists():
                content = self._read_snippet(path, 2400)
                snippets.append(f"\n---\nFile: {path.relative_to(repo_root)}\n{content}")

        return "\n".join(snippets)

    @staticmethod
    def _read_snippet(path: Path, max_chars: int) -> str:
        """Read a file up to max_chars."""
        try:
            text = path.read_text(encoding="utf-8")
            if len(text) > max_chars:
                return text[:max_chars] + "\n...[truncated]..."
            return text
        except Exception:
            return "[unreadable]"

    @staticmethod
    def _find_case_insensitive(root: Path, names: list[str]) -> list[Path]:
        """Find files under root matching any of the given names, case-insensitive."""
        found: list[Path] = []
        lower_targets = {name.lower() for name in names}
        for path in root.iterdir():
            if path.is_file() and path.name.lower() in lower_targets:
                found.append(path)
        return found

    @staticmethod
    def _gather_additional_files(paths: list[str]) -> str:
        """Read arbitrary files relative to repo root for additional context."""
        if not paths:
            return ""
        repo_root = Path.cwd()
        snippets: list[str] = []
        for raw in paths:
            raw = raw.strip()
            if not raw:
                continue
            file_path = (repo_root / raw).resolve()
            try:
                if file_path.is_file() and str(file_path).startswith(str(repo_root.resolve())):
                    content = file_path.read_text(encoding="utf-8")
                    if len(content) > 2400:
                        content = content[:2400] + "\n...[truncated]..."
                    snippets.append(f"---\nFile: {file_path.relative_to(repo_root)}\n{content}")
            except Exception:
                continue
        return "\n".join(snippets)

    @staticmethod
    def _extract_questions(spec: str) -> list[str]:
        """Extract clarifying questions from spec text."""
        questions: list[str] = []
        for line in spec.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if not stripped.endswith("?"):
                continue
            # Remove common bullet/numbering prefixes.
            while stripped and stripped[0] in "-*0123456789. ":
                stripped = stripped[1:].lstrip()
            questions.append(stripped)
        return questions

    async def _handle_clarification_answer(self, answer: str) -> None:
        """Process clarification answer from user input."""
        answer = answer.strip()

        if answer.lower() == "skip":
            # User wants to skip clarifications
            self.output_panel.write_line("[dim]Skipping clarifications...[/dim]")
            self.waiting_for_clarification = False
            self.clarification_questions = []
            self.clarification_answers = []
            self.clarification_task = None
            self.clarification_brief = ""

            # Restore input placeholder and focus
            self._focus_command_input("", placeholder=self.default_input_placeholder)
            return

        # Add answer to list
        self.clarification_answers.append(answer)
        self.output_panel.write_line(f"[dim]Answer {len(self.clarification_answers)}: {answer}[/dim]")

        # Check if we have all answers
        if len(self.clarification_answers) >= len(self.clarification_questions):
            # All questions answered, continue with spec generation
            self.waiting_for_clarification = False

            # Restore input placeholder and focus
            self._focus_command_input("", placeholder=self.default_input_placeholder)

            self.output_panel.write_line("")
            self.output_panel.write_line("[dim]Sending clarifications back to Claude...[/dim]")

            # Format answers
            formatted_answers = "\n".join(
                f"{i+1}. {q}\n   Answer: {a}"
                for i, (q, a) in enumerate(zip(self.clarification_questions, self.clarification_answers))
            )

            # Generate refined spec
            try:
                claude = await self.router.route(ModelRole.ARCHITECT)
                clarified_brief = self.clarification_brief + "\n\nClarification answers:\n" + formatted_answers

                refined_spec = await claude.generate_spec(clarified_brief)
                self.feature.save_task_spec(self.clarification_task.id, refined_spec)
                self.context_panel.set_spec(refined_spec)
                self.output_panel.write_success(
                    f"Refined task specification saved to {self.feature.task_spec_path(self.clarification_task.id)}"
                )
            except Exception as exc:
                self.output_panel.write_warning(f"Could not refine specification: {exc}")

            # Reset clarification state
            self.clarification_questions = []
            self.clarification_answers = []
            self.clarification_task = None
            self.clarification_brief = ""
        else:
            # More questions remaining
            remaining = len(self.clarification_questions) - len(self.clarification_answers)
            self.output_panel.write_line(f"[dim]({remaining} question(s) remaining)[/dim]")
            self._focus_command_input("", placeholder="Answer here (or type 'skip' to continue; press / to refocus)")

    def action_select_model(self) -> None:
        """Open the model selector modal."""
        self.run_worker(self._show_model_selector())

    async def _list_ollama_models(self) -> list[str]:
        """List available ollama models."""
        try:
            process = await asyncio.create_subprocess_exec(
                "ollama",
                "list",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                lines = stdout.decode().strip().split("\n")
                models: list[str] = []
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    parts = line.split()
                    if parts:
                        models.append(parts[0])
                return models
            return []
        except FileNotFoundError:
            return []
        except Exception:
            return []

    async def _show_model_selector(self) -> None:
        """Show model selector and save selection."""
        models = await self._list_ollama_models()
        current_model = self.config.get("local_model", "deepseek-coder:14b")

        result = await self.push_screen_wait(ModelSelectorModal(models, current_model))

        if result:
            self.config.set("local_model", result)
            self.output_panel.write_success(f"Model changed to: {result}")

    def action_stop_task(self) -> None:
        self.run_worker(self.command_handler.cmd_stop(""))

    def action_show_usage(self) -> None:
        self.push_screen(UsageModal(self.usage_tracker))

    def action_show_help(self) -> None:
        self.run_worker(self.command_handler.cmd_help(""))

    def action_focus_command(self) -> None:
        """Focus the command input and pre-fill with /help."""
        self._focus_command_input("/help", placeholder=self.default_input_placeholder)

    def action_exit_or_confirm(self) -> None:
        """Exit on double Ctrl+C."""
        self.exit()

    def log_task_conversation(self, task_id: str, role: str, message: str) -> None:
        """Log a message to the task's conversation history."""
        self.feature.append_task_conversation(task_id, role, message)

    def _focus_command_input(self, prefill: str = "", placeholder: str | None = None) -> None:
        """Focus the top command input with optional prefill/placeholder."""
        top_bar = self.query_one("#top-bar", TopBar)
        input_widget = top_bar.query_one(Input)
        if placeholder is not None:
            input_widget.placeholder = placeholder
        input_widget.value = prefill
        input_widget.cursor_position = len(prefill)
        self.set_focus(input_widget)
