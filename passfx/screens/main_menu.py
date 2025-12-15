"""Main Menu Screen for PassFX."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, OptionList, Static
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from passfx.app import PassFXApp


class MainMenuScreen(Screen):
    """Main menu with navigation options."""

    BINDINGS = [
        Binding("1", "passwords", "Passwords", show=False),
        Binding("2", "phones", "Phones", show=False),
        Binding("3", "cards", "Cards", show=False),
        Binding("4", "generator", "Generator", show=False),
        Binding("5", "search", "Search", show=False),
        Binding("6", "settings", "Settings", show=False),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Create the main menu layout."""
        app: PassFXApp = self.app  # type: ignore

        yield Header()

        with Center():
            with Vertical(id="menu-container"):
                yield Static(
                    "╔═══════════════════════════════════════╗\n"
                    "║      P A S S F X      ║\n"
                    "║   Your Secure Password Vault   ║\n"
                    "╚═══════════════════════════════════════╝",
                    classes="title",
                )

                # Get entry counts
                stats = app.vault.get_stats() if app._unlocked else {}
                email_count = stats.get("emails", 0)
                phone_count = stats.get("phones", 0)
                card_count = stats.get("cards", 0)

                yield OptionList(
                    Option(f"Passwords                        {email_count:>3}", id="passwords"),
                    Option(f"Phone Credentials                {phone_count:>3}", id="phones"),
                    Option(f"Credit Cards                     {card_count:>3}", id="cards"),
                    Option("Generate Password", id="generator"),
                    Option("Search All", id="search"),
                    Option("Settings", id="settings"),
                    Option("Exit", id="exit"),
                    id="main-menu",
                )

        yield Footer()

    def on_mount(self) -> None:
        """Focus the menu on mount."""
        self.query_one("#main-menu", OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle menu selection."""
        option_id = event.option.id

        if option_id == "passwords":
            self.action_passwords()
        elif option_id == "phones":
            self.action_phones()
        elif option_id == "cards":
            self.action_cards()
        elif option_id == "generator":
            self.action_generator()
        elif option_id == "search":
            self.action_search()
        elif option_id == "settings":
            self.action_settings()
        elif option_id == "exit":
            self.action_quit()

    def action_passwords(self) -> None:
        """Go to passwords screen."""
        from passfx.screens.passwords import PasswordsScreen
        self.app.push_screen(PasswordsScreen())

    def action_phones(self) -> None:
        """Go to phones screen."""
        from passfx.screens.phones import PhonesScreen
        self.app.push_screen(PhonesScreen())

    def action_cards(self) -> None:
        """Go to cards screen."""
        from passfx.screens.cards import CardsScreen
        self.app.push_screen(CardsScreen())

    def action_generator(self) -> None:
        """Go to password generator screen."""
        from passfx.screens.generator import GeneratorScreen
        self.app.push_screen(GeneratorScreen())

    def action_search(self) -> None:
        """Open search - for now just notify."""
        self.notify("Search coming soon!", title="Search")

    def action_settings(self) -> None:
        """Go to settings screen."""
        from passfx.screens.settings import SettingsScreen
        self.app.push_screen(SettingsScreen())

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.action_quit()
