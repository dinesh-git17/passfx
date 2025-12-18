# Integration Tests for Vault Encryption Round-Trips
# Validates that CryptoManager and Vault work correctly together across real workflows.
# Tests data integrity, persistence, and state transitions using actual encryption.

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from passfx.core.crypto import DecryptionError
from passfx.core.models import (
    CreditCard,
    EmailCredential,
    EnvEntry,
    NoteEntry,
    PhoneCredential,
    RecoveryEntry,
)
from passfx.core.vault import Vault, VaultCorruptedError, VaultError, VaultNotFoundError

if TYPE_CHECKING:
    from collections.abc import Callable


# Strong test password that meets validation requirements
TEST_PASSWORD = "SecurePass123!@#"
ALTERNATE_PASSWORD = "AnotherSecure456$%^"


class TestVaultCreationAndUnlock:
    """Tests for vault creation and unlock round-trips."""

    @pytest.mark.integration
    def test_create_vault_then_unlock(self, temp_vault_dir: Path) -> None:
        """Create a new vault, lock it, then unlock with correct password."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        assert vault.exists
        assert not vault.is_locked
        assert vault_path.exists()
        assert salt_path.exists()

        # Lock and re-unlock
        vault.lock()
        assert vault.is_locked

        vault.unlock(TEST_PASSWORD)
        assert not vault.is_locked

    @pytest.mark.integration
    def test_create_vault_wrong_password_fails(self, temp_vault_dir: Path) -> None:
        """Unlock with wrong password raises DecryptionError."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.lock()

        with pytest.raises(DecryptionError):
            vault.unlock("WrongPassword123!")

        # Vault should remain locked after failed unlock
        assert vault.is_locked

    @pytest.mark.integration
    def test_unlock_nonexistent_vault_raises_error(self, temp_vault_dir: Path) -> None:
        """Attempting to unlock a non-existent vault raises VaultNotFoundError."""
        vault_path = temp_vault_dir / "nonexistent.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)

        with pytest.raises(VaultNotFoundError):
            vault.unlock(TEST_PASSWORD)


class TestCredentialRoundTrips:
    """Tests for credential CRUD operations across save/load cycles."""

    @pytest.mark.integration
    def test_email_credential_roundtrip(self, temp_vault_dir: Path) -> None:
        """Add email credential, save, reload, verify data intact."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        # Create vault and add credential
        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        email_cred = EmailCredential(
            label="GitHub",
            email="user@example.com",
            password="gh_secret_password",
            notes="Personal account",
        )
        vault.add_email(email_cred)
        cred_id = email_cred.id

        # Lock and reload
        vault.lock()
        vault.unlock(TEST_PASSWORD)

        # Verify data
        loaded = vault.get_email_by_id(cred_id)
        assert loaded is not None
        assert loaded.label == "GitHub"
        assert loaded.email == "user@example.com"
        assert loaded.password == "gh_secret_password"
        assert loaded.notes == "Personal account"

    @pytest.mark.integration
    def test_phone_credential_roundtrip(self, temp_vault_dir: Path) -> None:
        """Add phone credential, save, reload, verify data intact."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        phone_cred = PhoneCredential(
            label="Bank PIN",
            phone="+1234567890",
            password="1234",
            notes="Primary bank",
        )
        vault.add_phone(phone_cred)
        cred_id = phone_cred.id

        vault.lock()
        vault.unlock(TEST_PASSWORD)

        loaded = vault.get_phone_by_id(cred_id)
        assert loaded is not None
        assert loaded.label == "Bank PIN"
        assert loaded.phone == "+1234567890"
        assert loaded.password == "1234"

    @pytest.mark.integration
    def test_credit_card_roundtrip(self, temp_vault_dir: Path) -> None:
        """Add credit card, save, reload, verify data intact."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        card = CreditCard(
            label="Chase Sapphire",
            card_number="4111111111111111",
            expiry="12/25",
            cvv="123",
            cardholder_name="John Doe",
            notes="Primary card",
        )
        vault.add_card(card)
        card_id = card.id

        vault.lock()
        vault.unlock(TEST_PASSWORD)

        loaded = vault.get_card_by_id(card_id)
        assert loaded is not None
        assert loaded.label == "Chase Sapphire"
        assert loaded.card_number == "4111111111111111"
        assert loaded.expiry == "12/25"
        assert loaded.cvv == "123"
        assert loaded.cardholder_name == "John Doe"

    @pytest.mark.integration
    def test_env_entry_roundtrip(self, temp_vault_dir: Path) -> None:
        """Add env entry, save, reload, verify data intact."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        env = EnvEntry(
            title="Production API",
            filename=".env.production",
            content="API_KEY=secret123\nDB_URL=postgres://...",
            notes="Production environment",
        )
        vault.add_env(env)
        env_id = env.id

        vault.lock()
        vault.unlock(TEST_PASSWORD)

        loaded = vault.get_env_by_id(env_id)
        assert loaded is not None
        assert loaded.title == "Production API"
        assert loaded.filename == ".env.production"
        assert loaded.content == "API_KEY=secret123\nDB_URL=postgres://..."

    @pytest.mark.integration
    def test_recovery_entry_roundtrip(self, temp_vault_dir: Path) -> None:
        """Add recovery codes, save, reload, verify data intact."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        recovery = RecoveryEntry(
            title="GitHub 2FA",
            content="abc123\ndef456\nghi789",
            notes="Backup codes",
        )
        vault.add_recovery(recovery)
        recovery_id = recovery.id

        vault.lock()
        vault.unlock(TEST_PASSWORD)

        loaded = vault.get_recovery_by_id(recovery_id)
        assert loaded is not None
        assert loaded.title == "GitHub 2FA"
        assert loaded.content == "abc123\ndef456\nghi789"

    @pytest.mark.integration
    def test_note_entry_roundtrip(self, temp_vault_dir: Path) -> None:
        """Add secure note, save, reload, verify data intact."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        note = NoteEntry(
            title="Office Wi-Fi",
            content="SSID: CorpNet\nPassword: wifi_secret",
            notes="Main office",
        )
        vault.add_note(note)
        note_id = note.id

        vault.lock()
        vault.unlock(TEST_PASSWORD)

        loaded = vault.get_note_by_id(note_id)
        assert loaded is not None
        assert loaded.title == "Office Wi-Fi"
        assert loaded.content == "SSID: CorpNet\nPassword: wifi_secret"


