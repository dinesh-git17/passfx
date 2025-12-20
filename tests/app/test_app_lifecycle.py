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

    @pytest.mark.unit
    def test_on_key_resets_activity_when_unlocked(self) -> None:
        """Verify on_key resets activity timer when vault is unlocked."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = True

            mock_event = MagicMock()
            app.on_key(mock_event)

            mock_vault.reset_activity.assert_called_once()

    @pytest.mark.unit
    def test_on_key_does_not_reset_activity_when_locked(self) -> None:
        """Verify on_key does not reset activity when vault is locked."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = False

            mock_event = MagicMock()
            app.on_key(mock_event)

            mock_vault.reset_activity.assert_not_called()

    @pytest.mark.unit
    def test_on_mouse_down_resets_activity_when_unlocked(self) -> None:
        """Verify on_mouse_down resets activity timer when vault is unlocked."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = True

            mock_event = MagicMock()
            app.on_mouse_down(mock_event)

            mock_vault.reset_activity.assert_called_once()

    @pytest.mark.unit
    def test_on_mouse_down_does_not_reset_activity_when_locked(self) -> None:
        """Verify on_mouse_down does not reset activity when vault is locked."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = False

            mock_event = MagicMock()
            app.on_mouse_down(mock_event)

            mock_vault.reset_activity.assert_not_called()

    @pytest.mark.unit
    def test_multiple_key_events_reset_activity_each_time(self) -> None:
        """Verify each key event resets activity timer."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = True

            mock_event = MagicMock()
            for _ in range(5):
                app.on_key(mock_event)

            assert mock_vault.reset_activity.call_count == 5


# ---------------------------------------------------------------------------
# Navigation Guard Tests
# ---------------------------------------------------------------------------


class TestNavigationGuards:
    """Tests for PassFXApp.action_back() navigation guard behavior.

    Validates that action_back() correctly prevents navigation from protected
    screens (MainMenuScreen, LoginScreen) while allowing normal back navigation
    from other screens when the stack depth permits.
    """

    @pytest.mark.unit
    def test_no_pop_on_main_menu_screen(self) -> None:
        """Verify action_back() does not call pop_screen() on MainMenuScreen.

        Guard invariant: MainMenuScreen is a navigation boundary - users cannot
        navigate back from it using the back action.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            # Create a mock screen with MainMenuScreen class name
            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "MainMenuScreen"

            # Stack with multiple screens (would allow pop otherwise)
            screen_stack_data = [MagicMock(), MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    # pop_screen must NOT be called
                    app.pop_screen.assert_not_called()

    @pytest.mark.unit
    def test_no_pop_on_login_screen(self) -> None:
        """Verify action_back() does not call pop_screen() on LoginScreen.

        Guard invariant: LoginScreen is a security boundary - users cannot
        navigate back from the authentication screen.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            # Create a mock screen with LoginScreen class name
            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "LoginScreen"

            # Stack with multiple screens
            screen_stack_data = [MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_not_called()

    @pytest.mark.unit
    def test_pop_screen_on_passwords_screen_with_stack_depth(self) -> None:
        """Verify action_back() calls pop_screen() on PasswordsScreen with stack > 1.

        Normal navigation: Non-guarded screens with sufficient stack depth allow
        back navigation.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "PasswordsScreen"

            # Stack depth > 1 (base + current)
            screen_stack_data = [MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_called_once()

    @pytest.mark.unit
    def test_pop_screen_on_cards_screen_with_stack_depth(self) -> None:
        """Verify action_back() calls pop_screen() on CardsScreen with stack > 1."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "CardsScreen"

            screen_stack_data = [MagicMock(), MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_called_once()

    @pytest.mark.unit
    def test_no_pop_on_non_guarded_screen_with_base_only(self) -> None:
        """Verify action_back() does not pop when stack length is exactly 1.

        Edge case: Even non-guarded screens cannot pop when they are the only
        screen on the stack.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "SettingsScreen"

            # Only one screen on stack
            screen_stack_data = [mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_not_called()

    @pytest.mark.unit
    def test_pop_screen_on_notes_screen(self) -> None:
        """Verify action_back() calls pop_screen() on NotesScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "NotesScreen"

            screen_stack_data = [MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_called_once()

    @pytest.mark.unit
    def test_pop_screen_on_phones_screen(self) -> None:
        """Verify action_back() calls pop_screen() on PhonesScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "PhonesScreen"

            screen_stack_data = [MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_called_once()

    @pytest.mark.unit
    def test_pop_screen_on_envs_screen(self) -> None:
        """Verify action_back() calls pop_screen() on EnvsScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "EnvsScreen"

            screen_stack_data = [MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_called_once()

    @pytest.mark.unit
    def test_pop_screen_on_recovery_screen(self) -> None:
        """Verify action_back() calls pop_screen() on RecoveryScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "RecoveryScreen"

            screen_stack_data = [MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_called_once()

    @pytest.mark.unit
    def test_pop_screen_on_generator_screen(self) -> None:
        """Verify action_back() calls pop_screen() on GeneratorScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "GeneratorScreen"

            screen_stack_data = [MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_called_once()

    @pytest.mark.unit
    def test_pop_screen_on_settings_screen(self) -> None:
        """Verify action_back() calls pop_screen() on SettingsScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "SettingsScreen"

            screen_stack_data = [MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_called_once()

    @pytest.mark.unit
    def test_main_menu_guard_with_deep_stack(self) -> None:
        """Verify MainMenuScreen guard works regardless of stack depth.

        Even with a deep stack, MainMenuScreen should not allow back navigation.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "MainMenuScreen"

            # Deep stack - 5 screens
            screen_stack_data = [MagicMock() for _ in range(5)]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_not_called()

    @pytest.mark.unit
    def test_login_guard_with_deep_stack(self) -> None:
        """Verify LoginScreen guard works regardless of stack depth."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "LoginScreen"

            # Deep stack
            screen_stack_data = [MagicMock() for _ in range(10)]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_not_called()

    @pytest.mark.unit
    def test_pop_screen_called_exactly_once(self) -> None:
        """Verify action_back() calls pop_screen() exactly once, not multiple times."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "PasswordsScreen"

            # Stack with 5 screens
            screen_stack_data = [MagicMock() for _ in range(5)]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    # Exactly one call, not multiple
                    assert app.pop_screen.call_count == 1

    @pytest.mark.unit
    def test_guard_uses_class_name_not_instance(self) -> None:
        """Verify guard checks __class__.__name__, not instance type.

        Implementation detail: The guard uses string comparison on class name,
        not isinstance() checks.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            # Create a mock that is not actually a MainMenuScreen instance
            # but has the same class name
            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "MainMenuScreen"

            screen_stack_data = [MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    # Guard should trigger based on class name
                    app.pop_screen.assert_not_called()

    @pytest.mark.unit
    def test_arbitrary_screen_name_not_guarded(self) -> None:
        """Verify arbitrary screen names are not guarded."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "SomeRandomScreen"

            screen_stack_data = [MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_called_once()

    @pytest.mark.unit
    def test_case_sensitive_guard_check(self) -> None:
        """Verify guard check is case-sensitive.

        'mainmenuscreen' should not be guarded, only 'MainMenuScreen'.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "mainmenuscreen"  # lowercase

            screen_stack_data = [MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    # Should NOT be guarded (case matters)
                    app.pop_screen.assert_called_once()

    @pytest.mark.unit
    def test_empty_screen_stack_no_pop(self) -> None:
        """Verify action_back() handles empty screen stack gracefully.

        Edge case: Empty stack should not cause errors or call pop_screen.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "PasswordsScreen"

            # Empty stack
            screen_stack_data: list[MagicMock] = []

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    app.pop_screen.assert_not_called()

    @pytest.mark.unit
    def test_multiple_action_back_calls(self) -> None:
        """Verify multiple action_back() calls are independent.

        Each call should evaluate conditions fresh.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "PasswordsScreen"

            screen_stack_data = [MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())
                    run_async(app.action_back())
                    run_async(app.action_back())

                    # Each call should have invoked pop_screen (3 calls total)
                    assert app.pop_screen.call_count == 3

    @pytest.mark.unit
    def test_action_back_is_async(self) -> None:
        """Verify action_back() is an async method.

        Implementation requirement: action_back must be awaitable.
        """
        import inspect

        from passfx.app import PassFXApp

        assert inspect.iscoroutinefunction(PassFXApp.action_back)

    @pytest.mark.unit
    def test_vault_interceptor_screen_not_guarded(self) -> None:
        """Verify VaultInterceptorScreen is not guarded by action_back().

        Only MainMenuScreen and LoginScreen are explicitly guarded.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "VaultInterceptorScreen"

            screen_stack_data = [MagicMock(), mock_screen]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    # VaultInterceptorScreen should NOT be guarded
                    app.pop_screen.assert_called_once()

    @pytest.mark.unit
    def test_guard_evaluated_before_stack_check(self) -> None:
        """Verify guard check happens before stack length check.

        Order matters: Even with stack > 1, guard should prevent pop.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "LoginScreen"

            # Large stack that would otherwise allow pop
            screen_stack_data = [MagicMock() for _ in range(100)]

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                with patch.object(
                    PassFXApp,
                    "screen_stack",
                    new_callable=lambda: property(lambda self: screen_stack_data),
                ):
                    app = PassFXApp()
                    app.pop_screen = MagicMock()  # type: ignore[method-assign]

                    run_async(app.action_back())

                    # Guard should have blocked, regardless of stack depth
                    app.pop_screen.assert_not_called()


# ---------------------------------------------------------------------------
# Global Search Toggle Tests
# ---------------------------------------------------------------------------


class TestSearchToggle:
    """Tests for PassFXApp.action_toggle_search() global search activation.

    Validates the search overlay activation guards, index building trigger,
    and modal push with correct callback wiring. Search overlay is a critical
    UX feature that must respect vault lock state.
    """

    @pytest.mark.unit
    def test_returns_early_when_vault_locked(self) -> None:
        """Verify action_toggle_search() returns immediately when _unlocked is False.

        Security invariant: Search overlay must never open on locked vault.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = False  # Vault is locked
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            app.action_toggle_search()

            # push_screen should NOT be called
            app.push_screen.assert_not_called()

    @pytest.mark.unit
    def test_returns_early_on_login_screen(self) -> None:
        """Verify action_toggle_search() does not open on LoginScreen.

        Guard invariant: Search is meaningless on login screen.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "LoginScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True  # Vault is unlocked
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                app.push_screen.assert_not_called()

    @pytest.mark.unit
    def test_returns_early_on_vault_interceptor_screen(self) -> None:
        """Verify action_toggle_search() does not open when already on search overlay.

        Guard invariant: Prevents recursive search overlay activation.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "VaultInterceptorScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                app.push_screen.assert_not_called()

    @pytest.mark.unit
    def test_opens_search_on_main_menu_screen(self) -> None:
        """Verify action_toggle_search() opens search overlay on MainMenuScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "MainMenuScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                app.push_screen.assert_called_once()

    @pytest.mark.unit
    def test_opens_search_on_passwords_screen(self) -> None:
        """Verify action_toggle_search() opens search overlay on PasswordsScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "PasswordsScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                app.push_screen.assert_called_once()

    @pytest.mark.unit
    def test_builds_search_index_before_push(self) -> None:
        """Verify _build_search_index() is called before push_screen().

        Index must be built before the search modal is pushed.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "PasswordsScreen"

            call_order: list[str] = []

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True

                original_build = app._build_search_index

                def track_build() -> None:
                    call_order.append("build_index")
                    original_build()

                def track_push(*args: object, **kwargs: object) -> None:
                    call_order.append("push_screen")

                app._build_search_index = track_build  # type: ignore[method-assign]
                app.push_screen = track_push  # type: ignore[method-assign, assignment]

                app.action_toggle_search()

            assert call_order == ["build_index", "push_screen"]

    @pytest.mark.unit
    def test_push_screen_with_vault_interceptor_screen(self) -> None:
        """Verify push_screen() is called with VaultInterceptorScreen instance."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.widgets.search_overlay import VaultInterceptorScreen

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "PasswordsScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                # Verify push_screen was called with VaultInterceptorScreen
                call_args = app.push_screen.call_args
                assert isinstance(call_args[0][0], VaultInterceptorScreen)

    @pytest.mark.unit
    def test_push_screen_with_callback(self) -> None:
        """Verify push_screen() is called with callback parameter."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "PasswordsScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                # Verify callback parameter was passed
                call_kwargs = app.push_screen.call_args[1]
                assert "callback" in call_kwargs
                assert call_kwargs["callback"] == app._handle_search_result

    @pytest.mark.unit
    def test_search_index_passed_to_modal(self) -> None:
        """Verify search index is passed to VaultInterceptorScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.widgets.search_overlay import VaultInterceptorScreen

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "PasswordsScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                # Get the VaultInterceptorScreen that was pushed
                pushed_screen = app.push_screen.call_args[0][0]
                assert isinstance(pushed_screen, VaultInterceptorScreen)
                # Index should have been set on app
                assert app._search_index is not None

    @pytest.mark.unit
    def test_guard_check_uses_class_name(self) -> None:
        """Verify guard checks use __class__.__name__ comparison."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            # Test with lowercase (should NOT be guarded)
            mock_screen.__class__.__name__ = "loginscreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                mock_vault.is_locked = False
                mock_vault.get_emails.return_value = []
                mock_vault.get_phones.return_value = []
                mock_vault.get_cards.return_value = []
                mock_vault.get_envs.return_value = []
                mock_vault.get_recovery_entries.return_value = []
                mock_vault.get_notes.return_value = []

                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                # Should NOT be guarded (case-sensitive check)
                app.push_screen.assert_called_once()

    @pytest.mark.unit
    def test_locked_vault_checked_first(self) -> None:
        """Verify _unlocked check happens before screen name check.

        Security invariant: Lock check is the primary security gate.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            # Even on a valid screen, locked vault should block
            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "PasswordsScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = False  # Locked
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                # Should be blocked by _unlocked check
                app.push_screen.assert_not_called()

    @pytest.mark.unit
    def test_ctrl_k_binding_defined(self) -> None:
        """Verify Ctrl+K is bound to toggle_search action."""
        from textual.binding import Binding

        from passfx.app import PassFXApp

        binding_found = False
        for b in PassFXApp.BINDINGS:
            if isinstance(b, Binding):
                if b.key == "ctrl+k" and b.action == "toggle_search":
                    binding_found = True
                    break

        assert binding_found, "Ctrl+K binding for toggle_search not found"


# ---------------------------------------------------------------------------
# Search Index Build Tests
# ---------------------------------------------------------------------------


class TestSearchIndexBuild:
    """Tests for PassFXApp._build_search_index() index construction.

    Validates that the search index is correctly built from vault data
    and respects the vault lock state.
    """

    @pytest.mark.unit
    def test_sets_index_none_when_vault_locked(self) -> None:
        """Verify _search_index is set to None when _unlocked is False."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = False

            app._build_search_index()

            assert app._search_index is None

    @pytest.mark.unit
    def test_sets_index_none_when_vault_is_locked_property(self) -> None:
        """Verify _search_index is None when vault.is_locked is True."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = True
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = True  # App thinks it's unlocked
            # But vault.is_locked is True

            app._build_search_index()

            assert app._search_index is None

    @pytest.mark.unit
    def test_builds_index_when_unlocked(self) -> None:
        """Verify _search_index is created when vault is unlocked."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchIndex

            app = PassFXApp()
            app._unlocked = True

            app._build_search_index()

            assert app._search_index is not None
            assert isinstance(app._search_index, SearchIndex)

    @pytest.mark.unit
    def test_calls_all_vault_getters(self) -> None:
        """Verify all vault getter methods are called."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = True

            app._build_search_index()

            # Verify all getters were called
            mock_vault.get_emails.assert_called_once()
            mock_vault.get_phones.assert_called_once()
            mock_vault.get_cards.assert_called_once()
            mock_vault.get_envs.assert_called_once()
            mock_vault.get_recovery_entries.assert_called_once()
            mock_vault.get_notes.assert_called_once()

    @pytest.mark.unit
    def test_builds_index_with_vault_data(self) -> None:
        """Verify SearchIndex.build_index() is called with vault data."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_emails = [MagicMock()]
            mock_phones = [MagicMock()]
            mock_cards = [MagicMock()]
            mock_envs = [MagicMock()]
            mock_recovery = [MagicMock()]
            mock_notes = [MagicMock()]

            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = mock_emails
            mock_vault.get_phones.return_value = mock_phones
            mock_vault.get_cards.return_value = mock_cards
            mock_vault.get_envs.return_value = mock_envs
            mock_vault.get_recovery_entries.return_value = mock_recovery
            mock_vault.get_notes.return_value = mock_notes
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            with patch("passfx.app.SearchIndex") as mock_index_class:
                mock_index = MagicMock()
                mock_index_class.return_value = mock_index

                app = PassFXApp()
                app._unlocked = True

                app._build_search_index()

                mock_index.build_index.assert_called_once_with(
                    emails=mock_emails,
                    phones=mock_phones,
                    cards=mock_cards,
                    envs=mock_envs,
                    recovery=mock_recovery,
                    notes=mock_notes,
                )

    @pytest.mark.unit
    def test_empty_vault_produces_valid_index(self) -> None:
        """Verify empty vault still produces a valid SearchIndex."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchIndex

            app = PassFXApp()
            app._unlocked = True

            app._build_search_index()

            assert app._search_index is not None
            assert isinstance(app._search_index, SearchIndex)

    @pytest.mark.unit
    def test_replaces_existing_index(self) -> None:
        """Verify _build_search_index() replaces existing index."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = True

            # Build first index
            app._build_search_index()
            first_index = app._search_index

            # Build second index
            app._build_search_index()
            second_index = app._search_index

            # Should be different objects
            assert first_index is not second_index

    @pytest.mark.unit
    def test_dual_condition_both_must_pass(self) -> None:
        """Verify both _unlocked and not vault.is_locked are required."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            # Case 1: _unlocked=False, is_locked=False
            mock_vault.is_locked = False
            app1 = PassFXApp()
            app1._unlocked = False
            app1._build_search_index()
            assert app1._search_index is None

            # Case 2: _unlocked=True, is_locked=True
            mock_vault.is_locked = True
            app2 = PassFXApp()
            app2._unlocked = True
            app2._build_search_index()
            assert app2._search_index is None

            # Case 3: _unlocked=True, is_locked=False (should build)
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            app3 = PassFXApp()
            app3._unlocked = True
            app3._build_search_index()
            assert app3._search_index is not None


# ---------------------------------------------------------------------------
# Search Result Handling Tests
# ---------------------------------------------------------------------------


class TestSearchResultHandling:
    """Tests for PassFXApp._handle_search_result() callback behavior.

    Validates that the search result handler correctly dispatches to
    navigation or ignores None results.
    """

    @pytest.mark.unit
    def test_none_result_no_navigation(self) -> None:
        """Verify None result does not trigger navigation."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._navigate_to_result = MagicMock()  # type: ignore[method-assign]

            app._handle_search_result(None)

            app._navigate_to_result.assert_not_called()

    @pytest.mark.unit
    def test_valid_result_triggers_navigation(self) -> None:
        """Verify valid SearchResult triggers _navigate_to_result()."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app._navigate_to_result = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "passwords"
            mock_result.credential_id = "test-id"

            app._handle_search_result(mock_result)

            app._navigate_to_result.assert_called_once_with(mock_result)

    @pytest.mark.unit
    def test_result_passed_unchanged(self) -> None:
        """Verify result is passed to _navigate_to_result unchanged."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()

            received_results: list[SearchResult] = []

            def capture_result(result: SearchResult) -> None:
                received_results.append(result)

            app._navigate_to_result = capture_result  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "cards"
            mock_result.credential_id = "card-123"

            app._handle_search_result(mock_result)

            assert len(received_results) == 1
            assert received_results[0] is mock_result


# ---------------------------------------------------------------------------
# Search Result Routing Tests
# ---------------------------------------------------------------------------


class TestSearchResultRouting:
    """Tests for PassFXApp._navigate_to_result() screen routing.

    Validates that search results are correctly routed to the appropriate
    screens with proper credential ID propagation.
    """

    @pytest.mark.unit
    def test_routes_to_passwords_screen(self) -> None:
        """Verify passwords result routes to PasswordsScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "passwords"
            mock_result.credential_id = "pwd-123"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_called_once()
            pushed_screen = app.push_screen.call_args[0][0]
            assert pushed_screen.__class__.__name__ == "PasswordsScreen"
            assert pushed_screen._pending_select_id == "pwd-123"

    @pytest.mark.unit
    def test_routes_to_phones_screen(self) -> None:
        """Verify phones result routes to PhonesScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "phones"
            mock_result.credential_id = "phone-456"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_called_once()
            pushed_screen = app.push_screen.call_args[0][0]
            assert pushed_screen.__class__.__name__ == "PhonesScreen"
            assert pushed_screen._pending_select_id == "phone-456"

    @pytest.mark.unit
    def test_routes_to_cards_screen(self) -> None:
        """Verify cards result routes to CardsScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "cards"
            mock_result.credential_id = "card-789"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_called_once()
            pushed_screen = app.push_screen.call_args[0][0]
            assert pushed_screen.__class__.__name__ == "CardsScreen"
            assert pushed_screen._pending_select_id == "card-789"

    @pytest.mark.unit
    def test_routes_to_envs_screen(self) -> None:
        """Verify envs result routes to EnvsScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "envs"
            mock_result.credential_id = "env-abc"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_called_once()
            pushed_screen = app.push_screen.call_args[0][0]
            assert pushed_screen.__class__.__name__ == "EnvsScreen"
            assert pushed_screen._pending_select_id == "env-abc"

    @pytest.mark.unit
    def test_routes_to_recovery_screen(self) -> None:
        """Verify recovery result routes to RecoveryScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "recovery"
            mock_result.credential_id = "rec-def"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_called_once()
            pushed_screen = app.push_screen.call_args[0][0]
            assert pushed_screen.__class__.__name__ == "RecoveryScreen"
            assert pushed_screen._pending_select_id == "rec-def"

    @pytest.mark.unit
    def test_routes_to_notes_screen(self) -> None:
        """Verify notes result routes to NotesScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "notes"
            mock_result.credential_id = "note-xyz"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_called_once()
            pushed_screen = app.push_screen.call_args[0][0]
            assert pushed_screen.__class__.__name__ == "NotesScreen"
            assert pushed_screen._pending_select_id == "note-xyz"

    @pytest.mark.unit
    def test_unknown_screen_name_no_action(self) -> None:
        """Verify unknown screen_name does not push any screen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "unknown_screen"
            mock_result.credential_id = "some-id"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_not_called()

    @pytest.mark.unit
    def test_credential_id_propagation(self) -> None:
        """Verify credential_id is correctly set on target screen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            test_cases = [
                ("passwords", "unique-pwd-id-123"),
                ("phones", "unique-phone-id-456"),
                ("cards", "unique-card-id-789"),
                ("envs", "unique-env-id-abc"),
                ("recovery", "unique-rec-id-def"),
                ("notes", "unique-note-id-xyz"),
            ]

            for screen_name, cred_id in test_cases:
                app = PassFXApp()
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                mock_result = MagicMock(spec=SearchResult)
                mock_result.screen_name = screen_name
                mock_result.credential_id = cred_id

                app._navigate_to_result(mock_result)

                pushed_screen = app.push_screen.call_args[0][0]
                assert (
                    pushed_screen._pending_select_id == cred_id
                ), f"Failed for {screen_name}"

    @pytest.mark.unit
    def test_push_screen_called_exactly_once(self) -> None:
        """Verify push_screen is called exactly once per navigation."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "passwords"
            mock_result.credential_id = "test-id"

            app._navigate_to_result(mock_result)

            assert app.push_screen.call_count == 1

    @pytest.mark.unit
    def test_screens_are_fresh_instances(self) -> None:
        """Verify each navigation creates a fresh screen instance."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()

            pushed_screens: list[object] = []

            def capture_push(screen: object) -> None:
                pushed_screens.append(screen)

            app.push_screen = capture_push  # type: ignore[method-assign, assignment]

            mock_result1 = MagicMock(spec=SearchResult)
            mock_result1.screen_name = "passwords"
            mock_result1.credential_id = "id-1"

            mock_result2 = MagicMock(spec=SearchResult)
            mock_result2.screen_name = "passwords"
            mock_result2.credential_id = "id-2"

            app._navigate_to_result(mock_result1)
            app._navigate_to_result(mock_result2)

            assert len(pushed_screens) == 2
            assert pushed_screens[0] is not pushed_screens[1]

    @pytest.mark.unit
    def test_lazy_imports_work_correctly(self) -> None:
        """Verify lazy imports in _navigate_to_result work correctly.

        Implementation uses lazy imports to avoid circular dependencies.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            # Test that all screen types can be imported and instantiated
            screen_types = ["passwords", "phones", "cards", "envs", "recovery", "notes"]

            for screen_type in screen_types:
                mock_result = MagicMock(spec=SearchResult)
                mock_result.screen_name = screen_type
                mock_result.credential_id = f"{screen_type}-id"

                # Should not raise import errors
                app._navigate_to_result(mock_result)

            # All six should have been pushed
            assert app.push_screen.call_count == 6


# ---------------------------------------------------------------------------
# Cross-Cutting Concerns Tests
# ---------------------------------------------------------------------------


class TestSearchAndAutoLockInteraction:
    """Tests for interaction between auto-lock and search state.

    Validates that auto-lock correctly resets search-related state.
    """

    @pytest.mark.unit
    def test_auto_lock_while_search_active(self) -> None:
        """Verify auto-lock clears search state when triggered.

        Search index should be invalidated when vault locks.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.check_timeout.return_value = True
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
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

                    # Build search index
                    app._build_search_index()
                    assert app._search_index is not None

                    # Trigger auto-lock
                    app._check_auto_lock()

                    # Verify vault is locked
                    assert app._unlocked is False

                    # Rebuild index should now set to None
                    app._build_search_index()
                    assert app._search_index is None

    @pytest.mark.unit
    def test_search_toggle_after_auto_lock(self) -> None:
        """Verify search toggle is blocked after auto-lock."""
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

                    # Trigger auto-lock
                    app._check_auto_lock()

                    # Reset push_screen mock
                    app.push_screen.reset_mock()

                    # Attempt to toggle search
                    app.action_toggle_search()

                    # Should be blocked because _unlocked is False
                    # Only the LoginScreen push from auto-lock should have occurred
                    # push_screen was reset, so new call should NOT happen
                    app.push_screen.assert_not_called()


# ---------------------------------------------------------------------------
# Initialization Tests for Search Index
# ---------------------------------------------------------------------------


class TestSearchIndexInitialization:
    """Tests for search index initialization state."""

    @pytest.mark.unit
    def test_search_index_initially_none(self) -> None:
        """Verify _search_index is None on app initialization."""
        with patch("passfx.app.Vault"):
            from passfx.app import PassFXApp

            app = PassFXApp()

            assert app._search_index is None

    @pytest.mark.unit
    def test_search_index_attribute_exists(self) -> None:
        """Verify _search_index attribute is defined."""
        with patch("passfx.app.Vault"):
            from passfx.app import PassFXApp

            app = PassFXApp()

            assert hasattr(app, "_search_index")
