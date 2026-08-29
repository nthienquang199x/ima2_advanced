# ima2-gen 안정화 + 500줄 분할 계획 (v2 — 감사 반영)

## 요약

리소스 누수 검증(이미 완료) → 13개 소스 파일 500줄 이하 분할.

## Phase 0 — 리소스 누수 검증 (이미 완료)

commit `369bb5b`에서 3건(E/F/G) 수정 완료. 회귀 테스트 8개 존재.
추가 누수 패턴 미발견. `npm test` + `tsc --noEmit` 통과 확인만 수행.

---

## Phase 1 — CSS 분할

### 1-1. ui/src/index.css (7,054줄 → 18파일 + barrel)

현재 순서(cascade) 보존. `@import` 순서 = 현재 소스 순서와 동일하게 유지.

| # | 새 파일 | 소스 행 범위 | 예상 줄수 |
|---|---------|-------------|----------|
| - | `index.css` (barrel) | 1-86 + @imports | ~100 |
| 1 | `styles/themes.css` | 87-553 | ~467 |
| 2 | `styles/sidebar.css` | 554-993 | ~440 |
| 3 | `styles/form-controls.css` | 994-1316 | ~323 |
| 4 | `styles/canvas-viewer.css` | 1317-1661 | ~345 |
| 5 | `styles/canvas-accordion.css` | 1662-2044 | ~383 |
| 6 | `styles/right-panel.css` | 2045-2499 | ~455 |
| 7 | `styles/progress-composer.css` | 2500-2999 | ~500 |
| 8 | `styles/gallery-modal.css` | 3000-3435 | ~436 |
| 9 | `styles/toast-modal.css` | 3436-3927 | ~492 |
| 10 | `styles/responsive-layout.css` | 3928-4200 | ~273 |
| 11 | `styles/responsive-mobile.css` | 4201-4441 | ~241 |
| 12 | `styles/node-workspace.css` | 4442-4925 | ~484 |
| 13 | `styles/node-polish.css` | 4926-5226 | ~301 |
| 14 | `styles/card-news-layout.css` | 5227-~5550 | ~324 |
| 15 | `styles/card-news-templates.css` | ~5551-5862 | ~312 |
| 16 | `styles/prompt-library-core.css` | 5863-~6300 | ~438 |
| 17 | `styles/prompt-library-detail.css` | ~6301-6652 | ~352 |
| 18 | `styles/prompt-library-extras.css` | 6653-7054 | ~402 |

합계: ~6,712 + barrel 100 ≈ 6,812 (원본 분할 시 빈 줄/주석 정리로 축소 예상).

**barrel `index.css`:**
```css
@import "tailwindcss";
/* reset (lines 3-86) 유지 */
@import "./styles/themes.css";
@import "./styles/sidebar.css";
/* ... 현재 소스 순서 그대로 18개 @import ... */
@import "./styles/prompt-library-extras.css";
```

### 1-2. ui/src/styles/canvas-mode.css (573줄 → 2파일)

| 새 파일 | 소스 행 범위 | 예상 줄수 |
|---------|-------------|----------|
| `styles/canvas-toolbar.css` | 1-~285 | ~285 |
| `styles/canvas-mode.css` | ~286-573 | ~288 |

### 1-3. ui/src/styles/agent-workspace-panels.css (506줄 → 2파일)

⚠️ 기존 `agent-workspace-sidebar.css`(main.tsx에서 import)와 이름 충돌 방지.

| 새 파일 | 소스 행 범위 | 예상 줄수 |
|---------|-------------|----------|
| `styles/agent-panels-composer.css` | 1-~276 | ~276 |
| `styles/agent-workspace-panels.css` | ~277-506 | ~230 |

---

## Phase 2 — Store & API 분할

### 2-1. ui/src/store/useAppStore.ts (4,681줄 → 11파일)

**Pre-store 헬퍼 (lines 1-1393):**

| 새 파일 | 소스 행 범위 | 내용 | 예상 줄수 |
|---------|-------------|------|----------|
| `store/storeTypes.ts` | 947-1218 + exported types (148, 734-767, 869-898) | AppState 인터페이스 + 공개 타입 (ComposeSheetTab, MultimodeSequenceState, ToastEntry 등) | ~420 |
| `store/storageUtils.ts` | 150-329 | load*/save* + theme resolution | ~350 |
| `store/historyHelpers.ts` | 330-355, 356-732, 900-946 | inflight 타입/스코프, compose, normalize, history map/merge, multimode sequence helpers | ~450 |
| `store/graphHelpers.ts` | 769-868 (graph utility functions), 1220-1393 | graph node helpers + format/metadata + defaults | ~300 |

