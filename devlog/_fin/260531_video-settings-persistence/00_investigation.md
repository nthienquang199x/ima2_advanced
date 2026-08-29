---
created: 2026-05-31
tags: [bug, video, ui, persistence, localStorage]
status: investigated (not fixed)
---

# Video Settings Not Persisted on Tab Switch

## 증상

이미지 생성 설정(모델, 품질, 사이즈 등)은 탭 전환/새로고침 후에도 유지되지만,
비디오 설정(모델, duration, resolution, aspect ratio)은 기본값으로 리셋됨.

## 원인

### 이미지 설정 — 정상 동작

수동 localStorage 저장 방식 사용:
- `ima2.imageModel` — `saveImageModel()` / `loadImageModel()`
- `ima2.reasoningEffort` — `saveReasoningEffort()` / `loadReasoningEffort()`
- `ima2.generationDefaults` (JSON blob) — provider, quality, size, format, moderation, count 등

모든 setter가 `saveGenerationDefaultsPatch()`를 호출하여 변경 즉시 localStorage에 저장.
스토어 초기화 시 `loadGenerationDefaults()`로 복원.

### 비디오 설정 — 버그

Zustand 스토어에 in-memory로만 존재:
```typescript
videoModelSelected: false,      // hardcoded
videoDuration: 5,               // hardcoded
videoResolution: "480p",        // hardcoded
videoAspectRatio: "auto",       // hardcoded
videoTopic: "",                 // hardcoded
```

setter들 (`setVideoDuration`, `setVideoResolution` 등)이 `set({...})`만 호출하고
localStorage에 저장하지 않음.

## 수정 방향

### Option B 권장 (별도 키)

1. `ui/src/store/persistenceRegistry.ts` — `"ima2.videoDefaults"` 키 등록
2. `ui/src/store/useAppStore.ts`:
   - `saveVideoDefaults()` / `loadVideoDefaults()` 헬퍼 추가
   - 비디오 setter들에 save 호출 추가
   - 초기 상태를 load 함수에서 읽도록 변경

### 저장할 필드

```json
{
  "model": "grok-imagine-video" | "grok-imagine-video-1.5-preview",
  "duration": 5,
  "resolution": "480p" | "720p",
  "aspectRatio": "auto" | "16:9" | "9:16" | "1:1" | ...,
  "topic": ""
}
```

## 관련 파일

- `ui/src/store/useAppStore.ts` — 비디오 state + setter
- `ui/src/store/persistenceRegistry.ts` — localStorage 키 레지스트리
- `ui/src/components/VideoControlsPanel.tsx` — 비디오 설정 UI
