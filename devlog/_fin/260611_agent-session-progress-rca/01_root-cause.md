# 01 Root Cause Analysis

## Symptom

When an Agent queue item is running or queued, switching to another Agent session and returning can remove the visible spinner/progress block in the chat. The right/sidebar status may still know something is running, but the chat timeline no longer shows the pending block the user expects.

## Direct Cause

`selectSession(id)` calls `loadWorkspace(id)`, and `loadWorkspace()` calls `applyWorkspace(loaded)`.

`applyWorkspace()` performs a full replacement:

```ts
setWorkspace({ ...emptyWorkspace(), ...payload });
setSelectedSessionId(payload.selectedSessionId ?? null);
```

That full replacement discards local turns, including the `localPendingTurn()` that carries:

```ts
role: "assistant",
status: "streaming"
```

The polling path has a different behavior:

```ts
refreshWorkspace() -> applyWorkspaceWithLocalTurns(loaded, new Set())
```

This path preserves local pending turns. Therefore the bug depends on the route into workspace replacement:

| Path | Preserves pending? |
|---|---:|
| Poll refresh while staying in same selected session | Yes |
| Enqueue 202 merge | Yes, except settled local user turn |
| Session switch through `loadWorkspace(id)` | No |
| Initial load/reload/remount | No |

## Structural Cause

The UI treats a local optimistic turn as both:

1. immediate optimistic feedback after send, and
2. the canonical progress indicator for the running queue item.

Those are different responsibilities.

The durable source of truth is the queue item (`agent_queue_items`) and its projection (`queueBySession`, `runSummaryBySession`). The local pending turn should only be an optimistic overlay before the server payload catches up.

## Why The Current Cleanup Logic Cannot Fully Fix It

There is a cleanup effect:

```ts
if (pendingTurnsRef.current > 0) return current;
...
const busy = summary?.status === "queued" || summary?.status === "running";
if (busy) continue;
turnsBySession[sessionId] = turns.filter((turn) => !isLocalPendingTurn(turn));
```

This only prevents cleanup from removing existing pending turns too early. It does not recreate a pending/progress block after `loadWorkspace()` has already dropped it.

## Why Server Polling Alone Cannot Fully Fix It

Polling updates `runSummaryBySession` and `queueBySession`, but the chat renderer currently displays progress text only when a local pending turn exists:

```ts
const pendingTurns = turns.filter(isLocalPendingTurn);
if (pendingTurns.length === 0) return null;
```

So a refreshed server payload can say `running`, while chat timeline still has no pending progress row.

## Why The User Notices It More After The Run Group Patch

The run group patch made a correct visual target:

```text
Agent
  Tool run
  intermediate text
  final text
```

But it still consumes `turns` only. Since queued/running state is not represented as a durable turn or derived display item, the grouped block disappears when the local pending turn disappears.

## Root Cause Statement

The root cause is state ownership drift: Agent progress is modeled partly as durable server queue state and partly as ephemeral local chat turns, without a single derived UI model that survives session switch, reload, and polling replacement.

## Required Architectural Correction

Create a durable progress projection for the selected session:

```ts
deriveAgentRunProgress({
  turns,
  queueItems,
  runSummary,
  localPendingTurns,
})
```

This projection should produce display-only run items for queued/running queue work even when no local pending turn exists. It should not write fake turns to SQLite; it should be a frontend view model.

## Non-Goals

- Do not make every queue status into a persisted assistant turn.
- Do not fake provider token streaming.
- Do not remove the durable queue panel.
- Do not make local pending turns survive by storing them in localStorage; the server queue already owns the durable state.

