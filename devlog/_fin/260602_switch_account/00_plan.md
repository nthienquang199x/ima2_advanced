# Switch Account — Device Code OAuth for Grok + Codex

## Date: 2026-06-02
## Status: PLAN

## Summary
ima2-gen Settings QuotaCard에 Switch Account 버튼을 추가한다. Grok과 Codex 모두 device-code OAuth flow를 사용하여 웹 UI에서 비대화형으로 계정 전환이 가능하다.

## UX Flow (Both Providers)
1. 사용자가 QuotaCard 하단 "Switch Account" 버튼 클릭
2. 서버: device code 요청 → `user_code` + `verification_url` 반환
3. 프론트: 새 탭으로 `verification_uri_complete` 열기 + user_code 표시 + 폴링 스피너
4. 사용자: 새 탭에서 로그인 + 코드 승인
5. 서버: 5초 간격 폴링 → 토큰 수신 → auth.json 덮어쓰기
6. 프론트: 완료 감지 → billing/quota 새로고침

## Technical Details

### Grok Device Code
- Endpoint: POST `https://auth.x.ai/oauth2/device/code`
- client_id: `b1a00492-073a-47ea-816f-4c329264a828`
- scope: `openid profile email offline_access grok-cli:access api:access`
- Token endpoint: `https://auth.x.ai/oauth2/token`
- grant_type: `urn:ietf:params:oauth:grant-type:device_code`
- Token save: `~/.progrok/auth.json` (progrok TokenData format)
- expires_in: 900s, poll interval: 5s

### Codex Device Code
- Endpoint: POST `https://auth0.openai.com/oauth/device/code`
- client_id: `app_EMoamEEZ73f0CkXaXp7hrann`
- scope: `openid profile email offline_access`
- Token endpoint: `https://auth0.openai.com/oauth/token`
- grant_type: `urn:ietf:params:oauth:grant-type:device_code`
- Token save: `~/.codex/auth.json` (codex format: {tokens: {id_token, access_token, refresh_token, account_id}, last_refresh})
- verification_uri: `https://auth.openai.com/codex/device`

---

## Files

### NEW: `routes/auth.ts` — Device code OAuth API endpoints

