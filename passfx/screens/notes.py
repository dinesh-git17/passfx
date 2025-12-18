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
    """Modal displaying secure note visualization matching password modal style."""

    # Color configuration for the note modal (Amber/Yellow theme)
    COLORS = {
        "border": "#f59e0b",
        "card_bg": "#0a0e27",
        "section_border": "#475569",
        "title_bg": "#fbbf24",
        "title_fg": "#000000",
        "label_dim": "#64748b",
        "value_fg": "#f8fafc",
        "accent": "#fcd34d",
        "muted": "#94a3b8",
    }

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "copy_content", "Copy"),
    ]

    def __init__(self, note: NoteEntry) -> None:
        super().__init__()
        self.note = note

    def compose(
        self,
    ) -> ComposeResult:  # pylint: disable=too-many-locals,too-many-statements
        """Create the secure note visualization layout."""
        c = self.COLORS

        # Format timestamp
        try:
            created = datetime.fromisoformat(self.note.created_at).strftime("%Y.%m.%d")
        except (ValueError, TypeError):
            created = "UNKNOWN"

        # Card dimensions (matching password modal)
        width = 96
        inner = width - 2
        section_inner = width - 6
        content_width = section_inner - 5

        # Truncate title if needed
        if len(self.note.title) > content_width:
            title_display = self.note.title[:content_width]
        else:
            title_display = self.note.title

        # Get content preview (first 80 chars per line, max 3 lines)
        content_lines = self.note.content.split("\n")[:3]
        preview_lines = []
        for line in content_lines:
            preview = line[:content_width] if len(line) > content_width else line
            preview_lines.append(preview)

        with Vertical(id="note-modal"):
            with Vertical(id="physical-note-card"):
                # Top border
                yield Static(f"[bold {c['border']}]╔{'═' * inner}╗[/]")

                # Title row
                title = " ENCRYPTED DATA SHARD "
                title_pad = inner - len(title) - 2
                title_line = (
                    f"[bold {c['border']}]║[/]  "
                    f"[on {c['title_bg']}][bold {c['title_fg']}]{title}[/]"
                    f"{' ' * title_pad}[bold {c['border']}]║[/]"
                )
                yield Static(title_line)

                # Divider
                yield Static(f"[bold {c['border']}]╠{'═' * inner}╣[/]")

                # Shard label
                shard_line = (
                    f"[bold {c['border']}]║[/]  [dim {c['label_dim']}]SHARD:[/] "
                    f"[bold {c['value_fg']}]{title_display:<{inner - 11}}[/] "
                    f"[bold {c['border']}]║[/]"
                )
                yield Static(shard_line)

                # Spacer
                yield Static(
                    f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]"
                )

                # Stats section
                stats = (
                    f"[{c['accent']}]{self.note.line_count}[/] lines  "
                    f"[{c['accent']}]{self.note.char_count}[/] chars"
                )
                stats_line = (
                    f"[bold {c['border']}]║[/]  [dim {c['label_dim']}]STATS:[/] "
                    f"{stats:<{inner - 11}}[bold {c['border']}]║[/]"
                )
                yield Static(stats_line)

                # Spacer
                yield Static(
                    f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]"
                )

                # Content section
                content_header = (
                    f"[bold {c['border']}]║[/]  [dim {c['section_border']}]"
                    f"┌─ CONTENT PREVIEW {'─' * (section_inner - 20)}┐[/]  "
                    f"[bold {c['border']}]║[/]"
                )
                yield Static(content_header)

                # Show preview lines
                for line in preview_lines:
                    preview_line = (
                        f"[bold {c['border']}]║[/]  [dim {c['section_border']}]│[/] "
                        f"[{c['accent']}]►[/] [{c['value_fg']}]{line:<{content_width}}[/] "
                        f"[dim {c['section_border']}]│[/]  [bold {c['border']}]║[/]"
                    )
                    yield Static(preview_line)

                # If less than 3 lines, pad with empty lines
                for _ in range(3 - len(preview_lines)):
                    empty_line = (
                        f"[bold {c['border']}]║[/]  [dim {c['section_border']}]│[/]   "
                        f"{' ' * content_width} [dim {c['section_border']}]│[/]  "
                        f"[bold {c['border']}]║[/]"
                    )
                    yield Static(empty_line)

                content_footer = (
                    f"[bold {c['border']}]║[/]  [dim {c['section_border']}]"
                    f"└{'─' * (section_inner - 1)}┘[/]  [bold {c['border']}]║[/]"
                )
                yield Static(content_footer)

                # Spacer
                yield Static(
                    f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]"
                )

                # Footer divider
                yield Static(f"[bold {c['border']}]╠{'═' * inner}╣[/]")

                # Footer row
                footer_left = (
                    f"  [dim {c['section_border']}]ID:[/] "
                    f"[{c['muted']}]{self.note.id[:8]}[/]"
                )
                footer_right = (
                    f"[dim {c['section_border']}]CREATED:[/] [{c['muted']}]{created}[/]"
                )
                footer_pad = inner - 32 - len(created)
                footer_full = (
                    f"[bold {c['border']}]║[/]{footer_left}{' ' * footer_pad}"
                    f"{footer_right}  [bold {c['border']}]║[/]"
                )
                yield Static(footer_full)

                # Bottom border
                yield Static(f"[bold {c['border']}]╚{'═' * inner}╝[/]")

            # Action Buttons
            with Horizontal(id="note-modal-buttons"):
                yield Button("COPY", id="copy-button")
                yield Button("CLOSE", id="close-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "close-button":
            self.dismiss(None)
        elif event.button.id == "copy-button":
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
                yield Label(
                    "[#94a3b8]CONTENT[/]  [dim #64748b]secure text[/]",
                    classes="note-input-label",
                )
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
                yield Input(
                    value=self.note.title,
                    placeholder="e.g. Office Wi-Fi Password",
                    id="title-input",
                )

                yield Label(
                    "[#94a3b8]CONTENT[/]  [dim #64748b]secure text[/]",
                    classes="note-input-label",
                )
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
                yield Static(
                    f"[#f8fafc]TARGET: '{self.item_name}'[/]", classes="delete-target"
                )
                yield Static(
                    "[bold #ef4444]THIS ACTION CANNOT BE UNDONE[/]", classes="warning"
                )
            with Horizontal(id="modal-buttons"):
                yield Button("[ESC] ABORT", id="cancel-button")
                yield Button(
                    "[Y] CONFIRM DELETE", id="delete-button", classes="note-delete-btn"
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
