"""Tests for device/bluetooth_reader.py"""

import pytest
import struct
from unittest.mock import MagicMock, patch
from device.bluetooth_reader import BluetoothReader, crc16_xmodem, build_command


class TestCRC16XMODEM:
    def test_empty_data(self):
        assert crc16_xmodem(b'') == 0

    def test_get_info_command_crc(self):
        # The FNB58 init uses 0xF4 as the low byte for [0xAA, 0x81, 0x00]
        crc = crc16_xmodem(bytes([0xAA, 0x81, 0x00]))
        assert (crc & 0xFF) == 0xF4

    def test_start_command_crc(self):
        # The FNB58 init uses 0xA7 as the low byte for [0xAA, 0x82, 0x00]
        crc = crc16_xmodem(bytes([0xAA, 0x82, 0x00]))
        assert (crc & 0xFF) == 0xA7

    def test_returns_16_bit_value(self):
        crc = crc16_xmodem(b'\x01\x02\x03')
        assert 0 <= crc <= 0xFFFF

    def test_single_byte(self):
        crc = crc16_xmodem(b'\x00')
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_different_data_different_crc(self):
        crc1 = crc16_xmodem(b'\x01')
        crc2 = crc16_xmodem(b'\x02')
        assert crc1 != crc2


class TestBuildCommand:
    def test_build_get_info_command(self):
        cmd = build_command(0x81)
        assert cmd[0] == 0xAA
        assert cmd[1] == 0x81
        assert cmd[2] == 0x00  # length = 0
        assert len(cmd) == 4

    def test_build_start_command(self):
        cmd = build_command(0x82)
        assert cmd[0] == 0xAA
        assert cmd[1] == 0x82
        assert cmd[2] == 0x00
        assert len(cmd) == 4

    def test_build_stop_command(self):
        cmd = build_command(0x84)
        assert cmd[0] == 0xAA
        assert cmd[1] == 0x84

    def test_build_command_with_payload(self):
        cmd = build_command(0x86, [0x01, 0x05])
        assert cmd[0] == 0xAA
        assert cmd[1] == 0x86
        assert cmd[2] == 2  # length
        assert cmd[3] == 0x01
        assert cmd[4] == 0x05
        assert len(cmd) == 6  # header(3) + payload(2) + crc(1)

    def test_crc_is_low_byte(self):
        cmd = build_command(0x81)
        packet_without_crc = cmd[:-1]
        expected_crc_low = crc16_xmodem(packet_without_crc) & 0xFF
        assert cmd[-1] == expected_crc_low

    def test_no_payload_default(self):
        cmd = build_command(0x81)
        assert cmd[2] == 0  # length byte is 0


class TestBluetoothReaderInit:
    def test_default_init(self):
        reader = BluetoothReader()
        assert reader.device_address is None
        assert reader.device_name is None
        assert reader.is_connected is False
        assert reader.is_reading is False
        assert reader.device_type is None
        assert reader.sample_count == 0
        assert reader._voltage == 0.0
        assert reader._current == 0.0

    def test_custom_init(self):
        reader = BluetoothReader(
            device_address='AA:BB:CC:DD:EE:FF',
            device_name='FNB58',
            adapter='hci1'
        )
        assert reader.device_address == 'AA:BB:CC:DD:EE:FF'
        assert reader.device_name == 'FNB58'
        assert reader.adapter == 'hci1'


