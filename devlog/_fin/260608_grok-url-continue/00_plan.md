# Grok "Continue as URL" Button

## Summary
Grok 이미지/비디오 생성 결과에서 xAI 원본 URL을 직접 활용하는 "URL로 이어서" 버튼 추가.
기존 "Continue here" 처럼 프롬프트 창에 레퍼런스를 세팅하되, 다음 생성 시 base64 대신 xAI CDN URL을 직접 전달.
1시간 TTL 자동 비활성화. I2I(multimode) + I2V(video) 모두 지원.

## Approach

### 핵심 아이디어
- Grok 이미지 생성: `response_format: "b64_json"` → `"url"` 전환
- xAI가 URL 반환 → 서버가 다운로드해서 로컬 저장 + base64 변환 (기존 파이프라인 호환)
- 원본 URL을 사이드카 메타데이터 + 히스토리에 `providerUrl`로 보존
- Grok 비디오: `videoUrl`은 이미 존재 → 그냥 사이드카에 저장
- 프론트엔드: "URL로 이어서" 버튼 클릭 → providerUrl을 store에 세팅 → 다음 생성 시 서버에 전달 → xAI API에 직접 URL 패스스루

### 이점
- xAI가 자체 CDN에서 직접 fetch (zero-hop)
- 클라이언트→서버 base64 업로드 불필요
- 대용량 이미지(1024²+)에서 특히 효과적

---

## File Changes (16 MODIFY, 0 NEW)

### Layer 1: Server — response_format 전환 + URL 다운로드

#### 1. MODIFY `lib/grokImageCore.ts`
**GrokGenerateResult 타입**:
```diff
 export interface GrokGenerateResult {
   b64: string;
+  providerUrl?: string;
   revisedPrompt?: string;
   usage: Record<string, number> | null;
   webSearchCalls: number;
   mime?: string;
 }
```

**GrokReferenceImage 타입**:
```diff
 export interface GrokReferenceImage {
   b64: string;
+  url?: string;
   declaredMime?: string | null;
   detectedMime?: string | null;
 }
```

**imagePayload / imageEditPayload**:
```diff
-  return { model, prompt, n: 1, response_format: "b64_json", ...mapSizeToGrokImageParams(size) };
+  return { model, prompt, n: 1, response_format: "url", ...mapSizeToGrokImageParams(size) };
```
(Both functions)

**referenceImageUrl — URL 패스스루**:
```diff
 export function referenceImageUrl(ref: GrokReferenceImage): string {
+  if (ref.url) return ref.url;
   const inputMime = ref.declaredMime || ref.detectedMime || detectImageMimeFromB64(ref.b64) || "image/png";
   return ref.b64.startsWith("data:") ? ref.b64 : `data:${inputMime};base64,${ref.b64}`;
 }
```

**NEW function — downloadGrokImageUrl**:
```ts
const MAX_IMAGE_DOWNLOAD_BYTES = 50 * 1024 * 1024;

export async function downloadGrokImageUrl(
  url: string,
  signal?: AbortSignal,
  timeoutMs = 30_000,
): Promise<{ buffer: Buffer; b64: string; mime: string }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const combined = signal ? AbortSignal.any([signal, controller.signal]) : controller.signal;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
      throw grokError("Image download URL must be HTTP(S)", 502, "GROK_IMAGE_DOWNLOAD_FAILED");
    }
    const res = await fetch(url, { signal: combined });
    if (!res.ok) throw grokError(`Image download failed: HTTP ${res.status}`, 502, "GROK_IMAGE_DOWNLOAD_FAILED");
    const contentLength = Number(res.headers.get("content-length") || "0");
    if (contentLength > MAX_IMAGE_DOWNLOAD_BYTES) {
      throw grokError("Image download exceeds 50MB limit", 502, "GROK_IMAGE_DOWNLOAD_FAILED");
    }
    const buffer = Buffer.from(await res.arrayBuffer());
    clearTimeout(timer);
    if (buffer.length === 0) throw grokError("Image download was empty", 502, "GROK_IMAGE_DOWNLOAD_FAILED");
    const mime = res.headers.get("content-type")?.split(";")[0]?.trim() || detectImageMimeFromBuffer(buffer) || "image/png";
    return { buffer, b64: buffer.toString("base64"), mime };
  } catch (e: any) {
    clearTimeout(timer);
    if (e.name === "AbortError") {
      if (signal?.aborted) throw grokError("Generation canceled", 499, "GENERATION_CANCELED");
      throw grokError("Image download timed out", 504, "GROK_IMAGE_TIMEOUT");
    }
    if (e.code && e.status) throw e;
    throw grokError(`Image download failed: ${e.message}`, 502, "GROK_IMAGE_DOWNLOAD_FAILED");
  }
}
```

