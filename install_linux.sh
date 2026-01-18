#!/bin/bash
# FNIRSI FNB48P Web Monitor - Linux Installation Script
# Supports: Ubuntu/Debian, Fedora/RHEL, Arch Linux

set -e

echo "========================================"
echo "  FNIRSI FNB48P Monitor - Linux Setup"
echo "========================================"
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Detect package manager
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt"
    echo "[*] Detected: Debian/Ubuntu"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    echo "[*] Detected: Fedora/RHEL"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    echo "[*] Detected: RHEL/CentOS"
elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
    echo "[*] Detected: Arch Linux"
else
    echo "[!] Unknown package manager. Please install dependencies manually:"
    echo "    - python3 (3.8+)"
    echo "    - python3-pip"
    echo "    - python3-venv"
    echo "    - libusb-1.0"
    exit 1
fi

# Check if running as root for system packages
SUDO=""
if [ "$EUID" -ne 0 ]; then
    SUDO="sudo"
    echo "[*] Will use sudo for system packages"
fi

# Install system dependencies
echo
echo "[1/4] Installing system dependencies..."

case $PKG_MANAGER in
    apt)
        $SUDO apt-get update || { echo "[!] apt-get update failed"; exit 1; }
        $SUDO apt-get install -y python3 python3-pip python3-venv libusb-1.0-0-dev || { echo "[!] Package installation failed"; exit 1; }
        ;;
    dnf)
        $SUDO dnf install -y python3 python3-pip python3-venv libusb1-devel || { echo "[!] Package installation failed"; exit 1; }
        ;;
    yum)
        $SUDO yum install -y python3 python3-pip libusb1-devel || { echo "[!] Package installation failed"; exit 1; }
        ;;
    pacman)
        $SUDO pacman -Sy --noconfirm python python-pip libusb || { echo "[!] Package installation failed"; exit 1; }
        ;;
esac

# Create virtual environment
echo
echo "[2/4] Setting up Python environment..."

VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "    Creating virtual environment..."
    python3 -m venv "$VENV_DIR" || { echo "[!] Failed to create virtual environment"; exit 1; }
fi

# Activate venv and install packages
source "$VENV_DIR/bin/activate" || { echo "[!] Failed to activate virtual environment"; exit 1; }

echo "[3/4] Installing Python packages..."
pip install --upgrade pip || { echo "[!] Failed to upgrade pip"; exit 1; }

# Check which requirements file to use
if [ -f "$SCRIPT_DIR/requirements-minimal.txt" ]; then
    echo "    Using requirements-minimal.txt (standalone monitor)"
    pip install -r "$SCRIPT_DIR/requirements-minimal.txt" || { echo "[!] Failed to install Python packages"; exit 1; }
elif [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    echo "    Using requirements.txt (full features)"
    pip install -r "$SCRIPT_DIR/requirements.txt" || { echo "[!] Failed to install Python packages"; exit 1; }
else
    echo "    Installing minimal packages..."
    pip install flask pyusb || { echo "[!] Failed to install Python packages"; exit 1; }
fi

# Setup udev rules for USB access
echo
echo "[4/4] Setting up USB permissions..."

UDEV_RULE="/etc/udev/rules.d/99-fnirsi.rules"

if [ ! -f "$UDEV_RULE" ]; then
    echo "    Creating udev rules for FNIRSI devices..."

    # Check if we have the rules file in docker directory
    if [ -f "$SCRIPT_DIR/docker/99-fnirsi.rules" ]; then
        $SUDO cp "$SCRIPT_DIR/docker/99-fnirsi.rules" "$UDEV_RULE" || { echo "[!] Failed to copy udev rules"; exit 1; }
    else
        $SUDO tee "$UDEV_RULE" > /dev/null << 'EOF'
# FNIRSI USB Testers - Allow non-root access
# FNB48P / FNB48S
SUBSYSTEM=="usb", ATTR{idVendor}=="2e3c", ATTR{idProduct}=="0049", MODE="0666"
# FNB58
SUBSYSTEM=="usb", ATTR{idVendor}=="2e3c", ATTR{idProduct}=="5558", MODE="0666"
# FNB48 (older)
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="003a", MODE="0666"
# C1
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="003b", MODE="0666"
EOF
    fi

    $SUDO udevadm control --reload-rules || echo "[!] Warning: Failed to reload udev rules"
    $SUDO udevadm trigger || echo "[!] Warning: Failed to trigger udev"
    echo "    [!] Please unplug and replug your FNIRSI device"
else
    echo "    udev rules already exist"
fi

echo
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo
echo "To run the monitor:"
echo "  ./run.sh"
echo
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  python3 fnb48p_monitor.py"
echo
echo "Then open: http://localhost:5002"
echo
echo "For full features (professional mode, Bluetooth, etc.):"
echo "  pip install -r requirements.txt"
echo
