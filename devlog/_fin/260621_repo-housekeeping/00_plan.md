# Repo Housekeeping Plan — 2026-06-21

## 1. Git Branch Cleanup + dev 생성

**DELETE** (stale local branches):
- `ts-strict-followup` — 7주 전, #24 완료됨
- `docs/structure-refresh-2026-05-06` — 6주 전, 완료
- `pr-74` — 4주 전, PR 종료
- `feat/grok-video-i2v` — 3주 전, 완료 후 _fin에 있음

**KEEP**:
- `feat/websocket` — 13일 전, remote 있음, SSE→WS 마이그레이션 활성
- `test` — 10일 전, 테스트용

**CREATE**: `dev` from `main` → 이후 작업 브랜치

## 2. ChatPoongKun 크레딧 반영

- Contributor: **Sanguk Ko** (@ChatPoongKun)
- Email: `samko@samlab.co.kr`
- Co-authored-by: `Sanguk Ko <samko@samlab.co.kr>`
- 기존 devlog `260621_issue95-generation-request-log/00_overview.md`에 이메일 업데이트

## 3. Closed 이슈 Devlog 미작성 건 — 일괄 작성

devlog 체계 확립 전 초기 이슈(#5~#41)는 커밋 기록으로 충분, 생략.
devlog 체계 확립 후 미커버 건:

| Issue | Title | Devlog 방식 |
|-------|-------|------------|
| #42 | Gallery default session | stub (커밋으로 해결) |
| #43 | Generation settings audit | stub |
| #46 | Canvas white canvas | stub |
| #49 | Backend provider:api | stub |
| #54 | In-flight cancellation | stub |
| #55 | GPT-5.5 지원 | stub (서버사이드 모델 추가) |
| #56 | CLI --out timeout | stub |
| #73 | API ETag 304 | stub |
| #82 | VPS grok login | stub (260608_grok-url-continue 연계) |
| #83 | CI nix flake | stub |
| #89 | Source provenance | stub (260611_agent-source-policy-progress 연계) |
| #91 | Windows SIGKILL | stub |
| #92 | Cross-platform audit | stub |

→ 하나의 일괄 devlog 파일 `_fin/260621_uncovered-issues-closeout/README.md`에 통합 stub 작성.

## 4. Devlog-only → GitHub 이슈 생성

_plan 중 이슈 없는 유의미 건:

| Devlog | 이슈 생성 대상 |
|--------|--------------|
| `260602_storyboard-planner-skill` | feat: storyboard planner skill |
| `260602_switch_account` | feat: switch account flow |
| `260602_gallery-skeleton-shimmer-f5fix` | fix: gallery shimmer on F5 |
| `260603_gallery-focus-white-screen-rca` | fix: gallery focus white screen |
| `260610_model-dropdown-scroll` | fix: model dropdown scroll |
| `260611_agent-session-progress-rca` | fix: agent session progress |
| `260611_generation-limit-unlock` | feat: generation limit unlock |

_fin 중 이슈 없는 건은 완료 작업이므로 이슈 불필요.

## 5. Future Work 분리 → `_plan/_future/`

`devlog/_plan/_future/`로 이동할 항목:

| Directory | Reason |
|-----------|--------|
| `260430_issue27-canvas-svg-export` | canvas feature, 장기 |
| `260430_issue28-canvas-pptx-export` | pptx, 장기 |
| `260430_issue31-provider-masked-edit` | canvas feature, 장기 |
| `260514_canvas-background-removal-library-research` | research, 장기 |
| `260514_canvas-library-research` | research, 장기 |
| `260602_storyboard-planner-skill` | feature, 장기 |
| `260611_swimwear-moderation-intent` | research, 보류 |

## 6. Open 이슈 현황 정리

현재 open 10개 → devlog _plan에 매핑 확인 후 누락 건 stub 생성.
