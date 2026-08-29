# P01 — Strict easy wins

**Goal:** Enable three strict sub-flags that produce ≤13 total errors. All trivially fixable.

**Effort:** XS
**Owner:** Boss (direct).
**Depends on:** P00 (CI typecheck active).

---

## Why

Per measured inventory:
- `strictFunctionTypes` → **0** errors. Free flip.
- `noUnusedLocals` → **5** errors (`bin/commands/multimode.ts:1`, `bin/ima2.ts:8,17`, `bin/lib/files.ts:2`).
- `noUnusedParameters` → **8** errors (`lib/oauthProxy.ts:219` ×2, `lib/promptImport/parsePromptCandidates.ts:95`, `lib/responsesImageAdapter.ts:62`, `routes/promptImport.ts:221`, `routes/prompts.ts:12,232,260`).

Total 13 fixes. Net types-safety gain + cleaner code.

## Scope

**MODIFY (~10 files):**

1. `tsconfig.json` — flip three flags.
2. Each file listed above — remove unused imports / prefix unused params with `_`.

## Diff highlights

### `tsconfig.json`
```json
   "compilerOptions": {
     ...
     "strict": false,
-    "noImplicitAny": false,
-    "strictNullChecks": false,
-    "noUnusedLocals": false,
-    "noUnusedParameters": false,
+    "noImplicitAny": false,
+    "strictNullChecks": false,
+    "strictFunctionTypes": true,
+    "noUnusedLocals": true,
+    "noUnusedParameters": true,
     "noImplicitOverride": true,
```

### Unused-locals fixes (delete unused imports)
```ts
// bin/commands/multimode.ts:1 — example
- import path from "node:path";   // unused
```
Repeat shape for `bin/ima2.ts:8,17` and `bin/lib/files.ts:2`. Each is a single deletion.

### Unused-parameters fixes (`_`-prefix)
```ts
// lib/oauthProxy.ts:219
- function throwOAuthTimeoutError(err, { timeoutMs, requestId, scope }) {
+ function throwOAuthTimeoutError(_err, { timeoutMs, requestId, scope: _scope }) {
```
Apply same `_` rename to:
- `lib/promptImport/parsePromptCandidates.ts:95`
- `lib/responsesImageAdapter.ts:62`
- `routes/promptImport.ts:221`
- `routes/prompts.ts:12, 232, 260`

> **Rule:** prefer `_name` over deletion when the parameter is part of an externally-visible signature (Express `(req, res, next)`, route handler). Use deletion only for stale local imports.

## Verify

```bash
npm run typecheck    # must be green with the three new flags
npm test             # no behavioral change → 539/539
npm run build:server
npm run build:cli
```

## Risk

- **Very low.** No runtime semantics change. Removing unused imports cannot affect emit.
- One trap: if a `_`-prefixed param is later referenced inside the function body, tsc reports `'_xx' is declared but...` only on flag — not on use. Double-check each file with `grep` after rename.

## Rollback

Single commit revert. tsconfig flag flips and ~13 line fixes are atomic.

## Exit criteria

- [ ] `tsconfig.json` has `strictFunctionTypes:true`, `noUnusedLocals:true`, `noUnusedParameters:true`.
- [ ] `npm run typecheck` is green.
- [ ] `npm test` 539/539.
- [ ] No new `// @ts-ignore` or `// @ts-expect-error` introduced (current count is 0; keep it 0).
