---
created: 2026-05-15
tags: [diff-plan, modularization, prompt-builder, frontend, backend]
status: proposed
---

# Modularization Plan

## Design Principle

Treat the fork as a product spike. Port the workflows, not the architecture.

The fork proves that a prompt-builder-centered workflow is useful, but its implementation spreads across a huge store file and large CSS file. Upstream should ship the same value with feature modules, pure helpers, explicit boundaries, and focused tests.

## Slice 1 — Prompt Builder Backend

### User-Facing Goal

Users can ask an embedded prompt builder to refine an idea, analyze references, and return a structured Korean/English prompt without leaving the app.

### New Files

```text
lib/promptBuilder/constants.ts
lib/promptBuilder/types.ts
lib/promptBuilder/errors.ts
lib/promptBuilder/requestSchema.ts
lib/promptBuilder/context.ts
lib/promptBuilder/attachments.ts
lib/promptBuilder/systemPrompt.ts
lib/promptBuilder/responseParser.ts
lib/promptBuilder/transport.ts
lib/promptBuilder/client.ts
routes/promptBuilder.ts
tests/prompt-builder-contract.test.ts
```

### Existing Files To Modify

```text
routes/index.ts
lib/oauthProxy/runtime.ts
docs/migration/runtime-test-inventory.md
```

### Why Split This Way

Fork `lib/promptBuilderClient.ts` currently holds validation, attachment normalization, transport selection, SSE parsing, and error mapping in one 534-line file. Upstream should keep each concern testable:

- `requestSchema.ts`: validate model/messages/context shape.
- `attachments.ts`: normalize image/text/file attachments, caps, data URLs.
- `context.ts`: turn current app context into prompt-builder context text.
- `transport.ts`: choose OAuth chat vs OAuth Responses; leave API transport extension point.
- `responseParser.ts`: extract chat text, Responses text, usage, and response summaries.
- `errors.ts`: stable public error codes and `errInfo` mapping.
- `client.ts`: orchestration only.

### API Shape

```http
POST /api/prompt-builder/chat
Content-Type: application/json
```

Request:

```json
{
  "model": "gpt-5.5",
  "messages": [
    {
      "role": "user",
      "content": "make this prompt more specific",
      "attachments": []
    }
  ],
  "context": {
    "currentPrompt": "...",
    "insertedPrompts": [{ "name": "Texture", "text": "..." }],
    "currentResultPrompt": "...",
    "settings": {
      "quality": "high",
      "size": "1536x1024",
      "mode": "auto"
    }
  }
}
```

Response:

```json
{
  "provider": "oauth",
  "model": "gpt-5.5",
  "message": {
    "role": "assistant",
    "content": "Brief Intent Summary:\n...\n\nFinal Prompt - Korean:\n...\n\nFinal Prompt - English:\n..."
  },
  "usage": {}
}
```

### Error Codes

Use stable route-level errors:

```text
PROMPT_BUILDER_BAD_MODEL
PROMPT_BUILDER_BAD_MESSAGES
PROMPT_BUILDER_EMPTY_MESSAGE
PROMPT_BUILDER_ATTACHMENT_TOO_LARGE
PROMPT_BUILDER_UPSTREAM_FAILED
PROMPT_BUILDER_EMPTY_RESPONSE
PROMPT_BUILDER_TIMEOUT
PROMPT_BUILDER_OAUTH_UNAVAILABLE
PROMPT_BUILDER_PROVIDER_UNSUPPORTED
```

### Model Policy

Initial MVP can be OAuth-only because the fork uses OAuth proxy paths. However, do not hardcode the feature as forever OAuth-only:

```ts
type PromptBuilderProvider = "oauth" | "api";
```

MVP may reject `"api"` with `PROMPT_BUILDER_PROVIDER_UNSUPPORTED` if needed, but the transport interface should not block a future API-key path.

### Security / Privacy Constraints

- Never log attachment payload data URLs.
- Cap message count and message length.
- Cap attachments count and text attachment size.
- Strip image data from persisted sessions.
- Use allowlist model validation.
- Use explicit timeout and return 504 on timeout.
- Do not expose hidden system prompt through the client.

### Tests

Minimum tests:

- Text-only request uses chat-completions path through OAuth.
- Image attachment request uses Responses path with `input_image`.
- Bad model fails before upstream.
- Empty messages fail before upstream.
- Upstream non-2xx maps to `PROMPT_BUILDER_UPSTREAM_FAILED` without leaking full upstream body.
- Empty upstream output maps to `PROMPT_BUILDER_EMPTY_RESPONSE`.
- Timeout maps to `PROMPT_BUILDER_TIMEOUT`.

## Slice 2 — Prompt Builder Frontend Module

### User-Facing Goal

Users see a Prompt Builder panel, chat with it, attach images/text, get structured Korean/English prompt cards, and apply or insert those prompts into the composer.

### New Files

