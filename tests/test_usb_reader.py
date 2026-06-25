"""Tests for device/usb_reader.py (hidapi-based transport)."""

import pytest
from unittest.mock import patch, MagicMock
from device.usb_reader import USBReader


def _enum_side_effect(target_vid, target_pid, entry):
    """Build a hid.enumerate side_effect that only matches one (vid, pid)."""
    def _enum(vid, pid):
        if vid == target_vid and pid == target_pid:
            return [entry]
        return []
    return _enum


def _entry(vid, pid):
    return {
        'path': b'/dev/hidraw-test',
        'vendor_id': vid,
        'product_id': pid,
        'interface_number': 0,
        'manufacturer_string': 'FNIRSI',
        'product_string': 'USB Tester',
        'serial_number': '0001',
    }


class TestUSBReaderInit:
    def test_default_init(self):
        reader = USBReader()
        assert reader.device is None
        assert reader.is_connected is False
        assert reader.is_reading is False
        assert len(reader.data_buffer) == 0

    def test_custom_vendor_product(self):
        reader = USBReader(vendor_id=0x1234, product_ids=[0x5678])
        assert reader.vendor_id == 0x1234
        assert reader.product_ids == [0x5678]

    def test_supported_devices_defined(self):
        assert len(USBReader.SUPPORTED_DEVICES) > 0
        for vid, pid in USBReader.SUPPORTED_DEVICES:
            assert isinstance(vid, int)
            assert isinstance(pid, int)


@patch('device.usb_reader._HIDAPI_AVAILABLE', True)
class TestUSBReaderConnect:
    @patch('device.usb_reader.hid')
    def test_connect_auto_detect(self, mock_hid):
        mock_hid.enumerate.side_effect = _enum_side_effect(
            0x2e3c, 0x0049, _entry(0x2e3c, 0x0049))
        mock_dev = MagicMock()
        mock_dev.read.return_value = [0xAA, 0x04] + [0] * 62
        mock_hid.device.return_value = mock_dev

        reader = USBReader()
        result = reader.connect()

        assert result is True
        assert reader.is_connected is True
        mock_dev.open_path.assert_called_once()

    @patch('device.usb_reader.hid')
    def test_connect_device_not_found(self, mock_hid):
        mock_hid.enumerate.return_value = []

        reader = USBReader()
        with pytest.raises(ConnectionError, match="not found"):
            reader.connect()

    @patch('device.usb_reader.hid')
    def test_connect_detects_fnb58_type(self, mock_hid):
        mock_hid.enumerate.side_effect = _enum_side_effect(
            0x2e3c, 0x5558, _entry(0x2e3c, 0x5558))
        mock_dev = MagicMock()
        mock_dev.read.return_value = []
        mock_hid.device.return_value = mock_dev

        reader = USBReader()
        reader.connect()

        assert reader.is_fnb58_or_fnb48s is True

    @patch('device.usb_reader.hid')
    def test_connect_detects_fnb48_type(self, mock_hid):
        mock_hid.enumerate.side_effect = _enum_side_effect(
            0x0483, 0x003a, _entry(0x0483, 0x003a))
        mock_dev = MagicMock()
        mock_dev.read.return_value = []
        mock_hid.device.return_value = mock_dev

        reader = USBReader()
        reader.connect()

        assert reader.is_fnb58_or_fnb48s is False

    @patch('device.usb_reader.hid')
    def test_connect_sends_init_handshake(self, mock_hid):
        mock_hid.enumerate.side_effect = _enum_side_effect(
            0x2e3c, 0x0049, _entry(0x2e3c, 0x0049))
        mock_dev = MagicMock()
        mock_dev.read.return_value = []
        mock_hid.device.return_value = mock_dev

        reader = USBReader()
        reader.connect()

        # Handshake writes go through the hid device
        assert mock_dev.write.called

    @patch('device.usb_reader.hid')
    def test_connect_open_failure_raises(self, mock_hid):
        mock_hid.enumerate.side_effect = _enum_side_effect(
            0x2e3c, 0x0049, _entry(0x2e3c, 0x0049))
        mock_dev = MagicMock()
        mock_dev.open_path.side_effect = OSError("open failed")
        mock_hid.device.return_value = mock_dev

        reader = USBReader()
        with pytest.raises(ConnectionError, match="Failed to open"):
            reader.connect()


