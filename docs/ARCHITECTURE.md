# PassFX Architecture

> "Your secrets deserve better than a sticky note. They deserve cryptographic paranoia."

This document is the source of truth for PassFX's architecture. It describes how the system is built, why decisions were made, and what you should never, under any circumstances, break.

---

## 1. Architecture Overview

PassFX is a production-grade, offline-first, terminal-based password manager built with Python and Textual. It stores credentials locally in an encrypted vault at `~/.passfx/`, using Fernet authenticated encryption (AES-128-CBC + HMAC-SHA256) with PBKDF2 key derivation.

### Core Philosophy

1. **Security over convenience.** Every architectural decision prioritizes protecting user secrets.
2. **Offline only.** No network code exists. You cannot hack a port that is not open.
3. **Zero knowledge.** The master password is never stored. Lose it, and your data is mathematically irretrievable.
4. **Defense in depth.** Encryption, file permissions, memory wiping, auto-lock, and rate limiting work together.
5. **Fail secure.** When something goes wrong, the vault locks and sensitive data is cleared.

### Architectural Goals

| Priority | Goal | Implementation |
|----------|------|----------------|
| 1 | Security | Fernet encryption, PBKDF2 (480k iterations), constant-time comparison |
| 2 | Correctness | Atomic writes, file locking, integrity verification |
| 3 | Maintainability | Layered architecture, type hints, comprehensive tests |
| 4 | Performance | Lazy-loaded screens, minimal dependencies |

The order matters. We will gladly sacrifice microseconds for security guarantees.

---

## 2. High-Level System Diagram

PassFX follows a strict layered architecture where dependencies flow downward. Upper layers may call lower layers, but lower layers must never import from upper layers.

```
                         +-----------------------+
                         |     Entry Points      |
                         |  cli.py / __main__.py |
                         +-----------+-----------+
                                     |
                                     v
                         +-----------------------+
                         |   Application Layer   |
                         |       app.py          |
                         |   (PassFXApp class)   |
                         +-----------+-----------+
                                     |
              +----------------------+----------------------+
              |                      |                      |
              v                      v                      v
   +-------------------+  +-------------------+  +-------------------+
   |   Screens Layer   |  |   Widgets Layer   |  |     UI Layer      |
   |     screens/      |  |     widgets/      |  |       ui/         |
   | (Textual screens) |  | (Textual widgets) |  | (Rich styling)    |
   +--------+----------+  +-------------------+  +-------------------+
            |
            v
   +-------------------+
   |   Utils Layer     |
   |      utils/       |
   | (Pure functions)  |
   +--------+----------+
            |
            v
   +========================================+
   ||         SECURITY BOUNDARY            ||
   +========================================+
            |
            v
   +-------------------+
   |   Core Layer      |
   |      core/        |
   | crypto.py         |  <-- Encryption, key derivation
   | vault.py          |  <-- Encrypted storage, file locking
   | models.py         |  <-- Credential dataclasses
   +--------+----------+
            |
            v
   +-------------------+
   | Platform Security |
   | platform_security |
   | (File permissions)|
   +--------+----------+
            |
            v
   +-------------------+
   |    File System    |
   |   ~/.passfx/      |
   +-------------------+
```

### What Talks to What

- **Entry Points** instantiate the application and register signal handlers.
- **Application Layer** owns the `Vault` instance and manages screen navigation.
- **Screens Layer** presents UI and calls vault CRUD methods. Screens never touch crypto directly.
- **Widgets Layer** provides reusable Textual components (terminal widget, modals).
- **UI Layer** handles Rich styling and branding. It has zero awareness of credentials.
- **Utils Layer** provides stateless helpers (password generation, strength checking, clipboard).
- **Core Layer** is the security kernel. It handles encryption, persistence, and data models.
- **Platform Security** abstracts file permission enforcement across Unix and Windows.

### What Must Never Talk to What

| Forbidden Dependency | Reason |
|----------------------|--------|
| Core imports Screens | Core must remain UI-agnostic |
| Crypto imports Vault | Crypto is pure; it encrypts bytes, period |
| Utils imports Screens | Utils must remain stateless |
| Any layer imports from above it | Dependency inversion violation |

