# PassFX Development Guidelines

# Location: CLAUDE.md

# Purpose: Senior-level development standards for PassFX password manager

## Project Overview

PassFX is a production-grade terminal-based password manager built with Python and Textual. It provides AES-256 encrypted storage for credentials with a cyberpunk-themed TUI. Security, data integrity, and user privacy are paramount.

**Technology Stack:**

- Python 3.11+
- Textual (TUI framework)
- cryptography (Fernet encryption)
- PBKDF2 key derivation (480k iterations)
- SQLite for future structured storage
- pyperclip for cross-platform clipboard

## Development Environment

### Setup Commands

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install in development mode
pip install -e .
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run application
passfx
python -m passfx

# Code quality
black passfx/
ruff check passfx/ --fix
mypy passfx/
pytest tests/ --cov=passfx --cov-report=html

# Security audit
pip-audit
bandit -r passfx/
```

## Architecture

### Directory Structure

```
passfx/
├── __init__.py
├── __main__.py
├── app.py                 # Textual App entry point
├── cli.py                 # CLI entry point
├── core/
│   ├── __init__.py
│   ├── crypto.py          # Encryption operations
│   ├── vault.py           # Encrypted storage manager
│   ├── models.py          # Credential dataclasses
│   └── exceptions.py      # Custom exceptions
├── screens/
│   ├── __init__.py
│   ├── login.py           # Master password entry
│   ├── main_menu.py       # Primary navigation
│   ├── passwords.py       # Email credential management
│   ├── phones.py          # Phone PIN management
│   ├── cards.py           # Credit card management
│   ├── generator.py       # Password/PIN generator
│   └── settings.py        # Configuration screen
├── utils/
│   ├── __init__.py
│   ├── generator.py       # Secure random generation
│   ├── clipboard.py       # Clipboard operations
│   ├── strength.py        # Password strength analysis
│   └── validators.py      # Input validation
├── styles/
│   └── passfx.tcss        # Textual CSS styling
└── tests/
    ├── unit/
    ├── integration/
    └── conftest.py
```

### Core Layer (`passfx/core/`)

#### crypto.py

**Purpose:** Cryptographic operations with zero compromise on security

**Requirements:**

- Fernet symmetric encryption (AES-256-CBC + HMAC-SHA256)
- PBKDF2-HMAC-SHA256 key derivation with 480,000 iterations minimum
- Cryptographically secure random salt generation (32 bytes)
- Salt storage separate from encrypted data
- Memory wiping for sensitive data after use
- Constant-time comparison for password verification

**Implementation Pattern:**

```python
"""
Module: passfx/core/crypto.py
Purpose: Cryptographic operations for secure credential storage
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from typing import Tuple
import secrets
import base64


class CryptoManager:
    """Manages encryption and decryption operations with secure key derivation."""

    ITERATIONS: int = 480_000
    SALT_LENGTH: int = 32

    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """Derive encryption key from master password using PBKDF2.

        Args:
            password: Master password string
            salt: Cryptographic salt (32 bytes)

        Returns:
            Derived encryption key suitable for Fernet

        Raises:
            ValueError: If salt length is invalid
        """
        if len(salt) != CryptoManager.SALT_LENGTH:
            raise ValueError(f"Salt must be {CryptoManager.SALT_LENGTH} bytes")

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=CryptoManager.ITERATIONS,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
```

#### vault.py

**Purpose:** Encrypted credential storage with atomic operations

**Requirements:**

- Atomic file writes (write to temp, then rename)
- File locking to prevent concurrent access
- Auto-lock timeout (configurable, default 5 minutes)
- Secure deletion of old vault versions
- Backup creation before destructive operations
- Version compatibility checks
- Data integrity verification (HMAC validation)

**Implementation Pattern:**

```python
"""
Module: passfx/core/vault.py
Purpose: Encrypted credential vault with atomic operations and auto-lock
"""

from pathlib import Path
from typing import List, Optional
import json
import tempfile
import os
from datetime import datetime, timedelta

from .crypto import CryptoManager
from .models import EmailCredential, PhoneCredential, CreditCard
from .exceptions import VaultError, VaultLockedError


class Vault:
    """Encrypted credential vault with atomic operations and auto-lock."""

    def __init__(self, vault_path: Optional[Path] = None) -> None:
        """Initialize vault with optional custom path."""
        self.vault_path = vault_path or Path.home() / ".passfx" / "vault.enc"
        self.vault_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._fernet: Optional[Fernet] = None
        self._last_activity: Optional[datetime] = None
        self._auto_lock_minutes: int = 5

    def unlock(self, master_password: str) -> None:
        """Unlock vault with master password."""
        salt = self._load_salt()
        key = CryptoManager.derive_key(master_password, salt)
        self._fernet = Fernet(key)
        self._verify_password()
        self._last_activity = datetime.now()

    def _atomic_write(self, data: bytes) -> None:
        """Write data atomically using temp file and rename."""
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.vault_path.parent,
            prefix=".vault_",
            suffix=".tmp"
        )
        try:
            os.write(temp_fd, data)
            os.fsync(temp_fd)
            os.close(temp_fd)
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, self.vault_path)
        except Exception:
            os.close(temp_fd)
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
```

#### models.py

**Purpose:** Type-safe credential data structures

**Requirements:**

- Immutable dataclasses with frozen=True
- Validation in **post_init**
- Secure string representation (no password leaks in logs)
- JSON serialization/deserialization methods
- Field-level encryption for sensitive data

**Implementation Pattern:**

```python
"""
Module: passfx/core/models.py
Purpose: Type-safe credential models with validation
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
import re


