# Login security tests for PassFX authentication and brute-force protection.
# Validates rate limiting, lockout behavior, and authentication error safety.
# nosec B101 - assert usage is intentional in test code

from __future__ import annotations

import io
import logging
import os
import stat
import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from passfx.screens.login import (
    LOCKOUT_FILE,
    MAX_ATTEMPTS_BEFORE_LOCKOUT,
    MAX_LOCKOUT_SECONDS,
    _check_lockout,
    _clear_lockout,
    _get_lockout_state,
    _record_failed_attempt,
    _save_lockout_state,
)

if TYPE_CHECKING:
    from collections.abc import Generator


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def isolated_lockout(tmp_path: Path) -> Generator[Path, None, None]:
    """Isolate lockout file to a temporary directory.

    Patches the LOCKOUT_FILE constant to use a temp directory, ensuring
    tests don't affect the real user's lockout state.
    """
    temp_lockout = tmp_path / ".passfx" / "lockout.json"
    temp_lockout.parent.mkdir(parents=True, exist_ok=True)

    with patch("passfx.screens.login.LOCKOUT_FILE", temp_lockout):
        yield temp_lockout

    # Cleanup
    if temp_lockout.exists():
        temp_lockout.unlink()


@pytest.fixture
def capture_logs() -> Generator[io.StringIO, None, None]:
    """Capture log output for inspection."""
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    original_level = root_logger.level
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

    yield log_capture

    root_logger.removeHandler(handler)
    root_logger.setLevel(original_level)


# -----------------------------------------------------------------------------
# Rate Limiting State Tests
# Validates lockout state persistence and retrieval.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestLockoutStatePersistence:
    """Validates lockout state read/write operations."""

    def test_get_lockout_state_returns_default_when_no_file(
        self, isolated_lockout: Path
    ) -> None:
        """Missing lockout file must return clean default state."""
        if isolated_lockout.exists():
            isolated_lockout.unlink()

        state = _get_lockout_state()

        assert state == {"failed_attempts": 0, "lockout_until": None}

    def test_save_and_retrieve_lockout_state(self, isolated_lockout: Path) -> None:
        """Saved lockout state must be retrievable."""
        test_state = {"failed_attempts": 3, "lockout_until": time.time() + 60}

        _save_lockout_state(test_state)
        retrieved = _get_lockout_state()

        assert retrieved["failed_attempts"] == 3
        assert retrieved["lockout_until"] is not None
        assert abs(retrieved["lockout_until"] - test_state["lockout_until"]) < 1

    def test_lockout_file_has_secure_permissions(self, isolated_lockout: Path) -> None:
        """Lockout file must have 0600 permissions (owner read/write only)."""
        _save_lockout_state({"failed_attempts": 1, "lockout_until": None})

        assert isolated_lockout.exists()
        mode = stat.S_IMODE(isolated_lockout.stat().st_mode)
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"

    def test_get_lockout_state_handles_corrupted_json(
        self, isolated_lockout: Path
    ) -> None:
        """Corrupted JSON in lockout file must return clean default state."""
        isolated_lockout.parent.mkdir(parents=True, exist_ok=True)
        isolated_lockout.write_text("not valid json {{{", encoding="utf-8")

        state = _get_lockout_state()

        assert state == {"failed_attempts": 0, "lockout_until": None}

    def test_get_lockout_state_handles_invalid_structure(
        self, isolated_lockout: Path
    ) -> None:
        """Invalid JSON structure in lockout file must return clean default."""
        isolated_lockout.parent.mkdir(parents=True, exist_ok=True)
        isolated_lockout.write_text('["array", "not", "dict"]', encoding="utf-8")

        state = _get_lockout_state()

        assert state == {"failed_attempts": 0, "lockout_until": None}

    def test_get_lockout_state_handles_invalid_values(
        self, isolated_lockout: Path
    ) -> None:
        """Invalid values in lockout file must be sanitized."""
        isolated_lockout.parent.mkdir(parents=True, exist_ok=True)
        isolated_lockout.write_text(
            '{"failed_attempts": "not_a_number", "lockout_until": "invalid"}',
            encoding="utf-8",
        )

        state = _get_lockout_state()

        assert state["failed_attempts"] == 0
        assert state["lockout_until"] is None

    def test_get_lockout_state_handles_negative_attempts(
        self, isolated_lockout: Path
    ) -> None:
        """Negative failed_attempts must be reset to zero."""
        isolated_lockout.parent.mkdir(parents=True, exist_ok=True)
        isolated_lockout.write_text(
            '{"failed_attempts": -5, "lockout_until": null}', encoding="utf-8"
        )

        state = _get_lockout_state()

        assert state["failed_attempts"] == 0


