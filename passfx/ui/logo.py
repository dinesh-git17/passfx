"""ASCII art logo and branding for PassFX - Visual Excellence."""

import random

from rich.align import Align
from rich.panel import Panel
from rich.text import Text

from passfx.ui.styles import console

# Epic ASCII art logo
LOGO_LARGE = r"""
    ██████╗  █████╗ ███████╗███████╗███████╗██╗  ██╗
    ██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝╚██╗██╔╝
    ██████╔╝███████║███████╗███████╗█████╗   ╚███╔╝
    ██╔═══╝ ██╔══██║╚════██║╚════██║██╔══╝   ██╔██╗
    ██║     ██║  ██║███████║███████║██║     ██╔╝ ██╗
    ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝  ╚═╝
"""

LOGO_SMALL = r"""
 ___  __   __  __  ___  _  _
(  ,\(  ) (  )(  )(  _)( \/ )
 ) _/ )(_  )( /)( ) _)  )  (
(_)  (___)(__)(__)(__)(_/\_)
"""

# Taglines - nerdy but professional
TAGLINES = [
    "Your secrets are safe with us. Probably.",
    "sudo rm -rf your_worries",
    "Encryption so good, even we can't read it.",
    "Because 'password123' wasn't cutting it.",
    "Fort Knox for your digital life.",
    "Trust issues? We've got encryption.",
    "Making hackers cry since 2024.",
    "256 bits of pure security.",
    "Where passwords go to live forever.",
    "Ctrl+S for your credentials.",
]

# Gradient color schemes
GRADIENT_CYBER = ["#00ffff", "#00d4ff", "#00aaff", "#0080ff", "#0055ff", "#aa00ff"]
GRADIENT_FIRE = ["#ff0000", "#ff4400", "#ff8800", "#ffaa00", "#ffcc00", "#ffff00"]
GRADIENT_MATRIX = ["#00ff00", "#00dd00", "#00bb00", "#009900", "#007700", "#005500"]
GRADIENT_OCEAN = ["#00ffff", "#00ddff", "#00bbff", "#0099ff", "#0077ff", "#0055ff"]


def get_logo() -> str:
    """Return the ASCII logo string."""
    return LOGO_LARGE


def get_random_tagline() -> str:
    """Return a random nerdy tagline."""
    return random.choice(TAGLINES)


def _apply_gradient(text: str, colors: list[str]) -> Text:
    """Apply gradient colors to text."""
    result = Text()
    lines = text.split("\n")

    for line_idx, line in enumerate(lines):
        if not line.strip():
            result.append("\n")
            continue

        color_idx = line_idx % len(colors)
        result.append(line, style=colors[color_idx])
        result.append("\n")

    return result


