#!/bin/bash
# FNIRSI FNB58 Monitor - Docker Entrypoint Script

set -e

echo "🚀 Starting FNIRSI FNB58 Monitor..."

# Check for USB devices
if [ -d "/dev/bus/usb" ]; then
    echo "✓ USB subsystem detected"
    USB_DEVICES=$(lsusb 2>/dev/null | grep -i "0716:" || true)
    if [ -n "$USB_DEVICES" ]; then
        echo "✓ FNIRSI device found:"
        echo "  $USB_DEVICES"
    else
        echo "⚠ No FNIRSI device detected (VID: 0716)"
        echo "  Make sure device is connected and container has USB access"
    fi
else
    echo "⚠ USB subsystem not available"
    echo "  Run with: docker run --device=/dev/bus/usb:/dev/bus/usb ..."
fi

# Check for Bluetooth
if command -v hciconfig &> /dev/null; then
    BT_STATUS=$(hciconfig 2>/dev/null | grep -i "UP RUNNING" || true)
    if [ -n "$BT_STATUS" ]; then
        echo "✓ Bluetooth adapter available"
    else
        echo "⚠ Bluetooth adapter not detected or down"
        echo "  For Bluetooth support, run with: docker run --net=host --privileged ..."
    fi
else
    echo "ℹ Bluetooth tools not available (USB-only mode)"
fi

# Create directories if they don't exist
mkdir -p /app/sessions /app/exports

# Show configuration
echo ""
echo "📊 Configuration:"
echo "  Host: ${HOST:-0.0.0.0}"
echo "  Port: ${PORT:-5000}"
echo "  Flask Env: ${FLASK_ENV:-production}"
if [ -n "$BT_DEVICE_ADDRESS" ]; then
    echo "  BT Device: $BT_DEVICE_ADDRESS"
fi

echo ""
echo "🌐 Access the monitor at: http://localhost:${PORT:-5000}"
echo ""

# Execute the main application
exec python /app/start.py
