"""Cryptographic operations for PassFX vault encryption.

Uses Fernet authenticated encryption (AES-128-CBC + HMAC-SHA256) with PBKDF2 key derivation.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# PBKDF2 iterations - high enough for security, low enough for UX
PBKDF2_ITERATIONS = 480_000  # OWASP 2023 recommendation
SALT_LENGTH = 32  # 256-bit salt


class CryptoError(Exception):
    """Base exception for cryptographic operations."""


class DecryptionError(CryptoError):
    """Raised when decryption fails (wrong password or corrupted data)."""


class CryptoManager:
    """Handles encryption and decryption of vault data.

    Uses Fernet symmetric encryption with PBKDF2 key derivation.
    Salt is stored with encrypted data for portability.
    """

    def __init__(self, master_password: str, salt: bytes | None = None) -> None:
        """Initialize the crypto manager.

        Args:
            master_password: The master password for encryption/decryption.
            salt: Optional salt for key derivation. Generated if not provided.
        """
        self._salt = salt or os.urandom(SALT_LENGTH)
        self._key = self._derive_key(master_password, self._salt)
        self._fernet = Fernet(self._key)
        # Keep password hash for verification (not the password itself)
        self._password_hash = self._hash_password(master_password)

    @property
    def salt(self) -> bytes:
        """Return the salt used for key derivation."""
        return self._salt

    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        """Derive a Fernet-compatible key from password and salt.

        Uses PBKDF2-HMAC-SHA256 for key derivation.

        Args:
            password: The master password.
            salt: Random salt for key derivation.

        Returns:
            Base64-encoded 32-byte key suitable for Fernet.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        key = kdf.derive(password.encode("utf-8"))
        return base64.urlsafe_b64encode(key)

    @staticmethod
    def _hash_password(password: str) -> str:
        """Create a hash of the password for verification.

        This is NOT for storage - only for runtime verification.

        Args:
            password: The password to hash.

        Returns:
            Hex-encoded SHA-256 hash.
        """
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Verify if the given password matches the stored hash.

        Args:
            password: Password to verify.

        Returns:
            True if password matches, False otherwise.
        """
        return secrets.compare_digest(
            self._password_hash, self._hash_password(password)
        )

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data using Fernet.

        Args:
            data: Plain bytes to encrypt.

        Returns:
            Encrypted bytes (includes IV and HMAC).
        """
        return self._fernet.encrypt(data)

    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt data using Fernet.

        Args:
            ciphertext: Encrypted bytes from encrypt().

        Returns:
            Original plain bytes.

        Raises:
            DecryptionError: If decryption fails (wrong key or corrupted data).
        """
        try:
            return self._fernet.decrypt(ciphertext)
        except InvalidToken as e:
            raise DecryptionError(
                "Decryption failed. Wrong password or corrupted data."
            ) from e

    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt a string and return base64-encoded result.

        Args:
            plaintext: String to encrypt.

        Returns:
            Base64-encoded encrypted string.
        """
        encrypted = self.encrypt(plaintext.encode("utf-8"))
        return base64.urlsafe_b64encode(encrypted).decode("ascii")

    def decrypt_string(self, ciphertext_b64: str) -> str:
        """Decrypt a base64-encoded string.

        Args:
            ciphertext_b64: Base64-encoded encrypted string.

        Returns:
            Original plaintext string.
        """
        ciphertext = base64.urlsafe_b64decode(ciphertext_b64.encode("ascii"))
        return self.decrypt(ciphertext).decode("utf-8")

    def wipe(self) -> None:
        """Securely wipe key material from memory.

        Note: Python's garbage collection makes true secure wiping difficult.
        This is a best-effort attempt.
        """
        # Overwrite key with random data
        if hasattr(self, "_key"):
            self._key = os.urandom(len(self._key))
            del self._key
        if hasattr(self, "_fernet"):
            del self._fernet
        if hasattr(self, "_password_hash"):
            self._password_hash = "0" * 64
            del self._password_hash


def generate_salt() -> bytes:
    """Generate a cryptographically secure random salt.

    Returns:
        Random salt bytes.
    """
    return os.urandom(SALT_LENGTH)


def validate_master_password(password: str) -> tuple[bool, list[str]]:
    """Validate master password strength.

    Args:
        password: Password to validate.

    Returns:
        Tuple of (is_valid, list_of_issues).
    """
    issues = []

    if len(password) < 12:
        issues.append("Password must be at least 12 characters")

    if not any(c.isupper() for c in password):
        issues.append("Include at least one uppercase letter")

    if not any(c.islower() for c in password):
        issues.append("Include at least one lowercase letter")

    if not any(c.isdigit() for c in password):
        issues.append("Include at least one number")

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        issues.append("Include at least one special character")

    return len(issues) == 0, issues
