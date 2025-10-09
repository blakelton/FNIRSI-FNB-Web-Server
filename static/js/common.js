// Common JavaScript utilities for FNIRSI Web Monitor

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    
    const colors = {
        success: 'bg-green-600',
        error: 'bg-red-600',
        warning: 'bg-yellow-600',
        info: 'bg-blue-600'
    };
    
    toast.className = `${colors[type]} text-white px-6 py-4 rounded-lg shadow-lg transform transition-all duration-300 opacity-0`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // Fade in
    setTimeout(() => {
        toast.classList.remove('opacity-0');
    }, 10);
    
    // Fade out and remove
    setTimeout(() => {
        toast.classList.add('opacity-0');
        setTimeout(() => container.removeChild(toast), 300);
    }, 3000);
}

// Update connection status indicator
function updateConnectionStatus(connected, type = null) {
    const statusEl = document.getElementById('connection-status');
    const dot = statusEl.querySelector('.pulse-dot');
    const text = statusEl.querySelector('span:last-child');
    
    if (connected) {
        dot.classList.remove('bg-gray-500');
        dot.classList.add('bg-green-500');
        text.textContent = type ? `Connected (${type.toUpperCase()})` : 'Connected';
        text.classList.remove('text-gray-400');
        text.classList.add('text-green-400');
    } else {
        dot.classList.remove('bg-green-500');
        dot.classList.add('bg-gray-500');
        text.textContent = 'Disconnected';
        text.classList.remove('text-green-400');
        text.classList.add('text-gray-400');
    }
}

// Format number with fixed decimals
function formatNumber(value, decimals = 5) {
    return Number(value).toFixed(decimals);
}

// Format duration from seconds
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// API request helper
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Download data as file
function downloadFile(data, filename, type = 'text/plain') {
    const blob = new Blob([data], { type });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Export data to CSV
function exportDataToCSV(data) {
    if (!data || data.length === 0) {
        showToast('No data to export', 'warning');
        return;
    }
    
    // Get headers from first object
    const headers = Object.keys(data[0]);
    
    // Create CSV content
    let csv = headers.join(',') + '\n';
    
    data.forEach(row => {
        const values = headers.map(header => {
            const value = row[header];
            // Escape commas and quotes
            return typeof value === 'string' && value.includes(',') 
                ? `"${value.replace(/"/g, '""')}"` 
                : value;
        });
        csv += values.join(',') + '\n';
    });
    
    // Download
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    downloadFile(csv, `fnirsi_export_${timestamp}.csv`, 'text/csv');
    showToast('Data exported successfully', 'success');
}

// Check connection status on page load
async function checkConnectionStatus() {
    try {
        const status = await apiRequest('/api/status');
        if (status.connected) {
            updateConnectionStatus(true, status.connection_type);
            return status;
        }
    } catch (error) {
        console.error('Failed to check connection status:', error);
    }
    return { connected: false };
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkConnectionStatus();
});
