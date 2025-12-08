"""Command input bar with history."""

from __future__ import annotations

from typing import List

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Static


class CommandBar(Widget):
    """Command input bar with autocomplete-style hints."""

    COMMANDS = [
        "/help",
        "/start",
        "/stop",
        "/correct",
        "/resume",
        "/switch-model",
        "/usage",
        "/tasks",
        "/done",
        "/delete",
        "/redo",
        "/missing",
        "/next",
        "/task",
        "/spec",
        "/logs",
        "/exit",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_history: List[str] = []
        self.history_index = -1

    def compose(self) -> ComposeResult:
        with Horizontal(id="command-bar-container"):
            yield Static("blueprint>", id="prompt")
            yield Input(placeholder="Enter command (type /help for commands)", id="command-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        if command:
            self.command_history.append(command)
            self.history_index = len(self.command_history)
            self.post_message(self.CommandSubmitted(command))
        event.input.value = ""

    def on_key(self, event) -> None:
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

    class CommandSubmitted(Message):
        """Message sent when command is submitted."""

        def __init__(self, command: str) -> None:
            super().__init__()
            self.command = command
