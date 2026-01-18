# FNB48PReader SRP Refactoring Plan

## Overview

The `FNB48PReader` class in `fnb48p_monitor.py` currently handles **7 distinct responsibilities**, violating the Single Responsibility Principle (SRP). This plan breaks it into focused, testable components.

## Current State Analysis

### Class Size
- **~550 lines** of code (lines 65-691)
- **30+ methods** (public and private)
- **7 responsibility domains** identified

### Identified Responsibilities

| # | Domain | Methods | Lines (approx) |
|---|--------|---------|----------------|
| 1 | USB Communication | `connect()`, `start_reading()`, `_read_loop()`, `stop()` | ~100 |
| 2 | Packet Decoding | `_decode_packet()` | ~45 |
| 3 | Statistics Tracking | `_update_stats()`, `get_stats()`, `reset_stats()`, `_format_duration()`, `_empty_stats()` | ~70 |
| 4 | Alert Management | `_check_alerts()`, `get_alerts()`, `set_alerts()` | ~35 |
| 5 | Protocol Detection | `_detect_protocol()`, `get_protocol()`, `trigger_protocol()` | ~45 |
| 6 | Session Recording | `start_recording()`, `stop_recording()`, `get_recording_status()`, `export_csv()` | ~60 |
| 7 | Session Storage | `list_sessions()`, `get_session()`, `delete_session()`, `_load_settings()`, `_save_settings()` | ~60 |

### Current Dependencies
- `pathlib.Path` - file operations
- `threading` - background reading
- `collections.deque` - data buffers
- `usb.core`, `usb.util` - USB communication
- `json`, `csv` - data serialization

---

## Proposed Architecture

### New Module Structure

```
fnirsi-web-monitor/
├── fnb48p_monitor.py          # Flask app + FNB48PMonitor (facade)
├── device/
│   ├── __init__.py
│   ├── usb_device.py          # USBDevice - connection & I/O
│   ├── packet_decoder.py      # PacketDecoder - raw data parsing
│   └── protocol_detector.py   # ProtocolDetector - D+/D- analysis
├── data/
│   ├── __init__.py
│   ├── statistics.py          # StatisticsTracker - min/max/avg/energy
│   ├── alerts.py              # AlertManager - threshold monitoring
│   └── buffers.py             # DataBuffer - deque wrappers
├── storage/
│   ├── __init__.py
│   ├── session_manager.py     # SessionManager - CRUD operations
│   └── settings.py            # SettingsManager - config persistence
└── shared/
    └── utils.py               # Existing utilities
```

### Class Responsibilities

#### 1. `USBDevice` (device/usb_device.py)
**Single Responsibility**: USB connection lifecycle and raw I/O

```python
class USBDevice:
    SUPPORTED_DEVICES = [...]

    def connect(self) -> bool
    def disconnect(self) -> None
    def read_packet(self, timeout: int) -> bytes
    def write_command(self, command: bytes) -> bool
    def get_device_info(self) -> Dict[str, str]
    @property
    def is_connected(self) -> bool
```

#### 2. `PacketDecoder` (device/packet_decoder.py)
**Single Responsibility**: Parse raw USB packets into readings

```python
class PacketDecoder:
    # Constants: PACKET_*, VOLTAGE_SCALE, etc.

    def decode(self, data: bytes) -> List[Reading]
```

```python
@dataclass
class Reading:
    timestamp: datetime
    voltage: float
    current: float
    power: float
    dp: float
    dn: float
    temperature: float
```

#### 3. `ProtocolDetector` (device/protocol_detector.py)
**Single Responsibility**: Detect charging protocol from D+/D- voltages

```python
class ProtocolDetector:
    SIGNATURES = [ProtocolSignature(...), ...]
    TRIGGER_COMMANDS = {...}

    def detect(self, dp: float, dn: float) -> Optional[Protocol]
    def get_trigger_command(self, protocol: str) -> bytes
```

#### 4. `StatisticsTracker` (data/statistics.py)
**Single Responsibility**: Accumulate and compute statistics

```python
class StatisticsTracker:
    def update(self, reading: Reading, dt: float) -> None
    def get_stats(self) -> Dict[str, Any]
    def reset(self) -> None
    def get_charge_estimate(self, target_mah: Optional[int]) -> Optional[Dict]
```

#### 5. `AlertManager` (data/alerts.py)
**Single Responsibility**: Monitor thresholds and generate alerts

