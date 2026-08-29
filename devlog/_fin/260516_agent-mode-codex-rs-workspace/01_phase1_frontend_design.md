---
created: 2026-05-16
status: implemented
tags: [ima2-gen, agent-mode, frontend, dev-frontend, responsive-ux]
depends_on:
  - 00_overview.md
---

# Phase 1 Frontend Design

## Implementation Status

2026-05-16: Implemented as a product-visible Agent workspace with responsive
Sessions/Chat/Image regions, mobile drawer/sheet dialogs, UI-only image-handle
state, and visual verification through `agbrowse`. It can be hidden explicitly
with `VITE_IMA2_AGENT_MODE=0`.

## Intent

Agent Mode is a full workspace mode, not a small assistant panel beside Node.
When the user switches to Agent, the app should feel like a ChatGPT-style image
agent session:

```text
Desktop:
Sessions | Chat | Image

Tablet:
Sessions drawer
Image
Chat

Mobile:
Sessions drawer
Chat
Image sheet
```

The frontend job for Phase 1 is to build the shell, responsive information
architecture, and state boundaries before the Codex-rs runtime is wired in.

## dev-frontend Fit

Classification:

| Axis | Decision |
|---|---|
| Surface type | AI productivity / creative tool |
| First screen | Working workspace, not landing or hero |
| Density | Medium-high; optimized for repeated creation and review |
| Motion | Low; only state transitions, sheet/drawer, streaming indicators |
| Locale | Korean-first labels with English parity |
| Primary asset | Actual generated image / current image, never decorative filler |
| Trust signal | Clear session state, compact status, current image provenance |

Applied dev-frontend rules:

- Use the real app surface as the first screen; no marketing hero.
- Keep the workspace quiet and operational, not illustrative or card-heavy.
- Avoid nested cards; panels are layout regions, not floating cards inside cards.
- Keep stable dimensions for session rows, composer, image preview, tabs, and
  mobile sheet triggers so text and generated thumbnails do not shift layout.
- Use icons for commands when an existing icon set is available; otherwise use
  existing ima2 button conventions until the icon dependency is settled.
- Korean labels must fit in compact controls and remain natural, not translated
  word-for-word from English.
- Verify the actual UI with desktop, tablet, and mobile screenshots before a
  Phase 1 implementation is considered done.

## Existing Frontend Anchors

Current mode switching lives in:

- `ui/src/App.tsx`
- `ui/src/components/UIModeSwitch.tsx`
- `ui/src/types.ts`
- `ui/src/store/useAppStore.ts`
- `ui/src/store/persistenceRegistry.ts`
- `ui/src/lib/devMode.ts`

Useful patterns to reuse:

- `ClassicWorkspace` already shows how a top-level workspace replaces the
  central canvas when the active mode changes.
- `PromptBuilderPanel`, `PromptBuilderMessageList`, and
  `PromptBuilderComposer` provide chat/message/composer interaction patterns.
- `SessionPicker` and the session store provide graph-session behavior, but
  Agent sessions need their own runtime identity because Codex thread state is
  not the same as Node graph state.
- `MobileAppBar` and `MobileComposeSheet` show how mobile-only overlays are
  already mounted globally from `App.tsx`.

Do not turn `prompt-builder` into Agent Mode. It is a prompt helper. Agent Mode
gets a dedicated `components/agent/` namespace and may copy only small proven
patterns.

## Target IA

Top-level modes:

```text
Classic | Node | Agent
```

Agent workspace regions:

| Region | Desktop | Tablet | Mobile |
|---|---|---|---|
| Sessions | Left sidebar | Drawer from top bar | Drawer from title bar |
| Chat | Center pane | Lower pane | Primary screen |
| Image | Right pane | Upper pane | Bottom sheet / full-screen dialog |

Desktop layout:

```text
┌────────────────┬────────────────────────┬────────────────────────┐
│ Agent Sessions │ Agent Chat             │ Image Workspace        │
│                │                        │                        │
│ New            │ Turns                  │ Current image          │
│ Search/filter  │ Tool summaries         │ Variants               │
│ Session list   │ Composer               │ Refs / Web / Memory    │
└────────────────┴────────────────────────┴────────────────────────┘
```

Column rules:

```text
>= 1280px:
280px | minmax(420px, 0.95fr) | minmax(520px, 1.05fr)

1024px - 1279px:
64px rail | minmax(420px, 1fr) | minmax(440px, 1fr)

768px - 1023px:
top bar + sessions drawer
image preview minmax(300px, 44dvh)
chat minmax(0, 1fr)

< 768px:
top bar
chat minmax(0, 1fr)
composer
image sheet hidden until opened
```

