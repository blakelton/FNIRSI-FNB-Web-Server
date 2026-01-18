"""Settings Manager - Persist and load configuration."""

import json
from pathlib import Path
from typing import Any, Dict, Tuple


class SettingsManager:
    """Manages persistence and loading of settings and alert configurations."""

    DEFAULT_SETTINGS = {
        'voltage_offset': 0.0,
        'current_offset': 0.0,
        'voltage_scale': 1.0,
        'current_scale': 1.0,
        'theme': 'dark',
        'chart_points': 150,
        'sample_rate': 100,
    }

    DEFAULT_ALERTS = {
        'voltage_max': 25.0,
        'voltage_min': 0.0,
        'current_max': 6.0,
        'power_max': 100.0,
        'temp_max': 80.0,
        'enabled': True,
    }

    def __init__(self, storage_dir: Path):
        """Initialize settings manager with storage directory.

        Args:
            storage_dir: Directory to store settings file
        """
        self.storage_dir = storage_dir
        self.settings_file = storage_dir / 'settings.json'

    def load(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Load settings and alerts from storage.

        Returns:
            Tuple of (settings_dict, alerts_dict)
        """
        settings = self.DEFAULT_SETTINGS.copy()
        alerts = self.DEFAULT_ALERTS.copy()

        if self.settings_file.exists():
            try:
                saved = json.loads(self.settings_file.read_text())
                settings.update(saved.get('settings', {}))
                alerts.update(saved.get('alerts', {}))
            except (OSError, json.JSONDecodeError, KeyError):
                pass  # Settings file corrupt or unreadable, use defaults

        return settings, alerts

    def save(self, settings: Dict[str, Any], alerts: Dict[str, Any]) -> None:
        """Save settings and alerts to storage.

        Args:
            settings: Settings dictionary
            alerts: Alerts configuration dictionary
        """
        try:
            self.settings_file.write_text(json.dumps({
                'settings': settings,
                'alerts': alerts
            }, indent=2))
        except OSError:
            pass  # Unable to save settings, non-critical