@dataclass(frozen=True)
class EmailCredential:
    """Email/password credential with metadata."""

    id: str
    service: str
    email: str
    password: str
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate credential data."""
        if not self.service or not self.service.strip():
            raise ValueError("Service name cannot be empty")
        if not self._is_valid_email(self.email):
            raise ValueError(f"Invalid email format: {self.email}")
        if not self.password:
            raise ValueError("Password cannot be empty")

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def __repr__(self) -> str:
        """Secure representation without exposing password."""
        return (
            f"EmailCredential(id={self.id!r}, service={self.service!r}, "
            f"email={self.email!r}, password='***')"
        )
```

### UI Layer (`passfx/screens/`)

#### Navigation Pattern

**Stack-based screen management:**

```
login.py → main_menu.py → [passwords.py | phones.py | cards.py | generator.py | settings.py]
                         ↓
                    All screens can pop back to menu
```

**Screen Implementation Pattern:**

```python
"""
Module: passfx/screens/passwords.py
Purpose: Email credential management interface
"""

from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Header, Footer, DataTable, Button
from textual.binding import Binding
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import PassFXApp


class PasswordsScreen(Screen):
    """Screen for managing email/password credentials."""

    BINDINGS = [
        Binding("a", "add_credential", "Add"),
        Binding("e", "edit_credential", "Edit"),
        Binding("d", "delete_credential", "Delete"),
        Binding("c", "copy_password", "Copy Password"),
        Binding("escape", "pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Compose screen layout."""
        yield Header()
        yield DataTable(id="credentials-table")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize screen after mounting."""
        self.app: PassFXApp
        table = self.query_one(DataTable)
        table.add_columns("Service", "Email", "Created")
        self._load_credentials()
```

### Utils Layer (`passfx/utils/`)

#### generator.py

**Purpose:** Cryptographically secure random generation

**Requirements:**

- Use secrets module exclusively (never random module)
- Configurable complexity for passwords
- Dictionary-based passphrase generation
- PIN generation with specified length
- Guarantee uniqueness in character selection

**Implementation Pattern:**

```python
"""
Module: passfx/utils/generator.py
Purpose: Cryptographically secure password and PIN generation
"""

import secrets
import string
from typing import List


class SecureGenerator:
    """Cryptographically secure password, passphrase, and PIN generator."""

    @staticmethod
    def generate_password(
        length: int = 16,
        use_uppercase: bool = True,
        use_lowercase: bool = True,
        use_digits: bool = True,
        use_symbols: bool = True,
    ) -> str:
        """Generate cryptographically secure password.

        Args:
            length: Password length (minimum 8)
            use_uppercase: Include uppercase letters
            use_lowercase: Include lowercase letters
            use_digits: Include digits
            use_symbols: Include special symbols

        Returns:
            Generated password string

        Raises:
            ValueError: If length < 8 or no character sets enabled
        """
        if length < 8:
            raise ValueError("Password length must be at least 8 characters")

        charset = ""
        if use_lowercase:
            charset += string.ascii_lowercase
        if use_uppercase:
            charset += string.ascii_uppercase
        if use_digits:
            charset += string.digits
        if use_symbols:
            charset += "!@#$%^&*()-_=+[]{}|;:,.<>?"

        if not charset:
            raise ValueError("At least one character set must be enabled")

        return "".join(secrets.choice(charset) for _ in range(length))
```

## Security Requirements

### Critical Security Rules

#### 1. Master Password Handling

- Never log master password or derived keys
- Clear password from memory immediately after use
- Use getpass for password input (no echo)
- Implement rate limiting on failed attempts
- No password hints or recovery mechanisms (by design)

#### 2. Credential Storage

- All credentials encrypted at rest with AES-256
- HMAC-SHA256 for authentication and integrity
- Salt stored separately from encrypted data (`.passfx/salt`)
- Vault file permissions set to 0600 (owner read/write only)
- Secure file deletion for old vault versions (overwrite before delete)

#### 3. Memory Management

```python
# Pattern for sensitive data handling
import ctypes

def secure_delete(data: str) -> None:
    """Overwrite string in memory before deletion."""
    if not data:
        return
    buffer = (ctypes.c_char * len(data)).from_buffer_copy(data.encode())
    ctypes.memset(ctypes.addressof(buffer), 0, len(data))
```

#### 4. Clipboard Security

- Auto-clear clipboard after 30 seconds
- Warn user before clipboard operations
- Optional clipboard disable in settings
- No clipboard history for password managers

#### 5. Auto-Lock Implementation

```python
def _check_auto_lock(self) -> None:
    """Check if auto-lock timeout has been exceeded."""
    if not self._last_activity or not self._fernet:
        return

    elapsed = datetime.now() - self._last_activity
    if elapsed > timedelta(minutes=self._auto_lock_minutes):
        self.lock()
        raise VaultLockedError("Vault auto-locked due to inactivity")
```

#### 6. Input Validation

- Sanitize all user input before storage
- Validate email formats with regex
- Limit credential field lengths
- Check for SQL injection patterns (future SQLite migration)
- Escape special characters in service names

#### 7. Audit Logging

- Log vault access attempts (success and failure)
- Log credential access (read operations)
- Never log sensitive data (passwords, PINs, card numbers)
- Rotate logs with size limits
- Log file permissions 0600

### Prohibited Practices

**NEVER:**

- Store master password on disk (even encrypted)
- Use print() for debugging sensitive data
- Log passwords, keys, or PII
- Use pickle for credential serialization (JSON only)
- Implement password recovery (security by design)
- Store encryption keys in environment variables
- Use weak KDF parameters (<480k iterations)
- Implement custom cryptography (use proven libraries)

## Code Quality Standards

### Type Safety

```python
"""
Module: passfx/core/vault.py
Purpose: Encrypted credential vault operations
"""

from __future__ import annotations
from typing import List, Optional, Protocol
from pathlib import Path


class Encryptable(Protocol):
    """Protocol for objects that can be encrypted."""

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Encryptable: ...
```

### Error Handling

```python
"""
Module: passfx/core/exceptions.py
Purpose: Application-specific exceptions
"""


class PassFXError(Exception):
    """Base exception for all PassFX errors."""
    pass


class VaultError(PassFXError):
    """Raised for vault operation failures."""
    pass


class VaultLockedError(VaultError):
    """Raised when attempting operations on locked vault."""
    pass


class CryptoError(PassFXError):
    """Raised for cryptographic operation failures."""
    pass


class InvalidMasterPasswordError(PassFXError):
    """Raised when master password is incorrect."""
    pass
```

### Logging Configuration

```python
"""
Module: passfx/utils/logging_config.py
Purpose: Secure logging configuration for password manager
"""

import logging
from pathlib import Path


class SensitiveDataFilter(logging.Filter):
    """Filter to prevent logging of sensitive data."""

    SENSITIVE_KEYS = {"password", "pin", "cvv", "master_password", "key", "salt"}

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out log records containing sensitive data."""
        message = str(record.msg).lower()
        return not any(key in message for key in self.SENSITIVE_KEYS)