class TestMultipleSaveLoadCycles:
    """Tests for data persistence across multiple save/load cycles."""

    @pytest.mark.integration
    def test_multiple_credentials_persist_across_cycles(
        self, temp_vault_dir: Path
    ) -> None:
        """Multiple credentials survive multiple lock/unlock cycles."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        # First cycle: create and add credentials
        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        email1 = EmailCredential(label="Site1", email="a@b.com", password="pw1")
        email2 = EmailCredential(label="Site2", email="c@d.com", password="pw2")
        vault.add_email(email1)
        vault.add_email(email2)

        # Second cycle
        vault.lock()
        vault.unlock(TEST_PASSWORD)
        emails = vault.get_emails()
        assert len(emails) == 2

        # Add more credentials
        card = CreditCard(
            label="Card1",
            card_number="4111111111111111",
            expiry="12/25",
            cvv="123",
            cardholder_name="Test User",
        )
        vault.add_card(card)

        # Third cycle
        vault.lock()
        vault.unlock(TEST_PASSWORD)

        # Verify all data persisted
        assert len(vault.get_emails()) == 2
        assert len(vault.get_cards()) == 1

        # Fourth cycle with new instance
        vault.lock()
        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        new_vault.unlock(TEST_PASSWORD)

        assert len(new_vault.get_emails()) == 2
        assert len(new_vault.get_cards()) == 1

    @pytest.mark.integration
    def test_five_consecutive_save_load_cycles(self, temp_vault_dir: Path) -> None:
        """Data remains intact after five consecutive save/load cycles."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        # Add initial credential
        email = EmailCredential(
            label="Persistent",
            email="test@test.com",
            password="persistent_password",
        )
        vault.add_email(email)
        cred_id = email.id

        # Five cycles
        for i in range(5):
            vault.lock()
            vault.unlock(TEST_PASSWORD)
            loaded = vault.get_email_by_id(cred_id)
            assert loaded is not None, f"Credential missing at cycle {i + 1}"
            assert (
                loaded.password == "persistent_password"
            ), f"Password wrong at cycle {i + 1}"


