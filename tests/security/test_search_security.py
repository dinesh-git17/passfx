"""Security tests for PassFX global search system.

Validates that the search infrastructure never indexes, exposes, or displays
sensitive credential data (passwords, PINs, CVVs, card numbers, secret content).

These tests act as security contracts - any regression indicates a potential
information disclosure vulnerability.
"""

from __future__ import annotations

import pytest

from passfx.core.models import (
    CreditCard,
    EmailCredential,
    EnvEntry,
    NoteEntry,
    PhoneCredential,
    RecoveryEntry,
)
from passfx.search.config import SEARCHABLE_FIELDS
from passfx.search.engine import (
    SearchIndex,
    _card_field_getter,
    _email_field_getter,
    _env_field_getter,
    _note_field_getter,
    _phone_field_getter,
    _recovery_field_getter,
)

# =============================================================================
# CREDENTIAL FIXTURES
# =============================================================================


@pytest.fixture
def email_cred() -> EmailCredential:
    """Email credential with identifiable secret."""
    return EmailCredential(
        label="GitHub Account",
        email="user@example.com",
        password="SuperSecretPassword123!",
        notes="Work account",
    )


@pytest.fixture
def phone_cred() -> PhoneCredential:
    """Phone credential with identifiable PIN."""
    return PhoneCredential(
        label="Bank Phone PIN",
        phone="+1-555-123-4567",
        password="9876",
        notes="Main bank",
    )


@pytest.fixture
def card_cred() -> CreditCard:
    """Credit card with identifiable sensitive data."""
    return CreditCard(
        label="Chase Sapphire",
        card_number="4532015112830366",
        expiry="12/25",
        cvv="789",
        cardholder_name="John Doe",
        notes="Primary card",
    )


@pytest.fixture
def env_cred() -> EnvEntry:
    """Environment entry with identifiable secret content."""
    return EnvEntry(
        title="Production Config",
        filename=".env.production",
        content="DATABASE_URL=postgresql://user:secretpass@db:5432/app\nAPI_KEY=sk_live_supersecret",
        notes="Prod secrets",
    )


@pytest.fixture
def recovery_cred() -> RecoveryEntry:
    """Recovery codes with identifiable secret content."""
    return RecoveryEntry(
        title="GitHub 2FA",
        content="ABCD-1234-EFGH\nIJKL-5678-MNOP\nQRST-9012-UVWX",
        notes="Backup codes",
    )


@pytest.fixture
def note_cred() -> NoteEntry:
    """Secure note with identifiable secret content."""
    return NoteEntry(
        title="Wi-Fi Credentials",
        content="SSID: OfficeNet\nPassword: WiFiSecret2024!",
        notes="Office access",
    )


@pytest.fixture
def search_index(
    email_cred: EmailCredential,
    phone_cred: PhoneCredential,
    card_cred: CreditCard,
    env_cred: EnvEntry,
    recovery_cred: RecoveryEntry,
    note_cred: NoteEntry,
) -> SearchIndex:
    """Fully populated search index."""
    index = SearchIndex()
    index.build_index(
        emails=[email_cred],
        phones=[phone_cred],
        cards=[card_cred],
        envs=[env_cred],
        recovery=[recovery_cred],
        notes=[note_cred],
    )
    return index


# =============================================================================
# SECTION 1: FIELD GETTER WHITELIST TESTS
# Verify that field getters return None for sensitive fields, preventing
# accidental exposure through search indexing.
# =============================================================================


@pytest.mark.security
class TestEmailFieldGetterWhitelist:
    """Verify email credential field getter blocks sensitive fields."""

    def test_email_field_getter_label(self, email_cred: EmailCredential) -> None:
        """Label is whitelisted and should return value."""
        result = _email_field_getter(email_cred, "label")
        assert result == "GitHub Account"

    def test_email_field_getter_email(self, email_cred: EmailCredential) -> None:
        """Email is whitelisted and should return value."""
        result = _email_field_getter(email_cred, "email")
        assert result == "user@example.com"

    def test_email_field_getter_notes(self, email_cred: EmailCredential) -> None:
        """Notes is whitelisted and should return value."""
        result = _email_field_getter(email_cred, "notes")
        assert result == "Work account"

    def test_email_field_getter_password(self, email_cred: EmailCredential) -> None:
        """Password is NOT whitelisted and MUST return None."""
        result = _email_field_getter(email_cred, "password")
        assert result is None, "Password field must return None from getter"

    def test_email_field_getter_unknown_field(
        self, email_cred: EmailCredential
    ) -> None:
        """Unknown fields must return None."""
        result = _email_field_getter(email_cred, "secret_field")
        assert result is None


