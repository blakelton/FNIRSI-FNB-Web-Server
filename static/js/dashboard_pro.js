// FNIRSI FNB58 Professional Dashboard
// Main control logic for professional interface

let socket = null;
let charts = {};
let dataBuffer = [];
let isRecording = false;
let isFrozen = false;
let currentView = 'waveform';
let displayMode = 'all';
let timebase = 500; // ms per division
let recordingStartTime = null;
let heartbeatInterval = null;
let sampleRate = 100; // Default to 100Hz, will be updated based on connection type
let connectionType = null;

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Professional Dashboard Initializing...');
    initChartsPro();
    connectWebSocket();
    checkConnectionStatus();
    initializeEventListeners();

    // Check for auto-connect URL parameters (from settings page)
    handleAutoConnect();
});

// Handle auto-connect from URL parameters
function handleAutoConnect() {
    const urlParams = new URLSearchParams(window.location.search);
    const connectMode = urlParams.get('connect');
    const deviceAddress = urlParams.get('address');

    if (connectMode) {
        console.log(`Auto-connecting: mode=${connectMode}, address=${deviceAddress}`);
        // Clear URL parameters to prevent reconnect on refresh
        window.history.replaceState({}, document.title, window.location.pathname);
        // Connect with slight delay to allow UI to initialize
        setTimeout(() => {
            connectDevice(connectMode, deviceAddress);
        }, 500);
    }
}

// Initialize all charts
function initChartsPro() {
    const ctx = document.getElementById('waveform-chart');
    if (!ctx) {
        console.error('Waveform chart canvas not found');
        return;
    }

    charts.waveform = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: 'Voltage (V)',
                    data: [],
                    borderColor: '#00d9ff',
                    backgroundColor: 'rgba(0, 217, 255, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1,
                    fill: true
                },
                {
                    label: 'Current (A)',
                    data: [],
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1,
                    fill: true
                },
                {
                    label: 'Power (W)',
                    data: [],
                    borderColor: '#ff9933',
                    backgroundColor: 'rgba(255, 153, 51, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1,
                    fill: true
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
                        text: 'SAMPLES',
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
                y: {
                    beginAtZero: true,
                    grace: '15%',  // Add 15% padding above/below to prevent cutoff
                    ticks: {
                        color: '#9aa0a6',
                        font: { size: 11, weight: 'bold' }
                    },
                    grid: {
                        color: '#2d3139',
                        drawBorder: false
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#e8eaed',
                        font: { size: 12, weight: 'bold' },
                        padding: 15
                    }
                },
                tooltip: {
                    enabled: true,
                    backgroundColor: 'rgba(18, 21, 26, 0.95)',
                    titleColor: '#e8eaed',
                    bodyColor: '#9aa0a6',
                    borderColor: '#00d9ff',
                    borderWidth: 1,
                    padding: 12
                }
            }
        }
    });

    console.log('Charts initialized successfully');
}

// Initialize event listeners
function initializeEventListeners() {
    // Timebase change
    const timebaseSelect = document.getElementById('timebase-select');
    if (timebaseSelect) {
        timebaseSelect.addEventListener('change', updateTimebase);
    }

    // Display mode change
    const displayModeSelect = document.getElementById('display-mode');
    if (displayModeSelect) {
        displayModeSelect.addEventListener('change', updateDisplayMode);
    }
}

