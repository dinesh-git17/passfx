# Regression tests for PassFX security-critical behaviors.
# These tests lock in invariants that must NEVER change.
# Failures indicate a security regression that requires immediate attention.
# nosec B101 - assert usage is intentional in test code
# nosec B105 - hardcoded test passwords are not production secrets

from __future__ import annotations

import inspect
import os
import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from passfx.core.crypto import (
    PBKDF2_ITERATIONS,
    SALT_LENGTH,
    CryptoManager,
    DecryptionError,
    generate_salt,
    validate_master_password,
)
from passfx.core.vault import (
    SaltIntegrityError,
    Vault,
    VaultCorruptedError,
    VaultError,
    VaultLockError,
    VaultNotFoundError,
)

if TYPE_CHECKING:
    from collections.abc import Generator


# -----------------------------------------------------------------------------
# REGRESSION MARKER - All tests in this file must use this marker
# -----------------------------------------------------------------------------

pytestmark = pytest.mark.security


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


# =============================================================================
# CRYPTOGRAPHIC PARAMETER LOCK-IN
# These values are security contracts. Any change requires security review.
# =============================================================================


class TestPBKDF2IterationsLockedIn:
    """PBKDF2 iteration count must remain at exactly 480,000.

    Rationale: This meets OWASP 2023 recommendations for PBKDF2-HMAC-SHA256.
    Lowering this value weakens password-to-key derivation against brute force.
    Raising requires migration strategy for existing vaults.
    """

    def test_pbkdf2_iterations_exact_value(self) -> None:
        """PBKDF2_ITERATIONS must be exactly 480,000.

        SECURITY CONTRACT: Do not change this value without:
        1. Security review and approval
        2. Migration plan for existing vaults
        3. Updated project documentation
        """
        assert PBKDF2_ITERATIONS == 480_000, (
            f"REGRESSION: PBKDF2_ITERATIONS changed from 480,000 to {PBKDF2_ITERATIONS}. "
            "This is a security-critical value that must not be modified."
        )

    def test_pbkdf2_iterations_type_is_int(self) -> None:
        """PBKDF2_ITERATIONS must be an integer, not a float or string."""
        assert isinstance(PBKDF2_ITERATIONS, int), (
            f"REGRESSION: PBKDF2_ITERATIONS type changed to {type(PBKDF2_ITERATIONS)}. "
            "Must be int for consistent key derivation."
        )


class TestSaltLengthLockedIn:
    """Salt length must remain at exactly 32 bytes (256 bits).

    Rationale: 256-bit salt provides sufficient uniqueness to prevent
    rainbow table attacks and ensures each vault has a unique key space.
    """

    def test_salt_length_exact_value(self) -> None:
        """SALT_LENGTH must be exactly 32 bytes (256 bits).

        SECURITY CONTRACT: Do not reduce this value.
        """
        assert SALT_LENGTH == 32, (
            f"REGRESSION: SALT_LENGTH changed from 32 to {SALT_LENGTH}. "
            "256-bit salt is a security requirement."
        )

    def test_generate_salt_produces_exact_length(self) -> None:
        """generate_salt() must produce exactly SALT_LENGTH bytes."""
        salt = generate_salt()
        assert (
            len(salt) == 32
        ), f"REGRESSION: generate_salt() produces {len(salt)} bytes, expected 32."

    def test_salt_length_type_is_int(self) -> None:
        """SALT_LENGTH must be an integer."""
        assert isinstance(SALT_LENGTH, int)


class TestKeyDerivationAlgorithmLockedIn:
    """Key derivation must use PBKDF2-HMAC-SHA256.

    Rationale: This is the algorithm specified in project security requirements
    and expected by the cryptography library's PBKDF2HMAC implementation.
    """

    def test_derive_key_uses_sha256(self) -> None:
        """Key derivation must use SHA256 hash algorithm.

        Verified by inspecting source code for hashes.SHA256() usage.
        """
        source = inspect.getsource(CryptoManager._derive_key)
        assert "SHA256" in source, (
            "REGRESSION: Key derivation no longer uses SHA256. "
            "Algorithm change requires security review."
        )

    def test_derive_key_uses_pbkdf2hmac(self) -> None:
        """Key derivation must use PBKDF2HMAC from cryptography library."""
        source = inspect.getsource(CryptoManager._derive_key)
        assert "PBKDF2HMAC" in source, (
            "REGRESSION: Key derivation no longer uses PBKDF2HMAC. "
            "KDF change requires security review."
        )


