"""
Device Manager - Unified interface for USB and Bluetooth connections
"""

from .usb_reader import USBReader
from .bluetooth_reader import BluetoothReader
from .protocol_detector import ProtocolDetector
from .alert_manager import AlertManager
from collections import deque
from datetime import datetime
import threading


class DeviceManager:
    """Manages device connection and data collection"""

    def __init__(self):
        self.connection_type = None  # 'usb' or 'bluetooth'
        self.reader = None
        self.is_connected = False
        self.is_recording = False
        self.data_callbacks = []
        self.data_buffer = deque(maxlen=10000)
        self.session_data = []
        self.session_start_time = None
        self.lock = threading.Lock()

        # Protocol detection and alerts
        self.protocol_detector = ProtocolDetector()
        self.alert_manager = AlertManager()
        self.current_protocol = None

        # Statistics
        self.stats = {
            'samples_collected': 0,
            'max_voltage': 0.0,
            'min_voltage': float('inf'),
            'max_current': 0.0,
            'min_current': float('inf'),
            'max_power': 0.0,
            'total_energy_wh': 0.0,
            'total_capacity_ah': 0.0,
            'avg_voltage': 0.0,
            'avg_current': 0.0,
            'avg_power': 0.0
        }
        
    def connect(self, mode='auto', **kwargs):
        """
        Connect to device
        mode: 'auto', 'usb', 'bluetooth'
        kwargs: device_address for Bluetooth, etc.
        """
        if self.is_connected:
            raise ConnectionError("Already connected to a device")
        
        success = False
        error = None
        
        # Try Bluetooth first if auto or bluetooth mode
        if mode in ['auto', 'bluetooth']:
            try:
                print("Attempting Bluetooth connection...")
                self.reader = BluetoothReader(
                    device_address=kwargs.get('device_address'),
                    device_name=kwargs.get('device_name', 'FNB58')
                )
                self.reader.connect()
                self.connection_type = 'bluetooth'
                success = True
                print("✓ Connected via Bluetooth")
            except Exception as e:
                error = str(e)
                print(f"✗ Bluetooth connection failed: {e}")
                if mode == 'bluetooth':
                    raise
        
        # Try USB if auto or usb mode (and Bluetooth failed)
        if not success and mode in ['auto', 'usb']:
            try:
                print("Attempting USB connection...")
                self.reader = USBReader()
                self.reader.connect()
                self.connection_type = 'usb'
                success = True
                print("✓ Connected via USB")
            except Exception as e:
                error = str(e)
                print(f"✗ USB connection failed: {e}")
                if mode == 'usb':
                    raise
        
        if not success:
            raise ConnectionError(f"Failed to connect via any method. Last error: {error}")
        
        self.is_connected = True
        return {
            'success': True,
            'connection_type': self.connection_type,
            'device_info': self.reader.get_device_info()
        }
    
    def start_monitoring(self):
        """Start collecting data from device"""
        if not self.is_connected:
            raise ConnectionError("Device not connected")
        
        self.reader.start_reading(callback=self._on_data_received)
        return True
    
    def stop_monitoring(self):
        """Stop collecting data"""
        if self.reader:
            self.reader.stop_reading()
    
    def start_recording(self):
        """Start recording session"""
        with self.lock:
            self.is_recording = True
            self.session_data = []
            self.session_start_time = datetime.now()
            self._reset_stats()
        return True
    
    def stop_recording(self):
        """Stop recording session"""
        with self.lock:
            self.is_recording = False
            session = {
                'start_time': self.session_start_time.isoformat() if self.session_start_time else None,
                'end_time': datetime.now().isoformat(),
                'data': self.session_data.copy(),
                'stats': self.stats.copy(),
                'connection_type': self.connection_type
            }
            return session
    
    def _on_data_received(self, reading):
        """Callback when new data is received from device"""
        with self.lock:
            # Detect protocol
            protocol_info = self.protocol_detector.detect_protocol(reading)
            self.current_protocol = protocol_info

            # Check for alerts
            alerts = self.alert_manager.check_reading(reading)

            # Enhance reading with protocol and alert info
            enhanced_reading = {
                **reading,
                'protocol': protocol_info,
                'has_alerts': len(alerts) > 0
            }

            # Add to buffer
            self.data_buffer.append(enhanced_reading)

            # Add to session if recording
            if self.is_recording:
                self.session_data.append(enhanced_reading)
                self._update_stats(reading)

            # Call registered callbacks
            for callback in self.data_callbacks:
                try:
                    callback(enhanced_reading)
                except Exception as e:
                    print(f"Error in data callback: {e}")
    
    def _update_stats(self, reading):
        """Update running statistics"""
        v = reading['voltage']
        c = reading['current']
        p = reading['power']
        
        self.stats['samples_collected'] += 1
        
        # Min/Max
        self.stats['max_voltage'] = max(self.stats['max_voltage'], v)
        self.stats['min_voltage'] = min(self.stats['min_voltage'], v)
        self.stats['max_current'] = max(self.stats['max_current'], c)
        self.stats['min_current'] = min(self.stats['min_current'], c)
        self.stats['max_power'] = max(self.stats['max_power'], p)
        
        # Running averages (simplified - could use proper windowed average)
        n = self.stats['samples_collected']
        self.stats['avg_voltage'] = ((self.stats['avg_voltage'] * (n - 1)) + v) / n
        self.stats['avg_current'] = ((self.stats['avg_current'] * (n - 1)) + c) / n
        self.stats['avg_power'] = ((self.stats['avg_power'] * (n - 1)) + p) / n
        
        # Energy and capacity (basic integration)
        # Assumes roughly 100Hz for USB, 10Hz for Bluetooth
        dt = 0.01 if self.connection_type == 'usb' else 0.1  # seconds
        self.stats['total_energy_wh'] += (p * dt) / 3600  # Wh
        self.stats['total_capacity_ah'] += (c * dt) / 3600  # Ah
    
    def _reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'samples_collected': 0,
            'max_voltage': 0.0,
            'min_voltage': float('inf'),
            'max_current': 0.0,
            'min_current': float('inf'),
            'max_power': 0.0,
            'total_energy_wh': 0.0,
            'total_capacity_ah': 0.0,
            'avg_voltage': 0.0,
            'avg_current': 0.0,
            'avg_power': 0.0
        }
    
    def register_callback(self, callback):
        """Register a callback for new data"""
        self.data_callbacks.append(callback)
    
    def unregister_callback(self, callback):
        """Unregister a callback"""
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
    
    def get_latest_reading(self):
        """Get the most recent reading"""
        with self.lock:
            if len(self.data_buffer) > 0:
                return self.data_buffer[-1]
            return None
    
    def get_recent_data(self, num_points=100):
        """Get recent data points"""
        with self.lock:
            data = list(self.data_buffer)
            return data[-num_points:] if len(data) > num_points else data
    
    def get_stats(self):
        """Get current statistics"""
        with self.lock:
            return self.stats.copy()
    
    def disconnect(self):
        """Disconnect from device"""
        self.stop_monitoring()

        if self.reader:
            self.reader.disconnect()

        self.is_connected = False
        self.connection_type = None
        self.reader = None

    def trigger_voltage(self, protocol, voltage):
        """
        Trigger fast charging protocol voltage

        Args:
            protocol: Protocol type ('pd', 'qc', 'afc', 'fcp', 'scp', 'vooc')
            voltage: Target voltage (5, 9, 12, 15, 20)

        Returns:
            bool: True if command sent successfully
        """
        if not self.is_connected:
            raise ConnectionError("Device not connected")

        if self.connection_type != 'usb':
            raise ValueError("Voltage triggering only supported via USB connection")

        return self.reader.trigger_voltage(protocol, voltage)

    def adjust_qc3_voltage(self, target_voltage):
        """
        Adjust QC 3.0 voltage in fine steps (3.6V - 12.0V)

        Args:
            target_voltage: Target voltage (float, 3.6 - 12.0)

        Returns:
            bool: True if command sent successfully
        """
        if not self.is_connected:
            raise ConnectionError("Device not connected")

        if self.connection_type != 'usb':
            raise ValueError("QC 3.0 adjustment only supported via USB connection")

        return self.reader.adjust_qc3_voltage(target_voltage)
    
    def get_connection_info(self):
        """Get connection information"""
        if not self.is_connected:
            return {'connected': False}
        
        return {
            'connected': True,
            'connection_type': self.connection_type,
            'device_info': self.reader.get_device_info() if self.reader else None,
            'is_recording': self.is_recording
        }
