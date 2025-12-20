"""Search engine for PassFX vault - tiered precision search.

Implements a predictable, intentional search algorithm:
- Tier 1: Exact, prefix, and strong substring matches on primary fields
- Tier 2: Fuzzy matches and secondary field matches (fallback only)

Security: Never searches or exposes password, cvv, or sensitive content fields.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from enum import IntEnum
from typing import Any

from passfx.core.models import (
    Credential,
    CreditCard,
    EmailCredential,
    EnvEntry,
    NoteEntry,
    PhoneCredential,
    RecoveryEntry,
)
from passfx.search.config import (
    SEARCH_CONFIGS,
    SEARCHABLE_FIELDS,
    CredentialType,
    SearchConfig,
)


class FieldWeight(IntEnum):
    """Field importance for search scoring."""

    PRIMARY = 100  # label, title (entry name)
    SECONDARY = 50  # email, phone, cardholder, filename
    TERTIARY = 20  # notes, tags


class MatchTier(IntEnum):
    """Match quality tiers - Tier 1 always preferred over Tier 2."""

    EXACT = 1000  # Exact match on primary field
    PREFIX = 900  # Query is prefix of field value
    STRONG_SUBSTRING = 800  # Query appears in field (word boundary)
    # --- Tier 1 cutoff: scores >= 800 are "hard" matches ---
    WEAK_SUBSTRING = 400  # Query appears anywhere in field
    TOKEN_MATCH = 300  # All query tokens found in entry tokens
    FUZZY = 100  # Edit distance match (typo tolerance)


# Minimum score threshold - results below this are not shown
MIN_RELEVANCE_THRESHOLD = 50

# Tier 1 cutoff - if any result scores at or above this, only show Tier 1
TIER_1_CUTOFF = 700


@dataclass
class SearchResult:
    """A single search result with scoring and display metadata.

    Attributes:
        credential: The matched credential object.
        cred_type: Type identifier for routing and display.
        score: Match quality score (higher = better match).
        primary_text: Main display text (label/title).
        secondary_text: Secondary context (email, phone, etc.) - safe to display.
        icon: Short code for visual identifier.
        accent_color: Theme color for this result type.
        screen_name: Target screen for navigation.
        credential_id: Unique ID for selection.
        matched_field: Which field matched the query.
    """

    credential: Credential
    cred_type: CredentialType
    score: float
    primary_text: str
    secondary_text: str
    icon: str
    accent_color: str
    screen_name: str
    credential_id: str
    matched_field: str


@dataclass
class SearchIndex:
    """Centralized search index for vault credentials.

    Implements tiered search: Tier 1 (hard matches) always preferred.
    Tier 2 (fuzzy/secondary) only shown when Tier 1 returns nothing.
    """

    _entries: list[_IndexEntry] = dataclass_field(default_factory=list)
    _cache_key: str = ""

    def build_index(
        self,
        *,
        emails: list[EmailCredential],
        phones: list[PhoneCredential],
        cards: list[CreditCard],
        envs: list[EnvEntry],
        recovery: list[RecoveryEntry],
        notes: list[NoteEntry],
    ) -> None:
        """Build the search index from all credential types.

        Args:
            emails: List of email credentials.
            phones: List of phone credentials.
            cards: List of credit cards.
            envs: List of environment entries.
            recovery: List of recovery entries.
            notes: List of note entries.
        """
        self._entries.clear()

        # Index each credential type
        self._index_credentials(emails, "email", _email_field_getter)
        self._index_credentials(phones, "phone", _phone_field_getter)
        self._index_credentials(cards, "card", _card_field_getter)
        self._index_credentials(envs, "env", _env_field_getter)
        self._index_credentials(recovery, "recovery", _recovery_field_getter)
        self._index_credentials(notes, "note", _note_field_getter)

        # Update cache key for invalidation tracking
        self._cache_key = (
            f"{len(emails)}_{len(phones)}_{len(cards)}_"
            f"{len(envs)}_{len(recovery)}_{len(notes)}"
        )

    def _index_credentials(
        self,
        credentials: list[Any],
        cred_type: CredentialType,
        field_getter: Callable[[Any, str], str | None],
    ) -> None:
        """Index a list of credentials of the same type.

        Args:
            credentials: List of credential objects.
            cred_type: The credential type identifier.
            field_getter: Function to extract field values from credential.
        """
        config = SEARCH_CONFIGS[cred_type]
        searchable = SEARCHABLE_FIELDS[cred_type]

        for cred in credentials:
            cred_id = getattr(cred, "id", "")
            primary = field_getter(cred, config.primary_field) or ""
            secondary = ""
            if config.secondary_field:
                secondary = field_getter(cred, config.secondary_field) or ""

            # Build searchable text for each field
            for field_name in searchable:
                value = field_getter(cred, field_name)
                if value:
                    normalized = _normalize_text(value)
                    tokens = _tokenize(normalized)

                    # Determine field weight
                    if field_name == config.primary_field:
                        weight = FieldWeight.PRIMARY
                    elif field_name == config.secondary_field:
                        weight = FieldWeight.SECONDARY
                    else:
                        weight = FieldWeight.TERTIARY

                    entry = _IndexEntry(
                        credential=cred,
                        cred_type=cred_type,
                        credential_id=cred_id,
                        field_name=field_name,
                        field_weight=weight,
                        raw_value=value,
                        normalized_value=normalized,
                        tokens=tokens,
                        primary_text=primary,
                        secondary_text=secondary,
                        config=config,
                    )
                    self._entries.append(entry)

    def search(self, query: str, max_results: int = 20) -> list[SearchResult]:
        """Search the index for matching credentials.

        Tiered search algorithm:
        1. First, find all Tier 1 matches (exact, prefix, strong substring on primary)
        2. If Tier 1 has results, return ONLY Tier 1
        3. If Tier 1 is empty, fall back to Tier 2 (fuzzy, secondary fields)
        4. Apply minimum relevance threshold
        5. Sort by score descending

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.

        Returns:
            List of SearchResult objects sorted by score (descending).
        """
        if not query or not query.strip():
            return []

        query_normalized = _normalize_text(query)
        query_tokens = _tokenize(query_normalized)

        if not query_normalized:
            return []

        # Track best score per credential ID to avoid duplicates
        best_scores: dict[str, tuple[float, SearchResult]] = {}

        for entry in self._entries:
            score = self._score_entry(entry, query_normalized, query_tokens)
            if score >= MIN_RELEVANCE_THRESHOLD:
                existing = best_scores.get(entry.credential_id)
                if existing is None or score > existing[0]:
                    result = SearchResult(
                        credential=entry.credential,
                        cred_type=entry.cred_type,
                        score=score,
                        primary_text=entry.primary_text,
                        secondary_text=entry.secondary_text,
                        icon=entry.config.icon,
                        accent_color=entry.config.accent_color,
                        screen_name=entry.config.screen_name,
                        credential_id=entry.credential_id,
                        matched_field=entry.field_name,
                    )
                    best_scores[entry.credential_id] = (score, result)

        # Check if we have any Tier 1 results
        has_tier1 = any(score >= TIER_1_CUTOFF for score, _ in best_scores.values())

        # Filter to Tier 1 only if we have hard matches
        if has_tier1:
            best_scores = {
                cid: (score, result)
                for cid, (score, result) in best_scores.items()
                if score >= TIER_1_CUTOFF
            }

        # Sort by score descending, then by primary text
        results = [r for _, r in best_scores.values()]
        results.sort(key=lambda r: (-r.score, r.primary_text.lower()))

        return results[:max_results]

    def _score_entry(
        self,
        entry: _IndexEntry,
        query_normalized: str,
        query_tokens: list[str],
    ) -> float:
        """Calculate match score for an index entry.

        Scoring considers both match type and field importance.

        Args:
            entry: The index entry to score.
            query_normalized: Normalized query string.
            query_tokens: Tokenized query.

        Returns:
            Match score (0 if no match).
        """
        field_weight = entry.field_weight
        is_primary = field_weight == FieldWeight.PRIMARY

        # 1. EXACT MATCH (Tier 1) - query equals field value
        if query_normalized == entry.normalized_value:
            return MatchTier.EXACT + field_weight

        # 2. PREFIX MATCH (Tier 1) - query is prefix of field value
        if entry.normalized_value.startswith(query_normalized):
            # Boost for more complete matches
            length_ratio = len(query_normalized) / max(len(entry.normalized_value), 1)
            bonus = length_ratio * 50
            return MatchTier.PREFIX + field_weight + bonus

        # 3. STRONG SUBSTRING (Tier 1) - query at word boundary in primary field
        if is_primary and _is_word_boundary_match(
            query_normalized, entry.normalized_value
        ):
            return MatchTier.STRONG_SUBSTRING + field_weight

        # --- Below this line is Tier 2 (fallback only) ---

        # 4. WEAK SUBSTRING (Tier 2) - query appears anywhere
        if query_normalized in entry.normalized_value:
            pos = entry.normalized_value.find(query_normalized)
            position_bonus = max(0, 20 - pos)  # Earlier = better
            return MatchTier.WEAK_SUBSTRING + (field_weight // 2) + position_bonus

        # 5. TOKEN MATCH (Tier 2) - all query tokens match entry tokens
        if query_tokens and _all_tokens_match(query_tokens, entry.tokens):
            return MatchTier.TOKEN_MATCH + (field_weight // 2)

        # 6. FUZZY MATCH (Tier 2) - edit distance for typo tolerance
        # Only for queries >= 4 chars, only on primary field, distance <= 1
        if is_primary and len(query_normalized) >= 4:
            for token in entry.tokens:
                if len(token) >= 4:
                    distance = _levenshtein_bounded(query_normalized, token, 1)
                    if distance is not None and distance <= 1:
                        # Only distance 1 allowed (stricter than before)
                        return MatchTier.FUZZY + field_weight - (distance * 30)

        return 0.0


@dataclass
class _IndexEntry:
    """Internal index entry for a searchable field.

    Not exposed publicly - internal implementation detail.
    """

    credential: Credential
    cred_type: CredentialType
    credential_id: str
    field_name: str
    field_weight: FieldWeight
    raw_value: str
    normalized_value: str
    tokens: list[str]
    primary_text: str
    secondary_text: str
    config: SearchConfig


def _normalize_text(text: str) -> str:
    """Normalize text for search matching.

    - Lowercase
    - Unicode normalization (NFKD)
    - Strip accents
    - Collapse whitespace

    Args:
        text: Input text.

    Returns:
        Normalized text string.
    """
    # Lowercase
    text = text.lower()

    # Unicode normalization - decompose accented characters
    text = unicodedata.normalize("NFKD", text)

    # Remove accent marks (combining characters)
    text = "".join(c for c in text if not unicodedata.combining(c))

    # Collapse whitespace
    text = " ".join(text.split())

    return text


def _tokenize(text: str) -> list[str]:
    """Split text into searchable tokens.

    Splits on whitespace and common delimiters.

    Args:
        text: Normalized text.

    Returns:
        List of tokens.
    """
    # Split on whitespace and common delimiters
    tokens = re.split(r"[\s\-_@.]+", text)
    return [t for t in tokens if t]


def _is_word_boundary_match(query: str, text: str) -> bool:
    """Check if query matches at a word boundary in text.

    A word boundary match means the query starts at the beginning
    of a word (after a delimiter or at start of string).

    Args:
        query: Normalized query string.
        text: Normalized text to search in.

    Returns:
        True if query matches at a word boundary.
    """
    if query not in text:
        return False

    pos = text.find(query)

    # Match at start of string
    if pos == 0:
        return True

    # Match after a word boundary (space, underscore, dash, etc.)
    char_before = text[pos - 1]
    return char_before in " -_@./"


def _all_tokens_match(query_tokens: list[str], entry_tokens: list[str]) -> bool:
    """Check if all query tokens match entry tokens.

    Each query token must be a prefix of at least one entry token.

    Args:
        query_tokens: Tokenized query.
        entry_tokens: Tokenized entry value.

    Returns:
        True if all query tokens match.
    """
    for qt in query_tokens:
        found = False
        for et in entry_tokens:
            if et.startswith(qt):
                found = True
                break
        if not found:
            return False
    return True


def _levenshtein_bounded(s1: str, s2: str, max_dist: int) -> int | None:
    """Compute Levenshtein distance with early termination.

    Stops computation if distance exceeds max_dist.

    Args:
        s1: First string.
        s2: Second string.
        max_dist: Maximum allowed distance.

    Returns:
        Distance if <= max_dist, None otherwise.
    """
    len1, len2 = len(s1), len(s2)

    # Quick length check
    if abs(len1 - len2) > max_dist:
        return None

    # Use shorter string as s1 for efficiency
    if len1 > len2:
        s1, s2 = s2, s1
        len1, len2 = len2, len1

    # Initialize row
    current_row = list(range(len1 + 1))

    for i in range(1, len2 + 1):
        previous_row = current_row
        current_row = [i] + [0] * len1

        # Track minimum in this row for early termination
        row_min = i

        for j in range(1, len1 + 1):
            add = previous_row[j] + 1
            delete = current_row[j - 1] + 1
            change = previous_row[j - 1]

            if s1[j - 1] != s2[i - 1]:
                change += 1

            current_row[j] = min(add, delete, change)
            row_min = min(row_min, current_row[j])

        # Early termination if minimum exceeds threshold
        if row_min > max_dist:
            return None

    result = current_row[len1]
    return result if result <= max_dist else None


# Field getter functions for each credential type
def _email_field_getter(cred: EmailCredential, field: str) -> str | None:
    """Get field value from EmailCredential."""
    if field == "label":
        return cred.label
    if field == "email":
        return cred.email
    if field == "notes":
        return cred.notes
    return None


def _phone_field_getter(cred: PhoneCredential, field: str) -> str | None:
    """Get field value from PhoneCredential."""
    if field == "label":
        return cred.label
    if field == "phone":
        return cred.phone
    if field == "notes":
        return cred.notes
    return None


def _card_field_getter(cred: CreditCard, field: str) -> str | None:
    """Get field value from CreditCard."""
    if field == "label":
        return cred.label
    if field == "cardholder_name":
        return cred.cardholder_name
    if field == "notes":
        return cred.notes
    return None


def _env_field_getter(cred: EnvEntry, field: str) -> str | None:
    """Get field value from EnvEntry."""
    if field == "title":
        return cred.title
    if field == "filename":
        return cred.filename
    if field == "notes":
        return cred.notes
    return None


def _recovery_field_getter(cred: RecoveryEntry, field: str) -> str | None:
    """Get field value from RecoveryEntry."""
    if field == "title":
        return cred.title
    if field == "notes":
        return cred.notes
    return None


def _note_field_getter(cred: NoteEntry, field: str) -> str | None:
    """Get field value from NoteEntry."""
    if field == "title":
        return cred.title
    if field == "notes":
        return cred.notes
    return None