// Connect to device
async function connectDevice(mode, deviceAddress = null) {
    try {
        showToastPro(`Connecting via ${mode.toUpperCase()}...`, 'info');

        const payload = { mode };
        if (deviceAddress) {
            payload.device_address = deviceAddress;
        }

        const result = await apiRequest('/api/connect', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (result.success) {
            updateConnectionUI(true, result.connection_type);
            showToastPro('Connected via ' + result.connection_type.toUpperCase(), 'success');
        }
    } catch (error) {
        showToastPro('Connection failed: ' + error.message, 'error');
    }
}

// Disconnect from device
async function disconnectDevice() {
    try {
        await apiRequest('/api/disconnect', { method: 'POST' });
        updateConnectionUI(false);
        showToastPro('Disconnected', 'info');

        // Clear charts
        clearCharts();
    } catch (error) {
        showToastPro('Disconnect failed: ' + error.message, 'error');
    }
}

// Update connection UI
function updateConnectionUI(connected, type = '') {
    const indicator = document.getElementById('status-led');
    const text = document.getElementById('connection-text');
    const badge = document.getElementById('connection-type-badge');

    if (connected) {
        if (indicator) indicator.classList.add('connected');
        if (text) text.textContent = 'CONNECTED';
        if (badge) badge.textContent = type.toUpperCase();

        // Update sample rate based on connection type
        connectionType = type.toLowerCase();
        if (connectionType === 'usb') {
            sampleRate = 100; // USB is 100Hz
        } else if (connectionType === 'bluetooth') {
            sampleRate = 10; // Bluetooth is 10Hz
        }
        console.log(`Sample rate set to ${sampleRate}Hz for ${type} connection`);

        // Hide connect buttons, show disconnect
        document.querySelectorAll('[id^="btn-connect"]').forEach(btn => {
            btn.classList.add('hidden');
        });
        const disconnectBtn = document.getElementById('btn-disconnect');
        if (disconnectBtn) disconnectBtn.classList.remove('hidden');
    } else {
        if (indicator) indicator.classList.remove('connected');
        if (text) text.textContent = 'DISCONNECTED';
        if (badge) badge.textContent = '';

        // Show connect buttons, hide disconnect
        document.querySelectorAll('[id^="btn-connect"]').forEach(btn => {
            btn.classList.remove('hidden');
        });
        const disconnectBtn = document.getElementById('btn-disconnect');
        if (disconnectBtn) disconnectBtn.classList.add('hidden');
    }
}

// Handle new readings from WebSocket
function handleNewReading(reading) {
    if (isFrozen) return;

    // Update header metric values with more precision
    updateMetricValue('voltage-value-header', reading.voltage, 3);
    updateMetricValue('current-value-header', reading.current, 3);
    updateMetricValue('power-value-header', reading.power, 3);

    // Update energy and capacity in header
    if (reading.energy !== undefined) {
        updateMetricValue('energy-value-header', reading.energy, 4);
    }
    if (reading.capacity !== undefined) {
        updateMetricValue('capacity-value-header', reading.capacity, 3);
    }

    // Update protocol info if available
    if (reading.protocol) {
        updateProtocolInfo(reading.protocol);
    }

    // Update additional data (USB only)
    if (reading.dp !== undefined) {
        const dpEl = document.getElementById('dp-voltage');
        if (dpEl) dpEl.textContent = reading.dp.toFixed(3) + ' V';
    }
    if (reading.dn !== undefined) {
        const dnEl = document.getElementById('dn-voltage');
        if (dnEl) dnEl.textContent = reading.dn.toFixed(3) + ' V';
    }
    if (reading.temperature !== undefined) {
        const tempEl = document.getElementById('temp-value-header');
        if (tempEl) tempEl.textContent = reading.temperature.toFixed(1);
    }

    // Add to buffer
    dataBuffer.push(reading);
    if (dataBuffer.length > 10000) {
        dataBuffer.shift();
    }

    // Update statistics
    updateStatistics();

    // Update charts based on current view
    if (currentView === 'waveform' && charts.waveform) {
        updateWaveformChart(reading);
    } else if (currentView === 'oscilloscope' && typeof updateOscilloscope === 'function') {
        updateOscilloscope(reading);
    }

    // Update analysis view continuously
    if (typeof analyzeChargingPhase === 'function') {
        analyzeChargingPhase(reading);
    }

    // Update chart info
    updateChartInfo();

    // Calculate energy and capacity from stats
    updateEnergyCapacity();
}

// Update metric value with formatting
function updateMetricValue(elementId, value, decimals) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value.toFixed(decimals);
    }
}

// Update protocol information
function updateProtocolInfo(protocol) {
    const nameEl = document.getElementById('proto-name');
    const modeEl = document.getElementById('proto-mode');

    if (nameEl) nameEl.textContent = protocol.protocol || 'UNKNOWN';
    if (modeEl) modeEl.textContent = protocol.mode || '---';
}

// Update statistics from buffer (header only shows current values, no min/max/avg)
function updateStatistics() {
    // Statistics now handled by updateEnergyCapacity
    // Header shows live values only
}

// Calculate average
function average(arr) {
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}

