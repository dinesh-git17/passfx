# PassFX Security Audit Report

**Audit Date:** 2025-12-18
**Version Audited:** 1.0.0
**Audit Type:** Adversarial Red Team + Blue Team Analysis
**Classification:** Internal Security Document

---

## 1. Executive Summary

PassFX is a terminal-based password manager built with Python and Textual, using AES-256 encryption via Fernet. This audit evaluated the application from multiple adversarial perspectives: malicious hackers, ill-intent users, rogue insiders, and sophisticated attackers with local system access.

### Overall Security Posture: **STRONG with Addressable Gaps**

| Category | Rating | Summary |
|----------|--------|---------|
| Cryptography | **A** | Industry-standard implementation, proper KDF parameters |
| Memory Security | **B-** | Best-effort wiping, limited by Python runtime |
| File System Security | **B** | Good permissions, but non-atomic writes |
| CLI/UX Attack Surface | **B+** | Proper input masking, clipboard auto-clear |
| Dependency Security | **B+** | Minimal surface, one missing declaration |
| Adversarial Resilience | **B** | Strong offline defense, weak against local privilege escalation |

### Critical Findings Count

| Severity | Count | Immediate Action Required |
|----------|-------|---------------------------|
| **CRITICAL** | 5 | Yes |
| **HIGH** | 4 | Yes |
| **MEDIUM** | 12 | Recommended |
| **LOW** | 8 | Hardening |

---

## 2. Threat Model Overview

### Assumed Attacker Capabilities

This audit assumed attackers with:
- Local filesystem access (read/write to `~/.passfx/`)
- Ability to read source code
- Ability to inspect process memory, logs, crash dumps
- No knowledge of master password

### Threat Categories Evaluated

| Threat Category | Defense Status |
|-----------------|----------------|
| Remote network attacks | N/A (offline app) |
| Brute-force master password | **STRONG** - 480k PBKDF2 iterations |
| Vault file tampering | **STRONG** - Fernet HMAC integrity |
| Unauthorized file access | **STRONG** - 0600/0700 permissions (Unix) |
| Memory forensics | **WEAK** - Python GC limitations |
| Local privilege escalation | **WEAK** - Cannot defend in Python |
| Clipboard hijacking | **MEDIUM** - 30s auto-clear mitigates |
| Supply chain attacks | **MEDIUM** - Minimal deps, needs pinning |

### Trust Boundaries

```
[User Input] --> [Textual TUI] --> [Vault Manager] --> [CryptoManager] --> [Filesystem]
                      |                   |                  |
                      v                   v                  v
                 [Clipboard]         [Memory]          [vault.enc + salt]
```

---

## 3. Critical Findings (Immediate Action Required)

### CRITICAL-1: Non-Atomic Vault Writes - Data Loss Risk

**Location:** `passfx/core/vault.py:205`
**Severity:** CRITICAL
**Impact:** Complete vault data loss on crash during save

**Issue:** The help screen claims "Atomic file writes" but `_save()` uses `Path.write_bytes()` which is NOT atomic. If the process crashes, is killed, or power fails during write, the vault file will be corrupted or empty.

**Current Code:**
```python
def _save(self) -> None:
    data_json = json.dumps(self._data, indent=2)
    encrypted = self._crypto.encrypt(data_json.encode("utf-8"))
    self.path.write_bytes(encrypted)  # NOT ATOMIC - truncates then writes
```

**Exploit Scenario:** User saves a credential, power fails mid-write, vault.enc is now 0 bytes or corrupted. All credentials lost.

**Recommended Fix:**
```python
import tempfile
import os

def _save(self) -> None:
    data_json = json.dumps(self._data, indent=2)
    encrypted = self._crypto.encrypt(data_json.encode("utf-8"))

    # Atomic write pattern
    temp_fd, temp_path = tempfile.mkstemp(
        dir=self.path.parent, prefix='.vault-', suffix='.tmp'
    )
    try:
        os.write(temp_fd, encrypted)
        os.fsync(temp_fd)
        os.close(temp_fd)
        os.rename(temp_path, self.path)  # Atomic on POSIX
        if os.name != "nt":
            os.chmod(self.path, 0o600)
    except Exception:
        os.unlink(temp_path)
        raise
```

---

### CRITICAL-2: Exported Files World-Readable (0644)

**Location:** `passfx/utils/io.py:46, 163`
**Severity:** CRITICAL
**Impact:** Complete credential exposure on multi-user systems

**Issue:** CSV and JSON exports are created with default umask permissions (typically 0644), making plaintext passwords readable by any local user.

