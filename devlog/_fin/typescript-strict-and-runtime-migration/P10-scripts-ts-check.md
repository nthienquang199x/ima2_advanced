# P10 — Scripts polish: `// @ts-check` + JSDoc

**Goal:** Light-touch checking on `scripts/*.mjs` without converting to `.ts`.

**Effort:** XS
**Owner:** Boss.
**Depends on:** —

---

## Why

Per inventory:
- `scripts/dev.mjs` (42 LOC) — pure orchestration
- `scripts/run-tests.mjs` (22 LOC) — trivial spawn
- `scripts/fix-shebangs.mjs` (30 LOC) — runs **after** tsc; converting to .ts would require yet another build step.

Conversion to `.ts` adds zero domain types and complicates the build ordering. Adding `// @ts-check` headers + JSDoc lets the IDE / `tsc --noEmit --allowJs` provide light-touch checking.

## Scope

**MODIFY (3 files):**

### `scripts/dev.mjs`
```js
#!/usr/bin/env node
+// @ts-check
+/** @typedef {import("node:child_process").SpawnSyncReturns<Buffer>} SpawnResult */
import { spawn, spawnSync } from "node:child_process";
...
```

### `scripts/run-tests.mjs`
```js
#!/usr/bin/env node
+// @ts-check
import { readdirSync } from "node:fs";
...
```

### `scripts/fix-shebangs.mjs`
```js
#!/usr/bin/env node
+// @ts-check
import { readFileSync, writeFileSync } from "node:fs";
...
```

## Verify

```bash
# Optional: prove that ts-check works
npx tsc --noEmit --allowJs --checkJs scripts/*.mjs --target ES2022 --module NodeNext --moduleResolution NodeNext --types node --skipLibCheck
```
Expect 0 errors. If any surface, fix with JSDoc annotations (no behavior change).

```bash
npm run dev:server   # still boots
npm test             # still 539/539
node scripts/fix-shebangs.mjs   # idempotent re-run
```

## Risk

Negligible. Comments are non-executing.

## Exit criteria

- [ ] All three `.mjs` files start with `// @ts-check`.
- [ ] `npx tsc --noEmit --allowJs --checkJs scripts/*.mjs ...` is 0 errors.
- [ ] No behavior change.
