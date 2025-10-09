"""
Bluetooth LE Reader for FNIRSI FNB58
Based on reverse-engineered protocol from parkerlreed's gist
"""

import asyncio
import struct
import threading
from datetime import datetime
from collections import deque
from bleak import BleakClient, BleakScanner


class BluetoothReader:
    """Bluetooth LE communication with FNIRSI FNB58"""
    
    # Bluetooth UUIDs
    WRITE_UUID = "0000ffe9-0000-1000-8000-00805f9b34fb"
    NOTIFY_UUID = "0000ffe4-0000-1000-8000-00805f9b34fb"
    
    # Initialization commands
    INIT_COMMANDS = [
        bytes([0xaa, 0x81, 0x00, 0xf4]),
        bytes([0xaa, 0x82, 0x00, 0xa7])
    ]
    
    def __init__(self, device_address=None, device_name="FNB58"):
        self.device_address = device_address
        self.device_name = device_name
        self.client = None
        self.is_connected = False
        self.is_reading = False
        self.data_callback = None
        self.data_buffer = deque(maxlen=1000)
        self.loop = None
        self.thread = None
        
    async def scan_devices(self, timeout=10):
        """Scan for FNIRSI devices"""
        print(f"Scanning for Bluetooth devices (timeout: {timeout}s)...")
        devices = await BleakScanner.discover(timeout=timeout)
        
        fnirsi_devices = []
        for device in devices:
            if device.name and self.device_name in device.name:
                fnirsi_devices.append({
                    'address': device.address,
                    'name': device.name,
                    'rssi': device.rssi if hasattr(device, 'rssi') else None
                })
        
        return fnirsi_devices
    
    async def _connect_async(self):
        """Async connection handler"""
        # If no address provided, scan for device
        if not self.device_address:
            devices = await self.scan_devices()
            if not devices:
                raise ConnectionError(f"No {self.device_name} devices found")
            
            # Use the first device found
            self.device_address = devices[0]['address']
            print(f"Found device: {devices[0]['name']} at {self.device_address}")
        
        # Connect to device
        self.client = BleakClient(self.device_address)
        await self.client.connect()
        
        if not self.client.is_connected:
            raise ConnectionError("Failed to connect to device")
        
        print(f"Connected to {self.device_address}")
        
        # Send initialization commands
        for cmd in self.INIT_COMMANDS:
            await self.client.write_gatt_char(self.WRITE_UUID, cmd)
            await asyncio.sleep(0.1)
        
        self.is_connected = True
        return True
    
    def connect(self):
        """Connect to Bluetooth device (synchronous wrapper)"""
        # Create new event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Run connection
        return self.loop.run_until_complete(self._connect_async())
    
    async def _start_reading_async(self):
        """Async reading handler"""
        
        def notification_handler(sender, data):
            """Handle incoming notifications"""
            reading = self._parse_data(data)
            if reading:
                self.data_buffer.append(reading)
                
                if self.data_callback:
                    self.data_callback(reading)
        
        # Start notifications
        await self.client.start_notify(self.NOTIFY_UUID, notification_handler)
        print("Bluetooth notifications enabled")
        
        # Keep reading until stopped
        while self.is_reading and self.client.is_connected:
            await asyncio.sleep(0.1)
        
        # Stop notifications
        try:
            await self.client.stop_notify(self.NOTIFY_UUID)
        except:
            pass
    
    def start_reading(self, callback=None):
        """Start reading data in background thread"""
        if not self.is_connected:
            raise ConnectionError("Device not connected")
        
        self.data_callback = callback
        self.is_reading = True
        
        # Start reading in background thread
        self.thread = threading.Thread(target=self._reading_thread, daemon=True)
        self.thread.start()
    
    def _reading_thread(self):
        """Thread function to run async reading"""
        if not self.loop:
            self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start_reading_async())
    
    def stop_reading(self):
        """Stop reading data"""
        self.is_reading = False
        if self.thread:
            self.thread.join(timeout=2)
    
    def _parse_data(self, data):
        """Parse notification data packet"""
        # Constants from reverse engineering
        offset = 21
        scale = 10000
        
        # Voltage range filter
        min_voltage = 0.0
        max_voltage = 150.0
        
        if len(data) < offset + 12:
            return None
        
        try:
            # Unpack 3 signed 32-bit integers (voltage, current, power)
            voltage, current, power = (value / scale for value in struct.unpack_from('<iii', data, offset))
            
            # Filter out invalid readings
            if not (min_voltage <= voltage <= max_voltage):
                return None
            
            reading = {
                'timestamp': datetime.now().isoformat(),
                'voltage': round(voltage, 5),
                'current': round(current, 5),
                'power': round(power, 5),
                'dp': 0.0,  # Not available via Bluetooth
                'dn': 0.0,  # Not available via Bluetooth
                'temperature': 0.0,  # Not available via Bluetooth (yet)
                'sample': 0
            }
            
            return reading
            
        except Exception as e:
            print(f"Error parsing Bluetooth data: {e}")
            return None
    
    async def _disconnect_async(self):
        """Async disconnect handler"""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
    
    def disconnect(self):
        """Disconnect from device"""
        self.stop_reading()
        
        if self.loop and self.client:
            try:
                self.loop.run_until_complete(self._disconnect_async())
            except:
                pass
        
        self.is_connected = False
    
    def get_device_info(self):
        """Get device information"""
        if not self.client:
            return None
        
        return {
            'address': self.device_address,
            'name': self.device_name,
            'connection_type': 'bluetooth'
        }
