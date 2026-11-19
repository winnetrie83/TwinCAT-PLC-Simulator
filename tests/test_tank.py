import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.pressure import TankWorld,TankController,TankSettings,TankService,SYMBOLS

class PlantTests(unittest.TestCase):
    def test_initial_conditions(self):
        w=TankWorld();self.assertEqual(w.level,35.0);self.assertFalse(w.inputs()['level_low'])
        self.assertFalse(w.inputs()['level_high']);self.assertAlmostEqual(w.pressure,88)
    def test_pumps(self):
        w=TankWorld();w.step(.1,True,False);self.assertAlmostEqual(w.level,36)
        w.step(.1,False,True);self.assertAlmostEqual(w.level,35.3)
    def test_thresholds(self):
        w=TankWorld();w.level=20;self.assertTrue(w.inputs()['level_low'])
        w.level=85;self.assertTrue(w.inputs()['level_high']);self.assertFalse(w.inputs()['pressure_high'])
        w.level=90;self.assertTrue(w.inputs()['pressure_high'])
    def test_clamps(self):
        w=TankWorld();w.level=99.9;w.step(.1,True,False)
        self.assertEqual(w.level,100);self.assertTrue(w.snapshot()['overflow'])
        w.level=0;w.step(.1,False,True);self.assertEqual(w.level,0)
    def test_demo_plc_toggles_on_rising_edge(self):
        ctl=TankController(TankSettings('1.2.3.4.1.1',851),demo=True);ctl.connect()
        base={'start':False,'stop':False,'level_low':False,'level_high':False,'pressure_high':False,'pressure':80.0}
        self.assertFalse(ctl.exchange(base)['pump_in'])
        base['start']=True;self.assertTrue(ctl.exchange(base)['pump_in'])
        self.assertTrue(ctl.exchange(base)['pump_in'])
        base['start']=False;ctl.exchange(base);base['start']=True
        self.assertFalse(ctl.exchange(base)['pump_in'])
        ctl.disconnect()
    def test_80_percent_demo_holds_exactly(self):
        w=TankWorld();c=TankController(TankSettings('1.2.3.4.1.1',851),demo=True)
        c.connect()
        inputs=lambda: {**w.inputs(),'start':False,'stop':False}
        c.exchange(inputs())
        started=inputs();started['start']=True
        outputs=c.exchange(started)
        self.assertTrue(outputs['pump_in'])
        for _ in range(80):
            w.step(.1,outputs['pump_in'],outputs['pump_out'],demo_limits=True)
            outputs=c.exchange(inputs())
        self.assertEqual(w.level,80.0)
        self.assertFalse(outputs['pump_in'])
        self.assertFalse(outputs['pump_out'])
        self.assertFalse(w.inputs()['pressure_high'])
    def test_demo_auto_cycles_between_limits(self):
        w=TankWorld();c=TankController(TankSettings('1.2.3.4.1.1',851),demo=True)
        c.demo_cycle=True;c.connect()
        x={**w.inputs(),'start':True,'stop':False};outputs=c.exchange(x)
        for _ in range(85):
            w.step(.1,outputs['pump_in'],outputs['pump_out'],demo_limits=True)
            outputs=c.exchange({**w.inputs(),'start':False,'stop':False})
        self.assertLess(w.level,80)
        self.assertTrue(outputs['pump_out'])
        for _ in range(85):
            w.step(.1,outputs['pump_in'],outputs['pump_out'],demo_limits=True)
            outputs=c.exchange({**w.inputs(),'start':False,'stop':False})
        self.assertGreaterEqual(w.level,25)
    def test_simultaneous_pumps_do_not_move_liquid(self):
        w=TankWorld();before=w.level
        w.step(.1,True,True)
        self.assertEqual(w.level,before)
    def test_live_not_clamped_at_80(self):
        w=TankWorld();w.level=79.9
        w.step(.1,True,False)
        self.assertGreater(w.level,80)
    def test_demo_cycle_setting_only_in_demo(self):
        s=TankService(TankSettings('1.2.3.4.1.1',851),demo=True)
        self.assertFalse(s.set_demo_cycle(False)['demo_cycle'])
        self.assertTrue(s.set_demo_cycle(True)['demo_cycle'])
        live=TankService(TankSettings('1.2.3.4.1.1',851),demo=False)
        with self.assertRaises(ValueError):live.set_demo_cycle(True)
    def test_controller_missing_ads_symbol(self):
        class FakeAds:
            PLCTYPE_BOOL='BOOL';PLCTYPE_REAL='REAL'
            class Connection:
                def __init__(self,*args):self.data={n:False for n in SYMBOLS.values() if n!='MAIN.bPumpOut'}
                def open(self):pass
                def close(self):pass
                def read_by_name(self,n,t):
                    if n not in self.data:
                        exc=Exception('symbol not found 1808');exc.err_code=1808;raise exc
                    return self.data[n]
                def get_all_symbols(self):return []
                def write_by_name(self,n,value,t):self.data[n]=value
        from unittest.mock import patch
        with patch.dict(sys.modules,{'pyads':FakeAds}):
            c=TankController(TankSettings('1.2.3.4.1.1',851));c.connect()
            self.assertFalse(c.available['pump_out'])
            self.assertEqual(c.exchange({'start':False,'stop':False,'level_low':False,'level_high':False,'pressure_high':False,'pressure':90.0})['pump_out'],False)
            c.disconnect()
    def test_service_connect_disconnect(self):
        s=TankService(TankSettings('1.2.3.4.1.1',851),demo=True)
        self.assertTrue(s.connect()['connected'])
        self.assertTrue(s.pulse('start')['signals']['start'])
        self.assertFalse(s.disconnect()['connected'])

if __name__=='__main__':unittest.main()
