@echo off
REM FNIRSI FNB48P Web Monitor - Windows Installation Script

echo ========================================
echo   FNIRSI FNB48P Monitor - Windows Setup
echo ========================================
echo.

cd /d "%~dp0"

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python not found!
    echo.
    echo Please install Python 3.8+ from:
    echo   https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [1/3] Python %PYTHON_VERSION% found

REM Create virtual environment
echo.
echo [2/3] Setting up Python environment...

if not exist "venv" (
    echo     Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [!] Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate venv and install packages
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [!] Failed to activate virtual environment
    pause
    exit /b 1
)

echo [3/3] Installing Python packages...
pip install --upgrade pip
if errorlevel 1 (
    echo [!] Warning: Failed to upgrade pip
)

REM Check which requirements file to use
if exist "requirements-minimal.txt" (
    echo     Using requirements-minimal.txt (standalone monitor)
    pip install -r requirements-minimal.txt
) else if exist "requirements.txt" (
    echo     Using requirements.txt (full features)
    pip install -r requirements.txt
) else (
    echo     Installing minimal packages...
    pip install flask pyusb
)

if errorlevel 1 (
    echo [!] Failed to install Python packages
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo To run the monitor:
echo   run.bat
echo.
echo Or manually:
echo   venv\Scripts\activate
echo   python fnb48p_monitor.py
echo.
echo Then open: http://localhost:5002
echo.
echo ----------------------------------------
echo IMPORTANT: Windows USB Driver Setup
echo ----------------------------------------
echo.
echo You may need to install the libusb driver using Zadig:
echo   1. Download Zadig from: https://zadig.akeo.ie/
echo   2. Connect your FNIRSI device
echo   3. Run Zadig, select your device (FNIRSI USB Tester)
echo   4. Install "libusb-win32" or "WinUSB" driver
echo.
echo For full features (professional mode, etc.):
echo   pip install -r requirements.txt
echo.
pause
