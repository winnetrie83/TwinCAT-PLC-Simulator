"""Tests of persistent fixed-lesson mappings and observable PLC test runner."""
import sys, tempfile, time, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.io_mapping import MappingStore, MappingError
from backend.exercise_tests import ExerciseTestRunner

DEFAULT={'conveyor':{'motor':'MAIN.bMotor','start':'MAIN.bStart'},'garage':{'button':'MAIN.bButton','motor_open':'MAIN.bOpen'},'tank':{'pump_in':'MAIN.bPumpIn','pressure':'MAIN.rPressure'}}

class MappingTests(unittest.TestCase):
    def test_persistence_and_default_reset(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'io.json';store=MappingStore(DEFAULT,path)
            edited={'motor':'MAIN.bMyMotor','start':'MAIN.bMyStart'}
            result=store.save('conveyor',edited)
            self.assertEqual(result['mappings']['conveyor'],edited)
            self.assertEqual(MappingStore(DEFAULT,path).snapshot()['mappings']['conveyor'],edited)
            store.save('conveyor',store.defaults['conveyor'])
            self.assertEqual(MappingStore(DEFAULT,path).snapshot()['mappings']['conveyor'],DEFAULT['conveyor'])
    def test_duplicate_is_rejected_without_changing_storage(self):
        with tempfile.TemporaryDirectory() as root:
            store=MappingStore(DEFAULT,Path(root)/'io.json')
            with self.assertRaises(MappingError):store.save('conveyor',{'motor':'MAIN.same','start':'MAIN.SAME'})
            self.assertEqual(store.snapshot()['mappings']['conveyor'],DEFAULT['conveyor'])
    def test_incorrect_ports_or_symbol_names(self):
        with tempfile.TemporaryDirectory() as root:
            store=MappingStore(DEFAULT,Path(root)/'io.json')
            for data in ({'motor':'MAIN.motor'}, {'motor':'motor','start':''},{'motor':'bad space','start':'MAIN.start'}):
                with self.assertRaises(MappingError):store.save('conveyor',data)

class FakeConveyor:
    def __init__(self,started=True):self.connected=started;self.motor=False;self.actions=[]
    def get_state(self):return {'connected':self.connected,'outputs':{'motor':self.motor}}
    def pulse(self,cmd):self.actions.append(cmd);self.motor=(cmd=='start')

class FakeTank:
    def __init__(self):self.connected=True;self.level=35;self.fill=False
    def get_state(self):
        if self.fill and self.level<80:self.level=min(80,self.level+6)
        if self.level>=80:self.fill=False
        return {'connected':self.connected,'demo':True,'demo_cycle':False,'world':{'level':self.level},'signals':{'pump_in':self.fill,'pump_out':False},'pump_conflict':False}
    def pulse(self,cmd):self.fill=cmd=='start'
    def set_demo_cycle(self,value):pass

class RunnerTests(unittest.TestCase):
    def test_cannot_start_unconnected(self):
        r=ExerciseTestRunner({'conveyor':FakeConveyor(False)})
        with self.assertRaises(ValueError):r.start('conveyor')
    def test_conveyor_starts_and_stops(self):
        c=FakeConveyor();r=ExerciseTestRunner({'conveyor':c})
        r.start('conveyor');r.worker.join(4)
        status=r.snapshot();self.assertFalse(status['running'])
        self.assertEqual(len(status['results']),2)
        self.assertTrue(all(x['passed'] for x in status['results']))
        self.assertFalse(c.motor)
    def test_tank_scenario(self):
        c=FakeTank();r=ExerciseTestRunner({'tank':c});r.start('tank');r.worker.join(4)
        results=r.snapshot()['results']
        self.assertGreaterEqual(len(results),3)
        self.assertTrue(all(r['passed'] for r in results))

if __name__=='__main__':unittest.main()