def _apply_horizontal_gradient(text: str, colors: list[str]) -> Text:
    """Apply horizontal gradient to each line."""
    result = Text()
    lines = text.split("\n")

    for line in lines:
        if not line.strip():
            result.append("\n")
            continue

        chars_per_color = max(1, len(line) // len(colors))
        for i, char in enumerate(line):
            color_idx = min(i // chars_per_color, len(colors) - 1)
            result.append(char, style=colors[color_idx])
        result.append("\n")

    return result


def display_logo(show_tagline: bool = True, style: str = "cyber") -> None:
    """Display the PassFX logo with gradient colors.

    Args:
        show_tagline: Whether to display a random tagline.
        style: Color style - "cyber", "fire", "matrix", "ocean"
    """
    gradients = {
        "cyber": GRADIENT_CYBER,
        "fire": GRADIENT_FIRE,
        "matrix": GRADIENT_MATRIX,
        "ocean": GRADIENT_OCEAN,
    }
    colors = gradients.get(style, GRADIENT_CYBER)

    # Apply gradient to logo
    logo_text = _apply_gradient(LOGO_LARGE, colors)

    console.print()
    console.print(Align.center(logo_text))

    if show_tagline:
        tagline = get_random_tagline()
        console.print(Align.center(Text(f'"{tagline}"', style="dim italic")))

    console.print()


def display_startup_message() -> None:
    """Display the startup sequence with visual flair."""
    console.print()

    # Logo with cyber gradient
    display_logo(show_tagline=True, style="cyber")

    # Startup message with animation feel
    startup_text = Text()
    startup_text.append("  ◆ ", style="cyan")
    startup_text.append("Initializing ", style="dim")
    startup_text.append("AES-256", style="bold cyan")
    startup_text.append(" encryption...", style="dim")

    console.print(Align.center(startup_text))
    console.print()


def display_exit_message() -> None:
    """Display the exit message with style."""
    console.print()

    # Create styled exit message
    exit_box = Text()
    exit_box.append("☕ ", style="yellow")
    exit_box.append(
        "May your passwords be strong and your coffee stronger", style="bright_cyan"
    )

    console.print(
        Panel(
            Align.center(exit_box),
            border_style="dim cyan",
            padding=(0, 2),
        )
    )

    console.print(
        Align.center(Text("Session terminated. Memory wiped. Goodbye!", style="dim"))
    )
    console.print()


def display_locked_message() -> None:
    """Display vault locked message."""
    lock_art = """
    ╔═══════════════════════════════════╗
    ║           🔒 VAULT LOCKED         ║
    ╠═══════════════════════════════════╣
    ║                                   ║
    ║   Session timed out for security  ║
    ║   Enter master password to unlock ║
    ║                                   ║
    ╚═══════════════════════════════════╝
    """
    console.print(Text(lock_art, style="yellow"))


def display_welcome_new_user() -> None:
    """Display welcome message for new users."""
    console.print()
    console.print(
        Panel(
            "[bold cyan]Welcome to PassFX![/bold cyan]\n\n"
            "[dim]No vault found. Let's create one and secure your digital life.[/dim]\n\n"
            "[yellow]⚡[/yellow] [dim]Your vault will be encrypted with[/dim] "
            "[bold]AES-256[/bold]\n"
            "[yellow]⚡[/yellow] [dim]Keys derived using[/dim] [bold]PBKDF2-SHA256[/bold] "
            "[dim](480k iterations)[/dim]\n"
            "[yellow]⚡[/yellow] [dim]Only you can unlock it with your master password[/dim]",
            title="[bold bright_cyan]🔐 First Time Setup[/bold bright_cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()


def display_vault_stats(emails: int, phones: int, cards: int) -> None:
    """Display vault statistics in a beautiful format."""
    total = emails + phones + cards

    stats_text = Text()
    stats_text.append("╭─────────────────────────────────╮\n", style="cyan")
    stats_text.append("│", style="cyan")
    stats_text.append("       📊 VAULT STATISTICS       ", style="bold")
    stats_text.append("│\n", style="cyan")
    stats_text.append("├─────────────────────────────────┤\n", style="cyan")

    stats_text.append("│", style="cyan")
    stats_text.append(f"  🔐 Passwords      │  {emails:>6}    ", style="white")
    stats_text.append("│\n", style="cyan")

    stats_text.append("│", style="cyan")
    stats_text.append(f"  📱 Phone PINs     │  {phones:>6}    ", style="white")
    stats_text.append("│\n", style="cyan")

    stats_text.append("│", style="cyan")
    stats_text.append(f"  💳 Credit Cards   │  {cards:>6}    ", style="white")
    stats_text.append("│\n", style="cyan")

    stats_text.append("├─────────────────────────────────┤\n", style="cyan")
    stats_text.append("│", style="cyan")
    stats_text.append("  ◆  Total Entries  │  ", style="bold cyan")
    stats_text.append(f"{total:>6}", style="bold bright_white")
    stats_text.append("    │\n", style="cyan")
    stats_text.append("╰─────────────────────────────────╯\n", style="cyan")

    console.print()
    console.print(stats_text)
