"""PassFX - Main Textual Application."""

from __future__ import annotations

from textual.app import App
from textual.binding import Binding

from passfx.core.crypto import CryptoError
from passfx.core.vault import Vault, VaultError
from passfx.screens.login import LoginScreen


class PassFXApp(App):
    """PassFX - Your secure password vault."""

    CSS_PATH = "styles/passfx.tcss"
    TITLE = "◀ PASSFX ▶ Your passwords. Offline. Encrypted."

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    SCREENS = {"login": LoginScreen}

    def __init__(self) -> None:
        super().__init__()
        self.vault = Vault()
        self._unlocked = False

    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.push_screen("login")

    async def action_back(self) -> None:
        """Go back to previous screen (but not from main menu)."""
        # Don't allow back from main menu or login
        screen_name = self.screen.__class__.__name__
        if screen_name in ("MainMenuScreen", "LoginScreen"):
            return

        if len(self.screen_stack) > 1:
            self.pop_screen()

    async def action_quit(self) -> None:
        """Quit the application."""
        if self.vault and self._unlocked:
            self.vault.lock()
        self.exit()

    def unlock_vault(self, password: str) -> bool:
        """Attempt to unlock the vault."""
        try:
            self.vault.unlock(password)
            self._unlocked = True
            return True
        except (VaultError, CryptoError):
            return False

    def create_vault(self, password: str) -> bool:
        """Create a new vault."""
        try:
            self.vault.create(password)
            self._unlocked = True
            return True
        except VaultError:
            return False


def run() -> None:
    """Run the PassFX application."""
    app = PassFXApp()
    app.run()


if __name__ == "__main__":
    run()
