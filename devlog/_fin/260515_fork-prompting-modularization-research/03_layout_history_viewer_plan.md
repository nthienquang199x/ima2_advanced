---
created: 2026-05-15
tags: [ima2-gen, fork-research, layout, history, viewer]
status: research / modularization plan
---

# Layout, History, Viewer Modularization Plan

This document continues [02_modularization_plan.md](02_modularization_plan.md). It intentionally separates high-blast-radius layout/viewer work from the prompt-builder backend, prompt-builder UI, and composer metadata slices.

## Slice 4 — Classic Workspace / Right Panel Layout

### User-Facing Goal

Desktop classic mode can use a bottom composer and a right-side builder/settings panel, matching the prompt-first workflow from the fork without breaking mobile or card-news layouts.

### New Files

```text
ui/src/components/classic/ClassicWorkspace.tsx
ui/src/components/classic/ResultDockPanel.tsx
ui/src/components/right-panel/RightPanelTabs.tsx
ui/src/components/right-panel/RightPanelBuilderStack.tsx
tests/classic-workspace-contract.test.js
```

### Existing Files To Modify

```text
ui/src/App.tsx
ui/src/components/RightPanel.tsx
ui/src/components/GenerationControlsPanel.tsx
ui/src/components/MobileComposeSheet.tsx
ui/src/index.css
```

### Layout Policy

- Desktop classic mode may render `ClassicWorkspace`.
- Mobile should keep existing mobile compose sheet unless separately redesigned.
- Card News should continue hiding the standard right panel.
- Node Mode must not inherit classic bottom composer.
- Readiness popup from `#65` remains popup-based, not a permanent panel.

### Risks

- This is the highest UX blast-radius slice. Do it after prompt-builder API and store contract are tested.
- The fork uses right panel tabs for builder/library. Upstream already has settings, prompt library, and readiness flows. Avoid turning the right panel into a hidden kitchen sink.

## Slice 5 — Sidebar History + Grouped Multimode Cards

### User-Facing Goal

Desktop users get a lightweight recent history sidebar. Multimode sequences appear as grouped cards instead of repeated individual thumbnails. Users can quickly delete individual images or grouped sequences.

This must reuse the existing upstream history layout setting. Current upstream already has `HistoryStripLayout = "rail" | "horizontal" | "sidebar"` and `HistoryStripLayoutToggle`; do not introduce a parallel `ui.historyPlacement` setting.

### New Files

```text
ui/src/components/history/SidebarHistory.tsx
ui/src/components/history/SidebarHistoryEntry.tsx
ui/src/components/history/SidebarHistorySequenceCard.tsx
ui/src/lib/history/sidebarHistoryEntries.ts
tests/sidebar-history-performance-contract.test.js
tests/multimode-sequence-history-contract.test.js
```

### Existing Files To Modify

```text
ui/src/components/Sidebar.tsx
ui/src/components/HistoryStrip.tsx
ui/src/store/useAppStore.ts
ui/src/lib/galleryNavigation.ts
ui/src/i18n/en.json
ui/src/i18n/ko.json
ui/src/index.css
```

### Setting Ownership

`SidebarHistory` is a Prompt Studio projection of the existing history surface, not a second independent sidebar preference.

Policy:

- `historyStripLayout: "sidebar"` is the target layout setting for the sidebar presentation.
- Prompt Studio may preset `historyStripLayout` to `"sidebar"`.
- Advanced settings may still let users choose `"rail"`, `"horizontal"`, or `"sidebar"` through the existing `HistoryStripLayoutToggle`.
- Multimode grouping belongs to a separate grouping policy such as `ui.multimodeHistoryGrouping`, not to a new placement setting.
- If a new `SidebarHistory` component replaces the visual internals of sidebar history, it must preserve the existing layout state, persistence key, and settings control.

### Pure Helper Contract

Do not put sequence grouping logic only inside the React component.

Helper:

```ts
type SidebarHistoryEntry =
  | { type: "image"; key: string; item: GenerateItem }
  | { type: "sequence"; key: string; sequenceId: string; items: GenerateItem[] };

function buildSidebarHistoryEntries(history: GenerateItem[], options: {
  limit: number;
}): SidebarHistoryEntry[];
```

Rules:

- Skip `canvasVersion` unless a dedicated canvas history mode is enabled.
- Deduplicate by existing `getGalleryItemKey`.
- Group by `sequenceId`.
- Sort sequence items by `sequenceIndex`, then `createdAt`.
- Cap sidebar render count.
- Use lazy image loading and async decoding.

### Delete Policy

Single image delete:

```text
trashHistoryItem(item)
```

Sequence delete:

```text
trashHistorySequence(sequenceId)
```

`trashHistorySequence` must be implemented as a store action that:

- collects visible items for the sequence;
- sends each to the existing trash route;
- removes them from history and multimode sequence state;
- preserves undo semantics if possible, or explicitly marks sequence bulk-delete as non-undo if not.

## Slice 6 — Viewer Zoom/Pan + Empty State

### User-Facing Goal

Users can inspect generated images in the main viewer with zoom and pan, and empty state feels alive without adding heavy UI.

### New Files

```text
ui/src/hooks/useViewerTransform.ts
ui/src/components/viewer/ViewerTransformFrame.tsx
ui/src/components/viewer/ViewerControls.tsx
ui/src/components/viewer/EmptyHalftoneCanvas.tsx
tests/viewer-workflow-ui-contract.test.js
tests/left-sidebar-halftone-contract.test.js
```

### Existing Files To Modify

```text
ui/src/components/Canvas.tsx
ui/src/index.css
ui/src/i18n/en.json
ui/src/i18n/ko.json
```

### Behavior

- Wheel zoom.
- Double-click toggle between 100% and 200%.
- Drag-to-pan only when zoomed.
- Reset on selected image change.
- Buttons for zoom out / reset / zoom in.
- Respect reduced motion for empty-state animation.

### Why Module

The fork puts this directly in `Canvas.tsx`. Upstream should not. Current upstream `Canvas.tsx` is small enough to preserve if transform logic moves into a hook and frame component.

## Slice 7 — Visual System / CSS

### Goal

Make the UI feel coherent without dumping large style blocks into `ui/src/index.css`.

### Suggested CSS Files

```text
ui/src/styles/prompt-builder.css
ui/src/styles/composer-flow.css
ui/src/styles/sidebar-history.css
ui/src/styles/viewer-workflow.css
```

Update `ui/src/main.tsx` to import the feature CSS files.

### Constraints

- Keep cards radius <= existing design convention.
- Use current theme variables; avoid a one-note dark/purple palette.
- Do not add decorative gradient orbs.
- Avoid nested cards.
- Ensure button text fits at mobile widths.

## Slice 8 — Documentation / Attribution

### Files

```text
devlog/_plan/260515_fork-prompting-modularization-research/*
docs/CLI.md
skills/ima2/SKILL.md
README.md
```

### Attribution Policy

If code is copied or adapted non-trivially from the fork, include attribution in the commit message or PR body. The fork says MIT in the public post and package metadata, but its GitHub `licenseInfo` from API was `null`, so treat license documentation carefully:

- verify root `LICENSE` in the fork before copying code;
- preserve notices if present;
- prefer reimplementation from behavior when practical;
- credit `damagethundercat/ima2-gen` in devlog and PR body.

## Do-Not-Port List

These fork changes should not be adopted:

- `package.json` package/bin rename to `@damagethundercat/ima2-gen` / `ima2x`.
- README/site changes specific to fork branding.
- `ResultActions.tsx` version that removes upstream first-node and deletion-focus behavior.
- Local `HistoryStrip` identity helper replacing shared upstream gallery helpers.
- Inline `Canvas.tsx` viewer transform implementation.
- Monolithic `useAppStore.ts` prompt-builder expansion.
- Monolithic `ui/src/index.css` expansion.
