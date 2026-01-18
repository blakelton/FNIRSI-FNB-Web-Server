"""Data Buffer - Thread-safe ring buffers for readings."""

import threading
from collections import deque
from typing import Any, Dict, List, Optional


class DataBuffer:
    """Thread-safe ring buffer for storing readings."""

    def __init__(self, maxlen: int = 2000):
        """Initialize data buffer.

        Args:
            maxlen: Maximum number of items to store
        """
        self._buffer: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._latest: Optional[Dict[str, Any]] = None

    def append(self, reading: Dict[str, Any]) -> None:
        """Add a reading to the buffer.

        Args:
            reading: Reading dictionary to add
        """
        with self._lock:
            self._buffer.append(reading)
            self._latest = reading

    def get_recent(self, n: int = 100) -> List[Dict[str, Any]]:
        """Get the n most recent readings.

        Args:
            n: Number of readings to retrieve

        Returns:
            List of reading dictionaries
        """
        with self._lock:
            return list(self._buffer)[-n:]

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """Get the most recent reading.

        Returns:
            Latest reading dictionary or None if buffer is empty
        """
        with self._lock:
            return self._latest

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all readings in the buffer.

        Returns:
            List of all reading dictionaries
        """
        with self._lock:
            return list(self._buffer)

    def clear(self) -> None:
        """Clear all readings from the buffer."""
        with self._lock:
            self._buffer.clear()
            self._latest = None

    def __len__(self) -> int:
        """Get the number of readings in the buffer."""
        with self._lock:
            return len(self._buffer)
