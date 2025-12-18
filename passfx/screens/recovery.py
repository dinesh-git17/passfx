"""Recovery Codes Screen for PassFX - Fail-Safe Protocol."""

# pylint: disable=duplicate-code

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Input, Label, Static, TextArea

from passfx.core.models import RecoveryEntry
from passfx.utils.clipboard import copy_to_clipboard

if TYPE_CHECKING:
    from passfx.app import PassFXApp


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


# pylint: disable=too-many-return-statements
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


class ViewRecoveryModal(ModalScreen[None]):
    """Modal displaying recovery codes visualization matching password modal style."""

    # Color configuration for the recovery modal (Rose theme)
    COLORS = {
        "border": "#f43f5e",
        "card_bg": "#0a0e27",
        "section_border": "#475569",
        "title_bg": "#fb7185",
        "title_fg": "#000000",
        "label_dim": "#64748b",
        "value_fg": "#f8fafc",
        "accent": "#fda4af",
        "muted": "#94a3b8",
    }

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "copy_content", "Copy"),
    ]

    def __init__(self, recovery: RecoveryEntry) -> None:
        super().__init__()
        self.recovery = recovery

    # pylint: disable=too-many-locals,too-many-statements
    def compose(self) -> ComposeResult:
        """Create the recovery codes visualization layout."""
        c = self.COLORS

        # Format timestamp
        try:
            created = datetime.fromisoformat(self.recovery.created_at).strftime(
                "%Y.%m.%d"
            )
        except (ValueError, TypeError):
            created = "UNKNOWN"

        # Card dimensions (matching password modal)
        width = 96
        inner = width - 2
        section_inner = width - 6
        content_width = section_inner - 5

        # Truncate title if needed
        title_display = (
            self.recovery.title[:content_width]
            if len(self.recovery.title) > content_width
            else self.recovery.title
        )

        # Get content preview (first 5 lines for recovery codes)
        content_lines = (
            self.recovery.content.split("\n")[:5] if self.recovery.content else []
        )
        preview_lines = []
        for line in content_lines:
            # Mask recovery codes for security (show first 4 and last 4 chars)
            line = line.strip()
            if line and not line.startswith("#"):
                if len(line) > 8:
                    masked = line[:4] + "•" * (len(line) - 8) + line[-4:]
                else:
                    masked = line
                preview_lines.append(masked[:content_width])
            else:
                preview_lines.append(
                    line[:content_width] if len(line) > content_width else line
                )

        with Vertical(id="recovery-modal"):
            with Vertical(id="physical-recovery-card"):
                # Top border
                yield Static(f"[bold {c['border']}]╔{'═' * inner}╗[/]")

                # Title row
                title = " FAIL-SAFE PROTOCOL "
                title_pad = inner - len(title) - 2
                yield Static(
                    f"[bold {c['border']}]║[/]  "
                    f"[on {c['title_bg']}][bold {c['title_fg']}]{title}[/]"
                    f"{' ' * title_pad}[bold {c['border']}]║[/]"
                )

                # Divider
                yield Static(f"[bold {c['border']}]╠{'═' * inner}╣[/]")

                # Service label
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['label_dim']}]SERVICE:[/] "
                    f"[bold {c['value_fg']}]{title_display:<{inner - 13}}[/] "
                    f"[bold {c['border']}]║[/]"
                )

                # Spacer
                yield Static(
                    f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]"
                )

                # Stats section
                stats = (
                    f"[{c['accent']}]{self.recovery.line_count}[/] lines  "
                    f"[{c['accent']}]{self.recovery.code_count}[/] codes"
                )
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['label_dim']}]STATS:[/]   "
                    f"{stats:<{inner - 13}}[bold {c['border']}]║[/]"
                )

                # Spacer
                yield Static(
                    f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]"
                )

                # Content section
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['section_border']}]"
                    f"┌─ RECOVERY CODES {'─' * (section_inner - 19)}┐[/]  "
                    f"[bold {c['border']}]║[/]"
                )

                # Show preview lines (masked codes)
                for line in preview_lines:
                    if line and not line.startswith("#"):
                        # Recovery code - show masked
                        yield Static(
                            f"[bold {c['border']}]║[/]  [dim {c['section_border']}]│[/] "
                            f"[{c['accent']}]►[/] [{c['accent']}]{line:<{content_width}}[/] "
                            f"[dim {c['section_border']}]│[/]  [bold {c['border']}]║[/]"
                        )
                    else:
                        # Comment or empty
                        yield Static(
                            f"[bold {c['border']}]║[/]  [dim {c['section_border']}]│[/] "
                            f"[{c['accent']}]►[/] [{c['muted']}]{line:<{content_width}}[/] "
                            f"[dim {c['section_border']}]│[/]  [bold {c['border']}]║[/]"
                        )

                # If less than 5 lines, pad with empty lines
                for _ in range(5 - len(preview_lines)):
                    yield Static(
                        f"[bold {c['border']}]║[/]  [dim {c['section_border']}]│[/]   "
                        f"{' ' * content_width} [dim {c['section_border']}]│[/]  "
                        f"[bold {c['border']}]║[/]"
                    )

                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['section_border']}]"
                    f"└{'─' * (section_inner - 1)}┘[/]  [bold {c['border']}]║[/]"
                )

                # Spacer
                yield Static(
                    f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]"
                )

                # Footer divider
                yield Static(f"[bold {c['border']}]╠{'═' * inner}╣[/]")

                # Footer row
                footer_left = (
                    f"  [dim {c['section_border']}]ID:[/] "
                    f"[{c['muted']}]{self.recovery.id[:8]}[/]"
                )
                footer_right = (
                    f"[dim {c['section_border']}]CREATED:[/] [{c['muted']}]{created}[/]"
                )
                footer_pad = inner - 32 - len(created)
                yield Static(
                    f"[bold {c['border']}]║[/]{footer_left}{' ' * footer_pad}"
                    f"{footer_right}  [bold {c['border']}]║[/]"
                )

                # Bottom border
                yield Static(f"[bold {c['border']}]╚{'═' * inner}╝[/]")

            # Action Buttons
            with Horizontal(id="recovery-modal-buttons"):
                yield Button("COPY", id="copy-button")
                yield Button("CLOSE", id="close-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "close-button":
            self.dismiss(None)
        elif event.button.id == "copy-button":
            self._copy_content()

    def _copy_content(self) -> None:
        """Copy content to clipboard."""
        if copy_to_clipboard(self.recovery.content, auto_clear=False):
            self.notify("Recovery codes copied to clipboard", title="Copied")
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)

    def action_copy_content(self) -> None:
        """Copy content via keybinding."""
        self._copy_content()