class TestUpdateAndDeletePersistence:
    """Tests for CRUD operations persisting correctly."""

    @pytest.mark.integration
    def test_update_credential_persists(self, temp_vault_dir: Path) -> None:
        """Updated credential values persist after save/load."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        email = EmailCredential(
            label="Original",
            email="old@test.com",
            password="old_password",
        )
        vault.add_email(email)
        cred_id = email.id

        # Update the credential
        vault.update_email(
            cred_id,
            label="Updated",
            email="new@test.com",
            password="new_password",
        )

        # Lock and reload
        vault.lock()
        vault.unlock(TEST_PASSWORD)

        loaded = vault.get_email_by_id(cred_id)
        assert loaded is not None
        assert loaded.label == "Updated"
        assert loaded.email == "new@test.com"
        assert loaded.password == "new_password"

    @pytest.mark.integration
    def test_delete_credential_persists(self, temp_vault_dir: Path) -> None:
        """Deleted credentials remain deleted after save/load."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        email1 = EmailCredential(label="Keep", email="keep@test.com", password="pw1")
        email2 = EmailCredential(
            label="Delete", email="delete@test.com", password="pw2"
        )
        vault.add_email(email1)
        vault.add_email(email2)

        keep_id = email1.id
        delete_id = email2.id

        # Delete one credential
        result = vault.delete_email(delete_id)
        assert result is True

        # Lock and reload
        vault.lock()
        vault.unlock(TEST_PASSWORD)

        # Verify state
        assert vault.get_email_by_id(keep_id) is not None
        assert vault.get_email_by_id(delete_id) is None
        assert len(vault.get_emails()) == 1

    @pytest.mark.integration
    def test_update_overwrites_previous_values(self, temp_vault_dir: Path) -> None:
        """Multiple updates correctly overwrite previous values."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        card = CreditCard(
            label="Card",
            card_number="1111222233334444",
            expiry="01/25",
            cvv="111",
            cardholder_name="First Name",
        )
        vault.add_card(card)
        card_id = card.id

        # First update
        vault.update_card(card_id, cardholder_name="Second Name")
        vault.lock()
        vault.unlock(TEST_PASSWORD)

        # Second update
        vault.update_card(card_id, cardholder_name="Third Name")
        vault.lock()
        vault.unlock(TEST_PASSWORD)

        loaded = vault.get_card_by_id(card_id)
        assert loaded is not None
        assert loaded.cardholder_name == "Third Name"


class TestPasswordChange:
    """Tests for password change scenarios."""

    @pytest.mark.integration
    def test_change_password_old_fails_new_works(self, temp_vault_dir: Path) -> None:
        """After password change, old password fails and new password works."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        # Create vault with original password
        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        email = EmailCredential(
            label="Survives Password Change",
            email="test@test.com",
            password="credential_password",
        )
        vault.add_email(email)
        cred_id = email.id
        vault.lock()

        # Unlock with original password
        vault.unlock(TEST_PASSWORD)
        data = vault.get_all_data()
        vault.lock()

        # Delete old vault and recreate with new password
        vault_path.unlink()
        salt_path.unlink()

        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        new_vault.create(ALTERNATE_PASSWORD)

        # Re-import the data (simulating password change)
        new_vault.import_data(data, merge=False)
        new_vault.lock()

        # Old password should fail
        with pytest.raises(DecryptionError):
            new_vault.unlock(TEST_PASSWORD)

        # New password should work
        new_vault.unlock(ALTERNATE_PASSWORD)
        loaded = new_vault.get_email_by_id(cred_id)
        assert loaded is not None
        assert loaded.password == "credential_password"

    @pytest.mark.integration
    def test_data_preserved_after_password_change(self, temp_vault_dir: Path) -> None:
        """All credential types survive a password change."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        # Create vault with various credentials
        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        email = EmailCredential(label="Email", email="e@e.com", password="e_pw")
        phone = PhoneCredential(label="Phone", phone="555", password="1234")
        card = CreditCard(
            label="Card",
            card_number="4111111111111111",
            expiry="12/25",
            cvv="123",
            cardholder_name="Test",
        )
        env = EnvEntry(title="Env", filename=".env", content="KEY=VAL")
        recovery = RecoveryEntry(title="Recovery", content="abc123")
        note = NoteEntry(title="Note", content="Secret note")

        vault.add_email(email)
        vault.add_phone(phone)
        vault.add_card(card)
        vault.add_env(env)
        vault.add_recovery(recovery)
        vault.add_note(note)

        # Export all data
        data = vault.get_all_data()
        vault.lock()

        # Recreate with new password
        vault_path.unlink()
        salt_path.unlink()
        backup_path = vault_path.with_suffix(".enc.bak")
        if backup_path.exists():
            backup_path.unlink()

        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        new_vault.create(ALTERNATE_PASSWORD)
        new_vault.import_data(data, merge=False)
        new_vault.lock()

        # Verify all data
        new_vault.unlock(ALTERNATE_PASSWORD)
        assert len(new_vault.get_emails()) == 1
        assert len(new_vault.get_phones()) == 1
        assert len(new_vault.get_cards()) == 1
        assert len(new_vault.get_envs()) == 1
        assert len(new_vault.get_recovery_entries()) == 1
        assert len(new_vault.get_notes()) == 1


class TestVaultStateConsistency:
    """Tests for vault state consistency across operations."""

    @pytest.mark.integration
    def test_lock_clears_in_memory_data(self, temp_vault_dir: Path) -> None:
        """Locking vault clears all in-memory credential data."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        email = EmailCredential(label="Secret", email="s@s.com", password="secret_pw")
        vault.add_email(email)

        # Verify data is present
        assert len(vault.get_emails()) == 1

        # Lock should clear in-memory data
        vault.lock()

        # Accessing internal data directly to verify it's cleared
        assert vault._data == {
            "emails": [],
            "phones": [],
            "cards": [],
            "envs": [],
            "recovery": [],
            "notes": [],
        }

    @pytest.mark.integration
    def test_stats_accurate_after_operations(self, temp_vault_dir: Path) -> None:
        """Vault stats reflect actual credential counts after CRUD operations."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        # Initial stats
        stats = vault.get_stats()
        assert stats["total"] == 0

        # Add credentials
        vault.add_email(EmailCredential(label="E1", email="e1@e.com", password="pw"))
        vault.add_email(EmailCredential(label="E2", email="e2@e.com", password="pw"))
        vault.add_phone(PhoneCredential(label="P1", phone="555", password="1234"))

        stats = vault.get_stats()
        assert stats["emails"] == 2
        assert stats["phones"] == 1
        assert stats["total"] == 3

        # Delete one
        emails = vault.get_emails()
        vault.delete_email(emails[0].id)

        stats = vault.get_stats()
        assert stats["emails"] == 1
        assert stats["total"] == 2

        # Verify persists after reload
        vault.lock()
        vault.unlock(TEST_PASSWORD)

        stats = vault.get_stats()
        assert stats["emails"] == 1
        assert stats["phones"] == 1
        assert stats["total"] == 2

    @pytest.mark.integration
    def test_search_finds_credentials_after_reload(self, temp_vault_dir: Path) -> None:
        """Search functionality works correctly after save/load cycle."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        vault.add_email(
            EmailCredential(label="GitHub", email="gh@gh.com", password="pw")
        )
        vault.add_email(
            EmailCredential(label="GitLab", email="gl@gl.com", password="pw")
        )
        vault.add_email(
            EmailCredential(label="Bitbucket", email="bb@bb.com", password="pw")
        )

        vault.lock()
        vault.unlock(TEST_PASSWORD)

        results = vault.search("Git")
        assert len(results) == 2

        results = vault.search("Bitbucket")
        assert len(results) == 1


