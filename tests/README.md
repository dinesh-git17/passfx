# PassFX Test Suite

> Tests exist to keep future us out of trouble.

This document is the canonical reference for the PassFX test suite. It covers test organization, execution, contribution guidelines, and the security-critical invariants that tests protect.

---

## Overview

PassFX is a **password manager**. The test suite exists to guarantee that credentials are encrypted correctly, stored securely, and never leaked through logs, exceptions, or careless refactoring.

### Philosophy

1. **Security first.** Tests that validate cryptographic guarantees and secret handling are non-negotiable. They run on every commit, every PR, and in CI. Always.

2. **Regression-resistant.** Security parameters (PBKDF2 iterations, salt lengths, file permissions) are locked in by tests. Changing them requires breaking tests, which forces conscious review.

3. **Defense in depth.** Unit tests verify isolated behavior. Integration tests verify components work together. Security tests verify the threat model. Edge tests verify graceful failure. This layering catches bugs that any single approach would miss.

4. **No flaky tests.** Tests that sometimes pass and sometimes fail are worse than no tests at all. They erode trust and train developers to ignore failures. Flaky tests are deleted or fixed immediately.

### Test Suite at a Glance

| Metric               | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Lines of test code   | ~23,500                                                            |
| Test directories     | 11                                                                 |
| Pytest markers       | 6 (`unit`, `integration`, `security`, `slow`, `edge`, `regression`) |
| Target coverage      | 90% overall, 100% for `core/crypto.py` and `core/vault.py`         |

---

## Test Directory Structure

```
tests/
├── conftest.py                     # Shared fixtures and pytest hooks
├── unit/                           # Pure function testing, no I/O
│   └── core/
│       ├── test_crypto.py          # CryptoManager, key derivation, encryption
│       ├── test_vault.py           # Vault state machine, CRUD operations
│       └── test_models.py          # Credential dataclasses, serialization
├── integration/                    # Component interaction verification
│   └── test_vault_roundtrip.py     # Full create/unlock/save/lock cycles
├── security/                       # Threat model validation
│   ├── test_security_invariants.py # Secret leakage, crypto strength, permissions
│   └── test_search_security.py     # Search does not expose sensitive data
├── regression/                     # Locked-in security contracts
│   └── test_security_regressions.py
├── edge/                           # Failure paths and hardening scenarios
│   └── test_failure_modes.py       # Disk errors, corruption, race conditions
├── utils/                          # Utility module tests
│   ├── test_password_generator.py  # Random password/passphrase generation
│   ├── test_password_strength.py   # zxcvbn-based strength analysis
│   ├── test_clipboard.py           # Clipboard operations and auto-clear
│   ├── test_io.py                  # File I/O utilities
│   └── test_platform.py            # Platform-specific security helpers
├── cli/                            # CLI entry point and signal handling
│   └── test_cli_entrypoint.py      # Startup, shutdown, signal traps
├── app/                            # Application lifecycle and state
│   ├── test_app_lifecycle.py       # PassFXApp initialization, vault binding
│   ├── test_search_routing.py      # Global search overlay activation and routing
│   └── test_autolock_countdown.py  # Auto-lock timer and countdown warnings
├── screens/                        # Screen logic and workflows
│   └── test_credential_screens.py  # CRUD operations, modal validation
├── ui/                             # UI behavior tests
│   ├── test_login_security.py      # Login screen security behavior
│   └── test_search_state_machine.py # Search overlay state transitions
└── performance/                    # Slow tests excluded from fast CI
    └── test_search_performance.py  # Search timing at scale (1,000+ credentials)
```

### What Belongs Where

