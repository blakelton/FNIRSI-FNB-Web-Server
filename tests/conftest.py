"""
Pytest configuration and fixtures for FNIRSI Web Monitor tests.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_usb_packet():
    """
    Sample USB data packet from FNB48P device.

    Format: 64 bytes
    - Byte 0: Packet type (0x04 for data)
    - Byte 1: Reserved
    - Bytes 2-61: 4 samples of 15 bytes each
    - Bytes 62-63: Reserved
    """
    # Create a sample packet with known values
    # Sample 1: 5.0V, 1.0A, D+=2.7V, D-=2.7V, Temp=25.0C
    packet = bytearray(64)
    packet[0] = 0x04  # Data packet type

    # Sample 1 at offset 2
    # Voltage: 5.0V = 500000 = 0x0007A120
    packet[2:6] = (500000).to_bytes(4, 'little')
    # Current: 1.0A = 100000 = 0x000186A0
    packet[6:10] = (100000).to_bytes(4, 'little')
    # D+: 2.7V = 2700 = 0x0A8C
    packet[10:12] = (2700).to_bytes(2, 'little')
    # D-: 2.7V = 2700 = 0x0A8C
    packet[12:14] = (2700).to_bytes(2, 'little')
    # Reserved byte
    packet[14] = 0x00
    # Temperature: 25.0C = 250 = 0x00FA
    packet[15:17] = (250).to_bytes(2, 'little')

    return bytes(packet)


@pytest.fixture
def sample_reading():
    """Sample decoded reading dictionary.

    Note: D+/D- fields use 'dp'/'dn' to match USB tester terminology
    and actual API response format.
    """
    return {
        'voltage': 5.0,
        'current': 1.0,
        'power': 5.0,
        'dp': 2.7,
        'dn': 2.7,
        'temperature': 25.0,
        'timestamp': '2025-01-09T12:00:00.000000'
    }


@pytest.fixture
def mock_usb_device(mocker):
    """Mock USB device for testing without hardware."""
    mock_device = mocker.MagicMock()
    mock_device.idVendor = 0x2e3c
    mock_device.idProduct = 0x0049
    mock_device.manufacturer = "FNIRSI"
    mock_device.product = "FNB48P"
    return mock_device
