#!/usr/bin/env python3
"""
FNIRSI USB Power Monitor - Startup Script
Quick launcher with system checks

Note: This script uses threading mode for Flask-SocketIO to support
both USB and Bluetooth connections. Do NOT use eventlet.
"""

import sys
import os

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required = [
        ('flask', 'flask'),
        ('flask_socketio', 'flask-socketio'),
        ('usb', 'pyusb'),
        ('bleak', 'bleak'),
    ]
    missing = []

    for import_name, package_name in required:
        try:
            __import__(import_name)
            print(f"✓ {package_name}")
        except ImportError:
            missing.append(package_name)
            print(f"❌ {package_name} not found")

    if missing:
        print("\n❌ Missing dependencies. Install with:")
        print("   pip install -r requirements.txt")
        return False

    return True

def check_device():
    """Check if device is connected"""
    print("\n🔍 Checking for FNIRSI device...")

    # Check USB
    try:
        import usb.core
        # Check all known FNIRSI vendor IDs
        vendors = [0x2e3c, 0x0483]
        for vid in vendors:
            device = usb.core.find(idVendor=vid)
            if device:
                print("✓ FNIRSI device detected (USB)")
                return True
        print("⚠️  No USB device detected")
        print("   Device may be connected via Bluetooth")
        return True
    except Exception as e:
        print(f"⚠️  Could not check USB: {e}")
        return True

def main():
    print("=" * 60)
    print("FNIRSI USB Power Monitor - Startup")
    print("=" * 60)
    print()

    # System checks
    print("System Checks:")
    print("-" * 60)

    if not check_python_version():
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)

    check_device()

    print()
    print("=" * 60)
    print("Starting Flask server...")
    print("Dashboard: http://localhost:5002")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    # Start Flask app
    try:
        from app import app, socketio
        socketio.run(app, host='0.0.0.0', port=5002, debug=True, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
