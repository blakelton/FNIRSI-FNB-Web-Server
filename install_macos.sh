#!/bin/bash
# FNIRSI FNB48P Web Monitor - macOS Installation Script

set -e

echo "========================================"
echo "  FNIRSI FNB48P Monitor - macOS Setup"
echo "========================================"
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "[!] Homebrew not found."
    echo
    echo "Would you like to install Homebrew? (recommended)"
    echo "Or you can install it manually from: https://brew.sh"
    echo
    read -p "Install Homebrew now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "[*] Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || { echo "[!] Failed to install Homebrew"; exit 1; }

        # Add Homebrew to PATH for Apple Silicon
        if [[ -f "/opt/homebrew/bin/brew" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    else
        echo "[!] Please install Homebrew and run this script again."
        exit 1
    fi
fi

echo "[1/3] Installing system dependencies..."
brew install python libusb || { echo "[!] Failed to install packages via Homebrew"; exit 1; }

echo
echo "[2/3] Setting up Python environment..."

VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "    Creating virtual environment..."
    python3 -m venv "$VENV_DIR" || { echo "[!] Failed to create virtual environment"; exit 1; }
fi

# Activate venv
source "$VENV_DIR/bin/activate" || { echo "[!] Failed to activate virtual environment"; exit 1; }

echo "[3/3] Installing Python packages..."
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
echo "Note: On macOS, USB access should work without additional"
echo "      configuration. If you encounter permission issues,"
echo "      try running with sudo."
echo
