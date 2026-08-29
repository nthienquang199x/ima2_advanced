---
created: 2026-05-17
status: plan
tags: [ima2-gen, agent-mode, ui-polish, jawdev, layout, settings, tool-folding]
depends_on:
  - ../260516_agent-mode-followup-jawdev/00_overview.md
---

# Agent UI Polish — Diagnostic & Fix Plan

## Why This Exists

`devlog/_plan/260516_agent-mode-followup-jawdev/` 구현이 codex를 통해 완료됨.
코드 자체는 동작하지만 UI 퀄리티에 문제가 있음:
- 설정 패널이 raw HTML `<select>` 나열 → "React vanilla" 느낌
- Tool 영역의 height가 과도함
- 레이아웃 breakpoint/CSS grid min mismatch로 예기치 않은 세로 전환 발생
- 기존 앱의 design language (settings-controls.css)와 일관성 부족

## User Requirements (260517)

1. **레이아웃 세로 전환 문제** — 가로 3분할이 갑자기 세로로 바뀜
2. **Tool 이중접힘** — cli-jaw 스타일 동작 확인/보정
3. **Queue** — cli-jaw 처럼 사용 가능 확인
4. **병렬 생성** — 프롬프트/tool 정의로 이미지 생성 병렬화
5. **오른쪽 사이드바** — 양식/퀄리티 등 폼 개선
6. **우측상단 모델 chip** — TopBar에 모델 지정 진입점
7. **세션별 스피너** — 세션 돌아갈 때 spinner 표시

## Diagnosis Summary

| # | 증상 | 원인 | 심각도 |
|---|---|---|---|
| 0 | **TypeError: Cannot read properties of undefined (reading 'as_...')** — 런타임 크래시 | `agentApi.ts:18` jsonFetch의 `.catch(() => ({}))` → 200 OK + JSON parse 실패 시 빈 객체가 workspace state에 주입 → Record 필드 undefined → 렌더 시 `undefined[sessionId]` crash | 🔴🔴 |
| 1 | 3열 → 세로 전환 | sessions preference 시 breakpoint 임계값(**1180px**)이 CSS grid 최소합(**1220px**)보다 작아서 overflow; auto preference + 960~1279px는 rail/stacked로 떨어짐 | 🔴 |
| 2 | Tool height 과도 | Details dl 풀 펼침 + padding/gap 누적; input/output 무제한 길이 | 🟡 |
| 3 | 설정창 vanilla 느낌 | `<select>` raw 나열; 기존 `settings-controls.css`의 radio-option/card 패턴 미적용 | 🟡 |
| 4 | 모델 chip이 잘 안 보임 | `AgentChatPane.tsx:49-60`에 chip 이미 존재하나, desktop-three-pane에선 TopBar 자체가 없고 chip 스타일(11px)이 작아 눈에 안 띔. settings null 가능성도 있음 | 🟡 |
| 5 | quality/model 탭 동일 컴포넌트 | 둘 다 `AgentGenerationSettingsPanel` 렌더 → 분리 필요 | 🟡 |
| 6 | Session spinner 연결 확인 필요 | 컴포넌트/CSS 존재하나 실 렌더 검증 필요 | 🟢 |
| 7 | Queue 실 동작 확인 필요 | API/store 구현 있으나 polling/완료 반영 검증 필요 | 🟢 |

## Architecture Direction

코드를 다시 쓰지 않고, 기존 모듈을 가져오는 방식으로 개선:

1. **Layout**: breakpoint 수치 조정 + CSS grid min 낮추기 (280→240 session col)
2. **Settings UI**: 기존 `settings-controls.css` 패턴을 Agent sidebar에 import
3. **Tool UI**: Details 영역 max-height + truncate 적용
4. **TopBar**: model chip 렌더 추가 (CSS 이미 있음)
5. **Sidebar tab 분리**: quality → `AgentQualityPanel`, model → `AgentModelSelector`

## Implementation Priority (수정)

1. **Phase 0**: 런타임 크래시 수정 (jsonFetch + applyWorkspace 방어) — 이거 안 고치면 나머지 다 의미 없음
2. **Phase 1**: Layout breakpoint 수치 조정
3. **Phase 2**: Sidebar tab 내용 분리 (quality ≠ model)
4. **Phase 3**: TopBar model chip 강화
5. **Phase 4**: Settings UI polish (카드/segment 형태)
6. **Phase 5**: Tool height 제한 + 접힘 개선

## Plan Documents

- `00_runtime_crash_fix.md` ← **NEW (Phase 0)**
- `01_layout_breakpoint_fix.md`
- `02_settings_ui_polish.md`
- `03_tool_height_and_folding.md`
- `04_topbar_model_chip.md`
- `05_sidebar_tab_separation.md`
- `06_verification_checklist.md`

## Closeout (2026-07-11, 260711_production-hardening WP1-3)

Polish 0-5 전 항목 구현 완료 (상세: devlog/_plan/260711_production-hardening/030_implementation.md).
브라우저 QA 스크린샷: 260711_production-hardening/assets/qa-agent-*.png. 전체 스위트 1120개 0 fail.
