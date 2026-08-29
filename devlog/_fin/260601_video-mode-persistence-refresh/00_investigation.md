---
created: 2026-06-01
tags: [bug, video, ui, persistence, localStorage, continueFromItem]
status: investigated (not fixed)
prior: 260531_video-settings-persistence/00_investigation.md
---

# Video Mode Resets to Image on Page Refresh

## 증상

사용자가 Video 모드로 동영상을 생성한 뒤 페이지를 새로고침하면,
**항상 이미지 모드로 폴백**됨. 이전에 동영상을 생성했다면 Video 설정이 유지돼야 함.

추가로, 갤러리에서 동영상 아이템에 "여기서 이어서"를 눌러도 **Video 모드로 전환되지 않음**.

## 근본 원인 (3건)

### 1. `videoModelSelected`가 localStorage에 저장되지 않음

```
파일: ui/src/store/useAppStore.ts:3107
```

```typescript
videoModelSelected: false,  // 하드코딩 — 새로고침 시 항상 false
```

비교: `imageModel`은 `ima2.imageModel` 키로 localStorage에 저장/복원됨 (line 228-240).
비디오는 아무것도 저장하지 않음.

| 속성 | 저장? | 키 | 초기값 |
|------|------|----|--------|
| imageModel | ✅ | `ima2.imageModel` | `gpt-5.4-mini` |
| videoModelSelected | ❌ | 없음 | `false` |
| videoDuration | ❌ | 없음 | `5` |
| videoResolution | ❌ | 없음 | `"480p"` |
| videoAspectRatio | ❌ | 없음 | `"auto"` |

### 2. `continueFromItem()`이 Video 모드를 활성화하지 않음

```
파일: ui/src/lib/continueFromItem.ts:32-45
```

동영상 아이템에서 "여기서 이어서"를 눌렀을 때:
- ✅ 마지막 프레임을 참조 이미지로 추출
- ✅ 비디오 연속성 계보(lineage) 설정
- ✅ 비디오 토픽 설정
- ❌ **`selectVideoModel()` 미호출** — Video 모드로 전환 안 됨

```typescript
if (isVideo) {
  const frameDataUrl = await extractLastFrame(videoSrc);
  store.addReferenceDataUrl(frameDataUrl);
  const lineage = buildVideoContinuityFromItem(item);
  store.setVideoContinuityLineage(lineage);
  // ← selectVideoModel() 호출 없음!
}
```

### 3. `setImageModel()`이 무조건 Video 모드를 끔

```
파일: ui/src/store/useAppStore.ts:3092-3094
```

```typescript
setImageModel: (imageModel) => {
  saveImageModel(imageModel);
  set({ videoModelSelected: false });  // 어떤 이미지 모델을 선택하든 Video 꺼짐
```

이것 자체는 정상이지만, **새로고침 시 `loadImageModel()`이 호출되면서
이미지 모델이 복원**되고, videoModelSelected는 false로 시작 → Video 모드가 복원될 기회가 없음.

## 영향받는 코드 경로

### 경로 A: Video 버튼 토글
```
PromptComposer.tsx:318-323
  → selectVideoModel("grok-imagine-video-1.5-preview")
  → set({ videoModelSelected: model })
  → 새로고침 → videoModelSelected: false ← 버그
```

### 경로 B: 갤러리 "여기서 이어서"
```
ResultActions.tsx:104 → continueFromItem(item)
  → isVideo → extractLastFrame, setContinuityLineage
  → selectVideoModel() 미호출 ← 버그
  → 새로고침 → 모든 비디오 상태 리셋 ← 버그
```

### 경로 C: 컴포저 "이어가기" 버튼
```
PromptComposer.tsx:305 → continueFromItem(currentImage)
  → 경로 B와 동일한 문제
```

## 수정 방향

### 필수 (P0)

1. **`persistenceRegistry.ts`에 `"ima2.videoDefaults"` 키 추가**
2. **`useAppStore.ts`에 `saveVideoDefaults()` / `loadVideoDefaults()` 헬퍼**
   - 저장 대상: `{ model, duration, resolution, aspectRatio }`
   - `videoTopic`과 `videoContinuityLineage`는 세션 내 맥락이므로 저장 안 함
3. **`selectVideoModel()`에 save 호출 추가**
4. **비디오 setter에 save 호출 추가** (`setVideoDuration`, `setVideoResolution`, `setVideoAspectRatio`)
5. **스토어 초기화 시 `loadVideoDefaults()`로 복원**
   - `videoModelSelected`가 truthy이면 provider도 `"grok"`으로 설정

### 필수 (P1)

6. **`continueFromItem()` — Video 아이템일 때 `selectVideoModel()` 호출**
   - 원본 아이템의 `videoContinuity?.model`이 있으면 그 모델 사용
   - 없으면 기본 `"grok-imagine-video-1.5-preview"` 사용

### 선택 (P2)

7. **탭 간 동기화** — `syncFromStorage()`에 video defaults 반영
8. **Video 모드 해제 시** `saveVideoDefaults({ model: false })` 호출하여 다음 새로고침에서 이미지 모드로 시작

## 관련 파일

| 파일 | 역할 |
|------|------|
| `ui/src/store/persistenceRegistry.ts` | localStorage 키 레지스트리 |
| `ui/src/store/useAppStore.ts:3107-3122` | Video state + setter |
| `ui/src/store/useAppStore.ts:228-240` | imageModel 저장/로드 (참고용) |
| `ui/src/lib/continueFromItem.ts:32-45` | continue 로직 — selectVideoModel 누락 |
| `ui/src/components/PromptComposer.tsx:315-324` | Video 토글 버튼 |
| `ui/src/components/ResultActions.tsx:101-123` | 갤러리 "여기서 이어서" |
| `ui/src/lib/imageModels.ts:51-59` | Video 모델 정의 |
