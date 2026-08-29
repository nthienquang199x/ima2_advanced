---
created: 2026-06-09
tags: [ima2-gen, url-continue, provider-url-reference, frontend, pabcd]
---

# URL Reference Lifecycle Plan

## Problem

The prompt composer now exposes an active provider URL reference badge, but the
state is still cleared by unrelated generation completion paths. This makes the
badge disappear when another image or video job finishes, even though the user
did not explicitly clear the URL reference.

## Root Cause

`providerUrlReference` is treated like one-shot transient state:

- `ui/src/store/storeGenImpl.ts` clears it in both classic and multimode
  generation `finally` blocks.
- `ui/src/store/storeVideoImpl.ts` clears it in the video generation `finally`
  block.

Reference image chips remain until explicitly removed. URL references should
follow the same visible lifecycle now that the composer has an explicit clear
button.

## Plan

### MODIFY `ui/src/store/storeGenImpl.ts`

Remove `providerUrlReference: null` from generation cleanup paths.

Before:

```ts
return {
  activeGenerations: Math.max(0, state.activeGenerations - 1),
  inFlight: remaining,
  activeFlightIds: nextFlights,
  multimodePreviewFlightId: nextPreview,
  multimodeSequences: nextSequences,
  providerUrlReference: null,
};
```

After:

```ts
return {
  activeGenerations: Math.max(0, state.activeGenerations - 1),
  inFlight: remaining,
  activeFlightIds: nextFlights,
  multimodePreviewFlightId: nextPreview,
  multimodeSequences: nextSequences,
};
```

Before:

```ts
set({
  activeGenerations: Math.max(0, get().activeGenerations - 1),
  inFlight: remaining,
  providerUrlReference: null,
});
```

After:

```ts
set({
  activeGenerations: Math.max(0, get().activeGenerations - 1),
  inFlight: remaining,
});
```

### MODIFY `ui/src/store/storeVideoImpl.ts`

Remove `providerUrlReference: null` from video cleanup.

Before:

```ts
set({ inFlight: remaining, activeGenerations: remaining.length, videoProgress: null, providerUrlReference: null });
```

After:

```ts
set({ inFlight: remaining, activeGenerations: remaining.length, videoProgress: null });
```

### MODIFY `tests/direct-mode-visual-contract.test.js`

Extend the existing prompt-composer visual contract to prove the URL reference
lifecycle is explicit-clear only:

- `PromptComposer.tsx` renders the URL reference clear button.
- `storeGenImpl.ts` does not clear `providerUrlReference` in generation cleanup.
- `storeVideoImpl.ts` does not clear `providerUrlReference` in video cleanup.
- Local reference replacement paths clear stale URL references before adding
  base64/image references, while `continueFromItemAsUrl()` sets the provider URL
  again after the shared normal continue setup.

### MODIFY `ui/src/store/storeReferenceImpl.ts`

Clear `providerUrlReference` whenever the user explicitly creates a local
reference path (`clearReferences`, file refs, current-image refs, canvas-version
refs). This prevents an old URL reference from silently overriding a later normal
`Continue here`.

### MODIFY `ui/src/store/storeUIImpl.ts`

Clear `providerUrlReference` when `addReferenceDataUrlImpl()` adds a local data
URL reference, covering video last-frame references and metadata restore refs.

## Verification

- `node --test tests/direct-mode-visual-contract.test.js`
- `npm run typecheck`
- `cd ui && npm run build`
- Browser check on the running local app:
  1. Click `URL continue`.
  2. Confirm the purple composer badge appears.
  3. Trigger or simulate unrelated gallery/current-image changes.
  4. Confirm the badge persists until clicked.

## Non-Goals

- Do not change server provider URL behavior.
- Do not change how provider URLs are sent in image/video request payloads.
- Do not persist provider URL references across browser reloads in this pass.
