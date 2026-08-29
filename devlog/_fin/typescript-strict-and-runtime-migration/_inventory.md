# TypeScript Migration Inventory — `ima2-gen`

Repo root: `/Users/jun/Developer/new/700_projects/ima2-gen`
TS source: 14,373 LOC across `lib/` + `routes/` + `bin/` (+ `server.ts`, `config.ts`).
Current TS: `tsconfig.json` has `strict:false`, `noImplicitAny:false`, `strictNullChecks:false`, `noUnusedLocals:false`, `noUnusedParameters:false`. `noImplicitOverride` and `noFallthroughCasesInSwitch` are already on.

---

## 1. Strict-mode pain points

Counts are total compiler diagnostics (one error = one line in tsc output). Each flag was enabled in isolation against `tsconfig.json` via `npx tsc --noEmit -p tsconfig.json --<flag>`.

| Flag | Errors | Status / notes |
|---|---|---|
| `noImplicitAny` | **1,205** | Largest single source of breakage. |
| `strictNullChecks` | **291** | Manageable. |
| `strictFunctionTypes` | **0** | Already clean — turn on now. |
| `strictPropertyInitialization` | n/a | Requires `strictNullChecks` first (TS5052). Effectively 0 once SNC is enabled (no class-field heavy code). |
| `useUnknownInCatchVariables` | **152** | Highly localized to `err.message/.code/.status` access in routes + bin commands. |
| `noUnusedLocals` | **5** | Trivial cleanup. |
| `noUnusedParameters` | **8** | Trivial cleanup (mostly `req`, `ctx`, `scope`). |
| `--strict` (CLI) | (152 reported, but masked) | CLI `--strict` is suppressed by explicit `false` overrides in `tsconfig.json`; real "all-on" is roughly **noImplicitAny + strictNullChecks + useUnknownInCatchVariables ≈ 1,648 errors** (overlap small). |

### Top-10 worst offender files

**`noImplicitAny` (top 15 shown):**

| Errors | File |
|---|---|
| 60 | `lib/oauthProxy.ts` |
| 46 | `routes/promptImport.ts` |
| 43 | `lib/responsesImageAdapter.ts` |
| 40 | `lib/promptImport/githubFolder.ts` |
| 37 | `routes/cardNews.ts` |
| 37 | `lib/promptImport/parsePromptCandidates.ts` |
| 30 | `routes/prompts.ts` |
| 29 | `lib/historyList.ts` |
| 29 | `lib/cardNewsPlannerSchema.ts` |
| 26 | `lib/sessionStore.ts` |
| 26 | `bin/commands/prompt.ts` |
| 25 | `lib/logger.ts` |
| 24 | `lib/promptImport/promptIndex.ts` |
| 24 | `lib/cardNewsPlanner.ts` |
| 23 | `routes/sessions.ts` |

**`strictNullChecks` top 10:**

| Errors | File |
|---|---|
| 46 | `routes/prompts.ts` |
| 22 | `lib/sessionStore.ts` |
| 17 | `routes/promptImport.ts` |
| 16 | `lib/promptImport/githubDiscovery.ts` |
| 12 | `lib/cardNewsPlannerSchema.ts` |
| 12 | `lib/cardNewsGenerator.ts` |
| 11 | `routes/generate.ts` |
| 11 | `lib/inflight.ts` |
| 10 | `lib/refs.ts` |
| 10 | `lib/promptImport/githubFolder.ts` |

**`useUnknownInCatchVariables` top 10** (all are `err.message/.code/.status` patterns, fix with one helper or `instanceof Error`):

| Errors | File |
|---|---|
| 16 | `routes/sessions.ts` |
| 16 | `routes/prompts.ts` |
| 12 | `routes/generate.ts` |
| 11 | `routes/nodes.ts` |
| 10 | `routes/history.ts` |
| 7  | `routes/multimode.ts` |
| 6  | `routes/canvasVersions.ts` |
| 6  | `lib/historyList.ts` |
| 6  | `bin/commands/ps.ts` |
| 6  | `bin/commands/gen.ts` |

