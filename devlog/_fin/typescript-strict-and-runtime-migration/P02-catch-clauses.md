# P02 — Catch-clause typing + `useUnknownInCatchVariables`

**Goal:** Enable `useUnknownInCatchVariables` after introducing a single `errInfo()` helper that handles 100% of the 152 measured errors.

**Effort:** S (half day)
**Owner:** Boss writes; sub-agent (`gpt-5.5`) optional for mechanical edit batch.
**Depends on:** P01.

---

## Why

`useUnknownInCatchVariables` makes `catch (e)` infer `e: unknown` instead of `any`. Measured: **152 errors**, all of the same shape: `err.message`, `err.code`, `err.status` accessed directly. One helper covers all of them.

Hot spots (from inventory): `routes/sessions.ts` (16), `routes/prompts.ts` (16), `routes/generate.ts` (12), `routes/nodes.ts` (11), `routes/history.ts` (10), `routes/multimode.ts` (7), `routes/canvasVersions.ts` (6), `lib/historyList.ts` (6), `bin/commands/ps.ts` (6), `bin/commands/gen.ts` (6).

## Scope

**NEW (1 file):**
- `lib/errInfo.ts` — single helper.

**MODIFY (~25 files):**
- All catch blocks accessing `err.{message,code,status,stack}` → use `errInfo(e)`.
- `tsconfig.json` — flip flag (after fixes are in).

## Diff highlights

### NEW `lib/errInfo.ts`
```ts
// lib/errInfo.ts
export interface ErrInfo {
  message: string;
  code: string | undefined;
  status: number | undefined;
  cause: unknown;
  stack: string | undefined;
  raw: unknown;
}

/** Narrow an unknown thrown value to a stable info shape. */
export function errInfo(e: unknown): ErrInfo {
  if (e instanceof Error) {
    const anyE = e as Error & { code?: unknown; status?: unknown; cause?: unknown };
    return {
      message: e.message,
      code: typeof anyE.code === "string" ? anyE.code : undefined,
      status: typeof anyE.status === "number" ? anyE.status : undefined,
      cause: anyE.cause,
      stack: e.stack,
      raw: e,
    };
  }
  if (e && typeof e === "object") {
    const o = e as Record<string, unknown>;
    return {
      message: typeof o.message === "string" ? o.message : String(e),
      code: typeof o.code === "string" ? o.code : undefined,
      status: typeof o.status === "number" ? o.status : undefined,
      cause: o.cause,
      stack: typeof o.stack === "string" ? o.stack : undefined,
      raw: e,
    };
  }
  return { message: String(e), code: undefined, status: undefined, cause: undefined, stack: undefined, raw: e };
}

/** Handy for `throw e instanceof Error ? e : asError(e)`. */
export function asError(e: unknown): Error {
  return e instanceof Error ? e : new Error(typeof e === "string" ? e : JSON.stringify(e));
}
```

### Per-file mechanical rewrite
Before:
```ts
try { ... } catch (err) {
  if (err.code === "ENOENT") return null;
  log.error(err.message);
  if (err.status === 401) ...
}
```
After:
```ts
import { errInfo } from "../lib/errInfo.ts";  // adjust relative path

try { ... } catch (e) {
  const err = errInfo(e);
  if (err.code === "ENOENT") return null;
  log.error(err.message);
  if (err.status === 401) ...
}
```

> **Rule:** never delete `instanceof Error` guards if already present — those need no change. Only sites that read `err.{message,code,status}` from a bare `catch (err)` need the helper.

### `tsconfig.json` flag flip
```json
+ "useUnknownInCatchVariables": true,
```

## Verification flow per file

For each touched file, ensure:
1. `import { errInfo } from "../...../lib/errInfo.ts";` is present.
2. No catch block accesses `err.message/code/status/stack` without going through the helper.
3. `npx tsc --noEmit -p tsconfig.json --useUnknownInCatchVariables 2>&1 | grep <file> | wc -l` is 0.

## Sub-agent batch (optional)

Dispatch `gpt-5.5` with prompt:
> "In ima2-gen at /Users/jun/Developer/new/700_projects/ima2-gen, add `import { errInfo } from "../lib/errInfo.ts"` (path-adjusted) to each file in [list], rewrite each `catch (err) { ... err.{message,code,status,stack} ... }` to `catch (e) { const err = errInfo(e); ... }`. Do not change `catch` blocks that already use `instanceof Error`. After edits, run `npx tsc --noEmit --useUnknownInCatchVariables` and report remaining error count per file."

## Verify

```bash
npm run typecheck   # green with flag on
npm test            # 539/539, no behavioral drift (errInfo preserves all current values)
npm run build:server
npm run build:cli
```

Smoke check that error responses are unchanged (sample a few): trigger 401 from oauthProxy, trigger ENOENT from history reader.

## Risk

- **Low** if helper is correct and applied mechanically.
- **Trap:** some sites may currently rely on `err.message` being `undefined` for non-Error throws to skip logging. Helper returns `String(e)` instead. Audit `if (err.message)` patterns — they keep working since the helper still returns a string, never `undefined` for `message`.
- **Trap:** `err.cause` typing — kept as `unknown` to avoid implicit-any.

## Rollback

Single revert. Helper deletion + 25-file revert is one commit.

## Exit criteria

- [ ] `lib/errInfo.ts` exists with two exports (`errInfo`, `asError`).
- [ ] `useUnknownInCatchVariables: true` in tsconfig.
- [ ] `npm run typecheck` 0 errors.
- [ ] `npm test` 539/539.
- [ ] Manual error-path smoke (oauth 401, ENOENT) returns identical user-visible messages.
