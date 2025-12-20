"""Password Generator Screen for PassFX - Crypto Generation Console."""

# pylint: disable=duplicate-code

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markup import escape
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Checkbox, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from passfx.core.models import EmailCredential
from passfx.utils.clipboard import copy_to_clipboard
from passfx.utils.generator import generate_passphrase, generate_password, generate_pin
from passfx.utils.strength import check_strength

if TYPE_CHECKING:
    from passfx.app import PassFXApp


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def _make_mode_item(code: str, label: str) -> Text:
    """Create a mode menu item with Operator theme styling.

    Args:
        code: The short code (e.g., "PWD", "PHR", "PIN")
        label: The mode label

    Returns:
        Rich Text object with [ CODE ] prefix decoration
    """
    text = Text()
    text.append("[", style="bold #00FFFF")
    text.append(f"{code:^5}", style="bold #00FFFF")
    text.append("]", style="bold #00FFFF")
    text.append(f" {label}", style="white")
    return text


def _get_strength_color(score: int) -> str:
    """Get hex color for strength score.

    Args:
        score: Strength score 0-4.

    Returns:
        Hex color string.
    """
    colors = {
        0: "#ef4444",  # Red - Very Weak
        1: "#f87171",  # Light Red - Weak
        2: "#f59e0b",  # Amber - Fair
        3: "#00FFFF",  # Cyan - Good
        4: "#22c55e",  # Green - Strong
    }
    return colors.get(score, "#94a3b8")


