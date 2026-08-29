# 10 Patch Plan

## Part 1: Human Explanation

The Agent UI should stop treating a local pending chat bubble as the only proof that work is happening. The server queue already knows when a session is queued or running, so the chat pane should derive a progress block from that durable queue state. Local pending bubbles should remain for instant feedback after clicking Send, but switching sessions should rebuild the visible run progress from `queueBySession` and `runSummaryBySession`. This turns the current fragile optimistic UI into a session-safe Agent progress model.

## Part 2: Diff-Level Plan

### NEW `ui/src/components/agent/agentRunProgress.ts`

Purpose: Create a pure display view model from persisted turns + queue state + local optimistic turns.

Exports:

```ts
export function deriveAgentRunProgress(input: {
  turns: AgentTurn[];
  queueItems: AgentQueueItem[];
  runSummary?: AgentSessionRunSummary;
  pendingText: {
    queued: string;
    planning: string;
    running: string;
  };
}): AgentTurn[];
```

Behavior:
- Preserve real turns in their existing order.
- If local pending turns already exist, rewrite their text from durable status.
- Select the active queue item deliberately: first item with `status === "running"`, otherwise first item with `status === "queued"`.
- If no local pending exists but the active queue item is `queued` or `running`, append one synthetic assistant turn as the active progress tail:
  - id: `agent-synthetic-progress-${queueItem.id}`
  - role: `assistant`
  - status: `streaming`
  - text: queued/planning/running text
  - createdAt: `Date.now()` or queue item `startedAt ?? createdAt`; ordering is display-tail semantics, not a chronological history write
- If queue item failed and no persisted assistant error turn exists yet, do not synthesize a fake error in this helper; rely on worker error turn and queue panel.
- Do not export an unused `AgentRunProgress` type unless renderers are changed to consume a real view model. Current renderers consume `AgentTurn[]`, so `AgentTurn[]` is the planned return shape.

### MODIFY `ui/src/components/agent/AgentWorkspace.tsx`

Current issue:

```ts
const displayTurns = pendingStageText
  ? turns.map((turn) => (isLocalPendingTurn(turn) ? { ...turn, text: pendingStageText } : turn))
  : turns;
```

After:

```ts
const displayTurns = deriveAgentRunProgress({
  turns,
  queueItems,
  runSummary: selectedRunSummary,
  pendingText: {
    queued: t("agent.pendingQueued"),
    planning: t("agent.pendingPlanning"),
    running: t("agent.pendingGenerating"),
  },
});
```

Additional changes:
- Remove `pendingStageText` inline IIFE.
- Keep `localPendingTurn()` for immediate optimistic feedback.
- Change `selectSession(id)` from `loadWorkspace(id)` to a preserving refresh path:

```ts
const selectSession = (id: string) => {
  setDrawerOpen(false);
  setSelectedSessionId(id);
  void refreshWorkspace(id).catch(console.error);
};
```

- Because `AgentWorkspace.tsx` is already exactly 500 lines, this patch must extract local turn helpers into `agentLocalTurns.ts`.
- `agentRunProgress.ts` and `agentLocalTurns.ts` are both required:
  - `agentRunProgress.ts` owns durable queue-derived display turns.
  - `agentLocalTurns.ts` owns local optimistic turn helpers and shared `isLocalPendingTurn()`.
- `AgentWorkspace.tsx` must import both helpers and remain below 500 lines after the patch.

### NEW `ui/src/components/agent/agentLocalTurns.ts`

Move:
- `LOCAL_TURN_PREFIX`
- `localUserTurn`
- `localPendingTurn`
- `localErrorTurn`
- `isLocalTurn`
- `isLocalPendingTurn`
- `nextLocalTurnId`

Rationale: `AgentWorkspace.tsx` is exactly 500 lines, so any non-trivial patch needs extraction. `deriveAgentRunProgress()` also needs a shared `isLocalPendingTurn()` without duplicating prefix knowledge.

