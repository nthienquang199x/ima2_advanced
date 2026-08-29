# 01 — API 키 관리 GTM 전략: 웹 UI 기반 키 입력 시스템

> 날짜: 2026-06-02
> 상태: 설계 문서 (구현 전)
> 의존: `00_grok-gemini-api-provider-research.md`
> 요약: GPT(OpenAI), Grok(xAI), Gemini(Google) API 키를 localhost 웹 설정에서 안전하게 붙여넣기하는 GTM(Go-To-Market) 전략

---

## 1. 현재 상태 분석

### 1.1 현재 API 키 관리 방식

| 방식 | 설명 | UX 난이도 |
|------|------|-----------|
| 환경 변수 | `OPENAI_API_KEY=sk-...` 셸에 export | ⚠️ 터미널 필요 |
| config.json | `~/.ima2/config.json`에 `{ "apiKey": "sk-..." }` | ⚠️ 파일 편집 필요 |
| progrok login | `ima2 grok login` CLI 명령 | ⚠️ CLI 전용 |
| agy CLI | Antigravity CLI 자체 인증 | ⚠️ CLI 전용 |

**문제점:**
- 웹 UI에서 API 키를 입력할 수 없음
- ProviderSelect에서 "Grok > API"와 "Gemini > API"가 `disabled: true`로 비활성화
- 비개발자가 접근하기 어려움 (터미널/파일 편집 필요)

### 1.2 현재 코드 경로

```
API 키 로드:
  server.ts:44 loadApiKey()
    → env OPENAI_API_KEY
    → config.json { apiKey: "..." }
    → null

API 키 검증:
  routes/health.ts:98 GET /api/billing
    → ctx.apiKey로 OpenAI /v1/models 호출
    → apiKeyValid: true/false 반환

UI 표시:
  AccountSettings.tsx
    → useBilling() hook → GET /api/billing
    → apiKeySource: "env" | "config" | "none"
    → apiKeyValid: boolean
    → 상태 표시만 (입력 UI 없음)
```

---

## 2. GTM 전략 개요

### 2.1 핵심 원칙

1. **붙여넣기 한 번으로 끝** — 복사 → 붙여넣기 → 저장 → 즉시 사용
2. **키는 절대 보이지 않음** — `type="password"` + 마스킹 (`sk-...abc`)
3. **localhost 전용 보안** — 외부 노출 없음, 서버 메모리 + 로컬 파일에만 저장
4. **기존 시스템과 호환** — env 변수 우선, 웹 입력은 config.json에 저장
5. **즉시 검증** — 붙여넣기 후 실시간 유효성 확인 + 상태 dot 업데이트

### 2.2 사용자 흐름 (최종 목표)

```
사용자가 Settings > Account 열기
  ↓
"GPT API Key" / "Grok API Key" / "Gemini API Key" 입력 필드 표시
  ↓
키 붙여넣기 (Ctrl/Cmd+V)
  ↓
입력 필드: ●●●●●●●●●●abc (마스킹)
  ↓
"Save" 버튼 클릭
  ↓
POST /api/keys/{provider} → 서버가 키 검증 → config.json 저장
  ↓
실시간 상태 업데이트: 🟢 Ready
  ↓
ProviderSelect에서 해당 프로바이더 즉시 활성화
```

---

## 3. 상세 설계

### 3.1 API 엔드포인트 설계

#### 3.1.1 키 저장 — `PUT /api/keys/:provider`

```
PUT /api/keys/openai
PUT /api/keys/xai
PUT /api/keys/gemini
```

**요청:**
```json
{
  "apiKey": "sk-proj-..."
}
```

**서버 처리:**
1. `provider` 파라미터 검증 (`openai | xai | gemini`)
2. API 키 포맷 사전 검증 (접두사 체크)
   - OpenAI: `sk-` 접두사
   - xAI: `xai-` 접두사
   - Gemini: `AI` 접두사 (Google AI Studio 키)
3. 실시간 검증 요청 (프로바이더별 경량 API 호출)
   - OpenAI: `GET https://api.openai.com/v1/models` (헤더에 키)
   - xAI: `GET https://api.x.ai/v1/models` (헤더에 키)
   - Gemini: `GET https://generativelanguage.googleapis.com/v1beta/models?key=...`
