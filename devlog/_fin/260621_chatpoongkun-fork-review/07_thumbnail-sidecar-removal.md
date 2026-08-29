# Feature 7: Thumbnail Sidecar Removal

Verdict: **ADAPT**

## What

이미지 썸네일 sidecar 파일 생성 중지.
갤러리가 원본 이미지를 직접 사용하므로 불필요.
video(.mp4) 썸네일만 유지.

## Files

| File | Change | Conflict |
|------|--------|----------|
| `lib/thumbBackfill.ts` | kind 타입 축소, 필터 regex mp4만 | Low (upstream 동일) |
| `routes/generate.ts` | generateImageThumbnailFromBuffer import/call 제거 | Med (수작업 필요) |

## Quality

- 타입 축소 (`"image" | "video"` → `"video"`) 일관적
- JSDoc 업데이트 완료

## Cherry-pick Plan

1. `lib/thumbBackfill.ts`는 그대로 cherry-pick
2. `routes/generate.ts`에서 `generateImageThumbnailFromBuffer` import/call은 현재 upstream 기준 수작업 제거
3. 다른 모듈에서 image thumbnail 의존하는 곳 없는지 grep 확인 필요
