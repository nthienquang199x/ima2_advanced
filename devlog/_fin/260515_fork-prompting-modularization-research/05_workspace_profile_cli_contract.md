---
created: 2026-05-15
tags: [ima2-gen, jawdev, workspace-profile, prompt-studio, cli-contract]
status: proposed / PABCD-ready planning note
---

# Workspace Profile + CLI Contract

This note turns the fork research into a jawdev-style implementation shape. The key decision is to treat the fork as a configurable **Prompt Studio workspace profile**, not as a replacement UI.

## Part 1 — Easy Explanation

The current app already treats Gallery as one data source with multiple views: date, session, favorites, strip, modal, and virtualized grids. The fork can be absorbed the same way.

Instead of copying the fork UI, upstream should expose a second workspace profile:

```text
Default workspace:
  prompt sidebar -> generate -> result viewer -> history/gallery

Prompt Studio workspace:
  prompt builder -> ordered composer blocks -> generate -> result viewer -> grouped history
```

Both profiles should use the same generation APIs, the same `GenerateItem` identity, and the same sidecar/history contracts. Settings should choose the workspace profile and display surfaces; CLI commands should remain stable and must not behave differently just because the UI profile changed.

## Part 2 — Abstraction From Fork To Upstream

### Source Difference

The fork is different from upstream in these product axes:

| Axis | Upstream today | Fork behavior | Upstream abstraction |
|---|---|---|---|
| Layout | Sidebar composer, center viewer, bottom history strip | Bottom composer, right builder panel, recent history sidebar | `WorkspaceLayoutProfile` |
| Prompt creation | Main prompt + inserted prompt chips | Conversation-based prompt builder with KO/EN final prompt | `PromptBuilderSession` + structured output |
| Prompt ordering | Inserted prompts are mostly flat chips | Prompt blocks can be arranged around the main prompt | `ComposerBlock[]` with `placement` and `order` |
| Current image context | Current image actions such as continue/canvas/first-node | Current image can scope a builder session | `CurrentImageContext` |
| History | Strip + gallery modal, existing dedupe helpers | Sidebar history, grouped multimode cards, quick delete | `HistoryPresentationEntry[]` |
| Persistence | Sidecar generation metadata | Composer/builder context restored from generated image | `ComposerSnapshot` in sidecar |
| Branding/distribution | `ima2`, package `ima2-gen` | `ima2x`, scoped fork package | Do not port |

## Part 3 — Settings Model

### New UI Settings Boundary

Do not add one toggle per component. Add one high-level profile, then optional advanced overrides.

Proposed config keys:

```text
ui.workspaceProfile = "default" | "prompt-studio"
ui.promptBuilderSurface = "off" | "right-panel" | "popup"
ui.composerPlacement = "sidebar" | "bottom"
historyStripLayout = "rail" | "horizontal" | "sidebar"
ui.multimodeHistoryGrouping = "individual" | "sequence"
ui.restoreComposerFromHistory = true | false
ui.viewerTools = "basic" | "zoom-pan"
```

### Policy

- `ui.workspaceProfile` selects the default bundle.
- Advanced settings may override profile defaults.
- These settings affect the browser UI only.
- They must not change `ima2 gen`, `ima2 edit`, `ima2 multimode`, or `ima2 node generate` behavior.
- If a setting is persisted in shared config, CLI docs must clearly mark it as UI-only.
- Do not add a second history placement key. Reuse the existing `historyStripLayout` state and `HistoryStripLayoutToggle`; Prompt Studio should preset or project through that existing setting.

### Default Presets

```ts
const DEFAULT_WORKSPACE_PROFILE = {
  promptBuilderSurface: "off",
  composerPlacement: "sidebar",
  historyStripLayout: "rail",
  multimodeHistoryGrouping: "individual",
  restoreComposerFromHistory: true,
  viewerTools: "basic",
};

const PROMPT_STUDIO_WORKSPACE_PROFILE = {
  promptBuilderSurface: "right-panel",
  composerPlacement: "bottom",
  historyStripLayout: "sidebar",
  multimodeHistoryGrouping: "sequence",
  restoreComposerFromHistory: true,
  viewerTools: "zoom-pan",
};
```

## Part 4 — CLI Command Contract

### Existing Commands To Preserve

