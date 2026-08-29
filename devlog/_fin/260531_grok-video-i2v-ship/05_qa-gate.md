# 05 — Strict QA Gate (Grok Video T2V/I2V)

Runner: `scripts/qa-grok-video.mjs` (tracked). This doc is the local devlog
record + evidence log. `devlog/` is gitignored; commit-visible tracking lives in
`structure/07-devlog-map.md`.

## Purpose

A single repeatable gate that MUST be green before merging `feat/grok-video-i2v`.
The reference-image-preservation check (I2V must keep the source subject) is the
centerpiece.

## Dependencies

- `ffmpeg` + `ffprobe` on PATH (used for mp4 validation + dHash frame extraction).
- A running server for the smoke stage: `ima2 serve` (bundled progrok auto-starts).
  Base URL is auto-detected from the advertise file or `--base-url`.

## Stages

| Stage | What it runs | Pass condition |
|---|---|---|
| static | `typecheck`, `typecheck:tests`, `build:server`, `build:cli`, `git diff --check` | all exit 0 |
| tests | targeted video suites (`grokVideoAdapter`, `videoRoute`, `history-video-row`, `grok-planner-adapter`) via `node --test` + tsx | all tests pass |
| smoke | live T2V ×N + I2V ×N against running server | each mp4 valid (ffprobe video stream + duration>0); I2V first-frame dHash hamming distance to source ≤ `--max-hamming` (default 20) |

### Reference-preservation method

For each I2V run, the output's first frame and the source image are each reduced
to a 9×8 grayscale frame via ffmpeg and converted to a 64-bit dHash (row-wise
horizontal gradient). The hamming distance bounds how much the opening frame may
drift from the source. I2V should start from the source image, so distances are
expected to be very small.

## Usage

```bash
# all stages, 3 runs each (server must be up for smoke)
node scripts/qa-grok-video.mjs

# subsets
node scripts/qa-grok-video.mjs --stage=static
node scripts/qa-grok-video.mjs --stage=tests
node scripts/qa-grok-video.mjs --stage=smoke --runs=3

# tuning
node scripts/qa-grok-video.mjs --stage=smoke --source=<file.png> --max-hamming=18 --resolution=720p
```

Per-run evidence is written to
`devlog/_plan/260531_grok-video-i2v-ship/evidence/qa-run-<ts>.json`.

## Evidence Log

### Run 2026-05-31 (initial, branch feat/grok-video-i2v @ 4eb785b)

GATE GREEN — static=PASS tests=PASS smoke=PASS

- static: typecheck, typecheck:tests, build:server, build:cli, git diff --check — all PASS.
- tests: targeted video suites — PASS.
- smoke (live, server :3333, progrok status=ready):
  - T2V ×3: `848x480`, ~1.04s, valid mp4 (31.7s / 37.1s / 35.1s).
  - I2V ×3 (source `n_c61e27416a.png`): `544x544`, **ref-preserved dHash distance = 1 ≤ 20** on every run (40s / 42s / 49s).

Reference preservation confirmed: opening frame is effectively identical to the
source image across all three I2V runs.
