"""Tests for config.py"""

from unittest.mock import patch, MagicMock
from config import Config, DevelopmentConfig, ProductionConfig, config


class TestConfigBase:
    def test_supported_devices_list(self):
        assert len(Config.SUPPORTED_DEVICES) == 4
        for entry in Config.SUPPORTED_DEVICES:
            assert len(entry) == 3
            assert isinstance(entry[0], int)  # vendor_id
            assert isinstance(entry[1], int)  # product_id
            assert isinstance(entry[2], str)  # name

    def test_sample_rates(self):
        assert Config.SAMPLE_RATE_HZ == 100
        assert Config.BT_SAMPLE_RATE_HZ == 10

    def test_max_data_points(self):
        assert Config.MAX_DATA_POINTS == 10000

    def test_socketio_async_mode(self):
        assert Config.SOCKETIO_ASYNC_MODE == 'threading'

    def test_bt_uuids_are_strings(self):
        assert isinstance(Config.BT_WRITE_UUID, str)
        assert isinstance(Config.BT_NOTIFY_UUID, str)

    def test_alert_check_interval(self):
        assert Config.ALERT_CHECK_INTERVAL == 1.0


class TestDevelopmentConfig:
    def test_debug_true(self):
        assert DevelopmentConfig.DEBUG is True

    def test_testing_false(self):
        assert DevelopmentConfig.TESTING is False


class TestProductionConfig:
    def test_debug_false(self):
        assert ProductionConfig.DEBUG is False

    def test_testing_false(self):
        assert ProductionConfig.TESTING is False


class TestInitApp:
    @patch('os.makedirs')
    def test_creates_directories(self, mock_makedirs):
        mock_app = MagicMock()
        Config.init_app(mock_app)
        assert mock_makedirs.call_count == 2
        # Verify both directories created with exist_ok=True
        for call in mock_makedirs.call_args_list:
            assert call[1].get('exist_ok') is True


class TestConfigDict:
    def test_config_keys(self):
        assert 'development' in config
        assert 'production' in config
        assert 'default' in config

    def test_default_is_development(self):
        assert config['default'] is DevelopmentConfig

    def test_development_class(self):
        assert config['development'] is DevelopmentConfig

    def test_production_class(self):
        assert config['production'] is ProductionConfig
