"""Cheap per-frame features: quality metrics and a visual embedding.

Only NumPy + Pillow. The embedding is a colour-histogram + downscaled
luminance vector: good enough for redundancy pruning and k-center
coverage, honest about not being a learned representation. A learned
extractor (DINOv2, the sheet encoder) can replace it behind the same
shape contract: one float vector per frame, L2-normalised.
"""

from __future__ import annotations

import numpy as np
from PIL import Image


def to_gray_array(image: Image.Image, width: int = 128) -> np.ndarray:
    """Grayscale float array in [0, 1], resized to a fixed width."""
    gray = image.convert("L")
    if gray.width != width:
        height = max(1, round(gray.height * width / gray.width))
        gray = gray.resize((width, height), Image.BILINEAR)
    return np.asarray(gray, dtype=np.float64) / 255.0


def laplacian_variance(gray: np.ndarray) -> float:
    """Variance of the discrete Laplacian: the standard blur meter."""
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    lap = (
        -4.0 * gray[1:-1, 1:-1]
        + gray[:-2, 1:-1]
        + gray[2:, 1:-1]
        + gray[1:-1, :-2]
        + gray[1:-1, 2:]
    )
    return float(lap.var())


def mean_luma(gray: np.ndarray) -> float:
    return float(gray.mean())


def frame_features(image: Image.Image) -> dict:
    gray = to_gray_array(image)
    return {
        "sharpness": laplacian_variance(gray),
        "luma": mean_luma(gray),
    }


def frame_embedding(image: Image.Image, hist_bins: int = 8, grid: int = 4) -> np.ndarray:
    """Colour histogram (3 x hist_bins) + grid x grid luminance, L2-normalised."""
    rgb = np.asarray(image.convert("RGB").resize((64, 64)), dtype=np.float64) / 255.0
    hist = []
    for channel in range(3):
        counts, _ = np.histogram(rgb[:, :, channel], bins=hist_bins, range=(0.0, 1.0))
        hist.append(counts / max(1.0, counts.sum()))
    small = np.asarray(image.convert("L").resize((grid, grid)), dtype=np.float64) / 255.0
    vec = np.concatenate(hist + [small.flatten()])
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec
