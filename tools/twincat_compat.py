"""TwinCAT 3 ADS connection checker / version-independent live launcher.

Read-only ADS diagnostics for TwinCAT 2024-era separate UMRT and newer runtimes.
The script never modifies project files or writes any PLC symbol. After a
successful test it can launch the existing app.py using a temporary config
with the user-selected AMS Net ID and PLC ADS port.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUT_SYMBOLS = {'start', 'stop', 'sensor_entry', 'sensor_exit', 'reject_type', 'sensor_diverter'}
OUTPUT_SYMBOLS = {'motor', 'diverter', 'counter'}
VALID_NET_ID = re.compile(r'^\d{1,3}(?:\.\d{1,3}){5}$')


def validate_net_id(value: str) -> str:
    value = value.strip()
    if not VALID_NET_ID.fullmatch(value) or any(int(part) > 255 for part in value.split('.')):
        raise ValueError('AMS Net ID must contain six numbers between 0 and 255 (example: 199.4.42.250.1.1).')
    return value


def validate_ads_port(value: str | int) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError('ADS port must be a number (usually 851 for PLC Runtime 1).') from exc
    if not (1 <= port <= 65535):
        raise ValueError('ADS port must be between 1 and 65535.')
    return port


def find_settings_path(explicit: str | None = None) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f'Configuration not found: {path}')
        return path
    for name in ('settings.json', 'settings.default.json'):
        candidate = ROOT / 'config' / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError('No config/settings.json or config/settings.default.json found.')


def load_config(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict) or not isinstance(raw.get('symbols'), dict):
        raise ValueError('Invalid settings: expected a JSON object with a symbols object.')
    return raw


def merged_config(original: dict[str, Any], net_id: str, port: int) -> dict[str, Any]:
    """Preserve *all* fields, including phase-3 advanced symbol mappings."""
    updated = dict(original)
    updated['ams_net_id'] = validate_net_id(net_id)
    updated['ads_port'] = validate_ads_port(port)
    return updated


def check_ads(settings: dict[str, Any], pyads_module=None, output=print) -> bool:
    """Check ADS state and all configured symbols. Never write to PLC!"""
    if pyads_module is None:
        try:
            import pyads as pyads_module
        except (ImportError, OSError) as exc:
            output(f'[ERROR] pyads / TwinCAT ADS library unavailable: {exc}')
            output('Run install.cmd and ensure TwinCAT ADS components are installed.')
            return False

    net_id = settings['ams_net_id']
    port = settings['ads_port']
    conn = None
    output(f'Connecting to PLC at {net_id}:{port} ...')
    try:
        conn = pyads_module.Connection(net_id, port)
        conn.open()
        state = conn.read_state()
        ads_state = state[0]
        output(f'[OK] ADS connection established. ADS state: {ads_state} (RUN is typically 5).')
        if ads_state != 5:
            output('[WARNING] PLC is not in RUN state. Activate configuration, login and start the PLC in TwinCAT.')
            # Checking symbols can help diagnose a PLC in STOP mode.
        errors = 0
        symbols = settings['symbols']
        for key, name in symbols.items():
            if not isinstance(name, str) or not name.strip():
                output(f'[ERROR] {key}: missing PLC symbol name')
                errors += 1
                continue
            # The standard project uses BOOL for all other known variables,
            # and UDINT for the cycle counter. For unknown future symbols,
            # use symbolic read without a forced type.
            plc_type = (pyads_module.PLCTYPE_UDINT if key == 'counter' else
                        pyads_module.PLCTYPE_BOOL if key in INPUT_SYMBOLS | OUTPUT_SYMBOLS else None)
            try:
                if plc_type is None:
                    value = conn.read_by_name(name)
                else:
                    value = conn.read_by_name(name, plc_type)
                output(f'[OK] {key:16} {name:36} = {value}')
            except Exception as exc:
                errors += 1
                output(f'[ERROR] {key:16} {name:36} : {exc}')
        if errors:
            output(f'[FAIL] ADS is reachable, but {errors} symbol(s) could not be read.')
            output('Check POU path (MAIN vs PLC1.MAIN), symbol types and downloaded PLC project.')
        elif ads_state == 5:
            output('[PASS] ADS RUN and configured PLC symbols are readable. No PLC values were modified.')
        return errors == 0 and ads_state == 5
    except Exception as exc:
        output(f'[ERROR] ADS connection failed: {exc}')
        output('Check: UMRT started, correct target AMS Net ID, PLC runtime in RUN, correct ADS port (often 851).')
        output('The UMRT may have a *different* AMS Net ID than the system TwinCAT router.')
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def prompt_with_default(label: str, default: str) -> str:
    typed = input(f'{label} [{default}]: ').strip()
    return typed if typed else default


def launch_live(settings: dict[str, Any], runner=None) -> int:
    """Use a temporary config so user's local settings and disclaimer stay untouched."""
    runner = runner or subprocess.run
    with tempfile.TemporaryDirectory(prefix='plc_sim_ads_') as directory:
        temporary_config = Path(directory) / 'settings.compat.json'
        temporary_config.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        command = [sys.executable, str(ROOT / 'app.py'), '--config', str(temporary_config)]
        result = runner(command, cwd=ROOT, check=False)
        return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Read-only TwinCAT ADS diagnostics and LIVE launcher (2024/2026+).')
    parser.add_argument('--config', help='Existing simulator config (default: settings.json or settings.default.json).')
    parser.add_argument('--net-id', help='Target runtime AMS Net ID; not your IP address.')
    parser.add_argument('--port', type=int, help='PLC ADS port, usually 851.')
    parser.add_argument('--check-only', action='store_true', help='Read-only diagnostics; do not launch the GUI.')
    parser.add_argument('--no-prompt', action='store_true', help='Use arguments or config without interactive questions.')
    args = parser.parse_args(argv)

    try:
        cfg_path = find_settings_path(args.config)
        base_cfg = load_config(cfg_path)
        net_id = str(args.net_id or base_cfg.get('ams_net_id', '127.0.0.1.1.1'))
        port = args.port if args.port is not None else base_cfg.get('ads_port', 851)
        print(f'Configuration source: {cfg_path}')
        print('IMPORTANT: Start the correct TwinCAT usermode runtime FIRST and set TwinCAT to RUN.')
        print('In UMRT console, look for: AmsNetId: <six numbers>.')
        if not args.no_prompt and not args.check_only:
            net_id = prompt_with_default('Target runtime AMS Net ID', net_id)
            port = prompt_with_default('PLC ADS port', str(port))
        cfg = merged_config(base_cfg, net_id, validate_ads_port(port))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f'[ERROR] Invalid configuration: {exc}')
        return 2

    if not check_ads(cfg):
        print('No launch. Fix the connection and retry. You may still use start_demo.cmd.')
        return 1
    if args.check_only:
        return 0
    if not args.no_prompt:
        answer = input('Launch the PLC Simulator LIVE now? [Y/n]: ').strip().lower()
        if answer not in ('', 'y', 'yes'):
            print('Live launch canceled; ADS diagnostic passed.')
            return 0
    return launch_live(cfg)


if __name__ == '__main__':
    raise SystemExit(main())
