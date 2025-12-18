# Security tests for PassFX threat model validation.
# Validates defensive guarantees against misuse, attack, and adversarial conditions.

from __future__ import annotations

import inspect
import io
import json
import logging
import os
import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from passfx.core.crypto import (
    PBKDF2_ITERATIONS,
    SALT_LENGTH,
    CryptoManager,
    DecryptionError,
    generate_salt,
)
from passfx.core.models import CreditCard, EmailCredential, PhoneCredential
from passfx.core.vault import SaltIntegrityError, Vault, VaultCorruptedError

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
    vault.lock()


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
# Secret Handling Tests
# Validates that secrets never leak through logs, exceptions, or disk writes.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestSecretNeverLogged:
    """Validates that secrets are never exposed in logs."""

    def test_password_not_logged_on_crypto_init(
        self, capture_logs: io.StringIO
    ) -> None:
        """Master password must never appear in logs during initialization."""
        secret_password = "SuperSecret_Password_123!"
        _ = CryptoManager(secret_password)

        log_output = capture_logs.getvalue().lower()
        assert secret_password.lower() not in log_output
        assert "supersecret" not in log_output

    def test_password_not_logged_on_vault_create(
        self, vault: Vault, capture_logs: io.StringIO
    ) -> None:
        """Master password must never appear in logs during vault creation."""
        secret_password = "VaultCreation_Secret_456!"
        vault.create(secret_password)

        log_output = capture_logs.getvalue().lower()
        assert secret_password.lower() not in log_output
        assert "vaultcreation" not in log_output
        vault.lock()

    def test_password_not_logged_on_unlock_failure(
        self, vault: Vault, capture_logs: io.StringIO
    ) -> None:
        """Wrong password must never appear in logs during failed unlock."""
        vault.create("CorrectPassword123!")
        vault.lock()

        wrong_password = "WrongPassword_Attempt_789!"
        with pytest.raises(DecryptionError):
            vault.unlock(wrong_password)

        log_output = capture_logs.getvalue().lower()
        assert wrong_password.lower() not in log_output
        assert "wrongpassword" not in log_output

    def test_credential_password_not_logged_on_save(
        self, unlocked_vault: Vault, capture_logs: io.StringIO
    ) -> None:
        """Credential passwords must never appear in logs during save."""
        cred_password = "CredentialSecret_XYZ_999!"
        email = EmailCredential(
            label="Test",
            email="test@example.com",
            password=cred_password,
        )
        unlocked_vault.add_email(email)

        log_output = capture_logs.getvalue().lower()
        assert cred_password.lower() not in log_output
        assert "credentialsecret" not in log_output


@pytest.mark.security
class TestSecretNeverInExceptions:
    """Validates that secrets never appear in exception messages."""

    def test_decryption_error_hides_password(self) -> None:
        """DecryptionError message must not contain the password."""
        salt = os.urandom(SALT_LENGTH)
        password = "TheActualPassword123!"

        manager1 = CryptoManager(password, salt=salt)
        manager2 = CryptoManager("DifferentPassword!", salt=salt)

        encrypted = manager1.encrypt(b"secret data")

        try:
            manager2.decrypt(encrypted)
            pytest.fail("Expected DecryptionError")
        except DecryptionError as e:
            error_str = str(e).lower()
            assert "theactualpassword" not in error_str
            assert "differentpassword" not in error_str
            assert "secret data" not in error_str

    def test_vault_error_hides_password(self, vault: Vault) -> None:
        """VaultError messages must not contain passwords."""
        password = "VaultPassword_Hidden_123!"
        vault.create(password)
        vault.lock()

        wrong_password = "WrongVaultPassword_456!"
        try:
            vault.unlock(wrong_password)
            pytest.fail("Expected DecryptionError")
        except DecryptionError as e:
            error_str = str(e).lower()
            assert "vaultpassword" not in error_str
            assert "wrongvaultpassword" not in error_str

    def test_credential_not_in_exception_on_corrupt_vault(self, vault: Vault) -> None:
        """Credential data must not appear in corruption exceptions."""
        password = "TestPassword123!"
        vault.create(password)
        email = EmailCredential(
            label="MyBank",
            email="secret@bank.com",
            password="BankingSecret!456",
        )
        vault.add_email(email)
        vault.lock()

        # Corrupt the vault file
        vault.path.write_bytes(os.urandom(100))

        try:
            vault.unlock(password)
            pytest.fail("Expected DecryptionError")
        except (DecryptionError, VaultCorruptedError) as e:
            error_str = str(e).lower()
            assert "mybank" not in error_str
            assert "secret@bank.com" not in error_str
            assert "bankingsecret" not in error_str