@pytest.mark.security
class TestPhoneFieldGetterWhitelist:
    """Verify phone credential field getter blocks sensitive fields."""

    def test_phone_field_getter_label(self, phone_cred: PhoneCredential) -> None:
        """Label is whitelisted and should return value."""
        result = _phone_field_getter(phone_cred, "label")
        assert result == "Bank Phone PIN"

    def test_phone_field_getter_phone(self, phone_cred: PhoneCredential) -> None:
        """Phone is whitelisted and should return value."""
        result = _phone_field_getter(phone_cred, "phone")
        assert result == "+1-555-123-4567"

    def test_phone_field_getter_notes(self, phone_cred: PhoneCredential) -> None:
        """Notes is whitelisted and should return value."""
        result = _phone_field_getter(phone_cred, "notes")
        assert result == "Main bank"

    def test_phone_field_getter_password(self, phone_cred: PhoneCredential) -> None:
        """Password (PIN) is NOT whitelisted and MUST return None."""
        result = _phone_field_getter(phone_cred, "password")
        assert result is None, "Password/PIN field must return None from getter"


@pytest.mark.security
class TestCardFieldGetterWhitelist:
    """Verify credit card field getter blocks sensitive fields."""

    def test_card_field_getter_label(self, card_cred: CreditCard) -> None:
        """Label is whitelisted and should return value."""
        result = _card_field_getter(card_cred, "label")
        assert result == "Chase Sapphire"

    def test_card_field_getter_cardholder_name(self, card_cred: CreditCard) -> None:
        """Cardholder name is whitelisted and should return value."""
        result = _card_field_getter(card_cred, "cardholder_name")
        assert result == "John Doe"

    def test_card_field_getter_notes(self, card_cred: CreditCard) -> None:
        """Notes is whitelisted and should return value."""
        result = _card_field_getter(card_cred, "notes")
        assert result == "Primary card"

    def test_card_field_getter_cvv(self, card_cred: CreditCard) -> None:
        """CVV is NOT whitelisted and MUST return None."""
        result = _card_field_getter(card_cred, "cvv")
        assert result is None, "CVV field must return None from getter"

    def test_card_field_getter_number(self, card_cred: CreditCard) -> None:
        """Card number is NOT whitelisted and MUST return None."""
        result = _card_field_getter(card_cred, "card_number")
        assert result is None, "Card number field must return None from getter"

    def test_card_field_getter_expiry(self, card_cred: CreditCard) -> None:
        """Expiry is NOT whitelisted (not in config) and should return None."""
        result = _card_field_getter(card_cred, "expiry")
        assert result is None


@pytest.mark.security
class TestEnvFieldGetterWhitelist:
    """Verify env entry field getter blocks sensitive content."""

    def test_env_field_getter_title(self, env_cred: EnvEntry) -> None:
        """Title is whitelisted and should return value."""
        result = _env_field_getter(env_cred, "title")
        assert result == "Production Config"

    def test_env_field_getter_filename(self, env_cred: EnvEntry) -> None:
        """Filename is whitelisted and should return value."""
        result = _env_field_getter(env_cred, "filename")
        assert result == ".env.production"

    def test_env_field_getter_notes(self, env_cred: EnvEntry) -> None:
        """Notes is whitelisted and should return value."""
        result = _env_field_getter(env_cred, "notes")
        assert result == "Prod secrets"

    def test_env_field_getter_content(self, env_cred: EnvEntry) -> None:
        """Content is NOT whitelisted and MUST return None."""
        result = _env_field_getter(env_cred, "content")
        assert result is None, "Env content field must return None from getter"


