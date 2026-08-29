---
phase: 0
priority: critical
status: plan
files:
  - ui/src/lib/agentApi.ts (MODIFY)
  - ui/src/components/agent/AgentWorkspace.tsx (MODIFY)
---

# Phase 0 — Runtime Crash Fix

## Error

```
AgentWorkspace-BL6qiGRG.js:3 Uncaught TypeError:
Cannot read properties of undefined (reading 'as_01KRRHGY9QG7J7TKYYHG5W9J1K')
```

## Root Cause

### Crash site (AgentWorkspace.tsx:214-218)

```ts
// 이 라인들에서 workspace.XXX 가 undefined 일 때 crash
const images = (workspace.imageIdsBySession[selectedSessionId] ?? [])...  // L214
const turns = workspace.turnsBySession[selectedSession.id] ?? [];          // L216
const queueItems = workspace.queueBySession[selectedSessionId] ?? [];      // L217
const selectedRunSummary = workspace.runSummaryBySession[selectedSessionId] // L218
```

### Origin (agentApi.ts:18)

```ts
async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  const data = (await res.json().catch(() => ({}))) as T & {...};  // ← HERE
  if (!res.ok) { throw err; }
  return data;  // res.ok=true + json parse fail → {} 반환
}
```

**Trigger path**:
1. Server returns 200 but body is incomplete (network drop, HMR, empty body)
2. `res.json()` fails → catch returns `{}`
3. `res.ok` = true → no throw
4. `applyWorkspace({})` → state becomes `{ }` (no Record fields)
5. Render: `undefined['as_01...']` → **CRASH**

## Fix Plan

### Fix A — agentApi.ts:18 (원인 제거)

```diff
- const data = (await res.json().catch(() => ({}))) as T & {
-   error?: string | { message?: string; code?: string };
-   code?: string;
- };
+ let data: T & { error?: string | { message?: string; code?: string }; code?: string };
+ try {
+   data = await res.json();
+ } catch {
+   throw new Error(`Invalid JSON response from ${url}`);
+ }
```

**효과**: JSON 파싱 실패 시 즉시 throw → 호출측 `.catch()`에서 잡힘 → workspace state 오염 방지

### Fix B — AgentWorkspace.tsx:160 (방어선)

```diff
  const applyWorkspace = useCallback((payload: AgentWorkspacePayload) => {
-   setWorkspace(payload);
-   setSelectedSessionId(payload.selectedSessionId);
+   setWorkspace((current) => ({
+     ...current,
+     ...payload,
+     turnsBySession: payload.turnsBySession ?? current.turnsBySession,
+     imagesById: payload.imagesById ?? current.imagesById,
+     imageIdsBySession: payload.imageIdsBySession ?? current.imageIdsBySession,
+     queueBySession: payload.queueBySession ?? current.queueBySession,
+     runSummaryBySession: payload.runSummaryBySession ?? current.runSummaryBySession,
+   }));
+   setSelectedSessionId(payload.selectedSessionId ?? null);
  }, []);
```

**효과**: payload에 누락 필드 있어도 이전 state 유지 → never undefined

### Fix C — mergeWorkspaceWithLocalTurns:141 (보조)

```diff
- return { ...incoming, turnsBySession };
+ return {
+   ...incoming,
+   turnsBySession,
+   imagesById: incoming.imagesById ?? {},
+   imageIdsBySession: incoming.imageIdsBySession ?? {},
+   queueBySession: incoming.queueBySession ?? {},
+   runSummaryBySession: incoming.runSummaryBySession ?? {},
+ };
```

## Verification

1. `npx tsc --noEmit` — 타입 에러 없음
2. Server 중지 후 Agent 탭 열기 → crash 대신 reconnecting 표시
3. Network throttle (slow 3G) + 생성 중 새로고침 → crash 없음
4. 정상 flow: 세션 생성 → 메시지 전송 → 이미지 생성 → 확인
