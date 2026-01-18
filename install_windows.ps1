# FNIRSI FNB48P Web Monitor - Windows Installation Script (PowerShell)

Write-Host "========================================"
Write-Host "  FNIRSI FNB48P Monitor - Windows Setup"
Write-Host "========================================"
Write-Host ""

$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Check for Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[1/3] $pythonVersion"
} catch {
    Write-Host "[!] Python not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.8+ from:"
    Write-Host "  https://www.python.org/downloads/"
    Write-Host ""
    Write-Host "Make sure to check 'Add Python to PATH' during installation."
    Read-Host "Press Enter to exit"
    exit 1
}

# Create virtual environment
$VenvDir = Join-Path $ScriptDir "venv"

Write-Host ""
Write-Host "[2/3] Setting up Python environment..."

if (-not (Test-Path $VenvDir)) {
    Write-Host "    Creating virtual environment..."
    try {
        python -m venv $VenvDir
    } catch {
        Write-Host "[!] Failed to create virtual environment" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Activate venv and install packages
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
try {
    & $ActivateScript
} catch {
    Write-Host "[!] Failed to activate virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[3/3] Installing Python packages..."

try {
    pip install --upgrade pip
} catch {
    Write-Host "[!] Warning: Failed to upgrade pip" -ForegroundColor Yellow
}

# Check which requirements file to use
$ReqMinimal = Join-Path $ScriptDir "requirements-minimal.txt"
$ReqFull = Join-Path $ScriptDir "requirements.txt"

try {
    if (Test-Path $ReqMinimal) {
        Write-Host "    Using requirements-minimal.txt (standalone monitor)"
        pip install -r $ReqMinimal
    } elseif (Test-Path $ReqFull) {
        Write-Host "    Using requirements.txt (full features)"
        pip install -r $ReqFull
    } else {
        Write-Host "    Installing minimal packages..."
        pip install flask pyusb
    }
} catch {
    Write-Host "[!] Failed to install Python packages" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "========================================"
Write-Host "  Installation Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "To run the monitor:"
Write-Host "  .\run.ps1"
Write-Host ""
Write-Host "Or manually:"
Write-Host "  .\venv\Scripts\Activate.ps1"
Write-Host "  python fnb48p_monitor.py"
Write-Host ""
Write-Host "Then open: http://localhost:5002"
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Yellow
Write-Host "IMPORTANT: Windows USB Driver Setup" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow
Write-Host ""
Write-Host "You may need to install the libusb driver using Zadig:"
Write-Host "  1. Download Zadig from: https://zadig.akeo.ie/"
Write-Host "  2. Connect your FNIRSI device"
Write-Host "  3. Run Zadig, select your device (FNIRSI USB Tester)"
Write-Host "  4. Install 'libusb-win32' or 'WinUSB' driver"
Write-Host ""
Write-Host "For full features (professional mode, etc.):"
Write-Host "  pip install -r requirements.txt"
Write-Host ""
Read-Host "Press Enter to continue"
