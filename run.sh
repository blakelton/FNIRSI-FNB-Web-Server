#!/bin/bash
# FNIRSI FNB48P Web Monitor - Cross-Platform Run Script (Linux/macOS)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  FNIRSI FNB48P Web Monitor"
echo "========================================"
echo

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    OS="windows"
fi

echo "[*] Detected OS: $OS"

# Check if venv exists
VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_CMD="python3"
PIP_CMD="pip3"

if [ -d "$VENV_DIR" ]; then
    echo "[*] Using virtual environment"
    if [ "$OS" == "windows" ]; then
        source "$VENV_DIR/Scripts/activate"
    else
        source "$VENV_DIR/bin/activate"
    fi
    PYTHON_CMD="python"
    PIP_CMD="pip"
else
    echo "[*] No virtual environment found"
fi

# Check for Python
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "[!] Python not found!"
    echo
    if [ "$OS" == "linux" ]; then
        echo "Run: ./install_linux.sh"
    elif [ "$OS" == "macos" ]; then
        echo "Run: ./install_macos.sh"
    else
        echo "Please install Python 3.8+ from https://www.python.org/"
    fi
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[*] Python version: $PYTHON_VERSION"

# Check for required packages
check_package() {
    $PYTHON_CMD -c "import $1" 2>/dev/null
    return $?
}

MISSING_PACKAGES=()

if ! check_package "flask"; then
    MISSING_PACKAGES+=("flask")
fi

if ! check_package "usb.core"; then
    MISSING_PACKAGES+=("pyusb")
fi

# If packages are missing, offer to install
if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo
    echo "[!] Missing packages: ${MISSING_PACKAGES[*]}"
    echo
    read -p "Install missing packages? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "[*] Installing packages..."
        $PIP_CMD install ${MISSING_PACKAGES[*]}
    else
        echo "[!] Cannot run without required packages."
        echo "    Run the install script for your OS:"
        if [ "$OS" == "linux" ]; then
            echo "      ./install_linux.sh"
        elif [ "$OS" == "macos" ]; then
            echo "      ./install_macos.sh"
        fi
        exit 1
    fi
fi

# Check for libusb on Linux
if [ "$OS" == "linux" ]; then
    if ! ldconfig -p 2>/dev/null | grep -q libusb; then
        echo
        echo "[!] libusb not found. Install with:"
        echo "    Ubuntu/Debian: sudo apt install libusb-1.0-0-dev"
        echo "    Fedora: sudo dnf install libusb1-devel"
        echo "    Arch: sudo pacman -S libusb"
        echo
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Check for libusb on macOS
if [ "$OS" == "macos" ]; then
    if ! brew list libusb &>/dev/null 2>&1; then
        echo
        echo "[!] libusb not found. Installing via Homebrew..."
        brew install libusb
    fi
fi

# Check udev rules on Linux
if [ "$OS" == "linux" ]; then
    if [ ! -f "/etc/udev/rules.d/99-fnirsi.rules" ]; then
        echo
        echo "[!] USB permission rules not found."
        echo "    You may need to run as root or install udev rules."
        echo
        echo "    To install udev rules, run:"
        echo "      sudo ./install_linux.sh"
        echo
        echo "    Or run with sudo (not recommended for regular use):"
        echo "      sudo $PYTHON_CMD fnb48p_monitor.py"
        echo
    fi
fi

# Run the monitor
echo
echo "[*] Starting FNIRSI FNB48P Monitor..."
echo "[*] Open http://localhost:5002 in your browser"
echo "[*] Press Ctrl+C to stop"
echo

$PYTHON_CMD fnb48p_monitor.py
