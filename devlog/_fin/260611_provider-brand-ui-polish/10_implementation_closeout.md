---
created: 2026-06-11
updated: 2026-06-11
status: completed
tags: [ima2-gen, frontend, provider-ui, brand-polish, closeout]
---

# Implementation Closeout

## Commit Scope

Implementation was split into small commits:

- `fb5dcf3 feat(ui): add provider identity metadata`
- `71f8121 feat(ui): polish provider selector cards`
- `7279760 refactor(ui): unify provider control copy`
- `34d5bdd feat(ui): align agent provider selection`

Final documentation/test-inventory commit is expected after this closeout file.

## Implementation Evidence

Provider identity source of truth:

- `ui/src/lib/providerIdentity.ts`
- `tests/provider-identity-contract.test.js`

Provider selector and CSS ownership:

- `ui/src/components/ProviderSelect.tsx`
- `ui/src/components/provider/ProviderCard.tsx`
- `ui/src/components/provider/ProviderStatusBadge.tsx`
- `ui/src/styles/provider-controls.css`
- `ui/src/styles/toast-modal.css`
- `ui/src/index.css`
- `tests/provider-ui-polish-contract.test.js`

Generation/settings copy cleanup:

- `ui/src/components/GenerationControlsPanel.tsx`
- `ui/src/components/SettingsWorkspace.tsx`
- `ui/src/i18n/en.json`
- `ui/src/i18n/ko.json`

Agent provider parity:

- `ui/src/components/agent/AgentModelSelector.tsx`
- `ui/src/styles/agent-workspace-sidebar.css`
- `tests/agent-mode-right-sidebar-contract.test.js`

Inventory update:

- `docs/migration/runtime-test-inventory.md`

## Verification Evidence

Commands run:

```bash
node --test tests/provider-identity-contract.test.js
node --test tests/provider-ui-polish-contract.test.js tests/agent-mode-right-sidebar-contract.test.js
npm run typecheck
npm run typecheck:tests
node scripts/classify-tests.mjs
npm run test:inventory
npm test
npm run ui:build
```

Results:

- `typecheck`: pass.
- `typecheck:tests`: pass.
- `test:inventory`: pass after regenerating the runtime inventory.
- First `npm test`: 1001/1002 pass; `tests/server-fallback-contract.test.js` failed once on a port fallback race (`actual` and `expected` both 4729).
- Targeted rerun of `tests/server-fallback-contract.test.js`: pass.
- Second full `npm test`: 1002/1002 pass.
- `ui:build`: pass. Vite still reports the existing large chunk warning for the main bundle.

## Visual QA Evidence

Local server:

- Started with `node bin/ima2.js serve --port 3467`.
- Runtime fell back to `http://127.0.0.1:3468` because requested ports were occupied.

Browser/CDP checks:

- Desktop viewport: provider cards render in the right settings panel as compact GPT/Grok/Gemini rows with selected/unavailable states visible. Screenshot: `/Users/jun/.cli-jaw-3460/screenshots/screenshot_1781109276426.png`.
- Mobile viewport 390x844: generation controls sheet shows provider cards in a stable two-column layout with no visible clipping/overlap. Screenshot: `/Users/jun/.cli-jaw-3460/screenshots/screenshot_1781109304635.png`.
- Agent mode visual check was not available in this runtime because `ENABLE_AGENT_MODE` is feature-gated off. Agent provider parity is covered by TypeScript and contract tests.

## Design Closeout

The implemented direction follows the original plan:

- Provider identity is display metadata only; generation routing did not change.
- GPT remains restrained/monochrome.
- Grok uses compact monochrome treatment without recreated official marks.
- Gemini uses a small gradient mark only; no gradient buttons or background decoration.
- Provider CSS is no longer owned by toast/modal CSS.
- Agent mode no longer uses a native provider `<select>` for provider selection.

## Follow-Up Candidates

- Add an enabled Agent-mode screenshot pass when the feature gate is on.
- Consider a future provider readiness popup polish pass using the same card primitive.
- Decide product naming for `agy`: current UI labels it as `Gemini CLI` with `Antigravity` detail.