If you find yourself tempted to add an upward dependency, stop. You are about to make a mistake that future maintainers will curse you for.

---

## 3. Core Architectural Layers

### 3.1 Entry Points (`cli.py`, `__main__.py`)

**Responsibilities:**
- Set process title and terminal title
- Register signal handlers (SIGINT, SIGTERM)
- Instantiate and run `PassFXApp`
- Guarantee cleanup on all exit paths (normal, signal, exception)

**What it must never do:**
- Contain business logic
- Access credentials directly
- Catch and swallow exceptions from the app layer

The entry point exists to bootstrap the application and ensure cleanup. That is all.

### 3.2 Application Layer (`app.py`)

**Responsibilities:**
- Own the `Vault` instance (single source of truth for credential state)
- Manage Textual screen stack and navigation
- Provide `unlock_vault()` and `create_vault()` high-level APIs
- Handle graceful shutdown with vault locking

**What it owns:**
- `self.vault`: The `Vault` instance
- `self._unlocked`: Boolean tracking vault state
- Screen lifecycle management

**What it must never do:**
- Perform encryption/decryption directly
- Access the filesystem except through `Vault`
- Expose the master password after vault unlock

### 3.3 Screens Layer (`screens/`)

PassFX has 11 screens, each focused on a specific credential type or function:

| Screen | Purpose |
|--------|---------|
| `login.py` | Master password entry, rate limiting, vault creation |
| `main_menu.py` | Dashboard with security score and navigation |
| `passwords.py` | Email/password credential management |
| `phones.py` | Phone PIN storage |
| `cards.py` | Credit card management with masked display |
| `notes.py` | Secure free-form notes |
| `envs.py` | Environment variable storage |
| `recovery.py` | 2FA recovery code storage |
| `generator.py` | Password/passphrase/PIN generation |
| `settings.py` | Configuration and import/export |
| `help.py` | User documentation |

**Responsibilities:**
- Render UI using Textual widgets
- Handle user input and key bindings
- Call `Vault` CRUD methods through `app.vault`
- Display credentials with appropriate masking

**What screens must never do:**
- Import from `core/crypto.py` (except `LoginScreen` for password validation)
- Store credentials outside of `Vault`
- Log or print credential values
- Bypass the Vault API for persistence

### 3.4 Widgets Layer (`widgets/`)

**Modules:**
- `terminal.py`: Interactive in-app terminal (RichLog + Input)
- `id_card_modal.py`: Reusable credential display modal

**Responsibilities:**
- Provide composable, reusable Textual components
- Handle presentation logic only

**What widgets must never do:**
- Access the vault directly
- Contain business logic
- Store state beyond their immediate rendering needs

### 3.5 UI Layer (`ui/`)

**Modules:**
- `styles.py`: Rich theme and console configuration
- `menu.py`: Interactive terminal menu using simple-term-menu
- `logo.py`: ASCII branding and gradient rendering

**Responsibilities:**
- Define color schemes and visual styling
- Provide input prompts and formatted output
- Display startup/exit messages

**What the UI layer must never do:**
- Handle credentials (it does not even know they exist)
- Import from core, screens, or widgets
- Contain application state

The UI layer is purely cosmetic. It could be replaced entirely without affecting security.

### 3.6 Utils Layer (`utils/`)

**Modules:**
| Module | Purpose |
|--------|---------|
| `generator.py` | Cryptographically secure password/passphrase/PIN generation |
| `strength.py` | Password analysis using zxcvbn, vault health scoring |
| `clipboard.py` | Copy with 15-second auto-clear, emergency cleanup |
| `io.py` | JSON/CSV import/export with path validation |
| `platform_security.py` | Cross-platform file permission enforcement |

**Responsibilities:**
- Provide pure, stateless utility functions
- Use `secrets` module for all randomness (never `random`)
- Document side effects explicitly in docstrings

**What utils must never do:**
- Maintain module-level state (except singleton console)
- Import from screens, widgets, or app
- Access the vault or crypto systems directly

### 3.7 Core Layer (`core/`)

