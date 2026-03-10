import unittest
from retry import retry_delays

class RetryOracle(unittest.TestCase):
    def test_zero_attempts(self):
        self.assertEqual(retry_delays(0), [])
    def test_invalid_base(self):
        with self.assertRaises(ValueError):
            retry_delays(3,0,8)
    def test_invalid_attempts(self):
        with self.assertRaises(ValueError):
            retry_delays(-1)
