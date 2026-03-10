import unittest
from pager import page_count

class PaginationOracle(unittest.TestCase):
    def test_small(self):
        self.assertEqual(page_count(1, 50), 1)
    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            page_count(1, 0)
    def test_negative_count(self):
        with self.assertRaises(ValueError):
            page_count(-1, 2)