### MODIFY `ui/src/components/agent/AgentRunGroup.tsx`

Add optional synthetic styling:

```tsx
const stepClassName = [
  "agent-run__step",
  turn.status === "streaming" ? "is-streaming" : "",
  turn.status === "error" ? "is-error" : "",
  turn.id.startsWith("agent-synthetic-progress-") ? "is-synthetic" : "",
].filter(Boolean).join(" ");

return <li key={turn.id} className={stepClassName}>...</li>;
```

Keep rendering as an assistant run block. Do not create a second card.

Alternative: avoid changing `AgentRunGroup` if synthetic turns can be styled through existing `status:"streaming"` only. If the patch uses `is-synthetic`, the marker must be derived from the stable `agent-synthetic-progress-` id prefix and tested. Do not keep the current leading-space `itemClass` convention if adding multiple conditional tokens; switch the whole `li` class to array + `join(" ")` so `.agent-run__step.is-synthetic` selectors match.

### MODIFY `ui/src/styles/agent-workspace-panels.css`

Add subtle treatment:

```css
.agent-run__step.is-synthetic .agent-run__step-body p {
  color: var(--text-dim);
}
```

Do not add a new large card or marketing-style loading state.

### MODIFY `tests/agent-mode-frontend-contract.test.js`

Add contract assertions:
- `AgentWorkspace.tsx` imports `deriveAgentRunProgress`.
- `selectSession` uses `refreshWorkspace(id)` or an equivalent merge-preserving path, not bare `loadWorkspace(id)`.
- `deriveAgentRunProgress` creates `agent-synthetic-progress-` turns for queued/running queue items.
- `AgentRunGroup` recognizes synthetic progress turns.
- `AgentWorkspace.tsx` imports local turn helpers from `agentLocalTurns.ts` instead of keeping them inline.

### NEW `tests/agent-mode-run-progress-contract.test.ts`

Executable behavior tests for pure helper. These must import and run `deriveAgentRunProgress()`, not only grep source strings.

1. queued item + no local pending -> synthetic streaming assistant turn exists.
2. running item + no local pending -> synthetic streaming assistant turn exists.
3. local pending + queued summary -> local pending text becomes pendingQueued.
4. no queue + complete turns -> no synthetic progress turn.
5. running item with server assistant prelude -> progress turn remains until queue settles.

Use direct unit coverage against `agentRunProgress.ts`. Because the helper is TypeScript, targeted execution should use `node --import tsx --test`.

### MODIFY `tests/agent-mode-right-sidebar-contract.test.js`

Add assertion that queue status and chat progress share the same source helper or fields:
- `queueItems={queueItems}`
- `runSummary={selectedRunSummary}`
- `deriveAgentRunProgress({ ..., queueItems, runSummary: selectedRunSummary })`

## Patch Order

1. Extract `agentRunProgress.ts` with tests first.
2. Wire `AgentWorkspace.tsx` to use the helper.
3. Change session select path to merge-preserving refresh.
4. Add synthetic styling.
5. Run targeted tests.
6. Run typecheck/build/full suite.
7. Browser smoke session switching.

## Risk Notes

- Synthetic progress turns are display-only and must not be sent to server APIs or persisted.
- If a queue item succeeds between polls, the synthetic turn may briefly show until next refresh; 600ms poll interval keeps this acceptable.
- If a queue item is running in another browser instance, opening the session should show progress even without any local pending turn. This is desired.
- Do not use localStorage for pending progress; it would create stale ghost runs after server completion.
- `cancelQueue()` and `retryQueue()` currently call `.then(applyWorkspace)`, which is a full replace. That remains acceptable only after chat progress is derived from durable `queueItems/runSummary`; local pending must not be required after these actions.
- `listAgentQueueItems()` sorts by status priority, then created time. The helper must not describe the selected item as "latest"; it must explicitly choose active item priority (`running` before `queued`).
