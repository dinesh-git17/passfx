# PassFX Installation Tests

Docker-based test harness for validating PassFX installation across pip, pipx, and Homebrew.

## Purpose

This test suite ensures PassFX installs correctly in clean, reproducible environments. It catches packaging issues before they reach users.

**Validated guarantees:**

- CLI binary discoverable on PATH
- `--help` and `--version` work correctly
- No unexpected stderr output
- Python modules import cleanly
- No premature filesystem access

## Quick Start

### Local Execution

```bash
# Run all tests (requires Docker)
./tests/install/run_install_tests.sh

# Run specific tests
./tests/install/run_install_tests.sh pip
./tests/install/run_install_tests.sh pipx
./tests/install/run_install_tests.sh brew

# Run with specific Python version
./tests/install/run_install_tests.sh --python 3.12 pip pipx

# Test specific PassFX version
./tests/install/run_install_tests.sh --version 1.0.1 pip
```

### Manual Docker Commands

```bash
cd tests/install

# pip test
docker build -f Dockerfile.pip -t passfx-test-pip .
docker run --rm passfx-test-pip

# pipx test
docker build -f Dockerfile.pipx -t passfx-test-pipx .
docker run --rm passfx-test-pipx

# Homebrew test (requires tap to be published)
docker build -f Dockerfile.brew -t passfx-test-brew .
docker run --rm passfx-test-brew
```

## Test Matrix

| Method | Base Image | Python Version | Notes |
|--------|------------|----------------|-------|
| pip | python:X.XX-slim | 3.10, 3.11, 3.12 | Standard installation |
| pipx | python:X.XX-slim | 3.11 | Isolated environment |
| brew | homebrew/brew | 3.12 | Linuxbrew validation |

## CI Integration

Tests run automatically via `.github/workflows/install-tests.yml`:

- **After PyPI publish**: Triggered by `workflow_run` when "Publish to PyPI" completes successfully
- **Manual trigger**: Configurable via workflow_dispatch (for pre-release verification)

This ensures the package is available on PyPI before installation tests run (no race condition).

### GitHub Actions Snippet

```yaml
- name: Run pip installation tests
  run: |
    cd tests/install
    docker build -f Dockerfile.pip -t passfx-test-pip .
    docker run --rm passfx-test-pip
```

## Validation Checks

Each installation path validates:

1. Binary on PATH (`command -v passfx`)
2. Version output matches (`passfx --version`)
3. Help content (`passfx --help` contains expected strings)
4. Exit codes are 0
5. No unexpected stderr
6. Python module imports work
7. Core modules exist
8. Invalid arguments don't produce tracebacks
9. No premature filesystem access

## Files

```
tests/install/
├── Dockerfile.pip       # pip installation test
├── Dockerfile.pipx      # pipx installation test
├── Dockerfile.brew      # Homebrew installation test
├── validate_install.sh  # Validation script (runs inside container)
├── run_install_tests.sh # Test runner (runs on host)
└── README.md            # This file
```

## Known Limitations

1. **Homebrew macOS**: Docker tests use Linuxbrew. True macOS validation runs only on release via GitHub Actions macos-latest runner.

2. **TUI Launch**: We don't test launching the TUI in Docker (no terminal). We validate CLI args (`--help`, `--version`) which don't require a terminal.

3. **Clipboard**: `pyperclip` may warn about missing clipboard backends in headless environments. This doesn't affect CLI argument processing.

4. **Homebrew Tap**: The brew test assumes the tap is published at `dinesh-git17/passfx`. If testing before tap publication, the test will fail.

## Troubleshooting

### Docker not found

```
Docker is not installed
```

Install Docker: https://docs.docker.com/get-docker/

### Docker daemon not running

```
Docker daemon is not running
```

Start Docker Desktop or the Docker service.

### Homebrew test fails

```
Error: No available formula with the name "passfx"
```

The Homebrew tap may not be published yet. This is expected before the first release.

### Version mismatch

```
Unexpected version output: passfx 1.0.1
Expected: passfx 1.0.2
```

Update `EXPECTED_VERSION` in `validate_install.sh` or use `--version` flag:

```bash
./run_install_tests.sh --version 1.0.1 pip
```

## Adding Tests

To add new validation checks, edit `validate_install.sh`:

```bash
# Test N: Description
run_test "Description" '
    # Your test logic here
    # Return 0 for pass, 1 for fail
'
```
