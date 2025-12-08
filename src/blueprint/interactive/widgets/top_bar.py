"""Top bar widget with menu buttons and command input."""

from __future__ import annotations

from typing import List

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Static


class TopBar(Widget):
    """Top bar with menu buttons, title, and command input."""

    DEFAULT_CSS = """
    TopBar {
        height: auto;
        dock: top;
        background: $panel;
    }

    TopBar Horizontal {
        height: 1;
        background: $primary;
        padding: 0;
    }

    TopBar #menu-button-left,
    TopBar #context-toggle-button {
        width: 3;
        content-align: center middle;
        background: $primary;
        color: $text;
    }

    TopBar #menu-button-left:hover,
    TopBar #context-toggle-button:hover {
        background: $primary-darken-1;
    }

    TopBar #title-status {
        width: 1fr;
        content-align: center middle;
        background: $primary;
        color: $text;
    }

    TopBar #command-input {
        height: 1;
        min-height: 1;
        max-height: 5;
        border: none;
        background: $surface;
        padding: 0 1;
    }
    """

    def __init__(self, feature_name: str = "Blueprint", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.feature_name = feature_name
        self.command_history: List[str] = []
        self.history_index = -1

    def compose(self) -> ComposeResult:
        """Compose the top bar layout."""
        with Horizontal():
            yield Static("≡", id="menu-button-left")
            yield Static(f"Blueprint - Feature: {self.feature_name}", id="title-status")
            yield Static("≡", id="context-toggle-button")
        yield Input(placeholder="Enter command (type /help for commands)", id="command-input")

    def on_mount(self) -> None:
        """Focus the input when mounted."""
        input_widget = self.query_one("#command-input", Input)
        input_widget.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Adjust input height based on line count."""
        if event.input.id != "command-input":
            return

        lines = event.value.count('\n') + 1
        new_height = min(lines, 5)  # Cap at 5 lines
        event.input.styles.height = new_height

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission."""
        if event.input.id != "command-input":
            return

        command = event.value.strip()
        if command:
            self.command_history.append(command)
            self.history_index = len(self.command_history)
            self.post_message(self.CommandSubmitted(command))

        # Reset input
        event.input.value = ""
        event.input.styles.height = 1

    async def on_click(self, event) -> None:
        """Handle clicks on buttons."""
        if event.button != 1:  # Only left clicks
            return

        # Check if click was on menu button
        try:
            if "menu-button-left" in event.style.node.id:
                self.post_message(self.MenuToggled())
                event.stop()
        except (AttributeError, TypeError):
            pass

        # Check if click was on context toggle button
        try:
            clicked_widget = self.get_widget_at(event.screen_x, event.screen_y)[0]
            if hasattr(clicked_widget, 'id'):
                if clicked_widget.id == "menu-button-left":
                    self.post_message(self.MenuToggled())
                    event.stop()
                elif clicked_widget.id == "context-toggle-button":
                    self.post_message(self.ContextToggled())
                    event.stop()
        except (AttributeError, IndexError):
            pass

    async def on_key(self, event) -> None:
        """Handle key presses for command history."""
        input_widget = self.query_one("#command-input", Input)

        if event.key == "up":
            if self.command_history and self.history_index > 0:
                self.history_index -= 1
                input_widget.value = self.command_history[self.history_index]
                input_widget.cursor_position = len(input_widget.value)
            event.prevent_default()
        elif event.key == "down":
            if self.command_history:
                if self.history_index < len(self.command_history) - 1:
                    self.history_index += 1
                    input_widget.value = self.command_history[self.history_index]
                else:
                    self.history_index = len(self.command_history)
                    input_widget.value = ""
                input_widget.cursor_position = len(input_widget.value)
            event.prevent_default()

    def update_title(self, title: str) -> None:
        """Update the title/status text."""
        title_widget = self.query_one("#title-status", Static)
        title_widget.update(title)

    class CommandSubmitted(Message):
        """Message sent when command is submitted."""

        def __init__(self, command: str) -> None:
            super().__init__()
            self.command = command

    class MenuToggled(Message):
        """Message sent when menu button is clicked."""

    class ContextToggled(Message):
        """Message sent when context toggle button is clicked."""
