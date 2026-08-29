# preview 배포 파이프라인 + size 패치 재적용 (stale base 대응)

- 작성일: 2026-06-27
- Goal ID: 005a3e7a-8f0
- 분류: C4 (release surface, npm publish 외부 게시, OIDC, CI/CD)

## 배경 / 전략
detached HEAD 5커밋(eb16209~b0a8b77, base `c1673e0`)이 origin/main(92커밋 앞)과 diverge — 특히 `responsesImageAdapter.ts` 370줄 리팩토링. 단순 머지 충돌. → **전략 A: origin/dev(=origin/main+2) 최신 위에 size 패치를 재적용 + 재검증.** 기존 5커밋은 버리고 내용만 옮긴다(검증된 patch 로직은 동일).

## work-phase 분해
- **wp1 (이번 PABCD)**: size 패치를 origin/dev 최신에 재적용 + typecheck/test/서버 E2E 재검증 + atomic 커밋.
- **wp2 (후속)**: preview 파이프라인 — preview 브랜치 + `publish-preview.yml`(OIDC `--tag preview`) + 버전 전략.
- **wp3 (후속)**: README/docs 제한 문구 + dev/main/preview push + npm 배포(외부, 실제 push 전 명시) + Actions 검증.

## wp1 — diff-level
### 작업 브랜치
- `git switch -c dev origin/dev` (detached HEAD 떠나 origin/dev 최신 기준).

### 재적용 (origin/dev 최신 코드 기준 — B에서 최신 구조 확인 후)
- `lib/oauthProxy/prompts.ts`: `sizeToCanvasDirective`/`qualityToDirective`/`buildSizeQualityDirective`/`sizeToOrientationPhrase` 신규 + `buildUserTextPrompt`/`buildEditTextPrompt`/`buildMultimodeSequencePrompt`에 in-request orientation phrase.
- `lib/oauthProxy/index.ts`: `buildSizeQualityDirective` barrel export.
- `lib/responsesImageAdapter.ts`: `generateViaResponses`/`editViaResponses`/`generateMultimodeViaResponses`에 size/quality 주입(`provider!=='api'` 가드) + developer directive. ⚠️ origin 최신 370줄 diverge라 함수 위치/시그니처 B에서 재확인.
- `lib/oauthProxy/generators.ts`: `generateViaOAuth`(+retry)/`editViaOAuth`/`generateMultimodeViaOAuth` builder size 전달 + developer directive + import.
- `tests/oauth-size-directive.test.ts`: 단위 19 케이스.
- `devlog/_plan/260627_oauth-size-quality-prompt-injection/*`: 기존 증거 문서 가져오기(또는 신규 경로).

### 검증
- `npm run typecheck` + 신규 테스트 + (build:server 후) 서버 `/api/generate` E2E 종횡비 재확인.

### 커밋
- atomic (feat: prompts/adapter/generators; test; docs 분리).

## 리스크
- **재적용 위치**: `responsesImageAdapter.ts`가 origin에서 370줄 바뀌어 `generateViaResponses` 등 구조가 다를 수 있음 → B에서 origin 최신 읽고 적용.
- **npm publish 외부**: wp3에서 OIDC trusted publishing(사용자 npm 계정 설정 의존). 실제 push/publish 전 명시.
- **버전 충돌**: origin/dev 버전(1.1.11) 기준 preview는 1.1.12-preview-<YYMMDD>.
