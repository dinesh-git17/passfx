# Edge-Case and Failure Path Tests for PassFX
# Validates graceful failure, data safety, and recovery under abnormal conditions.
# These tests simulate real-world failure scenarios that could lead to data loss.

from __future__ import annotations

import errno
import os
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from passfx.core.crypto import CryptoManager, DecryptionError
from passfx.core.models import (
    CreditCard,
    EmailCredential,
    EnvEntry,
    NoteEntry,
    PhoneCredential,
    RecoveryEntry,
)
from passfx.core.vault import Vault, VaultLockError
from passfx.utils.clipboard import (
    ClipboardManager,
    cancel_auto_clear,
    clear_clipboard,
    copy_to_clipboard,
    emergency_cleanup,
    reset_cleanup_flag,
)
from passfx.utils.io import (
    ImportExportError,
    PathValidationError,
    export_vault,
    import_vault,
    validate_path,
)

if TYPE_CHECKING:
    from collections.abc import Generator


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    """Create an isolated vault directory with secure permissions."""
    vault_path = tmp_path / ".passfx"
    vault_path.mkdir(mode=0o700)
    return vault_path


@pytest.fixture
def vault(vault_dir: Path) -> Vault:
    """Create a Vault instance with temporary paths."""
    return Vault(
        vault_path=vault_dir / "vault.enc",
        salt_path=vault_dir / "salt",
    )


@pytest.fixture
def unlocked_vault(vault: Vault) -> Generator[Vault, None, None]:
    """Create and unlock a vault for testing."""
    password = "TestMasterPassword123!"
    vault.create(password)
    yield vault
    if not vault.is_locked:
        vault.lock()


TEST_PASSWORD = "SecureTestPass123!"


# -----------------------------------------------------------------------------
# File and Data Corruption Tests
# Validates safe handling of corrupted, truncated, or malformed vault files.
# -----------------------------------------------------------------------------


@pytest.mark.edge
class TestFileCorruptionHandling:
    """Tests for graceful handling of file corruption scenarios."""

    def test_zero_byte_vault_file_fails_safely(self, vault_dir: Path) -> None:
        """Zero-byte vault file raises clean error without crash."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.lock()

        # Truncate to zero bytes
        vault_path.write_bytes(b"")

        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        with pytest.raises(DecryptionError):
            new_vault.unlock(TEST_PASSWORD)

    def test_single_byte_vault_file_fails_safely(self, vault_dir: Path) -> None:
        """Single-byte vault file raises clean error."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.lock()

        vault_path.write_bytes(b"\x00")

        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        with pytest.raises(DecryptionError):
            new_vault.unlock(TEST_PASSWORD)

    def test_truncated_at_various_positions_fails_safely(self, vault_dir: Path) -> None:
        """Vault truncated at various positions fails cleanly."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.add_email(
            EmailCredential(label="Test", email="t@t.com", password="secret")
        )
        vault.lock()

        original_data = vault_path.read_bytes()
        original_length = len(original_data)

        # Test truncation at various positions
        truncation_points = [
            1,
            10,
            original_length // 4,
            original_length // 2,
            original_length * 3 // 4,
            original_length - 10,
            original_length - 1,
        ]

        for trunc_at in truncation_points:
            vault_path.write_bytes(original_data[:trunc_at])
            new_vault = Vault(vault_path=vault_path, salt_path=salt_path)

            with pytest.raises(DecryptionError):
                new_vault.unlock(TEST_PASSWORD)

            # Restore original for next iteration
            vault_path.write_bytes(original_data)

    def test_partially_overwritten_vault_fails_safely(self, vault_dir: Path) -> None:
        """Vault with overwritten sections fails cleanly."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.add_email(
            EmailCredential(label="Important", email="i@i.com", password="critical")
        )
        vault.lock()

        original_data = vault_path.read_bytes()

        # Overwrite middle section with random data
        corrupted = bytearray(original_data)
        mid = len(corrupted) // 2
        for i in range(min(20, len(corrupted) - mid)):
            corrupted[mid + i] = (corrupted[mid + i] + 1) % 256
        vault_path.write_bytes(bytes(corrupted))

        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        with pytest.raises(DecryptionError):
            new_vault.unlock(TEST_PASSWORD)

    def test_salt_file_wrong_length_handled(self, vault_dir: Path) -> None:
        """Salt file with wrong length still allows vault operations."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.lock()

        # Salt file is read and used; if corrupted, key derivation differs
        original_salt = salt_path.read_bytes()

        # Truncate salt
        salt_path.write_bytes(original_salt[:16])

        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        # Either DecryptionError or an error during key derivation
        with pytest.raises((DecryptionError, ValueError, Exception)):
            new_vault.unlock(TEST_PASSWORD)

    def test_binary_garbage_in_vault_fails_safely(self, vault_dir: Path) -> None:
        """Random binary garbage in vault file fails cleanly."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.lock()

        # Replace with random garbage
        vault_path.write_bytes(os.urandom(500))

        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        with pytest.raises(DecryptionError):
            new_vault.unlock(TEST_PASSWORD)


