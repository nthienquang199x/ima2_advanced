# SSE 클라이언트 멀티플렉싱 감사 (2026-06-08)

## 범위

- `ui/src/lib/eventChannel.ts`
- `ui/src/lib/api-generation.ts`
- `ui/src/lib/nodeApi.ts`
- `ui/src/App.tsx`
- `ui/src/store/storeTypes.ts`
- `ui/src/store/storeGenImpl.ts`
- `ui/src/store/storeGenerateEntryImpl.ts`
- `ui/src/store/storeInflightImpl.ts`
- `ui/src/components/MultimodeSequencePreview.tsx`

## 패치 요약 (Phase 3 — 2026-06-08 감사+패치)

| ID | 심각도 | 조치 | 파일 |
|----|--------|------|------|
| D1 | RISK→패치 | 클라 `subscribe()` **POST fetch 이전** 등록 (이벤트 유실 race 제거) | `ui/src/lib/api-generation.ts`, `ui/src/lib/nodeApi.ts` |
| D5 | CRITICAL→패치 | ring buffer에 `done`/`partial`/`image` 대형 payload는 `_imageOmitted` 메타만 저장 (reconnect 시 terminal 복구) | `lib/eventBus.ts` |
| D3 | RISK→패치 | `RING_SIZE` 500→2000 (7+ 동시 생성 headroom) | `lib/eventBus.ts` |
| D6 | RISK→패치 | `abortJob` 즉시 `publish(error, GENERATION_CANCELED)` (route catch 대기 없이 클라 알림) | `lib/inflight.ts` |
| D4 | RISK→패치 | fallback requestId `Date.now().toString(36)` → `crypto.randomUUID()` | `api-generation.ts`, `nodeApi.ts` |
| C1 | CRITICAL (기존) | reconnect `lastEventId` query + server dual header/query | `eventChannel.ts`, `routes/events.ts` |
| C2 | CRITICAL→패치 | Classic `/api/generate`도 subscribe-before-fetch + async POST로 전환 (10-way 병렬 생성 hang 제거) | `ui/src/lib/api-generation.ts`, `ui/src/store/storeGenImpl.ts` |
| R1-R3 | RISK (기존) | stream timeout, jobId guard, resync on reconnect only | `eventChannel.ts` |

## Execution Log

```
2026-06-08 키타: SSE 멀티플렉싱 E2E 감사 9항목 수행
- lib/eventBus.ts: RING_SIZE 2000, toRingEntry() stripped replay for large images
- lib/inflight.ts: abortJob publishes GENERATION_CANCELED error event
- ui api-generation/nodeApi: subscribe-before-fetch, crypto.randomUUID fallbacks
- tests: event-bus.test.ts updated, async-stream-subscribe-order.test.js added
- verify: npm run build:server && cd ui && npm run build && npm test (see report)

2026-06-08 봇치: Classic generation 연결 점유 회귀 패치
- 현상: `ima2 serve` Classic 10개 병렬 생성 중 설정창/API/갤러리 이미지 로드 지연
- 원인: UI `runGenerateImpl`이 `/api/generate` sync JSON POST를 작업 완료까지 유지
- 조치: `postGenerateStream()`이 `/api/events` handler를 먼저 등록한 뒤 `{ async: true, requestId }` POST
- verify: UI production bundle에 `EventSource`/`/api/events` 포함, `getReader()`/`text/event-stream` 없음
```

## 잔여 RISK (모니터링)

- **partial replay**: reconnect 시 partial image bytes는 ring에 없음 — UI preview gap 가능, `done`/`url`/`filename`으로 최종 복구
- **global ring eviction**: 2000+ cross-job 이벤트 시 여전히 oldest eviction — 극端 부하 모니터링
- **reconcileInflight**: terminal job은 inflight 목록 정리, multimodeSequences pending은 stream timeout(30m)까지 유지
- **노드 AbortSignal**: storeNodeGenImpl signal 미전달 — cancelInflight 경로로 서버 abort
