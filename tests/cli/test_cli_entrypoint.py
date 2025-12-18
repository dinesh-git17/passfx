# CLI Entry Point Tests
# Validates process lifecycle: startup, signal handling, and clean shutdown.
# Tests use mocking to simulate signals safely without affecting test runner.

from __future__ import annotations

import signal
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reset_cli_module() -> Generator[None, None, None]:
    """Reset CLI module state between tests."""
    import passfx.cli as cli_module

    original_app = cli_module._app
    yield
    cli_module._app = original_app


@pytest.fixture
def reset_app_module() -> Generator[None, None, None]:
    """Reset app module state between tests."""
    import passfx.app as app_module

    original_instance = app_module._app_instance
    original_shutdown = app_module._shutdown_in_progress
    yield
    app_module._app_instance = original_instance
    app_module._shutdown_in_progress = original_shutdown


@pytest.fixture
def mock_passfx_app() -> Generator[MagicMock, None, None]:
    """Create a mock PassFXApp for testing without UI."""
    with patch("passfx.cli.PassFXApp") as mock_app_class:
        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app._unlocked = False
        mock_app.run = MagicMock()
        mock_app_class.return_value = mock_app
        yield mock_app


@pytest.fixture
def mock_emergency_cleanup() -> Generator[MagicMock, None, None]:
    """Mock emergency_cleanup to track calls without side effects."""
    with patch("passfx.cli.emergency_cleanup") as mock_cleanup:
        yield mock_cleanup


@pytest.fixture
def mock_setproctitle() -> Generator[MagicMock, None, None]:
    """Mock setproctitle to prevent actual process title changes."""
    with patch("passfx.cli.setproctitle") as mock_spt:
        yield mock_spt


@pytest.fixture
def mock_set_terminal_title() -> Generator[MagicMock, None, None]:
    """Mock set_terminal_title to track calls without stdout writes."""
    with patch("passfx.cli.set_terminal_title") as mock_title:
        yield mock_title


# ---------------------------------------------------------------------------
# Startup Behavior Tests
# ---------------------------------------------------------------------------


class TestCliStartup:
    """Tests for CLI startup behavior."""

    @pytest.mark.unit
    def test_main_sets_process_title(
        self,
        reset_cli_module: None,
        mock_passfx_app: MagicMock,
        mock_emergency_cleanup: MagicMock,
        mock_setproctitle: MagicMock,
        mock_set_terminal_title: MagicMock,
    ) -> None:
        """Verify main() sets the process title to 'PassFX'."""
        from passfx.cli import main

        with patch("passfx.cli.signal.signal"):
            main()

        mock_setproctitle.setproctitle.assert_called_once_with("PassFX")

    @pytest.mark.unit
    def test_main_sets_terminal_title(
        self,
        reset_cli_module: None,
        mock_passfx_app: MagicMock,
        mock_emergency_cleanup: MagicMock,
        mock_setproctitle: MagicMock,
        mock_set_terminal_title: MagicMock,
    ) -> None:
        """Verify main() calls set_terminal_title with expected title."""
        from passfx.cli import TERMINAL_TITLE, main

        with patch("passfx.cli.signal.signal"):
            main()

        mock_set_terminal_title.assert_called_once_with(TERMINAL_TITLE)

    @pytest.mark.unit
    def test_main_registers_signal_handlers(
        self,
        reset_cli_module: None,
        mock_passfx_app: MagicMock,
        mock_emergency_cleanup: MagicMock,
        mock_setproctitle: MagicMock,
        mock_set_terminal_title: MagicMock,
    ) -> None:
        """Verify main() registers SIGINT and SIGTERM handlers."""
        from passfx.cli import main

        with patch("passfx.cli.signal.signal") as mock_signal:
            main()

            # Verify both handlers were registered
            calls = mock_signal.call_args_list
            signal_nums = [c[0][0] for c in calls]
            assert signal.SIGINT in signal_nums
            assert signal.SIGTERM in signal_nums

    @pytest.mark.unit
    def test_main_creates_app_instance(
        self,
        reset_cli_module: None,
        mock_passfx_app: MagicMock,
        mock_emergency_cleanup: MagicMock,
        mock_setproctitle: MagicMock,
        mock_set_terminal_title: MagicMock,
    ) -> None:
        """Verify main() creates a PassFXApp instance."""
        from passfx.cli import main

        with patch("passfx.cli.signal.signal"):
            main()

        mock_passfx_app.run.assert_called_once()

    @pytest.mark.unit
    def test_main_returns_zero_on_success(
        self,
        reset_cli_module: None,
        mock_passfx_app: MagicMock,
        mock_emergency_cleanup: MagicMock,
        mock_setproctitle: MagicMock,
        mock_set_terminal_title: MagicMock,
    ) -> None:
        """Verify main() returns 0 on successful exit."""
        from passfx.cli import main

        with patch("passfx.cli.signal.signal"):
            result = main()

        assert result == 0

    @pytest.mark.unit
    def test_set_terminal_title_writes_ansi_sequence(self) -> None:
        """Verify set_terminal_title uses correct ANSI escape format."""
        from passfx.cli import set_terminal_title

        mock_stdout = MagicMock()
        with patch.object(sys, "stdout", mock_stdout):
            set_terminal_title("Test Title")

            mock_stdout.write.assert_called_once_with("\033]0;Test Title\007")
            mock_stdout.flush.assert_called_once()


