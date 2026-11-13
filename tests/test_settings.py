import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import settings


class SettingsTests(unittest.TestCase):
    def test_migrate_old_settings_and_save_profile(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(settings, 'PATH', Path(tmp)/'settings.json'):
            settings.PATH.write_text(json.dumps({'camera': 2, 'pinch': .5, 'mirror': False}), encoding='utf-8')
            initial = settings.read_store()
            self.assertEqual(initial['profiles']['Основной']['camera'], 2)
            self.assertEqual(initial['profiles']['Основной']['pinch'], .5)
            settings.save(initial['profiles']['Основной'])
            stored = settings.read_store()
            self.assertEqual(stored['selected'], 'Основной')
            self.assertFalse(stored['profiles']['Основной']['mirror'])

    def test_invalid_values_fall_back(self):
        data=settings.validate({'camera': -1, 'bounds': [0,0,.01,.01], 'bindings': {'ring':'invalid'}})
        self.assertEqual(data['camera'], 0); self.assertIsNone(data['bounds'])
        self.assertEqual(data['bindings']['ring'], 'Прокрутка')

if __name__ == '__main__': unittest.main()