def test_connect_without_hidapi_raises():
    """If hidapi is missing, connect() fails with an actionable message."""
    with patch('device.usb_reader._HIDAPI_AVAILABLE', False):
        reader = USBReader()
        with pytest.raises(ConnectionError, match="hidapi is not installed"):
            reader.connect()


class TestDecodePacket:
    def test_decode_valid_data_packet(self, usb_data_packet):
        reader = USBReader()
        readings = reader._decode_packet(usb_data_packet)
        assert len(readings) == 4

        # Sample 0: 5V, 1A, dp=2.7, dn=2.7, 25C
        assert readings[0]['voltage'] == 5.0
        assert readings[0]['current'] == 1.0
        assert readings[0]['dp'] == 2.7
        assert readings[0]['dn'] == 2.7
        assert readings[0]['temperature'] == 25.0
        assert readings[0]['sample'] == 0

    def test_decode_sample_1(self, usb_data_packet):
        reader = USBReader()
        readings = reader._decode_packet(usb_data_packet)
        # Sample 1: 9V, 2A, dp=0.6, dn=0.3, 30C
        assert readings[1]['voltage'] == 9.0
        assert readings[1]['current'] == 2.0
        assert readings[1]['dp'] == 0.6
        assert readings[1]['dn'] == 0.3
        assert readings[1]['temperature'] == 30.0

    def test_decode_sample_2(self, usb_data_packet):
        reader = USBReader()
        readings = reader._decode_packet(usb_data_packet)
        # Sample 2: 12V, 3A
        assert readings[2]['voltage'] == 12.0
        assert readings[2]['current'] == 3.0

    def test_decode_sample_3(self, usb_data_packet):
        reader = USBReader()
        readings = reader._decode_packet(usb_data_packet)
        # Sample 3: 20V, 5A
        assert readings[3]['voltage'] == 20.0
        assert readings[3]['current'] == 5.0
        assert readings[3]['dp'] == 0.0
        assert readings[3]['dn'] == 0.0

    def test_decode_non_data_packet(self, usb_non_data_packet):
        reader = USBReader()
        readings = reader._decode_packet(usb_non_data_packet)
        assert readings == []

    def test_decode_short_packet(self, usb_short_packet):
        reader = USBReader()
        readings = reader._decode_packet(usb_short_packet)
        assert readings == []

    def test_decode_power_calculation(self, usb_data_packet):
        reader = USBReader()
        readings = reader._decode_packet(usb_data_packet)
        for r in readings:
            expected_power = round(r['voltage'] * r['current'], 5)
            assert r['power'] == expected_power

    def test_decode_reading_has_all_fields(self, usb_data_packet):
        reader = USBReader()
        readings = reader._decode_packet(usb_data_packet)
        required_fields = ['timestamp', 'voltage', 'current', 'power', 'dp', 'dn', 'temperature', 'sample']
        for r in readings:
            for field in required_fields:
                assert field in r

    def test_decode_sample_indices(self, usb_data_packet):
        reader = USBReader()
        readings = reader._decode_packet(usb_data_packet)
        for i, r in enumerate(readings):
            assert r['sample'] == i

    def test_decode_zero_values(self, usb_zero_packet):
        reader = USBReader()
        readings = reader._decode_packet(usb_zero_packet)
        assert len(readings) == 4
        for r in readings:
            assert r['voltage'] == 0.0
            assert r['current'] == 0.0
            assert r['power'] == 0.0


class TestWriteReportId:
    """The hidapi write must prepend a 0x00 report-id byte (65-byte buffer)."""

    def test_write_prepends_report_id_and_pads(self):
        reader = USBReader()
        reader.device = MagicMock()
        reader.device.write.return_value = 65

        reader._write(b"\xaa\x83" + b"\x00" * 61 + b"\x9e")

        sent = reader.device.write.call_args[0][0]
        assert len(sent) == 65          # 1 report id + 64 data bytes
        assert sent[0] == 0x00          # report id
        assert sent[1] == 0xAA          # first data byte preserved

    def test_write_negative_result_raises(self):
        reader = USBReader()
        reader.device = MagicMock()
        reader.device.write.return_value = -1
        with pytest.raises(ConnectionError, match="HID write failed"):
            reader._write(b"\xaa\x83")


