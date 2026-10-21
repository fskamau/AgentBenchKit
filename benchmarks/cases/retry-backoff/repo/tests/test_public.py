import unittest

from retry import retry_delays


class RetryTests(unittest.TestCase):
    def test_count(self):
        self.assertEqual(retry_delays(4), [1.0, 2.0, 4.0])

    def test_cap(self):
        self.assertEqual(retry_delays(5, 4, 8), [4, 8, 8, 8])

    def test_one_attempt(self):
        self.assertEqual(retry_delays(1), [])
