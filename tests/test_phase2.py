"""Run from project root: python -m unittest discover -s tests -v"""
import json
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import JsApi, load_settings
from backend.model import ConveyorWorld, ENTRY_X, EXIT_X, DIVERTER_X
from backend.plc import AdsController, DemoController, INPUT_KEYS, OUTPUT_KEYS, DEFAULT_SYMBOLS, PlcError, Settings
from backend.service import SimulatorService


def settings():
    return Settings('127.0.0.1.1.1', 851, 150, dict(DEFAULT_SYMBOLS))


class PhysicsTests(unittest.TestCase):
    def test_package_does_not_move_if_motor_stopped(self):
        w = ConveyorWorld()
        w.enqueue('standard')
        w.step(0.02, False, False)
        initial = w.packages[0].x
        for _ in range(20): w.step(0.02, False, False)
        self.assertEqual(w.packages[0].x, initial)

    def test_entry_sensor_and_reject_type(self):
        w = ConveyorWorld()
        w.enqueue('reject')
        w.step(0, False, False)
        p = w.packages[0]
        p.x = ENTRY_X
        self.assertTrue(w.inputs()['sensor_entry'])
        self.assertTrue(w.inputs()['reject_type'])
        self.assertFalse(w.inputs()['sensor_exit'])
        p.x = EXIT_X
        self.assertFalse(w.inputs()['sensor_entry'])
        self.assertTrue(w.inputs()['sensor_exit'])
        self.assertFalse(w.inputs()['reject_type'])

    def test_blue_package_exits_straight(self):
        w = ConveyorWorld()
        w.enqueue('standard')
        for _ in range(600): w.step(0.02, True, False)
        self.assertEqual(w.normal_count, 1)
        self.assertEqual(w.reject_count, 0)
        self.assertEqual(w.packages, [])

    def test_orange_requires_plc_diverter(self):
        w = ConveyorWorld()
        w.enqueue('reject')
        for _ in range(600): w.step(0.02, True, False)
        self.assertEqual(w.normal_count, 1, 'Without PLC output, even orange should go straight')
        w.reset()
        w.enqueue('reject')
        for _ in range(600): w.step(0.02, True, True)
        self.assertEqual(w.reject_count, 1)
        self.assertEqual(w.normal_count, 0)

    def test_only_one_package_on_belt(self):
        w = ConveyorWorld()
        for _ in range(3): w.enqueue('standard')
        for _ in range(200):
            w.step(.02, True, False)
            self.assertLessEqual(len(w.packages), 1)

    def test_end_to_end_demo_sorting_is_controlled_by_outputs(self):
        world = ConveyorWorld()
        controller = DemoController()
        controller.connect()
        world.enqueue('standard')
        world.enqueue('reject')
        values = controller.exchange({'start': True, 'stop': False, **world.inputs()})
        for i in range(1600):
            world.step(0.02, values['motor'], values['diverter'])
            if i % 3 == 0:
                values = controller.exchange({'start': False, 'stop': False, **world.inputs()})
        self.assertEqual(world.normal_count, 1)
        self.assertEqual(world.reject_count, 1)
        controller.disconnect()

    def test_reject_invalid_type_and_max_queue(self):
        w = ConveyorWorld()
        with self.assertRaises(ValueError): w.enqueue('anything')
        for _ in range(24): w.enqueue('standard')
        with self.assertRaises(ValueError): w.enqueue('standard')

    def test_dt_is_clamped(self):
        w = ConveyorWorld()
        w.enqueue('standard')
        w.step(0, False, False)
        w.step(15, True, False)
        self.assertLess(w.packages[0].x, 0.1)


