---
phase: 1
title: "타입 + 설정 레이어"
---

# Phase 1: 타입 확장 + config.ts + 모델 검증

## 목표
`"grok"`을 세 번째 프로바이더로 인식시키되, 기존 `"oauth"` / `"api"` 경로는 일체 건드리지 않는다.

---

## 1.1 Provider 타입 확장

### `ui/src/types.ts:15`
```diff
- export type Provider = "oauth" | "api";
+ export type Provider = "oauth" | "api" | "grok";
```

### `ui/src/store/useAppStore.ts:1188-1189`
```diff
  function isProvider(value: unknown): value is Provider {
-   return value === "oauth" || value === "api";
+   return value === "oauth" || value === "api" || value === "grok";
  }
```

---

## 1.2 Grok 이미지 모델 세트

### `lib/imageModels.ts` — grok 전용 모델 검증 추가

기존 `normalizeImageModel()`은 OpenAI 모델 세트 (`gpt-5.5/5.4/5.4-mini`)만 검증한다.
grok일 때는 별도 모델 세트를 쓰되, 같은 함수 시그니처를 유지한다.

```typescript
// 기존 상수 아래에 추가
const GROK_FALLBACK_IMAGE_MODEL = "grok-imagine-image";
const VALID_GROK_IMAGE_MODELS = new Set(["grok-imagine-image", "grok-imagine-image-quality"]);

export function normalizeGrokImageModel(rawModel: unknown) {
  if (typeof rawModel !== "string" || rawModel.length === 0) {
    return { model: GROK_FALLBACK_IMAGE_MODEL };
  }
  if (!VALID_GROK_IMAGE_MODELS.has(rawModel)) {
    return {
      error: `Grok image model must be one of: ${[...VALID_GROK_IMAGE_MODELS].join(", ")}`,
      code: "INVALID_GROK_IMAGE_MODEL",
      status: 400,
    };
  }
  return { model: rawModel };
}
```

---

## 1.3 config.ts — grokProvider 섹션

### `config.ts` — `apiProvider` 블록 아래에 추가

```typescript
grokProvider: {
  proxyPort: pickInt(
    env.IMA2_GROK_PROXY_PORT,
    fileCfg.grokProvider?.proxyPort,
    18645,
  ),
  proxyHost: pickStr(
    env.IMA2_GROK_PROXY_HOST,
    fileCfg.grokProvider?.proxyHost,
    "127.0.0.1",
  ),
  defaultImageModel: pickStr(
    env.IMA2_GROK_IMAGE_MODEL_DEFAULT,
    fileCfg.grokProvider?.defaultImageModel,
    "grok-imagine-image",
  ),
  generationTimeoutMs: pickInt(
    env.IMA2_GROK_GENERATION_TIMEOUT_MS,
    fileCfg.grokProvider?.generationTimeoutMs,
    120_000,
  ),
},
```

**설정 설명:**
- `proxyPort` = progrok 기본 포트 (18645)
- `proxyHost` = 로컬 프록시 호스트
- `defaultImageModel` = 기본 모델 (`grok-imagine-image`)
- `generationTimeoutMs` = 생성 타임아웃 (xAI는 스트리밍 없으니 120초)

---

## 1.4 providerOptions.ts — grok 분기

### `lib/providerOptions.ts` — `resolveProviderOptions()` 수정

현재: `const activeProvider = provider === "api" ? "api" : "oauth";`
→ grok을 세 번째 값으로 통과시켜야 한다.

```diff
- const activeProvider = provider === "api" ? "api" : "oauth";
+ const activeProvider = provider === "grok" ? "grok" : provider === "api" ? "api" : "oauth";
```

grok일 때 모델 검증은 `normalizeGrokImageModel()` 사용:
```typescript
if (activeProvider === "grok") {
  const grokModelCheck = normalizeGrokImageModel(rawModel);
  if (grokModelCheck.error) return { error: grokModelCheck.error, code: grokModelCheck.code, status: grokModelCheck.status };
  return {
    provider: "grok" as const,
    model: grokModelCheck.model,
    reasoningEffort: "none",     // grok은 reasoning 미지원
    size: rawSize,               // grok은 size 무시하지만 UI에서 보낸 값 보존 (로깅용)
    webSearchEnabled: false,     // grok Images API에 web_search 없음
  };
}
```

---

## 수정 파일 목록

| 파일 | 변경 | 유형 |
|------|------|------|
| `ui/src/types.ts:15` | Provider union에 `"grok"` 추가 | MODIFY |
| `ui/src/store/useAppStore.ts:1188` | `isProvider()` 가드에 `"grok"` 추가 | MODIFY |
| `lib/imageModels.ts` | `normalizeGrokImageModel()` 함수 추가 | MODIFY |
| `config.ts` | `grokProvider` 섹션 추가 | MODIFY |
| `lib/providerOptions.ts` | grok 분기 추가 | MODIFY |
