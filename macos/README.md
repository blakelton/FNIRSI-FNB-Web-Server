# FNIRSI Monitor - Native macOS App

This directory contains resources for building the native macOS application.

## Building the App

### Prerequisites

```bash
# Install py2app
pip install py2app

# Install librsvg for icon generation (one-time)
brew install librsvg
```

### Build Steps

1. **Create the app icon:**
```bash
cd macos
./create_icon.sh
```

2. **Build the standalone Python app:**
```bash
cd ..
python setup.py py2app
```

3. **Test the app:**
```bash
open dist/start.app
```

The app will be created in `dist/start.app` with all Python dependencies bundled.

### App Structure

```
start.app/
├── Contents/
│   ├── Info.plist          # App metadata
│   ├── MacOS/
│   │   └── start           # Executable
│   ├── Resources/
│   │   ├── icon.icns       # App icon
│   │   ├── lib/            # Python libraries
│   │   ├── static/         # Web assets
│   │   └── templates/      # HTML templates
│   └── Frameworks/         # Python runtime
```

## Distribution

### Option 1: Direct Distribution

1. Compress the app:
```bash
cd dist
zip -r "FNIRSI Monitor.app.zip" start.app
```

2. Share the zip file with users
3. Users extract and drag to Applications folder

### Option 2: DMG Installer (Professional)

1. **Install create-dmg:**
```bash
brew install create-dmg
```

2. **Create DMG:**
```bash
create-dmg \
  --volname "FNIRSI Monitor" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "start.app" 200 190 \
  --hide-extension "start.app" \
  --app-drop-link 600 185 \
  "FNIRSI-Monitor-Installer.dmg" \
  "dist/start.app"
```

3. Distribute the DMG file

### Option 3: Mac App Store

Requirements:
- Apple Developer Account ($99/year)
- Code signing certificate
- App sandboxing
- Entitlements configuration

**Note:** App Store distribution requires significant additional work due to sandboxing restrictions on USB/Bluetooth access.

## Development

### Modifying the App

After making changes to Python code:

```bash
# Clean previous build
rm -rf build dist

# Rebuild
python setup.py py2app

# Test
open dist/start.app
```

### Debugging

View app logs:
```bash
# Run app from terminal to see console output
./dist/start.app/Contents/MacOS/start
```

### App Icon

The app icon is generated from `icon.svg`. To customize:

1. Edit `icon.svg` with your design tool
2. Run `./create_icon.sh` to regenerate `icon.icns`
3. Rebuild the app

## Features

The macOS native app includes:

- ✅ Standalone executable (no Python installation required)
- ✅ Full USB support via PyUSB
- ✅ Bluetooth support via Bleak
- ✅ Native macOS icon and UI integration
- ✅ Runs Flask server locally on port 5000
- ✅ Opens default browser to http://localhost:5000
- ✅ All web UI features available

## Troubleshooting

### "App is damaged" error

macOS Gatekeeper blocks unsigned apps. Users need to:

1. Right-click the app
2. Select "Open"
3. Click "Open" in the dialog

Or remove the quarantine attribute:
```bash
xattr -cr start.app
```

### USB device not detected

Ensure user has permissions to access USB devices:

```bash
# Check USB devices
system_profiler SPUSBDataType

# May need to run app with sudo (not recommended)
sudo ./dist/start.app/Contents/MacOS/start
```

### Bluetooth not working

Grant Bluetooth permissions in System Settings:
- Privacy & Security → Bluetooth → Enable for the app

### App won't launch

Check Console.app for crash logs:
1. Open Console.app
2. Search for "start"
3. Look for crash reports

## Code Signing (Optional)

For professional distribution:

```bash
# Get your Developer ID
security find-identity -v -p codesigning

# Sign the app
codesign --force --deep --sign "Developer ID Application: Your Name" dist/start.app

# Verify signature
codesign -dv --verbose=4 dist/start.app

# Notarize with Apple (requires Xcode)
xcrun altool --notarize-app \
  --primary-bundle-id "com.fnirsi.monitor" \
  --username "your@email.com" \
  --password "@keychain:AC_PASSWORD" \
  --file "FNIRSI-Monitor.dmg"
```

## Next Steps: Native Swift UI

For a fully native macOS app with SwiftUI:

1. Create Xcode project (see `FNIRSI-Monitor/` directory)
2. SwiftUI frontend communicates with Python backend
3. Native menu bar integration
4. System tray icon
5. Auto-launch on startup

The Swift app will use this Python bundle as its backend.

---

## License

MIT License - See ../LICENSE
