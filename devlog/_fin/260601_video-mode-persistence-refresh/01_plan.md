---
created: 2026-06-01
tags: [plan, video, persistence, bug-fix]
status: plan
---

# Plan: Video Mode Persistence on Refresh

## Part 1 — 요약

Video 모드 설정(모델, 해상도, 비율)이 새로고침 시 이미지 모드로 리셋되는 버그 수정.
이미지 모델과 동일한 localStorage 패턴을 비디오에도 적용하고,
"여기서 이어서" 시 비디오 아이템이면 자동으로 Video 모드를 켜도록 한다.

## Part 2 — Diff-level Plan

### MODIFY: `ui/src/store/persistenceRegistry.ts`

**Before (line 29):**
```typescript
  "ima2.workspaceOverrides",
] as const;
```

**After:**
```typescript
  "ima2.workspaceOverrides",
  // video
  "ima2.videoDefaults",
] as const;
```

**Before (line 52):**
```typescript
export const WORKSPACE_OVERRIDES_STORAGE_KEY = PERSISTED_KEYS[18];
```

**After:**
```typescript
export const WORKSPACE_OVERRIDES_STORAGE_KEY = PERSISTED_KEYS[18];
export const VIDEO_DEFAULTS_STORAGE_KEY = PERSISTED_KEYS[19];
```

**Before (line 80):**
```typescript
  "ima2.workspaceOverrides": { domain: "layout", shape: "json:WorkspaceOverrides", resetSafe: true },
};
```

**After:**
```typescript
  "ima2.workspaceOverrides": { domain: "layout", shape: "json:WorkspaceOverrides", resetSafe: true },
  "ima2.videoDefaults": { domain: "generation", shape: "json:{model,duration,resolution,aspectRatio}", resetSafe: true },
};
```

---

### MODIFY: `ui/src/store/useAppStore.ts`

#### A. Import 추가 (top)
```typescript
import { VIDEO_DEFAULTS_STORAGE_KEY } from "./persistenceRegistry";
```

#### B. save/load 헬퍼 추가 (line ~254, after saveWebSearchEnabled)

```typescript
type VideoDefaults = {
  model: string | false;
  duration: number;
  resolution: string;
  aspectRatio: string;
};

function loadVideoDefaults(): VideoDefaults {
  try {
    const raw = localStorage.getItem(VIDEO_DEFAULTS_STORAGE_KEY);
    if (!raw) return { model: false, duration: 5, resolution: "480p", aspectRatio: "auto" };
    const p = JSON.parse(raw) as Record<string, unknown>;
    return {
      model: typeof p.model === "string" ? p.model : false,
      duration: typeof p.duration === "number" ? p.duration : 5,
      resolution: p.resolution === "480p" || p.resolution === "720p" ? p.resolution : "480p",
      aspectRatio: typeof p.aspectRatio === "string" ? p.aspectRatio : "auto",
    };
  } catch {
    return { model: false, duration: 5, resolution: "480p", aspectRatio: "auto" };
  }
}

function saveVideoDefaults(patch: Partial<VideoDefaults>): void {
  try {
    const current = loadVideoDefaults();
    localStorage.setItem(VIDEO_DEFAULTS_STORAGE_KEY, JSON.stringify({ ...current, ...patch }));
  } catch {}
}
```

#### C. 스토어 초기화 (line ~1339)

**Before:**
```typescript
const storedGenerationDefaults = loadGenerationDefaults();
const storedImageModel = loadImageModel();
const initialProvider = ...;
```

**After:**
```typescript
const storedGenerationDefaults = loadGenerationDefaults();
const storedImageModel = loadImageModel();
const storedVideoDefaults = loadVideoDefaults();
const initialProvider = ...;
```

#### D. 초기 state 변경 (line ~3107)

**Before:**
```typescript
videoModelSelected: false,
videoDuration: 5,
videoResolution: "480p",
videoAspectRatio: "auto",
```

**After:**
```typescript
videoModelSelected: storedVideoDefaults.model,
videoDuration: storedVideoDefaults.duration,
videoResolution: storedVideoDefaults.resolution as VideoResolutionUI,
videoAspectRatio: storedVideoDefaults.aspectRatio,
```

#### E. selectVideoModel에 save 추가 (line ~3114)

**Before:**
```typescript
selectVideoModel: (model) => {
  set({ videoModelSelected: model || "grok-imagine-video" });
  if (get().provider !== "grok") get().setProvider("grok");
},
```

**After:**
```typescript
selectVideoModel: (model) => {
  const m = model || "grok-imagine-video";
  set({ videoModelSelected: m });
  saveVideoDefaults({ model: m });
  if (get().provider !== "grok") get().setProvider("grok");
},
```

#### F. video setter에 save 추가 (line ~3118)