**`noUnusedLocals` (5 total)**: `bin/commands/multimode.ts:1`, `bin/ima2.ts:8,17`, `bin/lib/files.ts:2`.
**`noUnusedParameters` (8 total)**: `lib/oauthProxy.ts:219` (×2), `lib/promptImport/parsePromptCandidates.ts:95`, `lib/responsesImageAdapter.ts:62`, `routes/promptImport.ts:221`, `routes/prompts.ts:12,232,260`.

### Recommended phased rollout

1. **Phase A (free wins, today):** turn on `strictFunctionTypes`, `noUnusedLocals`, `noUnusedParameters` — total 13 trivial fixes.
2. **Phase B (mechanical, 1–2 days):** `useUnknownInCatchVariables` — 152 errors all of one shape; one `errInfo()` helper covers it.
3. **Phase C (medium, ~1 week):** `strictNullChecks` (+ `strictPropertyInitialization` for free) — 291 errors clustered in 10 files.
4. **Phase D (large, 1–2 weeks):** `noImplicitAny` — 1,205 errors. Tackle by directory: `bin/` first (smaller surface), then `routes/`, then `lib/oauthProxy.ts` + `lib/responsesImageAdapter.ts` last (these contribute >100 alone).
5. **Phase E:** flip `strict: true` and remove individual overrides.

---

## 2. Test-file categorization

123 `.test.js` files in `tests/` (+ `package-install-smoke.mjs`). Heuristic: **integration** = imports `express` or `../server`; **runtime** = imports `../{lib,routes,bin}/…` only; **contract** = uses `readFileSync` to grep TS source; **other** = neither (often spawns CLI subprocess via `tsx`, or pure-JS unit tests).

Aggregate:

| Category | Files | Total LOC | Avg LOC | Convert priority |
|---|---|---|---|---|
| contract | 76 | 5,881 | 77 | **LOW** — string regex over source, gives no type safety |
| runtime  | 24 | 2,738 | 114 | **HIGH** — direct lib imports, would catch type drift |
| integration | 14 | 2,047 | 146 | **HIGH** — exercises real routes + lib together |
| other | 9 | 923 | 103 | MED — mostly CLI spawn-subprocess + a couple pure unit tests |

Note: tests already use `import "../lib/foo.ts"` with `--import tsx`, so `.ts` migration is mostly a rename + minor type sprinkles. Conversion gain ≈ catching call-shape drift in lib/routes APIs.

A representative table (full machine-generated list available; here the high-value subset — runtime + integration files):

