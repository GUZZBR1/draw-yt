"""License verification (stage 2): the video's own license field.

Measured route (2026-11-05): the default web client hits YouTube's bot
check from some IPs; player_client=tv,ios,web_embedded returns full
metadata including `license`. A present license field means the author
declared Creative Commons; standard license returns no field at all.
That asymmetry is the evidence — a filter alone is never trusted.
"""

from __future__ import annotations

import json
import subprocess

PLAYER_CLIENTS = "tv,ios,web_embedded"
CC_TEXT = "Creative Commons Attribution license (reuse allowed)"


def check_license(video_id: str, *, timeout: int = 60) -> dict:
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp", "-j", "--skip-download", "--ignore-no-formats-error",
        "--extractor-args", f"youtube:player_client={PLAYER_CLIENTS}",
        url,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    info = {}
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                info = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    license_field = info.get("license") or ""
    return {
        "video_id": video_id,
        "license": license_field,
        "cc_by_confirmed": license_field == CC_TEXT,
        "title": info.get("title", ""),
        "channel": info.get("channel") or info.get("uploader", ""),
        "channel_id": info.get("channel_id", ""),
        "duration_s": int(info.get("duration") or 0),
        "upload_date": info.get("upload_date", ""),
    }
