"""Context panel widget for task and spec display."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Markdown, Static

from ...state.tasks import Task


class ContextPanel(Widget):
    """Widget for displaying task context and spec."""

    current_task: Task | None = reactive(None, layout=True)
    spec_content: str = reactive("", layout=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "Context"

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="context-scroll"):
            yield Static(id="task-info")
            yield Markdown(id="spec-viewer")

    def watch_current_task(self, task: Task) -> None:
        if task:
            info = self.query_one("#task-info", Static)
            info.update(
                f"""[bold]Current Task:[/bold] {task.title}
[dim]ID:[/dim] {task.id}
[dim]Type:[/dim] {task.type.value}
[dim]Status:[/dim] {task.status.value}

[bold]Description:[/bold]
{task.description}
"""
            )

    def watch_spec_content(self, spec: str) -> None:
        if spec is not None:
            viewer = self.query_one("#spec-viewer", Markdown)
            viewer.update(spec)

    def set_task(self, task: Task) -> None:
        self.current_task = task

    def set_spec(self, spec: str) -> None:
        self.spec_content = spec

    def clear(self) -> None:
        self.current_task = None
        self.spec_content = ""
