---
created: 2026-05-16
status: plan
tags: [agent-mode, current-state, regression-map]
depends_on:
  - 00_overview.md
---

# Current State And Regression Map

## Chrome Observation

Observed through Computer Use after selecting the `Image Gen` Chrome tab:

```text
URL: http://127.0.0.1:3369/
Mode: Agent
Visible regions:
  left rail
  chat pane
  right image pane
Current image:
  third smoke after ready: small red sphere on gray paper
Visible turns:
  User
  Tool: ima2.get_image_context
  Tool: ima2.web_search + ima2.generate_image
  Agent: Generated an image artifact.
```

The visible UI proves that the first Agent implementation is functional, but
also confirms the gaps:

- Tool turns are shallow summaries.
- The composer cannot enqueue or batch.
- Right pane is image context only.
- Model/quality settings are not part of the Agent surface.
- Session status is global-ish and not visibly per-session.

## Existing Code Ownership

| Area | Current file | Current responsibility |
|---|---|---|
| Workspace orchestration | `ui/src/components/agent/AgentWorkspace.tsx` | Loads workspace, local optimistic turns, selected session, selected image, sends prompt. |
| Layout decision | `ui/src/hooks/useAgentWorkspaceLayout.ts` | Width/height breakpoint function. |
| Shell layout CSS | `ui/src/styles/agent-workspace.css` | Root Agent grid, sessions, rail, topbar. |
| Panel CSS | `ui/src/styles/agent-workspace-panels.css` | Chat, messages, tool summary, composer, image pane, dialogs. |
| Tool turn rendering | `ui/src/components/agent/AgentMessage.tsx` | One-level collapsible tool row. |
| Composer | `ui/src/components/agent/AgentComposer.tsx` | Draft textarea, attach button placeholder, web toggle, send. |
| Image/right pane | `ui/src/components/agent/AgentImagePane.tsx` | Current image, variants, tabs, static tab bodies. |
| Agent routes | `routes/agent.ts` | Sessions CRUD, compact, manifest, synchronous turn endpoint. |
| Runtime | `lib/agentRuntime.ts` | Tool allowlist, user/tool/assistant turn creation, one image generation call, retry. |
| Store | `lib/agentStore.ts` | SQLite-backed sessions, turns, images, refs, web findings, manifest. |
| Schema | `lib/db.ts` | Agent tables exist, but no queue table. |

## Requirement Gap Table

| Req | Symptom | Current root cause | Planned fix |
|---:|---|---|---|
| 1 | Desktop/laptop can collapse into rail/topbar sooner than desired. | `resolveAgentLayout()` only uses viewport width/height; no user-pinned pane mode and no container-based guard. | Add stable Agent layout shell, user layout preference, and CSS/container contracts for horizontal panes. |
| 2 | Tool card has one collapse layer. | `AgentMessage` has one `toolExpanded` boolean and `AgentTurn` has only `text/imageIds`. | Add structured tool groups and nested tool call details. |
| 3 | Prompt send blocks on one turn and returns final payload. | `POST /turns` awaits `runAgentTurn`; no queue item model. | Add durable queue table, queue endpoints, worker, and polling/SSE projection. |
| 4 | Parallel generation is not representable. | Runtime calls `generateViaResponses` once; composer sends only text. | Add generation plan parsing, variants count, tool-call fanout, and bounded concurrency. |
| 5 | Right pane only shows Image/Refs/Web/Memory. | `AgentImagePane` is image inspector, not an Agent sidebar. | Replace with `AgentRightSidebar` that contains image context plus Prompt Library, Forms, Quality, Model. |
| 6 | Model/quality controls are outside Agent flow. | `sendAgentTurn()` only sends prompt; route accepts options but UI does not collect them. | Add session generation settings API/client/state and top-right model control synced to sidebar. |
| 7 | Running status is not per session. | `pendingTurnsRef` is component-local and not persisted or per-session. | Derive session spinners from queue status summaries stored server-side. |

## Non-Negotiable Boundaries

- Keep Agent Mode separate from Classic and Node mode.
- Keep existing exports; preserve `lib/agentRuntime.ts` as a compatibility
  facade if runtime internals move into focused helper modules.
- Do not store raw base64 in chat turns or queue records.
- Do not expose arbitrary tools. Agent Mode remains image-only:
  `ima2.get_image_context`, `ima2.web_search`, `ima2.generate_image`.
- Queue state must survive reload.
- Parallel generation must be bounded. No unbounded `Promise.all` over user
  input.
- Prompt library/form/quality work should reuse existing prompt-library
  storage where possible instead of adding a second prompt database.

## Immediate Implementation Shape

The implementation should start with contracts, not visuals:

1. Extend shared types for session status, queue items, tool groups, and
   generation settings.
2. Add backend store/API contracts.
3. Add frontend read-only projection.
4. Add UI controls.
5. Add worker execution.
6. Verify with contract tests and live browser screenshots.
