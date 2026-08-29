# P05 — `strictNullChecks` rollout

**Goal:** Enable `strictNullChecks: true`. Measured 291 errors clustered in 10 files; this phase fixes them and flips the flag.

**Effort:** M (3–5 PRs split by directory)
**Owner:** Boss writes; sub-agent (`gpt-5.5`) batch-fixes the mechanical narrowings; GPT Pro consulted for any architectural typing question.
**Depends on:** P03 (RuntimeContext), P04 (oauthProxy split — error count per file becomes manageable).

---

## Why

`strictNullChecks` makes `T` and `T | null` distinct types. Catches the most common runtime bug class: assuming a value exists when it might be `undefined`. Measured **291 errors** total (verified `npx tsc --noEmit -p tsconfig.json --strictNullChecks`).

Hot spots:

| Errors | File | Strategy |
|---|---|---|
| 46 | `routes/prompts.ts` | guard inputs at route handler edges; many are `req.body.x` being possibly undefined |
| 22 | `lib/sessionStore.ts` | optional fields in stored records |
| 17 | `routes/promptImport.ts` | similar to prompts |
| 16 | `lib/promptImport/githubDiscovery.ts` | API response shapes |
| 12 | `lib/cardNewsPlannerSchema.ts` | parsed JSON schemas |
| 12 | `lib/cardNewsGenerator.ts` | downstream of schema |
| 11 | `routes/generate.ts` | request body fields |
| 11 | `lib/inflight.ts` | map lookups |
| 10 | `lib/refs.ts` | optional metadata |
| 10 | `lib/promptImport/githubFolder.ts` | API responses |

Top 10 = ~150 / 291 errors (~52%).

## Scope

**MODIFY:** the 10 hot files + `tsconfig.json` flag flip + scattered minor fixes.

**Sub-phases (one PR each):**
- **P05a:** routes/ (prompts, promptImport, generate) — 74 errors
- **P05b:** lib/sessionStore + lib/inflight + lib/refs — 43 errors
- **P05c:** lib/promptImport/* + lib/cardNews* — 50 errors
- **P05d:** Remaining ~120 long-tail errors across other files
- **P05e:** Flip `tsconfig.json` `strictNullChecks: true`

## Diff highlights — recurring patterns

### Pattern 1 — request body narrowing (routes)
Before:
```ts
app.post("/api/prompts", (req, res) => {
  const id = req.body.id;        // strictNullChecks: id: string | undefined
  const text = req.body.text;
  store.save(id, text);          // store.save(id: string, text: string) — error
});
```
After:
```ts
app.post("/api/prompts", (req, res) => {
  const id = typeof req.body?.id === "string" ? req.body.id : null;
  const text = typeof req.body?.text === "string" ? req.body.text : null;
  if (!id || !text) return res.status(400).json({ error: "id and text required" });
  store.save(id, text);
});
```
> **Rule:** ALL public-route input narrowing must produce a 400 response, not a thrown error. Existing tests likely already expect this — verify per file.

### Pattern 2 — Map.get narrowing (sessionStore, inflight)
Before:
```ts
const entry = inflightMap.get(key);
entry.controller.abort();     // entry: T | undefined — error
```
After:
```ts
const entry = inflightMap.get(key);
if (!entry) return;            // or throw with explicit message
entry.controller.abort();
```

### Pattern 3 — JSON.parse result
Before:
```ts
const cfg = JSON.parse(text);
return cfg.foo;              // any — but with strictNullChecks against typed parsers, becomes error
```
After: parse via a small zod-free validator OR cast to a typed shape:
```ts
function parseCfg(text: string): { foo?: string } {
  try { return JSON.parse(text); } catch { return {}; }
}
const cfg = parseCfg(text);
return cfg.foo ?? "default";
```

### Pattern 4 — non-null assertion `!`
**Allowed only** when the language can't prove it but a runtime invariant guarantees it (e.g., `regex.exec()` matched on the line above). Each `!` requires a code comment:
```ts
const m = /^(\w+)/.exec(s)!;          // ❌ no comment
const m = /^(\w+)/.exec(s);
if (!m) throw new Error("unreachable: regex tested above");
const word = m[1];                     // ✅
```
Avoid `!` in PR diff. Use early return / throw instead.

## tsconfig flip (final commit of P05)
```json
- "strictNullChecks": false,
+ "strictNullChecks": true,
```

`strictPropertyInitialization` becomes effective once `strictNullChecks` is on. Per inventory, ~0 errors expected (no class-field-heavy code). If any surface, add to the same PR:
```json
+ "strictPropertyInitialization": true,
```

## Sub-agent dispatch

For each sub-phase (P05a–d), dispatch:
> Sub-agent: `gpt-5.5`. Task:
> "ima2-gen at /Users/jun/Developer/new/700_projects/ima2-gen. Run `npx tsc --noEmit -p tsconfig.json --strictNullChecks 2>&1 | grep '^routes/prompts.ts'` (substitute filename per sub-phase). For each error, propose a minimal fix following Pattern 1–4 in P05-strict-null-checks.md. Output a unified diff. Do not flip the tsconfig flag in this PR. Do not introduce `!` non-null assertions. Run `npm test` after applying — report pass/fail. Ask before introducing any new dependency."

GPT Pro review at end of P05c (mid-rollout) and end of P05e (flag flip).

## Verify

After each sub-phase:
```bash
# Track error count regression
npx tsc --noEmit -p tsconfig.json --strictNullChecks 2>&1 | grep -c "error TS"
# Should monotonically decrease toward 0.

npm run typecheck         # current flags green
npm test                  # 539/539
npm run build:server && npm run build:cli
```

After P05e (flag flip):
```bash
npm run typecheck         # green WITH strictNullChecks: true
```

## Risk

- **Medium-high.** Behavioral changes possible: routes that previously returned 500 may now return 400 (intended improvement). Flag in PR description.
- **Test gap risk:** the contract tests don't exercise runtime behavior; only ~38 tests touch routes. **P07 (test conversion) should ideally land before P05** if the runtime test count needs improving — but P07 is large. Acceptable to do P05 with current coverage.
- **Trap:** widening to `T | null` in lib types may cascade to UI types if shared. Check `ui/src/api/types.ts` (if it exists) for shared shapes.

## Rollback

Per sub-phase. The flag flip (P05e) is the riskiest — keep that as a standalone PR so it can be reverted in isolation.

## Exit criteria

- [ ] `npx tsc --noEmit -p tsconfig.json --strictNullChecks` reports 0 errors.
- [ ] `tsconfig.json` has `strictNullChecks: true`.
- [ ] `npm test` 539/539.
- [ ] No new `!` non-null assertions in diff.
- [ ] No new dependencies introduced.
