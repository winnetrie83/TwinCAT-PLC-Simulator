"""Run: py -3 -m unittest tests/test_reject_conveyor.py -v"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.model import ConveyorWorld, DIVERTER_X, REJECT_SENSOR_Y
from backend.plc import DemoController, INPUT_KEYS, OUTPUT_KEYS, DEFAULT_SYMBOLS

class RejectConveyorTests(unittest.TestCase):
    def test_reject_turns_90_degrees_and_triggers_arrival_sensor(self):
        world = ConveyorWorld()
        world.enqueue('reject')
        world.step(0.02, True, True)
        self.assertEqual(world.packages[0].lane, 'main')
        for _ in range(500):
            world.step(0.02, True, True)
            if world.packages and world.packages[0].lane == 'reject':
                break
        pkg = world.packages[0]
        self.assertEqual(pkg.lane, 'reject')
        self.assertEqual(pkg.x, DIVERTER_X)
        previous_x = pkg.x
        seen = False
        for _ in range(400):
            world.step(0.02, True, True)
            seen |= world.inputs()['sensor_reject']
            if world.packages:
                self.assertEqual(world.packages[0].x, previous_x,
                                 'A reject package must move vertically, not diagonally')
        self.assertTrue(seen, 'LS-03 must activate when the parcel reaches the reject belt')
        self.assertEqual(world.reject_count, 1)
        self.assertEqual(world.normal_count, 0)

    def test_reject_sensor_releases_when_package_passes(self):
        world = ConveyorWorld()
        world.enqueue('reject')
        for _ in range(350):
            world.step(0.02, True, True)
            if world.inputs()['sensor_reject']:
                break
        self.assertTrue(world.inputs()['sensor_reject'])
        for _ in range(80):
            world.step(0.02, True, True)
        self.assertFalse(world.inputs()['sensor_reject'])

    def test_blue_package_uses_main_belt(self):
        world = ConveyorWorld()
        world.enqueue('standard')
        for _ in range(600):
            world.step(.02, True, False)
        self.assertEqual(world.normal_count, 1)
        self.assertEqual(world.reject_count, 0)
        self.assertFalse(world.inputs()['sensor_reject'])

    def test_stop_freezes_reject_belt(self):
        world = ConveyorWorld()
        world.enqueue('reject')
        for _ in range(350):
            world.step(.02, True, True)
            if world.packages and world.packages[0].lane == 'reject':
                break
        y = world.packages[0].y
        for _ in range(50):
            world.step(.02, False, False)
        self.assertEqual(world.packages[0].y, y)

    def test_plc_symbol_contract(self):
        self.assertIn('sensor_reject', INPUT_KEYS)
        self.assertEqual(DEFAULT_SYMBOLS['sensor_reject'], 'MAIN.bSensorReject')
        self.assertNotIn('sensor_reject', OUTPUT_KEYS)

if __name__ == '__main__':
    unittest.main()