4. 검증 성공 시 `~/.ima2/config.json`에 저장
5. `RuntimeContext` 업데이트 (서버 재시작 불필요)

**응답:**
```json
// 성공
{ "ok": true, "provider": "openai", "source": "config", "valid": true }

// 키 포맷 오류
{ "ok": false, "error": "Invalid key format: OpenAI keys start with 'sk-'", "code": "INVALID_KEY_FORMAT" }

// 검증 실패
{ "ok": false, "error": "API key is invalid or revoked", "code": "KEY_VALIDATION_FAILED" }
```

#### 3.1.2 키 상태 조회 — `GET /api/keys/status`

**응답:**
```json
{
  "openai": {
    "configured": true,
    "source": "config",
    "valid": true,
    "maskedKey": "sk-...abc"
  },
  "xai": {
    "configured": false,
    "source": "none",
    "valid": false,
    "maskedKey": null
  },
  "gemini": {
    "configured": true,
    "source": "env",
    "valid": true,
    "maskedKey": "AI...xyz"
  }
}
```

- `maskedKey`: 앞 2~3자 + `...` + 뒤 3자 (예: `sk-...abc`)
- 전체 키는 절대 API 응답에 포함하지 않음

#### 3.1.3 키 삭제 — `DELETE /api/keys/:provider`

```
DELETE /api/keys/openai
```

**응답:**
```json
{ "ok": true, "provider": "openai", "removed": true }
```

- config.json에서 해당 키만 제거
- env 변수로 설정된 키는 삭제 불가 → `{ "ok": false, "error": "Cannot remove env-sourced key", "code": "ENV_KEY_IMMUTABLE" }`

### 3.2 config.json 저장 형식

**현재:**
```json
{
  "apiKey": "sk-proj-..."
}
```

**변경 후:**
```json
{
  "apiKey": "sk-proj-...",
  "xaiApiKey": "xai-...",
  "geminiApiKey": "AIza..."
}
```

**키 이름 규칙:**
| 프로바이더 | config.json 키 | 환경 변수 |
|-----------|---------------|-----------|
| OpenAI | `apiKey` (기존 호환) | `OPENAI_API_KEY` |
| xAI | `xaiApiKey` | `XAI_API_KEY` |
| Gemini | `geminiApiKey` | `GEMINI_API_KEY` |

**로드 우선순위 (프로바이더별):**
```
env 변수 > config.json > none
```

### 3.3 서버 코드 변경

#### 3.3.1 `server.ts` — 키 로더 확장

```ts
// 현재: loadApiKey() → OpenAI만
// 변경: loadAllApiKeys() → 3개 프로바이더

async function loadAllApiKeys(): Promise<{
  openai: ApiKeyLoadResult;
  xai: ApiKeyLoadResult;
  gemini: ApiKeyLoadResult;
}> {
  const cfgPath = config.storage.configFile;
  let fileCfg: Record<string, string> = {};
  try {
    fileCfg = JSON.parse(await readFile(cfgPath, "utf-8"));
  } catch {}

  return {
    openai: {
      apiKey: process.env.OPENAI_API_KEY || fileCfg.apiKey || null,
      apiKeySource: process.env.OPENAI_API_KEY ? "env" : fileCfg.apiKey ? "config" : "none",
    },
    xai: {
      apiKey: process.env.XAI_API_KEY || fileCfg.xaiApiKey || null,
      apiKeySource: process.env.XAI_API_KEY ? "env" : fileCfg.xaiApiKey ? "config" : "none",
    },
    gemini: {
      apiKey: process.env.GEMINI_API_KEY || fileCfg.geminiApiKey || null,
      apiKeySource: process.env.GEMINI_API_KEY ? "env" : fileCfg.geminiApiKey ? "config" : "none",
    },
  };
}
```

#### 3.3.2 `RuntimeContext` 확장