**Current Code:**
```python
# Line 46 - JSON export
path.write_text(json.dumps(export_data, indent=2))  # Creates 0644!

# Line 163 - CSV export
with path.open("w", newline="", encoding="utf-8") as f:
    writer.writeheader()
    writer.writerows(rows)  # PLAINTEXT PASSWORDS, 0644!
```

**Exploit Scenario:** User exports vault to CSV for backup. File created with world-readable permissions. Another user on shared system reads all passwords.

**Recommended Fix:**
```python
import os

def export_vault(...):
    old_umask = os.umask(0o077)  # Restrict new files to owner-only
    try:
        path.write_text(json.dumps(export_data, indent=2))
    finally:
        os.umask(old_umask)

    # Or explicitly chmod after creation
    if os.name != "nt":
        os.chmod(path, 0o600)
```

---

### CRITICAL-3: Dataclass Models Expose Secrets via repr()

**Location:** `passfx/core/models.py:21-419`
**Severity:** CRITICAL
**Impact:** Passwords exposed in exception tracebacks, debug output, logs

**Issue:** All credential dataclasses (`EmailCredential`, `PhoneCredential`, `CreditCard`, etc.) use default `@dataclass` without `repr=False` on sensitive fields. Calling `repr()` or `str()` exposes plaintext secrets.

**Exploit Scenario:**
```python
# If exception occurs with credential in scope:
>>> cred = EmailCredential(email="user@test.com", password="SuperSecret123!")
>>> print(cred)  # Or in traceback
EmailCredential(email='user@test.com', password='SuperSecret123!', ...)
```

**Recommended Fix:**
```python
from dataclasses import dataclass, field

@dataclass
class EmailCredential:
    id: str = field(default_factory=_generate_id)
    email: str = ""
    password: str = field(default="", repr=False)  # Hide from repr
    # ... other fields

    def __repr__(self) -> str:
        return f"EmailCredential(id={self.id!r}, email={self.email!r}, password='***')"
```

---

### CRITICAL-4: Weak Master Password Requirements

**Location:** `passfx/screens/login.py:213-214`
**Severity:** CRITICAL
**Impact:** Entire vault security undermined by weak passwords

**Issue:** Master password minimum is only 8 characters with no complexity or strength requirements. Users can set "password" or "12345678" as their master password.

**Current Code:**
```python
if len(password) < 8:
    error_label.update("[error]Password must be at least 8 characters[/error]")
    return
```

**Exploit Scenario:** User sets master password "Test1234". Attacker captures vault.enc, brute-forces common 8-char passwords. Even with 480k PBKDF2 iterations, weak passwords fall quickly.

**Recommended Fix:**
```python
from zxcvbn import zxcvbn

def _validate_master_password(password: str) -> tuple[bool, str]:
    if len(password) < 12:
        return False, "Password must be at least 12 characters"

    result = zxcvbn(password)
    if result["score"] < 3:
        feedback = result["feedback"]["suggestions"]
        return False, f"Password too weak. {feedback[0] if feedback else 'Try a passphrase.'}"

    return True, ""
```

---

### CRITICAL-5: No Rate Limiting with Persistent Tracking

**Location:** `passfx/screens/login.py:168-197`
**Severity:** HIGH (upgraded from MEDIUM)
**Impact:** Enables scripted brute-force attacks

**Issue:** Failed login attempts (3 max) only tracked in-memory. Attacker can restart app infinitely for unlimited attempts. No exponential backoff.

**Current Code:**
```python
self.attempts += 1  # In-memory only, lost on restart
if remaining > 0:
    error_label.update(f"[error]Wrong password. {remaining} attempt(s) remaining.[/error]")
else:
    self.app.exit()  # Just exit, attacker restarts immediately
```

**Recommended Fix:**
```python
import time
from pathlib import Path

LOCKOUT_FILE = Path.home() / ".passfx" / ".lockout"

def check_lockout() -> tuple[bool, int]:
    """Check if account is locked out. Returns (is_locked, seconds_remaining)."""
    if not LOCKOUT_FILE.exists():
        return False, 0

    data = json.loads(LOCKOUT_FILE.read_text())
    lockout_until = data.get("lockout_until", 0)
    if time.time() < lockout_until:
        return True, int(lockout_until - time.time())
    return False, 0

def record_failed_attempt() -> None:
    """Record failed attempt with exponential backoff."""
    data = {"attempts": 0, "lockout_until": 0}
    if LOCKOUT_FILE.exists():
        data = json.loads(LOCKOUT_FILE.read_text())

    data["attempts"] = data.get("attempts", 0) + 1

    # Exponential backoff: 2^attempts seconds (max 1 hour)
    if data["attempts"] >= 3:
        lockout_seconds = min(2 ** data["attempts"], 3600)
        data["lockout_until"] = time.time() + lockout_seconds

    LOCKOUT_FILE.write_text(json.dumps(data))
    os.chmod(LOCKOUT_FILE, 0o600)
```

