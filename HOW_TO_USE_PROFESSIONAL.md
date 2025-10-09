# 📘 How to Use the Professional Dashboard

## 🚀 Quick Issues & Solutions

### **Issue: Oscilloscope shows blank/flat lines**

**Why This Happens:**
- Your power supply is very stable (8.8V, 1.28A constant)
- Oscilloscope shows AC waveforms and variations
- With DC power that's rock-solid, there's nothing to "scope"

**How to See Waveforms:**
1. **Trigger a QC/PD negotiation** - Unplug and replug the cable
2. **Change the load** - Plug in a device that varies its current draw
3. **Use a switching power supply** - These have ripple you can measure

**What You Should See:**
- Flat lines = GOOD (stable DC power)
- Wavy lines = Power supply ripple (can indicate quality issues)
- Spikes = Transients during negotiation or load changes

---

### **Issue: "VBUS not showing"**

**What's VBUS?**
- VBUS is another term for the main power voltage (same as "Voltage")
- Your dashboard shows it as **VOLTAGE: 8.80500V** in the cyan card

**Where to Find Voltage:**
- Top row, first card (cyan/blue colored)
- Shows 5 decimal places for precision
- Min/Max/Avg stats below

---

### **Issue: Spectrum shows "Not enough data for FFT"**

**Solution:**
1. Connect your device
2. Wait **15-20 seconds** (need 1024+ samples)
3. Switch to **SPECTRUM** tab
4. Click **ANALYZE** button
5. Spectrum will appear

**Note:** FFT is currently using mock data - real implementation coming soon

---

## 📊 Understanding Each View

### **WAVEFORM View** (Time-Series Charts)

**Purpose:** See how voltage, current, and power change over time

**Controls:**
- **TIMEBASE**: How much time to display (50ms to 10s per division)
  - 500ms/div = 5 seconds total visible
  - 10s/div = 100 seconds total visible

- **DISPLAY**: Which signals to show
  - "All Signals" = V+I+P on same chart
  - "Voltage Only" = Just voltage trace
  - "V+I Dual" = Voltage and current only

- **RUN/FREEZE**: Pause the display to examine a specific moment

- **CLEAR**: Reset charts and start fresh

**When to Use:**
- Monitor long-term stability
- Track charging progress
- Spot trends over time

---

### **OSCILLOSCOPE View** (Real-Time Scope)

**Purpose:** Examine waveforms and AC components like a real oscilloscope

**Controls (Left Panel):**

**VERTICAL:**
- CH1 (V): Voltage scale - 1V to 25V per division
- CH2 (I): Current scale - 0.1A to 10A per division

**HORIZONTAL:**
- TIME/DIV: How fast the waveform sweeps (10ms to 500ms)

**TRIGGER:**
- SOURCE: What signal triggers the capture (Voltage/Current)
- LEVEL: Voltage/current value to trigger on (e.g., 5.0V)
- EDGE: Rising or Falling edge detection

**DISPLAY:**
- PERSISTENCE: Leave trails (like phosphor glow on old scopes)
- X-Y MODE: Plot voltage vs current (Lissajous curves)

**Measurements (Bottom):**
- V<sub>RMS</sub>: Root-mean-square voltage (effective AC voltage)
- V<sub>PK</sub>: Peak voltage
- V<sub>PP</sub>: Peak-to-peak voltage (max - min)
- I<sub>RMS</sub>: RMS current
- FREQ: Estimated frequency (if periodic signal detected)

**When to Use:**
- Capture QC/PD negotiation transients
- Measure power supply ripple
- Examine switching noise
- Analyze fast load changes

**Why You See Flat Lines:**
- Your 8.8V DC is perfectly stable
- This is GOOD - means clean power
- Try unplugging/replugging to see transients

---

### **SPECTRUM View** (FFT Analysis)

**Purpose:** Frequency analysis for power quality measurement

**Controls:**
- **SIGNAL**: Analyze voltage, current, or power
- **WINDOW**: FFT window function
  - Hann: General purpose (good default)
  - Hamming: Better frequency resolution
  - Blackman: Best sidelobe suppression
  - Rectangular: No windowing (can cause artifacts)
- **FFT SIZE**: Number of samples
  - 1024: Fast, lower resolution
  - 2048: Balanced
  - 4096: Slow, high resolution

**Click ANALYZE to compute**

**Metrics:**
- **FUNDAMENTAL**: Primary frequency (e.g., 120Hz for AC ripple)
- **RIPPLE**: AC voltage on DC rail (should be <50mV for good PSU)
- **THD**: Total Harmonic Distortion (lower is better)
- **SNR**: Signal-to-Noise Ratio (higher is better)

**When to Use:**
- Check power supply quality
- Measure AC ripple on DC output
- Identify switching frequency
- Compare different chargers

---

### **ANALYSIS View** (Smart Features)

**Purpose:** Automatic detection and quality metrics

**Charging Phase Detection:**

Shows current phase of charging:
- **STANDBY**: No load (<0.1A)
- **DETECTING**: Analyzing power pattern
- **CC (Constant Current)**: Charging phase 1
  - Current steady, voltage rising
  - Bulk charging phase
