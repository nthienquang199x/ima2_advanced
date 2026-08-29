---
created: 2026-05-31
tags: [ima2-gen, pr-review, issue-triage, rebase]
---

# PR & Issue Review — 2026-05-31

오늘 하루 66 commits (v1.1.15 → v1.1.16 → v1.1.17 → v1.1.18).
Grok Video 전체 파이프라인 + Node-mode 통합 + Windows 호환 + CI 강화.

---

## Open PRs (2)

### PR #81 — Add Nix flake (philiptaron, 오늘 제출)

| 항목 | 내용 |
|------|------|
| 변경 | +351 / -1, 6 files (flake.nix, nix/*.nix, .gitignore, flake.lock) |
| 목적 | `nix run .#ima2-gen` 으로 CLI 실행, 846 tests sandboxed |
| 충돌 위험 | 낮음 — nix/ 디렉토리 신규, .gitignore 1줄 추가만 |
| 통합 판단 | **MERGE 가능** |
| 조건 | 1) flake.lock이 현재 main HEAD 기준인지 확인 (오늘 커밋 66개라 lockfile stale 가능) 2) `nix build` CI job 추가 여부는 후속 이슈로 분리 |
| 리베이스 | `gh pr comment 81 --body "Please rebase on latest main (66 commits landed today). After rebase, will merge."` |

### PR #3 — fix: surface upstream validation errors (aorying, 4/24 제출)

| 항목 | 내용 |
|------|------|
| 변경 | +206 / -13, 5 files (lib/oauthProxy.js, routes/generate.js, routes/nodes.js, tests x2) |
| 목적 | 업스트림 4xx 에러를 "safety refusal"로 삼키지 않고 실제 메시지 노출 |
| 충돌 위험 | **높음** — 대상 파일이 JS인데 현재 main은 TS 마이그레이션 완료 (#44, #50). `lib/oauthProxy.js`는 이미 `src/lib/oauthProxy/` 모듈로 분리됨 |
| 통합 판단 | **로직은 유효하나 코드 재작성 필요** |
| 계획 | 1) PR의 핵심 로직(에러 분기 + 테스트 케이스)을 현재 TS 구조에 cherry-pick/재구현 2) aorying에게 두 가지 옵션 제안: (a) 본인이 TS로 리베이스 (b) 메인테이너가 credit 유지하며 재구현 후 close |
| 리베이스 코멘트 | `gh pr comment 3 --body "Thanks for this fix! The codebase has since migrated to TypeScript (PR #44, #50) and oauthProxy.js was split into src/lib/oauthProxy/. The logic is still valuable. Would you like to rebase onto the new TS structure, or shall I re-implement with co-author credit?"` |

---

## Open Issues — 우선순위 & 상태

| # | Title | 우선순위 | 오늘 진행 영향 | 다음 액션 |
|---|-------|---------|--------------|----------|
| 80 | Batch Comparison Matrix | P3 | 없음 | 디자인 확정 후 착수. 외부 기여자 제안이라 spec 피드백 먼저. |
| 72 | Slash command dropup | P2 | 없음 | Agent Composer UI 작업 시 함께 처리. |
| 71 | Prompt Studio context injection | P1 | 없음 | 가장 큰 feature. 별도 sprint 필요. |
| 31 | Provider masked edit | P1 | 없음 | 업스트림 API 지원 대기 중. xAI/OpenAI 변경 시 즉시 착수. |
| 28 | Canvas PPTX export | P2 | 없음 | #27 완료 후 진행 (SVG overlay 재사용). |
| 27 | Canvas SVG export | P2 | 없음 | 독립 구현 가능. 다음 sprint 후보. |

---

## 리베이스 실행 계획

### 완료

1. **PR #81 (Nix flake)**: 코드 리뷰 완료 → APPROVE → rebase merge 완료 ✓
   - .gitignore 변경 안전, file: prefix 패치 합리적, 보안 이슈 없음, 유지보수 부담 낮음
2. **PR #3 (validation errors)**: @aorying 확인 — TS 마이그레이션에서 이미 구현됨 → close ✓

### 통합 우선순위 (main 안정성 기준)

```
#81 (Nix, 충돌 없음) → MERGED ✓ (rebase merge)
#3  (validation, 이미 TS에서 구현됨) → CLOSED ✓
```

---

## 오늘의 main 변경 요약 (PR 영향 분석용)

- **TS 구조**: `src/lib/oauthProxy/` 모듈 분리 완료 (PR #3 직접 충돌)
- **Video 파이프라인**: 신규 파일 다수 (`src/routes/video.ts`, `src/lib/grokVideo/`)
- **Node-mode**: `generateNodeVariation`, `runNodeBatch` 비디오 라우팅 추가
- **Windows**: `shell:true` spawn 패턴 통일
- **.gitignore**: devlog/ 제거 (PR #81 .gitignore 변경과 잠재 충돌)
