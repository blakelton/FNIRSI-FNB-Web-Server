// FNIRSI FNB58 - Oscilloscope View
// Real-time dual-trace oscilloscope with Chart.js for readability

let scopeChart = null;
let scopeBuffer = [];
let scopeSettings = {
    vScale: 10,      // Volts per division
    iScale: 5,       // Amps per division
    timeDiv: 500,    // ms per division (default 500ms = 5s total)
    triggerSource: 'none'
};

// Initialize oscilloscope when view becomes active
function initOscilloscope() {
    const canvas = document.getElementById('oscilloscope-canvas');
    if (!canvas) {
        console.error('Oscilloscope canvas not found');
        return;
    }

    // Destroy existing chart if present
    if (scopeChart) {
        scopeChart.destroy();
    }

    // Create new chart with oscilloscope styling
    scopeChart = new Chart(canvas, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: 'CH1: VBUS (V)',
                    data: [],
                    borderColor: '#00d9ff',
                    backgroundColor: 'rgba(0, 217, 255, 0.05)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1,
                    fill: false,
                    yAxisID: 'y-voltage'
                },
                {
                    label: 'CH2: Current (A)',
                    data: [],
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.05)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1,
                    fill: false,
                    yAxisID: 'y-current'
                },
                {
                    label: 'CH3: D+ Data Line (V)',
                    data: [],
                    borderColor: '#ff9933',
                    backgroundColor: 'rgba(255, 153, 51, 0.05)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1,
                    fill: false,
                    yAxisID: 'y-datalines',
                    hidden: false
                },
                {
                    label: 'CH4: D- Data Line (V)',
                    data: [],
                    borderColor: '#a855f7',
                    backgroundColor: 'rgba(168, 85, 247, 0.05)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1,
                    fill: false,
                    yAxisID: 'y-datalines',
                    hidden: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'TIME (ms)',
                        color: '#9aa0a6',
                        font: { size: 11, weight: 'bold' }
                    },
                    ticks: {
                        color: '#5f6368',
                        font: { size: 10 }
                    },
                    grid: {
                        color: '#2d3139',
                        drawBorder: false
                    }
                },
                'y-voltage': {
                    type: 'linear',
                    position: 'left',
                    title: {
                        display: true,
                        text: 'VBUS (V)',
                        color: '#00d9ff',
                        font: { size: 11, weight: 'bold' }
                    },
                    ticks: {
                        color: '#00d9ff',
                        font: { size: 11, weight: 'bold' },
                        callback: function(value) {
                            return value.toFixed(2) + 'V';
                        }
                    },
                    grid: {
                        color: '#2d3139',
                        drawBorder: false
                    },
                    min: 0,
                    max: scopeSettings.vScale
                },
                'y-current': {
                    type: 'linear',
                    position: 'right',
                    title: {
                        display: true,
                        text: 'CURRENT (A)',
                        color: '#00ff88',
                        font: { size: 11, weight: 'bold' }
                    },
                    ticks: {
                        color: '#00ff88',
                        font: { size: 11, weight: 'bold' },
                        callback: function(value) {
                            return value.toFixed(3) + 'A';
                        }
                    },
                    grid: {
                        drawOnChartArea: false,
                        color: '#2d3139',
                        drawBorder: false
                    },
                    min: 0,
                    max: scopeSettings.iScale
                },
                'y-datalines': {
                    type: 'linear',
                    position: 'right',
                    title: {
                        display: true,
                        text: 'D+/D- (V)',
                        color: '#ff9933',
                        font: { size: 10, weight: 'bold' }
                    },
                    ticks: {
                        color: '#ff9933',
                        font: { size: 10, weight: 'bold' },
                        callback: function(value) {
                            return value.toFixed(2) + 'V';
                        }
                    },
                    grid: {
                        drawOnChartArea: false,
                        color: '#2d3139',
                        drawBorder: false
                    },
                    min: 0,
                    max: 3.5  // USB data lines max ~3.3V
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#e8eaed',
                        font: { size: 11, weight: 'bold' },
                        padding: 15,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    enabled: true,
                    backgroundColor: 'rgba(18, 21, 26, 0.95)',
                    titleColor: '#e8eaed',
                    bodyColor: '#9aa0a6',
                    borderColor: '#00d9ff',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y;
                            if (label.includes('Voltage')) {
                                return label + ': ' + value.toFixed(5) + 'V';
                            } else {
                                return label + ': ' + value.toFixed(5) + 'A';
                            }
                        }
                    }
                }
            }
        }
    });

    console.log('Oscilloscope initialized with Chart.js');
}

// Update oscilloscope with new reading
function updateOscilloscope(reading) {
    if (!scopeChart) {
        initOscilloscope();
        return;
    }

    const sr = typeof sampleRate !== 'undefined' ? sampleRate : 100;
    const divisions = 10;
    const totalTimeMs = scopeSettings.timeDiv * divisions; // e.g., 50ms/div * 10 = 500ms
    const maxPoints = Math.floor((totalTimeMs / 1000) * sr); // e.g., 0.5s * 100Hz = 50 points

    // Add to buffer for measurements
    scopeBuffer.push({
        voltage: reading.voltage,
        current: reading.current,
        dp: reading.dp || 0,
        dn: reading.dn || 0
    });

    // Remove old points if over limit
    if (scopeBuffer.length > maxPoints) {
        scopeBuffer.shift();
    }

    // Rebuild chart data with proper time indexing (always starts from 0)
    const timePerSample = 1000 / sr; // ms per sample
    scopeChart.data.datasets[0].data = scopeBuffer.map((p, i) => ({ x: i * timePerSample, y: p.voltage }));
    scopeChart.data.datasets[1].data = scopeBuffer.map((p, i) => ({ x: i * timePerSample, y: p.current }));
    scopeChart.data.datasets[2].data = scopeBuffer.map((p, i) => ({ x: i * timePerSample, y: p.dp }));
    scopeChart.data.datasets[3].data = scopeBuffer.map((p, i) => ({ x: i * timePerSample, y: p.dn }));

    // Update chart
    scopeChart.update('none');

    // Update measurements
    updateMeasurements();
}

