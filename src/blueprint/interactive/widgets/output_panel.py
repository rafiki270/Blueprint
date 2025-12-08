"""Output panel widget for streaming LLM output."""

from __future__ import annotations

from rich.panel import Panel
from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog


class OutputPanel(Widget):
    """Widget for streaming LLM output."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "Output"

    def compose(self) -> ComposeResult:
        log = RichLog(id="output-log", highlight=True, markup=True, auto_scroll=True)
        yield log

    def write_line(self, text: str, style: str | None = None) -> None:
        log = self.query_one("#output-log", RichLog)
        if style:
            log.write(f"[{style}]{text}[/{style}]")
        else:
            log.write(text)

    def write_code(self, code: str, language: str = "python") -> None:
        log = self.query_one("#output-log", RichLog)
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        log.write(syntax)

    def write_section(self, title: str, content: str) -> None:
        log = self.query_one("#output-log", RichLog)
        panel = Panel(content, title=title, border_style="blue")
        log.write(panel)

    def clear(self) -> None:
        log = self.query_one("#output-log", RichLog)
        log.clear()

    def write_error(self, error: str) -> None:
        self.write_line(f"ERROR: {error}", style="bold red")

    def write_success(self, message: str) -> None:
        self.write_line(f"✓ {message}", style="bold green")

    def write_warning(self, message: str) -> None:
        self.write_line(f"⚠ {message}", style="bold yellow")
