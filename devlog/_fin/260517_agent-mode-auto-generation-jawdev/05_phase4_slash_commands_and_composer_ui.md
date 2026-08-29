---
created: 2026-05-17
status: implementation-patched
tags: [phase-4, slash-commands, composer, ui]
depends_on:
  - 04_phase3_text_response_and_question_flow.md
---

# Phase 4 — Slash Commands And Composer UI

## Goal

Add explicit command control without making the Agent UI noisy.

Slash commands are one-run overrides unless explicitly saved.

## Backend Parser

Add a pure parser:

```text
lib/agentCommandParser.ts
```

Implemented output shape:

```ts
export interface AgentSlashCommand {
  name: "question" | "help" | "variants" | "generate" | "parallelism";
  rawName: string;
  raw: string;
  prompt: string;
  value?: number;
}
```

Parsing rule:

- only parse when the first non-whitespace token starts with `/`;
- do not parse slashes inside ordinary prompt text;
- return `prompt` as the actual prompt after command removal.

## Initial Commands

| Command | Meaning |
|---|---|
| `/variants N` | Set planned variants for this run. |
| `/generate N` | Generate N variants for this run. |
| `/parallelism N` | Set parallel cap for this run. |
| `/question TEXT` | Ask/record a clarification instead of generating now. |
| `/help` | Show command help without creating queue work. |

Deferred command candidates, not part of the implemented v1 parser:

- `/auto`
- `/manual`
- `/model MODEL`
- `/quality high`

## Application Points

Apply parser to both paths:

- `POST /api/agent/sessions/:sessionId/queue`

The queue path is the authoritative path for slash commands and fanout. The
sync turns path remains a legacy single-turn path and receives normalized
generation metadata, but does not own slash/fanout execution.

## Composer UX

Current composer is a textarea plus buttons. Extend it lightly:

- placeholder:
  - EN: `Describe an image, or type / for commands`
  - KO: `이미지를 설명하거나 / 로 명령을 선택하세요`
- when user types `/` at the beginning of the draft, show command suggestions;
- keyboard:
  - ArrowUp/Down selects;
  - Enter inserts or sends based on state;
  - Tab completes;
  - Escape closes.

Avoid a heavy modal. This should feel like a compact command palette inside the
composer.

## Settings Panel UX

Add `Generation strategy` to the Agent settings panel:

```text
[ Auto ] [ Manual ]

Auto:
  Based on user request
  Max variants: 4
  Max parallel: 2

Manual:
  Variants: 1
  Parallelism: 2
```

Important distinction:

- Auto controls are caps/default policy.
- Manual controls are exact execution preference.
- Slash commands are one-run overrides.

## Model Chip UX

Current chip shows:

```text
gpt-5.4-mini · medium · 1x/2p
```

Target examples:

```text
gpt-5.4-mini · medium · auto <=4x/2p
gpt-5.4-mini · high · manual 2x/1p
gpt-5.4-mini · medium · this run 3x/2p
```

Keep the chip short. Full explanations belong in settings or tool details.

## Acceptance

- Slash command suggestions do not break ordinary prompt typing.
- `/variants 3 a logo` produces one-run planned 3 variants.
- `/parallelism 4 ...` is displayed as requested but runtime caps can clamp it.
- `/question ...` changes composer/chat state without creating image calls.
- Settings and model chip show Auto vs Manual unambiguously.
