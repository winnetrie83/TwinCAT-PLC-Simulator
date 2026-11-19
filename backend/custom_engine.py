"""Custom 2D automation simulator: physical components, ADS ports, and project persistence.

The PLC owns actuator decisions. This module only simulates mechanics, sensors and
optional source generators. All coordinates and speeds are expressed in scene units.
"""
from __future__ import annotations

import copy
import json
import math
import os
import random
import re
import tempfile
import threading
import time
from pathlib import Path

CATALOG = {
    'conveyor': {'label': 'Transportband', 'io': {'motor': 'out'}, 'defaults': {'length': 260, 'speed': 95, 'rotation': 0}},
    'sensor': {'label': 'Lichtsluis', 'io': {'detected': 'in'}, 'defaults': {'range': 22}},
    'button': {'label': 'Drukknop', 'io': {'pressed': 'in'}, 'defaults': {}},
    'lamp': {'label': 'Signaallamp', 'io': {'on': 'out'}, 'defaults': {}},
    'package': {'label': 'Startpakket', 'io': {}, 'defaults': {'color': 'blue'}},
    'source': {'label': 'Invoerbak', 'io': {'enabled': 'out'}, 'defaults': {'mode': 'pattern', 'color': 'blue', 'pattern': 'blue,orange,green', 'interval': 2.0}},
    'sink': {'label': 'Opvangbak', 'io': {'full': 'in'}, 'defaults': {'capacity': 20}},
}
COLORS = ('blue', 'orange', 'green', 'red', 'yellow', 'purple')
NAME_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_.]*$')
MAX_COMPONENTS = 100
MAX_PARCELS = 250
GAP = 34.0


class ProjectError(ValueError):
    pass


def default_project():
    return {'version': 1, 'name': 'Mijn eerste installatie', 'components': [
        {'id': 'belt1', 'type': 'conveyor', 'x': 185, 'y': 300, 'settings': {'length': 340, 'speed': 95, 'rotation': 0}, 'plc': {'motor': 'MAIN.bCustomMotor'}},
        {'id': 'sensor1', 'type': 'sensor', 'x': 370, 'y': 260, 'settings': {'range': 22}, 'plc': {'detected': 'MAIN.bCustomSensor'}},
        {'id': 'source1', 'type': 'source', 'x': 115, 'y': 300, 'settings': {'mode': 'pattern', 'color': 'blue', 'pattern': 'blue,orange,green', 'interval': 2}, 'plc': {'enabled': ''}},
        {'id': 'sink1', 'type': 'sink', 'x': 595, 'y': 300, 'settings': {'capacity': 20}, 'plc': {'full': ''}},
        {'id': 'button1', 'type': 'button', 'x': 90, 'y': 105, 'settings': {}, 'plc': {'pressed': 'MAIN.bCustomButton'}},
        {'id': 'lamp1', 'type': 'lamp', 'x': 195, 'y': 105, 'settings': {}, 'plc': {'on': 'MAIN.bCustomLamp'}},
    ]}


def _number(v, low, high, label):
    if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or not low <= v <= high:
        raise ProjectError('Ongeldige waarde voor ' + label)
    return float(v)


