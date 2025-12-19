"""Search engine for PassFX vault - hybrid search with scoring.

Implements a performant search algorithm optimized for TUI responsiveness:
1. Normalized prefix match (highest priority)
2. Substring match
3. Token-based fuzzy match
4. Bounded Levenshtein distance for typo tolerance

Security: Never searches or exposes password, cvv, or sensitive content fields.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dataclass_field
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

    Maintains an in-memory index of searchable credential data.
    Supports incremental updates when credentials change.
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
        self._cache_key = f"{len(emails)}_{len(phones)}_{len(cards)}_{len(envs)}_{len(recovery)}_{len(notes)}"

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

                    entry = _IndexEntry(
                        credential=cred,
                        cred_type=cred_type,
                        credential_id=cred_id,
                        field_name=field_name,
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

        Uses hybrid scoring:
        1. Exact prefix match on primary field = 100 points
        2. Exact prefix match on other fields = 80 points
        3. Substring match on primary field = 60 points
        4. Substring match on other fields = 40 points
        5. Token match = 30 points
        6. Fuzzy match (Levenshtein <= 2) = 20 points

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

        # Track best score per credential ID to avoid duplicates
        best_scores: dict[str, tuple[float, SearchResult]] = {}

        for entry in self._entries:
            score = self._score_entry(entry, query_normalized, query_tokens)
            if score > 0:
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

        Args:
            entry: The index entry to score.
            query_normalized: Normalized query string.
            query_tokens: Tokenized query.

        Returns:
            Match score (0 if no match).
        """
        score = 0.0
        is_primary = entry.field_name == entry.config.primary_field

        # 1. Exact prefix match (highest priority)
        if entry.normalized_value.startswith(query_normalized):
            score = 100.0 if is_primary else 80.0
            # Boost shorter matches (more precise)
            length_ratio = len(query_normalized) / max(len(entry.normalized_value), 1)
            score += length_ratio * 10
            return score

        # 2. Substring match
        if query_normalized in entry.normalized_value:
            score = 60.0 if is_primary else 40.0
            # Boost earlier matches
            pos = entry.normalized_value.find(query_normalized)
            position_bonus = max(0, 10 - pos)
            score += position_bonus
            return score

        # 3. Token match - all query tokens must match
        if query_tokens:
            matched_tokens = 0
            for qt in query_tokens:
                for et in entry.tokens:
                    if et.startswith(qt) or qt in et:
                        matched_tokens += 1
                        break

            if matched_tokens == len(query_tokens):
                score = 30.0 if is_primary else 25.0
                return score

        # 4. Fuzzy match (bounded Levenshtein for typo tolerance)
        # Only for queries >= 3 chars to avoid noise
        if len(query_normalized) >= 3:
            # Check against each token
            for token in entry.tokens:
                if len(token) >= 3:
                    distance = _levenshtein_bounded(query_normalized, token, 2)
                    if distance is not None and distance <= 2:
                        score = 20.0 - (
                            distance * 5
                        )  # 20 for d=0, 15 for d=1, 10 for d=2
                        return max(score, 0)

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
