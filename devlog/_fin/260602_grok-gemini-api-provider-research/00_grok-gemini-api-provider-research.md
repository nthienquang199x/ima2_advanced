# 00 — Grok API / Gemini API 직접 프로바이더 추가 가능성 조사

> 날짜: 2026-06-02
> 상태: 연구 완료 (구현 전)
> 요청: Grok API(xAI)와 Gemini API를 ima2-gen에 직접 API 키 방식으로 추가할 수 있는가?

---

## 1. 현재 ima2-gen 프로바이더 아키텍처

### 1.1 프로바이더 목록

```ts
// ui/src/types.ts:15
export type Provider = "oauth" | "api" | "grok" | "agy";
```

| Provider | 방식 | 어댑터 | 비고 |
|----------|------|--------|------|
| `oauth` | ChatGPT OAuth 프록시 경유 | `responsesImageAdapter.ts` | OpenAI Responses API |
| `api` | OpenAI API 키 직접 | `responsesImageAdapter.ts` | 동일 어댑터, 다른 인증 |
| `grok` | progrok 로컬 프록시 경유 | `grokImageAdapter.ts` | xAI Images API, OAuth 경유 |
| `agy` | Antigravity CLI 경유 | `agyImageAdapter.ts` | Gemini, `agy -p -` 스폰 |

### 1.2 프로바이더 라우팅 허브

**파일:** `lib/providerOptions.ts` (67줄)

```ts
// 핵심 분기 로직 (단순화)
if (provider === "agy")  → { model: "nano-banana-2", ... }
if (provider === "grok") → normalizeGrokImageModel(rawModel)
else                     → normalizeImageModel(rawModel)  // oauth | api
```

### 1.3 라우트 핸들러 분기 패턴

모든 생성 라우트가 동일 패턴:

```
routes/generate.ts, routes/edit.ts, routes/multimode.ts, routes/nodes.ts:
  if (activeProvider === "agy")   → generateViaAgy()
  if (activeProvider === "grok")  → generateViaGrok() / editViaGrok()
  else                            → generateViaResponses()
```

### 1.4 프로바이더 계약 (새 프로바이더 추가 시 필요한 것)

| 구성요소 | 파일 | 설명 |
|----------|------|------|
| 어댑터 모듈 | `lib/xxxImageAdapter.ts` | `{ b64, revisedPrompt, usage, webSearchCalls, mime }` 반환 |
| 모델 검증 | `lib/imageModels.ts` | `normalizeXxxModel()` 함수 |
| 프로바이더 옵션 | `lib/providerOptions.ts` | `resolveProviderOptions()` 분기 추가 |
| Config 섹션 | `config.ts` | 프로바이더별 설정 블록 |
| 라우트 분기 | `routes/generate.ts` 외 4개 | `activeProvider` 조건 분기 |
| UI 타입 | `ui/src/types.ts:15` | `Provider` 유니온 추가 |
| UI 모델 셀렉터 | `ui/src/components/ImageModelSelect.tsx` | 모델 옵션 추가 |
| UI 프로바이더 셀렉터 | `ui/src/components/ProviderSelect.tsx` | 그리드 셀 추가 |
| UI 모델 필터 | `ui/src/lib/imageModels.ts` | 프로바이더별 모델 필터 |
| Capabilities | `lib/capabilities.ts:10` | `VALID_PROVIDERS` 배열 |
| 상태 엔드포인트 | `routes/grok.ts` 참조 | `/api/xxx/status` (선택) |

### 1.5 UI 셀렉터 현황

**ProviderSelect 3열 그리드:**

| GPT | Grok | Gemini |
|-----|------|--------|
| OAuth ✅ | OAuth ✅ | agy ✅ |
| API ✅ | API *(disabled)* | API *(disabled)* |

**ImageModelSelect 구성:**
- GPT Image: `gpt-5.4-mini`, `gpt-5.4`, `gpt-5.5`
- Grok Image: `grok-imagine-image`, `grok-imagine-image-quality`
- Gemini Image: `nano-banana-2`
- Video: `grok-imagine-video`, `grok-imagine-video-1.5-preview`

---

## 2. Grok(xAI) API 직접 호출 계약

### 2.1 현재: progrok 프록시 경유

```
사용자 → ima2 서버 → progrok 프록시 (127.0.0.1:18645) → xAI API
                      (OAuth 처리)
```

- `progrok` = 번들된 npm 패키지 (`vendor/progrok-0.2.0.tgz`)
- xAI OAuth 토큰 관리를 대행
- 모든 요청에 `Authorization: "Bearer dummy"` 사용 (progrok이 실제 토큰 주입)