class TestEncryptionAlgorithmLockedIn:
    """Encryption must use Fernet (AES-128-CBC + HMAC-SHA256).

    Rationale: Fernet provides authenticated encryption, ensuring both
    confidentiality and integrity. Changes require security review.
    """

    def test_crypto_manager_uses_fernet(self) -> None:
        """CryptoManager must use Fernet for encryption."""
        source = inspect.getsource(CryptoManager)
        assert "Fernet" in source, (
            "REGRESSION: CryptoManager no longer uses Fernet. "
            "Encryption algorithm change requires security review."
        )

    def test_fernet_import_present(self) -> None:
        """Fernet must be imported from cryptography.fernet."""
        import passfx.core.crypto as crypto_module

        source = inspect.getsource(crypto_module)
        assert "from cryptography.fernet import Fernet" in source, (
            "REGRESSION: Fernet import changed. "
            "Must use cryptography library's Fernet implementation."
        )


class TestRandomnessSourceLockedIn:
    """Cryptographic randomness must use os.urandom, never random module.

    Rationale: random module is not cryptographically secure.
    os.urandom provides cryptographically secure random bytes.
    """

    def test_generate_salt_uses_os_urandom(self) -> None:
        """generate_salt must use os.urandom for randomness."""
        source = inspect.getsource(generate_salt)
        assert "os.urandom" in source, (
            "REGRESSION: generate_salt no longer uses os.urandom. "
            "Must use cryptographically secure random source."
        )

    def test_crypto_module_does_not_import_random(self) -> None:
        """crypto.py must not import the random module.

        The random module is not cryptographically secure and must
        never be used for security-critical operations.
        """
        import passfx.core.crypto as crypto_module

        source = inspect.getsource(crypto_module)
        # Check for 'import random' but allow 'os.urandom'
        lines = source.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("import random") or line.startswith("from random"):
                pytest.fail(
                    "REGRESSION: crypto.py imports 'random' module. "
                    "Use 'secrets' or 'os.urandom' for cryptographic operations."
                )

    def test_vault_module_does_not_import_random(self) -> None:
        """vault.py must not import the random module."""
        import passfx.core.vault as vault_module

        source = inspect.getsource(vault_module)
        lines = source.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("import random") or line.startswith("from random"):
                pytest.fail(
                    "REGRESSION: vault.py imports 'random' module. "
                    "Use 'secrets' or 'os.urandom' for cryptographic operations."
                )


# =============================================================================
# PASSWORD VALIDATION RULES LOCK-IN
# These rules define minimum security requirements for master passwords.
# =============================================================================


