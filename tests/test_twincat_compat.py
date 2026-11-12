"""No TwinCAT installation required: run `py -3 -m unittest discover -s tests`."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock

SOURCE = Path(__file__).resolve().parents[1] / 'tools' / 'twincat_compat.py'
spec = importlib.util.spec_from_file_location('twincat_compat', SOURCE)
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)


class FakeConnection:
    def __init__(self, net_id, port, state=5):
        self.net_id = net_id
        self.port = port
        self.ads_state = state
        self.closed = False
        self.reads = []
        self.writes = []

    def open(self):
        pass

    def read_state(self):
        return self.ads_state, 0

    def read_by_name(self, name, plc_type=None):
        self.reads.append((name, plc_type))
        return 4 if name.endswith('CycleCounter') else True

    def write_by_name(self, *args):
        self.writes.append(args)
        raise AssertionError('Diagnostics must not write to the PLC')

    def close(self):
        self.closed = True


class RuntimeCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            'ams_net_id': '127.0.0.1.1.1', 'ads_port': 851,
            'pulse_ms': 250, 'another_future_setting': {'nested': True},
            'symbols': {'start': 'MAIN.bStartButton', 'motor': 'MAIN.bConveyorMotor',
                        'counter': 'MAIN.nCycleCounter',
                        'sensor_diverter': 'MAIN.bSensorDiverter'},
        }

    def test_ams_net_id_validation(self):
        self.assertEqual(compat.validate_net_id('199.4.42.250.1.1'), '199.4.42.250.1.1')
        for value in ('localhost', '127.0.0.1', '256.0.0.1.1.1', '1.2.3.4.5.6.7', ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                compat.validate_net_id(value)

    def test_ads_port_validation(self):
        self.assertEqual(compat.validate_ads_port('851'), 851)
        self.assertEqual(compat.validate_ads_port('852'), 852)
        for value in (0, -5, 65536, 'abc'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                compat.validate_ads_port(value)

    def test_merge_does_not_discard_phase3_or_future_fields(self):
        cfg = compat.merged_config(self.config, '199.4.42.250.1.1', 852)
        self.assertEqual(cfg['ams_net_id'], '199.4.42.250.1.1')
        self.assertEqual(cfg['ads_port'], 852)
        self.assertIn('sensor_diverter', cfg['symbols'])
        self.assertEqual(cfg['another_future_setting'], {'nested': True})
        self.assertEqual(self.config['ads_port'], 851)

    def test_check_is_read_only_and_closes_connection(self):
        conn = FakeConnection('199.4.42.250.1.1', 851)
        pyads = MagicMock()
        pyads.Connection.return_value = conn
        pyads.PLCTYPE_BOOL = 'BOOL'
        pyads.PLCTYPE_UDINT = 'UDINT'
        output = []
        self.assertTrue(compat.check_ads(compat.merged_config(self.config, conn.net_id, 851), pyads, output.append))
        self.assertTrue(conn.closed)
        self.assertFalse(conn.writes)
        self.assertEqual(len(conn.reads), len(self.config['symbols']))
        self.assertIn(('MAIN.nCycleCounter', 'UDINT'), conn.reads)
        self.assertTrue(any('[PASS]' in item for item in output))

    def test_stopped_runtime_fails_closed(self):
        conn = FakeConnection('127.0.0.1.1.1', 851, state=4)
        pyads = MagicMock()
        pyads.Connection.return_value = conn
        self.assertFalse(compat.check_ads(self.config, pyads, lambda *_: None))
        self.assertTrue(conn.closed)

    def test_read_failure_fails_closed(self):
        conn = FakeConnection('127.0.0.1.1.1', 851)
        conn.read_by_name = MagicMock(side_effect=RuntimeError('symbol not found'))
        pyads = MagicMock()
        pyads.Connection.return_value = conn
        self.assertFalse(compat.check_ads(self.config, pyads, lambda *_: None))
        self.assertTrue(conn.closed)

    def test_launcher_writes_temporary_config_only(self):
        captures = []
        def fake_runner(command, cwd=None, check=False):
            config_arg = Path(command[command.index('--config') + 1])
            captures.append((json.loads(config_arg.read_text(encoding='utf-8')), cwd))
            return type('Result', (), {'returncode': 0})()
        config = compat.merged_config(self.config, '199.4.42.250.1.1', 851)
        self.assertEqual(compat.launch_live(config, runner=fake_runner), 0)
        self.assertEqual(captures[0][0]['ams_net_id'], '199.4.42.250.1.1')
        self.assertEqual(captures[0][0]['symbols'], self.config['symbols'])
        self.assertEqual(captures[0][1], compat.ROOT)


if __name__ == '__main__':
    unittest.main()
