// Dashboard JavaScript - Real-time monitoring with Chart.js and WebSocket

let socket = null;
let charts = {};
let dataBuffer = [];
let recordingStartTime = null;
let isRecording = false;
let stats = {};
let sampleCount = 0;
let lastSampleTime = Date.now();
let lastAlertFetch = 0; // Throttle alert fetching

// Previous values for trend detection
let previousValues = {
    voltage: null,
    current: null,
    power: null
};

// Chart configuration
const chartConfig = {
    type: 'line',
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 300,
            easing: 'easeInOutQuad'
        },
        interaction: {
            intersect: false,
            mode: 'index'
        },
        plugins: {
            legend: {
                labels: {
                    color: '#cbd5e1',
                    font: {
                        size: 12,
                        weight: 'bold'
                    },
                    padding: 15
                }
            },
            tooltip: {
                enabled: true,
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                titleColor: '#f1f5f9',
                bodyColor: '#cbd5e1',
                borderColor: 'rgba(59, 130, 246, 0.5)',
                borderWidth: 1,
                padding: 12,
                displayColors: true,
                callbacks: {
                    label: function(context) {
                        let label = context.dataset.label || '';
                        if (label) {
                            label += ': ';
                        }
                        label += context.parsed.y.toFixed(5);
                        return label;
                    }
                }
            }
        },
        scales: {
            x: {
                type: 'linear',
                display: true,
                ticks: {
                    color: '#64748b',
                    font: {
                        size: 10
                    }
                },
                grid: {
                    color: 'rgba(100, 116, 139, 0.15)',
                    drawBorder: false
                }
            },
            y: {
                ticks: {
                    color: '#cbd5e1',
                    font: {
                        size: 11,
                        weight: 'bold'
                    },
                    padding: 8
                },
                grid: {
                    color: 'rgba(100, 116, 139, 0.15)',
                    drawBorder: false
                }
            }
        }
    }
};

