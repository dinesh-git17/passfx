# Application Lifecycle Tests
# Validates PassFXApp initialization, state transitions, cleanup guarantees,
# and error handling. Tests focus on application logic, not UI rendering.

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


def run_async(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reset_app_module_state() -> Generator[None, None, None]:
    """Reset app module state between tests."""
    import passfx.app as app_module

    original_instance = app_module._app_instance
    original_shutdown = app_module._shutdown_in_progress
    yield
    app_module._app_instance = original_instance
    app_module._shutdown_in_progress = original_shutdown


@pytest.fixture
def mock_vault() -> Generator[MagicMock, None, None]:
    """Create a mock Vault for testing without filesystem."""
    mock = MagicMock()
    mock.is_locked = True
    mock.exists = False
    mock.lock = MagicMock()
    mock.unlock = MagicMock()
    mock.create = MagicMock()
    return mock


@pytest.fixture
def isolated_app(mock_vault: MagicMock):
    """Create an isolated PassFXApp instance for testing.

    Uses mocking to prevent actual UI rendering or filesystem access.
    """
    with patch("passfx.app.Vault", return_value=mock_vault):
        from passfx.app import PassFXApp

        app = PassFXApp()
        yield app


@pytest.fixture
def temp_vault_environment(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary environment for vault operations."""
    vault_dir = temp_dir / ".passfx"
    vault_dir.mkdir(mode=0o700)
    yield vault_dir


# ---------------------------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------------------------


class TestAppInitialization:
    """Tests for PassFXApp initialization behavior."""

    @pytest.mark.unit
    def test_app_creates_vault_instance(self) -> None:
        """Verify PassFXApp creates a Vault on initialization."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()

            mock_vault_class.assert_called_once()
            assert app.vault is mock_vault

    @pytest.mark.unit
    def test_app_initializes_unlocked_false(self) -> None:
        """Verify PassFXApp starts with _unlocked = False."""
        with patch("passfx.app.Vault"):
            from passfx.app import PassFXApp

            app = PassFXApp()

            assert app._unlocked is False

    @pytest.mark.unit
    def test_app_inherits_from_textual_app(self) -> None:
        """Verify PassFXApp is a proper Textual App subclass."""
        with patch("passfx.app.Vault"):
            from textual.app import App

            from passfx.app import PassFXApp

            app = PassFXApp()

            assert isinstance(app, App)

    @pytest.mark.unit
    def test_app_defines_required_bindings(self) -> None:
        """Verify PassFXApp defines essential key bindings."""
        from textual.binding import Binding

        from passfx.app import PassFXApp

        binding_keys = [
            b.key if isinstance(b, Binding) else b[0] for b in PassFXApp.BINDINGS
        ]

        assert "ctrl+c" in binding_keys
        assert "q" in binding_keys
        assert "escape" in binding_keys

    @pytest.mark.unit
    def test_app_defines_css_path(self) -> None:
        """Verify PassFXApp has CSS_PATH defined."""
        from passfx.app import PassFXApp

        assert hasattr(PassFXApp, "CSS_PATH")
        assert PassFXApp.CSS_PATH is not None

    @pytest.mark.unit
    def test_app_defines_title(self) -> None:
        """Verify PassFXApp has a title defined."""
        from passfx.app import PassFXApp

        assert hasattr(PassFXApp, "TITLE")
        assert "PASSFX" in PassFXApp.TITLE

    @pytest.mark.unit
    def test_app_registers_login_screen(self) -> None:
        """Verify PassFXApp registers the login screen."""
        from passfx.app import PassFXApp

        assert "login" in PassFXApp.SCREENS

    @pytest.mark.unit
    def test_multiple_app_instances_independent(self) -> None:
        """Verify multiple PassFXApp instances have independent state."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault_1 = MagicMock()
            mock_vault_2 = MagicMock()
            mock_vault_class.side_effect = [mock_vault_1, mock_vault_2]

            from passfx.app import PassFXApp

            app1 = PassFXApp()
            app2 = PassFXApp()

            assert app1.vault is not app2.vault
            assert app1._unlocked is False
            assert app2._unlocked is False


# ---------------------------------------------------------------------------
# State Management Tests
# ---------------------------------------------------------------------------


class TestStateManagement:
    """Tests for application state management."""

    @pytest.mark.unit
    def test_initial_state_is_locked(self, isolated_app: MagicMock) -> None:
        """Verify app starts in locked state."""
        assert isolated_app._unlocked is False

    @pytest.mark.unit
    def test_unlock_vault_success_sets_unlocked(self) -> None:
        """Verify successful unlock sets _unlocked to True."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.unlock = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            result = app.unlock_vault("test_password")

            assert result is True
            assert app._unlocked is True
            mock_vault.unlock.assert_called_once_with("test_password")

    @pytest.mark.unit
    def test_unlock_vault_failure_keeps_locked(self) -> None:
        """Verify failed unlock keeps _unlocked as False."""
        from passfx.core.vault import VaultError

        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.unlock.side_effect = VaultError("Wrong password")
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            result = app.unlock_vault("wrong_password")

            assert result is False
            assert app._unlocked is False

    @pytest.mark.unit
    def test_unlock_vault_handles_crypto_error(self) -> None:
        """Verify unlock handles CryptoError gracefully."""
        from passfx.core.crypto import CryptoError

        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.unlock.side_effect = CryptoError("Decryption failed")
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            result = app.unlock_vault("test_password")

            assert result is False
            assert app._unlocked is False

    @pytest.mark.unit
    def test_create_vault_success_sets_unlocked(self) -> None:
        """Verify successful vault creation sets _unlocked to True."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.create = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            result = app.create_vault("strong_password")

            assert result is True
            assert app._unlocked is True
            mock_vault.create.assert_called_once_with("strong_password")

    @pytest.mark.unit
    def test_create_vault_failure_keeps_locked(self) -> None:
        """Verify failed vault creation keeps _unlocked as False."""
        from passfx.core.vault import VaultError

        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.create.side_effect = VaultError("Vault exists")
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            result = app.create_vault("test_password")

            assert result is False
            assert app._unlocked is False

    @pytest.mark.unit
    def test_state_consistency_after_multiple_unlock_attempts(self) -> None:
        """Verify state remains consistent after multiple unlock attempts."""
        from passfx.core.vault import VaultError

        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            # First call fails, second succeeds
            mock_vault.unlock.side_effect = [
                VaultError("Wrong"),
                None,
            ]
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()

            # First attempt fails
            result1 = app.unlock_vault("wrong")
            assert result1 is False
            assert app._unlocked is False

            # Second attempt succeeds
            result2 = app.unlock_vault("correct")
            assert result2 is True
            assert app._unlocked is True


# ---------------------------------------------------------------------------
# Lifecycle Tests
# ---------------------------------------------------------------------------


class TestAppLifecycle:
    """Tests for application lifecycle hooks."""

    @pytest.mark.unit
    def test_on_mount_pushes_login_screen(self) -> None:
        """Verify on_mount pushes the login screen."""
        with patch("passfx.app.Vault"):
            from passfx.app import PassFXApp

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]
            app.set_interval = MagicMock()  # type: ignore[method-assign]

            app.on_mount()

            app.push_screen.assert_called_once_with("login")
            # Verify auto-lock timer is started
            app.set_interval.assert_called_once()

    @pytest.mark.unit
    def test_action_quit_locks_vault_when_unlocked(self) -> None:
        """Verify action_quit locks vault if unlocked."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = True
            app.exit = MagicMock()  # type: ignore[method-assign]

            run_async(app.action_quit())

            mock_vault.lock.assert_called_once()
            app.exit.assert_called_once()

    @pytest.mark.unit
    def test_action_quit_skips_lock_when_locked(self) -> None:
        """Verify action_quit skips lock if already locked."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = False
            app.exit = MagicMock()  # type: ignore[method-assign]

            run_async(app.action_quit())

            mock_vault.lock.assert_not_called()
            app.exit.assert_called_once()

    @pytest.mark.unit
    def test_action_quit_handles_none_vault(self) -> None:
        """Verify action_quit handles None vault gracefully."""
        with patch("passfx.app.Vault"):
            from passfx.app import PassFXApp

            app = PassFXApp()
            app.vault = None  # type: ignore[assignment]
            app._unlocked = True
            app.exit = MagicMock()  # type: ignore[method-assign]

            # Should not raise
            run_async(app.action_quit())

            app.exit.assert_called_once()

    @pytest.mark.unit
    def test_action_back_binding_exists(self) -> None:
        """Verify action_back is properly bound to escape key."""
        from textual.binding import Binding

        from passfx.app import PassFXApp

        binding_keys = [
            b.key if isinstance(b, Binding) else b[0] for b in PassFXApp.BINDINGS
        ]
        binding_actions = [
            b.action if isinstance(b, Binding) else b[1] for b in PassFXApp.BINDINGS
        ]

        assert "escape" in binding_keys
        assert "back" in binding_actions

    @pytest.mark.unit
    def test_action_quit_binding_exists(self) -> None:
        """Verify action_quit is properly bound."""
        from textual.binding import Binding

        from passfx.app import PassFXApp

        binding_keys = [
            b.key if isinstance(b, Binding) else b[0] for b in PassFXApp.BINDINGS
        ]
        binding_actions = [
            b.action if isinstance(b, Binding) else b[1] for b in PassFXApp.BINDINGS
        ]

        assert "ctrl+c" in binding_keys or "q" in binding_keys
        assert "quit" in binding_actions

    @pytest.mark.unit
    def test_screen_registration_includes_login(self) -> None:
        """Verify login screen is registered in SCREENS."""
        from passfx.app import PassFXApp
        from passfx.screens.login import LoginScreen

        assert "login" in PassFXApp.SCREENS
        assert PassFXApp.SCREENS["login"] == LoginScreen


# ---------------------------------------------------------------------------
# Cleanup Guarantee Tests
# ---------------------------------------------------------------------------


class TestCleanupGuarantees:
    """Tests verifying cleanup always runs."""

    @pytest.mark.unit
    def test_vault_locked_on_graceful_shutdown(
        self, reset_app_module_state: None
    ) -> None:
        """Verify vault is locked during graceful shutdown."""
        import passfx.app as app_module

        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app._unlocked = True
        app_module._app_instance = mock_app
        app_module._shutdown_in_progress = False

        with patch("passfx.app.emergency_cleanup"):
            with pytest.raises(SystemExit):
                app_module._graceful_shutdown(2, None)

        mock_app.vault.lock.assert_called_once()

    @pytest.mark.unit
    def test_clipboard_cleared_on_graceful_shutdown(
        self, reset_app_module_state: None
    ) -> None:
        """Verify clipboard is cleared during graceful shutdown."""
        import passfx.app as app_module

        app_module._app_instance = None
        app_module._shutdown_in_progress = False

        with patch("passfx.app.emergency_cleanup") as mock_cleanup:
            with pytest.raises(SystemExit):
                app_module._graceful_shutdown(2, None)

        mock_cleanup.assert_called_once()

    @pytest.mark.unit
    def test_cleanup_runs_on_atexit(self, reset_app_module_state: None) -> None:
        """Verify _cleanup_on_exit locks vault and clears clipboard."""
        import passfx.app as app_module

        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app._unlocked = True
        app_module._app_instance = mock_app
        app_module._shutdown_in_progress = False

        with patch("passfx.app.clear_clipboard") as mock_clear:
            app_module._cleanup_on_exit()

        mock_app.vault.lock.assert_called_once()
        mock_clear.assert_called_once()

    @pytest.mark.unit
    def test_cleanup_idempotent_via_flag(self, reset_app_module_state: None) -> None:
        """Verify cleanup only runs once via shutdown flag."""
        import passfx.app as app_module

        app_module._app_instance = None
        app_module._shutdown_in_progress = True

        with patch("passfx.app.clear_clipboard") as mock_clear:
            app_module._cleanup_on_exit()

        mock_clear.assert_not_called()

    @pytest.mark.unit
    def test_cleanup_suppresses_vault_exceptions(
        self, reset_app_module_state: None
    ) -> None:
        """Verify cleanup suppresses exceptions from vault.lock()."""
        import passfx.app as app_module

        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app.vault.lock.side_effect = RuntimeError("Lock failed")
        mock_app._unlocked = True
        app_module._app_instance = mock_app
        app_module._shutdown_in_progress = False

        with patch("passfx.app.clear_clipboard"):
            # Should not raise
            app_module._cleanup_on_exit()

        # Verify flag is still set despite exception
        assert app_module._shutdown_in_progress is True

    @pytest.mark.unit
    def test_cleanup_suppresses_clipboard_exceptions(
        self, reset_app_module_state: None
    ) -> None:
        """Verify cleanup suppresses exceptions from clipboard clear."""
        import passfx.app as app_module

        app_module._app_instance = None
        app_module._shutdown_in_progress = False

        with patch(
            "passfx.app.clear_clipboard",
            side_effect=RuntimeError("Clipboard failed"),
        ):
            # Should not raise
            app_module._cleanup_on_exit()

        assert app_module._shutdown_in_progress is True

    @pytest.mark.unit
    def test_graceful_shutdown_handles_none_app_instance(
        self, reset_app_module_state: None
    ) -> None:
        """Verify graceful shutdown handles None app instance."""
        import passfx.app as app_module

        app_module._app_instance = None
        app_module._shutdown_in_progress = False

        with patch("passfx.app.emergency_cleanup"):
            with pytest.raises(SystemExit):
                app_module._graceful_shutdown(2, None)

        assert app_module._shutdown_in_progress is True

    @pytest.mark.unit
    def test_graceful_shutdown_handles_none_vault(
        self, reset_app_module_state: None
    ) -> None:
        """Verify graceful shutdown handles None vault."""
        import passfx.app as app_module

        mock_app = MagicMock()
        mock_app.vault = None
        mock_app._unlocked = True
        app_module._app_instance = mock_app
        app_module._shutdown_in_progress = False

        with patch("passfx.app.emergency_cleanup"):
            # Should not raise
            with pytest.raises(SystemExit):
                app_module._graceful_shutdown(2, None)


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for error handling in application operations."""

    @pytest.mark.unit
    def test_unlock_catches_vault_error(self) -> None:
        """Verify unlock_vault catches VaultError and returns False."""
        from passfx.core.vault import VaultError

        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.unlock.side_effect = VaultError("Test error")
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            result = app.unlock_vault("password")

            assert result is False
            assert app._unlocked is False

    @pytest.mark.unit
    def test_unlock_catches_crypto_error(self) -> None:
        """Verify unlock_vault catches CryptoError and returns False."""
        from passfx.core.crypto import CryptoError

        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.unlock.side_effect = CryptoError("Test error")
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            result = app.unlock_vault("password")

            assert result is False

    @pytest.mark.unit
    def test_create_catches_vault_error(self) -> None:
        """Verify create_vault catches VaultError and returns False."""
        from passfx.core.vault import VaultError

        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.create.side_effect = VaultError("Vault exists")
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            result = app.create_vault("password")

            assert result is False
            assert app._unlocked is False

    @pytest.mark.unit
    def test_app_does_not_expose_sensitive_data_on_error(self) -> None:
        """Verify errors don't expose sensitive data."""
        from passfx.core.vault import VaultError

        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.unlock.side_effect = VaultError("Wrong password")
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()

            # Method returns boolean, not exception details
            result = app.unlock_vault("secret_password")

            assert result is False
            # Verify password is not stored anywhere accessible
            assert not hasattr(app, "_password")
            assert not hasattr(app, "password")


# ---------------------------------------------------------------------------
# Run Function Tests
# ---------------------------------------------------------------------------


class TestRunFunction:
    """Tests for the run() entry point function."""

    @pytest.mark.unit
    def test_run_registers_signal_handlers(self, reset_app_module_state: None) -> None:
        """Verify run() registers signal handlers before creating app."""
        import signal

        with patch("passfx.app.PassFXApp") as mock_app_class:
            mock_app = MagicMock()
            mock_app.run = MagicMock()
            mock_app_class.return_value = mock_app

            with patch("passfx.app.signal.signal") as mock_signal:
                with patch("passfx.app.atexit.register"):
                    with patch("passfx.app._cleanup_on_exit"):
                        from passfx.app import run

                        run()

                # Verify signal handlers were registered
                signal_nums = [c[0][0] for c in mock_signal.call_args_list]
                assert signal.SIGINT in signal_nums
                assert signal.SIGTERM in signal_nums

    @pytest.mark.unit
    def test_run_registers_atexit_handler(self, reset_app_module_state: None) -> None:
        """Verify run() registers atexit cleanup handler."""
        with patch("passfx.app.PassFXApp") as mock_app_class:
            mock_app = MagicMock()
            mock_app.run = MagicMock()
            mock_app_class.return_value = mock_app

            with patch("passfx.app.signal.signal"):
                with patch("passfx.app.atexit.register") as mock_atexit:
                    with patch("passfx.app._cleanup_on_exit"):
                        from passfx.app import run

                        run()

                mock_atexit.assert_called()

    @pytest.mark.unit
    def test_run_sets_app_instance(self, reset_app_module_state: None) -> None:
        """Verify run() sets module-level _app_instance."""
        import passfx.app as app_module

        with patch("passfx.app.PassFXApp") as mock_app_class:
            mock_app = MagicMock()
            mock_app.run = MagicMock()
            mock_app_class.return_value = mock_app

            with patch("passfx.app.signal.signal"):
                with patch("passfx.app.atexit.register"):
                    with patch("passfx.app._cleanup_on_exit"):
                        app_module.run()

            assert app_module._app_instance is mock_app

    @pytest.mark.unit
    def test_run_calls_app_run(self, reset_app_module_state: None) -> None:
        """Verify run() calls app.run()."""
        with patch("passfx.app.PassFXApp") as mock_app_class:
            mock_app = MagicMock()
            mock_app.run = MagicMock()
            mock_app_class.return_value = mock_app

            with patch("passfx.app.signal.signal"):
                with patch("passfx.app.atexit.register"):
                    with patch("passfx.app._cleanup_on_exit"):
                        from passfx.app import run

                        run()

            mock_app.run.assert_called_once()

    @pytest.mark.unit
    def test_run_cleanup_in_finally(self, reset_app_module_state: None) -> None:
        """Verify run() calls cleanup in finally block."""
        with patch("passfx.app.PassFXApp") as mock_app_class:
            mock_app = MagicMock()
            mock_app.run = MagicMock()
            mock_app_class.return_value = mock_app

            with patch("passfx.app.signal.signal"):
                with patch("passfx.app.atexit.register"):
                    with patch("passfx.app._cleanup_on_exit") as mock_cleanup:
                        from passfx.app import run

                        run()

                    mock_cleanup.assert_called()

    @pytest.mark.unit
    def test_run_cleanup_runs_on_exception(self, reset_app_module_state: None) -> None:
        """Verify run() cleanup runs even on exception."""
        with patch("passfx.app.PassFXApp") as mock_app_class:
            mock_app = MagicMock()
            mock_app.run.side_effect = RuntimeError("App crashed")
            mock_app_class.return_value = mock_app

            with patch("passfx.app.signal.signal"):
                with patch("passfx.app.atexit.register"):
                    with patch("passfx.app._cleanup_on_exit") as mock_cleanup:
                        from passfx.app import run

                        with pytest.raises(RuntimeError):
                            run()

                    mock_cleanup.assert_called()


# ---------------------------------------------------------------------------
# Module State Tests
# ---------------------------------------------------------------------------


class TestModuleState:
    """Tests for module-level state variables."""

    @pytest.mark.unit
    def test_app_instance_starts_none(self) -> None:
        """Verify _app_instance starts as None."""
        import importlib

        import passfx.app as app_module

        # Reload to get fresh state
        importlib.reload(app_module)

        assert app_module._app_instance is None

    @pytest.mark.unit
    def test_shutdown_flag_starts_false(self) -> None:
        """Verify _shutdown_in_progress starts as False."""
        import importlib

        import passfx.app as app_module

        importlib.reload(app_module)

        assert app_module._shutdown_in_progress is False

    @pytest.mark.unit
    def test_graceful_shutdown_sets_flag(self, reset_app_module_state: None) -> None:
        """Verify _graceful_shutdown sets the flag."""
        import passfx.app as app_module

        app_module._shutdown_in_progress = False
        app_module._app_instance = None

        with patch("passfx.app.emergency_cleanup"):
            with pytest.raises(SystemExit):
                app_module._graceful_shutdown(2, None)

        assert app_module._shutdown_in_progress is True

    @pytest.mark.unit
    def test_cleanup_on_exit_sets_flag(self, reset_app_module_state: None) -> None:
        """Verify _cleanup_on_exit sets the flag."""
        import passfx.app as app_module

        app_module._shutdown_in_progress = False
        app_module._app_instance = None

        with patch("passfx.app.clear_clipboard"):
            app_module._cleanup_on_exit()

        assert app_module._shutdown_in_progress is True


# ---------------------------------------------------------------------------
# Signal Handler Registration Tests
# ---------------------------------------------------------------------------


class TestSignalHandlerRegistration:
    """Tests for signal handler registration."""

    @pytest.mark.unit
    def test_register_signal_handlers_registers_sigint(self) -> None:
        """Verify _register_signal_handlers registers SIGINT."""
        import signal

        from passfx.app import _register_signal_handlers

        with patch("passfx.app.signal.signal") as mock_signal:
            _register_signal_handlers()

            # Find SIGINT registration
            sigint_calls = [
                c for c in mock_signal.call_args_list if c[0][0] == signal.SIGINT
            ]
            assert len(sigint_calls) == 1

    @pytest.mark.unit
    def test_register_signal_handlers_registers_sigterm(self) -> None:
        """Verify _register_signal_handlers registers SIGTERM."""
        import signal

        from passfx.app import _register_signal_handlers

        with patch("passfx.app.signal.signal") as mock_signal:
            _register_signal_handlers()

            # Find SIGTERM registration
            sigterm_calls = [
                c for c in mock_signal.call_args_list if c[0][0] == signal.SIGTERM
            ]
            assert len(sigterm_calls) == 1

    @pytest.mark.unit
    def test_signal_handlers_use_graceful_shutdown(self) -> None:
        """Verify signal handlers point to _graceful_shutdown."""
        from passfx.app import _graceful_shutdown, _register_signal_handlers

        with patch("passfx.app.signal.signal") as mock_signal:
            _register_signal_handlers()

            # All registered handlers should be _graceful_shutdown
            for call in mock_signal.call_args_list:
                assert call[0][1] == _graceful_shutdown


# ---------------------------------------------------------------------------
# Vault State Integration Tests
# ---------------------------------------------------------------------------


class TestVaultStateIntegration:
    """Tests for vault state management integration."""

    @pytest.mark.unit
    def test_vault_state_preserved_across_operations(self) -> None:
        """Verify vault state is preserved across operations."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()

            # Verify vault reference persists
            original_vault = app.vault
            _ = app.unlock_vault("password")

            assert app.vault is original_vault

    @pytest.mark.unit
    def test_unlocked_state_independent_of_vault_is_locked(self) -> None:
        """Verify app._unlocked is managed independently of vault.is_locked."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = True  # Vault reports locked
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()

            # Unlock succeeds
            app.unlock_vault("password")

            # App tracks its own state
            assert app._unlocked is True
            # Even though vault.is_locked might still return True in mock

    @pytest.mark.unit
    def test_quit_action_respects_unlocked_state(self) -> None:
        """Verify action_quit uses _unlocked state, not vault.is_locked."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False  # Vault says unlocked
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = False  # But app tracks as locked
            app.exit = MagicMock()  # type: ignore[method-assign]

            run_async(app.action_quit())

            # Should not lock because _unlocked is False
            mock_vault.lock.assert_not_called()


# ---------------------------------------------------------------------------
# Cleanup Order Tests
# ---------------------------------------------------------------------------


class TestCleanupOrder:
    """Tests verifying cleanup happens in correct order."""

    @pytest.mark.unit
    def test_graceful_shutdown_vault_then_clipboard(
        self, reset_app_module_state: None
    ) -> None:
        """Verify graceful shutdown locks vault before clearing clipboard."""
        import passfx.app as app_module

        call_order: list[str] = []

        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app.vault.lock.side_effect = lambda: call_order.append("vault_lock")
        mock_app._unlocked = True
        app_module._app_instance = mock_app
        app_module._shutdown_in_progress = False

        with patch(
            "passfx.app.emergency_cleanup",
            side_effect=lambda: call_order.append("clipboard"),
        ):
            with pytest.raises(SystemExit):
                app_module._graceful_shutdown(2, None)

        # Vault lock happens first, then clipboard clear
        assert call_order == ["vault_lock", "clipboard"]

    @pytest.mark.unit
    def test_cleanup_on_exit_vault_then_clipboard(
        self, reset_app_module_state: None
    ) -> None:
        """Verify _cleanup_on_exit locks vault before clearing clipboard."""
        import passfx.app as app_module

        call_order: list[str] = []

        mock_app = MagicMock()
        mock_app.vault = MagicMock()
        mock_app.vault.lock.side_effect = lambda: call_order.append("vault_lock")
        mock_app._unlocked = True
        app_module._app_instance = mock_app
        app_module._shutdown_in_progress = False

        with patch(
            "passfx.app.clear_clipboard",
            side_effect=lambda: call_order.append("clipboard"),
        ):
            app_module._cleanup_on_exit()

        assert call_order == ["vault_lock", "clipboard"]


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.unit
    def test_empty_password_handled(self) -> None:
        """Verify empty password is passed to vault (validation is vault's job)."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app.unlock_vault("")

            mock_vault.unlock.assert_called_once_with("")

    @pytest.mark.unit
    def test_unicode_password_handled(self) -> None:
        """Verify unicode passwords are passed correctly."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            unicode_password = "p@ssw\u00f6rd\u4e2d\u6587"
            app.unlock_vault(unicode_password)

            mock_vault.unlock.assert_called_once_with(unicode_password)

    @pytest.mark.unit
    def test_very_long_password_handled(self) -> None:
        """Verify very long passwords are passed correctly."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            long_password = "a" * 10000
            app.unlock_vault(long_password)

            mock_vault.unlock.assert_called_once_with(long_password)

    @pytest.mark.unit
    def test_app_css_path_is_string(self) -> None:
        """Verify CSS_PATH is a valid string path."""
        from passfx.app import PassFXApp

        assert isinstance(PassFXApp.CSS_PATH, str)
        assert PassFXApp.CSS_PATH.endswith(".tcss")

    @pytest.mark.unit
    def test_concurrent_cleanup_safe(self, reset_app_module_state: None) -> None:
        """Verify concurrent cleanup calls are safe via flag."""
        import passfx.app as app_module

        cleanup_count = 0

        def count_cleanup() -> None:
            nonlocal cleanup_count
            cleanup_count += 1

        app_module._shutdown_in_progress = False
        app_module._app_instance = None

        with patch("passfx.app.clear_clipboard", side_effect=count_cleanup):
            # First call
            app_module._cleanup_on_exit()
            # Second call (simulating concurrent access)
            app_module._cleanup_on_exit()

        # Only one cleanup should have run
        assert cleanup_count == 1


# ---------------------------------------------------------------------------
# Auto-Lock Tests
# ---------------------------------------------------------------------------


class TestAutoLock:
    """Tests for PassFXApp._check_auto_lock() method.

    Validates the auto-lock security invariant: vault auto-locks after
    inactivity, returning user to login screen with clipboard cleared.
    This is a critical security boundary.
    """

    @pytest.mark.unit
    def test_early_return_when_vault_locked(self) -> None:
        """Verify _check_auto_lock returns immediately when _unlocked is False.

        Security invariant: No side effects occur when vault is already locked.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = False  # Vault is locked

            # Call auto-lock check
            app._check_auto_lock()

            # Verify no timeout check occurred
            mock_vault.check_timeout.assert_not_called()
            # Verify vault.lock() was not called
            mock_vault.lock.assert_not_called()

    @pytest.mark.unit
    def test_calls_check_timeout_when_unlocked(self) -> None:
        """Verify vault.check_timeout() is called when app is unlocked."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = False
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = True

            app._check_auto_lock()

            mock_vault.check_timeout.assert_called_once()

    @pytest.mark.unit
    def test_no_action_when_timeout_not_exceeded(self) -> None:
        """Verify no locking actions when check_timeout() returns False."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = False
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = True
            app.notify = MagicMock()  # type: ignore[method-assign]

            app._check_auto_lock()

            # Verify no locking occurred
            mock_vault.lock.assert_not_called()
            assert app._unlocked is True
            app.notify.assert_not_called()

    @pytest.mark.unit
    def test_locks_vault_when_timeout_exceeded(self) -> None:
        """Verify vault.lock() is invoked when timeout is exceeded."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard"):
                from passfx.app import PassFXApp

                # Create mutable list for screen_stack simulation
                screen_stack_data = [MagicMock()]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    app._check_auto_lock()

                    mock_vault.lock.assert_called_once()

    @pytest.mark.unit
    def test_sets_unlocked_false_after_timeout(self) -> None:
        """Verify _unlocked flag is set to False after timeout."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard"):
                from passfx.app import PassFXApp

                screen_stack_data = [MagicMock()]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    app._check_auto_lock()

                    assert app._unlocked is False

    @pytest.mark.unit
    def test_clears_clipboard_on_timeout(self) -> None:
        """Verify clear_clipboard() is called on timeout.

        Security invariant: Sensitive data must be cleared from clipboard.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard") as mock_clear_clipboard:
                from passfx.app import PassFXApp

                screen_stack_data = [MagicMock()]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    app._check_auto_lock()

                    mock_clear_clipboard.assert_called_once()

    @pytest.mark.unit
    def test_notifies_user_with_correct_message(self) -> None:
        """Verify notify() is called with expected message."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard"):
                from passfx.app import PassFXApp

                screen_stack_data = [MagicMock()]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    app._check_auto_lock()

                    app.notify.assert_called_once()
                    call_args = app.notify.call_args
                    assert call_args[0][0] == "Vault locked due to inactivity"

    @pytest.mark.unit
    def test_notification_uses_warning_severity(self) -> None:
        """Verify notification uses severity='warning' parameter."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard"):
                from passfx.app import PassFXApp

                screen_stack_data = [MagicMock()]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    app._check_auto_lock()

                    call_kwargs = app.notify.call_args[1]
                    assert call_kwargs.get("severity") == "warning"

    @pytest.mark.unit
    def test_pops_all_screens_except_base(self) -> None:
        """Verify screen stack is reduced to base screen only.

        All non-base screens must be popped before pushing login.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard"):
                from passfx.app import PassFXApp

                # Simulate 4 screens on stack (base + 3 others)
                base_screen = MagicMock()
                screen_2 = MagicMock()
                screen_3 = MagicMock()
                screen_4 = MagicMock()
                screen_stack_data = [base_screen, screen_2, screen_3, screen_4]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = MagicMock()  # type: ignore[method-assign]

                    pop_count = 0

                    def mock_pop() -> None:
                        nonlocal pop_count
                        pop_count += 1
                        screen_stack_data.pop()

                    app.pop_screen = mock_pop  # type: ignore[method-assign, assignment]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    app._check_auto_lock()

                    # Should have popped 3 times (4 screens -> 1 base screen)
                    assert pop_count == 3
                    assert len(screen_stack_data) == 1
                    assert screen_stack_data[0] is base_screen

    @pytest.mark.unit
    def test_pushes_fresh_login_screen_instance(self) -> None:
        """Verify a fresh LoginScreen() instance is pushed, not a cached one.

        Security invariant: Login screen must be a new instance to ensure
        clean state (no residual data from previous session).
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard"):
                from passfx.app import PassFXApp
                from passfx.screens.login import LoginScreen

                screen_stack_data = [MagicMock()]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    app._check_auto_lock()

                    # Verify push_screen was called once
                    app.push_screen.assert_called_once()

                    # Verify the argument is an instance of LoginScreen
                    pushed_screen = app.push_screen.call_args[0][0]
                    assert isinstance(pushed_screen, LoginScreen)

    @pytest.mark.unit
    def test_login_screen_is_new_instance_each_time(self) -> None:
        """Verify each auto-lock creates a new LoginScreen instance."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard"):
                from passfx.app import PassFXApp
                from passfx.screens.login import LoginScreen

                screen_stack_data = [MagicMock()]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    # First auto-lock
                    app._unlocked = True
                    app._check_auto_lock()
                    first_screen = app.push_screen.call_args[0][0]

                    # Reset for second auto-lock
                    app.push_screen.reset_mock()
                    app._unlocked = True
                    app._check_auto_lock()
                    second_screen = app.push_screen.call_args[0][0]

                    # Verify both are LoginScreen instances but different objects
                    assert isinstance(first_screen, LoginScreen)
                    assert isinstance(second_screen, LoginScreen)
                    assert first_screen is not second_screen

    @pytest.mark.unit
    def test_complete_auto_lock_sequence(self) -> None:
        """Verify complete auto-lock sequence executes in correct order.

        Order: lock vault -> clear clipboard -> notify -> pop screens -> push login
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            call_order: list[str] = []

            def track_lock() -> None:
                call_order.append("vault_lock")

            def track_clipboard() -> None:
                call_order.append("clear_clipboard")

            mock_vault.lock.side_effect = track_lock

            with patch("passfx.app.clear_clipboard", side_effect=track_clipboard):
                from passfx.app import PassFXApp

                screen_stack_data = [MagicMock(), MagicMock()]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):

                    def track_notify(*args: object, **kwargs: object) -> None:
                        call_order.append("notify")

                    def track_pop() -> None:
                        call_order.append("pop_screen")
                        screen_stack_data.pop()

                    def track_push(screen: object) -> None:
                        call_order.append("push_screen")

                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = track_notify  # type: ignore[method-assign]
                    app.pop_screen = track_pop  # type: ignore[method-assign, assignment]
                    app.push_screen = track_push  # type: ignore[method-assign, assignment]

                    app._check_auto_lock()

            # Verify order matches implementation
            assert call_order == [
                "vault_lock",
                "clear_clipboard",
                "notify",
                "pop_screen",
                "push_screen",
            ]

    @pytest.mark.unit
    def test_notification_includes_title(self) -> None:
        """Verify notification includes 'Auto-Lock' title."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard"):
                from passfx.app import PassFXApp

                screen_stack_data = [MagicMock()]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    app._check_auto_lock()

                    call_kwargs = app.notify.call_args[1]
                    assert call_kwargs.get("title") == "Auto-Lock"

    @pytest.mark.unit
    def test_no_pop_when_only_base_screen(self) -> None:
        """Verify no pop_screen when only base screen exists."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard"):
                from passfx.app import PassFXApp

                screen_stack_data = [MagicMock()]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    app._check_auto_lock()

                    # pop_screen should not be called
                    app.pop_screen.assert_not_called()
                    # But push_screen should still be called
                    app.push_screen.assert_called_once()

    @pytest.mark.unit
    def test_multiple_auto_lock_checks_when_locked(self) -> None:
        """Verify multiple auto-lock checks are safe when already locked."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = False

            # Call multiple times
            for _ in range(5):
                app._check_auto_lock()

            # check_timeout should never be called
            mock_vault.check_timeout.assert_not_called()

    @pytest.mark.unit
    def test_auto_lock_state_transition(self) -> None:
        """Verify state transitions correctly during auto-lock.

        State: unlocked=True -> [timeout] -> unlocked=False
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard"):
                from passfx.app import PassFXApp

                screen_stack_data = [MagicMock()]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    # Initial state: unlocked
                    app._unlocked = True
                    assert app._unlocked is True

                    # Trigger auto-lock
                    app._check_auto_lock()

                    # Final state: locked
                    assert app._unlocked is False

                    # Second call should be no-op
                    mock_vault.check_timeout.reset_mock()
                    app._check_auto_lock()
                    mock_vault.check_timeout.assert_not_called()

    @pytest.mark.unit
    def test_handles_empty_screen_stack_gracefully(self) -> None:
        """Verify auto-lock handles edge case of empty screen stack.

        This shouldn't happen in practice, but defensive code should not crash.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard"):
                from passfx.app import PassFXApp

                screen_stack_data: list[MagicMock] = []

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    # Should not raise
                    app._check_auto_lock()

                    # Verify core security actions still occurred
                    mock_vault.lock.assert_called_once()
                    assert app._unlocked is False
                    app.push_screen.assert_called_once()

    @pytest.mark.unit
    def test_vault_lock_exception_does_not_crash(self) -> None:
        """Verify exceptions in vault.lock() don't crash the application.

        Note: Current implementation does not wrap vault.lock() in try/except.
        This test documents the current behavior for regression detection.
        If exception handling is added, update this test accordingly.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault.lock.side_effect = RuntimeError("Vault lock failed")
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard"):
                from passfx.app import PassFXApp

                screen_stack_data = [MagicMock()]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    # Current behavior: exception propagates
                    # If exception handling is added, this should not raise
                    with pytest.raises(RuntimeError, match="Vault lock failed"):
                        app._check_auto_lock()

    @pytest.mark.unit
    def test_clipboard_cleared_even_with_many_screens(self) -> None:
        """Verify clipboard is cleared regardless of screen stack depth.

        Security invariant: Clipboard must be cleared in all cases.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            with patch("passfx.app.clear_clipboard") as mock_clear_clipboard:
                from passfx.app import PassFXApp

                # Deep screen stack (10 screens)
                screen_stack_data = [MagicMock() for _ in range(10)]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = lambda: screen_stack_data.pop()  # type: ignore[method-assign]
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    app._check_auto_lock()

                    # Clipboard must be cleared
                    mock_clear_clipboard.assert_called_once()

    @pytest.mark.unit
    def test_unlocked_flag_set_before_ui_actions(self) -> None:
        """Verify _unlocked is set to False before screen manipulation.

        Security invariant: Internal state must be locked before UI transitions.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault_class.return_value = mock_vault

            unlocked_states: list[bool] = []

            def capture_state_on_push(screen: object) -> None:
                unlocked_states.append(app._unlocked)

            with patch("passfx.app.clear_clipboard"):
                from passfx.app import PassFXApp

                screen_stack_data = [MagicMock()]

                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.notify = MagicMock()  # type: ignore[method-assign]
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]
                    app.push_screen = capture_state_on_push  # type: ignore[method-assign, assignment]

                    app._check_auto_lock()

                    # When push_screen is called, _unlocked should already be False
                    assert unlocked_states == [False]
