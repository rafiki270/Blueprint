"""Usage modal for interactive mode."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static

from ...utils.usage_tracker import UsageTracker


class UsageModal(ModalScreen):
    """Modal displaying usage statistics."""

    def __init__(self, usage_tracker: UsageTracker, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usage_tracker = usage_tracker

    def compose(self) -> ComposeResult:
        with Container(id="usage-modal-container"):
            with Vertical():
                yield Static("Usage Dashboard", id="modal-title")

                today_usage = self.usage_tracker.get_today_usage()
                yield Static(
                    f"""
[bold]Today's Usage[/bold]

Claude Calls: {today_usage.get('claude', 0)}
Estimated Tokens: ~{today_usage.get('claude_tokens', 0):,}

Gemini Input: {today_usage.get('gemini_input_tokens', 0):,} tokens
Gemini Output: {today_usage.get('gemini_output_tokens', 0):,} tokens

DeepSeek Calls: {today_usage.get('deepseek', 0)}

Codex Calls: {today_usage.get('codex', 0)}
""",
                    id="today-usage",
                )

                yield Static("[bold]7-Day Trend[/bold]", id="trend-title")

                table = DataTable(id="trend-table")
                table.add_columns("Model", "Calls", "Trend")

                trend_data = self.usage_tracker.get_7day_trend()
                for model, data in trend_data.items():
                    table.add_row(model, str(data.get("total_calls", 0)), data.get("trend", "—"))

                yield table

                suggestions = self.usage_tracker.get_routing_suggestions()
                if suggestions:
                    bullets = "\n".join(f"• {s}" for s in suggestions)
                    yield Static(f"[bold]Suggestions[/bold]\n{bullets}", id="suggestions")

                yield Button("Close", variant="primary", id="close-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()
