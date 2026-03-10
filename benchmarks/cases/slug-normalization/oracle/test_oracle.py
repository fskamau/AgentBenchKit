import unittest
from slug import slugify

class SlugOracle(unittest.TestCase):
    def test_punctuation(self):
        self.assertEqual(slugify(" Hello, World! "), "hello-world")
    def test_symbols(self):
        self.assertEqual(slugify("a___b"), "a-b")
    def test_empty(self):
        self.assertEqual(slugify("..."), "")
