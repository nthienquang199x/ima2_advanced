# Gemini/Vertex 3종 수정 계획

> 작성일: 2026-06-10 · 근거 조사: devlog/02_vertex-api-format-research.md

## Part 1 — 쉬운 설명

1. **Vertex 400 에러 수정**: Vertex AI로 이미지 생성 시 서버가 거부하는 `responseFormat` 필드 대신 Vertex가 인식하는 `imageConfig` 필드로 보낸다.
2. **인증 모드 드롭다운 고침**: 설정에서 "Vertex"로 바꿔도 다시 열면 "API Key"로 돌아가는 문제 — 서버가 기억하는 모드를 UI가 읽어오게 하고, 드롭다운 변경 즉시 서버에 저장한다.
3. **자동결정/커스텀 버튼 추가**: Nano Banana(Gemini API) 모드에도 GPT 모드처럼 "Auto"(모델이 비율 자동 결정)와 "Custom"(가로×세로 직접 입력) 버튼을 추가한다.

## Part 2 — Diff 수준 상세

### Fix 1 — Vertex imageConfig 포맷 (MODIFY `lib/geminiApiImageAdapter.ts`)

L120-132 교체:

```ts
// BEFORE
const imageParams = parseGeminiImageParams(options.size);
const imageConfig = { aspect_ratio: imageParams.aspectRatio, image_size: imageParams.imageSize };
const generationConfig: Record<string, unknown> = useVertex
  ? { responseModalities: ["TEXT", "IMAGE"], responseFormat: { image: imageConfig } }
  : { response_modalities: ["TEXT", "IMAGE"], response_format: { image: imageConfig } };

// AFTER
const isAutoSize = !options.size || options.size === "auto";
const imageParams = isAutoSize ? null : parseGeminiImageParams(options.size);
const generationConfig: Record<string, unknown> = useVertex
  ? {
      responseModalities: ["TEXT", "IMAGE"],
      ...(imageParams
        ? { imageConfig: { aspectRatio: imageParams.aspectRatio, imageSize: imageParams.imageSize } }
        : {}),
    }
  : {
      response_modalities: ["TEXT", "IMAGE"],
      ...(imageParams
        ? { response_format: { image: { aspect_ratio: imageParams.aspectRatio, image_size: imageParams.imageSize } } }
        : {}),
    };
```

- `size === "auto"` → image config 자체를 생략 → 모델이 자동 결정 (자동결정 버튼의 백엔드 의미)
- `parseGeminiImageParams`의 `"auto"` 처리 분기(L28)는 호출 전에 걸러지므로 그대로 둠 (방어 코드)

### Fix 2 — geminiAuthMode 영속화

**MODIFY `routes/keys.ts`** — `GET /api/keys/status` (L52-74) 응답에 추가:

```ts
status.geminiAuthMode = (ctx as any).geminiAuthMode
  || (vertexJson && !ctx.geminiApiKey ? "vertex" : "apikey");
```

**ADD `routes/keys.ts`** — 드롭다운 변경 즉시 저장용 엔드포인트 (vertex PUT 라우트 아래):

```ts
app.put("/api/keys/gemini-auth-mode", async (req: Request, res: Response) => {
  const { mode } = req.body as { mode?: string };
  if (mode !== "apikey" && mode !== "vertex") {
    return res.status(400).json({ ok: false, error: "mode must be apikey|vertex", code: "INVALID_MODE" });
  }
  const cfgPath = ctx.config.storage.configFile;
  let existing: Record<string, unknown> = {};
  try { existing = JSON.parse(await readFile(cfgPath, "utf-8")); } catch { /* new file */ }
  existing.geminiAuthMode = mode;
  await writeConfigAtomic(cfgPath, existing);
  (ctx as any).geminiAuthMode = mode;
  return res.json({ ok: true, geminiAuthMode: mode });
});
```

**MODIFY `ui/src/hooks/useKeyStatus.ts`** — 타입 확장:

```ts
export type KeyStatus = Record<"openai" | "xai" | "gemini" | "vertex", KeyStatusEntry> & {
  geminiAuthMode?: "apikey" | "vertex";
};
```

**MODIFY `ui/src/components/GeminiKeySection.tsx`** — 서버 값으로 초기화 + 변경 시 서버 저장:

```ts
const serverAuthMode: "apikey" | "vertex" =
  keyStatus.geminiAuthMode === "vertex" ? "vertex" : "apikey";
const [authMode, setAuthMode] = useState<"apikey" | "vertex">(serverAuthMode);
const [userPicked, setUserPicked] = useState(false);

useEffect(() => {
  if (userPicked) return;
  setAuthMode(serverAuthMode);
}, [serverAuthMode, userPicked]);

const handleModeChange = async (mode: "apikey" | "vertex") => {
  setUserPicked(true);
  setAuthMode(mode);
  try {
    await fetch("/api/keys/gemini-auth-mode", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
  } catch { /* keep local state; status poll will reconcile */ }
};
```

(select onChange → `handleModeChange(e.target.value as ...)`)

### Fix 3 — Gemini 모드 Auto/Custom 버튼 (MODIFY `ui/src/components/GenerationControlsPanel.tsx`)

- L89-90: auto 인식 — `const isGeminiAuto = isGeminiApi && sizePreset === "auto";`
  `geminiSettings`는 auto일 때 그리드 하이라이트 없음 처리 (`ratio: "", res: ""`)
- Resolution 그룹 아래 새 option-group 추가:
  - **Auto 버튼**: `setSizePreset("auto")` — active 조건 `sizePreset === "auto"` → getResolvedSizeImpl이 `"auto"` 전달 → 백엔드에서 image config 생략
  - **Custom 버튼**: 로컬 state `geminiCustomOpen` 토글 → W×H 숫자 입력 2개 + 적용 시 `setSizePreset("custom"); setCustomSize(w, h)` — 백엔드 `parseGeminiImageParams`가 최근접 비율/해상도로 매핑 (기존 로직 재사용, 변경 없음)
  - 입력 아래 매핑 프리뷰 표시: 백엔드와 동일한 최근접 비율 계산을 인라인로직으로 표시 (선택)
- 기존 ratio/res 그리드 버튼 클릭 시 `setGeminiSize()` → custom 전환 (기존 동작 유지)

### 검증 (Success Criteria)

1. `npx tsc --noEmit` 통과 (server + ui)
2. ui 빌드 통과 (`npm run build` 또는 vite build)
3. Vertex 모드 실생성: 400 `Unknown name "responseFormat"` 에러가 사라지고 이미지 생성 성공
4. 설정 드롭다운 vertex 선택 → 설정 닫고 다시 열어도 vertex 유지 (서버 재시작 후에도)
5. Gemini 모드 UI에 Auto/Custom 버튼 표시, Auto 시 요청 body에 image config 없음

### 파일 변경 요약

| 파일 | 작업 |
|------|------|
| `lib/geminiApiImageAdapter.ts` | MODIFY — Vertex imageConfig + auto 생략 |
| `routes/keys.ts` | MODIFY — status에 geminiAuthMode 추가 + PUT gemini-auth-mode 라우트 |
| `ui/src/hooks/useKeyStatus.ts` | MODIFY — KeyStatus 타입 확장 |
| `ui/src/components/GeminiKeySection.tsx` | MODIFY — 서버 authMode 동기화 |
| `ui/src/components/GenerationControlsPanel.tsx` | MODIFY — Auto/Custom 버튼 |