| Directory      | Purpose                   | What Goes Here                                                                    | What Does NOT Go Here        |
| -------------- | ------------------------- | --------------------------------------------------------------------------------- | ---------------------------- |
| `unit/core/`   | Core module unit tests    | Tests for `crypto.py`, `vault.py`, `models.py` with no real I/O                   | Integration tests, UI tests  |
| `integration/` | Cross-component workflows | Vault creation → save → lock → unlock → read cycles                               | Single-function unit tests   |
| `security/`    | Threat model validation   | Tests that secrets never leak, crypto params are strong, permissions are enforced | Functional correctness tests |
| `regression/`  | Locked-in invariants      | Parameter values that must never change (iterations, salt length)                 | New feature tests            |
| `edge/`        | Failure path coverage     | Disk full, permission denied, corrupt data, race conditions                       | Happy path tests             |
| `utils/`       | Utility module tests      | Password generation, strength analysis, clipboard, I/O                            | Core crypto tests            |
| `cli/`         | Entry point tests         | Signal handling, startup, shutdown                                                | Application logic tests      |
| `app/`         | Application state tests   | PassFXApp lifecycle, vault initialization, search routing                         | Screen-level tests           |
| `screens/`     | Screen workflow tests     | CRUD operations, modal validation, state transitions                              | Unit tests for models        |
| `ui/`          | UI behavior tests         | Login security, search state machine, focus management                            | Integration tests            |
| `performance/` | Slow performance tests    | Benchmarks, timing validation, memory usage at scale                              | Functional correctness tests |

---

## Test Categories & Intent

### Unit Tests (`unit/`)

Unit tests verify that individual functions and classes behave correctly in isolation.

- **No I/O.** Real file operations are mocked or use temporary directories.
- **Fast.** Each test completes in milliseconds.
- **Deterministic.** Same inputs always produce same outputs.
- **Focused.** One test, one assertion, one failure mode.

Example: Testing that `CryptoManager.derive_key()` produces deterministic output.

### Integration Tests (`integration/`)

Integration tests verify that components work correctly together.

- **Real encryption.** Actual `cryptography` library operations, not mocks.
- **Real file I/O.** Temporary directories with real vault files.
- **Full workflows.** Create vault → add credential → lock → unlock → verify data.

Example: Testing that a credential survives a save/load cycle with correct encryption.

### Security Tests (`security/`)

Security tests validate the threat model. They answer: "If an attacker does X, does the system behave safely?"

- **Secret leakage.** Passwords must never appear in logs, exceptions, or error messages.
- **Crypto strength.** PBKDF2 iterations, salt length, randomness quality.
- **File permissions.** Vault files must be 0600, directories 0700.
- **Memory safety.** Sensitive data cleared after use.
- **Timing attacks.** Constant-time comparison for password verification.

**These tests must never be skipped, weakened, or deleted.**

### Regression Tests (`regression/`)

Regression tests lock in security-critical values as contracts. They exist to catch accidental changes to parameters that would weaken security.

- **Exact value checks.** `PBKDF2_ITERATIONS == 480_000`, not `>= 400_000`.
- **Implementation guards.** No `pickle` imports, `secrets` module required.
- **API stability.** Exception hierarchy, method signatures.

Changing these values requires:

1. Security review and approval
2. Migration plan for existing vaults
3. Explicit acknowledgment by updating the test

### Edge Case Tests (`edge/`)

Edge case tests verify graceful failure under abnormal conditions.

- **Disk failures.** Permission denied, disk full, read-only filesystem.
- **Corrupt data.** Truncated files, invalid JSON, tampered ciphertext.
- **Race conditions.** Concurrent access, signal interrupts.
- **Resource exhaustion.** Memory pressure, file descriptor limits.

These tests often use mocking to simulate failures that are hard to reproduce reliably.

### Performance Tests (`performance/`)

Performance tests validate timing and memory constraints at scale. They are marked `@pytest.mark.slow` and excluded from fast CI runs.

- **Search performance.** <100ms for 1,000+ credentials.
- **Levenshtein efficiency.** Fuzzy matching algorithm performance.
- **Memory usage.** Memory baseline under load.

These tests run weekly via scheduled workflow or on-demand via manual trigger.

---

## Running Tests Locally

### Prerequisites

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies including dev tools
pip install -e ".[dev]"
```

### Running All Tests

```bash
pytest tests/
```

### Running Specific Categories

```bash
# Unit tests only
pytest tests/unit/

# Security tests only
pytest tests/security/ tests/regression/

# Integration tests only
pytest tests/integration/

# Edge case tests only
pytest tests/edge/

# Application and UI tests
pytest tests/app/ tests/ui/ tests/screens/

# Utility tests
pytest tests/utils/ tests/cli/

