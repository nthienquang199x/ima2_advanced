# 02 Dev Skill Gap Audit

## Classification

- Work class: C3.
- Reason: issue crosses frontend state, server queue contract, UX state design, session switching, and regression tests.
- Required care: root-cause analysis, architecture-aware plan, independent audit, focused tests plus full suite after patch.

## dev-debugging Findings

| Rule | Current Gap | Evidence |
|---|---|---|
| Phase 0 structural check | This is structural, not a CSS-only bug | Same symptom class recurred across spinner, tool run grouping, queue feedback, and session switch |
| Trace data flow | State flow crosses local turn, server queue, poll refresh, session switch | `AgentWorkspace.tsx` owns all four paths |
| Fix root cause, not symptom | Adding another spinner to CSS would not survive `loadWorkspace()` | Session switch replaces local pending turns |
| One source of truth | Progress has two sources with different lifetimes | `pendingTurnsRef` + `runSummaryBySession` |

## dev-frontend Findings

| Requirement | Current Gap | Impact |
|---|---|---|
| AI UI states must be honest | Chat can look idle while server queue is running | User thinks Agent stopped or ignored the request |
| Loading/streaming state coverage | `queued/running` is shown in sidebar but not guaranteed in chat | Critical status hidden outside current focus |
| State classification before store/effect | Ephemeral local state is carrying server progress responsibility | State is lost on navigation-like session switch |
| Rendered truth verification | Existing tests are mostly source-string contracts | Need browser smoke for session switching and progress continuity |

## dev-uiux-design Findings

| UX Principle | Current Gap | Desired Behavior |
|---|---|---|
| Progressive disclosure | Tool details can be collapsible, but run status must remain visible | Compact run block always visible while work is active |
| Loading state continuity | Running state should persist through common navigation | Switching sessions must not erase “currently working” affordance |
| Visual hierarchy | Header, session row, queue panel, chat block are not synchronized | One coherent run status language: queued, planning, tools, final/error |
| Korean utility UI density | Agent is a working tool, not a marketing surface | Dense, scan-friendly status rows rather than large decorative cards |

## dev-testing Findings

| Testing Rule | Current Gap | Patch Requirement |
|---|---|---|
| Contract tests for shared payloads | `queueBySession/runSummaryBySession` exists, but chat recovery contract does not | Add frontend contract for queue-derived progress item |
| Playwright/rendered smoke for critical flow | Current session-switch progress continuity is not browser-verified | Add or document browser smoke script/steps |
| Regression test for bug | No test asserts `loadWorkspace(id)` uses merge path or durable view model | Add source/behavior contract |
| Avoid test-induced defense | Do not make fake persisted turns just for tests | Test view model output, not DB mutation |

## dev-architecture Findings

| Architecture Rule | Current Gap | Refactor Direction |
|---|---|---|
| Split when module hits 400 LOC | `AgentWorkspace.tsx` is 500 LOC | Extract progress/session controller helpers |
| Single source of truth | Progress source split across queue summary and local pending | Queue-derived display model becomes canonical |
| Avoid hidden temporal coupling | `pendingTurnsRef` must line up with async enqueue/finally and cleanup effect | Replace with explicit local pending ids/state keyed by session/queue |
| Boundary-only defense | Frontend should not infer impossible server states with ad hoc rules | Server queue status remains boundary contract; frontend derives display only |

## Severity Ranking

1. High: `loadWorkspace()` drops local pending on session switch.
2. High: chat timeline cannot reconstruct running state from durable queue.
3. Medium: `AgentWorkspace.tsx` is at 500 LOC and has mixed responsibilities.
4. Medium: status UI sources are inconsistent across header/sidebar/chat/queue.
5. Medium: tests do not cover session-switch recovery.
6. Low: queue row visual treatment is functional but not integrated into the chat narrative.

## Recommended Engineering Standard

After patch, the Agent UI should have this invariant:

> If `queueBySession[sessionId]` contains a queued/running item, then every view that can display that session must expose a non-idle progress affordance, regardless of local optimistic turns.

