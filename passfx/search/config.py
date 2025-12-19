"""Search configuration for PassFX vault search system.

Defines searchable fields per credential type and display configuration.
Security-first: never index sensitive fields (password, cvv, content with secrets).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Type alias for credential categories
CredentialType = Literal["email", "phone", "card", "env", "recovery", "note"]

# Searchable fields per credential type - NEVER include sensitive data
# These fields are safe to display in search results
SEARCHABLE_FIELDS: dict[CredentialType, list[str]] = {
    "email": ["label", "email", "notes"],
    "phone": ["label", "phone", "notes"],
    "card": ["label", "cardholder_name", "notes"],
    "env": ["title", "filename", "notes"],
    "recovery": ["title", "notes"],
    "note": ["title", "notes"],
}

# Display icons for each credential type - Operator theme aesthetic
CREDENTIAL_ICONS: dict[CredentialType, str] = {
    "email": "KEY",
    "phone": "PIN",
    "card": "CRD",
    "env": "ENV",
    "recovery": "SOS",
    "note": "MEM",
}

# Screen names for navigation
SCREEN_NAMES: dict[CredentialType, str] = {
    "email": "passwords",
    "phone": "phones",
    "card": "cards",
    "env": "envs",
    "recovery": "recovery",
    "note": "notes",
}

# Accent colors per credential type - matches existing screen themes
ACCENT_COLORS: dict[CredentialType, str] = {
    "email": "#8b5cf6",  # Purple - passwords
    "phone": "#ec4899",  # Pink - phones
    "card": "#22c55e",  # Green - cards
    "env": "#f59e0b",  # Amber - env vars
    "recovery": "#ef4444",  # Red - recovery
    "note": "#3b82f6",  # Blue - notes
}


@dataclass(frozen=True)
class SearchConfig:
    """Configuration for a searchable credential type.

    Attributes:
        cred_type: The credential type identifier.
        searchable_fields: List of field names safe to search and display.
        primary_field: Main field for display (typically label/title).
        secondary_field: Secondary context field (email, phone, filename).
        icon: Short code for visual identifier.
        accent_color: Theme color for this credential type.
        screen_name: Name of the screen to navigate to.
    """

    cred_type: CredentialType
    searchable_fields: list[str]
    primary_field: str
    secondary_field: str | None
    icon: str
    accent_color: str
    screen_name: str

    @classmethod
    def for_type(cls, cred_type: CredentialType) -> SearchConfig:
        """Create SearchConfig for a credential type.

        Args:
            cred_type: The credential type to configure.

        Returns:
            SearchConfig instance for the specified type.
        """
        primary_map = {
            "email": "label",
            "phone": "label",
            "card": "label",
            "env": "title",
            "recovery": "title",
            "note": "title",
        }
        secondary_map: dict[CredentialType, str | None] = {
            "email": "email",
            "phone": "phone",
            "card": "cardholder_name",
            "env": "filename",
            "recovery": None,
            "note": None,
        }

        return cls(
            cred_type=cred_type,
            searchable_fields=SEARCHABLE_FIELDS[cred_type],
            primary_field=primary_map[cred_type],
            secondary_field=secondary_map[cred_type],
            icon=CREDENTIAL_ICONS[cred_type],
            accent_color=ACCENT_COLORS[cred_type],
            screen_name=SCREEN_NAMES[cred_type],
        )


# Pre-built configs for each type
_CRED_TYPES: list[CredentialType] = [
    "email",
    "phone",
    "card",
    "env",
    "recovery",
    "note",
]
SEARCH_CONFIGS: dict[CredentialType, SearchConfig] = {
    cred_type: SearchConfig.for_type(cred_type) for cred_type in _CRED_TYPES
}
