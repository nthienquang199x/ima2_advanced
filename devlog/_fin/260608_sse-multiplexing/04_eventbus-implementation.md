# SSE Multiplexing via EventBus — Implementation Plan (v2, post-audit)

## Summary (CEO-level)

지금 UI에서 이미지/비디오 생성 시 작업당 1개씩 연결을 잡고 있어서, 동시에 여러 개 돌리면
브라우저 연결 6개 한도에 걸려 갤러리 이미지가 안 뜸.
→ "라디오 채널" 1개(GET /api/events)로 모든 진행 상황을 보내고, 생성 요청은 즉시 응답하는
방식으로 바꿈. CLI는 기존 SSE 그대로 유지.

## Architecture

```
[Before — per-job SSE]
Browser ──POST──→ Server (holds connection 15min)  × N jobs
Browser ──GET───→ Gallery image                    ← BLOCKED when N≥4

[After — single EventSource + async POST]
Browser ──GET /api/events──→ Server (1 persistent SSE)
Browser ──POST (async:true)─→ Server → 202 + requestId (instant)
Server ──eventBus.publish──→ /api/events stream → Browser routes by requestId
Browser ──GET───→ Gallery image                    ← 5 slots free ✅
```

## Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Validation errors → POST 4xx JSON; runtime errors → channel | Clean separation, no race |
| 2 | Partial images excluded from ring buffer replay | Memory safety; partials=2 per job, done has full result |
| 3 | Replace `multimodeAbortControllers` with `activeFlightIds: Set<string>` | Unified cancel via cancelInflight, preserve preview fallback |
| 4 | Allow big event serialization delay on single channel | localhost, sub-ms impact |
| 5 | Dual-emit uses closure `requestId`, not `data.requestId` | Some events (image, writeNodeError) lack requestId in data |

## File Changes

### NEW (3 files)

#### 1. `lib/eventBus.ts` (~60 lines)

```typescript
import { EventEmitter } from "node:events";

interface BusEvent {
  id: number;
  jobId: string;
  event: string;
  data: Record<string, unknown>;
}

const RING_SIZE = 500;
const bus = new EventEmitter();
bus.setMaxListeners(100);

let seq = 0;
const ring: BusEvent[] = [];

export function publish(jobId: string, event: string, data: Record<string, unknown>): void {
  seq++;
  const entry: BusEvent = { id: seq, jobId, event, data };
  const hasImage = typeof (data as any).image === "string" && (data as any).image.length > 1000;
  if (!hasImage) {
    ring.push(entry);
    if (ring.length > RING_SIZE) ring.shift();
  }
  bus.emit("event", entry);
}

export function subscribe(listener: (ev: BusEvent) => void): () => void {
  bus.on("event", listener);
  return () => bus.off("event", listener);
}

export function replaySince(lastEventId: number): BusEvent[] {
  const idx = ring.findIndex(e => e.id > lastEventId);
  return idx === -1 ? [] : ring.slice(idx);
}

export type { BusEvent };
```

#### 2. `routes/events.ts` (~50 lines)

Follows codebase convention: `export function registerEventsRoute(app: Express, ctx: RouteRuntimeContext)`.

```typescript
import type { Express } from "express";
import type { RouteRuntimeContext } from "../lib/runtimeContext.js";
import { subscribe, replaySince } from "../lib/eventBus.js";

export function registerEventsRoute(app: Express, _ctx: RouteRuntimeContext) {
  app.get("/api/events", (req, res) => {
    res.setHeader("Content-Type", "text/event-stream; charset=utf-8");
    res.setHeader("Cache-Control", "no-cache, no-transform");
    res.setHeader("Connection", "keep-alive");
    res.flushHeaders?.();

    const lastId = parseInt(req.headers["last-event-id"] as string, 10);
    if (!isNaN(lastId)) {
      for (const ev of replaySince(lastId)) {
        res.write(`id: ${ev.id}\nevent: ${ev.event}\ndata: ${JSON.stringify({ ...ev.data, jobId: ev.jobId })}\n\n`);
      }
    }

    const unsub = subscribe((ev) => {
      res.write(`id: ${ev.id}\nevent: ${ev.event}\ndata: ${JSON.stringify({ ...ev.data, jobId: ev.jobId })}\n\n`);
    });

    const heartbeat = setInterval(() => { res.write(": ping\n\n"); }, 15_000);

    req.on("close", () => { unsub(); clearInterval(heartbeat); });
  });
}
```

#### 3. `ui/src/lib/eventChannel.ts` (~80 lines)

