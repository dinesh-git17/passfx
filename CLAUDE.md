# CLAUDE.md - AI Assistant Guide for PassFX

This document provides guidance for AI assistants working on the PassFX codebase.

---

## Critical Rules (Read First)

### Security - ABSOLUTE PRIORITIES

- **NEVER** log, print, or expose passwords, keys, PINs, CVVs, or master passwords
- **NEVER** use `random` module for security operations - use `secrets` only
- **NEVER** implement custom cryptography - use `cryptography` library
- **NEVER** store master passwords on disk (even encrypted)
- **NEVER** implement password recovery mechanisms (security by design)
- **NEVER** use `pickle` for credential serialization - JSON only
- **NEVER** use weak KDF parameters (<480k PBKDF2 iterations)

### Git Commits - NEVER Commit Without Confirmation

- **NEVER** commit to GitHub without explicit user confirmation of the commit message
- Never mention "Claude", "AI", or "assistant" in commit messages
- Write commit messages as if a human developer made the changes
- Use conventional commit format: `type(scope): description`
- Always show the proposed commit message and proceed to commit

### Code Quality Enforcement

Before pushing to GitHub, and **before providing a summary**:

1. Run `ruff check passfx/` (linting)
2. Run `mypy passfx/` (type checking)
3. Run `bandit -r passfx/` (security audit)
4. If any check fails, fix the errors before proceeding
5. Report any issues clearly

---

## Security Requirements (Non-Negotiable)

### Cryptographic Standards

| Requirement | Specification |
|-------------|---------------|
| Encryption | AES-256-CBC via Fernet |
| Key Derivation | PBKDF2-HMAC-SHA256 |
| KDF Iterations | 480,000 minimum |
| Salt Length | 32 bytes |
| RNG | `secrets` module only |

### File Permissions

| File/Directory | Permission |
|----------------|------------|
| `~/.passfx/` | 0o700 |
| `vault.enc` | 0o600 |
| `salt` | 0o600 |
| `logs/` | 0o700 |
| `*.log` | 0o600 |

### Memory Security

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

### Prohibited Practices

| Never Do This | Why |
|---------------|-----|
| `print(password)` | Exposes secrets in logs |
| `import random` | Not cryptographically secure |
| `pickle.dump(creds)` | Arbitrary code execution risk |
| Store keys in env vars | Accessible to child processes |
| Password hints/recovery | Defeats security model |

---

## Code Standards (FAANG Senior Engineer Level)

### Philosophy

- Write production-grade code for a security-critical application
- Code should be self-documenting through clear naming
- Every line touching credentials requires security-first review
- Prioritize security > correctness > maintainability > performance

### Comment Standards (Strict)

**File-Level Comments:**
- Every file must have ONE block comment at the top (2-4 lines max)
- Describe purpose and role in security architecture
- No implementation details

**Function/Method Comments:**
- Only when the "why" is non-obvious
- Document security implications, edge cases, business constraints
- Never explain what code does (code should be self-explanatory)

**Inline Comments:**
- Use sparingly for critical security context only
- Explain crypto decisions, security tradeoffs, non-obvious constraints

**Forbidden:**
- Emojis in code/comments
- Casual/conversational tone
- Obvious restatements (`// encrypt the data`)
- Commented-out code (delete it)
- Unscoped TODOs without tickets/context
- Debugging leftovers (`print()`, `# testing`)

### Python Standards

- Python 3.11+ with strict type hints
- No `Any` types unless absolutely necessary (document why)
- Explicit return types for all functions
- Frozen dataclasses for credential models
- Unused variables prefixed with `_`

### Error Handling

