"""Tests for device/protocol_detector.py"""

from device.protocol_detector import ProtocolDetector


class TestProtocolDetectorInit:
    def test_initial_state(self):
        pd = ProtocolDetector()
        assert pd.current_protocol == 'Standard'
        assert pd.voltage_history == []
        assert pd.dp_history == []
        assert pd.dn_history == []
        assert pd.max_history_size == 10


class TestDetectProtocol:
    def test_detect_usb_pd_9v(self):
        pd = ProtocolDetector()
        result = pd.detect_protocol({'voltage': 9.0, 'dp': 0, 'dn': 0})
        assert result['protocol'] == 'USB-PD'
        assert result['mode'] == '9V'

    def test_detect_usb_pd_12v(self):
        pd = ProtocolDetector()
        result = pd.detect_protocol({'voltage': 12.0, 'dp': 0, 'dn': 0})
        assert result['protocol'] == 'USB-PD'
        assert result['mode'] == '12V'

    def test_detect_usb_pd_15v(self):
        pd = ProtocolDetector()
        result = pd.detect_protocol({'voltage': 15.0, 'dp': 0, 'dn': 0})
        assert result['protocol'] == 'USB-PD'
        assert result['mode'] == '15V'

    def test_detect_usb_pd_20v(self):
        pd = ProtocolDetector()
        result = pd.detect_protocol({'voltage': 20.0, 'dp': 0, 'dn': 0})
        assert result['protocol'] == 'USB-PD'
        assert result['mode'] == '20V'

    def test_detect_qc2_5v(self):
        pd = ProtocolDetector()
        result = pd.detect_protocol({'voltage': 5.0, 'dp': 0.30, 'dn': 0.30})
        assert result['protocol'] == 'QC 2.0'
        assert result['mode'] == '5V'

    def test_detect_qc2_9v(self):
        pd = ProtocolDetector()
        result = pd.detect_protocol({'voltage': 5.0, 'dp': 0.60, 'dn': 0.30})
        assert result['protocol'] == 'QC 2.0'
        assert result['mode'] == '9V'

    def test_detect_qc2_12v(self):
        pd = ProtocolDetector()
        result = pd.detect_protocol({'voltage': 5.0, 'dp': 0.60, 'dn': 0.60})
        assert result['protocol'] == 'QC 2.0'
        assert result['mode'] == '12V'

    def test_detect_qc3_variable_voltage(self):
        pd = ProtocolDetector()
        result = pd.detect_protocol({'voltage': 7.5, 'dp': 0.5, 'dn': 0.0})
        assert result['protocol'] == 'QC 3.0'
        assert '7.5' in result['mode']

    def test_detect_apple_2_4a(self):
        pd = ProtocolDetector()
        # Voltage must be outside QC 3.0 range (3.6-12.0V) to reach Apple check
        result = pd.detect_protocol({'voltage': 2.0, 'dp': 2.7, 'dn': 2.7})
        assert result['protocol'] == 'Apple 2.4A'

    def test_detect_dcp(self):
        pd = ProtocolDetector()
        # Voltage must be outside QC 3.0 range (3.6-12.0V) to reach DCP check
        result = pd.detect_protocol({'voltage': 2.0, 'dp': 2.0, 'dn': 2.0})
        assert result['protocol'] == 'DCP'

    def test_detect_standard_usb(self):
        pd = ProtocolDetector()
        result = pd.detect_protocol({'voltage': 5.0, 'dp': 0.0, 'dn': 0.0})
        assert result['protocol'] == 'Standard USB'

    def test_detect_unknown(self):
        pd = ProtocolDetector()
        result = pd.detect_protocol({'voltage': 3.0, 'dp': 0.0, 'dn': 0.0})
        assert result['protocol'] == 'Unknown'

    def test_detect_afc_unreachable_at_9v(self):
        pd = ProtocolDetector()
        # AFC requires 8.5-9.5V with dp/dn > 0.4, but USB-PD catches 9V first
        result = pd.detect_protocol({'voltage': 9.0, 'dp': 0.5, 'dn': 0.5})
        assert result['protocol'] == 'USB-PD'  # USB-PD takes precedence

    def test_result_has_all_keys(self):
        pd = ProtocolDetector()
        result = pd.detect_protocol({'voltage': 5.0, 'dp': 0, 'dn': 0})
        assert 'protocol' in result
        assert 'mode' in result
        assert 'version' in result
        assert 'description' in result


class TestHistoryTracking:
    def test_history_maintained(self):
        pd = ProtocolDetector()
        for i in range(15):
            pd.detect_protocol({'voltage': 5.0 + i * 0.1, 'dp': 0, 'dn': 0})
        assert len(pd.voltage_history) == 10
        assert len(pd.dp_history) == 10
        assert len(pd.dn_history) == 10

    def test_current_protocol_updated(self):
        pd = ProtocolDetector()
        pd.detect_protocol({'voltage': 5.0, 'dp': 0, 'dn': 0})
        assert pd.current_protocol == 'Standard USB'
        pd.detect_protocol({'voltage': 20.0, 'dp': 0, 'dn': 0})
        assert pd.current_protocol == 'USB-PD'

    def test_missing_keys_default_to_zero(self):
        pd = ProtocolDetector()
        result = pd.detect_protocol({})
        assert result['protocol'] == 'Unknown'


class TestGetProtocolColor:
    def test_known_protocols_return_hex(self):
        pd = ProtocolDetector()
        known_protocols = ['USB-PD', 'QC 2.0', 'QC 3.0', 'AFC',
                           'Apple 2.4A', 'DCP', 'Standard USB', 'Unknown']
        for proto in known_protocols:
            pd.current_protocol = proto
            color = pd.get_protocol_color()
            assert color.startswith('#')
            assert len(color) == 7

    def test_unknown_protocol_fallback(self):
        pd = ProtocolDetector()
        pd.current_protocol = 'SomeRandomProtocol'
        color = pd.get_protocol_color()
        assert color == '#6b7280'  # gray fallback