def _get_strength_label(score: int) -> str:
    """Get strength label for score.

    Args:
        score: Strength score 0-4.

    Returns:
        Human-readable strength label.
    """
    labels = {
        0: "CRITICAL",
        1: "WEAK",
        2: "FAIR",
        3: "GOOD",
        4: "STRONG",
    }
    return labels.get(score, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════════════
# MODAL: SAVE GENERATED TO VAULT
# ═══════════════════════════════════════════════════════════════════════════════


class SaveGeneratedModal(ModalScreen[EmailCredential | None]):
    """Modal for saving a generated password/passphrase to the vault."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, generated_value: str) -> None:
        super().__init__()
        self._generated_value = generated_value

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="pwd-modal", classes="secure-terminal"):
            yield Static(":: SAVE_TO_VAULT // NEW_ENTRY ::", id="modal-title")

            with Vertical(id="pwd-form"):
                yield Label("TARGET_SYSTEM", classes="input-label")
                yield Input(placeholder="e.g. GITHUB_MAIN", id="label-input")

                yield Label("USER_IDENTITY", classes="input-label")
                yield Input(placeholder="username@host", id="email-input")

                yield Label("GENERATED_KEY [READ-ONLY]", classes="input-label")
                yield Input(
                    value=self._generated_value,
                    id="password-input",
                    disabled=True,
                )

                yield Label("METADATA", classes="input-label")
                yield Input(placeholder="OPTIONAL_NOTES", id="notes-input")

            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ESC] ABORT", id="cancel-button")
                yield Button(
                    "[ENTER] ENCRYPT & SAVE", variant="primary", id="save-button"
                )

    def on_mount(self) -> None:
        """Focus first input."""
        self.query_one("#label-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            self._save()

    def _save(self) -> None:
        """Save the credential."""
        label = self.query_one("#label-input", Input).value.strip()
        email = self.query_one("#email-input", Input).value.strip()
        notes = self.query_one("#notes-input", Input).value.strip()

        if not label or not email:
            self.notify("Label and identity are required", severity="error")
            return

        credential = EmailCredential(
            label=label,
            email=email,
            password=self._generated_value,
            notes=notes if notes else None,
        )
        self.dismiss(credential)

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATOR SCREEN
# ═══════════════════════════════════════════════════════════════════════════════


class GeneratorScreen(Screen):
    """Crypto Generation Console - Operator Theme."""

    BINDINGS = [
        Binding("g", "generate", "Generate"),
        Binding("c", "copy", "Copy"),
        Binding("s", "save_to_vault", "Save"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._generated = ""
        self._mode = "password"  # password, passphrase, pin
        self._pulse_state: bool = True

    def compose(self) -> ComposeResult:
        """Create the generator screen layout - Operator Theme."""
        # Header - Command Bar
        with Horizontal(id="app-header"):
            yield Static(
                "[bold #00FFFF]:: CRYPTO_GENERATOR ::[/]",
                id="header-branding",
            )
            with Horizontal(id="header-right"):
                yield Static("", id="header-clock")
                yield Static("", id="header-lock")

        # Main Body - Horizontal Split Layout
        with Horizontal(id="vault-body"):
            # Left Pane: Mode Selection (30%)
            with Vertical(id="generator-mode-pane"):
                yield Static(" :: GENERATION_MODES ", classes="pane-header-block-cyan")

                yield OptionList(
                    Option(_make_mode_item("PWD", "Strong Password"), id="password"),
                    Option(_make_mode_item("PHR", "Memorable Phrase"), id="passphrase"),
                    Option(_make_mode_item("PIN", "PIN Code"), id="pin"),
                    id="mode-select",
                )

                yield Static(
                    " |-- SYSTEM_READY", classes="pane-footer", id="mode-footer"
                )

            # Right Pane: Generator Console (70%)
            with Vertical(id="generator-console"):
                yield Static(" :: CONFIGURATION ", classes="pane-header-block-cyan")

                # Password Options (default visible) - Compact horizontal layout
                with Horizontal(id="password-options", classes="gen-config-row"):
                    with Vertical(classes="gen-config-field"):
                        yield Label("> LENGTH", classes="gen-config-label")
                        yield Input(value="16", placeholder="8-128", id="length-input")
                    with Vertical(classes="gen-config-field"):
                        yield Checkbox(
                            "No ambiguous",
                            id="exclude-ambiguous",
                            value=True,
                        )
                        yield Checkbox(
                            "Safe symbols",
                            id="safe-symbols",
                            value=False,
                        )

                # Passphrase Options (hidden by default) - Compact horizontal layout
                with Horizontal(id="passphrase-options", classes="gen-config-row"):
                    with Vertical(classes="gen-config-field"):
                        yield Label("> WORDS", classes="gen-config-label")
                        yield Input(value="4", placeholder="3-10", id="words-input")
                    with Vertical(classes="gen-config-field"):
                        yield Label("> SEPARATOR", classes="gen-config-label")
                        yield Input(value="-", id="separator-input")

                # PIN Options (hidden by default) - Compact layout
                with Horizontal(id="pin-options", classes="gen-config-row"):
                    with Vertical(classes="gen-config-field"):
                        yield Label("> DIGITS", classes="gen-config-label")
                        yield Input(
                            value="6", placeholder="4-12", id="pin-length-input"
                        )

                # Secure Output Section - takes remaining space
                yield Static(" :: SECURE_OUTPUT ", classes="pane-header-block-cyan")

                with Vertical(id="output-panel"):
                    yield Static("", id="result-display")
                    with Horizontal(id="strength-section"):
                        yield Static("", id="strength-bar")
                        yield Static("", id="crack-time")

        # Footer - Mechanical Keycap Command Strip
        with Horizontal(id="app-footer"):
            yield Static(" GENERATOR ", id="footer-version")
            with Horizontal(id="footer-keys"):
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #00FFFF] G [/]", classes="keycap")
                    yield Static("[#666666]Generate[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #00FFFF] C [/]", classes="keycap")
                    yield Static("[#666666]Copy[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #00FFFF] S [/]", classes="keycap")
                    yield Static("[#666666]Save[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #00FFFF] ^K [/]", classes="keycap")
                    yield Static("[#666666]Search[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #00FFFF] ESC [/]", classes="keycap")
                    yield Static("[#666666]Back[/]", classes="keycap-label")

    def on_mount(self) -> None:
        """Initialize the screen."""
        mode_select = self.query_one("#mode-select", OptionList)
        mode_select.focus()
        mode_select.highlighted = 0

        # Hide passphrase and pin options initially
        self.query_one("#passphrase-options").display = False
        self.query_one("#pin-options").display = False

        # Generate initial password
        self.call_after_refresh(self.action_generate)

        # Start pulse animation
        self._update_pulse()
        self.set_interval(1.0, self._update_pulse)

    def _update_pulse(self) -> None:
        """Update the pulse indicator in the header."""
        self._pulse_state = not self._pulse_state
        header_lock = self.query_one("#header-lock", Static)
        if self._pulse_state:
            header_lock.update("[#22c55e]● [bold]READY[/][/]")
        else:
            header_lock.update("[#166534]○ [bold]READY[/][/]")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle mode selection."""
        if event.option.id:
            self._switch_mode(event.option.id)

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        """Handle mode highlight change (live preview)."""
        if event.option.id:
            self._switch_mode(event.option.id)

    def _switch_mode(self, mode: str) -> None:
        """Switch generator mode and update UI.

        Args:
            mode: One of 'password', 'passphrase', 'pin'.
        """
        if mode == self._mode:
            return

        self._mode = mode

        # Show/hide relevant options
        self.query_one("#password-options").display = mode == "password"
        self.query_one("#passphrase-options").display = mode == "passphrase"
        self.query_one("#pin-options").display = mode == "pin"

        # Update footer with mode info
        mode_names = {
            "password": "PASSWORD_MODE",
            "passphrase": "PASSPHRASE_MODE",
            "pin": "PIN_MODE",
        }
        footer = self.query_one("#mode-footer", Static)
        footer.update(f" |-- {mode_names.get(mode, 'UNKNOWN')}")

        # Auto-generate for new mode
        self.action_generate()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Auto-regenerate when config changes."""
        if event.input.id in (
            "length-input",
            "words-input",
            "separator-input",
            "pin-length-input",
        ):
            self.action_generate()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Auto-regenerate when checkbox changes."""
        if event.checkbox.id in ("exclude-ambiguous", "safe-symbols"):
            self.action_generate()

    def action_generate(self) -> None:  # pylint: disable=too-many-locals
        """Generate based on current mode and options."""
        result_display = self.query_one("#result-display", Static)
        strength_bar = self.query_one("#strength-bar", Static)
        crack_time = self.query_one("#crack-time", Static)

        try:
            if self._mode == "password":
                length_str = self.query_one("#length-input", Input).value
                length = int(length_str) if length_str else 16
                exclude_ambiguous = self.query_one("#exclude-ambiguous", Checkbox).value
                safe_symbols = self.query_one("#safe-symbols", Checkbox).value

                self._generated = generate_password(
                    length=max(8, min(128, length)),
                    exclude_ambiguous=exclude_ambiguous,
                    safe_symbols=safe_symbols,
                )

            elif self._mode == "passphrase":
                words_str = self.query_one("#words-input", Input).value
                words = int(words_str) if words_str else 4
                separator = self.query_one("#separator-input", Input).value or "-"

                self._generated = generate_passphrase(
                    word_count=max(3, min(10, words)),
                    separator=separator,
                )

            elif self._mode == "pin":
                length_str = self.query_one("#pin-length-input", Input).value
                length = int(length_str) if length_str else 6
                self._generated = generate_pin(max(4, min(12, length)))

            # Update result display with bright green terminal output
            # Escape special chars to prevent Rich markup interpretation
            safe_output = escape(self._generated)
            result_display.update(f"[bold #22c55e]{safe_output}[/]")

            # Flash effect on output panel
            output_panel = self.query_one("#output-panel", Vertical)
            output_panel.add_class("flash-generate")
            self.set_timer(0.2, lambda: output_panel.remove_class("flash-generate"))

            # Show strength analysis (except for PIN)
            if self._mode != "pin":
                strength = check_strength(self._generated)
                color = _get_strength_color(strength.score)

                # Build block progress bar (20 chars wide)
                filled_blocks = (strength.score + 1) * 4  # 0=4, 1=8, 2=12, 3=16, 4=20
                empty_blocks = 20 - filled_blocks

                filled = f"[{color}]" + ("█" * filled_blocks) + "[/]"
                empty = "[#333333]" + ("░" * empty_blocks) + "[/]"
                progress = f"{filled}{empty}"

                label = _get_strength_label(strength.score)
                strength_bar.update(f"{progress} [{color}]{label}[/]")
                crack_time.update(
                    f"[dim #666666]Crack time:[/] [#94a3b8]{strength.crack_time}[/]"
                )
            else:
                # PIN doesn't get strength analysis
                strength_bar.update("[dim #666666]PIN mode - strength N/A[/]")
                crack_time.update("")

        except (ValueError, TypeError) as e:
            result_display.update(f"[#ef4444]ERROR: {e}[/]")
            strength_bar.update("")
            crack_time.update("")

    def action_copy(self) -> None:
        """Copy generated value to clipboard."""
        if not self._generated:
            self.notify("Generate a value first", severity="warning")
            return

        if copy_to_clipboard(self._generated, auto_clear=True, clear_after=30):
            self.notify("Copied! Auto-clears in 30s", title="CLIPBOARD")
            # Flash effect on copy
            output_panel = self.query_one("#output-panel", Vertical)
            output_panel.add_class("flash-copy")
            self.set_timer(0.3, lambda: output_panel.remove_class("flash-copy"))
        else:
            self.notify("Clipboard operation failed", severity="error")

    def action_save_to_vault(self) -> None:
        """Save the generated value to the vault."""
        if not self._generated:
            self.notify("Generate a value first", severity="warning")
            return

        if self._mode == "pin":
            self.notify("PINs cannot be saved as passwords", severity="warning")
            return

        def handle_result(credential: EmailCredential | None) -> None:
            if credential:
                app: PassFXApp = self.app  # type: ignore
                app.vault.add_email(credential)
                self.notify(f"Saved '{credential.label}' to vault", title="SUCCESS")

        self.app.push_screen(SaveGeneratedModal(self._generated), handle_result)

    def action_back(self) -> None:
        """Handle escape - first focuses mode selector, second exits."""
        mode_select = self.query_one("#mode-select", OptionList)
        if self.focused != mode_select:
            # First ESC: focus the mode selector
            mode_select.focus()
        else:
            # Second ESC: exit to main menu
            self.app.pop_screen()