| File | Cat | LOC | Notes |
|---|---|---|---|
| api-provider-parity.test.js | integration | 264 | imports `routes/{generate,edit,multimode,nodes}.ts` + express |
| card-news-contract.test.js | integration | 478 | imports `lib/cardNews*.ts`, `routes/index.ts`, express |
| node-streaming-sse.test.js | integration | 151 | express + routes/nodes |
| oauth-proxy-error-safety.test.js | integration | 186 | express + lib/oauthProxy |
| request-logging.test.js | integration | 157 | express + lib/logger |
| image-metadata-route.test.js | integration | 111 | express + routes/imageImport |
| inflight.test.js | runtime | 111 | lib/inflight |
| inflight-persistence.test.js | runtime | 68 | lib/inflight |
| storage-migration.test.js | runtime | 248 | lib/storageMigration |
| logging.test.js | runtime | 109 | lib/logger |
| billing-source.test.js | runtime | 108 | lib/* |
| star-prompt.test.js | runtime | 77 | lib/promptStore |
| node-route-refs.test.js | runtime | 71 | routes/nodes |
| prompt-fidelity.test.js | runtime | 82 | lib/oauthProxy prompts |
| error-classify.test.js | runtime | 72 | lib/errors |
| size-presets.test.js | runtime | 57 | lib |
| reference-image-compress.test.js | runtime | 52 | lib/refs |
| oauth-normalize.test.js | runtime | 51 | lib/oauthProxy helpers |
| runtime-ports.test.js | runtime | 51 | lib/runtimePorts |
| image-metadata-xmp.test.js | runtime | 74 | lib/imageMetadataStore |
| image-model.test.js | runtime | 89 | lib/imageModel |
| node-validation-error-contract.test.js | runtime | 102 | routes/nodes |
| generate-route-validation-error.test.js | runtime | 75 | routes/generate |
| local-import-contract.test.js | runtime | 98 | lib/promptImport |
| node-pending-recovery-contract.test.js | runtime | 72 | lib |
| node-parent-source-contract.test.js | runtime | 69 | lib |
| refs-size.test.js | runtime | 78 | lib/refs |
| history-tombstone.test.js | runtime | 160 | lib/historyList |
| history-metadata-fallback.test.js | runtime | 82 | lib/historyList |
| session-conflict.test.js | runtime | 83 | lib/sessionStore |
| style-sheet.test.js | runtime | 88 | lib/styleSheet |
| generation-errors.test.js | runtime | 110 | lib/oauthProxy |

Sample contract-style files (NOT recommended for conversion — keep as `.js`): `*-contract.test.js`, `cli-lib.test.js`, `bin.test.js`, `comfyui-custom-node-contract.test.js`, all `canvas-*-contract.test.js`, `gallery-*-contract.test.js`, `prompt-*-ui-contract.test.js`, etc.

`tests/package-install-smoke.mjs` and `tests/*.mjs` (1) — keep as `.mjs`.

### Recommendation
- Convert ~38 files (24 runtime + 14 integration ≈ 4,785 LOC).
- Defer ~76 contract tests; they read `*.ts` source as text and gain nothing from TS.

---

## 3. Large-file split candidates (>500 lines)

Only **`lib/oauthProxy.ts`** exceeds 500 lines (1,003). The other six in the question are 350–460 lines — borderline; splitting can still help readability + strict rollout but is optional. Sizes confirmed:

```
1003 lib/oauthProxy.ts
 455 routes/nodes.ts
 444 bin/ima2.ts
 421 bin/commands/prompt.ts
 379 routes/prompts.ts
 354 routes/promptImport.ts
 352 lib/responsesImageAdapter.ts
```

### `lib/oauthProxy.ts` (1003) — **must split**

Exports: `REAL_PERSON_RESEARCH_DIRECTIVE`, `AUTO_PROMPT_FIDELITY_SUFFIX`, `DIRECT_PROMPT_FIDELITY_SUFFIX`, `PROMPT_FIDELITY_SUFFIX`, `GENERATE_DEVELOPER_PROMPT`, `GENERATE_NO_SEARCH_DEVELOPER_PROMPT`, `EDIT_DEVELOPER_PROMPT`, `EDIT_NO_SEARCH_DEVELOPER_PROMPT`, `buildUserTextPrompt`, `buildMultimodeSequencePrompt`, `buildEditTextPrompt`, `buildEditResearchTextPrompt`, `waitForOAuthReady`, `parseOpenAIErrorBody`, `generateViaOAuth`, `generateMultimodeViaOAuth`, `editViaOAuth`.

Proposed split (re-export from `lib/oauthProxy.ts` for back-compat):

| New file | Contents | LOC est. |
|---|---|---|
| `lib/oauthProxy/prompts.ts` | All `*_DEVELOPER_PROMPT`, `*_FIDELITY_SUFFIX`, `REAL_PERSON_RESEARCH_DIRECTIVE`, `buildUserTextPrompt`, `buildMultimodeSequencePrompt`, `buildEditTextPrompt`, `buildEditResearchTextPrompt` (lines 38–135) | ~140 |
| `lib/oauthProxy/errors.ts` | `makeOAuthError`, `parseOpenAIErrorBody`, `normalizedOAuthCode`, `throwOAuthHttpError`, `isAbortError`, `throwOAuthTimeoutError`, `createOAuthGenerationTimeout` | ~150 |
| `lib/oauthProxy/sse.ts` | `extractSseData`, `extractPartialImage`, `readImageStream`, `readMultimodeImageStream`, `summarizeEventTypes` | ~280 |
| `lib/oauthProxy/refs.ts` | `supportedImageMime`, `normalizeReferenceForOAuth` | ~40 |
| `lib/oauthProxy/context.ts` | `getOAuthUrl`, `getOAuthGenerationTimeoutMs`, `waitForOAuthReady`, `resolveReasoningEffort`, `resolveWebSearchEnabled`, `buildImageTools`, `fetchOAuth` | ~120 |
| `lib/oauthProxy/generate.ts` | `generateViaOAuth`, `generateMultimodeViaOAuth` | ~330 |
| `lib/oauthProxy/edit.ts` | `editViaOAuth` | ~150 |
| `lib/oauthProxy.ts` | thin barrel re-exporting all of the above (preserves existing import paths) | ~30 |

### `routes/nodes.ts` (455) — single export `registerNodeRoutes`, two routes (`POST /api/node/generate` lines 59–439, `GET /api/node/:nodeId` 440–455)

Split:
- `routes/nodes/helpers.ts` — `validateModeration`, `wantsSse`, `writeSse`, `writeNodeError`, `dataUrlFromB64` (~50)
- `routes/nodes/generate.ts` — POST handler body extracted to `handleNodeGenerate(req,res,ctx)` (~380)
- `routes/nodes/get.ts` — GET handler (~30)
- `routes/nodes.ts` — `registerNodeRoutes` wires the three (~25)

### `bin/ima2.ts` (444) — CLI entrypoint, no exports; one giant if/else dispatch

Split (dispatch already delegates most subcommands to `bin/commands/*`):
- `bin/ima2.ts` — shebang + arg parsing + dispatch only (~80)
- `bin/lib/configFile.ts` — `loadConfig`, `saveConfig`, `loadAdvertisement`, `advertisedServerUrl`, `CONFIG_DIR/FILE`, `LEGACY_CONFIG_FILE` (~70)
- `bin/commands/setup.ts` — `setup` (~60)
- `bin/commands/serve.ts` — `serve` (~60)
- `bin/commands/status.ts` — `showStatus` (~40)
- `bin/commands/doctor.ts` — `doctor`, `missingRuntimeDeps` (~90)
- `bin/lib/openBrowser.ts` — `openBrowser` (~10)
- `bin/lib/help.ts` — `showHelp` (~40)

### `bin/commands/prompt.ts` (421) — one default export `promptCmd`, 21 internal `*Sub` handlers

Split by subcommand cluster:
- `bin/commands/prompt/index.ts` — dispatcher (`promptCmd`, `getServer`, `handle`, `readLine`, `resolveText`) (~80)
- `bin/commands/prompt/crud.ts` — `lsSub`, `showSub`, `createSub`, `editSub`, `rmSub`, `favoriteSub`, `exportSub` (~140)
- `bin/commands/prompt/folders.ts` — `folderSub`, `folderLs`, `folderCreate`, `folderRename`, `folderRm` (~80)
- `bin/commands/prompt/import.ts` — `importSub`, `importSources`, `importRefresh`, `importCurated`, `importDiscovery`, `importFolder` (~160)

### `routes/prompts.ts` (379) — single export `registerPromptRoutes`, 10 endpoints

Split into route groups:
- `routes/prompts/crud.ts` — `GET/POST /api/prompts`, `GET/DELETE /api/prompts/:id`, `POST .../favorite` (~190)
- `routes/prompts/portability.ts` — `POST /api/prompts/import`, `GET /api/prompts/export` (~95)
- `routes/prompts/folders.ts` — `GET/POST /api/prompts/folders`, `DELETE /api/prompts/folders/:id` (~80)
- `routes/prompts.ts` — `registerPromptRoutes` calls three sub-registrars (~20)

### `routes/promptImport.ts` (354) — single export `registerPromptImportRoutes`, 10 endpoints + helpers

Split:
- `routes/promptImport/helpers.ts` — `promptImportLimits`, `sendPromptImportError`, `generateId`, `sourceFilename`, `normalizeLocalSource`, `normalizeFolderInput`, `assertCommitCandidateText`, `commitCandidates` (~140)
- `routes/promptImport/preview.ts` — `buildPreview`, `buildFolderFiles`, `buildFolderPreview`, plus the `preview`/`folder-files`/`folder-preview` routes (~120)
- `routes/promptImport/discovery.ts` — `discovery`, `discovery-search`, `discovery-review`, `curated-sources`, `curated-search`, `curated-refresh` routes (~80)
- `routes/promptImport.ts` — `registerPromptImportRoutes` thin barrel + `commit` route (~30)

### `lib/responsesImageAdapter.ts` (352) — three exports: `generateViaResponses`, `generateMultimodeViaResponses`, `editViaResponses`

Split:
- `lib/responsesImageAdapter/shared.ts` — request building, model resolution, references-to-content conversion, error wrappers (lines 1–241) (~240)
- `lib/responsesImageAdapter/generate.ts` — `generateViaResponses`, `generateMultimodeViaResponses` (~80)
- `lib/responsesImageAdapter/edit.ts` — `editViaResponses` (~50)
- `lib/responsesImageAdapter.ts` — barrel re-export (~10)

---

## 4. Build artifact layout — moving `outDir` to `dist/`

**Current state.** `tsconfig.build.json` and `tsconfig.bin.json` both set `outDir: "."` and `rootDir: "."`. The compiled `.js` lives next to each `.ts`:

- `bin/ima2.js`, `bin/commands/*.js`, `bin/lib/*.js`
- `lib/*.js`
- `routes/*.js`
- `server.js`, `config.js`

**Hard couplings to current layout (will break if you move to `dist/`):**

1. `package.json` `"bin": { "ima2": "./bin/ima2.js" }` — npm resolves `bin/ima2.js` at install time. Move → `dist/bin/ima2.js`.
2. `package.json` `"files"` whitelists `bin/`, `lib/`, `routes/`, `server.js`, `config.js`. Move → switch to `dist/`.
3. `package.json` `scripts.start` = `node bin/ima2.js serve`; `scripts.setup` = `node bin/ima2.js setup`.
4. `package.json` `lint:pkg` literally hard-codes `mustInclude=['bin/','lib/','routes/',...,'server.js']` → will fail.
5. `bin/ima2.ts:177` does `join(ROOT, "server.js")` and spawns Node on it — this is **the crucial runtime coupling**: the published CLI launches the server by path. If `server.js` moves to `dist/server.js`, this path needs updating (and it must still work both during `tsx`-based dev where `server.ts` exists, and in the published artifact where only the `.js` exists).
6. `scripts/dev.mjs:29` spawns `node --watch server.js`.
7. `scripts/fix-shebangs.mjs:26` hard-codes `join("bin","ima2.js")`.
8. `tests/cli-commands.test.js` runs `node --import tsx bin/ima2.ts` (uses `.ts` source, OK either way).
9. `.gitignore` already excludes the colocated artifacts (`/server.js`, `/config.js`, `/lib/**/*.js`, `/routes/**/*.js`, `/bin/ima2.js`, `/bin/commands/*.js`, `/bin/lib/*.js`) — moving to `dist/` actually simplifies this to a single `/dist/` entry.

**Pitfalls / migration checklist for `outDir: "dist/"`:**

- Update `package.json`: `bin.ima2 → ./dist/bin/ima2.js`; `files: ["dist/", "integrations/...", "ui/dist/", ...]`; `scripts.start → node dist/bin/ima2.js serve`; `scripts.setup → node dist/bin/ima2.js setup`; rewrite `lint:pkg` `mustInclude` list.
- Update `bin/ima2.ts:177` `serverPath` resolution: detect dev vs published (e.g., prefer `dist/server.js` if it exists, else `server.ts` via tsx).
- Update `scripts/dev.mjs` to either `tsx watch server.ts` (already exists as `dev:server`) or to `node --watch dist/server.js` after a build step.
- Update `scripts/fix-shebangs.mjs` `BIN_DIR` to `dist/bin`.
- Both `tsconfig.build.json` and `tsconfig.bin.json` currently `exclude: ["bin"]` and `include: ["bin/**/*.ts"]` respectively. With a single `outDir: "dist"`, you can collapse them into one tsconfig (`tsconfig.build.json`) if `rootDir` and emit roots align — currently kept separate so each project sees only its own files, but they overlap; with `dist/` you can keep them separate too, both writing into `dist/`.
- Note `package.json files[]` includes `server.ts` and `config.ts` — these are shipped as source. Decide whether to keep shipping `.ts` (for tsx-based dev usage by consumers) or drop. The published `bin/ima2.js` only references `server.js`, so `server.ts` in `files[]` is currently dead weight in the tarball.

