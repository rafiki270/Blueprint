"""Task list widget for interactive mode."""

from __future__ import annotations

from typing import List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label, ListItem, ListView

from ...state.tasks import Task, TaskStatus


class TaskListWidget(Widget):
    """Widget displaying task list with status."""

    DEFAULT_CSS = """
    TaskListWidget Vertical {
        height: 100%;
    }

    TaskListWidget Button {
        width: 100%;
        margin: 0 0 1 0;
    }

    TaskListWidget ListView {
        height: 1fr;
    }
    """

    tasks: List[Task] = reactive([], layout=True)
    current_task_id: Optional[str] = reactive(None, layout=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "Tasks"

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Button("+ New Task", variant="success", id="new-task-button")
            yield ListView(id="task-list-view")

    def watch_tasks(self, tasks: List[Task]) -> None:
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
        symbols = {
            TaskStatus.PENDING: "○",
            TaskStatus.IN_PROGRESS: "◐",
            TaskStatus.BLOCKED: "⚠",
            TaskStatus.COMPLETED: "●",
            TaskStatus.SKIPPED: "⊘",
        }
        return symbols.get(status, "?")

    @staticmethod
    def _get_status_color(status: TaskStatus) -> str:
        colors = {
            TaskStatus.PENDING: "#888888",
            TaskStatus.IN_PROGRESS: "yellow",
            TaskStatus.BLOCKED: "red",
            TaskStatus.COMPLETED: "green",
            TaskStatus.SKIPPED: "#555555",
        }
        return colors.get(status, "white")

    def update_tasks(self, tasks: List[Task], current_id: Optional[str] = None) -> None:
        self.tasks = tasks
        self.current_task_id = current_id

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press for new task."""
        if event.button.id == "new-task-button":
            self.post_message(self.NewTaskRequested())
            event.stop()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle task selection from list."""
        if event.list_view.index is not None and event.list_view.index < len(self.tasks):
            selected_task = self.tasks[event.list_view.index]
            self.post_message(self.TaskSelected(selected_task))

    class NewTaskRequested(Message):
        """Message sent when new task button is pressed."""

    class TaskSelected(Message):
        """Message sent when a task is selected from the list."""

        def __init__(self, task: Task) -> None:
            super().__init__()
            self.task = task