// Initialize charts
function initCharts() {
    const voltageCtx = document.getElementById('voltage-chart');
    const currentCtx = document.getElementById('current-chart');
    const powerCtx = document.getElementById('power-chart');
    const combinedCtx = document.getElementById('combined-chart');

    // Create gradient fills
    const voltageGradient = voltageCtx.getContext('2d').createLinearGradient(0, 0, 0, 250);
    voltageGradient.addColorStop(0, 'rgba(234, 179, 8, 0.3)');
    voltageGradient.addColorStop(1, 'rgba(234, 179, 8, 0.01)');

    const currentGradient = currentCtx.getContext('2d').createLinearGradient(0, 0, 0, 250);
    currentGradient.addColorStop(0, 'rgba(168, 85, 247, 0.3)');
    currentGradient.addColorStop(1, 'rgba(168, 85, 247, 0.01)');

    const powerGradient = powerCtx.getContext('2d').createLinearGradient(0, 0, 0, 250);
    powerGradient.addColorStop(0, 'rgba(239, 68, 68, 0.3)');
    powerGradient.addColorStop(1, 'rgba(239, 68, 68, 0.01)');

    charts.voltage = new Chart(voltageCtx, {
        ...chartConfig,
        data: {
            datasets: [{
                label: 'Voltage (V)',
                data: [],
                borderColor: '#eab308',
                backgroundColor: voltageGradient,
                borderWidth: 3,
                pointRadius: 0,
                tension: 0.2,
                fill: true
            }]
        }
    });

    charts.current = new Chart(currentCtx, {
        ...chartConfig,
        data: {
            datasets: [{
                label: 'Current (A)',
                data: [],
                borderColor: '#a855f7',
                backgroundColor: currentGradient,
                borderWidth: 3,
                pointRadius: 0,
                tension: 0.2,
                fill: true
            }]
        }
    });

    charts.power = new Chart(powerCtx, {
        ...chartConfig,
        data: {
            datasets: [{
                label: 'Power (W)',
                data: [],
                borderColor: '#ef4444',
                backgroundColor: powerGradient,
                borderWidth: 3,
                pointRadius: 0,
                tension: 0.2,
                fill: true
            }]
        }
    });
    
    charts.combined = new Chart(combinedCtx, {
        ...chartConfig,
        data: {
            datasets: [
                {
                    label: 'Voltage (V)',
                    data: [],
                    borderColor: '#3b82f6',
                    borderWidth: 2,
                    pointRadius: 0,
                    yAxisID: 'y'
                },
                {
                    label: 'Current (A)',
                    data: [],
                    borderColor: '#10b981',
                    borderWidth: 2,
                    pointRadius: 0,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            ...chartConfig.options,
            scales: {
                ...chartConfig.options.scales,
                y1: {
                    type: 'linear',
                    position: 'right',
                    ticks: {
                        color: '#94a3b8'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        }
    });
}

// Connect to WebSocket
function connectWebSocket() {
    socket = io();
    
    socket.on('connect', () => {
        console.log('WebSocket connected');
    });
    
    socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
    });
    
    socket.on('new_reading', (reading) => {
        handleNewReading(reading);
    });
    
    socket.on('historical_data', (data) => {
        // Load historical data into charts
        data.forEach(reading => handleNewReading(reading, false));
    });
}

// Handle new reading
function handleNewReading(reading, updateCharts = true) {
    // Update display values with flash animation
    const voltageEl = document.getElementById('voltage-value');
    const currentEl = document.getElementById('current-value');
    const powerEl = document.getElementById('power-value');

    // Add flash effect
    voltageEl.classList.add('value-updated');
    currentEl.classList.add('value-updated');
    powerEl.classList.add('value-updated');
    setTimeout(() => {
        voltageEl.classList.remove('value-updated');
        currentEl.classList.remove('value-updated');
        powerEl.classList.remove('value-updated');
    }, 500);

    voltageEl.textContent = formatNumber(reading.voltage, 5);
    currentEl.textContent = formatNumber(reading.current, 5);
    powerEl.textContent = formatNumber(reading.power, 5);

    // USB-only fields (may not be available via Bluetooth)
    if (reading.dp !== undefined) {
        document.getElementById('dp-value').textContent = formatNumber(reading.dp, 3) + ' V';
    }
    if (reading.dn !== undefined) {
        document.getElementById('dn-value').textContent = formatNumber(reading.dn, 3) + ' V';
    }
    if (reading.temperature !== undefined) {
        document.getElementById('temp-value').textContent = formatNumber(reading.temperature, 1) + ' °C';
    }

    // Update trend indicators
    updateTrendIndicator('voltage', reading.voltage);
    updateTrendIndicator('current', reading.current);
    updateTrendIndicator('power', reading.power);

    // Update protocol detection
    if (reading.protocol) {
        updateProtocolBadge(reading.protocol);
    }

    // Check for alerts (throttled to once per 2 seconds)
    if (reading.has_alerts) {
        const now = Date.now();
        if (now - lastAlertFetch > 2000) {
            lastAlertFetch = now;
            fetchAlerts();
        }
    }

    // Add to buffer
    dataBuffer.push(reading);
    if (dataBuffer.length > 1000) {
        dataBuffer.shift();
    }
    
    // Calculate sample rate
    sampleCount++;
    const now = Date.now();
    const elapsed = (now - lastSampleTime) / 1000;
    if (elapsed >= 1.0) {
        const rate = sampleCount / elapsed;
        document.getElementById('sample-rate').textContent = rate.toFixed(1) + ' Hz';
        sampleCount = 0;
        lastSampleTime = now;
    }
    
    if (updateCharts) {
        updateChartsWithReading(reading);
    }
    
    // Update statistics if recording
    if (isRecording) {
        updateRecordingStats();
    }
}

// Update trend indicator
function updateTrendIndicator(metric, value) {
    const trendEl = document.getElementById(`${metric}-trend`);
    if (!trendEl) return;

    if (previousValues[metric] !== null) {
        const diff = value - previousValues[metric];
        const threshold = 0.0001; // Threshold for detecting change

        if (Math.abs(diff) < threshold) {
            trendEl.textContent = '─';
            trendEl.className = 'font-semibold';
        } else if (diff > 0) {
            trendEl.textContent = '↑';
            trendEl.className = 'font-semibold text-green-400';
        } else {
            trendEl.textContent = '↓';
            trendEl.className = 'font-semibold text-red-400';
        }
    }

    previousValues[metric] = value;
}

// Update charts with new reading
function updateChartsWithReading(reading) {
    const timestamp = dataBuffer.length;
    
    // Voltage chart
    charts.voltage.data.datasets[0].data.push({
        x: timestamp,
        y: reading.voltage
    });
    
    // Current chart
    charts.current.data.datasets[0].data.push({
        x: timestamp,
        y: reading.current
    });
    
    // Power chart
    charts.power.data.datasets[0].data.push({
        x: timestamp,
        y: reading.power
    });
    
    // Combined chart
    charts.combined.data.datasets[0].data.push({
        x: timestamp,
        y: reading.voltage
    });
    charts.combined.data.datasets[1].data.push({
        x: timestamp,
        y: reading.current
    });
    
    // Keep only last 500 points for performance
    Object.values(charts).forEach(chart => {
        chart.data.datasets.forEach(dataset => {
            if (dataset.data.length > 500) {
                dataset.data.shift();
            }
        });
        chart.update('active'); // Update with smooth animation
    });
}

// Connect to device
async function connectDevice(mode = 'auto') {
    try {
        showToast(`Connecting via ${mode}...`, 'info');
        
        const result = await apiRequest('/api/connect', {
            method: 'POST',
            body: JSON.stringify({ mode })
        });
        
        if (result.success) {
            updateConnectionStatus(true, result.connection_type);
            showToast(`Connected via ${result.connection_type.toUpperCase()}`, 'success');
            
            // Update UI
            document.getElementById('connection-type-text').textContent = 
                `Connected via ${result.connection_type.toUpperCase()}`;
            document.querySelectorAll('[id^="btn-connect"]').forEach(btn => btn.classList.add('hidden'));
            document.getElementById('btn-disconnect').classList.remove('hidden');
            
            // Connect WebSocket
            if (!socket) {
                connectWebSocket();
            }
        }
    } catch (error) {
        showToast(`Connection failed: ${error.message}`, 'error');
    }
}

// Disconnect from device
async function disconnectDevice() {
    try {
        await apiRequest('/api/disconnect', { method: 'POST' });
        
        updateConnectionStatus(false);
        showToast('Disconnected', 'info');
        
        // Update UI
        document.getElementById('connection-type-text').textContent = 'Not connected';
        document.querySelectorAll('[id^="btn-connect"]').forEach(btn => btn.classList.remove('hidden'));
        document.getElementById('btn-disconnect').classList.add('hidden');
        
        // Disconnect WebSocket
        if (socket) {
            socket.disconnect();
            socket = null;
        }
    } catch (error) {
        showToast(`Disconnect failed: ${error.message}`, 'error');
    }
}

// Start recording
async function startRecording() {
    try {
        const result = await apiRequest('/api/recording/start', { method: 'POST' });
        
        if (result.success) {
            isRecording = true;
            recordingStartTime = new Date();
            dataBuffer = []; // Clear buffer for new recording
            
            showToast('Recording started', 'success');
            
            document.getElementById('recording-status').textContent = 'Recording...';
            document.getElementById('btn-start-recording').classList.add('hidden');
            document.getElementById('btn-stop-recording').classList.remove('hidden');
            
            // Start duration counter
            updateRecordingDuration();
        }
    } catch (error) {
        showToast(`Failed to start recording: ${error.message}`, 'error');
    }
}

// Stop recording
async function stopRecording() {
    try {
        const result = await apiRequest('/api/recording/stop', { method: 'POST' });
        
        if (result.success) {
            isRecording = false;
            
            showToast(`Recording stopped. ${result.session.stats.samples_collected} samples saved.`, 'success');
            
            document.getElementById('recording-status').textContent = 'Not recording';
            document.getElementById('btn-start-recording').classList.remove('hidden');
            document.getElementById('btn-stop-recording').classList.add('hidden');
        }
    } catch (error) {
        showToast(`Failed to stop recording: ${error.message}`, 'error');
    }
}

// Update recording duration
function updateRecordingDuration() {
    if (!isRecording) return;
    
    const elapsed = (Date.now() - recordingStartTime.getTime()) / 1000;
    document.getElementById('stat-duration').textContent = formatDuration(elapsed);
    
    setTimeout(updateRecordingDuration, 1000);
}

// Update recording statistics
async function updateRecordingStats() {
    try {
        const stats = await apiRequest('/api/stats');
        
        document.getElementById('stat-samples').textContent = stats.samples_collected || 0;
        document.getElementById('stat-energy').textContent = formatNumber(stats.total_energy_wh || 0, 4) + ' Wh';
        document.getElementById('stat-capacity').textContent = formatNumber(stats.total_capacity_ah || 0, 4) + ' Ah';
        
        // Update min/max values
        document.getElementById('voltage-min').textContent = formatNumber(stats.min_voltage, 2);
        document.getElementById('voltage-max').textContent = formatNumber(stats.max_voltage, 2);
        document.getElementById('current-min').textContent = formatNumber(stats.min_current, 2);
        document.getElementById('current-max').textContent = formatNumber(stats.max_current, 2);
        document.getElementById('power-max').textContent = formatNumber(stats.max_power, 2);
        document.getElementById('power-avg').textContent = formatNumber(stats.avg_power, 2);
    } catch (error) {
        console.error('Failed to update stats:', error);
    }
}

// Export to CSV
function exportToCSV() {
    if (dataBuffer.length === 0) {
        showToast('No data to export', 'warning');
        return;
    }

    exportDataToCSV(dataBuffer);
}

// Update protocol badge
function updateProtocolBadge(protocol) {
    const badge = document.getElementById('protocol-badge');
    const nameEl = document.getElementById('protocol-name');

    if (!badge || !nameEl) return;

    nameEl.textContent = `${protocol.protocol} ${protocol.mode}`;
    badge.classList.remove('hidden');

    // Set badge color based on protocol
    const protocolColors = {
        'USB-PD': 'bg-blue-600',
        'QC 2.0': 'bg-purple-600',
        'QC 3.0': 'bg-purple-500',
        'AFC': 'bg-pink-600',
        'Apple 2.4A': 'bg-green-600',
        'DCP': 'bg-amber-600',
        'Standard USB': 'bg-gray-600',
        'Unknown': 'bg-red-600'
    };

    // Remove all color classes
    Object.values(protocolColors).forEach(color => badge.classList.remove(color));

    // Add appropriate color
    const colorClass = protocolColors[protocol.protocol] || 'bg-gray-600';
    badge.classList.add(colorClass);
}

// Fetch and display alerts
async function fetchAlerts() {
    try {
        const result = await apiRequest('/api/alerts');
        if (result.success && result.alerts.length > 0) {
            displayAlerts(result.alerts);
        } else {
            hideAlerts();
        }
    } catch (error) {
        console.error('Failed to fetch alerts:', error);
    }
}

// Display alerts
function displayAlerts(alerts) {
    const panel = document.getElementById('alert-panel');
    const listEl = document.getElementById('alert-list');

    if (!panel || !listEl) return;

    listEl.innerHTML = '';

    alerts.forEach(alert => {
        const alertEl = document.createElement('div');
        alertEl.className = 'flex items-center justify-between p-2 rounded bg-gray-800/50';

        const levelColors = {
            'critical': 'text-red-400',
            'warning': 'text-yellow-400',
            'info': 'text-blue-400'
        };

        alertEl.innerHTML = `
            <div class="flex items-center gap-2">
                <span class="${levelColors[alert.level]} font-bold">⚠</span>
                <span class="text-sm">${alert.message}</span>
            </div>
            <button onclick="acknowledgeAlert('${alert.id}')"
                    class="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs transition">
                Dismiss
            </button>
        `;

        listEl.appendChild(alertEl);
    });

    panel.classList.remove('hidden');
}

// Hide alerts
function hideAlerts() {
    const panel = document.getElementById('alert-panel');
    if (panel) {
        panel.classList.add('hidden');
    }
}

// Acknowledge an alert
async function acknowledgeAlert(alertId) {
    try {
        await apiRequest(`/api/alerts/acknowledge/${alertId}`, { method: 'POST' });
        fetchAlerts();
    } catch (error) {
        console.error('Failed to acknowledge alert:', error);
    }
}

// Clear all alerts
async function clearAlerts() {
    try {
        await apiRequest('/api/alerts/clear', { method: 'POST' });
        hideAlerts();
        showToast('All alerts cleared', 'success');
    } catch (error) {
        showToast('Failed to clear alerts', 'error');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initCharts();

    // Check if already connected
    checkConnectionStatus().then(status => {
        if (status.connected) {
            connectWebSocket();

            // Request recent data
            if (socket) {
                socket.emit('request_data', { points: 100 });
            }
        }
    });

});
