"""Textual application for interactive mode."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Input, Static

from .commands import CommandHandler
from .widgets import CommandBar, ContextPanel, OutputPanel, TaskListWidget, UsageModal
from ..config import Config
from ..models.router import ModelRouter
from ..orchestrator.executor import TaskExecutor
from ..state.feature import Feature
from ..state.tasks import TaskManager
from ..utils.usage_tracker import UsageTracker


class BlueprintApp(App):
    """Blueprint interactive mode TUI."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 3;
        grid-rows: auto 1fr auto;
        grid-columns: 1fr 1fr 1fr;
        grid-gutter: 0 1;
    }

    Header {
        column-span: 3;
    }

    #task-list-widget {
        border: tall;
    }

    #output-panel {
        border: tall;
    }

    #context-panel {
        border: tall;
    }

    #command-bar {
        column-span: 3;
        border: tall;
        height: 1;
        padding: 0 1;
    }

    #command-bar #command-bar-container {
        layout: horizontal;
        align: center middle;
        height: 1;
    }

    #command-bar #command-input {
        width: 1fr;
        border: round;
        height: 1;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "stop_task", "Stop"),
        Binding("ctrl+c", "exit_or_confirm", "Exit"),
        Binding("ctrl+u", "show_usage", "Usage"),
        Binding("f1", "show_help", "Help"),
        Binding("/", "focus_command", "Command", show=False),
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

    def compose(self) -> ComposeResult:
        yield Header()

        self.task_list = TaskListWidget(id="task-list-widget")
        self.output_panel = OutputPanel(id="output-panel")
        self.context_panel = ContextPanel(id="context-panel")
        self.command_bar = CommandBar(id="command-bar")

        yield self.task_list
        yield self.output_panel
        yield self.context_panel
        yield self.command_bar

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
        self.action_focus_command()
        # Force a visible block cursor in the input.
        try:
            command_input = self.command_bar.query_one(Input)
            command_input.cursor_style = "block"
        except Exception:
            pass

    async def on_command_bar_command_submitted(self, event: CommandBar.CommandSubmitted) -> None:
        await self.command_handler.handle(event.command)

    def action_stop_task(self) -> None:
        self.run_worker(self.command_handler.cmd_stop(""))

    def action_show_usage(self) -> None:
        self.push_screen(UsageModal(self.usage_tracker))

    def action_show_help(self) -> None:
        self.run_worker(self.command_handler.cmd_help(""))

    def action_focus_command(self) -> None:
        """Focus the command input."""
        self.set_focus(self.command_bar.query_one(Input))

    def action_exit_or_confirm(self) -> None:
        """Exit on double Ctrl+C."""
        self.exit()
