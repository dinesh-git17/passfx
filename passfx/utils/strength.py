"""Password strength checking for PassFX.

Uses zxcvbn for realistic password strength estimation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rich.text import Text


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
        from zxcvbn import zxcvbn

        result = zxcvbn(password)

        score = result["score"]
        label, color = STRENGTH_LABELS.get(score, ("Unknown", "white"))

        # Get crack time display
        crack_time = result["crack_times_display"]["offline_slow_hashing_1e4_per_second"]

        # Get suggestions
        suggestions = result["feedback"].get("suggestions", [])

        # Get warning
        warning = result["feedback"].get("warning")
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
    except Exception:
        # Fallback for any other zxcvbn errors
        return _simple_strength_check(password)


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

    bar = Text()
    bar.append("[")
    bar.append("█" * filled, style=color)
    bar.append("░" * empty, style="dim")
    bar.append("]")

    return bar


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
    bar = get_strength_bar(result.score)
    display.append_text(bar)
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
        issues.append(f"Password strength is {result.label}, need at least {STRENGTH_LABELS[min_score][0]}")
        issues.extend(result.suggestions[:2])

    return len(issues) == 0, issues