class AddRecoveryModal(ModalScreen[RecoveryEntry | None]):
    """Modal for adding new recovery codes with TextArea support."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Create the modal layout with TextArea."""
        with Vertical(id="recovery-edit-modal"):
            # Header
            yield Static(
                "[bold #f43f5e]╔══ FAIL-SAFE // NEW ENTRY ══╗[/]",
                id="recovery-edit-title",
            )

            # Form
            with Vertical(id="recovery-form"):
                # Title input
                yield Label("[#f43f5e]PROTOCOL_NAME[/]", classes="recovery-input-label")
                yield Input(placeholder="e.g. GitHub 2FA Backup", id="title-input")

                # Content TextArea
                yield Label(
                    "[#f43f5e]RECOVERY_CODES[/]  [dim #64748b]paste or import[/]",
                    classes="recovery-input-label",
                )
                yield TextArea(
                    "",
                    id="content-area",
                    classes="recovery-code-editor",
                )

            # All buttons on one line
            with Horizontal(id="modal-buttons"):
                yield Button(
                    "IMPORT", id="import-button", classes="recovery-import-btn"
                )
                yield Button("ABORT", id="cancel-button")
                yield Button("SAVE", id="save-button", classes="recovery-save-btn")

    def on_mount(self) -> None:
        """Focus first input."""
        self.query_one("#title-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            self._save()
        elif event.button.id == "import-button":
            self._show_import_prompt()

    def _show_import_prompt(self) -> None:
        """Show a prompt to import from file path."""
        self.app.push_screen(ImportRecoveryPathModal(), self._handle_import)

    def _handle_import(self, file_path: str | None) -> None:
        """Handle imported file path."""
        if not file_path:
            return

        path = Path(file_path).expanduser()
        if not path.exists():
            self.notify(f"File not found: {file_path}", severity="error")
            return

        if not path.is_file():
            self.notify(f"Not a file: {file_path}", severity="error")
            return

        try:
            content = path.read_text(encoding="utf-8")
            text_area = self.query_one("#content-area", TextArea)
            text_area.load_text(content)

            self.notify(
                f"Imported {len(content)} chars from {path.name}", title="Imported"
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.notify(f"Failed to read file: {e}", severity="error")

    def _save(self) -> None:
        """Save the recovery entry."""
        title = self.query_one("#title-input", Input).value.strip()
        content = self.query_one("#content-area", TextArea).text

        if not title:
            self.notify("Title is required", severity="error")
            return

        recovery = RecoveryEntry(
            title=title,
            content=content,
        )
        self.dismiss(recovery)

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class EditRecoveryModal(ModalScreen[dict | None]):
    """Modal for editing existing recovery codes."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, recovery: RecoveryEntry) -> None:
        super().__init__()
        self.recovery = recovery

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="recovery-edit-modal"):
            # Header
            yield Static(
                f"[bold #f43f5e]╔══ MODIFY_PROTOCOL // {self.recovery.title.upper()[:20]} ══╗[/]",
                id="recovery-edit-title",
            )

            # Form
            with Vertical(id="recovery-form"):
                yield Label("[#f43f5e]PROTOCOL_NAME[/]", classes="recovery-input-label")
                yield Input(
                    value=self.recovery.title,
                    placeholder="e.g. GitHub 2FA Backup",
                    id="title-input",
                )

                yield Label(
                    "[#f43f5e]RECOVERY_CODES[/]  [dim #64748b]paste or import[/]",
                    classes="recovery-input-label",
                )
                yield TextArea(
                    self.recovery.content,
                    id="content-area",
                    classes="recovery-code-editor",
                )

            # All buttons on one line
            with Horizontal(id="modal-buttons"):
                yield Button(
                    "IMPORT", id="import-button", classes="recovery-import-btn"
                )
                yield Button("ABORT", id="cancel-button")
                yield Button("SAVE", id="save-button", classes="recovery-save-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            self._save()
        elif event.button.id == "import-button":
            self._show_import_prompt()

    def _show_import_prompt(self) -> None:
        """Show a prompt to import from file path."""
        self.app.push_screen(ImportRecoveryPathModal(), self._handle_import)

    def _handle_import(self, file_path: str | None) -> None:
        """Handle imported file path."""
        if not file_path:
            return

        path = Path(file_path).expanduser()
        if not path.exists():
            self.notify(f"File not found: {file_path}", severity="error")
            return

        if not path.is_file():
            self.notify(f"Not a file: {file_path}", severity="error")
            return

        try:
            content = path.read_text(encoding="utf-8")
            text_area = self.query_one("#content-area", TextArea)
            text_area.load_text(content)
            self.notify(
                f"Imported {len(content)} chars from {path.name}", title="Imported"
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.notify(f"Failed to read file: {e}", severity="error")

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


class ImportRecoveryPathModal(ModalScreen[str | None]):
    """Modal for entering a file path to import."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Create the path input modal."""
        with Vertical(id="recovery-import-modal"):
            yield Static(
                "[bold #f43f5e]╔══ IMPORT FROM PATH ══╗[/]",
                id="recovery-import-title",
            )
            yield Label("[#f43f5e]FILE_PATH[/]", classes="recovery-input-label")
            yield Input(placeholder="/path/to/recovery_codes.txt", id="path-input")
            yield Static(
                "[dim #64748b]Enter absolute path to recovery codes file[/]",
                id="recovery-import-hint",
            )
            with Horizontal(id="modal-buttons"):
                yield Button("[ESC] ABORT", id="cancel-button")
                yield Button(
                    "[ENTER] IMPORT", id="do-import-button", classes="recovery-save-btn"
                )

    def on_mount(self) -> None:
        """Focus input."""
        self.query_one("#path-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "do-import-button":
            self._import()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        """Handle enter key in input."""
        self._import()

    def _import(self) -> None:
        """Import the file path."""
        path = self.query_one("#path-input", Input).value.strip()
        if path:
            self.dismiss(path)
        else:
            self.notify("Please enter a file path", severity="warning")

    def action_cancel(self) -> None:
        """Cancel."""
        self.dismiss(None)


class ConfirmDeleteRecoveryModal(ModalScreen[bool]):
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
        with Vertical(id="recovery-delete-modal"):
            yield Static(
                "[bold #f43f5e]╔══ CONFIRM_DELETE // WARNING ══╗[/]",
                id="recovery-delete-title",
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
                    "[Y] CONFIRM DELETE",
                    id="delete-button",
                    classes="recovery-delete-btn",
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
# MAIN RECOVERY SCREEN
# ═══════════════════════════════════════════════════════════════════════════════


class RecoveryScreen(Screen):
    """Screen for managing recovery codes - emergency 2FA backup."""

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
        """Create the recovery screen layout."""
        # 1. Global Header with Breadcrumbs
        with Horizontal(id="app-header"):
            yield Static(
                "[dim #64748b]HOME[/] [#475569]>[/] [dim #64748b]VAULT[/] "
                "[#475569]>[/] [bold #f43f5e]RECOVERY[/]",
                id="header-branding",
            )
            yield Static("░░ FAIL-SAFE PROTOCOL ░░", id="header-status")
            yield Static("", id="header-lock")

        # 2. Body (Master-Detail Split)
        with Horizontal(id="vault-body"):
            # Left Pane: Data Grid (Master) - 65%
            with Vertical(id="vault-grid-pane"):
                yield Static(" ≡ EMERGENCY_DATABASE ", classes="pane-header-block-rose")
                yield DataTable(id="recovery-table", cursor_type="row")
                # Empty state
                with Center(id="empty-state"):
                    yield Static(
                        "[dim #475569]╔══════════════════════════════════════╗\n"
                        "║                                      ║\n"
                        "║      NO RECOVERY CODES FOUND         ║\n"
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
                yield Static(
                    " ≡ FAIL-SAFE_INSPECTOR ", classes="pane-header-block-rose"
                )
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
            header_lock.update("[#fda4af]● [bold]EMERGENCY[/][/]")
        else:
            header_lock.update("[#e11d48]○ [bold]EMERGENCY[/][/]")

    def _initialize_selection(self) -> None:
        """Initialize table selection and inspector."""
        table = self.query_one("#recovery-table", DataTable)
        table.focus()
        if table.row_count > 0:
            table.move_cursor(row=0)
            app: PassFXApp = self.app  # type: ignore
            entries = app.vault.get_recovery_entries()
            if entries:
                self._selected_row_key = entries[0].id
                self._update_inspector(entries[0].id)
        else:
            self._update_inspector(None)

    # pylint: disable=too-many-locals
    def _refresh_table(self) -> None:
        """Refresh the data table."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#recovery-table", DataTable)
        empty_state = self.query_one("#empty-state", Center)

        table.clear(columns=True)

        table.add_column("", width=3)
        table.add_column("Title", width=32)
        table.add_column("Codes", width=8)
        table.add_column("Updated", width=12)
        table.add_column("Notes", width=65)  # Wider to fill remaining space

        entries = app.vault.get_recovery_entries()

        if len(entries) == 0:
            table.display = False
            empty_state.display = True
        else:
            table.display = True
            empty_state.display = False

        for entry in entries:
            is_selected = entry.id == self._selected_row_key
            indicator = "[bold #f43f5e]▍[/]" if is_selected else " "
            title_text = entry.title[:26] if len(entry.title) > 26 else entry.title
            codes_text = f"[#f43f5e]{entry.code_count}[/]"
            updated = _get_relative_time(entry.updated_at)
            updated_text = f"[dim]{updated}[/]"
            notes_preview = ""
            if entry.notes:
                notes_preview = entry.notes[:50] + (
                    "..." if len(entry.notes) > 50 else ""
                )
                notes_text = f"[dim]{notes_preview}[/]"
            else:
                notes_text = "[dim #555555]-[/]"

            table.add_row(
                indicator,
                title_text,
                codes_text,
                updated_text,
                notes_text,
                key=entry.id,
            )

        footer = self.query_one("#grid-footer", Static)
        count = len(entries)
        footer.update(f" └── [{count}] FAIL-SAFES LOADED")

    def _update_row_indicators(self, old_key: str | None, new_key: str | None) -> None:
        """Update indicator column for selection change."""
        table = self.query_one("#recovery-table", DataTable)
        app: PassFXApp = self.app  # type: ignore
        entries = app.vault.get_recovery_entries()
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
                table.update_cell(new_key, indicator_col, "[bold #f43f5e]▍[/]")
            except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
                pass  # Row may not exist during rapid navigation

    def _get_selected_entry(self) -> RecoveryEntry | None:
        """Get the currently selected recovery entry."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#recovery-table", DataTable)

        if table.cursor_row is None:
            return None

        entries = app.vault.get_recovery_entries()
        if 0 <= table.cursor_row < len(entries):
            return entries[table.cursor_row]
        return None

    def action_add(self) -> None:
        """Add a new recovery entry."""

        def handle_result(recovery: RecoveryEntry | None) -> None:
            if recovery:
                app: PassFXApp = self.app  # type: ignore
                app.vault.add_recovery(recovery)
                self._refresh_table()
                self.notify(f"Added '{recovery.title}'", title="Success")

        self.app.push_screen(AddRecoveryModal(), handle_result)

    def action_copy(self) -> None:
        """Copy content to clipboard."""
        entry = self._get_selected_entry()
        if not entry:
            self.notify("No recovery codes selected", severity="warning")
            return

        if copy_to_clipboard(entry.content, auto_clear=False):
            self.notify("Recovery codes copied to clipboard", title=entry.title)
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_edit(self) -> None:
        """Edit selected recovery entry."""
        entry = self._get_selected_entry()
        if not entry:
            self.notify("No recovery codes selected", severity="warning")
            return

        def handle_result(changes: dict | None) -> None:
            if changes:
                app: PassFXApp = self.app  # type: ignore
                app.vault.update_recovery(entry.id, **changes)
                self._refresh_table()
                self.notify("Recovery codes updated", title="Success")

        self.app.push_screen(EditRecoveryModal(entry), handle_result)

    def action_delete(self) -> None:
        """Delete selected recovery entry."""
        entry = self._get_selected_entry()
        if not entry:
            self.notify("No recovery codes selected", severity="warning")
            return

        def handle_result(confirmed: bool | None) -> None:
            if confirmed:
                app: PassFXApp = self.app  # type: ignore
                app.vault.delete_recovery(entry.id)
                self._refresh_table()
                self.notify(f"Deleted '{entry.title}'", title="Deleted")

        self.app.push_screen(ConfirmDeleteRecoveryModal(entry.title), handle_result)

    def action_view(self) -> None:
        """View recovery entry details."""
        entry = self._get_selected_entry()
        if not entry:
            self.notify("No recovery codes selected", severity="warning")
            return

        self.app.push_screen(ViewRecoveryModal(entry))

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update inspector when row is highlighted."""
        key_value = (
            event.row_key.value
            if hasattr(event.row_key, "value")
            else str(event.row_key)
        )
        old_key = self._selected_row_key
        self._selected_row_key = key_value
        self._update_inspector(key_value)
        self._update_row_indicators(old_key, key_value)

    # pylint: disable=too-many-locals
    def _update_inspector(self, row_key: Any) -> None:
        """Update the inspector panel with recovery details."""
        inspector = self.query_one("#inspector-content", Vertical)
        inspector.remove_children()

        app: PassFXApp = self.app  # type: ignore
        entries = app.vault.get_recovery_entries()

        entry = None
        for e in entries:
            if e.id == str(row_key):
                entry = e
                break

        if not entry:
            inspector.mount(
                Static(
                    "[dim #555555]╔══════════════════════════╗\n"
                    "║    SELECT A FAIL-SAFE    ║\n"
                    "║    TO VIEW DETAILS       ║\n"
                    "╚══════════════════════════╝[/]",
                    classes="inspector-empty",
                )
            )
            return

        # Section 1: Recovery ID Card
        inspector.mount(
            Vertical(
                Horizontal(
                    Vertical(
                        Static(
                            "[on #f43f5e][bold #000000] SOS [/][/]",
                            classes="avatar-char",
                        ),
                        Static("[on #f43f5e]     [/]", classes="avatar-char"),
                        classes="avatar-box",
                    ),
                    Vertical(
                        Static(
                            f"[bold #f8fafc]{entry.title}[/]", classes="id-label-text"
                        ),
                        Static(
                            "[dim #94a3b8]Emergency Backup Codes[/]",
                            classes="id-email-text",
                        ),
                        classes="id-details-stack",
                    ),
                    classes="id-card-header",
                ),
                classes="id-card-wrapper recovery-card",
            )
        )

        # Section 2: Stats Widget
        inspector.mount(
            Vertical(
                Static("[dim #6b7280]▸ FAIL-SAFE STATS[/]", classes="section-label"),
                Static(
                    f"[#f43f5e]LINES:[/] {entry.line_count}    "
                    f"[#f43f5e]CODES:[/] {entry.code_count}",
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
                if line.strip() and not line.strip().startswith("#"):
                    # Mask part of the code for security
                    if len(line_preview) > 8:
                        masked = (
                            line_preview[:4]
                            + "•" * (len(line_preview) - 8)
                            + line_preview[-4:]
                        )
                        preview_lines.append(
                            f"[dim #475569]{i:2}[/] │ [#f43f5e]{masked}[/]"
                        )
                    else:
                        preview_lines.append(
                            f"[dim #475569]{i:2}[/] │ [#f43f5e]{line_preview}[/]"
                        )
                else:
                    preview_lines.append(
                        f"[dim #475569]{i:2}[/] │ [dim #64748b]{line_preview}[/]"
                    )
            if len(entry.content.split("\n")) > 8:
                preview_lines.append(
                    "[dim #475569]   [/]   [dim #64748b]... more codes[/]"
                )
        else:
            preview_lines.append("[dim #64748b] 1[/] │ [dim #555555]// EMPTY[/]")

        preview_content = "\n".join(preview_lines)
        notes_terminal = Vertical(
            Static(preview_content, classes="notes-code"),
            classes="notes-editor recovery-preview",
        )
        notes_terminal.border_title = "CODE_PREVIEW"

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
                    f"[dim #475569]ID:[/] [#64748b]{entry.id[:8]}[/]", classes="meta-id"
                ),
                Static(
                    f"[dim #475569]UPDATED:[/] [#64748b]{updated_full}[/]",
                    classes="meta-updated",
                ),
                classes="inspector-footer-bar",
            )
        )