### 2.2 목표: xAI API 키 직접 호출

```
사용자 → ima2 서버 → xAI API (https://api.x.ai/v1)
                      (API key 직접)
```

### 2.3 xAI API 계약 상세

#### 기본 정보

| 항목 | 값 |
|------|-----|
| Base URL | `https://api.x.ai/v1` |
| 인증 | `Authorization: Bearer xai-...` |
| API 키 접두사 | `xai-` |
| SDK 호환 | OpenAI SDK 호환 (`base_url` 변경만으로 사용 가능) |

#### 이미지 생성 — `POST /v1/images/generations`

```json
{
  "model": "grok-imagine-image-quality",
  "prompt": "A futuristic city skyline at sunset",
  "n": 1,
  "response_format": "b64_json",
  "aspect_ratio": "16:9",
  "resolution": "1k"
}
```

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `model` | string | ✅ | 모델 ID |
| `prompt` | string | ✅ | 텍스트 설명 |
| `n` | integer | ❌ | 생성 수 (1–10) |
| `response_format` | string | ❌ | `"url"` (기본) 또는 `"b64_json"` |
| `aspect_ratio` | string | ❌ | `"1:1"`, `"16:9"` 등 |
| `resolution` | string | ❌ | `"1k"` 또는 `"2k"` |

> ⚠️ `size` 파라미터 없음. `aspect_ratio` + `resolution` 조합 사용.

**응답:**
```json
{
  "data": [{
    "b64_json": "...",
    "url": "https://imgen.x.ai/...",
    "mime_type": "image/jpeg",
    "revised_prompt": ""
  }],
  "usage": { "cost_in_usd_ticks": 200000000 }
}
```

#### 이미지 편집 — `POST /v1/images/edits`

```json
{
  "model": "grok-imagine-image-quality",
  "prompt": "Render as a pencil sketch",
  "image": { "url": "data:image/png;base64,...", "type": "image_url" }
}
```

- `application/json` 사용 (NOT `multipart/form-data`)
- 마스크 불필요 — 자연어 편집
- 최대 3개 참조 이미지 (`images` 배열)
- 멀티 이미지: `{ "images": [...] }`

#### 사용 가능 모델

| 모델 ID | 상태 | 비고 |
|---------|------|------|
| `grok-imagine-image-quality` | ✅ 현재 권장 | Quality 모드 |
| `grok-imagine-image` | ✅ Active | 표준 |
| `grok-imagine-image-pro` | ⚠️ Deprecated (2026-05-15) | → `grok-imagine-image-quality`로 마이그레이션 |
| `grok-2-image` | ⚠️ Legacy | 이전 모델 |

#### 가격

| 작업 | 가격 |
|------|------|
| 이미지 생성 | $0.02/장 |
| 이미지 편집 | $0.02/장 |
| 비디오 생성 | $0.05/초 |

#### Rate Limits

누적 지출 기반 티어 시스템:
- Tier 0: $0 (기본)
- Tier 1: $50
- Tier 2: $250
- Tier 3: $1,000
- Tier 4: $5,000

429 응답 시 지수 백오프 필요.

### 2.4 ima2 기존 코드와의 호환성 분석

**현재 `grokImageAdapter.ts`의 API 호출:**

```ts
// lib/grokImageAdapter.ts:59-63 — 엔드포인트 구성
function getGrokEndpoint(ctx, path = "/v1/images/generations") {
  return {
    url: getGrokProxyUrl(ctx, path),  // progrok 프록시 URL
    headers: { "Content-Type": "application/json", Authorization: "Bearer dummy" },
  };
}
```

```ts
// lib/grokImageAdapter.ts:100-101 — 요청 페이로드
export function imagePayload(model, prompt, size) {
  return { model, prompt, n: 1, response_format: "b64_json", ...mapSizeToGrokImageParams(size) };
}
```

**핵심 발견: progrok과 직접 API 키의 엔드포인트/페이로드가 동일!**

- 같은 REST 경로: `/v1/images/generations`, `/v1/images/edits`
- 같은 요청 스키마: `{ model, prompt, n, response_format, aspect_ratio, resolution }`
- 같은 응답 스키마: `{ data: [{ b64_json, url, mime_type }], usage }`
- **차이점: URL (프록시 vs 직접) + Authorization 헤더 (dummy vs 실제 키)**

**∴ 직접 API 키 프로바이더 추가가 구조적으로 가능. 기존 `grokImageAdapter.ts`의 `postGrokImages()`, `imagePayload()`, `imageEditPayload()` 등을 그대로 재사용 가능. URL과 Authorization만 분기하면 됨.**

