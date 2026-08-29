---
title: "UX Hardening Details"
status: planned / issue split complete
created: 2026-05-15
tags: [ux, gallery, canvas, multimode, node-mode]
---

# UX Hardening Details

## Review Status

Frontend employee dispatch initially failed with:

```text
Error: fetch failed
```

The frontend employee report was later received and folded into this file. The
employee performed read-only inspection only: no code edits, commits, pushes, or
GitHub changes.

## Lane I — Gallery Deletion, Identity, And Large-Session Aftercare

Priority: P0

Related issue:

- #63 (closed as shipped)
- #68

New issue candidate:

```text
#68 Gallery UX: harden deletion aftercare, duplicate identity, and large-session loading
```

### Findings

The delete-aftercare patch appears present for the basic viewer and Canvas Mode:

- `ResultActions` accepts `onAfterDeleteFocus`;
- soft delete and hard delete call it in `finally`;
- basic viewer and Canvas Mode provide focusable containers and recovery
  callbacks.

Anchors:

- `ui/src/components/ResultActions.tsx:7-10`
- `ui/src/components/ResultActions.tsx:115-129`
- `ui/src/components/Canvas.tsx`
- `ui/src/components/canvas-mode/CanvasModeWorkspace.tsx`

Remaining UX gaps:

- Gallery modal delete uses `trashHistoryItem(item)` without a modal-local
  focus/selection/scroll aftercare policy.
- `HistoryStrip` dedupes visible items by `filename ?? image`, but Gallery modal
  uses `history.filter(isGalleryVisibleItem)` and does not obviously share that
  identity guard.
- Date gallery uses virtualization through `GalleryDateGrid`.
- Session grouping still renders ordinary grids from grouped rows and has no
  older-load control, only a session hint.

Anchors:

- `ui/src/components/GalleryModal.tsx`
- `ui/src/components/HistoryStrip.tsx`
- `ui/src/components/gallery/GalleryDateGrid.tsx`
- `ui/src/components/gallery/GallerySessionGroups.tsx`
- `ui/src/components/gallery/GalleryLoadControls.tsx`
- `ui/src/store/useAppStore.ts`

Recommended split:

- Close #63 if the shipped focus behavior is confirmed.
- Open a follow-up for modal delete aftercare, shared gallery identity dedupe,
  session/favorites loading, and session virtualization.

Risk:

- Medium. The implementation touches multiple surfaces that all read the same
  history state but have different focus/selection behavior.

## Lane J — Multimode Progress, Partial, Timeout, And Cancel UX

Priority: P0

Related issue:

- #60 (closed as shipped)
- #69

Current code appears to implement the original progress fix:

- frontend in-flight kind accepts `multimode`;
- polling adds a multimode scope when local multimode jobs exist;
- adapter exposes `onFinalImage`;
- multimode route persists and sends each image through SSE incrementally;
- `MultimodeSequenceStatus` includes `canceled`;
- tests assert the contract.

Anchors:

- `ui/src/lib/api.ts:52`
- `ui/src/store/useAppStore.ts:307-329`
- `ui/src/store/useAppStore.ts:1425-1497`
- `lib/responsesImageAdapter.ts:173-223`
- `routes/multimode.ts:201-257`
- `routes/multimode.ts:259-341`
- `tests/multimode-ui-contract.test.js:66-82`
- `tests/multimode-backend-contract.test.js:84-97`

Remaining UX gaps:

- cancel button visibility is tied to global active generation state rather than
  the specific active multimode sequence;
- index-less partial events can be mapped by a broad `find`, which may repeat
  one partial preview across several slots;
- active generation does not necessarily disable the main Generate button,
  which may be valid for concurrent jobs but needs clearer copy/state if so.

Anchors:

- `ui/src/components/MultimodeSequencePreview.tsx`
- `ui/src/components/GenerateButton.tsx`
- `ui/src/store/useAppStore.ts`
- `routes/multimode.ts`

Recommended split:

- Comment and close #60 if the original queued/stale behavior is fixed.
- Open a narrower follow-up for sequence-specific cancel, partial slot mapping,
  and concurrent generation copy/state.

New issue candidate:

```text
#69 Multimode UX: clarify sequence cancel, partial slot mapping, and active generation state
```

Risk:

- Medium-high. SSE, polling, cancel, and timeout UX are timing-sensitive.

## Lane K — Generate As First Node

Priority: P1

Related issue:

- #59

Current shared action surface:

- classic viewer uses `ResultActions`;
- Canvas Mode also uses `ResultActions` through `imageOverride`;
- More menu currently includes ComfyUI export and permanent delete.

Anchors:

- `ui/src/components/ResultActions.tsx:1-200`
- `ui/src/components/ResultActions.tsx:173-195`

Recommended implementation direction:

- add a store action to create a ready preview root node from a `GenerateItem`;
- add menu item to `ResultActions`;
- keep `Continue Here` behavior unchanged;
- from Canvas Mode, use the visible `imageOverride` composition;
- add contract tests for menu wiring, node graph state, and Canvas override input.

## Lane L — Canvas / Viewer Action Architecture

Priority: P1

Related issues:

- #59
- #31
- #27
- #28

