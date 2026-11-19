import sys, types, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.plc import AdsController, Settings, DEFAULT_SYMBOLS, INPUT_KEYS
from backend.garage import GarageController, GarageSettings, GARAGE_SYMBOLS
from backend.symbols import is_missing_symbol
class Missing(Exception):
    err_code=1808
    def __str__(self): return 'ADSError: symbol not found (1808)'
class Sym:
    def __init__(self,name):self.name=name
class Fake:
    missing=set(); broken=set(); no_list=False; last=None
    def __init__(self,*args):
        self.writes=[];self.data={n:False for n in list(DEFAULT_SYMBOLS.values())+list(GARAGE_SYMBOLS.values())}
        self.data.update({'MAIN.nCycleCounter':0,'MAIN.nGateCycleCounter':0,'MAIN.bUnused':True});Fake.last=self
    def open(self):pass
    def close(self):pass
    def read_by_name(self,name,typ):
        if name in self.broken:raise RuntimeError('route lost')
        if name in self.missing:raise Missing()
        return self.data[name]
    def write_by_name(self,name,value,typ):
        if name in self.missing:raise AssertionError('missing symbol written')
        self.writes.append((name,value))
    def get_all_symbols(self):
        if self.no_list:raise RuntimeError('unavailable')
        return [Sym(k) for k in self.data if k not in self.missing]
class SymbolTests(unittest.TestCase):
    def setUp(self):
        Fake.missing=set();Fake.broken=set();Fake.no_list=False
        self.p=patch.dict(sys.modules,{'pyads':types.SimpleNamespace(Connection=Fake,PLCTYPE_BOOL=object(),PLCTYPE_UDINT=object())});self.p.start()
    def tearDown(self):self.p.stop()
    def test_conveyor_optional_missing(self):
        Fake.missing={'MAIN.bSensorReject','MAIN.bConveyorMotor'}
        c=AdsController(Settings('1.2.3.4.1.1',851,250,dict(DEFAULT_SYMBOLS)));c.connect()
        self.assertFalse(c.available['sensor_reject']);self.assertFalse(c.available['motor'])
        self.assertEqual(c.exchange(dict.fromkeys(INPUT_KEYS,False))['motor'],False)
        self.assertNotIn('MAIN.bSensorReject',[n for n,v in Fake.last.writes]);self.assertIn('MAIN.bUnused',c.extra_symbols)
        c.disconnect()
    def test_garage_optional_missing(self):
        Fake.missing={'MAIN.bGateLimitOpen','MAIN.bGateMotorClose'}
        c=GarageController(GarageSettings('1.2.3.4.1.1',851,250,dict(GARAGE_SYMBOLS)),False);c.connect()
        self.assertFalse(c.available['limit_open']);self.assertFalse(c.exchange({'button':False,'limit_open':False,'limit_closed':True})['motor_close'])
        self.assertNotIn('MAIN.bGateLimitOpen',[n for n,v in Fake.last.writes]);c.disconnect()
    def test_unavailable_inventory(self):
        Fake.no_list=True;c=AdsController(Settings('1.2.3.4.1.1',851,250,dict(DEFAULT_SYMBOLS)));c.connect()
        self.assertEqual(c.inventory_status,'unavailable');c.disconnect()
    def test_real_failure_still_fails(self):
        Fake.broken={'MAIN.bGateButton'}
        c=GarageController(GarageSettings('1.2.3.4.1.1',851,250,dict(GARAGE_SYMBOLS)),False)
        with self.assertRaises(RuntimeError):c.connect()
    def test_error_classification(self):
        self.assertTrue(is_missing_symbol(Missing()));self.assertFalse(is_missing_symbol(RuntimeError('server down (6)')))
if __name__=='__main__':unittest.main()