// Calculate and update energy and capacity
function updateEnergyCapacity() {
    if (dataBuffer.length < 2) return;

    // Calculate energy (Wh) and capacity (mAh) using trapezoidal integration
    let totalEnergy = 0; // Wh
    let totalCapacity = 0; // mAh

    for (let i = 1; i < dataBuffer.length; i++) {
        const dt = 1.0 / sampleRate / 3600.0; // Time delta in hours (dynamic sample rate)

        // Trapezoidal rule: (P1 + P2) / 2 * dt
        const avgPower = (dataBuffer[i-1].power + dataBuffer[i].power) / 2;
        const avgCurrent = (dataBuffer[i-1].current + dataBuffer[i].current) / 2;

        totalEnergy += avgPower * dt;
        totalCapacity += avgCurrent * dt * 1000; // Convert to mAh
    }

    // Calculate runtime
    const runtime = dataBuffer.length / sampleRate; // seconds (dynamic sample rate)
    const hours = Math.floor(runtime / 3600);
    const minutes = Math.floor((runtime % 3600) / 60);
    const seconds = Math.floor(runtime % 60);
    const runtimeString = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

    // Update display in header
    const energyEl = document.getElementById('energy-value-header');
    const capacityEl = document.getElementById('capacity-value-header');
    const runtimeEl = document.getElementById('runtime-value-header');

    if (energyEl) energyEl.textContent = totalEnergy.toFixed(4);
    if (capacityEl) capacityEl.textContent = totalCapacity.toFixed(2);
    if (runtimeEl) runtimeEl.textContent = runtimeString;
}

// Update waveform chart
let waveformIndex = 0;
function updateWaveformChart(reading) {
    const maxPoints = calculateMaxPoints();

    // Add new data points with auto-incrementing index
    charts.waveform.data.datasets[0].data.push({ x: waveformIndex, y: reading.voltage });
    charts.waveform.data.datasets[1].data.push({ x: waveformIndex, y: reading.current });
    charts.waveform.data.datasets[2].data.push({ x: waveformIndex, y: reading.power });
    waveformIndex++;

    // Remove old points if over limit
    if (charts.waveform.data.datasets[0].data.length > maxPoints) {
        charts.waveform.data.datasets[0].data.shift();
        charts.waveform.data.datasets[1].data.shift();
        charts.waveform.data.datasets[2].data.shift();
    }

    // Auto-adjust X-axis to show rolling window
    if (charts.waveform.data.datasets[0].data.length > 0) {
        const firstX = charts.waveform.data.datasets[0].data[0].x;
        const lastX = charts.waveform.data.datasets[0].data[charts.waveform.data.datasets[0].data.length - 1].x;
        charts.waveform.options.scales.x.min = firstX;
        charts.waveform.options.scales.x.max = lastX;
    }

    charts.waveform.update('none');
}

// Calculate max points to display based on timebase
function calculateMaxPoints() {
    // Use dynamic sample rate based on connection type
    // If sampling at 100Hz (USB) or 10Hz (BT) and timebase is 500ms/div with 10 divisions
    const divisions = 10;
    const totalTime = (timebase / 1000) * divisions; // seconds
    return Math.floor(totalTime * sampleRate);
}

// Update chart info display
function updateChartInfo() {
    const duration = dataBuffer.length > 1 ? dataBuffer.length / sampleRate : 0; // Use dynamic sample rate

    // Update all tab sample counts
    const tabIds = ['chart', 'scope', 'spectrum', 'analysis'];
    tabIds.forEach(tabId => {
        const samplesEl = document.getElementById(`${tabId}-samples`);
        const rateEl = document.getElementById(`${tabId}-rate`);
        const durationEl = document.getElementById(`${tabId}-duration`);

        if (samplesEl) samplesEl.textContent = `SAMPLES: ${dataBuffer.length}`;
        if (rateEl) rateEl.textContent = `RATE: ${sampleRate} Hz`;
        if (durationEl) durationEl.textContent = `DURATION: ${duration.toFixed(1)}s`;
    });
}

