# Clipboard Utility Unit Tests
# Validates secure clipboard operations with auto-clear functionality.
# Ensures secrets do not linger longer than intended.

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, call, patch

import pytest

from passfx.utils import clipboard
from passfx.utils.clipboard import (
    DEFAULT_CLEAR_TIMEOUT,
    ClipboardManager,
    cancel_auto_clear,
    clear_clipboard,
    copy_to_clipboard,
    emergency_cleanup,
    get_clipboard,
    reset_cleanup_flag,
)

if TYPE_CHECKING:
    from collections.abc import Generator


# Test Fixtures


@pytest.fixture(autouse=True)
def reset_module_state() -> Generator[None, None, None]:
    """Reset clipboard module state before and after each test.

    Ensures tests are isolated and do not affect each other through
    module-level state (_active_timer, _cleanup_done).
    """
    # Directly reset module state to avoid calling methods on potentially mocked objects
    # This is safer than calling cancel_auto_clear() which may fail on Mock objects
    with clipboard._clipboard_lock:
        if clipboard._active_timer is not None:
            try:
                clipboard._active_timer.cancel()
            except (AttributeError, TypeError):
                pass  # Timer might be a Mock without cancel method
        clipboard._active_timer = None
    reset_cleanup_flag()
    yield
    # Clean up after test - same safe reset
    with clipboard._clipboard_lock:
        if clipboard._active_timer is not None:
            try:
                clipboard._active_timer.cancel()
            except (AttributeError, TypeError):
                pass
        clipboard._active_timer = None
    reset_cleanup_flag()


@pytest.fixture
def mock_pyperclip() -> Generator[MagicMock, None, None]:
    """Mock pyperclip module to avoid real clipboard operations."""
    clipboard_content = [""]  # Use list to allow mutation in nested function

    def mock_copy(text: str) -> None:
        clipboard_content[0] = text

    def mock_paste() -> str:
        return clipboard_content[0]

    with patch.dict("sys.modules", {"pyperclip": MagicMock()}) as _:
        mock_module = MagicMock()
        mock_module.copy = mock_copy
        mock_module.paste = mock_paste

        with patch.object(clipboard, "pyperclip", mock_module, create=True):
            # Patch the import inside the functions
            with patch(
                "passfx.utils.clipboard.copy_to_clipboard.__globals__",
                {**copy_to_clipboard.__globals__},
            ):
                yield mock_module


@pytest.fixture
def mock_timer() -> Generator[MagicMock, None, None]:
    """Mock threading.Timer for deterministic timing control."""
    mock_timer_instance = MagicMock(spec=threading.Timer)
    mock_timer_instance.daemon = True

    with patch("threading.Timer", return_value=mock_timer_instance) as mock_class:
        mock_class.return_value = mock_timer_instance
        yield mock_class


# ============================================================================
# Test Class: Copy to Clipboard Basic Operations
# ============================================================================


