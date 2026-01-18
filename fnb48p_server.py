#!/usr/bin/env python3
"""
FNIRSI FNB48P Full-Featured Web Monitor
- Real-time monitoring with charts
- Session recording with CSV/JSON export
- Protocol triggering (QC2.0/3.0, PD, AFC, FCP, SCP)
- Statistics tracking (min/max/avg, energy, capacity)
- Dark theme UI
"""

import sys
import time
import threading
import json
import csv
import io
import os
from datetime import datetime
from collections import deque
from flask import Flask, jsonify, render_template_string, request, Response

import usb.core
import usb.util

# === USB Reader for FNB48P ===
class FNB48PReader:
    """Full-featured USB reader for FNIRSI FNB48P"""

    SUPPORTED_DEVICES = [
        (0x2e3c, 0x0049),  # FNIRSI FNB48P / FNB48S
        (0x2e3c, 0x5558),  # FNIRSI FNB58
        (0x0483, 0x003a),  # FNIRSI FNB48 (older)
        (0x0483, 0x003b),  # FNIRSI C1
    ]

    # Protocol trigger commands
    TRIGGER_COMMANDS = {
        'qc2_5v':  b"\xaa\xa1\x01\x00",
        'qc2_9v':  b"\xaa\xa1\x02\x00",
        'qc2_12v': b"\xaa\xa1\x03\x00",
        'qc2_20v': b"\xaa\xa1\x04\x00",
        'qc3_5v':  b"\xaa\xa2\x01\x00",
        'qc3_9v':  b"\xaa\xa2\x02\x00",
        'qc3_12v': b"\xaa\xa2\x03\x00",
        'pd_5v':   b"\xaa\xa3\x01\x00",
        'pd_9v':   b"\xaa\xa3\x02\x00",
        'pd_12v':  b"\xaa\xa3\x03\x00",
        'pd_15v':  b"\xaa\xa3\x04\x00",
        'pd_20v':  b"\xaa\xa3\x05\x00",
        'afc_5v':  b"\xaa\xa4\x01\x00",
        'afc_9v':  b"\xaa\xa4\x02\x00",
        'afc_12v': b"\xaa\xa4\x03\x00",
        'fcp_5v':  b"\xaa\xa5\x01\x00",
        'fcp_9v':  b"\xaa\xa5\x02\x00",
        'fcp_12v': b"\xaa\xa5\x03\x00",
        'scp_5v':  b"\xaa\xa6\x01\x00",
        'scp_4.5v': b"\xaa\xa6\x02\x00",
    }

    def __init__(self):
        self.device = None
        self.ep_in = None
        self.ep_out = None
        self.is_connected = False
        self.is_reading = False
        self.read_thread = None
        self.data_buffer = deque(maxlen=1000)
        self.latest_reading = None
        self.lock = threading.Lock()

        # Recording
        self.is_recording = False
        self.recording_data = []
        self.recording_start_time = None
        self.recording_name = None

        # Statistics
        self.stats = self._empty_stats()

        # Sessions storage
        self.sessions_dir = os.path.expanduser("~/fnirsi_sessions")
        os.makedirs(self.sessions_dir, exist_ok=True)

    def _empty_stats(self):
        return {
            'samples': 0,
            'voltage_min': float('inf'),
            'voltage_max': 0,
            'voltage_sum': 0,
            'current_min': float('inf'),
            'current_max': 0,
            'current_sum': 0,
            'power_min': float('inf'),
            'power_max': 0,
            'power_sum': 0,
            'energy_wh': 0,
            'capacity_ah': 0,
            'duration_s': 0,
        }

    def connect(self):
        for vendor_id, product_id in self.SUPPORTED_DEVICES:
            self.device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
            if self.device:
                print(f"Found device: VID=0x{vendor_id:04x} PID=0x{product_id:04x}")
                break

        if not self.device:
            raise ConnectionError("FNIRSI device not found")

        try:
            self.device.reset()
        except:
            pass

        for cfg in self.device:
            for intf in cfg:
                if self.device.is_kernel_driver_active(intf.bInterfaceNumber):
                    try:
                        self.device.detach_kernel_driver(intf.bInterfaceNumber)
                    except:
                        pass

        try:
            self.device.set_configuration()
        except:
            pass

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
        print("Connected to FNIRSI FNB48P")
        return True

    def start_reading(self):
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
                        self.data_buffer.append(r)
                        self.latest_reading = r

                        # Update stats
                        self._update_stats(r, dt / len(readings) if readings else dt)

                        # Record if active
                        if self.is_recording:
                            self.recording_data.append(r)

                if time.time() >= continue_time:
                    continue_time = time.time() + refresh
                    self.ep_out.write(b"\xaa\x83" + b"\x00" * 61 + b"\x9e")

            except usb.core.USBError:
                if self.is_reading:
                    time.sleep(0.1)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(0.1)

    def _update_stats(self, r, dt):
        self.stats['samples'] += 1
        self.stats['voltage_min'] = min(self.stats['voltage_min'], r['voltage'])
        self.stats['voltage_max'] = max(self.stats['voltage_max'], r['voltage'])
        self.stats['voltage_sum'] += r['voltage']
        self.stats['current_min'] = min(self.stats['current_min'], r['current'])
        self.stats['current_max'] = max(self.stats['current_max'], r['current'])
        self.stats['current_sum'] += r['current']
        self.stats['power_min'] = min(self.stats['power_min'], r['power'])
        self.stats['power_max'] = max(self.stats['power_max'], r['power'])
        self.stats['power_sum'] += r['power']
        self.stats['energy_wh'] += (r['power'] * dt) / 3600
        self.stats['capacity_ah'] += (r['current'] * dt) / 3600
        self.stats['duration_s'] += dt

    def _decode_packet(self, data):
        readings = []
        timestamp = datetime.now()

        if len(data) < 64 or data[1] != 0x04:
            return readings

        for i in range(4):
            offset = 2 + (15 * i)
            if offset + 14 >= len(data):
                break

            voltage = (data[offset+3]*256*256*256 + data[offset+2]*256*256 +
                      data[offset+1]*256 + data[offset]) / 100000.0
            current = (data[offset+7]*256*256*256 + data[offset+6]*256*256 +
                      data[offset+5]*256 + data[offset+4]) / 100000.0
            dp = (data[offset+8] + data[offset+9]*256) / 1000.0
            dn = (data[offset+10] + data[offset+11]*256) / 1000.0
            temp = (data[offset+13] + data[offset+14]*256) / 10.0
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

    def get_latest(self):
        with self.lock:
            return self.latest_reading

    def get_recent(self, n=100):
        with self.lock:
            return list(self.data_buffer)[-n:]

    def get_stats(self):
        with self.lock:
            s = self.stats.copy()
            n = s['samples'] if s['samples'] > 0 else 1
            return {
                'samples': s['samples'],
                'voltage': {
                    'min': round(s['voltage_min'], 4) if s['voltage_min'] != float('inf') else 0,
                    'max': round(s['voltage_max'], 4),
                    'avg': round(s['voltage_sum'] / n, 4)
                },
                'current': {
                    'min': round(s['current_min'], 5) if s['current_min'] != float('inf') else 0,
                    'max': round(s['current_max'], 5),
                    'avg': round(s['current_sum'] / n, 5)
                },
                'power': {
                    'min': round(s['power_min'], 4) if s['power_min'] != float('inf') else 0,
                    'max': round(s['power_max'], 4),
                    'avg': round(s['power_sum'] / n, 4)
                },
                'energy_wh': round(s['energy_wh'], 6),
                'energy_mwh': round(s['energy_wh'] * 1000, 3),
                'capacity_ah': round(s['capacity_ah'], 6),
                'capacity_mah': round(s['capacity_ah'] * 1000, 3),
                'duration_s': round(s['duration_s'], 1),
                'duration_formatted': self._format_duration(s['duration_s'])
            }

    def _format_duration(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        elif m > 0:
            return f"{m}m {s}s"
        return f"{s}s"

    def reset_stats(self):
        with self.lock:
            self.stats = self._empty_stats()

    def start_recording(self, name=None):
        with self.lock:
            self.is_recording = True
            self.recording_data = []
            self.recording_start_time = datetime.now()
            self.recording_name = name or f"session_{self.recording_start_time.strftime('%Y%m%d_%H%M%S')}"
            self.stats = self._empty_stats()  # Reset stats for recording
        return self.recording_name

    def stop_recording(self):
        with self.lock:
            self.is_recording = False
            session = {
                'name': self.recording_name,
                'start_time': self.recording_start_time.isoformat() if self.recording_start_time else None,
                'end_time': datetime.now().isoformat(),
                'samples': len(self.recording_data),
                'stats': self.get_stats(),
                'data': self.recording_data.copy()
            }

            # Save to file
            filename = os.path.join(self.sessions_dir, f"{self.recording_name}.json")
            with open(filename, 'w') as f:
                json.dump(session, f, indent=2)

            return session

    def get_recording_status(self):
        with self.lock:
            return {
                'is_recording': self.is_recording,
                'name': self.recording_name,
                'samples': len(self.recording_data),
                'start_time': self.recording_start_time.isoformat() if self.recording_start_time else None
            }

    def export_csv(self, data=None):
        if data is None:
            with self.lock:
                data = self.recording_data.copy() if self.recording_data else list(self.data_buffer)

        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        return output.getvalue()

    def list_sessions(self):
        sessions = []
        for f in os.listdir(self.sessions_dir):
            if f.endswith('.json'):
                filepath = os.path.join(self.sessions_dir, f)
                try:
                    with open(filepath) as file:
                        data = json.load(file)
                        sessions.append({
                            'name': data.get('name', f[:-5]),
                            'start_time': data.get('start_time'),
                            'end_time': data.get('end_time'),
                            'samples': data.get('samples', 0),
                            'filename': f
                        })
                except:
                    pass
        return sorted(sessions, key=lambda x: x.get('start_time', ''), reverse=True)

    def get_session(self, name):
        filename = os.path.join(self.sessions_dir, f"{name}.json")
        if os.path.exists(filename):
            with open(filename) as f:
                return json.load(f)
        return None

    def trigger_protocol(self, protocol):
        if not self.is_connected or not self.ep_out:
            raise ConnectionError("Device not connected")

        if protocol not in self.TRIGGER_COMMANDS:
            raise ValueError(f"Unknown protocol: {protocol}")

        cmd = self.TRIGGER_COMMANDS[protocol]
        padded = cmd + b"\x00" * (64 - len(cmd))
        self.ep_out.write(padded)
        return True

    def stop(self):
        self.is_reading = False
        if self.read_thread:
            self.read_thread.join(timeout=2)


# === Flask App ===
app = Flask(__name__)
reader = FNB48PReader()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>FNIRSI FNB48P Monitor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0f0f1a; color: #e0e0e0; min-height: 100vh;
        }

        /* Header */
        header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 15px 20px;
            border-bottom: 1px solid #2a2a4a;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        header h1 { color: #4ecca3; font-size: 1.4rem; }
        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }
        .status-badge.connected { background: #27ae60; color: white; }
        .status-badge.disconnected { background: #c0392b; color: white; }
        .status-badge.recording { background: #e74c3c; animation: pulse 1s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }

        /* Tabs */
        .tabs {
            display: flex;
            background: #16213e;
            border-bottom: 1px solid #2a2a4a;
        }
        .tab {
            padding: 12px 24px;
            cursor: pointer;
            border: none;
            background: transparent;
            color: #888;
            font-size: 0.95rem;
            transition: all 0.2s;
        }
        .tab:hover { color: #4ecca3; }
        .tab.active { color: #4ecca3; border-bottom: 2px solid #4ecca3; background: rgba(78, 204, 163, 0.1); }

        /* Main content */
        main { padding: 20px; max-width: 1400px; margin: 0 auto; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        /* Cards grid */
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .card {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 12px;
            padding: 18px;
            border: 1px solid #2a2a4a;
        }
        .card h3 { color: #888; font-size: 0.75rem; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
        .card .value { font-size: 2rem; font-weight: 700; line-height: 1.2; }
        .card .unit { font-size: 1rem; color: #666; margin-left: 4px; }
        .card.voltage .value { color: #f1c40f; }
        .card.current .value { color: #3498db; }
        .card.power .value { color: #e74c3c; }
        .card.temp .value { color: #9b59b6; }
        .card.dp .value, .card.dn .value { color: #1abc9c; }
        .card.energy .value { color: #e67e22; }
        .card.capacity .value { color: #2ecc71; }

        /* Chart container */
        .chart-container {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #2a2a4a;
            margin-bottom: 20px;
        }
        .chart-container h3 { color: #4ecca3; margin-bottom: 15px; font-size: 1rem; }
        canvas { width: 100% !important; height: 280px !important; }

        /* Stats panel */
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .stats-card {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #2a2a4a;
        }
        .stats-card h3 { color: #4ecca3; margin-bottom: 15px; font-size: 1rem; border-bottom: 1px solid #2a2a4a; padding-bottom: 10px; }
        .stat-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1a1a2e; }
        .stat-row:last-child { border-bottom: none; }
        .stat-label { color: #888; }
        .stat-value { font-weight: 600; font-family: monospace; }

        /* Protocol buttons */
        .protocol-section { margin-bottom: 20px; }
        .protocol-section h3 { color: #4ecca3; margin-bottom: 12px; font-size: 1rem; }
        .protocol-group { margin-bottom: 15px; }
        .protocol-group-title { color: #888; font-size: 0.85rem; margin-bottom: 8px; }
        .protocol-buttons { display: flex; flex-wrap: wrap; gap: 8px; }
        .proto-btn {
            padding: 8px 16px;
            border: 1px solid #3a3a5a;
            background: #1a1a2e;
            color: #e0e0e0;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.9rem;
        }
        .proto-btn:hover { background: #4ecca3; color: #0f0f1a; border-color: #4ecca3; }
        .proto-btn:active { transform: scale(0.95); }

        /* Recording controls */
        .recording-controls {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #2a2a4a;
            margin-bottom: 20px;
        }
        .recording-controls h3 { color: #4ecca3; margin-bottom: 15px; }
        .rec-buttons { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
        .rec-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.95rem;
            font-weight: 500;
            transition: all 0.2s;
        }
        .rec-btn.start { background: #27ae60; color: white; }
        .rec-btn.stop { background: #e74c3c; color: white; }
        .rec-btn.export { background: #3498db; color: white; }
        .rec-btn.reset { background: #7f8c8d; color: white; }
        .rec-btn:hover { opacity: 0.9; transform: translateY(-1px); }
        .rec-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .rec-input {
            padding: 10px 15px;
            border: 1px solid #3a3a5a;
            background: #0f0f1a;
            color: #e0e0e0;
            border-radius: 8px;
            font-size: 0.95rem;
        }

        /* Sessions list */
        .sessions-list { max-height: 400px; overflow-y: auto; }
        .session-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 15px;
            background: #0f0f1a;
            border-radius: 8px;
            margin-bottom: 8px;
        }
        .session-info h4 { color: #4ecca3; margin-bottom: 4px; }
        .session-info p { color: #888; font-size: 0.85rem; }
        .session-actions { display: flex; gap: 8px; }
        .session-btn {
            padding: 6px 12px;
            border: 1px solid #3a3a5a;
            background: transparent;
            color: #e0e0e0;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85rem;
        }
        .session-btn:hover { background: #3a3a5a; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <header>
        <h1>FNIRSI FNB48P USB Power Monitor</h1>
        <div>
            <span id="rec-badge" class="status-badge" style="display:none; margin-right:10px;">REC</span>
            <span id="status" class="status-badge disconnected">Connecting...</span>
        </div>
    </header>

    <div class="tabs">
        <button class="tab active" data-tab="monitor">Monitor</button>
        <button class="tab" data-tab="stats">Statistics</button>
        <button class="tab" data-tab="protocol">Protocol Trigger</button>
        <button class="tab" data-tab="sessions">Sessions</button>
    </div>

    <main>
        <!-- Monitor Tab -->
        <div id="monitor" class="tab-content active">
            <div class="grid">
                <div class="card voltage">
                    <h3>Voltage</h3>
                    <span id="voltage" class="value">--</span><span class="unit">V</span>
                </div>
                <div class="card current">
                    <h3>Current</h3>
                    <span id="current" class="value">--</span><span class="unit">A</span>
                </div>
                <div class="card power">
                    <h3>Power</h3>
                    <span id="power" class="value">--</span><span class="unit">W</span>
                </div>
                <div class="card temp">
                    <h3>Temperature</h3>
                    <span id="temp" class="value">--</span><span class="unit">C</span>
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

            <div class="recording-controls">
                <h3>Recording</h3>
                <div class="rec-buttons">
                    <input type="text" id="session-name" class="rec-input" placeholder="Session name (optional)">
                    <button id="rec-start" class="rec-btn start" onclick="startRecording()">Start Recording</button>
                    <button id="rec-stop" class="rec-btn stop" onclick="stopRecording()" disabled>Stop Recording</button>
                    <button class="rec-btn export" onclick="exportCSV()">Export CSV</button>
                    <button class="rec-btn reset" onclick="resetStats()">Reset Stats</button>
                </div>
            </div>

            <div class="chart-container">
                <h3>Real-Time Data</h3>
                <canvas id="powerChart"></canvas>
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
                </div>
                <div class="stats-card">
                    <h3>Current Statistics</h3>
                    <div class="stat-row"><span class="stat-label">Minimum</span><span id="i-min" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Maximum</span><span id="i-max" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Average</span><span id="i-avg" class="stat-value">--</span></div>
                </div>
                <div class="stats-card">
                    <h3>Power Statistics</h3>
                    <div class="stat-row"><span class="stat-label">Minimum</span><span id="p-min" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Maximum</span><span id="p-max" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Average</span><span id="p-avg" class="stat-value">--</span></div>
                </div>
                <div class="stats-card">
                    <h3>Energy & Capacity</h3>
                    <div class="stat-row"><span class="stat-label">Energy</span><span id="energy" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Capacity</span><span id="capacity" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Duration</span><span id="duration" class="stat-value">--</span></div>
                    <div class="stat-row"><span class="stat-label">Samples</span><span id="samples" class="stat-value">--</span></div>
                </div>
            </div>
        </div>

        <!-- Protocol Trigger Tab -->
        <div id="protocol" class="tab-content">
            <div class="protocol-section">
                <h3>Fast Charging Protocol Trigger</h3>
                <p style="color:#888; margin-bottom:20px;">Trigger fast charging protocols to test charger capabilities. Make sure your charger supports the protocol before triggering.</p>

                <div class="protocol-group">
                    <div class="protocol-group-title">Quick Charge 2.0</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('qc2_5v')">QC2.0 5V</button>
                        <button class="proto-btn" onclick="trigger('qc2_9v')">QC2.0 9V</button>
                        <button class="proto-btn" onclick="trigger('qc2_12v')">QC2.0 12V</button>
                        <button class="proto-btn" onclick="trigger('qc2_20v')">QC2.0 20V</button>
                    </div>
                </div>

                <div class="protocol-group">
                    <div class="protocol-group-title">Quick Charge 3.0</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('qc3_5v')">QC3.0 5V</button>
                        <button class="proto-btn" onclick="trigger('qc3_9v')">QC3.0 9V</button>
                        <button class="proto-btn" onclick="trigger('qc3_12v')">QC3.0 12V</button>
                    </div>
                </div>

                <div class="protocol-group">
                    <div class="protocol-group-title">USB Power Delivery (PD)</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('pd_5v')">PD 5V</button>
                        <button class="proto-btn" onclick="trigger('pd_9v')">PD 9V</button>
                        <button class="proto-btn" onclick="trigger('pd_12v')">PD 12V</button>
                        <button class="proto-btn" onclick="trigger('pd_15v')">PD 15V</button>
                        <button class="proto-btn" onclick="trigger('pd_20v')">PD 20V</button>
                    </div>
                </div>

                <div class="protocol-group">
                    <div class="protocol-group-title">Samsung AFC</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('afc_5v')">AFC 5V</button>
                        <button class="proto-btn" onclick="trigger('afc_9v')">AFC 9V</button>
                        <button class="proto-btn" onclick="trigger('afc_12v')">AFC 12V</button>
                    </div>
                </div>

                <div class="protocol-group">
                    <div class="protocol-group-title">Huawei FCP</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('fcp_5v')">FCP 5V</button>
                        <button class="proto-btn" onclick="trigger('fcp_9v')">FCP 9V</button>
                        <button class="proto-btn" onclick="trigger('fcp_12v')">FCP 12V</button>
                    </div>
                </div>

                <div class="protocol-group">
                    <div class="protocol-group-title">Huawei SCP</div>
                    <div class="protocol-buttons">
                        <button class="proto-btn" onclick="trigger('scp_5v')">SCP 5V</button>
                        <button class="proto-btn" onclick="trigger('scp_4.5v')">SCP 4.5V</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Sessions Tab -->
        <div id="sessions" class="tab-content">
            <div class="recording-controls">
                <h3>Saved Sessions</h3>
                <button class="rec-btn export" onclick="loadSessions()" style="margin-bottom:15px;">Refresh List</button>
                <div id="sessions-list" class="sessions-list">
                    <p style="color:#888;">Loading sessions...</p>
                </div>
            </div>
        </div>
    </main>

    <script>
        // Chart setup
        const maxPoints = 150;
        const chartData = { labels: [], voltage: [], current: [], power: [] };

        const ctx = document.getElementById('powerChart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: [
                    { label: 'Voltage (V)', data: chartData.voltage, borderColor: '#f1c40f', borderWidth: 2, tension: 0.2, pointRadius: 0, yAxisID: 'y' },
                    { label: 'Current (A)', data: chartData.current, borderColor: '#3498db', borderWidth: 2, tension: 0.2, pointRadius: 0, yAxisID: 'y1' },
                    { label: 'Power (W)', data: chartData.power, borderColor: '#e74c3c', borderWidth: 2, tension: 0.2, pointRadius: 0, yAxisID: 'y2' }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: 'index' },
                scales: {
                    x: { display: false },
                    y: { type: 'linear', position: 'left', title: { display: true, text: 'Voltage (V)', color: '#f1c40f' }, grid: { color: '#2a2a4a' }, ticks: { color: '#888' } },
                    y1: { type: 'linear', position: 'right', title: { display: true, text: 'Current (A)', color: '#3498db' }, grid: { drawOnChartArea: false }, ticks: { color: '#888' } },
                    y2: { type: 'linear', position: 'right', title: { display: true, text: 'Power (W)', color: '#e74c3c' }, grid: { drawOnChartArea: false }, ticks: { color: '#888' }, offset: true }
                },
                plugins: { legend: { labels: { color: '#e0e0e0', usePointStyle: true } } },
                animation: { duration: 0 }
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
            });
        });

        // Fetch live data
        async function fetchData() {
            try {
                const res = await fetch('/api/latest');
                if (!res.ok) throw new Error('No data');
                const d = await res.json();

                document.getElementById('status').className = 'status-badge connected';
                document.getElementById('status').textContent = 'Connected';

                document.getElementById('voltage').textContent = d.voltage.toFixed(3);
                document.getElementById('current').textContent = d.current.toFixed(4);
                document.getElementById('power').textContent = d.power.toFixed(3);
                document.getElementById('temp').textContent = d.temperature.toFixed(1);
                document.getElementById('dp').textContent = d.dp.toFixed(3);
                document.getElementById('dn').textContent = d.dn.toFixed(3);

                // Update chart
                const time = new Date().toLocaleTimeString();
                chartData.labels.push(time);
                chartData.voltage.push(d.voltage);
                chartData.current.push(d.current);
                chartData.power.push(d.power);

                while (chartData.labels.length > maxPoints) {
                    chartData.labels.shift();
                    chartData.voltage.shift();
                    chartData.current.shift();
                    chartData.power.shift();
                }
                chart.update('none');
            } catch (e) {
                document.getElementById('status').className = 'status-badge disconnected';
                document.getElementById('status').textContent = 'Disconnected';
            }
        }

        // Fetch stats
        async function fetchStats() {
            try {
                const res = await fetch('/api/stats');
                if (!res.ok) return;
                const s = await res.json();

                document.getElementById('v-min').textContent = s.voltage.min.toFixed(3) + ' V';
                document.getElementById('v-max').textContent = s.voltage.max.toFixed(3) + ' V';
                document.getElementById('v-avg').textContent = s.voltage.avg.toFixed(3) + ' V';
                document.getElementById('i-min').textContent = (s.current.min * 1000).toFixed(2) + ' mA';
                document.getElementById('i-max').textContent = (s.current.max * 1000).toFixed(2) + ' mA';
                document.getElementById('i-avg').textContent = (s.current.avg * 1000).toFixed(2) + ' mA';
                document.getElementById('p-min').textContent = s.power.min.toFixed(3) + ' W';
                document.getElementById('p-max').textContent = s.power.max.toFixed(3) + ' W';
                document.getElementById('p-avg').textContent = s.power.avg.toFixed(3) + ' W';
                document.getElementById('energy').textContent = s.energy_mwh.toFixed(3) + ' mWh';
                document.getElementById('capacity').textContent = s.capacity_mah.toFixed(3) + ' mAh';
                document.getElementById('duration').textContent = s.duration_formatted;
                document.getElementById('samples').textContent = s.samples.toLocaleString();
            } catch (e) {}
        }

        // Recording status
        async function checkRecording() {
            try {
                const res = await fetch('/api/recording/status');
                const s = await res.json();
                const badge = document.getElementById('rec-badge');
                const startBtn = document.getElementById('rec-start');
                const stopBtn = document.getElementById('rec-stop');

                if (s.is_recording) {
                    badge.style.display = 'inline';
                    badge.className = 'status-badge recording';
                    badge.textContent = 'REC ' + s.samples;
                    startBtn.disabled = true;
                    stopBtn.disabled = false;
                } else {
                    badge.style.display = 'none';
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                }
            } catch (e) {}
        }

        // Recording controls
        async function startRecording() {
            const name = document.getElementById('session-name').value || undefined;
            await fetch('/api/recording/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name})
            });
            checkRecording();
        }

        async function stopRecording() {
            const res = await fetch('/api/recording/stop', {method: 'POST'});
            const session = await res.json();
            alert('Recording saved: ' + session.name + '\\n' + session.samples + ' samples');
            checkRecording();
        }

        async function resetStats() {
            await fetch('/api/stats/reset', {method: 'POST'});
            fetchStats();
        }

        function exportCSV() {
            window.location.href = '/api/export/csv';
        }

        // Protocol trigger
        async function trigger(protocol) {
            try {
                const res = await fetch('/api/trigger/' + protocol, {method: 'POST'});
                const result = await res.json();
                if (result.success) {
                    // Visual feedback
                    event.target.style.background = '#27ae60';
                    setTimeout(() => event.target.style.background = '', 500);
                } else {
                    alert('Trigger failed: ' + result.error);
                }
            } catch (e) {
                alert('Trigger error: ' + e.message);
            }
        }

        // Sessions
        async function loadSessions() {
            try {
                const res = await fetch('/api/sessions');
                const sessions = await res.json();
                const list = document.getElementById('sessions-list');

                if (sessions.length === 0) {
                    list.innerHTML = '<p style="color:#888;">No saved sessions yet. Start recording to create one.</p>';
                    return;
                }

                list.innerHTML = sessions.map(s => `
                    <div class="session-item">
                        <div class="session-info">
                            <h4>${s.name}</h4>
                            <p>${s.samples} samples - ${s.start_time ? new Date(s.start_time).toLocaleString() : 'Unknown date'}</p>
                        </div>
                        <div class="session-actions">
                            <button class="session-btn" onclick="downloadSession('${s.name}', 'json')">JSON</button>
                            <button class="session-btn" onclick="downloadSession('${s.name}', 'csv')">CSV</button>
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                document.getElementById('sessions-list').innerHTML = '<p style="color:#e74c3c;">Error loading sessions</p>';
            }
        }

        function downloadSession(name, format) {
            window.location.href = `/api/session/${name}/${format}`;
        }

        // Start polling
        setInterval(fetchData, 100);
        setInterval(fetchStats, 1000);
        setInterval(checkRecording, 1000);
        fetchData();
        fetchStats();
        checkRecording();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

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

@app.route('/api/stats')
def api_stats():
    return jsonify(reader.get_stats())

@app.route('/api/stats/reset', methods=['POST'])
def api_reset_stats():
    reader.reset_stats()
    return jsonify({'success': True})

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
        headers={'Content-Disposition': f'attachment; filename=fnirsi_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
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
    return jsonify({'error': 'Session not found'}), 404

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
    return jsonify({'error': 'Session not found'}), 404

@app.route('/api/trigger/<protocol>', methods=['POST'])
def api_trigger(protocol):
    try:
        reader.trigger_protocol(protocol)
        return jsonify({'success': True, 'protocol': protocol})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


def main():
    print("=" * 60)
    print("FNIRSI FNB48P Full-Featured Web Monitor")
    print("=" * 60)

    try:
        reader.connect()
        reader.start_reading()
        print("Data streaming started")
        print()
        print("Open http://localhost:5002 in your browser")
        print()
        print("Features:")
        print("  - Real-time voltage, current, power monitoring")
        print("  - Statistics (min/max/avg, energy, capacity)")
        print("  - Session recording with CSV/JSON export")
        print("  - Protocol triggering (QC, PD, AFC, FCP, SCP)")
        print()
        print("Press Ctrl+C to stop")
        print("=" * 60)

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
