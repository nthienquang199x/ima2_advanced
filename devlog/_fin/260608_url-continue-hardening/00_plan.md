# URL Continue Hardening

**Date:** 2026-06-08
**Status:** PABCD plan

## Part 1 — Summary

The first "Continue as URL" implementation preserved and displayed Grok provider URLs, but follow-up review found gaps in the actual default generation path. This hardening pass makes URL Continue work end-to-end for the default Classic generator, keeps multimode I2I and I2V intact, prevents video output URLs from being reused as image source URLs, and makes capacity retry cancellation safe. The result should be: fresh Grok image -> URL Continue -> Classic I2I, multimode I2I, and I2V all use the provider URL correctly, while stale or video-only URLs do not expose the wrong action.

## Findings To Fix

1. **Classic `/api/generate` ignores incoming `providerUrl`.**
   - UI sends `providerUrl` when `providerUrlReference` exists.
   - `routes/generate.ts` currently passes only `refCheck.refDetails` to Grok.
   - Default Classic URL Continue can silently become text-to-image instead of I2I.

2. **Video items can satisfy the URL Continue button condition.**
   - `ResultActions.tsx` checks Grok provider + providerUrl + TTL.
   - Grok video sidecars store output mp4 `providerUrl`.
   - Reusing that mp4 URL as an image source is wrong.

3. **Capacity retry loops are not fully abortable.**
   - `submitAsyncJobWithCapacityRetry` does not pass `signal` to `fetch`.
   - stream timeout rejects the UI promise but does not abort the retry loop.
   - generic in-flight cancel only calls server cancel, which cannot cancel a queued client retry before a server job exists.

4. **Video provider URL types drift from runtime payloads.**
   - `VideoGenerateRequest` accepts `providerUrl` at runtime but the type omits it.
   - `VideoGenerateDone` omits the server's `providerUrl` field.

5. **Tests are too source-regex-heavy for retry behavior.**
   - Need behavioral tests for 429 retry, abort during wait/fetch, and no ghost submit after abort.

## Part 2 — Diff-Level Plan

### MODIFY `routes/generate.ts`

Add boundary parsing for provider URL before the provider reference cap guard:

```diff
 const incomingProviderUrl =
   typeof req.body?.providerUrl === "string" && req.body.providerUrl.startsWith("http")
     ? req.body.providerUrl
     : null;
 const grokRefs = incomingProviderUrl
   ? [{ b64: "", url: incomingProviderUrl }, ...refCheck.refDetails]
   : refCheck.refDetails;
```

Then update the provider reference limit so Grok/Grok API count the URL reference too:

```diff
- if ((activeProvider === "grok" || activeProvider === "agy" || activeProvider === "grok-api" || activeProvider === "gemini-api") && refCheck.refs.length > 3) {
+ const providerRefCount = activeProvider === "grok" || activeProvider === "grok-api"
+   ? grokRefs.length
+   : refCheck.refs.length;
+ if ((activeProvider === "grok" || activeProvider === "agy" || activeProvider === "grok-api" || activeProvider === "gemini-api") && providerRefCount > 3) {
```

Use `grokRefs` for:

- Grok reference cap/log metadata where applicable. The cap must use `grokRefs.length`, not only `refCheck.refs.length`, so `providerUrl + 3 base64 refs` cannot exceed the upstream Grok edit limit.
- `planGrokImage(... references: grokRefs, referenceCount: grokRefs.length ...)`
- `generateViaGrok(... references: grokRefs ...)`

Keep non-Grok providers unchanged. Keep `providerUrl` and `createdAt` response preservation from commit `627d8f3`.

### MODIFY `ui/src/components/ResultActions.tsx`

Prevent video output provider URLs from showing the image URL Continue button:

```diff
 const PROVIDER_URL_TTL_MS = 60 * 60 * 1000;
 const providerUrlAlive = Boolean(!isVideo && ...)
```

Re-check TTL at click time before calling `continueFromItemAsUrl`.

### MODIFY `ui/src/lib/api-generation.ts`

Add `providerUrl?: string` to `VideoGenerateRequest` and `providerUrl?: string | null` to `VideoGenerateDone`.

Introduce or import a shared `mergeAbortSignals` helper and use a local submit abort controller per async stream call:

