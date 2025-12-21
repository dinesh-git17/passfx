"""Settings Control Deck for PassFX - System Configuration Interface.

Dual-pane master-detail layout for managing application settings,
vault operations, and diagnostics. Persists preferences immediately.
"""

from __future__ import annotations

import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Input, Label, OptionList, Static, Switch
from textual.widgets.option_list import Option

from passfx.core.config import get_config
from passfx.utils.io import (
    ImportExportError,
    PathValidationError,
    export_vault,
    import_vault,
)
from passfx.widgets.keycap_footer import KeycapFooter

if TYPE_CHECKING:
    from passfx.app import PassFXApp

# Settings categories with codes for sidebar display
SETTINGS_CATEGORIES = [
    ("SEC", "SECURITY"),
    ("VLT", "VAULT"),
    ("INT", "INTERFACE"),
    ("DAT", "DATA"),
    ("DIA", "DIAGNOSTICS"),
]


def _make_category_item(code: str, label: str) -> Text:
    """Create a category item with Operator theme [ ] prefix decorators."""
    text = Text()
    text.append("[", style="bold #00FFFF")
    text.append(f"{code:^5}", style="bold #00FFFF")
    text.append("]", style="bold #00FFFF")
    text.append(f" {label}", style="white")
    return text


# --- Modal Screens for Dangerous Operations ---


