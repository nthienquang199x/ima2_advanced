# AGY Provider PR Integration Plan

## Goal
Merge two external PR contributions (#107, #106) into dev→main via sequential PABCD cycles.

## Current State
- **dev** is 1 commit ahead of main (size directive feature `81d19be`)
- **PR #107** `codex/agy-bin-resolution` (GSL-R) — DRAFT, approved by review
  - New `lib/agyCli.ts` module centralizing agy binary resolution
  - Fixes server PATH not finding `~/.local/bin/agy`
  - 6 files, +97/-3, tests included
- **PR #106** `fix/agy-artifact-fallback` (lekthailtd-bit) — needs changes
  - Adds `findRecentAgyArtifact()` fallback when CLI stdout is not captured
  - 1 file (`agyImageAdapter.ts`), +68/-1, **no tests**
  - Blockers: (a) no test coverage, (b) symlink traversal in walk()

## Conflict Analysis
Both PRs modify `lib/agyImageAdapter.ts`:
- #107: adds `import { buildAgyPathEnv, resolveAgyBin }` + changes `spawnAgy()` spawn call
- #106: adds `findRecentAgyArtifact()` function + modifies `generateViaAgy()`
- **Different sections** — merge conflicts will be in the import area and spawn area only

## Phase 1: PR #107 (approved, clean merge)

### Steps
1. Fetch `codex/agy-bin-resolution` branch
2. Merge into `dev` (FF or merge commit)
3. Verify: typecheck + full test suite
4. Merge `dev` → `main` via PR or FF
5. Push both branches, close PR #107

### Files Affected
- `lib/agyCli.ts` (NEW)
- `lib/agyImageAdapter.ts` (MODIFY — import + spawnAgy)
- `routes/agy.ts` (MODIFY — import + resolveAgyBin call)
- `tests/agy-cli.test.ts` (NEW)
- `CHANGELOG.md` (MODIFY)
- `docs/CLI.md` (MODIFY)

## Phase 2: PR #106 (fix blockers, then merge)

### Blocker Fixes Required
1. **Add test coverage** for `findRecentAgyArtifact()`:
   - Unit test with temp dir containing matching/non-matching files
   - Test time window filtering (sinceMs)
   - Test depth limit
   - Test graceful handling of unreadable dirs

2. **Fix symlink traversal** in `walk()`:
   - Replace `entry.isDirectory()` with `!entry.isSymbolicLink() && entry.isDirectory()`
   - Prevents following symlinks outside `~/.gemini` during recursive walk

### Steps
1. Checkout `fix/agy-artifact-fallback` branch
2. Rebase onto current dev (resolve conflicts from #107's changes)
3. Apply blocker fixes (symlink guard + tests)
4. Verify: typecheck + full test suite
5. Merge into `dev`
6. Merge `dev` → `main` via PR or FF
7. Push, close PR #106

### Files Affected
- `lib/agyImageAdapter.ts` (MODIFY — symlink guard in walk())
- `tests/agy-artifact-fallback.test.ts` (NEW — test coverage)

## Verification
- `npm run typecheck` clean at each merge point
- `npm test` all pass at each merge point
- Git log linear (FF where possible)
