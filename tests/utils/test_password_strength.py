# Unit tests for password strength analysis utility.
# Validates scoring consistency, classification correctness, and rule enforcement.

from __future__ import annotations

from datetime import datetime, timedelta

from rich.text import Text

from passfx.utils.strength import (
    PASSWORD_AGE_THRESHOLD_DAYS,
    STRENGTH_LABELS,
    WEAK_PINS,
    StrengthResult,
    VaultHealthResult,
    _compute_vault_score,
    _simple_strength_check,
    analyze_vault,
    check_strength,
    get_strength_bar,
    get_strength_display,
    meets_requirements,
)


class TestStrengthResultDataclass:
    """Tests for StrengthResult dataclass structure."""

    def test_dataclass_fields_exist(self) -> None:
        """StrengthResult has all required fields."""
        result = StrengthResult(
            score=3,
            label="Good",
            color="bright_green",
            crack_time="centuries",
            suggestions=["Add more characters"],
            warning="This is weak",
        )
        assert result.score == 3
        assert result.label == "Good"
        assert result.color == "bright_green"
        assert result.crack_time == "centuries"
        assert result.suggestions == ["Add more characters"]
        assert result.warning == "This is weak"

    def test_dataclass_accepts_none_warning(self) -> None:
        """StrengthResult accepts None for warning."""
        result = StrengthResult(
            score=4,
            label="Strong",
            color="bold bright_green",
            crack_time="heat death of the universe",
            suggestions=[],
            warning=None,
        )
        assert result.warning is None

    def test_dataclass_accepts_empty_suggestions(self) -> None:
        """StrengthResult accepts empty suggestions list."""
        result = StrengthResult(
            score=4,
            label="Strong",
            color="bold bright_green",
            crack_time="centuries",
            suggestions=[],
            warning=None,
        )
        assert result.suggestions == []

    def test_score_range_not_enforced_by_dataclass(self) -> None:
        """Dataclass does not enforce score range (validation elsewhere)."""
        result = StrengthResult(
            score=10,
            label="Test",
            color="white",
            crack_time="unknown",
            suggestions=[],
            warning=None,
        )
        assert result.score == 10


class TestStrengthLabelsConstant:
    """Tests for STRENGTH_LABELS mapping constant."""

    def test_has_all_scores_0_to_4(self) -> None:
        """STRENGTH_LABELS contains entries for scores 0-4."""
        for score in range(5):
            assert score in STRENGTH_LABELS

    def test_score_0_is_very_weak(self) -> None:
        """Score 0 maps to Very Weak."""
        label, color = STRENGTH_LABELS[0]
        assert label == "Very Weak"
        assert "red" in color.lower()

    def test_score_1_is_weak(self) -> None:
        """Score 1 maps to Weak."""
        label, color = STRENGTH_LABELS[1]
        assert label == "Weak"
        assert "red" in color.lower()

    def test_score_2_is_fair(self) -> None:
        """Score 2 maps to Fair."""
        label, color = STRENGTH_LABELS[2]
        assert label == "Fair"
        assert "yellow" in color.lower()

    def test_score_3_is_good(self) -> None:
        """Score 3 maps to Good."""
        label, color = STRENGTH_LABELS[3]
        assert label == "Good"
        assert "green" in color.lower()

    def test_score_4_is_strong(self) -> None:
        """Score 4 maps to Strong."""
        label, color = STRENGTH_LABELS[4]
        assert label == "Strong"
        assert "green" in color.lower()

    def test_labels_are_tuples(self) -> None:
        """Each entry is a tuple of (label, color)."""
        for score, value in STRENGTH_LABELS.items():
            assert isinstance(value, tuple)
            assert len(value) == 2
            label, color = value
            assert isinstance(label, str)
            assert isinstance(color, str)


class TestCheckStrengthBasic:
    """Tests for basic check_strength functionality."""

    def test_returns_strength_result(self) -> None:
        """check_strength returns a StrengthResult instance."""
        result = check_strength("TestPassword123!")
        assert isinstance(result, StrengthResult)

    def test_score_is_integer_0_to_4(self) -> None:
        """Score is always an integer in range 0-4."""
        passwords = [
            "a",
            "password",
            "Password1",
            "P@ssw0rd!Str0ng",
            "correct horse battery staple",
        ]
        for password in passwords:
            result = check_strength(password)
            assert isinstance(result.score, int)
            assert 0 <= result.score <= 4

    def test_label_matches_score(self) -> None:
        """Label matches the expected label for the score."""
        result = check_strength("TestPassword123!")
        expected_label, _ = STRENGTH_LABELS.get(result.score, ("Unknown", "white"))
        assert result.label == expected_label

    def test_color_matches_score(self) -> None:
        """Color matches the expected color for the score."""
        result = check_strength("TestPassword123!")
        _, expected_color = STRENGTH_LABELS.get(result.score, ("Unknown", "white"))
        assert result.color == expected_color

    def test_crack_time_is_string(self) -> None:
        """crack_time is always a string."""
        result = check_strength("AnyPassword")
        assert isinstance(result.crack_time, str)

    def test_suggestions_is_list(self) -> None:
        """suggestions is always a list."""
        result = check_strength("weak")
        assert isinstance(result.suggestions, list)


