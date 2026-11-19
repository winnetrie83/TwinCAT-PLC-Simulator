"""Persistent ADS symbol mapping for the three built-in educational exercises.

Mappings are edited only while all simulator workers are disconnected.
Saved outside installation directory, preserving settings.json and README.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import tempfile
import threading

SYMBOL_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_.]*$')
MODULES = ('conveyor', 'garage', 'tank')

class MappingError(ValueError):
    pass

class MappingStore:
    def __init__(self, defaults, path=None):
        self.defaults = {module: dict(defaults[module]) for module in MODULES}
        self.path = Path(path) if path else Path(os.environ.get('LOCALAPPDATA') or (Path.home() / '.config')) / 'PLC-Simulation-Lab' / 'io_mapping.json'
        self.lock = threading.RLock()
        self.mappings = {module: dict(self.defaults[module]) for module in MODULES}
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(raw, dict) or raw.get('version') != 1 or not isinstance(raw.get('mappings'), dict):
                raise MappingError('Ongeldig I/O-mappingbestand.')
            for module in MODULES:
                if module in raw['mappings']:
                    self.mappings[module] = self.validate(module, raw['mappings'][module])

    def validate(self, module, symbols):
        if module not in MODULES:
            raise MappingError('Onbekende simulatie.')
        if not isinstance(symbols, dict) or set(symbols) != set(self.defaults[module]):
            raise MappingError('Het I/O-overzicht bevat ontbrekende of extra poorten.')
        parsed = {}
        used = set()
        for key, value in symbols.items():
            if not isinstance(value, str) or not SYMBOL_RE.fullmatch(value.strip()) or len(value) > 160:
                raise MappingError('Ongeldige PLC-symbolennaam voor ' + key)
            norm = value.strip().lower()
            if norm in used:
                raise MappingError('PLC-symbool dubbel toegewezen: ' + value)
            used.add(norm)
            parsed[key] = value.strip()
        return parsed

    def snapshot(self):
        with self.lock:
            return {'mappings': {m: dict(v) for m,v in self.mappings.items()}, 'defaults': {m: dict(v) for m,v in self.defaults.items()},'storage_path':str(self.path)}

    def save(self, module, symbols):
        validated = self.validate(module, symbols)
        with self.lock:
            next_values = {m: dict(v) for m,v in self.mappings.items()}
            next_values[module] = validated
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp = tempfile.mkstemp(prefix='.io-mapping-', suffix='.tmp', dir=self.path.parent)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump({'version':1,'mappings':next_values}, f, indent=2, ensure_ascii=False)
                    f.write('\n');f.flush();os.fsync(f.fileno())
                os.replace(temp,self.path)
            finally:
                if os.path.exists(temp):os.unlink(temp)
            self.mappings = next_values
            return self.snapshot()
