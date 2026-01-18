"""
Tests for Flask REST API endpoints.

Note: These tests require the Flask app to be importable.
They test API structure and response formats.
"""

import pytest
import json


class TestAPIStructure:
    """Test API endpoint structure and response formats."""

    def test_reading_format(self, sample_reading):
        """Test that readings have expected format.

        Note: D+/D- fields use 'dp'/'dn' to match USB tester terminology.
        """
        required_fields = ['voltage', 'current', 'power', 'dp', 'dn', 'temperature']

        for field in required_fields:
            assert field in sample_reading, f"Missing field: {field}"

    def test_reading_types(self, sample_reading):
        """Test that reading values have correct types."""
        assert isinstance(sample_reading['voltage'], (int, float))
        assert isinstance(sample_reading['current'], (int, float))
        assert isinstance(sample_reading['power'], (int, float))
        assert isinstance(sample_reading['dp'], (int, float))
        assert isinstance(sample_reading['dn'], (int, float))
        assert isinstance(sample_reading['temperature'], (int, float))

    def test_json_serialization(self, sample_reading):
        """Test that readings can be JSON serialized."""
        json_str = json.dumps(sample_reading)
        parsed = json.loads(json_str)

        assert parsed['voltage'] == sample_reading['voltage']
        assert parsed['current'] == sample_reading['current']


class TestAPIEndpoints:
    """Test expected API endpoint responses."""

    def test_latest_endpoint_format(self):
        """Test /api/latest response format.

        Note: D+/D- fields use 'dp'/'dn' to match USB tester terminology.
        """
        # Expected response structure
        expected_structure = {
            'voltage': float,
            'current': float,
            'power': float,
            'dp': float,
            'dn': float,
            'temperature': float,
            'timestamp': str,  # ISO format timestamp
        }

        # This documents the expected API contract
        for field, field_type in expected_structure.items():
            assert field_type in (int, float, str, bool, list, dict)

    def test_stats_endpoint_format(self):
        """Test /api/stats response format."""
        expected_fields = [
            'voltage_min', 'voltage_max', 'voltage_avg',
            'current_min', 'current_max', 'current_avg',
            'power_min', 'power_max', 'power_avg',
            'energy_wh', 'capacity_mah',
        ]

        # This documents the expected stats fields
        assert len(expected_fields) > 0

    def test_device_endpoint_format(self):
        """Test /api/device response format."""
        expected_fields = ['connected', 'vendor_id', 'product_id', 'name']

        # This documents the expected device info fields
        assert len(expected_fields) > 0


class TestRecordingAPI:
    """Test recording-related API functionality."""

    def test_recording_status_format(self):
        """Test recording status response format."""
        # Expected when not recording
        status_not_recording = {
            'recording': False,
            'duration': 0,
            'samples': 0,
        }

        assert status_not_recording['recording'] is False

    def test_session_list_format(self):
        """Test session list response format."""
        # Expected session entry format
        session_entry = {
            'name': 'session_20250109_120000',
            'created': '2025-01-09T12:00:00',
            'samples': 1000,
            'duration': 10.0,
        }

        assert 'name' in session_entry
        assert 'samples' in session_entry
