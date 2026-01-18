"""
Bluetooth LE Reader for FNIRSI USB Testers
Supports: FNB58, FNB48, FNB48S, FNB48P, C1

Protocol reverse-engineered from:
- FNB58: parkerlreed's gist (https://gist.github.com/parkerlreed/0ce45e907ce536a0541afb90b5b49350)
- FNB48: Decompiled FNIRSI Android app (com.uct)
"""

import asyncio
import struct
import threading
from datetime import datetime
from collections import deque
from bleak import BleakClient, BleakScanner


def crc16_xmodem(data):
    """Calculate CRC16-XMODEM (matching Android app CRC16_XMODEM function)

    This is the correct CRC algorithm used by the FNB48s device.
    Returns the full 16-bit CRC value.
    """
    crc = 0
    for byte in data:
        for bit in range(8):
            # Check bit 7-i of current byte
            xor_flag = ((byte >> (7 - bit)) & 1) == 1
            # Check MSB of CRC
            msb_set = ((crc >> 15) & 1) == 1
            # Shift CRC left
            crc = (crc << 1) & 0xFFFF
            # XOR with polynomial if needed
            if xor_flag ^ msb_set:
                crc ^= 0x1021  # XMODEM polynomial
    return crc & 0xFFFF


def build_command(cmd, payload=None):
    """Build FNB48 command packet: [0xAA][CMD][LEN][DATA...][CRC_LOW]

    Format: [0xAA][CMD][LEN][DATA...][CRC_LOW]
    CRC is CRC16-XMODEM calculated over all bytes except the CRC byte itself,
    and only the low byte is appended.
    """
    if payload is None:
        payload = []

    # Build packet without CRC
    length = len(payload)
    packet = bytes([0xAA, cmd, length]) + bytes(payload)

    # Calculate CRC16-XMODEM and take low byte
    crc = crc16_xmodem(packet)
    crc_low = crc & 0xFF

    # Append CRC low byte
    return packet + bytes([crc_low])


