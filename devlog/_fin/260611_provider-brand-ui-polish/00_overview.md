---
created: 2026-06-11
updated: 2026-06-11
status: planning
tags: [ima2-gen, frontend, provider-ui, brand-polish, dev-frontend]
---

# Provider Brand UI Polish Plan

## User Request

Jun noted that the frontend now has some company-specific design treatment, but it still does not feel clean enough under the dev-frontend standard. This folder scaffolds a detailed improvement plan before implementation.

## Scope

Polish the provider/company surfaces for:

- GPT / OpenAI: `oauth`, `api`
- Grok / xAI: `grok`, `grok-api`
- Gemini / Google: `agy`, `gemini-api`
- Agent-mode provider/model settings, which currently trail the main classic/sidebar surface

## Product Read

ima2-gen is an operational image/video generation tool, not a brand landing page. The right design target is a dense, repeatable work surface where provider identity helps recognition without turning controls into marketing cards.

Recommended design dials:

- `DESIGN_VARIANCE=4`: enough provider identity to distinguish GPT/Grok/Gemini, but no decorative overhaul.
- `MOTION_INTENSITY=2`: subtle selection/availability transitions only.
- Product density: compact tool UI, favoring scannable rows, stable controls, and short status language.
- Brand use: accents, small marks, type/shape cues, and status badges. Avoid large background gradients, decorative blobs, and logo-like usage unless sourced and legally safe.

## Current Diagnosis

The current repo already has brand-family theme tokens in `ui/src/styles/themes.css`, but the provider-specific UI is not unified:

- Provider selection lives in `ProviderSelect.tsx` with a three-column grid and generic OAuth/API pills.
- Provider compatibility copy lives inline in `GenerationControlsPanel.tsx` and `SettingsWorkspace.tsx`.
- Grok/Gemini controls use separate branches and custom inline styles.
- Provider styles live in `toast-modal.css`, which is not an obvious ownership boundary for provider UI.
- Agent mode still uses native `<select>` controls in `AgentModelSelector.tsx`, so it does not share the main provider design language.

## Desired Outcome

Provider surfaces should feel like one coherent system:

- One provider identity source of truth.
- One reusable provider card/option pattern across classic, settings, sidebar, readiness popup, and agent mode.
- Provider-specific visual cues that match official brand constraints and remain accessible.
- No duplicated hardcoded provider copy.
- Screenshot-verified desktop and mobile/narrow layout.

## Non-Goals

- Do not implement a landing-page style hero or brand showcase.
- Do not introduce unsourced official logos.
- Do not change generation behavior, provider availability logic, model routing, or billing semantics.
- Do not replace the global app theme system.
- Do not add gradients to backgrounds or primary controls just because a brand uses gradients in marketing.

## Folder Map

- `01_source_audit.md`: local code search results and risk map.
- `02_reference_research.md`: external official-source design research.
- `03_design_direction.md`: proposed UI direction and component boundaries.
- `04_execution_plan.md`: phased implementation checklist.
- `05_verification_plan.md`: tests and visual QA gates.
