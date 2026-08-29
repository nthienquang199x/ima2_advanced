---
created: 2026-05-17
status: implementation-patched
tags: [phase-1, schema, settings, queue]
depends_on:
  - 00_overview.md
  - 01_current_state_and_product_intent.md
---

# Phase 1 — Generation Strategy Schema

## Goal

Separate **policy** from **actual execution**.

Today:

```text
variants = exact count
parallelism = exact count
```

Target:

```text
auto mode:
  maxAutoVariants = count cap
  parallelism = requested concurrency cap
  planner chooses actual count for each run

manual mode:
  variants = exact count
  parallelism = exact requested cap
```

## Backend Type Direction

Extend `AgentGenerationSettings` with policy fields:

```ts
export interface AgentGenerationSettings {
  provider: "oauth" | "api";
  model: string;
  quality: "low" | "medium" | "high";
  size: string;
  format: "png" | "jpeg" | "webp";
  moderation: "auto" | "low";
  reasoningEffort: "low" | "medium" | "high" | "xhigh";
  webSearchEnabled: boolean;

  generationStrategy: "auto" | "manual";
  variants: number;
  parallelism: number;
  maxAutoVariants: number;
}
```

Compatibility:

- keep `variants` and `parallelism` so existing manual mode and old queue rows
  still load;
- default `generationStrategy` to `"auto"` only after UI copy clearly explains
  the behavior;
- default `maxAutoVariants` to `8`;
- keep `parallelism` as the user-visible requested concurrency cap;
- keep text-only behavior explicit through `/question` and runtime question-mode
  guards instead of a broad `allowTextOnly` settings flag.

## Generation Plan Shape

Extend `AgentGenerationPlan`:

```ts
export interface AgentGenerationPlan {
  mode: "single" | "fanout" | "question";
  prompts: string[];
  requestedVariants: number;
  plannedVariants: number;
  plannedParallelism: number;
  source: "auto-default" | "auto-request" | "manual-settings" | "slash-command" | "question-command";
  reason: string;
}
```

Optional fields are acceptable for backward compatibility while loading
existing rows.

## Queue Item Snapshot

Each queue item should preserve both:

- settings snapshot: what policy/caps were active;
- planned execution: what the Agent chose for this run.

Recommended JSON in `agent_queue_items.tool_plan`:

```json
{
  "mode": "fanout",
  "plannedVariants": 3,
  "plannedParallelism": 2,
  "source": "auto-request",
  "reason": "User asked for three options.",
  "prompts": ["...", "...", "..."]
}
```

## UI Copy Direction

English:

- `Generation strategy`
- `Auto`
- `Manual`
- `Based on user request`
- `Max variants`
- `Max parallel`
- `Defaults to 1 image. The agent may create more when you ask for options.`

Korean:

- `생성 전략`
- `자동`
- `수동`
- `요청에 따라`
- `최대 변형 수`
- `최대 병렬 수`
- `기본은 1장입니다. 여러 시안이나 후보를 요청하면 에이전트가 더 생성합니다.`

## Acceptance

- Existing sessions load with default strategy fields.
- Existing queue rows without new plan fields still render.
- Manual mode preserves the exact current `variants`/`parallelism` behavior.
- Auto mode stores caps, not exact values.
- Queue items store actual planned values.