```python
class AlertManager:
    def check(self, reading: Reading) -> List[Alert]
    def get_config(self) -> Dict[str, Any]
    def set_config(self, config: Dict[str, Any]) -> None
    @property
    def active_alerts(self) -> List[Alert]
```

#### 6. `DataBuffer` (data/buffers.py)
**Single Responsibility**: Thread-safe ring buffers for readings

```python
class DataBuffer:
    def __init__(self, maxlen: int)
    def append(self, reading: Reading) -> None
    def get_recent(self, n: int) -> List[Reading]
    def get_latest(self) -> Optional[Reading]
```

#### 7. `SessionManager` (storage/session_manager.py)
**Single Responsibility**: Recording sessions and session storage

```python
class SessionManager:
    def __init__(self, storage_dir: Path)
    def start_recording(self, name: Optional[str]) -> str
    def stop_recording(self) -> Session
    def add_reading(self, reading: Reading) -> None
    def get_status(self) -> Dict[str, Any]
    def list_sessions(self) -> List[Dict]
    def get_session(self, name: str) -> Optional[Session]
    def delete_session(self, name: str) -> bool
    def export_csv(self, data: List[Reading]) -> str
```

#### 8. `SettingsManager` (storage/settings.py)
**Single Responsibility**: Persist and load configuration

```python
class SettingsManager:
    def __init__(self, storage_dir: Path)
    def load(self) -> Tuple[Dict, Dict]  # (settings, alerts)
    def save(self, settings: Dict, alerts: Dict) -> None
```

#### 9. `FNB48PMonitor` (fnb48p_monitor.py) - Facade
**Single Responsibility**: Coordinate all components

```python
class FNB48PMonitor:
    """Facade that coordinates all subsystems."""

    def __init__(self):
        self.device = USBDevice()
        self.decoder = PacketDecoder()
        self.protocol = ProtocolDetector()
        self.stats = StatisticsTracker()
        self.alerts = AlertManager()
        self.buffer = DataBuffer(maxlen=2000)
        self.waveform = DataBuffer(maxlen=500)
        self.sessions = SessionManager(storage_dir)
        self.settings = SettingsManager(storage_dir)

    def connect(self) -> bool
    def start_reading(self) -> bool
    def stop(self) -> None
    # Delegate methods to appropriate components
```

---

## Implementation Phases

### Phase 1: Create Data Types Module
**Goal**: Define shared data structures

- [ ] Create `device/` directory with `__init__.py`
- [ ] Create `data/` directory with `__init__.py`
- [ ] Create `storage/` directory with `__init__.py`
- [ ] Define `Reading` dataclass in `device/packet_decoder.py`
- [ ] Define `Alert` dataclass in `data/alerts.py`
- [ ] Define `Session` dataclass in `storage/session_manager.py`
- [ ] Define `Protocol` dataclass in `device/protocol_detector.py`

### Phase 2: Extract PacketDecoder
**Goal**: Isolate packet parsing logic

- [ ] Create `device/packet_decoder.py`
- [ ] Move constants: `PACKET_*`, `*_SCALE`, `READING_SIZE`, `READINGS_PER_PACKET`
- [ ] Move `_decode_packet()` method
- [ ] Add unit tests for packet decoding
- [ ] Update `FNB48PReader` to use `PacketDecoder`

### Phase 3: Extract ProtocolDetector
**Goal**: Isolate protocol detection and triggering

- [ ] Create `device/protocol_detector.py`
- [ ] Move `PROTOCOL_SIGNATURES` list
- [ ] Move `TRIGGER_COMMANDS` dict
- [ ] Move `_detect_protocol()` method
- [ ] Move `trigger_protocol()` method
- [ ] Add unit tests for protocol detection
- [ ] Update `FNB48PReader` to use `ProtocolDetector`

### Phase 4: Extract StatisticsTracker
**Goal**: Isolate statistics accumulation

- [ ] Create `data/statistics.py`
- [ ] Move `_empty_stats()` method
- [ ] Move `_update_stats()` method
- [ ] Move `get_stats()` method
- [ ] Move `reset_stats()` method
- [ ] Move `_format_duration()` method
- [ ] Move `get_charge_estimate()` method
- [ ] Add unit tests for statistics
- [ ] Update `FNB48PReader` to use `StatisticsTracker`

### Phase 5: Extract AlertManager
**Goal**: Isolate alert threshold monitoring

