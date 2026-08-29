---
created: 2026-05-17
status: plan
tags: [agent-mode, settings-ui, design-system, polish]
depends_on:
  - 00_overview.md
---

# Settings UI Polish

## Problem

Agent 사이드바의 Model/Quality 설정이 raw `<select>` + `<input type="number">`로
기존 앱 Settings의 polished card/radio UI와 완전히 다른 look & feel.

## Current State (vanilla)

```tsx
// AgentModelSelector.tsx:17
<select value={settings.model} onChange={...}>
  {IMAGE_MODEL_OPTIONS.map(option => <option .../>)}
</select>

// AgentQualityPanel.tsx:16-53
<select value={settings.quality}>...</select>
<select value={settings.size}>...</select>
<select value={settings.format}>...</select>
<input type="number" min={1} max={8} value={settings.variants} />
```

CSS:
```css
.agent-settings-grid select,
.agent-settings-grid input {
  height: 34px;
  border: 1px solid var(--border);
  border-radius: 7px;
}
```

→ 텍스트 라벨 + bare select + bare number input. 시각적 계층/그룹핑/피드백 없음.

## Target State (앱 design language 재사용)

기존 `settings-controls.css` 패턴:
- `.settings-radio-option` — 카드형 라디오 (border, hover state, checked state)
- `.settings-field__label` — mono uppercase 11px 라벨
- hover → `border-strong`, checked → accent soft gradient

## Fix Plan

### A. Model Selector 개선

**Before**: bare `<select>` 하나

**After**: 라디오 카드 그리드 or segmented control

```text
┌──────────────────────────────────────┐
│ MODEL                                │
│ ┌────────────┐ ┌────────────┐       │
│ │ ● GPT-5.4  │ │ ○ GPT-4.1  │ ...  │
│ │   high res  │ │   standard │       │
│ └────────────┘ └────────────┘       │
├──────────────────────────────────────┤
│ PROVIDER                             │
│ ┌───────────────┐┌────────────────┐ │
│ │ ● OAuth       ││ ○ API Key     │ │
│ └───────────────┘└────────────────┘ │
├──────────────────────────────────────┤
│ REASONING                            │
│ [ low ] [medium] [ high ] [ xhigh ] │
└──────────────────────────────────────┘
```

구현 방향:
- Model은 3개 전부 card로 표시 (IMAGE_MODEL_OPTIONS가 3종뿐: gpt-5.4-mini, gpt-5.4, gpt-5.5)
- Provider는 2-segment toggle
- Reasoning은 4-segment toggle (기존 앱의 `ReasoningEffortSelect` 패턴 참조)

> NOTE: `ui/src/lib/imageModels.ts`에 모델이 3개뿐이므로 "More..." 드롭다운 불필요.

### B. Quality Panel 개선

**Before**: 6개 bare form 요소 나열

**After**: 그룹별 카드 분리

```text
┌──────────────────────────────────────┐
│ IMAGE                                │
│  Quality: [ low | med | high ]       │
│  Size:    segmented [ 1:1 | 3:2 | …] │
│  Format:  [ PNG | JPEG | WebP ]      │
├──────────────────────────────────────┤
│ GENERATION                           │
│  Moderation: [ auto | low ]          │
│  Variants:   [ – 2 + ]              │
│  Parallel:   [ – 1 + ]              │
└──────────────────────────────────────┘
```

구현 방향:
- Quality/Size/Format → segmented control (button group with active state)
- Variants/Parallelism → stepper (decrement / value / increment)
- Moderation → 2-segment

### C. CSS 재사용 전략

기존 `.settings-radio-option`, `.settings-field__label` 을 Agent 내에서도 사용:
- `agent-workspace-sidebar.css`에 agent-specific override만 추가
- 공통 패턴은 `settings-controls.css`를 import해서 사용
- 새 클래스: `.agent-segment-control`, `.agent-stepper`

Agent-specific override (사이드바 폭 제약 대응):
```css
.agent-sidebar-section .settings-radio-option {
  min-height: 40px;    /* 원본 64px → compact */
  padding: 8px 10px;   /* 원본 12px */
}

.agent-segment-control {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(48px, 1fr));
  gap: 3px;
  padding: 2px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--control-bg);
}

.agent-segment-control button {
  min-height: 30px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--text-dim);
  font-size: 12px;
  cursor: pointer;
}

.agent-segment-control button.active {
  background: var(--surface-2);
  color: var(--text);
  box-shadow: 0 1px 3px var(--shadow-soft);
}

.agent-stepper {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) 30px;
  align-items: center;
  gap: 4px;
  height: 34px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
}

.agent-stepper button {
  height: 100%;
  border: 0;
  background: transparent;
  color: var(--text-dim);
  font-size: 16px;
  cursor: pointer;
}

.agent-stepper span {
  text-align: center;
  font-weight: 600;
  font-size: 13px;
}
```

## Affected Files

| File | Action |
|---|---|
| `ui/src/components/agent/AgentModelSelector.tsx` | MODIFY — card/segment UI |
| `ui/src/components/agent/AgentQualityPanel.tsx` | MODIFY — segment/stepper UI |
| `ui/src/styles/agent-workspace-sidebar.css` | MODIFY — segment/stepper CSS |
| `ui/src/styles/settings-controls.css` | READ ONLY (패턴 참조) |

## Acceptance Criteria

- Select box 대신 segmented control / radio card 사용
- 기존 설정 페이지와 톤앤매너 일치 (border, radius, font, color)
- Number input 대신 stepper (+/-) 사용
- Hover/active/focus 상태가 자연스러움
- 기존 테마 변수 (var(--accent), var(--border-strong) 등) 100% 활용
