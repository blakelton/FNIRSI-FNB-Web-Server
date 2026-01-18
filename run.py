#!/usr/bin/env python3
"""
FNIRSI FNB48P Web Monitor - Universal Run Script

This script detects your operating system and either:
1. Runs the monitor directly if dependencies are installed
2. Offers to run the installer if dependencies are missing

Usage:
    python run.py
    python3 run.py
    python run.py --auto-install  # Non-interactive mode
"""

# Standard library imports
import argparse
import os
import platform
import subprocess
import sys

# Local imports
from shared.utils import detect_os, get_script_dir as _get_script_dir


def print_header():
    print("=" * 50)
    print("  FNIRSI FNB48P Web Monitor")
    print("=" * 50)
    print()


def get_script_dir():
    """Get the directory where this script is located."""
    return _get_script_dir(__file__)

def check_dependencies():
    """Check if required Python packages are installed."""
    missing = []

    try:
        import flask
    except ImportError:
        missing.append("flask")

    try:
        import usb.core
    except ImportError:
        missing.append("pyusb")

    return missing

def check_venv(script_dir):
    """Check if virtual environment exists and return activation info."""
    venv_dir = os.path.join(script_dir, "venv")

    if not os.path.exists(venv_dir):
        return None

    if platform.system().lower() == "windows":
        python_path = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        python_path = os.path.join(venv_dir, "bin", "python")

    if os.path.exists(python_path):
        return python_path

    return None

def run_installer(script_dir):
    """Run the universal installer."""
    installer = os.path.join(script_dir, "install.py")

    if os.path.exists(installer):
        print("[*] Running installer...")
        print()
        result = subprocess.run([sys.executable, installer], cwd=script_dir)
        return result.returncode == 0

    # Fall back to OS-specific installers
    detected_os = detect_os()

    if detected_os == "linux":
        script = os.path.join(script_dir, "install_linux.sh")
        if os.path.exists(script):
            os.chmod(script, 0o755)
            result = subprocess.run(["bash", script], cwd=script_dir)
            return result.returncode == 0

    elif detected_os == "macos":
        script = os.path.join(script_dir, "install_macos.sh")
        if os.path.exists(script):
            os.chmod(script, 0o755)
            result = subprocess.run(["bash", script], cwd=script_dir)
            return result.returncode == 0

    elif detected_os == "windows":
        script = os.path.join(script_dir, "install_windows.bat")
        if os.path.exists(script):
            result = subprocess.run([script], cwd=script_dir, shell=True)
            return result.returncode == 0

    return False

def run_monitor(script_dir, python_cmd=None):
    """Run the monitor application."""
    monitor_script = os.path.join(script_dir, "fnb48p_monitor.py")

    if not os.path.exists(monitor_script):
        print(f"[!] Error: {monitor_script} not found")
        return False

    if python_cmd is None:
        python_cmd = sys.executable

    print("[*] Starting FNIRSI FNB48P Monitor...")
    print("[*] Open http://localhost:5002 in your browser")
    print("[*] Press Ctrl+C to stop")
    print()

    try:
        result = subprocess.run([python_cmd, monitor_script], cwd=script_dir)
        return result.returncode == 0
    except KeyboardInterrupt:
        print()
        print("[*] Monitor stopped.")
        return True
    except Exception as e:
        print(f"[!] Error: {e}")
        return False

def prompt_yes_no(message, default=None):
    """
    Prompt user for yes/no response.

    Args:
        message: The prompt message
        default: Default value if input is not available (None, True, or False)

    Returns:
        bool: User's response or default
    """
    # Check if we're in a non-interactive environment
    if not sys.stdin.isatty():
        if default is not None:
            return default
        return False

    while True:
        try:
            response = input(f"{message} (y/n): ").strip().lower()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' or 'n'")
        except (EOFError, KeyboardInterrupt):
            print()
            return default if default is not None else False


