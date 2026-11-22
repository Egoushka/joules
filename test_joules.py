import unittest

import joules


class FakeSamplerEnergy(unittest.TestCase):
    def test_constant_2w_for_10s_is_20j(self):
        s = joules.FakeSampler(watts=2.0, seconds=10.0, start=100.0)
        j, n = joules.integrate(s.snapshot(), 100.0, 110.0)
        self.assertAlmostEqual(j["total"], 20.0, delta=0.1)
        self.assertAlmostEqual(j["cpu"], 20.0, delta=0.1)
        self.assertEqual(j["gpu"], 0.0)
        self.assertEqual(n, 40)

    def test_partial_window_counts_overlap(self):
        s = joules.FakeSampler(watts=2.0, seconds=10.0, start=0.0)
        j, _ = joules.integrate(s.snapshot(), 2.5, 7.5)
        self.assertAlmostEqual(j["total"], 10.0, delta=0.1)

    def test_measure_with_fake_sampler(self):
        import time
        now = time.time()
        s = joules.FakeSampler(watts=2.0, seconds=3.0, start=now)
        m = joules.measure(s, lambda: time.sleep(1.0))
        self.assertAlmostEqual(m["joules"]["total"], 2.0, delta=0.3)


if __name__ == "__main__":
    unittest.main()