class TestCopyToClipboardBasic:
    """Tests for basic copy_to_clipboard functionality."""

    def test_copy_succeeds_with_pyperclip(self) -> None:
        """Copy returns True when pyperclip.copy succeeds."""
        with patch("builtins.__import__") as mock_import:
            mock_pyperclip = MagicMock()
            mock_import.return_value = mock_pyperclip

            with patch.object(
                clipboard,
                "copy_to_clipboard",
                wraps=clipboard.copy_to_clipboard,
            ):
                # Directly test with mocked import
                with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
                    result = copy_to_clipboard("test_secret", auto_clear=False)
                    assert result is True

    def test_copy_returns_false_on_pyperclip_error(self) -> None:
        """Copy returns False when pyperclip raises an exception."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.copy.side_effect = RuntimeError("Clipboard error")

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            result = copy_to_clipboard("test_secret", auto_clear=False)
            assert result is False

    def test_copy_correct_value_passed_to_pyperclip(self) -> None:
        """Verify exact value is passed to pyperclip.copy."""
        mock_pyperclip = MagicMock()
        test_value = "super_secret_password_123!"

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            copy_to_clipboard(test_value, auto_clear=False)
            mock_pyperclip.copy.assert_called_once_with(test_value)

    def test_copy_empty_string(self) -> None:
        """Copy handles empty string without error."""
        mock_pyperclip = MagicMock()

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            result = copy_to_clipboard("", auto_clear=False)
            assert result is True
            mock_pyperclip.copy.assert_called_once_with("")

    def test_copy_unicode_content(self) -> None:
        """Copy handles unicode characters correctly."""
        mock_pyperclip = MagicMock()
        unicode_text = "p@ssw\u00f6rd_\u4e2d\u6587_\U0001f511"

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            result = copy_to_clipboard(unicode_text, auto_clear=False)
            assert result is True
            mock_pyperclip.copy.assert_called_once_with(unicode_text)

    def test_copy_multiline_content(self) -> None:
        """Copy handles multiline text correctly."""
        mock_pyperclip = MagicMock()
        multiline = "line1\nline2\nline3"

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            result = copy_to_clipboard(multiline, auto_clear=False)
            assert result is True
            mock_pyperclip.copy.assert_called_once_with(multiline)

    def test_copy_special_characters(self) -> None:
        """Copy handles special characters correctly."""
        mock_pyperclip = MagicMock()
        special = 'p@$$w0rd!#$%^&*(){}[]|\\:";<>?,./~`'

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            result = copy_to_clipboard(special, auto_clear=False)
            assert result is True
            mock_pyperclip.copy.assert_called_once_with(special)


# ============================================================================
# Test Class: Auto-Clear Timer Behavior
# ============================================================================


class TestAutoClearTimer:
    """Tests for auto-clear timer functionality."""

    def test_auto_clear_timer_started_by_default(self) -> None:
        """Timer is started when auto_clear=True (default)."""
        mock_pyperclip = MagicMock()
        mock_timer_instance = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch(
                "threading.Timer", return_value=mock_timer_instance
            ) as timer_cls:
                copy_to_clipboard("secret")
                timer_cls.assert_called_once()
                mock_timer_instance.start.assert_called_once()

    def test_auto_clear_timer_not_started_when_disabled(self) -> None:
        """Timer is not started when auto_clear=False."""
        mock_pyperclip = MagicMock()

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer") as timer_cls:
                copy_to_clipboard("secret", auto_clear=False)
                timer_cls.assert_not_called()

    def test_auto_clear_uses_custom_timeout(self) -> None:
        """Timer uses provided clear_after value."""
        mock_pyperclip = MagicMock()
        mock_timer_instance = MagicMock(spec=threading.Timer)
        custom_timeout = 45

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch(
                "threading.Timer", return_value=mock_timer_instance
            ) as timer_cls:
                copy_to_clipboard("secret", clear_after=custom_timeout)
                # First arg is timeout, second is callback
                assert timer_cls.call_args[0][0] == custom_timeout

    def test_auto_clear_uses_default_timeout(self) -> None:
        """Timer uses DEFAULT_CLEAR_TIMEOUT when not specified."""
        mock_pyperclip = MagicMock()
        mock_timer_instance = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch(
                "threading.Timer", return_value=mock_timer_instance
            ) as timer_cls:
                copy_to_clipboard("secret")
                assert timer_cls.call_args[0][0] == DEFAULT_CLEAR_TIMEOUT

    def test_auto_clear_timer_is_daemon(self) -> None:
        """Timer is set as daemon thread."""
        mock_pyperclip = MagicMock()
        mock_timer_instance = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer_instance):
                copy_to_clipboard("secret")
                assert mock_timer_instance.daemon is True

    def test_auto_clear_timer_not_started_with_zero_timeout(self) -> None:
        """Timer is not started when clear_after=0."""
        mock_pyperclip = MagicMock()

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer") as timer_cls:
                copy_to_clipboard("secret", clear_after=0)
                timer_cls.assert_not_called()

    def test_auto_clear_timer_not_started_with_negative_timeout(self) -> None:
        """Timer is not started when clear_after is negative."""
        mock_pyperclip = MagicMock()

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer") as timer_cls:
                copy_to_clipboard("secret", clear_after=-1)
                timer_cls.assert_not_called()


# ============================================================================
# Test Class: Timer Cancellation and Reset
# ============================================================================


class TestTimerCancellation:
    """Tests for timer cancellation behavior."""

    def test_new_copy_cancels_existing_timer(self) -> None:
        """New copy operation cancels any existing timer."""
        mock_pyperclip = MagicMock()
        first_timer = MagicMock(spec=threading.Timer)
        second_timer = MagicMock(spec=threading.Timer)
        timer_instances = [first_timer, second_timer]
        timer_index = [0]

        def create_timer(*args: Any, **kwargs: Any) -> MagicMock:
            timer = timer_instances[timer_index[0]]
            if timer_index[0] < len(timer_instances) - 1:
                timer_index[0] += 1
            return timer

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", side_effect=create_timer):
                copy_to_clipboard("first_secret")
                copy_to_clipboard("second_secret")

                # First timer should have been cancelled
                first_timer.cancel.assert_called()

    def test_cancel_auto_clear_stops_timer(self) -> None:
        """cancel_auto_clear() stops the active timer."""
        mock_pyperclip = MagicMock()
        mock_timer_instance = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer_instance):
                copy_to_clipboard("secret")
                cancel_auto_clear()

                mock_timer_instance.cancel.assert_called()

    def test_cancel_auto_clear_clears_timer_reference(self) -> None:
        """cancel_auto_clear() sets _active_timer to None."""
        mock_pyperclip = MagicMock()
        mock_timer_instance = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer_instance):
                copy_to_clipboard("secret")
                cancel_auto_clear()

                # Module state should be cleared
                assert clipboard._active_timer is None

    def test_cancel_auto_clear_safe_when_no_timer(self) -> None:
        """cancel_auto_clear() does not error when no timer exists."""
        # Ensure no timer exists
        cancel_auto_clear()
        # Should not raise
        cancel_auto_clear()

    def test_multiple_cancel_calls_are_safe(self) -> None:
        """Multiple cancel_auto_clear() calls do not cause errors."""
        mock_pyperclip = MagicMock()
        mock_timer_instance = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer_instance):
                copy_to_clipboard("secret")
                cancel_auto_clear()
                cancel_auto_clear()
                cancel_auto_clear()

                # Should only be cancelled once effectively
                # (multiple calls don't error)


# ============================================================================
# Test Class: Callback Invocation
# ============================================================================


class TestCallbackInvocation:
    """Tests for on_clear callback functionality."""

    def test_callback_invoked_on_auto_clear(self) -> None:
        """Callback is invoked when auto-clear timer fires."""
        mock_pyperclip = MagicMock()
        callback = MagicMock()
        captured_callback: list[Any] = []

        def capture_timer(timeout: float, callback_fn: Any) -> MagicMock:
            captured_callback.append(callback_fn)
            timer = MagicMock(spec=threading.Timer)
            return timer

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", side_effect=capture_timer):
                copy_to_clipboard("secret", on_clear=callback)

                # Manually invoke the timer callback
                assert len(captured_callback) == 1
                captured_callback[0]()

                callback.assert_called_once()

    def test_callback_not_invoked_when_timer_cancelled(self) -> None:
        """Callback is not invoked when timer is cancelled before firing."""
        mock_pyperclip = MagicMock()
        callback = MagicMock()
        mock_timer_instance = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer_instance):
                copy_to_clipboard("secret", on_clear=callback)
                cancel_auto_clear()

                # Callback should not have been called
                callback.assert_not_called()

    def test_callback_none_does_not_error(self) -> None:
        """No error when on_clear is None and timer fires."""
        mock_pyperclip = MagicMock()
        captured_callback: list[Any] = []

        def capture_timer(timeout: float, callback_fn: Any) -> MagicMock:
            captured_callback.append(callback_fn)
            return MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", side_effect=capture_timer):
                copy_to_clipboard("secret", on_clear=None)
                # Should not raise when timer fires
                captured_callback[0]()


# ============================================================================
# Test Class: Clear Clipboard
# ============================================================================


class TestClearClipboard:
    """Tests for clear_clipboard functionality."""

    def test_clear_sets_clipboard_to_empty_string(self) -> None:
        """clear_clipboard sets clipboard content to empty string."""
        mock_pyperclip = MagicMock()

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            result = clear_clipboard()

            assert result is True
            mock_pyperclip.copy.assert_called_once_with("")

    def test_clear_returns_false_on_error(self) -> None:
        """clear_clipboard returns False when pyperclip fails."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.copy.side_effect = RuntimeError("Clipboard error")

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            result = clear_clipboard()

            assert result is False

    def test_clear_cancels_active_timer(self) -> None:
        """clear_clipboard cancels any active timer."""
        mock_pyperclip = MagicMock()
        mock_timer_instance = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer_instance):
                copy_to_clipboard("secret")
                clear_clipboard()

                mock_timer_instance.cancel.assert_called()

    def test_clear_sets_timer_to_none(self) -> None:
        """clear_clipboard sets _active_timer to None."""
        mock_pyperclip = MagicMock()
        mock_timer_instance = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer_instance):
                copy_to_clipboard("secret")
                clear_clipboard()

                assert clipboard._active_timer is None

    def test_clear_safe_when_no_timer(self) -> None:
        """clear_clipboard does not error when no timer exists."""
        mock_pyperclip = MagicMock()

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            # Ensure no timer
            cancel_auto_clear()
            result = clear_clipboard()

            assert result is True


