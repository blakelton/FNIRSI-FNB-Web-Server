#!/usr/bin/env python3
"""
FNIRSI FNB58 Web Monitor - Startup Script
Quick launcher with system checks
"""

# IMPORTANT: eventlet monkey_patch MUST be first
import eventlet
eventlet.monkey_patch()

import sys
import subprocess
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
    required = ['flask', 'flask_socketio', 'usb', 'bleak']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            missing.append(package)
            print(f"❌ {package} not found")
    
    if missing:
        print("\n❌ Missing dependencies. Install with:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def check_device():
    """Check if device is connected"""
    print("\n🔍 Checking for FNIRSI device...")
    try:
        import usb.core
        device = usb.core.find(idVendor=0x0716)
        if device:
            print("✓ FNIRSI device detected (USB)")
            return True
        else:
            print("⚠️  No USB device detected")
            print("   Device may be connected via Bluetooth")
            return True
    except Exception as e:
        print(f"⚠️  Could not check USB: {e}")
        return True

def main():
    print("=" * 60)
    print("FNIRSI FNB58 Web Monitor - Startup")
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
    print("Dashboard: http://localhost:5001")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    # Start Flask app
    try:
        from app import app, socketio
        socketio.run(app, host='0.0.0.0', port=5001, debug=True)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