class MasterPasswordModal(ModalScreen[bool]):
    """Modal requiring master password confirmation for dangerous operations.

    Returns True if password verified, False if cancelled.
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, operation_name: str) -> None:
        super().__init__()
        self.operation_name = operation_name

    def compose(self) -> ComposeResult:
        """Create the confirmation modal layout."""
        with Vertical(id="settings-modal", classes="secure-terminal"):
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static(
                        f"[ :: {self.operation_name.upper()} :: ]", id="modal-title"
                    )
                    yield Static("AUTH REQUIRED", classes="modal-status-warning")

            with Vertical(id="modal-form"):
                yield Label(
                    "[bold #ef4444]DANGER:[/] This operation cannot be undone.",
                    classes="warning-label",
                )
                yield Static("")
                yield Label("> MASTER_PASSWORD", classes="input-label")
                yield Input(
                    placeholder="Enter master password to confirm",
                    password=True,
                    id="password-input",
                )
                yield Static("", id="error-message")

            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ ABORT ]", id="cancel-button")
                yield Button(r"\[ CONFIRM ]", variant="error", id="confirm-button")

    def on_mount(self) -> None:
        """Focus password input."""
        self.query_one("#password-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(False)
        elif event.button.id == "confirm-button":
            self._verify_password()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        """Handle enter key in password field."""
        self._verify_password()

    def _verify_password(self) -> None:
        """Verify the master password."""
        app: PassFXApp = self.app  # type: ignore
        password = self.query_one("#password-input", Input).value

        if not password:
            self._show_error("Password required")
            return

        # Verify against current vault crypto
        if app.vault._crypto is None:
            self._show_error("Vault is locked")
            return

        # Re-derive key and check - this validates the password
        try:
            # pylint: disable=import-outside-toplevel
            from passfx.core.crypto import CryptoManager

            salt = app.vault._salt_path.read_bytes()
            test_crypto = CryptoManager(password, salt)
            # Try to decrypt current vault data to verify
            encrypted_data = app.vault.path.read_bytes()
            test_crypto.decrypt(encrypted_data)
            test_crypto.wipe()
            self.dismiss(True)
        except Exception:  # pylint: disable=broad-exception-caught
            self._show_error("Invalid password")

    def _show_error(self, message: str) -> None:
        """Display error message."""
        error_widget = self.query_one("#error-message", Static)
        error_widget.update(f"[bold #ef4444]{message}[/]")

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(False)


class ExportModal(ModalScreen[None]):
    """Modal for exporting vault data with format selection."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        """Create the export modal layout."""
        with Vertical(id="settings-modal", classes="secure-terminal"):
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static("[ :: EXPORT PROTOCOL :: ]", id="modal-title")
                    yield Static("STATUS: READY", classes="modal-status")

            with Vertical(id="modal-form"):
                yield Label("> FORMAT", classes="input-label")
                yield OptionList(
                    Option("JSON (encrypted backup)", id="json"),
                    Option("CSV (readable, includes passwords!)", id="csv"),
                    id="format-select",
                )

                yield Label("> EXPORT_PATH", classes="input-label")
                yield Input(
                    value=str(Path.home() / "passfx_export.json"),
                    id="path-input",
                )

                yield Static("", id="export-status")

            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ ABORT ]", id="cancel-button")
                yield Button(r"\[ EXPORT ]", variant="primary", id="export-button")

    def on_mount(self) -> None:
        """Focus format select."""
        self.query_one("#format-select", OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Update path based on format."""
        fmt = event.option.id
        path_input = self.query_one("#path-input", Input)
        current = Path(path_input.value)
        new_path = current.with_suffix(f".{fmt}")
        path_input.value = str(new_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "export-button":
            self._export()

    def _export(self) -> None:
        """Export the vault."""
        app: PassFXApp = self.app  # type: ignore
        status = self.query_one("#export-status", Static)

        path_str = self.query_one("#path-input", Input).value
        path = Path(path_str).expanduser()

        fmt = "json" if path.suffix == ".json" else "csv"

        try:
            data = app.vault.get_all_data()
            count = export_vault(data, path, fmt=fmt, include_sensitive=True)
            status.update(f"[#22c55e]Exported {count} entries to {path}[/]")
            self.notify(f"Exported {count} entries", title="Success")
        except PathValidationError as e:
            status.update(f"[#ef4444]Invalid path: {e}[/]")
        except ImportExportError as e:
            status.update(f"[#ef4444]{e}[/]")

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class ImportModal(ModalScreen[None]):
    """Modal for importing vault data."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, on_complete: None = None) -> None:
        super().__init__()
        self._on_complete = on_complete

    def compose(self) -> ComposeResult:
        """Create the import modal layout."""
        with Vertical(id="settings-modal", classes="secure-terminal"):
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static("[ :: IMPORT PROTOCOL :: ]", id="modal-title")
                    yield Static("STATUS: READY", classes="modal-status")

            with Vertical(id="modal-form"):
                yield Label("> IMPORT_PATH", classes="input-label")
                yield Input(placeholder="/path/to/file.json", id="path-input")

                yield Static("", id="import-status")

            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ ABORT ]", id="cancel-button")
                yield Button(r"\[ IMPORT ]", variant="primary", id="import-button")

    def on_mount(self) -> None:
        """Focus path input."""
        self.query_one("#path-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "import-button":
            self._import()

    def _import(self) -> None:
        """Import vault data."""
        app: PassFXApp = self.app  # type: ignore
        status = self.query_one("#import-status", Static)

        path_str = self.query_one("#path-input", Input).value.strip()
        if not path_str:
            status.update("[#ef4444]Please enter a file path[/]")
            return

        path = Path(path_str).expanduser()

        try:
            data, _ = import_vault(path)
            imported = app.vault.import_data(data, merge=True)
            total = sum(imported.values())
            status.update(f"[#22c55e]Imported {total} entries[/]")
            self.notify(f"Imported {total} entries", title="Success")
        except PathValidationError as e:
            status.update(f"[#ef4444]Invalid path: {e}[/]")
        except ImportExportError as e:
            status.update(f"[#ef4444]{e}[/]")

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class FactoryResetModal(ModalScreen[bool]):
    """Modal for confirming factory reset with master password."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        """Create the factory reset confirmation modal."""
        with Vertical(id="settings-modal", classes="secure-terminal"):
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static("[ :: FACTORY RESET :: ]", id="modal-title")
                    yield Static("CRITICAL", classes="modal-status-critical")

            with Vertical(id="modal-form"):
                yield Label(
                    "[bold #ef4444]WARNING: This will permanently delete:[/]",
                    classes="warning-label",
                )
                yield Static("  • All stored passwords")
                yield Static("  • All phone PINs")
                yield Static("  • All credit cards")
                yield Static("  • All secure notes")
                yield Static("  • All environment variables")
                yield Static("  • All recovery codes")
                yield Static("  • Application settings")
                yield Static("")
                yield Label(
                    "[bold #ef4444]This action CANNOT be undone.[/]",
                    classes="warning-label",
                )
                yield Static("")
                yield Label("> MASTER_PASSWORD", classes="input-label")
                yield Input(
                    placeholder="Enter master password to confirm",
                    password=True,
                    id="password-input",
                )
                yield Static("", id="error-message")

            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ ABORT ]", id="cancel-button")
                yield Button(r"\[ PURGE ALL DATA ]", variant="error", id="reset-button")

    def on_mount(self) -> None:
        """Focus password input."""
        self.query_one("#password-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(False)
        elif event.button.id == "reset-button":
            self._verify_and_reset()

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        """Handle enter key in password field."""
        self._verify_and_reset()

    def _verify_and_reset(self) -> None:
        """Verify password and perform factory reset."""
        app: PassFXApp = self.app  # type: ignore
        password = self.query_one("#password-input", Input).value

        if not password:
            self._show_error("Password required")
            return

        if app.vault._crypto is None:
            self._show_error("Vault is locked")
            return

        # Verify password
        try:
            # pylint: disable=import-outside-toplevel
            from passfx.core.crypto import CryptoManager

            salt = app.vault._salt_path.read_bytes()
            test_crypto = CryptoManager(password, salt)
            encrypted_data = app.vault.path.read_bytes()
            test_crypto.decrypt(encrypted_data)
            test_crypto.wipe()
        except Exception:  # pylint: disable=broad-exception-caught
            self._show_error("Invalid password")
            return

        # Password verified - perform factory reset
        self._perform_reset(app)

    def _perform_reset(self, app: PassFXApp) -> None:
        """Perform the actual factory reset."""
        try:
            # Lock vault first
            app.vault.lock()
            app._unlocked = False  # pylint: disable=protected-access

            # Delete vault directory contents
            vault_dir = Path.home() / ".passfx"
            if vault_dir.exists():
                shutil.rmtree(vault_dir)

            # Reset config singleton
            # pylint: disable=import-outside-toplevel
            from passfx.core.config import ConfigManager

            ConfigManager.reset_singleton()

            self.notify("Factory reset complete. Restart PassFX.", title="Reset")
            self.dismiss(True)

            # Exit application
            self.app.exit()

        except Exception as e:  # pylint: disable=broad-exception-caught
            self._show_error(f"Reset failed: {e}")

    def _show_error(self, message: str) -> None:
        """Display error message."""
        error_widget = self.query_one("#error-message", Static)
        error_widget.update(f"[bold #ef4444]{message}[/]")

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(False)


# --- Main Settings Screen ---


class SettingsScreen(Screen):
    """System Control Deck - dual-pane settings interface.

    Left pane: Category navigation sidebar
    Right pane: Content panels for each category
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("tab", "focus_content", "Focus Content", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._active_category = "SECURITY"

    def compose(self) -> ComposeResult:
        """Create the settings control deck layout."""
        # Header
        with Horizontal(id="settings-header"):
            yield Static(
                "[bold #00FFFF]:: SYS_CONFIG ::[/]", id="settings-header-title"
            )
            yield Static("[dim]System Control Deck[/]", id="settings-header-subtitle")

        # Main dual-pane container
        with Horizontal(id="settings-container"):
            # Left pane: Navigation sidebar
            with Vertical(id="settings-sidebar") as sidebar:
                sidebar.border_title = "CATEGORIES"
                yield OptionList(
                    *[
                        Option(_make_category_item(code, label), id=label)
                        for code, label in SETTINGS_CATEGORIES
                    ],
                    id="category-menu",
                )

            # Right pane: Content area
            with Vertical(id="settings-content"):
                yield Vertical(id="content-pane")

        # Footer with keycaps
        yield KeycapFooter(
            hints=[
                ("↑↓", "Navigate"),
                ("TAB", "Focus"),
                ("^K", "Search"),
                ("ESC", "Back"),
            ],
            footer_id="settings-footer",
            label=" SETTINGS ",
        )

    def on_mount(self) -> None:
        """Initialize settings screen."""
        self.query_one("#category-menu", OptionList).focus()
        self._render_category("SECURITY")

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        """Update content pane when category is highlighted."""
        if event.option_list.id == "category-menu":
            category = str(event.option.id)
            if category != self._active_category:
                self._active_category = category
                self._render_category(category)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle category selection - focus content pane."""
        if event.option_list.id == "category-menu":
            self.action_focus_content()

    def _render_category(self, category: str) -> None:
        """Render the content pane for the selected category."""
        content_pane = self.query_one("#content-pane", Vertical)

        # Clear existing content
        content_pane.remove_children()

        # Render appropriate panel
        if category == "SECURITY":
            self._render_security_panel(content_pane)
        elif category == "VAULT":
            self._render_vault_panel(content_pane)
        elif category == "INTERFACE":
            self._render_interface_panel(content_pane)
        elif category == "DATA":
            self._render_data_panel(content_pane)
        elif category == "DIAGNOSTICS":
            self._render_diagnostics_panel(content_pane)

    def _render_security_panel(self, container: Vertical) -> None:
        """Render the SECURITY settings panel."""
        config = get_config()

        # Panel header
        header = Static(
            "[bold #00FFFF]≡ SECURITY CONFIGURATION[/]",
            classes="panel-header",
        )
        container.mount(header)

        # Auto-Lock Timeout
        auto_lock_section = Vertical(classes="setting-section")
        container.mount(auto_lock_section)

        auto_lock_section.mount(
            Static("[#00FFFF]AUTO-LOCK TIMEOUT[/]", classes="setting-title")
        )
        auto_lock_section.mount(
            Static(
                "[dim]Lock vault after inactivity (0 = disabled)[/]",
                classes="setting-desc",
            )
        )

        auto_lock_row = Horizontal(classes="setting-row")
        auto_lock_section.mount(auto_lock_row)

        auto_lock_input = Input(
            value=str(config.auto_lock_minutes),
            id="auto-lock-input",
            classes="setting-input",
        )
        auto_lock_row.mount(auto_lock_input)
        auto_lock_row.mount(Static("[dim]minutes[/]", classes="setting-unit"))

        # Clipboard Timeout
        clipboard_section = Vertical(classes="setting-section")
        container.mount(clipboard_section)

        clipboard_section.mount(
            Static("[#00FFFF]CLIPBOARD TIMEOUT[/]", classes="setting-title")
        )
        clipboard_section.mount(
            Static(
                "[dim]Auto-clear clipboard (minimum 5 seconds)[/]",
                classes="setting-desc",
            )
        )

        clipboard_row = Horizontal(classes="setting-row")
        clipboard_section.mount(clipboard_row)

        clipboard_input = Input(
            value=str(config.clipboard_timeout_seconds),
            id="clipboard-input",
            classes="setting-input",
        )
        clipboard_row.mount(clipboard_input)
        clipboard_row.mount(Static("[dim]seconds[/]", classes="setting-unit"))

        # Validation status
        container.mount(Static("", id="security-status", classes="status-message"))

    def _render_vault_panel(self, container: Vertical) -> None:
        """Render the VAULT settings panel."""
        app: PassFXApp = self.app  # type: ignore

        header = Static(
            "[bold #00FFFF]≡ VAULT INFORMATION[/]",
            classes="panel-header",
        )
        container.mount(header)

        # Vault Statistics
        if app._unlocked:  # pylint: disable=protected-access
            stats = app.vault.get_stats()

            stats_section = Vertical(classes="setting-section")
            container.mount(stats_section)

            stats_section.mount(
                Static("[#00FFFF]STORED CREDENTIALS[/]", classes="setting-title")
            )

            stats_grid = Vertical(classes="stats-grid")
            stats_section.mount(stats_grid)

            stats_grid.mount(
                Static(f"  Passwords:      [bold]{stats.get('emails', 0):>5}[/]")
            )
            stats_grid.mount(
                Static(f"  Phone PINs:     [bold]{stats.get('phones', 0):>5}[/]")
            )
            stats_grid.mount(
                Static(f"  Credit Cards:   [bold]{stats.get('cards', 0):>5}[/]")
            )
            stats_grid.mount(
                Static(f"  Secure Notes:   [bold]{stats.get('notes', 0):>5}[/]")
            )
            stats_grid.mount(
                Static(f"  Env Variables:  [bold]{stats.get('envs', 0):>5}[/]")
            )
            stats_grid.mount(
                Static(f"  Recovery Codes: [bold]{stats.get('recovery', 0):>5}[/]")
            )
            stats_grid.mount(Static("  [dim]────────────────────────[/]"))
            stats_grid.mount(
                Static(f"  [bold #00FFFF]Total:          {stats.get('total', 0):>5}[/]")
            )

            # Vault file info
            vault_info = Vertical(classes="setting-section")
            container.mount(vault_info)

            vault_info.mount(Static("[#00FFFF]VAULT FILE[/]", classes="setting-title"))

            if app.vault.path.exists():
                size_bytes = app.vault.path.stat().st_size
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                else:
                    size_str = f"{size_bytes // 1024} KB"

                vault_info.mount(Static(f"  Path: [dim]{app.vault.path}[/]"))
                vault_info.mount(Static(f"  Size: [dim]{size_str}[/]"))
                mtime = datetime.fromtimestamp(app.vault.path.stat().st_mtime)
                vault_info.mount(
                    Static(f"  Modified: [dim]{mtime.strftime('%Y-%m-%d %H:%M')}[/]")
                )
        else:
            container.mount(
                Static("[dim]Vault is locked. Unlock to view statistics.[/]")
            )

    def _render_interface_panel(self, container: Vertical) -> None:
        """Render the INTERFACE settings panel."""
        config = get_config()

        header = Static(
            "[bold #00FFFF]≡ INTERFACE PREFERENCES[/]",
            classes="panel-header",
        )
        container.mount(header)

        # Matrix Rain Toggle
        matrix_section = Vertical(classes="setting-section")
        container.mount(matrix_section)

        matrix_section.mount(
            Static("[#00FFFF]MATRIX RAIN ANIMATION[/]", classes="setting-title")
        )
        matrix_section.mount(
            Static(
                "[dim]Enable background animation on login screen[/]",
                classes="setting-desc",
            )
        )

        matrix_row = Horizontal(classes="setting-row-switch")
        matrix_section.mount(matrix_row)

        matrix_switch = Switch(
            value=config.matrix_rain_enabled,
            id="matrix-rain-switch",
        )
        matrix_row.mount(matrix_switch)
        matrix_row.mount(
            Static(
                (
                    "[#22c55e]ENABLED[/]"
                    if config.matrix_rain_enabled
                    else "[dim]DISABLED[/]"
                ),
                id="matrix-rain-label",
                classes="switch-label",
            )
        )

        # Compact Mode Toggle
        compact_section = Vertical(classes="setting-section")
        container.mount(compact_section)

        compact_section.mount(
            Static("[#00FFFF]COMPACT MODE[/]", classes="setting-title")
        )
        compact_section.mount(
            Static(
                "[dim]Reduce padding and spacing in UI elements[/]",
                classes="setting-desc",
            )
        )

        compact_row = Horizontal(classes="setting-row-switch")
        compact_section.mount(compact_row)

        compact_switch = Switch(
            value=config.compact_mode_enabled,
            id="compact-mode-switch",
        )
        compact_row.mount(compact_switch)
        compact_row.mount(
            Static(
                (
                    "[#22c55e]ENABLED[/]"
                    if config.compact_mode_enabled
                    else "[dim]DISABLED[/]"
                ),
                id="compact-mode-label",
                classes="switch-label",
            )
        )

    def _render_data_panel(self, container: Vertical) -> None:
        """Render the DATA operations panel with dangerous actions."""
        header = Static(
            "[bold #00FFFF]≡ DATA OPERATIONS[/]",
            classes="panel-header",
        )
        container.mount(header)

        # Export Section
        export_section = Vertical(classes="setting-section")
        container.mount(export_section)

        export_section.mount(
            Static("[#00FFFF]EXPORT VAULT[/]", classes="setting-title")
        )
        export_section.mount(
            Static(
                "[dim]Export all credentials to JSON or CSV file[/]",
                classes="setting-desc",
            )
        )

        export_row = Horizontal(classes="setting-row-button")
        export_section.mount(export_row)

        export_button = Button(
            r"\[ EXPORT DATA ]",
            id="export-button",
            variant="primary",
        )
        export_row.mount(export_button)

        # Import Section
        import_section = Vertical(classes="setting-section")
        container.mount(import_section)

        import_section.mount(Static("[#00FFFF]IMPORT DATA[/]", classes="setting-title"))
        import_section.mount(
            Static(
                "[dim]Import credentials from JSON file (merges with existing)[/]",
                classes="setting-desc",
            )
        )

        import_row = Horizontal(classes="setting-row-button")
        import_section.mount(import_row)

        import_button = Button(
            r"\[ IMPORT DATA ]",
            id="import-button",
            variant="primary",
        )
        import_row.mount(import_button)

        # Danger Zone - Factory Reset
        danger_section = Vertical(classes="danger-section")
        container.mount(danger_section)

        danger_section.mount(
            Static(
                "[bold #ef4444]⚠ DANGER ZONE[/]",
                classes="danger-header",
            )
        )

        danger_section.mount(
            Static("[#ef4444]FACTORY RESET[/]", classes="setting-title-danger")
        )
        danger_section.mount(
            Static(
                "[dim]Permanently delete ALL data and settings[/]",
                classes="setting-desc",
            )
        )

        reset_row = Horizontal(classes="setting-row-button")
        danger_section.mount(reset_row)

        reset_button = Button(
            r"\[ FACTORY RESET ]",
            id="factory-reset-button",
            variant="error",
        )
        reset_row.mount(reset_button)

    def _render_diagnostics_panel(self, container: Vertical) -> None:
        """Render the DIAGNOSTICS panel."""
        header = Static(
            "[bold #00FFFF]≡ SYSTEM DIAGNOSTICS[/]",
            classes="panel-header",
        )
        container.mount(header)

        # System Info
        sys_section = Vertical(classes="setting-section")
        container.mount(sys_section)

        sys_section.mount(
            Static("[#00FFFF]SYSTEM INFORMATION[/]", classes="setting-title")
        )

        sys_grid = Vertical(classes="stats-grid")
        sys_section.mount(sys_grid)

        sys_grid.mount(Static(f"  Python:     [dim]{sys.version.split()[0]}[/]"))
        sys_grid.mount(Static(f"  Platform:   [dim]{platform.system()}[/]"))
        sys_grid.mount(Static(f"  Machine:    [dim]{platform.machine()}[/]"))

        # PassFX Info
        pfx_section = Vertical(classes="setting-section")
        container.mount(pfx_section)

        pfx_section.mount(
            Static("[#00FFFF]PASSFX INFORMATION[/]", classes="setting-title")
        )

        pfx_grid = Vertical(classes="stats-grid")
        pfx_section.mount(pfx_grid)

        pfx_grid.mount(Static("  Version:    [dim]1.0.2[/]"))
        pfx_grid.mount(Static("  Encryption: [dim]Fernet (AES-128-CBC)[/]"))
        pfx_grid.mount(Static("  KDF:        [dim]PBKDF2-HMAC-SHA256[/]"))
        pfx_grid.mount(Static("  Iterations: [dim]480,000[/]"))

        # Config File Location
        config_section = Vertical(classes="setting-section")
        container.mount(config_section)

        config_section.mount(
            Static("[#00FFFF]CONFIGURATION[/]", classes="setting-title")
        )

        config_grid = Vertical(classes="stats-grid")
        config_section.mount(config_grid)

        config_dir = Path.home() / ".passfx"
        config_grid.mount(Static(f"  Directory:  [dim]{config_dir}[/]"))
        config_grid.mount(Static(f"  Config:     [dim]{config_dir / 'config.json'}[/]"))

    # --- Event Handlers ---

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for settings fields."""
        config = get_config()

        # Get status widget if it exists (may not exist if on different panel)
        try:
            status: Static | None = self.query_one("#security-status", Static)
        except Exception:  # pylint: disable=broad-exception-caught
            status = None

        if event.input.id == "auto-lock-input":
            try:
                value = max(int(event.value) if event.value else 0, 0)
                config.auto_lock_minutes = value

                # Also update vault timeout
                app: PassFXApp = self.app  # type: ignore
                app.vault.set_lock_timeout(value * 60)

                if status:
                    status.update("[#22c55e]Auto-lock updated[/]")
            except ValueError:
                if status:
                    status.update("[#ef4444]Invalid number[/]")

        elif event.input.id == "clipboard-input":
            try:
                value = max(int(event.value) if event.value else 5, 5)
                config.clipboard_timeout_seconds = value
                if status:
                    status.update("[#22c55e]Clipboard timeout updated[/]")
            except ValueError:
                if status:
                    status.update("[#ef4444]Invalid number[/]")

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch toggle changes."""
        config = get_config()

        if event.switch.id == "matrix-rain-switch":
            config.matrix_rain_enabled = event.value
            try:
                label = self.query_one("#matrix-rain-label", Static)
                label.update(
                    "[#22c55e]ENABLED[/]" if event.value else "[dim]DISABLED[/]"
                )
            # pylint: disable=broad-exception-caught
            except Exception:  # nosec B110 - widget may not exist on different panel
                pass

            self.notify(
                f"Matrix rain {'enabled' if event.value else 'disabled'}",
                title="Settings",
            )

        elif event.switch.id == "compact-mode-switch":
            config.compact_mode_enabled = event.value
            try:
                label = self.query_one("#compact-mode-label", Static)
                label.update(
                    "[#22c55e]ENABLED[/]" if event.value else "[dim]DISABLED[/]"
                )
            # pylint: disable=broad-exception-caught
            except Exception:  # nosec B110 - widget may not exist on different panel
                pass

            self.notify(
                f"Compact mode {'enabled' if event.value else 'disabled'}",
                title="Settings",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the settings panels."""
        if event.button.id == "export-button":
            self.app.push_screen(ExportModal())

        elif event.button.id == "import-button":

            def refresh_vault_panel(_: None) -> None:
                if self._active_category == "VAULT":
                    self._render_category("VAULT")

            self.app.push_screen(ImportModal(), refresh_vault_panel)

        elif event.button.id == "factory-reset-button":

            def handle_reset(confirmed: bool | None) -> None:
                if confirmed:
                    # App will exit from modal
                    pass

            self.app.push_screen(FactoryResetModal(), handle_reset)

    def action_focus_content(self) -> None:
        """Move focus to the first interactive element in content pane."""
        # Try to focus the first input or switch in the content pane
        content = self.query_one("#content-pane", Vertical)
        inputs = content.query("Input, Switch, Button")
        if inputs:
            inputs.first().focus()

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()
