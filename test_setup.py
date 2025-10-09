#!/usr/bin/env python3
"""
Quick test script to verify setup
"""

import sys

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    tests = {
        'Flask': 'flask',
        'Flask-SocketIO': 'flask_socketio',
        'PyUSB': 'usb.core',
        'Bleak': 'bleak',
        'NumPy': 'numpy',
        'Pandas': 'pandas'
    }
    
    passed = 0
    failed = 0
    
    for name, module in tests.items():
        try:
            __import__(module)
            print(f"  ✓ {name}")
            passed += 1
        except ImportError as e:
            print(f"  ✗ {name} - {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0

def test_device_modules():
    """Test if device modules are working"""
    print("\nTesting device modules...")
    
    try:
        from device import DeviceManager, USBReader, BluetoothReader
        print("  ✓ Device modules imported successfully")
        
        # Test instantiation
        manager = DeviceManager()
        print("  ✓ DeviceManager created")
        
        usb = USBReader()
        print("  ✓ USBReader created")
        
        bt = BluetoothReader()
        print("  ✓ BluetoothReader created")
        
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_flask_app():
    """Test if Flask app can be created"""
    print("\nTesting Flask app...")
    
    try:
        from app import app, socketio
        print("  ✓ Flask app imported")
        print("  ✓ SocketIO initialized")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("FNIRSI FNB58 Web Monitor - Setup Test")
    print("=" * 60)
    print()
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        all_passed = False
        print("\n⚠️  Some dependencies are missing!")
        print("   Run: pip install -r requirements.txt")
    
    # Test device modules
    if not test_device_modules():
        all_passed = False
    
    # Test Flask app
    if not test_flask_app():
        all_passed = False
    
    print()
    print("=" * 60)
    if all_passed:
        print("✅ All tests passed! Ready to run.")
        print("   Start with: python start.py")
    else:
        print("❌ Some tests failed. Check errors above.")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
