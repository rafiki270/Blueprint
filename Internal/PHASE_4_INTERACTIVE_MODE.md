# Phase 4: Interactive Mode (TUI)

## Overview
This phase implements the full-featured Textual-based TUI for interactive task management and live LLM CLI streaming.

## Dependencies
- Phase 1, 2, and 3 must be complete
- Install: `textual >= 0.47.0`

## Directory Structure
```
src/blueprint/interactive/
├── __init__.py
├── app.py
├── commands.py
└── widgets/
    ├── __init__.py
    ├── task_list.py
    ├── output_panel.py
    ├── context_panel.py
    ├── usage_modal.py
    └── command_bar.py
```

## File: `src/blueprint/interactive/widgets/task_list.py`
**Purpose**: Display tasks with status indicators

**Requirements**:
1. List all tasks with IDs, titles, and status
2. Highlight current task
3. Color-code by status (pending, in-progress, completed, blocked)
4. Update in real-time
5. Support scrolling for long lists

**Implementation outline**:
```python
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, ListView, ListItem, Label
from textual.reactive import reactive
from rich.text import Text
from typing import List
from ...state.tasks import Task, TaskStatus

class TaskListWidget(Widget):
    """Widget displaying task list with status"""

    tasks = reactive([])
    current_task_id = reactive(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "Tasks"

    def compose(self) -> ComposeResult:
        yield ListView(id="task-list-view")

    def watch_tasks(self, tasks: List[Task]):
        """Update task list when tasks change"""
        list_view = self.query_one("#task-list-view", ListView)
        list_view.clear()

        for task in tasks:
            status_symbol = self._get_status_symbol(task.status)
            status_color = self._get_status_color(task.status)

            text = Text()
            text.append(f"{status_symbol} ", style=status_color)
            text.append(f"[{task.id}] ", style="dim")
            text.append(task.title)

            if task.id == self.current_task_id:
                text.stylize("bold underline")

            item = ListItem(Label(text))
            list_view.append(item)

    @staticmethod
    def _get_status_symbol(status: TaskStatus) -> str:
        """Get symbol for task status"""
        symbols = {
            TaskStatus.PENDING: "○",
            TaskStatus.IN_PROGRESS: "◐",
            TaskStatus.BLOCKED: "⚠",
            TaskStatus.COMPLETED: "●",
            TaskStatus.SKIPPED: "⊘"
        }
        return symbols.get(status, "?")

    @staticmethod
    def _get_status_color(status: TaskStatus) -> str:
        """Get color for task status"""
        colors = {
            TaskStatus.PENDING: "gray",
            TaskStatus.IN_PROGRESS: "yellow",
            TaskStatus.BLOCKED: "red",
            TaskStatus.COMPLETED: "green",
            TaskStatus.SKIPPED: "dim"
        }
        return colors.get(status, "white")

    def update_tasks(self, tasks: List[Task], current_id: str = None):
        """Update displayed tasks"""
        self.tasks = tasks
        self.current_task_id = current_id
```

## File: `src/blueprint/interactive/widgets/output_panel.py`
**Purpose**: Stream live output from LLM CLI processes

**Requirements**:
1. Display real-time streaming output
2. Auto-scroll to bottom
3. Syntax highlighting for code blocks
4. Handle ANSI colors
5. Clear on new task
6. Save history

**Implementation outline**:
```python
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog
from textual.reactive import reactive
from rich.syntax import Syntax
from rich.panel import Panel

class OutputPanel(Widget):
    """Widget for streaming LLM output"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "Output"

    def compose(self) -> ComposeResult:
        log = RichLog(
            id="output-log",
            highlight=True,
            markup=True,
            auto_scroll=True
        )
        yield log

    def write_line(self, text: str, style: str = None):
        """Write a line to output"""
        log = self.query_one("#output-log", RichLog)
        if style:
            log.write(f"[{style}]{text}[/{style}]")
        else:
            log.write(text)

    def write_code(self, code: str, language: str = "python"):
        """Write syntax-highlighted code"""
        log = self.query_one("#output-log", RichLog)
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        log.write(syntax)

    def write_section(self, title: str, content: str):
        """Write a titled section"""
        log = self.query_one("#output-log", RichLog)
        panel = Panel(content, title=title, border_style="blue")
        log.write(panel)

    def clear(self):
        """Clear output"""
        log = self.query_one("#output-log", RichLog)
        log.clear()

    def write_error(self, error: str):
        """Write error message"""
        self.write_line(f"ERROR: {error}", style="bold red")

    def write_success(self, message: str):
        """Write success message"""
        self.write_line(f"✓ {message}", style="bold green")

    def write_warning(self, message: str):
        """Write warning message"""
        self.write_line(f"⚠ {message}", style="bold yellow")
```

