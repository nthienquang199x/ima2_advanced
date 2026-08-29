# 260530 Grok Publish + GitHub Pages Readiness

## Scope

Prepare the `ima2-gen@1.1.15` Grok image release surface for Jun's final deployment/publish step.

This lane reconciles:

- Runtime discovery contract: `ima2 capabilities --json`
- CLI contract: `ima2 gen/edit/multimode/node --provider <auto|oauth|api|grok>`, `ima2 grok`, `ima2 prompt build`
- HTTP contract: Grok Classic/Node/Agent image generation, `/api/grok/status`, prompt-builder CLI mapping
- GitHub Pages EN/KO docs
- Structure docs and release/publish notes

## Source Of Truth

Current code is the source of truth. README and existing docs are treated as secondary and must be checked against:

- `bin/commands/*.ts`
- `routes/*.ts`
- `lib/capabilities.ts`
- `lib/grokImageAdapter.ts`
- `config.ts` / `config.js`
- `site/src/pages/**/*.astro`

## Contract Decisions

- Grok image support is shipped for Classic, Node, and Agent Mode.
- Grok video T2V/I2V is not shipped in `1.1.15`; research docs are planning only.
- Agent Mode is web-UI only and has no `ima2 agent` command.
- Prompt Builder has a CLI wrapper: `ima2 prompt build`.
- `ima2 serve` starts bundled progrok unless `IMA2_NO_GROK_PROXY=1`.
- Grok requests always use mandatory xAI Web Search and a `grok-4.3` planner before xAI Images API.
- Grok requests with reference/current/parent images use xAI `/v1/images/edits` to preserve image-to-image context.

## Employee Audit

- 니지카: NEEDS_FIX. GitHub Pages was stale: OAuth/API-only provider docs, `1.1.14` badge, no progrok/Grok env, no video-not-shipped callout, and prompt-builder CLI mismatch.
- 료: NEEDS_FIX. Backend/CLI mostly worked, but `lib/capabilities.ts` omitted Grok and listed non-existent `agent`; docs/API/CLI and structure had prompt-builder and provider drift.

## Implementation Plan

1. Fix `lib/capabilities.ts` and capabilities text output.
2. Fix CLI help strings for Grok image models.
3. Fix `docs/API.md` and `docs/CLI.md` prompt-builder/Grok status/error/config drift.
4. Fix GitHub Pages EN/KO providers, CLI, API, config, architecture, modes, docs nav, and landing strings.
5. Fix structure docs 00/02/03/06/07.
6. Run typecheck, tests, site build, local browser visual verification, employee revalidation.
7. Commit and push. Jun handles actual deployment/publish.

## Git Note

`devlog/` is ignored by repository policy, so this lane is a local jawdev record. Commit-visible tracking is mirrored in `structure/07-devlog-map.md`.
