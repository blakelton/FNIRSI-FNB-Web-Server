"""Statistics Tracker - Accumulate and compute statistics."""

import threading
from datetime import datetime
from typing import Any, Dict, Optional


class StatisticsTracker:
    """Tracks and computes running statistics for readings.

    Thread-safe: All public methods are synchronized.
    """

    def __init__(self):
        """Initialize statistics tracker."""
        self._lock = threading.Lock()
        self.reset()

    def _empty_stats(self) -> Dict[str, Any]:
        """Create an empty statistics dictionary."""
        return {
            'samples': 0,
            'voltage_min': float('inf'),
            'voltage_max': 0,
            'voltage_sum': 0,
            'current_min': float('inf'),
            'current_max': 0,
            'current_sum': 0,
            'power_min': float('inf'),
            'power_max': 0,
            'power_sum': 0,
            'energy_wh': 0,
            'capacity_ah': 0,
            'duration_s': 0,
            'start_time': None,
        }

    def reset(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self._stats = self._empty_stats()
            self._stats['start_time'] = datetime.now()

    def update(self, reading: Dict[str, Any], dt: float) -> None:
        """Update statistics with a new reading.

        Args:
            reading: Dictionary with voltage, current, power values
            dt: Time delta in seconds since last reading
        """
        v = reading['voltage']
        c = reading['current']
        p = reading['power']

        with self._lock:
            self._stats['samples'] += 1
            self._stats['voltage_min'] = min(self._stats['voltage_min'], v)
            self._stats['voltage_max'] = max(self._stats['voltage_max'], v)
            self._stats['voltage_sum'] += v
            self._stats['current_min'] = min(self._stats['current_min'], c)
            self._stats['current_max'] = max(self._stats['current_max'], c)
            self._stats['current_sum'] += c
            self._stats['power_min'] = min(self._stats['power_min'], p)
            self._stats['power_max'] = max(self._stats['power_max'], p)
            self._stats['power_sum'] += p
            self._stats['energy_wh'] += (p * dt) / 3600
            self._stats['capacity_ah'] += (c * dt) / 3600
            self._stats['duration_s'] += dt

    def get_stats(self) -> Dict[str, Any]:
        """Get formatted statistics.

        Returns:
            Dictionary with computed statistics
        """
        with self._lock:
            s = self._stats.copy()
        n = s['samples'] if s['samples'] > 0 else 1
        return {
            'samples': s['samples'],
            'voltage': {
                'min': round(s['voltage_min'], 4) if s['voltage_min'] != float('inf') else 0,
                'max': round(s['voltage_max'], 4),
                'avg': round(s['voltage_sum'] / n, 4)
            },
            'current': {
                'min': round(s['current_min'], 5) if s['current_min'] != float('inf') else 0,
                'max': round(s['current_max'], 5),
                'avg': round(s['current_sum'] / n, 5)
            },
            'power': {
                'min': round(s['power_min'], 4) if s['power_min'] != float('inf') else 0,
                'max': round(s['power_max'], 4),
                'avg': round(s['power_sum'] / n, 4)
            },
            'energy_wh': round(s['energy_wh'], 6),
            'energy_mwh': round(s['energy_wh'] * 1000, 3),
            'capacity_ah': round(s['capacity_ah'], 6),
            'capacity_mah': round(s['capacity_ah'] * 1000, 3),
            'duration_s': round(s['duration_s'], 1),
            'duration_formatted': self._format_duration(s['duration_s']),
            'start_time': s['start_time'].isoformat() if s['start_time'] else None
        }

    def get_charge_estimate(self, target_mah: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Estimate charge completion based on current flow.

        Args:
            target_mah: Target capacity in mAh

        Returns:
            Dictionary with charge estimates or None if insufficient data
        """
        with self._lock:
            s = self._stats.copy()

        if s['samples'] < 100 or s['duration_s'] < 10:
            return None

        avg_current = s['current_sum'] / s['samples']
        if avg_current < 0.01:  # Less than 10mA
            return None

        current_mah = s['capacity_ah'] * 1000

        if target_mah:
            remaining_mah = target_mah - current_mah
            if remaining_mah <= 0:
                return {'complete': True, 'charged_mah': current_mah}

            avg_ma = avg_current * 1000
            remaining_hours = remaining_mah / avg_ma
            from datetime import timedelta
            eta = datetime.now() + timedelta(hours=remaining_hours)

            return {
                'complete': False,
                'charged_mah': round(current_mah, 1),
                'target_mah': target_mah,
                'remaining_mah': round(remaining_mah, 1),
                'avg_current_ma': round(avg_ma, 1),
                'remaining_time': self._format_duration(remaining_hours * 3600),
                'eta': eta.strftime('%H:%M:%S'),
                'percent': round((current_mah / target_mah) * 100, 1)
            }

        return {
            'charged_mah': round(current_mah, 1),
            'avg_current_ma': round(avg_current * 1000, 1),
            'charge_rate_mah_per_hour': round(avg_current * 1000, 1)
        }

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "1h 23m 45s")
        """
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        elif m > 0:
            return f"{m}m {s}s"
        return f"{s}s"
