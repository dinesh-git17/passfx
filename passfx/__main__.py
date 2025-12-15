"""Allow running PassFX as a module: python -m passfx."""

from passfx.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
