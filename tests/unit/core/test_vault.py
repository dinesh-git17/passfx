# Unit tests for Vault operations.
# Validates encrypted storage, persistence, and security invariants.

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest import mock

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
from passfx.core.vault import (
    LOCK_TIMEOUT_SECONDS,
    SaltIntegrityError,
    Vault,
    VaultCorruptedError,
    VaultError,
    VaultLockError,
    VaultNotFoundError,
)

if TYPE_CHECKING:
    from collections.abc import Generator


# Fixtures


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    """Create a temporary vault directory with proper permissions."""
    vault_path = tmp_path / ".passfx"
    vault_path.mkdir(mode=0o700)
    return vault_path


@pytest.fixture
def vault_path(vault_dir: Path) -> Path:
    """Return the path to the vault file."""
    return vault_dir / "vault.enc"


@pytest.fixture
def salt_path(vault_dir: Path) -> Path:
    """Return the path to the salt file."""
    return vault_dir / "salt"


@pytest.fixture
def vault(vault_path: Path, salt_path: Path) -> Vault:
    """Create a Vault instance with temporary paths."""
    return Vault(vault_path=vault_path, salt_path=salt_path)


@pytest.fixture
def unlocked_vault(vault: Vault) -> Generator[Vault, None, None]:
    """Create and unlock a vault for testing."""
    password = "TestMasterPassword123!"
    vault.create(password)
    yield vault
    vault.lock()


@pytest.fixture
def sample_email() -> EmailCredential:
    """Create a sample email credential for testing."""
    return EmailCredential(
        label="GitHub",
        email="test@example.com",
        password="SecretPassword123!",
        notes="Test account",
    )


@pytest.fixture
def sample_phone() -> PhoneCredential:
    """Create a sample phone credential for testing."""
    return PhoneCredential(
        label="Bank PIN",
        phone="+1234567890",
        password="1234",
        notes="Bank account PIN",
    )


@pytest.fixture
def sample_card() -> CreditCard:
    """Create a sample credit card for testing."""
    return CreditCard(
        label="Chase Sapphire",
        card_number="4111111111111111",
        expiry="12/25",
        cvv="123",
        cardholder_name="John Doe",
        notes="Personal card",
    )


@pytest.fixture
def sample_env() -> EnvEntry:
    """Create a sample environment entry for testing."""
    return EnvEntry(
        title="Production ENV",
        filename=".env.production",
        content="API_KEY=secret123\nDB_HOST=localhost",
        notes="Production environment",
    )


@pytest.fixture
def sample_recovery() -> RecoveryEntry:
    """Create a sample recovery entry for testing."""
    return RecoveryEntry(
        title="GitHub 2FA",
        content="ABCD-1234\nEFGH-5678\nIJKL-9012",
        notes="Backup codes",
    )


@pytest.fixture
def sample_note() -> NoteEntry:
    """Create a sample secure note for testing."""
    return NoteEntry(
        title="Office WiFi",
        content="Password: SecretWiFi123",
        notes="Main office network",
    )


class TestVaultInitialization:
    """Tests for Vault initialization behavior."""

    def test_init_with_default_paths(self) -> None:
        """Vault uses default paths when none specified."""
        vault = Vault()
        assert vault.path.name == "vault.enc"
        assert ".passfx" in str(vault.path)

    def test_init_with_custom_paths(self, vault_path: Path, salt_path: Path) -> None:
        """Vault uses provided custom paths."""
        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        assert vault.path == vault_path
        assert vault._salt_path == salt_path

    def test_init_creates_lock_path(self, vault: Vault) -> None:
        """Vault creates correct lock file path."""
        expected_lock = vault.path.with_suffix(".enc.lock")
        assert vault._lock_path == expected_lock

    def test_init_empty_data_structure(self, vault: Vault) -> None:
        """Vault initializes with empty data structure."""
        expected_keys = {"emails", "phones", "cards", "envs", "recovery", "notes"}
        assert set(vault._data.keys()) == expected_keys
        for key in expected_keys:
            assert vault._data[key] == []

    def test_init_is_locked_by_default(self, vault: Vault) -> None:
        """New vault is locked by default."""
        assert vault.is_locked is True
        assert vault._crypto is None

    def test_init_does_not_exist_initially(self, vault: Vault) -> None:
        """Vault file does not exist before creation."""
        assert vault.exists is False


class TestVaultCreation:
    """Tests for vault creation behavior."""

    def test_create_new_vault(self, vault: Vault) -> None:
        """Creating a new vault generates salt and saves encrypted data."""
        password = "TestMasterPassword123!"
        vault.create(password)

        assert vault.exists is True
        assert vault.is_locked is False
        assert vault._crypto is not None
        assert vault.path.exists()
        assert vault._salt_path.exists()

    def test_create_vault_directory_created(self, tmp_path: Path) -> None:
        """Creating vault creates parent directory if missing."""
        nested_path = tmp_path / "deep" / "nested" / ".passfx" / "vault.enc"
        salt_path = nested_path.parent / "salt"
        vault = Vault(vault_path=nested_path, salt_path=salt_path)

        vault.create("TestPassword123!")

        assert nested_path.parent.exists()
        assert vault.exists

    def test_create_vault_sets_directory_permissions(self, vault: Vault) -> None:
        """Creating vault sets secure directory permissions."""
        vault.create("TestPassword123!")

        # Check directory permissions (0o700 on Unix)
        if sys.platform != "win32":
            dir_mode = stat.S_IMODE(vault.path.parent.stat().st_mode)
            assert dir_mode == 0o700

    def test_create_vault_sets_file_permissions(self, vault: Vault) -> None:
        """Creating vault sets secure file permissions on vault and salt."""
        vault.create("TestPassword123!")

        if sys.platform != "win32":
            vault_mode = stat.S_IMODE(vault.path.stat().st_mode)
            salt_mode = stat.S_IMODE(vault._salt_path.stat().st_mode)
            assert vault_mode == 0o600
            assert salt_mode == 0o600

    def test_create_existing_vault_raises_error(self, unlocked_vault: Vault) -> None:
        """Creating a vault when one exists raises VaultError."""
        with pytest.raises(VaultError, match="already exists"):
            unlocked_vault.create("NewPassword123!")

    def test_create_vault_generates_unique_salt(
        self, vault_path: Path, salt_path: Path
    ) -> None:
        """Each vault creation generates a unique salt."""
        salts = []
        for i in range(3):
            vault_p = vault_path.with_name(f"vault_{i}.enc")
            salt_p = salt_path.with_name(f"salt_{i}")
            v = Vault(vault_path=vault_p, salt_path=salt_p)
            v.create("TestPassword123!")
            salts.append(salt_p.read_bytes())
            v.lock()

        # All salts should be unique
        assert len(set(salts)) == 3

    def test_create_vault_encrypts_data(self, vault: Vault) -> None:
        """Vault file contains encrypted data, not plaintext."""
        vault.create("TestPassword123!")

        encrypted_data = vault.path.read_bytes()
        # Encrypted data should not contain plaintext JSON keys
        assert b'"emails"' not in encrypted_data
        assert b'"phones"' not in encrypted_data

    def test_create_vault_caches_salt_hash(self, vault: Vault) -> None:
        """Creating vault caches salt hash for integrity checking."""
        vault.create("TestPassword123!")
        assert vault._cached_salt_hash is not None
        assert len(vault._cached_salt_hash) == 64  # SHA-256 hex


