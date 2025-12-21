# PassFX CI Workflows

This document describes the continuous integration system that guards the PassFX codebase.

---

## Overview

PassFX uses GitHub Actions to enforce code quality, run tests, and validate security invariants on every commit. The CI system is designed with three priorities:

1. **Security gates cannot be bypassed.** Tests that validate cryptographic behavior and secret handling must pass before merge.

2. **Fast feedback.** The pipeline is split into parallel jobs so contributors see failures quickly. Most PRs complete in under 3 minutes.

3. **No surprises.** What runs in CI matches what runs locally. If it passes on your machine with `pytest tests/`, it passes in CI.

### Workflow Files

| File                     | Trigger              | Purpose                                           |
| ------------------------ | -------------------- | ------------------------------------------------- |
| `code-quality.yml`       | Push to main, PRs    | Primary quality gate: linting, tests, coverage    |
| `performance-tests.yml`  | Weekly, manual       | Slow performance benchmarks (excluded from PRs)   |
| `dependency-review.yml`  | PRs                  | Block PRs with vulnerable dependencies            |
| `labeler.yml`            | PRs                  | Auto-label PRs based on changed files             |
| `pr-title-labeler.yml`   | PRs                  | Auto-label PRs based on conventional commit title |
| `publish.yml`            | Releases             | Publish to PyPI on release                        |

---

## Code Quality Workflow

**File:** `code-quality.yml`

This is the primary CI workflow. It runs on every push to `main` and every pull request targeting `main`. A PR cannot be merged unless all jobs pass.

### Job Structure

The workflow is split into five jobs that run in parallel after the initial quality check:

```
[code-quality]
      │
      ├──> [core-security-tests]  ─┐
      ├──> [ui-tests]             ─┼──> [ci-summary]
      ├──> [utils-cli-tests]      ─┤
      └──> [performance-status]   ─┘
```

### Job Breakdown

#### 1. Code Quality

**Runs:** Once on Python 3.11

Validates formatting, linting, and attribution before tests run:

| Check                | Tool         | Purpose                                          |
| -------------------- | ------------ | ------------------------------------------------ |
| Formatting           | black        | Consistent code style                            |
| Import sorting       | isort        | Consistent import order                          |
| Linting              | pylint       | Code quality and common errors                   |
| Compilation check    | py_compile   | Syntax validation                                |
| Attribution guard    | Custom       | Blocks commits mentioning AI assistants          |
| Pre-commit parity    | pre-commit   | Ensures CI matches local pre-commit hooks        |

If any check fails, downstream test jobs do not run.

#### 2. Core & Security Tests

**Runs:** On Python 3.10 and 3.11 (matrix)

Executes the security-critical test suite:

| Directory        | What It Tests                                              |
| ---------------- | ---------------------------------------------------------- |
| `tests/unit/core/` | Crypto, vault, models in isolation                       |
| `tests/integration/` | Vault round-trips with real encryption                 |
| `tests/security/` | Threat model validation (secret leakage, permissions)    |
| `tests/regression/` | Locked-in security parameters (PBKDF2, salt length)    |

This job validates that PassFX encrypts credentials correctly and never leaks secrets.

#### 3. UI & Screens Tests

**Runs:** On Python 3.10 and 3.11 (matrix)

Validates the terminal interface:

| Directory         | What It Tests                                             |
| ----------------- | --------------------------------------------------------- |
| `tests/ui/`       | Login security, search state machine                      |
| `tests/app/`      | Application lifecycle, vault initialization               |
| `tests/screens/`  | Screen workflows, CRUD operations                         |

This job validates that the Textual TUI behaves correctly.

#### 4. Utilities & CLI Tests

**Runs:** On Python 3.10 and 3.11 (matrix)

Validates helper functions and failure handling:

| Directory       | What It Tests                                               |
| --------------- | ----------------------------------------------------------- |
| `tests/utils/`  | Password generation, strength analysis, clipboard, I/O      |
| `tests/cli/`    | CLI entry point, signal handling                            |
| `tests/edge/`   | Failure modes (disk errors, corruption, race conditions)    |

This job validates that utilities work correctly and failures are handled gracefully.

#### 5. Performance Status

**Runs:** Once on Python 3.11

