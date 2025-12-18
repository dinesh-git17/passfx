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


class AddPhoneModal(ModalScreen[PhoneCredential | None]):
    """Modal for adding a new phone credential."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="pwd-modal", classes="secure-terminal"):
            # Header
            yield Static(":: SYSTEM_ENTRY // COMMS_DEVICE ::", id="modal-title")

            # Form Body
            with Vertical(id="pwd-form"):
                # Row 1: Label (Device)
                yield Label("TARGET_DEVICE", classes="input-label")
                yield Input(placeholder="e.g. BANK_HOTLINE", id="label-input")

                # Row 2: Phone (Uplink)
                yield Label("UPLINK_NUMBER", classes="input-label")
                yield Input(placeholder="+1 555 000 0000", id="phone-input")

                # Row 3: PIN (Access Code)
                yield Label("ACCESS_PIN", classes="input-label")
                with Horizontal(classes="input-row"):
                    yield Input(placeholder="••••••", password=True, id="pin-input")

                # Row 4: Notes
                yield Label("METADATA", classes="input-label")
                yield Input(placeholder="OPTIONAL_NOTES", id="notes-input")

            # Footer Actions
            with Horizontal(id="modal-buttons"):
                yield Button("[ESC] ABORT", id="cancel-button")
                yield Button(
                    "[ENTER] ENCRYPT & WRITE", variant="primary", id="save-button"
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
    """Modal for editing a phone credential."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, credential: PhoneCredential) -> None:
        super().__init__()
        self.credential = credential

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="pwd-modal", classes="secure-terminal"):
            yield Static(
                f":: MODIFY_ENTRY // {self.credential.label.upper()} ::",
                id="modal-title",
            )

            with Vertical(id="pwd-form"):
                yield Label("TARGET_DEVICE", classes="input-label")
                yield Input(
                    value=self.credential.label,
                    placeholder="e.g. BANK_HOTLINE",
                    id="label-input",
                )

                yield Label("UPLINK_NUMBER", classes="input-label")
                yield Input(
                    value=self.credential.phone,
                    placeholder="+1 555 000 0000",
                    id="phone-input",
                )

                yield Label("ACCESS_PIN [BLANK = KEEP CURRENT]", classes="input-label")
                with Horizontal(classes="input-row"):
                    yield Input(placeholder="••••••", password=True, id="pin-input")

                yield Label("METADATA", classes="input-label")
                yield Input(
                    value=self.credential.notes or "",
                    placeholder="OPTIONAL_NOTES",
                    id="notes-input",
                )

            with Horizontal(id="modal-buttons"):
                yield Button("[ESC] ABORT", id="cancel-button")
                yield Button(
                    "[ENTER] ENCRYPT & WRITE", variant="primary", id="save-button"
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


class ViewPhoneModal(ModalScreen[None]):
    """Modal displaying a Secure Comms Uplink visualization."""

    # Color configuration for the phone modal (Synthwave Purple/Pink theme)
    COLORS = {
        "border": "#8b5cf6",
        "card_bg": "#0a0e27",
        "section_border": "#475569",
        "title_bg": "#8b5cf6",
        "title_fg": "#000000",
        "label_dim": "#64748b",
        "value_fg": "#f8fafc",
        "accent": "#d946ef",
        "accent_dim": "#2d1f3d",
        "muted": "#94a3b8",
        "btn_primary_bg": "#2d1f4a",
        "btn_primary_fg": "#d946ef",
        "btn_secondary_bg": "#1e293b",
        "btn_secondary_fg": "#94a3b8",
    }

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "copy_pin", "Copy"),
    ]

    def __init__(self, credential: PhoneCredential) -> None:
        super().__init__()
        self.credential = credential

    # pylint: disable=too-many-locals,too-many-statements
    def compose(self) -> ComposeResult:
        """Create the secure comms uplink layout."""
        c = self.COLORS

        # Get PIN strength for visual indicator
        strength = check_strength(self.credential.password)
        strength_color = _get_strength_color(strength.score)

        # Build signal strength indicator (synthwave style)
        signal_bars = ""
        for i in range(5):
            if i < strength.score + 1:
                signal_bars += f"[{c['accent']}]▓[/]"
            else:
                signal_bars += f"[{c['accent_dim']}]░[/]"

        # Format timestamp
        try:
            created = datetime.fromisoformat(self.credential.created_at).strftime(
                "%Y.%m.%d"
            )
        except (ValueError, TypeError):
            created = "UNKNOWN"

        # Build encryption lock visual
        lock_icon = (
            f"[{c['accent']}]◈[/]" if strength.score >= 2 else f"[{c['border']}]◇[/]"
        )

        # Card dimensions
        width = 96
        inner = width - 2
        section_inner = width - 6
        content_width = section_inner - 5

        with Vertical(id="phone-modal"):
            with Vertical(id="physical-sim-card"):
                # Top border
                yield Static(f"[bold {c['border']}]╔{'═' * inner}╗[/]")

                # Title row
                title = " SECURE COMMS UPLINK "
                title_pad = inner - len(title) - 2
                title_line = (
                    f"[bold {c['border']}]║[/]  "
                    f"[on {c['title_bg']}][bold {c['title_fg']}]{title}[/]"
                    f"{' ' * title_pad}[bold {c['border']}]║[/]"
                )
                yield Static(title_line)

                # Divider
                yield Static(f"[bold {c['border']}]╠{'═' * inner}╣[/]")

                # Device label
                device_val = self.credential.label.upper()
                device_line = (
                    f"[bold {c['border']}]║[/]  [dim {c['label_dim']}]DEVICE:[/] "
                    f"[bold {c['value_fg']}]{device_val:<{inner - 11}}[/] "
                    f"[bold {c['border']}]║[/]"
                )
                yield Static(device_line)

                # Spacer
                yield Static(
                    f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]"
                )

                # Signal strength row
                signal_content = (
                    f"  [dim {c['section_border']}]SIGNAL:[/] {signal_bars}  "
                    f"{lock_icon} [{c['accent']}]ENCRYPTED[/]"
                )
                signal_pad = inner - 40
                signal_line = (
                    f"[bold {c['border']}]║[/]{signal_content}"
                    f"{' ' * signal_pad}[bold {c['border']}]║[/]"
                )
                yield Static(signal_line)

                # Spacer
                yield Static(
                    f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]"
                )

                # Uplink Number section
                uplink_header = (
                    f"[bold {c['border']}]║[/]  "
                    f"[dim {c['section_border']}]┌─ UPLINK NUMBER "
                    f"{'─' * (section_inner - 17)}┐[/]  "
                    f"[bold {c['border']}]║[/]"
                )
                yield Static(uplink_header)
                uplink_content = (
                    f"[bold {c['border']}]║[/]  [dim {c['section_border']}]│[/] "
                    f"[{c['accent']}]☎[/] "
                    f"[bold {c['value_fg']}]{self.credential.phone:<{content_width}}[/] "
                    f"[dim {c['section_border']}]│[/]  [bold {c['border']}]║[/]"
                )
                yield Static(uplink_content)
                uplink_footer = (
                    f"[bold {c['border']}]║[/]  "
                    f"[dim {c['section_border']}]└{'─' * (section_inner - 1)}┘[/]  "
                    f"[bold {c['border']}]║[/]"
                )
                yield Static(uplink_footer)

                # Spacer
                yield Static(
                    f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]"
                )

                # Access PIN section
                pin_header = (
                    f"[bold {c['border']}]║[/]  "
                    f"[dim {c['section_border']}]┌─ ACCESS PIN "
                    f"{'─' * (section_inner - 14)}┐[/]  "
                    f"[bold {c['border']}]║[/]"
                )
                yield Static(pin_header)
                pin_content = (
                    f"[bold {c['border']}]║[/]  [dim {c['section_border']}]│[/] "
                    f"[{c['accent']}]►[/] "
                    f"[bold {c['accent']}]{self.credential.password:<{content_width}}[/] "
                    f"[dim {c['section_border']}]│[/]  [bold {c['border']}]║[/]"
                )
                yield Static(pin_content)
                pin_footer = (
                    f"[bold {c['border']}]║[/]  "
                    f"[dim {c['section_border']}]└{'─' * (section_inner - 1)}┘[/]  "
                    f"[bold {c['border']}]║[/]"
                )
                yield Static(pin_footer)

                # Spacer
                yield Static(
                    f"[bold {c['border']}]║[/]{' ' * inner}[bold {c['border']}]║[/]"
                )

                # Complexity row
                complexity_content = (
                    f"  [dim {c['label_dim']}]COMPLEXITY:[/] "
                    f"[{strength_color}]{strength.label.upper():<16}[/]"
                )
                complexity_pad = inner - 32
                complexity_line = (
                    f"[bold {c['border']}]║[/]{complexity_content}"
                    f"{' ' * complexity_pad}[bold {c['border']}]║[/]"
                )
                yield Static(complexity_line)

                # Footer divider
                yield Static(f"[bold {c['border']}]╠{'═' * inner}╣[/]")

                # Footer row
                footer_left = (
                    f"  [dim {c['section_border']}]ID:[/] "
                    f"[{c['muted']}]{self.credential.id[:8]}[/]"
                )
                footer_right = (
                    f"[dim {c['section_border']}]LINKED:[/] [{c['muted']}]{created}[/]"
                )
                footer_pad = inner - 30 - len(created)
                footer_line = (
                    f"[bold {c['border']}]║[/]{footer_left}"
                    f"{' ' * footer_pad}{footer_right}  "
                    f"[bold {c['border']}]║[/]"
                )
                yield Static(footer_line)

                # Bottom border
                yield Static(f"[bold {c['border']}]╚{'═' * inner}╝[/]")

            # Action Buttons
            with Horizontal(id="phone-modal-buttons"):
                yield Button("COPY PIN", id="copy-button")
                yield Button("CLOSE", id="close-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "close-button":
            self.dismiss(None)
        elif event.button.id == "copy-button":
            self._copy_pin()

    def _copy_pin(self) -> None:
        """Copy PIN to clipboard."""
        if copy_to_clipboard(self.credential.password, auto_clear=True, clear_after=30):
            self.notify("PIN copied! Clears in 30s", title="Copied")
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

    def __init__(self) -> None:
        super().__init__()
        self._selected_row_key: str | None = None
        self._pulse_state: bool = True

    def compose(self) -> ComposeResult:
        """Create the phones screen layout."""
        # 1. Global Header with Breadcrumbs
        with Horizontal(id="app-header"):
            breadcrumb = (
                "[dim #64748b]HOME[/] [#475569]›[/] "
                "[dim #64748b]VAULT[/] [#475569]›[/] "
                "[bold #8b5cf6]PHONES[/]"
            )
            yield Static(breadcrumb, id="header-branding")
            yield Static("░░ SECURE COMMS BANK ░░", id="header-status")
            yield Static("", id="header-lock")  # Will be updated with pulse

        # 2. Body (Master-Detail Split)
        with Horizontal(id="vault-body"):
            # Left Pane: Data Grid (Master) - 65%
            with Vertical(id="vault-grid-pane"):
                # Inverted Block Header
                yield Static(" ≡ SECURE_COMMS_DB ", classes="pane-header-block-purple")
                yield DataTable(id="phones-table", cursor_type="row")
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
                yield Static(
                    " └── UPLINK_ESTABLISHED", classes="pane-footer", id="grid-footer"
                )

            # Right Pane: Inspector (Detail) - 35%
            with Vertical(id="vault-inspector"):
                # Inverted Block Header
                yield Static(" ≡ DEVICE_INSPECTOR ", classes="pane-header-block-purple")
                yield Vertical(id="inspector-content")  # Dynamic content here

        # 3. Global Footer
        with Horizontal(id="app-footer"):
            yield Static(" VAULT ", id="footer-version")
            footer_keys = (
                " \\[A] Add  \\[C] Copy  \\[E] Edit  "
                "\\[D] Delete  \\[V] View  \\[ESC] Back"
            )
            yield Static(footer_keys, id="footer-keys-static")

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
            header_lock.update("[#d946ef]● [bold]ENCRYPTED[/][/]")
        else:
            header_lock.update("[#6b21a8]○ [bold]ENCRYPTED[/][/]")

    def _initialize_selection(self) -> None:
        """Initialize table selection and inspector after render."""
        table = self.query_one("#phones-table", DataTable)
        table.focus()
        if table.row_count > 0:
            # Move cursor to first row
            table.move_cursor(row=0)
            # Get the key from the first credential
            app: PassFXApp = self.app  # type: ignore
            credentials = app.vault.get_phones()
            if credentials:
                self._selected_row_key = credentials[0].id
                self._update_inspector(credentials[0].id)
        else:
            self._update_inspector(None)

    # pylint: disable=too-many-locals
    def _refresh_table(self) -> None:
        """Refresh the data table with credentials."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#phones-table", DataTable)
        empty_state = self.query_one("#empty-state", Center)

        table.clear(columns=True)

        # Column layout - sized to fill available space
        table.add_column("", width=3)  # Selection indicator column
        table.add_column("Label", width=22)
        table.add_column("Phone", width=22)
        table.add_column("Status", width=10)
        table.add_column("Updated", width=12)
        table.add_column("Notes", width=40)  # Wider to fill remaining space

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
            indicator = "[bold #8b5cf6]▍[/]" if is_selected else " "

            # Label (white text)
            label_text = cred.label

            # Phone (muted)
            phone_text = f"[#94a3b8]{cred.phone}[/]"

            # Status column with colored lock icon based on PIN strength
            strength = check_strength(cred.password)
            color = _get_strength_color(strength.score)
            status = f"[{color}]🔒[/]"

            # Relative time (dim)
            updated = _get_relative_time(cred.updated_at)
            updated_text = f"[dim]{updated}[/]"

            # Notes preview (dim)
            if cred.notes and len(cred.notes) > 16:
                notes = cred.notes[:16] + "…"
            else:
                notes = cred.notes or "-"
            notes_text = f"[dim #64748b]{notes}[/]"

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
        footer.update(f" └── [{count}] UPLINKS LOADED")

    def _update_row_indicators(self, old_key: str | None, new_key: str | None) -> None:
        """Update only the indicator column for old and new selected rows.

        This avoids rebuilding the entire table on selection change.
        """
        table = self.query_one("#phones-table", DataTable)
        app: PassFXApp = self.app  # type: ignore
        credentials = app.vault.get_phones()

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
                table.update_cell(new_key, indicator_col, "[bold #8b5cf6]▍[/]")
            except Exception:  # pylint: disable=broad-exception-caught
                pass  # Row may not exist

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
        """Copy PIN to clipboard."""
        cred = self._get_selected_credential()
        if not cred:
            self.notify("No credential selected", severity="warning")
            return

        if copy_to_clipboard(cred.password, auto_clear=True, clear_after=30):
            self.notify("PIN copied! Clears in 30s", title=cred.label)
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

    # pylint: disable=too-many-locals
    def _update_inspector(self, row_key: Any) -> None:
        """Update the inspector panel with credential details.

        Renders a modernized "Device Inspector" with:
        - Digital ID Card header with 2-char avatar
        - Block-based PIN strength progress bar
        - Notes terminal with line numbers
        - Footer metadata (ID, Updated)
        """
        inspector = self.query_one("#inspector-content", Vertical)
        inspector.remove_children()

        # Get the credential by row key
        app: PassFXApp = self.app  # type: ignore
        credentials = app.vault.get_phones()

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
                        Static(
                            f"[bold #f8fafc]{cred.label}[/]",
                            classes="id-label-text",
                        ),
                        Static(
                            f"[dim #94a3b8]{cred.phone}[/]",
                            classes="id-email-text",
                        ),
                        classes="id-details-stack",
                    ),
                    classes="id-card-header",
                ),
                classes="id-card-wrapper",
            )
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 2: PIN Strength Widget with Block Progress Bar
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
                Static("[dim #6b7280]▸ PIN ANALYSIS[/]", classes="section-label"),
                Static(strength_display, classes="strength-bar-widget"),
                Static(
                    f"[dim #475569]Complexity:[/] [#94a3b8]{strength.crack_time}[/]",
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
                line_content = f"[#d946ef]{line}[/]" if line.strip() else ""
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
            updated_full = datetime.fromisoformat(cred.updated_at).strftime(
                "%Y-%m-%d %H:%M"
            )
        except (ValueError, TypeError):
            updated_full = cred.updated_at or "Unknown"

        inspector.mount(
            Horizontal(
                Static(
                    f"[dim #475569]ID:[/] [#64748b]{cred.id[:8]}[/]",
                    classes="meta-id",
                ),
                Static(
                    f"[dim #475569]UPDATED:[/] [#64748b]{updated_full}[/]",
                    classes="meta-updated",
                ),
                classes="inspector-footer-bar",
            )
        )
