"""PLC Simulation Lab / phase 1. Run: python app.py [--demo] [--cli]."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backend.plc import PlcService, Settings

BASE = Path(__file__).resolve().parent


def load_settings(path: Path) -> Settings:
    raw = json.loads(path.read_text(encoding="utf-8"))
    symbols = raw.get("symbols", {})
    required = ("start", "stop", "sensor", "motor", "counter")
    if not isinstance(symbols, dict) or any(
        name not in symbols or not isinstance(symbols[name], str) or not symbols[name]
        for name in required
    ):
        raise ValueError("settings.json: alle 5 variabelenamen moeten ingevuld zijn.")
    ms = int(raw.get("pulse_ms", 250))
    port = int(raw.get("ads_port", 851))
    if not (100 <= ms <= 1500 and 1 <= port <= 65535):
        raise ValueError("settings.json: pulse_ms moet 100-1500 en ads_port 1-65535 zijn.")
    return Settings(
        ams_net_id=str(raw.get("ams_net_id", "127.0.0.1.1.1")),
        ads_port=port,
        pulse_ms=ms,
        symbols=symbols,
    )


class JsApi:
    """Tiny whitelist: no arbitrary Python evaluation from JS."""

    def __init__(self, service: PlcService):
        self.service = service

    def connect(self):
        return self.service.connect()

    def disconnect(self):
        return self.service.disconnect()

    def get_state(self):
        return self.service.get_state()

    def press_start(self):
        return self.service.pulse("start")

    def press_stop(self):
        return self.service.pulse("stop")

    def set_sensor(self, active: bool):
        return self.service.set_sensor(active)


def run_cli(service: PlcService):
    print("PLC Simulation Lab — fase 1 (console)")
    print("DEMO: geen TwinCAT" if service.demo else "LIVE: echte ADS-verbinding")
    print("Typ: connect, status, start, stop, sensor on, sensor off, disconnect, quit")
    print("(De start/stop-knoppen zijn 250 ms pulsen, instelbaar in config.)")
    while True:
        try:
            command = input("PLC> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if command in {"quit", "exit", "q"}:
            break
        elif command == "connect":
            result = service.connect()
        elif command == "disconnect":
            result = service.disconnect()
        elif command in {"status", "s"}:
            result = service.get_state()
        elif command == "start":
            result = service.pulse("start")
        elif command == "stop":
            result = service.pulse("stop")
        elif command in {"sensor on", "sensor aan"}:
            result = service.set_sensor(True)
        elif command in {"sensor off", "sensor uit"}:
            result = service.set_sensor(False)
        elif command == "help":
            print("connect | status | start | stop | sensor on | sensor off | disconnect | quit")
            continue
        elif not command:
            continue
        else:
            print("Onbekende opdracht. Typ help.")
            continue
        print(json.dumps(result, indent=2, ensure_ascii=False))
    service.disconnect()


def run_gui(service: PlcService) -> None:
    try:
        import webview
    except (ImportError, OSError) as exc:
        print("PyWebView ontbreekt. Voer eerst 'py -m pip install -r requirements.txt' uit.")
        print("Voorlopig alternatief: py app.py --cli --demo")
        raise SystemExit(2) from exc

    api = JsApi(service)
    view = (BASE / "frontend" / "index.html").as_uri()
    webview.create_window(
        "PLC Simulation Lab | Fase 1",
        view,
        js_api=api,
        width=1050,
        height=760,
        min_size=(860, 660),
        background_color="#0c1220",
    )
    try:
        webview.start(debug=False)
    finally:
        service.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description="TwinCAT ADS proof of concept")
    parser.add_argument("--demo", action="store_true", help="Geen TwinCAT nodig (nep-PLC)")
    parser.add_argument("--cli", action="store_true", help="Console i.p.v. desktopvenster")
    parser.add_argument("--config", default=str(BASE / "config" / "settings.json"))
    args = parser.parse_args()
    try:
        settings = load_settings(Path(args.config))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Configuratiefout: {exc}", file=sys.stderr)
        return 2
    service = PlcService(settings, demo=args.demo)
    if args.cli:
        run_cli(service)
    else:
        run_gui(service)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
