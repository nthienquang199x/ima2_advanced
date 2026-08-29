# 00 — agy (Gemini) Provider Integration Audit

Date: 2026-06-02
Status: Phase 1 complete, gaps documented

## Overview

agy provider는 Google Antigravity CLI를 통해 Gemini 이미지 생성 모델(`default_api:generate_image`)을 호출하는 블랙박스 어댑터.
`spawn("agy", ["-p", "-"])` + stdin pipe 방식으로 프로세스 실행, stdout에서 artifact 경로 파싱 후 b64 변환.

## Architecture

```
ima2 request (provider=agy)
  → providerOptions.ts (model=gemini-image, size=1024x1024, webSearch=false)
  → agyImageAdapter.ts
    1. Build strict English prompt (~5600 chars)
    2. Write reference images to temp files (if i2i)
    3. spawn("agy", ["-p", "-"]) + stdin.write(prompt)
    4. Parse stdout: RESULT|<artifact_path>|<ext>
    5. Read artifact file → b64
    6. Cleanup temp refs
  → Return { b64, mime, usage, webSearchCalls:0 }
  → generate route saves to ~/.ima2/generated/
```

## Fixed Constraints

- Output: **1024x1024 fixed** (no size parameter in tool spec)
- Format: **JPEG** (despite .png extension, magic bytes are JPEG)
- References: **max 3** (tool spec hard limit)
- Web search: **disabled** (agy has no web search integration)
- Timeout: **360 seconds**
- Prompt delivery: **stdin pipe** (execFile args produce 0 stdout — TTY issue)

## Files Changed (17 files)

### New Files
| File | Purpose |
|------|---------|
| `lib/agyImageAdapter.ts` | Core adapter — spawn, prompt, parse, b64 |

### Backend Type/Config
| File | Change |
|------|--------|
| `lib/providerOptions.ts` | "agy" provider branch |
| `lib/capabilities.ts` | VALID_PROVIDERS += "agy" |
| `lib/agentTypes.ts` | provider union += "agy" |
| `lib/agentSettings.ts` | PROVIDERS Set += "agy" |
| `lib/agentRuntime.ts` | agy dispatch + import + format detection |

### Routes
| File | Change |
|------|--------|
| `routes/generate.ts` | agy dispatch, format=jpeg, ref limit, MIME detect |
| `routes/edit.ts` | agy edit branch, mask block, format detect |
| `routes/multimode.ts` | agy single-image branch, format detect |
| `routes/nodes.ts` | agy node branch, ref limit, format detect |

### UI
| File | Change |
|------|--------|
| `ui/src/types.ts` | Provider += "agy" |
| `ui/src/store/useAppStore.ts` | isProvider() += "agy" |
| `ui/src/components/ProviderSelect.tsx` | Gemini button + always-ok availability |
| `ui/src/components/CostEstimate.tsx` | free += "agy" |
| `ui/src/components/ProviderReadinessPopup.tsx` | "Gemini" label |
| `ui/src/components/agent/agentTypes.ts` | provider union += "agy" |
| `ui/src/components/agent/AgentModelSelector.tsx` | Gemini option + model switch |

## Remaining Gaps (Known)

### HIGH — Should fix before production

| # | Surface | Issue | Impact | Status |
|---|---------|-------|--------|--------|
| 1 | multimode | n>1 returns only 1 image | User requests 4, gets 1 | OPEN |
| 2 | generate | n>1 spawns N separate agy processes | Slow, resource heavy | OPEN |
| 3 | video routes | agy not explicitly rejected | Generic error | FIXED — AGY_VIDEO_UNSUPPORTED |
| 4 | UI imageModels.ts | No "gemini-image" in model options | Model selector shows GPT models | OPEN |
| 5 | ProviderSelect | No agy status check | Always green | OPEN |
| 6 | GenerationControlsPanel | No agy compat notes | Format/moderation shown | FIXED — compat note + hide controls |
| 7 | SettingsWorkspace | agy falls into non-grok branch | Irrelevant toggles | FIXED — agy-specific info panel |

### MEDIUM — Cosmetic / logging

| # | Surface | Issue | Status |
|---|---------|-------|--------|
| 8 | agentRuntime:541 | Web search label says "Responses" for agy | FIXED — providerLabel |
| 9 | agentRuntime:363 | Event name hardcoded "grok_ref_missing" | OPEN |
| 10 | agentRuntime:99 | Web search force-enable, should disable for agy | FIXED |
| 11 | i18n | No agy-specific translations | OPEN |
| 12 | nodes:198 | Quality model check doesn't document agy | OPEN |
| 13 | edit:303 | Model string inconsistent for agy quality | OPEN |

### LOW — Nice to have

| # | Surface | Issue |
|---|---------|-------|
| 14 | Composer prompts | Not passed to agy (stored but unused) |
| 15 | Size selector | Shows size options for agy (all ignored) |
| 16 | Quality selector | Shows quality options for agy (all ignored) |
| 17 | Mask editing | Blocked with error (correct, but no fallback) |

## Compatibility Matrix

| Mode | Status | Notes |
|------|--------|-------|
| Classic (generate) | WORKS | Single image, 1024x1024, JPEG |
| Edit | WORKS | i2i via reference, no mask |
| Multimode | PARTIAL | Returns 1 image regardless of maxImages |
| Node (graph) | WORKS | Parent/child, refs, context modes |
| Agent | WORKS | Image gen; video = grok only |
| Card News | WORKS | No restrictions |
| Video | N/A | Grok only |
| Prompt Builder | WORKS | Provider agnostic |
| Settings | PARTIAL | Can set default; no agy-specific UI |
| History | WORKS | Provider label correct |

## Provider Button Grid (Future Plan)

```
GPT OAuth  │  Grok OAuth  │  Gemini    ← current 4 buttons
GPT API    │  Grok API *  │  Gemini API *
                 (* = 나중)
```

## E2E Verification Results

| Test | Result |
|------|--------|
| tsc --noEmit (server) | PASS |
| tsc --noEmit (UI) | PASS |
| npm run build:server | PASS |
| npm run build (UI) | PASS |
| /api/capabilities — providers includes "agy" | PASS |
| /api/generate provider=agy — single image | PASS (27-32s, 1024x1024 PNG) |
| Metadata sidecar — provider:"agy", model:"gemini-image" | PASS |
| Server logs — clean request cycle | PASS |
| Smoke tests (CLI) — 7/7 passed | PASS |
| stdin pipe discovery — execFile fails, spawn+stdin works | PASS |
