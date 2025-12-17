"""Passwords Screen for PassFX."""
# pylint: disable=duplicate-code

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
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
from passfx.utils.strength import check_strength

if TYPE_CHECKING:
    from passfx.app import PassFXApp


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


# pylint: disable=too-many-return-statements
def _get_relative_time(iso_timestamp: str | None) -> str:
    """Convert ISO timestamp to relative time string.

    Args:
        iso_timestamp: ISO format timestamp string.

    Returns:
        Relative time string like "2m ago", "1d ago", "3w ago".
    """
    if not iso_timestamp:
        return "-"

    try:
        dt = datetime.fromisoformat(iso_timestamp)
        now = datetime.now()
        diff = now - dt

        seconds = int(diff.total_seconds())
        if seconds < 0:
            return "just now"
        if seconds < 60:
            return f"{seconds}s ago"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        if days < 7:
            return f"{days}d ago"
        weeks = days // 7
        if weeks < 4:
            return f"{weeks}w ago"
        months = days // 30
        if months < 12:
            return f"{months}mo ago"
        years = days // 365
        return f"{years}y ago"
    except (ValueError, TypeError):
        return "-"


def _get_avatar_initials(label: str) -> str:
    """Generate 2-character avatar initials from label.

    Args:
        label: Service/site label.

    Returns:
        2-character uppercase initials.
    """
    if not label:
        return "??"

    # Clean and split
    words = label.replace("_", " ").replace("-", " ").split()

    if len(words) >= 2:
        # First letter of first two words
        return (words[0][0] + words[1][0]).upper()
    if len(label) >= 2:
        # First two characters
        return label[:2].upper()
    return (label[0] + label[0]).upper() if label else "??"


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


def _get_avatar_bg_color(label: str) -> str:
    """Generate a consistent background color for avatar based on label.

    Args:
        label: Service/site label.

    Returns:
        Hex color string.
    """
    # Simple hash-based color selection
    colors = [
        "#3b82f6",  # Blue
        "#8b5cf6",  # Purple
        "#06b6d4",  # Cyan
        "#10b981",  # Emerald
        "#f59e0b",  # Amber
        "#ec4899",  # Pink
        "#6366f1",  # Indigo
        "#14b8a6",  # Teal
    ]
    if not label:
        return colors[0]
    hash_val = sum(ord(c) for c in label)
    return colors[hash_val % len(colors)]


# ═══════════════════════════════════════════════════════════════════════════════
# MODAL SCREENS
# ═══════════════════════════════════════════════════════════════════════════════


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


