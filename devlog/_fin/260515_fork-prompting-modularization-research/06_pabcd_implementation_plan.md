---
title: "PABCD Implementation Plan — Prompt Studio Full (Audit-Revised)"
status: A / audit-revised, awaiting user approval
created: 2026-05-15
revised: 2026-05-15 (post-audit)
project_root: /Users/jun/Developer/new/700_projects/ima2-gen
fork_clone: /tmp/ima2-gen-damagethundercat
tags: [pabcd, prompt-builder, workspace-profile, composer, layout, viewer, cli]
baseline:
  tests: 692 pass / 0 fail
  version: v1.1.11
  commit: 3e09dcf
audit_fixes:
  - "Fork line range 전부 교정 (actual functional boundaries)"
  - "promptBuilderSystemPrompt.ts (135줄) 누락 → 추가"
  - "ESM directory resolution 문제 → prompt.ts는 파일 유지, 하위 모듈은 prompt-sub/ 디렉토리"
  - "listHistoryRows() 필드 추출 명시"
  - "Store selector dual-import 매핑 테이블 추가"
  - "setPromptLibraryOpen → upstream에 추가 또는 toggle 패턴 유지 결정"
  - "Slice D scope 확대 (type migration + composePrompt rewrite)"
  - "showHistorySequence action Slice G에 추가"
  - "--canvas-empty-dot-rgb CSS variable Slice H에 추가"
  - "Business Q1 결정: OAuth-only MVP"
  - "api.ts 패턴 교정: jsonFetch (not jsonPost)"
  - "i18n 키 수 교정: ~32개"
  - "SettingsWorkspace 삽입 위치 명시"
---

# PABCD Implementation Plan — Prompt Studio Full (Audit-Revised)

## Business Logic Decisions (audit에서 블로커로 식별됨)

| Question | Decision | Rationale |
|---|---|---|
| Q1: OAuth vs API | **OAuth-only MVP** | fork가 OAuth-only, API transport는 `PROMPT_BUILDER_PROVIDER_UNSUPPORTED` 리턴 |
| Q2: Session auto-save | **Auto-save in sidecar** | generation 시 composer metadata 자동 기록, 별도 save API 불필요 |
| Q3: Default placement | **기존 library → before, builder insert → after** | fork 기본값 따름 |
| Q4: Profile storage | **browser localStorage only** | server-side route 불필요, `persistenceRegistry.ts` 패턴 사용 |

---

## Strategy: Import + Modularize

Fork clone: `/tmp/ima2-gen-damagethundercat`

### Fork Import Map (audit-revised)

| Fork Source | Lines | Upstream Target | Modularization |
|---|---|---|---|
| `lib/promptBuilderClient.ts` | 534 | `lib/promptBuilder/` (11 files) | 아래 corrected mapping 참조 |
| `lib/promptBuilderSystemPrompt.ts` | 135 | `lib/promptBuilder/systemPrompt.ts` | 거의 그대로 사용 |
| `PromptBuilderPanel.tsx` | 336 | `components/prompt-builder/` (8 files) | 컴포넌트 분할 |
| `promptBuilderStructuredOutput.ts` | 72 | `lib/promptBuilder/structuredOutput.ts` | 거의 그대로 |
| `SidebarHistory.tsx` | 246 | `components/history/` (3 files) + `lib/history/` (1 file) | grouping 순수함수 추출 |
| `ClassicWorkspace.tsx` | 15 | `components/classic/ClassicWorkspace.tsx` | 그대로 |
| `ResultDockPanel.tsx` | 70 | `components/classic/ResultDockPanel.tsx` | 그대로 |
| `Canvas.tsx` zoom/pan | ~250 추가분 | `hooks/useViewerTransform.ts` + `viewer/` (3 files) | hook + component 추출 |
| `RightPanel.tsx` diff | +9 lines | 직접 수정 | builder stack + setPromptLibraryOpen 추가 |
| `PromptComposer.tsx` diff | +157 lines | `components/composer/` (4 files) | flow/block 추출 |
| CSS 4종 | 164 rules | `styles/` (4 files) | fork index.css에서 추출 |
| `useAppStore.ts` builder state | ~200 추가분 | `store/promptBuilderStore.ts` (별도 Zustand) | 아래 dual-store mapping 참조 |

---

## Slice A — Prompt Builder Backend

### Fork `promptBuilderClient.ts` Corrected Functional Mapping

