"""Password generator for PassFX.

Generates cryptographically secure passwords with configurable options.
"""

from __future__ import annotations

import secrets
import string

# Character sets
LOWERCASE = string.ascii_lowercase
UPPERCASE = string.ascii_uppercase
DIGITS = string.digits
SYMBOLS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
SYMBOLS_SAFE = "!@#$%^&*_+-="  # Symbols less likely to cause issues

# Ambiguous characters that can be confused
AMBIGUOUS = "0O1lI|"


def generate_password(
    length: int = 16,
    use_uppercase: bool = True,
    use_lowercase: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    exclude_ambiguous: bool = False,
    safe_symbols: bool = False,
) -> str:
    """Generate a cryptographically secure random password.

    Args:
        length: Password length (default 16, minimum 4).
        use_uppercase: Include uppercase letters.
        use_lowercase: Include lowercase letters.
        use_digits: Include digits.
        use_symbols: Include special symbols.
        exclude_ambiguous: Exclude ambiguous characters (0, O, 1, l, I, |).
        safe_symbols: Use a safer subset of symbols (less special chars).

    Returns:
        Generated password string.

    Raises:
        ValueError: If length is too short or no character types selected.
    """
    if length < 4:
        raise ValueError("Password length must be at least 4")

    # Build character pool
    pool = ""

    if use_lowercase:
        pool += LOWERCASE
    if use_uppercase:
        pool += UPPERCASE
    if use_digits:
        pool += DIGITS
    if use_symbols:
        pool += SYMBOLS_SAFE if safe_symbols else SYMBOLS

    if not pool:
        raise ValueError("At least one character type must be enabled")

    # Remove ambiguous characters if requested
    if exclude_ambiguous:
        pool = "".join(c for c in pool if c not in AMBIGUOUS)

    if len(pool) < 2:
        raise ValueError("Not enough characters in pool after filtering")

    # Generate password ensuring at least one of each selected type
    password_chars: list[str] = []

    # Add at least one character from each enabled type
    if use_lowercase:
        chars = LOWERCASE if not exclude_ambiguous else LOWERCASE.replace("l", "")
        password_chars.append(secrets.choice(chars))

    if use_uppercase:
        chars = UPPERCASE
        if exclude_ambiguous:
            chars = chars.replace("O", "").replace("I", "")
        password_chars.append(secrets.choice(chars))

    if use_digits:
        chars = DIGITS if not exclude_ambiguous else DIGITS.replace("0", "").replace("1", "")
        password_chars.append(secrets.choice(chars))

    if use_symbols:
        chars = SYMBOLS_SAFE if safe_symbols else SYMBOLS
        if exclude_ambiguous:
            chars = chars.replace("|", "")
        if chars:
            password_chars.append(secrets.choice(chars))

    # Fill remaining length with random characters from pool
    remaining = length - len(password_chars)
    for _ in range(remaining):
        password_chars.append(secrets.choice(pool))

    # Shuffle the password characters
    secrets.SystemRandom().shuffle(password_chars)

    return "".join(password_chars)


def generate_passphrase(
    word_count: int = 4,
    separator: str = "-",
    capitalize: bool = True,
) -> str:
    """Generate a memorable passphrase using common words.

    Args:
        word_count: Number of words (default 4).
        separator: Character between words.
        capitalize: Capitalize first letter of each word.

    Returns:
        Generated passphrase.
    """
    # Common English words for passphrases (curated list)
    words = [
        "apple", "arrow", "beach", "brave", "bread", "brick", "bridge", "brush",
        "candy", "castle", "chair", "cheese", "cherry", "cloud", "clover", "coral",
        "daisy", "dance", "delta", "dream", "eagle", "earth", "ember", "fable",
        "falcon", "flame", "forest", "frost", "garden", "giant", "glass", "glory",
        "grape", "green", "grove", "harbor", "heart", "honey", "horse", "ivory",
        "jewel", "jungle", "karma", "knight", "lemon", "light", "lily", "lotus",
        "magic", "maple", "marble", "meadow", "melody", "mist", "moon", "mosaic",
        "noble", "north", "ocean", "olive", "onyx", "orbit", "orchid", "palace",
        "panda", "pearl", "phoenix", "piano", "pilot", "planet", "plaza", "polar",
        "quartz", "queen", "quest", "rabbit", "rainbow", "raven", "river", "rocket",
        "ruby", "sage", "sailor", "shadow", "silver", "solar", "spark", "spirit",
        "spring", "star", "stone", "storm", "sugar", "summer", "sunset", "swift",
        "temple", "tiger", "titan", "tower", "trail", "treasure", "tree", "tulip",
        "turtle", "twilight", "unity", "valley", "velvet", "violet", "voyage",
        "water", "willow", "winter", "wisdom", "wolf", "wonder", "zenith", "zephyr",
    ]

    selected = [secrets.choice(words) for _ in range(word_count)]

    if capitalize:
        selected = [word.capitalize() for word in selected]

    return separator.join(selected)


def generate_pin(length: int = 4) -> str:
    """Generate a random numeric PIN.

    Args:
        length: PIN length (default 4).

    Returns:
        Generated PIN string.
    """
    if length < 4:
        raise ValueError("PIN length must be at least 4")

    return "".join(secrets.choice(DIGITS) for _ in range(length))


def estimate_crack_time(password: str) -> str:
    """Estimate time to crack a password (rough estimate).

    This is a simplified estimation for display purposes.

    Args:
        password: Password to analyze.

    Returns:
        Human-readable time estimate.
    """
    # Calculate character pool size
    pool_size = 0
    if any(c in LOWERCASE for c in password):
        pool_size += 26
    if any(c in UPPERCASE for c in password):
        pool_size += 26
    if any(c in DIGITS for c in password):
        pool_size += 10
    if any(c in SYMBOLS for c in password):
        pool_size += len(SYMBOLS)

    if pool_size == 0:
        return "instant"

    # Calculate combinations
    combinations = pool_size ** len(password)

    # Assume 10 billion guesses per second (modern GPU)
    guesses_per_second = 10_000_000_000
    seconds = combinations / (2 * guesses_per_second)  # Average case

    # Convert to human readable
    if seconds < 1:
        return "instant"
    elif seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        return f"{int(seconds / 60)} minutes"
    elif seconds < 86400:
        return f"{int(seconds / 3600)} hours"
    elif seconds < 31536000:
        return f"{int(seconds / 86400)} days"
    elif seconds < 31536000 * 100:
        return f"{int(seconds / 31536000)} years"
    elif seconds < 31536000 * 1000:
        return f"{int(seconds / 31536000)} years"
    else:
        return "centuries"