```ts
const submitController = new AbortController();
const submitSignal = mergeAbortSignals(options.signal, submitController.signal);
```

On timeout, abort the submit controller before rejecting. Keep `cancelInflight(requestId)` for server-side jobs.

The helper can live in `ui/src/lib/asyncJobSubmit.ts` if kept small and shared by `api-generation.ts` and `nodeApi.ts`.

### MODIFY `ui/src/lib/asyncJobSubmit.ts`

Make retry submission behaviorally abortable:

- Pass `signal` to `fetch`.
- Avoid accumulating abort listeners in `wait` by removing the listener after timer resolution/rejection.
- Preserve same `requestId` for every retry.
- Continue only on `429 TOO_MANY_JOBS`.

Add `mergeAbortSignals(...signals)` here unless a better existing local utility is found.

### MODIFY `ui/src/lib/nodeApi.ts`

Apply the same local submit abort pattern to node stream submission.

### MODIFY `ui/src/store/storeGenImpl.ts`

Extend the existing `flightControllers` registry beyond multimode:

- `runGenerateImpl`: create `AbortController`, register `flightId`, call `postGenerateStream(payload, { signal: controller.signal })`, delete registry entry in `finally`.
- `generateMultimodeImpl`: keep the current controller pattern.
- `abortFlight(id)`: remains the local cancel entrypoint for Classic and multimode.

This is required because generic `InFlightList` cancellation uses request IDs, not the multimode-only cancel path.

### MODIFY `ui/src/store/storeUIImpl.ts`

Call local abort before or alongside `cancelInflight(requestId)` so queued retries with no server job also stop.

### MODIFY `ui/src/store/storeVideoImpl.ts`

Add a local video flight abort registry or reuse a small shared abort registry:

- `runVideoGenerateImpl`: create `AbortController`, register `flightId`, call `postVideoGenerateStream(..., { signal: controller.signal })`, delete in `finally`.
- `animateImageImpl`: either register a controller too or explicitly document why the existing server-side cancel path is sufficient for that entrypoint.
- Generic in-flight cancel must abort these local video controllers before or alongside server cancel.

Align immediate video item handling with the updated typed response only if video provider URLs remain intentionally stored. Do not let those URLs drive the image URL Continue button.

### MODIFY `ui/src/types.ts`

Optional low-risk type alignment:

- Add `providerUrl?: string | null` to `EmbeddedGenerationMetadata`.
- Keep `GenerateItem.providerUrl` as currently added.

### MODIFY Tests

Add or update tests:

1. `tests/api-provider-parity.test.ts`
   - `/api/generate` with Grok `providerUrl` uses `/v1/images/edits`, not `/v1/images/generations`.
   - returned body preserves the newly returned providerUrl.

2. `tests/current-image-actions-readiness-contract.test.js`
   - image item: URL Continue visible only for fresh Grok image provider URLs.
   - video item: URL Continue hidden even if providerUrl and createdAt exist.

3. `tests/async-capacity-retry-contract.test.js` or new `.test.ts`
   - behavioral fake-fetch tests for:
     - 429 `TOO_MANY_JOBS` then 202 resolves.
     - non-capacity 429 rejects.
     - abort during retry wait rejects and performs no extra POST.
     - fetch receives the AbortSignal.
     - timeout/local abort prevents a later retry submit.

4. Existing source-order test can remain as a light contract.

## Verification Plan

Commands:

```bash
npm run typecheck
npm run typecheck:tests
npm run test:inventory
node --test tests/api-provider-parity.test.ts tests/current-image-actions-readiness-contract.test.js tests/async-capacity-retry-contract.test.js
npm test
npm run build:server
npm run ui:build
git diff --check
```

Live smoke:

1. Generate fresh Grok image and capture providerUrl.
2. Classic `/api/generate` with that providerUrl must use I2I/edit path and complete.
3. `/api/generate/multimode` with that providerUrl must complete.
4. `/api/video/generate` with that providerUrl must complete as URL source I2V.
5. UI/CU: image result shows URL Continue; video result does not.

## Non-Goals

- Do not recover provider URLs for old history items whose sidecars lack the URL.
- Do not change CLI per-job SSE compatibility.
- Do not remove existing base64 Continue Here behavior.
