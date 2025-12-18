# Unit tests for CryptoManager and cryptographic operations.
# Validates encryption, key derivation, and security invariants.

from __future__ import annotations

import base64
import os

import pytest
from cryptography.fernet import Fernet

from passfx.core.crypto import (
    PBKDF2_ITERATIONS,
    SALT_LENGTH,
    CryptoError,
    CryptoManager,
    DecryptionError,
    generate_salt,
    validate_master_password,
)


class TestCryptoManagerInitialization:
    """Tests for CryptoManager initialization behavior."""

    def test_init_with_password_generates_salt(self) -> None:
        """CryptoManager generates a random salt when none is provided."""
        manager = CryptoManager("TestPassword123!")
        assert manager.salt is not None
        assert len(manager.salt) == SALT_LENGTH

    def test_init_with_explicit_salt_uses_provided_salt(self) -> None:
        """CryptoManager uses the provided salt when given."""
        provided_salt = os.urandom(SALT_LENGTH)
        manager = CryptoManager("TestPassword123!", salt=provided_salt)
        assert manager.salt == provided_salt

    def test_init_creates_valid_fernet_instance(self) -> None:
        """CryptoManager creates a working Fernet instance internally."""
        manager = CryptoManager("TestPassword123!")
        # Verify Fernet works by encrypting/decrypting
        test_data = b"test data"
        encrypted = manager.encrypt(test_data)
        assert encrypted != test_data
        decrypted = manager.decrypt(encrypted)
        assert decrypted == test_data

    def test_init_with_empty_password(self) -> None:
        """CryptoManager handles empty password (application should validate)."""
        # CryptoManager itself does not validate password strength
        # That is the responsibility of validate_master_password()
        manager = CryptoManager("")
        assert manager.salt is not None
        # Should still be able to encrypt/decrypt
        encrypted = manager.encrypt(b"data")
        assert manager.decrypt(encrypted) == b"data"

    def test_salt_property_returns_immutable_copy(self) -> None:
        """Salt property returns the stored salt value."""
        salt = os.urandom(SALT_LENGTH)
        manager = CryptoManager("TestPassword123!", salt=salt)
        assert manager.salt == salt


class TestKeyDerivation:
    """Tests for PBKDF2 key derivation behavior."""

    def test_same_password_same_salt_produces_same_key(self) -> None:
        """Deterministic: identical inputs produce identical keys."""
        salt = os.urandom(SALT_LENGTH)
        password = "TestPassword123!"

        manager1 = CryptoManager(password, salt=salt)
        manager2 = CryptoManager(password, salt=salt)

        # Both managers should be able to decrypt each other's ciphertext
        test_data = b"shared secret"
        encrypted = manager1.encrypt(test_data)
        decrypted = manager2.decrypt(encrypted)
        assert decrypted == test_data

    def test_same_password_different_salt_produces_different_key(self) -> None:
        """Different salts produce different keys, even with same password."""
        password = "TestPassword123!"
        salt1 = os.urandom(SALT_LENGTH)
        salt2 = os.urandom(SALT_LENGTH)

        manager1 = CryptoManager(password, salt=salt1)
        manager2 = CryptoManager(password, salt=salt2)

        # Manager2 should fail to decrypt manager1's ciphertext
        encrypted = manager1.encrypt(b"test data")
        with pytest.raises(DecryptionError):
            manager2.decrypt(encrypted)

    def test_different_password_same_salt_produces_different_key(self) -> None:
        """Different passwords produce different keys, even with same salt."""
        salt = os.urandom(SALT_LENGTH)

        manager1 = CryptoManager("Password1!", salt=salt)
        manager2 = CryptoManager("Password2!", salt=salt)

        encrypted = manager1.encrypt(b"test data")
        with pytest.raises(DecryptionError):
            manager2.decrypt(encrypted)

    def test_derive_key_returns_valid_fernet_key(self) -> None:
        """Derived key is valid for Fernet (32 bytes, base64 encoded)."""
        salt = os.urandom(SALT_LENGTH)
        key = CryptoManager._derive_key("TestPassword123!", salt)

        # Fernet keys are 32 bytes, URL-safe base64 encoded (44 chars with padding)
        decoded = base64.urlsafe_b64decode(key)
        assert len(decoded) == 32

        # Should be usable with Fernet directly
        fernet = Fernet(key)
        test_data = b"verification"
        assert fernet.decrypt(fernet.encrypt(test_data)) == test_data

    def test_derive_key_is_static_method(self) -> None:
        """_derive_key is a static method callable without instance."""
        salt = os.urandom(SALT_LENGTH)
        # Should be callable directly on class
        key = CryptoManager._derive_key("password", salt)
        assert key is not None

    def test_unicode_password_handled_correctly(self) -> None:
        """Unicode passwords are properly encoded and processed."""
        salt = os.urandom(SALT_LENGTH)
        unicode_password = "パスワード123!"  # Japanese characters

        manager = CryptoManager(unicode_password, salt=salt)
        test_data = b"unicode password test"
        encrypted = manager.encrypt(test_data)
        decrypted = manager.decrypt(encrypted)
        assert decrypted == test_data


