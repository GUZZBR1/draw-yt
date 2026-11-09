"""Manifest records: every video and every frame, traceable end to end."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class FrameRecord:
    frame_id: str
    video_id: str
    path: str
    t_s: float = 0.0
    sharpness: float = 0.0
    luma: float = 0.0
    ahash: str = ""
    kept_level0: bool = False
    drop_reason: str = ""
    cluster_id: int = -1
    selection_reason: str = ""
    label_kind: str = ""  # "reviewed" | "pseudo" | ""


@dataclass
class VideoRecord:
    video_id: str
    url: str
    title: str = ""
    channel: str = ""
    channel_id: str = ""
    duration_s: int = 0
    license: str = ""
    cc_by_confirmed: bool = False
    framing: str = ""
    sha256: str = ""
    bytes: int = 0
    download_route: str = ""
    session_split: str = ""  # "train" | "holdout_setup" | "excluded"
    queries: list = field(default_factory=list)


def write_frames_csv(records: list[FrameRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(records[0]).keys()) if records else [f.name for f in FrameRecord.__dataclass_fields__.values()])
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def write_videos_jsonl(records: list[VideoRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def write_receipt(receipt: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
