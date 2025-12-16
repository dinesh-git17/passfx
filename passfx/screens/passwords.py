"""Passwords Screen for PassFX."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
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
        # 1. Global Header (matches MainMenuScreen pattern)
        with Horizontal(id="app-header"):
            yield Static("[bold #00d4ff]◄ PASSFX ►[/]", id="header-branding")
            yield Static("░░ SECURE DATA BANK ░░", id="header-status")
            yield Static("🔒 ENCRYPTED", id="header-lock")

        # 2. Body (Master-Detail Split)
        with Horizontal(id="vault-body"):
            # Left Pane: Data Grid (Master) - 65%
            with Vertical(id="vault-grid-pane"):
                yield Static("[dim #555555]\\[///][/] CREDENTIAL_DATABASE.DB", classes="pane-header")
                yield DataTable(id="passwords-table", cursor_type="row")

            # Right Pane: Inspector (Detail) - 35%
            with Vertical(id="vault-inspector"):
                yield Static("[bold #60a5fa]ITEM_PROPERTIES[/]", classes="pane-header")
                yield Vertical(id="inspector-content")  # Dynamic content here

        # 3. Global Footer (matches MainMenuScreen pattern)
        with Horizontal(id="app-footer"):
            yield Static(" VAULT ", id="footer-version")
            yield Static(" \\[A] Add  \\[C] Copy  \\[E] Edit  \\[D] Delete  \\[V] View  \\[ESC] Back", id="footer-keys-static")

    def on_mount(self) -> None:
        """Initialize the data table."""
        self._refresh_table()
        # Focus table and initialize inspector after layout is complete
        self.call_after_refresh(self._initialize_selection)

    def _initialize_selection(self) -> None:
        """Initialize table selection and inspector after render."""
        table = self.query_one("#passwords-table", DataTable)
        table.focus()
        if table.row_count > 0:
            # Move cursor to first row
            table.move_cursor(row=0)
            # Get the key from the first credential
            app: PassFXApp = self.app  # type: ignore
            credentials = app.vault.get_emails()
            if credentials:
                self._update_inspector(credentials[0].id)
        else:
            self._update_inspector(None)

    def _refresh_table(self) -> None:
        """Refresh the data table with credentials."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#passwords-table", DataTable)

        table.clear(columns=True)
        # Add columns - total ~105 to fit 65% pane minus border
        table.add_column("#", width=5)
        table.add_column("Label", width=18)
        table.add_column("Email", width=28)
        table.add_column("Password", width=12)
        table.add_column("Updated", width=18)
        table.add_column("Notes", width=24)

        from datetime import datetime

        credentials = app.vault.get_emails()
        for i, cred in enumerate(credentials, 1):
            masked_pwd = "█" * min(len(cred.password), 8)  # Block character U+2588
            # Format updated_at timestamp
            try:
                updated = datetime.fromisoformat(cred.updated_at).strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                updated = cred.updated_at or "-"
            notes = (cred.notes[:20] + "...") if cred.notes and len(cred.notes) > 20 else (cred.notes or "-")
            table.add_row(str(i), cred.label, cred.email, masked_pwd, updated, notes, key=cred.id)

    def _get_selected_credential(self) -> EmailCredential | None:
        """Get the currently selected credential."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#passwords-table", DataTable)

        if table.cursor_row is None:
            return None

        # Get credentials and find by cursor row index
        credentials = app.vault.get_emails()
        if 0 <= table.cursor_row < len(credentials):
            return credentials[table.cursor_row]
        return None

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

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update inspector panel when a row is highlighted."""
        # row_key is a RowKey object, get its value
        key_value = event.row_key.value if hasattr(event.row_key, 'value') else str(event.row_key)
        self._update_inspector(key_value)

    def _update_inspector(self, row_key: Any) -> None:
        """Update the inspector panel with credential details."""
        inspector = self.query_one("#inspector-content", Vertical)
        inspector.remove_children()

        # Get the credential by row key
        app: PassFXApp = self.app  # type: ignore
        credentials = app.vault.get_emails()

        # Find credential by ID
        cred = None
        for c in credentials:
            if c.id == str(row_key):
                cred = c
                break

        if not cred:
            # Empty state
            inspector.mount(Static(
                "[dim #555555]╔══════════════════╗\n"
                "║   NO SELECTION   ║\n"
                "╚══════════════════╝[/]",
                classes="inspector-empty"
            ))
            return

        # Build detail view
        from datetime import datetime
        from passfx.utils.strength import check_strength

        # Title
        inspector.mount(Label(f"[bold #60a5fa]{cred.label}[/]", classes="inspector-title"))

        # Metadata section
        inspector.mount(Static(f"[dim]ID:[/] {cred.id}", classes="inspector-field"))
        inspector.mount(Static(f"[dim]Email:[/] {cred.email}", classes="inspector-field"))

        # Password strength indicator
        strength = check_strength(cred.password)
        strength_bar = "█" * strength.score + "░" * (4 - strength.score)
        strength_colors = {0: "#ef4444", 1: "#ef4444", 2: "#f59e0b", 3: "#60a5fa", 4: "#22c55e"}
        color = strength_colors.get(strength.score, "#94a3b8")
        inspector.mount(Static(f"[dim]Strength:[/] [{color}]{strength_bar}[/] [{color}]{strength.score}/4[/]", classes="inspector-field"))

        # Dates
        try:
            created = datetime.fromisoformat(cred.created_at).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            created = cred.created_at or "Unknown"
        try:
            updated = datetime.fromisoformat(cred.updated_at).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            updated = cred.updated_at or "Unknown"

        inspector.mount(Static(f"[dim]Created:[/] {created}", classes="inspector-field"))
        inspector.mount(Static(f"[dim]Updated:[/] {updated}", classes="inspector-field"))

        # Notes section (if present)
        if cred.notes:
            inspector.mount(Static("", classes="inspector-spacer"))  # Spacer
            inspector.mount(Static("[dim]─── NOTES ───[/]", classes="inspector-section"))
            inspector.mount(Static(cred.notes, classes="inspector-notes"))
