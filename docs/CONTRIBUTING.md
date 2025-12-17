# Contributing to PassFX

This document outlines the repository governance, branch protection rules, and contribution workflow for PassFX.

---

## Table of Contents

1. [Repository Governance](#repository-governance)
2. [Branch Protection Rules](#branch-protection-rules)
3. [Contribution Workflow](#contribution-workflow)
4. [Commit Standards](#commit-standards)
5. [Code Quality Requirements](#code-quality-requirements)
6. [Pull Request Process](#pull-request-process)
7. [Security Considerations](#security-considerations)

---

## Repository Governance

### Code Ownership

All code in this repository is owned and maintained by a single codeowner. The ownership is defined in `.github/CODEOWNERS`:

```
* @dinesh-git17
```

This means:
- External contributors require review and approval from the codeowner
- The codeowner has final authority on all merge decisions
- The codeowner can merge their own PRs without external review (CI must still pass)

### Protected Branches

The `main` branch is fully protected. Direct commits are not allowed.

---

## Branch Protection Rules

The following protections are enforced on the `main` branch:

### Pull Request Requirements

| Rule | Status |
|------|--------|
| Require pull request before merging | Enforced |
| Required approving reviews | 1 (codeowner) |
| Dismiss stale reviews on new commits | Enforced |
| Require review from Code Owners | Enforced |
| Require approval of most recent push | Enforced |
| Require conversation resolution | Enforced |

### Status Check Requirements

All CI checks must pass before merging:

| Check | Description |
|-------|-------------|
| `Quality Gate (Python 3.10)` | Linting, formatting, compilation on Python 3.10 |
| `Quality Gate (Python 3.11)` | Linting, formatting, compilation on Python 3.11 |

The CI pipeline validates:
- Black formatting compliance
- isort import sorting
- Pylint score (must be 10.0/10)
- Python syntax compilation
- Attribution guard (no AI/LLM references)
- Pre-commit hook parity

### Branch Synchronization

| Rule | Status |
|------|--------|
| Require branch to be up to date | Enforced |

Your branch must be rebased or merged with the latest `main` before merging.

### History Requirements

| Rule | Status |
|------|--------|
| Require linear history | Enforced |

All merges use squash or rebase to maintain a clean, linear commit history.

### Administrative Protections

| Rule | Status |
|------|--------|
| Enforce rules on administrators | Disabled (codeowner can bypass reviews) |
| Allow force pushes | Disabled |
| Allow deletions | Disabled |

The codeowner can bypass review requirements but force pushes and deletions remain blocked for everyone.

### Allowed Merge Methods

| Method | Status |
|--------|--------|
| Merge commits | Disabled |
| Squash merging | Enabled (default) |
| Rebase merging | Enabled |

All PRs are squashed by default to maintain a clean linear history.

---

## Contribution Workflow

### Step 1: Clone the Repository

```bash
git clone https://github.com/dinesh-git17/passfx.git
cd passfx
```

### Step 2: Set Up Development Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
pip install -r requirements-dev.txt
pre-commit install
```

### Step 3: Create a Feature Branch

Always create a new branch from the latest `main`:

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `security/` - Security-related changes
- `refactor/` - Code refactoring
- `docs/` - Documentation updates
- `test/` - Test additions or fixes

### Step 4: Make Changes

1. Write your code following the [Code Quality Requirements](#code-quality-requirements)
2. Run quality checks locally before committing:

```bash
black passfx/
isort passfx/
ruff check passfx/ --fix
pylint passfx/ --rcfile=.pylintrc --fail-under=10.0
```

### Step 5: Commit Changes

Follow the [Commit Standards](#commit-standards) when writing commit messages.

```bash
git add .
git commit -m "feat(scope): description"
```

### Step 6: Push and Create Pull Request

```bash
git push -u origin feature/your-feature-name
```

Then create a Pull Request on GitHub targeting `main`.

### Step 7: Address Review Feedback

- Respond to all review comments
- Push additional commits to address feedback
- Re-request review when ready

### Step 8: Merge

Once approved and all checks pass, the codeowner will merge via squash merge.

---

## Commit Standards

### Conventional Commit Format

All commits must follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `security` | Security-related change |
| `refactor` | Code refactoring (no functional change) |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `docs` | Documentation changes |
| `style` | Code style/formatting (no logic change) |
| `chore` | Maintenance tasks |
| `ci` | CI/CD configuration changes |

### Scopes

| Scope | Description |
|-------|-------------|
| `core` | Core business logic |
| `crypto` | Cryptographic operations |
| `vault` | Vault storage operations |
| `ui` | User interface components |
| `screens` | Screen-specific changes |
| `cli` | CLI entry point |
| `utils` | Utility functions |
| `tests` | Test files |
| `deps` | Dependency updates |

### Examples

```
feat(screens): add search functionality to passwords screen

- Implement case-insensitive search
- Add keyboard shortcut (/) for quick search
- Display result count in footer

Fixes #42
```

```
fix(crypto): prevent timing attack in password verification

Use secrets.compare_digest() for constant-time comparison
to prevent timing-based side-channel attacks.
```

```
security(vault): enforce stricter file permissions

- Set vault.enc to 0o600
- Set salt file to 0o600
- Validate permissions on vault load
```

### Commit Rules

1. Use imperative mood ("add feature" not "added feature")
2. Keep subject line under 72 characters
3. Capitalize the first letter after the colon
4. Do not end subject line with a period
5. Separate subject from body with a blank line
6. Reference issues in the footer with `Fixes #123` or `Closes #123`

### Forbidden in Commits

- References to AI assistants or language models
- Debugging code or print statements
- Commented-out code
- Unfinished work without clear TODO markers

---

## Code Quality Requirements

### Automated Checks

All code must pass these checks:

| Tool | Purpose | Command |
|------|---------|---------|
| Black | Code formatting | `black --check passfx/` |
| isort | Import sorting | `isort --check-only passfx/` |
| Ruff | Fast linting | `ruff check passfx/` |
| Pylint | Comprehensive linting | `pylint passfx/ --fail-under=10.0` |
| Bandit | Security audit | `bandit -r passfx/` |

### Pre-commit Hooks

Pre-commit hooks run automatically on each commit:

```bash
pre-commit install  # One-time setup
pre-commit run --all-files  # Manual run
```

### Type Hints

All functions and methods must include type hints:

```python
# Required
def derive_key(password: str, salt: bytes) -> bytes:
    ...

# Not acceptable
def derive_key(password, salt):
    ...
```

### Documentation

- Public APIs require docstrings explaining purpose and security implications
- Complex logic requires inline comments explaining "why" not "what"
- No redundant comments that restate the code

---

## Pull Request Process

### PR Title Format

Follow the same format as commits:

```
type(scope): description
```

### PR Description Template

```markdown
## Summary

Brief description of what this PR does.

## Changes

- Change 1
- Change 2
- Change 3

## Testing

How was this tested?

## Security Considerations

Any security implications of these changes?

## Related Issues

Fixes #123
```

### Review Criteria

PRs are evaluated on:

1. **Security** - No new vulnerabilities, proper handling of sensitive data
2. **Code Quality** - Follows style guide, type hints, clean code
3. **Testing** - Adequate test coverage for changes
4. **Documentation** - Updated docs if needed
5. **Performance** - No unnecessary performance regressions

### Merge Requirements

Before a PR can be merged:

- [ ] All CI checks pass
- [ ] At least 1 approval from codeowner
- [ ] All conversations resolved
- [ ] Branch is up to date with `main`

---

## Security Considerations

### Sensitive Data Handling

When working with code that handles credentials:

1. Never log passwords, keys, PINs, or CVVs
2. Use `secrets` module for random generation, never `random`
3. Clear sensitive data from memory after use
4. Use constant-time comparison for password verification

### File Permissions

Maintain strict file permissions:

| Resource | Permission |
|----------|------------|
| `~/.passfx/` directory | 0o700 |
| `vault.enc` | 0o600 |
| `salt` | 0o600 |

### Cryptographic Standards

Do not modify cryptographic parameters without security review:

| Parameter | Current Value | Standard |
|-----------|---------------|----------|
| PBKDF2 iterations | 480,000 | OWASP 2023 |
| Salt length | 32 bytes | 256-bit |
| Encryption | AES-256-CBC | Fernet |

---

## Questions or Issues

For questions about contributing, open an issue on the repository or contact the codeowner directly.
