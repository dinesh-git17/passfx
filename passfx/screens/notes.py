"""Secure Notes Screen for PassFX - Encrypted Data Shards."""

# pylint: disable=duplicate-code

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


def _get_relative_time(
    iso_timestamp: str | None,
) -> str:  # pylint: disable=too-many-return-statements
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
    """Modal for viewing a note - Operator Grade Secure Read Console."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "copy_content", "Copy"),
    ]

    def __init__(self, note: NoteEntry) -> None:
        super().__init__()
        self.note = note

    def compose(self) -> ComposeResult:
        """Create the Operator-grade view modal layout."""
        # Get content preview (first 60 chars)
        preview = (
            self.note.content[:60] + "..."
            if len(self.note.content) > 60
            else self.note.content
        )
        preview = preview.replace("\n", " ")

        with Vertical(id="pwd-modal", classes="secure-terminal"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static("[ :: SECURE READ PROTOCOL :: ]", id="modal-title")
                    yield Static("STATUS: DECRYPTED", classes="modal-status")

            # Data Display Body
            with Vertical(id="pwd-form"):
                # Row 1: Title
                yield Label("> SHARD_TITLE", classes="input-label")
                yield Static(
                    f"  {self.note.title}", classes="view-value", id="title-value"
                )

                # Row 2: Stats
                yield Label("> SHARD_STATS", classes="input-label")
                yield Static(
                    f"  [#fcd34d]{self.note.line_count}[/] lines  "
                    f"[#fcd34d]{self.note.char_count}[/] chars",
                    classes="view-value",
                    id="stats-value",
                )

                # Row 3: Content Preview
                yield Label("> CONTENT_PREVIEW", classes="input-label")
                yield Static(
                    f"  [#f59e0b]{preview}[/]",
                    classes="view-value secret",
                    id="preview-value",
                )

            # Footer Actions - right aligned
            with Horizontal(id="modal-buttons"):
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
    """Modal for adding a new secure note - Operator Grade Secure Write Console."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Create the Operator-grade modal layout with TextArea."""
        with Vertical(id="note-edit-modal"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static(
                        "[bold #94a3b8][ :: SECURE WRITE PROTOCOL :: ][/]",
                        id="note-edit-title",
                    )
                    yield Static("[#22c55e]STATUS: OPEN[/]", classes="modal-status")

            # Form
            with Vertical(id="note-form"):
                # Title input
                yield Label("[#94a3b8]> MEMO_TITLE[/]", classes="note-input-label")
                yield Input(placeholder="e.g. Office Wi-Fi Password", id="title-input")

                # Content TextArea
                yield Label(
                    "[#94a3b8]> CONTENT[/]  [dim #64748b]secure text[/]",
                    classes="note-input-label",
                )
                yield TextArea(
                    "",
                    id="content-area",
                    classes="note-code-editor",
                )

            # Footer Actions - right aligned
            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ ABORT ]", id="cancel-button")
                yield Button(
                    r"\[ ENCRYPT & COMMIT ]", id="save-button", classes="note-save-btn"
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
    """Modal for editing an existing secure note - Operator Grade Console."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, note: NoteEntry) -> None:
        super().__init__()
        self.note = note

    def compose(self) -> ComposeResult:
        """Create the Operator-grade modal layout."""
        with Vertical(id="note-edit-modal"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static(
                        f"[bold #94a3b8][ :: MODIFY // {self.note.title.upper()[:18]} :: ][/]",
                        id="note-edit-title",
                    )
                    yield Static("[#22c55e]STATUS: EDIT[/]", classes="modal-status")

            # Form
            with Vertical(id="note-form"):
                yield Label("[#94a3b8]> MEMO_TITLE[/]", classes="note-input-label")
                yield Input(
                    value=self.note.title,
                    placeholder="e.g. Office Wi-Fi Password",
                    id="title-input",
                )

                yield Label(
                    "[#94a3b8]> CONTENT[/]  [dim #64748b]secure text[/]",
                    classes="note-input-label",
                )
                yield TextArea(
                    self.note.content,
                    id="content-area",
                    classes="note-code-editor",
                )

            # Footer Actions - right aligned
            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ ABORT ]", id="cancel-button")
                yield Button(
                    r"\[ ENCRYPT & COMMIT ]", id="save-button", classes="note-save-btn"
                )

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
        with Vertical(id="note-delete-modal"):
            # HUD Header with warning status
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static(
                        "[bold #94a3b8][ :: PURGE PROTOCOL :: ][/]",
                        id="note-delete-title",
                    )
                    yield Static("[#ef4444]STATUS: ARMED[/]", classes="modal-status")
            with Vertical(id="delete-content"):
                yield Static(
                    f"[#f8fafc]TARGET: '{self.item_name}'[/]", classes="delete-target"
                )
                yield Static(
                    "[bold #ef4444]THIS ACTION CANNOT BE UNDONE[/]", classes="warning"
                )
            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ ABORT ]", id="cancel-button")
                yield Button(
                    r"\[ CONFIRM PURGE ]", id="delete-button", classes="note-delete-btn"
                )

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
            breadcrumb = (
                "[dim #64748b]HOME[/] [#475569]>[/] "
                "[dim #64748b]VAULT[/] [#475569]>[/] [bold #f59e0b]NOTES[/]"
            )
            yield Static(breadcrumb, id="header-branding")
            yield Static("░░ ENCRYPTED DATA SHARDS ░░", id="header-status")
            yield Static("", id="header-lock")

        # 2. Body (Master-Detail Split)
        with Horizontal(id="vault-body"):
            # Left Pane: Data Grid (Master) - 65%
            with Vertical(id="vault-grid-pane"):
                yield Static(" ≡ SHARD_DATABASE ", classes="pane-header-block-amber")
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
                yield Static(
                    " └── SYSTEM_READY", classes="pane-footer", id="grid-footer"
                )

            # Right Pane: Inspector (Detail) - 35%
            with Vertical(id="vault-inspector"):
                yield Static(" ≡ SHARD_INSPECTOR ", classes="pane-header-block-amber")
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
            header_lock.update("[#fcd34d]● [bold]ARCHIVED[/][/]")
        else:
            header_lock.update("[#b45309]○ [bold]ARCHIVED[/][/]")

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

    def _refresh_table(self) -> None:  # pylint: disable=too-many-locals
        """Refresh the data table."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#notes-table", DataTable)
        empty_state = self.query_one("#empty-state", Center)

        table.clear(columns=True)

        table.add_column("", width=3)  # Indicator
        table.add_column("Title", width=30)  # Title
        table.add_column("Lines", width=8)  # Lines
        table.add_column("Chars", width=10)  # Chars
        table.add_column("Updated", width=12)  # Updated - fixed width
        # Content preview to fill remaining space
        table.add_column("Preview", width=60)

        entries = app.vault.get_notes()

        if len(entries) == 0:
            table.display = False
            empty_state.display = True
        else:
            table.display = True
            empty_state.display = False

        for entry in entries:
            is_selected = entry.id == self._selected_row_key
            indicator = "[bold #f59e0b]▍[/]" if is_selected else " "
            title_text = entry.title[:23] if len(entry.title) > 23 else entry.title
            lines_text = f"[#94a3b8]{entry.line_count}[/]"
            chars_text = f"[#94a3b8]{entry.char_count}[/]"
            updated = _get_relative_time(entry.updated_at)
            updated_text = f"[dim]{updated}[/]"
            # Truncate content preview to first 50 characters
            notes_preview = (
                entry.content[:50] if len(entry.content) > 50 else entry.content
            )
            if len(entry.content) > 50:
                notes_preview += "…"
            if notes_preview:
                notes_text = f"[dim #94a3b8]{notes_preview}[/]"
            else:
                notes_text = "[dim #555555]// EMPTY[/]"

            table.add_row(
                indicator,
                title_text,
                lines_text,
                chars_text,
                updated_text,
                notes_text,
                key=entry.id,
            )

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
            except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
                pass  # Row may not exist during rapid navigation

        if new_key and new_key in entry_map:
            try:
                table.update_cell(new_key, indicator_col, "[bold #f59e0b]▍[/]")
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

    # pylint: disable=too-many-locals
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
                        Static(
                            "[on #94a3b8][bold #000000] MEM [/][/]",
                            classes="avatar-char",
                        ),
                        Static("[on #94a3b8]     [/]", classes="avatar-char"),
                        classes="avatar-box",
                    ),
                    Vertical(
                        Static(
                            f"[bold #f8fafc]{entry.title}[/]", classes="id-label-text"
                        ),
                        Static(
                            "[dim #94a3b8]Encrypted Data Shard[/]",
                            classes="id-email-text",
                        ),
                        classes="id-details-stack",
                    ),
                    classes="id-card-header",
                ),
                classes="id-card-wrapper note-card",
            )
        )

        # Section 2: Stats Widget
        stats_text = (
            f"[#94a3b8]LINES:[/] {entry.line_count}    "
            f"[#94a3b8]CHARS:[/] {entry.char_count}"
        )
        inspector.mount(
            Vertical(
                Static("[dim #6b7280]▸ SHARD STATS[/]", classes="section-label"),
                Static(stats_text, classes="strength-bar-widget"),
                classes="security-widget",
            )
        )

        # Section 3: Content Preview
        preview_lines = []
        if entry.content:
            lines = entry.content.split("\n")[:8]
            for i, line in enumerate(lines, 1):
                line_preview = line[:35] if len(line) > 35 else line
                formatted_line = f"[dim #475569]{i:2}[/] │ [#94a3b8]{line_preview}[/]"
                preview_lines.append(formatted_line)
            if len(entry.content.split("\n")) > 8:
                more_text = "[dim #475569]   [/]   [dim #64748b]... more content[/]"
                preview_lines.append(more_text)
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
            updated_full = datetime.fromisoformat(entry.updated_at).strftime(
                "%Y-%m-%d %H:%M"
            )
        except (ValueError, TypeError):
            updated_full = entry.updated_at or "Unknown"

        inspector.mount(
            Horizontal(
                Static(
                    f"[dim #475569]ID:[/] [#64748b]{entry.id[:8]}[/]",
                    classes="meta-id",
                ),
                Static(
                    f"[dim #475569]UPDATED:[/] [#64748b]{updated_full}[/]",
                    classes="meta-updated",
                ),
                classes="inspector-footer-bar",
            )
        )
