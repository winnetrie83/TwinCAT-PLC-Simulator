"""TwinCAT ADS adapter and offline demo controller.

Only simulator inputs are written through ADS. PLC outputs always belong to
TwinCAT, including the diverter and conveyor motor.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from .symbols import discover, is_missing_symbol

INPUT_KEYS = ('start', 'stop', 'sensor_entry', 'sensor_exit', 'reject_type', 'sensor_reject')
OUTPUT_KEYS = ('motor', 'diverter', 'counter')
DEFAULT_SYMBOLS = {
    'start': 'MAIN.bStartButton', 'stop': 'MAIN.bStopButton',
    'sensor_entry': 'MAIN.bSensorEntry', 'sensor_exit': 'MAIN.bSensorExit',
    'reject_type': 'MAIN.bRejectType', 'sensor_reject': 'MAIN.bSensorReject',
    'motor': 'MAIN.bConveyorMotor', 'diverter': 'MAIN.bDiverter',
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
    """Demo of the teacher example, not a PLC code interpreter."""
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
    """Synchronous pyads adapter used on a worker thread."""
    def __init__(self, settings: Settings):
        self.settings = settings
        self.connection = None
        self.pyads = None
        self._last_inputs: dict[str, bool] = {}
        self.available: dict[str, bool] = {}
        self.extra_symbols: list[str] = []
        self.inventory_status = "unavailable"
    def connect(self) -> None:
        try:
            import pyads
        except (ImportError, OSError) as exc:
            raise PlcError('pyads/TwinCAT ADS-bibliotheek ontbreekt; controleer de installatie.') from exc
        self.pyads = pyads
        try:
            self.connection = pyads.Connection(self.settings.ams_net_id, self.settings.ads_port)
            self.connection.open()
            self.available, self.extra_symbols, self.inventory_status = discover(
                self.connection, self.settings.symbols,
                lambda key, name: self.connection.read_by_name(
                    name, pyads.PLCTYPE_UDINT if key == 'counter' else pyads.PLCTYPE_BOOL))
            self._last_inputs = {}
        except Exception as exc:
            self.disconnect()
            raise PlcError(f'ADS-verbinding of PLC-symbolen niet geldig: {exc}') from exc
    def _read_outputs(self) -> dict:
        c, p = self.connection, self.pyads
        return {
            'motor': bool(c.read_by_name(self.settings.symbol('motor'), p.PLCTYPE_BOOL)) if self.available.get('motor') else False,
            'diverter': bool(c.read_by_name(self.settings.symbol('diverter'), p.PLCTYPE_BOOL)) if self.available.get('diverter') else False,
            'counter': int(c.read_by_name(self.settings.symbol('counter'), p.PLCTYPE_UDINT)) if self.available.get('counter') else 0,
        }
    def exchange(self, inputs: dict[str, bool]) -> dict:
        if self.connection is None:
            raise PlcError('Geen actieve ADS-verbinding.')
        try:
            for key in INPUT_KEYS:
                if not self.available.get(key):
                    continue
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
        self.available = {}
        self.extra_symbols = []
        self.inventory_status = "unavailable"
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
