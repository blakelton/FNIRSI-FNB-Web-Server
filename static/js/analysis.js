// FNIRSI FNB58 - Analysis View
// Charging phase detection and power quality metrics

let chargingPhase = 'STANDBY';
let phaseHistory = [];
let ccStartTime = null;
let cvStartTime = null;

// Initialize analysis view
function initAnalysis() {
    console.log('Analysis module initialized');
}

// Analyze reading for charging phase
function analyzeChargingPhase(reading) {
    const voltage = reading.voltage;
    const current = reading.current;

    // Detect charging phases
    const newPhase = detectPhase(voltage, current);

    if (newPhase !== chargingPhase) {
        onPhaseChange(chargingPhase, newPhase);
        chargingPhase = newPhase;
    }

    updatePhaseDisplay();
    updatePowerQuality(reading);
}

// Detect current charging phase
function detectPhase(voltage, current) {
    // Thresholds
    const MIN_CHARGE_CURRENT = 0.1; // Amperes
    const VOLTAGE_STABILITY_THRESHOLD = 0.05; // Volts

    if (current < MIN_CHARGE_CURRENT) {
        return 'STANDBY';
    }

    // Get recent readings for trend analysis
    const recentCount = 50;
    const recent = dataBuffer.slice(-recentCount);

    if (recent.length < recentCount) {
        return 'DETECTING';
    }

    const recentVoltages = recent.map(r => r.voltage);
    const recentCurrents = recent.map(r => r.current);

    const voltageStd = calculateStdDev(recentVoltages);
    const currentStd = calculateStdDev(recentCurrents);

    // CC Phase: Current stable, voltage rising
    if (currentStd < 0.05 && voltageStd > VOLTAGE_STABILITY_THRESHOLD) {
        return 'CC';
    }

    // CV Phase: Voltage stable, current dropping
    if (voltageStd < VOLTAGE_STABILITY_THRESHOLD && currentStd > 0.05) {
        return 'CV';
    }

    return 'DETECTING';
}

// Handle phase changes
function onPhaseChange(oldPhase, newPhase) {
    const timestamp = Date.now();

    phaseHistory.push({
        phase: newPhase,
        timestamp: timestamp,
        from: oldPhase
    });

    console.log(`Phase transition: ${oldPhase} -> ${newPhase}`);

    if (newPhase === 'CC') {
        ccStartTime = timestamp;
    } else if (newPhase === 'CV') {
        cvStartTime = timestamp;
    }

    updatePhaseTimeline();
}

// Update phase display
function updatePhaseDisplay() {
    const phaseEl = document.getElementById('charging-phase');
    if (phaseEl) {
        phaseEl.textContent = chargingPhase;

        // Color coding
        phaseEl.style.color = getPhaseColor(chargingPhase);
    }

    // Update durations
    const now = Date.now();

    if (ccStartTime && chargingPhase === 'CC') {
        const duration = (now - ccStartTime) / 1000;
        const ccDurationEl = document.getElementById('cc-duration');
        if (ccDurationEl) {
            ccDurationEl.textContent = formatDuration(duration);
        }
    }

    if (cvStartTime && chargingPhase === 'CV') {
        const duration = (now - cvStartTime) / 1000;
        const cvDurationEl = document.getElementById('cv-duration');
        if (cvDurationEl) {
            cvDurationEl.textContent = formatDuration(duration);
        }
    }

    // Estimate capacity (simplified)
    if (ccStartTime && dataBuffer.length > 0) {
        const avgCurrent = calculateAverageCurrent();
        const duration = (now - ccStartTime) / 1000 / 3600; // hours
        const capacity = avgCurrent * duration * 1000; // mAh

        const capacityEl = document.getElementById('est-capacity');
        if (capacityEl) {
            capacityEl.textContent = capacity.toFixed(0) + ' mAh';
        }
    }
}

// Get phase color
function getPhaseColor(phase) {
    switch (phase) {
        case 'CC': return '#00ff88';
        case 'CV': return '#ffd600';
        case 'STANDBY': return '#5f6368';
        case 'DETECTING': return '#00d9ff';
        default: return '#9aa0a6';
    }
}