class TestFailureScenarios:
    """Tests for failure handling and recovery."""

    @pytest.mark.integration
    def test_loading_invalid_vault_fails_safely(self, temp_vault_dir: Path) -> None:
        """Loading a corrupted vault file raises appropriate error."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        # Create valid vault
        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.lock()

        # Corrupt the vault file
        vault_path.write_bytes(b"not valid encrypted data")

        # Attempt to unlock should fail
        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        with pytest.raises(DecryptionError):
            new_vault.unlock(TEST_PASSWORD)

    @pytest.mark.integration
    def test_missing_salt_file_fails_safely(self, temp_vault_dir: Path) -> None:
        """Missing salt file raises VaultCorruptedError on unlock."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.lock()

        # Delete salt file
        salt_path.unlink()

        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        with pytest.raises(VaultCorruptedError, match="Salt file missing"):
            new_vault.unlock(TEST_PASSWORD)

    @pytest.mark.integration
    def test_vault_remains_readable_after_partial_operations(
        self, temp_vault_dir: Path
    ) -> None:
        """Vault remains readable after failed operations."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        email = EmailCredential(label="Existing", email="e@e.com", password="pw")
        vault.add_email(email)
        cred_id = email.id

        # Try to delete non-existent credential (no-op, returns False)
        result = vault.delete_email("nonexistent_id")
        assert result is False

        # Try to update non-existent credential (no-op, returns False)
        result = vault.update_email("nonexistent_id", label="New")
        assert result is False

        # Vault should still be functional
        vault.lock()
        vault.unlock(TEST_PASSWORD)

        loaded = vault.get_email_by_id(cred_id)
        assert loaded is not None
        assert loaded.label == "Existing"

    @pytest.mark.integration
    def test_create_vault_already_exists_raises_error(
        self, temp_vault_dir: Path
    ) -> None:
        """Creating a vault that already exists raises VaultError."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        # Try to create again
        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        with pytest.raises(VaultError, match="Vault already exists"):
            new_vault.create(TEST_PASSWORD)


