---
created: 2026-05-17
status: implementation-patched
tags: [phase-2, planner, variants, parallelism, fanout]
depends_on:
  - 02_phase1_generation_strategy_schema.md
---

# Phase 2 — Auto Generation Planner

## Goal

Implement a deterministic planner before adding any LLM planner.

The planner should answer:

```text
Should this request generate one image, several variants, or ask first?
How many prompts should be created?
What is the effective parallelism cap?
Why was this decision made?
```

## New Module

Add a pure planner module:

```text
lib/agentGenerationPlanner.ts
```

Implemented signature:

```ts
type PlanningInput = {
  prompt: string;
  settings: AgentGenerationSettings;
  command?: AgentSlashCommand | null;
};

export function deriveAgentGenerationPlan({
  prompt,
  settings,
  command = null,
}: PlanningInput): AgentGenerationPlan;
```

Keep it pure and deterministic for testability.

## Deterministic Heuristics

Start with explicit and cheap rules:

| Signal | Planned variants |
|---|---:|
| `/variants N` | `N` clamped to max |
| "1", "one", "한 장", "하나만", "딱 하나" | 1 |
| "2", "two", "두 개", "둘" | 2 |
| "3", "three", "세 개", "셋" | 3 |
| "4", "four", "네 개", "넷" | 4 |
| "options", "candidates", "variants", "versions" | 3 |
| "여러", "시안", "후보", "버전", "다양" | 3 |
| "A/B", "compare", "비교" | 2 |
| no count/multiple signal | 1 |

This keeps the current default behavior: one image unless the user asks for
more.

## Prompt Fanout

The first version may keep simple fanout prompts:

```text
Variant 1/3: clean/default interpretation
Variant 2/3: alternate composition
Variant 3/3: distinct style or framing
```

But this should be improved from the current generic suffix. The planner should
generate structured prompt variants based on the detected reason:

- options/candidates: different compositions;
- style exploration: different visual styles;
- A/B comparison: controlled pairs;
- exact count: numbered alternatives that preserve the core request.

## Effective Parallelism

Parallelism is not purely creative. It is a runtime safety cap.

Recommended calculation:

```ts
effectiveParallelism = min(
  plannedVariants,
  settings.parallelism,
  providerCap,
  qualityCap,
  workerCap
)
```

Initial caps:

| Condition | Cap |
|---|---:|
| `quality === "high"` | 2 |
| `provider === "oauth"` | 2 |
| reference/image edit present | 2 |
| `provider === "api"` and medium/low | 4 |
| global hard cap | 8 |

## Planner Source

Each decision should record source:

- `auto-default`
- `auto-request`
- `manual-settings`
- `slash-command`
- `question-command`

This source must be visible in queue/tool details.

Future LLM planning should add a new source only after deterministic telemetry
shows repeated gaps.

## Why Not LLM First

Staff review agreed deterministic first is safer:

- zero cost per prompt;
- stable CI;
- easy contract tests;
- no hidden planner latency;
- clear fallback when LLM planner is added later.

LLM planner can be Phase 5+ only after deterministic logs show repeated
failure cases.

## Acceptance

- `generate one logo` -> single prompt.
- `make three options` -> three prompts.
- `여러 시안 만들어줘` -> at least three prompts.
- `/variants 4 ...` -> four prompts, source `slash-command`.
- high-quality OAuth request never exceeds parallelism 2.
- queue plan stores reason and actual planned values.
