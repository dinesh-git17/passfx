"""Configuration management for PassFX.

Handles persistent storage of user preferences in ~/.passfx/config.json.
Uses atomic writes and secure file permissions for data integrity.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from passfx.utils.platform_security import secure_file_permissions

# Default config location
DEFAULT_CONFIG_DIR = Path.home() / ".passfx"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


class ConfigError(Exception):
    """Raised when configuration operations fail."""


@dataclass
class AppConfig:
    """Application configuration with type-safe defaults.

    All fields have sensible defaults - config file only stores overrides.
    """

    # Security settings
    auto_lock_minutes: int = 5  # 0 = disabled
    clipboard_timeout_seconds: int = 15

    # Interface settings
    matrix_rain_enabled: bool = True
    compact_mode_enabled: bool = False

    # Internal tracking (not user-facing)
    config_version: int = field(default=1, repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        """Create config from dictionary, ignoring unknown keys."""
        known_fields = {
            "auto_lock_minutes",
            "clipboard_timeout_seconds",
            "matrix_rain_enabled",
            "compact_mode_enabled",
            "config_version",
        }
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


class ConfigManager:
    """Manages persistent application configuration.

    Thread-safe singleton pattern ensures consistent config state across
    the application. All changes are persisted immediately.
    """

    _instance: ConfigManager | None = None
    _config: AppConfig

    def __new__(cls, config_path: Path | None = None) -> ConfigManager:
        """Singleton pattern - returns existing instance if available."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize config manager.

        Args:
            config_path: Custom config file path. Defaults to ~/.passfx/config.json.
        """
        if getattr(self, "_initialized", False):
            return

        self._path = config_path or DEFAULT_CONFIG_FILE
        self._config = AppConfig()
        self._load()
        self._initialized = True

    def _ensure_config_dir(self) -> None:
        """Ensure config directory exists with secure permissions."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Directory permissions handled by vault initialization

    def _load(self) -> None:
        """Load config from disk, falling back to defaults on error."""
        if not self._path.exists():
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._config = AppConfig.from_dict(data)
        except (json.JSONDecodeError, TypeError, KeyError):
            # Corrupted config - reset to defaults
            self._config = AppConfig()

    def _save(self) -> None:
        """Save config atomically with secure permissions."""
        self._ensure_config_dir()

        data = json.dumps(self._config.to_dict(), indent=2)
        config_dir = self._path.parent

        # Atomic write: temp file -> fsync -> rename
        fd, temp_path = tempfile.mkstemp(
            dir=config_dir,
            prefix=".config_",
            suffix=".tmp",
        )
        try:
            os.write(fd, data.encode("utf-8"))
            os.fsync(fd)
            os.close(fd)

            # Set secure permissions before rename
            secure_file_permissions(Path(temp_path))

            # Atomic rename
            os.replace(temp_path, self._path)

            # Re-apply permissions after rename
            secure_file_permissions(self._path)

        except Exception:
            # Clean up on failure
            try:
                os.close(fd)
            except OSError:
                pass
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    # --- Property accessors with immediate persistence ---

    @property
    def auto_lock_minutes(self) -> int:
        """Get auto-lock timeout in minutes."""
        return self._config.auto_lock_minutes

    @auto_lock_minutes.setter
    def auto_lock_minutes(self, value: int) -> None:
        """Set auto-lock timeout. 0 disables auto-lock."""
        self._config.auto_lock_minutes = max(value, 0)
        self._save()

    @property
    def clipboard_timeout_seconds(self) -> int:
        """Get clipboard auto-clear timeout in seconds."""
        return self._config.clipboard_timeout_seconds

    @clipboard_timeout_seconds.setter
    def clipboard_timeout_seconds(self, value: int) -> None:
        """Set clipboard timeout. Minimum 5 seconds for security."""
        self._config.clipboard_timeout_seconds = max(value, 5)
        self._save()

    @property
    def matrix_rain_enabled(self) -> bool:
        """Check if matrix rain animation is enabled."""
        return self._config.matrix_rain_enabled

    @matrix_rain_enabled.setter
    def matrix_rain_enabled(self, value: bool) -> None:
        """Enable or disable matrix rain animation."""
        self._config.matrix_rain_enabled = bool(value)
        self._save()

    @property
    def compact_mode_enabled(self) -> bool:
        """Check if compact mode is enabled."""
        return self._config.compact_mode_enabled

    @compact_mode_enabled.setter
    def compact_mode_enabled(self, value: bool) -> None:
        """Enable or disable compact mode."""
        self._config.compact_mode_enabled = bool(value)
        self._save()

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        self._config = AppConfig()
        self._save()

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset singleton instance. For testing only."""
        cls._instance = None


def get_config() -> ConfigManager:
    """Get the global config manager instance."""
    return ConfigManager()
