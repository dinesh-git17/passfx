#!/usr/bin/env bash
# validate_install.sh - Validates PassFX installation inside Docker container
#
# This script runs a comprehensive validation suite to ensure PassFX
# is correctly installed and functional. It is designed to fail hard
# on any error to ensure release quality.
#
# Usage: validate_install.sh [pip|pipx|brew]

set -euo pipefail

# Configuration
INSTALL_METHOD="${1:-unknown}"
EXPECTED_VERSION="1.0.3"
EXIT_CODE=0
TESTS_RUN=0
TESTS_PASSED=0

# Color output (if terminal supports it)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_test() {
    echo -e "\n${YELLOW}[TEST]${NC} $1"
}

# Test execution wrapper
run_test() {
    local test_name="$1"
    local test_cmd="$2"

    TESTS_RUN=$((TESTS_RUN + 1))
    log_test "$test_name"

    if eval "$test_cmd"; then
        log_info "PASSED: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_error "FAILED: $test_name"
        EXIT_CODE=1
        return 1
    fi
}

# Print header
echo "============================================================"
echo "PassFX Installation Validation"
echo "============================================================"
echo "Install Method: $INSTALL_METHOD"
echo "Expected Version: $EXPECTED_VERSION"
echo "Timestamp: $(date -Iseconds)"
echo "============================================================"
echo ""

# Test 1: Binary exists on PATH
run_test "Binary on PATH" '
    if command -v passfx >/dev/null 2>&1; then
        log_info "Found passfx at: $(command -v passfx)"
        return 0
    else
        log_error "passfx not found on PATH"
        log_error "PATH=$PATH"
        return 1
    fi
'

# Test 2: --version outputs expected format
run_test "Version output" '
    VERSION_OUTPUT=$(passfx --version 2>&1)
    if echo "$VERSION_OUTPUT" | grep -q "passfx $EXPECTED_VERSION"; then
        log_info "Version output: $VERSION_OUTPUT"
        return 0
    else
        log_error "Unexpected version output: $VERSION_OUTPUT"
        log_error "Expected: passfx $EXPECTED_VERSION"
        return 1
    fi
'

# Test 3: --version exit code is 0
run_test "Version exit code" '
    passfx --version >/dev/null 2>&1
    EXIT=$?
    if [ $EXIT -eq 0 ]; then
        log_info "Exit code: $EXIT"
        return 0
    else
        log_error "Exit code: $EXIT (expected 0)"
        return 1
    fi
'

# Test 4: --help outputs expected content
run_test "Help output" '
    HELP_OUTPUT=$(passfx --help 2>&1)
    REQUIRED_STRINGS=(
        "secure terminal password manager"
        "PBKDF2"
        "Fernet"
        "~/.passfx"
    )

    for required in "${REQUIRED_STRINGS[@]}"; do
        if ! echo "$HELP_OUTPUT" | grep -qi "$required"; then
            log_error "Missing expected string in help: $required"
            return 1
        fi
    done

    log_info "Help output contains all expected strings"
    return 0
'

# Test 5: --help exit code is 0
run_test "Help exit code" '
    passfx --help >/dev/null 2>&1
    EXIT=$?
    if [ $EXIT -eq 0 ]; then
        log_info "Exit code: $EXIT"
        return 0
    else
        log_error "Exit code: $EXIT (expected 0)"
        return 1
    fi
'

# Test 6: No unexpected stderr on --help
run_test "No stderr on help" '
    STDERR_OUTPUT=$(passfx --help 2>&1 >/dev/null)
    if [ -z "$STDERR_OUTPUT" ]; then
        log_info "No unexpected stderr output"
        return 0
    else
        log_error "Unexpected stderr: $STDERR_OUTPUT"
        return 1
    fi
'

# Test 7: No unexpected stderr on --version
run_test "No stderr on version" '
    STDERR_OUTPUT=$(passfx --version 2>&1 >/dev/null)
    if [ -z "$STDERR_OUTPUT" ]; then
        log_info "No unexpected stderr output"
        return 0
    else
        log_error "Unexpected stderr: $STDERR_OUTPUT"
        return 1
    fi
'

# Tests 8-11: Module import tests (skip for pipx - it isolates packages)
if [ "$INSTALL_METHOD" != "pipx" ]; then
    # Test 8: Module can be imported
    run_test "Python module import" '
        python -c "import passfx" 2>&1
        EXIT=$?
        if [ $EXIT -eq 0 ]; then
            log_info "Module imports successfully"
            return 0
        else
            log_error "Module import failed"
            return 1
        fi
    '

    # Test 9: CLI module can be imported
    run_test "CLI module import" '
        python -c "from passfx.cli import main" 2>&1
        EXIT=$?
        if [ $EXIT -eq 0 ]; then
            log_info "CLI module imports successfully"
            return 0
        else
            log_error "CLI module import failed"
            return 1
        fi
    '

    # Test 10: Version constant matches
    run_test "Version constant match" '
        PYTHON_VERSION=$(python -c "from passfx.cli import __version__; print(__version__)" 2>&1)
        if [ "$PYTHON_VERSION" = "$EXPECTED_VERSION" ]; then
            log_info "Python version constant: $PYTHON_VERSION"
            return 0
        else
            log_error "Python version constant: $PYTHON_VERSION (expected $EXPECTED_VERSION)"
            return 1
        fi
    '

    # Test 11: Core modules exist
    run_test "Core modules exist" '
        MODULES=(
            "passfx.core.crypto"
            "passfx.core.vault"
            "passfx.core.models"
        )

        for mod in "${MODULES[@]}"; do
            if ! python -c "import $mod" 2>&1; then
                log_error "Failed to import: $mod"
                return 1
            fi
        done

        log_info "All core modules import successfully"
        return 0
    '
else
    log_info "Skipping module import tests for pipx (packages are isolated)"
fi

# Test 12: Invalid argument handling
run_test "Invalid argument handling" '
    # Unknown flag should not crash (may exit non-zero, that is OK)
    # We just want to ensure it does not produce a Python traceback
    OUTPUT=$(passfx --invalid-flag-12345 2>&1 || true)
    if echo "$OUTPUT" | grep -q "Traceback"; then
        log_error "Python traceback exposed to user"
        return 1
    else
        log_info "No traceback on invalid argument"
        return 0
    fi
'

# Test 13: Data directory is configurable (doesn't touch real home)
run_test "No premature filesystem access" '
    # Running --help or --version should not create ~/.passfx
    # This test verifies CLI args are processed before TUI launch
    rm -rf ~/.passfx 2>/dev/null || true
    passfx --help >/dev/null 2>&1
    if [ -d ~/.passfx ]; then
        log_error "~/.passfx created during --help (should not happen)"
        return 1
    else
        log_info "No filesystem side effects on --help"
        return 0
    fi
'

# Print summary
echo ""
echo "============================================================"
echo "Validation Summary"
echo "============================================================"
echo "Install Method: $INSTALL_METHOD"
echo "Tests Run: $TESTS_RUN"
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $((TESTS_RUN - TESTS_PASSED))"
echo "============================================================"

if [ $EXIT_CODE -eq 0 ]; then
    log_info "ALL TESTS PASSED"
else
    log_error "SOME TESTS FAILED"
fi

exit $EXIT_CODE
