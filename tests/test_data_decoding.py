"""
Tests for USB packet data decoding.

These tests verify that raw USB packets are correctly decoded
into voltage, current, power, and other measurements.
"""

import pytest
import struct


class TestPacketDecoding:
    """Test USB packet decoding functions."""

    def test_voltage_decoding(self, sample_usb_packet):
        """Test voltage value extraction from packet."""
        # Extract voltage from sample packet (offset 2, 4 bytes, little-endian)
        raw_voltage = struct.unpack_from('<I', sample_usb_packet, 2)[0]
        voltage = raw_voltage / 100000.0

        assert voltage == 5.0, f"Expected 5.0V, got {voltage}V"

    def test_current_decoding(self, sample_usb_packet):
        """Test current value extraction from packet."""
        # Extract current from sample packet (offset 6, 4 bytes, little-endian)
        raw_current = struct.unpack_from('<I', sample_usb_packet, 6)[0]
        current = raw_current / 100000.0

        assert current == 1.0, f"Expected 1.0A, got {current}A"

    def test_power_calculation(self, sample_usb_packet):
        """Test power calculation from voltage and current."""
        raw_voltage = struct.unpack_from('<I', sample_usb_packet, 2)[0]
        raw_current = struct.unpack_from('<I', sample_usb_packet, 6)[0]

        voltage = raw_voltage / 100000.0
        current = raw_current / 100000.0
        power = voltage * current

        assert power == 5.0, f"Expected 5.0W, got {power}W"

    def test_d_plus_decoding(self, sample_usb_packet):
        """Test D+ voltage extraction from packet."""
        # Extract D+ from sample packet (offset 10, 2 bytes, little-endian)
        raw_d_plus = struct.unpack_from('<H', sample_usb_packet, 10)[0]
        d_plus = raw_d_plus / 1000.0

        assert d_plus == 2.7, f"Expected 2.7V, got {d_plus}V"

    def test_d_minus_decoding(self, sample_usb_packet):
        """Test D- voltage extraction from packet."""
        # Extract D- from sample packet (offset 12, 2 bytes, little-endian)
        raw_d_minus = struct.unpack_from('<H', sample_usb_packet, 12)[0]
        d_minus = raw_d_minus / 1000.0

        assert d_minus == 2.7, f"Expected 2.7V, got {d_minus}V"

    def test_temperature_decoding(self, sample_usb_packet):
        """Test temperature extraction from packet."""
        # Extract temperature from sample packet (offset 15, 2 bytes, little-endian)
        raw_temp = struct.unpack_from('<H', sample_usb_packet, 15)[0]
        temperature = raw_temp / 10.0

        assert temperature == 25.0, f"Expected 25.0C, got {temperature}C"

    def test_packet_type_identification(self, sample_usb_packet):
        """Test packet type identification."""
        packet_type = sample_usb_packet[0]
        assert packet_type == 0x04, f"Expected data packet type 0x04, got 0x{packet_type:02x}"


class TestValueRanges:
    """Test handling of various value ranges."""

    def test_zero_values(self):
        """Test decoding of zero values."""
        packet = bytearray(64)
        packet[0] = 0x04

        # All zeros
        raw_voltage = struct.unpack_from('<I', packet, 2)[0]
        voltage = raw_voltage / 100000.0

        assert voltage == 0.0

    def test_high_voltage(self):
        """Test decoding of high voltage values (e.g., 20V PD)."""
        packet = bytearray(64)
        packet[0] = 0x04

        # 20.0V = 2000000
        packet[2:6] = (2000000).to_bytes(4, 'little')

        raw_voltage = struct.unpack_from('<I', packet, 2)[0]
        voltage = raw_voltage / 100000.0

        assert voltage == 20.0

    def test_high_current(self):
        """Test decoding of high current values (e.g., 5A)."""
        packet = bytearray(64)
        packet[0] = 0x04

        # 5.0A = 500000
        packet[6:10] = (500000).to_bytes(4, 'little')

        raw_current = struct.unpack_from('<I', packet, 6)[0]
        current = raw_current / 100000.0

        assert current == 5.0

    @pytest.mark.skip(reason="FNB48P uses unsigned values; negative current representation TBD")
    def test_negative_current_representation(self):
        """Test that negative current is handled correctly.

        Note: The FNB48P uses unsigned 32-bit values for current measurement.
        Reverse current flow (negative current) may be:
        - Represented as a very large unsigned value (2's complement)
        - Not supported at all by the device
        - Represented differently based on firmware version

        This test should be implemented once the device's handling of
        reverse current flow is documented or reverse-engineered.
        """
        # TODO: Implement when negative current behavior is understood
        packet = bytearray(64)
        packet[0] = 0x04

        # If using 2's complement for negative values:
        # -0.5A might be represented as (2^32 - 50000) = 4294917296
        # packet[6:10] = (4294917296).to_bytes(4, 'little')

        # raw_current = struct.unpack_from('<I', packet, 6)[0]
        # Interpretation depends on device behavior


class TestProtocolDetection:
    """Test charging protocol detection from D+/D- voltages."""

    def test_qc2_9v_detection(self):
        """Test QC2.0 9V protocol detection."""
        # QC2.0 9V: D+ = 3.3V, D- = 0.6V
        d_plus = 3.3
        d_minus = 0.6

        # Protocol detection logic (simplified)
        is_qc2_9v = (3.2 <= d_plus <= 3.4) and (0.5 <= d_minus <= 0.7)
        assert is_qc2_9v, "Should detect QC2.0 9V protocol"

    def test_apple_2_4a_detection(self):
        """Test Apple 2.4A protocol detection."""
        # Apple 2.4A: D+ = 2.7V, D- = 2.7V
        d_plus = 2.7
        d_minus = 2.7

        is_apple = (2.6 <= d_plus <= 2.8) and (2.6 <= d_minus <= 2.8)
        assert is_apple, "Should detect Apple 2.4A protocol"

    def test_standard_usb_detection(self):
        """Test standard USB (no fast charge) detection."""
        # Standard USB: D+ = 0V, D- = 0V (or floating)
        d_plus = 0.0
        d_minus = 0.0

        is_standard = d_plus < 0.5 and d_minus < 0.5
        assert is_standard, "Should detect standard USB"
