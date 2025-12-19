# pylint: disable=too-many-lines,duplicate-code
"""Credit Cards Screen for PassFX."""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Input, Label, Static

from passfx.core.models import CreditCard
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


def _get_avatar_initials(label: str) -> str:
    """Generate 2-character avatar initials from label.

    Args:
        label: Card/bank label.

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


def _get_avatar_bg_color(label: str) -> str:
    """Generate a consistent background color for avatar based on label.

    Args:
        label: Card/bank label.

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


def _get_card_type_icon(card_number: str) -> str:
    """Get card network icon based on card number prefix.

    Args:
        card_number: Full or partial card number.

    Returns:
        Unicode icon representing card network.
    """
    digits = "".join(filter(str.isdigit, card_number))
    if not digits:
        return "💳"

    # Simple prefix detection
    if digits.startswith("4"):
        return "💳"  # Visa
    if digits.startswith(("51", "52", "53", "54", "55")):
        return "💳"  # Mastercard
    if digits.startswith(("34", "37")):
        return "💳"  # Amex
    if digits.startswith("6"):
        return "💳"  # Discover
    return "💳"


def _format_card_number(card_number: str) -> str:
    """Format card number with spaces every 4 digits.

    Args:
        card_number: Raw card number (may contain spaces/hyphens).

    Returns:
        Formatted card number like "4242 4242 4242 4242".
    """
    digits = "".join(filter(str.isdigit, card_number))
    # Group into chunks of 4
    chunks = [digits[i : i + 4] for i in range(0, len(digits), 4)]
    return " ".join(chunks)


def _validate_card_number(number: str) -> tuple[bool, str]:
    """Validate credit card number format.

    Args:
        number: Card number string (may contain spaces/hyphens).

    Returns:
        Tuple of (is_valid, cleaned_number or error_message).
    """
    # Strip spaces and hyphens
    cleaned = re.sub(r"[\s\-]", "", number)

    # Check digits only
    if not cleaned.isdigit():
        return False, "Invalid card number format"

    # Check length (13-19 digits for most cards)
    if 13 <= len(cleaned) <= 19:
        return True, cleaned
    return False, "Invalid card number format"


def _validate_expiry(expiry: str) -> tuple[bool, str]:
    """Validate and normalize expiry date format.

    Accepts various formats:
    - MMYY (e.g., "0125")
    - MM/YY (e.g., "01/25")
    - MM-YY (e.g., "01-25")

    Args:
        expiry: Expiry string in various formats.

    Returns:
        Tuple of (is_valid, normalized_expiry or error_message).
        Normalized format is always MM/YY.
    """
    # Strip whitespace
    expiry = expiry.strip()

    # Try to extract digits only
    digits = re.sub(r"[\s/\-]", "", expiry)

    # Must have exactly 4 digits (MMYY)
    if not digits.isdigit() or len(digits) != 4:
        return False, "Expiry must be MM/YY"

    month = int(digits[:2])
    year = digits[2:4]

    # Validate month range
    if 1 <= month <= 12:
        # Format as MM/YY
        normalized = f"{month:02d}/{year}"
        return True, normalized
    return False, "Expiry must be MM/YY"


def _validate_cvv(cvv: str) -> tuple[bool, str]:
    """Validate CVV format.

    Args:
        cvv: CVV string.

    Returns:
        Tuple of (is_valid, cvv or error_message).
    """
    # Must be 3 or 4 digits
    if not cvv.isdigit() or len(cvv) not in (3, 4):
        return False, "Invalid CVV"

    return True, cvv


# ═══════════════════════════════════════════════════════════════════════════════
# MODAL SCREENS
# ═══════════════════════════════════════════════════════════════════════════════


