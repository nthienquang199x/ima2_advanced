# P06 — `noImplicitAny` rollout (1,205 errors → 0)

**Goal:** Enable `noImplicitAny: true`. Largest single piece of work in the migration. Done in 4 directory-scoped sub-phases.

**Effort:** L (4 sub-phases × 1–2 PRs each = 5–8 PRs total)
**Owner:** Boss orchestrates; sub-agents (`gpt-5.5` for mechanical typing batch, `claude-opus-4.7` for architectural shape decisions); GPT Pro at each sub-phase gate.
**Depends on:** P03 (RuntimeContext kills ~80 errors), P04 (oauthProxy split bounds the largest hot spot), P05 (strictNullChecks first so types exist with proper nullability before being widened from `any`).

---

## Why

1,205 implicit-any errors. Going strict ad-hoc would spread to dozens of PRs without focus. Directory order chosen by surface size:

| Sub-phase | Surface | Approx errors | Strategy |
|---|---|---|---|
| **P06a** | `bin/` (CLI commands) | ~120 | Smallest area; many `(arg) => ...` callbacks. Quick win. |
| **P06b** | `routes/` (Express handlers) | ~250 | Mostly `req.body` / response shapes. Pairs with P05 work. |
| **P06c** | `lib/` (non-OAuth) | ~400 | Domain types — define small shape interfaces in `lib/types/`. |
| **P06d** | `lib/oauthProxy/*` + `lib/responsesImageAdapter/*` | ~430 | Already split (P04). Tight typing of OpenAI request/response shapes. |
| **P06e** | tsconfig flag flip | — | `noImplicitAny: true` |

## Scope

**NEW:**
- `lib/types/` directory for cross-cutting shape interfaces:
  - `lib/types/openai.ts` — request/response shapes for `POST /v1/responses`, `POST /v1/images/generations`, SSE event payloads.
  - `lib/types/promptImport.ts` — GitHub API + curated source shapes.
  - `lib/types/cardNews.ts` — planner schema types.

**MODIFY:** each `.ts` file in the corresponding directory per sub-phase + `tsconfig.json` final flip.

## Diff highlights — recurring patterns

### Pattern 1 — callback args (CLI, lib)
Before:
```ts
results.forEach((r) => {            // r: implicit any
  console.log(r.id, r.status);
});
```
After:
```ts
results.forEach((r: ResultRow) => {  // ResultRow defined nearby or imported
  console.log(r.id, r.status);
});
```
Or, if `results` itself is typed, this fixes itself — prefer typing the **source array** over annotating each callback.

### Pattern 2 — function params with defaults
Before:
```ts
function foo(opts = {}) { return opts.kind; }   // opts: any
```
After:
```ts
interface FooOpts { kind?: string }
function foo(opts: FooOpts = {}) { return opts.kind; }
```

### Pattern 3 — JSON.parse / external API shapes
Define a narrow shape type local to the module; do not pull in zod or new deps unless required:
```ts
interface GithubRepoSummary {
  name: string;
  default_branch?: string;
  // …only fields actually used
}
const repo = JSON.parse(body) as GithubRepoSummary;
```

### Pattern 4 — Express handlers
Before:
```ts
app.get("/foo", (req, res) => { ... });   // req, res implicitly typed
```
With `@types/express` already installed, these are typed. Implicit-any only when destructuring deep:
```ts
app.post("/foo", (req, res) => {
  const { id, text, opts = {} } = req.body;   // all any
});
```
After:
```ts
interface FooBody { id?: string; text?: string; opts?: { kind?: string } }
app.post("/foo", (req: Request<{}, unknown, FooBody>, res: Response) => {
  const { id, text, opts = {} } = req.body;
});
```

## Sub-phase plan

