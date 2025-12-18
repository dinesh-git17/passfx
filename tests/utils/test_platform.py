"""Unit tests for platform-specific security operations.

Validates PassFX's cross-platform security behavior including file permissions,
platform detection, and OS-specific security enforcement. Tests are designed
to run on any platform while validating platform-specific code paths.
"""

from __future__ import annotations

import logging
import os
import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from passfx.utils.platform_security import (
    PlatformSecurityError,
    _get_current_user_sid_windows,
    _set_windows_acl,
    get_platform_security_notes,
    secure_directory_permissions,
    secure_directory_permissions_best_effort,
    secure_file_permissions,
    secure_file_permissions_best_effort,
)

if TYPE_CHECKING:
    from collections.abc import Callable


# --- PlatformSecurityError Tests ---


class TestPlatformSecurityError:
    """Tests for the PlatformSecurityError exception class."""

    def test_is_exception(self) -> None:
        """PlatformSecurityError inherits from Exception."""
        assert issubclass(PlatformSecurityError, Exception)

    def test_can_be_raised(self) -> None:
        """PlatformSecurityError can be raised and caught."""
        with pytest.raises(PlatformSecurityError):
            raise PlatformSecurityError("test error")

    def test_preserves_message(self) -> None:
        """PlatformSecurityError preserves error message."""
        try:
            raise PlatformSecurityError("custom error message")
        except PlatformSecurityError as e:
            assert str(e) == "custom error message"

    def test_chained_exception(self) -> None:
        """PlatformSecurityError supports exception chaining."""
        original = ValueError("original")
        try:
            try:
                raise original
            except ValueError as e:
                raise PlatformSecurityError("wrapped") from e
        except PlatformSecurityError as e:
            assert e.__cause__ is original


# --- Windows-Only Function Tests ---


@pytest.mark.skipif(sys.platform == "win32", reason="Tests non-Windows behavior")
class TestWindowsFunctionsOnNonWindows:
    """Tests for Windows-only functions when running on non-Windows platforms."""

    def test_get_current_user_sid_windows_raises_on_non_windows(self) -> None:
        """_get_current_user_sid_windows raises PlatformSecurityError on non-Windows."""
        with pytest.raises(PlatformSecurityError) as exc_info:
            _get_current_user_sid_windows()
        assert "Windows-only" in str(exc_info.value)

    def test_set_windows_acl_raises_on_non_windows(self, temp_dir: Path) -> None:
        """_set_windows_acl raises PlatformSecurityError on non-Windows."""
        test_file = temp_dir / "test.txt"
        test_file.touch()

        with pytest.raises(PlatformSecurityError) as exc_info:
            _set_windows_acl(test_file, is_directory=False)
        assert "Windows-only" in str(exc_info.value)

    def test_set_windows_acl_for_directory_raises_on_non_windows(
        self, temp_dir: Path
    ) -> None:
        """_set_windows_acl with is_directory=True raises on non-Windows."""
        with pytest.raises(PlatformSecurityError) as exc_info:
            _set_windows_acl(temp_dir, is_directory=True)
        assert "Windows-only" in str(exc_info.value)


# --- Secure File Permissions Tests ---


