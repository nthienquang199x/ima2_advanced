# P09 — Flip `strict: true` and remove individual overrides

**Goal:** Once all sub-flags pass individually (P01, P02, P05, P06), turn on the umbrella `strict: true` and prune redundant `false` overrides from `tsconfig.json`. Final cleanup phase for type strictness.

**Effort:** XS (a single tsconfig diff + tsc verification).
**Owner:** Boss.
**Depends on:** P01, P02, P05, P06.

---

## Why

`strict: true` is the umbrella for: `noImplicitAny`, `strictNullChecks`, `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization`, `alwaysStrict`, `noImplicitThis`, `useUnknownInCatchVariables`. By the time P01–P06 land, **all** of these are already on or implicit. Flipping `strict: true` is the readability/canonical-form change.

Two checks remain that aren't in P01–P06:
- `strictBindCallApply` — strict typing of `Function.prototype.bind/call/apply`. Almost certainly already satisfied; verify with one tsc run.
- `noImplicitThis` — bans `this` typed as implicit `any`. Likely 0 errors in a codebase that has no `this`-bound classes outside `Error` subclasses.
- `alwaysStrict` — emits `"use strict"` in JS output. Cosmetic for ESM (already strict).

## Scope

**MODIFY:** `tsconfig.json` only.

## Diff

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "lib": ["ES2022"],
    "types": ["node"],

    "noEmit": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": false,

-   "strict": false,
-   "noImplicitAny": false,
-   "strictNullChecks": false,
-   "strictFunctionTypes": true,
-   "noUnusedLocals": true,
-   "noUnusedParameters": true,
-   "useUnknownInCatchVariables": true,
+   "strict": true,
+   "noUnusedLocals": true,
+   "noUnusedParameters": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "allowSyntheticDefaultImports": true
  },
  ...
}
```

After the flip, `noImplicitAny` etc. are inherited from `strict: true`. Keep `noUnusedLocals` and `noUnusedParameters` explicit because they're **not** part of `strict`.

## Verify

```bash
npm run typecheck             # MUST be 0 errors. If any appears, that flag wasn't covered by P01–P06.
npm run build:server
npm run build:cli
npm test
```

If new errors appear, they're from `strictBindCallApply` or `noImplicitThis`. Fix, then re-run. They should be small.

## GPT Pro gate (final)

Send the post-flip tsconfig + final error count + sample of the most "interesting" diff hunks from P01–P06:
```bash
agbrowse web-ai query --vendor chatgpt --model pro --inline-only --prompt "$(cat <<'EOF'
ima2-gen TypeScript migration is complete. Final tsconfig is:

[paste tsconfig.json]

Verify:
1. Are there any strict-mode flags worth turning on beyond `strict: true`?
   (exactOptionalPropertyTypes, noUncheckedIndexedAccess, noPropertyAccessFromIndexSignature)
2. For a Node ESM (NodeNext) backend with React/Vite UI, is this a sensible final state?
3. Anything missing for safe long-term maintenance (e.g., `--incremental`, `tsBuildInfoFile`, project references)?
EOF
)" --json
```

Post the response into `_gpt-pro-verification.md` for record.

## Risk

- **Low.** If P01–P06 were complete, `strict: true` is no-op.
- **Trap:** if a developer landed a regression between P06e and P09 that compiled because `noImplicitAny` was being toggled, this PR catches it. Treat any new error here as a regression bisect.

## Rollback

Single revert of the tsconfig diff.

## Exit criteria

- [ ] `tsconfig.json` has `strict: true` and no per-flag `false` overrides.
- [ ] `npm run typecheck` 0 errors.
- [ ] `npm test` 539/539.
- [ ] `npm run build:server` and `npm run build:cli` succeed.
- [ ] GPT Pro response saved to `_gpt-pro-verification.md`.
