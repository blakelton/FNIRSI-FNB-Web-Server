# ⚡ Quick Start: Professional Dashboard

## 🚀 Get Started in 60 Seconds

### **1. Start Your Server**
```bash
cd /Users/sethegger/FNB58
python app.py
```

### **2. Open Professional Dashboard**
In your browser, go to:
```
http://localhost:5000/dashboard
```

### **3. Connect Your FNB58**
Click the **AUTO CONNECT** button (or **USB**/**BLUETOOTH**)

✅ **That's it!** You should now see real-time measurements.

---

## 📊 What You're Looking At

### **Top Section: Metrics**
Four professional panels showing:
- **VOLTAGE** - Current voltage with MIN/MAX/AVG
- **CURRENT** - Current amperage with stats
- **POWER** - Current watts with stats
- **ENERGY** - Total Wh and Ah

### **Middle Section: View Tabs**
Four analysis modes:

1. **WAVEFORM** - Traditional time-series charts
2. **OSCILLOSCOPE** - Real oscilloscope with grid
3. **SPECTRUM** - FFT frequency analysis
4. **ANALYSIS** - Charging phases and power quality

### **Bottom Section: Recording**
- **START RECORDING** - Begin capturing session
- **STOP** - End and save session
- **EXPORT** - Download as CSV

---

## 🎯 Quick Tips

### **Waveform View**
- **Timebase**: Control how much time is visible
- **Display Mode**: Choose which signals to show
- **FREEZE**: Pause display to examine data
- **CLEAR**: Reset charts

### **Oscilloscope View**
- Adjust **V Scale** and **I Scale** for best view
- Set **Trigger** to capture events (like QC negotiation)
- Enable **Persistence** to see ripple trails

### **Spectrum View**
1. Select signal (Voltage/Current/Power)
2. Choose window function (Hann is good default)
3. Click **ANALYZE**
4. Check **Ripple** value (should be <50mV for clean power)

### **Analysis View**
- Watch **Charging Phase** change: STANDBY → CC → CV
- View **Protocol** detected (QC, PD, AFC, etc.)
- Check **Power Quality** bars (higher is better)

---

## 🔧 Common Tasks

### **Test a USB Charger**
1. Connect FNB58 between charger and device
2. Click **AUTO CONNECT**
3. View detected protocol in **ANALYSIS** tab
4. Check power quality metrics

### **Measure Charging Curve**
1. Connect device
2. Click **START RECORDING**
3. Begin charging
4. Watch phase transition in **ANALYSIS** tab
5. **STOP** after charging complete
6. **EXPORT** to CSV for analysis

### **Check Power Quality**
1. Switch to **SPECTRUM** tab
2. Select **Voltage**
3. Click **ANALYZE**
4. Check **Ripple** (lower is better)
5. Check **THD** (lower is better)

### **Capture Transients**
1. Switch to **OSCILLOSCOPE** tab
2. Set **Trigger** to Voltage, 5.5V, Rising
3. Plug in cable
4. Oscilloscope captures voltage spike
5. Click **FREEZE** to examine

---

## 🎨 Visual Guide

### **Status Indicators**
- **Green dot** = Connected
- **Red dot** = Disconnected
- **Pulsing red** = Recording

### **Color Coding**
- **Cyan (#00d9ff)** = Voltage
- **Green (#00ff88)** = Current
- **Orange (#ff9933)** = Power
- **Purple (#cc66ff)** = Energy

### **Phase Colors**
- **Green** = CC (Constant Current)
- **Yellow** = CV (Constant Voltage)
- **Gray** = STANDBY
- **Cyan** = DETECTING

---

## 🆚 Old vs New

| What | Old Dashboard (`/`) | Professional (`/dashboard`) |
|------|---------------------|------------------------------|
| **Look** | Consumer-grade with emojis | Lab equipment professional |
| **Charts** | Basic line charts | 4 modes: Waveform, Scope, Spectrum, Analysis |
| **Features** | Simple monitoring | Advanced analysis |
| **Best For** | Quick checks | Serious testing |

**Both are available!** Use whichever you prefer.

---

## 🐛 Troubleshooting

### **"Cannot connect to device"**
- Unplug and replug FNB58
- Try **USB** button specifically
- Check device is powered on

### **"Charts not showing"**
- Refresh page (Cmd+R or Ctrl+R)
- Check browser console for errors
- Ensure Flask server is running

### **"WebSocket disconnected"**
- Restart Flask server
- Refresh browser page
- Check firewall isn't blocking port 5000

### **"Not enough data for FFT"**
- Wait 10-15 seconds after connecting
- Need at least 1024 samples
- Check device is sending data

---

## 📖 Learn More

- **[PROFESSIONAL_UPGRADE_GUIDE.md](PROFESSIONAL_UPGRADE_GUIDE.md)** - Complete feature guide
- **[UPGRADE_SUMMARY.md](UPGRADE_SUMMARY.md)** - What was built
- **[FEATURES_GUIDE.md](FEATURES_GUIDE.md)** - Original feature documentation

---

## 🎉 You're All Set!

Your professional power monitoring dashboard is ready to use. Explore the four view modes and discover all the advanced features!

**Questions?** Check the guides above or examine the code in:
- `static/js/dashboard_pro.js` - Main dashboard
- `static/js/oscilloscope.js` - Oscilloscope view
- `static/js/spectrum.js` - Spectrum analyzer
- `static/js/analysis.js` - Charging phase detection

**Enjoy your professional-grade power analyzer!** ⚡
