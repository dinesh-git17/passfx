"""Reusable keycap footer widget for PassFX screens.

Provides consistent keyboard hint display across dual-pane screens.
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

# Global search shortcut - single source of truth for all footer displays
GLOBAL_SEARCH_HINT: tuple[str, str] = ("^K", "Search")


class KeycapHint(Horizontal):
    """Single keycap hint showing a key and its action."""

    DEFAULT_CSS = """
    KeycapHint {
        width: auto;
        height: auto;
    }
    """

    def __init__(self, key: str, label: str, **kwargs: Any) -> None:
        """Initialize keycap hint.

        Args:
            key: The key or key combination (e.g., "↑↓", "ESC", "TAB").
            label: The action description (e.g., "Navigate", "Close").
            **kwargs: Additional arguments passed to Horizontal.
        """
        super().__init__(classes="keycap-group", **kwargs)
        self._key = key
        self._label = label

    def compose(self) -> ComposeResult:
        """Compose the keycap hint."""
        yield Static(f"[bold #00FFFF] {self._key} [/]", classes="keycap")
        yield Static(f"[#666666]{self._label}[/]", classes="keycap-label")


class KeycapFooter(Horizontal):
    """Footer with keyboard hints for dual-pane screens."""

    DEFAULT_CSS = """
    KeycapFooter {
        width: 100%;
        height: auto;
    }
    """

    def __init__(
        self,
        hints: list[tuple[str, str]],
        footer_id: str | None = None,
        label: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize keycap footer.

        Args:
            hints: List of (key, label) tuples for keycap hints.
            footer_id: Optional ID for the footer container.
            label: Optional label to show before keycaps.
            **kwargs: Additional arguments passed to Horizontal.
        """
        super().__init__(id=footer_id, **kwargs)
        self._hints = hints
        self._label = label

    def compose(self) -> ComposeResult:
        """Compose the footer with keycap hints."""
        if self._label:
            yield Static(self._label, id=f"{self.id}-label" if self.id else None)

        for key, label in self._hints:
            yield KeycapHint(key, label)