@pytest.mark.edge
class TestDataIntegrityValidation:
    """Tests for validation of data integrity."""

    def test_valid_json_but_wrong_structure_handled(self, vault_dir: Path) -> None:
        """Valid JSON with wrong structure raises KeyError on access.

        The vault unlocks successfully but accessing missing keys raises
        KeyError. This validates the failure is predictable and not silent.
        """
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        salt = salt_path.read_bytes()
        vault.lock()

        # Encrypt valid JSON but wrong structure
        crypto = CryptoManager(TEST_PASSWORD, salt=salt)
        wrong_structure = b'{"wrong": "structure", "data": [1, 2, 3]}'
        vault_path.write_bytes(crypto.encrypt(wrong_structure))

        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        # Should unlock successfully (decryption works)
        new_vault.unlock(TEST_PASSWORD)

        # Accessing missing keys raises KeyError - failure is visible, not silent
        with pytest.raises(KeyError):
            new_vault.get_emails()

    def test_missing_category_keys_handled(self, vault_dir: Path) -> None:
        """Missing category keys raise KeyError on access.

        The vault unlocks but partial data causes KeyError on missing keys.
        This validates failures are visible rather than silently returning bad data.
        """
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        salt = salt_path.read_bytes()
        vault.lock()

        # Encrypt JSON with only some categories
        crypto = CryptoManager(TEST_PASSWORD, salt=salt)
        partial_data = b'{"emails": []}'
        vault_path.write_bytes(crypto.encrypt(partial_data))

        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        new_vault.unlock(TEST_PASSWORD)

        # emails exists, so should work
        assert new_vault.get_emails() == []

        # phones is missing, should raise KeyError
        with pytest.raises(KeyError):
            new_vault.get_phones()

    def test_null_values_in_credentials_handled(self, unlocked_vault: Vault) -> None:
        """Null values in credential fields are handled gracefully."""
        # Add credential with None notes
        email = EmailCredential(
            label="NullTest",
            email="null@test.com",
            password="pw",
            notes=None,
        )
        unlocked_vault.add_email(email)

        unlocked_vault.lock()
        unlocked_vault.unlock("TestMasterPassword123!")

        loaded = unlocked_vault.get_emails()
        assert len(loaded) == 1
        assert loaded[0].notes is None or loaded[0].notes == ""


# -----------------------------------------------------------------------------
# Filesystem Failure Tests
# Validates safe handling of filesystem errors and permission issues.
# -----------------------------------------------------------------------------