// Update measurement displays
function updateMeasurements() {
    if (scopeBuffer.length === 0) return;

    const voltages = scopeBuffer.map(r => r.voltage);
    const currents = scopeBuffer.map(r => r.current);

    // Calculate measurements
    const vRms = calculateRMS(voltages);
    const vPk = Math.max(...voltages);
    const iRms = calculateRMS(currents);
    const iPk = Math.max(...currents);

    // Update display
    const vRmsEl = document.getElementById('v-rms');
    const vPkEl = document.getElementById('v-pk');
    const iRmsEl = document.getElementById('i-rms');
    const iPkEl = document.getElementById('i-pk');

    if (vRmsEl) vRmsEl.textContent = vRms.toFixed(5) + 'V';
    if (vPkEl) vPkEl.textContent = vPk.toFixed(5) + 'V';
    if (iRmsEl) iRmsEl.textContent = iRms.toFixed(5) + 'A';
    if (iPkEl) iPkEl.textContent = iPk.toFixed(5) + 'A';

    // Estimate frequency (basic zero-crossing detection)
    const freqEl = document.getElementById('frequency');
    if (freqEl) {
        const freq = estimateFrequency(voltages);
        if (freq > 0) {
            freqEl.textContent = freq.toFixed(1) + ' Hz';
        } else {
            freqEl.textContent = 'DC';
        }
    }
}

// Calculate RMS value
function calculateRMS(values) {
    if (values.length === 0) return 0;
    const sumSquares = values.reduce((sum, val) => sum + val * val, 0);
    return Math.sqrt(sumSquares / values.length);
}

// Estimate frequency using zero-crossing detection
function estimateFrequency(values) {
    if (values.length < 10) return 0;

    // Find mean
    const mean = values.reduce((sum, val) => sum + val, 0) / values.length;

    // Count zero crossings
    let crossings = 0;
    for (let i = 1; i < values.length; i++) {
        if ((values[i-1] < mean && values[i] >= mean) ||
            (values[i-1] > mean && values[i] <= mean)) {
            crossings++;
        }
    }

    // Calculate frequency (crossings / 2 = cycles, then divide by time)
    const cycles = crossings / 2;
    const timeSeconds = values.length / (typeof sampleRate !== 'undefined' ? sampleRate : 100); // Use global sampleRate if available
    const frequency = cycles / timeSeconds;

    // Return 0 for very low frequencies (DC or near-DC)
    return frequency > 0.1 ? frequency : 0;
}

// Control functions
function updateVScale() {
    const select = document.getElementById('v-scale');
    if (select && scopeChart) {
        scopeSettings.vScale = parseFloat(select.value);
        scopeChart.options.scales['y-voltage'].max = scopeSettings.vScale;
        scopeChart.update('none');
        console.log('Voltage scale:', scopeSettings.vScale, 'V');
    }
}

function updateIScale() {
    const select = document.getElementById('i-scale');
    if (select && scopeChart) {
        scopeSettings.iScale = parseFloat(select.value);
        scopeChart.options.scales['y-current'].max = scopeSettings.iScale;
        scopeChart.update('none');
        console.log('Current scale:', scopeSettings.iScale, 'A');
    }
}

function updateScopeTimebase() {
    const select = document.getElementById('scope-timebase');
    if (select) {
        scopeSettings.timeDiv = parseInt(select.value);
        console.log('Scope timebase:', scopeSettings.timeDiv, 'ms/div');

        // Calculate new max points based on timebase
        const sr = typeof sampleRate !== 'undefined' ? sampleRate : 100;
        const divisions = 10;
        const totalTimeMs = scopeSettings.timeDiv * divisions;
        const newMaxPoints = Math.floor((totalTimeMs / 1000) * sr);

        // Trim buffer to new size if needed
        while (scopeBuffer.length > newMaxPoints) {
            scopeBuffer.shift();
        }

        // Force immediate chart update
        if (scopeChart && scopeBuffer.length > 0) {
            const timePerSample = 1000 / sr;
            scopeChart.data.datasets[0].data = scopeBuffer.map((p, i) => ({ x: i * timePerSample, y: p.voltage }));
            scopeChart.data.datasets[1].data = scopeBuffer.map((p, i) => ({ x: i * timePerSample, y: p.current }));
            scopeChart.data.datasets[2].data = scopeBuffer.map((p, i) => ({ x: i * timePerSample, y: p.dp }));
            scopeChart.data.datasets[3].data = scopeBuffer.map((p, i) => ({ x: i * timePerSample, y: p.dn }));
            scopeChart.update('none');
        }

        console.log(`Timebase changed: ${scopeSettings.timeDiv}ms/div (${totalTimeMs}ms total, ${newMaxPoints} points)`);
    }
}

console.log('Oscilloscope module loaded (Chart.js version)');
