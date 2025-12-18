"""Import/Export utilities for PassFX vault."""

from __future__ import annotations

import csv
import json
import os
import stat
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

# Secure file permissions: owner read/write only (0600)
_SECURE_FILE_MODE = stat.S_IRUSR | stat.S_IWUSR


class ImportExportError(Exception):
    """Error during import/export operations."""


class PathValidationError(ImportExportError):
    """Raised when path validation fails for security reasons."""


def validate_path(path: Path, must_exist: bool = False) -> Path:
    """Validate and resolve a path for import/export operations.

    Security checks performed:
    1. Path is resolved to absolute form
    2. Path must be within user's home directory
    3. Path must not be a symlink (prevents symlink attacks)
    4. Parent directory must exist and not be a symlink

    Args:
        path: Path to validate.
        must_exist: If True, file must already exist.

    Returns:
        Resolved absolute path.

    Raises:
        PathValidationError: If path fails security validation.
    """
    # Resolve path to absolute, normalized form
    try:
        resolved = path.expanduser().resolve()
    except (OSError, ValueError) as e:
        raise PathValidationError(f"Invalid path: {e}") from e

    # Get user home directory
    home_dir = Path.home().resolve()

    # Verify path is within home directory
    try:
        resolved.relative_to(home_dir)
    except ValueError as exc:
        raise PathValidationError(
            f"Path must be within home directory ({home_dir}). " f"Got: {resolved}"
        ) from exc

    # Check if path is a symlink (before it exists for export, or if it exists)
    if resolved.is_symlink():
        raise PathValidationError(
            f"Path cannot be a symlink for security reasons: {resolved}"
        )

    # For import, file must exist
    if must_exist:
        if not resolved.exists():
            raise PathValidationError(f"File not found: {resolved}")
        if not resolved.is_file():
            raise PathValidationError(f"Path is not a file: {resolved}")

    # For export, parent directory must exist and not be a symlink
    parent = resolved.parent
    if not parent.exists():
        raise PathValidationError(f"Parent directory does not exist: {parent}")
    if parent.is_symlink():
        raise PathValidationError(f"Parent directory cannot be a symlink: {parent}")
    if not parent.is_dir():
        raise PathValidationError(f"Parent path is not a directory: {parent}")

    return resolved