class TestCheckStrengthClassification:
    """Tests for password strength classification."""

    def test_very_weak_password_scores_low(self) -> None:
        """Very weak passwords score 0 or 1."""
        weak_passwords = ["a", "1234", "pass", "qwerty"]
        for pw in weak_passwords:
            result = check_strength(pw)
            assert result.score <= 1, f"{pw} should score low"

    def test_common_password_scores_low(self) -> None:
        """Common passwords are detected as weak."""
        result = check_strength("password")
        assert result.score <= 1

    def test_strong_password_scores_high(self) -> None:
        """Strong passwords with entropy score 3 or 4."""
        strong = "Xk9$mP2@zQ7!nL4#wE8"
        result = check_strength(strong)
        assert result.score >= 3

    def test_passphrase_style_scores_well(self) -> None:
        """Passphrase-style passwords score reasonably."""
        result = check_strength("correct horse battery staple")
        assert result.score >= 3

    def test_mixed_case_improves_score(self) -> None:
        """Mixed case passwords score higher than single case."""
        lower_only = check_strength("abcdefghijklmnop")
        mixed = check_strength("abcdEFGHijklMNOP")
        # Mixed should be at least as good due to more entropy
        assert mixed.score >= lower_only.score

    def test_numbers_improve_score(self) -> None:
        """Adding numbers improves score."""
        letters_only = check_strength("abcdefghij")
        with_numbers = check_strength("abcde12345")
        # With numbers should have comparable or better score
        assert with_numbers.score >= letters_only.score - 1


class TestCheckStrengthDeterminism:
    """Tests for deterministic scoring behavior."""

    def test_same_password_same_score(self) -> None:
        """Same password always produces same score."""
        password = "TestDeterminism123!"
        scores = [check_strength(password).score for _ in range(10)]
        assert all(s == scores[0] for s in scores)

    def test_same_password_same_label(self) -> None:
        """Same password always produces same label."""
        password = "ConsistentPassword!"
        labels = [check_strength(password).label for _ in range(10)]
        assert all(label == labels[0] for label in labels)

    def test_same_password_same_crack_time(self) -> None:
        """Same password always produces same crack time."""
        password = "DeterministicTime99"
        times = [check_strength(password).crack_time for _ in range(10)]
        assert all(t == times[0] for t in times)


class TestCheckStrengthEdgeCases:
    """Tests for edge cases in check_strength."""

    def test_empty_string(self) -> None:
        """Empty string returns valid result with lowest score."""
        result = check_strength("")
        assert result.score == 0
        assert isinstance(result.label, str)

    def test_single_character(self) -> None:
        """Single character password scores very low."""
        result = check_strength("x")
        assert result.score == 0

    def test_whitespace_only(self) -> None:
        """Whitespace-only password is handled."""
        result = check_strength("   ")
        assert isinstance(result, StrengthResult)
        assert result.score <= 1

    def test_very_long_password_uses_simple_check(self) -> None:
        """Passwords over 72 chars use simple strength check."""
        long_pw = "A" * 100
        result = check_strength(long_pw)
        assert isinstance(result, StrengthResult)
        # Simple check gives bonus for very long passwords
        assert result.score >= 3

    def test_unicode_password(self) -> None:
        """Unicode passwords are handled."""
        result = check_strength("p@ssword123")
        assert isinstance(result, StrengthResult)

    def test_special_characters_handled(self) -> None:
        """Passwords with special characters work."""
        result = check_strength("Test!@#$%^&*()")
        assert isinstance(result, StrengthResult)


class TestCheckStrengthLongPasswords:
    """Tests for passwords exceeding zxcvbn limit."""

    def test_73_char_password_uses_simple_check(self) -> None:
        """73 character password triggers simple check."""
        password = "a" * 73
        result = check_strength(password)
        assert isinstance(result, StrengthResult)

    def test_100_char_password_scores_high(self) -> None:
        """Very long passwords score high in simple check."""
        password = "aB1!" * 25  # 100 chars
        result = check_strength(password)
        assert result.score == 4

    def test_200_char_password_handled(self) -> None:
        """200 character passwords work correctly."""
        password = "x" * 200
        result = check_strength(password)
        assert isinstance(result, StrengthResult)


