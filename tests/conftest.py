"""
Pytest configuration and fixtures for FNIRSI Web Monitor tests.
"""

import pytest
import struct
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# USB Packet Fixtures
# ============================================================

@pytest.fixture
def usb_data_packet():
    """
    Valid 64-byte USB data packet with 4 samples.

    Matches USBReader._decode_packet() layout:
    - data[0] = 0xAA (start byte)
    - data[1] = 0x04 (data packet type)
    - 4 samples starting at offset 2, each 15 bytes:
      offset+0..3: voltage (4 bytes LE, /100000)
      offset+4..7: current (4 bytes LE, /100000)
      offset+8..9: D+ (2 bytes LE, /1000)
      offset+10..11: D- (2 bytes LE, /1000)
      offset+12: unused
      offset+13..14: temperature (2 bytes LE, /10)

    Sample 0: 5.0V, 1.0A, D+=2.7V, D-=2.7V, 25.0C
    Sample 1: 9.0V, 2.0A, D+=0.6V, D-=0.3V, 30.0C
    Sample 2: 12.0V, 3.0A, D+=0.6V, D-=0.6V, 35.0C
    Sample 3: 20.0V, 5.0A, D+=0.0V, D-=0.0V, 40.0C
    """
    packet = bytearray(64)
    packet[0] = 0xAA
    packet[1] = 0x04  # data packet type

    samples = [
        # (voltage_raw, current_raw, dp_raw, dn_raw, temp_raw)
        (500000, 100000, 2700, 2700, 250),   # 5V, 1A, 2.7V, 2.7V, 25C
        (900000, 200000, 600, 300, 300),      # 9V, 2A, 0.6V, 0.3V, 30C
        (1200000, 300000, 600, 600, 350),     # 12V, 3A, 0.6V, 0.6V, 35C
        (2000000, 500000, 0, 0, 400),         # 20V, 5A, 0V, 0V, 40C
    ]

    for i, (v, c, dp, dn, temp) in enumerate(samples):
        offset = 2 + (15 * i)
        packet[offset:offset+4] = v.to_bytes(4, 'little')
        packet[offset+4:offset+8] = c.to_bytes(4, 'little')
        packet[offset+8:offset+10] = dp.to_bytes(2, 'little')
        packet[offset+10:offset+12] = dn.to_bytes(2, 'little')
        packet[offset+12] = 0x00  # unused
        packet[offset+13:offset+15] = temp.to_bytes(2, 'little')

    return bytes(packet)


@pytest.fixture
def usb_non_data_packet():
    """64-byte USB packet that is NOT a data packet (type != 0x04)."""
    packet = bytearray(64)
    packet[0] = 0xAA
    packet[1] = 0x81  # info response, not data
    return bytes(packet)


@pytest.fixture
def usb_short_packet():
    """Packet shorter than 64 bytes."""
    return bytes(10)


@pytest.fixture
def usb_zero_packet():
    """64-byte data packet with all-zero sample values."""
    packet = bytearray(64)
    packet[0] = 0xAA
    packet[1] = 0x04
    # All remaining bytes are already 0
    return bytes(packet)


# ============================================================
# Bluetooth Packet Fixtures
# ============================================================

@pytest.fixture
def bt_fnb58_data_packet():
    """
    BLE notification packet for FNB58 device.
    FNB58 format: struct.unpack_from('<iii', data, 21), values /10000.
    Encodes: 5.0V, 1.0A, 5.0W
    """
    data = bytearray(40)
    struct.pack_into('<iii', data, 21, 50000, 10000, 50000)
    return bytes(data)


@pytest.fixture
def bt_fnb58_short_packet():
    """FNB58 BLE packet too short to parse (< 33 bytes)."""
    return bytes(20)


@pytest.fixture
def bt_fnb58_high_voltage_packet():
    """FNB58 BLE packet with voltage > 150V (out of range)."""
    data = bytearray(40)
    struct.pack_into('<iii', data, 21, 1600000, 10000, 50000)  # 160V
    return bytes(data)


@pytest.fixture
def bt_fnb48_cmd04_packet():
    """
    FNB48 BLE packet: command 0x04 (main V/I/P data).
    Format: [0xAA][0x04][12][V:4B][I:4B][P:4B][CRC]
    Values: 5.0V, 1.0A, 5.0W (scaled by /10000)
    """
    data = bytearray()
    data.append(0xAA)
    data.append(0x04)
    data.append(12)  # length
    data += struct.pack('<iii', 50000, 10000, 50000)
    data.append(0x00)  # CRC placeholder
    return bytes(data)