This is the security kernel. Every line of code here is critical.

#### `crypto.py` - The Encryption Engine

**Responsibilities:**
- PBKDF2-HMAC-SHA256 key derivation (480,000 iterations)
- Fernet encryption/decryption (AES-128-CBC + HMAC-SHA256)
- Salt generation using `os.urandom()` (32 bytes)
- Password hashing for runtime verification (SHA-256)
- Constant-time password comparison using `secrets.compare_digest()`
- Best-effort key material wiping

**What crypto.py must never do:**
- Import from vault.py (dependency flows: vault imports crypto)
- Store the master password
- Log, print, or expose any secret material
- Use the `random` module for any purpose

#### `vault.py` - Encrypted Persistence

**Responsibilities:**
- CRUD operations for all 6 credential types
- Exclusive file locking (fcntl on Unix, msvcrt on Windows)
- Atomic writes using temp file + fsync + os.replace
- Backup creation before overwrites
- Salt integrity verification (symlink attack detection, hash comparison)
- Activity tracking for auto-lock timeout

**What vault.py must never do:**
- Implement its own encryption (delegates to CryptoManager)
- Expose decrypted data outside its methods
- Skip file locking or atomic writes
- Store credentials in memory after `lock()` is called

#### `models.py` - Data Structures

**Credential Types:**
- `EmailCredential`: Email/password pairs
- `PhoneCredential`: Phone numbers with PINs
- `CreditCard`: Card details with masked display
- `EnvEntry`: Environment variable files
- `RecoveryEntry`: 2FA backup codes
- `NoteEntry`: Free-form secure notes

**Responsibilities:**
- Type-safe dataclasses with full type hints
- Serialization to/from JSON-compatible dicts
- Security-aware `__repr__` that redacts sensitive fields
- Metadata tracking (id, created_at, updated_at)

**What models must never do:**
- Contain business logic
- Perform I/O operations
- Access the filesystem or network

---

## 4. Data Flow and Trust Boundaries

### 4.1 The Life of a Secret

Here is exactly how sensitive data flows through the system:

```
USER INPUT                 MEMORY                    DISK
-----------               --------                   ----
Master Password  --->  CryptoManager (key)  --->   (never)
                              |
                              v
                       PBKDF2 Derived Key  --->    (never)
                              |
                              v
                       Fernet Instance  --->       (never)
                              |
Credential Data  --->  Python Objects  <--->  Encrypted JSON
(from UI form)         (in vault._data)       (vault.enc)
```

### 4.2 Unlocking the Vault

1. User enters master password in `LoginScreen`
2. Rate limiter checks for lockout (`~/.passfx/lockout.json`)
3. `Vault.unlock()` acquires exclusive file lock
4. Salt loaded from `~/.passfx/salt`
5. Salt file checked for symlinks (attack prevention)
6. `CryptoManager` derives key via PBKDF2 (480k iterations)
7. `vault.enc` is read and decrypted with Fernet
8. JSON is parsed into credential objects
9. Activity timestamp is recorded for auto-lock
10. Lock is released; vault is now "unlocked" in memory

### 4.3 Saving a Credential

1. User fills form in screen modal
2. Credential object is created with generated ID
3. `vault.add_*()` method called
4. File lock acquired
5. Salt integrity verified (hash comparison)
6. All credentials serialized to JSON
7. JSON encrypted with Fernet
8. Backup created (`vault.enc.bak`)
9. Atomic write: temp file -> fsync -> os.replace -> directory fsync
10. File permissions set to 0o600
11. Lock released

### 4.4 Locking the Vault

1. `vault.lock()` called (explicit or via auto-lock)
2. `CryptoManager.wipe()` overwrites key material with zeros
3. `vault._data` cleared (all credential objects removed)
4. `vault._crypto` set to None
5. `vault._cached_salt_hash` cleared
6. Clipboard cleared via `emergency_cleanup()`

### 4.5 Trust Boundaries

