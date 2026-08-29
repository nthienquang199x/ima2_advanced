# Patch Plan

## Product Behavior

Agent Mode should treat image source use as an explicit planning decision:

- `sourceImagePolicy: "none"` means fresh image generation; ignore the current session image.
- `sourceImagePolicy: "current"` means use the current image as an edit/reference input.
- `sourceImagePolicy: "auto"` means runtime fallback, reserved for compatibility and video/source flows.

For normal image generation, the safe default is `none`. The current image should be used only when the user explicitly asks to use, edit, transform, continue from, reference, or preserve that image.

## Design Read

Surface: Korean-first developer/creative tool UI.

Vibe: dense utility console, not marketing UI. Keep the existing Agent chrome and dropdown language. Progress should feel like a command-line task status near the input, not like a fake assistant utterance.

Do:

- Reuse existing Agent composer, message list, and queue state.
- Use compact one-line status above the composer.
- Keep chat content reserved for real user/assistant/tool turns.
- Add accessible live-region status for queued/planning/running.

Do not:

- Add another card inside the chat.
- Add new decorative controls.
- Hide durable progress behind local-only transient state.

## Backend Changes

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/lib/agentTypes.ts`

Add:

```ts
export type AgentSourceImagePolicy = "auto" | "none" | "current";
```

Extend `AgentGenerationPlan`:

```ts
sourceImagePolicy?: AgentSourceImagePolicy | null;
```

Rationale:

- This is the shared server contract for planner, queue item persistence, runtime, and UI payload typing.
- Optional preserves the shape of old queue items at parse time. Runtime policy for missing legacy values is specified below so old persisted items do not crash.

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/components/agent/agentTypes.ts`

Mirror the backend type:

```ts
export type AgentSourceImagePolicy = "auto" | "none" | "current";
```

Extend frontend `AgentGenerationPlan`:

```ts
sourceImagePolicy?: AgentSourceImagePolicy | null;
```

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/lib/agentToolManifest.ts`

Add `sourceImagePolicy` to `ima2.generate_image` parameters:

```json
{
  "sourceImagePolicy": {
    "type": "string",
    "enum": ["auto", "none", "current"],
    "description": "none creates a fresh image and ignores the current session image; current uses the current session image as edit/reference input; auto lets the runtime choose."
  }
}
```

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/lib/agentPlannerModel.ts`

Update the developer prompt:

- JSON example includes `"sourceImagePolicy":"none|current|auto"`.
- For image modes, require the field.
- Rules:
  - Use `"none"` for `새로`, `별도`, `i2i 말고`, `새로운 방식`, `from scratch`, `new image`, `without reference`, or when the user simply asks for a new image.
  - Use `"current"` only when the user explicitly asks to use/edit/modify/transform/reference the current image or says `이 이미지`, `현재 이미지`, `방금 그거`, `참조`, `reference`, `i2i`, `image-to-image`, `유지해서`.
  - Use `"auto"` only for compatibility when source use is genuinely ambiguous.

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/lib/agentGenerationPlanner.ts`

Add source policy cleaning and fallback inference:

```ts
function cleanSourceImagePolicy(value: unknown): AgentSourceImagePolicy | null
function inferSourceImagePolicy(prompt: string, mode: AgentGenerationPlan["mode"]): AgentSourceImagePolicy | null
```

Apply the inference in both paths:

- `deriveAgentGenerationPlan()` must set `sourceImagePolicy` on every returned generation plan.
- `normalizeAgentGenerationPlan()` must preserve a valid planner-provided policy; otherwise it must infer the policy for normalized plans.
- When `normalizeAgentGenerationPlan()` falls back to `deriveAgentGenerationPlan()` because prompts are empty, the derived plan must already include policy.

Expected fallback:

- Fresh/new phrases -> `none`.
- Explicit current/reference/edit phrases -> `current`.
- Plain `single`/`fanout` image requests -> `none`.
- `video` keeps `auto` so existing image-to-video continuity is not silently broken.
- `question`/`errors` -> `null`.

Persisted queue items with missing policy:

- If a stored queue item has no `sourceImagePolicy`, `normalizeAgentGenerationPlan()` must infer from prompt.
- This intentionally favors the new safe default over pre-patch implicit i2i behavior: plain image prompts infer `none`; explicit current/reference/edit prompts infer `current`; video infers `auto`.
- `runAgentGenerationPlan()` should still have a defensive fallback for malformed caller-created plans, but that fallback should be `"none"` for image generation and `"auto"` only for video.

`normalizeAgentGenerationPlan()` must preserve planner-provided valid policy. When invalid or missing, it must infer.

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/lib/agentRuntime.ts`

