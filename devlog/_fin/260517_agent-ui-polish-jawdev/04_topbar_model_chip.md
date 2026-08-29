---
created: 2026-05-17
status: plan
tags: [agent-mode, topbar, model-chip, visibility, sidebar-sync]
depends_on:
  - 00_overview.md
---

# Model Chip Visibility Fix

## Problem

요구사항 6: "우측상단 모델 지정 설정 → 사이드바 모델 탭 연동"

## 진단 (료 검증 반영)

### Model chip은 이미 존재한다

`AgentChatPane.tsx:49-60`:
```tsx
{modelSummary ? (
  <button
    type="button"
    className="agent-model-chip"
    aria-label={t("agent.openModelSettings")}
    title={t("agent.openModelSettings")}
    onClick={onOpenModelSettings}
  >
    <span>{t("agent.model")}</span>
    <strong>{modelSummary}</strong>
  </button>
) : null}
```

`formatModelSummary`는 `${settings.model} · ${settings.quality} · ${settings.variants}x/${settings.parallelism}p` 형식.

### 사용자가 "안 보인다"고 한 원인 후보

| # | 후보 | 근거 |
|---|---|---|
| 1 | `settings`가 null/undefined → `modelSummary` 빈문자열 → 렌더 안됨 | `AgentChatPane` props에 settings가 optional 가능. `withAgentGenerationDefaults(selectedSession?.generationSettings)` — selectedSession이 null이면? |
| 2 | chip 스타일이 너무 작음 (font-size: 11px, max-width 제한) | `.agent-model-chip` CSS: 11px 텍스트, max-width min(230px, 34vw) |
| 3 | desktop-three-pane에서 TopBar 자체가 없음 | `AgentWorkspace.tsx:322`: `{!showSidebar ? <AgentTopBar ... /> : null}` — three-pane에선 TopBar 미렌더. **하지만** chip은 TopBar가 아닌 ChatPane pane-header에 있으므로 이건 무관 |

### 실제 조사 필요 항목

1. `withAgentGenerationDefaults(undefined)` 반환값 확인 → null이면 chip 안 보임
2. 브라우저에서 실제 chip DOM 존재 확인 (DevTools inspect)
3. chip이 있는데 작아서 못 본 건지, 아예 렌더 안 된 건지 구분

## Fix Plan

### A. settings null 방어 강화

`ui/src/lib/agentGenerationSettings.ts`의 `withAgentGenerationDefaults` 확인:
- undefined/null input → 반드시 기본값 객체 반환하도록 보장
- `AgentChatPane`에서 settings prop이 undefined이면 fallback 적용

### B. Chip 시각적 강조

현재 CSS:
```css
.agent-model-chip {
  font-size: 11px;
  max-width: min(230px, 34vw);
  min-height: 34px;
}
```

개선:
```css
.agent-model-chip {
  font-size: 12px;
  min-height: 36px;
  background: color-mix(in srgb, var(--accent) 8%, var(--control-bg));
  border-color: color-mix(in srgb, var(--accent) 20%, var(--border));
}

.agent-model-chip strong {
  font-size: 12px;
  font-weight: 600;
}
```

→ 배경에 accent tint + border에 accent 혼합으로 눈에 띄게.

### C. 모바일 미디어쿼리 대응

`agent-workspace-panels.css:522-525`의 모바일 규칙:
```css
@media (max-width: 767px) {
  .agent-model-chip {
    max-width: min(160px, 30vw);
  }
}
```

이미 있으면 확인, 없으면 추가.

### D. AgentTopBar에 추가 렌더는 불필요

chip은 이미 ChatPane pane-header에 있고, 모든 레이아웃에서 ChatPane은 표시됨.
TopBar에 중복 배치하면 desktop-rail에서 chip이 2곳에 보임 → 불필요.

## Affected Files

| File | Action |
|---|---|
| `ui/src/lib/agentGenerationSettings.ts` | VERIFY — withAgentGenerationDefaults null 방어 |
| `ui/src/components/agent/AgentChatPane.tsx` | VERIFY — settings prop 전달 경로 |
| `ui/src/styles/agent-workspace-sidebar.css` | MODIFY — chip 스타일 강조 |
| `ui/src/styles/agent-workspace-panels.css` | MODIFY — 모바일 chip 대응 |

## Acceptance Criteria

- 세션 선택 시 model chip이 chat header에 확실히 보임
- chip 폰트/배경이 주변 UI 대비 눈에 띔
- 클릭 → 사이드바 model 탭 열림 (이미 동작 중, 확인만)
- settings가 null인 edge case에서도 기본값 chip 표시
- 모바일에서 overflow 없음
