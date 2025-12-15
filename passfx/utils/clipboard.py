"""Clipboard utilities for PassFX.

Provides secure clipboard operations with auto-clear functionality.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

# Track active clipboard timers
_active_timer: threading.Timer | None = None
_clipboard_lock = threading.Lock()

# Default clear timeout in seconds
DEFAULT_CLEAR_TIMEOUT = 30


def copy_to_clipboard(
    text: str,
    auto_clear: bool = True,
    clear_after: int = DEFAULT_CLEAR_TIMEOUT,
    on_clear: Callable[[], None] | None = None,
) -> bool:
    """Copy text to clipboard with optional auto-clear.

    Args:
        text: Text to copy to clipboard.
        auto_clear: Whether to automatically clear after timeout.
        clear_after: Seconds before auto-clearing (default 30).
        on_clear: Optional callback when clipboard is cleared.

    Returns:
        True if successful, False otherwise.
    """
    global _active_timer

    try:
        import pyperclip

        pyperclip.copy(text)

        if auto_clear and clear_after > 0:
            # Cancel any existing timer
            with _clipboard_lock:
                if _active_timer is not None:
                    _active_timer.cancel()

                # Start new timer
                def clear_callback() -> None:
                    clear_clipboard()
                    if on_clear:
                        on_clear()

                _active_timer = threading.Timer(clear_after, clear_callback)
                _active_timer.daemon = True
                _active_timer.start()

        return True

    except ImportError:
        # pyperclip not installed, try platform-specific fallback
        return _fallback_copy(text)
    except Exception:
        return False


def clear_clipboard() -> bool:
    """Clear the clipboard contents.

    Returns:
        True if successful, False otherwise.
    """
    global _active_timer

    with _clipboard_lock:
        if _active_timer is not None:
            _active_timer.cancel()
            _active_timer = None

    try:
        import pyperclip

        pyperclip.copy("")
        return True
    except ImportError:
        return _fallback_clear()
    except Exception:
        return False


def get_clipboard() -> str | None:
    """Get current clipboard contents.

    Returns:
        Clipboard text or None if failed.
    """
    try:
        import pyperclip

        return pyperclip.paste()
    except Exception:
        return None


def cancel_auto_clear() -> None:
    """Cancel any pending auto-clear timer."""
    global _active_timer

    with _clipboard_lock:
        if _active_timer is not None:
            _active_timer.cancel()
            _active_timer = None


def _fallback_copy(text: str) -> bool:
    """Platform-specific clipboard copy fallback.

    Args:
        text: Text to copy.

    Returns:
        True if successful, False otherwise.
    """
    import subprocess
    import sys

    try:
        if sys.platform == "darwin":
            # macOS
            process = subprocess.Popen(
                ["pbcopy"],
                stdin=subprocess.PIPE,
                close_fds=True,
            )
            process.communicate(text.encode("utf-8"))
            return process.returncode == 0

        elif sys.platform.startswith("linux"):
            # Linux with xclip
            try:
                process = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                    close_fds=True,
                )
                process.communicate(text.encode("utf-8"))
                return process.returncode == 0
            except FileNotFoundError:
                # Try xsel
                process = subprocess.Popen(
                    ["xsel", "--clipboard", "--input"],
                    stdin=subprocess.PIPE,
                    close_fds=True,
                )
                process.communicate(text.encode("utf-8"))
                return process.returncode == 0

        elif sys.platform == "win32":
            # Windows
            import ctypes

            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32

            user32.OpenClipboard(0)
            user32.EmptyClipboard()

            # Encode as Windows Unicode
            encoded = text.encode("utf-16-le") + b"\x00\x00"
            h_mem = kernel32.GlobalAlloc(0x0042, len(encoded))
            p_mem = kernel32.GlobalLock(h_mem)
            ctypes.memmove(p_mem, encoded, len(encoded))
            kernel32.GlobalUnlock(h_mem)
            user32.SetClipboardData(13, h_mem)  # CF_UNICODETEXT
            user32.CloseClipboard()
            return True

    except Exception:
        pass

    return False


def _fallback_clear() -> bool:
    """Platform-specific clipboard clear fallback.

    Returns:
        True if successful, False otherwise.
    """
    return _fallback_copy("")


class ClipboardManager:
    """Context manager for clipboard operations with guaranteed cleanup.

    Usage:
        with ClipboardManager(password, clear_after=30) as cm:
            # Password is in clipboard
            pass
        # Clipboard is now cleared
    """

    def __init__(
        self,
        text: str,
        auto_clear: bool = True,
        clear_after: int = DEFAULT_CLEAR_TIMEOUT,
    ) -> None:
        """Initialize clipboard manager.

        Args:
            text: Text to copy.
            auto_clear: Whether to auto-clear on exit.
            clear_after: Seconds before auto-clear (if not exited).
        """
        self._text = text
        self._auto_clear = auto_clear
        self._clear_after = clear_after
        self._success = False

    def __enter__(self) -> "ClipboardManager":
        """Copy text to clipboard on enter."""
        self._success = copy_to_clipboard(
            self._text,
            auto_clear=True,
            clear_after=self._clear_after,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        """Clear clipboard on exit if auto_clear is enabled."""
        if self._auto_clear:
            cancel_auto_clear()
            clear_clipboard()

    @property
    def success(self) -> bool:
        """Return whether copy was successful."""
        return self._success
