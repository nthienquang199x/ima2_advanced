# API Key Accordion UI + Vertex AI JSON Support

**Date:** 2026-06-02
**Scope:** UI 리팩토링 + Vertex AI 백엔드 지원

---

## Part 1: 요약 (비개발자용)

설정 페이지의 API 키 입력 영역을 **하나의 접이식 패널**로 통합합니다. 현재는 GPT, Grok, Gemini 키가 세 개의 큰 카드로 나열되어 공간을 많이 차지하는데, 이를 한 줄로 접고 필요할 때만 펼치는 구조로 바꿉니다.

Gemini 섹션에는 **"API Key" ↔ "Vertex JSON"** 전환 드롭다운을 추가합니다. 기존 Gemini API 키 외에 Google Cloud 서비스 계정 JSON을 붙여넣어 Vertex AI 경로로도 이미지를 생성할 수 있게 됩니다.

---

## Part 2: Diff-Level Plan

### Phase 1: Backend — Vertex AI Auth + Storage

#### 1.1 NEW `lib/vertexAuth.ts`
서비스 계정 JSON → 액세스 토큰 변환 헬퍼.

```typescript
import { GoogleAuth } from "google-auth-library";

let cachedAuth: GoogleAuth | null = null;
let cachedProjectId: string | null = null;

export function initVertexAuth(serviceAccountJson: string): { projectId: string } {
  const parsed = JSON.parse(serviceAccountJson);
  cachedProjectId = parsed.project_id;
  cachedAuth = new GoogleAuth({
    credentials: parsed,
    scopes: ["https://www.googleapis.com/auth/cloud-platform"],
  });
  return { projectId: cachedProjectId };
}

export async function getVertexAccessToken(): Promise<string> {
  if (!cachedAuth) throw new Error("Vertex AI not initialized");
  const client = await cachedAuth.getClient();
  const token = await client.getAccessToken();
  if (!token.token) throw new Error("Failed to get Vertex AI access token");
  return token.token;
}

export function getVertexProjectId(): string | null {
  return cachedProjectId;
}

export function clearVertexAuth(): void {
  cachedAuth = null;
  cachedProjectId = null;
}
```

#### 1.2 MODIFY `package.json`
```diff
  "dependencies": {
+   "google-auth-library": "^9.17.0",
    "better-sqlite3": "^12.9.0",
```

#### 1.3 MODIFY `lib/runtimeContext.ts`
RuntimeContext 인터페이스에 vertex 필드 추가:

```diff
  geminiApiKey: string | undefined;
  geminiApiKeySource: ApiKeySource;
  hasGeminiApiKey: boolean;
+ vertexServiceAccountJson: string | undefined;
+ vertexProjectId: string | undefined;
+ hasVertexKey: boolean;
```

`requireRuntimeContext()`에 초기화 추가:

```diff
  const hasGeminiApiKey = !!geminiApiKey;
+ const vertexServiceAccountJson = raw.vertexServiceAccountJson ?? undefined;
+ const vertexProjectId = raw.vertexProjectId ?? undefined;
+ const hasVertexKey = !!vertexServiceAccountJson;
```

#### 1.4 MODIFY `server.ts`
`loadVertexKey()` 함수 추가 (loadGeminiApiKey 패턴 동일):

```typescript
function loadVertexKey(): { json: string | null; projectId: string | null; source: ApiKeySource } {
  // 1. env: VERTEX_SERVICE_ACCOUNT_JSON
  // 2. config.json: vertexServiceAccountJson
  // JSON 파싱 → project_id 추출
}
```

컨텍스트 생성부에 vertex 필드 추가.

#### 1.5 MODIFY `routes/keys.ts`
KeyProvider 타입에 `"vertex"` 추가:

```diff
- type KeyProvider = "openai" | "xai" | "gemini";
+ type KeyProvider = "openai" | "xai" | "gemini" | "vertex";
```

**PUT /api/keys/vertex:**
- JSON.parse 검증 (type === "service_account", project_id 존재)
- config.json에 `vertexServiceAccountJson`으로 저장
- `initVertexAuth()`로 핫 로드
- Vertex AI API 테스트 호출로 검증

**GET /api/keys/status:**
- vertex 섹션 추가: `{ configured, source, valid, maskedKey: "${projectId}" }`

**DELETE /api/keys/vertex:**
- config.json에서 제거, `clearVertexAuth()` 호출

#### 1.6 MODIFY `lib/geminiApiImageAdapter.ts`
기존 `generateViaGeminiApi()` 함수에 Vertex AI 경로 추가:

```diff
  export async function generateViaGeminiApi(
    ctx: RuntimeContext,
    ...
  ): Promise<GeminiApiGenerateResult> {
+   // Vertex AI path: service account JSON → access token → Vertex endpoint
+   const useVertex = !ctx.geminiApiKey && ctx.hasVertexKey;
+   
+   let url: string;
+   let headers: Record<string, string>;
+   
+   if (useVertex) {
+     const token = await getVertexAccessToken();
+     const projectId = getVertexProjectId();
+     url = `https://aiplatform.googleapis.com/v1/projects/${projectId}/locations/global/publishers/google/models/${apiModelId}:generateContent`;
+     headers = { "Content-Type": "application/json", "Authorization": `Bearer ${token}` };
+   } else {
      // existing API key path
+     url = `https://generativelanguage.googleapis.com/v1beta/models/${apiModelId}:generateContent?key=${ctx.geminiApiKey}`;
+     headers = { "Content-Type": "application/json" };
+   }
    
    // request body는 동일 (contents + generationConfig)
