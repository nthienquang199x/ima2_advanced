# Phase 1 Backend Plan

## Files

- `/Users/jun/Developer/new/700_projects/ima2-gen/config.ts`
- `/Users/jun/Developer/new/700_projects/ima2-gen/lib/grokImageAdapter.ts`
- `/Users/jun/Developer/new/700_projects/ima2-gen/routes/generate.ts`
- `/Users/jun/Developer/new/700_projects/ima2-gen/routes/edit.ts`
- `/Users/jun/Developer/new/700_projects/ima2-gen/routes/multimode.ts`
- `/Users/jun/Developer/new/700_projects/ima2-gen/tests/*grok*`

## Adapter Contract

Add `GrokImageRequestOptions`:

```ts
type GrokImageRequestOptions = {
  model?: string;
  size?: string;
  quality?: string;
  signal?: AbortSignal;
  requestId?: string;
};
```

Add config:

```ts
grokProvider: {
  plannerModel: "grok-4.3",
  plannerTimeoutMs: 60_000,
  generationTimeoutMs: 120_000
}
```

## Planner Request

Endpoint:

```text
POST http://127.0.0.1:{grokProvider.proxyPort}/v1/chat/completions
```

Payload:

```json
{
  "model": "grok-4.3",
  "stream": false,
  "parallel_tool_calls": false,
  "messages": [
    { "role": "system", "content": "You are ima2's image generation planner..." },
    { "role": "user", "content": "Original user prompt + selected model/size constraints" }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "generate_image",
        "description": "Generate a single image through xAI Images API.",
        "parameters": {
          "type": "object",
          "properties": {
            "prompt": { "type": "string" },
            "model": { "type": "string", "enum": ["grok-imagine-image", "grok-imagine-image-quality"] },
          },
          "required": ["prompt", "model"]
        }
      }
    }
  ],
  "tool_choice": { "type": "function", "function": { "name": "generate_image" } }
}
```

## Execution

After parsing the tool call:

- Validate that tool name is `generate_image`.
- Parse JSON arguments safely.
- Clamp model to valid Grok image models.
- Final model is route-selected (`quality: high` promotes to `grok-imagine-image-quality`).
- Use size mapper result from route/server. The tool schema does not accept dimensions because size is a server-side contract.
- POST `/v1/images/generations` with `model`, `prompt`, `n: 1`, `response_format: "b64_json"`, `aspect_ratio`, `resolution`.
- Do not send a tool result back to the planner. ima2 only needs the forced tool arguments, then executes the local tool.

## Scope

- Classic `/api/generate`: planner/tool pipeline.
- Classic `n > 1`: planner once, reuse planned prompt for image requests.
- Edit `/api/edit`: no planner in this phase; fix endpoint to xAI `/v1/images/edits` and pass size mapping.
- Multimode: no planner in this phase; pass size mapping to each image request.
- Node/Agent: out of scope for this phase.

## Error Handling

Add specific error codes:

- `GROK_PLANNER_BAD_REQUEST`
- `GROK_PLANNER_EMPTY_TOOL_CALL`
- `GROK_PLANNER_INVALID_TOOL_ARGS`
- `GROK_PLANNER_NETWORK_FAILED`
- `GROK_PLANNER_TIMEOUT`

Do not silently fall back to direct prompt. If the planner cannot produce a tool call, return a clear failure.

HTTP status mapping:

| Code | HTTP |
|---|---|
| `GROK_PLANNER_BAD_REQUEST` | upstream 4xx or 502 for upstream 5xx |
| `GROK_PLANNER_EMPTY_TOOL_CALL` | 502 |
| `GROK_PLANNER_INVALID_TOOL_ARGS` | 502 |
| `GROK_PLANNER_NETWORK_FAILED` | 502 |
| `GROK_PLANNER_TIMEOUT` | 504 |
| `GENERATION_CANCELED` | 499 |