```ts
// lib/runtimeContext.ts — 현재 OpenAI만
interface RuntimeContext {
  apiKey: string | null;
  apiKeySource: ApiKeySource;
  hasApiKey: boolean;
  openai: OpenAI | null;

  // 추가
  xaiApiKey: string | null;
  xaiApiKeySource: ApiKeySource;
  hasXaiApiKey: boolean;

  geminiApiKey: string | null;
  geminiApiKeySource: ApiKeySource;
  hasGeminiApiKey: boolean;
}
```

#### 3.3.3 키 저장 라우트 — `routes/keys.ts` (신규)

```ts
import { readFile, writeFile } from "node:fs/promises";
import { config } from "../config.js";

const KEY_PREFIX_MAP: Record<string, string[]> = {
  openai: ["sk-"],
  xai: ["xai-"],
  gemini: ["AI"],
};

const VALIDATE_URL_MAP: Record<string, string> = {
  openai: "https://api.openai.com/v1/models",
  xai: "https://api.x.ai/v1/models",
  gemini: "https://generativelanguage.googleapis.com/v1beta/models",
};

const CONFIG_KEY_MAP: Record<string, string> = {
  openai: "apiKey",
  xai: "xaiApiKey",
  gemini: "geminiApiKey",
};

// PUT /api/keys/:provider
app.put("/api/keys/:provider", async (req, res) => {
  const { provider } = req.params;
  const { apiKey } = req.body;

  // 1. provider 검증
  if (!KEY_PREFIX_MAP[provider]) {
    return res.status(400).json({ ok: false, code: "INVALID_PROVIDER" });
  }

  // 2. 포맷 검증
  const validPrefix = KEY_PREFIX_MAP[provider].some(p => apiKey.startsWith(p));
  if (!validPrefix) {
    return res.status(400).json({
      ok: false,
      error: `Invalid key format for ${provider}`,
      code: "INVALID_KEY_FORMAT",
    });
  }

  // 3. 실시간 검증
  try {
    const url = VALIDATE_URL_MAP[provider];
    const headers: Record<string, string> = { "Content-Type": "application/json" };

    if (provider === "gemini") {
      // Gemini는 쿼리 파라미터로 인증
      const validateRes = await fetch(`${url}?key=${apiKey}`, {
        signal: AbortSignal.timeout(10_000),
      });
      if (!validateRes.ok) throw new Error("Validation failed");
    } else {
      // OpenAI, xAI는 Bearer 토큰
      headers.Authorization = `Bearer ${apiKey}`;
      const validateRes = await fetch(url, {
        headers,
        signal: AbortSignal.timeout(10_000),
      });
      if (!validateRes.ok) throw new Error("Validation failed");
    }
  } catch {
    return res.status(400).json({
      ok: false,
      error: "API key validation failed",
      code: "KEY_VALIDATION_FAILED",
    });
  }

  // 4. config.json에 저장
  const cfgPath = config.storage.configFile;
  let existing: Record<string, unknown> = {};
  try {
    existing = JSON.parse(await readFile(cfgPath, "utf-8"));
  } catch {}
  existing[CONFIG_KEY_MAP[provider]] = apiKey;
  await writeFile(cfgPath, JSON.stringify(existing, null, 2), "utf-8");

  // 5. RuntimeContext 핫 업데이트 (서버 재시작 불필요)
  ctx.updateApiKey(provider, apiKey, "config");

  return res.json({ ok: true, provider, source: "config", valid: true });
});
```

### 3.4 UI 컴포넌트 설계

#### 3.4.1 `ApiKeyInput` 컴포넌트

```
┌─────────────────────────────────────────────┐
│ GPT API Key                                  │
│ ┌──────────────────────────────────┐ ┌─────┐ │
│ │ ●●●●●●●●●●●●●●●●●●●●●●●●●abc  │ │Save │ │
│ └──────────────────────────────────┘ └─────┘ │
│ 🟢 Valid · Source: config                    │
│                                              │
│ Grok API Key (xAI)                           │
│ ┌──────────────────────────────────┐ ┌─────┐ │
│ │ Paste your xAI API key here     │ │Save │ │
│ └──────────────────────────────────┘ └─────┘ │
│ ⚪ Not configured                            │
│                                              │
│ Gemini API Key                               │
│ ┌──────────────────────────────────┐ ┌─────┐ │
│ │ Paste your Gemini API key here  │ │Save │ │
│ └──────────────────────────────────┘ └─────┘ │
│ ⚪ Not configured                            │
└─────────────────────────────────────────────┘
```

