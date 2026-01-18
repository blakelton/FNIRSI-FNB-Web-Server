# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-01-17

### Added
- Bluetooth support for FNB48, FNB48S, FNB48P, C1 devices
- Multi-device auto-detection (FNB58, FNB48, FNB48S, FNB48P, C1)
- Configurable Bluetooth adapter selection for multi-adapter systems
- Setup wizard (`setup.py`) with venv creation, dependency install, and desktop launchers
- Data layer modules (`data/alerts.py`, `data/buffers.py`, `data/statistics.py`)
- Storage layer modules (`storage/session_manager.py`, `storage/settings.py`)
- Cross-platform install scripts (`install.py`, `install_linux.sh`, `install_macos.sh`, `install_windows.bat`)
- Cross-platform run scripts (`run.py`, `run.sh`, `run.bat`, `run.ps1`)
- Test suite with pytest (`tests/test_api.py`, `tests/test_data_decoding.py`, `tests/test_statistics.py`)
- Project configuration (`pyproject.toml`, `Makefile`)
- Contributing guidelines (`CONTRIBUTING.md`)

### Fixed
- **Bluetooth CRC algorithm**: Changed from simple byte sum to CRC16-XMODEM (matching Android app)
- **Bluetooth notification sequence**: Enable notifications before sending commands (matching Android app)
- **Flask-SocketIO compatibility**: Changed from `eventlet` to `threading` async mode for asyncio compatibility
- **Port standardization**: All entry points now use port 5002 consistently
- **Device IDs**: Fixed vendor/product IDs in config.py to match actual FNIRSI devices

### Changed
- Default entry point changed from `fnb48p_monitor.py` to `app.py` for full USB+Bluetooth support
- Documentation reorganized into `docs/` folder
- Updated `CLAUDE.md` with detailed Bluetooth protocol documentation
- Removed eventlet dependency (conflicts with Bluetooth asyncio)

### Technical
- Bluetooth packet format: `[0xAA][CMD][LEN][DATA...][CRC_LOW]`
- CRC16-XMODEM polynomial: 0x1021
- BLE UUIDs: Write `0000ffe9-...`, Notify `0000ffe4-...`
- Initialization sequence: GET_INFO (0x81) → GET_STATUS (0x85) → START (0x82)
- Sample rate: ~10Hz over Bluetooth

## [1.0.0] - 2025-01-09

### Added
- Initial public release
- Real-time monitoring at 100Hz for voltage, current, power, temperature
- D+/D- voltage monitoring for charging protocol analysis
- Real-time charts with configurable data series
- Energy (Wh/mWh) and capacity (Ah/mAh) tracking
- Protocol auto-detection from D+/D- voltages
- Protocol triggering support:
  - Quick Charge 2.0/3.0 (5V, 9V, 12V, 20V)
  - USB Power Delivery (5V, 9V, 12V, 15V, 20V)
  - Samsung AFC (5V, 9V, 12V)
  - Huawei FCP/SCP
  - OPPO VOOC/WARP/SuperVOOC
  - Apple 2.1A/2.4A
- Session recording with automatic statistics
- Export to CSV and JSON formats
- Session management (save, load, delete)
- Charge estimation with ETA and progress tracking
- Configurable threshold alerts for voltage, current, power, temperature
- Visual alerts with flashing indicators
- Oscilloscope mode for waveform analysis
- Statistics tracking (min/max/avg for all parameters)
- Dark/light theme toggle
- Calibration offsets for voltage and current
- Persistent settings saved between sessions
- Cross-platform support (Linux, macOS, Windows)
- Universal Python install/run scripts
- Platform-specific shell scripts
- Docker support with docker-compose
- REST API for integration
- Support for multiple FNIRSI devices:
  - FNB48P / FNB48S (0x2e3c:0x0049)
  - FNB58 (0x2e3c:0x5558)
  - FNB48 (0x0483:0x003a)
  - C1 (0x0483:0x003b)

### Technical
- USB HID communication with 64-byte packets
- Initialization protocol: 0xaa 0x81, 0xaa 0x82 commands
- Data packets: Type 0x04, 4 samples of 15 bytes each
- Keep-alive: 0xaa 0x83 sent every ~1 second
- Flask web server on port 5002
- PyUSB for USB communication
