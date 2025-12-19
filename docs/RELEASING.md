# PassFX PyPI Publishing Guide

This document serves as the release SOP for PassFX. The initial publication is complete.

---

## Release Status

| Item | Status |
|------|--------|
| **PyPI Publication** | Complete |
| **Current Version** | 1.0.1 |
| **Trusted Publishing** | Active (OIDC) |
| **PyPI URL** | https://pypi.org/project/passfx/ |

**Last Verified:** 2025-12-19

---

## Known-Good Install

```bash
pip install passfx
passfx
```

This installs the latest stable release from PyPI and launches the TUI.

---

## Post-Release Verification Checklist

After any release, verify the package works correctly:

### 1. Clean Environment Install

```bash
# Create isolated environment
python3 -m venv /tmp/passfx-verify
source /tmp/passfx-verify/bin/activate

# Install from PyPI (not local)
pip install passfx
```

### 2. CLI Verification

```bash
# Binary exists
ls -la $(which passfx)

# Launches without error (exit with Ctrl+C or Ctrl+Q)
passfx
```

### 3. Import Verification

```python
import passfx
print(passfx.__version__)  # Should match PyPI version

from passfx.core.crypto import CryptoManager
from passfx.core.vault import Vault
from passfx.utils.generator import generate_password
```

### 4. Asset Verification

```python
from pathlib import Path
import passfx

pkg_path = Path(passfx.__file__).parent
tcss_path = pkg_path / "styles" / "passfx.tcss"
assert tcss_path.exists(), "TCSS missing"
assert tcss_path.stat().st_size > 70000, "TCSS truncated"
```

### 5. Dependency Check

```bash
pip check  # Should report "No broken requirements found."
```

### 6. Metadata Verification

Confirm at https://pypi.org/project/passfx/:
- README renders correctly
- License shows MIT
- Project URLs link to GitHub
- Both wheel and sdist available

---

## Future Release Workflow

### Version Bump

Update version in two files (must match):

| File | Format |
|------|--------|
| `pyproject.toml` | `version = "X.Y.Z"` |
| `passfx/__init__.py` | `__version__ = "X.Y.Z"` |

### Release Process

```bash
# 1. Start from main
git checkout main
git pull origin main

# 2. Create release branch
git checkout -b release/vX.Y.Z

# 3. Update versions
# Edit pyproject.toml and passfx/__init__.py

# 4. Update CHANGELOG.md

# 5. Commit
git add pyproject.toml passfx/__init__.py docs/CHANGELOG.md
git commit -m "chore(release): bump version to X.Y.Z"

# 6. Push and create PR
git push -u origin release/vX.Y.Z
# Create PR, get review, merge

# 7. Tag release
git checkout main
git pull origin main
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z

# 8. Create GitHub Release
# Go to: https://github.com/dinesh-git17/passfx/releases
# - Select tag vX.Y.Z
# - Copy release notes from CHANGELOG.md
# - Click "Publish release"
# This triggers automated PyPI publish via trusted publishing
```

### Monitor Deployment

1. Watch workflow: https://github.com/dinesh-git17/passfx/actions
2. Verify on PyPI: https://pypi.org/project/passfx/
3. Run verification checklist above

---

## Completed Setup (Historical)

The following one-time setup steps have been completed:

### PyPI Configuration

- [x] PyPI account created
- [x] 2FA enabled on PyPI
- [x] First release uploaded (claims package name)
- [x] Trusted Publisher configured on PyPI:
  - Owner: `dinesh-git17`
  - Repository: `passfx`
  - Workflow: `publish.yml`
  - Environment: `pypi`

### GitHub Configuration

- [x] GitHub environment `pypi` created
- [x] Publish workflow configured (`.github/workflows/publish.yml`)
- [x] OIDC authentication active (no API tokens stored)

### Package Configuration

- [x] `pyproject.toml` metadata complete
- [x] CLI entry point: `passfx = "passfx.cli:main"`
- [x] Build system: Hatchling
- [x] TCSS stylesheet included in wheel
- [x] Source distribution excludes dev-only directories
- [x] twine check passes

---

## Troubleshooting

### Build Failures

| Issue | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: hatchling` | Missing build deps | `pip install build` |
| Wheel missing TCSS | File not in package dir | Verify `passfx/styles/passfx.tcss` exists |
| `twine check` warnings | Missing readme | Ensure `readme = "README.md"` in pyproject.toml |

### Upload Failures

| Issue | Cause | Fix |
|-------|-------|-----|
| `403 Forbidden` | Wrong credentials | Check Trusted Publisher config |
| `400 File already exists` | Version already uploaded | Bump version number |
| OIDC token rejected | Publisher misconfigured | Verify owner/repo/workflow/environment match |

### Installation Failures

| Issue | Cause | Fix |
|-------|-------|-----|
| `passfx: command not found` | Venv not activated | `source .venv/bin/activate` |
| `ModuleNotFoundError` | Wrong Python | Use `python -m pip install` |
| Missing TCSS at runtime | Broken wheel | Rebuild with `python -m build` |

### Trusted Publishing Failures

| Issue | Cause | Fix |
|-------|-------|-----|
| Environment not found | Missing GitHub env | Create `pypi` environment in repo settings |
| Workflow not triggered | Wrong event type | Must be `published`, not `created` |
| Permission denied | Missing id-token | Add `permissions: id-token: write` |

---

## Local Build (Development Only)

For testing builds before release:

```bash
# Clean build
rm -rf dist/
python -m build

# Verify
twine check dist/*
unzip -l dist/passfx-*.whl | grep tcss  # Should show passfx.tcss

# Test install in separate venv
python3 -m venv /tmp/test-local
source /tmp/test-local/bin/activate
pip install dist/passfx-*.whl
python -c "import passfx; print(passfx.__version__)"
```

---

## Quick Reference

### Commands

```bash
# Build
python -m build

# Check
twine check dist/*

# Install from PyPI
pip install passfx

# Install specific version
pip install passfx==1.0.1

# Upgrade
pip install --upgrade passfx
```

### URLs

| Resource | URL |
|----------|-----|
| PyPI Project | https://pypi.org/project/passfx/ |
| PyPI JSON API | https://pypi.org/pypi/passfx/json |
| GitHub Repo | https://github.com/dinesh-git17/passfx |
| GitHub Actions | https://github.com/dinesh-git17/passfx/actions |
| GitHub Releases | https://github.com/dinesh-git17/passfx/releases |

### Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package metadata, version |
| `passfx/__init__.py` | Runtime version |
| `.github/workflows/publish.yml` | Automated publishing |
| `docs/CHANGELOG.md` | Release notes |

---

*Initial publication: December 2025*
*Current version: 1.0.1*
*Build system: Hatchling*
*Publishing: GitHub Actions + Trusted Publishing (OIDC)*
