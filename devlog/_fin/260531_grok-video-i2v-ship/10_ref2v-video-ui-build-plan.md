# Phase 1 — Reference-to-Video + Video Model UI Surface (Classic + Node)

Date: 2026-05-31
Branch: `feat/grok-video-i2v`
Project root: `/Users/jun/Developer/new/700_projects/ima2-gen`
Parent roadmap: `00_execution-roadmap.md` · QA gate: `05_qa-gate.md`

This plan refines roadmap steps **B6 (Node), B8 (UI)** and pulls the previously
v2-deferred **reference-to-video** into v1, per Jun's confirmed design.

---

## Part 1 — Plain explanation (what changes, why)

Today the only way to make a video is the one-click **Animate** button on an
existing image (fixed I2V, 480p/5s). This plan adds a real **video generation
surface**: the user picks a new **`grok (v)`** entry in the left model selector,
and the right "세부 설정" panel switches to video controls (length / resolution /
ratio). The number of attached reference images decides the mode automatically —
**0 → text-to-video, 1 → image-to-video, 2–5 → reference-to-video** — and the
length selector auto-caps at 10s once 2+ images are attached. It works in both
Classic and Node modes, shows a live progress %, and reuses the existing 5-slot
reference UI (so no new image-count guard is needed). Agent mode is out of scope
here. After the QA gate + employee PASS, the `feat/grok-video-i2v` branch is
**pushed to origin (no main merge)**, version is bumped to **1.2.0**, and the
docs + GitHub Pages site are updated to say video is shipped.

