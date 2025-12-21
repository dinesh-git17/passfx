"""Main CLI entry point for PassFX.

Entry point with signal handling for graceful shutdown and cleanup.
Handles CLI arguments (--help, --version) before launching the TUI.
"""

from __future__ import annotations

import argparse
import signal
import sys
from types import FrameType

import setproctitle

from passfx.app import PassFXApp
from passfx.utils.clipboard import emergency_cleanup

# Version constant - kept in sync with pyproject.toml
__version__ = "1.0.2"

# Help text for --help output
HELP_TEXT = """\
passfx - A secure terminal password manager

USAGE:
    passfx                   Launch the password manager
    passfx --help            Show this help message
    passfx --version         Show version information

FIRST RUN:
    Create a master password (12+ chars, mixed case, digit, symbol).
    WARNING: There is no password recovery. Forget it, lose everything.

DATA LOCATION:
    ~/.passfx/vault.enc      Encrypted credentials
    ~/.passfx/salt           Cryptographic salt

SECURITY:
    - Fernet encryption (AES-128-CBC + HMAC-SHA256)
    - PBKDF2 key derivation (480,000 iterations)
    - No network, no cloud, no sync
    - Clipboard auto-clears after 15 seconds

NAVIGATION:
    q             Quit
    Esc           Go back
    a / e / d     Add / Edit / Delete
    c             Copy to clipboard
    Ctrl+K        Global search

More info: https://github.com/dinesh-git17/passfx
"""

# Terminal title - shown in terminal tab/window
TERMINAL_TITLE = "◀ PASSFX ▶ Your passwords. Offline. Encrypted."

# Global app reference for signal handlers
_app: PassFXApp | None = None  # pylint: disable=invalid-name


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Handles --help and --version flags before TUI launch.
    Uses custom help text for better user experience.
    """
    parser = argparse.ArgumentParser(
        prog="passfx",
        description="A secure terminal password manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,  # We handle --help ourselves for custom output
    )

    parser.add_argument(
        "-h",
        "--help",
        action="store_true",
        help="Show this help message and exit",
    )

    parser.add_argument(
        "-V",
        "--version",
        action="store_true",
        help="Show version information and exit",
    )

    return parser.parse_args()


def set_terminal_title(title: str) -> None:
    """Set the terminal window/tab title using ANSI escape sequence."""
    sys.stdout.write(f"\033]0;{title}\007")
    sys.stdout.flush()


def _signal_handler(signum: int, _frame: FrameType | None) -> None:
    """Handle termination signals with cleanup.

    Ensures vault is locked and clipboard is cleared on SIGINT/SIGTERM.
    """
    # Clear clipboard first (most critical)
    emergency_cleanup()

    # Lock vault if app exists and is unlocked
    if _app is not None:
        try:
            if _app.vault and _app._unlocked:
                _app.vault.lock()
        except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
            pass  # Intentional: signal handler must not raise

    # Exit with appropriate code
    # SIGINT (Ctrl-C) = 130, SIGTERM = 143
    sys.exit(128 + signum)


def _setup_signal_handlers() -> None:
    """Register signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


def main() -> int:
    """Main entry point for PassFX.

    Parses CLI arguments first, then launches TUI if no special flags.

    Returns:
        Exit code (0 for success).
    """
    global _app  # pylint: disable=global-statement

    # Parse CLI arguments before anything else
    args = _parse_args()

    # Handle --help flag
    if args.help:
        print(HELP_TEXT)
        return 0

    # Handle --version flag
    if args.version:
        print(f"passfx {__version__}")
        return 0

    # No special flags - launch the TUI
    # Set process title (removes "Python" from terminal tab)
    setproctitle.setproctitle("PassFX")
    set_terminal_title(TERMINAL_TITLE)

    # Register signal handlers before app starts
    _setup_signal_handlers()

    _app = PassFXApp()
    try:
        _app.run()
    finally:
        # Ensure cleanup on any exit path
        emergency_cleanup()
        if _app.vault and _app._unlocked:
            try:
                _app.vault.lock()
            except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
                pass  # Intentional: cleanup must not raise

    return 0


if __name__ == "__main__":
    sys.exit(main())
