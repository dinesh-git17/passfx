"""Environment Variables Screen for PassFX - Config Vault."""

# pylint: disable=duplicate-code,too-many-lines

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Input, Label, Static, TextArea

from passfx.core.models import EnvEntry
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


class ViewEnvModal(ModalScreen[None]):
    """Modal displaying environment config visualization matching password modal style."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "copy_content", "Copy"),
    ]

    # Color configuration for the env modal (Indigo theme)
    COLORS = {
        "border": "#6366f1",
        "card_bg": "#0a0e27",
        "section_border": "#475569",
        "title_bg": "#818cf8",
        "title_fg": "#000000",
        "label_dim": "#64748b",
        "value_fg": "#f8fafc",
        "accent": "#a5b4fc",
        "muted": "#94a3b8",
    }

    def __init__(self, env: EnvEntry) -> None:
        super().__init__()
        self.env = env

    # pylint: disable=too-many-locals,too-many-statements
    def compose(self) -> ComposeResult:
        """Create the config visualization layout."""
        c = self.COLORS

        # Format timestamp
        try:
            created = datetime.fromisoformat(self.env.created_at).strftime("%Y.%m.%d")
        except (ValueError, TypeError):
            created = "UNKNOWN"

        # Card dimensions (matching password modal)
        width = 96
        inner = width - 2
        section_inner = width - 6
        content_width = section_inner - 5

        # Truncate title if needed
        title_display = (
            self.env.title[:content_width]
            if len(self.env.title) > content_width
            else self.env.title
        )

        # Get content preview (first 5 lines for env files)
        content_lines = self.env.content.split("\n")[:5] if self.env.content else []
        preview_lines = []
        for line in content_lines:
            # Mask values in env files (show key=***)
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=", 1)[0]
                preview = f"{key}=***"
            else:
                preview = line
            preview = (
                preview[:content_width] if len(preview) > content_width else preview
            )
            preview_lines.append(preview)

        with Vertical(id="env-modal"):
            with Vertical(id="physical-env-card"):
                # Top border
                yield Static(f"[bold {c['border']}]╔{'═' * inner}╗[/]")

                # Title row
                title = " CONFIG INJECTOR "
                title_pad = inner - len(title) - 2
                yield Static(
                    f"[bold {c['border']}]║[/]  [on {c['title_bg']}]"
                    f"[bold {c['title_fg']}]{title}[/]{' ' * title_pad}"
                    f"[bold {c['border']}]║[/]"
                )

                # Divider
                yield Static(f"[bold {c['border']}]╠{'═' * inner}╣[/]")

                # Config label
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['label_dim']}]CONFIG:[/] "
                    f"[bold {c['value_fg']}]{title_display:<{inner - 12}}[/] "
                    f"[bold {c['border']}]║[/]"
                )

                # Filename row
                filename_display = (
                    self.env.filename[:content_width]
                    if len(self.env.filename) > content_width
                    else self.env.filename
                )
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['label_dim']}]FILE:[/]   "
                    f"[{c['accent']}]{filename_display:<{inner - 12}}[/] "
                    f"[bold {c['border']}]║[/]"
                )

                # Spacer
                yield Static(
                    f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]"
                )

                # Stats section
                stats = (
                    f"[{c['accent']}]{self.env.line_count}[/] lines  "
                    f"[{c['accent']}]{self.env.var_count}[/] vars"
                )
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['label_dim']}]STATS:[/]  "
                    f"{stats:<{inner - 12}}[bold {c['border']}]║[/]"
                )

                # Spacer
                yield Static(
                    f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]"
                )

                # Content section
                yield Static(
                    f"[bold {c['border']}]║[/]  [dim {c['section_border']}]"
                    f"┌─ CONTENT PREVIEW {'─' * (section_inner - 20)}┐[/]  "
                    f"[bold {c['border']}]║[/]"
                )

                # Show preview lines (masked values)
                for line in preview_lines:
                    if "=" in line and not line.strip().startswith("#"):
                        # Highlight env var keys
                        key = line.split("=", 1)[0]
                        yield Static(
                            f"[bold {c['border']}]║[/]  [dim {c['section_border']}]│[/] "
                            f"[{c['accent']}]►[/] [{c['accent']}]{key}[/][{c['muted']}]=***"
                            f"{' ' * (content_width - len(key) - 4)}[/] "
                            f"[dim {c['section_border']}]│[/]  [bold {c['border']}]║[/]"
                        )
                    else:
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
                    f"[{c['muted']}]{self.env.id[:8]}[/]"
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
            with Horizontal(id="env-modal-buttons"):
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
        if copy_to_clipboard(self.env.content, auto_clear=True):
            self.notify("Config copied! Clears in 15s", title="Copied")
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)

    def action_copy_content(self) -> None:
        """Copy content via keybinding."""
        self._copy_content()


class AddEnvModal(ModalScreen[EnvEntry | None]):
    """Modal for adding a new environment config with TextArea support."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Create the modal layout with TextArea."""
        with Vertical(id="env-edit-modal"):
            # Header
            yield Static(
                "[bold #f59e0b]╔══ SYSTEM_CONFIG // NEW ENTRY ══╗[/]",
                id="env-edit-title",
            )

            # Form
            with Vertical(id="env-form"):
                # Title input
                yield Label("[#f59e0b]CONFIG_TITLE[/]", classes="env-input-label")
                yield Input(placeholder="e.g. Project X Production", id="title-input")

                # Filename input
                yield Label("[#f59e0b]FILENAME[/]", classes="env-input-label")
                yield Input(placeholder="e.g. .env.production", id="filename-input")

                # Content TextArea
                yield Label(
                    "[#f59e0b]CONTENT[/]  [dim #64748b]paste or drop file[/]",
                    classes="env-input-label",
                )
                yield TextArea(
                    "",
                    id="content-area",
                    language="dotenv",
                    classes="code-editor",
                )

            # All buttons on one line
            with Horizontal(id="modal-buttons"):
                yield Button("IMPORT", id="import-button", classes="import-btn")
                yield Button("ABORT", id="cancel-button")
                yield Button("SAVE", id="save-button", classes="env-save-btn")

    def on_mount(self) -> None:
        """Focus first input."""
        self.query_one("#title-input", Input).focus()

    def on_drop(self, event: Any) -> None:
        """Handle file drop events."""
        if hasattr(event, "paths") and event.paths:
            # Get the first dropped file
            file_path = event.paths[0]
            self._handle_import(str(file_path))

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
        self.app.push_screen(ImportPathModal(), self._handle_import)

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

            # Auto-fill filename if empty
            filename_input = self.query_one("#filename-input", Input)
            if not filename_input.value:
                filename_input.value = path.name

            self.notify(
                f"Imported {len(content)} chars from {path.name}",
                title="Imported",
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.notify(f"Failed to read file: {e}", severity="error")

    def _save(self) -> None:
        """Save the environment entry."""
        title = self.query_one("#title-input", Input).value.strip()
        filename = self.query_one("#filename-input", Input).value.strip()
        content = self.query_one("#content-area", TextArea).text

        if not title:
            self.notify("Title is required", severity="error")
            return

        if not filename:
            self.notify("Filename is required", severity="error")
            return

        env = EnvEntry(
            title=title,
            filename=filename,
            content=content,
        )
        self.dismiss(env)

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class EditEnvModal(ModalScreen[dict | None]):
    """Modal for editing an existing environment config."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, env: EnvEntry) -> None:
        super().__init__()
        self.env = env

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="env-edit-modal"):
            # Header
            yield Static(
                f"[bold #f59e0b]╔══ MODIFY_CONFIG // {self.env.title.upper()[:20]} ══╗[/]",
                id="env-edit-title",
            )

            # Form
            with Vertical(id="env-form"):
                yield Label("[#f59e0b]CONFIG_TITLE[/]", classes="env-input-label")
                yield Input(
                    value=self.env.title,
                    placeholder="e.g. Project X Production",
                    id="title-input",
                )

                yield Label("[#f59e0b]FILENAME[/]", classes="env-input-label")
                yield Input(
                    value=self.env.filename,
                    placeholder="e.g. .env.production",
                    id="filename-input",
                )

                yield Label(
                    "[#f59e0b]CONTENT[/]  [dim #64748b]paste or drop file[/]",
                    classes="env-input-label",
                )
                yield TextArea(
                    self.env.content,
                    id="content-area",
                    language="dotenv",
                    classes="code-editor",
                )

            # All buttons on one line
            with Horizontal(id="modal-buttons"):
                yield Button("IMPORT", id="import-button", classes="import-btn")
                yield Button("ABORT", id="cancel-button")
                yield Button("SAVE", id="save-button", classes="env-save-btn")

    def on_drop(self, event: Any) -> None:
        """Handle file drop events."""
        if hasattr(event, "paths") and event.paths:
            file_path = event.paths[0]
            self._handle_import(str(file_path))

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
        self.app.push_screen(ImportPathModal(), self._handle_import)

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
                f"Imported {len(content)} chars from {path.name}",
                title="Imported",
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.notify(f"Failed to read file: {e}", severity="error")

    def _save(self) -> None:
        """Save the changes."""
        title = self.query_one("#title-input", Input).value.strip()
        filename = self.query_one("#filename-input", Input).value.strip()
        content = self.query_one("#content-area", TextArea).text

        if not title:
            self.notify("Title is required", severity="error")
            return

        if not filename:
            self.notify("Filename is required", severity="error")
            return

        result = {
            "title": title,
            "filename": filename,
            "content": content,
        }
        self.dismiss(result)

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class ImportPathModal(ModalScreen[str | None]):
    """Modal for entering a file path to import."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Create the path input modal."""
        with Vertical(id="import-modal"):
            yield Static(
                "[bold #f59e0b]╔══ IMPORT FROM PATH ══╗[/]",
                id="import-title",
            )
            yield Label("[#f59e0b]FILE_PATH[/]", classes="env-input-label")
            yield Input(placeholder="/path/to/.env", id="path-input")
            yield Static(
                "[dim #64748b]Enter absolute path to .env file[/]",
                id="import-hint",
            )
            with Horizontal(id="modal-buttons"):
                yield Button("[ESC] ABORT", id="cancel-button")
                yield Button(
                    "[ENTER] IMPORT", id="do-import-button", classes="env-save-btn"
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


class ConfirmDeleteEnvModal(ModalScreen[bool]):
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
        with Vertical(id="env-delete-modal"):
            yield Static(
                "[bold #f59e0b]╔══ CONFIRM_DELETE // WARNING ══╗[/]",
                id="delete-title",
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
                    "[Y] CONFIRM DELETE", id="delete-button", classes="env-delete-btn"
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
# MAIN ENVS SCREEN
# ═══════════════════════════════════════════════════════════════════════════════


class EnvsScreen(Screen):
    """Screen for managing environment variable configs."""

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
        """Create the envs screen layout."""
        # 1. Global Header with Breadcrumbs
        with Horizontal(id="app-header"):
            yield Static(
                "[dim #64748b]HOME[/] [#475569]>[/] [dim #64748b]VAULT[/] "
                "[#475569]>[/] [bold #6366f1]ENV VARS[/]",
                id="header-branding",
            )
            yield Static("░░ CONFIG INJECTOR ░░", id="header-status")
            yield Static("", id="header-lock")

        # 2. Body (Master-Detail Split)
        with Horizontal(id="vault-body"):
            # Left Pane: Data Grid (Master) - 65%
            with Vertical(id="vault-grid-pane"):
                yield Static(" ≡ CONFIG_DATABASE ", classes="pane-header-block-indigo")
                yield DataTable(id="envs-table", cursor_type="row")
                # Empty state
                with Center(id="empty-state"):
                    yield Static(
                        "[dim #475569]╔══════════════════════════════════════╗\n"
                        "║                                      ║\n"
                        "║      NO CONFIGS FOUND                ║\n"
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
                yield Static(" ≡ CONFIG_INSPECTOR ", classes="pane-header-block-indigo")
                yield Vertical(id="inspector-content")

        # 3. Global Footer
        with Horizontal(id="app-footer"):
            yield Static(" VAULT ", id="footer-version")
            yield Static(
                " \\[A] Add  \\[C] Copy  \\[E] Edit  \\[D] Delete  "
                "\\[V] View  \\[ESC] Back",
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
            header_lock.update("[#a5b4fc]● [bold]INJECTOR[/][/]")
        else:
            header_lock.update("[#4f46e5]○ [bold]INJECTOR[/][/]")

    def _initialize_selection(self) -> None:
        """Initialize table selection and inspector."""
        table = self.query_one("#envs-table", DataTable)
        table.focus()
        if table.row_count > 0:
            table.move_cursor(row=0)
            app: PassFXApp = self.app  # type: ignore
            envs = app.vault.get_envs()
            if envs:
                self._selected_row_key = envs[0].id
                self._update_inspector(envs[0].id)
        else:
            self._update_inspector(None)

    # pylint: disable=too-many-locals
    def _refresh_table(self) -> None:
        """Refresh the data table."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#envs-table", DataTable)
        empty_state = self.query_one("#empty-state", Center)

        table.clear(columns=True)

        table.add_column("", width=3)
        table.add_column("Title", width=25)
        table.add_column("Filename", width=22)
        table.add_column("Vars", width=8)
        table.add_column("Updated", width=12)
        table.add_column("Notes", width=55)  # Wider to fill remaining space

        envs = app.vault.get_envs()

        if len(envs) == 0:
            table.display = False
            empty_state.display = True
        else:
            table.display = True
            empty_state.display = False

        for env in envs:
            is_selected = env.id == self._selected_row_key
            indicator = "[bold #6366f1]▍[/]" if is_selected else " "
            title_text = env.title[:20] if len(env.title) > 20 else env.title
            filename_text = f"[#94a3b8]{env.filename}[/]"
            vars_text = f"[#f59e0b]{env.var_count}[/]"
            updated = _get_relative_time(env.updated_at)
            updated_text = f"[dim]{updated}[/]"
            # Truncate notes to first 50 characters
            notes_preview = env.notes[:50] if env.notes else ""
            if env.notes and len(env.notes) > 50:
                notes_preview = notes_preview + "..."
            notes_text = f"[dim #64748b]{notes_preview}[/]"

            table.add_row(
                indicator,
                title_text,
                filename_text,
                vars_text,
                updated_text,
                notes_text,
                key=env.id,
            )

        footer = self.query_one("#grid-footer", Static)
        count = len(envs)
        footer.update(f" └── [{count}] CONFIGS LOADED")

    def _update_row_indicators(self, old_key: str | None, new_key: str | None) -> None:
        """Update indicator column for selection change."""
        table = self.query_one("#envs-table", DataTable)
        app: PassFXApp = self.app  # type: ignore
        envs = app.vault.get_envs()
        env_map = {e.id: e for e in envs}

        if not table.columns:
            return
        indicator_col = list(table.columns.keys())[0]

        if old_key and old_key in env_map:
            try:
                table.update_cell(old_key, indicator_col, " ")
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        if new_key and new_key in env_map:
            try:
                table.update_cell(new_key, indicator_col, "[bold #6366f1]▍[/]")
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    def _get_selected_env(self) -> EnvEntry | None:
        """Get the currently selected env entry."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#envs-table", DataTable)

        if table.cursor_row is None:
            return None

        envs = app.vault.get_envs()
        if 0 <= table.cursor_row < len(envs):
            return envs[table.cursor_row]
        return None

    def action_add(self) -> None:
        """Add a new env entry."""

        def handle_result(env: EnvEntry | None) -> None:
            if env:
                app: PassFXApp = self.app  # type: ignore
                app.vault.add_env(env)
                self._refresh_table()
                self.notify(f"Added '{env.title}'", title="Success")

        self.app.push_screen(AddEnvModal(), handle_result)

    def action_copy(self) -> None:
        """Copy content to clipboard with auto-clear for security."""
        env = self._get_selected_env()
        if not env:
            self.notify("No config selected", severity="warning")
            return

        if copy_to_clipboard(env.content, auto_clear=True):
            self.notify("Config copied! Clears in 15s", title=env.title)
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_edit(self) -> None:
        """Edit selected env entry."""
        env = self._get_selected_env()
        if not env:
            self.notify("No config selected", severity="warning")
            return

        def handle_result(changes: dict | None) -> None:
            if changes:
                app: PassFXApp = self.app  # type: ignore
                app.vault.update_env(env.id, **changes)
                self._refresh_table()
                self.notify("Config updated", title="Success")

        self.app.push_screen(EditEnvModal(env), handle_result)

    def action_delete(self) -> None:
        """Delete selected env entry."""
        env = self._get_selected_env()
        if not env:
            self.notify("No config selected", severity="warning")
            return

        def handle_result(confirmed: bool | None) -> None:
            if confirmed:
                app: PassFXApp = self.app  # type: ignore
                app.vault.delete_env(env.id)
                self._refresh_table()
                self.notify(f"Deleted '{env.title}'", title="Deleted")

        self.app.push_screen(ConfirmDeleteEnvModal(env.title), handle_result)

    def action_view(self) -> None:
        """View env entry details."""
        env = self._get_selected_env()
        if not env:
            self.notify("No config selected", severity="warning")
            return

        self.app.push_screen(ViewEnvModal(env))

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
        """Update the inspector panel with env details."""
        inspector = self.query_one("#inspector-content", Vertical)
        inspector.remove_children()

        app: PassFXApp = self.app  # type: ignore
        envs = app.vault.get_envs()

        env = None
        for e in envs:
            if e.id == str(row_key):
                env = e
                break

        if not env:
            inspector.mount(
                Static(
                    "[dim #555555]╔══════════════════════════╗\n"
                    "║    SELECT A CONFIG       ║\n"
                    "║    TO VIEW DETAILS       ║\n"
                    "╚══════════════════════════╝[/]",
                    classes="inspector-empty",
                )
            )
            return

        # Section 1: Config ID Card
        inspector.mount(
            Vertical(
                Horizontal(
                    Vertical(
                        Static(
                            "[on #f59e0b][bold #000000] ENV [/][/]",
                            classes="avatar-char",
                        ),
                        Static("[on #f59e0b]     [/]", classes="avatar-char"),
                        classes="avatar-box",
                    ),
                    Vertical(
                        Static(
                            f"[bold #f8fafc]{env.title}[/]", classes="id-label-text"
                        ),
                        Static(
                            f"[dim #94a3b8]{env.filename}[/]", classes="id-email-text"
                        ),
                        classes="id-details-stack",
                    ),
                    classes="id-card-header",
                ),
                classes="id-card-wrapper env-card",
            )
        )

        # Section 2: Stats Widget
        inspector.mount(
            Vertical(
                Static("[dim #6b7280]▸ CONFIG STATS[/]", classes="section-label"),
                Static(
                    f"[#f59e0b]LINES:[/] {env.line_count}    [#f59e0b]VARS:[/] {env.var_count}",
                    classes="strength-bar-widget",
                ),
                classes="security-widget",
            )
        )

        # Section 3: Content Preview
        preview_lines = []
        if env.content:
            lines = env.content.split("\n")[:8]
            for i, line in enumerate(lines, 1):
                line_preview = line[:35] if len(line) > 35 else line
                if "=" in line and not line.strip().startswith("#"):
                    parts = line_preview.split("=", 1)
                    preview_lines.append(
                        f"[dim #475569]{i:2}[/] │ [#f59e0b]{parts[0]}[/]=[dim]...[/]"
                    )
                else:
                    preview_lines.append(
                        f"[dim #475569]{i:2}[/] │ [dim #64748b]{line_preview}[/]"
                    )
            if len(env.content.split("\n")) > 8:
                preview_lines.append(
                    "[dim #475569]   [/]   [dim #64748b]... more lines[/]"
                )
        else:
            preview_lines.append("[dim #64748b] 1[/] │ [dim #555555]// EMPTY[/]")

        preview_content = "\n".join(preview_lines)
        notes_terminal = Vertical(
            Static(preview_content, classes="notes-code"),
            classes="notes-editor env-preview",
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
            updated_full = datetime.fromisoformat(env.updated_at).strftime(
                "%Y-%m-%d %H:%M"
            )
        except (ValueError, TypeError):
            updated_full = env.updated_at or "Unknown"

        inspector.mount(
            Horizontal(
                Static(
                    f"[dim #475569]ID:[/] [#64748b]{env.id[:8]}[/]",
                    classes="meta-id",
                ),
                Static(
                    f"[dim #475569]UPDATED:[/] [#64748b]{updated_full}[/]",
                    classes="meta-updated",
                ),
                classes="inspector-footer-bar",
            )
        )
