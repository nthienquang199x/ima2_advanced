# P04 — Split `lib/oauthProxy.ts` (1003 → 8 files)

**Goal:** Decompose the only file violating the project's 500-line rule. Each piece becomes independently testable and strict-mode-rollable.

**Effort:** M (1–2 PRs; recommend 2 — first the structural split as a no-op, second any signature changes that emerge.)
**Owner:** Boss writes the split; sub-agent (`claude-opus-4.7`) for the mechanical move; GPT Pro verifies barrel re-export preserves all public symbols.
**Depends on:** P00 (CI gate); independent of strict flag work.

---

## Why

- 1,003 LOC violates `Max 500 lines per file. Exceed → split` rule.
- 60 of 1,205 `noImplicitAny` errors live here (5%) — the highest single-file count.
- 21 of 222 `: any` annotations live here (9.5%).
- File is the SSE-streaming, prompt-building, and error-mapping core for OAuth-mode generation. Touching it is high-risk; splitting first reduces blast radius for every later phase.

## Scope

**NEW (8 files in `lib/oauthProxy/`):**

| New file | Contents (line ranges in current `oauthProxy.ts`) | Est LOC |
|---|---|---|
| `lib/oauthProxy/prompts.ts` | `REAL_PERSON_RESEARCH_DIRECTIVE`, all `*_DEVELOPER_PROMPT`, `*_FIDELITY_SUFFIX`, `buildUserTextPrompt`, `buildMultimodeSequencePrompt`, `buildEditTextPrompt`, `buildEditResearchTextPrompt` (lines 38–135) | ~140 |
| `lib/oauthProxy/errors.ts` | `makeOAuthError`, `parseOpenAIErrorBody`, `normalizedOAuthCode`, `throwOAuthHttpError`, `isAbortError`, `throwOAuthTimeoutError`, `createOAuthGenerationTimeout` | ~150 |
| `lib/oauthProxy/sse.ts` | `extractSseData`, `extractPartialImage`, `readImageStream`, `readMultimodeImageStream`, `summarizeEventTypes` | ~280 |
| `lib/oauthProxy/refs.ts` | `supportedImageMime`, `normalizeReferenceForOAuth` | ~40 |
| `lib/oauthProxy/context.ts` | `getOAuthUrl`, `getOAuthGenerationTimeoutMs`, `waitForOAuthReady`, `resolveReasoningEffort`, `resolveWebSearchEnabled`, `buildImageTools`, `fetchOAuth` | ~120 |
| `lib/oauthProxy/generate.ts` | `generateViaOAuth`, `generateMultimodeViaOAuth` | ~330 |
| `lib/oauthProxy/edit.ts` | `editViaOAuth` | ~150 |
| `lib/oauthProxy/index.ts` | (optional helper barrel; see below) | — |

**MODIFY:**
- `lib/oauthProxy.ts` → **becomes a thin barrel re-export** (~30 LOC). Public import path unchanged for callers.

## Diff highlights

### Final `lib/oauthProxy.ts`
```ts
// lib/oauthProxy.ts — barrel; preserves public import surface
export {
  REAL_PERSON_RESEARCH_DIRECTIVE,
  AUTO_PROMPT_FIDELITY_SUFFIX,
  DIRECT_PROMPT_FIDELITY_SUFFIX,
  PROMPT_FIDELITY_SUFFIX,
  GENERATE_DEVELOPER_PROMPT,
  GENERATE_NO_SEARCH_DEVELOPER_PROMPT,
  EDIT_DEVELOPER_PROMPT,
  EDIT_NO_SEARCH_DEVELOPER_PROMPT,
  buildUserTextPrompt,
  buildMultimodeSequencePrompt,
  buildEditTextPrompt,
  buildEditResearchTextPrompt,
} from "./oauthProxy/prompts.ts";
export { parseOpenAIErrorBody } from "./oauthProxy/errors.ts";
export { waitForOAuthReady } from "./oauthProxy/context.ts";
export { generateViaOAuth, generateMultimodeViaOAuth } from "./oauthProxy/generate.ts";
export { editViaOAuth } from "./oauthProxy/edit.ts";
```
Verified public symbols (greppable):
```bash
grep -E 'from "[^"]*lib/oauthProxy"|from "[^"]*lib/oauthProxy\\.ts"|from "../lib/oauthProxy' lib routes bin tests -r
```
The barrel must export every symbol returned by that grep.

### Test guarantee
- `tests/prompt-fidelity.test.js`, `tests/generation-errors.test.js`, `tests/oauth-normalize.test.js`, `tests/oauth-proxy-error-safety.test.js` all import from `../lib/oauthProxy.ts` (the barrel). They MUST stay green with zero edits.
- New direct imports from `../lib/oauthProxy/sse.ts` etc. are allowed and recommended for new tests, but legacy paths cannot break.

