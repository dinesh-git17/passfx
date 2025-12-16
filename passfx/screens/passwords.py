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
        with Vertical(id="pwd-modal", classes="secure-terminal"):
            # Header
            yield Static(":: SYSTEM_ENTRY // CREDENTIAL ::", id="modal-title")

            # Form Body
            with Vertical(id="pwd-form"):
                # Row 1: Label (System)
                yield Label("TARGET_SYSTEM", classes="input-label")
                yield Input(placeholder="e.g. GITHUB_MAIN", id="label-input")

                # Row 2: Email (Identity)
                yield Label("USER_IDENTITY", classes="input-label")
                yield Input(placeholder="username@host", id="email-input")

                # Row 3: Password (Secret)
                yield Label("ACCESS_KEY", classes="input-label")
                with Horizontal(classes="input-row"):
                    yield Input(placeholder="••••••••••••", password=True, id="password-input")

                # Row 4: Notes
                yield Label("METADATA", classes="input-label")
                yield Input(placeholder="OPTIONAL_NOTES", id="notes-input")

            # Footer Actions
            with Horizontal(id="modal-buttons"):
                yield Button("[ESC] ABORT", id="cancel-button")
                yield Button("[ENTER] ENCRYPT & WRITE", variant="primary", id="save-button")

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
        with Vertical(id="pwd-modal", classes="secure-terminal"):
            yield Static(f":: MODIFY_ENTRY // {self.credential.label.upper()} ::", id="modal-title")

            with Vertical(id="pwd-form"):
                yield Label("TARGET_SYSTEM", classes="input-label")
                yield Input(
                    value=self.credential.label,
                    placeholder="e.g. GITHUB_MAIN",
                    id="label-input",
                )

                yield Label("USER_IDENTITY", classes="input-label")
                yield Input(
                    value=self.credential.email,
                    placeholder="username@host",
                    id="email-input",
                )

                yield Label("ACCESS_KEY [BLANK = KEEP CURRENT]", classes="input-label")
                with Horizontal(classes="input-row"):
                    yield Input(placeholder="••••••••••••", password=True, id="password-input")

                yield Label("METADATA", classes="input-label")
                yield Input(
                    value=self.credential.notes or "",
                    placeholder="OPTIONAL_NOTES",
                    id="notes-input",
                )

            with Horizontal(id="modal-buttons"):
                yield Button("[ESC] ABORT", id="cancel-button")
                yield Button("[ENTER] ENCRYPT & WRITE", variant="primary", id="save-button")

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
        with Vertical(id="pwd-modal", classes="secure-terminal"):
            yield Static(":: CONFIRM_DELETE // WARNING ::", id="modal-title")

            with Vertical(id="pwd-form"):
                yield Static(f"TARGET: '{self.item_name}'", classes="delete-target")
                yield Static("⚠ THIS ACTION CANNOT BE UNDONE", classes="warning")

            with Horizontal(id="modal-buttons"):
                yield Button("[ESC] ABORT", id="cancel-button")
                yield Button("[Y] CONFIRM DELETE", variant="error", id="delete-button")

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
                with Horizontal(classes="pane-header"):
                    yield Static("[dim #555555]\\[///][/] CREDENTIAL_DATABASE.DB")
                yield DataTable(id="passwords-table", cursor_type="row")

            # Right Pane: Inspector (Detail) - 35%
            with Vertical(id="vault-inspector"):
                with Horizontal(classes="pane-header"):
                    yield Static("[bold #60a5fa]ITEM_PROPERTIES[/]")
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
            masked_pwd = f"[#475569]{'█' * min(len(cred.password), 8)}[/]"  # Muted blocks
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
        """Update the inspector panel with credential details.

        Renders a high-fidelity "Identity Analysis Module" with:
        - Digital ID Card header with avatar
        - Security Telemetry with 20-char segmented gauge
        - Metadata Grid with ID and timestamps
        - Notes Terminal with shell-style output
        """
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
                "[dim #555555]╔══════════════════════════╗\n"
                "║    SELECT AN ENTRY       ║\n"
                "║    TO VIEW DETAILS       ║\n"
                "╚══════════════════════════╝[/]",
                classes="inspector-empty"
            ))
            return

        # Build detail view
        from datetime import datetime
        from passfx.utils.strength import check_strength

        # ═══════════════════════════════════════════════════════════════
        # SECTION 1: Digital ID Card Header
        # ═══════════════════════════════════════════════════════════════
        inspector.mount(Vertical(
            Horizontal(
                Static("[bold #00d4ff]\\[[/] [bold #3b82f6]◈[/] [bold #00d4ff]\\][/]", classes="id-avatar-icon"),
                Vertical(
                    Static(f"[bold #f8fafc]{cred.label}[/]", classes="id-label"),
                    Static(f"[#00d4ff]{cred.email}[/]", classes="id-email"),
                    classes="id-info-stack",
                ),
                classes="id-card-row",
            ),
            Static("[dim #475569]" + "─" * 30 + "[/]", classes="id-separator"),
            classes="id-card",
        ))

        # ═══════════════════════════════════════════════════════════════
        # SECTION 2: Security Telemetry
        # ═══════════════════════════════════════════════════════════════
        strength = check_strength(cred.password)
        strength_colors = {
            0: "#ef4444",  # Red - Very Weak
            1: "#f87171",  # Light Red - Weak
            2: "#f59e0b",  # Amber - Fair
            3: "#60a5fa",  # Blue - Good
            4: "#22c55e",  # Green - Strong
        }
        color = strength_colors.get(strength.score, "#94a3b8")

        # Build 20-character segmented gauge
        # Each score level fills 4 chars (0=4, 1=8, 2=12, 3=16, 4=20)
        filled_count = (strength.score + 1) * 4
        empty_count = 20 - filled_count
        filled_char = "│"
        empty_char = "·"
        filled = f"[{color}]" + (filled_char * filled_count) + "[/]" if filled_count > 0 else ""
        empty = f"[#1e293b]" + (empty_char * empty_count) + "[/]" if empty_count > 0 else ""
        # Escape literal brackets with \[
        gauge = f"\\[ {filled}{empty} \\]"

        inspector.mount(Vertical(
            Static("[dim #6b7280]▸ SECURITY_TELEMETRY[/]", classes="section-header"),
            Static(f"{gauge}", classes="security-gauge"),
            Static(f"[{color}]{strength.label.upper()}[/]", classes="strength-label"),
            Static(f"[dim #6b7280]RESISTANCE:[/] [bold #94a3b8]{strength.crack_time}[/]", classes="tech-readout"),
            classes="security-section",
        ))

        # ═══════════════════════════════════════════════════════════════
        # SECTION 3: Metadata Grid
        # ═══════════════════════════════════════════════════════════════
        try:
            updated = datetime.fromisoformat(cred.updated_at).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            updated = cred.updated_at or "Unknown"

        inspector.mount(Vertical(
            Static("[dim #6b7280]▸ METADATA[/]", classes="section-header"),
            Horizontal(
                Static("[dim #475569]ID[/]", classes="meta-label"),
                Static(f"[#94a3b8]{cred.id[:8]}[/]", classes="meta-value"),
                classes="meta-row",
            ),
            Horizontal(
                Static("[dim #475569]UPDATED[/]", classes="meta-label"),
                Static(f"[#94a3b8]{updated}[/]", classes="meta-value"),
                classes="meta-row",
            ),
            classes="metadata-section",
        ))

        # ═══════════════════════════════════════════════════════════════
        # SECTION 4: Notes Terminal
        # ═══════════════════════════════════════════════════════════════
        if cred.notes:
            notes_content = (
                f"[#22c55e]>_[/] [dim #6b7280]ACCESSING METADATA...[/]\n"
                f"[#22c55e]>_[/] [dim #6b7280]BEGIN_NOTES:[/]\n"
                f"[#94a3b8]   {cred.notes}[/]\n"
                f"[#22c55e]>_[/] [dim #6b7280]END_OF_FILE[/]"
            )
        else:
            notes_content = (
                f"[#22c55e]>_[/] [dim #6b7280]ACCESSING METADATA...[/]\n"
                f"[#475569]>_ NO_DATA_FOUND[/]"
            )

        inspector.mount(Vertical(
            Static("[dim #6b7280]▸ NOTES_TERMINAL[/]", classes="section-header"),
            Static(notes_content, classes="notes-content"),
            classes="notes-terminal",
        ))
