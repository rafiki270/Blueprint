"""Modal for selecting ollama model."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static


class ModelSelectorModal(ModalScreen):
    """Modal dialog for selecting ollama model."""

    DEFAULT_CSS = """
    ModelSelectorModal {
        align: center middle;
    }

    ModelSelectorModal > Vertical {
        width: 60;
        height: auto;
        max-height: 25;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    ModelSelectorModal Label {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    ModelSelectorModal Static {
        width: 100%;
        color: $text-muted;
        margin-bottom: 1;
    }

    ModelSelectorModal ListView {
        width: 100%;
        height: 10;
        border: round $primary;
        margin-bottom: 1;
    }

    ModelSelectorModal Button {
        width: 100%;
    }
    """

    def __init__(self, available_models: list[str], current_model: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.available_models = available_models
        self.current_model = current_model

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical():
            yield Label("Select Ollama Model")
            yield Static(f"Current: {self.current_model}")

            list_view = ListView(id="model-list")
            yield list_view

            yield Button("Cancel", variant="default", id="cancel-button")

    def on_mount(self) -> None:
        """Populate the list when mounted."""
        list_view = self.query_one("#model-list", ListView)

        if not self.available_models:
            list_view.append(ListItem(Label("[dim]No models available. Run: ollama pull <model>[/dim]")))
        else:
            for model in self.available_models:
                marker = "● " if model == self.current_model else "  "
                list_view.append(ListItem(Label(f"{marker}{model}")))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle model selection."""
        if self.available_models:
            selected_index = event.list_view.index
            if selected_index is not None and selected_index < len(self.available_models):
                selected_model = self.available_models[selected_index]
                self.dismiss(selected_model)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