# By marker
pytest -m security
pytest -m integration
pytest -m "security or regression"
pytest -m "not slow"
```

### Running Performance Tests

Performance tests are excluded by default. Run them explicitly:

```bash
# Run slow performance tests
pytest tests/performance --run-slow -v
```

### Running With Coverage

```bash
# With terminal output
pytest tests/ --cov=passfx --cov-report=term-missing

# With HTML report
pytest tests/ --cov=passfx --cov-report=html
open htmlcov/index.html
```

### Running a Single Test File

```bash
pytest tests/unit/core/test_crypto.py -v
```

### Running a Single Test

```bash
pytest tests/unit/core/test_crypto.py::TestKeyDerivation::test_derive_key_deterministic -v
```

### Expected Runtime

| Scope                       | Approximate Time |
| --------------------------- | ---------------- |
| All tests (excluding slow)  | ~30-60 seconds   |
| Unit tests only             | ~10-15 seconds   |
| Security + regression tests | ~10-15 seconds   |
| All tests (including slow)  | ~2-3 minutes     |

Tests are parallelizable with `pytest-xdist`:

```bash
pytest tests/ -n auto
```

---

## Coverage Expectations

### Global Targets

| Component            | Required Coverage |
| -------------------- | ----------------- |
| `core/crypto.py`     | **100%**          |
| `core/vault.py`      | **100%**          |
| `core/models.py`     | 95%               |
| `utils/generator.py` | 95%               |
| Overall              | **90%**           |

### Why 100% for Core Crypto?

The `crypto.py` and `vault.py` modules handle:

- Master password derivation
- Encryption and decryption
- Salt generation and storage
- Vault file I/O

A single untested code path in these modules could result in:

- Data loss (corrupted vault)
- Security breach (weak encryption)
- Information disclosure (leaked secrets)

100% coverage ensures every branch is exercised. It does not guarantee correctness, but it guarantees no code runs in production that was never tested.

### Coverage Must Never Decrease

When adding new code:

1. Add tests that cover the new code
2. Run `pytest --cov=passfx --cov-report=term-missing`
3. Verify no coverage decrease
4. Add tests for any missing lines before submitting PR

---

## Writing New Tests

### Choosing the Right Category

Ask yourself:

1. **"Does this test a single function in isolation?"** → `unit/`
2. **"Does this test multiple components working together?"** → `integration/`
3. **"Does this test a security guarantee or threat scenario?"** → `security/`
4. **"Does this lock in a value that must never change?"** → `regression/`
5. **"Does this test failure handling or edge cases?"** → `edge/`
6. **"Does this test a utility module?"** → `utils/`
7. **"Does this test CLI behavior?"** → `cli/`
8. **"Does this test application lifecycle?"** → `app/`
9. **"Does this test screen logic?"** → `screens/`
10. **"Does this test UI behavior or state machines?"** → `ui/`
11. **"Does this test performance at scale?"** → `performance/`

### Naming Conventions

```python
# Test files
test_<module_name>.py

# Test classes (optional, for grouping)
class TestKeyDerivation:
class TestVaultCreation:
class TestSecretNeverLogged:

