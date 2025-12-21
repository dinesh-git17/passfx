"""Secure Notes Screen for PassFX - Encrypted Data Shards."""

# pylint: disable=duplicate-code,too-many-lines

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Input, Label, Static, TextArea

from passfx.core.models import NoteEntry
from passfx.utils.clipboard import copy_to_clipboard

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


# ═══════════════════════════════════════════════════════════════════════════════
# MODAL SCREENS
# ═══════════════════════════════════════════════════════════════════════════════


class ViewNoteModal(ModalScreen[None]):
    """Modal for viewing a note - Wide Console Panel Layout."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "copy_content", "Copy"),
    ]

    def __init__(self, note: NoteEntry) -> None:
        super().__init__()
        self.note = note

    def compose(self) -> ComposeResult:
        """Create wide-format console panel view layout."""
        with Vertical(id="pwd-modal", classes="note-modal-wide"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static("[ :: SECURE READ PROTOCOL :: ]", id="modal-title")
                    yield Static("STATUS: DECRYPTED", classes="modal-status")

            # Data Display Body - Grid Layout
            with Vertical(id="pwd-form", classes="pwd-form-grid"):
                # Row 1 (Identity): Title + Stats spans full width
                with Vertical(classes="form-row form-row-full"):
                    yield Label("> SHARD_TITLE", classes="input-label")
                    yield Static(
                        f"  {self.note.title}  "
                        f"[dim]({self.note.line_count}L {self.note.char_count}C)[/]",
                        classes="view-value",
                        id="title-value",
                    )

                # Row 2 (Content): Full content in TextArea (read-only reveal)
                with Vertical(classes="form-row form-row-full form-row-content"):
                    yield Label("> CONTENT [DECRYPTED]", classes="input-label")
                    yield TextArea(
                        self.note.content,
                        id="content-area",
                        classes="note-content-editor",
                        read_only=True,
                    )

            # Footer Actions - docked bottom, right aligned
            with Horizontal(id="modal-buttons", classes="modal-footer"):
                yield Button(r"\[ DISMISS ]", variant="default", id="cancel-button")
                yield Button(r"\[ COPY ]", variant="primary", id="save-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            self._copy_content()

    def _copy_content(self) -> None:
        """Copy content to clipboard with auto-clear for security."""
        if copy_to_clipboard(self.note.content, auto_clear=True):
            self.notify("Note copied! Clears in 15s", title="Copied")
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)

    def action_copy_content(self) -> None:
        """Copy content via keybinding."""
        self._copy_content()


class AddNoteModal(ModalScreen[NoteEntry | None]):
    """Modal for adding a new secure note - Wide Console Panel Layout."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Create wide-format console panel layout."""
        with Vertical(id="pwd-modal", classes="note-modal-wide"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static("[ :: SECURE WRITE PROTOCOL :: ]", id="modal-title")
                    yield Static("STATUS: OPEN", classes="modal-status")

            # Form Body - Grid Layout
            with Vertical(id="pwd-form", classes="pwd-form-grid"):
                # Row 1 (Identity): Title spans full width
                with Vertical(classes="form-row form-row-full"):
                    yield Label("> SHARD_TITLE", classes="input-label")
                    yield Input(
                        placeholder="e.g. Office Wi-Fi Password", id="title-input"
                    )

                # Row 2 (Content): Full width content editor
                with Vertical(classes="form-row form-row-full form-row-content"):
                    yield Label("> CONTENT", classes="input-label")
                    yield TextArea(
                        "",
                        id="content-area",
                        classes="note-content-editor",
                    )

            # Footer Actions - docked bottom, right aligned
            with Horizontal(id="modal-buttons", classes="modal-footer"):
                yield Button(r"\[ ABORT ]", variant="default", id="cancel-button")
                yield Button(
                    r"\[ ENCRYPT & COMMIT ]", variant="primary", id="save-button"
                )

    def on_mount(self) -> None:
        """Focus first input."""
        self.query_one("#title-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            self._save()

    def _save(self) -> None:
        """Save the note entry."""
        title = self.query_one("#title-input", Input).value.strip()
        content = self.query_one("#content-area", TextArea).text

        if not title:
            self.notify("Title is required", severity="error")
            return

        note = NoteEntry(
            title=title,
            content=content,
        )
        self.dismiss(note)

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class EditNoteModal(ModalScreen[dict | None]):
    """Modal for editing an existing secure note - Wide Console Panel Layout."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, note: NoteEntry) -> None:
        super().__init__()
        self.note = note

    def compose(self) -> ComposeResult:
        """Create wide-format console panel layout."""
        with Vertical(id="pwd-modal", classes="note-modal-wide"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static(
                        f"[ :: MODIFY // {self.note.title.upper()[:18]} :: ]",
                        id="modal-title",
                    )
                    yield Static("STATUS: EDIT", classes="modal-status")

            # Form Body - Grid Layout
            with Vertical(id="pwd-form", classes="pwd-form-grid"):
                # Row 1 (Identity): Title spans full width
                with Vertical(classes="form-row form-row-full"):
                    yield Label("> SHARD_TITLE", classes="input-label")
                    yield Input(
                        value=self.note.title,
                        placeholder="e.g. Office Wi-Fi Password",
                        id="title-input",
                    )

                # Row 2 (Content): Full width content editor
                with Vertical(classes="form-row form-row-full form-row-content"):
                    yield Label("> CONTENT", classes="input-label")
                    yield TextArea(
                        self.note.content,
                        id="content-area",
                        classes="note-content-editor",
                    )

            # Footer Actions - docked bottom, right aligned
            with Horizontal(id="modal-buttons", classes="modal-footer"):
                yield Button(r"\[ ABORT ]", variant="default", id="cancel-button")
                yield Button(
                    r"\[ ENCRYPT & COMMIT ]", variant="primary", id="save-button"
                )

    def on_mount(self) -> None:
        """Focus first input (Title field)."""
        self.query_one("#title-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            self._save()

    def _save(self) -> None:
        """Save the changes."""
        title = self.query_one("#title-input", Input).value.strip()
        content = self.query_one("#content-area", TextArea).text

        if not title:
            self.notify("Title is required", severity="error")
            return

        result = {
            "title": title,
            "content": content,
        }
        self.dismiss(result)

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class ConfirmDeleteNoteModal(ModalScreen[bool]):
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
                    yield Static(r"\[ :: PURGE PROTOCOL :: ]", id="modal-title")
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


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN NOTES SCREEN
# ═══════════════════════════════════════════════════════════════════════════════


class NotesScreen(Screen):
    """Screen for managing secure notes - encrypted data shards."""

    BINDINGS = [
        Binding("a", "add", "Add"),
        Binding("c", "copy", "Copy"),
        Binding("e", "edit", "Edit"),
        Binding("d", "delete", "Delete"),
        Binding("v", "view", "View"),
        Binding("escape", "back", "Back"),
    ]

    # Operator theme color tokens - Yellow accent (industrial/encrypted)
    COLORS = {
        "primary": "#00FFFF",  # Cyan - active selection, titles
        "accent": "#eab308",  # Yellow - labels, headers (matches purple luminosity)
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
        """Create the notes screen layout."""
        c = self.COLORS

        # 1. Global Header with Breadcrumbs - Operator theme
        with Horizontal(id="app-header"):
            yield Static(
                f"[bold {c['accent']}]VAULT // DATA_SHARDS[/]",
                id="header-branding",
                classes="screen-header",
            )
            with Horizontal(id="header-right"):
                yield Static("", id="header-lock")  # Will be updated with pulse

        # 2. Body (Master-Detail Split)
        with Horizontal(id="vault-body"):
            # Left Pane: Data Grid (Master) - 65%
            with Vertical(id="vault-grid-pane"):
                yield DataTable(id="notes-table", cursor_type="row")
                # Empty state placeholder (hidden by default)
                with Center(id="empty-state"):
                    yield Static(
                        f"[dim {c['muted']}]╔══════════════════════════════════════╗\n"
                        "║                                      ║\n"
                        "║      NO SHARDS FOUND                 ║\n"
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
                # Inverted Block Header - Operator accent (yellow)
                yield Static(" ≡ SHARD_INSPECTOR ", classes="pane-header-block-accent")
                yield Vertical(id="inspector-content")  # Dynamic content here

        # 3. Global Footer - Mechanical keycap style
        with Horizontal(id="app-footer"):
            yield Static(f" [{c['accent']}]SHARDS[/] ", id="footer-version")
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
        """Initialize table selection and inspector."""
        table = self.query_one("#notes-table", DataTable)
        table.focus()

        app: PassFXApp = self.app  # type: ignore
        entries = app.vault.get_notes()

        if table.row_count > 0:
            # Check for pending selection from search
            target_row = 0
            target_id = entries[0].id if entries else None

            if self._pending_select_id:
                for i, entry in enumerate(entries):
                    if entry.id == self._pending_select_id:
                        target_row = i
                        target_id = entry.id
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
        """Refresh the data table with notes."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#notes-table", DataTable)
        empty_state = self.query_one("#empty-state", Center)
        c = self.COLORS

        table.clear(columns=True)

        # Column layout - data stream style (matching Passwords total: 118)
        table.add_column("", width=2)  # Selection indicator column
        table.add_column("TITLE", width=28)
        table.add_column("LINES", width=8)
        table.add_column("CHARS", width=10)
        table.add_column("SYNC", width=12)
        table.add_column("PREVIEW", width=58)

        entries = app.vault.get_notes()

        # Toggle visibility based on entry count
        if len(entries) == 0:
            table.display = False
            empty_state.display = True
        else:
            table.display = True
            empty_state.display = False

        for entry in entries:
            # Selection indicator - will be updated dynamically
            is_selected = entry.id == self._selected_row_key
            indicator = f"[bold {c['primary']}]▸[/]" if is_selected else " "

            # Title - primary cyan for selected, white otherwise
            title_text = entry.title[:20] if len(entry.title) > 20 else entry.title

            # Lines (muted grey)
            lines_text = f"[{c['muted']}]{entry.line_count}[/]"

            # Chars (muted grey)
            chars_text = f"[{c['muted']}]{entry.char_count}[/]"

            # Relative time (dim muted)
            updated = _get_relative_time(entry.updated_at)
            updated_text = f"[dim {c['muted']}]{updated}[/]"

            # Metadata preview only - NEVER expose content values
            # Security: notes may contain secrets (passwords, keys, sensitive info)
            if entry.char_count > 0:
                preview_text = (
                    f"[dim {c['muted']}]{entry.char_count} chars · [ENCRYPTED][/]"
                )
            else:
                preview_text = f"[dim {c['muted']}]// EMPTY[/]"

            table.add_row(
                indicator,
                title_text,
                lines_text,
                chars_text,
                updated_text,
                preview_text,
                key=entry.id,
            )

        # Update the grid footer with object count
        footer = self.query_one("#grid-footer", Static)
        count = len(entries)
        footer.update(f" └── [{c['primary']}]{count}[/] SHARDS LOADED")

    def _update_row_indicators(self, old_key: str | None, new_key: str | None) -> None:
        """Update only the indicator column for old and new selected rows.

        This avoids rebuilding the entire table on selection change.
        """
        table = self.query_one("#notes-table", DataTable)
        app: PassFXApp = self.app  # type: ignore
        entries = app.vault.get_notes()
        c = self.COLORS

        # Build a map of id -> entry for quick lookup
        entry_map = {e.id: e for e in entries}

        # Get column keys (first column is the indicator)
        if not table.columns:
            return
        indicator_col = list(table.columns.keys())[0]

        # Clear old selection indicator
        if old_key and old_key in entry_map:
            try:
                table.update_cell(old_key, indicator_col, " ")
            except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
                pass  # Row may not exist during rapid navigation

        # Set new selection indicator - cyan arrow for locked target feel
        if new_key and new_key in entry_map:
            try:
                table.update_cell(new_key, indicator_col, f"[bold {c['primary']}]▸[/]")
            except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
                pass  # Row may not exist during rapid navigation

    def _get_selected_entry(self) -> NoteEntry | None:
        """Get the currently selected note entry."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#notes-table", DataTable)

        if table.cursor_row is None:
            return None

        entries = app.vault.get_notes()
        if 0 <= table.cursor_row < len(entries):
            return entries[table.cursor_row]
        return None

    def action_add(self) -> None:
        """Add a new note entry."""

        def handle_result(note: NoteEntry | None) -> None:
            if note:
                app: PassFXApp = self.app  # type: ignore
                app.vault.add_note(note)
                self._refresh_table()
                self.notify(f"Added '{note.title}'", title="Success")

        self.app.push_screen(AddNoteModal(), handle_result)

    def action_copy(self) -> None:
        """Copy content to clipboard with auto-clear for security."""
        entry = self._get_selected_entry()
        if not entry:
            self.notify("No note selected", severity="warning")
            return

        if copy_to_clipboard(entry.content, auto_clear=True):
            self.notify("Note copied! Clears in 15s", title=entry.title)
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_edit(self) -> None:
        """Edit selected note entry."""
        entry = self._get_selected_entry()
        if not entry:
            self.notify("No note selected", severity="warning")
            return

        def handle_result(changes: dict | None) -> None:
            if changes:
                app: PassFXApp = self.app  # type: ignore
                app.vault.update_note(entry.id, **changes)
                self._refresh_table()
                self.notify("Note updated", title="Success")

        self.app.push_screen(EditNoteModal(entry), handle_result)

    def action_delete(self) -> None:
        """Delete selected note entry."""
        entry = self._get_selected_entry()
        if not entry:
            self.notify("No note selected", severity="warning")
            return

        def handle_result(confirmed: bool | None) -> None:
            if confirmed:
                app: PassFXApp = self.app  # type: ignore
                app.vault.delete_note(entry.id)
                self._refresh_table()
                self.notify(f"Deleted '{entry.title}'", title="Deleted")

        self.app.push_screen(ConfirmDeleteNoteModal(entry.title), handle_result)

    def action_view(self) -> None:
        """View note entry details."""
        entry = self._get_selected_entry()
        if not entry:
            self.notify("No note selected", severity="warning")
            return

        self.app.push_screen(ViewNoteModal(entry))

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update inspector when row is highlighted."""
        if hasattr(event.row_key, "value"):
            key_value = event.row_key.value
        else:
            key_value = str(event.row_key)
        old_key = self._selected_row_key
        self._selected_row_key = key_value
        self._update_inspector(key_value)
        self._update_row_indicators(old_key, key_value)

    # pylint: disable=too-many-locals,too-many-statements
    def _update_inspector(self, row_key: Any) -> None:
        """Update the inspector panel with note details.

        Renders a structured "Shard Inspector" with:
        - Entry Header (large text, primary color)
        - Field Grid (labels in accent, values in text)
        - Shard Stats (lines, chars)
        - Preview Section (terminal style)
        """
        inspector = self.query_one("#inspector-content", Vertical)
        inspector.remove_children()
        c = self.COLORS

        # Get the entry by row key
        app: PassFXApp = self.app  # type: ignore
        entries = app.vault.get_notes()

        # Find entry by ID
        entry = None
        for e in entries:
            if e.id == str(row_key):
                entry = e
                break

        if not entry:
            # Empty state - styled for Operator theme
            inspector.mount(
                Static(
                    f"[dim {c['muted']}]╔══════════════════════════════╗\n"
                    "║                              ║\n"
                    "║    SELECT A SHARD            ║\n"
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
                    f"[bold underline {c['primary']}]{entry.title.upper()}[/]",
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
                # Type field
                Horizontal(
                    Static(f"[{c['accent']}]TYPE[/]", classes="field-label"),
                    Static(f"[{c['text']}]ENCRYPTED_SHARD[/]", classes="field-value"),
                    classes="field-row",
                ),
                # Content hint - truncated
                Horizontal(
                    Static(f"[{c['accent']}]DATA[/]", classes="field-label"),
                    Static(
                        f"[{c['muted']}]●●●●●●●●●●●●[/]  " f"[dim]\\[V] to reveal[/]",
                        classes="field-value",
                    ),
                    classes="field-row",
                ),
                classes="field-grid",
            )
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 3: Shard Stats - Size metrics
        # ═══════════════════════════════════════════════════════════════
        inspector.mount(
            Vertical(
                Static(
                    f"[{c['accent']}]SHARD_STATS[/]", classes="strength-section-label"
                ),
                Static(
                    f"[{c['text']}]{entry.line_count}[/] lines  "
                    f"[{c['text']}]{entry.char_count}[/] chars",
                    classes="strength-bar",
                ),
                classes="strength-section",
            )
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 4: Content Summary - Metadata only, no secret exposure
        # Security: notes may contain secrets - NEVER render content in inspector
        # ═══════════════════════════════════════════════════════════════
        if entry.content:
            # Show safe metadata only
            content_display = (
                f"[{c['muted']}]●●●●●●●●●●●●●●●●●●●●[/]\n\n"
                f"[dim {c['muted']}]{entry.line_count} lines · "
                f"{entry.char_count} characters[/]\n\n"
                f"[dim]Press [bold {c['primary']}]V[/] to reveal content[/]"
            )
        else:
            content_display = f"[dim {c['muted']}]// EMPTY[/]"

        notes_terminal = Vertical(
            Static(content_display, classes="notes-code"),
            Static("▌", classes="blink-cursor") if not entry.content else Static(""),
            classes="notes-terminal-box",
        )
        notes_terminal.border_title = "ENCRYPTED"

        inspector.mount(
            Vertical(
                Static(f"[{c['accent']}]CONTENT[/]", classes="notes-section-label"),
                notes_terminal,
                classes="notes-section",
            )
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 5: Footer Metadata Bar (ID + Updated)
        # ═══════════════════════════════════════════════════════════════
        try:
            updated_full = datetime.fromisoformat(entry.updated_at).strftime(
                "%Y-%m-%d %H:%M"
            )
        except (ValueError, TypeError):
            updated_full = entry.updated_at or "Unknown"

        inspector.mount(
            Horizontal(
                Static(
                    f"[dim {c['muted']}]ID:[/] [{c['muted']}]{entry.id[:8]}[/]",
                    classes="meta-id",
                ),
                Static(
                    f"[dim {c['muted']}]SYNC:[/] [{c['muted']}]{updated_full}[/]",
                    classes="meta-updated",
                ),
                classes="inspector-footer-bar",
            )
        )
