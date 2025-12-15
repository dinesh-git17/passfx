"""Main CLI entry point for PassFX."""

from __future__ import annotations

import sys


def main() -> int:
    """Main entry point for PassFX.

    Returns:
        Exit code (0 for success).
    """
    from passfx.app import PassFXApp

    app = PassFXApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
