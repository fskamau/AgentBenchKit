import unittest
from versions import sort_versions

class VersionTests(unittest.TestCase):
    def test_double_digits(self):
        self.assertEqual(sort_versions(["1.10.0","1.2.0"]), ["1.2.0","1.10.0"])
    def test_major(self):
        self.assertEqual(sort_versions(["3.0.0","2.0.0"]), ["2.0.0","3.0.0"])
