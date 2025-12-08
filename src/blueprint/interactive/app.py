"""Textual application for interactive mode."""

from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Input

from .commands import CommandHandler
from .widgets import ContextPanel, ModelSelectorModal, NewTaskModal, OutputPanel, TaskListWidget, TopBar, UsageModal
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
        Binding("/", "focus_command", "/help", show=True, key_display="/help"),
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
        yield Footer()

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
            # Show context pane - grid becomes 2x4 (TopBar, Panels, Context, Footer)
            context_pane.styles.display = "block"
            context_pane.styles.height = "30%"
            context_pane.styles.min_height = 8
            # Update grid to 4 rows
            self.screen.styles.grid_size = (2, 4)
            self.screen.styles.grid_rows = "auto 1fr auto auto"
        else:
            # Hide context pane - grid becomes 2x3 (TopBar, Panels, Footer)
            context_pane.styles.display = "none"
            context_pane.styles.height = "0"
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

    async def _show_new_task_modal(self) -> None:
        """Show the new task modal and handle result."""
        result = await self.push_screen_wait(NewTaskModal())
        if result:
            # TODO: Process the brief with Claude to generate a plan
            self.output_panel.write_line(f"[bold cyan]New Task Brief:[/bold cyan]")
            self.output_panel.write_line(result)
            self.output_panel.write_line("")
            self.output_panel.write_line("[dim]Next step: Process with Claude to generate plan...[/dim]")

    def action_new_task(self) -> None:
        """Show new task modal."""
        self.run_worker(self._show_new_task_modal())

    def action_select_model(self) -> None:
        """Show model selector modal."""
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
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                # Parse ollama list output
                lines = stdout.decode().strip().split('\n')
                models = []
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        # First column is model name
                        parts = line.split()
                        if parts:
                            models.append(parts[0])
                return models
            else:
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
            # Save selected model to config
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
        top_bar = self.query_one("#top-bar", TopBar)
        input_widget = top_bar.query_one(Input)
        input_widget.value = "/help"
        self.set_focus(input_widget)
        input_widget.cursor_position = len(input_widget.value)

    def action_exit_or_confirm(self) -> None:
        """Exit on double Ctrl+C."""
        self.exit()
