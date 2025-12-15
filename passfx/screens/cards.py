"""Credit Cards Screen for PassFX."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

from passfx.core.models import CreditCard
from passfx.utils.clipboard import copy_to_clipboard

if TYPE_CHECKING:
    from passfx.app import PassFXApp


class AddCardModal(ModalScreen[CreditCard | None]):
    """Modal for adding a new credit card."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="modal-container"):
            yield Static("Add Credit Card", id="modal-title")

            with Vertical(id="modal-content"):
                yield Label("Label (e.g., Chase Sapphire)")
                yield Input(placeholder="Label", id="label-input")

                yield Label("Card Number")
                yield Input(placeholder="Card Number", id="number-input")

                yield Label("Expiry (MM/YY)")
                yield Input(placeholder="MM/YY", id="expiry-input")

                yield Label("CVV")
                yield Input(placeholder="CVV", password=True, id="cvv-input")

                yield Label("Cardholder Name")
                yield Input(placeholder="Name", id="name-input")

                yield Label("Notes (optional)")
                yield Input(placeholder="Notes", id="notes-input")

            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel-button")
                yield Button("Save", variant="primary", id="save-button")

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
        """Save the card."""
        label = self.query_one("#label-input", Input).value.strip()
        number = self.query_one("#number-input", Input).value.strip()
        expiry = self.query_one("#expiry-input", Input).value.strip()
        cvv = self.query_one("#cvv-input", Input).value.strip()
        name = self.query_one("#name-input", Input).value.strip()
        notes = self.query_one("#notes-input", Input).value.strip()

        if not all([label, number, expiry, cvv, name]):
            self.notify("Please fill in all required fields", severity="error")
            return

        card = CreditCard(
            label=label,
            card_number=number,
            expiry=expiry,
            cvv=cvv,
            cardholder_name=name,
            notes=notes if notes else None,
        )
        self.dismiss(card)

    def action_cancel(self) -> None:
        """Cancel the modal."""
        self.dismiss(None)


class ViewCardModal(ModalScreen[None]):
    """Modal for viewing card details."""

    BINDINGS = [Binding("escape", "close", "Close")]

    def __init__(self, card: CreditCard) -> None:
        super().__init__()
        self.card = card

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Vertical(id="modal-container"):
            yield Static(f"Card: {self.card.label}", id="modal-title")

            with Vertical(id="modal-content"):
                yield Static(f"Number:      {self.card.card_number}")
                yield Static(f"Expiry:      {self.card.expiry}")
                yield Static(f"CVV:         {self.card.cvv}")
                yield Static(f"Cardholder:  {self.card.cardholder_name}")
                if self.card.notes:
                    yield Static(f"Notes:       {self.card.notes}")

                yield Static("")
                yield Static("Press Escape to close", classes="muted")

            with Horizontal(id="modal-buttons"):
                yield Button("Close", id="close-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        self.dismiss(None)

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)


class CardsScreen(Screen):
    """Screen for managing credit cards."""

    BINDINGS = [
        Binding("a", "add", "Add"),
        Binding("c", "copy", "Copy Number"),
        Binding("v", "view", "View"),
        Binding("d", "delete", "Delete"),
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Create the cards screen layout."""
        yield Header()

        with Vertical():
            yield Static(
                "[bold #00d4ff]╔══════════════════════════════════════╗[/]\n"
                "[bold #00d4ff]║[/]        [bold #00d4ff]CREDIT CARDS[/]        [bold #00d4ff]║[/]\n"
                "[bold #00d4ff]╚══════════════════════════════════════╝[/]",
                classes="title",
            )

            yield DataTable(id="cards-table", cursor_type="row")

            with Horizontal(id="action-bar"):
                yield Button("Add", id="add-button")
                yield Button("Copy", id="copy-button")
                yield Button("View", id="view-button")
                yield Button("Delete", id="delete-button", classes="-error")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the data table."""
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh the data table."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#cards-table", DataTable)

        table.clear(columns=True)
        table.add_columns("#", "Label", "Number", "Expiry", "Name")

        cards = app.vault.get_cards()
        for i, card in enumerate(cards, 1):
            table.add_row(
                str(i),
                card.label,
                card.masked_number,
                card.expiry,
                card.cardholder_name,
                key=card.id,
            )

        if cards:
            table.focus()

    def _get_selected_card(self) -> CreditCard | None:
        """Get the currently selected card."""
        app: PassFXApp = self.app  # type: ignore
        table = self.query_one("#cards-table", DataTable)

        if table.cursor_row is None:
            return None

        cards = app.vault.get_cards()
        if 0 <= table.cursor_row < len(cards):
            return cards[table.cursor_row]
        return None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "add-button":
            self.action_add()
        elif event.button.id == "copy-button":
            self.action_copy()
        elif event.button.id == "view-button":
            self.action_view()
        elif event.button.id == "delete-button":
            self.action_delete()

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
        """Copy card number to clipboard."""
        card = self._get_selected_card()
        if not card:
            self.notify("No card selected", severity="warning")
            return

        if copy_to_clipboard(card.card_number, auto_clear=True, clear_after=30):
            self.notify(f"Card number copied! Clears in 30s", title=card.label)
        else:
            self.notify("Failed to copy to clipboard", severity="error")

    def action_view(self) -> None:
        """View card details."""
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

        app: PassFXApp = self.app  # type: ignore
        app.vault.delete_card(card.id)
        self._refresh_table()
        self.notify(f"Deleted '{card.label}'", title="Deleted")

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()
