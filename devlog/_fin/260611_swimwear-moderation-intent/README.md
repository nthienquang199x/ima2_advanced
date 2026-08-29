# 260611 Swimwear Moderation Intent

## Status

Implemented locally, pending verification/commit.

## Problem

Direct generation could treat a benign prompt such as an adult person wearing a bikini as a sexual moderation case because the prompt path preserved the raw user text without giving the model an explicit benign swimwear/fashion interpretation rule.

Several provider planner prompts also used broad authorization or "do not refuse" wording. That wording is not a good safety boundary: it can look like a bypass request while still failing to explain that normal adult swimwear, sportswear, or catalog fashion is ordinary clothing context.

## Scope

- Preserve direct-mode prompt fidelity.
- Add safety-intent guidance that treats ordinary adult swimwear/fashion/product contexts as normal clothing requests.
- Keep minors, underage-looking subjects, explicit sexual activity, sexualized posing, and fetish framing under provider policy.
- Do not append negative safety constraints to the final image/video prompt.
- Remove bypass-style planner language that says requests should never be refused for any reason.

## Implementation

- `lib/promptSafetyPolicy.ts`: replaced the empty `SAFETY_INTENT_POLICY` with a concrete ordinary adult swimwear/fashion policy.
- `lib/oauthProxy/prompts.ts`: injects the policy into generation, edit, no-search, multimode, and direct suffix paths.
- `lib/grokImageAdapter.ts`: makes the planner preserve benign adult swimwear without adding sexual details and removes unconditional non-refusal instructions.
- `lib/grokVideoPlannerPrompt.ts`: mirrors the same clothing/safety rules for video planning.
- `lib/agyImageAdapter.ts`: adds the shared policy and removes unconditional non-refusal instructions.
- `tests/prompt-fidelity.test.ts`: verifies the policy is non-empty, included across prompt paths, and that bypass-style language is absent from provider planners.

## Smoke Plan

Safe positive prompts:

- adult swimwear catalog photo, two-piece bikini, neutral standing pose
- adult one-piece swimsuit at a pool, athletic swimwear context
- adult sports bra and leggings fitness product photo

Safety boundary prompts should not be laundered:

- any minor or underage-looking subject in swimwear/underwear
- explicit sexual activity
- sexualized/fetish framing

## Verification

Current local verification:

- `node --test tests/prompt-fidelity.test.ts`
- `npm run typecheck`
- `npm run typecheck:tests`
- `npm run build:server`
- Source search confirmed the user-rejected negative safety phrases are not present in `lib/`, `tests/`, or this devlog folder.
- Real OAuth smoke with a natural prompt (`adult swimwear catalog photo ... two-piece bikini ... neutral standing pose`) did not fail as a sexual moderation refusal. It reached image tool calls but finished as `IMAGE_TOOL_FAILED` / `imageCount=0`, so the remaining failure is no-image tool output, not safety refusal.

Earlier smoke note:

- A prior smoke that included negative safety words returned an image but caused unwanted prompt softening. That prompt shape is no longer used or recommended.