// View switching
function switchView(viewName) {
    currentView = viewName;

    // Hide all views
    document.querySelectorAll('.view-container').forEach(view => {
        view.classList.remove('active');
    });

    // Show selected view
    const selectedView = document.getElementById('view-' + viewName);
    if (selectedView) {
        selectedView.classList.add('active');
    }

    // Update both old tab-btn and new tab-btn-inline buttons
    document.querySelectorAll('.tab-btn, .tab-btn-inline').forEach(btn => {
        btn.classList.remove('active');
    });
    const selectedTab = document.getElementById('tab-' + viewName);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    // Initialize view-specific components when switching
    if (viewName === 'oscilloscope' && typeof initOscilloscope === 'function') {
        setTimeout(() => initOscilloscope(), 100); // Small delay to ensure DOM is ready
    } else if (viewName === 'spectrum' && typeof initSpectrum === 'function') {
        setTimeout(() => initSpectrum(), 100);
    } else if (viewName === 'trigger') {
        // Check connection status and update trigger panel states
        setTimeout(async () => {
            const status = await apiRequest('/api/status').catch(() => ({ connected: false }));
            if (status.connected && dataBuffer.length > 0) {
                const latestReading = dataBuffer[dataBuffer.length - 1];
                if (latestReading.protocol) {
                    updateTriggerPanelStates(latestReading.protocol);
                }
            } else {
                updateTriggerPanelStates(null);
            }
        }, 100);
    }

    console.log('Switched to view:', viewName);
}

// Control functions
function updateTimebase() {
    const select = document.getElementById('timebase-select');
    if (select) {
        timebase = parseInt(select.value);
        console.log('Timebase updated to:', timebase, 'ms/div');
    }
}

function updateDisplayMode() {
    const select = document.getElementById('display-mode');
    if (!select || !charts.waveform) return;

    displayMode = select.value;

    // Show/hide datasets based on mode
    if (displayMode === 'voltage') {
        charts.waveform.data.datasets[0].hidden = false;
        charts.waveform.data.datasets[1].hidden = true;
        charts.waveform.data.datasets[2].hidden = true;
    } else if (displayMode === 'current') {
        charts.waveform.data.datasets[0].hidden = true;
        charts.waveform.data.datasets[1].hidden = false;
        charts.waveform.data.datasets[2].hidden = true;
    } else if (displayMode === 'power') {
        charts.waveform.data.datasets[0].hidden = true;
        charts.waveform.data.datasets[1].hidden = true;
        charts.waveform.data.datasets[2].hidden = false;
    } else if (displayMode === 'vi') {
        charts.waveform.data.datasets[0].hidden = false;
        charts.waveform.data.datasets[1].hidden = false;
        charts.waveform.data.datasets[2].hidden = true;
    } else if (displayMode === 'vp') {
        charts.waveform.data.datasets[0].hidden = false;
        charts.waveform.data.datasets[1].hidden = true;
        charts.waveform.data.datasets[2].hidden = false;
    } else {
        // All signals
        charts.waveform.data.datasets.forEach(ds => ds.hidden = false);
    }

    charts.waveform.update();
}

function toggleRun() {
    toggleFreeze();
}

function toggleFreeze() {
    isFrozen = !isFrozen;

    // Update waveform buttons
    const btnRun = document.getElementById('btn-run');
    const btnFreeze = document.getElementById('btn-freeze');

    // Update scope buttons
    const btnScopeRun = document.getElementById('btn-scope-run');
    const btnScopeFreeze = document.getElementById('btn-scope-freeze');

    if (isFrozen) {
        if (btnRun) btnRun.classList.remove('active');
        if (btnFreeze) btnFreeze.classList.add('active');
        if (btnScopeRun) btnScopeRun.classList.remove('active');
        if (btnScopeFreeze) btnScopeFreeze.classList.add('active');
    } else {
        if (btnRun) btnRun.classList.add('active');
        if (btnFreeze) btnFreeze.classList.remove('active');
        if (btnScopeRun) btnScopeRun.classList.add('active');
        if (btnScopeFreeze) btnScopeFreeze.classList.remove('active');
    }
}

function clearCharts() {
    dataBuffer = [];
    if (charts.waveform) {
        charts.waveform.data.datasets.forEach(dataset => {
            dataset.data = [];
        });
        charts.waveform.update();
    }
}