```text
Fork actual range    Content                           Upstream module
─────────────────────────────────────────────────────────────────────────
1-12                 imports + constants                lib/promptBuilder/constants.ts
13-115               9 type definitions                 lib/promptBuilder/types.ts
116-129              promptBuilderError() +             lib/promptBuilder/errors.ts
                     normalizeModel()                   lib/promptBuilder/requestSchema.ts
130-157              normalizeMessages()                lib/promptBuilder/requestSchema.ts
159-191              normalizeAttachments()             lib/promptBuilder/attachments.ts
193-226              contextText() + attachmentText()   lib/promptBuilder/context.ts
228-262              toChatContent() +                  lib/promptBuilder/transport.ts
                     toResponsesContent() +              (payload formatting)
                     hasImageAttachments()
264-329              parseUpstreamError() +             lib/promptBuilder/responseParser.ts
                     responseSummary()
331-425              SSE helpers + extractChatText +    lib/promptBuilder/responseParser.ts
                     extractResponsesText +              (response reading — larger than initially planned)
                     readResponsesStream/Result
427-534              requestPromptBuilderChat()         lib/promptBuilder/client.ts
                     (single export: orchestration)      (validate→context→transport→parse pipeline)
```

### Fork `promptBuilderSystemPrompt.ts` (135줄) — 별도 파일로 존재!

```text
Fork file: lib/promptBuilderSystemPrompt.ts
  → Upstream: lib/promptBuilder/systemPrompt.ts
  거의 그대로 사용. "ima2-genX" 문자열만 "ima2-gen"으로 교체.
```

### NEW Files

```text
lib/promptBuilder/constants.ts       (~20줄)  model allowlist, limits, timeout, max tokens
lib/promptBuilder/types.ts           (~70줄)  PromptBuilderRole/Message/Context/Attachment/Request/Error types
lib/promptBuilder/errors.ts          (~40줄)  promptBuilderError() factory — lib/promptImport/errors.ts 패턴 따름
lib/promptBuilder/requestSchema.ts   (~60줄)  normalizeModel() + normalizeMessages()
lib/promptBuilder/attachments.ts     (~50줄)  normalizeAttachments() — fork lines 159-191
lib/promptBuilder/context.ts         (~50줄)  contextText() + attachmentText() — fork lines 193-226
lib/promptBuilder/systemPrompt.ts    (~135줄) fork promptBuilderSystemPrompt.ts 거의 그대로
lib/promptBuilder/transport.ts       (~80줄)  toChatContent/toResponsesContent + fetchOAuth call
lib/promptBuilder/responseParser.ts  (~120줄) SSE helpers + text extraction + responseSummary — fork lines 264-425
lib/promptBuilder/client.ts          (~80줄)  requestPromptBuilderChat() — fork lines 427-534 기반
routes/promptBuilder.ts              (~80줄)  POST /api/prompt-builder/chat
tests/prompt-builder-contract.test.ts (~150줄)
```

### MODIFY `routes/index.ts`

```diff
+import { registerPromptBuilderRoutes } from "./promptBuilder.js";
 ...
+  registerPromptBuilderRoutes(app, ctx);
```

### Error Code Pattern

`lib/promptImport/errors.ts` 패턴 따름: class + factory + code + status.
`errInfo()` (`lib/errInfo.ts`)와 호환. `PROMPT_BUILDER_*` namespace.

---

## Slice B — Prompt Builder CLI

### ⚠️ ESM Resolution Fix (audit critical finding)

`bin/ima2.ts:474`의 `import("./commands/${command}.js")` 패턴 때문에
`prompt.ts`를 디렉토리(`prompt/index.ts`)로 변환할 수 없음.

**수정된 전략:** `prompt.ts`는 파일로 유지하고, 하위 모듈을 `prompt-sub/` 디렉토리에 배치.

```text
bin/commands/prompt.ts                  MODIFY → dispatcher/help only (~120줄)
bin/commands/prompt-sub/library.ts      NEW → 기존 ls/show/create/edit/rm/favorite/export 이동 (~200줄)
bin/commands/prompt-sub/folders.ts      NEW → 기존 folder subcommands 이동 (~80줄)
bin/commands/prompt-sub/importCmd.ts    NEW → 기존 import subcommands 이동 (~150줄)
bin/commands/prompt-sub/build.ts        NEW → prompt build 구현 (~100줄)
tests/cli-prompt-builder-contract.test.js NEW (~80줄)
```

