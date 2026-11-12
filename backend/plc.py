"""Phase 1 ADS communication and deterministic demonstration backend.

Only communication and a *toy* PLC model live here. Physical simulation for
conveyors belongs in phase 2, not in this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import monotonic, sleep
from typing import Any, Protocol


class PlcError(RuntimeError):
    """Readable error to show in the UI."""


@dataclass(frozen=True)
class Settings:
    ams_net_id: str = "127.0.0.1.1.1"
    ads_port: int = 851
    pulse_ms: int = 250
    symbols: dict[str, str] | None = None

    def symbol(self, name: str) -> str:
        default = {
            "start": "MAIN.bStartButton",
            "stop": "MAIN.bStopButton",
            "sensor": "MAIN.bSensor",
            "motor": "MAIN.bMotor",
            "counter": "MAIN.nCycleCounter",
        }
        if self.symbols:
            return self.symbols.get(name, default[name])
        return default[name]


class Backend(Protocol):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def read(self) -> dict[str, Any]: ...
    def write_bool(self, key: str, value: bool) -> None: ...


class DemoPLC:
    """Offline imitation of the example ST; NOT ADS and NOT an actual PLC."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.connected = False
        self.inputs = {"start": False, "stop": False, "sensor": False}
        self.motor = False
        self.counter = 0
        self._last_scan = monotonic()

    def connect(self) -> None:
        self.connected = True
        self._last_scan = monotonic()

    def disconnect(self) -> None:
        self.connected = False

    def _scan(self) -> None:
        if not self.connected:
            raise PlcError("Demomodus is niet verbonden.")
        now = monotonic()
        # Approximate 10 ms cycles for a visual heartbeat, capped to avoid
        # giant leaps after a suspended machine. This is NOT a TwinCAT cycle.
        elapsed = min(now - self._last_scan, 5.0)
        ticks = max(1, int(elapsed / 0.01))
        self.counter = (self.counter + ticks) % (2**32)
        self._last_scan = now
        if self.inputs["stop"] or self.inputs["sensor"]:
            self.motor = False
        elif self.inputs["start"]:
            self.motor = True

    def read(self) -> dict[str, Any]:
        self._scan()
        return {**self.inputs, "motor": self.motor, "counter": self.counter}

    def write_bool(self, key: str, value: bool) -> None:
        if key not in self.inputs:
            raise PlcError(f"Geen schrijfbare ingang: {key}")
        self.inputs[key] = bool(value)
        self._scan()