@pytest.mark.security
class TestRecoveryFieldGetterWhitelist:
    """Verify recovery entry field getter blocks sensitive content."""

    def test_recovery_field_getter_title(self, recovery_cred: RecoveryEntry) -> None:
        """Title is whitelisted and should return value."""
        result = _recovery_field_getter(recovery_cred, "title")
        assert result == "GitHub 2FA"

    def test_recovery_field_getter_notes(self, recovery_cred: RecoveryEntry) -> None:
        """Notes is whitelisted and should return value."""
        result = _recovery_field_getter(recovery_cred, "notes")
        assert result == "Backup codes"

    def test_recovery_field_getter_content(self, recovery_cred: RecoveryEntry) -> None:
        """Content (recovery codes) is NOT whitelisted and MUST return None."""
        result = _recovery_field_getter(recovery_cred, "content")
        assert result is None, "Recovery content field must return None from getter"


@pytest.mark.security
class TestNoteFieldGetterWhitelist:
    """Verify note entry field getter blocks sensitive content."""

    def test_note_field_getter_title(self, note_cred: NoteEntry) -> None:
        """Title is whitelisted and should return value."""
        result = _note_field_getter(note_cred, "title")
        assert result == "Wi-Fi Credentials"

    def test_note_field_getter_notes(self, note_cred: NoteEntry) -> None:
        """Notes is whitelisted and should return value."""
        result = _note_field_getter(note_cred, "notes")
        assert result == "Office access"

    def test_note_field_getter_content(self, note_cred: NoteEntry) -> None:
        """Content is NOT whitelisted and MUST return None."""
        result = _note_field_getter(note_cred, "content")
        assert result is None, "Note content field must return None from getter"


# =============================================================================
# SECTION 2: INDEX CONTENT TESTS
# Verify that sensitive data never appears in the search index, even when
# the user searches for terms that would match secret content.
# =============================================================================


@pytest.mark.security
class TestPasswordNotIndexed:
    """Verify passwords are never indexed or searchable."""

    def test_password_not_indexed(
        self, search_index: SearchIndex, email_cred: EmailCredential
    ) -> None:
        """Searching for password value must return empty results."""
        # The password is "SuperSecretPassword123!"
        results = search_index.search("SuperSecretPassword")
        assert len(results) == 0, "Password values must not be searchable"

    def test_partial_password_not_indexed(
        self, search_index: SearchIndex, email_cred: EmailCredential
    ) -> None:
        """Partial password matches must not return results."""
        results = search_index.search("SecretPassword")
        assert len(results) == 0, "Partial password values must not be searchable"

    def test_phone_pin_not_indexed(
        self, search_index: SearchIndex, phone_cred: PhoneCredential
    ) -> None:
        """Phone PIN must not be searchable."""
        # The PIN is "9876"
        results = search_index.search("9876")
        assert len(results) == 0, "Phone PIN must not be searchable"


@pytest.mark.security
class TestCVVNotIndexed:
    """Verify CVV codes are never indexed or searchable."""

    def test_cvv_not_indexed(
        self, search_index: SearchIndex, card_cred: CreditCard
    ) -> None:
        """Searching for CVV value must return empty results."""
        # The CVV is "789"
        results = search_index.search("789")
        assert len(results) == 0, "CVV values must not be searchable"


@pytest.mark.security
class TestCardNumberNotIndexed:
    """Verify card numbers are never indexed or searchable."""

    def test_card_number_not_indexed(
        self, search_index: SearchIndex, card_cred: CreditCard
    ) -> None:
        """Searching for card number must return empty results."""
        # The card number is "4532015112830366"
        results = search_index.search("4532015112830366")
        assert len(results) == 0, "Card numbers must not be searchable"

    def test_partial_card_number_not_indexed(
        self, search_index: SearchIndex, card_cred: CreditCard
    ) -> None:
        """Partial card number matches must not return results."""
        # Search for last 4 digits
        results = search_index.search("0366")
        assert len(results) == 0, "Partial card numbers must not be searchable"

    def test_card_number_prefix_not_indexed(
        self, search_index: SearchIndex, card_cred: CreditCard
    ) -> None:
        """Card number prefix (BIN) must not be searchable."""
        # Search for first 6 digits (BIN)
        results = search_index.search("453201")
        assert len(results) == 0, "Card BIN must not be searchable"