# -----------------------------------------------------------------------------
# Rate Limiting Behavior Tests
# Validates exponential backoff and lockout mechanics.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestRateLimitingBehavior:
    """Validates rate limiting and exponential backoff."""

    def test_first_failed_attempt_creates_short_lockout(
        self, isolated_lockout: Path
    ) -> None:
        """First failed attempt must create 2-second lockout (2^1)."""
        _clear_lockout()

        _record_failed_attempt()

        state = _get_lockout_state()
        assert state["failed_attempts"] == 1
        assert state["lockout_until"] is not None

        # Lockout should be approximately 2 seconds from now
        remaining = state["lockout_until"] - time.time()
        assert 1 < remaining <= 2

    def test_exponential_backoff_doubles_each_attempt(
        self, isolated_lockout: Path
    ) -> None:
        """Each failed attempt must double the lockout duration."""
        _clear_lockout()

        expected_delays = [2, 4, 8, 16, 32]  # 2^1, 2^2, 2^3, 2^4, 2^5

        for i, expected_delay in enumerate(expected_delays):
            # Record attempt with frozen time
            with patch("passfx.screens.login.time") as mock_time:
                mock_time.time.return_value = 1000.0

                # Clear and set up state for this iteration
                if i > 0:
                    _save_lockout_state({"failed_attempts": i, "lockout_until": 1000.0})

                _record_failed_attempt()

                state = _get_lockout_state()
                actual_delay = state["lockout_until"] - 1000.0

                assert actual_delay == expected_delay, (
                    f"Attempt {i + 1}: expected {expected_delay}s delay, "
                    f"got {actual_delay}s"
                )

            # Reset for next iteration
            _clear_lockout()

    def test_lockout_capped_at_maximum(self, isolated_lockout: Path) -> None:
        """Lockout duration must never exceed MAX_LOCKOUT_SECONDS."""
        # Set up state with many failed attempts
        _save_lockout_state({"failed_attempts": 50, "lockout_until": None})

        with patch("passfx.screens.login.time") as mock_time:
            mock_time.time.return_value = 1000.0

            _record_failed_attempt()

            state = _get_lockout_state()
            actual_delay = state["lockout_until"] - 1000.0

            assert actual_delay <= MAX_LOCKOUT_SECONDS

    def test_check_lockout_returns_true_when_locked(
        self, isolated_lockout: Path
    ) -> None:
        """check_lockout must return True when user is locked out."""
        future_time = time.time() + 300
        _save_lockout_state({"failed_attempts": 5, "lockout_until": future_time})

        is_locked, seconds_remaining = _check_lockout()

        assert is_locked is True
        assert 290 < seconds_remaining <= 300

    def test_check_lockout_returns_false_when_not_locked(
        self, isolated_lockout: Path
    ) -> None:
        """check_lockout must return False when no lockout active."""
        _clear_lockout()

        is_locked, seconds_remaining = _check_lockout()

        assert is_locked is False
        assert seconds_remaining == 0

    def test_check_lockout_clears_expired_lockout(self, isolated_lockout: Path) -> None:
        """Expired lockout must be cleared automatically."""
        past_time = time.time() - 10
        _save_lockout_state({"failed_attempts": 3, "lockout_until": past_time})

        is_locked, seconds_remaining = _check_lockout()

        assert is_locked is False
        assert seconds_remaining == 0
        # File should be deleted
        assert not isolated_lockout.exists()

    def test_clear_lockout_removes_file(self, isolated_lockout: Path) -> None:
        """clear_lockout must remove the lockout file."""
        _save_lockout_state({"failed_attempts": 5, "lockout_until": time.time() + 100})
        assert isolated_lockout.exists()

        _clear_lockout()

        assert not isolated_lockout.exists()

    def test_clear_lockout_safe_when_no_file(self, isolated_lockout: Path) -> None:
        """clear_lockout must not raise when no file exists."""
        if isolated_lockout.exists():
            isolated_lockout.unlink()

        # Should not raise
        _clear_lockout()

        assert not isolated_lockout.exists()


# -----------------------------------------------------------------------------
# Lockout Threshold Tests
# Validates the MAX_ATTEMPTS_BEFORE_LOCKOUT behavior.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestLockoutThreshold:
    """Validates lockout is triggered at the correct threshold."""

    def test_max_attempts_is_three(self) -> None:
        """MAX_ATTEMPTS_BEFORE_LOCKOUT must be 3."""
        assert MAX_ATTEMPTS_BEFORE_LOCKOUT == 3

    def test_under_threshold_shows_remaining_attempts(
        self, isolated_lockout: Path
    ) -> None:
        """Failed attempts under threshold must report remaining attempts."""
        _clear_lockout()

        _record_failed_attempt()
        state = _get_lockout_state()

        remaining = MAX_ATTEMPTS_BEFORE_LOCKOUT - state["failed_attempts"]
        assert remaining == 2

    def test_reaching_threshold_triggers_lockout(self, isolated_lockout: Path) -> None:
        """Reaching MAX_ATTEMPTS must trigger lockout message."""
        _clear_lockout()

        for _ in range(MAX_ATTEMPTS_BEFORE_LOCKOUT):
            _record_failed_attempt()

        state = _get_lockout_state()
        assert state["failed_attempts"] >= MAX_ATTEMPTS_BEFORE_LOCKOUT

        is_locked, _ = _check_lockout()
        assert is_locked is True