```text
ui/src/components/prompt-builder/PromptBuilderPanel.tsx
ui/src/components/prompt-builder/PromptBuilderHeader.tsx
ui/src/components/prompt-builder/PromptBuilderMessageList.tsx
ui/src/components/prompt-builder/PromptBuilderMessage.tsx
ui/src/components/prompt-builder/PromptBuilderStructuredPromptCard.tsx
ui/src/components/prompt-builder/PromptBuilderComposer.tsx
ui/src/components/prompt-builder/PromptBuilderAttachments.tsx
ui/src/components/prompt-builder/PromptBuilderModelMenu.tsx
ui/src/components/prompt-builder/PromptBuilderScopeBadge.tsx
ui/src/lib/promptBuilder/structuredOutput.ts
ui/src/lib/promptBuilder/attachments.ts
ui/src/lib/promptBuilder/scope.ts
ui/src/lib/promptBuilder/sessionPersistence.ts
ui/src/store/promptBuilderStore.ts
tests/prompt-builder-ui-contract.test.js
tests/prompt-builder-structured-output.test.ts
```

### Existing Files To Modify

```text
ui/src/lib/api.ts
ui/src/components/RightPanel.tsx
ui/src/components/PromptLibraryPanel.tsx
ui/src/i18n/en.json
ui/src/i18n/ko.json
ui/src/store/persistenceRegistry.ts
```

### Store Boundary

Do not copy the fork's approach of adding hundreds of lines to `useAppStore.ts`.

Preferred architecture:

```text
useAppStore
  owns generation, current image, prompt, inserted prompt blocks

usePromptBuilderStore
  owns builder messages, scope, draft, attachments, loading, model

promptBuilderBridge
  reads current app state when sending
  applies structured prompt into useAppStore
  moves draft conversation onto image scope after generation
```

If a separate Zustand store feels too heavy, the fallback is:

```text
ui/src/store/promptBuilderSlice.ts
```

but it must export pure helpers and keep `useAppStore.ts` changes minimal.

### Structured Output Parser

Port the fork idea, but keep it independent:

```text
Brief Intent Summary:
Final Prompt - Korean:
Final Prompt - English:
Notes:
```

Parser behavior:

- Return `null` for ordinary chat replies.
- Extract Korean and English final prompt cards independently.
- Strip markdown fences if the model wraps output.
- Preserve exact visible text wording inside prompt content.

### UI Contract

Builder panel must include:

- current scope label: draft or image-specific;
- optional image thumbnail when scoped to a result;
- model picker;
- message list;
- structured prompt cards;
- apply-to-main-prompt button;
- insert-as-block button;
- attachment tray;
- send and clear buttons;
- thinking indicator.

### Tests

- Right panel can show Prompt Builder without breaking Prompt Library.
- Builder can send message through `postPromptBuilderChat`.
- Structured Korean/English card exposes apply and insert actions.
- Attachments are represented as image/text/file and not persisted with payload data URLs.
- Image-scoped session label resolves current/history item by shared identity key.
- i18n keys exist in English and Korean.

## Slice 3 — Composer Block Ordering + Metadata Restore

### User-Facing Goal

Inserted prompt-library blocks are no longer opaque chips always appended in one place. Users can see the final prompt order and move blocks before or after the main prompt.

### New Files

```text
ui/src/components/composer/ComposerPromptFlow.tsx
ui/src/components/composer/ComposerPromptBlock.tsx
ui/src/components/composer/ComposerToolbar.tsx
ui/src/components/composer/ComposerReferences.tsx
ui/src/hooks/useComposerAutoResize.ts
ui/src/hooks/usePromptFlowWheel.ts
ui/src/lib/composerPrompt.ts
tests/composer-prompt-flow-contract.test.js
tests/history-composer-restore-contract.test.js
```

### Existing Files To Modify

```text
ui/src/components/PromptComposer.tsx
ui/src/store/useAppStore.ts
ui/src/types.ts
ui/src/lib/api.ts
routes/generate.ts
routes/multimode.ts
lib/historyList.ts
docs/migration/runtime-test-inventory.md
```

### Data Contract

Extend inserted prompt snapshot:

```ts
export type ComposerInsertedPromptSnapshot = {
  id: string;
  name: string;
  text: string;
  placement?: "before" | "after";
};
```

Composition:

```text
before blocks
main prompt
after blocks
```

### History Metadata

Persist these fields in generation sidecars:

```text
composerPrompt
composerInsertedPrompts
```

When a history item is selected:

- restore `composerPrompt` into main prompt;
- restore `composerInsertedPrompts` into composer blocks;
- fallback to `item.prompt` if composer metadata is absent.

### Important Compatibility

Existing prompt-library inserted blocks without `placement` should behave as current behavior. Treat missing `placement` as `"before"` or `"after"` only after deciding the upstream default. The fork treats non-`after` blocks as before the main prompt; upstream should decide deliberately because this changes final prompt semantics.

Recommended upstream default:

```text
existing blocks => before
Prompt Builder "insert as block" => after
Canvas context block => before
```

Rationale:

- Library style/quality blocks often serve as global prefix constraints.
- Builder final prompt variants are usually follow-up refinements that should appear after the main idea unless user moves them.
- Canvas context should constrain the generation before the user request.
