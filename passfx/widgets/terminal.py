"""System Terminal Widget for PassFX - Interactive CLI within the dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Click
from textual.widgets import Input, Label, RichLog

if TYPE_CHECKING:
    pass


class SystemTerminal(Vertical, can_focus=True):
    """Interactive terminal widget with command input and log output.

    Provides a RichLog for displaying system messages and an Input
    for accepting user commands within the main menu dashboard.
    """

    def __init__(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        """Initialize the SystemTerminal widget."""
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    def on_click(self, event: Click) -> None:
        """Focus the input when terminal is clicked."""
        self.focus_input()
        event.stop()

    def compose(self) -> ComposeResult:
        """Compose the terminal layout with output log and input row."""
        yield RichLog(
            id="terminal-output",
            markup=True,
            wrap=True,
            auto_scroll=True,
        )
        with Horizontal(id="terminal-input-row"):
            yield Label(">", id="terminal-prompt", classes="terminal-prompt")
            yield Input(
                placeholder="",
                id="terminal-input",
            )

    def write_log(self, content: str) -> None:
        """Append timestamped text to the terminal output.

        Args:
            content: The text to append to the log.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        output = self.query_one("#terminal-output", RichLog)
        output.write(f"[dim #555555][{timestamp}][/] {content}")

    def log_raw(self, content: str) -> None:
        """Append text to the terminal output without timestamp.

        Args:
            content: The text to append to the log.
        """
        output = self.query_one("#terminal-output", RichLog)
        output.write(content)

    def clear_log(self) -> None:
        """Clear all content from the terminal output."""
        output = self.query_one("#terminal-output", RichLog)
        output.clear()

    def focus_input(self) -> None:
        """Set focus to the terminal input widget."""
        input_widget = self.query_one("#terminal-input", Input)
        input_widget.focus()

    def get_input(self) -> Input:
        """Get the terminal input widget.

        Returns:
            The Input widget for command entry.
        """
        return self.query_one("#terminal-input", Input)

    def clear_input(self) -> None:
        """Clear the terminal input field."""
        input_widget = self.query_one("#terminal-input", Input)
        input_widget.value = ""
