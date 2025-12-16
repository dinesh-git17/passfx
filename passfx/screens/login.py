"""Login Screen for PassFX."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static

if TYPE_CHECKING:
    from passfx.app import PassFXApp

# ASCII Logo (ANSI Shadow)
LOGO = """[bold #00d4ff]
██████╗  █████╗ ███████╗███████╗███████╗██╗  ██╗
██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝╚██╗██╔╝
██████╔╝███████║███████╗███████╗█████╗   ╚███╔╝
██╔═══╝ ██╔══██║╚════██║╚════██║██╔══╝   ██╔██╗
██║     ██║  ██║███████║███████║██║     ██╔╝ ██╗
╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝  ╚═╝
[/]"""

TAGLINES = [
    "Your secrets are safe with us. Probably.",
    "sudo rm -rf your_worries",
    "Encryption so good, even we can't read it.",
    "Because 'password123' wasn't cutting it.",
    "Fort Knox for your digital life.",
    "Trust issues? We've got encryption.",
    "Making hackers cry since 2024.",
    "256 bits of pure security.",
    "Where passwords go to live forever.",
    "Ctrl+S for your credentials.",
]

VERSION = "v1.0.0"


class LoginScreen(Screen):
    """Login screen with split-view: logo on left, form on right."""

    BINDINGS = [
        Binding("enter", "submit", "Submit", show=False),
    ]

    def __init__(self, new_vault: bool = False) -> None:
        super().__init__()
        self.new_vault = new_vault
        self.attempts = 0
        self.max_attempts = 3

    def compose(self) -> ComposeResult:
        """Create the full-screen login layout matching main menu grid."""
        app: PassFXApp = self.app  # type: ignore

        # Header - System Status Bar
        with Horizontal(id="app-header"):
            yield Static("[bold #00d4ff]◄ PASSFX ►[/]", id="header-branding")
            yield Static("░░ SYSTEM LOCKED ░░", id="header-status")
            yield Static("[#ef4444]🔒 RESTRICTED[/]", id="header-lock")

        # Body - Centered content
        with Center(id="login-form-pane"):
            with Vertical(id="login-content"):
                yield Static(LOGO, id="logo")
                yield Static(
                    f'[italic #8b5cf6]"{random.choice(TAGLINES)}"[/]',
                    id="tagline",
                )

                # Form container for centered inputs
                with Vertical(id="login-form"):
                    if app.vault.exists and not self.new_vault:
                        yield Static(
                            "[bold #60a5fa]━━━ IDENTITY VERIFICATION ━━━[/]",
                            id="form-title",
                        )
                        with Center():
                            yield Label("ENTER MASTER PASSWORD", classes="muted terminal-label")
                        with Center():
                            yield Input(
                                placeholder="••••••••",
                                password=True,
                                id="password-input",
                            )
                        with Center():
                            yield Button("▶ UNLOCK VAULT", variant="primary", id="unlock-button")
                    else:
                        yield Static(
                            "[bold #60a5fa]━━━ VAULT INITIALIZATION ━━━[/]",
                            id="form-title",
                        )
                        with Center():
                            yield Label(
                                "CREATE MASTER PASSWORD", classes="muted terminal-label"
                            )
                        with Center():
                            yield Input(
                                placeholder="••••••••",
                                password=True,
                                id="password-input",
                            )
                        with Center():
                            yield Label("CONFIRM PASSWORD", classes="muted terminal-label")
                        with Center():
                            yield Input(
                                placeholder="••••••••",
                                password=True,
                                id="confirm-input",
                            )
                        with Center():
                            yield Button(
                                "▶ INITIALIZE VAULT", variant="primary", id="create-button"
                            )

                    yield Static("", id="error-message")

        # Footer - Command Strip
        with Horizontal(id="app-footer"):
            yield Static(f" {VERSION} ", id="footer-version")
            with Horizontal(id="footer-keys"):
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #a78bfa]ENTER[/]", classes="keycap")
                    yield Static("[#64748b]Confirm[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #a78bfa] Q [/]", classes="keycap")
                    yield Static("[#64748b]Abort[/]", classes="keycap-label")

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
        """Handle vault unlock attempt."""
        app: PassFXApp = self.app  # type: ignore
        password_input = self.query_one("#password-input", Input)
        error_label = self.query_one("#error-message", Static)
        password = password_input.value

        if not password:
            error_label.update("[error]Please enter your password[/error]")
            return

        if app.unlock_vault(password):
            # Success - go to main menu
            from passfx.screens.main_menu import MainMenuScreen
            self.app.switch_screen(MainMenuScreen())
        else:
            self.attempts += 1
            remaining = self.max_attempts - self.attempts

            if remaining > 0:
                error_label.update(
                    f"[error]Wrong password. {remaining} attempt(s) remaining.[/error]"
                )
                password_input.value = ""
                password_input.focus()
            else:
                error_label.update("[error]Too many failed attempts. Goodbye.[/error]")
                self.app.exit()

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

        if len(password) < 8:
            error_label.update("[error]Password must be at least 8 characters[/error]")
            return

        if password != confirm:
            error_label.update("[error]Passwords don't match[/error]")
            confirm_input.value = ""
            confirm_input.focus()
            return

        if app.create_vault(password):
            # Success - go to main menu
            from passfx.screens.main_menu import MainMenuScreen
            self.app.switch_screen(MainMenuScreen())
        else:
            error_label.update("[error]Failed to create vault[/error]")