```typescript
type EventHandler = { onEvent(event: string, data: any): void };

const registry = new Map<string, EventHandler>();
let es: EventSource | null = null;
let resyncCallback: (() => void) | null = null;
let wasConnected = false;

const EVENT_TYPES = ["phase", "partial", "image", "done", "error", "planning", "submitted", "progress"];

function dispatch(evType: string, raw: string) {
  let parsed: any;
  try { parsed = JSON.parse(raw); } catch { return; }
  const jobId = parsed.jobId || parsed.requestId;
  if (!jobId) return;
  const handler = registry.get(jobId);
  if (handler) handler.onEvent(evType, parsed);
}

function connect() {
  if (es) return;
  es = new EventSource("/api/events");

  for (const evType of EVENT_TYPES) {
    es.addEventListener(evType, ((ev: MessageEvent) => dispatch(evType, ev.data)) as EventListener);
  }

  es.onopen = () => {
    if (wasConnected && resyncCallback) resyncCallback();
    wasConnected = true;
  };
  es.onerror = () => { /* EventSource auto-reconnects */ };
}

export function register(requestId: string, handlers: EventHandler): void {
  registry.set(requestId, handlers);
  connect();
}

export function unregister(requestId: string): void {
  registry.delete(requestId);
}

export function onResync(cb: () => void): void {
  resyncCallback = cb;
}

connect();
```

### MODIFY (12 files)

#### 4. `routes/index.ts` — register events route (+2 lines)

```diff
+import { registerEventsRoute } from "./events.js";
 // inside configureRoutes, after registerHealthRoutes:
+  registerEventsRoute(app, ctx);
```

#### 5. `routes/nodes.ts` — dual-emit + async mode (~40 lines changed)

- Import `publish` from `../lib/eventBus.js`
- Wrap `writeSse` calls with dual-emit helper using CLOSURE requestId:
  ```typescript
  function emitAndWrite(res, requestId, event, data) {
    writeSse(res, event, data);
    publish(requestId, event, data);
  }
  ```
- `writeNodeError` calls (nodeHelpers.ts:47): pass `requestId` from closure, publish separately
- Async mode (`body.async === true`):
  - Move validation BEFORE `startJob` (currently startJob is at L49, validation at L95+)
  - On validation fail → `res.status(4xx).json({ error, code })`
  - On pass → `startJob` + `registerJobAbortController` + `res.status(202).json({ requestId, async: true })`
  - Run generation detached: `runNodeGeneration(...).catch(...)` (not awaited)
  - All events via `publish(requestId, ...)` only (res closed)

#### 6. `routes/multimode.ts` — dual-emit + async mode (~40 lines changed)

- Import `publish` from `../lib/eventBus.js`
- Dual-emit at all `writeSse` calls using closure `requestId`:
  - **Specifically `writeSse(res, "image", item)` at L252**: `publish(requestId, "image", item)` (item lacks requestId, use closure)
- Async mode same pattern as nodes:
  - Validation (L99-131) → 4xx JSON
  - Pass → `startJob` + 202 + detached generation

#### 7. `routes/video.ts` — dual-emit + async mode (~35 lines changed)

- Import `publish` from `../lib/eventBus.js`
- Dual-emit in `sendSse` (closure already has `requestId`)
- Async mode: branch BEFORE L130 SSE headers
  - Validation → 4xx; pass → 202 + detached

#### 8. `lib/nodeHelpers.ts` — add requestId to writeNodeError (~5 lines)

- Add `requestId` parameter to `writeNodeError` signature
- Inside: after existing `writeSse(res, "error", ...)`, add `publish(requestId, "error", errorPayload)`
- Update call sites in `routes/nodes.ts` (L354, L455, L467) to pass requestId

#### 9. `ui/src/lib/api-generation.ts` — replace SSE streaming with eventChannel (~80 lines changed)

- `postMultimodeGenerateStream` (L17-98):
  - Generate `requestId` via `crypto.randomUUID()`
  - `register(requestId, { onEvent })` → POST with `{ ...body, requestId, async: true }`
  - Handle POST error (4xx) → call onError directly
  - Channel events → route to existing callbacks (onPartial, onImage, onDone, onError, onPhase)
  - On done/error → `unregister(requestId)`
  - Return `{ requestId }` for cancel reference

- `postVideoGenerateStream` (L205-270):
  - Same pattern: requestId → register → async POST → channel events
  - Map events: planning, submitted, progress, done, error

#### 10. `ui/src/lib/nodeApi.ts` — replace SSE streaming with eventChannel (~40 lines changed)

- Streaming variant (postNodeGenerateStream or equivalent):
  - requestId → register → async POST → channel events (phase, partial, done, error)
  - On done/error → unregister

#### 11. `ui/src/store/storeGenImpl.ts` — replace AbortControllers with activeFlightIds (~25 lines)

- Replace `multimodeAbortControllers: { ...s.multimodeAbortControllers, [flightId]: controller }` (L72)
  → `activeFlightIds: new Set([...s.activeFlightIds, flightId])`
- Preview fallback (L217-220): `Object.keys(nextControllers)` → `[...state.activeFlightIds]`
- Cleanup (L211-229): remove from Set instead of deleting controller key

#### 12. `ui/src/store/storeGenerateEntryImpl.ts` — update cancel (~3 lines)

- Replace `get().multimodeAbortControllers[flightId]?.abort()` (L28)
  → `cancelInflight(flightId)` (import from api-inflight)

#### 13. `ui/src/store/storeTypes.ts` — update type (~2 lines)

- Replace `multimodeAbortControllers: Record<string, AbortController>` (L210)
  → `activeFlightIds: Set<string>`