class TestDataIntegrityWithAllTypes:
    """Tests validating data integrity across all credential types."""

    @pytest.mark.integration
    def test_all_credential_types_in_single_vault(self, temp_vault_dir: Path) -> None:
        """All six credential types persist correctly in a single vault."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        # Add one of each type
        email = EmailCredential(
            label="Email Test",
            email="email@test.com",
            password="email_pw_secret",
        )
        phone = PhoneCredential(
            label="Phone Test",
            phone="+1-555-123-4567",
            password="7890",
        )
        card = CreditCard(
            label="Card Test",
            card_number="5500000000000004",
            expiry="06/28",
            cvv="456",
            cardholder_name="Test Cardholder",
        )
        env = EnvEntry(
            title="Env Test",
            filename=".env.test",
            content="SECRET_KEY=abcdef123456\nDATABASE_URL=postgres://localhost",
        )
        recovery = RecoveryEntry(
            title="Recovery Test",
            content="code1-abcd\ncode2-efgh\ncode3-ijkl",
        )
        note = NoteEntry(
            title="Note Test",
            content="This is a secret note with sensitive information.",
        )

        vault.add_email(email)
        vault.add_phone(phone)
        vault.add_card(card)
        vault.add_env(env)
        vault.add_recovery(recovery)
        vault.add_note(note)

        email_id = email.id
        phone_id = phone.id
        card_id = card.id
        env_id = env.id
        recovery_id = recovery.id
        note_id = note.id

        # Lock and create fresh instance
        vault.lock()

        new_vault = Vault(vault_path=vault_path, salt_path=salt_path)
        new_vault.unlock(TEST_PASSWORD)

        # Verify all data
        loaded_email = new_vault.get_email_by_id(email_id)
        assert loaded_email is not None
        assert loaded_email.password == "email_pw_secret"

        loaded_phone = new_vault.get_phone_by_id(phone_id)
        assert loaded_phone is not None
        assert loaded_phone.password == "7890"

        loaded_card = new_vault.get_card_by_id(card_id)
        assert loaded_card is not None
        assert loaded_card.cvv == "456"
        assert loaded_card.card_number == "5500000000000004"

        loaded_env = new_vault.get_env_by_id(env_id)
        assert loaded_env is not None
        assert "SECRET_KEY=abcdef123456" in loaded_env.content

        loaded_recovery = new_vault.get_recovery_by_id(recovery_id)
        assert loaded_recovery is not None
        assert "code1-abcd" in loaded_recovery.content

        loaded_note = new_vault.get_note_by_id(note_id)
        assert loaded_note is not None
        assert "sensitive information" in loaded_note.content

    @pytest.mark.integration
    def test_import_export_roundtrip(self, temp_vault_dir: Path) -> None:
        """Export and import preserves all data."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        # Create and populate vault
        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        for i in range(3):
            vault.add_email(
                EmailCredential(
                    label=f"Email{i}",
                    email=f"e{i}@test.com",
                    password=f"password{i}",
                )
            )
            vault.add_phone(
                PhoneCredential(
                    label=f"Phone{i}",
                    phone=f"555-000{i}",
                    password=f"pin{i}",
                )
            )

        # Export data
        exported = vault.get_all_data()
        vault.lock()

        # Create new vault and import
        new_vault_path = temp_vault_dir / "vault2.enc"
        new_salt_path = temp_vault_dir / "salt2"

        new_vault = Vault(vault_path=new_vault_path, salt_path=new_salt_path)
        new_vault.create(ALTERNATE_PASSWORD)
        counts = new_vault.import_data(exported, merge=False)

        assert counts["emails"] == 3
        assert counts["phones"] == 3

        # Verify data
        emails = new_vault.get_emails()
        phones = new_vault.get_phones()
        assert len(emails) == 3
        assert len(phones) == 3


