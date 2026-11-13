import unittest
from types import SimpleNamespace
from app.gestures import GestureState, pinch_ratio, screen_position


class GestureTests(unittest.TestCase):
    def test_one_click_per_pinch_and_rearm(self):
        state = GestureState(threshold=.4, confirm_seconds=.1)
        self.assertFalse(state.update(.2, 0))  # not armed until open
        self.assertFalse(state.update(.7, 1))
        self.assertFalse(state.update(.2, 2))
        self.assertTrue(state.update(.2, 2.11))
        self.assertFalse(state.update(.2, 3))
        self.assertFalse(state.update(.5, 4))  # below release threshold
        self.assertFalse(state.update(.2, 4.2))
        self.assertFalse(state.update(.7, 5))
        self.assertFalse(state.update(.2, 6))
        self.assertTrue(state.update(.2, 6.11))

    def test_reset_requires_open_before_click(self):
        state = GestureState()
        state.update(.9, 1)
        state.reset()
        self.assertFalse(state.update(.1, 2))
        self.assertFalse(state.update(.1, 3))

    def test_unconfirmed_pinch_does_not_click(self):
        state = GestureState(threshold=.4, confirm_seconds=.1)
        state.update(.8, 0)
        state.update(.2, 1)
        state.update(.5, 1.05)
        self.assertFalse(state.update(.2, 1.2))

    def test_coordinates_are_clamped_and_corners_avoided(self):
        self.assertEqual(screen_position(-1, -1, .15, 1920, 1080), (2, 2))
        self.assertEqual(screen_position(2, 2, .15, 1920, 1080), (1917, 1077))
        self.assertEqual(screen_position(.5, .5, .15, 1920, 1080), (960, 540))

    def test_pinch_ratio_uses_image_aspect(self):
        points = [SimpleNamespace(x=0, y=0) for _ in range(21)]
        points[4] = SimpleNamespace(x=.1, y=0)
        points[8] = SimpleNamespace(x=.2, y=0)
        points[5] = SimpleNamespace(x=0, y=0)
        points[17] = SimpleNamespace(x=0, y=.4)
        self.assertAlmostEqual(pinch_ratio(points, 2), .5)


if __name__ == "__main__":
    unittest.main()