# Test functions
def test_<action>_<expected_outcome>(self):
def test_derive_key_deterministic(self):
def test_wrong_password_raises_decryption_error(self):
def test_password_not_logged_on_vault_create(self):
```

### Using Fixtures

Shared fixtures live in `conftest.py`:

```python
@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Isolated temporary directory with 0o700 permissions."""

@pytest.fixture
def temp_vault_dir(temp_dir: Path) -> Path:
    """Directory structured like ~/.passfx for vault tests."""

@pytest.fixture
def isolated_env(monkeypatch) -> Generator[MonkeyPatch, None, None]:
    """Environment with PASSFX_* and XDG_* variables cleared."""

@pytest.fixture
def mock_home(temp_dir: Path, monkeypatch) -> Generator[Path, None, None]:
    """Override HOME to point to temporary directory."""

@pytest.fixture
def assert_file_permissions() -> Callable[[Path, int], None]:
    """Helper to verify file permissions."""

@pytest.fixture
def assert_dir_permissions() -> Callable[[Path, int], None]:
    """Helper to verify directory permissions."""
```

Use these instead of creating one-off fixtures for common scenarios.

### Marking Tests

Security tests **must** be marked:

```python
@pytest.mark.security
def test_password_not_in_exception_message(self):
    ...
```

The test framework enforces this. Unmarked tests in `security/` will fail.

Available markers (configured in `pyproject.toml`):

```python
@pytest.mark.unit         # Isolated tests with no I/O
@pytest.mark.integration  # Cross-component tests
@pytest.mark.security     # Threat model and invariant validation
@pytest.mark.slow         # Tests taking >1 second
@pytest.mark.edge         # Failure path tests
@pytest.mark.regression   # Bug fix contracts to prevent recurrence
```

### What Is Acceptable to Mock

| Acceptable                         | Not Acceptable            |
| ---------------------------------- | ------------------------- |
| External I/O (clipboard, terminal) | Encryption operations     |
| Time functions (for determinism)   | Password validation logic |
| Platform-specific code             | Salt generation           |
| UI rendering (Textual internals)   | Key derivation            |
| Signal handlers                    | File permission checks    |

**General rule:** Mock at system boundaries, never mock security logic.

### What Must Never Be Mocked

The following must use real implementations in tests:

- `CryptoManager.derive_key()`
- `CryptoManager.encrypt()` / `decrypt()`
- `generate_salt()`
- `validate_master_password()`
- `secrets.compare_digest()`

Mocking these defeats the purpose of testing. If your test needs to mock crypto, reconsider whether it is testing the right thing.

---

## Security & Regression Rules

### Security Tests Protect Invariants

These invariants are enforced by tests and must never be violated:

1. **Passwords never leak.** Not in logs, exceptions, error messages, or stack traces.
2. **Crypto is strong.** PBKDF2 >= 480,000 iterations, salt >= 32 bytes.
3. **Files are protected.** Vault 0600, salt 0600, directory 0700.
4. **Memory is cleared.** Sensitive data wiped after use.
5. **Timing is safe.** Constant-time comparison for secrets.
6. **No dangerous imports.** No `pickle`, no `random` for security.

### Regression Tests Lock In Parameters

Regression tests use exact equality checks:

```python
def test_pbkdf2_iterations_exact_value(self) -> None:
    assert PBKDF2_ITERATIONS == 480_000  # Exact, not >=
```

This is intentional. Security parameters should not drift. Changing them is a conscious decision requiring:

1. Security review
2. Migration plan
3. Updated tests

### Why Some Tests May Appear "Redundant"

You might see multiple tests that seem to check the same thing:

- **Unit test:** `validate_master_password()` returns False for weak passwords
- **Integration test:** Vault creation fails with weak password
- **Security test:** Weak password rejection is constant-time
- **Regression test:** Minimum length is exactly 12 characters

These are not redundant. Each tests a different property:

- Correctness (does it work?)
- Integration (do components agree?)
- Security (is it safe?)
- Stability (is the contract enforced?)

### Deleting or Weakening Tests Is Unacceptable

Tests in `security/` and `regression/` are contracts. Deleting them requires:

1. Explicit approval from a maintainer
2. Written justification in the PR
3. Replacement test if the invariant still applies

"The test was annoying" is not valid justification.

---

## CI Integration

### How Tests Run in CI

The CI pipeline splits tests into logical groups for parallel execution:

| CI Job            | Test Directories                                         | Purpose                                       |
| ----------------- | -------------------------------------------------------- | --------------------------------------------- |
| Core & Security   | `unit/core/`, `integration/`, `security/`, `regression/` | Cryptographic correctness, threat model       |
| UI & Screens      | `ui/`, `app/`, `screens/`                                | Terminal UI behavior, screen workflows        |
| Utilities & CLI   | `utils/`, `cli/`, `edge/`                                | Helper functions, entry points, failure modes |
| Performance       | `performance/`                                           | Slow tests (scheduled, not on every PR)       |

### Failing Tests Block Merges

PRs with failing tests cannot be merged. No exceptions.

### Coverage Is Enforced

Coverage thresholds are configured in `pyproject.toml`:

```toml
[tool.coverage.report]
fail_under = 0  # Phase 0: will increase to 90
```

As the test suite matures, this threshold increases. Decreasing coverage is a CI failure.

### No Skipped Security Tests

Security tests must not be skipped:

```python
# This will fail in CI:
@pytest.mark.skip("Fix later")  # NO
@pytest.mark.security
def test_password_not_logged():
    ...
```

If a security test is broken, fix it. Do not skip it.

---

## Common Mistakes & Anti-Patterns

### Writing Flaky Tests

Flaky tests are tests that sometimes pass and sometimes fail. Common causes:

- **Relying on timing:** `time.sleep(0.1)` is not a synchronization primitive
- **Relying on order:** Tests should not depend on other tests running first
- **Relying on global state:** Use fixtures to isolate state

If you find yourself adding `time.sleep()` to make a test pass, stop and reconsider. The test is probably testing the wrong thing.

> Flaky tests are a lifestyle choice we do not support.

### Relying on Timing

```python
# Bad - this will fail randomly
def test_auto_lock_after_timeout(self):
    vault.unlock()
    time.sleep(0.1)  # Unreliable on CI
    assert vault.is_locked

# Good - mock the clock
def test_auto_lock_after_timeout(self, mock_time):
    vault.unlock()
    mock_time.advance(AUTO_LOCK_SECONDS)
    vault.check_auto_lock()
    assert vault.is_locked
```

### Mocking Security-Sensitive Code

```python
# Bad - defeats the purpose of the test
@patch('passfx.core.crypto.CryptoManager.derive_key')
def test_vault_unlock(self, mock_derive):
    mock_derive.return_value = b'fake_key'  # NO
    ...

# Good - use real crypto
def test_vault_unlock(self, temp_vault_dir):
    vault = Vault(vault_path=..., salt_path=...)
    vault.create("RealPassword123!")
    vault.lock()
    vault.unlock("RealPassword123!")  # Real derivation
    assert not vault.is_locked
```

### Over-Testing Implementation Details

```python
# Bad - tests implementation, not behavior
def test_key_derivation_uses_hmac_sha256(self):
    # This test breaks if we refactor internals
    assert crypto._kdf_algorithm == 'hmac-sha256'

# Good - tests observable behavior
def test_key_derivation_produces_32_bytes(self):
    key = crypto.derive_key("password", salt)
    assert len(key) == 32
```

Test what the code does, not how it does it. Implementation details change; behavior contracts should not.

### Adding Tests in the Wrong Directory

```python
# Wrong - security test in unit/
# tests/unit/core/test_crypto.py
def test_password_never_logged():  # This belongs in security/
    ...

# Right
# tests/security/test_security_invariants.py
@pytest.mark.security
def test_password_never_logged():
    ...
```

If you are testing a security invariant, it belongs in `security/` or `regression/`, not scattered across unit tests.

### Testing Private Methods Directly

```python
# Bad - couples test to implementation
def test_internal_hash_function(self):
    result = vault._compute_internal_hash()
    assert result == expected

# Good - tests through public API
def test_vault_detects_tampering(self):
    vault.unlock(password)
    # Tamper with vault file
    vault_path.write_bytes(corrupted_data)
    with pytest.raises(VaultCorruptedError):
        vault.unlock(password)
```

### Hardcoding Test Passwords That Look Real

```python
# Bad - could trigger security scanners
TEST_PASSWORD = "admin123"  # Too realistic

# Good - obviously test data
TEST_PASSWORD = "TestMasterPassword123!"
```

---

## Final Notes

### Running the Full Quality Suite

Before submitting a PR, run the full quality suite:

```bash
# Format and lint
black passfx/
isort passfx/
ruff check passfx/ --fix

# Type check
mypy passfx/

# Security audit
bandit -r passfx/

# Tests with coverage
pytest tests/ --cov=passfx --cov-report=term-missing
```

### Getting Help

If a test is failing and you do not understand why:

1. Read the test docstring and class docstring
2. Read the code being tested
3. Run the test in isolation with `-v --tb=long`
4. Ask a maintainer

If a test seems wrong:

1. Assume it is right until proven otherwise
2. Understand why it was written before proposing changes
3. Open an issue for discussion before deleting

### Updating This Document

This README should be updated when:

- New test directories are added
- Coverage thresholds change
- CI configuration changes
- New markers are introduced

Keep it accurate. Outdated documentation is worse than no documentation.

---

_Tests are the specification. Code is the implementation. When they disagree, fix the code._
