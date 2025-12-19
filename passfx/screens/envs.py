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
    """Modal for viewing env config - Operator Grade Secure Read Console."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "copy_content", "Copy"),
    ]

    def __init__(self, env: EnvEntry) -> None:
        super().__init__()
        self.env = env

    def compose(self) -> ComposeResult:
        """Create the Operator-grade view modal layout.

        This is the explicit reveal action - user has pressed V to view content.
        Full content is displayed securely in a TextArea (read-only).
        """
        with Vertical(id="pwd-modal", classes="secure-terminal env-modal-wide"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static("[ :: SECURE READ PROTOCOL :: ]", id="modal-title")
                    yield Static("STATUS: DECRYPTED", classes="modal-status")

            # Data Display Body - matches EditEnvModal structure
            with Vertical(id="pwd-form"):
                # Row 1: Title and Filename side-by-side
                with Horizontal(classes="input-row"):
                    with Vertical(classes="input-col"):
                        yield Label("> CONFIG_TITLE", classes="input-label")
                        yield Static(
                            f"  {self.env.title}",
                            classes="view-value",
                            id="title-value",
                        )
                    with Vertical(classes="input-col"):
                        yield Label("> FILE_TARGET", classes="input-label")
                        yield Static(
                            f"  [#fcd34d]{self.env.filename}[/]  "
                            f"[dim]({self.env.line_count}L {self.env.var_count}V)[/]",
                            classes="view-value",
                            id="filename-value",
                        )

                # Row 2: Full content in TextArea (read-only reveal)
                yield Label("> CONTENT [DECRYPTED]", classes="input-label")
                yield TextArea(
                    self.env.content,
                    id="content-area",
                    language="dotenv",
                    classes="note-code-editor",
                    read_only=True,
                )

            # Footer Actions
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
    """Modal for adding a new environment config - Operator Grade Secure Write Console."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Create the Operator-grade modal layout with TextArea."""
        with Vertical(id="pwd-modal", classes="secure-terminal env-modal-wide"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static("[ :: SECURE WRITE PROTOCOL :: ]", id="modal-title")
                    yield Static("STATUS: OPEN", classes="modal-status")

            # Form - landscape layout
            with Vertical(id="pwd-form"):
                # Row 1: Title and Filename side-by-side
                with Horizontal(classes="input-row"):
                    with Vertical(classes="input-col"):
                        yield Label("> CONFIG_TITLE", classes="input-label")
                        yield Input(
                            placeholder="e.g. Project X Production", id="title-input"
                        )
                    with Vertical(classes="input-col"):
                        yield Label("> FILENAME", classes="input-label")
                        yield Input(
                            placeholder="e.g. .env.production", id="filename-input"
                        )

                # Row 2: Content TextArea
                yield Label("> CONTENT", classes="input-label")
                yield TextArea(
                    "",
                    id="content-area",
                    language="dotenv",
                    classes="note-code-editor",
                )

            # Footer Actions
            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ FILE ]", id="import-button")
                yield Button(r"\[ ABORT ]", variant="default", id="cancel-button")
                yield Button(r"\[ SAVE ]", variant="primary", id="save-button")

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
    """Modal for editing an existing environment config - Operator Grade Console."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, env: EnvEntry) -> None:
        super().__init__()
        self.env = env

    def compose(self) -> ComposeResult:
        """Create the Operator-grade modal layout."""
        with Vertical(id="pwd-modal", classes="secure-terminal env-modal-wide"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static(
                        f"[ :: MODIFY // {self.env.title.upper()[:18]} :: ]",
                        id="modal-title",
                    )
                    yield Static("STATUS: EDIT", classes="modal-status")

            # Form - landscape layout
            with Vertical(id="pwd-form"):
                # Row 1: Title and Filename side-by-side
                with Horizontal(classes="input-row"):
                    with Vertical(classes="input-col"):
                        yield Label("> CONFIG_TITLE", classes="input-label")
                        yield Input(
                            value=self.env.title,
                            placeholder="e.g. Project X Production",
                            id="title-input",
                        )
                    with Vertical(classes="input-col"):
                        yield Label("> FILENAME", classes="input-label")
                        yield Input(
                            value=self.env.filename,
                            placeholder="e.g. .env.production",
                            id="filename-input",
                        )

                # Row 2: Content TextArea
                yield Label("> CONTENT", classes="input-label")
                yield TextArea(
                    self.env.content,
                    id="content-area",
                    language="dotenv",
                    classes="note-code-editor",
                )

            # Footer Actions
            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ FILE ]", id="import-button")
                yield Button(r"\[ ABORT ]", variant="default", id="cancel-button")
                yield Button(r"\[ SAVE ]", variant="primary", id="save-button")

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
        with Vertical(id="pwd-modal", classes="secure-terminal"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static("[ :: IMPORT PROTOCOL :: ]", id="modal-title")
                    yield Static("STATUS: READY", classes="modal-status")

            # Form
            with Vertical(id="pwd-form"):
                yield Label("> FILE_PATH", classes="input-label")
                yield Input(placeholder="/path/to/.env", id="path-input")
                yield Static(
                    "[dim]Enter absolute path to .env file[/]",
                    classes="view-value",
                )

            # Footer Actions
            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ ABORT ]", variant="default", id="cancel-button")
                yield Button(r"\[ IMPORT ]", variant="primary", id="do-import-button")

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

    # Operator theme color tokens - Indigo accent (system config)
    COLORS = {
        "primary": "#00FFFF",  # Cyan - active selection, titles
        "accent": "#818cf8",  # Indigo - labels, headers
        "success": "#22c55e",  # Green - high strength, decrypted
        "muted": "#666666",  # Dim grey - metadata, timestamps
        "text": "#e0e0e0",  # Light text
        "surface": "#0a0a0a",  # Dark surface
    }

    def __init__(self) -> None:
        super().__init__()
        self._selected_row_key: str | None = None
        self._pulse_state: bool = True

    # pylint: disable=too-many-locals
    def compose(self) -> ComposeResult:
        """Create the envs screen layout."""
        c = self.COLORS

        # 1. Global Header with Breadcrumbs - Operator theme
        with Horizontal(id="app-header"):
            yield Static(
                f"[bold {c['accent']}]VAULT // CONFIG_FILES[/]",
                id="header-branding",
                classes="screen-header",
            )
            with Horizontal(id="header-right"):
                yield Static("", id="header-lock")  # Will be updated with pulse

        # 2. Body (Master-Detail Split)
        with Horizontal(id="vault-body"):
            # Left Pane: Data Grid (Master) - 65%
            with Vertical(id="vault-grid-pane"):
                yield DataTable(id="envs-table", cursor_type="row")
                # Empty state placeholder (hidden by default)
                with Center(id="empty-state"):
                    yield Static(
                        f"[dim {c['muted']}]╔══════════════════════════════════════╗\n"
                        "║                                      ║\n"
                        "║      NO CONFIGS FOUND                ║\n"
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
                yield Static(" ≡ CONFIG_INSPECTOR ", classes="pane-header-block-accent")
                yield Vertical(id="inspector-content")  # Dynamic content here

        # 3. Global Footer - Mechanical keycap style
        with Horizontal(id="app-footer"):
            yield Static(f" [{c['accent']}]CONFIGS[/] ", id="footer-version")
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
                    yield Static(f"[bold {c['primary']}] ESC [/]", classes="keycap")
                    yield Static(f"[{c['muted']}]Back[/]", classes="keycap-label")

    def on_mount(self) -> None:
        """Initialize the data table."""
        self._refresh_table()
        self.call_after_refresh(self._initialize_selection)
        self._update_pulse()
        self.set_interval(1.0, self._update_pulse)

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
        """Refresh the data table with configs."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#envs-table", DataTable)
        empty_state = self.query_one("#empty-state", Center)
        c = self.COLORS

        table.clear(columns=True)

        # Column layout - data stream style (matching Notes total: 118)
        table.add_column("", width=2)  # Selection indicator column
        table.add_column("TITLE", width=28)
        table.add_column("FILENAME", width=20)
        table.add_column("VARS", width=8)
        table.add_column("SYNC", width=12)
        table.add_column("PREVIEW", width=48)

        envs = app.vault.get_envs()

        # Toggle visibility based on entry count
        if len(envs) == 0:
            table.display = False
            empty_state.display = True
        else:
            table.display = True
            empty_state.display = False

        for env in envs:
            # Selection indicator - will be updated dynamically
            is_selected = env.id == self._selected_row_key
            indicator = f"[bold {c['primary']}]▸[/]" if is_selected else " "

            # Title - primary cyan for selected, white otherwise
            title_text = env.title[:20] if len(env.title) > 20 else env.title

            # Filename (muted grey)
            filename_text = f"[{c['muted']}]{env.filename}[/]"

            # Vars count (muted grey)
            vars_text = f"[{c['muted']}]{env.var_count}[/]"

            # Relative time (dim muted)
            updated = _get_relative_time(env.updated_at)
            updated_text = f"[dim {c['muted']}]{updated}[/]"

            # Metadata preview only - NEVER expose content values
            # Security: env files contain secrets (API keys, passwords, etc.)
            if env.var_count > 0:
                preview_text = (
                    f"[dim {c['muted']}]{env.var_count} vars · [ENCRYPTED][/]"
                )
            elif env.content.strip():
                preview_text = f"[dim {c['muted']}][ENCRYPTED][/]"
            else:
                preview_text = f"[dim {c['muted']}]// EMPTY[/]"

            table.add_row(
                indicator,
                title_text,
                filename_text,
                vars_text,
                updated_text,
                preview_text,
                key=env.id,
            )

        # Update the grid footer with object count
        footer = self.query_one("#grid-footer", Static)
        count = len(envs)
        footer.update(f" └── [{c['primary']}]{count}[/] CONFIGS LOADED")

    def _update_row_indicators(self, old_key: str | None, new_key: str | None) -> None:
        """Update only the indicator column for old and new selected rows.

        This avoids rebuilding the entire table on selection change.
        """
        table = self.query_one("#envs-table", DataTable)
        app: PassFXApp = self.app  # type: ignore
        envs = app.vault.get_envs()
        c = self.COLORS

        # Build a map of id -> entry for quick lookup
        env_map = {e.id: e for e in envs}

        # Get column keys (first column is the indicator)
        if not table.columns:
            return
        indicator_col = list(table.columns.keys())[0]

        # Clear old selection indicator
        if old_key and old_key in env_map:
            try:
                table.update_cell(old_key, indicator_col, " ")
            except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
                pass  # Row may not exist during rapid navigation

        # Set new selection indicator - cyan arrow for locked target feel
        if new_key and new_key in env_map:
            try:
                table.update_cell(new_key, indicator_col, f"[bold {c['primary']}]▸[/]")
            except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
                pass  # Row may not exist during rapid navigation

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

    # pylint: disable=too-many-locals,too-many-statements
    def _update_inspector(self, row_key: Any) -> None:
        """Update the inspector panel with env details.

        Renders a structured "Config Inspector" with:
        - Entry Header (large text, primary color)
        - Field Grid (labels in accent, values in text)
        - Config Stats (lines, vars)
        - Preview Section (terminal style)
        """
        inspector = self.query_one("#inspector-content", Vertical)
        inspector.remove_children()
        c = self.COLORS

        # Get the entry by row key
        app: PassFXApp = self.app  # type: ignore
        envs = app.vault.get_envs()

        # Find entry by ID
        env = None
        for e in envs:
            if e.id == str(row_key):
                env = e
                break

        if not env:
            # Empty state - styled for Operator theme
            inspector.mount(
                Static(
                    f"[dim {c['muted']}]╔══════════════════════════════╗\n"
                    "║                              ║\n"
                    "║    SELECT A CONFIG           ║\n"
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
                    f"[bold underline {c['primary']}]{env.title.upper()}[/]",
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
                    Static(f"[{c['text']}]CONFIG_FILE[/]", classes="field-value"),
                    classes="field-row",
                ),
                # Filename
                Horizontal(
                    Static(f"[{c['accent']}]FILE[/]", classes="field-label"),
                    Static(f"[{c['muted']}]{env.filename}[/]", classes="field-value"),
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
        # SECTION 3: Config Stats - Size metrics
        # ═══════════════════════════════════════════════════════════════
        inspector.mount(
            Vertical(
                Static(
                    f"[{c['accent']}]CONFIG_STATS[/]", classes="strength-section-label"
                ),
                Static(
                    f"[{c['text']}]{env.line_count}[/] lines  "
                    f"[{c['text']}]{env.var_count}[/] vars",
                    classes="strength-bar",
                ),
                classes="strength-section",
            )
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 4: Content Summary - Metadata only, no secret exposure
        # Security: env files contain secrets - NEVER render content in inspector
        # ═══════════════════════════════════════════════════════════════
        if env.content:
            # Count actual env vars (non-comment, non-empty lines with =)
            lines = env.content.split("\n")
            var_lines = [
                ln
                for ln in lines
                if "=" in ln and not ln.strip().startswith("#") and ln.strip()
            ]
            # Show safe metadata only
            content_display = (
                f"[{c['muted']}]●●●●●●●●●●●●●●●●●●●●[/]\n\n"
                f"[dim {c['muted']}]{len(lines)} lines · "
                f"{len(var_lines)} variables[/]\n\n"
                f"[dim]Press [bold {c['primary']}]V[/] to reveal content[/]"
            )
        else:
            content_display = f"[dim {c['muted']}]// EMPTY[/]"

        notes_terminal = Vertical(
            Static(content_display, classes="notes-code"),
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
            updated_full = datetime.fromisoformat(env.updated_at).strftime(
                "%Y-%m-%d %H:%M"
            )
        except (ValueError, TypeError):
            updated_full = env.updated_at or "Unknown"

        inspector.mount(
            Horizontal(
                Static(
                    f"[dim {c['muted']}]ID:[/] [{c['muted']}]{env.id[:8]}[/]",
                    classes="meta-id",
                ),
                Static(
                    f"[dim {c['muted']}]SYNC:[/] [{c['muted']}]{updated_full}[/]",
                    classes="meta-updated",
                ),
                classes="inspector-footer-bar",
            )
        )
