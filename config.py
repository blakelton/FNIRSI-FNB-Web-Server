import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Flask-SocketIO Configuration
    SOCKETIO_ASYNC_MODE = 'threading'  # or 'eventlet' or 'gevent'
    
    # Device Configuration
    DEVICE_VENDOR_ID = 0x0716  # FNIRSI vendor ID
    DEVICE_PRODUCT_IDS = [0x5030, 0x5031]  # FNB48, C1, FNB58
    
    # Bluetooth Configuration
    BT_WRITE_UUID = "0000ffe9-0000-1000-8000-00805f9b34fb"
    BT_NOTIFY_UUID = "0000ffe4-0000-1000-8000-00805f9b34fb"
    BT_DEVICE_NAME = "FNB58"  # Partial name to search for
    
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
