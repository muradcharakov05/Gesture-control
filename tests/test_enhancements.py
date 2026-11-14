import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from app.gesture_engine import GestureEngine,DEFAULT_BINDINGS
from app.motion import MotionController
from app.windows_input import Monitor
from app.training_metrics import TrainingSession,save_result,history
from app import settings
from app.tracker import Tracker

OPEN={f:1. for f in ('index','middle','ring','pinky')}
CLOSED=dict(OPEN,index=.1)

class EnhancementsTests(unittest.TestCase):
 def test_mouse_override_ignores_injected_events(self):
  from app.mouse_activity import MouseActivity
  monitor=MouseActivity.__new__(MouseActivity);monitor.last_activity=0.;monitor.event_count=0
  monitor.record_input(1,10);self.assertEqual(monitor.last_activity,0.)
  monitor.record_input(0,11);self.assertEqual(monitor.last_activity,11)
 def test_still_hold_neither_drags_nor_clicks(self):
  e=GestureEngine();e.update(OPEN,.5,0,.4,DEFAULT_BINDINGS,(.3,.3))
  e.update(CLOSED,.5,1,.4,DEFAULT_BINDINGS,(.3,.3))
  self.assertEqual(e.update(CLOSED,.5,2,.4,DEFAULT_BINDINGS,(.301,.3)),[])
  self.assertEqual(e.update(OPEN,.5,3,.4,DEFAULT_BINDINGS,(.301,.3)),[])
 def test_thresholds_are_independent(self):
  e=GestureEngine();limits=dict(index=.2,middle=.6,ring=.3,pinky=.4)
  e.update(OPEN,.5,0,limits,DEFAULT_BINDINGS)
  self.assertEqual(e.update(dict(OPEN,index=.3),.5,1,limits,DEFAULT_BINDINGS),[])
  self.assertEqual(e.update(dict(OPEN,middle=.5),.5,2,limits,DEFAULT_BINDINGS)[0].value,'middle')
 def test_relative_clutch_rebases_without_jump(self):
  m=Monitor('test',0,0,1920,1080);c=MotionController()
  self.assertEqual(c.update((.5,.5),0,(500,500),(.1,.1,.9,1),m,'relative',False),(500,500))
  self.assertGreater(c.update((.6,.5),.1,(500,500),(.1,.1,.9,1),m,'relative',False)[0],500)
  c.freeze()
  self.assertEqual(c.update((.2,.2),.3,(700,500),(.1,.1,.9,1),m,'relative',False),(700,500))
 def test_precision_reduces_slow_relative_displacement(self):
  m=Monitor('test',0,0,1920,1080);outputs=[]
  for precise in (False,True):
   c=MotionController();c.update((.5,.5),0,(500,500),(0,0,1,1),m,'relative',precise)
   outputs.append(c.update((.51,.5),.1,(500,500),(0,0,1,1),m,'relative',precise)[0])
  self.assertLess(outputs[1],outputs[0])
 def test_selected_hand_filters_other_hand_and_locks_nearest(self):
  tracker=Tracker(0,True,'right')
  def points(x):return [NS(x=x,y=.5)]*21
  def result(names,xs):return NS(hand_landmarks=[points(x) for x in xs],handedness=[[NS(category_name=n,score=.99)] for n in names])
  found,label=tracker.select_hand(result(['Left','Right'],[.2,.7]),0)
  self.assertEqual(label,'right');self.assertEqual(found[0].x,.7)
  found,_=tracker.select_hand(result(['Right'],[.1]),.1);self.assertIsNone(found)
 def test_training_metrics_and_persistence(self):
  session=TrainingSession(2);session.start(0);session.click(False,1);session.click(True,2);session.click(True,3)
  self.assertTrue(session.finished);m=session.metrics();self.assertAlmostEqual(m['accuracy'],2/3);self.assertEqual(m['average_seconds'],1.5)
  with tempfile.TemporaryDirectory() as folder,patch.object(settings,'PATH',Path(folder)/'settings.json'):
   save_result('test',settings.validate({}),m);self.assertEqual(history()[0]['metrics'],m)
 def test_new_settings_survive_validation(self):
  data=settings.validate({'pointer_mode':'relative','precision':False,'hand':'left','thresholds':{'middle':.6,'ring':.3},'pinch':.25})
  self.assertEqual(data['hand'],'left');self.assertEqual(data['thresholds']['pinky'],.25);self.assertEqual(data['thresholds']['middle'],.6)
  self.assertFalse(data['precision'])

class UiEnhancementsTests(unittest.TestCase):
 def setUp(self):
  import tkinter as tk
  from app.ui import App
  from test_working_area import FakeHotkey
  self.temp=tempfile.TemporaryDirectory()
  self.pathpatch=patch.object(settings,'PATH',Path(self.temp.name)/'settings.json');self.pathpatch.start()
  self.keypatch=patch('app.ui.GlobalPauseKey',FakeHotkey);self.keypatch.start()
  self.root=tk.Tk();self.root.withdraw();self.app=App(self.root)
 def tearDown(self):
  self.app.close();self.keypatch.stop();self.pathpatch.stop();self.temp.cleanup()
 def test_physical_mouse_activity_releases_drag_and_blocks_gesture(self):
  import time
  self.app.enabled=True;self.app.mouse_held=True;self.app.mouse_activity.last_activity=time.monotonic()
  with patch('app.ui.wi.mouse_up') as release:
   self.app._poll();release.assert_called_once()
  self.assertFalse(self.app.mouse_held)
  with patch.object(self.app.engine,'update') as gesture:
   self.app.process([NS(x=.5,y=.5)]*21,time.monotonic(),640,480);gesture.assert_not_called()
 def test_extended_settings_save(self):
  self.app.pointer_mode.set('relative');self.app.hand.set('left');self.app.threshold_vars['ring'].set(.65)
  self.app.precision.set(False);self.app.save_settings()
  config=settings.load()
  self.assertEqual(config['pointer_mode'],'relative');self.assertEqual(config['hand'],'left')
  self.assertEqual(config['thresholds']['ring'],.65);self.assertFalse(config['precision'])

 def test_measured_training_completes_and_saves(self):
  import tkinter as tk
  from tkinter import ttk
  from app.measured_training import measured_training
  win=tk.Toplevel(self.root);frame=ttk.Frame(win);frame.pack(fill='both',expand=True)
  measured_training(frame,self.app);self.root.update()
  button=next(w for w in frame.winfo_children() if isinstance(w,ttk.Button))
  canvas=next(w for w in frame.winfo_children() if isinstance(w,tk.Canvas))
  button.invoke();self.root.update()
  for _ in range(10):
   oval=next(item for item in canvas.find_all() if canvas.type(item)=='oval')
   x1,y1,x2,y2=canvas.coords(oval)
   canvas.event_generate('<Button-1>',x=round((x1+x2)/2),y=round((y1+y2)/2));self.root.update()
  self.assertEqual(history()[-1]['metrics']['hits'],10)
  self.assertEqual(history()[-1]['metrics']['accuracy'],1.)
  win.destroy()

if __name__=='__main__':unittest.main()