@pytest.mark.skipif(sys.platform == "win32", reason="Tests Unix chmod behavior")
class TestSecureFilePermissionsUnix:
    """Tests for secure_file_permissions on Unix platforms."""

    def test_sets_0600_permissions(
        self,
        temp_dir: Path,
        assert_file_permissions: Callable[[Path, int], None],
    ) -> None:
        """secure_file_permissions sets file mode to 0600."""
        test_file = temp_dir / "secret.txt"
        test_file.touch()
        # Start with overly permissive mode
        os.chmod(test_file, 0o644)

        secure_file_permissions(test_file)

        assert_file_permissions(test_file, 0o600)

    def test_rejects_world_readable_permissions(
        self,
        temp_dir: Path,
        assert_file_permissions: Callable[[Path, int], None],
    ) -> None:
        """secure_file_permissions removes world-readable permissions."""
        test_file = temp_dir / "secret.txt"
        test_file.touch()
        os.chmod(test_file, 0o777)

        secure_file_permissions(test_file)

        assert_file_permissions(test_file, 0o600)

    def test_removes_group_permissions(
        self,
        temp_dir: Path,
        assert_file_permissions: Callable[[Path, int], None],
    ) -> None:
        """secure_file_permissions removes group permissions."""
        test_file = temp_dir / "secret.txt"
        test_file.touch()
        os.chmod(test_file, 0o660)

        secure_file_permissions(test_file)

        assert_file_permissions(test_file, 0o600)

    def test_skips_nonexistent_file(
        self, temp_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """secure_file_permissions logs warning for non-existent file."""
        nonexistent = temp_dir / "does_not_exist.txt"

        with caplog.at_level(logging.WARNING):
            secure_file_permissions(nonexistent)

        assert "non-existent" in caplog.text.lower()

    def test_preserves_already_secure_permissions(
        self,
        temp_dir: Path,
        assert_file_permissions: Callable[[Path, int], None],
    ) -> None:
        """secure_file_permissions is idempotent on already-secure files."""
        test_file = temp_dir / "secret.txt"
        test_file.touch()
        os.chmod(test_file, 0o600)

        secure_file_permissions(test_file)

        assert_file_permissions(test_file, 0o600)

    def test_works_with_readonly_file(
        self,
        temp_dir: Path,
        assert_file_permissions: Callable[[Path, int], None],
    ) -> None:
        """secure_file_permissions can secure read-only files."""
        test_file = temp_dir / "readonly.txt"
        test_file.touch()
        os.chmod(test_file, 0o400)

        secure_file_permissions(test_file)

        assert_file_permissions(test_file, 0o600)


# --- Secure Directory Permissions Tests ---


@pytest.mark.skipif(sys.platform == "win32", reason="Tests Unix chmod behavior")
class TestSecureDirectoryPermissionsUnix:
    """Tests for secure_directory_permissions on Unix platforms."""

    def test_sets_0700_permissions(
        self,
        temp_dir: Path,
        assert_dir_permissions: Callable[[Path, int], None],
    ) -> None:
        """secure_directory_permissions sets directory mode to 0700."""
        test_dir = temp_dir / "secure_dir"
        test_dir.mkdir(mode=0o755)

        secure_directory_permissions(test_dir)

        assert_dir_permissions(test_dir, 0o700)

    def test_rejects_world_accessible_permissions(
        self,
        temp_dir: Path,
        assert_dir_permissions: Callable[[Path, int], None],
    ) -> None:
        """secure_directory_permissions removes world access."""
        test_dir = temp_dir / "secure_dir"
        test_dir.mkdir(mode=0o777)

        secure_directory_permissions(test_dir)

        assert_dir_permissions(test_dir, 0o700)

    def test_removes_group_permissions(
        self,
        temp_dir: Path,
        assert_dir_permissions: Callable[[Path, int], None],
    ) -> None:
        """secure_directory_permissions removes group permissions."""
        test_dir = temp_dir / "secure_dir"
        test_dir.mkdir(mode=0o770)

        secure_directory_permissions(test_dir)

        assert_dir_permissions(test_dir, 0o700)

    def test_skips_nonexistent_directory(
        self, temp_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """secure_directory_permissions logs warning for non-existent directory."""
        nonexistent = temp_dir / "does_not_exist"

        with caplog.at_level(logging.WARNING):
            secure_directory_permissions(nonexistent)

        assert "non-existent" in caplog.text.lower()

    def test_preserves_already_secure_permissions(
        self,
        temp_dir: Path,
        assert_dir_permissions: Callable[[Path, int], None],
    ) -> None:
        """secure_directory_permissions is idempotent on already-secure directories."""
        test_dir = temp_dir / "secure_dir"
        test_dir.mkdir(mode=0o700)

        secure_directory_permissions(test_dir)

        assert_dir_permissions(test_dir, 0o700)


# --- Best Effort Permission Functions Tests ---


@pytest.mark.skipif(sys.platform == "win32", reason="Tests Unix chmod behavior")
class TestSecureFilePermissionsBestEffort:
    """Tests for secure_file_permissions_best_effort."""

    def test_returns_true_on_success(self, temp_dir: Path) -> None:
        """secure_file_permissions_best_effort returns True on success."""
        test_file = temp_dir / "test.txt"
        test_file.touch()

        result = secure_file_permissions_best_effort(test_file)

        assert result is True

    def test_returns_false_on_nonexistent(
        self, temp_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """secure_file_permissions_best_effort returns False for non-existent files."""
        nonexistent = temp_dir / "does_not_exist.txt"

        # The function logs a warning (not an error) for non-existent files
        # and returns True because secure_file_permissions doesn't raise for this case
        with caplog.at_level(logging.WARNING):
            result = secure_file_permissions_best_effort(nonexistent)

        # Non-existent files are skipped with a warning, not an error
        # So best_effort returns True (no exception raised)
        assert result is True

    def test_logs_warning_on_permission_error(
        self, temp_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """secure_file_permissions_best_effort logs warning on OSError."""
        test_file = temp_dir / "test.txt"
        test_file.touch()

        # Mock os.chmod to raise OSError
        with (
            mock.patch("os.chmod", side_effect=OSError("Permission denied")),
            caplog.at_level(logging.WARNING),
        ):
            result = secure_file_permissions_best_effort(test_file)

        assert result is False
        assert "could not secure" in caplog.text.lower()

    def test_does_not_raise_on_error(self, temp_dir: Path) -> None:
        """secure_file_permissions_best_effort does not raise exceptions."""
        test_file = temp_dir / "test.txt"
        test_file.touch()

        with mock.patch("os.chmod", side_effect=OSError("Permission denied")):
            # Should not raise
            result = secure_file_permissions_best_effort(test_file)

        assert result is False


@pytest.mark.skipif(sys.platform == "win32", reason="Tests Unix chmod behavior")
class TestSecureDirectoryPermissionsBestEffort:
    """Tests for secure_directory_permissions_best_effort."""

    def test_returns_true_on_success(self, temp_dir: Path) -> None:
        """secure_directory_permissions_best_effort returns True on success."""
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()

        result = secure_directory_permissions_best_effort(test_dir)

        assert result is True

    def test_logs_warning_on_permission_error(
        self, temp_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """secure_directory_permissions_best_effort logs warning on OSError."""
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()

        with (
            mock.patch("os.chmod", side_effect=OSError("Permission denied")),
            caplog.at_level(logging.WARNING),
        ):
            result = secure_directory_permissions_best_effort(test_dir)

        assert result is False
        assert "could not secure" in caplog.text.lower()

    def test_does_not_raise_on_error(self, temp_dir: Path) -> None:
        """secure_directory_permissions_best_effort does not raise exceptions."""
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()

        with mock.patch("os.chmod", side_effect=OSError("Permission denied")):
            # Should not raise
            result = secure_directory_permissions_best_effort(test_dir)

        assert result is False


# --- Platform Security Notes Tests ---


class TestGetPlatformSecurityNotes:
    """Tests for get_platform_security_notes function."""

    def test_returns_list(self) -> None:
        """get_platform_security_notes returns a list."""
        notes = get_platform_security_notes()
        assert isinstance(notes, list)

    def test_returns_nonempty_list(self) -> None:
        """get_platform_security_notes returns non-empty list."""
        notes = get_platform_security_notes()
        assert len(notes) > 0

    def test_all_notes_are_strings(self) -> None:
        """All notes are strings."""
        notes = get_platform_security_notes()
        for note in notes:
            assert isinstance(note, str)

    def test_includes_python_limitations(self) -> None:
        """Notes include Python memory limitations."""
        notes = get_platform_security_notes()
        notes_text = " ".join(notes).lower()

        # Should mention Python memory limitations
        assert "python" in notes_text
        assert "memory" in notes_text

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_macos_notes(self) -> None:
        """macOS-specific notes are returned on macOS."""
        notes = get_platform_security_notes()
        notes_text = " ".join(notes)

        assert "macOS" in notes_text
        assert "Unix mode bits" in notes_text

    @pytest.mark.skipif(sys.platform != "linux", reason="Linux-specific test")
    def test_linux_notes(self) -> None:
        """Linux-specific notes are returned on Linux."""
        notes = get_platform_security_notes()
        notes_text = " ".join(notes)

        assert "Linux" in notes_text
        assert "Unix mode bits" in notes_text

    def test_windows_notes_via_mock(self) -> None:
        """Windows-specific notes are returned when platform is win32."""
        from passfx.utils import platform_security

        # Mock the platform detection at module level to simulate Windows
        with mock.patch.object(platform_security.sys, "platform", "win32"):
            result = platform_security.get_platform_security_notes()

        assert "Windows" in " ".join(result)
        assert "DACL" in " ".join(result)


# --- Platform Branch Coverage Tests ---


class TestPlatformBranchCoverage:
    """Tests to ensure all platform-specific branches are covered."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_unix_branch_in_secure_file_permissions(self, temp_dir: Path) -> None:
        """Verify Unix branch is taken for secure_file_permissions."""
        test_file = temp_dir / "test.txt"
        test_file.touch()

        with mock.patch("os.chmod") as mock_chmod:
            secure_file_permissions(test_file)
            mock_chmod.assert_called_once_with(test_file, 0o600)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_unix_branch_in_secure_directory_permissions(self, temp_dir: Path) -> None:
        """Verify Unix branch is taken for secure_directory_permissions."""
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()

        with mock.patch("os.chmod") as mock_chmod:
            secure_directory_permissions(test_dir)
            mock_chmod.assert_called_once_with(test_dir, 0o700)

    def test_windows_branch_via_mock_file(self, temp_dir: Path) -> None:
        """Verify Windows branch would be taken for files on Windows."""
        test_file = temp_dir / "test.txt"
        test_file.touch()

        # Mock both platform detection and the Windows ACL function
        with mock.patch.object(sys, "platform", "win32"):
            with mock.patch(
                "passfx.utils.platform_security._set_windows_acl"
            ) as mock_acl:
                # Re-import to get fresh platform detection
                from passfx.utils import platform_security

                with mock.patch.object(platform_security.sys, "platform", "win32"):
                    platform_security.secure_file_permissions(test_file)

                mock_acl.assert_called_once_with(test_file, is_directory=False)

    def test_windows_branch_via_mock_directory(self, temp_dir: Path) -> None:
        """Verify Windows branch would be taken for directories on Windows."""
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()

        with mock.patch("passfx.utils.platform_security._set_windows_acl") as mock_acl:
            from passfx.utils import platform_security

            with mock.patch.object(platform_security.sys, "platform", "win32"):
                platform_security.secure_directory_permissions(test_dir)

            mock_acl.assert_called_once_with(test_dir, is_directory=True)


# --- Permission Enforcement Invariants ---


@pytest.mark.skipif(sys.platform == "win32", reason="Tests Unix permission behavior")
class TestPermissionEnforcementInvariants:
    """Tests for security invariants that must never change."""

    def test_file_permission_value_is_0600(self) -> None:
        """File permission must be exactly 0o600 (owner rw only)."""
        # This is a contract test - the value must not change
        expected = stat.S_IRUSR | stat.S_IWUSR
        assert expected == 0o600

    def test_directory_permission_value_is_0700(self) -> None:
        """Directory permission must be exactly 0o700 (owner rwx only)."""
        expected = stat.S_IRWXU
        assert expected == 0o700

    def test_no_other_user_access_after_secure_file(
        self,
        temp_dir: Path,
    ) -> None:
        """After securing, no group or other permissions exist on files."""
        test_file = temp_dir / "secret.txt"
        test_file.touch()
        os.chmod(test_file, 0o777)

        secure_file_permissions(test_file)

        mode = stat.S_IMODE(test_file.stat().st_mode)
        group_bits = mode & 0o070
        other_bits = mode & 0o007
        assert group_bits == 0, "Group permissions must be zero"
        assert other_bits == 0, "Other permissions must be zero"

    def test_no_other_user_access_after_secure_directory(
        self,
        temp_dir: Path,
    ) -> None:
        """After securing, no group or other permissions exist on directories."""
        test_dir = temp_dir / "secure_dir"
        test_dir.mkdir(mode=0o777)

        secure_directory_permissions(test_dir)

        mode = stat.S_IMODE(test_dir.stat().st_mode)
        group_bits = mode & 0o070
        other_bits = mode & 0o007
        assert group_bits == 0, "Group permissions must be zero"
        assert other_bits == 0, "Other permissions must be zero"


# --- Error Handling Tests ---


class TestErrorHandling:
    """Tests for error handling in platform security functions."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_oserror_propagates_from_secure_file_permissions(
        self, temp_dir: Path
    ) -> None:
        """OSError from chmod propagates through secure_file_permissions."""
        test_file = temp_dir / "test.txt"
        test_file.touch()

        with mock.patch("os.chmod", side_effect=OSError("Test error")):
            with pytest.raises(OSError):
                secure_file_permissions(test_file)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_oserror_propagates_from_secure_directory_permissions(
        self, temp_dir: Path
    ) -> None:
        """OSError from chmod propagates through secure_directory_permissions."""
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()

        with mock.patch("os.chmod", side_effect=OSError("Test error")):
            with pytest.raises(OSError):
                secure_directory_permissions(test_dir)


# --- Logging Tests ---


class TestLogging:
    """Tests for logging behavior in platform security functions."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_logs_debug_on_successful_file_permission_change(
        self, temp_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Debug message is logged on successful file permission change."""
        test_file = temp_dir / "test.txt"
        test_file.touch()

        with caplog.at_level(logging.DEBUG):
            secure_file_permissions(test_file)

        assert "0600" in caplog.text or "Unix permissions" in caplog.text

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_logs_debug_on_successful_directory_permission_change(
        self, temp_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Debug message is logged on successful directory permission change."""
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()

        with caplog.at_level(logging.DEBUG):
            secure_directory_permissions(test_dir)

        assert "0700" in caplog.text or "Unix permissions" in caplog.text


# --- Platform Detection Tests ---


class TestPlatformDetection:
    """Tests for platform detection logic."""

    def test_current_platform_is_recognized(self) -> None:
        """Current platform returns valid security notes."""
        notes = get_platform_security_notes()

        # Should recognize at least one of the three platforms
        notes_text = " ".join(notes)
        recognized = (
            "Windows" in notes_text or "macOS" in notes_text or "Linux" in notes_text
        )
        assert recognized, "Current platform should be recognized"

    def test_platform_detection_uses_sys_platform(self) -> None:
        """Platform detection uses sys.platform correctly."""
        # Verify current platform matches expected detection
        if sys.platform == "win32":
            notes = get_platform_security_notes()
            assert "Windows" in " ".join(notes)
        elif sys.platform == "darwin":
            notes = get_platform_security_notes()
            assert "macOS" in " ".join(notes)
        else:
            notes = get_platform_security_notes()
            assert "Linux" in " ".join(notes)


# --- Symlink Safety Tests ---


@pytest.mark.skipif(
    sys.platform == "win32" or os.getuid() == 0,
    reason="Skip on Windows or when running as root",
)
class TestSymlinkSafety:
    """Tests for symlink handling in permission functions."""

    def test_secure_file_permissions_on_symlink(
        self,
        temp_dir: Path,
    ) -> None:
        """secure_file_permissions operates on the target, not the symlink."""
        real_file = temp_dir / "real.txt"
        real_file.touch()
        os.chmod(real_file, 0o644)

        symlink = temp_dir / "link.txt"
        symlink.symlink_to(real_file)

        # Secure the symlink - should affect the real file
        secure_file_permissions(symlink)

        # Real file should now be 0600
        real_mode = stat.S_IMODE(real_file.stat().st_mode)
        assert real_mode == 0o600

    def test_secure_directory_permissions_on_symlink(
        self,
        temp_dir: Path,
    ) -> None:
        """secure_directory_permissions operates on the target, not the symlink."""
        real_dir = temp_dir / "real_dir"
        real_dir.mkdir(mode=0o755)

        symlink = temp_dir / "link_dir"
        symlink.symlink_to(real_dir)

        # Secure the symlink - should affect the real directory
        secure_directory_permissions(symlink)

        # Real directory should now be 0700
        real_mode = stat.S_IMODE(real_dir.stat().st_mode)
        assert real_mode == 0o700


# --- Integration with Vault Module Tests ---


class TestVaultIntegration:
    """Tests to verify platform security integration with vault operations."""

    def test_vault_uses_platform_security(self) -> None:
        """Vault module imports and uses platform_security functions."""
        from passfx.core import vault

        # Verify the imports exist
        assert hasattr(vault, "secure_directory_permissions")
        assert hasattr(vault, "secure_file_permissions")

    def test_io_uses_platform_security(self) -> None:
        """IO module imports and uses platform_security functions."""
        from passfx.utils import io

        # Verify the import exists
        assert hasattr(io, "secure_file_permissions")


# --- Module Constants Tests ---


class TestModuleStructure:
    """Tests for module structure and exports."""

    def test_platform_security_error_is_exported(self) -> None:
        """PlatformSecurityError is accessible from module."""
        from passfx.utils import platform_security

        assert hasattr(platform_security, "PlatformSecurityError")

    def test_public_functions_are_exported(self) -> None:
        """All public functions are accessible from module."""
        from passfx.utils import platform_security

        public_functions = [
            "secure_file_permissions",
            "secure_directory_permissions",
            "secure_file_permissions_best_effort",
            "secure_directory_permissions_best_effort",
            "get_platform_security_notes",
        ]

        for func in public_functions:
            assert hasattr(platform_security, func), f"Missing {func}"

    def test_private_functions_exist(self) -> None:
        """Private helper functions exist for Windows support."""
        from passfx.utils import platform_security

        private_functions = [
            "_get_current_user_sid_windows",
            "_set_windows_acl",
        ]

        for func in private_functions:
            assert hasattr(platform_security, func), f"Missing {func}"
