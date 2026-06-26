"""
USB HID Reader for FNIRSI FNB58 and family.

Uses ``hidapi`` (cython-hidapi, imported as ``hid``) rather than libusb/PyUSB.
The FNIRSI meters expose a vendor-defined HID-class interface. On macOS the
kernel's IOHIDFamily driver exclusively owns every HID interface, so libusb
cannot claim it (it fails with "[Errno 13] Access denied" no matter what — root
and Privacy & Security settings do not help). hidapi talks through Apple's
IOHIDManager, which opens vendor-defined HID devices without root and without
any special permission, and it works identically on Linux and Windows.

Protocol (decoding, commands, refresh rates) is unchanged from the original
PyUSB implementation, based on baryluk/fnirsi-usb-power-data-logger.

hidapi notes that shape this code:
- Writes: the first byte of the buffer is the HID Report ID. These meters use a
  single, unnumbered report, so we prepend ``0x00`` to every 64-byte command
  (giving a 65-byte buffer); the 0x00 is consumed as the report id and the 64
  data bytes go on the wire. This matters on macOS/Windows especially.
- Reads: with unnumbered reports, ``read()`` returns the plain 64-byte report
  (no leading report-id byte), matching the old ``ep_in.read(64)``.
"""

import sys
import time
import threading
from collections import deque
from datetime import datetime

# hidapi is imported lazily/optionally so the rest of the app (e.g. the
# Bluetooth path) still works if it is not installed yet. connect() raises a
# clear, actionable error if it is missing.
try:
    import hid  # provided by the `hidapi` (cython-hidapi) package
    _HIDAPI_AVAILABLE = True
    _HIDAPI_IMPORT_ERROR = None
except ImportError as _e:  # pragma: no cover - environment dependent
    hid = None
    _HIDAPI_AVAILABLE = False
    _HIDAPI_IMPORT_ERROR = _e


REPORT_SIZE = 64  # bytes per HID report (command and data packets)


