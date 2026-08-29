---
created: 2026-05-16
status: plan
tags: [agent-mode, right-sidebar, prompt-library, model-settings, quality]
depends_on:
  - 00_overview.md
  - 03_phase2_queue_and_parallel_runtime.md
---

# Phase 3 Right Sidebar, Models, Forms, And Quality

## Phase Goal

Turn the current right image pane into a real Agent control sidebar without
losing the large current-image workflow.

The right side should answer:

- What image am I looking at?
- What references/web/memory affect the next turn?
- Which prompt-library snippets can I insert?
- Which form/template should this generation follow?
- Which model, quality, size, provider, reasoning, and moderation settings will
  the next queued item use?
- What is currently queued/running for this session?

## Sidebar IA

Replace the single-purpose `AgentImagePane` usage with:

```text
AgentRightSidebar
  ├─ Current Image
  │   ├─ preview
  │   └─ variants
  ├─ Context tabs
  │   ├─ Image
  │   ├─ Refs
  │   ├─ Web
  │   └─ Memory
  ├─ Prompt Library
  ├─ Forms
  ├─ Quality
  ├─ Model
  └─ Queue
```

On wide desktop, this can be one right column with nested tabs. On smaller
laptop widths, keep current image visible and move lower controls into tabs or
a drawer.

## New Components

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

Existing components to keep and reuse:

```text
ui/src/components/agent/AgentImagePane.tsx
ui/src/components/agent/AgentContextTabs.tsx
ui/src/components/PromptLibraryPanel.tsx
ui/src/components/ImageModelSelect.tsx
ui/src/components/prompt-builder/PromptBuilderModelMenu.tsx
ui/src/lib/imageModels.ts
```

If existing prompt-library components are too coupled to Classic mode, create a
thin Agent adapter instead of duplicating library logic.

## Generation Settings Model

Add a session-scoped settings snapshot:

```ts
export type AgentGenerationSettings = {
  provider: "oauth" | "api";
  model: string;
  quality: "low" | "medium" | "high";
  size: string;
  format: "png" | "webp" | "jpeg";
  moderation: "auto" | "low";
  reasoningEffort?: "low" | "medium" | "high" | "xhigh";
  webSearchEnabled: boolean;
  variants: number;
  parallelism: number;
};
```

Persistence options:

| Scope | Use |
|---|---|
| Session settings | Default for future prompts in this Agent session. |
| Queue item options | Immutable snapshot used for one queued item. |
| Global defaults | Existing app/config defaults. Used only when a session has no explicit override. |

Add to `agent_sessions`:

```sql
generation_settings TEXT NOT NULL DEFAULT '{}'
```

Expose via `AgentWorkspacePayload` and `PATCH /api/agent/sessions/:sessionId`.

## Top-Right Model Control

The top-right control should not become a second source of truth.

Plan:

- `AgentTopBar` receives selected `AgentGenerationSettings`.
- It shows compact chips:
  - model
  - quality
  - variants/parallelism when not default
- Clicking model chip opens the right sidebar's Model tab.
- Changing model in the sidebar updates session settings.
- Composer queue request snapshots those settings into the queue item.

Acceptance:

- Changing model in the top-right path changes the sidebar Model tab.
- Changing model in the sidebar changes the top-right chip.
- Existing Settings workspace remains global/default settings, not the active
  per-session override UI.

## Forms And Prompt Library

Do not create a second prompt database for forms in the first pass. Reuse the
existing prompt library and classify entries by tags.

Suggested tags:

```text
agent:form
agent:quality
agent:style
agent:composition
agent:negative
```

Form panel behavior:

- shows prompt-library entries tagged `agent:form`;
- can apply a form as:
  - composer insertion;
  - session style lock;
  - queue item template;
- keeps a visible preview of the final prompt contribution.

Quality panel behavior:

Separate "API quality" from "visual quality recipe":

| Layer | Example | Storage |
|---|---|---|
| API quality | `quality: high`, `size: 1536x1024` | `AgentGenerationSettings` |
| Prompt quality recipe | lighting, material, detail, camera, finish | prompt-library tagged snippets or session style locks |

This avoids confusing "quality" as only an API option.

## Context Tabs

Current tabs are static or sparse:

- Image
- Refs
- Web
- Memory

Upgrade plan:

- Image: filename, prompt, revised prompt, model/options, request id.
- Refs: actual session references from `agent_references`.
- Web: recorded findings from `agent_web_findings`, including query/title/url.
- Memory: style locks, subject locks, compact status, manifest preview.

Backend should project these in structured JSON, not make the UI parse XML
manifest text.

Add to payload:

```ts
agentContextBySession: Record<string, {
  references: AgentReferenceSummary[];
  webFindings: AgentWebFindingSummary[];
  styleLocks: string[];
  subjectLocks: string[];
}>;
```

## Right Sidebar API/Store Changes

Modify:

```text
routes/agent.ts
lib/agentStore.ts
lib/agentTypes.ts
ui/src/lib/agentApi.ts
ui/src/components/agent/agentTypes.ts
```

New store helpers:

```ts
setAgentGenerationSettings(sessionId, patch)
setAgentLocks(sessionId, patch)
addAgentReference(sessionId, ref)
removeAgentReference(sessionId, refId)
```

Existing `setAgentLocks()` exists on the backend; expose it in the UI.

## Phase 3 Acceptance

- Right sidebar includes image, prompt library, forms, quality, model, and queue
  surfaces.
- Prompt library entries can be inserted into Agent composer or used as a form.
- Quality panel controls both API quality and visual quality recipes.
- Top-right model setting is synchronized with sidebar model settings.
- Session settings are snapshotted into queued items.
- Image context tabs show real refs/web/locks, not placeholder copy.

