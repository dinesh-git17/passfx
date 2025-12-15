# PassFX Architecture Summary

> A production-grade terminal-based password manager built with Python and Textual

## Overview

PassFX is a cyberpunk-themed TUI (Terminal User Interface) password manager that provides AES-256 encrypted storage for:
- Email/password credentials
- Phone numbers with PINs
- Credit card information

**Entry Point:** `passfx` CLI command → `cli.py:main()` → `PassFXApp`

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| UI Framework | Textual 0.50+ | Terminal UI with async support |
| Encryption | cryptography (Fernet) | AES-256-CBC + HMAC-SHA256 |
| Key Derivation | PBKDF2-HMAC-SHA256 | 480k iterations |
| Password Strength | zxcvbn | Real-world strength estimation |
| Clipboard | pyperclip | Cross-platform clipboard ops |
| Styling | Rich | Terminal formatting/colors |

---

## Directory Structure

```
passfx/
├── app.py                 # Textual App root (PassFXApp)
├── cli.py                 # CLI entry point
├── __main__.py            # Module execution support
│
├── core/                  # Business logic layer
│   ├── crypto.py          # CryptoManager: encryption/decryption
│   ├── vault.py           # Vault: encrypted storage operations
│   ├── models.py          # EmailCredential, PhoneCredential, CreditCard
│   └── exceptions.py      # Custom exceptions
│
├── screens/               # UI screens (Textual Screen classes)
│   ├── login.py           # Authentication flow
│   ├── main_menu.py       # Navigation hub
│   ├── passwords.py       # Email credential CRUD
│   ├── phones.py          # Phone PIN CRUD
│   ├── cards.py           # Credit card CRUD
│   ├── generator.py       # Password/passphrase/PIN generation
│   └── settings.py        # Export/import/stats
│
├── utils/                 # Utility functions
│   ├── generator.py       # Secure random generation (secrets module)
│   ├── clipboard.py       # Copy with 30s auto-clear
│   ├── strength.py        # Password strength analysis
│   └── io.py              # JSON/CSV export/import
│
├── ui/                    # UI helpers
│   ├── styles.py          # Rich theme and display functions
│   ├── menu.py            # Terminal menu system
│   └── logo.py            # ASCII art and branding
│
└── styles/
    └── passfx.tcss        # Textual CSS stylesheet
```

---

## Core Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PassFXApp (app.py)                                             │
│  - Manages screen stack                                         │
│  - Holds Vault instance                                         │
│  - Global key bindings (q=quit, escape=back)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────────┐
│  Screen Stack           │     │  Vault (core/vault.py)          │
│  ├─ LoginScreen         │     │  - File I/O: ~/.passfx/vault.enc│
│  ├─ MainMenuScreen      │────▶│  - CRUD for 3 credential types  │
│  ├─ PasswordsScreen     │     │  - Auto-lock timeout            │
│  ├─ PhonesScreen        │     └─────────────┬───────────────────┘
│  ├─ CardsScreen         │                   │
│  ├─ GeneratorScreen     │                   ▼
│  └─ SettingsScreen      │     ┌─────────────────────────────────┐
└─────────────────────────┘     │  CryptoManager (core/crypto.py) │
                                │  - Key derivation (PBKDF2)      │
                                │  - Encrypt/decrypt (Fernet)     │
                                │  - Memory wiping                │
                                └─────────────────────────────────┘
```

### Screen Navigation Flow

```
LoginScreen
    │
    ├─ [New User] → Create vault with master password
    │
    └─ [Existing User] → Unlock vault
            │
            ▼
    MainMenuScreen
        │
        ├─ 1 → PasswordsScreen (email/password CRUD)
        ├─ 2 → PhonesScreen (phone/PIN CRUD)
        ├─ 3 → CardsScreen (credit card CRUD)
        ├─ 4 → GeneratorScreen (password/passphrase/PIN)
        ├─ 5 → Search (not implemented)
        ├─ 6 → SettingsScreen (export/import/stats)
        └─ 7 → Exit
```

---

## Core Components

### 1. CryptoManager (`core/crypto.py`)

Handles all cryptographic operations with zero-knowledge design.

```python
class CryptoManager:
    PBKDF2_ITERATIONS = 480_000  # OWASP 2023 recommendation
    SALT_LENGTH = 32             # 256-bit salt