class TestDeviceTypeDetection:
    def test_is_fnirsi_device_fnb58(self):
        reader = BluetoothReader()
        assert reader._is_fnirsi_device('FNB58-ABCD') is True

    def test_is_fnirsi_device_fnb48(self):
        reader = BluetoothReader()
        assert reader._is_fnirsi_device('FNB48') is True

    def test_is_fnirsi_device_fnb48s(self):
        reader = BluetoothReader()
        assert reader._is_fnirsi_device('FNB48S') is True

    def test_is_fnirsi_device_c1(self):
        reader = BluetoothReader()
        assert reader._is_fnirsi_device('C1') is True

    def test_is_fnirsi_device_unknown(self):
        reader = BluetoothReader()
        assert reader._is_fnirsi_device('RandomDevice') is False

    def test_is_fnirsi_device_none(self):
        reader = BluetoothReader()
        assert reader._is_fnirsi_device(None) is False

    def test_is_fnirsi_device_custom_name(self):
        reader = BluetoothReader(device_name='MyCustomDevice')
        assert reader._is_fnirsi_device('MyCustomDevice-123') is True

    def test_detect_device_type_fnb58(self):
        reader = BluetoothReader()
        assert reader._detect_device_type('FNB58') == 'fnb58'

    def test_detect_device_type_fnb48(self):
        reader = BluetoothReader()
        assert reader._detect_device_type('FNB48S') == 'fnb48'

    def test_detect_device_type_c1(self):
        reader = BluetoothReader()
        assert reader._detect_device_type('C1') == 'fnb48'

    def test_detect_device_type_none(self):
        reader = BluetoothReader()
        assert reader._detect_device_type(None) == 'fnb48'  # default

    def test_detect_device_type_unknown(self):
        reader = BluetoothReader()
        assert reader._detect_device_type('SomeDevice') == 'fnb48'  # default


class TestParseFNB58Data:
    def test_parse_valid_packet(self, bt_fnb58_data_packet):
        reader = BluetoothReader()
        reader.device_type = 'fnb58'
        result = reader._parse_fnb58_data(bt_fnb58_data_packet)
        assert result is not None
        assert result['voltage'] == 5.0
        assert result['current'] == 1.0
        assert result['power'] == 5.0

    def test_parse_short_packet(self, bt_fnb58_short_packet):
        reader = BluetoothReader()
        reader.device_type = 'fnb58'
        result = reader._parse_fnb58_data(bt_fnb58_short_packet)
        assert result is None

    def test_parse_high_voltage_out_of_range(self, bt_fnb58_high_voltage_packet):
        reader = BluetoothReader()
        reader.device_type = 'fnb58'
        result = reader._parse_fnb58_data(bt_fnb58_high_voltage_packet)
        assert result is None  # voltage > 150V

    def test_parse_increments_sample_count(self, bt_fnb58_data_packet):
        reader = BluetoothReader()
        reader.device_type = 'fnb58'
        reader._parse_fnb58_data(bt_fnb58_data_packet)
        assert reader.sample_count == 1
        reader._parse_fnb58_data(bt_fnb58_data_packet)
        assert reader.sample_count == 2

    def test_parse_returns_all_fields(self, bt_fnb58_data_packet):
        reader = BluetoothReader()
        reader.device_type = 'fnb58'
        result = reader._parse_fnb58_data(bt_fnb58_data_packet)
        required = ['timestamp', 'voltage', 'current', 'power', 'dp', 'dn', 'temperature', 'sample']
        for field in required:
            assert field in result


