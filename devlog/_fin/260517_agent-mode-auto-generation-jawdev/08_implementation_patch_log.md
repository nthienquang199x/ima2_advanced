---
created: 2026-05-17
status: implementation-patched
tags: [ima2-gen, agent-mode, planner, slash-commands, queue, verification]
---

# Implementation Patch Log

## Patch Summary

This pass converts the auto-generation lane from plan-only into a deterministic
first implementation slice.

Implemented code paths:

1. backend generation strategy schema
2. deterministic request-aware generation planner
3. slash command parser
4. `/question` text-only queue bypass
5. slash-driven fanout queue plans
6. runtime use of planned parallelism
7. assistant text that reports fanout/parallelism/reason
8. UI controls for `Based on user request` vs fixed count
9. queue rows that show planned variants, parallelism, and source
10. composer slash command hint
11. right sidebar split into image/library/forms/quality/model/queue tabs
12. legacy queue-table migration for new queue planner columns
13. server-side rejection of client-submitted queue plans
14. Responses text capture from SSE/JSON output
15. runtime guard for question/text-only plans
16. inflight metadata based on the actual normalized plan

## Backend Changes

### `lib/agentTypes.ts`

- Added `AgentGenerationStrategy`, `AgentGenerationPlanSource`,
  `AgentSlashCommandName`, and `AgentSlashCommand`.
- Expanded `AgentGenerationSettings` with:
  - `generationStrategy`
  - `maxAutoVariants`
- Expanded `AgentGenerationPlan` with:
  - `requestedVariants`
  - `plannedVariants`
  - `plannedParallelism`
  - `source`
  - `reason`
  - optional command/text metadata

Impact: queue rows, runtime fanout, and frontend workspace payload now share a
single visible execution-plan contract instead of inferring from raw settings.

### `lib/agentSettings.ts`

- Default strategy is now `auto`.
- Default `maxAutoVariants` is `8`.
- Existing `variants: 1` remains the manual fixed-count default.
- Existing `parallelism: 2` remains the concurrency cap.

Intent: UI can say `Based on user request` by default while preserving exact
manual counts when the user flips to fixed-count mode.

### `lib/agentCommandParser.ts`

New pure parser for slash commands:

- `/question`
- `/help`
- `/variants`
- `/generate`
- `/parallelism`

The parser extracts a leading `1-8` count and leaves the remaining prompt clean
for queue execution.

### `lib/agentGenerationPlanner.ts`

New pure planner that:

- defaults to one image when the prompt does not ask for multiple outputs;
- infers counts from English and Korean requests such as `three variants`,
  `세 장`, `여러 시안`, `options`, and comparison language;
- respects manual fixed-count settings;
- respects slash count overrides;
- caps fanout by `maxAutoVariants`;
- caps parallelism by requested cap, planned variants, provider, and quality.

The first implementation is deterministic by design. An LLM planner remains a
future extension only after logs prove deterministic gaps.

### `lib/agentQueueStore.ts`

- Queue creation now stores normalized planner output.
- Existing stored queue plans are still normalized when read.
- Queue items now carry explicit `plannedVariants`, `plannedParallelism`,
  `source`, and `reason`.

### `lib/db.ts`

- Added an additive migration helper for existing `agent_queue_items` tables.
- Existing local databases now receive missing queue columns without requiring a
  destructive reset:
  - `request_id`
  - `options`
  - `tool_plan`
  - `position`
  - `result_image_ids`
  - `error_code`
  - `error_message`
  - `started_at`
  - `finished_at`

Impact: the queue/planner patch is safe for users who already had Agent Mode
sessions before this lane added planner metadata.

### `routes/agent.ts`

- `/api/agent/sessions/:sessionId/queue` now parses slash commands server-side.
- `/question` and `/help` append a text assistant turn and do not create queue
  work.
- `/variants`, `/generate`, and `/parallelism` clean the executable prompt and
  create planner-backed queue work.
- Client-submitted `plan` bodies are ignored. The server always recomputes the
  executable plan from prompt, slash command, and normalized server options.

This keeps slash commands authoritative on the server instead of making them a
frontend-only convention, and prevents bypassing provider/quality/concurrency
caps through forged request JSON.

### `lib/agentRuntime.ts`

- Runtime now uses `plan.plannedParallelism` for `mapWithLimit`.
- Inflight metadata now reports `plannedVariants`, `plannedParallelism`, and
  `requestedVariants` from the normalized plan instead of raw settings.
