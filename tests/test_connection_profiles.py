"""Run: py -3 -m unittest discover -s tests -p test_connection_profiles.py -v"""
import json
import tempfile
import unittest
from pathlib import Path
from backend.profiles import ProfileStore, validate

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'connections.json'
        self.store=ProfileStore('199.4.42.250.1.1',851,self.path)
    def tearDown(self): self.tmp.cleanup()

    def test_default_is_migrated_and_saved(self):
        self.assertEqual(self.store.selected()['ams_net_id'],'199.4.42.250.1.1')
        self.assertTrue(self.path.is_file())

    def test_remembers_last_used_profile(self):
        self.store.upsert(None,'School','192.168.1.22.1.1',852)
        selected=self.store.selected()['id']
        self.assertEqual(ProfileStore('127.0.0.1.1.1',851,self.path).selected()['id'],selected)
        original=self.store.profiles[0]['id']
        self.store.select(original)
        self.assertEqual(ProfileStore('127.0.0.1.1.1',851,self.path).selected()['id'],original)

    def test_edit_and_delete(self):
        self.store.upsert(None,'School','192.168.1.22.1.1',852)
        school=self.store.selected()['id']
        self.store.upsert(school,'Nieuwe school','10.20.30.40.1.1',853)
        self.assertEqual(self.store.selected()['ads_port'],853)
        self.store.delete(school)
        self.assertEqual(len(self.store.profiles),1)
        with self.assertRaises(ValueError): self.store.delete(self.store.selected_id)

    def test_validation(self):
        for netid in ('abc','127.0.0.1.1','999.0.0.1.1.1','1.2.3.4.5.6.7'):
            with self.assertRaises(ValueError): validate('Test',netid,851)
        for port in (0,65536,'abc'):
            with self.assertRaises(ValueError): validate('Test','1.2.3.4.5.6',port)
        with self.assertRaises(ValueError): validate(' ','1.2.3.4.5.6',851)

    def test_invalid_persisted_file_not_silently_destroyed(self):
        self.path.write_text('INVALID',encoding='utf-8')
        with self.assertRaises(json.JSONDecodeError): ProfileStore('1.2.3.4.5.6',851,self.path)
        self.assertEqual(self.path.read_text(encoding='utf-8'),'INVALID')

if __name__=='__main__': unittest.main()