## File: `src/blueprint/interactive/widgets/context_panel.py`
**Purpose**: Display spec, current task details, and context

**Requirements**:
1. Show current task description
2. Display relevant spec sections
3. Show task metadata
4. Scrollable content
5. Markdown rendering

**Implementation outline**:
```python
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Markdown, Static
from textual.containers import VerticalScroll
from textual.reactive import reactive
from ...state.tasks import Task

class ContextPanel(Widget):
    """Widget for displaying task context and spec"""

    current_task = reactive(None)
    spec_content = reactive("")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "Context"

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="context-scroll"):
            yield Static(id="task-info")
            yield Markdown(id="spec-viewer")

    def watch_current_task(self, task: Task):
        """Update when current task changes"""
        if task:
            info = self.query_one("#task-info", Static)
            info.update(f"""[bold]Current Task:[/bold] {task.title}
[dim]ID:[/dim] {task.id}
[dim]Type:[/dim] {task.type.value}
[dim]Status:[/dim] {task.status.value}

[bold]Description:[/bold]
{task.description}
""")

    def watch_spec_content(self, spec: str):
        """Update spec viewer"""
        if spec:
            viewer = self.query_one("#spec-viewer", Markdown)
            viewer.update(spec)

    def set_task(self, task: Task):
        """Set current task"""
        self.current_task = task

    def set_spec(self, spec: str):
        """Set spec content"""
        self.spec_content = spec

    def clear(self):
        """Clear context"""
        self.current_task = None
        self.spec_content = ""
```

## File: `src/blueprint/interactive/widgets/usage_modal.py`
**Purpose**: Display usage statistics modal

**Requirements**:
1. Show per-model call counts
2. Estimate token usage
3. 7-day trends
4. Routing suggestions
5. Dismissible modal overlay

**Implementation outline**:
```python
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static, Button, DataTable
from textual.containers import Container, Vertical
from datetime import datetime, timedelta
from ...utils.usage_tracker import UsageTracker

class UsageModal(ModalScreen):
    """Modal displaying usage statistics"""

    def __init__(self, usage_tracker: UsageTracker, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usage_tracker = usage_tracker

    def compose(self) -> ComposeResult:
        with Container(id="usage-modal-container"):
            with Vertical():
                yield Static("Usage Dashboard", id="modal-title")

                # Today's usage
                today_usage = self.usage_tracker.get_today_usage()
                yield Static(f"""
[bold]Today's Usage[/bold]

Claude Calls: {today_usage.get('claude', 0)}
Estimated Tokens: ~{today_usage.get('claude_tokens', 0):,}

Gemini Input: {today_usage.get('gemini_input_tokens', 0):,} tokens
Gemini Output: {today_usage.get('gemini_output_tokens', 0):,} tokens

DeepSeek Calls: {today_usage.get('deepseek', 0)}

Codex Calls: {today_usage.get('codex', 0)}
""", id="today-usage")

                # 7-day trend
                yield Static("[bold]7-Day Trend[/bold]", id="trend-title")

                table = DataTable(id="trend-table")
                table.add_columns("Model", "Calls", "Trend")

                trend_data = self.usage_tracker.get_7day_trend()
                for model, data in trend_data.items():
                    table.add_row(
                        model,
                        str(data['total_calls']),
                        data['trend']  # e.g., "↑ 15%"
                    )

                yield table

                # Routing suggestions
                suggestions = self.usage_tracker.get_routing_suggestions()
                if suggestions:
                    yield Static(f"""
[bold]Suggestions[/bold]
{chr(10).join(f"• {s}" for s in suggestions)}
""", id="suggestions")

                yield Button("Close", variant="primary", id="close-button")

    def on_button_pressed(self, event: Button.Pressed):
        """Close modal on button press"""
        self.app.pop_screen()

    def on_key(self, event):
        """Close on Escape key"""
        if event.key == "escape":
            self.app.pop_screen()
```