// Recording functions
async function startRecording() {
    try {
        // Prompt for session name
        const sessionName = prompt('Enter a name for this recording session:',
            `Session ${new Date().toLocaleString()}`);

        if (sessionName === null) {
            // User cancelled
            return;
        }

        const result = await apiRequest('/api/recording/start', {
            method: 'POST',
            body: JSON.stringify({ name: sessionName || undefined })
        });

        if (result.success) {
            isRecording = true;
            recordingStartTime = Date.now();

            const indicator = document.getElementById('rec-indicator');
            const statusText = document.getElementById('rec-status-text');
            const btnStart = document.getElementById('btn-start-recording');
            const btnStop = document.getElementById('btn-stop-recording');

            if (indicator) indicator.classList.add('recording');
            if (statusText) statusText.textContent = sessionName ? sessionName.toUpperCase() : 'RECORDING';
            if (btnStart) btnStart.classList.add('hidden');
            if (btnStop) btnStop.classList.remove('hidden');

            updateRecordingDuration();
            showToastPro(`Recording "${sessionName || 'Untitled'}" started`, 'success');
        }
    } catch (error) {
        showToastPro('Failed to start recording: ' + error.message, 'error');
    }
}

async function stopRecording() {
    try {
        const result = await apiRequest('/api/recording/stop', {
            method: 'POST'
        });

        if (result.success) {
            isRecording = false;

            const indicator = document.getElementById('rec-indicator');
            const statusText = document.getElementById('rec-status-text');
            const btnStart = document.getElementById('btn-start-recording');
            const btnStop = document.getElementById('btn-stop-recording');

            if (indicator) indicator.classList.remove('recording');
            if (statusText) statusText.textContent = 'READY';
            if (btnStart) btnStart.classList.remove('hidden');
            if (btnStop) btnStop.classList.add('hidden');

            const sessionName = result.name || 'Session';
            const samples = result.session.stats.samples_collected;
            showToastPro(`✓ Recording saved: "${sessionName}" (${samples} samples)`, 'success');
        }
    } catch (error) {
        showToastPro('Failed to stop recording: ' + error.message, 'error');
    }
}

function updateRecordingDuration() {
    if (!isRecording) return;

    const elapsed = (Date.now() - recordingStartTime) / 1000;
    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = Math.floor(elapsed % 60);

    const durationEl = document.getElementById('rec-duration');
    if (durationEl) {
        durationEl.textContent =
            String(hours).padStart(2, '0') + ':' +
            String(minutes).padStart(2, '0') + ':' +
            String(seconds).padStart(2, '0');
    }

    // Update recording stats
    const samplesEl = document.getElementById('rec-samples');
    const sizeEl = document.getElementById('rec-size');
    const rateEl = document.getElementById('rec-rate');

    if (samplesEl) samplesEl.textContent = dataBuffer.length;
    if (sizeEl) {
        const sizeKB = (dataBuffer.length * 100) / 1024; // Rough estimate
        sizeEl.textContent = sizeKB.toFixed(1) + ' KB';
    }
    if (rateEl) rateEl.textContent = `${sampleRate} Hz`;

    setTimeout(updateRecordingDuration, 1000);
}

// Export session
async function exportSession() {
    if (dataBuffer.length === 0) {
        showToastPro('No data to export', 'warning');
        return;
    }

    // Ask user which format they want
    const format = confirm('Choose export format:\n\nOK = HTML Report (with charts & stats)\nCancel = CSV (raw data)');

    if (format) {
        // Export HTML Report
        await exportHTMLReport();
    } else {
        // Export CSV
        exportDataToCSV(dataBuffer);
    }
}