- Never silently swallow errors
- On crypto errors: lock vault, clear sensitive data
- Log errors with context (never log sensitive data)
- Handle edge cases explicitly
- Use custom exceptions from `core/exceptions.py`

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Functions | verbs | `encrypt_vault`, `derive_key`, `validate_input` |
| Variables | nouns | `vault_data`, `is_locked`, `credential_count` |
| Classes | PascalCase | `CryptoManager`, `VaultError`, `EmailCredential` |
| Constants | UPPER_SNAKE | `ITERATIONS`, `SALT_LENGTH`, `AUTO_LOCK_MINUTES` |
| Private | underscore | `_fernet`, `_last_activity`, `_load_salt` |

---

## Project Overview

**PassFX** is a production-grade terminal-based password manager built with Python and Textual. AES-256 encrypted storage with a cyberpunk-themed TUI. Security, data integrity, and user privacy are paramount.

### Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Textual (TUI) |
| Language | Python 3.11+ (strict typing) |
| Encryption | cryptography (Fernet/AES-256) |
| Key Derivation | PBKDF2 (480k iterations) |
| Styling | Textual CSS (.tcss) |
| Clipboard | pyperclip |
| Strength | zxcvbn |

### Directory Structure

```
passfx/
├── app.py                 # Textual App entry point
├── cli.py                 # CLI entry point
├── core/
│   ├── crypto.py          # Encryption operations (CRITICAL)
│   ├── vault.py           # Encrypted storage (CRITICAL)
│   ├── models.py          # Credential dataclasses
│   └── exceptions.py      # Custom exceptions
├── screens/
│   ├── login.py           # Master password entry
│   ├── main_menu.py       # Primary navigation
│   ├── passwords.py       # Email credentials
│   ├── phones.py          # Phone PINs
│   ├── cards.py           # Credit cards
│   ├── notes.py           # Secure notes
│   ├── envs.py            # Environment variables
│   ├── generator.py       # Password generator
│   ├── settings.py        # Configuration
│   └── recovery.py        # Recovery codes
├── ui/
│   ├── styles.py          # Style constants
│   ├── logo.py            # ASCII art
│   └── menu.py            # Menu components
├── utils/
│   ├── generator.py       # Secure random generation
│   ├── clipboard.py       # Clipboard with auto-clear
│   ├── strength.py        # Password analysis
│   └── io.py              # File I/O utilities
└── widgets/
    └── terminal.py        # Custom widgets
```

### Key Architectural Rules

1. **Core Layer** (`core/`): Zero dependencies on UI, pure security logic
2. **Screens** (`screens/`): Textual screens, lazy-loaded
3. **Utils** (`utils/`): Stateless helpers, no side effects
4. **Widgets** (`widgets/`): Reusable UI components

### Navigation Flow

```
login.py → main_menu.py → [passwords | phones | cards | notes | envs | generator | settings]
                         ↓
                    All screens pop back to menu via ESC
```

---

## Development Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e . && pip install -r requirements-dev.txt
pre-commit install

# Run
passfx                    # Production
python -m passfx          # Development

# Quality
ruff check passfx/ --fix  # Lint
mypy passfx/              # Type check
black passfx/             # Format

# Security
bandit -r passfx/         # Security audit
pip-audit                 # Dependency audit

# Test
pytest tests/ --cov=passfx --cov-report=html
```

---

## Testing Requirements

### Coverage Standards

| Component | Required Coverage |
|-----------|-------------------|
| `core/crypto.py` | 100% |
| `core/vault.py` | 100% |
| `core/models.py` | 95% |
| `utils/generator.py` | 95% |
| Overall | 90% minimum |

### Test Categories

1. **Unit Tests**: Pure function testing, no I/O
2. **Integration Tests**: Vault operations, encryption round-trips
3. **Security Tests**: Password strength, randomness validation

---

## Textual UI Patterns

### Screen Lifecycle

```python
def on_mount(self) -> None:
    """Initialize after mounting - load data, setup table."""
    self._setup_table()
    self._load_data()

def on_unmount(self) -> None:
    """Cleanup - save pending, clear sensitive data."""
    self._save_pending_changes()
    self._clear_sensitive_data()  # CRITICAL