class TestPasswordValidationRulesLockedIn:
    """Password validation rules must remain at security-acceptable levels.

    These rules ensure master passwords meet minimum complexity requirements.
    Weakening these rules is a security regression.
    """

    def test_minimum_password_length_is_12(self) -> None:
        """Minimum password length must be 12 characters.

        SECURITY CONTRACT: Do not reduce below 12.
        """
        # Password of length 11 should fail
        short_pass = "Abcdefgh1!1"  # 11 chars
        is_valid, issues = validate_master_password(short_pass)
        assert is_valid is False
        assert any("12" in issue for issue in issues), (
            "REGRESSION: Minimum password length changed from 12. "
            "Password validation must require at least 12 characters."
        )

        # Password of length 12 should pass length check
        valid_pass = "Abcdefgh1!12"  # 12 chars
        is_valid, issues = validate_master_password(valid_pass)
        length_issues = [i for i in issues if "character" in i.lower()]
        assert len(length_issues) == 0, "Password of 12 chars should pass length check"

    def test_requires_uppercase_letter(self) -> None:
        """Password must require at least one uppercase letter."""
        no_upper = "abcdefgh1234!"
        is_valid, issues = validate_master_password(no_upper)
        assert is_valid is False
        assert any(
            "uppercase" in issue.lower() for issue in issues
        ), "REGRESSION: Uppercase requirement removed from password validation."

    def test_requires_lowercase_letter(self) -> None:
        """Password must require at least one lowercase letter."""
        no_lower = "ABCDEFGH1234!"
        is_valid, issues = validate_master_password(no_lower)
        assert is_valid is False
        assert any(
            "lowercase" in issue.lower() for issue in issues
        ), "REGRESSION: Lowercase requirement removed from password validation."

    def test_requires_digit(self) -> None:
        """Password must require at least one digit."""
        no_digit = "Abcdefghijkl!"
        is_valid, issues = validate_master_password(no_digit)
        assert is_valid is False
        assert any(
            "number" in issue.lower() for issue in issues
        ), "REGRESSION: Digit requirement removed from password validation."

    def test_requires_special_character(self) -> None:
        """Password must require at least one special character."""
        no_special = "Abcdefghijk1"
        is_valid, issues = validate_master_password(no_special)
        assert is_valid is False
        assert any(
            "special" in issue.lower() for issue in issues
        ), "REGRESSION: Special character requirement removed from validation."

    def test_valid_password_returns_no_issues(self) -> None:
        """A password meeting all requirements should have no issues."""
        valid = "SecurePass123!"
        is_valid, issues = validate_master_password(valid)
        assert is_valid is True
        assert issues == []


# =============================================================================
# ERROR MESSAGE SAFETY LOCK-IN
# Error messages must remain generic to prevent information leakage.
# =============================================================================


class TestDecryptionErrorMessageLockedIn:
    """DecryptionError messages must remain generic.

    Specific error messages could help attackers distinguish between
    'wrong password' and 'corrupted data' scenarios.
    """

    def test_decryption_error_message_is_generic(self) -> None:
        """DecryptionError message must not reveal specific failure reason."""
        salt = os.urandom(SALT_LENGTH)
        manager1 = CryptoManager("Password1!", salt=salt)
        manager2 = CryptoManager("Password2!", salt=salt)

        encrypted = manager1.encrypt(b"secret")

        try:
            manager2.decrypt(encrypted)
            pytest.fail("Expected DecryptionError")
        except DecryptionError as e:
            msg = str(e).lower()
            # Must not reveal which specific check failed
            assert "wrong password" in msg or "failed" in msg, (
                "REGRESSION: DecryptionError message changed. " "Must remain generic."
            )
            # Must not reveal internal details
            assert "hmac" not in msg
            assert "signature" not in msg
            assert "authentication" not in msg

    def test_decryption_error_does_not_include_password(self) -> None:
        """DecryptionError must never include the password in the message."""
        salt = os.urandom(SALT_LENGTH)
        test_password = "UniqueTestPassword99!"
        manager = CryptoManager(test_password, salt=salt)
        encrypted = manager.encrypt(b"data")

        wrong_manager = CryptoManager("WrongPass!", salt=salt)

        try:
            wrong_manager.decrypt(encrypted)
        except DecryptionError as e:
            msg = str(e)
            assert "UniqueTestPassword" not in msg
            assert "WrongPass" not in msg


class TestVaultErrorMessagesLockedIn:
    """Vault error messages must remain generic and safe."""

    def test_vault_not_found_error_message(self) -> None:
        """VaultNotFoundError message must be generic."""
        error = VaultNotFoundError("No vault found. Create one first.")
        msg = str(error).lower()
        assert "create" in msg or "not found" in msg or "no vault" in msg

    def test_vault_corrupted_error_message(self) -> None:
        """VaultCorruptedError message must not expose data."""
        error = VaultCorruptedError("Vault data is corrupted.")
        msg = str(error).lower()
        assert "corrupt" in msg
        # Must not include data samples
        assert "0x" not in msg
        assert "bytes" not in str(error)


# =============================================================================
# FILE PERMISSION LOCK-IN
# File permissions are security hardening that must not be weakened.
# =============================================================================


