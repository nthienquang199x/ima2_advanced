# WP3 — devlog hardening

`devlog/_plan/README.md` active-lane table was last updated 2026-06-11 and no
longer matches the folder listing (33 entries incl. 9 loose `.md` files). The
SSE multiplexing work shipped (v2.0.0+), grok-video-15-1080p shipped (v2.0.5),
docs-refresh + preview-deploy-pipeline shipped (v2.0.4). AGENTS.md still says
v2.0.1 / 968 tests (actual: 2.0.5 / 1066).

## Audit rule

A unit moves `_plan` → `_fin` only with closeout evidence: shipped code +
tests in the current tree, or a CHANGELOG/release mention. Anything ambiguous
stays in `_plan` and is only re-labeled in the README table. Loose `.md`
audits that describe completed/shipped investigations move into `_fin` as
single-file entries (keep filename). No content edits to moved docs, no
deletions, no history rewrites.

## Candidate moves (verify each before moving)

- `260608_sse-*.md` (4 files) + `260608_sse-multiplexing-eventbus.md` — SSE
  multiplexing shipped in v2.0.0 (CHANGELOG); AGENTS.md describes the SSE
  architecture as current. → `_fin`.
- `260629_grok-video-15-1080p/` — shipped in v2.0.5 (HEAD release commits).
- `260627_docs-refresh/`, `260627_preview-deploy-pipeline/`,
  `260628_wp6_docs_code_grounding/` — shipped in v2.0.4 (CHANGELOG mentions
  preview publish + docs).
- `260602_post-release-security-audit.md`, `260602_agy-provider-audit.md`,
  `260602_node-session-evaporation-fix.md`, `260603_dropin-auth-flow-overhaul.md`
  — verify by checking whether referenced fixes exist in code; move only if closed.
- `00_model-selector-visibility.md` — non-conforming name; if still active,
  folder it or move to `_future`; if shipped, `_fin`.

## Doc updates

- `devlog/_plan/README.md` — rewrite active-lane table to the post-move listing.
- `structure/07-devlog-map.md` — refresh counts/paths.
- `AGENTS.md` — v2.0.1 → v2.0.5, 968 → 1066 tests (two spots: intro + Test
  Command section).

## Accept criteria

- `ls devlog/_plan` matches the README table 1:1 (minus README/_future).
- All gates still green (docs-only phase; run full suite anyway per loop rule).

## Audit synthesis (A, 2026-07-07, reviewer: gpt-5.5 explorer)

Spot-audit of the 8 riskiest closeout calls, all with file:line evidence:
- AGREE-MOVE: security_audit (routes/auth.ts:37-48 patches live), dropin-auth
  (4eb50cc surfaces present), sidebar-parity (SidebarHistoryImageCard.tsx:4-57;
  sequence card intentionally uses thumbnail+badge, codified in
  prompt-studio-ui-contract.test.js:172), sidecar-atomicity
  (atomicWriteJson + rollback, agentImageVideoGen.ts:195-198,353-356),
  model-selector-visibility (pill modifier shipped as
  image-model-select__trigger--pill, canvas-accordion.css:196-203),
  switch_account (POST/GET /api/auth/switch routes/auth.ts:238,256),
  api-key-accordion-vertex (AccountSettings.tsx:113-146, routes/keys.ts:52-75).
- KEEP-ACTIVE: 260605_stabilize-split — plan's own Phase 3 backend split is
  not descoped and routes/multimode.ts(564)/generate.ts(547)/nodes.ts(530)/
  lib/oauthProxy/generators.ts(501) still exceed the 500-line target.

## Final move list (B)

To `_fin`: 00_model-selector-visibility.md, 260602_agy-provider-audit.md,
260602_node-session-evaporation-fix.md, 260602_post-release-security-audit.md,
260603_dropin-auth-flow-overhaul.md, 260608_sse-{client-multiplexing,frontend-risk,
server-side-risk}-audit.md, 260608_sse-multiplexing-eventbus.md,
260601_agent-sidecar-atomicity/, 260601_prompt-studio-sidebar-parity/,
260602_api-key-accordion-vertex/, 260602_gallery-skeleton-shimmer-f5fix/,
260602_grok-gemini-api-provider-research/, 260602_security_audit/,
260602_switch_account/, 260608_grok-url-continue/,
260608_issue93-video-gallery-refresh/, 260624_agy-pr-integration/,
260627_docs-refresh/, 260627_preview-deploy-pipeline/,
260628_wp6_docs_code_grounding/, 260629_grok-video-15-1080p/.
Delete from `_plan` (byte-identical subsets of `_plan/_future` copies):
260529_issue80-batch-comparison-matrix/, 260602_storyboard-planner-skill/.
Stay in `_plan`: 260515_fork-prompting research, 260516/260517 jawdev units,
260531_pr-issue-review-rebase-plan (reference), 260531_video-settings-persistence,
260601_video-mode-persistence-refresh, 260605_stabilize-split (Phase 3 open),
260707 (this unit).
