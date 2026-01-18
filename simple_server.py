#!/usr/bin/env python3
"""
Simple FNIRSI FNB48P Web Monitor - No eventlet, just works
"""

import sys
import time
import threading
import json
from datetime import datetime
from collections import deque
from flask import Flask, jsonify, render_template_string

import usb.core
import usb.util

# === USB Reader ===
class FNIRSIReader:
    """Simple USB reader for FNIRSI FNB48P"""

    SUPPORTED_DEVICES = [
        (0x2e3c, 0x0049),  # FNIRSI FNB48P / FNB48S
        (0x2e3c, 0x5558),  # FNIRSI FNB58
        (0x0483, 0x003a),  # FNIRSI FNB48 (older)
        (0x0483, 0x003b),  # FNIRSI C1
    ]

    def __init__(self):
        self.device = None
        self.ep_in = None
        self.ep_out = None
        self.is_connected = False
        self.is_reading = False
        self.read_thread = None
        self.data_buffer = deque(maxlen=500)
        self.latest_reading = None
        self.lock = threading.Lock()

    def connect(self):
        # Find device
        for vendor_id, product_id in self.SUPPORTED_DEVICES:
            self.device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
            if self.device:
                print(f"Found device: VID=0x{vendor_id:04x} PID=0x{product_id:04x}")
                break

        if not self.device:
            raise ConnectionError("FNIRSI device not found")

        # Reset device
        try:
            self.device.reset()
        except:
            pass

        # Detach kernel driver
        for cfg in self.device:
            for intf in cfg:
                if self.device.is_kernel_driver_active(intf.bInterfaceNumber):
                    try:
                        self.device.detach_kernel_driver(intf.bInterfaceNumber)
                    except:
                        pass

        # Set config
        try:
            self.device.set_configuration()
        except:
            pass

        # Get endpoints
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

        # Send init handshake
        self.ep_out.write(b"\xaa\x81" + b"\x00" * 61 + b"\x8e")
        self.ep_out.write(b"\xaa\x82" + b"\x00" * 61 + b"\x96")
        self.ep_out.write(b"\xaa\x82" + b"\x00" * 61 + b"\x96")

        self.is_connected = True
        print("Connected to FNIRSI device")
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
        refresh = 1.0  # 1s for FNB48S
        continue_time = time.time() + refresh

        while self.is_reading:
            try:
                data = self.ep_in.read(size_or_buffer=64, timeout=5000)
                readings = self._decode_packet(data)

                with self.lock:
                    for r in readings:
                        self.data_buffer.append(r)
                        self.latest_reading = r

                if time.time() >= continue_time:
                    continue_time = time.time() + refresh
                    self.ep_out.write(b"\xaa\x83" + b"\x00" * 61 + b"\x9e")

            except usb.core.USBError as e:
                if self.is_reading:
                    time.sleep(0.1)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(0.1)

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
                'voltage': round(voltage, 4),
                'current': round(current, 4),
                'power': round(power, 4),
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

    def stop(self):
        self.is_reading = False
        if self.read_thread:
            self.read_thread.join(timeout=2)


