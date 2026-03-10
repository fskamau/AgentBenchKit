import unittest
from slug import slugify

class SlugTests(unittest.TestCase):
    def test_whitespace(self):
        self.assertEqual(slugify("Hello   WORLD"), "hello-world")
    def test_tab(self):
        self.assertEqual(slugify("alpha\tbeta"), "alpha-beta")
    def test_plain(self):
        self.assertEqual(slugify("hello"), "hello")
