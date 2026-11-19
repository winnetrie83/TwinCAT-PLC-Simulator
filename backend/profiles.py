"""Persistent connection profile storage. Kept outside installation directory."""
from __future__ import annotations
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

NET_ID = re.compile(r'^(?:\d{1,3}\.){5}\d{1,3}$')

def validate(name: str, net_id: str, port: int) -> dict:
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
        raise ValueError('Geef een profielnaam van 1 tot 60 tekens op.')
    if not isinstance(net_id, str) or not NET_ID.fullmatch(net_id.strip()) or any(int(p)>255 for p in net_id.strip().split('.')):
        raise ValueError('AMS Net ID moet zes getallen tussen 0 en 255 bevatten.')
    try:
        port = int(port)
    except (TypeError, ValueError) as exc:
        raise ValueError('Ongeldige ADS-poort.') from exc
    if not 1 <= port <= 65535:
        raise ValueError('ADS-poort moet tussen 1 en 65535 liggen.')
    return {'name':name.strip(), 'ams_net_id':net_id.strip(), 'ads_port':port}

class ProfileStore:
    def __init__(self, initial_net_id: str, initial_port: int, path: Path | None = None):
        base = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / '.config')) / 'PLC-Simulation-Lab'
        self.path = Path(path) if path is not None else base / 'connections.json'
        self._initial = validate('Standaard', initial_net_id, initial_port)
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(raw, dict) or not isinstance(raw.get('profiles'), list):
                raise ValueError('Ongeldig profielenbestand: ' + str(self.path))
            self.profiles = []
            ids = set()
            for item in raw['profiles']:
                p = validate(item['name'],item['ams_net_id'],item['ads_port'])
                ident = str(item['id'])
                if not ident or ident in ids:
                    raise ValueError('Dubbele of lege profiel-ID.')
                ids.add(ident)
                self.profiles.append({'id':ident, **p})
            if not self.profiles:
                raise ValueError('Het laatste verbindingsprofiel mag niet verwijderd worden.')
            self.selected_id = str(raw.get('selected_id', ''))
            if self.selected_id not in ids:
                self.selected_id = self.profiles[0]['id']
                self._save()
        else:
            self.profiles = [{'id':uuid.uuid4().hex, **self._initial}]
            self.selected_id = self.profiles[0]['id']
            self._save()

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {'version':1,'selected_id':self.selected_id,'profiles':self.profiles}
        fd, filename = tempfile.mkstemp(prefix='.connections-', suffix='.tmp', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write('\n')
                f.flush()
                os.fsync(f.fileno())
            os.replace(filename, self.path)
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def snapshot(self):
        return {'profiles':[dict(p) for p in self.profiles], 'selected_id':self.selected_id,
                'storage_path':str(self.path)}

    def selected(self):
        return next(p for p in self.profiles if p['id'] == self.selected_id)

    def select(self, ident):
        if not any(p['id'] == ident for p in self.profiles):
            raise ValueError('Onbekend verbindingsprofiel.')
        self.selected_id = ident
        self._save()
        return self.snapshot()

    def upsert(self, ident, name, net_id, port):
        fields = validate(name, net_id, port)
        if ident is None or ident == '':
            self.profiles.append({'id':uuid.uuid4().hex,**fields})
            self.selected_id = self.profiles[-1]['id']
        else:
            entry = next((p for p in self.profiles if p['id']==ident),None)
            if entry is None:
                raise ValueError('Onbekend verbindingsprofiel.')
            entry.update(fields)
        self._save()
        return self.snapshot()

    def delete(self, ident):
        if len(self.profiles) <= 1:
            raise ValueError('Je moet minstens één profiel behouden.')
        if not any(p['id']==ident for p in self.profiles):
            raise ValueError('Onbekend verbindingsprofiel.')
        self.profiles = [p for p in self.profiles if p['id']!=ident]
        if self.selected_id == ident:
            self.selected_id = self.profiles[0]['id']
        self._save()
        return self.snapshot()