class BluetoothReader:
    """Bluetooth LE communication with FNIRSI USB testers"""

    # BLE UUIDs - Same for both FNB58 and FNB48
    NOTIFY_SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
    WRITE_SERVICE_UUID = "0000ffe5-0000-1000-8000-00805f9b34fb"
    WRITE_UUID = "0000ffe9-0000-1000-8000-00805f9b34fb"
    NOTIFY_UUID = "0000ffe4-0000-1000-8000-00805f9b34fb"

    # FNB48 Commands (from decompiled Android app)
    CMD_GET_INFO = 0x81      # Get device information
    CMD_START = 0x82         # Start data transmission
    CMD_STOP = 0x84          # Stop data transmission
    CMD_GET_STATUS = 0x85    # Get charging status
    CMD_TRIGGER = 0x86       # Trigger fast charge protocol
    CMD_STOP_TRIGGER = 0x87  # Stop fast charge trigger
    CMD_GET_GROUP = 0x88     # Get data group
    CMD_CLEAR_GROUP = 0x89   # Clear data group
    CMD_GET_CAPACITY = 0x8A  # Get capacity data

    # Supported device name patterns
    SUPPORTED_DEVICES = ["FNB58", "FNB48", "FNB48s", "FNB48S", "FNB48P", "C1", "FNIRSI"]

    # Default BLE adapter (hci1 works on systems with multiple adapters)
    DEFAULT_ADAPTER = "hci1"

    def __init__(self, device_address=None, device_name=None, adapter=None):
        self.device_address = device_address
        self.device_name = device_name
        self.adapter = adapter or self.DEFAULT_ADAPTER
        self.client = None
        self.is_connected = False
        self.is_reading = False
        self.data_callback = None
        self.data_buffer = deque(maxlen=1000)
        self.loop = None
        self.thread = None
        self.device_type = None  # 'fnb58' or 'fnb48'
        self.sample_count = 0

        # Latest parsed values (for combining multiple packet types)
        self._voltage = 0.0
        self._current = 0.0
        self._power = 0.0
        self._dp = 0.0
        self._dn = 0.0
        self._temperature = 0.0

    def _is_fnirsi_device(self, device_name):
        """Check if device name matches a supported FNIRSI device"""
        if not device_name:
            return False
        if self.device_name:
            return self.device_name.lower() in device_name.lower()
        for pattern in self.SUPPORTED_DEVICES:
            if pattern.lower() in device_name.lower():
                return True
        return False

    def _detect_device_type(self, name):
        """Detect device type from name"""
        if not name:
            return 'fnb48'  # Default to FNB48 protocol
        name_lower = name.lower()
        if 'fnb58' in name_lower:
            return 'fnb58'
        elif 'fnb48' in name_lower or 'c1' in name_lower:
            return 'fnb48'
        return 'fnb48'  # Default

    async def scan_devices(self, timeout=10):
        """Scan for FNIRSI devices"""
        print(f"Scanning for Bluetooth devices (adapter: {self.adapter}, timeout: {timeout}s)...")
        devices = await BleakScanner.discover(timeout=timeout, adapter=self.adapter)

        fnirsi_devices = []
        for device in devices:
            if self._is_fnirsi_device(device.name):
                # Try to get RSSI from different Bleak versions
                rssi = None
                if hasattr(device, 'rssi'):
                    rssi = device.rssi
                elif hasattr(device, 'details') and device.details:
                    # Some Bleak versions store RSSI in details
                    rssi = device.details.get('rssi')
                fnirsi_devices.append({
                    'address': device.address,
                    'name': device.name,
                    'rssi': rssi
                })
                print(f"  Found: {device.name} ({device.address})")

        return fnirsi_devices

    async def _connect_async(self):
        """Async connection handler"""
        # Always scan first - Bleak needs device discovery before connection
        # Even if we have an address, we need the BLEDevice object
        print(f"Scanning for device (adapter: {self.adapter})...")
        devices = await self.scan_devices(timeout=5)

        if self.device_address:
            # Look for specific device by address
            target_device = None
            for d in devices:
                if d['address'].upper() == self.device_address.upper():
                    target_device = d
                    break

            if not target_device:
                # Try a longer scan
                print(f"Device {self.device_address} not found, trying longer scan...")
                devices = await self.scan_devices(timeout=10)
                for d in devices:
                    if d['address'].upper() == self.device_address.upper():
                        target_device = d
                        break

            if not target_device:
                raise ConnectionError(f"Device {self.device_address} not found in scan")

            self.device_name = target_device['name']
            print(f"Found device: {self.device_name} at {self.device_address}")
        else:
            # No address specified, use first found device
            if not devices:
                supported = ", ".join(self.SUPPORTED_DEVICES)
                raise ConnectionError(f"No FNIRSI devices found. Supported: {supported}")

            self.device_address = devices[0]['address']
            self.device_name = devices[0]['name']
            print(f"Found device: {devices[0]['name']} at {self.device_address}")

        # Detect device type
        self.device_type = self._detect_device_type(self.device_name)
        print(f"Device type: {self.device_type}")

        # Connect to device using specified adapter
        print(f"Connecting via adapter: {self.adapter}")
        self.client = BleakClient(self.device_address, adapter=self.adapter)
        await self.client.connect()

        if not self.client.is_connected:
            raise ConnectionError("Failed to connect to device")

        print(f"Connected to {self.device_address}")

        # NOTE: Don't send init commands here - they should be sent AFTER
        # notifications are enabled (matching Android app behavior)
        # The commands will be sent in _start_notifications()

        self.is_connected = True
        return True

    async def _send_init_commands(self):
        """Send initialization commands to start data streaming

        Sequence matches Android app (from BleDetailActivity.java):
        1. GET_INFO (0x81) - Request device information
        2. GET_STATUS (0x85) - Get current charging status
        3. START (0x82) - Begin data streaming
        """
        if self.device_type == 'fnb58':
            # FNB58 uses simple init commands (from parkerlreed's gist)
            commands = [
                (bytes([0xaa, 0x81, 0x00, 0xf4]), 0.5),   # Get info, wait 500ms
                (bytes([0xaa, 0x82, 0x00, 0xa7]), 0.1)    # Start streaming
            ]
        else:
            # FNB48/C1 use the build_command helper
            # Sequence from Android app: GET_INFO -> wait -> GET_STATUS -> START
            commands = [
                (build_command(self.CMD_GET_INFO), 1.0),    # Get device info, wait 1s for response
                (build_command(self.CMD_GET_STATUS), 0.3),  # Get charging status
                (build_command(self.CMD_START), 0.1),       # Start data streaming
            ]

        for cmd, delay in commands:
            print(f"Sending command: {cmd.hex()}")
            await self.client.write_gatt_char(self.WRITE_UUID, cmd)
            await asyncio.sleep(delay)

    def connect(self):
        """Connect to Bluetooth device (synchronous wrapper)"""
        # Start the connection in a background thread that will also handle reading
        self.thread = threading.Thread(target=self._connection_thread, daemon=True)
        self.thread.start()

        # Wait for connection to complete
        timeout = 30
        start = datetime.now()
        while not self.is_connected and (datetime.now() - start).seconds < timeout:
            if hasattr(self, '_connection_error') and self._connection_error:
                raise ConnectionError(self._connection_error)
            import time
            time.sleep(0.1)

        if not self.is_connected:
            raise ConnectionError("Connection timeout")

        return True

    def _connection_thread(self):
        """Thread that handles both connection and reading"""
        self._connection_error = None
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._connect_and_read_async())
        except Exception as e:
            print(f"Connection thread error: {e}")
            self._connection_error = str(e)
            import traceback
            traceback.print_exc()
        finally:
            self.is_connected = False
            self.is_reading = False

    async def _connect_and_read_async(self):
        """Async handler for connection and reading"""
        # Connect
        await self._connect_async()

        # Wait for is_reading to be set, then start notifications
        while self.is_connected:
            if self.is_reading and self.data_callback:
                await self._start_notifications()
                # After notifications started, keep the event loop alive
                # until we're told to stop reading
                while self.is_reading and self.client and self.client.is_connected:
                    await asyncio.sleep(0.1)
                break
            await asyncio.sleep(0.1)

    async def _start_notifications(self):
        """Start BLE notifications and send init commands (matching Android app sequence)"""
        # Prevent double notification setup (race condition guard)
        if hasattr(self, '_notifications_started') and self._notifications_started:
            return
        self._notifications_started = True

        def notification_handler(sender, data):
            """Handle incoming notifications"""
            reading = self._parse_data(data)
            if reading:
                self.data_buffer.append(reading)
                if self.data_callback:
                    self.data_callback(reading)

        # Step 1: Enable notifications FIRST (like Android app does)
        await self.client.start_notify(self.NOTIFY_UUID, notification_handler)
        print("Bluetooth notifications enabled")

        # Give the notification setup time to complete
        await asyncio.sleep(0.5)

        # Step 2: Send initialization commands AFTER notifications are enabled
        # This matches the Android app sequence: notify() -> sendCmd(GET_INFO) -> sendCmd(START)
        await self._send_init_commands()

        # Return immediately - the event loop in _connect_and_read_async will keep running
        # This allows start_reading() to return promptly after setup is complete

    def start_reading(self, callback=None):
        """Start reading data"""
        if not self.is_connected:
            raise ConnectionError("Device not connected")

        self.data_callback = callback
        self.is_reading = True

        # Schedule notifications to start in the running event loop
        if self.loop and self.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._start_notifications(), self.loop)
            # Wait for notification setup to complete (with timeout)
            try:
                future.result(timeout=10)  # 10 second timeout for setup
            except Exception as e:
                print(f"Warning: Notification setup returned: {e}")
        else:
            # Loop not running yet, it will start notifications when _connect_and_read_async completes connect
            pass

    def stop_reading(self):
        """Stop reading data"""
        self.is_reading = False

        # Stop notifications if still connected
        if self.loop and self.loop.is_running() and self.client:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.client.stop_notify(self.NOTIFY_UUID), self.loop
                )
                future.result(timeout=2)
            except Exception:
                pass

        if self.thread:
            self.thread.join(timeout=2)

    def _parse_data(self, data):
        """Parse notification data packet based on device type"""
        if self.device_type == 'fnb58':
            return self._parse_fnb58_data(data)
        else:
            return self._parse_fnb48_data(data)

    def _parse_fnb58_data(self, data):
        """Parse FNB58 notification packet (parkerlreed's format)"""
        offset = 21
        scale = 10000
        min_voltage = 0.0
        max_voltage = 150.0

        if len(data) < offset + 12:
            return None

        try:
            voltage, current, power = (value / scale for value in struct.unpack_from('<iii', data, offset))

            if not (min_voltage <= voltage <= max_voltage):
                return None

            self.sample_count += 1
            return {
                'timestamp': datetime.now().isoformat(),
                'voltage': round(voltage, 5),
                'current': round(current, 5),
                'power': round(power, 5),
                'dp': 0.0,
                'dn': 0.0,
                'temperature': 0.0,
                'sample': self.sample_count
            }

        except Exception as e:
            print(f"Error parsing FNB58 data: {e}")
            return None

    def _parse_fnb48_data(self, data):
        """Parse FNB48/C1 notification packet (from decompiled app)"""
        # FNB48 packets start with 0xAA and have structure: [0xAA][CMD][LEN][DATA...][CRC]
        # Multiple packets can be concatenated in one notification
        has_main_data = False
        i = 0

        # First pass: parse all packets to update state variables
        while i < len(data):
            if data[i] == 0xAA and i + 2 < len(data):
                try:
                    cmd = data[i + 1]
                    length = data[i + 2]

                    if i + 3 + length > len(data):
                        break

                    packet_data = data[i + 3:i + 3 + length]

                    # Parse based on command type
                    if cmd == 0x04:  # Main voltage/current/power data
                        self._parse_cmd_04_update(packet_data)
                        has_main_data = True
                    elif cmd == 0x05:  # Internal resistance and temperature
                        self._parse_cmd_05(packet_data)
                    elif cmd == 0x06:  # D+/D- voltage and protocol detection
                        self._parse_cmd_06(packet_data)
                    elif cmd == 0x07:  # Waveform data (higher frequency)
                        self._parse_cmd_07_update(packet_data)
                        has_main_data = True

                    # Skip past this packet (header + cmd + len + data + crc)
                    i += 3 + length + 1

                except Exception as e:
                    print(f"Error parsing FNB48 packet: {e}")
                    i += 1
            else:
                i += 1

        # Return a reading only if we got main data (V/I/P)
        if has_main_data:
            self.sample_count += 1
            return {
                'timestamp': datetime.now().isoformat(),
                'voltage': round(self._voltage, 5),
                'current': round(self._current, 5),
                'power': round(self._power, 5),
                'dp': round(self._dp, 3),
                'dn': round(self._dn, 3),
                'temperature': round(self._temperature, 1),
                'sample': self.sample_count
            }

        return None

    def _parse_cmd_04_update(self, data):
        """Parse command 0x04 and update state: Main voltage/current/power (12 bytes)"""
        if len(data) < 12:
            return

        scale = 10000
        voltage = struct.unpack_from('<i', data, 0)[0] / scale
        current = struct.unpack_from('<i', data, 4)[0] / scale
        power = struct.unpack_from('<i', data, 8)[0] / scale

        if 0.0 <= voltage <= 150.0:
            self._voltage = voltage
            self._current = current
            self._power = power

    def _parse_cmd_05(self, data):
        """Parse command 0x05: Internal resistance and temperature"""
        if len(data) < 7:
            return

        # Temperature is at bytes 4-6 (sign byte + 2-byte value)
        try:
            sign = 1 if data[4] > 0 else -1
            temp_raw = struct.unpack_from('<H', data, 5)[0]
            self._temperature = (sign * temp_raw) / 10.0
        except Exception:
            pass

    def _parse_cmd_06(self, data):
        """Parse command 0x06: D+/D- voltage and protocol detection"""
        if len(data) < 6:
            return

        try:
            # D- voltage (bytes 0-1), D+ voltage (bytes 2-3)
            dn_raw = struct.unpack_from('<H', data, 0)[0]
            dp_raw = struct.unpack_from('<H', data, 2)[0]
            self._dn = dn_raw / 1000.0
            self._dp = dp_raw / 1000.0
        except Exception:
            pass

    def _parse_cmd_07_update(self, data):
        """Parse command 0x07 and update state: Waveform data (4 bytes)"""
        if len(data) < 4:
            return

        try:
            # Bytes 0-1: voltage, Bytes 2-3: current (both in mV/mA)
            voltage_raw = struct.unpack_from('<H', data, 0)[0]
            current_raw = struct.unpack_from('<H', data, 2)[0]

            voltage = voltage_raw / 1000.0
            current = current_raw / 1000.0
            power = voltage * current

            if 0.0 <= voltage <= 150.0:
                self._voltage = voltage
                self._current = current
                self._power = power
        except Exception:
            pass

    async def _disconnect_async(self):
        """Async disconnect handler"""
        # Send stop command before disconnecting
        if self.client and self.client.is_connected:
            try:
                stop_cmd = build_command(self.CMD_STOP)
                await self.client.write_gatt_char(self.WRITE_UUID, stop_cmd)
                await asyncio.sleep(0.1)
            except Exception:
                pass
            await self.client.disconnect()

    def disconnect(self):
        """Disconnect from device"""
        self.stop_reading()
        self._notifications_started = False  # Reset for potential reconnection

        if self.loop and self.client:
            try:
                self.loop.run_until_complete(self._disconnect_async())
            except Exception:
                pass

        self.is_connected = False

    def get_device_info(self):
        """Get device information"""
        if not self.client:
            return None

        return {
            'address': self.device_address,
            'name': self.device_name,
            'device_type': self.device_type,
            'connection_type': 'bluetooth'
        }
