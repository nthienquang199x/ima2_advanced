---
created: 2026-05-17
status: implementation-patched
tags: [phase-5, queue, tool-observability, model-chip]
depends_on:
  - 05_phase4_slash_commands_and_composer_ui.md
---

# Phase 5 — Queue Tool Observability

## Goal

If the Agent decides execution automatically, the UI must show the decision.

Without this, users will see unexpected extra images and assume the app ignored
their settings.

## Queue Row

Queue rows should distinguish:

```text
Manual · 2 variants · 1 parallel
Agent planned · 3 variants · 2 parallel
Command override · 4 variants · capped to 2 parallel
Question pending
```

Recommended row fields:

- prompt summary;
- plan source;
- planned variants;
- planned parallelism;
- cap/clamp note;
- running progress such as `1/3 complete`;
- failed/partial count.

Do not put long planning reasons in the compact row. Use a details area or tool
detail.

## Tool Timeline

V1 records the plan on queue rows, inflight metadata, assistant text, and
existing tool summaries instead of adding a separate planning tool call.

```text
ima2.web_search + ima2.generate_image
```

Example detail:

```json
{
  "source": "auto-request",
  "plannedVariants": 3,
  "plannedParallelism": 2,
  "reason": "User asked for three options."
}
```

Then generation tool details can show:

```text
ima2.generate_image #1
ima2.generate_image #2
ima2.generate_image #3
```

This keeps the cli-jaw-style nested tool folding model intact.

## Assistant Text

Text should be visible outside collapsed tool details:

```text
I planned three variants because you asked for options. I kept parallelism at 2
because this is high quality.
```

After completion:

```text
Generated 3 options. Option 2 is the closest match to your reference.
```

## Model Chip

Chip should show policy at rest and actual plan while running:

- idle auto: `auto <=4x/2p`;
- running planned: `planned 3x/2p`;
- manual: `manual 2x/1p`;
- question state: `question pending`.

## Session Spinner

Session row/rail spinner should reflect plan state:

- queued fanout: queued indicator with count;
- running fanout: spinner plus progress;
- question pending: non-spinner waiting marker;
- failed partial: error marker and count.

## Acceptance

- User can tell whether extra images came from auto planning or a command.
- User can see when requested parallelism was capped.
- Tool details explain the plan without crowding the chat.
- Text response and image artifacts are both visible.
- Queue state remains useful after reload.
