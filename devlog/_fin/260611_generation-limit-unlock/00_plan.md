# 260611 Generation Limit Unlock

## Goal

Remove the remaining hard-coded 8/12 generation-count ceilings so the UI and server use one explicit runtime limit for classic count, multimode max images, stream parsing, capabilities metadata, and inflight capacity.

## Findings

- `lib/inflight.ts` hard-caps active jobs with `MAX_CONCURRENT_JOBS = 12`.
- `config.ts` exposes `limits.maxParallel`, but the default is 8 and capabilities says it is advisory only.
- Classic generation clamps `n` to 8 in `routes/generate.ts`.
- Multimode clamps `maxImages` to 8 through `lib/multimodeHelpers.ts`, OAuth/Grok/Responses adapters, and prompt builders.
- Frontend custom count controls clamp to 8 in `ui/src/components/CountPicker.tsx` and persisted generation defaults clamp to 8 in `ui/src/store/storePersistence.ts`.
- `/api/capabilities` reports `limits.maxGeneratedImages = 8`.

## Decision

Use a configurable default generation/count limit of 24, exposed as `limits.maxGeneratedImages`, and make inflight capacity use `limits.maxParallel` with a default of 24. This removes the hard 12 server cap while keeping an operational guardrail that can be overridden through config/env.

## Planned Changes

### MODIFY `config.ts`

- Add `limits.maxGeneratedImages` with env `IMA2_MAX_GENERATED_IMAGES`, config file override, default `24`.
- Change default `limits.maxParallel` from `8` to `24`.
- Export `MAX_GENERATED_IMAGES`.

### MODIFY server/runtime generation surfaces

- `routes/generate.ts`: clamp `n` with `ctx.config.limits.maxGeneratedImages`.
- `lib/multimodeHelpers.ts`: accept an optional max and clamp with it.
- `routes/multimode.ts`: pass `ctx.config.limits.maxGeneratedImages`.
- `lib/oauthProxy/prompts.ts`, `lib/oauthProxy/generators.ts`, `lib/oauthProxy/streams.ts`, `lib/responsesImageAdapter.ts`, `lib/grokMultimodeAdapter.ts`: use runtime/config max instead of hard-coded 8 where request max image counts are parsed or stream images are retained.
- `lib/capabilities.ts`: report `appConfig.limits.maxGeneratedImages` and mark `maxParallel.enforced = true`.
- `lib/inflight.ts`: derive `MAX_CONCURRENT_JOBS` from `config.limits.maxParallel`.

### MODIFY frontend

- Add or update a frontend generation limit constant to 24.
- `ui/src/components/CountPicker.tsx`: clamp custom counts to the frontend max instead of 8.
- `ui/src/store/storePersistence.ts`: normalize persisted count and multimode max images to the same frontend max.

### MODIFY docs/tests

- Update capability/docs text that says 8/12 where it describes the application limit.
- Update `tests/inflight-guard-contract.test.ts` and add focused contracts proving no 8/12 hard cap remains in generation count paths.

## Verification

- `node --test` focused count/capacity tests.
- `npm run build:server`
- `npm run typecheck`
- `npm run typecheck:tests`
- `cd ui && npm run build`
- `npm test` if focused verification passes and runtime allows.

## Implementation Result

- Added `limits.maxGeneratedImages` with `IMA2_MAX_GENERATED_IMAGES` support and default `24`.
- Raised default `limits.maxParallel` to `24` and wired `MAX_CONCURRENT_JOBS` to that runtime config value.
- Replaced classic, multimode, OAuth, Responses, Grok, Agent, and CLI hard-coded generation count clamps with the configured generation-count limit.
- Added `ui/src/lib/generationLimits.ts` and routed CountPicker plus persisted count normalization through it.
- Updated `/api/capabilities` so clients see `limits.maxGeneratedImages` and an enforced `limits.maxParallel`.
- Updated UI i18n strings, API/CLI/FAQ/structure docs, and writable config key metadata.
- Added `tests/generation-limit-unlock-contract.test.js` and refreshed affected contracts.

## Verification Result

- `npm run typecheck` passed.
- `npm run typecheck:tests` passed.
- `npm run build:server` passed.
- `npm run build:cli` passed.
- `npm run ui:build` passed.
- `node --test tests/agent-mode-auto-planner-contract.test.ts tests/cli-capabilities-contract.test.js tests/multimode-ui-contract.test.js tests/generation-limit-unlock-contract.test.js` passed.
- `node --test tests/server.test.js tests/generation-limit-unlock-contract.test.js tests/generation-controls-ux-contract.test.js tests/slash-command-menu-contract.test.ts` passed.
- `npm test` passed: 1003 tests, 134 suites, 0 failures.

## Post-Commit Audit Follow-Up

An independent verifier found one remaining Agent Mode path still capped at 8:

