# P11 — Build artifact layout: move `outDir` to `dist/`

**Goal:** Consolidate emitted `.js` artifacts under `dist/` instead of co-located with sources. Final cleanup so `git status` and source navigation are clean. Resolves the "long-term TS source + JS runtime artifact strategy" half of issue #24.

**Effort:** M
**Owner:** Boss writes; sub-agent (`claude-opus-4.7`) verifies path string sweeps; GPT Pro audits npm `bin` resolution.
**Depends on:** P09 (decoupled, but lower-risk to land after strict work is done so blast surface is smaller).

---

## Why

**Today:**
- `tsconfig.build.json` and `tsconfig.bin.json` both `outDir: "."`, `rootDir: "."`.
- `.js` is gitignored but emitted next to each `.ts`. `git status` is noisy after a build.
- `package.json files[]` whitelists each emit directory: `bin/`, `lib/`, `routes/`, `server.js`, `config.js`.
- Three runtime path couplings (verified in inventory section 4):
  1. `package.json` `"bin": { "ima2": "./bin/ima2.js" }`.
  2. `bin/ima2.ts:177` does `join(ROOT, "server.js")` and spawns Node on it. **Critical path.**
  3. `scripts/dev.mjs:29` `node --watch server.js`; `scripts/fix-shebangs.mjs:26` writes shebang to `join("bin","ima2.js")`.

**Goal state:** all emit goes to `dist/`. `bin.ima2 → ./dist/bin/ima2.js`. Sources stay where they are. `.gitignore` simplifies to `/dist/`.

## Scope

**NEW:** `dist/` directory (build output; gitignored).

**MODIFY:**
- `tsconfig.build.json` — `outDir: "dist"`.
- `tsconfig.bin.json` — `outDir: "dist"`.
- `package.json` — `bin`, `files`, `start`, `setup`, `lint:pkg`, `prepack` order if needed.
- `bin/ima2.ts:177` (or, if P08 landed, `bin/commands/serve.ts`) — `serverPath` resolution.
- `scripts/dev.mjs` — `dev` script (already has `dev:server` using tsx — see below).
- `scripts/fix-shebangs.mjs` — `BIN_DIR`.
- `.gitignore` — collapse to single `/dist/` entry.

## Diff highlights

### `tsconfig.build.json`
```json
 {
   "extends": "./tsconfig.json",
   "compilerOptions": {
     "noEmit": false,
-    "outDir": ".",
-    "rootDir": ".",
+    "outDir": "dist",
+    "rootDir": ".",
     "declaration": false,
     "sourceMap": false,
     "removeComments": false,
     "allowJs": false
   },
   ...
 }
```
With `rootDir: "."` and `outDir: "dist"`, `lib/foo.ts` emits to `dist/lib/foo.js`. `server.ts` → `dist/server.js`. `routes/x.ts` → `dist/routes/x.js`. ✅ (verify with `npm run build:server && find dist -type f -name '*.js' | head`)

### `tsconfig.bin.json`
```json
   "compilerOptions": {
     "noEmit": false,
-    "outDir": ".",
-    "rootDir": ".",
+    "outDir": "dist",
+    "rootDir": ".",
     ...
```
`bin/ima2.ts` → `dist/bin/ima2.js`. `bin/commands/x.ts` → `dist/bin/commands/x.js`.

