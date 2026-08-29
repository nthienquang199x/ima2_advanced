# ChatPoongKun Fork Review

- Fork: https://github.com/ChatPoongKun/ima2-gen
- Branch: `codex/classic-workflow-improvements`
- Upstream 대비: 16 commits ahead, 98 behind
- Issues: #95 (로그 기능 추가요청), #34 (UX개선 건의)
- 검토일: 2026-06-21

## Summary

| # | Feature | Verdict | Conflict | Action |
|---|---------|---------|----------|--------|
| 1 | Generation Request Log | **ADAPT** | Low+Med | 신규 파일 cherry-pick, generate.ts 통합은 수작업 |
| 2 | Classic Batch Streaming | **SKIP** | Critical | upstream asyncMode가 이미 동일 기능 제공 |
| 3 | Prompt UX (diff viewer, resize) | **ADAPT** | Medium | ResultPromptSummary + clipboard.ts 깨끗, PromptComposer는 충돌 |
| 4 | Synology Docker | **PICK** | None | 전부 신규 파일, 즉시 적용 가능 |
| 5 | Gallery Shortcut Dedup | **PICK** | Low | upstream 파일 동일, caller 업데이트 포함 |
| 6 | Network Settings UI | **ADAPT** | Low | 신규 파일, config/api.ts 연결 필요 |
| 7 | Thumbnail Sidecar 제거 | **ADAPT** | Low+Med | thumbBackfill.ts 깨끗, generate.ts는 수작업 |

## Key Blocker

upstream `routes/generate.ts`가 대폭 변경됨 (asyncMode, fail()/succeed(), providerUrl, createdAt, eventBus/ssePublish).
Fork의 generate.ts 패치는 전부 pre-divergence 기준이라 Feature 1, 2, 7 모두 이 파일에서 충돌.
Feature 2는 upstream asyncMode와 기능 중복이므로 SKIP.
