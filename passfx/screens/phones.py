"""Phones Screen for PassFX."""

# pylint: disable=duplicate-code,too-many-lines

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Input, Label, Static

from passfx.core.models import PhoneCredential
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


# ═══════════════════════════════════════════════════════════════════════════════
# MODAL SCREENS
# ═══════════════════════════════════════════════════════════════════════════════


class AddPhoneModal(ModalScreen[PhoneCredential | None]):
    """Modal for adding a new phone credential - Operator Grade Secure Write Console."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Create the Operator-grade modal layout."""
        with Vertical(id="pwd-modal", classes="secure-terminal"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static("[ :: SECURE WRITE PROTOCOL :: ]", id="modal-title")
                    yield Static("STATUS: OPEN", classes="modal-status")

            # Form Body
            with Vertical(id="pwd-form"):
                # Row 1: Label (Device)
                yield Label("> TARGET_DEVICE", classes="input-label")
                yield Input(placeholder="e.g. BANK_HOTLINE", id="label-input")

                # Row 2: Phone (Uplink)
                yield Label("> UPLINK_NUMBER", classes="input-label")
                yield Input(placeholder="+1 555 000 0000", id="phone-input")

                # Row 3: PIN (Access Code) - sensitive field
                yield Label("> ACCESS_PIN", classes="input-label")
                yield Input(placeholder="••••••", password=True, id="pin-input")

                # Row 4: Notes
                yield Label("> METADATA", classes="input-label")
                yield Input(placeholder="OPTIONAL_NOTES", id="notes-input")

            # Footer Actions - right aligned
            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ ABORT ]", id="cancel-button")
                yield Button(
                    r"\[ ENCRYPT & COMMIT ]", variant="primary", id="save-button"
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


class EditPhoneModal(ModalScreen[dict | None]):
    """Modal for editing a phone credential - Operator Grade Secure Write Console."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, credential: PhoneCredential) -> None:
        super().__init__()
        self.credential = credential

    def compose(self) -> ComposeResult:
        """Create the Operator-grade modal layout."""
        with Vertical(id="pwd-modal", classes="secure-terminal"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static(
                        f"[ :: MODIFY // {self.credential.label.upper()} :: ]",
                        id="modal-title",
                    )
                    yield Static("STATUS: EDIT", classes="modal-status")

            with Vertical(id="pwd-form"):
                yield Label("> TARGET_DEVICE", classes="input-label")
                yield Input(
                    value=self.credential.label,
                    placeholder="e.g. BANK_HOTLINE",
                    id="label-input",
                )

                yield Label("> UPLINK_NUMBER", classes="input-label")
                yield Input(
                    value=self.credential.phone,
                    placeholder="+1 555 000 0000",
                    id="phone-input",
                )

                yield Label("> ACCESS_PIN [BLANK = KEEP]", classes="input-label")
                yield Input(placeholder="••••••", password=True, id="pin-input")

                yield Label("> METADATA", classes="input-label")
                yield Input(
                    value=self.credential.notes or "",
                    placeholder="OPTIONAL_NOTES",
                    id="notes-input",
                )

            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ ABORT ]", id="cancel-button")
                yield Button(
                    r"\[ ENCRYPT & COMMIT ]", variant="primary", id="save-button"
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            self._save()

    def _save(self) -> None:
        """Save the changes."""
        label = self.query_one("#label-input", Input).value.strip()
        phone = self.query_one("#phone-input", Input).value.strip()
        pin = self.query_one("#pin-input", Input).value
        notes = self.query_one("#notes-input", Input).value.strip()

        if not label or not phone:
            self.notify("Label and phone are required", severity="error")
            return

        result = {
            "label": label,
            "phone": phone,
            "notes": notes if notes else None,
        }
        if pin:
            result["password"] = pin

        self.dismiss(result)

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class ConfirmDeleteModal(ModalScreen[bool]):
    """Modal for confirming deletion - Operator Grade Console."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
    ]

    def __init__(self, item_name: str) -> None:
        super().__init__()
        self.item_name = item_name

    def compose(self) -> ComposeResult:
        """Create the Operator-grade modal layout."""
        with Vertical(id="pwd-modal", classes="secure-terminal"):
            # HUD Header with warning status
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static("[ :: PURGE PROTOCOL :: ]", id="modal-title")
                    yield Static("STATUS: ARMED", classes="modal-status")

            with Vertical(id="pwd-form"):
                yield Static(f"TARGET: '{self.item_name}'", classes="delete-target")
                yield Static("THIS ACTION CANNOT BE UNDONE", classes="warning")

            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ ABORT ]", id="cancel-button")
                yield Button(r"\[ CONFIRM PURGE ]", variant="error", id="delete-button")

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


