"""Frame extraction (stage 4): ffmpeg at fixed fps + temporal pairs."""

from __future__ import annotations

import subprocess
from pathlib import Path


def extract_frames(video_path: Path, out_dir: Path, *, fps: float = 1.0) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(out_dir / "f_%06d.jpg")
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", f"fps={fps}", "-q:v", "3", pattern,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on {video_path}: {result.stderr.strip()[-500:]}")
    return sorted(out_dir.glob("f_*.jpg"))