```

---

### Phase 2: Frontend — Accordion + Vertex JSON Input

#### 2.1 MODIFY `ui/src/components/AccountSettings.tsx`
3개 ApiKeyInput을 아코디언으로 감싸기:

```tsx
const [keysOpen, setKeysOpen] = useState(false);

// ... 기존 OAuth/API/Grok status rows ...

{keyStatus && (
  <article className="settings-row settings-accordion">
    <button
      className="settings-accordion__trigger"
      onClick={() => setKeysOpen(!keysOpen)}
    >
      <h4>API Keys</h4>
      <span className="settings-accordion__arrow">{keysOpen ? "▲" : "▼"}</span>
    </button>
    {keysOpen && (
      <div className="settings-accordion__body">
        <ApiKeyInput provider="openai" ... />
        <ApiKeyInput provider="xai" ... />
        <GeminiKeySection
          keyStatus={keyStatus}
          onSaved={mutateKeys}
        />
      </div>
    )}
  </article>
)}
```

#### 2.2 NEW `ui/src/components/GeminiKeySection.tsx`
Gemini 전용 섹션 — API Key ↔ Vertex JSON 서브 드롭다운:

```tsx
export function GeminiKeySection({ keyStatus, onSaved }) {
  const [authMode, setAuthMode] = useState<"apikey" | "vertex">("apikey");

  return (
    <div className="gemini-key-section">
      <div className="gemini-key-section__header">
        <h5>Gemini (Google)</h5>
        <select
          value={authMode}
          onChange={(e) => setAuthMode(e.target.value as "apikey" | "vertex")}
          className="gemini-auth-mode-select"
        >
          <option value="apikey">API Key</option>
          <option value="vertex">Vertex JSON</option>
        </select>
      </div>

      {authMode === "apikey" ? (
        <ApiKeyInput provider="gemini" ... />
      ) : (
        <VertexJsonInput
          configured={keyStatus.vertex?.configured ?? false}
          maskedKey={keyStatus.vertex?.maskedKey ?? null}
          source={keyStatus.vertex?.source ?? "none"}
          onSaved={onSaved}
        />
      )}
    </div>
  );
}
```

#### 2.3 NEW `ui/src/components/VertexJsonInput.tsx`
서비스 계정 JSON textarea 입력:

```tsx
export function VertexJsonInput({ configured, maskedKey, source, onSaved }) {
  const [json, setJson] = useState("");
  // textarea + Save/Remove 버튼
  // PUT /api/keys/vertex { serviceAccountJson: json }
  // 검증 실패 시 에러 표시
}
```

#### 2.4 MODIFY `ui/src/hooks/useKeyStatus.ts`
```diff
- export type KeyStatus = Record<"openai" | "xai" | "gemini", KeyStatusEntry>;
+ export type KeyStatus = Record<"openai" | "xai" | "gemini" | "vertex", KeyStatusEntry>;
```

#### 2.5 MODIFY `ui/src/index.css`
아코디언 + Gemini 서브 드롭다운 + textarea 스타일 추가:

```css
/* Accordion */
.settings-accordion { ... }
.settings-accordion__trigger { display: flex; justify-content: space-between; cursor: pointer; }
.settings-accordion__body { padding-top: 12px; }
.settings-accordion__arrow { transition: transform 0.2s; }

/* Gemini auth mode */
.gemini-key-section__header { display: flex; align-items: center; gap: 12px; }
.gemini-auth-mode-select { background: var(--surface-2); border: 1px solid var(--border); ... }

/* Vertex JSON textarea */
.vertex-json-textarea { font-family: var(--mono); min-height: 120px; resize: vertical; ... }
```

#### 2.6 MODIFY `ui/src/i18n/en.json` + `ko.json`
```json
"vertex": {
  "label": "Vertex AI (Service Account)",
  "placeholder": "Paste your Google Cloud service account JSON...",
  "authModeApiKey": "API Key",
  "authModeVertex": "Vertex JSON"
}
```

---

### Phase 3: Integration + Validation

#### 3.1 `npm install google-auth-library`
#### 3.2 `npx tsc --noEmit` — TypeScript 빌드 통과 확인
#### 3.3 `npm run build` — UI + Server 빌드
#### 3.4 서버 시작 → `/api/keys/status` API 테스트
#### 3.5 CDP 스크린샷으로 아코디언 UI 확인

---

## File Change Summary

| Action | File | Description |
|--------|------|-------------|
| NEW | `lib/vertexAuth.ts` | Vertex AI 인증 헬퍼 |
| NEW | `ui/src/components/GeminiKeySection.tsx` | Gemini 서브 드롭다운 |
| NEW | `ui/src/components/VertexJsonInput.tsx` | Vertex JSON textarea |
| MODIFY | `package.json` | google-auth-library 추가 |
| MODIFY | `lib/runtimeContext.ts` | vertex 필드 추가 |
| MODIFY | `server.ts` | loadVertexKey() + 컨텍스트 확장 |
| MODIFY | `routes/keys.ts` | vertex provider CRUD |
| MODIFY | `lib/geminiApiImageAdapter.ts` | Vertex AI 경로 분기 |
| MODIFY | `ui/src/components/AccountSettings.tsx` | 아코디언 래핑 |
| MODIFY | `ui/src/hooks/useKeyStatus.ts` | vertex 타입 추가 |
| MODIFY | `ui/src/index.css` | 아코디언 + textarea 스타일 |
| MODIFY | `ui/src/i18n/en.json` | vertex i18n 추가 |
| MODIFY | `ui/src/i18n/ko.json` | vertex i18n 추가 |
