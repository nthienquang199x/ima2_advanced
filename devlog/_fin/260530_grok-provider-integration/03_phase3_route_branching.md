---
phase: 3
title: "라우트 분기"
---

# Phase 3: 라우트에서 grok 분기

## 목표
`routes/generate.ts`, `routes/edit.ts`, `routes/multimode.ts`에서
`activeProvider === "grok"`일 때 `grokImageAdapter` 함수를 호출하도록 분기한다.
기존 oauth/api 경로는 일체 변경하지 않는다.

---

## 3.1 `routes/generate.ts` — 단일/배치 이미지 생성

### 현재 흐름 (라인 152-174)
```typescript
const generateOne = async () => {
  // ...retry loop...
  const r = await generateViaResponses(activeProvider, prompt, quality, ...);
  // ...
};
```

### 변경: grok 분기 삽입

```diff
+ import { generateViaGrok } from "../lib/grokImageAdapter.js";

  const generateOne = async () => {
+   // ── Grok: Images API 직행 ──
+   if (activeProvider === "grok") {
+     const grokModel = quality === "high" ? "grok-imagine-image-quality" : imageModel;
+     const r = await generateViaGrok(prompt, ctx, {
+       model: grokModel,
+       signal: cancelController.signal,
+       requestId,
+     });
+     return { b64: r.b64, usage: r.usage, revisedPrompt: r.revisedPrompt, webSearchCalls: 0 };
+   }
+
+   // ── OAuth / API: 기존 Responses 경로 ──
    const MAX_RETRIES = 1;
    // ... (기존 코드 그대로) ...
  };
```

**grok은 retry 하지 않는다:** xAI Images API는 스트리밍이 아닌 동기 호출이므로
빈 응답(safety refusal)이 올 확률이 낮고, retry 시 2배 비용.
실패하면 에러를 바로 반환한다.

**quality → model 매핑:**
- `quality === "high"` → `grok-imagine-image-quality`
- 그 외 → config 기본값 (`grok-imagine-image`)

---

## 3.2 `routes/edit.ts` — 이미지 편집

### 현재 흐름 (라인 184-201)
```typescript
const result = await editViaResponses(activeProvider, prompt, imageB64, ...);
```

### 변경

```diff
+ import { editViaGrok } from "../lib/grokImageAdapter.js";

  // ... 기존 validation 후 ...

+ if (activeProvider === "grok") {
+   const grokModel = quality === "high" ? "grok-imagine-image-quality" : imageModel;
+   const result = await editViaGrok(prompt, imageB64, ctx, {
+     model: grokModel,
+     signal: cancelController.signal,
+     requestId,
+   });
+   // ... 결과 포맷팅 (기존 응답 형태에 맞춤) ...
+ } else {
    const result = await editViaResponses(activeProvider, prompt, imageB64, ...);
    // ... (기존 코드 그대로) ...
+ }
```

**grok edit 제약:**
- 마스크(mask) 미지원 — xAI Images API가 마스크를 지원하는지 미확인
- grok + mask 요청 시 → 400 에러 반환: `"Grok provider does not support mask editing"`
- 추가 참조 이미지(additionalRefs)도 미지원 — `image` 파라미터가 단일

---

## 3.3 `routes/multimode.ts` — 멀티 이미지 시퀀스

### 현재 흐름 (라인 276-311)
```typescript
const parsedResult = await generateMultimodeViaResponses(activeProvider, ...);
```

### 변경

```diff
+ import { generateMultimodeViaGrok } from "../lib/grokImageAdapter.js";

  // ... 기존 validation 후 ...

+ if (activeProvider === "grok") {
+   const grokModel = quality === "high" ? "grok-imagine-image-quality" : imageModel;
+   const parsedResult = await generateMultimodeViaGrok(prompt, ctx, {
+     model: grokModel,
+     maxImages,
+     signal: cancelController.signal,
+     requestId,
+     onFinalImage: async (image, index) => {
+       // SSE로 중간 이미지 전송 (기존 onFinalImage 로직 재사용)
+     },
+   });
+   // ... 응답 포맷팅 ...
+ } else {
    const parsedResult = await generateMultimodeViaResponses(activeProvider, ...);
    // ... (기존 코드 그대로) ...
+ }
```

**grok multimode 동작:**
- 순차 호출이므로 이미지가 하나씩 완료됨 → `onFinalImage`로 SSE event `image` 전송 가능
- `partial` event는 없음 (xAI에 partial_images 없음)
- `phase` event는 그대로 전송
- 개별 실패 시 건너뛰고 다음 이미지 시도 → 206 응답 가능

---

## 3.4 grok에서 무시/비활성화되는 파라미터

라우트에서 grok 분기 시 다음 파라미터들은 **무시하되 로깅/메타데이터에는 보존**:

| 파라미터 | grok에서 | 이유 |
|----------|----------|------|
| `size` | 무시 (payload에 미포함) | xAI `Argument not supported: size` |
| `moderation` | 무시 | xAI에 moderation 파라미터 없음 |
| `reasoningEffort` | `"none"` 고정 | xAI에 reasoning 없음 |
| `webSearchEnabled` | `false` 고정 | Images API에 web_search 없음 |
| `mode` (direct/auto) | 무시 | 프롬프트 가공 없이 직접 전달 |
| `references` (generate) | 무시 | Images API는 generate에서 참조 이미지 미지원 |
| `partial_images` | 무시 | xAI 미지원 |
| `composerPrompt` | 무시 | developer prompt 체계 없음 |

---

## 3.5 응답 필드 호환성

grok 어댑터 결과를 기존 라우트 응답 형태에 맞춰야 한다.

### generate 응답
```typescript
{
  image: `data:image/${format};base64,${b64}`,  // grok은 JPEG 반환 → format 변환 필요할 수 있음
  elapsed,
  filename,
  requestId,
  usage: { grok_cost_usd_ticks: 200000000 },
  provider: "grok",
  model: "grok-imagine-image",
  quality,                    // UI에서 보낸 값 그대로
  size,                       // UI에서 보낸 값 (실제 적용 안 됨)
  moderation,
  reasoningEffort: "none",
  webSearchEnabled: false,
  webSearchCalls: 0,
  revisedPrompt: null,        // xAI는 revised prompt 미반환
  promptMode: "direct",       // grok은 프롬프트 가공 없음
  warnings: [],
}
```

### format 변환
xAI는 항상 JPEG를 반환 (`mime_type: "image/jpeg"`).
사용자가 `format: "png"` 요청 시 → 서버에서 JPEG→PNG 변환하거나, JPEG 그대로 반환하고 `format` 필드만 `"jpeg"`로 표기.

**결정: JPEG 그대로 반환** — 변환은 불필요한 처리 비용. `format` 필드를 `"jpeg"`로 오버라이드하고 mime도 `image/jpeg`로 설정.

---

## 수정 파일 목록

| 파일 | 변경 | 유형 |
|------|------|------|
| `routes/generate.ts` | grok import + `generateOne()` 내 분기 | MODIFY |
| `routes/edit.ts` | grok import + edit 분기 + mask 거부 | MODIFY |
| `routes/multimode.ts` | grok import + multimode 분기 | MODIFY |
