import unittest

from drawyt.ids import parse_video_id


class TestParseVideoId(unittest.TestCase):
    def test_bare_id(self):
        self.assertEqual(parse_video_id("sVTAtgzPGhA"), "sVTAtgzPGhA")

    def test_watch_url_with_timestamp(self):
        # regression: splitting on '=' returned "42s" for this shape
        url = "https://www.youtube.com/watch?v=sVTAtgzPGhA&t=42s"
        self.assertEqual(parse_video_id(url), "sVTAtgzPGhA")

    def test_shorts_and_youtu_be(self):
        self.assertEqual(
            parse_video_id("https://www.youtube.com/shorts/sVTAtgzPGhA?feature=share"),
            "sVTAtgzPGhA",
        )
        self.assertEqual(parse_video_id("https://youtu.be/QiptDVNOZpQ?si=xyz"), "QiptDVNOZpQ")

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            parse_video_id("https://example.com/not-a-video")


if __name__ == "__main__":
    unittest.main()