@pytest.mark.security
class TestNoPlaintextOnDisk:
    """Validates that plaintext secrets are never written to disk."""

    def test_vault_file_contains_no_plaintext_passwords(
        self, unlocked_vault: Vault
    ) -> None:
        """Vault file must never contain plaintext credential passwords."""
        password = "CredPassword_OnDisk_Test!"
        email = EmailCredential(
            label="DiskTest",
            email="disk@test.com",
            password=password,
        )
        unlocked_vault.add_email(email)

        vault_content = unlocked_vault.path.read_bytes()
        assert password.encode() not in vault_content
        assert b"CredPassword" not in vault_content

    def test_vault_file_contains_no_plaintext_card_numbers(
        self, unlocked_vault: Vault
    ) -> None:
        """Vault file must never contain plaintext card numbers."""
        card_number = "4111222233334444"
        card = CreditCard(
            label="TestCard",
            card_number=card_number,
            expiry="12/25",
            cvv="123",
            cardholder_name="Test User",
        )
        unlocked_vault.add_card(card)

        vault_content = unlocked_vault.path.read_bytes()
        assert card_number.encode() not in vault_content
        assert b"4111222233334444" not in vault_content

    def test_vault_file_contains_no_plaintext_cvv(self, unlocked_vault: Vault) -> None:
        """Vault file must never contain plaintext CVV."""
        cvv = "999"
        card = CreditCard(
            label="CVVTest",
            card_number="5500000000000004",
            expiry="12/25",
            cvv=cvv,
            cardholder_name="CVV Test",
        )
        unlocked_vault.add_card(card)

        vault_content = unlocked_vault.path.read_bytes()
        # CVV is short so check for JSON pattern
        assert b'"cvv": "999"' not in vault_content
        assert b'"cvv":"999"' not in vault_content

    def test_vault_file_contains_no_plaintext_pins(self, unlocked_vault: Vault) -> None:
        """Vault file must never contain plaintext PINs."""
        pin = "54321"
        phone = PhoneCredential(
            label="PINTest",
            phone="+15555555555",
            password=pin,
        )
        unlocked_vault.add_phone(phone)

        vault_content = unlocked_vault.path.read_bytes()
        assert b'"password": "54321"' not in vault_content
        assert b'"password":"54321"' not in vault_content

    def test_salt_file_contains_only_random_bytes(self, vault: Vault) -> None:
        """Salt file must contain only cryptographically random bytes."""
        vault.create("TestPassword123!")

        salt_content = vault._salt_path.read_bytes()

        # Salt should be exactly SALT_LENGTH bytes
        assert len(salt_content) == SALT_LENGTH

        # Salt should not be all zeros or all ones
        assert salt_content != b"\x00" * SALT_LENGTH
        assert salt_content != b"\xff" * SALT_LENGTH

        # Salt should not contain obvious patterns
        assert len(set(salt_content)) > 10  # High entropy check

        vault.lock()


# -----------------------------------------------------------------------------
# Timing Safety Tests
# Validates resistance to timing attacks on password verification.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestTimingSafeComparison:
    """Validates that password comparison uses constant-time operations."""

    def test_verify_password_uses_compare_digest(self) -> None:
        """Password verification must use secrets.compare_digest.

        This is a source-level verification that the implementation uses
        a constant-time comparison function. Actual timing analysis is
        impractical in unit tests due to system noise.
        """
        source = inspect.getsource(CryptoManager.verify_password)
        assert (
            "compare_digest" in source
        ), "verify_password must use secrets.compare_digest for timing safety"

    def test_verify_password_imports_secrets(self) -> None:
        """CryptoManager must import secrets module for compare_digest."""
        import passfx.core.crypto as crypto_module

        # Verify secrets is imported
        assert hasattr(crypto_module, "secrets") or "secrets" in dir(crypto_module)

    def test_wrong_password_still_hashes(self) -> None:
        """Wrong password verification must still compute hash (no short-circuit)."""
        manager = CryptoManager("CorrectPassword!")

        # Both correct and wrong passwords should go through hashing
        # We verify by ensuring verify_password returns a boolean
        # (not raising an exception or short-circuiting on first char)
        result_correct = manager.verify_password("CorrectPassword!")
        result_wrong = manager.verify_password("WrongPassword!")

        assert result_correct is True
        assert result_wrong is False

    def test_password_hash_uses_full_input(self) -> None:
        """Password hashing must use full input (no truncation)."""
        # Passwords differing only at the end should produce different hashes
        manager = CryptoManager("PasswordPrefix_EndingA")

        assert manager.verify_password("PasswordPrefix_EndingA") is True
        assert manager.verify_password("PasswordPrefix_EndingB") is False