### 2.5 스모크 테스트

```bash
# 직접 API 키로 스모크 테스트
curl -s -X POST https://api.x.ai/v1/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $XAI_API_KEY" \
  -d '{
    "model": "grok-imagine-image-quality",
    "prompt": "A simple red circle on white background"
  }'
```

> **사용자 언급: "스모크는 X는 불가능"** — 이는 API 키가 없거나 무료 티어에서 이미지 생성이 불가능하다는 의미일 수 있음. 스모크 자체는 유료($0.02/장).

### 2.6 progrok과의 셀렉터 일치

**사용자 언급: "선택자에 포함되는 건 progrok이랑 완전히 일치"**

맞음. xAI 직접 API와 progrok 프록시의 계약이 동일:
- 동일한 모델 이름: `grok-imagine-image`, `grok-imagine-image-quality`
- 동일한 엔드포인트 경로: `/v1/images/generations`, `/v1/images/edits`
- 동일한 요청/응답 스키마
- **따라서 기존 `imagePayload()`, `imageEditPayload()`, 응답 파서, `grokSizeMapper` 모두 재사용 가능**

---

## 3. Gemini API 직접 호출 계약

### 3.1 현재: agy CLI 경유

```
사용자 → ima2 서버 → agy CLI (`agy -p -`) → Gemini API
                      (Antigravity CLI)
```

- `agy`를 `child_process.spawn()` 으로 실행
- stdin으로 프롬프트 전송, stdout에서 `RESULT|<path>|<ext>` 파싱
- 결과 이미지를 파일시스템에서 읽어 base64 변환
- 모델: `nano-banana-2` 하드코딩 (`providerOptions.ts:15`)
- 타임아웃: 360초
- 고정 해상도: `1024x1024`

### 3.2 목표: Gemini API 직접 호출

```
사용자 → ima2 서버 → Gemini API (generativelanguage.googleapis.com)
                      (API key 직접)
```

### 3.3 "nano-banana" 모델 코드명 해독

| 코드명 | API 모델 ID | 설명 |
|--------|-------------|------|
| **nano-banana-2** | `gemini-3.1-flash-image` | 고속, Flash 계열, 512px–4K |
| **nano-banana-pro** | `gemini-3-pro-image` | 프리미엄, 고품질, 느림 |
| **nano-banana (v1)** | `gemini-2.5-flash-image` | 이전 세대 |

> ⚠️ Preview 모델 (`*-preview`)은 2026-06-25 종료 예정.

### 3.4 Gemini API 계약 상세

#### 기본 정보

