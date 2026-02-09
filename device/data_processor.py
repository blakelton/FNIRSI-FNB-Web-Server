"""
Data Processor - Analysis and export functionality
"""

import json
import csv
import base64
from io import BytesIO
from datetime import datetime
from pathlib import Path
import numpy as np


class DataProcessor:
    """Process and export session data"""
    
    @staticmethod
    def export_to_csv(session_data, filename):
        """Export session data to CSV file"""
        if not session_data:
            raise ValueError("No data to export")
        
        # Get first item to determine keys
        keys = session_data[0].keys()
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(session_data)
        
        return filename
    
    @staticmethod
    def export_to_json(session, filename):
        """Export full session to JSON file"""
        with open(filename, 'w') as f:
            json.dump(session, f, indent=2)
        
        return filename
    
    @staticmethod
    def calculate_statistics(data):
        """Calculate detailed statistics from data"""
        if not data:
            return {}
        
        voltages = [d['voltage'] for d in data]
        currents = [d['current'] for d in data]
        powers = [d['power'] for d in data]
        
        stats = {
            'sample_count': len(data),
            'voltage': {
                'min': min(voltages),
                'max': max(voltages),
                'avg': sum(voltages) / len(voltages),
                'range': max(voltages) - min(voltages)
            },
            'current': {
                'min': min(currents),
                'max': max(currents),
                'avg': sum(currents) / len(currents),
                'range': max(currents) - min(currents)
            },
            'power': {
                'min': min(powers),
                'max': max(powers),
                'avg': sum(powers) / len(powers),
                'range': max(powers) - min(powers)
            }
        }
        
        # Calculate energy and capacity
        # Assume 100Hz sampling for USB, 10Hz for Bluetooth
        dt = 0.01  # Will need to adjust based on actual rate
        
        total_energy_ws = sum(p * dt for p in powers)
        total_capacity_as = sum(c * dt for c in currents)
        
        stats['energy_wh'] = total_energy_ws / 3600
        stats['capacity_ah'] = total_capacity_as / 3600
        stats['capacity_mah'] = (total_capacity_as / 3600) * 1000
        
        return stats
    
    @staticmethod
    def detect_charging_phases(data, current_threshold=0.1):
        """Detect different charging phases"""
        if not data:
            return []
        
        phases = []
        current_phase = None
        phase_start = 0
        
        for i, reading in enumerate(data):
            is_charging = reading['current'] > current_threshold
            
            if current_phase is None:
                current_phase = 'charging' if is_charging else 'idle'
                phase_start = i
            elif (is_charging and current_phase == 'idle') or (not is_charging and current_phase == 'charging'):
                # Phase change
                phases.append({
                    'phase': current_phase,
                    'start_index': phase_start,
                    'end_index': i - 1,
                    'duration_samples': i - phase_start
                })
                current_phase = 'charging' if is_charging else 'idle'
                phase_start = i
        
        # Add final phase
        if current_phase:
            phases.append({
                'phase': current_phase,
                'start_index': phase_start,
                'end_index': len(data) - 1,
                'duration_samples': len(data) - phase_start
            })
        
        return phases
    
    @staticmethod
    def calculate_advanced_statistics(data):
        """Calculate advanced statistics including RMS, ripple, THD, etc."""
        if not data:
            return {}

        voltages = np.array([d['voltage'] for d in data])
        currents = np.array([d['current'] for d in data])
        powers = np.array([d['power'] for d in data])

        # Basic stats
        stats = {
            'sample_count': len(data),
            'duration_seconds': len(data) / 100,  # Assuming 100Hz
            'voltage': {
                'min': float(np.min(voltages)),
                'max': float(np.max(voltages)),
                'avg': float(np.mean(voltages)),
                'rms': float(np.sqrt(np.mean(voltages**2))),
                'std': float(np.std(voltages)),
                'range': float(np.max(voltages) - np.min(voltages)),
                'ripple_pk_pk': float(np.max(voltages) - np.min(voltages)),
                'ripple_percent': float((np.max(voltages) - np.min(voltages)) / np.mean(voltages) * 100) if np.mean(voltages) > 0 else 0
            },
            'current': {
                'min': float(np.min(currents)),
                'max': float(np.max(currents)),
                'avg': float(np.mean(currents)),
                'rms': float(np.sqrt(np.mean(currents**2))),
                'std': float(np.std(currents)),
                'range': float(np.max(currents) - np.min(currents))
            },
            'power': {
                'min': float(np.min(powers)),
                'max': float(np.max(powers)),
                'avg': float(np.mean(powers)),
                'std': float(np.std(powers)),
                'range': float(np.max(powers) - np.min(powers))
            }
        }

        # Calculate energy and capacity using trapezoidal integration
        dt = 1.0 / 100.0 / 3600.0  # 100Hz to hours
        total_energy_wh = np.trapezoid(powers, dx=1/100) / 3600
        total_capacity_ah = np.trapezoid(currents, dx=1/100) / 3600

        stats['energy_wh'] = float(total_energy_wh)
        stats['capacity_ah'] = float(total_capacity_ah)
        stats['capacity_mah'] = float(total_capacity_ah * 1000)

        # Power factor (if meaningful)
        if stats['voltage']['rms'] > 0 and stats['current']['rms'] > 0:
            apparent_power = stats['voltage']['rms'] * stats['current']['rms']
            stats['power_factor'] = float(stats['power']['avg'] / apparent_power) if apparent_power > 0 else 0
        else:
            stats['power_factor'] = 0

        # Efficiency estimate (useful for charging)
        if total_energy_wh > 0:
            stats['efficiency_percent'] = 100.0  # Placeholder, needs reference

        return stats

    @staticmethod
    def generate_chart_data(data, max_points=1000):
        """Generate downsampled chart data for visualization"""
        if not data:
            return {'timestamps': [], 'voltage': [], 'current': [], 'power': []}

        # Downsample if needed
        if len(data) > max_points:
            step = len(data) // max_points
            data = data[::step]

        timestamps = list(range(len(data)))
        voltages = [d['voltage'] for d in data]
        currents = [d['current'] for d in data]
        powers = [d['power'] for d in data]

        return {
            'timestamps': timestamps,
            'voltage': voltages,
            'current': currents,
            'power': powers
        }

    @staticmethod
    def generate_html_report(session, filename):
        """Generate comprehensive HTML report with embedded charts"""
        data = session.get('data', [])
        if not data:
            raise ValueError("No data to generate report")

        # Calculate advanced statistics
        stats = DataProcessor.calculate_advanced_statistics(data)
        chart_data = DataProcessor.generate_chart_data(data)

        # Generate HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FNIRSI FNB58 - Power Analysis Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0c10 0%, #1a1e26 100%);
            color: #e8eaed;
            padding: 2rem;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(30, 34, 41, 0.8);
            backdrop-filter: blur(20px);
            border-radius: 12px;
            padding: 2rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
        }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            color: #00d9ff;
            text-align: center;
        }}
        .subtitle {{
            text-align: center;
            color: #9aa0a6;
            margin-bottom: 2rem;
        }}
        .info-section {{
            background: rgba(18, 21, 26, 0.5);
            border: 1px solid #2d3139;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
        }}
        .info-item {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid #2d3139;
        }}
        .info-label {{
            color: #9aa0a6;
            font-weight: 600;
        }}
        .info-value {{
            color: #00d9ff;
            font-weight: 700;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #1a1e26 0%, #12151a 100%);
            border: 1px solid #2d3139;
            border-radius: 8px;
            padding: 1.5rem;
        }}
        .stat-card h3 {{
            color: #00d9ff;
            margin-bottom: 1rem;
            font-size: 1.2rem;
        }}
        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid rgba(45, 49, 57, 0.5);
        }}
        .stat-row:last-child {{
            border-bottom: none;
        }}
        .stat-label {{
            color: #9aa0a6;
        }}
        .stat-value {{
            font-weight: 700;
            color: #fff;
        }}
        .voltage {{ color: #00d9ff; }}
        .current {{ color: #00ff88; }}
        .power {{ color: #ff9933; }}
        .energy {{ color: #cc66ff; }}
        .chart-container {{
            background: #0a0c10;
            border: 1px solid #2d3139;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }}
        .chart-container h3 {{
            margin-bottom: 1rem;
            color: #00d9ff;
        }}
        canvas {{
            max-height: 400px;
        }}
        .footer {{
            text-align: center;
            color: #5f6368;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #2d3139;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ FNIRSI FNB58 Power Analysis Report</h1>
        <p class="subtitle">Professional USB Power Measurement & Analysis</p>

        <div class="info-section">
            <h2 style="margin-bottom: 1rem;">Session Information</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Start Time:</span>
                    <span class="info-value">{session.get('start_time', 'N/A')}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">End Time:</span>
                    <span class="info-value">{session.get('end_time', 'N/A')}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Connection Type:</span>
                    <span class="info-value">{session.get('connection_type', 'N/A').upper()}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Total Samples:</span>
                    <span class="info-value">{stats['sample_count']:,}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Duration:</span>
                    <span class="info-value">{stats['duration_seconds']:.1f}s</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Sample Rate:</span>
                    <span class="info-value">100 Hz</span>
                </div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3 class="voltage">⚡ VOLTAGE STATISTICS</h3>
                <div class="stat-row">
                    <span class="stat-label">Minimum:</span>
                    <span class="stat-value voltage">{stats['voltage']['min']:.5f} V</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Maximum:</span>
                    <span class="stat-value voltage">{stats['voltage']['max']:.5f} V</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Average:</span>
                    <span class="stat-value voltage">{stats['voltage']['avg']:.5f} V</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">RMS:</span>
                    <span class="stat-value voltage">{stats['voltage']['rms']:.5f} V</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Std Dev:</span>
                    <span class="stat-value">{stats['voltage']['std']:.5f} V</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Ripple (pk-pk):</span>
                    <span class="stat-value">{stats['voltage']['ripple_pk_pk']:.5f} V</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Ripple %:</span>
                    <span class="stat-value">{stats['voltage']['ripple_percent']:.2f}%</span>
                </div>
            </div>

            <div class="stat-card">
                <h3 class="current">🔌 CURRENT STATISTICS</h3>
                <div class="stat-row">
                    <span class="stat-label">Minimum:</span>
                    <span class="stat-value current">{stats['current']['min']:.5f} A</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Maximum:</span>
                    <span class="stat-value current">{stats['current']['max']:.5f} A</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Average:</span>
                    <span class="stat-value current">{stats['current']['avg']:.5f} A</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">RMS:</span>
                    <span class="stat-value current">{stats['current']['rms']:.5f} A</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Std Dev:</span>
                    <span class="stat-value">{stats['current']['std']:.5f} A</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Range:</span>
                    <span class="stat-value">{stats['current']['range']:.5f} A</span>
                </div>
            </div>

            <div class="stat-card">
                <h3 class="power">⚡ POWER STATISTICS</h3>
                <div class="stat-row">
                    <span class="stat-label">Minimum:</span>
                    <span class="stat-value power">{stats['power']['min']:.5f} W</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Maximum:</span>
                    <span class="stat-value power">{stats['power']['max']:.5f} W</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Average:</span>
                    <span class="stat-value power">{stats['power']['avg']:.5f} W</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Std Dev:</span>
                    <span class="stat-value">{stats['power']['std']:.5f} W</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Range:</span>
                    <span class="stat-value">{stats['power']['range']:.5f} W</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Power Factor:</span>
                    <span class="stat-value">{stats.get('power_factor', 0):.3f}</span>
                </div>
            </div>

            <div class="stat-card">
                <h3 class="energy">🔋 ENERGY & CAPACITY</h3>
                <div class="stat-row">
                    <span class="stat-label">Total Energy:</span>
                    <span class="stat-value energy">{stats['energy_wh']:.4f} Wh</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Total Capacity:</span>
                    <span class="stat-value energy">{stats['capacity_mah']:.2f} mAh</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Capacity (Ah):</span>
                    <span class="stat-value">{stats['capacity_ah']:.4f} Ah</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Avg Power:</span>
                    <span class="stat-value">{stats['power']['avg']:.3f} W</span>
                </div>
            </div>
        </div>

        <div class="chart-container">
            <h3>📊 Voltage Over Time</h3>
            <canvas id="voltageChart"></canvas>
        </div>

        <div class="chart-container">
            <h3>📊 Current Over Time</h3>
            <canvas id="currentChart"></canvas>
        </div>

        <div class="chart-container">
            <h3>📊 Power Over Time</h3>
            <canvas id="powerChart"></canvas>
        </div>

        <div class="chart-container">
            <h3>📊 Combined View (V, I, P)</h3>
            <canvas id="combinedChart"></canvas>
        </div>

        <div class="footer">
            <p>Generated by FNIRSI FNB58 Professional Web Monitor</p>
            <p>Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>

    <script>
        const chartData = {json.dumps(chart_data)};

        const commonOptions = {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{
                    labels: {{
                        color: '#e8eaed',
                        font: {{ size: 12, weight: 'bold' }}
                    }}
                }}
            }},
            scales: {{
                x: {{
                    ticks: {{ color: '#9aa0a6' }},
                    grid: {{ color: '#2d3139' }}
                }},
                y: {{
                    ticks: {{ color: '#9aa0a6' }},
                    grid: {{ color: '#2d3139' }}
                }}
            }}
        }};

        // Voltage Chart
        new Chart(document.getElementById('voltageChart'), {{
            type: 'line',
            data: {{
                labels: chartData.timestamps,
                datasets: [{{
                    label: 'Voltage (V)',
                    data: chartData.voltage,
                    borderColor: '#00d9ff',
                    backgroundColor: 'rgba(0, 217, 255, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true
                }}]
            }},
            options: commonOptions
        }});

        // Current Chart
        new Chart(document.getElementById('currentChart'), {{
            type: 'line',
            data: {{
                labels: chartData.timestamps,
                datasets: [{{
                    label: 'Current (A)',
                    data: chartData.current,
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true
                }}]
            }},
            options: commonOptions
        }});

        // Power Chart
        new Chart(document.getElementById('powerChart'), {{
            type: 'line',
            data: {{
                labels: chartData.timestamps,
                datasets: [{{
                    label: 'Power (W)',
                    data: chartData.power,
                    borderColor: '#ff9933',
                    backgroundColor: 'rgba(255, 153, 51, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true
                }}]
            }},
            options: commonOptions
        }});

        // Combined Chart
        new Chart(document.getElementById('combinedChart'), {{
            type: 'line',
            data: {{
                labels: chartData.timestamps,
                datasets: [
                    {{
                        label: 'Voltage (V)',
                        data: chartData.voltage,
                        borderColor: '#00d9ff',
                        borderWidth: 2,
                        pointRadius: 0,
                        yAxisID: 'y'
                    }},
                    {{
                        label: 'Current (A)',
                        data: chartData.current,
                        borderColor: '#00ff88',
                        borderWidth: 2,
                        pointRadius: 0,
                        yAxisID: 'y1'
                    }},
                    {{
                        label: 'Power (W)',
                        data: chartData.power,
                        borderColor: '#ff9933',
                        borderWidth: 2,
                        pointRadius: 0,
                        yAxisID: 'y2'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        labels: {{
                            color: '#e8eaed',
                            font: {{ size: 12, weight: 'bold' }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#9aa0a6' }},
                        grid: {{ color: '#2d3139' }}
                    }},
                    y: {{
                        type: 'linear',
                        position: 'left',
                        ticks: {{ color: '#00d9ff' }},
                        grid: {{ color: '#2d3139' }}
                    }},
                    y1: {{
                        type: 'linear',
                        position: 'right',
                        ticks: {{ color: '#00ff88' }},
                        grid: {{ display: false }}
                    }},
                    y2: {{
                        type: 'linear',
                        position: 'right',
                        ticks: {{ color: '#ff9933' }},
                        grid: {{ display: false }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

        return filename

    @staticmethod
    def generate_report(session):
        """Generate a text report from session data"""
        report = []
        report.append("=" * 60)
        report.append("FNIRSI FNB58 - Session Report")
        report.append("=" * 60)
        report.append("")

        # Session info
        report.append(f"Start Time: {session.get('start_time', 'N/A')}")
        report.append(f"End Time: {session.get('end_time', 'N/A')}")
        report.append(f"Connection: {session.get('connection_type', 'N/A').upper()}")
        report.append("")

        # Statistics
        stats = session.get('stats', {})
        report.append("Statistics:")
        report.append(f"  Samples Collected: {stats.get('samples_collected', 0)}")
        report.append("")

        report.append("Voltage:")
        report.append(f"  Min: {stats.get('min_voltage', 0):.5f} V")
        report.append(f"  Max: {stats.get('max_voltage', 0):.5f} V")
        report.append(f"  Avg: {stats.get('avg_voltage', 0):.5f} V")
        report.append("")

        report.append("Current:")
        report.append(f"  Min: {stats.get('min_current', 0):.5f} A")
        report.append(f"  Max: {stats.get('max_current', 0):.5f} A")
        report.append(f"  Avg: {stats.get('avg_current', 0):.5f} A")
        report.append("")

        report.append("Power:")
        report.append(f"  Max: {stats.get('max_power', 0):.5f} W")
        report.append(f"  Avg: {stats.get('avg_power', 0):.5f} W")
        report.append("")

        report.append("Energy & Capacity:")
        report.append(f"  Total Energy: {stats.get('total_energy_wh', 0):.4f} Wh")
        report.append(f"  Total Capacity: {stats.get('total_capacity_ah', 0):.4f} Ah ({stats.get('total_capacity_ah', 0) * 1000:.2f} mAh)")
        report.append("")

        report.append("=" * 60)

        return "\n".join(report)