This job does not run tests. It reports that performance tests are intentionally skipped from the fast CI pipeline and provides instructions for running them locally or via the scheduled workflow.

#### 6. CI Summary

**Runs:** After all other jobs complete

Aggregates results from all jobs and:

- Generates a summary in the GitHub Actions UI
- Posts a comment on the PR with pass/fail status for each job
- Determines mergeability (all required jobs must pass)
- Sends Slack notification (if configured)

### Mergeability Rules

A PR is mergeable when:

| Job               | Required |
| ----------------- | -------- |
| Code Quality      | Yes      |
| Core & Security   | Yes      |
| UI & Screens      | Yes      |
| Utilities & CLI   | Yes      |
| Performance Status | No (informational) |

If any required job fails, the PR cannot be merged.

---

## Performance Tests Workflow

**File:** `performance-tests.yml`

Runs slow performance benchmarks that are excluded from the fast CI pipeline.

### Triggers

- **Scheduled:** Weekly on Sunday at 2 AM UTC
- **Manual:** Via GitHub Actions UI or `gh workflow run performance-tests.yml`

### What It Tests

| Test                     | Target       |
| ------------------------ | ------------ |
| Search at 1,000+ scale   | < 100ms      |
| Fuzzy matching           | < 50ms       |
| Memory baseline          | < 50MB       |

These tests validate that search performance meets requirements at scale.

### Why Excluded from PR CI

Performance tests are slow (>1 second each) and do not affect correctness. Running them on every PR would slow feedback without catching bugs that regular tests miss.

To run locally:

```bash
pytest tests/performance --run-slow -v
```

---

## Dependency Review Workflow

**File:** `dependency-review.yml`

Blocks PRs that introduce dependencies with known security vulnerabilities.

### How It Works

- Runs on every PR targeting `main`
- Uses GitHub's dependency graph and advisory database
- Fails on HIGH or CRITICAL severity vulnerabilities
- Posts a comment on the PR with vulnerability details

### License Allowlist

Only dependencies with these licenses are allowed:

- MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause
- ISC, Python-2.0, PSF-2.0, 0BSD
- Unlicense, WTFPL, CC0-1.0

The `cryptography` package is explicitly allowed despite SPDX parsing issues.

---

## PR Labeler Workflow

**File:** `labeler.yml`

Automatically applies labels to PRs based on changed files.

### Label Mappings

Configured in `.github/labeler.yml`. Labels are applied when files in specific directories change.

---

## PR Title Labeler Workflow

**File:** `pr-title-labeler.yml`

Automatically applies labels based on PR title prefixes (conventional commits).

### Prefix Mappings

| Prefix                    | Label         |
| ------------------------- | ------------- |
| `feat:`, `feature:`       | feature       |
| `fix:`, `bugfix:`, `hotfix:` | bug        |
| `docs:`, `doc:`           | docs          |
| `ci:`, `build:`, `infra:` | infra         |
| `security:`, `sec:`       | security      |
| `test:`, `tests:`         | tests         |
| `refactor:`, `cleanup:`   | refactor      |
| `perf:`, `performance:`   | performance   |
| `chore:`                  | chore         |
| `deps:`, `dep:`           | dependencies  |

---

## Publish Workflow

**File:** `publish.yml`

Publishes PassFX to PyPI when a GitHub Release is published.

### How It Works

1. Builds the package with `python -m build`
2. Uploads artifacts
3. Publishes to PyPI using trusted publishing (OIDC)

### Trigger

- **On release:** When a GitHub Release is published

This workflow uses PyPI's trusted publishing feature. No API token is stored in secrets.

---

## Failure Interpretation Guide

When CI fails, use this guide to understand what went wrong:

### Code Quality Job Failed

| Failure                | What It Means                                    | How to Fix                          |
| ---------------------- | ------------------------------------------------ | ----------------------------------- |
| black --check failed   | Code formatting does not match standard          | Run `black passfx/`                 |
| isort --check failed   | Import order incorrect                           | Run `isort passfx/`                 |
| pylint failed          | Linting errors or score below threshold          | Run `pylint passfx/` and fix issues |
| Attribution guard      | Commit mentions AI/Claude/assistant              | Remove attribution references       |
| Pre-commit failed      | Pre-commit hooks not passing                     | Run `pre-commit run --all-files`    |

### Core & Security Tests Failed

