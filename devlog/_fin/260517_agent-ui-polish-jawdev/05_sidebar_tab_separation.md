---
created: 2026-05-17
status: plan
tags: [agent-mode, sidebar, tabs, quality, model, forms]
depends_on:
  - 00_overview.md
  - 02_settings_ui_polish.md
---

# Sidebar Tab Separation & Right Sidebar Improvements

## Problem

1. `quality` 탭과 `model` 탭이 같은 `AgentGenerationSettingsPanel` 렌더
2. 사이드바 탭 6개인데 내용 분리가 모호
3. Forms 탭의 실용성 부족

## Current State

```tsx
// AgentRightSidebar.tsx:57-58
{sidebarTab === "quality" ? <AgentGenerationSettingsPanel .../> : null}
{sidebarTab === "model" ? <AgentGenerationSettingsPanel .../> : null}
```

둘 다 동일 컴포넌트를 렌더 → 탭을 바꿔도 내용이 같음.

`AgentGenerationSettingsPanel`은 `AgentModelSelector` + `AgentQualityPanel`을 합쳐 렌더하므로,
quality 탭이든 model 탭이든 모델+퀄리티 설정 전체가 한 번에 보임.

## Fix Plan

### A. 탭 역할 분리

| Tab | 컴포넌트 | 내용 |
|---|---|---|
| image | `AgentImagePane` | 현재 이미지 프리뷰 + 변형 + 컨텍스트(refs/web/memory) |
| library | `AgentPromptLibraryPanel` | 프롬프트 라이브러리 검색/삽입 |
| forms | `AgentFormTemplatePanel` | 양식/템플릿 (style lock, composition template) |
| quality | `AgentQualityPanel` (단독) | 이미지 quality/size/format/moderation/variants/parallelism |
| model | `AgentModelSelector` (단독) | model/provider/reasoning |
| queue | `AgentQueuePanel` | 대기열 상태/취소/재시도 |

### B. AgentRightSidebar.tsx 수정

```tsx
{sidebarTab === "quality" ? (
  <section className="agent-sidebar-section">
    <header><div><span>Quality</span><strong>Generation Settings</strong></div></header>
    <AgentQualityPanel settings={settings} onChange={onSettingsChange} />
  </section>
) : null}
{sidebarTab === "model" ? (
  <section className="agent-sidebar-section">
    <header><div><span>Model</span><strong>{settings.model}</strong></div></header>
    <AgentModelSelector settings={settings} onChange={onSettingsChange} />
  </section>
) : null}
```

### C. Forms 탭 개선

현재 `AgentFormTemplatePanel`이 어떤 상태인지 확인 필요.
구현 방향:
- 프롬프트 라이브러리에서 `agent:form` 태그된 항목을 필터해서 표시
- "양식 적용" = composer에 template text를 prefill
- "스타일 잠금" = session-level style lock으로 저장

### D. 탭 개수 최적화 (선택적)

6탭이 좁은 사이드바에서 과도할 수 있음:
- 안: quality + model을 합쳐서 "Settings" 탭 하나로 → 내부에서 accordion/section 분리
- 장점: 탭 5개로 줄어 아이콘/텍스트 여유
- 단점: 기존 구현에서 model/quality 나눈 의도 상실

**추천**: 분리 유지하되, 탭 라벨을 아이콘+축약어로 (🖼 / 📚 / 📋 / ⚙️ / 🤖 / ⏳)
→ CSS에서 `grid-template-columns: repeat(6, minmax(0, 1fr))`은 유지.

## Affected Files

| File | Action |
|---|---|
| `ui/src/components/agent/AgentRightSidebar.tsx` | MODIFY — quality/model 분리 렌더 |
| `ui/src/components/agent/AgentGenerationSettingsPanel.tsx` | KEEP — 호환용 유지 또는 삭제 |
| `ui/src/components/agent/AgentSidebarTabs.tsx` | MODIFY — 탭 라벨/아이콘 개선 |
| `ui/src/components/agent/AgentFormTemplatePanel.tsx` | MODIFY — 양식 적용 로직 |

## Acceptance Criteria

- quality 탭: size/format/moderation/variants/parallelism만 표시
- model 탭: model/provider/reasoning만 표시
- 탭 전환 시 내용이 확실히 다름
- forms 탭에 실제 양식/템플릿 적용 기능 존재
- 현재 모든 사이드바 탭이 기존 앱 design language 따름
