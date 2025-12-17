"""Interactive menu system for PassFX - Stunning terminal UI."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from rich.panel import Panel
from rich.table import Table
from simple_term_menu import TerminalMenu

from passfx.ui.styles import console, print_error

# ═══════════════════════════════════════════════════════════════════════════════
# THEME CONFIGURATION - Clean, Professional Design
# ═══════════════════════════════════════════════════════════════════════════════

THEME = {
    # Cursor - clean arrow
    "cursor": "  › ",
    "cursor_style": ("fg_cyan", "bold"),
    # Selection highlight - subtle but visible
    "highlight_style": ("fg_cyan", "bold"),
    # Search
    "search_highlight": ("fg_black", "bg_cyan", "bold"),
    # Shortcuts
    "shortcut_style": ("fg_cyan",),
    "shortcut_bracket_style": ("fg_gray",),
    # Status bar - minimal
    "status_style": ("fg_gray",),
    # Multi-select
    "multi_cursor": "  ◆ ",
    "multi_cursor_style": ("fg_green", "bold"),
}

# Menu item prefixes (no emojis - they break terminal width calc)
ICONS = {
    "passwords": "■",
    "phone": "■",
    "cards": "■",
    "generate": "■",
    "search": "■",
    "settings": "■",
    "exit": "■",
    "add": "+",
    "list": "≡",
    "copy": "□",
    "edit": "✎",
    "delete": "×",
    "back": "←",
    "export": "↑",
    "import": "↓",
    "stats": "#",
}


@dataclass
class MenuItem:
    """Menu item with label and action."""

    key: str
    label: str
    action: Callable[[], None] | None = None
    icon: str = ""
    description: str = ""
    preview: str = ""


class Menu:
    """Beautiful interactive terminal menu with simple-term-menu."""

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        show_search: bool = True,
        show_shortcut_hints: bool = True,
        status_bar: str = "",
    ) -> None:
        self.title = title
        self.subtitle = subtitle
        self.show_search = show_search
        self.show_shortcut_hints = show_shortcut_hints
        self.status_bar = status_bar or "↑↓ Navigate • Enter Select • / Search • q Quit"
        self._items: list[MenuItem] = []
        self._running: bool = False

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def add_item(
        self,
        key: str,
        label: str,
        action: Callable[[], None] | None = None,
        icon: str = "",
        description: str = "",
        preview: str = "",
    ) -> Menu:
        """Add a menu item with optional action and metadata."""
        self._items.append(MenuItem(key, label, action, icon, description, preview))
        return self

    def _build_entries(self) -> list[str]:
        """Build menu entry strings - clean and aligned."""
        entries = []

        for item in self._items:
            # Clean format: just the label, padded for alignment
            entry = f"    {item.label}"
            entries.append(entry)
        return entries

    def _build_previews(self) -> list[str] | None:
        """Build preview strings for each item."""
        previews = []
        has_any = False
        for item in self._items:
            if item.description:
                previews.append(f"\n  {item.description}\n")
                has_any = True
            elif item.preview:
                previews.append(item.preview)
                has_any = True
            else:
                previews.append("")
        return previews if has_any else None

    def _display_header(self) -> None:
        """Display clean boxed header."""
        console.print()

        # Box drawing characters
        width = 44
        title = self.title.upper()

        # Top border
        console.print(f"    [cyan]╭{'─' * width}╮[/cyan]")

        # Title centered
        padding = (width - len(title)) // 2
        title_pad_right = width - padding - len(title)
        console.print(
            f"    [cyan]│[/cyan][bold bright_white]"
            f"{' ' * padding}{title}{' ' * title_pad_right}"
            f"[/bold bright_white][cyan]│[/cyan]"
        )

        # Subtitle if present
        if self.subtitle:
            sub_padding = (width - len(self.subtitle)) // 2
            sub_pad_right = width - sub_padding - len(self.subtitle)
            console.print(
                f"    [cyan]│[/cyan][dim]"
                f"{' ' * sub_padding}{self.subtitle}{' ' * sub_pad_right}"
                f"[/dim][cyan]│[/cyan]"
            )

        # Bottom border
        console.print(f"    [cyan]╰{'─' * width}╯[/cyan]")
        console.print()

    def run(self) -> None:
        """Run the menu loop."""
        self._running = True

        while self._running:
            selected_item = self._run_selection()

            if selected_item is None or selected_item.action is None:
                self._running = False
            else:
                console.print()
                try:
                    selected_item.action()
                except KeyboardInterrupt:
                    console.print("\n[dim]↩ Interrupted[/dim]")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    print_error(f"Action failed: {e}")

    def _run_selection(self) -> MenuItem | None:
        """Run the selection UI."""
        self._display_header()

        entries = self._build_entries()

        try:
            menu = TerminalMenu(
                menu_entries=entries,
                menu_cursor=THEME["cursor"],
                menu_cursor_style=THEME["cursor_style"],
                menu_highlight_style=THEME["highlight_style"],
                cycle_cursor=True,
                clear_screen=False,
                quit_keys=("q", "Q"),
                status_bar="    [↑↓] Navigate    [Enter] Select    [q] Back",
                status_bar_style=THEME["status_style"],
            )
            selected_index = menu.show()
        except Exception as e:  # pylint: disable=broad-exception-caught
            print_error(f"Menu error: {e}")
            return None

        if selected_index is None:
            return None

        return self._items[selected_index]

    def stop(self) -> None:
        """Stop the menu loop."""
        self._running = False


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT FUNCTIONS - Beautiful input handling
# ═══════════════════════════════════════════════════════════════════════════════


def prompt_input(
    label: str,
    default: str = "",
    required: bool = True,
    password: bool = False,
) -> str:
    """Prompt for user input with beautiful styling."""
    # Build prompt with styling
    if required:
        prompt_label = f"[bold cyan]›[/bold cyan] [bold]{label}[/bold]"
    else:
        prompt_label = f"[dim cyan]›[/dim cyan] {label}"

    if default:
        prompt_label += f" [dim]({default})[/dim]"

    prompt_label += " [dim]→[/dim] "

    while True:
        try:
            if password:
                value = console.input(prompt_label, password=True)
            else:
                value = console.input(prompt_label)

            value = value.strip()

            if not value and default:
                return default
            if not value and required:
                console.print("  [red]✗[/red] [dim]This field is required[/dim]")
                continue

            return value

        except (EOFError, KeyboardInterrupt) as exc:
            raise KeyboardInterrupt("Input cancelled") from exc


def prompt_confirm(message: str, default: bool = False) -> bool:
    """Prompt for yes/no confirmation with style."""
    if default:
        hint = "[bold green]Y[/bold green]/n"
    else:
        hint = "y/[bold red]N[/bold red]"

    prompt = f"[bold cyan]?[/bold cyan] {message} [{hint}] [dim]→[/dim] "

    try:
        response = console.input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default

    if not response:
        return default

    return response in ("y", "yes", "1", "true")


def prompt_choice(
    message: str,
    choices: list[str],
    default: int = 0,
) -> int:
    """Prompt user to select from choices with beautiful menu."""
    console.print()
    console.print(f"[bold cyan]?[/bold cyan] [bold]{message}[/bold]")
    console.print()

    menu = TerminalMenu(
        menu_entries=choices,
        menu_cursor=THEME["cursor"],
        menu_cursor_style=THEME["cursor_style"],
        menu_highlight_style=THEME["highlight_style"],
        cycle_cursor=True,
        clear_screen=False,
        status_bar="↑↓ Navigate • Enter Select",
        status_bar_style=THEME["status_style"],
    )

    try:
        selected = menu.show()
        return selected if selected is not None else default
    except KeyboardInterrupt:
        return default


def prompt_multi_select(
    message: str,
    choices: list[str],
    defaults: list[int] | None = None,
) -> list[int]:
    """Multi-select prompt with checkboxes."""
    console.print()
    console.print(f"[bold cyan]?[/bold cyan] [bold]{message}[/bold]")
    console.print("[dim]  (Space to toggle, Enter to confirm)[/dim]")
    console.print()

    menu = TerminalMenu(
        menu_entries=choices,
        menu_cursor=THEME["cursor"],
        menu_cursor_style=THEME["cursor_style"],
        menu_highlight_style=THEME["highlight_style"],
        multi_select=True,
        show_multi_select_hint=True,
        multi_select_cursor=THEME["multi_cursor"],
        multi_select_cursor_style=THEME["multi_cursor_style"],
        multi_select_select_on_accept=False,
        multi_select_empty_ok=True,
        preselected_entries=defaults,
        cycle_cursor=True,
        clear_screen=False,
        status_bar="Space Toggle • Enter Confirm • q Cancel",
        status_bar_style=THEME["status_style"],
    )

    try:
        selected = menu.show()
        if selected is None:
            return defaults or []
        return list(selected) if isinstance(selected, tuple) else [selected]
    except KeyboardInterrupt:
        return defaults or []


# ═══════════════════════════════════════════════════════════════════════════════
# DISPLAY FUNCTIONS - Data visualization
# ═══════════════════════════════════════════════════════════════════════════════


def display_table(
    title: str,
    headers: list[str],
    rows: list[list[str]],
    show_index: bool = True,
) -> None:
    """Display a beautifully styled table."""
    table = Table(
        title=f"[bold bright_cyan]{title}[/bold bright_cyan]",
        border_style="cyan",
        header_style="bold bright_white on dark_blue",
        row_styles=["", "dim"],
        show_lines=False,
        padding=(0, 1),
    )

    if show_index:
        table.add_column("#", style="dim cyan", width=4, justify="right")

    for header in headers:
        table.add_column(header, style="white")

    for i, row in enumerate(rows):
        if show_index:
            table.add_row(f"[cyan]{i + 1}[/cyan]", *row)
        else:
            table.add_row(*row)

    console.print()
    console.print(table)
    console.print()


def display_empty_message(
    message: str = "Your vault is emptier than /dev/null",
) -> None:
    """Display a styled empty state message."""
    console.print()
    console.print(
        Panel(
            f"[dim italic]{message}[/dim italic]",
            border_style="dim",
            padding=(1, 4),
        )
    )
    console.print()


def display_success(message: str) -> None:
    """Display a success message with flair."""
    console.print(f"\n  [bold green]✓[/bold green] {message}\n")


def display_info(message: str) -> None:
    """Display an info message."""
    console.print(f"\n  [bold cyan]ℹ[/bold cyan] {message}\n")


def display_warning(message: str) -> None:
    """Display a warning message."""
    console.print(f"\n  [bold yellow]⚠[/bold yellow] {message}\n")


def display_box(title: str, content: str, style: str = "cyan") -> None:
    """Display content in a beautiful box."""
    console.print()
    console.print(
        Panel(
            content,
            title=f"[bold]{title}[/bold]",
            border_style=style,
            padding=(1, 2),
        )
    )
    console.print()