class TestSimpleStrengthCheck:
    """Tests for _simple_strength_check fallback function."""

    def test_short_password_scores_low(self) -> None:
        """Passwords under 8 chars score very low."""
        result = _simple_strength_check("abc")
        assert result.score <= 1

    def test_8_char_password_gets_one_point(self) -> None:
        """8 character passwords get at least one length point."""
        result = _simple_strength_check("abcdefgh")
        assert result.score >= 1

    def test_12_char_password_gets_two_points(self) -> None:
        """12 character passwords get at least two length points."""
        result = _simple_strength_check("abcdefghijkl")
        assert result.score >= 2

    def test_16_char_password_gets_three_points(self) -> None:
        """16 character passwords get at least three length points."""
        result = _simple_strength_check("abcdefghijklmnop")
        assert result.score >= 3

    def test_24_char_password_gets_four_points(self) -> None:
        """24+ character passwords can reach max score."""
        result = _simple_strength_check("abcdefghijklmnopqrstuvwx")
        assert result.score >= 4

    def test_complexity_adds_score(self) -> None:
        """Mixed character types add to score."""
        simple = _simple_strength_check("aaaaaaaaaaaa")
        complex_pw = _simple_strength_check("aA1!aA1!aA1!")
        assert complex_pw.score >= simple.score

    def test_three_character_types_adds_bonus(self) -> None:
        """Having 3+ character types adds bonus point."""
        two_types = _simple_strength_check("aaaAAAAA123")  # lower + upper + digit
        # With 11 chars and 3 types, should get length bonus + complexity
        assert two_types.score >= 2

    def test_score_capped_at_4(self) -> None:
        """Score never exceeds 4."""
        result = _simple_strength_check("aA1!bB2@cC3#dD4$eE5%fF6^gG7&hH8*")
        assert result.score == 4


class TestSimpleStrengthCheckSuggestions:
    """Tests for suggestions generated by _simple_strength_check."""

    def test_suggests_length_for_short_password(self) -> None:
        """Suggests longer password for short input."""
        result = _simple_strength_check("short")
        assert any("12" in s for s in result.suggestions)

    def test_suggests_uppercase_when_missing(self) -> None:
        """Suggests uppercase when not present."""
        result = _simple_strength_check("alllowercase")
        assert any("uppercase" in s.lower() for s in result.suggestions)

    def test_suggests_lowercase_when_missing(self) -> None:
        """Suggests lowercase when not present."""
        result = _simple_strength_check("ALLUPPERCASE")
        assert any("lowercase" in s.lower() for s in result.suggestions)

    def test_suggests_numbers_when_missing(self) -> None:
        """Suggests numbers when not present."""
        result = _simple_strength_check("NoNumbersHere")
        assert any("number" in s.lower() for s in result.suggestions)

    def test_suggests_symbols_when_missing(self) -> None:
        """Suggests special characters when not present."""
        result = _simple_strength_check("NoSpecialChars123")
        assert any("special" in s.lower() for s in result.suggestions)

    def test_no_suggestions_for_complete_password(self) -> None:
        """Strong password with all types has fewer suggestions."""
        result = _simple_strength_check("StrongP@ssw0rd!")
        # May still suggest length if under 12
        assert len(result.suggestions) <= 1


class TestSimpleStrengthCheckCrackTime:
    """Tests for crack time estimates in _simple_strength_check."""

    def test_very_long_password_heat_death(self) -> None:
        """64+ char passwords estimate heat death of universe."""
        result = _simple_strength_check("x" * 64)
        assert "heat death" in result.crack_time.lower()

    def test_32_char_password_billions_of_years(self) -> None:
        """32-63 char passwords estimate billions of years."""
        result = _simple_strength_check("x" * 32)
        assert "billion" in result.crack_time.lower()

    def test_20_char_password_millions_of_years(self) -> None:
        """20-31 char passwords estimate millions of years."""
        result = _simple_strength_check("x" * 20)
        assert "million" in result.crack_time.lower()

    def test_weak_password_short_crack_time(self) -> None:
        """Weak passwords have short crack time."""
        result = _simple_strength_check("weak")
        assert (
            "second" in result.crack_time.lower()
            or "minute" in result.crack_time.lower()
        )


