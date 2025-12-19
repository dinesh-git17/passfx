"""Login Screen for PassFX."""

# pylint: disable=duplicate-code

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static

from passfx.core.crypto import validate_master_password
from passfx.utils.platform_security import secure_file_permissions
from passfx.widgets.matrix_rain import MatrixRainStrip

if TYPE_CHECKING:
    from passfx.app import PassFXApp

# ASCII Logo - PASSFX in neon cyan
LOGO = """[bold #00FFFF]
██████╗  █████╗ ███████╗███████╗███████╗██╗  ██╗
██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝╚██╗██╔╝
██████╔╝███████║███████╗███████╗█████╗   ╚███╔╝
██╔═══╝ ██╔══██║╚════██║╚════██║██╔══╝   ██╔██╗
██║     ██║  ██║███████║███████║██║     ██╔╝ ██╗
╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝  ╚═╝
[/]"""

VERSION = "v1.0.1"

# Persistent rate limiting configuration
LOCKOUT_FILE = Path.home() / ".passfx" / "lockout.json"
MAX_LOCKOUT_SECONDS = 3600  # 1 hour maximum lockout
MAX_ATTEMPTS_BEFORE_LOCKOUT = 3


def _get_lockout_state() -> dict:
    """Read lockout state from disk.

    Returns a dictionary with:
    - failed_attempts: int
    - lockout_until: float | None (Unix timestamp)

    Handles file corruption gracefully by returning clean state.
    """
    if not LOCKOUT_FILE.exists():
        return {"failed_attempts": 0, "lockout_until": None}

    try:
        data = json.loads(LOCKOUT_FILE.read_text(encoding="utf-8"))
        # Validate structure
        if not isinstance(data, dict):
            return {"failed_attempts": 0, "lockout_until": None}

        failed_attempts = data.get("failed_attempts", 0)
        lockout_until = data.get("lockout_until")

        # Validate types
        if not isinstance(failed_attempts, int) or failed_attempts < 0:
            failed_attempts = 0
        if lockout_until is not None and not isinstance(lockout_until, int | float):
            lockout_until = None

        return {"failed_attempts": failed_attempts, "lockout_until": lockout_until}

    except (json.JSONDecodeError, OSError, ValueError):
        # File corrupted, reset to clean state
        return {"failed_attempts": 0, "lockout_until": None}


def _save_lockout_state(state: dict) -> None:
    """Save lockout state to disk with secure permissions.

    Args:
        state: Dictionary with failed_attempts and lockout_until keys.
    """
    LOCKOUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Write atomically using temp file
    temp_file = LOCKOUT_FILE.with_suffix(".json.tmp")
    try:
        temp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        secure_file_permissions(temp_file)
        temp_file.replace(LOCKOUT_FILE)
        secure_file_permissions(LOCKOUT_FILE)
    except OSError:
        # Clean up temp file on error
        if temp_file.exists():
            temp_file.unlink()
        raise


def _check_lockout() -> tuple[bool, int]:
    """Check if user is currently locked out.

    Returns:
        Tuple of (is_locked, seconds_remaining).
        If not locked, seconds_remaining is 0.
    """
    state = _get_lockout_state()
    lockout_until = state.get("lockout_until")

    if lockout_until is None:
        return False, 0

    current_time = time.time()
    if current_time < lockout_until:
        # Still locked out
        seconds_remaining = int(lockout_until - current_time)
        return True, seconds_remaining

    # Lockout expired, clear it
    _clear_lockout()
    return False, 0


def _record_failed_attempt() -> None:
    """Record a failed login attempt with exponential backoff.

    Implements 2^n second delay where n = failed_attempts.
    Maximum lockout is capped at MAX_LOCKOUT_SECONDS.
    """
    state = _get_lockout_state()
    failed_attempts = state.get("failed_attempts", 0) + 1

    # Calculate exponential backoff: 2^n seconds
    delay_seconds = min(2**failed_attempts, MAX_LOCKOUT_SECONDS)
    lockout_until = time.time() + delay_seconds

    new_state = {"failed_attempts": failed_attempts, "lockout_until": lockout_until}
    _save_lockout_state(new_state)


def _clear_lockout() -> None:
    """Clear lockout state after successful login."""
    if LOCKOUT_FILE.exists():
        try:
            LOCKOUT_FILE.unlink()
        except OSError:
            pass


