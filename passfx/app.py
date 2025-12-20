"""PassFX - Main Textual Application.

Entry point for the secure password manager TUI with signal-based cleanup.
"""

from __future__ import annotations

import atexit
import signal
import sys
from typing import TYPE_CHECKING, Any

from textual.app import App
from textual.binding import Binding
from textual.events import Key, MouseDown

from passfx.core.config import get_config
from passfx.core.crypto import CryptoError
from passfx.core.vault import Vault, VaultError
from passfx.screens.login import LoginScreen
from passfx.search.engine import SearchIndex, SearchResult
from passfx.utils.clipboard import clear_clipboard, emergency_cleanup
from passfx.widgets.search_overlay import VaultInterceptorScreen

if TYPE_CHECKING:
    pass

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
        except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
            pass  # Intentional: shutdown must not raise

    # Clear clipboard - critical for security
    try:
        emergency_cleanup()
    except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
        pass  # Intentional: shutdown must not raise

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
        except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
            pass  # Intentional: atexit must not raise

    # Clear clipboard
    try:
        clear_clipboard()
    except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
        pass  # Intentional: atexit must not raise


class PassFXApp(App):
    """PassFX - Your secure password vault."""

    CSS_PATH = "styles/passfx.tcss"
    TITLE = "◀ PASSFX ▶ Your passwords. Offline. Encrypted."

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+k", "toggle_search", "Search", priority=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "back", "Back", show=True),
    ]

    SCREENS = {"login": LoginScreen}

    def __init__(self) -> None:
        super().__init__()
        self.vault = Vault()
        self._unlocked = False
        self._search_index: SearchIndex | None = None

        # Apply saved settings from config
        config = get_config()
        self.vault.set_lock_timeout(config.auto_lock_minutes * 60)

    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.push_screen("login")
        # Start auto-lock timer - checks every 10 seconds
        self.set_interval(10, self._check_auto_lock)

    def on_key(self, _event: Key) -> None:
        """Reset activity timer on any key press."""
        if self._unlocked:
            self.vault.reset_activity()

    def on_mouse_down(self, _event: MouseDown) -> None:
        """Reset activity timer on any mouse click."""
        if self._unlocked:
            self.vault.reset_activity()

    def _check_auto_lock(self) -> None:
        """Check if vault should auto-lock due to inactivity.

        Called periodically to enforce auto-lock timeout.
        Returns user to login screen when timeout exceeded.
        """
        if not self._unlocked:
            return

        if self.vault.check_timeout():
            # Lock the vault
            self.vault.lock()
            self._unlocked = False

            # Clear clipboard for security
            clear_clipboard()

            # Show notification
            self.notify(
                "Vault locked due to inactivity",
                title="Auto-Lock",
                severity="warning",
            )

            # Navigate back to login - pop all screens except the base
            # then push a fresh login screen instance
            while len(self.screen_stack) > 1:
                self.pop_screen()

            # Push fresh login screen instance (not named screen which may be cached)
            self.push_screen(LoginScreen())

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

    def action_toggle_search(self) -> None:
        """Toggle the global search overlay (Ctrl+K)."""
        # Don't show search if vault is locked or on login screen
        if not self._unlocked:
            return

        screen_name = self.screen.__class__.__name__
        if screen_name in ("LoginScreen", "VaultInterceptorScreen"):
            return

        # Build search index and push modal
        self._build_search_index()
        self.push_screen(
            VaultInterceptorScreen(search_index=self._search_index),
            callback=self._handle_search_result,
        )

    def _build_search_index(self) -> None:
        """Build or rebuild the search index from vault data."""
        if not self._unlocked or self.vault.is_locked:
            self._search_index = None
            return

        index = SearchIndex()
        index.build_index(
            emails=self.vault.get_emails(),
            phones=self.vault.get_phones(),
            cards=self.vault.get_cards(),
            envs=self.vault.get_envs(),
            recovery=self.vault.get_recovery_entries(),
            notes=self.vault.get_notes(),
        )
        self._search_index = index

    def _handle_search_result(self, result: SearchResult | None) -> None:
        """Handle search result from modal - navigate to appropriate screen."""
        if result is not None:
            self._navigate_to_result(result)

    def _navigate_to_result(self, result: SearchResult) -> None:
        """Navigate to the screen containing the selected search result.

        Args:
            result: The selected search result.
        """
        # Import screens lazily to avoid circular imports
        # pylint: disable=import-outside-toplevel
        screen_name = result.screen_name
        credential_id = result.credential_id

        if screen_name == "passwords":
            from passfx.screens.passwords import PasswordsScreen

            pwd_screen = PasswordsScreen()
            pwd_screen._pending_select_id = credential_id
            self.push_screen(pwd_screen)

        elif screen_name == "phones":
            from passfx.screens.phones import PhonesScreen

            phone_screen = PhonesScreen()
            phone_screen._pending_select_id = credential_id
            self.push_screen(phone_screen)

        elif screen_name == "cards":
            from passfx.screens.cards import CardsScreen

            card_screen = CardsScreen()
            card_screen._pending_select_id = credential_id
            self.push_screen(card_screen)

        elif screen_name == "envs":
            from passfx.screens.envs import EnvsScreen

            env_screen = EnvsScreen()
            env_screen._pending_select_id = credential_id
            self.push_screen(env_screen)

        elif screen_name == "recovery":
            from passfx.screens.recovery import RecoveryScreen

            recovery_screen = RecoveryScreen()
            recovery_screen._pending_select_id = credential_id
            self.push_screen(recovery_screen)

        elif screen_name == "notes":
            from passfx.screens.notes import NotesScreen

            notes_screen = NotesScreen()
            notes_screen._pending_select_id = credential_id
            self.push_screen(notes_screen)


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