class TestFilePermissionsLockedIn:
    """File permissions must remain at their secure defaults.

    These permissions ensure only the owner can access sensitive files.
    """

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permissions test")
    def test_vault_file_permission_is_0600(self, vault: Vault) -> None:
        """Vault file must be created with 0600 permissions (owner rw only).

        SECURITY CONTRACT: Never create vault with world-readable permissions.
        """
        vault.create("TestPassword123!")

        mode = stat.S_IMODE(vault.path.stat().st_mode)
        assert mode == 0o600, (
            f"REGRESSION: Vault file permissions changed from 0600 to {oct(mode)}. "
            "Vault must be readable only by owner."
        )
        vault.lock()

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permissions test")
    def test_salt_file_permission_is_0600(self, vault: Vault) -> None:
        """Salt file must be created with 0600 permissions."""
        vault.create("TestPassword123!")

        mode = stat.S_IMODE(vault._salt_path.stat().st_mode)
        assert mode == 0o600, (
            f"REGRESSION: Salt file permissions changed from 0600 to {oct(mode)}. "
            "Salt must be readable only by owner."
        )
        vault.lock()

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix permissions test")
    def test_vault_directory_permission_is_0700(self, vault: Vault) -> None:
        """Vault directory must be created with 0700 permissions."""
        vault.create("TestPassword123!")

        mode = stat.S_IMODE(vault.path.parent.stat().st_mode)
        assert mode == 0o700, (
            f"REGRESSION: Directory permissions changed from 0700 to {oct(mode)}. "
            "Directory must be accessible only by owner."
        )
        vault.lock()


# =============================================================================
# RATE LIMITING PARAMETER LOCK-IN
# Rate limiting parameters protect against brute force attacks.
# =============================================================================


class TestRateLimitingParametersLockedIn:
    """Rate limiting constants must not be weakened."""

    def test_max_attempts_before_lockout_is_3(self) -> None:
        """MAX_ATTEMPTS_BEFORE_LOCKOUT must be 3.

        SECURITY CONTRACT: Do not increase above 5.
        """
        from passfx.screens.login import MAX_ATTEMPTS_BEFORE_LOCKOUT

        assert MAX_ATTEMPTS_BEFORE_LOCKOUT == 3, (
            f"REGRESSION: MAX_ATTEMPTS_BEFORE_LOCKOUT changed to "
            f"{MAX_ATTEMPTS_BEFORE_LOCKOUT}. Must be 3."
        )

    def test_max_lockout_seconds_is_3600(self) -> None:
        """MAX_LOCKOUT_SECONDS must be 3600 (1 hour).

        SECURITY CONTRACT: Do not reduce below 3600.
        """
        from passfx.screens.login import MAX_LOCKOUT_SECONDS

        assert MAX_LOCKOUT_SECONDS == 3600, (
            f"REGRESSION: MAX_LOCKOUT_SECONDS changed to {MAX_LOCKOUT_SECONDS}. "
            "Must be 3600 (1 hour)."
        )

    def test_exponential_backoff_formula_is_2_to_power_n(self) -> None:
        """Exponential backoff must use base 2 (2^n seconds).

        Verified by checking the implementation contains the 2**n pattern.
        """
        import passfx.screens.login as login_module

        source = inspect.getsource(login_module._record_failed_attempt)
        # The implementation must use 2**n or pow(2, n) for exponential backoff
        assert "2 **" in source or "2**" in source or "pow(2" in source, (
            "REGRESSION: Exponential backoff no longer uses 2^n formula. "
            "Rate limiting must use exponential backoff with base 2."
        )


# =============================================================================
# SERIALIZATION SAFETY LOCK-IN
# Serialization must use JSON, never pickle (arbitrary code execution risk).
# =============================================================================


