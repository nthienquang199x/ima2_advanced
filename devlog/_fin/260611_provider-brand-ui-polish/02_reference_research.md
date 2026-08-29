---
created: 2026-06-11
updated: 2026-06-11
status: research
tags: [frontend, provider-ui, brand-research]
---

# External Reference Research

## Search Method

Detailed external search was requested, so the planning pass used focused official-source searches rather than broad inspiration browsing.

Queries:

```text
OpenAI official brand guidelines ChatGPT interface monochrome design
xAI Grok official brand design interface monochrome
Google Gemini official brand guidelines Material Design 3 color system
Google Material Design 3 official color system components
site:m3.material.io Material Design 3 color roles primary secondary tertiary surface official
site:m3.material.io Material Design 3 components buttons official
```

## Sources Opened

- OpenAI Design Guidelines: https://openai.com/brand/
- OpenAI Apps SDK UI Guidelines: https://developers.openai.com/apps-sdk/concepts/ui-guidelines
- xAI Brand Guidelines: https://x.ai/legal/brand-guidelines
- xAI homepage / Grok product framing: https://x.ai/
- Google Design, Gemini AI Visual Design: https://design.google/library/gemini-ai-visual-design
- Material Design 3: https://m3.material.io/
- Material Design 3 color roles: https://m3.material.io/styles/color/roles
- Material Design 3 buttons: https://m3.material.io/components/buttons/overview
- Material Design 3 segmented buttons: https://m3.material.io/components/segmented-buttons

## OpenAI / GPT Direction

Official OpenAI brand guidance emphasizes correct trademark/logotype usage and warns against altering marks. The Apps SDK UI guidelines are more directly useful for this app: they describe a restrained ChatGPT visual world where system colors carry the structural UI and brand expression belongs in accents, icons, or inline imagery, not in core backgrounds or text color overrides.

Implication for ima2-gen:

- GPT/OpenAI provider treatment should be monochrome, quiet, and system-like.
- Use neutral surfaces, clean border hierarchy, and minimal outlined iconography.
- Do not use OpenAI/ChatGPT marks unless usage is sourced and compliant.
- Avoid green legacy ChatGPT accents; current local `themes.css` already notes GPT as monochrome.

## xAI / Grok Direction

xAI's official brand guideline is primarily legal/trademark guidance. It says xAI owns the `xAI` and `Grok` marks and that logos must be used exactly as provided. The xAI product site frames Grok as a broad multimodal developer platform with text, code, voice, images, and video through one API.

Implication for ima2-gen:

- Treat Grok as a stark, high-contrast provider with compact technical controls.
- Avoid recreating or modifying official xAI/Grok logos.
- Since Grok has image and video paths, its provider card needs a clear image/video mode affordance, not just a generic auth pill.
- Monochrome shape and heavier border contrast are safer than decorative brand marks.

## Google / Gemini Direction

Google Design's Gemini visual article emphasizes continuity with Google visual language: circles, rounded optimism, familiar Google-color references, softened Material shapes, and motion as a purposeful signal of system activity. Material 3 documentation describes an adaptable component system, color roles, and component patterns such as buttons, icon buttons, and segmented buttons.

Implication for ima2-gen:

- Gemini provider treatment should use rounded containers and calm blue-gray Material-like surfaces.
- Google/Gemini gradient should be reserved for tiny identity accents or generated-state indicators, not full-card backgrounds or primary buttons.
- Gemini API aspect/resolution controls should look like first-class segmented controls, not one-off inline grids.
- `agy` should be presented as a Gemini-family path with a precise access-method label, not as a separate company.

## Cross-Provider Rules

1. Brand identity should aid recognition, not dominate the work surface.
2. Use stable dimensions for provider controls so status dots, badges, and two-line labels do not resize the panel.
3. Use color as accent/status only; text and core controls should keep theme readability.
4. Keep labels short inside buttons. Put compatibility notes in details/summary or side copy.
5. Use accessible contrast and preserve keyboard focus states.
6. Avoid decorative gradients, blobs, or large illustrative branding in the right panel.

## Research Confidence

| Provider | Confidence | Notes |
|---|---|---|
| GPT/OpenAI | High | Official OpenAI brand and Apps SDK UI guidance are directly relevant to restrained system UI. |
| Grok/xAI | Medium | Official legal guidance exists, but less component-level UI guidance. Use xAI/Grok product framing plus safe monochrome treatment. |
| Gemini/Google | High | Google Design and Material 3 provide direct visual/component guidance. |
| agy / Antigravity path | Medium | In this repo it behaves as a Gemini-family CLI/provider path. Treat under Google/Gemini family unless product naming changes. |