- [ ] Create `data/alerts.py`
- [ ] Move alert config dict
- [ ] Move `_check_alerts()` method
- [ ] Move `get_alerts()` method
- [ ] Move `set_alerts()` method
- [ ] Add unit tests for alerts
- [ ] Update `FNB48PReader` to use `AlertManager`

### Phase 6: Extract DataBuffer
**Goal**: Isolate thread-safe buffer management

- [ ] Create `data/buffers.py`
- [ ] Create `DataBuffer` class wrapping `deque`
- [ ] Add thread-safe `append()` and `get_recent()` methods
- [ ] Add unit tests for buffer operations
- [ ] Update `FNB48PReader` to use `DataBuffer`

### Phase 7: Extract SessionManager
**Goal**: Isolate recording and session storage

- [ ] Create `storage/session_manager.py`
- [ ] Move `start_recording()` method
- [ ] Move `stop_recording()` method
- [ ] Move `get_recording_status()` method
- [ ] Move `export_csv()` method
- [ ] Move `list_sessions()` method
- [ ] Move `get_session()` method
- [ ] Move `delete_session()` method
- [ ] Add unit tests for session management
- [ ] Update `FNB48PReader` to use `SessionManager`

### Phase 8: Extract SettingsManager
**Goal**: Isolate configuration persistence

- [ ] Create `storage/settings.py`
- [ ] Move `_load_settings()` method
- [ ] Move `_save_settings()` method
- [ ] Add unit tests for settings
- [ ] Update `FNB48PReader` to use `SettingsManager`

### Phase 9: Extract USBDevice
**Goal**: Isolate USB communication

- [ ] Create `device/usb_device.py`
- [ ] Move `SUPPORTED_DEVICES` list
- [ ] Move `connect()` method
- [ ] Extract raw I/O from `_read_loop()`
- [ ] Move `stop()` method
- [ ] Add unit tests (mocked USB)
- [ ] Update `FNB48PReader` to use `USBDevice`

### Phase 10: Create FNB48PMonitor Facade
**Goal**: Replace FNB48PReader with clean facade

- [ ] Rename `FNB48PReader` to `FNB48PMonitor`
- [ ] Inject all component dependencies
- [ ] Keep `_read_loop()` as coordinator
- [ ] Delegate all methods to appropriate components
- [ ] Update Flask routes to use new class name
- [ ] Run full test suite
- [ ] Update documentation

---

## Testing Strategy

### Unit Tests (per component)
- `tests/device/test_packet_decoder.py`
- `tests/device/test_protocol_detector.py`
- `tests/data/test_statistics.py`
- `tests/data/test_alerts.py`
- `tests/data/test_buffers.py`
- `tests/storage/test_session_manager.py`
- `tests/storage/test_settings.py`

### Integration Tests
- `tests/test_fnb48p_monitor.py` - facade orchestration
- `tests/test_api.py` - existing API tests (should remain green)

### Backwards Compatibility
- All existing Flask API endpoints must continue to work
- No changes to API response formats
- Existing test suite must pass throughout refactoring

---

## Risk Mitigation

### Thread Safety
- `DataBuffer` must use locks for thread-safe access
- `StatisticsTracker.update()` called from read thread
- `SessionManager.add_reading()` called from read thread

### Migration Strategy
1. Extract one component at a time
2. Run full test suite after each extraction
3. Keep old code as fallback until component proven
4. Use feature flag if needed for gradual rollout

### Rollback Plan
- Git commits per phase
- Each phase is independently revertable
- Main branch stays stable

---

## Success Criteria

- [ ] All 31 existing tests pass
- [ ] Each new component has dedicated unit tests
- [ ] `FNB48PMonitor` class < 150 lines
- [ ] Each component < 100 lines
- [ ] No circular imports
- [ ] Cyclomatic complexity < 10 per method
- [ ] Type hints on all public APIs

---

## Estimated Complexity

| Phase | Complexity | Dependencies |
|-------|------------|--------------|
| 1. Data Types | Low | None |
| 2. PacketDecoder | Low | Phase 1 |
| 3. ProtocolDetector | Low | Phase 1 |
| 4. StatisticsTracker | Medium | Phase 1 |
| 5. AlertManager | Low | Phase 1 |
| 6. DataBuffer | Low | Phase 1 |
| 7. SessionManager | Medium | Phase 1, 6 |
| 8. SettingsManager | Low | None |
| 9. USBDevice | High | Phase 2 |
| 10. Facade | Medium | All above |

**Recommended Order**: 1 → 2 → 3 → 5 → 6 → 4 → 8 → 7 → 9 → 10