**Pitfall summary:** the single highest-risk item is `bin/ima2.ts:177` (`join(ROOT, "server.js")`). Everything else is a config-string update.

---

## 5. Scripts inventory (`scripts/*.mjs`)

| Script | LOC | Complexity (1-5) | Convert to .ts? | Rationale |
|---|---|---|---|---|
| `scripts/dev.mjs` | 42 | 2 | **No** | Pure shell-style orchestration: `spawnSync npm run ui:build`, then `spawn node --watch server.js`. Zero domain types. Gain from `.ts` ≈ 0; cost = needing tsx/node-loader to run a script that currently runs with bare `node`. |
| `scripts/run-tests.mjs` | 22 | 1 | **No** | `readdirSync('tests') → spawn node --import tsx --test`. Trivial. Stays `.mjs`. |
| `scripts/fix-shebangs.mjs` | 30 | 2 | **No** | Walks `bin/` and prepends shebang to `bin/ima2.js`. Runs **after** tsc as a post-build hook — making it `.ts` would require yet another build step before build. Keep `.mjs`. |

**Recommendation:** leave all three as `.mjs`. Optional polish: add JSDoc `@type` comments + `// @ts-check` at top so tsc/IDE provide light checking without changing the build pipeline.

Also note `scripts/install-mac.sh`, `scripts/install-windows.ps1`, `scripts/release.sh`, `scripts/release-preview.sh` are shell/PowerShell — N/A.

