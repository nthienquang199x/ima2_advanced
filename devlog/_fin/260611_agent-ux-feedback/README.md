# Agent 모드 UX 응답성 패치 (스피너·에러 표시·질문 응답·실시간 갱신)

- Date: 2026-06-11
- Class: C3 (server runtime + UI chat pane + planner prompt)
- Trigger: 사용자 스크린샷 — "영상 생성가능하니" 전송 후 스피너 없음, 답변 없음, 스트리밍 없음

## 재현된 결함 (조사 근거)

- D1. **질문이 video 생성으로 오분류**: `deriveAgentGenerationPlan("영상 생성가능하니")` → `mode: "video"` (키워드 정규식 "영상"). LLM planner 프롬프트에도 question 모드 규칙이 없어 능력 질문을 흡수 못 함 (`lib/agentPlannerModel.ts` 프롬프트 규칙).
- D2. **normalize의 question 함정**: planner가 `mode:"question", prompts:[]`를 내도 `prompts.length===0` 조기 반환이 정규식 plan으로 재유도 → 다시 video (`lib/agentGenerationPlanner.ts` — errors는 이미 조기 분기 처리했지만 question은 미처리).
- D3. **큐 실패가 채팅에 무표시**: `runClaimedQueueItem` catch는 `failAgentQueueItem`+log만 수행, 채팅 턴 미기록 (`lib/agentQueueWorker.ts:123-132`). 이미지 경로는 `runGeneratorWithRuntimeRecovery`가 error 턴을 남기지만 비디오/planner 경로 실패는 채팅이 영원히 침묵.
- D4. **실시간 피드백 부재**: `lib/inflight.ts`는 SSE 버스에 `error`만 publish (`lib/inflight.ts:151`); agent queue start/finish 이벤트가 UI로 안 흐름. (UI 폴링/구독 구조는 Explore 감사 결과 반영 예정)

## 수정 방향 (Explore 결과 반영 후 확정)

- F1. planner 프롬프트에 `question` 모드 규칙 추가 — 능력/메타 질문이면 `mode:"question"` + `assistantText`에 사용자 언어로 답변 작성
- F2. `normalizeAgentGenerationPlan`에 question 조기 분기 (errors와 동일 패턴, `prompts:[]`+`assistantText` 허용)
- F3. 큐 실패 시 assistant error 턴 기록 (워커 catch에서 appendAgentTurn)
- F4. 채팅 페인에 서버 큐 상태 기반 스피너/pending 표시 (local optimistic에만 의존하지 않음)
- F5. agent queue 라이프사이클 SSE publish + UI 구독으로 즉시 갱신
- F6. (범위 판단) 토큰 단위 스트리밍은 후속 — 이번에는 즉시성(스피너/이벤트/답변 도착)을 복구

## 검증 계획
- 신규/갱신 계약 테스트: question 모드 normalize/planner 규칙, 실패 시 error 턴 기록
- 런타임 smoke: 임시 서버에서 "영상 생성가능하니" enqueue → 답변 턴 도착 확인 (planner off 폴백 포함)
- tsc 3프로젝트 + 전체 스위트
