# 11 Test And Verification Plan

## Targeted Tests

### `tests/agent-mode-run-progress-contract.test.ts`

New executable behavior-focused test for `deriveAgentRunProgress`. This test imports the TypeScript helper and asserts returned `AgentTurn[]` values.

Cases:

| Case | Input | Expected |
|---|---|---|
| queued recovery | real user turn, queue item `queued`, no local pending | synthetic assistant streaming turn with queued text |
| running recovery | real user turn, queue item `running`, no local pending | synthetic assistant streaming turn with running/planning text |
| local pending rewrite | local pending exists + summary queued | pending text becomes `pendingQueued` |
| no busy queue | complete turns only | no synthetic turn |
| prelude plus running queue | assistant prelude exists + queue running | prelude remains and progress turn remains |
| active item priority | one queued and one running item | running item drives synthetic progress |
| display tail | later assistant prelude exists + running item | synthetic progress is appended as active tail |

### `tests/agent-mode-frontend-contract.test.js`

Update existing source contract:

- Assert `AgentWorkspace.tsx` imports `deriveAgentRunProgress`.
- Assert `selectSession` does not call `loadWorkspace(id)` directly.
- Assert `displayTurns` is produced from queue items and selected run summary.
- Assert `AgentWorkspace.tsx` imports local turn helpers from `agentLocalTurns.ts`.
- Keep existing `aria-live`, run group, and streaming indicators.

### `tests/agent-mode-right-sidebar-contract.test.js`

Update queue synchronization contract:

- Assert chat progress and queue panel consume same `queueItems` and `selectedRunSummary`.
- Assert no separate duplicate queue status derivation appears in right sidebar.

## Manual Browser Smoke

Use local server with a long-running mocked or real Agent run.

Steps:

1. Open Agent mode.
2. Send prompt that creates queued/running work.
3. Confirm chat shows one run block with progress.
4. Click another session.
5. Click back to original session before job completes.
6. Confirm progress block still exists.
7. Wait for completion.
8. Confirm synthetic/local pending disappears and final assistant/tool output remains.

Expected UI:

```text
Agent
  Tool run / or queued spinner
  Planning the response... / Running tools and generating...
  Final answer or image result
```

## Commands

Run after patch:

```bash
node --import tsx --test tests/agent-mode-run-progress-contract.test.ts tests/agent-mode-frontend-contract.test.js tests/agent-mode-right-sidebar-contract.test.js
npm run typecheck
npm run ui:build
npm test
```

Optional rendered verification:

```bash
npm start
cli-jaw browser start --agent
cli-jaw browser navigate "http://127.0.0.1:<actual-port>"
cli-jaw browser snapshot --interactive
cli-jaw browser screenshot --json
```

## Pass Criteria

- Targeted tests pass.
- TypeScript typecheck passes.
- UI production build passes.
- Full test suite passes.
- Browser smoke shows no blank/idle chat state while selected session has queued/running work.
- `AgentWorkspace.tsx` remains below 500 lines after extraction.
- `tests/agent-mode-run-progress-contract.test.ts` executes helper behavior; source-string checks alone are not sufficient.

## Known Non-Blocking Risk

The full suite can be affected by an already-running local `ima2 serve` process during `server-fallback-contract`. If that happens, stop the manual verification server and rerun. The final proof must be a clean suite with no manual server listening on the tested ports.
