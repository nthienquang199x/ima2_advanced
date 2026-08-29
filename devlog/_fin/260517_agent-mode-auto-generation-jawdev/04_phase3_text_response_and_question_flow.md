---
created: 2026-05-17
status: implementation-patched
tags: [phase-3, text-response, question-flow, slash-question]
depends_on:
  - 03_phase2_auto_generation_planner.md
---

# Phase 3 — Text Response And Question Flow

## Goal

Agent Mode should return useful text alongside images.

Implementation note:

- normal image generation still requires an image artifact;
- Responses model text is preserved when an image is produced;
- text-only success is limited to explicit `/question` plans;
- there is no broad `allowTextOnly` settings flag in the final v1.

Current assistant text is generic:

```text
Generated an image artifact.
Generated N image artifacts.
```

Target:

```text
I made three directions: clean product shot, editorial crop, and close-up detail.
Option 2 best matches the reference because it preserves the pose.
```

Also support `/question` and planner-driven clarification:

```text
Before I generate, should the variants explore style, composition, or subject?
```

## Text Response Capture

The image adapter/runtime should preserve text output when available.

Runtime behavior:

- if images and text are both present:
  - assistant turn text uses model/planner text;
  - image ids attach to the same assistant turn or adjacent result turn;
  - tool details show image generation calls.
- if images are present but no text:
  - fallback to existing generic text.
- if text-only appears:
  - default remains failure for normal image generation;
  - allow success only in explicit question/text mode.

## Preserve Existing Safety

Existing text-only failure behavior should not be removed globally.

Use explicit plan mode rather than a broad settings flag:

```ts
mode: "question"
```

Then:

- normal image generation with text-only result still fails;
- `/question` returns a question-mode assistant turn for that request;
- text answers can be rendered without pretending an image was generated.

## Question Mode

Extend the generation plan:

```ts
mode: "question"
```

When plan mode is `question`:

1. append the user turn;
2. do not create image generation tool calls;
3. append assistant text asking the question;
4. keep `imageIds` empty so the UI can render it as a text answer.

Status remains the existing turn status:

```ts
AgentTurnStatus = "streaming" | "complete" | "error"
```

## Follow-Up Loop

Keep v1 simple:

- no separate plan-thread entity;
- store the question as an assistant turn;
- next user message is a normal user turn;
- planner sees recent session turns and resumes from the answer.

Add a limit:

```text
maxQuestionTurnsPerRequest = 2
```

Provide an escape:

```text
Generate anyway
```

## UI Behavior

Chat:

- render a question assistant bubble with a clear `Question` status;
- composer placeholder becomes `Answer the agent question...`;
- Korean placeholder: `에이전트 질문에 답하세요...`;
- quick replies can be added later, but are not required for v1.

Queue:

- do not show a running image queue item for a question-only turn;
- if a queue item exists, show `Question pending`, not `Generating`.

Tool detail:

- do not bury natural language in collapsed tool detail;
- assistant text should be visible as a normal message.

## Acceptance

- `/question Which style should I use?` creates a text assistant turn and no
  image generation.
- normal prompt still requires image output unless text-only is explicitly
  routed through `mode: "question"`.
- generated images can include human-readable explanation text.
- question state does not create an infinite loop.
