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
        password: The password (redacted in repr for security).
        notes: Optional notes about this credential.
        id: Unique identifier.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
    """

    label: str
    email: str
    password: str = field(repr=False)
    notes: str | None = None
    id: str = field(default_factory=_generate_id)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def __repr__(self) -> str:
        """Return a safe representation with password redacted."""
        return (
            f"EmailCredential(id={self.id!r}, label={self.label!r}, "
            f"email={self.email!r}, password='[REDACTED]')"
        )

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
        password: PIN or password associated with the phone (redacted in repr).
        notes: Optional notes.
        id: Unique identifier.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
    """

    label: str
    phone: str
    password: str = field(repr=False)
    notes: str | None = None
    id: str = field(default_factory=_generate_id)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def __repr__(self) -> str:
        """Return a safe representation with password redacted."""
        return (
            f"PhoneCredential(id={self.id!r}, label={self.label!r}, "
            f"phone={self.phone!r}, password='[REDACTED]')"
        )

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
class CreditCard:  # pylint: disable=too-many-instance-attributes
    """Credit card information storage.

    Attributes:
        label: Human-readable name (e.g., 'Chase Sapphire').
        card_number: Full card number (redacted in repr).
        expiry: Expiration date (MM/YY format).
        cvv: Card security code (redacted in repr).
        cardholder_name: Name on the card.
        notes: Optional notes.
        id: Unique identifier.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
    """

    label: str
    card_number: str = field(repr=False)
    expiry: str
    cvv: str = field(repr=False)
    cardholder_name: str
    notes: str | None = None
    id: str = field(default_factory=_generate_id)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def __repr__(self) -> str:
        """Return a safe representation with card_number and cvv redacted."""
        return (
            f"CreditCard(id={self.id!r}, label={self.label!r}, "
            f"card_number='[REDACTED]', expiry={self.expiry!r}, "
            f"cvv='[REDACTED]', cardholder_name={self.cardholder_name!r})"
        )

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


@dataclass
class EnvEntry:
    """Environment variable file storage.

    Attributes:
        title: Human-readable name (e.g., 'Project X Production').
        filename: Original filename (e.g., '.env.production').
        content: Full text content of the env file (redacted in repr).
        notes: Optional notes.
        id: Unique identifier.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
    """

    title: str
    filename: str
    content: str = field(repr=False)
    notes: str | None = None
    id: str = field(default_factory=_generate_id)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def __repr__(self) -> str:
        """Return a safe representation with content redacted."""
        return (
            f"EnvEntry(id={self.id!r}, title={self.title!r}, "
            f"filename={self.filename!r}, content='[REDACTED]')"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": "env",
            "id": self.id,
            "title": self.title,
            "filename": self.filename,
            "content": self.content,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnvEntry:
        """Create an instance from a dictionary."""
        return cls(
            id=data.get("id", _generate_id()),
            title=data["title"],
            filename=data["filename"],
            content=data["content"],
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
    def line_count(self) -> int:
        """Return the number of lines in the content."""
        return len(self.content.split("\n")) if self.content else 0

    @property
    def var_count(self) -> int:
        """Return the estimated number of environment variables."""
        if not self.content:
            return 0
        count = 0
        for line in self.content.split("\n"):
            line = line.strip()
            # Count lines that look like KEY=VALUE (ignore comments and empty lines)
            if line and not line.startswith("#") and "=" in line:
                count += 1
        return count


@dataclass
class RecoveryEntry:
    """Recovery codes storage for 2FA backup codes.

    Attributes:
        title: Human-readable name (e.g., 'GitHub 2FA').
        content: Full text content of the recovery codes (redacted in repr).
        notes: Optional notes.
        id: Unique identifier.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
    """

    title: str
    content: str = field(repr=False)
    notes: str | None = None
    id: str = field(default_factory=_generate_id)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def __repr__(self) -> str:
        """Return a safe representation with content redacted."""
        return (
            f"RecoveryEntry(id={self.id!r}, title={self.title!r}, "
            f"content='[REDACTED]')"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": "recovery",
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecoveryEntry:
        """Create an instance from a dictionary."""
        return cls(
            id=data.get("id", _generate_id()),
            title=data["title"],
            content=data["content"],
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
    def line_count(self) -> int:
        """Return the number of lines in the content."""
        return len(self.content.split("\n")) if self.content else 0

    @property
    def code_count(self) -> int:
        """Return the estimated number of recovery codes."""
        if not self.content:
            return 0
        count = 0
        for line in self.content.split("\n"):
            line = line.strip()
            # Count non-empty lines that aren't comments
            if line and not line.startswith("#") and not line.startswith("//"):
                count += 1
        return count


@dataclass
class NoteEntry:
    """Secure note storage for miscellaneous secrets.

    Attributes:
        title: Human-readable name (e.g., 'Office Wi-Fi').
        content: Free text content of the note (redacted in repr).
        notes: Optional additional notes.
        id: Unique identifier.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
    """

    title: str
    content: str = field(repr=False)
    notes: str | None = None
    id: str = field(default_factory=_generate_id)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def __repr__(self) -> str:
        """Return a safe representation with content redacted."""
        return (
            f"NoteEntry(id={self.id!r}, title={self.title!r}, " f"content='[REDACTED]')"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": "note",
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NoteEntry:
        """Create an instance from a dictionary."""
        return cls(
            id=data.get("id", _generate_id()),
            title=data["title"],
            content=data["content"],
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
    def line_count(self) -> int:
        """Return the number of lines in the content."""
        return len(self.content.split("\n")) if self.content else 0

    @property
    def char_count(self) -> int:
        """Return the character count of the content."""
        return len(self.content) if self.content else 0


# Type alias for any credential type
Credential = (
    EmailCredential
    | PhoneCredential
    | CreditCard
    | EnvEntry
    | RecoveryEntry
    | NoteEntry
)


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
    if cred_type == "phone":
        return PhoneCredential.from_dict(data)
    if cred_type == "card":
        return CreditCard.from_dict(data)
    if cred_type == "env":
        return EnvEntry.from_dict(data)
    if cred_type == "recovery":
        return RecoveryEntry.from_dict(data)
    if cred_type == "note":
        return NoteEntry.from_dict(data)
    raise ValueError(f"Unknown credential type: {cred_type}")
