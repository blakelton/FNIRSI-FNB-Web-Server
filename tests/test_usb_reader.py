"""Tests for device/usb_reader.py"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from device.usb_reader import USBReader


class TestUSBReaderInit:
    def test_default_init(self):
        reader = USBReader()
        assert reader.device is None
        assert reader.is_connected is False
        assert reader.is_reading is False
        assert reader.ep_in is None
        assert reader.ep_out is None
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


class TestUSBReaderConnect:
    @patch('device.usb_reader.usb.util')
    @patch('device.usb_reader.usb.core')
    def test_connect_auto_detect(self, mock_core, mock_util):
        mock_device = MagicMock()
        mock_device.idVendor = 0x2e3c
        mock_device.idProduct = 0x0049

        # usb.core.find returns device on first supported device
        mock_core.find.return_value = mock_device

        # Mock configuration and endpoints
        mock_ep_in = MagicMock()
        mock_ep_out = MagicMock()
        mock_intf = MagicMock()
        mock_cfg = MagicMock()
        mock_cfg.__getitem__ = MagicMock(return_value=mock_intf)
        mock_device.get_active_configuration.return_value = mock_cfg
        mock_device.__iter__ = MagicMock(return_value=iter([]))
        mock_device.is_kernel_driver_active.return_value = False

        mock_util.find_descriptor.side_effect = [mock_ep_out, mock_ep_in]
        mock_util.endpoint_direction.return_value = 0
        mock_util.ENDPOINT_OUT = 0x00
        mock_util.ENDPOINT_IN = 0x80

        reader = USBReader()
        result = reader.connect()

        assert result is True
        assert reader.is_connected is True

    @patch('device.usb_reader.usb.core')
    def test_connect_device_not_found(self, mock_core):
        mock_core.find.return_value = None

        reader = USBReader()
        with pytest.raises(ConnectionError, match="not found"):
            reader.connect()

    @patch('device.usb_reader.usb.util')
    @patch('device.usb_reader.usb.core')
    def test_connect_endpoint_not_found(self, mock_core, mock_util):
        mock_device = MagicMock()
        mock_device.idVendor = 0x2e3c
        mock_device.idProduct = 0x0049
        mock_core.find.return_value = mock_device

        mock_cfg = MagicMock()
        mock_intf = MagicMock()
        mock_cfg.__getitem__ = MagicMock(return_value=mock_intf)
        mock_device.get_active_configuration.return_value = mock_cfg
        mock_device.__iter__ = MagicMock(return_value=iter([]))
        mock_device.is_kernel_driver_active.return_value = False

        # Endpoints not found
        mock_util.find_descriptor.return_value = None

        reader = USBReader()
        with pytest.raises(ConnectionError, match="endpoints"):
            reader.connect()

    @patch('device.usb_reader.usb.util')
    @patch('device.usb_reader.usb.core')
    def test_connect_detects_fnb58_type(self, mock_core, mock_util):
        mock_device = MagicMock()
        mock_device.idVendor = 0x2e3c  # FNB58/FNB48S vendor
        mock_device.idProduct = 0x5558
        mock_core.find.return_value = mock_device

        mock_ep_in = MagicMock()
        mock_ep_out = MagicMock()
        mock_intf = MagicMock()
        mock_cfg = MagicMock()
        mock_cfg.__getitem__ = MagicMock(return_value=mock_intf)
        mock_device.get_active_configuration.return_value = mock_cfg
        mock_device.__iter__ = MagicMock(return_value=iter([]))
        mock_device.is_kernel_driver_active.return_value = False
        mock_util.find_descriptor.side_effect = [mock_ep_out, mock_ep_in]

        reader = USBReader()
        reader.connect()

        assert reader.is_fnb58_or_fnb48s is True

    @patch('device.usb_reader.usb.util')
    @patch('device.usb_reader.usb.core')
    def test_connect_detects_fnb48_type(self, mock_core, mock_util):
        mock_device = MagicMock()
        mock_device.idVendor = 0x0483  # FNB48/C1 vendor
        mock_device.idProduct = 0x003a
        mock_core.find.return_value = mock_device

        mock_ep_in = MagicMock()
        mock_ep_out = MagicMock()
        mock_intf = MagicMock()
        mock_cfg = MagicMock()
        mock_cfg.__getitem__ = MagicMock(return_value=mock_intf)
        mock_device.get_active_configuration.return_value = mock_cfg
        mock_device.__iter__ = MagicMock(return_value=iter([]))
        mock_device.is_kernel_driver_active.return_value = False
        mock_util.find_descriptor.side_effect = [mock_ep_out, mock_ep_in]

        reader = USBReader()
        reader.connect()

        assert reader.is_fnb58_or_fnb48s is False

    @patch('device.usb_reader.usb.util')
    @patch('device.usb_reader.usb.core')
    def test_connect_sends_init_handshake(self, mock_core, mock_util):
        mock_device = MagicMock()
        mock_device.idVendor = 0x2e3c
        mock_device.idProduct = 0x0049
        mock_core.find.return_value = mock_device

        mock_ep_in = MagicMock()
        mock_ep_out = MagicMock()
        mock_intf = MagicMock()
        mock_cfg = MagicMock()
        mock_cfg.__getitem__ = MagicMock(return_value=mock_intf)
        mock_device.get_active_configuration.return_value = mock_cfg
        mock_device.__iter__ = MagicMock(return_value=iter([]))
        mock_device.is_kernel_driver_active.return_value = False
        mock_util.find_descriptor.side_effect = [mock_ep_out, mock_ep_in]

        reader = USBReader()
        reader.connect()

        # Handshake writes to ep_out
        assert mock_ep_out.write.called

    @patch('device.usb_reader.usb.util')
    @patch('device.usb_reader.usb.core')
    def test_connect_reset_failure_continues(self, mock_core, mock_util):
        mock_device = MagicMock()
        mock_device.idVendor = 0x2e3c
        mock_device.idProduct = 0x0049
        mock_core.find.return_value = mock_device
        mock_core.USBError = Exception
        mock_device.reset.side_effect = Exception("reset failed")

        mock_ep_in = MagicMock()
        mock_ep_out = MagicMock()
        mock_intf = MagicMock()
        mock_cfg = MagicMock()
        mock_cfg.__getitem__ = MagicMock(return_value=mock_intf)
        mock_device.get_active_configuration.return_value = mock_cfg
        mock_device.__iter__ = MagicMock(return_value=iter([]))
        mock_device.is_kernel_driver_active.return_value = False
        mock_util.find_descriptor.side_effect = [mock_ep_out, mock_ep_in]

        reader = USBReader()
        result = reader.connect()
        assert result is True


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
    @patch('device.usb_reader.usb.util')
    def test_disconnect_releases_resources(self, mock_util):
        reader = USBReader()
        reader.device = MagicMock()
        reader.is_connected = True
        reader.disconnect()
        mock_util.dispose_resources.assert_called_once_with(reader.device)
        assert reader.is_connected is False

    def test_disconnect_no_device(self):
        reader = USBReader()
        reader.device = None
        reader.disconnect()  # should not raise
        assert reader.is_connected is False


class TestGetDeviceInfo:
    @patch('device.usb_reader.usb.util')
    def test_get_device_info_connected(self, mock_util):
        reader = USBReader()
        reader.device = MagicMock()
        reader.device.idVendor = 0x2e3c
        reader.device.idProduct = 0x0049
        reader.device.iManufacturer = 1
        reader.device.iProduct = 2
        reader.device.iSerialNumber = 3
        mock_util.get_string.return_value = "TestValue"

        info = reader.get_device_info()
        assert info is not None
        assert 'vendor_id' in info
        assert 'product_id' in info
        assert 'manufacturer' in info

    def test_get_device_info_no_device(self):
        reader = USBReader()
        assert reader.get_device_info() is None


class TestTriggerVoltage:
    def test_trigger_pd_5v(self):
        reader = USBReader()
        reader.is_connected = True
        reader.ep_out = MagicMock()
        result = reader.trigger_voltage('pd', 5)
        assert result is True
        reader.ep_out.write.assert_called_once()

    def test_trigger_qc_9v(self):
        reader = USBReader()
        reader.is_connected = True
        reader.ep_out = MagicMock()
        result = reader.trigger_voltage('qc', 9)
        assert result is True

    def test_trigger_unknown_protocol(self):
        reader = USBReader()
        reader.is_connected = True
        reader.ep_out = MagicMock()
        with pytest.raises(ValueError, match="Unknown protocol"):
            reader.trigger_voltage('unknown_proto', 5)

    def test_trigger_unsupported_voltage(self):
        reader = USBReader()
        reader.is_connected = True
        reader.ep_out = MagicMock()
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
        reader.ep_out = MagicMock()
        result = reader.adjust_qc3_voltage(9.0)
        assert result is True
        reader.ep_out.write.assert_called_once()

    def test_adjust_below_minimum(self):
        reader = USBReader()
        reader.is_connected = True
        reader.ep_out = MagicMock()
        with pytest.raises(ValueError, match="3.6V and 12.0V"):
            reader.adjust_qc3_voltage(3.0)

    def test_adjust_above_maximum(self):
        reader = USBReader()
        reader.is_connected = True
        reader.ep_out = MagicMock()
        with pytest.raises(ValueError, match="3.6V and 12.0V"):
            reader.adjust_qc3_voltage(13.0)

    def test_adjust_not_connected(self):
        reader = USBReader()
        with pytest.raises(ConnectionError):
            reader.adjust_qc3_voltage(9.0)
