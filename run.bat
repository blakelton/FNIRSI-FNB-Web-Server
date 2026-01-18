@echo off
REM FNIRSI FNB48P Web Monitor - Windows Run Script

echo ========================================
echo   FNIRSI FNB48P Web Monitor
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
echo [*] Starting FNIRSI FNB48P Monitor...
echo [*] Open http://localhost:5002 in your browser
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

python fnb48p_monitor.py

pause
