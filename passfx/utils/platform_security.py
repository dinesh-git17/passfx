"""Platform-specific file security for PassFX.

Provides cross-platform file permission enforcement:
- Unix: Standard chmod (0600/0700)
- Windows: DACL-based ACLs restricting access to current user only

Windows ACL implementation uses native Security APIs via ctypes,
avoiding external dependencies like pywin32.
"""

# pylint: disable=logging-too-many-args
# Note: pylint incorrectly flags logging calls as having too many args.
# All format strings are correct (verified manually).

from __future__ import annotations

import ctypes
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class PlatformSecurityError(Exception):
    """Raised when platform-specific security operations fail."""


# Windows-specific implementation
def _get_current_user_sid_windows() -> (  # pragma: no cover
    tuple[ctypes.Array[ctypes.c_ubyte], ctypes.c_void_p, int]
):  # pylint: disable=import-outside-toplevel
    """Get the current user's SID on Windows.

    Returns:
        Tuple of (SID buffer, SID pointer, SID length).
        The buffer must be kept alive while the pointer is in use.

    Raises:
        PlatformSecurityError: If SID cannot be obtained.
    """
    if sys.platform != "win32":
        raise PlatformSecurityError("This function is Windows-only")

    # Import Windows-specific modules
    from ctypes import wintypes

    # Windows Security API constants
    token_query = 0x0008

    # Load Windows DLLs (windll only exists on Windows)
    advapi32 = ctypes.windll.advapi32
    kernel32 = ctypes.windll.kernel32

    # Define TOKEN_USER structure locally
    class TokenUser(ctypes.Structure):  # noqa: N801
        """Windows TOKEN_USER structure."""

        _fields_ = [
            ("User_Sid", ctypes.c_void_p),
            ("User_Attributes", wintypes.DWORD),
        ]

    # Set up function prototypes
    kernel32.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    kernel32.OpenProcessToken.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.GetLastError.argtypes = []
    kernel32.GetLastError.restype = wintypes.DWORD

    advapi32.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi32.GetTokenInformation.restype = wintypes.BOOL
    advapi32.GetLengthSid.argtypes = [ctypes.c_void_p]
    advapi32.GetLengthSid.restype = wintypes.DWORD
    advapi32.CopySid.argtypes = [
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    advapi32.CopySid.restype = wintypes.BOOL

    token_handle = wintypes.HANDLE()
    try:
        # Open process token
        if not kernel32.OpenProcessToken(
            kernel32.GetCurrentProcess(),
            token_query,
            ctypes.byref(token_handle),
        ):
            raise PlatformSecurityError(
                f"OpenProcessToken failed: {kernel32.GetLastError()}"
            )

        # Get required buffer size
        token_info_length = wintypes.DWORD()
        advapi32.GetTokenInformation(
            token_handle,
            1,  # TokenUser
            None,
            0,
            ctypes.byref(token_info_length),
        )

        # Allocate buffer and get token info
        token_info_buffer = (ctypes.c_ubyte * token_info_length.value)()
        if not advapi32.GetTokenInformation(
            token_handle,
            1,  # TokenUser
            ctypes.byref(token_info_buffer),
            token_info_length,
            ctypes.byref(token_info_length),
        ):
            raise PlatformSecurityError(
                f"GetTokenInformation failed: {kernel32.GetLastError()}"
            )

        # Extract SID from TOKEN_USER structure
        token_user = ctypes.cast(
            ctypes.byref(token_info_buffer),
            ctypes.POINTER(TokenUser),
        ).contents

        sid_ptr = token_user.User_Sid
        sid_length: int = advapi32.GetLengthSid(sid_ptr)

        # Copy SID to our own buffer (so it persists after token close)
        sid_buffer = (ctypes.c_ubyte * sid_length)()
        if not advapi32.CopySid(
            sid_length,
            ctypes.byref(sid_buffer),
            sid_ptr,
        ):
            raise PlatformSecurityError(f"CopySid failed: {kernel32.GetLastError()}")

        # Return buffer AND pointer - buffer must stay alive while pointer is used
        sid_ptr_out = ctypes.cast(ctypes.byref(sid_buffer), ctypes.c_void_p)
        return sid_buffer, sid_ptr_out, sid_length

    finally:
        if token_handle:
            kernel32.CloseHandle(token_handle)


def _set_windows_acl(  # pragma: no cover  # pylint: disable=import-outside-toplevel
    path: Path,
    is_directory: bool = False,
) -> None:
    """Set Windows ACL to restrict access to current user only.

    Creates a DACL with a single ACE granting full control to the
    current user. All other access is implicitly denied.

    Args:
        path: Path to the file or directory.
        is_directory: If True, applies inheritance flags for directories.

    Raises:
        PlatformSecurityError: If ACL cannot be set.
    """
    if sys.platform != "win32":
        raise PlatformSecurityError("This function is Windows-only")

    # Import Windows-specific modules
    from ctypes import wintypes

    # Windows Security API constants
    dacl_security_information = 0x00000004
    protected_dacl_security_information = 0x80000000
    file_all_access = 0x001F01FF
    container_inherit_ace = 0x02
    object_inherit_ace = 0x01
    acl_revision = 2

    # Load Windows DLLs (windll only exists on Windows)
    advapi32 = ctypes.windll.advapi32
    kernel32 = ctypes.windll.kernel32

    # Define structures locally
    class Acl(ctypes.Structure):  # noqa: N801
        """Windows ACL structure."""

        _fields_ = [
            ("AclRevision", ctypes.c_ubyte),
            ("Sbz1", ctypes.c_ubyte),
            ("AclSize", wintypes.WORD),
            ("AceCount", wintypes.WORD),
            ("Sbz2", wintypes.WORD),
        ]

    class AceHeader(ctypes.Structure):  # noqa: N801
        """Windows ACE_HEADER structure."""

        _fields_ = [
            ("AceType", ctypes.c_ubyte),
            ("AceFlags", ctypes.c_ubyte),
            ("AceSize", wintypes.WORD),
        ]

    class AccessAllowedAce(ctypes.Structure):  # noqa: N801
        """Windows ACCESS_ALLOWED_ACE structure."""

        _fields_ = [
            ("Header", AceHeader),
            ("Mask", wintypes.DWORD),
            ("SidStart", wintypes.DWORD),
        ]

    class SecurityDescriptor(ctypes.Structure):  # noqa: N801
        """Windows SECURITY_DESCRIPTOR structure."""

        _fields_ = [
            ("Revision", ctypes.c_ubyte),
            ("Sbz1", ctypes.c_ubyte),
            ("Control", wintypes.WORD),
            ("Owner", ctypes.c_void_p),
            ("Group", ctypes.c_void_p),
            ("Sacl", ctypes.c_void_p),
            ("Dacl", ctypes.c_void_p),
        ]

    # Set up function prototypes
    kernel32.GetLastError.argtypes = []
    kernel32.GetLastError.restype = wintypes.DWORD

    advapi32.InitializeAcl.argtypes = [
        ctypes.POINTER(Acl),
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    advapi32.InitializeAcl.restype = wintypes.BOOL

    advapi32.AddAccessAllowedAceEx.argtypes = [
        ctypes.POINTER(Acl),
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
    ]
    advapi32.AddAccessAllowedAceEx.restype = wintypes.BOOL

    advapi32.InitializeSecurityDescriptor.argtypes = [
        ctypes.POINTER(SecurityDescriptor),
        wintypes.DWORD,
    ]
    advapi32.InitializeSecurityDescriptor.restype = wintypes.BOOL

    advapi32.SetSecurityDescriptorDacl.argtypes = [
        ctypes.POINTER(SecurityDescriptor),
        wintypes.BOOL,
        ctypes.POINTER(Acl),
        wintypes.BOOL,
    ]
    advapi32.SetSecurityDescriptorDacl.restype = wintypes.BOOL

    advapi32.SetFileSecurityW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(SecurityDescriptor),
    ]
    advapi32.SetFileSecurityW.restype = wintypes.BOOL

    # Declare sid_buffer outside try block so it stays alive for entire function
    sid_buffer: ctypes.Array[ctypes.c_ubyte] | None = None

    try:
        # Get current user's SID
        # CRITICAL: sid_buffer must remain referenced while sid_ptr is used.
        # The pointer is only valid while the underlying buffer exists in memory.
        sid_buffer, sid_ptr, sid_length = _get_current_user_sid_windows()

        # Calculate ACL size
        # ACL header + ACCESS_ALLOWED_ACE (header + mask + SID - 4 bytes for SidStart)
        acl_size = ctypes.sizeof(Acl) + ctypes.sizeof(AccessAllowedAce) + sid_length

        # Allocate and initialize ACL
        acl_buffer = (ctypes.c_ubyte * acl_size)()
        acl = ctypes.cast(ctypes.byref(acl_buffer), ctypes.POINTER(Acl))

        if not advapi32.InitializeAcl(acl, acl_size, acl_revision):
            raise PlatformSecurityError(
                f"InitializeAcl failed: {kernel32.GetLastError()}"
            )

        # Set ACE flags for directory inheritance
        ace_flags = 0
        if is_directory:
            ace_flags = container_inherit_ace | object_inherit_ace

        # Add ACCESS_ALLOWED_ACE for current user with full control
        if not advapi32.AddAccessAllowedAceEx(
            acl,
            acl_revision,
            ace_flags,
            file_all_access,
            sid_ptr,
        ):
            raise PlatformSecurityError(
                f"AddAccessAllowedAceEx failed: {kernel32.GetLastError()}"
            )

        # Initialize security descriptor
        sd = SecurityDescriptor()
        if not advapi32.InitializeSecurityDescriptor(
            ctypes.byref(sd),
            1,  # SECURITY_DESCRIPTOR_REVISION
        ):
            raise PlatformSecurityError(
                f"InitializeSecurityDescriptor failed: {kernel32.GetLastError()}"
            )

        # Set the DACL
        if not advapi32.SetSecurityDescriptorDacl(
            ctypes.byref(sd),
            True,  # DaclPresent
            acl,
            False,  # DaclDefaulted
        ):
            raise PlatformSecurityError(
                f"SetSecurityDescriptorDacl failed: {kernel32.GetLastError()}"
            )

        # Apply security descriptor to file
        # Use PROTECTED_DACL to prevent inheritance from parent
        security_info = dacl_security_information | protected_dacl_security_information

        if not advapi32.SetFileSecurityW(
            str(path),
            security_info,
            ctypes.byref(sd),
        ):
            raise PlatformSecurityError(
                f"SetFileSecurityW failed for {path}: {kernel32.GetLastError()}"
            )

    except PlatformSecurityError:
        raise
    except Exception as e:
        raise PlatformSecurityError(f"Unexpected error setting Windows ACL: {e}") from e
    finally:
        # Explicitly delete SID buffer to clean up memory
        del sid_buffer


def secure_file_permissions(path: Path) -> None:
    """Set secure file permissions (owner read/write only).

    Platform behavior:
    - Unix: Sets mode to 0600 (rw-------)
    - Windows: Sets DACL to allow only current user full control

    Args:
        path: Path to the file.

    Raises:
        PlatformSecurityError: If permissions cannot be set on Windows.
        OSError: If chmod fails on Unix.
    """
    if not path.exists():
        logger.warning("Cannot set permissions on non-existent file: %s", path)
        return

    if sys.platform == "win32":  # pragma: no cover
        try:
            _set_windows_acl(path, is_directory=False)
            logger.debug("Set Windows ACL for file: %s", path)
        except PlatformSecurityError as e:
            # Log error but don't fail - best effort on Windows
            logger.error("Failed to set Windows ACL for %s: %s", path, e)
            raise
    else:
        os.chmod(path, 0o600)
        logger.debug("Set Unix permissions 0600 for file: %s", path)


def secure_directory_permissions(path: Path) -> None:
    """Set secure directory permissions (owner rwx only).

    Platform behavior:
    - Unix: Sets mode to 0700 (rwx------)
    - Windows: Sets DACL to allow only current user full control
               with inheritance for child objects

    Args:
        path: Path to the directory.

    Raises:
        PlatformSecurityError: If permissions cannot be set on Windows.
        OSError: If chmod fails on Unix.
    """
    if not path.exists():
        logger.warning("Cannot set permissions on non-existent directory: %s", path)
        return

    if sys.platform == "win32":  # pragma: no cover
        try:
            _set_windows_acl(path, is_directory=True)
            logger.debug("Set Windows ACL for directory: %s", path)
        except PlatformSecurityError as e:
            # Log error but don't fail - best effort on Windows
            logger.error("Failed to set Windows ACL for %s: %s", path, e)
            raise
    else:
        os.chmod(path, 0o700)
        logger.debug("Set Unix permissions 0700 for directory: %s", path)


def secure_file_permissions_best_effort(path: Path) -> bool:
    """Set secure file permissions, logging errors but not raising.

    Use this variant when ACL failure should not abort the operation.

    Args:
        path: Path to the file.

    Returns:
        True if permissions were set successfully, False otherwise.
    """
    try:
        secure_file_permissions(path)
        return True
    except (PlatformSecurityError, OSError) as e:
        logger.warning("Could not secure file permissions for %s: %s", path, e)
        return False


def secure_directory_permissions_best_effort(path: Path) -> bool:
    """Set secure directory permissions, logging errors but not raising.

    Use this variant when ACL failure should not abort the operation.

    Args:
        path: Path to the directory.

    Returns:
        True if permissions were set successfully, False otherwise.
    """
    try:
        secure_directory_permissions(path)
        return True
    except (PlatformSecurityError, OSError) as e:
        logger.warning("Could not secure directory permissions for %s: %s", path, e)
        return False


def get_platform_security_notes() -> list[str]:
    """Get platform-specific security notes for the current platform.

    Returns:
        List of security considerations for the current platform.
    """
    notes = []

    if sys.platform == "win32":
        notes.extend(
            [
                "Windows: File permissions are enforced via DACL (Access Control Lists).",
                "Windows: Memory cannot be reliably zeroed due to Python's memory model.",
                "Windows: Process memory may be accessible via admin/debug privileges.",
            ]
        )
    elif sys.platform == "darwin":
        notes.extend(
            [
                "macOS: File permissions enforced via standard Unix mode bits.",
                "macOS: Memory cannot be reliably zeroed due to Python's memory model.",
                "macOS: Keychain integration is not used; secrets are file-based.",
            ]
        )
    else:  # Linux and other Unix  # pragma: no cover
        notes.extend(
            [
                "Linux: File permissions enforced via standard Unix mode bits.",
                "Linux: Memory cannot be reliably zeroed due to Python's memory model.",
                "Linux: Consider using encrypted swap or disabling swap for sensitive use.",
            ]
        )

    # Common Python limitations
    notes.extend(
        [
            "Python: Strings are immutable; secure deletion is best-effort only.",
            "Python: GC may delay memory cleanup; explicit wipe attempts are made.",
        ]
    )

    return notes
