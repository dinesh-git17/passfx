"""Vault management for PassFX - encrypted storage of credentials."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from passfx.core.crypto import CryptoManager, DecryptionError, generate_salt
from passfx.core.models import (
    Credential,
    CreditCard,
    EmailCredential,
    EnvEntry,
    NoteEntry,
    PhoneCredential,
    RecoveryEntry,
)

# Default vault location
DEFAULT_VAULT_DIR = Path.home() / ".passfx"
DEFAULT_VAULT_FILE = DEFAULT_VAULT_DIR / "vault.enc"
SALT_FILE = DEFAULT_VAULT_DIR / "salt"
CONFIG_FILE = DEFAULT_VAULT_DIR / "config.json"


class VaultError(Exception):
    """Base exception for vault operations."""


class VaultNotFoundError(VaultError):
    """Raised when vault file doesn't exist."""


class VaultCorruptedError(VaultError):
    """Raised when vault data is corrupted."""


class Vault:  # pylint: disable=too-many-public-methods
    """Manages encrypted credential storage.

    The vault stores credentials in an encrypted JSON file. The encryption
    key is derived from the master password using PBKDF2.

    Attributes:
        path: Path to the encrypted vault file.
        is_locked: Whether the vault is currently locked.
    """

    def __init__(
        self,
        vault_path: Path | None = None,
        salt_path: Path | None = None,
    ) -> None:
        """Initialize the vault.

        Args:
            vault_path: Path to vault file. Defaults to ~/.passfx/vault.enc.
            salt_path: Path to salt file. Defaults to ~/.passfx/salt.
        """
        self.path = vault_path or DEFAULT_VAULT_FILE
        self._salt_path = salt_path or SALT_FILE
        self._crypto: CryptoManager | None = None
        self._data: dict[str, list[dict[str, Any]]] = {
            "emails": [],
            "phones": [],
            "cards": [],
            "envs": [],
            "recovery": [],
            "notes": [],
        }
        self._last_activity: float = 0
        self._lock_timeout: int = 300  # 5 minutes default

    @property
    def is_locked(self) -> bool:
        """Check if the vault is locked."""
        return self._crypto is None

    @property
    def exists(self) -> bool:
        """Check if the vault file exists."""
        return self.path.exists()

    def _ensure_vault_dir(self) -> None:
        """Ensure the vault directory exists with proper permissions."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Set directory permissions to owner-only on Unix
        if os.name != "nt":
            os.chmod(self.path.parent, 0o700)

    def _load_salt(self) -> bytes | None:
        """Load salt from file if it exists."""
        if self._salt_path.exists():
            return self._salt_path.read_bytes()
        return None

    def _save_salt(self, salt: bytes) -> None:
        """Save salt to file."""
        self._ensure_vault_dir()
        self._salt_path.write_bytes(salt)
        if os.name != "nt":
            os.chmod(self._salt_path, 0o600)

    def create(self, master_password: str) -> None:
        """Create a new vault with the given master password.

        Args:
            master_password: The master password for the vault.

        Raises:
            VaultError: If vault already exists.
        """
        if self.exists:
            raise VaultError("Vault already exists. Use unlock() instead.")

        self._ensure_vault_dir()

        # Generate and save salt
        salt = generate_salt()
        self._save_salt(salt)

        # Initialize crypto with new salt
        self._crypto = CryptoManager(master_password, salt)

        # Initialize empty data
        self._data = {
            "emails": [],
            "phones": [],
            "cards": [],
            "envs": [],
            "recovery": [],
            "notes": [],
        }

        # Save empty vault
        self._save()
        self._update_activity()

    def unlock(self, master_password: str) -> None:
        """Unlock an existing vault.

        Args:
            master_password: The master password.

        Raises:
            VaultNotFoundError: If vault doesn't exist.
            DecryptionError: If password is wrong.
        """
        if not self.exists:
            raise VaultNotFoundError("No vault found. Create one first.")

        salt = self._load_salt()
        if salt is None:
            raise VaultCorruptedError("Salt file missing. Vault may be corrupted.")

        self._crypto = CryptoManager(master_password, salt)

        # Try to decrypt and load data
        try:
            encrypted_data = self.path.read_bytes()
            decrypted = self._crypto.decrypt(encrypted_data)
            self._data = json.loads(decrypted.decode("utf-8"))
            # Migrate older vaults that don't have "envs" key
            if "envs" not in self._data:
                self._data["envs"] = []
            # Migrate older vaults that don't have "recovery" key
            if "recovery" not in self._data:
                self._data["recovery"] = []
            # Migrate older vaults that don't have "notes" key
            if "notes" not in self._data:
                self._data["notes"] = []
            self._update_activity()
        except DecryptionError:
            self._crypto = None
            raise
        except json.JSONDecodeError as e:
            self._crypto = None
            raise VaultCorruptedError("Vault data is corrupted.") from e

    def lock(self) -> None:
        """Lock the vault and wipe sensitive data from memory."""
        if self._crypto:
            self._crypto.wipe()
            self._crypto = None
        self._data = {
            "emails": [],
            "phones": [],
            "cards": [],
            "envs": [],
            "recovery": [],
            "notes": [],
        }

    def _save(self) -> None:
        """Save the vault to disk with atomic write and backup.

        Uses temp file + fsync + atomic rename pattern to prevent data loss
        on crash or power failure. Creates a backup of the existing vault
        before overwriting.
        """
        if self._crypto is None:
            raise VaultError("Vault is locked. Unlock first.")

        self._ensure_vault_dir()
        data_json = json.dumps(self._data, indent=2)
        encrypted = self._crypto.encrypt(data_json.encode("utf-8"))

        # Create backup of existing vault before overwriting
        if self.path.exists():
            self._create_backup()

        # Atomic write: temp file -> fsync -> rename
        self._atomic_write(encrypted)

    def _create_backup(self) -> None:
        """Create a backup copy of the vault before overwriting.

        Backup is stored as vault.enc.bak with preserved permissions.
        """
        backup_path = self.path.with_suffix(".enc.bak")
        # Use shutil.copy2 to preserve metadata, then enforce permissions
        shutil.copy2(self.path, backup_path)
        if os.name != "nt":
            os.chmod(backup_path, 0o600)

    def _atomic_write(self, data: bytes) -> None:
        """Write data atomically using temp file + fsync + rename.

        This pattern ensures that a crash at any point leaves either
        the old vault intact or the new vault fully written.
        """
        vault_dir = self.path.parent

        # Create temp file in same directory for atomic rename
        fd, temp_path = tempfile.mkstemp(
            dir=vault_dir,
            prefix=".vault_",
            suffix=".tmp",
        )
        try:
            # Write and sync data to temp file
            os.write(fd, data)
            os.fsync(fd)
            os.close(fd)

            # Set permissions before rename (temp file inherits umask)
            if os.name != "nt":
                os.chmod(temp_path, 0o600)

            # Atomic rename - replaces target atomically on POSIX
            os.replace(temp_path, self.path)

            # Sync directory to ensure rename is persisted
            self._fsync_directory(vault_dir)

        except Exception:
            # Clean up temp file on failure
            if not self._is_fd_closed(fd):
                os.close(fd)
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def _fsync_directory(self, directory: Path) -> None:
        """Sync directory to ensure file renames are persisted.

        On POSIX systems, fsync on the directory ensures that directory
        entries are written to disk. No-op on Windows.
        """
        if os.name == "nt":
            return

        dir_fd = os.open(str(directory), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)

    @staticmethod
    def _is_fd_closed(fd: int) -> bool:
        """Check if a file descriptor is already closed."""
        try:
            os.fstat(fd)
            return False
        except OSError:
            return True

    def _update_activity(self) -> None:
        """Update last activity timestamp."""
        self._last_activity = time.time()

    def check_timeout(self) -> bool:
        """Check if the vault should auto-lock due to inactivity.

        Returns:
            True if vault should be locked, False otherwise.
        """
        if self._lock_timeout <= 0:
            return False
        return time.time() - self._last_activity > self._lock_timeout

    def set_lock_timeout(self, seconds: int) -> None:
        """Set the auto-lock timeout.

        Args:
            seconds: Timeout in seconds. 0 to disable.
        """
        self._lock_timeout = seconds

    # --- Email Credentials ---

    def add_email(self, credential: EmailCredential) -> None:
        """Add an email credential to the vault."""
        self._update_activity()
        self._data["emails"].append(credential.to_dict())
        self._save()

    def get_emails(self) -> list[EmailCredential]:
        """Get all email credentials."""
        self._update_activity()
        return [EmailCredential.from_dict(d) for d in self._data["emails"]]

    def get_email_by_id(self, entry_id: str) -> EmailCredential | None:
        """Get an email credential by ID."""
        self._update_activity()
        for d in self._data["emails"]:
            if d.get("id") == entry_id:
                return EmailCredential.from_dict(d)
        return None

    def update_email(self, entry_id: str, **kwargs: Any) -> bool:
        """Update an email credential."""
        self._update_activity()
        for i, d in enumerate(self._data["emails"]):
            if d.get("id") == entry_id:
                cred = EmailCredential.from_dict(d)
                cred.update(**kwargs)
                self._data["emails"][i] = cred.to_dict()
                self._save()
                return True
        return False

    def delete_email(self, entry_id: str) -> bool:
        """Delete an email credential."""
        self._update_activity()
        for i, d in enumerate(self._data["emails"]):
            if d.get("id") == entry_id:
                del self._data["emails"][i]
                self._save()
                return True
        return False

    # --- Phone Credentials ---

    def add_phone(self, credential: PhoneCredential) -> None:
        """Add a phone credential to the vault."""
        self._update_activity()
        self._data["phones"].append(credential.to_dict())
        self._save()

    def get_phones(self) -> list[PhoneCredential]:
        """Get all phone credentials."""
        self._update_activity()
        return [PhoneCredential.from_dict(d) for d in self._data["phones"]]

    def get_phone_by_id(self, entry_id: str) -> PhoneCredential | None:
        """Get a phone credential by ID."""
        self._update_activity()
        for d in self._data["phones"]:
            if d.get("id") == entry_id:
                return PhoneCredential.from_dict(d)
        return None

    def update_phone(self, entry_id: str, **kwargs: Any) -> bool:
        """Update a phone credential."""
        self._update_activity()
        for i, d in enumerate(self._data["phones"]):
            if d.get("id") == entry_id:
                cred = PhoneCredential.from_dict(d)
                cred.update(**kwargs)
                self._data["phones"][i] = cred.to_dict()
                self._save()
                return True
        return False

    def delete_phone(self, entry_id: str) -> bool:
        """Delete a phone credential."""
        self._update_activity()
        for i, d in enumerate(self._data["phones"]):
            if d.get("id") == entry_id:
                del self._data["phones"][i]
                self._save()
                return True
        return False

    # --- Credit Cards ---

    def add_card(self, card: CreditCard) -> None:
        """Add a credit card to the vault."""
        self._update_activity()
        self._data["cards"].append(card.to_dict())
        self._save()

    def get_cards(self) -> list[CreditCard]:
        """Get all credit cards."""
        self._update_activity()
        return [CreditCard.from_dict(d) for d in self._data["cards"]]

    def get_card_by_id(self, entry_id: str) -> CreditCard | None:
        """Get a credit card by ID."""
        self._update_activity()
        for d in self._data["cards"]:
            if d.get("id") == entry_id:
                return CreditCard.from_dict(d)
        return None

    def update_card(self, entry_id: str, **kwargs: Any) -> bool:
        """Update a credit card."""
        self._update_activity()
        for i, d in enumerate(self._data["cards"]):
            if d.get("id") == entry_id:
                card = CreditCard.from_dict(d)
                card.update(**kwargs)
                self._data["cards"][i] = card.to_dict()
                self._save()
                return True
        return False

    def delete_card(self, entry_id: str) -> bool:
        """Delete a credit card."""
        self._update_activity()
        for i, d in enumerate(self._data["cards"]):
            if d.get("id") == entry_id:
                del self._data["cards"][i]
                self._save()
                return True
        return False

    # --- Environment Variables ---

    def add_env(self, env: EnvEntry) -> None:
        """Add an environment entry to the vault."""
        self._update_activity()
        if "envs" not in self._data:
            self._data["envs"] = []
        self._data["envs"].append(env.to_dict())
        self._save()

    def get_envs(self) -> list[EnvEntry]:
        """Get all environment entries."""
        self._update_activity()
        return [EnvEntry.from_dict(d) for d in self._data.get("envs", [])]

    def get_env_by_id(self, entry_id: str) -> EnvEntry | None:
        """Get an environment entry by ID."""
        self._update_activity()
        for d in self._data.get("envs", []):
            if d.get("id") == entry_id:
                return EnvEntry.from_dict(d)
        return None

    def update_env(self, entry_id: str, **kwargs: Any) -> bool:
        """Update an environment entry."""
        self._update_activity()
        for i, d in enumerate(self._data.get("envs", [])):
            if d.get("id") == entry_id:
                env = EnvEntry.from_dict(d)
                env.update(**kwargs)
                self._data["envs"][i] = env.to_dict()
                self._save()
                return True
        return False

    def delete_env(self, entry_id: str) -> bool:
        """Delete an environment entry."""
        self._update_activity()
        for i, d in enumerate(self._data.get("envs", [])):
            if d.get("id") == entry_id:
                del self._data["envs"][i]
                self._save()
                return True
        return False

    # --- Recovery Codes ---

    def add_recovery(self, recovery: RecoveryEntry) -> None:
        """Add a recovery entry to the vault."""
        self._update_activity()
        if "recovery" not in self._data:
            self._data["recovery"] = []
        self._data["recovery"].append(recovery.to_dict())
        self._save()

    def get_recovery_entries(self) -> list[RecoveryEntry]:
        """Get all recovery entries."""
        self._update_activity()
        return [RecoveryEntry.from_dict(d) for d in self._data.get("recovery", [])]

    def get_recovery_by_id(self, entry_id: str) -> RecoveryEntry | None:
        """Get a recovery entry by ID."""
        self._update_activity()
        for d in self._data.get("recovery", []):
            if d.get("id") == entry_id:
                return RecoveryEntry.from_dict(d)
        return None

    def update_recovery(self, entry_id: str, **kwargs: Any) -> bool:
        """Update a recovery entry."""
        self._update_activity()
        for i, d in enumerate(self._data.get("recovery", [])):
            if d.get("id") == entry_id:
                recovery = RecoveryEntry.from_dict(d)
                recovery.update(**kwargs)
                self._data["recovery"][i] = recovery.to_dict()
                self._save()
                return True
        return False

    def delete_recovery(self, entry_id: str) -> bool:
        """Delete a recovery entry."""
        self._update_activity()
        for i, d in enumerate(self._data.get("recovery", [])):
            if d.get("id") == entry_id:
                del self._data["recovery"][i]
                self._save()
                return True
        return False

    # --- Secure Notes ---

    def add_note(self, note: NoteEntry) -> None:
        """Add a secure note to the vault."""
        self._update_activity()
        if "notes" not in self._data:
            self._data["notes"] = []
        self._data["notes"].append(note.to_dict())
        self._save()

    def get_notes(self) -> list[NoteEntry]:
        """Get all secure notes."""
        self._update_activity()
        return [NoteEntry.from_dict(d) for d in self._data.get("notes", [])]

    def get_note_by_id(self, entry_id: str) -> NoteEntry | None:
        """Get a secure note by ID."""
        self._update_activity()
        for d in self._data.get("notes", []):
            if d.get("id") == entry_id:
                return NoteEntry.from_dict(d)
        return None

    def update_note(self, entry_id: str, **kwargs: Any) -> bool:
        """Update a secure note."""
        self._update_activity()
        for i, d in enumerate(self._data.get("notes", [])):
            if d.get("id") == entry_id:
                note = NoteEntry.from_dict(d)
                note.update(**kwargs)
                self._data["notes"][i] = note.to_dict()
                self._save()
                return True
        return False

    def delete_note(self, entry_id: str) -> bool:
        """Delete a secure note."""
        self._update_activity()
        for i, d in enumerate(self._data.get("notes", [])):
            if d.get("id") == entry_id:
                del self._data["notes"][i]
                self._save()
                return True
        return False

    # --- Search ---

    def search(self, query: str) -> list[Credential]:
        """Search all credentials by label, email, phone, cardholder name, or env title.

        Args:
            query: Search query (case-insensitive).

        Returns:
            List of matching credentials.
        """
        self._update_activity()
        query_lower = query.lower()
        results: list[Credential] = []

        for d in self._data["emails"]:
            if (
                query_lower in d.get("label", "").lower()
                or query_lower in d.get("email", "").lower()
                or query_lower in (d.get("notes") or "").lower()
            ):
                results.append(EmailCredential.from_dict(d))

        for d in self._data["phones"]:
            if (
                query_lower in d.get("label", "").lower()
                or query_lower in d.get("phone", "").lower()
                or query_lower in (d.get("notes") or "").lower()
            ):
                results.append(PhoneCredential.from_dict(d))

        for d in self._data["cards"]:
            if (
                query_lower in d.get("label", "").lower()
                or query_lower in d.get("cardholder_name", "").lower()
                or query_lower in (d.get("notes") or "").lower()
            ):
                results.append(CreditCard.from_dict(d))

        for d in self._data.get("envs", []):
            if (
                query_lower in d.get("title", "").lower()
                or query_lower in d.get("filename", "").lower()
                or query_lower in d.get("content", "").lower()
                or query_lower in (d.get("notes") or "").lower()
            ):
                results.append(EnvEntry.from_dict(d))

        for d in self._data.get("recovery", []):
            if (
                query_lower in d.get("title", "").lower()
                or query_lower in d.get("content", "").lower()
                or query_lower in (d.get("notes") or "").lower()
            ):
                results.append(RecoveryEntry.from_dict(d))

        for d in self._data.get("notes", []):
            if (
                query_lower in d.get("title", "").lower()
                or query_lower in d.get("content", "").lower()
                or query_lower in (d.get("notes") or "").lower()
            ):
                results.append(NoteEntry.from_dict(d))

        return results

    # --- Stats ---

    def get_stats(self) -> dict[str, int]:
        """Get vault statistics."""
        return {
            "emails": len(self._data["emails"]),
            "phones": len(self._data["phones"]),
            "cards": len(self._data["cards"]),
            "envs": len(self._data.get("envs", [])),
            "recovery": len(self._data.get("recovery", [])),
            "notes": len(self._data.get("notes", [])),
            "total": (
                len(self._data["emails"])
                + len(self._data["phones"])
                + len(self._data["cards"])
                + len(self._data.get("envs", []))
                + len(self._data.get("recovery", []))
                + len(self._data.get("notes", []))
            ),
        }

    def get_all_data(self) -> dict[str, list[dict[str, Any]]]:
        """Get all vault data (for export)."""
        self._update_activity()
        return self._data.copy()

    def import_data(
        self, data: dict[str, list[dict[str, Any]]], merge: bool = True
    ) -> dict[str, int]:
        """Import data into the vault.

        Args:
            data: Data to import with 'emails', 'phones', 'cards', 'envs', 'recovery', 'notes' keys.
            merge: If True, merge with existing data. If False, replace.

        Returns:
            Count of imported items by type.
        """
        self._update_activity()
        counts = {
            "emails": 0,
            "phones": 0,
            "cards": 0,
            "envs": 0,
            "recovery": 0,
            "notes": 0,
        }

        if not merge:
            self._data = {
                "emails": [],
                "phones": [],
                "cards": [],
                "envs": [],
                "recovery": [],
                "notes": [],
            }

        # Get existing IDs to avoid duplicates
        existing_ids = set()
        for category in ["emails", "phones", "cards", "envs", "recovery", "notes"]:
            for item in self._data.get(category, []):
                existing_ids.add(item.get("id"))

        for category in ["emails", "phones", "cards", "envs", "recovery", "notes"]:
            for item in data.get(category, []):
                if item.get("id") not in existing_ids:
                    if category not in self._data:
                        self._data[category] = []
                    self._data[category].append(item)
                    counts[category] += 1

        self._save()
        return counts
