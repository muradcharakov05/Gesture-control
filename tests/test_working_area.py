import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from app import settings
from app.ui import App
from app.dialogs import calibration
from app.working_area import working_area
from app.windows_input import map_point, Monitor


class FakeHotkey:
    def __init__(self, callback):
        self.registered = True
        self.ready = SimpleNamespace(wait=lambda **kwargs: None)
    def close(self): pass


class WorkingAreaTests(unittest.TestCase):
    def test_legacy_calibration_preserved(self):
        config = settings.validate({'bounds': [.1,.2,.8,.9], 'margin': .3})
        self.assertEqual(config['area_mode'], 'calibrated')
        self.assertEqual(working_area(config), (.1,.2,.8,.9))

    def test_manual_margin_changes_mapping_despite_saved_calibration(self):
        config = settings.validate({'bounds': [.1,.2,.8,.9], 'margin': .3, 'area_mode': 'manual'})
        self.assertEqual(working_area(config), (.3,.3,.7,.7))
        m=Monitor('test',0,0,1920,1080)
        self.assertNotEqual(map_point(.35,.35,working_area(config,.1),m), map_point(.35,.35,working_area(config,.3),m))


class UiRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.paths=patch.object(settings,'PATH',Path(self.temp.name)/'settings.json'); self.paths.start()
        self.hotkey=patch('app.ui.GlobalPauseKey',FakeHotkey); self.hotkey.start()
        settings.save(settings.validate({'bounds':[.1,.2,.8,.9], 'margin':.15}))
        self.root=tk.Tk(); self.root.withdraw(); self.app=App(self.root)

    def tearDown(self):
        self.app.close(); self.hotkey.stop(); self.paths.stop(); self.temp.cleanup()

    def test_margin_slider_switches_mode_and_survives_restart(self):
        self.assertTrue(self.app.calibrated_area.get())
        self.app.margin.set(.25)
        self.assertFalse(self.app.calibrated_area.get())
        self.assertEqual(working_area(self.app.config,self.app.margin.get()),(.25,.25,.75,.75))
        self.app.save_settings()
        stored=settings.load()
        self.assertEqual(stored['area_mode'],'manual')
        self.assertEqual(stored['margin'],.25)
        self.assertEqual(stored['bounds'],[.1,.2,.8,.9])
        self.app.calibrated_area.set(True); self.app.change_area_mode()
        self.assertEqual(working_area(self.app.config),(.1,.2,.8,.9))

    def test_slider_changes_coalesce_disk_writes(self):
        with patch('app.ui.settings.save') as save:
            for n in range(10): self.app.margin.set(.1+n*.01)
            self.assertEqual(save.call_count,0)
            deadline=time.monotonic()+.35
            while time.monotonic()<deadline: self.root.update(); time.sleep(.01)
            self.assertEqual(save.call_count,1)

    def test_calibration_prevents_reenable(self):
        calibration(self.app)
        self.app.last_frame=time.monotonic()
        self.app.toggle_control()
        self.assertFalse(self.app.enabled)
        self.assertTrue(self.app.calibrating)
        window=self.app.calibration_window
        self.root.tk.call(window.protocol('WM_DELETE_WINDOW'))
        self.assertFalse(self.app.calibrating)

    def test_lost_hand_releases_drag_and_discards_stale_calibration_sample(self):
        self.app.mouse_held=True; self.app.last_hand=('old',0,1)
        with patch('app.ui.wi.mouse_up') as release:
            self.app.lost_hand()
            release.assert_called_once()
        self.assertFalse(self.app.mouse_held); self.assertIsNone(self.app.last_hand)

    def test_callback_failure_pauses_and_poll_continues(self):
        self.app.enabled=True; self.app.mouse_held=True
        with patch.object(self.app,'_poll',side_effect=RuntimeError('test')), patch('app.ui.wi.mouse_up') as release, patch('app.ui.logging.getLogger'):
            self.app.poll()
            release.assert_called_once()
        self.assertFalse(self.app.enabled)
        self.assertIn('test',self.app.notice.get())

if __name__ == '__main__': unittest.main()