⚠️ Lines 1-147 (imports): 각 분할 파일에서 자기 필요한 import만 가져감. 원본 import 블록 그대로 복사 불가.

**Store 슬라이스 (lines 1394-4339 = 2,946줄, Zustand StateCreator 패턴, 6 slices):**

| 새 파일 | 내용 | 예상 줄수 |
|---------|------|----------|
| `store/slices/historySlice.ts` | History, gallery, favorites, trash | ~490 |
| `store/slices/generationSlice.ts` | Image generation, edit, multimode | ~490 |
| `store/slices/videoSlice.ts` | Video generation, multimode sequences | ~490 |
| `store/slices/sessionSlice.ts` | Session 관리, graph node CRUD | ~490 |
| `store/slices/uiSlice.ts` | Theme, locale, settings, canvas mode | ~490 |
| `store/slices/referencesSlice.ts` | Reference image 관리, metadata restore | ~490 |

⚠️ 실제 경계는 Build 시 함수 단위로 결정. 각 슬라이스 ≤500줄 엄수.

**Module-level 코드 (lines 4341-4681):**

| 새 파일 | 소스 행 범위 | 내용 | 예상 줄수 |
|---------|-------------|------|----------|
| `store/graphAutosave.ts` | 4341-4634 | debounced graph save + beforeunload + beacon | ~294 |

⚠️ Lines 4636-4674 (`addHistory`) → `historyHelpers.ts`로 이동.
⚠️ Lines 4676-4681 (`selectCurrentSessionId`) → barrel `useAppStore.ts`에 유지.

**Barrel:**

| 파일 | 내용 | 예상 줄수 |
|------|------|----------|
| `store/useAppStore.ts` | `create((...a) => ({ ...slice1(...a), ...slice2(...a), ... }))` + re-export + selectCurrentSessionId | ~180 |

**전략**: 각 슬라이스 = `(set, get, store) => ({...})`. `useAppStore.ts`에서 spread 합성.
기존 `import { useAppStore } from '@/store/useAppStore'` — 56개 consumer 전부 무변경.
슬라이스 간 `get()` 호출은 전체 store 참조이므로 순환 import 없음.

### 2-2. ui/src/lib/api.ts (1,161줄 → 6파일 + barrel)

| 새 파일 | 내용 | 예상 줄수 |
|---------|------|----------|
| `lib/api-core.ts` | jsonFetch, parseSseBlock, 공통 타입 | ~120 |
| `lib/api-generation.ts` | 이미지/비디오/multimode 생성 스트림 | ~300 |
| `lib/api-history.ts` | History CRUD, gallery favorites, trash | ~200 |
| `lib/api-sessions.ts` | Session 관리 | ~100 |
| `lib/api-library.ts` | Prompt library, import, curation | ~350 |
| `lib/api-canvas.ts` | Canvas annotations, versions | ~80 |
| `lib/api.ts` | Barrel: `export * from './api-core'; ...` | ~30 |

기존 barrel 패턴 (`nodeApi` re-export) 확장. 19곳 import 무변경.

---

## Phase 3 — Backend 분할 (5파일)

### 3-1. lib/agentRuntime.ts (611줄 → 4파일)

| 새 파일 | 내용 | 예상 줄수 |
|---------|------|----------|
| `lib/agentImageGen.ts` | generateAgentImage + persist | ~200 |
| `lib/agentVideoGen.ts` | runAgentVideoGeneration + persist | ~150 |
| `lib/agentPlanExecutor.ts` | runAgentGenerationPlan + retry/recovery | ~150 |
| `lib/agentRuntime.ts` | runAgentTurn entry + utilities | ~150 |

### 3-2. lib/grokImageAdapter.ts (573줄 → 2파일)

| 새 파일 | 내용 | 예상 줄수 |
|---------|------|----------|
| `lib/grokImageGenerate.ts` | generateViaGrok + image gen logic | ~290 |
| `lib/grokImageAdapter.ts` | adapter interface + planner/search helpers | ~290 |

