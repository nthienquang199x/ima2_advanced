---
created: 2026-06-11
status: fixed / archived
tags: [ima2-gen, node-mode, patch-log]
---

# Patch Log

## Patch 1: Gallery Drag Payloads Into Node References

Commit:

```text
f8812cb4fc94deb0984ed3487d37d60e13320f97 fix(node): accept gallery drag (ima2-ref) drops on node reference area
```

User report:

```text
현재 갤러기 -> 노드모드 드랍이 안되는 버그 수정
```

### Root Cause

Gallery/history tiles drag an internal `application/ima2-ref` JSON payload with
a generated media URL. `ImageNode` only read `e.dataTransfer.files`, which
works for local OS file drops but ignores internal gallery drags.

Classic `PromptComposer` already had an internal reference payload path; Node
Mode did not.

### Changed Files

### ui/src/components/ImageNode.tsx — read internal reference drops
- **Changes**: `onDropRefs` now checks `application/ima2-ref` before file drops,
  parses `{ image, url, filename }`, and calls `addNodeReferenceFromUrl`.
- **Impact**: node-local reference drops now accept gallery/history tiles as
  references without involving Classic composer state.
- **Verification**: `tests/node-gallery-drop-contract.test.js` asserts the
  drop handler reads the internal payload and calls the URL-based store action.

### ui/src/store/storeNodeRefImpl.ts — add URL-based node reference import
- **Changes**: added `addNodeReferenceFromUrlImpl`, which compresses image
  sources through `compressReferenceSource` and extracts the last frame from
  video sources via `extractLastFrame`.
- **Impact**: gallery/history image and video assets can become node-local
  references from URL payloads.
- **Verification**: `tests/node-gallery-drop-contract.test.js` asserts video
  frame extraction and image compression routing.

### ui/src/store/storeTypes.ts and ui/src/store/useAppStore.ts — expose action
- **Changes**: added the `addNodeReferenceFromUrl` store action type and wired
  it into the composed store.
- **Impact**: `ImageNode` can use the new URL import path without reaching into
  implementation modules.
- **Verification**: `tests/node-gallery-drop-contract.test.js` asserts the
  public store action signature exists.

### Verification

```text
tsc -b: pass
vite build: pass
npm test: 993 passed, 0 failed
```

## Patch 2: Image-Input Node Requests Must Not Auto-Retry Identically

Commit:

```text
52fd176f3b26a4cef23526faa83764b205d5fc83 fix(node): avoid retrying image-input generation
```

User report:

```text
지금 노드 모드에서 이미지 넣고 제너레이션 돌리면 두번 호출이 되는 버그가 발견됨
```

### Root Cause

`routes/nodes.ts` used a fixed same-request retry loop for node generation:

```text
MAX_RETRIES = 1
```

That meant a node request with explicit input images could call the upstream
provider twice if the first response produced no image. This was especially
visible after Patch 1 because gallery drops now correctly create node-local
references.

For image-input node requests, an identical automatic retry does not add a new
fallback strategy; it repeats the same reference-bearing payload and can spend
provider quota twice.

### Changed Files

### routes/nodes.ts — limit image-input attempts to one
- **Changes**: replaced fixed retry count with `maxAttempts`. Requests with
  `inputImageCount > 0` now get one attempt; text-only root generation keeps
  the previous two-attempt behavior.
- **Impact**: node generation with parent images or node-local references no
  longer sends a duplicate upstream image request after an empty image response.
  Text-only node generation keeps the existing retry tolerance.
- **Verification**: `tests/node-streaming-sse.test.ts` now covers a reference
  image request that receives an empty SSE response and asserts only one fake
  OAuth upstream hit.

### tests/node-streaming-sse.test.ts — lock the one-hit contract
- **Changes**: added an empty fake OAuth SSE response path and a regression test
  for reference-bearing node generation.
- **Impact**: future changes to Node Mode retry behavior will fail tests if
  image-input requests start retrying identically again.
- **Verification**: `node --test tests/node-streaming-sse.test.ts` passes.

### Verification

```text
npm run typecheck: pass
npm run typecheck:tests: pass
node --test tests/node-streaming-sse.test.ts: pass
node --test tests/node-validation-error-contract.test.ts tests/node-generation-lock-contract.test.js tests/node-gallery-drop-contract.test.js: pass
npm test: 994 passed, 0 failed
```

