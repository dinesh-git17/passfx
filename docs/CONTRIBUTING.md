# Contributing to PassFX

> "The best time to write a test was before the code. The second best time is now."

Welcome to PassFX, a password manager that takes your secrets seriously (and takes pull requests even more seriously). We are glad you are here. Whether you are fixing a typo, squashing a bug, or adding a feature that will make future users slightly less likely to store their passwords in a spreadsheet, your contribution matters.

This document explains how we work, what we expect, and what you can expect from us. Read it. Internalize it. When CI rejects your PR at 2 AM, you will know why.

---

## Table of Contents

1. [Welcome and Philosophy](#welcome-and-philosophy)
2. [Ways to Contribute](#ways-to-contribute)
3. [Development Setup](#development-setup)
4. [Coding Standards](#coding-standards)
5. [Testing Requirements](#testing-requirements)
6. [Pull Request Guidelines](#pull-request-guidelines)
7. [What Not To Do](#what-not-to-do)
8. [Security Notes for Contributors](#security-notes-for-contributors)
9. [Review Process and CI](#review-process-and-ci)
10. [Final Notes](#final-notes)

---

## Welcome and Philosophy

PassFX is a production-grade, terminal-based password manager. It stores the most sensitive data users have: their credentials, credit cards, recovery codes, and API keys. This is not a hobby project where "it works on my machine" is an acceptable standard. This is software where a single bug could expose someone's entire digital life.

Our priorities, in order:

1. **Security.** Every decision prioritizes protecting user secrets.
2. **Correctness.** The vault must never corrupt, lose, or mishandle data.
3. **Maintainability.** Code that cannot be reviewed cannot be trusted.
4. **Performance.** Fast is nice, but we will trade milliseconds for safety every time.

We welcome contributions from developers who share this mindset. If you approach code with the attitude of "what could go wrong?" rather than "it probably works," you will fit right in.

That said, we are not trying to be intimidating. We want you here. We just also want you to write tests.

---

## Ways to Contribute

There are many ways to help, and not all of them involve writing code.

### Code Contributions

- **Bug fixes.** Something broken? Fix it. Bonus points if you add a regression test.
- **Features.** New credential types, UI improvements, performance enhancements. Check the issues for ideas.
- **Refactoring.** Sometimes the best contribution is making existing code clearer without changing behavior.

### Tests

Our test suite is extensive, but coverage can always improve. If you find an untested code path, especially in security-critical areas, a test contribution is incredibly valuable.

### Documentation

Good documentation saves everyone time. If you found something confusing, chances are someone else will too. Fix the docs, and future you will thank present you.

### Bug Reports

Found a bug? Please report it via [GitHub Issues](https://github.com/dinesh-git17/passfx/issues). Include:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version and operating system

"It doesn't work" is not a bug report. "When I click X on macOS 14.2 with Python 3.11, Y happens instead of Z" is a bug report.

### Security Reports

**Do not file security vulnerabilities as public issues.**

If you find a security flaw, please report it privately. See our [Security Policy](SECURITY.md) for instructions. We take security reports seriously, respond promptly, and will credit you (if you wish) when the fix is released.

---

## Development Setup

A clean development environment prevents the classic "but it works in my terminal" problem that has plagued developers since terminals were invented.

### Quick Install (Users)

If you just want to use PassFX:

```bash
pip install passfx
passfx
```

For development, continue with the steps below.

### Prerequisites

- Python 3.10 or higher
- Git
- A terminal you are comfortable in
- Patience for linters

### Step 1: Clone the Repository

```bash
git clone https://github.com/dinesh-git17/passfx.git
cd passfx
```

### Step 2: Create a Fresh Virtual Environment

This is mandatory. We do not work with global Python environments because that way lies madness and version conflicts.

```bash
# If a .venv already exists, delete it first
rm -rf .venv

# Create a new virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

If you see `(.venv)` in your prompt, you are in. If you do not, something went wrong. Fix it before proceeding.

### Step 3: Install Dependencies

```bash
# Install the project in editable mode with dev dependencies
pip install -e ".[dev]"

# Install additional tooling
pip install black pylint isort pre-commit
```

### Step 4: Install Pre-commit Hooks

This is also mandatory. Pre-commit hooks catch formatting and linting issues before you commit, saving you from the embarrassment of CI rejecting your PR for a trailing whitespace.

```bash
pre-commit install
```

### Step 5: Verify Your Setup

```bash
# Run the test suite
pytest tests/

# Run the app
passfx
```

If tests pass and the app launches, you are ready to contribute. If not, check your Python version, ensure you are in the virtual environment, and try again.

### Working in the Virtual Environment

Every command you run (tests, linters, the app itself) must happen inside the virtual environment. If you open a new terminal, activate the venv again. If the venv becomes corrupted, delete it and recreate it.

We are strict about this because reproducing bugs is hard enough without "which Python is this using?" adding to the confusion.

---

## Coding Standards

We write code as if the person maintaining it is a sleep-deprived version of ourselves in six months. Clarity wins over cleverness every time.

### Style and Formatting

| Tool     | Purpose                         |
| -------- | ------------------------------- |
| Black    | Code formatting (88 char lines) |
| isort    | Import sorting                  |
| Pylint   | Linting (10.0/10 required)      |
| mypy     | Type checking                   |

Do not format code manually. Run the tools.

```bash
black passfx/
isort passfx/
```

If Black reformats your code, commit the reformatted version. Arguing with Black is a path to suffering.

### Type Hints

Every function and method must have type hints. We use mypy with strict settings.

```python
# Good
def derive_key(password: str, salt: bytes) -> bytes:
    ...

# Bad - will fail mypy
def derive_key(password, salt):
    ...
```

If you find yourself wanting to use `Any`, stop and reconsider. `Any` defeats the purpose of type checking. If you genuinely cannot avoid it, document why.

### Naming Things

Naming is famously one of the two hard problems in computer science (the other being cache invalidation and off-by-one errors). Here are our conventions:

| Type      | Convention    | Example                                    |
| --------- | ------------- | ------------------------------------------ |
| Functions | Verbs         | `encrypt_vault`, `derive_key`, `validate`  |
| Variables | Nouns         | `vault_data`, `is_locked`, `credential`    |
| Classes   | PascalCase    | `CryptoManager`, `VaultError`              |
| Constants | UPPER_SNAKE   | `PBKDF2_ITERATIONS`, `SALT_LENGTH`         |
| Private   | Leading `_`   | `_fernet`, `_load_salt`                    |

### Comments

Comments explain why, not what. The code explains what.

```python
# Bad - restates the code
# Encrypt the data
encrypted = fernet.encrypt(data)

# Good - explains non-obvious reasoning
# Use Fernet for authenticated encryption; provides both confidentiality
# and integrity without requiring separate HMAC management
encrypted = fernet.encrypt(data)
```

Do not leave commented-out code in the codebase. That is what version control is for.

### Error Handling

Catch specific exceptions. Let unexpected errors propagate.

```python
# Good
try:
    data = fernet.decrypt(ciphertext)
except InvalidToken as e:
    vault.lock()
    raise DecryptionError("Invalid password or corrupted vault") from e

# Bad - swallows all errors including bugs
try:
    data = fernet.decrypt(ciphertext)
except:
    pass
```

On cryptographic errors, always lock the vault and clear sensitive data before surfacing the error. Fail secure.

### No Print Debugging

Use the `logging` module if you need debug output. Never use `print()` in production code. Our CI will catch it.

More importantly, never log secrets. Not passwords, not keys, not PINs, not anything sensitive. If you find yourself typing `logger.debug(f"Password: {password}")`, step away from the keyboard.

---

## Testing Requirements

Tests are not optional. They are load-bearing walls in our architecture.

### Philosophy

We test for three reasons:

1. **Correctness.** Does the code do what it should?
2. **Security.** Does the code protect secrets properly?
3. **Regression prevention.** Will future changes break existing guarantees?

"It works when I try it" is not a substitute for automated tests. You will not remember to try all the edge cases every time. The test suite will.

### Coverage Requirements

| Module               | Required Coverage |
| -------------------- | ----------------- |
| `core/crypto.py`     | 100%              |
| `core/vault.py`      | 100%              |
| `core/models.py`     | 95%               |
| `utils/generator.py` | 95%               |
| Overall              | 90%               |

Yes, 100% for crypto and vault. Every untested code path in those modules is a potential data loss or security breach. We do not gamble with user credentials.

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=passfx --cov-report=term-missing

# Run specific categories
pytest tests/unit/
pytest tests/security/
pytest -m "security or regression"
```

### Test Organization

| Directory        | What Belongs There                                    |
| ---------------- | ----------------------------------------------------- |
| `unit/`          | Isolated function tests, no I/O                       |
| `integration/`   | Tests that verify components work together            |
| `security/`      | Threat model validation, secret leakage checks        |
| `regression/`    | Locked-in parameter values (iterations, salt length)  |
| `edge/`          | Failure paths: disk full, permissions denied, corrupt |

If you add a feature, add tests. If you fix a bug, add a test that would have caught it. If you are not sure where your test belongs, ask.

### What We Do Not Mock

Never mock cryptographic operations:

- `CryptoManager.derive_key()`
- `CryptoManager.encrypt()` / `decrypt()`
- `secrets.compare_digest()`
- Salt generation

Mocking these defeats the purpose of testing. Security tests must use real cryptographic operations, or they prove nothing.

### Flaky Tests

A test that sometimes passes and sometimes fails is worse than no test at all. It trains developers to ignore failures.

If your test requires `time.sleep()` to work, the test is wrong. Mock the clock instead. If your test fails randomly on CI, fix it before the PR.

We do not tolerate flaky tests. They erode trust in the entire suite.

---

## Pull Request Guidelines

A good PR is focused, well-described, and passes CI before anyone looks at it.

### Before You Start

1. Check if there is an existing issue for the work you want to do.
2. For significant changes, open an issue first to discuss the approach.
3. Pull the latest `main` and branch from there.

### Branch Naming

Branch names should describe the work:

```
feature/clipboard-auto-clear
fix/vault-corruption-on-concurrent-write
docs/update-security-policy
refactor/simplify-key-derivation
security/timing-attack-mitigation
```

Avoid generic names like `fix-stuff` or `updates`. They tell reviewers nothing.

### Commit Messages

We use conventional commits. The format is:

```
type(scope): description

Optional longer explanation of what changed and why.

Fixes #123
```

Types: `feat`, `fix`, `security`, `refactor`, `perf`, `test`, `docs`, `style`

Scopes: `core`, `crypto`, `vault`, `ui`, `cli`, `utils`, `tests`

Good examples:

```
feat(generator): add XKCD-style passphrase generation

security(crypto): increase PBKDF2 iterations to 600k

fix(vault): prevent race condition on concurrent saves
```

Bad examples:

```
fixed stuff
wip
updated code
```

We will ask you to rewrite bad commit messages.

### The PR Template

Fill it out completely. Do not delete sections. The template exists because we have been burned by PRs that were merged without proper consideration.

Key sections:

- **Summary:** What does this PR do?
- **Motivation:** Why is this change needed?
- **Testing:** How did you verify it works?
- **Security Considerations:** For anything touching `core/`

### One Concern Per PR

A PR that fixes a bug, adds a feature, and refactors three unrelated files is hard to review. Split it up.

If your PR description requires "and" more than once, consider whether it should be multiple PRs.

### Keep PRs Reviewable

Giant PRs take longer to review, have higher defect rates, and are more likely to introduce subtle bugs. Aim for PRs that can be reviewed in one sitting.

If you find yourself with a 2000-line PR, you probably should have split it up earlier. Learn from this experience for next time.

---

## What Not To Do

This section exists because every rule here was born from actual incidents or near misses.

### Never Log Secrets

```python
# This is a fireable offense in a professional context
logger.debug(f"Attempting unlock with password: {password}")
print(f"Key derived: {key.hex()}")
```

No exceptions. Not "just for debugging." Not "I'll remove it later." Our security tests actively check for this, and they will fail your PR.

### Never Weaken Cryptographic Parameters

The PBKDF2 iteration count is 480,000. The salt is 32 bytes. These values are not suggestions. They are locked in by regression tests.

If you think you have a good reason to lower them (you do not), open an issue for discussion. Do not just change them.

### Never Use `pickle`

Pickle allows arbitrary code execution during deserialization. An attacker who can write to the vault file could execute code the next time it is loaded.

We use JSON for serialization. Always. Forever.

```python
# Forbidden
import pickle
pickle.dump(credentials, f)

# Required
import json
json.dump(credentials, f)
```

### Never Use the `random` Module for Security

The `random` module is not cryptographically secure. It is for games and simulations, not for generating salts or passwords.

```python
# Forbidden
import random
salt = bytes([random.randint(0, 255) for _ in range(32)])

# Required
import secrets
salt = secrets.token_bytes(32)
```

### Never Skip Tests

"I'll add tests later" is a lie we tell ourselves. Later never comes.

If you submit a PR without tests for new functionality, we will ask you to add them. Save yourself a round trip.

### Never Sneak Unrelated Changes Into PRs

A PR titled "Fix typo in README" should not contain refactored cryptographic code. This is not about being pedantic; it is about reviewability and traceability.

If you find something unrelated that needs fixing while working on a PR, create a separate PR for it.

### Never Commit "Temporary" Hacks

Temporary hacks are permanent. That "quick fix" you added "just to get things working" will still be there in five years, commented with `# TODO: fix this properly`.

Do it right the first time, or do not do it at all.

---

## Security Notes for Contributors

This is a password manager. Everything we do is in service of protecting user secrets. If you are contributing code, especially to `core/`, you need to internalize this.

### The Threat Model

We assume:

- Attackers may gain read access to the vault file
- Attackers may gain read access to log files
- Attackers may observe timing differences in operations
- The user's machine is otherwise trustworthy (no keyloggers, rootkits)

We protect against:

- Brute-force attacks (480k PBKDF2 iterations)
- Chosen-ciphertext attacks (Fernet provides authenticated encryption)
- Information leakage via logs or exceptions
- Timing attacks on password verification

### Areas Requiring Extra Care

Some parts of the codebase require heightened scrutiny:

| Path                          | Why                                    |
| ----------------------------- | -------------------------------------- |
| `core/crypto.py`              | All encryption and key derivation      |
| `core/vault.py`               | Credential persistence and file locking|
| `utils/generator.py`          | Random number generation               |
| `utils/platform_security.py`  | File permission enforcement            |

Changes to these modules require 100% test coverage and explicit security sign-off in the PR checklist.

### Reporting Security Issues

If you discover a security vulnerability while contributing, do not file a public issue. See our [Security Policy](SECURITY.md) for responsible disclosure instructions.

We take security reports seriously. We will respond promptly. We will credit you when the fix is released.

---

## Review Process and CI

Every PR goes through the same process: automated checks first, human review second.

### The CI Pipeline

CI runs automatically on every PR. It checks:

| Check             | What It Does                                   |
| ----------------- | ---------------------------------------------- |
| Black             | Code formatting                                |
| isort             | Import sorting                                 |
| Pylint            | Linting (must score 10.0/10)                   |
| mypy              | Type checking                                  |
| bandit            | Security audit                                 |
| Attribution Guard | No AI/LLM headers in code                      |
| pytest            | Test suite with coverage                       |

If any check fails, the PR cannot be merged. Fix the issues and push again.

### Why CI Is Strict

CI is annoying by design. Every check exists because we have been burned by its absence.

- Formatting checks prevent style arguments in code review.
- Linting catches bugs before they reach production.
- Type checking catches type errors before they become runtime crashes.
- Security audits catch common vulnerability patterns.
- Tests catch regressions before users do.

Do not ask us to make exceptions. Fix the CI failures.

### Human Review

After CI passes, a maintainer will review your PR. Reviews focus on:

- Correctness: Does this code do what it claims?
- Security: Does this code handle secrets properly?
- Maintainability: Will future maintainers understand this code?
- Test coverage: Are the important paths tested?

Review feedback is about the code, not about you. We may request changes. This is normal. Address the feedback, push updates, and we will look again.

### Merge Process

We squash-merge all PRs. Your 17 commits will become one clean commit on `main`. Write a good PR description, and the squashed commit message will be meaningful.

Only maintainers can merge. Once approved and CI is green, we will merge promptly.

---

## Final Notes

Thank you for reading this far. Most people skim.

Contributing to open source can feel intimidating, especially to a project with strict standards. We get it. But those standards exist to protect users and to make the codebase a pleasure to work in.

Here is what we promise:

- **We will respond to your PR.** Maybe not instantly, but we will not leave you hanging.
- **We will explain our feedback.** If we request changes, we will tell you why.
- **We will credit your work.** Contributors make this project possible.

Here is what we ask:

- **Be patient.** Reviews take time. We have day jobs.
- **Be receptive.** Feedback is meant to help, not to criticize.
- **Be thorough.** A little extra effort on your end saves everyone time.

If you have questions, open an issue or start a discussion. We are here to help.

Now go forth and contribute. Your users' secrets are counting on you.

---

*Document maintained by the PassFX team. Last updated December 2025.*
