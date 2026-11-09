"""Download (stage 3): yt-dlp wrapper with named routes and receipts.

Measured on 2026-11-09 from a datacenter VM whose IP YouTube bot-checks
on the default web client: the `default` route fails with "Sign in to
confirm you're not a bot", while `android-node` (android player client
+ Node.js as the JS runtime for the n-challenge + no certificate check,
because some proxies break verification) downloads fine — at 360p,
because the SABR-only experiment skips the other android formats in
that session. On a residential connection the default route usually
delivers full quality, so routes are tried in quality order, **one
attempt per route, never a retry loop on a dead route**, and the
manifest records which route delivered each file.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

FORMAT = "bestvideo[height<={h}][ext=mp4]/bestvideo[height<={h}]/best[height<={h}]"


def routes() -> list[tuple[str, list[str]]]:
    """Ordered (name, extra yt-dlp args) download routes."""
    android = ["--extractor-args", "youtube:player_client=android", "--no-check-certificate"]
    node = shutil.which("node")
    if node:
        android += ["--js-runtimes", f"node:{node}"]
    return [
        ("default", []),
        ("android-node", android),
        ("tv-ios-web-embedded", ["--extractor-args", "youtube:player_client=tv,ios,web_embedded"]),
    ]


def build_command(route_args: list[str], video_id: str, out_dir: Path, max_height: int) -> list[str]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    return [
        "yt-dlp",
        "-f", FORMAT.format(h=max_height),
        "--continue",
        *route_args,
        "-o", str(out_dir / "%(id)s.%(ext)s"),
        url,
    ]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_video(
    video_id: str, out_dir: Path, *, max_height: int = 720, timeout: int = 1800
) -> tuple[Path, str]:
    """Try each route once, in order. Returns (file, route_name)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for name, route_args in routes():
        cmd = build_command(route_args, video_id, out_dir, max_height)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        candidates = sorted(out_dir.glob(f"{video_id}.*"))
        if result.returncode == 0 and candidates:
            return candidates[0], name
        tail = (result.stderr or result.stdout).strip().splitlines()
        errors.append(f"{name}: {tail[-1] if tail else 'no output'}")
    raise RuntimeError(f"all routes failed for {video_id} -> " + " | ".join(errors))