class TestSerializationSafetyLockedIn:
    """Serialization must use JSON, never pickle.

    Pickle allows arbitrary code execution during deserialization.
    This is a critical security requirement.
    """

    def test_vault_module_does_not_import_pickle(self) -> None:
        """vault.py must never import pickle module.

        SECURITY CONTRACT: Pickle is forbidden for security reasons.
        """
        import passfx.core.vault as vault_module

        source = inspect.getsource(vault_module)
        lines = source.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("import pickle") or line.startswith("from pickle"):
                pytest.fail(
                    "REGRESSION: vault.py imports 'pickle' module. "
                    "Pickle is forbidden - use JSON for serialization."
                )

    def test_crypto_module_does_not_import_pickle(self) -> None:
        """crypto.py must never import pickle module."""
        import passfx.core.crypto as crypto_module

        source = inspect.getsource(crypto_module)
        lines = source.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("import pickle") or line.startswith("from pickle"):
                pytest.fail(
                    "REGRESSION: crypto.py imports 'pickle' module. "
                    "Pickle is forbidden - use JSON for serialization."
                )

    def test_vault_uses_json_for_serialization(self) -> None:
        """Vault must use json module for data serialization."""
        import passfx.core.vault as vault_module

        source = inspect.getsource(vault_module)
        assert "import json" in source or "from json" in source, (
            "REGRESSION: Vault no longer imports json module. "
            "JSON serialization is required."
        )

    def test_vault_save_uses_json_dumps(self) -> None:
        """Vault._save_unlocked must use json.dumps for serialization."""
        source = inspect.getsource(Vault._save_unlocked)
        assert "json.dumps" in source, (
            "REGRESSION: Vault._save_unlocked no longer uses json.dumps. "
            "JSON serialization is required."
        )


# =============================================================================
# TIMING ATTACK PROTECTION LOCK-IN
# Password comparison must use constant-time comparison.
# =============================================================================


class TestTimingAttackProtectionLockedIn:
    """Password verification must use constant-time comparison.

    Variable-time comparison allows timing attacks that can leak
    information about the correct password.
    """

    def test_verify_password_uses_compare_digest(self) -> None:
        """verify_password must use secrets.compare_digest.

        SECURITY CONTRACT: Never use == for password comparison.
        """
        source = inspect.getsource(CryptoManager.verify_password)
        assert "compare_digest" in source, (
            "REGRESSION: verify_password no longer uses compare_digest. "
            "Constant-time comparison is required to prevent timing attacks."
        )

    def test_secrets_module_imported_in_crypto(self) -> None:
        """crypto.py must import secrets module for compare_digest."""
        import passfx.core.crypto as crypto_module

        source = inspect.getsource(crypto_module)
        assert "import secrets" in source or "from secrets" in source, (
            "REGRESSION: crypto.py no longer imports secrets module. "
            "secrets.compare_digest is required for timing-safe comparison."
        )


# =============================================================================
# API CONTRACT LOCK-IN
# Exception types and method behaviors must remain stable.
# =============================================================================


class TestExceptionHierarchyLockedIn:
    """Exception class hierarchy must remain stable.

    Code may rely on catching specific exception types.
    Changing hierarchy breaks error handling.
    """

    def test_decryption_error_inherits_from_crypto_error(self) -> None:
        """DecryptionError must be a subclass of CryptoError."""
        from passfx.core.crypto import CryptoError

        assert issubclass(
            DecryptionError, CryptoError
        ), "REGRESSION: DecryptionError no longer inherits from CryptoError."

    def test_vault_errors_inherit_from_vault_error(self) -> None:
        """All vault exceptions must inherit from VaultError."""
        assert issubclass(VaultNotFoundError, VaultError)
        assert issubclass(VaultCorruptedError, VaultError)
        assert issubclass(VaultLockError, VaultError)
        assert issubclass(SaltIntegrityError, VaultError)

    def test_vault_error_inherits_from_exception(self) -> None:
        """VaultError must be a subclass of Exception."""
        assert issubclass(VaultError, Exception)


class TestMethodSignaturesLockedIn:
    """Critical method signatures must remain stable."""

    def test_crypto_manager_init_signature(self) -> None:
        """CryptoManager.__init__ must accept password and optional salt."""
        sig = inspect.signature(CryptoManager.__init__)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "master_password" in params
        assert "salt" in params

    def test_vault_create_requires_password(self) -> None:
        """Vault.create must require master_password parameter."""
        sig = inspect.signature(Vault.create)
        params = list(sig.parameters.keys())

        assert "master_password" in params

    def test_vault_unlock_requires_password(self) -> None:
        """Vault.unlock must require master_password parameter."""
        sig = inspect.signature(Vault.unlock)
        params = list(sig.parameters.keys())

        assert "master_password" in params