### `npm run lint:pkg`
The current lint rule pins `package.json files[]`. After split, `lib/` still recursively contains the new subfolder, so `lib/` whitelist is sufficient — no `lint:pkg` change needed.

### prepack flow
`tsc -p tsconfig.build.json` already includes `lib/**/*.ts` recursively. Confirm `tsconfig.build.json` `include` covers `lib/oauthProxy/*.ts`:
```json
"include": [
  "server.ts",
  "config.ts",
  "lib/**/*.ts",      // ✅ recursive — covers new lib/oauthProxy/
  "routes/**/*.ts",
  "types/**/*.ts"
]
```
Yes — already recursive. No tsconfig change.

## Phased execution (within P04)

**Sub-phase P04a (single PR):** **No-op split.** Move code only; no signature changes. Verify the barrel preserves every export.
- Sub-agent dispatch (claude-opus-4.7):
  > "Split lib/oauthProxy.ts into the 7 files in lib/oauthProxy/ per [list]. Preserve every export verbatim. Replace lib/oauthProxy.ts with a barrel that re-exports the original public symbols. Run `npm run typecheck && npm test && npm run build:server`. Report any test failure with file:line."
- Verify with GPT Pro: paste before/after public-symbol diff list and ask for "did any exported symbol vanish or change shape?".

**Sub-phase P04b (separate PR, optional):** **Inline cleanup.** Now that files are smaller, do focused cleanups (rename internal helpers, tighten any internal types). Each commit ≤ 50 LOC delta.

## Verify

```bash
# After P04a
npm run typecheck
npm test            # 539/539; especially these files:
node --import tsx --test \
  tests/prompt-fidelity.test.js \
  tests/generation-errors.test.js \
  tests/oauth-normalize.test.js \
  tests/oauth-proxy-error-safety.test.js
npm run build:server
ls lib/oauthProxy/*.js     # 7 emitted artifacts
```

Live integration smoke:
```bash
# Boot server, hit a real OAuth-mode generate, watch SSE stream completes.
npm start &
PID=$!
sleep 3
curl -N -X POST localhost:11783/api/generate -H 'Content-Type: application/json' \
  -d '{"prompt":"smoke test","mode":"oauth"}'
kill $PID
```

## Risk

- **High** if any export is missed → silent runtime crash on import.
- **Mitigation:** automated symbol-diff before/after. Script:
  ```bash
  before=$(git show HEAD:lib/oauthProxy.ts | grep -oE '^export (async )?(function|const|class|interface|type) [A-Za-z_][A-Za-z0-9_]+' | awk '{print $NF}' | sort -u)
  after=$(grep -hoE '^export (async )?(function|const|class|interface|type) [A-Za-z_][A-Za-z0-9_]+|^export\s*\{[^}]+\}' lib/oauthProxy.ts lib/oauthProxy/*.ts | tr -d '{}' | tr ',' '\n' | awk '{print $NF}' | sort -u)
  diff <(echo "$before") <(echo "$after")
  ```
  Must be empty.
- **Trap:** circular imports between `generate.ts` ↔ `sse.ts` ↔ `errors.ts`. If tsc reports `Cannot redeclare ...` or runtime "X is undefined" inside another module's top level, restructure: keep types/constants in `errors.ts` and `prompts.ts` only; helpers may freely import from those leaves.

## GPT Pro verification gate

After P04a is implemented and tests pass locally, run:
```bash
agbrowse web-ai query --vendor chatgpt --model pro --inline-only --prompt "$(cat <<'EOF'
Review this no-op TypeScript split of lib/oauthProxy.ts. The 1003-line file was decomposed into 7 files under lib/oauthProxy/ with a barrel at lib/oauthProxy.ts. Public symbol surface should be unchanged.

[paste git diff --stat + the new lib/oauthProxy.ts barrel + symbol diff output]

Verify:
1. Are all original exports preserved by the barrel?
2. Any circular import risk in the new layout?
3. Anything that should be a `type` re-export vs `value` re-export?
4. Does this split match Node ESM + tsconfig NodeNext expectations?
EOF
)" --json
```

## Rollback

Single revert. Barrel preservation makes this trivial — no caller migration.

## Exit criteria

- [ ] `lib/oauthProxy.ts` is < 80 LOC (barrel only).
- [ ] 7 new files exist under `lib/oauthProxy/` totaling ~1100 LOC (split + small import boilerplate).
- [ ] Symbol-diff script is empty (no export lost).
- [ ] `npm run typecheck` green.
- [ ] `npm test` 539/539; the four oauthProxy-importing tests pass with zero edits.
- [ ] `npm run build:server` emits `.js` for every new `.ts`.
- [ ] GPT Pro review returns no critical issues.