`prompt.ts`의 `SUB` map (현재 line 464-474)이 submodule을 dynamic import:
```ts
const handler = await import("./prompt-sub/build.js");
```

### MODIFY `lib/capabilities.ts`, `skills/ima2/SKILL.md`

promptBuilder 블록 추가 (변경 없음).

---

## Slice C — Prompt Builder Frontend

### ⚠️ Dual-Store Selector Mapping (audit critical finding)

Fork `PromptBuilderPanel.tsx`가 사용하는 18개 selector의 upstream store 매핑:

```text
Selector                           Source Store            Notes
──────────────────────────────────────────────────────────────────
promptBuilderMessages              usePromptBuilderStore   NEW store
promptBuilderScope                 usePromptBuilderStore   NEW store
promptBuilderDraft                 usePromptBuilderStore   NEW store
promptBuilderModel                 usePromptBuilderStore   NEW store
promptBuilderLoading               usePromptBuilderStore   NEW store
promptBuilderAttachments           usePromptBuilderStore   NEW store
setPromptBuilderDraft              usePromptBuilderStore   NEW store
setPromptBuilderModel              usePromptBuilderStore   NEW store
sendPromptBuilderMessage           usePromptBuilderStore   NEW store
addPromptBuilderAttachments        usePromptBuilderStore   NEW store
removePromptBuilderAttachment      usePromptBuilderStore   NEW store
clearPromptBuilderImageScope       usePromptBuilderStore   NEW store
clearPromptBuilderMessages         usePromptBuilderStore   NEW store
─── above: NEW store (13개) ─── below: existing useAppStore (5개) ───
currentImage                       useAppStore             기존
history                            useAppStore             기존
setPrompt                          useAppStore             기존
insertPromptToComposer             useAppStore             기존 (placement 필드 추가 필요)
showToast                          useAppStore             기존
```

에이전트 주의: fork 코드에서 `useAppStore((s) => s.promptBuilder*)` 패턴을
`usePromptBuilderStore((s) => s.*)` 로 전부 교체해야 함.

### ⚠️ setPromptLibraryOpen 추가 필요 (audit finding)

Fork RightPanel이 `setPromptLibraryOpen(true/false)` 사용.
Upstream은 `togglePromptLibrary`만 있음.

수정: `useAppStore`에 `setPromptLibraryOpen: (open: boolean) => void` 추가 (~3줄).
기존 `togglePromptLibrary`는 유지 (다른 곳에서 사용).

### MODIFY `ui/src/lib/api.ts` (audit fix: jsonFetch 패턴)

```diff
+export async function postPromptBuilderChat(body: PromptBuilderChatRequest): Promise<PromptBuilderChatResponse> {
+  return jsonFetch<PromptBuilderChatResponse>("/api/prompt-builder/chat", {
+    method: "POST",
+    headers: { "Content-Type": "application/json" },
+    body: JSON.stringify(body),
+  });
+}
```

### i18n (audit fix: ~32 keys)

Fork에 이미 `promptBuilder.*` 28키 + `viewer.*` 4키 = 총 ~32키 존재.
Fork `en.json`, `ko.json`에서 해당 블록 복사.

### NEW Files (변경 없음)

```text
ui/src/store/promptBuilderStore.ts                           (~200줄)
ui/src/components/prompt-builder/ (8 files)
ui/src/lib/promptBuilder/ (4 files including structuredOutput.ts)
ui/src/styles/prompt-builder.css                              (~150줄)
tests/ (2 files)
```

---

## Slice D — Composer Block Ordering + History Restore

### ⚠️ Scope 확대 (audit critical finding: "~30줄" → ~80줄+)

Plan이 "useAppStore ~30줄 추가"라고 했지만 실제 필요한 변경:

```text
useAppStore.ts 변경 목록:
1. InsertedPrompt type에 placement?: "before" | "after" 추가    (~3줄)
2. composerBlocks → insertedPrompts에 placement 반영             (~5줄)
3. moveInsertedPromptInComposer action 추가                      (~20줄)
4. composePrompt() 함수 재작성: before/main/after 순서            (~15줄)
5. restoreComposerFromHistory action 추가                        (~15줄)
6. insertPromptToComposer에 placement param 지원                 (~5줄)
                                                         합계: ~63줄
```

### ⚠️ listHistoryRows() 필드 추출 명시 (audit finding)