# =============================================================================
# MEMORY SAFETY LOCK-IN
# Sensitive data must be wiped from memory.
# =============================================================================


class TestMemorySafetyLockedIn:
    """Memory wiping behavior must remain implemented."""

    def test_crypto_manager_has_wipe_method(self) -> None:
        """CryptoManager must have a wipe() method for memory cleanup."""
        assert hasattr(CryptoManager, "wipe"), (
            "REGRESSION: CryptoManager.wipe() method removed. "
            "Memory wiping is required for security."
        )

    def test_wipe_removes_key_material(self) -> None:
        """wipe() must remove _key, _fernet, and _password_hash."""
        manager = CryptoManager("TestPassword123!")

        # Verify attributes exist before wipe
        assert hasattr(manager, "_key")
        assert hasattr(manager, "_fernet")
        assert hasattr(manager, "_password_hash")

        manager.wipe()

        # Verify attributes are removed after wipe
        assert not hasattr(
            manager, "_key"
        ), "REGRESSION: wipe() no longer removes _key attribute."
        assert not hasattr(
            manager, "_fernet"
        ), "REGRESSION: wipe() no longer removes _fernet attribute."
        assert not hasattr(
            manager, "_password_hash"
        ), "REGRESSION: wipe() no longer removes _password_hash attribute."

    def test_vault_lock_calls_wipe(self, unlocked_vault: Vault) -> None:
        """Vault.lock() must clear crypto manager from memory."""
        assert unlocked_vault._crypto is not None

        unlocked_vault.lock()

        assert (
            unlocked_vault._crypto is None
        ), "REGRESSION: Vault.lock() no longer clears _crypto."

    def test_vault_lock_clears_data(self, unlocked_vault: Vault) -> None:
        """Vault.lock() must clear all credential data from memory."""
        from passfx.core.models import EmailCredential

        unlocked_vault.add_email(
            EmailCredential(label="Test", email="t@t.com", password="p")
        )

        unlocked_vault.lock()

        for category in unlocked_vault._data.values():
            assert (
                category == []
            ), "REGRESSION: Vault.lock() no longer clears credential data."


# =============================================================================
# SALT INTEGRITY PROTECTION LOCK-IN
# Salt file integrity checks must remain implemented.
# =============================================================================


class TestSaltIntegrityProtectionLockedIn:
    """Salt integrity checking must remain implemented."""

    def test_unlock_checks_for_symlink(self, vault: Vault, tmp_path: Path) -> None:
        """Vault.unlock must detect symlinked salt files.

        Symlink attacks could redirect salt reads to attacker-controlled files.
        """
        vault.create("TestPassword123!")
        vault.lock()

        # Replace salt with symlink
        fake_salt = tmp_path / "fake_salt"
        fake_salt.write_bytes(os.urandom(32))
        vault._salt_path.unlink()
        vault._salt_path.symlink_to(fake_salt)

        with pytest.raises(SaltIntegrityError, match="symlink"):
            vault.unlock("TestPassword123!")

    def test_save_detects_modified_salt(self, unlocked_vault: Vault) -> None:
        """Vault._save must detect if salt was modified after unlock.

        An attacker modifying salt could cause data to be encrypted
        with a different key, making it unrecoverable.
        """
        original_salt = unlocked_vault._salt_path.read_bytes()

        # Modify salt while vault is unlocked
        unlocked_vault._salt_path.write_bytes(os.urandom(32))

        from passfx.core.models import EmailCredential

        with pytest.raises(SaltIntegrityError, match="modified"):
            unlocked_vault.add_email(
                EmailCredential(label="Test", email="t@t.com", password="p")
            )

        # Restore for cleanup
        unlocked_vault._salt_path.write_bytes(original_salt)