# ---------------------------------------------------------------------------
# Signal Handling Tests
# ---------------------------------------------------------------------------


class TestSignalHandling:
    """Tests for signal handler behavior without sending real signals."""

    @pytest.mark.unit
    def test_signal_handler_calls_emergency_cleanup(
        self,
        reset_cli_module: None,
    ) -> None:
        """Verify _signal_handler calls emergency_cleanup first."""
        from passfx import cli as cli_module
        from passfx.cli import _signal_handler

        cli_module._app = None

        with patch("passfx.cli.emergency_cleanup") as mock_cleanup:
            with pytest.raises(SystemExit):
                _signal_handler(signal.SIGINT, None)

            mock_cleanup.assert_called_once()

    @pytest.mark.unit
    def test_signal_handler_locks_vault_when_unlocked(
        self,
        reset_cli_module: None,
    ) -> None:
        """Verify _signal_handler locks vault if app is unlocked."""
        from passfx import cli as cli_module
        from passfx.cli import _signal_handler

        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app._unlocked = True
        cli_module._app = mock_app

        with patch("passfx.cli.emergency_cleanup"):
            with pytest.raises(SystemExit):
                _signal_handler(signal.SIGINT, None)

        mock_app.vault.lock.assert_called_once()

    @pytest.mark.unit
    def test_signal_handler_skips_lock_when_no_vault(
        self,
        reset_cli_module: None,
    ) -> None:
        """Verify _signal_handler skips lock if vault is None."""
        from passfx import cli as cli_module
        from passfx.cli import _signal_handler

        mock_app = MagicMock()
        mock_app.vault = None
        mock_app._unlocked = False
        cli_module._app = mock_app

        with patch("passfx.cli.emergency_cleanup"):
            with pytest.raises(SystemExit):
                _signal_handler(signal.SIGINT, None)

        # No assertion on lock - just verify no exception

    @pytest.mark.unit
    def test_signal_handler_skips_lock_when_locked(
        self,
        reset_cli_module: None,
    ) -> None:
        """Verify _signal_handler skips lock if vault is already locked."""
        from passfx import cli as cli_module
        from passfx.cli import _signal_handler

        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app._unlocked = False
        cli_module._app = mock_app

        with patch("passfx.cli.emergency_cleanup"):
            with pytest.raises(SystemExit):
                _signal_handler(signal.SIGINT, None)

        mock_app.vault.lock.assert_not_called()

    @pytest.mark.unit
    def test_signal_handler_sigint_exit_code(
        self,
        reset_cli_module: None,
    ) -> None:
        """Verify SIGINT results in exit code 130 (128 + 2)."""
        from passfx import cli as cli_module
        from passfx.cli import _signal_handler

        cli_module._app = None

        with patch("passfx.cli.emergency_cleanup"):
            with pytest.raises(SystemExit) as exc_info:
                _signal_handler(signal.SIGINT, None)

        assert exc_info.value.code == 130  # 128 + SIGINT(2)

    @pytest.mark.unit
    def test_signal_handler_sigterm_exit_code(
        self,
        reset_cli_module: None,
    ) -> None:
        """Verify SIGTERM results in exit code 143 (128 + 15)."""
        from passfx import cli as cli_module
        from passfx.cli import _signal_handler

        cli_module._app = None

        with patch("passfx.cli.emergency_cleanup"):
            with pytest.raises(SystemExit) as exc_info:
                _signal_handler(signal.SIGTERM, None)

        assert exc_info.value.code == 143  # 128 + SIGTERM(15)

    @pytest.mark.unit
    def test_signal_handler_suppresses_lock_exceptions(
        self,
        reset_cli_module: None,
    ) -> None:
        """Verify _signal_handler suppresses exceptions from vault.lock()."""
        from passfx import cli as cli_module
        from passfx.cli import _signal_handler

        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app.vault.lock.side_effect = RuntimeError("Lock failed")
        mock_app._unlocked = True
        cli_module._app = mock_app

        with patch("passfx.cli.emergency_cleanup"):
            # Should not raise despite lock failure
            with pytest.raises(SystemExit) as exc_info:
                _signal_handler(signal.SIGINT, None)

        # Exit should still happen with correct code
        assert exc_info.value.code == 130

    @pytest.mark.unit
    def test_setup_signal_handlers_registers_both_signals(self) -> None:
        """Verify _setup_signal_handlers registers SIGINT and SIGTERM."""
        from passfx.cli import _setup_signal_handlers

        with patch("passfx.cli.signal.signal") as mock_signal:
            _setup_signal_handlers()

            # Both signals should be registered
            assert mock_signal.call_count == 2
            signal_nums = [c[0][0] for c in mock_signal.call_args_list]
            assert signal.SIGINT in signal_nums
            assert signal.SIGTERM in signal_nums


