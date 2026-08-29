---
created: 2026-06-11
status: fixed / archived
tags: [ima2-gen, node-mode, gallery, references, generation-retry]
commits:
  - f8812cb4fc94deb0984ed3487d37d60e13320f97
  - 52fd176f3b26a4cef23526faa83764b205d5fc83
---

# Node Gallery Reference Regressions

This folder records two same-session Node Mode fixes found after testing
gallery-to-node reference workflows.

## Scope

The affected workflow is:

```text
Gallery / history item
-> drag into a Node Mode image node reference area
-> generate from that node with an explicit image input
```

Two separate bugs were fixed:

1. Gallery/history drags did not attach as node-local references.
2. Node generation with an input image could call the upstream image provider
   twice inside one `/api/node/generate` request when the first image response
   was empty.

## Why This Matters

Node-local references are separate from Classic composer references. A gallery
tile drag carries an internal `application/ima2-ref` payload instead of an OS
file, so the node drop path needs explicit URL handling. Once that path works,
image-input node generation must also avoid spending a second provider call on
an identical retry after the model returns an empty image response.

## Source Of Truth

Main source files:

- `ui/src/components/ImageNode.tsx`
- `ui/src/store/storeNodeRefImpl.ts`
- `ui/src/store/storeTypes.ts`
- `ui/src/store/useAppStore.ts`
- `routes/nodes.ts`

Regression tests:

- `tests/node-gallery-drop-contract.test.js`
- `tests/node-streaming-sse.test.ts`

## Closeout Verification

Fresh verification after the second patch:

```bash
npm run typecheck
npm run typecheck:tests
node --test tests/node-streaming-sse.test.ts
node --test tests/node-validation-error-contract.test.ts tests/node-generation-lock-contract.test.js tests/node-gallery-drop-contract.test.js
npm test
```

Result:

```text
typecheck: pass
typecheck:tests: pass
targeted node tests: pass
npm test: 994 passed, 0 failed
```

