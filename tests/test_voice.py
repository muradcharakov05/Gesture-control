import unittest,tempfile,time
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from app import settings
from app.voice_commands import parse_command
from app.voice_inbox import send_command,receive_commands
import test_working_area as base_tests


def phrase(text,conf=.95):return {'result':[{'word':word,'conf':conf} for word in text.split()]}

class VoiceTests(unittest.TestCase):
 def test_commands_and_prefix(self):
  for text,command in [('джарвис','open'),('джарвис включи управление','control_on'),('запусти камеру','camera_on'),('выключи камеру','camera_off'),('останови управление','control_off')]:self.assertEqual(parse_command(phrase(text)),command)
 def test_noise_negation_and_uncertain_command_rejected(self):
  for text in ['не включи управление','камера','включи управление потом']:
   self.assertIsNone(parse_command(phrase(text)))
  self.assertIsNone(parse_command(phrase('джарвис',.3)))
 def test_inbox_once_and_expiry(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(settings,'PATH',Path(folder)/'settings.json'):
   send_command('camera_on');send_command('control_off')
   self.assertEqual(receive_commands(),['camera_on','control_off']);self.assertEqual(receive_commands(),[])
   (Path(folder)/'voice-inbox'/'cmd-expired.json').write_text('{"command":"control_on","created":1}')
   self.assertEqual(receive_commands(),[])

class VoiceUiTests(unittest.TestCase):
 setUp=base_tests.UiRegressionTests.setUp
 tearDown=base_tests.UiRegressionTests.tearDown
 def test_enable_waits_for_fresh_camera(self):
  with patch.object(self.app,'toggle_camera') as camera,patch.object(self.app,'toggle_control') as control:
   self.app.handle_voice_command('control_on');camera.assert_called_once();control.assert_not_called()
   self.assertIsNotNone(self.app.pending_voice_control)
   self.app.handle_voice_command('control_off');self.assertIsNone(self.app.pending_voice_control)
 def test_repeat_camera_start_does_not_stop_camera(self):
  self.app.tracker=NS(thread=NS(is_alive=lambda:True),stop_event=NS(is_set=lambda:False),stop=lambda:None)
  with patch.object(self.app,'toggle_camera') as camera:self.app.handle_voice_command('camera_on');camera.assert_not_called()
 def test_calibration_blocks_voice_start(self):
  self.app.calibrating=True
  with patch.object(self.app,'toggle_camera') as camera:self.app.handle_voice_command('control_on');camera.assert_not_called()
 def test_pause_cancels_voice_start_and_releases_drag(self):
  self.app.pending_voice_control=time.monotonic()+12;self.app.mouse_held=True
  with patch('app.ui.wi.mouse_up') as release:
   self.app.pause_requested.set();self.app._poll();release.assert_called_once()
  self.assertIsNone(self.app.pending_voice_control);self.assertFalse(self.app.enabled)

if __name__=='__main__':unittest.main()
