# Agent 모드 dev 탈출 + LLM planner 생성 권한 이양

- Date: 2026-06-11
- Class: C3 (cross-domain: ui gate + server planner + tool surface + config + tests)
- Interview: S1–S9 완료 기준 확정 (아래)
- Scope out: 비디오 provider 확장 (Grok `grok-imagine-video` 유지), 에러 "조회" 초과 진단 기능

## 완료 기준 (S1–S9)

- S1 자율 fanout — planner LLM이 mode/개수 스스로 결정, plan에 source/reason 기록
- S2 멀티턴 image→video — "방금 그거 10초 16:9 영상으로" → planner가 video 모드 + duration/resolution/aspectRatio 추출, lastImage 기반 I2V
- S3 파라미터 폴백 — 파라미터 없으면 기본값(5s/480p/auto)
- S4 planner 장애 내성 — LLM 실패/타임아웃 시 기존 정규식 planner 폴백, 세션 유지
- S5 provider 일관성 — grok 세션→grok planner(chat/completions, grokProvider.plannerModel), oauth/api 세션→Responses(planner model = 세션 model 설정)
- S6 prod 노출 — env 없이 빌드한 UI에서 Agent 모드 표시 (VITE_IMA2_AGENT_MODE=0일 때만 숨김)
- S7 계약 테스트 — 신규 planner 계약 테스트 + 기존 agent 계약 회귀 없음
- S8 명시적 도구 장착 — 도구를 파라미터 스키마까지 manifest로 선언, planner 프롬프트와 /api/agent/tools, capabilities에 반영
- S9 에러 조회 도구 — ima2.get_generation_errors(read-only): 세션의 실패 큐 잡 errorCode/errorMessage + error 턴 조회

## 현재 구조 (조사 근거)

- UI 게이트: `ui/src/lib/devMode.ts:12` — `ENABLE_AGENT_MODE = VITE_IMA2_AGENT_MODE === "1" || VITE_IMA2_DEV === "1"` (소비처 7파일은 수정 불요)
- 흐름: `routes/agent.ts` POST queue → `createAgentQueueItem` (enqueue 시 `normalizeAgentGenerationPlan` — 정규식 `deriveAgentGenerationPlan` 기반) → `agentQueueWorker.runClaimedQueueItem` → `runAgentGenerationPlan`
- 정규식 planner: `lib/agentGenerationPlanner.ts` (count words + `VIDEO_INTENT_PATTERN`)
- 비디오: `lib/agentImageVideoGen.ts:195` `runAgentVideoGeneration` — `parseVideoParams(prompt)` 정규식, Grok 고정, I2V는 `session.lastImageId` 자동
- 텍스트 LLM 호출 전례: `lib/agentQuestionResponder.ts` (oauth proxy / api.openai.com `/v1/responses`, SSE 파싱), grok 텍스트는 `getGrokEndpoint(ctx, "/v1/chat/completions")` (`lib/grokImageAdapter.ts:310`) + `getPlannerConfig` (`lib/grokImageCore.ts`)
- 폴백 패턴 전례: `lib/cardNewsPlanner.ts` — config 블록 {enabled, model, timeoutMs} + deterministic fallback
- 에러 기록: 큐 `agent_queue_items.error_code/error_message` (`lib/agentQueueStore.ts`), 턴 `status:"error"` (`lib/agentStore.ts:368`)
- capabilities `agentMode.allowedTools` (`lib/capabilities.ts:109`)는 현재 stale (generate_video 누락) — 이번에 manifest 단일 소스로 정정

## 설계 결정

1. **planner 호출 시점 = 큐 claim 직후(run 시점)**. enqueue 202 응답은 그대로 빠르게 유지. 초기 plan(정규식)은 enqueue 시 저장되고, run 시 LLM plan으로 교체 후 DB 갱신(`updateAgentQueueItemPlan`). LLM 실패 시 초기 정규식 plan 그대로 진행(S4).
2. **LLM planner 적용 조건**: `config.agentPlanner.enabled` && `options.generationStrategy === "auto"` && slash command 아님. `/variants` 등 수동 지시는 기존 결정론 경로 유지.
3. **provider-follow 모델**: grok → `grokProvider.plannerModel`(기본 grok-4.3) chat/completions; oauth/api → 세션 `model` 설정(기본 gpt-5.4-mini) Responses. agy(Gemini)는 텍스트 planner 경로 부재 → 정규식 폴백 명시.
4. **도구 5종 manifest**: 기존 4종 + `ima2.get_generation_errors`. manifest(JSON schema)는 `lib/agentToolManifest.ts` 신설 — planner developer prompt, `/api/agent/tools`, capabilities가 같은 소스 사용.
5. **에러 조회는 plan mode `errors`**: planner LLM이 사용자 의도를 "최근 생성 실패 질문"으로 판단하면 mode=errors → 런타임이 read-only 조회 후 tool 턴 + assistant 턴 기록. REST `GET /api/agent/sessions/:id/errors`도 추가(UI/디버그용).

