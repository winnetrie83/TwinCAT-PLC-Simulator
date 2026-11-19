"""New module tests. Run: py -3 -m unittest discover -s tests -p test_v05_garage.py -v"""
import sys
import time
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.garage import GarageController, GarageSettings, GarageService
from backend.model import ConveyorWorld, DIVERTER_X, REJECT_SENSOR_Y

class GarageTests(unittest.TestCase):
    def test_demo_open_and_close(self):
        c=GarageController(GarageSettings('127.0.0.1.1.1'),demo=True)
        c.connect()
        data={'button':True,'limit_open':False,'limit_closed':True}
        self.assertTrue(c.exchange(data)['motor_open'])
        data['button']=False
        c.exchange(data)
        data['limit_closed']=False
        data['limit_open']=True
        self.assertFalse(c.exchange(data)['motor_open'])
        data['button']=True
        self.assertTrue(c.exchange(data)['motor_close'])
        data['limit_open']=False
        data['limit_closed']=True
        self.assertFalse(c.exchange(data)['motor_close'])
        c.disconnect()

    def test_pulse_and_initial_limit(self):
        svc=GarageService(GarageSettings('127.0.0.1.1.1',pulse_ms=150),demo=True)
        self.assertTrue(svc.connect()['inputs']['limit_closed'])
        self.assertTrue(svc.press_button()['inputs']['button'])
        time.sleep(.2)
        state=svc.get_state()
        self.assertGreater(state['position'],0)
        self.assertFalse(state['inputs']['button'])
        svc.disconnect()
        self.assertFalse(svc.get_state()['connected'])

    def test_both_motors_halt_physics(self):
        svc=GarageService(GarageSettings('127.0.0.1.1.1'),demo=True)
        svc.outputs['motor_open']=True
        svc.outputs['motor_close']=True
        svc.connect()
        # Service reset is intentional; test direct collision logic is inside worker.
        svc.outputs['motor_open']=True
        svc.outputs['motor_close']=True
        time.sleep(.03)
        self.assertTrue(svc.get_state()['conflict'])
        self.assertEqual(svc.get_state()['position'],0)
        svc.disconnect()

class RejectGeometryTests(unittest.TestCase):
    def test_diverter_shifts_left_and_detects(self):
        self.assertAlmostEqual(DIVERTER_X,.66)
        w=ConveyorWorld()
        w.enqueue('reject')
        w.step(0,False,False)
        for _ in range(250):
            w.step(.02,True,True)
            if w.packages and w.packages[0].lane=='reject':break
        p=w.packages[0]
        self.assertEqual(p.lane,'reject')
        self.assertAlmostEqual(p.x,DIVERTER_X)
        for _ in range(250):
            w.step(.02,True,True)
            if w.inputs()['sensor_reject']:break
        self.assertTrue(w.inputs()['sensor_reject'])
        self.assertAlmostEqual(p.x,DIVERTER_X)

if __name__=='__main__':unittest.main()
