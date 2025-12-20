"""Vault Interceptor - Global search HUD for PassFX.

A full-screen, state-based search interface with Vim-style keyboard navigation.
Implements explicit Search Mode and Command Mode with blind copy operations.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

from rich.console import RenderableType
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.color import Color
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from passfx.core.models import (
    CreditCard,
    EmailCredential,
    EnvEntry,
    NoteEntry,
    PhoneCredential,
    RecoveryEntry,
)
from passfx.search.engine import SearchIndex, SearchResult
from passfx.utils.clipboard import copy_to_clipboard

if TYPE_CHECKING:
    from collections.abc import Callable

# Maximum visible results in the list (8 results * 2 lines = 16 lines max-height)
MAX_VISIBLE_RESULTS = 8

# Default theme color (Cyan)
DEFAULT_THEME_COLOR = Color.parse("#00FFFF")


class InterceptorMode(Enum):
    """Explicit state for the Vault Interceptor."""

    SEARCH = auto()  # Input focused, typing filters results
    COMMAND = auto()  # List focused, single-key commands


class InterceptorResultItem(Static):
    """A single search result row in the Interceptor HUD.

    Renders category badge, primary text, and secondary text.
    Supports selected/dimmed states for Command/Search mode.
    """

    is_selected: reactive[bool] = reactive(False)
    is_dimmed: reactive[bool] = reactive(False)

    def __init__(
        self, theme_color: Color = DEFAULT_THEME_COLOR, **kwargs: object
    ) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._theme_color = theme_color
        self._icon = ""
        self._primary = ""
        self._secondary = ""
        self._cred_type = ""

    def set_result(
        self,
        result: SearchResult | None,
        selected: bool = False,
        dimmed: bool = False,
    ) -> None:
        """Update the result item content."""
        if result is None:
            self._icon = ""
            self._primary = ""
            self._secondary = ""
            self._cred_type = ""
        else:
            self._icon = result.icon
            self._primary = result.primary_text
            self._secondary = self._format_secondary(result)
            self._cred_type = result.cred_type
        self.is_selected = selected
        self.is_dimmed = dimmed
        self.update(self._build_content())

    def _format_secondary(self, result: SearchResult) -> str:
        """Format secondary text based on credential type - security safe."""
        cred_type = result.cred_type

        # Env vars: show $VAR_NAME pattern, not content
        if cred_type == "env":
            return result.secondary_text or ""

        # Notes: always show [Encrypted]
        if cred_type == "note":
            return "[Encrypted]"

        # Recovery: show title only
        if cred_type == "recovery":
            return ""

        # Others: show secondary text (email, phone, cardholder - safe)
        return result.secondary_text or ""

    def _build_content(self) -> RenderableType:
        """Render the result item as Rich text."""
        if not self._primary:
            return Text("")

        line = Text()
        theme_hex = self._theme_color.hex

        # Determine styles based on state
        if self.is_selected and not self.is_dimmed:
            # Active selection in Command mode
            badge_style = f"bold black on {theme_hex}"
            primary_style = "bold black"
            secondary_style = "#333333"
        elif self.is_selected and self.is_dimmed:
            # Dimmed selection in Search mode (outlined effect)
            badge_style = f"bold {theme_hex}"
            primary_style = f"dim {theme_hex}"
            secondary_style = "dim #666666"
        else:
            # Normal unselected row
            badge_style = f"bold {theme_hex}"
            primary_style = "#e0e0e0"
            secondary_style = "#666666"

        # Category badge [KEY] [PIN] [ENV] etc.
        line.append(f"[{self._icon}]", style=badge_style)
        line.append("  ")

        # Primary text
        line.append(self._primary, style=primary_style)

        # Secondary text
        if self._secondary:
            line.append("  ")
            line.append(self._secondary, style=secondary_style)

        return line

    def watch_is_selected(self, _selected: bool) -> None:
        """Update styling when selection changes."""
        self._update_selection_class()
        self.update(self._build_content())

    def watch_is_dimmed(self, _dimmed: bool) -> None:
        """Update styling when dimmed state changes."""
        self._update_selection_class()
        self.update(self._build_content())

    def _update_selection_class(self) -> None:
        """Update CSS class based on selection and mode.

        Full highlight (-selected) only in Command mode.
        In Search mode, selection is shown via text styling only.
        """
        if self.is_selected and not self.is_dimmed:
            self.add_class("-selected")
        else:
            self.remove_class("-selected")


class InterceptorResultsContainer(Vertical):
    """Container for search results with reverse column layout.

    Results render above the input bar, with newest/best at bottom.
    """

    results: reactive[list[SearchResult]] = reactive([])
    selected_index: reactive[int] = reactive(0)
    mode: reactive[InterceptorMode] = reactive(InterceptorMode.SEARCH)

    def __init__(
        self, theme_color: Color = DEFAULT_THEME_COLOR, **kwargs: object
    ) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._theme_color = theme_color

    def compose(self) -> ComposeResult:
        """Pre-allocate result item widgets."""
        for _ in range(MAX_VISIBLE_RESULTS):
            yield InterceptorResultItem(
                theme_color=self._theme_color,
                classes="interceptor-result-item",
            )

    def watch_results(self, _results: list[SearchResult]) -> None:
        """Update result items when results change."""
        self._update_items()

    def watch_selected_index(self, _selected_index: int) -> None:
        """Update selection when index changes."""
        self._update_items()

    def watch_mode(self, _mode: InterceptorMode) -> None:
        """Update dimming when mode changes."""
        self._update_items()

    def _update_items(self) -> None:
        """Update all result item widgets with current data."""
        items = list(self.query(InterceptorResultItem))
        is_dimmed = self.mode == InterceptorMode.SEARCH

        for i, item in enumerate(items):
            if i < len(self.results):
                item.set_result(
                    self.results[i],
                    selected=i == self.selected_index,
                    dimmed=is_dimmed,
                )
                item.display = True
            else:
                item.set_result(None)
                item.display = False


class VaultInterceptorScreen(ModalScreen[SearchResult | None]):
    """Vault Interceptor - Full-screen search HUD with state-based navigation.

    Features:
    - Full-screen overlay with bottom-anchored input
    - Explicit Search Mode and Command Mode
    - Vim-style single-key commands (c, u, e)
    - Blind copy operations (no secret reveal)
    - Themeable accent color
    """

    # Styling is handled by passfx.tcss for proper CSS specificity
    DEFAULT_CSS = ""

    BINDINGS = [
        Binding("escape", "handle_escape", "Back/Close", priority=True),
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("tab", "enter_command_mode", "Command Mode", show=False),
        Binding("enter", "select_result", "Select", show=False),
    ]

    # Reactive state
    mode: reactive[InterceptorMode] = reactive(InterceptorMode.SEARCH)
    _esc_pending: reactive[bool] = reactive(False)

    def __init__(
        self,
        search_index: SearchIndex | None = None,
        on_select: Callable[[SearchResult], None] | None = None,
        theme_color: Color | None = None,
        **kwargs: object,
    ) -> None:
        """Initialize the Vault Interceptor.

        Args:
            search_index: Pre-built search index from vault.
            on_select: Callback when a result is selected.
            theme_color: Accent color (default: Cyan, use Red for panic mode).
        """
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._search_index = search_index
        self._on_select = on_select
        self._theme_color = theme_color or DEFAULT_THEME_COLOR

    def compose(self) -> ComposeResult:
        """Create the Interceptor HUD layout.

        Layout: Header -> Input (fixed) -> Results (grows down) -> Status
        Input stays in place as results appear/disappear below it.
        """
        with Vertical(id="interceptor-container"):
            yield Static(":: SYSTEM INTERCEPTOR ::", id="interceptor-header")
            yield Static("", id="mode-indicator")
            with Horizontal(id="interceptor-input-row"):
                yield Static("▶", id="interceptor-prompt")
                yield Input(placeholder="search...", id="interceptor-input")
            yield InterceptorResultsContainer(
                theme_color=self._theme_color,
                id="interceptor-results",
            )
            yield Static(self._get_status_text(), id="interceptor-status")

    def on_mount(self) -> None:
        """Focus the search input on mount."""
        self._focus_input()
        self._update_mode_indicator()

    def _focus_input(self) -> None:
        """Focus the search input widget."""
        try:
            search_input = self.query_one("#interceptor-input", Input)
            search_input.focus()
        except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
            pass  # Non-critical UI focus, fail silently

    def _blur_input(self) -> None:
        """Blur the search input so keys go to screen."""
        try:
            search_input = self.query_one("#interceptor-input", Input)
            search_input.blur()
            # Focus the screen itself to receive key events
            self.focus()
        except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
            pass  # Non-critical UI blur, fail silently

    def _get_status_text(self) -> str:
        """Get status bar text based on current mode."""
        if self.mode == InterceptorMode.SEARCH:
            return "[dim]ESC[/] close  [dim]↓/TAB[/] command mode  [dim]ENTER[/] open"
        return "[dim]ESC[/] search  [dim]↑↓[/] navigate  [dim]c[/] copy  [dim]u[/] user  [dim]e[/] open"

    def _update_status(self) -> None:
        """Update status bar text."""
        try:
            status = self.query_one("#interceptor-status", Static)
            status.update(self._get_status_text())
        except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
            pass  # Non-critical UI update, fail silently

    def _update_mode_indicator(self) -> None:
        """Update mode indicator in header."""
        try:
            indicator = self.query_one("#mode-indicator", Static)
            if self.mode == InterceptorMode.SEARCH:
                indicator.update("[dim]SEARCH[/]")
            else:
                indicator.update(f"[bold {self._theme_color.hex}]COMMAND[/]")
        except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
            pass  # Non-critical UI update, fail silently

    def watch_mode(self, mode: InterceptorMode) -> None:
        """Handle mode changes."""
        # Sync mode to results container
        try:
            container = self.query_one(
                "#interceptor-results", InterceptorResultsContainer
            )
            container.mode = mode
        except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
            pass  # Container may not exist during initialization

        self._update_status()
        self._update_mode_indicator()

        # Only reset _esc_pending when entering COMMAND mode, not when leaving.
        # This preserves the double-ESC pattern: first ESC from COMMAND returns
        # to SEARCH with _esc_pending=True, second ESC in SEARCH closes modal.
        if mode == InterceptorMode.COMMAND:
            self._esc_pending = False

        if mode == InterceptorMode.SEARCH:
            self._focus_input()
        else:
            # Command mode: blur input so keys go to screen
            self._blur_input()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id != "interceptor-input":
            return

        query = event.value.strip()
        self._perform_search(query)

        # Typing cancels double-ESC pattern - user is actively engaging
        self._esc_pending = False

        # Reset to search mode when typing
        if self.mode == InterceptorMode.COMMAND:
            self.mode = InterceptorMode.SEARCH

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in search input - select current result."""
        if event.input.id != "interceptor-input":
            return

        self.action_select_result()

    def _perform_search(self, query: str) -> None:
        """Execute search and update results."""
        container = self._get_results_container()

        if not self._search_index or not query:
            container.results = []
        else:
            container.results = self._search_index.search(
                query, max_results=MAX_VISIBLE_RESULTS
            )

        container.selected_index = 0

    def _get_results_container(self) -> InterceptorResultsContainer:
        """Get the results container."""
        return self.query_one("#interceptor-results", InterceptorResultsContainer)

    def _get_input(self) -> Input:
        """Get the search input widget."""
        return self.query_one("#interceptor-input", Input)

    def _get_selected_result(self) -> SearchResult | None:
        """Get the currently selected result."""
        container = self._get_results_container()
        if not container.results:
            return None
        if 0 <= container.selected_index < len(container.results):
            return container.results[container.selected_index]
        return None

    # --- Key Handling ---

    def on_key(self, event: Key) -> None:
        """Handle key events for state-based navigation."""
        # Only intercept in Command mode for single-key commands
        if self.mode != InterceptorMode.COMMAND:
            return

        key = event.key

        # Single-key commands in Command mode
        if key == "c":
            self._copy_primary_secret()
            event.prevent_default()
            event.stop()
        elif key == "u":
            self._copy_secondary_field()
            event.prevent_default()
            event.stop()
        elif key == "e":
            self.action_select_result()
            event.prevent_default()
            event.stop()
        elif key.isalpha() and len(key) == 1:
            # Block other letter keys in Command mode (only ESC returns to search)
            event.prevent_default()
            event.stop()

    def action_handle_escape(self) -> None:
        """Handle escape key based on mode and state.

        ESC behavior:
        - COMMAND mode (first ESC): Return to SEARCH, set _esc_pending=True
        - COMMAND mode (_esc_pending): Close modal (double-ESC in COMMAND)
        - SEARCH mode (_esc_pending): Close modal (double-ESC from COMMAND)
        - SEARCH mode (has text): Clear input
        - SEARCH mode (empty): Close modal
        """
        if self.mode == InterceptorMode.COMMAND:
            if self._esc_pending:
                # Double escape: close
                self.dismiss(None)
            else:
                # First escape: back to search mode
                self._esc_pending = True
                self.mode = InterceptorMode.SEARCH
        else:
            # Search mode
            if self._esc_pending:
                # Double-ESC from COMMAND mode: close immediately
                self.dismiss(None)
                return

            try:
                input_widget = self._get_input()
                if input_widget.value:
                    # Clear input first
                    input_widget.value = ""
                else:
                    # Empty input: close
                    self.dismiss(None)
            except Exception:  # pylint: disable=broad-exception-caught
                self.dismiss(None)

    def action_move_up(self) -> None:
        """Move selection up."""
        container = self._get_results_container()
        if container.results and container.selected_index > 0:
            container.selected_index -= 1

    def action_move_down(self) -> None:
        """Move selection down (also enters command mode from search)."""
        container = self._get_results_container()

        if self.mode == InterceptorMode.SEARCH and container.results:
            # Enter command mode
            self.mode = InterceptorMode.COMMAND
        elif self.mode == InterceptorMode.COMMAND:
            if (
                container.results
                and container.selected_index < len(container.results) - 1
            ):
                container.selected_index += 1

    def action_enter_command_mode(self) -> None:
        """Enter command mode (Tab key)."""
        container = self._get_results_container()
        if container.results:
            self.mode = InterceptorMode.COMMAND

    def action_select_result(self) -> None:
        """Select the current result and navigate."""
        result = self._get_selected_result()

        if result is None:
            # No selection, just close
            return

        if self._on_select:
            self._on_select(result)
        self.dismiss(result)

    # --- Copy Operations (Blind Copy) ---

    def _copy_primary_secret(self) -> None:
        """Copy the primary secret field (password, content, card number)."""
        result = self._get_selected_result()
        if result is None:
            return

        secret = self._get_primary_secret(result)
        if secret:
            if copy_to_clipboard(secret, auto_clear=True):
                self.notify("Copied to clipboard", severity="information", timeout=2)
            else:
                self.notify("Clipboard unavailable", severity="warning", timeout=2)

    def _copy_secondary_field(self) -> None:
        """Copy the secondary field (email, phone, username)."""
        result = self._get_selected_result()
        if result is None:
            return

        value = self._get_secondary_field(result)
        if value:
            if copy_to_clipboard(value, auto_clear=True):
                self.notify("Copied to clipboard", severity="information", timeout=2)
            else:
                self.notify("Clipboard unavailable", severity="warning", timeout=2)

    def _get_primary_secret(self, result: SearchResult) -> str | None:
        """Extract primary secret from credential - NEVER display this."""
        cred = result.credential
        cred_type = result.cred_type

        if cred_type == "email" and isinstance(cred, EmailCredential):
            return cred.password
        if cred_type == "phone" and isinstance(cred, PhoneCredential):
            return cred.password
        if cred_type == "card" and isinstance(cred, CreditCard):
            return cred.card_number
        if cred_type == "env" and isinstance(cred, EnvEntry):
            return cred.content
        if cred_type == "recovery" and isinstance(cred, RecoveryEntry):
            return cred.content
        if cred_type == "note" and isinstance(cred, NoteEntry):
            return cred.content

        return None

    def _get_secondary_field(self, result: SearchResult) -> str | None:
        """Extract secondary field from credential - safe to reference."""
        cred = result.credential
        cred_type = result.cred_type

        if cred_type == "email" and isinstance(cred, EmailCredential):
            return cred.email
        if cred_type == "phone" and isinstance(cred, PhoneCredential):
            return cred.phone
        if cred_type == "card" and isinstance(cred, CreditCard):
            return cred.cardholder_name
        if cred_type == "env" and isinstance(cred, EnvEntry):
            return cred.filename
        if cred_type == "recovery" and isinstance(cred, RecoveryEntry):
            return cred.title
        if cred_type == "note" and isinstance(cred, NoteEntry):
            return cred.title

        return None


# Backwards compatibility alias
SearchOverlay = VaultInterceptorScreen