- Tool output summaries include the planner reason.
- Assistant turns now include a text response describing image count, fanout
  concurrency, and planning reason.
- `question` mode is guarded inside runtime as well as routes. If a text-only
  plan reaches runtime, it appends an assistant text turn and performs no image
  work.

### `lib/responsesImageAdapter.ts`

- Responses SSE parsing now preserves text deltas and completed output text.
- Responses JSON parsing now preserves message/output text alongside image
  artifacts.
- Runtime prepends model-authored text when available, then appends deterministic
  execution metadata.

This means image turns can carry both model prose and concrete execution
observability instead of discarding text once an image artifact is found.

## Frontend Changes

### Agent Settings

- `AgentGenerationSettings` and defaults now include:
  - `generationStrategy`
  - `maxAutoVariants`
- `AgentQualityPanel` exposes:
  - `Based on user request`
  - `Fixed count`
  - auto max or fixed variants
  - parallelism cap

### Sidebar

The right sidebar tabs are now explicit:

```text
image | library | forms | quality | model | queue
```

`model` opens model/provider/reasoning controls. `quality` opens quality,
format, moderation, strategy, count cap, and layout preference controls.

### Composer

Typing `/` shows compact slash command chips:

- `/question`
- `/variants 3`
- `/generate 4`
- `/parallelism 2`

The chips are hints only; the server parser remains the source of truth.

### Queue

Queue rows now show the actual execution plan:

```text
<status> · <queue status> · <variants>v/<parallelism>p · <source> · <time>
<planner reason>
```

This addresses the previous concern that UI settings and queue execution could
drift.

## Verification Added

New tests:

- `tests/agent-mode-auto-planner-contract.test.ts`
- `tests/agent-mode-slash-command-contract.test.ts`
- `tests/agent-mode-queue-migration-contract.test.ts`

Updated tests:

- `tests/agent-mode-parallel-contract.test.ts`
- `tests/agent-mode-runtime-contract.test.ts`
- `tests/agent-mode-right-sidebar-contract.test.js`
- `tests/agent-mode-layout-contract.test.js`

Focused verification passed:

```text
npm run typecheck
npm run typecheck:tests
cd ui && npx tsc --noEmit
node --import tsx --test tests/agent-mode-auto-planner-contract.test.ts tests/agent-mode-queue-migration-contract.test.ts tests/agent-mode-slash-command-contract.test.ts tests/agent-mode-runtime-contract.test.ts tests/agent-mode-parallel-contract.test.ts tests/agent-mode-queue-contract.test.ts tests/agent-mode-right-sidebar-contract.test.js tests/agent-mode-layout-contract.test.js tests/agent-mode-frontend-contract.test.js
```

Focused result:

```text
26 tests pass / 0 fail
```

Full local gate passed after the focused run:

```text
npm run ui:build
npm run build:server
npm test
```

Full result:

```text
npm test: 756 tests pass / 0 fail
git diff --check: pass
ui:build: pass
build:server: pass
```

## Ryo Concern Closure Notes

Ryo's first implementation review returned `CONCERNS`. The blocking items were
patched in this pass:

1. Legacy queue tables now receive additive planner-column migrations.
2. Queue routes ignore client-submitted plan bodies and recompute plans
   server-side.
3. Responses text is preserved from SSE and JSON outputs and displayed in the
   assistant turn.
4. Runtime has a defense-in-depth text-only/question path.
5. Inflight metadata now reflects the normalized execution plan.
6. Slash fanout edge cases are explicit:
   - `/variants` with no count defaults to three variants;
   - counts above the planner cap are capped at eight;
   - `/generate` and `/parallelism` clean command syntax before execution.

## Closeout Gate Result

The remaining blockers were closed in follow-up patches:

1. Backend/runtime concerns were patched with additive DB migrations,
   server-side plan recomputation, text extraction, question-mode guards, and
   normalized inflight metadata.
2. UI concerns were patched with the mobile model settings sheet and a corrected
   four-column mobile topbar contract.
3. Documentation concerns were patched so the test matrix matches the concrete
   implementation and final field names.

Final verification:

```text
npm run typecheck: pass
npm run typecheck:tests: pass
cd ui && npx tsc --noEmit: pass
npm run build:server: pass
npm run ui:build: pass
npm test: 756 tests pass / 0 fail
git diff --check: pass
read-only docs re-review: PASS
read-only UI re-review: PASS
Chrome/Computer Use QA: PASS for visible desktop Agent layout, right sidebar
tabs, model chip, queue tab, nested tool folding, and slash command hints
```
