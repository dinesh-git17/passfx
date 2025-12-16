"""Secure Notes Screen for PassFX - Encrypted Data Shards."""

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
    TextArea,
)

from passfx.core.models import NoteEntry
from passfx.utils.clipboard import copy_to_clipboard

if TYPE_CHECKING:
    from passfx.app import PassFXApp


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def _get_relative_time(iso_timestamp: str | None) -> str:
    """Convert ISO timestamp to relative time string."""
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
    """Modal displaying secure note in a clean viewer."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "copy_content", "Copy"),
    ]

    def __init__(self, note: NoteEntry) -> None:
        super().__init__()
        self.note = note

    def compose(self) -> ComposeResult:
        """Create the viewer layout."""
        try:
            created = datetime.fromisoformat(self.note.created_at).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            created = "Unknown"

        with Vertical(id="note-view-modal"):
            # Header
            yield Static("MEMO :: CLASSIFIED", id="note-view-title")

            # Info section
            with Vertical(id="note-view-info"):
                yield Static(f"[bold #f8fafc]{self.note.title}[/]", classes="note-view-name")
                with Horizontal(classes="note-view-stats"):
                    yield Static(f"[dim]LINES:[/] [#94a3b8]{self.note.line_count}[/]")
                    yield Static(f"[dim]CHARS:[/] [#94a3b8]{self.note.char_count}[/]")
                    yield Static(f"[dim]ID:[/] [#64748b]{self.note.id[:8]}[/]")

            # Content area - read-only TextArea
            yield TextArea(
                self.note.content,
                id="note-view-content",
                read_only=True,
                classes="note-code-editor-view",
            )

            # Footer
            yield Static(f"[dim]Created: {created}[/]", id="note-view-footer")

            # Buttons
            with Horizontal(id="modal-buttons"):
                yield Button("COPY", id="copy-button", classes="note-import-btn")
                yield Button("CLOSE", id="close-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "close-button":
            self.dismiss(None)
        elif event.button.id == "copy-button":
            self._copy_content()

    def _copy_content(self) -> None:
        """Copy content to clipboard."""
        if copy_to_clipboard(self.note.content, auto_clear=False):
            self.notify("Note copied to clipboard", title="Copied")
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)

    def action_copy_content(self) -> None:
        """Copy content via keybinding."""
        self._copy_content()


class AddNoteModal(ModalScreen[NoteEntry | None]):
    """Modal for adding a new secure note with TextArea support."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Create the modal layout with TextArea."""
        with Vertical(id="note-edit-modal"):
            # Header
            yield Static(
                "[bold #94a3b8]╔══ DATA_SHARD // NEW ENTRY ══╗[/]",
                id="note-edit-title",
            )

            # Form
            with Vertical(id="note-form"):
                # Title input
                yield Label("[#94a3b8]MEMO_TITLE[/]", classes="note-input-label")
                yield Input(placeholder="e.g. Office Wi-Fi Password", id="title-input")

                # Content TextArea
                yield Label("[#94a3b8]CONTENT[/]  [dim #64748b]secure text[/]", classes="note-input-label")
                yield TextArea(
                    "",
                    id="content-area",
                    classes="note-code-editor",
                )

            # All buttons on one line
            with Horizontal(id="modal-buttons"):
                yield Button("ABORT", id="cancel-button")
                yield Button("SAVE", id="save-button", classes="note-save-btn")

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
    """Modal for editing an existing secure note."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, note: NoteEntry) -> None:
        super().__init__()
        self.note = note

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="note-edit-modal"):
            # Header
            yield Static(
                f"[bold #94a3b8]╔══ MODIFY_SHARD // {self.note.title.upper()[:20]} ══╗[/]",
                id="note-edit-title",
            )

            # Form
            with Vertical(id="note-form"):
                yield Label("[#94a3b8]MEMO_TITLE[/]", classes="note-input-label")
                yield Input(value=self.note.title, placeholder="e.g. Office Wi-Fi Password", id="title-input")

                yield Label("[#94a3b8]CONTENT[/]  [dim #64748b]secure text[/]", classes="note-input-label")
                yield TextArea(
                    self.note.content,
                    id="content-area",
                    classes="note-code-editor",
                )

            # All buttons on one line
            with Horizontal(id="modal-buttons"):
                yield Button("ABORT", id="cancel-button")
                yield Button("SAVE", id="save-button", classes="note-save-btn")

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
        with Vertical(id="note-delete-modal"):
            yield Static(
                "[bold #94a3b8]╔══ CONFIRM_DELETE // WARNING ══╗[/]",
                id="note-delete-title",
            )
            with Vertical(id="delete-content"):
                yield Static(f"[#f8fafc]TARGET: '{self.item_name}'[/]", classes="delete-target")
                yield Static("[bold #ef4444]THIS ACTION CANNOT BE UNDONE[/]", classes="warning")
            with Horizontal(id="modal-buttons"):
                yield Button("[ESC] ABORT", id="cancel-button")
                yield Button("[Y] CONFIRM DELETE", id="delete-button", classes="note-delete-btn")

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

    def __init__(self) -> None:
        super().__init__()
        self._selected_row_key: str | None = None
        self._pulse_state: bool = True

    def compose(self) -> ComposeResult:
        """Create the notes screen layout."""
        # 1. Global Header with Breadcrumbs
        with Horizontal(id="app-header"):
            yield Static(
                "[dim #64748b]HOME[/] [#475569]>[/] [dim #64748b]VAULT[/] [#475569]>[/] [bold #94a3b8]NOTES[/]",
                id="header-branding",
            )
            yield Static("░░ ENCRYPTED DATA SHARDS ░░", id="header-status")
            yield Static("", id="header-lock")

        # 2. Body (Master-Detail Split)
        with Horizontal(id="vault-body"):
            # Left Pane: Data Grid (Master) - 65%
            with Vertical(id="vault-grid-pane"):
                yield Static(" ≡ SHARD_DATABASE ", classes="pane-header-block note-header")
                yield DataTable(id="notes-table", cursor_type="row")
                # Empty state
                with Center(id="empty-state"):
                    yield Static(
                        "[dim #475569]╔══════════════════════════════════════╗\n"
                        "║                                      ║\n"
                        "║      NO SECURE NOTES FOUND           ║\n"
                        "║                                      ║\n"
                        "║      INITIATE SEQUENCE [A]           ║\n"
                        "║                                      ║\n"
                        "╚══════════════════════════════════════╝[/]",
                        id="empty-state-text",
                    )
                yield Static(" └── SYSTEM_READY", classes="pane-footer", id="grid-footer")

            # Right Pane: Inspector (Detail) - 35%
            with Vertical(id="vault-inspector"):
                yield Static(" ≡ SHARD_INSPECTOR ", classes="pane-header-block note-header")
                yield Vertical(id="inspector-content")

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
        self.call_after_refresh(self._initialize_selection)
        self._update_pulse()
        self.set_interval(1.0, self._update_pulse)

    def _update_pulse(self) -> None:
        """Update the pulse indicator."""
        self._pulse_state = not self._pulse_state
        header_lock = self.query_one("#header-lock", Static)
        if self._pulse_state:
            header_lock.update("[#94a3b8]● [bold]ARCHIVED[/][/]")
        else:
            header_lock.update("[#64748b]○ [bold]ARCHIVED[/][/]")

    def _initialize_selection(self) -> None:
        """Initialize table selection and inspector."""
        table = self.query_one("#notes-table", DataTable)
        table.focus()
        if table.row_count > 0:
            table.move_cursor(row=0)
            app: PassFXApp = self.app  # type: ignore
            entries = app.vault.get_notes()
            if entries:
                self._selected_row_key = entries[0].id
                self._update_inspector(entries[0].id)
        else:
            self._update_inspector(None)

    def _refresh_table(self) -> None:
        """Refresh the data table."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#notes-table", DataTable)
        empty_state = self.query_one("#empty-state", Center)

        table.clear(columns=True)

        table.add_column("", width=2)
        table.add_column("Title", width=28)
        table.add_column("Lines", width=8)
        table.add_column("Updated", width=10)

        entries = app.vault.get_notes()

        if len(entries) == 0:
            table.display = False
            empty_state.display = True
        else:
            table.display = True
            empty_state.display = False

        for entry in entries:
            is_selected = entry.id == self._selected_row_key
            indicator = "[bold #94a3b8]▍[/]" if is_selected else " "
            title_text = entry.title[:26] if len(entry.title) > 26 else entry.title
            lines_text = f"[#94a3b8]{entry.line_count}[/]"
            updated = _get_relative_time(entry.updated_at)
            updated_text = f"[dim]{updated}[/]"

            table.add_row(indicator, title_text, lines_text, updated_text, key=entry.id)

        footer = self.query_one("#grid-footer", Static)
        count = len(entries)
        footer.update(f" └── [{count}] SHARDS LOADED")

    def _update_row_indicators(self, old_key: str | None, new_key: str | None) -> None:
        """Update indicator column for selection change."""
        table = self.query_one("#notes-table", DataTable)
        app: PassFXApp = self.app  # type: ignore
        entries = app.vault.get_notes()
        entry_map = {e.id: e for e in entries}

        if not table.columns:
            return
        indicator_col = list(table.columns.keys())[0]

        if old_key and old_key in entry_map:
            try:
                table.update_cell(old_key, indicator_col, " ")
            except Exception:
                pass

        if new_key and new_key in entry_map:
            try:
                table.update_cell(new_key, indicator_col, "[bold #94a3b8]▍[/]")
            except Exception:
                pass

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
        """Copy content to clipboard."""
        entry = self._get_selected_entry()
        if not entry:
            self.notify("No note selected", severity="warning")
            return

        if copy_to_clipboard(entry.content, auto_clear=False):
            self.notify("Note copied to clipboard", title=entry.title)
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

        def handle_result(confirmed: bool) -> None:
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
        key_value = event.row_key.value if hasattr(event.row_key, "value") else str(event.row_key)
        old_key = self._selected_row_key
        self._selected_row_key = key_value
        self._update_inspector(key_value)
        self._update_row_indicators(old_key, key_value)

    def _update_inspector(self, row_key: Any) -> None:
        """Update the inspector panel with note details."""
        inspector = self.query_one("#inspector-content", Vertical)
        inspector.remove_children()

        app: PassFXApp = self.app  # type: ignore
        entries = app.vault.get_notes()

        entry = None
        for e in entries:
            if e.id == str(row_key):
                entry = e
                break

        if not entry:
            inspector.mount(
                Static(
                    "[dim #555555]╔══════════════════════════╗\n"
                    "║    SELECT A DATA SHARD   ║\n"
                    "║    TO VIEW DETAILS       ║\n"
                    "╚══════════════════════════╝[/]",
                    classes="inspector-empty",
                )
            )
            return

        # Section 1: Note ID Card
        inspector.mount(
            Vertical(
                Horizontal(
                    Vertical(
                        Static("[on #94a3b8][bold #000000] MEM [/][/]", classes="avatar-char"),
                        Static("[on #94a3b8]     [/]", classes="avatar-char"),
                        classes="avatar-box",
                    ),
                    Vertical(
                        Static(f"[bold #f8fafc]{entry.title}[/]", classes="id-label-text"),
                        Static("[dim #94a3b8]Encrypted Data Shard[/]", classes="id-email-text"),
                        classes="id-details-stack",
                    ),
                    classes="id-card-header",
                ),
                classes="id-card-wrapper note-card",
            )
        )

        # Section 2: Stats Widget
        inspector.mount(
            Vertical(
                Static("[dim #6b7280]▸ SHARD STATS[/]", classes="section-label"),
                Static(
                    f"[#94a3b8]LINES:[/] {entry.line_count}    [#94a3b8]CHARS:[/] {entry.char_count}",
                    classes="strength-bar-widget",
                ),
                classes="security-widget",
            )
        )

        # Section 3: Content Preview
        preview_lines = []
        if entry.content:
            lines = entry.content.split("\n")[:8]
            for i, line in enumerate(lines, 1):
                line_preview = line[:35] if len(line) > 35 else line
                preview_lines.append(f"[dim #475569]{i:2}[/] │ [#94a3b8]{line_preview}[/]")
            if len(entry.content.split("\n")) > 8:
                preview_lines.append("[dim #475569]   [/]   [dim #64748b]... more content[/]")
        else:
            preview_lines.append("[dim #64748b] 1[/] │ [dim #555555]// EMPTY[/]")

        preview_content = "\n".join(preview_lines)
        notes_terminal = Vertical(
            Static(preview_content, classes="notes-code"),
            classes="notes-editor note-preview",
        )
        notes_terminal.border_title = "CONTENT_PREVIEW"

        inspector.mount(
            Vertical(
                Static("[dim #6b7280]▸ PREVIEW[/]", classes="section-label"),
                notes_terminal,
                classes="notes-section",
            )
        )

        # Section 4: Footer
        try:
            updated_full = datetime.fromisoformat(entry.updated_at).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            updated_full = entry.updated_at or "Unknown"

        inspector.mount(
            Horizontal(
                Static(f"[dim #475569]ID:[/] [#64748b]{entry.id[:8]}[/]", classes="meta-id"),
                Static(f"[dim #475569]UPDATED:[/] [#64748b]{updated_full}[/]", classes="meta-updated"),
                classes="inspector-footer-bar",
            )
        )