### Business-logic decisions (already confirmed by Jun)
- Mode is derived from ref count (0/1/2+); no manual mode toggle.
- Ref2V length clamp ≤10s; I2V/T2V up to 15s.
- Reuse existing reference slots (cap 5 < xAI's 7).
- Selecting the video model auto-switches provider to **Grok**.
- Animate quick-action **stays**.
- No main merge; **push branch only**. Publish-prep (npm) excluded.

---

## Part 2 — Diff-level plan

### A. Backend (adapter accepts multiple references)

#### A1. MODIFY `lib/imageModels.ts`
- Extend video mode union + add ref2v knobs.
```diff
-export type VideoMode = "text-to-video" | "image-to-video";
+export type VideoMode = "text-to-video" | "image-to-video" | "reference-to-video";
+
+export const MAX_REF2V_REFERENCES = 7;       // xAI hard cap
+export const MAX_REF2V_DURATION = 10;        // xAI ref2v duration cap (seconds)
+
+// Derive the video mode from the number of attached reference images.
+export function deriveVideoMode(refCount: number): VideoMode {
+  if (refCount >= 2) return "reference-to-video";
+  if (refCount === 1) return "image-to-video";
+  return "text-to-video";
+}
+
+// Clamp duration to the ref2v ceiling when in reference-to-video mode.
+export function clampVideoDuration(duration: number, mode: VideoMode): number {
+  if (mode === "reference-to-video") return Math.min(duration, MAX_REF2V_DURATION);
+  return duration;
+}
```
- `normalizeVideoDuration` stays (1–15 validation); the ref2v clamp is applied
  in the route after mode is known.

#### A2. MODIFY `lib/grokVideoAdapter.ts`
- `GrokVideoOptions`: add `referenceImages?: string[]` (base64/data-uri/url list).
- `GrokVideoPlan`: `mode` already typed via `VideoMode` (now includes ref2v).
- `buildVideoGenerationPayload`: branch on mode.
```diff
 export function buildVideoGenerationPayload(
   plan: GrokVideoPlan,
-  opts: { model: string; sourceImageUrl?: string },
+  opts: { model: string; sourceImageUrl?: string; referenceImageUrls?: string[] },
 ): Record<string, unknown> {
-  if (plan.mode === "image-to-video" && !opts.sourceImageUrl) {
-    throw grokError("image-to-video requires a source image", 400, "GROK_VIDEO_INVALID_MODE");
-  }
+  if (plan.mode === "image-to-video" && !opts.sourceImageUrl) {
+    throw grokError("image-to-video requires a source image", 400, "GROK_VIDEO_INVALID_MODE");
+  }
+  const refs = opts.referenceImageUrls ?? [];
+  if (plan.mode === "reference-to-video") {
+    if (refs.length < 2) throw grokError("reference-to-video requires 2+ reference images", 400, "GROK_VIDEO_INVALID_MODE");
+    if (refs.length > MAX_REF2V_REFERENCES) throw grokError(`reference-to-video allows at most ${MAX_REF2V_REFERENCES} images`, 400, "GROK_VIDEO_REF_TOO_MANY");
+    if (opts.sourceImageUrl) throw grokError("reference-to-video cannot combine with a single source image", 400, "GROK_VIDEO_INVALID_MODE");
+  }
   const payload: Record<string, unknown> = { model: opts.model, prompt: plan.prompt, duration: plan.duration, resolution: plan.resolution };
   if (plan.aspectRatio && plan.aspectRatio !== "auto") payload.aspect_ratio = plan.aspectRatio;
-  if (plan.mode === "image-to-video") payload.image = { url: opts.sourceImageUrl };
+  if (plan.mode === "image-to-video") payload.image = { url: opts.sourceImageUrl };
+  if (plan.mode === "reference-to-video") payload.reference_images = refs.map((url) => ({ url }));
   return payload;
 }
```
- `GrokVideoOptions`: add `referenceImages?: string[]`.
- `buildGrokVideoPlannerPayload` — make continuity **3-way** + accept refs + extend tool enum:
```diff
 export function buildGrokVideoPlannerPayload(
   prompt: string,
-  opts: { model: string; mode: VideoMode; duration: number; resolution: VideoResolution; aspectRatio: VideoAspectRatio; plannerModel?: string; searchSummary?: string; sourceImageUrl?: string },
+  opts: { model: string; mode: VideoMode; duration: number; resolution: VideoResolution; aspectRatio: VideoAspectRatio; plannerModel?: string; searchSummary?: string; sourceImageUrl?: string; referenceImageUrls?: string[] },
 ) {
-  const isI2V = opts.mode === "image-to-video";
-  const continuity = isI2V
-    ? "This is image-to-video: preserve subject identity and composition unless asked otherwise, and use the source image as the first frame / starting point."
-    : "This is text-to-video: describe motion, camera, and action clearly.";
+  const isI2V = opts.mode === "image-to-video";
+  const isRef2V = opts.mode === "reference-to-video";
+  const continuity = isRef2V
+    ? "This is reference-to-video: use the provided reference images (referred to as <IMAGE_1>..<IMAGE_N>) as subject/style guidance and keep their subjects recognizable."
+    : isI2V
+    ? "This is image-to-video: preserve subject identity and composition unless asked otherwise, and use the source image as the first frame / starting point."
+    : "This is text-to-video: describe motion, camera, and action clearly.";
   const userContent: any[] = [ /* text block unchanged */ ];
   if (isI2V && opts.sourceImageUrl) {
     userContent.push({ type: "image_url", image_url: { url: opts.sourceImageUrl, detail: "high" } });
   }
+  if (isRef2V) {
+    for (const url of opts.referenceImageUrls ?? []) {
+      userContent.push({ type: "image_url", image_url: { url, detail: "high" } });
+    }
+  }
   // tools[0].function.parameters.properties.mode.enum:
-  mode: { type: "string", enum: ["text-to-video", "image-to-video"] },
+  mode: { type: "string", enum: ["text-to-video", "image-to-video", "reference-to-video"] },
 ```
- `planGrokVideo` — thread refs into planner + payload-prep; **duration is NOT
  clamped here** (route clamps once, §A3). Mode is decided by the route and passed
  in via `options.mode`:
```diff
   const search = await searchGrokVisualContext(prompt, ctx, { signal: options.signal, requestId: options.requestId });
+  const referenceImageUrls = (options.referenceImages ?? []).map((img) => sourceImageUrl(img, undefined));
   const payload = buildGrokVideoPlannerPayload(prompt, {
     model: cfg.model, mode, duration, resolution, aspectRatio,
     plannerModel: cfg.plannerModel, searchSummary: search.summary,
     sourceImageUrl: options.sourceImage ? sourceImageUrl(options.sourceImage, options.sourceMime) : undefined,
+    referenceImageUrls,
   });
```
  and set `const mode: VideoMode = options.mode ?? (options.sourceImage ? "image-to-video" : "text-to-video");`
- `generateVideoViaGrok` — build ref URLs and forward to payload:
```diff
   const srcUrl = options.sourceImage ? sourceImageUrl(options.sourceImage, options.sourceMime) : undefined;
+  const refUrls = (options.referenceImages ?? []).map((img) => sourceImageUrl(img, undefined));
   ...
-  const payload = buildVideoGenerationPayload(plan, { model, sourceImageUrl: srcUrl });
+  const payload = buildVideoGenerationPayload(plan, { model, sourceImageUrl: srcUrl, referenceImageUrls: refUrls });
```
  `plan.mode` comes from `planGrokVideo` (or the `plannedPrompt` shortcut, which
  must also honor `options.mode`).
- Add `import { MAX_REF2V_REFERENCES } from "./imageModels.js";` (used by payload guard).

#### A3. MODIFY `routes/video.ts`
- Add imports + a `toArray()` helper:
```diff
 import {
   normalizeGrokVideoModel,
   normalizeVideoResolution,
   normalizeVideoAspectRatio,
   normalizeVideoDuration,
+  deriveVideoMode,
+  clampVideoDuration,
+  MAX_REF2V_REFERENCES,
   type VideoMode,
 } from "../lib/imageModels.js";
+
+function toArray(v: unknown): unknown[] { return Array.isArray(v) ? v : []; }
```
- Replace the single-source resolve + rawMode derivation. The old code destructures
  `rawMode` and computes `source`; the new code resolves an array and derives mode
  **from count**. Remove `rawMode` from the destructure (now unused) and rewrite the
  3 downstream `source.*` references:
```diff
-      const { prompt, provider = "grok", model: rawModel, mode: rawMode } = req.body || {};
+      const { prompt, provider = "grok", model: rawModel } = req.body || {};
       ...
-      let source: { b64: string | null; filename: string | null };
-      try {
-        source = await resolveSourceImage(ctx, req.body?.sourceImage, req.body?.sourceFilename);
-      } catch (e: any) {
-        return fail(e?.status || 400, e?.code || "GROK_VIDEO_INVALID_MODE", e?.message || "invalid source image");
-      }
-      const mode: VideoMode = rawMode === "text-to-video" || rawMode === "image-to-video"
-        ? rawMode
-        : source.b64 ? "image-to-video" : "text-to-video";
-      if (mode === "image-to-video" && !source.b64) return fail(400, "GROK_VIDEO_INVALID_MODE", "image-to-video requires a source image");
+      const refInputs: Array<{ image?: unknown; filename?: unknown }> = [
+        ...toArray(req.body?.referenceImages).map((image) => ({ image })),
+        ...toArray(req.body?.referenceFilenames).map((filename) => ({ filename })),
+        ...(req.body?.sourceImage || req.body?.sourceFilename
+              ? [{ image: req.body?.sourceImage, filename: req.body?.sourceFilename }] : []),
+      ];
+      let resolved: Array<{ b64: string; filename: string | null }>;
+      try {
+        const all = await Promise.all(refInputs.map((r) => resolveSourceImage(ctx, r.image, r.filename)));
+        resolved = all.filter((r): r is { b64: string; filename: string | null } => Boolean(r.b64));
+      } catch (e: any) {
+        return fail(e?.status || 400, e?.code || "GROK_VIDEO_INVALID_MODE", e?.message || "invalid reference image");
+      }
+      if (resolved.length > MAX_REF2V_REFERENCES) return fail(400, "GROK_VIDEO_REF_TOO_MANY", `at most ${MAX_REF2V_REFERENCES} reference images`);
+      const mode: VideoMode = deriveVideoMode(resolved.length);
+      const duration = clampVideoDuration(durationCheck.duration, mode);
+      const referenceImages = mode === "reference-to-video" ? resolved.map((r) => r.b64) : undefined;
+      const sourceB64 = mode === "image-to-video" ? resolved[0]?.b64 : undefined;
+      const sourceFilename = resolved[0]?.filename ?? null;  // history continuity
```
- `startJob` meta + `generateVideoViaGrok` call + history meta use the new vars:
```diff
-        meta: { kind: "video", sessionId, clientNodeId, model: modelCheck.model, mode, duration: durationCheck.duration, resolution: resolutionCheck.resolution },
+        meta: { kind: "video", sessionId, clientNodeId, model: modelCheck.model, mode, duration, resolution: resolutionCheck.resolution },
       ...
       const result = await generateVideoViaGrok(prompt, ctx, {
         model: modelCheck.model,
         mode,
-        duration: durationCheck.duration,
+        duration,
         resolution: resolutionCheck.resolution,
         aspectRatio: aspectCheck.aspectRatio,
-        sourceImage: source.b64 || undefined,
+        sourceImage: sourceB64,
+        referenceImages,
         signal: cancelController.signal, requestId, onEvent,
       });
       ...
-          sourceImageFilename: source.filename,
+          sourceImageFilename: sourceFilename,
```
- `GrokVideoOptions` gains `mode?: VideoMode` (already present) and `referenceImages?`
  (added in A2); the route now passes both so the adapter does not re-derive mode.
- Also update the observability log to use the clamped value:
  `logEvent("video", "request", { ..., duration, ... })` (was `durationCheck.duration`).

### B. UI — model selector + video params

#### B1. MODIFY `ui/src/types.ts`
```diff
 export type GrokImageModel = "grok-imagine-image" | "grok-imagine-image-quality";
 export type ImageModel = OpenAIImageModel | GrokImageModel;
+export type VideoModel = "grok-imagine-video";
+export type VideoResolutionUI = "480p" | "720p";
```

#### B2. MODIFY `ui/src/lib/imageModels.ts`
```diff
 // add VideoModel to the existing type import
-import type { ImageModel, OpenAIImageModel, Provider, UnsupportedImageModel } from "../types";
+import type { ImageModel, OpenAIImageModel, Provider, UnsupportedImageModel, VideoModel } from "../types";
+
+export const VIDEO_MODEL_OPTIONS: Array<{ value: VideoModel; shortLabel: string; fullLabelKey: string }> = [
+  { value: "grok-imagine-video", shortLabel: "grok (v)", fullLabelKey: "settings.videoModel.grokImagine" },
+];
+export function isVideoModelValue(v: unknown): v is VideoModel {
+  return v === "grok-imagine-video";
+}
+
+// UI-side mirrors of the backend helpers (lib/imageModels.ts) — the UI lib is a
+// SEPARATE module, so these must be declared here for the store/panel to import.
+export const MAX_REF2V_DURATION_UI = 10;
+export function deriveVideoModeUI(refCount: number): "text-to-video" | "image-to-video" | "reference-to-video" {
+  if (refCount >= 2) return "reference-to-video";
+  if (refCount === 1) return "image-to-video";
+  return "text-to-video";
+}
+export function clampVideoDurationUI(duration: number, mode: string): number {
+  return mode === "reference-to-video" ? Math.min(duration, MAX_REF2V_DURATION_UI) : duration;
+}
```
(`VideoControlsPanel` and `runVideoGenerate` import `deriveVideoModeUI` /
`clampVideoDurationUI` from `../lib/imageModels`; the backend route remains the
authoritative clamp.)

#### B3. MODIFY `ui/src/components/ImageModelSelect.tsx`
- Read `videoModelSelected` + `selectVideoModel` from store.
- Trigger label: show `grok (v)` when video selected (else `current.shortLabel`).
- Append a **video** group after the image-model group (sidebar menu):
```diff
+            <div className="image-model-select__section" role="group" aria-label={t("sidebar.videoModelLabel")}>
+              <div className="image-model-select__section-title">{t("sidebar.videoModelLabel")}</div>
+              {VIDEO_MODEL_OPTIONS.map((option) => (
+                <button key={option.value} type="button"
+                  className={`image-model-select__item${videoModelSelected ? " is-active" : ""}`}
+                  role="menuitemradio" aria-checked={videoModelSelected} tabIndex={-1}
+                  onClick={() => { selectVideoModel(); setOpen(false); }}>
+                  <span>{option.shortLabel}</span><small>{t(option.fullLabelKey)}</small>
+                </button>
+              ))}
+            </div>
```
- Selecting an image model must clear `videoModelSelected`. Extend `setImageModel`
  to `set({ videoModelSelected: false })` — do it **once at function entry** so all
  three existing return branches (grok-image→provider grok / was-grok→provider oauth
  / plain) are covered, not just one (avoids "video mode won't clear" bug).
- a11y (N-7): the video group renders **alongside** the reasoning group when
  `provider !== "grok"`, so their `menuItemRefs` indices must not collide. Register
  video buttons at `menuItemRefs.current[modelOptions.length + index]` **and shift
  the reasoning group** to `menuItemRefs.current[modelOptions.length + VIDEO_MODEL_OPTIONS.length + index]`
  (matches DOM order: image → video → reasoning) so arrow-key nav reaches all items.

#### B4. NEW `ui/src/components/VideoControlsPanel.tsx`
Renders length / resolution / aspect-ratio using the existing `OptionGroup`.
Length max binds to ref count (≤10 when 2+ refs). Complete content:
```tsx
import { useAppStore } from "../store/useAppStore";
import { useI18n } from "../i18n";
import { OptionGroup } from "./OptionGroup";
import { deriveVideoModeUI, MAX_REF2V_DURATION_UI } from "../lib/imageModels";
import type { VideoResolutionUI } from "../types";

const RES_ITEMS = [
  { value: "480p" as const, label: "480p" },
  { value: "720p" as const, label: "720p" },
];
const ASPECT_ITEMS = ["auto", "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"].map((v) => ({ value: v, label: v }));
const DURATIONS = [3, 5, 8, 10, 12, 15];

export function VideoControlsPanel() {
  const { t } = useI18n();
  const refCount = useAppStore((s) => s.activeVideoRefCount());  // classic refs, or focused node's refs in node mode (§C1)
  const duration = useAppStore((s) => s.videoDuration);
  const setDuration = useAppStore((s) => s.setVideoDuration);
  const resolution = useAppStore((s) => s.videoResolution);
  const setResolution = useAppStore((s) => s.setVideoResolution);
  const aspect = useAppStore((s) => s.videoAspectRatio);
  const setAspect = useAppStore((s) => s.setVideoAspectRatio);
  const maxDuration = refCount >= 2 ? MAX_REF2V_DURATION_UI : 15;
  const mode = deriveVideoModeUI(refCount);  // reuse helper (L1)

  return (
    <div className="right-panel-settings video-controls">
      <div className="provider-compat-note" role="note">
        <strong>{t("video.modeLabel")}</strong>
        <span>{t(`video.mode.${mode}`, { n: refCount })}</span>
      </div>
      <div className="option-group">
        <div className="section-title">{t("video.durationTitle")}</div>
        <div className="option-row">
          {DURATIONS.filter((d) => d <= maxDuration).map((d) => (
            <button key={d} type="button"
              className={`option-btn${duration === d ? " active" : ""}`}
              onClick={() => setDuration(d)}>{d}s</button>
          ))}
        </div>
      </div>
      <OptionGroup<VideoResolutionUI> title={t("video.resolutionTitle")} items={RES_ITEMS} value={resolution} onChange={setResolution} />
      <OptionGroup<string> title={t("video.aspectTitle")} items={ASPECT_ITEMS} value={aspect} onChange={setAspect} />
    </div>
  );
}
```

#### B5. MODIFY `ui/src/components/GenerationControlsPanel.tsx`
Add the import and gate the **image-only** controls (incl. `CountPicker` +
`CostEstimate`, which are image-specific) behind the non-video branch. Video mode
shows only the provider + `VideoControlsPanel` (no Count/Cost — video returns a
single mp4 and image cost math does not apply).
```diff
+import { VideoControlsPanel } from "./VideoControlsPanel";
   ...
+  const videoModelSelected = useAppStore((s) => s.videoModelSelected);
   return (
     <div className="right-panel-settings" role="tabpanel">
       <ProviderSelect allowGrok />
-      { /* existing quality / SizePicker / format / moderation / multimode */ }
-      <CountPicker />
-      <CostEstimate />
+      {videoModelSelected ? (
+        <VideoControlsPanel />
+      ) : (
+        <>
+          { /* existing quality / SizePicker / format / moderation / multimode */ }
+          <CountPicker />
+          <CostEstimate />
+        </>
+      )}
     </div>
   );
```
No change to `CountPicker.tsx` / `CostEstimate.tsx` themselves — they are simply
not rendered in video mode, so count is effectively 1 (server `runVideoGenerate`
sends no `count`). (Removes the earlier dangling "see B6" note.)

### C. UI — generate routing + progress (store)

#### C1. MODIFY `ui/src/store/useAppStore.ts`
- New state + setters + selector:
```diff
+  videoModelSelected: boolean;
+  videoDuration: number;            // default 5
+  videoResolution: "480p" | "720p"; // default 480p
+  videoAspectRatio: string;         // default "auto"
+  videoProgress: number | null;     // 0..1 during generation, null otherwise
+  selectVideoModel: () => void;     // sets videoModelSelected=true, provider="grok"
+  setVideoDuration: (n: number) => void;
+  setVideoResolution: (r: "480p" | "720p") => void;
+  setVideoAspectRatio: (a: string) => void;
+  activeVideoRefCount: () => number; // node refs when a node is focused (node mode), else classic referenceImages.length
+  runVideoGenerate: (nodeId?: ClientNodeId) => Promise<void>;
```
- `selectVideoModel`: `set({ videoModelSelected: true })`; if `provider !== "grok"` call `get().setProvider("grok")`.
- Extend existing `setImageModel` to also `set({ videoModelSelected: false })`.
- `activeVideoRefCount()`: uses the **real** store shape (there is no `nodes` /
  `focusedNodeId`; selection is multi-select via `getSelectedNodeIds`):
```ts
activeVideoRefCount: () => {
  const s = get();
  if (s.uiMode === "node") {
    const id = getSelectedNodeIds(s.graphNodes)[0];           // rule: first selected node
    const node = s.graphNodes.find((n) => n.id === id);
    return node?.data.referenceImages?.length ?? 0;
  }
  return s.referenceImages.length;
},
```
  Import `getSelectedNodeIds` from `../lib/nodeSelection`. Multi-select rule:
  **first selected node** drives the panel preview; the actual generate uses the
  node passed to `runVideoGenerate` (below).
- Refs are gathered **inline inside `runVideoGenerate`** (see snippet) — node refs
  from `node.data.referenceImages` (FlowNode keyed by `n.id === nodeId`), else classic
  `get().referenceImages`. No separate module-local helper (avoids `get()` out of
  scope, N-2). There are **no filenames** in the store — refs are data-URLs, so I2V
  sends `sourceImage` (data-URL), not `sourceFilename` (C1-c).
- `runVideoGenerate(nodeId?)`: collect refs from the same source as the count
  (classic `referenceImages` / `referenceFilenames`, or the node's refs), compute
  `mode = deriveVideoMode(refs.length)` client-side for the clamp, then:
```ts
const node = nodeId ? get().graphNodes.find((n) => n.id === nodeId) : null;
const refs = node ? (node.data.referenceImages ?? []) : get().referenceImages;  // data-URLs, inline (N-2)
const mode = deriveVideoModeUI(refs.length);   // from ../lib/imageModels
const prompt = node ? node.data.prompt.trim()  // H1: node mode uses the node's own prompt
                    : composePrompt(get().prompt, get().insertedPrompts);  // classic composer
set({ videoProgress: 0 });
get().startInFlightPolling();   // N-3: ensure the 1.5s poller runs to pick up the finished mp4
try {
  await postVideoGenerateStream(
    { prompt,
      referenceImages: refs.length >= 2 ? refs : undefined,
      sourceImage:    refs.length === 1 ? refs[0] : undefined,
      duration: clampVideoDurationUI(get().videoDuration, mode),  // belt-and-suspenders; route re-clamps
      resolution: get().videoResolution, aspectRatio: get().videoAspectRatio,
      sessionId: get().activeSessionId, clientNodeId: nodeId ?? null },  // N-1: activeSessionId (no sessionId field)
    { onProgress: ({ progress }) => set({ videoProgress: progress ?? null }) },
  );
} finally { set({ videoProgress: null }); }
```
  Imports for the store: `postVideoGenerateStream` from `../lib/api` (M2 — store
  currently imports `postMultimodeGenerateStream` only), and `deriveVideoModeUI` /
  `clampVideoDurationUI` from `../lib/imageModels` (§B2). Refs are gathered **inline**
  (no module-local `get()` helper). No `referenceFilenames` — the store has none;
  data-URLs carry the payload and the route's `resolveSourceImage` accepts
  base64/data-URL. `startInFlightPolling()` (already a store action, called by
  `runGenerate`/`runGenerateNodeInPlace`) guarantees the finished mp4 is fetched
  into history.
- **Branch placement (avoid regression):**
  - `generate()` (classic, **no args**): after the existing prompt-empty guard,
    `if (get().videoModelSelected) return get().runVideoGenerate();` (no nodeId).
  - `generateNode(clientId)` (node entry called by `ImageNode.onGenerate`): branch
    **after the node prompt-empty guard, before `getCustomSizeConfirmation`** — so an
    empty node prompt still shows the toast, and the image-only custom-size modal does
    not intercept video:
    `if (get().videoModelSelected) return get().runVideoGenerate(clientId);`.
    (`runGenerateNode`/`runGenerateNodeInPlace` thus never see video.)
  - `runGenerateNodeInPlace` / variation paths: **video has no in-place/variation
    semantics** — when `videoModelSelected`, the node toolbar hides those buttons
    (belt-and-suspenders early return). Only first-generate routes to video.
- Count is not forced in state; the UI simply omits `CountPicker` in video mode
  (B5) and `runVideoGenerate` sends no count.

#### C2. MODIFY `ui/src/lib/api.ts`
```diff
 export type VideoGenerateRequest = {
   prompt: string; provider?: "grok"; model?: string;
-  mode?: "text-to-video" | "image-to-video";
+  mode?: "text-to-video" | "image-to-video" | "reference-to-video";
   sourceImage?: string; sourceFilename?: string;
+  referenceImages?: string[]; referenceFilenames?: string[];
   duration?: number; resolution?: string; aspectRatio?: string;
   sessionId?: string | null; clientNodeId?: string | null; clientRequestId?: string;
 };
```

#### C3. MODIFY `ui/src/components/Canvas.tsx` (+ `canvas-mode/CanvasModeWorkspace.tsx`)
- Surface `videoProgress` as a numeric % on the existing `.progress-bar`
  (e.g. width = `${videoProgress*100}%` + a `{Math.round(videoProgress*100)}%`
  label) when `videoProgress != null`.
- Note: the current `.progress-bar` is a **self-closing** `<div>` (Canvas.tsx:180).
  To host the `%` label child, convert it to a container (`<div class="progress-bar">
  <span class="progress-bar__pct">…</span></div>`) — keep the `active` class logic.

### D. Node mode

#### D1. MODIFY `ui/src/components/ImageNode.tsx`
- Node already owns `refs` (cap `MAX_NODE_REFS = 5`). When `videoModelSelected`,
  `onGenerate` routes via `generateNode(clientId)` → (C1 branch) →
  `runVideoGenerate(clientId)` (N-4: branch lives in `generateNode`, not
  `runGenerateNode`, so batch/variation paths stay image-only). The node's own refs
  supply count → mode.
- `runVideoGenerate(nodeId)` collects refs **inline** from the node
  (`graphNodes.find(n => n.id === nodeId)?.data.referenceImages`) in node mode, and
  `activeVideoRefCount()` mirrors the same source, so `VideoControlsPanel`'s mode
  hint/clamp matches what is sent (fixes the classic-vs-node ref mismatch).
- Hide the node's in-place re-generate / variation buttons when
  `videoModelSelected` (video = first-generate only); show the `(v)`/progress
  affordance inline (reuse `videoProgress`).

### E. Docs / version / site

| File | Change |
|---|---|
| `package.json`, `package-lock.json` | version `1.1.15` → `1.2.0` |
| `README.md:76` | flip "not shipped in 1.1.15" → "shipped in 1.2.0" |
| `docs/README.ko.md:65` | same (KO) |
| `docs/API.md:23` + body | document `POST /api/video/generate` (referenceImages[], mode derivation, ref2v ≤7/≤10s, error codes) |
| `docs/CLI.md` | note video scope (no CLI entry this round) |
| `site/src/pages/docs/concepts/providers.astro` (+`/ko/`) | flip image-only notice; describe video |
| `site/src/pages/docs/reference/api.astro` (+`/ko/`) | add `/api/video/generate` |
| `site/src/i18n/strings.ts` | npm badge `v1.1.15` → `v1.2.0` (both occurrences) |
| `structure/03-server-api.md`, `04-frontend-architecture.md`, `00/01/02/06` snapshots | record video surface + 1.2.0 |
| `devlog/_plan/260531_grok-video-i2v-ship/05_qa-gate.md` | add ref2v live-smoke rows |

### F. i18n + CSS
- `ui/src/i18n/en.json` + `ko.json`: `settings.videoModel.grokImagine`,
  `sidebar.videoModelLabel`, `video.modeLabel`, `video.mode.*`,
  `video.durationTitle`, `video.resolutionTitle`, `video.aspectTitle`,
  progress/toast keys.
- ⚠️ Verify `useI18n().t` supports `{ n }` interpolation before using
  `t("video.mode.*", { n })`; the existing `t("toast.animateProgress", { n })`
  call (ResultActions.tsx:64) proves param interpolation is supported — mirror it.
- `ui/src/index.css`: `.video-controls` reuses `.option-group/.option-btn`;
  add `.progress-bar__pct` label style.

### G. Tests (success gate)
- NEW `tests/grokVideoRef2v.test.ts`: payload shape (reference_images branch),
  `deriveVideoMode`, `clampVideoDuration`, ref count > 7 → `GROK_VIDEO_REF_TOO_MANY`,
  ref2v + image mutual-exclusion.
- Extend `tests/videoRoute.test.ts`: POST with 2–3 referenceFilenames → ref2v.
- UI contract test (mirrors existing `tests/*-contract.test.js`): selecting video
  model sets provider grok + count 1; duration clamp ≤10 when refs≥2.

---

## Files summary

NEW (2): `ui/src/components/VideoControlsPanel.tsx`, `tests/grokVideoRef2v.test.ts`
MODIFY backend (3): `lib/imageModels.ts`, `lib/grokVideoAdapter.ts`, `routes/video.ts`
MODIFY UI (9): `ui/src/types.ts`, `ui/src/lib/imageModels.ts`, `ui/src/lib/api.ts`,
`ui/src/components/ImageModelSelect.tsx`, `GenerationControlsPanel.tsx`,
`Canvas.tsx`, `canvas-mode/CanvasModeWorkspace.tsx`, `ImageNode.tsx`,
`ui/src/store/useAppStore.ts`
MODIFY i18n/css (3): `ui/src/i18n/en.json`, `ko.json`, `ui/src/index.css`
MODIFY docs/version (≈12): package(+lock), README, docs/README.ko, docs/API,
docs/CLI, 4 site pages, site/i18n strings, structure/* , 05_qa-gate.md
MODIFY tests (1): `tests/videoRoute.test.ts`

No DELETE. No new source-of-truth folder (reuses existing devlog lane).

## Completion gate (must all be green)
1. Static: `npm run typecheck`, `typecheck:tests`, ui `tsc -b`, `build:server`, `build:cli`, `ui:build`, `git diff --check`.
2. Unit/contract: full `npm test` (≥ prior 826 + new) + targeted video suite.
3. Live smoke (progrok 127.0.0.1): ref2v with 2+ images → valid mp4 + reference preservation; I2V + T2V regression.
4. Browser (CDP): Classic + Node compose→video, progress % renders, no console errors; Animate still works.
5. Employee PASS: 료 (backend/adapter/route), 니지카 (UI/UX), 키타 (data/smoke).
6. Site static build green.
7. Bump 1.2.0 + flip 8 notices + docs/site updated.
8. `git push -u origin feat/grok-video-i2v` (NO main merge).