class LoginScreen(Screen):
    """Login screen with Matrix rain background and centered login form."""

    BINDINGS = [
        Binding("enter", "submit", "Submit", show=False),
    ]

    def __init__(self, new_vault: bool = False) -> None:
        super().__init__()
        self.new_vault = new_vault

    def compose(self) -> ComposeResult:
        """Create the Night City login layout with Matrix rain strips."""
        app: PassFXApp = self.app  # type: ignore

        # Vertical layout with rain at top/bottom, horizontal with side strips
        with Vertical(id="matrix-bg"):
            yield MatrixRainStrip(
                update_interval=0.06,
                decay_rate=0.12,
                classes="matrix-strip-top",
            )
            with Horizontal(id="matrix-middle"):
                yield MatrixRainStrip(
                    update_interval=0.06,
                    decay_rate=0.08,
                    classes="matrix-strip-left",
                )
                with Center(id="login-form-pane"):
                    with Vertical(id="login-deck"):
                        yield Static(LOGO, id="brand-logo")
                        yield Label(":: SECURE VAULT ACCESS ::", id="brand-subtitle")

                        if app.vault.exists and not self.new_vault:
                            # Unlock mode
                            yield Label("> ENTER PASSPHRASE", classes="input-label")
                            yield Input(password=True, id="password-input")
                            yield Button("DECRYPT VAULT", id="unlock-button")
                        else:
                            # Create mode
                            yield Label("> CREATE PASSPHRASE", classes="input-label")
                            yield Input(password=True, id="password-input")
                            yield Label("> CONFIRM PASSPHRASE", classes="input-label")
                            yield Input(password=True, id="confirm-input")
                            with Center():
                                yield Button("[ INITIALIZE VAULT ]", id="create-button")

                        yield Static("", id="error-message")
                        yield Label(
                            "STATUS: WAITING... // AES-128 AUTHENTICATED ENCRYPTION",
                            id="status-footer",
                        )
                yield MatrixRainStrip(
                    update_interval=0.06,
                    decay_rate=0.08,
                    classes="matrix-strip-right",
                )
            yield MatrixRainStrip(
                update_interval=0.06,
                decay_rate=0.12,
                classes="matrix-strip-bottom",
            )

    def on_mount(self) -> None:
        """Focus the password input on mount."""
        self.query_one("#password-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "unlock-button":
            self._handle_unlock()
        elif event.button.id == "create-button":
            self._handle_create()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input fields."""
        app: PassFXApp = self.app  # type: ignore

        if event.input.id == "password-input":
            if app.vault.exists and not self.new_vault:
                self._handle_unlock()
            else:
                # Focus confirm input
                confirm = self.query_one("#confirm-input", Input)
                confirm.focus()
        elif event.input.id == "confirm-input":
            self._handle_create()

    def _handle_unlock(self) -> None:
        """Handle vault unlock attempt with persistent rate limiting."""
        app: PassFXApp = self.app  # type: ignore
        password_input = self.query_one("#password-input", Input)
        error_label = self.query_one("#error-message", Static)
        password = password_input.value

        if not password:
            error_label.update("[error]Please enter your password[/error]")
            return

        # Check if user is currently locked out
        is_locked, seconds_remaining = _check_lockout()
        if is_locked:
            minutes = seconds_remaining // 60
            seconds = seconds_remaining % 60
            if minutes > 0:
                time_str = f"{minutes}m {seconds}s"
            else:
                time_str = f"{seconds}s"
            error_label.update(
                f"[error]Account locked. Try again in {time_str}.[/error]"
            )
            password_input.value = ""
            password_input.focus()
            return

        # Attempt to unlock vault
        if app.unlock_vault(password):
            # Success - clear lockout state and proceed to main menu
            _clear_lockout()
            # pylint: disable=import-outside-toplevel
            from passfx.screens.main_menu import MainMenuScreen

            self.app.switch_screen(MainMenuScreen())
        else:
            # Failed attempt - record it with exponential backoff
            _record_failed_attempt()

            # Get updated lockout state
            state = _get_lockout_state()
            failed_attempts = state.get("failed_attempts", 0)

            if failed_attempts >= MAX_ATTEMPTS_BEFORE_LOCKOUT:
                # Lockout triggered - show lockout message
                _, seconds_remaining = _check_lockout()
                minutes = seconds_remaining // 60
                seconds = seconds_remaining % 60
                if minutes > 0:
                    time_str = f"{minutes}m {seconds}s"
                else:
                    time_str = f"{seconds}s"
                error_label.update(
                    f"[error]Too many failed attempts. Locked for {time_str}.[/error]"
                )
            else:
                # Show attempts remaining
                remaining = MAX_ATTEMPTS_BEFORE_LOCKOUT - failed_attempts
                error_label.update(
                    f"[error]Wrong password. {remaining} attempt(s) remaining.[/error]"
                )

            password_input.value = ""
            password_input.focus()

    def _handle_create(self) -> None:
        """Handle vault creation."""
        app: PassFXApp = self.app  # type: ignore
        password_input = self.query_one("#password-input", Input)
        confirm_input = self.query_one("#confirm-input", Input)
        error_label = self.query_one("#error-message", Static)

        password = password_input.value
        confirm = confirm_input.value

        if not password:
            error_label.update("[error]Please enter a password[/error]")
            return

        if password != confirm:
            error_label.update("[error]Passwords don't match[/error]")
            confirm_input.value = ""
            confirm_input.focus()
            return

        is_valid, issues = validate_master_password(password)
        if not is_valid:
            error_label.update(f"[error]{issues[0]}[/error]")
            return

        if app.create_vault(password):
            # Success - go to main menu
            # pylint: disable=import-outside-toplevel
            from passfx.screens.main_menu import MainMenuScreen

            self.app.switch_screen(MainMenuScreen())
        else:
            error_label.update("[error]Failed to create vault[/error]")