- `lib/agentSettings.ts` normalized `variants`, `maxAutoVariants`, and `parallelism` with max `8`.
- `ui/src/lib/agentGenerationSettings.ts` defaulted `maxAutoVariants` to `8`.
- `ui/src/components/agent/AgentQualityPanel.tsx` used `max={8}` for manual variants, auto max variants, and parallelism.
- `structure/01-file-function-map.md` still described `CountPicker.tsx` as `1-8`.

Follow-up patch:

- Server Agent generation settings now derive variant caps from `config.limits.maxGeneratedImages` and parallelism caps from `config.limits.maxParallel`.
- Frontend Agent generation settings now export `MAX_AGENT_VARIANTS` and `MAX_AGENT_PARALLELISM` from the shared frontend generation limit.
- Agent quality inputs now use those shared max constants instead of literal `8`.
- Contract tests now assert Agent settings normalize 24-count values and the Agent quality panel has no `max={8}` controls.

Follow-up evidence:

- Reproduction script after patch returned `variants: 24`, `maxAutoVariants: 24`, `parallelism: 24`, `/generate 25 -> 24`, and `/parallelism 25 -> 24`.
- `npm run build:server` passed and emitted Agent settings JS with config-derived caps.
- `node --test tests/generation-limit-unlock-contract.test.js tests/agent-mode-auto-planner-contract.test.ts tests/agent-mode-right-sidebar-contract.test.js tests/agent-mode-frontend-contract.test.js` passed: 17 tests, 0 failures.
- `npm run typecheck` passed.
- `npm run typecheck:tests` passed.
- `npm run ui:build` passed.
- `npm test` passed: 1004 tests, 134 suites, 0 failures.

## Second Audit Follow-Up

Independent stop audit found one more Agent Mode generation-count path:

- `lib/agentGenerationPlanner.ts` only recognized explicit natural-language counts through 8.
- Plain prompts such as `make 12 image variants`, `make 24 image variants`, and `make twenty-four image variants` fell through to the ambiguous multi-variant default of 3.

Follow-up patch:

- Added a numeric count parser for Agent natural-language fanout requests so explicit numeric counts are accepted up to the configured generation cap.
- Added English/Korean word forms for 12 and 24, with longer count words checked before shorter words to avoid `twenty-four` matching `four` or `스물네` matching `네`.
- Added regression coverage proving Agent natural-language fanout plans 12 and 24 variants.
- Aligned CLI reference attachment validation with `config.limits.maxRefCount` and routed the PromptComposer reference display through the shared frontend `MAX_REFERENCE_IMAGES` constant. The default behavior remains 5 references, but the source of truth is no longer duplicated locally in those paths.

Second follow-up evidence:

- Reproduction script now returns 12 planned variants for `make 12 image variants`, 24 for `make 24 image variants`, 24 for `make twenty-four image variants`, and 24 for `스물네 가지 시안 만들어줘`.
- `node --test tests/generation-limit-unlock-contract.test.js tests/agent-mode-auto-planner-contract.test.ts tests/cli-feature-parity-contract.test.js` passed: 17 tests, 0 failures.
- `npm run typecheck` passed.
- `npm run typecheck:tests` passed.
- `npm run build:server` passed.
- `npm run build:cli` passed.
- `npm run ui:build` passed.
- `npm test` passed: 1006 tests, 134 suites, 0 failures.
- Residual pattern search for generation-count/reference hard caps found only contract-test guard regexes and unrelated canvas stroke-width UI (`Math.min(8, ...)`), not image generation limits.

## Third Audit Follow-Up

Independent stop audit found that frontend reference-count paths still used a local `5` fallback instead of the server capabilities/config source.

Follow-up patch:

- Added a frontend capabilities API client for `/api/capabilities`.
- Added `referenceLimit` to the app store and `syncCapabilities()` to load `limits.maxRefCount`.
- Routed classic references, node references, direct data URL references, and PromptComposer display/room calculations through `referenceLimit`.
- Kept `DEFAULT_REFERENCE_IMAGE_LIMIT = 5` only as a startup/fetch-failure fallback matching the current server default.
- Added contract coverage proving the frontend reference limit syncs from capabilities and no longer uses local `MAX_REFERENCE_IMAGES`/`MAX_REFS` caps in active reference paths.

Third follow-up evidence:

- Residual reference-cap search found no active `MAX_REFERENCE_IMAGES`, `MAX_REFS`, `refs.length > 5`, or `max 5 --ref` matches.
- `node --test tests/generation-limit-unlock-contract.test.js tests/canvas-version-contract.test.js tests/cli-feature-parity-contract.test.js tests/agent-mode-auto-planner-contract.test.ts` passed: 25 tests, 0 failures.
- `npm run typecheck` passed.
- `npm run typecheck:tests` passed.
- `npm run ui:build` passed.
- `npm test` passed: 1007 tests, 134 suites, 0 failures.