def configure_logging(verbose: bool = False) -> None:
    """Configure secure logging with sensitive data filtering."""
    log_dir = Path.home() / ".passfx" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    log_file = log_dir / "passfx.log"
    log_file.touch(mode=0o600, exist_ok=True)

    level = logging.DEBUG if verbose else logging.INFO

    handler = logging.FileHandler(log_file)
    handler.addFilter(SensitiveDataFilter())

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[handler]
    )
```

## Testing Requirements

### Coverage Standards

- Minimum 90% code coverage (password manager critical)
- 100% coverage for crypto operations
- 100% coverage for vault operations
- Integration tests for all credential CRUD operations

### Test Structure

```python
"""
Module: tests/unit/core/test_crypto.py
Purpose: Unit tests for cryptographic operations
"""

import pytest
from passfx.core.crypto import CryptoManager
from passfx.core.exceptions import CryptoError


class TestCryptoManager:
    """Test suite for cryptographic operations."""

    def test_key_derivation_consistent(self) -> None:
        """Verify key derivation produces consistent results."""
        password = "test_password_123"
        salt = b"x" * 32

        key1 = CryptoManager.derive_key(password, salt)
        key2 = CryptoManager.derive_key(password, salt)

        assert key1 == key2

    def test_different_salts_produce_different_keys(self) -> None:
        """Verify different salts produce different keys."""
        password = "test_password_123"
        salt1 = b"x" * 32
        salt2 = b"y" * 32

        key1 = CryptoManager.derive_key(password, salt1)
        key2 = CryptoManager.derive_key(password, salt2)

        assert key1 != key2

    def test_encryption_decryption_roundtrip(self) -> None:
        """Verify data can be encrypted and decrypted successfully."""
        password = "test_password_123"
        salt = b"x" * 32
        plaintext = b"sensitive credential data"

        key = CryptoManager.derive_key(password, salt)
        fernet = Fernet(key)

        ciphertext = fernet.encrypt(plaintext)
        decrypted = fernet.decrypt(ciphertext)

        assert decrypted == plaintext
        assert ciphertext != plaintext