| Failure                     | What It Means                                  |
| --------------------------- | ---------------------------------------------- |
| test_crypto.py              | Cryptographic operation broken                 |
| test_vault.py               | Vault state machine broken                     |
| test_security_invariants.py | Secret leakage or weak crypto detected         |
| test_security_regressions.py | Security parameter changed unexpectedly       |
| test_vault_roundtrip.py     | Encryption/decryption cycle broken             |

Security test failures are serious. Do not bypass or skip these tests.

### UI & Screens Tests Failed

| Failure                     | What It Means                                  |
| --------------------------- | ---------------------------------------------- |
| test_login_security.py      | Login screen security behavior broken          |
| test_app_lifecycle.py       | Application startup/shutdown broken            |
| test_credential_screens.py  | CRUD operations broken                         |
| test_search_state_machine.py | Search overlay state transitions broken       |

### Utilities & CLI Tests Failed

| Failure                     | What It Means                                  |
| --------------------------- | ---------------------------------------------- |
| test_password_generator.py  | Password generation broken                     |
| test_clipboard.py           | Clipboard operations broken                    |
| test_failure_modes.py       | Error handling broken                          |
| test_cli_entrypoint.py      | CLI startup/shutdown broken                    |

---

## Local vs CI Parity

The CI pipeline is designed to match local development. What passes locally should pass in CI.

### Ensuring Parity

Before pushing, run the same checks CI runs:

```bash
# Quality checks (matches code-quality job)
black --check passfx/
isort --check-only passfx/
pylint passfx/ --fail-under=10.0
pre-commit run --all-files

# Tests (matches test jobs)
pytest tests/unit/core tests/integration tests/security tests/regression
pytest tests/ui tests/app tests/screens
pytest tests/utils tests/cli tests/edge
```

Or run everything at once:

```bash
pytest tests/ --cov=passfx --cov-report=term-missing
```

### Common Causes of CI-Only Failures

| Cause                        | Solution                                       |
| ---------------------------- | ---------------------------------------------- |
| Unstaged changes             | Commit all changes before pushing              |
| Different Python version     | CI runs 3.10 and 3.11; test on both            |
| Missing dev dependencies     | Run `pip install -e ".[dev]"`                  |
| Platform differences         | Some tests mock platform-specific behavior     |
| Pre-commit not installed     | Run `pre-commit install`                       |

---

## Concurrency and Cancellation

The CI pipeline uses GitHub Actions concurrency to cancel in-progress runs when a new commit is pushed to the same branch.

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true
```

This prevents wasted compute when you push multiple commits in quick succession.

---

## Coverage Reporting

Each test job uploads coverage data to Codecov. Coverage is tracked separately for:

- `core-security`: Core crypto and vault modules
- `ui-screens`: Textual UI and screen behavior
- `utils-cli`: Utility functions and CLI

The coverage badge on the README reflects overall coverage from the combined reports.

### Coverage Thresholds

Currently, coverage enforcement is at 0% (Phase 0). This will increase to 90% as the test suite matures.

| Component          | Target  |
| ------------------ | ------- |
| `core/crypto.py`   | 100%    |
| `core/vault.py`    | 100%    |
| `core/models.py`   | 95%     |
| `utils/generator.py` | 95%   |
| Overall            | 90%     |

---

## Notifications

### PR Comments

The ci-summary job posts a comment on every PR with:

- Pass/fail status for each job
- Mergeability verdict
- Link to the workflow run

If you push additional commits, the comment is updated rather than creating a new one.

### Slack (Optional)

If `SLACK_WEBHOOK_URL` is configured in repository secrets, CI results are posted to Slack. This is optional and does not affect CI success/failure.

---

## Adding New Workflows

If you need to add a new workflow:

1. Create the workflow file in `.github/workflows/`
2. Document it in this README
3. Ensure it does not bypass security gates
4. Test locally with `act` if possible

New workflows should not:

- Skip security tests
- Allow merging with failures
- Bypass the code quality job
- Add unnecessary dependencies

---

## Updating This Document

Update this README when:

- Workflows are added, removed, or renamed
- Job structure changes
- Triggers change
- New failure scenarios are identified

Keep it accurate. Contributors rely on this document to understand CI failures.

---

_CI exists to catch problems before they reach users. If it is annoying, that is the point._
