"""Plain console chat mode for Blueprint."""

from __future__ import annotations

import asyncio
from typing import Iterable, List, Optional, Union

import click

from .config import Config
from .models.base import LLMExecutionException, LLMUnavailableException
from .models.router import ModelRole, ModelRouter
from .models.deepseek import DeepSeekCLI
from .orchestrator.executor import TaskExecutor
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

        self.current_task: Optional[Task] = None
        self.context_limit: Optional[int] = None

    async def run(self) -> None:
        """Start the console chat session."""
        click.echo(f"Blueprint console mode - feature: {self.feature.name}")
        await self.router.check_availability()

        await self._entry_flow()
        await self._chat_loop()

    async def _entry_flow(self) -> None:
        """Handle initial task selection flow."""
        tasks = self.task_manager.list_all()
        if not tasks:
            click.echo("No existing tasks detected. Let's create one.")
            self.current_task = await self._create_task_flow()
            if self.current_task:
                self._reset_session_context(self.current_task)
            return

        click.echo("Select an option: 1) Create new task  2) Work on existing task")
        click.echo("Use up/down and Enter, or type 1/2. (q to quit)")
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
        click.echo("\n\033[1mType /help for commands. Press Ctrl+C to exit.\033[0m")
        while True:
            try:
                prompt = await asyncio.to_thread(input, self._prompt_label())
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
            click.echo("Session context cleared.")
            return True

        if cmd in ("/context", "/ctx"):
            self._print_context_usage()
            return True

        click.echo("Unknown command. Type /help for options.")
        return True

    def _print_help(self) -> None:
        click.echo(
            """
Commands:
  /help           Show this help
  /tasks          List tasks with status
  /task <id>      Switch to a task (or /task to select)
  /new            Create a new task
  /start          Execute the next pending task
  /done <id>      Mark task complete
  /redo <id>      Mark task pending
  /spec           Show the feature spec (if present)
  /context        Show session context usage vs limit (if available)
  /clear          Clear current session context
  /exit, /quit    Leave console mode

Anything else is sent to the configured model for a quick chat."""
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
        click.echo(f"Created task [{task.id}].")
        self._reset_session_context(task)
        return task

    async def _select_existing_task(self) -> Optional[Task]:
        """Show a selector for existing tasks."""
        tasks = self.task_manager.list_all()
        if not tasks:
            click.echo("No tasks available.")
            return None

        click.echo(
            "Select a task (1-{0}), or up/down + Enter. n for new, q to cancel.".format(len(tasks))
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
        """Execute the next pending task."""
        next_task = self.task_manager.get_next()
        if not next_task:
            click.echo("No pending tasks.")
            return

        self.current_task = next_task
        click.echo(f"Starting task: [{next_task.id}] {next_task.title}")
        await self.executor.execute_task(next_task)
        self._print_tasks(self.task_manager.list_all())

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
            model = await self.router.route(ModelRole.CODER)
        except LLMUnavailableException as exc:
            click.echo(f"Model unavailable: {exc}")
            return

        click.echo(f"[model: {model.__class__.__name__}]")
        response_lines: List[str] = []
        try:
            async for line in model.execute(prompt, stream=True):
                click.echo(line)
                response_lines.append(line)
        except (LLMUnavailableException, LLMExecutionException) as exc:
            click.echo(f"Error running model: {exc}")
            return

        if response_lines:
            self._append_conversation("assistant", "\n".join(response_lines))
        self._append_context("assistant", "\n".join(response_lines))

    def _append_conversation(self, role: str, text: str) -> None:
        """Persist conversation to the current task log."""
        if self.current_task:
            self.feature.append_task_conversation(self.current_task.id, role, text)

    def _append_context(self, role: str, text: str) -> None:
        """Append to session context for the current task."""
        if not self.current_task:
            return
        path = self._session_context_path(self.current_task)
        entry = f"{role}: {text}\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fp:
            fp.write(entry)

    def _clear_session_context(self) -> None:
        """Clear the current session context file."""
        if self.current_task:
            path = self._session_context_path(self.current_task)
            if path.exists():
                path.unlink()

    def _reset_session_context(self, task: Task) -> None:
        """Reset session context when entering a task."""
        path = self._session_context_path(task)
        if path.exists():
            path.unlink()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        asyncio.create_task(self._refresh_context_limit())

    def _session_context_path(self, task: Task):
        """Path to the session context file for a task."""
        return task and self.feature.task_dir(task.id) / "session.context"

    def _print_context_usage(self) -> None:
        """Print current context size and limit if known."""
        if not self.current_task:
            click.echo("No task selected.")
            return
        path = self._session_context_path(self.current_task)
        size_bytes = path.stat().st_size if path.exists() else 0
        approx_tokens = max(1, size_bytes // 4) if size_bytes else 0
        limit = self.context_limit
        if limit:
            percent = min(100, int((approx_tokens / limit) * 100)) if limit else 0
            click.echo(f"Context: ~{approx_tokens} tokens / {limit} (~{percent}% used)")
        else:
            click.echo(f"Context: ~{approx_tokens} tokens (limit unknown)")

    async def _refresh_context_limit(self) -> None:
        """Refresh cached context limit from DeepSeek if available."""
        try:
            model = await self.router.route(ModelRole.CODER)
            if isinstance(model, DeepSeekCLI):
                limit = await model.get_context_limit()
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
                line = f"\033[1m{line}\033[0m"
            click.echo(f"\r\033[K{line}")

    @staticmethod
    def _move_cursor_up(lines: int) -> None:
        """Move cursor up a number of lines (ANSI)."""
        if lines > 0:
            click.echo(f"\033[{lines}A", nl=False)

    def _prompt_label(self) -> str:
        """Prompt label showing current task context."""
        if self.current_task:
            return f"[{self.current_task.id}]> "
        return "blueprint> "


async def run_console_chat(feature: str) -> None:
    """Helper to run the console chat session."""
    session = ConsoleChat(feature)
    await session.run()