```

### Security Testing

```python
"""
Module: tests/security/test_password_strength.py
Purpose: Security validation tests
"""

import pytest
from passfx.utils.generator import SecureGenerator
from passfx.utils.strength import analyze_password_strength


class TestPasswordSecurity:
    """Security tests for password generation and validation."""

    def test_generated_passwords_are_strong(self) -> None:
        """Verify all generated passwords meet minimum strength."""
        for _ in range(100):
            password = SecureGenerator.generate_password(length=16)
            strength = analyze_password_strength(password)
            assert strength.score >= 3, f"Weak password generated: {strength}"

    def test_generator_uses_secure_randomness(self) -> None:
        """Verify password generation uses cryptographically secure RNG."""
        passwords = {
            SecureGenerator.generate_password(length=16)
            for _ in range(1000)
        }
        assert len(passwords) == 1000, "Duplicate passwords detected"
```

## Textual UI Patterns

### Screen Lifecycle

```python
def on_mount(self) -> None:
    """Initialize screen components after mounting."""
    self._setup_table()
    self._load_data()
    self._focus_default_widget()

def on_unmount(self) -> None:
    """Cleanup before screen is removed."""
    self._save_pending_changes()
    self._clear_sensitive_data()
```

### Key Binding Pattern

```python
BINDINGS = [
    Binding("ctrl+q", "quit", "Quit", priority=True),
    Binding("escape", "pop_screen", "Back"),
    Binding("f1", "help", "Help"),
]

async def action_quit(self) -> None:
    """Handle quit action with confirmation."""
    if await self._confirm_quit():
        self.app.exit()
```

### Style Guidelines

```tcss
/* File: passfx/styles/passfx.tcss
   Purpose: Global styling for PassFX TUI */

/* Color palette - cyberpunk theme */
$pfx-primary: #00ff41;
$pfx-secondary: #ff006e;
$pfx-background: #0a0e27;
$pfx-surface: #151b3d;
$pfx-text: #e0e0e0;
$pfx-border: #00ff41 50%;

/* Component styles */
Screen {
    background: $pfx-background;
}

Button {
    background: $pfx-surface;
    color: $pfx-primary;
    border: tall $pfx-border;
}

Button:hover {
    background: $pfx-primary 20%;
}