# ---------------------------------------------------------------------------
# Exit Safety Tests
# ---------------------------------------------------------------------------


class TestExitSafety:
    """Tests verifying cleanup on all exit paths."""

    @pytest.mark.unit
    def test_main_cleanup_in_finally_block(
        self,
        reset_cli_module: None,
        mock_setproctitle: MagicMock,
        mock_set_terminal_title: MagicMock,
    ) -> None:
        """Verify emergency_cleanup is called in finally block."""
        with patch("passfx.cli.PassFXApp") as mock_app_class:
            mock_app = MagicMock()
            mock_app.vault = None
            mock_app._unlocked = False
            mock_app.run = MagicMock()
            mock_app_class.return_value = mock_app

            with patch("passfx.cli.emergency_cleanup") as mock_cleanup:
                with patch("passfx.cli.signal.signal"):
                    from passfx.cli import main

                    main()

                # Cleanup should be called in finally
                mock_cleanup.assert_called()

    @pytest.mark.unit
    def test_main_locks_vault_on_exit_when_unlocked(
        self,
        reset_cli_module: None,
        mock_setproctitle: MagicMock,
        mock_set_terminal_title: MagicMock,
    ) -> None:
        """Verify vault is locked in finally block when unlocked."""
        with patch("passfx.cli.PassFXApp") as mock_app_class:
            mock_app = MagicMock()
            mock_app.vault = MagicMock()
            mock_app._unlocked = True
            mock_app.run = MagicMock()
            mock_app_class.return_value = mock_app

            with patch("passfx.cli.emergency_cleanup"):
                with patch("passfx.cli.signal.signal"):
                    from passfx.cli import main

                    main()

            mock_app.vault.lock.assert_called_once()

    @pytest.mark.unit
    def test_main_skips_lock_when_vault_locked(
        self,
        reset_cli_module: None,
        mock_setproctitle: MagicMock,
        mock_set_terminal_title: MagicMock,
    ) -> None:
        """Verify vault.lock() not called when vault is already locked."""
        with patch("passfx.cli.PassFXApp") as mock_app_class:
            mock_app = MagicMock()
            mock_app.vault = MagicMock()
            mock_app._unlocked = False
            mock_app.run = MagicMock()
            mock_app_class.return_value = mock_app

            with patch("passfx.cli.emergency_cleanup"):
                with patch("passfx.cli.signal.signal"):
                    from passfx.cli import main

                    main()

            mock_app.vault.lock.assert_not_called()

    @pytest.mark.unit
    def test_main_cleanup_runs_on_app_exception(
        self,
        reset_cli_module: None,
        mock_setproctitle: MagicMock,
        mock_set_terminal_title: MagicMock,
    ) -> None:
        """Verify cleanup runs even when app.run() raises."""
        with patch("passfx.cli.PassFXApp") as mock_app_class:
            mock_app = MagicMock()
            mock_app.vault = MagicMock()
            mock_app._unlocked = True
            mock_app.run.side_effect = RuntimeError("App crashed")
            mock_app_class.return_value = mock_app

            with patch("passfx.cli.emergency_cleanup") as mock_cleanup:
                with patch("passfx.cli.signal.signal"):
                    from passfx.cli import main

                    with pytest.raises(RuntimeError, match="App crashed"):
                        main()

                # Cleanup should still be called despite exception
                mock_cleanup.assert_called()
                mock_app.vault.lock.assert_called_once()

    @pytest.mark.unit
    def test_main_suppresses_lock_exception_in_finally(
        self,
        reset_cli_module: None,
        mock_setproctitle: MagicMock,
        mock_set_terminal_title: MagicMock,
    ) -> None:
        """Verify exceptions from vault.lock() in finally are suppressed."""
        with patch("passfx.cli.PassFXApp") as mock_app_class:
            mock_app = MagicMock()
            mock_app.vault = MagicMock()
            mock_app.vault.lock.side_effect = RuntimeError("Lock failed")
            mock_app._unlocked = True
            mock_app.run = MagicMock()
            mock_app_class.return_value = mock_app

            with patch("passfx.cli.emergency_cleanup"):
                with patch("passfx.cli.signal.signal"):
                    from passfx.cli import main

                    # Should not raise despite lock failure
                    result = main()

            assert result == 0

    @pytest.mark.unit
    def test_cleanup_order_clipboard_before_vault_in_signal(
        self,
        reset_cli_module: None,
    ) -> None:
        """Verify clipboard cleared before vault locked in signal handler."""
        from passfx import cli as cli_module
        from passfx.cli import _signal_handler

        call_order: list[str] = []

        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app.vault.lock.side_effect = lambda: call_order.append("vault_lock")
        mock_app._unlocked = True
        cli_module._app = mock_app

        with patch(
            "passfx.cli.emergency_cleanup",
            side_effect=lambda: call_order.append("clipboard_clear"),
        ):
            with pytest.raises(SystemExit):
                _signal_handler(signal.SIGINT, None)

        # Clipboard should be cleared first (critical for security)
        assert call_order == ["clipboard_clear", "vault_lock"]


