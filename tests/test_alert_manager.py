"""Tests for device/alert_manager.py"""

import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from device.alert_manager import AlertManager, AlertLevel, AlertType


class TestAlertManagerInit:
    def test_default_thresholds(self):
        am = AlertManager()
        assert am.thresholds['max_voltage'] == 21.0
        assert am.thresholds['min_voltage'] == 3.0
        assert am.thresholds['max_current'] == 6.0
        assert am.thresholds['max_power'] == 120.0
        assert am.thresholds['max_temperature'] == 80.0
        assert am.thresholds['voltage_drop_threshold'] == 0.5

    def test_empty_initial_state(self):
        am = AlertManager()
        assert am.active_alerts == []
        assert am.alert_history == []
        assert am.alert_callbacks == []
        assert am.previous_voltage is None


class TestSetThreshold:
    def test_set_known_threshold(self):
        am = AlertManager()
        result = am.set_threshold('max_voltage', 25.0)
        assert result is True
        assert am.thresholds['max_voltage'] == 25.0

    def test_set_unknown_threshold(self):
        am = AlertManager()
        result = am.set_threshold('nonexistent', 1.0)
        assert result is False

    def test_get_thresholds_returns_copy(self):
        am = AlertManager()
        thresholds = am.get_thresholds()
        thresholds['max_voltage'] = 999
        assert am.thresholds['max_voltage'] == 21.0  # unchanged


class TestCheckReading:
    def test_overvoltage_alert(self):
        am = AlertManager()
        alerts = am.check_reading({'voltage': 22.0, 'current': 1.0, 'power': 22.0, 'temperature': 25.0})
        assert len(alerts) >= 1
        assert any(a['type'] == 'overvoltage' for a in alerts)
        assert any(a['level'] == 'critical' for a in alerts)

    def test_undervoltage_alert(self):
        am = AlertManager()
        alerts = am.check_reading({'voltage': 2.5, 'current': 0.5, 'power': 1.25, 'temperature': 25.0})
        assert any(a['type'] == 'undervoltage' for a in alerts)
        assert any(a['level'] == 'warning' for a in alerts)

    def test_zero_voltage_no_undervoltage_alert(self):
        am = AlertManager()
        alerts = am.check_reading({'voltage': 0.0, 'current': 0.0, 'power': 0.0, 'temperature': 25.0})
        assert not any(a['type'] == 'undervoltage' for a in alerts)

    def test_overcurrent_alert(self):
        am = AlertManager()
        alerts = am.check_reading({'voltage': 5.0, 'current': 7.0, 'power': 35.0, 'temperature': 25.0})
        assert any(a['type'] == 'overcurrent' for a in alerts)

    def test_overpower_alert(self):
        am = AlertManager()
        alerts = am.check_reading({'voltage': 20.0, 'current': 5.0, 'power': 130.0, 'temperature': 25.0})
        assert any(a['type'] == 'overpower' for a in alerts)

    def test_overtemperature_alert(self):
        am = AlertManager()
        alerts = am.check_reading({'voltage': 5.0, 'current': 1.0, 'power': 5.0, 'temperature': 85.0})
        assert any(a['type'] == 'overtemperature' for a in alerts)

    def test_voltage_drop_alert(self):
        am = AlertManager()
        am.check_reading({'voltage': 12.0, 'current': 1.0, 'power': 12.0, 'temperature': 25.0})
        alerts = am.check_reading({'voltage': 11.0, 'current': 1.0, 'power': 11.0, 'temperature': 25.0})
        assert any(a['type'] == 'voltage_drop' for a in alerts)

    def test_no_voltage_drop_on_first_reading(self):
        am = AlertManager()
        alerts = am.check_reading({'voltage': 5.0, 'current': 1.0, 'power': 5.0, 'temperature': 25.0})
        assert not any(a['type'] == 'voltage_drop' for a in alerts)

    def test_no_alerts_within_thresholds(self):
        am = AlertManager()
        alerts = am.check_reading({'voltage': 5.0, 'current': 1.0, 'power': 5.0, 'temperature': 25.0})
        assert len(alerts) == 0

    def test_multiple_simultaneous_alerts(self):
        am = AlertManager()
        alerts = am.check_reading({'voltage': 22.0, 'current': 7.0, 'power': 154.0, 'temperature': 85.0})
        alert_types = {a['type'] for a in alerts}
        assert 'overvoltage' in alert_types
        assert 'overcurrent' in alert_types
        assert 'overtemperature' in alert_types

    def test_alert_has_required_fields(self):
        am = AlertManager()
        alerts = am.check_reading({'voltage': 22.0, 'current': 1.0, 'power': 22.0, 'temperature': 25.0})
        alert = alerts[0]
        assert 'id' in alert
        assert 'type' in alert
        assert 'level' in alert
        assert 'message' in alert
        assert 'timestamp' in alert
        assert 'reading' in alert
        assert 'acknowledged' in alert
        assert alert['acknowledged'] is False

    def test_previous_voltage_updated(self):
        am = AlertManager()
        am.check_reading({'voltage': 5.0, 'current': 1.0, 'power': 5.0, 'temperature': 25.0})
        assert am.previous_voltage == 5.0


