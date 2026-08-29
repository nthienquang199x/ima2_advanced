# 10 Implementation Evidence

## Scope

Hardened URL Continue so Grok provider URLs work across the real Classic, multimode, and video continuation paths, while queued async submissions can be canceled before the server accepts a job.

## Changes

### `/Users/jun/Developer/new/700_projects/ima2-gen/routes/generate.ts`
- Classic `/api/generate` now converts incoming `providerUrl` into the Grok reference list.
- Grok and grok-api count `providerUrl` toward the 3-reference cap.
- Grok planning/generation now receives the merged `grokRefs`, causing providerUrl continuation to use `/v1/images/edits`.

### `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/components/ResultActions.tsx`
- Added `PROVIDER_URL_TTL_MS`.
- URL Continue button is now hidden for videos.
- URL Continue click path rechecks TTL before setting the provider URL reference.

### `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/lib/asyncJobSubmit.ts`
- Added `mergeAbortSignals`.
- Async capacity retry now passes `AbortSignal` into `fetch`.
- Retry-After waits now clear timers and reject on abort, preventing ghost submissions after user cancel.

### `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/lib/api-generation.ts`
- Classic, multimode, and video async stream clients now use a local submit controller merged with caller abort signal.
- Timeout/user abort now aborts pre-accept POST retry loops before calling server cancel.
- Video request/done types now include `providerUrl`.

### `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/lib/nodeApi.ts`
- Node async stream client now uses a local submit controller merged with caller abort signal.

### `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/store/flightAbortRegistry.ts`
- Added shared flight abort registry for classic, multimode, video, and node jobs.

### `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/store/storeGenImpl.ts`
- Classic and multimode jobs register/clear local abort controllers.

### `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/store/storeVideoImpl.ts`
- Video generation and image animation jobs register/clear local abort controllers.

### `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/store/storeNodeGenImpl.ts`
- Node jobs now register/clear local abort controllers and pass the signal to `postNodeGenerateStream`.

### `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/store/storeUIImpl.ts`
- General inflight cancel now aborts the local queued retry loop before calling the server cancel endpoint.

### `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/types.ts`
- `EmbeddedGenerationMetadata` and `GenerateRequest` now include provider URL fields.

### `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/i18n/en.json`
### `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/i18n/ko.json`
- Added URL Continue expired toast copy.

### Tests
- `/Users/jun/Developer/new/700_projects/ima2-gen/tests/api-provider-parity.test.ts`
  - Added Classic providerUrl I2I regression for Grok edits endpoint.
  - Added providerUrl + 3 refs cap regression.
- `/Users/jun/Developer/new/700_projects/ima2-gen/tests/async-capacity-retry-behavior.test.ts`
  - Added behavioral retry/abort tests.
- `/Users/jun/Developer/new/700_projects/ima2-gen/tests/async-capacity-retry-contract.test.js`
  - Extended source contract for merged signals and node store abort wiring.
- `/Users/jun/Developer/new/700_projects/ima2-gen/tests/current-image-actions-readiness-contract.test.js`
  - Extended source contract for provider URL TTL constant and video guard.

## Verification

- `npm run typecheck` — PASS.
- `cd /Users/jun/Developer/new/700_projects/ima2-gen/ui && npm run build` — PASS.
- `npm run build:server` — PASS.
- `node --test tests/api-provider-parity.test.ts tests/async-capacity-retry-contract.test.js tests/async-capacity-retry-behavior.test.ts tests/current-image-actions-readiness-contract.test.js` — PASS, 22/22.
- `node --test tests/node-context-policy.test.js tests/server-fallback-contract.test.js tests/async-capacity-retry-contract.test.js` — PASS, 7/7 after preserving the node source-contract call shape.
- `npm test` — PASS, 985/985.
- `git diff --check` — PASS.

## Live Smoke

Server: `http://127.0.0.1:3464`.

- Grok source image generation returned provider URL:
  - `https://imgen.x.ai/xai-imgen/xai-tmp-imgen-f01ba86e-963d-462b-a9b0-fbaa05402154.jpeg`
- Classic providerUrl I2I via `/api/generate` — PASS.
  - Output: `/generated/1780930147069_559520d8_0.jpeg`
  - Output provider URL: `https://imgen.x.ai/xai-imgen/xai-tmp-imgen-726547e6-3f13-4e64-8043-4ffb02f8a375.jpeg`
- Multimode providerUrl I2I via `/api/generate/multimode` SSE — PASS.
  - `image` event count: 1
  - Output provider URL: `https://imgen.x.ai/xai-imgen/xai-tmp-imgen-788443e0-e85c-4c4e-aee7-bb08455a70aa.jpeg`
- Video providerUrl I2V via `/api/video/generate` SSE — PASS.
  - Output: `/generated/1780930308650_08debe82.mp4`
  - Output provider URL: `https://vidgen.x.ai/xai-vidgen-bucket/xai-video-742568df-7a4a-4c6c-84fa-5a86a6303f3e.mp4`

## CU Verification

Using Computer Use against Google Chrome on `http://127.0.0.1:3464/`:

- Selected video result `1780930308650_08debe82.mp4` showed no URL Continue button.
- Selected Grok image result showed `URL continue` button.

## Review

- `료` backend read-only audit: DONE. Noted non-blocking optional coverage for grok-api/provider=api/non-capacity 429.
- `니지카` first frontend audit: NEEDS_FIX for missing node store abort wiring.
- Node store abort wiring was fixed and covered by contract test.
- `니지카` final re-audit could not start because the employee session failed with `Session does not exist`.
- `키타` final read-only audit: DONE. Verified Classic providerUrl edit refs, URL Continue UI gating, local abort wiring for classic/multimode/video/node, InFlight cancel ordering, types, i18n, tests, and devlog consistency.
