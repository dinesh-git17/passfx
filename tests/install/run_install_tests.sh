#!/usr/bin/env bash
# run_install_tests.sh - Docker-based PassFX installation test harness
#
# This script builds and runs Docker containers to validate that PassFX
# installs correctly via pip, pipx, and Homebrew. It is designed to catch
# packaging and installation issues before they reach users.
#
# Usage:
#   ./run_install_tests.sh              # Run all tests
#   ./run_install_tests.sh pip          # Run pip test only
#   ./run_install_tests.sh pipx         # Run pipx test only
#   ./run_install_tests.sh brew         # Run brew test only
#   ./run_install_tests.sh pip pipx     # Run multiple tests
#
# Options:
#   --python VERSION    Python version for pip/pipx tests (default: 3.11)
#   --version VERSION   PassFX version to install (default: latest)
#   --no-cache          Build without Docker cache
#   --verbose           Enable verbose output
#   --help              Show this help message

set -euo pipefail

# Script directory (where Dockerfiles live)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration defaults
PYTHON_VERSION="3.11"
PASSFX_VERSION=""
NO_CACHE=""
VERBOSE=""
TESTS_TO_RUN=()

# Exit codes
EXIT_SUCCESS=0
EXIT_DOCKER_NOT_RUNNING=1
EXIT_BUILD_FAILED=2
EXIT_TEST_FAILED=3
EXIT_INVALID_ARGS=4

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "\n${BLUE}==> $1${NC}"; }

# Print usage
print_usage() {
    cat <<EOF
PassFX Installation Test Harness

Usage:
    $(basename "$0") [options] [test...]

Tests:
    pip     Test pip installation (python:3.XX-slim)
    pipx    Test pipx installation (python:3.XX-slim)
    brew    Test Homebrew installation (homebrew/brew)
    all     Run all tests (default if none specified)

Options:
    --python VERSION    Python version for pip/pipx tests (default: 3.11)
    --version VERSION   PassFX version to install (default: latest)
    --no-cache          Build without Docker cache
    --verbose           Enable verbose output
    --help              Show this help message

Examples:
    $(basename "$0")                    # Run all tests
    $(basename "$0") pip pipx           # Run pip and pipx tests
    $(basename "$0") --python 3.12 pip  # Test with Python 3.12
    $(basename "$0") --version 1.0.1    # Test specific version

Requirements:
    - Docker must be installed and running
    - Internet access to pull images and packages
EOF
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --python)
                PYTHON_VERSION="$2"
                shift 2
                ;;
            --version)
                PASSFX_VERSION="$2"
                shift 2
                ;;
            --no-cache)
                NO_CACHE="--no-cache"
                shift
                ;;
            --verbose)
                VERBOSE="1"
                shift
                ;;
            --help|-h)
                print_usage
                exit $EXIT_SUCCESS
                ;;
            pip|pipx|brew)
                TESTS_TO_RUN+=("$1")
                shift
                ;;
            all)
                TESTS_TO_RUN=(pip pipx brew)
                shift
                ;;
            *)
                log_error "Unknown argument: $1"
                print_usage
                exit $EXIT_INVALID_ARGS
                ;;
        esac
    done

    # Default to all tests if none specified
    if [[ ${#TESTS_TO_RUN[@]} -eq 0 ]]; then
        TESTS_TO_RUN=(pip pipx brew)
    fi
}

# Check Docker is available
check_docker() {
    log_step "Checking Docker availability"

    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed"
        exit $EXIT_DOCKER_NOT_RUNNING
    fi

    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running"
        log_error "Start Docker and try again"
        exit $EXIT_DOCKER_NOT_RUNNING
    fi

    log_info "Docker is available"
}

# Build and run a test
run_test() {
    local test_name="$1"
    local dockerfile="Dockerfile.$test_name"
    local image_tag="passfx-test-$test_name"

    log_step "Running $test_name installation test"

    # Check Dockerfile exists
    if [[ ! -f "$SCRIPT_DIR/$dockerfile" ]]; then
        log_error "Dockerfile not found: $SCRIPT_DIR/$dockerfile"
        return 1
    fi

    # Build arguments
    local build_args=()
    build_args+=("--file" "$SCRIPT_DIR/$dockerfile")
    build_args+=("--tag" "$image_tag")

    if [[ -n "$NO_CACHE" ]]; then
        build_args+=("--no-cache")
    fi

    # Add Python version for pip/pipx tests
    if [[ "$test_name" == "pip" || "$test_name" == "pipx" ]]; then
        build_args+=("--build-arg" "PYTHON_VERSION=$PYTHON_VERSION")
    fi

    # Add PassFX version if specified
    if [[ -n "$PASSFX_VERSION" ]]; then
        build_args+=("--build-arg" "PASSFX_VERSION=$PASSFX_VERSION")
    fi

    build_args+=("$SCRIPT_DIR")

    # Build the image
    log_info "Building Docker image: $image_tag"
    if [[ -n "$VERBOSE" ]]; then
        if ! docker build "${build_args[@]}"; then
            log_error "Failed to build image: $image_tag"
            return 1
        fi
    else
        if ! docker build "${build_args[@]}" --quiet; then
            log_error "Failed to build image: $image_tag"
            return 1
        fi
    fi

    log_info "Image built successfully"

    # Run the container
    log_info "Running validation tests"
    if ! docker run --rm "$image_tag"; then
        log_error "Tests failed for $test_name"
        return 1
    fi

    log_info "$test_name installation test PASSED"
    return 0
}

# Main
main() {
    parse_args "$@"

    echo ""
    echo "============================================================"
    echo "PassFX Installation Test Harness"
    echo "============================================================"
    echo "Python Version: $PYTHON_VERSION"
    echo "PassFX Version: ${PASSFX_VERSION:-latest}"
    echo "Tests to Run: ${TESTS_TO_RUN[*]}"
    echo "============================================================"
    echo ""

    check_docker

    local failed_tests=()
    local passed_tests=()

    for test in "${TESTS_TO_RUN[@]}"; do
        if run_test "$test"; then
            passed_tests+=("$test")
        else
            failed_tests+=("$test")
        fi
    done

    # Summary
    echo ""
    echo "============================================================"
    echo "Test Summary"
    echo "============================================================"
    echo "Passed: ${#passed_tests[@]}"
    echo "Failed: ${#failed_tests[@]}"

    if [[ ${#passed_tests[@]} -gt 0 ]]; then
        log_info "Passed tests: ${passed_tests[*]}"
    fi

    if [[ ${#failed_tests[@]} -gt 0 ]]; then
        log_error "Failed tests: ${failed_tests[*]}"
        exit $EXIT_TEST_FAILED
    fi

    echo "============================================================"
    log_info "ALL INSTALLATION TESTS PASSED"
    exit $EXIT_SUCCESS
}

main "$@"