class TestCooldown:
    def test_cooldown_prevents_duplicate_alerts(self):
        am = AlertManager()
        reading = {'voltage': 22.0, 'current': 1.0, 'power': 22.0, 'temperature': 25.0}
        alerts1 = am.check_reading(reading)
        alerts2 = am.check_reading(reading)
        assert len(alerts1) >= 1
        overvoltage_alerts2 = [a for a in alerts2 if a['type'] == 'overvoltage']
        assert len(overvoltage_alerts2) == 0  # suppressed by cooldown

    def test_cooldown_expires(self):
        am = AlertManager()
        reading = {'voltage': 22.0, 'current': 1.0, 'power': 22.0, 'temperature': 25.0}

        # First alert
        alerts1 = am.check_reading(reading)
        assert len(alerts1) >= 1

        # Manually expire cooldown by setting time in the past
        for key in am.cooldown_periods:
            am.cooldown_periods[key] = datetime.now() - timedelta(seconds=10)

        # Second alert should now fire
        alerts2 = am.check_reading(reading)
        assert any(a['type'] == 'overvoltage' for a in alerts2)

    def test_different_alert_types_independent_cooldown(self):
        am = AlertManager()
        reading = {'voltage': 22.0, 'current': 7.0, 'power': 154.0, 'temperature': 85.0}
        alerts = am.check_reading(reading)
        alert_types = {a['type'] for a in alerts}
        # All different types should fire on first check
        assert 'overvoltage' in alert_types
        assert 'overcurrent' in alert_types
        assert 'overtemperature' in alert_types


class TestAlertCallbacks:
    def test_register_callback(self):
        am = AlertManager()
        callback = MagicMock()
        am.register_callback(callback)
        am.check_reading({'voltage': 22.0, 'current': 1.0, 'power': 22.0, 'temperature': 25.0})
        assert callback.called

    def test_multiple_callbacks(self):
        am = AlertManager()
        cb1 = MagicMock()
        cb2 = MagicMock()
        am.register_callback(cb1)
        am.register_callback(cb2)
        am.check_reading({'voltage': 22.0, 'current': 1.0, 'power': 22.0, 'temperature': 25.0})
        assert cb1.called
        assert cb2.called

    def test_callback_error_does_not_propagate(self):
        am = AlertManager()
        bad_callback = MagicMock(side_effect=Exception("callback error"))
        am.register_callback(bad_callback)
        # Should not raise
        alerts = am.check_reading({'voltage': 22.0, 'current': 1.0, 'power': 22.0, 'temperature': 25.0})
        assert len(alerts) >= 1


class TestAlertManagement:
    def test_acknowledge_alert(self):
        am = AlertManager()
        am.check_reading({'voltage': 22.0, 'current': 1.0, 'power': 22.0, 'temperature': 25.0})
        alert_id = am.active_alerts[0]['id']
        result = am.acknowledge_alert(alert_id)
        assert result is True
        assert am.active_alerts[0]['acknowledged'] is True

    def test_acknowledge_nonexistent_alert(self):
        am = AlertManager()
        result = am.acknowledge_alert('fake_id')
        assert result is False

    def test_clear_acknowledged_alerts(self):
        am = AlertManager()
        # Trigger multiple alerts
        am.check_reading({'voltage': 22.0, 'current': 7.0, 'power': 154.0, 'temperature': 85.0})
        # Acknowledge first one
        am.acknowledge_alert(am.active_alerts[0]['id'])
        total_before = len(am.active_alerts)
        am.clear_acknowledged_alerts()
        assert len(am.active_alerts) == total_before - 1

    def test_get_active_alerts_excludes_acknowledged(self):
        am = AlertManager()
        am.check_reading({'voltage': 22.0, 'current': 1.0, 'power': 22.0, 'temperature': 25.0})
        am.acknowledge_alert(am.active_alerts[0]['id'])
        active = am.get_active_alerts()
        assert len(active) == 0

    def test_get_alert_history_with_limit(self):
        am = AlertManager()
        # Generate multiple alerts by expiring cooldowns between each
        for i in range(5):
            for key in list(am.cooldown_periods.keys()):
                am.cooldown_periods[key] = datetime.now() - timedelta(seconds=10)
            am.check_reading({'voltage': 22.0, 'current': 1.0, 'power': 22.0, 'temperature': 25.0})

        history = am.get_alert_history(limit=3)
        assert len(history) == 3

    def test_alert_history_capped_at_100(self):
        am = AlertManager()
        # Force-create 105 alerts by manipulating cooldown each time
        for i in range(105):
            for key in list(am.cooldown_periods.keys()):
                am.cooldown_periods[key] = datetime.now() - timedelta(seconds=10)
            am.check_reading({'voltage': 22.0, 'current': 1.0, 'power': 22.0, 'temperature': 25.0})

        assert len(am.alert_history) <= 100

    def test_clear_all_alerts(self):
        am = AlertManager()
        am.check_reading({'voltage': 22.0, 'current': 1.0, 'power': 22.0, 'temperature': 25.0})
        assert len(am.active_alerts) > 0
        am.clear_all_alerts()
        assert len(am.active_alerts) == 0


class TestAlertEnums:
    def test_alert_levels(self):
        assert AlertLevel.INFO.value == 'info'
        assert AlertLevel.WARNING.value == 'warning'
        assert AlertLevel.CRITICAL.value == 'critical'

    def test_alert_types(self):
        assert AlertType.OVERVOLTAGE.value == 'overvoltage'
        assert AlertType.UNDERVOLTAGE.value == 'undervoltage'
        assert AlertType.OVERCURRENT.value == 'overcurrent'
        assert AlertType.OVERPOWER.value == 'overpower'
        assert AlertType.OVERTEMPERATURE.value == 'overtemperature'
        assert AlertType.VOLTAGE_DROP.value == 'voltage_drop'
        assert AlertType.CONNECTION_LOST.value == 'connection_lost'
