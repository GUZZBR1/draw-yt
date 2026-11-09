"""Pruning level 0 (pixel) over a folder of frames, plus the receipt.

Removes exact duplicates (file hash), near-duplicates (perceptual hash),
temporally static frames (mean absolute change vs the previous kept
frame), blurred frames and exposure failures. What survives is written
to a FrameRecord manifest; nothing is deleted on disk.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

from .features import frame_features, to_gray_array
from .hashing import average_hash, hamming
from .manifest import FrameRecord

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prune_frames(
    frames_dir: Path,
    video_id: str,
    *,
    judge=None,
    hash_distance: int = 4,
    static_threshold: float = 0.004,
    min_sharpness_quantile: float = 0.10,
    luma_range: tuple[float, float] = (0.03, 0.97),
) -> tuple[list[FrameRecord], dict]:
    paths = sorted(p for p in frames_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    records: list[FrameRecord] = []
    receipt = {"video_id": video_id, "input_frames": len(paths), "dropped": {}, "kept": 0}

    def drop(reason: str) -> None:
        receipt["dropped"][reason] = receipt["dropped"].get(reason, 0) + 1

    # first pass: features for the sharpness quantile of this video itself
    sharpness_values: list[float] = []
    per_path: dict[Path, dict] = {}
    for path in paths:
        with Image.open(path) as image:
            feats = frame_features(image)
            per_path[path] = feats
            sharpness_values.append(feats["sharpness"])
    sharp_floor = (
        float(np.quantile(sharpness_values, min_sharpness_quantile)) if sharpness_values else 0.0
    )

    seen_sha: set[str] = set()
    kept_hashes: list[int] = []
    prev_gray: np.ndarray | None = None

    for index, path in enumerate(paths):
        feats = per_path[path]
        record = FrameRecord(
            frame_id=f"{video_id}_{index:06d}",
            video_id=video_id,
            path=str(path),
            sharpness=feats["sharpness"],
            luma=feats["luma"],
        )
        sha = _file_sha(path)
        if sha in seen_sha:
            record.drop_reason = "exact_duplicate"
            drop("exact_duplicate")
            records.append(record)
            continue
        seen_sha.add(sha)

        if not (luma_range[0] <= feats["luma"] <= luma_range[1]):
            record.drop_reason = "exposure"
            drop("exposure")
            records.append(record)
            continue
        if feats["sharpness"] < sharp_floor:
            record.drop_reason = "blurred"
            drop("blurred")
            records.append(record)
            continue

        with Image.open(path) as image:
            ahash = average_hash(image)
            gray = to_gray_array(image, width=64)
        record.ahash = f"{ahash:016x}"

        if any(hamming(ahash, kept) <= hash_distance for kept in kept_hashes):
            record.drop_reason = "near_duplicate"
            drop("near_duplicate")
            records.append(record)
            continue
        if prev_gray is not None and float(np.abs(gray - prev_gray).mean()) < static_threshold:
            record.drop_reason = "static"
            drop("static")
            records.append(record)
            continue

        record.kept_level0 = True
        if judge is not None:
            with Image.open(path) as judged_image:
                scores = judge.score(judged_image)
            record.sheet_presence = scores.sheet_presence
            record.ink_density = scores.ink_density
        kept_hashes.append(ahash)
        prev_gray = gray
        receipt["kept"] += 1
        records.append(record)

    receipt["sharpness_floor"] = sharp_floor
    return records, receipt
