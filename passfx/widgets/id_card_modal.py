"""Reusable ID Card Modal Component for PassFX."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


@dataclass
class IDCardField:
    """Configuration for a field section in the ID card."""

    label: str
    value: str
    value_color: str = "#e2e8f0"


@dataclass
class IDCardButton:
    """Configuration for a button in the ID card modal."""

    label: str
    id: str
    callback: Callable[[], None] | None = None
    is_primary: bool = False


@dataclass
class IDCardColors:
    """Color configuration for the ID card modal."""

    # Border and accent color
    border: str = "#00d4ff"
    # Background colors
    card_bg: str = "#0a0e27"
    section_border: str = "#475569"
    # Text colors
    title_bg: str = "#00d4ff"
    title_fg: str = "#000000"
    label_dim: str = "#64748b"
    value_fg: str = "#f8fafc"
    accent: str = "#22c55e"
    muted: str = "#94a3b8"
    # Button colors (primary)
    btn_primary_bg: str = "#0a2e1a"
    btn_primary_fg: str = "#22c55e"
    btn_primary_hover_bg: str = "#22c55e"
    btn_primary_hover_fg: str = "#0f172a"
    # Button colors (secondary)
    btn_secondary_bg: str = "#1e293b"
    btn_secondary_fg: str = "#94a3b8"
    btn_secondary_hover_bg: str = "#94a3b8"
    btn_secondary_hover_fg: str = "#0f172a"


@dataclass
class IDCardConfig:
    """Full configuration for an ID card modal."""

    title: str
    modal_id: str
    card_id: str
    buttons_id: str
    width: int = 96
    colors: IDCardColors = field(default_factory=IDCardColors)
    fields: list[IDCardField] = field(default_factory=list)
    buttons: list[IDCardButton] = field(default_factory=list)
    footer_left: str = ""
    footer_right: str = ""
    security_bar: str | None = None
    security_label: str | None = None
    security_color: str | None = None


class IDCardModal(ModalScreen[None]):
    """Reusable ID Card Modal with configurable colors and content."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]

    def __init__(self, config: IDCardConfig) -> None:
        super().__init__()
        self.config = config
        self._button_callbacks: dict[str, Callable[[], None]] = {}

        # Register button callbacks
        for btn in config.buttons:
            if btn.callback:
                self._button_callbacks[btn.id] = btn.callback

    def _build_border_top(self) -> str:
        """Build the top border line."""
        c = self.config.colors
        inner_width = self.config.width - 2
        return f"[bold {c.border}]╔{'═' * inner_width}╗[/]"

    def _build_border_bottom(self) -> str:
        """Build the bottom border line."""
        c = self.config.colors
        inner_width = self.config.width - 2
        return f"[bold {c.border}]╚{'═' * inner_width}╝[/]"

    def _build_divider(self) -> str:
        """Build a horizontal divider line."""
        c = self.config.colors
        inner_width = self.config.width - 2
        return f"[bold {c.border}]╠{'═' * inner_width}╣[/]"

    def _build_empty_row(self) -> str:
        """Build an empty row with side borders."""
        c = self.config.colors
        inner_width = self.config.width - 2
        return f"[bold {c.border}]║[/]{' ' * inner_width}[bold {c.border}]║[/]"

    def _build_title_row(self) -> str:
        """Build the title row."""
        c = self.config.colors
        inner_width = self.config.width - 2
        title_text = f" {self.config.title} "
        padding = inner_width - len(title_text) - 2
        return f"[bold {c.border}]║[/]  [on {c.title_bg}][bold {c.title_fg}]{title_text}[/]{' ' * padding}[bold {c.border}]║[/]"

    def _build_label_row(self, label: str, value: str, value_color: str | None = None) -> str:
        """Build a label: value row."""
        c = self.config.colors
        inner_width = self.config.width - 2
        color = value_color or c.value_fg
        content = f"  [dim {c.label_dim}]{label}:[/] [bold {color}]{value}"
        # Calculate visible length (without markup)
        visible_len = len(f"  {label}: {value}")
        padding = inner_width - visible_len - 1
        return f"[bold {c.border}]║[/]{content}{' ' * padding}[bold {c.border}]║[/]"

    def _build_section_header(self, label: str) -> str:
        """Build a section header with inner borders."""
        c = self.config.colors
        inner_width = self.config.width - 6  # Account for outer borders and padding
        label_text = f"─ {label} "
        dashes = inner_width - len(label_text) - 1
        return f"[bold {c.border}]║[/]  [dim {c.section_border}]┌{label_text}{'─' * dashes}┐[/]  [bold {c.border}]║[/]"

    def _build_section_content(self, value: str, value_color: str | None = None) -> str:
        """Build a section content row."""
        c = self.config.colors
        inner_width = self.config.width - 6
        color = value_color or c.value_fg
        content_width = inner_width - 5  # Account for │ ► and │
        return f"[bold {c.border}]║[/]  [dim {c.section_border}]│[/] [{c.accent}]►[/] [bold {color}]{value:<{content_width}}[/] [dim {c.section_border}]│[/]  [bold {c.border}]║[/]"

    def _build_section_footer(self) -> str:
        """Build a section footer with inner borders."""
        c = self.config.colors
        inner_width = self.config.width - 6
        return f"[bold {c.border}]║[/]  [dim {c.section_border}]└{'─' * (inner_width - 1)}┘[/]  [bold {c.border}]║[/]"

    def _build_footer_row(self) -> str:
        """Build the footer row with left and right content."""
        c = self.config.colors
        inner_width = self.config.width - 2
        left = f"  [dim {c.section_border}]ID:[/] [{c.muted}]{self.config.footer_left}[/]"
        right = f"[dim {c.section_border}]ISSUED:[/] [{c.muted}]{self.config.footer_right}[/]"
        # Calculate padding between left and right
        left_visible = len(f"  ID: {self.config.footer_left}")
        right_visible = len(f"ISSUED: {self.config.footer_right}")
        padding = inner_width - left_visible - right_visible - 3
        return f"[bold {c.border}]║[/]{left}{' ' * padding}{right}  [bold {c.border}]║[/]"

    def _build_security_row(self) -> str:
        """Build the security bar row."""
        c = self.config.colors
        inner_width = self.config.width - 2
        bar = self.config.security_bar or ""
        label = self.config.security_label or ""
        color = self.config.security_color or c.accent
        content = f"  [dim {c.label_dim}]SECURITY:[/] {bar} [{color}]{label}"
        # Rough padding calculation
        visible_len = len(f"  SECURITY:  {label}") + 5  # 5 for bar blocks
        padding = inner_width - visible_len - 10
        return f"[bold {c.border}]║[/]{content}{' ' * max(0, padding)}[bold {c.border}]║[/]"

    def compose(self) -> ComposeResult:
        """Compose the ID card modal."""
        with Vertical(id=self.config.modal_id):
            with Vertical(id=self.config.card_id):
                # Top border
                yield Static(self._build_border_top(), classes="id-card-line")

                # Title row
                yield Static(self._build_title_row(), classes="id-card-line")

                # Divider
                yield Static(self._build_divider(), classes="id-card-line")

                # Fields
                for i, fld in enumerate(self.config.fields):
                    # Add spacer before sections (except first)
                    if i > 0:
                        yield Static(self._build_empty_row(), classes="id-card-line")

                    # Section with box
                    yield Static(self._build_section_header(fld.label), classes="id-card-line")
                    yield Static(
                        self._build_section_content(fld.value, fld.value_color),
                        classes="id-card-line",
                    )
                    yield Static(self._build_section_footer(), classes="id-card-line")

                # Security bar if provided
                if self.config.security_bar:
                    yield Static(self._build_empty_row(), classes="id-card-line")
                    yield Static(self._build_security_row(), classes="id-card-line")

                # Footer divider and content
                yield Static(self._build_divider(), classes="id-card-line")
                yield Static(self._build_footer_row(), classes="id-card-line")

                # Bottom border
                yield Static(self._build_border_bottom(), classes="id-card-line")

            # Buttons
            with Horizontal(id=self.config.buttons_id):
                for btn in self.config.buttons:
                    classes = "modal-btn-primary" if btn.is_primary else "modal-btn-secondary"
                    yield Button(btn.label, id=btn.id, classes=classes)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        btn_id = event.button.id
        if btn_id in self._button_callbacks:
            self._button_callbacks[btn_id]()
        elif btn_id and btn_id.endswith("-close"):
            self.dismiss(None)

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)
