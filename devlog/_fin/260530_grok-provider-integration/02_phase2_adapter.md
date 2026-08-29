---
phase: 2
title: "Grok 이미지 어댑터"
---

# Phase 2: `lib/grokImageAdapter.ts` — xAI Images API 어댑터

## 목표
`/v1/images/generations` 엔드포인트를 직접 호출하는 독립 어댑터를 만든다.
기존 `responsesImageAdapter.ts`(Responses API 전용)는 일체 건드리지 않는다.

---

## 2.1 아키텍처 결정

**왜 별도 파일인가:**
- Responses API와 Images API는 요청/응답 형태가 완전히 다름
- Responses 어댑터에 분기를 넣으면 `postResponses()`, `parseStream()`, 프롬프트 빌더 등 무관한 코드에 grok 예외가 퍼짐
- 별도 파일이면 grok 관련 변경이 기존 oauth/api 경로에 부작용을 줄 수 없음

**어댑터 책임:**
- progrok 프록시 URL 구성
- xAI Images API 요청 payload 조립
- JSON 응답 파싱 → `ParsedImage` 형태로 반환
- 타임아웃 + AbortSignal 처리
- 에러 분류 (upstream 에러 → ima2-gen 에러 코드 매핑)

---

## 2.2 파일 전체 구조

```typescript
// lib/grokImageAdapter.ts

import { logEvent } from "./logger.js";
import { errInfo } from "./errInfo.js";
import type { RouteRuntimeContext } from "./runtimeContext.js";

// ── Types ──────────────────────────────────────────────────────────────

interface GrokImageResponse {
  data: Array<{
    b64_json?: string;
    url?: string;
    mime_type?: string;
  }>;
  usage?: {
    cost_in_usd_ticks?: number;
  };
}

interface GrokGenerateResult {
  b64: string;
  revisedPrompt?: string;
  usage: Record<string, number> | null;
  mime?: string;
}

interface GrokMultimodeResult {
  images: Array<{ b64: string; revisedPrompt?: string }>;
  usage: Record<string, number> | null;
  extraIgnored: number;
}

// ── Endpoint ───────────────────────────────────────────────────────────

function getGrokEndpoint(ctx: RouteRuntimeContext): { url: string; headers: Record<string, string> } {
  const grokCfg = (ctx.config as any).grokProvider || {};
  const host = grokCfg.proxyHost || "127.0.0.1";
  const port = grokCfg.proxyPort || 18645;
  return {
    url: `http://${host}:${port}/v1/images/generations`,
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer dummy",  // progrok이 OAuth 토큰 자동 주입
    },
  };
}

function getGrokTimeout(ctx: RouteRuntimeContext): number {
  return (ctx.config as any).grokProvider?.generationTimeoutMs || 120_000;
}

// ── Core fetch ─────────────────────────────────────────────────────────

async function postGrokImages(
  ctx: RouteRuntimeContext,
  payload: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<GrokImageResponse> {
  const { url, headers } = getGrokEndpoint(ctx);
  const timeoutMs = getGrokTimeout(ctx);

  const timeoutController = new AbortController();
  const timer = setTimeout(() => timeoutController.abort(), timeoutMs);

  const combinedSignal = signal
    ? AbortSignal.any([signal, timeoutController.signal])
    : timeoutController.signal;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
      signal: combinedSignal,
    });
    clearTimeout(timer);

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      let parsed: any;
      try { parsed = JSON.parse(text); } catch { /* ignore */ }
      const msg = parsed?.error || text || `HTTP ${res.status}`;
      const err: any = new Error(`Grok image generation failed: ${msg}`);
      err.status = res.status;
      err.upstreamCode = parsed?.code;
      throw err;
    }

    return await res.json() as GrokImageResponse;
  } catch (e: any) {
    clearTimeout(timer);
    if (e.name === "AbortError") {
      if (signal?.aborted) {
        const err: any = new Error("Generation canceled");
        err.status = 499;
        err.code = "GENERATION_CANCELED";
        throw err;
      }
      const err: any = new Error("Grok image generation timed out");
      err.status = 504;
      err.code = "GENERATION_TIMEOUT";
      throw err;
    }
    throw e;
  }
}

// ── Generate (단일 이미지) ─────────────────────────────────────────────

export async function generateViaGrok(
  prompt: string,
  ctx: RouteRuntimeContext,
  options: {
    model?: string;
    signal?: AbortSignal;
    requestId?: string;
  } = {},
): Promise<GrokGenerateResult> {
  const model = options.model || (ctx.config as any).grokProvider?.defaultImageModel || "grok-imagine-image";

  const payload: Record<string, unknown> = {
    model,
    prompt,
    n: 1,
    response_format: "b64_json",
  };

  logEvent("grok", "generate:start", { requestId: options.requestId, model, promptChars: prompt.length });

  const result = await postGrokImages(ctx, payload, options.signal);

  if (!result.data?.[0]?.b64_json) {
    throw Object.assign(new Error("Grok returned empty image data"), { status: 502, code: "GROK_EMPTY_RESPONSE" });
  }

  const usage = result.usage ? { grok_cost_usd_ticks: result.usage.cost_in_usd_ticks ?? 0 } : null;

  logEvent("grok", "generate:done", { requestId: options.requestId, model, b64Len: result.data[0].b64_json.length });

  return {
    b64: result.data[0].b64_json,
    usage,
    mime: result.data[0].mime_type,
  };
}

// ── Edit (참조 이미지 + 프롬프트) ──────────────────────────────────────

