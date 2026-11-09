"""Domain judges (pruning level 1): pluggable scorers, never sole vetoes.

A judge scores a frame; the pipeline uses scores to classify and rank.
By design (rule: who generates does not judge) no single judge can drop
a frame on its own: dropping requires the cheap pixel level or the
human-review quotas defined in the spec.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PIL import Image


@dataclass
class JudgeScores:
    sheet_presence: float | None = None  # 0..1
    hand_present: float | None = None    # 0..1
    ink_density: float | None = None     # 0..1


class Judge(Protocol):
    name: str

    def score(self, image: Image.Image) -> JudgeScores:
        ...


class BrightRegionJudge:
    """Baseline judge with no ML: paper is usually a large, bright,
    low-texture region. Honest placeholder until Draw's neural sheet
    detector, ink model, and hand landmarker are plugged in behind
    this same interface."""

    name = "bright-region-baseline"

    def score(self, image: Image.Image) -> JudgeScores:
        import numpy as np

        rgb = np.asarray(image.convert("RGB").resize((96, 96)), dtype=np.float64) / 255.0
        luma = rgb.mean(axis=2)
        bright = float((luma > 0.72).mean())
        # ink proxy: dark pixels inside bright areas
        ink = float(((luma < 0.35) & (rgb.max(axis=2) - rgb.min(axis=2) < 0.25)).mean())
        return JudgeScores(sheet_presence=bright, hand_present=None, ink_density=ink)
