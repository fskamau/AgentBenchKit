import unittest

from pager import page_count


class PaginationTests(unittest.TestCase):
    def test_remainder(self):
        self.assertEqual(page_count(11, 5), 3)

    def test_empty(self):
        self.assertEqual(page_count(0, 5), 0)

    def test_even(self):
        self.assertEqual(page_count(10, 5), 2)
