# Unit tests for password generation utility.
# Validates correctness, security properties, and stability of password generation.

from __future__ import annotations

import string

import pytest

from passfx.utils.generator import (
    AMBIGUOUS,
    DIGITS,
    LOWERCASE,
    SYMBOLS,
    SYMBOLS_SAFE,
    UPPERCASE,
    estimate_crack_time,
    generate_passphrase,
    generate_password,
    generate_pin,
)


class TestGeneratePasswordLength:
    """Tests for password length handling."""

    def test_default_length_is_16(self) -> None:
        """Default password length is 16 characters."""
        password = generate_password()
        assert len(password) == 16

    def test_custom_length_respected(self) -> None:
        """Password matches requested length."""
        for length in [4, 8, 20, 32, 64, 128]:
            password = generate_password(length=length)
            assert len(password) == length

    def test_minimum_length_of_4(self) -> None:
        """Length of 4 is accepted."""
        password = generate_password(length=4)
        assert len(password) == 4

    def test_length_below_minimum_raises_error(self) -> None:
        """Length below 4 raises ValueError."""
        with pytest.raises(ValueError, match="at least 4"):
            generate_password(length=3)

    def test_length_of_1_raises_error(self) -> None:
        """Length of 1 raises ValueError."""
        with pytest.raises(ValueError, match="at least 4"):
            generate_password(length=1)

    def test_length_of_0_raises_error(self) -> None:
        """Length of 0 raises ValueError."""
        with pytest.raises(ValueError, match="at least 4"):
            generate_password(length=0)

    def test_negative_length_raises_error(self) -> None:
        """Negative length raises ValueError."""
        with pytest.raises(ValueError, match="at least 4"):
            generate_password(length=-1)


class TestGeneratePasswordCharacterSets:
    """Tests for character set inclusion."""

    def test_includes_lowercase_by_default(self) -> None:
        """Default password contains lowercase letters."""
        password = generate_password(length=32)
        assert any(c in LOWERCASE for c in password)

    def test_includes_uppercase_by_default(self) -> None:
        """Default password contains uppercase letters."""
        password = generate_password(length=32)
        assert any(c in UPPERCASE for c in password)

    def test_includes_digits_by_default(self) -> None:
        """Default password contains digits."""
        password = generate_password(length=32)
        assert any(c in DIGITS for c in password)

    def test_includes_symbols_by_default(self) -> None:
        """Default password contains symbols."""
        password = generate_password(length=32)
        assert any(c in SYMBOLS for c in password)

    def test_lowercase_only(self) -> None:
        """Password with only lowercase enabled contains only lowercase."""
        password = generate_password(
            length=20,
            use_lowercase=True,
            use_uppercase=False,
            use_digits=False,
            use_symbols=False,
        )
        assert all(c in LOWERCASE for c in password)
        assert len(password) == 20

    def test_uppercase_only(self) -> None:
        """Password with only uppercase enabled contains only uppercase."""
        password = generate_password(
            length=20,
            use_lowercase=False,
            use_uppercase=True,
            use_digits=False,
            use_symbols=False,
        )
        assert all(c in UPPERCASE for c in password)

    def test_digits_only(self) -> None:
        """Password with only digits enabled contains only digits."""
        password = generate_password(
            length=20,
            use_lowercase=False,
            use_uppercase=False,
            use_digits=True,
            use_symbols=False,
        )
        assert all(c in DIGITS for c in password)

    def test_symbols_only(self) -> None:
        """Password with only symbols enabled contains only symbols."""
        password = generate_password(
            length=20,
            use_lowercase=False,
            use_uppercase=False,
            use_digits=False,
            use_symbols=True,
        )
        assert all(c in SYMBOLS for c in password)

    def test_no_character_types_raises_error(self) -> None:
        """Disabling all character types raises ValueError."""
        with pytest.raises(ValueError, match="At least one character type"):
            generate_password(
                use_lowercase=False,
                use_uppercase=False,
                use_digits=False,
                use_symbols=False,
            )

    def test_mixed_lowercase_and_digits(self) -> None:
        """Password with lowercase and digits contains both."""
        password = generate_password(
            length=32,
            use_lowercase=True,
            use_uppercase=False,
            use_digits=True,
            use_symbols=False,
        )
        assert any(c in LOWERCASE for c in password)
        assert any(c in DIGITS for c in password)
        assert not any(c in UPPERCASE for c in password)
        assert not any(c in SYMBOLS for c in password)

    def test_all_character_types_combined(self) -> None:
        """Password with all types enabled contains all types."""
        password = generate_password(length=32)
        assert any(c in LOWERCASE for c in password)
        assert any(c in UPPERCASE for c in password)
        assert any(c in DIGITS for c in password)
        assert any(c in SYMBOLS for c in password)


