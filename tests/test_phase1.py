"""Offline regression tests for Phase 1 (no TwinCAT installation required)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import load_settings, JsApi
from backend.plc import AdsPLC, PlcError, PlcService, Settings


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.svc = PlcService(Settings(pulse_ms=100), demo=True)
        state = self.svc.connect()
        self.assertTrue(state['connected'])

    def tearDown(self):
        self.svc.disconnect()

    def test_start_stop(self):
        result = self.svc.pulse('start')
        self.assertTrue(result['values']['motor'])
        self.assertFalse(result['values']['start'])
        result = self.svc.pulse('stop')
        self.assertFalse(result['values']['motor'])
        self.assertFalse(result['values']['stop'])

    def test_sensor_has_priority(self):
        self.svc.pulse('start')
        self.assertTrue(self.svc.set_sensor(True)['values']['sensor'])
        self.assertFalse(self.svc.get_state()['values']['motor'])
        self.svc.pulse('start')
        self.assertFalse(self.svc.get_state()['values']['motor'])
        self.svc.set_sensor(False)
        self.assertFalse(self.svc.get_state()['values']['motor'])
        self.svc.pulse('start')
        self.assertTrue(self.svc.get_state()['values']['motor'])

    def test_cycle_counter_moves(self):
        a = self.svc.get_state()['values']['counter']
        b = self.svc.get_state()['values']['counter']
        self.assertGreater(b, a)

    def test_disconnect(self):
        self.svc.disconnect()
        self.assertFalse(self.svc.get_state()['connected'])
        self.assertIn('Niet verbonden', self.svc.pulse('start')['error'])

    def test_js_api(self):
        api = JsApi(self.svc)
        self.assertTrue(api.press_start()['values']['motor'])
        self.assertFalse(api.set_sensor(True)['values']['motor'])


class SettingsTests(unittest.TestCase):
    def test_reads_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'settings.json'
            file.write_text(json.dumps({
                'ams_net_id': '1.2.3.4.1.1', 'ads_port': 852, 'pulse_ms': 200,
                'symbols': {name: 'MAIN.' + name for name in ('start','stop','sensor','motor','counter')}
            }), encoding='utf-8')
            cfg = load_settings(file)
            self.assertEqual(cfg.ams_net_id, '1.2.3.4.1.1')
            self.assertEqual(cfg.symbol('motor'), 'MAIN.motor')

    def test_rejects_missing_symbol(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'settings.json'
            file.write_text('{"symbols": {}}', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_settings(file)


class FakeConnection:
    instances = []

    def __init__(self, netid, port):
        self.netid = netid
        self.port = port
        self.is_open = False
        self.vars = {
            'MAIN.bStartButton': False,
            'MAIN.bStopButton': False,
            'MAIN.bSensor': False,
            'MAIN.bMotor': False,
            'MAIN.nCycleCounter': 42,
        }
        self.__class__.instances.append(self)

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False

    def read_by_name(self, symbol, data_type):
        return self.vars[symbol]

    def write_by_name(self, symbol, value, data_type):
        self.vars[symbol] = value


class AdsAdapterTests(unittest.TestCase):
    def setUp(self):
        self.fake_pyads = types.SimpleNamespace(
            Connection=FakeConnection,
            PLCTYPE_BOOL=object(),
            PLCTYPE_UDINT=object(),
        )
        self.patcher = patch.dict(sys.modules, {'pyads': self.fake_pyads})
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_real_adapter_reads_and_writes_with_correct_symbols(self):
        backend = AdsPLC(Settings())
        backend.connect()
        self.assertEqual(backend.read()['counter'], 42)
        backend.write_bool('sensor', True)
        self.assertTrue(backend.read()['sensor'])
        self.assertEqual(backend.connection.port, 851)
        with self.assertRaises(PlcError):
            backend.write_bool('motor', True)
        fake = backend.connection
        backend.disconnect()
        self.assertFalse(fake.is_open)

    def test_missing_symbol_does_not_silently_connect(self):
        backend = AdsPLC(Settings(symbols={'motor':'MAIN.niet_bestaand'}))
        with self.assertRaises(PlcError):
            backend.connect()
        self.assertIsNone(backend.connection)


if __name__ == '__main__':
    unittest.main()
