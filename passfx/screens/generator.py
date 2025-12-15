"""Password Generator Screen for PassFX."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option

from passfx.utils.clipboard import copy_to_clipboard
from passfx.utils.generator import generate_passphrase, generate_password, generate_pin
from passfx.utils.strength import check_strength


class GeneratorScreen(Screen):
    """Screen for generating passwords, passphrases, and PINs."""

    BINDINGS = [
        Binding("g", "generate", "Generate"),
        Binding("c", "copy", "Copy"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._generated = ""
        self._mode = "password"  # password, passphrase, pin

    def compose(self) -> ComposeResult:
        """Create the generator screen layout."""
        yield Header()

        with Vertical():
            yield Static(
                "[bold #00ff88]╔══════════════════════════════════════╗[/]\n"
                "[bold #00ff88]║[/]     [bold #00ff88]PASSWORD GENERATOR[/]     [bold #00ff88]║[/]\n"
                "[bold #00ff88]╚══════════════════════════════════════╝[/]",
                classes="title",
            )

            # Mode selection
            yield Label("Select Type:", classes="subtitle")
            yield OptionList(
                Option("Strong Password", id="password"),
                Option("Memorable Passphrase", id="passphrase"),
                Option("PIN Code", id="pin"),
                id="mode-select",
            )

            # Password options
            with Vertical(id="password-options"):
                yield Label("Length:")
                yield Input(value="16", id="length-input", type="integer")

                with Horizontal():
                    yield Checkbox("Exclude ambiguous (0, O, l, 1)", id="exclude-ambiguous", value=True)

                with Horizontal():
                    yield Checkbox("Safe symbols only", id="safe-symbols", value=False)

            # Passphrase options (hidden by default)
            with Vertical(id="passphrase-options"):
                yield Label("Number of words:")
                yield Input(value="4", id="words-input", type="integer")

                yield Label("Separator:")
                yield Input(value="-", id="separator-input")

            # PIN options (hidden by default)
            with Vertical(id="pin-options"):
                yield Label("PIN length:")
                yield Input(value="6", id="pin-length-input", type="integer")

            # Generate button
            yield Button("Generate", variant="primary", id="generate-button")

            # Result display
            yield Static("", id="result-display", classes="box")
            yield Static("", id="strength-display")

            # Action buttons
            with Horizontal(id="action-bar"):
                yield Button("Generate", id="gen-button")
                yield Button("Copy", id="copy-button")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the screen."""
        self.query_one("#mode-select", OptionList).focus()
        # Hide passphrase and pin options initially
        self.query_one("#passphrase-options").display = False
        self.query_one("#pin-options").display = False

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle mode selection."""
        mode = event.option.id
        self._mode = mode

        # Show/hide relevant options
        self.query_one("#password-options").display = mode == "password"
        self.query_one("#passphrase-options").display = mode == "passphrase"
        self.query_one("#pin-options").display = mode == "pin"

        # Auto-generate
        self.action_generate()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id in ("generate-button", "gen-button"):
            self.action_generate()
        elif event.button.id == "copy-button":
            self.action_copy()

    def action_generate(self) -> None:
        """Generate based on current mode and options."""
        result_display = self.query_one("#result-display", Static)
        strength_display = self.query_one("#strength-display", Static)

        try:
            if self._mode == "password":
                length = int(self.query_one("#length-input", Input).value or "16")
                exclude_ambiguous = self.query_one("#exclude-ambiguous", Checkbox).value
                safe_symbols = self.query_one("#safe-symbols", Checkbox).value

                self._generated = generate_password(
                    length=max(8, min(128, length)),
                    exclude_ambiguous=exclude_ambiguous,
                    safe_symbols=safe_symbols,
                )

            elif self._mode == "passphrase":
                words = int(self.query_one("#words-input", Input).value or "4")
                separator = self.query_one("#separator-input", Input).value or "-"

                self._generated = generate_passphrase(
                    word_count=max(3, min(10, words)),
                    separator=separator,
                )

            elif self._mode == "pin":
                length = int(self.query_one("#pin-length-input", Input).value or "6")
                self._generated = generate_pin(max(4, min(12, length)))

            # Update display
            result_display.update(f"[bold bright_green]{self._generated}[/bold bright_green]")

            # Show strength
            if self._mode != "pin":
                strength = check_strength(self._generated)
                strength_display.update(
                    f"Strength: [{strength.color}]{strength.label}[/{strength.color}] | "
                    f"Crack time: {strength.crack_time}"
                )
            else:
                strength_display.update("")

        except Exception as e:
            result_display.update(f"[error]Error: {e}[/error]")

    def action_copy(self) -> None:
        """Copy generated value to clipboard."""
        if not self._generated:
            self.notify("Nothing to copy. Generate first!", severity="warning")
            return

        if copy_to_clipboard(self._generated, auto_clear=True, clear_after=30):
            self.notify("Copied to clipboard! Clears in 30s", title="Copied")
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()
