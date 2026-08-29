---
created: 2026-06-11
updated: 2026-06-11
status: execution-plan
tags: [frontend, provider-ui, plan]
---

# Execution Plan

## Phase 0 - Baseline Capture

Before changing code:

- Capture screenshots of current provider controls in classic right panel, settings workspace, readiness popup, and agent mode.
- Record desktop and narrow/mobile widths.
- Save notes on text wrapping, clipped menus, focus states, and selected/unavailable states.

Suggested local views:

- Classic right panel with GPT OAuth selected.
- Classic right panel with Grok selected.
- Classic right panel with Gemini API selected.
- Settings generation section.
- Provider readiness popup.
- Agent settings panel.

## Phase 1 - Provider Identity Layer

Add a frontend display metadata module:

- `ui/src/lib/providerIdentity.ts`
- Unit/contract tests for provider identity completeness.

Acceptance:

- Every `Provider` has display metadata.
- The map includes company/product/method/family/status kind.
- No generation behavior changes.
- No source file imports React from this metadata module.

## Phase 2 - Provider Selector Polish

Refactor `ProviderSelect.tsx` to use provider identity metadata and a reusable card pattern.

Tasks:

- Replace `GRID` labels with identity metadata.
- Preserve `useProviderAvailability` behavior.
- Add `ProviderCard` and `ProviderStatusBadge`.
- Use stable card dimensions and compact labels.
- Ensure unavailable cards still explain the reason through modal/title/aria.

Acceptance:

- Same provider values can be selected as before.
- Unavailable paths still open `ApiDisabledModal`.
- GPT/Grok/Gemini families are visually distinct but restrained.
- No card text overflows at right-panel width.

## Phase 3 - Provider Control Unification

Refactor provider-specific controls in `GenerationControlsPanel.tsx`.

Tasks:

- Extract provider compatibility note rendering.
- Move hardcoded Gemini API copy into i18n.
- Wrap Gemini model/aspect/resolution controls in shared option group primitives.
- Align Grok image/video toggle, Grok model picker, and Gemini controls to one spacing rhythm.

Acceptance:

- GPT, Grok, Gemini branches keep existing behavior.
- Gemini API model/aspect/resolution controls no longer use inline styles for layout.
- Provider compatibility text is sourced from i18n/metadata.

## Phase 4 - Settings And Readiness Parity

Tasks:

- Apply provider identity display to `SettingsWorkspace.tsx`.
- Recheck `ProviderReadinessPopup.tsx`, `AccountSettings.tsx`, `GeminiKeySection.tsx`, and `BillingBar.tsx`.
- Keep account/security settings utilitarian; do not turn them into brand cards unless it improves scanning.

Acceptance:

- Settings generation provider text matches right-panel terminology.
- No hardcoded provider copy remains in React branches unless intentionally technical.
- Readiness popup uses the same provider names/method labels.

## Phase 5 - Agent Mode Parity

Tasks:

- Replace native provider `<select>` in `AgentModelSelector.tsx` with the shared compact provider option pattern or a dense segmented version.
- Decide whether agent mode should support `grok-api` and `gemini-api`; if not, document why in code comments/devlog.
- Align model selection labels with `ImageModelSelect.tsx`.

Acceptance:

- Agent mode no longer feels like a separate older UI.
- Provider/model constraints remain correct.
- Keyboard navigation remains clear.

## Phase 6 - CSS Ownership Cleanup

Tasks:

- Move provider CSS from `toast-modal.css` to `provider-controls.css`.
- Keep modal-specific styles in `toast-modal.css`.
- Import new stylesheet through the existing CSS entrypoint.

Acceptance:

- No provider UI class remains owned only by toast/modal CSS.
- CSS remains scoped and under the repo's file-size discipline.

## Phase 7 - Visual Polish Pass

Tasks:

- Tune spacing, border weights, badges, and selected states after screenshot review.
- Verify light/dark modes and GPT/Grok/Gemini theme families.
- Remove any one-off inline styles introduced during earlier phases.

Acceptance:

- Controls feel cohesive across providers.
- No one-note palette dominates the app.
- No text overlap, unstable card sizing, or clipped selected states.