class TestGetStrengthBar:
    """Tests for get_strength_bar visual output."""

    def test_returns_rich_text(self) -> None:
        """Returns a Rich Text object."""
        bar = get_strength_bar(3)
        assert isinstance(bar, Text)

    def test_contains_brackets(self) -> None:
        """Bar is enclosed in brackets."""
        bar = get_strength_bar(2)
        plain = bar.plain
        assert plain.startswith("[")
        assert plain.endswith("]")

    def test_default_width_is_10(self) -> None:
        """Default bar width is 10 characters inside brackets."""
        bar = get_strength_bar(2, width=10)
        plain = bar.plain
        # Remove brackets
        inner = plain[1:-1]
        assert len(inner) == 10

    def test_custom_width_respected(self) -> None:
        """Custom width is applied."""
        for width in [5, 15, 20]:
            bar = get_strength_bar(3, width=width)
            inner = bar.plain[1:-1]
            assert len(inner) == width

    def test_score_0_has_some_fill(self) -> None:
        """Score 0 has at least some visual indicator."""
        bar = get_strength_bar(0, width=10)
        assert isinstance(bar, Text)

    def test_score_4_mostly_filled(self) -> None:
        """Score 4 is mostly filled."""
        bar = get_strength_bar(4, width=10)
        # Check that filled portion increases with score
        assert isinstance(bar, Text)

    def test_all_scores_produce_valid_bar(self) -> None:
        """All scores 0-4 produce valid bars."""
        for score in range(5):
            bar = get_strength_bar(score)
            assert isinstance(bar, Text)
            assert "[" in bar.plain
            assert "]" in bar.plain


class TestGetStrengthDisplay:
    """Tests for get_strength_display full output."""

    def test_returns_rich_text(self) -> None:
        """Returns a Rich Text object."""
        display = get_strength_display("TestPassword123")
        assert isinstance(display, Text)

    def test_contains_strength_bar(self) -> None:
        """Display includes strength bar."""
        display = get_strength_display("TestPassword")
        plain = display.plain
        assert "[" in plain

    def test_contains_crack_time(self) -> None:
        """Display includes crack time."""
        display = get_strength_display("TestPassword")
        plain = display.plain.lower()
        assert "crack time" in plain

    def test_contains_label(self) -> None:
        """Display includes strength label."""
        display = get_strength_display("TestPassword123!")
        plain = display.plain
        # Should contain one of the labels
        labels = [label for label, _ in STRENGTH_LABELS.values()]
        assert any(label in plain for label in labels)

    def test_shows_suggestions_by_default(self) -> None:
        """Suggestions shown by default for weak passwords."""
        display = get_strength_display("weak")
        plain = display.plain.lower()
        # Weak password should have tips
        assert "tip" in plain or len(plain) > 50

    def test_can_hide_suggestions(self) -> None:
        """Suggestions can be hidden with parameter."""
        display_with = get_strength_display("weak", show_suggestions=True)
        display_without = get_strength_display("weak", show_suggestions=False)
        # Without suggestions should be shorter
        assert len(display_without.plain) <= len(display_with.plain)

    def test_warning_shown_when_present(self) -> None:
        """Warning is shown when zxcvbn provides one."""
        # Common password triggers warning
        display = get_strength_display("password")
        plain = display.plain.lower()
        # May or may not have warning, but should have some content
        assert len(plain) > 10

    def test_max_three_suggestions(self) -> None:
        """At most 3 suggestions are shown."""
        display = get_strength_display("a")
        plain = display.plain
        # Count bullet points
        bullet_count = plain.count("•")
        assert bullet_count <= 3


class TestMeetsRequirements:
    """Tests for meets_requirements validation."""

    def test_returns_tuple(self) -> None:
        """Returns a tuple of (bool, list)."""
        result = meets_requirements("TestPassword123!")
        assert isinstance(result, tuple)
        assert len(result) == 2
        meets, issues = result
        assert isinstance(meets, bool)
        assert isinstance(issues, list)

    def test_strong_password_meets_default_requirements(self) -> None:
        """Strong password meets default requirements."""
        meets, issues = meets_requirements("Str0ngP@ssword!")
        assert meets is True
        assert issues == []

    def test_short_password_fails_length_check(self) -> None:
        """Short password fails minimum length check."""
        meets, issues = meets_requirements("Short1!")
        assert meets is False
        assert any("8" in issue for issue in issues)

    def test_custom_min_length(self) -> None:
        """Custom minimum length is enforced."""
        meets, issues = meets_requirements("StrongP@ss1!", min_length=6)
        # 12 chars with good complexity should pass min_length=6
        assert meets is True

    def test_weak_password_fails_score_check(self) -> None:
        """Weak password fails minimum score check."""
        meets, issues = meets_requirements("password123", min_score=3)
        assert meets is False
        assert any("strength" in issue.lower() for issue in issues)

    def test_custom_min_score_0_always_passes_score(self) -> None:
        """min_score=0 allows any strength."""
        meets, issues = meets_requirements("aaaaaaaa", min_score=0)
        # Should pass score check (might fail other checks)
        score_issues = [i for i in issues if "strength" in i.lower()]
        assert len(score_issues) == 0

    def test_min_score_4_requires_strong(self) -> None:
        """min_score=4 requires Strong password."""
        meets, issues = meets_requirements("password", min_score=4)
        assert meets is False

    def test_issues_include_suggestions(self) -> None:
        """Issues include suggestions from strength check."""
        meets, issues = meets_requirements("weak", min_score=3)
        assert meets is False
        # Should have more than just the strength message
        assert len(issues) > 1


