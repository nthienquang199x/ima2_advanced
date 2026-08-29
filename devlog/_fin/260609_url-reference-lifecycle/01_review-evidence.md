---
created: 2026-06-09
tags: [ima2-gen, url-continue, provider-url-reference, review, verification]
---

# URL Reference Lifecycle Review Evidence

## Scope

Goal: keep the prompt-side URL reference indicator stable while unrelated image
selection or generation completion occurs, prevent stale provider URLs from
overriding later local reference choices, and review the recent URL continue
flow with PABCD/dev discipline.

Project root used for all commands and audits:

```text
/Users/jun/Developer/new/700_projects/ima2-gen
```

## PABCD Evidence

| Phase | Evidence |
|---|---|
| P | `00_plan.md` documents the root cause, planned source changes, test changes, and browser verification steps. |
| A | Independent read-only lifecycle audit found generation cleanup clears as the root cause and confirmed removing them was sufficient for the disappearing badge symptom. |
| A follow-up | Independent read-only code review found an additional stale-source risk: keeping URL refs indefinitely would let normal `Continue here` be overridden by an older URL ref. |
| B | Implemented stable lifecycle: generation cleanup no longer clears provider URL refs; explicit local reference paths clear stale URL refs; `URL continue` restores provider URL after normal continue setup. |
| B verification | Independent read-only implementation verifier returned `DONE`: source, tests, and plan matched the intended lifecycle. |
| C | Fresh automated checks passed: targeted node tests, server typecheck, test typecheck, full test suite, UI build, server build, and `git diff --check`. |
| D | Browser verification confirmed the user-visible lifecycle: `URL continue` shows the badge, current-image transition and concurrent generation completion preserve it, normal `Continue here` clears it. |

## Dev-Skill Review

### dev / architecture

- Scope remained within the existing React/Zustand frontend architecture.
- No new abstraction or module was introduced.
- The state owner remained `useAppStore` and its existing store slices.
- Existing request precedence was preserved: generation sends `providerUrl` when
  `providerUrlReference` is set; otherwise it sends local `references`.

### dev-frontend

- The existing prompt composer badge surface was reused.
- The URL reference remains visible in the prompt header while active.
- The badge is an accessible button with a clear aria label.
- Browser verification used the local app rather than source-only inspection.

### dev-testing

- Contract tests cover the lifecycle in source:
  - generation cleanup does not clear `providerUrlReference`;
  - video cleanup does not clear `providerUrlReference`;
  - local reference paths clear stale URL refs;
  - URL continue restores provider URL after normal continue setup.
- Browser verification covers the user-visible state transitions.

### dev-debugging

- Root cause was traced to cleanup paths clearing shared state, not to rendering.
- A second audit caught the derived stale-source bug before stop.
- The fix separates automatic completion cleanup from explicit user intent.

### dev-code-reviewer

- Main correctness risk found: a stale URL ref could override a later normal
  local reference. This was fixed before completion.
- No security-sensitive surface or new external dependency was added.
- Remaining known untracked path, `ui/mock/`, is unrelated and was not modified.

## Implementation Evidence

- `ui/src/store/storeGenImpl.ts`
  - Multimode and classic generation cleanup no longer clear `providerUrlReference`.
- `ui/src/store/storeVideoImpl.ts`
  - Video generation cleanup no longer clears `providerUrlReference`.
- `ui/src/store/storeReferenceImpl.ts`
  - File/local/canvas/current-image reference paths clear stale URL refs.
- `ui/src/store/storeUIImpl.ts`
  - Data URL reference path clears stale URL refs.
- `tests/direct-mode-visual-contract.test.js`
  - Adds lifecycle contract coverage.
- `tests/video-continuity-ui-contract.test.js`
  - Updates clear-reference contract to include URL refs.

## Verification Evidence

Fresh continuation checks:

```text
node --test tests/direct-mode-visual-contract.test.js tests/video-continuity-ui-contract.test.js
Result: 10 tests, 2 suites, 10 pass, 0 fail.
```

```text
npm run typecheck
Result: exit 0.
```

```text
cd ui && npm run build
Result: exit 0. Existing Vite chunk-size warning only.
```

```text
npm run build:server
Result: exit 0.
```

Earlier full-suite check in this goal:

```text
npm test
Result: 988 tests, 131 suites, 988 pass, 0 fail.
```

Browser verification:

```text
Local app: http://127.0.0.1:3463
Selected image: 1780932242327_b70a1630_0.jpeg
Clicked URL continue: .composer__url-ref-badge appeared with text "URL ref".
Clicked current-image next: .composer__url-ref-badge remained while active generation count changed from 10 to 9.
Clicked normal Continue here: .composer__url-ref-badge disappeared and only "Refs 1/5" remained.
```

Git evidence:

```text
509bdc0 fix: stabilize URL reference lifecycle
```

`git status --short --branch` after commit showed only the pre-existing
untracked `ui/mock/` path.
