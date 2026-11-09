# Changelog

## 0.2.0 — 2026-11-09

Audit pass over the whole codebase, driven by defects found in the code
(not by taste). Full findings: `docs/AUDIT_2026-11-09.md`.

- **Fixed:** `fetch` parsed watch URLs by splitting on `=` — a URL with a
  timestamp (`?v=ID&t=42s`) was parsed as the ID `42s`. New
  `drawyt.ids.parse_video_id` handles watch/shorts/live/embed/youtu.be
  and bare IDs, with tests.
- **Fixed:** `download --cc-only` was a dead flag (`store_true` with
  `default=True` could never be turned off). Now a proper
  `--cc-only/--no-cc-only` boolean option.
- **Level 1 wired:** the baseline sheet/ink judge existed but was never
  called. `prune --judge` and `fetch --judge` now score kept frames and
  write `sheet_presence`/`ink_density` into the frame manifest.
- **Coreset honours pruning:** `coreset --from-manifest <frames_manifest.csv>`
  selects only from frames kept at level 0, instead of re-reading the
  whole frames folder.
- **`fetch --budget N`:** the one-shot pipeline now also builds the
  coreset from the kept frames, in the same receipt.
- Added `python -m drawyt`, a GitHub Actions workflow for Python
  3.10–3.12 (in `docs/ci-workflow.yml` — activation is one copy into
  `.github/workflows/`, a path the repo's automation cannot write), and
  this changelog.

## 0.1.1 — 2026-11-09

- Working download routes measured live: default → android-node →
  tv/ios/web-embedded, one attempt each, delivering route recorded.
- `drawyt fetch`: one-shot download + extract + prune with combined receipt.
- Live end-to-end test receipt (`docs/LIVE_TEST_2026-11-09.md`).

## 0.1.0 — 2026-11-09

- Initial release: discovery, per-video license verification, download,
  ffmpeg extraction, level-0 pruning, k-center coreset, manifests and
  receipts, spec, tests.
