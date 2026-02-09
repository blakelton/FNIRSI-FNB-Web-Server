"""Tests for device/data_processor.py"""

import pytest
import json
import csv
import os
from device.data_processor import DataProcessor


class TestCalculateStatistics:
    def test_basic_statistics(self, sample_readings_list):
        stats = DataProcessor.calculate_statistics(sample_readings_list)
        assert stats['sample_count'] == 100
        assert 'voltage' in stats
        assert 'current' in stats
        assert 'power' in stats
        assert stats['voltage']['min'] <= stats['voltage']['avg'] <= stats['voltage']['max']

    def test_empty_data(self):
        stats = DataProcessor.calculate_statistics([])
        assert stats == {}

    def test_single_reading(self, sample_reading):
        stats = DataProcessor.calculate_statistics([sample_reading])
        assert stats['sample_count'] == 1
        assert stats['voltage']['min'] == stats['voltage']['max'] == stats['voltage']['avg']

    def test_energy_and_capacity_present(self, sample_readings_list):
        stats = DataProcessor.calculate_statistics(sample_readings_list)
        assert 'energy_wh' in stats
        assert 'capacity_ah' in stats
        assert 'capacity_mah' in stats
        assert stats['energy_wh'] > 0
        assert stats['capacity_mah'] == stats['capacity_ah'] * 1000

    def test_range_calculation(self, sample_readings_list):
        stats = DataProcessor.calculate_statistics(sample_readings_list)
        expected_range = stats['voltage']['max'] - stats['voltage']['min']
        assert abs(stats['voltage']['range'] - expected_range) < 1e-10


class TestCalculateAdvancedStatistics:
    def test_advanced_stats_keys(self, sample_readings_list):
        stats = DataProcessor.calculate_advanced_statistics(sample_readings_list)
        assert 'sample_count' in stats
        assert 'duration_seconds' in stats
        assert 'voltage' in stats
        assert 'rms' in stats['voltage']
        assert 'std' in stats['voltage']
        assert 'ripple_pk_pk' in stats['voltage']
        assert 'ripple_percent' in stats['voltage']

    def test_empty_data(self):
        stats = DataProcessor.calculate_advanced_statistics([])
        assert stats == {}

    def test_rms_calculation(self):
        # Known data: [3, 4] -> rms = sqrt((9+16)/2) = sqrt(12.5)
        data = [
            {'voltage': 3.0, 'current': 0.0, 'power': 0.0},
            {'voltage': 4.0, 'current': 0.0, 'power': 0.0},
        ]
        stats = DataProcessor.calculate_advanced_statistics(data)
        import math
        expected_rms = math.sqrt((9 + 16) / 2)
        assert abs(stats['voltage']['rms'] - expected_rms) < 0.001

    def test_power_factor_calculated(self, sample_readings_list):
        stats = DataProcessor.calculate_advanced_statistics(sample_readings_list)
        assert 'power_factor' in stats
        assert 0 <= stats['power_factor'] <= 1.1  # allow slight rounding

    def test_energy_trapezoidal(self, sample_readings_list):
        stats = DataProcessor.calculate_advanced_statistics(sample_readings_list)
        assert stats['energy_wh'] > 0
        assert stats['capacity_ah'] > 0


class TestDetectChargingPhases:
    def test_detect_three_phases(self, charging_phase_readings):
        phases = DataProcessor.detect_charging_phases(charging_phase_readings)
        assert len(phases) == 3
        assert phases[0]['phase'] == 'idle'
        assert phases[1]['phase'] == 'charging'
        assert phases[2]['phase'] == 'idle'

    def test_phase_durations(self, charging_phase_readings):
        phases = DataProcessor.detect_charging_phases(charging_phase_readings)
        assert phases[0]['duration_samples'] == 10
        assert phases[1]['duration_samples'] == 20
        assert phases[2]['duration_samples'] == 10

    def test_single_phase_charging(self):
        data = [{'voltage': 5.0, 'current': 1.5, 'power': 7.5} for _ in range(20)]
        phases = DataProcessor.detect_charging_phases(data)
        assert len(phases) == 1
        assert phases[0]['phase'] == 'charging'

    def test_single_phase_idle(self):
        data = [{'voltage': 5.0, 'current': 0.01, 'power': 0.05} for _ in range(20)]
        phases = DataProcessor.detect_charging_phases(data)
        assert len(phases) == 1
        assert phases[0]['phase'] == 'idle'

    def test_empty_data(self):
        phases = DataProcessor.detect_charging_phases([])
        assert phases == []

    def test_custom_threshold(self, charging_phase_readings):
        phases = DataProcessor.detect_charging_phases(charging_phase_readings, current_threshold=0.5)
        assert len(phases) == 3

    def test_phase_structure(self, charging_phase_readings):
        phases = DataProcessor.detect_charging_phases(charging_phase_readings)
        for phase in phases:
            assert 'phase' in phase
            assert 'start_index' in phase
            assert 'end_index' in phase
            assert 'duration_samples' in phase


