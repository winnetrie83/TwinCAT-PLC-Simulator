"""PLC Simulation Lab v0.8: existing conveyor/garage and custom modular 2D editor."""
from __future__ import annotations
import argparse
import json
import sys
import threading
from pathlib import Path
from backend.plc import INPUT_KEYS,OUTPUT_KEYS,Settings
from backend.service import SimulatorService
from backend.garage import GarageService,GarageSettings,GARAGE_SYMBOLS
from backend.profiles import ProfileStore
from backend.custom_engine import CustomService
from backend.pressure import TankService,TankSettings,SYMBOLS as TANK_SYMBOLS
from backend.io_mapping import MappingStore
from backend.exercise_tests import ExerciseTestRunner

BASE=Path(__file__).resolve().parent

def load_settings(path:Path)->Settings:
    raw=json.loads(path.read_text(encoding='utf-8'))
    symbols=raw.get('symbols',{})
    missing=[k for k in (*INPUT_KEYS,*OUTPUT_KEYS) if not isinstance(symbols.get(k),str) or not symbols[k].strip()]
    if missing:raise ValueError('Ontbrekende transportbandsymbolen: '+', '.join(missing))
    port=int(raw.get('ads_port',851));pulse=int(raw.get('pulse_ms',250))
    if not (1<=port<=65535 and 100<=pulse<=1500):raise ValueError('Ongeldige ADS-poort of drukknopduur')
    return Settings(str(raw.get('ams_net_id','127.0.0.1.1.1')),port,pulse,
                    {k:symbols[k] for k in (*INPUT_KEYS,*OUTPUT_KEYS)})

