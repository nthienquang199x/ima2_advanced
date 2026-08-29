---
created: 2026-05-16
status: plan
tags: [ima2-gen, agent-mode, jawdev, queue, parallel-generation, right-sidebar]
sources:
  - https://gall.dcinside.com/mgallery/board/view/?id=thesingularity&no=1182644&search_head=120&page=1
  - https://github.com/damagethundercat/ima2-gen
  - devlog/_fin/260516_agent-mode-codex-rs-workspace/
---

# Agent Mode Follow-up Jawdev Plan

## Why This Exists

`devlog/_fin/260516_agent-mode-codex-rs-workspace/` is already completed.
The current work is a follow-up lane on top of that implementation.

The live Chrome state at `http://127.0.0.1:3369/` shows that Agent Mode is
working, but the workspace is still closer to a first-pass shell than the
queue-driven image-agent workflow Jun wants.

Current visible state:

- Agent Mode is selected.
- The app has a left icon rail, chat pane, and right image pane.
- Chat turns show `ima2.get_image_context` and
  `ima2.web_search + ima2.generate_image`.
- Tool turns have one collapsible summary layer.
- Generated images appear in chat thumbs, right preview, and right variants.
- The selected session has several completed generations.
- The composer can send one prompt, but queue and batch controls are absent.

This plan turns Agent Mode from "one prompt -> one generated artifact" into a
Jaw/Codex-like image-agent workspace with stable panes, nested tool inspection,
reload-safe queue state, parallel generation, per-session progress, and a
usable right-side control surface for model, prompt library, form, quality, and
context.

## User Requirements

Jun's follow-up requirements are:

1. Restore the Agent window layout. The left-side workspace regressed from the
   intended horizontal multi-pane layout into a vertical/narrow rail layout.
2. Change tools to double-folding like cli-jaw, not a single shallow collapse.
3. Add queue behavior like cli-jaw.
4. Allow prompt/tool definitions to produce parallel image generations.
5. Add right sidebar functionality beyond prompt library: form/template,
   quality, and other generation controls.
6. Add top-right model/settings controls and make them integrate with the
   sidebar model controls.
7. Show session-specific spinners while sessions are running.

## External Product Signals

The DCInside post and fork README both point in the same direction:

- The fork shifted the product toward a prompt-centered local studio.
- Prompt Builder sessions are image-scoped.
- The user can apply Korean/English refined prompts directly.
- Prompt library insertion and ordering are important.
- Multimode/batch generation and active/recent job visibility are product
  features, not just backend internals.
- Model, quality, moderation, and provider settings are already part of the
  fork's public workflow.

Agent Mode should reuse those ideas, but not merge the fork architecture
directly. The correct implementation is modular: Agent layout, tool
presentation, queue/runtime, right sidebar, and generation settings each get
separate modules and contracts.

## Current Local Implementation Signals

Read files:

- `ui/src/components/agent/AgentWorkspace.tsx`
- `ui/src/components/agent/AgentMessage.tsx`
- `ui/src/components/agent/AgentChatPane.tsx`
- `ui/src/components/agent/AgentComposer.tsx`
- `ui/src/components/agent/AgentImagePane.tsx`
- `ui/src/hooks/useAgentWorkspaceLayout.ts`
- `ui/src/styles/agent-workspace.css`
- `ui/src/styles/agent-workspace-panels.css`
- `routes/agent.ts`
- `lib/agentRuntime.ts`
- `lib/agentStore.ts`
- `lib/agentTypes.ts`
- `lib/db.ts`
- `tests/agent-mode-frontend-contract.test.js`
- `tests/agent-mode-runtime-contract.test.ts`

Key current facts:

- `AgentWorkspace` owns all frontend session/chat/image orchestration.
- `useAgentWorkspaceLayout` switches layout by `window.innerWidth` and
  `window.innerHeight`.
- `AgentMessage` renders tool turns with one local `toolExpanded` state.
- `AgentComposer` only sends a text prompt plus web-search toggle.
- `AgentImagePane` is image context only: Image / Refs / Web / Memory.
- `routes/agent.ts` has synchronous turn execution:
  `POST /api/agent/sessions/:sessionId/turns` waits for generation.
- `lib/agentRuntime.ts` appends user/tool/assistant turns directly and calls
  `generateViaResponses` once.
- `lib/agentStore.ts` stores sessions, turns, images, references, and web
  findings, but no queue items or generation setting snapshots.
- `pendingTurnsRef` is global to the selected workspace component, not a
  per-session durable status source.

## Architecture Direction

Build Agent Mode v2 as a modular monolith inside the existing app:

```text
Agent Workspace
  ├─ Layout shell
  ├─ Chat timeline
  │   └─ Tool group renderer
  ├─ Queue client
  ├─ Right sidebar
  │   ├─ Image context
  │   ├─ Prompt library
  │   ├─ Form/templates
  │   ├─ Quality/profile
  │   └─ Model/settings
  └─ Session status projection

Server
  ├─ Agent routes
  ├─ Agent store
  ├─ Agent queue store
  ├─ Agent queue worker
  ├─ Agent generation plan parser
  ├─ Agent tool executor
  └─ Responses image adapter
```

Do not grow `AgentWorkspace.tsx`, `AgentMessage.tsx`, or
`lib/agentRuntime.ts` into god files. Keep the current compatibility exports
where needed and move new behavior behind focused modules.

## Plan Documents

This lane is split into:

- `01_current_state_and_regressions.md`
- `02_phase1_layout_and_tool_folding.md`
- `03_phase2_queue_and_parallel_runtime.md`
- `04_phase3_right_sidebar_models_and_quality.md`
- `05_pabcd_implementation_plan.md`
- `06_verification_risks_and_acceptance.md`


## Closeout (2026-07-11, 260711_production-hardening WP1-3)

잔여 스코프가 production-hardening 레인에서 구현 완료됨: durable queue/fanout/이중 접힘/세션별
spinner(기존 DONE) + 이번 라운드에서 pane preference(ima2.agentPanePreference), 모델 칩→사이드바
Model 탭 연동, Quality 세그먼트/스테퍼 UI, tool compact 계약(32/28px·3줄 clamp·400px scroll),
모바일 모드 복귀/큐 시트, 정직한 진행 표시(startedAt+progressStage), running 취소, 재시작 복구.
Refs/Web context projection과 forms/style-lock은 future scope로 disposition
(devlog/_plan/260711_production-hardening/030_implementation.md 참조). 전체 스위트 1120개 0 fail.
