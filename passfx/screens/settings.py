"""Settings Screen for PassFX."""
# pylint: disable=duplicate-code

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from passfx.utils.io import ImportExportError, export_vault, import_vault

if TYPE_CHECKING:
    from passfx.app import PassFXApp


class ExportModal(ModalScreen[None]):
    """Modal for exporting vault data."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="modal-container"):
            yield Static("Export Vault", id="modal-title")

            with Vertical(id="modal-content"):
                yield Label("Export Format:")
                yield OptionList(
                    Option("JSON (encrypted backup)", id="json"),
                    Option("CSV (readable, includes passwords!)", id="csv"),
                    id="format-select",
                )

                yield Label("Export Path:")
                yield Input(
                    value=str(Path.home() / "passfx_export.json"),
                    id="path-input",
                )

                yield Static("", id="export-status")

            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel-button")
                yield Button("Export", variant="primary", id="export-button")

    def on_mount(self) -> None:
        """Focus format select."""
        self.query_one("#format-select", OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Update path based on format."""
        fmt = event.option.id
        path_input = self.query_one("#path-input", Input)
        current = Path(path_input.value)
        new_path = current.with_suffix(f".{fmt}")
        path_input.value = str(new_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "export-button":
            self._export()

    def _export(self) -> None:
        """Export the vault."""
        app: PassFXApp = self.app  # type: ignore
        status = self.query_one("#export-status", Static)

        path_str = self.query_one("#path-input", Input).value
        path = Path(path_str).expanduser()

        # Determine format from extension
        fmt = "json" if path.suffix == ".json" else "csv"

        try:
            data = app.vault.get_all_data()
            count = export_vault(data, path, fmt=fmt, include_sensitive=True)
            status.update(f"[success]Exported {count} entries to {path}[/success]")
            self.notify(f"Exported {count} entries", title="Success")
        except ImportExportError as e:
            status.update(f"[error]{e}[/error]")

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class ImportModal(ModalScreen[None]):
    """Modal for importing vault data."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="modal-container"):
            yield Static("Import Data", id="modal-title")

            with Vertical(id="modal-content"):
                yield Label("Import File Path:")
                yield Input(placeholder="/path/to/file.json", id="path-input")

                yield Static("", id="import-status")

            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel-button")
                yield Button("Import", variant="primary", id="import-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "import-button":
            self._import()

    def _import(self) -> None:
        """Import vault data."""
        app: PassFXApp = self.app  # type: ignore
        status = self.query_one("#import-status", Static)

        path_str = self.query_one("#path-input", Input).value.strip()
        if not path_str:
            status.update("[error]Please enter a file path[/error]")
            return

        path = Path(path_str).expanduser()
        if not path.exists():
            status.update(f"[error]File not found: {path}[/error]")
            return

        try:
            data, _ = import_vault(path)
            imported = app.vault.import_data(data, merge=True)
            total = sum(imported.values())
            status.update(f"[success]Imported {total} entries[/success]")
            self.notify(f"Imported {total} entries", title="Success")
        except ImportExportError as e:
            status.update(f"[error]{e}[/error]")

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class SettingsScreen(Screen):
    """Screen for settings and vault management."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Create the settings screen layout."""
        yield Header()

        with Vertical():
            yield Static(
                "[bold #8b949e]╔════════════════════════════════════╗[/]\n"
                "[bold #8b949e]║[/]         [bold #8b949e]SETTINGS[/]         [bold #8b949e]║[/]\n"
                "[bold #8b949e]╚════════════════════════════════════╝[/]",
                classes="title",
            )

            yield OptionList(
                Option("Export Vault", id="export"),
                Option("Import Data", id="import"),
                Option("─────────────────────────", id="sep1", disabled=True),
                Option("Vault Statistics", id="stats"),
                Option("─────────────────────────", id="sep2", disabled=True),
                Option("Back", id="back"),
                id="settings-menu",
            )

            # Stats display
            yield Static("", id="stats-display", classes="box")

        yield Footer()

    def on_mount(self) -> None:
        """Focus menu and show stats."""
        self.query_one("#settings-menu", OptionList).focus()
        self._show_stats()

    def _show_stats(self) -> None:
        """Display vault statistics."""
        app: PassFXApp = self.app  # type: ignore
        stats_display = self.query_one("#stats-display", Static)

        if not app._unlocked:  # pylint: disable=protected-access
            stats_display.update("Vault is locked")
            return

        stats = app.vault.get_stats()
        stats_text = (
            f"[bold]Vault Statistics[/bold]\n\n"
            f"  Passwords:      {stats.get('emails', 0):>5}\n"
            f"  Phone PINs:     {stats.get('phones', 0):>5}\n"
            f"  Credit Cards:   {stats.get('cards', 0):>5}\n"
            f"  {'─' * 24}\n"
            f"  [bold]Total:          {stats.get('total', 0):>5}[/bold]"
        )
        stats_display.update(stats_text)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle menu selection."""
        option_id = event.option.id

        if option_id == "export":
            self.app.push_screen(ExportModal())
        elif option_id == "import":

            def refresh_stats(_: None) -> None:
                self._show_stats()

            self.app.push_screen(ImportModal(), refresh_stats)
        elif option_id == "stats":
            self._show_stats()
        elif option_id == "back":
            self.action_back()

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()
