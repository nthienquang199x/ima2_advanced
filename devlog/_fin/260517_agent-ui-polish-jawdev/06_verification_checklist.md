---
created: 2026-05-17
status: plan
tags: [agent-mode, verification, qa, acceptance]
depends_on:
  - 00_overview.md
  - 01_layout_breakpoint_fix.md
  - 02_settings_ui_polish.md
  - 03_tool_height_and_folding.md
  - 04_topbar_model_chip.md
  - 05_sidebar_tab_separation.md
---

# Verification Checklist

## Pre-Implementation Checks

- [ ] 기존 `npm test` 전체 통과 확인 (749+ tests)
- [ ] `npx tsc --noEmit` 통과
- [ ] dev server 정상 기동 확인
- [ ] 현재 git status clean (기존 작업 보존)

## Per-Phase Verification

### Phase 1: Layout Breakpoint Fix

- [ ] `resolveAgentLayout` 단위 테스트 업데이트
- [ ] Chrome 1440x900 → desktop-three-pane 확인
- [ ] Chrome 1240x800 + sessions preference → desktop-three-pane, overflow 없음
- [ ] Chrome 1100x800 + auto → desktop-rail, 정상 표시
- [ ] Chrome 800x700 → tablet-stacked
- [ ] 리사이즈 시 레이아웃 전환 smooth

### Phase 2: Settings UI Polish

- [ ] Model selector: 카드 또는 segmented control 표시
- [ ] Quality: segmented control 표시
- [ ] Variants/Parallelism: stepper UI
- [ ] 테마 전환 (dark/light) 정상
- [ ] 설정 변경 → session settings 즉시 반영
- [ ] 기존 `settings-controls.css` 변수 사용 확인

### Phase 3: Tool Height & Folding

- [ ] Tool group 접힌 상태 32px 이하
- [ ] Tool call row 접힌 상태 28px 이하
- [ ] Long input/output 3줄 truncate
- [ ] "더보기" 클릭 시 전체 표시
- [ ] Outer/Inner 계층 시각적 구분 명확
- [ ] Details 영역 max-height scroll 동작

### Phase 4: TopBar Model Chip

- [ ] desktop-rail/mobile 모드에서 chip 표시
- [ ] desktop-three-pane에서 chat header에 chip 표시
- [ ] chip 클릭 → sidebar model 탭 열림
- [ ] sidebar에서 모델 변경 → chip 즉시 업데이트
- [ ] 긴 모델명 ellipsis 처리

### Phase 5: Sidebar Tab Separation

- [ ] quality 탭: size/format/moderation/variants/parallelism
- [ ] model 탭: model/provider/reasoning
- [ ] 두 탭 내용이 확실히 다름
- [ ] forms 탭에 템플릿 적용 기능

## Post-Implementation Checks

- [ ] `npm test` 전체 통과 (기존 749+ tests + 신규)
- [ ] `npx tsc --noEmit` 통과
- [ ] UI build 성공
- [ ] Chrome Computer Use QA (실제 화면 확인)
  - Agent 3열 레이아웃 정상
  - 설정 패널 polished 확인
  - Tool 접힘/펼침 동작
  - Queue 탭 동작
  - Model chip 클릭 → sidebar
  - Session spinner 표시

## Risks

| Risk | Mitigation |
|---|---|
| CSS grid min 변경으로 기존 wide-screen 레이아웃에 빈 공간 | fr 비율 유지로 stretch |
| Settings control 변경으로 기존 settings page 스타일 오염 | Agent-specific class prefix 유지 |
| Tool truncate로 중요 정보 가려짐 | "더보기" toggle 제공 |
| TopBar grid column 추가로 좁은 화면에서 overflow | @media 767px에서 chip 숨김 |

## Implementation Order (권장 — 료 검증 반영)

1. **Layout fix** (01) — 가장 눈에 띄는 regression 먼저
2. **Sidebar tab separation** (05) — model/quality 탭 분리 (chip의 도착지)
3. **Model chip visibility** (04) — 분리된 model 탭이 있어야 chip→탭 연동 의미 있음
4. **Settings UI polish** (02) — 분리된 컴포넌트를 card/segment로 polish
5. **Tool height** (03) — 독립적, 마지막 compact화

각 단계 후 `tsc + test + browser QA` 검증 루프.

> NOTE: Plan 04는 "신규 구현"이 아닌 "기존 chip 가시성 보강"임.
> AgentChatPane.tsx:49-60에 model chip이 이미 존재함을 전제로 작업.