class ViewPhoneModal(ModalScreen[None]):
    """Modal for viewing a phone credential - Operator Grade Secure Read Console."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "copy_pin", "Copy"),
    ]

    def __init__(self, credential: PhoneCredential) -> None:
        super().__init__()
        self.credential = credential

    def compose(self) -> ComposeResult:
        """Create the Operator-grade view modal layout."""
        # Get PIN strength for visual indicator
        strength = check_strength(self.credential.password)
        strength_color = _get_strength_color(strength.score)
        filled = strength.score + 1
        security_bars = (
            f"[{strength_color}]{'█' * filled}[/][#1e293b]{'░' * (5 - filled)}[/]"
        )

        with Vertical(id="pwd-modal", classes="secure-terminal"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static("[ :: SECURE READ PROTOCOL :: ]", id="modal-title")
                    yield Static("STATUS: DECRYPTED", classes="modal-status")

            # Data Display Body
            with Vertical(id="pwd-form"):
                # Row 1: Label (Device)
                yield Label("> DEVICE_NAME", classes="input-label")
                yield Static(
                    f"  {self.credential.label}", classes="view-value", id="label-value"
                )

                # Row 2: Phone Number
                yield Label("> UPLINK_NUMBER", classes="input-label")
                yield Static(
                    f"  {self.credential.phone}", classes="view-value", id="phone-value"
                )

                # Row 3: PIN (Secret)
                yield Label("> ACCESS_PIN", classes="input-label")
                yield Static(
                    f"  [#d946ef]{self.credential.password}[/]",
                    classes="view-value secret",
                    id="pin-value",
                )

                # Row 4: Security Level
                yield Label("> COMPLEXITY", classes="input-label")
                yield Static(
                    f"  {security_bars} [{strength_color}]{strength.label.upper()}[/]",
                    classes="view-value",
                    id="strength-value",
                )

                # Row 5: Notes (if present)
                if self.credential.notes:
                    yield Label("> METADATA", classes="input-label")
                    yield Static(
                        f"  {self.credential.notes}",
                        classes="view-value",
                        id="notes-value",
                    )

            # Footer Actions - right aligned
            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ DISMISS ]", variant="default", id="cancel-button")
                yield Button(r"\[ COPY PIN ]", variant="primary", id="save-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            self._copy_pin()

    def _copy_pin(self) -> None:
        """Copy PIN to clipboard with auto-clear for security."""
        if copy_to_clipboard(self.credential.password, auto_clear=True):
            self.notify("PIN copied! Clears in 15s", title="Copied")
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)

    def action_copy_pin(self) -> None:
        """Copy PIN via keybinding."""
        self._copy_pin()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PHONES SCREEN
# ═══════════════════════════════════════════════════════════════════════════════


class PhonesScreen(Screen):
    """Screen for managing phone credentials."""

    BINDINGS = [
        Binding("a", "add", "Add"),
        Binding("c", "copy", "Copy"),
        Binding("e", "edit", "Edit"),
        Binding("d", "delete", "Delete"),
        Binding("v", "view", "View"),
        Binding("escape", "back", "Back"),
    ]

    # Operator theme color tokens - Pink accent for phones
    COLORS = {
        "primary": "#00FFFF",  # Cyan - active selection, titles
        "accent": "#ec4899",  # Pink - labels, headers (phones-specific)
        "success": "#22c55e",  # Green - high strength, decrypted
        "muted": "#666666",  # Dim grey - metadata, timestamps
        "text": "#e0e0e0",  # Light text
        "surface": "#0a0a0a",  # Dark surface
    }

    def __init__(self) -> None:
        super().__init__()
        self._selected_row_key: str | None = None
        self._pulse_state: bool = True
        self._pending_select_id: str | None = None  # For search navigation

    # pylint: disable=too-many-locals
    def compose(self) -> ComposeResult:
        """Create the phones screen layout."""
        c = self.COLORS

        # 1. Global Header with Breadcrumbs - Operator theme
        with Horizontal(id="app-header"):
            yield Static(
                f"[bold {c['accent']}]VAULT // COMMS[/]",
                id="header-branding",
                classes="screen-header",
            )
            with Horizontal(id="header-right"):
                yield Static("", id="header-lock")  # Will be updated with pulse

        # 2. Body (Master-Detail Split)
        with Horizontal(id="vault-body"):
            # Left Pane: Data Grid (Master) - 65%
            with Vertical(id="vault-grid-pane"):
                yield DataTable(id="phones-table", cursor_type="row")
                # Empty state placeholder (hidden by default)
                with Center(id="empty-state"):
                    yield Static(
                        f"[dim {c['muted']}]╔══════════════════════════════════════╗\n"
                        "║                                      ║\n"
                        "║      NO ENTRIES FOUND                ║\n"
                        "║                                      ║\n"
                        f"║      INITIATE SEQUENCE [{c['primary']}]A[/]           ║\n"
                        "║                                      ║\n"
                        "╚══════════════════════════════════════╝[/]",
                        id="empty-state-text",
                    )
                # Footer with object count
                yield Static(
                    " └── SYSTEM_READY", classes="pane-footer", id="grid-footer"
                )

            # Right Pane: Inspector (Detail) - 35%
            with Vertical(id="vault-inspector"):
                # Inverted Block Header - Pink accent
                yield Static(" ≡ DEVICE_INSPECTOR ", classes="pane-header-block-pink")
                yield Vertical(id="inspector-content")  # Dynamic content here

        # 3. Global Footer - Mechanical keycap style
        with Horizontal(id="app-footer"):
            yield Static(f" [{c['accent']}]VAULT[/] ", id="footer-version")
            with Horizontal(id="footer-keys"):
                # Keycap groups for each command
                with Horizontal(classes="keycap-group"):
                    yield Static(f"[bold {c['primary']}] A [/]", classes="keycap")
                    yield Static(f"[{c['muted']}]Add[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static(f"[bold {c['primary']}] C [/]", classes="keycap")
                    yield Static(f"[{c['muted']}]Copy[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static(f"[bold {c['primary']}] E [/]", classes="keycap")
                    yield Static(f"[{c['muted']}]Edit[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static(f"[bold {c['primary']}] D [/]", classes="keycap")
                    yield Static(f"[{c['muted']}]Del[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static(f"[bold {c['primary']}] V [/]", classes="keycap")
                    yield Static(f"[{c['muted']}]View[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static(f"[bold {c['primary']}] ^K [/]", classes="keycap")
                    yield Static(f"[{c['muted']}]Search[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static(f"[bold {c['primary']}] ESC [/]", classes="keycap")
                    yield Static(f"[{c['muted']}]Back[/]", classes="keycap-label")

    def on_mount(self) -> None:
        """Initialize the data table."""
        self._refresh_table()
        # Focus table and initialize inspector after layout is complete
        self.call_after_refresh(self._initialize_selection)
        # Start pulse animation
        self._update_pulse()
        self.set_interval(1.0, self._update_pulse)
        # Start cursor blink animation
        self.set_interval(0.5, self._blink_cursor)

    def _blink_cursor(self) -> None:
        """Toggle the blinking cursor visibility in empty notes."""
        try:
            cursor = self.query_one(".blink-cursor", Static)
            cursor.toggle_class("-blink-off")
        except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
            pass  # Cursor may not exist if notes have content

    def _update_pulse(self) -> None:
        """Update the pulse indicator in the header."""
        self._pulse_state = not self._pulse_state
        header_lock = self.query_one("#header-lock", Static)
        c = self.COLORS
        if self._pulse_state:
            header_lock.update(f"[{c['success']}]● [bold]ENCRYPTED[/][/]")
        else:
            header_lock.update(f"[#166534]○ [{c['success']}]ENCRYPTED[/][/]")

    def _initialize_selection(self) -> None:
        """Initialize table selection and inspector after render."""
        table = self.query_one("#phones-table", DataTable)
        table.focus()

        app: PassFXApp = self.app  # type: ignore
        credentials = app.vault.get_phones()

        if table.row_count > 0:
            # Check for pending selection from search
            target_row = 0
            target_id = credentials[0].id if credentials else None

            if self._pending_select_id:
                for i, cred in enumerate(credentials):
                    if cred.id == self._pending_select_id:
                        target_row = i
                        target_id = cred.id
                        break
                self._pending_select_id = None  # Clear pending selection

            # Move cursor to target row
            table.move_cursor(row=target_row)

            if target_id:
                self._selected_row_key = target_id
                self._update_inspector(target_id)
        else:
            self._update_inspector(None)

    # pylint: disable=too-many-locals
    def _refresh_table(self) -> None:
        """Refresh the data table with credentials."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#phones-table", DataTable)
        empty_state = self.query_one("#empty-state", Center)
        c = self.COLORS

        table.clear(columns=True)

        # Column layout - data stream style (matches passwords)
        table.add_column("", width=2)  # Selection indicator column
        table.add_column("DEVICE", width=22)
        table.add_column("UPLINK", width=22)
        table.add_column("LEVEL", width=10)
        table.add_column("SYNC", width=12)
        table.add_column("METADATA", width=40)

        credentials = app.vault.get_phones()

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
            indicator = f"[bold {c['primary']}]▸[/]" if is_selected else " "

            # Label - primary text
            label_text = cred.label

            # Phone (muted grey)
            phone_text = f"[{c['muted']}]{cred.phone}[/]"

            # Status column with colored indicator based on PIN strength
            strength = check_strength(cred.password)
            color = _get_strength_color(strength.score)
            status = f"[{color}]●[/]"

            # Relative time (dim muted)
            updated = _get_relative_time(cred.updated_at)
            updated_text = f"[dim {c['muted']}]{updated}[/]"

            # Notes preview (dim)
            notes = (
                (cred.notes[:16] + "…")
                if cred.notes and len(cred.notes) > 16
                else (cred.notes or "-")
            )
            notes_text = f"[dim {c['muted']}]{notes}[/]"

            table.add_row(
                indicator,
                label_text,
                phone_text,
                status,
                updated_text,
                notes_text,
                key=cred.id,
            )

        # Update the grid footer with object count
        footer = self.query_one("#grid-footer", Static)
        count = len(credentials)
        footer.update(f" └── [{c['primary']}]{count}[/] OBJECTS LOADED")

    def _update_row_indicators(self, old_key: str | None, new_key: str | None) -> None:
        """Update only the indicator column for old and new selected rows.

        This avoids rebuilding the entire table on selection change.
        """
        table = self.query_one("#phones-table", DataTable)
        app: PassFXApp = self.app  # type: ignore
        credentials = app.vault.get_phones()
        c = self.COLORS

        # Build a map of id -> credential for quick lookup
        cred_map = {cred.id: cred for cred in credentials}

        # Get column keys (first column is the indicator)
        if not table.columns:
            return
        indicator_col = list(table.columns.keys())[0]

        # Clear old selection indicator
        if old_key and old_key in cred_map:
            try:
                table.update_cell(old_key, indicator_col, " ")
            except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
                pass  # Row may not exist during rapid navigation

        # Set new selection indicator - cyan arrow for locked target feel
        if new_key and new_key in cred_map:
            try:
                table.update_cell(new_key, indicator_col, f"[bold {c['primary']}]▸[/]")
            except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
                pass  # Row may not exist during rapid navigation

    def _get_selected_credential(self) -> PhoneCredential | None:
        """Get the currently selected credential."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#phones-table", DataTable)

        if table.cursor_row is None:
            return None

        # Get credentials and find by cursor row index
        credentials = app.vault.get_phones()
        if 0 <= table.cursor_row < len(credentials):
            return credentials[table.cursor_row]
        return None

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
        """Copy PIN to clipboard with auto-clear for security."""
        cred = self._get_selected_credential()
        if not cred:
            self.notify("No credential selected", severity="warning")
            return

        if copy_to_clipboard(cred.password, auto_clear=True):
            self.notify("PIN copied! Clears in 15s", title=cred.label)
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
                app.vault.update_phone(cred.id, **changes)
                self._refresh_table()
                self.notify("Credential updated", title="Success")

        self.app.push_screen(EditPhoneModal(cred), handle_result)

    def action_delete(self) -> None:
        """Delete selected credential."""
        cred = self._get_selected_credential()
        if not cred:
            self.notify("No credential selected", severity="warning")
            return

        def handle_result(confirmed: bool | None) -> None:
            if confirmed:
                app: PassFXApp = self.app  # type: ignore
                app.vault.delete_phone(cred.id)
                self._refresh_table()
                self.notify(f"Deleted '{cred.label}'", title="Deleted")

        self.app.push_screen(ConfirmDeleteModal(cred.label), handle_result)

    def action_view(self) -> None:
        """View credential details in Secure Comms Uplink modal."""
        cred = self._get_selected_credential()
        if not cred:
            self.notify("No credential selected", severity="warning")
            return

        self.app.push_screen(ViewPhoneModal(cred))

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update inspector panel when a row is highlighted."""
        # row_key is a RowKey object, get its value
        key_value = (
            event.row_key.value
            if hasattr(event.row_key, "value")
            else str(event.row_key)
        )
        old_key = self._selected_row_key
        self._selected_row_key = key_value
        self._update_inspector(key_value)
        # Update only the indicator cells instead of rebuilding entire table
        self._update_row_indicators(old_key, key_value)

    # pylint: disable=too-many-locals,too-many-statements
    def _update_inspector(self, row_key: Any) -> None:
        """Update the inspector panel with credential details.

        Renders a structured "Device Inspector" with:
        - Entry Header (large text, primary color)
        - Field Grid (labels in accent, values in text)
        - PIN Field (masked with reveal toggle hint)
        - Strength Meter (block progress bar)
        - Notes Section (terminal style)
        """
        inspector = self.query_one("#inspector-content", Vertical)
        inspector.remove_children()
        c = self.COLORS

        # Get the credential by row key
        app: PassFXApp = self.app  # type: ignore
        credentials = app.vault.get_phones()

        # Find credential by ID
        cred = None
        for credential in credentials:
            if credential.id == str(row_key):
                cred = credential
                break

        if not cred:
            # Empty state - styled for Operator theme
            inspector.mount(
                Static(
                    f"[dim {c['muted']}]╔══════════════════════════════╗\n"
                    "║                              ║\n"
                    "║    SELECT AN ENTRY           ║\n"
                    "║    TO INSPECT DETAILS        ║\n"
                    "║                              ║\n"
                    "╚══════════════════════════════╝[/]",
                    classes="inspector-empty",
                )
            )
            return

        # ═══════════════════════════════════════════════════════════════
        # SECTION 1: Entry Header - Large title with underline
        # ═══════════════════════════════════════════════════════════════
        inspector.mount(
            Vertical(
                Static(
                    f"[bold underline {c['primary']}]{cred.label.upper()}[/]",
                    classes="inspector-title",
                ),
                classes="inspector-header",
            )
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 2: Field Grid - Structured label/value pairs
        # ═══════════════════════════════════════════════════════════════
        inspector.mount(
            Vertical(
                # Uplink (phone number) field
                Horizontal(
                    Static(f"[{c['accent']}]UPLINK[/]", classes="field-label"),
                    Static(f"[{c['text']}]{cred.phone}[/]", classes="field-value"),
                    classes="field-row",
                ),
                # PIN field - masked by default
                Horizontal(
                    Static(f"[{c['accent']}]ACCESS PIN[/]", classes="field-label"),
                    Static(
                        f"[{c['muted']}]●●●●●●[/]  " f"[dim]\\[V] to reveal[/]",
                        classes="field-value",
                    ),
                    classes="field-row",
                ),
                classes="field-grid",
            )
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 3: Strength Meter - Entropy Level Progress Bar
        # ═══════════════════════════════════════════════════════════════
        strength = check_strength(cred.password)
        strength_color = _get_strength_color(strength.score)

        # Build block progress bar (20 chars wide)
        filled_blocks = (strength.score + 1) * 4  # 0=4, 1=8, 2=12, 3=16, 4=20
        empty_blocks = 20 - filled_blocks

        filled = f"[{strength_color}]" + ("█" * filled_blocks) + "[/]"
        empty = "[#1e293b]" + ("░" * empty_blocks) + "[/]"
        progress_bar = f"{filled}{empty}"

        inspector.mount(
            Vertical(
                Static(
                    f"[{c['accent']}]ENTROPY LEVEL[/]", classes="strength-section-label"
                ),
                Static(progress_bar, classes="strength-bar"),
                Static(
                    f"[{strength_color}]{strength.label.upper()}[/]  "
                    f"[dim {c['muted']}]// {strength.crack_time}[/]",
                    classes="strength-label",
                ),
                classes="strength-section",
            )
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 4: Notes Terminal - Styled like terminal output
        # ═══════════════════════════════════════════════════════════════
        if cred.notes:
            lines = cred.notes.split("\n")
            numbered_lines = []
            for i, line in enumerate(lines[:8], 1):  # Limit to 8 lines
                line_num = f"[dim {c['muted']}]{i:2}[/]"
                line_content = f"[{c['success']}]{line}[/]" if line.strip() else ""
                numbered_lines.append(f"{line_num} │ {line_content}")
            notes_content = "\n".join(numbered_lines)
        else:
            notes_content = (
                f"[dim {c['muted']}] 1[/] │ [dim {c['muted']}]// NO NOTES[/] "
            )

        notes_terminal = Vertical(
            Static(notes_content, classes="notes-code"),
            Static("▌", classes="blink-cursor") if not cred.notes else Static(""),
            classes="notes-terminal-box",
        )
        notes_terminal.border_title = "NOTES"

        inspector.mount(
            Vertical(
                Static(f"[{c['accent']}]METADATA[/]", classes="notes-section-label"),
                notes_terminal,
                classes="notes-section",
            )
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 5: Footer Metadata Bar (ID + Updated)
        # ═══════════════════════════════════════════════════════════════
        try:
            updated_full = datetime.fromisoformat(cred.updated_at).strftime(
                "%Y-%m-%d %H:%M"
            )
        except (ValueError, TypeError):
            updated_full = cred.updated_at or "Unknown"

        inspector.mount(
            Horizontal(
                Static(
                    f"[dim {c['muted']}]ID:[/] [{c['muted']}]{cred.id[:8]}[/]",
                    classes="meta-id",
                ),
                Static(
                    f"[dim {c['muted']}]SYNC:[/] [{c['muted']}]{updated_full}[/]",
                    classes="meta-updated",
                ),
                classes="inspector-footer-bar",
            )
        )
