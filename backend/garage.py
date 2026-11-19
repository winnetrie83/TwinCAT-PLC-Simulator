"""Garage door physics and PLC bridge; PLC owns motor direction, simulator owns limit sensors.

No interaction with conveyor variables. One button and two end limits.
"""
from __future__ import annotations
import threading
import time
from .symbols import discover
from dataclasses import dataclass

GARAGE_SYMBOLS = {
    'button': 'MAIN.bGateButton',
    'limit_open': 'MAIN.bGateLimitOpen',
    'limit_closed': 'MAIN.bGateLimitClosed',
    'motor_open': 'MAIN.bGateMotorOpen',
    'motor_close': 'MAIN.bGateMotorClose',
    'counter': 'MAIN.nGateCycleCounter',
}

@dataclass
class GarageSettings:
    ams_net_id: str
    ads_port: int = 851
    pulse_ms: int = 250
    symbols: dict | None = None
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = dict(GARAGE_SYMBOLS)

class GarageController:
    """Demo logic or real ADS; never writes PLC outputs in live mode."""
    def __init__(self, settings: GarageSettings, demo: bool):
        self.settings, self.demo = settings, demo
        self.conn = None
        self.pyads = None
        self.motor_open = self.motor_close = False
        self.previous_button = False
        self.counter = 0
        self.last_inputs = {}
        self.available = {}
        self.extra_symbols = []
        self.inventory_status = "unavailable"

    def connect(self):
        if self.demo:
            self.motor_open = self.motor_close = self.previous_button = False
            self.counter = 0
            return
        import pyads
        self.pyads = pyads
        try:
            self.conn = pyads.Connection(self.settings.ams_net_id, self.settings.ads_port)
            self.conn.open()
            self.available, self.extra_symbols, self.inventory_status = discover(
                self.conn, self.settings.symbols,
                lambda key, name: self.conn.read_by_name(
                    name, pyads.PLCTYPE_UDINT if key == 'counter' else pyads.PLCTYPE_BOOL))
        except Exception:
            self.disconnect()
            raise
        self.last_inputs = {}

    def exchange(self, inputs: dict) -> dict:
        if self.demo:
            pressed = inputs['button'] and not self.previous_button
            self.previous_button = inputs['button']
            if pressed:
                if self.motor_open or self.motor_close:
                    self.motor_open = self.motor_close = False
                elif inputs['limit_open']:
                    self.motor_close = True
                elif inputs['limit_closed']:
                    self.motor_open = True
                else:
                    # After a mid-travel stop, resume towards opening.
                    self.motor_open = True
            if inputs['limit_open']:
                self.motor_open = False
            if inputs['limit_closed']:
                self.motor_close = False
            self.counter = (self.counter + 1) % 2**32
            return {'motor_open':self.motor_open,'motor_close':self.motor_close,'counter':self.counter}
        for key in ('button','limit_open','limit_closed'):
            if not self.available.get(key):
                continue
            value = bool(inputs[key])
            if self.last_inputs.get(key) != value:
                self.conn.write_by_name(self.settings.symbols[key], value, self.pyads.PLCTYPE_BOOL)
                self.last_inputs[key] = value
        return {
            'motor_open': bool(self.conn.read_by_name(self.settings.symbols['motor_open'], self.pyads.PLCTYPE_BOOL)) if self.available.get('motor_open') else False,
            'motor_close': bool(self.conn.read_by_name(self.settings.symbols['motor_close'], self.pyads.PLCTYPE_BOOL)) if self.available.get('motor_close') else False,
            'counter': int(self.conn.read_by_name(self.settings.symbols['counter'], self.pyads.PLCTYPE_UDINT)) if self.available.get('counter') else 0,
        }

    def disconnect(self):
        conn, self.conn = self.conn, None
        self.available = {}
        self.extra_symbols = []
        self.inventory_status = "unavailable"
        if conn is not None:
            try: conn.close()
            except Exception: pass

class GarageService:
    def __init__(self, settings:GarageSettings, demo:bool=False):
        self.settings, self.demo = settings, demo
        self.controller = GarageController(settings, demo)
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.worker = None
        self.connected = False
        self.error = ''
        self.position = 0.0  # 0 closed, 1 open
        self.button_until = 0.0
        self.outputs = {'motor_open':False,'motor_close':False,'counter':0}
        self.conflict = False

    def _snapshot(self):
        return {'connected':self.connected,'demo':self.demo,'error':self.error,
                'target':f'{self.settings.ams_net_id}:{self.settings.ads_port}',
                'position':round(self.position,5),
                'inputs':{'button':time.monotonic()<self.button_until,
                          'limit_open':self.position>=1.0,'limit_closed':self.position<=0.0},
                'outputs':dict(self.outputs), 'conflict':self.conflict}

    def get_state(self):
        with self.lock: return self._snapshot()

    def connect(self):
        with self.lock:
            if self.connected: return self._snapshot()
            if self.worker and self.worker.is_alive():
                return {**self._snapshot(),'error':'Vorige verbinding wordt nog afgesloten.'}
        try:
            self.controller.connect()
        except Exception as exc:
            with self.lock:
                self.error = f'Garage ADS-verbinding mislukt: {exc}'
                return self._snapshot()
        with self.lock:
            self.stop_event = threading.Event()
            self.position = 0.0
            self.button_until = 0.0
            self.outputs = {'motor_open':False,'motor_close':False,'counter':0}
            self.conflict = False
            self.error = ''
            self.connected = True
            self.worker = threading.Thread(target=self._run, daemon=True, name='garage-worker')
            self.worker.start()
            return self._snapshot()

    def _run(self):
        last = time.monotonic()
        exchange_at = 0.0
        try:
            while not self.stop_event.wait(.02):
                now = time.monotonic()
                dt = max(0.0,min(.10, now-last))
                last = now
                with self.lock:
                    op = bool(self.outputs['motor_open'])
                    cl = bool(self.outputs['motor_close'])
                    self.conflict = op and cl
                    if not self.conflict:
                        if op: self.position = min(1.0,self.position+dt*.25)
                        elif cl: self.position = max(0.0,self.position-dt*.25)
                    inputs = {'button':now<self.button_until,
                              'limit_open':self.position>=1.0,
                              'limit_closed':self.position<=0.0}
                if now-exchange_at >= .05:
                    result = self.controller.exchange(inputs)
                    with self.lock: self.outputs.update(result)
                    exchange_at = now
        except Exception as exc:
            with self.lock:
                if not self.stop_event.is_set(): self.error=str(exc)
        finally:
            self.controller.disconnect()
            with self.lock:
                self.connected = False
                self.outputs['motor_open']=self.outputs['motor_close']=False

    def press_button(self):
        with self.lock:
            if not self.connected: return {**self._snapshot(),'error':'Garagepoort niet verbonden.'}
            self.button_until = time.monotonic()+self.settings.pulse_ms/1000
            return self._snapshot()

    def disconnect(self):
        self.stop_event.set()
        if self.worker and self.worker.is_alive(): self.worker.join(timeout=2)
        with self.lock:
            self.connected=False
            self.button_until=0
            self.outputs['motor_open']=self.outputs['motor_close']=False
            return self._snapshot()