# -----------------------------------------------------------------------------
# File Permission Tests
# Validates that file system security is properly enforced.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestFilePermissionEnforcement:
    """Validates secure file permission enforcement."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permissions test")
    def test_vault_file_has_secure_permissions(self, vault: Vault) -> None:
        """Vault file must have 0600 permissions (owner read/write only)."""
        vault.create("TestPassword123!")

        mode = stat.S_IMODE(vault.path.stat().st_mode)
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"
        vault.lock()

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permissions test")
    def test_salt_file_has_secure_permissions(self, vault: Vault) -> None:
        """Salt file must have 0600 permissions (owner read/write only)."""
        vault.create("TestPassword123!")

        mode = stat.S_IMODE(vault._salt_path.stat().st_mode)
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"
        vault.lock()

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permissions test")
    def test_vault_directory_has_secure_permissions(self, vault: Vault) -> None:
        """Vault directory must have 0700 permissions (owner rwx only)."""
        vault.create("TestPassword123!")

        mode = stat.S_IMODE(vault.path.parent.stat().st_mode)
        assert mode == 0o700, f"Expected 0o700, got {oct(mode)}"
        vault.lock()

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permissions test")
    def test_backup_file_has_secure_permissions(self, unlocked_vault: Vault) -> None:
        """Backup file must have 0600 permissions."""
        # Trigger backup creation by modifying vault
        unlocked_vault.add_email(
            EmailCredential(label="Test", email="t@t.com", password="p")
        )

        backup_path = unlocked_vault.path.with_suffix(".enc.bak")
        if backup_path.exists():
            mode = stat.S_IMODE(backup_path.stat().st_mode)
            assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permissions test")
    def test_permissions_set_after_atomic_write(self, unlocked_vault: Vault) -> None:
        """Permissions must be correctly set after atomic write operations."""
        # Multiple saves should maintain correct permissions
        for i in range(3):
            unlocked_vault.add_email(
                EmailCredential(label=f"Test{i}", email=f"t{i}@t.com", password="p")
            )

        mode = stat.S_IMODE(unlocked_vault.path.stat().st_mode)
        assert mode == 0o600


@pytest.mark.security
class TestSymlinkAttackPrevention:
    """Validates protection against symlink attacks."""

    def test_salt_symlink_detected_on_unlock(
        self, vault: Vault, tmp_path: Path
    ) -> None:
        """Salt file symlink must be detected and rejected on unlock."""
        vault.create("TestPassword123!")
        vault.lock()

        # Replace salt with symlink to attacker-controlled file
        fake_salt = tmp_path / "attacker_salt"
        fake_salt.write_bytes(os.urandom(32))
        vault._salt_path.unlink()
        vault._salt_path.symlink_to(fake_salt)

        with pytest.raises(SaltIntegrityError, match="symlink"):
            vault.unlock("TestPassword123!")

    def test_salt_symlink_detected_on_save(
        self, unlocked_vault: Vault, tmp_path: Path
    ) -> None:
        """Salt file symlink must be detected and rejected on save."""
        original_salt = unlocked_vault._salt_path.read_bytes()

        # Replace salt with symlink
        fake_salt = tmp_path / "attacker_salt"
        fake_salt.write_bytes(original_salt)
        unlocked_vault._salt_path.unlink()
        unlocked_vault._salt_path.symlink_to(fake_salt)

        with pytest.raises(SaltIntegrityError, match="symlink"):
            unlocked_vault.add_email(
                EmailCredential(label="Test", email="t@t.com", password="p")
            )


# -----------------------------------------------------------------------------
# Misuse and Abuse Scenario Tests
# Validates graceful handling of malformed, tampered, or malicious input.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestInvalidCiphertextHandling:
    """Validates safe handling of invalid or tampered ciphertext."""

    def test_decrypt_random_bytes_raises_clean_error(self) -> None:
        """Decrypting random bytes must raise DecryptionError without crashing."""
        manager = CryptoManager("TestPassword123!")

        for _ in range(10):
            random_data = os.urandom(100)
            with pytest.raises(DecryptionError):
                manager.decrypt(random_data)

    def test_decrypt_truncated_ciphertext_raises_clean_error(self) -> None:
        """Decrypting truncated ciphertext must raise DecryptionError."""
        manager = CryptoManager("TestPassword123!")
        encrypted = manager.encrypt(b"test data")

        for truncate_at in [1, 10, len(encrypted) // 2, len(encrypted) - 1]:
            truncated = encrypted[:truncate_at]
            with pytest.raises(DecryptionError):
                manager.decrypt(truncated)

    def test_decrypt_corrupted_ciphertext_raises_clean_error(self) -> None:
        """Decrypting corrupted ciphertext must raise DecryptionError."""
        manager = CryptoManager("TestPassword123!")
        encrypted = manager.encrypt(b"test data")

        # Corrupt at various positions
        for position in [0, 10, len(encrypted) // 2, len(encrypted) - 1]:
            corrupted = bytearray(encrypted)
            corrupted[position] ^= 0xFF
            with pytest.raises(DecryptionError):
                manager.decrypt(bytes(corrupted))

    def test_decrypt_empty_bytes_raises_clean_error(self) -> None:
        """Decrypting empty bytes must raise DecryptionError."""
        manager = CryptoManager("TestPassword123!")

        with pytest.raises(DecryptionError):
            manager.decrypt(b"")


@pytest.mark.security
class TestTamperedVaultHandling:
    """Validates safe handling of tampered vault files."""

    def test_tampered_vault_file_raises_error(self, vault: Vault) -> None:
        """Tampered vault file must raise DecryptionError on unlock."""
        password = "TestPassword123!"
        vault.create(password)
        vault.add_email(
            EmailCredential(label="Secret", email="s@s.com", password="secret!")
        )
        vault.lock()

        # Tamper with vault file
        original = vault.path.read_bytes()
        tampered = bytearray(original)
        tampered[len(tampered) // 2] ^= 0xFF
        vault.path.write_bytes(bytes(tampered))

        with pytest.raises(DecryptionError):
            vault.unlock(password)

    def test_modified_salt_detected_on_save(self, unlocked_vault: Vault) -> None:
        """Modified salt file must be detected when saving."""
        original_salt = unlocked_vault._salt_path.read_bytes()

        # Modify salt while vault is unlocked
        new_salt = os.urandom(32)
        unlocked_vault._salt_path.write_bytes(new_salt)

        with pytest.raises(SaltIntegrityError, match="modified"):
            unlocked_vault.add_email(
                EmailCredential(label="Test", email="t@t.com", password="p")
            )

        # Restore for cleanup
        unlocked_vault._salt_path.write_bytes(original_salt)

    def test_deleted_salt_detected_on_save(self, unlocked_vault: Vault) -> None:
        """Deleted salt file must be detected when saving."""
        unlocked_vault._salt_path.unlink()

        with pytest.raises(SaltIntegrityError, match="deleted"):
            unlocked_vault.add_email(
                EmailCredential(label="Test", email="t@t.com", password="p")
            )

    def test_invalid_json_in_vault_raises_error(self, vault: Vault) -> None:
        """Invalid JSON in decrypted vault must raise VaultCorruptedError."""
        password = "TestPassword123!"
        vault.create(password)
        salt = vault._salt_path.read_bytes()
        vault.lock()

        # Encrypt invalid JSON
        crypto = CryptoManager(password, salt=salt)
        vault.path.write_bytes(crypto.encrypt(b"not valid json at all"))

        with pytest.raises(VaultCorruptedError, match="corrupted"):
            vault.unlock(password)


@pytest.mark.security
class TestMalformedInputHandling:
    """Validates safe handling of malformed or edge-case inputs."""

    def test_very_long_password_handled(self) -> None:
        """Very long passwords must be handled without crashing."""
        long_password = "A" * 100000
        manager = CryptoManager(long_password)

        # Should encrypt and decrypt successfully
        data = b"test"
        assert manager.decrypt(manager.encrypt(data)) == data

    def test_null_bytes_in_password_handled(self) -> None:
        """Passwords with null bytes must be handled safely."""
        null_password = "pass\x00word\x00test"
        manager = CryptoManager(null_password)

        data = b"test"
        assert manager.decrypt(manager.encrypt(data)) == data

    def test_unicode_password_handled(self) -> None:
        """Unicode passwords must be handled correctly."""
        unicode_password = "\U0001F512\U0001F511\U0001F510"  # Lock, key, closed lock
        manager = CryptoManager(unicode_password)

        data = b"test"
        assert manager.decrypt(manager.encrypt(data)) == data

    def test_empty_password_handled(self) -> None:
        """Empty password must be handled (validation is separate concern)."""
        # CryptoManager should not crash on empty password
        # Password strength validation is a separate function
        manager = CryptoManager("")
        data = b"test"
        assert manager.decrypt(manager.encrypt(data)) == data

    def test_binary_data_in_credentials_handled(self, unlocked_vault: Vault) -> None:
        """Binary/special characters in credential fields handled safely."""
        email = EmailCredential(
            label="Binary\x00Test\xff",
            email="test@test.com",
            password="pass\x00\xff\xfe",
            notes="Notes\x00with\xffbinary",
        )
        unlocked_vault.add_email(email)

        # Retrieve and verify
        emails = unlocked_vault.get_emails()
        assert len(emails) == 1
        assert emails[0].password == "pass\x00\xff\xfe"


# -----------------------------------------------------------------------------
# Cryptographic Strength Invariants
# Validates that cryptographic parameters meet security requirements.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestCryptographicStrengthInvariants:
    """Validates cryptographic parameter security requirements."""

    def test_pbkdf2_iterations_meet_owasp_minimum(self) -> None:
        """PBKDF2 iterations must meet OWASP 2023 minimum (480,000)."""
        assert (
            PBKDF2_ITERATIONS >= 480_000
        ), f"PBKDF2 iterations {PBKDF2_ITERATIONS} below OWASP minimum 480,000"

    def test_salt_length_is_256_bits(self) -> None:
        """Salt length must be at least 256 bits (32 bytes)."""
        assert SALT_LENGTH >= 32, f"Salt length {SALT_LENGTH} below 32 bytes"

    def test_generated_salt_is_random(self) -> None:
        """Generated salt must be cryptographically random."""
        salts = [generate_salt() for _ in range(100)]

        # All salts must be unique
        assert len(set(salts)) == 100, "Generated salts are not unique"

        # Each salt must have high entropy (simple check)
        for salt in salts:
            unique_bytes = len(set(salt))
            assert unique_bytes > 15, "Salt has low entropy"

    def test_different_encryptions_produce_different_ciphertext(self) -> None:
        """Encrypting same plaintext must produce different ciphertext (IV uniqueness)."""
        manager = CryptoManager("TestPassword123!")
        plaintext = b"same data"

        ciphertexts = [manager.encrypt(plaintext) for _ in range(100)]

        # All ciphertexts must be unique (different IVs)
        assert len(set(ciphertexts)) == 100, "Ciphertexts are not unique (IV reuse)"

    def test_key_derivation_is_deterministic(self) -> None:
        """Same password and salt must derive same key (reproducibility)."""
        salt = os.urandom(SALT_LENGTH)
        password = "TestPassword123!"

        manager1 = CryptoManager(password, salt=salt)
        manager2 = CryptoManager(password, salt=salt)

        # Cross-decryption should work
        encrypted = manager1.encrypt(b"test")
        assert manager2.decrypt(encrypted) == b"test"


# -----------------------------------------------------------------------------
# Memory Security Tests
# Validates secure memory handling for sensitive data.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestMemorySecurity:
    """Validates secure memory handling."""

    def test_wipe_removes_key_material(self) -> None:
        """wipe() must remove key material from memory."""
        manager = CryptoManager("TestPassword123!")

        assert hasattr(manager, "_key")
        assert hasattr(manager, "_fernet")
        assert hasattr(manager, "_password_hash")

        manager.wipe()

        assert not hasattr(manager, "_key")
        assert not hasattr(manager, "_fernet")
        assert not hasattr(manager, "_password_hash")

    def test_vault_lock_wipes_crypto(self, unlocked_vault: Vault) -> None:
        """Vault lock must wipe crypto manager."""
        assert unlocked_vault._crypto is not None

        unlocked_vault.lock()

        assert unlocked_vault._crypto is None

    def test_vault_lock_clears_cached_salt_hash(self, unlocked_vault: Vault) -> None:
        """Vault lock must clear cached salt hash."""
        assert unlocked_vault._cached_salt_hash is not None

        unlocked_vault.lock()

        assert unlocked_vault._cached_salt_hash is None

    def test_vault_lock_clears_credential_data(self, unlocked_vault: Vault) -> None:
        """Vault lock must clear all credential data from memory."""
        unlocked_vault.add_email(
            EmailCredential(label="Test", email="t@t.com", password="secret!")
        )

        unlocked_vault.lock()

        for category in unlocked_vault._data.values():
            assert category == [], f"Data not cleared: {category}"

    def test_operations_fail_after_wipe(self) -> None:
        """Crypto operations must fail after wipe."""
        manager = CryptoManager("TestPassword123!")
        manager.wipe()

        with pytest.raises(AttributeError):
            manager.encrypt(b"test")


# -----------------------------------------------------------------------------
# Error Isolation Tests
# Validates that errors don't leak internal state.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestErrorIsolation:
    """Validates that errors don't expose internal state."""

    def test_decryption_error_has_no_stack_trace_secrets(self) -> None:
        """DecryptionError should not contain secrets in traceback."""
        salt = os.urandom(SALT_LENGTH)
        secret_password = "VerySecretPassword123!"
        secret_data = b"Super secret data that must not leak"

        manager = CryptoManager(secret_password, salt=salt)
        encrypted = manager.encrypt(secret_data)

        wrong_manager = CryptoManager("WrongPassword!", salt=salt)

        try:
            wrong_manager.decrypt(encrypted)
            pytest.fail("Expected DecryptionError")
        except DecryptionError:
            import traceback

            tb = traceback.format_exc()
            assert "VerySecretPassword" not in tb
            assert "Super secret data" not in tb

    def test_vault_error_does_not_expose_data(self, vault: Vault) -> None:
        """VaultError should not expose stored credentials."""
        vault.create("TestPassword123!")
        vault.add_email(
            EmailCredential(
                label="BankAccount",
                email="bank@secret.com",
                password="BankPassword!99",
            )
        )
        vault.lock()

        # Attempt with wrong password
        try:
            vault.unlock("WrongPassword!")
        except DecryptionError as e:
            full_str = str(e) + repr(e)
            assert "BankAccount" not in full_str
            assert "bank@secret.com" not in full_str
            assert "BankPassword" not in full_str


