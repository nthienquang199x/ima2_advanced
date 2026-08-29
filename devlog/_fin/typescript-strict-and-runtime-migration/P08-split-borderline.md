# P08 — (Optional) Split borderline files

**Goal:** Split 6 files in the 350–460 LOC range to improve readability and bound strict-mode blast radius. Optional — none violates the 500-line rule.

**Effort:** M (one PR per file or batched 2–3)
**Owner:** Boss + sub-agent (`claude-opus-4.7`).
**Depends on:** P00. Independent of strict work; landing earlier reduces P05/P06 per-file diff sizes.

---

## Why

| File | LOC | Justification |
|---|---|---|
| `routes/nodes.ts` | 455 | One giant POST handler ~380 lines |
| `bin/ima2.ts` | 444 | Argument dispatch + ~10 inline command bodies |
| `bin/commands/prompt.ts` | 421 | 21 sub-handlers in one file |
| `routes/prompts.ts` | 379 | 10 endpoints; pairs with 46 strictNull errors |
| `routes/promptImport.ts` | 354 | 10 endpoints + helpers; 46 noImplicitAny errors |
| `lib/responsesImageAdapter.ts` | 352 | 3 exports + 240 lines of shared helpers |

None exceeds 500 LOC, but each shows directional growth. Splitting is **optional**: skip if other phases are time-pressured. **Recommended order**: tackle the file that has the most strict-mode errors first (`routes/promptImport.ts` 46 noImplicitAny → split before P06b).

## Scope per file

### `routes/nodes.ts` (455)
**NEW:**
- `routes/nodes/helpers.ts` — `validateModeration`, `wantsSse`, `writeSse`, `writeNodeError`, `dataUrlFromB64` (~50 LOC)
- `routes/nodes/generate.ts` — POST handler body extracted to `handleNodeGenerate(req, res, ctx)` (~380 LOC)
- `routes/nodes/get.ts` — GET handler (~30 LOC)

**MODIFY:**
- `routes/nodes.ts` — `registerNodeRoutes` becomes a 25-line wire-up file.

### `bin/ima2.ts` (444)
**NEW (note: bin/ima2.ts is the entrypoint — keep it small):**
- `bin/lib/configFile.ts` — `loadConfig`, `saveConfig`, `loadAdvertisement`, `advertisedServerUrl`, `CONFIG_DIR/FILE`, `LEGACY_CONFIG_FILE` (~70 LOC)
- `bin/commands/setup.ts` — `setup` (~60 LOC)
- `bin/commands/serve.ts` — `serve` (~60 LOC; **this is where the `serverPath` resolution lives — preserve carefully for P11**)
- `bin/commands/status.ts` — `showStatus` (~40 LOC)
- `bin/commands/doctor.ts` — `doctor`, `missingRuntimeDeps` (~90 LOC)
- `bin/lib/openBrowser.ts` — `openBrowser` (~10 LOC)
- `bin/lib/help.ts` — `showHelp` (~40 LOC)

**MODIFY:**
- `bin/ima2.ts` — shebang + arg parsing + dispatch only (~80 LOC)

> **Sequencing trap:** P11 (dist/ outDir) edits `bin/ima2.ts:177` `serverPath` resolution. If P08-bin runs first, that logic moves to `bin/commands/serve.ts`. P11 must be aware. **Recommend P08-bin land before P11**, or skip P08-bin and consolidate the two changes.

### `bin/commands/prompt.ts` (421)
**NEW:**
- `bin/commands/prompt/index.ts` — dispatcher (~80 LOC)
- `bin/commands/prompt/crud.ts` — `lsSub, showSub, createSub, editSub, rmSub, favoriteSub, exportSub` (~140 LOC)
- `bin/commands/prompt/folders.ts` — folder ops (~80 LOC)
- `bin/commands/prompt/import.ts` — `importSub` and friends (~160 LOC)

**MODIFY:**
- `bin/commands/prompt.ts` → barrel `export { default } from "./prompt/index.ts"` for back-compat with `bin/ima2.ts` import.

### `routes/prompts.ts` (379)
**NEW:**
- `routes/prompts/crud.ts` — CRUD endpoints (~190 LOC)
- `routes/prompts/portability.ts` — import/export (~95 LOC)
- `routes/prompts/folders.ts` — folder endpoints (~80 LOC)

**MODIFY:**
- `routes/prompts.ts` → `registerPromptRoutes` calls three sub-registrars (~20 LOC).

### `routes/promptImport.ts` (354)
**NEW:**
- `routes/promptImport/helpers.ts` — limits, error helpers, ID gen, normalizers, commit logic (~140 LOC)
- `routes/promptImport/preview.ts` — preview / folder-files / folder-preview (~120 LOC)
- `routes/promptImport/discovery.ts` — discovery / curated routes (~80 LOC)

**MODIFY:**
- `routes/promptImport.ts` → barrel + `commit` route (~30 LOC).

### `lib/responsesImageAdapter.ts` (352)
**NEW:**
- `lib/responsesImageAdapter/shared.ts` — request building, model resolution, references-to-content, error wrappers (~240 LOC)
- `lib/responsesImageAdapter/generate.ts` — `generateViaResponses`, `generateMultimodeViaResponses` (~80 LOC)
- `lib/responsesImageAdapter/edit.ts` — `editViaResponses` (~50 LOC)

**MODIFY:**
- `lib/responsesImageAdapter.ts` → barrel re-export (~10 LOC).

## Universal rules for splits

1. **Public path stable**: every file that other modules currently import from MUST continue to export the same symbols (use barrel re-exports).
2. **No-op semantics**: each split PR is structural. Behavior changes go in a separate PR.
3. **Symbol diff check** (mandatory pre-merge):
   ```bash
   before=$(git show HEAD:<file> | grep -oE '^export [^=]*' | sort -u)
   after=$(grep -hoE '^export [^=]*' <file>* <new-files>* | sort -u)
   diff <(echo "$before") <(echo "$after")
   ```
4. **Tests run unchanged.** Any test failure means the split is not no-op.

## GPT Pro verification (recommended for `routes/nodes.ts` split — biggest function-extraction)

Paste before/after `registerNodeRoutes` and ask:
> "Does this function-extraction preserve handler semantics? Are there closure variables that became stale after extraction?"

## Verify

```bash
npm run typecheck
npm test                # 539/539
npm run build:server
npm run build:cli
ls <split-dir>/*.js     # confirm emit
```

## Risk

- **Medium.** Function-extraction (`routes/nodes.ts`) carries closure-variable risk. The other splits are pure module re-organization.
- **Trap:** moving Express handler body out without preserving the `req` / `res` references. Pattern: extract to `async function handleNodeGenerate(req: Request, res: Response, ctx: RuntimeContext) { ... }` and have the route definition `app.post("/api/node/generate", (req, res) => handleNodeGenerate(req, res, ctx))`.

## Rollback

Per file. Each split is its own PR.

## Exit criteria (per file)

- [ ] Original file is < 100 LOC (barrel only) OR contains only the registrar pattern.
- [ ] All previously-exported symbols are reachable through original import path.
- [ ] `npm test` 539/539.
- [ ] `npm run typecheck` green.
- [ ] Handler smoke for routes (curl POST /api/node/generate, /api/prompts, etc.) returns same shape as before.