#### 14. `ui/src/store/useAppStore.ts` — update initial state (~1 line)

- Replace `multimodeAbortControllers: {}` (L163)
  → `activeFlightIds: new Set()`

#### 15. `ui/src/components/MultimodeSequencePreview.tsx` — update cancel check (~2 lines)

- Replace `s.multimodeAbortControllers[id]` (L13)
  → `s.activeFlightIds.has(id)`

### TEST UPDATES (4 files)

#### 16. `tests/multimode-ui-contract.test.js` — update contract assertions

- Replace `multimodeAbortControllers` assertions → `activeFlightIds`
- Remove `signal: controller.signal` assertions (no longer passed to fetch)

#### 17. `tests/multimode-concurrent-store-contract.test.js` — same

- Update `abort()` assertions → `cancelInflight` pattern

#### 18. `tests/event-bus.test.ts` (NEW) — unit test for eventBus

- publish/subscribe/replaySince/ring limit/partial exclusion

#### 19. `tests/events-channel-contract.test.ts` (NEW) — integration test

- 2 async jobs → single /api/events stream delivers both by requestId
- Last-Event-ID replay
- POST returns before generation completes
- DELETE cancel → error event arrives

## Implementation Order

1. `lib/eventBus.ts` + `tests/event-bus.test.ts`
2. `routes/events.ts` + `routes/index.ts` registration + `tests/events-channel-contract.test.ts`
3. `lib/nodeHelpers.ts` requestId param addition
4. Dual-emit in 3 routes (existing tests MUST remain green — wire unchanged)
5. Async mode in 3 routes + contract tests
6. `ui/src/lib/eventChannel.ts`
7. `ui/src/lib/api-generation.ts` + `ui/src/lib/nodeApi.ts` client migration
8. Store cleanup: storeGenImpl → storeGenerateEntryImpl → storeTypes → useAppStore → MultimodeSequencePreview
9. Test updates: multimode-ui-contract, multimode-concurrent-store-contract
10. Final: `npm run typecheck && npm run typecheck:tests && npm test`

Each step: atomic commit, tests pass.

## Success Criteria

1. `npm test` — 936+ pass (+ new eventBus/channel tests)
2. `npx tsc --noEmit` — 0 errors
3. Browser: 7+ simultaneous generations → gallery loads without hang
4. CLI: per-job SSE works unchanged
5. Reconnection: server restart → UI resync via inflight reconcile

## Audit v2 Fixes Applied (N1-N5)

| Finding | Fix |
|---------|-----|
| N1: multimode.ts SSE headers before async check | async branch BEFORE L66 SSE headers (same as video) |
| N2: writeNodeError called on closed async res | async detached path uses `publish()` only, never writeNodeError(res) |
| N3: onResync not connected to reconcileInflight | Add step: App.tsx or store init calls `onResync(() => reconcileInflight())` |
| N4: Double cancel (abort + cancelInFlightJob) | Remove abort, keep only `cancelInFlightJob(flightId)` |
| N5: signal assertion in contract test | Item 16 covers signal removal explicitly |

### Implementation details for N1-N3:

**N1 (multimode.ts async headers):** Item 6 revised — async check at L40 (after requestId), before L66 headers:
```typescript
const isAsync = body.async === true;
if (isAsync) {
  // validate → 4xx JSON on fail
  // startJob + 202 on pass
  // detached generation (publish only)
  return;
}
// existing SSE path unchanged below
res.setHeader("Content-Type", "text/event-stream; charset=utf-8");
```

**N2 (writeNodeError in async):** Item 5 revised — async detached catch block:
```typescript
// In detached generation catch:
} catch (err) {
  publish(requestId, "error", { error: { code: "GENERATION_ERROR", message: err.message }, parentNodeId, status: 500 });
  finishJob(requestId, { status: "error", ... });
}
// writeNodeError is ONLY used in sync SSE path (res still open)
```

**N3 (resync connection):** Added as implementation step 7.5:
- In `ui/src/App.tsx` or store initialization, connect resync:
  ```typescript
  import { onResync } from "./lib/eventChannel";
  onResync(() => { reconcileInflight(); });
  ```

---

## Audit Fixes Applied (v2)

| Finding | Fix |
|---------|-----|
| F1: Route registration wrong file | → `routes/index.ts` + `(app, ctx)` pattern |
| F2: Client migration wrong file | → `ui/src/lib/api-generation.ts` |
| F3: multimode image event no requestId | → closure-based `publish(requestId, ...)` |
| F4: writeNodeError no requestId | → add `requestId` param to writeNodeError |
| F5: multimodeAbortControllers incomplete | → full list: 6 files + 2 test files |
| F6: Contract tests not in plan | → added as items 16-17 |
| F7: Preview fallback broken | → `activeFlightIds` Set preserves same keys |
| F8: nodes.ts job before validation | → reorder in async mode |
| F9: Route export convention | → `registerEventsRoute(app, ctx)` |
| F10: 202 inconsistency | → explicit `res.status(202).json(...)` everywhere |
