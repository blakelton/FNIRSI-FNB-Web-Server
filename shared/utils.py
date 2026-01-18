"""
Shared utility functions for FNIRSI Web Monitor.

This module contains common functions used across multiple scripts
to avoid code duplication.
"""

import platform
from pathlib import Path
from typing import Optional, Union


def detect_os() -> Optional[str]:
    """
    Detect the operating system.

    Returns:
        str or None: 'linux', 'macos', 'windows', or None if unknown.
    """
    system = platform.system().lower()

    if system == "linux":
        return "linux"
    elif system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    else:
        return None


def get_script_dir(file_path: Union[str, Path]) -> str:
    """
    Get the directory where a script is located.

    Args:
        file_path: The __file__ attribute of the calling script.

    Returns:
        str: Absolute path to the directory containing the script.
    """
    return str(Path(file_path).resolve().parent)
