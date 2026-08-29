# Test Plan

## Backend Contract Tests

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/tests/agent-mode-llm-planner-contract.test.ts`

Add assertions:

- Tool manifest includes `sourceImagePolicy` in `ima2.generate_image`.
- Planner developer prompt includes the JSON field.
- Prompt rules explicitly distinguish:
  - fresh/new/no-i2i -> `none`
  - current/reference/edit/i2i -> `current`
- `normalizeAgentGenerationPlan()` preserves valid planner-provided source policy.

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/tests/agent-mode-auto-planner-contract.test.ts`

Add fallback cases:

- `i2i 말고 새로운 방식으로 생성` -> `sourceImagePolicy === "none"`.
- `새로 별도 이미지 하나` -> `sourceImagePolicy === "none"`.
- `이 이미지 스타일 유지해서 다시 만들어줘` -> `sourceImagePolicy === "current"`.
- Plain image request -> `sourceImagePolicy === "none"`.
- Video request -> `sourceImagePolicy === "auto"` and existing video param extraction still works.
- Missing-policy persisted image plans also infer from the prompt instead of preserving old implicit i2i behavior.

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/tests/agent-mode-runtime-contract.test.ts`

Add/adjust Grok runtime assertions:

- A Grok Agent image request with a current image and `sourceImagePolicy: "none"` calls `/v1/images/generations`.
- It does not send `image`/reference payload to `/v1/images/edits`.
- A Grok Agent image request with `sourceImagePolicy: "current"` and a current image calls `/v1/images/edits`.
- `model: "grok-4.3"` remains planner-only and never becomes the image model.
- Replace the existing mechanical fallback assertion at `tests/agent-mode-runtime-contract.test.ts` that expects `Generated 1 image artifact.` with a natural fallback assertion. The test should assert that assistant text does not contain `Generated 1 image artifact.`, `Single-image plan completed.`, or `Fanout used`.
- Add a direct `/turns` or `runAgentTurn()` assertion that its inline plan defaults to `sourceImagePolicy: "none"` and does not attach the current image for Grok unless a full planner-derived plan says `current`.
- Add one Korean fallback prose assertion using the `/[\uAC00-\uD7AF]/u` language rule.

If route-level tests cannot easily inject policy, use direct `runAgentGenerationPlan()` or queue plan persistence with a mocked fetch. Prefer behavior-level proof over source-string only.

## Frontend Contract Tests

### MODIFY `/Users/jun/Developer/new/700_projects/ima2-gen/tests/agent-mode-frontend-contract.test.js`

Replace the old pending-bubble assertions:

- `AgentWorkspace` still creates an optimistic local user turn.
- `AgentWorkspace` imports `deriveAgentRunProgress`.
- `displayTurns` filters `isLocalPendingTurn`.
- `AgentChatPane` receives `runProgress`.
- `AgentRunStatusBar` is rendered above `AgentComposer`.
- The message list remains `aria-live="polite"`.
- The old requirement that `AgentMessage` renders `agent-message__stream-progress` inside chat is removed.

### NEW `/Users/jun/Developer/new/700_projects/ima2-gen/tests/agent-mode-run-progress-contract.test.ts`

Behavior tests for pure helper:

- queued summary -> queued status.
- running summary before any server tool/assistant turn -> planning status.
- running summary after server tool turn -> running status.
- running summary after only a planner prelude assistant turn, with no tool turn yet -> still planning status.
- full workspace reload with no local pending but active run summary -> active progress still returned.
- idle summary and no local pending -> `null`.
- error summary with lastError -> error progress.

Run with:

```bash
node --import tsx --test tests/agent-mode-run-progress-contract.test.ts
```

## Verification Commands

Targeted first:

```bash
node --import tsx --test \
  tests/agent-mode-auto-planner-contract.test.ts \
  tests/agent-mode-llm-planner-contract.test.ts \
  tests/agent-mode-runtime-contract.test.ts \
  tests/agent-mode-run-progress-contract.test.ts

node --test tests/agent-mode-frontend-contract.test.js
```

Then full gates:

```bash
npm run typecheck
npm run typecheck:tests
npm run build:server
npm run ui:build
npm test
```

Inventory:

```bash
npm run test:inventory
```

## Visual / Browser Smoke

Use the local server at `http://127.0.0.1:3333` after rebuilding/restarting if needed.

Smoke checks:

- Agent mode opens.
- Send a prompt; the user turn appears, but the pending assistant bubble does not.
- A compact `Planning the response` / `Running tools` status appears above the composer.
- Switching away from the session and back keeps the status visible while the queue item is active.
- Refreshing while a queue item is active still shows progress from durable queue projection.
- File attach button and paste still route through `onAttachFiles`.

## Expected Commit Shape

Commit in small units:

1. Planner/runtime source-image policy.
2. Durable progress helper + composer status UI.
3. Tests/docs/build artifacts.

Do not include unrelated existing lockfile modifications.
