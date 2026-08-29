# 02 — 구현 계획서: Grok API + Gemini API + API Key Web UI

> 날짜: 2026-06-02
> 상태: 구현 진행중
> 선행: `00_grok-gemini-api-provider-research.md`, `01_api-key-web-ui-gtm-strategy.md`

---

## 최종 확인 사항 (인터뷰 결과)

| 항목 | 결정 |
|------|------|
| nano-banana-pro | ✅ 추가 (gemini-api 전용) |
| nano-banana-2 | ✅ agy + gemini-api 양쪽 |
| Gemini 파이프라인 | 플래너 없음, 직통 |
| Grok API | 기존 grok과 동일 동작, OAuth↔API 토글 |
| Grok 비디오 | grok-api에서도 동일 지원 |
| Provider 값 | `"grok-api"`, `"gemini-api"` 신규 추가 |
| UI 토글 | 기존 그리드 셀 활성화 |
| API 키 입력 | Settings > Account에 마스킹 입력 필드 |
| 완료 기준 | CDP 스크린샷 + 실제 동작 검증 |

---

## Phase 1: 서버 — config + RuntimeContext 확장

### 1.1 `config.ts`
- `xaiApiKey` env: `XAI_API_KEY`, configJson: `xaiApiKey`
- `geminiApiKey` env: `GEMINI_API_KEY`, configJson: `geminiApiKey`

### 1.2 `server.ts`
- `loadApiKey()` → 확장해서 xAI/Gemini도 로드
- env → config.json → null 우선순위

### 1.3 `lib/runtimeContext.ts`
- `xaiApiKey`, `xaiApiKeySource`, `hasXaiApiKey` 추가
- `geminiApiKey`, `geminiApiKeySource`, `hasGeminiApiKey` 추가
- `updateApiKey(provider, key, source)` 메서드

---

## Phase 2: 서버 — API 키 CRUD 라우트

### 2.1 `routes/keys.ts` (신규)
- `PUT /api/keys/:provider` — 키 저장 + 검증
- `GET /api/keys/status` — 마스킹 상태 반환
- `DELETE /api/keys/:provider` — 키 삭제

### 2.2 `routes/index.ts` 등록

---

## Phase 3: 서버 — 모델 & 프로바이더 타입 확장

### 3.1 `lib/imageModels.ts`
- `VALID_GEMINI_API_MODELS` 추가
- `normalizeGeminiApiModel()` 추가

### 3.2 `lib/providerOptions.ts` — grok-api, gemini-api 분기

### 3.3 `lib/capabilities.ts` — VALID_PROVIDERS 확장

---

## Phase 4: 서버 — Gemini API 어댑터 (신규)

### 4.1 `lib/geminiApiImageAdapter.ts` (신규)
- model → API ID 매핑 (nano-banana-2 → gemini-3.1-flash-image)
- generateContent 호출, inlineData.data 추출

---

## Phase 5: 서버 — Grok API 키 모드

### 5.1 grokRuntime / grokImageAdapter / grokVideoAdapter 수정
- grok-api → https://api.x.ai 직접 + 실제 키

---

## Phase 6: 서버 — 라우트 핸들러 분기 (generate/edit/multimode/nodes/video)

---

## Phase 7: UI — 타입 & 모델 확장 (types.ts, imageModels.ts, i18n)

---

## Phase 8: UI — API 키 입력 + 프로바이더 셀렉터

---

## Phase 9: 빌드 + CDP 검증
