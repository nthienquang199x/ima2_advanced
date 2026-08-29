# Feature 3: Prompt UX Improvements

Verdict: **ADAPT**

## What

1. ResultPromptSummary → User/Revised 탭 + LCS word-level diff 하이라이팅
2. PromptComposer → 세로 리사이즈 드래그 핸들 + Escape blur
3. clipboard.ts → navigator.clipboard + execCommand fallback

## Files

| File | Change | Conflict |
|------|--------|----------|
| `ResultPromptSummary.tsx` | +142/-18 전면 교체 | Low (upstream 32줄 그대로) |
| `PromptComposer.tsx` | +68 | Med (upstream에 lastVariantRef 이미 존재, fork는 신규 추가) |
| `ui/src/lib/clipboard.ts` | New | None |

## Quality

- LCS diff: `Uint32Array` DP 테이블, 정석 backtracking
- Pointer capture resize: `setPointerCapture`/`releasePointerCapture` 패턴
- ARIA: `role="tablist"`, `role="tab"`, `aria-selected`
- Props 변경: `{prompt, onCopy}` → `{userPrompt, revisedPrompt}` (breaking)

## Cherry-pick Plan

1. `clipboard.ts` 그대로 적용
2. `ResultPromptSummary.tsx` 그대로 적용 + 호출부 props 업데이트 (userPrompt/revisedPrompt)
3. `PromptComposer.tsx`는 lastVariantRef 충돌 해소 후 resize/escape 부분만 수작업
