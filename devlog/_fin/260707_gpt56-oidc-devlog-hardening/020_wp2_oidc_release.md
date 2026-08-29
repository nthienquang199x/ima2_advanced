# WP2 — OIDC release transition (local flow stops direct `npm publish`)

Production publishing already runs through `.github/workflows/publish.yml`
(npm trusted publishing / OIDC): GitHub Release → `latest`, `preview` branch
push → `preview` dist-tag, with npm >= 11.5.1 + OIDC endpoint preconditions.
The remaining gap: local tooling still performs credentialed `npm publish`.

## File change map

- `.github/workflows/publish.yml` (plan amendment from audit blocker #1)
  - Release path gains a tag/version guard before publish: fail unless
    `github.event.release.tag_name == "v" + package.json.version`. Without it a
    mismatched Release would publish the checked-out version as `latest`,
    contradicting the documented contract in structure/06.
- `package.json`
  - `release:patch|minor|major`: replace
    `npm version X && npm publish && git push origin main --tags` with
    `./scripts/release.sh patch|minor|major` (single entry point; script owns
    collision handling and ends at `gh release create`).
- `scripts/release.sh`
  - Drop the `npm whoami` preflight (no npm credentials needed locally);
    require `command -v gh` AND `gh auth status` BEFORE any irreversible
    step (audit blocker #4).
  - Remove the `npm publish --access public` step entirely.
  - Keep: worktree-clean check, version detection/bump, build, commit, tag,
    push commit+tag, `gh release create` (now REQUIRED, not best-effort —
    the Release event is what triggers the OIDC publish). New safe order
    (audit blocker #3): commit -> tag -> push commit+tag -> gh release create;
    the old "publish before tag push" rationale inverts under OIDC.
  - End with a pointer to the Actions run:
    `gh run list --workflow=publish.yml --limit 1` hint + release URL.
- `structure/06-infra-operations.md`
  - §npm Publish (OIDC): state local `release.sh` is now a release-trigger
    only (no direct publish path remains); update the 2026-06-27 note with a
    2026-07-07 entry.
- `docs/README.ko.md` — refresh the OIDC line if it still implies local publish.
- `CHANGELOG.md` — Unreleased entry: local release flow now OIDC-only.

## Accept criteria

- `rg -n "npm publish" package.json scripts/release.sh` → only hits inside
  comments or the preview note, none executable in the local path.
- `bash -n scripts/release.sh` exits 0.
- publish.yml release path contains the version/tag guard (yaml read-back).
- typecheck/typecheck:tests/test/test:inventory stay green (no src changes).

## Audit synthesis (A, 2026-07-07, reviewer: gpt-5.5 explorer)

Verdict FAIL → blockers #2/#3 confirm the planned removal + ordering flip
(accepted, already in scope); #1 (publish.yml missing tag/version guard) and
#4 (gh auth preflight) are new and ACCEPTED as plan amendments above.
publish.yml is no longer out-of-scope: the guard is required to make the
Release-triggered path safe. Reviewer confirmed collision_check survives
(npm view is unauthenticated), no tests pin release script bodies, and
generate-release-notes.mjs stays.

## Out of scope

- Running a release; touching `publish.yml` (already correct); npm tokens.
