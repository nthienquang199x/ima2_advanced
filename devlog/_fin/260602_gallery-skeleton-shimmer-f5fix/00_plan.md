# Gallery Skeleton Shimmer + F5 Bug Fix

## Summary
갤러리 스트립에 생성 중 skeleton-shimmer 카드를 추가하고, #93 F5 버그(polling 조기 중단)를 동시에 수정.

## File Map

| Action | File | Changes |
|--------|------|---------|
| MODIFY | `ui/src/store/useAppStore.ts` | F5 fix: polling grace tick + multimode persistence |
| MODIFY | `ui/src/components/HistoryStrip.tsx` | skeleton cards + collection card rendering |
| MODIFY | `ui/src/components/MultimodeSequencePreview.tsx` | empty slots → skeleton-shimmer |
| MODIFY | `ui/src/index.css` | skeleton thumb CSS + fade transitions + slot shimmer |

## Detailed Changes

### 1. MODIFY `ui/src/store/useAppStore.ts`

#### 1a. F5 Bug Fix — Polling Grace Tick (line 1636)

**Before:**
```ts
if (cur.length === 0 && get().activeGenerations === 0) {
  if (w.__ima2InflightTimer) {
    clearInterval(w.__ima2InflightTimer);
    w.__ima2InflightTimer = undefined;
  }
  return;
}
```

**After:**
```ts
const shouldStop = cur.length === 0 && get().activeGenerations === 0;
if (shouldStop) {
  if (w.__ima2InflightTimer) {
    clearInterval(w.__ima2InflightTimer);
    w.__ima2InflightTimer = undefined;
  }
  // Run one final history fetch before stopping so newly completed
  // items are picked up without requiring a manual F5 refresh.
}
```
Remove the `return;` — let the tick fall through to the history query section, THEN exit. The interval is already cleared so no further ticks will run.

#### 1b. Multimode Grid Persistence

**selectHistory (line 3457-3462):**
Currently clears `multimodePreviewFlightId: null`. Change to only clear when explicitly leaving multimode, not when clicking an image within the grid.

**setMultimode (line 3362-3370):**
Currently clears sequences when multimode disabled. Keep completed sequences in state so `showHistorySequence` can recall them.

### 2. MODIFY `ui/src/components/HistoryStrip.tsx`

**Add subscriptions:**
```tsx
const inFlight = useAppStore((s) => s.inFlight);
const multimodeSequences = useAppStore((s) => s.multimodeSequences);
const activeGenerations = useAppStore((s) => s.activeGenerations);
const showHistorySequence = useAppStore((s) => s.showHistorySequence);
```

**Before history items, render skeleton cards:**

For each inFlight entry:
- `kind === "multimode"`: render N skeleton cards + 1 collection skeleton (N = sequence.requested)
- `kind === "video"`: render 1 skeleton
- default (single/sequential): render 1 skeleton (or `count` if sequential with count > 1)

**Collection card for completed multimode:**
After skeletons, check for completed sequences in history (by `sequenceId`). Render a mini-grid collection thumbnail that calls `showHistorySequence` on click.

### 3. MODIFY `ui/src/components/MultimodeSequencePreview.tsx`

**Line 91-101 — Replace empty slot text with skeleton:**

**Before:**
```tsx
<div className="multimode-sequence__empty">
  {sequence.status === "error" ? ... : t("multimode.generating")}
</div>
```

**After:**
```tsx
{sequence.status === "pending" || sequence.status === "partial" ? (
  <div className="multimode-sequence__skeleton" />
) : (
  <div className="multimode-sequence__empty">
    {sequence.status === "error" ? ... : ...}
  </div>
)}
```

### 4. MODIFY `ui/src/index.css`

**New rules:**

```css
/* Gallery skeleton thumb */
.history-thumb--skeleton {
  background: linear-gradient(
    90deg,
    var(--surface-2) 25%,
    color-mix(in srgb, var(--amber) 18%, var(--surface-2)) 50%,
    var(--surface-2) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 6px;
  border: 1px solid var(--border);
  opacity: 1;
}

/* Fade transition for skeleton → real image */
.history-thumb {
  /* add to existing: */
  transition: all 0.15s, opacity 0.2s ease;
}
.history-thumb--fade-in {
  animation: thumb-fade-in 200ms ease forwards;
}
@keyframes thumb-fade-in {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 0.6; transform: scale(1); }
}

/* Collection skeleton/thumb */
.history-thumb--collection {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  padding: 1px;
  background: var(--border);
  overflow: hidden;
}
.history-thumb--collection > .collection-mini {
  aspect-ratio: 1/1;
  object-fit: cover;
  width: 100%;
}

/* Multimode slot skeleton */
.multimode-sequence__skeleton {
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    var(--surface-2) 25%,
    color-mix(in srgb, var(--amber) 18%, var(--surface-2)) 50%,
    var(--surface-2) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 6px;
}

/* Multimode slot image fade-in */
.multimode-sequence__slot img {
  /* add: */
  animation: thumb-fade-in 200ms ease forwards;
}
```

## Success Criteria
- [ ] tsc --noEmit clean
- [ ] All tests pass
- [ ] F5 bug: generation completes → gallery updates without refresh
- [ ] Single gen: 1 skeleton → fade to image
- [ ] Multimode 4: 4 skeletons + 1 collection → images arrive one by one with fade
- [ ] Video: 1 skeleton → fade to video thumb
- [ ] Multimode grid persists after completion
- [ ] Collection card in gallery strip → shows grid on click
- [ ] Cancel → skeletons removed