class ViewPasswordModal(ModalScreen[None]):
    """Modal displaying an Identity Access Token visualization."""

    # Color configuration for the password modal (Cyberpunk Cyan/Green theme)
    COLORS = {
        "border": "#00d4ff",
        "card_bg": "#0a0e27",
        "section_border": "#475569",
        "title_bg": "#00d4ff",
        "title_fg": "#000000",
        "label_dim": "#64748b",
        "value_fg": "#f8fafc",
        "accent": "#22c55e",
        "muted": "#94a3b8",
        "btn_primary_bg": "#0a2e1a",
        "btn_primary_fg": "#22c55e",
        "btn_secondary_bg": "#1e293b",
        "btn_secondary_fg": "#94a3b8",
    }

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "copy_password", "Copy"),
    ]

    def __init__(self, credential: EmailCredential) -> None:
        super().__init__()
        self.credential = credential

    # pylint: disable=too-many-locals
    def compose(self) -> ComposeResult:
        """Create the identity access token layout."""
        c = self.COLORS

        # Get password strength for visual indicator
        strength = check_strength(self.credential.password)
        strength_color = _get_strength_color(strength.score)

        # Build security level indicator bars
        filled = strength.score + 1
        security_bars = (
            f"[{strength_color}]" + ("█" * filled) + "[/]"
            + "[#1e293b]" + ("░" * (5 - filled)) + "[/]"
        )

        # Format timestamp
        try:
            created = datetime.fromisoformat(self.credential.created_at).strftime("%Y.%m.%d")
        except (ValueError, TypeError):
            created = "UNKNOWN"

        # Card dimensions
        width = 96
        inner = width - 2
        section_inner = width - 6
        content_width = section_inner - 5

        with Vertical(id="password-modal"):
            with Vertical(id="physical-id-card"):
                # Top border
                yield Static(f"[bold {c['border']}]╔{'═' * inner}╗[/]")

                # Title row
                title = " IDENTITY ACCESS TOKEN "
                title_pad = inner - len(title) - 2
                yield Static(
                    f"[bold {c['border']}]║[/]  [on {c['title_bg']}][bold "
                    f"{c['title_fg']}]{title}[/]{' ' * title_pad}[bold {c['border']}]║[/]"
                )

                # Divider
                yield Static(f"[bold {c['border']}]╠{'═' * inner}╣[/]")

                # System label
                system_val = self.credential.label.upper()
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['label_dim']}]SYSTEM:[/] "
                    f"[bold {c['value_fg']}]{system_val:<{inner - 12}}[/] "
                    f"[bold {c['border']}]║[/]"
                )

                # Spacer
                yield Static(f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]")

                # User Identity section
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['section_border']}]"
                    f"┌─ USER IDENTITY {'─' * (section_inner - 17)}┐[/]  "
                    f"[bold {c['border']}]║[/]"
                )
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['section_border']}]│[/] "
                    f"[{c['accent']}]►[/] [bold {c['value_fg']}]"
                    f"{self.credential.email:<{content_width}}[/] "
                    f"[dim {c['section_border']}]│[/]  [bold {c['border']}]║[/]"
                )
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['section_border']}]"
                    f"└{'─' * (section_inner - 1)}┘[/]  [bold {c['border']}]║[/]"
                )

                # Spacer
                yield Static(f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]")

                # Access Key section
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['section_border']}]"
                    f"┌─ ACCESS KEY {'─' * (section_inner - 14)}┐[/]  "
                    f"[bold {c['border']}]║[/]"
                )
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['section_border']}]│[/] "
                    f"[{c['accent']}]►[/] [bold {c['accent']}]"
                    f"{self.credential.password:<{content_width}}[/] "
                    f"[dim {c['section_border']}]│[/]  [bold {c['border']}]║[/]"
                )
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['section_border']}]"
                    f"└{'─' * (section_inner - 1)}┘[/]  [bold {c['border']}]║[/]"
                )

                # Spacer
                yield Static(f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]")

                # Security bar
                sec_content = (
                    f"  [dim {c['label_dim']}]SECURITY:[/] {security_bars} "
                    f"[{strength_color}]{strength.label.upper():<12}[/]"
                )
                sec_pad = inner - 35
                yield Static(
                    f"[bold {c['border']}]║[/]{sec_content}{' ' * sec_pad}"
                    f"[bold {c['border']}]║[/]"
                )

                # Footer divider
                yield Static(f"[bold {c['border']}]╠{'═' * inner}╣[/]")

                # Footer row
                footer_left = (
                    f"  [dim {c['section_border']}]ID:[/] "
                    f"[{c['muted']}]{self.credential.id[:8]}[/]"
                )
                footer_right = (
                    f"[dim {c['section_border']}]ISSUED:[/] [{c['muted']}]{created}[/]"
                )
                footer_pad = inner - 30 - len(created)
                yield Static(
                    f"[bold {c['border']}]║[/]{footer_left}{' ' * footer_pad}"
                    f"{footer_right}  [bold {c['border']}]║[/]"
                )

                # Bottom border
                yield Static(f"[bold {c['border']}]╚{'═' * inner}╝[/]")

            # Action Buttons
            with Horizontal(id="password-modal-buttons"):
                yield Button("COPY KEY", id="copy-button")
                yield Button("CLOSE", id="close-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "close-button":
            self.dismiss(None)
        elif event.button.id == "copy-button":
            self._copy_password()

    def _copy_password(self) -> None:
        """Copy password to clipboard."""
        if copy_to_clipboard(self.credential.password, auto_clear=True, clear_after=30):
            self.notify("Password copied! Clears in 30s", title="Copied")
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)

    def action_copy_password(self) -> None:
        """Copy password via keybinding."""
        self._copy_password()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PASSWORDS SCREEN
