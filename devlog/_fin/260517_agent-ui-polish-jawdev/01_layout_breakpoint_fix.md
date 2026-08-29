---
created: 2026-05-17
status: plan
tags: [agent-mode, layout, breakpoint, css-grid, regression]
depends_on:
  - 00_overview.md
---

# Layout Breakpoint Fix

## Problem

사용자 창 크기에 따라 Agent 3열 레이아웃이 세로로 전환됨.

## Root Cause Analysis

### 1. CSS grid 최소 합 vs breakpoint 임계값 불일치

```css
/* agent-workspace.css:35 */
.agent-workspace__body {
  grid-template-columns: 280px minmax(420px, 0.95fr) minmax(520px, 1.05fr);
}
```

**최소 합**: 280 + 420 + 520 = **1220px**

```ts
/* agentLayout.ts:14 */
if (width >= 1280) return "desktop-three-pane";
```

- `auto` preference에서는 1280px부터 3열 → 문제 없음
- `sessions` preference에서는 **1180px**부터 3열 → **1220px 미만이면 overflow!**

### 2. 960~1279px 구간이 desktop-rail로 전환

```ts
if (width >= 960 && height >= 560) return "desktop-rail";
```

이 구간에서 세션 column이 64px rail로 축소되면서 "3분할 → 2분할처럼 보이는" 레이아웃으로 바뀜.
사용자가 기대하는 건 "풀 세션 목록 + 채팅 + 이미지"인데, rail 모드에선 아이콘만 보임.

### 3. desktop-rail의 CSS grid도 문제

```css
.agent-workspace--desktop-rail .agent-workspace__body {
  grid-template-columns: 64px minmax(420px, 1fr) minmax(440px, 1fr);
}
```

**최소 합**: 64 + 420 + 440 = **924px** — 960px breakpoint보단 작아서 overflow는 없지만,
타이트한 간격에서 우측 사이드바가 찌그러짐.

## Fix Plan

### A. breakpoint 조정 (`ui/src/lib/agentLayout.ts`)

```ts
export function resolveAgentLayout(input) {
  const { width, height, preference } = input;
  if (height < 560 && width < 1280) return "mobile-chat-image-sheet";
  // sessions preference일 때도 최소 1240px 필요 (grid min 1220 + 20px margin)
  if (width >= 1240 && preference === "sessions") return "desktop-three-pane";
  if (width >= 1024 && preference === "rail") return "desktop-rail";
  if (width >= 1280) return "desktop-three-pane";
  // rail 임계값 올리기: 1024→1060 (grid min 924 + 136px 여유)
  if (width >= 1060 && height >= 560) return "desktop-rail";
  if (width >= 768 && height >= 700) return "tablet-stacked";
  return "mobile-chat-image-sheet";
}
```

### B. CSS grid min 낮추기 (`ui/src/styles/agent-workspace.css`)

session column: 280 → 260px (모바일 대응)
chat min: 420 → 380px
image/sidebar min: 520 → 460px

```css
.agent-workspace__body {
  grid-template-columns: 260px minmax(380px, 0.95fr) minmax(460px, 1.05fr);
}
```

**새 최소합**: 260 + 380 + 460 = **1100px** — 1240px 임계값에 140px 여유.

### C. desktop-rail도 보정

```css
.agent-workspace--desktop-rail .agent-workspace__body {
  grid-template-columns: 64px minmax(380px, 1fr) minmax(400px, 1fr);
}
```

**새 최소합**: 64 + 380 + 400 = **844px** — 1060px breakpoint에 216px 여유.

## Affected Files

| File | Action |
|---|---|
| `ui/src/lib/agentLayout.ts` | MODIFY — breakpoint 수치 조정 |
| `ui/src/styles/agent-workspace.css` | MODIFY — grid min 조정 |
| `tests/agent-mode-layout-contract.test.js` | MODIFY — 테스트 기대값 업데이트 |

## Acceptance Criteria

- 1280px 이상 + auto → desktop-three-pane (변경 없음)
- 1240px + sessions → desktop-three-pane (overflow 없음)
- 1100~1239px + auto → desktop-rail (rail 정상 표시)
- 1060px + rail preference → desktop-rail (overflow 없음)
- 768~1059px → tablet-stacked (의도된 세로)
- Chrome DevTools 976x772에서 desktop-rail이 안정적으로 동작
