# Agent Source Policy + Durable Progress RCA

## Goal

Agent Mode must behave like a normal agent while still controlling image/video tools explicitly:

- It must distinguish a fresh text-to-image request from an image-to-image/current-image reference request.
- It must let the planner/tool contract express that distinction instead of hiding it in provider runtime behavior.
- It must keep visible progress after refresh or session switch by deriving progress from durable queue state.
- It must show `running/planning` near the composer, not as a synthetic chat bubble inside the conversation.

## Observed Symptoms

1. User asks for a separate new image after an Agent session already has a current image.
2. Grok Agent generation still becomes image-to-image because the runtime automatically attaches the current image.
3. The chat shows mechanical fallback prose such as `Generated 1 image artifact. Single-image plan completed.`
4. The in-chat pending spinner disappears after selecting another session or refreshing.
5. Progress UI is visually noisy because pending state appears as a generated assistant message instead of a compact bottom status.

## Root Causes

### RC1: no source-image policy exists in the plan contract

`AgentGenerationPlan` has image/video mode, prompt count, planner source, assistant text, and video params, but no field that says whether image generation should use the current image.

Code anchor:

- `/Users/jun/Developer/new/700_projects/ima2-gen/lib/agentTypes.ts`
- `AgentGenerationPlan` has no `sourceImagePolicy`.

Effect:

- The LLM planner can decide `single` or `fanout`, but it cannot say `new image from scratch` vs `use current image as reference/edit`.
- Regex fallback cannot preserve explicit phrases such as `i2i 말고`, `새로운 방식`, `별도`, or `from scratch`.

### RC2: Grok Agent image runtime always attaches current image references

`generateAgentImage()` passes the current Agent image to Grok generation every time:

- `/Users/jun/Developer/new/700_projects/ima2-gen/lib/agentImageVideoGen.ts`
- `references: await loadAgentCurrentImageReferences(ctx, sessionId)`

Effect:

- If a session has `lastImageId`, Grok switches from `/v1/images/generations` to `/v1/images/edits`.
- The user cannot force a fresh image through natural language.
- The runtime behavior contradicts Agent-level intent.

### RC3: planner prompt declares tools but does not declare source-image semantics

`buildPlannerDeveloperPrompt()` tells the model about tools and modes, but it does not require a field for source image use.

Code anchor:

- `/Users/jun/Developer/new/700_projects/ima2-gen/lib/agentPlannerModel.ts`
- JSON schema example lacks `sourceImagePolicy`.

Effect:

- The planner is not instructed to choose between fresh T2I and i2i/current reference.
- Tool contract remains incomplete even though tools are now explicitly listed.

### RC4: progress spinner is a local-only synthetic assistant turn

`AgentWorkspace.tsx` creates a local pending assistant turn:

- `localPendingTurn()`
- `appendTurns(current, sessionId, [userTurn, pendingTurn])`
- `pendingStageText` is computed only from `turns.filter(isLocalPendingTurn)`.

Code anchor:

- `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/components/agent/AgentWorkspace.tsx`

Effect:

- `refreshWorkspace()` preserves local pending turns, but `loadWorkspace()` full-replaces state.
- Session switching calls `loadWorkspace(id)`, so the pending turn disappears.
- Browser refresh also loses local-only pending turns.
- The durable queue summary still exists, but the UI does not render progress from it.

### RC5: pending progress is rendered as chat content

`AgentMessage` and `AgentRunGroup` render `agent-message__stream-progress` inside the message/run bubble.

Code anchors:

- `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/components/agent/AgentMessage.tsx`
- `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/components/agent/AgentRunGroup.tsx`

Effect:

- The UI implies the assistant already wrote a message while the runtime is only queued/planning/running.
- On fast state changes, the conversation visually jumps.
- This conflicts with the desired cli-jaw-like bottom `running ...` pattern.

### RC6: fallback assistant prose is mechanical

`formatAgentAssistantText()` falls back to:

- `Generated 1 image artifact.`
- `Single-image plan completed.`

Code anchor:

- `/Users/jun/Developer/new/700_projects/ima2-gen/lib/agentRuntime.ts`

Effect:

- If planner/model prose is omitted, the user sees implementation-speak rather than normal agent speech.

## Existing Durable Data We Should Reuse

The backend already returns durable queue projection in workspace payload:

- `/Users/jun/Developer/new/700_projects/ima2-gen/lib/agentStore.ts`
- `/Users/jun/Developer/new/700_projects/ima2-gen/lib/agentQueueStore.ts`
- `/Users/jun/Developer/new/700_projects/ima2-gen/ui/src/components/agent/agentTypes.ts`

Available fields:

- `queueBySession`
- `runSummaryBySession`
- `AgentQueueItem.status`
- `AgentSessionRunSummary.status`
- `queuedCount`
- `runningCount`
- `lastQueueItemId`
- `lastError`

Therefore the progress fix should not invent a second client persistence layer. The UI should derive its current progress display from these durable fields and only use optimistic local state to cover the small gap before the enqueue response arrives.