DataTable {
    background: $pfx-surface;
    color: $pfx-text;
}
```

## Performance Considerations

### Lazy Loading

- Import screens only when needed (avoid circular imports)
- Load credentials on-demand, not all at startup
- Implement pagination for large credential lists

### Memory Management

```python
def _clear_credential_cache(self) -> None:
    """Clear cached credentials from memory."""
    if hasattr(self, '_credentials'):
        for cred in self._credentials:
            secure_delete(cred.password)
        self._credentials.clear()
```

### Vault Operations

- Batch credential updates to minimize disk writes
- Use atomic operations to prevent corruption
- Implement write-ahead logging for critical operations

## Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.8
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ["--maxkb=500"]
      - id: detect-private-key

  - repo: https://github.com/pycqa/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
        additional_dependencies: ["bandit[toml]"]
```

## Dependencies

```toml
# pyproject.toml
[project]
name = "passfx"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "textual>=0.45.0",
    "cryptography>=41.0.0",
    "pyperclip>=1.8.2",
    "zxcvbn>=4.4.28",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.1",
    "mypy>=1.7.1",
    "black>=23.12.1",
    "ruff>=0.1.8",
    "pre-commit>=3.6.0",
    "bandit[toml]>=1.7.5",
    "pip-audit>=2.6.1",
]

[project.scripts]
passfx = "passfx.cli:main"

[tool.black]
line-length = 88
target-version = ['py311']

[tool.ruff]
line-length = 88
select = ["E", "F", "W", "I", "N", "UP", "S", "B", "A", "C4", "DTZ", "PIE", "PT", "SIM"]
ignore = ["E501"]

[tool.mypy]
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
python_version = "3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=passfx --cov-report=html --cov-report=term-missing --cov-fail-under=90"
asyncio_mode = "auto"

[tool.bandit]
exclude_dirs = ["tests", ".venv"]
skips = ["B101"]  # Skip assert_used in tests
```

## Git Workflow

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**

- feat: New feature
- fix: Bug fix
- security: Security improvement
- refactor: Code restructuring
- test: Test additions/changes
- docs: Documentation
- style: Formatting changes
- perf: Performance improvement

**Example:**

```
security(crypto): increase PBKDF2 iterations to 480k

- Updated key derivation to use 480,000 iterations
- Added migration for existing vaults
- Updated security documentation

Closes #42
```

### Branch Protection

- main: Production releases only
- develop: Integration branch
- feature/\*: New features
- security/\*: Security fixes (expedited review)
- hotfix/\*: Critical production fixes

## Code Review Checklist

### Security Review

- [ ] No hardcoded credentials or test passwords
- [ ] Sensitive data cleared from memory
- [ ] Proper error handling without information leakage
- [ ] Cryptographic operations use approved libraries
- [ ] File permissions set correctly (0600/0700)
- [ ] No logging of passwords or keys
- [ ] Input validation on all user data
- [ ] Secure deletion implemented where needed

### Functional Review

- [ ] Type hints on all functions
- [ ] Docstrings on public APIs
- [ ] Unit tests with >90% coverage
- [ ] Integration tests for critical paths
- [ ] Error messages are user-friendly
- [ ] No circular imports
- [ ] Lazy loading for screens
- [ ] Memory leaks checked

### UI Review

- [ ] Keyboard navigation works correctly
- [ ] Focus management implemented
- [ ] Loading indicators for slow operations
- [ ] Confirmation dialogs for destructive actions
- [ ] Consistent styling with passfx.tcss
- [ ] Responsive to terminal resize
- [ ] Accessible color contrasts

## Final Notes

### Security Principles

1. **Defense in Depth**: Multiple layers of security (encryption, file permissions, auto-lock)
2. **Fail Securely**: On error, lock vault and clear sensitive data
3. **Least Privilege**: Minimal file permissions, no unnecessary access
4. **Audit Trail**: Log access patterns without exposing secrets
5. **No Recovery**: By design, no master password recovery (security over convenience)

### Performance Targets

- Vault unlock: <500ms
- Credential search: <100ms
- Screen transitions: <50ms
- Memory usage: <50MB baseline

### Compliance Considerations

- GDPR: User data encrypted at rest, exportable, deletable
- OWASP: Follow Top 10 security practices
- PCI DSS: Credit card data encrypted separately (if storing CVV)

---

**Remember:** PassFX is a security-critical application. When in doubt, prioritize security over convenience, performance, or features. Every line of code that touches credentials must be reviewed with a security-first mindset.
