"""
USB HID Reader for FNIRSI FNB58
Based on reverse-engineered protocol from baryluk/fnirsi-usb-power-data-logger
"""

import usb.core
import usb.util
import time
import threading
from collections import deque
from datetime import datetime


class USBReader:
    """USB HID communication with FNIRSI devices"""
    
    def __init__(self, vendor_id=0x0716, product_ids=None):
        self.vendor_id = vendor_id
        self.product_ids = product_ids or [0x5030, 0x5031]
        self.device = None
        self.ep_in = None
        self.ep_out = None
        self.is_connected = False
        self.is_reading = False
        self.is_fnb58 = False
        self.read_thread = None
        self.data_callback = None
        self.data_buffer = deque(maxlen=1000)
        
    def connect(self):
        """Connect to USB device"""
        # Find device
        for product_id in self.product_ids:
            self.device = usb.core.find(idVendor=self.vendor_id, idProduct=product_id)
            if self.device is not None:
                break
        
        if self.device is None:
            raise ConnectionError("FNIRSI device not found. Make sure it's connected via USB.")
        
        # Detach kernel driver if necessary
        if self.device.is_kernel_driver_active(0):
            try:
                self.device.detach_kernel_driver(0)
            except usb.core.USBError:
                pass
        
        # Set configuration
        try:
            self.device.set_configuration()
        except usb.core.USBError:
            pass
        
        # Get endpoints
        cfg = self.device.get_active_configuration()
        intf = cfg[(0, 0)]
        
        self.ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )
        
        self.ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
        )
        
        if self.ep_in is None or self.ep_out is None:
            raise ConnectionError("Could not find USB endpoints")
        
        # Detect if FNB58 or FNB48S (slower refresh rate)
        product_id = self.device.idProduct
        self.is_fnb58 = product_id == 0x5031
        
        self.is_connected = True
        return True
    
    def start_reading(self, callback=None):
        """Start reading data in background thread"""
        if not self.is_connected:
            raise ConnectionError("Device not connected")
        
        self.data_callback = callback
        self.is_reading = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
    
    def stop_reading(self):
        """Stop reading data"""
        self.is_reading = False
        if self.read_thread:
            self.read_thread.join(timeout=2)
    
    def _read_loop(self):
        """Main reading loop - runs in background thread"""
        # Initial delay
        time.sleep(0.1)
        
        # Refresh interval depends on device type
        refresh = 1.0 if self.is_fnb58 else 0.003
        continue_time = time.time() + refresh
        
        while self.is_reading:
            try:
                # Read data packet
                data = self.ep_in.read(size_or_buffer=64, timeout=5000)
                
                # Decode the packet
                readings = self._decode_packet(data)
                
                # Store in buffer
                for reading in readings:
                    self.data_buffer.append(reading)
                    
                    # Call callback if provided
                    if self.data_callback:
                        self.data_callback(reading)
                
                # Send keep-alive/request more data
                if time.time() >= continue_time:
                    continue_time = time.time() + refresh
                    self.ep_out.write(b"\xaa\x83" + b"\x00" * 61 + b"\x9e")
                    
            except usb.core.USBError as e:
                if self.is_reading:  # Only print if we're still supposed to be reading
                    print(f"USB Error: {e}")
                    time.sleep(0.1)
            except Exception as e:
                print(f"Error in read loop: {e}")
                time.sleep(0.1)
    
    def _decode_packet(self, data):
        """Decode data packet into readings"""
        readings = []
        timestamp = datetime.now()
        
        # Each packet contains 4 samples at offsets 1, 17, 33, 49
        offsets = [1, 17, 33, 49]
        
        for i, offset in enumerate(offsets):
            if offset + 14 >= len(data):
                break
            
            # Voltage (4 bytes, little-endian, /100000)
            voltage = (
                data[offset + 3] * 256 * 256 * 256 +
                data[offset + 2] * 256 * 256 +
                data[offset + 1] * 256 +
                data[offset + 0]
            ) / 100000.0
            
            # Current (4 bytes, little-endian, /100000)
            current = (
                data[offset + 7] * 256 * 256 * 256 +
                data[offset + 6] * 256 * 256 +
                data[offset + 5] * 256 +
                data[offset + 4]
            ) / 100000.0
            
            # D+ voltage (2 bytes, little-endian, /1000)
            dp = (data[offset + 8] + data[offset + 9] * 256) / 1000.0
            
            # D- voltage (2 bytes, little-endian, /1000)
            dn = (data[offset + 10] + data[offset + 11] * 256) / 1000.0
            
            # Temperature (2 bytes, little-endian, /10)
            temp = (data[offset + 13] + data[offset + 14] * 256) / 10.0
            
            # Calculate power
            power = voltage * current
            
            reading = {
                'timestamp': timestamp.isoformat(),
                'voltage': round(voltage, 5),
                'current': round(current, 5),
                'power': round(power, 5),
                'dp': round(dp, 3),
                'dn': round(dn, 3),
                'temperature': round(temp, 1),
                'sample': i
            }
            
            readings.append(reading)
        
        return readings
    
    def disconnect(self):
        """Disconnect from device"""
        self.stop_reading()
        
        if self.device:
            try:
                usb.util.dispose_resources(self.device)
            except:
                pass
        
        self.is_connected = False
    
    def get_device_info(self):
        """Get device information"""
        if not self.device:
            return None

        return {
            'vendor_id': f"0x{self.device.idVendor:04x}",
            'product_id': f"0x{self.device.idProduct:04x}",
            'manufacturer': usb.util.get_string(self.device, self.device.iManufacturer) if self.device.iManufacturer else "Unknown",
            'product': usb.util.get_string(self.device, self.device.iProduct) if self.device.iProduct else "Unknown",
            'serial': usb.util.get_string(self.device, self.device.iSerialNumber) if self.device.iSerialNumber else "Unknown"
        }

    def trigger_voltage(self, protocol, voltage):
        """
        Trigger fast charging protocol voltage

        Args:
            protocol: Protocol type ('pd', 'qc', 'afc', 'fcp', 'scp', 'vooc')
            voltage: Target voltage (5, 9, 12, 15, 20)

        Returns:
            bool: True if command sent successfully
        """
        if not self.is_connected or not self.ep_out:
            raise ConnectionError("Device not connected")

        # Protocol trigger commands (based on FNIRSI protocol)
        trigger_commands = {
            'pd': {
                5: b"\x5a\x01\x05",   # PD 5V
                9: b"\x5a\x01\x09",   # PD 9V
                12: b"\x5a\x01\x0c",  # PD 12V
                15: b"\x5a\x01\x0f",  # PD 15V
                20: b"\x5a\x01\x14"   # PD 20V
            },
            'qc': {
                5: b"\x5a\x02\x05",   # QC 5V
                9: b"\x5a\x02\x09",   # QC 9V
                12: b"\x5a\x02\x0c"   # QC 12V
            },
            'afc': {
                5: b"\x5a\x03\x05",   # AFC 5V
                9: b"\x5a\x03\x09",   # AFC 9V
                12: b"\x5a\x03\x0c"   # AFC 12V
            },
            'fcp': {
                5: b"\x5a\x04\x05",   # FCP 5V
                9: b"\x5a\x04\x09",   # FCP 9V
                12: b"\x5a\x04\x0c"   # FCP 12V
            },
            'scp': {
                5: b"\x5a\x05\x05",   # SCP 5V
                9: b"\x5a\x05\x09",   # SCP 9V
                12: b"\x5a\x05\x0c"   # SCP 12V
            },
            'vooc': {
                5: b"\x5a\x06\x05",   # VOOC 5V
                10: b"\x5a\x06\x0a"   # VOOC 10V
            }
        }

        if protocol not in trigger_commands:
            raise ValueError(f"Unknown protocol: {protocol}")

        if voltage not in trigger_commands[protocol]:
            raise ValueError(f"Unsupported voltage {voltage}V for {protocol.upper()}")

        command = trigger_commands[protocol][voltage]

        # Pad command to 64 bytes
        padded_command = command + b"\x00" * (64 - len(command))

        try:
            self.ep_out.write(padded_command)
            print(f"✓ Triggered {protocol.upper()} {voltage}V")
            return True
        except Exception as e:
            print(f"❌ Trigger command failed: {e}")
            raise

    def adjust_qc3_voltage(self, target_voltage):
        """
        Adjust QC 3.0 voltage in fine steps (3.6V - 12.0V)

        Args:
            target_voltage: Target voltage (float, 3.6 - 12.0)

        Returns:
            bool: True if command sent successfully
        """
        if not self.is_connected or not self.ep_out:
            raise ConnectionError("Device not connected")

        if target_voltage < 3.6 or target_voltage > 12.0:
            raise ValueError("QC 3.0 voltage must be between 3.6V and 12.0V")

        # Convert voltage to millivolts
        millivolts = int(target_voltage * 1000)

        # QC 3.0 adjustment command
        command = b"\x5a\x02" + millivolts.to_bytes(2, byteorder='little')
        padded_command = command + b"\x00" * (64 - len(command))

        try:
            self.ep_out.write(padded_command)
            print(f"✓ QC 3.0 adjusted to {target_voltage:.2f}V")
            return True
        except Exception as e:
            print(f"❌ QC 3.0 adjustment failed: {e}")
            raise