**동작 규칙:**

| 상태 | 입력 필드 | 버튼 | 상태 표시 |
|------|----------|------|----------|
| 미설정 | placeholder 텍스트, 비어있음 | Save (disabled) | ⚪ Not configured |
| env 설정됨 | `●●●●...abc` (readonly) | — | 🟢 Valid · Source: env |
| config 설정됨 | `●●●●...abc` (편집 가능) | Save | 🟢 Valid · Source: config |
| 입력 중 | `type="password"`, 입력값 | Save (active) | ⏳ Validating... |
| 검증 실패 | 입력값 유지, 빨간 테두리 | Save | 🔴 Invalid key |
| 검증 성공 | `●●●●...abc`로 전환 | ✓ Saved | 🟢 Valid · Source: config |

#### 3.4.2 보안 세부사항

```tsx
// ApiKeyInput.tsx 핵심 로직

// 1. 입력 필드는 항상 type="password"
<input
  type="password"
  autoComplete="off"
  spellCheck={false}
  data-1p-ignore          // 1Password 자동완성 방지
  data-lpignore="true"    // LastPass 자동완성 방지
  data-form-type="other"  // 브라우저 자동저장 방지
/>

// 2. 마스킹: 서버에서만 반환 (프론트에서 전체 키를 보관하지 않음)
// GET /api/keys/status → maskedKey: "sk-...abc"

// 3. 붙여넣기 후 즉시 Save 활성화
const handlePaste = (e: React.ClipboardEvent) => {
  const pasted = e.clipboardData.getData("text").trim();
  setDirty(true);
  setKey(pasted);
};

// 4. 저장 시 서버로 전체 키 전송 → 즉시 메모리에서 삭제
const handleSave = async () => {
  setSaving(true);
  const res = await fetch(`/api/keys/${provider}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ apiKey: key }),
  });
  setKey("");        // 메모리에서 즉시 삭제
  setDirty(false);
  // 상태 새로고침
  mutateKeyStatus();
};
```

#### 3.4.3 `AccountSettings.tsx` 확장 — 기존 레이아웃에 삽입

현재 `AccountSettings`는 3개 `settings-row` 카드:
1. GPT OAuth 상태
2. API key 상태 (읽기전용)
3. Grok 프록시 상태

**변경 후:**
1. GPT OAuth 상태 (기존)
2. **GPT API Key 입력** (신규 — `ApiKeyInput provider="openai"`)
3. Grok OAuth 프록시 상태 (기존)
4. **Grok API Key 입력** (신규 — `ApiKeyInput provider="xai"`)
5. Gemini agy 상태 (기존 + 표현 변경)
6. **Gemini API Key 입력** (신규 — `ApiKeyInput provider="gemini"`)

각 프로바이더 섹션이 "OAuth/CLI 방식"과 "API Key 방식"을 나란히 보여주고, 사용자가 선택할 수 있게.

#### 3.4.4 ProviderSelect 그리드 활성화

**변경 전:**
```ts
// ProviderSelect.tsx:83
{ value: "api", label: "API", disabled: true },  // Grok API
// ProviderSelect.tsx:90
{ value: "api", label: "API", disabled: true },  // Gemini API
```

**변경 후:**
```ts
// disabled를 동적으로 결정
{ value: "grok-api", label: "API", disabled: !hasXaiApiKey },
{ value: "gemini-api", label: "API", disabled: !hasGeminiApiKey },
```

### 3.5 config.json 보안 고려사항

#### 3.5.1 파일 권한

```ts
// 키 저장 시 파일 권한 제한
import { chmod } from "node:fs/promises";
await writeFile(cfgPath, JSON.stringify(cfg, null, 2), "utf-8");
await chmod(cfgPath, 0o600);  // owner only (rw-------)
```

#### 3.5.2 키 절대 로깅하지 않음

```ts
// logger.ts에 키 마스킹 필터 추가
function redactSecrets(obj: Record<string, unknown>) {
  const sensitiveKeys = ["apiKey", "xaiApiKey", "geminiApiKey", "authorization"];
  for (const key of Object.keys(obj)) {
    if (sensitiveKeys.includes(key.toLowerCase())) {
      obj[key] = "***REDACTED***";
    }
  }
}
```

#### 3.5.3 localhost 전용 보안

```
ima2-gen 서버는 127.0.0.1에서만 수신 (기본값).
→ /api/keys/* 엔드포인트는 외부에서 접근 불가.
→ 추가 인증 불필요 (localhost 신뢰 모델).
→ 만약 외부 바인딩 시: /api/keys/* 를 127.0.0.1에서만 허용하는 미들웨어 추가.
```

---

## 4. 프로바이더별 키 검증 세부사항

### 4.1 OpenAI (GPT)

| 항목 | 값 |
|------|-----|
| 키 접두사 | `sk-` 또는 `sk-proj-` |
| 검증 엔드포인트 | `GET https://api.openai.com/v1/models` |
| 검증 헤더 | `Authorization: Bearer sk-...` |
| 성공 기준 | HTTP 200 |
| 실패 코드 | 401 (invalid), 429 (rate limited), 403 (no access) |
| 검증 비용 | 무료 (모델 목록 조회) |
| 타임아웃 | 10초 |

### 4.2 xAI (Grok)

| 항목 | 값 |
|------|-----|
| 키 접두사 | `xai-` |
| 검증 엔드포인트 | `GET https://api.x.ai/v1/models` |
| 검증 헤더 | `Authorization: Bearer xai-...` |
| 성공 기준 | HTTP 200 |
| 실패 코드 | 401/403 (invalid), 429 (rate limited) |
| 검증 비용 | 무료 (모델 목록 조회) |
| 타임아웃 | 10초 |

### 4.3 Gemini (Google)

| 항목 | 값 |
|------|-----|
| 키 접두사 | `AI` (Google AI Studio 키: `AIza...`) |
| 검증 엔드포인트 | `GET https://generativelanguage.googleapis.com/v1beta/models?key=...` |
| 검증 방식 | 쿼리 파라미터 (`?key=`) |
| 성공 기준 | HTTP 200 |
| 실패 코드 | 400/403 (invalid key) |
| 검증 비용 | 무료 (모델 목록 조회) |
| 타임아웃 | 10초 |

---

## 5. UI/UX 상세 디자인

### 5.1 키 입력 필드 상태 머신

```
                ┌──────────────┐
                │   EMPTY      │ 미설정, placeholder 표시
                └──────┬───────┘
                       │ 붙여넣기/입력
                       ▼
                ┌──────────────┐
                │   DIRTY      │ 입력 중, Save 버튼 활성화
                └──────┬───────┘
                       │ Save 클릭
                       ▼
                ┌──────────────┐
                │  VALIDATING  │ 서버 검증 중, 스피너 표시
                └──────┬───────┘
               ┌───────┴────────┐
               ▼                ▼
        ┌──────────┐     ┌──────────┐
        │  VALID   │     │ INVALID  │
        │ 🟢 저장됨 │     │ 🔴 실패  │
        └──────────┘     └──────┬───┘
                                │ 재입력
                                ▼
                         ┌──────────────┐
                         │   DIRTY      │
                         └──────────────┘
```

### 5.2 마스킹 규칙

| 원본 키 | 마스킹 결과 |
|---------|------------|
| `sk-proj-abc...xyz123` | `sk-p...123` |
| `xai-abc...def789` | `xai-...789` |
| `AIzaSyABC...XYZ` | `AIza...XYZ` |

규칙: **앞 4자** + `...` + **뒤 3자**

### 5.3 i18n 키 추가

```ts
// 한국어 (ko)
"settings.apiKeys.title": "API 키",
"settings.apiKeys.openai.label": "GPT API Key (OpenAI)",
"settings.apiKeys.openai.placeholder": "sk-proj-... 형식의 OpenAI API 키 붙여넣기",
"settings.apiKeys.xai.label": "Grok API Key (xAI)",
"settings.apiKeys.xai.placeholder": "xai-... 형식의 xAI API 키 붙여넣기",
"settings.apiKeys.gemini.label": "Gemini API Key (Google)",
"settings.apiKeys.gemini.placeholder": "AIza... 형식의 Google AI 키 붙여넣기",
"settings.apiKeys.save": "저장",
"settings.apiKeys.saved": "저장됨",
"settings.apiKeys.saving": "검증 중...",
"settings.apiKeys.remove": "삭제",
"settings.apiKeys.removeConfirm": "이 API 키를 삭제하시겠습니까?",
"settings.apiKeys.status.valid": "유효",
"settings.apiKeys.status.invalid": "유효하지 않은 키",
"settings.apiKeys.status.notConfigured": "미설정",
"settings.apiKeys.status.envSource": "환경 변수에서 로드됨",
"settings.apiKeys.status.configSource": "설정 파일에서 로드됨",
"settings.apiKeys.status.envImmutable": "환경 변수로 설정된 키는 웹에서 변경할 수 없습니다",
"settings.apiKeys.formatError.openai": "OpenAI 키는 'sk-'로 시작해야 합니다",
"settings.apiKeys.formatError.xai": "xAI 키는 'xai-'로 시작해야 합니다",
"settings.apiKeys.formatError.gemini": "Gemini 키는 'AI'로 시작해야 합니다",

// 영어 (en)
"settings.apiKeys.title": "API Keys",
"settings.apiKeys.openai.label": "GPT API Key (OpenAI)",
"settings.apiKeys.openai.placeholder": "Paste your OpenAI API key (sk-proj-...)",
// ... 동일 구조
```

### 5.4 CSS 클래스 (기존 설정 테마 준수)

```css
/* 기존 settings-row 패턴 재사용 */
.api-key-row {
  /* settings-row와 동일한 패딩/마진 */
}

