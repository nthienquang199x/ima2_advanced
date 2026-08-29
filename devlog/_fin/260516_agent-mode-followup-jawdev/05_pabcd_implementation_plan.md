---
created: 2026-05-16
status: P / plan
tags: [pabcd, jawdev, implementation-plan]
project_root: /Users/jun/Developer/new/700_projects/ima2-gen
depends_on:
  - 00_overview.md
  - 01_current_state_and_regressions.md
  - 02_phase1_layout_and_tool_folding.md
  - 03_phase2_queue_and_parallel_runtime.md
  - 04_phase3_right_sidebar_models_and_quality.md
---

# PABCD Implementation Plan

## Part 1: Easy Explanation

We will keep the current Agent Mode, but harden it into a real queue-based
image-agent workspace.

First, fix the visible workspace:

- the Agent panes should stay horizontally organized on desktop/laptop;
- sessions can be pinned as a full sidebar or a compact rail;
- tool calls should open like cli-jaw: one row for the tool group, then nested
  rows for each tool's input/output/artifact details.

Second, add the queue:

- sending a prompt adds it to a durable server queue;
- the user can send more prompts while one is running;
- every session row gets its own spinner/queued badge/error marker;
- queue state survives reload;
- one prompt can generate several images in parallel with a bounded limit.

Third, make the right side useful:

- keep current image and variants;
- add prompt library;
- add form/template controls;
- add quality controls;
- add model/provider/size/reasoning settings;
- sync top-right model chips with the sidebar model tab;
- snapshot settings into each queued job.

This should be implemented as a new active lane, not as a patch to the already
finished Agent Mode closeout.

## Part 2: Diff-Level Plan

### Phase A: Layout + Tool Folding

New files:

```text
ui/src/components/agent/AgentLayoutShell.tsx
ui/src/components/agent/AgentPaneToggle.tsx
ui/src/components/agent/AgentToolGroup.tsx
ui/src/components/agent/AgentToolCallRow.tsx
ui/src/components/agent/AgentToolCallDetails.tsx
ui/src/lib/agentLayout.ts
ui/src/lib/agentToolFormatting.ts
tests/agent-mode-layout-contract.test.js
tests/agent-mode-tool-folding-contract.test.js
```

Modify:

```text
ui/src/components/agent/AgentWorkspace.tsx
ui/src/components/agent/AgentTopBar.tsx
ui/src/components/agent/AgentSessionSidebar.tsx
ui/src/components/agent/AgentSessionRail.tsx
ui/src/components/agent/AgentMessage.tsx
ui/src/components/agent/agentTypes.ts
ui/src/hooks/useAgentWorkspaceLayout.ts
ui/src/styles/agent-workspace.css
ui/src/styles/agent-workspace-panels.css
ui/src/i18n/en.json
ui/src/i18n/ko.json
lib/agentTypes.ts
lib/agentStore.ts
lib/agentRuntime.ts
tests/agent-mode-frontend-contract.test.js
tests/agent-mode-runtime-contract.test.ts
```

Before:

```text
AgentWorkspace does layout composition directly.
useAgentWorkspaceLayout only returns one of four modes from window size.
AgentMessage handles tool turns with one boolean expansion state.
AgentTurn exposes only role/text/imageIds/webFindingIds/status.
```

After:

```text
AgentLayoutShell owns pane composition.
agentLayout.ts owns pure layout resolution and tests.
Agent pane preference can pin sessions or rail.
AgentMessage delegates tool turns to AgentToolGroup.
AgentTurn can include structured toolCalls from raw backend data.
```

### Phase B: Queue Backend

New files:

```text
lib/agentQueueStore.ts
lib/agentQueueWorker.ts
lib/agentSettings.ts
tests/agent-mode-queue-contract.test.ts
tests/agent-mode-parallel-contract.test.ts
```

Modify:

```text
lib/db.ts
lib/agentRuntime.ts
lib/agentStore.ts
lib/agentTypes.ts
routes/agent.ts
routes/index.ts
tests/agent-mode-runtime-contract.test.ts
```

Before:

```text
POST /api/agent/sessions/:sessionId/turns waits for runAgentTurn().
runAgentTurn() appends turns and calls generateViaResponses once.
No durable queue item exists.
No per-session running summary exists.
```

After:

```text
POST /api/agent/sessions/:sessionId/queue creates agent_queue_items rows.
Agent queue worker executes queued items with bounded concurrency.
Synchronous runAgentTurn remains for compatibility.
Workspace payload includes queueBySession and runSummaryBySession.
Completed items append normal user/tool/assistant turns and image handles.
```

### Phase C: Queue Frontend + Per-Session Spinner

New files:

