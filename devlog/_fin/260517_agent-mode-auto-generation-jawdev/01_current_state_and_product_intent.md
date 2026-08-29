---
created: 2026-05-17
status: implementation-patched
tags: [current-state, product-intent, agent-mode]
depends_on:
  - 00_overview.md
---

# Current State And Product Intent

## Scope Note

This file records the baseline that triggered the lane. The implementation was
patched after this analysis; use `08_implementation_patch_log.md` and
`07_tests_verification_risks_acceptance.md` as the final source of truth for
exact field names, slash commands, and verification status.

## Baseline Runtime Truth

At lane start, the implementation was not yet an autonomous planner.

### Baseline Defaults Were Fixed Settings

Server defaults:

```ts
// lib/agentSettings.ts
variants: 1,
parallelism: 2,
```

UI defaults:

```ts
// ui/src/lib/agentGenerationSettings.ts
variants: 1,
parallelism: 2,
```

These were static values. They did not inspect the user prompt.

### Queue Submission Carries Prompt Plus Options

The frontend sends the selected session settings to the queue endpoint:

```text
enqueueAgentTurn(sessionId, text, selectedSettings)
```

The API body is effectively:

```json
{
  "prompt": "user text",
  "options": {
    "model": "gpt-5.4-mini",
    "quality": "medium",
    "variants": 1,
    "parallelism": 2
  }
}
```

At lane start, `routes/agent.ts` merged request options with the current session
generation settings. It did not infer variants from text like "make three
options".

### Fanout Is Numeric, Not Semantic

`lib/agentQueueStore.ts` normalizes a plan as:

```text
if explicit plan.prompts exists:
  use those prompts
else:
  create N prompts from options.variants
```

When `variants > 1`, the fallback prompt is the original prompt plus a generic
English suffix like:

```text
Variant 2/3: explore a distinct composition while preserving the request.
```

This gave bounded fanout, but it did not mean the Agent had reasoned about the
user's intent.

### Parallelism Is A Concurrency Cap

`lib/agentRuntime.ts` runs planned prompts through `mapWithLimit` using
`options.parallelism`.

This is a runtime concurrency limit. It should stay bounded by:

- requested variant count;
- user/session max parallelism;
- provider caps;
- quality/reference complexity;
- global queue worker limits.

## Current Text Response Limitation

At lane start, successful assistant turns used generic fixed text:

```text
Generated an image artifact.
Generated N image artifacts.
```

Text-only model output was treated as failure by the image-generation path. That
remains correct for normal generation requests, but `/question` now has an
explicit question plan that returns text without spending image calls.

## Patched Runtime Truth

The implementation now has a deterministic planner and explicit execution plan
metadata:

- `generationStrategy: "auto"` lets the planner infer bounded variants from the
  request while defaulting to one image when the prompt does not ask for more.
- `generationStrategy: "manual"` keeps exact fixed-count user control.
- `/variants`, `/generate`, and `/parallelism` are parsed server-side and stored
  as queue execution plans.
- `/question` returns a text assistant turn without queueing image generation.
- Responses model text is preserved before deterministic image artifact copy
  when an image is produced.
- Queue rows, inflight state, tool rows, and the model chip expose planned
  variants/parallelism rather than raw untrusted client values.

## Product Intent

Agent Mode should feel like a real assistant:

- It can decide whether the user asked for one image or multiple options.
- It can explain what it is about to generate.
- It can ask a clarification question before spending image calls.
- It can preserve text alongside generated images.
- It can expose the plan in the queue/tool UI so the user understands what
  happened.
- It still gives the user numeric controls for caps and exact manual override.

## Key Principle

Use this mental model:

```text
Settings panel = default policy and max caps
Slash command = one-run override
Planner = actual decision for this run
Queue row = actual planned values
Tool detail = execution evidence
Assistant text = human-readable explanation
```
