# 드롭인 / 인증 플로우 개선 — 조사 및 계획

- 작성일: 2026-06-03
- Goal: f5a417c6-cdb
- 단계: PABCD / P (조사 = 코드 정독 + 서브에이전트 조사 + 웹 검색)

## 1. 요구사항 (사용자 확정)

1. CLI 첫 설정(`ima2 setup`)에서 "API Key" 선택지 제거 → "웹에서 설정"으로 교체, 웹 드롭인 강화
2. `@openai/codex@latest`를 npm 의존성으로 번들 → codex 미설치 환경에서도 동작 (agy는 미번들)
3. 무인증(GPT·Grok·Gemini 전부) 시 onboarding 팝업 (영/한)
4. Settings에 agy(Gemini) 상태 줄 추가
5. 인증 대기 화면 "Open tab again" → "Retry"

## 2. 현재 동작 (조사 결과)

### 2.1 CLI setup — `bin/ima2.ts:62-164`
- 선택지 1-4 (67-70), `choice === "4"` → OpenAI API key 입력·저장 (75-85)
- GPT OAuth 경로: `detectCodexAuth()` + `execSync(resolveBin("npx") @openai/codex login)` (112, 147)

### 2.2 codex 의존성
- **런타임(이미지 생성)**: 번들 `openai-oauth` proxy (`lib/oauthLauncher.ts:28`, `npx openai-oauth`). auth 파일 없으면 GPT OAuth 스킵하고 `"Grok-only mode is fine"` (20, 69) → **codex CLI 무관**
- **로그인(토큰 발급)**: CLI `npx @openai/codex login`; 웹 Switch Account `spawn("codex", ["login", "--device-auth"])` (`routes/auth.ts:142`, 미설치 시 `codex not found` 208) → **codex CLI 의존**
- `package.json` dependencies(67-78)에 `@openai/codex` **없음**

### 2.3 인증 대기 UI — `ui/src/components/settings/QuotaCard.tsx`
- `SwitchAccountButton` (77-215), provider "grok"|"codex" 공용
- waiting 상태(151-189): userCode + **"Open tab again"**(162-169, `window.open`) + **"Copy link"**(170-182)
- error 상태(200-214)에 "Try again"(205-212), `startSwitch`(82-104) = POST `/api/auth/switch`

### 2.4 Settings — `ui/src/components/AccountSettings.tsx`
- OAuth row(41-51) / API Key row(53-69, 조건부) / Grok row(71-81). **agy 상태 줄 없음**
- `statusLabel`(10-18), 훅 `useOAuthStatus`/`useGrokStatus`/`useKeyStatus`

### 2.5 onboarding
- **없음**. `ProviderReadinessPopup`(provider 준비 점검, 수동 `readinessPopupOpen`)만 존재 — modal/`role="dialog"`/`openSettings("account")` 패턴 재사용 가능
- App 루트 `ui/src/App.tsx`(45-178) 모달 목록(162-169)에 마운트

### 2.6 agy
- `lib/agyImageAdapter.ts:103` `spawn("agy", ["-p", "-"])`. 설치 감지 유틸 없음(`resolveBin`은 이름만 반환). 로그인 상태 확인 수단 없음
- `/api/agy/status` 없음. 라우트 등록은 `routes/index.ts:29-56`, 패턴은 `routes/grok.ts:5-24`(`GET /api/grok/status`)

## 3. 변경 계획 (diff-level)

### 작업1 — CLI setup "API Key" 제거 (`bin/ima2.ts` + `bin/ima2.js`)
- 67-70 선택지: `4) API Key — paste your OpenAI API key (paid)` → `4) Configure in the web UI — set everything from the browser` (한/영 톤 맞춤)
- 75-85 `choice === "4"` 분기: API key 입력/검증 제거 → `config.provider = "oauth"` 기본 + 안내 "웹에서 모든 걸 설정할 수 있습니다 (ima2 serve 후 Settings)" 출력 후 종료
- 빌드 산출물 `bin/ima2.js` 동기화

