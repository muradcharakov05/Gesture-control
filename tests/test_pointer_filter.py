import unittest
from app.pointer_filter import PointerFilter


class PointerFilterTests(unittest.TestCase):
    def test_stationary_noise_is_reduced(self):
        f = PointerFilter(); f.seed((500,500), (500,500), 0)
        values = []
        for i in range(1, 121):
            target=(500+(3 if i % 2 else -3),500)
            values.append(f.update(target, i/60, .35, (1920,1080))[0])
        self.assertLess(max(values[30:])-min(values[30:]), 2)

    def test_fast_motion_adapts_without_overshoot(self):
        slow = PointerFilter(); fast = PointerFilter()
        slow.seed((0,0),(0,0),0); fast.seed((0,0),(0,0),0)
        for i in range(1, 16):
            slow_pos = slow.update((i*2,0),i/60,.35,(1920,1080))[0]
            fast_pos = fast.update((i*40,0),i/60,.35,(1920,1080))[0]
        self.assertLess((600-fast_pos)/600, (30-slow_pos)/30)
        self.assertLessEqual(fast_pos, 600)

    def test_similar_time_response_at_different_frame_rates(self):
        def run(rate):
            f=PointerFilter(); f.seed((0,0),(500,0),0)
            for i in range(1,rate+1): out=f.update((500,0),i/rate,.35,(1920,1080))
            return out[0]
        self.assertAlmostEqual(run(30), run(60), delta=2)

    def test_seed_prevents_resume_jumps(self):
        f=PointerFilter(); f.seed((200,200),(900,900),10)
        x,y = f.update((900,900),10.02,.35,(1920,1080))
        self.assertGreater(x,200); self.assertLess(x,350)
        self.assertEqual(x,y)
        f.reset(); self.assertIsNone(f.output)

if __name__ == '__main__': unittest.main()
