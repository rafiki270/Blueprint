"""Task list widget for interactive mode."""

from __future__ import annotations

from typing import List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView

from ...state.tasks import Task, TaskStatus


class TaskListWidget(Widget):
    """Widget displaying task list with status."""

    tasks: List[Task] = reactive([], layout=True)
    current_task_id: Optional[str] = reactive(None, layout=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "Tasks"

    def compose(self) -> ComposeResult:
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
            TaskStatus.PENDING: "gray",
            TaskStatus.IN_PROGRESS: "yellow",
            TaskStatus.BLOCKED: "red",
            TaskStatus.COMPLETED: "green",
            TaskStatus.SKIPPED: "dim",
        }
        return colors.get(status, "white")

    def update_tasks(self, tasks: List[Task], current_id: Optional[str] = None) -> None:
        self.tasks = tasks
        self.current_task_id = current_id