```
+------------------------------------------------------------------+
|                    UNTRUSTED: Outside World                       |
|   - User input (keyboard)                                         |
|   - Clipboard (shared with other apps)                            |
|   - File system (other processes can read if permissions wrong)   |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                    BOUNDARY: Input Validation                     |
|   - Master password strength validation                           |
|   - Path validation (no symlinks, home directory bounds)          |
|   - Credential data sanitization                                  |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                    TRUSTED: Core Security Kernel                  |
|   - CryptoManager (encryption, key derivation)                    |
|   - Vault (atomic persistence, file locking)                      |
|   - platform_security (permission enforcement)                    |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                    PROTECTED: Encrypted Storage                   |
|   - ~/.passfx/vault.enc (0o600)                                   |
|   - ~/.passfx/salt (0o600)                                        |
|   - ~/.passfx/ directory (0o700)                                  |
+------------------------------------------------------------------+
```

### 4.6 Where Secrets Must Never Appear

| Location | Why |
|----------|-----|
| Log files | Attacker with read access gets credentials |
| Exception messages | Stack traces can be logged or displayed |
| `__repr__` output | Debug printing can leak secrets |
| Clipboard (after 15s) | Other apps can read it |
| Process arguments | Visible in `ps` output |
| Environment variables | Inherited by child processes |
| Disk (plaintext) | The entire point of this application |

---

## 5. Testing as Architecture

Tests are not an afterthought. They are load-bearing walls in the architecture.

### 5.1 Test Categories as Layers

```
tests/
+-- unit/              Maps to: Core Layer (isolated functions)
|   +-- core/          100% coverage required
|   +-- utils/         95% coverage target
|
+-- integration/       Maps to: Cross-layer interactions
|                      Real encryption, real file I/O
|
+-- security/          Maps to: Threat model validation
|                      Attack scenarios, invariant checks
|
+-- regression/        Maps to: Security contracts
|                      Lock-in tests for crypto parameters
|
+-- edge/              Maps to: Failure modes
|                      Disk full, permissions denied, corruption
|
+-- app/               Maps to: Application lifecycle
+-- cli/               Maps to: Entry point behavior
+-- screens/           Maps to: UI component logic
```

### 5.2 Why Tests Are Architectural

**Security tests enforce invariants that code review alone cannot guarantee:**

- `test_pbkdf2_iterations_meet_owasp_minimum`: If someone changes `PBKDF2_ITERATIONS` to 1000 "for faster tests," this test fails. The 480,000 value is a security contract.

- `test_password_not_logged_on_crypto_init`: Captures all log output and asserts passwords are absent. You cannot accidentally add a debug statement.

- `test_salt_symlink_detected_on_unlock`: Creates a symlink attack scenario and verifies it is blocked. The threat model is executable.

**Regression tests prevent security downgrades:**

Tests in `tests/regression/` use exact value assertions. PBKDF2 iterations must be exactly 480,000, not "at least" 480,000. This ensures any change requires explicit, conscious modification of the test.

### 5.3 Coverage Requirements

| Module | Required Coverage | Rationale |
|--------|------------------|-----------|
| `core/crypto.py` | 100% | One untested path = potential data loss or breach |
| `core/vault.py` | 100% | Persistence bugs corrupt user data |
| `core/models.py` | 95% | Data integrity is critical |
| `utils/generator.py` | 95% | Weak passwords = weak security |
| Overall | 90% minimum | Defense in depth |

### 5.4 What Must Never Be Mocked

- `CryptoManager.derive_key()`
- `CryptoManager.encrypt()` / `decrypt()`
- `generate_salt()`
- `secrets.compare_digest()`

Mocking these defeats the purpose of testing. Security tests must use real cryptographic operations.

---

## 6. Failure Modes and Resilience

### 6.1 The Fail-Secure Principle

When something goes wrong, PassFX fails closed:

| Failure | Response |
|---------|----------|
| Decryption error | Vault locks, memory cleared |
| File permission error | Operation aborted, error surfaced |
| Disk full | Atomic write fails, original vault preserved |
| Corrupted vault | `VaultCorruptedError` raised, vault remains locked |
| Salt integrity violation | `SaltIntegrityError`, vault locks immediately |
| Signal received (SIGINT/SIGTERM) | Emergency cleanup, vault locks, clipboard cleared |

