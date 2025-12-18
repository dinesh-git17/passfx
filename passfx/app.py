"""PassFX - Main Textual Application.

Entry point for the secure password manager TUI with signal-based cleanup.
"""

from __future__ import annotations

import atexit
import signal
import sys
from typing import Any

from textual.app import App
from textual.binding import Binding

from passfx.core.crypto import CryptoError
from passfx.core.vault import Vault, VaultError
from passfx.screens.login import LoginScreen
from passfx.utils.clipboard import clear_clipboard, emergency_cleanup

# Module-level state for signal handling (mutable, not constants)
_app_instance: PassFXApp | None = None  # pylint: disable=invalid-name
_shutdown_in_progress: bool = False  # pylint: disable=invalid-name


def _graceful_shutdown(_signum: int, _frame: Any) -> None:
    """Handle termination signals with secure cleanup.

    Ensures vault is locked and clipboard is cleared before exit.
    Safe to call multiple times - uses flag to prevent double-cleanup.
    """
    global _shutdown_in_progress  # pylint: disable=global-statement

    if _shutdown_in_progress:
        return
    _shutdown_in_progress = True

    # Lock vault if app exists and is unlocked
    if _app_instance is not None:
        try:
            if _app_instance.vault and _app_instance._unlocked:
                _app_instance.vault.lock()
        except Exception:  # pylint: disable=broad-exception-caught
            pass  # Fail silently during shutdown

    # Clear clipboard - critical for security
    try:
        emergency_cleanup()
    except Exception:  # pylint: disable=broad-exception-caught
        pass  # Fail silently during shutdown

    # Exit cleanly
    sys.exit(0)


def _register_signal_handlers() -> None:
    """Register signal handlers for graceful shutdown.

    SIGINT: User interrupt (Ctrl-C)
    SIGTERM: Process termination request
    """
    signal.signal(signal.SIGINT, _graceful_shutdown)
    signal.signal(signal.SIGTERM, _graceful_shutdown)


def _cleanup_on_exit() -> None:
    """Atexit handler for normal application exit.

    Ensures clipboard is cleared even on normal exit paths.
    """
    global _shutdown_in_progress  # pylint: disable=global-statement

    if _shutdown_in_progress:
        return
    _shutdown_in_progress = True

    # Lock vault if exists
    if _app_instance is not None:
        try:
            if _app_instance.vault and _app_instance._unlocked:
                _app_instance.vault.lock()
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    # Clear clipboard
    try:
        clear_clipboard()
    except Exception:  # pylint: disable=broad-exception-caught
        pass


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
    """Run the PassFX application with secure signal handling.

    Registers signal handlers and atexit cleanup to ensure:
    - Vault is locked on abnormal termination
    - Clipboard is cleared on any exit path
    """
    global _app_instance  # pylint: disable=global-statement

    # Register signal handlers before creating app
    _register_signal_handlers()

    # Register atexit handler for normal exit cleanup
    atexit.register(_cleanup_on_exit)

    # Create and store app instance for signal handler access
    app = PassFXApp()
    _app_instance = app

    try:
        app.run()
    finally:
        # Ensure cleanup runs even if app.run() raises
        _cleanup_on_exit()


if __name__ == "__main__":
    run()