@pytest.mark.security
class TestEnvContentNotIndexed:
    """Verify environment variable content is never indexed."""

    def test_env_content_not_indexed(
        self, search_index: SearchIndex, env_cred: EnvEntry
    ) -> None:
        """Searching for env content must return empty results."""
        # Content contains "DATABASE_URL" and "secretpass"
        results = search_index.search("DATABASE_URL")
        assert len(results) == 0, "Env content must not be searchable"

    def test_env_secret_value_not_indexed(
        self, search_index: SearchIndex, env_cred: EnvEntry
    ) -> None:
        """Env secret values must not be searchable."""
        results = search_index.search("secretpass")
        assert len(results) == 0, "Env secret values must not be searchable"

    def test_env_api_key_not_indexed(
        self, search_index: SearchIndex, env_cred: EnvEntry
    ) -> None:
        """API keys in env content must not be searchable."""
        results = search_index.search("sk_live_supersecret")
        assert len(results) == 0, "API keys must not be searchable"

    def test_env_filename_is_searchable(
        self, search_index: SearchIndex, env_cred: EnvEntry
    ) -> None:
        """Env filename (non-sensitive) should be searchable."""
        results = search_index.search("production")
        # Should find via filename ".env.production" or title "Production Config"
        assert len(results) >= 1, "Env filename/title should be searchable"


@pytest.mark.security
class TestRecoveryCodesNotIndexed:
    """Verify recovery codes are never indexed or searchable."""

    def test_recovery_codes_not_indexed(
        self, search_index: SearchIndex, recovery_cred: RecoveryEntry
    ) -> None:
        """Searching for recovery code must return empty results."""
        # Content contains "ABCD-1234-EFGH"
        results = search_index.search("ABCD-1234")
        assert len(results) == 0, "Recovery codes must not be searchable"

    def test_recovery_partial_code_not_indexed(
        self, search_index: SearchIndex, recovery_cred: RecoveryEntry
    ) -> None:
        """Partial recovery codes must not be searchable."""
        results = search_index.search("EFGH")
        assert len(results) == 0, "Partial recovery codes must not be searchable"

    def test_recovery_title_is_searchable(
        self, search_index: SearchIndex, recovery_cred: RecoveryEntry
    ) -> None:
        """Recovery title (non-sensitive) should be searchable."""
        results = search_index.search("GitHub 2FA")
        assert len(results) >= 1, "Recovery title should be searchable"


@pytest.mark.security
class TestNoteContentNotIndexed:
    """Verify secure note content is never indexed or searchable."""

    def test_note_content_not_indexed(
        self, search_index: SearchIndex, note_cred: NoteEntry
    ) -> None:
        """Searching for note content must return empty results."""
        # Content contains "WiFiSecret2024!"
        results = search_index.search("WiFiSecret")
        assert len(results) == 0, "Note content must not be searchable"

    def test_note_ssid_not_indexed(
        self, search_index: SearchIndex, note_cred: NoteEntry
    ) -> None:
        """SSID in note content must not be searchable."""
        results = search_index.search("OfficeNet")
        assert len(results) == 0, "SSID in note content must not be searchable"

    def test_note_title_is_searchable(
        self, search_index: SearchIndex, note_cred: NoteEntry
    ) -> None:
        """Note title (non-sensitive) should be searchable."""
        results = search_index.search("Wi-Fi Credentials")
        assert len(results) >= 1, "Note title should be searchable"


# =============================================================================
# SECTION 3: DISPLAY SECURITY TESTS
# Verify that search result display formatting never reveals sensitive data.
# These tests validate the _format_secondary() method behavior.
# =============================================================================


@pytest.mark.security
class TestResultDisplayNoPassword:
    """Verify passwords never appear in search result display."""

    def test_result_display_no_password(
        self, search_index: SearchIndex, email_cred: EmailCredential
    ) -> None:
        """Search result for email must not expose password in any field."""
        results = search_index.search("GitHub")
        assert len(results) >= 1

        result = results[0]
        # Check all display fields
        assert email_cred.password not in result.primary_text
        assert email_cred.password not in result.secondary_text
        assert "SuperSecretPassword" not in result.primary_text
        assert "SuperSecretPassword" not in result.secondary_text


