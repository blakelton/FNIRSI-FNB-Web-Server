"""
Protocol Detection for USB Power Delivery
Detects QC 2.0, QC 3.0, PD, AFC, and other fast charging protocols
"""

class ProtocolDetector:
    """Detect charging protocols based on voltage/current patterns"""

    def __init__(self):
        self.current_protocol = 'Standard'
        self.voltage_history = []
        self.dp_history = []
        self.dn_history = []
        self.max_history_size = 10

    def detect_protocol(self, reading):
        """
        Detect charging protocol based on voltage and D+/D- levels

        Args:
            reading: Dictionary with voltage, dp, dn values

        Returns:
            Dictionary with protocol info
        """
        voltage = reading.get('voltage', 0)
        dp = reading.get('dp', 0)
        dn = reading.get('dn', 0)

        # Update history
        self.voltage_history.append(voltage)
        self.dp_history.append(dp)
        self.dn_history.append(dn)

        # Keep history limited
        if len(self.voltage_history) > self.max_history_size:
            self.voltage_history.pop(0)
            self.dp_history.pop(0)
            self.dn_history.pop(0)

        # Detect protocol
        protocol_info = self._analyze_protocol(voltage, dp, dn)
        self.current_protocol = protocol_info['protocol']

        return protocol_info

    def _analyze_protocol(self, voltage, dp, dn):
        """Analyze current readings to determine protocol"""

        # USB Power Delivery (PD) - typically 9V, 12V, 15V, 20V
        if voltage >= 8.5 and voltage <= 20.5:
            if 8.5 <= voltage <= 9.5:
                return {
                    'protocol': 'USB-PD',
                    'mode': '9V',
                    'version': '2.0/3.0',
                    'description': 'USB Power Delivery 9V'
                }
            elif 11.5 <= voltage <= 12.5:
                return {
                    'protocol': 'USB-PD',
                    'mode': '12V',
                    'version': '2.0/3.0',
                    'description': 'USB Power Delivery 12V'
                }
            elif 14.5 <= voltage <= 15.5:
                return {
                    'protocol': 'USB-PD',
                    'mode': '15V',
                    'version': '2.0/3.0',
                    'description': 'USB Power Delivery 15V'
                }
            elif 19.5 <= voltage <= 20.5:
                return {
                    'protocol': 'USB-PD',
                    'mode': '20V',
                    'version': '3.0',
                    'description': 'USB Power Delivery 20V'
                }

        # Quick Charge detection based on D+/D- voltages
        if dp > 0 or dn > 0:
            # QC 2.0 Class A (5V)
            if 0.25 <= dp <= 0.35 and 0.25 <= dn <= 0.35:
                return {
                    'protocol': 'QC 2.0',
                    'mode': '5V',
                    'version': '2.0',
                    'description': 'Qualcomm Quick Charge 2.0 (5V)'
                }

            # QC 2.0 Class B (9V)
            elif 0.55 <= dp <= 0.65 and 0.25 <= dn <= 0.35:
                return {
                    'protocol': 'QC 2.0',
                    'mode': '9V',
                    'version': '2.0',
                    'description': 'Qualcomm Quick Charge 2.0 (9V)'
                }

            # QC 2.0 Class A (12V)
            elif 0.55 <= dp <= 0.65 and 0.55 <= dn <= 0.65:
                return {
                    'protocol': 'QC 2.0',
                    'mode': '12V',
                    'version': '2.0',
                    'description': 'Qualcomm Quick Charge 2.0 (12V)'
                }

            # QC 3.0 (variable voltage 3.6V - 12V)
            elif dp > 0.3 or dn > 0.3:
                if 3.6 <= voltage <= 12.0:
                    return {
                        'protocol': 'QC 3.0',
                        'mode': f'{voltage:.1f}V',
                        'version': '3.0',
                        'description': f'Qualcomm Quick Charge 3.0 ({voltage:.1f}V)'
                    }

            # Samsung AFC (Adaptive Fast Charging)
            # AFC uses D+/D- communication, typically 9V
            if 8.5 <= voltage <= 9.5 and (dp > 0.4 or dn > 0.4):
                return {
                    'protocol': 'AFC',
                    'mode': '9V',
                    'version': '1.0',
                    'description': 'Samsung Adaptive Fast Charging'
                }

        # Apple 2.4A detection (D+ and D- shorted to ~2.7V each)
        if 2.5 <= dp <= 2.9 and 2.5 <= dn <= 2.9:
            return {
                'protocol': 'Apple 2.4A',
                'mode': '5V/2.4A',
                'version': '1.0',
                'description': 'Apple 2.4A Charging'
            }

        # DCP (Dedicated Charging Port) - D+ and D- shorted
        if abs(dp - dn) < 0.1 and 1.8 <= dp <= 2.2:
            return {
                'protocol': 'DCP',
                'mode': '5V',
                'version': '1.2',
                'description': 'USB Battery Charging 1.2 DCP'
            }

        # Standard USB (5V)
        if 4.5 <= voltage <= 5.5:
            return {
                'protocol': 'Standard USB',
                'mode': '5V',
                'version': '2.0/3.0',
                'description': 'Standard USB 5V'
            }

        # Unknown/Other
        return {
            'protocol': 'Unknown',
            'mode': f'{voltage:.1f}V',
            'version': 'N/A',
            'description': f'Unknown Protocol ({voltage:.1f}V)'
        }

    def get_protocol_color(self):
        """Get color code for current protocol"""
        protocol_colors = {
            'USB-PD': '#3b82f6',      # Blue
            'QC 2.0': '#8b5cf6',      # Purple
            'QC 3.0': '#a855f7',      # Light Purple
            'AFC': '#ec4899',          # Pink
            'Apple 2.4A': '#10b981',  # Green
            'DCP': '#f59e0b',          # Amber
            'Standard USB': '#6b7280', # Gray
            'Unknown': '#ef4444'       # Red
        }
        return protocol_colors.get(self.current_protocol, '#6b7280')