The frontend employee recommended not adding every new current-image action
directly into `ResultActions`, `CanvasModeWorkspace`, or `CanvasToolbar`.

Reason:

- `ResultActions` is the shared default viewer / Canvas Mode current-image
  action surface.
- Canvas Mode and toolbar files are already near the 500-line jaw limit.
- #59 first-node, #31 masked edit copy/guard, #27 SVG export, and #28 PPTX
  export all share "which current image/composition am I acting on?" semantics.

Recommended architecture:

1. Extract a current-image action menu boundary.
2. Add #59 first-node action against that boundary.
3. Add #27/#28 export actions after vector/export contracts are stable.
4. Keep #31 provider-backed mask copy and fail-closed semantics separate.

Anchors:

- `ui/src/components/ResultActions.tsx`
- `ui/src/components/canvas-mode/CanvasModeWorkspace.tsx`
- `ui/src/components/canvas-mode/CanvasToolbar.tsx`
- `ui/src/components/canvas-mode/CanvasModeFloatingToolbar.tsx`
- `ui/src/store/useAppStore.ts`

## Lane M — Canvas Export Stack

Priority: P2, but likely next after #59 or #31 decision

Related issues:

- #27
- #28

Recommended sequence:

1. #27 SVG/vector package from current annotation data model.
2. #28 PPTX export using the vector package and/or raster fallback.

Use the existing canvas library research as reference:

- `devlog/_plan/260514_canvas-library-research/README.md`

Expected implementation shape:

- serialize current annotation primitives first;
- use SVG/vector as the model boundary;
- add PPTX after vector coordinate/style contracts are stable;
- avoid a full Canvas Mode framework rewrite unless an issue proves the current
  model cannot support the required export.

## Lane N — Provider-Backed Masked Edit

Priority: P1/P2 depending on provider certainty

Related issue:

- #31

Policy:

- keep fail-closed until provider contract is verified;
- do not ship a prompt-only fallback as "masked edit";
- if guided edit remains useful, label it separately from true provider-backed
  mask/inpaint.

Implementation should include:

- provider payload verification;
- no silent fallback to full-image edit;
- UI error for unsupported provider/mask path;
- tests proving mask bytes and source image bytes stay dimension-compatible;
- CLI `edit --mask` only after #31 semantics are confirmed.

## Lane O — Provider / Capability / Settings Readiness

Priority: P1

Related issue:

- #62 (closed as shipped)
- #65

Issue:

```text
#65 UI: expose provider and capability readiness for first-run users
```

Findings:

- `ProviderSelect` exists and computes OAuth/API availability reasons, but the
  current code search suggests it may not be mounted in the main settings flow.
- Settings show model/reasoning/web-search/gallery scope, but provider readiness
  is not obvious from the generation section.
- Account settings can show OAuth/API state, but users need to know to go there.
- Generate button state is not obviously tied to provider readiness.
- OAuth status polling focuses on `starting`; `auth_required` refresh behavior
  should be verified so login state does not appear stale.

Anchors:

- `ui/src/components/ProviderSelect.tsx`
- `ui/src/components/SettingsWorkspace.tsx`
- `ui/src/components/AccountSettings.tsx`
- `ui/src/components/Sidebar.tsx`
- `ui/src/components/GenerateButton.tsx`
- `ui/src/hooks/useOAuthStatus.ts`
- `ui/src/store/useAppStore.ts`

Recommended direction:

- Add a compact provider/capability readiness panel.
- Tie UI wording to `ima2 capabilities` / `ima2 defaults` terminology.
- Keep secrets hidden; expose only booleans and actionable setup commands.

## Lane P — Prompt Library / Prompt Import UX Closeout

Priority: P2

Related issue:

- no current open GitHub issue; related to prior prompt import devlog work.

New issue candidate:

```text
Prompt Library UX: close out import workspace, source selection, and folder discoverability
```

Findings:

- Prompt import dialog already has v2-like workspace behavior: sections,
  selected count, source toggle, result/preview workspace.
- Candidate addition no longer auto-selects everything.
- Prompt library panel is import/search/favorites/list oriented.
- The UI does not expose the same "agent prompting/defaults" guidance that the
  packaged `skills/ima2/SKILL.md` exposes to CLI agents.

Anchors:

- `ui/src/components/PromptImportDialog.tsx`
- `ui/src/components/PromptLibraryPanel.tsx`
- `skills/ima2/SKILL.md`

Recommended direction:

- Treat as closeout QA rather than a large feature.
- Add small empty-state/source-selection wording if user testing shows friction.

## Lane Q — First-Run Blocked-State UX

Priority: P2

Issue:

```text
#65 UI: expose provider and capability readiness for first-run users
```

Findings:

- Sidebar first screen centers prompt/model/settings, not provider/auth readiness.
- Empty prompt currently exits early in generation flow.
- Account settings show readiness, but first-run users may not discover it.
- Blank canvas entry is separate from auth/provider/model readiness.

Anchors:

- `ui/src/components/Sidebar.tsx`
- `ui/src/store/useAppStore.ts`
- `ui/src/components/Canvas.tsx`
- `ui/src/components/SettingsWorkspace.tsx`

Recommended direction:

- Add a compact readiness chip/checklist near generation entry.
- Prefer short actionable state over large onboarding text.
