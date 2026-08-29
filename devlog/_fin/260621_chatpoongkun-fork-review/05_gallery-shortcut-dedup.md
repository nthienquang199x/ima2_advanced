# Feature 5: Gallery Keyboard Shortcut Dedup

Verdict: **PICK**

## What

Canvas mode에서 Delete/Arrow/Home/End 키보드 핸들러 제거.
갤러리 레벨에서 이미 처리하므로 중복 → 충돌 방지.

## Files

| File | Change |
|------|--------|
| `useCanvasModeShortcuts.ts` | -35줄 (핸들러 + interface 축소) |
| `CanvasModeWorkspace.tsx` | -16줄 (제거된 props 호출부 정리) |

## Quality

- 깨끗한 제거, 데드코드 없음
- Interface에서 unused params 정리 완료

## Cherry-pick Plan

1. upstream 파일이 fork base와 동일 확인됨
2. 두 파일 함께 cherry-pick
3. `useGalleryViewerNavigation.ts`에서 해당 단축키 처리 확인 필요
