import unittest
from divide import safe_divide

class DivisionTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(safe_divide(8,2), 4)
    def test_negative(self):
        self.assertEqual(safe_divide(-8,2), -4)
