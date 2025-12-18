# Unit tests for credential data models.
# Validates initialization, serialization, and data integrity.

from __future__ import annotations

import re
import time
from datetime import datetime

import pytest

from passfx.core.models import (
    CreditCard,
    EmailCredential,
    EnvEntry,
    NoteEntry,
    PhoneCredential,
    RecoveryEntry,
    _generate_id,
    _now_iso,
    credential_from_dict,
)


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_generate_id_returns_8_character_string(self) -> None:
        """Generated IDs are 8 characters (truncated UUID)."""
        generated_id = _generate_id()
        assert isinstance(generated_id, str)
        assert len(generated_id) == 8

    def test_generate_id_returns_hex_characters(self) -> None:
        """Generated IDs contain only valid hexadecimal characters."""
        generated_id = _generate_id()
        assert re.match(r"^[0-9a-f]{8}$", generated_id)

    def test_generate_id_produces_unique_values(self) -> None:
        """Consecutive calls produce different IDs."""
        ids = [_generate_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_now_iso_returns_valid_iso_format(self) -> None:
        """Timestamp is in ISO 8601 format."""
        timestamp = _now_iso()
        # Should be parseable by datetime
        parsed = datetime.fromisoformat(timestamp)
        assert parsed is not None

    def test_now_iso_returns_current_time(self) -> None:
        """Timestamp represents approximately current time."""
        before = datetime.now()
        timestamp = _now_iso()
        after = datetime.now()

        parsed = datetime.fromisoformat(timestamp)
        assert before <= parsed <= after


class TestEmailCredential:
    """Tests for EmailCredential dataclass."""

    def test_init_with_required_fields(self) -> None:
        """EmailCredential initializes with required fields only."""
        cred = EmailCredential(
            label="GitHub",
            email="user@example.com",
            password="secret123",
        )
        assert cred.label == "GitHub"
        assert cred.email == "user@example.com"
        assert cred.password == "secret123"
        assert cred.notes is None

    def test_init_with_all_fields(self) -> None:
        """EmailCredential accepts all optional fields."""
        cred = EmailCredential(
            label="GitHub",
            email="user@example.com",
            password="secret123",
            notes="Work account",
            id="abc12345",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        assert cred.notes == "Work account"
        assert cred.id == "abc12345"
        assert cred.created_at == "2024-01-01T00:00:00"
        assert cred.updated_at == "2024-01-02T00:00:00"

    def test_default_id_is_generated(self) -> None:
        """Default ID is auto-generated."""
        cred = EmailCredential(label="Test", email="a@b.com", password="pw")
        assert len(cred.id) == 8
        assert re.match(r"^[0-9a-f]{8}$", cred.id)

    def test_default_timestamps_are_generated(self) -> None:
        """Default timestamps are auto-generated to current time."""
        before = datetime.now()
        cred = EmailCredential(label="Test", email="a@b.com", password="pw")
        after = datetime.now()

        created = datetime.fromisoformat(cred.created_at)
        updated = datetime.fromisoformat(cred.updated_at)

        assert before <= created <= after
        assert before <= updated <= after

    def test_repr_redacts_password(self) -> None:
        """String representation hides password."""
        cred = EmailCredential(
            label="GitHub",
            email="user@example.com",
            password="SuperSecret123!",
        )
        repr_str = repr(cred)

        assert "SuperSecret123!" not in repr_str
        assert "[REDACTED]" in repr_str
        assert "GitHub" in repr_str
        assert "user@example.com" in repr_str

    def test_to_dict_contains_all_fields(self) -> None:
        """to_dict includes all fields with correct types."""
        cred = EmailCredential(
            label="GitHub",
            email="user@example.com",
            password="secret123",
            notes="Work",
            id="abc12345",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        data = cred.to_dict()

        assert data["type"] == "email"
        assert data["id"] == "abc12345"
        assert data["label"] == "GitHub"
        assert data["email"] == "user@example.com"
        assert data["password"] == "secret123"
        assert data["notes"] == "Work"
        assert data["created_at"] == "2024-01-01T00:00:00"
        assert data["updated_at"] == "2024-01-02T00:00:00"

    def test_to_dict_includes_password_in_cleartext(self) -> None:
        """to_dict includes actual password for storage (not redacted)."""
        cred = EmailCredential(
            label="Test",
            email="a@b.com",
            password="ActualSecret123",
        )
        data = cred.to_dict()
        assert data["password"] == "ActualSecret123"

    def test_from_dict_with_full_data(self) -> None:
        """from_dict reconstructs credential from complete dictionary."""
        data = {
            "type": "email",
            "id": "abc12345",
            "label": "GitHub",
            "email": "user@example.com",
            "password": "secret123",
            "notes": "Work",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }
        cred = EmailCredential.from_dict(data)

        assert cred.id == "abc12345"
        assert cred.label == "GitHub"
        assert cred.email == "user@example.com"
        assert cred.password == "secret123"
        assert cred.notes == "Work"
        assert cred.created_at == "2024-01-01T00:00:00"
        assert cred.updated_at == "2024-01-02T00:00:00"

    def test_from_dict_with_minimal_data(self) -> None:
        """from_dict generates defaults for missing optional fields."""
        data = {
            "label": "GitHub",
            "email": "user@example.com",
            "password": "secret123",
        }
        cred = EmailCredential.from_dict(data)

        assert cred.label == "GitHub"
        assert cred.email == "user@example.com"
        assert cred.password == "secret123"
        assert cred.notes is None
        assert len(cred.id) == 8
        assert cred.created_at is not None
        assert cred.updated_at is not None

    def test_from_dict_missing_required_field_raises_keyerror(self) -> None:
        """from_dict raises KeyError when required fields are missing."""
        with pytest.raises(KeyError):
            EmailCredential.from_dict({"label": "Test", "email": "a@b.com"})

    def test_to_dict_from_dict_roundtrip(self) -> None:
        """Round-trip through to_dict/from_dict preserves all data."""
        original = EmailCredential(
            label="GitHub",
            email="user@example.com",
            password="secret123",
            notes="Work account",
            id="abc12345",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        data = original.to_dict()
        restored = EmailCredential.from_dict(data)

        assert restored.id == original.id
        assert restored.label == original.label
        assert restored.email == original.email
        assert restored.password == original.password
        assert restored.notes == original.notes
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at

    def test_update_modifies_specified_fields(self) -> None:
        """update() changes only the specified fields."""
        cred = EmailCredential(
            label="Old",
            email="old@example.com",
            password="oldpass",
        )
        cred.update(label="New", password="newpass")

        assert cred.label == "New"
        assert cred.email == "old@example.com"  # unchanged
        assert cred.password == "newpass"

    def test_update_refreshes_updated_at(self) -> None:
        """update() refreshes updated_at timestamp."""
        cred = EmailCredential(
            label="Test",
            email="a@b.com",
            password="pw",
            updated_at="2020-01-01T00:00:00",
        )
        old_updated = cred.updated_at

        time.sleep(0.01)  # Ensure timestamp difference
        cred.update(label="New")

        assert cred.updated_at != old_updated
        assert cred.updated_at > old_updated

    def test_update_does_not_modify_id(self) -> None:
        """update() cannot modify ID field."""
        cred = EmailCredential(
            label="Test",
            email="a@b.com",
            password="pw",
            id="original1",
        )
        cred.update(id="attempted")

        assert cred.id == "original1"

    def test_update_does_not_modify_created_at(self) -> None:
        """update() cannot modify created_at field."""
        cred = EmailCredential(
            label="Test",
            email="a@b.com",
            password="pw",
            created_at="2020-01-01T00:00:00",
        )
        cred.update(created_at="2025-12-31T23:59:59")

        assert cred.created_at == "2020-01-01T00:00:00"

    def test_update_ignores_nonexistent_fields(self) -> None:
        """update() ignores kwargs for fields that don't exist."""
        cred = EmailCredential(label="Test", email="a@b.com", password="pw")
        cred.update(nonexistent_field="value")  # Should not raise

        assert (
            not hasattr(cred, "nonexistent_field")
            or cred.__dict__.get("nonexistent_field") != "value"
        )

    def test_equality_by_value(self) -> None:
        """Two credentials with same values are equal (dataclass default)."""
        cred1 = EmailCredential(
            label="Test",
            email="a@b.com",
            password="pw",
            id="same1234",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        cred2 = EmailCredential(
            label="Test",
            email="a@b.com",
            password="pw",
            id="same1234",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert cred1 == cred2

    def test_fields_retain_assigned_values(self) -> None:
        """Fields retain their assigned values without modification."""
        special_chars = "Pass!@#$%^&*()_+-=[]{}|;':\",./<>?"
        unicode_email = "user+tag@example.com"
        cred = EmailCredential(
            label="Test Label",
            email=unicode_email,
            password=special_chars,
            notes="Some notes here",
        )
        assert cred.label == "Test Label"
        assert cred.email == unicode_email
        assert cred.password == special_chars
        assert cred.notes == "Some notes here"


class TestPhoneCredential:
    """Tests for PhoneCredential dataclass."""

    def test_init_with_required_fields(self) -> None:
        """PhoneCredential initializes with required fields."""
        cred = PhoneCredential(
            label="Bank PIN",
            phone="+1-555-123-4567",
            password="1234",
        )
        assert cred.label == "Bank PIN"
        assert cred.phone == "+1-555-123-4567"
        assert cred.password == "1234"
        assert cred.notes is None

    def test_init_with_all_fields(self) -> None:
        """PhoneCredential accepts all optional fields."""
        cred = PhoneCredential(
            label="Bank PIN",
            phone="+1-555-123-4567",
            password="1234",
            notes="Primary account",
            id="def56789",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        assert cred.notes == "Primary account"
        assert cred.id == "def56789"

    def test_default_id_is_generated(self) -> None:
        """Default ID is auto-generated."""
        cred = PhoneCredential(label="Test", phone="555", password="1234")
        assert len(cred.id) == 8

    def test_default_timestamps_are_generated(self) -> None:
        """Default timestamps are auto-generated."""
        cred = PhoneCredential(label="Test", phone="555", password="1234")
        assert cred.created_at is not None
        assert cred.updated_at is not None
        datetime.fromisoformat(cred.created_at)  # Validates format

    def test_repr_redacts_password(self) -> None:
        """String representation hides password."""
        cred = PhoneCredential(
            label="Bank",
            phone="555-1234",
            password="9876",
        )
        repr_str = repr(cred)

        assert "9876" not in repr_str
        assert "[REDACTED]" in repr_str
        assert "Bank" in repr_str
        assert "555-1234" in repr_str

    def test_to_dict_contains_all_fields(self) -> None:
        """to_dict includes all fields with correct types."""
        cred = PhoneCredential(
            label="Bank",
            phone="555-1234",
            password="9876",
            notes="PIN",
            id="abc12345",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        data = cred.to_dict()

        assert data["type"] == "phone"
        assert data["id"] == "abc12345"
        assert data["label"] == "Bank"
        assert data["phone"] == "555-1234"
        assert data["password"] == "9876"
        assert data["notes"] == "PIN"

    def test_from_dict_with_full_data(self) -> None:
        """from_dict reconstructs credential from complete dictionary."""
        data = {
            "type": "phone",
            "id": "def56789",
            "label": "Bank",
            "phone": "555-1234",
            "password": "9876",
            "notes": "PIN",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }
        cred = PhoneCredential.from_dict(data)

        assert cred.id == "def56789"
        assert cred.label == "Bank"
        assert cred.phone == "555-1234"
        assert cred.password == "9876"

    def test_from_dict_with_minimal_data(self) -> None:
        """from_dict generates defaults for missing optional fields."""
        data = {
            "label": "Bank",
            "phone": "555-1234",
            "password": "9876",
        }
        cred = PhoneCredential.from_dict(data)

        assert cred.label == "Bank"
        assert cred.notes is None
        assert len(cred.id) == 8

    def test_from_dict_missing_required_field_raises_keyerror(self) -> None:
        """from_dict raises KeyError when required fields are missing."""
        with pytest.raises(KeyError):
            PhoneCredential.from_dict({"label": "Test", "phone": "555"})

    def test_to_dict_from_dict_roundtrip(self) -> None:
        """Round-trip through to_dict/from_dict preserves all data."""
        original = PhoneCredential(
            label="Bank",
            phone="555-1234",
            password="9876",
            notes="PIN code",
            id="def56789",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        restored = PhoneCredential.from_dict(original.to_dict())

        assert restored.id == original.id
        assert restored.label == original.label
        assert restored.phone == original.phone
        assert restored.password == original.password
        assert restored.notes == original.notes

    def test_update_modifies_specified_fields(self) -> None:
        """update() changes only the specified fields."""
        cred = PhoneCredential(
            label="Old",
            phone="111",
            password="0000",
        )
        cred.update(label="New", password="9999")

        assert cred.label == "New"
        assert cred.phone == "111"  # unchanged
        assert cred.password == "9999"

    def test_update_refreshes_updated_at(self) -> None:
        """update() refreshes updated_at timestamp."""
        cred = PhoneCredential(
            label="Test",
            phone="555",
            password="1234",
            updated_at="2020-01-01T00:00:00",
        )
        old_updated = cred.updated_at
        time.sleep(0.01)
        cred.update(label="New")

        assert cred.updated_at != old_updated

    def test_update_does_not_modify_id(self) -> None:
        """update() cannot modify ID field."""
        cred = PhoneCredential(
            label="Test",
            phone="555",
            password="1234",
            id="original1",
        )
        cred.update(id="attempted")

        assert cred.id == "original1"


class TestCreditCard:
    """Tests for CreditCard dataclass."""

    def test_init_with_required_fields(self) -> None:
        """CreditCard initializes with required fields."""
        card = CreditCard(
            label="Chase Sapphire",
            card_number="4111111111111111",
            expiry="12/25",
            cvv="123",
            cardholder_name="John Doe",
        )
        assert card.label == "Chase Sapphire"
        assert card.card_number == "4111111111111111"
        assert card.expiry == "12/25"
        assert card.cvv == "123"
        assert card.cardholder_name == "John Doe"
        assert card.notes is None

    def test_init_with_all_fields(self) -> None:
        """CreditCard accepts all optional fields."""
        card = CreditCard(
            label="Chase",
            card_number="4111111111111111",
            expiry="12/25",
            cvv="123",
            cardholder_name="John Doe",
            notes="Primary card",
            id="card1234",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        assert card.notes == "Primary card"
        assert card.id == "card1234"

    def test_default_id_is_generated(self) -> None:
        """Default ID is auto-generated."""
        card = CreditCard(
            label="Test",
            card_number="4111",
            expiry="12/25",
            cvv="123",
            cardholder_name="Test",
        )
        assert len(card.id) == 8

    def test_default_timestamps_are_generated(self) -> None:
        """Default timestamps are auto-generated."""
        card = CreditCard(
            label="Test",
            card_number="4111",
            expiry="12/25",
            cvv="123",
            cardholder_name="Test",
        )
        assert card.created_at is not None
        assert card.updated_at is not None

    def test_repr_redacts_card_number_and_cvv(self) -> None:
        """String representation hides card_number and cvv."""
        card = CreditCard(
            label="Chase",
            card_number="4111222233334444",
            expiry="12/25",
            cvv="789",
            cardholder_name="John Doe",
        )
        repr_str = repr(card)

        assert "4111222233334444" not in repr_str
        assert "789" not in repr_str
        assert "[REDACTED]" in repr_str
        assert "Chase" in repr_str
        assert "12/25" in repr_str
        assert "John Doe" in repr_str

    def test_to_dict_contains_all_fields(self) -> None:
        """to_dict includes all fields with correct types."""
        card = CreditCard(
            label="Chase",
            card_number="4111111111111111",
            expiry="12/25",
            cvv="123",
            cardholder_name="John Doe",
            notes="Primary",
            id="card1234",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        data = card.to_dict()

        assert data["type"] == "card"
        assert data["id"] == "card1234"
        assert data["label"] == "Chase"
        assert data["card_number"] == "4111111111111111"
        assert data["expiry"] == "12/25"
        assert data["cvv"] == "123"
        assert data["cardholder_name"] == "John Doe"
        assert data["notes"] == "Primary"

    def test_from_dict_with_full_data(self) -> None:
        """from_dict reconstructs credential from complete dictionary."""
        data = {
            "type": "card",
            "id": "card1234",
            "label": "Chase",
            "card_number": "4111111111111111",
            "expiry": "12/25",
            "cvv": "123",
            "cardholder_name": "John Doe",
            "notes": "Primary",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }
        card = CreditCard.from_dict(data)

        assert card.id == "card1234"
        assert card.label == "Chase"
        assert card.card_number == "4111111111111111"
        assert card.cvv == "123"

    def test_from_dict_with_minimal_data(self) -> None:
        """from_dict generates defaults for missing optional fields."""
        data = {
            "label": "Chase",
            "card_number": "4111111111111111",
            "expiry": "12/25",
            "cvv": "123",
            "cardholder_name": "John Doe",
        }
        card = CreditCard.from_dict(data)

        assert card.label == "Chase"
        assert card.notes is None
        assert len(card.id) == 8

    def test_from_dict_missing_required_field_raises_keyerror(self) -> None:
        """from_dict raises KeyError when required fields are missing."""
        with pytest.raises(KeyError):
            CreditCard.from_dict(
                {
                    "label": "Chase",
                    "card_number": "4111",
                    "expiry": "12/25",
                    "cvv": "123",
                    # missing cardholder_name
                }
            )

    def test_to_dict_from_dict_roundtrip(self) -> None:
        """Round-trip through to_dict/from_dict preserves all data."""
        original = CreditCard(
            label="Chase",
            card_number="4111111111111111",
            expiry="12/25",
            cvv="123",
            cardholder_name="John Doe",
            notes="Primary",
            id="card1234",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        restored = CreditCard.from_dict(original.to_dict())

        assert restored.id == original.id
        assert restored.label == original.label
        assert restored.card_number == original.card_number
        assert restored.cvv == original.cvv

    def test_update_modifies_specified_fields(self) -> None:
        """update() changes only the specified fields."""
        card = CreditCard(
            label="Old",
            card_number="4111",
            expiry="01/20",
            cvv="111",
            cardholder_name="Old Name",
        )
        card.update(label="New", expiry="12/30")

        assert card.label == "New"
        assert card.expiry == "12/30"
        assert card.card_number == "4111"  # unchanged

    def test_update_refreshes_updated_at(self) -> None:
        """update() refreshes updated_at timestamp."""
        card = CreditCard(
            label="Test",
            card_number="4111",
            expiry="12/25",
            cvv="123",
            cardholder_name="Test",
            updated_at="2020-01-01T00:00:00",
        )
        old_updated = card.updated_at
        time.sleep(0.01)
        card.update(label="New")

        assert card.updated_at != old_updated

    def test_update_does_not_modify_id(self) -> None:
        """update() cannot modify ID field."""
        card = CreditCard(
            label="Test",
            card_number="4111",
            expiry="12/25",
            cvv="123",
            cardholder_name="Test",
            id="original1",
        )
        card.update(id="attempted")

        assert card.id == "original1"

    def test_masked_number_shows_last_four_digits(self) -> None:
        """masked_number property shows only last 4 digits."""
        card = CreditCard(
            label="Test",
            card_number="4111222233334444",
            expiry="12/25",
            cvv="123",
            cardholder_name="Test",
        )
        assert card.masked_number == "•••• •••• •••• 4444"

    def test_masked_number_with_spaces_in_card_number(self) -> None:
        """masked_number handles card numbers with spaces."""
        card = CreditCard(
            label="Test",
            card_number="4111 2222 3333 4444",
            expiry="12/25",
            cvv="123",
            cardholder_name="Test",
        )
        assert card.masked_number == "•••• •••• •••• 4444"

    def test_masked_number_with_dashes_in_card_number(self) -> None:
        """masked_number handles card numbers with dashes."""
        card = CreditCard(
            label="Test",
            card_number="4111-2222-3333-4444",
            expiry="12/25",
            cvv="123",
            cardholder_name="Test",
        )
        assert card.masked_number == "•••• •••• •••• 4444"

    def test_masked_number_short_card_number(self) -> None:
        """masked_number handles card numbers shorter than 4 digits."""
        card = CreditCard(
            label="Test",
            card_number="123",
            expiry="12/25",
            cvv="123",
            cardholder_name="Test",
        )
        assert card.masked_number == "•••"

    def test_masked_number_exactly_four_digits(self) -> None:
        """masked_number handles exactly 4 digit card numbers."""
        card = CreditCard(
            label="Test",
            card_number="1234",
            expiry="12/25",
            cvv="123",
            cardholder_name="Test",
        )
        assert card.masked_number == "•••• •••• •••• 1234"


class TestEnvEntry:
    """Tests for EnvEntry dataclass."""

    def test_init_with_required_fields(self) -> None:
        """EnvEntry initializes with required fields."""
        entry = EnvEntry(
            title="Production",
            filename=".env.production",
            content="API_KEY=secret\nDB_URL=postgres://",
        )
        assert entry.title == "Production"
        assert entry.filename == ".env.production"
        assert entry.content == "API_KEY=secret\nDB_URL=postgres://"
        assert entry.notes is None

    def test_init_with_all_fields(self) -> None:
        """EnvEntry accepts all optional fields."""
        entry = EnvEntry(
            title="Production",
            filename=".env.production",
            content="API_KEY=secret",
            notes="Production env",
            id="env12345",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        assert entry.notes == "Production env"
        assert entry.id == "env12345"

    def test_default_id_is_generated(self) -> None:
        """Default ID is auto-generated."""
        entry = EnvEntry(title="Test", filename=".env", content="X=Y")
        assert len(entry.id) == 8

    def test_default_timestamps_are_generated(self) -> None:
        """Default timestamps are auto-generated."""
        entry = EnvEntry(title="Test", filename=".env", content="X=Y")
        assert entry.created_at is not None
        assert entry.updated_at is not None

    def test_repr_redacts_content(self) -> None:
        """String representation hides content."""
        entry = EnvEntry(
            title="Production",
            filename=".env.prod",
            content="SECRET_KEY=super_secret_value",
        )
        repr_str = repr(entry)

        assert "super_secret_value" not in repr_str
        assert "[REDACTED]" in repr_str
        assert "Production" in repr_str
        assert ".env.prod" in repr_str

    def test_to_dict_contains_all_fields(self) -> None:
        """to_dict includes all fields with correct types."""
        entry = EnvEntry(
            title="Production",
            filename=".env.production",
            content="API_KEY=secret",
            notes="Prod env",
            id="env12345",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        data = entry.to_dict()

        assert data["type"] == "env"
        assert data["id"] == "env12345"
        assert data["title"] == "Production"
        assert data["filename"] == ".env.production"
        assert data["content"] == "API_KEY=secret"
        assert data["notes"] == "Prod env"

    def test_from_dict_with_full_data(self) -> None:
        """from_dict reconstructs credential from complete dictionary."""
        data = {
            "type": "env",
            "id": "env12345",
            "title": "Production",
            "filename": ".env.production",
            "content": "API_KEY=secret",
            "notes": "Prod env",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }
        entry = EnvEntry.from_dict(data)

        assert entry.id == "env12345"
        assert entry.title == "Production"
        assert entry.content == "API_KEY=secret"

    def test_from_dict_with_minimal_data(self) -> None:
        """from_dict generates defaults for missing optional fields."""
        data = {
            "title": "Production",
            "filename": ".env.production",
            "content": "API_KEY=secret",
        }
        entry = EnvEntry.from_dict(data)

        assert entry.title == "Production"
        assert entry.notes is None
        assert len(entry.id) == 8

    def test_from_dict_missing_required_field_raises_keyerror(self) -> None:
        """from_dict raises KeyError when required fields are missing."""
        with pytest.raises(KeyError):
            EnvEntry.from_dict({"title": "Test", "filename": ".env"})

    def test_to_dict_from_dict_roundtrip(self) -> None:
        """Round-trip through to_dict/from_dict preserves all data."""
        original = EnvEntry(
            title="Production",
            filename=".env.production",
            content="API_KEY=secret\nDB_URL=postgres://",
            notes="Prod env",
            id="env12345",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        restored = EnvEntry.from_dict(original.to_dict())

        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.content == original.content

    def test_update_modifies_specified_fields(self) -> None:
        """update() changes only the specified fields."""
        entry = EnvEntry(
            title="Old",
            filename=".env.old",
            content="OLD=value",
        )
        entry.update(title="New", content="NEW=value")

        assert entry.title == "New"
        assert entry.filename == ".env.old"  # unchanged
        assert entry.content == "NEW=value"

    def test_update_refreshes_updated_at(self) -> None:
        """update() refreshes updated_at timestamp."""
        entry = EnvEntry(
            title="Test",
            filename=".env",
            content="X=Y",
            updated_at="2020-01-01T00:00:00",
        )
        old_updated = entry.updated_at
        time.sleep(0.01)
        entry.update(title="New")

        assert entry.updated_at != old_updated

    def test_update_does_not_modify_id(self) -> None:
        """update() cannot modify ID field."""
        entry = EnvEntry(
            title="Test",
            filename=".env",
            content="X=Y",
            id="original1",
        )
        entry.update(id="attempted")

        assert entry.id == "original1"

    def test_line_count_empty_content(self) -> None:
        """line_count returns 0 for empty content."""
        entry = EnvEntry(title="Test", filename=".env", content="")
        assert entry.line_count == 0

    def test_line_count_single_line(self) -> None:
        """line_count returns 1 for single line content."""
        entry = EnvEntry(title="Test", filename=".env", content="API_KEY=secret")
        assert entry.line_count == 1

    def test_line_count_multiple_lines(self) -> None:
        """line_count returns correct count for multi-line content."""
        entry = EnvEntry(
            title="Test",
            filename=".env",
            content="API_KEY=secret\nDB_URL=postgres://\nDEBUG=true",
        )
        assert entry.line_count == 3

    def test_var_count_empty_content(self) -> None:
        """var_count returns 0 for empty content."""
        entry = EnvEntry(title="Test", filename=".env", content="")
        assert entry.var_count == 0

    def test_var_count_single_variable(self) -> None:
        """var_count returns 1 for single variable."""
        entry = EnvEntry(title="Test", filename=".env", content="API_KEY=secret")
        assert entry.var_count == 1

    def test_var_count_multiple_variables(self) -> None:
        """var_count returns correct count for multiple variables."""
        entry = EnvEntry(
            title="Test",
            filename=".env",
            content="API_KEY=secret\nDB_URL=postgres://\nDEBUG=true",
        )
        assert entry.var_count == 3

    def test_var_count_ignores_comments(self) -> None:
        """var_count ignores comment lines."""
        entry = EnvEntry(
            title="Test",
            filename=".env",
            content="# This is a comment\nAPI_KEY=secret\n# Another comment",
        )
        assert entry.var_count == 1

    def test_var_count_ignores_empty_lines(self) -> None:
        """var_count ignores empty lines."""
        entry = EnvEntry(
            title="Test",
            filename=".env",
            content="API_KEY=secret\n\n\nDB_URL=postgres://",
        )
        assert entry.var_count == 2

    def test_var_count_ignores_lines_without_equals(self) -> None:
        """var_count ignores lines without '=' sign."""
        entry = EnvEntry(
            title="Test",
            filename=".env",
            content="API_KEY=secret\nNOT_A_VARIABLE\nDB_URL=postgres://",
        )
        assert entry.var_count == 2


class TestRecoveryEntry:
    """Tests for RecoveryEntry dataclass."""

    def test_init_with_required_fields(self) -> None:
        """RecoveryEntry initializes with required fields."""
        entry = RecoveryEntry(
            title="GitHub 2FA",
            content="abc123\ndef456\nghi789",
        )
        assert entry.title == "GitHub 2FA"
        assert entry.content == "abc123\ndef456\nghi789"
        assert entry.notes is None

    def test_init_with_all_fields(self) -> None:
        """RecoveryEntry accepts all optional fields."""
        entry = RecoveryEntry(
            title="GitHub 2FA",
            content="abc123\ndef456",
            notes="Backup codes",
            id="rec12345",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        assert entry.notes == "Backup codes"
        assert entry.id == "rec12345"

    def test_default_id_is_generated(self) -> None:
        """Default ID is auto-generated."""
        entry = RecoveryEntry(title="Test", content="codes")
        assert len(entry.id) == 8

    def test_default_timestamps_are_generated(self) -> None:
        """Default timestamps are auto-generated."""
        entry = RecoveryEntry(title="Test", content="codes")
        assert entry.created_at is not None
        assert entry.updated_at is not None

    def test_repr_redacts_content(self) -> None:
        """String representation hides content."""
        entry = RecoveryEntry(
            title="GitHub 2FA",
            content="secret_recovery_code_12345",
        )
        repr_str = repr(entry)

        assert "secret_recovery_code_12345" not in repr_str
        assert "[REDACTED]" in repr_str
        assert "GitHub 2FA" in repr_str

    def test_to_dict_contains_all_fields(self) -> None:
        """to_dict includes all fields with correct types."""
        entry = RecoveryEntry(
            title="GitHub 2FA",
            content="abc123\ndef456",
            notes="Backup codes",
            id="rec12345",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        data = entry.to_dict()

        assert data["type"] == "recovery"
        assert data["id"] == "rec12345"
        assert data["title"] == "GitHub 2FA"
        assert data["content"] == "abc123\ndef456"
        assert data["notes"] == "Backup codes"

    def test_from_dict_with_full_data(self) -> None:
        """from_dict reconstructs credential from complete dictionary."""
        data = {
            "type": "recovery",
            "id": "rec12345",
            "title": "GitHub 2FA",
            "content": "abc123\ndef456",
            "notes": "Backup codes",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }
        entry = RecoveryEntry.from_dict(data)

        assert entry.id == "rec12345"
        assert entry.title == "GitHub 2FA"
        assert entry.content == "abc123\ndef456"

    def test_from_dict_with_minimal_data(self) -> None:
        """from_dict generates defaults for missing optional fields."""
        data = {
            "title": "GitHub 2FA",
            "content": "abc123",
        }
        entry = RecoveryEntry.from_dict(data)

        assert entry.title == "GitHub 2FA"
        assert entry.notes is None
        assert len(entry.id) == 8

    def test_from_dict_missing_required_field_raises_keyerror(self) -> None:
        """from_dict raises KeyError when required fields are missing."""
        with pytest.raises(KeyError):
            RecoveryEntry.from_dict({"title": "Test"})

    def test_to_dict_from_dict_roundtrip(self) -> None:
        """Round-trip through to_dict/from_dict preserves all data."""
        original = RecoveryEntry(
            title="GitHub 2FA",
            content="abc123\ndef456\nghi789",
            notes="Backup codes",
            id="rec12345",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        restored = RecoveryEntry.from_dict(original.to_dict())

        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.content == original.content

    def test_update_modifies_specified_fields(self) -> None:
        """update() changes only the specified fields."""
        entry = RecoveryEntry(
            title="Old",
            content="old_codes",
        )
        entry.update(title="New", content="new_codes")

        assert entry.title == "New"
        assert entry.content == "new_codes"

    def test_update_refreshes_updated_at(self) -> None:
        """update() refreshes updated_at timestamp."""
        entry = RecoveryEntry(
            title="Test",
            content="codes",
            updated_at="2020-01-01T00:00:00",
        )
        old_updated = entry.updated_at
        time.sleep(0.01)
        entry.update(title="New")

        assert entry.updated_at != old_updated

    def test_update_does_not_modify_id(self) -> None:
        """update() cannot modify ID field."""
        entry = RecoveryEntry(
            title="Test",
            content="codes",
            id="original1",
        )
        entry.update(id="attempted")

        assert entry.id == "original1"

    def test_line_count_empty_content(self) -> None:
        """line_count returns 0 for empty content."""
        entry = RecoveryEntry(title="Test", content="")
        assert entry.line_count == 0

    def test_line_count_single_line(self) -> None:
        """line_count returns 1 for single line content."""
        entry = RecoveryEntry(title="Test", content="abc123")
        assert entry.line_count == 1

    def test_line_count_multiple_lines(self) -> None:
        """line_count returns correct count for multi-line content."""
        entry = RecoveryEntry(
            title="Test",
            content="abc123\ndef456\nghi789",
        )
        assert entry.line_count == 3

    def test_code_count_empty_content(self) -> None:
        """code_count returns 0 for empty content."""
        entry = RecoveryEntry(title="Test", content="")
        assert entry.code_count == 0

    def test_code_count_single_code(self) -> None:
        """code_count returns 1 for single code."""
        entry = RecoveryEntry(title="Test", content="abc123")
        assert entry.code_count == 1

    def test_code_count_multiple_codes(self) -> None:
        """code_count returns correct count for multiple codes."""
        entry = RecoveryEntry(
            title="Test",
            content="abc123\ndef456\nghi789",
        )
        assert entry.code_count == 3

    def test_code_count_ignores_hash_comments(self) -> None:
        """code_count ignores # comment lines."""
        entry = RecoveryEntry(
            title="Test",
            content="# Header comment\nabc123\n# Another comment\ndef456",
        )
        assert entry.code_count == 2

    def test_code_count_ignores_slash_comments(self) -> None:
        """code_count ignores // comment lines."""
        entry = RecoveryEntry(
            title="Test",
            content="// Header comment\nabc123\n// Another comment\ndef456",
        )
        assert entry.code_count == 2

    def test_code_count_ignores_empty_lines(self) -> None:
        """code_count ignores empty lines."""
        entry = RecoveryEntry(
            title="Test",
            content="abc123\n\n\ndef456",
        )
        assert entry.code_count == 2


class TestNoteEntry:
    """Tests for NoteEntry dataclass."""

    def test_init_with_required_fields(self) -> None:
        """NoteEntry initializes with required fields."""
        entry = NoteEntry(
            title="Office Wi-Fi",
            content="Password: SecretWiFi123",
        )
        assert entry.title == "Office Wi-Fi"
        assert entry.content == "Password: SecretWiFi123"
        assert entry.notes is None

    def test_init_with_all_fields(self) -> None:
        """NoteEntry accepts all optional fields."""
        entry = NoteEntry(
            title="Office Wi-Fi",
            content="Password: SecretWiFi123",
            notes="Additional notes",
            id="note1234",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        assert entry.notes == "Additional notes"
        assert entry.id == "note1234"

    def test_default_id_is_generated(self) -> None:
        """Default ID is auto-generated."""
        entry = NoteEntry(title="Test", content="content")
        assert len(entry.id) == 8

    def test_default_timestamps_are_generated(self) -> None:
        """Default timestamps are auto-generated."""
        entry = NoteEntry(title="Test", content="content")
        assert entry.created_at is not None
        assert entry.updated_at is not None

    def test_repr_redacts_content(self) -> None:
        """String representation hides content."""
        entry = NoteEntry(
            title="Wi-Fi",
            content="super_secret_password_123",
        )
        repr_str = repr(entry)

        assert "super_secret_password_123" not in repr_str
        assert "[REDACTED]" in repr_str
        assert "Wi-Fi" in repr_str

    def test_to_dict_contains_all_fields(self) -> None:
        """to_dict includes all fields with correct types."""
        entry = NoteEntry(
            title="Wi-Fi",
            content="Password: secret",
            notes="Office",
            id="note1234",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        data = entry.to_dict()

        assert data["type"] == "note"
        assert data["id"] == "note1234"
        assert data["title"] == "Wi-Fi"
        assert data["content"] == "Password: secret"
        assert data["notes"] == "Office"

    def test_from_dict_with_full_data(self) -> None:
        """from_dict reconstructs credential from complete dictionary."""
        data = {
            "type": "note",
            "id": "note1234",
            "title": "Wi-Fi",
            "content": "Password: secret",
            "notes": "Office",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }
        entry = NoteEntry.from_dict(data)

        assert entry.id == "note1234"
        assert entry.title == "Wi-Fi"
        assert entry.content == "Password: secret"

    def test_from_dict_with_minimal_data(self) -> None:
        """from_dict generates defaults for missing optional fields."""
        data = {
            "title": "Wi-Fi",
            "content": "Password: secret",
        }
        entry = NoteEntry.from_dict(data)

        assert entry.title == "Wi-Fi"
        assert entry.notes is None
        assert len(entry.id) == 8

    def test_from_dict_missing_required_field_raises_keyerror(self) -> None:
        """from_dict raises KeyError when required fields are missing."""
        with pytest.raises(KeyError):
            NoteEntry.from_dict({"title": "Test"})

    def test_to_dict_from_dict_roundtrip(self) -> None:
        """Round-trip through to_dict/from_dict preserves all data."""
        original = NoteEntry(
            title="Wi-Fi",
            content="Password: secret\nSSID: network",
            notes="Office network",
            id="note1234",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        restored = NoteEntry.from_dict(original.to_dict())

        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.content == original.content

    def test_update_modifies_specified_fields(self) -> None:
        """update() changes only the specified fields."""
        entry = NoteEntry(
            title="Old",
            content="old content",
        )
        entry.update(title="New", content="new content")

        assert entry.title == "New"
        assert entry.content == "new content"

    def test_update_refreshes_updated_at(self) -> None:
        """update() refreshes updated_at timestamp."""
        entry = NoteEntry(
            title="Test",
            content="content",
            updated_at="2020-01-01T00:00:00",
        )
        old_updated = entry.updated_at
        time.sleep(0.01)
        entry.update(title="New")

        assert entry.updated_at != old_updated

    def test_update_does_not_modify_id(self) -> None:
        """update() cannot modify ID field."""
        entry = NoteEntry(
            title="Test",
            content="content",
            id="original1",
        )
        entry.update(id="attempted")

        assert entry.id == "original1"

    def test_line_count_empty_content(self) -> None:
        """line_count returns 0 for empty content."""
        entry = NoteEntry(title="Test", content="")
        assert entry.line_count == 0

    def test_line_count_single_line(self) -> None:
        """line_count returns 1 for single line content."""
        entry = NoteEntry(title="Test", content="Single line note")
        assert entry.line_count == 1

    def test_line_count_multiple_lines(self) -> None:
        """line_count returns correct count for multi-line content."""
        entry = NoteEntry(
            title="Test",
            content="Line 1\nLine 2\nLine 3",
        )
        assert entry.line_count == 3

    def test_char_count_empty_content(self) -> None:
        """char_count returns 0 for empty content."""
        entry = NoteEntry(title="Test", content="")
        assert entry.char_count == 0

    def test_char_count_non_empty_content(self) -> None:
        """char_count returns correct character count."""
        entry = NoteEntry(title="Test", content="Hello World")
        assert entry.char_count == 11

    def test_char_count_with_newlines(self) -> None:
        """char_count includes newline characters."""
        entry = NoteEntry(title="Test", content="Line1\nLine2")
        assert entry.char_count == 11  # 5 + 1 + 5


class TestCredentialFromDict:
    """Tests for credential_from_dict factory function."""

    def test_creates_email_credential(self) -> None:
        """Factory creates EmailCredential for type 'email'."""
        data = {
            "type": "email",
            "label": "GitHub",
            "email": "user@example.com",
            "password": "secret",
        }
        cred = credential_from_dict(data)

        assert isinstance(cred, EmailCredential)
        assert cred.label == "GitHub"
        assert cred.email == "user@example.com"

    def test_creates_phone_credential(self) -> None:
        """Factory creates PhoneCredential for type 'phone'."""
        data = {
            "type": "phone",
            "label": "Bank",
            "phone": "555-1234",
            "password": "1234",
        }
        cred = credential_from_dict(data)

        assert isinstance(cred, PhoneCredential)
        assert cred.label == "Bank"
        assert cred.phone == "555-1234"

    def test_creates_credit_card(self) -> None:
        """Factory creates CreditCard for type 'card'."""
        data = {
            "type": "card",
            "label": "Chase",
            "card_number": "4111111111111111",
            "expiry": "12/25",
            "cvv": "123",
            "cardholder_name": "John Doe",
        }
        cred = credential_from_dict(data)

        assert isinstance(cred, CreditCard)
        assert cred.label == "Chase"
        assert cred.card_number == "4111111111111111"

    def test_creates_env_entry(self) -> None:
        """Factory creates EnvEntry for type 'env'."""
        data = {
            "type": "env",
            "title": "Production",
            "filename": ".env.prod",
            "content": "API_KEY=secret",
        }
        cred = credential_from_dict(data)

        assert isinstance(cred, EnvEntry)
        assert cred.title == "Production"
        assert cred.filename == ".env.prod"

    def test_creates_recovery_entry(self) -> None:
        """Factory creates RecoveryEntry for type 'recovery'."""
        data = {
            "type": "recovery",
            "title": "GitHub 2FA",
            "content": "abc123\ndef456",
        }
        cred = credential_from_dict(data)

        assert isinstance(cred, RecoveryEntry)
        assert cred.title == "GitHub 2FA"

    def test_creates_note_entry(self) -> None:
        """Factory creates NoteEntry for type 'note'."""
        data = {
            "type": "note",
            "title": "Wi-Fi",
            "content": "Password: secret",
        }
        cred = credential_from_dict(data)

        assert isinstance(cred, NoteEntry)
        assert cred.title == "Wi-Fi"

    def test_defaults_to_email_when_type_missing(self) -> None:
        """Factory defaults to EmailCredential when type is not specified."""
        data = {
            "label": "GitHub",
            "email": "user@example.com",
            "password": "secret",
        }
        cred = credential_from_dict(data)

        assert isinstance(cred, EmailCredential)

    def test_raises_value_error_for_unknown_type(self) -> None:
        """Factory raises ValueError for unrecognized type."""
        data = {
            "type": "unknown_type",
            "label": "Test",
        }
        with pytest.raises(ValueError, match="Unknown credential type: unknown_type"):
            credential_from_dict(data)

    def test_preserves_all_fields_through_factory(self) -> None:
        """Factory preserves all fields including timestamps and ID."""
        data = {
            "type": "email",
            "id": "abc12345",
            "label": "GitHub",
            "email": "user@example.com",
            "password": "secret",
            "notes": "Work",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
        }
        cred = credential_from_dict(data)

        assert cred.id == "abc12345"
        assert cred.notes == "Work"
        assert cred.created_at == "2024-01-01T00:00:00"
        assert cred.updated_at == "2024-01-02T00:00:00"


class TestDataIntegrity:
    """Tests for data integrity across all models."""

    def test_special_characters_preserved(self) -> None:
        """Special characters in fields are preserved through serialization."""
        special = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        cred = EmailCredential(
            label=special,
            email="test@example.com",
            password=special,
            notes=special,
        )
        restored = EmailCredential.from_dict(cred.to_dict())

        assert restored.label == special
        assert restored.password == special
        assert restored.notes == special

    def test_unicode_characters_preserved(self) -> None:
        """Unicode characters are preserved through serialization."""
        unicode_str = "Password: Crème brûlée"
        cred = NoteEntry(
            title=unicode_str,
            content=unicode_str,
            notes=unicode_str,
        )
        restored = NoteEntry.from_dict(cred.to_dict())

        assert restored.title == unicode_str
        assert restored.content == unicode_str
        assert restored.notes == unicode_str

    def test_empty_strings_preserved(self) -> None:
        """Empty strings are preserved (not converted to None)."""
        cred = EmailCredential(
            label="",
            email="",
            password="",
        )
        restored = EmailCredential.from_dict(cred.to_dict())

        assert restored.label == ""
        assert restored.email == ""
        assert restored.password == ""

    def test_multiline_content_preserved(self) -> None:
        """Multiline content is preserved through serialization."""
        multiline = "Line 1\nLine 2\nLine 3\n\nLine 5"
        entry = EnvEntry(
            title="Test",
            filename=".env",
            content=multiline,
        )
        restored = EnvEntry.from_dict(entry.to_dict())

        assert restored.content == multiline

    def test_whitespace_preserved(self) -> None:
        """Leading/trailing whitespace is preserved."""
        content = "  spaces before and after  "
        entry = NoteEntry(
            title="Test",
            content=content,
        )
        restored = NoteEntry.from_dict(entry.to_dict())

        assert restored.content == content

    def test_none_notes_serialization(self) -> None:
        """None notes field serializes correctly."""
        cred = EmailCredential(
            label="Test",
            email="a@b.com",
            password="pw",
            notes=None,
        )
        data = cred.to_dict()

        assert data["notes"] is None
        restored = EmailCredential.from_dict(data)
        assert restored.notes is None