```

### Key Bindings

```python
BINDINGS = [
    Binding("ctrl+q", "quit", "Quit", priority=True),
    Binding("escape", "pop_screen", "Back"),
    Binding("a", "add", "Add"),
    Binding("e", "edit", "Edit"),
    Binding("d", "delete", "Delete"),
    Binding("c", "copy", "Copy"),
]
```

### Style Variables (Cyberpunk Theme)

```tcss
$pfx-primary: #00ff41;      /* Matrix green */
$pfx-secondary: #ff006e;    /* Neon pink */
$pfx-background: #0a0e27;   /* Deep blue-black */
$pfx-surface: #151b3d;      /* Panel background */
$pfx-text: #e0e0e0;         /* Light gray */
$pfx-border: #00ff41 50%;   /* Green with opacity */
```

---

## Git Workflow

### Commit Format

```
type(scope): description (imperative mood, max 72 chars)

- Explain what changed and why
- Reference issues with Fixes #123

Types: feat, fix, security, refactor, perf, test, docs, style
Scopes: core, crypto, vault, ui, cli, utils, tests
```

### Good Commit Examples

```
security(crypto): increase PBKDF2 iterations to 480k

- Updated key derivation to meet OWASP 2024 recommendations
- Maintains backward compatibility with existing vaults
- Added migration for older vault formats

Fixes #42
```

```
fix(vault): prevent data corruption on concurrent writes

Implemented file locking to prevent race conditions when
multiple processes write to vault simultaneously.

- fcntl-based locking for Unix
- msvcrt-based locking for Windows
- Added integration tests

Fixes #89
```

### Branch Protection

- `main`: Production releases only
- `develop`: Integration branch
- `feature/*`: New features
- `security/*`: Security fixes (expedited)
- `hotfix/*`: Critical production fixes

---

## Performance Targets

| Operation | Target |
|-----------|--------|
| Vault unlock | <500ms |
| Credential search | <100ms |
| Screen transitions | <50ms |
| Memory baseline | <50MB |

---

## Code Review Checklist

### Security Review

- [ ] No hardcoded credentials or test passwords
- [ ] Sensitive data cleared from memory after use
- [ ] Proper error handling without information leakage
- [ ] Cryptographic operations use `cryptography` library
- [ ] File permissions set correctly (0600/0700)
- [ ] No logging of passwords, keys, or PII
- [ ] Input validation on all user data
- [ ] Secure deletion implemented where needed

### Functional Review

- [ ] Type hints on all functions
- [ ] Docstrings on public APIs
- [ ] Unit tests with >90% coverage
- [ ] Error messages are user-friendly (no stack traces to user)
- [ ] No circular imports
- [ ] Lazy loading for screens

### UI Review

- [ ] Keyboard navigation works
- [ ] Focus management implemented
- [ ] Confirmation dialogs for destructive actions
- [ ] Consistent styling with passfx.tcss
- [ ] Responsive to terminal resize

---

## Security Principles

1. **Defense in Depth**: Encryption + file permissions + auto-lock
2. **Fail Securely**: On error, lock vault and clear sensitive data
3. **Least Privilege**: Minimal permissions, no unnecessary access
4. **No Recovery**: By design, no master password recovery
5. **Audit Trail**: Log access patterns, never secrets

---

## Communication Style

- Sound like a sharp senior security engineer
- Direct, precise, security-focused
- Flag security risks immediately
- No corporate fluff, no casual tone

### Tone Rules

- Call out security issues clearly
- Be decisive about security tradeoffs
- Push for secure defaults
- No emojis in code contexts

### Example

**Instead of:**
"This implementation looks okay but might have some edge cases."

**Say:**
"This is solid. No timing attacks, proper constant-time comparison. Ship it."

Security first. Think like an attacker. Let's build.

---

## Remember

You are not writing code for a tutorial or demo.
You are writing code for a **password manager** that protects users' most sensitive data.
Every line touching credentials must be reviewed with a security-first mindset.
When in doubt, prioritize security over convenience, performance, or features.