### 3-3. routes/nodes.ts (600줄 → 3파일)

| 새 파일 | 내용 | 예상 줄수 |
|---------|------|----------|
| `lib/nodeGeneration.ts` | Provider routing, retry loop (~309-550) | ~250 |
| `lib/nodeValidation.ts` | Request validation, moderation (~106-242) | ~150 |
| `routes/nodes.ts` | Route handlers only | ~200 |

### 3-4. routes/generate.ts (555줄 → 2파일)

| 새 파일 | 내용 | 예상 줄수 |
|---------|------|----------|
| `lib/generatePipeline.ts` | Generation pipeline logic | ~280 |
| `routes/generate.ts` | Route handler | ~280 |

### 3-5. routes/multimode.ts (531줄 → 2파일)

| 새 파일 | 내용 | 예상 줄수 |
|---------|------|----------|
| `lib/multimodePipeline.ts` | Multimode stream logic | ~270 |
| `routes/multimode.ts` | Route handler | ~270 |

---

## Phase 4 — Frontend Components & Hooks (2파일)

### 4-1. ui/src/hooks/useCanvasAnnotations.ts (549줄 → 2파일)

| 새 파일 | 내용 | 예상 줄수 |
|---------|------|----------|
| `hooks/canvasAnnotationHelpers.ts` | 순수 로직 + 타입 (1-451) | ~450 |
| `hooks/useCanvasAnnotations.ts` | React hook (452-549) | ~100 |

⚠️ helpers가 451줄이면 450 근접. 구현 시 정확한 경계 조정.

### 4-2. ui/src/components/GalleryModal.tsx (515줄 → 2파일)

| 새 파일 | 내용 | 예상 줄수 |
|---------|------|----------|
| `components/gallery/GalleryActions.tsx` | 액션 버튼, 메타데이터, 핸들러 | ~260 |
| `components/GalleryModal.tsx` | 모달 쉘 + 이미지/비디오 뷰어 | ~260 |

---

## Phase 5 — Tests (1파일)

### 5-1. tests/card-news-contract.test.ts (511줄 → 2파일)

| 새 파일 | 내용 | 예상 줄수 |
|---------|------|----------|
| `tests/card-news-contract.test.ts` | Core contract tests | ~260 |
| `tests/card-news-template.test.ts` | Template-specific tests | ~260 |

---

## 범위 외 (변경 없음)

- `package-lock.json` 3종 — 자동 생성
- `ui/src/i18n/en.json`, `ko.json` (1,317줄) — JSON 데이터, i18n 아키텍처 변경 필요, 별도 이슈
- 컴파일 `.js` 산출물 — `.ts` 분할 후 `tsc` 재빌드
- `127.0.0.1 vs localhost` — 현 정책 유지

## 실행 순서

크기 내림차순 (사용자 요청):
1. index.css (7,054)
2. useAppStore.ts (4,681)
3. api.ts (1,161)
4. agentRuntime.ts (611)
5. nodes.ts (600)
6. canvas-mode.css (573)
7. grokImageAdapter.ts (573)
8. generate.ts (555)
9. useCanvasAnnotations.ts (549)
10. multimode.ts (531)
11. GalleryModal.tsx (515)
12. card-news-contract.test.ts (511)
13. agent-workspace-panels.css (506)

## 검증 (각 파일 분할 후)

1. `npx tsc --noEmit` — 서버 TypeScript
2. `cd ui && npx tsc -b --noEmit` — UI TypeScript
3. `npm test` — 전체 테스트
4. `cd ui && npm run build` — Vite 빌드
5. 분할된 모든 파일 `wc -l` ≤ 500 확인

## Phase 3 Closeout (2026-07-11, 260711_production-hardening WP6)

백엔드 4파일 분할 완료 (worker Copernicus): routes/multimode.ts 9줄, routes/generate.ts 9줄,
routes/nodes.ts 27줄, lib/oauthProxy/generators.ts 219줄. 신규 모듈: lib/generatePipeline.ts(499),
lib/multimodePipeline.ts(492), lib/nodeGeneration.ts(471), lib/nodeValidation.ts(29),
lib/oauthProxy/multimodeGenerators.ts(303) — 전부 500줄 이하. 이동 관련 소스 계약 테스트 20건 갱신,
전체 스위트 1116개 중 1114 pass 0 fail, typecheck/typecheck:tests 통과.
