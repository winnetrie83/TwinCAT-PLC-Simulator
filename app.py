"""PLC Simulation Lab phase 2. Run: py app.py --demo or py app.py."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from backend.plc import DEFAULT_SYMBOLS, INPUT_KEYS, OUTPUT_KEYS, Settings
from backend.service import SimulatorService

BASE = Path(__file__).resolve().parent


def load_settings(file: Path) -> Settings:
    raw = json.loads(file.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise ValueError('settings.json moet een JSON-object bevatten.')
    symbols = raw.get('symbols')
    if not isinstance(symbols, dict):
        raise ValueError('settings.json: symbols ontbreekt.')
    missing = [k for k in (*INPUT_KEYS, *OUTPUT_KEYS) if not isinstance(symbols.get(k), str) or not symbols[k].strip()]
    if missing:
        raise ValueError('Ontbrekende PLC-symbolen: ' + ', '.join(missing))
    port = int(raw.get('ads_port', 851))
    pulse = int(raw.get('pulse_ms', 250))
    if not (1 <= port <= 65535 and 100 <= pulse <= 1500):
        raise ValueError('ads_port moet 1-65535 zijn en pulse_ms 100-1500.')
    return Settings(
        ams_net_id=str(raw.get('ams_net_id', '127.0.0.1.1.1')),
        ads_port=port, pulse_ms=pulse,
        symbols={k: symbols[k] for k in (*INPUT_KEYS, *OUTPUT_KEYS)},
    )


class JsApi:
    """Explicitly allowlisted operations available to the local HTML interface."""
    def __init__(self, service: SimulatorService):
        self.service = service

    def connect(self): return self.service.connect()
    def disconnect(self): return self.service.disconnect()
    def get_state(self): return self.service.get_state()
    def press_start(self): return self.service.pulse('start')
    def press_stop(self): return self.service.pulse('stop')
    def add_package(self, kind): return self.service.add_package(kind)
    def reset_scene(self): return self.service.reset_scene()
    def set_auto_feed(self, enabled): return self.service.set_auto_feed(enabled)


def run_gui(service: SimulatorService) -> None:
    try:
        import webview
    except (ImportError, OSError) as exc:
        print('PyWebView ontbreekt. Voer install.cmd uit of gebruik --cli --demo.')
        raise SystemExit(2) from exc
    page = (BASE / 'frontend' / 'index.html').as_uri()
    webview.create_window(
        'PLC Simulation Lab | Fase 2', page,
        js_api=JsApi(service), width=1250, height=840,
        min_size=(950, 720), background_color='#0b1424',
    )
    try:
        webview.start(debug=False)
    finally:
        service.disconnect()


def run_cli(service: SimulatorService) -> None:
    print('PLC Simulation Lab Fase 2 | DEMO' if service.demo else 'PLC Simulation Lab Fase 2 | ADS LIVE')
    print('Opdrachten: connect, start, stop, blue, orange, auto on, auto off, status, reset, disconnect, quit')
    try:
        while True:
            line = input('PLC> ').strip().lower()
            if line in ('quit', 'exit', 'q'):
                break
            if line == 'connect': state = service.connect()
            elif line == 'disconnect': state = service.disconnect()
            elif line == 'start': state = service.pulse('start')
            elif line == 'stop': state = service.pulse('stop')
            elif line == 'blue': state = service.add_package('standard')
            elif line == 'orange': state = service.add_package('reject')
            elif line == 'auto on': state = service.set_auto_feed(True)
            elif line == 'auto off': state = service.set_auto_feed(False)
            elif line == 'status': state = service.get_state()
            elif line == 'reset': state = service.reset_scene()
            elif not line: continue
            else:
                print('Onbekend commando.')
                continue
            print(json.dumps(state, ensure_ascii=False, indent=2))
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        service.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description='TwinCAT conveyor visualization')
    parser.add_argument('--demo', action='store_true', help='Voorbeeldbesturing zonder TwinCAT')
    parser.add_argument('--cli', action='store_true', help='CMD-interface')
    parser.add_argument('--config', default=str(BASE / 'config' / 'settings.json'))
    args = parser.parse_args()
    try:
        settings = load_settings(Path(args.config))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'Configuratiefout: {exc}', file=sys.stderr)
        return 2
    service = SimulatorService(settings, demo=args.demo)
    if args.cli:
        run_cli(service)
    else:
        run_gui(service)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
