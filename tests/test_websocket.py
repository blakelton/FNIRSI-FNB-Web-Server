"""Tests for app.py WebSocket events"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_device_manager():
    """Create a mocked device manager for WebSocket tests."""
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
    return mock_dm


@pytest.fixture
def socketio_client(mock_device_manager):
    """Flask-SocketIO test client with mocked device_manager."""
    with patch('app.device_manager', mock_device_manager):
        with patch('app.data_processor', MagicMock()):
            from app import app, socketio
            app.config['TESTING'] = True
            client = socketio.test_client(app)
            yield client, mock_device_manager
            if client.is_connected():
                client.disconnect()


class TestWebSocketConnect:
    def test_client_connect_receives_response(self, socketio_client):
        client, mock_dm = socketio_client
        assert client.is_connected()
        received = client.get_received()
        # Should receive 'connection_response' event on connect
        event_names = [msg['name'] for msg in received]
        assert 'connection_response' in event_names

    def test_client_disconnect(self, socketio_client):
        client, mock_dm = socketio_client
        assert client.is_connected()
        client.disconnect()
        assert not client.is_connected()
        # Reconnect so fixture teardown doesn't error
        client.connect()


class TestWebSocketEvents:
    def test_request_data_returns_historical(self, socketio_client):
        client, mock_dm = socketio_client
        mock_dm.get_recent_data.return_value = [
            {'voltage': 5.0, 'current': 1.0, 'power': 5.0}
        ] * 10
        # Clear initial events
        client.get_received()

        client.emit('request_data', {'points': 10})
        received = client.get_received()
        event_names = [msg['name'] for msg in received]
        assert 'historical_data' in event_names

    def test_ping_returns_pong(self, socketio_client):
        client, mock_dm = socketio_client
        # Clear initial events
        client.get_received()

        client.emit('ping')
        received = client.get_received()
        event_names = [msg['name'] for msg in received]
        assert 'pong' in event_names