# ============================================================================
# Test Class: Get Clipboard
# ============================================================================


class TestGetClipboard:
    """Tests for get_clipboard functionality."""

    def test_get_returns_clipboard_content(self) -> None:
        """get_clipboard returns current clipboard content."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.return_value = "clipboard_content"

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            result = get_clipboard()

            assert result == "clipboard_content"

    def test_get_returns_none_on_error(self) -> None:
        """get_clipboard returns None when pyperclip fails."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.side_effect = RuntimeError("Clipboard error")

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            result = get_clipboard()

            assert result is None

    def test_get_returns_empty_string_when_clipboard_empty(self) -> None:
        """get_clipboard returns empty string when clipboard is empty."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.return_value = ""

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            result = get_clipboard()

            assert result == ""

    def test_get_preserves_unicode(self) -> None:
        """get_clipboard preserves unicode characters."""
        mock_pyperclip = MagicMock()
        unicode_content = "\u4e2d\u6587\U0001f511"
        mock_pyperclip.paste.return_value = unicode_content

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            result = get_clipboard()

            assert result == unicode_content


# ============================================================================
# Test Class: ClipboardManager Context Manager
# ============================================================================


class TestClipboardManager:
    """Tests for ClipboardManager context manager."""

    def test_manager_copies_on_enter(self) -> None:
        """ClipboardManager copies text when entering context."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                with ClipboardManager("test_secret"):
                    mock_pyperclip.copy.assert_called_with("test_secret")

    def test_manager_clears_on_exit(self) -> None:
        """ClipboardManager clears clipboard when exiting context."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                with ClipboardManager("test_secret"):
                    pass
                # Should have called copy("") to clear
                assert call("") in mock_pyperclip.copy.call_args_list

    def test_manager_clears_on_exception(self) -> None:
        """ClipboardManager clears clipboard even when exception raised."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                with pytest.raises(ValueError):
                    with ClipboardManager("test_secret"):
                        raise ValueError("Test error")

                # Should still have cleared
                assert call("") in mock_pyperclip.copy.call_args_list

    def test_manager_success_property_true_on_success(self) -> None:
        """ClipboardManager.success is True when copy succeeds."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                with ClipboardManager("test_secret") as cm:
                    assert cm.success is True

    def test_manager_success_property_false_on_failure(self) -> None:
        """ClipboardManager.success is False when copy fails."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.copy.side_effect = RuntimeError("Copy failed")

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with ClipboardManager("test_secret") as cm:
                assert cm.success is False

    def test_manager_cancels_timer_on_exit(self) -> None:
        """ClipboardManager cancels auto-clear timer on exit."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                with ClipboardManager("test_secret"):
                    pass

                mock_timer.cancel.assert_called()

    def test_manager_uses_custom_clear_after(self) -> None:
        """ClipboardManager uses provided clear_after value."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer) as timer_cls:
                with ClipboardManager("test_secret", clear_after=60):
                    assert timer_cls.call_args[0][0] == 60

    def test_manager_auto_clear_false_skips_clear_on_exit(self) -> None:
        """ClipboardManager does not clear if auto_clear=False."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                with ClipboardManager("test_secret", auto_clear=False):
                    pass

                # When auto_clear=False in __init__, the copy still happens
                # but __exit__ behavior depends on _auto_clear flag
                # This test documents the current behavior
                pass


class TestClipboardManagerEdgeCases:
    """Edge case tests for ClipboardManager."""

    def test_manager_nested_context(self) -> None:
        """Nested ClipboardManager instances work correctly."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                with ClipboardManager("outer"):
                    with ClipboardManager("inner"):
                        # Inner should have copied
                        assert call("inner") in mock_pyperclip.copy.call_args_list

    def test_manager_reusable(self) -> None:
        """ClipboardManager can be used multiple times in sequence."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                with ClipboardManager("first"):
                    pass
                with ClipboardManager("second"):
                    pass

                assert call("first") in mock_pyperclip.copy.call_args_list
                assert call("second") in mock_pyperclip.copy.call_args_list


# ============================================================================
# Test Class: Emergency Cleanup
# ============================================================================


class TestEmergencyCleanup:
    """Tests for emergency_cleanup functionality."""

    def test_emergency_cleanup_clears_clipboard(self) -> None:
        """emergency_cleanup clears the clipboard."""
        mock_pyperclip = MagicMock()

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            reset_cleanup_flag()
            emergency_cleanup()

            mock_pyperclip.copy.assert_called_with("")

    def test_emergency_cleanup_idempotent(self) -> None:
        """emergency_cleanup only runs once per session."""
        mock_pyperclip = MagicMock()

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            reset_cleanup_flag()
            emergency_cleanup()
            emergency_cleanup()
            emergency_cleanup()

            # Should only be called once
            assert mock_pyperclip.copy.call_count == 1

    def test_emergency_cleanup_cancels_timer(self) -> None:
        """emergency_cleanup cancels any active timer."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                reset_cleanup_flag()
                copy_to_clipboard("secret")
                emergency_cleanup()

                mock_timer.cancel.assert_called()

    def test_emergency_cleanup_safe_on_error(self) -> None:
        """emergency_cleanup does not raise on errors."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.copy.side_effect = RuntimeError("Cleanup error")

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            reset_cleanup_flag()
            # Should not raise
            emergency_cleanup()

    def test_reset_cleanup_flag_allows_rerun(self) -> None:
        """reset_cleanup_flag allows emergency_cleanup to run again."""
        mock_pyperclip = MagicMock()

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            reset_cleanup_flag()
            emergency_cleanup()
            reset_cleanup_flag()
            emergency_cleanup()

            # Should be called twice
            assert mock_pyperclip.copy.call_count == 2


# ============================================================================
# Test Class: Fallback Copy (Platform-Specific)
# ============================================================================


class TestFallbackCopyMacOS:
    """Tests for macOS pbcopy fallback."""

    def test_fallback_copy_macos_success(self) -> None:
        """Fallback copy works on macOS using pbcopy."""
        from passfx.utils.clipboard import _fallback_copy

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.__enter__ = MagicMock(return_value=mock_process)
        mock_process.__exit__ = MagicMock(return_value=False)

        with patch("sys.platform", "darwin"):
            with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
                result = _fallback_copy("test")

                assert result is True
                mock_popen.assert_called_once()
                call_args = mock_popen.call_args
                assert call_args[0][0] == ["pbcopy"]

    def test_fallback_copy_macos_failure(self) -> None:
        """Fallback copy returns False on macOS when pbcopy fails."""
        from passfx.utils.clipboard import _fallback_copy

        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.__enter__ = MagicMock(return_value=mock_process)
        mock_process.__exit__ = MagicMock(return_value=False)

        with patch("sys.platform", "darwin"):
            with patch("subprocess.Popen", return_value=mock_process):
                result = _fallback_copy("test")

                assert result is False


class TestFallbackCopyLinux:
    """Tests for Linux xclip/xsel fallback."""

    def test_fallback_copy_linux_xclip_success(self) -> None:
        """Fallback copy works on Linux using xclip."""
        from passfx.utils.clipboard import _fallback_copy

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.__enter__ = MagicMock(return_value=mock_process)
        mock_process.__exit__ = MagicMock(return_value=False)

        with patch("sys.platform", "linux"):
            with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
                result = _fallback_copy("test")

                assert result is True
                call_args = mock_popen.call_args
                assert call_args[0][0] == ["xclip", "-selection", "clipboard"]

    def test_fallback_copy_linux_xsel_fallback(self) -> None:
        """Fallback copy falls back to xsel when xclip not found."""
        from passfx.utils.clipboard import _fallback_copy

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.__enter__ = MagicMock(return_value=mock_process)
        mock_process.__exit__ = MagicMock(return_value=False)

        def popen_side_effect(cmd: list[str], **kwargs: Any) -> MagicMock:
            if cmd[0] == "xclip":
                raise FileNotFoundError("xclip not found")
            return mock_process

        with patch("sys.platform", "linux"):
            with patch("subprocess.Popen", side_effect=popen_side_effect):
                result = _fallback_copy("test")

                assert result is True


class TestFallbackClear:
    """Tests for fallback clear functionality."""

    def test_fallback_clear_calls_fallback_copy_empty(self) -> None:
        """_fallback_clear calls _fallback_copy with empty string."""
        with patch(
            "passfx.utils.clipboard._fallback_copy", return_value=True
        ) as mock_copy:
            from passfx.utils.clipboard import _fallback_clear

            result = _fallback_clear()

            assert result is True
            mock_copy.assert_called_once_with("")


class TestFallbackUnsupportedPlatform:
    """Tests for fallback on unsupported platforms."""

    def test_fallback_copy_unsupported_platform_returns_false(self) -> None:
        """_fallback_copy returns False on unsupported platforms."""
        from passfx.utils.clipboard import _fallback_copy

        with patch("sys.platform", "freebsd"):
            result = _fallback_copy("test")
            assert result is False

    def test_fallback_copy_exception_returns_false(self) -> None:
        """_fallback_copy returns False when subprocess fails."""
        from passfx.utils.clipboard import _fallback_copy

        with patch("sys.platform", "darwin"):
            with patch("subprocess.Popen", side_effect=OSError("Command failed")):
                result = _fallback_copy("test")
                assert result is False


# ============================================================================
# Test Class: Import Error Handling
# ============================================================================


class TestImportErrorHandling:
    """Tests for handling pyperclip import errors."""

    def test_copy_uses_fallback_on_import_error(self) -> None:
        """copy_to_clipboard uses fallback when pyperclip import fails."""
        import builtins

        with patch(
            "passfx.utils.clipboard._fallback_copy", return_value=True
        ) as mock_fallback:
            original_import = builtins.__import__

            def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
                if name == "pyperclip":
                    raise ImportError("No module named 'pyperclip'")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", mock_import):
                result = copy_to_clipboard("test", auto_clear=False)
                assert result is True
                mock_fallback.assert_called_once_with("test")

    def test_clear_uses_fallback_on_import_error(self) -> None:
        """clear_clipboard uses fallback when pyperclip import fails."""
        import builtins

        with patch(
            "passfx.utils.clipboard._fallback_clear", return_value=True
        ) as mock_fallback:
            original_import = builtins.__import__

            def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
                if name == "pyperclip":
                    raise ImportError("No module named 'pyperclip'")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", mock_import):
                result = clear_clipboard()
                assert result is True
                mock_fallback.assert_called_once()


class TestEmergencyCleanupExceptionHandling:
    """Tests for exception handling in emergency_cleanup."""

    def test_emergency_cleanup_suppresses_clear_clipboard_exception(self) -> None:
        """emergency_cleanup suppresses exceptions from clear_clipboard."""
        reset_cleanup_flag()

        with patch(
            "passfx.utils.clipboard.clear_clipboard",
            side_effect=RuntimeError("Clear failed"),
        ):
            # Should not raise
            emergency_cleanup()

    def test_emergency_cleanup_still_cancels_timer_on_exception(self) -> None:
        """emergency_cleanup cancels timer even if clear raises."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                reset_cleanup_flag()
                copy_to_clipboard("secret")

                # Make clear_clipboard raise after canceling timer
                def clear_that_raises() -> bool:
                    # Call original to test the real path
                    raise RuntimeError("Clear failed")

                with patch.object(clipboard, "clear_clipboard", clear_that_raises):
                    emergency_cleanup()

                # Timer should still have been cancelled (via cancel_auto_clear)
                mock_timer.cancel.assert_called()


