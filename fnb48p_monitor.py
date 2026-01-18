#!/usr/bin/env python3
"""
FNIRSI USB Tester Web Monitor
=============================
Full-featured web interface for FNIRSI USB Power Meters.

Features:
- Real-time voltage, current, power, temperature monitoring
- Protocol auto-detection from D+/D- voltages (20+ protocols)
- Threshold alerts with visual/audio warnings
- Session recording with CSV/JSON export
- Protocol triggering (QC2.0/3.0, PD, AFC, FCP, SCP, VOOC)
- Statistics tracking (min/max/avg, energy, capacity)
- Oscilloscope mode for waveform analysis
- Charge curve plotting with time estimates
- Configurable settings and calibration
- Dark/light theme support
- Dynamic device detection and identification

Supported Devices:
- FNIRSI FNB48P / FNB48S - Premium USB tester with metal housing
- FNIRSI FNB58 - Advanced USB tester with 2.0" display
- FNIRSI FNB48 - Original USB tester (legacy)
- FNIRSI C1 - Compact Type-C PD trigger

Author: Created with Claude Code
License: MIT
"""

# Standard library imports
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

# Third-party imports
import usb.core
import usb.util
from flask import Flask, Response, jsonify, render_template_string, request

# Local module imports
from data.statistics import StatisticsTracker
from data.alerts import AlertManager
from data.buffers import DataBuffer
from storage.session_manager import SessionManager
from storage.settings import SettingsManager

# ============================================================================
# Data Types
# ============================================================================

class ProtocolSignature(NamedTuple):
    """Definition of a charging protocol based on D+/D- voltage ranges."""
    dp_min: float       # Minimum D+ voltage for this protocol
    dp_max: float       # Maximum D+ voltage for this protocol
    dn_min: float       # Minimum D- voltage for this protocol
    dn_max: float       # Maximum D- voltage for this protocol
    name: str           # Short protocol name (e.g., 'QC2.0 9V')
    description: str    # Full description (e.g., 'Qualcomm Quick Charge 9V mode')


# ============================================================================
# USB Reader for FNIRSI USB Power Meters
# ============================================================================

