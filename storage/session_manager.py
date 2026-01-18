"""Session Manager - Recording sessions and session storage."""

import csv
import io
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class SessionManager:
    """Manages recording sessions and session storage.

    Thread-safe: All public methods are synchronized.
    """

    def __init__(self, storage_dir: Path):
        """Initialize session manager with storage directory.

        Args:
            storage_dir: Directory to store session files
        """
        self._lock = threading.Lock()
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(exist_ok=True)

        # Recording state
        self._is_recording = False
        self._recording_data: List[Dict[str, Any]] = []
        self._recording_start_time: Optional[datetime] = None
        self._recording_name: Optional[str] = None

    @property
    def is_recording(self) -> bool:
        """Thread-safe access to recording state."""
        with self._lock:
            return self._is_recording

    @property
    def recording_data(self) -> List[Dict[str, Any]]:
        """Thread-safe access to recording data (returns copy)."""
        with self._lock:
            return self._recording_data.copy()

    def start_recording(self, name: Optional[str] = None) -> str:
        """Start recording data to a session.

        Args:
            name: Optional session name. Auto-generated if not provided.

        Returns:
            The session name
        """
        with self._lock:
            self._is_recording = True
            self._recording_data = []
            self._recording_start_time = datetime.now()
            self._recording_name = name or f"session_{self._recording_start_time.strftime('%Y%m%d_%H%M%S')}"
            return self._recording_name

    def stop_recording(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Stop recording and save the session.

        Args:
            stats: Statistics dictionary for the session

        Returns:
            The saved session data
        """
        with self._lock:
            self._is_recording = False
            session = {
                'name': self._recording_name,
                'start_time': self._recording_start_time.isoformat() if self._recording_start_time else None,
                'end_time': datetime.now().isoformat(),
                'samples': len(self._recording_data),
                'stats': stats,
                'data': self._recording_data.copy()
            }

            session_file = self.storage_dir / f"{self._recording_name}.json"
            session_file.write_text(json.dumps(session))

            return session

    def add_reading(self, reading: Dict[str, Any]) -> None:
        """Add a reading to the current recording.

        Args:
            reading: Reading dictionary to add
        """
        with self._lock:
            if self._is_recording:
                self._recording_data.append(reading)

    def get_status(self) -> Dict[str, Any]:
        """Get the current recording status.

        Returns:
            Dictionary with recording status information
        """
        with self._lock:
            return {
                'is_recording': self._is_recording,
                'name': self._recording_name,
                'samples': len(self._recording_data),
                'start_time': self._recording_start_time.isoformat() if self._recording_start_time else None,
            }

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all saved sessions.

        Returns:
            List of session metadata dictionaries
        """
        sessions = []
        for filepath in self.storage_dir.glob('*.json'):
            if filepath.name == 'settings.json':
                continue
            try:
                data = json.loads(filepath.read_text())
                sessions.append({
                    'name': data.get('name', filepath.stem),
                    'start_time': data.get('start_time'),
                    'end_time': data.get('end_time'),
                    'samples': data.get('samples', 0),
                    'filename': filepath.name
                })
            except (OSError, json.JSONDecodeError, KeyError):
                pass  # Skip corrupt or unreadable session files
        return sorted(sessions, key=lambda x: x.get('start_time', ''), reverse=True)

    def get_session(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a saved session by name.

        Args:
            name: Session name (without .json extension)

        Returns:
            Session data dictionary or None if not found
        """
        session_file = self.storage_dir / f"{name}.json"
        if session_file.exists():
            return json.loads(session_file.read_text())
        return None

    def delete_session(self, name: str) -> bool:
        """Delete a saved session by name.

        Args:
            name: Session name (without .json extension)

        Returns:
            True if deleted, False if not found
        """
        session_file = self.storage_dir / f"{name}.json"
        if session_file.exists():
            session_file.unlink()
            return True
        return False

    @staticmethod
    def export_csv(data: List[Dict[str, Any]]) -> str:
        """Export data as CSV string.

        Args:
            data: List of reading dictionaries

        Returns:
            CSV string
        """
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        return output.getvalue()
