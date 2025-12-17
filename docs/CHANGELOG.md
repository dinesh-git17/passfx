# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Encryption support for export formats (Planned).
- YubiKey / Hardware Token integration (Planned).

---

## [1.0.0] - 12/17/2025

**"The Beta Release"**

This is the initial public release of PassFX. It includes the core architecture, full TUI implementation, and security primitives.

### Added

- **Core Security:**
  - AES-256-CBC encryption via `cryptography.fernet`.
  - PBKDF2-HMAC-SHA256 key derivation with 480,000 iterations.
  - Zero-knowledge architecture with separate salt storage.
- **Terminal UI (TUI):**
  - Full `Textual` based interface with mouse support.
  - Screens: Login, Dashboard, Passwords, Phones, Cards, Notes, Generator, Settings.
  - Modal dialogs for Creating/Editing entries.
- **Storage Types:**
  - `EmailCredential`: Standard username/password storage.
  - `PhoneCredential`: Phone numbers and PINs.
  - `CreditCard`: Full payment details (PAN, CVV, Expiry).
  - `EnvEntry`: Environment variables and API keys.
  - `RecoveryEntry`: 2FA backup codes.
  - `NoteEntry`: Encrypted free-text markdown notes.
- **Utilities:**
  - **Password Generator**: Configurable generator (length, special chars, passphrase mode).
  - **Strength Meter**: Integrated `zxcvbn` for realistic strength estimation.
  - **Clipboard Manager**: Auto-clearing clipboard (30s timeout).
  - **Import/Export**: Support for CSV and JSON (plaintext) backups.
- **DevOps:**
  - Pre-commit hooks for Black, Isort, Pylint.
  - `attribution_guard.py` to prevent AI-generated code leaks.
  - GitHub Actions CI pipeline with strict quality gates.

### Security

- Implemented constant-time comparison for master password verification.
- Enforced `0o700`/`0o600` permissions on vault directories and files.
- Added best-effort memory wiping for sensitive key material.

[Unreleased]: https://github.com/dinesh-git17/passfx/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/dinesh-git17/passfx/releases/tag/v1.0.0
