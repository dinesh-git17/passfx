"""Phones Screen for PassFX."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

from passfx.core.models import PhoneCredential
from passfx.utils.clipboard import copy_to_clipboard

if TYPE_CHECKING:
    from passfx.app import PassFXApp


class AddPhoneModal(ModalScreen[PhoneCredential | None]):
    """Modal for adding a new phone credential."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="modal-container"):
            yield Static("Add Phone Credential", id="modal-title")

            with Vertical(id="modal-content"):
                yield Label("Label (e.g., Bank PIN, Voicemail)")
                yield Input(placeholder="Label", id="label-input")

                yield Label("Phone Number")
                yield Input(placeholder="Phone", id="phone-input")

                yield Label("PIN or Password")
                yield Input(placeholder="PIN", password=True, id="pin-input")

                yield Label("Notes (optional)")
                yield Input(placeholder="Notes", id="notes-input")

            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel-button")
                yield Button("Save", variant="primary", id="save-button")

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
        phone = self.query_one("#phone-input", Input).value.strip()
        pin = self.query_one("#pin-input", Input).value
        notes = self.query_one("#notes-input", Input).value.strip()

        if not label or not phone or not pin:
            self.notify("Please fill in all required fields", severity="error")
            return

        credential = PhoneCredential(
            label=label,
            phone=phone,
            password=pin,
            notes=notes if notes else None,
        )
        self.dismiss(credential)

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class PhonesScreen(Screen):
    """Screen for managing phone credentials."""

    BINDINGS = [
        Binding("a", "add", "Add"),
        Binding("c", "copy", "Copy"),
        Binding("d", "delete", "Delete"),
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Create the phones screen layout."""
        yield Header()

        with Vertical():
            yield Static(
                "[bold #00d4ff]╔══════════════════════════════════════╗[/]\n"
                "[bold #00d4ff]║[/]     [bold #00d4ff]PHONE CREDENTIALS[/]     [bold #00d4ff]║[/]\n"
                "[bold #00d4ff]╚══════════════════════════════════════╝[/]",
                classes="title",
            )

            yield DataTable(id="phones-table", cursor_type="row")

            with Horizontal(id="action-bar"):
                yield Button("Add", id="add-button")
                yield Button("Copy", id="copy-button")
                yield Button("Delete", id="delete-button", classes="-error")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the data table."""
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh the data table."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#phones-table", DataTable)

        table.clear(columns=True)
        table.add_columns("#", "Label", "Phone", "PIN")

        credentials = app.vault.get_phones()
        for i, cred in enumerate(credentials, 1):
            masked_pin = "*" * min(len(cred.password), 6)
            table.add_row(str(i), cred.label, cred.phone, masked_pin, key=cred.id)

        if credentials:
            table.focus()

    def _get_selected_credential(self) -> PhoneCredential | None:
        """Get the currently selected credential."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#phones-table", DataTable)

        if table.cursor_row is None:
            return None

        credentials = app.vault.get_phones()
        if 0 <= table.cursor_row < len(credentials):
            return credentials[table.cursor_row]
        return None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "add-button":
            self.action_add()
        elif event.button.id == "copy-button":
            self.action_copy()
        elif event.button.id == "delete-button":
            self.action_delete()

    def action_add(self) -> None:
        """Add a new credential."""
        def handle_result(credential: PhoneCredential | None) -> None:
            if credential:
                app: PassFXApp = self.app  # type: ignore
                app.vault.add_phone(credential)
                self._refresh_table()
                self.notify(f"Added '{credential.label}'", title="Success")

        self.app.push_screen(AddPhoneModal(), handle_result)

    def action_copy(self) -> None:
        """Copy PIN to clipboard."""
        cred = self._get_selected_credential()
        if not cred:
            self.notify("No credential selected", severity="warning")
            return

        if copy_to_clipboard(cred.password, auto_clear=True, clear_after=30):
            self.notify(f"PIN copied! Clears in 30s", title=cred.label)
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_delete(self) -> None:
        """Delete selected credential."""
        cred = self._get_selected_credential()
        if not cred:
            self.notify("No credential selected", severity="warning")
            return

        # Simple confirmation via notify for now
        app: PassFXApp = self.app  # type: ignore
        app.vault.delete_phone(cred.id)
        self._refresh_table()
        self.notify(f"Deleted '{cred.label}'", title="Deleted")

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()
