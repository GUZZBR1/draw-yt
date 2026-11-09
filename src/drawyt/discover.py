"""Discovery (stage 1): YouTube search via yt-dlp flat playlists.

Search works from networks where the pixel download is bot-checked:
metadata flows even when downloads do not. The Creative Commons filter
is a search hint only; the license is verified per video afterwards.
"""

from __future__ import annotations

import subprocess

CC_FILTER = "EgIwAQ%253D%253D"  # YouTube search filter: Creative Commons


def search_query(query: str, *, limit: int = 20, cc_only: bool = False) -> list[dict]:
    if cc_only:
        url = (
            "https://www.youtube.com/results?search_query="
            + query.replace(" ", "+")
            + f"&sp={CC_FILTER}"
        )
        target = url
    else:
        target = f"ytsearch{limit}:{query}"
    cmd = [
        "yt-dlp", "--flat-playlist", "--dump-json",
        "--playlist-end", str(limit), target,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    results = []
    import json

    for line in out.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        results.append(
            {
                "video_id": item.get("id", ""),
                "url": item.get("url") or f"https://www.youtube.com/watch?v={item.get('id','')}",
                "title": item.get("title", ""),
                "channel": item.get("channel") or item.get("uploader", ""),
                "duration_s": int(item.get("duration") or 0),
                "view_count": int(item.get("view_count") or 0),
                "queries": query,
            }
        )
    return results
