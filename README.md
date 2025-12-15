# PassFX

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A secure, terminal-based password manager with AES-256 encryption and a cyberpunk-themed interface.

```
    ____                 _______  __
   / __ \____ ___________/ ____/ |/ /
  / /_/ / __ `/ ___/ ___/ /_   |   /
 / ____/ /_/ (__  |__  ) __/  /   |
/_/    \__,_/____/____/_/    /_/|_|

    [ Secure Password Management ]
```

## Features

- **AES-256 Encryption** — Military-grade encryption for all stored credentials
- **PBKDF2 Key Derivation** — 480,000 iterations for maximum security against brute-force attacks
- **Zero-Knowledge Architecture** — Your master password never leaves your device
- **Multiple Credential Types** — Store passwords, phone PINs, and credit card details
- **Secure Password Generator** — Cryptographically secure random generation
- **Password Strength Analysis** — Real-time strength feedback using zxcvbn
- **Auto-Lock** — Configurable automatic vault locking on inactivity
- **Clipboard Integration** — One-key copy with automatic clipboard clearing
- **Cross-Platform** — Works on macOS, Linux, and Windows

## Installation

### From PyPI (Recommended)

```bash
pip install passfx
```

### From Source

```bash
git clone https://github.com/dinesh-git17/passfx.git
cd passfx
pip install -e .
```

## Quick Start

```bash
# Launch PassFX
passfx

# Or run as a module
python -m passfx
```

On first launch, you'll be prompted to create a master password. This password encrypts your vault — **there is no recovery option by design**.

## Usage

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `↑` `↓` | Navigate menu |
| `Enter` | Select |
| `a` | Add new credential |
| `e` | Edit selected |
| `d` | Delete selected |
| `c` | Copy password to clipboard |
| `g` | Open password generator |
| `Escape` | Go back |
| `Ctrl+Q` | Quit |

### Credential Types

- **Passwords** — Email/username and password combinations for websites and services
- **Phone PINs** — Secure storage for phone unlock codes and PINs
- **Credit Cards** — Card numbers, expiration dates, and CVVs

## Security

PassFX is built with security as the top priority:

| Feature | Implementation |
|---------|----------------|
| Encryption | AES-256-CBC with HMAC-SHA256 (Fernet) |
| Key Derivation | PBKDF2-HMAC-SHA256, 480,000 iterations |
| Salt | 32-byte cryptographically random per vault |
| File Permissions | Vault files restricted to owner (0600) |
| Memory | Sensitive data cleared after use |
| Clipboard | Auto-cleared after 30 seconds |

### Security Design Principles

- **No Cloud Sync** — Your data stays on your device
- **No Recovery** — Master password cannot be reset or recovered
- **No Telemetry** — Zero data collection or phone-home functionality
- **Auditable** — Open source and dependency-minimal

## Configuration

PassFX stores its data in `~/.passfx/`:

```
~/.passfx/
├── vault.enc      # Encrypted credential vault
├── salt           # Cryptographic salt
├── config.json    # User preferences
└── logs/          # Audit logs (no sensitive data)
```

### Settings

Access settings from the main menu to configure:

- Auto-lock timeout (default: 5 minutes)
- Clipboard clear delay (default: 30 seconds)
- Password generator defaults

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/dinesh-git17/passfx.git
cd passfx

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Code Quality

```bash
# Format code
black passfx/

# Lint
ruff check passfx/ --fix

# Type checking
mypy passfx/

# Run tests
pytest tests/ --cov=passfx

# Security audit
bandit -r passfx/
pip-audit
```

### Project Structure

```
passfx/
├── core/           # Encryption, vault, and data models
├── screens/        # Textual TUI screens
├── utils/          # Password generation, clipboard, validators
├── styles/         # Textual CSS theming
└── ui/             # Reusable UI components
```

## Requirements

- Python 3.11 or higher
- Dependencies:
  - `textual` — Terminal UI framework
  - `cryptography` — Encryption primitives
  - `pyperclip` — Cross-platform clipboard
  - `zxcvbn` — Password strength estimation

## Contributing

Contributions are welcome! Please read the following before submitting:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Ensure tests pass and coverage remains above 90%
4. Run `black`, `ruff`, and `mypy` before committing
5. Submit a pull request

For security vulnerabilities, please email directly rather than opening a public issue.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Textual](https://github.com/Textualize/textual) — Modern TUI framework
- [cryptography](https://github.com/pyca/cryptography) — Cryptographic recipes
- [zxcvbn](https://github.com/dropbox/zxcvbn) — Password strength estimation

---

<p align="center">
  <sub>Built with security in mind.</sub>
</p>
