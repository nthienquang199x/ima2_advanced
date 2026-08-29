# Prompt Studio Sidebar History — Feature Parity Plan

## Goal
프롬프트 스튜디오의 사이드바 히스토리 카드가 기본 모드 HistoryStrip / GalleryImageTile 대비 빠져있는 기능을 패리티 맞춤.

## Gap Summary
| # | Feature | Basic Mode | Prompt Studio |
|---|---------|-----------|---------------|
| 1 | Video item rendering | `<video>` with muted/playsInline | `<img>` only — broken |
| 2 | Drag-to-compose | draggable + application/ima2-ref | none |
| 3 | Video continuity payload | buildVideoDragPayload | none |
| 4 | Prompt hover title | title={item.prompt} | none |

## Files

### MODIFY: ui/src/components/history/SidebarHistoryImageCard.tsx
- Import `isVideoItem` from `../../lib/videoMedia`
- Import `buildVideoDragPayload` from `../../lib/videoContinuity`
- Import `type DragEvent` from react
- Add `onDragStart` handler: same pattern as GalleryImageTile (isVideoItem → buildVideoDragPayload, else image+filename)
- Add `draggable` + `onDragStart` on the button element
- Add `title={item.prompt ?? ""}` on button
- Conditional render: isVideoItem → `<video>`, else `<img>`

### MODIFY: ui/src/components/history/SidebarHistorySequenceCard.tsx
- Import `isVideoItem` from `../../lib/videoMedia`
- In the sequence grid loop, conditional render: isVideoItem → `<video>`, else `<img>`

### MODIFY: ui/src/styles/sidebar-history.css
- Add `.sidebar-history__thumb video` styles matching img sizing

### MODIFY: tests/prompt-studio-ui-contract.test.js
- New test: "renders video items with <video> element in sidebar history cards"
- New test: "adds drag support with application/ima2-ref to sidebar history cards"
- New test: "shows prompt title on hover for sidebar history image cards"

## Not in scope
- Favorite toggle in sidebar history (separate PABCD round if needed)
- Caption overlay (GalleryModal only feature, not HistoryStrip either)
