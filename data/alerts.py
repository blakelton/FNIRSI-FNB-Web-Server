"""Alert Manager - Monitor thresholds and generate alerts."""

import threading
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class Alert:
    """Represents an active alert."""
    alert_type: str
    message: str


class AlertManager:
    """Monitors reading thresholds and generates alerts.

    Thread-safe: All public methods are synchronized.
    """

    def __init__(self):
        """Initialize alert manager with default thresholds."""
        self._lock = threading.Lock()
        self._config = {
            'voltage_max': 25.0,
            'voltage_min': 0.0,
            'current_max': 6.0,
            'power_max': 100.0,
            'temp_max': 80.0,
            'enabled': True
        }
        self._active_alerts: List[Dict[str, str]] = []

    def check(self, reading: Dict[str, Any]) -> List[Dict[str, str]]:
        """Check reading against thresholds and update active alerts.

        Args:
            reading: Dictionary with voltage, current, power, temperature

        Returns:
            List of triggered alert dictionaries
        """
        with self._lock:
            if not self._config['enabled']:
                self._active_alerts = []
                return []

            alerts = []

            v = reading['voltage']
            c = reading['current']
            p = reading['power']
            t = reading['temperature']

            if v > self._config['voltage_max']:
                alerts.append({'type': 'danger', 'message': f"Overvoltage: {v:.2f}V"})

            if v < self._config['voltage_min'] and v > 0.1:
                alerts.append({'type': 'warning', 'message': f"Undervoltage: {v:.2f}V"})

            if c > self._config['current_max']:
                alerts.append({'type': 'danger', 'message': f"Overcurrent: {c:.3f}A"})

            if p > self._config['power_max']:
                alerts.append({'type': 'danger', 'message': f"Overpower: {p:.2f}W"})

            if t > self._config['temp_max']:
                alerts.append({'type': 'warning', 'message': f"High temp: {t:.1f}°C"})

            self._active_alerts = alerts
            return alerts

    @property
    def active_alerts(self) -> List[Dict[str, str]]:
        """Get currently active alerts."""
        with self._lock:
            return self._active_alerts.copy()

    def get_config(self) -> Dict[str, Any]:
        """Get current alert configuration.

        Returns:
            Dictionary with threshold configuration
        """
        with self._lock:
            return self._config.copy()

    def set_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update alert configuration.

        Args:
            config: Dictionary with threshold values to update

        Returns:
            Updated configuration dictionary
        """
        with self._lock:
            self._config.update(config)
            return self._config.copy()

    def get_status(self) -> Dict[str, Any]:
        """Get current alert status and configuration.

        Returns:
            Dictionary with active alerts and configuration
        """
        with self._lock:
            return {
                'active': self._active_alerts.copy(),
                'config': self._config.copy()
            }
