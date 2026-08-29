# wp2 — preview 배포 파이프라인

- 작성일: 2026-06-27
- 분류: C4 (release surface, OIDC npm publish, CI/CD)
- 전제: wp1에서 size 기능은 origin/dev `sizeDirective`로 이미 작동 확인 → 코드 패치 불필요. 이번은 **배포 파이프라인만**.

## Part 1 — 목표
preview dist-tag npm 배포 파이프라인 구축. latest(정식)는 기존 `publish.yml`(`on: release: published`) 유지, preview는 신규 워크플로로.

## Part 2 — 산출물 (diff-level)

### NEW: `.github/workflows/publish-preview.yml`
- `on: push: branches: [preview]` + `workflow_dispatch`
- `permissions: { contents: read, id-token: write }` (OIDC)
- 기존 `publish.yml` 스텝 재활용: checkout → setup-node(registry npmjs) → `npm install -g npm@latest`(OIDC) → `npm ci` → ui install → typecheck/typecheck:tests/test:inventory → build:server/build:cli/ui build → `npm test` → lint:pkg → test:package-install → **OIDC precondition check**(npm>=11.5.1 + ACTIONS_ID_TOKEN_REQUEST_URL)
- **버전 설정 스텝**: base `2.0.3` → `2.0.4-preview-<YYMMDD>` (patch+1 + `-preview-` + date), `npm version <v> --no-git-tag-version`
- `npm publish --tag preview --provenance --access public` (latest 아님 = preview dist-tag)

### preview 브랜치 (wp3에서)
- `main` 기반 생성, push 시 publish-preview.yml 트리거

### docs 제한 문구 (재량)
- `README.md` `## Provider Paths` 뒤 + `docs/API.md`: OAuth 경로 이미지 해상도 — 종횡비는 정확하나 총 픽셀 ~1.57M(≈1024×1536) 캡, 1K 프리셋 정확/그 이상 종횡비 유지하며 축소. **일시적 제한, 향후 방향 미정.** 정확한 큰 픽셀은 API key `/images/generations`.

## Part 3 — 버전 전략
| dist-tag | 트리거 | 버전 | 워크플로 |
|---|---|---|---|
| latest | GitHub Release published | `2.0.x` (npm version) | publish.yml (기존) |
| preview | push preview 브랜치 | `2.0.(x+1)-preview-<YYMMDD>` | publish-preview.yml (신규) |

## Part 4 — 리스크 / 외부 게시
- **npm publish는 외부 게시(돌이킬 수 없음)** — wp3 push 전 명시.
- **OIDC trusted publishing**: npm 레지스트리에 GitHub repo trusted publisher 등록이 선행돼야 작동(Jun님 npm 계정). 미설정 시 Actions 실패(코드 무해).
- preview prerelease 버전은 npm `latest`를 덮지 않음(`--tag preview`).
