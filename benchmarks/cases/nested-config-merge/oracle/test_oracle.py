import unittest
from merge import merge_config

class ConfigOracle(unittest.TestCase):
    def test_recursive_third_level(self):
        self.assertEqual(merge_config({"x":{"y":{"a":1,"b":2}}},
                                      {"x":{"y":{"b":3}}}),
                         {"x":{"y":{"a":1,"b":3}}})
    def test_does_not_mutate_inputs(self):
        base = {"x":{"data":[1]}}
        result = merge_config(base,{})
        result["x"]["data"].append(2)
        self.assertEqual(base["x"]["data"], [1])
