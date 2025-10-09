# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for FNIRSI FNB58 Monitor
Creates a standalone macOS application bundle
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files from templates and static folders
datas = [
    ('templates', 'templates'),
    ('static', 'static'),
    ('device', 'device'),
    ('config.py', '.'),
    ('app.py', '.'),
]

# Collect all eventlet and dns modules
datas += collect_data_files('eventlet')
datas += collect_data_files('dns')

# Collect all Flask and SocketIO related modules
hiddenimports = collect_submodules('eventlet') + collect_submodules('dns') + [
    'flask',
    'flask_socketio',
    'flask_cors',
    'engineio',
    'socketio',
    'simple_websocket',
    'wsproto',
    'h11',
    'eventlet',
    'eventlet.hubs',
    'eventlet.hubs.epolls',
    'eventlet.hubs.kqueue',
    'eventlet.hubs.selects',
    'eventlet.green',
    'eventlet.green.socket',
    'eventlet.green.threading',
    'eventlet.green.ssl',
    'eventlet.support',
    'dns',
    'dns.resolver',
    'greenlet',
    'usb.core',
    'usb.util',
    'usb.backend',
    'usb.backend.libusb1',
    'bleak',
    'bleak.backends.corebluetooth',
    'numpy',
    'pandas',
    'dotenv',
    'dateutil',
    'werkzeug',
    'jinja2',
    'click',
    'itsdangerous',
    'markupsafe',
    'bidict',
]

# Add all device module submodules
hiddenimports += [
    'device.usb_reader',
    'device.bluetooth_reader',
    'device.device_manager',
    'device.data_processor',
    'device.protocol_detector',
    'device.alert_manager',
]

a = Analysis(
    ['start.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'PIL', 'IPython'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FNIRSI Monitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='macos/icon.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FNIRSI Monitor',
)

app = BUNDLE(
    coll,
    name='FNIRSI Monitor.app',
    icon='macos/icon.icns',
    bundle_identifier='com.fnirsi.monitor',
    info_plist={
        'CFBundleName': 'FNIRSI Monitor',
        'CFBundleDisplayName': 'FNIRSI FNB58 Monitor',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'MIT License',
        'LSMinimumSystemVersion': '10.15',
        'NSHighResolutionCapable': True,
        'NSBluetoothAlwaysUsageDescription': 'FNIRSI Monitor uses Bluetooth to connect to your power meter.',
        'NSBluetoothPeripheralUsageDescription': 'FNIRSI Monitor uses Bluetooth to connect to your power meter.',
    },
)