# ═══════════════════════════════════════════════════════════════════════════════


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

    def __init__(self) -> None:
        super().__init__()
        self._selected_row_key: str | None = None
        self._pulse_state: bool = True

    # pylint: disable=too-many-locals
    def compose(self) -> ComposeResult:
        """Create the passwords screen layout."""
        # 1. Global Header with Breadcrumbs
        with Horizontal(id="app-header"):
            yield Static(
                "[dim #64748b]HOME[/] [#475569]›[/] [dim #64748b]VAULT[/] "
                "[#475569]›[/] [bold #00d4ff]PASSWORDS[/]",
                id="header-branding",
            )
            yield Static("░░ SECURE DATA BANK ░░", id="header-status")
            yield Static("", id="header-lock")  # Will be updated with pulse

        # 2. Body (Master-Detail Split)
        with Horizontal(id="vault-body"):
            # Left Pane: Data Grid (Master) - 65%
            with Vertical(id="vault-grid-pane"):
                # Inverted Block Header
                yield Static(" ≡ CREDENTIAL_DATABASE ", classes="pane-header-block")
                yield DataTable(id="passwords-table", cursor_type="row")
                # Empty state placeholder (hidden by default)
                with Center(id="empty-state"):
                    yield Static(
                        "[dim #475569]╔══════════════════════════════════════╗\n"
                        "║                                      ║\n"
                        "║      NO ENTRIES FOUND                ║\n"
                        "║                                      ║\n"
                        "║      INITIATE SEQUENCE [A]           ║\n"
                        "║                                      ║\n"
                        "╚══════════════════════════════════════╝[/]",
                        id="empty-state-text",
                    )
                # Footer with object count
                yield Static(" └── SYSTEM_READY", classes="pane-footer", id="grid-footer")

            # Right Pane: Inspector (Detail) - 35%
            with Vertical(id="vault-inspector"):
                # Inverted Block Header
                yield Static(" ≡ IDENTITY_INSPECTOR ", classes="pane-header-block")
                yield Vertical(id="inspector-content")  # Dynamic content here

        # 3. Global Footer
        with Horizontal(id="app-footer"):
            yield Static(" VAULT ", id="footer-version")
            yield Static(
                " \\[A] Add  \\[C] Copy  \\[E] Edit  \\[D] Delete  \\[V] View  \\[ESC] Back",
                id="footer-keys-static",
            )

    def on_mount(self) -> None:
        """Initialize the data table."""
        self._refresh_table()
        # Focus table and initialize inspector after layout is complete
        self.call_after_refresh(self._initialize_selection)
        # Start pulse animation
        self._update_pulse()
        self.set_interval(1.0, self._update_pulse)

    def _update_pulse(self) -> None:
        """Update the pulse indicator in the header."""
        self._pulse_state = not self._pulse_state
        header_lock = self.query_one("#header-lock", Static)
        if self._pulse_state:
            header_lock.update("[#22c55e]● [bold]ENCRYPTED[/][/]")
        else:
            header_lock.update("[#166534]○ [bold]ENCRYPTED[/][/]")

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
                self._selected_row_key = credentials[0].id
                self._update_inspector(credentials[0].id)
        else:
            self._update_inspector(None)

    # pylint: disable=too-many-locals
    def _refresh_table(self) -> None:
        """Refresh the data table with credentials."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#passwords-table", DataTable)
        empty_state = self.query_one("#empty-state", Center)

        table.clear(columns=True)

        # New column layout without # index, with Status instead of Password
        # Column layout - sized to fill available space
        table.add_column("", width=3)  # Selection indicator column
        table.add_column("Label", width=22)
        table.add_column("Email", width=32)
        table.add_column("Status", width=10)
        table.add_column("Updated", width=12)
        table.add_column("Notes", width=40)  # Wider to fill remaining space

        credentials = app.vault.get_emails()

        # Toggle visibility based on credential count
        if len(credentials) == 0:
            table.display = False
            empty_state.display = True
        else:
            table.display = True
            empty_state.display = False

        for cred in credentials:
            # Selection indicator - will be updated dynamically
            is_selected = cred.id == self._selected_row_key
            indicator = "[bold #00d4ff]▍[/]" if is_selected else " "

            # Label (white text)
            label_text = cred.label

            # Email (muted)
            email_text = f"[#94a3b8]{cred.email}[/]"

            # Status column with colored lock icon based on strength
            strength = check_strength(cred.password)
            color = _get_strength_color(strength.score)
            status = f"[{color}]🔒[/]"

            # Relative time (dim)
            updated = _get_relative_time(cred.updated_at)
            updated_text = f"[dim]{updated}[/]"

            # Notes preview (dim)
            notes = (
                (cred.notes[:16] + "…")
                if cred.notes and len(cred.notes) > 16
                else (cred.notes or "-")
            )
            notes_text = f"[dim #64748b]{notes}[/]"

            table.add_row(
                indicator, label_text, email_text, status, updated_text, notes_text, key=cred.id
            )

        # Update the grid footer with object count
        footer = self.query_one("#grid-footer", Static)
        count = len(credentials)
        footer.update(f" └── [{count}] OBJECTS LOADED")

    def _update_row_indicators(self, old_key: str | None, new_key: str | None) -> None:
        """Update only the indicator column for old and new selected rows.

        This avoids rebuilding the entire table on selection change.
        """
        table = self.query_one("#passwords-table", DataTable)
        app: PassFXApp = self.app  # type: ignore
        credentials = app.vault.get_emails()

        # Build a map of id -> credential for quick lookup
        cred_map = {c.id: c for c in credentials}

        # Get column keys (first column is the indicator)
        if not table.columns:
            return
        indicator_col = list(table.columns.keys())[0]

        # Clear old selection indicator
        if old_key and old_key in cred_map:
            try:
                table.update_cell(old_key, indicator_col, " ")
            except Exception:  # pylint: disable=broad-exception-caught
                pass  # Row may not exist

        # Set new selection indicator
        if new_key and new_key in cred_map:
            try:
                table.update_cell(new_key, indicator_col, "[bold #00d4ff]▍[/]")
            except Exception:  # pylint: disable=broad-exception-caught
                pass  # Row may not exist

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
            self.notify("Password copied! Clears in 30s", title=cred.label)
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
        """View credential details in Identity Access Token modal."""
        cred = self._get_selected_credential()
        if not cred:
            self.notify("No credential selected", severity="warning")
            return

        self.app.push_screen(ViewPasswordModal(cred))

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update inspector panel when a row is highlighted."""
        # row_key is a RowKey object, get its value
        key_value = event.row_key.value if hasattr(event.row_key, "value") else str(event.row_key)
        old_key = self._selected_row_key
        self._selected_row_key = key_value
        self._update_inspector(key_value)
        # Update only the indicator cells instead of rebuilding entire table
        self._update_row_indicators(old_key, key_value)

    # pylint: disable=too-many-locals
    def _update_inspector(self, row_key: Any) -> None:
        """Update the inspector panel with credential details.

        Renders a modernized "Identity Inspector" with:
        - Digital ID Card header with 2-char avatar
        - Block-based strength progress bar
        - Notes terminal with line numbers
        - Footer metadata (ID, Updated)
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
            inspector.mount(
                Static(
                    "[dim #555555]╔══════════════════════════╗\n"
                    "║    SELECT AN ENTRY       ║\n"
                    "║    TO VIEW DETAILS       ║\n"
                    "╚══════════════════════════╝[/]",
                    classes="inspector-empty",
                )
            )
            return

        # ═══════════════════════════════════════════════════════════════
        # SECTION 1: Digital ID Card Header with Avatar
        # ═══════════════════════════════════════════════════════════════
        initials = _get_avatar_initials(cred.label)
        avatar_bg = _get_avatar_bg_color(cred.label)

        # Build avatar box (2-line tall for visual weight)
        avatar_top = f"[on {avatar_bg}][bold #ffffff] {initials} [/][/]"
        avatar_bot = f"[on {avatar_bg}]     [/]"

        inspector.mount(
            Vertical(
                Horizontal(
                    Vertical(
                        Static(avatar_top, classes="avatar-char"),
                        Static(avatar_bot, classes="avatar-char"),
                        classes="avatar-box",
                    ),
                    Vertical(
                        Static(f"[bold #f8fafc]{cred.label}[/]", classes="id-label-text"),
                        Static(f"[dim #94a3b8]{cred.email}[/]", classes="id-email-text"),
                        classes="id-details-stack",
                    ),
                    classes="id-card-header",
                ),
                classes="id-card-wrapper",
            )
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 2: Security Strength Widget with Block Progress Bar
        # ═══════════════════════════════════════════════════════════════
        strength = check_strength(cred.password)
        color = _get_strength_color(strength.score)

        # Build smooth block progress bar (20 chars wide)
        filled_blocks = (strength.score + 1) * 4  # 0=4, 1=8, 2=12, 3=16, 4=20
        empty_blocks = 20 - filled_blocks

        filled = f"[{color}]" + ("█" * filled_blocks) + "[/]"
        empty = "[#1e293b]" + ("░" * empty_blocks) + "[/]"
        progress_bar = f"{filled}{empty}"

        # Strength label inline with bar
        strength_display = f"{progress_bar} [{color}]{strength.label.upper()}[/]"

        inspector.mount(
            Vertical(
                Static("[dim #6b7280]▸ SECURITY ANALYSIS[/]", classes="section-label"),
                Static(strength_display, classes="strength-bar-widget"),
                Static(
                    f"[dim #475569]Crack time:[/] [#94a3b8]{strength.crack_time}[/]",
                    classes="crack-time-label",
                ),
                classes="security-widget",
            )
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 3: Notes Terminal with Line Numbers
        # ═══════════════════════════════════════════════════════════════
        if cred.notes:
            # Split notes into lines and add line numbers
            lines = cred.notes.split("\n")
            numbered_lines = []
            for i, line in enumerate(lines[:10], 1):  # Limit to 10 lines
                line_num = f"[dim #475569]{i:2}[/]"
                line_content = f"[#22c55e]{line}[/]" if line.strip() else ""
                numbered_lines.append(f"{line_num} │ {line_content}")
            notes_content = "\n".join(numbered_lines)
        else:
            notes_content = "[dim #475569] 1[/] │ [dim #64748b]// NO NOTES[/]"

        notes_terminal = Vertical(
            Static(notes_content, classes="notes-code"),
            classes="notes-editor",
        )
        notes_terminal.border_title = "ENCRYPTED_NOTES"

        inspector.mount(
            Vertical(
                Static("[dim #6b7280]▸ METADATA[/]", classes="section-label"),
                notes_terminal,
                classes="notes-section",
            )
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 4: Footer Metadata Bar (ID + Updated)
        # ═══════════════════════════════════════════════════════════════
        try:
            updated_full = datetime.fromisoformat(cred.updated_at).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            updated_full = cred.updated_at or "Unknown"

        inspector.mount(
            Horizontal(
                Static(
                    f"[dim #475569]ID:[/] [#64748b]{cred.id[:8]}[/]", classes="meta-id"
                ),
                Static(
                    f"[dim #475569]UPDATED:[/] [#64748b]{updated_full}[/]",
                    classes="meta-updated",
                ),
                classes="inspector-footer-bar",
            )
        )
