import unittest

from merge import merge_config


class ConfigTests(unittest.TestCase):
    def test_nested_preserved(self):
        self.assertEqual(
            merge_config(
                {"db": {"host": "localhost", "port": 5432}},
                {"db": {"port": 5433}},
            ),
            {"db": {"host": "localhost", "port": 5433}},
        )

    def test_simple_override(self):
        self.assertEqual(merge_config({"a": 1}, {"a": 2})["a"], 2)