### `package.json`
```diff
   "bin": {
-    "ima2": "./bin/ima2.js"
+    "ima2": "./dist/bin/ima2.js"
   },
   "scripts": {
-    "start": "node bin/ima2.js serve",
+    "start": "node dist/bin/ima2.js serve",
     "dev": "node scripts/dev.mjs",
     "dev:server": "tsx watch server.ts",
     ...
-    "setup": "node bin/ima2.js setup",
+    "setup": "node dist/bin/ima2.js setup",
     "prepack": "npm run ui:build && npm run build:server && npm run build:cli",
-    "lint:pkg": "node -e \"const p=require('./package.json'); const req=['name','version','bin']; for(const k of req){if(!p[k])throw new Error('missing '+k)} const mustInclude=['bin/','lib/','routes/','integrations/comfyui/ima2_gen_bridge/__init__.py','integrations/comfyui/ima2_gen_bridge/nodes.py','integrations/comfyui/ima2_gen_bridge/README.md','assets/card-news/templates/','server.js']; for(const f of mustInclude){if(!p.files.includes(f))throw new Error('files[] must include '+f)}\""
+    "lint:pkg": "node -e \"const p=require('./package.json'); const req=['name','version','bin']; for(const k of req){if(!p[k])throw new Error('missing '+k)} const mustInclude=['dist/','integrations/comfyui/ima2_gen_bridge/__init__.py','integrations/comfyui/ima2_gen_bridge/nodes.py','integrations/comfyui/ima2_gen_bridge/README.md','assets/card-news/templates/']; for(const f of mustInclude){if(!p.files.includes(f))throw new Error('files[] must include '+f)}\""
   },
   "files": [
-    "bin/",
-    "lib/",
-    "routes/",
+    "dist/",
     "integrations/comfyui/ima2_gen_bridge/__init__.py",
     "integrations/comfyui/ima2_gen_bridge/nodes.py",
     "integrations/comfyui/ima2_gen_bridge/README.md",
     "ui/dist/",
     "docs/",
     "assets/card-news/templates/",
-    "server.ts",
-    "config.ts",
     ".env.example",
-    "README.md",
-    "server.js",
-    "config.js"
+    "README.md"
   ],
```
> Removed `server.ts` and `config.ts` from `files[]` — they were dead weight in the published tarball (the published `dist/bin/ima2.js` only spawns `dist/server.js`, not the TS source).

### `bin/ima2.ts:177` (or `bin/commands/serve.ts` if P08-bin landed)
The current code does roughly:
```ts
const serverPath = join(ROOT, "server.js");
spawn(process.execPath, [serverPath, ...args], { ... });
```
After:
```ts
// Resolve published-vs-dev:
//   - In published tarball: __dirname is .../node_modules/ima2-gen/dist/bin
//     → server lives at ../../dist/server.js relative to here.
//   - In dev (running via tsx): __dirname is .../ima2-gen/bin (TS source)
//     → server.ts lives at ../server.ts; we use tsx to load it.
import { fileURLToPath } from "node:url";
import { existsSync } from "node:fs";

const here = fileURLToPath(new URL(".", import.meta.url));
const distServer = join(here, "..", "..", "dist", "server.js");
const distServerSibling = join(here, "..", "server.js");      // when running compiled bin from dist/bin
const devServer = join(here, "..", "server.ts");              // when running source via tsx

let serverEntry: string;
let extraNodeArgs: string[] = [];
if (existsSync(distServerSibling)) {
  serverEntry = distServerSibling;
} else if (existsSync(distServer)) {
  serverEntry = distServer;
} else if (existsSync(devServer)) {
  serverEntry = devServer;
  extraNodeArgs = ["--import", "tsx"];
} else {
  throw new Error("ima2: cannot locate server.js or server.ts");
}

spawn(process.execPath, [...extraNodeArgs, serverEntry, ...args], { ... });
```
> The two `dist`-side branches handle (a) published tarball where `bin/ima2.js` is at `dist/bin/ima2.js` (sibling lookup hits `dist/server.js`), (b) ad-hoc invocations from project root after `npm run build:server`. The `devServer` branch is for `tsx`-based dev where no emit exists.

### `scripts/dev.mjs`
The current `dev.mjs` spawns `node --watch server.js`. After move:
- Either keep `dev.mjs` orchestrating a build first, then watching `dist/server.js`.
- Or simpler: route `npm run dev` to invoke `tsx watch server.ts` (the existing `dev:server` script). Drop `dev.mjs` use.

```diff
   "scripts": {
     "start": "node dist/bin/ima2.js serve",
-    "dev": "node scripts/dev.mjs",
+    "dev": "npm run ui:build && tsx watch server.ts",
     "dev:server": "tsx watch server.ts",
```
Then `scripts/dev.mjs` can be deleted (or kept for any orchestration the team wants).

### `scripts/fix-shebangs.mjs`
```diff
- const BIN_DIR = join("bin");
+ const BIN_DIR = join("dist", "bin");
```
Plus the entrypoint string update for the shebang target.

### `.gitignore`
```diff
 ui/dist/
 ui/tsconfig.app.tsbuildinfo
 ui/tsconfig.node.tsbuildinfo
 __pycache__/
 *.pyc

-# TS build emit artifacts (generated by build:server / build:cli)
-/server.js
-/config.js
-/lib/**/*.js
-/routes/**/*.js
-/bin/ima2.js
-/bin/commands/*.js
-/bin/lib/*.js
+# TS build emit artifacts (generated by build:server / build:cli)
+/dist/
```

