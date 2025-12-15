"""Data models for PassFX vault entries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _generate_id() -> str:
    """Generate a unique ID for vault entries."""
    return str(uuid.uuid4())[:8]


def _now_iso() -> str:
    """Return current timestamp in ISO format."""
    return datetime.now().isoformat()


@dataclass
class EmailCredential:
    """Credential for email/username + password combinations.

    Attributes:
        label: Human-readable name for this credential (e.g., 'GitHub').
        email: Email address or username.
        password: The password.
        notes: Optional notes about this credential.
        id: Unique identifier.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
    """

    label: str
    email: str
    password: str
    notes: str | None = None
    id: str = field(default_factory=_generate_id)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": "email",
            "id": self.id,
            "label": self.label,
            "email": self.email,
            "password": self.password,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmailCredential:
        """Create an instance from a dictionary."""
        return cls(
            id=data.get("id", _generate_id()),
            label=data["label"],
            email=data["email"],
            password=data["password"],
            notes=data.get("notes"),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
        )

    def update(self, **kwargs: Any) -> None:
        """Update fields and refresh updated_at timestamp."""
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ("id", "created_at"):
                setattr(self, key, value)
        self.updated_at = _now_iso()


@dataclass
class PhoneCredential:
    """Credential for phone number + PIN/password combinations.

    Attributes:
        label: Human-readable name (e.g., 'Bank Phone PIN').
        phone: Phone number.
        password: PIN or password associated with the phone.
        notes: Optional notes.
        id: Unique identifier.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
    """

    label: str
    phone: str
    password: str
    notes: str | None = None
    id: str = field(default_factory=_generate_id)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": "phone",
            "id": self.id,
            "label": self.label,
            "phone": self.phone,
            "password": self.password,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PhoneCredential:
        """Create an instance from a dictionary."""
        return cls(
            id=data.get("id", _generate_id()),
            label=data["label"],
            phone=data["phone"],
            password=data["password"],
            notes=data.get("notes"),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
        )

    def update(self, **kwargs: Any) -> None:
        """Update fields and refresh updated_at timestamp."""
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ("id", "created_at"):
                setattr(self, key, value)
        self.updated_at = _now_iso()


@dataclass
class CreditCard:
    """Credit card information storage.

    Attributes:
        label: Human-readable name (e.g., 'Chase Sapphire').
        card_number: Full card number.
        expiry: Expiration date (MM/YY format).
        cvv: Card security code.
        cardholder_name: Name on the card.
        notes: Optional notes.
        id: Unique identifier.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
    """

    label: str
    card_number: str
    expiry: str
    cvv: str
    cardholder_name: str
    notes: str | None = None
    id: str = field(default_factory=_generate_id)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": "card",
            "id": self.id,
            "label": self.label,
            "card_number": self.card_number,
            "expiry": self.expiry,
            "cvv": self.cvv,
            "cardholder_name": self.cardholder_name,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CreditCard:
        """Create an instance from a dictionary."""
        return cls(
            id=data.get("id", _generate_id()),
            label=data["label"],
            card_number=data["card_number"],
            expiry=data["expiry"],
            cvv=data["cvv"],
            cardholder_name=data["cardholder_name"],
            notes=data.get("notes"),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
        )

    def update(self, **kwargs: Any) -> None:
        """Update fields and refresh updated_at timestamp."""
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ("id", "created_at"):
                setattr(self, key, value)
        self.updated_at = _now_iso()

    @property
    def masked_number(self) -> str:
        """Return masked card number showing only last 4 digits."""
        digits = "".join(filter(str.isdigit, self.card_number))
        if len(digits) < 4:
            return "•" * len(digits)
        return f"•••• •••• •••• {digits[-4:]}"


# Type alias for any credential type
Credential = EmailCredential | PhoneCredential | CreditCard


def credential_from_dict(data: dict[str, Any]) -> Credential:
    """Create appropriate credential type from dictionary.

    Args:
        data: Dictionary with 'type' field indicating credential type.

    Returns:
        Appropriate credential instance.

    Raises:
        ValueError: If type is unknown.
    """
    cred_type = data.get("type", "email")

    if cred_type == "email":
        return EmailCredential.from_dict(data)
    elif cred_type == "phone":
        return PhoneCredential.from_dict(data)
    elif cred_type == "card":
        return CreditCard.from_dict(data)
    else:
        raise ValueError(f"Unknown credential type: {cred_type}")