---

## 6. CI workflow

`.github/workflows/ci.yml` (37 lines) — only file (the other is `pages.yml` for docs).

- Triggers: `push` to `main`, `pull_request` to `main`.
- Concurrency cancel-in-progress on same ref.
- Job `test` matrix: `os: [ubuntu-latest, windows-latest]`, `fail-fast: false`. **✅ Confirmed ubuntu+windows.**
- Node version: `'22'`. **✅ Confirmed Node 22.** No matrix across Node versions (single 22).
- Steps: `npm ci` → `npm --prefix ui install` → `npm --prefix ui run build` → **`npm test`** (timeout-minutes: 3) → `npm run lint:pkg` (ubuntu only).

**Missing steps** (gaps for migration):
- ❌ No `npm run typecheck` step. Strict-mode rollout is invisible to CI until added.
- ❌ No `npm run build:server` / `build:cli` step in CI. The compile is only validated indirectly by `prepublishOnly`.
- ❌ No artifact upload, no coverage.
- ❌ No `.test.ts` in matrix (tests are still `.test.js`).

**Recommendation:** add a `typecheck` step before `npm test` (fast, fails early). Add `build:server` + `build:cli` to ensure tsc emit succeeds on every PR; this is essential before flipping strict flags.

---

## 7. `any` / explicit-cast / suppression usage (`lib/` + `routes/` + `bin/`)

