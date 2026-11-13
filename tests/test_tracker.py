import time
import unittest
from unittest.mock import patch
from app.tracker import Tracker


class MissingCamera:
    def isOpened(self):
        return False
    def release(self):
        self.released = True


class TrackerTests(unittest.TestCase):
    def test_unavailable_camera_reports_error_and_releases(self):
        fake = MissingCamera()
        with patch('app.tracker.cv2.VideoCapture', return_value=fake):
            tracker = Tracker(0, True)
            tracker.start()
            tracker.thread.join(timeout=10)
        self.assertFalse(tracker.thread.is_alive())
        kind, message = tracker.results.get_nowait()
        self.assertEqual(kind, 'error')
        self.assertIn('камер', message.lower())
        self.assertTrue(fake.released)


if __name__ == '__main__':
    unittest.main()
