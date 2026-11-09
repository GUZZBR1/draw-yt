import unittest
from pathlib import Path

from drawyt.download import build_command, routes


class TestDownloadRoutes(unittest.TestCase):
    def test_route_names_are_unique_and_default_first(self):
        names = [name for name, _ in routes()]
        self.assertEqual(names[0], "default")
        self.assertEqual(len(names), len(set(names)))

    def test_android_route_carries_the_measured_workarounds(self):
        by_name = dict(routes())
        args = by_name["android-node"]
        self.assertIn("youtube:player_client=android", args)
        self.assertIn("--no-check-certificate", args)

    def test_command_targets_the_video_and_caps_height(self):
        cmd = build_command([], "abc123XYZ", Path("/tmp/out"), 720)
        self.assertIn("https://www.youtube.com/watch?v=abc123XYZ", cmd)
        self.assertTrue(any("height<=720" in part for part in cmd))


if __name__ == "__main__":
    unittest.main()
