---
created: 2026-06-11
updated: 2026-06-11
status: design-direction
tags: [frontend, provider-ui, design]
---

# Design Direction

## Principle

Make provider selection feel like a compact cockpit control, not a marketing section. The user should instantly see:

- which company/product family is selected;
- which access path is active;
- whether the path is ready;
- which provider-specific controls are available next.

## Provider Identity Model

Create a provider identity map with fields similar to:

```ts
type ProviderIdentity = {
  provider: Provider;
  company: "OpenAI" | "xAI" | "Google";
  product: "GPT" | "Grok" | "Gemini";
  method: "OAuth" | "API" | "CLI";
  compactLabel: string;
  longLabel: string;
  family: "gpt" | "grok" | "gemini";
  statusKind: "oauth" | "api-key" | "local-cli";
  accentVar: string;
};
```

This metadata should not replace backend provider routing. It only centralizes display, i18n keys, and visual styling.

## Visual Language By Provider

### GPT / OpenAI

- Shape: simple rounded rectangles, no decorative fill.
- Color: monochrome surfaces and borders; selected state uses strong contrast, not a saturated accent.
- Controls: precise, quiet, system-native feel.
- Avoid: green ChatGPT legacy accent, large logo treatment, gradients.

### Grok / xAI

- Shape: compact, high-contrast, technical.
- Color: monochrome with stronger black/white contrast and crisp active borders.
- Controls: image/video mode should be more prominent because Grok spans both modalities.
- Avoid: approximated official logos, oversized sci-fi styling, unnecessary animation.

### Gemini / Google

- Shape: softer and rounder, with Material-like segmented groups.
- Color: cool blue-gray surfaces plus restrained Google blue accent.
- Gradient: only small identity accent, selected indicator, or loading affordance if it remains subtle.
- Controls: aspect/resolution should become proper segmented controls with stable grid dimensions.
- Avoid: gradient buttons, full-card rainbow backgrounds, over-rounded controls that break density.

## Component Direction

1. `ProviderCard`

   Replaces the current tiny generic provider pills with a compact card per access path. It should show:

   - product family (`GPT`, `Grok`, `Gemini`);
   - access method (`OAuth`, `API`, `CLI`);
   - readiness badge;
   - short secondary label when needed (`Codex login`, `xAI key`, `Google key`, `Antigravity`).

2. `ProviderOptionGroup`

   Shared wrapper for provider cards in right panel, settings, and readiness popup. It should support compact and full variants.

3. `ProviderStatusBadge`

   Replaces raw status dots where text would help. Use dot-only only in dense contexts with tooltip/title.

4. `ProviderCompatNote`

   Extract provider compatibility details from `GenerationControlsPanel.tsx` into metadata/i18n-driven content.

5. `ProviderModelControls`

   Wrap provider-specific model/size/aspect controls so GPT/Grok/Gemini branches share title spacing, grid rhythm, active state, disabled state, and help text.

## CSS Direction

Move provider-specific CSS out of `toast-modal.css` into `ui/src/styles/provider-controls.css`, then import it from the existing style entrypoint.

Candidate class families:

- `.provider-option-group`
- `.provider-card`
- `.provider-card--gpt`
- `.provider-card--grok`
- `.provider-card--gemini`
- `.provider-status-badge`
- `.provider-compat-details`
- `.provider-control-grid`

Use CSS variables already present in `themes.css` first. Add only local provider-control variables when needed.

## Copy Direction

- Move hardcoded provider strings in `GenerationControlsPanel.tsx`, `SettingsWorkspace.tsx`, and `AgentModelSelector.tsx` into i18n.
- Use `Gemini CLI` or `Antigravity CLI` consistently after product review. Current code labels `agy` as both `agy` and `Gemini`; the UI should make the relationship explicit.
- Distinguish company/product/method:
  - Company: OpenAI, xAI, Google
  - Product: GPT, Grok, Gemini
  - Method: OAuth, API key, CLI

## Accessibility Direction

- Every provider card remains a real `button`.
- Use `aria-pressed` for selected state.
- Use descriptive `aria-label`: product + method + ready/unavailable reason.
- Preserve keyboard focus ring with sufficient contrast.
- Keep text readable at narrow sidebar width; no label should rely on viewport-scaled font.