#### 2. MODIFY `lib/grokImageAdapter.ts`
**generateViaGrok**:
```diff
- if (!result.data?.[0]?.b64_json) {
-   throw grokError("Grok returned empty image data", 502, "GROK_EMPTY_RESPONSE");
+ const imageUrl = result.data?.[0]?.url;
+ if (!imageUrl) {
+   throw grokError("Grok returned no image URL", 502, "GROK_EMPTY_RESPONSE");
  }
+ const downloaded = await downloadGrokImageUrl(imageUrl, options.signal);
  ...
- return { b64: result.data[0].b64_json, usage, webSearchCalls: plan.webSearchCalls, mime: result.data[0].mime_type, revisedPrompt: plan.prompt };
+ return { b64: downloaded.b64, providerUrl: imageUrl, usage, webSearchCalls: plan.webSearchCalls, mime: downloaded.mime, revisedPrompt: plan.prompt };
```

**editViaGrok**:
```diff
- if (!result.data?.[0]?.b64_json) {
-   throw grokError("Grok edit returned empty image data", 502, "GROK_EMPTY_RESPONSE");
+ const editUrl = result.data?.[0]?.url;
+ if (!editUrl) {
+   throw grokError("Grok edit returned no image URL", 502, "GROK_EMPTY_RESPONSE");
  }
+ const downloaded = await downloadGrokImageUrl(editUrl, options.signal);
  ...
- return { b64: result.data[0].b64_json, usage, webSearchCalls: 0, mime: result.data[0].mime_type, revisedPrompt: ... };
+ return { b64: downloaded.b64, providerUrl: editUrl, usage, webSearchCalls: 0, mime: downloaded.mime, revisedPrompt: ... };
```

#### 3. MODIFY `lib/grokMultimodeAdapter.ts`
```diff
 export interface GrokMultimodeResult {
-  images: Array<{ b64: string; revisedPrompt?: string; mime?: string }>;
+  images: Array<{ b64: string; revisedPrompt?: string; mime?: string; providerUrl?: string }>;
```

Loop body:
```diff
-      if (result.data?.[0]?.b64_json) {
-        const img = { b64: result.data[0].b64_json, mime: result.data[0].mime_type, revisedPrompt: plan.prompt };
+      const imgUrl = result.data?.[0]?.url;
+      if (imgUrl) {
+        const dl = await downloadGrokImageUrl(imgUrl, options.signal);
+        const img = { b64: dl.b64, mime: dl.mime, revisedPrompt: plan.prompt, providerUrl: imgUrl };
```

### Layer 2: Server — providerUrl 저장 + 참조 수신

#### 4. MODIFY `routes/multimode.ts`
**사이드카 meta + SSE event에 providerUrl 추가**:
```diff
 const meta = { ... provider: activeProvider, createdAt: Date.now(), ... };
+ // providerUrl: image.providerUrl from GrokMultimodeResult (Grok only)
```

onFinalImage callback에서:
```diff
 const item = {
   image: `data:${resultMime};base64,${image.b64}`,
   filename,
+  providerUrl: image.providerUrl ?? undefined,
   revisedPrompt: image.revisedPrompt || null,
```

meta에도 추가:
```diff
 const meta = {
   ...existingFields,
+  providerUrl: image.providerUrl ?? null,
 };
```

**providerUrl 기반 참조 수신**:
```diff
 // After refCheck validation, before Grok generation:
+ const incomingProviderUrl = typeof req.body?.providerUrl === "string" && req.body.providerUrl.startsWith("http") ? req.body.providerUrl : null;
+ if (incomingProviderUrl && (activeProvider === "grok" || activeProvider === "grok-api")) {
+   refCheck.refDetails.unshift({ index: -1, b64: "", url: incomingProviderUrl, declaredMime: null, detectedMime: null, b64Chars: 0, approxBytes: 0, source: "providerUrl", warnings: [] });
+ }
```

#### 5. MODIFY `routes/video.ts`
**사이드카에 providerUrl 저장** (result.url은 xAI 비디오 URL):
```diff
 const meta = {
   kind: "video",
+  providerUrl: result.url,
   ...rest,
 };
```

**SSE done event에 providerUrl 추가**:
```diff
 dualEmitVideo(res, requestId, "done", {
+  providerUrl: result.url,
   ...existingFields,
 });
```

**providerUrl 기반 소스 이미지 수신**:
```diff
+ const incomingProviderUrl = typeof req.body?.providerUrl === "string" && req.body.providerUrl.startsWith("http") ? req.body.providerUrl : null;
  // After reference resolution:
- const sourceB64 = mode === "image-to-video" ? resolved[0]?.b64 : undefined;
+ const sourceB64 = incomingProviderUrl || (mode === "image-to-video" ? resolved[0]?.b64 : undefined);
```
(sourceImageUrl() in grokVideoAdapter already handles `http` URLs)

#### 6. MODIFY `lib/historyList.ts`
```diff
 return {
   filename: rel,
+  providerUrl: meta?.providerUrl || null,
   url: `/generated/...`,
```

### Layer 3: Frontend — 타입 + 매핑

#### 7. MODIFY `ui/src/lib/api-history.ts`
```diff
 export type HistoryItem = {
+  providerUrl?: string | null;
   filename: string;
```

