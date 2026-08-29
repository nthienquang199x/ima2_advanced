# Security + Quality Audit — v1.1.23 → HEAD

## Date: 2026-06-02
## Scope: 25 commits, 60 files changed
## Status: ALL PATCHED (commit fdfc9cb)

## Findings

| # | Severity | File | Issue | Fix | Commit |
|---|----------|------|-------|-----|--------|
| 1 | MEDIUM | routes/auth.ts | Session Map unbounded growth (DoS) | MAX_CONCURRENT_SESSIONS=20 cap | fdfc9cb |
| 2 | LOW | routes/auth.ts | Math.random() session ID (guessable) | crypto.randomBytes(16) | fdfc9cb |
| 3 | LOW | routes/auth.ts | deviceCode lingers in memory | delete s.deviceCode in cleanup() | fdfc9cb |
| 4 | LOW | QuotaCard.tsx | Switch button double-click unguarded | useRef switching guard | fdfc9cb |
| 5 | INFO | geminiApiImageAdapter.ts | API key in URL query string | x-goog-api-key header | fdfc9cb |
| 6 | INFO | routes/quota.ts | Email in API response | Acceptable for local tool | — |
| 7 | OK | agyImageAdapter.ts | Subprocess prompt injection | Safe: prompt via stdin, not args | — |
| 8 | OK | ApiKeyInput.tsx | isEnv guard removal | Benign: server validates | — |

## Build & Test
- tsc --noEmit: 0 errors
- npm test: 920/920 pass, 0 fail
- `as any` casts: 4 pragmatic bridge casts, no hidden type errors

## UX Audit
- setProvider/setImageModel: no circular dependency (both use set() directly)
- ImageModelSelect shortLabel.split(" "): safe for all current labels
- Duplicate nano-banana-2 in IMAGE_MODEL_OPTIONS: isImageModel() uses .some(), no break
- SwitchAccountButton: double-click now guarded with useRef

## Verification
- Employee (Backend) verified all 5 patches at fdfc9cb
- All evidence: file reads, grep, test run — DONE verdict