Extend `AgentRunOptions`:

```ts
sourceImagePolicy?: AgentSourceImagePolicy | null;
```

When running image generation, pass:

```ts
sourceImagePolicy: plan.sourceImagePolicy ?? "none"
```

Keep video source behavior unchanged unless a future plan adds video source policy.
Also update the direct `runAgentTurn()` inline plan so it includes `sourceImagePolicy: "none"` for the synchronous `/api/agent/sessions/:id/turns` route. The queued UI path uses planner/derive plans, but runtime tests and direct API callers still exercise `runAgentTurn()`.

Improve `formatAgentAssistantText()` fallback:

- If no planner/model text exists, return natural short prose.
- Add `prompt: string` to the function signature, or use the first non-empty value from `[prompt, ...plan.prompts]` at the callsite; do not infer language from `reason`.
- Korean detection should use a simple Hangul test such as `/[\uAC00-\uD7AF]/u` against that prompt text.
- Korean prompt -> `이미지 생성이 완료됐어요.` or `이미지 N장을 생성했어요.`
- Non-Korean prompt -> `Done — I generated the image.` or `Done — I generated N images.`
- Do not include internal terms like `artifact`, `plan completed`, or `fanout`.

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/lib/agentImageVideoGen.ts`

Change:

```ts
loadAgentCurrentImageReferences(ctx, sessionId)
```

to:

```ts
loadAgentCurrentImageReferences(ctx, sessionId, policy)
```

Behavior:

- `policy === "none"` -> return `[]`.
- `policy === "current"` -> load the current session image if available.
- `policy === "auto"` -> current behavior for backward compatibility.

`generateAgentImage()` passes `options.sourceImagePolicy ?? "none"` to the loader. New image plans get `"none"` from planner/derive, and missing image plans also fail safe to fresh generation.

Add a small log event with policy and whether references were attached, without logging image data.

## Frontend Changes

### NEW `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/components/agent/agentLocalTurns.ts`

Move local turn ownership out of `AgentWorkspace.tsx`:

- `LOCAL_TURN_PREFIX`
- `PENDING_TURN_PREFIX`
- `isLocalTurn()`
- `isLocalPendingTurn()`
- `localUserTurn()`
- `localPendingTurn()` only if still needed for a short pre-enqueue bridge.
- `localErrorTurn()`

Reason:

- `AgentWorkspace.tsx` is already at the 500-line limit.
- Progress helper and workspace should not duplicate local turn prefix logic.

### NEW `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/components/agent/agentRunProgress.ts`

Pure helper:

```ts
export type AgentRunProgress = {
  active: boolean;
  status: "queued" | "planning" | "running" | "error";
  labelKey: "pendingQueued" | "pendingPlanning" | "pendingGenerating" | "runError";
  queuedCount: number;
  runningCount: number;
  lastError?: string | null;
};

export function deriveAgentRunProgress(args: {
  turns: AgentTurn[];
  queueItems: AgentQueueItem[];
  runSummary?: AgentSessionRunSummary | null;
  localPendingCount: number;
}): AgentRunProgress | null
```

Rules:

- `runSummary.status === "queued"` -> active queued.
- `runSummary.status === "running"`:
  - if no server tool turn exists after the current queue started -> planning.
  - otherwise running/generating.
- `runSummary.status === "error"` -> error if `lastError`.
- `localPendingCount > 0` before queue response -> planning.
- No active state -> `null`.

Sorting/age:

- Use the newest active queue item createdAt/startedAt if available.
- If missing, fall back to local pending.

### NEW `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/components/agent/AgentRunStatusBar.tsx`

Render one compact line above the composer:

- Spinner/dots at left.
- Label text from i18n.
- Optional counts: `1 running`, `2 queued`, short and muted.
- `role="status"` and `aria-live="polite"`.

No card nesting. No message bubble.

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/components/agent/AgentWorkspace.tsx`