@pytest.fixture
def bt_fnb48_cmd05_packet():
    """
    FNB48 BLE packet: command 0x05 (resistance + temperature).
    Format: [0xAA][0x05][7][resistance:4B][sign][temp:2B][CRC]
    Temperature: 35.0C (positive)
    """
    data = bytearray()
    data.append(0xAA)
    data.append(0x05)
    data.append(7)  # length
    data += bytes([0, 0, 0, 0])  # resistance placeholder
    data.append(1)   # sign = positive
    data += struct.pack('<H', 350)  # temp = 35.0C
    data.append(0x00)  # CRC
    return bytes(data)


@pytest.fixture
def bt_fnb48_cmd06_packet():
    """
    FNB48 BLE packet: command 0x06 (D+/D- voltage).
    Format: [0xAA][0x06][6][DN:2B][DP:2B][proto:2B][CRC]
    D-=2.7V, D+=2.7V
    """
    data = bytearray()
    data.append(0xAA)
    data.append(0x06)
    data.append(6)  # length
    data += struct.pack('<HH', 2700, 2700)  # dn=2.7V, dp=2.7V
    data += struct.pack('<H', 0)  # protocol
    data.append(0x00)  # CRC
    return bytes(data)


@pytest.fixture
def bt_fnb48_cmd07_packet():
    """
    FNB48 BLE packet: command 0x07 (waveform data).
    Format: [0xAA][0x07][4][V:2B][I:2B][CRC]
    Values in mV/mA: 5000mV=5.0V, 1000mA=1.0A
    """
    data = bytearray()
    data.append(0xAA)
    data.append(0x07)
    data.append(4)  # length
    data += struct.pack('<HH', 5000, 1000)
    data.append(0x00)  # CRC
    return bytes(data)


# ============================================================
# Reading / Data Fixtures
# ============================================================

@pytest.fixture
def sample_reading():
    """A single reading dict matching the format produced by readers."""
    return {
        'timestamp': '2025-01-09T12:00:00.000000',
        'voltage': 5.0,
        'current': 1.0,
        'power': 5.0,
        'dp': 2.7,
        'dn': 2.7,
        'temperature': 25.0,
        'sample': 0
    }


@pytest.fixture
def sample_readings_list():
    """100 readings simulating a short recording session at ~5V/1A."""
    readings = []
    for i in range(100):
        v = 5.0 + (i % 10) * 0.01  # slight variation
        c = 1.0 + (i % 5) * 0.01
        readings.append({
            'timestamp': f'2025-01-09T12:00:{i:02d}.000000',
            'voltage': round(v, 5),
            'current': round(c, 5),
            'power': round(v * c, 5),
            'dp': 2.7,
            'dn': 2.7,
            'temperature': 25.0,
            'sample': i
        })
    return readings


@pytest.fixture
def charging_phase_readings():
    """Readings that transition: idle -> charging -> idle."""
    readings = []
    # 10 idle readings (low current)
    for i in range(10):
        readings.append({'voltage': 5.0, 'current': 0.01, 'power': 0.05,
                         'dp': 0.0, 'dn': 0.0, 'temperature': 25.0})
    # 20 charging readings (high current)
    for i in range(20):
        readings.append({'voltage': 5.0, 'current': 1.5, 'power': 7.5,
                         'dp': 2.7, 'dn': 2.7, 'temperature': 30.0})
    # 10 idle readings
    for i in range(10):
        readings.append({'voltage': 5.0, 'current': 0.02, 'power': 0.1,
                         'dp': 0.0, 'dn': 0.0, 'temperature': 25.0})
    return readings


@pytest.fixture
def sample_session(sample_readings_list):
    """A complete session object as returned by DeviceManager.stop_recording()."""
    return {
        'start_time': '2025-01-09T12:00:00.000000',
        'end_time': '2025-01-09T12:01:40.000000',
        'data': sample_readings_list,
        'stats': {
            'samples_collected': len(sample_readings_list),
            'max_voltage': 5.09,
            'min_voltage': 5.0,
            'max_current': 1.04,
            'min_current': 1.0,
            'max_power': 5.3,
            'total_energy_wh': 0.0014,
            'total_capacity_ah': 0.00028,
            'avg_voltage': 5.045,
            'avg_current': 1.02,
            'avg_power': 5.15
        },
        'connection_type': 'usb',
        'name': 'Test Session'
    }
