# WP1 — GPT-5.6 sol/terra/luna + `max` reasoning rollout

Mirrors opencodex `d8c44b7`. Defaults unchanged (`gpt-5.4-mini`, reasoning default
untouched). New slugs: `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`. New
reasoning effort: `max` (ladder position: after `xhigh`). Access errors for 5.6
surface from upstream OAuth; we only stop pre-blocking.

## File change map (MODIFY unless noted)

Server model validation:
- `config.ts:263` — `imageModels.valid` += 3 slugs; `:270` `validReasoningEfforts` += `max`.
- `lib/imageModels.ts:4` — `VALID_IMAGE_MODELS` += 3; `:7` `VALID_REASONING_EFFORTS` += `max`;
  error strings `:26` (`none, low, medium, high, xhigh, max`) and `:53` (model list).
- `lib/oauthProxy/runtime.ts:8` — `VALID_REASONING_EFFORTS` += `max`.
- `lib/agentSettings.ts:8` — `REASONING_EFFORTS` += `max`.
- `lib/agentTypes.ts:28` — union += `"max"`.
- `lib/promptBuilder/constants.ts:1` — `VALID_PROMPT_BUILDER_MODELS` += 3;
  `lib/promptBuilder/requestSchema.ts:15` error string.
- `routes/capabilities.ts:5` — `GROK_PLANNER_MODELS` += 3 (planner may use 5.6).

CLI:
- `bin/commands/gen.ts:12,64,101,103,105` — KNOWN_IMAGE_MODELS, help, die msgs, reasoning set.
- `bin/commands/edit.ts:12,46,52,68,70,72` — same shape.
- `bin/commands/multimode.ts:48,53,69,75` — same shape.
- `bin/commands/node.ts:60,65` — reasoning set + die msg.
- `bin/commands/prompt-sub/build.ts:16,24` — help text.
- `bin/commands/defaults.ts` — no change (reads config sets).
- `bin/lib/error-hints.ts:5-6` — mention 5.6 slugs.

UI:
- `ui/src/types.ts:19` — `OpenAIImageModel` += 3.
- `ui/src/types.ts:90,168,186,214` — additional reasoning unions += `"max"`
  (audit blocker #2).
- `ui/src/store/promptBuilderStore.ts:18` — `PromptBuilderModel` += 3.
- `ui/src/components/prompt-builder/PromptBuilderModelMenu.tsx:5` — hardcoded
  menu list += 3 (audit blocker #1).
- `ui/src/lib/nodeApi.ts:15,36` — reasoning unions += `"max"` (audit blocker #2).
- `ui/src/components/agent/agentTypes.ts:28` — reasoning union += `"max"`
  (audit blocker #2).
- `ui/src/lib/imageModels.ts` — `IMAGE_MODEL_OPTIONS` += 3 rows (shortLabels
  `5.6s`/`5.6t`/`5.6l`, fullLabelKeys `settings.imageModel.gpt56Sol|Terra|Luna`).
- `ui/src/lib/agentModelOptions.ts` — += 3 oauth rows.
- `ui/src/lib/reasoning.ts` — `ReasoningEffort` += `"max"`, option row
  (shortLabel `max`, key `settings.reasoning.max`), `REASONING_SHORT.max = "M"`.
- `ui/src/store/storeTypes.ts:119` — union += `"max"`.
- `ui/src/i18n/en.json` + `ko.json` — keys `settings.imageModel.gpt56Sol/Terra/Luna`,
  `settings.reasoning.max`.

Docs/skills (published to npm via `package.json` files[], audit blocker #3):
- `docs/CLI.md:57`, `docs/FAQ.md:124` — model list mentions += 5.6 slugs + `max`.
- `skills/ima2/SKILL.md:59,231,341` — model/effort lists += 5.6 slugs + `max`.

Build artifacts (audit blocker #4): compiled `.js` siblings of touched `.ts`
files are tracked (e.g. `config.js`, `lib/imageModels.js`, `bin/commands/*.js`).
B closes with `npm run build:server && npm run build:cli` and commits the
regenerated output; `npm run ui:build` refreshes the served `ui/dist`
(gitignored, needed for the live capabilities probe only).

Tests:
- `tests/image-model.test.ts` — accept cases for 3 slugs; `max` reasoning accept
  + invalid-still-rejected case (activation evidence for the widened validators).
- `tests/config.test.js:80` — valid list assertion += 3 (sorted).
- New: `tests/gpt56-rollout-contract.test.ts` — drives
  `normalizeImageModel`/`normalizeReasoningEffort` with `gpt-5.6-*` + `max`,
  checks error strings, checks CLI sources and UI unions mention the slugs
  (readSource contract style). Inventory: regenerate
  `docs/migration/runtime-test-inventory.md` via `node scripts/classify-tests.mjs`
  (auto-detects new test files; stale inventory fails `--check`).

## Audit synthesis (A, 2026-07-07, reviewer: gpt-5.5 explorer)

Verdict FAIL → 4 blockers, all ACCEPTED and folded in above:
1. PromptBuilderModelMenu.tsx hardcoded list (missed surface).
2. Extra reasoning unions: ui/src/types.ts x4, nodeApi.ts x2, agent/agentTypes.ts.
3. docs/ + skills/ ship in the npm package; lists must be updated.
4. Tracked compiled .js artifacts require build:server/build:cli in B.
Reviewer confirmed: `max` reaches the OAuth payload once validators widen
(providerOptions.ts:70-88 → generators.ts:83,99; responsesImageAdapter.ts:322,406);
REASONING_SHORT map is exhaustiveness-checked; inventory auto-detects new tests.

## Accept criteria

- `normalizeImageModel({}, "gpt-5.6-sol"|"terra"|"luna")` → `{model}` (was 400).
- `normalizeReasoningEffort({}, "max")` → `{effort:"max"}` (was 400) — activation
  scenario: the previously-rejecting branch now passes; inverse guard
  (`"ultra"` still 400) proves the validator still rejects unknowns.
- `node bin/ima2.js capabilities --json` lists the 3 slugs under
  `valid.imageModels.supported` and `max` under `reasoningEfforts`.
- Full gates green: typecheck, typecheck:tests, test (1066+ → expect +N), inventory.

## Out of scope

- No default flips; no `ultra`; no removal of `gpt-5.3-codex-spark` unsupported entry.