class TestVaultUnlock:
    """Tests for vault unlocking behavior."""

    def test_unlock_with_correct_password(self, vault: Vault) -> None:
        """Unlocking with correct password succeeds."""
        password = "TestMasterPassword123!"
        vault.create(password)
        vault.lock()

        vault.unlock(password)

        assert vault.is_locked is False
        assert vault._crypto is not None

    def test_unlock_with_wrong_password_raises_error(self, vault: Vault) -> None:
        """Unlocking with wrong password raises DecryptionError."""
        vault.create("CorrectPassword123!")
        vault.lock()

        with pytest.raises(DecryptionError):
            vault.unlock("WrongPassword123!")

        assert vault.is_locked is True

    def test_unlock_nonexistent_vault_raises_error(self, vault: Vault) -> None:
        """Unlocking a vault that doesn't exist raises VaultNotFoundError."""
        with pytest.raises(VaultNotFoundError, match="No vault found"):
            vault.unlock("AnyPassword123!")

    def test_unlock_missing_salt_raises_error(self, vault: Vault) -> None:
        """Unlocking with missing salt file raises VaultCorruptedError."""
        vault.create("TestPassword123!")
        vault.lock()
        vault._salt_path.unlink()

        with pytest.raises(VaultCorruptedError, match="Salt file missing"):
            vault.unlock("TestPassword123!")

    def test_unlock_corrupted_vault_raises_error(self, vault: Vault) -> None:
        """Unlocking a corrupted vault file raises DecryptionError."""
        vault.create("TestPassword123!")
        vault.lock()

        # Corrupt the vault file
        vault.path.write_bytes(os.urandom(100))

        with pytest.raises(DecryptionError):
            vault.unlock("TestPassword123!")

    def test_unlock_invalid_json_raises_error(self, vault: Vault) -> None:
        """Unlocking a vault with invalid JSON raises VaultCorruptedError."""
        password = "TestPassword123!"
        vault.create(password)
        salt = vault._salt_path.read_bytes()
        vault.lock()

        # Encrypt invalid JSON
        crypto = CryptoManager(password, salt=salt)
        vault.path.write_bytes(crypto.encrypt(b"not valid json"))

        with pytest.raises(VaultCorruptedError, match="corrupted"):
            vault.unlock(password)

    def test_unlock_salt_symlink_raises_error(
        self, vault: Vault, tmp_path: Path
    ) -> None:
        """Unlocking with salt as symlink raises SaltIntegrityError."""
        vault.create("TestPassword123!")
        vault.lock()

        # Replace salt with symlink
        fake_salt = tmp_path / "fake_salt"
        fake_salt.write_bytes(os.urandom(32))
        vault._salt_path.unlink()
        vault._salt_path.symlink_to(fake_salt)

        with pytest.raises(SaltIntegrityError, match="symlink"):
            vault.unlock("TestPassword123!")

    def test_unlock_preserves_data(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Data persists across lock/unlock cycles."""
        unlocked_vault.add_email(sample_email)
        password = "TestMasterPassword123!"

        unlocked_vault.lock()
        unlocked_vault.unlock(password)

        emails = unlocked_vault.get_emails()
        assert len(emails) == 1
        assert emails[0].email == sample_email.email

    def test_unlock_migrates_missing_keys(self, vault: Vault) -> None:
        """Unlock migrates vaults missing newer keys like 'envs'."""
        password = "TestPassword123!"
        vault.create(password)
        salt = vault._salt_path.read_bytes()
        vault.lock()

        # Create vault data without 'envs', 'recovery', 'notes' keys
        old_data: dict[str, list[Any]] = {"emails": [], "phones": [], "cards": []}
        crypto = CryptoManager(password, salt=salt)
        vault.path.write_bytes(crypto.encrypt(json.dumps(old_data).encode("utf-8")))

        vault.unlock(password)

        # Should have migrated keys
        assert "envs" in vault._data
        assert "recovery" in vault._data
        assert "notes" in vault._data


class TestVaultLock:
    """Tests for vault locking behavior."""

    def test_lock_clears_crypto(self, unlocked_vault: Vault) -> None:
        """Locking vault clears crypto manager."""
        assert unlocked_vault._crypto is not None
        unlocked_vault.lock()
        assert unlocked_vault._crypto is None
        assert unlocked_vault.is_locked is True

    def test_lock_clears_data(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Locking vault clears in-memory data."""
        unlocked_vault.add_email(sample_email)
        unlocked_vault.lock()

        # Data should be empty
        for key in unlocked_vault._data:
            assert unlocked_vault._data[key] == []

    def test_lock_clears_salt_hash(self, unlocked_vault: Vault) -> None:
        """Locking vault clears cached salt hash."""
        assert unlocked_vault._cached_salt_hash is not None
        unlocked_vault.lock()
        assert unlocked_vault._cached_salt_hash is None

    def test_lock_calls_crypto_wipe(self, unlocked_vault: Vault) -> None:
        """Locking vault calls crypto.wipe() for memory cleanup."""
        crypto = unlocked_vault._crypto
        with mock.patch.object(crypto, "wipe") as mock_wipe:
            unlocked_vault.lock()
            mock_wipe.assert_called_once()

    def test_double_lock_is_safe(self, unlocked_vault: Vault) -> None:
        """Calling lock multiple times does not raise errors."""
        unlocked_vault.lock()
        unlocked_vault.lock()  # Should not raise
        assert unlocked_vault.is_locked is True


class TestEmailCRUD:
    """Tests for email credential CRUD operations."""

    def test_add_email(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Adding an email credential persists it."""
        unlocked_vault.add_email(sample_email)

        emails = unlocked_vault.get_emails()
        assert len(emails) == 1
        assert emails[0].label == sample_email.label
        assert emails[0].email == sample_email.email

    def test_get_emails_empty(self, unlocked_vault: Vault) -> None:
        """Getting emails from empty vault returns empty list."""
        assert unlocked_vault.get_emails() == []

    def test_get_email_by_id(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Getting email by ID returns correct credential."""
        unlocked_vault.add_email(sample_email)
        result = unlocked_vault.get_email_by_id(sample_email.id)

        assert result is not None
        assert result.id == sample_email.id

    def test_get_email_by_id_not_found(self, unlocked_vault: Vault) -> None:
        """Getting email by nonexistent ID returns None."""
        result = unlocked_vault.get_email_by_id("nonexistent")
        assert result is None

    def test_update_email(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Updating an email credential changes its fields."""
        unlocked_vault.add_email(sample_email)
        new_email = "updated@example.com"

        result = unlocked_vault.update_email(sample_email.id, email=new_email)

        assert result is True
        updated = unlocked_vault.get_email_by_id(sample_email.id)
        assert updated is not None
        assert updated.email == new_email

    def test_update_email_not_found(self, unlocked_vault: Vault) -> None:
        """Updating nonexistent email returns False."""
        result = unlocked_vault.update_email("nonexistent", email="new@test.com")
        assert result is False

    def test_delete_email(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Deleting an email credential removes it."""
        unlocked_vault.add_email(sample_email)
        result = unlocked_vault.delete_email(sample_email.id)

        assert result is True
        assert unlocked_vault.get_email_by_id(sample_email.id) is None
        assert len(unlocked_vault.get_emails()) == 0

    def test_delete_email_not_found(self, unlocked_vault: Vault) -> None:
        """Deleting nonexistent email returns False."""
        result = unlocked_vault.delete_email("nonexistent")
        assert result is False


class TestPhoneCRUD:
    """Tests for phone credential CRUD operations."""

    def test_add_phone(
        self, unlocked_vault: Vault, sample_phone: PhoneCredential
    ) -> None:
        """Adding a phone credential persists it."""
        unlocked_vault.add_phone(sample_phone)

        phones = unlocked_vault.get_phones()
        assert len(phones) == 1
        assert phones[0].phone == sample_phone.phone

    def test_get_phone_by_id(
        self, unlocked_vault: Vault, sample_phone: PhoneCredential
    ) -> None:
        """Getting phone by ID returns correct credential."""
        unlocked_vault.add_phone(sample_phone)
        result = unlocked_vault.get_phone_by_id(sample_phone.id)

        assert result is not None
        assert result.id == sample_phone.id

    def test_get_phone_by_id_not_found(self, unlocked_vault: Vault) -> None:
        """Getting phone by nonexistent ID returns None."""
        assert unlocked_vault.get_phone_by_id("nonexistent") is None

    def test_update_phone(
        self, unlocked_vault: Vault, sample_phone: PhoneCredential
    ) -> None:
        """Updating a phone credential changes its fields."""
        unlocked_vault.add_phone(sample_phone)
        result = unlocked_vault.update_phone(sample_phone.id, phone="+9876543210")

        assert result is True
        updated = unlocked_vault.get_phone_by_id(sample_phone.id)
        assert updated is not None
        assert updated.phone == "+9876543210"

    def test_update_phone_not_found(self, unlocked_vault: Vault) -> None:
        """Updating nonexistent phone returns False."""
        assert unlocked_vault.update_phone("nonexistent", phone="123") is False

    def test_delete_phone(
        self, unlocked_vault: Vault, sample_phone: PhoneCredential
    ) -> None:
        """Deleting a phone credential removes it."""
        unlocked_vault.add_phone(sample_phone)
        result = unlocked_vault.delete_phone(sample_phone.id)

        assert result is True
        assert len(unlocked_vault.get_phones()) == 0

    def test_delete_phone_not_found(self, unlocked_vault: Vault) -> None:
        """Deleting nonexistent phone returns False."""
        assert unlocked_vault.delete_phone("nonexistent") is False


class TestCardCRUD:
    """Tests for credit card CRUD operations."""

    def test_add_card(self, unlocked_vault: Vault, sample_card: CreditCard) -> None:
        """Adding a credit card persists it."""
        unlocked_vault.add_card(sample_card)

        cards = unlocked_vault.get_cards()
        assert len(cards) == 1
        assert cards[0].cardholder_name == sample_card.cardholder_name

    def test_get_card_by_id(
        self, unlocked_vault: Vault, sample_card: CreditCard
    ) -> None:
        """Getting card by ID returns correct card."""
        unlocked_vault.add_card(sample_card)
        result = unlocked_vault.get_card_by_id(sample_card.id)

        assert result is not None
        assert result.id == sample_card.id

    def test_get_card_by_id_not_found(self, unlocked_vault: Vault) -> None:
        """Getting card by nonexistent ID returns None."""
        assert unlocked_vault.get_card_by_id("nonexistent") is None

    def test_update_card(self, unlocked_vault: Vault, sample_card: CreditCard) -> None:
        """Updating a credit card changes its fields."""
        unlocked_vault.add_card(sample_card)
        result = unlocked_vault.update_card(sample_card.id, expiry="06/30")

        assert result is True
        updated = unlocked_vault.get_card_by_id(sample_card.id)
        assert updated is not None
        assert updated.expiry == "06/30"

    def test_update_card_not_found(self, unlocked_vault: Vault) -> None:
        """Updating nonexistent card returns False."""
        assert unlocked_vault.update_card("nonexistent", expiry="12/99") is False

    def test_delete_card(self, unlocked_vault: Vault, sample_card: CreditCard) -> None:
        """Deleting a credit card removes it."""
        unlocked_vault.add_card(sample_card)
        result = unlocked_vault.delete_card(sample_card.id)

        assert result is True
        assert len(unlocked_vault.get_cards()) == 0

    def test_delete_card_not_found(self, unlocked_vault: Vault) -> None:
        """Deleting nonexistent card returns False."""
        assert unlocked_vault.delete_card("nonexistent") is False


class TestEnvCRUD:
    """Tests for environment entry CRUD operations."""

    def test_add_env(self, unlocked_vault: Vault, sample_env: EnvEntry) -> None:
        """Adding an env entry persists it."""
        unlocked_vault.add_env(sample_env)

        envs = unlocked_vault.get_envs()
        assert len(envs) == 1
        assert envs[0].title == sample_env.title

    def test_get_env_by_id(self, unlocked_vault: Vault, sample_env: EnvEntry) -> None:
        """Getting env by ID returns correct entry."""
        unlocked_vault.add_env(sample_env)
        result = unlocked_vault.get_env_by_id(sample_env.id)

        assert result is not None
        assert result.id == sample_env.id

    def test_get_env_by_id_not_found(self, unlocked_vault: Vault) -> None:
        """Getting env by nonexistent ID returns None."""
        assert unlocked_vault.get_env_by_id("nonexistent") is None

    def test_update_env(self, unlocked_vault: Vault, sample_env: EnvEntry) -> None:
        """Updating an env entry changes its fields."""
        unlocked_vault.add_env(sample_env)
        result = unlocked_vault.update_env(sample_env.id, title="Staging ENV")

        assert result is True
        updated = unlocked_vault.get_env_by_id(sample_env.id)
        assert updated is not None
        assert updated.title == "Staging ENV"

    def test_update_env_not_found(self, unlocked_vault: Vault) -> None:
        """Updating nonexistent env returns False."""
        assert unlocked_vault.update_env("nonexistent", title="New") is False

    def test_delete_env(self, unlocked_vault: Vault, sample_env: EnvEntry) -> None:
        """Deleting an env entry removes it."""
        unlocked_vault.add_env(sample_env)
        result = unlocked_vault.delete_env(sample_env.id)

        assert result is True
        assert len(unlocked_vault.get_envs()) == 0

    def test_delete_env_not_found(self, unlocked_vault: Vault) -> None:
        """Deleting nonexistent env returns False."""
        assert unlocked_vault.delete_env("nonexistent") is False

    def test_add_env_initializes_missing_key(
        self, vault_path: Path, salt_path: Path
    ) -> None:
        """Adding env initializes 'envs' key if missing."""
        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create("TestPassword123!")
        # Simulate old vault without 'envs' key
        del vault._data["envs"]

        env = EnvEntry(title="Test", filename=".env", content="KEY=value")
        vault.add_env(env)

        assert "envs" in vault._data
        assert len(vault._data["envs"]) == 1


class TestRecoveryCRUD:
    """Tests for recovery entry CRUD operations."""

    def test_add_recovery(
        self, unlocked_vault: Vault, sample_recovery: RecoveryEntry
    ) -> None:
        """Adding a recovery entry persists it."""
        unlocked_vault.add_recovery(sample_recovery)

        entries = unlocked_vault.get_recovery_entries()
        assert len(entries) == 1
        assert entries[0].title == sample_recovery.title

    def test_get_recovery_by_id(
        self, unlocked_vault: Vault, sample_recovery: RecoveryEntry
    ) -> None:
        """Getting recovery by ID returns correct entry."""
        unlocked_vault.add_recovery(sample_recovery)
        result = unlocked_vault.get_recovery_by_id(sample_recovery.id)

        assert result is not None
        assert result.id == sample_recovery.id

    def test_get_recovery_by_id_not_found(self, unlocked_vault: Vault) -> None:
        """Getting recovery by nonexistent ID returns None."""
        assert unlocked_vault.get_recovery_by_id("nonexistent") is None

    def test_update_recovery(
        self, unlocked_vault: Vault, sample_recovery: RecoveryEntry
    ) -> None:
        """Updating a recovery entry changes its fields."""
        unlocked_vault.add_recovery(sample_recovery)
        result = unlocked_vault.update_recovery(sample_recovery.id, title="Backup 2FA")

        assert result is True
        updated = unlocked_vault.get_recovery_by_id(sample_recovery.id)
        assert updated is not None
        assert updated.title == "Backup 2FA"

    def test_update_recovery_not_found(self, unlocked_vault: Vault) -> None:
        """Updating nonexistent recovery returns False."""
        assert unlocked_vault.update_recovery("nonexistent", title="X") is False

    def test_delete_recovery(
        self, unlocked_vault: Vault, sample_recovery: RecoveryEntry
    ) -> None:
        """Deleting a recovery entry removes it."""
        unlocked_vault.add_recovery(sample_recovery)
        result = unlocked_vault.delete_recovery(sample_recovery.id)

        assert result is True
        assert len(unlocked_vault.get_recovery_entries()) == 0

    def test_delete_recovery_not_found(self, unlocked_vault: Vault) -> None:
        """Deleting nonexistent recovery returns False."""
        assert unlocked_vault.delete_recovery("nonexistent") is False


class TestNoteCRUD:
    """Tests for secure note CRUD operations."""

    def test_add_note(self, unlocked_vault: Vault, sample_note: NoteEntry) -> None:
        """Adding a note persists it."""
        unlocked_vault.add_note(sample_note)

        notes = unlocked_vault.get_notes()
        assert len(notes) == 1
        assert notes[0].title == sample_note.title

    def test_get_note_by_id(
        self, unlocked_vault: Vault, sample_note: NoteEntry
    ) -> None:
        """Getting note by ID returns correct entry."""
        unlocked_vault.add_note(sample_note)
        result = unlocked_vault.get_note_by_id(sample_note.id)

        assert result is not None
        assert result.id == sample_note.id

    def test_get_note_by_id_not_found(self, unlocked_vault: Vault) -> None:
        """Getting note by nonexistent ID returns None."""
        assert unlocked_vault.get_note_by_id("nonexistent") is None

    def test_update_note(self, unlocked_vault: Vault, sample_note: NoteEntry) -> None:
        """Updating a note changes its fields."""
        unlocked_vault.add_note(sample_note)
        result = unlocked_vault.update_note(sample_note.id, title="Updated Note")

        assert result is True
        updated = unlocked_vault.get_note_by_id(sample_note.id)
        assert updated is not None
        assert updated.title == "Updated Note"

    def test_update_note_not_found(self, unlocked_vault: Vault) -> None:
        """Updating nonexistent note returns False."""
        assert unlocked_vault.update_note("nonexistent", title="X") is False

    def test_delete_note(self, unlocked_vault: Vault, sample_note: NoteEntry) -> None:
        """Deleting a note removes it."""
        unlocked_vault.add_note(sample_note)
        result = unlocked_vault.delete_note(sample_note.id)

        assert result is True
        assert len(unlocked_vault.get_notes()) == 0

    def test_delete_note_not_found(self, unlocked_vault: Vault) -> None:
        """Deleting nonexistent note returns False."""
        assert unlocked_vault.delete_note("nonexistent") is False


class TestPersistence:
    """Tests for vault persistence and round-trip data integrity."""

    def test_save_load_roundtrip_preserves_emails(
        self, vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Email credentials survive save/load cycle."""
        password = "TestMasterPassword123!"
        vault.create(password)
        vault.add_email(sample_email)
        vault.lock()

        vault.unlock(password)
        emails = vault.get_emails()

        assert len(emails) == 1
        assert emails[0].label == sample_email.label
        assert emails[0].email == sample_email.email
        assert emails[0].password == sample_email.password

    def test_save_load_roundtrip_preserves_all_types(
        self,
        vault: Vault,
        sample_email: EmailCredential,
        sample_phone: PhoneCredential,
        sample_card: CreditCard,
        sample_env: EnvEntry,
        sample_recovery: RecoveryEntry,
        sample_note: NoteEntry,
    ) -> None:
        """All credential types survive save/load cycle."""
        password = "TestMasterPassword123!"
        vault.create(password)

        vault.add_email(sample_email)
        vault.add_phone(sample_phone)
        vault.add_card(sample_card)
        vault.add_env(sample_env)
        vault.add_recovery(sample_recovery)
        vault.add_note(sample_note)
        vault.lock()

        vault.unlock(password)

        assert len(vault.get_emails()) == 1
        assert len(vault.get_phones()) == 1
        assert len(vault.get_cards()) == 1
        assert len(vault.get_envs()) == 1
        assert len(vault.get_recovery_entries()) == 1
        assert len(vault.get_notes()) == 1

    def test_multiple_saves_do_not_corrupt(self, unlocked_vault: Vault) -> None:
        """Multiple sequential saves maintain data integrity."""
        for i in range(5):
            email = EmailCredential(
                label=f"Test {i}",
                email=f"test{i}@example.com",
                password="pass123!",
            )
            unlocked_vault.add_email(email)

        emails = unlocked_vault.get_emails()
        assert len(emails) == 5
        labels = {e.label for e in emails}
        assert labels == {"Test 0", "Test 1", "Test 2", "Test 3", "Test 4"}

    def test_save_locked_vault_raises_error(self, vault: Vault) -> None:
        """Saving a locked vault raises VaultError."""
        with pytest.raises(VaultError, match="locked"):
            vault._save()

    def test_save_creates_backup(self, unlocked_vault: Vault) -> None:
        """Saving an existing vault creates a backup file."""
        # First save happens during create, second save needs to create backup
        unlocked_vault.add_email(
            EmailCredential(label="Test", email="t@t.com", password="p")
        )

        backup_path = unlocked_vault.path.with_suffix(".enc.bak")
        assert backup_path.exists()

    def test_backup_has_correct_permissions(self, unlocked_vault: Vault) -> None:
        """Backup file has secure permissions (0600)."""
        unlocked_vault.add_email(
            EmailCredential(label="Test", email="t@t.com", password="p")
        )

        backup_path = unlocked_vault.path.with_suffix(".enc.bak")
        if sys.platform != "win32":
            mode = stat.S_IMODE(backup_path.stat().st_mode)
            assert mode == 0o600


class TestSaltIntegrity:
    """Tests for salt file integrity checking."""

    def test_save_with_modified_salt_raises_error(self, unlocked_vault: Vault) -> None:
        """Saving after salt modification raises SaltIntegrityError."""
        # Modify salt after vault is unlocked
        original_salt = unlocked_vault._salt_path.read_bytes()
        new_salt = os.urandom(32)
        unlocked_vault._salt_path.write_bytes(new_salt)

        with pytest.raises(SaltIntegrityError, match="modified"):
            unlocked_vault.add_email(
                EmailCredential(label="Test", email="t@t.com", password="p")
            )

        # Restore salt for cleanup
        unlocked_vault._salt_path.write_bytes(original_salt)

    def test_save_with_deleted_salt_raises_error(self, unlocked_vault: Vault) -> None:
        """Saving after salt deletion raises SaltIntegrityError."""
        unlocked_vault._salt_path.unlink()

        with pytest.raises(SaltIntegrityError, match="deleted"):
            unlocked_vault.add_email(
                EmailCredential(label="Test", email="t@t.com", password="p")
            )

    def test_save_with_symlinked_salt_raises_error(
        self, unlocked_vault: Vault, tmp_path: Path
    ) -> None:
        """Saving with salt as symlink raises SaltIntegrityError."""
        # Replace salt with symlink
        fake_salt = tmp_path / "fake_salt"
        fake_salt.write_bytes(unlocked_vault._salt_path.read_bytes())
        unlocked_vault._salt_path.unlink()
        unlocked_vault._salt_path.symlink_to(fake_salt)

        with pytest.raises(SaltIntegrityError, match="symlink"):
            unlocked_vault.add_email(
                EmailCredential(label="Test", email="t@t.com", password="p")
            )

    def test_hash_salt_produces_consistent_hash(self) -> None:
        """_hash_salt produces consistent SHA-256 hashes."""
        salt = b"test_salt_bytes"
        hash1 = Vault._hash_salt(salt)
        hash2 = Vault._hash_salt(salt)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex


class TestSearch:
    """Tests for vault search functionality."""

    def test_search_by_label(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Search finds credentials by label."""
        unlocked_vault.add_email(sample_email)
        results = unlocked_vault.search("GitHub")

        assert len(results) == 1
        # Cast to EmailCredential since we know we only added an email
        result = results[0]
        assert isinstance(result, EmailCredential)
        assert result.label == "GitHub"

    def test_search_by_email(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Search finds credentials by email address."""
        unlocked_vault.add_email(sample_email)
        results = unlocked_vault.search("test@example")

        assert len(results) == 1

    def test_search_by_phone(
        self, unlocked_vault: Vault, sample_phone: PhoneCredential
    ) -> None:
        """Search finds credentials by phone number."""
        unlocked_vault.add_phone(sample_phone)
        results = unlocked_vault.search("123456")

        assert len(results) == 1

    def test_search_by_cardholder(
        self, unlocked_vault: Vault, sample_card: CreditCard
    ) -> None:
        """Search finds cards by cardholder name."""
        unlocked_vault.add_card(sample_card)
        results = unlocked_vault.search("John Doe")

        assert len(results) == 1

    def test_search_by_env_title(
        self, unlocked_vault: Vault, sample_env: EnvEntry
    ) -> None:
        """Search finds env entries by title."""
        unlocked_vault.add_env(sample_env)
        results = unlocked_vault.search("Production")

        assert len(results) == 1

    def test_search_by_env_content(
        self, unlocked_vault: Vault, sample_env: EnvEntry
    ) -> None:
        """Search finds env entries by content."""
        unlocked_vault.add_env(sample_env)
        results = unlocked_vault.search("API_KEY")

        assert len(results) == 1

    def test_search_by_recovery_title(
        self, unlocked_vault: Vault, sample_recovery: RecoveryEntry
    ) -> None:
        """Search finds recovery entries by title."""
        unlocked_vault.add_recovery(sample_recovery)
        results = unlocked_vault.search("2FA")

        assert len(results) == 1

    def test_search_by_note_content(
        self, unlocked_vault: Vault, sample_note: NoteEntry
    ) -> None:
        """Search finds notes by content."""
        unlocked_vault.add_note(sample_note)
        results = unlocked_vault.search("WiFi")

        assert len(results) == 1

    def test_search_case_insensitive(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Search is case-insensitive."""
        unlocked_vault.add_email(sample_email)
        results = unlocked_vault.search("GITHUB")

        assert len(results) == 1

    def test_search_no_results(self, unlocked_vault: Vault) -> None:
        """Search with no matches returns empty list."""
        results = unlocked_vault.search("nonexistent")
        assert results == []

    def test_search_multiple_types(
        self,
        unlocked_vault: Vault,
        sample_email: EmailCredential,
        sample_note: NoteEntry,
    ) -> None:
        """Search returns results from multiple credential types."""
        # Both contain "Test"
        email = EmailCredential(
            label="Test Service", email="test@test.com", password="p"
        )
        note = NoteEntry(title="Test Note", content="test content")

        unlocked_vault.add_email(email)
        unlocked_vault.add_note(note)

        results = unlocked_vault.search("Test")
        assert len(results) == 2


class TestStats:
    """Tests for vault statistics."""

    def test_get_stats_empty_vault(self, unlocked_vault: Vault) -> None:
        """Stats for empty vault shows zeros."""
        stats = unlocked_vault.get_stats()

        assert stats["emails"] == 0
        assert stats["phones"] == 0
        assert stats["cards"] == 0
        assert stats["envs"] == 0
        assert stats["recovery"] == 0
        assert stats["notes"] == 0
        assert stats["total"] == 0

    def test_get_stats_with_data(
        self,
        unlocked_vault: Vault,
        sample_email: EmailCredential,
        sample_phone: PhoneCredential,
        sample_card: CreditCard,
    ) -> None:
        """Stats reflect actual credential counts."""
        unlocked_vault.add_email(sample_email)
        unlocked_vault.add_phone(sample_phone)
        unlocked_vault.add_card(sample_card)

        stats = unlocked_vault.get_stats()

        assert stats["emails"] == 1
        assert stats["phones"] == 1
        assert stats["cards"] == 1
        assert stats["total"] == 3


class TestImportExport:
    """Tests for vault import/export functionality."""

    def test_get_all_data_returns_dict_structure(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """get_all_data returns dict with all credential categories."""
        unlocked_vault.add_email(sample_email)
        data = unlocked_vault.get_all_data()

        # Verify structure contains all expected keys
        expected_keys = {"emails", "phones", "cards", "envs", "recovery", "notes"}
        assert set(data.keys()) == expected_keys
        assert len(data["emails"]) == 1
        assert data["emails"][0]["email"] == sample_email.email

    def test_import_data_merge_mode(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Import with merge=True adds to existing data."""
        unlocked_vault.add_email(sample_email)

        new_email = {
            "id": "new123",
            "label": "New",
            "email": "new@test.com",
            "password": "pass",
        }
        import_data = {"emails": [new_email]}

        counts = unlocked_vault.import_data(import_data, merge=True)

        assert counts["emails"] == 1
        assert len(unlocked_vault.get_emails()) == 2

    def test_import_data_replace_mode(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Import with merge=False replaces existing data."""
        unlocked_vault.add_email(sample_email)

        new_email = {
            "id": "new123",
            "label": "New",
            "email": "new@test.com",
            "password": "pass",
        }
        import_data = {"emails": [new_email]}

        counts = unlocked_vault.import_data(import_data, merge=False)

        assert counts["emails"] == 1
        emails = unlocked_vault.get_emails()
        assert len(emails) == 1
        assert emails[0].label == "New"

    def test_import_skips_duplicate_ids(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Import skips entries with existing IDs."""
        unlocked_vault.add_email(sample_email)

        # Try to import same email again
        import_data = {"emails": [sample_email.to_dict()]}
        counts = unlocked_vault.import_data(import_data, merge=True)

        assert counts["emails"] == 0
        assert len(unlocked_vault.get_emails()) == 1

    def test_import_all_credential_types(self, unlocked_vault: Vault) -> None:
        """Import works for all credential types."""
        import_data = {
            "emails": [{"id": "e1", "label": "E", "email": "e@e.com", "password": "p"}],
            "phones": [{"id": "p1", "label": "P", "phone": "123", "password": "1234"}],
            "cards": [
                {
                    "id": "c1",
                    "label": "C",
                    "card_number": "4111",
                    "expiry": "12/25",
                    "cvv": "123",
                    "cardholder_name": "X",
                }
            ],
            "envs": [{"id": "v1", "title": "V", "filename": ".env", "content": "X=Y"}],
            "recovery": [{"id": "r1", "title": "R", "content": "codes"}],
            "notes": [{"id": "n1", "title": "N", "content": "note"}],
        }

        counts = unlocked_vault.import_data(import_data, merge=True)

        assert counts["emails"] == 1
        assert counts["phones"] == 1
        assert counts["cards"] == 1
        assert counts["envs"] == 1
        assert counts["recovery"] == 1
        assert counts["notes"] == 1


class TestTimeout:
    """Tests for vault auto-lock timeout functionality."""

    def test_check_timeout_returns_false_when_active(
        self, unlocked_vault: Vault
    ) -> None:
        """check_timeout returns False when recently active."""
        unlocked_vault._update_activity()
        unlocked_vault._lock_timeout = 300

        assert unlocked_vault.check_timeout() is False

    def test_check_timeout_returns_true_when_expired(
        self, unlocked_vault: Vault
    ) -> None:
        """check_timeout returns True when timeout exceeded."""
        unlocked_vault._last_activity = time.time() - 400
        unlocked_vault._lock_timeout = 300

        assert unlocked_vault.check_timeout() is True

    def test_check_timeout_disabled_when_zero(self, unlocked_vault: Vault) -> None:
        """check_timeout returns False when timeout is 0 (disabled)."""
        unlocked_vault._last_activity = time.time() - 10000
        unlocked_vault.set_lock_timeout(0)

        assert unlocked_vault.check_timeout() is False

    def test_set_lock_timeout(self, unlocked_vault: Vault) -> None:
        """set_lock_timeout updates the timeout value."""
        unlocked_vault.set_lock_timeout(600)
        assert unlocked_vault._lock_timeout == 600

    def test_reset_activity_updates_timestamp(self, unlocked_vault: Vault) -> None:
        """reset_activity updates the last activity timestamp."""
        unlocked_vault._last_activity = time.time() - 1000
        old_activity = unlocked_vault._last_activity

        unlocked_vault.reset_activity()

        assert unlocked_vault._last_activity > old_activity
        assert unlocked_vault._last_activity >= time.time() - 1

    def test_reset_activity_prevents_timeout(self, unlocked_vault: Vault) -> None:
        """reset_activity prevents check_timeout from returning True."""
        unlocked_vault._lock_timeout = 300
        unlocked_vault._last_activity = time.time() - 400

        assert unlocked_vault.check_timeout() is True

        unlocked_vault.reset_activity()

        assert unlocked_vault.check_timeout() is False

    def test_get_remaining_lock_time_returns_none_when_locked(
        self, vault: Vault
    ) -> None:
        """get_remaining_lock_time returns None when vault is locked."""
        assert vault.get_remaining_lock_time() is None

    def test_get_remaining_lock_time_returns_none_when_disabled(
        self, unlocked_vault: Vault
    ) -> None:
        """get_remaining_lock_time returns None when auto-lock is disabled."""
        unlocked_vault.set_lock_timeout(0)
        assert unlocked_vault.get_remaining_lock_time() is None

    def test_get_remaining_lock_time_returns_remaining_seconds(
        self, unlocked_vault: Vault
    ) -> None:
        """get_remaining_lock_time returns correct remaining seconds."""
        unlocked_vault._lock_timeout = 300
        unlocked_vault._last_activity = time.time()

        remaining = unlocked_vault.get_remaining_lock_time()

        assert remaining is not None
        assert 298 <= remaining <= 300

    def test_get_remaining_lock_time_returns_none_when_exceeded(
        self, unlocked_vault: Vault
    ) -> None:
        """get_remaining_lock_time returns None when timeout exceeded."""
        unlocked_vault._lock_timeout = 300
        unlocked_vault._last_activity = time.time() - 400

        assert unlocked_vault.get_remaining_lock_time() is None

    def test_get_remaining_lock_time_returns_integer(
        self, unlocked_vault: Vault
    ) -> None:
        """get_remaining_lock_time returns integer, not float."""
        unlocked_vault._lock_timeout = 300
        unlocked_vault._last_activity = time.time()

        remaining = unlocked_vault.get_remaining_lock_time()

        assert isinstance(remaining, int)


class TestFileLocking:
    """Tests for vault file locking behavior."""

    def test_acquire_release_lock(self, vault: Vault) -> None:
        """Lock can be acquired and released."""
        vault._ensure_vault_dir()
        vault._acquire_lock()

        assert vault._lock_fd is not None
        assert vault._lock_path.exists()

        vault._release_lock()
        assert vault._lock_fd is None

    def test_release_lock_without_acquire_is_safe(self, vault: Vault) -> None:
        """Releasing lock without acquiring does not raise."""
        vault._release_lock()  # Should not raise

    def test_vault_lock_context_manager(self, vault: Vault) -> None:
        """_vault_lock context manager acquires and releases."""
        vault._ensure_vault_dir()

        with vault._vault_lock():
            assert vault._lock_fd is not None

        assert vault._lock_fd is None

    def test_vault_lock_context_releases_on_exception(self, vault: Vault) -> None:
        """_vault_lock releases lock even on exception."""
        vault._ensure_vault_dir()

        with pytest.raises(ValueError):
            with vault._vault_lock():
                assert vault._lock_fd is not None
                raise ValueError("test error")

        assert vault._lock_fd is None


class TestAtomicWrite:
    """Tests for atomic write operations."""

    def test_atomic_write_creates_file(self, unlocked_vault: Vault) -> None:
        """Atomic write creates file with correct content."""
        test_data = b"test encrypted content"
        unlocked_vault._atomic_write(test_data)

        assert unlocked_vault.path.exists()
        assert unlocked_vault.path.read_bytes() == test_data

    def test_atomic_write_sets_permissions(self, unlocked_vault: Vault) -> None:
        """Atomic write sets secure file permissions."""
        unlocked_vault._atomic_write(b"test content")

        if sys.platform != "win32":
            mode = stat.S_IMODE(unlocked_vault.path.stat().st_mode)
            assert mode == 0o600

    def test_atomic_write_replaces_existing(self, unlocked_vault: Vault) -> None:
        """Atomic write replaces existing file content."""
        unlocked_vault.path.write_bytes(b"old content")
        unlocked_vault._atomic_write(b"new content")

        assert unlocked_vault.path.read_bytes() == b"new content"

    def test_is_fd_closed_returns_true_for_closed(self) -> None:
        """_is_fd_closed returns True for closed file descriptor."""
        fd = os.open(
            tempfile.mktemp(),
            os.O_CREAT | os.O_RDWR,
            0o600,
        )
        os.close(fd)
        assert Vault._is_fd_closed(fd) is True

    def test_is_fd_closed_returns_false_for_open(self) -> None:
        """_is_fd_closed returns False for open file descriptor."""
        fd = os.open(
            tempfile.mktemp(),
            os.O_CREAT | os.O_RDWR,
            0o600,
        )
        try:
            assert Vault._is_fd_closed(fd) is False
        finally:
            os.close(fd)


class TestErrorClasses:
    """Tests for vault exception classes."""

    def test_vault_error_is_exception(self) -> None:
        """VaultError is a base exception."""
        assert issubclass(VaultError, Exception)

    def test_vault_not_found_error_is_vault_error(self) -> None:
        """VaultNotFoundError is a VaultError."""
        assert issubclass(VaultNotFoundError, VaultError)

    def test_vault_corrupted_error_is_vault_error(self) -> None:
        """VaultCorruptedError is a VaultError."""
        assert issubclass(VaultCorruptedError, VaultError)

    def test_vault_lock_error_is_vault_error(self) -> None:
        """VaultLockError is a VaultError."""
        assert issubclass(VaultLockError, VaultError)

    def test_salt_integrity_error_is_vault_error(self) -> None:
        """SaltIntegrityError is a VaultError."""
        assert issubclass(SaltIntegrityError, VaultError)


class TestSecurityInvariants:
    """Tests validating security properties and invariants."""

    def test_vault_file_never_contains_plaintext(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """Vault file never contains plaintext credential data."""
        unlocked_vault.add_email(sample_email)

        encrypted_data = unlocked_vault.path.read_bytes()

        # Plaintext should not appear in encrypted file
        assert sample_email.email.encode() not in encrypted_data
        assert sample_email.password.encode() not in encrypted_data
        assert sample_email.label.encode() not in encrypted_data

    def test_salt_file_is_random(self, vault: Vault) -> None:
        """Salt file contains cryptographically random bytes."""
        vault.create("TestPassword123!")

        salt = vault._salt_path.read_bytes()
        assert len(salt) == 32  # SALT_LENGTH

        # Salt should be high entropy (simple check: no obvious patterns)
        assert salt != b"\x00" * 32
        assert salt != b"\xff" * 32

    def test_different_vaults_have_different_salts(self, tmp_path: Path) -> None:
        """Different vault instances have different salts."""
        salts = []
        for i in range(3):
            vault_dir = tmp_path / f"vault_{i}"
            vault_dir.mkdir()
            v = Vault(
                vault_path=vault_dir / "vault.enc",
                salt_path=vault_dir / "salt",
            )
            v.create("TestPassword123!")
            salts.append(v._salt_path.read_bytes())
            v.lock()

        assert len(set(salts)) == 3

    def test_wrong_password_does_not_leak_data(self, vault: Vault) -> None:
        """Failed decryption does not expose any data."""
        vault.create("CorrectPassword123!")
        vault.add_email(
            EmailCredential(
                label="Secret",
                email="secret@test.com",
                password="SecretPassword!",
            )
        )
        vault.lock()

        try:
            vault.unlock("WrongPassword123!")
            pytest.fail("Should have raised DecryptionError")
        except DecryptionError as e:
            error_msg = str(e).lower()
            assert "secret" not in error_msg
            assert "password" not in error_msg or "wrong" in error_msg

    def test_credentials_cleared_on_lock(
        self, unlocked_vault: Vault, sample_email: EmailCredential
    ) -> None:
        """All credentials cleared from memory on lock."""
        unlocked_vault.add_email(sample_email)
        unlocked_vault.lock()

        # Check all data structures are empty
        for key in unlocked_vault._data:
            assert unlocked_vault._data[key] == []


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_vault_operations(self, unlocked_vault: Vault) -> None:
        """Operations on empty vault work correctly."""
        assert unlocked_vault.get_emails() == []
        assert unlocked_vault.get_phones() == []
        assert unlocked_vault.get_cards() == []
        assert unlocked_vault.get_envs() == []
        assert unlocked_vault.get_recovery_entries() == []
        assert unlocked_vault.get_notes() == []
        assert unlocked_vault.search("anything") == []
        assert unlocked_vault.get_stats()["total"] == 0

    def test_unicode_credentials(self, unlocked_vault: Vault) -> None:
        """Unicode data in credentials is handled correctly."""
        email = EmailCredential(
            label="日本語サービス",
            email="user@日本.jp",
            password="パスワード123!",
            notes="Unicode test with emoji: 🔐",
        )
        unlocked_vault.add_email(email)

        password = "TestMasterPassword123!"
        unlocked_vault.lock()
        unlocked_vault.unlock(password)

        loaded = unlocked_vault.get_emails()[0]
        assert loaded.label == "日本語サービス"
        assert loaded.email == "user@日本.jp"
        assert loaded.notes is not None
        assert "🔐" in loaded.notes

    def test_large_credential_data(self, unlocked_vault: Vault) -> None:
        """Large credential data is handled correctly."""
        # Create env with large content
        large_content = "KEY=value\n" * 10000  # ~100KB
        env = EnvEntry(
            title="Large ENV",
            filename=".env.large",
            content=large_content,
        )
        unlocked_vault.add_env(env)

        password = "TestMasterPassword123!"
        unlocked_vault.lock()
        unlocked_vault.unlock(password)

        loaded = unlocked_vault.get_envs()[0]
        assert loaded.content == large_content

    def test_many_credentials(self, unlocked_vault: Vault) -> None:
        """Vault handles many credentials correctly."""
        for i in range(100):
            email = EmailCredential(
                label=f"Service {i}",
                email=f"user{i}@test.com",
                password=f"pass{i}!",
            )
            unlocked_vault.add_email(email)

        assert len(unlocked_vault.get_emails()) == 100

        password = "TestMasterPassword123!"
        unlocked_vault.lock()
        unlocked_vault.unlock(password)

        assert len(unlocked_vault.get_emails()) == 100

    def test_special_characters_in_notes(self, unlocked_vault: Vault) -> None:
        """Special characters in notes field work correctly."""
        email = EmailCredential(
            label="Test",
            email="t@t.com",
            password="p",
            notes="Special chars: <>&\"'\\n\\t\x00",
        )
        unlocked_vault.add_email(email)

        password = "TestMasterPassword123!"
        unlocked_vault.lock()
        unlocked_vault.unlock(password)

        loaded = unlocked_vault.get_emails()[0]
        assert loaded.notes == email.notes

    def test_activity_updated_on_operations(self, unlocked_vault: Vault) -> None:
        """Activity timestamp updated on vault operations."""
        initial_time = unlocked_vault._last_activity

        time.sleep(0.01)  # Small delay to ensure time difference
        unlocked_vault.get_emails()

        assert unlocked_vault._last_activity >= initial_time


class TestConcurrentAccess:
    """Tests for concurrent access behavior (behavioral tests)."""

    def test_lock_timeout_constant(self) -> None:
        """Lock timeout constant is reasonable."""
        assert LOCK_TIMEOUT_SECONDS >= 1.0
        assert LOCK_TIMEOUT_SECONDS <= 60.0

    def test_second_vault_instance_can_read_after_unlock(
        self, vault_path: Path, salt_path: Path
    ) -> None:
        """Second vault instance can read after first releases lock."""
        password = "TestPassword123!"

        vault1 = Vault(vault_path=vault_path, salt_path=salt_path)
        vault1.create(password)
        vault1.add_email(EmailCredential(label="Test", email="t@t.com", password="p"))
        vault1.lock()

        # Second instance should be able to unlock
        vault2 = Vault(vault_path=vault_path, salt_path=salt_path)
        vault2.unlock(password)

        emails = vault2.get_emails()
        assert len(emails) == 1
        vault2.lock()


class TestLegacySaltSave:
    """Tests for legacy _save_salt method."""

    def test_save_salt_creates_file(self, vault: Vault) -> None:
        """Legacy _save_salt creates salt file."""
        vault._ensure_vault_dir()
        salt = os.urandom(32)
        vault._save_salt(salt)

        assert vault._salt_path.exists()
        assert vault._salt_path.read_bytes() == salt

    def test_save_salt_sets_permissions(self, vault: Vault) -> None:
        """Legacy _save_salt sets secure file permissions."""
        vault._ensure_vault_dir()
        vault._save_salt(os.urandom(32))

        if sys.platform != "win32":
            mode = stat.S_IMODE(vault._salt_path.stat().st_mode)
            assert mode == 0o600


class TestVerifySaltIntegrity:
    """Tests for _verify_salt_integrity edge cases."""

    def test_verify_with_no_cached_hash_returns_early(self, vault: Vault) -> None:
        """_verify_salt_integrity returns early when no cached hash."""
        vault._cached_salt_hash = None
        # Should not raise even without salt file
        vault._verify_salt_integrity()


class TestSaveUnlocked:
    """Tests for _save_unlocked method."""

    def test_save_unlocked_when_locked_raises_error(self, vault: Vault) -> None:
        """_save_unlocked raises VaultError when vault is locked."""
        vault._crypto = None
        with pytest.raises(VaultError, match="locked"):
            vault._save_unlocked()


class TestFsyncDirectory:
    """Tests for _fsync_directory method."""

    def test_fsync_directory_works(self, unlocked_vault: Vault) -> None:
        """_fsync_directory syncs directory on Unix."""
        if sys.platform == "win32":
            pytest.skip("fsync directory is no-op on Windows")

        # Should not raise
        unlocked_vault._fsync_directory(unlocked_vault.path.parent)


class TestRecoveryNotesKeyInitialization:
    """Tests for recovery and notes key initialization."""

    def test_add_recovery_initializes_missing_key(
        self, vault_path: Path, salt_path: Path
    ) -> None:
        """Adding recovery initializes 'recovery' key if missing."""
        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create("TestPassword123!")
        # Simulate old vault without 'recovery' key
        del vault._data["recovery"]

        recovery = RecoveryEntry(title="Test", content="codes")
        vault.add_recovery(recovery)

        assert "recovery" in vault._data
        assert len(vault._data["recovery"]) == 1

    def test_add_note_initializes_missing_key(
        self, vault_path: Path, salt_path: Path
    ) -> None:
        """Adding note initializes 'notes' key if missing."""
        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create("TestPassword123!")
        # Simulate old vault without 'notes' key
        del vault._data["notes"]

        note = NoteEntry(title="Test", content="content")
        vault.add_note(note)

        assert "notes" in vault._data
        assert len(vault._data["notes"]) == 1


class TestAtomicWriteErrorHandling:
    """Tests for atomic write error handling paths."""

    def test_atomic_write_cleans_up_on_replace_error(
        self, vault_path: Path, salt_path: Path
    ) -> None:
        """Atomic write cleans up temp file if os.replace fails."""
        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create("TestPassword123!")

        # Mock os.replace to raise an error
        with mock.patch("os.replace", side_effect=OSError("Mocked error")):
            with pytest.raises(OSError):
                vault._atomic_write(b"test content")

        # Temp files should be cleaned up (none left in parent dir)
        temp_files = list(vault.path.parent.glob(".vault_*.tmp"))
        assert len(temp_files) == 0


class TestSaveSaltAtomicErrorHandling:
    """Tests for _save_salt_atomic error handling."""

    def test_save_salt_atomic_cleans_up_on_error(self, vault: Vault) -> None:
        """_save_salt_atomic cleans up temp file on error."""
        vault._ensure_vault_dir()

        # Mock os.replace to raise an error
        with mock.patch("os.replace", side_effect=OSError("Mocked error")):
            with pytest.raises(OSError):
                vault._save_salt_atomic(os.urandom(32))

        # Temp files should be cleaned up
        temp_files = list(vault._salt_path.parent.glob(".salt_*.tmp"))
        assert len(temp_files) == 0


class TestImportDataKeyInitialization:
    """Tests for import_data key initialization."""

    def test_import_initializes_missing_category_keys(
        self, unlocked_vault: Vault
    ) -> None:
        """import_data initializes missing category keys during import."""
        # Remove a key to simulate old vault format
        del unlocked_vault._data["notes"]

        import_data = {
            "notes": [{"id": "n1", "title": "N", "content": "note"}],
        }

        counts = unlocked_vault.import_data(import_data, merge=True)
        assert counts["notes"] == 1
        assert "notes" in unlocked_vault._data


class TestSearchWithNoneNotes:
    """Tests for search with None notes field."""

    def test_search_handles_none_notes(self, unlocked_vault: Vault) -> None:
        """Search handles credentials with None notes field."""
        email = EmailCredential(
            label="Test",
            email="test@example.com",
            password="pass123",
            notes=None,
        )
        unlocked_vault.add_email(email)

        # Should not raise when notes is None
        results = unlocked_vault.search("Test")
        assert len(results) == 1

    def test_search_with_none_notes_in_all_types(self, unlocked_vault: Vault) -> None:
        """Search handles None notes in all credential types."""
        phone = PhoneCredential(label="Phone", phone="123", password="1234", notes=None)
        card = CreditCard(
            label="Card",
            card_number="4111",
            expiry="12/25",
            cvv="123",
            cardholder_name="Test",
            notes=None,
        )
        env = EnvEntry(title="Env", filename=".env", content="X=Y", notes=None)
        recovery = RecoveryEntry(title="Recovery", content="codes", notes=None)
        note = NoteEntry(title="Note", content="content", notes=None)

        unlocked_vault.add_phone(phone)
        unlocked_vault.add_card(card)
        unlocked_vault.add_env(env)
        unlocked_vault.add_recovery(recovery)
        unlocked_vault.add_note(note)

        # Should not raise
        results = unlocked_vault.search("test_nonexistent_query")
        assert results == []
