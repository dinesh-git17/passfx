"""Rich console styling and theme configuration for PassFX."""

from rich.console import Console
from rich.theme import Theme

# Custom theme for PassFX
theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "prompt": "bold bright_cyan",
        "muted": "dim",
        "highlight": "bold magenta",
        "menu.header": "bold bright_cyan",
        "menu.option": "white",
        "menu.key": "bold yellow",
        "menu.description": "dim",
        "table.header": "bold bright_cyan",
        "table.row": "white",
        "password.weak": "bold red",
        "password.fair": "yellow",
        "password.good": "bright_green",
        "password.strong": "bold bright_green",
        "credit.card": "bold yellow",
        "secret": "dim red",
    }
)

# Global console instance
console = Console(theme=theme)


def print_error(message: str) -> None:
    """Print an error message with styling."""
    console.print(f"[error]Error:[/error] {message}")


def print_success(message: str) -> None:
    """Print a success message with styling."""
    console.print(f"[success]{message}[/success]")


def print_warning(message: str) -> None:
    """Print a warning message with styling."""
    console.print(f"[warning]Warning:[/warning] {message}")


def print_info(message: str) -> None:
    """Print an info message with styling."""
    console.print(f"[info]{message}[/info]")


def print_divider(char: str = "─", width: int = 50) -> None:
    """Print a styled divider line."""
    console.print(f"[dim]{char * width}[/dim]")


def print_header(title: str) -> None:
    """Print a styled header."""
    console.print()
    console.print(f"[menu.header]═══ {title} ═══[/menu.header]")
    console.print()


def get_masked_password(password: str, show_chars: int = 0) -> str:
    """Return a masked version of a password.

    Args:
        password: The password to mask.
        show_chars: Number of characters to show at the end.

    Returns:
        Masked password string.
    """
    if show_chars <= 0 or len(password) <= show_chars:
        return "•" * len(password)
    return "•" * (len(password) - show_chars) + password[-show_chars:]


def get_masked_card(card_number: str) -> str:
    """Return a masked credit card number showing only last 4 digits.

    Args:
        card_number: The card number to mask.

    Returns:
        Masked card number (e.g., '•••• •••• •••• 1234').
    """
    digits = "".join(filter(str.isdigit, card_number))
    if len(digits) < 4:
        return "•" * len(digits)
    last_four = digits[-4:]
    return f"•••• •••• •••• {last_four}"