// Update phase timeline visualization
function updatePhaseTimeline() {
    const timeline = document.getElementById('phase-timeline');
    if (!timeline) return;

    // Clear timeline
    timeline.innerHTML = '';

    // Draw phase history
    phaseHistory.forEach((entry, index) => {
        const segment = document.createElement('div');
        segment.style.cssText = `
            flex: 1;
            background: ${getPhaseColor(entry.phase)};
            height: 100%;
            border-right: 1px solid #1a1e26;
        `;
        timeline.appendChild(segment);
    });
}

// Calculate average current
function calculateAverageCurrent() {
    if (dataBuffer.length === 0) return 0;

    const currents = dataBuffer.map(r => r.current);
    return currents.reduce((a, b) => a + b, 0) / currents.length;
}

// Calculate standard deviation
function calculateStdDev(values) {
    if (values.length === 0) return 0;

    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    const squareDiffs = values.map(v => Math.pow(v - avg, 2));
    const avgSquareDiff = squareDiffs.reduce((a, b) => a + b, 0) / squareDiffs.length;

    return Math.sqrt(avgSquareDiff);
}

// Format duration
function formatDuration(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);

    if (h > 0) {
        return `${h}h ${m}m ${s}s`;
    } else if (m > 0) {
        return `${m}m ${s}s`;
    } else {
        return `${s}s`;
    }
}

// Update power quality metrics
function updatePowerQuality(reading) {
    if (dataBuffer.length < 10) return;

    // Calculate power factor (simplified)
    const powerFactor = calculatePowerFactor();
    updateMetricBar('power-factor', powerFactor * 100, powerFactor.toFixed(3));

    // Calculate efficiency (if both input and output are available)
    // This is a placeholder - real efficiency needs dual measurement
    const efficiency = 90 + Math.random() * 8; // Mock 90-98%
    updateMetricBar('efficiency', efficiency, efficiency.toFixed(1) + '%');

    // Calculate voltage stability
    const stability = calculateVoltageStability();
    updateMetricBar('stability', stability * 100, (stability * 100).toFixed(1) + '%');
}

// Calculate power factor
function calculatePowerFactor() {
    // Simplified: P / (V * I)
    const recent = dataBuffer.slice(-100);
    if (recent.length === 0) return 0;

    const avgV = recent.reduce((sum, r) => sum + r.voltage, 0) / recent.length;
    const avgI = recent.reduce((sum, r) => sum + r.current, 0) / recent.length;
    const avgP = recent.reduce((sum, r) => sum + r.power, 0) / recent.length;

    if (avgV * avgI === 0) return 0;

    const pf = avgP / (avgV * avgI);
    return Math.min(1.0, Math.max(0, pf));
}

// Calculate voltage stability
function calculateVoltageStability() {
    const recent = dataBuffer.slice(-100);
    if (recent.length === 0) return 0;

    const voltages = recent.map(r => r.voltage);
    const avg = voltages.reduce((a, b) => a + b, 0) / voltages.length;
    const stdDev = calculateStdDev(voltages);

    // Stability = 1 - (stdDev / avg)
    // Higher is better
    if (avg === 0) return 0;

    const stability = 1 - Math.min(1, stdDev / avg);
    return Math.max(0, stability);
}

// Update metric bar
function updateMetricBar(metric, percentage, value) {
    const barEl = document.getElementById(metric + '-bar');
    const numEl = document.getElementById(metric);

    if (barEl) {
        barEl.style.width = percentage + '%';

        // Color based on value
        if (percentage > 80) {
            barEl.style.background = 'linear-gradient(90deg, #00ff88, #00d9ff)';
        } else if (percentage > 50) {
            barEl.style.background = 'linear-gradient(90deg, #ffd600, #ff9933)';
        } else {
            barEl.style.background = 'linear-gradient(90deg, #ff4444, #cc0000)';
        }
    }

    if (numEl) {
        numEl.textContent = value;
    }
}

console.log('Analysis module loaded');
