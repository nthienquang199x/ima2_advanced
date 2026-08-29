---
created: 2026-05-17
status: implementation-patched
tags: [ima2-gen, agent-mode, auto-generation, slash-commands, text-response, jawdev]
depends_on:
  - ../260516_agent-mode-followup-jawdev/00_overview.md
  - ../260517_agent-ui-polish-jawdev/00_overview.md
---

# Agent Mode Auto Generation Jawdev Plan

## Status Note

This overview started as the lane proposal. It is now kept as the high-level
map for the implementation-patched lane.

Final source of truth:

- `08_implementation_patch_log.md` for implemented modules, UI surfaces,
  verification, and closeout evidence;
- `07_tests_verification_risks_acceptance.md` for the concrete test matrix;
- `90_employee_discussion_log.md` for staff review history and concern closure.

## Why This Exists

At lane start, Agent Mode worked as a queue-backed image workflow, but it was
still mostly **settings-driven**:

```text
user prompt
-> session/UI generation settings snapshot
-> queue item options
-> fanout by variants
-> mapWithLimit by parallelism
-> image artifacts
```

Jun's newer requirement was more agentic:

```text
user prompt
-> Agent understands the request
-> Agent decides whether to ask, answer, generate one image, or fan out
-> Agent preserves text response and execution reason
-> queue/tool UI shows what was planned and why
```

The difference matters. `variants` and `parallelism` should not just be raw
numeric knobs. They should become an execution policy:

- default to one image when the user asks for one thing;
- create several variants when the user explicitly asks for options,
  candidates, versions, or a specific count;
- cap parallelism by user/session limits, provider stability, quality, and
  runtime safety;
- allow manual override when the user wants exact control;
- allow `/question` when the Agent should ask before spending image calls;
- preserve text responses alongside generated image artifacts.

## User Intent Captured At Lane Start

Jun's 2026-05-17 request can be restated as:

1. The then-current implementation was effectively prompt/settings delivery,
   not autonomous Agent planning.
2. Image results should come with text responses, not only generic
   `Generated an image artifact.` copy.
3. UI defaults should be phrased in English as an agent policy such as
   `Based on user request`, not as if users must always set a fixed count.
4. The prompt policy can remain "one image by default"; when the user asks for
   multiple images, the Agent should call the image tool multiple times or build
   a fanout plan.
5. Numeric controls should still exist as caps or manual overrides.
6. The Agent should be able to ask follow-up questions through `/question`.
7. Slash commands should exist for explicit control, such as `/question`,
   `/variants`, `/generate`, and `/parallelism`.
8. This should be recorded as a Jawdev implementation lane after staff
   discussion.

## Implemented V1 Summary

The patched v1 implements the deterministic first slice:

- `generationStrategy: "auto"` defaults to one image and infers bounded fanout
  only when the user asks for multiple options or a count.
- `generationStrategy: "manual"` preserves exact fixed-count control.
- `/question`, `/help`, `/variants`, `/generate`, and `/parallelism` are parsed
  server-side.
- Queue execution stores normalized plans with planned variants/parallelism,
  source, and reason.
- Responses text is preserved before deterministic image artifact copy.
- Normal generation still requires an image artifact; text-only success is
  reserved for explicit `mode: "question"`.
- Right sidebar quality/model/queue/forms/library surfaces, mobile model sheet,
  model chip, nested tool folding, queue rows, and session spinners expose the
  plan and runtime state.

## Scope Boundary

This is not a replacement for the already-created Agent Mode follow-up lane.

- `../260516_agent-mode-followup-jawdev/` covers layout, queue, nested tool
  folding, right sidebar controls, parallel runtime, and spinners.
- `../260517_agent-ui-polish-jawdev/` covers visual polish, crash triage,
  breakpoint mismatch, tab separation, and settings polish.
- This lane covers **agent execution policy**: auto planning, text responses,
  slash commands, question flow, and observability of planned execution.

## Architecture Direction

The implementation followed the deterministic-first direction:

```text
Phase 1: generation strategy schema
Phase 2: deterministic auto planner
Phase 3: text response capture
Phase 4: question/follow-up flow
Phase 5: slash command parser and UI
Phase 6: queue/tool/model observability
Phase 7: tests, QA, and caps
Optional: LLM planner after deterministic data proves gaps
```

Do not start with an LLM planner. Staff review agreed deterministic heuristics
should come first because they are cheap, stable in CI, and easy to reason
about. A later LLM planner can be added as a hybrid fallback after the system
has logs showing where deterministic planning fails.

## Plan Documents

- `01_current_state_and_product_intent.md`
- `02_phase1_generation_strategy_schema.md`
- `03_phase2_auto_generation_planner.md`
- `04_phase3_text_response_and_question_flow.md`
- `05_phase4_slash_commands_and_composer_ui.md`
- `06_phase5_queue_tool_observability.md`
- `07_tests_verification_risks_acceptance.md`
- `08_implementation_patch_log.md`
- `90_employee_discussion_log.md`