---

## 4. High Severity Findings

### HIGH-1: Master Password Lifetime in Memory

**Location:** `passfx/screens/login.py:173-198`, `passfx/app.py:51-67`
**Impact:** Master password recoverable from memory dumps

**Issue:** Master password extracted from Input widget is passed through multiple function calls without explicit cleanup. Python string immutability prevents secure wiping.

**Recommended Mitigation:**
- Document as known Python limitation
- Attempt best-effort cleanup after authentication
- Recommend users lock vault when not in use

---

### HIGH-2: Windows Has No File Permission Enforcement

**Location:** `passfx/core/vault.py:91, 104, 207`
**Impact:** Vault files readable by other Windows users

**Issue:** All `os.chmod()` calls are wrapped in `if os.name != "nt":`, leaving Windows users without permission protection.

**Recommended Fix:** Implement Windows ACL restrictions using `pywin32` or document as platform limitation.

---

### HIGH-3: Missing Dependency Declaration

**Location:** `pyproject.toml`
**Impact:** ImportError for users installing via pip

**Issue:** `simple-term-menu` is imported in `passfx/ui/menu.py` but not declared in `pyproject.toml`.

**Recommended Fix:**
```toml
dependencies = [
    # ... existing deps
    "simple-term-menu>=1.6.0",
]
```

---

### HIGH-4: No Signal Handlers for Cleanup

**Location:** Application-wide
**Impact:** Sensitive data left in memory on abnormal termination

**Issue:** SIGTERM, SIGINT (beyond Textual handling), or crashes bypass vault lock and cleanup routines.

**Recommended Fix:**
```python
import signal
import atexit

def handle_shutdown(signum, frame):
    if vault and vault.is_unlocked():
        vault.lock()
    clipboard_manager.clear()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)
atexit.register(handle_shutdown, None, None)
```

---

## 5. Medium Severity Findings

| ID | Finding | Location | Recommendation |
|----|---------|----------|----------------|
| M-1 | Unused `_password_hash` stored in memory | `crypto.py:48` | Remove - authentication via decryption is sufficient |
| M-2 | Memory wipe is best-effort only | `crypto.py:158-172` | Document limitation, add `gc.collect()` |
| M-3 | Salt file has race window (brief 0644) | `vault.py:103-105` | Use `os.open()` with mode flags |
| M-4 | No backup before vault overwrites | `vault.py:197-208` | Create `.vault.enc.bak` before save |
| M-5 | Path traversal in import/export | `settings.py:78, 133` | Validate paths within home directory |
| M-6 | Passwords visible in view modals | `passwords.py:474`, `cards.py:577` | Add show/hide toggle, default masked |
| M-7 | Notes/envs clipboard lacks auto-clear | `notes.py:246`, `envs.py:268` | Enable `auto_clear=True` for all sensitive data |
| M-8 | No directory fsync after vault write | `vault.py:197-208` | Add `os.fsync(dir_fd)` after rename |
| M-9 | Symlink attacks not prevented | `vault.py` | Check `path.is_symlink()` before operations |
| M-10 | No file locking for concurrent access | `vault.py` | Add `fcntl.flock()` / `msvcrt.locking()` |
| M-11 | Version pinning uses minimum constraints | `pyproject.toml` | Use exact pins or constrained ranges |
| M-12 | Salt integrity not verified | `vault.py:96-98` | Add HMAC to salt or store inside vault |

---

## 6. Low Severity Findings

| ID | Finding | Recommendation |
|----|---------|----------------|
| L-1 | UUID truncation to 8 chars | Increase to 12 chars for collision resistance |
| L-2 | No input length limits | Add `maxlength` to Input widgets |
| L-3 | cryptography 2 versions behind | Upgrade to 46.0.3 |
| L-4 | textual several versions behind | Upgrade to 6.11.0 |
| L-5 | Terminal title reveals app name | Make configurable for OPSEC |
| L-6 | Error messages may leak paths | Sanitize to generic messages |
| L-7 | CONFIG_FILE defined but unused | Remove or implement with 0600 |
| L-8 | Help claims logs dir exists | Remove claim or clarify unused |