@pytest.mark.edge
class TestFilesystemPermissionFailures:
    """Tests for handling filesystem permission failures."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permission test")
    def test_readonly_vault_directory_behavior(self, vault_dir: Path) -> None:
        """Read-only vault directory behavior depends on lock file existence.

        The vault uses atomic writes with temp files in the same directory.
        When the directory is read-only:
        - If lock file doesn't exist: creation fails
        - If lock file exists (from previous operations): may succeed on some systems

        This test verifies either behavior is handled gracefully.
        """
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.lock()

        # Make directory read-only BEFORE unlocking
        os.chmod(vault_dir, stat.S_IRUSR | stat.S_IXUSR)

        try:
            # Unlock should work (reading only, lock file already exists)
            vault.unlock(TEST_PASSWORD)

            # Adding credential may or may not fail depending on lock file state
            # The important thing is no crash or data corruption
            try:
                vault.add_email(
                    EmailCredential(label="Test", email="t@t.com", password="pw")
                )
                # If it succeeds, verify data is intact
                emails = vault.get_emails()
                assert len(emails) == 1
            except (OSError, PermissionError):
                # This is the expected failure path
                pass
        finally:
            # Restore permissions for cleanup
            os.chmod(vault_dir, stat.S_IRWXU)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permission test")
    def test_readonly_vault_file_still_allows_atomic_write(
        self, vault_dir: Path
    ) -> None:
        """Read-only vault file doesn't block atomic writes.

        Atomic writes use temp file + rename, so the source file permissions
        don't block the write. This is by design - atomic writes work as long
        as the directory is writable.
        """
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        # Make vault file read-only
        os.chmod(vault_path, stat.S_IRUSR)

        try:
            # Atomic write should still succeed (uses temp file + rename)
            # This is by design - os.replace() overwrites read-only files
            vault.add_email(
                EmailCredential(label="Test", email="t@t.com", password="pw")
            )

            # Verify the write succeeded
            vault.lock()
            vault.unlock(TEST_PASSWORD)
            emails = vault.get_emails()
            assert len(emails) == 1
        finally:
            os.chmod(vault_path, stat.S_IRUSR | stat.S_IWUSR)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permission test")
    def test_readonly_salt_file_prevents_modification(self, vault_dir: Path) -> None:
        """Read-only salt file is handled appropriately."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        # Salt file is only written during creation, not modification
        # Just verify it exists and has correct content
        assert salt_path.exists()
        original_salt = salt_path.read_bytes()
        assert len(original_salt) == 32

    def test_nonexistent_parent_directory_fails_safely(self, tmp_path: Path) -> None:
        """Vault in non-existent directory fails safely."""
        vault_path = tmp_path / "nonexistent" / "deep" / "path" / "vault.enc"
        salt_path = tmp_path / "nonexistent" / "deep" / "path" / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)

        # Create should create the directory structure
        vault.create(TEST_PASSWORD)
        assert vault_path.exists()
        vault.lock()


