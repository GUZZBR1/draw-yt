"""Download (stage 3): yt-dlp wrapper with integrity receipts.

720p cap, no audio (dead weight for vision), resume-friendly, and the
SHA-256 + size of every delivered file goes into the manifest. Routes
are attempted one at a time by the caller; this module never loops
retries on a dead route.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_video(video_id: str, out_dir: Path, *, max_height: int = 720, timeout: int = 1800) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    url = f"https://www.youtube.com/watch?v={video_id}"
    fmt = f"bestvideo[height<={max_height}][ext=mp4]/bestvideo[height<={max_height}]/best[height<={max_height}]"
    cmd = [
        "yt-dlp", "-f", fmt, "--no-audio", "--continue",
        "-o", str(out_dir / "%(id)s.%(ext)s"), url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed for {video_id}: {result.stderr.strip()[-500:]}")
    candidates = sorted(out_dir.glob(f"{video_id}.*"))
    if not candidates:
        raise RuntimeError(f"yt-dlp reported success but no file for {video_id}")
    return candidates[0]