class TestBackupBehavior:
    """Tests for vault backup behavior during saves."""

    @pytest.mark.integration
    def test_backup_created_on_save(self, temp_vault_dir: Path) -> None:
        """Backup file is created when saving to existing vault."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"
        backup_path = vault_path.with_suffix(".enc.bak")

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)

        # First save doesn't create backup (no existing file to back up)
        assert not backup_path.exists()

        # Add credential to trigger save
        vault.add_email(EmailCredential(label="Test", email="t@t.com", password="pw"))

        # Backup should exist now
        assert backup_path.exists()

    @pytest.mark.integration
    def test_backup_has_secure_permissions(
        self, temp_vault_dir: Path, assert_file_permissions: Callable[[Path, int], None]
    ) -> None:
        """Backup file has secure permissions (0600)."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"
        backup_path = vault_path.with_suffix(".enc.bak")

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.add_email(EmailCredential(label="Test", email="t@t.com", password="pw"))

        # On macOS/Linux, check permissions
        if os.name != "nt":
            assert_file_permissions(backup_path, 0o600)


class TestCryptoVaultInteraction:
    """Tests verifying CryptoManager and Vault work together correctly."""

    @pytest.mark.integration
    def test_different_vaults_different_salts(self, temp_vault_dir: Path) -> None:
        """Each vault gets a unique salt."""
        vault1_path = temp_vault_dir / "vault1.enc"
        salt1_path = temp_vault_dir / "salt1"
        vault2_path = temp_vault_dir / "vault2.enc"
        salt2_path = temp_vault_dir / "salt2"

        vault1 = Vault(vault_path=vault1_path, salt_path=salt1_path)
        vault1.create(TEST_PASSWORD)

        vault2 = Vault(vault_path=vault2_path, salt_path=salt2_path)
        vault2.create(TEST_PASSWORD)

        # Salts should be different
        salt1 = salt1_path.read_bytes()
        salt2 = salt2_path.read_bytes()
        assert salt1 != salt2

    @pytest.mark.integration
    def test_same_password_different_salts_different_ciphertext(
        self, temp_vault_dir: Path
    ) -> None:
        """Same data encrypted with same password but different salts yields different ciphertext."""
        vault1_path = temp_vault_dir / "vault1.enc"
        salt1_path = temp_vault_dir / "salt1"
        vault2_path = temp_vault_dir / "vault2.enc"
        salt2_path = temp_vault_dir / "salt2"

        # Create two vaults with identical data
        for vault_path, salt_path in [
            (vault1_path, salt1_path),
            (vault2_path, salt2_path),
        ]:
            vault = Vault(vault_path=vault_path, salt_path=salt_path)
            vault.create(TEST_PASSWORD)
            vault.add_email(
                EmailCredential(
                    id="same_id",
                    label="Same",
                    email="same@same.com",
                    password="same_password",
                )
            )
            vault.lock()

        # Ciphertexts should be different due to different salts and IVs
        ciphertext1 = vault1_path.read_bytes()
        ciphertext2 = vault2_path.read_bytes()
        assert ciphertext1 != ciphertext2

    @pytest.mark.integration
    def test_crypto_manager_key_derivation_consistent(
        self, temp_vault_dir: Path
    ) -> None:
        """Same password and salt always derives same key (deterministic)."""
        vault_path = temp_vault_dir / "vault.enc"
        salt_path = temp_vault_dir / "salt"

        vault = Vault(vault_path=vault_path, salt_path=salt_path)
        vault.create(TEST_PASSWORD)
        vault.add_email(
            EmailCredential(label="Test", email="t@t.com", password="secret")
        )
        vault.lock()

        # Multiple unlocks should work (key derivation is deterministic)
        for _ in range(3):
            vault.unlock(TEST_PASSWORD)
            emails = vault.get_emails()
            assert len(emails) == 1
            assert emails[0].password == "secret"
            vault.lock()