### 작업2 — codex npm 번들 (`package.json`, `routes/auth.ts`)
- `package.json` dependencies(67-78)에 `"@openai/codex": "latest"` 추가
- `routes/auth.ts:142` `spawn("codex", ["login","--device-auth"])` → 번들 bin 직접 호출. routes/auth.ts엔 현재 platform import 없으므로 `node:path`의 `join`으로 `node_modules/.bin/codex`(win: `codex.cmd`) 절대경로를 만들어 `spawn(codexBin, ...)`. 번들 보장이라 PATH 무관하게 항상 존재. (audit 반영: PATH의 `codex`가 아니라 번들 bin)
- `bin/ima2.ts:112,147` `${resolveBin("npx")} @openai/codex login`: `npx`는 로컬 `node_modules/@openai/codex`를 우선 resolve하므로 번들 후 자동 동작 — 변경 최소. (안전 통일 위해 `node_modules/.bin/codex login` 직접 호출로 바꾸는 것도 검토)

### 작업3 — onboarding 팝업 (NEW `ui/src/components/OnboardingPopup.tsx`)
- 무인증 감지: `oauth.status ∈ {auth_required, offline}` AND `grok.status ∈ {offline, error}` AND `keyStatus.gemini.configured === false` (로딩 중 null이면 판정 보류)
- 내용(i18n): "안녕하세요, 처음이신가요? 여기서 로그인하세요" + [네]→`openSettings("account")` / [알아서 진행하겠습니다]→`localStorage['ima2.onboardingDismissed']='1'` + close
- 재노출 차단: localStorage 플래그 set이면 안 띄움
- `App.tsx` 모달 목록(162-169)에 `<OnboardingPopup />` 추가
- i18n `onboarding.*` 키 (en.json / ko.json)

### 작업4 — agy status 줄 (NEW `routes/agy.ts`, `AccountSettings.tsx`)
- NEW `routes/agy.ts`: `GET /api/agy/status` → agy 설치 감지. (audit 반영) 기존 코드 패턴(`lib/agyImageAdapter.ts:103` `spawn("agy")`)과 일관되게 **spawn-and-catch** 사용: `spawn("agy", ["--version"])` 시도 → `error`(ENOENT)면 `installed:false`, 정상 exit면 `installed:true`. shell `which`/`where` 미사용(크로스플랫폼·새 의존 회피) → `{ installed: boolean }`
- `routes/index.ts`에 `registerAgyRoutes(app, ctx)` 등록
- NEW 훅 `ui/src/hooks/useAgyStatus.ts` (useGrokStatus 패턴)
- `AccountSettings.tsx` Grok row(81) 뒤 agy row 추가:
  - 미설치: "antigravity CLI" 하이퍼링크 → `https://antigravity.google/docs/cli-install`
  - 설치됨: "로그인 상태는 확인할 수 없습니다" + `agy login` 안내 + 작은 글씨 "antigravity 모델과 이미지 할당량은 별도입니다"
- i18n `settings.account.agy.*` 키 (en/ko)

### 작업5 — Retry (`QuotaCard.tsx`)
- 162-169 "Open tab again"(`window.open`) → **"Retry"**: `onClick`을 `startSwitch`(device code 재발급 + 탭 새로)로 교체
- "Copy link"(170-182) 유지. Codex/Grok 공용이라 자동 적용
- 버튼 라벨 i18n 처리(현재 하드코딩)

## 4. 외부 참조 — Antigravity CLI
- 설치 안내: https://antigravity.google/docs/cli-install , https://antigravity.google/docs/cli-getting-started
- 바이너리 `agy` → `~/.local/bin/agy` (Go, 2026-05-13 공개). install: `https://antigravity.google/cli/install.sh`

## 5. 성공 기준
1. codex 미설치 환경에서 `npm i -g ima2-gen` 후 `codex login`·Switch Account 동작
2. `ima2 setup`에서 API Key 제거 + "웹에서 설정" 표시
3. 무인증 onboarding 팝업 영/한 + [네]→Settings / [알아서]→재노출 안 함
4. agy status 줄: 설치 감지 / 미설치 링크 / 설치 시 안내 문구
5. Retry(코드 재발급+탭) + Copy link 유지 (Codex+Grok)
6. `npm test` · `npx tsc --noEmit` · `astro build` 통과

## 6. 리스크 / 미결
- `@openai/codex@latest` 패키지 크기·설치 시간 증가 (사용자 승인됨)
- `spawn("codex")` resolve: 전역(-g) vs 로컬 설치 시 `node_modules/.bin` 경로 차이 — resolve 헬퍼로 흡수
- 무인증 false positive(상태 로딩 중 null) 방지: 세 훅 모두 로드 완료 후 판정
- `which agy` 크로스플랫폼(Windows `where`) 처리