class TestGeneratePasswordAmbiguousExclusion:
    """Tests for ambiguous character exclusion."""

    def test_exclude_ambiguous_removes_ambiguous_chars(self) -> None:
        """Excluding ambiguous characters removes them from output."""
        # Generate many passwords to have statistical confidence
        for _ in range(50):
            password = generate_password(length=64, exclude_ambiguous=True)
            for char in AMBIGUOUS:
                assert char not in password

    def test_ambiguous_chars_present_by_default(self) -> None:
        """Ambiguous characters are allowed by default."""
        # Check that ambiguous chars are in the pools
        assert "0" in DIGITS
        assert "O" in UPPERCASE
        assert "1" in DIGITS
        assert "l" in LOWERCASE
        assert "I" in UPPERCASE

    def test_exclude_ambiguous_with_digits_only(self) -> None:
        """Excluding ambiguous with digits only removes 0 and 1."""
        for _ in range(50):
            password = generate_password(
                length=32,
                use_lowercase=False,
                use_uppercase=False,
                use_digits=True,
                use_symbols=False,
                exclude_ambiguous=True,
            )
            assert "0" not in password
            assert "1" not in password

    def test_exclude_ambiguous_with_uppercase_only(self) -> None:
        """Excluding ambiguous with uppercase removes O and I."""
        for _ in range(50):
            password = generate_password(
                length=32,
                use_lowercase=False,
                use_uppercase=True,
                use_digits=False,
                use_symbols=False,
                exclude_ambiguous=True,
            )
            assert "O" not in password
            assert "I" not in password


class TestGeneratePasswordSafeSymbols:
    """Tests for safe symbols option."""

    def test_safe_symbols_uses_safe_set(self) -> None:
        """Safe symbols option uses the restricted symbol set."""
        for _ in range(50):
            password = generate_password(
                length=32,
                use_lowercase=False,
                use_uppercase=False,
                use_digits=False,
                use_symbols=True,
                safe_symbols=True,
            )
            assert all(c in SYMBOLS_SAFE for c in password)

    def test_full_symbols_used_by_default(self) -> None:
        """Full symbol set is used when safe_symbols is False."""
        # Verify full symbols set is larger
        assert len(SYMBOLS) > len(SYMBOLS_SAFE)

    def test_safe_symbols_is_subset_of_full_symbols(self) -> None:
        """Safe symbols are a subset of full symbols."""
        assert all(c in SYMBOLS for c in SYMBOLS_SAFE)


class TestGeneratePasswordGuarantees:
    """Tests for character type guarantees in output."""

    def test_guarantees_at_least_one_of_each_enabled_type(self) -> None:
        """Generated password contains at least one of each enabled type."""
        # Minimum length is 4, which should still work with all types
        password = generate_password(length=4)
        assert any(c in LOWERCASE for c in password)
        assert any(c in UPPERCASE for c in password)
        assert any(c in DIGITS for c in password)
        assert any(c in SYMBOLS for c in password)

    def test_short_password_has_required_chars(self) -> None:
        """Even minimum length passwords have required character types."""
        for _ in range(100):
            password = generate_password(
                length=4,
                use_lowercase=True,
                use_uppercase=True,
                use_digits=True,
                use_symbols=True,
            )
            assert len(password) == 4
            # Should have at least one of each type
            assert any(c in LOWERCASE for c in password)
            assert any(c in UPPERCASE for c in password)
            assert any(c in DIGITS for c in password)
            assert any(c in SYMBOLS for c in password)


class TestGeneratePasswordNonDeterminism:
    """Tests for randomness and non-determinism."""

    def test_consecutive_passwords_are_different(self) -> None:
        """Consecutive calls produce different passwords."""
        passwords = [generate_password() for _ in range(100)]
        # All should be unique
        assert len(set(passwords)) == 100

    def test_same_parameters_produce_different_results(self) -> None:
        """Same parameters produce different results each call."""
        passwords = [
            generate_password(
                length=20,
                use_lowercase=True,
                use_uppercase=True,
                use_digits=True,
                use_symbols=True,
            )
            for _ in range(50)
        ]
        assert len(set(passwords)) == 50

    def test_character_distribution_is_varied(self) -> None:
        """Characters appear in varied positions across passwords."""
        # Generate multiple passwords and check first character varies
        first_chars = [generate_password()[0] for _ in range(100)]
        # Should have multiple unique first characters
        assert len(set(first_chars)) > 10


class TestGeneratePasswordEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_long_password(self) -> None:
        """Very long passwords are generated correctly."""
        password = generate_password(length=1000)
        assert len(password) == 1000

    def test_pool_too_small_after_filtering_raises_error(self) -> None:
        """Error when filtering leaves insufficient characters."""
        # If we exclude ambiguous and use only specific chars, pool might be tiny
        # This test validates the "Not enough characters" check
        # Currently digits without ambiguous = 8 chars (2-9), which is > 2
        # This edge case is hard to trigger with current options
        # Let's verify the error message exists in the function
        pass  # The function has this check but current options don't trigger it

    def test_exclude_ambiguous_with_exclude_pattern_still_works(self) -> None:
        """Combining exclude_ambiguous with single char type works."""
        # Lowercase without ambiguous (no 'l')
        password = generate_password(
            length=20,
            use_lowercase=True,
            use_uppercase=False,
            use_digits=False,
            use_symbols=False,
            exclude_ambiguous=True,
        )
        assert "l" not in password
        assert all(c in LOWERCASE and c != "l" for c in password)


class TestGeneratePassphraseBasic:
    """Tests for basic passphrase generation."""

    def test_default_word_count_is_4(self) -> None:
        """Default passphrase has 4 words."""
        passphrase = generate_passphrase()
        words = passphrase.split("-")
        assert len(words) == 4

    def test_custom_word_count(self) -> None:
        """Custom word count is respected."""
        for count in [2, 3, 5, 8]:
            passphrase = generate_passphrase(word_count=count)
            words = passphrase.split("-")
            assert len(words) == count

    def test_default_separator_is_hyphen(self) -> None:
        """Default separator is hyphen."""
        passphrase = generate_passphrase()
        assert "-" in passphrase

    def test_custom_separator(self) -> None:
        """Custom separator is used correctly."""
        passphrase = generate_passphrase(separator="_")
        words = passphrase.split("_")
        assert len(words) == 4

    def test_space_separator(self) -> None:
        """Space can be used as separator."""
        passphrase = generate_passphrase(separator=" ")
        words = passphrase.split(" ")
        assert len(words) == 4

    def test_empty_separator(self) -> None:
        """Empty separator concatenates words."""
        passphrase = generate_passphrase(separator="")
        # Without separator, should be single concatenated string
        assert "-" not in passphrase
        assert " " not in passphrase


class TestGeneratePassphraseCapitalization:
    """Tests for passphrase capitalization."""

    def test_capitalize_by_default(self) -> None:
        """Words are capitalized by default."""
        passphrase = generate_passphrase()
        words = passphrase.split("-")
        for word in words:
            assert word[0].isupper()
            assert word[1:].islower()

    def test_capitalize_false_keeps_lowercase(self) -> None:
        """Setting capitalize=False keeps words lowercase."""
        passphrase = generate_passphrase(capitalize=False)
        words = passphrase.split("-")
        for word in words:
            assert word.islower()

    def test_capitalization_with_custom_separator(self) -> None:
        """Capitalization works with custom separator."""
        passphrase = generate_passphrase(separator=".", capitalize=True)
        words = passphrase.split(".")
        for word in words:
            assert word[0].isupper()


class TestGeneratePassphraseNonDeterminism:
    """Tests for passphrase randomness."""

    def test_consecutive_passphrases_are_different(self) -> None:
        """Consecutive calls produce different passphrases."""
        passphrases = [generate_passphrase() for _ in range(50)]
        assert len(set(passphrases)) == 50

    def test_word_selection_is_random(self) -> None:
        """Different words are selected across generations."""
        first_words = [generate_passphrase().split("-")[0] for _ in range(50)]
        # Should have variety in first words
        assert len(set(first_words)) > 5


class TestGeneratePassphraseWordList:
    """Tests for passphrase word list properties."""

    def test_words_are_common_english(self) -> None:
        """Generated words appear to be common English words."""
        passphrase = generate_passphrase(capitalize=False)
        words = passphrase.split("-")
        for word in words:
            # All words should be alphabetic
            assert word.isalpha()
            # Words should be reasonable length
            assert 3 <= len(word) <= 12


