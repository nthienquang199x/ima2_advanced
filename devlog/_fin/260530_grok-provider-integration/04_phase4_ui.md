---
phase: 4
title: "UI — 프로바이더 선택 + 가용성"
---

# Phase 4: 프론트엔드 Grok 프로바이더 UI

## 목표
ProviderSelect 컴포넌트에 "Grok" 버튼을 추가하고,
progrok 프록시 가용성 체크를 구현한다.

---

## 4.1 Provider 타입 (Phase 1에서 완료)

`ui/src/types.ts:15` — `"grok"` 이미 추가됨
`ui/src/store/useAppStore.ts:1188` — `isProvider()` 이미 추가됨

---

## 4.2 ProviderSelect.tsx — 세 번째 버튼

### 현재 (라인 50-53)
```typescript
const PROVIDERS: { value: Provider; label: string }[] = [
  { value: "oauth", label: "OAuth" },
  { value: "api", label: t("provider.apiLabel") },
];
```

### 변경
```diff
  const PROVIDERS: { value: Provider; label: string }[] = [
    { value: "oauth", label: "OAuth" },
    { value: "api", label: t("provider.apiLabel") },
+   { value: "grok", label: "Grok" },
  ];
```

---

## 4.3 가용성 체크 — `useProviderAvailability()`

### 현재 (라인 15-41)
- oauth: `useOAuthStatus()` → `status === "ready"` 확인
- api: `useBilling()` → `apiKeyValid === true` 확인

### grok 가용성 확인 방법
progrok 프록시가 떠있는지 확인 → `/v1/models` 엔드포인트 GET 요청.

**서버 사이드 엔드포인트 필요:**
프론트엔드에서 직접 `localhost:18645`에 CORS 요청하면 CORS 에러.
→ ima2-gen 서버에 프록시 상태 확인 엔드포인트를 추가.

### 새 서버 엔드포인트: `GET /api/grok/status`

```typescript
// routes/grok.ts (NEW)
export function registerGrokRoutes(app, ctx) {
  app.get("/api/grok/status", async (_req, res) => {
    const grokCfg = ctx.config.grokProvider || {};
    const host = grokCfg.proxyHost || "127.0.0.1";
    const port = grokCfg.proxyPort || 18645;
    try {
      const r = await fetch(`http://${host}:${port}/v1/models`, {
        signal: AbortSignal.timeout(3000),
      });
      if (r.ok) {
        const data = await r.json();
        const models = data?.data?.map((m: any) => m.id).filter(Boolean) || [];
        const hasImageModel = models.some((m: string) => m.startsWith("grok-imagine"));
        return res.json({ status: hasImageModel ? "ready" : "no_image_model", models });
      }
      return res.json({ status: "error", reason: `HTTP ${r.status}` });
    } catch {
      return res.json({ status: "offline" });
    }
  });
}
```

### 프론트엔드 Hook: `useGrokStatus()`

```typescript
// ui/src/hooks/useGrokStatus.ts (NEW)
import useSWR from "swr";

export function useGrokStatus() {
  const { data } = useSWR("/api/grok/status", (url) =>
    fetch(url).then((r) => r.json()),
    { refreshInterval: 10_000 }   // 10초마다 폴링
  );
  return data;
}
```

### `useProviderAvailability()` 확장

```diff
+ import { useGrokStatus } from "../hooks/useGrokStatus";

  export function useProviderAvailability(): Record<Provider, ProviderAvailability> {
    const oauth = useOAuthStatus();
    const { data } = useBilling();
+   const grok = useGrokStatus();

    // ... 기존 oauth/api 로직 ...

+   const grokReady = grok?.status === "ready";
+   const grokReason = grok?.status === "offline"
+     ? t("provider.grokOffline")         // "Grok 프록시가 실행되지 않고 있습니다"
+     : grok?.status === "no_image_model"
+       ? t("provider.grokNoImageModel")  // "이미지 생성 모델을 찾을 수 없습니다"
+       : t("provider.grokNotReady");     // "Grok을 사용할 수 없습니다"

    return {
      oauth: { ... },
      api: { ... },
+     grok: { ok: grokReady, reason: grokReady ? "" : grokReason },
    };
  }
```

---

## 4.4 i18n 문자열

### `ui/src/i18n/en.ts` + `ui/src/i18n/ko.ts`에 추가

```typescript
// en
"provider.grokOffline": "Grok proxy is not running",
"provider.grokNoImageModel": "No image generation model found",
"provider.grokNotReady": "Grok is not available",

// ko
"provider.grokOffline": "Grok 프록시가 실행되지 않고 있습니다",
"provider.grokNoImageModel": "이미지 생성 모델을 찾을 수 없습니다",
"provider.grokNotReady": "Grok을 사용할 수 없습니다",
```

---

## 4.5 grok 선택 시 UI 차이

grok은 일부 옵션이 비활성화됨:
- **Size 프리셋**: 비활성화 (xAI가 size 미지원)
- **Reasoning Effort**: 비활성화 (xAI 미지원)
- **Web Search 토글**: 비활성화 (Images API에 없음)
- **Model 선택**: `grok-imagine-image` / `grok-imagine-image-quality` 로 표시

### 구현 방법
`provider === "grok"`일 때 해당 컨트롤의 `disabled` prop 설정.
별도 컴포넌트를 만들지 않고, 기존 컨트롤에 조건부 disabled 추가.

---

## 4.6 grok 선택 시 모델 자동 전환

grok 선택 → 모델이 `gpt-*`이면 자동으로 `grok-imagine-image`로 전환.
반대로 oauth/api 선택 → 모델이 `grok-*`이면 기본 OpenAI 모델로 복원.

### `useAppStore.ts` — `setProvider()` 수정 (라인 2964-2966)

```diff
  setProvider: (provider) => {
    saveGenerationDefaultsPatch({ provider });
-   set({ provider });
+   const currentModel = get().model;
+   if (provider === "grok" && currentModel?.startsWith("gpt-")) {
+     set({ provider, model: "grok-imagine-image" as any });
+   } else if (provider !== "grok" && currentModel?.startsWith("grok-")) {
+     set({ provider, model: "gpt-5.4-mini" as any });
+   } else {
+     set({ provider });
+   }
  },
```

---

## 수정 파일 목록

| 파일 | 변경 | 유형 |
|------|------|------|
| `routes/grok.ts` | `/api/grok/status` 엔드포인트 | NEW |
| `server.ts` (또는 라우트 등록 파일) | `registerGrokRoutes()` 호출 추가 | MODIFY |
| `ui/src/hooks/useGrokStatus.ts` | grok 상태 hook | NEW |
| `ui/src/components/ProviderSelect.tsx` | PROVIDERS 배열에 grok 추가 + availability 확장 | MODIFY |
| `ui/src/i18n/en.ts` | grok 관련 문자열 추가 | MODIFY |
| `ui/src/i18n/ko.ts` | grok 관련 문자열 추가 | MODIFY |
| `ui/src/store/useAppStore.ts` | setProvider에 모델 자동 전환 로직 | MODIFY |
