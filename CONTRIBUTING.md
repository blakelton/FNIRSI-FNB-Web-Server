# Contributing to FNIRSI Web Monitor

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Adding Device Support](#adding-device-support)

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all experience levels.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment
4. Create a branch for your changes
5. Make your changes
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- A FNIRSI USB power meter (for testing hardware features)

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/fnirsi-web-monitor.git
cd fnirsi-web-monitor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install all dependencies including dev tools
pip install -r requirements.txt
pip install pytest pytest-cov black flake8

# Or use pyproject.toml
pip install -e ".[full,dev]"
```

### USB Permissions (Linux)

```bash
sudo cp docker/99-fnirsi.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Project Structure

```
fnirsi-web-monitor/
├── fnb48p_monitor.py     # Standalone monitor (minimal deps)
├── app.py                # Full-featured app (all deps)
├── config.py             # Configuration
├── device/               # Device communication modules
│   ├── usb_reader.py     # USB communication
│   ├── bluetooth_reader.py
│   ├── data_processor.py
│   ├── protocol_detector.py
│   ├── alert_manager.py
│   └── device_manager.py
├── templates/            # HTML templates
├── static/               # CSS/JS assets
├── tests/                # Test suite
└── docs/                 # Documentation
```

### Entry Points

| File | Use Case | Dependencies |
|------|----------|--------------|
| `fnb48p_monitor.py` | Standalone, simple deployment | Flask, PyUSB |
| `app.py` | Full features, professional mode | All requirements.txt |

## Making Changes

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring

### Commit Messages

Use clear, descriptive commit messages:

```
Add support for FNIRSI FNB58 device

- Add device ID 0x2e3c:0x5558 to supported devices
- Update packet decoding for FNB58 format
- Add documentation for FNB58 specifics
```

## Submitting Changes

1. Ensure your code follows the style guidelines
2. Add tests for new functionality
3. Update documentation as needed
4. Push to your fork
5. Create a pull request with a clear description

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
How was this tested?

## Checklist
- [ ] Code follows project style
- [ ] Tests pass
- [ ] Documentation updated
```

## Code Style

### Python

- Follow PEP 8 guidelines
- Maximum line length: 100 characters
- Use type hints where practical
- Use docstrings for functions and classes

```python
def decode_packet(data: bytes) -> dict:
    """
    Decode a USB packet from the FNIRSI device.

    Args:
        data: Raw 64-byte USB packet

    Returns:
        Dictionary with decoded values (voltage, current, etc.)
    """
    ...
```

### Formatting

Use `black` for automatic formatting:

```bash
black fnb48p_monitor.py app.py device/
```

Use `flake8` for linting:

```bash
flake8 fnb48p_monitor.py app.py device/
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_usb_reader.py
```

### Writing Tests

Place tests in the `tests/` directory:

```python
# tests/test_data_processor.py
import pytest
from device.data_processor import DataProcessor

def test_voltage_decoding():
    processor = DataProcessor()
    # Raw value representing 5.0V (5.0 * 100000 = 500000)
    raw = 500000
    assert processor.decode_voltage(raw) == 5.0

def test_negative_current():
    processor = DataProcessor()
    # Test negative current handling
    ...
```

## Adding Device Support

To add support for a new FNIRSI device:

1. **Find the device IDs:**
   ```bash
   lsusb  # Look for FNIRSI or the device name
   ```

2. **Add to SUPPORTED_DEVICES in `fnb48p_monitor.py`:**
   ```python
   SUPPORTED_DEVICES = [
       (0x2e3c, 0x0049, "FNB48P/FNB48S"),
       (0x2e3c, 0x5558, "FNB58"),
       (0xNEW_VENDOR, 0xNEW_PRODUCT, "NEW_MODEL"),  # Add here
   ]
   ```

3. **Add udev rule in `docker/99-fnirsi.rules`:**
   ```
   SUBSYSTEM=="usb", ATTR{idVendor}=="xxxx", ATTR{idProduct}=="yyyy", MODE="0666"
   ```

4. **Test the device** and document any protocol differences

5. **Update documentation** in README.md

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions or ideas

Thank you for contributing!
