"""Tests for app.py REST API endpoints"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock, mock_open


@pytest.fixture
def mock_device_manager():
    """Create a mocked device manager for API tests."""
    mock_dm = MagicMock()
    mock_dm.is_connected = False
    mock_dm.is_recording = False
    mock_dm.data_buffer = []
    mock_dm.data_callbacks = []
    mock_dm.current_protocol = None
    mock_dm.connection_type = None
    mock_dm.get_connection_info.return_value = {'connected': False}
    mock_dm.get_latest_reading.return_value = None
    mock_dm.get_recent_data.return_value = []
    mock_dm.get_stats.return_value = {'samples_collected': 0}
    mock_dm.alert_manager = MagicMock()
    mock_dm.alert_manager.get_active_alerts.return_value = []
    mock_dm.alert_manager.get_alert_history.return_value = []
    mock_dm.alert_manager.get_thresholds.return_value = {}
    mock_dm.alert_manager.set_threshold.return_value = True
    mock_dm.alert_manager.acknowledge_alert.return_value = True
    mock_dm.session_name = None
    return mock_dm


@pytest.fixture
def client(mock_device_manager):
    """Flask test client with mocked device_manager."""
    with patch('app.device_manager', mock_device_manager):
        with patch('app.data_processor', MagicMock()):
            from app import app
            app.config['TESTING'] = True
            with app.test_client() as client:
                yield client, mock_device_manager


class TestAPIStatus:
    def test_get_status_disconnected(self, client):
        c, mock_dm = client
        response = c.get('/api/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['connected'] is False

    def test_get_status_connected(self, client):
        c, mock_dm = client
        mock_dm.get_connection_info.return_value = {
            'connected': True, 'connection_type': 'usb',
            'device_info': {}, 'is_recording': False
        }
        response = c.get('/api/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['connected'] is True


class TestAPIConnect:
    def test_connect_auto_success(self, client):
        c, mock_dm = client
        mock_dm.connect.return_value = {
            'success': True, 'connection_type': 'usb', 'device_info': {}
        }
        response = c.post('/api/connect',
                          data=json.dumps({'mode': 'auto'}),
                          content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_connect_bluetooth_with_address(self, client):
        c, mock_dm = client
        mock_dm.connect.return_value = {
            'success': True, 'connection_type': 'bluetooth', 'device_info': {}
        }
        response = c.post('/api/connect',
                          data=json.dumps({'mode': 'bluetooth', 'device_address': 'AA:BB:CC:DD:EE:FF'}),
                          content_type='application/json')
        assert response.status_code == 200
        mock_dm.connect.assert_called_once_with(mode='bluetooth', device_address='AA:BB:CC:DD:EE:FF')

    def test_connect_failure(self, client):
        c, mock_dm = client
        mock_dm.connect.side_effect = ConnectionError("No device found")
        response = c.post('/api/connect',
                          data=json.dumps({'mode': 'auto'}),
                          content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_disconnect_success(self, client):
        c, mock_dm = client
        response = c.post('/api/disconnect')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        mock_dm.disconnect.assert_called_once()


class TestAPIReading:
    def test_latest_reading_exists(self, client):
        c, mock_dm = client
        mock_dm.get_latest_reading.return_value = {
            'voltage': 5.0, 'current': 1.0, 'power': 5.0
        }
        response = c.get('/api/reading/latest')
        assert response.status_code == 200
        data = response.get_json()
        assert data['voltage'] == 5.0

    def test_latest_reading_none(self, client):
        c, mock_dm = client
        mock_dm.get_latest_reading.return_value = None
        response = c.get('/api/reading/latest')
        assert response.status_code == 404

    def test_recent_data(self, client):
        c, mock_dm = client
        mock_dm.get_recent_data.return_value = [{'voltage': 5.0}] * 50
        response = c.get('/api/reading/recent?points=50')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 50

    def test_recent_data_default_points(self, client):
        c, mock_dm = client
        mock_dm.get_recent_data.return_value = []
        response = c.get('/api/reading/recent')
        assert response.status_code == 200
        mock_dm.get_recent_data.assert_called_with(100)


class TestAPIStats:
    def test_get_stats(self, client):
        c, mock_dm = client
        mock_dm.get_stats.return_value = {'samples_collected': 100, 'avg_voltage': 5.0}
        response = c.get('/api/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert data['samples_collected'] == 100


class TestAPIRecording:
    def test_start_recording(self, client):
        c, mock_dm = client
        response = c.post('/api/recording/start',
                          data=json.dumps({}),
                          content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        mock_dm.start_recording.assert_called_once()

    def test_start_recording_with_name(self, client):
        c, mock_dm = client
        response = c.post('/api/recording/start',
                          data=json.dumps({'name': 'My Session'}),
                          content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == 'My Session'

    @patch('builtins.open', mock_open())
    @patch('json.dump')
    def test_stop_recording(self, mock_json_dump, client):
        c, mock_dm = client
        mock_dm.stop_recording.return_value = {
            'start_time': '2025-01-01T00:00:00',
            'end_time': '2025-01-01T01:00:00',
            'data': [], 'stats': {}, 'connection_type': 'usb'
        }
        response = c.post('/api/recording/stop')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'filename' in data


class TestAPIProtocol:
    def test_get_protocol(self, client):
        c, mock_dm = client
        mock_dm.current_protocol = {'protocol': 'USB-PD', 'mode': '9V'}
        response = c.get('/api/protocol')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_get_protocol_none(self, client):
        c, mock_dm = client
        mock_dm.current_protocol = None
        response = c.get('/api/protocol')
        assert response.status_code == 200
        data = response.get_json()
        assert data['protocol'] is None


class TestAPITrigger:
    def test_trigger_voltage(self, client):
        c, mock_dm = client
        response = c.post('/api/trigger/voltage',
                          data=json.dumps({'protocol': 'pd', 'voltage': 9}),
                          content_type='application/json')
        assert response.status_code == 200
        mock_dm.trigger_voltage.assert_called_once()

    def test_trigger_voltage_missing_params(self, client):
        c, mock_dm = client
        response = c.post('/api/trigger/voltage',
                          data=json.dumps({}),
                          content_type='application/json')
        assert response.status_code == 400

    def test_qc3_adjust(self, client):
        c, mock_dm = client
        response = c.post('/api/trigger/qc3-adjust',
                          data=json.dumps({'voltage': 9.0}),
                          content_type='application/json')
        assert response.status_code == 200
        mock_dm.adjust_qc3_voltage.assert_called_once()

    def test_qc3_adjust_missing_voltage(self, client):
        c, mock_dm = client
        response = c.post('/api/trigger/qc3-adjust',
                          data=json.dumps({}),
                          content_type='application/json')
        assert response.status_code == 400


class TestAPIAlerts:
    def test_get_alerts(self, client):
        c, mock_dm = client
        response = c.get('/api/alerts')
        assert response.status_code == 200
        data = response.get_json()
        assert 'alerts' in data

    def test_get_alert_history(self, client):
        c, mock_dm = client
        response = c.get('/api/alerts/history?limit=10')
        assert response.status_code == 200
        data = response.get_json()
        assert 'history' in data

    def test_acknowledge_alert(self, client):
        c, mock_dm = client
        response = c.post('/api/alerts/acknowledge/test_id')
        assert response.status_code == 200
        mock_dm.alert_manager.acknowledge_alert.assert_called_with('test_id')

    def test_clear_alerts(self, client):
        c, mock_dm = client
        response = c.post('/api/alerts/clear')
        assert response.status_code == 200
        mock_dm.alert_manager.clear_acknowledged_alerts.assert_called_once()


class TestAPIThresholds:
    def test_get_thresholds(self, client):
        c, mock_dm = client
        response = c.get('/api/thresholds')
        assert response.status_code == 200
        data = response.get_json()
        assert 'thresholds' in data

    def test_set_threshold(self, client):
        c, mock_dm = client
        response = c.post('/api/thresholds',
                          data=json.dumps({'name': 'max_voltage', 'value': 25.0}),
                          content_type='application/json')
        assert response.status_code == 200
        mock_dm.alert_manager.set_threshold.assert_called_once_with('max_voltage', 25.0)

    def test_set_threshold_missing_params(self, client):
        c, mock_dm = client
        response = c.post('/api/thresholds',
                          data=json.dumps({}),
                          content_type='application/json')
        assert response.status_code == 400


class TestAPISessions:
    @patch('app.Path')
    def test_list_sessions(self, MockPath, client):
        c, mock_dm = client
        mock_file = MagicMock()
        mock_file.name = 'session_test.json'
        MockPath.return_value.glob.return_value = [mock_file]

        with patch('builtins.open', mock_open(read_data=json.dumps({
            'start_time': '2025-01-01', 'end_time': '2025-01-02',
            'connection_type': 'usb', 'data': [1, 2, 3], 'name': 'Test'
        }))):
            response = c.get('/api/sessions')
            assert response.status_code == 200

    @patch('os.path.exists', return_value=True)
    def test_get_session(self, mock_exists, client):
        c, mock_dm = client
        session_data = {'data': [], 'stats': {}}
        with patch('builtins.open', mock_open(read_data=json.dumps(session_data))):
            response = c.get('/api/sessions/test.json')
            assert response.status_code == 200

    @patch('os.path.exists', return_value=False)
    def test_get_session_not_found(self, mock_exists, client):
        c, mock_dm = client
        response = c.get('/api/sessions/missing.json')
        assert response.status_code == 404

    @patch('os.remove')
    @patch('os.path.exists', return_value=True)
    def test_delete_session(self, mock_exists, mock_remove, client):
        c, mock_dm = client
        response = c.delete('/api/sessions/test.json')
        assert response.status_code == 200
        mock_remove.assert_called_once()

    def test_delete_session_path_traversal(self, client):
        c, mock_dm = client
        # Use a filename with '..' that Flask won't normalize away
        response = c.delete('/api/sessions/..etc_passwd')
        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid filename' in data['error']

    @patch('os.path.exists', return_value=False)
    def test_delete_session_not_found(self, mock_exists, client):
        c, mock_dm = client
        response = c.delete('/api/sessions/missing.json')
        assert response.status_code == 404


class TestAPISystemStats:
    @patch('psutil.cpu_percent', return_value=25.0)
    @patch('psutil.virtual_memory')
    def test_system_stats_with_psutil(self, mock_mem, mock_cpu, client):
        c, mock_dm = client
        mock_mem.return_value = MagicMock(
            used=8 * 1024**3, total=16 * 1024**3, percent=50.0
        )
        response = c.get('/api/system-stats')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'cpu_percent' in data


class TestErrorHandlers:
    def test_404(self, client):
        c, mock_dm = client
        response = c.get('/api/nonexistent')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
