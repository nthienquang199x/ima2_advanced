# Grok Video (T2V/I2V) Ship + Strict QA + Publish Prep — Execution Roadmap

Date: 2026-05-31
Branch: `feat/grok-video-i2v`
Driver goal (Jun): implement video, run repeated smoke tests verifying the
reference image is preserved, build a strict QA gate, verify in browser, get
employee verification, merge, run full Grok verification, prepare publish, and
fully implement the official GitHub Pages docs.

Design source of truth (already employee-reviewed): `docs/grok-video-i2v-plan.md`
+ `docs/grok-video-i2v-research.md`.

This file is the EXECUTION roadmap (what we actually run, in order, with the QA
gate). It does not re-derive the design — it sequences it and adds the gate,
verification, merge, publish-prep, and docs work.

## Current Verified State (pre-build)

- Branch `feat/grok-video-i2v`, version `1.1.15`, 7 commits ahead of `main`.
- Grok IMAGE provider: shipped + verified in Multimode / Node / Agent.
- Grok VIDEO: research + plan only. NOT implemented in runtime. Docs carry an
  explicit "video not shipped in 1.1.15" notice (README.md:76, docs/README.ko.md:65,
  docs/API.md:23).
- Grok proxy port fallback fix committed (723b53b), verified live.
- `npm test` baseline last known 826/826 pass.

## Decisions Needing Jun (business logic)

1. **Version bump on shipping video.** Shipping a new generation surface is a
   feature → propose `1.2.0`. This also requires flipping the three
   "video not shipped in 1.1.15" notices to "shipped in 1.2.0".
   (Alternative: keep `1.1.15` and just remove notices — not recommended,
   semver-wrong.)
2. **Scope for v1.** Adopt plan recommendation: ship **T2V + I2V**, defer
   reference-to-video to v2. Confirm.
3. **Plan open-decisions** — adopt recommended defaults unless Jun overrides:
   label `Video` (model layer) + `Animate` (image cards); default duration 5s UI
   / 1s smokes; default resolution 480p (720p allowed); I2V aspect ratio `auto`.
4. **Merge.** Merge `feat/grok-video-i2v` → `main` after the QA gate + employee
   PASS. Merge is local; **no `git push` / no publish without explicit go**.
5. **Publish boundary.** "퍼블리시 준비" = version bump + metadata + dry-run +
   pack inspection ONLY. Actual `npm publish` stays a Jun-only manual step
   (consistent with prior sessions). Confirm I should stop at prep.
6. **GitHub Pages.** Implement/refresh the docs-site content (EN/KO) in the repo
   and verify the static build. Actual Pages deploy = push, left to Jun.

## Implementation Sequence (maps to docs/grok-video-i2v-plan.md phases)

Boss writes all code directly (PABCD B-phase). Employees are read-only verifiers.

| Step | Plan phase | Files (new/modify) | Output |
|---|---|---|---|
| B1 | Phase 1 types/config/caps | `config.ts`, `lib/imageModels.ts`, `ui/src/lib/imageModels.ts`, `ui/src/types.ts`, `routes/capabilities.ts` | video model kind, config knobs |
| B2 | Phase 8 contract tests (TDD-first) | `tests/grokVideoAdapter.test.ts`, `tests/videoRoute.test.ts`, history/inflight tests | failing contract tests |
| B3 | Phase 2 adapter | NEW `lib/grokVideoAdapter.ts` | search→planner→generate→poll→download |
| B4 | Phase 3 storage/history | history/scan modules, `mediaType` sidecar | `.mp4` + `.mp4.json` persistence |
| B5 | Phase 4 route | NEW `routes/video.ts` `POST /api/video/generate` SSE | streaming progress |
| B6 | Phase 5 Node mode | node action wiring | Animate node → I2V |
| B7 | Phase 6 Agent mode | `ima2.generate_video` tool | Agent video turn |
| B8 | Phase 7 UI | ResultActions, gallery cards, node toolbar, agent pane, right panel | video UX |

## Strict QA Gate (the "엄격한 qa 게이트")

A single repeatable gate script/checklist that MUST be green before merge. The
reference-image-preservation check is the centerpiece (I2V must keep the source
subject/composition).

Gate stages (all must pass, run repeatedly):

1. **Static**: `npm run typecheck`, `npm run typecheck:tests`, ui `tsc`,
   `build:server`, `build:cli`, `ui:build`, `git diff --check`.
2. **Unit/contract**: full `npm test` (target ≥ prior 826 + new video tests),
   plus targeted video suite green.
3. **Live smoke ×N (repeatable, progrok at 127.0.0.1)**:
   - T2V 1s/480p ×3 → each downloads a valid `.mp4` (`ffprobe` duration/stream).
   - I2V 1s/480p ×3 from a known generated image → **reference-preservation
     assertion**: poster/first-frame of the output vs source image similarity
     above threshold (perceptual hash distance bound), subject retained.
   - Failure on any run → gate red, do not merge.
4. **Browser** (CDP, headed, DOM app): generate video from a result card
   (Animate), Node Animate, Agent Animate; confirm video card plays, progress
   phases render, no console errors.
5. **Employee verification**: Ryo (backend/adapter/route/storage), Nijika
   (UI/UX), Kita (data/pipeline + smoke evidence) must each return PASS.

QA gate artifact: `devlog/_plan/260531_grok-video-i2v-ship/05_qa-gate.md` (the
checklist + each run's evidence) and a helper smoke script under
`scripts/` if one does not already exist.

## Full Grok Verification (regression, "전반적인 grok 전체 검증")

After video lands, re-verify the existing Grok image surfaces did not regress:
Multimode generate + edit-with-reference, Node Grok generate + parent edit,
Agent Grok turn, `/api/grok/status`, port-fallback path. Live + browser.

## Publish Prep ("퍼블리시 준비")

- Version bump (decision #1), update CHANGELOG/README/docs notices (flip the 3
  "not shipped" notices), `npm run prepublishOnly`, `npm run publish:dry-run`,
  `npm pack --dry-run` summary (missing[]/forbidden[] must be empty).
- Remove stray untracked artifact `ima2-gen-1.1.14.tgz`.
- STOP before actual `npm publish`.

## GitHub Pages Docs ("공식 github page docs까지 전부 구현완료")

- Update docs-site (EN/KO) + `docs/API.md` + `docs/CLI.md` + `structure/` to
  document video: `POST /api/video/generate`, model layer `video`, Node/Agent
  Animate, storage/history `.mp4`, error codes, scope.
- Verify the site static build passes; browser-preview key pages.
- Push/deploy left to Jun (decision #6).

## Merge

After QA gate green + all employee PASS + Jun approval: merge
`feat/grok-video-i2v` → `main` locally (no push). Report.

## Out of Scope (v1)

- reference-to-video, video nodes in graph schema, poster-thumbnail generation,
  720p-only tuning, skipping web search for pure I2V (future optimization).
