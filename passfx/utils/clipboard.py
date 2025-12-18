"""Clipboard utilities for PassFX.

Provides secure clipboard operations with auto-clear functionality.
Includes emergency cleanup for signal-based shutdown scenarios.
"""

# pylint: disable=import-outside-toplevel

from __future__ import annotations

import atexit
import threading
from collections.abc import Callable

# Track active clipboard timers (mutable module state, not a constant)
_active_timer: threading.Timer | None = None  # pylint: disable=invalid-name
_clipboard_lock = threading.Lock()

# Flag to prevent double-cleanup
_cleanup_done: bool = False  # pylint: disable=invalid-name

# Default clear timeout in seconds (reduced from 30s for security)
DEFAULT_CLEAR_TIMEOUT = 15


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
        clear_after: Seconds before auto-clearing (default 15).
        on_clear: Optional callback when clipboard is cleared.

    Returns:
        True if successful, False otherwise.
    """
    global _active_timer  # pylint: disable=global-statement

    try:
        import pyperclip  # type: ignore[import-untyped]

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
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def clear_clipboard() -> bool:
    """Clear the clipboard contents.

    Returns:
        True if successful, False otherwise.
    """
    global _active_timer  # pylint: disable=global-statement

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
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def get_clipboard() -> str | None:
    """Get current clipboard contents.

    Returns:
        Clipboard text or None if failed.
    """
    try:
        import pyperclip

        result: str = pyperclip.paste()
        return result
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def cancel_auto_clear() -> None:
    """Cancel any pending auto-clear timer."""
    global _active_timer  # pylint: disable=global-statement

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
    import subprocess  # nosec B404 - Required for clipboard fallback
    import sys

    try:
        if sys.platform == "darwin":
            # macOS - pbcopy is a hardcoded system utility, not user input
            with subprocess.Popen(  # nosec B603 B607
                ["pbcopy"],
                stdin=subprocess.PIPE,
                close_fds=True,
            ) as process:
                process.communicate(text.encode("utf-8"))
                return process.returncode == 0

        if sys.platform.startswith("linux"):
            # Linux with xclip
            try:
                # xclip is a hardcoded system utility, not user input
                with subprocess.Popen(  # nosec B603 B607
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                    close_fds=True,
                ) as process:
                    process.communicate(text.encode("utf-8"))
                    return process.returncode == 0
            except FileNotFoundError:
                # xsel is a hardcoded system utility, not user input
                with subprocess.Popen(  # nosec B603 B607
                    ["xsel", "--clipboard", "--input"],
                    stdin=subprocess.PIPE,
                    close_fds=True,
                ) as process:
                    process.communicate(text.encode("utf-8"))
                    return process.returncode == 0

        if sys.platform == "win32":
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

    except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
        pass  # Fallback must fail silently

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

    def __enter__(self) -> ClipboardManager:
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


def emergency_cleanup() -> None:
    """Perform emergency clipboard cleanup on shutdown.

    Called by signal handlers or atexit to ensure clipboard is cleared
    even during abnormal termination. Safe to call multiple times.
    """
    global _cleanup_done  # pylint: disable=global-statement

    with _clipboard_lock:
        if _cleanup_done:
            return
        _cleanup_done = True

    # Cancel any pending timer
    cancel_auto_clear()

    # Clear clipboard - fail silently on errors
    try:
        clear_clipboard()
    except Exception:  # pylint: disable=broad-exception-caught  # nosec B110
        pass  # Emergency cleanup must not raise


def reset_cleanup_flag() -> None:
    """Reset cleanup flag for testing purposes only."""
    global _cleanup_done  # pylint: disable=global-statement
    _cleanup_done = False


# Register atexit handler for normal exit cleanup
atexit.register(emergency_cleanup)
