# FNIRSI FNB48P Web Monitor - Windows Run Script (PowerShell)

Write-Host "========================================"
Write-Host "  FNIRSI FNB48P Web Monitor"
Write-Host "========================================"
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$VenvDir = Join-Path $ScriptDir "venv"
$VenvActivate = Join-Path $VenvDir "Scripts\Activate.ps1"

# Check if venv exists
if (Test-Path $VenvActivate) {
    Write-Host "[*] Using virtual environment"
    & $VenvActivate
} else {
    Write-Host "[!] Virtual environment not found."
    Write-Host "    Running install script..."
    Write-Host ""

    $InstallScript = Join-Path $ScriptDir "install_windows.ps1"
    & $InstallScript

    if (-not (Test-Path $VenvActivate)) {
        Write-Host "[!] Installation failed." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }

    & $VenvActivate
}

# Check for Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[*] $pythonVersion"
} catch {
    Write-Host "[!] Python not found!" -ForegroundColor Red
    Write-Host "    Please install Python 3.8+ from https://www.python.org/"
    Write-Host "    Make sure to check 'Add Python to PATH' during installation."
    Read-Host "Press Enter to exit"
    exit 1
}

# Check for required packages
Write-Host "[*] Checking dependencies..."

$flaskInstalled = python -c "import flask" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Flask not found. Installing..."
    pip install flask
}

$pyusbInstalled = python -c "import usb.core" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] PyUSB not found. Installing..."
    pip install pyusb libusb
}

Write-Host ""
Write-Host "[*] Starting FNIRSI FNB48P Monitor..."
Write-Host "[*] Open http://localhost:5002 in your browser"
Write-Host "[*] Press Ctrl+C to stop"
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Yellow
Write-Host "NOTE: If the device is not detected, you may need to" -ForegroundColor Yellow
Write-Host "install the libusb driver using Zadig:" -ForegroundColor Yellow
Write-Host "  1. Download from https://zadig.akeo.ie/" -ForegroundColor Yellow
Write-Host "  2. Connect your FNIRSI device" -ForegroundColor Yellow
Write-Host "  3. Select your device in Zadig" -ForegroundColor Yellow
Write-Host "  4. Install libusb-win32 or WinUSB driver" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow
Write-Host ""

python fnb48p_monitor.py
