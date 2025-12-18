# Security Policy

First off, thank you for taking the time to responsibly disclose vulnerabilities. We take security seriously—PassFX is a password manager, so trust is our only currency.

## 📦 Supported Versions

We only support the latest stable release and the current `main` branch. Older versions are considered unsupported.

| Version | Supported          |
| ------- | ------------------ |
| `1.x`   | :white_check_mark: |
| `0.x`   | :x:                |
| `main`  | :white_check_mark: |

## 🐞 Reporting a Vulnerability

**DO NOT file a public issue.** If you believe you have found a security vulnerability in PassFX, please report it privately.

### Preferred Method (GitHub)

Please use the **[Private Vulnerability Reporting](https://github.com/dinesh-git17/passfx/security/advisories/new)** feature on this repository. This allows us to collaborate on a fix in a private space.

### Alternative Method (Email)

If you cannot use GitHub reporting, email us at `security@dineshd.dev`

- Please include "SECURITY" in the subject line.
- If possible, encrypt your message using our PGP key (ID: `0xDEADBEEF` - _Coming Soon_).

### What to Include

- Description of the vulnerability.
- Steps to reproduce the issue (PoC code is appreciated).
- The impact of the vulnerability.
- Any potential mitigations you have identified.

## 🎯 Threat Model & Scope

To help you focus your research, here is what we consider in-scope and out-of-scope.

### In Scope (We want to know about these)

- **Cryptographic Weaknesses:** Flaws in our implementation of Fernet (AES-128-CBC with HMAC-SHA256) or PBKDF2.
- **Data Leaks:** Credentials appearing in logs, unencrypted swap, or persisting in memory after a "lock" event.
- **Side-Channel Attacks:** Timing attacks on password verification or key derivation.
- **Injection:** TUI rendering bugs that allow arbitrary code execution via malicious payloads.

### Out of Scope (Please do not report these)

- **Compromised Host:** If the user's machine has malware/keyloggers/rootkits, PassFX cannot protect them. We assume the host OS is trusted.
- **Physical Access:** If an attacker has the unlocked device and a $5 wrench, cryptography is irrelevant.
- **Weak Master Passwords:** We enforce complexity rules, but we cannot stop a user from using "Password123!" if they really try.
- **Social Engineering:** Phishing attacks against the user.

---

## 🖥️ Platform-Specific Security

PassFX implements platform-specific security measures. Users should be aware of the following platform differences and limitations.

### File Permission Enforcement

| Platform | Mechanism | Vault/Salt Files | Exported Files |
| -------- | --------- | ---------------- | -------------- |
| **Linux/macOS** | Unix mode bits | `0600` (owner rw) | `0600` (owner rw) |
| **Windows** | DACL (ACLs) | Current user only | Current user only |

**Windows Implementation Details:**

PassFX uses native Windows Security APIs via `ctypes` to set Discretionary Access Control Lists (DACLs) on sensitive files. This restricts access to the current user only, providing equivalent protection to Unix `0600` permissions.

- Vault file (`vault.enc`): Restricted to current user
- Salt file (`salt`): Restricted to current user
- Backup file (`vault.enc.bak`): Restricted to current user
- Exported files (JSON/CSV): Restricted to current user

### Known Platform Limitations

#### All Platforms (Python Runtime Constraints)

| Limitation | Impact | Mitigation |
| ---------- | ------ | ---------- |
| **Python strings are immutable** | Sensitive data (passwords, keys) cannot be reliably overwritten in memory | Best-effort memory wiping attempted via `ctypes.memset`; consider using a compiled language for higher security requirements |
| **Garbage collection timing** | Memory containing secrets may persist until GC runs | Explicit cleanup calls made; GC is triggered on vault lock |
| **No memory locking** | Python cannot prevent memory from being swapped to disk | Users with high security requirements should use encrypted swap or disable swap entirely |

#### Windows-Specific

| Limitation | Impact | Mitigation |
| ---------- | ------ | ---------- |
| **No native mlock()** | Memory cannot be locked to prevent swapping | Use Windows with BitLocker or disable pagefile for sensitive machines |
| **Admin/Debug privilege escalation** | Users with `SeDebugPrivilege` can read process memory | Run on machines where admin access is controlled |
| **ACL propagation on file rename** | ACLs may not persist through atomic rename operations | PassFX re-applies ACLs after each rename operation |

#### Linux-Specific

| Limitation | Impact | Mitigation |
| ---------- | ------ | ---------- |
| **Root bypass** | Root user can read any file regardless of permissions | Standard Unix security model; use disk encryption |
| **ptrace attacks** | Processes with `CAP_SYS_PTRACE` can read memory | Run with Yama ptrace restrictions enabled |
| **Core dumps** | Crashes may write memory to disk | PassFX does not enable core dumps; ensure `ulimit -c 0` |

#### macOS-Specific

| Limitation | Impact | Mitigation |
| ---------- | ------ | ---------- |
| **No Keychain integration** | Secrets stored in encrypted file, not system keychain | File encryption provides equivalent security |
| **Transparency, Consent, and Control (TCC)** | May require folder access permissions | Grant PassFX access to `~/.passfx` if prompted |

### Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PassFX Security Layers                        │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Encryption at Rest                                     │
│  ├── Fernet (AES-128-CBC + HMAC-SHA256)                         │
│  ├── PBKDF2-HMAC-SHA256 (480,000 iterations)                    │
│  └── 32-byte cryptographic salt                                 │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: File System Protection                                 │
│  ├── Unix: Mode 0600/0700 (owner only)                          │
│  ├── Windows: DACL (current user only)                          │
│  └── Symlink attack prevention                                  │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Runtime Protection                                     │
│  ├── Auto-lock on inactivity                                    │
│  ├── Memory wiping on lock (best-effort)                        │
│  ├── No secrets in logs or error messages                       │
│  └── Clipboard auto-clear                                       │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: Integrity Protection                                   │
│  ├── Salt integrity verification                                │
│  ├── Atomic file writes (crash safety)                          │
│  └── Concurrent access locking                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Recommendations for High-Security Environments

1. **Use encrypted swap** (Linux: `cryptswap`, macOS: FileVault, Windows: BitLocker)
2. **Disable core dumps**: `ulimit -c 0` on Unix systems
3. **Use full-disk encryption** for additional protection at rest
4. **Restrict admin/root access** to the machine running PassFX
5. **Keep the system updated** with security patches
6. **Use a strong master password** (PassFX enforces minimum requirements)

## ⏳ Response Timeline

We are committed to the following response timeline:

- **Acknowledgment:** Within 48 hours.
- **Validation:** Within 5 business days.
- **Patch:** As soon as possible, prioritizing critical severity.
- **Disclosure:** We will coordinate a public disclosure with you once the patch is released.

## 🛡️ Safe Harbor

If you conduct security research within the scope of this policy, we will not pursue legal action against you. In fact, we'll probably thank you in our release notes (and maybe buy you a coffee).

---

<div align="center">
  <sub>Policy maintained by Dinesh. Stay paranoid.</sub>
</div>
