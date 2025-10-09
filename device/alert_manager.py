"""
Alert Manager for monitoring thresholds and triggering notifications
"""

from datetime import datetime
from enum import Enum

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'

class AlertType(Enum):
    """Types of alerts"""
    OVERVOLTAGE = 'overvoltage'
    UNDERVOLTAGE = 'undervoltage'
    OVERCURRENT = 'overcurrent'
    OVERPOWER = 'overpower'
    OVERTEMPERATURE = 'overtemperature'
    VOLTAGE_DROP = 'voltage_drop'
    CONNECTION_LOST = 'connection_lost'

class AlertManager:
    """Manage alerts and thresholds"""

    def __init__(self):
        self.thresholds = {
            'max_voltage': 21.0,      # Maximum voltage (V)
            'min_voltage': 3.0,       # Minimum voltage (V)
            'max_current': 6.0,       # Maximum current (A)
            'max_power': 120.0,       # Maximum power (W)
            'max_temperature': 80.0,  # Maximum temperature (°C)
            'voltage_drop_threshold': 0.5,  # Voltage drop detection (V)
        }

        self.active_alerts = []
        self.alert_history = []
        self.alert_callbacks = []
        self.previous_voltage = None
        self.cooldown_periods = {}  # Prevent alert spam

    def set_threshold(self, threshold_name, value):
        """Set a threshold value"""
        if threshold_name in self.thresholds:
            self.thresholds[threshold_name] = value
            return True
        return False

    def get_thresholds(self):
        """Get all current thresholds"""
        return self.thresholds.copy()

    def check_reading(self, reading):
        """
        Check a reading against all thresholds

        Args:
            reading: Dictionary with voltage, current, power, temperature

        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        voltage = reading.get('voltage', 0)
        current = reading.get('current', 0)
        power = reading.get('power', 0)
        temperature = reading.get('temperature', 0)

        # Check overvoltage
        if voltage > self.thresholds['max_voltage']:
            alert = self._create_alert(
                AlertType.OVERVOLTAGE,
                AlertLevel.CRITICAL,
                f'Voltage exceeded {self.thresholds["max_voltage"]}V: {voltage:.2f}V',
                reading
            )
            if alert:
                triggered_alerts.append(alert)

        # Check undervoltage
        if voltage < self.thresholds['min_voltage'] and voltage > 0:
            alert = self._create_alert(
                AlertType.UNDERVOLTAGE,
                AlertLevel.WARNING,
                f'Voltage below {self.thresholds["min_voltage"]}V: {voltage:.2f}V',
                reading
            )
            if alert:
                triggered_alerts.append(alert)

        # Check overcurrent
        if current > self.thresholds['max_current']:
            alert = self._create_alert(
                AlertType.OVERCURRENT,
                AlertLevel.CRITICAL,
                f'Current exceeded {self.thresholds["max_current"]}A: {current:.2f}A',
                reading
            )
            if alert:
                triggered_alerts.append(alert)

        # Check overpower
        if power > self.thresholds['max_power']:
            alert = self._create_alert(
                AlertType.OVERPOWER,
                AlertLevel.WARNING,
                f'Power exceeded {self.thresholds["max_power"]}W: {power:.2f}W',
                reading
            )
            if alert:
                triggered_alerts.append(alert)

        # Check overtemperature
        if temperature > self.thresholds['max_temperature']:
            alert = self._create_alert(
                AlertType.OVERTEMPERATURE,
                AlertLevel.CRITICAL,
                f'Temperature exceeded {self.thresholds["max_temperature"]}°C: {temperature:.1f}°C',
                reading
            )
            if alert:
                triggered_alerts.append(alert)

        # Check voltage drop
        if self.previous_voltage is not None:
            voltage_drop = self.previous_voltage - voltage
            if voltage_drop > self.thresholds['voltage_drop_threshold']:
                alert = self._create_alert(
                    AlertType.VOLTAGE_DROP,
                    AlertLevel.WARNING,
                    f'Voltage dropped {voltage_drop:.2f}V ({self.previous_voltage:.2f}V → {voltage:.2f}V)',
                    reading
                )
                if alert:
                    triggered_alerts.append(alert)

        self.previous_voltage = voltage

        # Trigger callbacks
        for alert in triggered_alerts:
            self._trigger_callbacks(alert)

        return triggered_alerts

    def _create_alert(self, alert_type, level, message, reading):
        """Create an alert if not in cooldown"""
        # Check cooldown
        alert_key = f"{alert_type.value}_{level.value}"
        now = datetime.now()

        if alert_key in self.cooldown_periods:
            last_alert_time = self.cooldown_periods[alert_key]
            elapsed = (now - last_alert_time).total_seconds()
            if elapsed < 5.0:  # 5 second cooldown
                return None

        # Create alert
        alert = {
            'id': f"{alert_type.value}_{now.timestamp()}",
            'type': alert_type.value,
            'level': level.value,
            'message': message,
            'timestamp': now.isoformat(),
            'reading': reading,
            'acknowledged': False
        }

        self.active_alerts.append(alert)
        self.alert_history.append(alert)
        self.cooldown_periods[alert_key] = now

        # Keep history limited to 100 alerts
        if len(self.alert_history) > 100:
            self.alert_history.pop(0)

        return alert

    def _trigger_callbacks(self, alert):
        """Trigger all registered alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Error in alert callback: {e}")

    def register_callback(self, callback):
        """Register a callback to be called when alerts are triggered"""
        self.alert_callbacks.append(callback)

    def acknowledge_alert(self, alert_id):
        """Acknowledge an alert"""
        for alert in self.active_alerts:
            if alert['id'] == alert_id:
                alert['acknowledged'] = True
                return True
        return False

    def clear_acknowledged_alerts(self):
        """Remove all acknowledged alerts from active list"""
        self.active_alerts = [a for a in self.active_alerts if not a['acknowledged']]

    def get_active_alerts(self):
        """Get all active (unacknowledged) alerts"""
        return [a for a in self.active_alerts if not a['acknowledged']]

    def get_alert_history(self, limit=50):
        """Get recent alert history"""
        return self.alert_history[-limit:]

    def clear_all_alerts(self):
        """Clear all active alerts"""
        self.active_alerts = []
