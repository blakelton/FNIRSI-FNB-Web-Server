# FNIRSI FNB58 Monitor - Complete Features Guide

## 🎯 **Overview**

This guide explains all the features, how they work, and how the data flows through the system.

---

## 📊 **Current Features**

### **1. Real-Time Monitoring**
- **Voltage, Current, Power** - Live updates at 100Hz (USB) or 10Hz (Bluetooth)
- **D+/D- Voltages** - USB data line voltages (USB only)
- **Temperature** - Device temperature monitoring (USB only)
- **Trend Indicators** - Up/Down/Stable arrows showing value changes
- **Sample Rate Display** - Shows actual sampling frequency

### **2. Protocol Detection** 🔍
Automatically identifies charging protocols based on voltage and D+/D- analysis:

**Supported Protocols:**
- ✅ **USB Power Delivery (PD)** - 9V, 12V, 15V, 20V modes
- ✅ **Qualcomm Quick Charge 2.0** - 5V, 9V, 12V
- ✅ **Qualcomm Quick Charge 3.0** - Variable 3.6V-12V
- ✅ **Samsung AFC** - Adaptive Fast Charging (9V)
- ✅ **Apple 2.4A** - Apple charging protocol
- ✅ **USB DCP** - Dedicated Charging Port
- ✅ **Standard USB** - Regular 5V USB

**How It Works:**
1. Device sends voltage + D+/D- readings
2. `ProtocolDetector` analyzes the values
3. Compares against known protocol signatures
4. Returns protocol info with name, mode, version
5. Badge appears on dashboard with color coding

**Color Codes:**
- 🔵 Blue = USB-PD
- 🟣 Purple = Quick Charge 2.0
- 🟪 Light Purple = Quick Charge 3.0
- 🎀 Pink = Samsung AFC
- 🟢 Green = Apple 2.4A
- 🟡 Amber = DCP
- ⚫ Gray = Standard USB
- 🔴 Red = Unknown

### **3. Alert System** ⚠️
Real-time threshold monitoring with visual and dismissible notifications.

**Monitored Thresholds:**
| Threshold | Default | Type |
|-----------|---------|------|
| Max Voltage | 21.0V | Critical |
| Min Voltage | 3.0V | Warning |
| Max Current | 6.0A | Critical |
| Max Power | 120.0W | Warning |
| Max Temperature | 80°C | Critical |
| Voltage Drop | 0.5V | Warning |

**Alert Levels:**
- 🔴 **CRITICAL** - Dangerous conditions (overvoltage, overcurrent, overtemp)
- 🟡 **WARNING** - Concerning but not critical (undervoltage, power limits)
- 🔵 **INFO** - Informational notifications

**Features:**
- **5-second cooldown** - Prevents alert spam
- **Dismissible notifications** - Click to acknowledge
- **Alert history** - Last 100 alerts stored
- **Auto-clear** - Acknowledged alerts automatically removed
- **Real-time panel** - Shows active alerts on dashboard

**How It Works:**
1. Every reading checked against thresholds
2. `AlertManager.check_reading()` compares values
3. If threshold exceeded → creates alert object
4. Alert added to `active_alerts` array
5. Frontend receives `has_alerts: true` in reading
6. Frontend calls `/api/alerts` to fetch details
7. Alert panel displays with color-coded severity
8. User clicks "Dismiss" → alert acknowledged
9. "Clear All" removes acknowledged alerts

### **4. Session Recording** 📹
Record and save monitoring sessions with full statistics.

**Recording Flow:**
```
1. User clicks "Start Recording" on Dashboard
   ↓
2. POST /api/recording/start
   ↓
3. DeviceManager.is_recording = true
   ↓
4. All readings saved to session_data[] array (in memory)
   ↓
5. Stats calculated in real-time (min/max/avg/energy/capacity)
   ↓
6. User clicks "Stop Recording"
   ↓
7. POST /api/recording/stop
   ↓
8. Session saved to sessions/session_YYYYMMDD_HHMMSS.json
   ↓
9. File contains:
   - start_time
   - end_time
   - data[] (all readings with protocol info)
   - stats (complete statistics)
   - connection_type (USB/Bluetooth)
```

