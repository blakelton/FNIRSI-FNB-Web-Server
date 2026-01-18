# FNIRSI USB Tester Web Monitor

A full-featured web-based monitoring application for FNIRSI USB power meters with cross-platform support. Automatically detects and identifies your connected device.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)

## Features

### Real-Time Monitoring
- **Live readings** at 100Hz: Voltage, Current, Power, Temperature
- **D+/D- voltage monitoring** for charging protocol analysis
- **Real-time charts** with configurable data series
- **Energy (Wh/mWh) and Capacity (Ah/mAh) tracking**

### Protocol Support
- **Auto-detection** of charging protocols from D+/D- voltages
- **Protocol triggering** for fast charge testing:
  - Quick Charge 2.0/3.0 (5V, 9V, 12V, 20V)
  - USB Power Delivery (5V, 9V, 12V, 15V, 20V)
  - Samsung AFC (5V, 9V, 12V)
  - Huawei FCP/SCP
  - OPPO VOOC/WARP/SuperVOOC
  - Apple 2.1A/2.4A

### Recording & Export
- **Session recording** with automatic statistics
- **Export to CSV or JSON** formats
- **Session management** - save, load, delete recordings
- **Charge estimation** with ETA and progress tracking

### Alerts & Safety
- **Configurable thresholds** for voltage, current, power, temperature
- **Visual alerts** with flashing indicators
- **Alert banner** for immediate notification

### Analysis Tools
- **Oscilloscope mode** for waveform analysis
- **Statistics tracking** (min/max/avg for all parameters)
- **Charge curve plotting** with completion estimates

### Customization
- **Dark/Light theme** toggle
- **Calibration offsets** for voltage and current
- **Persistent settings** saved between sessions

## Supported Devices

The monitor automatically detects your device and updates the UI with the model name.

| Device | Description | Vendor ID | Product ID | Status |
|--------|-------------|-----------|------------|--------|
| **FNB48P/S** | Premium USB tester with metal housing, 1.77" display | 0x2e3c | 0x0049 | ✅ Fully Supported |
| **FNB58** | Advanced USB tester with 2.0" display, Bluetooth | 0x2e3c | 0x5558 | ✅ Supported |
| **FNB48** | Original USB tester (legacy hardware) | 0x0483 | 0x003a | ✅ Supported |
| **C1** | Compact Type-C PD trigger with 1.3" display | 0x0483 | 0x003b | ✅ Supported |

## Application Modes

This project provides two entry points depending on your needs:

| Entry Point | Dependencies | Features |
|-------------|--------------|----------|
| `fnb48p_monitor.py` | Flask, PyUSB | Standalone monitor with all core features. **Recommended for most users.** |
| `app.py` | Full requirements.txt | Professional mode with Bluetooth, advanced analysis, WebSocket support |

**For most users:** Use `fnb48p_monitor.py` (installed by default)

**For advanced features:** Install full dependencies with `pip install -r requirements.txt`, then run `app.py`

## Quick Start

### Universal Python Scripts (Recommended)

The easiest way to get started - works on any platform with Python installed:

```bash
# Install dependencies (auto-detects your OS)
python install.py

# Run the monitor (auto-detects your OS)
python run.py
```

### Platform-Specific Scripts

Alternatively, use the native scripts for your platform:

**Linux / macOS:**
```bash
./run.sh
```

**Windows (Command Prompt):**
```cmd
run.bat
```

**Windows (PowerShell):**
```powershell
.\run.ps1
```

Then open **http://localhost:5002** in your browser.

---

## Installation

### Linux

**Automatic Installation:**
```bash
./install_linux.sh
```

**Manual Installation:**
```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip python3-venv libusb-1.0-0-dev

# Fedora
sudo dnf install python3 python3-pip libusb1-devel

# Arch Linux
sudo pacman -S python python-pip libusb

# Create virtual environment and install packages
python3 -m venv venv
source venv/bin/activate
pip install flask pyusb
```

**USB Permissions (Required):**
```bash
sudo tee /etc/udev/rules.d/99-fnirsi.rules << 'EOF'
# FNIRSI USB Testers
SUBSYSTEM=="usb", ATTR{idVendor}=="2e3c", ATTR{idProduct}=="0049", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="2e3c", ATTR{idProduct}=="5558", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="003a", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="003b", MODE="0666"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger
```

**Important:** Unplug and replug your device after creating the udev rule.

---

### macOS

**Automatic Installation:**
```bash
./install_macos.sh
```

**Manual Installation:**
```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python libusb

# Create virtual environment and install packages
python3 -m venv venv
source venv/bin/activate
pip install flask pyusb
```

---

### Windows

**Automatic Installation:**

Option 1 - Command Prompt:
```cmd
install_windows.bat
```

Option 2 - PowerShell:
```powershell
.\install_windows.ps1
```

**Manual Installation:**