def _secure_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write text to a file with secure permissions (0600).

    Creates the file with owner-only read/write permissions to prevent
    other users from reading exported secrets.
    """
    # Open with O_CREAT | O_WRONLY | O_TRUNC, mode 0600
    fd = os.open(str(path), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, _SECURE_FILE_MODE)
    with os.fdopen(fd, "w", encoding=encoding) as f:
        f.write(content)
    # Ensure permissions are correct even if umask was permissive
    os.chmod(str(path), _SECURE_FILE_MODE)


def export_vault(
    data: dict[str, list[dict[str, Any]]],
    path: Path,
    fmt: str = "json",
    include_sensitive: bool = True,
) -> int:
    """Export vault data to a file.

    Args:
        data: Vault data with 'emails', 'phones', 'cards' keys.
        path: Output file path.
        fmt: Export format ('json' or 'csv').
        include_sensitive: Whether to include passwords/CVV (CSV only).

    Returns:
        Number of entries exported.

    Raises:
        PathValidationError: If path fails security validation.
        ImportExportError: If export fails.
    """
    # Validate path before export
    validated_path = validate_path(path, must_exist=False)

    try:
        count = 0

        if fmt == "json":
            export_data = {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "data": data,
            }
            _secure_write_text(validated_path, json.dumps(export_data, indent=2))
            count = sum(len(v) for v in data.values())

        elif fmt == "csv":
            count = _export_csv(data, validated_path, include_sensitive)

        else:
            raise ImportExportError(f"Unknown format: {fmt}")

        return count

    except PathValidationError:
        raise
    except Exception as e:
        raise ImportExportError(f"Export failed: {e}") from e


def _export_csv(
    data: dict[str, list[dict[str, Any]]],
    path: Path,
    include_sensitive: bool,
) -> int:
    """Export vault data to CSV format.

    CSV format combines all credential types with a 'type' column.

    Args:
        data: Vault data.
        path: Output path.
        include_sensitive: Include passwords/CVV.

    Returns:
        Number of entries exported.
    """
    count = 0
    rows = []

    # Headers for combined CSV
    headers = [
        "type",
        "label",
        "email",
        "phone",
        "password",
        "card_number",
        "expiry",
        "cvv",
        "cardholder_name",
        "notes",
        "created_at",
    ]

    if not include_sensitive:
        headers = [h for h in headers if h not in ("password", "cvv")]

    # Process emails
    for item in data.get("emails", []):
        row = {
            "type": "email",
            "label": item.get("label", ""),
            "email": item.get("email", ""),
            "phone": "",
            "password": item.get("password", "") if include_sensitive else "***",
            "card_number": "",
            "expiry": "",
            "cvv": "",
            "cardholder_name": "",
            "notes": item.get("notes", "") or "",
            "created_at": item.get("created_at", ""),
        }
        if not include_sensitive:
            row.pop("password", None)
            row.pop("cvv", None)
        rows.append(row)
        count += 1

    # Process phones
    for item in data.get("phones", []):
        row = {
            "type": "phone",
            "label": item.get("label", ""),
            "email": "",
            "phone": item.get("phone", ""),
            "password": item.get("password", "") if include_sensitive else "***",
            "card_number": "",
            "expiry": "",
            "cvv": "",
            "cardholder_name": "",
            "notes": item.get("notes", "") or "",
            "created_at": item.get("created_at", ""),
        }
        if not include_sensitive:
            row.pop("password", None)
            row.pop("cvv", None)
        rows.append(row)
        count += 1

    # Process cards
    for item in data.get("cards", []):
        row = {
            "type": "card",
            "label": item.get("label", ""),
            "email": "",
            "phone": "",
            "password": "",
            "card_number": item.get("card_number", ""),
            "expiry": item.get("expiry", ""),
            "cvv": item.get("cvv", "") if include_sensitive else "***",
            "cardholder_name": item.get("cardholder_name", ""),
            "notes": item.get("notes", "") or "",
            "created_at": item.get("created_at", ""),
        }
        if not include_sensitive:
            row.pop("password", None)
            row.pop("cvv", None)
        rows.append(row)
        count += 1

    # Write CSV with secure permissions (0600)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    _secure_write_text(path, output.getvalue())

    return count


def import_vault(
    path: Path,
    fmt: str | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], int]:
    """Import vault data from a file.

    Args:
        path: Input file path.
        fmt: Import format ('json' or 'csv'). Auto-detected if None.

    Returns:
        Tuple of (data dict, count of entries).

    Raises:
        PathValidationError: If path fails security validation.
        ImportExportError: If import fails.
    """
    # Validate path before import
    validated_path = validate_path(path, must_exist=True)

    # Auto-detect format
    if fmt is None:
        suffix = validated_path.suffix.lower()
        if suffix == ".json":
            fmt = "json"
        elif suffix == ".csv":
            fmt = "csv"
        else:
            raise ImportExportError(f"Unknown file type: {suffix}")

    try:
        if fmt == "json":
            return _import_json(validated_path)
        if fmt == "csv":
            return _import_csv(validated_path)
        raise ImportExportError(f"Unknown format: {fmt}")

    except (ImportExportError, PathValidationError):
        raise
    except Exception as e:
        raise ImportExportError(f"Import failed: {e}") from e


def _import_json(path: Path) -> tuple[dict[str, list[dict[str, Any]]], int]:
    """Import from JSON format.

    Args:
        path: JSON file path.

    Returns:
        Tuple of (data, count).
    """
    content = path.read_text(encoding="utf-8")
    parsed = json.loads(content)

    # Handle export format with 'data' key
    if "data" in parsed:
        data = parsed["data"]
    else:
        data = parsed

    # Validate structure
    if not isinstance(data, dict):
        raise ImportExportError("Invalid JSON structure")

    # Ensure required keys
    result: dict[str, list[dict[str, Any]]] = {
        "emails": data.get("emails", []),
        "phones": data.get("phones", []),
        "cards": data.get("cards", []),
    }

    count = sum(len(v) for v in result.values())
    return result, count


def _import_csv(path: Path) -> tuple[dict[str, list[dict[str, Any]]], int]:
    """Import from CSV format.

    Args:
        path: CSV file path.

    Returns:
        Tuple of (data, count).
    """
    result: dict[str, list[dict[str, Any]]] = {
        "emails": [],
        "phones": [],
        "cards": [],
    }
    count = 0

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            entry_type = row.get("type", "email").lower()

            if entry_type == "email":
                entry = {
                    "type": "email",
                    "label": row.get("label", "Imported"),
                    "email": row.get("email", ""),
                    "password": row.get("password", ""),
                    "notes": row.get("notes"),
                }
                result["emails"].append(entry)
                count += 1

            elif entry_type == "phone":
                entry = {
                    "type": "phone",
                    "label": row.get("label", "Imported"),
                    "phone": row.get("phone", ""),
                    "password": row.get("password", ""),
                    "notes": row.get("notes"),
                }
                result["phones"].append(entry)
                count += 1

            elif entry_type == "card":
                entry = {
                    "type": "card",
                    "label": row.get("label", "Imported"),
                    "card_number": row.get("card_number", ""),
                    "expiry": row.get("expiry", ""),
                    "cvv": row.get("cvv", ""),
                    "cardholder_name": row.get("cardholder_name", ""),
                    "notes": row.get("notes"),
                }
                result["cards"].append(entry)
                count += 1

    return result, count


def export_to_string(
    data: dict[str, list[dict[str, Any]]],
    fmt: str = "json",
) -> str:
    """Export vault data to a string.

    Args:
        data: Vault data.
        fmt: Export format.

    Returns:
        Exported data as string.
    """
    if fmt == "json":
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "data": data,
        }
        return json.dumps(export_data, indent=2)

    if fmt == "csv":
        output = StringIO()
        headers = [
            "type",
            "label",
            "email",
            "phone",
            "password",
            "card_number",
            "expiry",
            "cvv",
            "cardholder_name",
            "notes",
        ]
        writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()

        for item in data.get("emails", []):
            writer.writerow({"type": "email", **item})
        for item in data.get("phones", []):
            writer.writerow({"type": "phone", **item})
        for item in data.get("cards", []):
            writer.writerow({"type": "card", **item})

        return output.getvalue()

    raise ImportExportError(f"Unknown format: {fmt}")
