"""Tests for device/device_manager.py"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from device.device_manager import DeviceManager


class TestDeviceManagerInit:
    def test_initial_state(self):
        dm = DeviceManager()
        assert dm.is_connected is False
        assert dm.is_recording is False
        assert dm.connection_type is None
        assert dm.reader is None
        assert dm.data_callbacks == []
        assert len(dm.data_buffer) == 0

    def test_stats_initial_values(self):
        dm = DeviceManager()
        assert dm.stats['samples_collected'] == 0
        assert dm.stats['max_voltage'] == 0.0
        assert dm.stats['min_voltage'] == float('inf')
        assert dm.stats['total_energy_wh'] == 0.0
        assert dm.stats['total_capacity_ah'] == 0.0

    def test_has_protocol_detector_and_alert_manager(self):
        dm = DeviceManager()
        from device.protocol_detector import ProtocolDetector
        from device.alert_manager import AlertManager
        assert isinstance(dm.protocol_detector, ProtocolDetector)
        assert isinstance(dm.alert_manager, AlertManager)


class TestConnect:
    @patch('device.device_manager.USBReader')
    @patch('device.device_manager.BluetoothReader')
    def test_connect_auto_tries_bluetooth_first(self, MockBT, MockUSB):
        mock_bt = MagicMock()
        mock_bt.get_device_info.return_value = {'name': 'FNB48S'}
        MockBT.return_value = mock_bt

        dm = DeviceManager()
        result = dm.connect(mode='auto')

        assert result['success'] is True
        assert result['connection_type'] == 'bluetooth'
        assert dm.is_connected is True
        mock_bt.connect.assert_called_once()

    @patch('device.device_manager.USBReader')
    @patch('device.device_manager.BluetoothReader')
    def test_connect_auto_falls_back_to_usb(self, MockBT, MockUSB):
        MockBT.return_value.connect.side_effect = ConnectionError("BT failed")
        mock_usb = MagicMock()
        mock_usb.get_device_info.return_value = {'name': 'FNB48P'}
        MockUSB.return_value = mock_usb

        dm = DeviceManager()
        result = dm.connect(mode='auto')

        assert result['connection_type'] == 'usb'
        assert dm.is_connected is True

    @patch('device.device_manager.BluetoothReader')
    def test_connect_bluetooth_only_success(self, MockBT):
        mock_bt = MagicMock()
        mock_bt.get_device_info.return_value = {'name': 'FNB58'}
        MockBT.return_value = mock_bt

        dm = DeviceManager()
        result = dm.connect(mode='bluetooth')

        assert result['connection_type'] == 'bluetooth'

    @patch('device.device_manager.BluetoothReader')
    def test_connect_bluetooth_only_fails(self, MockBT):
        MockBT.return_value.connect.side_effect = ConnectionError("BT failed")

        dm = DeviceManager()
        with pytest.raises(ConnectionError):
            dm.connect(mode='bluetooth')

    @patch('device.device_manager.USBReader')
    def test_connect_usb_only_success(self, MockUSB):
        mock_usb = MagicMock()
        mock_usb.get_device_info.return_value = {'name': 'FNB48'}
        MockUSB.return_value = mock_usb

        dm = DeviceManager()
        result = dm.connect(mode='usb')

        assert result['connection_type'] == 'usb'

    @patch('device.device_manager.USBReader')
    def test_connect_usb_only_fails(self, MockUSB):
        MockUSB.return_value.connect.side_effect = ConnectionError("USB failed")

        dm = DeviceManager()
        with pytest.raises(ConnectionError):
            dm.connect(mode='usb')

    @patch('device.device_manager.USBReader')
    @patch('device.device_manager.BluetoothReader')
    def test_connect_auto_all_fail(self, MockBT, MockUSB):
        MockBT.return_value.connect.side_effect = ConnectionError("BT failed")
        MockUSB.return_value.connect.side_effect = ConnectionError("USB failed")

        dm = DeviceManager()
        with pytest.raises(ConnectionError, match="Failed to connect"):
            dm.connect(mode='auto')

    @patch('device.device_manager.BluetoothReader')
    def test_connect_already_connected(self, MockBT):
        dm = DeviceManager()
        dm.is_connected = True
        with pytest.raises(ConnectionError, match="Already connected"):
            dm.connect()

    @patch('device.device_manager.BluetoothReader')
    def test_connect_passes_device_address(self, MockBT):
        mock_bt = MagicMock()
        mock_bt.get_device_info.return_value = {}
        MockBT.return_value = mock_bt

        dm = DeviceManager()
        dm.connect(mode='bluetooth', device_address='AA:BB:CC:DD:EE:FF')

        MockBT.assert_called_once_with(
            device_address='AA:BB:CC:DD:EE:FF',
            device_name=None
        )

    @patch('device.device_manager.BluetoothReader')
    def test_connect_returns_info_dict(self, MockBT):
        mock_bt = MagicMock()
        mock_bt.get_device_info.return_value = {'name': 'Test'}
        MockBT.return_value = mock_bt

        dm = DeviceManager()
        result = dm.connect(mode='bluetooth')
        assert 'success' in result
        assert 'connection_type' in result
        assert 'device_info' in result


class TestMonitoring:
    @patch('device.device_manager.BluetoothReader')
    def test_start_monitoring_calls_reader(self, MockBT):
        mock_bt = MagicMock()
        mock_bt.get_device_info.return_value = {}
        MockBT.return_value = mock_bt

        dm = DeviceManager()
        dm.connect(mode='bluetooth')
        dm.start_monitoring()

        mock_bt.start_reading.assert_called_once()

    def test_start_monitoring_not_connected(self):
        dm = DeviceManager()
        with pytest.raises(ConnectionError):
            dm.start_monitoring()

    @patch('device.device_manager.BluetoothReader')
    def test_stop_monitoring(self, MockBT):
        mock_bt = MagicMock()
        mock_bt.get_device_info.return_value = {}
        MockBT.return_value = mock_bt

        dm = DeviceManager()
        dm.connect(mode='bluetooth')
        dm.start_monitoring()
        dm.stop_monitoring()

        mock_bt.stop_reading.assert_called_once()

    def test_stop_monitoring_no_reader(self):
        dm = DeviceManager()
        dm.stop_monitoring()  # should not raise


class TestRecording:
    def test_start_recording(self):
        dm = DeviceManager()
        result = dm.start_recording()
        assert result is True
        assert dm.is_recording is True
        assert dm.session_data == []
        assert dm.session_start_time is not None

    def test_stop_recording_returns_session(self):
        dm = DeviceManager()
        dm.connection_type = 'usb'
        dm.start_recording()
        session = dm.stop_recording()

        assert 'start_time' in session
        assert 'end_time' in session
        assert 'data' in session
        assert 'stats' in session
        assert 'connection_type' in session
        assert dm.is_recording is False

    def test_recording_captures_data(self, sample_reading):
        dm = DeviceManager()
        dm.connection_type = 'usb'
        dm.start_recording()

        for _ in range(5):
            dm._on_data_received(sample_reading.copy())

        assert len(dm.session_data) == 5

    def test_not_recording_does_not_capture(self, sample_reading):
        dm = DeviceManager()
        dm._on_data_received(sample_reading.copy())
        assert dm.session_data == []


class TestOnDataReceived:
    def test_adds_to_buffer(self, sample_reading):
        dm = DeviceManager()
        dm._on_data_received(sample_reading.copy())
        assert len(dm.data_buffer) == 1

    def test_calls_protocol_detector(self, sample_reading):
        dm = DeviceManager()
        dm.protocol_detector = MagicMock()
        dm.protocol_detector.detect_protocol.return_value = {'protocol': 'Standard USB'}
        dm._on_data_received(sample_reading.copy())
        dm.protocol_detector.detect_protocol.assert_called_once()

    def test_calls_alert_manager(self, sample_reading):
        dm = DeviceManager()
        dm.alert_manager = MagicMock()
        dm.alert_manager.check_reading.return_value = []
        dm._on_data_received(sample_reading.copy())
        dm.alert_manager.check_reading.assert_called_once()

    def test_enhanced_reading_has_protocol_and_alerts(self, sample_reading):
        dm = DeviceManager()
        dm._on_data_received(sample_reading.copy())
        buffered = dm.data_buffer[-1]
        assert 'protocol' in buffered
        assert 'has_alerts' in buffered

    def test_calls_registered_callbacks(self, sample_reading):
        dm = DeviceManager()
        callback = MagicMock()
        dm.register_callback(callback)
        dm._on_data_received(sample_reading.copy())
        assert callback.called

    def test_callback_error_does_not_propagate(self, sample_reading):
        dm = DeviceManager()
        bad_callback = MagicMock(side_effect=Exception("boom"))
        dm.register_callback(bad_callback)
        # Should not raise
        dm._on_data_received(sample_reading.copy())
        assert len(dm.data_buffer) == 1

    def test_buffer_maxlen_respected(self, sample_reading):
        dm = DeviceManager()
        for i in range(10001):
            r = sample_reading.copy()
            r['sample'] = i
            dm._on_data_received(r)
        assert len(dm.data_buffer) == 10000


class TestUpdateStats:
    def test_stats_accumulate(self):
        dm = DeviceManager()
        dm.connection_type = 'usb'
        dm.start_recording()

        dm._on_data_received({'voltage': 4.0, 'current': 0.5, 'power': 2.0,
                              'dp': 0, 'dn': 0, 'temperature': 25.0})
        dm._on_data_received({'voltage': 6.0, 'current': 1.5, 'power': 9.0,
                              'dp': 0, 'dn': 0, 'temperature': 25.0})

        assert dm.stats['samples_collected'] == 2
        assert dm.stats['max_voltage'] == 6.0
        assert dm.stats['min_voltage'] == 4.0
        assert dm.stats['max_current'] == 1.5

    def test_energy_calculation_usb(self):
        dm = DeviceManager()
        dm.connection_type = 'usb'
        dm.start_recording()

        dm._on_data_received({'voltage': 5.0, 'current': 1.0, 'power': 5.0,
                              'dp': 0, 'dn': 0, 'temperature': 25.0})

        # USB: dt=0.01, energy = 5.0 * 0.01 / 3600
        expected_energy = (5.0 * 0.01) / 3600
        assert abs(dm.stats['total_energy_wh'] - expected_energy) < 1e-10

    def test_energy_calculation_bluetooth(self):
        dm = DeviceManager()
        dm.connection_type = 'bluetooth'
        dm.start_recording()

        dm._on_data_received({'voltage': 5.0, 'current': 1.0, 'power': 5.0,
                              'dp': 0, 'dn': 0, 'temperature': 25.0})

        # BT: dt=0.1, energy = 5.0 * 0.1 / 3600
        expected_energy = (5.0 * 0.1) / 3600
        assert abs(dm.stats['total_energy_wh'] - expected_energy) < 1e-10

    def test_running_average(self):
        dm = DeviceManager()
        dm.connection_type = 'usb'
        dm.start_recording()

        dm._on_data_received({'voltage': 4.0, 'current': 1.0, 'power': 4.0,
                              'dp': 0, 'dn': 0, 'temperature': 25.0})
        dm._on_data_received({'voltage': 6.0, 'current': 1.0, 'power': 6.0,
                              'dp': 0, 'dn': 0, 'temperature': 25.0})

        assert abs(dm.stats['avg_voltage'] - 5.0) < 1e-10


class TestCallbacks:
    def test_register_callback(self):
        dm = DeviceManager()
        fn = MagicMock()
        dm.register_callback(fn)
        assert fn in dm.data_callbacks

    def test_unregister_callback(self):
        dm = DeviceManager()
        fn = MagicMock()
        dm.register_callback(fn)
        dm.unregister_callback(fn)
        assert fn not in dm.data_callbacks

    def test_unregister_nonexistent(self):
        dm = DeviceManager()
        fn = MagicMock()
        dm.unregister_callback(fn)  # should not raise


class TestGetData:
    def test_get_latest_reading_empty(self):
        dm = DeviceManager()
        assert dm.get_latest_reading() is None

    def test_get_latest_reading(self, sample_reading):
        dm = DeviceManager()
        dm._on_data_received(sample_reading.copy())
        latest = dm.get_latest_reading()
        assert latest is not None
        assert latest['voltage'] == 5.0

    def test_get_recent_data(self, sample_reading):
        dm = DeviceManager()
        for i in range(200):
            r = sample_reading.copy()
            r['sample'] = i
            dm._on_data_received(r)
        recent = dm.get_recent_data(50)
        assert len(recent) == 50

    def test_get_recent_data_less_than_requested(self, sample_reading):
        dm = DeviceManager()
        for i in range(30):
            r = sample_reading.copy()
            r['sample'] = i
            dm._on_data_received(r)
        recent = dm.get_recent_data(100)
        assert len(recent) == 30

    def test_get_stats_returns_copy(self):
        dm = DeviceManager()
        stats = dm.get_stats()
        stats['samples_collected'] = 999
        assert dm.stats['samples_collected'] == 0  # unchanged


class TestDisconnect:
    @patch('device.device_manager.BluetoothReader')
    def test_disconnect_calls_reader(self, MockBT):
        mock_bt = MagicMock()
        mock_bt.get_device_info.return_value = {}
        MockBT.return_value = mock_bt

        dm = DeviceManager()
        dm.connect(mode='bluetooth')
        dm.disconnect()

        mock_bt.stop_reading.assert_called()
        mock_bt.disconnect.assert_called_once()

    @patch('device.device_manager.BluetoothReader')
    def test_disconnect_resets_state(self, MockBT):
        mock_bt = MagicMock()
        mock_bt.get_device_info.return_value = {}
        MockBT.return_value = mock_bt

        dm = DeviceManager()
        dm.connect(mode='bluetooth')
        dm.disconnect()

        assert dm.is_connected is False
        assert dm.connection_type is None
        assert dm.reader is None

    def test_disconnect_no_reader(self):
        dm = DeviceManager()
        dm.disconnect()  # should not raise


class TestTriggerVoltage:
    @patch('device.device_manager.USBReader')
    def test_trigger_via_usb(self, MockUSB):
        mock_usb = MagicMock()
        mock_usb.get_device_info.return_value = {}
        mock_usb.trigger_voltage.return_value = True
        MockUSB.return_value = mock_usb

        dm = DeviceManager()
        dm.connect(mode='usb')
        result = dm.trigger_voltage('pd', 9)

        assert result is True
        mock_usb.trigger_voltage.assert_called_once_with('pd', 9)

    @patch('device.device_manager.BluetoothReader')
    def test_trigger_via_bluetooth_fails(self, MockBT):
        mock_bt = MagicMock()
        mock_bt.get_device_info.return_value = {}
        MockBT.return_value = mock_bt

        dm = DeviceManager()
        dm.connect(mode='bluetooth')
        with pytest.raises(ValueError, match="USB"):
            dm.trigger_voltage('pd', 9)

    def test_trigger_not_connected(self):
        dm = DeviceManager()
        with pytest.raises(ConnectionError):
            dm.trigger_voltage('pd', 9)

    @patch('device.device_manager.USBReader')
    def test_qc3_adjust_via_usb(self, MockUSB):
        mock_usb = MagicMock()
        mock_usb.get_device_info.return_value = {}
        mock_usb.adjust_qc3_voltage.return_value = True
        MockUSB.return_value = mock_usb

        dm = DeviceManager()
        dm.connect(mode='usb')
        result = dm.adjust_qc3_voltage(9.0)
        assert result is True

    @patch('device.device_manager.BluetoothReader')
    def test_qc3_adjust_via_bluetooth_fails(self, MockBT):
        mock_bt = MagicMock()
        mock_bt.get_device_info.return_value = {}
        MockBT.return_value = mock_bt

        dm = DeviceManager()
        dm.connect(mode='bluetooth')
        with pytest.raises(ValueError, match="USB"):
            dm.adjust_qc3_voltage(9.0)


class TestGetConnectionInfo:
    def test_not_connected(self):
        dm = DeviceManager()
        info = dm.get_connection_info()
        assert info['connected'] is False

    @patch('device.device_manager.USBReader')
    def test_connected_usb(self, MockUSB):
        mock_usb = MagicMock()
        mock_usb.get_device_info.return_value = {'name': 'FNB48P'}
        MockUSB.return_value = mock_usb

        dm = DeviceManager()
        dm.connect(mode='usb')
        info = dm.get_connection_info()

        assert info['connected'] is True
        assert info['connection_type'] == 'usb'
        assert 'device_info' in info
        assert 'is_recording' in info
