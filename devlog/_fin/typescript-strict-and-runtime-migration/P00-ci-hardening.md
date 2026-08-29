# P00 — CI hardening: add `typecheck` + build steps

**Goal:** Surface TS regressions in CI before they merge. Without this, Phases P01–P09 are invisible to PR checks.

**Effort:** XS (≤30 min)
**Owner:** Boss (direct edit). No sub-agent needed.
**Depends on:** —
**Unblocks:** every subsequent phase.

---

## Why

Current `.github/workflows/ci.yml` runs `npm test` + `lint:pkg` only. `npm run typecheck` and `tsc -p tsconfig.build.json` are never invoked on PRs. As soon as P01 enables a strict flag, a developer who runs only `npm test` locally won't catch a regression. This phase adds the missing gates.

## Scope

**MODIFY:** `.github/workflows/ci.yml` (1 file)

## Diff

```yaml
# .github/workflows/ci.yml — full file after change
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: test (${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - name: Install root deps
        run: npm ci
      - name: Install ui deps
        run: npm --prefix ui install --no-audit --no-fund
+     - name: Typecheck
+       run: npm run typecheck
+     - name: Build server (tsc emit)
+       run: npm run build:server
+     - name: Build cli (tsc emit)
+       run: npm run build:cli
      - name: Build ui
        run: npm --prefix ui run build
      - name: Run tests
        run: npm test
        timeout-minutes: 3
      - name: Lint package.json
        if: matrix.os == 'ubuntu-latest'
        run: npm run lint:pkg
+     - name: Package install smoke
+       if: matrix.os == 'ubuntu-latest'
+       run: npm run test:package-install
```

**Why this order:** typecheck is fast-fail (no emit), runs first. `build:server` + `build:cli` ensure tsc actually emits. `npm test` then runs against fresh emit. `test:package-install` validates the published-tarball flow end-to-end (currently only invoked by `prepublishOnly`).

## Verify (locally before PR)

```bash
cd /Users/jun/Developer/new/700_projects/ima2-gen
npm run typecheck      # must pass (baseline already green)
npm run build:server   # emits .js next to .ts in lib/, routes/, server.js, config.js
npm run build:cli      # emits bin/**/*.js
npm test               # 539/539
npm run lint:pkg
npm run test:package-install
```

After PR merges, intentionally introduce a `: number = "x"` somewhere in `lib/`, push to a throwaway branch, confirm CI fails on the typecheck step. Revert.

## Risk

- **Low.** Adds steps; doesn't change existing steps.
- Build steps require `node_modules` (already installed by `npm ci`). No new deps.
- Windows path issues: `tsc` is cross-platform; verified by current `prepublishOnly` working on developer machines.

## Rollback

`git revert <SHA>` of the single CI workflow commit.

## Exit criteria

- [ ] `.github/workflows/ci.yml` has 5 new steps in the order above.
- [ ] PR CI run is green on both ubuntu and windows.
- [ ] A deliberate type error in a draft PR fails the new `Typecheck` step (probe-and-revert).
- [ ] No change to test count (539/539).
