"""Help Screen for PassFX - System Operator's Manual.

Implements a sidebar + content pane layout matching the Operator console aesthetic.
All content is data-driven for maintainability and consistency.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from passfx.widgets.keycap_footer import KeycapFooter

# ═══════════════════════════════════════════════════════════════════════════════
# HELP DATA - Single source of truth for all help content
# ═══════════════════════════════════════════════════════════════════════════════

HELP_DATA: dict[str, dict[str, dict[str, str]]] = {
    "commands": {
        "Navigation": {
            "UP / DOWN": "Navigate through list items",
            "ENTER": "Select / Confirm action",
            "ESC": "Go back / Close modal / Cancel",
            "/": "Focus terminal (Main Menu only)",
        },
        "Credential Actions": {
            "A": "Add new entry",
            "E": "Edit selected entry",
            "D": "Delete selected entry",
            "V": "View entry details",
            "C": "Copy to clipboard (auto-clear 15s)",
        },
        "Delete Confirmation": {
            "Y": "Confirm deletion",
            "N": "Cancel deletion",
        },
        "Generator Actions": {
            "G": "Generate new password/passphrase/PIN",
            "C": "Copy generated value (auto-clear 30s)",
            "S": "Save generated value to vault",
        },
        "Global": {
            "Q": "Quit application (locks vault)",
            "?": "Open this help screen",
        },
        "Terminal Commands": {
            "/key": "Passwords screen",
            "/pin": "Phones/PINs screen",
            "/crd": "Cards screen",
            "/mem": "Secure Notes screen",
            "/env": "Env Variables screen",
            "/sos": "Recovery Codes screen",
            "/gen": "Password Generator",
            "/set": "Settings screen",
            "/help": "Help screen",
            "/clear": "Clear terminal output",
            "/quit": "Exit application",
        },
    },
    "legend": {
        "Password Strength": {
            "[on #ef4444]  [/] WEAK": "Easily cracked - change immediately",
            "[on #f87171]  [/] POOR": "Below minimum security threshold",
            "[on #f59e0b]  [/] FAIR": "Acceptable but could be stronger",
            "[on #60a5fa]  [/] GOOD": "Meets security recommendations",
            "[on #22c55e]  [/] STRONG": "Excellent protection level",
        },
        "Vault Status": {
            "[#22c55e]●[/] ENCRYPTED": "Vault locked and secured",
            "[#22c55e]DECRYPTED": "Vault unlocked (active session)",
        },
        "Visual Indicators": {
            "[#00FFFF]▸[/]": "Currently selected row",
            "[#8b5cf6]>[/]": "Active sidebar menu item",
            "[dim]****[/]": "Masked sensitive data",
        },
    },
    "system": {
        "Encryption Protocol": {
            "CIPHER": "Fernet (AES-128-CBC)",
            "INTEGRITY": "HMAC-SHA256",
            "KEY DERIVE": "PBKDF2-HMAC-SHA256",
            "ITERATIONS": "480,000 (OWASP 2023)",
            "SALT": "32 bytes (256-bit)",
        },
        "Storage Paths": {
            "VAULT": "~/.passfx/vault.enc",
            "SALT": "~/.passfx/salt",
            "LOCK": "~/.passfx/vault.enc.lock",
        },
        "Security Features": {
            "+ Clipboard": "Auto-clear after 15 seconds",
            "+ Memory": "Secrets wiped on vault lock",
            "+ Atomic": "Writes ensure data integrity",
            "+ Permissions": "Files 0600, directories 0700",
            "+ No Recovery": "By design - zero backdoors",
        },
    },
}

# Section display names and order
SECTIONS: list[tuple[str, str]] = [
    ("commands", "COMMANDS"),
    ("legend", "LEGEND"),
    ("system", "SYSTEM"),
]


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER WIDGETS
# ═══════════════════════════════════════════════════════════════════════════════


class HelpSection(Static):
    """A section block with header and key-value rows.

    Renders a purple inverted header followed by cyan-highlighted key-value pairs.
    """

    def __init__(
        self,
        title: str,
        items: dict[str, str],
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._title = title
        self._items = items

    def compose(self) -> ComposeResult:
        """Compose the section with header and rows."""
        yield Static(f" {self._title} ", classes="help-section-header")
        for key, value in self._items.items():
            yield Static(
                f"  [bold #00FFFF]{key:<16}[/] [#94a3b8]{value}[/]",
                classes="help-row",
            )


class HelpContentPane(VerticalScroll):
    """Scrollable content pane that displays help sections based on selection."""

    current_section: reactive[str] = reactive("commands")

    def compose(self) -> ComposeResult:
        """Initial composition - content updated reactively."""
        yield from self._build_sections(self.current_section)

    def _build_sections(self, section_key: str) -> list[HelpSection]:
        """Build HelpSection widgets for the given section."""
        sections: list[HelpSection] = []
        section_data = HELP_DATA.get(section_key, {})

        for group_name, items in section_data.items():
            sections.append(HelpSection(group_name, items))

        return sections

    def watch_current_section(self, section_key: str) -> None:
        """React to section changes by rebuilding content."""
        self.remove_children()
        for section in self._build_sections(section_key):
            self.mount(section)


# ═══════════════════════════════════════════════════════════════════════════════
# HELP SCREEN
# ═══════════════════════════════════════════════════════════════════════════════


class HelpScreen(ModalScreen[None]):
    """System Operator's Manual - Help documentation modal.

    Features a sidebar + content pane layout matching the Operator console theme.
    Keyboard-first navigation with ESC to close.
    """

    BINDINGS = [
        Binding("escape", "close", "Close", priority=True),
        Binding("q", "close", "Close"),
        Binding("question_mark", "close", "Close"),
        Binding("left", "focus_sidebar", "Sidebar", show=False),
        Binding("right", "focus_content", "Content", show=False),
        Binding("tab", "toggle_focus", "Toggle", show=False),
    ]

    CSS = """
    HelpScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    """

    def compose(self) -> ComposeResult:
        """Create the help modal layout with sidebar and content pane."""
        with Vertical(id="help-dialog"):
            # Header - Inverted cyan block
            yield Static(
                " SYSTEM OPERATOR'S MANUAL ",
                id="help-header",
            )

            # Subtitle
            yield Static(
                "[#94a3b8]PassFX Security Terminal v1.0[/]",
                id="help-subtitle",
            )

            # Body - Sidebar + Content
            with Horizontal(id="help-body"):
                # Sidebar - Section selector
                with Vertical(id="help-sidebar"):
                    yield OptionList(
                        Option("[ CMD ] Commands", id="commands"),
                        Option("[ LGD ] Legend", id="legend"),
                        Option("[ SYS ] System", id="system"),
                        id="help-nav",
                    )

                # Content pane
                yield HelpContentPane(id="help-content")

            # Footer - Mechanical keycap hints
            yield KeycapFooter(
                hints=[
                    ("↑↓", "Navigate"),
                    ("←→", "Switch Pane"),
                    ("^K", "Search"),
                    ("ESC", "Close"),
                ],
                footer_id="help-footer",
            )

    def on_mount(self) -> None:
        """Focus sidebar on mount and highlight first option."""
        nav = self.query_one("#help-nav", OptionList)
        nav.focus()
        nav.highlighted = 0

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        """Update content pane when sidebar selection changes."""
        if event.option and event.option.id:
            content = self.query_one("#help-content", HelpContentPane)
            content.current_section = event.option.id

    def action_close(self) -> None:
        """Close the help modal."""
        self.dismiss(None)

    def action_focus_sidebar(self) -> None:
        """Focus the sidebar navigation."""
        self.query_one("#help-nav", OptionList).focus()

    def action_focus_content(self) -> None:
        """Focus the content pane for scrolling."""
        self.query_one("#help-content", HelpContentPane).focus()

    def action_toggle_focus(self) -> None:
        """Toggle focus between sidebar and content."""
        nav = self.query_one("#help-nav", OptionList)
        content = self.query_one("#help-content", HelpContentPane)

        if nav.has_focus:
            content.focus()
        else:
            nav.focus()
