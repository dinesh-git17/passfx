# Unit tests for import/export operations.
# Validates filesystem safety, path validation, and data integrity during
# serialization/deserialization to prevent data loss and path traversal attacks.

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from passfx.utils.io import (
    ImportExportError,
    PathValidationError,
    export_to_string,
    export_vault,
    import_vault,
    validate_path,
)

if TYPE_CHECKING:
    from collections.abc import Callable


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_vault_data() -> dict[str, list[dict[str, Any]]]:
    """Provide sample vault data for export/import tests."""
    return {
        "emails": [
            {
                "id": "email1",
                "type": "email",
                "label": "Personal Gmail",
                "email": "user@example.com",
                "password": "SecurePass123!",
                "notes": "Primary email account",
                "created_at": "2024-01-01T12:00:00",
            },
            {
                "id": "email2",
                "type": "email",
                "label": "Work Email",
                "email": "work@company.com",
                "password": "WorkPass456@",
                "notes": None,
                "created_at": "2024-01-02T10:30:00",
            },
        ],
        "phones": [
            {
                "id": "phone1",
                "type": "phone",
                "label": "Mobile Banking",
                "phone": "555-1234",
                "password": "1234",
                "notes": "Bank PIN",
                "created_at": "2024-01-03T08:00:00",
            },
        ],
        "cards": [
            {
                "id": "card1",
                "type": "card",
                "label": "Primary Card",
                "card_number": "4111111111111111",
                "expiry": "12/25",
                "cvv": "123",
                "cardholder_name": "John Doe",
                "notes": "Main credit card",
                "created_at": "2024-01-04T14:00:00",
            },
        ],
    }


@pytest.fixture
def empty_vault_data() -> dict[str, list[dict[str, Any]]]:
    """Provide empty vault data structure."""
    return {"emails": [], "phones": [], "cards": []}


# ============================================================================
# Path Validation Tests
# ============================================================================


class TestValidatePathBasic:
    """Tests for basic path validation functionality."""

    def test_validate_path_resolves_relative_path(
        self, mock_home: Path, temp_file: Callable[[str, str], Path]
    ) -> None:
        """Validate that relative paths are resolved to absolute."""
        test_file = temp_file("test.json", "{}")

        # When in the same directory, relative path should work
        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            os.chdir(mock_home)
            validated = validate_path(Path(test_file.name), must_exist=True)
            assert validated.is_absolute()

    def test_validate_path_accepts_absolute_within_home(
        self, mock_home: Path, temp_file: Callable[[str, str], Path]
    ) -> None:
        """Validate that absolute paths within home are accepted."""
        test_file = temp_file("export.json", "{}")

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            validated = validate_path(test_file, must_exist=True)
            assert validated == test_file.resolve()

    def test_validate_path_expands_tilde(self, mock_home: Path) -> None:
        """Validate that ~ is expanded to home directory."""
        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            # Create test directory
            subdir = mock_home / "subdir"
            subdir.mkdir()

            # Use tilde expansion
            tilde_path = Path("~/subdir/test.json")
            with patch.object(Path, "expanduser") as mock_expand:
                mock_expand.return_value = mock_home / "subdir" / "test.json"
                with patch.object(
                    Path, "resolve", return_value=mock_home / "subdir" / "test.json"
                ):
                    # Parent exists check will pass since we made subdir
                    validated = validate_path(tilde_path, must_exist=False)
                    assert validated.is_absolute()