`lib/historyList.ts:31-71` `listHistoryRows()`에서 sidecar metadata를
읽을 때 명시적으로 새 필드를 추출해야 함:

```diff
// lib/historyList.ts — listHistoryRows() 내부의 field 추출 목록에 추가:
+composerPrompt: meta.composerPrompt ?? null,
+composerInsertedPrompts: meta.composerInsertedPrompts ?? null,
```

이것 없이 sidecar에만 쓰면 history API response에서 새 필드가 drop됨.

### MODIFY `routes/generate.ts` + `routes/multimode.ts`

sidecar meta 리터럴에 추가:
```diff
+composerPrompt: req.body.composerPrompt ?? null,
+composerInsertedPrompts: req.body.composerInsertedPrompts ?? null,
```

### NEW Files (변경 없음)

```text
ui/src/components/composer/ (4 files)
ui/src/hooks/ (2 files)
ui/src/lib/composerPrompt.ts
ui/src/styles/composer-flow.css
tests/ (2 files)
```

---

## Slice E — Workspace Profile Settings

### ⚠️ SettingsWorkspace 삽입 위치 명시 (audit finding)

`SettingsWorkspace.tsx:15` `SETTINGS_SECTIONS` 배열:
`["account", "generation", "appearance", "language", "future"]`

Workspace profile → `"appearance"` 뒤, `"language"` 앞에 삽입:
`["account", "generation", "appearance", "workspace", "language", "future"]`

### NEW Files (변경 없음)

```text
ui/src/lib/workspaceProfile.ts
ui/src/components/settings/WorkspaceProfileSettings.tsx
tests/workspace-profile-settings-contract.test.js
```

---

## Slice F — Classic Layout + Right Panel Tabs

변경 없음. Fork `ClassicWorkspace.tsx`(15줄) + `ResultDockPanel.tsx`(70줄) 그대로.

---

## Slice G — Sidebar History + Grouped Multimode Cards

### ⚠️ showHistorySequence action 추가 (audit finding)

Fork `SidebarHistory.tsx:61`이 사용하는 `showHistorySequence` action이
upstream `useAppStore`에 없음.

```text
useAppStore.ts 추가:
1. showHistorySequence: (sequenceId: string) => void     (~15줄)
2. trashHistorySequence: (sequenceId: string) => void     (~15줄)
                                                    합계: ~30줄
```

---

## Slice H — Viewer Zoom/Pan + Empty State

### ⚠️ --canvas-empty-dot-rgb CSS variable 추가 (audit finding)

Fork `Canvas.tsx:52`에서 사용하는 CSS variable이 upstream에 없음.
`ui/src/styles/viewer-workflow.css`에 추가:

```css
:root {
  --canvas-empty-dot-rgb: 245, 247, 250;
  --canvas-empty-dot-alpha-scale: 1;
}
[data-theme="dark"] {
  --canvas-empty-dot-rgb: 40, 42, 48;
}
```

---

## Slice I — Documentation + Attribution

변경 없음.

---

## Implementation Order (변경 없음)

```text
Phase 1: Slice A → Slice B (Backend + CLI)
Phase 2: Slice E → Slice C (Settings + Frontend)
Phase 3: Slice D → Slice G (Composer + History)
Phase 4: Slice F → Slice H (Layout + Viewer)
Phase 5: Slice 0 → Slice I (Issues + Docs)
```

## File Count Summary (revised)

| Category | NEW | MODIFY |
|---|---|---|
| Backend (lib/promptBuilder/) | 11 (+1 systemPrompt) | 0 |
| Route | 1 | 1 |
| CLI (bin/commands/prompt-sub/) | 4 (+prompt.ts refactor) | 2 |
| Frontend store | 1 | 2 |
| Frontend prompt-builder/ | 8 | 0 |
| Frontend composer/ | 4 | 1 |
| Frontend classic/ | 2 | 2 |
| Frontend history/ | 3 | 1 |
| Frontend viewer/ | 3 | 1 |
| Frontend hooks | 3 | 0 |
| Frontend lib | 9 | 3 |
| Frontend styles | 4 | 1 |
| Settings | 2 | 2 |
| i18n | 0 | 2 |
| Tests | 14 | 3 |
| Docs | 0 | 3 |
| **Total** | **69** | **24** |

## Verification Plan (변경 없음)

Baseline: 692 tests. 예상 최종: ~740+ tests.