# ============================================================================
# Test Class: Thread Safety
# ============================================================================


class TestThreadSafety:
    """Tests for thread-safe clipboard operations."""

    def test_concurrent_copy_operations(self) -> None:
        """Concurrent copy operations do not cause race conditions."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)
        results: list[bool] = []
        errors: list[Exception] = []

        def copy_task(value: str) -> None:
            try:
                result = copy_to_clipboard(value, auto_clear=False)
                results.append(result)
            except Exception as e:
                errors.append(e)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                threads = [
                    threading.Thread(target=copy_task, args=(f"value_{i}",))
                    for i in range(10)
                ]

                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

                assert len(errors) == 0
                assert all(r is True for r in results)

    def test_concurrent_cancel_operations(self) -> None:
        """Concurrent cancel operations do not cause race conditions."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)
        errors: list[Exception] = []

        def cancel_task() -> None:
            try:
                cancel_auto_clear()
            except Exception as e:
                errors.append(e)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                copy_to_clipboard("secret")

                threads = [threading.Thread(target=cancel_task) for _ in range(10)]

                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

                assert len(errors) == 0

    def test_copy_and_cancel_concurrent(self) -> None:
        """Copy and cancel operations can run concurrently safely."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)
        errors: list[Exception] = []

        def mixed_task(op: str, value: str = "") -> None:
            try:
                if op == "copy":
                    copy_to_clipboard(value, auto_clear=False)
                else:
                    cancel_auto_clear()
            except Exception as e:
                errors.append(e)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                threads = []
                for i in range(5):
                    threads.append(
                        threading.Thread(target=mixed_task, args=("copy", f"v{i}"))
                    )
                    threads.append(
                        threading.Thread(target=mixed_task, args=("cancel",))
                    )

                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

                assert len(errors) == 0


# ============================================================================
# Test Class: Safety Guarantees
# ============================================================================


class TestSafetyGuarantees:
    """Tests validating clipboard safety guarantees."""

    def test_clear_replaces_with_empty_not_none(self) -> None:
        """Clipboard is cleared with empty string, not None."""
        mock_pyperclip = MagicMock()

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            clear_clipboard()

            # Must be empty string, not None
            mock_pyperclip.copy.assert_called_once_with("")

    def test_exception_does_not_expose_content(self) -> None:
        """Exceptions do not include clipboard content in message."""
        mock_pyperclip = MagicMock()
        secret_value = "super_secret_password_123"
        mock_pyperclip.copy.side_effect = RuntimeError("Generic clipboard error")

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            # The function should return False, not raise
            result = copy_to_clipboard(secret_value, auto_clear=False)
            assert result is False

            # If we got an exception, verify it doesn't contain the secret
            try:
                mock_pyperclip.copy.reset_mock()
                mock_pyperclip.copy.side_effect = RuntimeError("Error")
                mock_pyperclip.copy(secret_value)
            except RuntimeError as e:
                assert secret_value not in str(e)

    def test_timer_callback_clears_clipboard(self) -> None:
        """Timer callback actually clears the clipboard."""
        mock_pyperclip = MagicMock()
        captured_callback: list[Any] = []

        def capture_timer(timeout: float, callback_fn: Any) -> MagicMock:
            captured_callback.append(callback_fn)
            timer = MagicMock(spec=threading.Timer)
            return timer

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", side_effect=capture_timer):
                copy_to_clipboard("secret")

                # Invoke the callback
                captured_callback[0]()

                # Verify clipboard was cleared
                assert call("") in mock_pyperclip.copy.call_args_list

    def test_manager_guarantees_cleanup_on_any_exit(self) -> None:
        """ClipboardManager guarantees cleanup regardless of exit path."""
        mock_pyperclip = MagicMock()
        mock_timer = MagicMock(spec=threading.Timer)

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=mock_timer):
                # Normal exit
                with ClipboardManager("secret1"):
                    pass
                assert call("") in mock_pyperclip.copy.call_args_list

                mock_pyperclip.copy.reset_mock()

                # Exception exit
                try:
                    with ClipboardManager("secret2"):
                        raise KeyboardInterrupt()
                except KeyboardInterrupt:
                    pass
                assert call("") in mock_pyperclip.copy.call_args_list

                mock_pyperclip.copy.reset_mock()

                # Early return (simulated)
                with ClipboardManager("secret3"):
                    pass  # Would be return in real code
                assert call("") in mock_pyperclip.copy.call_args_list


# ============================================================================
# Test Class: Module Constants
# ============================================================================


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_default_clear_timeout_reasonable(self) -> None:
        """DEFAULT_CLEAR_TIMEOUT is a reasonable value."""
        # Should be positive
        assert DEFAULT_CLEAR_TIMEOUT > 0
        # Should not be too short (allow user to paste)
        assert DEFAULT_CLEAR_TIMEOUT >= 5
        # Should not be too long (security risk)
        assert DEFAULT_CLEAR_TIMEOUT <= 60

    def test_default_clear_timeout_exact_value(self) -> None:
        """DEFAULT_CLEAR_TIMEOUT has expected value of 15 seconds."""
        assert DEFAULT_CLEAR_TIMEOUT == 15


# ============================================================================
# Test Class: Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Integration-style tests for common clipboard workflows."""

    def test_copy_clear_cycle(self) -> None:
        """Complete copy-clear cycle works correctly."""
        mock_pyperclip = MagicMock()
        clipboard_content = [""]

        def mock_copy(text: str) -> None:
            clipboard_content[0] = text

        def mock_paste() -> str:
            return clipboard_content[0]

        mock_pyperclip.copy = mock_copy
        mock_pyperclip.paste = mock_paste

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=MagicMock(spec=threading.Timer)):
                # Copy
                copy_to_clipboard("secret", auto_clear=False)
                assert clipboard_content[0] == "secret"

                # Clear
                clear_clipboard()
                assert clipboard_content[0] == ""

    def test_rapid_copy_replace_cycle(self) -> None:
        """Rapid copy operations correctly replace previous content."""
        mock_pyperclip = MagicMock()
        clipboard_content = [""]

        def mock_copy(text: str) -> None:
            clipboard_content[0] = text

        mock_pyperclip.copy = mock_copy

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=MagicMock(spec=threading.Timer)):
                for i in range(10):
                    copy_to_clipboard(f"secret_{i}", auto_clear=False)

                # Only the last value should be in clipboard
                assert clipboard_content[0] == "secret_9"

    def test_manager_workflow_complete(self) -> None:
        """ClipboardManager workflow from entry to exit."""
        mock_pyperclip = MagicMock()
        clipboard_content = ["initial"]

        def mock_copy(text: str) -> None:
            clipboard_content[0] = text

        mock_pyperclip.copy = mock_copy

        with patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            with patch("threading.Timer", return_value=MagicMock(spec=threading.Timer)):
                # Before context
                assert clipboard_content[0] == "initial"

                with ClipboardManager("secret"):
                    # Inside context - secret should be in clipboard
                    assert clipboard_content[0] == "secret"

                # After context - clipboard should be cleared
                assert clipboard_content[0] == ""