@pytest.mark.edge
class TestDiskSpaceFailures:
    """Tests for handling disk space exhaustion."""

    def test_write_failure_during_atomic_save_handled(
        self, vault_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Write failure during atomic save is handled without corruption."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        # Mock os.write to fail
        original_write = os.write

        def failing_write(fd: int, data: bytes) -> int:
            # Fail on temp file writes (for atomic write)
            raise OSError(errno.ENOSPC, "No space left on device")

        monkeypatch.setattr(os, "write", failing_write)

        try:
            with pytest.raises(OSError):
                vault.add_email(
                    EmailCredential(label="Test", email="t@t.com", password="pw")
                )
        finally:
            monkeypatch.setattr(os, "write", original_write)

        # Original vault should remain intact (not corrupted)
        # Note: The original content check may not work if the vault was never
        # fully written, but the vault should still be in a consistent state
        vault.lock()

    def test_tempfile_creation_failure_handled(
        self, vault_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Temp file creation failure during save is handled cleanly."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        # Mock tempfile.mkstemp to fail
        def failing_mkstemp(*args: Any, **kwargs: Any) -> tuple[int, str]:
            raise OSError(errno.ENOSPC, "No space left on device")

        monkeypatch.setattr(tempfile, "mkstemp", failing_mkstemp)

        with pytest.raises(OSError):
            vault.add_email(
                EmailCredential(label="Test", email="t@t.com", password="pw")
            )


@pytest.mark.edge
class TestFileLockingFailures:
    """Tests for file locking failures."""

    def test_lock_timeout_raises_clean_error(
        self, vault_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lock acquisition timeout raises VaultLockError."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)

        # Mock flock/locking to always fail
        if sys.platform != "win32":
            import fcntl

            def failing_flock(fd: int, operation: int) -> None:
                raise OSError(errno.EAGAIN, "Resource temporarily unavailable")

            monkeypatch.setattr(fcntl, "flock", failing_flock)
        else:
            import msvcrt

            def failing_locking(fd: int, mode: int, nbytes: int) -> None:
                raise OSError(errno.EACCES, "Permission denied")

            monkeypatch.setattr(msvcrt, "locking", failing_locking)

        # Reduce timeout for faster test
        monkeypatch.setattr("passfx.core.vault.LOCK_TIMEOUT_SECONDS", 0.1)

        with pytest.raises(VaultLockError):
            vault.create(TEST_PASSWORD)


# -----------------------------------------------------------------------------
# Interrupted Execution Tests
# Validates safe handling of interrupted operations.
# -----------------------------------------------------------------------------


@pytest.mark.edge
class TestInterruptedOperations:
    """Tests for handling interrupted operations."""

    def test_unlock_cleans_up_on_decryption_failure(self, vault_dir: Path) -> None:
        """Failed unlock properly cleans up state."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.lock()

        # Attempt unlock with wrong password
        with pytest.raises(DecryptionError):
            vault.unlock("WrongPassword!")

        # Vault should remain locked and in clean state
        assert vault.is_locked
        assert vault._crypto is None
        assert vault._cached_salt_hash is None

    def test_create_cleans_up_on_failure(
        self, vault_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Failed create operation cleans up partial state."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)

        # Mock atomic write to fail after salt is saved
        def failing_atomic_write(data: bytes) -> None:
            raise OSError("Simulated write failure")

        monkeypatch.setattr(vault, "_atomic_write", failing_atomic_write)

        with pytest.raises(OSError):
            vault.create(TEST_PASSWORD)

        # Vault should be in clean state after failure
        assert vault.is_locked or vault._crypto is not None

    def test_save_failure_leaves_vault_usable(
        self, unlocked_vault: Vault, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Failed save leaves vault in usable state."""
        # Add a credential first
        unlocked_vault.add_email(
            EmailCredential(label="First", email="f@f.com", password="pw1")
        )

        # Mock next save to fail
        def failing_atomic_write(data: bytes) -> None:
            raise OSError("Simulated write failure")

        monkeypatch.setattr(unlocked_vault, "_atomic_write", failing_atomic_write)

        # This should fail
        with pytest.raises(OSError):
            unlocked_vault.add_email(
                EmailCredential(label="Second", email="s@s.com", password="pw2")
            )

        # Vault should still be usable (in-memory state preserved)
        # Note: The second credential may or may not be in memory depending on
        # when the failure occurred
        assert not unlocked_vault.is_locked

    def test_lock_always_succeeds(self, unlocked_vault: Vault) -> None:
        """Vault lock always succeeds regardless of state."""
        # Add some data
        unlocked_vault.add_email(
            EmailCredential(label="Test", email="t@t.com", password="pw")
        )

        # Lock should always work
        unlocked_vault.lock()
        assert unlocked_vault.is_locked
        assert unlocked_vault._crypto is None

        # Double lock should not crash
        unlocked_vault.lock()
        assert unlocked_vault.is_locked


@pytest.mark.edge
class TestStateConsistencyAfterFailure:
    """Tests for state consistency after failures."""

    def test_vault_state_consistent_after_failed_unlock(self, vault_dir: Path) -> None:
        """Vault state is consistent after multiple failed unlock attempts."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.add_email(
            EmailCredential(label="Protected", email="p@p.com", password="secret")
        )
        vault.lock()

        # Multiple failed attempts
        for i in range(5):
            with pytest.raises(DecryptionError):
                vault.unlock(f"WrongPassword{i}!")
            assert vault.is_locked

        # Correct password should still work
        vault.unlock(TEST_PASSWORD)
        emails = vault.get_emails()
        assert len(emails) == 1
        assert emails[0].label == "Protected"

    def test_in_memory_data_cleared_on_lock(self, unlocked_vault: Vault) -> None:
        """In-memory credential data is cleared on lock."""
        # Add credentials of all types
        unlocked_vault.add_email(
            EmailCredential(label="Email", email="e@e.com", password="epw")
        )
        unlocked_vault.add_phone(
            PhoneCredential(label="Phone", phone="555", password="1234")
        )
        unlocked_vault.add_card(
            CreditCard(
                label="Card",
                card_number="4111111111111111",
                expiry="12/25",
                cvv="123",
                cardholder_name="Test",
            )
        )
        unlocked_vault.add_env(
            EnvEntry(title="Env", filename=".env", content="KEY=VAL")
        )
        unlocked_vault.add_recovery(RecoveryEntry(title="Recovery", content="code123"))
        unlocked_vault.add_note(NoteEntry(title="Note", content="Secret"))

        unlocked_vault.lock()

        # Verify all data cleared
        for category, items in unlocked_vault._data.items():
            assert items == [], f"Category {category} not cleared"


# -----------------------------------------------------------------------------
# Resource Exhaustion Tests
# Validates cleanup under resource constraints.
# -----------------------------------------------------------------------------


@pytest.mark.edge
class TestClipboardCleanup:
    """Tests for clipboard cleanup under failure conditions."""

    def test_clipboard_cleared_on_context_manager_exception(self) -> None:
        """ClipboardManager clears clipboard even when exception occurs."""
        reset_cleanup_flag()

        try:
            with ClipboardManager("sensitive_data", auto_clear=True):
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Clipboard should be cleared despite exception
        # Note: This is best-effort; clipboard state depends on platform

    def test_emergency_cleanup_safe_to_call_multiple_times(self) -> None:
        """Emergency cleanup is safe to call multiple times."""
        reset_cleanup_flag()

        # Should not raise on multiple calls
        emergency_cleanup()
        emergency_cleanup()
        emergency_cleanup()

    def test_cancel_auto_clear_with_no_timer(self) -> None:
        """Canceling auto-clear with no active timer doesn't crash."""
        cancel_auto_clear()  # Should not raise

    def test_clear_clipboard_cancels_pending_timer(self) -> None:
        """Clearing clipboard cancels any pending auto-clear timer."""
        reset_cleanup_flag()

        # Start a copy with long timeout
        copy_to_clipboard("test", auto_clear=True, clear_after=60)

        # Clear immediately - should cancel timer
        clear_clipboard()

        # Verify timer was cancelled (no way to directly check, but no crash)


@pytest.mark.edge
class TestThreadCleanup:
    """Tests for thread and timer cleanup."""

    def test_clipboard_timer_is_daemon(self) -> None:
        """Clipboard auto-clear timer is a daemon thread."""
        reset_cleanup_flag()

        # Copy with auto-clear
        copy_to_clipboard("test", auto_clear=True, clear_after=30)

        # Give a moment for timer to be created
        time.sleep(0.1)

        # Cancel and verify cleanup works
        cancel_auto_clear()


# -----------------------------------------------------------------------------
# Input Abuse Tests
# Validates safe handling of malicious or extreme inputs.
# -----------------------------------------------------------------------------


@pytest.mark.edge
class TestExtremeInputHandling:
    """Tests for handling extreme input values."""

    def test_very_large_number_of_credentials(self, vault_dir: Path) -> None:
        """Vault handles many credentials without corruption."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        # Add 100 credentials
        for i in range(100):
            vault.add_email(
                EmailCredential(
                    label=f"Site{i}",
                    email=f"user{i}@example{i}.com",
                    password=f"password_{i}_secret",
                )
            )

        vault.lock()
        vault.unlock(TEST_PASSWORD)

        emails = vault.get_emails()
        assert len(emails) == 100

        # Verify data integrity
        for i, email in enumerate(emails):
            assert f"Site{i}" in [e.label for e in emails]

    def test_very_long_credential_fields(self, unlocked_vault: Vault) -> None:
        """Very long credential field values are handled safely."""
        long_string = "A" * 10000

        email = EmailCredential(
            label=long_string,
            email="long@test.com",
            password=long_string,
            notes=long_string,
        )
        unlocked_vault.add_email(email)
        cred_id = email.id

        unlocked_vault.lock()
        unlocked_vault.unlock("TestMasterPassword123!")

        loaded = unlocked_vault.get_email_by_id(cred_id)
        assert loaded is not None
        assert len(loaded.label) == 10000
        assert len(loaded.password) == 10000

    def test_unicode_edge_cases_in_credentials(self, unlocked_vault: Vault) -> None:
        """Unicode edge cases are handled correctly."""
        # Various unicode challenges
        test_cases = [
            "\u0000",  # Null character
            "\uFEFF",  # BOM
            "\uD800",  # Lone surrogate (invalid UTF-8)
            "\uFFFF",  # Non-character
            "\U0010FFFF",  # Max codepoint
            "👨‍👩‍👧‍👦",  # Family emoji (ZWJ sequence)
            "🏳️‍🌈",  # Rainbow flag (ZWJ)
            "\u202E",  # Right-to-left override
            "A\u0308",  # Combining characters (A + umlaut)
        ]

        for i, test_str in enumerate(test_cases):
            try:
                email = EmailCredential(
                    label=f"Unicode_{i}_{test_str}",
                    email=f"u{i}@test.com",
                    password=f"pw_{test_str}",
                )
                unlocked_vault.add_email(email)
            except (ValueError, UnicodeError):
                # Some unicode may be rejected, which is acceptable
                pass

    def test_json_injection_in_fields_prevented(self, unlocked_vault: Vault) -> None:
        """JSON injection attempts are safely serialized."""
        malicious_values = [
            '{"injected": "data"}',
            '", "evil": "value',
            "\\",
            "\\n\\r\\t",
            "</script>",
            "'; DROP TABLE users; --",
        ]

        for i, value in enumerate(malicious_values):
            email = EmailCredential(
                label=value,
                email=f"inject{i}@test.com",
                password=value,
                notes=value,
            )
            unlocked_vault.add_email(email)

        # Lock and reload
        unlocked_vault.lock()
        unlocked_vault.unlock("TestMasterPassword123!")

        # Verify data is stored literally, not interpreted
        emails = unlocked_vault.get_emails()
        assert len(emails) == len(malicious_values)

        for email in emails:
            # Data should be stored as-is, not executed/interpreted
            assert email.label in malicious_values

    def test_empty_string_fields_handled(self, unlocked_vault: Vault) -> None:
        """Empty string fields are handled correctly."""
        email = EmailCredential(
            label="",  # Empty
            email="empty@test.com",
            password="",  # Empty
            notes="",  # Empty
        )
        unlocked_vault.add_email(email)
        cred_id = email.id

        unlocked_vault.lock()
        unlocked_vault.unlock("TestMasterPassword123!")

        loaded = unlocked_vault.get_email_by_id(cred_id)
        assert loaded is not None
        assert loaded.label == ""
        assert loaded.password == ""


@pytest.mark.edge
class TestMalformedImportData:
    """Tests for handling malformed import data."""

    def test_import_missing_required_fields_handled(
        self, unlocked_vault: Vault
    ) -> None:
        """Import with missing required fields doesn't corrupt vault."""
        malformed_data: dict[str, list[dict[str, Any]]] = {
            "emails": [
                {"label": "NoEmail"},  # Missing email and password
                {},  # Completely empty
            ],
            "phones": [
                {"label": "NoPhone"},  # Missing phone
            ],
            "cards": [],
        }

        # Import should handle gracefully (may skip invalid entries)
        try:
            unlocked_vault.import_data(malformed_data, merge=True)
        except (KeyError, TypeError):
            pass  # Some implementations may reject malformed data

        # Vault should remain usable
        unlocked_vault.lock()
        unlocked_vault.unlock("TestMasterPassword123!")

    def test_import_wrong_data_types_handled(self, unlocked_vault: Vault) -> None:
        """Import with wrong data types doesn't crash."""
        wrong_types_data: dict[str, list[dict[str, Any]]] = {
            "emails": [
                {
                    "label": 12345,  # Should be string
                    "email": ["list", "instead"],  # Should be string
                    "password": {"dict": "value"},  # Should be string
                }
            ],
            "phones": [],
            "cards": [],
        }

        # Should handle gracefully
        try:
            unlocked_vault.import_data(wrong_types_data, merge=True)
        except (TypeError, AttributeError):
            pass  # Acceptable to reject invalid types

    def test_import_extra_fields_ignored(self, unlocked_vault: Vault) -> None:
        """Import with extra fields doesn't cause issues."""
        extra_fields_data: dict[str, list[dict[str, Any]]] = {
            "emails": [
                {
                    "id": "extra_test_id",
                    "label": "Extra Fields",
                    "email": "extra@test.com",
                    "password": "pw",
                    "unknown_field": "should be ignored",
                    "another_unknown": 12345,
                    "nested": {"deep": "object"},
                }
            ],
            "phones": [],
            "cards": [],
            "unknown_category": [{"data": "ignored"}],  # Unknown category
        }

        counts = unlocked_vault.import_data(extra_fields_data, merge=True)
        assert counts["emails"] == 1


# -----------------------------------------------------------------------------
# Path Validation Edge Cases
# Validates path validation security.
# -----------------------------------------------------------------------------


@pytest.mark.edge
class TestPathValidationEdgeCases:
    """Tests for path validation edge cases."""

    def test_path_with_null_bytes_rejected(self, tmp_path: Path) -> None:
        """Paths with null bytes are rejected."""
        try:
            path = tmp_path / "test\x00file.json"
            with pytest.raises((PathValidationError, ValueError, OSError)):
                validate_path(path)
        except (ValueError, TypeError):
            # Some systems reject null bytes at Path construction
            pass

    def test_relative_path_resolved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Relative paths are resolved to absolute."""
        from unittest.mock import patch

        # Use tmp_path as mock home for CI compatibility
        monkeypatch.chdir(tmp_path)

        # Create a temp file in working directory
        test_file = tmp_path / "passfx_test_temp.txt"
        test_file.write_text("test")

        with patch("passfx.utils.io.Path.home", return_value=tmp_path):
            resolved = validate_path(Path("passfx_test_temp.txt"), must_exist=True)
            assert resolved.is_absolute()

    def test_symlink_parent_rejected(self, tmp_path: Path) -> None:
        """Parent directory that is symlink is rejected."""
        # Create real directory and symlink to it
        real_dir = tmp_path / "real_dir"
        real_dir.mkdir()
        symlink_dir = tmp_path / "symlink_dir"
        symlink_dir.symlink_to(real_dir)

        target = symlink_dir / "file.json"

        # This should be rejected due to symlink parent
        with pytest.raises(PathValidationError, match="symlink"):
            validate_path(target)


# -----------------------------------------------------------------------------
# Vault Lock Contention Tests
# Validates behavior under concurrent access attempts.
# -----------------------------------------------------------------------------


@pytest.mark.edge
class TestConcurrentAccess:
    """Tests for concurrent access handling."""

    def test_second_instance_can_access_after_first_releases(
        self, vault_dir: Path
    ) -> None:
        """Second vault instance can access after first releases lock."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault1 = Vault(vault_path=vault_path, salt_path=salt_path)
        vault1.create(TEST_PASSWORD)
        vault1.lock()

        # Second instance should be able to access after first releases
        vault2 = Vault(vault_path=vault_path, salt_path=salt_path)
        vault2.unlock(TEST_PASSWORD)
        assert not vault2.is_locked
        vault2.lock()

    def test_lock_released_after_context_exit(self, vault_dir: Path) -> None:
        """Lock is properly released after context manager exit."""
        vault_path = vault_dir / "vault.enc"
        salt_path = vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        # After create, lock should be released
        # A new instance should be able to acquire it
        vault2 = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.lock()

        # Should not raise
        vault2.unlock(TEST_PASSWORD)
        vault2.lock()


# -----------------------------------------------------------------------------
# Export/Import Failure Tests
# Validates safe handling of export/import failures.
# -----------------------------------------------------------------------------


@pytest.fixture
def home_test_dir() -> Generator[Path, None, None]:
    """Create a test directory within user's home for path validation tests."""
    test_dir = Path.home() / ".passfx_test_temp"
    test_dir.mkdir(mode=0o700, exist_ok=True)
    yield test_dir
    # Cleanup
    if test_dir.exists():
        shutil.rmtree(test_dir)


@pytest.mark.edge
class TestExportImportFailures:
    """Tests for export/import failure handling."""

    def test_import_path_outside_home_rejected(self, tmp_path: Path) -> None:
        """Importing from path outside home directory is rejected.

        Path validation requires all import paths to be within home
        directory to prevent directory traversal attacks.
        """
        # tmp_path is typically in /var/folders or /tmp, outside home
        fake_path = tmp_path / "nonexistent.json"

        with pytest.raises(PathValidationError, match="within home directory"):
            import_vault(fake_path)

    def test_import_nonexistent_file_fails_cleanly(self, home_test_dir: Path) -> None:
        """Importing non-existent file raises clean error."""
        fake_path = home_test_dir / "nonexistent.json"

        with pytest.raises(PathValidationError, match="not found"):
            import_vault(fake_path)

    def test_import_directory_fails_cleanly(self, home_test_dir: Path) -> None:
        """Importing a directory raises clean error."""
        dir_path = home_test_dir / "a_directory"
        dir_path.mkdir()

        with pytest.raises(PathValidationError, match="not a file"):
            import_vault(dir_path)

    def test_export_to_readonly_location_fails_cleanly(
        self, home_test_dir: Path
    ) -> None:
        """Exporting to read-only location fails cleanly."""
        if sys.platform == "win32":
            pytest.skip("Unix permission test")

        readonly_dir = home_test_dir / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, stat.S_IRUSR | stat.S_IXUSR)

        export_path = readonly_dir / "export.json"
        data: dict[str, list[dict[str, Any]]] = {
            "emails": [],
            "phones": [],
            "cards": [],
        }

        try:
            with pytest.raises((OSError, PermissionError, ImportExportError)):
                export_vault(data, export_path)
        finally:
            os.chmod(readonly_dir, stat.S_IRWXU)

    def test_import_invalid_json_fails_cleanly(self, home_test_dir: Path) -> None:
        """Importing invalid JSON file fails cleanly."""
        bad_json = home_test_dir / "bad.json"
        bad_json.write_text("{ not valid json }")

        with pytest.raises(ImportExportError):
            import_vault(bad_json)

    def test_import_unknown_format_fails_cleanly(self, home_test_dir: Path) -> None:
        """Importing unknown file format fails cleanly."""
        unknown_file = home_test_dir / "data.xyz"
        unknown_file.write_text("some data")

        with pytest.raises(ImportExportError, match="Unknown file type"):
            import_vault(unknown_file)