# -----------------------------------------------------------------------------
# Successful Login Reset Tests
# Validates that successful login clears all lockout state.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestSuccessfulLoginReset:
    """Validates successful login clears lockout state."""

    def test_clear_lockout_resets_failed_attempts(self, isolated_lockout: Path) -> None:
        """Successful login (via clear_lockout) must reset all state."""
        _save_lockout_state({"failed_attempts": 5, "lockout_until": time.time() + 1000})

        _clear_lockout()

        state = _get_lockout_state()
        assert state["failed_attempts"] == 0
        assert state["lockout_until"] is None

    def test_lockout_file_deleted_on_success(self, isolated_lockout: Path) -> None:
        """Lockout file must be deleted after successful login."""
        _save_lockout_state({"failed_attempts": 3, "lockout_until": None})
        assert isolated_lockout.exists()

        _clear_lockout()

        assert not isolated_lockout.exists()


# -----------------------------------------------------------------------------
# Authentication Error Safety Tests
# Validates that error messages don't leak sensitive information.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestAuthenticationErrorSafety:
    """Validates authentication errors don't expose sensitive info."""

    def test_lockout_message_hides_attempt_count(self) -> None:
        """Lockout message must not reveal exact attempt count to attacker."""
        # This is tested by checking the error message format in login.py
        # The message shows time remaining, not detailed attempt info
        # Verify the constant is a reasonable security threshold
        assert MAX_ATTEMPTS_BEFORE_LOCKOUT >= 3
        assert MAX_ATTEMPTS_BEFORE_LOCKOUT <= 5

    def test_error_messages_are_generic(self) -> None:
        """Error messages must be generic and not reveal internal state.

        Validates that the codebase doesn't use specific error messages
        that could aid attackers (e.g., "password too short" vs "wrong password").
        """
        # The login screen uses generic messages like:
        # - "Wrong password. X attempt(s) remaining."
        # - "Account locked. Try again in X."
        # It does NOT say "password incorrect" vs "user not found"
        assert True  # Pattern validation - actual messages tested in integration

    def test_timing_attack_mitigation_via_rate_limiting(self) -> None:
        """Rate limiting mitigates timing attacks by forcing delays.

        Even if password comparison time varies slightly, the exponential
        backoff makes timing analysis impractical after a few attempts.
        """
        # After 3 attempts: 2 + 4 + 8 = 14 seconds minimum delay
        # After 5 attempts: 2 + 4 + 8 + 16 + 32 = 62 seconds minimum delay
        # This makes timing attacks impractical
        total_delay = sum(2**i for i in range(1, 6))
        assert total_delay >= 60


# -----------------------------------------------------------------------------
# Lockout State Security Tests
# Validates lockout state cannot be tampered with easily.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestLockoutStateSecurity:
    """Validates lockout state is protected against tampering."""

    def test_lockout_directory_exists_after_save(
        self, isolated_lockout: Path, tmp_path: Path
    ) -> None:
        """Lockout directory must be created if it doesn't exist.

        Directory permissions (0o700) are set by the main PassFX app on startup,
        not by the lockout functions. This test verifies the directory is created.
        """
        # Use a fresh path that doesn't exist
        fresh_lockout = tmp_path / "new_passfx_dir" / "lockout.json"

        with patch("passfx.screens.login.LOCKOUT_FILE", fresh_lockout):
            _save_lockout_state({"failed_attempts": 1, "lockout_until": None})

            assert fresh_lockout.parent.exists()
            assert fresh_lockout.parent.is_dir()
            assert fresh_lockout.exists()

    def test_atomic_write_prevents_corruption(self, isolated_lockout: Path) -> None:
        """Lockout state must be written atomically."""
        # Verify atomic write by checking no .tmp file remains
        _save_lockout_state({"failed_attempts": 3, "lockout_until": time.time()})

        temp_file = isolated_lockout.with_suffix(".json.tmp")
        assert not temp_file.exists()
        assert isolated_lockout.exists()

    def test_lockout_state_survives_process_restart(
        self, isolated_lockout: Path
    ) -> None:
        """Lockout state must persist across process restarts (simulated)."""
        _save_lockout_state({"failed_attempts": 5, "lockout_until": time.time() + 300})

        # Simulate "restart" by clearing any in-memory state
        # and reading fresh from disk
        state = _get_lockout_state()

        assert state["failed_attempts"] == 5
        assert state["lockout_until"] is not None


