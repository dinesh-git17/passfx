"""Import/Export utilities for PassFX vault."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any


class ImportExportError(Exception):
    """Error during import/export operations."""


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
        ImportExportError: If export fails.
    """
    try:
        count = 0

        if fmt == "json":
            export_data = {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "data": data,
            }
            path.write_text(json.dumps(export_data, indent=2))
            count = sum(len(v) for v in data.values())

        elif fmt == "csv":
            count = _export_csv(data, path, include_sensitive)

        else:
            raise ImportExportError(f"Unknown format: {fmt}")

        return count

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

    # Write CSV
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

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
        ImportExportError: If import fails.
    """
    if not path.exists():
        raise ImportExportError(f"File not found: {path}")

    # Auto-detect format
    if fmt is None:
        suffix = path.suffix.lower()
        if suffix == ".json":
            fmt = "json"
        elif suffix == ".csv":
            fmt = "csv"
        else:
            raise ImportExportError(f"Unknown file type: {suffix}")

    try:
        if fmt == "json":
            return _import_json(path)
        if fmt == "csv":
            return _import_csv(path)
        raise ImportExportError(f"Unknown format: {fmt}")

    except ImportExportError:
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
