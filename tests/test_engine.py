import unittest
from app.gesture_engine import GestureEngine, PalmToggle, DEFAULT_BINDINGS
from app.windows_input import Monitor, map_point

OPEN = {'index': 1., 'middle': 1., 'ring': 1., 'pinky': 1.}

def fingers(**changes):
    return dict(OPEN, **changes)

def kinds(events): return [e.kind for e in events]

class EngineTests(unittest.TestCase):
    def test_short_index_click_only_on_release(self):
        e = GestureEngine(); e.update(OPEN, .5, 0., .4, DEFAULT_BINDINGS)
        self.assertEqual(kinds(e.update(fingers(index=.1), .5, 1., .4, DEFAULT_BINDINGS)), ['gesture'])
        self.assertEqual(e.update(fingers(index=.1), .5, 1.2, .4, DEFAULT_BINDINGS), [])
        self.assertEqual(kinds(e.update(OPEN, .5, 1.25, .4, DEFAULT_BINDINGS)), ['left_click'])
        self.assertEqual(e.update(OPEN, .5, 1.3, .4, DEFAULT_BINDINGS), [])

    def test_drag_has_down_up_and_no_click(self):
        e = GestureEngine(); e.update(OPEN, .5, 0, .4, DEFAULT_BINDINGS)
        e.update(fingers(index=.1), .5, 1, .4, DEFAULT_BINDINGS, (.3,.3))
        self.assertEqual(kinds(e.update(fingers(index=.1), .5, 1.6, .4, DEFAULT_BINDINGS, (.34,.3))), ['drag_start'])
        self.assertEqual(e.update(fingers(index=.1), .5, 2, .4, DEFAULT_BINDINGS), [])
        self.assertEqual(kinds(e.update(OPEN, .5, 2.1, .4, DEFAULT_BINDINGS)), ['drag_end'])

    def test_right_click_fires_only_once(self):
        e=GestureEngine(); e.update(OPEN,.5,0,.4,DEFAULT_BINDINGS)
        e.update(fingers(middle=.1),.5,1,.4,DEFAULT_BINDINGS)
        event=e.update(fingers(middle=.1),.5,1.2,.4,DEFAULT_BINDINGS)
        self.assertEqual((event[0].kind,event[0].value), ('action','Правая кнопка'))
        self.assertEqual(e.update(fingers(middle=.1),.5,1.5,.4,DEFAULT_BINDINGS), [])

    def test_scroll_direction_and_dead_zone(self):
        e=GestureEngine(); e.update(OPEN,.5,0,.4,DEFAULT_BINDINGS)
        e.update(fingers(ring=.1),.5,1,.4,DEFAULT_BINDINGS)
        self.assertEqual(e.update(fingers(ring=.1),.51,1.2,.4,DEFAULT_BINDINGS), [])
        result=e.update(fingers(ring=.1),.58,1.3,.4,DEFAULT_BINDINGS)
        self.assertEqual(result[0].kind,'scroll'); self.assertLess(result[0].value, 0)

    def test_palm_requires_rearm_and_hold(self):
        p=PalmToggle()
        self.assertFalse(p.update(True,0)); self.assertFalse(p.update(True,3))
        p.update(False,4); self.assertFalse(p.update(True,5)); self.assertTrue(p.update(True,6.7))
        self.assertFalse(p.update(True,9)); p.disarm(); self.assertFalse(p.update(True,12))

    def test_negative_monitor_origin(self):
        m=Monitor('left',-1920,-100,1920,1080)
        self.assertEqual(map_point(0,0,[.1,.1,.9,.9],m),(-1918,-98))
        self.assertEqual(map_point(1,1,[.1,.1,.9,.9],m),(-3,977))

if __name__ == '__main__': unittest.main()
