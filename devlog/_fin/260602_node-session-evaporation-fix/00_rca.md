# Node Mode Session Evaporation — Root Cause Analysis & Fix

**Date**: 2026-06-02
**Severity**: Critical (data loss)
**Commit introducing bug**: `a09867a` — `fix(ui): gate agent mode to dev builds`

## Symptom

Node mode sessions disappear on page reload in production builds. Users create nodes, work on graphs, then lose everything after navigating away or refreshing.

## Root Cause

`a09867a` changed session initialization from unconditional to agent-mode-gated:

```diff
- loadSessions();
+ if (ENABLE_AGENT_MODE) loadSessions();
```

`loadSessions()` is the **only** entry point that:
1. Fetches sessions from SQLite (`GET /api/sessions`)
2. Sets `activeSessionId` (required for all graph persistence)
3. Restores the last active session from localStorage

In production builds (`ENABLE_AGENT_MODE = false`, `ENABLE_NODE_MODE = true`):
- `activeSessionId` stays `null`
- `scheduleGraphSave` → `if (!s.activeSessionId) return` → always skips
- Nodes exist only in memory; never persisted to SQLite
- Page reload = total data loss

## DB Evidence

| Metric | Value |
|---|---|
| Total sessions | 100 |
| Sessions with 0 nodes | 84 |
| Sessions with `graph_version > 0` AND 0 nodes | 27 |
| Max graph_version with 0 nodes | 11 |

27 sessions had data saved multiple times (version incremented), then were wiped by empty-array saves.

## Fix (3 patches)

### 1. Root cause — `ui/src/App.tsx:83`

```diff
- if (ENABLE_AGENT_MODE) loadSessions();
+ if (ENABLE_AGENT_MODE || ENABLE_NODE_MODE) loadSessions();
```

### 2. Defensive guard — `doSave()` in `useAppStore.ts`

Prevent saving empty `graphNodes` to a session that already has data (`graphVersion > 0`):

```typescript
if (sessionLoading) return "skipped";
if (graphNodes.length === 0 && graphVersion > 0) return "skipped";
```

### 3. Defensive guard — `flushGraphSaveBeacon()`

Same empty-save protection on page unload:

```typescript
if (s.sessionLoading) return;
if (s.graphNodes.length === 0 && s.activeSessionGraphVersion > 0) return;
```

## Files Changed

- `ui/src/App.tsx` — session load gate fix
- `ui/src/store/useAppStore.ts` — defensive guards in `doSave()` and `flushGraphSaveBeacon()`