class TestValidatePathSecurityChecks:
    """Tests for path validation security checks."""

    def test_validate_path_rejects_outside_home(self, mock_home: Path) -> None:
        """Validate that paths outside home directory are rejected."""
        outside_home = Path("/tmp/evil/export.json")

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError) as exc_info:
                validate_path(outside_home, must_exist=False)

            assert "within home directory" in str(exc_info.value)

    def test_validate_path_rejects_path_traversal(self, mock_home: Path) -> None:
        """Validate that path traversal attempts are blocked."""
        # Path that tries to escape home directory
        traversal_path = mock_home / ".." / ".." / "etc" / "passwd"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError) as exc_info:
                validate_path(traversal_path, must_exist=False)

            assert "within home directory" in str(exc_info.value)

    def test_validate_path_rejects_symlink_to_outside_home(
        self, mock_home: Path
    ) -> None:
        """Validate that symlinks pointing outside home are rejected.

        Note: Path.resolve() follows symlinks, so the symlink itself isn't detected.
        However, if the symlink target is outside home, the path fails validation.
        This provides defense against symlink attacks that escape the home directory.
        """
        symlink_path = mock_home / "evil_symlink.json"
        try:
            symlink_path.symlink_to("/etc/passwd")
        except OSError:
            pytest.skip("Cannot create symlink (permissions)")

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError) as exc_info:
                validate_path(symlink_path, must_exist=False)

            # The symlink resolves outside home, so it's rejected
            assert "within home directory" in str(exc_info.value)

    def test_validate_path_symlink_within_home_resolves(
        self, mock_home: Path, temp_file: Callable[[str, str], Path]
    ) -> None:
        """Document that symlinks within home resolve and pass validation.

        Note: This is the current behavior. After resolve(), the symlink is
        followed so is_symlink() returns False. Symlinks within home are
        effectively allowed. The security boundary is the home directory check.
        """
        real_file = temp_file("real.json", "{}")
        symlink_path = mock_home / "symlink.json"
        symlink_path.symlink_to(real_file)

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            # Symlink within home resolves successfully
            validated = validate_path(symlink_path, must_exist=True)
            # The validated path is the resolved (real) path
            assert validated == real_file.resolve()

    def test_validate_path_symlink_parent_to_outside_rejected(
        self, mock_home: Path
    ) -> None:
        """Validate that symlink parent directories outside home are rejected."""
        # Create symlink in mock_home pointing to /tmp
        symlink_dir = mock_home / "symlink_to_tmp"
        try:
            symlink_dir.symlink_to("/tmp")
        except OSError:
            pytest.skip("Cannot create symlink (permissions)")

        target_path = symlink_dir / "export.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError) as exc_info:
                validate_path(target_path, must_exist=False)

            # Path resolves outside home
            assert "within home directory" in str(exc_info.value)

    def test_validate_path_rejects_nonexistent_parent(self, mock_home: Path) -> None:
        """Validate that nonexistent parent directories are rejected."""
        target_path = mock_home / "nonexistent" / "export.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError) as exc_info:
                validate_path(target_path, must_exist=False)

            assert "Parent directory does not exist" in str(exc_info.value)

    def test_validate_path_rejects_file_as_parent(
        self, mock_home: Path, temp_file: Callable[[str, str], Path]
    ) -> None:
        """Validate that using a file as parent directory is rejected."""
        temp_file("not_a_dir.txt", "content")
        # Try to use file as if it were a directory
        target_path = mock_home / "not_a_dir.txt" / "export.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError) as exc_info:
                validate_path(target_path, must_exist=False)

            # Will fail because not_a_dir.txt is a file, not a directory
            error_msg = str(exc_info.value)
            assert (
                "not a directory" in error_msg or "does not exist" in error_msg.lower()
            )


class TestValidatePathMustExist:
    """Tests for path validation with must_exist flag."""

    def test_validate_path_must_exist_accepts_existing_file(
        self, mock_home: Path, temp_file: Callable[[str, str], Path]
    ) -> None:
        """Validate that existing files pass when must_exist=True."""
        test_file = temp_file("existing.json", '{"data": "test"}')

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            validated = validate_path(test_file, must_exist=True)
            assert validated.exists()
            assert validated.is_file()

    def test_validate_path_must_exist_rejects_nonexistent(
        self, mock_home: Path
    ) -> None:
        """Validate that nonexistent files are rejected when must_exist=True."""
        nonexistent = mock_home / "does_not_exist.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError) as exc_info:
                validate_path(nonexistent, must_exist=True)

            assert "File not found" in str(exc_info.value)

    def test_validate_path_must_exist_rejects_directory(self, mock_home: Path) -> None:
        """Validate that directories are rejected when must_exist=True."""
        subdir = mock_home / "subdir"
        subdir.mkdir()

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError) as exc_info:
                validate_path(subdir, must_exist=True)

            assert "not a file" in str(exc_info.value)


