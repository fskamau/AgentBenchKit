import unittest

from versions import sort_versions


class VersionOracle(unittest.TestCase):
    def test_patch_component(self):
        self.assertEqual(
            sort_versions(["1.2.12", "1.2.3"]), ["1.2.3", "1.2.12"]
        )

    def test_bad_version(self):
        with self.assertRaises(ValueError):
            sort_versions(["v1.0.0"])