class AdsPLC:
    """Reads PLC outputs and writes *only* the three external test inputs."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.connection = None
        self.pyads = None

    def connect(self) -> None:
        try:
            import pyads
        except (ImportError, OSError) as exc:
            raise PlcError(
                "pyads of de TwinCAT ADS-bibliotheek ontbreekt. "
                "Installeer requirements.txt en TwinCAT op Windows."
            ) from exc

        self.pyads = pyads
        try:
            self.connection = pyads.Connection(
                self.settings.ams_net_id,
                self.settings.ads_port,
            )
            self.connection.open()
            # Verify symbols and read/write types before declaring success.
            self.read()
        except Exception as exc:
            self.disconnect()
            raise PlcError(
                f"ADS-verbinding niet bruikbaar ({self.settings.ams_net_id}:"
                f"{self.settings.ads_port}): {exc}"
            ) from exc

    def disconnect(self) -> None:
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception:
                pass
        self.connection = None

    def _require(self):
        if self.connection is None or self.pyads is None:
            raise PlcError("Geen ADS-verbinding. Druk eerst op Verbinden.")
        return self.connection

    def read(self) -> dict[str, Any]:
        conn = self._require()
        p = self.pyads
        try:
            return {
                "start": bool(conn.read_by_name(self.settings.symbol("start"), p.PLCTYPE_BOOL)),
                "stop": bool(conn.read_by_name(self.settings.symbol("stop"), p.PLCTYPE_BOOL)),
                "sensor": bool(conn.read_by_name(self.settings.symbol("sensor"), p.PLCTYPE_BOOL)),
                "motor": bool(conn.read_by_name(self.settings.symbol("motor"), p.PLCTYPE_BOOL)),
                "counter": int(conn.read_by_name(self.settings.symbol("counter"), p.PLCTYPE_UDINT)),
            }
        except Exception as exc:
            raise PlcError(
                "PLC-symbolen niet leesbaar. Controleer MAIN, de variabelenamen, "
                f"de datatypes en of de PLC draait. ADS-detail: {exc}"
            ) from exc

    def write_bool(self, key: str, value: bool) -> None:
        if key not in ("start", "stop", "sensor"):
            raise PlcError(f"Schrijven naar '{key}' is niet toegestaan.")
        conn = self._require()
        try:
            conn.write_by_name(self.settings.symbol(key), bool(value), self.pyads.PLCTYPE_BOOL)
        except Exception as exc:
            raise PlcError(f"ADS-schrijffout ({self.settings.symbol(key)}): {exc}") from exc


class PlcService:
    """Thread-safe interface shared by GUI and command-line tester."""

    def __init__(self, settings: Settings, demo: bool = False):
        self.settings = settings
        self.demo = demo
        self._backend: Backend = DemoPLC(settings) if demo else AdsPLC(settings)
        self._lock = RLock()
        self.connected = False
        self.error = ""
        self._values = {
            "start": False, "stop": False, "sensor": False,
            "motor": False, "counter": 0,
        }

    def _response(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "demo": self.demo,
            "error": self.error,
            "target": f"{self.settings.ams_net_id} : {self.settings.ads_port}",
            "values": dict(self._values),
        }

    def connect(self) -> dict[str, Any]:
        with self._lock:
            if self.connected:
                return self.get_state()
            try:
                self._backend.connect()
                self._values = self._backend.read()
                self.connected = True
                self.error = ""
            except PlcError as exc:
                self._backend.disconnect()
                self.connected = False
                self.error = str(exc)
            except Exception as exc:
                self._backend.disconnect()
                self.connected = False
                self.error = f"Onverwachte verbindingsfout: {exc}"
            return self._response()

    def disconnect(self) -> dict[str, Any]:
        with self._lock:
            self._backend.disconnect()
            self.connected = False
            self.error = ""
            self._values = {
                "start": False, "stop": False, "sensor": False,
                "motor": False, "counter": 0,
            }
            return self._response()

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            if self.connected:
                try:
                    self._values = self._backend.read()
                    self.error = ""
                except PlcError as exc:
                    self._backend.disconnect()
                    self.connected = False
                    self.error = str(exc)
                except Exception as exc:
                    self._backend.disconnect()
                    self.connected = False
                    self.error = f"Verbinding verloren: {exc}"
            return self._response()

    def pulse(self, key: str) -> dict[str, Any]:
        if key not in ("start", "stop"):
            raise PlcError("Alleen start en stop kunnen als puls verzonden worden.")
        with self._lock:
            if not self.connected:
                return {**self._response(), "error": "Niet verbonden."}
            try:
                self._backend.write_bool(key, True)
                try:
                    sleep(self.settings.pulse_ms / 1000.0)
                finally:
                    self._backend.write_bool(key, False)
                return self.get_state()
            except PlcError as exc:
                self._backend.disconnect()
                self.connected = False
                self.error = str(exc)
                return self._response()

    def set_sensor(self, value: bool) -> dict[str, Any]:
        with self._lock:
            if not self.connected:
                return {**self._response(), "error": "Niet verbonden."}
            try:
                self._backend.write_bool("sensor", bool(value))
                return self.get_state()
            except PlcError as exc:
                self._backend.disconnect()
                self.connected = False
                self.error = str(exc)
                return self._response()
