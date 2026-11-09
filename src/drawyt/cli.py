"""drawyt command line: one subcommand per pipeline stage."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from . import __version__
from .coreset import assign_clusters, kcenter_greedy, medoid_index
from .discover import search_query
from .download import download_video, file_sha256
from .extract import extract_frames
from .features import frame_embedding
from .license_check import check_license
from .manifest import FrameRecord, VideoRecord, write_frames_csv, write_receipt, write_videos_jsonl
from .prune import IMAGE_SUFFIXES, prune_frames


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def cmd_search(args) -> int:
    queries = [q.strip() for q in Path(args.queries).read_text(encoding="utf-8").splitlines() if q.strip()]
    by_id: dict[str, dict] = {}
    for query in queries:
        for hit in search_query(query, limit=args.limit, cc_only=args.cc_only):
            if hit["video_id"] in by_id:
                by_id[hit["video_id"]]["queries"] += f";{query}"
            else:
                by_id[hit["video_id"]] = hit
    rows = sorted(by_id.values(), key=lambda r: -r["view_count"])
    _write_csv(rows, Path(args.out))
    print(f"search: {len(rows)} unique candidates -> {args.out}")
    return 0


def cmd_check(args) -> int:
    rows = _read_csv(Path(args.input))
    out_rows = []
    for row in rows:
        info = check_license(row["video_id"])
        merged = {**row, **{k: v for k, v in info.items() if v not in ("", 0)}}
        merged["cc_by_confirmed"] = "sim" if info["cc_by_confirmed"] else "nao"
        merged["license_field"] = info["license"]
        out_rows.append(merged)
        print(f"check: {row['video_id']} cc_by={merged['cc_by_confirmed']}")
    _write_csv(out_rows, Path(args.out))
    confirmed = sum(1 for r in out_rows if r["cc_by_confirmed"] == "sim")
    print(f"check: {confirmed}/{len(out_rows)} CC BY confirmed -> {args.out}")
    return 0


def cmd_download(args) -> int:
    rows = _read_csv(Path(args.input))
    out_dir = Path(args.out)
    records: list[VideoRecord] = []
    failures = 0
    for row in rows:
        if args.cc_only and row.get("cc_by_confirmed") != "sim":
            continue
        try:
            path, route_used = download_video(row["video_id"], out_dir)
        except Exception as exc:  # one attempt per route; report, do not loop
            print(f"download: FAILED {row['video_id']}: {exc}", file=sys.stderr)
            failures += 1
            continue
        records.append(
            VideoRecord(
                video_id=row["video_id"],
                url=row.get("url", ""),
                title=row.get("title", ""),
                channel=row.get("channel", ""),
                duration_s=int(row.get("duration_s") or 0),
                license=row.get("license_field", ""),
                cc_by_confirmed=row.get("cc_by_confirmed") == "sim",
                sha256=file_sha256(path),
                bytes=path.stat().st_size,
                download_route=route_used,
            )
        )
        print(f"download: ok {row['video_id']} ({path.stat().st_size} bytes)")
    write_videos_jsonl(records, out_dir / "manifest.jsonl")
    write_receipt(
        {"stage": "download", "ok": len(records), "failed": failures},
        out_dir / "receipt_download.json",
    )
    print(f"download: {len(records)} ok, {failures} failed -> {out_dir}")
    return 0 if records or not failures else 1


def cmd_extract(args) -> int:
    frames = extract_frames(Path(args.video), Path(args.out), fps=args.fps)
    print(f"extract: {len(frames)} frames -> {args.out}")
    return 0


def cmd_prune(args) -> int:
    frames_dir = Path(args.frames)
    video_id = args.video_id or frames_dir.name
    records, receipt = prune_frames(frames_dir, video_id)
    out = Path(args.out)
    write_frames_csv(records, out / "frames_manifest.csv")
    write_receipt({"stage": "prune_level0", **receipt}, out / "receipt_prune.json")
    print(f"prune: {receipt['kept']}/{receipt['input_frames']} kept, dropped={receipt['dropped']} -> {out}")
    return 0


def cmd_coreset(args) -> int:
    frames_dir = Path(args.frames)
    paths = sorted(p for p in frames_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    if not paths:
        print("coreset: no frames found", file=sys.stderr)
        return 1
    embeddings = []
    for path in paths:
        with Image.open(path) as image:
            embeddings.append(frame_embedding(image))
    matrix = np.stack(embeddings)
    seed = medoid_index(matrix)
    chosen = kcenter_greedy(matrix, args.budget, seed_index=seed)
    clusters = assign_clusters(matrix, chosen)

    out = Path(args.out)
    (out / "frames").mkdir(parents=True, exist_ok=True)
    video_id = args.video_id or frames_dir.name
    records: list[FrameRecord] = []
    chosen_set = set(chosen)
    for idx, path in enumerate(paths):
        if idx not in chosen_set:
            continue
        dest = out / "frames" / path.name
        shutil.copy2(path, dest)
        records.append(
            FrameRecord(
                frame_id=f"{video_id}_{idx:06d}",
                video_id=video_id,
                path=str(dest),
                cluster_id=int(clusters[idx]),
                selection_reason="kcenter_cover",
            )
        )
    write_frames_csv(records, out / "manifest_frames.csv")
    receipt = {
        "stage": "coreset_kcenter",
        "input_frames": len(paths),
        "budget": args.budget,
        "selected": len(records),
    }
    write_receipt(receipt, out / "receipt_coreset.json")
    print(f"coreset: {len(records)}/{len(paths)} selected -> {out}")
    return 0


def cmd_fetch(args) -> int:
    """One-shot personal pipeline: URL/ID -> video -> frames -> pruned manifest."""
    from .download import download_video as _dl

    video_ref = args.url.rstrip("/").split("/")[-1].split("=")[-1].split("?")[0]
    root = Path(args.out)
    path, route_used = _dl(video_ref, root / "videos")
    frames = extract_frames(path, root / "frames" / video_ref, fps=args.fps)
    records, receipt = prune_frames(root / "frames" / video_ref, video_ref)
    write_frames_csv(records, root / "work" / video_ref / "frames_manifest.csv")
    combined = {
        "stage": "fetch",
        "video_id": video_ref,
        "route": route_used,
        "file": str(path),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
        "frames_extracted": len(frames),
        "prune": receipt,
    }
    write_receipt(combined, root / "receipt_fetch.json")
    print(
        f"fetch: {video_ref} via {route_used}: {combined['bytes']} bytes, "
        f"{len(frames)} frames, {receipt['kept']} kept after pruning -> {root}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="drawyt", description="YouTube -> coreset pipeline for Draw.")
    parser.add_argument("--version", action="version", version=f"drawyt {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search", help="discover candidates via yt-dlp")
    p.add_argument("--queries", required=True)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--cc-only", action="store_true")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("check", help="verify license per video")
    p.add_argument("input")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("download", help="download verified videos (720p, no audio)")
    p.add_argument("input")
    p.add_argument("--out", required=True)
    p.add_argument("--cc-only", action="store_true", default=True)
    p.set_defaults(fn=cmd_download)

    p = sub.add_parser("fetch", help="one-shot: download a video and prune its frames")
    p.add_argument("url", help="YouTube URL or bare video ID")
    p.add_argument("--out", required=True)
    p.add_argument("--fps", type=float, default=1.0)
    p.set_defaults(fn=cmd_fetch)

    p = sub.add_parser("extract", help="extract frames from a local video (ffmpeg)")
    p.add_argument("video")
    p.add_argument("--out", required=True)
    p.add_argument("--fps", type=float, default=1.0)
    p.set_defaults(fn=cmd_extract)

    p = sub.add_parser("prune", help="level-0 pruning over a frames folder")
    p.add_argument("frames")
    p.add_argument("--out", required=True)
    p.add_argument("--video-id")
    p.set_defaults(fn=cmd_prune)

    p = sub.add_parser("coreset", help="k-center coreset selection over a frames folder")
    p.add_argument("frames")
    p.add_argument("--budget", type=int, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--video-id")
    p.set_defaults(fn=cmd_coreset)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
