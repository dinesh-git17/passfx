"""Passwords Screen for PassFX."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
)

from passfx.core.models import EmailCredential
from passfx.utils.clipboard import copy_to_clipboard

if TYPE_CHECKING:
    from passfx.app import PassFXApp


class AddPasswordModal(ModalScreen[EmailCredential | None]):
    """Modal for adding a new password."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="modal-container"):
            yield Static("Add New Password", id="modal-title")

            with Vertical(id="modal-content"):
                yield Label("Label (e.g., GitHub, Gmail)")
                yield Input(placeholder="Label", id="label-input")

                yield Label("Email or Username")
                yield Input(placeholder="Email", id="email-input")

                yield Label("Password")
                yield Input(placeholder="Password", password=True, id="password-input")

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
        email = self.query_one("#email-input", Input).value.strip()
        password = self.query_one("#password-input", Input).value
        notes = self.query_one("#notes-input", Input).value.strip()

        if not label or not email or not password:
            self.notify("Please fill in all required fields", severity="error")
            return

        credential = EmailCredential(
            label=label,
            email=email,
            password=password,
            notes=notes if notes else None,
        )
        self.dismiss(credential)

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class EditPasswordModal(ModalScreen[dict | None]):
    """Modal for editing a password."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, credential: EmailCredential) -> None:
        super().__init__()
        self.credential = credential

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="modal-container"):
            yield Static(f"Edit: {self.credential.label}", id="modal-title")

            with Vertical(id="modal-content"):
                yield Label("Label")
                yield Input(
                    value=self.credential.label,
                    placeholder="Label",
                    id="label-input",
                )

                yield Label("Email or Username")
                yield Input(
                    value=self.credential.email,
                    placeholder="Email",
                    id="email-input",
                )

                yield Label("Password (leave empty to keep current)")
                yield Input(placeholder="New password", password=True, id="password-input")

                yield Label("Notes")
                yield Input(
                    value=self.credential.notes or "",
                    placeholder="Notes",
                    id="notes-input",
                )

            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel-button")
                yield Button("Save", variant="primary", id="save-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            self._save()

    def _save(self) -> None:
        """Save the changes."""
        label = self.query_one("#label-input", Input).value.strip()
        email = self.query_one("#email-input", Input).value.strip()
        password = self.query_one("#password-input", Input).value
        notes = self.query_one("#notes-input", Input).value.strip()

        if not label or not email:
            self.notify("Label and email are required", severity="error")
            return

        result = {
            "label": label,
            "email": email,
            "notes": notes if notes else None,
        }
        if password:
            result["password"] = password

        self.dismiss(result)

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class ConfirmDeleteModal(ModalScreen[bool]):
    """Modal for confirming deletion."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
    ]

    def __init__(self, item_name: str) -> None:
        super().__init__()
        self.item_name = item_name

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="modal-container"):
            yield Static("Confirm Delete", id="modal-title")

            with Vertical(id="modal-content"):
                yield Static(f"Delete '{self.item_name}'?")
                yield Static("This action cannot be undone.", classes="warning")

            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel-button")
                yield Button("Delete", variant="error", id="delete-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(False)
        elif event.button.id == "delete-button":
            self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel deletion."""
        self.dismiss(False)

    def action_confirm(self) -> None:
        """Confirm deletion."""
        self.dismiss(True)


class PasswordsScreen(Screen):
    """Screen for managing password credentials."""

    BINDINGS = [
        Binding("a", "add", "Add"),
        Binding("c", "copy", "Copy"),
        Binding("e", "edit", "Edit"),
        Binding("d", "delete", "Delete"),
        Binding("v", "view", "View"),
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Create the passwords screen layout."""
        yield Header()

        with Vertical():
            yield Static(
                "[bold #00d4ff]╔══════════════════════════════════════╗[/]\n"
                "[bold #00d4ff]║[/]       [bold #00d4ff]PASSWORD VAULT[/]       [bold #00d4ff]║[/]\n"
                "[bold #00d4ff]╚══════════════════════════════════════╝[/]",
                classes="title",
            )

            yield DataTable(id="passwords-table", cursor_type="row")

            with Horizontal(id="action-bar"):
                yield Button("Add", id="add-button")
                yield Button("Copy", id="copy-button")
                yield Button("Edit", id="edit-button")
                yield Button("Delete", id="delete-button", classes="-error")
                yield Button("View", id="view-button")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the data table."""
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh the data table with credentials."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#passwords-table", DataTable)

        table.clear(columns=True)
        table.add_columns("#", "Label", "Email", "Password", "Notes")

        credentials = app.vault.get_emails()
        for i, cred in enumerate(credentials, 1):
            masked_pwd = "*" * min(len(cred.password), 8)
            notes = (cred.notes[:20] + "...") if cred.notes and len(cred.notes) > 20 else (cred.notes or "-")
            table.add_row(str(i), cred.label, cred.email, masked_pwd, notes, key=cred.id)

        if credentials:
            table.focus()

    def _get_selected_credential(self) -> EmailCredential | None:
        """Get the currently selected credential."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#passwords-table", DataTable)

        if table.cursor_row is None:
            return None

        try:
            row_key = table.get_row_at(table.cursor_row)
            cred_id = table.get_row_key(row_key).value if hasattr(table.get_row_key(row_key), 'value') else str(row_key)
        except Exception:
            return None

        # Get credentials and find by index
        credentials = app.vault.get_emails()
        if 0 <= table.cursor_row < len(credentials):
            return credentials[table.cursor_row]
        return None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        button_actions = {
            "add-button": self.action_add,
            "copy-button": self.action_copy,
            "edit-button": self.action_edit,
            "delete-button": self.action_delete,
            "view-button": self.action_view,
        }
        action = button_actions.get(event.button.id)
        if action:
            action()

    def action_add(self) -> None:
        """Add a new credential."""
        def handle_result(credential: EmailCredential | None) -> None:
            if credential:
                app: PassFXApp = self.app  # type: ignore
                app.vault.add_email(credential)
                self._refresh_table()
                self.notify(f"Added '{credential.label}'", title="Success")

        self.app.push_screen(AddPasswordModal(), handle_result)

    def action_copy(self) -> None:
        """Copy password to clipboard."""
        cred = self._get_selected_credential()
        if not cred:
            self.notify("No credential selected", severity="warning")
            return

        if copy_to_clipboard(cred.password, auto_clear=True, clear_after=30):
            self.notify(f"Password copied! Clears in 30s", title=cred.label)
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_edit(self) -> None:
        """Edit selected credential."""
        cred = self._get_selected_credential()
        if not cred:
            self.notify("No credential selected", severity="warning")
            return

        def handle_result(changes: dict | None) -> None:
            if changes:
                app: PassFXApp = self.app  # type: ignore
                app.vault.update_email(cred.id, **changes)
                self._refresh_table()
                self.notify("Credential updated", title="Success")

        self.app.push_screen(EditPasswordModal(cred), handle_result)

    def action_delete(self) -> None:
        """Delete selected credential."""
        cred = self._get_selected_credential()
        if not cred:
            self.notify("No credential selected", severity="warning")
            return

        def handle_result(confirmed: bool) -> None:
            if confirmed:
                app: PassFXApp = self.app  # type: ignore
                app.vault.delete_email(cred.id)
                self._refresh_table()
                self.notify(f"Deleted '{cred.label}'", title="Deleted")

        self.app.push_screen(ConfirmDeleteModal(cred.label), handle_result)

    def action_view(self) -> None:
        """View credential details."""
        cred = self._get_selected_credential()
        if not cred:
            self.notify("No credential selected", severity="warning")
            return

        # Show details in notification for now
        details = f"Label: {cred.label}\nEmail: {cred.email}\nPassword: {cred.password}"
        if cred.notes:
            details += f"\nNotes: {cred.notes}"
        self.notify(details, title="Credential Details", timeout=10)

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()
