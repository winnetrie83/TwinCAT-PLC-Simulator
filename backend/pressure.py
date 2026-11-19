"""Educational two-pump tank: TwinCAT commands outputs, Python simulates plant.

This is a deliberately simplified, non-safety-rated water-level/pressure model.
All ADS access is isolated in the worker; a demo controller is only a sample PLC.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import threading
import time

SYMBOLS = {
    'start': 'MAIN.bTankStart', 'stop': 'MAIN.bTankStop',
    'level_low': 'MAIN.bTankLevelLow', 'level_high': 'MAIN.bTankLevelHigh',
    'pressure_high': 'MAIN.bTankPressureHigh',
    'pressure': 'MAIN.fTankPressure',
    'pump_in': 'MAIN.bPumpIn', 'pump_out': 'MAIN.bPumpOut',
}
SENSORS = ('start','stop','level_low','level_high','pressure_high','pressure')
ACTUATORS = ('pump_in','pump_out')

@dataclass
class TankSettings:
    net_id: str
    port: int
    pulse_ms: int = 250
    symbols: dict = field(default_factory=lambda:dict(SYMBOLS))

class TankWorld:
    """level is % of tank capacity; pressure is illustrative kPa, not fluid engineering."""
    def __init__(self):
        self.level = 35.0
        self.volume_l = 100.0
        self.fill_rate = 10.0  # percentage points/s
        self.drain_rate = 7.0
        self.low_at = 25.0
        self.high_at = 80.0
        self.pressure_alarm_at = 185.0  # above normal 80% level (169 kPa)
        self.overflow_seconds = 0.0
    @property
    def pressure(self):
        return round(25.0 + self.level * 1.8, 2)
    def inputs(self):
        return {'level_low':self.level <= self.low_at,
                'level_high':self.level >= self.high_at,
                'pressure_high':self.pressure >= self.pressure_alarm_at,
                'pressure':float(self.pressure)}
    def step(self,dt,pump_in,pump_out,*,demo_limits=False):
        dt=max(0.0,min(float(dt),.1))
        # Opposite pump commands indicate incorrect PLC logic; do not move the liquid.
        if bool(pump_in) and bool(pump_out):
            return
        next_level=self.level+(self.fill_rate*bool(pump_in)-self.drain_rate*bool(pump_out))*dt
        if next_level>100:self.overflow_seconds+=dt
        if demo_limits:
            # Precise demo sensor edges, irrespective of the 20/50 ms simulation steps.
            # LIVE is deliberately NOT clamped to these limits: the student's PLC owns control.
            if pump_in and self.level <= self.high_at:
                next_level=min(next_level,self.high_at)
            if pump_out and self.level >= self.low_at:
                next_level=max(next_level,self.low_at)
        self.level=max(0.0,min(100.0,next_level))
    def snapshot(self):
        return {'level':round(self.level,2),'pressure':self.pressure,
                'volume_l':self.volume_l,'low_at':self.low_at,
                'high_at':self.high_at,'pressure_alarm_at':self.pressure_alarm_at,
                'overflow':self.overflow_seconds>0}

class TankController:
    def __init__(self,settings:TankSettings,demo=False):
        self.settings=settings;self.demo=demo
        self.conn=None;self.pyads=None;self.available={};self.extra_symbols=[]
        self.inventory_status='unavailable';self._last={}
        self._run=False;self._last_start=False;self.demo_cycle=False
    def connect(self):
        self._last={};self._last_start=False;self._run=False;self._fill=True
        if self.demo:
            self.available={key:True for key in SYMBOLS}
            self.inventory_status='demo'
            return
        import pyads
        from .symbols import discover
        self.pyads=pyads
        try:
            self.conn=pyads.Connection(self.settings.net_id,self.settings.port)
            self.conn.open()
            self.available,self.extra_symbols,self.inventory_status=discover(
                self.conn,self.settings.symbols,
                lambda key,name:self.conn.read_by_name(name,pyads.PLCTYPE_REAL if key=='pressure' else pyads.PLCTYPE_BOOL))
        except Exception:
            self.disconnect();raise
    def exchange(self,inputs):
        if self.demo:
            start=bool(inputs['start'])
            if bool(inputs['stop']):self._run=False
            elif start and not self._last_start:self._run=not self._run
            self._last_start=start
            # Demo only: hold at the upper sensor by default, or cycle high -> low.
            # An independent high-pressure alarm must never activate the fill pump.
            if inputs['level_high'] or inputs['pressure_high']:
                self._fill=False
            elif inputs['level_low'] and self.demo_cycle:
                self._fill=True
            return {'pump_in':self._run and self._fill and not inputs['pressure_high'],
                    'pump_out':self._run and self.demo_cycle and not self._fill}
        if self.conn is None:raise RuntimeError('Geen actieve ADS-verbinding.')
        try:
            for key in SENSORS:
                if not self.available.get(key):continue
                value=float(inputs[key]) if key=='pressure' else bool(inputs[key])
                if self._last.get(key)!=value:
                    self.conn.write_by_name(self.settings.symbols[key],value,
                        self.pyads.PLCTYPE_REAL if key=='pressure' else self.pyads.PLCTYPE_BOOL)
                    self._last[key]=value
            return {key:bool(self.conn.read_by_name(self.settings.symbols[key],self.pyads.PLCTYPE_BOOL))
                    if self.available.get(key) else False for key in ACTUATORS}
        except Exception as exc:
            raise RuntimeError(f'Tank ADS I/O-fout: {exc}') from exc
    def disconnect(self):
        conn,self.conn=self.conn,None
        self._last={};self.available={};self.extra_symbols=[];self.inventory_status='unavailable'
        if conn is not None:
            try:conn.close()
            except Exception:pass

class TankService:
    def __init__(self,settings,demo=False,controller=None):
        self.settings=settings;self.demo=demo
        self.controller=controller if controller is not None else TankController(settings,demo)
        self.world=TankWorld();self.outputs={'pump_in':False,'pump_out':False}
        self.lock=threading.RLock();self.stop_event=threading.Event();self.worker=None
        self.connected=False;self.connecting=False;self.error='';self.pulses={'start':0.0,'stop':0.0}
    def get_state(self):
        with self.lock:
            signals={**self.world.inputs(),**self.outputs,
                     'start':time.monotonic()<self.pulses['start'],
                     'stop':time.monotonic()<self.pulses['stop']}
            return {'connected':self.connected,'demo':self.demo,'error':self.error,
                    'target':f'{self.settings.net_id}:{self.settings.port}',
                    'world':self.world.snapshot(),'signals':signals,
                    'demo_cycle':self.controller.demo_cycle if self.demo else False,
                    'pump_conflict':bool(self.outputs['pump_in'] and self.outputs['pump_out']),
                    'diagnostics':{'available':dict(self.controller.available),
                        'extra':list(self.controller.extra_symbols),
                        'inventory_status':self.controller.inventory_status,
                        'missing':[self.settings.symbols[k] for k,v in self.controller.available.items() if not v]}}
    def connect(self):
        with self.lock:
            if self.connected:return self.get_state()
            if self.connecting or (self.worker and self.worker.is_alive()):
                return {**self.get_state(),'error':'Vorige verbinding nog actief of wordt afgesloten.'}
            self.connecting=True
        try:
            self.controller.connect()
            with self.lock:
                self.stop_event=threading.Event();self.world=TankWorld()
                self.outputs={'pump_in':False,'pump_out':False}
                self.pulses={'start':0.0,'stop':0.0};self.error='';self.connected=True
                self.worker=threading.Thread(target=self._loop,daemon=True,name='tank-simulator')
                self.worker.start()
        except Exception as exc:
            self.controller.disconnect()
            with self.lock:self.error=f'Tankverbinding mislukt: {exc}';self.connected=False
        finally:
            with self.lock:self.connecting=False
        return self.get_state()
    def _loop(self):
        prev=time.monotonic();next_exchange=prev
        try:
            while not self.stop_event.wait(.02):
                now=time.monotonic();dt=min(.1,now-prev);prev=now
                with self.lock:
                    self.world.step(dt,self.outputs['pump_in'],self.outputs['pump_out'],demo_limits=self.demo)
                    inputs={**self.world.inputs(),
                            'start':now<self.pulses['start'],
                            'stop':now<self.pulses['stop']}
                if now>=next_exchange:
                    outputs=self.controller.exchange(inputs)
                    with self.lock:self.outputs.update(outputs)
                    next_exchange=now+.05
        except Exception as exc:
            with self.lock:
                if not self.stop_event.is_set():self.error=str(exc)
        finally:
            self.controller.disconnect()
            with self.lock:
                self.connected=False;self.outputs={'pump_in':False,'pump_out':False}
    def set_demo_cycle(self,enabled):
        if not self.demo:
            raise ValueError('Deze instelling is uitsluitend beschikbaar in DEMO. LIVE blijft PLC-gestuurd.')
        with self.lock:
            self.controller.demo_cycle=bool(enabled)
            # Re-evaluate the demo phase from the physical level to avoid stale outputs.
            self.controller._fill=self.world.level < self.world.high_at
            if not enabled:
                self.outputs['pump_out']=False
            return self.get_state()

    def pulse(self,key):
        if key not in ('start','stop'):raise ValueError('Ongeldige tankbediening.')
        with self.lock:
            if not self.connected:return {**self.get_state(),'error':'Tank niet verbonden.'}
            self.pulses[key]=time.monotonic()+self.settings.pulse_ms/1000
            return self.get_state()
    def disconnect(self):
        self.stop_event.set()
        worker=self.worker
        if worker and worker.is_alive() and worker is not threading.current_thread():worker.join(timeout=2)
        with self.lock:
            self.connected=False;self.pulses={'start':0.0,'stop':0.0}
            self.outputs={'pump_in':False,'pump_out':False}
            if worker and worker.is_alive():self.error='Afsluiten duurt langer dan verwacht.'
            else:self.error=''
        return self.get_state()
