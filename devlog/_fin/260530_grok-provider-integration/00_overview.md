---
created: 2026-05-30
tags: [feature, provider, xai, grok, image-generation]
---

# Grok (xAI) 프로바이더 통합

## 배경

progrok (`127.0.0.1:18645`)은 xAI Grok의 OAuth 프록시로, SuperGrok 구독만 있으면 API key 없이 xAI의 전체 `/v1/*` 엔드포인트를 사용할 수 있다.

xAI는 이미지 생성을 지원하지만 **OpenAI Responses API의 `image_generation` tool은 미구현**:
- `tools: [{ type: "image_generation" }]` → `unknown variant` 에러
- 지원 tools: `function`, `web_search`, `x_search`, `code_execution`, `code_interpreter`, `mcp`, `shell`

대신 **`/v1/images/generations` (Images API)**를 통해 이미지 생성이 가능하다:
- 모델: `grok-imagine-image`, `grok-imagine-image-quality`
- generate + edit (참조 이미지 입력) 둘 다 지원
- `b64_json` / `url` 응답 형식 모두 지원
- `size` 파라미터 미지원 (서버가 해상도 결정)
- 스트리밍 없음 — 단일 JSON 응답

## 실측 테스트 결과 (2026-05-30)

| 테스트 | 결과 | 비고 |
|--------|------|------|
| Responses API + `image_generation` tool | **실패** | xAI 미지원 |
| Images API — `grok-imagine-image` | **성공** | b64_json 127KB JPEG |
| Images API — `grok-imagine-image-quality` | **성공** | URL 응답 OK |
| Images API — 참조 이미지 (edit) | **성공** | `image` 파라미터로 base64 입력 |
| Images API — `size` 파라미터 | **실패** | `Argument not supported: size` |

## 설계 방침

1. **Responses API 어댑터를 건드리지 않는다** — 기존 `responsesImageAdapter.ts`는 OpenAI Responses API 전용으로 유지
2. **새 어댑터 `grokImageAdapter.ts`를 만든다** — `/v1/images/generations` 직행, 스트리밍 없음
3. **에이전트 모드는 건너뛴다** — Agent Mode는 Responses API의 tool/developer prompt 체계에 의존하므로 grok 불가
4. **`provider === "grok"`일 때 라우트에서 분기** — generate/edit/multimode 라우트가 grok이면 새 어댑터 호출

## API 차이 맵

| 기능 | OpenAI (oauth/api) | xAI (grok) |
|------|-------------------|------------|
| 엔드포인트 | `/v1/responses` | `/v1/images/generations` |
| 인증 | Bearer API key / OAuth proxy | progrok 프록시 (토큰 자동 주입) |
| 요청 형태 | `{ model, input, tools, tool_choice, reasoning, stream }` | `{ model, prompt, n, response_format }` |
| 이미지 모델 | `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini` | `grok-imagine-image`, `grok-imagine-image-quality` |
| size | 지원 (`1024x1024` 등) | **미지원** |
| quality | tool 옵션으로 전달 | 모델명으로 분리 (`-quality` 접미사) |
| developer prompt | 지원 | 해당 없음 |
| web_search | tool로 병합 가능 | 해당 없음 |
| reasoning | `{ effort }` 지원 | 해당 없음 |
| 스트리밍 | SSE (`text/event-stream`) | 없음 (단일 JSON) |
| partial_images | 지원 | 없음 |
| 참조 이미지 (edit) | `input_image` in user content | `image: { url: "data:..." }` |
| 마스크 (edit) | PNG alpha 지원 | 미확인 |
| 응답 형태 | SSE events → `image_generation_call.result` | `{ data: [{ b64_json, mime_type }] }` |

## Phase 구성

| Phase | 파일 | 내용 |
|-------|------|------|
| 01 | 타입 + 설정 | Provider 타입 확장, config.ts grok 섹션, imageModels grok 모델 |
| 02 | 어댑터 | `lib/grokImageAdapter.ts` — generate, edit, multimode |
| 03 | 라우트 분기 | routes/generate, edit, multimode에서 grok 분기 |
| 04 | UI | Provider 타입, ProviderSelect, availability, store |
| 05 | 검증 | tsc, 단위 테스트, 실 호출 E2E |