---

## 7. What PassFX Does Exceptionally Well

PassFX demonstrates **production-grade security engineering** in several areas:

### Cryptographic Excellence

| Practice | Implementation | Rating |
|----------|----------------|--------|
| Key Derivation | PBKDF2-HMAC-SHA256, 480k iterations | Exceeds OWASP 2023 |
| Encryption | AES-256-CBC via Fernet (authenticated) | Industry standard |
| Salt | 32 bytes, cryptographically random | Excellent |
| RNG | `secrets` module exclusively | Perfect |
| Comparison | `secrets.compare_digest()` | Timing-safe |

### Security-First Design Decisions

1. **No Password Recovery** - By design, lost master password = lost data. No backdoors.

2. **No Custom Crypto** - Uses audited `cryptography` library exclusively.

3. **No Pickle Serialization** - JSON only, preventing arbitrary code execution.

4. **No Secrets in Logs** - Zero instances of password logging found.

5. **Clipboard Auto-Clear** - 30-second timeout with thread-safe implementation.

6. **Input Masking** - All password/PIN inputs use `password=True`.

7. **File Permissions** - Consistent 0600/0700 on Unix (when applied).

8. **Attempt Limiting** - 3 failed attempts before exit (needs persistence).

9. **Auto-Lock** - 5-minute inactivity timeout enabled by default.

10. **Minimal Dependencies** - Only 7 direct dependencies, reducing attack surface.

### Code Quality

- Fully typed codebase with type hints
- Custom exception hierarchy
- No bare `except:` clauses
- Proper error handling without information leakage
- Clean separation of concerns (core/screens/utils/widgets)

---

## 8. Attack Scenarios Walkthrough

### Scenario 1: Local Attacker with Python Debugger

**Attacker:** Local user with debugger privileges
**Goal:** Extract all credentials

**Attack Path:**
1. User unlocks PassFX vault
2. Attacker attaches debugger: `python -m pdb -p <pid>`
3. Extract via introspection: `gc.get_objects()` → find `CryptoManager`
4. Read `_key` (Fernet key) and `vault._data` (decrypted credentials)

**Current Defense:** None (Python limitation)
**Residual Risk:** CRITICAL if attacker has local access
**Recommendation:** Document as out-of-scope, require trusted environment

### Scenario 2: Export File Leakage

**Attacker:** Read access to filesystem (cloud sync, backup)
**Goal:** Obtain all passwords

**Attack Path:**
1. User exports vault to `~/Documents/backup.csv`
2. File created with 0644 permissions (world-readable)
3. Cloud sync uploads plaintext file
4. Attacker gains cloud access, downloads backup
5. All passwords exposed in plaintext CSV

**Current Defense:** None
**Residual Risk:** CRITICAL
**Recommendation:** Fix export permissions (0600), add encryption option

### Scenario 3: Clipboard Monitoring Malware

**Attacker:** Malware with clipboard monitoring
**Goal:** Intercept copied passwords

**Attack Path:**
1. Malware polls clipboard every 100ms
2. User copies password via PassFX
3. Malware captures password within milliseconds
4. 30-second auto-clear is too late

**Current Defense:** 30s auto-clear (partial mitigation)
**Residual Risk:** HIGH if malware present
**Recommendation:** Reduce timeout, document clipboard risks

### Scenario 4: Crash During Vault Save

**Attacker:** None (reliability issue)
**Impact:** Complete data loss

**Attack Path:**
1. User adds new credential, triggers save
2. `write_bytes()` truncates vault.enc to 0 bytes
3. Power failure / crash before write completes
4. vault.enc is now corrupted/empty
5. All credentials permanently lost

**Current Defense:** None
**Residual Risk:** CRITICAL
**Recommendation:** Implement atomic writes with temp file + rename

---

## 9. Defense-in-Depth Evaluation

### Security Layers

| Layer | Implementation | Strength |
|-------|----------------|----------|
| **Encryption at Rest** | AES-256 Fernet | STRONG |
| **Key Derivation** | PBKDF2 480k iterations | STRONG |
| **File Permissions** | 0600/0700 (Unix) | STRONG |
| **Memory Clearing** | `wipe()` method | WEAK (Python GC) |
| **Auto-Lock** | 5-minute timeout | MODERATE |
| **Attempt Limiting** | 3 attempts per session | WEAK (no persistence) |
| **Clipboard Protection** | 30s auto-clear | MODERATE |
| **Integrity Verification** | Fernet HMAC | STRONG |