class DemoControllerTests(unittest.TestCase):
    def test_start_stop_and_sort(self):
        c = DemoController()
        c.connect()
        inp = dict.fromkeys(INPUT_KEYS, False)
        inp['start'] = True
        self.assertTrue(c.exchange(inp)['motor'])
        inp['start'] = False
        inp['sensor_entry'] = True
        inp['reject_type'] = True
        self.assertTrue(c.exchange(inp)['diverter'])
        inp['sensor_entry'] = False
        inp['sensor_exit'] = True
        self.assertFalse(c.exchange(inp)['diverter'])
        inp['stop'] = True
        self.assertFalse(c.exchange(inp)['motor'])
        c.disconnect()


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.svc = SimulatorService(settings(), demo=True)
        self.svc.connect()

    def tearDown(self):
        self.svc.disconnect()

    def test_nonblocking_start_pulse(self):
        t0 = time.perf_counter()
        state = self.svc.pulse('start')
        self.assertLess(time.perf_counter() - t0, 0.08)
        self.assertTrue(state['inputs']['start'])
        time.sleep(.12)
        self.assertTrue(self.svc.get_state()['outputs']['motor'])
        time.sleep(.10)
        self.assertFalse(self.svc.get_state()['inputs']['start'])
        self.assertTrue(self.svc.get_state()['outputs']['motor'])

    def test_io_sample_flow(self):
        api = JsApi(self.svc)
        self.assertTrue(api.connect()['connected'])
        self.assertEqual(api.add_package('standard')['world']['queue_count'], 3)
        self.assertTrue(api.set_auto_feed(True)['world']['auto_feed'])
        self.assertEqual(api.reset_scene()['world']['queue_count'], 0)
        self.assertFalse(api.get_state()['world']['auto_feed'])
        self.assertFalse(api.disconnect()['connected'])

    def test_stop_and_error(self):
        self.svc.pulse('start')
        time.sleep(.1)
        self.svc.pulse('stop')
        time.sleep(.1)
        self.assertFalse(self.svc.get_state()['outputs']['motor'])
        self.assertIn('Onbekend', self.svc.add_package('nonsense')['error'])


class FakeConnection:
    instances = []
    def __init__(self, netid, port):
        self.netid, self.port = netid, port
        self.vars = {symbol: (0 if key == 'counter' else False) for key,symbol in DEFAULT_SYMBOLS.items()}
        self.closed = False
        self.written = []
        self.__class__.instances.append(self)
    def open(self): pass
    def close(self): self.closed = True
    def read_by_name(self, name, typ): return self.vars[name]
    def write_by_name(self, name, value, typ):
        self.vars[name] = value
        self.written.append(name)


class AdsTests(unittest.TestCase):
    def setUp(self):
        fake = types.SimpleNamespace(Connection=FakeConnection, PLCTYPE_BOOL=object(), PLCTYPE_UDINT=object())
        self.patch = patch.dict(sys.modules, {'pyads': fake})
        self.patch.start()

    def tearDown(self): self.patch.stop()

    def test_owns_only_input_symbols(self):
        adapter = AdsController(settings())
        adapter.connect()
        ins = {key: False for key in INPUT_KEYS}
        self.assertFalse(adapter.exchange(ins)['motor'])
        ins['sensor_entry'] = True
        adapter.exchange(ins)
        self.assertEqual(adapter.connection.written.count(DEFAULT_SYMBOLS['sensor_entry']), 2)
        self.assertEqual(len(adapter.connection.written), 6)
        self.assertTrue(set(adapter.connection.written).issubset({DEFAULT_SYMBOLS[k] for k in INPUT_KEYS}))
        conn = adapter.connection
        adapter.disconnect()
        self.assertTrue(conn.closed)

    def test_missing_symbol_fails_connect(self):
        wrong = settings()
        wrong.symbols['motor'] = 'MAIN.doesNotExist'
        adapter = AdsController(wrong)
        with self.assertRaises(PlcError): adapter.connect()
        self.assertIsNone(adapter.connection)


class ConfigTests(unittest.TestCase):
    def test_real_config_valid(self):
        cfg = load_settings(Path(__file__).resolve().parents[1] / 'config/settings.json')
        self.assertEqual(cfg.ads_port, 851)
        self.assertEqual(cfg.symbol('diverter'), 'MAIN.bDiverter')

    def test_missing_symbol_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'cfg.json'
            p.write_text(json.dumps({'symbols': {'start': 'MAIN.bStartButton'}}))
            with self.assertRaises(ValueError): load_settings(p)


if __name__ == '__main__': unittest.main()