.api-key-input {
  font-family: var(--font-mono);
  letter-spacing: 0.05em;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 12px;
  width: 100%;
  color: var(--text-1);
  /* 비밀번호 필드 특성 */
  -webkit-text-security: disc;
}

.api-key-input:focus {
  border-color: var(--accent);
  outline: none;
  box-shadow: 0 0 0 2px var(--accent-alpha-20);
}

.api-key-input.is-invalid {
  border-color: var(--error);
}

.api-key-input[readonly] {
  opacity: 0.7;
  cursor: not-allowed;
}

.api-key-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.api-key-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 0.85em;
  color: var(--text-2);
}
```

---

## 6. 구현 순서 (GTM 페이즈)

### Phase 1: OpenAI API Key 웹 입력 (기존 패턴 확장)

가장 단순 — 이미 config.json 경로가 존재하고, `/api/billing`에서 검증 로직이 있음.

1. `routes/keys.ts` 신규 생성 — `PUT /api/keys/openai`, `GET /api/keys/status`, `DELETE /api/keys/openai`
2. `ui/src/components/ApiKeyInput.tsx` 신규 생성
3. `AccountSettings.tsx`에 GPT API Key 입력 필드 추가
4. `server.ts`의 `loadApiKey()` → config.json `apiKey` 핫 리로드 지원

### Phase 2: xAI (Grok) API Key

OpenAI 패턴 복제 + Grok 어댑터 분기 추가.

1. `config.ts`에 `xaiApiKey` 필드 추가
2. `server.ts`에 xAI 키 로드 추가
3. `lib/grokImageAdapter.ts`에 API 키 모드 분기 (progrok vs 직접)
4. `routes/keys.ts`에 xAI 핸들러 추가
5. `ProviderSelect.tsx`에서 "Grok > API" 셀 활성화
6. `AccountSettings.tsx`에 Grok API Key 입력 추가

### Phase 3: Gemini API Key

새 어댑터 작성 필요 — 가장 작업량 큼.

1. `config.ts`에 `geminiApiKey` 필드 추가
2. `lib/geminiApiImageAdapter.ts` 신규 생성 (REST 직접 호출)
3. `routes/keys.ts`에 Gemini 핸들러 추가
4. `lib/providerOptions.ts`에 `gemini-api` 분기 추가
5. 라우트 핸들러 4개에 `gemini-api` 분기 추가
6. `ProviderSelect.tsx`에서 "Gemini > API" 셀 활성화
7. `AccountSettings.tsx`에 Gemini API Key 입력 추가

---

## 7. Provider 타입 확장 전략

### 7.1 선택지

**Option A: 기존 Provider에 "mode" 추가**

```ts
type Provider = "oauth" | "api" | "grok" | "agy";
// grok = progrok OAuth
// grok-api = xAI API key (새 Provider 값)
// gemini-api = Gemini API key (새 Provider 값)
```

```ts
// 변경
type Provider = "oauth" | "api" | "grok" | "grok-api" | "agy" | "gemini-api";
```

**Option B: Provider + AuthMode 분리** (더 깨끗)

```ts
type ProviderFamily = "openai" | "grok" | "gemini";
type AuthMode = "oauth" | "api";
// Provider = ProviderFamily × AuthMode
```

**권장: Option A** — 기존 코드 변경 최소화, `resolveProviderOptions()`에 분기만 추가.

### 7.2 ProviderSelect 그리드 변경

```ts
// 현재
{ value: "api", label: "API", disabled: true },  // Grok API
{ value: "api", label: "API", disabled: true },  // Gemini API