def validate_project(project):
    if not isinstance(project, dict) or project.get('version') != 1:
        raise ProjectError('Niet-ondersteunde projectversie (verwacht 1).')
    name = project.get('name')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
        raise ProjectError('Projectnaam moet 1 tot 80 tekens bevatten.')
    components = project.get('components')
    if not isinstance(components, list) or len(components) > MAX_COMPONENTS:
        raise ProjectError('Maximaal 100 componenten toegelaten.')
    seen = set()
    assigned = set()
    result = []
    for c in components:
        if not isinstance(c, dict) or c.get('type') not in CATALOG:
            raise ProjectError('Onbekend componenttype.')
        ident, typ = c.get('id'), c['type']
        if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}', ident) or ident in seen:
            raise ProjectError('Component-ID ongeldig of dubbel: ' + str(ident))
        seen.add(ident)
        x = _number(c.get('x'), 0, 1200, 'X positie')
        y = _number(c.get('y'), 0, 720, 'Y positie')
        settings = c.get('settings', {})
        if not isinstance(settings, dict):
            raise ProjectError('Ongeldige componentinstellingen.')
        values = copy.deepcopy(CATALOG[typ]['defaults'])
        for key in values:
            v = settings.get(key, values[key])
            if key in ('length', 'speed'):
                values[key] = _number(v, 20 if key == 'length' else 1, 600, key)
            elif key == 'range':
                values[key] = _number(v, 4, 70, key)
            elif key == 'interval':
                values[key] = _number(v, .2, 120, key)
            elif key == 'capacity':
                values[key] = int(_number(v, 1, 250, key))
            elif key == 'rotation':
                if v not in (0, 90, 180, 270):
                    raise ProjectError('Rotatie moet 0, 90, 180 of 270 graden zijn.')
                values[key] = int(v)
            elif key == 'color':
                if v not in COLORS:
                    raise ProjectError('Ongeldige pakketkleur.')
                values[key] = v
            elif key == 'mode':
                if v not in ('fixed', 'random', 'pattern'):
                    raise ProjectError('Ongeldige invoermodus.')
                values[key] = v
            elif key == 'pattern':
                if not isinstance(v, str) or len(v) > 200 or not v.strip():
                    raise ProjectError('Geef een kleurpatroon op.')
                tokens = [part.strip().lower() for part in v.split(',')]
                if not 1 <= len(tokens) <= 32 or any(t not in COLORS for t in tokens):
                    raise ProjectError('Patroon: blue, orange, green, red, yellow of purple, gescheiden door komma’s.')
                values[key] = ','.join(tokens)
        plc = c.get('plc', {})
        if not isinstance(plc, dict) or any(k not in CATALOG[typ]['io'] for k in plc):
            raise ProjectError('Onbekende I/O-poort.')
        symbols = {}
        for port in CATALOG[typ]['io']:
            symbol = plc.get(port, '')
            if isinstance(symbol, str):symbol=symbol.strip()
            if not isinstance(symbol, str) or (symbol and not NAME_PATTERN.fullmatch(symbol)):
                raise ProjectError('Ongeldige PLC-symbolennaam voor ' + ident + '.' + port)
            if symbol:
                if symbol.lower() in assigned:
                    raise ProjectError('PLC-symbool is meermaals toegewezen: ' + symbol)
                assigned.add(symbol.lower())
            symbols[port] = symbol
        result.append({'id': ident, 'type': typ, 'x': x, 'y': y, 'settings': values, 'plc': symbols})
    return {'version': 1, 'name': name.strip(), 'components': result}


def geom(belt):
    a = math.radians(belt['settings'].get('rotation', 0))
    return math.cos(a), math.sin(a)


def belt_point(belt, distance):
    dx, dy = geom(belt)
    return belt['x'] + dx * distance, belt['y'] + dy * distance


def closest_belt(belts, x, y, max_offset=42):
    best = None
    for belt in belts:
        dx, dy = geom(belt)
        along = (x - belt['x']) * dx + (y - belt['y']) * dy
        sideways = abs((x - belt['x']) * dy - (y - belt['y']) * dx)
        if -16 <= along <= belt['settings']['length'] + 16 and sideways <= max_offset:
            score = sideways + max(0, -along, along - belt['settings']['length'])
            if best is None or score < best[2]:
                best = (belt, max(0., min(along, belt['settings']['length'])), score)
    return best