### Single Points of Failure

1. **Master Password** - If compromised, entire vault accessible (by design)
2. **Python Runtime** - Malicious imports bypass all security
3. **Process Memory** - Local attacker with debug access can extract keys
4. **Salt File** - Replacement enables vault substitution attack

### Layers to Strengthen

1. Add persistent rate limiting across restarts
2. Implement atomic file writes with backup
3. Strengthen master password requirements
4. Add signal handlers for graceful shutdown

---

## 10. Recommendations & Next Steps

### Priority 0 - Immediate (Before Next Release)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 1 | Fix export file permissions (0600) | 30 min | Prevents credential leak |
| 2 | Implement atomic vault writes | 2 hours | Prevents data loss |
| 3 | Add `repr=False` to sensitive dataclass fields | 1 hour | Prevents traceback leaks |
| 4 | Strengthen master password requirements | 2 hours | Improves base security |
| 5 | Add missing `simple-term-menu` dependency | 5 min | Fixes installation |

### Priority 1 - High (This Sprint)

| # | Action | Effort |
|---|--------|--------|
| 6 | Implement persistent rate limiting | 3 hours |
| 7 | Add signal handlers for cleanup | 2 hours |
| 8 | Add vault backup before save | 1 hour |
| 9 | Exact version pinning in pyproject.toml | 30 min |

### Priority 2 - Medium (Next Sprint)

| # | Action | Effort |
|---|--------|--------|
| 10 | File locking for concurrent access | 3 hours |
| 11 | Symlink attack prevention | 1 hour |
| 12 | Salt integrity verification | 2 hours |
| 13 | Windows ACL implementation | 4 hours |
| 14 | Upgrade cryptography to 46.0.3 | 30 min |

### Priority 3 - Hardening (Backlog)

- Clipboard timeout configurability
- Show/hide toggle for view modals
- Document threat model in README
- Memory page locking investigation (mlock)

---

## 11. Final Security Verdict

### Summary

PassFX is a **well-engineered password manager** with strong cryptographic foundations. The development team has made excellent security decisions in:
- Choosing industry-standard encryption (AES-256 via Fernet)
- Using proper key derivation (PBKDF2 with 480k iterations)
- Implementing timing-safe comparisons
- Avoiding dangerous patterns (pickle, eval, custom crypto)

However, several **critical gaps** must be addressed before production deployment:
1. Non-atomic file writes risk data loss
2. Export files expose credentials on multi-user systems
3. Weak master password requirements undermine encryption strength
4. Dataclass repr() can leak secrets in tracebacks

### Risk Rating

| Environment | Risk Level | Recommendation |
|-------------|------------|----------------|
| Single-user desktop | **MODERATE** | Deploy after P0 fixes |
| Multi-user system | **HIGH** | Do not deploy until export permissions fixed |
| Shared/enterprise | **HIGH** | Requires Windows ACL + additional hardening |
| Hostile environment | **CRITICAL** | Not suitable (Python memory limitations) |

### Certification

**Current Status:** NOT READY for production deployment

**After P0 Fixes:** APPROVED for single-user desktop deployment

**Conditional Approval Requirements:**
1. All Priority 0 items resolved
2. Security documentation updated
3. User education on threat model limitations

---

## Appendix A: Files Audited

```
passfx/
├── app.py                 # Application entry, vault management
├── cli.py                 # CLI entry point
├── core/
│   ├── crypto.py          # CRITICAL - Encryption operations
│   ├── vault.py           # CRITICAL - Encrypted storage
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
│   ├── settings.py        # Configuration/export
│   ├── recovery.py        # Recovery codes
│   └── help.py            # Help screen
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

## Appendix B: Tools Used

- Static analysis: Manual code review
- Dependency scanning: pip-audit, Snyk database
- Security patterns: OWASP guidelines, project coding standards
- Cryptographic review: NIST SP 800-132, OWASP password storage

## Appendix C: Auditor Notes

This audit was conducted with full source code access, simulating an attacker who has obtained the PassFX codebase. The findings represent a worst-case scenario analysis where the attacker understands all implementation details.

PassFX's security model correctly assumes:
- The master password is the root of trust
- Local filesystem permissions are enforced by the OS
- The Python runtime is not compromised

PassFX's security model does NOT defend against:
- Attackers with root/admin access
- Compromised Python interpreters
- Hardware-level attacks (cold boot, DMA)
- Physical coercion

---

**Report Generated:** 2025-12-18
**Next Audit Recommended:** After Priority 0 fixes implemented
