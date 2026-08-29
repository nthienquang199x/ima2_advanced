# Phase 2-5 Size, UI, Docs, Verification

## Size Mapping

Input is ima2's resolved size string:

- `auto` -> `aspect_ratio: "auto"`, no explicit resolution unless user selected a 2K preset.
- `1024x1024` -> `aspect_ratio: "1:1"`, `resolution: "1k"`.
- `1536x1024` -> `aspect_ratio: "3:2"`, `resolution: "1k"`.
- `1024x1536` -> `aspect_ratio: "2:3"`, `resolution: "1k"`.
- `1360x1024` -> `aspect_ratio: "4:3"`, `resolution: "1k"`.
- `1024x1360` -> `aspect_ratio: "3:4"`, `resolution: "1k"`.
- `1824x1024` -> `aspect_ratio: "16:9"`, `resolution: "1k"`.
- `1024x1824` -> `aspect_ratio: "9:16"`, `resolution: "1k"`.
- `2048x2048`, `2048x1152`, `1152x2048` -> matching aspect, `resolution: "2k"`.
- `3840x2160`, `2160x3840` -> matching aspect, `resolution: "2k"` because xAI officially supports only `1k` and `2k`.
- Custom sizes -> reduce to closest supported `aspect_ratio`; choose `2k` when the longest edge or pixel budget is closer to 2K.

The original `size` remains in ima2 metadata. The xAI request receives only `aspect_ratio` and `resolution`.

## Frontend UX

Fixes required:

- Settings image model select must list both OpenAI and Grok models so Grok is selectable from Settings.
- Selecting a Grok model switches provider to `grok`.
- Selecting an OpenAI model while provider is Grok switches provider back to `oauth`.
- Classic controls should show `SizePicker` even when provider is Grok because Grok now maps size to xAI `aspect_ratio` and `resolution`.
- Grok compatibility note should say format/moderation/reasoning are OpenAI-only, but size is supported through xAI aspect/resolution.

## Docs

Update:

- `/Users/jun/Developer/new/700_projects/ima2-gen/docs/API.md`
- `/Users/jun/Developer/new/700_projects/ima2-gen/docs/CLI.md`
- `/Users/jun/Developer/new/700_projects/ima2-gen/structure/02-runtime-providers.md` if present; otherwise nearest provider architecture doc.
- This devlog lane.

Docs must explicitly say:

- `ima2 serve` bundles and starts progrok.
- Grok generation uses a planner/tool pipeline, not direct prompt-only image calls.
- xAI size is mapped to `aspect_ratio` and `resolution`; `size` is not sent upstream.

## Verification

Automated:

- `npm run typecheck`
- `npm run typecheck:tests`
- `npm run build:server`
- `npm run build:cli`
- `npm run ui:build`
- Targeted Grok adapter tests
- UI contract tests
- `npm test`

Live:

- Start `ima2 serve` on an alternate port.
- Confirm `/api/grok/status` ready.
- Generate via `/api/generate` with `provider: "grok"`, `model: "grok-imagine-image-quality"`, and a 16:9 2K size.
- Inspect logs for planner call then image call.
- Browser UI check: Settings can select Grok; right panel shows size controls; generation succeeds.
- Control employee E2E after local verification.

Employee Review:

- 료: backend/API/adapter docs and tests.
- 니지카: settings, controls, copy, clipping, user flow.
- 세이카: docs wording and source-of-truth alignment.
- Control: live visible UI E2E.
