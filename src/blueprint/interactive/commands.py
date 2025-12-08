"""Command handlers for interactive mode."""

from __future__ import annotations

import asyncio
from typing import Callable, Dict

from ..orchestrator.executor import TaskExecutor
from ..state.feature import Feature
from ..state.tasks import TaskManager
from ..utils.usage_tracker import UsageTracker


class CommandHandler:
    """Handles interactive mode commands."""

    def __init__(
        self,
        task_manager: TaskManager,
        executor: TaskExecutor,
        usage_tracker: UsageTracker,
        feature: Feature,
        app,
    ):
        self.task_manager = task_manager
        self.executor = executor
        self.usage_tracker = usage_tracker
        self.feature = feature
        self.app = app

        self.commands: Dict[str, Callable] = {
            "/help": self.cmd_help,
            "/start": self.cmd_start,
            "/stop": self.cmd_stop,
            "/correct": self.cmd_correct,
            "/resume": self.cmd_resume,
            "/switch-model": self.cmd_switch_model,
            "/usage": self.cmd_usage,
            "/tasks": self.cmd_tasks,
            "/done": self.cmd_done,
            "/delete": self.cmd_delete,
            "/redo": self.cmd_redo,
            "/missing": self.cmd_missing,
            "/next": self.cmd_next,
            "/task": self.cmd_task,
            "/spec": self.cmd_spec,
            "/logs": self.cmd_logs,
            "/exit": self.cmd_exit,
        }

    async def handle(self, command: str) -> None:
        # Check if it's a slash command
        if command.startswith("/"):
            parts = command.split(maxsplit=1)
            cmd = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            handler = self.commands.get(cmd)
            if handler:
                await handler(args)
            else:
                self.app.output_panel.write_error(f"Unknown command: {cmd}")
                self.app.output_panel.write_line("Type /help for available commands")
        else:
            # Free-form input - send to ollama
            await self.chat_with_ollama(command)

    async def cmd_help(self, args: str) -> None:
        help_text = """
[bold]Blueprint Interactive Commands[/bold]

[bold cyan]Free-form Chat:[/bold cyan]
  Type any text (without /) to chat with the selected ollama model
  Press Ctrl+M to select a different model

Task Management:
  /tasks          List all tasks
  /done <id>      Mark task as completed
  /delete <id>    Delete a task
  /redo <id>      Mark task as incomplete
  /missing        Show incomplete tasks
  /next           Move to next incomplete task
  /task <id>      Jump to specific task

Execution Control:
  /start          Start next task
  /stop           Stop current task
  /correct        Enter correction mode
  /resume         Resume current task

Configuration:
  /switch-model   Change local coder model (or use Ctrl+M)
  /usage          Show usage dashboard
  /spec           View specification
  /logs           View logs

Other:
  /help           Show this help
  /exit           Exit Blueprint
"""
        self.app.output_panel.write_section("Help", help_text)

    async def cmd_start(self, args: str) -> None:
        next_task = self.task_manager.get_next()
        if not next_task:
            self.app.output_panel.write_warning("No pending tasks")
            return
        self.app.output_panel.write_line(f"Starting task: {next_task.title}")
        await self.executor.execute_task(next_task)
        self.app.task_list.update_tasks(self.task_manager.list_all(), current_id=None)

    async def cmd_stop(self, args: str) -> None:
        await self.executor.stop_current_task()
        self.app.output_panel.write_warning("Task stopped")

    async def cmd_correct(self, args: str) -> None:
        self.app.output_panel.write_line("Correction mode - (placeholder)")

    async def cmd_resume(self, args: str) -> None:
        current = self.executor.get_current_task()
        if current:
            self.app.output_panel.write_line(f"Resuming: {current.title}")
            await self.executor.execute_task(current)
        else:
            self.app.output_panel.write_warning("No task to resume")

    async def cmd_switch_model(self, args: str) -> None:
        # Trigger the model selector
        self.app.action_select_model()

    async def cmd_usage(self, args: str) -> None:
        from .widgets.usage_modal import UsageModal

        self.app.push_screen(UsageModal(self.usage_tracker))

    async def cmd_tasks(self, args: str) -> None:
        tasks = self.task_manager.list_all()
        self.app.task_list.update_tasks(tasks)
        self.app.output_panel.write_line(f"Total tasks: {len(tasks)}")

    async def cmd_done(self, args: str) -> None:
        if not args:
            self.app.output_panel.write_error("Usage: /done <task_id>")
            return
        if self.task_manager.mark_done(args):
            self.app.output_panel.write_success(f"Task {args} marked as done")
            self.app.task_list.update_tasks(self.task_manager.list_all())
        else:
            self.app.output_panel.write_error(f"Task {args} not found")

    async def cmd_delete(self, args: str) -> None:
        if not args:
            self.app.output_panel.write_error("Usage: /delete <task_id>")
            return
        if self.task_manager.delete(args):
            self.app.output_panel.write_success(f"Task {args} deleted")
            self.app.task_list.update_tasks(self.task_manager.list_all())
        else:
            self.app.output_panel.write_error(f"Task {args} not found")

    async def cmd_redo(self, args: str) -> None:
        if not args:
            self.app.output_panel.write_error("Usage: /redo <task_id>")
            return
        if self.task_manager.mark_redo(args):
            self.app.output_panel.write_success(f"Task {args} marked as incomplete")
            self.app.task_list.update_tasks(self.task_manager.list_all())
        else:
            self.app.output_panel.write_error(f"Task {args} not found")

    async def cmd_missing(self, args: str) -> None:
        missing = self.task_manager.get_missing()
        self.app.output_panel.write_line(f"Incomplete tasks: {len(missing)}")
        for task in missing:
            self.app.output_panel.write_line(f"  [{task.id}] {task.title}")

    async def cmd_next(self, args: str) -> None:
        next_task = self.task_manager.get_next()
        if next_task:
            self.app.output_panel.write_line(f"Next task: [{next_task.id}] {next_task.title}")
            self.app.context_panel.set_task(next_task)
        else:
            self.app.output_panel.write_warning("No pending tasks")

    async def cmd_task(self, args: str) -> None:
        if not args:
            self.app.output_panel.write_error("Usage: /task <task_id>")
            return
        task = self.task_manager.get(args)
        if task:
            self.app.context_panel.set_task(task)
            self.app.output_panel.write_line(f"Viewing task: {task.title}")
        else:
            self.app.output_panel.write_error(f"Task {args} not found")

    async def cmd_spec(self, args: str) -> None:
        spec = self.feature.load_spec()
        if spec:
            self.app.context_panel.set_spec(spec)
            self.app.output_panel.write_line("Specification loaded in context panel")
        else:
            self.app.output_panel.write_error("No specification found")

    async def cmd_logs(self, args: str) -> None:
        logs_dir = self.feature.base_dir / "logs"
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.log"))
            self.app.output_panel.write_line(f"Log files in {logs_dir}:")
            for log_file in log_files:
                self.app.output_panel.write_line(f"  - {log_file.name}")
        else:
            self.app.output_panel.write_warning("No logs directory found")

    async def cmd_exit(self, args: str) -> None:
        self.app.exit()

    async def chat_with_ollama(self, prompt: str) -> None:
        """Send free-form prompt to ollama model."""
        from ..config import Config

        config = Config()
        model = config.get("local_model", "deepseek-coder:14b")

        self.app.output_panel.write_line(f"[dim]Using model: {model}[/dim]")
        self.app.output_panel.write_line("")

        try:
            process = await asyncio.create_subprocess_exec(
                "ollama",
                "run",
                model,
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Stream output line by line
            if process.stdout:
                async for line_bytes in process.stdout:
                    line = line_bytes.decode(errors="replace").rstrip()
                    if line:
                        self.app.output_panel.write_line(line)

            await process.wait()

            if process.returncode != 0 and process.stderr:
                stderr = await process.stderr.read()
                error_msg = stderr.decode(errors="replace")
                self.app.output_panel.write_error(f"Ollama error: {error_msg}")

        except FileNotFoundError:
            self.app.output_panel.write_error("Ollama not found. Please install ollama first.")
        except Exception as e:
            self.app.output_panel.write_error(f"Error: {str(e)}")