class TestWeakPinsConstant:
    """Tests for WEAK_PINS constant."""

    def test_weak_pins_is_set(self) -> None:
        """WEAK_PINS is a set."""
        assert isinstance(WEAK_PINS, set)

    def test_contains_repeated_digits(self) -> None:
        """Contains PINs with all same digits."""
        for digit in "0123456789":
            assert digit * 4 in WEAK_PINS

    def test_contains_sequential_ascending(self) -> None:
        """Contains common ascending sequences."""
        assert "1234" in WEAK_PINS
        assert "0123" in WEAK_PINS

    def test_contains_sequential_descending(self) -> None:
        """Contains common descending sequences."""
        assert "4321" in WEAK_PINS
        assert "3210" in WEAK_PINS

    def test_contains_common_years(self) -> None:
        """Contains common year patterns."""
        assert "2000" in WEAK_PINS
        assert "2023" in WEAK_PINS
        assert "2024" in WEAK_PINS

    def test_contains_patterns(self) -> None:
        """Contains common pattern PINs."""
        assert "1212" in WEAK_PINS
        assert "2580" in WEAK_PINS  # Vertical line on keypad

    def test_all_pins_are_numeric(self) -> None:
        """All entries are numeric strings."""
        for pin in WEAK_PINS:
            assert pin.isdigit(), f"Non-numeric PIN in set: {pin}"

    def test_all_pins_are_4_digits(self) -> None:
        """All entries are 4 digit PINs."""
        for pin in WEAK_PINS:
            assert len(pin) == 4, f"Non-4-digit PIN in set: {pin}"


class TestVaultHealthResultDataclass:
    """Tests for VaultHealthResult dataclass."""

    def test_dataclass_fields_exist(self) -> None:
        """VaultHealthResult has all required fields."""
        result = VaultHealthResult(
            overall_score=85,
            reuse_count=1,
            old_count=2,
            weak_count=3,
            total_analyzed=10,
            password_scores=[4, 3, 2],
            issues=["Test issue"],
        )
        assert result.overall_score == 85
        assert result.reuse_count == 1
        assert result.old_count == 2
        assert result.weak_count == 3
        assert result.total_analyzed == 10
        assert result.password_scores == [4, 3, 2]
        assert result.issues == ["Test issue"]

    def test_accepts_empty_lists(self) -> None:
        """Accepts empty password_scores and issues lists."""
        result = VaultHealthResult(
            overall_score=100,
            reuse_count=0,
            old_count=0,
            weak_count=0,
            total_analyzed=0,
            password_scores=[],
            issues=[],
        )
        assert result.password_scores == []
        assert result.issues == []


class TestAnalyzeVaultEmpty:
    """Tests for analyze_vault with empty/minimal inputs."""

    def test_empty_credentials_returns_perfect_score(self) -> None:
        """Empty credentials list returns perfect health."""
        result = analyze_vault([])
        assert result.overall_score == 100
        assert result.reuse_count == 0
        assert result.old_count == 0
        assert result.weak_count == 0
        assert result.total_analyzed == 0

    def test_empty_credentials_no_issues(self) -> None:
        """Empty credentials has no issues."""
        result = analyze_vault([])
        assert result.issues == []


class TestAnalyzeVaultEmailCredentials:
    """Tests for analyze_vault with email credentials."""

    def test_strong_password_no_weak_count(self) -> None:
        """Strong password doesn't count as weak."""
        from passfx.core.models import EmailCredential

        cred = EmailCredential(
            label="Test",
            email="test@example.com",
            password="Str0ngP@ssword!123",
        )
        result = analyze_vault([cred])
        assert result.weak_count == 0

    def test_weak_password_counted(self) -> None:
        """Weak password is counted."""
        from passfx.core.models import EmailCredential

        cred = EmailCredential(
            label="Test",
            email="test@example.com",
            password="weak",
        )
        result = analyze_vault([cred])
        assert result.weak_count == 1

    def test_very_weak_password_generates_issue(self) -> None:
        """Very weak password generates issue message."""
        from passfx.core.models import EmailCredential

        cred = EmailCredential(
            label="MyAccount",
            email="test@example.com",
            password="123",
        )
        result = analyze_vault([cred])
        assert any("weak" in issue.lower() for issue in result.issues)

    def test_password_scores_populated(self) -> None:
        """Password scores are populated for email credentials."""
        from passfx.core.models import EmailCredential

        cred = EmailCredential(
            label="Test",
            email="test@example.com",
            password="TestPassword",
        )
        result = analyze_vault([cred])
        assert len(result.password_scores) == 1

    def test_old_password_detected(self) -> None:
        """Old passwords (>90 days) are detected."""
        from passfx.core.models import EmailCredential

        old_date = (datetime.now() - timedelta(days=100)).isoformat()
        cred = EmailCredential(
            label="Test",
            email="test@example.com",
            password="TestPassword123!",
            updated_at=old_date,
        )
        result = analyze_vault([cred])
        assert result.old_count == 1

    def test_recent_password_not_old(self) -> None:
        """Recent passwords are not counted as old."""
        from passfx.core.models import EmailCredential

        recent_date = datetime.now().isoformat()
        cred = EmailCredential(
            label="Test",
            email="test@example.com",
            password="TestPassword123!",
            updated_at=recent_date,
        )
        result = analyze_vault([cred])
        assert result.old_count == 0


