# Issue #93 Fix: Video Gallery Refresh After Generation

## Summary

Video generation completes but gallery doesn't update without F5. Image generation paths call `addHistory()` directly; video paths don't.

## Root Cause

1. `storeVideoImpl.ts` — `generateVideoImpl` and `animateImageImpl` never call `addHistory()` after video completes. Gallery update relies solely on polling's last tick.
2. `storeInflightImpl.ts` — When `shouldStop=true`, interval clears immediately. Only one final history fetch runs; if server indexing is slow, gallery misses the new video.

## Changes

### MODIFY `ui/src/store/storeVideoImpl.ts`

**Import addHistory:**
```diff
+import { addHistory } from "./storeGraphSave";
+import type { GenerateItem } from "../types";
```
(line 1 area — add alongside existing imports)

**generateVideoImpl — add addHistory after try-block success (line ~141):**
```diff
       get().scheduleGraphSave();
       void get().flushGraphSave("video-node-complete");
     }
+    if (result) {
+      const videoItem: GenerateItem = {
+        image: result.url,
+        filename: result.filename,
+        url: result.url,
+        mediaType: "video",
+        prompt,
+        elapsed: result.elapsed,
+        video: result.video as Record<string, unknown> ?? {},
+        videoSeries: result.videoSeries ?? null,
+        videoContinuity: result.videoContinuity ?? null,
+        revisedPrompt: result.revisedPrompt ?? null,
+        requestId: result.requestId ?? flightId,
+        createdAt: Date.now(),
+        sessionId: requestSessionId,
+      };
+      await addHistory(videoItem, set, get);
+    }
   } catch (error) {
```

**animateImageImpl — capture result, add addHistory (line ~204-212):**
```diff
-    await postVideoGenerateStream(
+    const result = await postVideoGenerateStream(
       { ... },
       { ... },
     );
+    const videoItem: GenerateItem = {
+      image: result.url,
+      filename: result.filename,
+      url: result.url,
+      mediaType: "video",
+      prompt: p,
+      elapsed: result.elapsed,
+      video: result.video as Record<string, unknown> ?? {},
+      videoSeries: result.videoSeries ?? null,
+      videoContinuity: result.videoContinuity ?? null,
+      revisedPrompt: result.revisedPrompt ?? null,
+      requestId: result.requestId ?? flightId,
+      createdAt: Date.now(),
+    };
+    await addHistory(videoItem, set, get);
   } catch (error) {
```

### MODIFY `ui/src/store/storeInflightImpl.ts`

**Grace-tick: require 2 consecutive shouldStop ticks before clearing interval (line 29-40):**
```diff
   const w = window as unknown as {
     __ima2InflightTimer?: number;
+    __ima2StopTicks?: number;
   };
   if (w.__ima2InflightTimer) return;
   const tick = async () => {
     const cur = get().inFlight;
     const shouldStop = cur.length === 0 && get().activeGenerations === 0;
     if (shouldStop) {
-      if (w.__ima2InflightTimer) {
+      w.__ima2StopTicks = (w.__ima2StopTicks ?? 0) + 1;
+      if (w.__ima2StopTicks >= 2 && w.__ima2InflightTimer) {
         clearInterval(w.__ima2InflightTimer);
         w.__ima2InflightTimer = undefined;
+        w.__ima2StopTicks = 0;
       }
+    } else {
+      w.__ima2StopTicks = 0;
     }
```

### NEW `tests/video-gallery-refresh-contract.test.ts`

Contract test verifying:
1. Video done result includes fields required by addHistory (filename, url, mediaType)
2. Grace-tick polling does not clear interval on first shouldStop tick

## Verification

- `npx tsc --noEmit` — zero errors
- `npm test` — 968+ tests pass, including new contract test
- Employee audit: verify imports resolve, no regressions
