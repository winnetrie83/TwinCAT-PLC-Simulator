"""Non-blocking, thread-safe bridge between UI, PLC, and conveyor physics."""
from __future__ import annotations

import threading
import time
from typing import Any

from .model import ConveyorWorld
from .plc import AdsController, Controller, DemoController, INPUT_KEYS, PlcError, Settings


class SimulatorService:
    def __init__(self, settings: Settings, demo: bool = False, controller: Controller | None = None):
        self.settings = settings
        self.demo = demo
        self._controller = controller or (DemoController() if demo else AdsController(settings))
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._world = ConveyorWorld()
        self._outputs: dict[str, Any] = {'motor': False, 'diverter': False, 'counter': 0}
        self._pulse_until = {'start': 0.0, 'stop': 0.0}
        self._connected = False
        self._connecting = False
        self._error = ''

    def _snapshot(self) -> dict:
        world = self._world.snapshot()
        inputs = {
            'start': time.monotonic() < self._pulse_until['start'],
            'stop': time.monotonic() < self._pulse_until['stop'],
            **world['inputs'],
        }
        return {
            'connected': self._connected,
            'demo': self.demo,
            'error': self._error,
            'target': f'{self.settings.ams_net_id}:{self.settings.ads_port}',
            'inputs': inputs,
            'outputs': dict(self._outputs),
            'world': world,
        }

    def get_state(self) -> dict:
        with self._lock:
            return self._snapshot()

    def connect(self) -> dict:
        with self._lock:
            if self._connected:
                return self._snapshot()
            if self._connecting or (self._worker is not None and self._worker.is_alive()):
                return {**self._snapshot(), 'error': 'Verbinding wordt nog afgesloten. Probeer opnieuw.'}
            self._connecting = True
        try:
            self._controller.connect()
            self._stop_event = threading.Event()
            with self._lock:
                self._outputs = {'motor': False, 'diverter': False, 'counter': 0}
                self._pulse_until = {'start': 0.0, 'stop': 0.0}
                self._connected = True
                self._error = ''
                self._world.reset()
                if self.demo:
                    self._world.enqueue('standard')
                    self._world.enqueue('reject')
            self._worker = threading.Thread(target=self._run, name='PLC-simulation-worker', daemon=True)
            self._worker.start()
        except Exception as exc:
            self._controller.disconnect()
            with self._lock:
                self._connected = False
                self._error = str(exc)
        finally:
            with self._lock:
                self._connecting = False
                return self._snapshot()

    def _run(self) -> None:
        last = time.monotonic()
        last_exchange = 0.0
        try:
            while not self._stop_event.wait(0.02):
                now = time.monotonic()
                dt = now - last
                last = now
                with self._lock:
                    self._world.step(dt, bool(self._outputs['motor']), bool(self._outputs['diverter']))
                    world_inputs = self._world.inputs()
                    input_values = {
                        'start': now < self._pulse_until['start'],
                        'stop': now < self._pulse_until['stop'],
                        **world_inputs,
                    }
                if now - last_exchange >= 0.05:
                    # Synchronous ADS work happens OUTSIDE the state lock. UI stays responsive.
                    result = self._controller.exchange(input_values)
                    with self._lock:
                        self._outputs.update(result)
                    last_exchange = now
        except Exception as exc:
            with self._lock:
                if not self._stop_event.is_set():
                    self._error = str(exc)
        finally:
            # This thread owns the connection after connect() succeeds.
            self._controller.disconnect()
            with self._lock:
                self._connected = False
                self._outputs['motor'] = False
                self._outputs['diverter'] = False

    def disconnect(self) -> dict:
        self._stop_event.set()
        worker = self._worker
        if worker and worker.is_alive() and worker is not threading.current_thread():
            worker.join(timeout=2.0)
        with self._lock:
            self._connected = False
            self._pulse_until = {'start': 0.0, 'stop': 0.0}
            self._outputs['motor'] = False
            self._outputs['diverter'] = False
            self._error = ''
            return self._snapshot()

    def pulse(self, key: str) -> dict:
        if key not in ('start', 'stop'):
            return {**self.get_state(), 'error': 'Ongeldige drukknop.'}
        with self._lock:
            if not self._connected:
                return {**self._snapshot(), 'error': 'Niet verbonden.'}
            self._pulse_until[key] = time.monotonic() + self.settings.pulse_ms / 1000.0
            return self._snapshot()

    def add_package(self, kind: str) -> dict:
        with self._lock:
            if not self._connected:
                return {**self._snapshot(), 'error': 'Niet verbonden.'}
            try:
                self._world.enqueue(kind)
            except ValueError as exc:
                return {**self._snapshot(), 'error': str(exc)}
            return self._snapshot()

    def set_auto_feed(self, enabled: bool) -> dict:
        with self._lock:
            self._world.set_auto_feed(bool(enabled))
            return self._snapshot()

    def reset_scene(self) -> dict:
        with self._lock:
            self._world.reset()
            return self._snapshot()