**Session File Structure:**
```json
{
  "start_time": "2025-01-08T14:30:00.000Z",
  "end_time": "2025-01-08T14:35:00.000Z",
  "connection_type": "usb",
  "data": [
    {
      "timestamp": "...",
      "voltage": 5.12345,
      "current": 1.23456,
      "power": 6.32541,
      "dp": 0.650,
      "dn": 0.350,
      "temperature": 25.5,
      "protocol": {
        "protocol": "QC 2.0",
        "mode": "9V",
        "version": "2.0",
        "description": "..."
      },
      "has_alerts": false
    }
  ],
  "stats": {
    "samples_collected": 30000,
    "max_voltage": 5.15,
    "min_voltage": 5.10,
    "max_current": 1.50,
    "min_current": 0.10,
    "max_power": 7.50,
    "total_energy_wh": 0.0521,
    "total_capacity_ah": 0.0104,
    "avg_voltage": 5.12,
    "avg_current": 1.25,
    "avg_power": 6.40
  }
}
```

### **5. Session Management** 🗂️
View, analyze, export, and delete recorded sessions.

**Features:**
- **Session List** - All recordings with duration, samples, connection type
- **Session Viewer** - Full statistics and multi-axis charts
- **Export Options:**
  - CSV - Compatible with Excel/spreadsheets
  - JSON - Full data with metadata
- **Delete Sessions** - Remove unwanted recordings
- **Comparison Charts** - Voltage/Current/Power on separate Y-axes

**Session Viewer Details:**
- **Duration** - Total recording time
- **Samples** - Number of data points
- **Energy** - Total Wh consumed
- **Capacity** - Total mAh capacity
- **Min/Max/Avg** - For voltage, current, power
- **Interactive Chart** - Zoom, pan, hover tooltips

### **6. Advanced UI** 🎨
Modern, responsive interface with animations.

**Visual Features:**
- **Gradient backgrounds** - Animated radial glows
- **Glass morphism** - Frosted glass effect panels
- **Shimmer animation** - Light sweep across cards
- **Neon accents** - Color-coded metric cards
- **Value flash** - Highlights when values change
- **Smooth transitions** - 300ms cubic-bezier animations
- **Hover effects** - Cards lift and glow on hover
- **Chart gradients** - Area fills under line charts
- **Color themes:**
  - 🟡 Yellow/Gold - Voltage
  - 🟣 Purple - Current
  - 🔴 Red - Power

**Responsive Design:**
- Desktop: 3-column layout
- Tablet: 2-column layout
- Mobile: 1-column stacked

---

## 🔄 **Data Flow Architecture**

### **Complete Flow Diagram:**

```
┌─────────────────────────────────────────────────────────────┐
│                    FNIRSI FNB58 Device                        │
│         (100Hz USB HID / 10Hz Bluetooth LE)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Raw Data Packets
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│  USBReader       │          │ BluetoothReader  │
│  (usb_reader.py) │          │(bluetooth_reader.│
│                  │          │     py)          │
│ • Decodes 64-byte│          │ • Async BLE      │
│   HID packets    │          │ • Notify UUID    │
│ • 4 samples/pkt  │          │ • 3 values only  │
│ • V,I,D+,D-,Temp │          │ • V,I,W          │
└────────┬─────────┘          └────────┬─────────┘
         │                             │
         │ Parsed Readings             │
         │                             │
         └──────────┬──────────────────┘
                    │
                    ▼
       ┌────────────────────────┐
       │   DeviceManager        │
       │ (device_manager.py)    │
       │                        │
       │ 1. Protocol Detection  │◄─── ProtocolDetector
       │ 2. Alert Checking      │◄─── AlertManager
       │ 3. Session Recording   │
       │ 4. Statistics          │
       │ 5. Data Buffering      │
       └────────┬───────────────┘
                │
                │ Enhanced Reading
                │ {
                │   voltage, current, power,
                │   dp, dn, temperature,
                │   protocol: {...},
                │   has_alerts: true/false
                │ }
                │
        ┌───────┴────────┐
        │                │
        ▼                ▼
┌──────────────┐  ┌──────────────┐
│  Flask App   │  │  WebSocket   │
│  (app.py)    │  │  (SocketIO)  │
│              │  │              │
│ • REST API   │  │ • Real-time  │
│ • Sessions   │  │   broadcast  │
│ • Alerts     │  │ • new_reading│
│ • Thresholds │  │   event      │
└──────┬───────┘  └──────┬───────┘
       │                 │
       │ HTTP/JSON       │ WebSocket
       │                 │
       └────────┬────────┘
                │
                ▼
       ┌────────────────────┐
       │   Browser Client   │
       │                    │
       │ • dashboard.js     │
       │ • history.js       │
       │ • common.js        │
       │                    │
       │ 1. Update UI       │
       │ 2. Draw Charts     │
       │ 3. Show Alerts     │
       │ 4. Display Protocol│
       └────────────────────┘
```

---

## 🔌 **API Endpoints Reference**