# ---------------------------------------------------------------------------
# App Module Signal Handling Tests
# ---------------------------------------------------------------------------


class TestAppModuleShutdown:
    """Tests for app.py graceful shutdown functionality."""

    @pytest.mark.unit
    def test_graceful_shutdown_sets_flag(
        self,
        reset_app_module: None,
    ) -> None:
        """Verify _graceful_shutdown sets shutdown flag."""
        import passfx.app as app_module

        app_module._shutdown_in_progress = False
        app_module._app_instance = None

        with patch("passfx.app.emergency_cleanup"):
            with pytest.raises(SystemExit):
                app_module._graceful_shutdown(signal.SIGINT, None)

        assert app_module._shutdown_in_progress is True

    @pytest.mark.unit
    def test_graceful_shutdown_idempotent(
        self,
        reset_app_module: None,
    ) -> None:
        """Verify _graceful_shutdown only runs once."""
        import passfx.app as app_module

        app_module._shutdown_in_progress = True
        app_module._app_instance = None

        # Should return immediately without calling cleanup
        with patch("passfx.app.emergency_cleanup") as mock_cleanup:
            # No SystemExit should be raised
            app_module._graceful_shutdown(signal.SIGINT, None)
            mock_cleanup.assert_not_called()

    @pytest.mark.unit
    def test_graceful_shutdown_locks_vault(
        self,
        reset_app_module: None,
    ) -> None:
        """Verify _graceful_shutdown locks vault when unlocked."""
        import passfx.app as app_module

        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app._unlocked = True
        app_module._app_instance = mock_app
        app_module._shutdown_in_progress = False

        with patch("passfx.app.emergency_cleanup"):
            with pytest.raises(SystemExit):
                app_module._graceful_shutdown(signal.SIGINT, None)

        mock_app.vault.lock.assert_called_once()

    @pytest.mark.unit
    def test_graceful_shutdown_clears_clipboard(
        self,
        reset_app_module: None,
    ) -> None:
        """Verify _graceful_shutdown calls emergency_cleanup."""
        import passfx.app as app_module

        app_module._app_instance = None
        app_module._shutdown_in_progress = False

        with patch("passfx.app.emergency_cleanup") as mock_cleanup:
            with pytest.raises(SystemExit):
                app_module._graceful_shutdown(signal.SIGINT, None)

        mock_cleanup.assert_called_once()

    @pytest.mark.unit
    def test_graceful_shutdown_suppresses_vault_exceptions(
        self,
        reset_app_module: None,
    ) -> None:
        """Verify _graceful_shutdown suppresses vault.lock() exceptions."""
        import passfx.app as app_module

        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app.vault.lock.side_effect = RuntimeError("Lock failed")
        mock_app._unlocked = True
        app_module._app_instance = mock_app
        app_module._shutdown_in_progress = False

        with patch("passfx.app.emergency_cleanup"):
            # Should not raise despite lock failure
            with pytest.raises(SystemExit) as exc_info:
                app_module._graceful_shutdown(signal.SIGINT, None)

        assert exc_info.value.code == 0

    @pytest.mark.unit
    def test_graceful_shutdown_suppresses_cleanup_exceptions(
        self,
        reset_app_module: None,
    ) -> None:
        """Verify _graceful_shutdown suppresses emergency_cleanup exceptions."""
        import passfx.app as app_module

        app_module._app_instance = None
        app_module._shutdown_in_progress = False

        with patch(
            "passfx.app.emergency_cleanup",
            side_effect=RuntimeError("Cleanup failed"),
        ):
            # Should not raise despite cleanup failure
            with pytest.raises(SystemExit) as exc_info:
                app_module._graceful_shutdown(signal.SIGINT, None)

        assert exc_info.value.code == 0

    @pytest.mark.unit
    def test_cleanup_on_exit_sets_flag(
        self,
        reset_app_module: None,
    ) -> None:
        """Verify _cleanup_on_exit sets shutdown flag."""
        import passfx.app as app_module

        app_module._shutdown_in_progress = False
        app_module._app_instance = None

        with patch("passfx.app.clear_clipboard"):
            app_module._cleanup_on_exit()

        assert app_module._shutdown_in_progress is True

    @pytest.mark.unit
    def test_cleanup_on_exit_idempotent(
        self,
        reset_app_module: None,
    ) -> None:
        """Verify _cleanup_on_exit only runs once."""
        import passfx.app as app_module

        app_module._shutdown_in_progress = True
        app_module._app_instance = None

        with patch("passfx.app.clear_clipboard") as mock_clear:
            app_module._cleanup_on_exit()
            mock_clear.assert_not_called()

    @pytest.mark.unit
    def test_cleanup_on_exit_locks_vault(
        self,
        reset_app_module: None,
    ) -> None:
        """Verify _cleanup_on_exit locks vault when unlocked."""
        import passfx.app as app_module

        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app._unlocked = True
        app_module._app_instance = mock_app
        app_module._shutdown_in_progress = False

        with patch("passfx.app.clear_clipboard"):
            app_module._cleanup_on_exit()

        mock_app.vault.lock.assert_called_once()

    @pytest.mark.unit
    def test_cleanup_on_exit_clears_clipboard(
        self,
        reset_app_module: None,
    ) -> None:
        """Verify _cleanup_on_exit calls clear_clipboard."""
        import passfx.app as app_module

        app_module._app_instance = None
        app_module._shutdown_in_progress = False

        with patch("passfx.app.clear_clipboard") as mock_clear:
            app_module._cleanup_on_exit()

        mock_clear.assert_called_once()

    @pytest.mark.unit
    def test_register_signal_handlers_registers_both(self) -> None:
        """Verify _register_signal_handlers registers SIGINT and SIGTERM."""
        from passfx.app import _register_signal_handlers

        with patch("passfx.app.signal.signal") as mock_signal:
            _register_signal_handlers()

            assert mock_signal.call_count == 2
            signal_nums = [c[0][0] for c in mock_signal.call_args_list]
            assert signal.SIGINT in signal_nums
            assert signal.SIGTERM in signal_nums


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for error handling and exit codes."""

    @pytest.mark.unit
    def test_main_normal_exit_code_zero(
        self,
        reset_cli_module: None,
        mock_passfx_app: MagicMock,
        mock_emergency_cleanup: MagicMock,
        mock_setproctitle: MagicMock,
        mock_set_terminal_title: MagicMock,
    ) -> None:
        """Verify normal exit returns code 0."""
        from passfx.cli import main

        with patch("passfx.cli.signal.signal"):
            exit_code = main()

        assert exit_code == 0

    @pytest.mark.unit
    def test_signal_exit_codes_are_standard_unix(
        self,
        reset_cli_module: None,
    ) -> None:
        """Verify signal exit codes follow Unix convention (128 + signum)."""
        from passfx import cli as cli_module
        from passfx.cli import _signal_handler

        cli_module._app = None

        test_cases = [
            (signal.SIGINT, 130),  # 128 + 2
            (signal.SIGTERM, 143),  # 128 + 15
        ]

        for sig, expected_code in test_cases:
            with patch("passfx.cli.emergency_cleanup"):
                with pytest.raises(SystemExit) as exc_info:
                    _signal_handler(sig, None)

            assert (
                exc_info.value.code == expected_code
            ), f"Signal {sig} should exit with code {expected_code}"

    @pytest.mark.unit
    def test_app_graceful_shutdown_exits_zero(
        self,
        reset_app_module: None,
    ) -> None:
        """Verify app graceful shutdown exits with code 0."""
        import passfx.app as app_module

        app_module._app_instance = None
        app_module._shutdown_in_progress = False

        with patch("passfx.app.emergency_cleanup"):
            with pytest.raises(SystemExit) as exc_info:
                app_module._graceful_shutdown(signal.SIGINT, None)

        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# Module State Tests
# ---------------------------------------------------------------------------


class TestModuleState:
    """Tests for module-level state management."""

    @pytest.mark.unit
    def test_cli_app_initially_none(self) -> None:
        """Verify _app starts as None before main() is called."""
        # Fresh import to get initial state
        import importlib

        import passfx.cli as cli_module

        importlib.reload(cli_module)
        assert cli_module._app is None

    @pytest.mark.unit
    def test_app_instance_initially_none(self) -> None:
        """Verify _app_instance starts as None before run() is called."""
        import importlib

        import passfx.app as app_module

        importlib.reload(app_module)
        assert app_module._app_instance is None

    @pytest.mark.unit
    def test_shutdown_flag_initially_false(self) -> None:
        """Verify _shutdown_in_progress starts as False."""
        import importlib

        import passfx.app as app_module

        importlib.reload(app_module)
        assert app_module._shutdown_in_progress is False

    @pytest.mark.unit
    def test_cli_terminal_title_constant(self) -> None:
        """Verify TERMINAL_TITLE constant is defined."""
        from passfx.cli import TERMINAL_TITLE

        assert isinstance(TERMINAL_TITLE, str)
        assert len(TERMINAL_TITLE) > 0
        assert "PASSFX" in TERMINAL_TITLE


# ---------------------------------------------------------------------------
# Integration-like Tests (Still Unit, but More Complete)
# ---------------------------------------------------------------------------


class TestCliLifecycleIntegration:
    """Tests verifying complete lifecycle paths."""

    @pytest.mark.unit
    def test_full_startup_to_shutdown_sequence(
        self,
        reset_cli_module: None,
        mock_setproctitle: MagicMock,
        mock_set_terminal_title: MagicMock,
    ) -> None:
        """Verify complete startup -> run -> shutdown sequence."""
        with patch("passfx.cli.PassFXApp") as mock_app_class:
            mock_app = MagicMock()
            mock_app.vault = MagicMock()
            mock_app._unlocked = True
            mock_app.run = MagicMock()
            mock_app_class.return_value = mock_app

            cleanup_called = []

            def track_cleanup() -> None:
                cleanup_called.append("cleanup")

            with patch(
                "passfx.cli.emergency_cleanup", side_effect=track_cleanup
            ) as mock_cleanup:
                with patch("passfx.cli.signal.signal") as mock_signal:
                    from passfx.cli import main

                    result = main()

                    # Verify sequence
                    assert mock_setproctitle.setproctitle.called
                    assert mock_set_terminal_title.called
                    assert mock_signal.call_count == 2
                    assert mock_app_class.called
                    assert mock_app.run.called
                    assert mock_cleanup.called
                    assert mock_app.vault.lock.called
                    assert result == 0

    @pytest.mark.unit
    def test_signal_during_unlocked_state(
        self,
        reset_cli_module: None,
    ) -> None:
        """Verify signal handling when vault is unlocked."""
        from passfx import cli as cli_module
        from passfx.cli import _signal_handler

        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app._unlocked = True
        cli_module._app = mock_app

        cleanup_sequence: list[str] = []

        with patch(
            "passfx.cli.emergency_cleanup",
            side_effect=lambda: cleanup_sequence.append("cleanup"),
        ):
            mock_app.vault.lock.side_effect = lambda: cleanup_sequence.append("lock")
            with pytest.raises(SystemExit) as exc_info:
                _signal_handler(signal.SIGINT, None)

        # Verify cleanup happened before lock
        assert cleanup_sequence == ["cleanup", "lock"]
        assert exc_info.value.code == 130

    @pytest.mark.unit
    def test_multiple_signal_handling_attempts(
        self,
        reset_app_module: None,
    ) -> None:
        """Verify multiple signals are handled idempotently."""
        import passfx.app as app_module

        app_module._shutdown_in_progress = False
        app_module._app_instance = None

        call_count = 0

        def count_calls() -> None:
            nonlocal call_count
            call_count += 1

        with patch("passfx.app.emergency_cleanup", side_effect=count_calls):
            # First call should run cleanup
            with pytest.raises(SystemExit):
                app_module._graceful_shutdown(signal.SIGINT, None)

            # Second call should be no-op (flag is set)
            app_module._graceful_shutdown(signal.SIGINT, None)

        # Only one cleanup should have run
        assert call_count == 1
