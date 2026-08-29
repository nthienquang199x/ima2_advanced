# Plan — 사이드바 모델 드롭다운 뷰포트 오버플로/내부 스크롤 버그 수정

- Date: 2026-06-10
- Class: C1 (single-component local patch, no new abstractions)
- Trigger: 사용자 리포트 — 세로 폭이 좁을 때 드롭다운이 뷰포트를 넘고, 드롭다운 안에서 스크롤이 안 됨 (스크린샷 확인)

## Root Cause

1. **메뉴 내부 스크롤이 메뉴를 즉시 닫음.**
   `ui/src/components/ImageModelSelect.tsx:138` — `window.addEventListener("scroll", close, true)`.
   capture 단계라 **메뉴 내부에서 발생하는 scroll 이벤트까지** 잡혀서, 사용자가 드롭다운 안을
   스크롤하는 순간 `close()`가 호출됨 → "스크롤이 안 된다"고 체감.
2. **max-height가 실제 메뉴 위치를 모름.**
   `ui/src/styles/canvas-accordion.css:261` — `max-height: calc(100dvh - 80px)`은 메뉴 top이
   80px 근처라는 고정 가정. 실제 top은 JS에서 `rect.bottom + 7`로 계산되므로(`ImageModelSelect.tsx:131`)
   트리거가 내려가면 메뉴 하단이 뷰포트를 초과.

## Changes (MODIFY only, 2 files)

### MODIFY `ui/src/components/ImageModelSelect.tsx`

1. `menuPos` state에 `maxHeight` 추가 (line 21-25):
   ```ts
   const [menuPos, setMenuPos] = useState<{ top: number; left: number; width: number; maxHeight: number }>({
     top: 0, left: 12, width: 280, maxHeight: 480,
   });
   ```
2. `measure()`에서 가용 높이 실측 (line 126-131):
   ```ts
   const top = rect.bottom + 7;
   const maxHeight = Math.max(160, window.innerHeight - top - gutter);
   setMenuPos({ top, left, width, maxHeight });
   ```
3. `close`가 메뉴 내부 scroll을 무시 (line 135):
   ```ts
   const close = (event?: Event) => {
     if (event && menuRef.current?.contains(event.target as Node)) return;
     setOpen(false);
   };
   ```
   - `resize` 리스너는 인자 타입이 호환되므로 그대로 `close` 재사용 가능 (Event 전달됨,
     target은 window라 menuRef에 포함되지 않음 → 기존처럼 닫힘).
4. 포털 메뉴 인라인 스타일에 `maxHeight`/`overflowY` 추가 (line 191-197):
   ```tsx
   style={{ position: "fixed", top: menuPos.top, left: menuPos.left,
            width: menuPos.width, maxHeight: menuPos.maxHeight,
            overflowY: "auto", zIndex: 160 }}
   ```

### MODIFY `ui/src/styles/canvas-accordion.css`

`.image-model-select__menu`(line 247-263)에 한 줄 추가:
```css
overscroll-behavior: contain;
```
(메뉴 끝까지 스크롤 시 배경 페이지로 스크롤 체이닝 방지.
기존 `max-height: calc(100dvh - 80px)`은 settings variant 등 비포털 fallback으로 유지.)

## Verification

1. `cd ui && npx tsc --noEmit` — zero errors
2. 기존 테스트 스위트 (`npm test` 해당 범위) 통과
3. 브라우저 실측 (CDP): 좁은 세로 뷰포트(~500px)에서 드롭다운 열기 →
   (a) 메뉴 하단이 뷰포트 안에 있는지, (b) 메뉴 내부 스크롤이 동작하고 메뉴가 닫히지 않는지,
   (c) 사이드바(외부) 스크롤 시에는 기존대로 닫히는지 확인
4. 커밋 (push 없음)

## Out of Scope

- `ReasoningEffortSelect.tsx` — 동일 패턴 없음 확인됨 (scroll listener/portal 미사용)
- flip-above-trigger(공간 부족 시 위로 펼침) — 트리거가 항상 상단 부근이라 불필요
