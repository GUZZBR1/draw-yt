"""Perceptual hashing for near-duplicate frame detection (pruning level 0)."""

from __future__ import annotations

import numpy as np
from PIL import Image


def average_hash(image: Image.Image, size: int = 8) -> int:
    """Classic average hash: downscale to size x size, threshold by the mean.

    Returns a size*size-bit integer. Two frames of the same scene at nearly
    the same instant produce hashes a few bits apart; different scenes
    produce hashes far apart.
    """
    gray = image.convert("L").resize((size, size), Image.BILINEAR)
    pixels = np.asarray(gray, dtype=np.float64)
    threshold = pixels.mean()
    bits = (pixels > threshold).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


def hamming(a: int, b: int) -> int:
    """Number of differing bits between two hashes."""
    return bin(a ^ b).count("1")
