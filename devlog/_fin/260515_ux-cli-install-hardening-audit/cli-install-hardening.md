---
title: "CLI And Install Hardening Details"
status: planned / issue split complete
created: 2026-05-15
tags: [cli, packaging, install, postinstall, release, agent-ux]
---

# CLI And Install Hardening Details

## Lane A — Agent Discovery Completeness

Priority: P1

Related issues:

- #62 (closed as shipped)
- #64

### Problem

`ima2 capabilities --json` exists, but it does not yet expose every validation
enum an agent needs to choose flags safely without reading each command help
screen.

Current capabilities expose:

- supported/unsupported image models;
- reasoning efforts;
- quality values;
- reference/image limits;
- advisory max parallel metadata.

Missing or weakly surfaced values:

- `mode`: `auto | direct`
- `moderation`: `auto | low`
- `provider`: `auto | oauth | api`
- size policy/defaults
- writable config keys and env override mapping

Anchors:

- `lib/capabilities.ts:38-83`
- `bin/commands/gen.ts`
- `bin/commands/edit.ts`
- `bin/commands/multimode.ts`
- `bin/commands/node.ts`
- `bin/lib/config-store.ts`

### Recommended Diff Direction

Add to `buildIma2Capabilities(...)`:

```ts
valid: {
  imageModels: { supported, unsupported },
  reasoningEfforts,
  quality,
  modes: ["auto", "direct"],
  moderation: ["auto", "low"],
  providers: ["auto", "oauth", "api"]
}
```

Add a discoverable config key layer:

- option A: `ima2 config keys --json`;
- option B: `capabilities.writableConfigKeys` and `capabilities.envOverrides`.

Preferred:

- Add `ima2 config keys --json` for local config-specific discovery.
- Add a pointer in `capabilities.guidance.config`.

### Tests

- Extend `tests/cli-capabilities-contract.test.js`.
- Add a contract that `mode`, `moderation`, `provider`, and config key discovery
  are present.

### Issue

```text
#64 CLI/Skill: harden agent discovery, help, and command examples
```

## Lane B — Top-Level Help And Skill Examples

Priority: P1

Related issues:

- #62 (closed as shipped)
- #64

### Problem

Top-level help is agent-friendly, but agents still need `docs/CLI.md` for global
discovery details:

- `--server <url>`
- `IMA2_SERVER`
- `IMA2_CONFIG_DIR`
- `IMA2_GENERATED_DIR`
- `IMA2_CARD_NEWS`
- `IMA2_LOG_LEVEL`
- `~/.ima2/server.json` discovery

Anchors:

- `bin/ima2.ts:312-368`
- `docs/CLI.md:18-41`
- `docs/CLI.md:213-246`

`skills/ima2/SKILL.md` can also use worked examples for:

- multimode SSE events;
- `ima2 inflight ls --json` inspection;
- `ima2 history import <file>`;
- `ima2 storage status --json`;
- server-not-running recovery.

Anchors:

- `skills/ima2/SKILL.md:19-41`
- `skills/ima2/SKILL.md:84-120`
- `bin/commands/history.ts:110-131`
- `bin/commands/observability.ts`

### Recommended Diff Direction

Modify `bin/ima2.ts` top-level help:

```text
  Common client discovery:
    --server <url>       Override server URL on client commands
    IMA2_SERVER          Env server URL override
    ~/.ima2/server.json  Written by running server

  Useful env:
    IMA2_CONFIG_DIR
    IMA2_GENERATED_DIR
    IMA2_CARD_NEWS=1
    IMA2_LOG_LEVEL
```

Modify `skills/ima2/SKILL.md`:

- add `Watching Jobs` section;
- add `History Import` section;
- add multimode event explanation:
  `phase -> partial -> image -> done/error`.

### Tests

- Extend `tests/bin.test.js` help assertions.
- Extend `tests/cli-skill-command-contract.test.js`.

### Issue

```text
#64 CLI/Skill: harden agent discovery, help, and command examples
```

## Lane C — CLI Route Parity Edges

Priority: P1

### C1. `ima2 edit --mask`

Related issue:

- #31

Server edit route validates optional masks. CLI still defers `--mask` until
provider-backed masked edit semantics are verified.

Anchors:

- `routes/edit.ts`
- `docs/CLI.md:84`
- `docs/CLI.md:189-191`

Decision:

- Keep deferred under #31.
- When #31 lands, include CLI `ima2 edit <file> --prompt <text> --mask <png>`.
- Do not expose this earlier as a prompt-only/guided-edit alias.

### C2. Prompt Import Single-Record CLI

Server exposes prompt import surfaces that are only partially represented in CLI
ergonomics. The current CLI has curated/discovery/folder flows, but
single-record JSON import and generic preview are not obvious from CLI alone.

Anchors:

- `routes/promptImport.ts:106-146`
- `routes/promptImport.ts:148-199`
- `bin/commands/prompt.ts:25-31`
- `bin/commands/prompt.ts:282-287`

Recommended split:

```text
#70 CLI: add prompt import JSON and preview wrappers for non-folder workflows
```

### C3. Node Edit/Cancel

Current CLI and server are aligned. The server has node generate/show surfaces,
not a separate node edit/cancel endpoint.

Decision:

- No issue now.
- Revisit only if server adds node edit/cancel endpoints.

### C4. Canvas Version List/Delete

Current CLI notes that the server only exposes save/update behavior.

Decision:

- No CLI-only issue.
- If users ask for list/delete, add server and CLI together.

## Lane D — Destructive CLI UX

Priority: P2

### Problem

Most destructive commands use confirmation or `--yes`, but local config commands
are sharper:

- `ima2 reset` rewrites the config file without confirmation;
- `ima2 config rm` removes config keys without confirmation;
- config file permissions are not surfaced in `doctor`.

Anchors:

- `bin/ima2.ts:403-410`
- `bin/commands/config.ts`
- `bin/commands/history.ts:60-78`
- `bin/commands/prompt.ts:165-178`

### Recommended Diff Direction

Add confirmation parity:

- `ima2 reset --yes`
- `ima2 config rm <key> --yes`
- TTY prompt for interactive use.
- non-TTY requires `--yes`.

Add doctor warning:

- if `~/.ima2/config.json` contains sensitive keys and is group/other-readable
  on POSIX, show warning;
- skip or degrade gracefully on Windows.

### Issue

```text
#66 CLI: add destructive command confirmations and doctor/status hardening
```

## Lane E — Doctor / Status Hardening

Priority: P2

### Problem

`ima2 doctor` and `ima2 status` can expose more actionable support details:

- preferred port is printed but not actively probed;
- Card News effective feature value is not obvious;
- `ima2 status` does not show generated directory;
- `doctor` could show whether package skill/capabilities commands are present.

Anchors:

- `bin/ima2.ts:190-300`
- `docs/CLI.md:135-150`
- `structure/06-infra-operations.md:83`

### Recommended Diff Direction

Add to `doctor`:

- preferred server port availability check;
- effective Card News status and source;
- skill file/package integrity hint;
- config permission warning from Lane D.

Add to `status`:

- generated directory path;
- advertised server URL when present;
- current package skill path.

### Issue

```text
#66 CLI: add destructive command confirmations and doctor/status hardening
```

## Lane F — Package And Release Hardening

Priority: P2

### Problem

Publish gates are strong, but package hygiene has holes:

- `package.json` declares MIT but no root `LICENSE` file is present;
- `test:package-install` is available but should be considered for more CI
  matrix coverage;
- `npm publish --dry-run` is not a distinct CI step;
- release scripts publish/push and should refuse dirty or pre-staged worktrees
  before doing anything irreversible.

Anchors:

- `package.json:21-23`
- `package.json:24-26`
- `package.json:39`
- `package.json:44-61`
- `tests/package-install-smoke.mjs:80-204`
- `.github/workflows/ci.yml`
- `scripts/release.sh`
- `scripts/release-preview.sh`

### Recommended Diff Direction

Add root `LICENSE`:

- MIT text matching `package.json:39`;
- include `"LICENSE"` in `files[]`;
- assert in `lint:pkg`.

Improve CI/package smoke:

- add explicit `npm publish --dry-run` on ubuntu/node22 or a release-gate job;
- consider running `test:package-install` on Windows matrix, since the smoke test
  already has `npm.cmd` handling.

Harden release scripts:

- refuse dirty worktree;
- refuse staged changes;
- print exact package version and tarball before publish;
- keep `release:*` scripts forbidden for agents unless user explicitly requests.

### Issue

```text
#67 Packaging: add LICENSE, publish dry-run, and release-script guards
```

## Lane G — Postinstall Policy

Priority: P3 / policy record

### Conclusion

Do not add `postinstall`, `preinstall`, or `prepare` for normal package users.

Rationale:

- install scripts are often disabled by `--ignore-scripts`, so core behavior
  must not depend on them;
- writing to `~/.ima2` during install would create hidden side effects;
- OAuth/config checks belong in `ima2 setup`, `ima2 doctor`, and first-run
  `ima2 serve`, not package installation;
- UI/server/CLI artifacts are already prepared by `prepack`.

Anchors:

- `package.json:9-31`
- `bin/ima2.ts:143-145`
- `tests/package-install-smoke.mjs:80-204`

Allowed future exception:

- A no-op informational postinstall would be low risk but low value. It should
  still be avoided unless users repeatedly fail first-run discovery.

Recommended record:

```text
Lifecycle policy: ima2-gen intentionally has no postinstall; use doctor/setup/prepack/package smoke instead
```

## Lane H — Parallel Queue / Inflight Semantics

Priority: P2

Related issue:

- #60 (closed as shipped)
- #69

### Problem

`limits.maxParallel` is intentionally advisory:

- `lib/capabilities.ts` reports `enforced: false`;
- `skills/ima2/SKILL.md` says there is no `--parallel` flag and agents should
  submit several normal jobs.

This is honest, but if future UX needs a real queue, it should become explicit
instead of implied.

Anchors:

- `lib/capabilities.ts:71-74`
- `skills/ima2/SKILL.md:91-107`
- `routes/health.ts`
- `bin/commands/observability.ts`

### Recommended Diff Direction

Do not silently treat `maxParallel` as enforced.

If needed later:

- add an opt-in server semaphore;
- expose `queueReason`;
- include `queuePosition` or `blockedBy` in `/api/inflight`;
- document in CLI and skill.

### Issue Candidate

```text
Server: optionally enforce maxParallel and expose queueReason via inflight APIs
```