## File: `src/blueprint/interactive/widgets/command_bar.py`
**Purpose**: Command input and quick help

**Requirements**:
1. Text input for commands
2. Command history (↑/↓ arrows)
3. Autocomplete for commands
4. Quick help display
5. Status line

**Implementation outline**:
```python
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Input, Static
from textual.containers import Horizontal
from typing import List

class CommandBar(Widget):
    """Command input bar with autocomplete"""

    COMMANDS = [
        "/help", "/start", "/stop", "/correct", "/resume",
        "/switch-model", "/usage", "/tasks", "/done", "/delete",
        "/redo", "/missing", "/next", "/task", "/spec", "/logs", "/exit"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_history: List[str] = []
        self.history_index = -1

    def compose(self) -> ComposeResult:
        with Horizontal(id="command-bar-container"):
            yield Static("blueprint>", id="prompt")
            yield Input(
                placeholder="Enter command (type /help for commands)",
                id="command-input"
            )

    def on_input_submitted(self, event: Input.Submitted):
        """Handle command submission"""
        command = event.value.strip()
        if command:
            self.command_history.append(command)
            self.history_index = len(self.command_history)
            self.post_message(self.CommandSubmitted(command))

        # Clear input
        event.input.value = ""

    def on_key(self, event):
        """Handle key events for history navigation"""
        if event.key == "up":
            if self.command_history and self.history_index > 0:
                self.history_index -= 1
                cmd_input = self.query_one("#command-input", Input)
                cmd_input.value = self.command_history[self.history_index]
            event.prevent_default()

        elif event.key == "down":
            if self.command_history and self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                cmd_input = self.query_one("#command-input", Input)
                cmd_input.value = self.command_history[self.history_index]
            event.prevent_default()

    class CommandSubmitted(Widget.MessageSent):
        """Message sent when command is submitted"""

        def __init__(self, command: str):
            super().__init__()
            self.command = command
```

## File: `src/blueprint/interactive/widgets/__init__.py`
```python
"""Interactive mode widgets"""

from .task_list import TaskListWidget
from .output_panel import OutputPanel
from .context_panel import ContextPanel
from .usage_modal import UsageModal
from .command_bar import CommandBar

__all__ = [
    "TaskListWidget",
    "OutputPanel",
    "ContextPanel",
    "UsageModal",
    "CommandBar"
]
```

## File: `src/blueprint/interactive/commands.py`
**Purpose**: Command handlers for interactive mode

**Requirements**:
1. Parse and route commands
2. Execute command actions
3. Provide command help
4. Handle async operations
5. Update UI state

