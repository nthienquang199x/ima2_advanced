---
created: 2026-05-17
status: plan
tags: [agent-mode, tool-ui, height, folding, cli-jaw]
depends_on:
  - 00_overview.md
---

# Tool Height & Folding Improvements

## Problem

1. Tool 영역의 펼침 height가 과도함
2. cli-jaw 스타일 이중접힘 구현은 되어 있으나 시각적 구분이 약함

## Current Implementation

이중접힘 구조는 이미 존재:
```
AgentToolGroup (outer collapse)
  → AgentToolCallRow[] (inner collapse per call)
    → AgentToolCallDetails (input/output/requestId/duration)
```

### 문제 1: Details 내용이 길어서 height 폭발

`AgentToolCallDetails` 에서:
- `inputSummary` — 프롬프트 전체 or tool input JSON (수십~수백자)
- `outputSummary` — 결과 설명 (길 수 있음)
- requestId, duration은 짧음

→ input/output이 긴 경우 한 tool call 상세가 200px+ 차지.

### 문제 2: 시각적 계층이 약함

- Outer group toggle: dashed border, green dot
- Inner call row: solid border, status dot
- 둘 다 비슷한 크기와 스타일 → 사용자가 "어디까지가 1단 접힘이고 어디가 2단인지" 구분 어려움

## Fix Plan

### A. Details truncate + max-height

```css
.agent-tool-call-details dd {
  max-height: 3.6em;      /* 약 3줄 */
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.agent-tool-call-details dd.is-expanded {
  max-height: none;
  -webkit-line-clamp: unset;
}
```

각 dd에 "더보기" 클릭시 `is-expanded` toggle.

TSX 패턴 (AgentToolCallDetails에 state 추가):
```tsx
const [expandedFields, setExpandedFields] = useState<Record<string, boolean>>({});
const toggle = (key: string) => setExpandedFields(prev => ({...prev, [key]: !prev[key]}));

// 각 dd에:
<dd
  className={expandedFields[key] ? "is-expanded" : undefined}
  onClick={() => toggle(key)}
  role="button"
  tabIndex={0}
>
  {value}
</dd>
```

toggle 대상은 `inputSummary`와 `outputSummary` 2개만 (requestId/duration은 항상 짧으므로 불필요).

### B. Outer group을 더 compact하게

현재 outer toggle:
```css
.agent-message__tool-toggle {
  padding: 8px 10px;
  border: 1px dashed var(--border);
}
```

cli-jaw 스타일처럼 더 타이트하게:
```css
.agent-message__tool-toggle {
  padding: 5px 8px;
  min-height: 32px;  /* 현재 암묵적 ~38px → 32px */
}
```

### C. Inner call row도 compact

```css
.agent-tool-call-row__toggle {
  padding: 5px 7px;   /* 현재 7px 8px */
  min-height: 28px;
}
```

### D. 시각적 계층 강화

Outer group: 왼쪽에 2px accent bar (cli-jaw의 그룹 표시 패턴)
Inner call: indent + 좌측 thin line (tree connector 느낌)

```css
.agent-message--tool.is-collapsible {
  border-left: 2px solid var(--border-strong);
  padding-left: 10px;
}

.agent-tool-call-list {
  padding-left: 12px;
  border-left: 1px solid var(--border);
}
```

### E. 전체 tool group max-height (선택적)

펼쳤을 때 tool call이 10개 이상이면 스크롤:
```css
.agent-message__tool-details {
  max-height: min(400px, 50vh);
  overflow-y: auto;
}
```

## Affected Files

| File | Action |
|---|---|
| `ui/src/styles/agent-workspace-panels.css` | MODIFY — padding/height/truncate |
| `ui/src/styles/agent-workspace-sidebar.css` | MODIFY — tool call details truncate |
| `ui/src/components/agent/AgentToolCallDetails.tsx` | MODIFY — 더보기 toggle state |
| `ui/src/components/agent/AgentToolGroup.tsx` | MODIFY — compact padding |

## Acceptance Criteria

- Tool group 접힌 상태: 32px 높이의 한 줄 summary
- Tool group 펼친 상태: 각 call row 28px 높이
- Call details: input/output 3줄 이상이면 truncate + "..." 표시
- Outer → Inner 접힘 계층이 시각적으로 명확 (indent + border)
- 전체 tool details 영역 max-height 400px, 넘으면 scroll
