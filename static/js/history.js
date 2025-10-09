// History Page JavaScript - Session Management

let sessionChart = null;
let currentSessionData = null;
let currentSessionFilename = null;

// Load all sessions
async function loadSessions() {
    try {
        const container = document.getElementById('sessions-container');
        container.innerHTML = '<div class="text-center text-gray-400 py-12"><p class="text-lg">Loading sessions...</p></div>';

        const result = await apiRequest('/api/sessions');

        if (result.success && result.sessions.length > 0) {
            displaySessionsList(result.sessions);
        } else {
            container.innerHTML = `
                <div class="text-center text-gray-400 py-12">
                    <p class="text-lg mb-2">📁 No sessions recorded yet</p>
                    <p class="text-sm">Start recording on the Dashboard to create sessions</p>
                </div>
            `;
        }
    } catch (error) {
        showToast('Failed to load sessions: ' + error.message, 'error');
    }
}

// Display sessions list
function displaySessionsList(sessions) {
    const container = document.getElementById('sessions-container');
    container.innerHTML = '';

    sessions.forEach(session => {
        const card = createSessionCard(session);
        container.appendChild(card);
    });
}

// Create session card
function createSessionCard(session) {
    const card = document.createElement('div');
    card.className = 'glass rounded-lg p-6 hover:border-blue-500/50 border border-transparent transition cursor-pointer';

    const startDate = new Date(session.start_time);
    const endDate = new Date(session.end_time);
    const duration = Math.round((endDate - startDate) / 1000);

    const displayName = session.name || 'Untitled Session';

    card.innerHTML = `
        <div class="flex items-start justify-between">
            <div class="flex-1">
                <h3 class="text-xl font-bold mb-2">${displayName}</h3>
                <p class="text-sm text-gray-400 mb-3">${formatDate(startDate)} at ${formatTime(startDate)}</p>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                        <span class="text-gray-400">Duration:</span>
                        <span class="font-semibold ml-1">${formatDuration(duration)}</span>
                    </div>
                    <div>
                        <span class="text-gray-400">Samples:</span>
                        <span class="font-semibold ml-1">${session.samples.toLocaleString()}</span>
                    </div>
                    <div>
                        <span class="text-gray-400">Connection:</span>
                        <span class="font-semibold ml-1 uppercase">${session.connection_type || 'Unknown'}</span>
                    </div>
                    <div>
                        <span class="text-gray-400">Filename:</span>
                        <span class="font-semibold ml-1 text-xs">${session.filename}</span>
                    </div>
                </div>
            </div>
            <div class="flex gap-2 ml-4">
                <button onclick="viewSession('${session.filename}'); event.stopPropagation();"
                        class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition">
                    📊 View
                </button>
                <button onclick="deleteSession('${session.filename}'); event.stopPropagation();"
                        class="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg transition">
                    🗑️
                </button>
            </div>
        </div>
    `;

    card.onclick = () => viewSession(session.filename);

    return card;
}

// View session details
async function viewSession(filename) {
    try {
        const result = await apiRequest(`/api/sessions/${filename}`);

        if (result.success) {
            currentSessionData = result.session;
            currentSessionFilename = filename;
            displaySessionModal(result.session);
        }
    } catch (error) {
        showToast('Failed to load session: ' + error.message, 'error');
    }
}

// Display session modal
function displaySessionModal(session) {
    const modal = document.getElementById('session-modal');
    modal.classList.remove('hidden');

    // Update title
    const startDate = new Date(session.start_time);
    document.getElementById('modal-title').textContent = `Session - ${formatDate(startDate)} ${formatTime(startDate)}`;

    // Update stats
    const endDate = new Date(session.end_time);
    const duration = Math.round((endDate - startDate) / 1000);

    document.getElementById('session-duration').textContent = formatDuration(duration);
    document.getElementById('session-samples').textContent = session.data.length.toLocaleString();
    document.getElementById('session-energy').textContent = formatNumber(session.stats.total_energy_wh || 0, 4) + ' Wh';
    document.getElementById('session-capacity').textContent = formatNumber(session.stats.total_capacity_ah || 0, 4) + ' Ah';

    // Update detailed stats
    document.getElementById('stat-v-min').textContent = formatNumber(session.stats.min_voltage, 3);
    document.getElementById('stat-v-max').textContent = formatNumber(session.stats.max_voltage, 3);
    document.getElementById('stat-v-avg').textContent = formatNumber(session.stats.avg_voltage, 3);
    document.getElementById('stat-c-min').textContent = formatNumber(session.stats.min_current, 3);
    document.getElementById('stat-c-max').textContent = formatNumber(session.stats.max_current, 3);
    document.getElementById('stat-c-avg').textContent = formatNumber(session.stats.avg_current, 3);
    document.getElementById('stat-p-max').textContent = formatNumber(session.stats.max_power, 3);
    document.getElementById('stat-p-avg').textContent = formatNumber(session.stats.avg_power, 3);

    // Create chart
    createSessionChart(session.data);
}

