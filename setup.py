#!/usr/bin/env python3
"""
FNIRSI USB Tester Web Monitor - Setup Wizard

Complete installation with:
- Virtual environment creation
- Dependency installation
- Desktop launcher creation
- udev rules setup (Linux)
- System integration

Usage:
    python setup.py           # Interactive setup
    python setup.py --full    # Full install with all options
    python setup.py --minimal # Minimal install (deps only)
"""

import os
import sys
import platform
import subprocess
import shutil
import argparse
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

APP_NAME = "FNIRSI USB Monitor"
APP_ID = "fnirsi-usb-monitor"
APP_VERSION = "1.1.0"
PYTHON_MIN_VERSION = (3, 8)
DEFAULT_PORT = 5002

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Disable colors on Windows unless using Windows Terminal
if platform.system() == 'Windows' and 'WT_SESSION' not in os.environ:
    for attr in dir(Colors):
        if not attr.startswith('_'):
            setattr(Colors, attr, '')


# ============================================================
# Utility Functions
# ============================================================

def print_header():
    """Print application header."""
    print()
    print(f"{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {APP_NAME} - Setup Wizard v{APP_VERSION}{Colors.END}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.END}")
    print()


def print_step(step_num, total, message):
    """Print a step indicator."""
    print(f"{Colors.BLUE}[{step_num}/{total}]{Colors.END} {message}")


def print_success(message):
    """Print success message."""
    print(f"  {Colors.GREEN}✓{Colors.END} {message}")


def print_warning(message):
    """Print warning message."""
    print(f"  {Colors.YELLOW}⚠{Colors.END} {message}")


def print_error(message):
    """Print error message."""
    print(f"  {Colors.RED}✗{Colors.END} {message}")


def print_info(message):
    """Print info message."""
    print(f"  {Colors.CYAN}ℹ{Colors.END} {message}")


