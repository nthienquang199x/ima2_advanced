---
created: 2026-05-17
status: implementation-patched
tags: [tests, verification, risks, acceptance]
depends_on:
  - 00_overview.md
---

# Tests Verification Risks Acceptance

## Required Contract Tests

### Planner

New:

```text
tests/agent-mode-auto-planner-contract.test.ts
```

Cases:

- default prompt -> one planned variant;
- `make three options` -> three planned variants;
- `여러 시안 만들어줘` -> multiple planned variants;
- `딱 하나만` -> one planned variant;
- manual strategy preserves exact numbers;
- auto strategy respects `maxAutoVariants`;
- high quality or OAuth caps parallelism;
- planning reason/source are stored.

### Slash Commands

New:

```text
tests/agent-mode-slash-command-contract.test.ts
```

Cases:

- `/variants 3 logo` creates a one-run three-variant plan;
- `/generate 4 logo` creates a one-run four-variant plan;
- `/parallelism 4 ...` applies requested cap, then runtime caps if needed;
- `/question ...` produces a question plan and no image generation;
- slash commands only parse at first token/line;
- forged client-submitted `plan` bodies are ignored and recomputed server-side.

### Text Response

Covered in:

- `tests/agent-mode-runtime-contract.test.ts`
- `tests/agent-mode-slash-command-contract.test.ts`

Cases:

- image + model text response preserves the assistant-authored text before image artifact copy;
- image + no model text falls back to deterministic image artifact copy (`Generated 1 image artifact...`);
- direct runtime text-only/no-image output remains failure by default;
- explicit `/question` mode returns a text assistant turn without queueing or image generation.

Current non-goal:

- no broad text-only success mode for normal generation requests; text-only completion is reserved for explicit question plans.

### Queue/Runtime

Update:

```text
tests/agent-mode-parallel-contract.test.ts
tests/agent-mode-queue-contract.test.ts
tests/agent-mode-runtime-contract.test.ts
```

Cases:

- planned prompt count matches queue item plan;
- `mapWithLimit` receives effective planned parallelism;
- partial success text reports completed count;
- old rows without plan metadata still load.

### Frontend

Update or add:

```text
tests/agent-mode-right-sidebar-contract.test.js
tests/agent-mode-frontend-contract.test.js
```

Cases:

- settings panel exposes Auto/Manual strategy;
- model chip shows strategy/caps;
- composer supports slash command entry points;
- queue row exposes planned values;
- question state has localized copy.

## Chrome QA

Manual visual QA must check:

- desktop three-pane layout with Auto strategy visible;
- model chip text does not overlap at narrow widths;
- `/` command palette keyboard flow;
- `/variants 3` one-run override;
- `/question` question bubble and composer placeholder;
- generated result with assistant text + tool group + thumbnails;
- queue row planned values;
- Korean long labels;
- mobile composer command palette.

## Risks

### Cost Surprise

Auto variants can spend more image calls than the user expected.

Mitigation:

- default to one image;
- only increase count on explicit multi/option signal;
- show plan before/during queue;
- cap max variants;
- add optional confirm for high cost later.

### Parallelism Overload

Parallelism affects provider stability and quota.

Mitigation:

- treat UI value as a cap;
- clamp by provider/quality/reference complexity;
- preserve worker global/session caps.

### Question Loop

An Agent that asks too often feels broken.

Mitigation:

- max 1 or 2 follow-up questions per user request;
- provide `Generate anyway`;
- use `/question` for explicit question-first behavior.

### Test Flakiness

LLM planner would make plan results nondeterministic.

Mitigation:

- deterministic planner first;
- LLM planner optional and behind fallback/cap;
- contract tests lock deterministic outcomes.

### UI Ambiguity

Users can confuse max caps with actual planned count.

Mitigation:

- settings panel says `max`;
- queue row says `planned`;
- tool detail says `reason`.

## Acceptance Summary

The implementation-patched lane is acceptable when:

- schema fields match `lib/agentTypes.ts`;
- deterministic planner contracts pass;
- `/question` behavior is route- and runtime-guarded;
- text-only safety is preserved by default;
- slash command one-run override semantics are covered by tests;
- queue/tool UI shows actual plan and reason;
- headed Chrome/Computer Use QA confirms the visible Agent layout.
