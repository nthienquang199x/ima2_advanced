# Post-Release Security Audit — v1.1.23..HEAD

**Date**: 2026-06-02
**Scope**: 34 commits since v1.1.23 + uncommitted changes
**Method**: 4-dimension parallel sub-agent audit (backend security, frontend state, API validation, auth/secrets)

## Patches Applied

### P1 — Gemini API key leaked via URL query string
- **File**: routes/keys.ts:166
- **Was**: `fetch(\`${url}?key=${trimmed}\`)` — key visible in logs, proxy, referrer headers
- **Fix**: Use `x-goog-api-key` header instead of query parameter

### P2 — Vertex auth error leaks internal details
- **File**: routes/keys.ts:93
- **Was**: `error: \`Auth init failed: ${e.message}\`` — exposes internal error to client
- **Fix**: Generic error message: `"Service account validation failed"`

### P3 — No size limit on API key input
- **File**: routes/keys.ts:149
- **Fix**: Added 512-byte limit on API key, 50KB limit on Vertex service account JSON

### P4 — Weak key masking exposes too many characters
- **File**: routes/keys.ts:30-33
- **Was**: First 4 + last 3 chars exposed (7 chars for short keys)
- **Fix**: First 4 + last 2, minimum length raised to 10

### P5 — Grok size format parsed without structure validation
- **File**: lib/grokSizeMapper.ts:63-71
- **Was**: No minimum part count check; `"grok:"` alone would produce garbage
- **Fix**: Reject if `parts.length < 3`

### P6 — Division by zero in aspect ratio math
- **File**: lib/grokSizeMapper.ts:45-47
- **Was**: `w / h` with no check for `h === 0`
- **Fix**: Guard `Number.isFinite(h) && h !== 0`, fallback to 1

### P7 — Node session evaporation (separate devlog)
- See `260602_node-session-evaporation-fix.md`

## Findings Not Patched (accepted risk or needs design discussion)

### Accepted — Local-only tool design
- `/api/keys/*` has no authentication — ima2 is a localhost-only personal tool. Adding auth middleware would break the setup UX. Risk accepted for local deployment.
- API keys stored plaintext in `~/.ima2/config.json` with 0o600 — standard for local CLI tools (same pattern as `.npmrc`, `.docker/config.json`). Encryption would require a master key, adding complexity without meaningful security gain for local use.

### Deferred — Needs architecture change
- Vertex service account JSON contains private key stored in config — requires redesign to support keyring/env-only mode. Filed as future work.
- RuntimeContext holds raw keys in memory — would need a credential-store abstraction.

### Low priority
- Silent localStorage `catch {}` in save functions — only affects edge case (quota exceeded). Would need unified persistence error reporting.
- `as any` casts for grokAspectRatio/grokResolution — type safety issue, not security. Fix when adding GenerationDefaults type to include these fields.
- Provider switch doesn't flush graph save — race window is narrow (provider switch + page close within 800ms debounce). Existing guards from session evaporation fix cover most cases.

## Verification
- `npx tsc --noEmit` — pass
- Contract tests — pass
- Frontend employee verification — pending