class AddCardModal(ModalScreen[CreditCard | None]):
    """Modal for adding a new credit card - Operator Grade Secure Write Console."""

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
                # Row 1: Label (Issuer)
                yield Label("> ISSUER_LABEL", classes="input-label")
                yield Input(placeholder="e.g. CHASE_SAPPHIRE", id="label-input")

                # Row 2: Card Number (PAN)
                yield Label("> PAN_NUMBER", classes="input-label")
                yield Input(placeholder="•••• •••• •••• ••••", id="number-input")

                # Row 3: Expiry Date
                yield Label("> EXPIRY_DATE", classes="input-label")
                yield Input(placeholder="MM/YY", id="expiry-input")

                # Row 4: CVV (Security Code) - sensitive field
                yield Label("> SECURITY_CODE", classes="input-label")
                yield Input(placeholder="•••", password=True, id="cvv-input")

                # Row 5: Cardholder Name
                yield Label("> CARDHOLDER", classes="input-label")
                yield Input(placeholder="NAME ON CARD", id="name-input")

                # Row 6: Notes
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
        """Save the card with strict validation."""
        label = self.query_one("#label-input", Input).value.strip()
        number_raw = self.query_one("#number-input", Input).value.strip()
        expiry = self.query_one("#expiry-input", Input).value.strip()
        cvv = self.query_one("#cvv-input", Input).value.strip()
        name = self.query_one("#name-input", Input).value.strip()
        notes = self.query_one("#notes-input", Input).value.strip()

        # Check required fields first
        if not label:
            self.notify("Label is required", severity="error")
            return
        if not name:
            self.notify("Cardholder name is required", severity="error")
            return

        # Validate card number
        valid, result = _validate_card_number(number_raw)
        if not valid:
            self.notify(result, severity="error")
            return
        cleaned_number = result

        # Validate expiry
        valid, result = _validate_expiry(expiry)
        if not valid:
            self.notify(result, severity="error")
            return
        normalized_expiry = result

        # Validate CVV
        valid, result = _validate_cvv(cvv)
        if not valid:
            self.notify(result, severity="error")
            return

        # All validations passed - create card
        card = CreditCard(
            label=label,
            card_number=cleaned_number,
            expiry=normalized_expiry,
            cvv=cvv,
            cardholder_name=name,
            notes=notes if notes else None,
        )
        self.dismiss(card)

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class EditCardModal(ModalScreen[dict | None]):
    """Modal for editing a credit card - Operator Grade Secure Write Console."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, card: CreditCard) -> None:
        super().__init__()
        self.card = card

    def compose(self) -> ComposeResult:
        """Create the Operator-grade modal layout."""
        with Vertical(id="pwd-modal", classes="secure-terminal"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static(
                        f"[ :: MODIFY // {self.card.label.upper()} :: ]",
                        id="modal-title",
                    )
                    yield Static("STATUS: EDIT", classes="modal-status")

            with Vertical(id="pwd-form"):
                yield Label("> ISSUER_LABEL", classes="input-label")
                yield Input(
                    value=self.card.label,
                    placeholder="e.g. CHASE_SAPPHIRE",
                    id="label-input",
                )

                yield Label("> PAN_NUMBER [BLANK = KEEP]", classes="input-label")
                yield Input(placeholder="•••• •••• •••• ••••", id="number-input")

                yield Label("> EXPIRY_DATE", classes="input-label")
                yield Input(
                    value=self.card.expiry,
                    placeholder="MM/YY",
                    id="expiry-input",
                )

                yield Label("> SECURITY_CODE [BLANK = KEEP]", classes="input-label")
                yield Input(placeholder="•••", password=True, id="cvv-input")

                yield Label("> CARDHOLDER", classes="input-label")
                yield Input(
                    value=self.card.cardholder_name,
                    placeholder="NAME ON CARD",
                    id="name-input",
                )

                yield Label("> METADATA", classes="input-label")
                yield Input(
                    value=self.card.notes or "",
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
        """Save the changes with validation."""
        label = self.query_one("#label-input", Input).value.strip()
        number_raw = self.query_one("#number-input", Input).value.strip()
        expiry = self.query_one("#expiry-input", Input).value.strip()
        cvv = self.query_one("#cvv-input", Input).value.strip()
        name = self.query_one("#name-input", Input).value.strip()
        notes = self.query_one("#notes-input", Input).value.strip()

        # Check required fields
        if not label:
            self.notify("Label is required", severity="error")
            return
        if not name:
            self.notify("Cardholder name is required", severity="error")
            return

        # Validate expiry (always required)
        valid, result = _validate_expiry(expiry)
        if not valid:
            self.notify(result, severity="error")
            return
        normalized_expiry = result

        # Build result dict
        result_dict: dict[str, Any] = {
            "label": label,
            "expiry": normalized_expiry,
            "cardholder_name": name,
            "notes": notes if notes else None,
        }

        # Validate card number only if provided
        if number_raw:
            valid, result = _validate_card_number(number_raw)
            if not valid:
                self.notify(result, severity="error")
                return
            result_dict["card_number"] = result

        # Validate CVV only if provided
        if cvv:
            valid, result = _validate_cvv(cvv)
            if not valid:
                self.notify(result, severity="error")
                return
            result_dict["cvv"] = cvv

        self.dismiss(result_dict)

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class ViewCardModal(ModalScreen[None]):
    """Modal for viewing a card - Operator Grade Secure Read Console."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "copy_number", "Copy"),
    ]

    def __init__(self, card: CreditCard) -> None:
        super().__init__()
        self.card = card

    def compose(self) -> ComposeResult:
        """Create the Operator-grade view modal layout."""
        # Format the card number with spaces
        formatted_number = _format_card_number(self.card.card_number)

        with Vertical(id="pwd-modal", classes="secure-terminal"):
            # HUD Header with status indicator
            with Vertical(classes="modal-header"):
                with Horizontal(classes="modal-header-row"):
                    yield Static("[ :: SECURE READ PROTOCOL :: ]", id="modal-title")
                    yield Static("STATUS: DECRYPTED", classes="modal-status")

            # Data Display Body
            with Vertical(id="pwd-form"):
                # Row 1: Label (Issuer)
                yield Label("> CARD_ISSUER", classes="input-label")
                yield Static(
                    f"  {self.card.label}", classes="view-value", id="label-value"
                )

                # Row 2: Cardholder Name
                yield Label("> CARDHOLDER", classes="input-label")
                yield Static(
                    f"  {self.card.cardholder_name}",
                    classes="view-value",
                    id="holder-value",
                )

                # Row 3: Card Number (Secret)
                yield Label("> CARD_NUMBER", classes="input-label")
                yield Static(
                    f"  [#22c55e]{formatted_number}[/]",
                    classes="view-value secret",
                    id="number-value",
                )

                # Row 4: Expiry
                yield Label("> VALID_THRU", classes="input-label")
                yield Static(
                    f"  {self.card.expiry}", classes="view-value", id="expiry-value"
                )

                # Row 5: CVV (Secret)
                yield Label("> CVV_CODE", classes="input-label")
                yield Static(
                    f"  [#f59e0b]{self.card.cvv}[/]",
                    classes="view-value secret",
                    id="cvv-value",
                )

            # Footer Actions - right aligned
            with Horizontal(id="modal-buttons"):
                yield Button(r"\[ DISMISS ]", variant="default", id="cancel-button")
                yield Button(r"\[ COPY NUMBER ]", variant="primary", id="save-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            self._copy_number()

    def _copy_number(self) -> None:
        """Copy card number to clipboard with auto-clear for security."""
        if copy_to_clipboard(self.card.card_number, auto_clear=True):
            self.notify("Card number copied! Clears in 15s", title="Copied")
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)

    def action_copy_number(self) -> None:
        """Copy card number via keybinding."""
        self._copy_number()


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


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CARDS SCREEN
# ═══════════════════════════════════════════════════════════════════════════════