These commands must continue to mean exactly what they mean today:

```text
ima2 gen
ima2 edit
ima2 multimode
ima2 node generate
ima2 prompt
ima2 skill
ima2 capabilities
ima2 defaults
ima2 config
ima2 show
ima2 ls
```

The workspace profile is a UI composition setting. It must not silently alter generation defaults, provider selection, model selection, reasoning effort, web search, refs, or output directory behavior.

### Recommended New CLI Surface

Prefer adding the prompt-builder command under existing `ima2 prompt` rather than creating a new top-level command. This avoids another `bin/ima2.ts` dispatch/help whitelist path and keeps prompt-related workflows grouped.

Implementation warning: current `bin/commands/prompt.ts` is already close to the repository's 500-line file limit. The command name should live under `prompt`, but the implementation must be split out of the current monolithic file.

Required shape:

```text
bin/commands/prompt.ts              thin dispatcher/help wiring only
bin/commands/prompt/build.ts        prompt-builder command implementation
```

If the implementation uses a different filename such as `bin/commands/promptBuild.ts`, the same rule applies: keep `prompt.ts` as a dispatcher and keep the build logic in a focused module.

Proposed command:

```text
ima2 prompt build --message "<request>" [--ref <image>] [--model <model>] [--language ko|en|both] [--json]
ima2 prompt build --messages <file|@file|-> [--json]
```

Behavior:

- Calls the same server route as the UI Prompt Builder.
- Accepts optional image refs for image-to-prompt refinement.
- Returns structured fields, not just a raw string.
- Does not write to prompt library unless an explicit save/import command is used.
- Does not mutate composer settings, generation defaults, or workspace profile.

Suggested JSON output:

```json
{
  "intentSummary": "...",
  "finalPrompt": {
    "ko": "...",
    "en": "..."
  },
  "notes": ["..."],
  "model": "gpt-5.5",
  "source": "prompt-builder"
}
```

### Existing Prompt Commands Must Stay Separate

`ima2 prompt build` should not replace these existing prompt-library commands:

```text
ima2 prompt ls
ima2 prompt show
ima2 prompt create
ima2 prompt edit
ima2 prompt rm
ima2 prompt favorite
ima2 prompt export
ima2 prompt import json
ima2 prompt import preview
```

Builder output can later feed prompt-library commands explicitly:

```text
ima2 prompt build --message "..." --json > /tmp/prompt-builder.json
ima2 prompt create --name "..." --text "$(jq -r '.finalPrompt.en' /tmp/prompt-builder.json)"
```

Do not make `prompt build` implicitly create prompt-library records.

## Part 5 — Capabilities / Skill / Help Updates

### Capabilities Payload

When Prompt Studio lands, `ima2 capabilities --json` should expose the UI profile and builder command without suggesting that UI profile changes affect CLI generation.

Proposed shape:

```json
{
  "workspaceProfiles": {
    "profiles": ["default", "prompt-studio"],
    "default": "default",
    "uiOnly": true,
    "settingsKeys": [
      "ui.workspaceProfile",
      "ui.promptBuilderSurface",
      "ui.composerPlacement",
      "historyStripLayout",
      "ui.multimodeHistoryGrouping",
      "ui.restoreComposerFromHistory",
      "ui.viewerTools"
    ]
  },
  "promptBuilder": {
    "available": true,
    "route": "/api/prompt-builder/chat",
    "cliCommand": "ima2 prompt build",
    "structuredOutput": ["intentSummary", "finalPrompt.ko", "finalPrompt.en", "notes"]
  }
}
```

### SKILL.md Update

The packaged skill should teach agents this rule:

```text
Use `ima2 prompt build` to improve or translate prompt intent.
Use `ima2 gen` / `ima2 multimode` to generate images.
Workspace profile settings are UI-only and do not change CLI generation behavior.
```

### Help Text

`ima2 prompt --help` should include:

```text
ima2 prompt build --message "<request>" [--ref <image>] [--json]
```

Top-level `ima2 --help` does not need a new command if `prompt build` remains under `prompt`. If a future implementation adds `ima2 prompt-builder` as a top-level command, then `bin/ima2.ts` help, whitelist, switch dispatch, docs, tests, and packaged skill must all be updated together.