```text
ui/src/components/agent/AgentQueuePanel.tsx
ui/src/components/agent/AgentQueueRow.tsx
ui/src/components/agent/AgentSessionSpinner.tsx
ui/src/lib/agentQueueFormatting.ts
```

Modify:

```text
ui/src/components/agent/AgentWorkspace.tsx
ui/src/components/agent/AgentChatPane.tsx
ui/src/components/agent/AgentComposer.tsx
ui/src/components/agent/AgentSessionList.tsx
ui/src/components/agent/AgentSessionRail.tsx
ui/src/components/agent/AgentStatusBadge.tsx
ui/src/components/agent/agentTypes.ts
ui/src/lib/agentApi.ts
ui/src/styles/agent-workspace-panels.css
ui/src/i18n/en.json
ui/src/i18n/ko.json
tests/agent-mode-frontend-contract.test.js
```

Before:

```text
pendingTurnsRef tracks local running state.
Composer sends and then clears one prompt.
Session list cannot show queued/running state per session.
```

After:

```text
Composer enqueues.
Queue panel shows active/recent queued items.
Session row/rail display spinner and queued badge from server summaries.
User can cancel queued item and retry failed item.
```

### Phase D: Parallel Generation

Modify:

```text
lib/agentRuntime.ts
lib/agentQueueWorker.ts
routes/agent.ts
ui/src/components/agent/AgentComposer.tsx
ui/src/components/agent/AgentGenerationSettingsPanel.tsx
tests/agent-mode-parallel-contract.test.ts
```

Before:

```text
One user prompt maps to one image generation request.
```

After:

```text
One user prompt can map to:
  single: one generation
  fanout: N generation prompts

Queue item result_image_ids can contain multiple image IDs.
Tool group can show multiple ima2.generate_image child calls.
```

### Phase E: Right Sidebar + Model/Quality/Form

New files:

```text
ui/src/components/agent/AgentRightSidebar.tsx
ui/src/components/agent/AgentSidebarTabs.tsx
ui/src/components/agent/AgentGenerationSettingsPanel.tsx
ui/src/components/agent/AgentModelSelector.tsx
ui/src/components/agent/AgentQualityPanel.tsx
ui/src/components/agent/AgentFormTemplatePanel.tsx
ui/src/components/agent/AgentPromptLibraryPanel.tsx
ui/src/components/agent/AgentRunInspector.tsx
ui/src/lib/agentGenerationSettings.ts
tests/agent-mode-right-sidebar-contract.test.js
```

Modify:

```text
ui/src/components/agent/AgentWorkspace.tsx
ui/src/components/agent/AgentTopBar.tsx
ui/src/components/agent/AgentImagePane.tsx
ui/src/components/agent/AgentContextTabs.tsx
ui/src/components/agent/agentTypes.ts
ui/src/lib/agentApi.ts
ui/src/styles/agent-workspace.css
ui/src/styles/agent-workspace-panels.css
ui/src/i18n/en.json
ui/src/i18n/ko.json
routes/agent.ts
lib/agentStore.ts
lib/agentTypes.ts
lib/db.ts
tests/agent-mode-runtime-contract.test.ts
```

Before:

```text
Right pane is image context only.
Route accepts generation options but UI does not expose session settings.
Web-search toggle is the only visible Agent setting.
```

After:

```text
Right sidebar includes Image, Context, Prompt Library, Forms, Quality, Model,
and Queue/Run Inspector.
Session generation settings are persisted.
Top-right model chip opens/syncs with sidebar model tab.
Queue item options snapshot the current session settings.
```

## Audit Questions For A Phase

Plan audit should verify:

- `routes/index.ts` actually exists and route registration pattern matches.
- `PromptLibraryPanel` can be reused safely inside Agent or needs an adapter.
- `ImageModelSelect` or `PromptBuilderModelMenu` is the better model control
  base.
- `lib/db.ts` file length remains under limit after schema additions.
- `routes/agent.ts` stays under 500 lines; split only if it approaches the cap.
- `AgentWorkspace.tsx` stays under 500 lines after extracting shell/queue/sidebar.
- Existing `agent-mode-*` tests are updated, not deleted.
- New queue worker does not start duplicate workers in tests or repeated route
  registration.

## Business Logic I Should Not Decide Alone

These can be defaulted for implementation, but should be confirmed before B:

1. Default Agent queue concurrency:
   - recommended: global 2, per-session 1; fanout uses queue item
     `options.parallelism` clamped to 1-8.
2. Default queued prompt behavior:
   - recommended: every send enqueues; selected session still shows optimistic
     queued row immediately.
3. Form/template storage:
   - recommended: reuse prompt-library tags first, no new table in MVP.
4. Model setting scope:
   - recommended: session-scoped override, queue item snapshots, global
     settings remain defaults.