**Before:**
```typescript
setVideoDuration: (videoDuration) => set({ videoDuration }),
setVideoResolution: (videoResolution) => set({ videoResolution }),
setVideoAspectRatio: (videoAspectRatio) => set({ videoAspectRatio }),
```

**After:**
```typescript
setVideoDuration: (videoDuration) => { set({ videoDuration }); saveVideoDefaults({ duration: videoDuration }); },
setVideoResolution: (videoResolution) => { set({ videoResolution }); saveVideoDefaults({ resolution: videoResolution }); },
setVideoAspectRatio: (videoAspectRatio) => { set({ videoAspectRatio }); saveVideoDefaults({ aspectRatio: videoAspectRatio }); },
```

#### G. setImageModel의 videoModelSelected false 시 save 추가 (line ~3094)

**Before:**
```typescript
set({ videoModelSelected: false });
```

**After:**
```typescript
set({ videoModelSelected: false });
saveVideoDefaults({ model: false });
```

#### H. 초기 provider에 video 모델 반영 (line ~1341)

**Before:**
```typescript
const initialProvider =
  isGrokImageModel(storedImageModel) ? "grok" : (storedGenerationDefaults.provider ?? "oauth") === "grok" ? "oauth" : (storedGenerationDefaults.provider ?? "oauth");
```

**After:**
```typescript
const initialProvider =
  storedVideoDefaults.model ? "grok" :
  isGrokImageModel(storedImageModel) ? "grok" : (storedGenerationDefaults.provider ?? "oauth") === "grok" ? "oauth" : (storedGenerationDefaults.provider ?? "oauth");
```

#### I. syncFromStorage에 video defaults 반영 (line ~1779)

**Before:**
```typescript
syncFromStorage: () => {
  const nextInflight = loadInFlight();
  const nextSelected = loadSelectedFilename();
  const nextImageModel = loadImageModel();
  set((s) => {
    ...
    return {
      inFlight: nextInflight,
      activeGenerations: nextInflight.length,
      imageModel: nextImageModel,
      currentImage: ...,
    };
  });
```

**After:**
```typescript
syncFromStorage: () => {
  const nextInflight = loadInFlight();
  const nextSelected = loadSelectedFilename();
  const nextImageModel = loadImageModel();
  const nextVideo = loadVideoDefaults();
  set((s) => {
    ...
    return {
      inFlight: nextInflight,
      activeGenerations: nextInflight.length,
      imageModel: nextImageModel,
      videoModelSelected: nextVideo.model,
      videoDuration: nextVideo.duration,
      videoResolution: nextVideo.resolution as VideoResolutionUI,
      videoAspectRatio: nextVideo.aspectRatio,
      currentImage: ...,
    };
  });
```

---

### MODIFY: `ui/src/lib/continueFromItem.ts`

**Before (line 32-45):**
```typescript
if (isVideo) {
  const videoSrc = item.url || item.image;
  const frameDataUrl = await extractLastFrame(videoSrc);
  store.addReferenceDataUrl(frameDataUrl);
  const lineage = buildVideoContinuityFromItem(item);
  store.setVideoContinuityLineage(lineage);
  if (lineage) {
    store.insertPromptToComposer(buildContinuityPromptChip(lineage));
  }
  if (item.videoSeries?.topic) {
    store.setVideoTopic(item.videoSeries.topic);
  }
}
```

**After:**
```typescript
if (isVideo) {
  const videoSrc = item.url || item.image;
  const frameDataUrl = await extractLastFrame(videoSrc);
  store.addReferenceDataUrl(frameDataUrl);
  const lineage = buildVideoContinuityFromItem(item);
  store.setVideoContinuityLineage(lineage);
  if (lineage) {
    store.insertPromptToComposer(buildContinuityPromptChip(lineage));
  }
  if (item.videoSeries?.topic) {
    store.setVideoTopic(item.videoSeries.topic);
  }
  if (!store.videoModelSelected) {
    store.selectVideoModel("grok-imagine-video-1.5-preview");
  }
}
```

## 관련 파일

| 파일 | 변경 |
|------|------|
| `ui/src/store/persistenceRegistry.ts` | MODIFY — `ima2.videoDefaults` 키 등록 |
| `ui/src/store/useAppStore.ts` | MODIFY — save/load 헬퍼, 초기화, setter, sync |
| `ui/src/lib/continueFromItem.ts` | MODIFY — Video 아이템 → selectVideoModel() |

## Closeout (2026-07-11, 260711_production-hardening WP5)

Video mode 새로고침 persistence + continue-from-video 모드 전환 모두 코드 반영 확인:
useAppStore.ts:388(videoModelSelected 복원), continueFromItem.ts:45(selectVideoModel 호출).
계약 테스트: tests/video-defaults-persistence-contract.test.js (7 pass).