## Visual System

Use the existing ima2 theme tokens instead of introducing a new palette:

- Background: `var(--bg)`
- Primary surface: `var(--surface)`
- Secondary surface: `var(--surface-2)`
- Border: `var(--border)` / `var(--border-strong)`
- Text: `var(--text)` / `var(--text-dim)` / `var(--text-faint)`
- Accent: existing `var(--accent)` / `var(--accent-soft)` family

Agent Mode can have its own CSS namespace:

```css
.agent-workspace { ... }
.agent-sessions { ... }
.agent-chat { ... }
.agent-image { ... }
```

Style constraints:

- No new dominant purple/blue gradient theme.
- No decorative orb/blob/bokeh backgrounds.
- No hero-scale type inside tool panels.
- Keep panel border radius aligned with existing app controls; do not increase
  radius beyond current workspace conventions.
- Use full-height constrained panes with internal scrolling only.
- Never let the whole page scroll on desktop Agent Mode.

## Component Plan

New frontend files:

| File | Purpose |
|---|---|
| `ui/src/components/agent/AgentWorkspace.tsx` | Owns the complete Agent Mode shell and responsive region composition. |
| `ui/src/components/agent/AgentTopBar.tsx` | Mobile/tablet title, session drawer trigger, current image trigger. |
| `ui/src/components/agent/AgentSessionSidebar.tsx` | Desktop session list with search, create, rename, delete. |
| `ui/src/components/agent/AgentSessionRail.tsx` | Laptop narrow rail with thumbnails and unread/compact badges. |
| `ui/src/components/agent/AgentSessionDrawer.tsx` | Tablet/mobile session drawer. |
| `ui/src/components/agent/AgentChatPane.tsx` | Chat region wrapper with status header, message list, composer. |
| `ui/src/components/agent/AgentMessageList.tsx` | Virtual-ready message list and auto-scroll policy. |
| `ui/src/components/agent/AgentMessage.tsx` | User/agent/tool-summary turn rendering. |
| `ui/src/components/agent/AgentComposer.tsx` | Text input, image reference attachment, web-search toggle, send. |
| `ui/src/components/agent/AgentImagePane.tsx` | Current image, variants, image actions, provenance tabs. |
| `ui/src/components/agent/AgentImageSheet.tsx` | Mobile image preview sheet/dialog. |
| `ui/src/components/agent/AgentContextTabs.tsx` | Image / Refs / Web / Memory tabs. |
| `ui/src/components/agent/AgentStatusBadge.tsx` | Runtime, compact, generating, and auth state badges. |
| `ui/src/components/agent/agentTypes.ts` | UI-only Agent Mode types before backend contract stabilizes. |
| `ui/src/hooks/useAgentWorkspaceLayout.ts` | Maps viewport to desktop/rail/tablet/mobile layout. |
| `ui/src/lib/agentApi.ts` | Thin API client for Phase 2 runtime endpoints. Stubbed in Phase 1 if needed. |
| `ui/src/styles/agent-workspace.css` | Agent Mode layout and visual rules. |

Modify existing files:

| File | Change |
|---|---|
| `ui/src/types.ts` | Add `UIMode = "classic" | "node" | "card-news" | "agent"`. |
| `ui/src/lib/devMode.ts` | Add `ENABLE_AGENT_MODE`, default off until runtime contract exists. |
| `ui/src/store/persistenceRegistry.ts` | `ima2.uiMode` already exists; document `"agent"` as an accepted value in related tests if needed. |
| `ui/src/store/useAppStore.ts` | Allow loading/persisting `uiMode === "agent"` only when `ENABLE_AGENT_MODE` is on. |
| `ui/src/components/UIModeSwitch.tsx` | Add Agent tab with Korean/English i18n. |
| `ui/src/App.tsx` | Lazy-load `AgentWorkspace`; hide Classic/Node right-panel surfaces when Agent is active. |
| `ui/src/main.tsx` | Import `./styles/agent-workspace.css`. |
| `ui/src/i18n/ko.json` | Add natural Korean labels. |
| `ui/src/i18n/en.json` | Add English parity labels. |

## State Model

Phase 1 can use UI mock state behind the gate, but the types should match the
future backend shape.