```

**Key Methods:**
| Method | Purpose |
|--------|---------|
| `derive_key(password, salt)` | PBKDF2 key derivation |
| `encrypt(data) / decrypt(ciphertext)` | Fernet AES-256 operations |
| `verify_password(password)` | Constant-time comparison |
| `wipe()` | Secure memory cleanup |

**Security Features:**
- Uses `secrets.compare_digest()` for constant-time comparison
- Attempts memory wiping of sensitive data
- Salt stored separately from encrypted data

### 2. Vault (`core/vault.py`)

Manages encrypted credential storage with file operations.

**File Locations:**
```
~/.passfx/
├── vault.enc    # Encrypted credentials (0o600)
├── salt         # Cryptographic salt (0o600)
└── config.json  # User preferences
```

**Key Methods:**
| Method | Purpose |
|--------|---------|
| `create(master_password)` | Initialize new vault |
| `unlock(master_password)` | Decrypt and load data |
| `lock()` | Clear sensitive data from memory |
| `add_*/get_*/update_*/delete_*` | CRUD for each credential type |
| `search(query)` | Case-insensitive search across all types |

**Data Structure:**
```json
{
  "emails": [EmailCredential...],
  "phones": [PhoneCredential...],
  "cards": [CreditCard...]
}
```

### 3. Models (`core/models.py`)

Three credential types as dataclasses:

| Model | Key Fields | Sensitive Fields |
|-------|------------|------------------|
| `EmailCredential` | label, email, notes | password |
| `PhoneCredential` | label, phone, notes | password (PIN) |
| `CreditCard` | label, cardholder_name, expiry, notes | card_number, cvv |

All models include: `id`, `created_at`, `updated_at`

**Common Methods:** `to_dict()`, `from_dict()`, `update()`

---

## UI Screens

### Screen Pattern

Each screen follows this structure:

```python
class ExampleScreen(Screen):
    BINDINGS = [
        Binding("a", "add", "Add"),
        Binding("escape", "pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="table")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_table()

    def action_add(self) -> None:
        self.app.push_screen(AddModal(), self._handle_add_result)
```

### Modal Pattern

Modals return data via callbacks:

```python
# Push modal with callback
self.app.push_screen(AddPasswordModal(), self._on_password_added)

# Callback receives modal result
def _on_password_added(self, result: EmailCredential | None) -> None:
    if result:
        self.app.vault.add_email(result)
        self._refresh_table()
```

### Key Bindings by Screen

| Screen | Key Bindings |
|--------|--------------|
| PasswordsScreen | a=add, c=copy, e=edit, d=delete, v=view, esc=back |
| PhonesScreen | a=add, c=copy, d=delete, esc=back |
| CardsScreen | a=add, c=copy, v=view, d=delete, esc=back |
| GeneratorScreen | g=generate, c=copy, esc=back |

---

## Utilities

### Secure Generation (`utils/generator.py`)

```python
generate_password(length=16, use_uppercase=True, ...)  # Cryptographic
generate_passphrase(word_count=4, separator="-")       # Word-based
generate_pin(length=4)                                  # Numeric
```

All use `secrets` module (CSPRNG), never `random`.

### Clipboard (`utils/clipboard.py`)

```python
copy_to_clipboard(text, auto_clear=True, clear_after=30)
```
- 30-second auto-clear timer
- Thread-safe with locking
- Platform fallbacks (pbcopy, xclip, xsel)

### Password Strength (`utils/strength.py`)

```python
check_strength(password) → StrengthResult(score, label, color, crack_time)
```
- Uses zxcvbn for real-world analysis
- Scores: 0=Very Weak, 1=Weak, 2=Fair, 3=Good, 4=Strong
- Falls back to simple analysis for passwords >72 chars

---

## Security Model

### Encryption Pipeline

```
Master Password
      │
      ▼
┌─────────────────────────────┐
│ PBKDF2-HMAC-SHA256          │
│ - 480,000 iterations        │
│ - 32-byte salt (per vault)  │
└─────────────────────────────┘
      │
      ▼
  256-bit Key
      │
      ▼
┌─────────────────────────────┐
│ Fernet (AES-256-CBC)        │
│ + HMAC-SHA256 auth tag      │
└─────────────────────────────┘
      │
      ▼
  Encrypted Vault (vault.enc)
```

### Security Features

| Feature | Implementation |
|---------|----------------|
| Key Derivation | PBKDF2 with 480k iterations |
| Encryption | AES-256-CBC with HMAC-SHA256 |
| Salt Storage | Separate file (~/.passfx/salt) |
| File Permissions | 0o700 dirs, 0o600 files |
| Clipboard | 30s auto-clear |
| Password Verification | Constant-time comparison |
| Memory | Attempted wiping of sensitive data |
| Rate Limiting | 3 failed login attempts |

### What's NOT Stored

- Master password (only used for key derivation)
- Encryption keys on disk
- Password hints or recovery data

---

## Styling

### Color Palette (`styles/passfx.tcss`)

| Variable | Hex | Usage |
|----------|-----|-------|
| `$pfx-primary` | #3b82f6 | Primary blue |
| `$pfx-accent` | #8b5cf6 | Purple accent |
| `$pfx-success` | #22c55e | Success green |
| `$pfx-warning` | #f59e0b | Warning orange |
| `$pfx-error` | #ef4444 | Error red |
| `$pfx-bg` | #0f172a | Dark background |
| `$pfx-surface` | #1e293b | Surface color |
| `$pfx-fg` | #f8fafc | Foreground text |

---

## Import/Export (`utils/io.py`)

| Format | Export | Import | Notes |
|--------|--------|--------|-------|
| JSON | ✓ | ✓ | Wrapped with version/timestamp |
| CSV | ✓ | ✓ | Unified table with type column |

CSV includes option to mask sensitive data for sharing.

---

## Key Patterns & Conventions

### Type Hints
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..app import PassFXApp  # Avoid circular imports
```

### Union Types (Python 3.10+)
```python
Credential = EmailCredential | PhoneCredential | CreditCard
```

### Async Actions
```python
def action_copy(self) -> None:  # Textual binding handler
    # Actions prefixed with action_ are auto-bound
```

### Resource Cleanup
```python
def lock(self) -> None:
    if self._crypto:
        self._crypto.wipe()  # Clear sensitive data
        self._crypto = None
```

---

## Quick Reference

### Running the App
```bash
passfx              # Via entry point
python -m passfx    # Via module
```

### Development
```bash
pip install -e .                    # Install in dev mode
pip install -r requirements-dev.txt # Dev dependencies
black passfx/ && ruff check passfx/ # Format & lint
pytest tests/                       # Run tests
```

### File Locations
```
~/.passfx/
├── vault.enc   # Encrypted credentials
├── salt        # Cryptographic salt
└── config.json # User preferences
```
