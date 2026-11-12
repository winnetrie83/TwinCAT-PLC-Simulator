"""TwinCAT ADS access and offline imitation of the included example ST code.

Python NEVER writes motor or diverter in live mode. Only external inputs are
writable; outputs are entirely owned by the student's TwinCAT application.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


INPUT_KEYS = ('start', 'stop', 'sensor_entry', 'sensor_exit', 'reject_type')
OUTPUT_KEYS = ('motor', 'diverter', 'counter')
DEFAULT_SYMBOLS = {
    'start': 'MAIN.bStartButton',
    'stop': 'MAIN.bStopButton',
    'sensor_entry': 'MAIN.bSensorEntry',
    'sensor_exit': 'MAIN.bSensorExit',
    'reject_type': 'MAIN.bRejectType',
    'motor': 'MAIN.bConveyorMotor',
    'diverter': 'MAIN.bDiverter',
    'counter': 'MAIN.nCycleCounter',
}


class PlcError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    ams_net_id: str
    ads_port: int
    pulse_ms: int
    symbols: dict[str, str]

    def symbol(self, key: str) -> str:
        return self.symbols[key]


class Controller(Protocol):
    def connect(self) -> None: ...
    def exchange(self, inputs: dict[str, bool]) -> dict: ...
    def disconnect(self) -> None: ...


class DemoController:
    """Illustrative controller matching twincat/MAIN_implementation.st.

    Not a PLC interpreter; actual student logic is only executed in TwinCAT.
    """
    def __init__(self):
        self.connected = False
        self.motor = False
        self.diverter = False
        self.counter = 0

    def connect(self) -> None:
        self.connected = True
        self.motor = False
        self.diverter = False
        self.counter = 0

    def disconnect(self) -> None:
        self.connected = False

    def exchange(self, inputs: dict[str, bool]) -> dict:
        if not self.connected:
            raise PlcError('Democontroller is niet verbonden.')
        # Simulated cyclic behavior of the example program, not actual ADS.
        if inputs['stop']:
            self.motor = False
        elif inputs['start']:
            self.motor = True
        if inputs['sensor_entry']:
            self.diverter = bool(inputs['reject_type'])
        if inputs['sensor_exit']:
            self.diverter = False
        self.counter = (self.counter + 5) % (2**32)
        return {'motor': self.motor, 'diverter': self.diverter, 'counter': self.counter}


class AdsController:
    """Synchronous pyads adapter, accessed by one background I/O thread."""
    def __init__(self, settings: Settings):
        self.settings = settings
        self.connection = None
        self.pyads = None
        self._last_inputs: dict[str, bool] = {}

    def connect(self) -> None:
        try:
            import pyads
        except (ImportError, OSError) as exc:
            raise PlcError('pyads/TwinCAT ADS-bibliotheek ontbreekt; controleer de installatie.') from exc
        self.pyads = pyads
        try:
            self.connection = pyads.Connection(self.settings.ams_net_id, self.settings.ads_port)
            self.connection.open()
            # Force symbol/type lookup for every input and output, before announcing success.
            for key in INPUT_KEYS:
                self.connection.read_by_name(self.settings.symbol(key), pyads.PLCTYPE_BOOL)
            self._read_outputs()
            self._last_inputs = {}  # first exchange writes all sensor/button states
        except Exception as exc:
            self.disconnect()
            raise PlcError(f'ADS-verbinding of PLC-symbolen niet geldig: {exc}') from exc

    def _read_outputs(self) -> dict:
        c = self.connection
        p = self.pyads
        return {
            'motor': bool(c.read_by_name(self.settings.symbol('motor'), p.PLCTYPE_BOOL)),
            'diverter': bool(c.read_by_name(self.settings.symbol('diverter'), p.PLCTYPE_BOOL)),
            'counter': int(c.read_by_name(self.settings.symbol('counter'), p.PLCTYPE_UDINT)),
        }

    def exchange(self, inputs: dict[str, bool]) -> dict:
        if self.connection is None:
            raise PlcError('Geen actieve ADS-verbinding.')
        try:
            for key in INPUT_KEYS:
                value = bool(inputs[key])
                if self._last_inputs.get(key) != value:
                    self.connection.write_by_name(self.settings.symbol(key), value, self.pyads.PLCTYPE_BOOL)
                    self._last_inputs[key] = value
            return self._read_outputs()
        except Exception as exc:
            raise PlcError(f'ADS I/O-fout (PLC-symbolen of runtime controleren): {exc}') from exc

    def disconnect(self) -> None:
        conn = self.connection
        self.connection = None
        self._last_inputs = {}
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