export async function editViaGrok(
  prompt: string,
  imageB64: string,
  ctx: RouteRuntimeContext,
  options: {
    model?: string;
    signal?: AbortSignal;
    requestId?: string;
  } = {},
): Promise<GrokGenerateResult> {
  const model = options.model || (ctx.config as any).grokProvider?.defaultImageModel || "grok-imagine-image";

  // xAI accepts image as { url: "data:image/...;base64,..." }
  // imageB64가 data URL이면 그대로, raw base64면 data URL로 감싼다
  const imageUrl = imageB64.startsWith("data:")
    ? imageB64
    : `data:image/jpeg;base64,${imageB64}`;

  const payload: Record<string, unknown> = {
    model,
    prompt,
    n: 1,
    response_format: "b64_json",
    image: { url: imageUrl },
  };

  logEvent("grok", "edit:start", { requestId: options.requestId, model, promptChars: prompt.length });

  const result = await postGrokImages(ctx, payload, options.signal);

  if (!result.data?.[0]?.b64_json) {
    throw Object.assign(new Error("Grok edit returned empty image data"), { status: 502, code: "GROK_EMPTY_RESPONSE" });
  }

  const usage = result.usage ? { grok_cost_usd_ticks: result.usage.cost_in_usd_ticks ?? 0 } : null;

  logEvent("grok", "edit:done", { requestId: options.requestId, model, b64Len: result.data[0].b64_json.length });

  return {
    b64: result.data[0].b64_json,
    usage,
    mime: result.data[0].mime_type,
  };
}

// ── Multimode (N장 순차 생성) ──────────────────────────────────────────

export async function generateMultimodeViaGrok(
  prompt: string,
  ctx: RouteRuntimeContext,
  options: {
    model?: string;
    maxImages?: number;
    signal?: AbortSignal;
    requestId?: string;
    onFinalImage?: (image: { b64: string; revisedPrompt?: string }, index: number) => void | Promise<void>;
  } = {},
): Promise<GrokMultimodeResult> {
  const model = options.model || (ctx.config as any).grokProvider?.defaultImageModel || "grok-imagine-image";
  const maxImages = Math.min(8, Math.max(1, options.maxImages || 4));

  // xAI의 n 파라미터가 여러 장을 지원하는지 불확실 → 안전하게 순차 호출
  // (OpenAI Images API는 n>1 지원하지만 xAI는 미확인, 순차가 안전)
  const images: Array<{ b64: string; revisedPrompt?: string }> = [];
  let lastUsage: Record<string, number> | null = null;

  logEvent("grok", "multimode:start", { requestId: options.requestId, model, maxImages });

  for (let i = 0; i < maxImages; i++) {
    if (options.signal?.aborted) break;

    const indexedPrompt = maxImages > 1
      ? `[Image ${i + 1} of ${maxImages}] ${prompt}`
      : prompt;

    const payload: Record<string, unknown> = {
      model,
      prompt: indexedPrompt,
      n: 1,
      response_format: "b64_json",
    };

    try {
      const result = await postGrokImages(ctx, payload, options.signal);
      if (result.data?.[0]?.b64_json) {
        const img = { b64: result.data[0].b64_json };
        images.push(img);
        if (result.usage) {
          lastUsage = { grok_cost_usd_ticks: result.usage.cost_in_usd_ticks ?? 0 };
        }
        await options.onFinalImage?.(img, i);
      }
    } catch (e) {
      logEvent("grok", "multimode:item-error", { requestId: options.requestId, index: i, error: errInfo(e) });
      // 개별 실패는 건너뛰고 다음 이미지 시도
      if ((e as any)?.status === 499) throw e; // 취소는 전파
    }
  }

  logEvent("grok", "multimode:done", { requestId: options.requestId, model, returned: images.length, requested: maxImages });

  return {
    images,
    usage: lastUsage,
    extraIgnored: 0,
  };
}
```

---

## 핵심 설계 결정

### 스트리밍 없음
xAI Images API는 SSE를 지원하지 않는다. `postGrokImages()`는 단일 `fetch` → JSON 파싱.
multimode에서 `onFinalImage` 콜백을 각 이미지 완료 시 호출해 SSE 라우트가 중간 결과를 보낼 수 있게 한다.

### quality → 모델명 매핑
OpenAI는 `tools: [{ type: "image_generation", quality: "high" }]`로 quality를 전달하지만,
xAI는 모델 자체가 quality를 결정한다:
- `grok-imagine-image` = standard quality
- `grok-imagine-image-quality` = high quality

라우트에서 `quality === "high"` → `model = "grok-imagine-image-quality"` 매핑은 Phase 3에서 처리.

### size 무시
xAI가 `size` 파라미터를 거부하므로 payload에 포함하지 않는다.
UI에서 보낸 size 값은 로깅·메타데이터용으로만 보존.

### multimode 순차 호출
xAI의 `n>1` 지원 여부가 불확실하므로, 안전하게 순차 호출.
각 이미지에 `[Image K of N]` 프리픽스를 붙여 시퀀스 의도를 전달.
개별 실패는 건너뛰되 취소(499)는 즉시 전파.

### 에러 매핑
| xAI 에러 | ima2-gen 매핑 |
|----------|--------------|
| HTTP 400 | 400 + `GROK_BAD_REQUEST` |
| HTTP 401/403 | 502 + `GROK_AUTH_FAILED` (progrok 토큰 만료) |
| HTTP 429 | 429 + `GROK_RATE_LIMITED` |
| HTTP 500+ | 502 + `GROK_UPSTREAM_ERROR` |
| 빈 응답 | 502 + `GROK_EMPTY_RESPONSE` |
| 타임아웃 | 504 + `GENERATION_TIMEOUT` |
| 취소 | 499 + `GENERATION_CANCELED` |

---

## 수정 파일 목록

| 파일 | 변경 | 유형 |
|------|------|------|
| `lib/grokImageAdapter.ts` | 전체 신규 생성 | NEW |