// 변경
{ value: "grok-api", label: "API", disabled: !hasXaiApiKey },
{ value: "gemini-api", label: "API", disabled: !hasGeminiApiKey },
```

> ⚠️ 현재 Grok과 Gemini의 API 셀이 둘 다 `value: "api"`를 사용하고 있어서 충돌 위험. 각각 고유한 Provider 값 필요.

---

## 8. 핵심 파일 변경 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `routes/keys.ts` | **NEW** | API 키 CRUD 엔드포인트 |
| `ui/src/components/ApiKeyInput.tsx` | **NEW** | 범용 API 키 입력 컴포넌트 |
| `lib/geminiApiImageAdapter.ts` | **NEW** (Phase 3) | Gemini REST 직접 어댑터 |
| `config.ts` | MODIFY | `xaiApiKey`, `geminiApiKey` 필드 추가 |
| `server.ts` | MODIFY | 키 로더 확장 + RuntimeContext 확장 |
| `lib/runtimeContext.ts` | MODIFY | xAI/Gemini 키 필드 추가 |
| `lib/providerOptions.ts` | MODIFY | `grok-api`, `gemini-api` 분기 |
| `lib/grokImageAdapter.ts` | MODIFY | API 키 모드 분기 |
| `lib/capabilities.ts` | MODIFY | VALID_PROVIDERS 확장 |
| `ui/src/types.ts` | MODIFY | Provider 타입 확장 |
| `ui/src/components/AccountSettings.tsx` | MODIFY | 키 입력 필드 3개 추가 |
| `ui/src/components/ProviderSelect.tsx` | MODIFY | API 셀 활성화 + 고유 값 |
| `ui/src/i18n/ko.ts` | MODIFY | i18n 키 추가 |
| `ui/src/i18n/en.ts` | MODIFY | i18n 키 추가 |
| `ui/src/hooks/useKeyStatus.ts` | **NEW** | 키 상태 폴링 훅 |
| `routes/generate.ts` | MODIFY | `grok-api`, `gemini-api` 분기 |
| `routes/edit.ts` | MODIFY | 동일 |
| `routes/multimode.ts` | MODIFY | 동일 |
| `routes/nodes.ts` | MODIFY | 동일 |

---

## 9. 보안 체크리스트

- [ ] API 키가 `type="password"` 필드에만 입력됨
- [ ] 서버 응답에 전체 키가 포함되지 않음 (마스킹만)
- [ ] config.json 파일 권한이 0o600 (owner only)
- [ ] 로그에 API 키가 기록되지 않음 (redaction)
- [ ] 브라우저 자동완성/비밀번호 매니저가 키를 캡처하지 않음 (`data-1p-ignore` 등)
- [ ] `/api/keys/*` 엔드포인트가 localhost에서만 접근 가능
- [ ] 프론트엔드에서 저장 후 키를 메모리에서 즉시 삭제
- [ ] env 변수로 설정된 키는 웹에서 삭제/수정 불가
- [ ] HTTPS가 아닌 localhost HTTP 연결에서도 키가 안전 (로컬 루프백)