```typescript
import type { Express } from "express";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

// --- Grok ---
const GROK_CLIENT_ID = "b1a00492-073a-47ea-816f-4c329264a828";
const GROK_SCOPE = "openid profile email offline_access grok-cli:access api:access";
const GROK_DEVICE_CODE_URL = "https://auth.x.ai/oauth2/device/code";
const GROK_TOKEN_URL = "https://auth.x.ai/oauth2/token";

// --- Codex ---
const CODEX_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann";
const CODEX_SCOPE = "openid profile email offline_access";
const CODEX_DEVICE_CODE_URL = "https://auth0.openai.com/oauth/device/code";
const CODEX_TOKEN_URL = "https://auth0.openai.com/oauth/token";

// In-flight device code sessions
const pendingSessions = new Map<string, {
  provider: string;
  deviceCode: string;
  tokenUrl: string;
  clientId: string;
  expiresAt: number;
  interval: number;
  pollTimer?: ReturnType<typeof setInterval>;
  resolved?: { accessToken: string; refreshToken?: string; idToken?: string; expiresIn?: number };
  error?: string;
}>();

function sessionId() { return Math.random().toString(36).slice(2, 10); }

async function requestDeviceCode(provider: "grok" | "codex") {
  const isGrok = provider === "grok";
  const res = await fetch(isGrok ? GROK_DEVICE_CODE_URL : CODEX_DEVICE_CODE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: isGrok ? GROK_CLIENT_ID : CODEX_CLIENT_ID,
      scope: isGrok ? GROK_SCOPE : CODEX_SCOPE,
    }),
    signal: AbortSignal.timeout(15000),
  });
  if (!res.ok) throw new Error(`Device code request failed: ${res.status}`);
  return res.json() as Promise<{
    device_code: string;
    user_code: string;
    verification_uri: string;
    verification_uri_complete?: string;
    expires_in: number;
    interval?: number;
  }>;
}

function startPolling(sid: string) {
  const session = pendingSessions.get(sid);
  if (!session) return;
  session.pollTimer = setInterval(async () => {
    try {
      const res = await fetch(session.tokenUrl, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          grant_type: "urn:ietf:params:oauth:grant-type:device_code",
          client_id: session.clientId,
          device_code: session.deviceCode,
        }),
        signal: AbortSignal.timeout(10000),
      });
      if (res.ok) {
        const tokens = await res.json() as Record<string, unknown>;
        session.resolved = {
          accessToken: tokens.access_token as string,
          refreshToken: tokens.refresh_token as string | undefined,
          idToken: tokens.id_token as string | undefined,
          expiresIn: tokens.expires_in as number | undefined,
        };
        clearInterval(session.pollTimer);
        saveTokens(session.provider, session.resolved);
        return;
      }
      const err = await res.json() as { error?: string };
      if (err.error === "authorization_pending") return;
      if (err.error === "slow_down") return;
      session.error = err.error || "unknown";
      clearInterval(session.pollTimer);
    } catch {
      // network error — keep polling
    }
  }, session.interval * 1000);
}

function saveTokens(provider: string, tokens: { accessToken: string; refreshToken?: string; idToken?: string; expiresIn?: number }) {
  if (provider === "grok") {
    const dir = join(homedir(), ".progrok");
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true, mode: 0o700 });
    let email: string | undefined;
    if (tokens.idToken) {
      try {
        const payload = JSON.parse(Buffer.from(tokens.idToken.split(".")[1], "base64url").toString());
        email = payload.email;
      } catch {}
    }
    const data: Record<string, unknown> = {
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
      expiresAt: tokens.expiresIn ? Date.now() + tokens.expiresIn * 1000 : undefined,
      tokenEndpoint: GROK_TOKEN_URL,
    };
    if (email) data.email = email;
    writeFileSync(join(dir, "auth.json"), JSON.stringify(data, null, 2), { mode: 0o600 });
  } else {
    const dir = join(homedir(), ".codex");
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true, mode: 0o700 });
    let accountId = "";
    if (tokens.idToken) {
      try {
        const payload = JSON.parse(Buffer.from(tokens.idToken.split(".")[1], "base64url").toString());
        accountId = payload["https://api.openai.com/auth"]?.user_id ?? payload.sub ?? "";
      } catch {}
    }
    const data = {
      tokens: {
        id_token: tokens.idToken ?? "",
        access_token: tokens.accessToken,
        refresh_token: tokens.refreshToken ?? "",
        account_id: accountId,
      },
      last_refresh: new Date().toISOString(),
    };
    writeFileSync(join(dir, "auth.json"), JSON.stringify(data, null, 2), { mode: 0o600 });
  }
}

export function registerAuthRoutes(app: Express) {
  // POST /api/auth/switch — start device code flow
  app.post("/api/auth/switch", async (req, res) => {
    const provider = req.body?.provider;
    if (provider !== "grok" && provider !== "codex") {
      return res.status(400).json({ error: "provider must be grok or codex" });
    }
    try {
      const dc = await requestDeviceCode(provider);
      const sid = sessionId();
      const isGrok = provider === "grok";
      pendingSessions.set(sid, {
        provider,
        deviceCode: dc.device_code,
        tokenUrl: isGrok ? GROK_TOKEN_URL : CODEX_TOKEN_URL,
        clientId: isGrok ? GROK_CLIENT_ID : CODEX_CLIENT_ID,
        expiresAt: Date.now() + dc.expires_in * 1000,
        interval: Math.max(dc.interval || 5, 5),
      });
      startPolling(sid);
      setTimeout(() => { pendingSessions.delete(sid); }, dc.expires_in * 1000 + 60000);
      res.json({
        sessionId: sid,
        userCode: dc.user_code,
        verificationUrl: dc.verification_uri_complete || dc.verification_uri,
        expiresIn: dc.expires_in,
      });
    } catch (e) {
      res.status(502).json({ error: (e as Error).message });
    }
  });

  // GET /api/auth/switch/:sessionId — poll status
  app.get("/api/auth/switch/:sessionId", (req, res) => {
    const session = pendingSessions.get(req.params.sessionId);
    if (!session) return res.status(404).json({ status: "expired" });
    if (session.resolved) {
      pendingSessions.delete(req.params.sessionId);
      return res.json({ status: "complete" });
    }
    if (session.error) {
      pendingSessions.delete(req.params.sessionId);
      return res.json({ status: "error", error: session.error });
    }
    if (Date.now() > session.expiresAt) {
      pendingSessions.delete(req.params.sessionId);
      return res.json({ status: "expired" });
    }
    res.json({ status: "pending" });
  });
}
```

### MODIFY: `routes/index.ts` — register auth routes

```diff
+import { registerAuthRoutes } from "./auth.js";
 ...
   registerQuotaRoutes(app, ctx);
+  registerAuthRoutes(app);
```

### MODIFY: `ui/src/components/settings/QuotaCard.tsx` — Switch Account buttons

Add SwitchAccountButton component + integration into both Codex and Grok cards.

### MODIFY: `server.ts` — add body-parser for JSON (if not already)

Express json() middleware should already be configured; verify only.

---

## cli-jaw Documentation

### NEW: `devlog/_plan/260602_switch_account/00_plan.md` (this file — shared reference)

---

## Verification Plan

### V1. Device Code Request
```bash
curl -sS -X POST http://localhost:4959/api/auth/switch -H "Content-Type: application/json" -d '{"provider":"grok"}' | jq '.userCode, .verificationUrl, .sessionId'
```

### V2. Poll Status
```bash
# After V1, poll with sessionId
curl -sS http://localhost:4959/api/auth/switch/<sessionId> | jq '.status'
# Expected: "pending" → "complete" (after browser approval)
```

### V3. Token Save
```bash
# After switch complete
cat ~/.progrok/auth.json | jq '.accessToken[:20]'
# Should show new token
```

### V4. QuotaCard UI
- Settings → Rate limits → Grok card has "Switch Account" button
- Click → new tab opens xAI/OpenAI auth page
- After approval → card refreshes with new account info

### V5. Build
```bash
npx tsc --noEmit  # ima2-gen
npm run build:server && npm run ui:build
```
