# P07 — Test migration (`.test.js` → `.test.ts`, runtime + integration only)

**Goal:** Convert ~38 high-value tests (24 runtime + 14 integration) to `.test.ts`. Keep ~76 contract tests and 1 `.mjs` smoke as `.js`/`.mjs` — converting them adds zero type safety since they regex over source text.

**Effort:** M (2–3 PRs)
**Owner:** Boss orchestrates; sub-agent (`gpt-5.5`) does mechanical rename + minor type sprinkles.
**Depends on:** P00 (CI gate). Independent of strict flag work; can land in parallel with P05/P06.

---

## Why

| Category | Files | Convert? | Reason |
|---|---|---|---|
| **runtime** (imports `lib/routes/bin`) | 24 | ✅ | catches API drift between test and source |
| **integration** (express + routes + lib) | 14 | ✅ | end-to-end type safety on req/res shapes |
| **contract** (regex over TS source) | 76 | ❌ | no runtime imports → TS adds nothing |
| **other** (CLI subprocess spawn) | 9 | ❌ | spawns child processes, no type benefit |
| **smoke .mjs** | 1 (`package-install-smoke.mjs`) | ❌ | runs against published tarball without dev deps |

Full list of high-value files: see `_inventory.md` section 2.

## Scope

**RENAME (38 files, .test.js → .test.ts):**
- 24 runtime files: `inflight.test`, `inflight-persistence.test`, `storage-migration.test`, `logging.test`, `billing-source.test`, `star-prompt.test`, `node-route-refs.test`, `prompt-fidelity.test`, `error-classify.test`, `size-presets.test`, `reference-image-compress.test`, `oauth-normalize.test`, `runtime-ports.test`, `image-metadata-xmp.test`, `image-model.test`, `node-validation-error-contract.test`, `generate-route-validation-error.test`, `local-import-contract.test`, `node-pending-recovery-contract.test`, `node-parent-source-contract.test`, `refs-size.test`, `history-tombstone.test`, `history-metadata-fallback.test`, `session-conflict.test`, `style-sheet.test`, `generation-errors.test`.
- 14 integration files: `api-provider-parity.test`, `card-news-contract.test`, `node-streaming-sse.test`, `oauth-proxy-error-safety.test`, `request-logging.test`, `image-metadata-route.test`, plus 8 others (see inventory).

**MODIFY:**
- `scripts/run-tests.mjs` — extension match.
- `tsconfig.json` — include `tests/**/*.test.ts` for typecheck only.
- `package.json` `lint:pkg` — no change needed (tests excluded from publish).

## Diff highlights

### `scripts/run-tests.mjs`
```js
- const files = readdirSync(testDir)
-   .filter((f) => f.endsWith(".test.js"))
+ const files = readdirSync(testDir)
+   .filter((f) => f.endsWith(".test.js") || f.endsWith(".test.ts"))
    .map((f) => join(testDir, f))
    .sort();
```
Already invokes via `node --import tsx --test`, which transparently runs `.ts`. No further changes.

### `tsconfig.json`
```json
   "exclude": [
     "node_modules",
     "ui",
-    "tests",
     "scripts",
     "integrations",
-    "**/*.test.ts"
+    "**/*.test.ts.snapshot"
   ]
```
Result: `.test.ts` files are typechecked with the project. Production build configs (`tsconfig.build.json`, `tsconfig.bin.json`) keep their existing `tests` exclusion — tests are never emitted.

> **Add to `tsconfig.json`** if test imports need additional types:
> ```json
> "types": ["node"],
> ```
> (already present)

### Per-file typing: minimum required

Most tests need **just a rename**. tsx handles execution; `node:test` types come from `@types/node`.

A few cases need a small `import type`:
```ts
// Before: tests/inflight.test.js
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { register, lookup } from "../lib/inflight.ts";
```
```ts
// After: tests/inflight.test.ts (often unchanged!)
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { register, lookup } from "../lib/inflight.ts";
```
TypeScript will infer types from `inflight.ts` exports. Type errors that surface here are **valuable** — they're the API drift the migration is supposed to catch.

When integration tests stub express request/response objects:
```ts
import type { Request, Response } from "express";
const fakeReq = { body: { id: "x" } } as Partial<Request> as Request;
```
Use `as Partial<Request> as Request` to make the bridge explicit.

## Sub-phase plan

- **P07a:** Rename + run, fix surfaced type errors. (24 runtime files; 1 PR.)
- **P07b:** Rename + run for the 14 integration files. (1 PR.)
- **P07c:** Update `scripts/run-tests.mjs` filter + tsconfig include. (Tiny PR; can be folded into P07a if landed first.)

## Sub-agent dispatch (per sub-phase)

```
cli-jaw dispatch --agent "Backend" --task "..."
```
Or via Task tool with `gpt-5.5`:
> "Rename the [N] test files in [list] from .test.js to .test.ts in /Users/jun/Developer/new/700_projects/ima2-gen/tests/. After renaming, run `npm test` and `npx tsc --noEmit -p tsconfig.json` (after updating the include glob per P07-test-migration.md). For any TS errors, propose minimal typing fixes in the test files (do NOT modify lib/routes/bin source). Output a per-file report: passed | typed-with-N-fixes | failed-because-X."

## Verify

```bash
# Per sub-phase
git mv tests/foo.test.js tests/foo.test.ts   # …×24
npm run typecheck                # must include test files now
npm test                         # 539/539; runtime test count unchanged
npm run build:server             # production build still excludes tests
```

## Risk

- **Low-medium.** Existing tests already use `--import tsx`, so `.ts` execution works today.
- **Trap:** if a test imports `../lib/something.js` (note `.js` extension on a TS source path), tsx resolves it. After `.ts` rename, those imports may now report TS error "module has no default export". Fix by changing `.js` import suffix to `.ts` in test imports — the project already uses NodeNext, which requires the file extension.
- **Trap:** test fixtures stored as `.json` next to tests are fine. Fixtures stored as `.js` modules need either rename or kept as `.js`.

## Rollback

Per sub-phase. Each rename PR can be reverted independently.

## Exit criteria

- [ ] 38 test files have `.test.ts` extension.
- [ ] `tests/*.test.js` count = 76 (the contract tests, intentionally kept).
- [ ] `tests/*.mjs` count = 1 (smoke).
- [ ] `scripts/run-tests.mjs` matches both extensions.
- [ ] `npm run typecheck` passes including tests.
- [ ] `npm test` 539/539 (no test count change; conversion is rename-only behaviorally).
