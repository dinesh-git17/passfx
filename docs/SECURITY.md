# Security Policy

PassFX is a password manager. The only thing standing between your credentials and the void is the code in this repository. We take that responsibility seriously.

This document describes our security philosophy, how to report vulnerabilities, and what we expect from contributors touching security-sensitive code. If you find a hole in our defenses, we want to hear about it—preferably before anyone else does.

---

## Table of Contents

1. [Security Philosophy](#security-philosophy)
2. [Supported Versions](#supported-versions)
3. [Reporting a Vulnerability](#reporting-a-vulnerability)
4. [Responsible Disclosure Guidelines](#responsible-disclosure-guidelines)
5. [Scope of Security Issues](#scope-of-security-issues)
6. [Security Architecture](#security-architecture)
7. [Platform-Specific Considerations](#platform-specific-considerations)
8. [Security Best Practices for Contributors](#security-best-practices-for-contributors)
9. [Acknowledgments](#acknowledgments)
10. [Safe Harbor](#safe-harbor)

---

## Security Philosophy

PassFX operates on three core principles:

**Defense in Depth**: We layer protections. Encryption at rest. Restrictive file permissions. Auto-lock timeouts. Memory wiping. Clipboard clearing. If one layer fails, others remain. Belt and suspenders, except the suspenders are also encrypted.

**Fail Securely**: When something goes wrong, we lock the vault first and ask questions later. Decryption failure? Lock. Suspicious file modification? Lock. Anything unexpected? You guessed it—lock.

**Least Privilege**: We request only what we need. No network access. No cloud sync. No telemetry. Your secrets stay on your disk, encrypted, where you left them.

We use well-audited cryptographic primitives from the `cryptography` library. We do not invent our own algorithms. The crypto community has produced battle-tested solutions; we simply apply them correctly.

---

## Supported Versions

We maintain security patches only for supported versions. Running unsupported software is like using a padlock you found in a parking lot—technically functional, but inadvisable.

| Version | Status      | Notes                                             |
| ------- | ----------- | ------------------------------------------------- |
| 1.x     | Supported   | Current stable release line                       |
| main    | Supported   | Latest development (may contain unreleased fixes) |
| 0.x     | Unsupported | Pre-release; upgrade immediately                  |

When we release a security patch, we strongly recommend updating within 48 hours for critical issues. Version pinning is fine for reproducibility; version fossilization is not.

---

## Reporting a Vulnerability

If you discover a security vulnerability in PassFX, please report it privately. Public disclosure before a fix is available puts users at risk.

### Preferred Method: GitHub Security Advisories

Use GitHub's **[Private Vulnerability Reporting](https://github.com/dinesh-git17/passfx/security/advisories/new)** feature. This creates a private space where we can discuss the issue, collaborate on a fix, and coordinate disclosure.

### Alternative Method: Email

If you cannot use GitHub, email us at `security@dineshd.dev`. Please include "SECURITY" in the subject line so we can prioritize appropriately.

### What to Include

A good vulnerability report contains:

- **Description**: What is the vulnerability? Be specific.
- **Reproduction steps**: How can we trigger it? Proof-of-concept code is helpful.
- **Impact assessment**: What can an attacker do with this? Data disclosure? Privilege escalation? Denial of service?
- **Affected versions**: Which versions did you test?
- **Suggested mitigation**: If you have ideas for a fix, we welcome them.

### What Not to Include

Please do not include:

- Actual passwords, credentials, or real user data (use test data)
- Exploit code designed for malicious use beyond proof-of-concept
- Information about other users' systems or data

### Response Timeline

We commit to the following:

| Stage                  | Timeframe                  |
| ---------------------- | -------------------------- |
| Acknowledgment         | Within 48 hours            |
| Validation             | Within 5 business days     |
| Patch development      | Priority based on severity |
| Coordinated disclosure | After patch is available   |

For critical vulnerabilities (remote code execution, credential disclosure), we drop everything. For lower-severity issues, we balance urgency against thoroughness. Either way, you will hear from us.

---

## Responsible Disclosure Guidelines

We operate on the principle that security researchers and maintainers are on the same team. The goal is protecting users, not scoring points.

### What We Ask

1. **Report privately first**. Give us time to fix the issue before public disclosure.
2. **Do not exploit the vulnerability** beyond what is necessary for proof-of-concept.
3. **Do not access, modify, or delete other users' data** during your research.
4. **Do not perform automated scanning** on production systems without prior approval.
5. **Work with us on disclosure timing**. We aim for 90 days maximum, but complex issues may require coordination.

### What We Promise

1. **We will acknowledge your report promptly** and keep you informed of our progress.
2. **We will not pursue legal action** against researchers acting in good faith within this policy.
3. **We will credit you publicly** (if you wish) when the fix is released.
4. **We will be transparent** about the issue once it is resolved.

Security research is difficult, often thankless work. We appreciate researchers who help us find bugs before attackers do. Future maintainers will thank you. Users will thank you. We thank you now.

---

## Scope of Security Issues

Not every bug is a security vulnerability. This section clarifies what we consider reportable security issues versus general bugs or user-side problems.

### In Scope (Report as Security Issue)

**Cryptographic weaknesses**

- Flaws in our Fernet (AES-128-CBC + HMAC-SHA256) implementation
- Key derivation issues (PBKDF2 parameter problems, salt handling)
- IV reuse, nonce misuse, or other crypto misconfigurations

**Data disclosure**

- Credentials appearing in logs, error messages, or stack traces
- Secrets persisting in memory after vault lock
- Plaintext data written to disk (swap, temp files, core dumps)

**Authentication bypass**

- Any path that unlocks the vault without the correct master password
- Rate limiting bypass that enables brute force attacks

**Injection attacks**

- TUI rendering bugs allowing code execution via malicious input
- Path traversal enabling file access outside intended directories

**Integrity violations**

- Ability to modify vault contents without detection
- Salt or vault tampering that goes unnoticed

**Side-channel attacks**

- Timing attacks on password verification
- Observable differences in behavior based on secret values

### Out of Scope (Not a Security Issue for PassFX)

**Compromised host environment**
If the user's machine has malware, keyloggers, or rootkits, PassFX cannot protect them. We assume the operating system is trustworthy. This is not passing the buck—it is acknowledging the threat model boundary.

**Physical access attacks**
If an attacker has physical access to an unlocked device (or a $5 wrench), cryptography provides limited protection. Full-disk encryption and physical security are the user's responsibility.

**Weak master passwords**
We enforce minimum complexity requirements (12+ characters, mixed case, numbers, symbols). We cannot prevent a determined user from choosing "Tr0ub4dor&3" and feeling clever about it.

**Social engineering**
Phishing attacks, pretexting, and other human-layer attacks are out of scope. PassFX is software; it cannot fix wetware.

**Denial of service via resource exhaustion**
If someone can run arbitrary code to exhaust CPU/memory, they already have bigger problems than PassFX.

### Where to Report Non-Security Bugs

General bugs (UI glitches, crashes, feature requests) should be reported via [GitHub Issues](https://github.com/dinesh-git17/passfx/issues). Please confirm the issue is not security-related before filing publicly.

---

## Security Architecture

PassFX implements security through layered defenses. Each layer addresses different threat vectors.

```
+-------------------------------------------------------------------+
|                    PassFX Security Layers                         |
+-------------------------------------------------------------------+
|  Layer 1: Encryption at Rest                                      |
|  - Fernet (AES-128-CBC + HMAC-SHA256)                             |
|  - PBKDF2-HMAC-SHA256 with 480,000 iterations                     |
|  - 32-byte (256-bit) cryptographically random salt                |
+-------------------------------------------------------------------+
|  Layer 2: File System Protection                                  |
|  - Unix: Mode 0600 for files, 0700 for directories                |
|  - Windows: DACL restricting access to current user only          |
|  - Symlink attack detection and prevention                        |
+-------------------------------------------------------------------+
|  Layer 3: Runtime Protection                                      |
|  - Auto-lock after inactivity timeout                             |
|  - Memory wiping on lock (best-effort, Python limitations apply)  |
|  - No secrets in logs, exceptions, or error messages              |
|  - Clipboard auto-clear (15 seconds)                              |
+-------------------------------------------------------------------+
|  Layer 4: Integrity Protection                                    |
|  - Salt integrity verification (detects tampering)                |
|  - Atomic file writes with fsync (crash safety)                   |
|  - File locking for concurrent access prevention                  |
+-------------------------------------------------------------------+
|  Layer 5: Authentication Hardening                                |
|  - Constant-time password comparison (timing attack resistant)    |
|  - Rate limiting with exponential backoff (max 1 hour lockout)    |
|  - Persistent lockout state (survives application restart)        |
+-------------------------------------------------------------------+
```

### Cryptographic Parameters

| Parameter      | Value                      | Rationale                                   |
| -------------- | -------------------------- | ------------------------------------------- |
| Encryption     | Fernet                     | AES-128-CBC with HMAC-SHA256 authentication |
| Key derivation | PBKDF2-HMAC-SHA256         | Well-audited, widely supported              |
| Iterations     | 480,000                    | Exceeds OWASP 2023 recommendations          |
| Salt length    | 32 bytes                   | 256 bits of entropy                         |
| RNG source     | `os.urandom()` / `secrets` | Cryptographically secure only               |

These parameters are locked in by regression tests. Any PR attempting to weaken them will fail CI.

---

## Platform-Specific Considerations

PassFX runs on Linux, macOS, and Windows. Each platform has different security characteristics.

### File Permission Implementation

| Platform    | Mechanism              | Effect                                 |
| ----------- | ---------------------- | -------------------------------------- |
| Linux/macOS | Unix mode bits         | `chmod 0600` / `chmod 0700`            |
| Windows     | DACL via Security APIs | Access restricted to current user only |

On Windows, we use `ctypes` to call native Security APIs directly. No `pywin32` dependency required. ACLs are reapplied after atomic rename operations to ensure they persist.

### Known Limitations

These are inherent to the Python runtime and cannot be fully mitigated at the application level:

**Memory management**
Python strings are immutable. We cannot reliably overwrite sensitive data in memory. We make best-effort attempts using `ctypes.memset`, but garbage collection timing is unpredictable. Users with extreme security requirements should consider compiled-language alternatives or encrypted swap.

**Swap and hibernation**
Python cannot lock memory to prevent it from being swapped to disk. On sensitive machines:

- Linux: Use encrypted swap (`cryptswap`)
- macOS: Enable FileVault
- Windows: Enable BitLocker or disable the pagefile

**Privilege escalation**
Users with administrative access (root on Unix, SeDebugPrivilege on Windows) can read process memory regardless of application-level protections. This is a fundamental limitation of the operating system security model.

### Recommendations for High-Security Environments

1. Enable full-disk encryption (FileVault, LUKS, BitLocker)
2. Use encrypted swap or disable swap entirely
3. Disable core dumps (`ulimit -c 0` on Unix)
4. Restrict administrative access to the machine
5. Keep the operating system and dependencies updated
6. Use a strong master password (we enforce minimums, but longer is better)

---

## Security Best Practices for Contributors

If you contribute code to PassFX, especially in security-sensitive areas (`core/crypto.py`, `core/vault.py`), these rules are non-negotiable.

### Absolute Rules

**Never log secrets**

```python
# Forbidden - this will fail code review
logger.debug(f"Unlocking with password: {password}")
print(f"Key derived: {key.hex()}")
```

**Never use the `random` module for security**

```python
# Forbidden
import random
salt = bytes([random.randint(0, 255) for _ in range(32)])

# Required
import secrets
salt = secrets.token_bytes(32)
```

**Never implement custom cryptography**
Use the `cryptography` library. Do not roll your own AES implementation. Do not invent new key derivation schemes. Do not create novel authentication mechanisms. The road to cryptographic disaster is paved with clever ideas.

**Never weaken security parameters**
PBKDF2 iterations stay at 480,000 or higher. Salt stays at 32 bytes. Fernet stays as the encryption primitive. Regression tests enforce these values.

**Never use pickle for credential serialization**
Pickle allows arbitrary code execution during deserialization. We use JSON exclusively.

**Never store master passwords**
The master password exists only in memory, only while needed. It is never written to disk, not even encrypted.

### Code Review Requirements

Security-sensitive changes require:

- 100% test coverage for new code paths
- No skipping of security markers in tests
- Explicit sign-off in the PR checklist
- Review by a maintainer before merge

### Memory Handling

When working with sensitive data:

```python
# Pattern for cleanup
try:
    sensitive_data = decrypt(ciphertext)
    process(sensitive_data)
finally:
    # Best-effort wipe
    if sensitive_data:
        wipe(sensitive_data)
```

Assume anything you allocate might persist. Clean up explicitly. Do not rely on scope exit or garbage collection.

### Error Messages

Error messages must be safe for logging:

```python
# Forbidden - leaks password
raise DecryptionError(f"Failed to decrypt with password: {password}")

# Correct - generic message
raise DecryptionError("Decryption failed - invalid password or corrupted data")
```

The user does not need their password echoed back in an error message. Neither do potential attackers reading logs.

---

## Acknowledgments

We believe in recognizing those who help make PassFX more secure. Researchers who responsibly disclose vulnerabilities may be credited here (with permission) after the fix is released.

### Hall of Gratitude

_No entries yet. Perhaps you will be the first._

We do not operate a formal bug bounty program, but we offer sincere gratitude and public recognition. Future users who never experience a breach because of your report will unknowingly appreciate your contribution.

If you prefer to remain anonymous, we respect that. The fix matters more than the fame.

---

## Safe Harbor

PassFX supports security research conducted in good faith.

If you:

- Act in accordance with this policy
- Report vulnerabilities through designated channels
- Avoid accessing, modifying, or deleting other users' data
- Do not exploit vulnerabilities beyond proof-of-concept

Then we will:

- Not pursue legal action against you
- Work with you to understand and resolve the issue
- Credit you publicly (if desired) when the fix is released

Security research is essential to software safety. We will not retaliate against researchers who help us protect our users.

This safe harbor applies to research conducted within the scope defined in this document. Activities that cause harm to users, systems, or data—or that violate applicable law—are not covered.

---

## Contact

- **Security issues**: `security@dineshd.dev` or [GitHub Security Advisories](https://github.com/dinesh-git17/passfx/security/advisories/new)
- **General bugs**: [GitHub Issues](https://github.com/dinesh-git17/passfx/issues)
- **Questions**: [GitHub Discussions](https://github.com/dinesh-git17/passfx/discussions)

---

_Your secrets deserve paranoid software. We aim to deliver._