**Implementation outline**:
```python
from typing import Callable, Dict, Optional
from ..state.tasks import TaskManager, Task
from ..orchestrator.executor import TaskExecutor
from ..utils.usage_tracker import UsageTracker

class CommandHandler:
    """Handles interactive mode commands"""

    def __init__(self, task_manager: TaskManager, executor: TaskExecutor,
                 usage_tracker: UsageTracker, app):
        self.task_manager = task_manager
        self.executor = executor
        self.usage_tracker = usage_tracker
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
            "/exit": self.cmd_exit
        }

    async def handle(self, command: str):
        """Handle command"""
        parts = command.split(maxsplit=1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        handler = self.commands.get(cmd)
        if handler:
            await handler(args)
        else:
            self.app.output_panel.write_error(f"Unknown command: {cmd}")
            self.app.output_panel.write_line("Type /help for available commands")

    async def cmd_help(self, args: str):
        """Show help"""
        help_text = """
[bold]Blueprint Interactive Commands[/bold]

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
  /switch-model   Change local coder model
  /usage          Show usage dashboard
  /spec           View specification
  /logs           View logs

Other:
  /help           Show this help
  /exit           Exit Blueprint
"""
        self.app.output_panel.write_section("Help", help_text)

    async def cmd_start(self, args: str):
        """Start next task"""
        next_task = self.task_manager.get_next()
        if not next_task:
            self.app.output_panel.write_warning("No pending tasks")
            return

        self.app.output_panel.write_line(f"Starting task: {next_task.title}")
        await self.executor.execute_task(next_task)

    async def cmd_stop(self, args: str):
        """Stop current task"""
        await self.executor.stop_current_task()
        self.app.output_panel.write_warning("Task stopped")

    async def cmd_correct(self, args: str):
        """Enter correction mode"""
        self.app.output_panel.write_line("Correction mode - Enter your correction:")
        # Implementation depends on app flow
        pass

    async def cmd_resume(self, args: str):
        """Resume current task"""
        current = self.executor.get_current_task()
        if current:
            self.app.output_panel.write_line(f"Resuming: {current.title}")
            await self.executor.execute_task(current)
        else:
            self.app.output_panel.write_warning("No task to resume")

    async def cmd_switch_model(self, args: str):
        """Switch local coder model"""
        # Implementation: prompt for model selection
        pass

    async def cmd_usage(self, args: str):
        """Show usage dashboard"""
        from .widgets.usage_modal import UsageModal
        self.app.push_screen(UsageModal(self.usage_tracker))

    async def cmd_tasks(self, args: str):
        """List all tasks"""
        tasks = self.task_manager.list_all()
        self.app.task_list.update_tasks(tasks)
        self.app.output_panel.write_line(f"Total tasks: {len(tasks)}")

    async def cmd_done(self, args: str):
        """Mark task done"""
        if not args:
            self.app.output_panel.write_error("Usage: /done <task_id>")
            return

        if self.task_manager.mark_done(args):
            self.app.output_panel.write_success(f"Task {args} marked as done")
            await self.cmd_tasks("")
        else:
            self.app.output_panel.write_error(f"Task {args} not found")

    async def cmd_delete(self, args: str):
        """Delete task"""
        if not args:
            self.app.output_panel.write_error("Usage: /delete <task_id>")
            return

        if self.task_manager.delete(args):
            self.app.output_panel.write_success(f"Task {args} deleted")
            await self.cmd_tasks("")
        else:
            self.app.output_panel.write_error(f"Task {args} not found")

    async def cmd_redo(self, args: str):
        """Mark task as incomplete"""
        if not args:
            self.app.output_panel.write_error("Usage: /redo <task_id>")
            return

        if self.task_manager.mark_redo(args):
            self.app.output_panel.write_success(f"Task {args} marked as incomplete")
            await self.cmd_tasks("")
        else:
            self.app.output_panel.write_error(f"Task {args} not found")

    async def cmd_missing(self, args: str):
        """Show incomplete tasks"""
        missing = self.task_manager.get_missing()
        self.app.output_panel.write_line(f"Incomplete tasks: {len(missing)}")
        for task in missing:
            self.app.output_panel.write_line(f"  [{task.id}] {task.title}")

    async def cmd_next(self, args: str):
        """Show next task"""
        next_task = self.task_manager.get_next()
        if next_task:
            self.app.output_panel.write_line(f"Next task: [{next_task.id}] {next_task.title}")
            self.app.context_panel.set_task(next_task)
        else:
            self.app.output_panel.write_warning("No pending tasks")

    async def cmd_task(self, args: str):
        """Jump to specific task"""
        if not args:
            self.app.output_panel.write_error("Usage: /task <task_id>")
            return

        task = self.task_manager.get(args)
        if task:
            self.app.context_panel.set_task(task)
            self.app.output_panel.write_line(f"Viewing task: {task.title}")
        else:
            self.app.output_panel.write_error(f"Task {args} not found")

    async def cmd_spec(self, args: str):
        """View specification"""
        spec = self.executor.feature.load_spec()
        if spec:
            self.app.context_panel.set_spec(spec)
            self.app.output_panel.write_line("Specification loaded in context panel")
        else:
            self.app.output_panel.write_error("No specification found")

    async def cmd_logs(self, args: str):
        """View logs"""
        logs_dir = self.executor.feature_dir / "logs"
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.log"))
            self.app.output_panel.write_line(f"Log files in {logs_dir}:")
            for log_file in log_files:
                self.app.output_panel.write_line(f"  - {log_file.name}")
        else:
            self.app.output_panel.write_warning("No logs directory found")

    async def cmd_exit(self, args: str):
        """Exit Blueprint"""
        self.app.exit()
```

