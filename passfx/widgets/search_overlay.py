"""Global search overlay for PassFX - Spotlight-style search interface.

A modal screen that provides instant search across all vault credentials.
"""

from __future__ import annotations

from collections.abc import Callable

from rich.console import RenderableType
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from passfx.search.engine import SearchIndex, SearchResult

# Maximum number of visible results
MAX_VISIBLE_RESULTS = 10


class SearchResultItem(Static):
    """A single search result item that can be updated."""

    is_selected: reactive[bool] = reactive(False)

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._icon = ""
        self._primary = ""
        self._secondary = ""

    def set_result(self, result: SearchResult | None, selected: bool = False) -> None:
        """Update the result item content."""
        if result is None:
            self._icon = ""
            self._primary = ""
            self._secondary = ""
        else:
            self._icon = result.icon
            self._primary = result.primary_text
            self._secondary = result.secondary_text or ""
        self.is_selected = selected
        self.update(self._build_content())

    def _build_content(self) -> RenderableType:
        """Render the result item as Rich text."""
        if not self._primary:
            return Text("")

        # Build the display text with proper formatting
        line = Text()
        icon_style = "black" if self.is_selected else "#00FFFF"
        text_style = "black" if self.is_selected else "#e0e0e0"
        secondary_style = "#333333" if self.is_selected else "#666666"

        line.append(f"[{self._icon}]", style=icon_style)
        line.append("  ")
        line.append(self._primary, style=text_style)
        if self._secondary:
            line.append("  ")
            line.append(self._secondary, style=secondary_style)

        return line

    def watch_is_selected(self, selected: bool) -> None:
        """Update styling when selection changes."""
        if selected:
            self.add_class("-selected")
        else:
            self.remove_class("-selected")
        # Re-render with new selection state
        self.update(self._build_content())


class SearchResultsContainer(Vertical):
    """Container for search results using pre-allocated item widgets.

    Uses update() pattern for reliable real-time refresh in ModalScreen contexts.
    Pre-allocates result item widgets and updates their content rather than
    mounting/unmounting, which avoids refresh timing issues.
    """

    results: reactive[list[SearchResult]] = reactive([])
    selected_index: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        """Pre-allocate result item widgets."""
        for _ in range(MAX_VISIBLE_RESULTS):
            yield SearchResultItem(classes="search-result-item")

    def watch_results(self, _results: list[SearchResult]) -> None:
        """Update result item widgets when results change."""
        self._update_items()

    def watch_selected_index(self, _selected_index: int) -> None:
        """Update selection when index changes."""
        self._update_items()

    def _update_items(self) -> None:
        """Update all result item widgets with current data."""
        items = list(self.query(SearchResultItem))
        for i, item in enumerate(items):
            if i < len(self.results):
                item.set_result(self.results[i], selected=i == self.selected_index)
                item.display = True
            else:
                item.set_result(None)
                item.display = False


class SearchOverlay(ModalScreen[SearchResult | None]):
    """Spotlight-style search modal for vault credentials.

    Features:
    - Top-anchored search bar
    - Results list below search bar
    - Keyboard navigation (up/down/enter/escape)
    - Instant search with scoring
    """

    DEFAULT_CSS = """
    SearchOverlay {
        align: center top;
        background: transparent;
    }

    SearchOverlay #search-modal {
        width: 90%;
        max-width: 100;
        height: auto;
        max-height: 60%;
        margin-top: 2;
        background: #0a0a0a;
        border: heavy #00FFFF;
    }

    SearchOverlay #search-input-row {
        width: 100%;
        height: 3;
        background: #0a0a0a;
        padding: 0 1;
    }

    SearchOverlay #search-input {
        width: 100%;
        border: none;
        background: #0a0a0a;
    }

    SearchOverlay #search-input:focus {
        border: none;
    }

    SearchOverlay #search-results {
        width: 100%;
        height: auto;
        max-height: 15;
        background: #0a0a0a;
        border-top: solid #333333;
    }

    SearchOverlay #search-results:empty {
        display: none;
    }

    SearchOverlay .search-result-item {
        width: 100%;
        height: 2;
        padding: 0 1;
        background: #0a0a0a;
    }

    SearchOverlay .search-result-item:hover {
        background: #1a1a2e;
    }

    SearchOverlay .search-result-item.-selected {
        background: #00FFFF;
    }

    SearchOverlay #search-hint {
        width: 100%;
        height: 1;
        background: #0a0a0a;
        color: #666666;
        text-align: center;
        border-top: solid #333333;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Close", priority=True),
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("enter", "select_result", "Select", show=False),
    ]

    def __init__(
        self,
        search_index: SearchIndex | None = None,
        on_select: Callable[[SearchResult], None] | None = None,
        **kwargs: object,
    ) -> None:
        """Initialize the search overlay."""
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._search_index = search_index
        self._on_select = on_select

    def compose(self) -> ComposeResult:
        """Create the search modal layout."""
        with Vertical(id="search-modal"):
            with Container(id="search-input-row"):
                yield Input(
                    placeholder="Search vault...",
                    id="search-input",
                )
            yield SearchResultsContainer(id="search-results")
            yield Static(
                "[dim]ESC[/] close  [dim]↑↓[/] navigate  [dim]ENTER[/] select",
                id="search-hint",
            )

    def on_mount(self) -> None:
        """Focus the search input on mount."""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id != "search-input":
            return

        query = event.value.strip()
        self._perform_search(query)

    def _perform_search(self, query: str) -> None:
        """Execute search and update results."""
        results_container = self.query_one("#search-results", SearchResultsContainer)

        if not self._search_index or not query:
            results_container.results = []
        else:
            results_container.results = self._search_index.search(query, max_results=10)

        results_container.selected_index = 0

    def _get_results_container(self) -> SearchResultsContainer:
        """Get the search results container."""
        return self.query_one("#search-results", SearchResultsContainer)

    def action_move_up(self) -> None:
        """Move selection up."""
        container = self._get_results_container()
        if container.results and container.selected_index > 0:
            container.selected_index -= 1

    def action_move_down(self) -> None:
        """Move selection down."""
        container = self._get_results_container()
        if container.results and container.selected_index < len(container.results) - 1:
            container.selected_index += 1

    def action_select_result(self) -> None:
        """Select the current result."""
        container = self._get_results_container()

        if not container.results:
            self.dismiss(None)
            return

        if 0 <= container.selected_index < len(container.results):
            result = container.results[container.selected_index]
            if self._on_select:
                self._on_select(result)
            self.dismiss(result)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Close the modal without selection."""
        self.dismiss(None)