class USBReader:
    """USB HID communication with FNIRSI devices (via hidapi)."""

    # Supported FNIRSI devices: (vendor_id, product_id)
    SUPPORTED_DEVICES = [
        (0x2e3c, 0x0049),  # FNIRSI FNB48P / FNB48S
        (0x2e3c, 0x5558),  # FNIRSI FNB58
        (0x0483, 0x003a),  # FNIRSI FNB48 (older)
        (0x0483, 0x003b),  # FNIRSI C1
        (0x0716, 0x5030),  # WITRN U2p
        (0x0716, 0x5031),  # WITRN variant
    ]

    def __init__(self, vendor_id=None, product_ids=None):
        self.vendor_id = vendor_id
        self.product_ids = product_ids
        self.device = None              # hid.device() handle once opened
        self.is_connected = False
        self.is_reading = False
        self.is_fnb58_or_fnb48s = False
        self.read_thread = None
        self.data_callback = None
        self.data_buffer = deque(maxlen=1000)
        self._device_info = {}          # populated from hid.enumerate() entry

    def connect(self):
        """Connect to the USB device via hidapi.

        Raises:
            ConnectionError: if hidapi is unavailable, no device is found, or
                the device rejects the open/handshake. Unlike the previous
                implementation, failures are NOT swallowed — connect() only
                returns True when the transport is genuinely working.
        """
        if not _HIDAPI_AVAILABLE:
            raise ConnectionError(
                "hidapi is not installed. Install it with: pip install hidapi "
                f"(import failed: {_HIDAPI_IMPORT_ERROR})"
            )

        # Decide which (vendor, product) pairs to look for.
        if self.vendor_id and self.product_ids:
            candidates = [(self.vendor_id, pid) for pid in self.product_ids]
        else:
            candidates = list(self.SUPPORTED_DEVICES)

        info = None
        for vid, pid in candidates:
            entries = hid.enumerate(vid, pid)
            if entries:
                info = self._select_interface(entries)
                self.vendor_id = vid
                self.product_id = pid
                print(f"Found device: VID=0x{vid:04x} PID=0x{pid:04x}")
                break

        if info is None:
            raise ConnectionError(
                "FNIRSI device not found. Make sure it's connected via USB."
            )

        self._device_info = info

        # Open the HID device. No kernel-driver detach, no set_configuration,
        # no interface claim — hidapi/IOHIDManager handle that for us.
        self.device = hid.device()
        try:
            self.device.open_path(info["path"])
        except Exception as e:
            raise ConnectionError(self._open_error_hint(e))

        # Blocking reads with an explicit per-read timeout (see _read_loop).
        try:
            self.device.set_nonblocking(0)
        except Exception:
            pass  # not fatal; default is blocking

        # FNB58 and FNB48S (vendor 0x2e3c) need a different refresh rate.
        self.is_fnb58_or_fnb48s = (self.vendor_id == 0x2e3c)
        print(f"Device type: {'FNB58/FNB48S' if self.is_fnb58_or_fnb48s else 'FNB48/C1'}")

        # Required to start data streaming. Errors propagate (no swallowing).
        self._send_init_handshake()

        # Best-effort sanity read: surface a dead pipe immediately, but tolerate
        # an empty result (the first packet can lag, especially on FNB58 @ 1Hz).
        try:
            self.device.read(REPORT_SIZE, 1000)
        except Exception as e:
            raise ConnectionError(f"USB read failed after handshake: {e}")

        self.is_connected = True
        return True

    @staticmethod
    def _select_interface(entries):
        """Pick the HID interface from hid.enumerate() results.

        hid.enumerate() only returns HID-class interfaces, so every entry here is
        already a valid candidate. On the FNB58 the data protocol lives on the
        device's sole HID interface (interface 3, interrupt EP 0x83/0x03 per its
        USB descriptor); the mass-storage and CDC interfaces are not HID and
        never appear here, so we take the first HID interface. If a device ever
        exposes more than one HID interface we log them so the choice is
        debuggable.
        """
        if len(entries) > 1:
            numbers = [e.get("interface_number", "?") for e in entries]
            print(f"Multiple HID interfaces found (interface numbers {numbers}); "
                  "using the first")
        return entries[0]

    @staticmethod
    def _open_error_hint(error):
        """Build an actionable error message for an open_path() failure."""
        msg = f"Failed to open USB (HID) device: {error}"
        if sys.platform.startswith("linux"):
            msg += (
                ". On Linux this is almost always a permissions problem on the "
                "/dev/hidraw* node. Install the hidraw udev rule, e.g. "
                "'SUBSYSTEM==\"hidraw\", ATTRS{idVendor}==\"2e3c\", MODE=\"0666\"' "
                "(re-run ./install_linux.sh, or copy docker/99-fnirsi.rules to "
                "/etc/udev/rules.d/), reload with 'sudo udevadm control "
                "--reload-rules && sudo udevadm trigger', then unplug/replug the "
                "device. A usb-subsystem-only rule does NOT grant hidraw access."
            )
        return msg

    def _write(self, payload):
        """Write a 64-byte command, prepending the report-id (0x00) byte.

        Args:
            payload: bytes of length <= REPORT_SIZE (padded with zeros).
        """
        if not self.device:
            raise ConnectionError("Device not connected")
        buf = bytes(payload[:REPORT_SIZE])
        buf = buf + bytes(REPORT_SIZE - len(buf))   # pad to 64 data bytes
        buf = bytes([0x00]) + buf                    # leading report id
        result = self.device.write(list(buf))
        if isinstance(result, int) and result < 0:
            err = ""
            try:
                err = self.device.error()
            except Exception:
                pass
            raise ConnectionError(f"HID write failed: {err}")
        return result

    def _send_init_handshake(self):
        """Send initialization commands to start data streaming.

        Raises:
            ConnectionError: if the device rejects a command, so connect() does
                not report a false success.
        """
        try:
            # Initial setup commands
            self._write(b"\xaa\x81" + b"\x00" * 61 + b"\x8e")
            self._write(b"\xaa\x82" + b"\x00" * 61 + b"\x96")

            # Request data command differs by device type
            if self.is_fnb58_or_fnb48s:
                self._write(b"\xaa\x82" + b"\x00" * 61 + b"\x96")
            else:
                self._write(b"\xaa\x83" + b"\x00" * 61 + b"\x9e")
            print("Initialization handshake sent")
        except ConnectionError:
            raise
        except Exception as e:
            raise ConnectionError(f"USB handshake failed: {e}")

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

        # Refresh interval: 1s for FNB58/FNB48S, 3ms for FNB48/C1
        refresh = 1.0 if self.is_fnb58_or_fnb48s else 0.003
        continue_time = time.time() + refresh

        while self.is_reading:
            try:
                # Read data packet (blocking with timeout). Returns a list of
                # ints, or [] on timeout.
                data = self.device.read(REPORT_SIZE, 5000)
                if not data:
                    continue

                # Decode the packet (decoder is transport-agnostic)
                readings = self._decode_packet(bytes(data))

                # Store in buffer
                for reading in readings:
                    self.data_buffer.append(reading)

                    # Call callback if provided
                    if self.data_callback:
                        self.data_callback(reading)

                # Send keep-alive/request more data
                if time.time() >= continue_time:
                    continue_time = time.time() + refresh
                    # Keep-alive command (same for all devices)
                    self._write(b"\xaa\x83" + b"\x00" * 61 + b"\x9e")

            except Exception as e:
                if self.is_reading:  # Only print if we're still supposed to be reading
                    print(f"USB Error: {e}")
                    time.sleep(0.1)

    def _decode_packet(self, data):
        """Decode data packet into readings"""
        readings = []
        timestamp = datetime.now()

        # Check packet type - byte 1 should be 0x04 for data packets
        if len(data) < 64 or data[1] != 0x04:
            return readings  # Ignore non-data packets

        # Each packet contains 4 samples, each 15 bytes, starting at offset 2
        # Layout: [0xaa][type][sample0 15B][sample1 15B][sample2 15B][sample3 15B][unknown][crc]
        for i in range(4):
            offset = 2 + (15 * i)
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

            # Temperature (2 bytes, little-endian, /10) - at offset 13-14
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
                self.device.close()
            except Exception:
                pass  # Device may already be disconnected

        self.is_connected = False

    def get_device_info(self):
        """Get device information"""
        if not self.device:
            return None

        info = self._device_info or {}

        def _fallback(getter, key):
            value = info.get(key)
            if value:
                return value
            try:
                return getter() or "Unknown"
            except Exception:
                return "Unknown"

        return {
            'vendor_id': f"0x{self.vendor_id:04x}" if self.vendor_id else "Unknown",
            'product_id': f"0x{getattr(self, 'product_id', 0):04x}" if getattr(self, 'product_id', None) else "Unknown",
            'manufacturer': _fallback(self.device.get_manufacturer_string, 'manufacturer_string'),
            'product': _fallback(self.device.get_product_string, 'product_string'),
            'serial': _fallback(self.device.get_serial_number_string, 'serial_number'),
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
        if not self.is_connected or not self.device:
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

        try:
            self._write(command)
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
        if not self.is_connected or not self.device:
            raise ConnectionError("Device not connected")

        if target_voltage < 3.6 or target_voltage > 12.0:
            raise ValueError("QC 3.0 voltage must be between 3.6V and 12.0V")

        # Convert voltage to millivolts
        millivolts = int(target_voltage * 1000)

        # QC 3.0 adjustment command
        command = b"\x5a\x02" + millivolts.to_bytes(2, byteorder='little')

        try:
            self._write(command)
            print(f"✓ QC 3.0 adjusted to {target_voltage:.2f}V")
            return True
        except Exception as e:
            print(f"❌ QC 3.0 adjustment failed: {e}")
            raise