```ts
export type AgentLayoutMode =
  | "desktop-three-pane"
  | "desktop-rail"
  | "tablet-stacked"
  | "mobile-chat-image-sheet";

export type AgentSessionSummary = {
  id: string;
  title: string;
  codexThreadId?: string | null;
  lastImageId?: string | null;
  imageCount: number;
  compacted: boolean;
  webSearchEnabled: boolean;
  updatedAt: number;
};

export type AgentTurn = {
  id: string;
  role: "user" | "assistant" | "tool";
  text: string;
  imageIds?: string[];
  webFindingIds?: string[];
  status?: "streaming" | "complete" | "error";
};

export type AgentImageHandle = {
  id: string;
  filename: string;
  url: string;
  thumbUrl?: string;
  prompt?: string | null;
  revisedPrompt?: string | null;
  createdAt: number;
};
```

Frontend rule: chat turns may reference image handles, but do not store raw
base64 images in Agent chat state.

## Interaction Spec

Session sidebar:

- `새 에이전트` creates a blank Agent session.
- Session row shows thumbnail, title, updated time, image count, web marker,
  compact badge.
- Rename prompt defaults to the session title only.
- Delete requires confirmation and should not delete generated image files in
  Phase 1.

Chat:

- User messages align with current app chat conventions.
- Assistant messages can show short tool summaries, but the user-visible end
  state should be an image or image action.
- Streaming state uses one compact status row; avoid verbose instruction text.
- Composer supports text, reference image attachment, web toggle, and send.
- `Cmd/Ctrl+Enter` sends; Enter behavior follows existing composer convention.

Image workspace:

- Current image is always visible on desktop/tablet.
- Variants are thumbnails with stable square cells.
- Tabs: `이미지`, `참조`, `웹 근거`, `기억`.
- `이미지 열기` on mobile opens `AgentImageSheet`.
- Empty image state should be quiet and functional, not explanatory marketing
  copy.

Mobile:

- Chat remains the first-class surface.
- The image sheet has focus trapping, Escape/close button, and restores focus to
  the trigger.
- Generated image chip above the composer shows the latest thumbnail and opens
  the sheet.

## Korean Copy

Initial Korean labels:

| Key | Korean |
|---|---|
| Mode tab | `에이전트` |
| New session | `새 에이전트` |
| Session drawer | `세션` |
| Chat pane | `채팅` |
| Image pane | `이미지` |
| Open image sheet | `이미지 열기` |
| Web toggle | `검색 사용` |
| Compact badge | `컴팩트됨` |
| Current image | `현재 이미지` |
| References tab | `참조` |
| Web evidence tab | `웹 근거` |
| Memory tab | `기억` |
| Generating | `생성 중` |
| Runtime reconnecting | `연결 복구 중` |

Avoid visible feature-explanation paragraphs. Labels should name controls, not
teach the app.

## Accessibility

- The mode switch remains a `tablist`.
- Session rows are buttons with visible selected state and `aria-current` where
  appropriate.
- Drawer/sheet uses dialog semantics, focus trap, Escape close, and focus
  restoration.
- Image preview has useful alt text derived from title or prompt fallback.
- Status changes use `aria-live="polite"` only for high-value state changes.
- Touch targets on mobile are at least 44px.

## File-Level Build Order

1. Add types, feature gate, i18n keys, and `UIModeSwitch` Agent tab.
2. Add `AgentWorkspace` with static mock session/chat/image data behind
   `ENABLE_AGENT_MODE`.
3. Add responsive layout hook and CSS.
4. Add session sidebar/rail/drawer.
5. Add chat pane and composer shell.
6. Add image pane and mobile sheet.
7. Replace mock data with `agentApi` stubs only after the shell is visually
   stable.

## Verification Gates

Required after Phase 1 implementation:

```bash
npm run typecheck
npm test
npm run ui:build
```

Visual verification viewports:

| Viewport | Expected |
|---|---|
| 1440x900 | Three panes visible; no page scroll; image pane has largest preview. |
| 1180x820 | Session rail visible; drawer opens full session list. |
| 900x900 | Image above chat; composer remains reachable. |
| 390x844 | Chat primary; latest image opens in sheet; no clipped Korean labels. |

Manual UX checks:

- No overlapping text in Korean or English.
- No nested card surfaces.
- No full-page desktop scroll.
- Session drawer and image sheet restore focus.
- Agent tab does not affect Classic/Node/Card News when gate is off.
- Mobile image sheet does not erase chat scroll position.

## Non-Goals

- Do not implement Codex-rs app-server runtime in Phase 1.
- Do not implement durable Agent SQLite schema in Phase 1.
- Do not expose shell/filesystem/browser tools.
- Do not make text-only final answer success states.
- Do not add a new design system or external UI framework.
- Do not reuse Node graph sessions as Agent sessions.