## 파일 변경 목록

### MODIFY
1. `ui/src/lib/devMode.ts` — `ENABLE_AGENT_MODE = import.meta.env.VITE_IMA2_AGENT_MODE !== "0"` (Node 모드 패턴, 주석 갱신)
2. `lib/agentTypes.ts`
   - `AGENT_ALLOWED_TOOLS` += `"ima2.get_generation_errors"`
   - `AgentGenerationPlanMode` += `"errors"`
   - `AgentGenerationPlanSource` += `"llm-planner"`
   - `AgentGenerationPlan` += `videoParams?: { duration?: number; resolution?: string; aspectRatio?: string } | null`
   - `AgentGenerationErrorRecord` 타입 신설 {scope:"queue"|"turn", code, message, prompt?, at}
3. `lib/agentGenerationPlanner.ts` — `normalizeAgentGenerationPlan`이 `mode:"errors"`/`source:"llm-planner"`/`videoParams`(duration 1–15 정수, resolution enum 480p/720p, aspectRatio enum) 검증·클램프
4. `lib/agentRuntime.ts` — `plan.mode === "errors"` 분기(조회→tool 턴→assistant 턴), video 분기에서 `plan.videoParams` 전달
5. `lib/agentImageVideoGen.ts` — `runAgentVideoGeneration` options에 `videoParams` 추가: plan 값 우선, 없으면 기존 `parseVideoParams(prompt)`, 최종 기본값 5s/480p/auto 유지
6. `lib/agentQueueWorker.ts` — claim 후 `resolveRuntimePlan`: 조건 충족 시 `requestAgentPlanFromModel` 호출, 성공 시 plan 교체+DB 갱신, 실패 시 logEvent 후 기존 plan
7. `lib/agentQueueStore.ts` — `updateAgentQueueItemPlan(id, plan)`, `getAgentGenerationErrors(sessionId, limit=10)` (failed 큐 + error 턴 join)
8. `routes/agent.ts` — `GET /api/agent/sessions/:sessionId/errors` 추가
9. `lib/capabilities.ts` — `agentMode.allowedTools`를 manifest 기반 5종으로 정정, `toolManifest` 노출
10. `config.ts` — `agentPlanner: { enabled(IMA2_AGENT_PLANNER_ENABLED, true), timeoutMs(IMA2_AGENT_PLANNER_TIMEOUT_MS, 30000) }`
11. `lib/configKeys.ts` — 위 2키 등록

12. `ui/src/lib/agentToolFormatting.ts` — `TOOL_NAMES` 3종 → 5종 (generate_video, get_generation_errors 추가) + 라벨/아이콘 매핑
13. `ui/src/components/agent/agentTypes.ts` — 서버 `lib/agentTypes.ts`와 동기화: `AgentToolName` 5종, `AgentGenerationPlan.mode`에 `"video" | "errors"` 추가, `videoParams` 필드, source에 `"llm-planner"` 추가
14. `ui/src/components/agent/AgentWorkspace.tsx` — fallback `allowedTools` 3종 → 5종

### NEW
15. `lib/agentToolManifest.ts` — 도구 5종 이름/설명/파라미터 JSON schema 단일 소스 (< 200줄)
16. `lib/agentPlannerModel.ts` — `requestAgentPlanFromModel(ctx, {sessionId, prompt, settings, manifest})`: provider-follow 엔드포인트 결정, 도구 manifest + 세션 컨텍스트(lastImage 유무, 직전 에러 유무) 포함 developer prompt, JSON 출력 파싱(코드펜스 제거) → `normalizeAgentGenerationPlan`, 실패/타임아웃 → null (< 300줄)
17. `tests/agent-mode-llm-planner-contract.test.ts` — normalize 확장(videoParams 클램프/errors mode), manifest 5종 schema, planner JSON→plan 매핑, 폴백 계약, capabilities 동기화

### 부수
18. `docs/migration/runtime-test-inventory.md` — `node scripts/classify-tests.mjs` 재생성 (CI inventory gate)
19. 기존 테스트 영향: `agent-mode-runtime-contract.test.ts:97`(allowedTools 4종 hard assert → 5종 갱신), `tests/cli-capabilities-contract.test.js`(agentMode allowedTools/toolManifest), `agent-mode-queue-contract`, `agent-mode-slash-command-contract`(plan.command 보존 확인)

## 감사(A) 반영 — 구현 세부 결정 (F1–F6)