@pytest.mark.security
class TestResultDisplayNoCVV:
    """Verify CVV never appears in search result display."""

    def test_result_display_no_cvv(
        self, search_index: SearchIndex, card_cred: CreditCard
    ) -> None:
        """Search result for card must not expose CVV in any field."""
        results = search_index.search("Chase")
        assert len(results) >= 1

        result = results[0]
        assert card_cred.cvv not in result.primary_text
        assert card_cred.cvv not in result.secondary_text


@pytest.mark.security
class TestResultDisplayNoCardNumber:
    """Verify card numbers never appear in search result display."""

    def test_result_display_no_card_number(
        self, search_index: SearchIndex, card_cred: CreditCard
    ) -> None:
        """Search result for card must not expose card number in any field."""
        results = search_index.search("Chase")
        assert len(results) >= 1

        result = results[0]
        assert card_cred.card_number not in result.primary_text
        assert card_cred.card_number not in result.secondary_text
        # Also check for partial card number
        assert "4532" not in result.secondary_text
        assert "0366" not in result.secondary_text


@pytest.mark.security
class TestNoteShowsEncrypted:
    """Verify notes display [Encrypted] placeholder, not actual content."""

    def test_note_secondary_text_no_content(
        self, search_index: SearchIndex, note_cred: NoteEntry
    ) -> None:
        """Note search result must not expose content in secondary text."""
        results = search_index.search("Wi-Fi")
        assert len(results) >= 1

        result = results[0]
        # Verify content is not exposed
        assert note_cred.content not in result.secondary_text
        assert "WiFiSecret" not in result.secondary_text
        assert "OfficeNet" not in result.secondary_text
        # Secondary text for notes should be empty in SearchResult
        # (UI layer adds [Encrypted] during display)


@pytest.mark.security
class TestEnvDisplayNoContent:
    """Verify env display shows filename, not content."""

    def test_env_display_no_content(
        self, search_index: SearchIndex, env_cred: EnvEntry
    ) -> None:
        """Env search result must not expose content in display fields."""
        results = search_index.search("Production")
        assert len(results) >= 1

        result = results[0]
        # Content must not appear
        assert "DATABASE_URL" not in result.secondary_text
        assert "secretpass" not in result.secondary_text
        assert "sk_live" not in result.secondary_text
        # Should show filename as secondary
        assert result.secondary_text == ".env.production"


@pytest.mark.security
class TestRecoveryDisplayNoContent:
    """Verify recovery display shows title only, not codes."""

    def test_recovery_display_no_content(
        self, search_index: SearchIndex, recovery_cred: RecoveryEntry
    ) -> None:
        """Recovery search result must not expose codes in display fields."""
        results = search_index.search("GitHub 2FA")
        assert len(results) >= 1

        result = results[0]
        # Codes must not appear
        assert "ABCD" not in result.secondary_text
        assert "1234" not in result.secondary_text
        assert "EFGH" not in result.secondary_text


# =============================================================================
# SECTION 4: CONFIGURATION SECURITY TESTS
# Verify the SEARCHABLE_FIELDS configuration properly excludes sensitive fields.
# =============================================================================


@pytest.mark.security
class TestSearchableFieldsWhitelist:
    """Verify SEARCHABLE_FIELDS configuration excludes all sensitive fields."""

    def test_email_searchable_fields_no_password(self) -> None:
        """Email searchable fields must not include password."""
        fields = SEARCHABLE_FIELDS["email"]
        assert "password" not in fields, "password must not be searchable for email"

    def test_phone_searchable_fields_no_password(self) -> None:
        """Phone searchable fields must not include password."""
        fields = SEARCHABLE_FIELDS["phone"]
        assert "password" not in fields, "password must not be searchable for phone"

    def test_card_searchable_fields_no_cvv(self) -> None:
        """Card searchable fields must not include cvv."""
        fields = SEARCHABLE_FIELDS["card"]
        assert "cvv" not in fields, "cvv must not be searchable for card"

    def test_card_searchable_fields_no_card_number(self) -> None:
        """Card searchable fields must not include card_number."""
        fields = SEARCHABLE_FIELDS["card"]
        assert "card_number" not in fields, "card_number must not be searchable"

    def test_env_searchable_fields_no_content(self) -> None:
        """Env searchable fields must not include content."""
        fields = SEARCHABLE_FIELDS["env"]
        assert "content" not in fields, "content must not be searchable for env"

    def test_recovery_searchable_fields_no_content(self) -> None:
        """Recovery searchable fields must not include content."""
        fields = SEARCHABLE_FIELDS["recovery"]
        assert "content" not in fields, "content must not be searchable for recovery"

    def test_note_searchable_fields_no_content(self) -> None:
        """Note searchable fields must not include content."""
        fields = SEARCHABLE_FIELDS["note"]
        assert "content" not in fields, "content must not be searchable for note"

    def test_all_credential_types_have_config(self) -> None:
        """All credential types must have searchable field configuration."""
        required_types = ["email", "phone", "card", "env", "recovery", "note"]
        for cred_type in required_types:
            assert cred_type in SEARCHABLE_FIELDS, f"Missing config for {cred_type}"

    def test_searchable_fields_immutable_structure(self) -> None:
        """Searchable fields must follow expected structure."""
        for cred_type, fields in SEARCHABLE_FIELDS.items():
            assert isinstance(fields, list), f"{cred_type} must have list of fields"
            for field in fields:
                assert isinstance(
                    field, str
                ), f"Field {field} in {cred_type} must be string"


