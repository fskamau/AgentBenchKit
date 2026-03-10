import unittest
from divide import safe_divide

class DivisionOracle(unittest.TestCase):
    def test_zero_denominator(self):
        with self.assertRaises(ZeroDivisionError):
            safe_divide(1,0)
    def test_zero_over_zero(self):
        with self.assertRaises(ZeroDivisionError):
            safe_divide(0,0)