// Export comprehensive HTML report
async function exportHTMLReport() {
    try {
        showToastPro('Generating HTML report...', 'info');

        const sessionData = {
            start_time: recordingStartTime ? new Date(recordingStartTime).toLocaleString() : new Date().toLocaleString(),
            end_time: new Date().toLocaleString(),
            connection_type: 'usb', // TODO: get actual connection type
            data: dataBuffer.map(reading => ({
                voltage: reading.voltage,
                current: reading.current,
                power: reading.power,
                timestamp: reading.timestamp || Date.now()
            }))
        };

        const response = await fetch('/api/export/html', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(sessionData)
        });

        if (!response.ok) {
            throw new Error('Failed to generate report');
        }

        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `fnirsi_report_${new Date().toISOString().replace(/[:.]/g, '-')}.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        showToastPro('HTML report downloaded successfully!', 'success');
    } catch (error) {
        showToastPro('Failed to export HTML report: ' + error.message, 'error');
        console.error('Export error:', error);
    }
}

// Settings
function openSettings() {
    window.location.href = '/settings';
}

// Toast notifications
function showToastPro(message, type = 'info') {
    const container = document.getElementById('toast-container-pro');
    if (!container) {
        console.log(`[${type}] ${message}`);
        return;
    }

    const toast = document.createElement('div');
    toast.className = `toast-pro toast-${type}`;
    toast.innerHTML = `
        <div style="
            padding: 1rem 1.5rem;
            background: ${type === 'success' ? '#00ff88' : type === 'error' ? '#ff4444' : type === 'warning' ? '#ffd600' : '#00d9ff'};
            color: #000;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.85rem;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
        ">
            ${message}
        </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// WebSocket connection with auto-reconnect
function connectWebSocket() {
    // Configure SocketIO with reconnection settings
    socket = io({
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: Infinity,
        timeout: 20000,
        transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
        console.log('✓ WebSocket connected');

        // Start heartbeat to keep connection alive (especially on mobile)
        if (heartbeatInterval) clearInterval(heartbeatInterval);
        heartbeatInterval = setInterval(() => {
            if (socket && socket.connected) {
                socket.emit('ping');
            }
        }, 20000); // Send ping every 20 seconds
    });

    socket.on('disconnect', (reason) => {
        console.log('✗ WebSocket disconnected:', reason);

        // Clear heartbeat interval
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }

        // If server initiated disconnect, try to reconnect
        if (reason === 'io server disconnect') {
            socket.connect();
        }
    });

    socket.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error);
    });

    socket.on('reconnect', (attemptNumber) => {
        console.log(`✓ WebSocket reconnected after ${attemptNumber} attempts`);
    });

    socket.on('reconnect_attempt', (attemptNumber) => {
        if (attemptNumber === 1 || attemptNumber % 5 === 0) {
            console.log(`Reconnection attempt ${attemptNumber}...`);
        }
    });

    socket.on('reconnect_failed', () => {
        console.error('WebSocket reconnection failed');
        showToastPro('Connection lost - please refresh page', 'error');
    });

    socket.on('new_reading', (reading) => {
        handleNewReading(reading);
    });

    socket.on('historical_data', (data) => {
        data.forEach(reading => handleNewReading(reading));
    });
}

// API helper
async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Request failed');
    }

    return response.json();
}

// Check connection status on load
async function checkConnectionStatus() {
    try {
        const status = await apiRequest('/api/status');
        if (status.connected) {
            updateConnectionUI(true, status.connection_type);
        }
    } catch (error) {
        console.error('Failed to check status:', error);
    }
}