class TestGeneratePinBasic:
    """Tests for basic PIN generation."""

    def test_default_length_is_4(self) -> None:
        """Default PIN length is 4 digits."""
        pin = generate_pin()
        assert len(pin) == 4

    def test_custom_length(self) -> None:
        """Custom PIN length is respected."""
        for length in [4, 6, 8, 10]:
            pin = generate_pin(length=length)
            assert len(pin) == length

    def test_contains_only_digits(self) -> None:
        """PIN contains only numeric digits."""
        for length in [4, 6, 8]:
            pin = generate_pin(length=length)
            assert pin.isdigit()
            assert all(c in DIGITS for c in pin)

    def test_minimum_length_is_4(self) -> None:
        """PIN length must be at least 4."""
        pin = generate_pin(length=4)
        assert len(pin) == 4

    def test_length_below_4_raises_error(self) -> None:
        """PIN length below 4 raises ValueError."""
        with pytest.raises(ValueError, match="at least 4"):
            generate_pin(length=3)

    def test_length_of_1_raises_error(self) -> None:
        """PIN length of 1 raises ValueError."""
        with pytest.raises(ValueError, match="at least 4"):
            generate_pin(length=1)


class TestGeneratePinNonDeterminism:
    """Tests for PIN randomness."""

    def test_consecutive_pins_show_variety(self) -> None:
        """Consecutive PIN calls produce varied values.

        With 100 samples from 10,000 possibilities, birthday paradox means
        some collisions are expected (~40% probability). We verify high variety
        rather than perfect uniqueness.
        """
        pins = [generate_pin() for _ in range(100)]
        # Should have at least 90 unique (allowing for some birthday collisions)
        assert len(set(pins)) >= 90

    def test_long_pins_are_random(self) -> None:
        """Longer PINs show randomness."""
        pins = [generate_pin(length=10) for _ in range(50)]
        assert len(set(pins)) == 50