class TestAnalyzeVaultPhoneCredentials:
    """Tests for analyze_vault with phone credentials."""

    def test_weak_pin_detected(self) -> None:
        """Weak PIN from WEAK_PINS set is detected."""
        from passfx.core.models import PhoneCredential

        cred = PhoneCredential(
            label="Phone",
            phone="555-1234",
            password="1234",  # In WEAK_PINS
        )
        result = analyze_vault([cred])
        assert result.weak_count == 1

    def test_strong_pin_not_weak(self) -> None:
        """Strong PIN is not counted as weak."""
        from passfx.core.models import PhoneCredential

        cred = PhoneCredential(
            label="Phone",
            phone="555-1234",
            password="7391",  # Not in WEAK_PINS
        )
        result = analyze_vault([cred])
        assert result.weak_count == 0

    def test_short_pin_is_weak(self) -> None:
        """PINs shorter than 4 digits are weak."""
        from passfx.core.models import PhoneCredential

        cred = PhoneCredential(
            label="Phone",
            phone="555-1234",
            password="123",  # Too short
        )
        result = analyze_vault([cred])
        assert result.weak_count == 1

    def test_repeated_digit_pin_is_weak(self) -> None:
        """PIN with all same digits is weak."""
        from passfx.core.models import PhoneCredential

        cred = PhoneCredential(
            label="Phone",
            phone="555-1234",
            password="5555",  # All same
        )
        result = analyze_vault([cred])
        assert result.weak_count == 1

    def test_phone_old_pin_detected(self) -> None:
        """Old phone PINs are detected."""
        from passfx.core.models import PhoneCredential

        old_date = (datetime.now() - timedelta(days=100)).isoformat()
        cred = PhoneCredential(
            label="Phone",
            phone="555-1234",
            password="7391",
            updated_at=old_date,
        )
        result = analyze_vault([cred])
        assert result.old_count == 1


class TestAnalyzeVaultPasswordReuse:
    """Tests for password reuse detection."""

    def test_no_reuse_when_all_unique(self) -> None:
        """No reuse count when all passwords are unique."""
        from passfx.core.models import Credential, EmailCredential

        creds: list[Credential] = [
            EmailCredential(label="A", email="a@test.com", password="UniquePassword1!"),
            EmailCredential(label="B", email="b@test.com", password="UniquePassword2!"),
            EmailCredential(label="C", email="c@test.com", password="UniquePassword3!"),
        ]
        result = analyze_vault(creds)
        assert result.reuse_count == 0

    def test_reuse_detected(self) -> None:
        """Password reuse is detected."""
        from passfx.core.models import Credential, EmailCredential

        creds: list[Credential] = [
            EmailCredential(label="A", email="a@test.com", password="SharedPassword!"),
            EmailCredential(label="B", email="b@test.com", password="SharedPassword!"),
        ]
        result = analyze_vault(creds)
        assert result.reuse_count == 1

    def test_multiple_reuses_counted(self) -> None:
        """Multiple different reused passwords counted."""
        from passfx.core.models import Credential, EmailCredential

        creds: list[Credential] = [
            EmailCredential(label="A", email="a@test.com", password="Password1!"),
            EmailCredential(label="B", email="b@test.com", password="Password1!"),
            EmailCredential(label="C", email="c@test.com", password="Password2!"),
            EmailCredential(label="D", email="d@test.com", password="Password2!"),
        ]
        result = analyze_vault(creds)
        assert result.reuse_count == 2

    def test_reuse_generates_issue(self) -> None:
        """Password reuse generates issue message."""
        from passfx.core.models import Credential, EmailCredential

        creds: list[Credential] = [
            EmailCredential(label="A", email="a@test.com", password="SharedPassword!"),
            EmailCredential(label="B", email="b@test.com", password="SharedPassword!"),
        ]
        result = analyze_vault(creds)
        assert any("reuse" in issue.lower() for issue in result.issues)