class CustomEngine:
    """Physics independent of rendering. Runtime parcels never modify saved editor components."""
    def __init__(self, project=None):
        self.load(project if project is not None else default_project())

    def load(self, project):
        self.project = validate_project(project)
        self.by_id = {c['id']: c for c in self.project['components']}
        self.belts = [c for c in self.by_id.values() if c['type'] == 'conveyor']
        self.values = {c['id']: {p: False for p in CATALOG[c['type']]['io']} for c in self.by_id.values()}
        self.pressed = set()
        self.demo_latched = False
        self.elapsed = 0.
        self.parcels = []
        self.next_id = 1
        self.rng = random.Random(136)
        self.generated = 0
        self.collected = {c['id']: 0 for c in self.by_id.values() if c['type'] == 'sink'}
        self.source_time = {c['id']: 0. for c in self.by_id.values() if c['type'] == 'source'}
        self.source_index = {c['id']: 0 for c in self.by_id.values() if c['type'] == 'source'}
        self.links = {}
        self._build_links()
        for c in self.by_id.values():
            if c['type'] == 'package':
                match = closest_belt(self.belts, c['x'], c['y'])
                if match:
                    self._spawn(match[0], match[1], c['settings']['color'])
        self.inputs()

    def _build_links(self):
        for belt in self.belts:
            sx, sy = belt['x'], belt['y']
            ex, ey = belt_point(belt, belt['settings']['length'])
            sources = [c for c in self.by_id.values() if c['type'] == 'source' and math.hypot(c['x']-sx, c['y']-sy) <= 110]
            sinks = [c for c in self.by_id.values() if c['type'] == 'sink' and math.hypot(c['x']-ex, c['y']-ey) <= 110]
            next_belts = [b for b in self.belts if b is not belt and math.hypot(b['x']-ex, b['y']-ey) <= 40]
            self.links[belt['id']] = {
                'sources': sorted(sources, key=lambda c: math.hypot(c['x']-sx,c['y']-sy)),
                'sink': min(sinks, key=lambda c: math.hypot(c['x']-ex,c['y']-ey)) if sinks else None,
                'next': min(next_belts, key=lambda c: math.hypot(c['x']-ex,c['y']-ey)) if next_belts else None,
            }

    def _spawn(self, belt, pos, color):
        if len(self.parcels) >= MAX_PARCELS:
            return False
        if any(p['belt'] == belt['id'] and abs(p['pos']-pos) < GAP for p in self.parcels):
            return False
        self.parcels.append({'id': 'p'+str(self.next_id), 'belt': belt['id'], 'pos': float(pos), 'color': color})
        self.next_id += 1
        return True

    def press(self, ident, pressed):
        if ident not in self.by_id or self.by_id[ident]['type'] != 'button':
            raise ProjectError('Drukknop niet gevonden.')
        if pressed:
            self.pressed.add(ident)
        else:
            self.pressed.discard(ident)

    def inputs(self):
        inputs = {}
        for c in self.by_id.values():
            typ, ident = c['type'], c['id']
            if typ == 'sensor':
                near = closest_belt(self.belts, c['x'], c['y'], max_offset=85)
                if near:
                    belt, pos, _ = near
                    detected = any(p['belt'] == belt['id'] and abs(p['pos']-pos) <= c['settings']['range'] for p in self.parcels)
                else:
                    detected = False
                self.values[ident]['detected'] = detected
            elif typ == 'button':
                self.values[ident]['pressed'] = ident in self.pressed
            elif typ == 'sink':
                self.values[ident]['full'] = self.collected[ident] >= c['settings']['capacity']
            for port, direction in CATALOG[typ]['io'].items():
                if direction == 'in':
                    inputs[(ident, port)] = self.values[ident][port]
        return inputs

    def _choose_color(self, source):
        settings = source['settings']
        mode = settings['mode']
        if mode == 'fixed':
            return settings['color']
        if mode == 'random':
            return self.rng.choice(COLORS)
        seq = settings['pattern'].split(',')
        index = self.source_index[source['id']]
        self.source_index[source['id']] = index + 1
        return seq[index % len(seq)]

    def _transfer(self, p, old_belt, new_belt):
        if any(other is not p and other['belt'] == new_belt['id'] and other['pos'] < GAP for other in self.parcels):
            return False
        p['belt'], p['pos'] = new_belt['id'], 0.
        return True

    def step(self, dt, outputs):
        dt = max(0., min(.1, float(dt)))
        self.elapsed += dt
        for (ident, port), value in outputs.items():
            if ident in self.values and port in self.values[ident] and CATALOG[self.by_id[ident]['type']]['io'].get(port) == 'out':
                self.values[ident][port] = bool(value)
        # A source without PLC mapping is automatically enabled, even in LIVE mode.
        for belt in self.belts:
            if not self.values[belt['id']]['motor']:
                continue
            on_belt = sorted((p for p in self.parcels if p['belt'] == belt['id']), key=lambda p: p['pos'], reverse=True)
            front = belt['settings']['length'] + GAP
            for p in on_belt:
                max_pos = min(belt['settings']['length'], front - GAP)
                p['pos'] = min(max_pos, p['pos'] + belt['settings']['speed'] * dt)
                if p['pos'] >= belt['settings']['length'] - .001:
                    link = self.links[belt['id']]
                    sink = link['sink']
                    if sink and self.collected[sink['id']] < sink['settings']['capacity']:
                        self.collected[sink['id']] += 1
                        self.parcels.remove(p)
                    elif not sink and link['next'] and self.values[link['next']['id']]['motor']:
                        self._transfer(p, belt, link['next'])
                front = p['pos'] if p in self.parcels and p['belt'] == belt['id'] else belt['settings']['length'] + GAP
        for source in (c for c in self.by_id.values() if c['type'] == 'source'):
            ident = source['id']
            candidates = [(b, math.hypot(source['x']-b['x'],source['y']-b['y'])) for b in self.belts if source in self.links[b['id']]['sources']]
            if not candidates:
                continue
            belt = min(candidates, key=lambda pair: pair[1])[0]
            self.source_time[ident] += dt
            interval = source['settings']['interval']
            if self.source_time[ident] >= interval:
                enabled = self.values[ident]['enabled'] if source['plc'].get('enabled') else True
                if enabled and not any(parcel['belt'] == belt['id'] and parcel['pos'] < GAP for parcel in self.parcels) and len(self.parcels) < MAX_PARCELS:
                    color = self._choose_color(source)
                    if self._spawn(belt, 0, color):
                        self.source_time[ident] -= interval
                        self.generated += 1
                else:
                    self.source_time[ident] = interval  # blocked source waits, never builds an infinite queue
        self.inputs()

    def empty_sink(self, ident):
        if ident not in self.collected:
            raise ProjectError('Opvangbak niet gevonden.')
        self.collected[ident] = 0
        self.inputs()

    def snapshot(self):
        parcels = []
        for p in self.parcels:
            belt = self.by_id[p['belt']]
            x, y = belt_point(belt, p['pos'])
            parcels.append({'id': p['id'], 'x': round(x, 3), 'y': round(y, 3), 'color': p['color'], 'belt': p['belt']})
        return {'project': copy.deepcopy(self.project), 'values': copy.deepcopy(self.values),
                'parcels': parcels, 'collected': dict(self.collected), 'generated': self.generated,
                'links': {ident: {'sink': v['sink']['id'] if v['sink'] else None,
                                  'next': v['next']['id'] if v['next'] else None,
                                  'sources': [s['id'] for s in v['sources']]} for ident, v in self.links.items()},
                'elapsed': round(self.elapsed, 3)}