1. Install Python 3.8+ from [python.org](https://www.python.org/downloads/)
   - **Important:** Check "Add Python to PATH" during installation

2. Open Command Prompt or PowerShell:
```cmd
python -m venv venv
venv\Scripts\activate
pip install flask pyusb libusb
```

**USB Driver Setup (Required):**

Windows requires a libusb-compatible driver for the FNIRSI device:

1. Download [Zadig](https://zadig.akeo.ie/)
2. Connect your FNIRSI device
3. Run Zadig
4. Select your device (FNIRSI USB Tester) from the dropdown
5. Select **libusb-win32** or **WinUSB** as the driver
6. Click "Install Driver"

---

## Usage

### Running the Monitor

**Linux / macOS:**
```bash
./run.sh
# Or manually:
source venv/bin/activate
python3 fnb48p_monitor.py
```

**Windows:**
```cmd
run.bat
REM Or manually:
venv\Scripts\activate
python fnb48p_monitor.py
```

Then open **http://localhost:5002** in your browser.

### Web Interface Tabs

| Tab | Description |
|-----|-------------|
| **Monitor** | Live readings, charts, recording controls |
| **Statistics** | Detailed min/max/avg statistics |
| **Waveform** | Oscilloscope-style waveform view |
| **Trigger** | Fast charging protocol trigger buttons |
| **Sessions** | Saved recording management |
| **Settings** | Alerts, calibration, device info |

---

## API Reference

The application provides a REST API for integration:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/latest` | GET | Get latest reading |
| `/api/recent?points=100` | GET | Get recent readings |
| `/api/waveform?points=500` | GET | Get waveform data |
| `/api/stats` | GET | Get statistics |
| `/api/stats/reset` | POST | Reset statistics |
| `/api/protocol` | GET | Get detected protocol |
| `/api/alerts` | GET/POST | Get/set alert config |
| `/api/settings` | GET/POST | Get/set calibration |
| `/api/device` | GET | Get device info |
| `/api/recording/start` | POST | Start recording |
| `/api/recording/stop` | POST | Stop recording |
| `/api/recording/status` | GET | Get recording status |
| `/api/sessions` | GET | List saved sessions |
| `/api/session/{name}/json` | GET | Download session as JSON |
| `/api/session/{name}/csv` | GET | Download session as CSV |
| `/api/session/{name}` | DELETE | Delete session |
| `/api/trigger/{protocol}` | POST | Trigger charging protocol |
| `/api/export/csv` | GET | Export current data as CSV |
| `/api/charge-estimate?target_mah=3000` | GET | Get charge estimate |

### Protocol Trigger Values

```
qc2_5v, qc2_9v, qc2_12v, qc2_20v
qc3_5v, qc3_9v, qc3_12v
pd_5v, pd_9v, pd_12v, pd_15v, pd_20v
afc_5v, afc_9v, afc_12v
fcp_5v, fcp_9v, fcp_12v
scp_5v, scp_4.5v
vooc, warp, supervooc
apple_2.4a, apple_2.1a
```

---

## Data Storage

- **Sessions** are saved to `~/fnirsi_sessions/`
- **Settings** are persisted in `~/fnirsi_sessions/settings.json`
- **Export formats**: CSV (spreadsheet-compatible), JSON (full data)

---

## Troubleshooting

### Device Not Found

**Linux:**
1. Check USB connection: `lsusb | grep -i fnirsi` or `lsusb | grep 2e3c`
2. Verify udev rules are loaded: `sudo udevadm control --reload-rules`
3. Unplug and replug the device
4. Try running with sudo (for testing): `sudo python3 fnb48p_monitor.py`

**macOS:**
1. Check USB connection: `system_profiler SPUSBDataType | grep -i fnirsi`
2. Ensure libusb is installed: `brew list libusb`
3. Try unplugging and replugging the device

**Windows:**
1. Open Device Manager and check if the device appears
2. Ensure Zadig driver is installed (see Installation section)
3. Try a different USB port

### Permission Denied (Linux)

Ensure the udev rule is correctly installed and you've unplugged/replugged the device.

### No Data Displayed

1. Check the device is in USB mode (not Bluetooth)
2. Ensure no other application is using the device
3. Check the terminal for error messages

### Resource Busy Error

Another application (like the official FNIRSI software) may be holding the device. Close other USB monitoring applications and try again.

### Windows: Python Not Found

Make sure Python was installed with "Add Python to PATH" checked. You may need to reinstall Python with this option enabled.

---

## Technical Details

### Protocol

Communication uses USB HID with 64-byte packets:

- **Initialization**: `0xaa 0x81`, `0xaa 0x82` commands
- **Data packets**: Type `0x04`, containing 4 samples of 15 bytes each
- **Keep-alive**: `0xaa 0x83` sent every ~1 second

### Data Format (per sample)

| Offset | Size | Description |
|--------|------|-------------|
| 0-3 | 4 bytes | Voltage (divide by 100000 for V) |
| 4-7 | 4 bytes | Current (divide by 100000 for A) |
| 8-9 | 2 bytes | D+ voltage (divide by 1000 for V) |
| 10-11 | 2 bytes | D- voltage (divide by 1000 for V) |
| 13-14 | 2 bytes | Temperature (divide by 10 for C) |

### Sample Rate

- USB polling: ~100 samples/second
- 4 samples per packet = 25 packets/second

---

## Credits

- Web UI interface: [f4inu/FNB58](https://github.com/f4inu/FNB58) (MIT License)
- USB protocol reverse engineering: [baryluk/fnirsi-usb-power-data-logger](https://github.com/baryluk/fnirsi-usb-power-data-logger)
- Bluetooth protocol: Reverse-engineered from FNIRSI Android app
- Original Windows software: [FNIRSI](https://www.fnirsi.com/)

## License

MIT License - See [LICENSE](LICENSE) for details.

All dependencies are compatible with MIT licensing:
- Flask (BSD-3-Clause)
- PyUSB (BSD-3-Clause)
- libusb (LGPL-2.1 - system library)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

### v1.0.0
- Initial release
- Real-time monitoring with charts
- Protocol auto-detection
- Session recording with CSV/JSON export
- Protocol triggering for all major fast charge standards
- Threshold alerts
- Oscilloscope waveform view
- Charge estimation
- Calibration settings
- Dark/light theme support
- Cross-platform support (Linux, macOS, Windows)