class TestStartStopReading:
    def test_start_reading_not_connected(self):
        reader = USBReader()
        with pytest.raises(ConnectionError):
            reader.start_reading()

    def test_start_reading_creates_thread(self):
        reader = USBReader()
        reader.is_connected = True
        callback = MagicMock()
        reader.start_reading(callback=callback)
        assert reader.is_reading is True
        assert reader.read_thread is not None
        assert reader.data_callback is callback
        # Clean up
        reader.stop_reading()

    def test_stop_reading_sets_flag(self):
        reader = USBReader()
        reader.is_reading = True
        reader.read_thread = MagicMock()
        reader.stop_reading()
        assert reader.is_reading is False


class TestDisconnect:
    def test_disconnect_releases_resources(self):
        reader = USBReader()
        reader.device = MagicMock()
        reader.is_connected = True
        reader.disconnect()
        reader.device.close.assert_called_once()
        assert reader.is_connected is False

    def test_disconnect_no_device(self):
        reader = USBReader()
        reader.device = None
        reader.disconnect()  # should not raise
        assert reader.is_connected is False


class TestGetDeviceInfo:
    def test_get_device_info_connected(self):
        reader = USBReader()
        reader.device = MagicMock()
        reader.vendor_id = 0x2e3c
        reader.product_id = 0x0049
        reader._device_info = {
            'manufacturer_string': 'FNIRSI',
            'product_string': 'FNB58',
            'serial_number': '0001',
        }

        info = reader.get_device_info()
        assert info is not None
        assert info['vendor_id'] == '0x2e3c'
        assert info['product_id'] == '0x0049'
        assert info['manufacturer'] == 'FNIRSI'
        assert info['product'] == 'FNB58'
        assert info['serial'] == '0001'

    def test_get_device_info_no_device(self):
        reader = USBReader()
        assert reader.get_device_info() is None


class TestTriggerVoltage:
    def test_trigger_pd_5v(self):
        reader = USBReader()
        reader.is_connected = True
        reader.device = MagicMock()
        result = reader.trigger_voltage('pd', 5)
        assert result is True
        reader.device.write.assert_called_once()

    def test_trigger_qc_9v(self):
        reader = USBReader()
        reader.is_connected = True
        reader.device = MagicMock()
        result = reader.trigger_voltage('qc', 9)
        assert result is True

    def test_trigger_unknown_protocol(self):
        reader = USBReader()
        reader.is_connected = True
        reader.device = MagicMock()
        with pytest.raises(ValueError, match="Unknown protocol"):
            reader.trigger_voltage('unknown_proto', 5)

    def test_trigger_unsupported_voltage(self):
        reader = USBReader()
        reader.is_connected = True
        reader.device = MagicMock()
        with pytest.raises(ValueError, match="Unsupported voltage"):
            reader.trigger_voltage('pd', 7)

    def test_trigger_not_connected(self):
        reader = USBReader()
        with pytest.raises(ConnectionError):
            reader.trigger_voltage('pd', 5)


class TestAdjustQC3Voltage:
    def test_adjust_valid_voltage(self):
        reader = USBReader()
        reader.is_connected = True
        reader.device = MagicMock()
        result = reader.adjust_qc3_voltage(9.0)
        assert result is True
        reader.device.write.assert_called_once()

    def test_adjust_below_minimum(self):
        reader = USBReader()
        reader.is_connected = True
        reader.device = MagicMock()
        with pytest.raises(ValueError, match="3.6V and 12.0V"):
            reader.adjust_qc3_voltage(3.0)

    def test_adjust_above_maximum(self):
        reader = USBReader()
        reader.is_connected = True
        reader.device = MagicMock()
        with pytest.raises(ValueError, match="3.6V and 12.0V"):
            reader.adjust_qc3_voltage(13.0)

    def test_adjust_not_connected(self):
        reader = USBReader()
        with pytest.raises(ConnectionError):
            reader.adjust_qc3_voltage(9.0)