@pytest.mark.security
class TestSensitiveFieldsExcluded:
    """Comprehensive test that ALL sensitive fields are excluded from search."""

    SENSITIVE_FIELDS: dict[str, list[str]] = {
        "email": ["password"],
        "phone": ["password"],
        "card": ["card_number", "cvv"],
        "env": ["content"],
        "recovery": ["content"],
        "note": ["content"],
    }

    @pytest.mark.parametrize(
        "cred_type,sensitive_field",
        [
            ("email", "password"),
            ("phone", "password"),
            ("card", "card_number"),
            ("card", "cvv"),
            ("env", "content"),
            ("recovery", "content"),
            ("note", "content"),
        ],
    )
    def test_sensitive_field_excluded(
        self, cred_type: str, sensitive_field: str
    ) -> None:
        """Parametrized test: sensitive field must not be in searchable list."""
        fields = SEARCHABLE_FIELDS[cred_type]  # type: ignore[index]
        assert (
            sensitive_field not in fields
        ), f"{sensitive_field} must be excluded from {cred_type} searchable fields"


# =============================================================================
# SECTION 5: INDEX INTEGRITY TESTS
# Verify search index internal state never contains sensitive data.
# =============================================================================


@pytest.mark.security
class TestIndexInternalIntegrity:
    """Verify internal index state never contains sensitive data."""

    def test_index_entries_no_password(
        self, search_index: SearchIndex, email_cred: EmailCredential
    ) -> None:
        """Index entries must not contain password values."""
        for entry in search_index._entries:
            assert email_cred.password not in entry.raw_value
            assert email_cred.password not in entry.normalized_value
            assert email_cred.password.lower() not in entry.normalized_value

    def test_index_entries_no_cvv(
        self, search_index: SearchIndex, card_cred: CreditCard
    ) -> None:
        """Index entries must not contain CVV values."""
        for entry in search_index._entries:
            assert card_cred.cvv not in entry.raw_value
            assert card_cred.cvv not in entry.normalized_value

    def test_index_entries_no_card_number(
        self, search_index: SearchIndex, card_cred: CreditCard
    ) -> None:
        """Index entries must not contain card numbers."""
        for entry in search_index._entries:
            assert card_cred.card_number not in entry.raw_value
            assert card_cred.card_number not in entry.normalized_value

    def test_index_entries_no_env_content(
        self, search_index: SearchIndex, env_cred: EnvEntry
    ) -> None:
        """Index entries must not contain env content."""
        for entry in search_index._entries:
            # Check for key identifiers from env content
            assert "DATABASE_URL" not in entry.raw_value
            assert "secretpass" not in entry.raw_value
            assert "sk_live" not in entry.raw_value

    def test_index_entries_no_recovery_codes(
        self, search_index: SearchIndex, recovery_cred: RecoveryEntry
    ) -> None:
        """Index entries must not contain recovery codes."""
        for entry in search_index._entries:
            assert "ABCD-1234-EFGH" not in entry.raw_value
            assert "IJKL-5678-MNOP" not in entry.raw_value

    def test_index_entries_no_note_content(
        self, search_index: SearchIndex, note_cred: NoteEntry
    ) -> None:
        """Index entries must not contain note content."""
        for entry in search_index._entries:
            assert "WiFiSecret" not in entry.raw_value
            assert "OfficeNet" not in entry.raw_value

    def test_index_field_names_safe(self, search_index: SearchIndex) -> None:
        """Verify all indexed field names are from safe whitelist."""
        safe_fields = {
            "label",
            "email",
            "phone",
            "cardholder_name",
            "title",
            "filename",
            "notes",
        }
        sensitive_fields = {"password", "cvv", "card_number", "content"}

        for entry in search_index._entries:
            assert (
                entry.field_name in safe_fields
            ), f"Unexpected field {entry.field_name} indexed"
            assert (
                entry.field_name not in sensitive_fields
            ), f"Sensitive field {entry.field_name} was indexed"


