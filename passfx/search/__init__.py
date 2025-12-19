"""Search module for PassFX - centralized vault search engine."""

from passfx.search.config import (
    CREDENTIAL_ICONS,
    SEARCHABLE_FIELDS,
    CredentialType,
    SearchConfig,
)
from passfx.search.engine import SearchIndex, SearchResult

__all__ = [
    "CREDENTIAL_ICONS",
    "SEARCHABLE_FIELDS",
    "CredentialType",
    "SearchConfig",
    "SearchIndex",
    "SearchResult",
]