class TestValidatePathEdgeCases:
    """Tests for edge cases in path validation."""

    def test_validate_path_handles_special_characters(self, mock_home: Path) -> None:
        """Validate handling of special characters in filenames."""
        subdir = mock_home / "sub dir with spaces"
        subdir.mkdir()
        target = subdir / "file-with_special.chars!.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            validated = validate_path(target, must_exist=False)
            assert "special.chars" in str(validated)

    def test_validate_path_handles_unicode(self, mock_home: Path) -> None:
        """Validate handling of unicode characters in paths."""
        subdir = mock_home / "フォルダ"
        subdir.mkdir()
        target = subdir / "файл.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            validated = validate_path(target, must_exist=False)
            assert validated.is_absolute()

    def test_validate_path_normalizes_multiple_slashes(
        self, mock_home: Path, temp_file: Callable[[str, str], Path]
    ) -> None:
        """Validate that multiple slashes are normalized."""
        test_file = temp_file("test.json", "{}")
        # Create path with multiple slashes
        path_with_slashes = Path(str(mock_home) + "///" + test_file.name)

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            validated = validate_path(path_with_slashes, must_exist=True)
            assert "///" not in str(validated)


# ============================================================================
# Export Tests
# ============================================================================


class TestExportVaultJSON:
    """Tests for JSON export functionality."""

    def test_export_vault_json_creates_file(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that JSON export creates a file."""
        export_path = mock_home / "export.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            count = export_vault(sample_vault_data, export_path, fmt="json")

            assert export_path.exists()
            assert count == 4  # 2 emails + 1 phone + 1 card

    def test_export_vault_json_contains_version(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that JSON export contains version metadata."""
        export_path = mock_home / "export.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(sample_vault_data, export_path, fmt="json")

            content = json.loads(export_path.read_text())
            assert "version" in content
            assert content["version"] == "1.0"

    def test_export_vault_json_contains_timestamp(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that JSON export contains export timestamp."""
        export_path = mock_home / "export.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(sample_vault_data, export_path, fmt="json")

            content = json.loads(export_path.read_text())
            assert "exported_at" in content
            # Verify ISO format
            assert "T" in content["exported_at"]

    def test_export_vault_json_preserves_all_data(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that JSON export preserves all credential data."""
        export_path = mock_home / "export.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(sample_vault_data, export_path, fmt="json")

            content = json.loads(export_path.read_text())
            data = content["data"]

            assert len(data["emails"]) == 2
            assert len(data["phones"]) == 1
            assert len(data["cards"]) == 1

            # Verify specific fields
            assert data["emails"][0]["email"] == "user@example.com"
            assert data["emails"][0]["password"] == "SecurePass123!"
            assert data["cards"][0]["cvv"] == "123"

    def test_export_vault_json_empty_data(
        self,
        mock_home: Path,
        empty_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that JSON export handles empty vault."""
        export_path = mock_home / "export.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            count = export_vault(empty_vault_data, export_path, fmt="json")

            assert export_path.exists()
            assert count == 0

            content = json.loads(export_path.read_text())
            assert content["data"]["emails"] == []


class TestExportVaultCSV:
    """Tests for CSV export functionality."""

    def test_export_vault_csv_creates_file(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that CSV export creates a file."""
        export_path = mock_home / "export.csv"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            count = export_vault(sample_vault_data, export_path, fmt="csv")

            assert export_path.exists()
            assert count == 4

    def test_export_vault_csv_has_headers(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that CSV export includes headers."""
        export_path = mock_home / "export.csv"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(sample_vault_data, export_path, fmt="csv")

            with export_path.open() as f:
                reader = csv.reader(f)
                headers = next(reader)

            assert "type" in headers
            assert "label" in headers
            assert "email" in headers
            assert "password" in headers

    def test_export_vault_csv_excludes_sensitive_when_requested(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that CSV export can exclude sensitive fields."""
        export_path = mock_home / "export.csv"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(
                sample_vault_data,
                export_path,
                fmt="csv",
                include_sensitive=False,
            )

            with export_path.open() as f:
                reader = csv.reader(f)
                headers = next(reader)

            # Password and CVV should be excluded from headers
            assert "password" not in headers
            assert "cvv" not in headers

    def test_export_vault_csv_includes_type_column(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that CSV export includes type column for each entry."""
        export_path = mock_home / "export.csv"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(sample_vault_data, export_path, fmt="csv")

            with export_path.open() as f:
                reader = csv.DictReader(f)
                types = [row["type"] for row in reader]

            assert "email" in types
            assert "phone" in types
            assert "card" in types


class TestExportVaultPermissions:
    """Tests for file permission enforcement during export."""

    def test_export_vault_sets_secure_permissions(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
        assert_file_permissions: Callable[[Path, int], None],
    ) -> None:
        """Validate that exported files have 0600 permissions."""
        export_path = mock_home / "secure_export.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(sample_vault_data, export_path, fmt="json")

            assert_file_permissions(export_path, 0o600)

    def test_export_vault_csv_sets_secure_permissions(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
        assert_file_permissions: Callable[[Path, int], None],
    ) -> None:
        """Validate that CSV exports have 0600 permissions."""
        export_path = mock_home / "secure_export.csv"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(sample_vault_data, export_path, fmt="csv")

            assert_file_permissions(export_path, 0o600)


class TestExportVaultErrors:
    """Tests for export error handling."""

    def test_export_vault_rejects_unknown_format(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that unknown formats are rejected."""
        export_path = mock_home / "export.xml"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(ImportExportError) as exc_info:
                export_vault(sample_vault_data, export_path, fmt="xml")

            assert "Unknown format" in str(exc_info.value)

    def test_export_vault_validates_path(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that export validates path before writing."""
        outside_path = Path("/tmp/evil/export.json")

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError):
                export_vault(sample_vault_data, outside_path, fmt="json")


# ============================================================================
# Import Tests
# ============================================================================


class TestImportVaultJSON:
    """Tests for JSON import functionality."""

    def test_import_vault_json_reads_data(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that JSON import reads data correctly."""
        export_content = {
            "version": "1.0",
            "exported_at": "2024-01-01T00:00:00",
            "data": sample_vault_data,
        }
        json_file = temp_file("import.json", json.dumps(export_content))

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            data, count = import_vault(json_file, fmt="json")

            assert count == 4
            assert len(data["emails"]) == 2
            assert len(data["phones"]) == 1
            assert len(data["cards"]) == 1

    def test_import_vault_json_handles_raw_data(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that JSON import handles raw data without wrapper."""
        json_file = temp_file("raw.json", json.dumps(sample_vault_data))

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            data, count = import_vault(json_file, fmt="json")

            assert count == 4
            assert data["emails"][0]["email"] == "user@example.com"

    def test_import_vault_json_autodetects_format(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that import auto-detects JSON format from extension."""
        export_content = {"version": "1.0", "data": sample_vault_data}
        json_file = temp_file("autodetect.json", json.dumps(export_content))

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            data, count = import_vault(json_file)  # No fmt specified

            assert count == 4

    def test_import_vault_json_preserves_all_fields(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that JSON import preserves all credential fields."""
        export_content = {"data": sample_vault_data}
        json_file = temp_file("full.json", json.dumps(export_content))

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            data, _ = import_vault(json_file, fmt="json")

            # Verify email fields
            email = data["emails"][0]
            assert email["password"] == "SecurePass123!"
            assert email["notes"] == "Primary email account"

            # Verify card fields
            card = data["cards"][0]
            assert card["cvv"] == "123"
            assert card["cardholder_name"] == "John Doe"


class TestImportVaultCSV:
    """Tests for CSV import functionality."""

    def test_import_vault_csv_reads_data(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
    ) -> None:
        """Validate that CSV import reads data correctly."""
        csv_content = (
            "type,label,email,phone,password,card_number,expiry,cvv,cardholder_name,notes\n"
            "email,Gmail,user@test.com,,pass123,,,,,,Test note\n"
            "phone,Banking,,555-0123,1234,,,,,\n"
            "card,Visa,,,,4111111111111111,12/25,999,John Doe,\n"
        )
        csv_file = temp_file("import.csv", csv_content)

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            data, count = import_vault(csv_file, fmt="csv")

            assert count == 3
            assert len(data["emails"]) == 1
            assert len(data["phones"]) == 1
            assert len(data["cards"]) == 1

    def test_import_vault_csv_autodetects_format(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
    ) -> None:
        """Validate that import auto-detects CSV format from extension."""
        csv_content = "type,label,email,password\nemail,Test,test@test.com,pass\n"
        csv_file = temp_file("autodetect.csv", csv_content)

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            data, count = import_vault(csv_file)  # No fmt specified

            assert count == 1
            assert data["emails"][0]["email"] == "test@test.com"

    def test_import_vault_csv_handles_missing_type(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
    ) -> None:
        """Validate that CSV import defaults to email type when missing."""
        csv_content = "label,email,password\nTest,test@test.com,pass\n"
        csv_file = temp_file("notype.csv", csv_content)

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            data, count = import_vault(csv_file, fmt="csv")

            assert count == 1
            assert len(data["emails"]) == 1

    def test_import_vault_csv_handles_empty_values(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
    ) -> None:
        """Validate that CSV import handles empty values gracefully."""
        csv_content = "type,label,email,password,notes\nemail,Test,test@test.com,,\n"
        csv_file = temp_file("empty_values.csv", csv_content)

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            data, count = import_vault(csv_file, fmt="csv")

            assert count == 1
            assert data["emails"][0]["password"] == ""


class TestImportVaultErrors:
    """Tests for import error handling."""

    def test_import_vault_rejects_nonexistent_file(self, mock_home: Path) -> None:
        """Validate that import rejects nonexistent files."""
        nonexistent = mock_home / "does_not_exist.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError) as exc_info:
                import_vault(nonexistent, fmt="json")

            assert "File not found" in str(exc_info.value)

    def test_import_vault_rejects_unknown_extension(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
    ) -> None:
        """Validate that import rejects unknown file extensions."""
        xml_file = temp_file("data.xml", "<data></data>")

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(ImportExportError) as exc_info:
                import_vault(xml_file)  # Auto-detect should fail

            assert "Unknown file type" in str(exc_info.value)

    def test_import_vault_rejects_invalid_json(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
    ) -> None:
        """Validate that import rejects malformed JSON."""
        bad_json = temp_file("bad.json", "{invalid json content}")

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(ImportExportError) as exc_info:
                import_vault(bad_json, fmt="json")

            assert "Import failed" in str(exc_info.value)

    def test_import_vault_rejects_invalid_json_structure(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
    ) -> None:
        """Validate that import rejects JSON with invalid structure."""
        # JSON that is valid but wrong structure (array instead of object)
        bad_structure = temp_file("array.json", '["email1", "email2"]')

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(ImportExportError) as exc_info:
                import_vault(bad_structure, fmt="json")

            assert "Invalid JSON structure" in str(exc_info.value)

    def test_import_vault_rejects_unknown_format_explicit(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
    ) -> None:
        """Validate that import rejects explicitly unknown formats."""
        json_file = temp_file("data.json", "{}")

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(ImportExportError) as exc_info:
                import_vault(json_file, fmt="yaml")

            assert "Unknown format" in str(exc_info.value)


# ============================================================================
# Round-Trip Tests
# ============================================================================


class TestExportImportRoundTrip:
    """Tests for export/import round-trip data integrity."""

    def test_json_roundtrip_preserves_data(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that JSON export->import preserves all data."""
        export_path = mock_home / "roundtrip.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(sample_vault_data, export_path, fmt="json")
            imported_data, count = import_vault(export_path, fmt="json")

            assert count == 4

            # Verify all credential types preserved
            assert len(imported_data["emails"]) == len(sample_vault_data["emails"])
            assert len(imported_data["phones"]) == len(sample_vault_data["phones"])
            assert len(imported_data["cards"]) == len(sample_vault_data["cards"])

            # Verify specific data
            orig_email = sample_vault_data["emails"][0]
            imported_email = imported_data["emails"][0]
            assert imported_email["email"] == orig_email["email"]
            assert imported_email["password"] == orig_email["password"]

    def test_csv_roundtrip_preserves_core_data(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that CSV export->import preserves core data."""
        export_path = mock_home / "roundtrip.csv"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(sample_vault_data, export_path, fmt="csv")
            imported_data, count = import_vault(export_path, fmt="csv")

            assert count == 4

            # Verify credential counts
            assert len(imported_data["emails"]) == 2
            assert len(imported_data["phones"]) == 1
            assert len(imported_data["cards"]) == 1

    def test_empty_vault_roundtrip(
        self,
        mock_home: Path,
        empty_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that empty vault survives round-trip."""
        export_path = mock_home / "empty.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(empty_vault_data, export_path, fmt="json")
            imported_data, count = import_vault(export_path, fmt="json")

            assert count == 0
            assert imported_data["emails"] == []
            assert imported_data["phones"] == []
            assert imported_data["cards"] == []


# ============================================================================
# Export to String Tests
# ============================================================================


class TestExportToString:
    """Tests for string export functionality."""

    def test_export_to_string_json(
        self,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate JSON string export."""
        result = export_to_string(sample_vault_data, fmt="json")

        parsed = json.loads(result)
        assert "version" in parsed
        assert "exported_at" in parsed
        assert "data" in parsed
        assert len(parsed["data"]["emails"]) == 2

    def test_export_to_string_csv(
        self,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate CSV string export."""
        result = export_to_string(sample_vault_data, fmt="csv")

        lines = result.strip().split("\n")
        assert len(lines) == 5  # Header + 4 data rows

        # Verify header
        headers = lines[0].split(",")
        assert "type" in headers
        assert "email" in headers

    def test_export_to_string_rejects_unknown_format(
        self,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that unknown formats are rejected."""
        with pytest.raises(ImportExportError) as exc_info:
            export_to_string(sample_vault_data, fmt="yaml")

        assert "Unknown format" in str(exc_info.value)


# ============================================================================
# Data Integrity Tests
# ============================================================================


class TestDataIntegrity:
    """Tests for data integrity during export/import."""

    def test_special_characters_preserved_json(
        self,
        mock_home: Path,
    ) -> None:
        """Validate that special characters are preserved in JSON."""
        data = {
            "emails": [
                {
                    "label": "Test <>&\"'",
                    "email": "test@test.com",
                    "password": "p@ss<w0rd>&\"'",
                    "notes": "Notes with\nnewlines\tand\ttabs",
                }
            ],
            "phones": [],
            "cards": [],
        }
        export_path = mock_home / "special.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(data, export_path, fmt="json")
            imported, _ = import_vault(export_path, fmt="json")

            assert imported["emails"][0]["label"] == "Test <>&\"'"
            assert imported["emails"][0]["password"] == "p@ss<w0rd>&\"'"
            assert "\n" in imported["emails"][0]["notes"]

    def test_unicode_preserved(
        self,
        mock_home: Path,
    ) -> None:
        """Validate that unicode characters are preserved."""
        data = {
            "emails": [
                {
                    "label": "日本語テスト",
                    "email": "user@例え.jp",
                    "password": "密码123",
                    "notes": "Emoji: 🔐🔑",
                }
            ],
            "phones": [],
            "cards": [],
        }
        export_path = mock_home / "unicode.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(data, export_path, fmt="json")
            imported, _ = import_vault(export_path, fmt="json")

            assert imported["emails"][0]["label"] == "日本語テスト"
            assert imported["emails"][0]["password"] == "密码123"
            assert "🔐" in imported["emails"][0]["notes"]

    def test_large_data_handled(
        self,
        mock_home: Path,
    ) -> None:
        """Validate that large datasets are handled correctly."""
        # Create 100 credentials
        data = {
            "emails": [
                {
                    "label": f"Email {i}",
                    "email": f"user{i}@test.com",
                    "password": f"pass{i}",
                    "notes": f"Note {i}" * 100,  # Long notes
                }
                for i in range(100)
            ],
            "phones": [],
            "cards": [],
        }
        export_path = mock_home / "large.json"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            count = export_vault(data, export_path, fmt="json")
            imported, imported_count = import_vault(export_path, fmt="json")

            assert count == 100
            assert imported_count == 100
            assert len(imported["emails"]) == 100


# ============================================================================
# Overwrite Prevention Tests
# ============================================================================


class TestOverwriteBehavior:
    """Tests for file overwrite behavior."""

    def test_export_overwrites_existing_file(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that export overwrites existing files."""
        # Create existing file with different content
        existing = temp_file("existing.json", '{"old": "data"}')
        original_content = existing.read_text()

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(sample_vault_data, existing, fmt="json")

            new_content = existing.read_text()
            assert new_content != original_content
            assert "emails" in new_content

    def test_export_maintains_secure_permissions_after_overwrite(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
        sample_vault_data: dict[str, list[dict[str, Any]]],
        assert_file_permissions: Callable[[Path, int], None],
    ) -> None:
        """Validate permissions remain secure after overwrite."""
        existing = temp_file("existing.json", '{"old": "data"}')
        # Make it world-readable initially
        os.chmod(existing, 0o644)

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            export_vault(sample_vault_data, existing, fmt="json")

            # Should be secured after export
            assert_file_permissions(existing, 0o600)


# ============================================================================
# Path Traversal Attack Prevention Tests
# ============================================================================


class TestPathTraversalPrevention:
    """Tests to ensure path traversal attacks are prevented."""

    def test_double_dot_in_filename_rejected(self, mock_home: Path) -> None:
        """Validate that .. in filename is handled safely."""
        # Create a valid parent directory first
        attack_path = mock_home / ".." / ".." / "etc" / "passwd"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError):
                validate_path(attack_path, must_exist=False)

    def test_encoded_traversal_rejected(self, mock_home: Path) -> None:
        """Validate that URL-encoded traversal is blocked."""
        # After URL decoding, this would be ../etc/passwd
        # Path.resolve() should normalize this
        subdir = mock_home / "subdir"
        subdir.mkdir()

        # This path, when resolved, should escape home
        attack_path = subdir / ".." / ".." / ".." / "etc" / "passwd"

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError):
                validate_path(attack_path, must_exist=False)

    def test_symlink_attack_on_import_rejected(
        self,
        mock_home: Path,
    ) -> None:
        """Validate that symlink attacks during import are rejected.

        Symlinks pointing outside home are rejected because the resolved path
        falls outside the home directory boundary.
        """
        # Create a symlink pointing to /etc/passwd
        symlink = mock_home / "evil_link.json"
        try:
            symlink.symlink_to("/etc/passwd")
        except OSError:
            pytest.skip("Cannot create symlink (permissions)")

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError) as exc_info:
                import_vault(symlink, fmt="json")

            # Rejected because resolved path is outside home directory
            assert "within home directory" in str(exc_info.value)

    def test_symlink_attack_on_export_rejected(
        self,
        mock_home: Path,
        sample_vault_data: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Validate that symlink attacks during export are rejected.

        Symlinks pointing outside home are rejected because the resolved path
        falls outside the home directory boundary.
        """
        symlink = mock_home / "evil_export.json"
        try:
            symlink.symlink_to("/tmp/captured_secrets.json")
        except OSError:
            pytest.skip("Cannot create symlink (permissions)")

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            with pytest.raises(PathValidationError) as exc_info:
                export_vault(sample_vault_data, symlink, fmt="json")

            # Rejected because resolved path is outside home directory
            assert "within home directory" in str(exc_info.value)


# ============================================================================
# Import Defaults Tests
# ============================================================================


class TestImportDefaults:
    """Tests for default values during import."""

    def test_import_csv_default_label(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
    ) -> None:
        """Validate that CSV import provides default label."""
        csv_content = "type,email,password\nemail,test@test.com,pass\n"
        csv_file = temp_file("no_label.csv", csv_content)

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            data, _ = import_vault(csv_file, fmt="csv")

            assert data["emails"][0]["label"] == "Imported"

    def test_import_json_missing_keys_filled(
        self,
        mock_home: Path,
        temp_file: Callable[[str, str], Path],
    ) -> None:
        """Validate that missing keys are filled with empty lists."""
        # JSON with only emails, no phones or cards keys
        partial_data = {"emails": [{"label": "Test", "email": "t@t.com"}]}
        json_file = temp_file("partial.json", json.dumps(partial_data))

        with patch("passfx.utils.io.Path.home", return_value=mock_home):
            data, _ = import_vault(json_file, fmt="json")

            assert "phones" in data
            assert "cards" in data
            assert data["phones"] == []
            assert data["cards"] == []
