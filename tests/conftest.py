# Shared Test Fixtures
# Provides common fixtures for all test modules. Security-critical fixtures
# (crypto, vault) are intentionally excluded from Phase 0 infrastructure.

from __future__ import annotations

import os
import stat
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable


# Temporary Directory Fixtures


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory that is cleaned up after the test.

    Provides an isolated filesystem location for tests that require file I/O.
    Directory permissions are set to 0o700 matching PassFX security defaults.
    """
    with tempfile.TemporaryDirectory(prefix="passfx_test_") as tmpdir:
        path = Path(tmpdir)
        os.chmod(path, stat.S_IRWXU)
        yield path


@pytest.fixture
def temp_vault_dir(temp_dir: Path) -> Path:
    """Create a temporary directory structured like ~/.passfx for vault tests.

    Creates the expected directory structure with proper permissions:
    - vault_dir/ (0o700)
    - vault_dir/logs/ (0o700)

    Does not create actual vault files; those should be created by tests.
    """
    logs_dir = temp_dir / "logs"
    logs_dir.mkdir(mode=0o700)
    return temp_dir


@pytest.fixture
def temp_file(temp_dir: Path) -> Generator[Callable[[str, str], Path], None, None]:
    """Factory fixture to create temporary files with content.

    Usage:
        def test_example(temp_file):
            path = temp_file("test.txt", "content")
            assert path.read_text() == "content"
    """

    def _create_temp_file(name: str, content: str = "") -> Path:
        file_path = temp_dir / name
        file_path.write_text(content)
        os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
        return file_path

    yield _create_temp_file


# Environment Isolation Fixtures


@pytest.fixture
def isolated_env(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[pytest.MonkeyPatch, None, None]:
    """Provide an isolated environment with common PassFX variables cleared.

    Clears environment variables that could affect test behavior:
    - HOME (prevents access to real ~/.passfx)
    - XDG_* directories
    - PASSFX_* configuration
    """
    env_vars_to_clear = [
        "PASSFX_HOME",
        "PASSFX_DEBUG",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
    ]
    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)
    yield monkeypatch


@pytest.fixture
def mock_home(
    temp_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[Path, None, None]:
    """Override HOME to point to a temporary directory.

    Useful for tests that need to verify ~/.passfx behavior without
    touching the real home directory.
    """
    monkeypatch.setenv("HOME", str(temp_dir))
    yield temp_dir


# Marker-Based Fixtures


@pytest.fixture(autouse=True)
def _skip_slow_unless_requested(request: pytest.FixtureRequest) -> None:
    """Skip tests marked as 'slow' unless explicitly requested.

    Run slow tests with: pytest -m slow
    Run all tests with: pytest --run-slow
    """
    if request.node.get_closest_marker("slow"):
        if not request.config.getoption("--run-slow", default=False):
            pytest.skip("Slow test - use --run-slow to execute")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command-line options for pytest."""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run tests marked as slow",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with -m 'not slow')"
    )


# Test Lifecycle Hooks


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Hook called before each test runs.

    Validates that security tests have proper markers.
    """
    if "security" in str(item.fspath):
        markers = [m.name for m in item.iter_markers()]
        if "security" not in markers:
            pytest.fail(
                f"Security test {item.name} must have @pytest.mark.security decorator"
            )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Modify test collection to add implicit markers based on path."""
    for item in items:
        # Add markers based on test location
        test_path = str(item.fspath)
        if "/unit/" in test_path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in test_path:
            item.add_marker(pytest.mark.integration)
        elif "/security/" in test_path:
            item.add_marker(pytest.mark.security)


# Utility Functions for Tests


@pytest.fixture
def assert_file_permissions() -> Callable[[Path, int], None]:
    """Fixture providing a helper to verify file permissions.

    Usage:
        def test_permissions(assert_file_permissions, temp_file):
            path = temp_file("test.txt", "content")
            assert_file_permissions(path, 0o600)
    """

    def _assert_permissions(path: Path, expected_mode: int) -> None:
        actual_mode = stat.S_IMODE(path.stat().st_mode)
        assert (
            actual_mode == expected_mode
        ), f"Expected permissions {oct(expected_mode)}, got {oct(actual_mode)}"

    return _assert_permissions


@pytest.fixture
def assert_dir_permissions() -> Callable[[Path, int], None]:
    """Fixture providing a helper to verify directory permissions.

    Usage:
        def test_dir_permissions(assert_dir_permissions, temp_dir):
            assert_dir_permissions(temp_dir, 0o700)
    """

    def _assert_permissions(path: Path, expected_mode: int) -> None:
        actual_mode = stat.S_IMODE(path.stat().st_mode)
        assert (
            actual_mode == expected_mode
        ), f"Expected directory permissions {oct(expected_mode)}, got {oct(actual_mode)}"

    return _assert_permissions