class JsApi:
    def __init__(self,service:SimulatorService,garage:GarageService,profiles:ProfileStore,custom:CustomService,tank:TankService,mapping:MappingStore,tests:ExerciseTestRunner):
        self.service=service;self.garage=garage;self.profiles=profiles;self.custom=custom;self.tank=tank
        self._profile_lock=threading.RLock()
        self.mapping=mapping;self.tests=tests

    @staticmethod
    def _with_diagnostics(data,controller,symbols,demo):
        present={key:True for key in symbols} if demo else dict(getattr(controller,'available',{}))
        missing=[name for key,name in symbols.items() if present.get(key) is False]
        return {**data,'symbol_diagnostics':{'available':present,'missing':missing,
            'extras':list(getattr(controller,'extra_symbols',[])) if not demo else [],
            'inventory_status':'demo' if demo else getattr(controller,'inventory_status','unavailable')}}

    def _conveyor_status(self,data):
        return self._with_diagnostics(data,self.service._controller,self.service.settings.symbols,self.service.demo)
    def _garage_status(self,data):
        return self._with_diagnostics(data,self.garage.controller,self.garage.settings.symbols,self.garage.demo)

    def get_profiles(self):
        with self._profile_lock:return self.profiles.snapshot()

    def _busy(self):
        active = (self.service.get_state()['connected'] or self.garage.get_state()['connected']
                  or self.custom.get_state()['connected'] or self.tank.get_state()['connected'])
        workers = (getattr(self.service, '_worker', None), getattr(self.garage, 'worker', None),
                   getattr(self.custom, '_worker', None), getattr(self.tank, 'worker', None))
        return active or any(w is not None and w.is_alive() for w in workers)


    def _apply_profile(self):
        if self._busy():raise ValueError('Verbreek eerst alle actieve PLC-verbindingen.')
        p=self.profiles.selected();old=self.service.settings
        new=Settings(p['ams_net_id'],p['ads_port'],old.pulse_ms,dict(old.symbols))
        self.service.settings=new
        if hasattr(self.service._controller,'settings'):self.service._controller.settings=new
        g=self.garage.settings
        new_g=GarageSettings(p['ams_net_id'],p['ads_port'],g.pulse_ms,dict(g.symbols))
        self.garage.settings=new_g;self.garage.controller.settings=new_g
        self.custom.set_target(p['ams_net_id'],p['ads_port'])
        self.tank.settings.net_id=p['ams_net_id'];self.tank.settings.port=p['ads_port']
        self.tank.controller.settings=self.tank.settings

    def select_profile(self,ident):
        with self._profile_lock:
            if self._busy():raise ValueError('Verbreek eerst alle actieve PLC-verbindingen.')
            result=self.profiles.select(ident);self._apply_profile();return result

    def save_profile(self,ident,name,net_id,port):
        with self._profile_lock:
            if self._busy():raise ValueError('Verbreek eerst alle actieve PLC-verbindingen.')
            result=self.profiles.upsert(ident,name,net_id,port);self._apply_profile();return result

    def delete_profile(self,ident):
        with self._profile_lock:
            if self._busy():raise ValueError('Verbreek eerst alle actieve PLC-verbindingen.')
            result=self.profiles.delete(ident);self._apply_profile();return result

    def connect(self):
        if self.garage.get_state()['connected'] or self.custom.get_state()['connected'] or self.tank.get_state()['connected']:
            return {**self.service.get_state(),'error':'Verbreek eerst de andere simulatieverbinding.'}
        return self._conveyor_status(self.service.connect())
    def disconnect(self):return self._conveyor_status(self.service.disconnect())
    def get_state(self):return self._conveyor_status(self.service.get_state())
    def press_start(self):return self._conveyor_status(self.service.pulse('start'))
    def press_stop(self):return self._conveyor_status(self.service.pulse('stop'))
    def add_package(self,kind):return self._conveyor_status(self.service.add_package(kind))
    def reset_scene(self):return self._conveyor_status(self.service.reset_scene())
    def set_auto_feed(self,enabled):return self._conveyor_status(self.service.set_auto_feed(enabled))
    def garage_get_state(self):return self._garage_status(self.garage.get_state())
    def garage_connect(self):
        if self.service.get_state()['connected'] or self.custom.get_state()['connected'] or self.tank.get_state()['connected']:
            return {**self.garage.get_state(),'error':'Verbreek eerst de andere simulatieverbinding.'}
        return self._garage_status(self.garage.connect())
    def garage_disconnect(self):return self._garage_status(self.garage.disconnect())
    def garage_press_button(self):return self._garage_status(self.garage.press_button())

    def tank_get_state(self):return self.tank.get_state()
    def tank_connect(self):
        if self.service.get_state()['connected'] or self.garage.get_state()['connected'] or self.custom.get_state()['connected']:
            return {**self.tank.get_state(),'error':'Verbreek eerst de andere simulatieverbinding.'}
        return self.tank.connect()
    def tank_disconnect(self):return self.tank.disconnect()
    def tank_press_start(self):return self.tank.pulse('start')
    def tank_press_stop(self):return self.tank.pulse('stop')
    def tank_set_demo_cycle(self,enabled):return self.tank.set_demo_cycle(enabled)

    def io_mapping_get(self):
        return self.mapping.snapshot()

    def io_mapping_save(self,module,symbols):
        with self._profile_lock:
            if self._busy() or self.tests.snapshot()['running']:
                raise ValueError('Verbreek alle simulaties en wacht op lopende tests voordat je PLC-symbolen wijzigt.')
            result=self.mapping.save(module,symbols)
            self._set_module_symbols(module,result['mappings'][module])
            return result

    def io_mapping_reset(self,module):
        if module not in ('conveyor','garage','tank'):
            raise ValueError('Onbekende simulatie.')
        return self.io_mapping_save(module,self.mapping.defaults[module])

    def _set_module_symbols(self,module,symbols):
        if module=='conveyor':
            old=self.service.settings
            updated=Settings(old.ams_net_id,old.ads_port,old.pulse_ms,dict(symbols))
            self.service.settings=updated
            if hasattr(self.service._controller,'settings'):self.service._controller.settings=updated
        elif module=='garage':
            old=self.garage.settings
            updated=GarageSettings(old.ams_net_id,old.ads_port,old.pulse_ms,dict(symbols))
            self.garage.settings=updated;self.garage.controller.settings=updated
        elif module=='tank':
            self.tank.settings.symbols=dict(symbols)
            self.tank.controller.settings=self.tank.settings

    def exercise_test_start(self,module):
        return self.tests.start(module)
    def exercise_test_status(self):
        return self.tests.snapshot()

    def custom_catalog(self):return self.custom.catalog()
    def custom_get_state(self):return self.custom.get_state()
    def custom_load_project(self,project):return self.custom.load_project(project)
    def custom_save(self,name):return self.custom.save(name)
    def custom_list_projects(self):return self.custom.list_projects()
    def custom_open(self,name):return self.custom.open(name)
    def custom_press(self,ident,pressed):return self.custom.press(ident,pressed)
    def custom_connect(self):
        if self.service.get_state()['connected'] or self.garage.get_state()['connected'] or self.tank.get_state()['connected']:
            return {**self.custom.get_state(),'error':'Verbreek eerst de andere simulatieverbinding.'}
        return self.custom.connect()
    def custom_disconnect(self):return self.custom.disconnect()
    def custom_empty_sink(self,ident):return self.custom.empty_sink(ident)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--demo',action='store_true')
    parser.add_argument('--cli',action='store_true');parser.add_argument('--config',default=str(BASE/'config'/'settings.json'))
    args=parser.parse_args()
    try:cfg=load_settings(Path(args.config))
    except Exception as exc:
        print(f'Configuratiefout: {exc}',file=sys.stderr);return 2
    try:profiles=ProfileStore(cfg.ams_net_id,cfg.ads_port)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print(f'Profielconfiguratiefout: {exc}',file=sys.stderr);return 2
    chosen=profiles.selected();cfg=Settings(chosen['ams_net_id'],chosen['ads_port'],cfg.pulse_ms,dict(cfg.symbols))
    service=SimulatorService(cfg,demo=args.demo)
    garage=GarageService(GarageSettings(cfg.ams_net_id,cfg.ads_port,cfg.pulse_ms,dict(GARAGE_SYMBOLS)),demo=args.demo)
    custom=CustomService(cfg.ams_net_id,cfg.ads_port,demo=args.demo)
    tank=TankService(TankSettings(cfg.ams_net_id,cfg.ads_port,cfg.pulse_ms),demo=args.demo)
    try:
        mapping=MappingStore({'conveyor':cfg.symbols,'garage':GARAGE_SYMBOLS,'tank':TANK_SYMBOLS})
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f'I/O-mappingconfiguratiefout: {exc}',file=sys.stderr)
        return 2
    for mod, symbols in mapping.snapshot()['mappings'].items():
        if mod=='conveyor':
            updated=Settings(service.settings.ams_net_id,service.settings.ads_port,service.settings.pulse_ms,dict(symbols))
            service.settings=updated
            if hasattr(service._controller,'settings'):service._controller.settings=updated
        elif mod=='garage':
            updated=GarageSettings(garage.settings.ams_net_id,garage.settings.ads_port,garage.settings.pulse_ms,dict(symbols))
            garage.settings=updated;garage.controller.settings=updated
        elif mod=='tank':
            tank.settings.symbols=dict(symbols)
    tests=ExerciseTestRunner({'conveyor':service,'garage':garage,'tank':tank})
    if args.cli:
        print('PLC Simulation Lab | CLI transportband | garage en custom via GUI')
        try:
            while True:
                cmd=input('PLC> ').strip().lower()
                if cmd in ('exit','quit','q'):break
                if cmd=='connect':state=service.connect()
                elif cmd=='disconnect':state=service.disconnect()
                elif cmd=='start':state=service.pulse('start')
                elif cmd=='stop':state=service.pulse('stop')
                elif cmd=='blue':state=service.add_package('standard')
                elif cmd=='orange':state=service.add_package('reject')
                elif cmd=='auto on':state=service.set_auto_feed(True)
                elif cmd=='auto off':state=service.set_auto_feed(False)
                elif cmd=='status':state=service.get_state()
                elif cmd=='reset':state=service.reset_scene()
                else:
                    print('Commands: connect, disconnect, start, stop, blue, orange, auto on/off, status, reset, quit');continue
                print(json.dumps(state,ensure_ascii=False,indent=2))
        except (KeyboardInterrupt,EOFError):pass
        finally:service.disconnect();garage.disconnect();custom.disconnect();tank.disconnect()
        return 0
    try:import webview
    except (ImportError,OSError) as exc:
        print('PyWebView ontbreekt; voer install.cmd uit.',file=sys.stderr);return 2
    # Generate augmented page at runtime; original index.html remains intact.
    source=(BASE/'frontend'/'index.html').read_text(encoding='utf-8')
    if '<script src="custom.js"></script>' not in source:
        source=source.replace('</head>','  <link rel="stylesheet" href="custom.css">\n</head>',1)
        source=source.replace('</body>','  <script src="custom.js"></script>\n</body>',1)
    if '<script src="tank.js"></script>' not in source:
        source=source.replace('</head>','  <link rel="stylesheet" href="tank.css">\n</head>',1)
        source=source.replace('</body>','  <script src="tank.js"></script>\n</body>',1)
    source=source.replace('</head>', '  <link rel="stylesheet" href="module-tools.css">\n</head>',1)
    source=source.replace('</body>', '  <script src="module-tools.js"></script>\n</body>',1)
    page=BASE/'frontend'/'_index_v11_generated.html'
    page.write_text(source,encoding='utf-8')
    webview.create_window('PLC Simulation Lab | v1.1',page.as_uri(),js_api=JsApi(service,garage,profiles,custom,tank,mapping,tests),
                          width=1390,height=900,min_size=(950,720),background_color='#0b1424')
    try:webview.start(debug=False)
    finally:
        custom.disconnect();tank.disconnect();service.disconnect();garage.disconnect()
        try:page.unlink(missing_ok=True)
        except OSError:pass
    return 0
if __name__=='__main__':raise SystemExit(main())
