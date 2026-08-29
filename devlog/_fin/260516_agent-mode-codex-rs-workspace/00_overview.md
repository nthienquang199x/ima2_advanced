---
created: 2026-05-16
status: implemented
tags: [ima2-gen, agent-mode, codex-rs, image-agent, ux]
---

# Agent Mode Codex-rs Workspace

## Implementation Status

2026-05-16: All planned phases are implemented. Agent Mode is product-visible
by default and can be hidden with `VITE_IMA2_AGENT_MODE=0`.
Agent Mode now has the responsive frontend workspace, persistent Agent sessions
and turns in SQLite, image context manifests, a narrow server-side tool policy,
Responses-backed `ima2.generate_image` / `ima2.web_search` binding, text-only
result rejection with one forced-image retry, compact/resume manifest retention,
and `agbrowse` validation across desktop, tablet, and mobile layouts.

## Intent

Agent Mode is not a small control inside the existing Classic composer. It is a
third workspace mode next to Classic and Node, but selecting it changes the
whole surface into a ChatGPT-like image-agent workspace:

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
Image as popup / bottom sheet
```

The product target is a Codex-backed visual agent workspace:

- Codex-rs owns conversational session, resume, compact, and turn lifecycle.
- ima2 owns image files, image metadata, references, canvas state, web findings,
  generation storage, and UI projection.
- The agent can use only web search and image generation.
- The user-visible final artifact is an image. Text is only context, tool
  summary, or metadata.

## Mode IA

Top-level workflow modes:

```text
Classic | Node | Agent
```

The modes have different source-of-truth surfaces:

| Mode | Primary surface | State source |
|---|---|---|
| Classic | prompt -> image | current composer + generated history |
| Node | graph branch generation | node graph + generation sidecars |
| Agent | session chat + image workspace | Codex thread + ima2 image context DB |

Agent Mode must not reuse the Classic prompt panel as its main surface. It may
reuse controls such as model, size, quality, web-search toggle, Save, Use
current, and reference attachment, but the layout is session-first.

## Agent Mode Desktop Layout

```text
┌──────────────┬──────────────────────┬──────────────────────┐
│ Sessions     │ Chat                 │ Image Workspace      │
│              │                      │                      │
│ + New Agent  │ user / agent turns   │ current output       │
│ session list │ tool summaries       │ variants / refs      │
│ search       │ composer             │ canvas actions       │
└──────────────┴──────────────────────┴──────────────────────┘
```

Recommended desktop columns:

```text
280px | minmax(420px, 0.95fr) | minmax(520px, 1.05fr)
```

The session sidebar row should include:

- last generated image thumbnail
- session title
- image count
- web-search marker
- compact badge
- updated time

## Responsive Rules

### Wide Desktop: `>= 1280px`

- Full session sidebar.
- Chat and Image side-by-side.
- Image Workspace owns large preview, variants strip, and tabs for Image / Refs
  / Web / Memory.
- Splitter may be resizable, with a stable minimum for both Chat and Image.

### Laptop: `1024px - 1279px`

- Session sidebar collapses to a narrow rail.
- Chat and Image remain side-by-side.
- Full sessions list opens as a drawer.
- Image Workspace hides secondary metadata behind tabs or a drawer.

### Tablet: `768px - 1023px`

- Sessions become a drawer.
- Chat and Image stack vertically.
- Image stays visible above Chat as the visual anchor.
- Composer remains sticky at the bottom of the Chat section.

```text
Top bar
Image preview / variants
Chat turns / composer
```

### Mobile: `< 768px`

- Chat is primary.
- Sessions are a drawer.
- Image opens as a full-screen modal or bottom sheet.
- A persistent generated-image chip or thumbnail above the composer opens the
  image sheet.

```text
Session title
Chat
Generated image chip
Composer
```

## Runtime Ownership

Agent Mode should assume Codex is installed and authenticated, but must separate
Codex session memory from ima2 image truth.

```text
Codex-rs:
- thread/start
- thread/resume
- turn/start
- compact
- text reasoning
- chat memory

ima2:
- image files
- image IDs
- current image
- references
- canvas versions
- generation options
- web findings
- image-only output validation
```

The compacted Codex thread is allowed to remember intent, style direction, and
conversation decisions. It must not be the only source of exact image state.

## Image Context Manifest

Every Agent turn should receive a host-owned manifest generated from ima2 state.
This manifest is re-injected after resume/compact so visual state does not decay
into vague text memory.

```xml
<ima2-image-context>
sessionId: ...
currentImage:
  id: ...
  path: ...
  prompt: ...
  revisedPrompt: ...
  model: ...
styleLocks:
  - ...
subjectLocks:
  - ...
references:
  - id: ...
    role: style | source | character | composition | mask
webFindings:
  - query: ...
    url: ...
    snippet: ...
constraints:
  - final user-visible output must be an image
  - allowed tools: web_search, image_generation
</ima2-image-context>
```

## Tool Boundary

The Agent runtime should expose a narrow ima2-owned tool surface:

- `ima2.get_image_context`
- `ima2.web_search`
- `ima2.generate_image`

Initial version should not expose:

- shell
- filesystem read/write
- browser control
- arbitrary MCP tools
- recursive dispatch
- non-image final answers

The image generation tool should return image handles, not large raw base64 in
the Codex transcript:

```json
{
  "imageId": "img_...",
  "thumbnailUrl": "/api/history/.../thumb",
  "path": "~/.ima2/generated/...",
  "revisedPrompt": "...",
  "width": 1024,
  "height": 1024
}
```

## Implementation Phases

### Phase 1: Agent Workspace Shell

Detailed frontend design: `01_phase1_frontend_design.md`.

- Add Agent as a third top-level workflow mode.
- Replace the Classic prompt panel with Agent session shell when active.
- Add responsive layout states:
  - `desktop-three-pane`
  - `desktop-rail`
  - `tablet-stacked`
  - `mobile-chat-with-image-sheet`
- Add session sidebar / rail / drawer behavior.

### Phase 2: Codex-rs Session Runtime

- Start or attach a Codex app-server session per ima2 Agent session.
- Maintain `codexThreadId`, `lastTurnId`, and compact status.
- Project Codex events into ima2 chat turns.
- Retire/restart the Codex runtime on timeout, auth failure, or protocol wedge.

### Phase 3: Image Context Memory

- Store image agent sessions and turns in SQLite.
- Store current image, references, web findings, style locks, and subject locks.
- Re-inject the Image Context Manifest every turn and after compact/resume.

### Phase 4: Image-only Tool Bridge

- Implement `ima2.generate_image` using existing Responses image adapter paths.
- Implement `ima2.web_search` or bind to the existing web-search-enabled
  Responses tool path.
- Enforce allowed-tool policy server-side.
- Reject text-only success; retry once with forced image generation if needed.

### Phase 5: Tests and UX Gates

- Contract test: Agent mode exposes only allowed tools.
- Contract test: image context manifest survives compact/resume.
- Contract test: mobile layout opens image as sheet/modal.
- Contract test: text-only model result is not treated as success.
- Browser smoke: desktop three-pane, tablet stacked, mobile image sheet.

## Open Questions

- Should Agent Mode use Codex app-server directly in MVP, or first ship a
  Codex-auth-backed Responses runtime with the same UI shell?
- Should web search be Codex-native, ima2-native, or Responses-native?
- Should compact status be visible as a small badge only, or should users be able
  to inspect compact summaries?
- Should Agent sessions appear in the existing History/Gallery views, or only in
  the Agent session sidebar until exported?
