import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from drawyt.judges import BrightRegionJudge
from drawyt.prune import prune_frames


class TestJudgeWiring(unittest.TestCase):
    def test_kept_frames_get_judge_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = Path(tmp)
            for i, offset in enumerate([0, 30, 60]):
                img = Image.new("RGB", (160, 120), (110, 85, 55))
                draw = ImageDraw.Draw(img)
                draw.rectangle([30 + offset // 3, 20, 130, 100], fill=(238, 238, 232))
                draw.line([40, 40 + i * 15, 100, 40 + i * 15], fill=(15, 15, 15), width=2)
                img.save(frames / f"f_{i:06d}.jpg", quality=92)
            records, _ = prune_frames(frames, "vid", judge=BrightRegionJudge())
            kept = [r for r in records if r.kept_level0]
            self.assertTrue(kept)
            for record in kept:
                self.assertIsNotNone(record.sheet_presence)
                self.assertGreater(record.sheet_presence, 0.2)


if __name__ == "__main__":
    unittest.main()