| 항목 | 값 |
|------|-----|
| Base URL | `https://generativelanguage.googleapis.com/v1beta/` |
| 인증 (쿼리) | `?key=YOUR_API_KEY` |
| 인증 (헤더) | `x-goog-api-key: YOUR_API_KEY` |
| 키 발급 | [Google AI Studio](https://aistudio.google.com/) |

#### 이미지 생성 — `generateContent` (Nano Banana 모델)

**엔드포인트:**
```
POST /v1beta/models/{MODEL_ID}:generateContent?key=YOUR_API_KEY
```

**요청:**
```json
{
  "contents": [{
    "parts": [{"text": "A cute cat wearing a top hat, digital art"}]
  }],
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"]
  }
}
```

> ⚠️ **필수**: `responseModalities`에 `"TEXT"`와 `"IMAGE"` 둘 다 포함해야 함. IMAGE만 넣으면 에러.

**응답:**
```json
{
  "candidates": [{
    "content": {
      "parts": [
        {"text": "Here is the generated image..."},
        {
          "inlineData": {
            "mimeType": "image/png",
            "data": "iVBORw0KGgo..."
          }
        }
      ]
    },
    "finishReason": "STOP"
  }],
  "usageMetadata": { ... }
}
```

- 이미지는 항상 **Base64 인라인 데이터**로 반환 (URL 없음)
- `mimeType`은 보통 `image/png`

#### 이미지 편집 (인페인팅/아웃페인팅)

```json
{
  "contents": [{
    "parts": [
      {
        "inlineData": {
          "mimeType": "image/png",
          "data": "BASE64_OF_SOURCE_IMAGE"
        }
      },
      {"text": "Add a rainbow in the sky"}
    ]
  }],
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"]
  }
}
```

- 소스 이미지를 `inlineData`로 포함
- 마스크 기반 편집도 가능 (마스크를 별도 `inlineData`로)
- 텍스트 프롬프트로 자연어 편집

#### 모델별 URL 매핑

| 사용자 이름 | API 모델 ID | URL 경로 |
|------------|-------------|----------|
| `nano-banana-2` | `gemini-3.1-flash-image` | `models/gemini-3.1-flash-image` |
| `nano-banana-pro` | `gemini-3-pro-image` | `models/gemini-3-pro-image` |

> 사용자 언급: **"기본모델이 필요없고 nano-banana-2 nano-banana-pro에 인자와 함께 요청을 보내면 되는 형식"** — 모델을 URL 경로에 명시하므로 기본 모델 폴백 불필요.

#### 가격/Rate Limits

- 프로젝트 단위 (API 키 단위가 아님)
- RPM, RPD, TPM, IPM 제한
- 무료 티어: 제한적, 유료 연결 시 확장
- 429 `RESOURCE_EXHAUSTED` = 쿼터 초과

### 3.5 ima2 기존 코드와의 호환성 분석

**현재 `agyImageAdapter.ts`의 방식:**

```ts
// 1. agy CLI 스폰
const child = spawn("agy", ["-p", "-"], { stdio: ["pipe", "pipe", "pipe"] });
// 2. stdin으로 거대한 프롬프트 전송 (시스템 프롬프트 + 사용자 프롬프트)
child.stdin.write(prompt);
// 3. stdout에서 RESULT|path|ext 파싱
const { artifactPath } = parseAgyOutput(stdout);
// 4. 파일시스템에서 이미지 읽기
const buffer = await readFile(artifactPath);
```

**직접 API로 전환 시 핵심 변경:**

| 항목 | agy CLI 현재 | Gemini API 직접 |
|------|-------------|----------------|
| 호출 | `spawn("agy", ...)` | `fetch("https://generativelanguage.googleapis.com/v1beta/...")` |
| 인증 | agy 내부 처리 | `?key=` 또는 `x-goog-api-key` 헤더 |
| 모델 지정 | `nano-banana-2` (하드코딩) | URL 경로: `models/gemini-3.1-flash-image` |
| 입력 | stdin으로 시스템 프롬프트 전송 | JSON body `{ contents, generationConfig }` |
| 출력 | 파일 → 읽기 → base64 | 응답 JSON에서 `inlineData.data` 직접 추출 |
| 레퍼런스 이미지 | 임시 파일 저장 → 경로 전달 | `inlineData`로 base64 직접 포함 |
| 타임아웃 | 360초 | 설정 가능 |
| 해상도 | 1024x1024 고정 | 모델에 따라 다름 |

**∴ 완전히 새로운 어댑터 필요. agy 어댑터 재사용 불가능하지만 반환 형식 (`{ b64, revisedPrompt, usage, webSearchCalls, mime }`)은 동일하게 맞추면 됨.**

### 3.6 스모크 테스트

```bash
# nano-banana-2 (gemini-3.1-flash-image) 스모크
curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent?key=${GEMINI_API_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{
    "contents": [{"parts": [{"text": "A simple red circle on white background"}]}],
    "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
  }' | jq '.candidates[0].content.parts[] | select(.inlineData) | .inlineData.mimeType'

# nano-banana-pro (gemini-3-pro-image) 스모크
curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image:generateContent?key=${GEMINI_API_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{
    "contents": [{"parts": [{"text": "A simple red circle on white background"}]}],
    "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
  }'
```

> 사용자 언급: **"스모크는 gemini api는 할 수 있고"** — Gemini API 키가 이미 있거나 무료 티어로 테스트 가능.

---

## 4. 결론: 추가 가능 여부

### 4.1 Grok API 직접 (xAI API key)

| 항목 | 판정 |
|------|------|
| API 계약 호환 | ✅ progrok과 100% 동일한 엔드포인트/스키마 |
| 기존 코드 재사용 | ✅ `imagePayload()`, `imageEditPayload()`, `grokSizeMapper`, 응답 파서 전부 |
| 필요한 변경 | URL 분기 (프록시 vs 직접) + Authorization 헤더 (`dummy` vs 실제 키) |
| 새 어댑터 필요? | ❌ 기존 `grokImageAdapter.ts` 확장으로 충분 |
| 스모크 테스트 | ❌ 유료 ($0.02/장), API 키 필요 |
| UI 셀렉터 | ✅ 이미 "Grok > API" 셀이 disabled 상태로 존재 |

**결론: 추가 가능, 작업량 소(Small). 기존 어댑터에 API 키 분기만 추가.**

### 4.2 Gemini API 직접 (Google API key)

| 항목 | 판정 |
|------|------|
| API 계약 호환 | ⚠️ 완전히 다른 API (generateContent vs agy CLI) |
| 기존 코드 재사용 | ❌ `agyImageAdapter.ts` 재사용 불가 (CLI vs REST) |
| 필요한 변경 | 새 어댑터 전체 + 모델 매핑 + 응답 파서 |
| 새 어댑터 필요? | ✅ `geminiApiImageAdapter.ts` 신규 작성 필요 |
| 모델 | `nano-banana-2` → `gemini-3.1-flash-image`, `nano-banana-pro` → `gemini-3-pro-image` |
| 스모크 테스트 | ✅ 가능 (무료 티어 또는 기존 API 키) |
| UI 셀렉터 | ✅ 이미 "Gemini > API" 셀이 disabled 상태로 존재 |

**결론: 추가 가능, 작업량 중(Medium). 새 REST 어댑터 작성 필요하지만 패턴은 명확.**

---

## 5. 구현 시 체크리스트 (향후 참조)

### 5.1 Grok API 키 프로바이더

- [ ] `config.ts`에 `xaiApiKey` 설정 추가 (env: `XAI_API_KEY`)
- [ ] `lib/grokImageAdapter.ts`의 `getGrokEndpoint()` 수정: API 키 모드일 때 `https://api.x.ai/v1` + 실제 Authorization
- [ ] `lib/providerOptions.ts`에 `provider === "grok-api"` 분기 (또는 기존 grok에 mode 추가)
- [ ] `routes/grok.ts` — API 키 상태 확인 엔드포인트
- [ ] UI: `ProviderSelect` 그리드에서 "Grok > API" 셀 활성화
- [ ] 테스트: 기존 grok 테스트가 API 키 모드에서도 패스하는지 확인

### 5.2 Gemini API 키 프로바이더

- [ ] `config.ts`에 `geminiApiKey` 설정 추가 (env: `GEMINI_API_KEY`)
- [ ] `lib/geminiApiImageAdapter.ts` 신규 작성
  - `generateContent` 엔드포인트 호출
  - `responseModalities: ["TEXT", "IMAGE"]` 필수
  - 응답에서 `inlineData.data` (base64) 추출
  - 레퍼런스 이미지: `inlineData`로 parts에 포함
  - 모델 매핑: `nano-banana-2` → `gemini-3.1-flash-image`, `nano-banana-pro` → `gemini-3-pro-image`
- [ ] `lib/imageModels.ts`에 `normalizeGeminiApiModel()` 추가
- [ ] `lib/providerOptions.ts`에 Gemini API 분기
- [ ] `routes/generate.ts` 외 4개 라우트에 `activeProvider === "gemini-api"` 분기
- [ ] UI: `ProviderSelect` "Gemini > API" 셀 활성화 + 모델 `nano-banana-pro` 추가
- [ ] 테스트: generateContent 응답 파싱 단위 테스트

---

## 6. 핵심 파일 레퍼런스

| 파일 | 역할 |
|------|------|
| `lib/providerOptions.ts` | 프로바이더 라우팅 허브 |
| `lib/imageModels.ts` | 모델 검증/정규화 |
| `lib/grokImageAdapter.ts` | Grok 이미지 어댑터 (520줄) |
| `lib/grokRuntime.ts` | Grok 프록시 URL 해석 |
| `lib/grokProxyLauncher.ts` | progrok 프로세스 관리 |
| `lib/grokSizeMapper.ts` | size → aspect_ratio/resolution 매핑 |
| `lib/agyImageAdapter.ts` | agy CLI 어댑터 (376줄) |
| `lib/capabilities.ts` | VALID_PROVIDERS 정의 |
| `lib/runtimeContext.ts` | 런타임 컨텍스트 인터페이스 |
| `config.ts` | 전체 설정 (grokProvider L280-295) |
| `routes/generate.ts` | 생성 라우트 (프로바이더 분기 L208-232) |
| `routes/edit.ts` | 편집 라우트 |
| `routes/multimode.ts` | 멀티모드 라우트 |
| `routes/nodes.ts` | 노드 라우트 |
| `routes/video.ts` | 비디오 라우트 |
| `ui/src/types.ts:15` | `Provider` 타입 |
| `ui/src/components/ProviderSelect.tsx` | 프로바이더 셀렉터 UI |
| `ui/src/components/ImageModelSelect.tsx` | 모델 셀렉터 UI |
| `ui/src/lib/imageModels.ts` | UI측 모델 옵션 |
