import unittest

from PIL import Image, ImageDraw

from drawyt.hashing import average_hash, hamming


class TestHashing(unittest.TestCase):
    def test_identical_images_have_zero_distance(self):
        img = Image.new("RGB", (64, 64), "white")
        ImageDraw.Draw(img).rectangle([8, 8, 40, 40], fill="black")
        self.assertEqual(hamming(average_hash(img), average_hash(img.copy())), 0)

    def test_opposite_images_are_far_apart(self):
        left_dark = Image.new("RGB", (64, 64), "white")
        ImageDraw.Draw(left_dark).rectangle([0, 0, 31, 63], fill="black")
        right_dark = Image.new("RGB", (64, 64), "white")
        ImageDraw.Draw(right_dark).rectangle([32, 0, 63, 63], fill="black")
        self.assertGreater(hamming(average_hash(left_dark), average_hash(right_dark)), 20)


if __name__ == "__main__":
    unittest.main()
