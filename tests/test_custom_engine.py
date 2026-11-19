"""Regression tests for v0.9 modular conveyor / generator / sensor / ADS adapter."""
import copy
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.custom_engine import CustomEngine, CustomService, ProjectError, default_project, validate_project, belt_point


def minimal():
    p = default_project()
    p['components'] = [c for c in p['components'] if c['type'] in ('conveyor', 'sensor', 'source', 'sink')]
    return p


class TestCustomEngine(unittest.TestCase):
    def test_default_and_old_project_supported(self):
        self.assertEqual(len(validate_project(default_project())['components']), 6)
        old = {'version': 1, 'name': 'Old project', 'components': [
            {'id': 'oldbelt', 'type': 'conveyor', 'x': 100, 'y': 200, 'settings': {'length': 200, 'speed': 80}, 'plc': {'motor': ''}},
            {'id': 'oldbox', 'type': 'package', 'x': 100, 'y': 200, 'settings': {}, 'plc': {}}]}
        e = CustomEngine(old)
        self.assertEqual(len(e.parcels), 1)
        self.assertEqual(e.belts[0]['settings']['rotation'], 0)

    def test_duplicate_id_rejected(self):
        p = default_project();p['components'].append(copy.deepcopy(p['components'][0]))
        with self.assertRaises(ProjectError): validate_project(p)

    def test_duplicate_plc_symbol_rejected(self):
        p = default_project();p['components'][1]['plc']['detected'] = 'MAIN.bCustomMotor'
        with self.assertRaises(ProjectError):validate_project(p)

    def test_bad_pattern_rejected(self):
        p = default_project();next(c for c in p['components'] if c['type'] == 'source')['settings']['pattern'] = 'pink'
        with self.assertRaises(ProjectError): validate_project(p)

    def test_nonfinite_position_rejected(self):
        p = default_project();p['components'][0]['x'] = float('nan')
        with self.assertRaises(ProjectError):validate_project(p)

    def test_package_moves_and_stops(self):
        p = minimal();p['components'] = [c for c in p['components'] if c['type'] == 'conveyor']
        p['components'].append({'id': 'box', 'type': 'package', 'x': 200, 'y': 300, 'settings': {}, 'plc': {}})
        e = CustomEngine(p);before = e.parcels[0]['pos']
        e.step(.1, {('belt1', 'motor'): True});self.assertGreater(e.parcels[0]['pos'], before)
        e.step(.1, {('belt1', 'motor'): False});at = e.parcels[0]['pos']
        e.step(.1, {('belt1', 'motor'): False});self.assertEqual(e.parcels[0]['pos'], at)

    def test_sensor_next_to_belt(self):
        p = minimal();p['components'] = [c for c in p['components'] if c['type'] in ('conveyor', 'sensor')]
        p['components'].append({'id': 'box', 'type': 'package', 'x': 370, 'y': 300, 'settings': {}, 'plc': {}})
        e = CustomEngine(p)
        self.assertTrue(e.inputs()[('sensor1', 'detected')])
        e.parcels[0]['pos'] = 0
        self.assertFalse(e.inputs()[('sensor1', 'detected')])

    def test_pattern_source_and_collector(self):
        e = CustomEngine(minimal())
        outputs = {('belt1', 'motor'): True}
        # Keep stepping for > 9s to generate and collect multiple packages.
        for _ in range(1000):e.step(.02, outputs)
        self.assertGreaterEqual(e.generated, 6)
        self.assertGreaterEqual(e.collected['sink1'], 2)
        self.assertEqual(e.source_index['source1'], e.generated)

    def test_source_modes(self):
        for mode in ('fixed', 'random', 'pattern'):
            p = minimal();source = next(c for c in p['components'] if c['type'] == 'source')
            source['settings'].update({'mode': mode, 'color': 'red', 'interval': .2, 'pattern': 'green,orange'})
            e=CustomEngine(p)
            for _ in range(15):e.step(.1,{('belt1','motor'):True})
            self.assertGreaterEqual(e.generated, 1)
            self.assertTrue(all(p['color'] in ('red',) if mode=='fixed' else p['color'] in ('green','orange') if mode=='pattern' else p['color'] in ('blue','orange','green','red','yellow','purple') for p in e.parcels))

    def test_capacity_full_and_empty(self):
        p=minimal();next(c for c in p['components'] if c['type']=='sink')['settings']['capacity']=1
        e=CustomEngine(p)
        for _ in range(400):e.step(.05,{('belt1','motor'):True})
        self.assertEqual(e.collected['sink1'],1)
        self.assertTrue(e.inputs()[('sink1','full')])
        self.assertTrue(e.parcels)
        e.empty_sink('sink1')
        self.assertFalse(e.inputs()[('sink1','full')])

    def test_second_belt_transfer_rotated(self):
        p=minimal();p['components']=[c for c in p['components'] if c['type']=='conveyor']
        p['components'][0]['settings']['length']=100
        p['components'].append({'id':'belt2','type':'conveyor','x':285,'y':300,'settings':{'length':110,'speed':85,'rotation':90},'plc':{'motor':''}})
        p['components'].append({'id':'box','type':'package','x':185,'y':300,'settings':{},'plc':{}})
        e=CustomEngine(p)
        for _ in range(120):e.step(.02,{('belt1','motor'):True,('belt2','motor'):True})
        self.assertEqual(e.parcels[0]['belt'],'belt2')
        self.assertGreaterEqual(e.parcels[0]['pos'],0)
        self.assertEqual(belt_point(e.belts[1],20),(285,320))

    def test_button_and_release(self):
        e=CustomEngine();e.press('button1',True);self.assertTrue(e.inputs()[('button1','pressed')])
        e.press('button1',False);self.assertFalse(e.inputs()[('button1','pressed')])

    def test_save_load(self):
        with tempfile.TemporaryDirectory() as temp:
            s=CustomService('1.2.3.4.1.1',851,True);s.storage=Path(temp)
            s.save('example');self.assertEqual(s.list_projects(),['example'])
            s.engine.project['name']='changed';self.assertEqual(s.open('example')['project']['name'],'Mijn eerste installatie')

    def test_demo_start_stop(self):
        s=CustomService('1.2.3.4.1.1',851,True)
        try:
            self.assertTrue(s.connect()['connected'])
            s.press('button1',True);time.sleep(.12);s.press('button1',False);time.sleep(.11)
            self.assertTrue(s.get_state()['values']['belt1']['motor'])
            s.press('button1',True);time.sleep(.12);s.press('button1',False);time.sleep(.11)
            self.assertFalse(s.get_state()['values']['belt1']['motor'])
        finally:s.disconnect()

    def test_fake_ads_roundtrip(self):
        class Sym:
            def __init__(self,name):self.name=name
        class FakeADS:
            writes=[]
            def __init__(self,*args):self.symbols={name:False for name in ['MAIN.bCustomMotor','MAIN.bCustomLamp','MAIN.bCustomSensor','MAIN.bCustomButton']}
            def open(self):pass
            def close(self):pass
            def get_all_symbols(self):return [Sym(name) for name in self.symbols]
            def read_by_name(self,name,typ):return self.symbols[name]
            def write_by_name(self,name,value,typ):self.writes.append((name,value))
        with patch.dict(sys.modules, {'pyads':types.SimpleNamespace(Connection=FakeADS,PLCTYPE_BOOL=object())}):
            s=CustomService('1.2.3.4.1.1',851,False)
            try:
                self.assertTrue(s.connect()['connected'],s.get_state()['error'])
                s.press('button1',True);time.sleep(.12)
                self.assertIn(('MAIN.bCustomButton',True),FakeADS.writes)
            finally:s.disconnect()

if __name__=='__main__':unittest.main()
