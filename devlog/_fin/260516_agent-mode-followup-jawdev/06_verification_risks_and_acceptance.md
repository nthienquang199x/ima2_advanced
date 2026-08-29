---
created: 2026-05-16
status: plan
tags: [verification, qa, risk, acceptance]
depends_on:
  - 05_pabcd_implementation_plan.md
---

# Verification, Risks, And Acceptance

## Required Verification Commands

Run after implementation:

```bash
node --test tests/agent-mode-layout-contract.test.js
node --test tests/agent-mode-tool-folding-contract.test.js
node --import tsx --test tests/agent-mode-queue-contract.test.ts
node --import tsx --test tests/agent-mode-parallel-contract.test.ts
node --test tests/agent-mode-right-sidebar-contract.test.js
node --test tests/agent-mode-frontend-contract.test.js
node --import tsx --test tests/agent-mode-runtime-contract.test.ts
npm run typecheck
npm run typecheck:tests
cd ui && npx tsc -b --noEmit
cd ui && npm run build
npm test
git diff --check
```

Run browser verification with the local app:

```bash
npx @damagethundercat/ima2-gen serve --dev
```

Open the advertised URL from `~/.ima2/server.json` or terminal output. Do not
assume port `3333`.

## Browser QA Matrix

Desktop:

- `1440x900`: full sessions + chat + right sidebar.
- `1280x800`: full horizontal layout remains stable.
- `1180x760`: rail or pinned sessions, but not vertical broken stacking.

Laptop/small:

- `976x772` at Chrome 90% zoom: should match the observed environment and show
  a deliberate desktop-rail or pinned layout, not accidental mobile.
- `900x520`: mobile image sheet is acceptable due short height.

Tablet/mobile:

- `820x760`: tablet stacked.
- `390x844`: mobile chat with image sheet.

## Acceptance Criteria By User Requirement

| Req | Acceptance |
|---:|---|
| 1 | Desktop/laptop Agent workspace keeps intentional horizontal regions. Pane preference can pin full sessions or rail. |
| 2 | Tool rows have outer group folding and inner per-tool details, with image thumbs outside expand buttons. |
| 3 | User can enqueue multiple prompts, see queue rows, cancel queued work, retry failed work, and reload without losing state. |
| 4 | One prompt can produce multiple image jobs with bounded parallelism and all resulting image handles appear in chat/right variants. |
| 5 | Right sidebar includes image context, prompt library, form/templates, quality controls, model/settings, and queue inspector. |
| 6 | Top-right model/settings control is synced to the sidebar and snapshots settings into queued items. |
| 7 | Each session row/rail item shows its own running spinner, queued count, and error state. |

## Regression Checks

Existing behavior that must remain:

- Agent Mode remains visible by default unless `VITE_IMA2_AGENT_MODE=0`.
- Image handles, not base64, are stored in turns.
- Image focus sync across chat thumbs, right variants, and mobile sheet remains.
- `ima2.get_image_context`, `ima2.web_search`, and `ima2.generate_image` remain
  the only allowed tools.
- Web-search toggle still affects whether `web_search` is used.
- Text-only image results still fail and retry once.
- Cross-session image focus is still rejected.
- Current image manifest still survives compact/resume.

## Main Risks

### Risk 1: Queue Worker Lifetime

If the worker starts every time routes are registered, tests or dev HMR may run
duplicate workers.

Mitigation:

- expose `ensureAgentQueueWorker(ctx)` with idempotent module-level guard;
- allow tests to call worker functions directly without starting timers;
- make worker tick deterministic in contract tests.

### Risk 2: UI Payload Size

Adding queue, tool calls, contexts, prompt library, and settings to one
workspace payload can get heavy.

Mitigation:

- initial payload includes queue summaries and recent queue items only;
- full tool details can be in `raw` but projected compactly;
- long prompt-library searches stay behind existing library endpoints.

### Risk 3: Parallel Generation Cost/Quota

Fanout can burn quota quickly.

Mitigation:

- visible variants count;
- hard cap 8;
- default parallelism 2;
- queue row shows number of planned generations before running;
- cancellation is available before start.

### Risk 4: Prompt Library Coupling

Existing prompt-library UI may assume Classic mode state.

Mitigation:

- create `AgentPromptLibraryPanel` adapter;
- reuse storage/search APIs;
- do not import Classic-only composer actions directly;
- insert into Agent composer through an Agent-specific callback.

### Risk 5: File Size Creep

Agent files are already approaching broad responsibility.

Mitigation:

- extract layout shell, queue panel, right sidebar, and tool group components;
- keep `AgentWorkspace.tsx` as orchestration only;
- split backend runtime into focused flat `lib/agent*.ts` helper modules;
- split routes if `routes/agent.ts` approaches 500 lines.

## Stop Conditions

Stop and re-plan if:

- queue requires changing global generation APIs in a way that breaks Classic
  or Node mode;
- prompt library cannot be reused without large Classic coupling;
- parallel generation needs model behavior that cannot be made deterministic;
- route or runtime files exceed the 500-line limit after extraction attempts;
- tests require deleting existing Agent contract assertions rather than
  evolving them.

## Done Definition

This lane can move to `_fin` only when:

- all seven user requirements are implemented;
- contract tests cover layout, tool folding, queue, parallel fanout, sidebar,
  settings sync, and session spinners;
- desktop/laptop/mobile browser QA screenshots or notes are recorded;
- `npm test`, backend typecheck, UI typecheck, UI build, and `git diff --check`
  pass;
- `devlog/_plan/README.md` and `structure/07-devlog-map.md` are updated with
  closeout evidence.
