# Feature 2: Classic Batch Streaming

Verdict: **SKIP**

## What

classic 배치 생성 시 Accept: text/event-stream이면 SSE로 개별 결과 스트리밍.
완료 순서대로 `image` 이벤트 → 마지막에 `done` 이벤트.

## Why Skip

1. **기능 중복**: upstream이 이미 `asyncMode` + `publishJobEvent` + `eventBus`/`ssePublish`로 동일 기능 구현
2. **충돌 불가능**: fork의 generate.ts 패치는 pre-asyncMode 기준 (+213/-88줄), upstream은 이미 537줄로 완전 재구성
3. **누락 필드**: fork에 `providerUrl`, `createdAt`, `upstreamErrorFields()` 없음
4. **누락 패턴**: `fail()`/`succeed()` 헬퍼 미사용

## Salvageable Ideas

- `persistGeneratedResult` 함수 추출은 좋은 리팩터 아이디어 → upstream asyncMode 위에서 별도로 구현 가능
- 개별 이미지 완료 즉시 UI 반영 UX는 upstream `publishJobEvent`로 이미 가능