def handle_missing_packages(args, script_dir, error_context=""):
    """
    Handle missing packages by prompting for installation.

    Returns:
        bool: True if installation succeeded or was skipped, False if should exit.
    """
    if error_context:
        print(f"[!] {error_context}")

    should_install = args.auto_install
    if not should_install and not args.no_install:
        should_install = prompt_yes_no("[?] Run installer to fix?", default=args.auto_install)

    if should_install:
        if run_installer(script_dir):
            return True
        print("[!] Installation failed.")
        return False

    if args.no_install:
        print("[!] Cannot run without required packages (--no-install specified).")
    else:
        print("[!] Cannot run without required packages.")
        print("    Run 'python install.py' to install dependencies.")
    return False


def ensure_dependencies_with_venv(args, script_dir, venv_python):
    """
    Ensure dependencies are available when using a virtual environment.

    Returns:
        str or None: Python command to use, or None if setup failed.
    """
    print("[*] Using virtual environment")

    # Check if venv has required packages
    result = subprocess.run(
        [venv_python, "-c", "import flask; import usb.core"],
        capture_output=True
    )

    if result.returncode == 0:
        return venv_python

    # Packages missing - try to fix
    if not handle_missing_packages(args, script_dir, "Virtual environment missing packages."):
        return None

    # Refresh venv check after installation
    return check_venv(script_dir) or venv_python


def ensure_dependencies_system(args, script_dir):
    """
    Ensure dependencies are available in system Python.

    Returns:
        str or None: Python command to use, or None if setup failed.
    """
    missing = check_dependencies()

    if not missing:
        return sys.executable

    print(f"[!] Missing packages: {', '.join(missing)}")
    print()

    if not handle_missing_packages(args, script_dir):
        return None

    # Check for venv after install (installer may create one)
    venv_python = check_venv(script_dir)
    if venv_python:
        return venv_python

    # Re-check dependencies in system Python
    missing = check_dependencies()
    if missing:
        print("[!] Dependencies still missing after install.")
        return None

    return sys.executable


def check_linux_prerequisites(detected_os):
    """Check Linux-specific prerequisites and print warnings."""
    if detected_os != "linux":
        return

    # Check for libusb
    try:
        result = subprocess.run(
            ["ldconfig", "-p"],
            capture_output=True,
            text=True
        )
        if "libusb" not in result.stdout:
            print("[!] Warning: libusb may not be installed.")
            print("    Install with: sudo apt install libusb-1.0-0-dev")
            print()
    except OSError:
        pass  # ldconfig not available, skip check

    # Check for udev rules
    if not os.path.exists("/etc/udev/rules.d/99-fnirsi.rules"):
        print("[!] Warning: USB permission rules not found.")
        print("    You may need to run as root or install udev rules.")
        print("    Run: sudo ./install_linux.sh")
        print()


def main():
    parser = argparse.ArgumentParser(description='FNIRSI FNB48P Web Monitor')
    parser.add_argument('--auto-install', action='store_true',
                        help='Automatically install dependencies without prompting')
    parser.add_argument('--no-install', action='store_true',
                        help='Do not attempt to install missing dependencies')
    args = parser.parse_args()

    print_header()

    detected_os = detect_os()
    print(f"[*] Detected OS: {detected_os or 'Unknown'}")
    print(f"[*] Python version: {platform.python_version()}")

    script_dir = get_script_dir()

    # Ensure dependencies are available
    venv_python = check_venv(script_dir)
    if venv_python:
        python_cmd = ensure_dependencies_with_venv(args, script_dir, venv_python)
    else:
        python_cmd = ensure_dependencies_system(args, script_dir)

    if python_cmd is None:
        sys.exit(1)

    print()

    # Platform-specific checks
    check_linux_prerequisites(detected_os)

    # Run the monitor
    run_monitor(script_dir, python_cmd)

if __name__ == "__main__":
    main()
