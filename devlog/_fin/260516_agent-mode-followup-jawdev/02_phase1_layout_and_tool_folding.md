---
created: 2026-05-16
status: plan
tags: [agent-mode, frontend, layout, tool-folding]
depends_on:
  - 00_overview.md
  - 01_current_state_and_regressions.md
---

# Phase 1 Layout And Tool Folding

## Phase Goal

Fix the immediately visible Agent UI problems before queue/runtime expansion:

- restore a stable horizontal Agent workspace on desktop/laptop;
- prevent accidental vertical/narrow mode when the visible app still has room;
- make the left/session/chat/image regions feel like a deliberate devtool;
- replace shallow tool cards with cli-jaw-style nested tool inspection.

## Layout Decision

Agent Mode needs two different concepts:

| Concept | Meaning |
|---|---|
| Viewport mode | What the screen can physically fit. |
| Pane preference | What the user wants pinned: full sessions, rail, or auto. |

The current `useAgentWorkspaceLayout` mixes those concerns. It should become:

```ts
type AgentPanePreference = "auto" | "sessions" | "rail";

type AgentLayoutMode =
  | "desktop-three-pane"
  | "desktop-rail"
  | "tablet-stacked"
  | "mobile-chat-image-sheet";
```

Rules:

- `desktop-three-pane` should stay active on wide app containers when the user
  pins sessions.
- `desktop-rail` should be an explicit space-saving desktop mode, not a random
  fallback from Chrome zoom or height.
- `tablet-stacked` should be reserved for genuinely narrow container widths.
- `mobile-chat-image-sheet` should remain for phone/small-height cases.

## Layout Files

New files:

```text
ui/src/components/agent/AgentLayoutShell.tsx
ui/src/components/agent/AgentPaneToggle.tsx
ui/src/lib/agentLayout.ts
tests/agent-mode-layout-contract.test.js
```

Modify:

```text
ui/src/components/agent/AgentWorkspace.tsx
ui/src/components/agent/AgentTopBar.tsx
ui/src/components/agent/AgentSessionSidebar.tsx
ui/src/components/agent/AgentSessionRail.tsx
ui/src/hooks/useAgentWorkspaceLayout.ts
ui/src/styles/agent-workspace.css
ui/src/styles/agent-workspace-panels.css
ui/src/i18n/en.json
ui/src/i18n/ko.json
```

## Layout Implementation Notes

Move layout constants out of the hook:

```ts
export function resolveAgentLayout(input: {
  width: number;
  height: number;
  preference: AgentPanePreference;
}): AgentLayoutMode
```

Add tests for:

- `1440x900 + auto` -> `desktop-three-pane`
- `1180x760 + sessions` -> `desktop-three-pane` if minimums fit
- `1180x760 + rail` -> `desktop-rail`
- `976x772 + auto` -> `desktop-rail`, not mobile
- `900x520 + auto` -> `mobile-chat-image-sheet`
- `820x760 + auto` -> `tablet-stacked`

CSS should use stable pane minimums:

```css
.agent-workspace__body {
  grid-template-columns:
    var(--agent-session-column, 280px)
    minmax(380px, 0.95fr)
    minmax(420px, 1.05fr);
}
```

For the complaint that the left side became vertical, acceptance is:

- desktop/laptop shows horizontal regions in one row;
- the rail does not force chat content under the topbar in a cramped vertical
  stack unless the container is truly tablet/mobile;
- the user can pin full sessions from the Agent UI.

## Tool Folding Decision

The current tool turn is:

```text
Tool
ima2.web_search + ima2.generate_image
  [1 img] [chevron]
```

Target cli-jaw-like double folding:

```text
Tool group
  ima2.web_search + ima2.generate_image     [1 img] [duration] [status] >

Expanded group:
  Tool group
    summary row
    ├─ ima2.get_image_context     complete   >
    ├─ ima2.web_search            complete   >
    └─ ima2.generate_image        complete   1 img >

Expanded child:
  ima2.generate_image
    Arguments
    Output summary
    Artifacts
    Timing / request id
```

This needs structured data, not string parsing.

## Tool Data Types

Extend frontend and backend `AgentTurn` projection:

```ts
export type AgentToolCallStatus = "queued" | "running" | "complete" | "error";

export type AgentToolCallSummary = {
  id: string;
  name: AgentToolName;
  status: AgentToolCallStatus;
  startedAt?: number | null;
  finishedAt?: number | null;
  durationMs?: number | null;
  requestId?: string | null;
  inputSummary?: string | null;
  outputSummary?: string | null;
  imageIds?: string[];
  webFindingIds?: string[];
  errorCode?: string | null;
  errorMessage?: string | null;
};

export type AgentTurn = {
  ...
  toolCalls?: AgentToolCallSummary[];
};
```

The existing `raw` column in `agent_turns` can store this immediately. If the
shape becomes important for querying, add a dedicated `agent_tool_calls` table
later. MVP can project from `raw` safely.

## Tool UI Files

New files:

```text
ui/src/components/agent/AgentToolGroup.tsx
ui/src/components/agent/AgentToolCallRow.tsx
ui/src/components/agent/AgentToolCallDetails.tsx
ui/src/lib/agentToolFormatting.ts
tests/agent-mode-tool-folding-contract.test.js
```

Modify:

```text
ui/src/components/agent/AgentMessage.tsx
ui/src/components/agent/agentTypes.ts
ui/src/styles/agent-workspace-panels.css
ui/src/i18n/en.json
ui/src/i18n/ko.json
lib/agentTypes.ts
lib/agentStore.ts
lib/agentRuntime.ts
tests/agent-mode-runtime-contract.test.ts
```

## Tool Accessibility

Rules:

- Outer group button controls the child list.
- Each child row has its own button controlling details.
- Never nest image thumb buttons inside the expand button.
- `aria-expanded`, `aria-controls`, `aria-busy`, and status text must be
  present.
- Keyboard path:
  - Tab enters group.
  - Enter/Space expands group.
  - Tab enters tool rows.
  - Enter/Space expands child detail.
  - Image thumbs remain independently focusable.

## Phase 1 Acceptance

- At desktop/laptop size, Agent body is a horizontal workspace.
- User can pin full sessions or rail without resizing the browser.
- Tool rows use two levels of expansion.
- Current image thumb selection still works after tool UI refactor.
- Existing `agent-mode-frontend-contract.test.js` is updated instead of
  weakened.

