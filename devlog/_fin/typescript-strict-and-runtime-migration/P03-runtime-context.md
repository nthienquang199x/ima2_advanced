# P03 — `RuntimeContext` interface

**Goal:** Replace pervasive `ctx: any = {}` with a typed `RuntimeContext` interface. Unblocks ~80 of the 1,205 `noImplicitAny` errors and enables intellisense across server/route/bin entry points.

**Effort:** S
**Owner:** Boss writes interface; sub-agent (`claude-opus-4.7`) optional for sweep.
**Depends on:** P02.

---

## Why

`ctx: any = {}` appears as a default param in `lib/oauthProxy.ts`, `lib/responsesImageAdapter.ts`, and is forwarded through routes. Measured fields used today (verified by `grep -hE 'ctx\.(\w+)'`):

| Field | Type (verified usage) | Source |
|---|---|---|
| `apiKey` | `string \| undefined` | env or oauth |
| `apiKeySource` | `"env" \| "oauth" \| "config" \| undefined` | resolved at boot |
| `config` | `LoadedConfig` (existing type in `bin/lib/configFile`) | loaded at boot |
| `hasApiKey` | `boolean` | derived |
| `oauthActualPort` | `number \| undefined` | runtimePorts |
| `oauthPort` | `number` | configured |
| `oauthReadyPromise` | `Promise<void> \| null` | inflight |
| `oauthReadyState` | `"pending" \| "ready" \| "error" \| undefined` | runtime |
| `oauthUrl` | `string` | derived |
| `openai` | `OpenAI` (from `openai` package) | client |
| `packageVersion` | `string` | from package.json |
| `rootDir` | `string` | resolved at boot |
| `serverActualPort` | `number \| undefined` | runtime |
| `serverConfiguredPort` | `number` | config |
| `serverUrl` | `string` | derived |
| `startedAt` | `number` (epoch ms) | boot |

## Scope

**NEW:**
- `lib/runtimeContext.ts` — `RuntimeContext` interface + `createRuntimeContext()` factory + `RuntimeContextOverrides` partial.

**MODIFY:**
- `server.ts` — annotate the `ctx` it builds.
- `lib/oauthProxy.ts` (and split successors from P04) — `ctx: any = {}` → `ctx: RuntimeContext`.
- `lib/responsesImageAdapter.ts` — same.
- `routes/*.ts` — import the type wherever a `ctx` parameter is forwarded.
- `bin/commands/*.ts` (those that build/inspect ctx) — same.

## Diff highlights

### NEW `lib/runtimeContext.ts`
```ts
import type OpenAI from "openai";
import type { LoadedConfig } from "../bin/lib/configFile.ts"; // adjust if config type lives elsewhere

export type ApiKeySource = "env" | "oauth" | "config" | undefined;
export type OAuthReadyState = "pending" | "ready" | "error" | undefined;

export interface RuntimeContext {
  apiKey: string | undefined;
  apiKeySource: ApiKeySource;
  config: LoadedConfig;
  hasApiKey: boolean;
  oauthActualPort: number | undefined;
  oauthPort: number;
  oauthReadyPromise: Promise<void> | null;
  oauthReadyState: OAuthReadyState;
  oauthUrl: string;
  openai: OpenAI | null;
  packageVersion: string;
  rootDir: string;
  serverActualPort: number | undefined;
  serverConfiguredPort: number;
  serverUrl: string;
  startedAt: number;
}

/** A partial used during boot when only some fields are known. */
export type RuntimeContextOverrides = Partial<RuntimeContext>;

/** Stub-friendly default (used by tests; do not use in production boot). */
export function createTestRuntimeContext(over: RuntimeContextOverrides = {}): RuntimeContext {
  const now = Date.now();
  const base: RuntimeContext = {
    apiKey: undefined,
    apiKeySource: undefined,
    config: {} as LoadedConfig,
    hasApiKey: false,
    oauthActualPort: undefined,
    oauthPort: 11782,
    oauthReadyPromise: null,
    oauthReadyState: undefined,
    oauthUrl: "http://127.0.0.1:11782",
    openai: null,
    packageVersion: "0.0.0-test",
    rootDir: process.cwd(),
    serverActualPort: undefined,
    serverConfiguredPort: 11783,
    serverUrl: "http://127.0.0.1:11783",
    startedAt: now,
  };
  return { ...base, ...over };
}
```

### Mechanical sweep
For every match of `ctx: any = {}` or `ctx: any` in `lib/`, `routes/`, `bin/`:
```ts
- function foo(ctx: any = {}) {
+ function foo(ctx: RuntimeContext) {
```
For optional ctx forwards, prefer `Partial<RuntimeContext>` rather than `RuntimeContext | undefined`. Avoid making `ctx` truly optional unless current call sites support that.

If a call site currently passes `{}`:
```ts
- generateViaOAuth(args, {});
+ generateViaOAuth(args, ctx);   // require caller to thread ctx
```
This is the **integration risk** — track every changed call site in PR description.

## Sub-agent dispatch (optional)

```bash
cli-jaw dispatch --agent "Backend" --task "..."
```

Or use Task tool with `claude-opus-4.7`:
> "Sweep ima2-gen lib/ routes/ bin/ for `ctx: any` parameter declarations. For each, replace with `RuntimeContext` (import from `lib/runtimeContext.ts`). Identify call sites that pass `{}` literal as ctx — for those, report the call chain (do not auto-edit; manual review needed). Output a markdown table: file:line | old signature | new signature | callers."

## Verify

```bash
npm run typecheck
# Note: ~80 noImplicitAny errors expected to disappear (these don't actually surface
# until P06 enables noImplicitAny; this phase pays down the debt early.)
npm test
npm run build:server && npm run build:cli
```

Boot smoke:
```bash
npm start &           # node bin/ima2.js serve
sleep 3
curl -s localhost:11783/api/health | jq .
kill %1
```

## Risk

- **Medium.** Touching call signatures in `lib/oauthProxy.ts` ripples to every route that calls `generateViaOAuth` etc.
- **Mitigation:** if a call site cannot supply `ctx` (e.g., a test), use the new `createTestRuntimeContext()` factory.
- **Trap:** circular import — `lib/runtimeContext.ts` imports `LoadedConfig` from `bin/lib/configFile.ts`. If circularity arises, move `LoadedConfig` to `lib/configTypes.ts` (type-only file with `export interface LoadedConfig`).

## Rollback

Revert PR. Phase is one logical unit but may want to be **2 PRs**: (1) introduce type + factory; (2) sweep call sites. Latter is more reverable.

## Exit criteria

- [ ] `lib/runtimeContext.ts` exists with `RuntimeContext`, `RuntimeContextOverrides`, `createTestRuntimeContext`.
- [ ] No `ctx: any` remains in `lib/`, `routes/`, `bin/` (`grep -nE 'ctx\\s*:\\s*any' lib routes bin -r` empty).
- [ ] `npm run typecheck` green.
- [ ] `npm test` 539/539.
- [ ] `npm start` boots and `/api/health` returns 200.
