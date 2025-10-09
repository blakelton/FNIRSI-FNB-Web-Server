// FNIRSI FNB58 - Spectrum Analyzer
// FFT analysis for power quality and ripple measurement

let spectrumChart = null;
let fftSettings = {
    source: 'voltage',
    window: 'hann',
    size: 1024
};

// Initialize spectrum analyzer
function initSpectrum() {
    const ctx = document.getElementById('spectrum-chart');
    if (!ctx) {
        console.error('Spectrum chart canvas not found');
        return;
    }

    spectrumChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Magnitude (dB)',
                data: [],
                borderColor: '#00d9ff',
                backgroundColor: 'rgba(0, 217, 255, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'FREQUENCY (Hz)',
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
                    title: {
                        display: true,
                        text: 'MAGNITUDE (dB)',
                        color: '#9aa0a6',
                        font: { size: 11, weight: 'bold' }
                    },
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
                        font: { size: 11, weight: 'bold' }
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

    console.log('Spectrum analyzer initialized');
}

// Compute FFT
function computeFFT() {
    // Check if dataBuffer exists (from dashboard_pro.js)
    if (typeof dataBuffer === 'undefined' || !dataBuffer) {
        showToastPro('No data available. Connect device first.', 'warning');
        return;
    }

    if (dataBuffer.length < fftSettings.size) {
        showToastPro(`Need ${fftSettings.size} samples, have ${dataBuffer.length}. Wait ${Math.ceil((fftSettings.size - dataBuffer.length) / 10)} more seconds.`, 'warning');
        return;
    }

    showToastPro('Computing FFT...', 'info');

    // Get signal data
    const signal = getSignalData();

    if (signal.length === 0) {
        showToastPro('No signal data available', 'error');
        return;
    }

    // Apply window function
    const windowed = applyWindow(signal, fftSettings.window);

    // Compute FFT using DFT
    const spectrum = performDFT(windowed);

    // Update chart
    updateSpectrumChart(spectrum);

    // Calculate metrics
    calculateSpectrumMetrics(spectrum, signal);

    showToastPro('FFT analysis complete', 'success');
}

// Get signal data based on selected source
function getSignalData() {
    const source = fftSettings.source;
    const size = fftSettings.size;
    const data = dataBuffer.slice(-size);

    if (source === 'voltage') {
        return data.map(r => r.voltage || 0);
    } else if (source === 'current') {
        return data.map(r => r.current || 0);
    } else if (source === 'power') {
        return data.map(r => r.power || 0);
    }

    return [];
}

// Apply window function
function applyWindow(signal, windowType) {
    const N = signal.length;
    const windowed = [];

    for (let i = 0; i < N; i++) {
        let w = 1.0;

        if (windowType === 'hann') {
            w = 0.5 * (1 - Math.cos(2 * Math.PI * i / (N - 1)));
        } else if (windowType === 'hamming') {
            w = 0.54 - 0.46 * Math.cos(2 * Math.PI * i / (N - 1));
        } else if (windowType === 'blackman') {
            const a0 = 0.42;
            const a1 = 0.5;
            const a2 = 0.08;
            w = a0 - a1 * Math.cos(2 * Math.PI * i / (N - 1)) +
                a2 * Math.cos(4 * Math.PI * i / (N - 1));
        }

        windowed.push(signal[i] * w);
    }

    return windowed;
}

// Perform DFT (Discrete Fourier Transform)
// For production, consider using fft.js library for better performance
function performDFT(signal) {
    const N = signal.length;
    const spectrum = [];
    const sr = typeof sampleRate !== 'undefined' ? sampleRate : 100; // Use global sampleRate if available

    // Only compute first half (Nyquist frequency)
    const numFreqs = Math.floor(N / 2);

    for (let k = 0; k < numFreqs; k++) {
        let realSum = 0;
        let imagSum = 0;

        // Compute DFT for frequency bin k
        for (let n = 0; n < N; n++) {
            const angle = -2 * Math.PI * k * n / N;
            realSum += signal[n] * Math.cos(angle);
            imagSum += signal[n] * Math.sin(angle);
        }

        // Calculate magnitude
        const magnitude = Math.sqrt(realSum * realSum + imagSum * imagSum) / N;

        // Convert to dB (with floor to avoid log(0))
        const magnitudeDB = magnitude > 0 ? 20 * Math.log10(magnitude) : -100;

        // Calculate frequency
        const frequency = k * sr / N;

        spectrum.push({ x: frequency, y: magnitudeDB });
    }

    return spectrum;
}

