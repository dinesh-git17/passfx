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

- **Cryptographic Weaknesses:** Flaws in our implementation of Fernet (AES-256-CBC) or PBKDF2.
- **Data Leaks:** Credentials appearing in logs, unencrypted swap, or persisting in memory after a "lock" event.
- **Side-Channel Attacks:** Timing attacks on password verification or key derivation.
- **Injection:** TUI rendering bugs that allow arbitrary code execution via malicious payloads.

### Out of Scope (Please do not report these)

- **Compromised Host:** If the user's machine has malware/keyloggers/rootkits, PassFX cannot protect them. We assume the host OS is trusted.
- **Physical Access:** If an attacker has the unlocked device and a $5 wrench, cryptography is irrelevant.
- **Weak Master Passwords:** We enforce complexity rules, but we cannot stop a user from using "Password123!" if they really try.
- **Social Engineering:** Phishing attacks against the user.

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