## Part 6 — Backend / UI File Plan

The authoritative backend module split is Slice 1 in [02_modularization_plan.md](02_modularization_plan.md). The list below repeats that source of truth so implementation issues do not accidentally drop support files.

### Backend

```text
ADD    lib/promptBuilder/constants.ts
ADD    lib/promptBuilder/types.ts
ADD    lib/promptBuilder/errors.ts
ADD    lib/promptBuilder/requestSchema.ts
ADD    lib/promptBuilder/attachments.ts
ADD    lib/promptBuilder/context.ts
ADD    lib/promptBuilder/systemPrompt.ts
ADD    lib/promptBuilder/transport.ts
ADD    lib/promptBuilder/responseParser.ts
ADD    lib/promptBuilder/client.ts
ADD    routes/promptBuilder.ts
MODIFY routes/index.ts
ADD    tests/prompt-builder-contract.test.ts
```

### CLI

```text
MODIFY bin/commands/prompt.ts              # dispatcher/help only
ADD    bin/commands/prompt/build.ts        # implementation; keep prompt.ts under 500 lines
MODIFY docs/CLI.md
MODIFY skills/ima2/SKILL.md
MODIFY lib/capabilities.ts
ADD    tests/cli-prompt-builder-contract.test.js
MODIFY tests/cli-capabilities-contract.test.js
MODIFY tests/cli-skill-command-contract.test.js
```

### UI Settings

```text
ADD    ui/src/lib/workspaceProfile.ts
ADD    ui/src/components/settings/WorkspaceProfileSettings.tsx
MODIFY ui/src/components/SettingsWorkspace.tsx
MODIFY ui/src/store/persistenceRegistry.ts
MODIFY ui/src/store/useAppStore.ts
ADD    tests/workspace-profile-settings-contract.test.js
```

### Prompt Studio UI

```text
ADD    ui/src/store/promptBuilderStore.ts
ADD    ui/src/components/prompt-builder/*
ADD    ui/src/components/composer/*
ADD    ui/src/lib/promptBuilder/*
ADD    ui/src/lib/composerPrompt.ts
```

## Part 7 — Acceptance Criteria

### Settings

- Settings has a clear `Workspace layout` or `Workspace profile` control.
- `Default` keeps the current UI behavior.
- `Prompt Studio` enables the builder/composer/history preset.
- Advanced overrides do not make settings copy dense or confusing.
- Mobile behavior is not silently changed by a desktop-only profile.

### CLI

- `ima2 gen`, `edit`, `multimode`, and `node generate` outputs do not change from profile settings.
- `ima2 prompt build --json` returns parseable structured output.
- `ima2 prompt build` does not create prompt-library entries unless a separate command is used.
- `ima2 capabilities --json` makes UI-only status explicit.
- `ima2 skill` explains the builder/generate separation.
- `ima2 --help` and `ima2 prompt --help` remain agent-friendly.

### Tests

```text
node --test tests/cli-prompt-builder-contract.test.js
node --test tests/cli-capabilities-contract.test.js tests/cli-skill-command-contract.test.js
node --test tests/workspace-profile-settings-contract.test.js
npm run typecheck
cd ui && npx tsc -b --noEmit
npm run ui:build
npm test
git diff --check
```

## Part 8 — Non-Goals

- Do not rename package or binary.
- Do not make CLI generation depend on UI workspace profile.
- Do not hide generation controls behind Prompt Studio.
- Do not make prompt-builder output auto-save into prompt library.
- Do not add a new top-level command unless `prompt build` proves too cramped.
- Do not copy the fork's large `useAppStore.ts`, `index.css`, or inline `Canvas.tsx` patterns.

## Part 9 — Audit Questions

Before implementation, plan audit should verify:

1. Is `ima2 prompt build` the right command surface, or should it be a top-level command?
2. Are UI workspace config keys acceptable in shared config, or should they stay browser-local?
3. Does `capabilities --json` clearly mark workspace settings as UI-only?
4. Does the prompt-builder endpoint leak prompt/image context into logs or persisted state?
5. Are `ComposerSnapshot` and sidecar restore scoped enough to avoid bloating `GenerateItem`?
6. Does the CLI implementation keep `bin/commands/prompt.ts` under the 500-line file limit by using a split build module?
