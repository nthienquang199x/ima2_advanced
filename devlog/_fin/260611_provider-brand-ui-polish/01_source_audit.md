---
created: 2026-06-11
updated: 2026-06-11
status: source-audit
tags: [frontend, provider-ui, audit]
---

# Source Audit

## Local Search Performed

Commands used during planning:

```bash
rg -n "OpenAI|GPT|Grok|xAI|Gemini|Google|Vertex|Antigravity|Agy|provider|imageModel|model picker|Billing|Account|oauth|api key|apiKey|grok-api|gemini-api|agy" ui/src site docs structure tests
rg --files ui/src
```

## Primary Surfaces

| Surface | Current role | Design concern |
|---|---|---|
| `ui/src/styles/themes.css` | Contains brand-family theme tokens for GPT, Claude, Gemini, and likely Grok farther down the file. | Theme tokens exist, but provider controls do not consume a provider identity layer consistently. |
| `ui/src/components/ProviderSelect.tsx` | Three company columns: GPT, Grok, Gemini. Each column exposes OAuth/API/agy cells. | Columns are clear but visually generic. Status, method, product, and company are compressed into tiny pills. |
| `ui/src/components/GenerationControlsPanel.tsx` | Branches on `isGrok`, `isAgyOnly`, `isGeminiApi`, `isAnyGemini`; renders provider details and Grok/Gemini-specific controls. | Provider copy and control layouts are inline. Gemini API has hardcoded English text. Grok/Gemini controls diverge from shared option patterns. |
| `ui/src/components/ImageModelSelect.tsx` | Groups GPT/Grok/Gemini model choices in a custom portal menu. | Stronger than native select, but model/provider identity is label-driven and not tied to provider card language. |
| `ui/src/lib/imageModels.ts` | Central model lists and provider hints. | Good model source of truth, but not enough metadata for company/product display or visual treatment. |
| `ui/src/styles/toast-modal.css` | Owns `.provider-grid`, `.provider-pill`, `.provider-compat-details`, Grok mode/size picker styles. | Provider component styles living in toast/modal CSS makes ownership unclear and increases accidental coupling. |
| `ui/src/components/SettingsWorkspace.tsx` | Account/generation settings with provider-specific branches. | Gemini API text is hardcoded; settings design does not share a provider identity card. |
| `ui/src/components/agent/AgentModelSelector.tsx` | Agent mode provider/model/reasoning settings. | Uses native `<select>`, so it visually lags the main provider selector. Provider options omit `grok-api` and `gemini-api`, so parity needs product review. |

## Supporting Surfaces To Recheck During Implementation

- `ui/src/components/GrokModelPicker.tsx`
- `ui/src/components/GrokSizePicker.tsx`
- `ui/src/components/VideoControlsPanel.tsx`
- `ui/src/components/ProviderReadinessPopup.tsx`
- `ui/src/components/AccountSettings.tsx`
- `ui/src/components/GeminiKeySection.tsx`
- `ui/src/components/BillingBar.tsx`
- `ui/src/styles/right-panel.css`
- `ui/src/styles/settings-controls.css`
- `ui/src/styles/agent-workspace-sidebar.css`
- `ui/src/i18n/*` provider/model strings

## Structural Problems

1. Provider identity is implicit.

   `Provider` values are routed through availability, model, billing, and generation code, but there is no single frontend metadata map that says: company name, product name, auth method, brand family, accent, icon strategy, compact label, long label, readiness label, and preferred control density.

2. Provider control styles are not colocated.

   `.provider-grid` and `.provider-pill` live in `toast-modal.css`, while the user sees them in the right panel. This makes provider UI feel like an add-on instead of a first-class surface.

3. Model controls are provider-specific but not systemized.

   Grok uses `GrokModelPicker`/`GrokSizePicker`; Gemini API uses inline button grids; GPT falls back to shared quality/format/moderation controls. The visual rhythm changes by provider.

4. Settings and agent mode are behind.

   `SettingsWorkspace.tsx` and `AgentModelSelector.tsx` present provider-specific controls with less polish than the main panel, causing cross-mode inconsistency.

5. Copy/i18n drift exists.

   Hardcoded strings such as `Gemini API` and `Google Gemini API direct...` should move to i18n and provider metadata, not remain inline in React branches.

## Recommended Boundary

Introduce a small frontend-only identity layer before visual work:

- `ui/src/lib/providerIdentity.ts`
- `ui/src/components/provider/ProviderCard.tsx`
- `ui/src/components/provider/ProviderOptionGroup.tsx`
- `ui/src/components/provider/ProviderStatusBadge.tsx`
- `ui/src/styles/provider-controls.css`

This should remain UI metadata only. Generation routing and server behavior should continue to use the existing provider/model types.
