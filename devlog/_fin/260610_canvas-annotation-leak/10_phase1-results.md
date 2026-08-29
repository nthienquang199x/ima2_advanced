# Canvas annotation leak fix — 구현/검증 결과 (issue #96)

날짜: 2026-06-10
상태: D (done)
커밋: `0509f65`, `7fc8f23`

## 구현 요약

플랜(00_plan.md)대로 구현 + E2E에서 발견된 블로커 2건 추가 수정.

### 커밋 1 — `0509f65` fix: stop leaking canvas annotations into model payloads (#96)
- NEW `ui/src/lib/canvas/memoPrompt.ts` — `describeMemoPosition`, `buildMemoEditInstructions`
- `canvasModeHelpers.ts` — `resolveCleanSourceUrl`, `loadCleanSourceDataUrl`
- `useCanvasModeSession.ts` — `lastCleanDataUrlRef`, 메모 캡처(reset 전), clean editImage, 메모→프롬프트 합성, attach에 clean override
- `CanvasModeWorkspace.tsx` — ref 추가/리셋/전달
- `storeTypes/storeReferenceImpl/useAppStore` — `attachCanvasVersionReference(item, overrideSource?)`
- 계약 테스트 3파일 갱신/추가

### 커밋 2 — `7fc8f23` fix: normalize clean payload to PNG + sanitize edit size
E2E에서 발견한 블로커:
1. **INVALID_EDIT_IMAGE_BASE64**: 원본이 JPEG면 `data:image/jpeg` dataURL이 백엔드 PNG 전용 검증에 거부됨 → Image 로드 → canvas 재인코딩(PNG)으로 수정
2. **INVALID_REQUEST (upstreamParam=tools)**: grok 생성 이미지의 size 토큰(`grok:auto:1k`)이 GPT 편집에 상속돼 OpenAI가 거부 → `/^\d+x\d+$/` 아니면 `getResolvedSize()` 폴백

## E2E 검증 (성공 기준 충족)

- 환경: 로컬 서버(3463, 최신 빌드), cli-jaw browser CDP, 모델 gpt-5.5(GPT-IMAGE-2)
- 절차: 컵 3개 이미지에 메모 3개(좌: 파란 통→주황 / 중: 초록 컵에 흰 별 / 우: 컵 아래 빨간 받침) + 마스크 박스 → Edit boxed areas
- 전송 페이로드 확인(fetch 후킹): 프롬프트에 메모 3건이 좌표 %와 함께 텍스트로 합성됨, image/mask 모두 `data:image/png`
- 결과(`~/.ima2/generated/1781082984384_2d17a8d3.png`, 102.7s):
  - 노트/박스/펜 잔존 **0개**
  - 메모 지시 3건 모두 반영, **지정 위치 정확**

## 알려진 한계 / 후속 후보

1. apply → 일반 생성 경로: 참조가 클린본이 되면서 기존 `canvas-mode-context` 주입 프롬프트("이미지 속 마크를 지시로 해석")가 무의미해짐 — 메모 텍스트를 generate 경로 insertedPrompts로 주입하는 후속 작업 검토 필요
2. 마스크는 advisory: Responses API 특성상 마스크 밖(상단 라벨 텍스트)이 미세하게 변형될 수 있음 (E2E에서 라벨 문구 일부 재작성 관찰)
3. 백엔드 `resolveProviderOptions`가 provider 비호환 size 토큰을 사전 거부하지 않음 — 백엔드 하드닝 후보
