@echo off
REM FNIRSI USB Power Monitor - Windows Run Script
REM Supports USB and Bluetooth connections

echo ========================================
echo   FNIRSI USB Power Monitor
echo ========================================
echo.

cd /d "%~dp0"

REM Check if venv exists
if exist "venv\Scripts\activate.bat" (
    echo [*] Using virtual environment
    call venv\Scripts\activate.bat
) else (
    echo [!] Virtual environment not found.
    echo     Running install script...
    echo.
    call install_windows.bat
    if errorlevel 1 (
        echo [!] Installation failed.
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
)

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python not found!
    echo     Please install Python 3.8+ from https://www.python.org/
    echo     Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [*] Python found
python --version

REM Check for required packages
echo [*] Checking dependencies...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [!] Flask not found. Installing...
    pip install flask
)

python -c "import usb.core" >nul 2>&1
if errorlevel 1 (
    echo [!] PyUSB not found. Installing...
    pip install pyusb libusb
)

echo.
echo [*] Starting FNIRSI USB Monitor...
echo [*] Web interface: http://localhost:5002
echo [*] Press Ctrl+C to stop
echo.
echo ----------------------------------------
echo NOTE: If the device is not detected, you may need to
echo install the libusb driver using Zadig:
echo   1. Download from https://zadig.akeo.ie/
echo   2. Connect your FNIRSI device
echo   3. Select your device in Zadig
echo   4. Install libusb-win32 or WinUSB driver
echo ----------------------------------------
echo.

REM Open browser after delay
if not "%1"=="--no-browser" (
    start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5002"
)

REM Use app.py for full USB + Bluetooth support
REM Use fnb48p_monitor.py for USB-only lightweight mode
python app.py

pause