### **Device Control**
```
POST /api/connect
Body: { "mode": "auto"|"usb"|"bluetooth", "device_address": "..." }
Response: { "success": true, "connection_type": "usb"|"bluetooth" }

POST /api/disconnect
Response: { "success": true }

GET /api/status
Response: { "connected": true, "connection_type": "usb" }
```

### **Data Access**
```
GET /api/reading/latest
Response: { ...reading with protocol and alert info }

GET /api/reading/recent?points=100
Response: [ ...array of recent readings ]

GET /api/stats
Response: { ...statistics object }
```

### **Protocol Detection**
```
GET /api/protocol
Response: {
  "success": true,
  "protocol": {
    "protocol": "USB-PD",
    "mode": "9V",
    "version": "2.0/3.0",
    "description": "USB Power Delivery 9V"
  }
}
```

### **Alert Management**
```
GET /api/alerts
Response: { "success": true, "alerts": [ ...active alerts ] }

GET /api/alerts/history?limit=50
Response: { "success": true, "history": [ ...alert history ] }

POST /api/alerts/acknowledge/:alert_id
Response: { "success": true }

POST /api/alerts/clear
Response: { "success": true }

GET /api/thresholds
Response: { "success": true, "thresholds": { ...threshold values } }

POST /api/thresholds
Body: { "name": "max_voltage", "value": 21.0 }
Response: { "success": true }
```

### **Session Recording**
```
POST /api/recording/start
Response: { "success": true, "start_time": "..." }

POST /api/recording/stop
Response: {
  "success": true,
  "session": { ...session data },
  "filename": "session_20250108_143000.json"
}

GET /api/sessions
Response: {
  "success": true,
  "sessions": [
    {
      "filename": "session_20250108_143000.json",
      "start_time": "...",
      "end_time": "...",
      "connection_type": "usb",
      "samples": 30000
    }
  ]
}

GET /api/sessions/:filename
Response: { "success": true, "session": { ...complete session data } }

DELETE /api/sessions/:filename
Response: { "success": true, "message": "Session deleted" }
```

### **Export**
```
POST /api/export/csv
Body: { "data": [ ...readings array ] }
Response: CSV file download
```

---

## 💡 **Feature Ideas to Add**

### **1. Efficiency Calculation** ⚡
Calculate charging efficiency if measuring both input and output.
- Input power vs output power
- Energy loss percentage
- Real-time efficiency gauge

### **2. Charging Phase Detection** 🔋
Auto-detect CC (Constant Current) and CV (Constant Voltage) phases.
- Identify when current starts dropping (CV phase)
- Calculate CC→CV transition point
- Estimate battery capacity from CC phase

### **3. Ripple/Noise Analysis** 📈
FFT analysis of voltage/current for power quality.
- Frequency spectrum
- Ripple voltage (mV)
- Harmonic distortion

### **4. E-Marker Detection** 🔌
Read USB-C cable E-Marker chip data.
- Cable capabilities (3A/5A)
- VBUS/VCONN ratings
- USB version support

### **5. Multi-Device Support** 🖥️
Monitor multiple FNB58 devices simultaneously.
- Side-by-side comparison
- Efficiency testing
- Load balancing analysis

### **6. Webhook Notifications** 🔔
Send alerts to external services.
- Discord/Slack notifications
- IFTTT integration
- Email alerts

### **7. Cloud Sync** ☁️
Save sessions to cloud storage.
- Google Drive
- Dropbox
- S3-compatible

### **8. Advanced Analytics** 📊
ML-powered insights.
- Battery health estimation
- Anomaly detection
- Predictive maintenance

---

## 🐛 **Troubleshooting**

### **Temperature Not Showing**
- Only available via USB (not Bluetooth)
- Check browser console: `console.log(dataBuffer[dataBuffer.length-1])`
- Verify `temperature` field exists in readings

### **Protocol Not Detected**
- Requires USB connection (needs D+/D- voltages)
- Some protocols may not be detected correctly
- Standard 5V USB will show as "Standard USB"

### **Alerts Not Appearing**
- Check thresholds: `/api/thresholds`
- Verify readings exceed thresholds
- Check browser console for errors

### **Sessions Not Saving**
- Check `sessions/` directory exists
- Verify write permissions
- Check Flask logs for errors

---

## 🚀 **Performance Tips**

1. **Limit chart points** - Keep at 500 max for smooth animation
2. **Use USB over Bluetooth** - 10x faster sampling rate
3. **Close unused sessions** - Reduces memory usage
4. **Export old sessions** - Keep sessions folder clean
5. **Disable alerts** - If not needed, reduces CPU usage

---

**Last Updated:** 2025-01-08
**Version:** 2.0.0 (with Protocol Detection & Alerts)
