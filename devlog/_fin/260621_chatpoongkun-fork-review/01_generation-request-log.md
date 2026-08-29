# Feature 1: Generation Request Log

Verdict: **ADAPT**

## What

프롬프트별 생성 요청 로그 (성공/실패 횟수, 에러 내용) 저장 + UI 패널.
Issue #95에서 ChatPoongKun이 직접 요청한 기능.

## Files

| File | Status | Notes |
|------|--------|-------|
| `lib/generationRequestLog.ts` | New | JSON file-backed log, 200 entry cap, atomic write queue |
| `routes/generationRequestLog.ts` | New | GET /api/generation-requests |
| `ui/src/components/GenerationRequestLogPanel.tsx` | New | 자동 갱신, 클릭시 프롬프트 복사, ARIA 준수 |
| `routes/generate.ts` | Modified | finally block에 appendGenerationRequestLog 호출 추가 |

## Quality

- 직렬 write queue (`writeQueue.catch().then()`) 패턴 깔끔
- 200 entry cap으로 무한 성장 방지
- ARIA role 올바르게 적용
- API 실패 시 error boundary 없음 (minor)

## Cherry-pick Plan

1. 신규 3파일은 그대로 cherry-pick
2. `config.ts`에 `generationRequestLogFile` 필드 추가
3. `routes/generate.ts`의 appendGenerationRequestLog 호출은 현재 upstream asyncMode 구조에 맞게 수작업 통합
4. `routes/index.ts`에 라우트 등록