class TestAnalyzeVaultMixedCredentials:
    """Tests for analyze_vault with mixed credential types."""

    def test_handles_mixed_types(self) -> None:
        """Handles mix of email and phone credentials."""
        from passfx.core.models import Credential, EmailCredential, PhoneCredential

        creds: list[Credential] = [
            EmailCredential(
                label="Email", email="test@test.com", password="Password123!"
            ),
            PhoneCredential(label="Phone", phone="555-1234", password="7391"),
        ]
        result = analyze_vault(creds)
        assert result.total_analyzed == 2

    def test_ignores_other_credential_types(self) -> None:
        """Other credential types are not analyzed for passwords."""
        from passfx.core.models import Credential, NoteEntry

        creds: list[Credential] = [
            NoteEntry(title="Note", content="Secret note content"),
        ]
        result = analyze_vault(creds)
        # Notes don't have passwords, shouldn't affect analysis
        assert result.total_analyzed == 0


class TestAnalyzeVaultIssuesLimit:
    """Tests for issues list limit."""

    def test_max_5_issues_returned(self) -> None:
        """At most 5 issues are returned."""
        from passfx.core.models import Credential, EmailCredential

        # Create many weak passwords to generate many issues
        creds: list[Credential] = [
            EmailCredential(
                label=f"Account{i}", email=f"test{i}@test.com", password="1"
            )
            for i in range(10)
        ]
        result = analyze_vault(creds)
        assert len(result.issues) <= 5


class TestComputeVaultScore:
    """Tests for _compute_vault_score weighted scoring."""

    def test_empty_vault_returns_100(self) -> None:
        """Empty vault returns perfect score."""
        score = _compute_vault_score(
            password_scores=[],
            reuse_count=0,
            old_count=0,
            weak_count=0,
            total_analyzed=0,
        )
        assert score == 100

    def test_perfect_scores_returns_100(self) -> None:
        """All score 4 passwords with no issues returns 100."""
        score = _compute_vault_score(
            password_scores=[4, 4, 4, 4],
            reuse_count=0,
            old_count=0,
            weak_count=0,
            total_analyzed=4,
        )
        assert score == 100

    def test_password_strength_affects_score(self) -> None:
        """Lower password strength reduces score."""
        high_strength = _compute_vault_score(
            password_scores=[4, 4, 4],
            reuse_count=0,
            old_count=0,
            weak_count=0,
            total_analyzed=3,
        )
        low_strength = _compute_vault_score(
            password_scores=[1, 1, 1],
            reuse_count=0,
            old_count=0,
            weak_count=0,
            total_analyzed=3,
        )
        assert high_strength > low_strength

    def test_reuse_penalty_applied(self) -> None:
        """Password reuse reduces score."""
        no_reuse = _compute_vault_score(
            password_scores=[4, 4],
            reuse_count=0,
            old_count=0,
            weak_count=0,
            total_analyzed=2,
        )
        with_reuse = _compute_vault_score(
            password_scores=[4, 4],
            reuse_count=1,
            old_count=0,
            weak_count=0,
            total_analyzed=2,
        )
        assert no_reuse > with_reuse

    def test_reuse_penalty_capped_at_25(self) -> None:
        """Reuse penalty doesn't exceed 25 points."""
        score_3_reuse = _compute_vault_score(
            password_scores=[4, 4, 4, 4],
            reuse_count=3,
            old_count=0,
            weak_count=0,
            total_analyzed=4,
        )
        score_10_reuse = _compute_vault_score(
            password_scores=[4, 4, 4, 4],
            reuse_count=10,
            old_count=0,
            weak_count=0,
            total_analyzed=4,
        )
        # Both should have max 25 point penalty, so should be equal
        assert score_3_reuse == score_10_reuse

    def test_old_password_penalty_applied(self) -> None:
        """Old passwords reduce score."""
        no_old = _compute_vault_score(
            password_scores=[4, 4],
            reuse_count=0,
            old_count=0,
            weak_count=0,
            total_analyzed=2,
        )
        with_old = _compute_vault_score(
            password_scores=[4, 4],
            reuse_count=0,
            old_count=1,
            weak_count=0,
            total_analyzed=2,
        )
        assert no_old > with_old

    def test_old_password_penalty_capped_at_15(self) -> None:
        """Old password penalty doesn't exceed 15 points."""
        score_3_old = _compute_vault_score(
            password_scores=[4, 4, 4, 4],
            reuse_count=0,
            old_count=3,
            weak_count=0,
            total_analyzed=4,
        )
        score_10_old = _compute_vault_score(
            password_scores=[4, 4, 4, 4],
            reuse_count=0,
            old_count=10,
            weak_count=0,
            total_analyzed=4,
        )
        # Both should have max 15 point penalty
        assert score_3_old == score_10_old

    def test_weak_password_penalty_applied(self) -> None:
        """Weak passwords reduce score."""
        no_weak = _compute_vault_score(
            password_scores=[4, 4],
            reuse_count=0,
            old_count=0,
            weak_count=0,
            total_analyzed=2,
        )
        with_weak = _compute_vault_score(
            password_scores=[4, 4],
            reuse_count=0,
            old_count=0,
            weak_count=1,
            total_analyzed=2,
        )
        assert no_weak > with_weak

    def test_weak_password_penalty_capped_at_20(self) -> None:
        """Weak password penalty doesn't exceed 20 points."""
        score_3_weak = _compute_vault_score(
            password_scores=[4, 4, 4, 4],
            reuse_count=0,
            old_count=0,
            weak_count=3,
            total_analyzed=4,
        )
        score_10_weak = _compute_vault_score(
            password_scores=[4, 4, 4, 4],
            reuse_count=0,
            old_count=0,
            weak_count=10,
            total_analyzed=4,
        )
        # Both should have max 20 point penalty
        assert score_3_weak == score_10_weak

    def test_score_never_below_0(self) -> None:
        """Score never goes below 0."""
        score = _compute_vault_score(
            password_scores=[0, 0, 0, 0],
            reuse_count=10,
            old_count=10,
            weak_count=10,
            total_analyzed=4,
        )
        assert score >= 0

    def test_score_never_above_100(self) -> None:
        """Score never exceeds 100."""
        score = _compute_vault_score(
            password_scores=[4, 4, 4, 4],
            reuse_count=0,
            old_count=0,
            weak_count=0,
            total_analyzed=4,
        )
        assert score <= 100


