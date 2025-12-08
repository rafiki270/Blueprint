"""Modal for creating a new task."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea


class NewTaskModal(ModalScreen):
    """Modal dialog for creating a new task."""

    DEFAULT_CSS = """
    NewTaskModal {
        align: center middle;
    }

    NewTaskModal > Vertical {
        width: 80;
        height: auto;
        max-height: 30;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    NewTaskModal Label {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    NewTaskModal TextArea {
        width: 100%;
        height: 15;
        border: round $primary;
        margin-bottom: 1;
    }

    NewTaskModal Grid {
        width: 100%;
        height: auto;
        grid-size: 2;
        grid-gutter: 1;
    }

    NewTaskModal Button {
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical():
            yield Label("Create New Task")
            yield TextArea(
                id="task-brief-input",
                text="",
                language=None,
            )
            with Grid():
                yield Button("Cancel", variant="default", id="cancel-button")
                yield Button("Create", variant="primary", id="create-button")

    def on_mount(self) -> None:
        """Focus the text area when mounted."""
        text_area = self.query_one("#task-brief-input", TextArea)
        text_area.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "create-button":
            text_area = self.query_one("#task-brief-input", TextArea)
            brief = text_area.text.strip()
            if brief:
                self.dismiss(brief)
            else:
                # Don't dismiss if empty
                text_area.focus()

    class TaskBriefSubmitted(Message):
        """Message sent when task brief is submitted."""

        def __init__(self, brief: str) -> None:
            super().__init__()
            self.brief = brief