### 6.2 Atomic Write Guarantee

Every vault write follows this pattern:

1. Write to temporary file in vault directory
2. `fsync()` the file (ensure kernel buffer flushed)
3. Set permissions to 0o600
4. `os.replace()` (atomic rename, POSIX guarantee)
5. `fsync()` the directory (ensure rename persisted)

If power is lost at any step before step 4, the original vault remains intact. There is no window where data is partially written.

### 6.3 Backup Strategy

Before every write, the current vault is copied to `vault.enc.bak`. If atomic write fails, the backup is available. Both files have 0o600 permissions.

### 6.4 File Locking

Concurrent access to the vault is prevented via exclusive file locks:

- **Unix**: `fcntl.flock(fd, LOCK_EX | LOCK_NB)`
- **Windows**: `msvcrt.locking(fd, LK_NBLCK, 1)`

Lock acquisition times out after 5 seconds with `VaultLockError`.

### 6.5 Rate Limiting

`LoginScreen` implements persistent rate limiting:

- 3 failed attempts trigger escalating delays
- Maximum lockout: 1 hour
- State persisted in `~/.passfx/lockout.json`
- File corruption resets to clean state (fail-open for usability)

---

## 7. UI Independence and Evolution

### 7.1 The Decoupling Guarantee

The UI layer (`screens/`, `widgets/`, `ui/`) is intentionally decoupled from security logic. This enables:

- **Testability**: Core crypto/vault can be tested without Textual framework
- **Portability**: Core could be reused in a GUI, web interface, or headless tool
- **Auditability**: Security review focuses on `core/`, not CSS styling

### 7.2 What UI Changes Cannot Affect

| Protected Property | Why It Cannot Break |
|--------------------|---------------------|
| Encryption strength | UI never touches CryptoManager |
| File permissions | UI goes through Vault, which calls platform_security |
| Credential storage format | Models are in core, not screens |
| Auto-lock behavior | Vault manages timeouts internally |

### 7.3 What UI Is Allowed to Do

- Change colors, fonts, and layout
- Add new screens (following existing patterns)
- Modify key bindings
- Add visual flourishes (gradients, ASCII art)

### 7.4 What UI Must Never Do

- Import from `core/crypto.py`
- Bypass `Vault` for credential access
- Store credentials in widget state
- Disable or modify security features
- Log credential values for "debugging"

If a UI change requires modifying core, the UI change is wrong.

---

## 8. Architectural Invariants (Non-Negotiable)

These are the rules that must never be broken. They are enforced by tests, CI, and code review.

### 8.1 Cryptographic Invariants

| Invariant | Value | Enforcement |
|-----------|-------|-------------|
| Encryption algorithm | Fernet (AES-128-CBC + HMAC-SHA256) | Regression test |
| Key derivation | PBKDF2-HMAC-SHA256 | Regression test |
| KDF iterations | Exactly 480,000 | Regression test (not >=) |
| Salt length | 32 bytes | Regression test |
| RNG source | `secrets` module only | Security test, code audit |
| Serialization | JSON only (no pickle) | Security test |

### 8.2 File System Invariants

| File | Permission | Enforcement |
|------|------------|-------------|
| `~/.passfx/` | 0o700 | Created with umask, verified on access |
| `vault.enc` | 0o600 | Set after every write |
| `salt` | 0o600 | Set on creation |
| `*.bak` | 0o600 | Set on backup creation |

### 8.3 Memory Invariants

- Master password is never stored (used only for key derivation)
- Derived key is wiped when vault locks
- Credential data is cleared when vault locks
- Clipboard is cleared after 15 seconds or on exit

### 8.4 Layering Invariants

- Core layer has zero UI dependencies
- Utils layer has zero screen/widget dependencies
- Crypto module never imports Vault
- Vault never imports Screens
- Upward dependencies are forbidden

### 8.5 API Invariants

- `Vault.unlock()` is the only way to access credentials
- `Vault.lock()` always clears sensitive data
- All credential access updates `_last_activity` timestamp
- All writes use atomic file operations

---

## 9. For Contributors: How Not to Break the Architecture