| Pattern | Total |
|---|---|
| `: any` | **222** |
| `as any` | **10** |
| `// @ts-ignore` | **0** |
| `// @ts-expect-error` | **0** |

**Top files by `: any`:**

| Count | File |
|---|---|
| 21 | `lib/oauthProxy.ts` |
| 14 | `bin/commands/prompt.ts` |
| 9  | `lib/storageMigration.ts` |
| 8  | `lib/cardNewsTemplateStore.ts` |
| 8  | `bin/commands/config.ts` |
| 7  | `lib/responsesImageAdapter.ts` |
| 7  | `lib/assetLifecycle.ts` |
| 7  | `bin/commands/node.ts` |
| 6  | `lib/promptImport/githubDiscovery.ts` |
| 6  | `lib/cardNewsPlannerClient.ts` |
| 6  | `lib/canvasVersionStore.ts` |
| 6  | `bin/lib/client.ts` |
| 6  | `bin/commands/session.ts` |
| 5  | `lib/styleSheet.ts` |
| 5  | `lib/nodeStore.ts` |

**Top files by `as any`:** `lib/runtimePorts.ts` (2), `lib/comfyBridge.ts` (2), `bin/commands/prompt.ts` (2), `routes/prompts.ts` (1), `routes/comfy.ts` (1), `lib/imageMetadataStore.ts` (1), `bin/lib/sse.ts` (1).