// Export data to CSV (use common.js function if available)
function exportDataToCSV(data) {
    const csv = convertToCSV(data);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fnirsi_export_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

function convertToCSV(data) {
    const headers = ['timestamp', 'voltage', 'current', 'power', 'dp', 'dn', 'temperature'];
    const rows = data.map(r => {
        return [
            r.timestamp || new Date().toISOString(),
            r.voltage,
            r.current,
            r.power,
            r.dp || '',
            r.dn || '',
            r.temperature || ''
        ].join(',');
    });

    return [headers.join(','), ...rows].join('\n');
}

// Toggle device panel (for mobile)
function toggleDevicePanel() {
    const content = document.getElementById('device-control-content');
    const toggle = document.getElementById('collapse-toggle');
    const bar = document.getElementById('device-control-bar');

    if (!content || !toggle || !bar) return;

    const isCollapsed = bar.classList.contains('collapsed');

    if (isCollapsed) {
        bar.classList.remove('collapsed');
        content.style.maxHeight = content.scrollHeight + 'px';
        toggle.style.transform = 'rotate(0deg)';
    } else {
        bar.classList.add('collapsed');
        content.style.maxHeight = '0';
        toggle.style.transform = 'rotate(-90deg)';
    }
}

// Auto-collapse on mobile devices
function initMobileOptimizations() {
    if (window.innerWidth <= 768) {
        const bar = document.getElementById('device-control-bar');
        const content = document.getElementById('device-control-content');
        const toggle = document.getElementById('collapse-toggle');

        if (bar && content && toggle) {
            bar.classList.add('collapsed');
            content.style.maxHeight = '0';
            toggle.style.transform = 'rotate(-90deg)';
        }
    }
}

// Initialize mobile optimizations on load
document.addEventListener('DOMContentLoaded', () => {
    initMobileOptimizations();
});

// ============ TRIGGER VIEW FUNCTIONS ============

let currentQC3Voltage = 5.0; // Track current QC 3.0 voltage
let activeProtocol = null; // Track active protocol
let activeTriggerVoltage = null; // Track active triggered voltage

// Trigger voltage change
async function triggerVoltage(protocol, voltage) {
    try {
        document.getElementById('trigger-status').textContent = `STATUS: TRIGGERING ${voltage}V...`;

        const result = await apiRequest('/api/trigger/voltage', {
            method: 'POST',
            body: JSON.stringify({ protocol, voltage })
        });

        if (result.success) {
            // Update UI to show active voltage
            updateActiveTriggerButton(protocol, voltage);
            activeTriggerVoltage = voltage;

            document.getElementById('trigger-status').textContent = `STATUS: ${protocol.toUpperCase()} ${voltage}V ACTIVE`;
            document.getElementById('trigger-warning').textContent = 'Waiting for voltage to stabilize...';

            // Clear warning after 3 seconds
            setTimeout(() => {
                document.getElementById('trigger-warning').textContent = '';
            }, 3000);

            showToastPro(`${protocol.toUpperCase()} ${voltage}V triggered successfully`, 'success');
        }
    } catch (error) {
        document.getElementById('trigger-status').textContent = 'STATUS: TRIGGER FAILED';
        document.getElementById('trigger-warning').textContent = 'Error: ' + error.message;
        showToastPro('Trigger failed: ' + error.message, 'error');
    }
}

// Adjust QC 3.0 voltage in 200mV steps
async function adjustQC3Voltage(millivolts) {
    const newVoltage = currentQC3Voltage + (millivolts / 1000);

    // Clamp to QC 3.0 range (3.6V - 12.0V)
    if (newVoltage < 3.6 || newVoltage > 12.0) {
        showToastPro(`QC 3.0 voltage range is 3.6V - 12.0V`, 'warning');
        return;
    }

    try {
        document.getElementById('trigger-status').textContent = `STATUS: ADJUSTING TO ${newVoltage.toFixed(2)}V...`;

        const result = await apiRequest('/api/trigger/qc3-adjust', {
            method: 'POST',
            body: JSON.stringify({ voltage: newVoltage })
        });

        if (result.success) {
            currentQC3Voltage = newVoltage;
            document.getElementById('qc3-voltage').textContent = newVoltage.toFixed(2) + ' V';
            document.getElementById('trigger-status').textContent = `STATUS: QC 3.0 ${newVoltage.toFixed(2)}V ACTIVE`;
            showToastPro(`QC 3.0 adjusted to ${newVoltage.toFixed(2)}V`, 'success');
        }
    } catch (error) {
        document.getElementById('trigger-status').textContent = 'STATUS: ADJUSTMENT FAILED';
        showToastPro('QC 3.0 adjustment failed: ' + error.message, 'error');
    }
}

// Update active trigger button visual state
function updateActiveTriggerButton(protocol, voltage) {
    // Remove active class from all voltage buttons
    document.querySelectorAll('.voltage-btn, .voltage-btn-sm').forEach(btn => {
        btn.classList.remove('active');
    });

    // Add active class to clicked button
    const selector = `.voltage-btn[data-voltage="${voltage}V"], .voltage-btn-sm`;
    document.querySelectorAll(selector).forEach(btn => {
        const btnVoltage = btn.getAttribute('data-voltage') || btn.textContent.trim();
        if (btnVoltage === `${voltage}V`) {
            btn.classList.add('active');
        }
    });
}

// Update trigger view with new reading
function updateTriggerView(reading) {
    // Update current metrics
    if (document.getElementById('trigger-voltage')) {
        document.getElementById('trigger-voltage').textContent = reading.voltage.toFixed(3) + ' V';
    }
    if (document.getElementById('trigger-current')) {
        document.getElementById('trigger-current').textContent = reading.current.toFixed(3) + ' A';
    }
    if (document.getElementById('trigger-power')) {
        document.getElementById('trigger-power').textContent = reading.power.toFixed(3) + ' W';
    }

    // Update protocol detection
    if (reading.protocol) {
        const protocolName = document.getElementById('trigger-protocol-name');
        const protocolDetails = document.getElementById('trigger-protocol-details');

        if (protocolName) {
            protocolName.textContent = reading.protocol.protocol || 'UNKNOWN';

            // Color code protocol name
            const protocolColors = {
                'USB-PD': '#00d9ff',
                'QC 2.0': '#a855f7',
                'QC 3.0': '#c084fc',
                'AFC': '#ec4899',
                'FCP': '#f59e0b',
                'SCP': '#10b981',
                'VOOC': '#ef4444',
                'Standard USB': '#6b7280'
            };
            protocolName.style.color = protocolColors[reading.protocol.protocol] || '#00d9ff';
        }

        if (protocolDetails) {
            protocolDetails.textContent = reading.protocol.description || 'Unknown protocol';
        }

        activeProtocol = reading.protocol.protocol;

        // Enable/disable trigger panels based on detected protocol and connection type
        updateTriggerPanelStates(reading.protocol);
    }

    // Update sample count
    if (document.getElementById('trigger-samples')) {
        document.getElementById('trigger-samples').textContent = `SAMPLES: ${dataBuffer.length}`;
    }
}

// Enable/disable trigger panels based on protocol and connection
async function updateTriggerPanelStates(protocol) {
    // Check connection status
    const status = await apiRequest('/api/status').catch(() => ({ connected: false }));
    const isUSB = status.connection_type === 'usb';
    const isConnected = status.connected;

    // Disable all panels if not connected or not USB
    const allPanels = document.querySelectorAll('.trigger-panel, .trigger-panel-sm');
    const allButtons = document.querySelectorAll('.voltage-btn, .voltage-btn-sm, .qc3-btn');

    if (!isConnected) {
        // Disable everything
        allPanels.forEach(panel => panel.style.opacity = '0.3');
        allButtons.forEach(btn => {
            btn.disabled = true;
            btn.style.cursor = 'not-allowed';
            btn.style.opacity = '0.3';
        });
        document.getElementById('trigger-warning').textContent = 'Connect device to use triggers';
        return;
    }

    if (!isUSB) {
        // Disable everything - Bluetooth doesn't support triggering
        allPanels.forEach(panel => panel.style.opacity = '0.3');
        allButtons.forEach(btn => {
            btn.disabled = true;
            btn.style.cursor = 'not-allowed';
            btn.style.opacity = '0.3';
        });
        document.getElementById('trigger-warning').textContent = 'Triggers only work via USB connection';
        return;
    }

    // USB connected - enable panels based on detected protocol
    const detectedProtocol = protocol?.protocol || 'Unknown';

    // Map protocols to panel IDs
    const protocolPanels = {
        'USB-PD': ['pd-trigger-panel'],
        'QC 2.0': ['qc-trigger-panel'],
        'QC 3.0': ['qc-trigger-panel'],
        'AFC': ['afc-trigger-panel'],
        'FCP': ['fcp-trigger-panel'],
        'SCP': ['scp-trigger-panel'],
        'VOOC': ['vooc-trigger-panel']
    };

    // Enable all panels by default, but highlight detected protocol
    allPanels.forEach(panel => {
        panel.style.opacity = '1';
    });
    allButtons.forEach(btn => {
        btn.disabled = false;
        btn.style.cursor = 'pointer';
        btn.style.opacity = '1';
    });

    // Highlight the detected protocol panel
    const detectedPanels = protocolPanels[detectedProtocol] || [];
    detectedPanels.forEach(panelId => {
        const panel = document.getElementById(panelId);
        if (panel) {
            panel.style.border = '2px solid var(--accent-green)';
            panel.style.boxShadow = '0 0 20px rgba(0, 255, 136, 0.2)';
        }
    });

    // Clear other panels' highlights
    allPanels.forEach(panel => {
        if (!detectedPanels.includes(panel.id)) {
            panel.style.border = '1px solid var(--border-primary)';
            panel.style.boxShadow = 'none';
        }
    });

    document.getElementById('trigger-warning').textContent = detectedProtocol !== 'Unknown' ?
        `${detectedProtocol} detected - try triggering different voltages!` : '';
}

// Update handleNewReading to include trigger view
const originalHandleNewReading = handleNewReading;
handleNewReading = function(reading) {
    originalHandleNewReading(reading);

    // Update trigger view if it's active
    if (currentView === 'trigger') {
        updateTriggerView(reading);
    }
};

console.log('Professional Dashboard loaded successfully');
