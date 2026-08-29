# Phase 2: PR #106 — agy artifact fallback recovery

## Result: MERGED (with blocker fixes)

### Blockers resolved
1. **Symlink traversal** — `walk()` in `findRecentAgyArtifact` followed symlinks via `entry.isDirectory()`. Fixed by adding `!entry.isSymbolicLink()` guard to skip symlinks during directory traversal.

2. **No test coverage** — Added 8 unit tests in `tests/agy-artifact-fallback.test.ts`:
   - Time window filtering (match / reject stale)
   - Filename pattern filtering
   - Subdirectory recursive discovery
   - Depth limit enforcement (>5 levels ignored)
   - Symlink blocking verification
   - Newest-first sort when multiple candidates
   - Empty/missing directory graceful handling

### What was done
- Fetched `fix/agy-artifact-fallback` branch from fork (lekthailtd-bit / Tom Smith)
- Rebased onto current `dev` (clean, no conflicts)
- Applied blocker fixes (symlink guard + test file)
- Exported `findRecentAgyArtifact` with optional `rootOverrides` param for testability
- Verified: typecheck clean, 1053 tests pass (+8 new)
- FF merged into `dev`, then `dev` → `main`, pushed both
- PR #106 manually closed with contribution acknowledgment

### Files added/modified
- `lib/agyImageAdapter.ts` (MODIFY) — symlink guard, export + rootOverrides param
- `tests/agy-artifact-fallback.test.ts` (NEW) — 8 unit tests
