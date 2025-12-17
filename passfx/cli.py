"""Main CLI entry point for PassFX."""

from __future__ import annotations

import sys

import setproctitle

from passfx.app import PassFXApp

# Terminal title - shown in terminal tab/window
TERMINAL_TITLE = "◀ PASSFX ▶ Your passwords. Offline. Encrypted."


def set_terminal_title(title: str) -> None:
    """Set the terminal window/tab title using ANSI escape sequence."""
    sys.stdout.write(f"\033]0;{title}\007")
    sys.stdout.flush()


def main() -> int:
    """Main entry point for PassFX.

    Returns:
        Exit code (0 for success).
    """
    # Set process title (removes "Python" from terminal tab)
    setproctitle.setproctitle("PassFX")
    set_terminal_title(TERMINAL_TITLE)

    app = PassFXApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