class TestParseFNB48Data:
    def test_parse_cmd04(self, bt_fnb48_cmd04_packet):
        reader = BluetoothReader()
        reader.device_type = 'fnb48'
        result = reader._parse_fnb48_data(bt_fnb48_cmd04_packet)
        assert result is not None
        assert result['voltage'] == 5.0
        assert result['current'] == 1.0
        assert result['power'] == 5.0

    def test_parse_cmd05_updates_temperature(self, bt_fnb48_cmd05_packet):
        reader = BluetoothReader()
        reader.device_type = 'fnb48'
        result = reader._parse_fnb48_data(bt_fnb48_cmd05_packet)
        assert result is None  # cmd05 alone doesn't return a reading
        assert reader._temperature == 35.0

    def test_parse_cmd06_updates_dp_dn(self, bt_fnb48_cmd06_packet):
        reader = BluetoothReader()
        reader.device_type = 'fnb48'
        result = reader._parse_fnb48_data(bt_fnb48_cmd06_packet)
        assert result is None  # cmd06 alone doesn't return a reading
        assert reader._dp == 2.7
        assert reader._dn == 2.7

    def test_parse_cmd07_waveform(self, bt_fnb48_cmd07_packet):
        reader = BluetoothReader()
        reader.device_type = 'fnb48'
        result = reader._parse_fnb48_data(bt_fnb48_cmd07_packet)
        assert result is not None
        assert result['voltage'] == 5.0
        assert result['current'] == 1.0

    def test_parse_concatenated_packets(self, bt_fnb48_cmd05_packet, bt_fnb48_cmd04_packet):
        reader = BluetoothReader()
        reader.device_type = 'fnb48'
        # Concatenate cmd05 (temp) + cmd04 (V/I/P)
        combined = bt_fnb48_cmd05_packet + bt_fnb48_cmd04_packet
        result = reader._parse_fnb48_data(combined)
        assert result is not None
        # Temperature from cmd05 should be incorporated
        assert result['temperature'] == 35.0
        assert result['voltage'] == 5.0

    def test_parse_empty_data(self):
        reader = BluetoothReader()
        reader.device_type = 'fnb48'
        result = reader._parse_fnb48_data(b'')
        assert result is None

    def test_parse_malformed_packet(self):
        reader = BluetoothReader()
        reader.device_type = 'fnb48'
        result = reader._parse_fnb48_data(b'\x01\x02\x03')
        assert result is None

    def test_parse_cmd04_voltage_out_of_range(self):
        reader = BluetoothReader()
        reader.device_type = 'fnb48'
        # Build cmd04 with voltage > 150V
        data = bytearray()
        data.append(0xAA)
        data.append(0x04)
        data.append(12)
        data += struct.pack('<iii', 1600000, 10000, 50000)  # 160V
        data.append(0x00)
        result = reader._parse_fnb48_data(bytes(data))
        # Voltage > 150 means _voltage is NOT updated, so it stays at 0.0
        assert reader._voltage == 0.0


class TestParseDataDispatch:
    def test_dispatch_fnb58(self, bt_fnb58_data_packet):
        reader = BluetoothReader()
        reader.device_type = 'fnb58'
        result = reader._parse_data(bt_fnb58_data_packet)
        assert result is not None
        assert result['voltage'] == 5.0

    def test_dispatch_fnb48(self, bt_fnb48_cmd04_packet):
        reader = BluetoothReader()
        reader.device_type = 'fnb48'
        result = reader._parse_data(bt_fnb48_cmd04_packet)
        assert result is not None
        assert result['voltage'] == 5.0


class TestGetDeviceInfo:
    def test_get_info_with_client(self):
        reader = BluetoothReader()
        reader.client = MagicMock()
        reader.device_address = 'AA:BB:CC:DD:EE:FF'
        reader.device_name = 'FNB48S'
        reader.device_type = 'fnb48'
        info = reader.get_device_info()
        assert info is not None
        assert info['address'] == 'AA:BB:CC:DD:EE:FF'
        assert info['name'] == 'FNB48S'
        assert info['connection_type'] == 'bluetooth'

    def test_get_info_no_client(self):
        reader = BluetoothReader()
        assert reader.get_device_info() is None


class TestBluetoothReaderConstants:
    def test_ble_uuids_defined(self):
        assert BluetoothReader.NOTIFY_UUID == "0000ffe4-0000-1000-8000-00805f9b34fb"
        assert BluetoothReader.WRITE_UUID == "0000ffe9-0000-1000-8000-00805f9b34fb"

    def test_command_constants(self):
        assert BluetoothReader.CMD_GET_INFO == 0x81
        assert BluetoothReader.CMD_START == 0x82
        assert BluetoothReader.CMD_STOP == 0x84
        assert BluetoothReader.CMD_GET_STATUS == 0x85

    def test_supported_devices_list(self):
        assert 'FNB58' in BluetoothReader.SUPPORTED_DEVICES
        assert 'FNB48' in BluetoothReader.SUPPORTED_DEVICES
        assert 'C1' in BluetoothReader.SUPPORTED_DEVICES