# =============================================================================
# SECTION 6: CROSS-CREDENTIAL ISOLATION TESTS
# Verify that credentials cannot be found via other credentials' secrets.
# =============================================================================


@pytest.mark.security
class TestCrossCredentialIsolation:
    """Verify searching one credential's secret doesn't expose others."""

    def test_password_search_no_cross_match(self, search_index: SearchIndex) -> None:
        """Searching a password must not return any credentials."""
        # Search for a password-like string
        results = search_index.search("SuperSecret")
        assert len(results) == 0

    def test_content_search_no_cross_match(self, search_index: SearchIndex) -> None:
        """Searching env content must not return any credentials."""
        results = search_index.search("DATABASE")
        assert len(results) == 0

    def test_code_search_no_cross_match(self, search_index: SearchIndex) -> None:
        """Searching recovery code pattern must not return any credentials."""
        results = search_index.search("ABCD")
        assert len(results) == 0


# =============================================================================
# SECTION 7: EDGE CASE SECURITY TESTS
# Verify security holds under edge conditions.
# =============================================================================


@pytest.mark.security
class TestEdgeCaseSecurity:
    """Verify security under edge conditions."""

    def test_empty_query_no_results(self, search_index: SearchIndex) -> None:
        """Empty query must return no results (no accidental data leak)."""
        results = search_index.search("")
        assert len(results) == 0

    def test_whitespace_query_no_results(self, search_index: SearchIndex) -> None:
        """Whitespace-only query must return no results."""
        results = search_index.search("   ")
        assert len(results) == 0

    def test_special_chars_query_no_injection(self, search_index: SearchIndex) -> None:
        """Special characters must not cause injection or unexpected behavior."""
        # Test regex-like patterns
        results = search_index.search(".*")
        # Should not match everything
        assert len(results) == 0 or all(
            ".*" in r.primary_text.lower() or ".*" in r.secondary_text.lower()
            for r in results
        )

    def test_unicode_query_handled_safely(self, search_index: SearchIndex) -> None:
        """Unicode queries must be handled safely."""
        results = search_index.search("\u0000\u0001\u0002")
        # Should not crash, should return empty or safe results
        assert isinstance(results, list)

    def test_very_long_query_handled_safely(self, search_index: SearchIndex) -> None:
        """Very long queries must be handled safely."""
        long_query = "a" * 10000
        results = search_index.search(long_query)
        assert isinstance(results, list)
        assert len(results) == 0  # No match expected


@pytest.mark.security
class TestFieldGetterNoneInput:
    """Verify field getters handle None/missing gracefully."""

    def test_email_getter_none_notes(self) -> None:
        """Email getter handles None notes field."""
        cred = EmailCredential(label="Test", email="test@test.com", password="pass")
        result = _email_field_getter(cred, "notes")
        assert result is None

    def test_phone_getter_none_notes(self) -> None:
        """Phone getter handles None notes field."""
        cred = PhoneCredential(label="Test", phone="+1234567890", password="1234")
        result = _phone_field_getter(cred, "notes")
        assert result is None

    def test_card_getter_none_notes(self) -> None:
        """Card getter handles None notes field."""
        cred = CreditCard(
            label="Test",
            card_number="1234567890123456",
            expiry="12/25",
            cvv="123",
            cardholder_name="Test User",
        )
        result = _card_field_getter(cred, "notes")
        assert result is None