class FNIRSIReader:
    """Full-featured USB reader for FNIRSI USB Power Meters.

    Supported devices:
    - FNB48P / FNB48S: Premium USB tester with metal housing, 1.77" display
    - FNB58: Advanced USB tester with 2.0" display, Bluetooth support
    - FNB48: Original USB tester (older hardware revision)
    - C1: Compact Type-C PD trigger with 1.3" display
    """

    # Supported devices: (vendor_id, product_id, model_name, description)
    SUPPORTED_DEVICES = [
        (0x2e3c, 0x0049, 'FNB48P/S', 'FNIRSI FNB48P/FNB48S USB Tester'),
        (0x2e3c, 0x5558, 'FNB58', 'FNIRSI FNB58 USB Tester'),
        (0x0483, 0x003a, 'FNB48', 'FNIRSI FNB48 USB Tester (legacy)'),
        (0x0483, 0x003b, 'C1', 'FNIRSI C1 Type-C PD Tester'),
    ]

    # Protocol trigger commands (reverse-engineered)
    TRIGGER_COMMANDS = {
        # Quick Charge 2.0
        'qc2_5v':   b"\xaa\xa1\x01\x00",
        'qc2_9v':   b"\xaa\xa1\x02\x00",
        'qc2_12v':  b"\xaa\xa1\x03\x00",
        'qc2_20v':  b"\xaa\xa1\x04\x00",
        # Quick Charge 3.0
        'qc3_5v':   b"\xaa\xa2\x01\x00",
        'qc3_9v':   b"\xaa\xa2\x02\x00",
        'qc3_12v':  b"\xaa\xa2\x03\x00",
        # USB Power Delivery
        'pd_5v':    b"\xaa\xa3\x01\x00",
        'pd_9v':    b"\xaa\xa3\x02\x00",
        'pd_12v':   b"\xaa\xa3\x03\x00",
        'pd_15v':   b"\xaa\xa3\x04\x00",
        'pd_20v':   b"\xaa\xa3\x05\x00",
        # Samsung AFC
        'afc_5v':   b"\xaa\xa4\x01\x00",
        'afc_9v':   b"\xaa\xa4\x02\x00",
        'afc_12v':  b"\xaa\xa4\x03\x00",
        # Huawei FCP
        'fcp_5v':   b"\xaa\xa5\x01\x00",
        'fcp_9v':   b"\xaa\xa5\x02\x00",
        'fcp_12v':  b"\xaa\xa5\x03\x00",
        # Huawei SCP
        'scp_5v':   b"\xaa\xa6\x01\x00",
        'scp_4.5v': b"\xaa\xa6\x02\x00",
        # VOOC/WARP (OPPO/OnePlus)
        'vooc':     b"\xaa\xa7\x01\x00",
        'warp':     b"\xaa\xa7\x02\x00",
        'supervooc': b"\xaa\xa7\x03\x00",
        # Apple
        'apple_2.4a': b"\xaa\xa8\x01\x00",
        'apple_2.1a': b"\xaa\xa8\x02\x00",
    }

    # Protocol detection based on D+/D- voltages
    # Reference: USB Battery Charging Spec 1.2, proprietary protocols
    PROTOCOL_SIGNATURES = [
        # Qualcomm Quick Charge
        ProtocolSignature(2.6, 2.8, 2.6, 2.8, 'QC2.0/3.0', 'Qualcomm Quick Charge handshake'),
        ProtocolSignature(0.5, 0.7, 0.5, 0.7, 'QC2.0 5V', 'Quick Charge 5V mode'),
        ProtocolSignature(3.2, 3.4, 0.5, 0.7, 'QC2.0 9V', 'Quick Charge 9V mode'),
        ProtocolSignature(0.5, 0.7, 3.2, 3.4, 'QC2.0 12V', 'Quick Charge 12V mode'),
        ProtocolSignature(3.2, 3.4, 3.2, 3.4, 'QC2.0 20V', 'Quick Charge 20V mode'),
        # Apple charging modes
        ProtocolSignature(2.7, 2.8, 2.7, 2.8, 'Apple 2.4A', 'Apple 12W iPad charger'),
        ProtocolSignature(2.0, 2.1, 2.7, 2.8, 'Apple 2.1A', 'Apple 10W iPad charger'),
        ProtocolSignature(2.7, 2.8, 2.0, 2.1, 'Apple 1A', 'Apple 5W iPhone charger'),
        ProtocolSignature(2.0, 2.1, 2.0, 2.1, 'Apple 0.5A', 'Apple 2.5W charger'),
        # Samsung
        ProtocolSignature(1.2, 1.3, 1.2, 1.3, 'Samsung AFC', 'Samsung Adaptive Fast Charging'),
        ProtocolSignature(0.9, 1.0, 0.9, 1.0, 'Samsung 2A', 'Samsung 2A standard charging'),
        # USB Battery Charging 1.2 spec
        ProtocolSignature(0.0, 0.1, 0.0, 0.1, 'USB-C PD', 'USB Power Delivery (no D+/D- signaling)'),
        ProtocolSignature(0.4, 0.6, 0.4, 0.6, 'DCP', 'Dedicated Charging Port (D+/D- shorted)'),
        ProtocolSignature(1.7, 1.95, 1.7, 1.95, 'USB SDP', 'Standard Downstream Port (USB 5V)'),
        ProtocolSignature(1.5, 1.7, 1.5, 1.7, 'USB CDP', 'Charging Downstream Port (USB 5V 1.5A)'),
        # Huawei
        ProtocolSignature(2.0, 2.1, 2.0, 2.1, 'Huawei FCP', 'Huawei Fast Charge Protocol'),
        ProtocolSignature(0.8, 0.9, 0.8, 0.9, 'Huawei SCP', 'Huawei Super Charge Protocol'),
        # Other proprietary
        ProtocolSignature(0.3, 0.4, 0.3, 0.4, 'YD/T 1591', 'Chinese telecom standard 1A'),
        ProtocolSignature(2.4, 2.5, 2.4, 2.5, 'Divider 1', 'Voltage divider mode 1'),
        ProtocolSignature(2.9, 3.0, 2.9, 3.0, 'Divider 2', 'Voltage divider mode 2'),
    ]

    # Data packet decoding constants
    # USB packet format: Header + 4 readings of 15 bytes each
    PACKET_HEADER_SIZE = 2
    PACKET_DATA_TYPE = 0x04         # Expected data type identifier
    PACKET_MIN_SIZE = 64            # Minimum valid packet size
    READING_SIZE = 15               # Bytes per reading in packet
    READINGS_PER_PACKET = 4         # Number of readings per packet

    # Scaling factors for raw USB data conversion
    # Raw values are integers that need division to get actual units
    VOLTAGE_SCALE = 100000.0        # Raw value / VOLTAGE_SCALE = Volts
    CURRENT_SCALE = 100000.0        # Raw value / CURRENT_SCALE = Amps
    D_VOLTAGE_SCALE = 1000.0        # D+/D- raw value / D_VOLTAGE_SCALE = Volts
    TEMPERATURE_SCALE = 10.0        # Raw value / TEMPERATURE_SCALE = Celsius

    # Data buffer sizes
    DATA_BUFFER_SIZE = 2000         # Number of readings to keep in history
    WAVEFORM_BUFFER_SIZE = 500      # Number of readings for oscilloscope view

    def __init__(self):
        # USB device state
        self.device = None
        self.ep_in = None
        self.ep_out = None
        self.is_connected = False
        self.is_reading = False
        self.read_thread = None
        self.lock = threading.Lock()
        self.device_info = {}

        # Storage directory
        self.sessions_dir = Path.home() / "fnirsi_sessions"
        self.sessions_dir.mkdir(exist_ok=True)

        # Initialize modular components
        self._settings_mgr = SettingsManager(self.sessions_dir)
        self.settings, alerts_config = self._settings_mgr.load()

        self._stats = StatisticsTracker()
        self._alerts = AlertManager()
        self._alerts.set_config(alerts_config)

        self._data_buffer = DataBuffer(maxlen=self.DATA_BUFFER_SIZE)
        self._waveform_buffer = DataBuffer(maxlen=self.WAVEFORM_BUFFER_SIZE)

        self._session_mgr = SessionManager(self.sessions_dir)

        # Protocol detection state
        self.detected_protocol = None

    # -------------------------------------------------------------------------
    # Backward compatibility properties (for existing code that accesses these)
    # -------------------------------------------------------------------------

    @property
    def alerts(self) -> Dict[str, Any]:
        """Get alert configuration (backward compatibility)."""
        return self._alerts.get_config()

    @alerts.setter
    def alerts(self, value: Dict[str, Any]) -> None:
        """Set alert configuration (backward compatibility)."""
        self._alerts.set_config(value)

    @property
    def active_alerts(self) -> List[Dict[str, str]]:
        """Get active alerts (backward compatibility)."""
        return self._alerts.active_alerts

    @property
    def is_recording(self) -> bool:
        """Get recording state (backward compatibility)."""
        return self._session_mgr.is_recording

    @property
    def recording_data(self) -> List[Dict[str, Any]]:
        """Get recording data (backward compatibility)."""
        return self._session_mgr.recording_data

    @property
    def latest_reading(self) -> Optional[Dict[str, Any]]:
        """Get latest reading (backward compatibility)."""
        return self._data_buffer.get_latest()

    @property
    def data_buffer(self):
        """Get data buffer (backward compatibility)."""
        return self._data_buffer

    def _save_settings(self) -> None:
        """Save settings and alerts to storage (delegates to SettingsManager)."""
        self._settings_mgr.save(self.settings, self._alerts.get_config())

    def connect(self) -> bool:
        """Connect to the FNIRSI USB device."""
        detected_model = None
        detected_description = None

        for vendor_id, product_id, model_name, description in self.SUPPORTED_DEVICES:
            self.device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
            if self.device:
                detected_model = model_name
                detected_description = description
                print(f"Found device: {model_name} (VID=0x{vendor_id:04x} PID=0x{product_id:04x})")
                break

        if not self.device:
            raise ConnectionError("FNIRSI device not found. Make sure it's connected via USB.")

        # Get device info
        try:
            self.device_info = {
                'vendor_id': f"0x{self.device.idVendor:04x}",
                'product_id': f"0x{self.device.idProduct:04x}",
                'model': detected_model or 'Unknown',
                'model_description': detected_description or 'FNIRSI USB Tester',
                'manufacturer': usb.util.get_string(self.device, self.device.iManufacturer) if self.device.iManufacturer else "FNIRSI",
                'product': usb.util.get_string(self.device, self.device.iProduct) if self.device.iProduct else "USB Tester",
                'serial': usb.util.get_string(self.device, self.device.iSerialNumber) if self.device.iSerialNumber else "N/A"
            }
        except (usb.core.USBError, ValueError):
            self.device_info = {
                'vendor_id': 'unknown',
                'product_id': 'unknown',
                'model': detected_model or 'Unknown',
                'model_description': detected_description or 'FNIRSI USB Tester'
            }

        try:
            self.device.reset()
        except usb.core.USBError:
            pass  # Reset may fail on some platforms, non-critical

        for cfg in self.device:
            for intf in cfg:
                if self.device.is_kernel_driver_active(intf.bInterfaceNumber):
                    try:
                        self.device.detach_kernel_driver(intf.bInterfaceNumber)
                    except usb.core.USBError:
                        pass  # Kernel driver detach may fail, try to continue

        try:
            self.device.set_configuration()
        except usb.core.USBError:
            pass  # Configuration may already be set

        cfg = self.device.get_active_configuration()
        intf = cfg[(0, 0)]

        self.ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )
        self.ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
        )

        if not self.ep_in or not self.ep_out:
            raise ConnectionError("Could not find USB endpoints")

        # Init handshake
        self.ep_out.write(b"\xaa\x81" + b"\x00" * 61 + b"\x8e")
        self.ep_out.write(b"\xaa\x82" + b"\x00" * 61 + b"\x96")
        self.ep_out.write(b"\xaa\x82" + b"\x00" * 61 + b"\x96")

        self.is_connected = True
        self._stats.reset()  # Start fresh statistics on connect
        print(f"Connected to {self.device_info.get('product', 'FNIRSI Device')}")
        return True

    def start_reading(self) -> bool:
        """Start the background reading thread."""
        if not self.is_connected:
            return False
        self.is_reading = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        return True

    def _read_loop(self):
        time.sleep(0.1)
        refresh = 1.0
        continue_time = time.time() + refresh
        last_time = time.time()

        while self.is_reading:
            try:
                data = self.ep_in.read(size_or_buffer=64, timeout=5000)
                readings = self._decode_packet(data)

                current_time = time.time()
                dt = current_time - last_time
                last_time = current_time

                with self.lock:
                    for r in readings:
                        # Apply calibration
                        r['voltage'] = (r['voltage'] + self.settings['voltage_offset']) * self.settings['voltage_scale']
                        r['current'] = (r['current'] + self.settings['current_offset']) * self.settings['current_scale']
                        r['power'] = r['voltage'] * r['current']

                        # Store in buffers (using modular components)
                        self._data_buffer.append(r)
                        self._waveform_buffer.append(r)

                        # Update stats (using StatisticsTracker)
                        self._stats.update(r, dt / len(readings) if readings else dt)

                        # Check alerts (using AlertManager)
                        self._alerts.check(r)

                        # Detect protocol
                        self._detect_protocol(r)

                        # Record if active (using SessionManager)
                        self._session_mgr.add_reading(r)

                if time.time() >= continue_time:
                    continue_time = time.time() + refresh
                    self.ep_out.write(b"\xaa\x83" + b"\x00" * 61 + b"\x9e")

            except usb.core.USBError:
                if self.is_reading:
                    time.sleep(0.1)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(0.1)

    def _detect_protocol(self, r):
        dp, dn = r['dp'], r['dn']

        for sig in self.PROTOCOL_SIGNATURES:
            if sig.dp_min <= dp <= sig.dp_max and sig.dn_min <= dn <= sig.dn_max:
                self.detected_protocol = {
                    'name': sig.name,
                    'description': sig.description,
                    'dp': dp,
                    'dn': dn
                }
                return

        # Unknown protocol
        if dp > 0.1 or dn > 0.1:
            self.detected_protocol = {'name': 'Unknown', 'description': f'D+={dp:.2f}V D-={dn:.2f}V', 'dp': dp, 'dn': dn}
        else:
            self.detected_protocol = {'name': 'None', 'description': 'No charging protocol detected', 'dp': dp, 'dn': dn}

    def _decode_packet(self, data):
        readings = []
        timestamp = datetime.now()

        if len(data) < self.PACKET_MIN_SIZE or data[1] != self.PACKET_DATA_TYPE:
            return readings

        for i in range(self.READINGS_PER_PACKET):
            offset = self.PACKET_HEADER_SIZE + (self.READING_SIZE * i)
            if offset + self.READING_SIZE - 1 >= len(data):
                break

            # Decode 32-bit little-endian values for voltage and current
            voltage_raw = (data[offset+3]*256*256*256 + data[offset+2]*256*256 +
                          data[offset+1]*256 + data[offset])
            current_raw = (data[offset+7]*256*256*256 + data[offset+6]*256*256 +
                          data[offset+5]*256 + data[offset+4])
            # Decode 16-bit little-endian values for D+, D-, and temperature
            dp_raw = data[offset+8] + data[offset+9]*256
            dn_raw = data[offset+10] + data[offset+11]*256
            temp_raw = data[offset+13] + data[offset+14]*256

            # Apply scaling factors to convert to physical units
            voltage = voltage_raw / self.VOLTAGE_SCALE
            current = current_raw / self.CURRENT_SCALE
            dp = dp_raw / self.D_VOLTAGE_SCALE
            dn = dn_raw / self.D_VOLTAGE_SCALE
            temp = temp_raw / self.TEMPERATURE_SCALE
            power = voltage * current

            readings.append({
                'timestamp': timestamp.isoformat(),
                'voltage': round(voltage, 5),
                'current': round(current, 5),
                'power': round(power, 5),
                'dp': round(dp, 3),
                'dn': round(dn, 3),
                'temperature': round(temp, 1)
            })

        return readings

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """Get the most recent reading."""
        return self._data_buffer.get_latest()

    def get_recent(self, n: int = 100) -> List[Dict[str, Any]]:
        """Get the n most recent readings."""
        return self._data_buffer.get_recent(n)

    def get_waveform(self, n: int = 500) -> List[Dict[str, Any]]:
        """Get waveform data for oscilloscope view."""
        return self._waveform_buffer.get_recent(n)

    def get_stats(self) -> Dict[str, Any]:
        """Get accumulated statistics for the session."""
        return self._stats.get_stats()

    def reset_stats(self) -> None:
        """Reset accumulated statistics."""
        self._stats.reset()

    def get_alerts(self) -> Dict[str, Any]:
        """Get current alert status and configuration."""
        return self._alerts.get_status()

    def set_alerts(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update alert thresholds configuration."""
        self._alerts.set_config(config)
        self._save_settings()
        return self._alerts.get_config()

    def get_protocol(self) -> Optional[Dict[str, Any]]:
        """Get the currently detected charging protocol."""
        return self.detected_protocol

    def get_device_info(self) -> Dict[str, str]:
        """Get USB device information."""
        return self.device_info

    def get_settings(self) -> Dict[str, Any]:
        """Get current settings."""
        return self.settings

    def set_settings(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update settings."""
        self.settings.update(config)
        self._save_settings()
        return self.settings

    def start_recording(self, name: Optional[str] = None) -> str:
        """Start recording data to a session."""
        self._stats.reset()  # Reset stats for new recording
        return self._session_mgr.start_recording(name)

    def stop_recording(self) -> Dict[str, Any]:
        """Stop recording and save the session."""
        return self._session_mgr.stop_recording(self._stats.get_stats())

    def get_recording_status(self) -> Dict[str, Any]:
        """Get the current recording status."""
        status = self._session_mgr.get_status()
        if status['is_recording']:
            stats = self._stats.get_stats()
            status['duration'] = stats.get('duration_formatted')
        return status

    def export_csv(self, data: Optional[List[Dict[str, Any]]] = None) -> str:
        """Export data as CSV string."""
        if data is None:
            data = self._session_mgr.recording_data if self._session_mgr.is_recording else self._data_buffer.get_all()
        return SessionManager.export_csv(data)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all saved sessions."""
        return self._session_mgr.list_sessions()

    def get_session(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a saved session by name."""
        return self._session_mgr.get_session(name)

    def delete_session(self, name: str) -> bool:
        """Delete a saved session by name."""
        return self._session_mgr.delete_session(name)

    def trigger_protocol(self, protocol: str) -> bool:
        """Trigger a fast charging protocol."""
        if not self.is_connected or not self.ep_out:
            raise ConnectionError("Device not connected")

        if protocol not in self.TRIGGER_COMMANDS:
            raise ValueError(f"Unknown protocol: {protocol}")

        cmd = self.TRIGGER_COMMANDS[protocol]
        padded = cmd + b"\x00" * (64 - len(cmd))
        self.ep_out.write(padded)
        return True

    def get_charge_estimate(self, target_mah: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Estimate charge completion based on current flow."""
        return self._stats.get_charge_estimate(target_mah)

    def stop(self) -> None:
        """Stop reading and clean up."""
        self.is_reading = False
        if self.read_thread:
            self.read_thread.join(timeout=2)


# ============================================================================
# Flask App
# ============================================================================

app = Flask(__name__)
reader = FNIRSIReader()

# Load the HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>FNIRSI USB Tester Monitor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#0f0f1a">
    <link rel="manifest" href="/manifest.json">
    <style>
        :root {
            --bg-primary: #0f0f1a;
            --bg-secondary: #1a1a2e;
            --bg-card: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            --border-color: #2a2a4a;
            --text-primary: #e0e0e0;
            --text-secondary: #888;
            --accent: #4ecca3;
            --voltage-color: #f1c40f;
            --current-color: #3498db;
            --power-color: #e74c3c;
            --temp-color: #9b59b6;
            --dp-color: #1abc9c;
            --energy-color: #e67e22;
            --capacity-color: #2ecc71;
        }
        .light-theme {
            --bg-primary: #f5f5f5;
            --bg-secondary: #ffffff;
            --bg-card: linear-gradient(135deg, #ffffff 0%, #f0f0f0 100%);
            --border-color: #ddd;
            --text-primary: #333;
            --text-secondary: #666;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }

        /* Header */
        header {
            background: var(--bg-card);
            padding: 12px 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }
        .logo { display: flex; align-items: center; gap: 10px; }
        .logo h1 { color: var(--accent); font-size: 1.3rem; }
        .logo .device-info { color: var(--text-secondary); font-size: 0.8rem; }
        .header-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        .status-badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        .status-badge.connected { background: #27ae60; color: white; }
        .status-badge.disconnected { background: #c0392b; color: white; }
        .status-badge.recording { background: #e74c3c; animation: pulse 1s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
        .protocol-badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            background: var(--accent);
            color: #0f0f1a;
        }
        .theme-toggle {
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
        }

        /* Alert banner */
        .alert-banner {
            background: #c0392b;
            color: white;
            padding: 10px 20px;
            display: none;
            align-items: center;
            gap: 10px;
        }
        .alert-banner.active { display: flex; }
        .alert-banner.warning { background: #f39c12; }

        /* Tabs */
        .tabs {
            display: flex;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            overflow-x: auto;
        }
        .tab {
            padding: 12px 20px;
            cursor: pointer;
            border: none;
            background: transparent;
            color: var(--text-secondary);
            font-size: 0.9rem;
            white-space: nowrap;
            transition: all 0.2s;
        }
        .tab:hover { color: var(--accent); }
        .tab.active { color: var(--accent); border-bottom: 2px solid var(--accent); background: rgba(78, 204, 163, 0.1); }

        /* Main content */
        main { padding: 15px; max-width: 1600px; margin: 0 auto; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        /* Cards grid */
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 15px; }
        .grid-6 { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
        .card {
            background: var(--bg-card);
            border-radius: 10px;
            padding: 15px;
            border: 1px solid var(--border-color);
        }
        .card h3 { color: var(--text-secondary); font-size: 0.7rem; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 1px; }
        .card .value { font-size: 1.8rem; font-weight: 700; line-height: 1.2; font-family: 'SF Mono', Monaco, monospace; }
        .card .unit { font-size: 0.9rem; color: var(--text-secondary); margin-left: 2px; }
        .card .subvalue { font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px; }
        .card.voltage .value { color: var(--voltage-color); }
        .card.current .value { color: var(--current-color); }
        .card.power .value { color: var(--power-color); }
        .card.temp .value { color: var(--temp-color); }
        .card.dp .value, .card.dn .value { color: var(--dp-color); }
        .card.energy .value { color: var(--energy-color); }
        .card.capacity .value { color: var(--capacity-color); }
        .card.alert { border-color: #e74c3c; animation: alert-pulse 0.5s infinite; }
        @keyframes alert-pulse { 0%, 100% { border-color: #e74c3c; } 50% { border-color: #c0392b; } }

        /* Chart container */
        .chart-container {
            background: var(--bg-card);
            border-radius: 10px;
            padding: 15px;
            border: 1px solid var(--border-color);
            margin-bottom: 15px;
        }
        .chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 10px; }
        .chart-header h3 { color: var(--accent); font-size: 0.95rem; }
        .chart-controls { display: flex; gap: 8px; flex-wrap: wrap; }
        .chart-btn {
            padding: 4px 10px;
            border: 1px solid var(--border-color);
            background: transparent;
            color: var(--text-primary);
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
        }
        .chart-btn.active { background: var(--accent); color: var(--bg-primary); border-color: var(--accent); }
        canvas { width: 100% !important; height: 250px !important; }

        /* Recording controls */
        .controls-bar {
            background: var(--bg-card);
            border-radius: 10px;
            padding: 12px 15px;
            border: 1px solid var(--border-color);
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .controls-bar h3 { color: var(--accent); font-size: 0.9rem; margin-right: 10px; }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.2s;
        }
        .btn:hover { opacity: 0.9; transform: translateY(-1px); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .btn-success { background: #27ae60; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-primary { background: #3498db; color: white; }
        .btn-secondary { background: #7f8c8d; color: white; }
        .btn-outline {
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-primary);
        }
        .input {
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            background: var(--bg-primary);
            color: var(--text-primary);
            border-radius: 6px;
            font-size: 0.85rem;
        }

        /* Stats panel */
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; }
        .stats-card {
            background: var(--bg-card);
            border-radius: 10px;
            padding: 15px;
            border: 1px solid var(--border-color);
        }
        .stats-card h3 { color: var(--accent); margin-bottom: 12px; font-size: 0.95rem; border-bottom: 1px solid var(--border-color); padding-bottom: 8px; }
        .stat-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--bg-primary); }
        .stat-row:last-child { border-bottom: none; }
        .stat-label { color: var(--text-secondary); font-size: 0.85rem; }
        .stat-value { font-weight: 600; font-family: 'SF Mono', Monaco, monospace; font-size: 0.85rem; }

        /* Protocol section */
        .protocol-section { margin-bottom: 15px; }
        .protocol-section h3 { color: var(--accent); margin-bottom: 10px; font-size: 0.95rem; }
        .protocol-group { margin-bottom: 12px; }
        .protocol-group-title { color: var(--text-secondary); font-size: 0.8rem; margin-bottom: 6px; }
        .protocol-buttons { display: flex; flex-wrap: wrap; gap: 6px; }
        .proto-btn {
            padding: 6px 14px;
            border: 1px solid var(--border-color);
            background: var(--bg-secondary);
            color: var(--text-primary);
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.85rem;
        }
        .proto-btn:hover { background: var(--accent); color: var(--bg-primary); border-color: var(--accent); }
        .proto-btn:active { transform: scale(0.95); }

        /* Sessions list */
        .sessions-list { max-height: 500px; overflow-y: auto; }
        .session-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            background: var(--bg-primary);
            border-radius: 6px;
            margin-bottom: 8px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .session-info h4 { color: var(--accent); margin-bottom: 4px; font-size: 0.9rem; }
        .session-info p { color: var(--text-secondary); font-size: 0.8rem; }
        .session-actions { display: flex; gap: 6px; }
        .session-btn {
            padding: 5px 10px;
            border: 1px solid var(--border-color);
            background: transparent;
            color: var(--text-primary);
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
        }
        .session-btn:hover { background: var(--border-color); }
        .session-btn.delete:hover { background: #e74c3c; border-color: #e74c3c; }

        /* Settings */
        .settings-section { margin-bottom: 20px; }
        .settings-section h3 { color: var(--accent); margin-bottom: 12px; font-size: 0.95rem; }
        .setting-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--border-color);
        }
        .setting-label { color: var(--text-primary); }
        .setting-desc { color: var(--text-secondary); font-size: 0.8rem; }
        .setting-input { width: 120px; text-align: right; }

        /* Charge estimate */
        .charge-estimate {
            background: var(--bg-card);
            border-radius: 10px;
            padding: 15px;
            border: 1px solid var(--border-color);
            margin-bottom: 15px;
        }
        .charge-estimate h3 { color: var(--accent); margin-bottom: 10px; }
        .progress-bar {
            height: 20px;
            background: var(--bg-primary);
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent), #2ecc71);
            border-radius: 10px;
            transition: width 0.5s;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .grid { grid-template-columns: repeat(3, 1fr); }
            .card .value { font-size: 1.4rem; }
            header { padding: 10px 15px; }
            main { padding: 10px; }
        }
        @media (max-width: 480px) {
            .grid { grid-template-columns: repeat(2, 1fr); }
            .tabs { justify-content: flex-start; }
            .tab { padding: 10px 15px; font-size: 0.8rem; }
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <header>
        <div class="logo">
            <h1 id="app-title">FNIRSI Monitor</h1>
            <span class="device-info" id="device-info"></span>
        </div>
        <div class="header-right">
            <span id="protocol-badge" class="protocol-badge" title="Detected charging protocol">Protocol: --</span>
            <span id="rec-badge" class="status-badge recording" style="display:none;">REC</span>
            <span id="status" class="status-badge disconnected">Connecting...</span>
            <button class="theme-toggle" onclick="toggleTheme()">Theme</button>
        </div>
    </header>

    <div id="alert-banner" class="alert-banner">
        <span id="alert-message"></span>
    </div>

    <div class="tabs">
        <button class="tab active" data-tab="monitor">Monitor</button>
        <button class="tab" data-tab="stats">Statistics</button>
        <button class="tab" data-tab="waveform">Waveform</button>
        <button class="tab" data-tab="protocol">Trigger</button>
        <button class="tab" data-tab="sessions">Sessions</button>
        <button class="tab" data-tab="settings">Settings</button>
    </div>

    <main>
        <!-- Monitor Tab -->
        <div id="monitor" class="tab-content active">
            <div class="grid grid-6">
                <div class="card voltage" id="card-voltage">
                    <h3>Voltage</h3>
                    <span id="voltage" class="value">--</span><span class="unit">V</span>
                </div>
                <div class="card current" id="card-current">
                    <h3>Current</h3>
                    <span id="current" class="value">--</span><span class="unit">A</span>
                    <div id="current-ma" class="subvalue"></div>
                </div>
                <div class="card power" id="card-power">
                    <h3>Power</h3>
                    <span id="power" class="value">--</span><span class="unit">W</span>
                </div>
                <div class="card temp" id="card-temp">
                    <h3>Temperature</h3>
                    <span id="temp" class="value">--</span><span class="unit">°C</span>
                </div>
                <div class="card dp">
                    <h3>D+ Voltage</h3>
                    <span id="dp" class="value">--</span><span class="unit">V</span>
                </div>
                <div class="card dn">
                    <h3>D- Voltage</h3>
                    <span id="dn" class="value">--</span><span class="unit">V</span>
                </div>
            </div>

            <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
                <div class="card energy">
                    <h3>Energy</h3>
                    <span id="energy-val" class="value">--</span><span class="unit">mWh</span>
                </div>
                <div class="card capacity">
                    <h3>Capacity</h3>
                    <span id="capacity-val" class="value">--</span><span class="unit">mAh</span>
                </div>
                <div class="card">
                    <h3>Duration</h3>
                    <span id="duration-val" class="value">--</span>
                </div>
            </div>

            <div class="controls-bar">
                <h3>Recording</h3>
                <input type="text" id="session-name" class="input" placeholder="Session name" style="width:150px;">
                <button id="rec-start" class="btn btn-success" onclick="startRecording()">Start</button>
                <button id="rec-stop" class="btn btn-danger" onclick="stopRecording()" disabled>Stop</button>
                <button class="btn btn-primary" onclick="exportCSV()">Export CSV</button>
                <button class="btn btn-secondary" onclick="resetStats()">Reset Stats</button>
            </div>

            <div class="charge-estimate" id="charge-section" style="display:none;">
                <h3>Charge Estimate</h3>
                <div style="display:flex; gap:10px; align-items:center; margin-bottom:10px;">
                    <span>Target capacity:</span>
                    <input type="number" id="target-mah" class="input" placeholder="mAh" style="width:100px;" value="3000">
                    <button class="btn btn-outline" onclick="updateChargeEstimate()">Calculate</button>
                </div>
                <div class="progress-bar"><div id="charge-progress" class="progress-fill" style="width:0%"></div></div>
                <div id="charge-info" style="color:var(--text-secondary);font-size:0.85rem;"></div>
            </div>

            <div class="chart-container">
                <div class="chart-header">
                    <h3>Real-Time Data</h3>
                    <div class="chart-controls">
                        <button class="chart-btn active" data-series="voltage">Voltage</button>
                        <button class="chart-btn active" data-series="current">Current</button>
                        <button class="chart-btn active" data-series="power">Power</button>
                    </div>
                </div>
                <canvas id="mainChart"></canvas>
            </div>
        </div>

        <!-- Statistics Tab -->
        <div id="stats" class="tab-content">
            <div class="stats-grid">
                <div class="stats-card">
                    <h3>Voltage Statistics</h3>
                    <div class="stat-row"><span class="stat-label">Minimum</span><span id="v-min" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Maximum</span><span id="v-max" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Average</span><span id="v-avg" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Range</span><span id="v-range" class="stat-value">--</span></div>
                </div>
                <div class="stats-card">
                    <h3>Current Statistics</h3>
                    <div class="stat-row"><span class="stat-label">Minimum</span><span id="i-min" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Maximum</span><span id="i-max" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Average</span><span id="i-avg" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Peak</span><span id="i-peak" class="stat-value">--</span></div>
                </div>
                <div class="stats-card">
                    <h3>Power Statistics</h3>
                    <div class="stat-row"><span class="stat-label">Minimum</span><span id="p-min" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Maximum</span><span id="p-max" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Average</span><span id="p-avg" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Peak</span><span id="p-peak" class="stat-value">--</span></div>
                </div>
                <div class="stats-card">
                    <h3>Energy & Capacity</h3>
                    <div class="stat-row"><span class="stat-label">Energy (Wh)</span><span id="energy-wh" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Energy (mWh)</span><span id="energy-mwh" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Capacity (Ah)</span><span id="capacity-ah" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Capacity (mAh)</span><span id="capacity-mah" class="stat-value">--</span></div>
                </div>
                <div class="stats-card">
                    <h3>Session Info</h3>
                    <div class="stat-row"><span class="stat-label">Duration</span><span id="duration" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Samples</span><span id="samples" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Sample Rate</span><span id="sample-rate" class="stat-value">~100 Hz</span></div>
                    <div class="stat-row"><span class="stat-label">Start Time</span><span id="start-time" class="stat-value">--</span></div>
                </div>
                <div class="stats-card">
                    <h3>Protocol Detection</h3>
                    <div class="stat-row"><span class="stat-label">Detected</span><span id="proto-name" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Description</span><span id="proto-desc" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">D+ Voltage</span><span id="proto-dp" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">D- Voltage</span><span id="proto-dn" class="stat-value">--</span></div>
                </div>
            </div>
        </div>

        <!-- Waveform Tab -->
        <div id="waveform" class="tab-content">
            <div class="chart-container" style="height:400px;">
                <div class="chart-header">
                    <h3>Oscilloscope View</h3>
                    <div class="chart-controls">
                        <button class="chart-btn" onclick="setWaveformMode('voltage')">Voltage</button>
                        <button class="chart-btn active" onclick="setWaveformMode('current')">Current</button>
                        <button class="chart-btn" onclick="setWaveformMode('power')">Power</button>
                        <span style="margin-left:10px;color:var(--text-secondary);">Points:</span>
                        <select id="waveform-points" class="input" style="width:80px;" onchange="updateWaveformPoints()">
                            <option value="100">100</option>
                            <option value="200">200</option>
                            <option value="500" selected>500</option>
                        </select>
                    </div>
                </div>
                <canvas id="waveformChart" style="height:350px !important;"></canvas>
            </div>
        </div>

        <!-- Protocol Trigger Tab -->
        <div id="protocol" class="tab-content">
            <div class="protocol-section">
                <h3>Fast Charging Protocol Trigger</h3>
                <p style="color:var(--text-secondary);margin-bottom:15px;font-size:0.85rem;">
                    Trigger fast charging protocols to test charger capabilities. Ensure your charger supports the selected protocol.
                </p>

                <div class="protocol-group">
                    <div class="protocol-group-title">Quick Charge 2.0</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('qc2_5v')">5V</button>
                        <button class="proto-btn" onclick="trigger('qc2_9v')">9V</button>
                        <button class="proto-btn" onclick="trigger('qc2_12v')">12V</button>
                        <button class="proto-btn" onclick="trigger('qc2_20v')">20V</button>
                    </div>
                </div>

                <div class="protocol-group">
                    <div class="protocol-group-title">Quick Charge 3.0</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('qc3_5v')">5V</button>
                        <button class="proto-btn" onclick="trigger('qc3_9v')">9V</button>
                        <button class="proto-btn" onclick="trigger('qc3_12v')">12V</button>
                    </div>
                </div>

                <div class="protocol-group">
                    <div class="protocol-group-title">USB Power Delivery (PD)</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('pd_5v')">5V</button>
                        <button class="proto-btn" onclick="trigger('pd_9v')">9V</button>
                        <button class="proto-btn" onclick="trigger('pd_12v')">12V</button>
                        <button class="proto-btn" onclick="trigger('pd_15v')">15V</button>
                        <button class="proto-btn" onclick="trigger('pd_20v')">20V</button>
                    </div>
                </div>

                <div class="protocol-group">
                    <div class="protocol-group-title">Samsung AFC (Adaptive Fast Charging)</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('afc_5v')">5V</button>
                        <button class="proto-btn" onclick="trigger('afc_9v')">9V</button>
                        <button class="proto-btn" onclick="trigger('afc_12v')">12V</button>
                    </div>
                </div>

                <div class="protocol-group">
                    <div class="protocol-group-title">Huawei FCP (Fast Charge Protocol)</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('fcp_5v')">5V</button>
                        <button class="proto-btn" onclick="trigger('fcp_9v')">9V</button>
                        <button class="proto-btn" onclick="trigger('fcp_12v')">12V</button>
                    </div>
                </div>

                <div class="protocol-group">
                    <div class="protocol-group-title">Huawei SCP (Super Charge Protocol)</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('scp_5v')">5V</button>
                        <button class="proto-btn" onclick="trigger('scp_4.5v')">4.5V</button>
                    </div>
                </div>

                <div class="protocol-group">
                    <div class="protocol-group-title">OPPO/OnePlus VOOC</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('vooc')">VOOC</button>
                        <button class="proto-btn" onclick="trigger('warp')">WARP</button>
                        <button class="proto-btn" onclick="trigger('supervooc')">SuperVOOC</button>
                    </div>
                </div>

                <div class="protocol-group">
                    <div class="protocol-group-title">Apple</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('apple_2.4a')">2.4A (12W)</button>
                        <button class="proto-btn" onclick="trigger('apple_2.1a')">2.1A (10W)</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Sessions Tab -->
        <div id="sessions" class="tab-content">
            <div class="controls-bar">
                <h3>Saved Sessions</h3>
                <button class="btn btn-outline" onclick="loadSessions()">Refresh</button>
                <span style="color:var(--text-secondary);font-size:0.85rem;" id="sessions-path"></span>
            </div>
            <div id="sessions-list" class="sessions-list">
                <p style="color:var(--text-secondary);">Loading sessions...</p>
            </div>
        </div>

        <!-- Settings Tab -->
        <div id="settings" class="tab-content">
            <div class="stats-grid">
                <div class="stats-card">
                    <h3>Alert Thresholds</h3>
                    <div class="setting-row">
                        <div><div class="setting-label">Max Voltage</div><div class="setting-desc">Alert when exceeded</div></div>
                        <input type="number" id="alert-v-max" class="input setting-input" value="25" step="0.1"> V
                    </div>
                    <div class="setting-row">
                        <div><div class="setting-label">Max Current</div><div class="setting-desc">Alert when exceeded</div></div>
                        <input type="number" id="alert-i-max" class="input setting-input" value="6" step="0.1"> A
                    </div>
                    <div class="setting-row">
                        <div><div class="setting-label">Max Power</div><div class="setting-desc">Alert when exceeded</div></div>
                        <input type="number" id="alert-p-max" class="input setting-input" value="100" step="1"> W
                    </div>
                    <div class="setting-row">
                        <div><div class="setting-label">Max Temperature</div><div class="setting-desc">Alert when exceeded</div></div>
                        <input type="number" id="alert-t-max" class="input setting-input" value="80" step="1"> °C
                    </div>
                    <div class="setting-row">
                        <div><div class="setting-label">Enable Alerts</div></div>
                        <input type="checkbox" id="alert-enabled" checked>
                    </div>
                    <button class="btn btn-primary" onclick="saveAlerts()" style="margin-top:10px;">Save Alerts</button>
                </div>

                <div class="stats-card">
                    <h3>Calibration</h3>
                    <div class="setting-row">
                        <div><div class="setting-label">Voltage Offset</div><div class="setting-desc">Add to reading</div></div>
                        <input type="number" id="cal-v-offset" class="input setting-input" value="0" step="0.001"> V
                    </div>
                    <div class="setting-row">
                        <div><div class="setting-label">Voltage Scale</div><div class="setting-desc">Multiply reading</div></div>
                        <input type="number" id="cal-v-scale" class="input setting-input" value="1" step="0.001">
                    </div>
                    <div class="setting-row">
                        <div><div class="setting-label">Current Offset</div><div class="setting-desc">Add to reading</div></div>
                        <input type="number" id="cal-i-offset" class="input setting-input" value="0" step="0.0001"> A
                    </div>
                    <div class="setting-row">
                        <div><div class="setting-label">Current Scale</div><div class="setting-desc">Multiply reading</div></div>
                        <input type="number" id="cal-i-scale" class="input setting-input" value="1" step="0.001">
                    </div>
                    <button class="btn btn-primary" onclick="saveCalibration()" style="margin-top:10px;">Save Calibration</button>
                </div>

                <div class="stats-card">
                    <h3>Device Info</h3>
                    <div class="stat-row"><span class="stat-label">Model</span><span id="dev-model" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Description</span><span id="dev-model-desc" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Vendor ID</span><span id="dev-vid" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Product ID</span><span id="dev-pid" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Manufacturer</span><span id="dev-mfr" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Product</span><span id="dev-prod" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Serial</span><span id="dev-serial" class="stat-value">--</span></div>
                </div>
            </div>
        </div>
    </main>

    <script>
        // State
        let theme = localStorage.getItem('theme') || 'dark';
        let chartSeries = {voltage: true, current: true, power: true};
        let waveformMode = 'current';
        let waveformPoints = 500;

        // Apply theme
        if (theme === 'light') document.body.classList.add('light-theme');

        // Charts
        const maxPoints = 150;
        const chartData = {labels: [], voltage: [], current: [], power: []};

        const mainCtx = document.getElementById('mainChart').getContext('2d');
        const mainChart = new Chart(mainCtx, {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: [
                    {label: 'Voltage (V)', data: chartData.voltage, borderColor: '#f1c40f', borderWidth: 2, tension: 0.2, pointRadius: 0, yAxisID: 'y'},
                    {label: 'Current (A)', data: chartData.current, borderColor: '#3498db', borderWidth: 2, tension: 0.2, pointRadius: 0, yAxisID: 'y1'},
                    {label: 'Power (W)', data: chartData.power, borderColor: '#e74c3c', borderWidth: 2, tension: 0.2, pointRadius: 0, yAxisID: 'y2'}
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: {intersect: false, mode: 'index'},
                scales: {
                    x: {display: false},
                    y: {type: 'linear', position: 'left', grid: {color: '#2a2a4a'}, ticks: {color: '#888'}},
                    y1: {type: 'linear', position: 'right', grid: {drawOnChartArea: false}, ticks: {color: '#888'}},
                    y2: {type: 'linear', position: 'right', grid: {drawOnChartArea: false}, ticks: {color: '#888'}, display: false}
                },
                plugins: {legend: {labels: {color: '#e0e0e0', usePointStyle: true}}},
                animation: {duration: 0}
            }
        });

        const waveCtx = document.getElementById('waveformChart').getContext('2d');
        const waveChart = new Chart(waveCtx, {
            type: 'line',
            data: {labels: [], datasets: [{label: 'Current (A)', data: [], borderColor: '#3498db', borderWidth: 1.5, tension: 0, pointRadius: 0, fill: true, backgroundColor: 'rgba(52, 152, 219, 0.1)'}]},
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {x: {display: false}, y: {grid: {color: '#2a2a4a'}, ticks: {color: '#888'}}},
                plugins: {legend: {display: false}},
                animation: {duration: 0}
            }
        });

        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById(tab.dataset.tab).classList.add('active');
                if (tab.dataset.tab === 'sessions') loadSessions();
                if (tab.dataset.tab === 'settings') loadSettings();
            });
        });

        // Chart series toggle
        document.querySelectorAll('.chart-btn[data-series]').forEach(btn => {
            btn.addEventListener('click', () => {
                const series = btn.dataset.series;
                chartSeries[series] = !chartSeries[series];
                btn.classList.toggle('active');
                const idx = series === 'voltage' ? 0 : series === 'current' ? 1 : 2;
                mainChart.data.datasets[idx].hidden = !chartSeries[series];
                mainChart.update('none');
            });
        });

        // Theme toggle
        function toggleTheme() {
            theme = theme === 'dark' ? 'light' : 'dark';
            document.body.classList.toggle('light-theme');
            localStorage.setItem('theme', theme);
        }

        // Fetch data
        async function fetchData() {
            try {
                const res = await fetch('/api/latest');
                if (!res.ok) throw new Error();
                const d = await res.json();

                document.getElementById('status').className = 'status-badge connected';
                document.getElementById('status').textContent = 'Connected';

                document.getElementById('voltage').textContent = d.voltage.toFixed(3);
                document.getElementById('current').textContent = d.current.toFixed(4);
                document.getElementById('current-ma').textContent = (d.current * 1000).toFixed(1) + ' mA';
                document.getElementById('power').textContent = d.power.toFixed(3);
                document.getElementById('temp').textContent = d.temperature.toFixed(1);
                document.getElementById('dp').textContent = d.dp.toFixed(3);
                document.getElementById('dn').textContent = d.dn.toFixed(3);

                // Chart
                chartData.labels.push('');
                chartData.voltage.push(d.voltage);
                chartData.current.push(d.current);
                chartData.power.push(d.power);
                while (chartData.labels.length > maxPoints) {
                    chartData.labels.shift();
                    chartData.voltage.shift();
                    chartData.current.shift();
                    chartData.power.shift();
                }
                mainChart.update('none');

                // Check alerts
                checkAlerts();
            } catch (e) {
                document.getElementById('status').className = 'status-badge disconnected';
                document.getElementById('status').textContent = 'Disconnected';
            }
        }

        async function fetchStats() {
            try {
                const res = await fetch('/api/stats');
                if (!res.ok) return;
                const s = await res.json();

                document.getElementById('energy-val').textContent = s.energy_mwh.toFixed(2);
                document.getElementById('capacity-val').textContent = s.capacity_mah.toFixed(2);
                document.getElementById('duration-val').textContent = s.duration_formatted;

                document.getElementById('v-min').textContent = s.voltage.min.toFixed(3) + ' V';
                document.getElementById('v-max').textContent = s.voltage.max.toFixed(3) + ' V';
                document.getElementById('v-avg').textContent = s.voltage.avg.toFixed(3) + ' V';
                document.getElementById('v-range').textContent = (s.voltage.max - s.voltage.min).toFixed(3) + ' V';

                document.getElementById('i-min').textContent = (s.current.min * 1000).toFixed(1) + ' mA';
                document.getElementById('i-max').textContent = (s.current.max * 1000).toFixed(1) + ' mA';
                document.getElementById('i-avg').textContent = (s.current.avg * 1000).toFixed(1) + ' mA';
                document.getElementById('i-peak').textContent = (s.current.max * 1000).toFixed(1) + ' mA';

                document.getElementById('p-min').textContent = s.power.min.toFixed(3) + ' W';
                document.getElementById('p-max').textContent = s.power.max.toFixed(3) + ' W';
                document.getElementById('p-avg').textContent = s.power.avg.toFixed(3) + ' W';
                document.getElementById('p-peak').textContent = s.power.max.toFixed(3) + ' W';

                document.getElementById('energy-wh').textContent = s.energy_wh.toFixed(6) + ' Wh';
                document.getElementById('energy-mwh').textContent = s.energy_mwh.toFixed(3) + ' mWh';
                document.getElementById('capacity-ah').textContent = s.capacity_ah.toFixed(6) + ' Ah';
                document.getElementById('capacity-mah').textContent = s.capacity_mah.toFixed(3) + ' mAh';
                document.getElementById('duration').textContent = s.duration_formatted;
                document.getElementById('samples').textContent = s.samples.toLocaleString();
                if (s.start_time) document.getElementById('start-time').textContent = new Date(s.start_time).toLocaleString();
            } catch (e) {}
        }

        async function fetchProtocol() {
            try {
                const res = await fetch('/api/protocol');
                if (!res.ok) return;
                const p = await res.json();
                if (p && p.name) {
                    const badge = document.getElementById('protocol-badge');
                    badge.textContent = 'Protocol: ' + p.name;
                    badge.title = p.description + ' | D+=' + p.dp.toFixed(2) + 'V D-=' + p.dn.toFixed(2) + 'V';
                    document.getElementById('proto-name').textContent = p.name;
                    document.getElementById('proto-desc').textContent = p.description;
                    document.getElementById('proto-dp').textContent = p.dp.toFixed(3) + ' V';
                    document.getElementById('proto-dn').textContent = p.dn.toFixed(3) + ' V';
                }
            } catch (e) {}
        }

        async function fetchWaveform() {
            try {
                const res = await fetch('/api/waveform?points=' + waveformPoints);
                if (!res.ok) return;
                const data = await res.json();
                if (data.length === 0) return;

                const values = data.map(d => d[waveformMode]);
                const labels = data.map((_, i) => i);

                waveChart.data.labels = labels;
                waveChart.data.datasets[0].data = values;
                waveChart.data.datasets[0].label = waveformMode.charAt(0).toUpperCase() + waveformMode.slice(1);
                waveChart.data.datasets[0].borderColor = waveformMode === 'voltage' ? '#f1c40f' : waveformMode === 'current' ? '#3498db' : '#e74c3c';
                waveChart.update('none');
            } catch (e) {}
        }

        async function checkAlerts() {
            try {
                const res = await fetch('/api/alerts');
                if (!res.ok) return;
                const a = await res.json();
                const banner = document.getElementById('alert-banner');
                if (a.active && a.active.length > 0) {
                    banner.classList.add('active');
                    banner.classList.toggle('warning', a.active[0].type === 'warning');
                    document.getElementById('alert-message').textContent = a.active.map(x => x.message).join(' | ');
                    // Highlight cards
                    document.querySelectorAll('.card').forEach(c => c.classList.remove('alert'));
                    a.active.forEach(alert => {
                        if (alert.message.includes('voltage')) document.getElementById('card-voltage').classList.add('alert');
                        if (alert.message.includes('current')) document.getElementById('card-current').classList.add('alert');
                        if (alert.message.includes('power')) document.getElementById('card-power').classList.add('alert');
                        if (alert.message.includes('temp')) document.getElementById('card-temp').classList.add('alert');
                    });
                } else {
                    banner.classList.remove('active');
                    document.querySelectorAll('.card').forEach(c => c.classList.remove('alert'));
                }
            } catch (e) {}
        }

        async function checkRecording() {
            try {
                const res = await fetch('/api/recording/status');
                const s = await res.json();
                const badge = document.getElementById('rec-badge');
                if (s.is_recording) {
                    badge.style.display = 'inline';
                    badge.textContent = 'REC ' + s.samples;
                    document.getElementById('rec-start').disabled = true;
                    document.getElementById('rec-stop').disabled = false;
                    document.getElementById('charge-section').style.display = 'block';
                } else {
                    badge.style.display = 'none';
                    document.getElementById('rec-start').disabled = false;
                    document.getElementById('rec-stop').disabled = true;
                }
            } catch (e) {}
        }

        // Actions
        async function startRecording() {
            const name = document.getElementById('session-name').value || undefined;
            await fetch('/api/recording/start', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name})});
            checkRecording();
        }

        async function stopRecording() {
            const res = await fetch('/api/recording/stop', {method: 'POST'});
            const session = await res.json();
            alert('Saved: ' + session.name + ' (' + session.samples + ' samples)');
            checkRecording();
        }

        async function resetStats() {
            await fetch('/api/stats/reset', {method: 'POST'});
            fetchStats();
        }

        function exportCSV() {
            window.location.href = '/api/export/csv';
        }

        async function trigger(protocol) {
            try {
                const res = await fetch('/api/trigger/' + protocol, {method: 'POST'});
                const result = await res.json();
                if (result.success) {
                    event.target.style.background = '#27ae60';
                    setTimeout(() => event.target.style.background = '', 500);
                } else {
                    alert('Failed: ' + result.error);
                }
            } catch (e) {
                alert('Error: ' + e.message);
            }
        }

        async function loadSessions() {
            try {
                const res = await fetch('/api/sessions');
                const sessions = await res.json();
                const list = document.getElementById('sessions-list');
                if (sessions.length === 0) {
                    list.innerHTML = '<p style="color:var(--text-secondary);">No sessions yet.</p>';
                    return;
                }
                list.innerHTML = sessions.map(s => `
                    <div class="session-item">
                        <div class="session-info">
                            <h4>${s.name}</h4>
                            <p>${s.samples} samples - ${s.start_time ? new Date(s.start_time).toLocaleString() : 'Unknown'}</p>
                        </div>
                        <div class="session-actions">
                            <button class="session-btn" onclick="downloadSession('${s.name}', 'json')">JSON</button>
                            <button class="session-btn" onclick="downloadSession('${s.name}', 'csv')">CSV</button>
                            <button class="session-btn delete" onclick="deleteSession('${s.name}')">Delete</button>
                        </div>
                    </div>
                `).join('');
            } catch (e) {}
        }

        function downloadSession(name, format) {
            window.location.href = '/api/session/' + name + '/' + format;
        }

        async function deleteSession(name) {
            if (!confirm('Delete session ' + name + '?')) return;
            await fetch('/api/session/' + name, {method: 'DELETE'});
            loadSessions();
        }

        async function loadSettings() {
            try {
                const [alertRes, settingsRes, deviceRes] = await Promise.all([
                    fetch('/api/alerts'),
                    fetch('/api/settings'),
                    fetch('/api/device')
                ]);
                const alerts = await alertRes.json();
                const settings = await settingsRes.json();
                const device = await deviceRes.json();

                document.getElementById('alert-v-max').value = alerts.config.voltage_max;
                document.getElementById('alert-i-max').value = alerts.config.current_max;
                document.getElementById('alert-p-max').value = alerts.config.power_max;
                document.getElementById('alert-t-max').value = alerts.config.temp_max;
                document.getElementById('alert-enabled').checked = alerts.config.enabled;

                document.getElementById('cal-v-offset').value = settings.voltage_offset;
                document.getElementById('cal-v-scale').value = settings.voltage_scale;
                document.getElementById('cal-i-offset').value = settings.current_offset;
                document.getElementById('cal-i-scale').value = settings.current_scale;

                document.getElementById('dev-model').textContent = device.model || '--';
                document.getElementById('dev-model-desc').textContent = device.model_description || '--';
                document.getElementById('dev-vid').textContent = device.vendor_id;
                document.getElementById('dev-pid').textContent = device.product_id;
                document.getElementById('dev-mfr').textContent = device.manufacturer;
                document.getElementById('dev-prod').textContent = device.product;
                document.getElementById('dev-serial').textContent = device.serial;

                // Update app title and device info with model name
                const modelName = device.model || 'FNIRSI';
                document.getElementById('app-title').textContent = modelName + ' Monitor';
                document.getElementById('device-info').textContent = device.product + ' (' + device.serial + ')';
                document.title = 'FNIRSI ' + modelName + ' Monitor';
            } catch (e) {}
        }

        async function saveAlerts() {
            await fetch('/api/alerts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    voltage_max: parseFloat(document.getElementById('alert-v-max').value),
                    current_max: parseFloat(document.getElementById('alert-i-max').value),
                    power_max: parseFloat(document.getElementById('alert-p-max').value),
                    temp_max: parseFloat(document.getElementById('alert-t-max').value),
                    enabled: document.getElementById('alert-enabled').checked
                })
            });
            alert('Alerts saved');
        }

        async function saveCalibration() {
            await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    voltage_offset: parseFloat(document.getElementById('cal-v-offset').value),
                    voltage_scale: parseFloat(document.getElementById('cal-v-scale').value),
                    current_offset: parseFloat(document.getElementById('cal-i-offset').value),
                    current_scale: parseFloat(document.getElementById('cal-i-scale').value)
                })
            });
            alert('Calibration saved');
        }

        function setWaveformMode(mode) {
            waveformMode = mode;
            document.querySelectorAll('#waveform .chart-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
        }

        function updateWaveformPoints() {
            waveformPoints = parseInt(document.getElementById('waveform-points').value);
        }

        async function updateChargeEstimate() {
            const target = parseInt(document.getElementById('target-mah').value);
            if (!target) return;
            try {
                const res = await fetch('/api/charge-estimate?target_mah=' + target);
                const est = await res.json();
                if (est) {
                    document.getElementById('charge-progress').style.width = (est.percent || 0) + '%';
                    document.getElementById('charge-info').innerHTML = est.complete ?
                        'Charging complete!' :
                        `${est.charged_mah} / ${est.target_mah} mAh (${est.percent}%) | ${est.avg_current_ma} mA avg | ETA: ${est.eta} (${est.remaining_time})`;
                }
            } catch (e) {}
        }

        // Polling
        setInterval(fetchData, 100);
        setInterval(fetchStats, 1000);
        setInterval(fetchProtocol, 2000);
        setInterval(checkRecording, 1000);
        setInterval(fetchWaveform, 200);
        setInterval(updateChargeEstimate, 5000);

        fetchData();
        fetchStats();
        fetchProtocol();
        checkRecording();
        loadSettings();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/manifest.json')
def manifest():
    device_info = reader.get_device_info()
    model = device_info.get('model', 'FNIRSI')
    return jsonify({
        "name": f"FNIRSI {model} Monitor",
        "short_name": model,
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f0f1a",
        "theme_color": "#4ecca3"
    })

@app.route('/api/latest')
def api_latest():
    reading = reader.get_latest()
    if reading:
        return jsonify(reading)
    return jsonify({'error': 'No data'}), 404

@app.route('/api/recent')
def api_recent():
    n = request.args.get('points', 100, type=int)
    return jsonify(reader.get_recent(n))

@app.route('/api/waveform')
def api_waveform():
    n = request.args.get('points', 500, type=int)
    return jsonify(reader.get_waveform(n))

@app.route('/api/stats')
def api_stats():
    return jsonify(reader.get_stats())

@app.route('/api/stats/reset', methods=['POST'])
def api_reset_stats():
    reader.reset_stats()
    return jsonify({'success': True})

@app.route('/api/alerts', methods=['GET', 'POST'])
def api_alerts():
    if request.method == 'POST':
        reader.set_alerts(request.json)
    return jsonify(reader.get_alerts())

@app.route('/api/protocol')
def api_protocol():
    return jsonify(reader.get_protocol())

@app.route('/api/device')
def api_device():
    return jsonify(reader.get_device_info())

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'POST':
        reader.set_settings(request.json)
    return jsonify(reader.get_settings())

@app.route('/api/recording/start', methods=['POST'])
def api_start_recording():
    data = request.json or {}
    name = reader.start_recording(data.get('name'))
    return jsonify({'success': True, 'name': name})

@app.route('/api/recording/stop', methods=['POST'])
def api_stop_recording():
    session = reader.stop_recording()
    return jsonify(session)

@app.route('/api/recording/status')
def api_recording_status():
    return jsonify(reader.get_recording_status())

@app.route('/api/export/csv')
def api_export_csv():
    csv_data = reader.export_csv()
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=fnirsi_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )

@app.route('/api/sessions')
def api_sessions():
    return jsonify(reader.list_sessions())

@app.route('/api/session/<name>/json')
def api_session_json(name):
    session = reader.get_session(name)
    if session:
        return Response(
            json.dumps(session, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={name}.json'}
        )
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/session/<name>/csv')
def api_session_csv(name):
    session = reader.get_session(name)
    if session and session.get('data'):
        csv_data = reader.export_csv(session['data'])
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={name}.csv'}
        )
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/session/<name>', methods=['DELETE'])
def api_delete_session(name):
    if reader.delete_session(name):
        return jsonify({'success': True})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/trigger/<protocol>', methods=['POST'])
def api_trigger(protocol):
    try:
        reader.trigger_protocol(protocol)
        return jsonify({'success': True, 'protocol': protocol})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/charge-estimate')
def api_charge_estimate():
    target = request.args.get('target_mah', type=int)
    est = reader.get_charge_estimate(target)
    if est:
        return jsonify(est)
    return jsonify({'error': 'Insufficient data'}), 400


def main():
    print()
    print("=" * 60)
    print("  FNIRSI USB Tester Web Monitor")
    print("  Supports: FNB48P/S, FNB58, FNB48, C1")
    print("=" * 60)

    try:
        reader.connect()
        reader.start_reading()
        print()
        print(f"  Device: {reader.device_info.get('product', 'Unknown')}")
        print(f"  Serial: {reader.device_info.get('serial', 'N/A')}")
        print()
        print("  Open: http://localhost:5002")
        print()
        print("  Features:")
        print("    - Real-time monitoring with charts")
        print("    - Protocol auto-detection")
        print("    - Threshold alerts")
        print("    - Session recording (CSV/JSON)")
        print("    - Protocol triggering")
        print("    - Oscilloscope waveform view")
        print("    - Charge estimation")
        print("    - Calibration settings")
        print()
        print("  Press Ctrl+C to stop")
        print("=" * 60)
        print()

        app.run(host='0.0.0.0', port=5002, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reader.stop()


if __name__ == '__main__':
    main()
