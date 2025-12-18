"""Main CLI entry point for PassFX.

Entry point with signal handling for graceful shutdown and cleanup.
"""

from __future__ import annotations

import signal
import sys
from types import FrameType

import setproctitle

from passfx.app import PassFXApp
from passfx.utils.clipboard import emergency_cleanup

# Terminal title - shown in terminal tab/window
TERMINAL_TITLE = "◀ PASSFX ▶ Your passwords. Offline. Encrypted."

# Global app reference for signal handlers
_app: PassFXApp | None = None  # pylint: disable=invalid-name


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
        except Exception:  # pylint: disable=broad-exception-caught
            pass  # Fail silently during shutdown

    # Exit with appropriate code
    # SIGINT (Ctrl-C) = 130, SIGTERM = 143
    sys.exit(128 + signum)


def _setup_signal_handlers() -> None:
    """Register signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


def main() -> int:
    """Main entry point for PassFX.

    Returns:
        Exit code (0 for success).
    """
    global _app  # pylint: disable=global-statement

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
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