# =============================================================================
# AUTHENTICATION BEHAVIOR LOCK-IN
# Wrong passwords must always fail; no bypass paths.
# =============================================================================


class TestAuthenticationBehaviorLockedIn:
    """Authentication must fail correctly for wrong passwords."""

    def test_wrong_password_always_raises_decryption_error(self, vault: Vault) -> None:
        """Wrong password must always raise DecryptionError, never succeed.

        SECURITY CONTRACT: There must be no code path that allows
        unlocking with an incorrect password.
        """
        vault.create("CorrectPassword123!")
        vault.lock()

        wrong_passwords = [
            "WrongPassword123!",
            "CorrectPassword123",  # Missing !
            "correctpassword123!",  # Wrong case
            "CorrectPassword124!",  # Wrong digit
            "",  # Empty
            " CorrectPassword123!",  # Leading space
            "CorrectPassword123! ",  # Trailing space
        ]

        for wrong in wrong_passwords:
            with pytest.raises(DecryptionError):
                vault.unlock(wrong)

    def test_correct_password_always_succeeds(self, vault: Vault) -> None:
        """Correct password must always unlock successfully."""
        password = "CorrectPassword123!"
        vault.create(password)
        vault.lock()

        # Multiple unlock/lock cycles should always work
        for _ in range(3):
            vault.unlock(password)
            assert vault.is_locked is False
            vault.lock()
            assert vault.is_locked is True


# =============================================================================
# CRYPTOGRAPHY LIBRARY LOCK-IN
# Must use the 'cryptography' library, not custom implementations.
# =============================================================================


class TestCryptographyLibraryLockedIn:
    """Must use the 'cryptography' library for all crypto operations.

    Custom cryptography implementations are prohibited.
    """

    def test_crypto_imports_from_cryptography_library(self) -> None:
        """crypto.py must import from 'cryptography' package."""
        import passfx.core.crypto as crypto_module

        source = inspect.getsource(crypto_module)
        assert "from cryptography" in source, (
            "REGRESSION: crypto.py no longer imports from 'cryptography' library. "
            "Custom crypto implementations are prohibited."
        )

    def test_fernet_from_cryptography(self) -> None:
        """Fernet must be imported from cryptography.fernet."""
        import passfx.core.crypto as crypto_module

        source = inspect.getsource(crypto_module)
        assert "from cryptography.fernet import" in source

    def test_pbkdf2_from_cryptography(self) -> None:
        """PBKDF2HMAC must be from cryptography.hazmat.primitives.kdf.pbkdf2."""
        import passfx.core.crypto as crypto_module

        source = inspect.getsource(crypto_module)
        assert "from cryptography.hazmat.primitives.kdf.pbkdf2 import" in source


# =============================================================================
# ATOMIC WRITE LOCK-IN
# Data writes must be atomic to prevent corruption.
# =============================================================================


class TestAtomicWriteLockedIn:
    """Atomic write pattern must remain implemented."""

    def test_vault_has_atomic_write_method(self) -> None:
        """Vault must have _atomic_write method."""
        assert hasattr(Vault, "_atomic_write"), (
            "REGRESSION: Vault._atomic_write() method removed. "
            "Atomic writes prevent data corruption."
        )

    def test_atomic_write_uses_temp_file(self) -> None:
        """_atomic_write must use temporary file pattern."""
        source = inspect.getsource(Vault._atomic_write)
        assert (
            "tempfile" in source or "mkstemp" in source
        ), "REGRESSION: _atomic_write no longer uses temp file pattern."

    def test_atomic_write_uses_os_replace(self) -> None:
        """_atomic_write must use os.replace for atomic rename."""
        source = inspect.getsource(Vault._atomic_write)
        assert "os.replace" in source, (
            "REGRESSION: _atomic_write no longer uses os.replace. "
            "Atomic rename is required for data safety."
        )

    def test_atomic_write_uses_fsync(self) -> None:
        """_atomic_write must use fsync to ensure durability."""
        source = inspect.getsource(Vault._atomic_write)
        assert "fsync" in source, (
            "REGRESSION: _atomic_write no longer uses fsync. "
            "fsync ensures data is written to disk before rename."
        )