- **F2 errors mode 정규화**: `normalizeAgentGenerationPlan`에서 `input.mode === "errors"` 분기를 `prompts.length === 0` 조기 반환(`agentGenerationPlanner.ts:106`) **앞**에 배치 — errors plan은 `prompts: []` 허용. mode 결정식(L112)과 `cleanPlanSource`(L210)에 `"errors"`/`"llm-planner"` 추가.
- **F3 UI 타입 동기화**: UI `agentTypes.ts`를 서버 타입과 수동 동기화(기존 관례 유지, re-export 구조 변경은 범위 밖). 이미 뒤처진 `"video"` mode/`ima2.generate_video`도 이번에 함께 동기화.
- **F4 planner 실행 조건 (허용 리스트, F5와 통합)**: `resolveRuntimePlan`은 **모든** 조건 충족 시에만 LLM planner 시도 — `config.agentPlanner.enabled === true` && `item.plan.source ∈ {"auto-default","auto-request"}` && `item.plan.command == null` && `item.options.generationStrategy === "auto"` && `item.options.provider !== "agy"`. 그 외 전부 저장된 plan 그대로 실행. prompt 재파싱으로 slash 감지하지 않음.
- **F5 retry 정책 (재감사 반영)**: `resolveRuntimePlan`은 `item.plan.source ∈ {"auto-default","auto-request"}`일 때**만** LLM planner를 시도한다(허용 리스트 방식 — F4의 스킵 리스트를 이것으로 대체). 1차 run에서 planner가 성공하면 source가 `"llm-planner"`로 저장되므로 retry는 자동으로 저장된 plan을 재사용. 1차 planner가 실패해 정규식 plan(source=auto-*)이 남은 경우 retry 시 planner 재시도는 **의도된 동작**(LLM plan이 만들어진 적 없으므로). 추가 DB 컬럼/플래그 불필요.
- **F6 capabilities.finalArtifact**: `"image"` 유지 (이미 video 존재 시점부터 stale했고, 외부 CLI 소비 계약 변경은 이번 범위 밖). `allowedTools`/`toolManifest`만 갱신.
- 에러 턴 앵커 정정: `lib/agentStore.ts:368`은 `restartAgentRuntimeSession`의 tool 턴 error 기록. 에러 조회 소스는 (1) failed 큐 잡 error_code/error_message (2) `status:"error"` 턴 텍스트.

## 검증 계획 (C 단계)
- `npx tsc --noEmit` (root + ui tsconfig)
- `npm test` 전체 (agent 계약 + inventory)
- `npm run build:server && npm run ui:build`
- 수동 smoke: planner mock 없이 정규식 폴백 경로(agentPlanner.enabled=false) 동작 확인

## 구현 결과 (B 단계, 2026-06-11)

구현 파일 (계획 대비 전부 반영):
- MODIFY: `ui/src/lib/devMode.ts`(기본 ON), `lib/agentTypes.ts`(5종 도구·errors mode·llm-planner source·AgentVideoParams·AgentGenerationErrorRecord), `lib/agentGenerationPlanner.ts`(errors 조기 분기·cleanVideoParams·llm-planner source), `lib/agentRuntime.ts`(errors 분기 runAgentErrorLookup·videoParams 전달·manifest payload), `lib/agentImageVideoGen.ts`(plan videoParams 우선·정규식 폴백), `lib/agentQueueWorker.ts`(isLlmPlanningEligible 허용 리스트 + resolveRuntimePlan + plan DB 갱신), `lib/agentQueueStore.ts`(updateAgentQueueItemPlan·getAgentGenerationErrors), `routes/agent.ts`(GET /errors), `lib/capabilities.ts`(allowedTools 5종 + toolManifest), `config.ts`/`lib/configKeys.ts`(agentPlanner.enabled/timeoutMs), UI 3파일 동기화
- NEW: `lib/agentToolManifest.ts`(도구 5종 JSON schema 단일 소스 + 누락 시 즉시 throw), `lib/agentPlannerModel.ts`(requestAgentPlanFromModel: oauth/api→Responses, grok→chat/completions, agy→null, 실패/타임아웃→null), `tests/agent-mode-llm-planner-contract.test.ts`(12케이스)
- 테스트 갱신: runtime-contract(5종+manifest), frontend-contract(기본 ON 게이트), queue/slash/parallel 픽스처에 `agentPlanner:{enabled:false}` 명시

검증 결과:
- `npx tsc --noEmit` root/ui/tests 3개 프로젝트 전부 clean
- `npm test` 전체 1019 tests / 135 suites / fail 0
- `npm run build:server`, `npm run ui:build` 성공, `npm run test:inventory` 통과 (67 runtime / 129 contract)
- 알려진 사항: `tests/agent-mode-queue-contract.test.ts`의 durable 케이스는 **단독 실행 시** main HEAD에서도 실패하는 기존 플레이크 (워크트리 베이스라인으로 확인, line 173) — 전체 스위트에서는 통과, 이번 변경과 무관
