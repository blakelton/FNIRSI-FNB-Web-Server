#!/usr/bin/env python3
"""
FNIRSI FNB48P Web Monitor - Universal Installer

This script detects your operating system and runs the appropriate
installation script automatically.

Usage:
    python install.py
    python3 install.py
"""

# Standard library imports
import os
import platform
import shutil
import subprocess
import sys

# Local imports
from shared.utils import detect_os, get_script_dir as _get_script_dir


def print_header():
    print("=" * 50)
    print("  FNIRSI FNB48P Web Monitor - Universal Installer")
    print("=" * 50)
    print()


def get_script_dir():
    """Get the directory where this script is located."""
    return _get_script_dir(__file__)

def run_shell_installer(script_dir, script_name):
    """
    Run a shell installation script.

    Args:
        script_dir: Directory containing the script.
        script_name: Name of the shell script file.

    Returns:
        bool: True if installation succeeded, False otherwise.
    """
    script_path = os.path.join(script_dir, script_name)

    if not os.path.exists(script_path):
        print(f"[!] Error: {script_path} not found")
        return False

    # Make sure it's executable
    os.chmod(script_path, 0o755)

    print(f"[*] Running: {script_path}")
    print()

    try:
        result = subprocess.run(["bash", script_path], cwd=script_dir)
        return result.returncode == 0
    except OSError as e:
        print(f"[!] Error running installer: {e}")
        return False


def run_linux_installer(script_dir):
    """Run the Linux installation script."""
    return run_shell_installer(script_dir, "install_linux.sh")


def run_macos_installer(script_dir):
    """Run the macOS installation script."""
    return run_shell_installer(script_dir, "install_macos.sh")

def run_windows_installer(script_dir):
    """Run the Windows installation script."""
    # Try PowerShell first, fall back to batch
    ps_script = os.path.join(script_dir, "install_windows.ps1")
    bat_script = os.path.join(script_dir, "install_windows.bat")

    # Check if PowerShell is available
    powershell_path = shutil.which("powershell")

    if powershell_path and os.path.exists(ps_script):
        print(f"[*] Running PowerShell installer: {ps_script}")
        print()
        try:
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script],
                cwd=script_dir
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[!] PowerShell failed: {e}")
            print("[*] Falling back to batch script...")

    # Fall back to batch script
    if os.path.exists(bat_script):
        print(f"[*] Running batch installer: {bat_script}")
        print()
        try:
            result = subprocess.run([bat_script], cwd=script_dir, shell=True)
            return result.returncode == 0
        except Exception as e:
            print(f"[!] Error running installer: {e}")
            return False

    print("[!] No Windows installer script found")
    return False

def check_python_version():
    """Check if Python version is adequate."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"[!] Warning: Python 3.8+ recommended (you have {version.major}.{version.minor})")
        return False
    return True

def main():
    print_header()

    # Check Python version
    print(f"[*] Python version: {platform.python_version()}")
    check_python_version()

    # Detect OS
    detected_os = detect_os()
    print(f"[*] Detected OS: {detected_os or 'Unknown'}")
    print()

    if not detected_os:
        print("[!] Unable to detect operating system.")
        print("    Supported platforms: Linux, macOS, Windows")
        print()
        print("    Please run the appropriate installer manually:")
        print("      Linux:   ./install_linux.sh")
        print("      macOS:   ./install_macos.sh")
        print("      Windows: install_windows.bat or install_windows.ps1")
        sys.exit(1)

    script_dir = get_script_dir()
    success = False

    if detected_os == "linux":
        success = run_linux_installer(script_dir)
    elif detected_os == "macos":
        success = run_macos_installer(script_dir)
    elif detected_os == "windows":
        success = run_windows_installer(script_dir)

    print()
    if success:
        print("=" * 50)
        print("  Installation Complete!")
        print("=" * 50)
        print()
        print("To run the monitor:")
        if detected_os == "windows":
            print("  run.bat")
            print("  or: .\\run.ps1")
        else:
            print("  ./run.sh")
        print()
        print("Then open: http://localhost:5002")
    else:
        print("=" * 50)
        print("  Installation may have encountered issues")
        print("=" * 50)
        print()
        print("Please check the output above for errors.")
        print("You can also try running the installer manually:")
        if detected_os == "linux":
            print("  ./install_linux.sh")
        elif detected_os == "macos":
            print("  ./install_macos.sh")
        elif detected_os == "windows":
            print("  install_windows.ps1 (PowerShell)")
            print("  install_windows.bat (Command Prompt)")
        sys.exit(1)

if __name__ == "__main__":
    main()
