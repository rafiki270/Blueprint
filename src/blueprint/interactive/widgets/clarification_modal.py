"""Modal dialog to collect clarifications and optional file paths."""

from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TextArea


class ClarificationModal(ModalScreen[Optional[dict]]):
    """Collect clarifying answers and extra file paths for Claude."""

    DEFAULT_CSS = """
    ClarificationModal {
        align: center middle;
    }

    ClarificationModal > Vertical {
        width: 90%;
        height: auto;
        max-height: 30;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    ClarificationModal Label {
        width: 100%;
        content-align: left middle;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    ClarificationModal #questions-display {
        width: 100%;
        padding: 1;
        border: tall $primary;
        background: $surface;
        margin-bottom: 1;
    }

    ClarificationModal TextArea {
        width: 100%;
        height: 15;
        border: round $primary;
        margin-bottom: 1;
    }

    ClarificationModal Input {
        width: 100%;
        border: round $primary;
        height: 3;
        padding: 0 1;
        margin-bottom: 1;
    }

    ClarificationModal Grid {
        width: 100%;
        height: auto;
        grid-size: 2;
        grid-gutter: 1;
        margin-top: 1;
    }

    ClarificationModal Button {
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("escape", "skip", "Skip"),
        Binding("ctrl+enter", "submit", "Submit"),
        Binding("meta+enter", "submit", "Submit"),
    ]

    def __init__(self, questions_text: str) -> None:
        super().__init__()
        self.questions_text = questions_text

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical():
            yield Label("Claude needs clarifications. Answer below (free-form).")
            yield Static(self.questions_text, id="questions-display")
            yield TextArea(id="clarifications-input", text="", language=None)
            yield Label("Optional: comma-separated file paths to include (relative to repo root).")
            yield Input(placeholder="docs/architecture.md, src/config.py", id="files-input")
            with Grid(id="clarification-actions"):
                yield Button("Skip (Esc)", variant="default", id="skip-button")
                yield Button("Submit (Ctrl+Enter)", variant="primary", id="submit-button")

    def on_mount(self) -> None:
        text_area = self.query_one("#clarifications-input", TextArea)
        text_area.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "skip-button":
            self._skip()
        elif event.button.id == "submit-button":
            self._submit()

    def action_submit(self) -> None:
        """Keyboard shortcut to submit clarifications."""
        self._submit()

    def action_skip(self) -> None:
        """Keyboard shortcut to skip clarifications."""
        self._skip()

    def _submit(self) -> None:
        """Collect answers/files and close the modal."""
        text_area = self.query_one("#clarifications-input", TextArea)
        files_input = self.query_one("#files-input", Input)
        answers = text_area.text.strip()
        raw_files = files_input.value.strip() if files_input.value else ""
        files = [f.strip() for f in raw_files.split(",") if f.strip()]
        self.dismiss({"answers": answers, "files": files} if (answers or files) else None)

    def _skip(self) -> None:
        """Dismiss the modal without sending clarifications."""
        self.dismiss(None)