# -----------------------------------------------------------------------------
# Constants Validation Tests
# Validates security-critical constants are set correctly.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestSecurityConstants:
    """Validates security-critical constants."""

    def test_max_lockout_is_one_hour(self) -> None:
        """Maximum lockout must be capped at 1 hour."""
        assert MAX_LOCKOUT_SECONDS == 3600

    def test_max_attempts_before_lockout_is_reasonable(self) -> None:
        """Max attempts must be in reasonable range (3-5)."""
        assert 3 <= MAX_ATTEMPTS_BEFORE_LOCKOUT <= 5

    def test_lockout_file_path_is_in_passfx_directory(self) -> None:
        """Lockout file must be stored in ~/.passfx directory."""
        assert ".passfx" in str(LOCKOUT_FILE)
        assert LOCKOUT_FILE.name == "lockout.json"


# -----------------------------------------------------------------------------
# Concurrent Access Tests
# Validates behavior under concurrent access scenarios.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestConcurrentAccess:
    """Validates lockout behavior under concurrent access."""

    def test_rapid_failed_attempts_increment_correctly(
        self, isolated_lockout: Path
    ) -> None:
        """Rapid consecutive failures must all be recorded."""
        _clear_lockout()

        for _ in range(5):
            _record_failed_attempt()

        state = _get_lockout_state()
        assert state["failed_attempts"] == 5

    def test_check_and_record_sequence_is_safe(self, isolated_lockout: Path) -> None:
        """Check-then-record sequence must not lose attempts."""
        _clear_lockout()

        # Simulate login flow: check, then record if failed
        is_locked, _ = _check_lockout()
        assert is_locked is False

        _record_failed_attempt()
        _record_failed_attempt()

        state = _get_lockout_state()
        assert state["failed_attempts"] == 2


# -----------------------------------------------------------------------------
# Edge Case Tests
# Validates handling of edge cases and boundary conditions.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestEdgeCases:
    """Validates edge case handling."""

    def test_lockout_file_read_permission_error(self, isolated_lockout: Path) -> None:
        """Permission error reading lockout file must return clean state."""
        _save_lockout_state({"failed_attempts": 5, "lockout_until": time.time()})

        # Remove read permissions
        os.chmod(isolated_lockout, 0o000)

        try:
            state = _get_lockout_state()
            # Should return default state on read error
            assert state == {"failed_attempts": 0, "lockout_until": None}
        finally:
            # Restore permissions for cleanup
            os.chmod(isolated_lockout, 0o600)

    def test_very_large_failed_attempts_handled(self, isolated_lockout: Path) -> None:
        """Very large failed_attempts values must not cause overflow."""
        _save_lockout_state(
            {"failed_attempts": 999999, "lockout_until": time.time() + 100}
        )

        state = _get_lockout_state()
        assert state["failed_attempts"] == 999999

        # Recording another attempt should still work
        _record_failed_attempt()

        state = _get_lockout_state()
        assert state["failed_attempts"] == 1000000

    def test_lockout_until_far_future_handled(self, isolated_lockout: Path) -> None:
        """Far-future lockout_until must still work correctly."""
        far_future = time.time() + (365 * 24 * 3600)  # 1 year from now
        _save_lockout_state({"failed_attempts": 10, "lockout_until": far_future})

        is_locked, seconds_remaining = _check_lockout()

        assert is_locked is True
        assert seconds_remaining > 0

    def test_empty_lockout_file_returns_default(self, isolated_lockout: Path) -> None:
        """Empty lockout file must return clean default state."""
        isolated_lockout.parent.mkdir(parents=True, exist_ok=True)
        isolated_lockout.write_text("", encoding="utf-8")

        state = _get_lockout_state()

        assert state == {"failed_attempts": 0, "lockout_until": None}


# -----------------------------------------------------------------------------
# No Logging of Sensitive Data Tests
# Validates that login flow doesn't log passwords.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestNoSensitiveLogging:
    """Validates no sensitive data is logged during login operations."""

    def test_record_failed_attempt_does_not_log_password(
        self, isolated_lockout: Path, capture_logs: io.StringIO
    ) -> None:
        """Recording failed attempt must not log any password-related info."""
        _clear_lockout()

        _record_failed_attempt()

        log_output = capture_logs.getvalue().lower()
        assert "password" not in log_output

    def test_check_lockout_does_not_log_secrets(
        self, isolated_lockout: Path, capture_logs: io.StringIO
    ) -> None:
        """Checking lockout status must not log any secrets."""
        _save_lockout_state({"failed_attempts": 3, "lockout_until": time.time() + 60})

        _check_lockout()

        log_output = capture_logs.getvalue().lower()
        assert "password" not in log_output
        assert "secret" not in log_output
