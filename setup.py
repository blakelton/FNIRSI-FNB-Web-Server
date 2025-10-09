"""
py2app setup script for FNIRSI FNB58 Monitor
Creates a standalone macOS application bundle with Python backend
"""

from setuptools import setup

APP = ['start.py']

# Include all data files
DATA_FILES = [
    ('', ['config.py', 'app.py']),
    ('device', [
        'device/__init__.py',
        'device/usb_reader.py',
        'device/bluetooth_reader.py',
        'device/device_manager.py',
        'device/data_processor.py',
        'device/protocol_detector.py',
        'device/alert_manager.py'
    ]),
    ('static/css', ['static/css/professional.css', 'static/css/style.css']),
    ('static/js', [
        'static/js/dashboard_pro.js',
        'static/js/oscilloscope.js',
        'static/js/spectrum.js',
        'static/js/analysis.js',
        'static/js/common.js',
        'static/js/dashboard.js',
        'static/js/history.js'
    ]),
    ('static', ['static/manifest.json']),
    ('templates', [
        'templates/base_pro.html',
        'templates/dashboard_pro.html',
        'templates/history_pro.html',
        'templates/settings_pro.html',
        'templates/base.html',
        'templates/dashboard.html',
        'templates/history.html',
        'templates/settings.html'
    ])
]

OPTIONS = {
    'argv_emulation': False,  # Don't need drag-and-drop support
    'packages': [
        'flask',
        'flask_socketio',
        'flask_cors',
        'engineio',
        'socketio',
        'usb',  # pyusb module is 'usb'
        'bleak',
        'numpy',
        'pandas',
        'dotenv',
        'dateutil'
    ],
    'includes': [
        'usb.core',
        'usb.util',
        'usb.backend',
        'usb.backend.libusb1',
        'jaraco.text',
        'jaraco.functools',
        'jaraco.context'
    ],
    'excludes': [
        'tkinter',
        'matplotlib',
        'scipy',
        'PIL',
        'IPython',
        'pyusb',  # Exclude meta-package
        'setuptools',
        'pkg_resources'
    ],
    'strip': True,  # Strip debug symbols to reduce size
    'optimize': 2,  # Optimize bytecode
    'iconfile': 'macos/icon.icns',  # App icon (we'll create this)
    'plist': {
        'CFBundleName': 'FNIRSI Monitor',
        'CFBundleDisplayName': 'FNIRSI FNB58 Monitor',
        'CFBundleIdentifier': 'com.fnirsi.monitor',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'MIT License',
        'LSMinimumSystemVersion': '10.15',  # macOS Catalina or later
        'LSUIElement': False,  # Show in Dock
        'NSHighResolutionCapable': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
        # USB permissions
        'NSAppleEventsUsageDescription': 'FNIRSI Monitor needs to access USB devices.',
        'NSBluetoothAlwaysUsageDescription': 'FNIRSI Monitor uses Bluetooth to connect to your power meter.',
        'NSBluetoothPeripheralUsageDescription': 'FNIRSI Monitor uses Bluetooth to connect to your power meter.',
    }
}

setup(
    name='FNIRSI Monitor',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
