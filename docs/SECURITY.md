# Security Policy

PassFX is a password manager. The only thing standing between your credentials and the void is the code in this repository. We take that responsibility seriously.

This document describes our security philosophy, how to report vulnerabilities, and what we expect from contributors touching security-sensitive code. If you find a hole in our defenses, we want to hear about it—preferably before anyone else does.

---

## Table of Contents

1. [Security Philosophy](#security-philosophy)
2. [Security Assessment](#security-assessment)
3. [Supported Versions](#supported-versions)
4. [Reporting a Vulnerability](#reporting-a-vulnerability)
5. [Responsible Disclosure Guidelines](#responsible-disclosure-guidelines)
6. [Scope of Security Issues](#scope-of-security-issues)
7. [Security Architecture](#security-architecture)
8. [Platform-Specific Considerations](#platform-specific-considerations)
9. [Security Best Practices for Contributors](#security-best-practices-for-contributors)
10. [Acknowledgments](#acknowledgments)
11. [Safe Harbor](#safe-harbor)

---

## Security Philosophy

PassFX operates on three core principles:

**Defense in Depth**: We layer protections. Encryption at rest. Restrictive file permissions. Auto-lock timeouts. Memory wiping. Clipboard clearing. If one layer fails, others remain. Belt and suspenders, except the suspenders are also encrypted.

**Fail Securely**: When something goes wrong, we lock the vault first and ask questions later. Decryption failure? Lock. Suspicious file modification? Lock. Anything unexpected? You guessed it—lock.

**Least Privilege**: We request only what we need. No network access. No cloud sync. No telemetry. Your secrets stay on your disk, encrypted, where you left them.

We use well-audited cryptographic primitives from the `cryptography` library. We do not invent our own algorithms. The crypto community has produced battle-tested solutions; we simply apply them correctly.

---

## Security Assessment

A comprehensive internal penetration test was conducted against PassFX covering filesystem operations, cryptographic implementation, runtime behavior, UI components, clipboard handling, signal processing, search functionality, and shutdown paths.

**Threat Model:** Local attacker with user-level access but without the master password.

**Conclusion:** PassFX is secure for its intended use. No vulnerabilities were found that allow vault data extraction without the master password.

The assessment validated the following controls:

- PBKDF2-HMAC-SHA256 key derivation (480,000 iterations)
- Authenticated encryption via Fernet (AES-128-CBC + HMAC-SHA256)
- Strict filesystem permissions (0700 directories, 0600 files)
- Clipboard auto-clearing, auto-lock, and secure shutdown handling
- Secret redaction in logs, exceptions, and search results
- Timing-safe password comparison and rate limiting

**Known Limitations:** Python's memory model prevents reliable secret wiping—this is an inherent platform constraint affecting all Python credential managers and is documented in the codebase. Root-level attackers with debugger access fall outside the threat model.

PassFX is appropriate for offline personal password management and meets modern security expectations.

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

### Response Timeline

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
4. **Work with us on disclosure timing**. We aim for 90 days maximum, but complex issues may require coordination.

### What We Promise

1. **We will acknowledge your report promptly** and keep you informed of our progress.
2. **We will not pursue legal action** against researchers acting in good faith within this policy.
3. **We will credit you publicly** (if you wish) when the fix is released.
4. **We will be transparent** about the issue once it is resolved.

---

## Scope of Security Issues

### In Scope (Report as Security Issue)

- Cryptographic weaknesses (Fernet implementation, key derivation, salt handling)
- Data disclosure (credentials in logs, error messages, or stack traces)
- Authentication bypass (unlocking vault without correct password)
- Rate limiting bypass enabling brute force
- Injection attacks or path traversal
- Integrity violations (undetected vault tampering)
- Side-channel attacks (timing attacks on password verification)

### Out of Scope

- **Compromised host environment**: Malware, keyloggers, or rootkits on the user's machine
- **Physical access attacks**: Attacker with physical access to unlocked device
- **Weak master passwords**: We enforce complexity requirements; user choices beyond that are their own
- **Social engineering**: Phishing and human-layer attacks
- **Denial of service**: Resource exhaustion by arbitrary code execution

General bugs should be reported via [GitHub Issues](https://github.com/dinesh-git17/passfx/issues).

---

## Security Architecture

PassFX implements security through layered defenses:

| Layer                       | Implementation                                           |
| --------------------------- | -------------------------------------------------------- |
| Encryption at Rest          | Fernet (AES-128-CBC + HMAC-SHA256), PBKDF2 480k iterations, 32-byte salt |
| File System Protection      | Unix mode 0600/0700, Windows DACL, symlink detection     |
| Runtime Protection          | Auto-lock, memory wiping, clipboard auto-clear, no secrets in logs |
| Integrity Protection        | Salt verification, atomic writes with fsync, file locking |
| Authentication Hardening    | Constant-time comparison, exponential backoff rate limiting |

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

### File Permissions

| Platform    | Mechanism              | Effect                                 |
| ----------- | ---------------------- | -------------------------------------- |
| Linux/macOS | Unix mode bits         | `chmod 0600` / `chmod 0700`            |
| Windows     | DACL via Security APIs | Access restricted to current user only |

### Known Limitations

**Memory management**: Python strings are immutable. We cannot reliably overwrite sensitive data in memory. Best-effort cleanup is implemented.

**Swap and hibernation**: Python cannot lock memory. For sensitive environments, use encrypted swap or full-disk encryption.

**Privilege escalation**: Root/admin users can read process memory regardless of application protections.

### Recommendations for High-Security Environments

1. Enable full-disk encryption (FileVault, LUKS, BitLocker)
2. Use encrypted swap or disable swap entirely
3. Disable core dumps
4. Keep the operating system and dependencies updated

---

## Security Best Practices for Contributors

### Absolute Rules

- **Never log secrets** (passwords, keys, credentials)
- **Never use the `random` module** for security (use `secrets`)
- **Never implement custom cryptography** (use `cryptography` library)
- **Never weaken security parameters** (regression tests enforce this)
- **Never use pickle** for credential serialization (JSON only)
- **Never store master passwords** on disk

### Code Review Requirements

Security-sensitive changes (`core/crypto.py`, `core/vault.py`) require:

- 100% test coverage for new code paths
- Explicit sign-off in the PR checklist
- Maintainer review before merge

---

## Acknowledgments

We believe in recognizing those who help make PassFX more secure. Researchers who responsibly disclose vulnerabilities may be credited here (with permission) after the fix is released.

### Hall of Gratitude

_No entries yet. Perhaps you will be the first._

---

## Safe Harbor

PassFX supports security research conducted in good faith.

If you act in accordance with this policy, report vulnerabilities through designated channels, and avoid accessing or modifying other users' data, we will not pursue legal action against you and will work with you to resolve the issue.

---

## Contact

- **Security issues**: `security@dineshd.dev` or [GitHub Security Advisories](https://github.com/dinesh-git17/passfx/security/advisories/new)
- **General bugs**: [GitHub Issues](https://github.com/dinesh-git17/passfx/issues)
- **Questions**: [GitHub Discussions](https://github.com/dinesh-git17/passfx/discussions)

---

_Your secrets deserve paranoid software. We aim to deliver._