Welcome, future maintainer. Here are the mistakes that seem reasonable at 2 AM but will cause pain.

### 9.1 The "Just This Once" Shortcut

**Temptation:** "I need to access a credential from the UI layer. I will just import CryptoManager directly."

**Reality:** You have now bypassed the vault's locking, activity tracking, and file integrity checks. Congratulations, you have created a security hole.

**Solution:** Always go through `app.vault`. If the API is missing something, add a method to Vault.

### 9.2 The Debug Print

**Temptation:** "I will just add a `print(password)` to debug this issue."

**Reality:** Tests will fail. The security suite captures logs and asserts secrets are absent. Even if you remove it before committing, you have trained your fingers to type dangerous patterns.

**Solution:** Use breakpoints. Use logging for events, never for values. If you must see a value, use a debugger with explicit acknowledgment.

### 9.3 The Faster Test

**Temptation:** "PBKDF2 is slow. I will reduce iterations to 100 for tests."

**Reality:** The regression test will fail. Even if you change the test, you have now made it possible for production to ship with weak parameters.

**Solution:** Use pytest markers to skip slow tests during development. Run the full suite before committing.

### 9.4 The Convenient Global

**Temptation:** "I need access to the vault from a utility function. I will add a global reference."

**Reality:** You have created hidden state. Tests will interfere with each other. The vault lifecycle becomes unpredictable.

**Solution:** Pass dependencies explicitly. If a utility needs vault access, it is not a utility. Move it to the app or screen layer.

### 9.5 The "Helpful" Recovery Feature

**Temptation:** "Users forget passwords. I will add a recovery mechanism."

**Reality:** Any recovery mechanism either stores the password (forbidden) or weakens the encryption (forbidden). The zero-knowledge design is intentional.

**Solution:** Document the importance of password backup. Recommend users store their master password in a physical location.

### 9.6 The New Dependency

**Temptation:** "This library makes password hashing easier."

**Reality:** Every dependency is an attack surface. The `cryptography` library is large, well-audited, and stable. Random PyPI packages are not.

**Solution:** Use `cryptography` for crypto. Use stdlib where possible. Any new dependency requires security review.

### 9.7 The "Temporary" Pickle

**Temptation:** "JSON is slow. I will use pickle for internal serialization."

**Reality:** Pickle enables arbitrary code execution. It is explicitly banned in security tests. An attacker who can write to your vault file can now execute code on deserialization.

**Solution:** JSON only. Always. Forever.

---

## Appendix A: File System Layout

```
~/.passfx/
+-- vault.enc           Encrypted JSON blob (Fernet)
+-- vault.enc.bak       Backup from last write
+-- salt                32-byte random salt for PBKDF2
+-- lockout.json        Rate limiting state
+-- .vault_*.tmp        Atomic write temp files (cleaned up)
+-- logs/               Log directory (if enabled)
    +-- *.log           Log files
```

All files are created with 0o600 permissions. The directory is 0o700.

---

## Appendix B: Exception Hierarchy

```
Exception
+-- CryptoError
|   +-- DecryptionError     Wrong password or corrupted data
|
+-- VaultError
    +-- VaultNotFoundError  Vault file does not exist
    +-- VaultCorruptedError JSON parse failed, salt missing
    +-- VaultLockError      Could not acquire file lock
    +-- SaltIntegrityError  Salt was modified or is a symlink
```

All exceptions intentionally hide sensitive details. Error messages are user-safe.

---

## Appendix C: Security Checklist for Code Review

Before approving any PR:

- [ ] No logging of passwords, PINs, CVVs, or master passwords
- [ ] No use of `random` module for security (only `secrets`)
- [ ] No new dependencies without security justification
- [ ] No pickle usage anywhere
- [ ] File permissions set correctly (0o600/0o700)
- [ ] Atomic writes for all persistent data
- [ ] Sensitive data cleared on lock/exit
- [ ] No upward layer dependencies
- [ ] Tests exist for new security-relevant code
- [ ] No credential storage in UI layer

---

*Document maintained by the PassFX Engineering Team.*
*Last updated: Based on codebase analysis December 2025.*