class CustomService:
    def __init__(self, net_id, port, demo=False):
        self.net_id = net_id
        self.port = port
        self.demo = demo
        self.lock = threading.RLock()
        self.engine = CustomEngine()
        self.connected = False
        self.error = ''
        self.missing = []
        self.extra = []
        self.inventory_status = 'unavailable'
        self._worker = None
        self._stop = threading.Event()
        self._conn = None
        self._ads = None
        self._available = {}
        self._prev_inputs = {}
        self._last_button = False
        self.storage = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / '.config')) / 'PLC-Simulation-Lab' / 'projects'

    def set_target(self, net_id, port):
        with self.lock:
            if self.connected or (self._worker and self._worker.is_alive()):
                raise ProjectError('Verbreek eerst de Custom Simulator.')
            self.net_id, self.port = net_id, int(port)

    def catalog(self):
        return copy.deepcopy(CATALOG)

    def get_state(self):
        with self.lock:
            return {**self.engine.snapshot(), 'connected': self.connected, 'demo': self.demo, 'error': self.error,
                    'target': f'{self.net_id}:{self.port}', 'missing': self.missing[:], 'extra': self.extra[:],
                    'inventory_status': self.inventory_status}

    def load_project(self, project):
        with self.lock:
            if self.connected or (self._worker and self._worker.is_alive()):
                raise ProjectError('Verbreek eerst de PLC-verbinding om het project te wijzigen.')
            self.engine.load(project)
            self.error = ''
            return self.get_state()

    def _path(self, name):
        if not isinstance(name, str) or not re.fullmatch('[A-Za-z0-9_-]{1,60}', name):
            raise ProjectError('Gebruik 1–60 letters, cijfers, _ of - voor de bestandsnaam.')
        return self.storage / (name + '.json')

    def save(self, name):
        with self.lock:
            if self.connected:
                raise ProjectError('Stop de simulatie voor je opslaat.')
            target = self._path(name)
            self.storage.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix='.custom-', suffix='.tmp', dir=self.storage)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(self.engine.project, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, target)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            return {'saved': name, 'path': str(target)}

    def list_projects(self):
        return sorted(p.stem for p in self.storage.glob('*.json') if re.fullmatch('[A-Za-z0-9_-]{1,60}', p.stem)) if self.storage.exists() else []

    def open(self, name):
        target = self._path(name)
        if target.stat().st_size > 200000:
            raise ProjectError('Projectbestand is te groot.')
        return self.load_project(json.loads(target.read_text(encoding='utf-8')))

    def connect(self):
        with self.lock:
            if self.connected:
                return self.get_state()
            if self._worker and self._worker.is_alive():
                raise ProjectError('Vorige verbinding wordt nog afgesloten.')
            self.error = ''
            self._available = {}
            self.missing = []
            self.extra = []
            self.inventory_status = 'unavailable'
            # Restore initial physical state each time a simulation starts.
            self.engine.load(self.engine.project)
            self._prev_inputs = {}
            self._last_button = False
            self._stop = threading.Event()
            mapping = {(c['id'], p): sym for c in self.engine.project['components'] for p, sym in c['plc'].items() if sym}
        if not self.demo:
            try:
                import pyads
                from .symbols import discover
                conn = pyads.Connection(self.net_id, self.port)
                conn.open()
                available, extras, status = discover(
                    conn, {f'{key[0]}/{key[1]}': value for key, value in mapping.items()},
                    lambda key, sym: conn.read_by_name(sym, pyads.PLCTYPE_BOOL))
            except Exception as exc:
                if 'conn' in locals():
                    try:
                        conn.close()
                    except Exception:
                        pass
                with self.lock:
                    self.error = f'ADS-verbinding mislukt: {exc}'
                return self.get_state()
            with self.lock:
                self._conn, self._ads = conn, pyads
                self._available = {key: available[f'{key[0]}/{key[1]}'] for key in mapping}
                self.missing = [sym for key, sym in mapping.items() if not self._available[key]]
                self.extra = extras
                self.inventory_status = status
        with self.lock:
            self.connected = True
            self._worker = threading.Thread(target=self._run, args=(mapping,), daemon=True, name='custom-simulator-worker')
            self._worker.start()
            return self.get_state()

    def _run(self, mapping):
        last = time.monotonic()
        last_ads = 0.
        outputs = {}
        try:
            while not self._stop.wait(.02):
                now = time.monotonic()
                dt = now - last
                last = now
                with self.lock:
                    inputs = self.engine.inputs()
                    if self.demo:
                        buttons = any(value for (ident, port), value in inputs.items() if port == 'pressed')
                        if buttons and not self._last_button:
                            self.engine.demo_latched = not self.engine.demo_latched
                        self._last_button = buttons
                        outputs = {(c['id'], port): (self.engine.demo_latched if port in ('motor', 'enabled') else any(inputs.values()))
                                   for c in self.engine.project['components']
                                   for port, direction in CATALOG[c['type']]['io'].items() if direction == 'out'}
                if not self.demo and now - last_ads >= .05:
                    fresh_outputs = {}
                    for key, value in inputs.items():
                        if key in mapping and self._available.get(key) and self._prev_inputs.get(key) != value:
                            self._conn.write_by_name(mapping[key], bool(value), self._ads.PLCTYPE_BOOL)
                            self._prev_inputs[key] = value
                    for c in self.engine.project['components']:
                        for port, direction in CATALOG[c['type']]['io'].items():
                            key = (c['id'], port)
                            if direction == 'out':
                                fresh_outputs[key] = bool(self._conn.read_by_name(mapping[key], self._ads.PLCTYPE_BOOL)) if key in mapping and self._available.get(key) else False
                    outputs = fresh_outputs
                    last_ads = now
                with self.lock:
                    self.engine.step(dt, outputs)
        except Exception as exc:
            with self.lock:
                self.error = 'Simulatie/ADS I/O-fout: ' + str(exc)
        finally:
            conn, self._conn = self._conn, None
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            with self.lock:
                self.connected = False
                for c in self.engine.project['components']:
                    for port, direction in CATALOG[c['type']]['io'].items():
                        if direction == 'out':
                            self.engine.values[c['id']][port] = False

    def press(self, ident, pressed):
        with self.lock:
            if not self.connected:
                raise ProjectError('Verbind eerst de simulator.')
            self.engine.press(ident, bool(pressed))
            return self.get_state()

    def empty_sink(self, ident):
        with self.lock:
            self.engine.empty_sink(ident)
            return self.get_state()

    def disconnect(self):
        self._stop.set()
        worker = self._worker
        if worker and worker.is_alive() and worker is not threading.current_thread():
            worker.join(timeout=2)
        with self.lock:
            return self.get_state()
