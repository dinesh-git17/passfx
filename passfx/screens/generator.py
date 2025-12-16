"""Password Generator Screen for PassFX."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from rich.text import Text
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    OptionList,
    Static,
)
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
    """Create a mode menu item with consistent formatting.

    Args:
        code: The short code (e.g., "1", "2", "3")
        label: The mode label

    Returns:
        Rich Text object with styling
    """
    text = Text()
    text.append(f"[{code}]", style="bold #3b82f6")
    text.append(f" {label}", style="bold white")
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
        3: "#60a5fa",  # Blue - Good
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
                yield Button("[ESC] ABORT", id="cancel-button")
                yield Button("[ENTER] ENCRYPT & SAVE", variant="primary", id="save-button")

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
    """Screen for generating passwords, passphrases, and PINs."""

    BINDINGS = [
        Binding("enter", "generate", "Generate", priority=False),
        Binding("f2", "copy", "Copy"),
        Binding("f3", "save_to_vault", "Save"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._generated = ""
        self._mode = "password"  # password, passphrase, pin
        self._pulse_state: bool = True

    def compose(self) -> ComposeResult:
        """Create the generator screen layout."""
        # 1. Global Header with Breadcrumbs
        with Horizontal(id="app-header"):
            yield Static(
                "[dim #64748b]HOME[/] [#475569]>[/] [dim #64748b]TOOLS[/] [#475569]>[/] [bold #00d4ff]GENERATOR[/]",
                id="header-branding",
            )
            yield Static(":: CRYPTO_GENERATOR ::", id="header-status")
            yield Static("", id="header-lock")

        # 2. Body (Master-Detail Split)
        with Horizontal(id="vault-body"):
            # Left Pane: Mode Selection (30%)
            with Vertical(id="generator-mode-pane"):
                yield Static(" :: GENERATOR_MODES ", classes="pane-header-block")

                yield OptionList(
                    Option(_make_mode_item("1", "STRONG PASSWORD"), id="password"),
                    Option(_make_mode_item("2", "MEMORABLE PHRASE"), id="passphrase"),
                    Option(_make_mode_item("3", "PIN CODE"), id="pin"),
                    id="mode-select",
                )

                yield Static(" |-- SYSTEM_READY", classes="pane-footer", id="mode-footer")

            # Right Pane: Generator Console (70%)
            with Vertical(id="generator-console"):
                yield Static(" :: CRYPTO_CONSOLE ", classes="pane-header-block")

                # Console Content Area
                with Vertical(id="console-content"):
                    # Section A: Configuration Panel
                    with Vertical(id="config-section"):
                        yield Static(
                            "[dim #6b7280]> CONFIGURATION[/]",
                            classes="console-section-label",
                        )

                        # Password Options (default visible)
                        with Vertical(id="password-options", classes="config-panel"):
                            yield Label("LENGTH:", classes="config-label")
                            yield Input(value="16", id="length-input")
                            yield Checkbox(
                                "Exclude ambiguous (0, O, l, 1)",
                                id="exclude-ambiguous",
                                value=True,
                            )
                            yield Checkbox(
                                "Safe symbols only (!@#$)",
                                id="safe-symbols",
                                value=False,
                            )

                        # Passphrase Options (hidden by default)
                        with Vertical(id="passphrase-options", classes="config-panel"):
                            yield Label("WORDS:", classes="config-label")
                            yield Input(value="4", id="words-input")
                            yield Label("SEPARATOR:", classes="config-label")
                            yield Input(value="-", id="separator-input")

                        # PIN Options (hidden by default)
                        with Vertical(id="pin-options", classes="config-panel"):
                            yield Label("DIGITS:", classes="config-label")
                            yield Input(value="6", id="pin-length-input")

                    # Section B: Output Display
                    with Vertical(id="output-section"):
                        yield Static(
                            "[dim #6b7280]> OUTPUT[/]",
                            classes="console-section-label",
                        )

                        # Result Display Box
                        yield Static("", id="result-display")

                        # Strength Analysis (matches passwords.py style)
                        with Vertical(id="strength-section"):
                            yield Static("", id="strength-bar")
                            yield Static("", id="crack-time")

                    # Section C: Action Deck
                    with Horizontal(id="action-deck"):
                        yield Button("GENERATE", id="generate-button", variant="primary")
                        yield Button("COPY", id="copy-button")
                        yield Button("SAVE TO VAULT", id="save-button")

        # 3. Global Footer
        with Horizontal(id="app-footer"):
            yield Static(" TOOLS ", id="footer-version")
            yield Static(
                " \\[ENTER] Generate  \\[F2] Copy  \\[F3] Save  \\[ESC] Back",
                id="footer-keys-static",
            )

    def on_mount(self) -> None:
        """Initialize the screen."""
        mode_select = self.query_one("#mode-select", OptionList)
        mode_select.focus()
        # Highlight first option
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
            header_lock.update("[#22c55e]* [bold]READY[/][/]")
        else:
            header_lock.update("[#166534]o [bold]READY[/][/]")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle mode selection."""
        if event.option.id:
            self._switch_mode(event.option.id)

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "generate-button":
            self.action_generate()
        elif event.button.id == "copy-button":
            self.action_copy()
        elif event.button.id == "save-button":
            self.action_save_to_vault()

    def action_generate(self) -> None:
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
            result_display.update(f"[bold #00ff00]{self._generated}[/]")

            # Show strength analysis (except for PIN)
            if self._mode != "pin":
                strength = check_strength(self._generated)
                color = _get_strength_color(strength.score)

                # Build block progress bar (20 chars wide) - matches passwords.py
                filled_blocks = (strength.score + 1) * 4  # 0=4, 1=8, 2=12, 3=16, 4=20
                empty_blocks = 20 - filled_blocks

                filled = f"[{color}]" + ("=" * filled_blocks) + "[/]"
                empty = "[#1e293b]" + ("-" * empty_blocks) + "[/]"
                progress = f"{filled}{empty}"

                label = _get_strength_label(strength.score)
                strength_bar.update(f"{progress} [{color}]{label}[/]")
                crack_time.update(
                    f"[dim #475569]Crack time:[/] [#94a3b8]{strength.crack_time}[/]"
                )
            else:
                # PIN doesn't get strength analysis
                strength_bar.update("[dim #475569]PIN mode - strength N/A[/]")
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
        """Go back to main menu."""
        self.app.pop_screen()