## File: `src/blueprint/interactive/app.py`
**Purpose**: Main Textual app orchestration

**Requirements**:
1. Multi-panel layout
2. Integrate all widgets
3. Handle async LLM streaming
4. Keybindings
5. Feature selection on startup
6. Resume detection

**Implementation outline**:
```python
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer
from textual.binding import Binding
from pathlib import Path

from .widgets import (
    TaskListWidget, OutputPanel, ContextPanel,
    UsageModal, CommandBar
)
from .commands import CommandHandler
from ..config import Config
from ..state.feature import Feature
from ..state.tasks import TaskManager
from ..models.router import ModelRouter
from ..orchestrator.executor import TaskExecutor
from ..utils.usage_tracker import UsageTracker

class BlueprintApp(App):
    """Blueprint Interactive Mode TUI"""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 3;
        grid-rows: auto 1fr auto;
    }

    #task-list-widget {
        column-span: 1;
        row-span: 2;
    }

    #output-panel {
        column-span: 2;
        row-span: 1;
    }

    #context-panel {
        column-span: 2;
        row-span: 1;
    }

    #command-bar {
        column-span: 3;
        row-span: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "stop_task", "Stop"),
        Binding("ctrl+c", "exit", "Exit"),
        Binding("ctrl+u", "show_usage", "Usage"),
        Binding("f1", "show_help", "Help"),
    ]

    def __init__(self, feature_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = Config()
        self.feature = Feature(feature_name)
        self.task_manager = TaskManager(self.feature.base_dir)
        self.router = ModelRouter(self.config)
        self.executor = TaskExecutor(
            self.task_manager,
            self.router,
            self.feature.base_dir
        )
        self.usage_tracker = UsageTracker(self.feature.base_dir)

        self.command_handler = CommandHandler(
            self.task_manager,
            self.executor,
            self.usage_tracker,
            self
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

        yield Footer()

    async def on_mount(self):
        """Initialize on mount"""
        # Load tasks
        tasks = self.task_manager.list_all()
        self.task_list.update_tasks(tasks)

        # Load spec
        spec = self.feature.load_spec()
        if spec:
            self.context_panel.set_spec(spec)

        # Check model availability
        await self.router.check_availability()

        self.output_panel.write_line(f"Blueprint Interactive Mode - Feature: {self.feature.name}")
        self.output_panel.write_line(f"Type /help for commands")

    async def on_command_bar_command_submitted(self, event: CommandBar.CommandSubmitted):
        """Handle command submission"""
        await self.command_handler.handle(event.command)

    def action_stop_task(self):
        """Stop current task (Ctrl+S)"""
        self.run_worker(self.command_handler.cmd_stop(""))

    def action_show_usage(self):
        """Show usage dashboard (Ctrl+U)"""
        self.push_screen(UsageModal(self.usage_tracker))

    def action_show_help(self):
        """Show help (F1)"""
        self.run_worker(self.command_handler.cmd_help(""))
```

## File: `src/blueprint/interactive/__init__.py`
```python
"""Interactive mode components"""

from .app import BlueprintApp

__all__ = ["BlueprintApp"]
```

## Testing Checklist
- [ ] TUI launches without errors
- [ ] Task list displays all tasks
- [ ] Output panel streams live content
- [ ] Context panel shows spec and task details
- [ ] Commands execute correctly
- [ ] Usage modal displays statistics
- [ ] Keybindings work (Ctrl+S, Ctrl+U, F1)
- [ ] Command history works (↑/↓)
- [ ] Process can be stopped mid-execution
- [ ] Layout is responsive

## Dependencies
Add to requirements/pyproject.toml:
- textual >= 0.47.0
- rich >= 13.0.0

## Success Criteria
- Full-featured TUI runs smoothly
- All commands work as specified
- Real-time streaming works without blocking
- UI updates reflect state changes
- Modal overlays work correctly
- Keyboard shortcuts function properly
- App can be cleanly exited