### tsconfig consolidation (optional)
With both build configs writing to `dist/`, you can collapse them into one `tsconfig.build.json` by including bin:
```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "noEmit": false,
    "outDir": "dist",
    "rootDir": ".",
    "declaration": false,
    "allowJs": false
  },
  "include": ["server.ts", "config.ts", "lib/**/*.ts", "routes/**/*.ts", "bin/**/*.ts", "types/**/*.ts"],
  "exclude": ["node_modules", "ui", "tests", "scripts", "integrations", "**/*.test.ts", "**/*.d.ts"]
}
```
Then in `package.json`:
```diff
- "build:server": "tsc -p tsconfig.build.json",
- "build:cli": "tsc -p tsconfig.bin.json && node scripts/fix-shebangs.mjs",
+ "build": "tsc -p tsconfig.build.json && node scripts/fix-shebangs.mjs",
```
**Defer this consolidation** — keep the two configs separate in P11 to minimize delta. Optional follow-up PR.

## Verify

```bash
# Clean slate
rm -rf dist
npm run build:server && npm run build:cli
ls dist/             # bin/  config.js  lib/  routes/  server.js
ls dist/bin/         # commands/  ima2.js  lib/
file dist/bin/ima2.js   # confirm has #!/usr/bin/env node shebang

npm run typecheck
npm test                       # 539/539
npm run lint:pkg               # uses new mustInclude=['dist/', ...]

# Local install smoke (most important — exercises bin resolution)
npm run test:package-install   # publishes a tarball, installs, runs `ima2 --help`

# Boot smoke
npm start &
PID=$!
sleep 3
curl -s localhost:11783/api/health | jq .
kill $PID
```

## GPT Pro audit (mandatory gate before merge)

```bash
agbrowse web-ai query --vendor chatgpt --model pro --inline-only --prompt "$(cat <<'EOF'
Audit ima2-gen P11 (move build emit from co-located to dist/).

Key concerns:
1. Does this resolution chain in bin/ima2.ts cover all real-world install scenarios?
   - npm install -g ima2-gen → __dirname = .../node_modules/ima2-gen/dist/bin
   - npx ima2-gen → cached tarball under ~/.npm/_npx
   - direct git clone + npm run build → project root with dist/
   - tsx-based dev (no dist) → fallback to server.ts
   [paste the resolution code]

2. Is `files: ["dist/", ...]` correct? Does dropping server.ts/config.ts from files[] break any consumer? Are there any consumers that rely on TS source being shipped?

3. The `lint:pkg` mustInclude rewrite — is "dist/" enough or should we list "dist/server.js", "dist/bin/ima2.js" explicitly to catch incomplete build?

4. Any reason to keep outDir: "." for one of the two configs?

5. Anything missing for cross-platform Windows path handling in the new resolver?
EOF
)" --json
```

## Risk

- **High** if the `serverPath` resolution chain misses an install scenario. **Always run `npm run test:package-install` before merging.**
- **Medium** for `lint:pkg`: a typo in mustInclude could let a broken tarball ship.
- **Trap:** `npm publish` from a checkout that has stale co-located `.js` files (left over from before the move) will pack both old and new layouts. Add to PR: a one-time manual `git clean -fdx` recipe.

## Rollback

Single revert. The change touches several files but is one logical unit.

## Exit criteria

- [ ] `tsconfig.build.json` and `tsconfig.bin.json` both `outDir: "dist"`.
- [ ] `npm run build:server` produces `dist/server.js`, `dist/lib/...`, `dist/routes/...`, `dist/config.js`.
- [ ] `npm run build:cli` produces `dist/bin/ima2.js` (with shebang) and `dist/bin/commands/*.js`, `dist/bin/lib/*.js`.
- [ ] `package.json` `bin.ima2` = `./dist/bin/ima2.js`.
- [ ] `package.json files[]` lists `dist/` (and removes the per-directory entries).
- [ ] `npm run lint:pkg` passes with new mustInclude.
- [ ] `npm run test:package-install` passes — verifies the published tarball boots `ima2 --help` correctly.
- [ ] `git status` after build is clean (no co-located `.js` artifacts).
- [ ] GPT Pro audit returns no critical issues.
