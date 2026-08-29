---
created: 2026-06-11
updated: 2026-06-11
status: verification-plan
tags: [frontend, provider-ui, verification]
---

# Verification Plan

## Static Checks

Run after each implementation slice:

```bash
npm run typecheck
npm run typecheck:tests
git diff --check
```

## Targeted Tests To Add Or Update

Recommended contract tests:

- Provider identity map covers all `Provider` values.
- `ProviderSelect` preserves selection behavior for ready providers.
- Unavailable provider card still opens the disabled modal with the correct reason.
- Gemini API display copy comes from i18n keys, not inline English.
- Agent provider selector preserves model/provider coercion behavior.

Likely test files:

- `tests/provider-select-contract.test.js`
- `tests/provider-identity-contract.test.js`
- existing agent generation settings tests if present

## Full Regression

Before commit:

```bash
npm test
```

If CSS/component-only changes are large, also run the frontend build:

```bash
cd ui && npm run build
```

Use the repo's actual package scripts if they differ at implementation time.

## Visual QA

Use Browser/CDP or Playwright screenshots after implementation.

Required states:

- Desktop classic panel, GPT selected.
- Desktop classic panel, Grok selected with image/video mode visible.
- Desktop classic panel, Gemini API selected with aspect/resolution controls visible.
- Settings workspace generation section.
- Provider readiness popup with at least one unavailable provider.
- Agent mode provider/model settings.
- Narrow/mobile width where the right panel has the least space.
- Light and dark theme modes.

Checks:

- No text overlap or clipped labels.
- Provider cards retain stable dimensions when status changes.
- Focus ring visible on every provider card.
- Selected and unavailable states are distinguishable without relying only on color.
- Gemini gradients, if used, are tiny accents only.
- Grok does not use recreated/modified official marks.
- GPT remains monochrome and restrained.

## Risk Register

| Risk | Mitigation |
|---|---|
| Provider UI refactor changes generation routing. | Keep identity layer display-only; add tests around provider selection and model coercion. |
| Brand polish becomes visually noisy. | Keep brand expression to accents, badges, and shape rhythm. No decorative backgrounds. |
| Agent mode provider support differs from classic mode. | Document support matrix and test coercion behavior. |
| CSS move breaks modal/readiness layout. | Move provider selectors incrementally and screenshot readiness popup. |
| Hardcoded copy remains. | Search for `Gemini API`, `Grok`, `GPT`, `agy`, `grok-api`, `gemini-api` in React files before closeout. |

## Closeout Evidence Required

Implementation should not be considered done until the closeout devlog includes:

- Documentation evidence: updated `_plan` or `_fin` path.
- Implementation evidence: changed source/test paths.
- Verification evidence: command output summary and screenshot/visual QA notes.
