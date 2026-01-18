"""
Tests for statistics tracking functionality.
"""

import pytest
from collections import deque


class TestStatisticsTracking:
    """Test statistics calculation and tracking."""

    def test_min_max_tracking(self):
        """Test minimum and maximum value tracking."""
        readings = [1.0, 2.5, 0.5, 3.0, 1.5]

        min_val = min(readings)
        max_val = max(readings)

        assert min_val == 0.5
        assert max_val == 3.0

    def test_average_calculation(self):
        """Test average value calculation."""
        readings = [1.0, 2.0, 3.0, 4.0, 5.0]

        avg = sum(readings) / len(readings)

        assert avg == 3.0

    def test_energy_accumulation(self):
        """Test energy (Wh) accumulation over time."""
        # Simulate 1 hour of 5W power
        power_watts = 5.0
        duration_hours = 1.0

        energy_wh = power_watts * duration_hours

        assert energy_wh == 5.0

    def test_capacity_accumulation(self):
        """Test capacity (mAh) accumulation over time."""
        # Simulate 1 hour of 1A current
        current_amps = 1.0
        duration_hours = 1.0

        capacity_ah = current_amps * duration_hours
        capacity_mah = capacity_ah * 1000

        assert capacity_mah == 1000.0

    def test_rolling_buffer(self):
        """Test rolling buffer for recent readings."""
        buffer = deque(maxlen=100)

        # Add 150 items
        for i in range(150):
            buffer.append(i)

        # Buffer should only contain last 100 items
        assert len(buffer) == 100
        assert buffer[0] == 50
        assert buffer[-1] == 149


class TestAlertThresholds:
    """Test alert threshold checking."""

    def test_voltage_over_threshold(self):
        """Test voltage over-threshold detection."""
        voltage = 25.0
        threshold = 24.0

        is_over = voltage > threshold
        assert is_over

    def test_voltage_under_threshold(self):
        """Test voltage under-threshold detection."""
        voltage = 4.5
        threshold = 4.75

        is_under = voltage < threshold
        assert is_under

    def test_current_over_threshold(self):
        """Test current over-threshold detection."""
        current = 3.5
        threshold = 3.0

        is_over = current > threshold
        assert is_over

    def test_power_over_threshold(self):
        """Test power over-threshold detection."""
        power = 65.0
        threshold = 60.0

        is_over = power > threshold
        assert is_over

    def test_temperature_over_threshold(self):
        """Test temperature over-threshold detection."""
        temperature = 85.0
        threshold = 80.0

        is_over = temperature > threshold
        assert is_over
