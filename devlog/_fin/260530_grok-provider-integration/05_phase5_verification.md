---
phase: 5
title: "검증"
---

# Phase 5: 검증 계획

## 5.1 정적 분석

```bash
# TypeScript 전체 검사
npx tsc --noEmit
npx tsc --noEmit -p tests/tsconfig.json

# 서버 빌드
npm run build:server

# CLI 빌드
npm run build:cli
```

---

## 5.2 기존 테스트 회귀

```bash
npm test
```

기존 785+ 테스트가 전부 통과해야 한다.
grok 코드는 기존 oauth/api 경로에 영향을 주지 않으므로 회귀가 없어야 정상.

---

## 5.3 grok 어댑터 단위 테스트

### 새 테스트 파일: `tests/grokImageAdapter.test.ts`

| 테스트 | 내용 |
|--------|------|
| `getGrokEndpoint()` | config에서 host/port 읽기, 기본값 확인 |
| `generateViaGrok()` — 성공 | mock fetch → b64_json 응답 → GrokGenerateResult 반환 |
| `generateViaGrok()` — 빈 응답 | mock fetch → `{ data: [] }` → GROK_EMPTY_RESPONSE 에러 |
| `generateViaGrok()` — HTTP 400 | mock fetch → 400 → 에러 전파 |
| `generateViaGrok()` — 타임아웃 | AbortController 타임아웃 → GENERATION_TIMEOUT |
| `generateViaGrok()` — 취소 | 외부 signal abort → GENERATION_CANCELED |
| `editViaGrok()` — 성공 | image 파라미터 포함 확인, b64 반환 |
| `editViaGrok()` — data URL vs raw base64 | 두 형태 모두 올바르게 data URL로 감싸는지 |
| `generateMultimodeViaGrok()` — 3장 | 순차 3회 호출, onFinalImage 3회 호출 |
| `generateMultimodeViaGrok()` — 중간 실패 | 2번째 실패 → 건너뛰고 3번째 시도 → 2장 반환 |
| `generateMultimodeViaGrok()` — 취소` | 2번째에서 취소 → 1장만 반환하지 않고 throw |

### 새 테스트 파일: `tests/providerOptions-grok.test.ts`

| 테스트 | 내용 |
|--------|------|
| `resolveProviderOptions({ provider: "grok" })` | provider "grok" 반환, reasoningEffort "none", webSearchEnabled false |
| `resolveProviderOptions({ provider: "grok", rawModel: "grok-imagine-image-quality" })` | 유효 모델 통과 |
| `resolveProviderOptions({ provider: "grok", rawModel: "gpt-5.4" })` | 잘못된 grok 모델 → 에러 |
| 기존 "oauth"/"api" 호출 | 변경 없음 확인 (회귀 테스트) |

---

## 5.4 E2E 실 호출 테스트 (progrok 필요)

progrok을 띄운 상태에서 수동 확인:

### generate
```bash
curl -X POST http://127.0.0.1:3333/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A red circle on white background",
    "provider": "grok",
    "quality": "low"
  }'
# 기대: { image: "data:image/jpeg;base64,...", provider: "grok", model: "grok-imagine-image" }
```

### generate (high quality)
```bash
curl -X POST http://127.0.0.1:3333/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cute cat in watercolor style",
    "provider": "grok",
    "quality": "high"
  }'
# 기대: model: "grok-imagine-image-quality"
```

### edit
```bash
# 1. 먼저 generate로 이미지 하나 생성
# 2. 그 base64를 image 필드에 넣어 edit 호출
curl -X POST http://127.0.0.1:3333/api/edit \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Change the circle to blue",
    "image": "data:image/jpeg;base64,...",
    "provider": "grok"
  }'
# 기대: 편집된 이미지 반환
```

### multimode
```bash
curl -X POST http://127.0.0.1:3333/api/generate/multimode \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "prompt": "Four seasons: spring, summer, autumn, winter",
    "provider": "grok",
    "maxImages": 4
  }'
# 기대: SSE events — phase → image × 4 → done
```

### grok status
```bash
curl http://127.0.0.1:3333/api/grok/status
# progrok ON:  { "status": "ready", "models": ["grok-imagine-image", ...] }
# progrok OFF: { "status": "offline" }
```

---

## 5.5 UI 브라우저 검증

1. `http://127.0.0.1:3333` 접속
2. ProviderSelect에 "Grok" 버튼 표시 확인
3. progrok OFF → 회색 dot + 비활성 → 클릭 시 모달 (offline 메시지)
4. progrok ON → 초록 dot + 선택 가능
5. Grok 선택 → 프롬프트 입력 → 생성 → 이미지 반환 확인
6. Grok 선택 → size/reasoning/web search 컨트롤 비활성화 확인
7. Grok → OAuth 전환 → 모델이 `gpt-5.4-mini`로 복원 확인
8. OAuth → Grok 전환 → 모델이 `grok-imagine-image`로 전환 확인
9. Multimode → Grok → 3장 생성 → SSE로 중간 이미지 확인

---

## 5.6 범위 외 (하지 않는 것)

- Agent Mode에 grok 추가하지 않음 (Responses API 의존)
- Node Mode에 grok 추가는 별도 이슈로 분리 가능
- `n>1` 단일 호출 최적화 (xAI의 n 지원 확인 후 별도)
- JPEG→PNG 변환 (불필요한 비용)
- CLI (`bin/commands/`)에 grok 전용 명령 추가하지 않음 (기존 `--provider grok` 으로 충분)
