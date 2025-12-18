"""Password strength checking for PassFX.

Uses zxcvbn for realistic password strength estimation.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from rich.text import Text

if TYPE_CHECKING:
    from passfx.core.models import Credential


@dataclass
class StrengthResult:
    """Password strength analysis result.

    Attributes:
        score: Strength score from 0-4.
        label: Human-readable strength label.
        color: Color for display.
        crack_time: Estimated time to crack.
        suggestions: List of improvement suggestions.
        warning: Warning message if applicable.
    """

    score: int
    label: str
    color: str
    crack_time: str
    suggestions: list[str]
    warning: str | None


STRENGTH_LABELS = {
    0: ("Very Weak", "bright_red"),
    1: ("Weak", "red"),
    2: ("Fair", "yellow"),
    3: ("Good", "bright_green"),
    4: ("Strong", "bold bright_green"),
}


def check_strength(password: str) -> StrengthResult:
    """Check password strength using zxcvbn.

    Args:
        password: Password to analyze.

    Returns:
        StrengthResult with detailed analysis.
    """
    # zxcvbn has a 72 character limit - use simple check for longer passwords
    if len(password) > 72:
        return _simple_strength_check(password)

    try:
        # pylint: disable-next=import-outside-toplevel
        from zxcvbn import zxcvbn  # type: ignore[import-untyped]

        result = zxcvbn(password)

        score = result["score"]
        label, color = STRENGTH_LABELS.get(score, ("Unknown", "white"))

        # Get crack time display
        crack_time = result["crack_times_display"][
            "offline_slow_hashing_1e4_per_second"
        ]

        # Get suggestions
        suggestions = result["feedback"].get("suggestions", [])

        # Get warning
        warning: str | None = result["feedback"].get("warning")
        if warning == "":
            warning = None

        return StrengthResult(
            score=score,
            label=label,
            color=color,
            crack_time=str(crack_time),
            suggestions=suggestions,
            warning=warning,
        )

    except ImportError:
        # Fallback to simple analysis if zxcvbn not available
        return _simple_strength_check(password)
    except Exception:  # pylint: disable=broad-exception-caught
        # Fallback for any other zxcvbn errors
        return _simple_strength_check(password)


# pylint: disable=too-many-branches
def _simple_strength_check(password: str) -> StrengthResult:
    """Simple password strength check without zxcvbn.

    Args:
        password: Password to analyze.

    Returns:
        StrengthResult with basic analysis.
    """
    score = 0
    suggestions = []

    length = len(password)

    # Length scoring - long passwords are inherently strong
    if length >= 8:
        score += 1
    if length >= 12:
        score += 1
    if length >= 16:
        score += 1
    if length >= 24:
        score += 1  # Bonus for very long passwords

    # Complexity scoring
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)

    complexity = sum([has_lower, has_upper, has_digit, has_symbol])
    if complexity >= 3:
        score += 1

    # Cap score at 4
    score = min(score, 4)

    # Generate suggestions
    if length < 12:
        suggestions.append("Use at least 12 characters")
    if not has_upper:
        suggestions.append("Add uppercase letters")
    if not has_lower:
        suggestions.append("Add lowercase letters")
    if not has_digit:
        suggestions.append("Add numbers")
    if not has_symbol:
        suggestions.append("Add special characters")

    label, color = STRENGTH_LABELS.get(score, ("Unknown", "white"))

    # Estimate crack time based on length and complexity
    if length >= 64:
        crack_time = "heat death of the universe"
    elif length >= 32:
        crack_time = "billions of years"
    elif length >= 20:
        crack_time = "millions of years"
    elif score <= 1:
        crack_time = "seconds to minutes"
    elif score == 2:
        crack_time = "hours to days"
    elif score == 3:
        crack_time = "months to years"
    else:
        crack_time = "centuries"

    return StrengthResult(
        score=score,
        label=label,
        color=color,
        crack_time=crack_time,
        suggestions=suggestions,
        warning=None,
    )


def get_strength_bar(score: int, width: int = 10) -> Text:
    """Generate a visual strength bar.

    Args:
        score: Strength score (0-4).
        width: Bar width in characters.

    Returns:
        Rich Text object with colored bar.
    """
    filled = int((score + 1) / 5 * width)
    empty = width - filled

    _, color = STRENGTH_LABELS.get(score, ("", "white"))

    strength_bar = Text()
    strength_bar.append("[")
    strength_bar.append("█" * filled, style=color)
    strength_bar.append("░" * empty, style="dim")
    strength_bar.append("]")

    return strength_bar


def get_strength_display(password: str, show_suggestions: bool = True) -> Text:
    """Get a complete strength display with bar and details.

    Args:
        password: Password to analyze.
        show_suggestions: Whether to include suggestions.

    Returns:
        Rich Text with full strength display.
    """
    result = check_strength(password)

    display = Text()

    # Strength bar
    strength_bar = get_strength_bar(result.score)
    display.append_text(strength_bar)
    display.append(" ")
    display.append(result.label, style=result.color)
    display.append("\n")

    # Crack time
    display.append(f"  Crack time: {result.crack_time}\n", style="dim")

    # Warning
    if result.warning:
        display.append(f"  Warning: {result.warning}\n", style="yellow")

    # Suggestions
    if show_suggestions and result.suggestions:
        display.append("  Tips:\n", style="dim")
        for suggestion in result.suggestions[:3]:  # Max 3 suggestions
            display.append(f"    • {suggestion}\n", style="dim")

    return display


def meets_requirements(
    password: str,
    min_score: int = 2,
    min_length: int = 8,
) -> tuple[bool, list[str]]:
    """Check if password meets minimum requirements.

    Args:
        password: Password to check.
        min_score: Minimum strength score (0-4).
        min_length: Minimum password length.

    Returns:
        Tuple of (meets_requirements, list_of_issues).
    """
    issues = []

    if len(password) < min_length:
        issues.append(f"Password must be at least {min_length} characters")

    result = check_strength(password)

    if result.score < min_score:
        min_label = STRENGTH_LABELS[min_score][0]
        issues.append(f"Password strength is {result.label}, need at least {min_label}")
        issues.extend(result.suggestions[:2])

    return len(issues) == 0, issues


# Password age threshold in days
PASSWORD_AGE_THRESHOLD_DAYS = 90

# Common weak PINs to check against
WEAK_PINS = {
    "0000",
    "1111",
    "2222",
    "3333",
    "4444",
    "5555",
    "6666",
    "7777",
    "8888",
    "9999",
    "1234",
    "4321",
    "1212",
    "2121",
    "1122",
    "2211",
    "0123",
    "3210",
    "9876",
    "6789",
    "1010",
    "2020",
    "1357",
    "2468",
    "1379",
    "2580",
    "0852",
    "1590",
    "7531",
    "8642",
    "0001",
    "0002",
    "0007",
    "0011",
    "0069",
    "0420",
    "1004",
    "1007",
    "2000",
    "2001",
    "2002",
    "2003",
    "2004",
    "2005",
    "2006",
    "2007",
    "2008",
    "2009",
    "2010",
    "2011",
    "2012",
    "2013",
    "2014",
    "2015",
    "2016",
    "2017",
    "2018",
    "2019",
    "2021",
    "2022",
    "2023",
    "2024",
    "2025",
    "6969",
    "4200",
    "1337",
}


@dataclass
class VaultHealthResult:
    """Vault health analysis result.

    Attributes:
        overall_score: Weighted security score from 0-100.
        reuse_count: Number of passwords used in multiple entries.
        old_count: Number of passwords not updated in 90 days.
        weak_count: Number of passwords with strength score < 3.
        total_analyzed: Total number of entries analyzed.
        password_scores: Individual strength scores for histogram display.
        issues: List of specific security issues found.
    """

    overall_score: int
    reuse_count: int
    old_count: int
    weak_count: int
    total_analyzed: int
    password_scores: list[int]
    issues: list[str]


# pylint: disable=too-many-locals
def analyze_vault(credentials: list[Credential]) -> VaultHealthResult:
    """Analyze vault security health across all credentials.

    Performs comprehensive analysis including:
    - Password strength evaluation
    - Password reuse detection
    - Password age analysis (>90 days warning)
    - Weak PIN detection for phone credentials

    Args:
        credentials: List of all vault credentials.

    Returns:
        VaultHealthResult with detailed analysis data.
    """
    # pylint: disable=import-outside-toplevel
    from passfx.core.models import EmailCredential, PhoneCredential

    if not credentials:
        return VaultHealthResult(
            overall_score=100,
            reuse_count=0,
            old_count=0,
            weak_count=0,
            total_analyzed=0,
            password_scores=[],
            issues=[],
        )

    now = datetime.now()
    password_scores: list[int] = []
    all_passwords: list[str] = []
    old_count = 0
    weak_count = 0
    issues: list[str] = []

    # Process email credentials
    for cred in credentials:
        if isinstance(cred, EmailCredential):
            password = cred.password
            all_passwords.append(password)

            # Check strength
            strength = check_strength(password)
            password_scores.append(strength.score)

            if strength.score < 3:
                weak_count += 1
                if strength.score <= 1:
                    issues.append(f"Very weak password: {cred.label}")

            # Check age using updated_at
            try:
                updated = datetime.fromisoformat(cred.updated_at)
                age_days = (now - updated).days
                if age_days > PASSWORD_AGE_THRESHOLD_DAYS:
                    old_count += 1
            except (ValueError, TypeError):
                pass

        elif isinstance(cred, PhoneCredential):
            pin = cred.password
            all_passwords.append(pin)

            # Check for weak PINs
            is_weak_pin = (
                pin in WEAK_PINS
                or len(pin) < 4
                or len(set(pin)) == 1  # All same digits
            )

            if is_weak_pin:
                weak_count += 1
                issues.append(f"Weak PIN: {cred.label}")

            # Check age for PINs too
            try:
                updated = datetime.fromisoformat(cred.updated_at)
                age_days = (now - updated).days
                if age_days > PASSWORD_AGE_THRESHOLD_DAYS:
                    old_count += 1
            except (ValueError, TypeError):
                pass

    # Detect password reuse
    password_counts = Counter(all_passwords)
    reuse_count = sum(1 for count in password_counts.values() if count > 1)

    if reuse_count > 0:
        issues.append(f"{reuse_count} password(s) reused across entries")

    # Calculate overall weighted score
    overall_score = _compute_vault_score(
        password_scores=password_scores,
        reuse_count=reuse_count,
        old_count=old_count,
        weak_count=weak_count,
        total_analyzed=len(all_passwords),
    )

    return VaultHealthResult(
        overall_score=overall_score,
        reuse_count=reuse_count,
        old_count=old_count,
        weak_count=weak_count,
        total_analyzed=len(all_passwords),
        password_scores=password_scores,
        issues=issues[:5],
    )


def _compute_vault_score(
    password_scores: list[int],
    reuse_count: int,
    old_count: int,
    weak_count: int,
    total_analyzed: int,
) -> int:
    """Compute weighted vault security score.

    Weighting:
    - Password strength: 40%
    - Password reuse: 25%
    - Password age: 15%
    - Weak passwords/PINs: 20%

    Args:
        password_scores: List of individual strength scores (0-4).
        reuse_count: Number of reused passwords.
        old_count: Number of old passwords.
        weak_count: Number of weak passwords/PINs.
        total_analyzed: Total credentials analyzed.

    Returns:
        Score from 0-100.
    """
    if total_analyzed == 0:
        return 100

    score = 100.0

    # Password strength component (40% of score)
    if password_scores:
        avg_strength = sum(password_scores) / len(password_scores)
        strength_points = (avg_strength / 4) * 40
        score = score - 40 + strength_points

    # Password reuse penalty (25% of score)
    if reuse_count > 0:
        reuse_penalty = min(25, reuse_count * 10)
        score -= reuse_penalty

    # Password age penalty (15% of score)
    if old_count > 0:
        age_penalty = min(15, old_count * 5)
        score -= age_penalty

    # Weak password/PIN penalty (20% of score)
    if weak_count > 0:
        weak_penalty = min(20, weak_count * 8)
        score -= weak_penalty

    return max(0, min(100, int(score)))