def ask_yes_no(question, default=True):
    """Ask a yes/no question."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"  {question} [{default_str}]: ").strip().lower()
        if response == '':
            return default
        if response in ('y', 'yes'):
            return True
        if response in ('n', 'no'):
            return False
        print("  Please enter 'y' or 'n'")


def run_command(cmd, capture=False, check=True):
    """Run a shell command."""
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, check=check)
            return True
    except subprocess.CalledProcessError as e:
        if capture:
            return None
        return False
    except FileNotFoundError:
        return None if capture else False


def get_project_dir():
    """Get the project directory."""
    return Path(__file__).parent.resolve()


def get_venv_python():
    """Get the path to venv Python executable."""
    project_dir = get_project_dir()
    if platform.system() == 'Windows':
        return project_dir / 'venv' / 'Scripts' / 'python.exe'
    return project_dir / 'venv' / 'bin' / 'python'


def get_os_type():
    """Detect operating system."""
    system = platform.system().lower()
    if system == 'linux':
        return 'linux'
    elif system == 'darwin':
        return 'macos'
    elif system == 'windows':
        return 'windows'
    return None


# ============================================================
# Installation Steps
# ============================================================

def check_system_requirements():
    """Check system requirements."""
    print_step(1, 6, "Checking system requirements...")

    errors = []

    # Check Python version
    py_version = sys.version_info[:2]
    if py_version >= PYTHON_MIN_VERSION:
        print_success(f"Python {py_version[0]}.{py_version[1]} (>= {PYTHON_MIN_VERSION[0]}.{PYTHON_MIN_VERSION[1]} required)")
    else:
        print_error(f"Python {py_version[0]}.{py_version[1]} (>= {PYTHON_MIN_VERSION[0]}.{PYTHON_MIN_VERSION[1]} required)")
        errors.append("Python version too old")

    # Check pip
    if shutil.which('pip') or shutil.which('pip3'):
        print_success("pip is available")
    else:
        print_error("pip not found")
        errors.append("pip not installed")

    # Check OS
    os_type = get_os_type()
    if os_type:
        print_success(f"Operating system: {platform.system()}")
    else:
        print_warning(f"Unknown OS: {platform.system()}")

    # Check git (optional)
    if shutil.which('git'):
        print_success("git is available")
    else:
        print_info("git not found (optional)")

    print()
    return len(errors) == 0


def create_virtual_environment():
    """Create Python virtual environment."""
    print_step(2, 6, "Setting up Python virtual environment...")

    project_dir = get_project_dir()
    venv_dir = project_dir / 'venv'

    if venv_dir.exists():
        print_info("Virtual environment already exists")
        if not ask_yes_no("Recreate virtual environment?", default=False):
            print_success("Using existing virtual environment")
            return True
        shutil.rmtree(venv_dir)

    # Create venv
    print_info("Creating virtual environment...")
    result = run_command([sys.executable, '-m', 'venv', str(venv_dir)])

    if result and venv_dir.exists():
        print_success("Virtual environment created")
        return True
    else:
        print_error("Failed to create virtual environment")
        return False


def install_dependencies():
    """Install Python dependencies."""
    print_step(3, 6, "Installing dependencies...")

    project_dir = get_project_dir()
    venv_python = get_venv_python()

    if not venv_python.exists():
        print_error("Virtual environment not found")
        return False

    # Upgrade pip first
    print_info("Upgrading pip...")
    run_command([str(venv_python), '-m', 'pip', 'install', '--upgrade', 'pip'], check=False)

    # Install requirements
    requirements_file = project_dir / 'requirements.txt'
    if requirements_file.exists():
        print_info("Installing from requirements.txt...")
        result = run_command([str(venv_python), '-m', 'pip', 'install', '-r', str(requirements_file)])
        if result:
            print_success("Dependencies installed")
            return True
        else:
            print_error("Failed to install dependencies")
            return False
    else:
        # Install minimal dependencies
        print_info("Installing minimal dependencies...")
        deps = ['flask', 'flask-socketio', 'flask-cors', 'pyusb', 'bleak']
        result = run_command([str(venv_python), '-m', 'pip', 'install'] + deps)
        if result:
            print_success("Dependencies installed")
            return True
        else:
            print_error("Failed to install dependencies")
            return False


def setup_udev_rules():
    """Set up udev rules for USB access (Linux only)."""
    if get_os_type() != 'linux':
        return True

    print_step(4, 6, "Setting up USB permissions (Linux)...")

    udev_rule = '''# FNIRSI USB Testers
# FNB48P/FNB48S
SUBSYSTEM=="usb", ATTR{idVendor}=="2e3c", ATTR{idProduct}=="0049", MODE="0666", GROUP="plugdev"
# FNB58
SUBSYSTEM=="usb", ATTR{idVendor}=="2e3c", ATTR{idProduct}=="5558", MODE="0666", GROUP="plugdev"
# FNB48
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="003a", MODE="0666", GROUP="plugdev"
# C1
SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="003b", MODE="0666", GROUP="plugdev"
'''

    rules_file = Path('/etc/udev/rules.d/99-fnirsi.rules')

    # Check if already installed
    if rules_file.exists():
        print_info("udev rules already installed")
        return True

    # Check if we have sudo access
    if os.geteuid() != 0:
        print_warning("Root access required for udev rules")
        if ask_yes_no("Install udev rules with sudo?", default=True):
            # Write to temp file and move with sudo
            temp_file = Path('/tmp/99-fnirsi.rules')
            temp_file.write_text(udev_rule)

            result = run_command(['sudo', 'mv', str(temp_file), str(rules_file)], check=False)
            if result:
                run_command(['sudo', 'udevadm', 'control', '--reload-rules'], check=False)
                run_command(['sudo', 'udevadm', 'trigger'], check=False)
                print_success("udev rules installed")
                print_info("You may need to reconnect your USB device")
                return True
            else:
                print_warning("Could not install udev rules (requires sudo)")
                print_info("Run manually: sudo cp /tmp/99-fnirsi.rules /etc/udev/rules.d/")
        else:
            print_info("Skipping udev rules (USB may require root access)")

    return True


def create_desktop_launcher():
    """Create desktop launcher/shortcut."""
    print_step(5, 6, "Creating desktop launcher...")

    os_type = get_os_type()
    project_dir = get_project_dir()

    if os_type == 'linux':
        return create_linux_launcher(project_dir)
    elif os_type == 'macos':
        return create_macos_launcher(project_dir)
    elif os_type == 'windows':
        return create_windows_launcher(project_dir)
    else:
        print_warning("Desktop launcher not supported on this OS")
        return True


def create_linux_launcher(project_dir):
    """Create Linux .desktop file."""
    # Use SVG icon (better quality, no conversion needed)
    icon_path = project_dir / 'static' / 'icons' / 'fnirsi-monitor.svg'

    desktop_entry = f'''[Desktop Entry]
Version=1.0
Type=Application
Name={APP_NAME}
Comment=Real-time USB power monitoring for FNIRSI devices
Exec={project_dir}/run.sh
Icon={icon_path}
Terminal=true
Categories=Utility;Development;Electronics;
Keywords=USB;Power;Monitor;FNIRSI;Voltage;Current;
StartupNotify=true
'''

    # Verify icon exists
    if not icon_path.exists():
        print_warning("Icon file not found, launcher will use default icon")

    # Install icons to user's icon theme for better integration
    icons_src = project_dir / 'static' / 'icons'
    icon_sizes = [16, 32, 48, 64, 128, 256]

    for size in icon_sizes:
        src_icon = icons_src / f'fnirsi-monitor-{size}.png'
        if src_icon.exists():
            dest_dir = Path.home() / '.local' / 'share' / 'icons' / 'hicolor' / f'{size}x{size}' / 'apps'
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(src_icon, dest_dir / f'{APP_ID}.png')

    # Also install scalable SVG
    svg_icon = icons_src / 'fnirsi-monitor.svg'
    if svg_icon.exists():
        scalable_dir = Path.home() / '.local' / 'share' / 'icons' / 'hicolor' / 'scalable' / 'apps'
        scalable_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(svg_icon, scalable_dir / f'{APP_ID}.svg')

    # Update icon cache
    run_command(['gtk-update-icon-cache', str(Path.home() / '.local' / 'share' / 'icons' / 'hicolor')], check=False)

    # Try to install to user applications
    desktop_dir = Path.home() / '.local' / 'share' / 'applications'
    desktop_dir.mkdir(parents=True, exist_ok=True)

    desktop_file = desktop_dir / f'{APP_ID}.desktop'

    try:
        desktop_file.write_text(desktop_entry)
        desktop_file.chmod(0o755)
        print_success(f"Desktop launcher created: {desktop_file}")
        print_success("Application icons installed to user icon theme")

        # Update desktop database
        run_command(['update-desktop-database', str(desktop_dir)], check=False)

        return True
    except Exception as e:
        print_warning(f"Could not create desktop launcher: {e}")
        return True


def create_macos_launcher(project_dir):
    """Create macOS app launcher script."""
    # Create a simple shell script that can be added to Dock
    launcher_script = f'''#!/bin/bash
cd "{project_dir}"
./run.sh &
sleep 2
open "http://localhost:{DEFAULT_PORT}"
'''

    launcher_path = project_dir / 'FNIRSI Monitor.command'

    try:
        launcher_path.write_text(launcher_script)
        launcher_path.chmod(0o755)
        print_success(f"macOS launcher created: {launcher_path}")
        print_info("You can drag this file to your Dock for quick access")
        return True
    except Exception as e:
        print_warning(f"Could not create launcher: {e}")
        return True


def create_windows_launcher(project_dir):
    """Create Windows shortcut and batch launcher."""
    # Create a VBS script to launch without console window
    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{project_dir}"
WshShell.Run "run.bat", 0, False
WScript.Sleep 2000
WshShell.Run "http://localhost:{DEFAULT_PORT}"
'''

    # Also create a simple batch file for desktop
    batch_content = f'''@echo off
cd /d "{project_dir}"
start "" run.bat
timeout /t 2 /nobreak > nul
start "" "http://localhost:{DEFAULT_PORT}"
'''

    try:
        # Create VBS launcher (hidden console)
        vbs_path = project_dir / 'FNIRSI Monitor.vbs'
        vbs_path.write_text(vbs_content)
        print_success(f"Windows launcher created: {vbs_path}")

        # Create batch launcher
        batch_path = project_dir / 'Start Monitor.bat'
        batch_path.write_text(batch_content)
        print_success(f"Batch launcher created: {batch_path}")

        # Try to create desktop shortcut
        desktop = Path.home() / 'Desktop'
        if desktop.exists():
            shortcut_batch = desktop / 'FNIRSI Monitor.bat'
            shortcut_batch.write_text(batch_content)
            print_success(f"Desktop shortcut created: {shortcut_batch}")

        return True
    except Exception as e:
        print_warning(f"Could not create launcher: {e}")
        return True


def print_completion_message():
    """Print setup completion message."""
    print_step(6, 6, "Setup complete!")
    print()

    os_type = get_os_type()
    project_dir = get_project_dir()

    print(f"{Colors.GREEN}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}  Installation Complete!{Colors.END}")
    print(f"{Colors.GREEN}{'=' * 60}{Colors.END}")
    print()

    print(f"{Colors.BOLD}To start the monitor:{Colors.END}")
    print()

    if os_type == 'linux':
        print(f"  Option 1: Use the desktop launcher (search for '{APP_NAME}')")
        print(f"  Option 2: Run from terminal:")
        print(f"            cd {project_dir}")
        print(f"            ./run.sh")
    elif os_type == 'macos':
        print(f"  Option 1: Double-click 'FNIRSI Monitor.command'")
        print(f"  Option 2: Run from terminal:")
        print(f"            cd {project_dir}")
        print(f"            ./run.sh")
    elif os_type == 'windows':
        print(f"  Option 1: Double-click 'Start Monitor.bat' on your desktop")
        print(f"  Option 2: Run from command prompt:")
        print(f"            cd {project_dir}")
        print(f"            run.bat")

    print()
    print(f"{Colors.BOLD}Web interface:{Colors.END} http://localhost:{DEFAULT_PORT}")
    print()

    print(f"{Colors.CYAN}Tip:{Colors.END} Connect your FNIRSI device via USB or Bluetooth,")
    print(f"     then click 'Connect' in the web interface.")
    print()


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description=f'{APP_NAME} Setup Wizard')
    parser.add_argument('--full', action='store_true', help='Full install with all options')
    parser.add_argument('--minimal', action='store_true', help='Minimal install (dependencies only)')
    parser.add_argument('--no-launcher', action='store_true', help='Skip desktop launcher creation')
    parser.add_argument('--no-udev', action='store_true', help='Skip udev rules setup (Linux)')
    args = parser.parse_args()

    print_header()

    # Step 1: Check requirements
    if not check_system_requirements():
        print_error("System requirements not met. Please fix the issues above.")
        sys.exit(1)

    # Step 2: Create virtual environment
    if not create_virtual_environment():
        print_error("Failed to create virtual environment")
        sys.exit(1)
    print()

    # Step 3: Install dependencies
    if not install_dependencies():
        print_error("Failed to install dependencies")
        sys.exit(1)
    print()

    # Step 4: Setup udev rules (Linux only)
    if not args.no_udev and not args.minimal:
        setup_udev_rules()
        print()

    # Step 5: Create desktop launcher
    if not args.no_launcher and not args.minimal:
        create_desktop_launcher()
        print()

    # Step 6: Done
    print_completion_message()


if __name__ == '__main__':
    main()