- **CV (Constant Voltage)**: Charging phase 2
  - Voltage steady, current dropping
  - Top-off phase

**Timeline:** Color-coded phases over time
- Yellow = CC
- Cyan = CV
- Gray = Standby

**Stats:**
- CC DURATION: How long in constant current
- CV DURATION: How long in constant voltage
- ESTIMATED CAPACITY: Battery capacity (mAh)

**Protocol Information:**

Your dashboard shows:
- **DETECTED PROTOCOL**: USB-PD (USB Power Delivery)
- **MODE**: 9V (negotiated voltage)
- **D+ VOLTAGE**: 0.000V (USB data line)
- **D- VOLTAGE**: 0.000V (USB data line)

**Power Quality Metrics:**

Three bars showing quality (green is good):
- **POWER FACTOR**: How efficiently power is used (0-1.0)
  - 1.0 = Perfect
  - 0.9+ = Good
  - <0.8 = Poor

- **EFFICIENCY**: Input vs output power ratio
  - 90%+ = Excellent
  - 80-90% = Good
  - <80% = Check connections

- **VOLTAGE STABILITY**: How stable the voltage is
  - 99%+ = Rock solid
  - 95-99% = Good
  - <95% = Noisy/unstable

---

## 📈 Understanding the Metrics

### **Top Row Cards:**

**VOLTAGE (Cyan):**
- Main power voltage (VBUS)
- 5 decimal precision
- Your 8.80500V = USB-PD 9V mode

**CURRENT (Green):**
- Load current
- Your 1.28070A = device drawing 1.28A

**POWER (Orange):**
- Watts (V × I)
- Your 11.27730W = actual power consumption

**ENERGY/TEMP (Purple):**
- **ENERGY**: Accumulated watt-hours (Wh)
  - Starts at 0.0000 Wh
  - Increases over time
  - 39.1140 Wh = energy used since you connected

- **CAPACITY**: Accumulated milliamp-hours (mAh)
  - 4.4434 Ah = 4443.4 mAh
  - Useful for battery capacity testing

- **TEMP**: Device temperature
  - Only available via USB (not Bluetooth)
  - Shows °C
  - "-- °C" means no data available

---

## 🎯 Common Use Cases

### **Test a USB Charger:**
1. Connect FNB58 between charger and phone
2. Navigate to `/dashboard`
3. Click AUTO CONNECT
4. Check **ANALYSIS** tab for detected protocol
5. Look at **Power Quality** bars
6. Good charger = all bars >90%

### **Measure Battery Capacity:**
1. Connect between charger and battery
2. Start RECORDING
3. Let battery charge fully
4. Stop when current drops to ~0.05A
5. Check **CAPACITY** value = battery mAh
6. Export CSV for detailed analysis

### **Find Power Supply Ripple:**
1. Connect PSU
2. Wait 15 seconds
3. Switch to **SPECTRUM** tab
4. Select **Voltage**
5. Click **ANALYZE**
6. Check **RIPPLE** value
7. <50mV = Good, >100mV = Noisy

### **Capture QC/PD Negotiation:**
1. Switch to **OSCILLOSCOPE** tab
2. Set TRIGGER: Voltage, 6.0V, Rising
3. Click FREEZE
4. Unplug and replug cable
5. Scope captures voltage spike
6. Examine waveform

---

## 🔧 Troubleshooting

### **Energy/Capacity Not Changing:**
- ✅ **Fixed!** Just refresh your browser
- Should now accumulate properly
- Uses trapezoidal integration

### **Temperature Shows "--":**
- Normal if using Bluetooth
- Bluetooth doesn't transmit temperature
- Only USB HID protocol includes temp data

### **Oscilloscope Always Flat:**
- This is NORMAL for stable DC power
- Means your power supply is good quality
- Try different power source to see waveforms

### **Charging Phase Stuck on "DETECTING":**
- Normal for constant power
- Needs actual battery charging to show CC/CV
- Will transition when current/voltage patterns change

---

## 💡 Pro Tips

1. **Use FREEZE** to examine specific moments
2. **Record sessions** for later analysis
3. **Export CSV** for Excel/Python analysis
4. **Compare chargers** side-by-side
5. **Check ripple** on cheap chargers
6. **Monitor phone charging** to see CC→CV transition
7. **Use timebase** to zoom in/out on waveforms

---

## 🎨 Visual Guide

### **What Good Power Looks Like:**

**Waveform View:**
- Smooth, flat lines
- No sudden spikes
- Minimal fluctuation

**Oscilloscope:**
- Flat traces (for DC)
- Clean transitions during load changes

**Spectrum:**
- Low ripple (<50mV)
- No unexpected harmonics
- High SNR (>60dB)

**Analysis:**
- Power Factor >0.95
- Efficiency >90%
- Stability >99%

---

## 📞 Still Need Help?

Check these files:
- **QUICK_START_PROFESSIONAL.md** - Getting started
- **PROFESSIONAL_UPGRADE_GUIDE.md** - All features explained
- **REFRESH_INSTRUCTIONS.md** - Latest fixes

Or ask me specific questions about what you want to measure!