#### 8. MODIFY `ui/src/types.ts`
```diff
 export type GenerateItem = {
+  providerUrl?: string | null;
   image: string;
```

#### 9. MODIFY `ui/src/store/storeHelpers.ts`
```diff
 return {
   image: it.url,
+  providerUrl: it.providerUrl ?? null,
   url: it.url,
```

### Layer 4: Frontend — Store + Button + Flow

#### 10. MODIFY `ui/src/store/storeTypes.ts`
```diff
 // Add to AppState:
+  providerUrlReference: string | null;
+  setProviderUrlReference: (url: string | null) => void;
```

#### 11. MODIFY `ui/src/store/useAppStore.ts`
```diff
+  providerUrlReference: null,
+  setProviderUrlReference: (url) => set({ providerUrlReference: url }),
```

#### 12. MODIFY `ui/src/lib/continueFromItem.ts`
Add `continueFromItemAsUrl`:
```ts
export async function continueFromItemAsUrl(
  item: ContinueableItem & { providerUrl?: string | null },
): Promise<ContinueResult> {
  const result = await continueFromItem(item);
  if (item.providerUrl) {
    useAppStore.getState().setProviderUrlReference(item.providerUrl);
  }
  return result;
}
```

#### 13. MODIFY `ui/src/components/ResultActions.tsx`
After "Continue here" button, add:
```tsx
{isGrokProvider && actionImage.providerUrl && isWithinOneHour && (
  <button
    type="button"
    className="action-btn"
    onClick={continueAsUrl}
    title={t("result.continueAsUrlTitle")}
  >
    {t("result.continueAsUrl")}
  </button>
)}
```

Where:
```ts
const isGrokProvider = actionImage.provider === "grok" || actionImage.provider === "grok-api";
const isWithinOneHour = Boolean(actionImage.createdAt && (Date.now() - actionImage.createdAt) < 3_600_000);

const continueAsUrl = async () => {
  await continueFromItemAsUrl(actionImage);
  const promptEl = document.querySelector<HTMLTextAreaElement>(
    'textarea[name="prompt"], textarea#prompt, .sidebar textarea',
  );
  if (promptEl) {
    promptEl.focus();
    promptEl.setSelectionRange(promptEl.value.length, promptEl.value.length);
  }
  showToast(t("toast.continueAsUrlStarted"));
};
```

#### 14. MODIFY `ui/src/store/storeGenImpl.ts`
In `runGenerateImpl`, request body:
```diff
 {
   prompt,
   ...otherFields,
+  ...(s.providerUrlReference ? { providerUrl: s.providerUrlReference } : {}),
   ...(s.referenceImages.length ? { references: s.referenceImages.map(stripDataUrlPrefix) } : {}),
 }
```

After generation completes (in finally or after res):
```diff
+ set({ providerUrlReference: null });
```

#### 15. MODIFY `ui/src/store/storeVideoImpl.ts`
In `runVideoGenerateImpl`, request body:
```diff
 {
   prompt,
+  ...(get().providerUrlReference ? { providerUrl: get().providerUrlReference } : {}),
   referenceImages: refs.length >= 2 ? refs : undefined,
```

After generation completes:
```diff
+ set({ providerUrlReference: null });
```

### Layer 5: i18n

#### 16. MODIFY `ui/src/i18n/en.json` + `ko.json`
```json
"continueAsUrl": "URL continue",
"continueAsUrlTitle": "Use provider URL directly — valid ~1 hour after generation",
"continueAsUrlStarted": "Provider URL set as reference. Edit prompt and generate."
```
```json
"continueAsUrl": "URL로 이어서",
"continueAsUrlTitle": "프로바이더 URL 직접 사용 — 생성 후 약 1시간 유효",
"continueAsUrlStarted": "프로바이더 URL을 참조로 설정했어요. 프롬프트 수정 후 생성하세요."
```

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| `response_format: "url"` 전환으로 이미지 다운로드 실패 | Medium | downloadGrokImageUrl에 타임아웃 + 에러 핸들링. 기존 downloadVideo 패턴 재사용 |
| xAI URL 1시간 내 만료 | Low | 프론트엔드 TTL 체크로 버튼 자동 비활성화 |
| MIME 타입 감지 차이 | Low | Content-Type 헤더 + buffer magic bytes 이중 감지 |
| 기존 non-Grok 프로바이더 영향 | None | response_format 변경은 grokImageCore.ts의 imagePayload/imageEditPayload에만 적용, 다른 프로바이더는 자체 어댑터 사용 |
| providerUrlReference 상태 누수 | Low | finally 블록에서 항상 clear |

## Verification Criteria
1. `npx tsc --noEmit` clean
2. 기존 테스트 전체 PASS
3. Grok 이미지 생성 → 갤러리에 표시 + providerUrl 사이드카에 저장
4. "URL로 이어서" 버튼: Grok 항목에만 표시, 1시간 후 사라짐
5. I2I: URL 레퍼런스로 편집 생성 성공
6. I2V: URL 소스로 비디오 생성 성공