// Create session chart
function createSessionChart(data) {
    const canvas = document.getElementById('session-chart');
    const ctx = canvas.getContext('2d');

    // Destroy existing chart
    if (sessionChart) {
        sessionChart.destroy();
    }

    // Prepare data
    const voltageData = [];
    const currentData = [];
    const powerData = [];

    data.forEach((reading, index) => {
        voltageData.push({ x: index, y: reading.voltage });
        currentData.push({ x: index, y: reading.current });
        powerData.push({ x: index, y: reading.power });
    });

    // Create gradient fills
    const voltageGradient = ctx.createLinearGradient(0, 0, 0, 300);
    voltageGradient.addColorStop(0, 'rgba(234, 179, 8, 0.3)');
    voltageGradient.addColorStop(1, 'rgba(234, 179, 8, 0.01)');

    const currentGradient = ctx.createLinearGradient(0, 0, 0, 300);
    currentGradient.addColorStop(0, 'rgba(168, 85, 247, 0.3)');
    currentGradient.addColorStop(1, 'rgba(168, 85, 247, 0.01)');

    const powerGradient = ctx.createLinearGradient(0, 0, 0, 300);
    powerGradient.addColorStop(0, 'rgba(239, 68, 68, 0.3)');
    powerGradient.addColorStop(1, 'rgba(239, 68, 68, 0.01)');

    sessionChart = new Chart(canvas, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: 'Voltage (V)',
                    data: voltageData,
                    borderColor: '#eab308',
                    backgroundColor: voltageGradient,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.2,
                    fill: true,
                    yAxisID: 'y'
                },
                {
                    label: 'Current (A)',
                    data: currentData,
                    borderColor: '#a855f7',
                    backgroundColor: currentGradient,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.2,
                    fill: true,
                    yAxisID: 'y1'
                },
                {
                    label: 'Power (W)',
                    data: powerData,
                    borderColor: '#ef4444',
                    backgroundColor: powerGradient,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.2,
                    fill: true,
                    yAxisID: 'y2'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#cbd5e1',
                        font: { size: 12, weight: 'bold' },
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
                    padding: 12
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    display: true,
                    ticks: { color: '#64748b', font: { size: 10 } },
                    grid: { color: 'rgba(100, 116, 139, 0.15)', drawBorder: false }
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    ticks: { color: '#eab308', font: { size: 11, weight: 'bold' } },
                    grid: { color: 'rgba(234, 179, 8, 0.1)', drawBorder: false }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    ticks: { color: '#a855f7', font: { size: 11, weight: 'bold' } },
                    grid: { drawOnChartArea: false }
                },
                y2: {
                    type: 'linear',
                    position: 'right',
                    ticks: { color: '#ef4444', font: { size: 11, weight: 'bold' } },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });
}

// Close session modal
function closeSessionModal() {
    const modal = document.getElementById('session-modal');
    modal.classList.add('hidden');
    currentSessionData = null;
    currentSessionFilename = null;
}

// Delete session
async function deleteSession(filename) {
    if (!confirm(`Are you sure you want to delete this session?\n\nFilename: ${filename}\n\nThis action cannot be undone.`)) {
        return;
    }

    try {
        const result = await apiRequest(`/api/sessions/${filename}`, {
            method: 'DELETE'
        });

        if (result.success) {
            showToast('Session deleted successfully', 'success');
            loadSessions(); // Reload list
        } else {
            showToast('Failed to delete session: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Failed to delete session: ' + error.message, 'error');
    }
}

// Delete current session (from modal)
async function deleteCurrentSession() {
    if (!currentSessionFilename) return;

    if (!confirm(`Are you sure you want to delete this session?\n\nThis action cannot be undone.`)) {
        return;
    }

    try {
        const result = await apiRequest(`/api/sessions/${currentSessionFilename}`, {
            method: 'DELETE'
        });

        if (result.success) {
            showToast('Session deleted successfully', 'success');
            closeSessionModal();
            loadSessions(); // Reload list
        } else {
            showToast('Failed to delete session: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('Failed to delete session: ' + error.message, 'error');
    }
}

// Export session as CSV
async function exportSessionCSV() {
    if (!currentSessionData) return;

    try {
        const result = await apiRequest('/api/export/csv', {
            method: 'POST',
            body: JSON.stringify({ data: currentSessionData.data })
        });

        // The API returns a file download, so we need to handle it differently
        showToast('CSV export started...', 'info');
    } catch (error) {
        showToast('Failed to export CSV: ' + error.message, 'error');
    }
}

// Export session as HTML report
async function exportSessionHTML() {
    if (!currentSessionData) return;

    try {
        showToast('Generating HTML report...', 'info');

        const response = await fetch('/api/export/html', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start_time: currentSessionData.start_time,
                end_time: currentSessionData.end_time,
                connection_type: currentSessionData.connection_type,
                data: currentSessionData.data
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentSessionFilename.replace('.json', '')}_report.html`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast('HTML report downloaded successfully', 'success');
        } else {
            showToast('Failed to generate HTML report', 'error');
        }
    } catch (error) {
        showToast('Failed to export HTML: ' + error.message, 'error');
    }
}

// Export session as JSON
function exportSessionJSON() {
    if (!currentSessionData) return;

    const dataStr = JSON.stringify(currentSessionData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentSessionFilename || 'session'}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast('Session exported as JSON', 'success');
}

// Format date
function formatDate(date) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
}

// Format time
function formatTime(date) {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadSessions();

    // Close modal on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeSessionModal();
        }
    });

    // Close modal on background click
    document.getElementById('session-modal')?.addEventListener('click', (e) => {
        if (e.target.id === 'session-modal') {
            closeSessionModal();
        }
    });
});