# === Flask App ===
app = Flask(__name__)
reader = FNIRSIReader()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>FNIRSI FNB48P Monitor</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e; color: #eee; padding: 20px;
        }
        h1 { color: #4ecca3; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card {
            background: #16213e; border-radius: 12px; padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .card h3 { color: #888; font-size: 14px; margin-bottom: 10px; text-transform: uppercase; }
        .card .value { font-size: 36px; font-weight: bold; }
        .card .unit { font-size: 18px; color: #888; }
        .voltage .value { color: #f39c12; }
        .current .value { color: #3498db; }
        .power .value { color: #e74c3c; }
        .temp .value { color: #9b59b6; }
        .dp .value, .dn .value { color: #1abc9c; }
        #chart { background: #16213e; border-radius: 12px; padding: 20px; height: 300px; }
        canvas { width: 100% !important; height: 260px !important; }
        .status { margin-bottom: 20px; padding: 10px 15px; border-radius: 8px; }
        .status.connected { background: #27ae60; }
        .status.disconnected { background: #c0392b; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h1>FNIRSI FNB48P USB Power Monitor</h1>
    <div id="status" class="status disconnected">Connecting...</div>

    <div class="grid">
        <div class="card voltage">
            <h3>Voltage</h3>
            <span id="voltage" class="value">--</span><span class="unit"> V</span>
        </div>
        <div class="card current">
            <h3>Current</h3>
            <span id="current" class="value">--</span><span class="unit"> A</span>
        </div>
        <div class="card power">
            <h3>Power</h3>
            <span id="power" class="value">--</span><span class="unit"> W</span>
        </div>
        <div class="card temp">
            <h3>Temperature</h3>
            <span id="temp" class="value">--</span><span class="unit"> C</span>
        </div>
        <div class="card dp">
            <h3>D+ Voltage</h3>
            <span id="dp" class="value">--</span><span class="unit"> V</span>
        </div>
        <div class="card dn">
            <h3>D- Voltage</h3>
            <span id="dn" class="value">--</span><span class="unit"> V</span>
        </div>
    </div>

    <div id="chart">
        <canvas id="powerChart"></canvas>
    </div>

    <script>
        const maxPoints = 100;
        const data = { labels: [], voltage: [], current: [], power: [] };

        const ctx = document.getElementById('powerChart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    { label: 'Voltage (V)', data: data.voltage, borderColor: '#f39c12', tension: 0.1, pointRadius: 0 },
                    { label: 'Current (A)', data: data.current, borderColor: '#3498db', tension: 0.1, pointRadius: 0 },
                    { label: 'Power (W)', data: data.power, borderColor: '#e74c3c', tension: 0.1, pointRadius: 0 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { display: false },
                    y: { beginAtZero: true, grid: { color: '#333' } }
                },
                plugins: { legend: { labels: { color: '#eee' } } },
                animation: { duration: 0 }
            }
        });

        async function fetchData() {
            try {
                const res = await fetch('/api/latest');
                if (!res.ok) throw new Error('No data');
                const d = await res.json();

                document.getElementById('status').className = 'status connected';
                document.getElementById('status').textContent = 'Connected - Live Data';

                document.getElementById('voltage').textContent = d.voltage.toFixed(3);
                document.getElementById('current').textContent = d.current.toFixed(4);
                document.getElementById('power').textContent = d.power.toFixed(3);
                document.getElementById('temp').textContent = d.temperature.toFixed(1);
                document.getElementById('dp').textContent = d.dp.toFixed(3);
                document.getElementById('dn').textContent = d.dn.toFixed(3);

                // Update chart
                const time = new Date().toLocaleTimeString();
                data.labels.push(time);
                data.voltage.push(d.voltage);
                data.current.push(d.current);
                data.power.push(d.power);

                if (data.labels.length > maxPoints) {
                    data.labels.shift();
                    data.voltage.shift();
                    data.current.shift();
                    data.power.shift();
                }

                chart.update();
            } catch (e) {
                document.getElementById('status').className = 'status disconnected';
                document.getElementById('status').textContent = 'Waiting for data...';
            }
        }

        setInterval(fetchData, 100);  // Update 10x per second
        fetchData();
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
    return jsonify(reader.get_recent(100))


def main():
    print("=" * 50)
    print("FNIRSI FNB48P Simple Web Monitor")
    print("=" * 50)

    try:
        reader.connect()
        reader.start_reading()
        print("Data streaming started")
        print()
        print("Open http://localhost:5002 in your browser")
        print("Press Ctrl+C to stop")
        print("=" * 50)

        app.run(host='0.0.0.0', port=5002, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        reader.stop()


if __name__ == '__main__':
    main()
