# Grok LLM Tool Pipeline Plan

Date: 2026-05-30

## Problem

The first Grok provider implementation sends the user prompt directly to xAI Images API. That is too weak for ima2 because the OpenAI Responses path implicitly uses an LLM/tool structure: the model receives system/developer instructions, normalizes intent, and then calls image generation. Direct image calls skip that prompt-planning layer.

## Goal

For `provider: "grok"`, use:

1. Mandatory xAI Web Search through `/v1/responses`.
2. `grok-4.3` planner call.
3. Forced custom function/tool call named `generate_image`.
4. Local execution of that tool through xAI `/v1/images/generations`.
4. xAI-native `aspect_ratio` and `resolution` mapping from ima2 size.
5. UI that lets users actually select Grok and still set size/aspect hints.
6. Docs and verification covering official xAI behavior, server tests, UI tests, and live E2E.

## Official xAI Docs Grounding

- Function calling: xAI documents custom tools where Grok returns a tool call, the client executes it locally, and then may send the result back. It supports `tool_choice: "required"` and forcing a specific tool with `{"type":"function","function":{"name":"..."}}`.
- Image generation: xAI documents `/v1/images/generations` with `model`, `prompt`, `n`, and `response_format`.
- Size mapping: xAI does not use OpenAI's `size` field here. It documents:
  - `aspect_ratio`: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`, `2:1`, `1:2`, `19.5:9`, `9:19.5`, `20:9`, `9:20`, `auto`.
  - `resolution`: `1k` or `2k`.
- Recommended image model: docs say to use `grok-imagine-image-quality` for new image generation requests, while `grok-imagine-image` remains available.

## Architecture

```text
ima2 UI / CLI
  -> /api/generate provider=grok model=grok-imagine-image-quality size=2048x1152
  -> lib/grokImageAdapter.generateViaGrok()
  -> POST /v1/responses model=grok-4.3 tools=[web_search] tool_choice=required
  -> POST /v1/chat/completions model=grok-4.3 tools=[generate_image]
     tool_choice={"type":"function","function":{"name":"generate_image"}}
  -> parse tool args: { prompt, model, aspect_ratio, resolution }
  -> POST /v1/images/generations with tool args + response_format=b64_json
  -> normalize JPEG b64 result into existing ima2 response shape
```

## Design Decisions

- Keep the tool local. xAI does not host an image generation tool inside chat; ima2 defines a custom function and executes Images API after Grok requests it.
- Do not use direct Images API prompt for classic generation unless the planner itself fails with a clear user-facing error. Silent fallback would hide prompt-quality regressions.
- Use `grok-4.3` as default planner model via config (`IMA2_GROK_PLANNER_MODEL`) with a separate planner timeout (`IMA2_GROK_PLANNER_TIMEOUT_MS`).
- Keep final output format JPEG for Grok because xAI returns JPEG.
- Preserve image request metadata: `prompt` is the original user prompt; `revisedPrompt` is the planner-generated image prompt.
- For size, send official `aspect_ratio` and `resolution`; do not send unsupported `size`.

## Phases

1. Backend planner/tool adapter
2. Size mapper and route threading
3. Frontend Grok model/size UX
4. Docs and jawdev notes
5. Verification: unit, integration, live server, Control E2E, employee review

## Employee Audit Incorporation

- 료 returned NEEDS_FIX. Incorporated: explicit tool_choice JSON, no tool-result roundtrip, planner config/timeout, planner error taxonomy, full size table, route size threading, generate-only planner v1 scope, edit endpoint correction to `/v1/images/edits`, planner-once for classic `n > 1`, revisedPrompt metadata, and Grok tests.
- 니지카 returned NEEDS_FIX. Incorporated: Settings model select lists Grok, Grok model selection switches provider, Grok controls keep `SizePicker`, compatibility copy distinguishes xAI size mapping from OpenAI-only format/moderation/reasoning/web-search, and UI contract coverage prevents hiding SizePicker again.
