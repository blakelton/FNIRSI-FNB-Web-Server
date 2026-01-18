# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
