# Phase 1 Results — 사이드바 모델 드롭다운 스크롤/오버플로 수정

- Date: 2026-06-10
- Plan: `00_plan.md` (audit PASS — 니지카, read-only)

## Changes

### `ui/src/components/ImageModelSelect.tsx`
- **Changes**: `menuPos` state에 `maxHeight` 추가, `measure()`에서 `window.innerHeight - top - gutter` 실측(`Math.max(160, …)` 하한), `close(event?)`가 메뉴 내부에서 발생한 scroll 이벤트를 무시(`menuRef.current?.contains(event.target)` 가드), 포털 인라인 스타일에 `maxHeight`/`overflowY: "auto"` 적용
- **Impact**: sidebar variant 사용처 — `Sidebar.tsx:45`, `MobileAppBar.tsx:31` (모바일 동일 버그 함께 수정). settings variant·`ReasoningEffortSelect` 영향 없음
- **Verification**: 아래 통합 검증 참조

### `ui/src/styles/canvas-accordion.css`
- **Changes**: `.image-model-select__menu`에 `overscroll-behavior: contain` 추가 (스크롤 체이닝 방지)
- **Impact**: 해당 클래스 사용처는 포털 메뉴 1곳
- **Verification**: computed style `overscrollBehaviorY: "contain"` 확인

## Verification Evidence

1. `npx tsc -b --force` (ui workspace) — exit 0
2. `npm test` — **990/990 pass**, 0 fail
3. `npm run build` (ui) — built in 1.02s
4. 브라우저 E2E (CDP, 뷰포트 900×520, http://localhost:3333):
   - 기하: `menuTop 68, menuBottom 508 ≤ viewportH 520`, `inlineMaxHeight "440px"`(= 520−68−12), `overflowY auto`, `overscroll contain`, `scrollH 579 > clientH 438`
   - 내부 스크롤: `scrollBy(0,200)` 후 메뉴 **유지**(`open: true, scrollTop: 140.5` = 최대치) — 수정 전엔 window capture 리스너가 즉시 닫았음
   - 외부 스크롤: `.sidebar__scroll`에 scroll 이벤트 → 메뉴 **닫힘** (기존 동작 보존)
