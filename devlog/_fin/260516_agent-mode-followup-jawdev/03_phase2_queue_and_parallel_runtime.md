---
created: 2026-05-16
status: plan
tags: [agent-mode, backend, queue, parallel-generation, runtime]
depends_on:
  - 00_overview.md
  - 01_current_state_and_regressions.md
---

# Phase 2 Queue And Parallel Runtime

## Phase Goal

Make Agent Mode behave like a Jaw/Codex queue:

- sending a prompt creates a durable queue item;
- the UI can keep accepting prompts while earlier work runs;
- queue state survives reload;
- session list shows running/queued/error status per session;
- multiple image generations can run from one prompt/tool plan with bounded
  concurrency;
- completed results append normal Agent turns and image handles.

## Queue Model

Add a durable Agent queue table. Do not rely on in-memory React state or only
the existing `inflight` table.

New schema in `lib/db.ts`:

```sql
CREATE TABLE IF NOT EXISTS agent_queue_items (
  id               TEXT PRIMARY KEY,
  session_id       TEXT NOT NULL,
  request_id       TEXT NOT NULL,
  prompt           TEXT NOT NULL DEFAULT '',
  options          TEXT NOT NULL DEFAULT '{}',
  tool_plan        TEXT NOT NULL DEFAULT '{}',
  status           TEXT NOT NULL DEFAULT 'queued',
  position         INTEGER NOT NULL DEFAULT 0,
  result_image_ids TEXT NOT NULL DEFAULT '[]',
  error_code       TEXT,
  error_message    TEXT,
  created_at       INTEGER NOT NULL,
  started_at       INTEGER,
  finished_at      INTEGER,
  FOREIGN KEY (session_id) REFERENCES agent_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_queue_session
  ON agent_queue_items(session_id, status, created_at);

CREATE INDEX IF NOT EXISTS idx_agent_queue_status
  ON agent_queue_items(status, created_at);
```

Status enum:

```ts
type AgentQueueStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "canceled";
```

## Queue Store Modules

New files:

```text
lib/agentQueueStore.ts
lib/agentQueueWorker.ts
lib/agentSettings.ts
tests/agent-mode-queue-contract.test.ts
tests/agent-mode-parallel-contract.test.ts
```

Keep compatibility:

```text
lib/agentRuntime.ts
```

Current implementation keeps the existing flat `lib/*.ts` convention instead
of adding a nested `lib/agent/` directory. `lib/agentRuntime.ts` remains the
runtime facade and exports the existing synchronous `runAgentTurn()` path for
tests/compatibility while the UI uses queue endpoints.

## Queue API

Add to `routes/agent.ts` or split into `routes/agentQueue.ts` if line count
approaches the 500-line limit.

Endpoints:

```http
GET /api/agent/queue
GET /api/agent/sessions/:sessionId/queue
POST /api/agent/sessions/:sessionId/queue
POST /api/agent/queue/:itemId/cancel
POST /api/agent/queue/:itemId/retry
```

MVP request:

```json
{
  "prompt": "four logo concepts",
  "options": {
    "provider": "oauth",
    "model": "gpt-5.4",
    "quality": "high",
    "size": "1024x1024",
    "format": "png",
    "moderation": "low",
    "reasoningEffort": "medium",
    "webSearchEnabled": true,
    "parallelism": 2,
    "variants": 4
  },
  "plan": {
    "mode": "fanout",
    "prompts": [
      "logo concept A ...",
      "logo concept B ..."
    ]
  }
}
```

MVP response:

```json
{
  "queueItem": {
    "id": "aq_...",
    "sessionId": "as_...",
    "status": "queued",
    "position": 2
  },
  "workspace": { "...": "AgentWorkspacePayload" }
}
```

## Parallel Generation Modes

Support two modes:

| Mode | Meaning | First implementation |
|---|---|---|
| `single` | One prompt, one image. | Existing behavior through queue. |
| `fanout` | One user prompt becomes N generation prompts. | Use explicit `variants` or a parsed prompt list. |

Later mode:

| Mode | Meaning | Reason to defer |
|---|---|---|
| `tool_plan` | Agent emits multiple tool calls with different arguments. | Requires richer LLM tool planning and validation. |

First pass should not ask the model to invent arbitrary tools. The host should
build an explicit generation plan:

```ts
type AgentGenerationPlan = {
  mode: "single" | "fanout";
  prompts: string[];
  options: AgentGenerationOptions;
};
```

The plan is then executed by `toolExecutor`.

## Bounded Concurrency

Use a small queue worker with configurable limits:

```ts
type AgentQueueConfig = {
  maxGlobalRunning: number;     // default 2
  maxSessionRunning: number;    // default 1
};
```

Do not let a single session starve all others. A simple first pass:

- pick oldest queued item;
- skip if its session already has `maxSessionRunning`;
- run up to `maxGlobalRunning`;
- inside a fanout item, use the queue item's snapshotted
  `options.parallelism`, clamped by runtime to 1-8.

## Relationship To Existing `inflight`

The existing `inflight` table powers active/recent jobs and CLI observability.
Agent queue should own Agent scheduling, but mirror each running item into
`inflight`:

```text
agent_queue_items: durable Agent work order
inflight: cross-product active/recent observability
```

That makes `ima2x inflight ls` still useful without overloading it with queue
semantics it was not designed to own.

The prompt plan is frozen when the queue item is inserted: `tool_plan` stores
`JSON.stringify(plan)`, so later edits to settings or prompt templates do not
change already queued work.

## Frontend Queue Types

Extend `AgentWorkspacePayload`:

```ts
type AgentSessionRunSummary = {
  status: "idle" | "queued" | "running" | "error";
  queuedCount: number;
  runningCount: number;
  lastQueueItemId?: string | null;
  lastError?: string | null;
};

type AgentQueueItem = {
  id: string;
  sessionId: string;
  prompt: string;
  status: AgentQueueStatus;
  position: number;
  resultImageIds: string[];
  errorCode?: string | null;
  errorMessage?: string | null;
  createdAt: number;
  startedAt?: number | null;
  finishedAt?: number | null;
};
```

Payload additions:

```ts
queueBySession: Record<string, AgentQueueItem[]>;
runSummaryBySession: Record<string, AgentSessionRunSummary>;
```

## Frontend Queue UI

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
ui/src/lib/agentApi.ts
ui/src/components/agent/agentTypes.ts
```

Composer changes:

- `Send` enqueues by default.
- Add a small send-menu for:
  - Send now / queue
  - Variants count
  - Parallelism
- Disable only when prompt is empty, not when another item is running.

Session list changes:

- show spinner when `runningCount > 0`;
- show queued badge when `queuedCount > 0`;
- show error marker when latest item failed;
- clicking a session switches chat and queue context.

## Session-Specific Spinners

Spinner source must be server payload, not `pendingTurnsRef`.

Acceptance:

- Session A running shows spinner on Session A row only.
- Session B queued shows queued badge on Session B row only.
- Switching sessions keeps the correct spinner/badge.
- Reloading the page preserves queue state.
- A completed queue item clears the spinner and appends image turns.

## Phase 2 Acceptance

- User can submit a second prompt while the first is running.
- Queue rows appear and update.
- A queued item can be canceled before running.
- Failed item can be retried.
- Parallel fanout stores multiple image handles in one session.
- Existing synchronous runtime tests still pass through compatibility APIs.
