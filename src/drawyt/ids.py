"""YouTube video ID parsing: every URL shape a user will paste."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def parse_video_id(ref: str) -> str:
    """Accept a bare ID, watch/shorts/live/embed URLs, or youtu.be links.

    Query parameters after the ID (timestamps, tracking) are ignored —
    splitting a watch URL on '=' returns the *last* parameter's value,
    which silently turned '?v=ID&t=42s' into the ID '42s'. Parse the URL
    properly instead.
    """
    ref = ref.strip()
    if _ID_RE.match(ref):
        return ref
    parsed = urlparse(ref)
    host = (parsed.hostname or "").lower()
    parts = [p for p in parsed.path.split("/") if p]
    candidate = ""
    if host.endswith("youtu.be"):
        candidate = parts[0] if parts else ""
    elif host.endswith("youtube.com"):
        if parts and parts[0] in {"shorts", "live", "embed", "v"} and len(parts) > 1:
            candidate = parts[1]
        else:
            candidate = (parse_qs(parsed.query).get("v") or [""])[0]
    if _ID_RE.match(candidate):
        return candidate
    raise ValueError(f"could not find a YouTube video ID in: {ref!r}")
