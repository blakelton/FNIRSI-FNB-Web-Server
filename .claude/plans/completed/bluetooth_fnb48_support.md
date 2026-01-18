# Bluetooth FNB48 Family Support

**Status**: COMPLETED
**Date**: 2026-01-17
**Devices**: FNB48, FNB48S, FNB48P, C1

## Problem Statement

The Bluetooth reader was connecting to FNB48s devices successfully but receiving no data. The connection showed "Connected" but 0 packets were received during data streaming.

## Root Cause Analysis

### Investigation Process

1. **Initial Symptoms**:
   - Bluetooth connection established successfully
   - Device LED for Bluetooth turned off during test, came back on at end
   - 0 data packets received despite connection

2. **Android APK Analysis**:
   - Decompiled FNIRSI Android app (com.uct)
   - Examined `CrcTool.java`, `CmdUtli.java`, `BleDetailActivity.java`
   - Discovered critical differences from original implementation

3. **Root Causes Identified**:

   **A. Wrong CRC Algorithm**
   - Original: Simple byte sum `sum(packet) & 0xFF`
   - Correct: CRC16-XMODEM, low byte only
   - Evidence: `CrcTool.java` uses `CRC16_XMODEM()` function with polynomial 0x1021

   **B. Wrong Initialization Sequence**
   - Original: Send commands first, then enable notifications
   - Correct: Enable notifications FIRST, then send commands
   - Evidence: `BleDetailActivity.java` calls `enableNotify()` before `sendCmd()`

   **C. Flask-SocketIO Incompatibility**
   - Original: `async_mode='eventlet'`
   - Correct: `async_mode='threading'`
   - Reason: Eventlet doesn't work with asyncio (used by BluetoothReader)

## Solution Implementation

### 1. CRC16-XMODEM Algorithm

```python
def crc16_xmodem(data):
    """Calculate CRC16-XMODEM (matching Android app)"""
    crc = 0
    for byte in data:
        for bit in range(8):
            xor_flag = ((byte >> (7 - bit)) & 1) == 1
            msb_set = ((crc >> 15) & 1) == 1
            crc = (crc << 1) & 0xFFFF
            if xor_flag ^ msb_set:
                crc ^= 0x1021  # XMODEM polynomial
    return crc & 0xFFFF

def build_command(cmd, payload=None):
    """Build packet with correct CRC"""
    packet = bytes([0xAA, cmd, len(payload or [])]) + bytes(payload or [])
    crc_low = crc16_xmodem(packet) & 0xFF
    return packet + bytes([crc_low])
```

### 2. Notification Sequence Fix

```python
async def _start_notifications(self):
    # Step 1: Enable notifications FIRST
    await self.client.start_notify(self.NOTIFY_UUID, notification_handler)
    await asyncio.sleep(0.5)

    # Step 2: Send commands AFTER notifications enabled
    await self._send_init_commands()
```

### 3. Flask-SocketIO Fix

```python
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',  # Changed from 'eventlet'
)
```

## Files Modified

1. **`device/bluetooth_reader.py`**:
   - Added `crc16_xmodem()` function
   - Added `build_command()` helper
   - Fixed notification sequence in `_start_notifications()`
   - Added support for FNB48 device family
   - Added configurable adapter selection

2. **`app.py`**:
   - Changed SocketIO `async_mode` from `'eventlet'` to `'threading'`

## Test Results

- **Sample rate**: ~10 Hz (consistent with Bluetooth specification)
- **Readings**: 100+ readings per 10 seconds
- **Data accuracy**: Voltage, current, power values match device display
- **Stability**: Sustained streaming over multiple minutes

## Command Reference

| Command | Hex | Description |
|---------|-----|-------------|
| GET_INFO | 0x81 | Get device information |
| START | 0x82 | Start data transmission |
| STOP | 0x84 | Stop data transmission |
| GET_STATUS | 0x85 | Get charging status |
| TRIGGER | 0x86 | Trigger fast charge protocol |

## Example Packets

```
GET_INFO:   aa 81 00 f4  (CRC low byte = 0xF4)
START:      aa 82 00 a7  (CRC low byte = 0xA7)
STOP:       aa 84 00 01  (CRC low byte = 0x01)
GET_STATUS: aa 85 00 30  (CRC low byte = 0x30)
```

## Lessons Learned

1. **Always verify CRC algorithms** - Simple checksums vs polynomial CRCs look similar but produce different results
2. **Match reference implementation exactly** - Initialization sequence order matters
3. **Test async compatibility** - Eventlet and asyncio don't mix
4. **APK decompilation is valuable** - Official Android app is authoritative source for protocol details