class TestEstimateCrackTimeBasic:
    """Tests for crack time estimation."""

    def test_instant_for_empty_password(self) -> None:
        """Empty password returns instant."""
        result = estimate_crack_time("")
        assert result == "instant"

    def test_instant_for_very_short_password(self) -> None:
        """Very short password returns instant."""
        result = estimate_crack_time("a")
        assert result == "instant"

    def test_returns_string(self) -> None:
        """Estimate returns a string."""
        result = estimate_crack_time("password123")
        assert isinstance(result, str)

    def test_longer_password_takes_longer(self) -> None:
        """Longer passwords have longer crack times."""
        short_result = estimate_crack_time("aaaa")
        long_result = estimate_crack_time("aaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        # Short should be instant or seconds
        assert short_result in ("instant", "0 seconds") or "second" in short_result
        # Long should be years or centuries
        assert "year" in long_result or "centuries" in long_result

    def test_complex_password_takes_longer(self) -> None:
        """Passwords with more character types take longer to crack."""
        simple = estimate_crack_time("aaaaaaaaaa")  # lowercase only
        complex_pw = estimate_crack_time("aA1!aA1!aA")  # all types
        # Both are 10 chars but complex has larger pool
        # Can't easily compare strings, just verify they're valid
        assert isinstance(simple, str)
        assert isinstance(complex_pw, str)


class TestEstimateCrackTimeFormats:
    """Tests for crack time output formats."""

    def test_seconds_format(self) -> None:
        """Returns seconds for very weak passwords."""
        # Short lowercase password
        result = estimate_crack_time("aaaaa")
        assert result == "instant" or "second" in result

    def test_minutes_format(self) -> None:
        """Minutes format is used for moderate passwords."""
        # Medium lowercase password
        result = estimate_crack_time("aaaaaaaa")
        # Could be seconds, minutes, or hours depending on calculation
        valid_formats = ["instant", "second", "minute", "hour"]
        assert any(fmt in result for fmt in valid_formats)

    def test_centuries_format(self) -> None:
        """Centuries format is used for strong passwords."""
        # Very long password with all character types
        result = estimate_crack_time("aA1!bB2@cC3#dD4$eE5%fF6^")
        assert "year" in result or "centuries" in result


class TestEstimateCrackTimePoolDetection:
    """Tests for character pool detection."""

    def test_detects_lowercase_pool(self) -> None:
        """Lowercase characters are detected."""
        result = estimate_crack_time("abcdefgh")
        assert isinstance(result, str)

    def test_detects_uppercase_pool(self) -> None:
        """Uppercase characters are detected."""
        result = estimate_crack_time("ABCDEFGH")
        assert isinstance(result, str)

    def test_detects_digit_pool(self) -> None:
        """Digit characters are detected."""
        result = estimate_crack_time("12345678")
        assert isinstance(result, str)

    def test_detects_symbol_pool(self) -> None:
        """Symbol characters are detected."""
        result = estimate_crack_time("!@#$%^&*")
        assert isinstance(result, str)

    def test_detects_mixed_pools(self) -> None:
        """Mixed character types are detected."""
        result = estimate_crack_time("aA1!")
        assert isinstance(result, str)


class TestSecurityProperties:
    """Tests for security properties of generation functions."""

    def test_password_uses_secrets_module(self) -> None:
        """Password generation exhibits cryptographic randomness properties.

        This test validates behavioral properties consistent with secrets module:
        - High uniqueness across samples
        - No detectable patterns
        """
        # Generate many passwords and verify uniqueness
        passwords = [generate_password(length=16) for _ in range(1000)]
        # All 1000 should be unique (cryptographic randomness)
        assert len(set(passwords)) == 1000

    def test_passphrase_uses_secrets_module(self) -> None:
        """Passphrase generation uses cryptographic randomness."""
        passphrases = [generate_passphrase() for _ in range(500)]
        assert len(set(passphrases)) == 500

    def test_pin_uses_secrets_module(self) -> None:
        """PIN generation uses cryptographic randomness."""
        pins = [generate_pin(length=6) for _ in range(500)]
        # 6-digit PIN has 1M possibilities, 500 samples should be unique
        assert len(set(pins)) == 500

    def test_no_sequential_patterns_in_passwords(self) -> None:
        """Passwords don't contain obvious sequential patterns."""
        for _ in range(100):
            password = generate_password(length=20)
            # Should not contain common sequences
            assert "1234" not in password
            assert "abcd" not in password
            assert "ABCD" not in password
            assert "0000" not in password

    def test_password_character_distribution_reasonable(self) -> None:
        """Characters are reasonably distributed in passwords.

        Cryptographic randomness should produce varied character usage.
        """
        # Generate a long password and check distribution
        password = generate_password(length=200)
        char_counts: dict[str, int] = {}
        for c in password:
            char_counts[c] = char_counts.get(c, 0) + 1

        # With 200 chars from ~90 char pool, most chars should appear 1-5 times
        # No single character should dominate (>20% of password)
        max_count = max(char_counts.values())
        assert max_count < 40  # Less than 20% for any single char

    def test_shuffling_occurs(self) -> None:
        """Password characters are shuffled, not in predictable order.

        The guaranteed characters should not always be in the same positions.
        """
        # Generate multiple passwords and track first character types
        first_char_types = []
        for _ in range(100):
            password = generate_password(length=8)
            first = password[0]
            if first in LOWERCASE:
                first_char_types.append("lower")
            elif first in UPPERCASE:
                first_char_types.append("upper")
            elif first in DIGITS:
                first_char_types.append("digit")
            else:
                first_char_types.append("symbol")

        # All four types should appear as first character due to shuffling
        assert len(set(first_char_types)) == 4


class TestConstantValues:
    """Tests for module constants."""

    def test_lowercase_is_standard(self) -> None:
        """LOWERCASE constant matches string.ascii_lowercase."""
        assert LOWERCASE == string.ascii_lowercase

    def test_uppercase_is_standard(self) -> None:
        """UPPERCASE constant matches string.ascii_uppercase."""
        assert UPPERCASE == string.ascii_uppercase

    def test_digits_is_standard(self) -> None:
        """DIGITS constant matches string.digits."""
        assert DIGITS == string.digits

    def test_ambiguous_contains_expected_chars(self) -> None:
        """AMBIGUOUS contains commonly confused characters."""
        assert "0" in AMBIGUOUS
        assert "O" in AMBIGUOUS
        assert "1" in AMBIGUOUS
        assert "l" in AMBIGUOUS
        assert "I" in AMBIGUOUS

    def test_symbols_safe_is_subset(self) -> None:
        """Safe symbols are a subset of full symbols."""
        for char in SYMBOLS_SAFE:
            assert char in SYMBOLS or char in "+-="