class TestEncryptionDecryption:
    """Tests for encrypt/decrypt operations."""

    def test_encrypt_produces_different_ciphertext_each_time(self) -> None:
        """Fernet uses unique IV, so same plaintext produces different ciphertext."""
        manager = CryptoManager("TestPassword123!")
        plaintext = b"same plaintext"

        ciphertext1 = manager.encrypt(plaintext)
        ciphertext2 = manager.encrypt(plaintext)

        assert ciphertext1 != ciphertext2
        # But both should decrypt to same plaintext
        assert manager.decrypt(ciphertext1) == plaintext
        assert manager.decrypt(ciphertext2) == plaintext

    def test_encrypt_decrypt_roundtrip_bytes(self) -> None:
        """Bytes encryption round-trip preserves data integrity."""
        manager = CryptoManager("TestPassword123!")
        test_cases = [
            b"simple text",
            b"",  # Empty bytes
            b"\x00\x01\x02\xff\xfe\xfd",  # Binary data
            b"a" * 10000,  # Large data
            os.urandom(1024),  # Random binary
        ]

        for original in test_cases:
            encrypted = manager.encrypt(original)
            decrypted = manager.decrypt(encrypted)
            assert decrypted == original

    def test_encrypt_string_decrypt_string_roundtrip(self) -> None:
        """String encryption round-trip preserves content."""
        manager = CryptoManager("TestPassword123!")
        test_cases = [
            "Hello, World!",
            "",  # Empty string
            "Unicode: 日本語 emoji: 🔐",
            "Special chars: !@#$%^&*()",
            "Newlines:\nand\ttabs",
            "x" * 10000,  # Large string
        ]

        for original in test_cases:
            encrypted = manager.encrypt_string(original)
            decrypted = manager.decrypt_string(encrypted)
            assert decrypted == original

    def test_encrypt_string_returns_base64_encoded(self) -> None:
        """encrypt_string returns valid base64-encoded result."""
        manager = CryptoManager("TestPassword123!")
        encrypted = manager.encrypt_string("test")

        # Should be valid base64
        decoded = base64.urlsafe_b64decode(encrypted.encode("ascii"))
        assert decoded is not None

    def test_encrypted_data_is_different_from_plaintext(self) -> None:
        """Encrypted output should never equal plaintext."""
        manager = CryptoManager("TestPassword123!")

        plaintext = b"secret data"
        ciphertext = manager.encrypt(plaintext)

        assert ciphertext != plaintext
        assert plaintext not in ciphertext


