"""Plain console chat mode for Blueprint."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Iterable, List, Optional, Union

try:
    import readline  # type: ignore
except ImportError:  # pragma: no cover - platform dependent
    readline = None

import click

from .config import Config
from .models.base import ChatMessage, LLMExecutionException, LLMUnavailableException
from .models.router import ModelRole, ModelRouter
from .interactive.prompt_history import PromptHistory
from .orchestrator.executor import TaskExecutor
from .orchestrator.orchestrator import LLMOrchestrator
from .orchestrator.supervisor import Supervisor
from .state.feature import Feature
from .state.tasks import Task, TaskManager, TaskStatus, TaskType


STATUS_SYMBOLS = {
    TaskStatus.PENDING: "○",
    TaskStatus.IN_PROGRESS: "◐",
    TaskStatus.BLOCKED: "⚠",
    TaskStatus.COMPLETED: "●",
    TaskStatus.SKIPPED: "⊘",
}


class ConsoleChat:
    """Sequential console chat experience."""

    def __init__(self, feature_name: str) -> None:
        self.config = Config()
        self.feature = Feature(feature_name)
        self.feature.initialize()

        self.task_manager = TaskManager(self.feature.base_dir)
        self.router = ModelRouter(self.config)
        self.executor = TaskExecutor(self.task_manager, self.router, self.feature.base_dir)
        self.supervisor = Supervisor(self.router, self.feature.base_dir)
        self.orchestrator = LLMOrchestrator(self.config)
        self.orchestrator.feature_dir = self.feature.base_dir

        self.current_task: Optional[Task] = None
        self.context_limit: Optional[int] = None
        self.context_budget_ratio: float = 0.6  # use up to 60% of coder context
        self.current_backend: Optional[str] = None
        self._history_loaded_for: Optional[str] = None
        self._prompt_history: Optional[PromptHistory] = None

    async def run(self) -> None:
        """Start the console chat session."""
        self._print_header()
        await self.router.check_availability()

        try:
            await self._entry_flow()
            await self._chat_loop()
        except KeyboardInterrupt:
            click.echo("\nExiting Blueprint.")
        finally:
            await self._shutdown()

    async def _entry_flow(self) -> None:
        """Handle initial task selection flow."""
        tasks = self.task_manager.list_all()
        if not tasks:
            click.echo("No existing tasks detected. Let's create one.")
            self.current_task = await self._create_task_flow()
            if self.current_task:
                self._reset_session_context(self.current_task)
            return

        click.echo(self._color("Select an option: 1) Create new task  2) Work on existing task", "accent"))
        click.echo(self._muted("Use up/down and Enter, or type 1/2. (q to quit)"))
        choice = self._prompt_choice(["Create new task", "Work on existing task"])

        if choice is None:
            raise SystemExit(0)
        if choice == 0:
            self.current_task = await self._create_task_flow()
        else:
            self.current_task = await self._select_existing_task()
        if self.current_task:
            self._reset_session_context(self.current_task)

    async def _chat_loop(self) -> None:
        """Main chat loop."""
        click.echo("\n" + self._bold(self._color("Type /help for commands. Press Ctrl+C to exit.", "primary")))
        while True:
            self._ensure_history_ready()
            try:
                click.echo(self._prompt_label(), nl=False)
                prompt = input()
            except (KeyboardInterrupt, EOFError):
                click.echo("\nExiting Blueprint.")
                return

            prompt = prompt.strip()
            if not prompt:
                continue

            if prompt.startswith("/"):
                keep_running = await self._handle_command(prompt)
                if not keep_running:
                    return
                continue

            await self._chat_with_model(prompt)

    async def _handle_command(self, command: str) -> bool:
        """Handle slash commands. Returns False to exit loop."""
        parts = command.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("/exit", "/quit"):
            return False

        if cmd == "/help":
            self._print_help()
            return True

        if cmd == "/tasks":
            self._print_tasks(self.task_manager.list_all())
            return True

        if cmd == "/task":
            if arg:
                task = self.task_manager.get(arg)
                if task:
                    self.current_task = task
                    click.echo(f"Switched to [{task.id}] {task.title}")
                else:
                    click.echo(f"Task {arg} not found.")
            else:
                selected = await self._select_existing_task()
                if selected:
                    self.current_task = selected
            return True

        if cmd == "/new":
            created = await self._create_task_flow()
            if created:
                self.current_task = created
            return True

        if cmd == "/start":
            await self._start_next_task()
            return True

        if cmd == "/done":
            if not arg:
                click.echo("Usage: /done <task_id>")
            elif self.task_manager.mark_done(arg):
                click.echo(f"Task {arg} marked done.")
            else:
                click.echo(f"Task {arg} not found.")
            return True

        if cmd == "/redo":
            if not arg:
                click.echo("Usage: /redo <task_id>")
            elif self.task_manager.mark_redo(arg):
                click.echo(f"Task {arg} reset to pending.")
            else:
                click.echo(f"Task {arg} not found.")
            return True

        if cmd == "/spec":
            spec = self.feature.load_spec()
            if spec:
                click.echo("\n--- SPEC ---")
                click.echo(spec)
                click.echo("------------")
            else:
                click.echo("No specification found for this feature.")
            return True

        if cmd == "/clear":
            self._clear_session_context()
            self._clear_prompt_history()
            click.echo(self._color("Session context cleared.", "primary"))
            return True

        if cmd in ("/context", "/ctx"):
            self._print_context_usage()
            return True

        if cmd == "/stats":
            stats = self.orchestrator.get_usage_stats()
            click.echo("Usage:")
            if stats:
                click.echo("\n".join(f"- {k}: {v}" for k, v in stats.items()))
            else:
                click.echo("- no usage recorded yet")
            router_stats = self.router.get_routing_stats()
            click.echo("\nRouting health:")
            for provider, status in router_stats.get("models", {}).items():
                click.echo(f"- {provider}: {status}")
            return True

        if cmd == "/mode":
            click.echo(f"Tool mode: {self.orchestrator.get_tool_mode()}")
            return True

        if cmd.startswith("/persona"):
            if arg:
                try:
                    persona = self.orchestrator.set_persona(arg.strip())
                    click.echo(f"Active persona set to '{persona.name}'")
                except KeyError:
                    click.echo(f"Unknown persona '{arg.strip()}'.")
            else:
                names = ", ".join(self.orchestrator.personas.list_names())
                click.echo(f"Personas: {names}")
                click.echo(f"Current: {self.orchestrator.get_active_persona().name}")
            return True

        if cmd == "/ls":
            await self._cmd_ls(arg)
            return True

        if cmd == "/read":
            await self._cmd_read(arg)
            return True

        if cmd in ("/find", "/rg"):
            await self._cmd_find(arg)
            return True

        if cmd in ("/start", "/run"):
            await self._run_current_task()
            return True

        click.echo("Unknown command. Type /help for options.")
        return True

    def _print_help(self) -> None:
        click.echo(
            "\n".join(
                [
                    self._bold(self._color("Commands:", "primary")),
                    f"  {self._color('/help', 'accent'):15} Show this help",
                    f"  {self._color('/tasks', 'accent'):15} List tasks with status",
                    f"  {self._color('/task <id>', 'accent'):15} Switch to a task (or /task to select)",
                    f"  {self._color('/new', 'accent'):15} Create a new task",
                    f"  {self._color('/run', 'accent'):15} Execute current task (code + review loop) [/start alias]",
                    f"  {self._color('/done <id>', 'accent'):15} Mark task complete",
                    f"  {self._color('/redo <id>', 'accent'):15} Mark task pending",
                    f"  {self._color('/spec', 'accent'):15} Show the feature spec (if present)",
                    f"  {self._color('/ls [path]', 'accent'):15} List files (default: cwd)",
                    f"  {self._color('/read <path>', 'accent'):15} Read file into context",
                    f"  {self._color('/find <pat> [path]', 'accent'):15} Ripgrep search (default path: cwd)",
                    f"  {self._color('/context', 'accent'):15} Show session context usage vs limit",
                    f"  {self._color('/clear', 'accent'):15} Clear current session context",
                    f"  {self._color('/exit, /quit', 'accent'):15} Leave console mode",
                    "",
                    self._muted("Anything else is sent to the configured model for a quick chat."),
                ]
            )
        )

    async def _create_task_flow(self) -> Optional[Task]:
        """Prompt for a new task description and create it."""
        while True:
            description = click.prompt("Enter a task description").strip()
            if description:
                break
            click.echo("Please add a brief description.")

        if not click.confirm(f"Create task '{description}'?", default=True):
            click.echo("Cancelled new task.")
            return None

        task = self.task_manager.create(description, description, TaskType.CODE)
        click.echo(self._color(f"Created task [{task.id}].", "primary"))
        self._reset_session_context(task)
        return task

    async def _select_existing_task(self) -> Optional[Task]:
        """Show a selector for existing tasks."""
        tasks = self.task_manager.list_all()
        if not tasks:
            click.echo("No tasks available.")
            return None

        click.echo(
            self._color(
                "Select a task (1-{0}), or up/down + Enter. n for new, q to cancel.".format(len(tasks)),
                "accent",
            )
        )
        options = [self._task_line(task) for task in tasks]
        choice = self._prompt_choice(options, allow_new=True)

        if choice is None:
            return None
        if choice == "new":
            return await self._create_task_flow()
        selected = tasks[choice]
        self._reset_session_context(selected)
        return selected

    async def _start_next_task(self) -> None:
        """(Deprecated) Execute the next pending task."""
        await self._run_current_task()

    async def _run_current_task(self) -> None:
        """Execute the current task with review loop (single-task focus)."""
        task = self.current_task or self.task_manager.get_next()
        if not task:
            click.echo(self._color("No task selected or pending.", "warning"))
            return

        self.current_task = task
        code_path = self.feature.base_dir / "partial" / f"{task.id}_code.py"

        # If already completed and code exists, run review-only to avoid regenerating.
        if task.status == TaskStatus.COMPLETED and code_path.exists():
            click.echo(self._color(f"Reviewing existing output for [{task.id}] without regeneration.", "accent"))
            await self._review_code_task(task, code_path)
            return

        click.echo(self._color(f"Executing task: [{task.id}] {task.title}", "primary"))
        self.executor.run_context = self._prepare_run_context()
        success = await self.executor.execute_task(task)
        if not success:
            click.echo(self._color("Execution failed.", "warning"))
            return

        if task.type == TaskType.CODE:
            if code_path.exists():
                await self._review_code_task(task, code_path)
            else:
                click.echo(self._color("No code output found for review.", "warning"))

        self._print_tasks(self.task_manager.list_all())

    async def _review_code_task(self, task: Task, code_path: Path) -> None:
        """Run Codex review loop on a code artifact."""
        code_content = code_path.read_text(encoding="utf-8")
        click.echo(self._color("Reviewing with Codex...", "accent"))
        try:
            approved, final_output = await self.supervisor.iterative_correction(task, code_content)
            if approved:
                click.echo(self._color("Code approved by Codex.", "primary"))
            else:
                self.task_manager.mark_redo(task.id)
                click.echo(
                    self._color("Review failed; task reset to pending for manual follow-up.", "warning")
                )
        except Exception as exc:  # pragma: no cover - defensive
            msg = str(exc) or repr(exc)
            click.echo(
                self._color(
                    f"Codex review unavailable or failed: {msg}. Proceeding without automated review.",
                    "warning",
                )
            )

    def _print_tasks(self, tasks: List[Task]) -> None:
        """Pretty-print tasks."""
        if not tasks:
            click.echo("No tasks found.")
            return

        for task in tasks:
            click.echo(self._task_line(task))

    async def _chat_with_model(self, prompt: str) -> None:
        """Send free-form prompt to routed model and stream output."""
        self._append_conversation("user", prompt)

        try:
            adapter = await self.router.route(ModelRole.CODER)
        except LLMUnavailableException as exc:
            click.echo(self._color(f"Model unavailable: {exc}", "warning"))
            return

        backend = adapter.provider.value
        self.current_backend = backend
        model_name = getattr(adapter, "default_model", adapter.__class__.__name__)
        click.echo(self._muted(f"[model: {model_name}]"))

        try:
            response = await self.orchestrator.chat(
                prompt,
                backend=backend,
                include_context=True,
            )
        except (LLMUnavailableException, LLMExecutionException) as exc:
            click.echo(self._color(f"Error running model: {exc}", "warning"))
            return

        click.echo(self._color(response.content, "output"))
        self._append_conversation("assistant", response.content)
        self._append_context("assistant", response.content, backend)

    def _append_conversation(self, role: str, text: str) -> None:
        """Persist conversation to the current task log."""
        if self.current_task:
            self.feature.append_task_conversation(self.current_task.id, role, text)
        if role == "user":
            self._append_prompt_history(text)

    def _append_context(self, role: str, text: str, backend: Optional[str]) -> None:
        """Append to session context for the current task."""
        if not self.current_task:
            return
        backend_key = backend or self.current_backend or "global"
        self.orchestrator.context_manager.add_message(
            backend_key, ChatMessage(role=role, content=text)
        )

    def _clear_session_context(self) -> None:
        """Clear the current session context file."""
        self.orchestrator.context_manager.clear_all()
        if self.current_task:
            self.feature.clear_task_conversation(self.current_task.id)

    def _reset_session_context(self, task: Task) -> None:
        """Reset session context when entering a task."""
        self.orchestrator.context_manager.clear_all()
        self.feature.clear_task_conversation(task.id)
        self._clear_prompt_history()
        self._prime_context_from_history(task)
        asyncio.create_task(self._refresh_context_limit())
        self._refresh_prompt_history_state()

    def _prime_context_from_history(self, task: Task) -> None:
        """Load persisted conversation history into the orchestrator context."""
        entries = self.feature.load_task_conversation_entries(task.id)
        if not entries:
            return

        backend_key = self.current_backend or "global"
        for entry in entries[-50:]:  # cap to recent history
            role = entry.get("role")
            content = entry.get("content")
            if role and content:
                self.orchestrator.context_manager.add_message(
                    backend_key,
                    ChatMessage(role=role, content=content),
                )

    def _print_context_usage(self) -> None:
        """Print current context size and limit if known."""
        if not self.current_task:
            click.echo(self._color("No task selected.", "warning"))
            return
        backend_key = self.current_backend or "global"
        stats = self.orchestrator.context_manager.stats(backend_key)
        approx_tokens = stats["estimated_tokens"]
        limit = self.context_limit
        if limit:
            percent = min(100, int((approx_tokens / limit) * 100)) if limit else 0
            style = "warning" if percent >= 80 else "primary"
            click.echo(self._color(f"Context: ~{approx_tokens} tokens / {limit} (~{percent}% used)", style))
        else:
            click.echo(self._muted(f"Context: ~{approx_tokens} tokens (limit unknown)"))

    # Prompt history helpers
    def _history_path(self, task: Task) -> Path:
        """Per-task prompt history path."""
        return self.feature.task_dir(task.id) / "prompt-history.json"

    def _ensure_history_ready(self) -> None:
        """Load history into readline for the active task."""
        if readline is None or not self.current_task:
            return
        if self._history_loaded_for == self.current_task.id:
            return
        self._load_prompt_history()

    def _load_prompt_history(self) -> None:
        """Load stored prompts into readline."""
        if readline is None or not self.current_task:
            return
        self._prompt_history = PromptHistory(self._history_path(self.current_task))
        prompts = self._prompt_history.load()
        readline.clear_history()
        for prompt in prompts:
            readline.add_history(prompt)
        self._history_loaded_for = self.current_task.id

    def _append_prompt_history(self, prompt: str) -> None:
        """Append prompt to history file and readline."""
        if readline is None or not self.current_task:
            return
        if not self._prompt_history:
            self._prompt_history = PromptHistory(self._history_path(self.current_task))
        # Persist without reloading full history into readline to avoid corruption.
        self._prompt_history.append(prompt)
        try:
            readline.add_history(prompt)
        except Exception:
            pass

    def _clear_prompt_history(self) -> None:
        """Remove stored history for the current task."""
        if readline is not None:
            try:
                readline.clear_history()
            except Exception:
                pass
        if not self.current_task:
            return
        if self._prompt_history is None:
            self._prompt_history = PromptHistory(self._history_path(self.current_task))
        self._prompt_history.clear()
        self._history_loaded_for = None

    def _refresh_prompt_history_state(self) -> None:
        """Ensure readline history is reloaded for the current task."""
        if readline is None or not self.current_task:
            return
        self._history_loaded_for = None
        self._load_prompt_history()

    async def _refresh_context_limit(self) -> None:
        """Refresh cached context limit from the active coder backend if it exposes one."""
        try:
            adapter = await self.router.route(ModelRole.CODER)
            limit = await adapter.get_context_limit()
            if limit:
                self.context_limit = limit
        except Exception:
            return

    def _prompt_choice(self, options: Iterable[str], allow_new: bool = False) -> Optional[Union[int, str]]:
        """Prompt user for a choice with arrow or numeric input."""
        options_list = list(options)
        index = 0
        self._render_options(options_list, index)

        while True:
            key = self._read_key()

            if key == "up":
                index = (index - 1) % len(options_list)
            elif key == "down":
                index = (index + 1) % len(options_list)
            elif key == "enter":
                return index
            elif key.isdigit():
                num = int(key)
                if 1 <= num <= len(options_list):
                    return num - 1
            elif allow_new and key.lower() == "n":
                return "new"
            elif key.lower() in ("q", "escape"):
                return None
            else:
                continue

            # Re-render options in place without duplicating lines.
            self._move_cursor_up(len(options_list))
            self._render_options(options_list, index)

    def _task_line(self, task: Task) -> str:
        """Format a single task line."""
        symbol = STATUS_SYMBOLS.get(task.status, "?")
        return f"{symbol} [{task.id}] {task.title} ({task.status.value})"

    def _read_key(self) -> str:
        """Read a single keypress, translating arrows and enter."""
        char = click.getchar(echo=False)

        # Handle full escape sequences returned as one string (common).
        if "\x1b[A" in char:
            return "up"
        if "\x1b[B" in char:
            return "down"

        # Handle incremental escape sequence reads.
        if char == "\x1b":
            next1 = click.getchar(echo=False)
            if next1 == "[":
                next2 = click.getchar(echo=False)
                if next2 == "A":
                    return "up"
                if next2 == "B":
                    return "down"
            return "escape"

        if char in ("\r", "\n"):
            return "enter"

        return char

    def _render_options(self, options: List[str], index: int) -> None:
        """Render selectable options with a highlight."""
        for i, option in enumerate(options):
            prefix = ">" if i == index else " "
            line = f"{prefix} {i + 1}) {option}"
            if i == index:
                line = self._bold(self._color(line, "primary"))
            click.echo(f"\r\033[K{line}")

    @staticmethod
    def _move_cursor_up(lines: int) -> None:
        """Move cursor up a number of lines (ANSI)."""
        if lines > 0:
            click.echo(f"\033[{lines}A", nl=False)

    def _prompt_label(self) -> str:
        """Prompt label showing current task context."""
        if self.current_task:
            return self._color(f"[{self.current_task.id}]> ", "accent")
        return self._color("blueprint> ", "accent")

    async def _shutdown(self) -> None:
        """Cleanup resources on exit."""
        try:
            deepseek = getattr(self.router, "deepseek", None)
            if deepseek:
                await deepseek.stop_daemon()
        except Exception:
            # Best-effort cleanup; ignore errors on exit.
            pass

    # Context staging for executor
    def _prepare_run_context(self) -> str:
        """
        Prepare supplemental context for the coder model, capped to a budget.

        We use up to 60% of the known context limit (or a conservative default)
        to leave generation room. Oldest content is dropped first.
        """
        path = self._session_context_path(self.current_task) if self.current_task else None
        if not path or not path.exists():
            return ""

        raw = path.read_text(encoding="utf-8")
        limit_tokens = self.context_limit or 4096  # fallback
        budget_tokens = int(limit_tokens * self.context_budget_ratio)
        if budget_tokens <= 0:
            return ""

        # Approximate tokens as bytes/4.
        bytes_budget = budget_tokens * 4
        if len(raw) <= bytes_budget:
            return raw

        trimmed = raw[-bytes_budget:]
        self._append_conversation("system", f"[context trimmed to fit budget ~{budget_tokens} tokens]")
        return trimmed

    # Styling helpers
    @staticmethod
    def _color(text: str, style: str) -> str:
        palette = {
            "primary": "bright_green",
            "accent": "bright_cyan",
            "output": "bright_white",
            "muted": "bright_black",
            "warning": "bright_yellow",
        }
        return click.style(text, fg=palette.get(style, "white"))

    def _muted(self, text: str) -> str:
        return self._color(text, "muted")

    @staticmethod
    def _bold(text: str) -> str:
        return click.style(text, bold=True)

    def _print_header(self) -> None:
        border = self._color("=" * 60, "muted")
        title = self._bold(self._color("Blueprint console mode", "primary"))
        feature = self._color(f"feature: {self.feature.name}", "accent")
        click.echo(f"{border}\n{title}  [{feature}]\n{border}")

    # File and search helpers
    async def _cmd_ls(self, arg: str) -> None:
        """List files in a directory."""
        target = Path(arg.strip() or ".").expanduser()
        if not target.exists():
            click.echo(self._color(f"Path not found: {target}", "warning"))
            return

        try:
            entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except Exception as exc:
            click.echo(self._color(f"Unable to list {target}: {exc}", "warning"))
            return

        click.echo(self._bold(self._color(f"Listing {target}:", "primary")))
        for entry in entries[:200]:
            label = f"{entry.name}/" if entry.is_dir() else entry.name
            click.echo(self._muted("  ") + label)
        if len(entries) > 200:
            click.echo(self._muted(f"  ... and {len(entries) - 200} more"))

    async def _cmd_read(self, arg: str) -> None:
        """Read a file into session context."""
        path_str = arg.strip()
        if not path_str:
            click.echo(self._color("Usage: /read <path>", "warning"))
            return

        path = Path(path_str).expanduser()
        if not path.exists() or not path.is_file():
            click.echo(self._color(f"File not found: {path}", "warning"))
            return

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as exc:
            click.echo(self._color(f"Unable to read file: {exc}", "warning"))
            return

        max_chars = 20000
        truncated = len(content) > max_chars
        content_to_use = content[:max_chars]

        header = f"[file] {path}"
        if truncated:
            header += f" (truncated to {max_chars} chars)"
        self._append_context("system", f"{header}\n{content_to_use}")
        click.echo(self._color(f"Added to context: {path}", "primary"))
        if truncated:
            click.echo(self._muted("File was truncated to fit the context guard."))

    async def _cmd_find(self, arg: str) -> None:
        """Run ripgrep and print results, also append to context."""
        if not arg:
            click.echo(self._color("Usage: /find <pattern> [path]", "warning"))
            return
        parts = arg.split(maxsplit=1)
        pattern = parts[0]
        target = Path(parts[1]).expanduser() if len(parts) > 1 else Path(".")

        rg_cmd = ["rg", "--no-heading", "--line-number", "--color", "never", pattern, str(target)]
        try:
            proc = await asyncio.create_subprocess_exec(
                *rg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            click.echo(self._color("ripgrep (rg) not found. Please install rg.", "warning"))
            return
        except Exception as exc:
            click.echo(self._color(f"Unable to run rg: {exc}", "warning"))
            return

        stdout, stderr = await proc.communicate()
        if stderr:
            click.echo(self._muted(stderr.decode(errors="replace")))
        if stdout:
            output = stdout.decode(errors="replace")
            lines = output.splitlines()
            for line in lines[:200]:
                click.echo(self._color(line, "output"))
            if len(lines) > 200:
                click.echo(self._muted(f"... and {len(lines) - 200} more lines"))
            snippet = "\n".join(lines[:200])
            self._append_context("system", f"[rg] pattern={pattern} path={target}\n{snippet}")
        else:
            click.echo(self._muted("No matches found."))


async def run_console_chat(feature: str) -> None:
    """Helper to run the console chat session."""
    session = ConsoleChat(feature)
    await session.run()