### P06a — `bin/` (~120 errors, 1 PR)
- Top files: `bin/commands/prompt.ts` (26), `bin/ima2.ts` (after P01 cleanup).
- Sub-agent dispatch (`gpt-5.5`):
  > "Run `npx tsc --noEmit -p tsconfig.json --noImplicitAny 2>&1 | grep '^bin/' | head -200`. For each error, propose typed-fix patch. Prefer typing source arrays/objects over per-callback annotations. Output unified diff. Do not flip tsconfig flag."
- Verify: `npm test` (CLI tests), `npm run build:cli` emits, `node bin/ima2.js --help` works.

### P06b — `routes/` (~250 errors, 1–2 PRs)
- Top files: `routes/promptImport.ts` (46), `routes/cardNews.ts` (37), `routes/prompts.ts` (30).
- Sub-agent: same shape. Add: define `XxxBody` interfaces local to each route file.
- Verify: `npm test` (route + integration tests).

### P06c — `lib/` non-OAuth (~400 errors, 2 PRs)
- Top: `lib/responsesImageAdapter` (43, deferred to P06d), `lib/promptImport/githubFolder.ts` (40), `lib/promptImport/parsePromptCandidates.ts` (37), `lib/historyList.ts` (29), `lib/cardNewsPlannerSchema.ts` (29), `lib/sessionStore.ts` (26), `lib/logger.ts` (25).
- Strategy: introduce `lib/types/promptImport.ts`, `lib/types/cardNews.ts` first (small NEW PR), then mechanical typing.

### P06d — `lib/oauthProxy/*` + `lib/responsesImageAdapter/*` (~430 errors, 1–2 PRs)
- Pre-req: P04 split done.
- Strategy: introduce `lib/types/openai.ts` capturing the SSE event shape used by `extractPartialImage` etc. GPT Pro consult: "What is the canonical shape of OpenAI Responses API SSE `image.partial` event in 2026? Confirm against current `openai` npm package types."
- Verify: live SSE smoke (curl streaming generate, observe partial frames).

### P06e — tsconfig flip
```json
- "noImplicitAny": false,
+ "noImplicitAny": true,
```
Standalone PR. Should be a no-op if P06a–d completed.

## GPT Pro gates

After each sub-phase:
```bash
agbrowse web-ai query --vendor chatgpt --model pro --inline-only --prompt "$(cat <<'EOF'
ima2-gen P06X review.

Diff stats: [paste git diff --stat]
Remaining noImplicitAny errors after this PR: [paste count]
Sample of typed shapes introduced: [paste 1–2 representative interfaces]

Verify:
1. Are introduced interfaces minimal (only fields used) or over-specified?
2. Any place where `unknown` would be safer than the chosen specific type?
3. Any signature change that breaks public API surface (re-exported from lib/oauthProxy.ts barrel)?
4. Any pattern that should be lifted to a shared type module before the next sub-phase?
EOF
)" --json
```

## Risk

- **High overall** because of breadth, but **per-sub-phase risk is low** — directory isolation bounds blast radius.
- **Trap:** typing OpenAI response shapes too narrowly. The `openai` package ships its own types; **prefer importing from there** rather than redefining. Inspect:
  ```bash
  grep -r "from \"openai\"" lib routes
  ```
  Use `OpenAI.Responses.*` types where available; only fall back to local shapes for fields the package types don't expose.
- **Trap:** `req.body` is typed as `any` in `@types/express` to allow generic body. Use `Request<P, ResB, ReqB>` parameterization rather than asserting `req.body as Foo`.

## Rollback

Per sub-phase. Each is independent; revert any one without blocking others.

## Exit criteria

- [ ] `npx tsc --noEmit --noImplicitAny` reports 0 errors.
- [ ] `tsconfig.json` has `noImplicitAny: true`.
- [ ] `: any` count (across `lib/routes/bin`) reduced from 222 to **≤ 30** (allow some `: any` for genuinely unknown JSON parse boundaries — but each remaining one needs a `// reason:` comment).
- [ ] `npm test` 539/539 throughout.
- [ ] Live SSE generate smoke produces partial frames correctly (P06d gate).
- [ ] No new dependencies (no zod, no io-ts, etc.).
