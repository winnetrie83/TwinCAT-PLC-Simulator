"""PLC Simulation Lab — conveyor and garage, demo or TwinCAT ADS."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from backend.plc import INPUT_KEYS, OUTPUT_KEYS, Settings
from backend.service import SimulatorService
from backend.garage import GarageService, GarageSettings, GARAGE_SYMBOLS
from backend.profiles import ProfileStore
import threading

BASE = Path(__file__).resolve().parent

def load_settings(path:Path)->Settings:
    raw=json.loads(path.read_text(encoding='utf-8'))
    symbols=raw.get('symbols',{})
    missing=[k for k in (*INPUT_KEYS,*OUTPUT_KEYS) if not isinstance(symbols.get(k),str) or not symbols[k].strip()]
    if missing: raise ValueError('Ontbrekende transportbandsymbolen: '+', '.join(missing))
    port=int(raw.get('ads_port',851))
    pulse=int(raw.get('pulse_ms',250))
    if not (1<=port<=65535 and 100<=pulse<=1500): raise ValueError('Ongeldige ADS-poort of drukknopduur')
    return Settings(str(raw.get('ams_net_id','127.0.0.1.1.1')),port,pulse,
                    {k:symbols[k] for k in (*INPUT_KEYS,*OUTPUT_KEYS)})

class JsApi:
    def __init__(self, service:SimulatorService, garage:GarageService | None = None,
                 profiles:ProfileStore | None = None):
        self.service=service
        self.garage=garage
        self.profiles=profiles
        self._profile_lock=threading.RLock()

    @staticmethod
    def _with_diagnostics(data, controller, symbols, demo):
        if demo:
            present = {key: True for key in symbols}
        else:
            present = dict(getattr(controller, 'available', {}))
        missing = [name for key, name in symbols.items() if present.get(key) is False]
        return {**data, 'symbol_diagnostics': {
            'available': present,
            'missing': missing,
            'extras': list(getattr(controller, 'extra_symbols', [])) if not demo else [],
            'inventory_status': 'demo' if demo else getattr(controller, 'inventory_status', 'unavailable')
        }}

    def _conveyor_status(self, data):
        return self._with_diagnostics(data, self.service._controller,
                                      self.service.settings.symbols, self.service.demo)

    def _garage_status(self, data):
        return self._with_diagnostics(data, self.garage.controller,
                                      self.garage.settings.symbols, self.garage.demo)

    def get_profiles(self):
        with self._profile_lock: return self.profiles.snapshot()

    def _apply_profile(self):
        # Never change the target of an active ADS connection.
        if self.service.get_state()['connected'] or self.garage.get_state()['connected']:
            raise ValueError('Verbreek eerst de actieve PLC-verbinding voordat je van profiel wisselt.')
        p = self.profiles.selected()
        old = self.service.settings
        new = Settings(p['ams_net_id'], p['ads_port'], old.pulse_ms, dict(old.symbols))
        self.service.settings = new
        if hasattr(self.service._controller, 'settings'):
            self.service._controller.settings = new
        g = self.garage.settings
        new_g = GarageSettings(p['ams_net_id'], p['ads_port'], g.pulse_ms, dict(g.symbols))
        self.garage.settings = new_g
        self.garage.controller.settings = new_g

    def select_profile(self, ident):
        with self._profile_lock:
            if self.service.get_state()['connected'] or self.garage.get_state()['connected']:
                raise ValueError('Verbreek eerst de actieve PLC-verbinding voordat je van profiel wisselt.')
            result = self.profiles.select(ident)
            self._apply_profile()
            return result

    def save_profile(self, ident, name, net_id, port):
        with self._profile_lock:
            if self.service.get_state()['connected'] or self.garage.get_state()['connected']:
                raise ValueError('Verbreek eerst de actieve PLC-verbinding om profielen te wijzigen.')
            result = self.profiles.upsert(ident, name, net_id, port)
            self._apply_profile()
            return result

    def delete_profile(self, ident):
        with self._profile_lock:
            if self.service.get_state()['connected'] or self.garage.get_state()['connected']:
                raise ValueError('Verbreek eerst de actieve PLC-verbinding om profielen te verwijderen.')
            result = self.profiles.delete(ident)
            self._apply_profile()
            return result
    def connect(self):
        if self.garage is not None and self.garage.get_state()['connected']:
            return {**self.service.get_state(),'error':'Verbreek eerst de garagepoort-ADS-verbinding.'}
        return self._conveyor_status(self.service.connect())
    def disconnect(self): return self._conveyor_status(self.service.disconnect())
    def get_state(self): return self._conveyor_status(self.service.get_state())
    def press_start(self): return self._conveyor_status(self.service.pulse('start'))
    def press_stop(self): return self._conveyor_status(self.service.pulse('stop'))
    def add_package(self,kind): return self._conveyor_status(self.service.add_package(kind))
    def reset_scene(self): return self._conveyor_status(self.service.reset_scene())
    def set_auto_feed(self,enabled): return self._conveyor_status(self.service.set_auto_feed(enabled))
    def garage_get_state(self): return self._garage_status(self.garage.get_state())
    def garage_connect(self):
        if self.service.get_state()['connected']:
            return {**self.garage.get_state(),'error':'Verbreek eerst de transportband-ADS-verbinding.'}
        return self._garage_status(self.garage.connect())
    def garage_disconnect(self): return self._garage_status(self.garage.disconnect())
    def garage_press_button(self): return self._garage_status(self.garage.press_button())


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--cli',action='store_true')
    parser.add_argument('--config',default=str(BASE/'config'/'settings.json'))
    args=parser.parse_args()
    try:
        cfg=load_settings(Path(args.config))
    except Exception as exc:
        print(f'Configuratiefout: {exc}',file=sys.stderr)
        return 2
    try:
        profiles=ProfileStore(cfg.ams_net_id,cfg.ads_port)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print(f'Profielconfiguratiefout: {exc}',file=sys.stderr)
        return 2
    chosen=profiles.selected()
    cfg=Settings(chosen['ams_net_id'],chosen['ads_port'],cfg.pulse_ms,dict(cfg.symbols))
    service=SimulatorService(cfg,demo=args.demo)
    garage=GarageService(GarageSettings(cfg.ams_net_id,cfg.ads_port,cfg.pulse_ms,dict(GARAGE_SYMBOLS)),demo=args.demo)
    if args.cli:
        print('PLC Simulation Lab | CLI transportband | garage in GUI')
        try:
            while True:
                cmd=input('PLC> ').strip().lower()
                if cmd in ('exit','quit','q'): break
                if cmd=='connect': state=service.connect()
                elif cmd=='disconnect': state=service.disconnect()
                elif cmd=='start': state=service.pulse('start')
                elif cmd=='stop': state=service.pulse('stop')
                elif cmd=='blue': state=service.add_package('standard')
                elif cmd=='orange': state=service.add_package('reject')
                elif cmd=='auto on': state=service.set_auto_feed(True)
                elif cmd=='auto off': state=service.set_auto_feed(False)
                elif cmd=='status': state=service.get_state()
                elif cmd=='reset': state=service.reset_scene()
                else:
                    print('Commands: connect, disconnect, start, stop, blue, orange, auto on/off, status, reset, quit')
                    continue
                print(json.dumps(state,ensure_ascii=False,indent=2))
        except (KeyboardInterrupt,EOFError): pass
        finally:
            service.disconnect()
            garage.disconnect()
        return 0
    try:
        import webview
    except (ImportError,OSError) as exc:
        print('PyWebView ontbreekt; voer install.cmd uit.',file=sys.stderr)
        return 2
    page=(BASE/'frontend'/'index.html').as_uri()
    webview.create_window('PLC Simulation Lab | v0.7',page,js_api=JsApi(service,garage,profiles),width=1250,height=840,min_size=(950,720),background_color='#0b1424')
    try: webview.start(debug=False)
    finally:
        service.disconnect()
        garage.disconnect()
    return 0
if __name__=='__main__': raise SystemExit(main())
