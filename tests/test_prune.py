import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from drawyt.prune import prune_frames


def _sheet_image(path: Path, offset: int, noise_seed: int) -> None:
    img = Image.new("RGB", (160, 120), (120, 90, 60))
    draw = ImageDraw.Draw(img)
    draw.rectangle([30 + offset, 20, 130 + offset, 100], fill=(235, 235, 230))
    draw.line([40 + offset, 40, 90 + offset, 40], fill=(20, 20, 20), width=2)
    # deterministic texture so sharpness is non-trivial
    pixels = img.load()
    for x in range(0, 160, 3):
        for y in range(0, 120, 3):
            if (x * 7 + y * 13 + noise_seed) % 5 == 0:
                pixels[x, y] = (200, 200, 200)
    img.save(path, quality=92)


class TestPrune(unittest.TestCase):
    def test_duplicates_drop_and_distinct_frames_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = Path(tmp)
            _sheet_image(frames / "f_000001.jpg", 0, 1)
            # exact duplicate bytes
            (frames / "f_000002.jpg").write_bytes((frames / "f_000001.jpg").read_bytes())
            _sheet_image(frames / "f_000003.jpg", 25, 2)
            _sheet_image(frames / "f_000004.jpg", 50, 3)

            records, receipt = prune_frames(frames, "vid1")
            self.assertEqual(receipt["input_frames"], 4)
            reasons = [r.drop_reason for r in records]
            self.assertIn("exact_duplicate", reasons)
            kept = [r for r in records if r.kept_level0]
            self.assertGreaterEqual(len(kept), 2)
            self.assertEqual(receipt["kept"], len(kept))


if __name__ == "__main__":
    unittest.main()
