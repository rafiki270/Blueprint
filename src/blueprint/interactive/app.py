"""Textual application for interactive mode."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input

from .commands import CommandHandler
from .widgets import ContextPanel, OutputPanel, TaskListWidget, TopBar, UsageModal
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
        grid-size: 2 2;
        grid-rows: auto 1fr;
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
        self.context_visible = False

    def compose(self) -> ComposeResult:
        yield TopBar(feature_name=self.feature.name, id="top-bar")

        self.task_list = TaskListWidget(id="task-list-widget")
        self.output_panel = OutputPanel(id="output-panel")
        self.context_panel = ContextPanel(id="context-panel")

        yield self.task_list
        yield self.output_panel
        yield self.context_panel

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

    async def on_top_bar_command_submitted(self, event: TopBar.CommandSubmitted) -> None:
        """Handle command submission from TopBar."""
        await self.command_handler.handle(event.command)

    async def on_top_bar_context_toggled(self, event: TopBar.ContextToggled) -> None:
        """Handle context pane toggle from TopBar."""
        self.context_visible = not self.context_visible

        context_pane = self.query_one("#context-panel", ContextPanel)

        if self.context_visible:
            # Show context pane
            context_pane.styles.display = "block"
            context_pane.styles.height = "30%"
            context_pane.styles.min_height = 8
            # Update grid to 3 rows
            self.screen.styles.grid_size = (2, 3)
            self.screen.styles.grid_rows = "auto 1fr auto"
        else:
            # Hide context pane
            context_pane.styles.display = "none"
            context_pane.styles.height = "0"
            # Update grid to 2 rows
            self.screen.styles.grid_size = (2, 2)
            self.screen.styles.grid_rows = "auto 1fr"

        self.refresh(layout=True)

    async def on_top_bar_menu_toggled(self, event: TopBar.MenuToggled) -> None:
        """Handle menu toggle from TopBar - open command palette."""
        self.action_command_palette()

    def action_stop_task(self) -> None:
        self.run_worker(self.command_handler.cmd_stop(""))

    def action_show_usage(self) -> None:
        self.push_screen(UsageModal(self.usage_tracker))

    def action_show_help(self) -> None:
        self.run_worker(self.command_handler.cmd_help(""))

    def action_focus_command(self) -> None:
        """Focus the command input."""
        top_bar = self.query_one("#top-bar", TopBar)
        input_widget = top_bar.query_one(Input)
        self.set_focus(input_widget)

    def action_exit_or_confirm(self) -> None:
        """Exit on double Ctrl+C."""
        self.exit()