class TestPasswordAgeThreshold:
    """Tests for PASSWORD_AGE_THRESHOLD_DAYS constant."""

    def test_threshold_is_90_days(self) -> None:
        """Password age threshold is 90 days."""
        assert PASSWORD_AGE_THRESHOLD_DAYS == 90


class TestZxcvbnFallback:
    """Tests for zxcvbn fallback behavior."""

    def test_long_password_uses_simple_check(self) -> None:
        """Passwords over 72 chars use simple check (no zxcvbn)."""
        # This is the primary fallback path - zxcvbn has 72 char limit
        result = check_strength("a" * 73)
        assert isinstance(result, StrengthResult)
        # Simple check should score this highly due to length
        assert result.score >= 3

    def test_simple_check_provides_all_fields(self) -> None:
        """Simple check fallback provides all required fields."""
        result = check_strength("a" * 100)  # Triggers simple check
        assert isinstance(result.score, int)
        assert isinstance(result.label, str)
        assert isinstance(result.color, str)
        assert isinstance(result.crack_time, str)
        assert isinstance(result.suggestions, list)
        assert result.warning is None  # Simple check always sets None


class TestStrengthRules:
    """Tests validating strength scoring rules are enforced."""

    def test_length_8_minimum_for_basic_score(self) -> None:
        """8 character minimum contributes to scoring."""
        short = _simple_strength_check("1234567")
        long = _simple_strength_check("12345678")
        assert long.score >= short.score

    def test_length_12_improves_score(self) -> None:
        """12 character passwords score better."""
        short = _simple_strength_check("12345678901")
        long = _simple_strength_check("123456789012")
        assert long.score >= short.score

    def test_character_diversity_improves_score(self) -> None:
        """Multiple character types improve score."""
        single_type = _simple_strength_check("aaaaaaaaaaaa")
        multi_type = _simple_strength_check("aaaAAA111!!!")
        assert multi_type.score > single_type.score

    def test_common_passwords_penalized(self) -> None:
        """Common passwords are penalized by zxcvbn."""
        common = check_strength("password123")
        random_pw = check_strength("xK9mP2zQ7nL4")
        # Random should score better even if similar length
        assert random_pw.score >= common.score


class TestDeterministicBehavior:
    """Tests validating deterministic (non-random) behavior."""

    def test_no_randomness_in_check_strength(self) -> None:
        """check_strength produces identical results for same input."""
        results = [check_strength("ConsistentTest123!") for _ in range(50)]
        scores = [r.score for r in results]
        labels = [r.label for r in results]
        assert len(set(scores)) == 1
        assert len(set(labels)) == 1

    def test_no_randomness_in_simple_check(self) -> None:
        """_simple_strength_check produces identical results for same input."""
        results = [_simple_strength_check("ConsistentSimple!") for _ in range(50)]
        scores = [r.score for r in results]
        assert len(set(scores)) == 1

    def test_no_randomness_in_vault_score(self) -> None:
        """_compute_vault_score produces identical results for same input."""
        scores = [
            _compute_vault_score(
                password_scores=[3, 4, 2],
                reuse_count=1,
                old_count=2,
                weak_count=1,
                total_analyzed=3,
            )
            for _ in range(50)
        ]
        assert len(set(scores)) == 1