# -----------------------------------------------------------------------------
# Import Security Tests
# Validates secure handling of import operations.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestImportSecurity:
    """Validates security of import operations."""

    def test_import_rejects_duplicate_ids(self, unlocked_vault: Vault) -> None:
        """Import must reject entries with duplicate IDs (prevents overwrite)."""
        email = EmailCredential(
            label="Original",
            email="original@test.com",
            password="OriginalPass!",
        )
        unlocked_vault.add_email(email)

        # Try to import with same ID but different data
        malicious_import: dict[str, list[dict[str, Any]]] = {
            "emails": [
                {
                    "id": email.id,
                    "label": "Malicious",
                    "email": "malicious@evil.com",
                    "password": "EvilPass!",
                }
            ]
        }

        counts = unlocked_vault.import_data(malicious_import, merge=True)
        assert counts["emails"] == 0

        # Original should be unchanged
        emails = unlocked_vault.get_emails()
        assert len(emails) == 1
        assert emails[0].label == "Original"
        assert emails[0].email == "original@test.com"


# -----------------------------------------------------------------------------
# Serialization Security Tests
# Validates secure serialization practices.
# -----------------------------------------------------------------------------


@pytest.mark.security
class TestSerializationSecurity:
    """Validates secure serialization (no pickle, JSON only)."""

    def test_vault_uses_json_not_pickle(self, vault: Vault) -> None:
        """Vault must use JSON serialization, never pickle."""
        vault.create("TestPassword123!")

        # Read encrypted data and decrypt manually
        salt = vault._salt_path.read_bytes()
        crypto = CryptoManager("TestPassword123!", salt=salt)
        decrypted = crypto.decrypt(vault.path.read_bytes())

        # Should be valid JSON
        data = json.loads(decrypted)
        assert isinstance(data, dict)
        assert "emails" in data

        vault.lock()

    def test_vault_data_is_json_serializable(self, unlocked_vault: Vault) -> None:
        """All vault data must be JSON serializable."""
        unlocked_vault.add_email(
            EmailCredential(label="Test", email="t@t.com", password="p")
        )

        data = unlocked_vault.get_all_data()

        # Should serialize without error
        json_str = json.dumps(data)
        assert json_str is not None

        # Should deserialize back
        restored = json.loads(json_str)
        assert restored == data
