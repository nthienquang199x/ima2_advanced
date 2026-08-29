# 260707 — GPT-5.6 rollout + OIDC release transition + devlog hardening

Date: 2026-07-07
Branch: `dev`
Session: cxc-loop HOTL, one PABCD cycle per work-phase.
Status: ACTIVE (Windows package-local OAuth corrective release)
Release baseline: `v2.0.14` at `bea7ae5b5ea0a6e9039732794d2bdeb939e429b3`

## Objective

1. **WP1** — mirror the opencodex GPT-5.6 rollout (opencodex `d8c44b7`,
   devlog `260702_gpt56-max-rollout`) into ima2-gen: accept
   `gpt-5.6-sol` / `gpt-5.6-terra` / `gpt-5.6-luna` as OAuth image models on
   every model surface, and extend the reasoning ladder with `max` after
   `xhigh`. Defaults stay `gpt-5.4-mini` (opencodex explicitly deferred
   defaulting to 5.6; access errors surface from upstream, we do not pre-block).
2. **WP2** — finish the OIDC release transition: production publish is the
   `publish.yml` trusted-publishing workflow (GitHub Release → `latest`,
   `preview` branch push → `preview` dist-tag). Local release scripts stop
   running credentialed `npm publish` and instead end at `gh release create`.
3. **WP3** — devlog hardening: `devlog/_plan/README.md` active-lane table is
   stale (updated 2026-06-11); audit `_plan` units, move closed-out ones to
   `_fin`, folder loose `.md` files, refresh `structure/07-devlog-map.md`,
   fix stale AGENTS.md facts (v2.0.1 → 2.0.5, 968 → 1066 tests).
4. **WP4** — release recurrence hardening after the live v2.0.8-v2.0.13
   sequence: make preview a mandatory pre-tag candidate gate, publish the exact
   tarball that passed install smoke, narrow OIDC to the publish job, enforce
   event/ref/version/main-ancestry contracts, pin the release toolchain and
   bundled Codex dependency, support npm 12 install-script policy explicitly,
   and wait for registry/provenance proof before declaring a release done.

## Source evidence

- opencodex `d8c44b7` (`feat(catalog): add GPT-5.6 Sol Terra Luna rollout metadata`):
  `src/codex-catalog.ts` adds the three slugs to `NATIVE_OPENAI_MODELS` with
  372k context override; `src/reasoning-effort.ts` makes `max` a first-class
  Codex reasoning level after `xhigh` (`requestToCodexEffort("max")` keeps `max`).
- ima2-gen currently pins `["gpt-5.5","gpt-5.4","gpt-5.4-mini"]` at
  `config.ts:263`, `lib/imageModels.ts:4`, and mirrors it across UI/CLI/tests.
- Reasoning ladder currently `none|low|medium|high|xhigh` at `config.ts:270`,
  `lib/imageModels.ts:7`, `lib/oauthProxy/runtime.ts:8`, `lib/agentSettings.ts:8`,
  `lib/agentTypes.ts:28`, `ui/src/lib/reasoning.ts:1`, `ui/src/store/storeTypes.ts:119`,
  CLI validators in `bin/commands/{gen,edit,multimode,node}.ts`.
- Publish workflow `.github/workflows/publish.yml` already implements OIDC
  trusted publishing with preconditions; `scripts/release.sh` and
  `package.json` `release:*` still run direct `npm publish`.
- `~/.codex/opencodex-catalog.json` on this machine does not yet list 5.6
  slugs — live probes of gpt-5.6 may fail upstream; that is acceptable
  evidence (surface-not-blocked is what we verify).
- Live release evidence on 2026-07-10: v2.0.8-v2.0.12 all created tags and
  GitHub Releases before their deterministic install/test/package failures;
  v2.0.13 is the first successful `latest` + `preview` pair. The failure
  taxonomy and prevention design are recorded in `040_wp4_release_pipeline_hardening.md`.

## Work-phase map (dependency-ordered)

| WP | Doc | Scope |
|----|-----|-------|
| 1 | `010_wp1_gpt56_models.md` | model + reasoning surfaces, tests, i18n |
| 2 | `020_wp2_oidc_release.md` | release scripts + infra docs |
| 3 | `030_wp3_devlog_hardening.md` | devlog/_plan audit + structure docs + AGENTS.md |
| 4 | `040_wp4_release_pipeline_hardening.md` | pre-tag preview gate, tested artifact publish, npm/OIDC/package policy |

## Out of scope

- opencodex repo changes outside the vendored compatibility reference;
- flipping any default model or reasoning default;
- new dependencies; UI redesign.

## Scope amendment — 2026-07-10

The user subsequently authorized commit, push, preview publishing, and main npm
publishing. WP4 therefore includes the live preview → stable promotion and
post-publish proof needed to verify the hardening. It still excludes opencodex
changes, unrelated third-party dependencies, UI work, npm trusted-publisher identity
changes, and GitHub branch-protection/ruleset changes.

## Acceptance (every WP)

Fresh green: `npm run typecheck`, `npm run typecheck:tests`, `npm test`
(1094 pass), `npm run test:inventory`. Per-WP activation evidence is listed in
each decade doc. WP4 closes with signed preview/stable registry proof, green
Ubuntu/Windows npm 11/12 CI, and live Luna/Terra `medium` image generation from
the published package.