class CardsScreen(Screen):
    """Screen for managing credit cards."""

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
        """Create the cards screen layout."""
        # 1. Global Header with Breadcrumbs
        with Horizontal(id="app-header"):
            yield Static(
                "[dim #64748b]HOME[/] [#475569]›[/] "
                "[dim #64748b]VAULT[/] [#475569]›[/] [bold #10b981]CARDS[/]",
                id="header-branding",
            )
            yield Static("░░ FINANCIAL VAULT ░░", id="header-status")
            yield Static("", id="header-lock")  # Will be updated with pulse

        # 2. Body (Master-Detail Split)
        with Horizontal(id="vault-body"):
            # Left Pane: Data Grid (Master) - 65%
            with Vertical(id="vault-grid-pane"):
                # Inverted Block Header
                yield Static(
                    " ≡ FINANCIAL_DATABASE ", classes="pane-header-block-green"
                )
                yield DataTable(id="cards-table", cursor_type="row")
                # Empty state placeholder (hidden by default)
                with Center(id="empty-state"):
                    yield Static(
                        "[dim #475569]╔══════════════════════════════════════╗\n"
                        "║                                      ║\n"
                        "║      NO CARDS FOUND                  ║\n"
                        "║                                      ║\n"
                        "║      INITIATE SEQUENCE [A]           ║\n"
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
                # Inverted Block Header
                yield Static(" ≡ ASSET_INSPECTOR ", classes="pane-header-block-green")
                yield Vertical(id="inspector-content")  # Dynamic content here

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
            header_lock.update("[#34d399]● [bold]ENCRYPTED[/][/]")
        else:
            header_lock.update("[#059669]○ [bold]ENCRYPTED[/][/]")

    def _initialize_selection(self) -> None:
        """Initialize table selection and inspector after render."""
        table = self.query_one("#cards-table", DataTable)
        table.focus()
        if table.row_count > 0:
            # Move cursor to first row
            table.move_cursor(row=0)
            # Get the key from the first card
            app: PassFXApp = self.app  # type: ignore
            cards = app.vault.get_cards()
            if cards:
                self._selected_row_key = cards[0].id
                self._update_inspector(cards[0].id)
        else:
            self._update_inspector(None)

    # pylint: disable=too-many-locals
    def _refresh_table(self) -> None:
        """Refresh the data table with cards."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#cards-table", DataTable)
        empty_state = self.query_one("#empty-state", Center)

        table.clear(columns=True)

        # Column layout - sized to fill available space
        table.add_column("", width=3)  # Selection indicator column
        table.add_column("Label", width=20)
        table.add_column("Number", width=24)
        table.add_column("Expiry", width=10)
        table.add_column("Holder", width=22)
        table.add_column("Updated", width=40)  # Wider to fill remaining space

        cards = app.vault.get_cards()

        # Toggle visibility based on card count
        if len(cards) == 0:
            table.display = False
            empty_state.display = True
        else:
            table.display = True
            empty_state.display = False

        for card in cards:
            # Selection indicator - will be updated dynamically
            is_selected = card.id == self._selected_row_key
            indicator = "[bold #10b981]▍[/]" if is_selected else " "

            # Label (white text)
            label_text = card.label

            # Masked Number (muted)
            number_text = f"[#94a3b8]{card.masked_number}[/]"

            # Expiry (cyan)
            expiry_text = f"[#06b6d4]{card.expiry}[/]"

            # Holder (dimmed)
            holder_text = f"[dim]{card.cardholder_name}[/]"

            # Relative time (dim)
            updated = _get_relative_time(card.updated_at)
            updated_text = f"[dim]{updated}[/]"

            table.add_row(
                indicator,
                label_text,
                number_text,
                expiry_text,
                holder_text,
                updated_text,
                key=card.id,
            )

        # Update the grid footer with object count
        footer = self.query_one("#grid-footer", Static)
        count = len(cards)
        footer.update(f" └── [{count}] ASSETS LOADED")

    def _update_row_indicators(self, old_key: str | None, new_key: str | None) -> None:
        """Update only the indicator column for old and new selected rows.

        This avoids rebuilding the entire table on selection change.
        """
        table = self.query_one("#cards-table", DataTable)
        app: PassFXApp = self.app  # type: ignore
        cards = app.vault.get_cards()

        # Build a map of id -> card for quick lookup
        card_map = {c.id: c for c in cards}

        # Get column keys (first column is the indicator)
        if not table.columns:
            return
        indicator_col = list(table.columns.keys())[0]

        # Clear old selection indicator
        if old_key and old_key in card_map:
            try:
                table.update_cell(old_key, indicator_col, " ")
            except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
                pass  # Row may not exist during rapid navigation

        # Set new selection indicator
        if new_key and new_key in card_map:
            try:
                table.update_cell(new_key, indicator_col, "[bold #10b981]▍[/]")
            except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
                pass  # Row may not exist during rapid navigation

    def _get_selected_card(self) -> CreditCard | None:
        """Get the currently selected card."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#cards-table", DataTable)

        if table.cursor_row is None:
            return None

        # Get cards and find by cursor row index
        cards = app.vault.get_cards()
        if 0 <= table.cursor_row < len(cards):
            return cards[table.cursor_row]
        return None

    def action_add(self) -> None:
        """Add a new card."""

        def handle_result(card: CreditCard | None) -> None:
            if card:
                app: PassFXApp = self.app  # type: ignore
                app.vault.add_card(card)
                self._refresh_table()
                self.notify(f"Added '{card.label}'", title="Success")

        self.app.push_screen(AddCardModal(), handle_result)

    def action_copy(self) -> None:
        """Copy card number to clipboard with auto-clear for security."""
        card = self._get_selected_card()
        if not card:
            self.notify("No card selected", severity="warning")
            return

        if copy_to_clipboard(card.card_number, auto_clear=True):
            self.notify("Card number copied! Clears in 15s", title=card.label)
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_edit(self) -> None:
        """Edit selected card."""
        card = self._get_selected_card()
        if not card:
            self.notify("No card selected", severity="warning")
            return

        def handle_result(changes: dict | None) -> None:
            if changes:
                app: PassFXApp = self.app  # type: ignore
                app.vault.update_card(card.id, **changes)
                self._refresh_table()
                self.notify("Card updated", title="Success")

        self.app.push_screen(EditCardModal(card), handle_result)

    def action_view(self) -> None:
        """View selected card in physical card format."""
        card = self._get_selected_card()
        if not card:
            self.notify("No card selected", severity="warning")
            return

        self.app.push_screen(ViewCardModal(card))

    def action_delete(self) -> None:
        """Delete selected card."""
        card = self._get_selected_card()
        if not card:
            self.notify("No card selected", severity="warning")
            return

        def handle_result(confirmed: bool | None) -> None:
            if confirmed:
                app: PassFXApp = self.app  # type: ignore
                app.vault.delete_card(card.id)
                self._refresh_table()
                self.notify(f"Deleted '{card.label}'", title="Deleted")

        self.app.push_screen(ConfirmDeleteModal(card.label), handle_result)

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
        """Update the inspector panel with card details.

        Renders a modernized "Asset Inspector" with:
        - Digital ID Card header with 2-char avatar
        - Payment Details widget (replaces security strength)
        - Notes terminal with line numbers
        - Footer metadata (ID, Updated)
        """
        inspector = self.query_one("#inspector-content", Vertical)
        inspector.remove_children()

        # Get the card by row key
        app: PassFXApp = self.app  # type: ignore
        cards = app.vault.get_cards()

        # Find card by ID
        card = None
        for c in cards:
            if c.id == str(row_key):
                card = c
                break

        if not card:
            # Empty state
            inspector.mount(
                Static(
                    "[dim #555555]╔══════════════════════════╗\n"
                    "║    SELECT AN ASSET       ║\n"
                    "║    TO VIEW DETAILS       ║\n"
                    "╚══════════════════════════╝[/]",
                    classes="inspector-empty",
                )
            )
            return

        # ═══════════════════════════════════════════════════════════════
        # SECTION 1: Digital ID Card Header with Avatar
        # ═══════════════════════════════════════════════════════════════
        initials = _get_avatar_initials(card.label)
        avatar_bg = _get_avatar_bg_color(card.label)

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
                            f"[bold #f8fafc]{card.label}[/]", classes="id-label-text"
                        ),
                        Static(
                            f"[dim #94a3b8]{card.cardholder_name}[/]",
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
        # SECTION 2: Payment Details Widget (replaces Security Strength)
        # ═══════════════════════════════════════════════════════════════
        icon = _get_card_type_icon(card.card_number)

        # Build card details display
        card_number_display = f"[#94a3b8]{card.masked_number}[/]"
        expiry_display = f"[#06b6d4]{card.expiry}[/]"
        cvv_display = "[#f59e0b]•••[/]"  # Always hidden

        inspector.mount(
            Vertical(
                Static("[dim #6b7280]▸ PAYMENT DETAILS[/]", classes="section-label"),
                Static(f"{icon} {card_number_display}", classes="strength-bar-widget"),
                Horizontal(
                    Static(
                        f"[dim #475569]EXPIRY:[/] {expiry_display}", classes="meta-id"
                    ),
                    Static(
                        f"[dim #475569]CVV:[/] {cvv_display}", classes="meta-updated"
                    ),
                    classes="inspector-footer-bar",
                ),
                classes="security-widget",
            )
        )

        # ═══════════════════════════════════════════════════════════════
        # SECTION 3: Notes Terminal with Line Numbers
        # ═══════════════════════════════════════════════════════════════
        if card.notes:
            # Split notes into lines and add line numbers
            lines = card.notes.split("\n")
            numbered_lines = []
            for i, line in enumerate(lines[:10], 1):  # Limit to 10 lines
                line_num = f"[dim #475569]{i:2}[/]"
                line_content = f"[#34d399]{line}[/]" if line.strip() else ""
                numbered_lines.append(f"{line_num} │ {line_content}")
            notes_content = "\n".join(numbered_lines)
        else:
            notes_content = "[dim #475569] 1[/] │ [dim #64748b]// NO NOTES[/]"

        notes_terminal = Vertical(
            Static(notes_content, classes="notes-code"),
            classes="notes-editor",
        )
        notes_terminal.border_title = "ENCRYPTED_MEMO"

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
            updated_full = datetime.fromisoformat(card.updated_at).strftime(
                "%Y-%m-%d %H:%M"
            )
        except (ValueError, TypeError):
            updated_full = card.updated_at or "Unknown"

        inspector.mount(
            Horizontal(
                Static(
                    f"[dim #475569]ID:[/] [#64748b]{card.id[:8]}[/]", classes="meta-id"
                ),
                Static(
                    f"[dim #475569]UPDATED:[/] [#64748b]{updated_full}[/]",
                    classes="meta-updated",
                ),
                classes="inspector-footer-bar",
            )
        )
