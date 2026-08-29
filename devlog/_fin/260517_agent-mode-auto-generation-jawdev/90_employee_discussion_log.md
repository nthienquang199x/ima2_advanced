---
created: 2026-05-17
status: implementation-patched
tags: [employee-review, discussion-log, jawdev]
depends_on:
  - 00_overview.md
---

# Employee Discussion Log

## Context

Jun asked whether Agent Mode should decide `variants` and `parallelism` by
itself. The discussion expanded into an implementation lane covering:

- auto variants and parallelism;
- text responses with images;
- `/question` clarification;
- slash commands;
- manual numeric override;
- queue/tool/model chip observability.

## Backend Review — 료

### Planning Review

Verdict: `CONCERNS`

Key points:

- Current implementation is prompt plus settings snapshot, not autonomous
  planning.
- `variants` and `parallelism` are static settings clamped to 1-8.
- Fanout currently duplicates the prompt with a generic variant suffix.
- Assistant text is currently generic and text-only output is treated as
  failure by runtime contracts.
- `/question` conflicts with the current "image required" invariant and needs
  explicit question/text mode.
- Deterministic planner should come before LLM planner.
- Slash commands should parse server-side and apply to both queue and sync turn
  paths.
- Runtime must cap parallelism by provider, quality, references, and worker
  limits.

Recommended backend modules:

- `lib/agentGenerationPlanner.ts`
- `lib/agentCommandParser.ts`

Recommended tests:

- auto planner contract;
- slash command contract;
- text response contract;
- updates to queue/runtime parallel contracts.

### Implementation Review 1

Verdict: `CONCERNS`

Key blockers raised:

- Existing `agent_queue_items` tables could miss new queue planner columns such
  as `tool_plan`, breaking users with pre-existing Agent Mode databases.
- The queue route accepted a client-submitted `plan` body, allowing request JSON
  to bypass provider, quality, and concurrency caps.
- `assistantText` existed in the type surface but actual Responses model text was
  not preserved from SSE/JSON output.
- `question` mode needed a runtime guard, not only a route-level bypass.
- Inflight metadata still reported raw option values instead of the normalized
  execution plan.

Patch response:

- Added additive DB migration coverage for legacy queue tables.
- Removed client plan forwarding from queue route execution.
- Added Responses SSE/JSON text extraction and runtime assistant text merging.
- Added runtime defense-in-depth for text-only/question plans.
- Changed inflight metadata to report planned variants/parallelism.
- Added focused contracts for server-side plan recomputation and queue migration.

## Frontend Review — 니지카

Initial attempt:

- stopped due to a fragile helper `sed` pipeline failure;
- no UI conclusion from that attempt.

Retried scoped UI review:

Verdict: `CONCERNS`

Key points:

- `AgentComposer` is the right insertion point for slash command palette.
- `AgentGenerationSettingsPanel` is the right place for Auto/Manual strategy.
- Settings panel should show policy/caps; queue row should show actual planned
  values.
- Model chip must stay short, such as `auto <=4x/2p` or `manual 2x/1p`.
- Slash command discoverability should use `/` at the composer, not a heavy
  modal.
- Text response should be visible as an assistant bubble and not buried inside
  tool details.
- `/question` should show a clear question state and change composer
  placeholder.
- Queue rows should show `Agent planned`, `Command override`, or `Question
  pending`.

Recommended UI copy:

- EN: `Based on user request`, `Max variants`, `Max parallel`,
  `Describe an image, or type / for commands`.
- KO: `요청에 따라`, `최대 변형 수`, `최대 병렬 수`,
  `이미지를 설명하거나 / 로 명령을 선택하세요`.

## Documentation Review — 세이카

Verdict: `PASS / CONCERNS`

Key points:

- Create a new active lane only if this is intended for implementation soon.
- Use `_future` if it is merely deferred ideation.
- Recommended active folder:
  `devlog/_plan/260517_agent-mode-auto-generation-jawdev/`.
- Update both `devlog/_plan/README.md` and `structure/07-devlog-map.md`.
- Keep numbered Jawdev filenames, not bare `PLAN.md`.
- Include a discussion log file because user explicitly requested employee
  discussion to be recorded.

## Boss Decision

This is recorded as an active `_plan` lane because Jun asked to "차후 구현
플랜으로 올리고 devlog에 작성" after employee discussion, then asked to continue
patching until concerns were closed.

Current decision:

- The lane is no longer plan-only.
- Backend/runtime implementation is patched and covered by focused contracts.
- UI implementation is patched and covered by layout/sidebar/tool-folding
  contracts plus headed Chrome/Computer Use QA.
- The implementation log, not the early planning sections, is the source of
  truth for exact final field names and command support.