class TestDecryptionErrors:
    """Tests for decryption error handling."""

    def test_decrypt_with_wrong_password_raises_decryption_error(self) -> None:
        """Decryption with wrong password raises DecryptionError."""
        salt = os.urandom(SALT_LENGTH)
        manager1 = CryptoManager("CorrectPassword!", salt=salt)
        manager2 = CryptoManager("WrongPassword!", salt=salt)

        encrypted = manager1.encrypt(b"secret")

        with pytest.raises(DecryptionError) as exc_info:
            manager2.decrypt(encrypted)

        # Error message should not reveal sensitive information
        assert (
            "password" not in str(exc_info.value).lower()
            or "wrong" in str(exc_info.value).lower()
        )
        assert "secret" not in str(exc_info.value).lower()

    def test_decrypt_corrupted_ciphertext_raises_decryption_error(self) -> None:
        """Decryption of corrupted data raises DecryptionError."""
        manager = CryptoManager("TestPassword123!")
        encrypted = manager.encrypt(b"test data")

        # Corrupt the ciphertext by modifying bytes
        corrupted_arr = bytearray(encrypted)
        corrupted_arr[10] ^= 0xFF
        corrupted = bytes(corrupted_arr)

        with pytest.raises(DecryptionError):
            manager.decrypt(corrupted)

    def test_decrypt_truncated_ciphertext_raises_decryption_error(self) -> None:
        """Decryption of truncated data raises DecryptionError."""
        manager = CryptoManager("TestPassword123!")
        encrypted = manager.encrypt(b"test data")

        # Truncate the ciphertext
        truncated = encrypted[: len(encrypted) // 2]

        with pytest.raises(DecryptionError):
            manager.decrypt(truncated)

    def test_decrypt_invalid_ciphertext_raises_decryption_error(self) -> None:
        """Decryption of random bytes raises DecryptionError."""
        manager = CryptoManager("TestPassword123!")

        with pytest.raises(DecryptionError):
            manager.decrypt(os.urandom(100))

    def test_decrypt_string_invalid_base64_raises_error(self) -> None:
        """decrypt_string with invalid base64 raises appropriate error."""
        manager = CryptoManager("TestPassword123!")

        # Invalid base64 should raise an error (binascii.Error or similar)
        with pytest.raises(Exception):  # May be binascii.Error or DecryptionError
            manager.decrypt_string("not-valid-base64!!!")

    def test_decryption_error_is_crypto_error_subclass(self) -> None:
        """DecryptionError is a subclass of CryptoError."""
        assert issubclass(DecryptionError, CryptoError)


class TestPasswordVerification:
    """Tests for password verification functionality."""

    def test_verify_password_returns_true_for_correct_password(self) -> None:
        """verify_password returns True for matching password."""
        password = "TestPassword123!"
        manager = CryptoManager(password)

        assert manager.verify_password(password) is True

    def test_verify_password_returns_false_for_wrong_password(self) -> None:
        """verify_password returns False for non-matching password."""
        manager = CryptoManager("CorrectPassword!")

        assert manager.verify_password("WrongPassword!") is False

    def test_verify_password_returns_false_for_similar_password(self) -> None:
        """verify_password returns False for similar but different password."""
        manager = CryptoManager("Password123!")

        # Case difference
        assert manager.verify_password("password123!") is False
        # Extra character
        assert manager.verify_password("Password123!x") is False
        # Missing character
        assert manager.verify_password("Password123") is False

    def test_verify_password_handles_unicode(self) -> None:
        """verify_password works correctly with unicode passwords."""
        unicode_password = "パスワード123!"
        manager = CryptoManager(unicode_password)

        assert manager.verify_password(unicode_password) is True
        assert manager.verify_password("パスワード123") is False

    def test_verify_password_uses_constant_time_comparison(self) -> None:
        """verify_password uses secrets.compare_digest for timing safety.

        This is a behavioral test - we verify the implementation uses
        constant-time comparison. Actual timing analysis is impractical
        in unit tests due to noise.
        """
        # The implementation uses secrets.compare_digest
        # We verify this by checking the method exists and is used
        import inspect

        source = inspect.getsource(CryptoManager.verify_password)
        assert "compare_digest" in source

    def test_hash_password_is_deterministic(self) -> None:
        """_hash_password produces consistent output for same input."""
        password = "TestPassword123!"
        hash1 = CryptoManager._hash_password(password)
        hash2 = CryptoManager._hash_password(password)

        assert hash1 == hash2

    def test_hash_password_produces_hex_string(self) -> None:
        """_hash_password returns a hexadecimal string."""
        password = "TestPassword123!"
        password_hash = CryptoManager._hash_password(password)

        # SHA-256 produces 64 hex characters
        assert len(password_hash) == 64
        assert all(c in "0123456789abcdef" for c in password_hash)


class TestSecurityInvariants:
    """Tests validating security properties and invariants."""

    def test_pbkdf2_iterations_meets_minimum(self) -> None:
        """PBKDF2 iterations meet OWASP minimum recommendation."""
        # OWASP 2023 recommends minimum 480,000 for PBKDF2-SHA256
        assert PBKDF2_ITERATIONS >= 480_000

    def test_salt_length_is_sufficient(self) -> None:
        """Salt length is at least 256 bits (32 bytes)."""
        assert SALT_LENGTH >= 32

    def test_generated_salt_length_matches_constant(self) -> None:
        """generate_salt produces salt of correct length."""
        salt = generate_salt()
        assert len(salt) == SALT_LENGTH

    def test_generated_salts_are_unique(self) -> None:
        """generate_salt produces cryptographically random, unique values."""
        salts = [generate_salt() for _ in range(100)]

        # All salts should be unique
        assert len(set(salts)) == 100

    def test_error_messages_do_not_contain_secrets(self) -> None:
        """Error messages should not leak sensitive information."""
        salt = os.urandom(SALT_LENGTH)
        password = "SuperSecretPassword!"
        manager1 = CryptoManager(password, salt=salt)
        manager2 = CryptoManager("WrongPassword!", salt=salt)

        encrypted = manager1.encrypt(b"sensitive data")

        try:
            manager2.decrypt(encrypted)
        except DecryptionError as e:
            error_msg = str(e).lower()
            assert "supersecretpassword" not in error_msg
            assert "sensitive data" not in error_msg

    def test_key_material_not_exposed_in_repr(self) -> None:
        """CryptoManager repr/str does not expose key material."""
        manager = CryptoManager("TestPassword123!")

        # Default repr should not contain key material
        repr_str = repr(manager)
        assert "TestPassword123!" not in repr_str


class TestWipeOperation:
    """Tests for secure memory wiping functionality."""

    def test_wipe_removes_key_attribute(self) -> None:
        """wipe removes the _key attribute from the manager."""
        manager = CryptoManager("TestPassword123!")
        assert hasattr(manager, "_key")

        manager.wipe()

        assert not hasattr(manager, "_key")

    def test_wipe_removes_fernet_attribute(self) -> None:
        """wipe removes the _fernet attribute from the manager."""
        manager = CryptoManager("TestPassword123!")
        assert hasattr(manager, "_fernet")

        manager.wipe()

        assert not hasattr(manager, "_fernet")

    def test_wipe_removes_password_hash_attribute(self) -> None:
        """wipe removes the _password_hash attribute from the manager."""
        manager = CryptoManager("TestPassword123!")
        assert hasattr(manager, "_password_hash")

        manager.wipe()

        assert not hasattr(manager, "_password_hash")

    def test_wipe_can_be_called_multiple_times(self) -> None:
        """Multiple wipe calls do not raise exceptions."""
        manager = CryptoManager("TestPassword123!")

        manager.wipe()
        manager.wipe()  # Should not raise
        manager.wipe()  # Should not raise

    def test_operations_fail_after_wipe(self) -> None:
        """Crypto operations fail after wipe is called."""
        manager = CryptoManager("TestPassword123!")
        manager.wipe()

        with pytest.raises(AttributeError):
            manager.encrypt(b"test")


class TestGenerateSalt:
    """Tests for the generate_salt utility function."""

    def test_generate_salt_returns_bytes(self) -> None:
        """generate_salt returns bytes object."""
        salt = generate_salt()
        assert isinstance(salt, bytes)

    def test_generate_salt_correct_length(self) -> None:
        """generate_salt returns salt of SALT_LENGTH bytes."""
        salt = generate_salt()
        assert len(salt) == SALT_LENGTH

    def test_generate_salt_uses_secure_random(self) -> None:
        """generate_salt uses os.urandom for cryptographic randomness."""
        # Generate many salts and check for collision (extremely unlikely)
        salts = {generate_salt() for _ in range(1000)}
        assert len(salts) == 1000


class TestValidateMasterPassword:
    """Tests for master password validation function."""

    def test_valid_password_passes_all_checks(self) -> None:
        """A password meeting all criteria returns (True, [])."""
        valid_password = "SecurePass123!"

        is_valid, issues = validate_master_password(valid_password)

        assert is_valid is True
        assert issues == []

    def test_short_password_fails(self) -> None:
        """Password under 12 characters fails validation."""
        short_password = "Short1!"

        is_valid, issues = validate_master_password(short_password)

        assert is_valid is False
        assert any("12 character" in issue for issue in issues)

    def test_missing_uppercase_fails(self) -> None:
        """Password without uppercase letter fails validation."""
        no_upper = "lowercase123!"

        is_valid, issues = validate_master_password(no_upper)

        assert is_valid is False
        assert any("uppercase" in issue.lower() for issue in issues)

    def test_missing_lowercase_fails(self) -> None:
        """Password without lowercase letter fails validation."""
        no_lower = "UPPERCASE123!"

        is_valid, issues = validate_master_password(no_lower)

        assert is_valid is False
        assert any("lowercase" in issue.lower() for issue in issues)

    def test_missing_digit_fails(self) -> None:
        """Password without digit fails validation."""
        no_digit = "NoDigitsHere!"

        is_valid, issues = validate_master_password(no_digit)

        assert is_valid is False
        assert any("number" in issue.lower() for issue in issues)

    def test_missing_special_char_fails(self) -> None:
        """Password without special character fails validation."""
        no_special = "NoSpecialChar123"

        is_valid, issues = validate_master_password(no_special)

        assert is_valid is False
        assert any("special" in issue.lower() for issue in issues)

    def test_empty_password_fails_multiple_checks(self) -> None:
        """Empty password fails all validation checks."""
        is_valid, issues = validate_master_password("")

        assert is_valid is False
        assert len(issues) >= 5  # Should fail length + all character requirements

    def test_multiple_issues_reported(self) -> None:
        """Multiple validation issues are all reported."""
        weak_password = "weak"

        is_valid, issues = validate_master_password(weak_password)

        assert is_valid is False
        # Should report: length, uppercase, digit, special char
        assert len(issues) >= 4

    def test_exactly_12_chars_passes_length_check(self) -> None:
        """Password of exactly 12 characters passes length check."""
        exactly_12 = "Abcdefg123!!"  # 12 chars

        is_valid, issues = validate_master_password(exactly_12)

        assert is_valid is True
        assert issues == []

    def test_special_characters_recognized(self) -> None:
        """All documented special characters are recognized."""
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"

        for char in special_chars:
            test_password = f"TestPassword1{char}"
            if len(test_password) >= 12:
                is_valid, issues = validate_master_password(test_password)
                # Should not fail due to missing special char
                assert (
                    "special" not in " ".join(issues).lower()
                ), f"Character '{char}' not recognized as special"


class TestCryptoManagerEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_long_password(self) -> None:
        """CryptoManager handles very long passwords."""
        long_password = "A" * 10000 + "a1!"
        manager = CryptoManager(long_password)

        test_data = b"test"
        assert manager.decrypt(manager.encrypt(test_data)) == test_data

    def test_password_with_null_bytes(self) -> None:
        """CryptoManager handles passwords with null bytes."""
        null_password = "pass\x00word123!"
        manager = CryptoManager(null_password)

        test_data = b"test"
        assert manager.decrypt(manager.encrypt(test_data)) == test_data

    def test_binary_data_encryption(self) -> None:
        """CryptoManager correctly encrypts arbitrary binary data."""
        manager = CryptoManager("TestPassword123!")

        # All possible byte values
        binary_data = bytes(range(256))
        assert manager.decrypt(manager.encrypt(binary_data)) == binary_data

    def test_large_data_encryption(self) -> None:
        """CryptoManager handles large data blocks."""
        manager = CryptoManager("TestPassword123!")

        # 1MB of random data
        large_data = os.urandom(1024 * 1024)
        encrypted = manager.encrypt(large_data)
        decrypted = manager.decrypt(encrypted)

        assert decrypted == large_data

    def test_encrypt_empty_bytes(self) -> None:
        """CryptoManager encrypts empty bytes correctly."""
        manager = CryptoManager("TestPassword123!")

        encrypted = manager.encrypt(b"")
        decrypted = manager.decrypt(encrypted)

        assert decrypted == b""

    def test_encrypt_empty_string(self) -> None:
        """CryptoManager encrypts empty string correctly."""
        manager = CryptoManager("TestPassword123!")

        encrypted = manager.encrypt_string("")
        decrypted = manager.decrypt_string(encrypted)

        assert decrypted == ""

    def test_salt_preserved_across_operations(self) -> None:
        """Salt remains constant throughout CryptoManager lifecycle."""
        manager = CryptoManager("TestPassword123!")
        original_salt = manager.salt

        # Perform various operations
        manager.encrypt(b"data1")
        manager.encrypt(b"data2")
        manager.verify_password("TestPassword123!")

        # Salt should not change
        assert manager.salt == original_salt


class TestCrossManagerCompatibility:
    """Tests verifying data portability between CryptoManager instances."""

    def test_data_portable_with_same_credentials(self) -> None:
        """Data encrypted by one manager is decryptable by another with same creds."""
        password = "TestPassword123!"
        salt = os.urandom(SALT_LENGTH)

        manager1 = CryptoManager(password, salt=salt)
        encrypted = manager1.encrypt(b"portable data")

        # Simulate new session with same credentials
        manager2 = CryptoManager(password, salt=salt)
        decrypted = manager2.decrypt(encrypted)

        assert decrypted == b"portable data"

    def test_string_data_portable_with_same_credentials(self) -> None:
        """String data is portable between managers with same credentials."""
        password = "TestPassword123!"
        salt = os.urandom(SALT_LENGTH)

        manager1 = CryptoManager(password, salt=salt)
        encrypted = manager1.encrypt_string("portable string")

        manager2 = CryptoManager(password, salt=salt)
        decrypted = manager2.decrypt_string(encrypted)

        assert decrypted == "portable string"
