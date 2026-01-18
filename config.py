import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Flask-SocketIO Configuration
    # MUST use 'threading' for Bluetooth asyncio compatibility (NOT eventlet)
    SOCKETIO_ASYNC_MODE = 'threading'

    # Device Configuration - FNIRSI USB Testers
    # Supported devices with their vendor/product IDs:
    SUPPORTED_DEVICES = [
        (0x2e3c, 0x0049, 'FNB48P/S'),   # FNB48P, FNB48S - Premium testers
        (0x2e3c, 0x5558, 'FNB58'),       # FNB58 - Advanced tester with Bluetooth
        (0x0483, 0x003a, 'FNB48'),       # FNB48 - Original tester
        (0x0483, 0x003b, 'C1'),          # C1 - Compact Type-C trigger
    ]

    # Bluetooth Configuration
    BT_WRITE_UUID = "0000ffe9-0000-1000-8000-00805f9b34fb"
    BT_NOTIFY_UUID = "0000ffe4-0000-1000-8000-00805f9b34fb"
    BT_DEVICE_PATTERNS = ["FNB58", "FNB48", "C1", "FNIRSI"]  # Device name patterns
    
    # Data Collection
    SAMPLE_RATE_HZ = 100  # Hz (USB mode)
    BT_SAMPLE_RATE_HZ = 10  # Hz (Bluetooth is slower)
    MAX_DATA_POINTS = 10000  # Maximum points to keep in memory
    
    # Export Settings
    EXPORT_DIR = os.path.join(os.path.dirname(__file__), 'exports')
    
    # Alert Settings
    ALERT_CHECK_INTERVAL = 1.0  # seconds
    
    # Session Settings
    SESSION_DIR = os.path.join(os.path.dirname(__file__), 'sessions')
    
    @staticmethod
    def init_app(app):
        """Initialize application directories"""
        os.makedirs(Config.EXPORT_DIR, exist_ok=True)
        os.makedirs(Config.SESSION_DIR, exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