class TestGenerateChartData:
    def test_basic_chart_data(self, sample_readings_list):
        chart = DataProcessor.generate_chart_data(sample_readings_list)
        assert 'timestamps' in chart
        assert 'voltage' in chart
        assert 'current' in chart
        assert 'power' in chart
        assert len(chart['timestamps']) == len(chart['voltage'])

    def test_downsampling(self):
        # Create 2000 readings
        data = [{'voltage': 5.0, 'current': 1.0, 'power': 5.0} for _ in range(2000)]
        chart = DataProcessor.generate_chart_data(data, max_points=500)
        assert len(chart['voltage']) <= 500

    def test_empty_data(self):
        chart = DataProcessor.generate_chart_data([])
        assert chart['timestamps'] == []
        assert chart['voltage'] == []

    def test_no_downsampling_when_under_limit(self, sample_readings_list):
        chart = DataProcessor.generate_chart_data(sample_readings_list, max_points=1000)
        assert len(chart['voltage']) == len(sample_readings_list)


class TestExportToCSV:
    def test_export_csv(self, sample_readings_list, tmp_path):
        filename = str(tmp_path / 'test.csv')
        result = DataProcessor.export_to_csv(sample_readings_list, filename)
        assert result == filename
        assert os.path.exists(filename)

        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 100

    def test_export_empty_data_raises(self, tmp_path):
        filename = str(tmp_path / 'empty.csv')
        with pytest.raises(ValueError):
            DataProcessor.export_to_csv([], filename)

    def test_csv_contains_all_columns(self, sample_readings_list, tmp_path):
        filename = str(tmp_path / 'test.csv')
        DataProcessor.export_to_csv(sample_readings_list, filename)
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            assert 'voltage' in headers
            assert 'current' in headers
            assert 'power' in headers


class TestExportToJSON:
    def test_export_json(self, sample_session, tmp_path):
        filename = str(tmp_path / 'test.json')
        result = DataProcessor.export_to_json(sample_session, filename)
        assert result == filename
        assert os.path.exists(filename)

        with open(filename, 'r') as f:
            loaded = json.load(f)
            assert loaded['connection_type'] == 'usb'
            assert len(loaded['data']) == 100

    def test_json_is_valid(self, sample_session, tmp_path):
        filename = str(tmp_path / 'test.json')
        DataProcessor.export_to_json(sample_session, filename)
        with open(filename, 'r') as f:
            # Should not raise
            data = json.load(f)
            assert isinstance(data, dict)


class TestGenerateHTMLReport:
    def test_generate_report_creates_file(self, sample_session, tmp_path):
        filename = str(tmp_path / 'report.html')
        result = DataProcessor.generate_html_report(sample_session, filename)
        assert result == filename
        assert os.path.exists(filename)

    def test_report_contains_stats(self, sample_session, tmp_path):
        filename = str(tmp_path / 'report.html')
        DataProcessor.generate_html_report(sample_session, filename)
        with open(filename, 'r') as f:
            html = f.read()
            assert 'VOLTAGE' in html
            assert 'CURRENT' in html
            assert 'POWER' in html

    def test_report_contains_chart_data(self, sample_session, tmp_path):
        filename = str(tmp_path / 'report.html')
        DataProcessor.generate_html_report(sample_session, filename)
        with open(filename, 'r') as f:
            html = f.read()
            assert 'chartData' in html

    def test_report_empty_data_raises(self, tmp_path):
        filename = str(tmp_path / 'report.html')
        empty_session = {'data': []}
        with pytest.raises(ValueError, match="No data"):
            DataProcessor.generate_html_report(empty_session, filename)


class TestGenerateReport:
    def test_text_report(self, sample_session):
        report = DataProcessor.generate_report(sample_session)
        assert isinstance(report, str)
        assert 'Session Report' in report
        assert 'Voltage' in report
        assert 'Current' in report

    def test_report_contains_session_info(self, sample_session):
        report = DataProcessor.generate_report(sample_session)
        assert 'Start Time' in report
        assert 'End Time' in report
        assert 'USB' in report  # connection_type