// Update spectrum chart
function updateSpectrumChart(spectrum) {
    if (!spectrumChart) {
        initSpectrum();
        return;
    }

    spectrumChart.data.datasets[0].data = spectrum;
    spectrumChart.update('none');
}

// Calculate spectrum metrics
function calculateSpectrumMetrics(spectrum, signal) {
    // Find fundamental frequency (peak above DC)
    let maxMag = -Infinity;
    let fundamentalFreq = 0;
    let dcOffset = spectrum[0].y;

    // Skip DC component (index 0) and low frequencies
    for (let i = 2; i < spectrum.length; i++) {
        if (spectrum[i].y > maxMag) {
            maxMag = spectrum[i].y;
            fundamentalFreq = spectrum[i].x;
        }
    }

    // Calculate RMS of signal for ripple
    const mean = signal.reduce((sum, val) => sum + val, 0) / signal.length;
    const variance = signal.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / signal.length;
    const rms = Math.sqrt(variance);

    // Ripple voltage (AC component RMS in mV)
    const rippleVoltage = rms * 1000;

    // Calculate THD (Total Harmonic Distortion)
    // Sum of harmonics power / fundamental power
    let fundamentalPower = 0;
    let harmonicsPower = 0;

    const fundamentalIndex = Math.round(fundamentalFreq * spectrum.length / 50); // Assuming 50Hz max freq
    if (fundamentalIndex > 0 && fundamentalIndex < spectrum.length) {
        fundamentalPower = Math.pow(10, spectrum[fundamentalIndex].y / 10);

        // Sum 2nd through 5th harmonics
        for (let h = 2; h <= 5; h++) {
            const harmonicIndex = fundamentalIndex * h;
            if (harmonicIndex < spectrum.length) {
                harmonicsPower += Math.pow(10, spectrum[harmonicIndex].y / 10);
            }
        }
    }

    const thd = fundamentalPower > 0 ? Math.sqrt(harmonicsPower / fundamentalPower) * 100 : 0;

    // Calculate SNR (Signal to Noise Ratio)
    // Use DC component as signal, and estimate noise from high frequency content
    const signalPower = Math.pow(10, dcOffset / 10);
    let noisePower = 0;
    const noiseStart = Math.floor(spectrum.length * 0.8); // Last 20% is likely noise

    for (let i = noiseStart; i < spectrum.length; i++) {
        noisePower += Math.pow(10, spectrum[i].y / 10);
    }
    noisePower /= (spectrum.length - noiseStart);

    const snr = noisePower > 0 ? 10 * Math.log10(signalPower / noisePower) : 100;

    // Update display
    const fundEl = document.getElementById('fundamental-freq');
    const rippleEl = document.getElementById('ripple-voltage');
    const thdEl = document.getElementById('thd-value');
    const snrEl = document.getElementById('snr-value');

    if (fundEl) {
        if (fundamentalFreq > 0.5) {
            fundEl.textContent = fundamentalFreq.toFixed(2) + ' Hz';
        } else {
            fundEl.textContent = 'DC (0 Hz)';
        }
    }
    if (rippleEl) rippleEl.textContent = rippleVoltage.toFixed(2) + ' mV';
    if (thdEl) thdEl.textContent = thd.toFixed(2) + ' %';
    if (snrEl) snrEl.textContent = snr.toFixed(1) + ' dB';
}

// Update FFT source
function updateFFTSource() {
    const select = document.getElementById('fft-source');
    if (select) {
        fftSettings.source = select.value;
        console.log('FFT source:', fftSettings.source);
    }
}

// Update FFT size
function updateFFTSize() {
    const select = document.getElementById('fft-size');
    if (select) {
        fftSettings.size = parseInt(select.value);
        console.log('FFT size:', fftSettings.size);
    }
}

// Update window type
function updateFFTWindow() {
    const select = document.getElementById('fft-window');
    if (select) {
        fftSettings.window = select.value;
        console.log('FFT window:', fftSettings.window);
    }
}

console.log('Spectrum analyzer module loaded');