**Observation:** zero `@ts-ignore` / `@ts-expect-error` anywhere — that's clean. The `: any` annotations are the migration debt; many are deliberate `ctx: any = {}` defaults that would be the first target of a `RuntimeContext` interface.

---

## Phased plan synthesis (what the data says)

1. **Quick CI hardening** — add `npm run typecheck` + `npm run build:server` + `npm run build:cli` to `ci.yml`. Cost: 5 min. Catches all subsequent strict regressions automatically.
2. **Phase A strict (today):** enable `strictFunctionTypes`, `noUnusedLocals`, `noUnusedParameters` (13 errors total).
3. **Phase B catch-clause (1 PR):** introduce `function errInfo(e: unknown): { message?:string; code?:string; status?:number }` helper, replace ~50 sites, then enable `useUnknownInCatchVariables` (152 errors).
4. **Define `RuntimeContext`** (the `ctx: any = {}` pattern is everywhere — touching it unblocks ~80 of the `noImplicitAny` errors and ~half of `: any` annotations).
5. **Split `lib/oauthProxy.ts`** before tackling its 60 noImplicitAny + 21 `: any`. Splitting shrinks per-file blast radius for strict-mode PRs. The other 6 files are <500 LOC; defer.
6. **Phase C strictNullChecks** (291 errors, top 10 files cover ~150 of them).
7. **Phase D noImplicitAny** — directory-by-directory: `bin/` (~120 errors) → `routes/` (~250) → `lib/` non-OAuth (~400) → `lib/oauthProxy*` + `lib/responsesImageAdapter*` (~430) — total 1,205. Big effort; the only one that needs sustained calendar time.
8. **Test conversion** — convert ~38 high-value tests (24 runtime + 14 integration); skip 76 contract tests. Saves ~60% of the work for ~95% of the type-safety value.
9. **Artifact layout** — defer `dist/` move until after strict rollout (it touches different files and shouldn't be coupled to strict-mode PRs). When done, the critical fix is `bin/ima2.ts:177` `serverPath` resolution; everything else is config-string updates.
10. **Scripts** — leave `.mjs` as-is; add `// @ts-check` for lightweight checking.___BEGIN___COMMAND_DONE_MARKER___0