Changes:

- Import local turn helpers from `agentLocalTurns.ts`.
- Import `deriveAgentRunProgress`.
- Stop mapping local pending turns into `displayTurns`.
- `displayTurns` filters out local pending turns so pending progress is not chat content.
- Pass `runProgress` into `AgentChatPane`.
- Use `runSummaryBySession`/`queueBySession` to recover progress after `loadWorkspace()` full replace.
- Keep optimistic local user turn.
- Keep a local pending turn only as a pre-enqueue bridge for `localPendingCount`; it must not render in `displayTurns`.
- Keep error turn for enqueue failure.

Important:

- `loadWorkspace(id)` can still full-replace state; progress remains visible because it comes from server queue projection.
- `refreshWorkspace()` can continue preserving local optimistic turns.

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/components/agent/AgentChatPane.tsx`

Add prop:

```ts
runProgress: AgentRunProgress | null;
```

Render:

```tsx
<AgentRunStatusBar progress={runProgress} />
<AgentComposer ... />
```

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/components/agent/AgentMessage.tsx`

Remove in-message streaming dots if no longer needed for synthetic pending turns. Keep `aria-busy` behavior only for real streaming turns if any remain.

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/components/agent/AgentRunGroup.tsx`

Remove or de-emphasize `agent-message__stream-progress` inside assistant run steps. Tool details stay folded in the existing one-line tool summary.

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/styles/agent-panels-composer.css`

Add compact status bar styles:

- `.agent-run-status`
- `.agent-run-status__spinner`
- `.agent-run-status__meta`

Constraints:

- Stable height.
- Does not resize composer.
- Works on mobile width.
- Uses existing CSS variables.
- Respects `prefers-reduced-motion`.

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/styles/agent-workspace-panels.css`

Remove or leave only compatibility styling for in-message streaming dots if no code path uses it. Existing tool fold styles must remain.

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/i18n/ko.json`

Reuse existing `pendingQueued`, `pendingPlanning`, and `pendingGenerating` copy for the status bar. `AgentRunProgress.labelKey` stores the short key without the `agent.` prefix and `AgentRunStatusBar` calls `t(\`agent.${progress.labelKey}\`)`. Add only the missing error key:

```json
"runError": "실행 중 오류가 발생했어요"
```

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/i18n/en.json`

Reuse existing `pendingQueued`, `pendingPlanning`, and `pendingGenerating` copy for the status bar. `AgentRunProgress.labelKey` stores the short key without the `agent.` prefix and `AgentRunStatusBar` calls `t(\`agent.${progress.labelKey}\`)`. Add only the missing error key:

```json
"runError": "Run failed"
```

## Documentation Changes

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/structure/03-server-api.md`

Document Agent source policy:

- Agent image generation defaults to fresh T2I.
- Current image is attached only when planner/command says `sourceImagePolicy: "current"`.
- Existing Grok video auto-I2V remains unchanged.

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/structure/04-frontend-architecture.md`

Document Agent progress UI:

- Durable queue projection drives composer-adjacent run status.
- Chat message list excludes synthetic pending assistant turns.

## Build Artifact Changes

After TypeScript source changes:

- Run `npm run build:server`.
- Commit generated JS artifacts that the build updates, but do not hand-edit generated JS.

## Non-Goals

- Do not change Grok video provider.
- Do not add a new sidebar/dropdown design.
- Do not change moderation policy in this patch.
- Do not push.
- Do not stage existing unrelated `package-lock.json` or `site/package-lock.json` changes.
